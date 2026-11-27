"""LEVZ B4 exit engine (PREREG_X3_1127 A2-A3) on 1-minute CLOSE, same path / funding / gap conventions as B1 exits.py (imported).
Path minute i (0..43200) = close of 1m bar open T_k + i min (ffilled, B1 path_of). Budget of one slot = 1 (normalised), held WHOLE from
the entry; n_add + 1 legs of notional N = 1 / (1 + n_add) each. Leg 0 = E0 entry at p0 = path[0] (fee 0.07 %). Add-leg l (1..n_add):
resting limit at L_l = p0 (1 + a l); filled at the first minute i >= 1 (i < nv, i <= exit minute) with close >= L_l (1 - 1e-12)
(float tolerance) at EXACTLY L_l
(fee 0.07 %). Average cost = sum N / sum (N / L) over filled legs (quantity-weighted mean price).
Order inside a minute i (CHOICES_B4): (1) limit fills, (2) SL: close >= avg (1 + s) -> close all at close x 1.003, (3) trailing
(arm a / gap g from avg): armed at the first i >= 1 with close <= avg_i (1 - a); trough = min close since arming; exit at the first
i > i_a with close >= trough(i-1) (1 + g) at close x 1.001 (B1 rule: arming and exit never in the same minute; arming persists when a
later leg fills), (4) STATE (T1: first h >= 1 with finalised W7 row k + h: z_oi < 0 or z_f < 0 or f <= 0.0001 -> close at minute
60 h), (5) TIME minute 60 H, (6) MISS (B1). EOD at nv - 1 if nothing. Priority on the same minute: SL > TRAIL > STATE > TIME > MISS.
Funding (B1 convention): boundary h is paid on a leg iff the leg filled at minute f < 60 h - 1 and the position is still open
(60 h - 1 <= j); amount per budget = N (p0 / L) fh[h] (fh = B1 funding per p0-notional).
Port mapping (no change to port.py): per budget, xr_eff = sum_filled N X / L + N (n_add - nf) (1 - FEE) / (1 + FEE), fund_eff as above
=> port net / N = 1 - xr_eff - FEE (1 + xr_eff) + fund_eff == DCA net per budget exactly (unfilled budget earns 0). Hourly arrays per
DCA kind: minute mark mkm[i] = N (n_add - cnt_i) (1 - FEE) + sum_{filled <= i} N p[i] / L  (port MTM 1 - mk - FEE = true MTM incl.
leg fees), mk[h] = mkm[60 h], hm[h] = max mkm over (60(h-1), 60h], fh_eff[h]; mx = max mkm[0..j], mxh = max mkm over exit window.
n_add = 0 reduces to B1 / T1 bit-for-bit (test a). Extra cols: nleg, avg (avg cost / p0 at exit), xraw (X / p0), retb (net per
budget computed directly), worst = min(1 - FEE - mx, retb) (worst MTM per budget incl. entry fees, funding ignored intra-trade).
usage: python3 code/exits_b4.py all   (real W7_E0 union candidates -> work/exits_b4.npz + work/hourly_b4_<kind>.npz; hygiene only)"""
import os
import sys
import time
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common_b4 as C
sys.path.pop(0)
import numpy as np

log = C.setup_log('exits')
CB = C.CB
XB1 = C.b1('exits')
BIG = C.BIG
assert BIG == XB1.BIG
FEE = C.FEE
KEYS = ('j', 'rs', 'rt', 'xr', 'fund', 'mx', 'mxh', 'flag', 'nleg', 'avg', 'xraw', 'retb', 'worst')
DK = C.DNAMES[1:]                    # DCA kinds with their own hourly arrays (NONE = B1 hourly)
KIND = {d[0]: (d[1], d[2]) for d in C.DCAS}


def first_ge(p, s, e, lvl):
    if s >= e:
        return BIG
    m = p[s:e] >= lvl
    x = int(np.argmax(m))
    return s + x if m[x] else BIG


def first_le(p, s, e, lvl):
    if s >= e:
        return BIG
    m = p[s:e] <= lvl
    x = int(np.argmax(m))
    return s + x if m[x] else BIG


class Kind:
    """per (candidate, DCA kind): fill minutes, levels, minute mark, hourly arrays."""
    def __init__(self, p, nv, fh, n, a):
        self.n, self.a = n, a
        p0 = p[0]
        self.N = N = 1.0 / (1 + n)
        cmax = np.maximum.accumulate(p[1:nv]) if nv > 1 else np.zeros(0)
        self.f, self.L = [], []
        for l in range(1, n + 1):
            lv = p0 * (1.0 + a * l)
            i = int(np.searchsorted(cmax, lv * (1.0 - C.LIM_TOL), 'left')) + 1     # close >= level (float tolerance, MASTER)
            self.f.append(i if i < nv else BIG)
            self.L.append(lv)
        mkm = N * (p / p0)
        if n > 0:
            cnt = np.zeros(len(p))
            for f, L in zip(self.f, self.L):
                if f < BIG:
                    mkm[f:] += N * (p[f:] / L)
                    cnt[f:] += 1.0
            mkm += N * (n - cnt) * (1.0 - FEE)
        self.mkm = mkm
        self.cmx = np.maximum.accumulate(mkm)
        self.rmh = np.maximum.accumulate(mkm[1:].reshape(CB.HMAX, 60), axis=1).ravel()
        hh = np.arange(CB.HMAX + 1)
        w = np.full(CB.HMAX + 1, N)
        for f, L in zip(self.f, self.L):
            w = w + np.where(f < 60 * hh - 1, N * (p0 / L), 0.0)
        self.fh = fh * w if n > 0 else fh * 1.0
        self.fc = np.concatenate([[0.0], np.cumsum(self.fh[1:])])
        self.mk = mkm[::60].copy()
        self.hm = np.concatenate([[mkm[0]], mkm[1:].reshape(CB.HMAX, 60).max(axis=1)])
        # segments (start, end, avg) in time order
        self.segs = []
        qty = N / p0
        starts = [1] + self.f
        ends = self.f + [nv]
        for m in range(n + 1):
            if m >= 1:
                qty = qty + N / self.L[m - 1]
            st, en = starts[m], min(ends[m], nv)
            if st >= BIG or st >= nv:
                break
            avg = p0 if m == 0 else N * (m + 1) / qty
            self.segs.append((st, en, avg))


def exit_one(p, nv, miss_m, gm, K, s, arm, gap, hh, state_m):
    """one exit cfg for one candidate and DCA kind K. arm = 0 -> no trailing; state_m = BIG -> no STATE."""
    p0 = p[0]
    sl_i = BIG
    for st, en, avg in K.segs:
        sl_i = first_ge(p, st, en, avg * (1.0 + s))
        if sl_i < BIG:
            break
    tr_i = BIG
    if arm > 0:
        ia = BIG
        for st, en, avg in K.segs:
            ia = first_le(p, st, en, avg * (1.0 - arm))
            if ia < BIG:
                break
        if ia < nv - 1:
            tr = np.minimum.accumulate(p[ia:nv])
            cond = p[ia + 1:nv] >= tr[:-1] * (1.0 + gap)
            x = int(np.argmax(cond))
            if cond[x]:
                tr_i = ia + 1 + x
    ev = [(sl_i, C.RT_SL), (tr_i, C.RT_TRAIL), (state_m if state_m < nv else BIG, C.RT_STATE),
          (60 * hh if 60 * hh < nv else BIG, C.RT_TIME), (miss_m if miss_m < nv else BIG, C.RT_MISS)]
    j, rt = BIG, C.RT_EOD
    for e in ev:
        if e[0] < j:
            j, rt = e
    if j >= BIG:
        j, rt = nv - 1, C.RT_EOD
    mult = 1.0 + CB.SL_SLIP if rt == C.RT_SL else (1.0 + CB.TR_SLIP if rt == C.RT_TRAIL else 1.0)
    X = p[j] * mult
    N, n = K.N, K.n
    xr = N * (X / p0)
    gross = N * (1.0 - X / p0)
    qx = N * (X / p0)
    qty = N / p0
    nf = 0
    for f, L in zip(K.f, K.L):
        if f <= j:
            nf += 1
            xr += N * (X / L)
            gross += N * (1.0 - X / L)
            qx += N * (X / L)
            qty += N / L
    if nf < n:
        xr += N * (n - nf) * (1.0 - FEE) / (1.0 + FEE)
    fund = K.fc[min((j + 1) // 60, CB.HMAX)]
    retb = gross - FEE * N * (1 + nf) - FEE * qx + fund
    mx = K.cmx[j]
    return dict(j=j, rt=rt, rs=int(C.C1.RT2RS[rt]), xr=xr, fund=fund, mx=mx, mxh=K.rmh[j - 1], flag=int(gm[j]) if gm is not None else 0,
                nleg=1 + nf, avg=(N * (1 + nf) / qty) / p0 if nf else 1.0, xraw=X / p0, retb=retb, worst=min(1.0 - FEE - mx, retb))


def candidate(p, nv, miss_m, gm, fh, sth):
    """all 60 exit cfgs for one candidate; sth = STATE hour (z_out 0) or BIG. Returns (rows list, {kind: Kind})."""
    kinds = {dn: Kind(p, nv, fh, n, a) for dn, n, a in C.DCAS}
    rows = []
    for x in C.XLIST:
        K = kinds[x['dca']]
        st = 60 * sth if (x['ex'] == 'STATE' and sth < BIG) else BIG
        rows.append(exit_one(p, nv, miss_m, gm, K, x['s'], x['arm'], x['gap'], x['H'], st))
    return rows, kinds


def state_hours(ks, cs, sig=None):
    XT1 = C.t1('exits_t1')
    sig = sig if sig is not None else XT1.load_sig()
    cond = XT1.state_cond(sig, C.STATE_ZO)
    return np.array([XT1.state_hour(cond, k, c) for k, c in zip(ks, cs)], dtype=np.int64)


def compute(st, ks, cs, sth, pathfn=None):
    """exit table (n x 60 per key) + hourly per DCA kind (n x 721: mk, hm, fh; NONE included for tests).
    pathfn(i) -> (p, nv, miss_m, gm, fh) replaces B1 path_of (fake data); default = real paths from st."""
    n = len(ks)
    T = {kk: np.empty((n, C.NX)) for kk in KEYS}
    HK = {dn: {kk: np.empty((n, CB.HMAX + 1)) for kk in ('mk', 'hm', 'fh')} for dn in C.DNAMES}
    p0 = np.empty(n)
    for i in range(n):
        if pathfn is None:
            p, nv, miss_m, gm, fh, lg = XB1.path_of(st, int(cs[i]), int(ks[i]))
        else:
            p, nv, miss_m, gm, fh = pathfn(i)
        rows, kinds = candidate(p, nv, miss_m, gm, fh, int(sth[i]))
        for xi, r in enumerate(rows):
            for kk in KEYS:
                T[kk][i, xi] = r[kk]
        for dn, K in kinds.items():
            HK[dn]['mk'][i], HK[dn]['hm'][i], HK[dn]['fh'][i] = K.mk, K.hm, K.fh
        p0[i] = p[0]
    for kk in ('j', 'nleg'):
        T[kk] = T[kk].astype(np.int32)
    for kk in ('rs', 'rt', 'flag'):
        T[kk] = T[kk].astype(np.int8)
    T['k'], T['c'], T['sth'], T['p0'] = np.asarray(ks), np.asarray(cs), np.asarray(sth), p0
    return T, HK


def view(T, HK, xi):
    """port.XView for exit cfg xi: per-cfg exit columns + hourly arrays of its DCA kind (fc = cumsum fh)."""
    P = C.b1('port')
    h = HK[C.XLIST[xi]['dca']]
    d = {kk: T[kk] for kk in ('j', 'rs', 'xr', 'fund', 'mxh', 'mx', 'flag')}
    d.update(mk=h['mk'], hm=h['hm'], fh=h['fh'], fc=h['fc'] if 'fc' in h else np.cumsum(h['fh'], axis=1))
    return P.XView(d, xi)


def save(T, HK, work=C.WORK):
    np.savez(work + '/exits_b4.npz.tmp.npz', **T)
    os.replace(work + '/exits_b4.npz.tmp.npz', work + '/exits_b4.npz')
    for dn in DK:
        np.savez(work + '/hourly_b4_%s.npz.tmp.npz' % dn, **HK[dn])
        os.replace(work + '/hourly_b4_%s.npz.tmp.npz' % dn, work + '/hourly_b4_%s.npz' % dn)


def load_table(work=C.WORK, ucid=None):
    """T (exit table) + HK (hourly per kind; NONE = B1 exits.npz rows ucid, verified equal by test a)."""
    z = np.load(work + '/exits_b4.npz')
    T = {kk: z[kk] for kk in z.files}
    HK = {}
    for dn in DK:
        h = np.load(work + '/hourly_b4_%s.npz' % dn)
        HK[dn] = {kk: h[kk] for kk in h.files}
        HK[dn]['fc'] = np.cumsum(HK[dn]['fh'], axis=1)
    if ucid is None:
        ucid = C.cand_classes()[1]
    b = np.load(CB.WORK + '/exits.npz')
    assert (b['k'][ucid] == T['k']).all() and (b['c'][ucid] == T['c']).all()
    HK['NONE'] = {kk: b[kk][ucid] for kk in ('mk', 'hm', 'fh', 'fc')}
    return T, HK


def hygiene(T):
    """NO profit: rows, NaN, nleg distribution and exit-reason shares per DCA kind."""
    for dn in C.DNAMES:
        cols = [xi for xi, x in enumerate(C.XLIST) if x['dca'] == dn]
        nl = T['nleg'][:, cols]
        rt = T['rt'][:, cols]
        dist = {int(v): round(float((nl == v).mean()), 4) for v in np.unique(nl)}
        sh = {C.RTNAMES[r]: round(float((rt == r).mean()), 4) for r in range(len(C.RTNAMES)) if (rt == r).any()}
        log.info('hygiene %s rows=%d cfgs=%d nan_xr=%d nan_fund=%d nleg=%s reasons=%s', dn, nl.shape[0], len(cols),
                 int(np.isnan(T['xr'][:, cols]).sum()), int(np.isnan(T['fund'][:, cols]).sum()), dist, sh)


def main_all():
    cls, ucid, uk, uc = C.cand_classes()
    st = XB1.Store()
    t0 = time.time()
    sth = state_hours(uk, uc)
    T, HK = compute(st, uk, uc, sth)
    T['ucid'] = ucid
    save(T, HK)
    log.info('exits_b4 all n=%d %.1fs', len(uk), time.time() - t0)
    hygiene(T)


def bench(n=200):
    cls, ucid, uk, uc = C.cand_classes()
    st = XB1.Store()
    t0 = time.time()
    sth = np.full(n, BIG)
    compute(st, uk[:n], uc[:n], sth)
    log.info('bench n=%d %.2fs -> %.4f s/cand (60 cfgs)', n, time.time() - t0, (time.time() - t0) / n)


if __name__ == '__main__':
    {'all': main_all, 'bench': bench}[sys.argv[1]]()
