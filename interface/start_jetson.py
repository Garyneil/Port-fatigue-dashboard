"""One-command launcher for the Jetson serial EEG dashboard."""
import argparse
import os
from pathlib import Path
import subprocess
import sys


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--collector', type=Path, default=root.parent / 'eeg-ecg-action-dataset-collector')
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--http-port', type=int, default=8765)
    parser.add_argument('--channel-names', help='Eight verified electrode names in serial order')
    args = parser.parse_args()
    collector = args.collector.expanduser().resolve()
    for name in ('config.yaml', 'serial_reader.py'):
        if not (collector / name).is_file():
            parser.error('Missing %s in %s; use --collector to select the collector project.' % (name, collector))
    python = root / '.venv' / 'bin' / 'python'
    if not python.is_file():
        python = Path(sys.executable)
    check = subprocess.run([str(python), '-c', 'import yaml, serial'], capture_output=True, text=True)
    if check.returncode:
        parser.error('Dependencies missing. Run: %s -m pip install -r %s' % (python, root / 'interface' / 'requirements.txt'))
    command = [str(python), '-u', str(root / 'interface' / 'eeg_bridge.py'), '--collector', str(collector),
               '--host', args.host, '--http-port', str(args.http_port)]
    if args.channel_names:
        command += ['--channel-names', args.channel_names]
    print('Collector: %s' % collector, flush=True)
    print('Serial settings: collector config.yaml (no configuration files changed).', flush=True)
    print('Open on Jetson: http://127.0.0.1:%s/' % args.http_port, flush=True)
    print('Keep simulation OFF. Stop other programs using the serial port. Ctrl+C stops the bridge.', flush=True)
    try:
        os.execv(str(python), command)
    except OSError as error:
        parser.error(str(error))


if __name__ == '__main__':
    main()
