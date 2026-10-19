#!/usr/bin/env python3
"""TS_AFTER (chan doan, chi mo ta): lenh bi time-stop 168h tren K24+skipFull (8 seed gqsf) - neu GIU them thi sao?"""
import json
import logging
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/home/ubuntu/claude_master/gvz")
import gvz_mtm as MT  # noqa: E402
sys.path.insert(0, "/home/ubuntu/claude_master/iso")
import iso_risk_driver as I  # noqa: E402
import reset_rule_score as R  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("tsa")
S = I.SEEDS
HZ = [7, 14, 30, 60, 90]
DAY0 = pd.Timestamp(R.DAY0)
D0MS = int(DAY0.value // 10 ** 6)
END = pd.Timestamp("2026-01-01")

# ---- cum ts theo seed ----
CL, ALL = [], {}
for s in S:
    L = R.load_legs_minute(R.load_legs(I.OFF[s]))
    hold_d = (L["m1"] - L["m0"]) / 1440.0
    ALL[s] = dict(pnl=float(L["pnl"].sum()), capdays=float((L["margin"] * hold_d).sum()), legs=L[["sym", "m0"]].copy())
    t = L[L["status"].astype(str) == "STOP_LOSS_DONE"]
    for (sym, m1), g in t.groupby(["sym", "m1"]):
        q = float(g["quantity"].sum())
        CL.append(dict(seed=s, sym=str(sym) + "USDT", m1=int(m1), q=q, avg=float((g["quantity"] * g["entry"]).sum() / q),
                       pnl_cut=float(g["pnl"].sum()), n_leg=len(g)))
C = pd.DataFrame(CL)
C["t_cut"] = DAY0 + pd.to_timedelta(C["m1"], unit="m")
log.info("cum time-stop: %d (%.0f/seed), legs %d, pnl_cut %.0f/seed", len(C), len(C) / 8, C["n_leg"].sum(), C["pnl_cut"].sum() / 8)

# ---- duong gia sau cat (toi 90 ngay) ----
need = {}
for i, r in C.iterrows():
    for ym in pd.period_range(r["t_cut"].to_period("M"), (r["t_cut"] + pd.Timedelta(days=91)).to_period("M"), freq="M"):
        if ym.start_time < END:
            need.setdefault(str(ym), []).append(i)
path = {i: ([], []) for i in C.index}
for ym in sorted(need):
    mc = MT.month_close(ym)
    for i in need[ym]:
        sym = C.at[i, "sym"]
        if sym in mc:
            ts, cl = mc[sym]
            path[i][0].append(ts)
            path[i][1].append(cl)
    log.info("thang %s: %d cum", ym, len(need[ym]))

z = np.load("/home/ubuntu/claude_master/edge_attr/index.npz")
ew_g = (z["ew_ts"].astype(np.int64) - D0MS) // 60000
ewc = pd.Series(np.cumsum(z["ew_r"]), index=ew_g)   # log chi so alt EW
ewd = ewc.groupby(ewc.index // 1440).last()

rows = []
for i, r in C.iterrows():
    if not path[i][0]:
        continue
    ts = np.concatenate(path[i][0])
    cl = np.concatenate(path[i][1]).astype(float)
    o = np.argsort(ts)
    ts, cl = ts[o], cl[o]
    t0 = D0MS + r["m1"] * 60000
    k0 = np.searchsorted(ts, t0)
    if k0 >= len(ts):
        continue
    pc = cl[min(k0, len(cl) - 1)]
    d = dict(i=i, pc=pc)
    for H in HZ:
        t1 = t0 + H * 86400000
        if pd.Timestamp(t1, unit="ms") > END - pd.Timedelta(days=1):
            d["ok%d" % H] = False
            continue
        k1 = np.searchsorted(ts, t1)
        seg = cl[k0:k1 + 1]
        if len(seg) < 10:
            d["ok%d" % H] = False
            continue
        d["ok%d" % H] = True
        d["ret%d" % H] = seg[-1] / pc - 1
        d["mdd%d" % H] = seg.min() / pc - 1
        d["be%d" % H] = bool(seg.max() >= r["avg"])
        arm = r["avg"] * 1.07
        hit = np.nonzero(seg >= arm)[0]
        exitp = arm * 0.97 if len(hit) else seg[-1]
        d["exit_day%d" % H] = (hit[0] / 1440.0) if len(hit) else float(H)
        d["inc%d" % H] = r["q"] * (exitp - pc)        # PnL them so voi cat (bo phi)
        d["arm%d" % H] = bool(len(hit))
    dd = int(r["m1"] // 1440)
    w = ewd.loc[max(dd - 30, ewd.index.min()):dd]
    d["mkt_dd30"] = float(np.exp(w.iloc[-1] - w.max()) - 1) if len(w) else np.nan
    rows.append(d)
D = pd.DataFrame(rows).set_index("i")
C = C.join(D, how="inner")
C["notional"] = C["q"] * C["pc"]
C["year"] = C["t_cut"].dt.year
C["mkt_t"] = pd.qcut(C["mkt_dd30"], 3, labels=["T1 alt sap manh", "T2", "T3 alt binh thuong"])
rcap = np.mean([ALL[s]["pnl"] / ALL[s]["capdays"] for s in S])   # lai/USD-margin/ngay cua he
log.info("cum co duong gia: %d ; r_cap he = %.5f /USD/ngay (%.2f%%/ngay)", len(C), rcap, 100 * rcap)
log.info("mkt_dd30 tercile bien: %s", C.groupby("mkt_t", observed=True)["mkt_dd30"].agg(["min", "max"]).round(3).to_dict())

out = {"n_cluster": len(C), "rcap": rcap, "pnl_cut_per_seed": float(C["pnl_cut"].sum() / 8)}


def summ(G, tag):
    res = {}
    for H in HZ:
        g = G[G.get("ok%d" % H, False) == True]  # noqa: E712
        if not len(g):
            continue
        inc = g["inc%d" % H].sum() / 8
        opp = (rcap * g["notional"] * g["exit_day%d" % H]).sum() / 8
        res[H] = dict(n=int(len(g)), ret_med=float(g["ret%d" % H].median()), ret_mean=float(g["ret%d" % H].mean()),
                      mdd_med=float(g["mdd%d" % H].median()), mdd_p10=float(g["mdd%d" % H].quantile(0.1)),
                      be=float(g["be%d" % H].mean()), arm=float(g["arm%d" % H].mean()),
                      inc_per_seed=float(inc), opp_per_seed=float(opp), net_per_seed=float(inc - opp))
        log.info("%-22s H=%2dd n=%4d ret med %+.1f%% mean %+.1f%% | mdd med %+.1f%% p10 %+.1f%% | ve hoa von %.0f%% cham arm %.0f%% | "
                 "PnL them %+.0f  chi phi co hoi %.0f  rong %+.0f /seed", tag, H, len(g), 100 * res[H]["ret_med"],
                 100 * res[H]["ret_mean"], 100 * res[H]["mdd_med"], 100 * res[H]["mdd_p10"], 100 * res[H]["be"],
                 100 * res[H]["arm"], inc, opp, inc - opp)
    return res


out["all"] = summ(C, "TAT CA")
out["by_mkt"] = {str(k): summ(g, str(k)) for k, g in C.groupby("mkt_t", observed=True)}
out["by_year"] = {int(k): summ(g, "nam %d" % k) for k, g in C.groupby("year")}
# tai vao lai cung coin trong 30 ngay sau cat (de biet phan "co cua cuu" da duoc he bat lai)
re = []
for _, r in C.iterrows():
    lg = ALL[r["seed"]]["legs"]
    s = lg[(lg["sym"].astype(str) + "USDT" == r["sym"]) & (lg["m0"] > r["m1"]) & (lg["m0"] <= r["m1"] + 30 * 1440)]
    re.append(len(s) > 0)
C["reentry30"] = re
log.info("ty le cum bi he vao lai cung coin trong 30 ngay: %.1f%%", 100 * np.mean(re))
out["reentry30"] = float(np.mean(re))
json.dump(out, open("/home/ubuntu/claude_master/ts_after/ts_after.json", "w"), indent=1, default=float)
C.drop(columns=["t_cut"]).to_parquet("/home/ubuntu/claude_master/ts_after/clusters.parquet")
