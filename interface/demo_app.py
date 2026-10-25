"""Portable Windows launcher for the Sichiray Gemini fatigue demonstration."""
import argparse
from argparse import Namespace
import json
import logging
import os
from pathlib import Path
import sys
import threading
import webbrowser

VERSION = '0.1.4'
RELEASES_URL = 'https://github.com/Garyneil/Port-fatigue-dashboard/releases/latest'
ONLINE_URL = 'https://garyneil.github.io/Port-fatigue-dashboard/'


def self_test(output):
    """Exercise the actual bundled model, preprocessing and local HTTP service."""
    from urllib.request import build_opener, ProxyHandler, Request
    urlopen = build_opener(ProxyHandler({})).open
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    if sys.stderr is None:
        sys.stderr = open(os.devnull, 'w')
    import numpy as np
    from live_fatigue_inference50 import LiveFatigueInference
    from signal_processing50 import filter_bank
    from riemann_twochannel import cov, features, expm, logm
    from sichiray_bridge import create_server, MODEL_IMPORT_ERROR
    if MODEL_IMPORT_ERROR:
        raise RuntimeError(MODEL_IMPORT_ERROR)
    model = LiveFatigueInference()
    if model.model is None:
        raise RuntimeError('Bundled model missing')
    t = np.arange(700) / 50
    signal = np.array([np.sin(2*np.pi*6*t), np.cos(2*np.pi*9*t)])
    bands = filter_bank(signal)
    matrices = np.array([cov(b[:, -200:]) for b in bands])
    center = expm(logm(matrices))
    vector = features(matrices[None], center)[0]
    z = (vector-model.model['mean']) / model.model['scale']
    from scipy.special import expit
    score = float(expit(z @ model.model['coef'] + model.model['intercept']))
    assert np.isfinite(score) and 0 <= score <= 1
    # Test inputs are synthetic and never served as live headset data.
    for i in range(3200):
        model.push({'sequence':i % 256, 'wear_code':1,
                    'eeg_filtered':signal[:, i % 700].tolist()}, 1000+i/50)
    assert model.snapshot()['status'] in ('fatigue_inference', 'out_of_distribution')
    model.reference_path = Path(output).with_name('reference-self-test.npz')
    model.save_reference()
    restored = LiveFatigueInference(reference_path=model.reference_path)
    assert restored.snapshot()['reference_loaded']
    assert np.allclose(restored.center, model.center)
    restored.recalibrate()
    assert not model.reference_path.exists()
    server, control = create_server(Namespace(port='TEST-NO-DEVICE', baudrate=115200,
        wear_ok_code=None, host='127.0.0.1', http_port=0))
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    url = f'http://127.0.0.1:{server.server_port}'
    try:
        with urlopen(url + '/') as response:
            assert 'SADT' in response.read().decode('utf-8')
        with urlopen(url + '/api/eeg/latest') as response:
            payload = json.load(response)
            assert payload['has_data'] is False
            assert payload['candidate_inference']['status'] == 'waiting_for_data'
        with urlopen(url + '/api/model/verification') as response:
            assert json.load(response)['numeric_export_max_abs_error'] == 0
        request = Request(url + '/api/model/recalibrate', data=b'',
            headers={'X-Serial-Control':'1'}, method='POST')
        with urlopen(request) as response:
            reference = json.load(response)
            assert reference['reference_windows'] == 0
            assert reference['reference_ready'] is False
        result = dict(version=VERSION, passed=True, model_loaded=True,
            synthetic_numeric_check_score=score, synthetic_stream_status=model.snapshot()['status'],
            http_and_assets=True, reference_cache_roundtrip=True, no_device_data_fabricated=True)
        Path(output).write_text(json.dumps(result, indent=2), encoding='utf-8')
    finally:
        server.shutdown()
        server.server_close()
        worker.join(3)


def run_gui():
    import tkinter as tk
    from tkinter import ttk, messagebox
    from serial.tools import list_ports
    from sichiray_bridge import create_server, MODEL_IMPORT_ERROR
    from live_fatigue_inference50 import MODEL

    data_dir = Path(os.environ.get('LOCALAPPDATA', str(Path.home()))) / 'PortFatigueDemo'
    data_dir.mkdir(parents=True, exist_ok=True)
    log_path = data_dir / 'demo.log'
    # Windowed builds have no stdout; redirect backend diagnostics to a user log.
    log_stream = log_path.open('a', encoding='utf-8', buffering=1)
    sys.stdout = sys.stderr = log_stream
    logging.basicConfig(stream=log_stream, level=logging.INFO)
    config_path = data_dir / 'config.json'
    try:
        config = json.loads(config_path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        config = {}

    root = tk.Tk()
    root.title(f'脑电疲劳监测 · 演示版 {VERSION}')
    root.geometry('640x410')
    root.minsize(620, 410)
    root.configure(bg='#eef3f7')
    frame = ttk.Frame(root, padding=24)
    frame.pack(fill='both', expand=True)
    ttk.Label(frame, text='脑电疲劳监测', font=('Microsoft YaHei UI', 20, 'bold')).pack(anchor='w')
    ttk.Label(frame, text=f'双子座头环 · Fp1 / Fp2 · 演示版 {VERSION}').pack(anchor='w', pady=(4, 20))
    row = ttk.Frame(frame)
    row.pack(fill='x')
    ttk.Label(row, text='设备串口').pack(side='left', padx=(0, 10))
    port_var = tk.StringVar(value=config.get('port', ''))
    ports_box = ttk.Combobox(row, textvariable=port_var, width=25)
    ports_box.pack(side='left', fill='x', expand=True)
    status_var = tk.StringVar(value='连接头环后，选择串口并点击“启动演示”。')
    detail_var = tk.StringVar(value='首次连续采集约 1 分钟建立参考，信号合格后显示疲劳倾向。')
    progress_var = tk.DoubleVar(value=0)
    progress_text = tk.StringVar(value='0 / 12 · 0%')
    service = {'server':None, 'control':None, 'worker':None, 'url':None}

    def refresh_ports():
        ports = list(list_ports.comports())
        ports_box['values'] = [p.device for p in ports]
        selected = port_var.get().strip()
        if ports and selected not in [p.device for p in ports]:
            port_var.set(ports[0].device)
        if not ports:
            status_var.set('未检测到串口。请连接头环接收器，再点击“刷新”。')
        elif not service['server']:
            detail_var.set('；'.join(f'{p.device} · {p.description}' for p in ports))

    ttk.Button(row, text='刷新', command=refresh_ports).pack(side='left', padx=(8, 0))
    buttons = ttk.Frame(frame)
    buttons.pack(fill='x', pady=(20, 16))

    def stop():
        if service['server']:
            try:
                service['control'].set_enabled(False)
                service['server'].shutdown()
                service['server'].server_close()
                service['worker'].join(3)
            except Exception:
                logging.exception('Stop failed')
                messagebox.showerror('停止失败', f'请关闭程序后重新启动。日志：{log_path}')
                return
            service.update(server=None, control=None, worker=None, url=None)
        start_button.configure(state='normal')
        ports_box.configure(state='normal')
        stop_button.configure(state='disabled')
        recalibrate_button.configure(state='disabled')
        status_var.set('演示已停止，设备串口已释放。')
        progress_var.set(0)
        progress_text.set('0 / 12 · 0%')

    def start():
        if service['server']:
            webbrowser.open(service['url'])
            return
        port = port_var.get().strip()
        if not port:
            messagebox.showinfo('请选择串口', '请连接头环接收器，点击“刷新”，然后选择设备串口。')
            return
        if MODEL_IMPORT_ERROR or not MODEL.exists():
            messagebox.showerror('模型加载失败', f'请重新解压完整演示包。\n{MODEL_IMPORT_ERROR or MODEL}')
            return
        server = control = None
        try:
            # Let Windows allocate an available port, avoiding conflicts with old services.
            server, control = create_server(Namespace(port=port, baudrate=115200,
                wear_ok_code=None, host='127.0.0.1', http_port=0,
                reference_path=data_dir / 'personal-reference-v1.npz'))
            worker = threading.Thread(target=server.serve_forever, daemon=True)
            worker.start()
            control.set_enabled(True)
            url = f'http://127.0.0.1:{server.server_port}/'
            service.update(server=server, control=control, worker=worker, url=url)
            config_path.write_text(json.dumps({'port':port}), encoding='utf-8')
            start_button.configure(state='disabled')
            ports_box.configure(state='disabled')
            stop_button.configure(state='normal')
            recalibrate_button.configure(state='normal')
            webbrowser.open(url)
        except Exception as error:
            logging.exception('Startup failed')
            if control:
                control.set_enabled(False)
            if server:
                server.server_close()
            service.update(server=None, control=None, worker=None, url=None)
            messagebox.showerror('启动失败', f'{error}\n日志：{log_path}')

    start_button = ttk.Button(buttons, text='启动演示', command=start)
    start_button.pack(side='left')
    ttk.Button(buttons, text='打开监测界面', command=lambda: webbrowser.open(service['url']) if service['url'] else start()).pack(side='left', padx=8)
    stop_button = ttk.Button(buttons, text='停止 / 释放设备', command=stop, state='disabled')
    stop_button.pack(side='left')
    def recalibrate():
        if service['control']:
            service['control'].store.recalibrate()
            progress_var.set(0)
            progress_text.set('0 / 12 · 0%')
            detail_var.set('重新校准已开始，正在采集新的个人参考。')
    recalibrate_button = ttk.Button(buttons, text='重新校准', command=recalibrate, state='disabled')
    recalibrate_button.pack(side='left', padx=(8, 0))
    ttk.Separator(frame).pack(fill='x', pady=8)
    ttk.Label(frame, textvariable=status_var, wraplength=570, font=('Microsoft YaHei UI', 11)).pack(anchor='w', pady=8)
    ttk.Label(frame, textvariable=detail_var, wraplength=570).pack(anchor='w', pady=4)
    progress_row = ttk.Frame(frame)
    progress_row.pack(fill='x', pady=(10, 4))
    ttk.Progressbar(progress_row, variable=progress_var, maximum=100,
                    mode='determinate').pack(side='left', fill='x', expand=True)
    ttk.Label(progress_row, textvariable=progress_text, width=22,
              anchor='e').pack(side='right', padx=(12, 0))
    footer = ttk.Frame(frame)
    footer.pack(side='bottom', fill='x', pady=(12, 0))
    ttk.Button(footer, text='下载新版本', command=lambda:webbrowser.open(RELEASES_URL)).pack(side='left')
    ttk.Button(footer, text='在线页面', command=lambda:webbrowser.open(ONLINE_URL)).pack(side='left', padx=8)
    ttk.Button(footer, text='打开日志', command=lambda:os.startfile(str(log_path))).pack(side='right')

    def tick():
        if service['control']:
            payload = service['control'].store.payload()
            labels = {'closed':'已关闭', 'streaming':'正在接收真实脑电', 'waiting':'等待设备数据', 'disconnected':'串口连接失败，正在重试'}
            status_var.set(f"{port_var.get()} · {labels.get(payload['connection_status'], payload['connection_status'])}")
            candidate = payload['candidate_inference']
            if payload['has_data'] or candidate.get('display_stale') or candidate.get('reference_ready'):
                score = candidate.get('drowsy_model_score')
                detail_var.set(f"{round(score*100)} / 100 · {candidate.get('message', '')}"
                               if score is not None else candidate.get('message', ''))
                count = min(12, max(0, candidate.get('reference_windows', 0)))
                percent = round(count / 12 * 100)
                progress_var.set(percent)
                progress_text.set(('已加载上次参考 · 100%' if candidate.get('reference_loaded') else '参考已完成 · 100%') if candidate.get('reference_ready')
                                  else f'{count} / 12 · {percent}%')
            else:
                detail_var.set('请检查设备电源、串口和佩戴；关闭正在占用串口的厂家软件。')
        root.after(1000, tick)

    def close():
        stop()
        root.destroy()

    root.protocol('WM_DELETE_WINDOW', close)
    refresh_ports()
    tick()
    root.mainloop()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--self-test', metavar='RESULT_JSON')
    args = parser.parse_args()
    if args.self_test:
        try:
            self_test(args.self_test)
        except Exception as error:
            Path(args.self_test).parent.mkdir(parents=True, exist_ok=True)
            Path(args.self_test).write_text(json.dumps({'passed':False, 'error':repr(error)}), encoding='utf-8')
            sys.exit(1)
    else:
        run_gui()
