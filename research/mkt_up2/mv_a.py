#!/usr/bin/env python3
"""MKT_UP2 tang A - dung PREREG_MKT_UP2.md (233d9679) + addendum 1 (9c326745). Khong tune, khong bien the, chay 1 lan.
TIMING (kiem tu rex_s0.py): panel day t = nen k1d mo luc 00:00 UTC ngay t, close t = gia luc 00:00 UTC t+1.
  feature panel ngay t dung close <= close t; y1 = CF(t+1)/C(t)-1, y3 = CF(t+3)/C(t)-1 (SIMPLE return, CF = close ffill sau delist).
  => moc quyet dinh cua dong t = T(t) = 00:00 UTC (t+1). Feature thi truong 18 cot tinh tai T(t), chi dung phut ts < T(t)
  (index.npz: r[ts] = log(close_ts / close_{ts-1m}), ts = open-time => tong r[ts<x] = log-gia tai thoi diem x).
  Label dong t dung close t -> close t+3; label NaN neu t+3 >= 2026-01-01 (khong dung gia 2026).
Usage: mv_a.py [quick]"""
import json
import logging
import sys
import warnings

import numpy as np
import pandas as pd
import pyarrow.dataset as pads
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import StandardScaler
import lightgbm as lgb

QUICK = len(sys.argv) > 1 and sys.argv[1] == "quick"
OUT = "/home/ubuntu/claude_master/mkt_up2"
TAG = "mv_a_quick" if QUICK else "mv_a"
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", force=True,
                    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler(OUT + "/%s.log" % TAG, mode="w")])
log = logging.getLogger("mv")
warnings.simplefilter("ignore")
DAY0 = pd.Timestamp("20210701")
MS_D = 86400000
SQ = np.sqrt(1440.0)
HO = pd.Timestamp("2026-01-01")
LAST_LAB = pd.Timestamp("2025-12-28")      # t+3 <= 2025-12-31
TR0 = pd.Timestamp("2022-01-01")           # dong du 27 feature dau tien (S1 bat dau 2022-01-01)

# ---------------- index.npz + 18 feature thi truong (giong mu_a.py) ----------------
z = np.load("/home/ubuntu/claude_master/edge_attr/index.npz")
SER = {"ew": (z["ew_ts"].astype(np.int64), z["ew_r"].astype(np.float64)),
       "bt": (z["bt_ts"].astype(np.int64), z["bt_r"].astype(np.float64))}
for k, (ts, r) in SER.items():
    assert np.all(np.diff(ts) > 0) and not np.isnan(r).any()
    log.info("%s: %d phut %s -> %s", k, len(ts), pd.to_datetime(ts[0], unit="ms"), pd.to_datetime(ts[-1], unit="ms"))


def feat_one(ts, r, t):
    n = np.searchsorted(ts, t, "left")
    ts, r = ts[:n], r[:n]
    cum0 = np.concatenate([[0.0], np.cumsum(r)])

    def cf(x):
        return cum0[np.searchsorted(ts, x, "left")]
    c_t = cum0[n]
    f = {}
    for d in (1, 3, 7, 30):
        f["ret%dd" % d] = c_t - cf(t - d * MS_D)
    for d in (1, 7):
        lo = np.searchsorted(ts, t - d * MS_D, "left")
        f["vol%dd" % d] = float(np.std(r[lo:n], ddof=1) * SQ) if n - lo >= 2 else np.nan
    lo = np.searchsorted(ts, t - 30 * MS_D, "left")
    w = cum0[lo:n + 1]
    f["dmax30"] = c_t - w.max()
    f["dmin30"] = c_t - w.min()
    return f


def mfeats(t, ser=SER):
    fe = feat_one(*ser["ew"], t)
    fb = feat_one(*ser["bt"], t)
    o = {"ew_" + k: v for k, v in fe.items()}
    o.update({"bt_" + k: v for k, v in fb.items()})
    o["ewmbt_ret7d"] = fe["ret7d"] - fb["ret7d"]
    o["ewmbt_ret30d"] = fe["ret30d"] - fb["ret30d"]
    return o


MF = (["ew_ret1d", "ew_ret3d", "ew_ret7d", "ew_ret30d", "ew_vol1d", "ew_vol7d", "ew_dmax30", "ew_dmin30"]
      + ["bt_ret1d", "bt_ret3d", "bt_ret7d", "bt_ret30d", "bt_vol1d", "bt_vol7d", "bt_dmax30", "bt_dmin30"]
      + ["ewmbt_ret7d", "ewmbt_ret30d"])
assert len(MF) == 18
CUM0 = {k: np.concatenate([[0.0], np.cumsum(r)]) for k, (ts, r) in SER.items()}


def lp(k, x):            # log-gia tai thoi diem x = tong r phut ts < x
    return CUM0[k][np.searchsorted(SER[k][0], np.asarray(x, dtype=np.int64), "left")]


# ---------------- panel + S1 ----------------
P = pd.read_parquet("/home/ubuntu/claude_master/rex/panel.parquet",
                    columns=["day", "sym", "mom1", "mom7", "mom28", "vol30", "lqv30", "br50", "y1", "y3"])
n_all = len(P)
P = P[P.day < HO].reset_index(drop=True)
S = pd.read_parquet("/home/ubuntu/claude_master/rex/pred_s1.parquet")
S = S[S.day < HO]
assert P.day.max() < HO and S.day.max() < HO
log.info("panel: %d dong (loai %d dong >=2026), %s..%s; S1 %d dong %s..%s", len(P), n_all - len(P), P.day.min().date(),
         P.day.max().date(), len(S), S.day.min().date(), S.day.max().date())
P = P.merge(S, on=["day", "sym"], how="left")
y3nan_pre = int(P[(P.day <= LAST_LAB)].y3.isna().sum())
log.info("y3 NaN trong panel ngay <= 2025-12-28: %d (ky vong 0 => dieu kien 'co y3' khong loai coin nao)", y3nan_pre)
S1_miss = int(P[(P.day >= TR0)].score.isna().sum())
log.info("dong panel >=2022 khong co score S1: %d", S1_miss)
Y1 = P.set_index(["day", "sym"])["y1"]

DAYS = pd.date_range("2021-08-01", "2025-12-31", freq="D")
BK = {}   # day -> dict
fb_n, fb_tot, chk3 = 0, 0, []


def baskets(Pd):
    """Pd = cac dong panel cua DUNG 1 ngay t. Tra (B1 df, B2 df). Chi dung cot ngay t."""
    e = Pd[Pd.y3.notna() & Pd.lqv30.notna()].sort_values(["lqv30", "sym"], ascending=[False, True])
    b1 = e.head(30)
    e2 = Pd[Pd.y3.notna() & Pd.score.notna()].sort_values(["score", "sym"], ascending=[False, True])
    b2 = e2.head(10)
    return b1, b2


def bfeats(b1, b2, Pd):
    o = {}
    for nm, b in (("b1", b1), ("b2", b2)):
        for c in ("mom1", "mom7", "mom28", "vol30"):
            o["%s_%s" % (nm, c)] = float(b[c].mean()) if len(b) == (30 if nm == "b1" else 10) else np.nan
    o["br50"] = float(Pd.br50.iloc[0])
    assert Pd.br50.nunique(dropna=False) == 1
    return o


BF = ["b1_mom1", "b1_mom7", "b1_mom28", "b1_vol30", "b2_mom1", "b2_mom7", "b2_mom28", "b2_vol30", "br50"]
FEATS = MF + BF
assert len(FEATS) == 27


def path_inc(b, t):
    """Lo mo tai close t, giu co dinh gio b (trong so deu luc mo, buy&hold). Tra increments [d1,d2,d3] cua mean G_k."""
    global fb_n, fb_tot
    g1 = 1 + b.y1.to_numpy()
    g3 = 1 + b.y3.to_numpy()
    y1n = Y1.reindex(list(zip([t + pd.Timedelta(days=1)] * len(b), b.sym))).to_numpy()
    g2 = g1 * (1 + y1n)
    miss = np.isnan(g2)
    fb_n += int(miss.sum()); fb_tot += len(b)
    g2 = np.where(miss, np.sqrt(np.clip(g1 * g3, 0, None)), g2)
    m = [1.0, g1.mean(), g2.mean(), g3.mean()]
    return [m[1] - m[0], m[2] - m[1], m[3] - m[2]]


rows = []
GP = {d: g for d, g in P.groupby("day")}
for t in DAYS:
    Pd = GP[t]
    b1, b2 = baskets(Pd)
    o = dict(day=t)
    o.update(bfeats(b1, b2, Pd))
    o["n_univ"] = len(Pd)
    o["n_b2"] = len(b2)
    o["rB1"] = float(b1.y3.mean())
    o["rB2"] = float(b2.y3.mean()) if len(b2) == 10 else np.nan
    if t <= LAST_LAB:
        i1 = path_inc(b1, t)
        i2 = path_inc(b2, t) if len(b2) == 10 else [np.nan] * 3
        for k in range(3):
            o["iB1_%d" % (k + 1)] = i1[k]
            o["iB2_%d" % (k + 1)] = i2[k]
        if len(b2) == 10:
            chk3.append(abs(sum(i2) - o["rB2"]))
        chk3.append(abs(sum(i1) - o["rB1"]))
    BK[t] = (list(b1.sym), list(b2.sym))
    rows.append(o)
D = pd.DataFrame(rows).set_index("day")
log.info("path: fallback g2 (coin roi universe ngay t+1) %d/%d = %.4f; max |sum(inc)-mean y3| %.2e", fb_n, fb_tot,
         fb_n / max(fb_tot, 1), max(chk3))
assert max(chk3) < 1e-9
TT = ((DAYS + pd.Timedelta(days=1)).asi8 // 10 ** 6).astype(np.int64)      # moc T(t) = 00:00 UTC t+1
XM = pd.DataFrame([mfeats(int(t)) for t in TT], index=DAYS)[MF]
X = pd.concat([XM, D[BF]], axis=1)[FEATS]
log.info("feature: %d ngay x %d cot; NaN theo nam: %s", len(X), X.shape[1],
         X.isna().any(axis=1).groupby(X.index.year).sum().to_dict())
# ALT_EW 3 ngay: close t -> close t+3 = thoi diem T(t) -> T(t)+3d (simple)
D["rEW"] = np.exp(lp("ew", TT + 3 * MS_D) - lp("ew", TT)) - 1
D["rBT"] = np.exp(lp("bt", TT + 3 * MS_D) - lp("bt", TT)) - 1
lab_ok = D.index <= LAST_LAB
D.loc[~lab_ok, ["rB1", "rB2", "rEW", "rBT"]] = np.nan
D["L1"] = np.where(D.rB1.notna(), (D.rB1 > 0).astype(float), np.nan)
D["L2"] = np.where(D.rB2.notna(), (D.rB2 > 0).astype(float), np.nan)
D["L3"] = np.where(D.rB2.notna() & D.rB1.notna(), (D.rB2 - D.rB1 > 0).astype(float), np.nan)
D.loc[D.index < TR0, ["L2", "L3"]] = np.nan
for L in ("L1", "L2", "L3"):
    log.info("label %s: %d ngay co nhan, ty le 1 = %.3f; %s..%s", L, int(D[L].notna().sum()), float(D[L].mean()),
             D[L].first_valid_index().date(), D[L].last_valid_index().date())

# ---------------- walk-forward ----------------
OOS0 = {"L1": pd.Timestamp("2022-07-01"), "L2": pd.Timestamp("2023-01-01"), "L3": pd.Timestamp("2023-01-01")}
FULL = X.notna().all(axis=1)
V3 = {}
COEF = {}
LABS = ["L1", "L2", "L3"]
for L in LABS:
    D["P_" + L] = np.nan
    D["Pg_" + L] = np.nan
    D["fm_" + L] = pd.NaT
    V3[L] = []
    months = pd.date_range(OOS0[L], "2025-12-01", freq="MS")
    if QUICK:
        months = months[:3].append(months[-2:])
    for m in months:
        tr = (D.index >= TR0) & (D.index <= m - pd.Timedelta(days=3)) & D[L].notna() & FULL
        te = (D.index >= m) & (D.index < m + pd.offsets.MonthBegin(1))
        assert FULL[te].all()
        Xtr, ytr = X[tr].to_numpy(), D.loc[tr, L].to_numpy().astype(int)
        sc = StandardScaler().fit(Xtr)
        lr = LogisticRegression(C=1.0, penalty="l2", max_iter=1000).fit(sc.transform(Xtr), ytr)
        gb = lgb.LGBMClassifier(max_depth=3, n_estimators=200, learning_rate=0.05, random_state=42, verbose=-1).fit(Xtr, ytr)
        D.loc[te, "P_" + L] = lr.predict_proba(sc.transform(X[te].to_numpy()))[:, 1]
        D.loc[te, "Pg_" + L] = gb.predict_proba(X[te].to_numpy())[:, 1]
        D.loc[te, "fm_" + L] = m
        last_t = D.index[tr].max()
        lab_end = last_t + pd.Timedelta(days=4)          # close (t+3) = 00:00 UTC t+4
        first_dec = m + pd.Timedelta(days=1)             # du bao dong t=m lap luc 00:00 UTC m+1
        V3[L].append(dict(moc=str(m.date()), n_train=int(tr.sum()), train_first=str(D.index[tr].min().date()),
                          train_last=str(last_t.date()), label_end=str(lab_end), first_decision=str(first_dec),
                          ok=bool(lab_end <= first_dec), n_test=int(te.sum()), lr_iter=int(lr.n_iter_[0])))
        if m == pd.Timestamp("2025-01-01"):
            COEF[L] = sorted([(FEATS[i], float(lr.coef_[0][i])) for i in range(27)], key=lambda x: -abs(x[1]))
    assert all(v["ok"] for v in V3[L])
    log.info("%s walk-forward %d refit, purge OK; vd %s", L, len(V3[L]), V3[L][0])

# ---------------- E1 ----------------
PER = {"DEV": ("2022-07-01", "2024-12-31"), "2022H2": ("2022-07-01", "2022-12-31"), "2023": ("2023-01-01", "2023-12-31"),
       "2024": ("2024-01-01", "2024-12-31"), "VAL2025": ("2025-01-01", "2025-12-31")}


def pmask(idx, p, L=None):
    a, b = PER[p]
    a = pd.Timestamp(a)
    if L is not None and p == "DEV":
        a = OOS0[L]
    return (idx >= a) & (idx <= pd.Timestamp(b))


def auc(L, col, p):
    m = pmask(D.index, p, L) & D[L].notna() & D[col].notna()
    if m.sum() < 20:
        return None
    yy = D.loc[m, L].to_numpy()
    return dict(auc=float(roc_auc_score(yy, D.loc[m, col])), n=int(m.sum()), base=float(yy.mean()))


AUC, E1 = {}, {}
for L in LABS:
    AUC[L] = {c: {p: auc(L, c + L, p) for p in PER} for c in ("P_", "Pg_")}
    A = {p: (v if v else dict(auc=float("nan"), n=0, base=float("nan"))) for p, v in AUC[L]["P_"].items()}
    yrs = ["2022H2", "2023", "2024"] if L == "L1" else ["2023", "2024"]
    need = 2 if L == "L1" else 2
    ny = sum(A[p]["auc"] > 0.5 for p in yrs)
    E1[L] = dict(auc_dev=A["DEV"]["auc"], years={p: A[p]["auc"] for p in yrs}, n_year_gt05=int(ny), need=need,
                 auc_val=A["VAL2025"]["auc"], ok=bool(A["DEV"]["auc"] > 0.55 and ny >= need and A["VAL2025"]["auc"] > 0.5),
                 val_ge_053=bool(A["VAL2025"]["auc"] >= 0.53))
    for c in ("P_", "Pg_"):
        log.info("AUC %s %-3s: %s", L, "LR" if c == "P_" else "LGB", "  ".join(
            "%s %.4f(n%d,b%.3f)" % (p, v["auc"], v["n"], v["base"]) for p, v in AUC[L][c].items() if v))
    log.info("E1 %s: DEV %.4f (>0.55), nam>0.5 %d/%d (can %d), VAL %.4f -> %s | VAL>=0.53 %s", L, E1[L]["auc_dev"], ny, len(yrs), need,
             E1[L]["auc_val"], "PASS" if E1[L]["ok"] else "FAIL", E1[L]["val_ge_053"])
    ps = D.loc[pmask(D.index, "DEV", L), "P_" + L]
    pv = D.loc[pmask(D.index, "VAL2025"), "P_" + L]
    log.info("   P %s: DEV q10 %.3f med %.3f q90 %.3f, >0.55 %.3f, <0.45 %.3f | VAL >0.55 %.3f <0.45 %.3f", L, ps.quantile(.1),
             ps.median(), ps.quantile(.9), (ps > .55).mean(), (ps < .45).mean(), (pv > .55).mean(), (pv < .45).mean())


# ---------------- E3 / E5: mo phong lo ----------------
def sh(x):
    x = np.asarray(x, float)
    return float(x.mean() / x.std(ddof=1) * np.sqrt(365)) if len(x) > 2 and x.std(ddof=1) > 0 else np.nan


def btc_daily(days):
    t0 = (days.asi8 // 10 ** 6).astype(np.int64)
    return np.exp(lp("bt", t0 + MS_D) - lp("bt", t0)) - 1     # ngay PnL d: 00:00 d -> 00:00 d+1 = close d-1 -> close d


def sim(sig_days, a, b, legs, fee):
    """Lo mo tai close t (t in sig_days, a<=t<=b), trong so 1/3, giu 3 ngay PnL d=t+1..t+3. legs: [(gio, dau)].
    Phi = fee x 1/3 tru vao ngay d=t+1 (ngay dau cua lo). Tra Series PnL ngay d in [a+1, b+3] va bang lo."""
    days = pd.date_range(a + pd.Timedelta(days=1), b + pd.Timedelta(days=3), freq="D")
    pnl = pd.Series(0.0, index=days)
    lots = []
    for t in sig_days:
        if not (a <= t <= b):
            continue
        inc = np.zeros(3)
        for g, s in legs:
            inc += s * np.array([D.at[t, "i%s_%d" % (g, k)] for k in (1, 2, 3)])
        assert np.isfinite(inc).all()
        for k in range(3):
            pnl[t + pd.Timedelta(days=k + 1)] += inc[k] / 3
        pnl[t + pd.Timedelta(days=1)] -= fee / 3
        lots.append(dict(t=t, gross=float(inc.sum() / 3), net=float(inc.sum() / 3 - fee / 3)))
    return pnl, pd.DataFrame(lots)


def period_bounds(L, p):
    if p == "DEV":
        return OOS0[L], pd.Timestamp("2024-12-31")
    return pd.Timestamp("2025-01-01"), LAST_LAB


def layer(L, legs, fee):
    res = {}
    ser = {}
    for p in ("DEV", "VAL2025"):
        a, b = period_bounds(L, p)
        cand = D.index[(D.index >= a) & (D.index <= b)]
        sigd = cand[(D.loc[cand, "P_" + L] > 0.55).to_numpy()]
        pn, lots = sim(sigd, a, b, legs, fee)
        pa, _ = sim(cand, a, b, legs, fee)
        bt = btc_daily(pn.index)
        r = dict(sharpe=sh(pn), sharpe_always=sh(pa), sharpe_btc=sh(bt), sum=float(pn.sum()), sum_always=float(pa.sum()),
                 sum_btc=float(bt.sum()), n_lots=int(len(lots)), n_cand=int(len(cand)), n_days=int(len(pn)),
                 frac_inmkt=float((pn != 0).mean()))
        if p == "DEV":
            r["by_year"] = {int(y): dict(sharpe=sh(g), sum=float(g.sum())) for y, g in pn.groupby(pn.index.year)}
        res[p] = r
        ser[p] = (pn, lots, pa)
    return res, ser


E3, E3S, E5, E5S = {}, {}, {}, {}
for L in LABS:
    g = "B1" if L == "L1" else "B2"
    res, ser = layer(L, [(g, 1)], 0.002)
    dv, vl = res["DEV"], res["VAL2025"]
    ok = bool(dv["sharpe"] > 0.5 and dv["sharpe"] > dv["sharpe_always"] and dv["sharpe"] > dv["sharpe_btc"] and vl["sharpe"] > 0)
    E3[L] = dict(basket=g, detail=res, ok=ok)
    E3S[L] = ser
    for p, v in res.items():
        log.info("E3 %s (mua %s) %-7s Sharpe %+.3f | luon mo %+.3f | BTC %+.3f | sum %+.3f (luon %+.3f, BTC %+.3f) | lo %d/%d | ngay co vt %.3f %s",
                 L, g, p, v["sharpe"], v["sharpe_always"], v["sharpe_btc"], v["sum"], v["sum_always"], v["sum_btc"], v["n_lots"],
                 v["n_cand"], v["frac_inmkt"], v.get("by_year", ""))
    log.info("E3 %s -> %s", L, "PASS" if ok else "FAIL")
res, ser = layer("L3", [("B2", 1), ("B1", -1)], 0.004)
dv, vl = res["DEV"], res["VAL2025"]
E5["L3"] = dict(detail=res, ok=bool(dv["sharpe"] > 0.5 and dv["sharpe"] > dv["sharpe_always"] and vl["sharpe"] > 0))
E5S["L3"] = ser
for p, v in res.items():
    log.info("E5 L3 (B2-B1) %-7s Sharpe %+.3f | luon mo %+.3f | sum %+.3f (luon %+.3f) | lo %d/%d %s", p, v["sharpe"], v["sharpe_always"],
             v["sum"], v["sum_always"], v["n_lots"], v["n_cand"], v.get("by_year", ""))
log.info("E5 L3 -> %s (so mo ta: S1b REX VAL Sharpe -0.02)", "PASS" if E5["L3"]["ok"] else "FAIL")

# ---------------- E2 ----------------
C = pd.read_parquet("/home/ubuntu/claude_master/entry_confirm/ec_a_clusters.parquet", columns=["seed", "sym", "m1", "M", "pnl"])
SEEDS = ["A1", "S7", "S13", "S21", "S99", "S123", "S777", "S2024"]
assert sorted(C.seed.unique()) == sorted(SEEDS)
C["tM"] = DAY0 + pd.to_timedelta(C["M"], unit="m")
C["tm1"] = DAY0 + pd.to_timedelta(C["m1"], unit="m")
C["dayM"] = C["tM"].dt.floor("D")
C["dayP"] = C["dayM"] - pd.Timedelta(days=1)            # dong du bao: t = ngay UTC(M) - 1, lap luc 00:00 ngay UTC(M) <= tM
C["per"] = np.where(C.tM < pd.Timestamp("2023-01-01"), "2022H2", np.where(C.tM < pd.Timestamp("2024-01-01"), "2023",
                    np.where(C.tM < pd.Timestamp("2025-01-01"), "2024", np.where(C.tM < HO, "VAL2025", "HO"))))
E2 = {}
V4c = []
for L in ("L1", "L2"):
    c = C[(C.dayP >= OOS0[L]) & (C.tM < HO)].copy()
    c["P"] = D["P_" + L].reindex(c["dayP"]).to_numpy()
    c["fm"] = D["fm_" + L].reindex(c["dayP"]).to_numpy()
    if QUICK:
        c = c[c.P.notna()].copy()
    assert c.P.notna().all()
    assert (pd.to_datetime(c.dayP) + pd.Timedelta(days=1) <= c.tM).all()
    c["low"] = c.P < 0.45
    c["dpnl"] = np.where(c.low, -0.5 * c.pnl, 0.0)
    yrs = ["2022H2", "2023", "2024"] if L == "L1" else ["2023", "2024"]
    sd = {}
    for s in SEEDS:
        g = c[c.seed == s]
        dv = g[g.per != "VAL2025"]
        sd[s] = dict(dpnl_dev=float(dv.dpnl.sum()), n_dev=int(len(dv)), n_low_dev=int(dv.low.sum()), pnl_dev=float(dv.pnl.sum()),
                     by_per={p: dict(dpnl=float(g[g.per == p].dpnl.sum()), n=int((g.per == p).sum()), n_low=int(g[g.per == p].low.sum()))
                             for p in yrs + ["VAL2025"]})
    dm = float(np.mean([sd[s]["dpnl_dev"] for s in SEEDS]))
    npos = int(sum(sd[s]["dpnl_dev"] > 0 for s in SEEDS))
    pm = {p: float(np.mean([sd[s]["by_per"][p]["dpnl"] for s in SEEDS])) for p in yrs + ["VAL2025"]}
    nyp = int(sum(pm[p] > 0 for p in yrs))
    need = 2
    E2[L] = dict(dpnl_dev_mean=dm, n_seed_pos=npos, per_mean=pm, n_year_pos=nyp, need_year=need, seed=sd,
                 n_clusters_excluded_first_day=int(((C.dayM == OOS0[L])).sum()),
                 ok=bool(dm > 5000 and npos >= 6 and nyp >= need and pm["VAL2025"] > 0))
    for s in SEEDS:
        q = sd[s]
        log.info("E2 %s %-6s dPnL DEV %+9.0f (cum %d, P<.45 %d) | %s", L, s, q["dpnl_dev"], q["n_dev"], q["n_low_dev"],
                 " ".join("%s %+.0f(%d/%d)" % (p, v["dpnl"], v["n_low"], v["n"]) for p, v in q["by_per"].items()))
    log.info("E2 %s: TB DEV %+.0f (>5000), seed duong %d/8, nam %s duong %d/%d, VAL %+.0f -> %s", L, dm, npos,
             {k: round(v) for k, v in pm.items()}, nyp, len(yrs), pm["VAL2025"], "PASS" if E2[L]["ok"] else "FAIL")
    rng = np.random.default_rng(7 + len(L))
    for i in rng.choice(len(c), 5, replace=False):
        r = c.iloc[i]
        ok = bool(r.dayP + pd.Timedelta(days=1) <= r.tM < r.dayP + pd.Timedelta(days=2) and pd.Timestamp(r.fm) <= r.dayP
                  and float(D.at[r.dayP, "P_" + L]) == float(r.P))
        V4c.append(dict(L=L, seed=r.seed, sym=r.sym, tM=str(r.tM), dayP=str(r.dayP.date()), fit=str(pd.Timestamp(r.fm).date()),
                        P=float(r.P), ok=ok))
        log.info("V-E2 %s %s %s tM %s -> dong du bao %s (fit %s) P %.4f -> %s", L, r.seed, r.sym, r.tM, r.dayP.date(),
                 pd.Timestamp(r.fm).date(), r.P, "OK" if ok else "FAIL")

# ---------------- E4 (tinh cho ca 3 label) ----------------
cb = C[C.tm1 < HO].groupby(C.tm1.dt.floor("D")).pnl.sum() / 8.0          # PnL crash-buy theo ngay UTC dong cum, TB 8 seed
nopen = C[C.tM < HO].groupby(C.dayM).size() / 8.0                        # so cum mo / ngay, TB 8 seed
WAVE = set(nopen.index[nopen >= 6])
nA1 = C[(C.seed == "A1") & (C.tM < HO)].groupby("dayM").size()
WAVE_A1 = set(nA1.index[nA1 >= 6])
log.info("ngay dot (TB seed >=6 cum mo): %d ngay; theo A1: %d ngay", len(WAVE), len(WAVE_A1))


def e4(L, ser, tag):
    pn, lots, _ = ser["DEV"]
    cbs = cb.reindex(pn.index).fillna(0.0)
    corr = float(np.corrcoef(pn.to_numpy(), cbs.to_numpy())[0, 1])
    o = dict(layer=tag, corr=corr)
    for nm, W in (("mean8", WAVE), ("A1", WAVE_A1)):
        if len(lots) == 0:
            o["b_" + nm] = None
            continue
        fl = lots.t.apply(lambda t: any((t - pd.Timedelta(days=k)) in W for k in range(4)))
        tot = lots.net.sum()
        o["b_" + nm] = dict(frac_lots=float(fl.mean()), pnl_flag=float(lots.net[fl].sum()), pnl_tot=float(tot),
                            pct=float(lots.net[fl].sum() / tot * 100) if tot > 0 else None,
                            pct_gross=float(lots.gross[fl].sum() / lots.gross.sum() * 100) if lots.gross.sum() > 0 else None)
    b = o["b_mean8"]
    o["TRUNG"] = bool(corr > 0.5 or (b is not None and b["pct"] is not None and b["pct"] > 50))
    o["note_b"] = "pct=None khi tong PnL net DEV <= 0 (khong dinh nghia duoc)"
    log.info("E4 %s [%s]: corr ngay vs crash-buy %+.3f | (b) TB8: %s | A1: %s | TRUNG=%s", L, tag, corr, b, o["b_A1"], o["TRUNG"])
    return o


E4 = {}
for L in LABS:
    E4[L] = {"E3": e4(L, E3S[L], "E3")}
    if L == "L3":
        E4[L]["E5"] = e4(L, E5S["L3"], "E5")
    E4[L]["top5_coef_LR_fit2025-01"] = COEF[L][:5] if L in COEF else None
    log.info("E4(c) %s top5 |coef| LR chuan hoa (fit 2025-01, train <= 2024-12-29): %s", L,
             [(a, round(b, 3)) for a, b in COEF.get(L, [])[:5]])

# ---------------- mo ta: corr return 3 ngay B1/B2/ALT_EW ----------------
mm = (D.index >= TR0) & (D.index <= LAST_LAB)
R3 = D.loc[mm, ["rB1", "rB2", "rEW", "rBT"]]
R3n = R3.iloc[::3]
DESC = dict(corr_overlap=R3.corr().round(4).to_dict(), corr_nonoverlap=R3n.corr().round(4).to_dict(), n=int(len(R3)),
            mean=R3.mean().round(5).to_dict())
log.info("corr 3 ngay (2022-01..2025-12-28, overlap):\n%s", R3.corr().round(3))
log.info("corr 3 ngay (khong overlap, moi 3 ngay):\n%s", R3n.corr().round(3))

# ---------------- ket luan ----------------
VERD = {}
for L in LABS:
    e2ok = E2[L]["ok"] if L in E2 else False
    e3ok = E3[L]["ok"]
    e5ok = E5[L]["ok"] if L in E5 else False
    trung = False
    if e3ok and E4[L]["E3"]["TRUNG"]:
        trung = True
    if e5ok and E4[L]["E5"]["TRUNG"]:
        trung = True
    # neu ca E3 va E5 deu dat, TRUNG chi khi moi lop dat deu trung; neu chi E2 dat thi E4 khong ap dung
    if e3ok and e5ok:
        trung = E4[L]["E3"]["TRUNG"] and E4[L]["E5"]["TRUNG"]
    go = bool(E1[L]["ok"] and (e2ok or e3ok or e5ok) and not trung and E1[L]["val_ge_053"])
    VERD[L] = dict(E1=E1[L]["ok"], E2=e2ok if L in E2 else None, E3=e3ok, E5=e5ok if L in E5 else None, TRUNG=trung,
                   VAL_ge_053=E1[L]["val_ge_053"], PASS=go)
    log.info("KET LUAN %s: %s", L, VERD[L])
ANY = any(v["PASS"] for v in VERD.values())
log.info("TONG: %s", "co label qua tang A" if ANY else "KHONG label nao qua => DONG ho 'gate du bao huong gio'")

# ---------------- V1: look-ahead ----------------
rng = np.random.default_rng(20261020)
V1 = []
for i in rng.choice(len(DAYS), 10, replace=False):
    t, T = DAYS[i], int(TT[i])
    cut = {k: (ts[ts < T], r[ts < T]) for k, (ts, r) in SER.items()}
    junk = {k: (ts, np.where(ts >= T, rng.normal(0, 0.05, len(r)), r)) for k, (ts, r) in SER.items()}
    f0 = mfeats(T)
    dm_cut = max(abs(mfeats(T, cut)[c] - f0[c]) for c in MF)
    dm_junk = max(abs(mfeats(T, junk)[c] - f0[c]) for c in MF)
    dm_tab = max(abs(X.at[t, c] - f0[c]) for c in MF)
    Pc = P[P.day <= t]                                          # cat panel/S1 sau t
    Pj = P.copy()
    fut = Pj.day > t
    for c in ("mom1", "mom7", "mom28", "vol30", "lqv30", "br50", "score"):
        Pj.loc[fut, c] = rng.normal(0, 1, int(fut.sum()))
    bc = bfeats(*baskets(Pc[Pc.day == t]), Pc[Pc.day == t])
    bj = bfeats(*baskets(Pj[Pj.day == t]), Pj[Pj.day == t])
    db_cut = max(abs(bc[c] - X.at[t, c]) for c in BF if not np.isnan(X.at[t, c]))
    db_junk = max(abs(bj[c] - X.at[t, c]) for c in BF if not np.isnan(X.at[t, c]))
    V1.append(dict(t=str(t.date()), T=str(pd.to_datetime(T, unit="ms")), m_cut=float(dm_cut), m_junk=float(dm_junk), m_tab=float(dm_tab),
                   b_cut=float(db_cut), b_junk=float(db_junk)))
    log.info("V1 %s", V1[-1])
V1ok = all(max(v["m_cut"], v["m_junk"], v["m_tab"], v["b_cut"], v["b_junk"]) == 0 for v in V1)
assert not any(c.startswith("y") or c in ("rB1", "rB2", "L1", "L2", "L3") for c in FEATS)
log.info("V1 -> %s", "OK" if V1ok else "FAIL")

# ---------------- V2: y3 / mom1 / mom7 vs kline1m close (phut 23:59 = close ngay) ----------------
V2 = []
cand = [d for d in DAYS if d >= pd.Timestamp("2022-01-08") and 8 <= d.day <= 27 and d <= LAST_LAB]
for i in rng.choice(len(cand), 10, replace=False):
    t = cand[i]
    b1, b2 = BK[t]
    syms = list(dict.fromkeys([b1[int(rng.integers(30))], b2[int(rng.integers(10))] if b2 else b1[0], "BTCUSDT"]))
    need = {k: t + pd.Timedelta(days=k) for k in (-7, -1, 0, 3)}
    tsl = [int((d.value // 10 ** 6) + 86340000) for d in need.values()]
    f = "/home/ubuntu/vz_e1/raw/kline1m-%04d-%02d.parquet" % (t.year, t.month)
    kl = pads.dataset(f).to_table(columns=["ts", "sym", "close"], filter=pads.field("sym").isin(syms) & pads.field("ts").isin(tsl)).to_pandas()
    kl["sym"] = kl.sym.astype(str)
    kc = kl.set_index(["sym", "ts"]).close
    for s in syms:
        rp = P[(P.day == t) & (P.sym == s)]
        if rp.empty:
            continue
        rp = rp.iloc[0]
        try:
            c0, cm1, cm7, c3 = (float(kc[(s, x)]) for x in (tsl[2], tsl[1], tsl[0], tsl[3]))
        except KeyError:
            V2.append(dict(t=str(t.date()), sym=s, note="thieu kline")); continue
        e = dict(y3=abs(rp.y3 - (c3 / c0 - 1)), mom1=abs(rp.mom1 - (c0 / cm1 - 1)), mom7=abs(rp.mom7 - (c0 / cm7 - 1)))
        V2.append(dict(t=str(t.date()), sym=s, y3=float(rp.y3), y3_k=float(c3 / c0 - 1), err=float(max(e.values())), ok=bool(max(e.values()) < 1e-9)))
        log.info("V2 %s %-12s y3 panel %+.6f kline %+.6f | max err (y3,mom1,mom7) %.2e -> %s", t.date(), s, rp.y3, c3 / c0 - 1,
                 max(e.values()), "OK" if V2[-1]["ok"] else "FAIL")
V2ok = all(v.get("ok", False) for v in V2 if "note" not in v) and sum("note" not in v for v in V2) >= 20
log.info("V2 -> %s (%d so sanh)", "OK" if V2ok else "FAIL", sum("note" not in v for v in V2))

# ---------------- V4: in gio 3 ngay ----------------
V4 = []
for t in [pd.Timestamp("2022-03-15"), pd.Timestamp("2023-08-02"), pd.Timestamp("2025-06-20")]:
    Pd = GP[t]
    b1, b2 = baskets(Pd)
    chk = (b1.lqv30.min() >= Pd[~Pd.sym.isin(b1.sym)].lqv30.max()) and (b2.score.min() >= Pd[~Pd.sym.isin(b2.sym)].score.max())
    V4.append(dict(day=str(t.date()), n_univ=len(Pd), B1=list(b1.sym), B2=list(b2.sym), B2_score=[round(x, 5) for x in b2.score],
                   rB1=float(b1.y3.mean()), rB2=float(b2.y3.mean()), ok=bool(chk and len(b1) == 30 and len(b2) == 10
                                                                       and abs(b1.y3.mean() - D.at[t, "rB1"]) < 1e-12)))
    log.info("V4 %s univ %d | B1 %s | B2 %s | rB1 %+.4f rB2 %+.4f | L %s -> %s", t.date(), len(Pd), list(b1.sym), list(b2.sym),
             b1.y3.mean(), b2.y3.mean(), (D.at[t, "L1"], D.at[t, "L2"], D.at[t, "L3"]), "OK" if V4[-1]["ok"] else "FAIL")
V4ok = all(v["ok"] for v in V4)

# ---------------- V5 ----------------
V5 = dict(panel_max=str(P.day.max().date()), s1_max=str(S.day.max().date()), D_max=str(D.index.max().date()),
          last_label={L: str(D[L].last_valid_index().date()) for L in LABS}, cluster_max_tM=str(C[C.tM < HO].tM.max()),
          ok=bool(P.day.max() < HO and S.day.max() < HO and all(D[L].last_valid_index() <= LAST_LAB for L in LABS)))
log.info("V5 %s", V5)
V3ok = all(all(v["ok"] for v in V3[L]) for L in LABS)
log.info("V: V1 %s V2 %s V3 %s V4 %s V5 %s", V1ok, V2ok, V3ok, V4ok, V5["ok"])

out = dict(prereg="PREREG_MKT_UP2.md@233d9679 + addendum1@9c326745", quick=QUICK, feats=FEATS,
           notes=dict(
               timing="panel day t = nen k1d 00:00..24:00 UTC t; feature ngay t dung close<=close t; y1/y3 SIMPLE return close t->close t+1/t+3 "
                      "(CF ffill sau delist). Feature thi truong tai T(t)=00:00 UTC t+1, phut ts<T(t). Label NaN neu t>2025-12-28 (khong dung gia 2026).",
               s1="pred_s1.parquet = winner REX S1 'C1' (LGB rk1, walk-forward quy, purge h+1); diem ngay t dung feature ngay t.",
               train="train tu 2022-01-01 cho CA 3 label (dong du 27 feature; feature gio B2 can S1 tu 2022-01). LR L2 C=1 + StandardScaler; "
                     "LGB depth3/200/0.05 rs42 (mo ta). Refit dau thang m, train t<=m-3d (label ket thuc 00:00 t+4 <= 00:00 m+1 = luc du bao dong t=m).",
               baskets="B1 top30 lqv30, B2 top10 score S1, trong universe panel ngay t va co y3 (y3 NaN = 0 dong truoc 2025-12-29 => khong loai coin nao); "
                       "hoa: sym tang dan. Feature gio = mean 30/10 coin.",
               e3="Lo mo tai close t neu P>0.55 (P du bao dong t), trong so 1/3, buy&hold gio co dinh 3 ngay: PnL ngay d=t+k = (mean G_k - mean G_{k-1})/3, "
                  "G1=1+y1(t), G2=(1+y1(t))(1+y1(t+1)) [fallback sqrt(G1*G3) khi coin roi universe], G3=1+y3(t) => tong = mean y3/3. "
                  "Phi 0.20%/lo x1/3 tru ngay t+1. DEV mo phong rieng (lo t in [OOS0,2024-12-31], ngay PnL toi 2025-01-03); VAL rieng "
                  "(lo t in [2025-01-01,2025-12-28]). Luon mo lo = cung co che, moi ngay. BTC = simple return ngay tu index.npz cung tap ngay. Sharpe ddof1 x sqrt365.",
               e5="long B2 - short B1 cung notional, phi 0.40%/lo, funding bo qua.",
               e2="x0.5 pnl cum khi P<0.45; P = du bao dong t = ngay UTC(M)-1; chi cum co t>=OOS0 cua label va tM<2026. Nam theo UTC tM. "
                  "L2 chi co 2 nam DEV (2023,2024) => yeu cau ca 2 nam duong (dien giai '>=2/3 nam' theo E1).",
               e4="(a) Pearson corr PnL ngay lop moi (DEV) vs crash-buy (sum pnl cum theo ngay UTC dong cum m1 /8 seed, ngay khong cum = 0). "
                  "(b) ngay dot = ngay UTC(M) co so cum mo TB 8 seed >= 6; lo 't - ngay dot in [0,3]'; pct = PnL net lo co co / tong PnL net lo DEV (None neu tong<=0). "
                  "Ban A1 mo ta. (c) LR fit moc 2025-01-01 (train <= 2024-12-29)."),
           AUC=AUC, E1=E1, E2=E2, E3=E3, E5=E5, E4=E4, DESC=DESC, VERDICT=VERD, ANY_PASS=ANY,
           V1=dict(ok=V1ok, rows=V1), V2=dict(ok=V2ok, rows=V2), V3=dict(ok=V3ok, rows=V3), V4=dict(ok=V4ok, rows=V4), V5=V5,
           path_fallback=dict(n=fb_n, tot=fb_tot), y3_nan_pre=y3nan_pre)
json.dump(out, open(OUT + "/%s.json" % TAG, "w"), indent=1, default=str)
if not QUICK:
    Q = D.reset_index().rename(columns={"index": "day"})
    keep = ["day", "L1", "L2", "L3", "rB1", "rB2", "rEW", "rBT", "P_L1", "P_L2", "P_L3", "Pg_L1", "Pg_L2", "Pg_L3", "fm_L1", "fm_L2", "fm_L3"] + BF
    Q[keep].to_parquet(OUT + "/mv_a_pred.parquet")
log.info("ghi %s/%s.json (+pred parquet neu full), log", OUT, TAG)
