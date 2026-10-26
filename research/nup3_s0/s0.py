#!/usr/bin/env python3
"""NUP3-S0 (docs/prereg/PREREG_NUP3_S0.md, commit b7267738, sha256 4e45950f...) - CHI DO tren artefact san co.
Lenh = cum (sym, end) cua printDone; gio vao = t0 = leg dau cum (+07). PnL/notional = tong cac leg cua cum.
Lenh them = cum A2 co t0 trong ky, KHONG khop cum B0 cung seed (cung sym, |dt0| <= 60s, greedy nhu score.match_groups).
W_burst: #cum A2 (moi, tuc t0) trong [t-60', t) >= 10
W_mkt  : ALT_EW 24h tai phut t-1 = exp(sum ew_r bar [t-1440', t-1']) - 1 <= -8 %
W_book : U_B0(t) = sum notional leg B0 (ts < t <= te) / (CAP0 + sum pnl leg B0 te < t) >= 0.20
W_quiet: NGOAI = B0 khong mo cum nao trong [t-24h, t)
Out: docs/result/nup3_s0/*.csv ; trung gian ~/claude_master/nup3_s0_wk/
"""
import json
import os
import sys

import numpy as np
import pandas as pd

REPO = "/home/ubuntu/claude_master/vz_e1_wt"
KS = "/home/ubuntu/kaggle_sim/out/"
WK = "/home/ubuntu/claude_master/nup3_s0_wk"
OUTD = REPO + "/docs/result/nup3_s0"
EW_DEV = "/home/ubuntu/claude_master/edge_attr/index.npz"
EW_HO = "/home/ubuntu/claude_master/tsx/ho/ew_out/ew_2026.npz"
CAP0 = 35000.0
H7 = 7 * 3600 * 1000
MM = 60000
DAY = 86400000
STRESS = 0.002
DEV_SEEDS = ["a1", "s7", "s13", "s21", "s99", "s123", "s777", "s2024"]
HO_SEEDS = [42, 7, 13, 21, 99, 123, 777, 2024]
YEARS = [2022, 2023, 2024, 2025]
WS = ["W_burst", "W_mkt", "W_book", "W_quiet"]


def lms(s):
    return int(np.datetime64(s, "ms").astype(np.int64))


PER = {"DEV": (lms("2022-01-01"), lms("2026-01-01")), "HO": (lms("2026-01-01"), lms("2026-10-01"))}
YPER = {str(y): (lms("%d-01-01" % y), lms("%d-01-01" % (y + 1))) for y in YEARS}


def to_ms(col):
    t = pd.to_datetime(col.astype(str).str.strip(), format="%Y%m%d %H:%M")
    return t.to_numpy().astype("datetime64[ms]").astype(np.int64)


def load(tag):
    d = pd.read_csv(KS + tag + "/storage/printDone.csv", index_col=False)
    d.columns = [c.strip() for c in d.columns]
    for c in ("quantity", "entry", "pnl"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    n0 = len(d)
    d = d.dropna(subset=["pnl", "quantity", "entry"]).copy()
    assert len(d) == n0, tag
    d["sym"] = d["sym"].astype(str).str.strip()
    d["ts_l"] = to_ms(d["start"])
    d["te_l"] = to_ms(d["end"])
    assert d.ts_l.dtype == np.int64 and (d.te_l >= d.ts_l).all()
    d["notional"] = d["quantity"] * d["entry"]
    d["pnl_s"] = d["pnl"] - STRESS * d["notional"]
    return d.sort_values(["ts_l", "sym"], kind="mergesort").reset_index(drop=True)


def clusters(d):
    c = d.groupby(["sym", "te_l"], sort=False).agg(t0=("ts_l", "min"), n=("sym", "size"), pnl=("pnl", "sum"),
                                                   notional=("notional", "sum"), pnl_s=("pnl_s", "sum")).reset_index()
    return c.sort_values(["t0", "sym", "te_l"], kind="mergesort").reset_index(drop=True)


def match(A_sym, A_t, B_sym, B_t):
    """= score.match_groups: duyet A theo thu tu t; voi moi A chon B chua dung cung sym |dt| nho nhat (hoa -> B som hon), khop neu <= 60s."""
    A_t = np.asarray(A_t, np.int64)
    B_t = np.asarray(B_t, np.int64)
    usedB = np.zeros(len(B_t), bool)
    mA = np.zeros(len(A_t), bool)
    byB, byA = {}, {}
    for j, s in enumerate(B_sym):
        byB.setdefault(s, []).append(j)
    for i, s in enumerate(A_sym):
        byA.setdefault(s, []).append(i)
    for s, ia in byA.items():
        cand = sorted(byB.get(s, []), key=lambda j: (B_t[j], j))
        bt = B_t[cand] if cand else np.zeros(0, np.int64)
        for i in ia:
            ta = A_t[i]
            lo, hi = np.searchsorted(bt, ta - 60000, "left"), np.searchsorted(bt, ta + 60000, "right")
            best, bd = None, 61000
            for k in range(lo, hi):
                j = cand[k]
                if usedB[j]:
                    continue
                dd = abs(int(bt[k]) - int(ta))
                if dd < bd:
                    bd, best = dd, j
            if best is not None and bd <= 60000:
                usedB[best] = True
                mA[i] = True
    return mA, usedB


def inwin(t, w):
    return (t >= w[0]) & (t < w[1])


class EW:
    def __init__(self):
        z, h = np.load(EW_DEV), np.load(EW_HO)
        m = h["ew_ts"] >= lms("2026-01-01")
        t = np.concatenate([z["ew_ts"], h["ew_ts"][m]])
        r = np.concatenate([z["ew_r"], h["ew_r"][m]])
        assert t.dtype == np.int64 and np.all(np.diff(t) > 0) and np.all(t % MM == 0)
        self.g0 = int(t[0])
        n = int((t[-1] - self.g0) // MM) + 1
        R, N = np.zeros(n), np.zeros(n, np.int64)
        k = (t - self.g0) // MM
        R[k], N[k] = r, 1
        self.n = n
        self.C = np.concatenate([[0.0], np.cumsum(R)])
        self.CN = np.concatenate([[0], np.cumsum(N)])
        self.info = dict(n_bar=int(len(t)), first=int(t[0]), last=int(t[-1]), grid=n)

    def ret24(self, tu):
        assert np.all((tu - self.g0) % MM == 0)
        i = (tu - self.g0) // MM            # bar mo luc t; cua so = bar [i-1440, i-1]
        a = i - 1440
        ok = (a >= 0) & (i <= self.n)
        ii, aa = np.clip(i, 0, self.n), np.clip(a, 0, self.n)
        s = self.C[ii] - self.C[aa]
        cnt = self.CN[ii] - self.CN[aa]
        ret = np.where(ok & (cnt > 0), np.expm1(s), np.nan)
        return ret, np.where(ok, cnt, 0)


def features(ex_t, a2c, b0d, b0c, ew):
    """ex_t: t0 gio +07 ms cua lenh can tinh. Moi dac trung chi dung du lieu < t."""
    t = np.asarray(ex_t, np.int64)
    tu = t - H7
    T = np.sort(a2c.t0.to_numpy(np.int64))
    burst = np.searchsorted(T, t, "left") - np.searchsorted(T, t - 3600000, "left")
    ret, nbar = ew.ret24(tu)
    ts, te = b0d.ts_l.to_numpy(np.int64), b0d.te_l.to_numpy(np.int64)
    nt, pn = b0d.notional.to_numpy(float), b0d.pnl.to_numpy(float)
    o1, o2 = np.argsort(ts, kind="mergesort"), np.argsort(te, kind="mergesort")
    ts_s, te_s = ts[o1], te[o2]
    cn1 = np.concatenate([[0.0], np.cumsum(nt[o1])])
    cn2 = np.concatenate([[0.0], np.cumsum(nt[o2])])
    cp2 = np.concatenate([[0.0], np.cumsum(pn[o2])])
    k1, k2 = np.searchsorted(ts_s, t, "left"), np.searchsorted(te_s, t, "left")
    open_n = np.maximum(cn1[k1] - cn2[k2], 0.0)   # leg ts < t va te >= t (te >= ts)
    eq = CAP0 + cp2[k2]
    U = open_n / eq
    B = np.sort(b0c.t0.to_numpy(np.int64))
    q24 = np.searchsorted(B, t, "left") - np.searchsorted(B, t - DAY, "left")
    return pd.DataFrame(dict(burst=burst, mkt_ret=ret, mkt_nbar=nbar, U=U, b0_open_n=open_n, b0_eq=eq, b0_cnt24=q24))


def run_seed(phase, seed, ew):
    if phase == "DEV":
        ta, tb = "nup-a2-%s" % seed, "tsx-x14-%s" % seed
    else:
        ta, tb = "nup-ho-a2-s%d" % seed, "tsx-ho-x14-s%d" % seed
    a2d, b0d = load(ta), load(tb)
    a2c, b0c = clusters(a2d), clusters(b0d)
    w = PER[phase]
    A = a2c[inwin(a2c.t0.to_numpy(), w)].reset_index(drop=True)
    B = b0c[inwin(b0c.t0.to_numpy(), w)].reset_index(drop=True)
    mA, uB = match(A.sym.tolist(), A.t0.to_numpy(), B.sym.tolist(), B.t0.to_numpy())
    A["common"] = mA
    B["matched"] = uB
    F = features(A.t0.to_numpy(), a2c, b0d, b0c, ew)
    A = pd.concat([A, F], axis=1)
    A["W_burst"] = A.burst >= 10
    A["W_mkt"] = A.mkt_ret <= -0.08
    A["W_book"] = A.U >= 0.20
    A["W_quiet"] = A.b0_cnt24 > 0                  # TRONG = B0 co mo cum trong 24h truoc; NGOAI = quiet
    A["phase"], A["seed"] = phase, str(seed)
    B["phase"], B["seed"] = phase, str(seed)
    # leg-level (NUP) de doi chieu
    al = a2d[inwin(a2d.ts_l.to_numpy(), w)]
    bl = b0d[inwin(b0d.ts_l.to_numpy(), w)]
    mL, uL = match(al.sym.tolist(), al.ts_l.to_numpy(), bl.sym.tolist(), bl.ts_l.to_numpy())
    mc = dict(phase=phase, seed=str(seed), a2_cl=len(A), b0_cl=len(B), common=int(mA.sum()), extra=int((~mA).sum()),
              lost=int(len(B) - uB.sum()), leg_common=int(mL.sum()), leg_new=int((~mL).sum()), leg_lost=int(len(bl) - uL.sum()),
              a2_cl_multi=int((A.n > 1).sum()), mkt_nan=int(A.mkt_ret.isna().sum()), mkt_nbar_min=int(A.mkt_nbar.min()))
    return A, B, mc, a2c, b0c


def agg(df):
    n = len(df)
    nt = df.notional.sum()
    return dict(n=n, pnl=float(df.pnl.sum()), pnl_s=float(df.pnl_s.sum()), notional=float(nt),
                roi=float(100 * df.pnl.sum() / nt) if nt else np.nan, roi_s=float(100 * df.pnl_s.sum() / nt) if nt else np.nan)


def periods(phase):
    if phase == "DEV":
        return [(y, YPER[y], 1.0 if y != "2024" else 366 / 365) for y in YPER] + [("DEV_T", PER["DEV"], 4.0)]
    return [("HO", PER["HO"], 273 / 365)]


def group_rows(A, B):
    rows = []
    ph, sd = A.phase.iloc[0], A.seed.iloc[0]
    X = A[~A.common]
    for pname, pw, yrs in periods(ph):
        Xp = X[inwin(X.t0.to_numpy(), pw)]
        Bp = B[inwin(B.t0.to_numpy(), pw)]
        rows.append(dict(phase=ph, seed=sd, period=pname, W="B0", group="ALL", yrs=yrs, **agg(Bp)))
        rows.append(dict(phase=ph, seed=sd, period=pname, W="EXTRA", group="ALL", yrs=yrs, **agg(Xp)))
        for W in WS:
            fl = Xp[W].to_numpy(bool)
            rows.append(dict(phase=ph, seed=sd, period=pname, W=W, group="TRONG", yrs=yrs, **agg(Xp[fl])))
            rows.append(dict(phase=ph, seed=sd, period=pname, W=W, group="NGOAI", yrs=yrs, **agg(Xp[~fl])))
    return rows


def gini(x):
    x = np.sort(np.asarray(x, float))
    if x.sum() == 0:
        return np.nan
    n = len(x)
    return float((2 * np.arange(1, n + 1) - n - 1).dot(x) / (n * x.sum()))


def episodes(t):
    t = np.sort(np.asarray(t, np.int64))
    if not len(t):
        return []
    br = np.where(np.diff(t) >= 6 * 3600000)[0]
    st = np.concatenate([[0], br + 1])
    en = np.concatenate([br, [len(t) - 1]])
    return list(zip(t[st], t[en]))


def daily_rows(A, B, b0c_all):
    ph, sd = A.phase.iloc[0], A.seed.iloc[0]
    X = A[~A.common]
    b0days = set((b0c_all.t0.to_numpy(np.int64) - H7) // DAY)
    b0ep = episodes(b0c_all.t0.to_numpy(np.int64))
    eps_s = np.array([e[0] for e in b0ep], np.int64)
    eps_e = np.array([e[1] for e in b0ep], np.int64)
    rows = []
    for pname, pw, yrs in periods(ph):
        Xp = X[inwin(X.t0.to_numpy(), pw)]
        Bp = B[inwin(B.t0.to_numpy(), pw)]
        xd = (Xp.t0.to_numpy(np.int64) - H7) // DAY
        bd = (Bp.t0.to_numpy(np.int64) - H7) // DAY
        on_nob0 = np.array([d not in b0days for d in xd], bool)
        ud = np.unique(xd)
        ud_nob0 = np.array([d not in b0days for d in ud], bool)
        d0, d1 = (pw[0] - H7) // DAY, (pw[1] - 1 - H7) // DAY
        days = np.arange(d0, d1 + 1)
        px = pd.Series(Xp.pnl.to_numpy(), index=xd).groupby(level=0).sum().reindex(days, fill_value=0.0)
        pb = pd.Series(Bp.pnl.to_numpy(), index=bd).groupby(level=0).sum().reindex(days, fill_value=0.0)
        corr = float(np.corrcoef(px.to_numpy(), pb.to_numpy())[0, 1]) if px.std() > 0 and pb.std() > 0 else np.nan
        tot = Xp.pnl.sum()
        top10 = float(100 * np.sort(px.to_numpy())[::-1][:10].sum() / tot) if tot != 0 else np.nan
        mon = pd.Series(1, index=pd.to_datetime(Xp.t0.to_numpy(), unit="ms").to_period("M")).groupby(level=0).sum()
        allm = pd.period_range(pd.Timestamp(pw[0], unit="ms"), pd.Timestamp(pw[1] - 1, unit="ms"), freq="M")
        mon = mon.reindex(allm, fill_value=0)
        top10m = float(100 * np.sort(mon.to_numpy())[::-1][:10].sum() / mon.sum()) if mon.sum() else np.nan
        xe = episodes(Xp.t0.to_numpy(np.int64))
        be = episodes(Bp.t0.to_numpy(np.int64))
        nonov = 0
        for s, e in xe:   # giao neu ton tai dot B0 [bs, be] voi bs <= e va be >= s
            k = np.searchsorted(eps_s, e, "right")
            hit = bool(k > 0 and np.any(eps_e[:k] >= s))
            nonov += not hit
        rows.append(dict(phase=ph, seed=sd, period=pname, yrs=yrs, n_extra=len(Xp), pct_extra_on_nob0_day=100 * on_nob0.mean() if len(Xp) else np.nan,
                         days_extra_y=len(ud) / yrs, days_extra_b0day_y=int((~ud_nob0).sum()) / yrs, days_extra_nob0day_y=int(ud_nob0.sum()) / yrs,
                         days_b0_y=len(np.unique(bd)) / yrs, n_months=len(allm), gini_month=gini(mon.to_numpy()), top10_month_pct=top10m,
                         corr_daily_pnl=corr, top10_day_pct_pnl=top10, ep_extra_y=len(xe) / yrs, ep_b0_y=len(be) / yrs,
                         ep_extra_nonoverlap_y=nonov / yrs, pct_ep_extra_nonoverlap=100 * nonov / len(xe) if xe else np.nan))
    return rows


def main():
    os.makedirs(WK, exist_ok=True)
    os.makedirs(OUTD, exist_ok=True)
    ew = EW()
    print("EW", ew.info)
    G, D, M, XS = [], [], [], []
    for ph, seeds in (("DEV", DEV_SEEDS), ("HO", HO_SEEDS)):
        for s in seeds:
            A, B, mc, a2c, b0c = run_seed(ph, s, ew)
            G += group_rows(A, B)
            D += daily_rows(A, B, b0c)
            M.append(mc)
            A.to_parquet(WK + "/A_%s_%s.parquet" % (ph, s), index=False)
            B.to_parquet(WK + "/B_%s_%s.parquet" % (ph, s), index=False)
            print(mc, flush=True)
    G, D, M = pd.DataFrame(G), pd.DataFrame(D), pd.DataFrame(M)
    G.to_csv(OUTD + "/groups_by_seed.csv", index=False)
    D.to_csv(OUTD + "/daily_by_seed.csv", index=False)
    M.to_csv(OUTD + "/match_counts.csv", index=False)
    # median qua seed
    G["n_y"] = G.n / G.yrs
    med = G.groupby(["phase", "period", "W", "group"]).agg(n_y=("n_y", "median"), roi=("roi", "median"), roi_s=("roi_s", "median"),
                                                          pnl=("pnl", "median"), pnl_s=("pnl_s", "median"),
                                                          pct_seed_pos_s=("pnl_s", lambda x: 100 * (x > 0).mean()),
                                                          n_seed_pos_s=("pnl_s", lambda x: int((x > 0).sum()))).reset_index()
    med.to_csv(OUTD + "/groups_median.csv", index=False)
    Dm = D.groupby(["phase", "period"]).median(numeric_only=True).reset_index()
    Dm.to_csv(OUTD + "/daily_median.csv", index=False)
    # luat S0
    V = []
    b0_ny = med[(med.phase == "DEV") & (med.period == "DEV_T") & (med.W == "B0")].n_y.iloc[0]
    b0_ny_ho = med[(med.phase == "HO") & (med.W == "B0")].n_y.iloc[0]
    for W in WS:
        g = med[(med.W == W) & (med.group == "NGOAI")]
        dt = g[(g.phase == "DEV") & (g.period == "DEV_T")].iloc[0]
        ypos = int(sum(g[(g.phase == "DEV") & (g.period == str(y))].pnl_s.iloc[0] > 0 for y in YEARS))
        ho = g[g.phase == "HO"].iloc[0]
        c1 = bool(dt.roi_s >= 1.0 and ypos >= 3)
        c2 = bool(ho.pnl_s > 0 and ho.n_seed_pos_s >= 5)
        c3 = bool(dt.n_y >= 0.5 * b0_ny)
        V.append(dict(W=W, dev_n_y=dt.n_y, b0_n_y=b0_ny, ratio_n=dt.n_y / b0_ny, ho_n_y=ho.n_y, ho_ratio_n=ho.n_y / b0_ny_ho,
                      dev_roi=dt.roi, dev_roi_s=dt.roi_s, dev_pnl_s=dt.pnl_s, dev_years_pos=ypos, ho_pnl_s=ho.pnl_s,
                      ho_seed_pos=int(ho.n_seed_pos_s), C1=c1, C2=c2, C3=c3, PASS=c1 and c2 and c3))
    V = pd.DataFrame(V)
    V.to_csv(OUTD + "/verdict.csv", index=False)
    pd.set_option("display.width", 250)
    pd.set_option("display.max_columns", 40)
    print(M.to_string(index=False))
    print(med.to_string(index=False))
    print(V.to_string(index=False))
    print(Dm.to_string(index=False))
    json.dump(dict(ew=ew.info), open(OUTD + "/run_info.json", "w"), indent=1)


if __name__ == "__main__":
    main()
