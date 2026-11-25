"""LEVZ2 portfolio simulator (PREREG_LEVZ2 @278725ae sec 2, 4). SHORT only, 1x, hourly loop.
Hour grid: index k <-> T_k = H0 + k*1h = tier-1 decision hour h (info up to T_k).
px row k = store candle [T_k - 1h, T_k) (close-time label T_k; S2 convention A).
Entry at close of hour t (= CL[k]); exit checks start at candle k+1.
Funding FR[k] = sum of settlement rates whose ts rounds to boundary T_k.
usage: python3 code/sim.py prep | smoke
See CHOICES2.md for every interpretation."""
import os
import sys
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:] = [x for x in sys.path if os.path.abspath(x or os.getcwd()) != _HERE]  # code/select.py must not shadow stdlib select
import importlib.util
import json
import logging
import math
sys.dont_write_bytecode = True
import numpy as np
import pandas as pd

log = logging.getLogger('levz2.sim')
BASE = '/home/ubuntu/claude_master/w3/levz2'
WORK = BASE + '/work'
OUT = BASE + '/out'
H = 3600000
DAY = 86400000
H0 = 1638316800000      # 2021-12-01 00:00 UTC
CUT = 1767225600000     # 2026-01-01 00:00 UTC
INIT = 10000.0
FEE = 0.0007            # per side
EXPO = 0.60
SL_SLIP = 0.005
DCA_UP = 0.10
TR_ACT = 0.10
TR_GAP = 0.05
TR_SLIP = 0.001
COOL = 72               # hours, from ENTRY; re-entry needs k - k_entry > COOL (same as tier-1 CHOICES 9)
E1_WIN = 24
ZR_TH = -2.0
F_MIN = 0.0001
MISS_MAX = 24
EPS = 1e-12
FOLDS = (('DEV', '2022-01-01', '2026-01-01'), ('F1', '2022-01-01', '2024-01-01'),
         ('F2', '2024-01-01', '2025-01-01'), ('F3', '2025-01-01', '2026-01-01'))
REASONS = ('sl', 'trail', 'time', 'time_sub', 'gap', 'eod')
GRID = dict(W=(14, 7), E=('E0', 'E1'), zmin=(2.5, 3.0, 3.5), K=(3, 5, 10), SL=(0.15, 0.30, 0.50), H=(24, 72, 168),
            trail=(0, 1), dca=(0, 1))
PKEYS = ('W', 'E', 'zmin', 'K', 'SL', 'H', 'trail', 'dca')


def load_sibling(name):
    """import code/<name>.py under module name levz2_<name> (never via sys.path)."""
    mn = 'levz2_' + name
    if mn in sys.modules:
        return sys.modules[mn]
    spec = importlib.util.spec_from_file_location(mn, os.path.join(_HERE, name + '.py'))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mn] = mod
    spec.loader.exec_module(mod)
    return mod


def ms(s):
    return int(pd.Timestamp(s, tz='UTC').value // 10**6)


def kidx(t_ms):
    return int((t_ms - H0) // H)


# ---------------------------------------------------------------- candidates
def candidates(z_oi, z_f, f, z_r, u, pxok, E, zmin):
    """Return (ck, cc, cs) sorted by (k asc, s desc, c asc). c index = sym sorted asc => tie-break sym asc.
    E0: LEV(k) & price at k. LEV = u & z_oi>=zmin & z_f>=zmin & f>F_MIN (NaN -> False).
    E1: z_r(k) <= -2 & latest LEV hour s in [k-24, k-1] & no z_r<=-2 hour in (s, k) & price at k; score from hour s."""
    with np.errstate(invalid='ignore'):
        lev = u & (z_oi >= zmin) & (z_f >= zmin) & (f > F_MIN)
        sc = np.fmin(z_oi, z_f)
    if E == 'E0':
        m = lev & pxok
        ck, cc = np.nonzero(m)
        cs = sc[ck, cc]
    else:
        NH = lev.shape[0]
        idx = np.arange(NH, dtype=np.int64)[:, None]
        a = np.where(lev, idx, -1)
        last_lev = np.full(lev.shape, -1, dtype=np.int64)
        last_lev[1:] = np.maximum.accumulate(a, axis=0)[:-1]
        with np.errstate(invalid='ignore'):
            zr = z_r <= ZR_TH
        b = np.where(zr, idx, -1)
        last_zr = np.full(lev.shape, -1, dtype=np.int64)
        last_zr[1:] = np.maximum.accumulate(b, axis=0)[:-1]
        m = zr & (last_lev >= 0) & (idx - last_lev <= E1_WIN) & (last_zr <= last_lev) & pxok
        ck, cc = np.nonzero(m)
        cs = sc[last_lev[ck, cc], cc]
    assert np.isfinite(cs).all()
    o = np.lexsort((cc, -cs, ck))
    return ck[o].astype(np.int64), cc[o].astype(np.int64), cs[o].astype(np.float64)


class Cand:
    """per-hour candidate lists: hours -> list of (c, s)."""
    def __init__(self, ck, cc, cs):
        self.ck, self.cc, self.cs = ck, cc, cs
        self.by_k = {}
        if len(ck):
            brk = np.flatnonzero(np.diff(ck)) + 1
            st = np.concatenate([[0], brk])
            en = np.concatenate([brk, [len(ck)]])
            ccl = cc.tolist()
            for a, b in zip(st.tolist(), en.tolist()):
                self.by_k[int(ck[a])] = ccl[a:b]
        self.hours = np.array(sorted(self.by_k), dtype=np.int64)


# ---------------------------------------------------------------- inputs
class Inputs:
    pass


def prep():
    """Build work/inputs.npz: tms, syms, O,HI,LO,CL (float32 store values), FR, U, and candidates for 12 (W,E,zmin)."""
    SG = load_sibling('sig')       # sig.py puts the frozen tier-1 code dir on sys.path
    import common as C
    with open(WORK + '/sig_meta.json') as fh:
        meta = json.load(fh)
    syms, NH = meta['syms'], meta['NH']
    assert meta['H0'] == H0 and H0 + NH * H == CUT
    col = {s: i for i, s in enumerate(syms)}
    ns = len(syms)
    px = pd.read_parquet(WORK + '/px_1h.parquet')
    px = px[px['sym'].isin(col)]
    k = ((px['t'].values - H0) // H).astype(np.int64)
    m = (k >= 0) & (k < NH)       # candle closing at CUT (k == NH) is not needed (last decision hour = NH-1)
    px, k = px[m], k[m]
    c = px['sym'].map(col).values.astype(np.int64)
    arr = {}
    for nm, cn in (('O', 'open'), ('HI', 'high'), ('LO', 'low'), ('CL', 'close')):
        a = np.full((NH, ns), np.nan, dtype=np.float32)
        a[k, c] = px[cn].values.astype(np.float32)
        arr[nm] = a
    fl = [C.read_funding(y, CUT) for y in range(2021, 2026)]
    f = pd.concat(fl, ignore_index=True)
    f = f[f['sym'].isin(col) & np.isfinite(f['rate']) & (f['interval_h'] > 0)]
    f = f.sort_values(['sym', 'ts'], kind='mergesort').drop_duplicates(['sym', 'ts'], keep='last')
    assert int(f['ts'].max()) < CUT
    fk = ((f['ts'].values - H0 + H // 2) // H).astype(np.int64)
    fm = (fk >= 0) & (fk < NH)
    FR = np.zeros((NH, ns))
    np.add.at(FR, (fk[fm], f['sym'].map(col).values.astype(np.int64)[fm]), f['rate'].values[fm])
    off = (f['ts'].values - H0) - ((f['ts'].values - H0 + H // 2) // H) * H
    log.info('funding rows=%d off_ms min=%d max=%d', int(fm.sum()), int(off.min()), int(off.max()))
    pxok = np.isfinite(arr['CL'])
    out = dict(tms=H0 + np.arange(NH, dtype=np.int64) * H, syms=np.array(syms), FR=FR, **arr)
    for W in (14, 7):
        S = SG.dense_from_sig(W)
        assert S['syms'] == syms
        if W == 14:
            out['U'] = S['u']
        else:
            assert (out['U'] == S['u']).all()
        for E in ('E0', 'E1'):
            for z in (2.5, 3.0, 3.5):
                ck, cc, cs = candidates(S['z_oi'], S['z_f'], S['f'], S['z_r'], S['u'], pxok, E, z)
                key = 'cand_W%d_%s_%.1f' % (W, E, z)
                out[key + '_k'], out[key + '_c'], out[key + '_s'] = ck, cc, cs
                log.info('%s n=%d', key, len(ck))
        del S
    np.savez(WORK + '/inputs.npz', **out)
    log.info('inputs saved NH=%d ns=%d', NH, ns)


def load_inputs(path=WORK + '/inputs.npz'):
    z = np.load(path, allow_pickle=False)
    I = Inputs()
    I.tms = z['tms']
    I.syms = [str(s) for s in z['syms']]
    assert int(I.tms[-1]) < CUT
    I.px = dict(O=z['O'].astype(np.float64), HI=z['HI'].astype(np.float64), LO=z['LO'].astype(np.float64),
                CL=z['CL'].astype(np.float64), tms=I.tms)
    I.FR = z['FR']
    I.U = z['U']
    I.cand = {}
    for W in (14, 7):
        for E in ('E0', 'E1'):
            for zz in (2.5, 3.0, 3.5):
                key = 'cand_W%d_%s_%.1f' % (W, E, zz)
                I.cand[(W, E, zz)] = Cand(z[key + '_k'], z[key + '_c'], z[key + '_s'])
    return I


# ---------------------------------------------------------------- core
class Pos:
    __slots__ = ('c', 'ke', 'p0', 'size0', 'qty', 'avg', 'stop', 'last', 'fee', 'fund', 'nin', 'dcad', 'kd',
                 'trough', 'active', 'lvl', 'miss')


def _close(p, k, px_exit, reason, cash, trades, flag=0):
    gross = p.qty * (p.avg - px_exit)
    fee = p.qty * px_exit * FEE
    p.fee += fee
    net = gross - p.fee + p.fund
    trades.append((p.c, p.ke, k, p.p0, p.avg, px_exit, p.qty, p.size0, p.nin, int(p.dcad), p.kd, reason, gross,
                   p.fee, p.fund, net, net / p.nin, flag))
    return cash + gross - fee


TCOLS = ('c', 'ke', 'kx', 'p0', 'avg', 'px_exit', 'qty', 'size0', 'notional_in', 'dca', 'k_dca', 'reason', 'gross',
         'fees', 'funding', 'net', 'ret', 'flag')


def run(cfg, sig, px, funding, start, end):
    """cfg: dict(W,E,zmin,K,SL,H,trail,dca). sig: Cand (candidates already for cfg's W/E/zmin).
    px: dict(O,HI,LO,CL,tms) dense (NH x ns). funding: FR dense. start/end: 'YYYY-MM-DD' (entries for T in [start, end)).
    Returns (trades DataFrame, equity DataFrame, metrics dict)."""
    O, HI, LO, CL, tms = px['O'], px['HI'], px['LO'], px['CL'], px['tms']
    FR = funding
    k0 = kidx(ms(start))
    kl = kidx(ms(end)) - 1
    assert 0 <= k0 <= kl < len(tms) and int(tms[kl]) < CUT
    K = int(cfg['K'])
    SL = float(cfg['SL'])
    HH = int(cfg['H'])
    TRAIL = bool(cfg['trail'])
    DCA = bool(cfg['dca'])
    NHr = kl - k0 + 1
    eqc = np.full(NHr, np.nan)
    eqw = np.full(NHr, np.nan)
    expo = np.zeros(NHr)
    cash = INIT
    pos = {}
    last_entry = {}
    trades = []
    by_k = sig.by_k
    hours = sig.hours
    hi = int(np.searchsorted(hours, k0))
    nh = len(hours)
    k = k0
    while k <= kl:
        if not pos:
            while hi < nh and hours[hi] < k:
                hi += 1
            if hi >= nh or hours[hi] > kl:
                break
            k = int(hours[hi])
        adj = 0.0
        if pos:
            done = []
            newlast = {}
            for c in sorted(pos):
                p = pos[c]
                cl = CL.item(k, c)
                if cl != cl:  # missing candle
                    p.miss += 1
                    r = FR.item(k, c)
                    if r != 0.0:
                        fu = p.qty * p.last * r
                        cash += fu
                        p.fund += fu
                    if k - p.ke >= HH:
                        cash = _close(p, k, p.last, 'time_sub', cash, trades, 1)
                        done.append(c)
                    elif p.miss > MISS_MAX:
                        cash = _close(p, k, p.last, 'gap', cash, trades, 1)
                        done.append(c)
                    elif k == kl:
                        cash = _close(p, k, p.last, 'eod', cash, trades, 1)
                        done.append(c)
                    continue
                p.miss = 0
                o = O.item(k, c)
                h = HI.item(k, c)
                lo = LO.item(k, c)
                xp = None
                if o >= p.stop:                       # (a) SL gap at open: exit at open, no DCA (ADDENDUM2 G2)
                    xp, rs = o, 'sl'
                else:
                    thit = TRAIL and p.active and h >= p.lvl   # trail armed before & hit by previous level (G3: no DCA)
                    if DCA and not p.dcad and not thit and h >= p.p0 * (1.0 + DCA_UP):   # (b) DCA BEFORE SL check (G2)
                        pd_ = p.p0 * (1.0 + DCA_UP)
                        unr = 0.0
                        notl = 0.0
                        for q in pos.values():
                            if q is p or q.c in done:
                                continue
                            unr += q.qty * (q.avg - q.last)
                            notl += q.qty * q.last
                        eq_now = cash + unr + p.qty * (p.avg - pd_)
                        if notl + p.qty * pd_ + p.size0 <= EXPO * eq_now + EPS:
                            qa = p.size0 / pd_
                            fe = p.size0 * FEE
                            cash -= fe
                            p.fee += fe
                            p.avg = (p.qty * p.avg + qa * pd_) / (p.qty + qa)
                            p.qty += qa
                            p.nin += p.size0
                            p.dcad = True
                            p.kd = k
                    if h >= p.stop:                    # (a) SL touch, on the (possibly DCA-increased) quantity
                        xp, rs = p.stop * (1.0 + SL_SLIP), 'sl'
                    elif TRAIL:                        # (c) trailing: check previous level, then update trough
                        if thit:
                            xp, rs = max(o, p.lvl * (1.0 + TR_SLIP)), 'trail'
                        else:
                            if lo < p.trough:
                                p.trough = lo
                            if (not p.active) and lo <= p.avg * (1.0 - TR_ACT):
                                p.active = True
                            if p.active:
                                p.lvl = p.trough * (1.0 + TR_GAP)
                if xp is not None:                     # intrabar exit: funding at T_k not received
                    cash = _close(p, k, xp, rs, cash, trades)
                    done.append(c)
                    continue
                r = FR.item(k, c)                      # funding at boundary T_k (position open through T_k)
                if r != 0.0:
                    fu = p.qty * cl * r
                    cash += fu
                    p.fund += fu
                adj += p.qty * (h - cl)
                newlast[c] = cl
                if k - p.ke >= HH:                     # (d) time-stop at close
                    p.last = cl
                    cash = _close(p, k, cl, 'time', cash, trades)
                    done.append(c)
                elif k == kl:
                    p.last = cl
                    cash = _close(p, k, cl, 'eod', cash, trades)
                    done.append(c)
            for c in done:
                del pos[c]
            for c, v in newlast.items():
                if c in pos:
                    pos[c].last = v
        # entries at close of hour k
        if k < kl:
            lst = by_k.get(k)
            if lst and len(pos) < K:
                eq = cash
                for q in pos.values():
                    eq += q.qty * (q.avg - q.last)
                size = eq * EXPO / K
                if size > 0:
                    for c in lst:
                        if len(pos) >= K:
                            break
                        if c in pos:
                            continue
                        le = last_entry.get(c)
                        if le is not None and k - le <= COOL:
                            continue
                        pr = CL.item(k, c)
                        p = Pos()
                        p.c, p.ke, p.p0, p.size0 = c, k, pr, size
                        p.qty = size / pr
                        p.avg = pr
                        p.stop = pr * (1.0 + SL)
                        p.last = pr
                        p.fee = size * FEE
                        cash -= p.fee
                        p.fund = 0.0
                        p.nin = size
                        p.dcad = False
                        p.kd = -1
                        p.trough = math.inf
                        p.active = False
                        p.lvl = math.inf
                        p.miss = 0
                        pos[c] = p
                        last_entry[c] = k
        eq = cash
        notl = 0.0
        for q in pos.values():
            eq += q.qty * (q.avg - q.last)
            notl += q.qty * q.last
        i = k - k0
        eqc[i] = eq
        eqw[i] = eq - adj
        expo[i] = notl / eq if eq > 0 else np.nan
        k += 1
    assert not pos
    # fill skipped hours (flat book: equity constant)
    s = pd.Series(eqc)
    eqc = s.ffill().fillna(INIT).values
    m = np.isnan(eqw)
    eqw[m] = eqc[m]
    tr = pd.DataFrame(trades, columns=list(TCOLS))
    eqdf = pd.DataFrame({'t': tms[k0:kl + 1], 'eq': eqc, 'eq_worst': eqw, 'expo': expo})
    met = metrics(tr, eqdf, cash, tms, k0, kl)
    return tr, eqdf, met


def _maxdd(eq, eqw):
    peak = np.maximum.accumulate(np.concatenate([[INIT], eq]))
    dd = 1.0 - eq / peak[1:]
    ddw = 1.0 - eqw / peak[:-1]     # worst-in-hour vs peak of CLOSE equity before this hour
    return float(max(dd.max(), 0.0)), float(max(ddw.max(), 0.0))


def metrics(tr, eqdf, cash_end, tms, k0, kl):
    eq = eqdf['eq'].values
    eqw = eqdf['eq_worst'].values
    t = eqdf['t'].values
    end_eq = float(eq[-1])
    m = {}
    m['n'] = int(len(tr))
    m['eq_end'] = end_eq
    m['ret'] = end_eq / INIT - 1.0
    m['acct_err'] = float(tr['net'].sum() - (cash_end - INIT)) if len(tr) else float(cash_end - INIT)
    yrs = (kl - k0 + 1) / (24 * 365.25)
    m['cagr'] = (end_eq / INIT) ** (1.0 / yrs) - 1.0 if end_eq > 0 else -1.0
    dd, ddw = _maxdd(eq, eqw)
    m['maxdd'], m['maxdd_worst'] = dd, ddw
    m['calmar'] = m['cagr'] / dd if dd > 0 else np.nan
    m['calmar_worst'] = m['cagr'] / ddw if ddw > 0 else np.nan
    dmask = (t % DAY) == 0
    de = np.concatenate([[INIT], eq[dmask]])
    dr = de[1:] / de[:-1] - 1.0
    sd = dr.std(ddof=1) if len(dr) > 1 else 0.0
    m['sharpe_d'] = float(dr.mean() / sd * math.sqrt(365.0)) if sd > 0 else 0.0
    m['expo_mean'] = float(np.nanmean(eqdf['expo'].values))
    if len(tr):
        m['win'] = float((tr['net'] > 0).mean())
        m['mean_ret'] = float(tr['ret'].mean())
        m['mean_pnl'] = float(tr['net'].mean())
        m['worst_ret'] = float(tr['ret'].min())
        m['fund_total'] = float(tr['funding'].sum())
        m['fees_total'] = float(tr['fees'].sum())
        m['n_dca'] = int(tr['dca'].sum())
        m['n_flag'] = int(tr['flag'].sum())
        for r in REASONS:
            m['x_' + r] = float((tr['reason'] == r).mean())
    else:
        for kk in ('win', 'mean_ret', 'mean_pnl', 'worst_ret'):
            m[kk] = np.nan
        m['fund_total'] = m['fees_total'] = 0.0
        m['n_dca'] = m['n_flag'] = 0
        for r in REASONS:
            m['x_' + r] = np.nan
    yr = pd.to_datetime(t, unit='ms').year.values
    prev = INIT
    for y in range(2022, 2026):
        mm = yr == y
        if mm.any():
            v = float(eq[mm][-1])
            m['pnl_%d' % y] = v - prev
            prev = v
    return m


def run_all(cfg, I, cand=None):
    """DEV + F1..F3, each independent from INIT. Returns flat dict."""
    if cand is None:
        cand = I.cand[(int(cfg['W']), cfg['E'], float(cfg['zmin']))]
    out = {}
    for name, a, b in FOLDS:
        tr, eq, m = run(cfg, cand, I.px, I.FR, a, b)
        for kk, v in m.items():
            out['%s_%s' % (name, kk)] = v
    return out


def all_cfgs():
    import itertools
    res = []
    for i, v in enumerate(itertools.product(*[GRID[p] for p in PKEYS])):
        d = dict(zip(PKEYS, v))
        d['cfg_id'] = i
        res.append(d)
    assert len(res) == 1296
    return res


# ---------------------------------------------------------------- smoke (ONLY allowed real run at this step)
SMOKE = dict(W=14, E='E0', zmin=2.5, K=10, SL=0.50, H=24, trail=0, dca=0)


def smoke():
    import time
    I = load_inputs()
    t0 = time.time()
    tr, eq, m = run(SMOKE, I.cand[(14, 'E0', 2.5)], I.px, I.FR, '2022-01-01', '2026-01-01')
    dt = time.time() - t0
    tr['sym'] = [I.syms[c] for c in tr['c']]
    tr['te'] = I.tms[tr['ke'].values]
    tr['gross_ret'] = tr['gross'] / tr['notional_in']
    tr.to_parquet(OUT + '/smoke_trades.parquet', index=False)
    eq.to_parquet(OUT + '/smoke_equity.parquet', index=False)
    t1 = time.time()
    r2 = run(SMOKE, I.cand[(14, 'E0', 2.5)], I.px, I.FR, '2022-01-01', '2026-01-01')
    det = bool(r2[0].drop(columns=[]).equals(tr[list(TCOLS)])) and bool(r2[1].equals(eq))
    t2 = time.time()
    oa = run_all(SMOKE, I)
    t3 = time.time()
    ev = pd.concat([pd.read_parquet('/home/ubuntu/claude_master/w3/levz/out/events_A1_%s.parquet' % p) for p in ('explore', 'confirm')])
    ev['sym'] = ev['sym'].astype(str)
    j = tr.merge(ev[['sym', 't0', 'te', 'p_te', 'p_end_24', 'gross_24', 'mae_24', 'nop', 'sub_24']], on=['sym', 'te'], how='outer', indicator=True)
    both = j[j['_merge'] == 'both']
    nsl = both[both['reason'] != 'time']
    tm = both[both['reason'] == 'time']
    rep = dict(seconds_one_run=dt, seconds_run_all_4=t3 - t2, deterministic=det, metrics_keys=len(m),
               n_trades=int(len(tr)), acct_err=m['acct_err'], reasons=tr['reason'].value_counts().to_dict(),
               sl_frac=float((tr['reason'] == 'sl').mean()),
               n_A1_events=int(len(ev)), n_match=int(len(both)), n_sim_only=int((j['_merge'] == 'left_only').sum()),
               n_tier1_only=int((j['_merge'] == 'right_only').sum()),
               n_match_time=int(len(tm)), n_match_nontime=int(len(nsl)),
               gross_diff_time_mean=float((tm['gross_ret'] - tm['gross_24']).mean()) if len(tm) else None,
               gross_diff_time_absmed=float((tm['gross_ret'] - tm['gross_24']).abs().median()) if len(tm) else None,
               gross_diff_time_absq95=float((tm['gross_ret'] - tm['gross_24']).abs().quantile(0.95)) if len(tm) else None,
               gross_diff_time_absmax=float((tm['gross_ret'] - tm['gross_24']).abs().max()) if len(tm) else None,
               entry_px_reldiff_absmax=float((both['p0'] / both['p_te'] - 1).abs().max()) if len(both) else None,
               entry_px_reldiff_absmed=float((both['p0'] / both['p_te'] - 1).abs().median()) if len(both) else None,
               mean_gross_sim_matched_time=float(tm['gross_ret'].mean()) if len(tm) else None,
               mean_gross24_tier1_matched_time=float(tm['gross_24'].mean()) if len(tm) else None)
    j.to_parquet(OUT + '/smoke_vs_A1.parquet', index=False)
    with open(OUT + '/smoke.json', 'w') as fh:
        json.dump(dict(report=rep, dev_metrics=m, run_all=oa), fh, indent=1, default=float)
    log.info('smoke %s', json.dumps(rep, default=float))


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    {'prep': prep, 'smoke': smoke}[sys.argv[1]]()
