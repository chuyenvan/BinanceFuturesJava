#!/usr/bin/env python3
"""R4_SIGNAL_SCREEN cham (prereg PREREG_R4_SIGNAL_SCREEN 5db738e2 §2 C3, §3 quota C3, §4 sang).
Input: screen/cells.parquet, screen/count.json, screen/out/r4s_fwd.parquet. Output: screen/r4_screen.json + docs/result/R4_SIGNAL_SCREEN.md."""
import json
import logging
import sys

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("r4score")
G = "/home/ubuntu/claude_master/res1109/r4_signal/screen/"
DOC = "/home/ubuntu/claude_master/vz_e1_wt/docs/result/R4_SIGNAL_SCREEN.md"
FEE, SEED, NB, TZ, D, H = 0.002, 20261111, 2000, 7 * 3600000, 86400000, 3600000
YB = {2022: 1640970000000, 2023: 1672506000000, 2024: 1704042000000, 2025: 1735664400000, 2026: 1767200400000}
YRS = (2022, 2023, 2024, 2025)
FEATS = ["f_rq", "f_u", "f_m60", "f_tsince", "f_n60", "f_rank", "f_lopen"]
QLO, QHI, TOL = 0.85, 1.15, 0.05
CI_LO, CI_HI = 1.65, 98.35          # hai phia 96,7 %


def c3_select(P):
    """WFO theo nam, LR mac dinh, giu prob >= tau(h) (phan vi 1/3 trong [h-90d, h), <50 o => phan vi 1/3 train)."""
    keep, info = [], {}
    for s, X in P.groupby("seed"):
        X = X.sort_values("ts").reset_index(drop=True)
        for y in YRS:
            tr = X[(X.ts < YB[y] - 3 * D) & X.ret72.notna()]
            med = tr[FEATS].median()
            sc = StandardScaler().fit(tr[FEATS].fillna(med))
            lr = LogisticRegression(C=1.0, max_iter=1000).fit(sc.transform(tr[FEATS].fillna(med)), (tr.ret72 > 0).astype(int))
            ptr = lr.predict_proba(sc.transform(tr[FEATS].fillna(med)))[:, 1]
            W = X[(X.ts >= YB[y] - 90 * D) & (X.ts < YB[y + 1])].copy()
            W["prob"] = lr.predict_proba(sc.transform(W[FEATS].fillna(med)))[:, 1]
            wt, wp = W.ts.to_numpy(), W.prob.to_numpy()
            ev = W[(W.ts >= YB[y])]
            h0 = (ev.ts.to_numpy() // H) * H
            lo = np.searchsorted(wt, h0 - 90 * D, "left")
            hi = np.searchsorted(wt, h0, "left")
            tau = np.array([np.quantile(wp[a:b], 1 / 3) if b - a >= 50 else np.quantile(ptr, 1 / 3) for a, b in zip(lo, hi)])
            kk = ev[ev.prob.to_numpy() >= tau]
            keep.append(kk)
            info.setdefault(s, {})[y] = dict(n_train=int(len(tr)), pos_rate=round(float((tr.ret72 > 0).mean()), 4),
                                             n_pool=int(len(ev)), n_keep=int(len(kk)),
                                             coef=dict(zip(FEATS, np.round(lr.coef_[0], 4).tolist())))
    K = pd.concat(keep, ignore_index=True)
    K["set"] = "C3"
    return K, info


def day_sums(df, days):
    g = df.groupby("day").ret.agg(["sum", "count"]).reindex(days).fillna(0.0)
    return g["sum"].to_numpy(), g["count"].to_numpy()


def main():
    A = pd.read_parquet(G + "cells.parquet")
    cnt = json.load(open(G + "count.json"))
    F = pd.read_parquet(G + "out/r4s_fwd.parquet")
    meta = dict(n_fwd=len(F), nan0=int(F.c0.isna().sum()), nan24=int(F.c24.isna().sum()), nan72=int(F.c72.isna().sum()))
    log.info("fwd %s", meta)
    A = A.merge(F[["ts", "sym", "c0", "c24", "c72"]], on=["ts", "sym"], how="left")
    assert A.c0.notna().mean() > 0.95, "thieu fwd"
    A["ret72"] = A.c72 / A.c0 - 1.0 - FEE
    A["ret24"] = A.c24 / A.c0 - 1.0 - FEE
    A["day"] = (A.ts.astype(np.int64) + TZ) // D
    b0 = A[A.set == "B0"]
    b0n = {s: {y: int(v) for y, v in zip(YRS, cnt["b0_by_seed"][s])} for s in cnt["b0_by_seed"]}
    T = cnt["T_B0"]
    arms = {}
    # C3
    P = A[A.set == "P3"]
    if not cnt["arms"]["P3"]["LOAI"]:
        K3, info3 = c3_select(P)
        n3 = K3.groupby(["seed", "year"]).size()
        qy = {y: float(np.median([n3.get((s, y), 0) / max(b0n[s][y], 1) for s in b0n])) for y in YRS}
        tot = int(len(K3))
        ent = dict(N=tot, ratio=round(tot / T, 4), quota_year_med=qy, iso_ok=bool(abs(tot / T - 1) <= TOL),
                   quota_ok=bool(all(QLO <= v <= QHI for v in qy.values())), wfo=info3)
        ent["LOAI"] = bool(not (ent["iso_ok"] and ent["quota_ok"]))
        arms["C3"] = (ent, K3)
    else:
        arms["C3"] = (dict(LOAI=True, why="pool P3 khong dat iso-count"), None)
    for a in ("C1", "C2"):
        e = dict(cnt["arms"][a])
        arms[a] = (e, A[A.set == a])
    # tap THEM / BOT
    sets = {}
    for a, (e, X) in arms.items():
        if e.get("LOAI"):
            continue
        key = ["seed", "ts", "sid"]
        mA = X[key + ["sym", "ret72", "ret24", "day", "year", "sat"]].merge(b0[key], on=key, how="left", indicator=True)
        add = mA[mA._merge == "left_only"].drop(columns="_merge")
        mB = b0.merge(X[key], on=key, how="left", indicator=True)
        rem = mB[mB._merge == "left_only"].drop(columns="_merge")
        sets[a] = (add, rem)
    days = np.unique(np.concatenate([np.r_[ad.day.to_numpy(), rm.day.to_numpy()] for ad, rm in sets.values()])) if sets else np.zeros(0)
    rng = np.random.default_rng(SEED)
    BS = [rng.choice(len(days), len(days), replace=True) for _ in range(NB)]
    res = dict(prereg="5db738e2", fee=FEE, rng_seed=SEED, n_boot=NB, ci="hai phia 96,7 % (1,65/98,35)", fwd_meta=meta, arms={})
    for a, (e, X) in arms.items():
        out = {k: v for k, v in e.items() if k != "wfo"}
        if a == "C3" and "wfo" in e:
            res["c3_wfo"] = e["wfo"]
        if a not in sets:
            out["QUA"] = False
            res["arms"][a] = out
            continue
        add, rem = sets[a]
        for Hh in ("72", "24"):
            ad = add[add["ret" + Hh].notna()].rename(columns={"ret" + Hh: "ret"})
            rm = rem[rem["ret" + Hh].notna()].rename(columns={"ret" + Hh: "ret"})
            sa, na = day_sums(ad, days)
            sr, nr = day_sums(rm, days)
            pt = sa.sum() / na.sum() - sr.sum() / nr.sum()
            bd = []
            for ix in BS:
                xa, xr = na[ix].sum(), nr[ix].sum()
                if xa > 0 and xr > 0:
                    bd.append(sa[ix].sum() / xa - sr[ix].sum() / xr)
            r = dict(n_add=int(len(ad)), n_rem=int(len(rm)), mean_add=round(float(sa.sum() / na.sum()), 5),
                     mean_rem=round(float(sr.sum() / nr.sum()), 5), diff=round(float(pt), 5),
                     ci967=[round(float(v), 5) for v in np.percentile(bd, [CI_LO, CI_HI])],
                     ci90=[round(float(v), 5) for v in np.percentile(bd, [5, 95])], n_boot_ok=len(bd))
            if Hh == "72":
                yd = {}
                for y in YRS:
                    a_, r_ = ad[ad.year == y], rm[rm.year == y]
                    yd[y] = round(float(a_.ret.mean() - r_.ret.mean()), 5) if len(a_) and len(r_) else None
                r["diff_year"] = yd
                a2, r2 = ad[~ad.sat], rm[~rm.sat]
                r["diff_exsat"] = round(float(a2.ret.mean() - r2.ret.mean()), 5)
                r["n_add_exsat"], r["n_rem_exsat"] = int(len(a2)), int(len(r2))
            out["H" + Hh] = r
        h = out["H72"]
        ny = sum(1 for v in h["diff_year"].values() if v is not None and v > 0)
        out["cond"] = dict(a_ci_lo_gt0=bool(h["ci967"][0] > 0), b_years_pos=ny, b_ok=bool(ny >= 3),
                           c_exsat_pos=bool(h["diff_exsat"] > 0), d_quota=True)
        out["QUA"] = bool(out["cond"]["a_ci_lo_gt0"] and out["cond"]["b_ok"] and out["cond"]["c_exsat_pos"])
        res["arms"][a] = out
        log.info("%s %s", a, json.dumps(out)[:1500])
    json.dump(res, open(G + "r4_screen.json", "w"), indent=1, default=str)
    L = ["# R4_SIGNAL_SCREEN — kết quả sàng (prereg 5db738e2) — tự sinh bởi research/r4_signal/r4_score.py", "",
         "fwd: %s. Bootstrap cụm ngày (+07) %d lần, seed %d, CI hai phía 96,7 %%. Raw `~/claude_master/res1109/r4_signal/screen/r4_screen.json`." % (meta, NB, SEED), "",
         "| arm | quota tổng | quota năm (median 22/23/24/25) | THÊM / BỚT | Δfwd72 (pp) [CI96,7] | năm dương | bỏ bão hoà | H24 Δ | KẾT |", "|---|---|---|---|---|---|---|---|---|"]
    for a in ("C1", "C2", "C3"):
        o = res["arms"][a]
        qy = o.get("quota_year_med", {})
        qs = "/".join("%.2f" % qy[k] for k in sorted(qy)) if qy else "-"
        if "H72" in o:
            h, h24 = o["H72"], o["H24"]
            L.append("| %s | %s | %s | %d / %d | %+.2f [%+.2f; %+.2f] | %d/4 | %+.2f | %+.2f | %s |" % (
                a, o.get("ratio"), qs, h["n_add"], h["n_rem"], 100 * h["diff"], 100 * h["ci967"][0], 100 * h["ci967"][1],
                o["cond"]["b_years_pos"], 100 * h["diff_exsat"], 100 * h24["diff"], "QUA" if o["QUA"] else "TRƯỢT"))
        else:
            L.append("| %s | %s | %s | - | - | - | - | - | LOẠI (iso/quota) |" % (a, o.get("ratio"), qs))
    open(DOC, "w").write("\n".join(L) + "\n")
    log.info("WROTE %s", DOC)


if __name__ == "__main__":
    main()
