#!/usr/bin/env python3
"""MKT_UP tang A - dung theo PREREG_MKT_UP.md (commit 8a4b8b1c). Khong tune, khong bien the.
Quy uoc thoi gian: ew_ts/bt_ts = ms UTC cua phut (theo index.npz). Feature tai t chi dung phut ts < t.
Label y = C_le(t+72h) - C_le(t) > 0, C_le(x) = tong log-ret cac phut ts <= x (asof) => phut (t, t+72h].
Mau 1 dong/ngay 00:00 UTC. Walk-forward refit dau thang, train t in [2021-08-01, moc-3d] (label ket thuc <= moc)."""
import json
import logging
import sys
import warnings

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import StandardScaler
import lightgbm as lgb

OUT = "/home/ubuntu/claude_master/mkt_up"
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", force=True,
                    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler(OUT + "/mu_a.log", mode="w")])
log = logging.getLogger("mu")
DAY0 = pd.Timestamp("20210701")   # reset_rule_score.DAY0 (ec_a.py: tM = DAY0 + M phut, UTC)
MS_D = 86400000
MS_H = 3600000
SQ = np.sqrt(1440.0)

z = np.load("/home/ubuntu/claude_master/edge_attr/index.npz")
SER = {"ew": (z["ew_ts"].astype(np.int64), z["ew_r"].astype(np.float64)),
       "bt": (z["bt_ts"].astype(np.int64), z["bt_r"].astype(np.float64))}
for k, (ts, r) in SER.items():
    assert np.all(np.diff(ts) > 0) and not np.isnan(r).any()
    log.info("%s: %d phut %s -> %s, gap>1m %d, gap max %d phut", k, len(ts), pd.to_datetime(ts[0], unit="ms"),
             pd.to_datetime(ts[-1], unit="ms"), int((np.diff(ts) != 60000).sum()), int(np.diff(ts).max() // 60000))
LAST_TS = min(SER["ew"][0][-1], SER["bt"][0][-1])


def feat_one(ts, r, t):
    """Feature cho 1 chuoi tai t (ms). Chi dung phut ts < t: cat ngay o day."""
    n = np.searchsorted(ts, t, "left")
    ts, r = ts[:n], r[:n]
    cum0 = np.concatenate([[0.0], np.cumsum(r)])         # cum0[i] = tong r[:i]

    def cf(x):                                              # log-gia asof: tong r co ts < x
        return cum0[np.searchsorted(ts, x, "left")]
    c_t = cum0[n]
    f = {}
    for d in (1, 3, 7, 30):
        f["ret%dd" % d] = c_t - cf(t - d * MS_D)
    for d in (1, 7):
        lo = np.searchsorted(ts, t - d * MS_D, "left")
        f["vol%dd" % d] = float(np.std(r[lo:n], ddof=1) * SQ) if n - lo >= 2 else np.nan
    lo = np.searchsorted(ts, t - 30 * MS_D, "left")
    w = cum0[lo:n + 1]                                      # log-gia theo phut trong [t-30d, t), gom muc dau cua so
    f["dmax30"] = c_t - w.max()                             # <= 0
    f["dmin30"] = c_t - w.min()                             # >= 0
    return f


def feats(t, ser=SER):
    fe = feat_one(*ser["ew"], t)
    fb = feat_one(*ser["bt"], t)
    o = {"ew_" + k: v for k, v in fe.items()}
    o.update({"bt_" + k: v for k, v in fb.items()})
    o["ewmbt_ret7d"] = fe["ret7d"] - fb["ret7d"]
    o["ewmbt_ret30d"] = fe["ret30d"] - fb["ret30d"]
    return o


FEATS = (["ew_ret1d", "ew_ret3d", "ew_ret7d", "ew_ret30d", "ew_vol1d", "ew_vol7d", "ew_dmax30", "ew_dmin30"]
         + ["bt_ret1d", "bt_ret3d", "bt_ret7d", "bt_ret30d", "bt_vol1d", "bt_vol7d", "bt_dmax30", "bt_dmin30"]
         + ["ewmbt_ret7d", "ewmbt_ret30d"])
assert len(FEATS) == 18
CUM0 = {k: np.concatenate([[0.0], np.cumsum(r)]) for k, (ts, r) in SER.items()}


def cle(k, x):          # tong log-ret phut ts <= x
    return CUM0[k][np.searchsorted(SER[k][0], x, "right")]


def fwd(k, t, h_ms):    # log-ret phut (t, t+h]; NaN neu t+h vuot du lieu
    x = np.asarray(t, dtype=np.int64)
    v = cle(k, x + h_ms) - cle(k, x)
    return np.where(x + h_ms <= LAST_TS + 60000 - 1, v, np.nan)   # phut cuoi = ts LAST_TS


days = pd.date_range("2021-08-01", "2025-12-31", freq="D")
T = (days.asi8 // 10 ** 6).astype(np.int64)
rows = [feats(int(t)) for t in T]
X = pd.DataFrame(rows, index=days)[FEATS]
log.info("feature: %d ngay x %d cot, NaN %d", len(X), X.shape[1], int(X.isna().sum().sum()))
D = pd.DataFrame(index=days)
# label: day t+72h phai <= ts phut cuoi du lieu (asof); t+72h = 2026-01-01 khong co => NaN
ok72 = T + 72 * MS_H <= LAST_TS
D["y"] = np.where(ok72, (cle("ew", T + 72 * MS_H) - cle("ew", T) > 0).astype(float), np.nan)
D["y_bt72"] = np.where(ok72, (cle("bt", T + 72 * MS_H) - cle("bt", T) > 0).astype(float), np.nan)
ok7 = T + 7 * MS_D <= LAST_TS
D["y_ew7d"] = np.where(ok7, (cle("ew", T + 7 * MS_D) - cle("ew", T) > 0).astype(float), np.nan)
log.info("label: y co %d/%d ngay, ty le y=1 %.3f", int(D.y.notna().sum()), len(D), float(D.y.mean()))

# ---- walk-forward ----
months = pd.date_range("2022-07-01", "2025-12-01", freq="MS")
D["P_lr"] = np.nan
D["P_lgb"] = np.nan
D["fit_month"] = pd.NaT
V3 = []
warnings.simplefilter("ignore")
for m in months:
    tr = (D.index >= "2021-08-01") & (D.index <= m - pd.Timedelta(days=3)) & D.y.notna()
    te = (D.index >= m) & (D.index < m + pd.offsets.MonthBegin(1))
    Xtr, ytr = X[tr].to_numpy(), D.y[tr].to_numpy().astype(int)
    sc = StandardScaler().fit(Xtr)
    lr = LogisticRegression(C=1.0, penalty="l2", max_iter=1000).fit(sc.transform(Xtr), ytr)
    gb = lgb.LGBMClassifier(max_depth=3, n_estimators=200, learning_rate=0.05, random_state=42, verbose=-1).fit(Xtr, ytr)
    D.loc[te, "P_lr"] = lr.predict_proba(sc.transform(X[te].to_numpy()))[:, 1]
    D.loc[te, "P_lgb"] = gb.predict_proba(X[te].to_numpy())[:, 1]
    D.loc[te, "fit_month"] = m
    last_t = D.index[tr].max()
    V3.append(dict(moc=str(m.date()), n_train=int(tr.sum()), train_first=str(D.index[tr].min().date()),
                   train_last=str(last_t.date()), label_end=str(last_t + pd.Timedelta(hours=72)),
                   ok=bool(last_t + pd.Timedelta(hours=72) <= m), lr_iter=int(lr.n_iter_[0]), n_test=int(te.sum())))
assert all(v["ok"] for v in V3)
log.info("walk-forward: %d lan refit, V3 purge OK=%s", len(V3), all(v["ok"] for v in V3))
for v in V3[:3] + V3[17:19] + V3[-2:]:
    log.info("  V3 moc %s: train %s..%s (n %d), label mau cuoi ket thuc %s, test %d ngay, lr iter %d", v["moc"], v["train_first"],
             v["train_last"], v["n_train"], v["label_end"], v["n_test"], v["lr_iter"])

# ---- E1 ----
PER = {"DEV": ("2022-07-01", "2024-12-31"), "2022H2": ("2022-07-01", "2022-12-31"), "2023": ("2023-01-01", "2023-12-31"),
       "2024": ("2024-01-01", "2024-12-31"), "VAL2025": ("2025-01-01", "2025-12-31")}


def pmask(idx, p):
    a, b = PER[p]
    return (idx >= pd.Timestamp(a)) & (idx < pd.Timestamp(b) + pd.Timedelta(days=1))


def auc(lab, col, p):
    m = pmask(D.index, p) & D[lab].notna() & D[col].notna()
    yy = D.loc[m, lab].to_numpy()
    return dict(auc=float(roc_auc_score(yy, D.loc[m, col])), n=int(m.sum()), base=float(yy.mean())) if m.sum() else None


AUC = {lab: {col: {p: auc(lab, col, p) for p in PER} for col in ("P_lr", "P_lgb")} for lab in ("y", "y_bt72", "y_ew7d")}
A = AUC["y"]["P_lr"]
e1y = sum(A[p]["auc"] > 0.5 for p in ("2022H2", "2023", "2024"))
E1 = dict(auc_dev=A["DEV"]["auc"], n_year_gt05=int(e1y), auc_val=A["VAL2025"]["auc"],
          ok=bool(A["DEV"]["auc"] > 0.55 and e1y >= 2 and A["VAL2025"]["auc"] > 0.5))
for lab in AUC:
    for col in AUC[lab]:
        log.info("AUC %-6s %-5s: %s", lab, col, "  ".join("%s %.4f(n%d,base %.3f)" % (p, v["auc"], v["n"], v["base"])
                                                          for p, v in AUC[lab][col].items() if v))
log.info("E1: AUC DEV %.4f (>0.55), nam >0.5: %d/3, VAL %.4f -> %s", E1["auc_dev"], e1y, E1["auc_val"], "PASS" if E1["ok"] else "FAIL")
PS = D.loc[pmask(D.index, "DEV") | pmask(D.index, "VAL2025"), "P_lr"]
log.info("P_lr OOS: min %.3f q10 %.3f med %.3f q90 %.3f max %.3f; ty le <0.45 DEV %.3f VAL %.3f; >0.55 DEV %.3f VAL %.3f",
         PS.min(), PS.quantile(.1), PS.median(), PS.quantile(.9), PS.max(),
         (D.P_lr[pmask(D.index, "DEV")] < .45).mean(), (D.P_lr[pmask(D.index, "VAL2025")] < .45).mean(),
         (D.P_lr[pmask(D.index, "DEV")] > .55).mean(), (D.P_lr[pmask(D.index, "VAL2025")] > .55).mean())

# ---- E2 ----
C = pd.read_parquet("/home/ubuntu/claude_master/entry_confirm/ec_a_clusters.parquet", columns=["seed", "sym", "M", "pnl"])
SEEDS = ["A1", "S7", "S13", "S21", "S99", "S123", "S777", "S2024"]
assert sorted(C.seed.unique()) == sorted(SEEDS)
C["tM"] = DAY0 + pd.to_timedelta(C["M"], unit="m")          # UTC
C["day"] = C["tM"].dt.floor("D")
C = C[C["tM"] >= pd.Timestamp("2022-07-01")].copy()
C["P"] = D["P_lr"].reindex(C["day"]).to_numpy()
C["fit_month"] = D["fit_month"].reindex(C["day"]).to_numpy()
assert C["P"].notna().all(), "cum khong co P"
C["per"] = np.where(C.tM < pd.Timestamp("2023-01-01"), "2022H2", np.where(C.tM < pd.Timestamp("2024-01-01"), "2023",
                    np.where(C.tM < pd.Timestamp("2025-01-01"), "2024", "VAL2025")))
C["low"] = C["P"] < 0.45
C["dpnl"] = np.where(C["low"], -0.5 * C["pnl"], 0.0)
E2s = {}
for s in SEEDS:
    g = C[C.seed == s]
    dv = g[g.per != "VAL2025"]
    E2s[s] = dict(dpnl_dev=float(dv.dpnl.sum()), n_dev=int(len(dv)), n_low_dev=int(dv.low.sum()),
                  pnl_dev=float(dv.pnl.sum()),
                  by_per={p: dict(dpnl=float(g[g.per == p].dpnl.sum()), n=int((g.per == p).sum()), n_low=int(g[g.per == p].low.sum()))
                          for p in ("2022H2", "2023", "2024", "VAL2025")})
dev_mean = float(np.mean([E2s[s]["dpnl_dev"] for s in SEEDS]))
npos = int(sum(E2s[s]["dpnl_dev"] > 0 for s in SEEDS))
per_mean = {p: float(np.mean([E2s[s]["by_per"][p]["dpnl"] for s in SEEDS])) for p in ("2022H2", "2023", "2024", "VAL2025")}
nyp = int(sum(per_mean[p] > 0 for p in ("2022H2", "2023", "2024")))
E2 = dict(dpnl_dev_mean=dev_mean, n_seed_pos=npos, per_mean=per_mean, n_year_pos=nyp,
          ok=bool(dev_mean > 5000 and npos >= 6 and nyp >= 2 and per_mean["VAL2025"] > 0))
# tercile P: cutoff tren P_lr cac NGAY DEV-OOS (mo ta)
q1, q2 = D.P_lr[pmask(D.index, "DEV")].quantile([1 / 3, 2 / 3]).to_numpy()
C["terc"] = np.where(C.P < q1, "T1", np.where(C.P < q2, "T2", "T3"))
TER = {}
for p, gp in (("DEV", C[C.per != "VAL2025"]), ("VAL2025", C[C.per == "VAL2025"])):
    TER[p] = {t: dict(n_per_seed=float(len(gt) / 8), pnl_per_cluster=float(gt.pnl.mean()) if len(gt) else np.nan,
                      pnl_sum_per_seed=float(gt.pnl.sum() / 8)) for t, gt in gp.groupby("terc")}
for s in SEEDS:
    q = E2s[s]
    log.info("E2 %-6s dPnL DEV %+9.0f (cum %d, P<.45 %d) | %s", s, q["dpnl_dev"], q["n_dev"], q["n_low_dev"],
             " ".join("%s %+.0f(%d/%d)" % (p, v["dpnl"], v["n_low"], v["n"]) for p, v in q["by_per"].items()))
log.info("E2: TB DEV %+.0f (>5000), seed duong %d/8, nam %s duong %d/3, VAL %+.0f -> %s", dev_mean, npos,
         {k: round(v) for k, v in per_mean.items()}, nyp, per_mean["VAL2025"], "PASS" if E2["ok"] else "FAIL")
log.info("E2 tercile (cutoff P ngay DEV %.4f / %.4f): %s", q1, q2, json.dumps(TER))

# ---- E3 ----
OOS = D.index[(D.index >= "2022-07-01") & (D.index <= "2025-12-31")]
sig = (D.loc[OOS, "P_lr"] > 0.55).astype(float).to_numpy()
expo = (sig + np.concatenate([[0], sig[:-1]]) + np.concatenate([[0, 0], sig[:-2]])) / 3.0   # lenh mo ngay d, d-1, d-2
TO = (OOS.asi8 // 10 ** 6).astype(np.int64)
dchg = np.abs(np.diff(np.concatenate([[0.0], expo])))
fee = 0.001 * dchg
E3 = {}
for k in ("ew", "bt"):
    rd = cle(k, TO + MS_D) - cle(k, TO)                     # log-ret phut (d, d+1d]
    net = expo * rd - fee
    res = {}
    for p in ("DEV", "2022H2", "2023", "2024", "VAL2025"):
        mm = pmask(OOS, p)

        def sh(x):
            return float(x.mean() / x.std(ddof=1) * np.sqrt(365)) if x.std(ddof=1) > 0 else np.nan
        res[p] = dict(sharpe=sh(net[mm]), sharpe_hold=sh(rd[mm]), ret_sum=float(net[mm].sum()), ret_hold=float(rd[mm].sum()),
                      mean_expo=float(expo[mm].mean()), frac_inmkt=float((expo[mm] > 0).mean()), fee_sum=float(fee[mm].sum()),
                      n_days=int(mm.sum()))
    E3[k] = res
    for p, v in res.items():
        log.info("E3 %s %-7s Sharpe %+.3f | hold %+.3f | sum logret %+.3f (hold %+.3f) | expo TB %.3f, ngay co vi the %.3f, phi %.4f",
                 k, p, v["sharpe"], v["sharpe_hold"], v["ret_sum"], v["ret_hold"], v["mean_expo"], v["frac_inmkt"], v["fee_sum"])
e = E3["ew"]
E3r = dict(sharpe_dev=e["DEV"]["sharpe"], sharpe_hold_dev=e["DEV"]["sharpe_hold"], sharpe_val=e["VAL2025"]["sharpe"],
           ok=bool(e["DEV"]["sharpe"] > 0.5 and e["DEV"]["sharpe"] > e["DEV"]["sharpe_hold"] and e["VAL2025"]["sharpe"] > 0))
log.info("E3 (EW): Sharpe DEV %+.3f (>0.5 va > hold %+.3f), VAL %+.3f -> %s", E3r["sharpe_dev"], E3r["sharpe_hold_dev"],
         E3r["sharpe_val"], "PASS" if E3r["ok"] else "FAIL")
GO = bool(E1["ok"] and (E2["ok"] or E3r["ok"]))
log.info("KET LUAN: %s", "DI TIEP TANG B" if GO else "DONG huong model thi truong di len")

# ---- V1: cat du lieu sau t / pha du lieu ts>=t => feature khong doi ----
rng = np.random.default_rng(20261020)
V1 = []
for t in rng.choice(T, 10, replace=False):
    t = int(t)
    cut = {k: (ts[ts < t], r[ts < t]) for k, (ts, r) in SER.items()}
    junk = {k: (ts, np.where(ts >= t, rng.normal(0, 0.05, len(r)), r)) for k, (ts, r) in SER.items()}
    f0 = feats(t)
    d_cut = max(abs(feats(t, cut)[c] - f0[c]) for c in FEATS)
    d_junk = max(abs(feats(t, junk)[c] - f0[c]) for c in FEATS)
    d_tab = max(abs(X.loc[pd.to_datetime(t, unit="ms"), c] - f0[c]) for c in FEATS)
    V1.append(dict(t=str(pd.to_datetime(t, unit="ms")), maxdiff_cut=float(d_cut), maxdiff_junk=float(d_junk), maxdiff_table=float(d_tab)))
    log.info("V1 %s: |cat-full| %.3g, |pha ts>=t - full| %.3g, |bang-tinh lai| %.3g", V1[-1]["t"], d_cut, d_junk, d_tab)
V1ok = all(v["maxdiff_cut"] == 0 and v["maxdiff_junk"] == 0 and v["maxdiff_table"] == 0 for v in V1)
log.info("V1 -> %s", "OK" if V1ok else "FAIL")

# ---- V2: label = phut (t, t+72h] ----
V2 = []
ts, r = SER["ew"]
for t in rng.choice(T[ok72], 8, replace=False):
    t = int(t)
    mk = (ts > t) & (ts <= t + 72 * MS_H)
    s = r[mk].sum()
    yy = D.loc[pd.to_datetime(t, unit="ms"), "y"]
    V2.append(dict(t=str(pd.to_datetime(t, unit="ms")), first=str(pd.to_datetime(ts[mk][0], unit="ms")),
                   last=str(pd.to_datetime(ts[mk][-1], unit="ms")), n_min=int(mk.sum()), sum=float(s), y=float(yy),
                   ok=bool(float(s > 0) == yy)))
    log.info("V2 %s: phut %s..%s (n %d), sum %+.5f, y %d -> %s", V2[-1]["t"], V2[-1]["first"], V2[-1]["last"], mk.sum(), s, yy,
             "OK" if V2[-1]["ok"] else "FAIL")
yfull = np.array([float(r[(ts > t) & (ts <= t + 72 * MS_H)].sum() > 0) for t in T[ok72]])
V2all = bool((yfull == D.y.to_numpy()[ok72]).all())
log.info("V2 doi chieu toan bo %d label: %s; ngay khong co label: %s", int(ok72.sum()), V2all, [str(d.date()) for d in D.index[~ok72]])

# ---- V4: 20 cum ----
V4 = []
for i in rng.choice(len(C), 20, replace=False):
    c = C.iloc[i]
    pd_ = float(D.at[c.day, "P_lr"])
    ok = bool(c.day <= c.tM < c.day + pd.Timedelta(days=1) and abs(pd_ - c.P) == 0 and c.fit_month <= c.day
              and c.tM == pd.Timestamp("2021-07-01") + pd.Timedelta(minutes=int(c.M)))
    V4.append(dict(seed=c.seed, sym=c.sym, M=int(c.M), tM=str(c.tM), day=str(c.day.date()), P=float(c.P), P_table=pd_,
                   fit_month=str(pd.Timestamp(c.fit_month).date()), per=c.per, low=bool(c.low), pnl=float(c.pnl), ok=ok))
    log.info("V4 %-6s %-12s M %7d -> %s UTC -> ngay %s (fit %s) P %.4f [bang %.4f] %s low=%s pnl %+.1f -> %s", c.seed, c.sym, c.M,
             c.tM, c.day.date(), pd.Timestamp(c.fit_month).date(), c.P, pd_, c.per, c.low, c.pnl, "OK" if ok else "FAIL")
V4ok = all(v["ok"] for v in V4)

out = dict(prereg="PREREG_MKT_UP.md@8a4b8b1c", feats=FEATS,
           notes=dict(time="ts = ms UTC tu index.npz; feature dung phut ts<t; label phut (t,t+72h]",
                      dmaxmin="tren chuoi log-gia tich luy theo PHUT trong [t-30d,t), gom muc dau cua so",
                      vol="std(ddof=1) log-ret 1m trong [t-d,t) x sqrt(1440)",
                      purge="train t <= moc-3d va co label => label ket thuc <= moc (phut ts<=moc)",
                      e2_year="nam theo UTC cua tM (DEV-OOS dinh nghia UTC); ec_a dung +07",
                      e2_tercile="cutoff tren P_lr cac ngay DEV-OOS",
                      e3="vi the = (so lenh mo ngay d,d-1,d-2)/3; ret ngay = expo x log-ret (d,d+1d]; phi 0.1% x |dexpo|; Sharpe ddof=1 x sqrt365",
                      lgb="LGBMClassifier max_depth=3 n_estimators=200 lr=0.05 random_state=42, con lai mac dinh"),
           AUC=AUC, E1=E1, E2=dict(rule=E2, seed=E2s, tercile=TER, cut=[float(q1), float(q2)]), E3=dict(rule=E3r, detail=E3),
           GO_TIER_B=GO, V1=dict(ok=V1ok, rows=V1), V2=dict(ok=bool(V2all and all(v["ok"] for v in V2)), rows=V2),
           V3=dict(ok=all(v["ok"] for v in V3), rows=V3), V4=dict(ok=V4ok, rows=V4))
json.dump(out, open(OUT + "/mu_a.json", "w"), indent=1, default=str)
P = D.reset_index().rename(columns={"index": "day"})
P[["day", "y", "P_lr", "P_lgb", "y_bt72", "y_ew7d", "fit_month"]].to_parquet(OUT + "/mu_a_pred.parquet")
log.info("V: V1 %s V2 %s V3 %s V4 %s", V1ok, out["V2"]["ok"], out["V3"]["ok"], V4ok)
log.info("ghi %s/mu_a.json, mu_a_pred.parquet, mu_a.log", OUT)
