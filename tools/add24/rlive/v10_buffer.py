#!/usr/bin/env python3
"""ADD24 cong V10 (ERRATA3 A4 + ERRATA4 C3). So (ts, r) rig nap vao buffer gate voi buffer live (file gate_ratio_live cua lan pull SAU cua so).
V10a (truot => HUY): mien = phut ma rig va live co CUNG tap dang giu (giao voi ung vien phut do) VA cung trang thai so day, HOAC phut truoc
  lech L-E dau tien: multiset r (bit float32) phai TRUNG va lech dem = 0.
V10b (bao cao): phut lech dem NGOAI mien V10a -> outside_domain_mismatch_minutes; rlive_score.py --v10 xet thuoc cum lech co nhan, con lai =
  lech L-N KHONG GIAI THICH. Chi dem / so bit - khong in gia tri r.
Dang giu live phut m = cum live co leg 0 SUBMIT truoc m+60 s va chua dong (dong dong cum) tai m+60 s (gate phut m chay o giay ~6 phut sau).
So day live = tong notional leg mo / cap >= U_MAX (xap xi; rig: co bookfull trong trace_dec).
usage: v10_buffer.py --rig <lane dir> --live <parse dir> --live-buffer <pull>/run/gate_ratio_live.bin.gz --start --end --cap --out V10.json
"""
import argparse, csv, gzip, json, os, shutil, sys, tempfile
from collections import defaultdict
from datetime import datetime, timedelta, timezone
import numpy as np

sys.path.insert(0, os.path.expanduser('~/claude_master/1016/grr'))
import grr_lib  # noqa: E402
TZ7 = timezone(timedelta(hours=7)); MIN = 60000


def ms7(s):
    return int(datetime.strptime(s, '%Y-%m-%d %H:%M').replace(tzinfo=TZ7).timestamp() * 1000)


def bits(x):
    return int(np.array([x], dtype=np.float32).view(np.int32)[0])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--rig', required=True); ap.add_argument('--live', required=True); ap.add_argument('--live-buffer', required=True)
    ap.add_argument('--start', required=True); ap.add_argument('--end', required=True); ap.add_argument('--cap', type=float, default=1000.0)
    ap.add_argument('--u-max', type=float, default=0.6); ap.add_argument('--out', required=True)
    a = ap.parse_args()
    S, E = ms7(a.start), ms7(a.end)
    rig = defaultdict(list)
    for x in csv.DictReader(gzip.open(a.rig + '/appended.csv.gz', 'rt')):
        t = int(x['ts'])
        if S <= t < E:
            rig[t].append(int(x['r_bits']))
    d = tempfile.mkdtemp(dir='/dev/shm/add24')
    try:
        p = os.path.join(d, 'b.bin')
        with gzip.open(a.live_buffer, 'rb') as fi, open(p, 'wb') as fo:
            shutil.copyfileobj(fi, fo)
        ts, r, bad = grr_lib.load(p)
    finally:
        shutil.rmtree(d)
    live = defaultdict(list)
    m = (ts >= S) & (ts < E)
    for t, v in zip(ts[m], r[m]):
        live[int(t)].append(bits(v))
    # trang thai rig theo phut (trace_dec): ung vien, dang giu, so day
    cand, rheld, rfull = defaultdict(set), defaultdict(set), {}
    for x in csv.DictReader(gzip.open(a.rig + '/trace_dec.csv.gz', 'rt')):
        t = int(x['ts'])
        if not (S <= t < E):
            continue
        cand[t].add(x['symbol'])
        if x['held'] == '1':
            rheld[t].add(x['symbol'])
        rfull[t] = rfull.get(t, False) or x['bookfull'] == '1'
    # cum live
    sub = [x for x in csv.DictReader(open(a.live + '/submit.csv')) if x['outcome'] == 'SUBMITTED']
    closes = sorted((int(x['log_ms']), x['symbol']) for x in csv.DictReader(open(a.live + '/book_close.csv'))) if os.path.exists(a.live + '/book_close.csv') else []
    cl, openc = [], {}
    for t_, kind, x in sorted([(int(x['log_ms']), 0, x) for x in sub] + [(c[0], 1, c) for c in closes], key=lambda z: (z[0], z[1])):
        if kind == 0:
            c = openc.get(x['symbol'])
            if c is None:
                c = {'symbol': x['symbol'], 't0': t_, 'tc': None, 'legs': []}; openc[x['symbol']] = c; cl.append(c)
            c['legs'].append((t_, float(x['notional'] or 0)))
        else:
            c = openc.pop(x[1], None)
            if c:
                c['tc'] = x[0]
    # lech L-E dau tien (khoa (dts, symbol, level, legIdx))
    gp = os.path.join(a.live, 'gate.csv')
    lfull_g = {(int(x['log_ms']) // MIN - 1) * MIN for x in csv.DictReader(open(gp)) if x.get('n_skipfull') and int(x['n_skipfull']) > 0} if os.path.exists(gp) else None
    lk = {(int(x['cid'].split('-')[-2]) * MIN, x['symbol'], x['level'], int(x['legIdx'] or x['cid'].split('-')[-1])) for x in sub}
    rk = {(int(x['decision_ts']), x['symbol'], x['level'], int(x['leg_idx'])) for x in csv.DictReader(open(a.rig + '/legs.csv')) if x['outcome'] == 'SUBMITTED'}
    dif = [k[0] for k in lk ^ rk if S <= k[0] < E]
    first_dev = min(dif) if dif else E
    dom, in_bad, out_bad, n_dom = [], 0, [], 0
    diag = []
    for t in sorted(set(live) | set(rig) | set(cand)):
        tg = t + MIN
        lheld = {c['symbol'] for c in cl if c['t0'] < tg and (c['tc'] is None or c['tc'] > tg)}
        lfull = sum(n for c in cl if c['t0'] < tg and (c['tc'] is None or c['tc'] > tg) for (tt, n) in c['legs'] if tt < tg) / a.cap >= a.u_max
        if lfull_g is not None:
            lfull = t in lfull_g          # [ERRATA5 D1] so day = SO GIAY theo dong [GATE] n_skipfull > 0
        same = (lheld & cand.get(t, set())) == rheld.get(t, set()) and lfull == rfull.get(t, False)
        A_, B_ = sorted(live.get(t, [])), sorted(rig.get(t, []))
        if t < first_dev or same:
            n_dom += 1
            if A_ != B_:
                in_bad += 1; dom.append(t)
                # chan doan (ERRATA5 B(ii)): tap r lech theo phut (bit), trang thai giu / so day hai ben - khong gia / kich thuoc lenh
                diag.append({'ts': t, 'n_live': len(A_), 'n_rig': len(B_), 'r_bits_chi_live': sorted(set(A_) - set(B_))[:30],
                             'r_bits_chi_rig': sorted(set(B_) - set(A_))[:30], 'held_live': sorted(lheld & cand.get(t, set())),
                             'held_rig': sorted(rheld.get(t, set())), 'full_live': lfull, 'full_rig': rfull.get(t, False)})
        elif len(A_) != len(B_) or A_ != B_:
            out_bad.append(t)
    n_l = sum(len(v) for v in live.values()); n_r = sum(len(v) for v in rig.values())
    res = {'window': [S, E], 'live_records': n_l, 'rig_records': n_r, 'first_L_E_dev': first_dev, 'domain_minutes': n_dom,
           'V10a_mismatch_minutes': in_bad, 'V10a_first': dom[:20], 'outside_domain_mismatch_minutes': out_bad,
           'live_buffer_bad_frames': bad, 'live_buffer': a.live_buffer}
    res['V10a_ok'] = in_bad == 0 and bad == 0
    res['ok'] = res['V10a_ok']
    json.dump(res, open(a.out, 'w'), indent=1)
    json.dump(diag, open(a.out.replace('.json', '') + '_diag.json', 'w'), indent=0)
    res['diag_file'] = a.out.replace('.json', '') + '_diag.json'
    print(json.dumps({k: res[k] for k in ('V10a_ok', 'live_records', 'rig_records', 'domain_minutes', 'V10a_mismatch_minutes')} | {'outside_n': len(out_bad)}))
    return 0 if res['ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
