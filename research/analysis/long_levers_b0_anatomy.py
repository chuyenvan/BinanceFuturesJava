#!/usr/bin/env python3
"""AUDIT LONG_LEVERS 2026-10-02 — giai phau PnL B0 (G2+FLAT3), 0-sim, CHI DOC.
Nguon: ~/kaggle_sim/out/de-p1/storage/printDone.csv (B0, md5 650c386f) + CLOSES_1H.bin (close 1h).
DEV <= 2025-12-31. Khong chay Java, khong 2026. Output: JSON (argv[1]) + bang text ra stdout.
"""
import sys, json, collections
import numpy as np, pandas as pd

PD = "/home/ubuntu/kaggle_sim/out/de-p1/storage/printDone.csv"
CL = "/home/ubuntu/java/fsrun/CLOSES_1H.bin"
SM = "/home/ubuntu/selector_pred_out/symbol_map.csv"
OUT = sys.argv[1] if len(sys.argv) > 1 else "/tmp/long_levers_b0_anatomy.json"
COST = 0.000982 + 2 * 0.000067
R = {}

d = pd.read_csv(PD)
d = d[d.side == "BUY"].copy()
d["t0"] = pd.to_datetime(d.start, format="%Y%m%d %H:%M")
d["t1"] = pd.to_datetime(d.end, format="%Y%m%d %H:%M")
d["notional"] = d.quantity * d.entry
d["ret_gross"] = d.tp / d.entry - 1
d["yr"] = d.t0.dt.year
d["q"] = d.t0.dt.year.astype(str) + "Q" + d.t0.dt.quarter.astype(str)
TOT = float(d.pnl.sum())
R["n"] = int(len(d)); R["sum_pnl"] = TOT; R["sum_funding"] = float(d.funding.sum())
R["sum_notional"] = float(d.notional.sum()); R["cost_total_est"] = float(d.notional.sum() * COST)
R["n_entry_ticks"] = int(d.start.nunique())
R["dca_rows_lastentry_ne_entry"] = int((abs(d.lastentry / d.entry - 1) > 1e-6).sum())


def grp(key, df=d):
    g = df.groupby(key)
    t = pd.DataFrame({"n": g.size(), "pnl": g.pnl.sum(), "mean_profit": g.profit.mean(),
                      "med_profit": g.profit.median(), "win": g.apply(lambda x: (x.pnl > 0).mean())})
    t["share"] = t.pnl / TOT
    return t


def show(name, t):
    print("\n## " + name)
    print(t.round(3).to_string())
    R[name] = {str(k): {c: (float(v) if not isinstance(v, str) else v) for c, v in row.items()}
               for k, row in t.iterrows()}

# ---------- 1. lop thoat / thoi gian giu / ROI bucket / level ----------
d["exit_cls"] = np.where(d.status == "STOP_MARKET_DONE", "TS_armed",
                         np.where(d.time_order >= 167, "TIME_STOP_168h", "SL_other"))
show("by_exit_cls", grp("exit_cls"))
show("by_level", grp("level"))
d["hold_b"] = pd.cut(d.time_order, [-1, 0, 1, 4, 12, 24, 48, 96, 166, 1000],
                     labels=["0h", "1h", "2-4h", "5-12h", "13-24h", "25-48h", "49-96h", "97-166h", "167h+"])
show("by_hold", grp("hold_b"))
d["roi_b"] = pd.cut(d.profit, [-1000, -30, -15, -7, 0, 4, 6, 8, 12, 20, 50, 1000])
show("by_roi_bucket", grp("roi_b"))
show("by_year", grp("yr"))
show("by_quarter", grp("q"))
d["hour"] = d.t0.dt.hour
d["dow_w"] = d.t0.dt.dayofweek
show("by_entry_hour", grp("hour"))
show("by_weekday", grp("dow_w"))

# ---------- 2. tier coin (volume luc vao = proxy thanh khoan), gia ----------
d["vol_q"] = pd.qcut(d.volume, 5, labels=["V1low", "V2", "V3", "V4", "V5high"])
show("by_volume_quintile", grp("vol_q"))

# ---------- 3. conviction: pred15m (p15 gate), symbolPred, ratio du lieu ----------
d["p15_q"] = pd.qcut(d.pred15m, 5, labels=["P1low", "P2", "P3", "P4", "P5high"])
show("by_p15_quintile", grp("p15_q"))
sp = d[d.symbolPred.notna()].copy()
sp["sp_q"] = pd.qcut(sp.symbolPred, 5, labels=["S1low", "S2", "S3", "S4", "S5high"])
show("by_symbolPred_quintile_selector", grp("sp_q", sp))
d["dow15_q"] = pd.qcut(d.dow15m, 5, labels=["D1deep", "D2", "D3", "D4", "D5shallow"])
show("by_dow15m_quintile", grp("dow15_q"))
# Spearman conviction -> profit (theo lenh) va trong cung tick vao
from scipy.stats import spearmanr
R["spearman_p15_profit"] = float(spearmanr(d.pred15m, d.profit).correlation)
R["spearman_symbolPred_profit"] = float(spearmanr(sp.symbolPred, sp.profit).correlation)
R["spearman_dow15m_profit"] = float(spearmanr(d.dow15m, d.profit).correlation)
print("\nspearman p15/symbolPred/dow15m vs profit:", R["spearman_p15_profit"],
      R["spearman_symbolPred_profit"], R["spearman_dow15m_profit"])

# ---------- 4. cum lenh: so lenh / tick vao, PnL theo co cum ----------
cs = d.groupby("start").size()
d["tick_n"] = d.start.map(cs)
d["tick_b"] = pd.cut(d.tick_n, [0, 1, 3, 7, 100], labels=["1", "2-3", "4-7", "8+"])
show("by_tick_cluster_size", grp("tick_b"))
# trong cung tick (>=3 lenh): lenh co symbolPred thap (tot hon?) co profit cao hon khong
w = sp[sp.start.map(cs) >= 3].copy()
w["rk"] = w.groupby("start").symbolPred.rank(pct=True)
w["dprof"] = w.profit - w.groupby("start").profit.transform("mean")
R["within_tick_spearman_symbolPred_dprofit"] = float(spearmanr(w.rk, w.dprof).correlation)
R["within_tick_n"] = int(len(w))
w["p15rk"] = w.groupby("start").pred15m.rank(pct=True)
print("within-tick spearman symbolPred-rank vs demeaned profit:", R["within_tick_spearman_symbolPred_dprofit"], len(w))

# ---------- 5. episode (ngay dong lenh, gap <= 2 ngay) ----------
days = sorted(d.t1.dt.normalize().unique())
eps, s, p = [], days[0], days[0]
for x in days[1:]:
    if (x - p).days > 2:
        eps.append((s, p)); s = x
    p = x
eps.append((s, p))
d["ep"] = -1
for i, (a, b) in enumerate(eps):
    d.loc[(d.t1.dt.normalize() >= a) & (d.t1.dt.normalize() <= b), "ep"] = i
ep = d.groupby("ep").agg(n=("pnl", "size"), pnl=("pnl", "sum"), t0=("t1", "min"), t1=("t1", "max"))
ep = ep.sort_values("pnl", ascending=False)
ep["share"] = ep.pnl / TOT
print("\n## top-8 episode"); print(ep.head(8).to_string())
print("## bottom-5 episode"); print(ep.tail(5).to_string())
R["n_episodes"] = int(len(ep)); R["top5_ep_share"] = float(ep.pnl.head(5).sum() / TOT)
R["top10_ep_share"] = float(ep.pnl.head(10).sum() / TOT)
R["top_episodes"] = [[str(r.t0.date()), str(r.t1.date()), int(r.n), float(r.pnl)] for _, r in ep.head(8).iterrows()]
# so lenh doc lap hieu dung: entry-day clusters
R["n_entry_days"] = int(d.t0.dt.normalize().nunique())

# ---------- 6. duong gia 1h: truoc/sau thoat ----------
DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("c", ">f4")])
a = np.fromfile(CL, dtype=DT)
ts_all = a["ts"].astype(np.int64); sy_all = a["sym"].astype(np.int32); c_all = a["c"].astype(np.float64)
del a
o = np.lexsort((ts_all, sy_all)); ts_all, sy_all, c_all = ts_all[o], sy_all[o], c_all[o]
bnd = np.flatnonzero(np.diff(sy_all)) + 1
starts = np.r_[0, bnd]; ends = np.r_[bnd, len(sy_all)]
SER = {int(sy_all[s]): (ts_all[s:e], c_all[s:e]) for s, e in zip(starts, ends)}
TMAX = int(ts_all.max())
m = pd.read_csv(SM); MP = dict(zip(m.symbol.str.replace("USDT$", "", regex=True), m.symId))
d["sid"] = d.sym.map(MP)
R["map_rate"] = float(d.sid.notna().mean())
H = 3600 * 1000


def at(sid, t):  # close cua bar cuoi cung co ts <= t
    ts, c = SER[sid]; i = np.searchsorted(ts, t, side="right") - 1
    return c[i] if i >= 0 else np.nan


def win(sid, t_a, t_b):
    ts, c = SER[sid]; i = np.searchsorted(ts, t_a, side="right"); j = np.searchsorted(ts, t_b, side="right")
    return c[i:j]


# can chinh mui gio: chon offset lam |entry/close-1| nho nhat
best = None
for off_h in (0, -7, 7, -1, 1):
    errs = []
    for r in d[d.sid.notna()].head(600).itertuples():
        sid = int(r.sid)
        if sid not in SER: continue
        t = int(r.t0.value // 10**6) + off_h * H
        cc = at(sid, t)
        if cc == cc and cc > 0: errs.append(abs(r.entry / cc - 1))
    med = float(np.median(errs)) if errs else 9
    print("offset", off_h, "median |entry/close-1|", med)
    if best is None or med < best[1]: best = (off_h, med)
OFF = best[0] * H; R["tz_offset_h"] = best[0]; R["tz_align_median_err"] = best[1]

rows = []
for r in d.itertuples():
    if r.sid != r.sid or int(r.sid) not in SER: continue
    sid = int(r.sid); t0 = int(r.t0.value // 10**6) + OFF; t1 = int(r.t1.value // 10**6) + OFF
    x = dict(idx=r.Index, sid=sid)
    pre = win(sid, t0, t1)
    x["mfe_pre_close"] = (pre.max() / r.entry - 1) if len(pre) else np.nan
    x["mae_pre_close"] = (pre.min() / r.entry - 1) if len(pre) else np.nan
    # gio dau tien close >= +7% (xap xi arm; close < high nen la can tren thoi gian arm)
    ts_, c_ = SER[sid]; i = np.searchsorted(ts_, t0, side="right"); j = np.searchsorted(ts_, t1, side="right")
    hit = np.flatnonzero(c_[i:j] >= r.entry * 1.07)
    x["arm_h_est"] = ((ts_[i + hit[0]] - t0) / H) if len(hit) else np.nan
    for hh in (24, 48, 72, 96, 120):
        x["c_t0_%d" % hh] = at(sid, t0 + hh * H) / r.entry - 1 if t0 + hh * H <= TMAX else np.nan
    for hh in (24, 72, 168):
        if t1 + hh * H > TMAX: x["post_ret_%d" % hh] = np.nan; x["post_mfe_%d" % hh] = np.nan; continue
        post = win(sid, t1, t1 + hh * H)
        x["post_ret_%d" % hh] = at(sid, t1 + hh * H) / r.tp - 1
        x["post_mfe_%d" % hh] = (post.max() / r.tp - 1) if len(post) else np.nan
        x["post_mae_%d" % hh] = (post.min() / r.tp - 1) if len(post) else np.nan
    rows.append(x)
P = pd.DataFrame(rows).set_index("idx"); d = d.join(P.drop(columns=["sid"]))
R["path_coverage"] = float(d.mfe_pre_close.notna().mean())


def q(s):
    s = s.dropna()
    return {"n": int(len(s)), "mean": float(s.mean()), "p25": float(s.quantile(.25)), "med": float(s.median()),
            "p75": float(s.quantile(.75)), "p90": float(s.quantile(.9)), "frac_gt_0": float((s > 0).mean()),
            "frac_gt_7pct": float((s > 0.07).mean())}


R["post_exit"] = {}
for cls in ("TS_armed", "TIME_STOP_168h"):
    g = d[d.exit_cls == cls]
    R["post_exit"][cls] = {k: q(g[k]) for k in ["post_ret_24", "post_ret_72", "post_ret_168", "post_mfe_24",
                                                    "post_mfe_72", "post_mfe_168", "post_mae_72"]}
    print("\n## post-exit", cls)
    for k, v in R["post_exit"][cls].items(): print(k, {a: round(b, 4) for a, b in v.items()})

# ---------- 7. pre-arm loser: co cham gan arm khong (close-based, can duoi cua high) ----------
ts_l = d[d.exit_cls == "TIME_STOP_168h"]
R["timestop_mfe_pre"] = {"n": int(len(ts_l)), "ge3": float((ts_l.mfe_pre_close >= .03).mean()),
                         "ge5": float((ts_l.mfe_pre_close >= .05).mean()), "med": float(ts_l.mfe_pre_close.median()),
                         "pnl": float(ts_l.pnl.sum()), "mean_profit": float(ts_l.profit.mean())}
print("\ntime-stop pre MFE:", R["timestop_mfe_pre"])
for hh in (24, 48, 72, 96, 120):
    R["timestop_mfe_pre"]["c_at_%dh_med" % hh] = float(ts_l["c_t0_%d" % hh].median())
    R["timestop_mfe_pre"]["c_at_%dh_frac_lt_m10" % hh] = float((ts_l["c_t0_%d" % hh] < -.10).mean())

# ---------- 8. counterfactual time-stop som hon (XAP XI, tuyen tinh notional, bo funding/realloc) ----------
R["cf_timestop"] = {}
for hh in (48, 72, 96, 120):
    aff = d[(d.time_order > hh) & ((d.status == "STOP_LOSS_DONE") | (d.arm_h_est > hh))]
    amb = d[(d.time_order > hh) & (d.status == "STOP_MARKET_DONE") & d.arm_h_est.isna()]
    cf = aff.notional * (aff["c_t0_%d" % hh] - COST)
    dl = float((cf - aff.pnl).sum())
    R["cf_timestop"][hh] = {"n_aff": int(len(aff)), "n_aff_winners": int((aff.status == "STOP_MARKET_DONE").sum()),
                            "dPnL": dl, "dPnL_losers": float((cf - aff.pnl)[aff.status == "STOP_LOSS_DONE"].sum()),
                            "dPnL_winners": float((cf - aff.pnl)[aff.status == "STOP_MARKET_DONE"].sum()),
                            "n_ambiguous_armed_by_high": int(len(amb))}
    print("cf time-stop", hh, R["cf_timestop"][hh])

# ---------- 9. re-entry sau TS: gia tiep tuc chay + he thong co vao lai ----------
ds = d.sort_values("t0")
re_n, re_pnl = 0, 0.0
for r in d[d.exit_cls == "TS_armed"].itertuples():
    nx = ds[(ds.sym == r.sym) & (ds.t0 > r.t1) & (ds.t0 <= r.t1 + pd.Timedelta(hours=72))]
    if len(nx): re_n += 1; re_pnl += float(nx.pnl.iloc[0])
R["reentry_after_TS_72h"] = {"n": re_n, "pnl_of_reentries": re_pnl}
print("re-entry after TS within 72h:", re_n, re_pnl)

# ---------- 10. sizing theo conviction (counterfactual tuyen tinh, cung tong notional) + CI block-72h ----------
rng = np.random.default_rng(20260905)
d["blk"] = ((d.t0 - pd.Timestamp("2021-07-01")).dt.total_seconds() // (72 * 3600)).astype(int)
BL = d.blk.unique()


def boot_sum(v, nrep=2000):
    s = pd.Series(v.values, index=d.loc[v.index, "blk"].values).groupby(level=0).sum()
    arr = s.reindex(BL, fill_value=0).values
    bs = np.array([arr[rng.integers(0, len(arr), len(arr))].sum() for _ in range(nrep)])
    return float(v.sum()), float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))


R["conviction_sizing"] = {}
for col, sign in (("pred15m", 1), ("symbolPred", -1), ("dow15m", -1), ("volume", -1)):
    g = d[d[col].notna()]
    rk = (sign * g[col]).rank(pct=True)
    wgt = 0.5 + rk  # 0.5x .. 1.5x, trung binh ~1
    wgt = wgt / (wgt * g.notional).sum() * g.notional.sum()
    dl = (wgt - 1) * g.pnl
    R["conviction_sizing"][col] = dict(zip(["dPnL", "lo", "hi"], boot_sum(dl)))
    print("conviction", col, R["conviction_sizing"][col])
R["sum_pnl_ci"] = dict(zip(["sum", "lo", "hi"], boot_sum(d.pnl)))
print("sum pnl CI block72:", R["sum_pnl_ci"])
for k in ("TS_armed", "TIME_STOP_168h", "SL_other"):
    print(k, "n", int((d.exit_cls == k).sum()))
json.dump(R, open(OUT, "w"), indent=1, default=str)
print("WROTE", OUT)

# ================= PHAN 2 (bo sung, cung pre-plan mo ta; khong doi phan 1) =================
# 11. CI block-72h cho counterfactual time-stop + kich ban xau (lenh armed-by-high mo ho cung bi cat)
R["cf_timestop_ci"] = {}
for hh in (48, 72, 96, 120):
    m_l = (d.time_order > hh) & (d.status == "STOP_LOSS_DONE")
    m_w = (d.time_order > hh) & (d.status == "STOP_MARKET_DONE") & (d.arm_h_est > hh)
    m_a = (d.time_order > hh) & (d.status == "STOP_MARKET_DONE") & d.arm_h_est.isna()
    cfv = d.notional * (d["c_t0_%d" % hh] - COST) - d.pnl
    base = cfv.where(m_l | m_w, 0.0).fillna(0.0)
    worst = cfv.where(m_l | m_w | m_a, 0.0).fillna(0.0)
    R["cf_timestop_ci"][hh] = {"base": boot_sum(base), "worst_amb_cut": boot_sum(worst),
                               "by_year_base": {int(y): float(base[d.yr == y].sum()) for y in sorted(d.yr.unique())}}
    print("cf TS CI", hh, R["cf_timestop_ci"][hh])

# 12. conviction dow15m / p15: bo episode top-1, theo nam
EPTOP = int(ep.index[0])
for col, sign in (("dow15m", -1), ("pred15m", 1)):
    rk = (sign * d[col]).rank(pct=True); wgt = 0.5 + rk
    wgt = wgt / (wgt * d.notional).sum() * d.notional.sum(); dl = (wgt - 1) * d.pnl
    R["conviction_sizing"][col + "_ex_top_ep"] = dict(zip(["dPnL", "lo", "hi"], boot_sum(dl.where(d.ep != EPTOP, 0.0))))
    R["conviction_sizing"][col + "_by_year"] = {int(y): float(dl[d.yr == y].sum()) for y in sorted(d.yr.unique())}
    print("conv", col, R["conviction_sizing"][col + "_ex_top_ep"], R["conviction_sizing"][col + "_by_year"])
d2 = d[d.ep != EPTOP].copy(); d2["dq"] = pd.qcut(d2.dow15m, 5, labels=False)
R["dow15m_quintile_ex_top_ep"] = d2.groupby("dq").profit.mean().round(3).to_dict()
print("dow15m quintile mean profit ex top ep:", R["dow15m_quintile_ex_top_ep"])

# 13. post-exit: tach beta — tru loi suat EW toan universe cung cua so (close 1h)
hrs = (ts_all // H).astype(np.int64); h0 = int(hrs.min()); hidx = hrs - h0
ns = int(sy_all.max()) + 1; nh = int(hidx.max()) + 1
PV = np.full((nh, ns), np.nan, dtype=np.float32); PV[hidx, sy_all] = c_all.astype(np.float32)


def ew(t_ms, hh):
    i = int(t_ms // H) - h0; j = i + hh
    if i < 0 or j >= nh: return np.nan
    a_, b_ = PV[i], PV[j]; ok = (a_ > 0) & (b_ > 0)
    return float(np.nanmean(b_[ok] / a_[ok] - 1)) if ok.sum() > 30 else np.nan


R["post_exit_excess"] = {}
for cls in ("TS_armed", "TIME_STOP_168h"):
    g = d[d.exit_cls == cls]; out = {}
    for hh in (24, 72, 168):
        e = np.array([ew(int(t.value // 10**6) + OFF, hh) for t in g.t1])
        ex = g["post_ret_%d" % hh].values - e
        ser = pd.Series(ex, index=g.index).dropna()
        bs = pd.Series(ser.values, index=d.loc[ser.index, "blk"].values).groupby(level=0).mean()
        bb = [bs.values[rng.integers(0, len(bs), len(bs))].mean() for _ in range(2000)]
        out[hh] = {"mean_ew": float(np.nanmean(e)), "mean_excess": float(ser.mean()), "med_excess": float(ser.median()),
                   "ci_blockmean": [float(np.percentile(bb, 2.5)), float(np.percentile(bb, 97.5))]}
    R["post_exit_excess"][cls] = out
    print("post-exit excess", cls, out)
for off_h in (-6, -7, -8):
    errs = [abs(r.tp / at(int(r.sid), int(r.t1.value // 10**6) + off_h * H) - 1)
            for r in d[(d.exit_cls == "TS_armed") & d.sid.notna()].head(600).itertuples() if int(r.sid) in SER]
    R["tz_check_exit_off%d" % off_h] = float(np.nanmedian(errs)); print("exit align", off_h, np.nanmedian(errs))
json.dump(R, open(OUT, "w"), indent=1, default=str)
print("WROTE2", OUT)

# ================= PHAN 3: time-decay arm (XAP XI close 1h, mo ta de dinh co lever, KHONG chon tham so) =========
# Luat gia dinh: neu chua arm (theo close) sau X gio => arm ha xuong +3%; sau do FLAT3: thoat khi close <= entry*(1+peak-0.03).
# Lenh da arm theo close truoc X: khong doi. Neu luat cf khong kich hoat truoc t1 goc: giu PnL goc.
R["time_decay_arm"] = {}
for X in (24, 48, 72):
    dl = pd.Series(0.0, index=d.index); nconv = 0; nconv_w = 0
    cand = d[(d.time_order > X) & ~(d.arm_h_est <= X) & d.sid.notna()]
    for r in cand.itertuples():
        sid = int(r.sid)
        if sid not in SER: continue
        t0 = int(r.t0.value // 10**6) + OFF; t1 = int(r.t1.value // 10**6) + OFF
        ts_, c_ = SER[sid]; i = np.searchsorted(ts_, t0 + X * H, side="right"); j = np.searchsorted(ts_, t1, side="right")
        cc = c_[i:j] / r.entry - 1
        armed, pk, ex = False, -9, None
        for v in cc:
            if not armed and v >= 0.03: armed = True
            if armed:
                pk = max(pk, v)
                if v <= pk - 0.03: ex = v; break
        if ex is None: continue
        dl[r.Index] = r.notional * (ex - COST) - r.pnl; nconv += 1
        nconv_w += int(r.status == "STOP_MARKET_DONE")
    R["time_decay_arm"][X] = {"n_cand": int(len(cand)), "n_conv": nconv, "n_conv_orig_winners": nconv_w,
                              "dPnL": boot_sum(dl), "dPnL_losers": float(dl[d.status == "STOP_LOSS_DONE"].sum()),
                              "dPnL_winners": float(dl[d.status == "STOP_MARKET_DONE"].sum()),
                              "by_year": {int(y): float(dl[d.yr == y].sum()) for y in sorted(d.yr.unique())}}
    print("time-decay arm X=%d" % X, R["time_decay_arm"][X])
json.dump(R, open(OUT, "w"), indent=1, default=str)
print("WROTE3", OUT)
