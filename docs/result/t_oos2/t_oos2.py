#!/usr/bin/env python3
"""T_OOS2 (PREREG_T_OOS2): kiem DOC LAP lan 2 bo loc T (sleeve spot: OFF khi close ngay <= thr x dinh close P ngay; vao lai khi close ngay > max close R ngay truoc)
 (A) BTC Bitstamp 2014-01-01..2017-07-31 (truoc Binance); (B1) ETHUSDT spot 2018-01-01..2019-12-31; (B2) ETHUSDT spot 2021-07-01..2025-12-31.
TAI DUNG DUNG cac ham trong docs/result/t_oos/t_oos.py (t_states, run_equity, bh_equity, metrics, evaluate, lookahead_check, ...) - nap theo duong dan, kiem sha256,
KHONG viet lai. Chi them: nap du lieu (cho phep nam >= 2021, cam 2020), tong hop theo ky, thong ke dot ON, do nhay phi 0,30 %/chieu, bang markdown.
Usage:
  python3 -I t_oos2.py --mode selftest --toos-dir DIR_T_OOS --out OUT           (chi dung du lieu T_OOS cu 2018-19 BTC: V1 + doi chieu)
  python3 -I t_oos2.py --mode run --toos-dir DIR_T_OOS --data-dir DIR_DATA --out OUT
"""
import argparse
import hashlib
import importlib.util
import json
import logging
import math
import os
import sys

import numpy as np
import pandas as pd

log = logging.getLogger("toos2")
TOOS_SHA = "d36af81313e95829b285064c03995e8b81bb79ad16565db30cc60a14a560cfaf"   # docs/result/t_oos/t_oos.py (commit prereg T_OOS 27d33a1e)
BTC18_CLEAN_SHA = "b08921d392de29b310c93dd298d7f4bdc7f781abb9e839efccee2565b7e85f7a"
COST_HI = 0.0030                     # do nhay phi: 0,30 %/chieu (0,15 % -> x2), chi mo ta
CELLS_NEED = 19                      # >= 70 % cua 27 o

# moc quyet dinh co dinh (khong doi sau prereg)
PERIODS = [
    dict(name="A_BTC_2014_2017", asset="BTC (Bitstamp USD)", file="btc_bitstamp_1d_clean.csv", t0="2013-12-31", end="2017-07-31",
         cuts=["2015-06-30", "2016-06-30", "2017-03-31"], main=True),
    dict(name="B1_ETH_2018_2019", asset="ETHUSDT spot", file="eth_seg1_1d_clean.csv", t0="2017-12-31", end="2019-12-31",
         cuts=["2018-04-30", "2018-12-31", "2019-06-30"], main=False),
    dict(name="B2_ETH_2021_2025", asset="ETHUSDT spot", file="eth_seg2_1d_clean.csv", t0="2021-06-30", end="2025-12-31",
         cuts=["2022-06-30", "2023-12-31", "2025-03-31"], main=False),
]


# ------------------------------------------------------------------------------------------------ nap ham T_OOS goc
def load_toos(toos_dir):
    p = os.path.join(toos_dir, "t_oos.py")
    sha = hashlib.sha256(open(p, "rb").read()).hexdigest()
    assert sha == TOOS_SHA, "t_oos.py sha256 khac prereg: %s" % sha
    spec = importlib.util.spec_from_file_location("t_oos_orig", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


# ------------------------------------------------------------------------------------------------ du lieu
def load_clean2(path):
    """Giong T.load_clean nhung cho phep nam >= 2021; CAM bat ky ngay nao nam 2020 (V2)."""
    d = pd.read_csv(path)
    d["date"] = pd.to_datetime(d["date"]).dt.date
    d = d.sort_values("date").reset_index(drop=True)
    assert d["date"].is_unique, "ngay trung"
    yrs = pd.to_datetime(d["date"]).dt.year
    assert not (yrs == 2020).any(), "V2: co ngay nam 2020"
    full = pd.date_range(d["date"].min(), d["date"].max(), freq="D").date
    assert len(full) == len(d) and all(a == b for a, b in zip(full, d["date"])), "thieu ngay sau khi lam day"
    assert (d["close"] > 0).all() and d["close"].notna().all()
    return list(d["date"]), d["close"].to_numpy(float)


def sha_file(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


# ------------------------------------------------------------------------------------------------ danh gia them phi (khong sua T_OOS)
def evaluate_cost(T, dc, days, dates, thr, P, R, cost, st_override=None):
    """Dung dung T.t_states / T.run_equity / T.bh_equity / T.metrics nhu T.evaluate, chi cho phep doi phi."""
    if st_override is None:
        st, sw = T.t_states(dc, days, thr, P, R, True)
    else:
        st = st_override
        sw = [(n, "ON" if st[n] else "OFF") for n in range(1, len(st)) if st[n] != st[n - 1]]
    eq, trades, eps = T.run_equity(dc, days, st, cost)
    bh = T.bh_equity(dc, days, cost)
    steps = len(days) - 1

    def dof(k):
        return dates[days[max(k - 1, 0)]]
    mt = T.metrics(T.primary_series(eq), steps, dof)
    mb = T.metrics(T.primary_series(bh), steps, dof)
    c1 = abs(mt["maxdd"]) <= 0.6 * abs(mb["maxdd"])
    c2 = mt["total"] >= mb["total"]
    c3 = mt["maxdd"] >= -0.40
    return dict(T=mt, BH=mb, c1=bool(c1), c2=bool(c2), c3=bool(c3), switches=len(sw), off_days=int((~st).sum()),
                eq=eq, bh=bh, st=st, trades=trades, episodes=eps)


def ep_stats(rows, total):
    """Thong ke dot ON: so dot, thang, dot lon nhat, LN cac dot con lai nhan lai, ty phan log-LN cua dot lon nhat."""
    rets = [r["ret"] for r in rows]
    n = len(rets)
    prod_all = float(np.prod([1.0 + x for x in rets])) - 1.0 if n else 0.0
    assert abs(prod_all - total) < 1e-9, "tich cac dot != tong LN T (%r vs %r)" % (prod_all, total)
    if n == 0:
        return dict(n=0, wins=0, max_ret=None, max_entry=None, max_exit=None, rest_compounded=None, share_log=None, median=None,
                    min=None, n_le2d=0)
    k = int(np.argmax(rets))
    rest = float(np.prod([1.0 + x for i, x in enumerate(rets) if i != k])) - 1.0
    share = (math.log1p(rets[k]) / math.log1p(total)) if total > 0 else None
    return dict(n=n, wins=int(sum(1 for x in rets if x > 0)), max_ret=float(rets[k]), max_entry=rows[k]["entry"], max_exit=rows[k]["exit"],
                rest_compounded=rest, share_log=share, median=float(np.median(rets)), min=float(min(rets)),
                n_le2d=int(sum(1 for r in rows if (r["exit"] is not None and (pd.Timestamp(r["exit"]) - pd.Timestamp(r["entry"])).days <= 2))))


def run_period(T, name, dc, dates, t0, end, cuts, asset="", with_v3=True):
    idx = {str(d): i for i, d in enumerate(dates)}
    j0, j1 = idx[t0], idx[end]
    days = list(range(j0, j1 + 1))
    BASE = T.BASE
    log.info("[%s] data %s..%s n=%d ; cham t0=%s .. %s (%d buoc) ; lich su truoc t0 = %d ngay close", name, dates[0], dates[-1], len(dates), t0, end,
             len(days) - 1, j0 + 1)
    out = dict(name=name, asset=asset, first=str(dates[0]), last=str(dates[-1]), t0=t0, end=end, steps=len(days) - 1, hist_days_to_t0=j0 + 1)

    prim = T.evaluate(dc, days, dates, **BASE)
    eps = T.ep_rows(prim, days, dates)
    st = ep_stats(eps, prim["T"]["total"])
    out["primary"] = dict(T=prim["T"], BH=prim["BH"], c1=prim["c1"], c2=prim["c2"], c3=prim["c3"], switches=prim["switches"],
                          off_days=prim["off_days"], n_decision_days=len(days), episodes=eps, trades=T.trade_rows(prim, days, dates),
                          dd_ratio=abs(prim["T"]["maxdd"]) / abs(prim["BH"]["maxdd"]), ep_stats=st)
    log.info("[%s] T  : %s ; sw=%d off=%d", name, T.short(prim["T"]), prim["switches"], prim["off_days"])
    log.info("[%s] B&H: %s", name, T.short(prim["BH"]))
    log.info("[%s] C1=%s C2=%s C3=%s", name, prim["c1"], prim["c2"], prim["c3"])

    grid = []
    for thr in T.GRID_THR:
        for P in T.GRID_P:
            for R in T.GRID_R:
                r = T.evaluate(dc, days, dates, thr, P, R)
                grid.append(dict(thr=thr, P=P, R=R, T_total=r["T"]["total"], T_maxdd=r["T"]["maxdd"], BH_total=r["BH"]["total"],
                                 BH_maxdd=r["BH"]["maxdd"], c1=r["c1"], c2=r["c2"], c3=r["c3"], both=bool(r["c1"] and r["c2"]),
                                 switches=r["switches"], off_days=r["off_days"]))
    n_both = sum(g["both"] for g in grid)
    cond_sub = n_both >= CELLS_NEED
    centre = [g for g in grid if (g["thr"], g["P"], g["R"]) == (0.70, 180, 30)][0]
    assert centre["T_total"] == prim["T"]["total"] and centre["T_maxdd"] == prim["T"]["maxdd"], "o trung tam != T chinh"
    out["grid"] = grid
    out["grid_summary"] = dict(n_cells=len(grid), n_c1c2=n_both, n_c1=sum(g["c1"] for g in grid), n_c2=sum(g["c2"] for g in grid),
                               n_c3=sum(g["c3"] for g in grid), threshold_cells=CELLS_NEED, cond_sub=bool(cond_sub))
    log.info("[%s] GRID: %d/27 o dat C1&C2 (can >= %d)", name, n_both, CELLS_NEED)
    passed = bool(prim["c1"] and prim["c2"] and prim["c3"] and cond_sub)
    out["pass"] = passed
    out["verdict"] = "PASS (khong bi bac bo)" if passed else "FAIL"
    log.info("[%s] VERDICT: %s", name, out["verdict"])

    # --- bao cao phu: warm-start (khong tham gia verdict)
    st_w, sw_w = T.t_states(dc, list(range(0, j1 + 1)), **BASE)
    rw = T.evaluate(dc, days, dates, 0.70, 180, 30, st_override=st_w[j0:])
    out["warm_start"] = dict(T=rw["T"], BH=rw["BH"], c1=rw["c1"], c2=rw["c2"], c3=rw["c3"], switches=rw["switches"], off_days=rw["off_days"],
                             state_at_t0="ON" if st_w[j0] else "OFF", switches_before_t0=int(sum(1 for n, _ in sw_w if n < j0)),
                             trades=T.trade_rows(rw, days, dates))

    # --- bao cao phu: do nhay phi 0,30 %/chieu (mo ta, khong tham gia verdict)
    fe = evaluate_cost(T, dc, days, dates, 0.70, 180, 30, COST_HI)
    gcnt, gcells = 0, []
    for thr in T.GRID_THR:
        for P in T.GRID_P:
            for R in T.GRID_R:
                r = evaluate_cost(T, dc, days, dates, thr, P, R, COST_HI)
                gcells.append(bool(r["c1"] and r["c2"]))
    out["fee_hi"] = dict(cost=COST_HI, T=fe["T"], BH=fe["BH"], c1=fe["c1"], c2=fe["c2"], c3=fe["c3"], switches=fe["switches"],
                         n_c1c2_cells=int(sum(gcells)))
    log.info("[%s] PHI 0,30 %%: T %s | B&H %s | C1/C2/C3=%s/%s/%s | luoi %d/27", name, T.short(fe["T"]), T.short(fe["BH"]), fe["c1"], fe["c2"], fe["c3"],
             sum(gcells))

    # --- V3 look-ahead
    if with_v3:
        out["v3"] = T.lookahead_check(dc, days, BASE, [idx[c] for c in cuts], name)
    return out


# ------------------------------------------------------------------------------------------------ V1
def v1_check(T, toos_dir, clean18, ref_json):
    """V1: tai lap T_OOS 2018-2019 BTC (+75,4 %, DD -35,3 %, 35 lan doi) bang CUNG ma + doi chieu t_oos_res.json (primary, 27 o, dot ON, giao dich)."""
    assert sha_file(clean18) == BTC18_CLEAN_SHA, "btcusdt_1d_clean.csv sha256 khac"
    dates, dc = T.load_clean(clean18)
    r = run_period(T, "V1_BTC_2018_2019", dc, dates, T.T0_DATE, T.END_DATE, ["2018-04-30", "2018-12-31", "2019-06-30"], "BTCUSDT spot", with_v3=False)
    ref = json.load(open(ref_json))
    p, q = r["primary"], ref["primary"]
    ok = dict(total=p["T"]["total"] == q["T"]["total"], maxdd=p["T"]["maxdd"] == q["T"]["maxdd"], switches=p["switches"] == q["switches"] == 35,
              off_days=p["off_days"] == q["off_days"], bh_total=p["BH"]["total"] == q["BH"]["total"], bh_maxdd=p["BH"]["maxdd"] == q["BH"]["maxdd"],
              grid=all(a["T_total"] == b["T_total"] and a["T_maxdd"] == b["T_maxdd"] and a["switches"] == b["switches"]
                       for a, b in zip(r["grid"], ref["grid"])),
              n_c1c2=r["grid_summary"]["n_c1c2"] == ref["grid_summary"]["n_c1c2"] == 21,
              episodes=all(abs(a["ret"] - b["ret"]) < 1e-12 and a["entry"] == b["entry"] and a["exit"] == b["exit"]
                           for a, b in zip(p["episodes"], q["episodes"])) and len(p["episodes"]) == len(q["episodes"]) == 18,
              trades=p["trades"] == q["trades"])
    # cost-evaluation consistency: evaluate_cost(COST) == evaluate
    j0 = {str(d): i for i, d in enumerate(dates)}[T.T0_DATE]
    j1 = {str(d): i for i, d in enumerate(dates)}[T.END_DATE]
    days = list(range(j0, j1 + 1))
    ec = evaluate_cost(T, dc, days, dates, 0.70, 180, 30, T.COST)
    ok["cost_fn_consistent"] = bool(ec["T"]["total"] == p["T"]["total"] and ec["T"]["maxdd"] == p["T"]["maxdd"] and ec["BH"]["total"] == p["BH"]["total"])
    ok["headline"] = bool(round(100 * p["T"]["total"], 1) == 75.4 and round(100 * p["T"]["maxdd"], 1) == -35.3)
    res = dict(ok=bool(all(ok.values())), checks=ok, T=p["T"], BH=p["BH"], switches=p["switches"], off_days=p["off_days"])
    log.info("V1: %s", res)
    assert res["ok"], "V1 FAIL: %s" % ok
    return res, r


# ------------------------------------------------------------------------------------------------ bang markdown
def pct(x, d=1):
    return "%+.*f %%" % (d, 100 * x)


def md_period(r):
    p = r["primary"]
    T, B, s = p["T"], p["BH"], p["ep_stats"]
    L = []
    L.append("### %s - %s, cua so cham %s..%s (%d buoc; lich su close truoc t0 = %d ngay)" % (r["name"], r["asset"], r["t0"], r["end"], r["steps"], r["hist_days_to_t0"]))
    L.append("")
    L.append("| | tong LN | CAGR | maxDD | dinh -> day (close ngay) | so lan doi | ngay OFF |")
    L.append("|---|---|---|---|---|---|---|")
    L.append("| T | %s | %s | %s | %s -> %s | %d | %d / %d |" % (pct(T["total"]), pct(T["cagr"]), pct(T["maxdd"]), T["peak_date"], T["trough_date"], p["switches"], p["off_days"], p["n_decision_days"]))
    L.append("| B&H | %s | %s | %s | %s -> %s | - | - |" % (pct(B["total"]), pct(B["cagr"]), pct(B["maxdd"]), B["peak_date"], B["trough_date"]))
    L.append("")
    L.append("Tieu chi: C1 |DD_T|<=0,6x|DD_B&H| : %.1f %% vs %.1f %% -> ty le %.3f -> %s ; C2 LN_T>=LN_B&H : %s vs %s -> %s ; C3 |DD_T|<=40 %% : %.1f %% -> %s ; luoi %d/27 (can >= %d) -> %s ; **verdict %s**" % (
        100 * abs(T["maxdd"]), 100 * abs(B["maxdd"]), p["dd_ratio"], "DAT" if p["c1"] else "TRUOT", pct(T["total"]), pct(B["total"]), "DAT" if p["c2"] else "TRUOT",
        100 * abs(T["maxdd"]), "DAT" if p["c3"] else "TRUOT", r["grid_summary"]["n_c1c2"], CELLS_NEED, "DAT" if r["grid_summary"]["cond_sub"] else "TRUOT", r["verdict"]))
    L.append("")
    if s["n"]:
        L.append("Dot ON (net phi): %d dot, %d thang, median %s, min %s, max %s (%s -> %s); %d dot keo dai <= 2 ngay; LN %d dot con lai nhan lai %s; ty phan log-LN cua dot lon nhat %s" % (
            s["n"], s["wins"], pct(s["median"]), pct(s["min"]), pct(s["max_ret"]), s["max_entry"], (s["max_exit"] or "mo cuoi ky"), s["n_le2d"], s["n"] - 1, pct(s["rest_compounded"]),
            ("%.0f %%" % (100 * s["share_log"]) if s["share_log"] is not None else "n/a (T khong duong)")))
    L.append("")
    L.append("Dot ON:")
    L.append("")
    L.append("| # | vao | ra | LN |")
    L.append("|---|---|---|---|")
    for i, e in enumerate(p["episodes"], 1):
        L.append("| %d | %s | %s | %s%s |" % (i, e["entry"], e["exit"] or "(mo cuoi ky)", pct(e["ret"]), " (MTM)" if e["open"] else ""))
    L.append("")
    L.append("Ngay doi trang thai (close UTC; dong dau = mua khoi tao tai t0):")
    L.append("")
    L.append("| ngay | lenh | gia |")
    L.append("|---|---|---|")
    for t in p["trades"]:
        L.append("| %s | %s | %.2f |" % (t["date"], t["action"], t["price"]))
    L.append("")
    L.append("Luoi 27 o (LN T / DD T . C1C2C3 . so lan doi; B&H %s / %s):" % (pct(B["total"]), pct(B["maxdd"])))
    L.append("")
    g = r["grid"]
    for thr in sorted({x["thr"] for x in g}):
        L.append("thr %.2f | R=20 | R=30 | R=40" % thr)
        L.append("---|---|---|---")
        for P in sorted({x["P"] for x in g}):
            row = []
            for R in (20, 30, 40):
                c = [x for x in g if x["thr"] == thr and x["P"] == P and x["R"] == R][0]
                row.append("%s / %.1f . %s%s%s . %d" % ("%+.1f" % (100 * c["T_total"]), 100 * c["T_maxdd"], "D" if c["c1"] else "x", "D" if c["c2"] else "x", "D" if c["c3"] else "x", c["switches"]))
            L.append("P=%d | %s" % (P, " | ".join(row)))
        L.append("")
    w, f = r["warm_start"], r["fee_hi"]
    L.append("Phu (khong tham gia verdict) - warm-start lien tuc tu dau du lieu (%s; %d lan doi truoc t0; t0 trang thai %s): T %s / DD %s / %d doi / %d ngay OFF ; C1/C2/C3 = %s/%s/%s" % (
        r["first"], w["switches_before_t0"], w["state_at_t0"], pct(w["T"]["total"]), pct(w["T"]["maxdd"]), w["switches"], w["off_days"],
        "D" if w["c1"] else "x", "D" if w["c2"] else "x", "D" if w["c3"] else "x"))
    L.append("")
    L.append("Phu (mo ta) - do nhay phi 0,30 %%/chieu (ca T va B&H): T %s / CAGR %s / DD %s ; B&H %s / DD %s ; C1/C2/C3 = %s/%s/%s ; luoi %d/27 o dat C1&C2" % (
        pct(f["T"]["total"]), pct(f["T"]["cagr"]), pct(f["T"]["maxdd"]), pct(f["BH"]["total"]), pct(f["BH"]["maxdd"]),
        "D" if f["c1"] else "x", "D" if f["c2"] else "x", "D" if f["c3"] else "x", f["n_c1c2_cells"]))
    L.append("")
    return "\n".join(L)


# ------------------------------------------------------------------------------------------------ chinh
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", required=True, choices=["selftest", "run"])
    ap.add_argument("--toos-dir", required=True)
    ap.add_argument("--data-dir")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout)
    T = load_toos(a.toos_dir)
    os.makedirs(a.out, exist_ok=True)
    v1, v1_run = v1_check(T, a.toos_dir, os.path.join(a.toos_dir, "btcusdt_1d_clean.csv"), os.path.join(a.toos_dir, "t_oos_res.json"))
    result = dict(cost_per_side=T.COST, v1=v1, toos_sha256=TOOS_SHA)
    if a.mode == "selftest":
        open(os.path.join(a.out, "selftest_tab.md"), "w").write(md_period(v1_run))
        json.dump(result, open(os.path.join(a.out, "selftest_res.json"), "w"), indent=1, default=str)
        log.info("SELFTEST_DONE")
        return
    periods, md, flags = [], [], {}
    for cfg in PERIODS:
        path = os.path.join(a.data_dir, cfg["file"])
        dates, dc = load_clean2(path)
        r = run_period(T, cfg["name"], dc, dates, cfg["t0"], cfg["end"], cfg["cuts"], cfg["asset"])
        r["data_sha256"] = sha_file(path)
        r["main"] = cfg["main"]
        periods.append(r)
        md.append(md_period(r))
        flags[cfg["name"]] = r["pass"]
        assert not any(str(d).startswith("2020") for d in dates), "V2"
    result["periods"] = periods
    result["v2"] = dict(ok=True, note="load_clean2: khong co ngay nam 2020 trong bat ky file nao; BTC Bitstamp max < 2017-08-01 + xcheck < 2018-01-01; ETH thang 2017-08..2019-12 va 2021-01..2025-12")
    result["v3_ok"] = bool(all(x["truncate_ok"] and x["scramble_ok"] for r in periods for x in r["v3"]))
    A = flags["A_BTC_2014_2017"]
    result["verdict_A"] = "PASS: T khong bi bac bo lan 2 (BTC, doc lap)" if A else "FAIL: T bi bac bo tren BTC 2014-2017"
    b1, b2 = flags["B1_ETH_2018_2019"], flags["B2_ETH_2021_2025"]
    if b1 and b2:
        eth = "ETH: PASS ca 2 ky - T khong bi bac bo tren ETH (tong quat hoa, nhung B2 trung thoi gian voi DEV cua luat)"
    elif (not b1) and (not b2):
        eth = "ETH: FAIL ca 2 ky - T khong tong quat sang ETH"
    else:
        eth = "ETH: HON HOP (B1 %s, B2 %s) - khong ket luan tong quat" % ("PASS" if b1 else "FAIL", "PASS" if b2 else "FAIL")
    result["verdict_ETH"] = eth
    log.info("VERDICT A: %s | %s", result["verdict_A"], eth)
    open(os.path.join(a.out, "t_oos2_tab.md"), "w").write("\n".join(md))
    json.dump(result, open(os.path.join(a.out, "t_oos2_res.json"), "w"), indent=1, default=str)
    log.info("DONE v3_ok=%s", result["v3_ok"])


if __name__ == "__main__":
    main()
