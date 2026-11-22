#!/usr/bin/env python3
"""ADD24 R-LIVE bo cham (prereg s8, s9; ERRATA1 29152e39, ERRATA2 bb91e639 s4, ERRATA3 050912ca muc A).
L-E, L-N, L-S, L-S2, L-P (bao cao), L-D, L-T, L-SL, L-X, L-K + nhan N1-N9 tu dong. KHONG in / ghi gia, PnL, equity (chi lech tuong doi + dem).
Trang thai (ERRATA3 A1): >= 1 lech KHONG GIAI THICH => FAIL bat ke mau; INSUFFICIENT chi khi 0 lech khong giai thich VA mau < toi thieu.
Nhan (ERRATA3 A2/A3/A8/A10): N1 phut khong sel_dump; N2 live chan MINUTE-* ma tiem khong hieu luc; N3 dts co sel_dump nhung live KHONG co dong
tick "Btc ticker size .. -> dts" (CHI cho rig-co-live-khong); N4 lech "rig co cum, live khong co vi the" khi leg live CUNG (dts,symbol,legIdx)
co bang chung tu choi / het han / KHONG khop THEO CID; N5 day chuyen: lech goc co nhan N1-N4/N6/N9 xay ra TRUOC va (cung symbol hoac la lech
SUBMIT => doi U) VA L0-FOLLOW(-lite) khop live o khoa nay; N6 so giay; N7 -4130; N8 chi khi REF-nhip xac nhan phut; N9 EQ_UNAVAIL
[dts, dts+120 s). Muc cua mot cum ma CHINH cum (leg dau) da gan nhan => mang cung nhan (ke thua, ghi 'ke_thua') - gia dinh cho A1.
"""
import argparse, csv, gzip, json, logging, os, statistics, sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ref_size as RS

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger('score')
TZ7 = timezone(timedelta(hours=7))
MIN = 60000
PASS, FAIL, INS = 'PASS', 'FAIL', 'INSUFFICIENT'
LABELS = ('N1', 'N2', 'N3', 'N4', 'N5', 'N6', 'N7', 'N8', 'N9')
ROOT = ('N1', 'N2', 'N3', 'N4', 'N6', 'N9')
RISKS = ['trang thai sau restart JVM (peak trailing, quota) KHONG tai hien trong rig (ERRATA3 A11)',
         'bang chung N9 thua: dong positions() loi bi throttle 10 phut (C3MainEquity:153-158)',
         'K7 (availableBalance + margin) KHONG kiem phia live (chi dem dong CANH BAO ky quy)',
         'mau nho: R-LIVE ~1 ngay vao lenh', 'U_MAX = 0,60 (Configs.java:177) dua tren 242 khong dat SIM_U_MAX / TRADING_PROFILE (MASTER kiem)']


def ms7(s):
    return int(datetime.strptime(s, '%Y-%m-%d %H:%M').replace(tzinfo=TZ7).timestamp() * 1000)


def rd(p):
    if not p or not os.path.exists(p):
        return []
    f = gzip.open(p, 'rt') if p.endswith('.gz') else open(p)
    return list(csv.DictReader(f))


def fnum(x, d=None):
    try:
        return float(x)
    except (TypeError, ValueError):
        return d


def status(n_bad, n, nmin):
    """ERRATA3 A1."""
    if n_bad > 0:
        return FAIL
    return INS if n < nmin else PASS


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


def exit_kind(reason):
    r = (reason or '').upper()
    if 'X14' in r or '336' in r:
        return 'X14'
    if 'TIME' in r:
        return 'TIME_STOP'
    return 'TRAIL'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--live', required=True); ap.add_argument('--rig', required=True); ap.add_argument('--follow', default='')
    ap.add_argument('--fx', required=True); ap.add_argument('--mark', default='')
    ap.add_argument('--cap', type=float, default=1000.0); ap.add_argument('--start', required=True); ap.add_argument('--end', required=True)
    ap.add_argument('--apply-ratio', default='on', help='dev 11-05 dry (jar r4q, co TAT) = off')
    ap.add_argument('--u-max', type=float, default=0.6); ap.add_argument('--arm', type=float, default=0.07)
    ap.add_argument('--fee-max', type=float, default=0.0005); ap.add_argument('--out', required=True)
    ap.add_argument('--px-bars', default='union')
    ap.add_argument('--no-tick-check', action='store_true', help='CHI test tong hop: khong co tick_dts.csv => N3 tat')
    a = ap.parse_args()
    S, E = ms7(a.start), ms7(a.end)
    os.makedirs(a.out, exist_ok=True)
    K = dict(U_MAX=a.u_max) if a.apply_ratio == 'on' else dict(U_MAX=a.u_max, SCALE=1.0, W=(1.0, 1.0, 1.0, 1.0))
    L = lambda n: rd(os.path.join(a.live, n))
    inwin = lambda t: S <= t < E
    labels = []

    def lab(item, key, lb, ev):
        labels.append({'item': item, 'decision_ts': key[0], 'symbol': key[1], 'level': key[2], 'leg': key[3], 'label': lb, 'evidence': ev})
        return lb
    # ------------------------------------------------ dau vao
    sel_min = {int(r['ts']) for r in rd(a.fx + '/sel.csv.gz') if inwin(int(r['ts']))}
    tick_path = os.path.join(a.live, 'tick_dts.csv')
    tick = {int(r['dts']) for r in rd(tick_path)} if os.path.exists(tick_path) else None
    no_tick = (lambda d: False) if (tick is None or a.no_tick_check) else (lambda d: d not in tick)
    bars = Bars(a.fx + '/klines.csv.gz')
    mark = Bars(a.mark) if a.mark else bars
    step, tick_sz = exinfo(a.fx)
    sub = [r for r in L('submit.csv') if r['outcome'] == 'SUBMITTED']
    for r in sub:
        r['dts'] = int(r['cid'].split('-')[-2]) * MIN
        r['t'] = int(r['log_ms'])
        r['leg'] = int(r['legIdx']) if r.get('legIdx') else int(r['cid'].split('-')[-1])
    sub = [r for r in sub if inwin(r['dts'])]
    sub.sort(key=lambda r: r['t'])
    fill = {}   # cid -> (t, qty, avg) som nhat (stream / EXEC FILL / ACK gia)
    for n, qk, pk in (('fill_stream.csv', 'qty', 'avg'), ('exec_fill.csv', 'qty', 'avg'), ('exec_ack.csv', None, 'px')):
        for x in L(n):
            t = int(x['log_ms']); px = fnum(x.get(pk))
            if not px:
                continue
            q = fnum(x.get(qk)) if qk else None
            if x['cid'] not in fill or t < fill[x['cid']][0]:
                fill[x['cid']] = (t, q, px)
    rejected = {}
    for n in ('exec_khong_khop.csv', 'leg_khong_khop.csv', 'order_rejected.csv', 'order_expired.csv', 'tuchoi_cid.csv'):
        for x in L(n):
            rejected.setdefault(x['cid'], '%s %s' % (n[:-4], x['log_ms']))
    skips = [(int(r['log_ms']), r.get('symbol', '')) for n in ('skip_paper.csv', 'skip_paper2.csv') for r in L(n)]
    blk = {(int(r['decision_ts']), r['symbol'], r['level']) for r in L('block.csv')}
    equn = [int(r['log_ms']) for r in L('eq_unavail.csv')]
    closes = sorted([(int(x['log_ms']), x['symbol'], x['reason'], fnum(x['exitAvg']), fnum(x['realized'], 0.0), fnum(x['fee'], 0.0))
                     for x in L('book_close.csv')])
    rig = [r for r in rd(a.rig + '/legs.csv') if r['outcome'] == 'SUBMITTED' and inwin(int(r['decision_ts']))]
    fol = [r for r in rd(a.follow + '/legs.csv') if r['outcome'] == 'SUBMITTED'] if a.follow else None
    key = lambda s, lv, d, lg: (d, s, lv, lg)
    LK = {key(r['symbol'], r['level'], r['dts'], r['leg']): r for r in sub}
    RK = {key(r['symbol'], r['level'], int(r['decision_ts']), int(r['leg_idx'])): r for r in rig}
    FK = {key(r['symbol'], r['level'], int(r['decision_ts']), int(r['leg_idx'])) for r in fol} if fol is not None else None
    # ------------------------------------------------ L-E / L-N (+ nhan)
    roots = []          # (dts, symbol, is_submit_level, label)
    le = {'live_submits': len(sub), 'rig_submits': len(rig), 'matched': 0, 'unexplained': 0, 'by_label': {}}
    cl_label = {}       # (symbol, dts leg0) -> nhan cua cum (ke thua)
    for k in sorted(set(LK) | set(RK)):
        if k in LK and k in RK:
            le['matched'] += 1
            continue
        side = 'live_only' if k in LK else 'rig_only'
        it = 'L-E ' + side
        if k[0] not in sel_min:
            lb = lab(it, k, 'N1', 'khong co sel_dump phut nay')
        elif side == 'rig_only' and no_tick(k[0]):
            lb = lab(it, k, 'N3', 'live khong co dong tick "Btc ticker size .. -> dts"')
        elif side == 'rig_only' and any(x[1] == k[1] and x[0] // MIN * MIN in (k[0], k[0] + MIN) for x in skips):
            lb = lab(it, k, 'N6', 'skip so giay cung phut + symbol')
        elif side == 'rig_only' and any(k[0] <= t < k[0] + 2 * MIN for t in equn):
            lb = lab(it, k, 'N9', "EQ_UNAVAIL positions() loi trong [dts, dts+120 s)")
        elif side == 'rig_only' and ((k[0], k[1], k[2]) in blk or (k[0], '*', '*') in blk or (k[0], k[1], '*') in blk):
            lb = lab(it, k, 'N2', 'live chan MINUTE-* nhung tiem khong hieu luc')
        elif FK is not None and ((k in FK) == (k in LK)) and any(r[0] < k[0] and (r[1] == k[1] or r[2]) for r in roots):
            r0 = [r for r in roots if r[0] < k[0] and (r[1] == k[1] or r[2])][0]
            lb = lab(it, k, 'N5', 'goc %s %s@%d; L0-FOLLOW khop live o khoa nay' % (r0[3], r0[1], r0[0]))
        else:
            lb = lab(it, k, 'UNEXPLAINED', '')
            le['unexplained'] += 1
        if lb in ROOT:
            roots.append((k[0], k[1], True, lb))
        if k[3] == 0:
            cl_label[(k[1], k[0])] = lb
        le['by_label'][lb] = le['by_label'].get(lb, 0) + 1
    by_l, by_r = {}, {}
    for r in sub:
        k = key(r['symbol'], r['level'], r['dts'], r['leg'])
        if k in RK:
            by_l.setdefault(k[0], []).append(k)
    for r in sorted(rig, key=lambda r: int(r['submit_ms'])):
        k = key(r['symbol'], r['level'], int(r['decision_ts']), int(r['leg_idx']))
        if k in LK:
            by_r.setdefault(k[0], []).append(k)
    ordm = [m for m in by_l if by_l[m] != by_r.get(m)]
    le['order_minutes'] = len(by_l); le['order_mismatch'] = len(ordm)
    n_sc = sum(1 for k in LK if k[0] in sel_min)
    le['live_scorable_submits'] = n_sc
    s_le = status(le['unexplained'] + len(ordm), n_sc, 20)
    lm = {k[0] for k in LK}; rm = {k[0] for k in RK}
    ln_bad = [m for m in (lm ^ rm) if m in sel_min]
    ln_unexp = [m for m in ln_bad if any(x['decision_ts'] == m and x['label'] == 'UNEXPLAINED' and x['item'].startswith('L-E') for x in labels)]
    s_ln = status(len(ln_unexp), len(sel_min), 1)

    # cum live: symbol -> list cum {legs, t0, close}
    def live_clusters():
        out, openc = [], {}
        ev = [(r['t'], 0, r) for r in sub] + [(c[0], 1, c) for c in closes]
        for t, kind, x in sorted(ev, key=lambda z: (z[0], z[1])):
            if kind == 0:
                c = openc.get(x['symbol'])
                if c is None:
                    c = {'symbol': x['symbol'], 'dts0': x['dts'], 'legs': [], 'close': None}
                    openc[x['symbol']] = c; out.append(c)
                c['legs'].append(x)
            else:
                c = openc.pop(x[1], None)
                if c is not None:
                    c['close'] = x
        return out
    LC = live_clusters()

    def cl_of(sym, t):
        for c in LC:
            if c['symbol'] == sym and c['legs'][0]['t'] <= t + 2 * MIN and (c['close'] is None or t <= c['close'][0] + 2 * MIN):
                return c
        return None

    def inherit(sym, t):
        """nhan ke thua cua cum: cum live leg0 bi tu choi (N4 theo cid) hoac cum rig thua da gan nhan."""
        c = cl_of(sym, t)
        if c is not None:
            cid0 = c['legs'][0]['cid']
            if cid0 in rejected:
                return 'N4', 'leg dau %s tu choi/het han/KHONG khop (%s)' % (cid0, rejected[cid0])
        for (s, d0), lb in cl_label.items():
            if s == sym and d0 <= t and lb in LABELS:
                return lb, 'ke_thua cum %s@%d (%s)' % (s, d0, lb)
        return None, ''
    # ------------------------------------------------ L-S (bao s9.3, margin PENDING nhu Java - ERRATA3 A7)
    fund = L('funding.csv')
    ls = {'n': 0, 'ok': 0, 'fail': 0, 'ins_no_px': 0, 'mark_source': 'mark' if a.mark else 'kline_proxy(DEV)'}
    for r in sub:
        k = key(r['symbol'], r['level'], r['dts'], r['leg'])
        if k[0] not in sel_min:
            continue
        t = r['t']
        openl, realized, fee_closed_hi = [], 0.0, 0.0
        for c in LC:
            if c['legs'][0]['t'] >= t:
                continue
            if c['close'] is not None and c['close'][0] < t:
                realized += c['close'][4] - c['close'][5]          # realized - phi (LiveBookC3:737; C3MainEquity:138)
                continue
            for x in c['legs']:
                if x['t'] < t:
                    openl.append(x)
        exp_leg = sum(1 for x in openl if x['symbol'] == r['symbol'])
        bad = []
        if r['leg'] != exp_leg:
            bad.append('legIdx %d != %d' % (r['leg'], exp_leg))
        marg, ulo, uhi, fee_open = 0.0, 0.0, 0.0, 0.0
        for x in openl:
            f = fill.get(x['cid']); nt = fnum(x['notional'], 0.0); q = fnum(x['qty'], 0.0)
            if f and f[0] < t:
                qq = f[1] if f[1] else q; marg += qq * f[2]; avg = f[2]
            else:
                qq = q; marg += nt; avg = (nt / q) if q else 0.0    # PENDING = notional sizing (LiveBookC3:416-420); khong avg = 0
            fee_open += a.fee_max * qq * avg
            ms = [mark.get(x['symbol'], k[0] + i * MIN) for i in (-2, -1, 0, 1)]     # ERRATA3 A10: gom nen dts+1
            ms = [m for m in ms if m]
            if ms:
                ulo += qq * (min(m[2] for m in ms) - avg); uhi += qq * (max(m[1] for m in ms) - avg)
        fl = [fnum(x.get('cum'), 0) for x in fund if int(x['log_ms']) < t]
        fsum = abs(fl[-1]) if fl else 0.0
        E_lo = a.cap + realized - fee_closed_hi - fee_open - fsum + ulo
        E_hi = a.cap + realized + fsum + uhi
        U = fnum(r['U_before'], 0.0)
        bb = RS.bao(a.cap, E_lo, E_hi, U, r['leg'], **K)
        b = float(r['budget'])
        if bb is None or not (bb[0] * (1 - 1e-5) <= b <= bb[1] * (1 + 1e-5)):
            bad.append('budget ngoai bao')
        if U > 0:
            ci = marg / U
            if not (min(a.cap, E_lo) * (1 - 1e-6) <= ci <= min(a.cap, E_hi) * (1 + 1e-6)):
                bad.append('U_before khong nhat quan')
        elif marg > 0:
            bad.append('U_before=0 nhung co margin')
        q = fnum(r['qty'], 0.0); nt = fnum(r['notional'])
        b0, b1 = bars.get(r['symbol'], k[0]), bars.get(r['symbol'], k[0] + MIN)
        bb_ = [x for x in (b0, b1) if x] if a.px_bars == 'union' else [x for x in (b0,) if x]
        if not (nt and q > 0 and bb_):
            ls['ins_no_px'] += 1                                   # ERRATA3 A10: no_px => leg INSUFFICIENT
            continue
        ls['n'] += 1
        px = nt / q
        if not (min(x[2] for x in bb_) * (1 - 1e-9) <= px <= max(x[1] for x in bb_) * (1 + 1e-9)):
            bad.append('px ngam ngoai [low,high]')
        stp = step.get(r['symbol'])
        if stp and abs(RS.floor_to(b / px, stp) - q) > stp * 0.5:
            bad.append('qty != floor(budget/px, step)')
        if bad:
            ls['fail'] += 1; lab('L-S', k, 'UNEXPLAINED', ';'.join(bad))
        else:
            ls['ok'] += 1
    s_ls = status(ls['fail'], ls['n'], 20)
    rel = []
    for k in LK:
        if k in RK and k[0] in sel_min:
            bl, br_ = float(LK[k]['budget']), float(RK[k]['budget'])
            rel.append(abs(br_ - bl) / bl)
    ls2 = {'n': len(rel), 'max_rel': max(rel) if rel else None,
           'share_le_5e-4': (sum(1 for x in rel if x <= 5e-4) / len(rel)) if rel else None, 'n_gt_2e-3': sum(1 for x in rel if x > 2e-3)}
    s_ls2 = status(ls2['n_gt_2e-3'] + (1 if rel and ls2['share_le_5e-4'] < 0.9 else 0), len(rel), 20)
    # ------------------------------------------------ L-P (bao cao)
    bps = []
    for r in sub:
        f = fill.get(r['cid']); br = bars.get(r['symbol'], r['dts'])
        if f and br:
            bps.append((f[2] / br[3] - 1) * 1e4)
    lp = {'n': len(bps), 'median_bps': statistics.median(bps) if bps else None, 'p90_bps': sorted(bps)[int(0.9 * (len(bps) - 1))] if bps else None}
    lp['bao_owner_g_exec'] = bool(bps) and lp['median_bps'] > 30

    def two_way(item, lst_l, lst_r, tol, extra_ok=None):
        """ghep 2 chieu theo symbol, thu tu thoi gian; tra (cap, live_thua, rig_thua)."""
        pairs, lo, ro = [], [], []
        syms = set(s for s, *_ in lst_l) | set(s for s, *_ in lst_r)
        for s in syms:
            A_ = sorted([x for x in lst_l if x[0] == s], key=lambda z: z[1]); B_ = sorted([x for x in lst_r if x[0] == s], key=lambda z: z[1])
            used = set()
            for x in A_:
                c = [j for j, y in enumerate(B_) if j not in used and abs(y[1] - x[1]) <= tol]
                if c:
                    j = min(c, key=lambda j: abs(B_[j][1] - x[1])); used.add(j); pairs.append((x, B_[j]))
                else:
                    lo.append(x)
            ro += [y for j, y in enumerate(B_) if j not in used]
        return pairs, lo, ro

    def unexp_or_inherit(item, sym, t, what):
        lb, ev = inherit(sym, t)
        if lb:
            lab(item, (t // MIN * MIN, sym, what, -1), lb, ev); return 0
        lab(item, (t // MIN * MIN, sym, what, -1), 'UNEXPLAINED', what); return 1
    # ------------------------------------------------ L-D (DCA: bac = level + legIdx, phut +-1, hai chieu)
    dl = [(k[1], k[0], k[2], k[3]) for k in LK if k[3] > 0 and k[0] in sel_min]
    dr = [(k[1], k[0], k[2], k[3]) for k in RK if k[3] > 0]
    pairs, lo, ro = two_way('L-D', dl, dr, MIN)
    ld_bad = sum(1 for x, y in pairs if x[2] != y[2] or x[3] != y[3])
    for x, y in pairs:
        if x[2] != y[2] or x[3] != y[3]:
            lab('L-D', (x[1], x[0], x[2], x[3]), 'UNEXPLAINED', 'bac/legIdx rig %s/%d' % (y[2], y[3]))
    ld_bad += sum(unexp_or_inherit('L-D live_only', x[0], x[1], 'DCA') for x in lo) + sum(unexp_or_inherit('L-D rig_only', y[0], y[1], 'DCA') for y in ro)
    ld = {'live': len(dl), 'rig': len(dr), 'pairs': len(pairs), 'live_only': len(lo), 'rig_only': len(ro), 'bad': ld_bad}
    s_ld = status(ld_bad, len(dl), 1)
    # ------------------------------------------------ L-T (arm, hai chieu, N8 chi REF-nhip)
    ev = rd(a.rig + '/events.csv')
    arm_l = [(x['symbol'], int(x['log_ms']) // MIN * MIN, float(x['entry'])) for x in L('trail_arm.csv')]
    arm_r = [(x['symbol'], int(x['ms']) // MIN * MIN, None) for x in ev if x['type'] == 'TRAIL_ARM']

    def ref_arm(sym, entry, t0, t1):
        for i in range(0, (t1 - t0) // MIN + 1):
            br = bars.get(sym, t0 + i * MIN)
            if br and br[1] >= entry * (1 + a.arm):
                return t0 + i * MIN
        return None
    pairs, lo, ro = two_way('L-T', arm_l, arm_r, 5 * MIN)
    lt = {'n_live': len(arm_l), 'n_rig': len(arm_r), 'same': 0, 'n8': 0, 'bad': 0}
    for x, y in pairs:
        if x[1] == y[1]:
            lt['same'] += 1; continue
        d = abs(x[1] - y[1]); rm_ = ref_arm(x[0], x[2], min(x[1], y[1]) - 3 * MIN, max(x[1], y[1]))
        if d <= 2 * MIN and rm_ in (x[1], y[1]):
            lt['n8'] += 1; lab('L-T', (x[1], x[0], 'ARM', -1), 'N8', 'REF-nhip phut %s' % rm_)
        else:
            lt['bad'] += 1; lab('L-T', (x[1], x[0], 'ARM', -1), 'UNEXPLAINED', 'lech %d phut, REF %s' % (d // MIN, rm_))
    lt['bad'] += sum(unexp_or_inherit('L-T live_only', x[0], x[1], 'ARM') for x in lo) + sum(unexp_or_inherit('L-T rig_only', y[0], y[1], 'ARM') for y in ro)
    lt['live_only'], lt['rig_only'] = len(lo), len(ro)
    s_lt = status(lt['bad'], len(arm_l), 5)
    if len(arm_l) >= 5 and lt['same'] < 0.9 * len(arm_l):       # prereg s9: >= 90 % cung phut
        s_lt = FAIL
    # ------------------------------------------------ L-SL (gia stop hai chieu +-2', co stop sau arm, kieu + N7)
    sl_l = [(x['symbol'], int(x['log_ms']), float(x['stop']), x['mode']) for x in L('trail_stop.csv')]
    sl_r = [(x['symbol'], int(x['ms']), float(x['value']), 'closePosition') for x in ev if x['type'] == 'TRAIL_STOP_PLACED']
    e4130 = {}
    for x in L('trail_4130.csv'):
        e4130.setdefault(x['symbol'], []).append(int(x['log_ms']))
    lsl = {'n_live': len(sl_l), 'n_rig': len(sl_r), 'ok': 0, 'bad': 0, 'mode_N7': 0, 'arm_no_stop': 0}
    pairs, lo, ro = [], [], []
    for s in set(x[0] for x in sl_l) | set(x[0] for x in sl_r):
        A_ = [x for x in sl_l if x[0] == s]; B_ = [x for x in sl_r if x[0] == s]; usedB = set()
        for x in A_:
            c = [j for j, y in enumerate(B_) if abs(y[1] - x[1]) <= 2 * MIN]
            if not c:
                lo.append(x); continue
            j = min(c, key=lambda j: (abs(B_[j][2] - x[2]), abs(B_[j][1] - x[1]))); usedB.add(j); pairs.append((x, B_[j]))
        ro += [y for j, y in enumerate(B_) if j not in usedB and not any(abs(y[1] - x[1]) <= 2 * MIN for x in A_)]
    for x, y in pairs:
        tk = tick_sz.get(x[0], 0)
        if abs(x[2] - y[2]) <= 2 * tk + 1e-12 or abs(x[2] - y[2]) / y[2] <= 1e-3:
            lsl['ok'] += 1
        else:
            lsl['bad'] += 1; lab('L-SL', (x[1] // MIN * MIN, x[0], 'STOP', -1), 'UNEXPLAINED', 'gia stop lech %.2e' % (abs(x[2] - y[2]) / y[2]))
        if x[3] != 'closePosition':
            if any(t <= x[1] for t in e4130.get(x[0], [])):
                lsl['mode_N7'] += 1; lab('L-SL', (x[1] // MIN * MIN, x[0], 'MODE', -1), 'N7', '-4130 truoc do')
            else:
                lsl['bad'] += 1; lab('L-SL', (x[1] // MIN * MIN, x[0], 'MODE', -1), 'UNEXPLAINED', 'kieu khac khong co -4130')
    lsl['bad'] += sum(unexp_or_inherit('L-SL live_only', x[0], x[1], 'STOP') for x in lo) + sum(unexp_or_inherit('L-SL rig_only', y[0], y[1], 'STOP') for y in ro)
    for (s, t, _) in arm_l:
        if not any(x[0] == s and t - MIN <= x[1] <= t + 3 * MIN for x in sl_l):
            lsl['arm_no_stop'] += 1; lab('L-SL', (t, s, 'ARM_NO_STOP', -1), 'UNEXPLAINED', 'live arm khong co stop c3s- sau arm')
    rarm_ms = [(x['symbol'], int(x['ms'])) for x in ev if x['type'] == 'TRAIL_ARM']
    for (s, t) in rarm_ms:
        if not any(y[0] == s and t - MIN <= y[1] <= t + 3 * MIN for y in sl_r):
            lsl['arm_no_stop'] += 1; lab('L-SL', (t // MIN * MIN, s, 'RIG_ARM_NO_STOP', -1), 'UNEXPLAINED', 'rig arm khong co stop sau arm')
    lsl['bad'] += lsl['arm_no_stop']; lsl['live_only'], lsl['rig_only'] = len(lo), len(ro)
    s_lsl = status(lsl['bad'], len(sl_l), 5)
    # ------------------------------------------------ L-X (thoat hai chieu; cum con giu tai T_cut)
    x_l = [(c[1], c[0] // MIN * MIN, exit_kind(c[2]), c[3]) for c in closes if inwin(c[0])]
    if not closes:   # khong co dong dong cum (log cu) => dung dong stop khop / TIME-STOP
        x_l = [(x['symbol'], int(x['log_ms']) // MIN * MIN, 'TRAIL', fnum(x['px'])) for x in L('fill_stop.csv')] + \
              [(x['symbol'], int(x['log_ms']) // MIN * MIN, 'TIME_STOP', None) for x in L('time_stop.csv')]
    tsr = {(x['symbol'], int(x['ms']) // MIN) for x in ev if x['type'] == 'TRAIL_TIME_STOP'}
    x_r = []
    for x in rd(a.rig + '/fills.csv'):
        if x['side'] == 'SELL':
            m = int(x['ms']) // MIN
            x_r.append((x['symbol'], m * MIN, 'TIME_STOP' if any((x['symbol'], m - j) in tsr for j in (0, 1)) else 'TRAIL', float(x['price'])))
    # gop nhieu khop ban cung symbol + phut thanh 1 thoat
    def merge(lst):
        d = {}
        for s, m, k, p in lst:
            d.setdefault((s, m), (s, m, k, p))
        return list(d.values())
    x_l, x_r = merge(x_l), merge(x_r)
    pairs, lo, ro = two_way('L-X', x_l, x_r, 30 * MIN)
    stops_l = sorted(sl_l, key=lambda z: z[1])

    def ref_exit(sym, t_from, t_to):
        st = [x for x in stops_l if x[0] == sym and x[1] <= t_to]
        if not st:
            return None
        sp = st[-1][2]
        for i in range(0, (t_to - t_from) // MIN + 3):
            br = bars.get(sym, t_from + i * MIN)
            if br and br[2] <= sp:
                return t_from + i * MIN
        return None
    lx = {'n_live': len(x_l), 'n_rig': len(x_r), 'reason_ok': 0, 'same_min': 0, 'n8': 0, 'bad': 0, 'deltas': []}
    for x, y in pairs:
        if x[2] == y[2]:
            lx['reason_ok'] += 1
        else:
            lx['bad'] += 1; lab('L-X', (x[1], x[0], x[2], -1), 'UNEXPLAINED', 'ly do %s != rig %s' % (x[2], y[2]))
        d = abs(x[1] - y[1])
        if d == 0:
            lx['same_min'] += 1
        else:
            rm_ = ref_exit(x[0], min(x[1], y[1]) - 3 * MIN, max(x[1], y[1])) if x[2] == 'TRAIL' else None
            if d <= 2 * MIN and rm_ in (x[1], y[1]):
                lx['n8'] += 1; lab('L-X', (x[1], x[0], x[2], -1), 'N8', 'REF-nhip phut %s' % rm_)
            else:
                lx['bad'] += 1; lab('L-X', (x[1], x[0], x[2], -1), 'UNEXPLAINED', 'lech %d phut, REF %s' % (d // MIN, rm_))
        if x[2] == 'TRAIL' and x[3] and y[3]:
            dl_ = (x[3] - y[3]) / y[3]; lx['deltas'].append(dl_)
            if dl_ < -0.015 and abs(x[3] - y[3]) > 2 * tick_sz.get(x[0], 0):
                lx['bad'] += 1; lab('L-X', (x[1], x[0], 'PX', -1), 'UNEXPLAINED', 'gia thoat lech %.2e' % dl_)
    lx['bad'] += sum(unexp_or_inherit('L-X live_only', x[0], x[1], 'EXIT') for x in lo) + sum(unexp_or_inherit('L-X rig_only (live con giu)', y[0], y[1], 'EXIT') for y in ro)
    md = sum(lx['deltas']) / len(lx['deltas']) if lx['deltas'] else None
    lx['mean_delta'] = md; lx['deltas'] = len(lx['deltas']); lx['live_only'], lx['rig_only'] = len(lo), len(ro)
    if md is not None and not (-0.008 <= md <= 0.002):
        lx['bad'] += 1
    s_lx = status(lx['bad'], len(x_l), 5)
    if len(x_l) >= 5 and lx['same_min'] < 0.9 * len(x_l):       # prereg s9: >= 90 % cung phut
        s_lx = FAIL
    # ------------------------------------------------ L-K
    res = json.load(open(a.rig + '/result.json'))
    rl = open(a.rig + '/run.log', errors='replace').read()
    o4130 = [(int(x['log_ms']), x['symbol']) for x in L('order_4130.csv')]
    rep_ = sum(1 for (t, s) in o4130 if any(y[0] == s and 0 <= y[1] - t <= 20000 for y in sl_l))
    lk = {'rig_errors': len(res.get('errors', [])), 'rig_latch': res.get('ks_any_latch'), 'rig_khan': rl.count('KHAN'),
          'live_4130': len(o4130), 'live_4130_replaced_le_2nhip': rep_}
    s_lk = PASS if lk['rig_errors'] == 0 and not lk['rig_latch'] and lk['rig_khan'] == 0 and rep_ == len(o4130) else FAIL
    # ------------------------------------------------ gioi han nhan
    warn = []
    n8 = sum(1 for x in labels if x['label'] == 'N8'); n6 = sum(1 for x in labels if x['label'] == 'N6')
    n9 = len({x['decision_ts'] for x in labels if x['label'] == 'N9'})
    clusters = len(LC)
    if clusters and n8 > 0.1 * clusters:
        warn.append('N8 > 10% cum => L-T/L-X FAIL')
        if any(x['item'] == 'L-T' and x['label'] == 'N8' for x in labels):
            s_lt = FAIL
        if any(x['item'] == 'L-X' and x['label'] == 'N8' for x in labels):
            s_lx = FAIL
    if n6 > 3 or (rig and n6 > 0.1 * len(rig)):
        warn.append('N6 > 3 cum hoac > 10% SUBMIT rig => MASTER bao owner')
    if n9 > 2:
        warn.append('N9 > 2 phut-SUBMIT => MASTER bao owner (loi doc equity chan lenh that)')
    st = {'L-E': s_le, 'L-N': s_ln, 'L-S': s_ls, 'L-S2': s_ls2, 'L-D': s_ld, 'L-T': s_lt, 'L-SL': s_lsl, 'L-X': s_lx, 'L-K': s_lk}
    out = {'window': [S, E], 'px_bars': a.px_bars, 'cap': a.cap, 'apply_ratio': a.apply_ratio, 'u_max': a.u_max,
           'u_max_source': 'Configs.java:177 U_MAX=0.60f; :924 SIM_U_MAX (242 khong dat; TRADING_PROFILE 0 lan - ERRATA2 s4)',
           'minutes_with_sel': len(sel_min), 'tick_minutes': (len(tick) if tick is not None else None), 'status': st,
           'L-E': le, 'L-N': {'minutes_diff': len(ln_bad), 'unexplained': len(ln_unexp)}, 'L-S': ls, 'L-S2': ls2, 'L-P': lp, 'L-D': ld,
           'L-T': lt, 'L-SL': lsl, 'L-X': lx, 'L-K': lk, 'clusters_live': clusters,
           'labels_n': {lb: sum(1 for x in labels if x['label'] == lb) for lb in LABELS + ('UNEXPLAINED',)}, 'N9_phut': n9, 'warn': warn,
           'follow': bool(a.follow), 'rui_ro_A11': RISKS}
    json.dump(out, open(os.path.join(a.out, 'score.json'), 'w'), indent=1, default=str)
    with open(os.path.join(a.out, 'labels.csv'), 'w') as fh:
        w = csv.DictWriter(fh, fieldnames=['item', 'decision_ts', 'symbol', 'level', 'leg', 'label', 'evidence'], lineterminator='\n')
        w.writeheader(); w.writerows(labels)
    print(json.dumps(st), json.dumps(out['labels_n']))


if __name__ == '__main__':
    main()
