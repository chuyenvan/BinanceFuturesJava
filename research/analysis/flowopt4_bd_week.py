#!/usr/bin/env python3
"""flowopt4_bd_week.py — do OFFLINE (0 sim) cho PREREG_FLOWOPT4.md.

Cau hoi: path BIG_DOWN / DCA_LEVEL1 (bypass gate) co fire trong TUAN GATE DONG cua G2 khong,
va net cua chung co >0 ngoai CI (block-72h) khong?
CHI doc artifact DA CO. KHONG sim/train/build, KHONG cham 2026/242/ONNX/LIVE. Output nho.
"""
import json
import os

import numpy as np
import pandas as pd

ROOT = "/home/ubuntu/kaggle_sim/out"
ART = {
    "G2": f"{ROOT}/de-p1/storage/printDone.csv",              # chinh, n 2517 (@base)
    "G2S": f"{ROOT}/gdv2-g2-stress/storage/printDone.csv",     # robustness (@stress n 2509)
    "G2B": f"{ROOT}/featv1-b0/storage/printDone.csv",          # robustness (n 2517)
}
OUT = "/home/ubuntu/src/BinanceFuturesJava/docs/result/flowopt4.json"
PATH_LEVELS = ("BIG_DOWN", "DCA_LEVEL1")
W0 = pd.Timestamp("2021-07-01")
WEND = pd.Timestamp("2025-12-31 23:59:59")
NB = int((WEND - W0).total_seconds() // (7 * 86400)) + 1
INFL2 = float(np.sqrt(2.0 * np.log(2.0)))   # 1.177410
BLK = 72 * 3600 * 1000                       # 72h in ms
NREP = 2000


def wkbin(ts, origin_days=0):
    o = W0 + pd.Timedelta(days=origin_days)
    return ((ts - o).dt.total_seconds() // (7 * 86400)).astype("int64")


def load(p):
    d = pd.read_csv(p)
    d.columns = [c.strip() for c in d.columns]
    d = d.loc[:, ~d.columns.str.startswith("Unnamed")]
    d["ts"] = pd.to_datetime(d["start"].astype(str).str.strip(), format="%Y%m%d %H:%M")
    d["ts_ms"] = d["ts"].astype("int64") // 10**6
    d["level"] = d["level"].astype(str)
    d["net_leg"] = d["pnl"].astype(float) / d["margin"].astype(float)
    d["pnl"] = d["pnl"].astype(float)
    return d


def ci_block(v, ts_ms, seed=20260919, nrep=NREP):
    """CI block-72h cua trung binh (resample BLOCK co hoan lai) + inflate k2."""
    v = np.asarray(v, float); b = (np.asarray(ts_ms, "int64") // BLK)
    ub = np.unique(b); ib = np.searchsorted(ub, b)
    s = np.bincount(ib, v, len(ub)); c = np.bincount(ib, None, len(ub))
    rng = np.random.default_rng(seed); k = len(ub)
    reps = np.empty(nrep)
    for r in range(nrep):
        p = rng.integers(0, k, k)
        reps[r] = s[p].sum() / c[p].sum()
    mu = float(v.mean()); lo, hi = np.percentile(reps, [2.5, 97.5])
    il, ih = mu - (mu - lo) * INFL2, mu + (hi - mu) * INFL2
    return dict(mean=mu, raw=[float(lo), float(hi)], k2=[float(il), float(ih)],
                out_k2=bool(il > 0 or ih < 0), n=int(len(v)), nblk=int(k))


def placebo(pool_net, m, seed=20260930, nrep=NREP):
    """Null: boc m leg ngau nhien tu toan bo n leg; p 2 phia cho mean."""
    rng = np.random.default_rng(seed); N = len(pool_net)
    reps = np.empty(nrep)
    for r in range(nrep):
        reps[r] = pool_net[rng.choice(N, m, replace=False)].mean()
    return reps


def measure(d, origin_days=0, tag="G2"):
    wb = wkbin(d["ts"], origin_days)
    d = d.assign(wb=wb)
    allw = set(range(NB))
    openP = set(d.loc[d["level"] == "PREDICT_SYMBOL_TRADE", "wb"])
    anyw = set(d["wb"])
    D1 = sorted(allw - openP); D2 = sorted(allw - anyw)
    ispath = d["level"].isin(PATH_LEVELS)
    inD1 = d["wb"].isin(D1); inD2 = d["wb"].isin(D2)
    P = d[ispath & inD1]                      # PATH trong tuan gate dong (D1)
    Po = d[ispath & ~inD1]                    # PATH trong tuan gate mo
    res = dict(tag=tag, n=int(len(d)), nB=int(NB),
               n_weeks_D1=len(D1), n_weeks_D2=len(D2),
               n_weeks_open_predict=len(openP), n_weeks_any=len(anyw),
               level_counts=d["level"].value_counts().to_dict(),
               m_leg_D1=int(len(P)), m_week_D1_covered=int(P["wb"].nunique()),
               share_weeks_D1_pct=round(100.0 * P["wb"].nunique() / max(1, len(D1)), 2),
               m_leg_D2=int(len(d[ispath & inD2])),
               by_level_D1=P["level"].value_counts().to_dict(),
               pnl_sum_D1=round(float(P["pnl"].sum()), 1),
               pnl_sum_all_path=round(float(d.loc[ispath, "pnl"].sum()), 1),
               m_leg_total_path=int(ispath.sum()),
               dn_pct_of_n=round(100.0 * len(P) / max(1, len(d)), 3))
    if len(P):
        res["B1_net_D1"] = ci_block(P["net_leg"].values, P["ts_ms"].values)
        res["raw_mean_D1"] = round(float(P["net_leg"].mean()), 5)
        res["med_D1"] = round(float(P["net_leg"].median()), 5)
        res["winrate_D1"] = round(100.0 * float((P["net_leg"] > 0).mean()), 1)
        if len(Po):
            res["B3_net_open"] = ci_block(Po["net_leg"].values, Po["ts_ms"].values)
            res["B3_raw_mean_open"] = round(float(Po["net_leg"].mean()), 5)
        reps = placebo(d["net_leg"].values, len(P))
        p = 2 * min((reps <= P["net_leg"].mean()).mean(), (reps >= P["net_leg"].mean()).mean())
        res["placebo_perm"] = dict(m=len(P), null_mean=round(float(reps.mean()), 5),
                                   null_p2_5=round(float(np.percentile(reps, 2.5)), 5),
                                   null_p97_5=round(float(np.percentile(reps, 97.5)), 5),
                                   p_two_sided=round(float(p), 4))
    res["A1_pass"] = bool(len(P) >= 100)
    res["B1_pass"] = bool(len(P) and P["net_leg"].mean() > 0)
    res["B2_pass"] = bool(len(P) and res.get("B1_net_D1", {}).get("out_k2")
                          and res["B1_net_D1"]["k2"][0] > 0)
    res["VERDICT"] = "GO" if (res["A1_pass"] and res["B1_pass"] and res["B2_pass"]) else "NO-GO/NULL"
    return res


def main():
    out = {"meta": dict(nb=int(NB), w0=str(W0.date()), wend=str(WEND.date()),
                        infl_k2=round(INFL2, 6), blk_h=72, nrep=NREP,
                        seed_ci=20260919, seed_perm=20260930, path=list(PATH_LEVELS),
                        net_def="pnl/margin (calTp da net fee+slippage+funding)")}
    d = load(ART["G2"])
    out["main"] = measure(d, 0, "G2")
    # robustness: artifact khac
    out["robust_artifact"] = {}
    for k in ("G2S", "G2B"):
        try:
            out["robust_artifact"][k] = measure(load(ART[k]), 0, k)
        except Exception as e:  # noqa: BLE001
            out["robust_artifact"][k] = {"error": str(e)}
    # robustness: dich goc tuan 1..3 ngay
    out["robust_origin"] = {}
    for off in (1, 2, 3):
        r = measure(d, off, f"origin+{off}d")
        out["robust_origin"][f"+{off}d"] = dict(m_leg_D1=r["m_leg_D1"],
                                                covered=r["m_week_D1_covered"],
                                                net=round(r.get("raw_mean_D1", float("nan")), 5),
                                                verdict=r["VERDICT"])
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print(json.dumps(out, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
