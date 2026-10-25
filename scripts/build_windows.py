"""Build and verify a portable Windows x64 release, including all runtime assets."""
import hashlib
import importlib.metadata
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'interface'))
from demo_app import VERSION


def main():
    if sys.platform != 'win32':
        raise SystemExit('Build this Windows application on Windows.')
    output = ROOT / 'release' / f'v{VERSION}'
    output.mkdir(parents=True, exist_ok=True)
    name = 'PortFatigueDemo'
    subprocess.run([sys.executable, '-m', 'PyInstaller', '--noconfirm', '--clean',
        '--windowed', '--onedir', '--name', name,
        '--distpath', str(output), '--workpath', str(ROOT / 'build' / 'pyinstaller'),
        '--specpath', str(ROOT / 'build'),
        '--paths', str(ROOT / 'interface'),
        '--add-data', f'{ROOT / "dist"};dist',
        '--add-data', f'{ROOT / "interface" / "models"};models',
        str(ROOT / 'interface' / 'demo_app.py')], check=True, cwd=ROOT)
    bundle = output / name
    shutil.copy2(ROOT / 'DEMO_GUIDE.md', bundle / '使用说明.md')
    licenses = bundle / 'licenses'
    licenses.mkdir(exist_ok=True)
    for package in ('numpy', 'scipy', 'pyserial', 'pyinstaller'):
        distribution = importlib.metadata.distribution(package)
        for item in distribution.files or []:
            if any(part.lower().startswith(('license', 'copying')) for part in item.parts):
                source = Path(distribution.locate_file(item))
                if source.is_file():
                    target = licenses / package / Path(*item.parts[1:])
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, target)
    result_file = bundle / 'package-self-test.json'
    subprocess.run([str(bundle / f'{name}.exe'), '--self-test', str(result_file)], check=True, timeout=90)
    result = json.loads(result_file.read_text(encoding='utf-8'))
    if not result.get('passed'):
        raise SystemExit(f'Packaged application failed self-test: {result}')
    archive_name = f'{name}-Windows-x64-v{VERSION}'
    archive = Path(shutil.make_archive(str(output / archive_name), 'zip', output, name))
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    (output / f'{archive_name}.sha256').write_text(f'{digest}  {archive.name}\n', encoding='ascii')
    print(json.dumps({'archive':str(archive), 'bytes':archive.stat().st_size, 'sha256':digest,
        'self_test':result}, indent=2))


if __name__ == '__main__':
    main()
