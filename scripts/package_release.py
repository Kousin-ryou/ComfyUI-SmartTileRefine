"""Build an installable node ZIP and SHA-256 checksum without local artifacts."""
import hashlib
from pathlib import Path
import re
import zipfile

ROOT = Path(__file__).resolve().parents[1]
VERSION = re.search(r'^version\s*=\s*"([^"]+)"', (ROOT / 'pyproject.toml').read_text(encoding='utf-8'), re.M)[1]
ROOT_FILES = ('__init__.py', 'nodes.py', 'geometry.py', 'image_ops.py', 'pyproject.toml',
              'requirements.txt', 'README.md', 'README.en.md', 'LICENSE', 'THIRD_PARTY_NOTICES.md', 'CHANGELOG.md')
FOLDERS = ('web', 'locales', 'examples', 'docs')


def build():
    files = [ROOT / name for name in ROOT_FILES]
    for folder in FOLDERS:
        files.extend(p for p in (ROOT / folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    paths = {p.relative_to(ROOT).as_posix() for p in files}
    for required in ('web/smart_tile_final.js', 'locales/zh/nodeDefs.json', 'docs/usage.md'):
        if required not in paths:
            raise RuntimeError('Missing release file: ' + required)
    for path in files:
        if path.suffix.lower() in ('.md', '.py', '.js', '.json', '.toml', '.txt'):
            text = path.read_text(encoding='utf-8')
            if re.search(r'(?:E|F):\\(?:Comfyuiai|sucaiku)', text):
                raise RuntimeError('Local machine path in release: ' + str(path))
    target = ROOT / 'dist'
    target.mkdir(exist_ok=True)
    archive = target / f'ComfyUI-SmartTileRefine-v{VERSION}.zip'
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as stream:
        for path in sorted(files):
            info = zipfile.ZipInfo('ComfyUI-SmartTileRefine/' + path.relative_to(ROOT).as_posix(), (2026, 11, 11, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            stream.writestr(info, path.read_bytes())
    checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
    (target / 'SHA256SUMS.txt').write_text(f'{checksum}  {archive.name}\n', encoding='ascii')
    print(f'{archive.name}: {len(files)} files, {archive.stat().st_size} bytes, sha256 {checksum}')
    return archive


if __name__ == '__main__':
    build()
