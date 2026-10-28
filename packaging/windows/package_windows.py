"""Package a completed Windows build with its instructions and checksum."""
import hashlib
from pathlib import Path
import shutil
from zipfile import ZipFile, ZIP_DEFLATED

root = Path(__file__).resolve().parents[2]
output = root / 'dist' / 'windows-x86_64'
binary = output / 'GitDesk.exe'
if not binary.is_file() or binary.read_bytes()[:2] != b'MZ':
    raise SystemExit('Build the real Windows executable before packaging.')
shutil.copy2(root / 'packaging/windows/README.md', output / 'README.md')
(output / 'SHA256SUMS').write_text(hashlib.sha256(binary.read_bytes()).hexdigest() + '  GitDesk.exe\n')
archive_path = root / 'dist' / 'GitDesk-Windows-x86_64.zip'
with ZipFile(archive_path, 'w', ZIP_DEFLATED) as archive:
    for name in ['GitDesk.exe', 'README.md', 'SHA256SUMS']:
        archive.write(output / name, name)
print(archive_path)
