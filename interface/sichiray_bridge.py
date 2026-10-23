"""Sichiray serial bridge with experimental SADT fatigue-tendency classification."""
import argparse
from collections import deque
from datetime import datetime, timezone
from functools import partial
from http.server import ThreadingHTTPServer
import json
import math
from pathlib import Path
import sys
import threading
import time
import uuid
from urllib.parse import urlparse, parse_qs

from eeg_bridge import Handler

MODEL_ROOT = Path(r'E:\CODEX Projects\SADT-Fp1Fp2')
if str(MODEL_ROOT) not in sys.path:
    sys.path.insert(0, str(MODEL_ROOT))
try:
    from live_fatigue_inference50 import LiveFatigueInference as LiveHeadsetInference
except Exception as model_import_error:
    LiveHeadsetInference = None
    MODEL_IMPORT_ERROR = str(model_import_error)
else:
    MODEL_IMPORT_ERROR = None


def parse_line(line):
    fields = line.decode('ascii').strip().split(',')
    if len(fields) != 21:
        raise ValueError('Expected exactly 21 columns')
    v = [float(x) for x in fields]
    if not all(math.isfinite(x) for x in v):
        raise ValueError('Nonfinite data')
    if not v[0].is_integer() or v[0] < 0 or not v[2].is_integer():
        raise ValueError('Invalid sequence or wear code')
    # ADC words may be printed as signed values or unsigned 16-bit words.
    def signed(x):
        if not x.is_integer() or not -32768 <= x <= 65535:
            raise ValueError('Invalid 16-bit ADC word')
        return int(x) - 65536 if x > 32767 else int(x)
    return dict(sequence=int(v[0]), battery_voltage=v[1], wear_code=int(v[2]),
                wear_measurement=v[3], eeg=[signed(v[4]), signed(v[5])],
                eeg_filtered=v[6:8], gyroscope=v[8:11], acceleration=v[11:14],
                band_values=dict(zip(['delta','theta','alpha','beta','gamma'], v[14:19])),
                device_attention=v[19], device_relaxation=v[20])


class Store:
    def __init__(self, wear_ok=None):
        self.lock = threading.Lock()
        self.latest = None
        self.received = 0
        self.count = 0
        self.errors = 0
        self.status = 'waiting'
        self.wear_ok = wear_ok
        self.arrivals = deque(maxlen=1000)
        self.history = deque(maxlen=15000)
        self.session = uuid.uuid4().hex
        self.inference = LiveHeadsetInference() if LiveHeadsetInference else None

    def update(self, packet):
        with self.lock:
            self.latest = packet
            self.received = time.time()
            self.count += 1
            self.history.append(dict(id=self.count, time=self.received, sequence=packet['sequence'], eeg_filtered=list(packet["eeg_filtered"]), attention=packet["device_attention"], relaxation=packet["device_relaxation"], wear_code=packet["wear_code"]))
            if self.inference:
                try:
                    self.inference.push(packet, self.received)
                except Exception as error:
                    self.inference.set_result('inference_error', '推理暂时失败：' + type(error).__name__)
            self.arrivals.append(self.received)
            while self.arrivals and self.received - self.arrivals[0] > 5:
                self.arrivals.popleft()
            self.status = 'streaming'

    def samples(self, after):
        with self.lock:
            rows = [row for row in self.history if row['id'] > after]
            return dict(session=self.session, samples=rows, cursor=self.count,
                        truncated=bool(self.history and after and after < self.history[0]['id']-1),
                        connection_status=self.status)

    def payload(self):
        with self.lock:
            valid = self.latest is not None and time.time() - self.received < 2 and self.status == 'streaming'
            result = dict(source='real', device='Sichiray Gemini', has_data=valid,
                          channels=['Fp1','Fp2'], sample_rate_hz=250, eeg_unit='ADC counts',
                          sample_count=self.count, parse_errors=self.errors,
                          connection_status=self.status, calibrated=False,
                          model_compatible=False,
                          candidate_inference=(self.inference.snapshot() if self.inference else {
                              'status':'model_unavailable','ready':False,
                              'message':MODEL_IMPORT_ERROR or '候选模型模块未加载',
                              'output_meaning':'反应时间代理，不是疲劳概率','hardware_validated':False}))
            if not valid and self.latest is not None:
                result['connection_status'] = 'waiting'
                result['candidate_inference'] = dict(status='data_interrupted',ready=False,
                    model='SADT Fp1/Fp2 黎曼疲劳分类 v1',message='头环数据中断，等待重新采集',
                    hardware_validated=False,probability_calibrated=False)
            if valid:
                result.update(self.latest)
                span = self.arrivals[-1] - self.arrivals[0]
                result['stream_rate_hz'] = round((len(self.arrivals)-1)/span, 1) if span > 0 else None
                result['timestamp'] = datetime.fromtimestamp(self.received, timezone.utc).isoformat()
                code = self.latest['wear_code']
                result['wear_status'] = 'failed' if code == 0 else ('ok' if code == self.wear_ok else 'unknown')
                if result['wear_status'] == 'ok' and 0 <= self.latest['device_attention'] <= 100:
                    result['attention'] = self.latest['device_attention']
            return result


def read_serial(args, store, stop):
    import serial
    while not stop.is_set():
        try:
            with serial.Serial(args.port, args.baudrate, timeout=.2) as stream:
                print(f'Connected: {args.port}', flush=True)
                buffer = bytearray()
                while not stop.is_set():
                    buffer.extend(stream.read(min(max(stream.in_waiting, 1), 8192)))
                    while b'\n' in buffer:
                        line, _, rest = buffer.partition(b'\n')
                        buffer = bytearray(rest)
                        try:
                            packet = parse_line(line)
                        except (ValueError, UnicodeError):
                            with store.lock:
                                store.errors += 1
                            continue
                        store.update(packet)
                    if len(buffer) > 16384:
                        buffer.clear()
                        with store.lock:
                            store.errors += 1
        except (serial.SerialException, OSError) as error:
            with store.lock:
                store.status = 'disconnected'
                store.latest = None
            print(f'Serial unavailable: {error}; retrying in 3 seconds.', flush=True)
            stop.wait(3)


class SerialControl:
    def __init__(self, args, store):
        self.args, self.store = args, store
        self.lock = threading.Lock()
        self.worker = None
        self.stop = threading.Event()
        self.enabled = False

    def state(self):
        with self.lock:
            return self._state()

    def _state(self):
        return dict(enabled=self.enabled, port=self.args.port,
                    connection_status=self.store.payload()['connection_status'])

    def set_enabled(self, enabled):
        with self.lock:
            if enabled and not self.enabled:
                self.stop = threading.Event()
                with self.store.lock:
                    self.store.status = 'waiting'
                    self.store.latest = None
                    self.store.arrivals.clear()
                    self.store.history.clear()
                    self.store.session = uuid.uuid4().hex
                    if self.store.inference:
                        self.store.inference.reset()
                self.worker = threading.Thread(target=read_serial,
                    args=(self.args, self.store, self.stop), daemon=True)
                self.enabled = True
                self.worker.start()
            elif not enabled:
                self.stop.set()
                if self.worker:
                    self.worker.join(4)
                    if self.worker.is_alive():
                        raise RuntimeError('Serial reader is still stopping; retry close')
                self.enabled = False
                with self.store.lock:
                    self.store.latest = None
                    self.store.status = 'closed'
            return self._state()


class ControlHandler(Handler):
    control = None

    def reply(self, status, payload):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if urlparse(self.path).path == '/api/model/verification':
            try:
                path = MODEL_ROOT / 'results' / 'fatigue_classifier_v1' / 'inference_verification.json'
                self.reply(200, json.loads(path.read_text(encoding='utf-8')))
            except (OSError, ValueError):
                self.reply(503, {'error': 'Verification record unavailable'})
        elif urlparse(self.path).path == '/api/eeg/samples':
            try:
                after = max(0, int(parse_qs(urlparse(self.path).query).get('after', ['0'])[0]))
            except ValueError:
                self.reply(400, {'error': 'Invalid cursor'})
                return
            self.reply(200, self.store.samples(after))
        elif self.path == '/api/serial/status':
            self.reply(200, self.control.state())
        else:
            super().do_GET()

    def do_POST(self):
        # Custom header prevents cross-origin forms from controlling hardware.
        origin = self.headers.get('Origin')
        if self.headers.get('X-Serial-Control') != '1' or (origin and origin != 'http://' + self.headers.get('Host', '')):
            self.reply(403, {'error': 'Same-origin control required'})
            return
        if self.path not in ('/api/serial/open', '/api/serial/close'):
            self.reply(404, {'error': 'Unknown action'})
            return
        try:
            self.reply(200, self.control.set_enabled(self.path.endswith('/open')))
        except RuntimeError as error:
            self.reply(503, {'error': str(error)})

    def log_message(self, format, *args):
        # Polling at four requests/second should not fill the service output pipe.
        if args and '/api/' in str(args[0]):
            return
        super().log_message(format, *args)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', default='COM8')
    parser.add_argument('--baudrate', type=int, default=115200)
    parser.add_argument('--http-port', type=int, default=8765)
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--wear-ok-code', type=int, help='Only set after confirming the successful wear code')
    args = parser.parse_args()
    store = Store(args.wear_ok_code)
    ControlHandler.store = store
    control = SerialControl(args, store)
    ControlHandler.control = control
    root = Path(__file__).resolve().parents[1] / 'dist'
    server = ThreadingHTTPServer((args.host, args.http_port), partial(ControlHandler, directory=str(root)))
    control.set_enabled(True)
    print(f'Dashboard: http://{args.host}:{args.http_port}/', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        control.set_enabled(False)
        server.server_close()


if __name__ == '__main__':
    main()
