#!/usr/bin/env python3
"""PARITY_V12_DRY ADD2 (bb9571fb) — nguon (B) live lam sach + M3 TradFi. Chi doc file da keo ve Oracle."""
import sys, glob, gzip, json, re, struct, zlib, hashlib, datetime as dt
import numpy as np, pandas as pd, snappy
sys.path.insert(0, '/home/ubuntu/claude_master/1016/grr')
import grr_lib as G
W = '/home/ubuntu/claude_master/gst1030/'
H = 3600000; DAY = 86400000
PCT = float(np.float32(0.999950829))
f32 = np.float32


def ratio(p15, sp):
    fac = np.maximum(f32(0.26787), (sp.astype(f32) / f32(0.15)) * f32(1.2876)).astype(f32)
    return (p15.astype(f32) / (fac * f32(1.55))).astype(f32)


def classify(ct, ut):
    c = (ct or '').strip().upper(); u = (ut or '').strip().upper()
    if 'TRADIFI' in c or 'TRADFI' in c: return 'TRADFI'
    if u in ('EQUITY', 'HK_EQUITY', 'KR_EQUITY', 'CN_EQUITY', 'COMMODITY', 'FX'): return 'TRADFI'
    if u == 'INDEX': return 'INDEX'
    if u == '': return 'UNCLASSIFIED'
    return 'CRYPTO'


def write_grr(path, ts, r):
    raw = np.empty(len(ts), dtype=np.dtype([('t', '>i8'), ('r', '>f4')]))
    raw['t'] = ts; raw['r'] = r
    comp = snappy.compress(raw.tobytes())
    with open(path, 'wb') as f:
        f.write(struct.pack('>iiI', 0x47525231, len(comp), zlib.crc32(comp) & 0xffffffff)); f.write(comp)
    t2, r2, bad = G.load(path)
    assert bad == 0 and np.array_equal(t2, ts) and np.array_equal(r2.astype(f32), r), 'reload mismatch'
    return hashlib.md5(open(path, 'rb').read()).hexdigest()


def qhours(ts, r, hours):
    out = []
    for h in hours:
        a = r[(ts >= h - 90 * DAY) & (ts < h)]
        m = len(a)
        if m == 0: out.append(np.nan); continue
        k = min(m - 1, max(0, int(np.floor(PCT * (m - 1)))))
        out.append(float(np.partition(a, k)[k]))
    return np.array(out)


ts, r, bad = G.load(W + 'gate_ratio_live_2242.bin'); r = r.astype(f32)
def rd(f):
    import io
    b = b''
    try:
        with gzip.open(f) as g:
            while True:
                c = g.read(1 << 20)
                if not c: break
                b += c
    except EOFError:
        b = b[:b.rfind(b'\n') + 1]
    return pd.read_csv(io.BytesIO(b)) if b.count(b'\n') > 1 else None
_L = [rd(f) for f in sorted(glob.glob(W + 'live/sel/sel_dump_*.csv.gz'))]
print('sel files', len(_L), 'none', sum(x is None for x in _L))
S = pd.concat([x for x in _L if x is not None], ignore_index=True)
S = S.drop_duplicates(['ts', 'symbol', 'rank'])
S['r'] = ratio(S.p15.values, S.gateValue.values)
# ghep (ts, r) multiset
B = pd.DataFrame(dict(ts=ts, r=r)); B['k'] = B.groupby(['ts', 'r']).cumcount()
S['k'] = S.groupby(['ts', 'r']).cumcount()
M = B.merge(S[['ts', 'r', 'k', 'symbol', 'rank']], on=['ts', 'r', 'k'], how='left')
inS = (M.ts >= S.ts.min()) & (M.ts <= S.ts.max())
match_rate = float(M.symbol[inS].notna().mean())
# exchangeInfo
ei = json.load(gzip.open('/home/ubuntu/claude_master/v12/fixtures/exchangeInfo_20261027_1140.json.gz'))
cls = {s['symbol']: classify(s.get('contractType'), s.get('underlyingType')) for s in ei['symbols']}
M['kind'] = M.symbol.map(lambda s: cls.get(s, 'NOT_IN_SNAPSHOT') if isinstance(s, str) else 'UNMATCHED')
# held so giay
ev = []
for ln in open(W + 'live/shadow_events_all.txt'):
    m = re.match(r'(\d\d/\d\d/\d{4} \d\d:\d\d:\d\d)\.(\d+)\s+(open|closed) (\S+)', ln)
    if m:
        t = int((dt.datetime.strptime(m.group(1), '%d/%m/%Y %H:%M:%S') - dt.datetime(1970, 1, 1)).total_seconds() * 1000) - 7 * H
        ev.append((t, m.group(3), m.group(4)))
iv = {}
op = {}
for t, k, s in sorted(ev):
    if k == 'open' and s not in op: op[s] = t
    elif k == 'closed' and s in op: iv.setdefault(s, []).append((op.pop(s), t))
for s, t in op.items(): iv.setdefault(s, []).append((t, 1 << 62))
held = np.zeros(len(M), bool)
sym = M.symbol.values; tt = M.ts.values + 63000
for s, lst in iv.items():
    idx = np.nonzero(sym == s)[0]
    for a, b in lst:
        held[idx[(tt[idx] > a) & (tt[idx] < b)]] = True
M['held'] = held
excl = M.kind.isin(['TRADFI', 'INDEX'])
res = dict(n=len(M), match_rate_in_seldump=round(match_rate, 5), n_unmatched=int(M.symbol.isna().sum()),
           first_sel_ts=int(S.ts.min()), kinds=M.kind.value_counts().to_dict(),
           tf_share=round(float((M.kind == 'TRADFI').mean()), 4), index_share=round(float((M.kind == 'INDEX').mean()), 4),
           held_share=round(float(M.held.mean()), 4), held_and_excl=int((M.held & excl).sum()))
# q tung gio 10-30 + toan cua so
h30 = int((dt.datetime(2026, 10, 30) - dt.datetime(1970, 1, 1)).total_seconds() * 1000) - 7 * H
hrs = [h30 + i * H for i in range(0, 22)]
keepA = ~excl.values; keepB = keepA & ~M.held.values
qa = qhours(M.ts.values, M.r.values, hrs); qb = qhours(M.ts.values[keepA], M.r.values[keepA], hrs)
qc = qhours(M.ts.values[keepB], M.r.values[keepB], hrs)
res['q_1030'] = {pd.Timestamp(h + 7 * H, unit='ms').strftime('%H'): [round(a, 6), round(b, 6), round(c, 6)] for h, a, b, c in zip(hrs, qa, qb, qc)}
hall = list(range((int(ts.min()) // H + 1 + 7 * 24) * H, (int(ts.max()) // H + 1) * H, H))
QA = qhours(M.ts.values, M.r.values, hall); QB = qhours(M.ts.values[keepA], M.r.values[keepA], hall)
QC = qhours(M.ts.values[keepB], M.r.values[keepB], hall)
res['q_rel_noTF_vs_raw'] = dict(med=round(float(np.median(QB / QA - 1)), 4), min=round(float(np.min(QB / QA - 1)), 4), max=round(float(np.max(QB / QA - 1)), 4))
res['q_rel_noTFheld_vs_raw'] = dict(med=round(float(np.median(QC / QA - 1)), 4), min=round(float(np.min(QC / QA - 1)), 4), max=round(float(np.max(QC / QA - 1)), 4))
import os; os.makedirs(W + 'seed', exist_ok=True)
tb = M.ts.values[keepB].astype(np.int64); rb = M.r.values[keepB].astype(f32)
res['B_n'] = int(len(tb)); res['B_md5'] = write_grr(W + 'seed/B_live_clean_20261001_20261030.bin', tb, rb)
res['B_range'] = [pd.Timestamp(int(tb[0]) + 7 * H, unit='ms').isoformat(), pd.Timestamp(int(tb[-1]) + 7 * H, unit='ms').isoformat()]
M[['ts', 'r', 'symbol', 'rank', 'kind', 'held']].to_parquet(W + 'live/buffer_labeled.parquet')
json.dump(res, open(W + 'seed/B_report.json', 'w'), indent=1, default=str)
print(json.dumps(res, indent=1, default=str))
