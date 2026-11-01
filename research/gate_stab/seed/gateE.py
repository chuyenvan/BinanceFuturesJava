#!/usr/bin/env python3
"""Cong E (ADD5 5ffb3402): daily noi == monthly tung byte, 2026-09, 5 symbol."""
import io, json, zipfile, urllib.request, hashlib, calendar
U = 'https://data.binance.vision/data/futures/um/'
SYMS = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'PARTIUSDT', 'BLESSUSDT']


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'gst/1'}), timeout=120) as r:
        return r.read()


def lines(zb):
    z = zipfile.ZipFile(io.BytesIO(zb)); t = z.read(z.namelist()[0])
    ls = t.splitlines(keepends=True)
    hdr = bool(ls) and ls[0][:1].isalpha()
    body = ls[1:] if hdr else ls
    if body and not body[-1].endswith(b'\n'): body[-1] = body[-1] + b'\n'   # chuan hoa dong cuoi
    return hdr, body


res = {}
for s in SYMS:
    hm, bm = lines(get(U + 'monthly/klines/%s/1m/%s-1m-2026-09.zip' % (s, s)))
    bd, hd_all = [], []
    for d in range(1, calendar.monthrange(2026, 9)[1] + 1):
        hd, b = lines(get(U + 'daily/klines/%s/1m/%s-1m-2026-09-%02d.zip' % (s, s, d)))
        hd_all.append(hd); bd += b
    M, D = b''.join(bm), b''.join(bd)
    res[s] = dict(equal=M == D, n_month=len(bm), n_daily=len(bd), md5_m=hashlib.md5(M).hexdigest(), md5_d=hashlib.md5(D).hexdigest(),
                  hdr_month=hm, hdr_daily=sorted(set(hd_all)))
    if M != D:
        i = next((k for k, (x, y) in enumerate(zip(bm, bd)) if x != y), None)
        res[s]['first_diff'] = [i, bm[i].decode()[:120] if i is not None else None, bd[i].decode()[:120] if i is not None else None]
    print(s, res[s], flush=True)
res['PASS'] = all(v['equal'] for k, v in res.items() if k in SYMS)
json.dump(res, open('/home/ubuntu/claude_master/gst1030/seed/gateE.json', 'w'), indent=1)
print('GATE_E_PASS', res['PASS'])
