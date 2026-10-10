"""Serve the dashboard and real serial EEG from the user's collector project.

No synthetic data or fatigue inference is produced by this bridge.
"""
from argparse import ArgumentParser
from datetime import datetime, timezone
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import importlib.util
import json
import math
import threading
import time


class LatestEEG:
    def __init__(self, sample_rate):
        self.lock = threading.Lock()
        self.sample_rate = sample_rate
        self.values = None
        self.received = 0
        self.count = 0

    def update(self, sample):
        # Serial12HexReader yields timestamp + 8 EEG + 4 ECG values.
        values = list(sample[1:9])
        if len(values) != 8 or not all(math.isfinite(v) for v in values):
            return
        with self.lock:
            self.values = values
            self.received = time.time()
            self.count += 1

    def payload(self):
        with self.lock:
            valid = self.values is not None and time.time() - self.received <= 5
            result = {'source': 'real', 'has_data': valid, 'sample_rate_hz': self.sample_rate,
                      'channels': [f'eeg_{i}' for i in range(1, 9)], 'sample_count': self.count,
                      'calibrated': False}
            if valid:
                result.update(eeg=list(self.values), timestamp=datetime.fromtimestamp(self.received, timezone.utc).isoformat())
            return result


class Handler(SimpleHTTPRequestHandler):
    store = None
    allowed_origin = None

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store')
        if self.allowed_origin and self.headers.get('Origin') == self.allowed_origin:
            self.send_header('Access-Control-Allow-Origin', self.allowed_origin)
            self.send_header('Vary', 'Origin')
        super().end_headers()

    def do_GET(self):
        if self.path.split('?')[0] == '/api/eeg/latest':
            data = json.dumps(self.store.payload(), allow_nan=False).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(data)))
            self.end_headers()
            self.wfile.write(data)
        else:
            super().do_GET()


def read_serial(reader_class, config, store):
    while True:
        reader = None
        try:
            reader = reader_class(**config)
            print('Serial device connected.', flush=True)
            for sample in reader.samples():
                store.update(sample)
        except Exception as error:
            print(f'Serial device unavailable: {error}. Retrying in 3 seconds.', flush=True)
            time.sleep(3)
        finally:
            if reader is not None:
                reader.close()


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument('--collector', type=Path, required=True, help='eeg-ecg-action-dataset-collector checkout')
    parser.add_argument('--port', help='Override configured serial port, e.g. COM3')
    parser.add_argument('--http-port', type=int, default=8765)
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--allow-origin', help='Exact hosted dashboard origin if using an HTTPS reverse proxy')
    args = parser.parse_args()
    import yaml
    collector = args.collector.resolve()
    with (collector / 'config.yaml').open(encoding='utf-8') as f:
        runtime = yaml.safe_load(f)['runtime']
    if runtime['source'] != 'serial12hex':
        raise ValueError('Only the actual serial12hex collector source is supported')
    config = dict(runtime['source_args'])
    if args.port:
        config['port'] = args.port
    if config['eeg_channels'] != 8 or config['ecg_channels'] != 4:
        raise ValueError('Expected collector protocol: 8 EEG + 4 ECG channels')
    spec = importlib.util.spec_from_file_location('collector_serial_reader', collector / 'serial_reader.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    store = LatestEEG(config['fs'])
    Handler.store = store
    Handler.allowed_origin = args.allow_origin
    thread = threading.Thread(target=read_serial, args=(module.Serial12HexReader, config, store), daemon=True)
    thread.start()
    root = Path(__file__).resolve().parents[1] / 'dist'
    server = ThreadingHTTPServer((args.host, args.http_port), partial(Handler, directory=str(root)))
    print(f'Dashboard: http://{args.host}:{args.http_port}/ ; EEG: /api/eeg/latest', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
