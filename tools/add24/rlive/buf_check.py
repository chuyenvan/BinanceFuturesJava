#!/usr/bin/env python3
"""ADD24 R-LIVE [ERRATA6 M1] cong buffer gate fail-closed. CHI dung ts + so sanh BYTE; KHONG in / thong ke gia tri r.
Can cu: persist live (GateRatioPersist) append-only - moi anh pull242/<D>/run/gate_ratio_live.bin.gz la tien to byte cua anh sau
(kiem 11-03..11-23); rig (CrashDayRig:255-271) nap ban ghi ts < START cua fixture, init() production cat theo dong ho THAT (now - DAYS).
pre : ban ghi ts < START cua buffer fixture == ban ghi ts < START cua anh live muon nhat (LIVEBUF): cung so luong, cung sha256 byte (ts,r);
      ts tang dan; 0 chunk hong; ban ghi cu nhat >= now - DAYS + 1 ngay (khong ban ghi nao bi init() cat theo dong ho that).
post: moi lane: result.json buffer_init_records == buffer_after_load == n_pre cua buoc pre.
usage: buf_check.py pre --fx-buf F --live-buf G --start 'YYYY-MM-DD HH:MM' --out J [--days 90]
       buf_check.py post --pre J --lanes DIR1,DIR2,...
exit 0 = dat; 3 = truot (run_rlive => exit 17, KHONG cham)."""
import argparse, gzip, hashlib, json, os, struct, sys, time
from datetime import datetime, timedelta, timezone

MAGIC = 0x47525231
DAY = 86400000
TZ7 = timezone(timedelta(hours=7))


def raw_records(p):
    """Bytes ban ghi (12 B: ts>q + r>f) noi tiep theo thu tu file + so chunk hong (dung la 0)."""
    import snappy
    b = (gzip.open(p, 'rb') if p.endswith('.gz') else open(p, 'rb')).read()
    i, out, bad = 0, [], 0
    while i + 12 <= len(b):
        m, n, _ = struct.unpack('>iii', b[i:i + 12])
        if m != MAGIC or n < 0 or i + 12 + n > len(b):
            bad += 1
            break
        raw = snappy.uncompress(b[i + 12:i + 12 + n])
        out.append(raw[:len(raw) - len(raw) % 12])
        i += 12 + n
    if i != len(b):
        bad += 1
    return b''.join(out), bad


def pre_part(p, start):
    raw, bad = raw_records(p)
    n, last, mono, first = 0, None, True, None
    for (t,) in struct.iter_unpack('>q', b''.join(raw[k:k + 8] for k in range(0, len(raw), 12))):
        if first is None:
            first = t
        if last is not None and t < last:
            mono = False
        last = t
        if t < start:
            n += 1
    seg = raw[:n * 12]
    return {'file': p, 'n_all': len(raw) // 12, 'n_pre': n, 'sha256_pre': hashlib.sha256(seg).hexdigest(), 'bad_chunks': bad,
            'monotone': mono, 'min_ts': first}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('mode', choices=['pre', 'post'])
    ap.add_argument('--fx-buf'); ap.add_argument('--live-buf'); ap.add_argument('--start'); ap.add_argument('--out')
    ap.add_argument('--days', type=int, default=90); ap.add_argument('--pre'); ap.add_argument('--lanes', default='')
    ap.add_argument('--now-ms', type=int, default=0, help='CHI test')
    a = ap.parse_args()
    if a.mode == 'pre':
        S = int(datetime.strptime(a.start, '%Y-%m-%d %H:%M').replace(tzinfo=TZ7).timestamp() * 1000)
        fx, lv = pre_part(a.fx_buf, S), pre_part(a.live_buf, S)
        now = a.now_ms or int(time.time() * 1000)
        chk = {'same_n_pre': fx['n_pre'] == lv['n_pre'] and fx['n_pre'] > 0, 'same_sha_pre': fx['sha256_pre'] == lv['sha256_pre'],
               'no_bad_chunk': fx['bad_chunks'] == 0 and lv['bad_chunks'] == 0, 'monotone': fx['monotone'] and lv['monotone'],
               'no_wallclock_trim': fx['min_ts'] is not None and fx['min_ts'] >= now - a.days * DAY + DAY}
        res = {'start': S, 'days': a.days, 'now_ms': now, 'fx': fx, 'live': lv, 'checks': chk, 'ok': all(chk.values())}
        json.dump(res, open(a.out, 'w'), indent=1)
    else:
        pre = json.load(open(a.pre))
        n = pre['fx']['n_pre']
        lanes = {}
        for d in [x for x in a.lanes.split(',') if x]:
            r = json.load(open(os.path.join(d, 'result.json')))
            lanes[d] = {'buffer_init_records': r.get('buffer_init_records'), 'buffer_after_load': r.get('buffer_after_load')}
            lanes[d]['ok'] = lanes[d]['buffer_init_records'] == lanes[d]['buffer_after_load'] == n
        res = {'n_pre': n, 'pre_ok': bool(pre.get('ok')), 'lanes': lanes, 'ok': bool(pre.get('ok')) and bool(lanes) and all(v['ok'] for v in lanes.values())}
    print(json.dumps({'mode': a.mode, 'ok': res['ok'], 'checks': res.get('checks'), 'lanes': {k: v['ok'] for k, v in res.get('lanes', {}).items()}}))
    return 0 if res['ok'] else 3


if __name__ == '__main__':
    sys.exit(main())
