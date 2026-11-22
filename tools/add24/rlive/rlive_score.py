#!/usr/bin/env python3
"""ADD24 R-LIVE bo cham (prereg s8, s9.1-s9.3; P7): L-E, L-N, L-S, L-S2, L-P(bao cao), L-D, L-T, L-SL, L-X, L-K + gan nhan N1-N8 tu dong.
Dau vao: --live (thu muc live_log_parse --mode full), --rig (luot L0), [--follow (L0-FOLLOW)], [--dry (L0-DRY)], --fx (fixture),
--mark (mark 1m csv.gz symbol,t,o,h,l,c; thieu => dung kline fixture lam proxy, ghi ro), --cap, --start/--end (+07).
Ra: score.json (trang thai + so dem + lech tuong doi), labels.csv (moi lech + nhan + bang chung). KHONG in gia / PnL.
Trang thai: PASS / FAIL / INSUFFICIENT ("KHONG XAY RA" khong bao gio = PASS).
"""
import argparse, csv, gzip, json, logging, math, os, statistics, sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ref_size as RS

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger('score')
TZ7 = timezone(timedelta(hours=7))
MIN = 60000
PASS, FAIL, INS = 'PASS', 'FAIL', 'INSUFFICIENT'
LABELS = ('N1', 'N2', 'N3', 'N4', 'N5', 'N6', 'N7', 'N8')


def ms7(s):
    return int(datetime.strptime(s, '%Y-%m-%d %H:%M').replace(tzinfo=TZ7).timestamp() * 1000)


def rd(p):
    if not os.path.exists(p):
        return []
    f = gzip.open(p, 'rt') if p.endswith('.gz') else open(p)
    return list(csv.DictReader(f))


def fnum(x, d=None):
    try:
        return float(x)
    except (TypeError, ValueError):
        return d


class Bars:
    def __init__(self, path):
        self.b = {}
        for r in rd(path):
            self.b[(r['symbol'], int(r['t']))] = (float(r['o']), float(r['h']), float(r['l']), float(r['c']))

    def get(self, s, t):
        return self.b.get((s, t))


def exinfo(fx):
    st, tk = {}, {}
    try:
        d = json.load(open(fx + '/exinfo.json'))
        for s in d.get('symbols', []):
            for f in s.get('filters', []):
                if f.get('filterType') == 'MARKET_LOT_SIZE':
                    st[s['symbol']] = float(f['stepSize'])
                if f.get('filterType') == 'LOT_SIZE' and s['symbol'] not in st:
                    st[s['symbol']] = float(f['stepSize'])
                if f.get('filterType') == 'PRICE_FILTER':
                    tk[s['symbol']] = float(f['tickSize'])
    except Exception as e:
        log.warning('exinfo: %s', e)
    return st, tk


def st_merge(*xs):
    return FAIL if FAIL in xs else (INS if INS in xs else PASS)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--live', required=True); ap.add_argument('--rig', required=True); ap.add_argument('--follow', default='')
    ap.add_argument('--dry', default=''); ap.add_argument('--fx', required=True); ap.add_argument('--mark', default='')
    ap.add_argument('--cap', type=float, default=1000.0); ap.add_argument('--start', required=True); ap.add_argument('--end', required=True)
    ap.add_argument('--apply-ratio', default='on', help='dev 11-05 dry (jar r4q, co TAT) = off')
    ap.add_argument('--u-max', type=float, default=0.6); ap.add_argument('--arm', type=float, default=0.07)
    ap.add_argument('--fee-max', type=float, default=0.0005); ap.add_argument('--out', required=True)
    ap.add_argument('--px-bars', default='union', help='ERRATA_PROPOSED_A E-A5: nen dts + dts+1 (quyet dinh o giay ~6 phut sau, price_realtime/cache)')
    a = ap.parse_args()
    S, E = ms7(a.start), ms7(a.end)
    os.makedirs(a.out, exist_ok=True)
    K = dict(U_MAX=a.u_max) if a.apply_ratio == 'on' else dict(U_MAX=a.u_max, SCALE=1.0, W=(1.0, 1.0, 1.0, 1.0))
    if a.apply_ratio != 'on':
        K['W'] = (1.0, 1.0, 1.0, 1.0); K['SCALE'] = 1.0
    L = lambda n: rd(os.path.join(a.live, n))
    inwin = lambda t: S <= t < E
    # ---------------- dau vao + phut co input
    sel_min = {int(r['ts']) for r in rd(a.fx + '/sel.csv.gz') if inwin(int(r['ts']))}
    gaps = {int(r['minute_ms']) for r in L('gaps.csv')}
    jvm = [int(r['log_ms']) for r in L('jvm_start.csv')]
    down = set(gaps)
    for t in jvm:
        down |= {(t // MIN) * MIN, (t // MIN + 1) * MIN}          # N3: phut khoi dong + tick dau (ERRATA_PROPOSED_A E-A6)
    bars = Bars(a.fx + '/klines.csv.gz')
    mark = Bars(a.mark) if a.mark else bars
    step, tick = exinfo(a.fx)
    sub = [r for r in L('submit.csv') if r['outcome'] == 'SUBMITTED']
    for r in sub:
        r['dts'] = int(r['cid'].split('-')[-2]) * MIN
        r['t'] = int(r['log_ms'])
        r['leg'] = int(r['legIdx']) if r.get('legIdx') else int(r['cid'].split('-')[-1])
    sub = [r for r in sub if inwin(r['dts'])]
    sub.sort(key=lambda r: r['t'])   # on dinh: giu thu tu dong log khi cung ms
    rig = [r for r in rd(a.rig + '/legs.csv') if r['outcome'] == 'SUBMITTED' and inwin(int(r['decision_ts']))]
    fol = [r for r in rd(a.follow + '/legs.csv') if r['outcome'] == 'SUBMITTED'] if a.follow else None
    key = lambda s, lv, d, lg: (d, s, lv, lg)
    LK = {key(r['symbol'], r['level'], r['dts'], r['leg']): r for r in sub}
    RK = {key(r['symbol'], r['level'], int(r['decision_ts']), int(r['leg_idx'])): r for r in rig}
    FK = {key(r['symbol'], r['level'], int(r['decision_ts']), int(r['leg_idx'])) for r in fol} if fol is not None else None
    rej = [(int(r['log_ms']), r.get('g2', ''), r.get('g1', '')) for n in ('reject.csv', 'expired.csv') for r in L(n)]
    tuchoi = [(int(r['log_ms']), r.get('g1', '')) for r in L('tuchoi_cid.csv')]
    skips = [(int(r['log_ms']), r.get('g2', '')) for n in ('skip_paper.csv', 'skip_paper2.csv') for r in L(n)]
    blk = {(int(r['decision_ts']), r['symbol'], r['level']) for r in L('block.csv')}
    labels = []

    def lab(item, k, lb, ev):
        labels.append({'item': item, 'decision_ts': k[0], 'symbol': k[1], 'level': k[2], 'leg': k[3], 'label': lb, 'evidence': ev})
        return lb

    def n4(k, t, cid):
        for (x, s, w) in rej:
            if (s == k[1] or cid in w) and 0 <= x - t <= 60000:
                return 'reject/expired %d' % x
        for (x, c) in tuchoi:
            if c == cid or (k[1] in c and 0 <= x - t <= 60000):
                return 'tu choi %d' % x
        return None

    def n6(k):
        for (x, s) in skips:
            if s == k[1] and x // MIN * MIN in (k[0], k[0] + MIN):
                return 'skip so giay %d' % x
        return None
    # ---------------- L-E / L-N
    dev_first = None
    le = {'live_submits': len(sub), 'rig_submits': len(rig), 'matched': 0, 'N1': 0, 'scorable': 0, 'unexplained': 0, 'by_label': {}}
    for k in sorted(set(LK) | set(RK)):
        if k in LK and k in RK:
            le['matched'] += 1; le['scorable'] += 1
            continue
        side = 'live_only' if k in LK else 'rig_only'
        if k[0] not in sel_min:
            lb = lab('L-E ' + side, k, 'N1', 'khong co sel_dump phut nay'); le['N1'] += 1
        elif k[0] in down:
            lb = lab('L-E ' + side, k, 'N3', 'JVM khoi dong / khoang trong log')
        else:
            le['scorable'] += 1 if side == 'live_only' else 0
            ev4 = n4(k, LK[k]['t'], LK[k]['cid']) if side == 'live_only' else None
            ev6 = n6(k) if side == 'rig_only' else None
            if ev4:
                lb = lab('L-E ' + side, k, 'N4', ev4)
            elif ev6:
                lb = lab('L-E ' + side, k, 'N6', ev6)
            elif side == 'rig_only' and ((k[0], k[1], k[2]) in blk or (k[0], '*', '*') in blk):
                lb = lab('L-E ' + side, k, 'N2', 'live chan MINUTE-* nhung tiem khong hieu luc')
            elif dev_first is not None and FK is not None and ((k in FK) == (k in LK)):
                lb = lab('L-E ' + side, k, 'N5', 'L0-FOLLOW khong lech; lech dau tien da gan nhan luc %d' % dev_first)
            else:
                lb = lab('L-E ' + side, k, 'UNEXPLAINED', '')
                le['unexplained'] += 1
            if lb in ('N4', 'N6', 'N2') and dev_first is None:
                dev_first = k[0]
        le['by_label'][lb] = le['by_label'].get(lb, 0) + 1
    # thu tu trong phut (chi cac khoa khop)
    by_min_l, by_min_r = {}, {}
    for r in sub:
        k = key(r['symbol'], r['level'], r['dts'], r['leg'])
        if k in RK:
            by_min_l.setdefault(k[0], []).append(k)
    for r in sorted(rig, key=lambda r: int(r['submit_ms'])):
        k = key(r['symbol'], r['level'], int(r['decision_ts']), int(r['leg_idx']))
        if k in LK:
            by_min_r.setdefault(k[0], []).append(k)
    ordm = [m for m in by_min_l if by_min_l[m] != by_min_r.get(m)]
    le['order_minutes'] = len(by_min_l); le['order_mismatch'] = len(ordm)
    n_sc = sum(1 for k in LK if k[0] in sel_min and k[0] not in down)
    le['live_scorable_submits'] = n_sc
    s_le = INS if n_sc < 20 else (PASS if le['unexplained'] == 0 and not ordm else FAIL)
    # L-N theo phut
    lm = {k[0] for k in LK}; rm = {k[0] for k in RK}
    ln_bad = [m for m in (lm ^ rm) if m in sel_min and m not in down]
    ln_unexp = [m for m in ln_bad if not any(x['decision_ts'] == m and x['label'] != 'UNEXPLAINED' for x in labels)]
    s_ln = INS if not sel_min else (PASS if not ln_unexp else FAIL)
    # ---------------- L-S (bao s9.3) + L-S2
    fills = L('fill_stream.csv'); stops = L('fill_stop.csv'); tstops = L('time_stop.csv'); fund = L('funding.csv')
    buy = {r['cid']: r for r in fills if r['cid'].startswith('c3-')}
    sells = sorted([(int(r['log_ms']), r['symbol'], float(r['qty']), float(r['px'])) for r in stops]
                   + [(int(r['log_ms']), r['symbol'], float(r['qty']), float(r['avg'])) for r in fills if not r['cid'].startswith('c3-')])
    ls = {'n': 0, 'ok': 0, 'fail': [], 'no_px': 0, 'mark_source': 'mark' if a.mark else 'kline_proxy(DEV)'}
    openc = {}          # symbol -> list of (cid, qty_fill, avg, notional_log)
    realized = 0.0; fee_hi = 0.0; si = 0
    for r in sub:
        k = key(r['symbol'], r['level'], r['dts'], r['leg'])
        while si < len(sells) and sells[si][0] < r['t']:
            t, s, q, px = sells[si]; si += 1
            if s in openc:
                q0 = sum(x[1] for x in openc[s]); c0 = sum(x[1] * x[2] for x in openc[s])
                if q0 > 0:
                    realized += q * px - c0 * min(1.0, q / q0)
                    fee_hi += a.fee_max * q * px
                if q >= q0 - 1e-12:
                    openc.pop(s)
        if k[0] not in sel_min or k[0] in down:
            openc.setdefault(r['symbol'], []).append((r['cid'], float((buy.get(r['cid']) or {}).get('qty') or r['qty']),
                                                     float((buy.get(r['cid']) or {}).get('avg') or 0), float(r['notional'] or 0)))
            continue
        ls['n'] += 1
        bad = []
        # legIdx
        exp_leg = len(openc.get(r['symbol'], []))
        if r['leg'] != exp_leg:
            bad.append('legIdx %d != %d' % (r['leg'], exp_leg))
        # equity bao
        ulo = uhi = 0.0
        for s, legs in openc.items():
            q = sum(x[1] for x in legs); c = sum(x[1] * x[2] for x in legs)
            ms = [mark.get(s, k[0] - i * MIN) for i in (0, 1, 2)]
            ms = [m for m in ms if m]
            if not ms:
                continue
            lo, hi = min(m[2] for m in ms), max(m[1] for m in ms)
            ulo += q * lo - c; uhi += q * hi - c
        fsum = sum(abs(fnum(x.get('g3'), 0)) for x in fund if int(x['log_ms']) < r['t'])
        fee_open = a.fee_max * sum(x[1] * x[2] for v in openc.values() for x in v)
        E_lo = a.cap + realized - fee_hi - fee_open - fsum + ulo
        E_hi = a.cap + realized + fsum + uhi
        U = fnum(r['U_before'], 0.0)
        bb = RS.bao(a.cap, E_lo, E_hi, U, r['leg'], **K)
        b = float(r['budget'])
        if bb is None or not (bb[0] * (1 - 1e-5) <= b <= bb[1] * (1 + 1e-5)):
            bad.append('budget ngoai bao')
        sumn = sum((x[1] * x[2] if x[2] else x[3]) for v in openc.values() for x in v)   # margin = qty khop x gia khop (book)
        if U > 0:
            ci = sumn / U
            if not (min(a.cap, E_lo) * (1 - 1e-6) <= ci <= min(a.cap, E_hi) * (1 + 1e-6)):
                bad.append('U_before khong nhat quan')
        elif sumn > 0:
            bad.append('U_before=0 nhung co leg mo')
        q = float(r['qty']); nt = fnum(r['notional'])
        b0, b1 = bars.get(r['symbol'], k[0]), bars.get(r['symbol'], k[0] + MIN)
        bb_ = [x for x in (b0, b1) if x] if a.px_bars == 'union' else [x for x in (b0,) if x]
        br = (0, max(x[1] for x in bb_), min(x[2] for x in bb_), 0) if bb_ else None
        if nt and q > 0 and br:
            px = nt / q
            if not (br[2] * (1 - 1e-9) <= px <= br[1] * (1 + 1e-9)):
                bad.append('px ngam ngoai [low,high]')
            stp = step.get(r['symbol'])
            if stp and abs(RS.floor_to(b / px, stp) - q) > stp * 0.5:
                bad.append('qty != floor(budget/px, step)')
        else:
            ls['no_px'] += 1
        if bad:
            ls['fail'].append({'k': list(k), 'why': bad})
            lab('L-S', k, 'UNEXPLAINED', ';'.join(bad))
        else:
            ls['ok'] += 1
        openc.setdefault(r['symbol'], []).append((r['cid'], float((buy.get(r['cid']) or {}).get('qty') or r['qty']),
                                                 float((buy.get(r['cid']) or {}).get('avg') or 0), float(r['notional'] or 0)))
    s_ls = INS if ls['n'] < 20 else (PASS if ls['ok'] == ls['n'] else FAIL)
    rel = []
    for k in LK:
        if k in RK and k[0] in sel_min and k[0] not in down:
            bl, br_ = float(LK[k]['budget']), float(RK[k]['budget'])
            rel.append(abs(br_ - bl) / bl)
    ls2 = {'n': len(rel), 'max_rel': max(rel) if rel else None, 'share_le_5e-4': (sum(1 for x in rel if x <= 5e-4) / len(rel)) if rel else None,
           'n_gt_2e-3': sum(1 for x in rel if x > 2e-3)}
    s_ls2 = INS if len(rel) < 20 else (PASS if ls2['share_le_5e-4'] >= 0.9 and ls2['n_gt_2e-3'] == 0 else FAIL)
    # ---------------- L-P (bao cao)
    bps = []
    for r in sub:
        f = buy.get(r['cid']); br = bars.get(r['symbol'], r['dts'])
        if f and br and fnum(f['avg']):
            bps.append((float(f['avg']) / br[3] - 1) * 1e4)
    lp = {'n': len(bps), 'median_bps': statistics.median(bps) if bps else None,
          'p90_bps': sorted(bps)[int(0.9 * (len(bps) - 1))] if bps else None}
    lp['bao_owner_g_exec'] = bool(bps) and lp['median_bps'] > 30
    # ---------------- L-D
    ld_l = [k for k in LK if k[3] > 0 and k[0] in sel_min and k[0] not in down]
    ld_r = [k for k in RK if k[3] > 0]
    ok = sum(1 for k in ld_l if any(x[1] == k[1] and x[3] == k[3] and abs(x[0] - k[0]) <= MIN for x in ld_r))
    extra = sum(1 for k in ld_r if not any(x[1] == k[1] and x[3] == k[3] and abs(x[0] - k[0]) <= MIN for x in ld_l))
    s_ld = INS if not ld_l else (PASS if ok == len(ld_l) and extra == 0 else FAIL)
    ld = {'live': len(ld_l), 'rig': len(ld_r), 'match': ok, 'rig_extra': extra}
    # ---------------- L-T / L-SL / L-X (rig events)
    ev = rd(a.rig + '/events.csv')
    r_arm = {}
    for x in ev:
        if x['type'] == 'TRAIL_ARM':
            r_arm.setdefault(x['symbol'], []).append(int(x['ms']) // MIN * MIN)
    l_arm = {}
    for x in L('trail_arm.csv'):
        l_arm.setdefault(x['symbol'], []).append((int(x['log_ms']) // MIN * MIN, float(x['entry'])))

    def ref_arm(sym, entry, t0):
        for i in range(0, 3 * 1440):
            br = bars.get(sym, t0 + i * MIN)
            if br and br[1] >= entry * (1 + a.arm):
                return t0 + i * MIN
        return None
    lt = {'n': 0, 'same': 0, 'n8': 0, 'bad': 0, 'live_only': 0, 'rig_only': 0}
    for s, arms in l_arm.items():
        ra = r_arm.get(s, [])
        for i, (m, ent) in enumerate(arms):
            lt['n'] += 1
            if i >= len(ra):
                lt['live_only'] += 1; continue
            d = abs(ra[i] - m)
            if d == 0:
                lt['same'] += 1
            elif d <= 2 * MIN and ref_arm(s, ent, min(m, ra[i]) - 10 * MIN) in (m, ra[i]):
                lt['n8'] += 1; lab('L-T', (m, s, 'ARM', i), 'N8', 'REF-nhip phut %s' % ref_arm(s, ent, min(m, ra[i]) - 10 * MIN))
            else:
                lt['bad'] += 1; lab('L-T', (m, s, 'ARM', i), 'UNEXPLAINED', 'lech %d phut' % (d // MIN))
        lt['rig_only'] += max(0, len(ra) - len(arms))
    s_lt = INS if lt['n'] < 5 else (PASS if lt['same'] >= 0.9 * lt['n'] and lt['bad'] == 0 and lt['live_only'] == 0 and lt['rig_only'] == 0 else FAIL)
    r_sl = {}
    for x in ev:
        if x['type'] == 'TRAIL_STOP_PLACED':
            r_sl.setdefault(x['symbol'], []).append(float(x['value']))
    l_sl = {}
    for x in L('trail_stop.csv'):
        l_sl.setdefault(x['symbol'], []).append((float(x['stop']), x['mode'], int(x['log_ms'])))
    e4130 = {}
    for x in L('trail_4130.csv'):
        e4130.setdefault(x['symbol'], []).append(int(x['log_ms']))
    lsl = {'n': 0, 'ok': 0, 'bad': 0, 'mode_N7': 0, 'mode_bad': 0, 'pairing': 'rig dat gan nhat trong +-2 phut'}
    r_slt = {}
    for x in ev:
        if x['type'] == 'TRAIL_STOP_PLACED':
            r_slt.setdefault(x['symbol'], []).append((int(x['ms']), float(x['value'])))
    for s_, lst in l_sl.items():
        rr = r_slt.get(s_, [])
        for i, (px, mode, t) in enumerate(lst):
            lsl['n'] += 1
            cand = [z for z in rr if abs(z[0] - t) <= 2 * MIN]
            if not cand:
                lsl['bad'] += 1; lab('L-SL', (t // MIN * MIN, s_, 'STOP', i), 'UNEXPLAINED', 'rig khong dat stop trong +-2 phut'); continue
            rp = min(cand, key=lambda z: (abs(z[1] - px), abs(z[0] - t)))[1]
            tk = tick.get(s_, 0)
            if abs(px - rp) <= 2 * tk + 1e-12 or abs(px - rp) / rp <= 1e-3:
                lsl['ok'] += 1
            else:
                lsl['bad'] += 1; lab('L-SL', (t // MIN * MIN, s_, 'STOP', i), 'UNEXPLAINED', 'gia stop lech %.2e' % (abs(px - rp) / rp))
            if mode != 'closePosition':
                if any(x <= t for x in e4130.get(s_, [])):
                    lsl['mode_N7'] += 1; lab('L-SL', (t // MIN * MIN, s_, 'MODE', i), 'N7', '-4130 truoc do')
                else:
                    lsl['mode_bad'] += 1; lab('L-SL', (t // MIN * MIN, s_, 'MODE', i), 'UNEXPLAINED', 'mode khac khong co -4130')
    s_lsl = INS if lsl['n'] < 5 else (PASS if lsl['bad'] == 0 and lsl['mode_bad'] == 0 else FAIL)
    r_x = {}
    rf = rd(a.rig + '/fills.csv')
    tsr = {(x['symbol'], int(x['ms']) // MIN) for x in ev if x['type'] == 'TRAIL_TIME_STOP'}
    for x in rf:
        if x['side'] == 'SELL':
            m = int(x['ms']) // MIN
            r_x.setdefault(x['symbol'], []).append((m * MIN, float(x['price']), 'TIME_STOP' if any((x['symbol'], m - j) in tsr for j in (0, 1)) else 'TRAIL'))
    l_x = {}
    for x in stops:
        l_x.setdefault(x['symbol'], []).append((int(x['log_ms']) // MIN * MIN, float(x['px']), 'TRAIL'))
    for x in tstops:
        l_x.setdefault(x['symbol'], []).append((int(x['log_ms']) // MIN * MIN, None, 'TIME_STOP'))
    lx = {'n': 0, 'reason_ok': 0, 'same_min': 0, 'n8': 0, 'bad_min': 0, 'deltas': [], 'bad_px': 0}
    for s, lst in l_x.items():
        rr = sorted(r_x.get(s, []))
        for i, (m, px, why) in enumerate(sorted(lst, key=lambda z: z[0])):
            lx['n'] += 1
            if i >= len(rr):
                lab('L-X', (m, s, why, i), 'UNEXPLAINED', 'rig khong thoat'); continue
            if rr[i][2] == why:
                lx['reason_ok'] += 1
            else:
                lab('L-X', (m, s, why, i), 'UNEXPLAINED', 'ly do %s != rig %s' % (why, rr[i][2]))
            d = abs(rr[i][0] - m)
            if d == 0:
                lx['same_min'] += 1
            elif d <= 2 * MIN:
                lx['n8'] += 1; lab('L-X', (m, s, why, i), 'N8', 'lech %d phut (can REF-nhip xac nhan - A1)' % (d // MIN))
            else:
                lx['bad_min'] += 1; lab('L-X', (m, s, why, i), 'UNEXPLAINED', 'lech %d phut' % (d // MIN))
            if px is not None and rr[i][1]:
                dl = (px - rr[i][1]) / rr[i][1]; lx['deltas'].append(dl)
                if dl < -0.015 and abs(px - rr[i][1]) > 2 * tick.get(s, 0):
                    lx['bad_px'] += 1
    md = sum(lx['deltas']) / len(lx['deltas']) if lx['deltas'] else None
    lx['mean_delta'] = md; lx['deltas'] = len(lx['deltas'])
    s_lx = INS if lx['n'] < 5 else (PASS if lx['reason_ok'] == lx['n'] and lx['same_min'] >= 0.9 * lx['n'] and lx['bad_min'] == 0
                                    and md is not None and -0.008 <= md <= 0.002 and lx['bad_px'] == 0 else FAIL)
    # ---------------- L-K
    res = json.load(open(a.rig + '/result.json'))
    rl = open(a.rig + '/run.log', errors='replace').read()
    o4130 = [(int(x['log_ms']), x['symbol']) for x in L('order_4130.csv')]
    rep = sum(1 for (t, s) in o4130 if any(st[0] == s and 0 <= st[1] - t <= 20000 for st in
                                            [(x['symbol'], int(x['log_ms'])) for x in L('trail_stop.csv')]))
    lk = {'rig_errors': len(res.get('errors', [])), 'rig_latch': res.get('ks_any_latch'), 'rig_khan': rl.count('KHAN'),
          'live_4130': len(o4130), 'live_4130_replaced_le_2nhip': rep}
    s_lk = PASS if lk['rig_errors'] == 0 and not lk['rig_latch'] and lk['rig_khan'] == 0 and rep == len(o4130) else FAIL
    n8 = sum(1 for x in labels if x['label'] == 'N8'); n6 = sum(1 for x in labels if x['label'] == 'N6')
    clusters = sum(1 for k in LK if k[3] == 0)
    warn = []
    if clusters and n8 > 0.1 * clusters:
        warn.append('N8 > 10%% cum => tieu chi tuong ung FAIL'); s_lt = FAIL if any(x['item'] == 'L-T' and x['label'] == 'N8' for x in labels) else s_lt
        s_lx = FAIL if any(x['item'] == 'L-X' and x['label'] == 'N8' for x in labels) else s_lx
    if n6 > 3 or (rig and n6 > 0.1 * len(rig)):
        warn.append('N6 > 3 cum hoac > 10% SUBMIT rig => MASTER bao owner')
    out = {'window': [S, E], 'px_bars': a.px_bars, 'cap': a.cap, 'apply_ratio': a.apply_ratio, 'u_max': a.u_max, 'minutes_with_sel': len(sel_min), 'minutes_down_N3': len(down),
           'status': {'L-E': s_le, 'L-N': s_ln, 'L-S': s_ls, 'L-S2': s_ls2, 'L-D': s_ld, 'L-T': s_lt, 'L-SL': s_lsl, 'L-X': s_lx, 'L-K': s_lk},
           'L-E': le, 'L-N': {'minutes_diff': len(ln_bad), 'unexplained': len(ln_unexp)}, 'L-S': {k: v for k, v in ls.items() if k != 'fail'},
           'L-S_fail_n': len(ls['fail']), 'L-S2': ls2, 'L-P': lp, 'L-D': ld, 'L-T': lt, 'L-SL': lsl, 'L-X': lx, 'L-K': lk,
           'labels_n': {lb: sum(1 for x in labels if x['label'] == lb) for lb in LABELS + ('UNEXPLAINED',)}, 'warn': warn,
           'follow': bool(a.follow), 'dry': bool(a.dry)}
    json.dump(out, open(os.path.join(a.out, 'score.json'), 'w'), indent=1, default=str)
    with open(os.path.join(a.out, 'labels.csv'), 'w') as fh:
        w = csv.DictWriter(fh, fieldnames=['item', 'decision_ts', 'symbol', 'level', 'leg', 'label', 'evidence'], lineterminator='\n')
        w.writeheader(); w.writerows(labels)
    print(json.dumps(out['status']), json.dumps(out['labels_n']))


if __name__ == '__main__':
    main()
