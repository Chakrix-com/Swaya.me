#!/usr/bin/env python3
import json, os, hashlib
from pathlib import Path

ROOT=Path('/home/vinay/Swaya.me')
OUT=ROOT/'frontend/public/assets/help-screens'
manifest=json.loads((ROOT/'scripts/help_screenshot_manifest.json').read_text(encoding='utf-8'))
langs=manifest['languages']; themes=manifest['themes']; files=[f['name'] for f in manifest['files']]

missing=[]
for l in langs:
  for t in themes:
    for f in files:
      p=OUT/l/t/f
      if not p.exists() or p.stat().st_size < 5000:
        missing.append(str(p))

if missing:
  print('FAIL missing/too-small assets:', len(missing))
  for p in missing[:20]: print(' ',p)
  raise SystemExit(1)

# ensure per-language home differs (sanity language check)
for t in themes:
  hashes=[]
  for l in langs:
    p=OUT/l/t/'home.png'
    hashes.append(hashlib.sha1(p.read_bytes()).hexdigest()[:12])
  uniq=len(set(hashes))
  print(f'{t}: unique home variants {uniq}/{len(langs)}')
  if uniq < len(langs)-1:
    raise SystemExit(f'FAIL low language variance on {t}')

print('PASS asset file checks')
