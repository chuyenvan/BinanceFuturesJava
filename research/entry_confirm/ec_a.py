#!/usr/bin/env python3
"""ENTRY_CONFIRM tang A (chan doan offline) - dung theo PREREG_ENTRY_CONFIRM.md (99d1c1f8).
Cum=(sym,m1); chan mo = m0 nho nhat; R(c,W): xac nhan tai phut t dau tien M<t<=M+W co close_t >= min(close_(M,t])*(1+c), close_t>0."""
import json
import logging
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/home/ubuntu/claude_master/gvz")
import gvz_mtm as MT  # noqa: E402
sys.path.insert(0, "/home/ubuntu/claude_master/iso")
import iso_risk_driver as I  # noqa: E402
import reset_rule_score as R  # noqa: E402

OUTD = "/home/ubuntu/claude_master/entry_confirm"
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("ec")
SEEDS = I.SEEDS if len(sys.argv) < 2 else sys.argv[1].split(",")
TEST = len(sys.argv) >= 2
DAY0 = pd.Timestamp(R.DAY0)
D0MS = int(DAY0.value // 10 ** 6)
ARMS = {"A1": (0.02, 240), "A2": (0.01, 60), "A3": (0.03, 1440)}
WMAX = max(w for _, w in ARMS.values())
PRE = 1  # luu them 1 phut truoc M (chan doan V2)
YEARS = [2021, 2022, 2023, 2024, 2025]

# ---- cum theo seed ----
CL, V1 = [], {}
for s in SEEDS:
    L = R.load_legs_minute(R.load_legs(I.OFF[s]))
    V1[s] = dict(n_leg=int(len(L)), sum_pnl=float(L["pnl"].sum()))
    L = L.reset_index(drop=True)
    L["_ord"] = np.arange(len(L))
    ties = 0
    for (sym, m1), g in L.groupby(["sym", "m1"], sort=False):
        mn = g["m0"].min()
        gg = g[g["m0"] == mn].sort_values("_ord")
        ties += int(len(gg) > 1)
        o = gg.iloc[0]
        CL.append(dict(seed=s, sym=str(sym) + "USDT", m1=int(m1), M=int(o["m0"]), P0=float(o["entry"]), N0=float(o["margin"]),
                       pnl=float(g["pnl"].sum()), ts=bool((g["status"].astype(str) == "STOP_LOSS_DONE").any()), n_leg=int(len(g))))
    nc = sum(1 for c in CL if c["seed"] == s)
    V1[s].update(n_cluster=nc, opener_ties=ties, sum_pnl_cluster=float(sum(c["pnl"] for c in CL if c["seed"] == s)))
    log.info("seed %s: legs %d, cum %d, ties m0 chan mo %d, sum pnl %.2f", s, V1[s]["n_leg"], nc, ties, V1[s]["sum_pnl"])
C = pd.DataFrame(CL)
C["tM"] = DAY0 + pd.to_timedelta(C["M"], unit="m")                  # UTC
C["year"] = (C["tM"] + pd.Timedelta(hours=7)).dt.year               # nam +07
log.info("tong cum %d, nam: %s", len(C), C["year"].value_counts().sort_index().to_dict())

# ---- gia: cua so offset -PRE..WMAX phut quanh M ----
NW = PRE + WMAX + 1
PX = np.full((len(C), NW), np.nan)
need = {}
for i, r in C.iterrows():
    a = r["tM"] - pd.Timedelta(minutes=PRE)
    b = r["tM"] + pd.Timedelta(minutes=WMAX)
    for ym in pd.period_range(a.to_period("M"), b.to_period("M"), freq="M"):
        need.setdefault(str(ym), []).append(i)
nomonth, nosym = [], 0
for ym in sorted(need):
    try:
        mc = MT.month_close(ym)
    except (FileNotFoundError, OSError) as e:
        nomonth.append(ym)
        log.info("thang %s: KHONG co file (%s) - %d cum anh huong", ym, type(e).__name__, len(need[ym]))
        continue
    for i in need[ym]:
        sym = C.at[i, "sym"]
        if sym not in mc:
            nosym += 1
            continue
        ts, cl = mc[sym]
        t0 = D0MS + int(C.at[i, "M"]) * 60000
        lo = np.searchsorted(ts, t0 - PRE * 60000, "left")
        hi = np.searchsorted(ts, t0 + WMAX * 60000, "right")
        if hi <= lo:
            continue
        tt = ts[lo:hi]
        off = (tt - t0)
        ok = (off % 60000 == 0)
        k = (off[ok] // 60000).astype(np.int64) + PRE
        PX[i, k] = cl[lo:hi][ok].astype(np.float64)
    log.info("thang %s: %d cum", ym, len(need[ym]))
log.info("thang thieu file: %s ; (cum,thang) thieu sym: %d", nomonth, nosym)

# ---- V2 ----
cM = PX[:, PRE]
dev = np.abs(C["P0"].to_numpy() / cM - 1)
cMm1 = PX[:, PRE - 1]
dev_m1 = np.abs(C["P0"].to_numpy() / cMm1 - 1)
cMp1 = PX[:, PRE + 1]
dev_p1 = np.abs(C["P0"].to_numpy() / cMp1 - 1)
V2 = dict(median_abs_dev_M=float(np.nanmedian(dev)), p90_abs_dev_M=float(np.nanpercentile(dev, 90)),
          median_abs_dev_Mminus1=float(np.nanmedian(dev_m1)), median_abs_dev_Mplus1=float(np.nanmedian(dev_p1)),
          n_closeM_missing=int(np.isnan(cM).sum()), ok=bool(np.nanmedian(dev) < 0.002))
log.info("V2: median |P0/close(M)-1| = %.4f%% (p90 %.3f%%); M-1 %.4f%%, M+1 %.4f%%; thieu close(M) %d -> %s",
         100 * V2["median_abs_dev_M"], 100 * V2["p90_abs_dev_M"], 100 * V2["median_abs_dev_Mminus1"],
         100 * V2["median_abs_dev_Mplus1"], V2["n_closeM_missing"], "OK" if V2["ok"] else "FAIL")

# ---- luat R(c,W) ----
W1 = PX[:, PRE + 1:]          # offset 1..WMAX
RUNMIN = np.fmin.accumulate(W1, axis=1)   # min tren (M,t], bo NaN
res, V3 = {}, {}
for arm, (c, W) in ARMS.items():
    x = W1[:, :W]
    lm = RUNMIN[:, :W]
    cond = (x >= lm * (1 + c)) & (x > 0)          # NaN -> False
    hit = cond.any(axis=1)
    k = np.argmax(cond, axis=1)
    Pc = np.where(hit, x[np.arange(len(x)), k], np.nan)
    C[arm + "_conf"] = hit
    C[arm + "_k"] = np.where(hit, k + 1, -1)
    C[arm + "_Pc"] = Pc
    miss_any = np.isnan(x).any(axis=1)
    miss_all = np.isnan(x).all(axis=1)
    C[arm + "_miss"] = miss_any
    V3[arm] = dict(n_miss_any=int(miss_any.sum()), n_miss_all=int(miss_all.sum()), rate_any=float(miss_any.mean()),
                   ok=bool(miss_any.mean() < 0.01))
    log.info("V3 %s: cum thieu >=1 phut trong cua so %d (%.3f%%), thieu ca cua so %d", arm, miss_any.sum(), 100 * miss_any.mean(), miss_all.sum())


def stats(g, arm):
    conf = g[arm + "_conf"]
    sk, cf = g[~conf], g[conf]
    lost = float((cf["N0"] * (cf[arm + "_Pc"] / cf["P0"] - 1)).sum())
    pskip = float(sk["pnl"].sum())
    return dict(n_cluster=int(len(g)), n_skip=int(len(sk)), skip_rate=float(len(sk) / len(g)) if len(g) else np.nan,
                pnl_skip=pskip, pnl_conf=float(cf["pnl"].sum()),
                pnl_per_skip=float(sk["pnl"].mean()) if len(sk) else np.nan,
                pnl_per_conf=float(cf["pnl"].mean()) if len(cf) else np.nan,
                ts_rate_skip=float(sk["ts"].mean()) if len(sk) else np.nan,
                ts_rate_conf=float(cf["ts"].mean()) if len(cf) else np.nan,
                lost=lost, dpnl=float(-pskip - lost),
                med_wait_min=float(cf[arm + "_k"].median()) if len(cf) else np.nan)


for arm in ARMS:
    res[arm] = {"seed": {}, "year": {}}
    for s in SEEDS:
        g = C[C["seed"] == s]
        st = stats(g, arm)
        st["by_year"] = {int(y): stats(g[g["year"] == y], arm) for y in YEARS if (g["year"] == y).any()}
        res[arm]["seed"][s] = st
    keys = ["n_cluster", "skip_rate", "pnl_skip", "pnl_per_skip", "pnl_per_conf", "ts_rate_skip", "ts_rate_conf", "lost", "dpnl", "med_wait_min"]
    res[arm]["mean"] = {k: float(np.mean([res[arm]["seed"][s][k] for s in SEEDS])) for k in keys}
    for y in YEARS:
        vals = [res[arm]["seed"][s]["by_year"].get(y) for s in SEEDS]
        vals = [v for v in vals if v]
        if vals:
            res[arm]["year"][y] = {k: float(np.mean([v[k] for v in vals])) for k in ("n_cluster", "skip_rate", "pnl_skip", "lost", "dpnl")}
    m = res[arm]["mean"]
    log.info("%s TB: n %.0f skip %.1f%% PnL_skip %+.0f PnL/bo %+.2f PnL/xn %+.2f ts bo %.1f%% ts xn %.1f%% lost %+.0f dPnL %+.0f cho med %.0f'",
             arm, m["n_cluster"], 100 * m["skip_rate"], m["pnl_skip"], m["pnl_per_skip"], m["pnl_per_conf"],
             100 * m["ts_rate_skip"], 100 * m["ts_rate_conf"], m["lost"], m["dpnl"], m["med_wait_min"])
    for s in SEEDS:
        q = res[arm]["seed"][s]
        log.info("   %s %-6s n %d skip %.1f%% PnL_skip %+.0f PnL/bo %+.2f PnL/xn %+.2f ts bo/xn %.1f/%.1f%% lost %+.0f dPnL %+.0f",
                 arm, s, q["n_cluster"], 100 * q["skip_rate"], q["pnl_skip"], q["pnl_per_skip"], q["pnl_per_conf"],
                 100 * q["ts_rate_skip"], 100 * q["ts_rate_conf"], q["lost"], q["dpnl"])
    for y, v in res[arm]["year"].items():
        log.info("   %s nam %d: n %.0f skip %.1f%% PnL_skip %+.0f lost %+.0f dPnL %+.0f (TB seed)", arm, y, v["n_cluster"],
                 100 * v["skip_rate"], v["pnl_skip"], v["lost"], v["dpnl"])

# ---- luat (chi A1) ----
A = res["A1"]
n = len(SEEDS)
D1v = A["mean"]["skip_rate"]
D1 = dict(skip_rate_mean=D1v, ok=bool(0.05 <= D1v <= 0.60))
d2a = sum(A["seed"][s]["pnl_per_skip"] < A["seed"][s]["pnl_per_conf"] for s in SEEDS)
d2b = sum(A["seed"][s]["pnl_skip"] < 0 for s in SEEDS)
D2 = dict(n_per_skip_lt_conf=int(d2a), n_pnl_skip_neg=int(d2b), ok=bool(d2a >= 6 and d2b >= 6))
d3pos = sum(A["seed"][s]["dpnl"] > 0 for s in SEEDS)
yrs = {y: A["year"][y]["dpnl"] for y in (2022, 2023, 2024, 2025) if y in A["year"]}
d3y = sum(v > 0 for v in yrs.values())
D3 = dict(dpnl_mean=A["mean"]["dpnl"], n_seed_pos=int(d3pos), year_dpnl=yrs, n_year_pos=int(d3y),
          ok=bool(A["mean"]["dpnl"] > 8000 and d3pos >= 6 and d3y >= 3))
RULE = dict(D1=D1, D2=D2, D3=D3, PASS=bool(D1["ok"] and D2["ok"] and D3["ok"]))
if n != 8:
    RULE["note"] = "chay thu %d seed - luat chi co nghia voi 8 seed" % n
log.info("D1 skip TB %.1f%% -> %s", 100 * D1v, "PASS" if D1["ok"] else "FAIL")
log.info("D2 PnL/bo<PnL/xn %d/%d, PnL_skip<0 %d/%d -> %s", d2a, n, d2b, n, "PASS" if D2["ok"] else "FAIL")
log.info("D3 dPnL TB %+.0f, seed duong %d/%d, nam duong %d/4 %s -> %s", A["mean"]["dpnl"], d3pos, n, d3y,
         {k: round(v) for k, v in yrs.items()}, "PASS" if D3["ok"] else "FAIL")
log.info("TONG: %s", "PASS (di tiep tang B)" if RULE["PASS"] else "FAIL (dong huong 3)")

# ---- V1 doi chieu ----
ext = json.load(open("/home/ubuntu/claude_master/tsx/ts_mkt_ext.json"))["rows"]
for s in SEEDS:
    ref = ext.get(s, {}).get("sum_pnl", [np.nan])[0]
    V1[s]["ts_mkt_ext_off_sum_pnl"] = float(ref)
    V1[s]["diff"] = float(V1[s]["sum_pnl"] - ref)
    log.info("V1 %-6s legs %d cum %d sumPnL %.2f | ts_mkt_ext OFF %.2f | lech %+.2f | sum cum %.2f",
             s, V1[s]["n_leg"], V1[s]["n_cluster"], V1[s]["sum_pnl"], ref, V1[s]["diff"], V1[s]["sum_pnl_cluster"])

out = dict(prereg="PREREG_ENTRY_CONFIRM.md@99d1c1f8", arms={k: dict(c=v[0], W=v[1]) for k, v in ARMS.items()}, seeds=SEEDS,
           V1=V1, V2=V2, V3=V3, months_missing=nomonth, rule_A1=RULE, results=res,
           limits="bo qua DCA neo lai theo Pc, duong thoat moi, hieu ung von/slot/quota (path divergence) => chi sang loc")
fn = os.path.join(OUTD, "ec_a_test.json" if TEST else "ec_a.json")
json.dump(out, open(fn, "w"), indent=1, default=float)
if not TEST:
    C.drop(columns=["tM"]).to_parquet(os.path.join(OUTD, "ec_a_clusters.parquet"))
log.info("ghi %s", fn)
