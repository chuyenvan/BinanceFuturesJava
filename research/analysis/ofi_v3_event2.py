#!/usr/bin/env python3
"""ofi_v3_event2.py — do OFFLINE (0 sim) cho PREREG_OFI_V3_EVENT2.md.

Cau hoi: OFI V3 co sinh su kien/entry MOI trong TUAN GATE DONG cua G2 khong, va net co >0 ngoai CI
(so random) khong?  Chi doc artifact DA CO. KHONG sim/train, KHONG cham 2026/242/ONNX/LIVE.

Nguon:
  G2       : /home/ubuntu/kaggle_sim/out/gdv2-g2-stress/storage/printDone.csv
  luoi OFI : index /home/ubuntu/ofi_v3/ms/outALL/ms_diffs_s42.parquet
  P32+nhan : /home/ubuntu/mr_kaggle/ds_mr_labels/label_b_pnl.parquet
  NEW pairs: /home/ubuntu/ofi_v3/ofimoney/label_b_pnl_ext_reorient.parquet
"""
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, "/home/ubuntu/sel1m_code")
import model_ruler as MR  # noqa: E402
import c3_rates as C      # noqa: E402

G2 = "/home/ubuntu/kaggle_sim/out/gdv2-g2-stress/storage/printDone.csv"
G2B = "/home/ubuntu/kaggle_sim/out/featv1-b0/storage/printDone.csv"
MSD = "/home/ubuntu/ofi_v3/ms/outALL/ms_diffs_s42.parquet"
P32 = "/home/ubuntu/mr_kaggle/ds_mr_labels/label_b_pnl.parquet"
NEW = "/home/ubuntu/ofi_v3/ofimoney/label_b_pnl_ext_reorient.parquet"

W0 = pd.Timestamp("2021-07-01")
W1 = pd.Timestamp("2025-12-31 23:59:59")
EDGES = np.arange(W0.value, W1.value + 1, 7 * 86400 * 10**9)
NB = len(EDGES) - 1
F = 0.006
K = 8
SEED = 20260930
RNG = np.random.default_rng(SEED)
INFL2 = float(np.sqrt(2.0 * np.log(2.0)))  # 1.177410


def wkbin(ns):
    """ns = thoi gian NANOSECOND (moi cho quy ve ns truoc khi goi)."""
    i = np.searchsorted(EDGES, np.asarray(ns, dtype="int64"), side="right") - 1
    return i


def g2_times(p):
    d = pd.read_csv(p)
    return pd.to_datetime(d["start"].astype(str).str.strip(), format="%Y%m%d %H:%M")


def ci(v, ts, paired=True):
    r = MR.ci_mean(np.asarray(v, np.float64), np.asarray(ts, np.int64), inflate=INFL2)
    lo, hi = r["raw"]
    il, ih = r["honest_infl"]
    return dict(mean=float(r["mean"]), raw=[float(lo), float(hi)], k2=[float(il), float(ih)],
                out_k2=bool((il > 0) or (ih < 0)), n=int(r["n"]))


def ci_two(A, tsA, B, tsB):
    """CI hieu 2 trung binh (KHONG ghep cap) bang block-72h bootstrap hai mau."""
    blk = 72 * 3600 * 1000
    rng = np.random.default_rng(20260919)
    bA = (np.asarray(tsA, "int64") // blk)
    bB = (np.asarray(tsB, "int64") // blk)
    uA = np.unique(bA); uB = np.unique(bB)
    iA = np.searchsorted(uA, bA); iB = np.searchsorted(uB, bB)
    A = np.asarray(A, float); B = np.asarray(B, float)
    sA = np.bincount(iA, A, len(uA)); cA = np.bincount(iA, None, len(uA))
    sB = np.bincount(iB, B, len(uB)); cB = np.bincount(iB, None, len(uB))
    reps = np.empty(2000)
    for r in range(2000):
        pA = rng.integers(0, len(uA), len(uA)); pB = rng.integers(0, len(uB), len(uB))
        mA = sA[pA].sum() / cA[pA].sum(); mB = sB[pB].sum() / cB[pB].sum()
        reps[r] = mA - mB
    mu = float(A.mean() - B.mean())
    lo, hi = float(np.percentile(reps, 2.5)), float(np.percentile(reps, 97.5))
    il, ih = mu - (mu - lo) * INFL2, mu + (hi - mu) * INFL2
    return dict(mean=mu, raw=[lo, hi], k2=[il, ih], out_k2=bool((il > 0) or (ih < 0)),
                nA=int(len(A)), nB=int(len(B)), nblkA=int(len(uA)), nblkB=int(len(uB)))


def gr1dv(sel, ticks_all):
    """net_gr1dv = SUM(gross-f)/SUM_t e_t ; e_t = so leg dang mo tai t (ts->exit_ts)."""
    ts = sel["ts"].values.astype("int64")
    ex = sel["exit_ts"].values.astype("int64")
    net = sel["gross"].values - F
    num = net.sum()
    order = np.argsort(ts)
    grid = np.sort(np.asarray(ticks_all, "int64"))
    idx = np.searchsorted(grid, ts[order], side="right")
    end = np.searchsorted(grid, ex[order], side="right")
    diff = np.zeros(len(grid) + 1)
    for a, b in zip(idx, end):
        diff[a] += 1; diff[b] -= 1
    e = np.cumsum(diff[:-1])
    return float(num / e.sum()), int(e.sum())


def main():
    out = {}
    # ---------- A: tuan gate dong ----------
    g2 = g2_times(G2)
    wg2 = set(wkbin(g2.astype("int64").values))
    g2b = g2_times(G2B)
    wg2b = set(wkbin(g2b.astype("int64").values))
    allw = set(range(NB))
    closed = sorted(allw - wg2)
    best = cur = 0
    for w in range(NB):
        cur = 0 if w in wg2 else cur + 1
        best = max(best, cur)
    gaps = g2.sort_values().diff().dropna().dt.total_seconds() / 86400.0
    out["G2_weeks"] = dict(n_weeks=NB, n_open=len(wg2), n_closed=len(closed),
                           max_run_closed_weeks=best, cov_open_pct=round(100 * len(wg2) / NB, 1),
                           max_gap_days=round(float(gaps.max()), 2), n_trades=int(len(g2)),
                           n_days_with_trades=int(len(g2.dt.date.unique())),
                           defn_robust_same_as_GBASE=bool(wg2 == wg2b))

    # ---------- luoi tick ----------
    ms = np.asarray(pd.read_parquet(MSD).index.values, "int64")   # ms (giu nguyen cho CI)
    pool = pd.read_parquet(P32)
    pool["ts"] = pool["ts"].astype("int64")           # ms — giu cho CI/gr1dv
    pool["exit_ts"] = pool["exit_ts"].astype("int64")  # ms
    p32t = np.sort(pool["ts"].unique().astype("int64"))
    wms = set(wkbin((ms * 10**6)).tolist())
    wp32 = set(wkbin((p32t * 10**6)).tolist())
    out["grids"] = dict(n_ticks_ofl= int(len(ms)), n_ticks_pool=int(len(p32t)),
                        pool_subset_of_ofl_pct=round(100 * float(np.isin(p32t, ms).mean()), 3),
                        n_weeks_ofl=len(wms), n_weeks_pool=len(wp32))
    # A1/A2
    cl_ms = [w for w in closed if w in wms]
    cl_p32 = [w for w in closed if w in wp32]
    out["A1_closed_weeks_with_ofl_tick"] = dict(n=len(cl_ms), of_closed=len(closed),
                                               pct=round(100 * len(cl_ms) / len(closed), 1),
                                               dat=(len(cl_ms) / len(closed) >= 0.25))
    out["A2_closed_weeks_with_pool_tick"] = dict(n=len(cl_p32), dat=(len(cl_p32) >= 20))

    # ---------- B: chat luong leg trong tuan dong (arm S1-8 vs random-8) ----------
    pool = pool.copy()
    pool["wb"] = wkbin(pool["ts"].values * 10**6)
    pool["closed"] = pool["wb"].isin(closed)
    pool["gross"] = pool["gross"].astype(float)
    arms = {}
    res = {}
    for name, mask in [("closed", pool["closed"]), ("open", ~pool["closed"])]:
        sub = pool[mask]
        # per-tick selection: S1-8 = rank<8 ; random-8
        selA, selB = [], []
        for t, g in sub.groupby("ts", sort=True):
            a = g[g["rank"] < K]
            b = g.iloc[RNG.choice(len(g), size=min(K, len(g)), replace=False)]
            selA.append(a); selB.append(b)
        A = pd.concat(selA); B = pd.concat(selB)
        ticks = np.sort(sub["ts"].unique().astype("int64"))
        nA = A["gross"].values - F
        nB = B["gross"].values - F
        d = None
        # ghep cap theo tick
        ga = A.groupby("ts")["gross"].mean() - F
        gb = B.groupby("ts")["gross"].mean() - F
        common = ga.index.intersection(gb.index)
        dd = (ga.loc[common] - gb.loc[common]).values
        d = ci(dd, common.values.astype("int64"))
        g1, e1 = gr1dv(A, ticks)
        g2_, e2 = gr1dv(B, ticks)
        res[name] = dict(n_tick=int(sub["ts"].nunique()), n_leg_arm=int(len(A)),
                         net_coin_S1_8=ci(nA, A["ts"].values.astype("int64")),
                         net_coin_rand8=ci(nB, B["ts"].values.astype("int64")),
                         net_gr1dv_S1_8=g1, net_gr1dv_rand8=g2_,
                         delta_S1_8_minus_rand8=d,
                         gross_pool_mean=float(sub["gross"].mean()))
        arms[name] = (A, B)
    out["B_by_week_type"] = res
    # B3: dong - mo (khong ghep cap)
    Ad, Bd = arms["closed"][0], arms["closed"][1]
    Ao, Bo = arms["open"][0], arms["open"][1]
    out["B3_S1_8_closed_minus_open"] = ci_two(Ad["gross"].values - F, Ad["ts"].values,
                                              Ao["gross"].values - F, Ao["ts"].values)
    out["B3_rand8_closed_minus_open"] = ci_two(Bd["gross"].values - F, Bd["ts"].values,
                                              Bo["gross"].values - F, Bo["ts"].values)

    # ---------- C1: 293 entry THEM THAT (ngoai P32) ----------
    nw = pd.read_parquet(NEW)
    nw["ts"] = nw["ts"].astype("int64")
    nw["wb"] = wkbin(nw["ts"].values * 10**6)
    nwc = nw["wb"].isin(closed)
    c1 = dict(n=int(len(nw)), n_sym=int(nw["sym"].nunique()), n_tick=int(nw["ts"].nunique()),
              n_in_closed_week=int(nwc.sum()), n_in_open_week=int((~nwc).sum()),
              gross_mean_all=float(nw["gross"].mean()),
              gross_mean_closed=float(nw.loc[nwc, "gross"].mean()) if nwc.any() else None,
              net_coin_all=ci(nw["gross"].values - F, nw["ts"].values.astype("int64")))
    if nwc.any():
        c1["net_coin_closed"] = ci(nw.loc[nwc, "gross"].values - F, nw.loc[nwc, "ts"].values.astype("int64"))
        # doi chung: tai CUNG tick do, bốc 1 coin ngau nhien trong P32
        rc = RNG.integers(0, 32, size=int(nwc.sum()))
        p2 = pool[nwc.values & pool["closed"].values] if False else None
        rmap = pool.groupby("ts")["gross"].apply(list)
        rg = []
        for i, t in enumerate(nw.loc[nwc, "ts"].values):
            lst = rmap.get(t)
            rg.append(lst[rc[i] % len(lst)] if lst else np.nan) if lst else rg.append(np.nan)
        rg = np.asarray(rg, float)
        ok = np.isfinite(rg)
        c1["rand_pool_same_tick"] = ci(rg[ok] - F, nw.loc[nwc, "ts"].values[ok])
        c1["delta_closed_new_minus_rand_pool"] = ci(
            (nw.loc[nwc, "gross"].values[ok] - F) - (rg[ok] - F),
            nw.loc[nwc, "ts"].values[ok].astype("int64"))
    out["C1_new_entries"] = c1

    # ---------- C2: doc lap cau truc ----------
    try:
        s0 = json.load(open("/home/ubuntu/claude_audit_0928/ofirx/step0_orient.json"))
        sp = {k: v.get("spearman_tick_mean(score,rank)") for k, v in s0.items()}
    except Exception as e:
        sp = {"err": str(e)}
    try:
        m = json.load(open("docs/result/ofi_money_reorient.json"))
        b1 = m["B1_topk_outside_p32"]["candidate"]["K8"]["pct_outside"]
    except Exception as e:
        b1 = None
        sp["err2"] = str(e)
    out["C2_structural"] = dict(spearman_ofi_vs_S1_rank=sp,
                                pct_top8_ofi_outside_p32=b1,
                                independent_if_ge_10pct=bool(b1 is not None and b1 >= 10.0))

    # ---------- verdict ----------
    B2 = res["closed"]["delta_S1_8_minus_rand8"]
    b1ok = res["closed"]["net_coin_S1_8"]["mean"] > 0
    B2ok = bool(B2["out_k2"] and B2["mean"] > 0)
    C1ok = bool(c1["net_coin_all"]["out_k2"] and c1["net_coin_all"]["mean"] > 0)
    C2ok = out["C2_structural"]["independent_if_ge_10pct"]
    out["VERDICT"] = dict(B1_level_positive=b1ok, B2_out_ci_positive_vs_random=B2ok,
                          C1_new_entries_out_ci_positive=C1ok, C2_independent=C2ok,
                          GO=bool(B2ok and C1ok and C2ok), noise_control="MISSING_OFFLINE")
    out["_meta"] = dict(prereg="docs/prereg/PREREG_OFI_V3_EVENT2.md", fee=F, K=K, seed_random=SEED,
                        block_h=72, nrep=2000, seed_boot=20260919, inflate_k2=round(INFL2, 6))
    # ---------- ROBUSTNESS: dich goc bin 0..6 ngay ----------
    g2ns = g2.astype("int64").values
    rob = {}
    for ph in range(7):
        ed = EDGES + ph * 86400 * 10**9
        nb = len(ed) - 1
        wg = set((np.searchsorted(ed, g2ns, "right") - 1).tolist())
        allw2 = set(range(nb))
        cl = sorted(allw2 - wg)
        pv = pool[pool["wb"].isin(cl)] if False else None
        wbv = wkbin(pool["ts"].values * 10**6)
        if ph:
            wbv = np.searchsorted(ed, pool["ts"].values * 10**6, "right") - 1
        sub = pool[np.isin(wbv, cl)]
        if len(sub) == 0:
            continue
        ga = sub[sub["rank"] < K].groupby("ts")["gross"].mean() - F
        rb = []
        for t, g in sub.groupby("ts", sort=True):
            rb.append((t, g["gross"].values[RNG.choice(len(g), K, replace=False)].mean() - F))
        rb = pd.DataFrame(rb, columns=["ts", "v"]).set_index("ts")["v"]
        cm = ga.index.intersection(rb.index)
        d = ga.loc[cm] - rb.loc[cm]
        cid = ci(d.values, cm.values.astype("int64"))
        rob["ph%d" % ph] = dict(n_closed=len(cl), n_tick=int(sub["ts"].nunique()),
                                 net_coin_S1_8=round(float(ga.mean()), 6),
                                 net_coin_rand8=round(float(rb.mean()), 6),
                                 delta_mean=round(float(d.mean()), 6),
                                 delta_k2=[round(x, 6) for x in cid["k2"]],
                                 delta_out_k2=cid["out_k2"])
    out["ROBUST_bin_phase"] = rob

    os.makedirs("docs/result", exist_ok=True)
    with open("docs/result/ofi_v3_event2.json", "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(json.dumps({k: out[k] for k in ["G2_weeks", "grids", "A1_closed_weeks_with_ofl_tick",
                                          "A2_closed_weeks_with_pool_tick", "VERDICT",
                                          "C2_structural"]}, ensure_ascii=False, indent=1))
    print("B closed:", json.dumps({k: res["closed"][k] for k in ["n_tick", "net_coin_S1_8",
          "net_coin_rand8", "delta_S1_8_minus_rand8", "net_gr1dv_S1_8", "net_gr1dv_rand8"]}, ensure_ascii=False))
    print("B open  :", json.dumps({k: res["open"][k] for k in ["n_tick", "net_coin_S1_8",
          "net_coin_rand8", "delta_S1_8_minus_rand8"]}, ensure_ascii=False))
    print("C1:", json.dumps(c1, ensure_ascii=False)[:1200])


if __name__ == "__main__":
    main()
