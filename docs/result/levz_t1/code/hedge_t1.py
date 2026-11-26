"""LEVZ T1 HEDGE overlay (PREREG_LEVZ_T1 sec 3 + ADD1 A1-A3). Short side = B1 port.run logic (copied loop, B1 port._ledger reused
unchanged) with short size = equity x 0.60 / ((1 + h) x K); long hedge leg(s) in BTC or 50 % BTC + 50 % ETH:
- hour k (decision bar T_k): price P_k = close of the 1m bar open T_k (same minute as short entries / marks mk = path[60 h]).
- funding at boundary T_k for units held since k - 1: cash -= units x close(bar ending T_k) x FR[k, coin] (long pays when rate > 0).
- after the short exits / entries of hour k: target long notional L_k = h x sum over OPEN shorts of N x mk (current short notional),
  split by weight; rebalance at P_k; fee 0.07 % on |traded notional|. At kl (fold end) the hedge is closed (target 0).
- equity used for sizing at k = B1 short equity + hedge equity (cash + units x P_k, before the rebalance of hour k).
- eq (close-hour) = short eq + hedge eq after rebalance; eq_worst = short eq_worst (B1) + hedge eq - units_{k-1} x (P_k - min 1m close
  of window (T_{k-1}, T_k]) (ADD1 A3). h = 0 => identical to B1 port.run (test c).
Metrics = B0 sim.metrics on the combined equity; acct_err = sum short net + hedge net - (cash end - INIT); extra hedge_* columns."""
import os
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common_t1 as C
sys.path.pop(0)
import numpy as np

CB = C.CB
P = C.b1('port')
S = P.S
INIT, FEE, EXPO, COOL = P.INIT, P.FEE, P.EXPO, P.COOL
BTC, ETH = 'BTCUSDT', 'ETHUSDT'


class Leg:
    """hourly arrays of one hedge instrument: P[k] = close 1m at minute 60k, PF[k] = close at 60k - 1, PMIN[k] = min close over
    minutes (60(k-1), 60k], FR[k] funding rate settled at T_k."""
    def __init__(self, c1m, fr, w):
        x = np.asarray(c1m, dtype=np.float64)
        nh = len(x) // 60
        assert np.isfinite(x[60:]).all(), 'hedge instrument has missing 1m closes'
        self.P = x[0:60 * nh:60]
        self.PF = np.concatenate([[np.nan], x[59:60 * nh:60]])[:nh]
        mn = np.full(nh, np.nan)
        mn[1:] = x[1:60 * (nh - 1) + 1].reshape(nh - 1, 60).min(axis=1)
        self.PMIN = mn
        self.FR = np.asarray(fr, dtype=np.float64)
        self.w = float(w)


def make_legs(inst, mm=None, FR=None):
    syms = CB.meta()['syms']
    if mm is None:
        mm = np.load(CB.WORK + '/close1m.npy', mmap_mode='r')
    if FR is None:
        FR = np.load(CB.L2 + '/work/inputs.npz')['FR']
    names = {'BTC': ((BTC, 1.0),), 'BTCETH': ((BTC, 0.5), (ETH, 0.5))}[inst]
    return [Leg(mm[syms.index(s)], FR[:, syms.index(s)], w) for s, w in names]


def run(K, cand, X, k0, kl, h, legs):
    """same contract as port.run (+ h, legs). Returns (trades, equity, metrics)."""
    assert 0 <= k0 < kl < CB.NH
    K = int(K)
    h = float(h)
    J, XR, FUND, MXH, RS = X.j, X.xr, X.fund, X.mxh, X.rs
    MK, FC, HM = X.mk, X.fc, X.hm
    opn = []
    trades = []
    last_entry = {}
    held = set()
    realized = 0.0
    cand_k = set(cand.hours[(cand.hours >= k0) & (cand.hours < kl)].tolist())
    nl = len(legs)
    units = [0.0] * nl
    hcash = 0.0
    n = kl - k0 + 1
    he = np.zeros(n)
    hadj = np.zeros(n)
    hval = np.zeros(n)
    hfee = hfund = htrade = 0.0
    for k in range(k0, kl + 1):
        i = k - k0
        # hedge: funding at boundary T_k, mark
        hv = 0.0
        for li, L in enumerate(legs):
            if units[li] != 0.0:
                f = units[li] * L.PF[k] * L.FR[k]
                hcash -= f
                hfund -= f
                hadj[i] += units[li] * (L.P[k] - L.PMIN[k])
            hv += units[li] * L.P[k]
        # short exits: processed ONLY at candidate hours, exactly as port.run (same float summation order of 'realized')
        if k in cand_k and opn:
            keep = []
            for p in opn:
                if p[4] <= k:
                    trades.append(p)
                    realized += P._net(p)
                    held.discard(p[0])
                else:
                    keep.append(p)
            opn = keep
        if k in cand_k and len(opn) < K:
            eq = INIT + realized
            for p in opn:
                hh = k - p[2]
                eq += p[3] * (1.0 - MK.item(p[1], hh) + FC.item(p[1], hh) - FEE)
            eq += hcash + hv
            size = eq * EXPO / ((1.0 + h) * K)
            if size > 0:
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
                        hh = kl - k
                        p = [c, cid, k, size, kl, 60 * hh, float(MK[cid, hh]), float(FC[cid, hh]), float(HM[cid, hh]), CB.R_EOD]
                    else:
                        p = [c, cid, k, size, kx, j, float(XR[cid]), float(FUND[cid]), float(MXH[cid]), int(RS[cid])]
                    opn.append(p)
                    held.add(c)
                    last_entry[c] = k
        # hedge rebalance after the short decisions of hour k
        if k < kl:
            sn = 0.0
            for p in opn:
                if p[4] > k:
                    sn += p[3] * MK.item(p[1], k - p[2])
            tgt = h * sn
        else:
            tgt = 0.0
        hv = 0.0
        for li, L in enumerate(legs):
            u_new = tgt * L.w / L.P[k]
            du = u_new - units[li]
            if du != 0.0:
                fee = abs(du) * L.P[k] * FEE
                hcash -= du * L.P[k] + fee
                htrade -= du * L.P[k]
                hfee += fee
                units[li] = u_new
            hv += units[li] * L.P[k]
        he[i] = hcash + hv
        hval[i] = hv
    for p in opn:
        trades.append(p)
        realized += P._net(p)
    trades.sort(key=lambda p: (p[4], p[2], p[0]))
    tr, eqdf, m0 = P._ledger(trades, X, k0, kl)
    assert all(u == 0.0 for u in units)
    eq_s = eqdf['eq'].values.copy()
    notl = eqdf['expo'].values * eq_s
    eqdf['eq'] = eq_s + he
    eqdf['eq_worst'] = eqdf['eq_worst'].values + he - hadj
    with np.errstate(divide='ignore', invalid='ignore'):
        eqdf['expo'] = np.where(eqdf['eq'].values > 0, (notl + hval) / eqdf['eq'].values, np.nan)
    cash_end_s = INIT + (float(tr['net'].sum()) if len(tr) else 0.0) - m0['acct_err']
    tms = CB.H0 + np.arange(CB.NH, dtype=np.int64) * CB.H
    m = S.metrics(tr, eqdf, cash_end_s, tms, k0, kl)
    for r in ('time_sub', 'gap'):
        m.pop('x_' + r, None)
    m['x_miss'] = float((tr['reason'] == 'miss').mean()) if len(tr) else np.nan
    m['acct_err'] = m0['acct_err']                                  # short ledger invariant (B1, unchanged)
    m['eq_end_ledger_minus_eq'] = m0['eq_end_ledger_minus_eq'] + (hcash - float(he[-1]))
    m['hedge_acct_err'] = hcash - (htrade - hfee + hfund)            # hedge cash == sum of its flows
    m['hedge_pnl'] = hcash
    m['hedge_fees'] = hfee
    m['hedge_funding'] = hfund
    m['hedge_val_mean'] = float(hval.mean())
    return tr, eqdf, m


def run_all(K, cand, X, h, legs):
    out = {}
    for name, a, b in P.FOLDS:
        k0 = S.kidx(S.ms(a))
        kl = S.kidx(S.ms(b)) - 1
        tr, eq, m = run(K, cand, X, k0, kl, h, legs)
        for kk, v in m.items():
            out['%s_%s' % (name, kk)] = v
    return out
