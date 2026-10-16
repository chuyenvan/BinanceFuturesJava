"""CARRY_OPP backtest (PREREG_CARRY_OPP.md 116de7e3). Usage: co_bt.py [check|run]
Chi tiet thuc thi (addendum 1, khai truoc khi chay run): cap dang giu duoc GIU neu con du dieu kien; slot trong lap bang s cao nhat;
notional co dinh tai luc vao = (equity/10)/CAP; PnL ngay t = N*(funding settle trong ngay t + ret_spot(t) - ret_perp(t)) (close-to-close);
vao/ra gia close ngay truoc (= mo cua ngay t). Thanh ly: (high_perp/ref - 1)*N >= margin => phat 1,5% N + dong cap.
"""
import glob
import io
import json
import logging
import os
import sys
import zipfile

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("cobt")
W = os.path.expanduser("~/claude_master/1016/carry")
THR, NMAX, FEE1, REB_FEE, LIQ_PEN = 0.0001, 10, 0.0015, 0.0015, 0.015
# [ADDENDUM 1 - truoc outcome] loai 17 sym lech perp/spot >20% so ngay (delist/ticker tai su dung/sai map)
BAD_SYMS = frozenset("BTCSTUSDT BTSUSDT CTKUSDT CVCUSDT CVXUSDT DGBUSDT FTTUSDT GLMRUSDT IDEXUSDT MDTUSDT RADUSDT RAYUSDT SCUSDT SLPUSDT SNTUSDT STPTUSDT STRAXUSDT".split())


def load_k(kind, s):
    rows = []
    for p in sorted(glob.glob(f"{W}/k/{kind}/{s}/*.zip")):
        with zipfile.ZipFile(p) as z:
            b = z.read(z.namelist()[0])
        x = pd.read_csv(io.BytesIO(b), header=None)
        if not str(x.iloc[0, 0]).strip().isdigit():
            x = x.iloc[1:]
        rows.append(x.iloc[:, [0, 2, 4, 7]].astype(float))
    if not rows:
        return None
    k = pd.concat(rows)
    k.columns = ["ot", "high", "close", "qv"]
    k["ot"] = np.where(k.ot > 1e14, k.ot / 1000, k.ot)  # spot 2025+ la micro-giay
    k["day"] = pd.to_datetime(k.ot, unit="ms").dt.floor("D")
    return k.drop_duplicates("day").set_index("day")[["high", "close", "qv"]]


def panel():
    S = pd.read_parquet(W + "/signal.parquet")
    syms = sorted(set(os.listdir(W + "/k/perp")) & set(os.listdir(W + "/k/spot")))
    parts = []
    for s in syms:
        p, q = load_k("perp", s), load_k("spot", s)
        if p is None or q is None:
            continue
        d = p.join(q, lsuffix="_p", rsuffix="_s", how="inner")
        d["sym"] = s
        parts.append(d.reset_index())
    K = pd.concat(parts, ignore_index=True)
    P = K.merge(S, on=["sym", "day"], how="left")
    P = P.sort_values(["sym", "day"])
    g = P.groupby("sym")
    P["liq_p"] = g.qv_p.transform(lambda x: x.rolling(30, min_periods=20).median().shift(1))
    P["liq_s"] = g.qv_s.transform(lambda x: x.rolling(30, min_periods=20).median().shift(1))
    P["ret_p"] = g.close_p.pct_change()
    P["ret_s"] = g.close_s.pct_change()
    P["prev_close_p"] = g.close_p.shift(1)
    P.to_parquet(W + "/panel.parquet")
    return P


def check(P):
    S = pd.read_parquet(W + "/signal.parquet")
    btc = S[S.sym == "BTCUSDT"].copy(); btc["y"] = btc.day.dt.year
    c1 = btc.groupby("y").fund_day.sum().round(4).to_dict()
    both = P.dropna(subset=["close_p", "close_s"])
    dev = (both.close_p / both.close_s - 1).abs()
    c2 = float((dev <= 0.02).mean())
    res = {"C1_btc_funding_sum_by_year": c1, "C1_btc_mean_annual": float(np.mean([v for k, v in c1.items() if 2021 <= k <= 2025])),
           "C2_close_within_2pct": c2, "C2_ok": c2 >= 0.99, "n_sym_panel": int(P.sym.nunique()), "days": [str(P.day.min()), str(P.day.max())],
           "worst_dev_syms": both.assign(dev=dev).groupby("sym").dev.apply(lambda x: (x > 0.02).mean()).sort_values(ascending=False).head(10).round(3).to_dict()}
    log.info("CHECK %s", json.dumps(res, default=str))
    json.dump(res, open(W + "/check.json", "w"), indent=1, default=str)
    return res


def simulate(P, cap=2.0, fee1=FEE1, excl=frozenset(), start="2021-01-01", end="2026-09-30", tag=""):
    P = P[(P.day >= start) & (P.day <= end) & ~P.sym.isin(excl) & ~P.sym.isin(BAD_SYMS)].copy()
    P["dev"] = (P.close_p / P.close_s - 1).abs()
    P["valid"] = (P.qv_p > 0) & (P.qv_s > 0) & (P.dev <= 0.02)
    days = sorted(P.day.unique())
    by = {d: g.set_index("sym") for d, g in P.groupby("day")}
    eq, hold, curve, nreb, nliq, ntr, inmk, ninv = 1.0, {}, [], 0, 0, 0, 0, 0
    for d in days:
        g = by[d]
        elig = g[(g.s > THR) & (g.liq_p >= 20e6) & (g.liq_s >= 5e6) & g.prev_close_p.notna() & g.valid]
        pnl = 0.0
        # dong cap khong con du dieu kien (tai mo cua ngay d)
        for s in list(hold):
            if s not in elig.index:
                pnl -= hold[s]["N"] * fee1; del hold[s]; ntr += 1
        free = NMAX - len(hold)
        if free > 0:
            for s in elig.drop(index=[x for x in hold if x in elig.index]).sort_values("s", ascending=False).index[:free]:
                N = eq / NMAX / cap
                hold[s] = {"N": N, "ref": float(elig.at[s, "prev_close_p"]), "M": N * (cap - 1)}
                pnl -= N * fee1
        # PnL trong ngay
        for s in list(hold):
            if s not in g.index or pd.isna(g.at[s, "ret_p"]) or pd.isna(g.at[s, "ret_s"]):
                continue
            h, r = hold[s], g.loc[s]
            if r.qv_p <= 0 or r.dev > 0.10:  # du lieu vo hieu (delist/stale) -> dong tai gia hom truoc
                pnl -= h["N"] * fee1; ninv += 1; del hold[s]; continue
            pnl += h["N"] * ((r.fund_day if pd.notna(r.fund_day) else 0.0) + r.ret_s - r.ret_p)
            if (r.high_p / h["ref"] - 1) * h["N"] >= h["M"]:
                pnl -= h["N"] * (LIQ_PEN + fee1); nliq += 1; del hold[s]; continue
            if (r.close_p / h["ref"] - 1) * h["N"] > 0.5 * h["M"]:
                pnl -= h["N"] * REB_FEE; nreb += 1; h["ref"] = float(r.close_p)
        inmk += int(len(hold) > 0)
        eq += pnl
        curve.append((d, eq, len(hold)))
    C = pd.DataFrame(curve, columns=["day", "eq", "n"]).set_index("day")
    r = C.eq.pct_change().fillna(C.eq.iloc[0] - 1)
    yrs = (C.index[-1] - C.index[0]).days / 365.25
    out = {"tag": tag, "cap": cap, "fee_rt": 2 * fee1, "CAGR": float(C.eq.iloc[-1] ** (1 / yrs) - 1), "Sharpe": float(r.mean() / r.std() * np.sqrt(365)) if r.std() > 0 else 0.0,
           "maxDD": float((C.eq / C.eq.cummax() - 1).min()), "pct_days_in": float(inmk / len(C)), "n_exits": ntr, "n_rebal": nreb, "n_liq": nliq, "n_invalid_close": ninv,
           "by_year": {int(y): float(g.eq.iloc[-1] / (C.eq[C.index < g.index[0]].iloc[-1] if (C.index < g.index[0]).any() else 1.0) - 1) for y, g in C.groupby(C.index.year)},
           "avg_pairs_when_in": float(C.n[C.n > 0].mean()) if (C.n > 0).any() else 0.0}
    return out, C


def crash_daily():
    d = pd.read_csv(os.path.expanduser("~/kaggle_sim/out/gqsf-a1/storage/printDone.csv"), index_col=False)
    d["t1"] = pd.to_datetime(d["end"], format="%Y%m%d %H:%M", errors="coerce") - pd.Timedelta(hours=7)
    d["t0"] = pd.to_datetime(d["start"], format="%Y%m%d %H:%M") - pd.Timedelta(hours=7)
    pnl = d.groupby(d.t1.dt.floor("D")).pnl.sum() / 35000.0
    trades_m = d.groupby(d.t0.dt.to_period("M")).size()
    return pnl, trades_m


def run():
    P = pd.read_parquet(W + "/panel.parquet")
    chk = json.load(open(W + "/check.json"))
    Pc = P[~P.sym.isin(BAD_SYMS)].dropna(subset=["close_p", "close_s"])
    c2b = float(((Pc.close_p / Pc.close_s - 1).abs() <= 0.02).mean())
    chk["C2_after_addendum1"] = c2b
    if c2b < 0.99:
        log.error("C2 (sau addendum) FAIL -> dung"); sys.exit(2)
    v21 = P[P.day.dt.year == 2021].groupby("sym").qv_p.mean().sort_values(ascending=False)
    top30 = frozenset(v21.index[:30])
    res = {"check": chk, "top30_2021": sorted(top30)}
    runs = [("DEV_main", dict(cap=2.0, end="2025-12-31")), ("DEV_cap1.5", dict(cap=1.5, end="2025-12-31")),
            ("DEV_maker", dict(cap=2.0, fee1=0.00075, end="2025-12-31")), ("DEV_excl_top30", dict(cap=2.0, end="2025-12-31", excl=top30)),
            ("HO2026", dict(cap=2.0, start="2025-12-01", end="2026-09-30"))]
    curves = {}
    for tag, kw in runs:
        o, C = simulate(P, tag=tag, **kw)
        if tag == "HO2026":
            C = C[C.index >= "2026-01-01"]; C = C / C.eq.iloc[0]
            yrs = (C.index[-1] - C.index[0]).days / 365.25
            o["CAGR"] = float(C.eq.iloc[-1] ** (1 / yrs) - 1); o["ret_total"] = float(C.eq.iloc[-1] - 1)
            o["maxDD"] = float((C.eq / C.eq.cummax() - 1).min())
        curves[tag] = C; res[tag] = o
        log.info("%-15s CAGR %+.2f%% Sharpe %.2f maxDD %.2f%% in %.0f%% pairs %.1f exits %d reb %d liq %d | nam %s", tag, 100 * o["CAGR"], o["Sharpe"],
                 100 * o["maxDD"], 100 * o["pct_days_in"], o["avg_pairs_when_in"], o["n_exits"], o["n_rebal"], o["n_liq"],
                 {k: round(100 * v, 2) for k, v in o["by_year"].items()})
    cp, tm = crash_daily()
    c = curves["DEV_main"].eq.pct_change().dropna()
    j = pd.concat([c.rename("carry"), cp.rename("crash")], axis=1).fillna(0.0)
    j = j[(j.index >= "2021-07-09") & (j.index <= "2025-11-21")]
    res["corr_daily"] = float(j.carry.corr(j.crash))
    cm = curves["DEV_main"].eq.resample("M").last().pct_change().dropna()
    cm.index = cm.index.to_period("M")
    idle = [m for m in cm.index if m >= pd.Period("2021-08", "M") and m <= pd.Period("2025-11", "M") and tm.get(m, 0) == 0]
    res["idle_months"] = {"n": len(idle), "carry_ret_sum": float(cm.loc[idle].sum()) if idle else 0.0,
                          "carry_ret_sum_all_months": float(cm.loc[(cm.index >= pd.Period("2021-08", "M")) & (cm.index <= pd.Period("2025-11", "M"))].sum())}
    m, x, h = res["DEV_main"], res["DEV_excl_top30"], res["HO2026"]
    G = {"G1": m["CAGR"] >= 0.05 and m["Sharpe"] >= 1.5,
         "G2": m["maxDD"] >= -0.10 and min(v for k, v in m["by_year"].items() if k <= 2025) >= -0.02,
         "G3": x["CAGR"] > 0 and x["Sharpe"] >= 1.0,
         "G4": (h["CAGR"] > 0) if h["pct_days_in"] > 0 else "chua_quan_sat",
         "G5": res["corr_daily"] <= 0.3, "G6": m["n_liq"] == 0}
    res["gates"] = G
    res["verdict"] = "GO" if all(v is True or v == "chua_quan_sat" for v in G.values()) else "NO-GO"
    log.info("corr ngay %.3f | thang he mua day 0 lenh: %s | GATES %s -> %s", res["corr_daily"], res["idle_months"], G, res["verdict"])
    json.dump(res, open(W + "/carry_opp_result.json", "w"), indent=1, default=str)
    curves["DEV_main"].to_csv(W + "/curve_dev_main.csv")


if __name__ == "__main__":
    if sys.argv[1] == "check":
        check(panel())
    else:
        run()
