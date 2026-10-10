#!/usr/bin/env python3
"""HO26 scorer B (doc lap) - cham holdout 2026H1 theo PREREG_HOLDOUT2026H1 §1 + ADDENDUM-1/2.

Dinh nghia: docs/result/ho26/score_B_defs.md. Khong import script phan tich nao;
chi dung research/analysis/jbin.py (doc nen 1m, tuple (startTime,max,min,close,open,vol)).
"""
import argparse, csv, datetime as dt, gzip, hashlib, json, logging, math, os, re, sys, time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import jbin  # noqa: E402

LOG = logging.getLogger('ho26b')
OUT = '/home/ubuntu/kaggle_sim/out'
TICK = '/home/ubuntu/kaggle_data_hpo'
T26MD5 = '/home/ubuntu/claude_master/1003/ho1/ticker26_oracle_gunzip_md5.json'
LOCK = '/home/ubuntu/claude_master/1002/oracle_heavy.lock'
TZ7 = dt.timezone(dt.timedelta(hours=7))
MIN = 60000
DAY = 1440
EQ0 = 35000.0
SEEDS = [42, 7, 13, 21, 99, 123, 777, 2024]
DEV_REF = {'sharpe': 1.80, 'cagr': 27.6, 'maxdd': -22.9}  # DEV baseline stress (K24-S, nsel-nen)
INFL = math.sqrt(2 * math.log(3))
G = {}


def ms7(s, fmt='%Y%m%d %H:%M'):
    return int(dt.datetime.strptime(s, fmt).replace(tzinfo=TZ7).timestamp() * 1000)


def load_pd(path):
    rows = []
    with open(path, newline='') as f:
        for r in csv.DictReader(f):
            e = float(r['entry'])
            rows.append(dict(sym=r['sym'], side=r['side'], entry=e,
                             start=ms7(r['start']), end=ms7(r['end']),
                             q=float(r['margin']) / e, pnl=float(r['pnl'])))
    return rows


def _init(g0, nmin, syms):
    G['G0'], G['NMIN'], G['SYMS'] = g0, nmin, syms


def parse_file(path):
    raw = gzip.open(path, 'rb').read()
    md5 = hashlib.md5(raw).hexdigest()
    g0, nmin, syms = G['G0'], G['NMIN'], G['SYMS']
    acc, nk, bad, kmin, kmax = {}, 0, 0, None, None
    for k, m in jbin.iter_minutes(raw):
        nk += 1
        if k % MIN:
            bad += 1
        kmin = k if kmin is None else min(kmin, k)
        kmax = k if kmax is None else max(kmax, k)
        i = (k - g0) // MIN
        if i < 0 or i >= nmin or not m:
            continue
        for s0, t in m.items():
            s = s0[:-4] if s0.endswith('USDT') else s0  # ticker key = <sym>USDT, printDone sym = <sym>
            if t is not None and s in syms:
                a = acc.get(s)
                if a is None:
                    a = acc[s] = ([], [])
                a[0].append(i)
                a[1].append(t[3])
    del raw
    res = {s: (np.asarray(a[0], np.int32), np.asarray(a[1], np.float32)) for s, a in acc.items()}
    return os.path.basename(path), md5, nk, bad, kmin, kmax, res


def build_grid(g0, g1, syms, workers):
    nmin = (g1 - g0) // MIN
    d = dt.datetime.fromtimestamp(g0 / 1000, dt.timezone.utc).date()
    d1 = dt.datetime.fromtimestamp((g1 - 1) / 1000, dt.timezone.utc).date() + dt.timedelta(days=1)
    files = []
    while d <= d1:
        p = os.path.join(TICK, 'ticker_%s.bin.gz' % d.strftime('%Y%m%d'))
        if os.path.exists(p):
            files.append(p)
        d += dt.timedelta(days=1)
    LOG.info('grid nmin=%d syms=%d files=%d (%s..%s)', nmin, len(syms), len(files),
             os.path.basename(files[0]), os.path.basename(files[-1]))
    grid = {s: np.full(nmin, np.nan, np.float32) for s in syms}
    meta = []
    with ProcessPoolExecutor(workers, initializer=_init, initargs=(g0, nmin, frozenset(syms))) as ex:
        for name, md5, nk, bad, kmin, kmax, res in ex.map(parse_file, files):
            for s, (ii, cc) in res.items():
                grid[s][ii] = cc
            meta.append(dict(file=name, md5=md5, minutes=nk, bad_key=bad, kmin=kmin, kmax=kmax))
            LOG.info('parsed %s minutes=%d syms=%d', name, nk, len(res))
    return grid, meta, nmin


def equity(rows, g0, g1, nmin, grid):
    """E[i] = EQ0 + sum pnl(end <= m_i) + sum_{start<=m_i<end} side*q*(close(m_i)-entry)."""
    real = np.zeros(nmin, np.float64)
    unr = np.zeros(nmin, np.float64)
    cnt = np.zeros(nmin, np.int32)
    base, beyond, miss, tot = EQ0, 0, 0, 0
    for r in rows:
        if r['end'] < g0:
            base += r['pnl']
        elif r['end'] < g1:
            real[(r['end'] - g0) // MIN] += r['pnl']
        else:
            beyond += 1
        a, b = max(r['start'], g0), min(r['end'], g1)
        if b <= a:
            continue
        ia, ib = (a - g0) // MIN, (b - g0) // MIN
        px = grid[r['sym']][ia:ib].astype(np.float64)
        nn = int(np.isnan(px).sum())
        miss += nn
        tot += ib - ia
        if nn:
            px = np.concatenate([[r['entry']], px])
            idx = np.where(~np.isnan(px), np.arange(len(px)), 0)
            np.maximum.accumulate(idx, out=idx)
            px = px[idx][1:]
        sg = 1.0 if r['side'] == 'BUY' else -1.0
        unr[ia:ib] += sg * r['q'] * (px - r['entry'])
        cnt[ia:ib] += 1
    E = base + np.cumsum(real) + unr
    return E, cnt, dict(beyond=beyond, miss_legmin=miss, legmin=tot)


def month_bounds(w0, w1):
    out, m = [], dt.datetime.fromtimestamp(w0 / 1000, TZ7)
    while True:
        t = int(m.timestamp() * 1000)
        if t >= w1:
            break
        out.append((m.strftime('%Y-%m'), t))
        m = m.replace(year=m.year + (m.month == 12), month=m.month % 12 + 1)
    return out


def metrics(rows, E, cnt, g0, w0, w1):
    iw0, iw1 = (w0 - g0) // MIN, (w1 - g0) // MIN
    win_s = [r for r in rows if w0 <= r['start'] < w1]
    win_e = [r for r in rows if w0 <= r['end'] < w1]
    ew = E[iw0:iw1]
    peak = np.maximum.accumulate(ew)
    mdd = float((ew / peak - 1).min() * 100)
    e0, e1 = float(E[iw0]), float(E[iw1 - 1])
    roi = e1 / e0 - 1
    nd = (iw1 - iw0) // DAY
    pts = [iw0 + DAY * j for j in range(nd)] + [iw1 - 1]
    P = E[pts]
    r = P[1:] / P[:-1] - 1
    sd = float(r.std(ddof=1))
    dn = float(np.sqrt(np.mean(np.minimum(r, 0) ** 2)))
    sh = float(r.mean() / sd * math.sqrt(365)) if sd > 0 else float('nan')
    so = float(r.mean() / dn * math.sqrt(365)) if dn > 0 else float('nan')
    mb = month_bounds(w0, w1)
    mi = [(t - g0) // MIN for _, t in mb] + [iw1 - 1]
    monthly = {}
    for k, (lab, t) in enumerate(mb):
        t1 = mb[k + 1][1] if k + 1 < len(mb) else w1
        monthly[lab] = dict(roi=float(E[mi[k + 1]] / E[mi[k]] - 1) * 100,
                            spnl=sum(x['pnl'] for x in win_e if t <= x['end'] < t1),
                            n=sum(1 for x in win_s if t <= x['start'] < t1))
    dent = {(x['start'] - w0) // (DAY * MIN) for x in win_s}
    dopen = sum(1 for j in range(nd) if cnt[iw0 + DAY * j: iw0 + DAY * (j + 1)].max() > 0)
    return dict(n=len(win_s), spnl=sum(x['pnl'] for x in win_e), e0=e0, e1=e1, roi=roi * 100,
                maxdd=mdd, sharpe=sh, sortino=so, cagr=((1 + roi) ** (365.0 / nd) - 1) * 100,
                ndays=nd, pct_days_entry=100.0 * len(dent) / nd, pct_days_open=100.0 * dopen / nd,
                episodes=len({x['start'] for x in win_s}), monthly=monthly,
                daily_pnl=np.diff(P).tolist(), daily_ret=r.tolist())


def log_check(logpath, E, g0, w0, w1):
    rx = re.compile(r'Update (\d{8} \d\d:\d\d) => b:\s*(-?\d+).*?unP:\s*(-?\d+)')
    d0, d1 = [], []
    with open(logpath, errors='replace') as f:
        for line in f:
            mm = rx.search(line)
            if not mm:
                continue
            t = ms7(mm.group(1))
            if not (w0 <= t < w1):
                continue
            i = (t - g0) // MIN
            v = float(mm.group(2)) + float(mm.group(3))
            if v != 0:
                d0.append(abs(E[i] / v - 1) * 100)
                d1.append(abs(E[i - 1] / v - 1) * 100)
    if not d0:
        return dict(n=0)
    return dict(n=len(d0), med_at=float(np.median(d0)), max_at=float(np.max(d0)),
                med_prev=float(np.median(d1)), max_prev=float(np.max(d1)))


def agg(v):
    v = [x for x in v if x == x]
    return dict(mean=float(np.mean(v)), min=float(np.min(v)), max=float(np.max(v))) if v else {}


def boot(DA, DB, rng, B, L=10):
    """Moving-block bootstrap ngay (block L), cung chi so ngay cho moi seed. Stat = mean_seed sum_ngay (A-B)."""
    D = np.asarray(DA) - np.asarray(DB)
    n = D.shape[1]
    nb = -(-n // L)
    s0 = float(D.sum(1).mean())
    st = rng.integers(0, n - L + 1, size=(B, nb))
    idx = (st[:, :, None] + np.arange(L)).reshape(B, -1)[:, :n]
    bs = D[:, idx].sum(2).mean(0)
    lo, hi = np.percentile(bs, [2.5, 97.5])
    hw = (hi - lo) / 2
    return dict(point=s0, lo=float(lo), hi=float(hi), p_gt0=float((bs > 0).mean()),
                infl_lo=s0 - hw * INFL, infl_hi=s0 + hw * INFL, B=B, L=L)


def raw_lines(path):
    with open(path) as f:
        L = [x.rstrip('\r\n') for x in f]
    return L[1:]


def selfcheck3(hdir, ddir, E, g0, w0):
    """Phan truoc 2026 cua run holdout vs run DEV cung cau hinh."""
    C = ms7('20251231 07:00')  # sim DEV dung sau ngay UTC 2025-12-30 (= 2025-12-31 06:59 +07)
    Lh = raw_lines(os.path.join(hdir, 'storage/printDone.csv'))
    Ld = raw_lines(os.path.join(ddir, 'storage/printDone.csv'))
    ch = Counter(x for x in Lh if ms7(x.split(',')[8]) < C)
    cd = Counter(Ld)
    common = sum((ch & cd).values())
    rh, rd = load_pd(os.path.join(hdir, 'storage/printDone.csv')), load_pd(os.path.join(ddir, 'storage/printDone.csv'))
    rj = json.load(open(os.path.join(ddir, 'result.json')))
    iw0 = (w0 - g0) // MIN
    eq_dev = EQ0 + sum(r['pnl'] for r in rd)
    eq_h_C = EQ0 + sum(r['pnl'] for r in rh if r['end'] < C)
    eq_h_real_w0 = EQ0 + sum(r['pnl'] for r in rh if r['end'] < w0)
    return dict(dev=os.path.basename(ddir), n_dev=len(Ld), n_ho_end_lt_C=sum(ch.values()),
                lines_common=common, only_ho=sum((ch - cd).values()), only_dev=sum((cd - ch).values()),
                ho_open_over_C=sum(1 for r in rh if r['start'] < C <= r['end']),
                eq_dev_result=rj.get('equity_final'), eq_dev_sum=eq_dev, eq_ho_realized_C=eq_h_C,
                eq_ho_realized_lt_w0=eq_h_real_w0, eq_ho_mtm_w0m1=float(E[iw0 - 1]),
                diff_realized_C_pct=(eq_h_C / eq_dev - 1) * 100,
                diff_mtm_w0m1_pct=(float(E[iw0 - 1]) / eq_dev - 1) * 100)


def take_lock():
    while os.path.exists(LOCK):
        LOG.info('lock busy, waiting: %s', open(LOCK).read().strip())
        time.sleep(60)
    with open(LOCK, 'w') as f:
        f.write('ho26_score_b pid=%d %s\n' % (os.getpid(), time.strftime('%F %T')))


def rules(R, cfgs, seeds):
    b0, k24, m2 = cfgs
    S = R['s']
    g = lambda c, k: [S[c][s][k] for s in seeds]
    out = {}
    pk = g(k24, 'spnl')
    out['E0'] = dict(mean_spnl_k24=float(np.mean(pk)), n_pos=sum(x > 0 for x in pk),
                     ok=bool(np.mean(pk) > 0 and sum(x > 0 for x in pk) >= 6))
    dp = [a - b for a, b in zip(g(k24, 'spnl'), g(b0, 'spnl'))]
    dd = [a - b for a, b in zip(g(k24, 'maxdd'), g(b0, 'maxdd'))]
    out['HA'] = dict(mean_dspnl=float(np.mean(dp)), mean_dmaxdd=float(np.mean(dd)),
                     ok=bool(np.mean(dp) >= 0 and np.mean(dd) >= -5))
    dn = [a - b for a, b in zip(g(m2, 'n'), g(k24, 'n'))]
    dp = [a - b for a, b in zip(g(m2, 'spnl'), pk)]
    dd = [a - b for a, b in zip(g(m2, 'maxdd'), g(k24, 'maxdd'))]
    thr = -0.10 * float(np.mean(pk))
    nseed = sum(d >= -0.10 * p for d, p in zip(dp, pk))
    c = [np.mean(dn) >= 200, np.mean(dp) >= thr, np.mean(dd) >= -8, nseed >= 5]
    out['HB'] = dict(mean_dn=float(np.mean(dn)), mean_dspnl=float(np.mean(dp)), thr_dspnl=thr,
                     mean_dmaxdd=float(np.mean(dd)), n_seed_ok=nseed, conds=[bool(x) for x in c], ok=bool(all(c)))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--w0', default='20260101')
    ap.add_argument('--w1', default='20260701')
    ap.add_argument('--fmt', default='ho26-{cfg}-{fee}-s{seed}')
    ap.add_argument('--cfgs', default='b0,k24,m2', help='vai: base,k24,m2')
    ap.add_argument('--fees', default='s,b')
    ap.add_argument('--seeds', default=','.join(map(str, SEEDS)))
    ap.add_argument('--workers', type=int, default=3)
    ap.add_argument('--boot', type=int, default=10000)
    ap.add_argument('--dev-ref', default='nsel-nen-s42', help="'' = bo tu kiem 3")
    ap.add_argument('--out', default='docs/result/ho26/HO26_RESULT_B')
    ap.add_argument('--defs-hash', default='')
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    cfgs, fees, seeds = a.cfgs.split(','), a.fees.split(','), [int(x) for x in a.seeds.split(',')]
    w0, w1 = ms7(a.w0 + ' 00:00'), ms7(a.w1 + ' 00:00')
    g0, g1 = w0 - DAY * MIN, w1 + 31 * 60 * MIN
    runs = {}
    for fee in fees:
        for c in cfgs:
            for s in seeds:
                d = os.path.join(OUT, a.fmt.format(cfg=c, fee=fee, seed=s))
                assert os.path.isfile(os.path.join(d, 'storage/printDone.csv')), d
                runs[(fee, c, s)] = (d, load_pd(os.path.join(d, 'storage/printDone.csv')))
    syms = sorted({r['sym'] for _, rows in runs.values() for r in rows if r['end'] > g0 and r['start'] < g1})
    take_lock()
    try:
        grid, tmeta, nmin = build_grid(g0, g1, syms, a.workers)
    finally:
        os.remove(LOCK)
    R, CHK, Ecache = {f: {c: {} for c in cfgs} for f in fees}, {}, {}
    tz7, tzu = [], []
    for (fee, c, s), (d, rows) in runs.items():
        E, cnt, st = equity(rows, g0, g1, nmin, grid)
        m = metrics(rows, E, cnt, g0, w0, w1)
        R[fee][c][s] = m
        rj = json.load(open(os.path.join(d, 'result.json')))
        eq_all = EQ0 + sum(r['pnl'] for r in rows)
        CHK[os.path.basename(d)] = dict(
            eq_result=rj.get('equity_final'), n_result=rj.get('n_trades'), ok=rj.get('ok'),
            date_last=rj.get('date_last'), n_pd=len(rows), eq_sum_all=eq_all,
            diff_sum_pct=(eq_all / rj['equity_final'] - 1) * 100,
            eq_mtm_last=float(E[-1]), diff_mtm_last_pct=(float(E[-1]) / rj['equity_final'] - 1) * 100,
            n_match=len(rows) == rj.get('n_trades'), miss_pct=100.0 * st['miss_legmin'] / max(st['legmin'], 1),
            beyond=st['beyond'], log=log_check(os.path.join(d, 'logs/sim.out'), E, g0, w0, w1))
        if (fee, c, s) == ('s', cfgs[1], seeds[0]):
            Ecache['sc3'] = (d, E)
        for r in rows:
            if w0 <= r['start'] < w1:
                i = (r['start'] - g0) // MIN
                v = grid[r['sym']][i]
                if v == v and v > 0:
                    tz7.append(abs(r['entry'] / v - 1))
                v = grid[r['sym']][i + 420] if i + 420 < nmin else np.nan
                if v == v and v > 0:
                    tzu.append(abs(r['entry'] / v - 1))
        LOG.info('%s n=%d spnl=%.0f roi=%.2f mdd=%.2f', os.path.basename(d), m['n'], m['spnl'], m['roi'], m['maxdd'])
    t26 = json.load(open(T26MD5))
    got = {x['file'][:-3]: x['md5'] for x in tmeta}
    want = {k: v for k, v in t26.items() if w0 <= ms7(k[7:15] + ' 07:00') < w1}
    T = dict(ok=sum(got.get(k) == v for k, v in want.items()), bad=sum(k in got and got[k] != v for k, v in want.items()),
             miss=sum(k not in got for k in want), files=[x['file'] for x in tmeta],
             bad_key=sum(x['bad_key'] for x in tmeta),
             tz_med_plus7=float(np.median(tz7)) if tz7 else None, tz_n_plus7=len(tz7),
             tz_med_utc=float(np.median(tzu)) if tzu else None, tz_n_utc=len(tzu))
    SC3 = selfcheck3(Ecache['sc3'][0], os.path.join(OUT, a.dev_ref), Ecache['sc3'][1], g0, w0) if a.dev_ref and 'sc3' in Ecache else None
    RU = rules(R, cfgs, seeds) if 's' in fees else None
    rng = np.random.default_rng(20261010)
    BT, DL = {}, {}
    for fee in fees:
        for arm, base in ((cfgs[1], cfgs[0]), (cfgs[2], cfgs[1]), (cfgs[2], cfgs[0])):
            BT['%s-%s_vs_%s' % (fee, arm, base)] = boot([R[fee][arm][s]['daily_pnl'] for s in seeds],
                                                       [R[fee][base][s]['daily_pnl'] for s in seeds], rng, a.boot)
            k = lambda key: [R[fee][arm][s][key] - R[fee][base][s][key] for s in seeds]
            DL['%s-%s_vs_%s' % (fee, arm, base)] = {key: dict(agg(k(key)), npos=sum(x > 0 for x in k(key)), per_seed=k(key))
                                                    for key in ('n', 'spnl', 'maxdd', 'roi', 'sharpe', 'e1')}
    SUM = {fee: {c: {key: agg([R[fee][c][s][key] for s in seeds])
                     for key in ('n', 'spnl', 'roi', 'maxdd', 'sharpe', 'sortino', 'cagr', 'pct_days_entry',
                                 'pct_days_open', 'episodes', 'e0', 'e1')} for c in cfgs} for fee in fees}
    res = dict(scorer='B', w0=a.w0, w1=a.w1, cfgs=cfgs, fees=fees, seeds=seeds, defs_hash=a.defs_hash,
               runs=R, checks=CHK, ticker=T, selfcheck3=SC3, rules=RU, boot=BT, delta=DL, summary=SUM)
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    json.dump(res, open(a.out + '.json', 'w'), indent=1, default=float)
    write_md(res, a.out + '.md')
    LOG.info('done -> %s.{json,md}', a.out)


def f(x, p=0):
    return ('%.' + str(p) + 'f') % x if x is not None and x == x else 'nan'


def mmm(d, p=0):
    return '%s [%s..%s]' % (f(d['mean'], p), f(d['min'], p), f(d['max'], p)) if d else '-'


def write_md(res, path):
    cf, fees, seeds = res['cfgs'], res['fees'], res['seeds']
    L = ['# HO26 — kết quả scorer B (độc lập)', '',
         'Prereg `docs/prereg/PREREG_HOLDOUT2026H1.md` (35d03784 + ADD-1 0e3282a6 + ADD-2 1682a311/2691816d/8fe35b23) §1. '
         'Định nghĩa `docs/result/ho26/score_B_defs.md` (commit `%s`, trước khi đọc dữ liệu 2026). Script `research/analysis/ho26_score_b.py`. '
         'Cửa sổ [%s 00:00, %s 00:00) +07. Seed %s.' % (res['defs_hash'], res['w0'], res['w1'], seeds), '',
         '## Tự kiểm', '',
         '| run | n pd | n result | eq Σpnl | eq result | lệch % | eq MTM cuối lưới lệch % | chân quá lưới | thiếu giá % | log b+unP n | med lệch % (tại/phút trước) | max lệch % |',
         '|---|---|---|---|---|---|---|---|---|---|---|---|']
    for k, c in res['checks'].items():
        lg = c['log']
        L.append('| %s | %d | %s | %s | %s | %s | %s | %d | %s | %d | %s / %s | %s |' % (
            k, c['n_pd'], c['n_result'], f(c['eq_sum_all']), f(c['eq_result']), f(c['diff_sum_pct'], 4),
            f(c['diff_mtm_last_pct'], 4), c['beyond'], f(c['miss_pct'], 4), lg.get('n', 0),
            f(lg.get('med_at'), 4), f(lg.get('med_prev'), 4), f(lg.get('max_at'), 4)))
    T = res['ticker']
    L += ['', 'Ticker md5(gunzip) vs `ticker26_oracle_gunzip_md5.json`: ok %d / bad %d / miss %d; key lẻ phút %d; file %s..%s. '
          'TZ: median |entry/close(start)−1| giả định +07 = %s (n=%d); nếu start là UTC = %s (n=%d).' % (
              T['ok'], T['bad'], T['miss'], T['bad_key'], T['files'][0], T['files'][-1],
              f(T['tz_med_plus7'], 5), T['tz_n_plus7'], f(T['tz_med_utc'], 5), T['tz_n_utc'])]
    if res['selfcheck3']:
        s3 = res['selfcheck3']
        L += ['', 'Phần trước 2026 (run %s-s-s%d vs %s): dòng printDone end<2025-12-31 07:00 +07: holdout %d, DEV %d, trùng y hệt %d, chỉ holdout %d, chỉ DEV %d; '
              'chân holdout mở qua 2025-12-31 07:00: %d. Equity DEV %s (result %s) vs holdout realized tại mốc %s (lệch %s%%); '
              'holdout MTM 2025-12-31 23:59 +07 = %s (lệch %s%%).' % (
                  cf[1], seeds[0], s3['dev'], s3['n_ho_end_lt_C'], s3['n_dev'], s3['lines_common'], s3['only_ho'], s3['only_dev'],
                  s3['ho_open_over_C'], f(s3['eq_dev_sum']), s3['eq_dev_result'], f(s3['eq_ho_realized_C']),
                  f(s3['diff_realized_C_pct'], 4), f(s3['eq_ho_mtm_w0m1']), f(s3['diff_mtm_w0m1_pct'], 4))]
    for fee in fees:
        L += ['', '## Bảng cfg — %s (mean [min..max], 8 seed)' % ('STRESS 1,675% (CHÍNH)' if fee == 's' else 'phí gốc (báo kèm)'), '',
              '| cfg | n | ΣPnL | ROI % | maxDD % | Sharpe | Sortino | CAGR năm hoá % | % ngày có vào | % ngày có vị thế | số đợt |',
              '|---|---|---|---|---|---|---|---|---|---|---|']
        for c in cf:
            S = res['summary'][fee][c]
            L.append('| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |' % (
                c, mmm(S['n']), mmm(S['spnl']), mmm(S['roi'], 2), mmm(S['maxdd'], 2), mmm(S['sharpe'], 2),
                mmm(S['sortino'], 2), mmm(S['cagr'], 1), mmm(S['pct_days_entry'], 1), mmm(S['pct_days_open'], 1), mmm(S['episodes'])))
        L += ['', '| cfg | seed | n | ΣPnL | E đầu | E cuối | ROI % | maxDD % | Sharpe |', '|---|---|---|---|---|---|---|---|---|']
        for c in cf:
            for s in seeds:
                m = res['runs'][fee][c][s]
                L.append('| %s | %d | %d | %s | %s | %s | %s | %s | %s |' % (c, s, m['n'], f(m['spnl']), f(m['e0']), f(m['e1']),
                                                                       f(m['roi'], 2), f(m['maxdd'], 2), f(m['sharpe'], 2)))
    L += ['', '## Δ ghép cặp theo seed (arm − base; mean [min..max], #Δ>0/8)', '',
          '| cặp | Δn | ΔΣPnL | ΔmaxDD pp | ΔROI pp | ΔSharpe | ΔE cuối |', '|---|---|---|---|---|---|---|']
    for k, D in res['delta'].items():
        L.append('| %s | %s | %s | %s | %s | %s | %s |' % (k, *['%s (%d)' % (mmm(D[x], 2 if x in ('maxdd', 'roi', 'sharpe') else 0), D[x]['npos'])
                                                         for x in ('n', 'spnl', 'maxdd', 'roi', 'sharpe', 'e1')]))
    if res['rules']:
        R = res['rules']
        e, ha, hb = R['E0'], R['HA'], R['HB']
        L += ['', '## Verdict (bản CHÍNH = stress)', '',
              '- **E0 %s**: mean ΣPnL_S(%s) = %s (ngưỡng > 0); seed > 0: %d/8 (ngưỡng ≥ 6).' % (
                  'PASS' if e['ok'] else 'FAIL', cf[1], f(e['mean_spnl_k24']), e['n_pos']),
              '- **H-A %s**: mean ΔΣPnL_S = %s (≥ 0); mean ΔmaxDD = %s pp (≥ −5).' % (
                  'XÁC NHẬN' if ha['ok'] else 'KHÔNG xác nhận', f(ha['mean_dspnl']), f(ha['mean_dmaxdd'], 2)),
              '- **H-B %s**: mean Δn = %s (≥ +200) [%s]; mean ΔΣPnL_S = %s (≥ %s) [%s]; mean ΔmaxDD = %s pp (≥ −8) [%s]; '
              'seed ΔΣPnL_S ≥ −10%%·ΣPnL_S(k24 cùng seed): %d/8 (≥ 5) [%s].' % (
                  'XÁC NHẬN' if hb['ok'] else 'KHÔNG xác nhận', f(hb['mean_dn']), hb['conds'][0], f(hb['mean_dspnl']),
                  f(hb['thr_dspnl']), hb['conds'][1], f(hb['mean_dmaxdd'], 2), hb['conds'][2], hb['n_seed_ok'], hb['conds'][3])]
    L += ['', '## Bootstrap MTM block-10d (Δ $ PnL MTM cửa sổ, mean 8 seed, cùng chỉ số ngày cho mọi seed; inflate k=3 ×%.3f)' % INFL, '',
          '| cặp | điểm | CI95 | CI95 inflate | P(Δ>0) |', '|---|---|---|---|---|']
    for k, b in res['boot'].items():
        L.append('| %s | %s | [%s, %s] | [%s, %s] | %s |' % (k, f(b['point']), f(b['lo']), f(b['hi']),
                                                         f(b['infl_lo']), f(b['infl_hi']), f(b['p_gt0'], 3)))
    for fee in fees:
        months = list(res['runs'][fee][cf[0]][seeds[0]]['monthly'].keys())
        L += ['', '## Theo tháng — %s (mean 8 seed: ROI %% / ΣPnL / n)' % fee, '',
              '| cfg | ' + ' | '.join(months) + ' |', '|---' * (len(months) + 1) + '|']
        for c in cf:
            cells = []
            for mo in months:
                v = [res['runs'][fee][c][s]['monthly'][mo] for s in seeds]
                cells.append('%s / %s / %s' % (f(np.mean([x['roi'] for x in v]), 2), f(np.mean([x['spnl'] for x in v])),
                                               f(np.mean([x['n'] for x in v]))))
            L.append('| %s | %s |' % (c, ' | '.join(cells)))
    if 's' in fees:
        L += ['', '## Holdout/DEV (stress; DEV baseline K24-S: Sharpe %.2f, CAGR %.1f%%, maxDD %.1f%%)' % (
            DEV_REF['sharpe'], DEV_REF['cagr'], DEV_REF['maxdd']), '',
              '| cfg | Sharpe HO | tỉ lệ | CAGR năm hoá HO % | tỉ lệ | maxDD HO % | tỉ lệ |', '|---|---|---|---|---|---|---|']
        for c in cf:
            S = res['summary']['s'][c]
            L.append('| %s | %s | %s | %s | %s | %s | %s |' % (
                c, f(S['sharpe']['mean'], 2), f(S['sharpe']['mean'] / DEV_REF['sharpe'], 2), f(S['cagr']['mean'], 1),
                f(S['cagr']['mean'] / DEV_REF['cagr'], 2), f(S['maxdd']['mean'], 2), f(S['maxdd']['mean'] / DEV_REF['maxdd'], 2)))
    with open(path, 'w') as fo:
        fo.write('\n'.join(L) + '\n')


if __name__ == '__main__':
    main()
