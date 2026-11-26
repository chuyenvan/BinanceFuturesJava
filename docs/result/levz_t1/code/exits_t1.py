"""LEVZ T1 exit engine (PREREG_LEVZ_T1 sec 2-3) on 1-minute CLOSE, same conventions as B1 exits.py (imported, unchanged):
path minute i (0..43200) = close of 1m bar open T_k + i min (ffilled); entry p0 = path[0]; events evaluated at minutes i >= 1.
SL: close >= p0 (1 + sl) -> close x 1.003. TP (resting limit): close <= p0 (1 - tp) -> fill at EXACTLY p0 (1 - tp), no slip.
TIME: i = 60 H -> close. MISS (missing run > 24 h) / EOD as B1. Tie priority within a minute: SL > TP > STATE > TIME > MISS.
BRK  : sl = s, tp = R s.                     VOL: sl = clip(a u, 2 %, 50 %), tp = R sl (R = 0: no TP); u from 168 h BEFORE entry.
PART : partial (50 %) at the first i with close <= p0 (1 - s) (fill at p0 (1 - s)) if it comes before SL and not after TIME/MISS;
       then remainder: break-even stop close >= p0 (-> close x 1.003, 'be'), TP close <= p0 (1 - 3 s), TIME, MISS - all searched at
       minutes > partial minute (TIME / MISS at the partial minute close the remainder in that minute).
STATE: exit at path minute 60 h (1 minute after T_{k+h}, as entry / B1 time stop) for the first h >= 1 with the FINALISED W7 signal row
       k + h: z_oi < z_out OR z_f < z_out OR f <= 0.0001 (NaN -> no trigger); SL always on; cap H.
Output per family table (rows = candidates, cols = family exit cfgs): j, rs (B1 port reason code), rt (T1 reason), xr, fund, mx, mxh,
flag; PART also j1 (-1 = no partial), xr1, mxh_raw; VOL also u, slv. Hourly mk / hm / fh / fc / p0 identical to B1 (hourly_core).
PART is fed to port.py as ONE trade with xr = 0.5 xr1 + 0.5 xr2 and effective hourly arrays (part_view; CHOICES_T1).
usage: python3 code/exits_t1.py all   (real union candidates -> work/exits_t1_<FAM>.npz; hygiene stats only)"""
import os
import sys
import logging
import time
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common_t1 as C
sys.path.pop(0)
import numpy as np
import pandas as pd

log = logging.getLogger('levz_t1.exits')
CB = C.CB
XB1 = C.b1('exits')
BIG = XB1.BIG
FAMS = ('BRK', 'VOL', 'PART', 'STATE')
KEYS = ('j', 'rs', 'rt', 'xr', 'fund', 'mx', 'mxh', 'flag')


class Cur:
    """per-candidate path helpers (first-hit searches cached by level)."""
    def __init__(self, p, nv, miss_m, fh, gm):
        self.p, self.nv = p, nv
        self.p0 = p[0]
        q = p[1:]
        self.cmax = np.maximum.accumulate(q)
        self.cmin = np.minimum.accumulate(q)
        self.mi = miss_m if miss_m < nv else BIG
        self.fc = np.concatenate([[0.0], np.cumsum(fh[1:])])
        self.rmh = np.maximum.accumulate(q.reshape(CB.HMAX, 60), axis=1).ravel()
        self.gm = gm
        self._ge, self._le = {}, {}

    def ge(self, level):
        """first minute i >= 1 (< nv) with close >= level."""
        r = self._ge.get(level)
        if r is None:
            i = int(np.searchsorted(self.cmax, level, 'left')) + 1
            r = self._ge[level] = i if i < self.nv else BIG
        return r

    def le(self, level):
        r = self._le.get(level)
        if r is None:
            i = int(np.searchsorted(-self.cmin, -level, 'left')) + 1
            r = self._le[level] = i if i < self.nv else BIG
        return r

    def tmin(self, hh):
        return 60 * hh if 60 * hh < self.nv else BIG

    def after(self, i0, cond_fn):
        """first minute i > i0 (< nv) with cond_fn(p[i]) True."""
        seg = self.p[i0 + 1:self.nv]
        if len(seg) == 0:
            return BIG
        m = cond_fn(seg)
        x = int(np.argmax(m))
        return i0 + 1 + x if m[x] else BIG

    def fund(self, j):
        return self.fc[min((j + 1) // 60, CB.HMAX)]

    def finish(self, j, rt, xr):
        """common outputs for a single-leg exit; j = BIG -> eod."""
        if j >= BIG:
            j, rt, xr = self.nv - 1, C.RT_EOD, None
        if xr is None:
            xr = self.p[j] / self.p0
        mx = max(self.p0, self.cmax[j - 1]) / self.p0
        mxh = self.rmh[j - 1] / self.p0
        flag = int(self.gm[j]) if self.gm is not None else 0
        return j, rt, xr, mx, mxh, flag


def _pick(ev):
    """ev: list of (minute, rt, xr_or_None) in priority order -> earliest (first in list on ties)."""
    best = None
    for e in ev:
        if e[0] < BIG and (best is None or e[0] < best[0]):
            best = e
    return best if best is not None else (BIG, C.RT_EOD, None)


def bracket(cu, sl, tp, hh, state_m=BIG):
    """SL / TP / STATE / TIME / MISS single-leg exit. tp <= 0 or None -> no TP."""
    p0 = cu.p0
    i_sl = cu.ge(p0 * (1.0 + sl))
    ev = [(i_sl, C.RT_SL, None)]
    if tp is not None and tp > 0:
        ev.append((cu.le(p0 * (1.0 - tp)), C.RT_TP, 1.0 - tp))
    ev.append((state_m if state_m < cu.nv else BIG, C.RT_STATE, None))
    ev.append((cu.tmin(hh), C.RT_TIME, None))
    ev.append((cu.mi, C.RT_MISS, None))
    j, rt, xr = _pick(ev)
    if rt == C.RT_SL:
        xr = cu.p[j] * (1.0 + CB.SL_SLIP) / p0
    j, rt, xr, mx, mxh, flag = cu.finish(j, rt, xr)
    return dict(j=j, rt=rt, xr=xr, fund=cu.fund(j), mx=mx, mxh=mxh, flag=flag)


def part(cu, s, hh):
    p0 = cu.p0
    i_sl = cu.ge(p0 * (1.0 + s))
    T = cu.tmin(hh)
    i1 = cu.le(p0 * (1.0 - s))
    if not (i1 < BIG and i1 < i_sl and i1 <= T and i1 <= cu.mi):
        r = bracket(cu, s, None, hh)
        r.update(j1=-1, xr1=np.nan, mxh_raw=r['mxh'])
        return r
    xr1 = 1.0 - s
    lv_tp = p0 * (1.0 - C.PART_TPX * s)
    ev = [(cu.after(i1, lambda x: x >= p0), C.RT_BE, None),
          (cu.after(i1, lambda x: x <= lv_tp), C.RT_TP, 1.0 - C.PART_TPX * s),
          (T, C.RT_TIME, None), (cu.mi, C.RT_MISS, None)]
    j, rt, xr2 = _pick(ev)
    if rt == C.RT_BE:
        xr2 = cu.p[j] * (1.0 + CB.SL_SLIP) / p0
    j, rt, xr2, mx, mxh_raw, flag = cu.finish(j, rt, xr2)
    m1 = min((i1 + 1) // 60, CB.HMAX)
    m2 = min((j + 1) // 60, CB.HMAX)
    fund = cu.fc[m1] + (1.0 - C.PART_FRAC) * (cu.fc[m2] - cu.fc[m1])
    xr = C.PART_FRAC * xr1 + (1.0 - C.PART_FRAC) * xr2
    mxh_eff = C.PART_FRAC * xr1 + (1.0 - C.PART_FRAC) * mxh_raw
    if i1 > 60 * ((j - 1) // 60):          # partial inside the exit hour window -> conservative
        mxh_eff = max(mxh_raw, mxh_eff)
    return dict(j=j, rt=rt, xr=xr, fund=fund, mx=mx, mxh=mxh_eff, flag=flag, j1=i1, xr1=xr1, mxh_raw=mxh_raw)


# ---------------------------------------------------------------- side inputs (VOL u, STATE trigger hours), causal
def vol_u(CL, k, c):
    """u = sd (ddof 1) of hourly log returns over the 168 h ending at T_k (closes CL[k-168..k]; CL[k] = candle closing at T_k,
    known before the entry at T_k + 1 min) x sqrt(24). Returns (u, n_valid_returns); u = nan if n < VOL_MINRET."""
    a = max(0, int(k) - C.VOL_WIN)
    x = np.asarray(CL[a:int(k) + 1, int(c)], dtype=np.float64)
    with np.errstate(invalid='ignore', divide='ignore'):
        r = np.diff(np.log(x))
    r = r[np.isfinite(r)]
    if len(r) < C.VOL_MINRET:
        return np.nan, len(r)
    return float(np.std(r, ddof=1) * np.sqrt(24.0)), len(r)


def vol_sl(a, u):
    if not np.isfinite(u):
        return C.VOL_CAP
    return float(min(max(a * u, C.VOL_FLOOR), C.VOL_CAP))


def state_cond(sig, zo):
    """bool NH x ns: z_oi < zo OR z_f < zo OR f <= 0.0001 (NaN compare False)."""
    with np.errstate(invalid='ignore'):
        return (sig['z_oi'] < zo) | (sig['z_f'] < zo) | (sig['f'] <= C.STATE_F)


def state_hour(cond, k, c):
    """first h in 1..720 with cond[k + h, c] (row k + h exists) -> h, else BIG."""
    k = int(k)
    seg = cond[k + 1:min(k + CB.HMAX + 1, cond.shape[0]), int(c)]
    if len(seg) == 0 or not seg.any():
        return BIG
    return int(np.argmax(seg)) + 1


def load_sig(W=7):
    meta = CB.meta()
    syms = meta['syms']
    col = {s: i for i, s in enumerate(syms)}
    d = pd.read_parquet('%s/work/sig_W%d.parquet' % (C.L2, W), columns=['sym', 't', 'z_oi', 'z_f', 'f'])
    assert int(d['t'].max()) < CB.CUT
    r = ((d['t'].values - CB.H0) // CB.H).astype(np.int64)
    cc = d['sym'].map(col).values.astype(np.int64)
    out = {}
    for kk in ('z_oi', 'z_f', 'f'):
        a = np.full((CB.NH, len(syms)), np.nan)
        a[r, cc] = d[kk].values
        out[kk] = a
    return out


def load_CL():
    return np.load(C.L2 + '/work/inputs.npz')['CL']


# ---------------------------------------------------------------- tables
def candidate_rows(cu, fams, u=None, sth=None):
    """all family exits for ONE candidate. sth: {zo: state hour or BIG}."""
    out = {}
    for fam in fams:
        rows = []
        for x in C.fam_cfgs(fam):
            if fam == 'BRK':
                r = bracket(cu, x['s'], x['R'] * x['s'], x['H'])
            elif fam == 'VOL':
                sl = vol_sl(x['a'], u)
                r = bracket(cu, sl, x['R'] * sl if x['R'] > 0 else None, x['H'])
                r['slv'] = sl
            elif fam == 'PART':
                r = part(cu, x['s'], x['H'])
            else:
                h = sth[x['zo']]
                r = bracket(cu, x['s'], None, x['H'], 60 * h if h < BIG else BIG)
            rows.append(r)
        out[fam] = rows
    return out


def compute(st, ks, cs, fams=FAMS, CL=None, sig=None, conds=None):
    """exit tables for candidate list (ks, cs) (any candidates, e.g. random). Returns {fam: table} + 'hourly' (mk, hm, fh, fc, p0)."""
    n = len(ks)
    if 'VOL' in fams and CL is None:
        CL = load_CL()
    if 'STATE' in fams and conds is None:
        sig = sig if sig is not None else load_sig()
        conds = {zo: state_cond(sig, zo) for zo in C.STATE_Z}
    acc = {f: {kk: np.empty((n, C.NFAM[f])) for kk in KEYS} for f in fams}
    for f in fams:
        if f == 'PART':
            for kk in ('j1', 'xr1', 'mxh_raw'):
                acc[f][kk] = np.empty((n, C.NFAM[f]))
        if f == 'VOL':
            acc[f]['slv'] = np.empty((n, C.NFAM[f]))
            acc[f]['u'] = np.empty(n)
            acc[f]['u_n'] = np.empty(n)
        if f == 'STATE':
            acc[f]['sth'] = np.empty((n, len(C.STATE_Z)))
    mk = np.empty((n, CB.HMAX + 1))
    hm = np.empty((n, CB.HMAX + 1))
    fh = np.empty((n, CB.HMAX + 1))
    p0 = np.empty(n)
    for i in range(n):
        p, nv, miss_m, gm, f_, longgap = XB1.path_of(st, int(cs[i]), int(ks[i]))
        cu = Cur(p, nv, miss_m, f_, gm)
        u = None
        sth = None
        if 'VOL' in fams:
            u, un = vol_u(CL, ks[i], cs[i])
            acc['VOL']['u'][i], acc['VOL']['u_n'][i] = u, un
        if 'STATE' in fams:
            sth = {zo: state_hour(conds[zo], ks[i], cs[i]) for zo in C.STATE_Z}
            acc['STATE']['sth'][i] = [sth[zo] for zo in C.STATE_Z]
        rows = candidate_rows(cu, fams, u, sth)
        for f in fams:
            for xi, r in enumerate(rows[f]):
                for kk, v in r.items():
                    acc[f][kk][i, xi] = v
        mk[i], hm[i] = XB1.hourly_core(p, f_)
        fh[i] = f_
        p0[i] = p[0]
    out = {}
    for f in fams:
        t = acc[f]
        t['j'] = t['j'].astype(np.int32)
        t['rt'] = t['rt'].astype(np.int8)
        t['rs'] = C.RT2RS[t['rt']]
        t['flag'] = t['flag'].astype(np.int8)
        if f == 'PART':
            t['j1'] = t['j1'].astype(np.int32)
        t['k'], t['c'] = np.asarray(ks), np.asarray(cs)
        out[f] = t
    out['hourly'] = dict(mk=mk, hm=hm, fh=fh, fc=np.cumsum(fh, axis=1), p0=p0)
    return out


def with_hourly(t, hourly):
    """family table + shared hourly arrays -> dict usable by port.XView (non-PART) / part_view (PART)."""
    T = dict(t)
    T.update(hourly)
    return T


def load_family(fam, hourly=None):
    z = np.load('%s/exits_t1_%s.npz' % (C.WORK, fam))
    t = {kk: z[kk] for kk in z.files}
    if hourly is None:
        hourly = load_b1_hourly(t['k'], t['c'])
    return with_hourly(t, hourly)


def load_b1_hourly(k=None, c=None):
    z = np.load(CB.WORK + '/exits.npz')
    if k is not None:
        assert (z['k'] == k).all() and (z['c'] == c).all(), 'candidate order differs from B1 exits.npz'
    return {kk: z[kk] for kk in ('mk', 'hm', 'fh', 'fc', 'p0')}


class PartView:
    """port.XView-compatible view of PART exit cfg xi with effective hourly arrays (0.5 of the position realised at j1)."""
    def __init__(self, T, xi):
        P = C.b1('port')
        base = P.XView(T, xi)
        self.__dict__.update(base.__dict__)
        j1 = T['j1'][:, xi].astype(np.int64)
        xr1 = T['xr1'][:, xi]
        has = j1 >= 0
        w = C.PART_FRAC
        hh = np.arange(CB.HMAX + 1)[None, :]
        j1c = np.where(has, j1, BIG)[:, None]
        xr1c = np.where(has, xr1, 0.0)[:, None]
        after = (60 * hh >= j1c)                       # mark minute 60h at/after partial
        self.mk = np.where(after, w * xr1c + (1.0 - w) * T['mk'], T['mk'])
        hm_after = w * xr1c + (1.0 - w) * T['hm']
        full_after = 60 * (hh - 1) >= j1c              # whole window after partial
        inside = (~full_after) & after                  # partial inside window (60(h-1), 60h]
        self.hm = np.where(full_after, hm_after, np.where(inside, np.maximum(T['hm'], hm_after), T['hm']))
        wf = np.where(60 * hh - 1 <= j1c, 1.0, 1.0 - w)
        self.fh = T['fh'] * wf
        self.fc = np.cumsum(self.fh, axis=1)


def view(fam, T, xi):
    if fam == 'PART':
        return PartView(T, xi)
    return C.b1('port').XView(T, xi)


def main_all():
    cz = np.load(CB.WORK + '/cand_b1.npz')
    uk, uc = cz['U_k'], cz['U_c']
    st = XB1.Store()
    t0 = time.time()
    out = compute(st, uk, uc)
    hb = load_b1_hourly(uk, uc)
    for kk in ('mk', 'hm', 'fh', 'p0'):
        assert np.array_equal(out['hourly'][kk], hb[kk]), kk
    for f in FAMS:
        fn = '%s/exits_t1_%s.npz' % (C.WORK, f)
        np.savez(fn + '.tmp.npz', **out[f])
        os.replace(fn + '.tmp.npz', fn)
    log.info('exits_t1 all n=%d %.1fs', len(uk), time.time() - t0)
    hygiene(out)


def hygiene(out):
    """NO profit: rows, NaN, exit-reason shares per family."""
    for f in FAMS:
        t = out[f]
        rt = t['rt']
        sh = {C.RTNAMES[r]: round(float((rt == r).mean()), 4) for r in range(len(C.RTNAMES)) if (rt == r).any()}
        log.info('hygiene %s rows=%d cfgs=%d nan_xr=%d nan_fund=%d reasons=%s', f, rt.shape[0], rt.shape[1],
                 int(np.isnan(t['xr']).sum()), int(np.isnan(t['fund']).sum()), sh)
        if f == 'VOL':
            u = t['u']
            log.info('hygiene VOL u nan=%d q05/50/95=%s', int(np.isnan(u).sum()), np.round(np.nanquantile(u, [0.05, 0.5, 0.95]), 4))
        if f == 'PART':
            log.info('hygiene PART partial share per cfg=%s', np.round((t['j1'] >= 0).mean(axis=0), 4))


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    {'all': main_all}[sys.argv[1]]()
