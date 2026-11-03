"""Verify the source files shipped in this security update."""
from pathlib import Path
import hashlib
import json

root = Path(__file__).resolve().parents[1]
manifest = json.loads((root / 'deploy/a3-security-manifest.json').read_text())
for name, expected in manifest['files'].items():
    path = root / name
    if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise SystemExit(f'FAIL: source mismatch: {name}')
print(f"PASS: verified {len(manifest['files'])} security update files.")
