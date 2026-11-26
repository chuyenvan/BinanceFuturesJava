"""LEVZ B1 step 3 - portfolio layer = B0 logic (sim.run, PREREG_LEVZ2 sec 2 + ADDENDUM1 A-C) with exits taken from the exit table.
Hour k <-> T_k = H0 + k h. Decisions at hour k use info up to T_k (B0 candidates(), imported). Entry at the close of the 1m bar
open_time T_k (path minute 0). An exit at path minute j (bar open T_ke + j min) lies in hour window (T_{kx-1}, T_kx] with
kx = ke + ceil(j / 60); the slot is free for decisions at kx (exit at j <= 60 h happens no later than the decision bar of hour kx,
same as B0 'exits before entries'). Fold end kl = end - 1 h: no entry at kl; positions with kx > kl closed at mark(kl) ('eod').
Top-K by s desc (tie sym asc; order from B0 candidates()); size = equity(k) x 0.60 / K_max, equity(k) = MTM at mark k
(path[60 h] of open positions, funding received up to T_k, entry fees paid), before the fees of the entries at k; cooldown:
re-entry only if k - k_last_entry > 72 (B0). Fees 0.07 % per side on notional. Funding per exits table / hourly fh.
Equity MTM per hour = cash + sum N (1 - mk[h]); 'worst' = minus sum N (hm[h] - mk[h]) for positions open through T_k and minus
N max(0, mxh - xr) for positions exiting inside the window (CHOICES_B1). Metrics = B0 sim.metrics (imported) + x_miss."""
import os
import sys
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:] = [x for x in sys.path if os.path.abspath(x or os.getcwd()) != _HERE]
import logging
import math
sys.dont_write_bytecode = True
sys.path.insert(0, _HERE)
import common_b1 as CB
sys.path.pop(0)
import numpy as np
import pandas as pd

log = logging.getLogger('levz_b1.port')
S = CB.load_b0('sim')
INIT, FEE, EXPO, COOL = S.INIT, S.FEE, S.EXPO, S.COOL
assert (INIT, FEE, EXPO, COOL) == (10000.0, 0.0007, 0.60, 72)
FOLDS = S.FOLDS
TCOLS = ('c', 'cid', 'ke', 'kx', 'j', 'notional_in', 'xr', 'reason', 'gross', 'fees', 'funding', 'net', 'ret', 'flag', 'mx')


class CandB1:
    """per-hour candidate lists (c, cid) in B0 order (k asc, s desc, c asc)."""
    def __init__(self, ck, cc, cs, cid):
        o = np.lexsort((cc, -cs, ck))
        self.ck, self.cc, self.cs, self.cid = ck[o], cc[o], cs[o], cid[o]
        self.by_k = {}
        if len(ck):
            brk = np.flatnonzero(np.diff(self.ck)) + 1
            st = np.concatenate([[0], brk])
            en = np.concatenate([brk, [len(self.ck)]])
            cl, il = self.cc.tolist(), self.cid.tolist()
            for a, b in zip(st.tolist(), en.tolist()):
                self.by_k[int(self.ck[a])] = list(zip(cl[a:b], il[a:b]))
        self.hours = np.array(sorted(self.by_k), dtype=np.int64)


class XView:
    """exit table restricted to one exit config xi (vectors over cid) + hourly arrays (shared)."""
    def __init__(self, T, xi):
        self.j = T['j'][:, xi].astype(np.int64)
        self.rs = T['rs'][:, xi]
        self.xr = T['xr'][:, xi]
        self.fund = T['fund'][:, xi]
        self.mxh = T['mxh'][:, xi]
        self.mx = T['mx'][:, xi]
        self.flag = T['flag'][:, xi]
        self.mk, self.hm, self.fh, self.fc = T['mk'], T['hm'], T['fh'], T['fc']


def run(K, cand, X, k0, kl, debug=None):
    """K: K_max; cand: CandB1; X: XView; entries for hours k in [k0, kl); fold closes at kl.
    Returns (trades DataFrame, equity DataFrame, metrics dict)."""
    assert 0 <= k0 < kl < CB.NH
    K = int(K)
    J, XR, FUND, MXH, RS = X.j, X.xr, X.fund, X.mxh, X.rs
    MK, FC, HM = X.mk, X.fc, X.hm
    opn = []                    # [c, cid, ke, N, kx, j, xr, fund, mxh, rs]
    trades = []
    last_entry = {}
    held = set()
    realized = 0.0
    hours = cand.hours
    hs = hours[(hours >= k0) & (hours < kl)].tolist()
    for k in hs:
        if opn:
            keep = []
            for p in opn:
                if p[4] <= k:
                    trades.append(p)
                    realized += _net(p)
                    held.discard(p[0])
                else:
                    keep.append(p)
            opn = keep
        if len(opn) >= K:
            continue
        eq = INIT + realized
        for p in opn:
            h = k - p[2]
            eq += p[3] * (1.0 - MK.item(p[1], h) + FC.item(p[1], h) - FEE)
        if debug is not None:
            debug.append((k, eq))
        size = eq * EXPO / K
        if size <= 0:
            continue
        for c, cid in cand.by_k[k]:
            if len(opn) >= K:
                break
            if c in held:
                continue
            le = last_entry.get(c)
            if le is not None and k - le <= COOL:
                continue
            j = int(J[cid])
            kx = k + (j + 59) // 60
            if kx > kl:
                h = kl - k
                p = [c, cid, k, size, kl, 60 * h, float(MK[cid, h]), float(FC[cid, h]), float(HM[cid, h]), CB.R_EOD]
            else:
                p = [c, cid, k, size, kx, j, float(XR[cid]), float(FUND[cid]), float(MXH[cid]), int(RS[cid])]
            opn.append(p)
            held.add(c)
            last_entry[c] = k
    for p in opn:
        trades.append(p)
        realized += _net(p)
    trades.sort(key=lambda p: (p[4], p[2], p[0]))
    return _ledger(trades, X, k0, kl)


def _net(p):
    N, xr, fu = p[3], p[6], p[7]
    return N * (1.0 - xr) - N * FEE - N * xr * FEE + N * fu


def _ledger(trades, X, k0, kl):
    MK, HM, FH = X.mk, X.hm, X.fh
    n = kl - k0 + 1
    cashd = np.zeros(n + 1)
    unr = np.zeros(n)
    notl = np.zeros(n)
    adjw = np.zeros(n)
    rows = []
    for p in trades:
        c, cid, ke, N, kx, j, xr, fu, mxh, rs = p
        i0, ix, hx = ke - k0, kx - k0, kx - ke
        cashd[i0] -= N * FEE
        hf = min((j + 1) // 60, hx)
        if hf > 0:
            cashd[i0 + 1:i0 + hf + 1] += N * FH[cid, 1:hf + 1]
        cashd[ix] += N * (1.0 - xr) - N * xr * FEE
        unr[i0:ix] += N * (1.0 - MK[cid, 0:hx])
        notl[i0:ix] += N * MK[cid, 0:hx]
        if hx > 1:
            adjw[i0 + 1:ix] += N * (HM[cid, 1:hx] - MK[cid, 1:hx])
        adjw[ix] += N * max(0.0, mxh - xr)
        gross = N * (1.0 - xr)
        fees = N * FEE + N * xr * FEE
        funding = N * fu
        net = gross - fees + funding
        flag = int(X.flag[cid]) if rs != CB.R_EOD else 0
        rows.append((c, cid, ke, kx, j, N, xr, CB.RNAMES[rs], gross, fees, funding, net, net / N, flag,
                     float(X.mx[cid]) if rs != CB.R_EOD else float(np.max(X.hm[cid, :hx + 1]))))
    cash = INIT + np.cumsum(cashd)[:n]
    eq = cash + unr
    eqw = eq - adjw
    with np.errstate(divide='ignore', invalid='ignore'):
        expo = np.where(eq > 0, notl / eq, np.nan)
    tms = CB.H0 + np.arange(CB.NH, dtype=np.int64) * CB.H
    tr = pd.DataFrame(rows, columns=list(TCOLS))
    tr['dca'] = 0
    eqdf = pd.DataFrame({'t': tms[k0:kl + 1], 'eq': eq, 'eq_worst': eqw, 'expo': expo})
    cash_end = INIT + float(cashd.sum())
    m = S.metrics(tr, eqdf, cash_end, tms, k0, kl)
    for r in ('time_sub', 'gap'):
        m.pop('x_' + r, None)
    m['x_miss'] = float((tr['reason'] == 'miss').mean()) if len(tr) else np.nan
    m['eq_end_ledger_minus_eq'] = float(cash_end - eq[-1])
    return tr, eqdf, m


def run_all(K, cand, X):
    out = {}
    for name, a, b in FOLDS:
        k0 = S.kidx(S.ms(a))
        kl = S.kidx(S.ms(b)) - 1
        tr, eq, m = run(K, cand, X, k0, kl)
        for kk, v in m.items():
            out['%s_%s' % (name, kk)] = v
    return out


def load_class(cz, W, E, z):
    key = 'W%d_%s_%.1f' % (W, E, z)
    return CandB1(cz[key + '_k'], cz[key + '_c'], cz[key + '_s'], cz[key + '_cid'])
