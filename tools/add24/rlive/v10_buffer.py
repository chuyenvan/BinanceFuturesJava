#!/usr/bin/env python3
"""ADD24 cong V10 (ERRATA3 A4): tap (ts, r) rig nap vao buffer gate trong cua so == ban ghi buffer live (file gate_ratio_live cua lan pull
SAU cua so) cho cac phut cua so: so ban ghi lech <= 1e-4 tuong doi VA r lech <= 1e-6. Chi dem / so - khong in gia tri r.
usage: v10_buffer.py --rig-appended <lane>/appended.csv.gz --live-buffer <pull>/run/gate_ratio_live.bin.gz --start --end --out V10.json
"""
import argparse, csv, gzip, json, os, shutil, struct, sys, tempfile
from collections import defaultdict
from datetime import datetime, timedelta, timezone
import numpy as np

sys.path.insert(0, os.path.expanduser('~/claude_master/1016/grr'))
import grr_lib  # noqa: E402
TZ7 = timezone(timedelta(hours=7))


def ms7(s):
    return int(datetime.strptime(s, '%Y-%m-%d %H:%M').replace(tzinfo=TZ7).timestamp() * 1000)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--rig-appended', required=True); ap.add_argument('--live-buffer', required=True)
    ap.add_argument('--start', required=True); ap.add_argument('--end', required=True); ap.add_argument('--out', required=True)
    a = ap.parse_args()
    S, E = ms7(a.start), ms7(a.end)
    rig = defaultdict(list)
    for x in csv.DictReader(gzip.open(a.rig_appended, 'rt')):
        t = int(x['ts'])
        if S <= t < E:
            rig[t].append(float(np.array([int(x['r_bits'])], dtype=np.int32).view(np.float32)[0]))
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
        live[int(t)].append(float(np.float32(v)))
    n_l = sum(len(v) for v in live.values()); n_r = sum(len(v) for v in rig.values())
    n_diff, rmax, ts_bad = 0, 0.0, []
    for t in set(live) | set(rig):
        A_, B_ = sorted(live.get(t, [])), sorted(rig.get(t, []))
        n_diff += abs(len(A_) - len(B_))
        if len(A_) != len(B_):
            ts_bad.append(t); continue
        for x, y in zip(A_, B_):
            rmax = max(rmax, abs(x - y))
    rel = n_diff / max(1, n_l)
    res = {'window': [S, E], 'live_records': n_l, 'rig_records': n_r, 'abs_count_diff': n_diff, 'rel_count_diff': rel,
           'minutes_count_mismatch': len(ts_bad), 'first_mismatch_minutes': sorted(ts_bad)[:20], 'r_max_abs_diff': rmax,
           'live_buffer_bad_frames': bad, 'live_buffer': a.live_buffer}
    res['ok'] = rel <= 1e-4 and rmax <= 1e-6 and bad == 0
    json.dump(res, open(a.out, 'w'), indent=1)
    print(json.dumps({k: res[k] for k in ('ok', 'live_records', 'rig_records', 'abs_count_diff', 'rel_count_diff', 'minutes_count_mismatch', 'r_max_abs_diff')}))
    return 0 if res['ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
