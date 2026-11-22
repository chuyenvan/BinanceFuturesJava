#!/usr/bin/env python3
"""ADD24 R-SIM converter (DEV-B). HO5 s123 artefacts -> rig inputs ("theo vet sim").
Replicates sim candidate stream: bins A3 2026 (score = 1 - p0, float32) forward-filled 15m -> every minute (stale <= 15 min),
sorted by sim quickSortByFloatPred (Lomuto, non-stable, exact port), top-K=24 (cap-then-skip: held still takes a rank).
p15 = pred_2026.bin (market predReturn15M per minute). Held (sim) from printDone intervals.
Outputs (dir --out): cand.csv.gz  (ts,symbol,score,rank,p15,held_sim,sim_entry) for [warm_lo, hi)
                     sel.csv.gz   (rig format ts,symbol,selectorScore,rank,gateValue,p15) for [lo, hi)
                     sim_entries.csv (sim cums with start in [lo,hi)), bigdown.csv (rig format), manifest_conv.json
No PnL is written or printed."""
import argparse, csv, gzip, hashlib, json, logging, os, struct, sys
from datetime import datetime, timezone, timedelta
import numpy as np
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s'); L = logging.getLogger('conv')
TZ7 = timezone(timedelta(hours=7))
MIN = 60000
TS_MAX = int(datetime(2026, 9, 30, 23, 59, tzinfo=TZ7).timestamp() * 1000)   # V3 hard limit (+07, strictest)
REC = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("p0", ">f4"), ("p1", ">f4"), ("p2", ">f4"), ("p3", ">f4")])
HO5 = '/home/ubuntu/claude_master/w3/ho5'
PD = HO5 + '/out/ho5-a3-l26-s123/storage/printDone.csv'
DS = HO5 + '/a3/data26/ds'
MAP = HO5 + '/mapper/ov_idtostr.tsv'
TOPK = 24

def d7(s):  # 'YYYY-MM-DD' or 'YYYYMMDD HH:MM' (+07) -> ms
    for f in ('%Y-%m-%d', '%Y%m%d %H:%M'):
        try: return int(datetime.strptime(s, f).replace(tzinfo=TZ7).timestamp() * 1000)
        except ValueError: pass
    raise ValueError(s)

def md5(p):
    h = hashlib.md5()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''): h.update(b)
    return h.hexdigest()

def sha256(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''): h.update(b)
    return h.hexdigest()

def qsort_sim(vals):
    """exact port of quickSortByFloatPred/partition (Lomuto, pivot=high, Float.compare<=0). returns permutation."""
    a = list(range(len(vals))); v = list(vals)
    st = [(0, len(a) - 1)]
    while st:
        lo, hi = st.pop()
        if lo >= hi: continue
        pv = v[a[hi]]; i = lo - 1
        for j in range(lo, hi):
            x = v[a[j]]
            if x <= pv:   # Float.compare(x,pv)<=0 ; NaN already dropped (s3_funding keep=~isnan)
                i += 1; a[i], a[j] = a[j], a[i]
        a[i + 1], a[hi] = a[hi], a[i + 1]
        p = i + 1
        st.append((p + 1, hi)); st.append((lo, p - 1))
    return a

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--warm_lo', required=True); ap.add_argument('--lo', required=True); ap.add_argument('--hi', required=True)
    ap.add_argument('--bins', nargs='+', required=True); ap.add_argument('--out', required=True)
    a = ap.parse_args()
    W0, LO, HI = d7(a.warm_lo), d7(a.lo), d7(a.hi)
    assert W0 < LO < HI <= TS_MAX + MIN, 'window'
    os.makedirs(a.out, exist_ok=True)
    idmap = {}
    for ln in open(MAP):
        p = ln.rstrip('\n').split('\t')
        if len(p) == 2 and p[0].lstrip('-').isdigit(): idmap[int(p[0])] = p[1]
    # bins -> 15m marks (file order kept = Java byTs list order: files sorted by name, records in file order)
    files = sorted(a.bins)
    tsl, syl, scl = [], [], []
    inputs = {}
    for f in files:
        r = np.fromfile(f, dtype=REC)
        inputs[os.path.basename(f)] = dict(md5=md5(f), sha256=sha256(f), n=int(len(r)), ts_min=int(r['ts'].min()), ts_max=int(r['ts'].max()))
        assert int(r['ts'].max()) <= TS_MAX, 'V3 bins ts > 2026-09-30 23:59 +07 -> ABORT'
        k = ~np.isnan(r['p0'])
        tsl.append(r['ts'][k].astype(np.int64)); syl.append(r['sym'][k].astype(np.int64))
        scl.append((np.float32(1.0) - r['p0'][k].astype(np.float32)).astype(np.float32))
    ts = np.concatenate(tsl); sy = np.concatenate(syl); sc = np.concatenate(scl)
    o = np.argsort(ts, kind='stable'); ts, sy, sc = ts[o], sy[o], sc[o]
    marks, starts = np.unique(ts, return_index=True); ends = np.append(starts[1:], len(ts))
    L.info('bins marks=%d recs=%d', len(marks), len(ts))
    # top-K per mark (sim sort)
    top = {}
    for m, s0, e0 in zip(marks, starts, ends):
        if m < W0 - 15 * MIN or m >= HI: continue
        perm = qsort_sim(sc[s0:e0].tolist())[:TOPK]
        top[int(m)] = [(int(sy[s0 + i]), float(sc[s0 + i])) for i in perm]
    # p15
    pp = DS + '/pred_2026.bin'
    raw = open(pp, 'rb').read(); n = struct.unpack('>i', raw[:4])[0]
    pr = np.frombuffer(raw[4:], dtype=np.dtype([('ts', '>i8'), ('p15', '>f4'), ('risk', '>f4')]), count=n)
    assert int(pr['ts'].max()) <= TS_MAX, 'V3 pred ts > limit -> ABORT'
    inputs['pred_2026.bin'] = dict(md5=md5(pp), sha256=sha256(pp), n=int(n), ts_min=int(pr['ts'].min()), ts_max=int(pr['ts'].max()))
    p15 = dict(zip(pr['ts'].astype(np.int64).tolist(), pr['p15'].astype(np.float32).tolist()))
    # printDone: held intervals + entries
    rows = list(csv.DictReader(open(PD)))
    inputs['printDone.csv'] = dict(md5=md5(PD), sha256=sha256(PD), n=len(rows))
    held = {}   # symbol -> list of (from, to)
    ent = {}    # (ts, symbol) -> level
    # printDone = 1 dong / LEG; cum = nhom (sym, end). Leg DCA cua cum co leg0 truoc LO => KHONG theo vet (rig khong co leg0), dem.
    leg0 = {}
    for r in rows:
        k = (r['sym'], r['end']); t = d7(r['start'])
        leg0[k] = min(leg0.get(k, t), t)
    excl_dca = []
    for r in rows:
        s = r['sym'] + 'USDT'; t0 = d7(r['start']); t1 = d7(r['end'])
        f0 = t0 + (MIN if r['level'] == 'PREDICT_SYMBOL_TRADE' else 0)
        held.setdefault(s, []).append((f0, t1))
        if LO <= t0 < HI:
            if r['level'] == 'DCA_LEVEL1' and leg0[(r['sym'], r['end'])] < LO: excl_dca.append((t0, s)); continue
            ent[(t0, s)] = r['level']
    def is_held(s, t):
        return any(a0 <= t < b0 for a0, b0 in held.get(s, ()))
    mk = np.array(sorted(top), dtype=np.int64)
    nmiss_p15 = nstale = 0; nsel = 0; ent_seen = set()
    with gzip.open(a.out + '/cand.csv.gz', 'wt') as fc, gzip.open(a.out + '/sel.csv.gz', 'wt') as fs:
        fc.write('ts,symbol,score,rank,p15,held_sim,sim_entry\n'); fs.write('ts,symbol,selectorScore,rank,gateValue,p15\n')
        for t in range(W0, HI, MIN):
            i = np.searchsorted(mk, t, side='right') - 1
            if i < 0 or t - mk[i] > 15 * MIN: nstale += 1; continue
            q = p15.get(t)
            if q is None: nmiss_p15 += 1; continue
            for rk, (sid, s_) in enumerate(top[int(mk[i])], 1):
                s = idmap.get(sid, 'ID%d' % sid)
                h = 1 if is_held(s, t) else 0
                e = 1 if (t, s) in ent else 0
                if e: ent_seen.add((t, s))
                fc.write('%d,%s,%.9g,%d,%.9g,%d,%d\n' % (t, s, s_, rk, q, h, e))
                if t >= LO:
                    fs.write('%d,%s,%.9g,%d,%.9g,%.9g\n' % (t, s, s_, rk, s_, q)); nsel += 1
    pred_ent = {k: v for k, v in ent.items() if v == 'PREDICT_SYMBOL_TRADE'}
    miss = sorted(k for k in pred_ent if k not in ent_seen)
    with open(a.out + '/sim_entries.csv', 'w') as f:
        f.write('ts,symbol,level,in_top24\n')
        for (t, s), lv in sorted(ent.items()): f.write('%d,%s,%s,%d\n' % (t, s, lv, 1 if (t, s) in ent_seen else 0))
    with open(a.out + '/bigdown.csv', 'w') as f:
        f.write('ts,symbol,entry,qty,level\n')
        for (t, s), lv in sorted(ent.items()):
            if lv == 'BIG_DOWN': f.write('%d,%s,,,BIG_DOWN\n' % (t, s))
    man = dict(window=[a.lo, a.hi], warm_lo=a.warm_lo, W0=W0, LO=LO, HI=HI, TS_MAX=TS_MAX, inputs=inputs, topk=TOPK,
               sel_rows=nsel, minutes_stale_or_nomark=nstale, minutes_no_p15=nmiss_p15,
               sim_entries=len(ent), sim_predict_entries=len(pred_ent), excluded_dca_legs_leg0_before_window=[list(x) for x in excl_dca], predict_entries_not_in_top24=[list(x) for x in miss],
               note='score=1-p0 float32; ffill stale<=15m; sort=port quickSortByFloatPred; held from printDone (PREDICT: start+1m; BIG_DOWN: start) to end (excl)')
    json.dump(man, open(a.out + '/manifest_conv.json', 'w'), indent=1)
    L.info('done sel_rows=%d stale=%d nop15=%d entries=%d predict=%d predict_not_in_top24=%d', nsel, nstale, nmiss_p15,
           len(ent), len(pred_ent), len(miss))

if __name__ == '__main__':
    main()
