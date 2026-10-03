#!/usr/bin/env python3
"""REAUDIT FLAT3 2026-10-03 — "FLAT3 co that la cau hinh thoat tot nhat?" (0-sim, CHI DOC artifact Kaggle co san).

Cham lai MOI arm exit da chay tren CUNG nen entry G2 (jar sim-jar-gdv2 7368be46) bang 3 thuoc:
  (i)  dPnL ghep cap theo lenh (khop sym|start|level; size-neutral = dprofit x notional_REF; lenh lech +/- PnL chinh no)
       vs FLAT3 va vs G2-T0; CI block-72h theo gio vao, NREP 2000, seed 20260905 (rng moi cho moi contrast),
       inflate quanh diem uoc luong x sqrt(2 ln k), k = 11 contrast (so arm khac FLAT3).
  (ii) MTM NGAY (b+unP tu logs/sim.out) paired moving-block 10 ngay (cung chi so khoi moi arm), dCAGR/dmaxDD/dCalmar.
  (iii) theo nam (vao lenh) cho (i); ROI nam + maxDD nam tu MTM ngay.
  (iv) phan phoi ROI (profit %) toan bo + nhom armed (STOP_MARKET_DONE).
MTM PHUT (maxDD/UW) lay tu cache run_mtm da tinh o cac vong truoc (khong tinh lai).
KHONG sim, KHONG Kaggle, KHONG Java, KHONG cham 242/shadow. Post-hoc: KHONG dung de chon arm moi.
Usage: python3 reaudit_flat3.py [OUT_JSON]
"""
import hashlib
import json
import math
import os
import sys

import numpy as np
import pandas as pd

REPO = "/home/ubuntu/src/BinanceFuturesJava"
sys.path.insert(0, os.path.join(REPO, "research/analysis"))
import reset_rule_score as R  # noqa: E402  (load_daily: equity ngay = b + unP)

KOUT = "/home/ubuntu/kaggle_sim/out"
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(REPO, "docs/audit/REAUDIT_FLAT3_20261003.json")
ARMS = [  # (ten, tag, mo ta, vong)
    ("FLAT3", "trail2-g2-flat3", "arm7 gap phang 3pp (ratio1.0 cap .03/.03) = B0", "TRAIL2"),
    ("T0", "trail2-g2-t0", "arm7 min(0.5p, 8%|3% theo pNoPump) = G2", "TRAIL/TRAIL2"),
    ("A5", "trail-g2-a5", "arm5 + gap T0", "TRAIL"),
    ("GV3", "trail-g2-gv3", "arm7 min(0.3p, 8%|3%)", "TRAIL"),
    ("LAD", "trail-g2-lad", "arm7 ladder .02/.04/.08 @5/10/20%", "TRAIL"),
    ("A5LAD", "trail-g2-a5lad", "arm5 + ladder", "TRAIL"),
    ("PROP50", "trail2-g2-prop50", "arm7 gap 0.5p khong tran", "TRAIL2"),
    ("PROP30", "trail2-g2-prop30", "arm7 gap 0.3p khong tran", "TRAIL2"),
    ("FLAT5", "trail2-g2-flat5", "arm7 gap phang 5pp", "TRAIL2"),
    ("HTD1", "htd-h1", "FLAT3 + BO time-stop 168h", "HOLDTODIE"),
    ("ET_A1", "exit-time-a1", "FLAT3 + time-stop 72h", "EXIT_TIME_B0"),
    ("ET_A2", "exit-time-a2", "FLAT3 + cond-exit 72h x MFE<5%", "EXIT_TIME_B0"),
]
REFS = ["FLAT3", "T0"]
NREP, SEED, BLK_H, BLK_D = 2000, 20260905, 72, 10
K = len(ARMS) - 1
INFL = math.sqrt(2 * math.log(K))
CAP0 = 35000.0
YEARS = [2021, 2022, 2023, 2024, 2025]
MTM_CACHES = ["/tmp/trail2_g2_mtm.json", "/tmp/trail_g2_mtm.json", "/tmp/holdtodie_mtm.json"]


def md5(tag):
    h = hashlib.md5()
    with open(os.path.join(KOUT, tag, "storage/printDone.csv"), "rb") as f:
        h.update(f.read())
    return h.hexdigest()


def legs(tag):
    d = pd.read_csv(os.path.join(KOUT, tag, "storage/printDone.csv"))
    d["t0"] = pd.to_datetime(d.start, format="%Y%m%d %H:%M")
    d["notional"] = d.quantity * d.entry
    d["key"] = d.sym + "|" + d.start + "|" + d.level
    return d


def mtm_minute():
    out = {}
    for f in MTM_CACHES:
        if os.path.exists(f):
            for t, v in json.load(open(f)).items():
                out[t] = v["legacy"]
    et = json.load(open(os.path.join(REPO, "docs/result/exit_time_b0.json")))["metrics"]
    for k, t in (("A1", "exit-time-a1"), ("A2", "exit-time-a2")):
        m = et[k]
        out[t] = dict(dd_total=m["dd_mtm"], uw_total_days=m["uw_mtm"], dd_year=None, src="exit_time_b0.json")
    return out


def ci_infl(d, lo, hi):
    return [float(d - (d - lo) * INFL), float(d + (hi - d) * INFL)]


def paired(ref, arm):
    """dPnL = arm - ref, size-neutral theo notional REF (lenh khop); lenh lech +/- PnL rieng (profit x notional chinh no)."""
    b = ref.drop_duplicates("key").set_index("key")
    x = arm.drop_duplicates("key").set_index("key")
    cm = b.index.intersection(x.index)
    ob, oa = b.index.difference(x.index), x.index.difference(b.index)
    dm = (x.loc[cm, "profit"] - b.loc[cm, "profit"]) / 100 * b.loc[cm, "notional"]
    db = -(b.loc[ob, "profit"] / 100 * b.loc[ob, "notional"])
    da = x.loc[oa, "profit"] / 100 * x.loc[oa, "notional"]
    t = pd.concat([pd.DataFrame({"t0": b.loc[cm, "t0"], "v": dm.values, "m": 1}),
                   pd.DataFrame({"t0": b.loc[ob, "t0"], "v": db.values, "m": 0}),
                   pd.DataFrame({"t0": x.loc[oa, "t0"], "v": da.values, "m": 0})])
    t["blk"] = ((t.t0 - pd.Timestamp("2021-07-01")).dt.total_seconds() // (BLK_H * 3600)).astype(int)
    g_all = t.groupby("blk").v.sum()
    g_m = t[t.m == 1].groupby("blk").v.sum().reindex(g_all.index, fill_value=0.0)
    rng = np.random.default_rng(SEED)
    idx = rng.integers(0, len(g_all), (NREP, len(g_all)))
    bs_all = g_all.values[idx].sum(1)
    bs_m = g_m.values[idx].sum(1)
    d, dmt = float(t.v.sum()), float(dm.sum())
    lo, hi = np.percentile(bs_all, [2.5, 97.5])
    lom, him = np.percentile(bs_m, [2.5, 97.5])
    yr = t.assign(y=t.t0.dt.year).groupby("y").v.sum()
    yrm = t[t.m == 1].assign(y=lambda z: z.t0.dt.year).groupby("y").v.sum()
    chg = float((dm.abs() > 1e-6).mean()) if len(dm) else 0.0
    return dict(n_common=int(len(cm)), n_only_ref=int(len(ob)), n_only_arm=int(len(oa)), frac_matched_changed=chg,
                d=d, ci_raw=[float(lo), float(hi)], ci_infl=ci_infl(d, lo, hi), halfwidth=float((hi - lo) / 2),
                d_matched=dmt, ci_matched_raw=[float(lom), float(him)], ci_matched_infl=ci_infl(dmt, lom, him),
                d_unmatched=float(db.sum() + da.sum()),
                year={int(k): float(v) for k, v in yr.items()},
                year_matched={int(k): float(v) for k, v in yrm.items()})


def daily_series(tag):
    e = R.load_daily(tag)["equity"].astype(float)
    return e[e.index <= pd.Timestamp("2025-12-31")]


def met(r, years):
    eq = np.concatenate(([1.0], np.cumprod(1.0 + r)))
    mdd = float((eq / np.maximum.accumulate(eq) - 1.0).min() * 100.0)
    cagr = (eq[-1] ** (1.0 / years) - 1.0) * 100.0
    return cagr, mdd, (cagr / abs(mdd) if mdd < 0 else np.nan)


def daily_boot(eqs):
    idx = sorted(set().union(*[set(v.index) for v in eqs.values()]))
    idx = pd.DatetimeIndex(idx)
    Rr = {}
    for k, v in eqs.items():
        a = v.reindex(idx).ffill().bfill().values
        Rr[k] = a[1:] / a[:-1] - 1.0
    T = len(idx) - 1
    years = (idx[-1] - idx[0]).days / 365.25
    obs = {k: met(r, years) for k, r in Rr.items()}
    nb = int(math.ceil(T / BLK_D))
    rng = np.random.default_rng(SEED)
    bs = {k: np.empty((NREP, 3)) for k in Rr}
    for i in range(NREP):
        st = rng.integers(0, T - BLK_D + 1, size=nb)
        pick = (st[:, None] + np.arange(BLK_D)[None, :]).ravel()[:T]
        for k, r in Rr.items():
            bs[k][i] = met(r[pick], years)
    return obs, bs


def year_stats(e):
    out = {}
    prev = CAP0
    for y in YEARS:
        s = e[e.index.year == y]
        if s.empty:
            continue
        roi = (s.iloc[-1] / prev - 1) * 100
        pk = np.maximum.accumulate(np.concatenate(([prev], s.values)))
        dd = float(((np.concatenate(([prev], s.values)) / pk) - 1).min() * 100)
        out[y] = dict(roi=float(roi), maxdd_daily=dd)
        prev = s.iloc[-1]
    return out


def roi_dist(d):
    p = d.profit.values
    a = d[d.status == "STOP_MARKET_DONE"].profit.values
    q = [10, 25, 50, 75, 90, 95, 99]
    bk = [(-1e9, 0), (0, 4), (4, 6), (6, 8), (8, 12), (12, 25), (25, 1e9)]
    tot = d.pnl.sum()
    return dict(q_all={str(x): float(np.percentile(p, x)) for x in q},
                q_armed={str(x): float(np.percentile(a, x)) for x in q} if len(a) else None,
                buckets={"%s..%s" % (lo, hi): [int(((p >= lo) & (p < hi)).sum()),
                                              float(d.pnl[(p >= lo) & (p < hi)].sum()),
                                              float(d.pnl[(p >= lo) & (p < hi)].sum() / tot * 100)] for lo, hi in bk})


def main():
    mm = mtm_minute()
    L, E, M = {}, {}, {}
    for name, tag, desc, rnd in ARMS:
        d = legs(tag)
        L[name] = d
        E[name] = daily_series(tag)
        e = E[name]
        days = (e.index[-1] - pd.Timestamp("2021-07-01")).days
        eq_end = float(e.iloc[-1])
        cagr = ((eq_end / CAP0) ** (365.25 / days) - 1) * 100
        hold = d.time_order
        ts = d[(d.status == "STOP_LOSS_DONE") & (hold >= 167)]
        mi = mm.get(tag, {})
        ddm = mi.get("dd_total")
        M[name] = dict(tag=tag, desc=desc, round=rnd, md5=md5(tag), n=int(len(d)), sum_pnl=float(d.pnl.sum()),
                       equity_daily_end=eq_end, cagr=float(cagr), dd_mtm_min=ddm, uw_mtm_min=mi.get("uw_total_days"),
                       calmar_mtm_min=(float(cagr / abs(ddm)) if ddm else None),
                       sl_pct=float((d.status == "STOP_LOSS_DONE").mean() * 100),
                       n_armed=int((d.status == "STOP_MARKET_DONE").sum()),
                       pnl_armed=float(d.pnl[d.status == "STOP_MARKET_DONE"].sum()),
                       n_timestop=int(len(ts)), pnl_timestop=float(ts.pnl.sum()),
                       n_sl_other=int(((d.status == "STOP_LOSS_DONE") & (hold < 167)).sum()),
                       win=float((d.profit > 0).mean() * 100), year=year_stats(e), roi=roi_dist(d))
    obs, bs = daily_boot(E)
    for k in M:
        M[k].update(cagr_daily=float(obs[k][0]), mdd_daily=float(obs[k][1]), calmar_daily=float(obs[k][2]))
    C = {}
    for ref in REFS:
        for name, *_ in ARMS:
            if name == ref:
                continue
            p = paired(L[ref], L[name])
            dm = {}
            for j, q in enumerate(("cagr", "mdd", "calmar")):
                o = obs[name][j] - obs[ref][j]
                a = bs[name][:, j] - bs[ref][:, j]
                a = a[np.isfinite(a)]
                lo, hi = np.percentile(a, [2.5, 97.5])
                dm[q] = dict(d=float(o), ci_raw=[float(lo), float(hi)], ci_infl=ci_infl(o, lo, hi),
                             p_gt0=float((a > 0).mean()))
            yrd = {y: (M[name]["year"].get(y, {}).get("roi", np.nan) - M[ref]["year"].get(y, {}).get("roi", np.nan))
                   for y in YEARS}
            p["mtm_daily"] = dm
            p["year_roi_diff"] = {int(y): float(v) for y, v in yrd.items()}
            p["all_years_paired_pos_2022_25"] = all(p["year"].get(y, 0) > 0 for y in (2022, 2023, 2024, 2025))
            p["all_years_roi_ge_2022_25"] = all(yrd[y] >= 0 for y in (2022, 2023, 2024, 2025))
            C["%s-%s" % (name, ref)] = p
    res = dict(k=K, inflate=INFL, nrep=NREP, seed=SEED, block_h=BLK_H, block_d=BLK_D, cap0=CAP0,
               note="post-hoc, 0-sim; khong dung de chon arm", arms=M, contrasts=C)
    json.dump(res, open(OUT, "w"), indent=1, default=float)
    f = lambda v, n=2: ("%.*f" % (n, v)) if isinstance(v, (int, float)) and v == v else "-"  # noqa: E731
    print("ARM | md5 | n | SumPnL | eqEnd | CAGR | ddMTMmin | UW | CalMTMmin | CAGRd | mddD | CalD | SL% | nTS/PnLTS | armed n/PnL")
    for k, m in M.items():
        print(k, m["md5"][:8], m["n"], f(m["sum_pnl"], 0), f(m["equity_daily_end"], 0), f(m["cagr"]),
              f(m["dd_mtm_min"]), f(m["uw_mtm_min"], 0), f(m["calmar_mtm_min"], 3), f(m["cagr_daily"]),
              f(m["mdd_daily"]), f(m["calmar_daily"], 3), f(m["sl_pct"]), "%d/%s" % (m["n_timestop"], f(m["pnl_timestop"], 0)),
              "%d/%s" % (m["n_armed"], f(m["pnl_armed"], 0)), sep=" | ")
    print("\nYEAR ROI% (MTM ngay)")
    for k, m in M.items():
        print(k, " ".join("%d:%s/%s" % (y, f(m["year"][y]["roi"], 1), f(m["year"][y]["maxdd_daily"], 1)) for y in YEARS))
    print("\nCONTRAST | dPnL | CIraw | CIinfl | matched d [CIinfl] | unmatched | yr21..25 | dCAGRd [infl] | dMDDd [infl] | dCalD [infl] p>0 | allYrPaired+ | allYrROI>=")
    for c, p in C.items():
        dm = p["mtm_daily"]
        print(c, f(p["d"], 0), "[%s;%s]" % (f(p["ci_raw"][0], 0), f(p["ci_raw"][1], 0)),
              "[%s;%s]" % (f(p["ci_infl"][0], 0), f(p["ci_infl"][1], 0)),
              "%s [%s;%s]" % (f(p["d_matched"], 0), f(p["ci_matched_infl"][0], 0), f(p["ci_matched_infl"][1], 0)),
              f(p["d_unmatched"], 0), "/".join(f(p["year"].get(y, 0), 0) for y in YEARS),
              "%s [%s;%s]" % (f(dm["cagr"]["d"]), f(dm["cagr"]["ci_infl"][0]), f(dm["cagr"]["ci_infl"][1])),
              "%s [%s;%s]" % (f(dm["mdd"]["d"]), f(dm["mdd"]["ci_infl"][0]), f(dm["mdd"]["ci_infl"][1])),
              "%s [%s;%s] %s" % (f(dm["calmar"]["d"], 3), f(dm["calmar"]["ci_infl"][0], 2), f(dm["calmar"]["ci_infl"][1], 2),
                                f(dm["calmar"]["p_gt0"], 2)),
              p["all_years_paired_pos_2022_25"], p["all_years_roi_ge_2022_25"], sep=" | ")
    print("\nROI armed q10/25/50/75/90/95/99 | bucket share PnL% (<0,0-4,4-6,6-8,8-12,12-25,25+)")
    for k, m in M.items():
        qa = m["roi"]["q_armed"]
        print(k, "/".join(f(qa[x], 1) for x in ("10", "25", "50", "75", "90", "95", "99")),
              "|", " ".join(f(v[2], 1) for v in m["roi"]["buckets"].values()))
    print("WROTE", OUT, "k", K, "infl", round(INFL, 4))


if __name__ == "__main__":
    main()
