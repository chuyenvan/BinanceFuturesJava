#!/usr/bin/env python3
"""seed_build.py (PREREG_PARITY_V12_DRY ADD3 299f00b0 + ADD4 feb32107): seed = A (dump sim, ts < T_cut) U C (live sach, ts >= T_cut).
C: gate_ratio_live.bin ghep sel_dump theo (ts, r float32); bo TRADFI/INDEX (exchangeInfo) + coin giu so giay (ShadowBookC3);
chi ngay (+07) ghep 100 %. Usage: seed_build.py --live DIR --tcut-ms T [--a A.bin] --exinfo F --out DIR [--label-only]"""
import argparse, glob, gzip, io, json, re, struct, zlib, hashlib, datetime as dt, os, sys
import numpy as np, pandas as pd, snappy
f32 = np.float32; H = 3600000


def load_grr(p):
    b = open(p, 'rb').read(); i = 0; T = []; R = []; bad = 0
    while i + 12 <= len(b):
        mg, ln, crc = struct.unpack('>iiI', b[i:i + 12])
        if mg != 0x47525231 or ln < 0 or i + 12 + ln > len(b): bad += 1; i += 1; continue
        c = b[i + 12:i + 12 + ln]
        if zlib.crc32(c) & 0xffffffff != crc: bad += 1; i += 1; continue
        a = np.frombuffer(snappy.uncompress(c), dtype=np.dtype([('t', '>i8'), ('r', '>f4')]))
        T.append(a['t'].astype(np.int64)); R.append(a['r'].astype(f32)); i += 12 + ln
    return (np.concatenate(T) if T else np.zeros(0, np.int64)), (np.concatenate(R) if R else np.zeros(0, f32)), bad


def write_grr(path, ts, r):
    raw = np.empty(len(ts), dtype=np.dtype([('t', '>i8'), ('r', '>f4')])); raw['t'] = ts; raw['r'] = r
    comp = snappy.compress(raw.tobytes())
    with open(path, 'wb') as f:
        f.write(struct.pack('>iiI', 0x47525231, len(comp), zlib.crc32(comp) & 0xffffffff)); f.write(comp)
    t2, r2, bad = load_grr(path)
    assert bad == 0 and np.array_equal(t2, ts) and np.array_equal(r2, r), 'reload mismatch'
    return hashlib.md5(open(path, 'rb').read()).hexdigest()


def ratio(p15, sp):
    fac = np.maximum(f32(0.26787), (sp.astype(f32) / f32(0.15)) * f32(1.2876)).astype(f32)
    return (p15.astype(f32) / (fac * f32(1.55))).astype(f32)


def kind(ct, ut):
    c = (ct or '').strip().upper(); u = (ut or '').strip().upper()
    if 'TRADIFI' in c or 'TRADFI' in c or u in ('EQUITY', 'HK_EQUITY', 'KR_EQUITY', 'CN_EQUITY', 'COMMODITY', 'FX'): return 'TRADFI'
    if u == 'INDEX': return 'INDEX'
    return 'UNCLASSIFIED' if u == '' else 'CRYPTO'


def rd(f):
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


def label_live(live, exinfo):
    ts, r, bad = load_grr(live + '/gate_ratio_live.bin')
    L = [x for x in (rd(f) for f in sorted(glob.glob(live + '/sel/sel_dump_*.csv.gz'))) if x is not None]
    S = pd.concat(L, ignore_index=True).drop_duplicates(['ts', 'symbol', 'rank'])
    S['r'] = ratio(S.p15.values, S.gateValue.values)
    B = pd.DataFrame(dict(ts=ts, r=r)); B['k'] = B.groupby(['ts', 'r']).cumcount()
    S['k'] = S.groupby(['ts', 'r']).cumcount()
    M = B.merge(S[['ts', 'r', 'k', 'symbol', 'rank', 'gateValue', 'p15']], on=['ts', 'r', 'k'], how='left')
    ei = json.load(gzip.open(exinfo) if exinfo.endswith('.gz') else open(exinfo))
    cls = {s['symbol']: kind(s.get('contractType'), s.get('underlyingType')) for s in ei['symbols']}
    M['kind'] = [cls.get(s, 'NOT_IN_SNAPSHOT') if isinstance(s, str) else 'UNMATCHED' for s in M.symbol]
    ev = []
    for ln in open(live + '/shadow_events_all.txt'):
        m = re.match(r'(\d\d/\d\d/\d{4} \d\d:\d\d:\d\d)\.(\d+)\s+(open|closed) (\S+)', ln)
        if m:
            t = int((dt.datetime.strptime(m.group(1), '%d/%m/%Y %H:%M:%S') - dt.datetime(1970, 1, 1)).total_seconds() * 1000) - 7 * H
            ev.append((t, m.group(3), m.group(4)))
    iv, op = {}, {}
    for t, k, s in sorted(ev):
        if k == 'open' and s not in op: op[s] = t
        elif k == 'closed' and s in op: iv.setdefault(s, []).append((op.pop(s), t))
    for s, t in op.items(): iv.setdefault(s, []).append((t, 1 << 62))
    held = np.zeros(len(M), bool); sym = M.symbol.values; tt = M.ts.values + 63000
    for s, lst in iv.items():
        idx = np.nonzero(sym == s)[0]
        for a, b in lst: held[idx[(tt[idx] > a) & (tt[idx] < b)]] = True
    M['held'] = held
    M['day'] = pd.to_datetime(M.ts + 7 * H, unit='ms').dt.strftime('%Y-%m-%d')
    full = M.groupby('day').symbol.apply(lambda s: bool(s.notna().all()))
    M['day_full'] = M.day.map(full)
    M['clean'] = M.day_full & ~M.kind.isin(['TRADFI', 'INDEX']) & ~M.held
    return M, bad


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--live', required=True); ap.add_argument('--tcut-ms', type=int, required=True)
    ap.add_argument('--a'); ap.add_argument('--exinfo', required=True); ap.add_argument('--out', required=True)
    ap.add_argument('--label-only', action='store_true')
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    M, badL = label_live(a.live, a.exinfo)
    M.to_parquet(a.out + '/live_labeled.parquet')
    rep = dict(live_bad_chunks=badL, live_n=len(M), tcut_ms=a.tcut_ms,
               days={d: dict(n=int(g.size), full=bool(g.day_full.iloc[0]), clean=int(g.clean.sum())) for d, g in M.groupby('day')})
    if not a.label_only:
        C = M[(M.ts >= a.tcut_ms) & M.clean]
        if a.a:
            ta, ra, badA = load_grr(a.a); keep = ta < a.tcut_ms; ta, ra = ta[keep], ra[keep]
        else:
            ta, ra, badA = np.zeros(0, np.int64), np.zeros(0, f32), 0
        ts = np.concatenate([ta, C.ts.values.astype(np.int64)]); rr = np.concatenate([ra, C.r.values.astype(f32)])
        o = np.argsort(ts, kind='stable'); ts, rr = ts[o], rr[o]
        name = 'seed_%s.bin' % pd.Timestamp(int(ts[-1]) + 7 * H, unit='ms').strftime('%Y%m%d_%H%M') if len(ts) else 'seed_empty.bin'
        rep.update(A_n=int(len(ta)), A_bad=badA, C_n=int(len(C)), seed_n=int(len(ts)), seed_file=name,
                   seed_md5=write_grr(a.out + '/' + name, ts, rr),
                   C_days_dropped=sorted(d for d, v in rep['days'].items() if not v['full'] and d >= pd.Timestamp(a.tcut_ms + 7 * H, unit='ms').strftime('%Y-%m-%d')))
    json.dump(rep, open(a.out + '/seed_manifest.json', 'w'), indent=1)
    print(json.dumps({k: v for k, v in rep.items() if k != 'days'}, indent=1))
