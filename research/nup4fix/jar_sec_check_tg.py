#!/usr/bin/env python3
"""Bo sung cho research/nup3/jar_sec_check.py: tim token Telegram (\\d{8,10}:[A-Za-z0-9_-]{35}) trong MOI class
com/binance/** va MOI resource text cua jar. Khong in gia tri, chi ten entry + sha256[:10]. Exit 1 neu co."""
import hashlib, json, re, sys, zipfile
TG = re.compile(rb'(?<![0-9])[0-9]{8,10}:[A-Za-z0-9_-]{35}(?![A-Za-z0-9_-])')
TXT = ('.properties', '.xml', '.json', '.yml', '.yaml', '.conf', '.txt', '.cfg', '.env', '.sh', '.py', '.md')
def scan(j):
    z = zipfile.ZipFile(j); hits = []
    for n in z.namelist():
        if n.endswith('.class'):
            if not n.startswith('com/binance/'): continue
        elif not n.lower().endswith(TXT):
            continue
        for m in TG.finditer(z.read(n)):
            hits.append((n, hashlib.sha256(m.group(0)).hexdigest()[:10]))
    return hits
res = {}
for j in sys.argv[1:]:
    h = scan(j); res[j] = dict(ok=not h, n_hits=len(h), hits=h)
print(json.dumps(res, indent=1))
sys.exit(0 if all(v['ok'] for v in res.values()) else 1)
