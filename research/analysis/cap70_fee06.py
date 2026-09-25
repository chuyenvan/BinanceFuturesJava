#!/usr/bin/env python3
"""cap70_fee06.py — PREREG_CAP70_FEE06 (commit 6f37caa): tran gross 70% CUNG + phi chuan 0,6%/vong.

DUONG RE: pool P32 da la top-32 S1 moi tick => top-K = `rank < K` cat tu chinh pool.
KHONG chay lai exit engine, KHONG train, KHONG sim. Chi doc 1 parquet.

Chi so (chot truoc o PREREG §3):
  net_tick_K(f)  = mean_t SUM_{i in topK}(gross_i - f)              (net/tick)
  net_coin_K(f)  = mean_t MEAN_{i in topK}(gross_i - f)             (net/coin/vong)
  net_gr1dv_K(f) = SUM_i (gross_i - f) / SUM_t e_t                  (net tren 1 don vi gross exposure)
  e_t  = so VI THE dang mo tai t ; d_t = so COIN PHAN BIET dang mo tai t

AP TRAN 70% (khai bao DUNG 2 cach, bao CA BA he so):
  (A)   sA   = 70 / gross_TB(K)      voi gross_TB(K) = 100 * 0.02 * d_mean(K)
  (B95) sB95 = 70 / gross_p95(K)
  (Bmx) sBmx = 70 / gross_max(K)
net/tick SAU SIZE (%equity/tick) = 2 * s * net_tick_K(f)   [vi s0=0.02 => 100*0.02=2]

CI: khoi 72h, NREP=2000, SEED=20260905 (c3_rates); inflate(k=5)=1.7941 (nguyen MR.ci_mean).
Chay: python3 cap70_fee06.py --out docs/result/cap70_fee06.json
"""
import argparse
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..")))
import model_ruler as MR                        # noqa: E402
import c3_rates as C                            # noqa: E402

LABEL = "/home/ubuntu/mr_kaggle/ds_mr_labels/label_b_pnl.parquet"
SHA = "1d42b7f67466ca4ea9e8e74c4efe3c0a8664bde8a850a9f855209ef24927bb13"
KS = [8, 10, 12, 16, 32]
FEES = [0.0, 0.004, 0.006, 0.008]
S0 = 0.02                                        # 2,0 %equity/lenh (neo POST-HOC)
CAP = 70.0                                       # tran gross %equity (owner 26/09)
INFL5 = float(np.sqrt(2.0 * np.log(5.0)))        # 1,7941 — k = 5 muc K da thu
H = 3600000                                      # 1h (ms)


def mk(v, ts):
    ci = MR.ci_mean(np.asarray(v, np.float64), np.asarray(ts, np.int64), inflate=INFL5)
    mu = float(ci["mean"])
    raw = [float(x) for x in ci["raw"]]
    b5 = [float(x) for x in ci["honest_infl"]]
    return {"mean": round(mu, 8), "raw": [round(x, 8) for x in raw],
            "k5": [round(x, 8) for x in b5],
            "out_raw": bool(raw[0] > 0 or raw[1] < 0),
            "out5": bool(b5[0] > 0 or b5[1] < 0),
            "out_both": bool((raw[0] > 0 or raw[1] < 0) and (b5[0] > 0 or b5[1] < 0)),
            "dir": 1 if mu > 0 else -1, "n": int(ci["n"])}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", default=LABEL)
    ap.add_argument("--out", default="docs/result/cap70_fee06.json")
    a = ap.parse_args()
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)

    d = pd.read_parquet(a.label, columns=["ts", "symId", "rank", "gross", "exit_ts", "hold_min"])
    d = d.sort_values(["ts", "rank"], kind="stable").reset_index(drop=True)
    ticks = np.sort(d.ts.unique().astype(np.int64))
    nt = len(ticks)
    NS = int(d["rank"].max()) + 1
    assert len(d) == nt * NS, "pool khong vuong %d" % NS
    TS = d.ts.to_numpy(np.int64).reshape(nt, NS)
    G = d.gross.to_numpy(np.float64).reshape(nt, NS)
    assert (TS[:, 0][:, None] == TS).all()
    tsv = TS[:, 0]
    tsflat = d.ts.to_numpy(np.int64)
    exflat = d.exit_ts.to_numpy(np.int64)
    symflat = d.symId.to_numpy(np.int64)
    rankflat = d["rank"].to_numpy()
    holdflat = d["hold_min"].to_numpy(np.float64)
    pool_t = G.mean(1)

    # khoi 72h (giong stage2_score.block_boot_mean)
    inv = np.unique((tsv // (C.BLOCK_H * H)), return_inverse=True)[1]
    nb = int(inv.max()) + 1
    BI = np.random.default_rng(C.SEED).integers(0, nb, (C.NREP, nb))

    def counts(x):
        return np.bincount(inv, weights=x, minlength=nb)

    print("### pool %s: %d dong, %d tick x %d | gross_pool=%.6f | khoi=%d nrep=%d seed=%d "
          "| S0=%.3f CAP=%.1f infl5=%.4f" % (
              os.path.basename(a.label), len(d), nt, NS, pool_t.mean(), nb, C.NREP, C.SEED,
              S0, CAP, INFL5), flush=True)

    out = {"label": a.label, "sha256": SHA, "n_rows": int(len(d)), "n_tick": nt, "n_slot": NS,
           "gross_pool": round(float(pool_t.mean()), 6), "ks": KS, "fees": FEES,
           "s0_per_order": S0, "cap_pct": CAP, "inflate_k5": round(INFL5, 6),
           "block_h": C.BLOCK_H, "nrep": C.NREP, "seed": C.SEED, "n_block": nb,
           "level": {}, "size": {}, "delta_vs_K8": {}, "be": {}, "rule": {}}
    L, E, D = {}, {}, {}
    NT = {}                                      # NT[(K,f)] = chuoi net_tick (decimal) / tick

    for K in KS:
        m = rankflat < K
        ti, ei, sy, hm = tsflat[m], exflat[m], symflat[m], holdflat[m]
        sel = G[:, :K]
        mg = sel.mean(1)
        sg = sel.sum(1)
        aa = np.searchsorted(ticks, ti, "left")
        bb = np.searchsorted(ticks, ei, "left")
        ca = np.bincount(aa, minlength=nt + 1)[:nt]
        cb = np.bincount(bb, minlength=nt + 1)[:nt]
        e = (np.cumsum(ca) - np.cumsum(cb)).astype(np.float64)
        cnt = bb - aa
        tot = int(cnt.sum())
        tri = np.repeat(np.arange(len(aa)), cnt)
        base = np.repeat(aa, cnt) + np.arange(tot) - np.repeat(np.cumsum(cnt) - cnt, cnt)
        dt = (pd.DataFrame({"t": base.astype(np.int32), "s": sy[tri].astype(np.int32)})
              .drop_duplicates().groupby("t").size()
              .reindex(range(nt), fill_value=0).to_numpy(np.float64))
        del tri, base
        E[K], D[K] = e, dt
        rec = {"e_mean": round(float(e.mean()), 3), "e_max": int(e.max()),
               "e_p95": round(float(np.percentile(e, 95)), 1),
               "d_mean": round(float(dt.mean()), 3), "d_max": int(dt.max()),
               "d_p95": round(float(np.percentile(dt, 95)), 1),
               "hold_med_min": float(np.median(hm)),
               "gross_pct_anchor": {  # %equity = 100*S0*d
                   "mean": round(100 * S0 * float(dt.mean()), 2),
                   "p95": round(100 * S0 * float(np.percentile(dt, 95)), 2),
                   "max": round(100 * S0 * float(dt.max()), 2)},
               "metrics": {}}
        for f in FEES:
            nc, nsT = mg - f, sg - f * K
            NT[(K, f)] = nsT
            nb_num, nb_den = counts(nsT), counts(e)
            reps = nb_num[BI].sum(1) / nb_den[BI].sum(1)
            rec["metrics"]["net_coin|%.3f" % f] = mk(nc, tsv)
            rec["metrics"]["net_tick|%.3f" % f] = mk(nsT, tsv)
            rec["metrics"]["net_gr1dv|%.3f" % f] = dict(
                mean=round(float(nsT.sum() / e.sum()), 8),
                raw=[round(float(np.percentile(reps, 2.5)), 8),
                     round(float(np.percentile(reps, 97.5)), 8)],
                out_raw=bool(np.percentile(reps, 2.5) > 0 or np.percentile(reps, 97.5) < 0))
            rec["_reps|%.3f" % f] = reps
        rec["metrics"]["lift"] = mk(mg - pool_t, tsv)
        # break-even fee
        rec["be_fee_coin"] = round(float(mg.mean()), 6)          # phi lam net_coin = 0
        rec["be_fee_tick_per_order"] = round(float(sg.mean() / K), 6)
        L[K] = rec

    # ---- HE SO SIZE cho tran 70% (3 cach) ----
    for K in KS:
        r = L[K]
        dm, dp, dx = r["d_mean"], r["d_p95"], r["d_max"]
        gm, gp, gx = 100 * S0 * dm, 100 * S0 * dp, 100 * S0 * dx
        s = {"gross_anchor_mean": round(gm, 2), "gross_anchor_p95": round(gp, 2),
             "gross_anchor_max": round(gx, 2),
             "A_mean": round(CAP / gm, 4), "B_p95": round(CAP / gp, 4),
             "B_max": round(CAP / gx, 4)}
        s["A_mean_post"] = {  # gross sau khi co size
            "mean": round(gm * s["A_mean"], 3), "p95": round(gp * s["A_mean"], 2),
            "max": round(gx * s["A_mean"], 2)}
        s["B_p95_post"] = {"mean": round(gm * s["B_p95"], 3), "p95": round(gp * s["B_p95"], 3),
                           "max": round(gx * s["B_p95"], 2)}
        s["B_max_post"] = {"mean": round(gm * s["B_max"], 3), "p95": round(gp * s["B_max"], 3),
                           "max": round(gx * s["B_max"], 3)}
        out["size"]["K%d" % K] = s

    # ---- net/tick SAU SIZE (%equity/tick) cho tung cach + delta vs K=8 (cung cach) ----
    METHODS = {"A_mean": "A_mean", "B_p95": "B_p95", "B_max": "B_max"}
    for meth, skey in METHODS.items():
        out["delta_vs_K8"][meth] = {}
        for K in KS:
            sK = out["size"]["K%d" % K][skey]
            for f in FEES:
                ser = (2.0 * sK) * NT[(K, f)]                       # %equity/tick
                tag = "sized_net_tick|%.3f" % f
                L[K].setdefault("sized", {}).setdefault(meth, {})[tag] = mk(ser, tsv)
            rec8 = L[8]["sized"][meth]
            if K == 8:
                continue
            dd = {}
            for f in FEES:
                sK = out["size"]["K%d" % K][skey]
                s8 = out["size"]["K8"][skey]
                a_ = (2.0 * sK) * NT[(K, f)]
                b_ = (2.0 * s8) * NT[(8, f)]
                dd["d_sized_net_tick|%.3f" % f] = mk(a_ - b_, tsv)
                # delta net_gr1dv (bat bien size) — ratio paired
                dR = L[K]["_reps|%.3f" % f] - L[8]["_reps|%.3f" % f]
                mu = float(NT[(K, f)].sum() / E[K].sum() - NT[(8, f)].sum() / E[8].sum())
                lo, hi = float(np.percentile(dR, 2.5)), float(np.percentile(dR, 97.5))
                dd["d_net_gr1dv|%.3f" % f] = dict(
                    mean=round(mu, 8), raw=[round(lo, 8), round(hi, 8)],
                    k5=[round(mu - (mu - lo) * INFL5, 8), round(mu + (hi - mu) * INFL5, 8)],
                    out_raw=bool(lo > 0 or hi < 0),
                    out5=bool((mu - (mu - lo) * INFL5 > 0) or (mu + (hi - mu) * INFL5 < 0)),
                    out_both=bool((lo > 0 or hi < 0) and ((mu - (mu - lo) * INFL5 > 0) or
                                                          (mu + (hi - mu) * INFL5 < 0))))
            dd["d_e"] = mk(E[K] - E[8], tsv)
            dd["d_d"] = mk(D[K] - D[8], tsv)
            out["delta_vs_K8"][meth]["K%d" % K] = dd
        L[8]["sized"][meth]  # noqa

    # ---- LUAT §8 (chot truoc) ----
    for meth in METHODS:
        for K in KS:
            if K == 8:
                continue
            dd = out["delta_vs_K8"][meth]["K%d" % K]
            g6 = dd["d_sized_net_tick|0.006"]
            g0 = dd["d_sized_net_tick|0.000"]
            better = bool(g6["out_both"] and g6["dir"] == 1 and g0["out_both"] and g0["dir"] == 1)
            out["rule"]["%s|K%d" % (meth, K)] = {
                "d_sized_net_tick_f006_outside": bool(g6["out_both"]),
                "d_sized_net_tick_f000_outside": bool(g0["out_both"]),
                "verdict": "DOI K" if better else "GIU K=8"}
    L[8]["sized"]["A_mean"]  # noqa

    # ghi level (bo _reps)
    for K in KS:
        r = {k: v for k, v in L[K].items() if not k.startswith("_")}
        out["level"]["K%d" % K] = r

    json.dump(out, open(a.out, "w"), indent=1, default=str)
    print("JSON -> %s (%.1f KB)" % (a.out, os.path.getsize(a.out) / 1024.0), flush=True)

    # ---- bang ----
    print("\n### HE SO SIZE + GROSS SAU SIZE (%equity)")
    rows = []
    for K in KS:
        s = out["size"]["K%d" % K]
        rows.append({"K": K, "gross_TB": s["gross_anchor_mean"], "gross_p95": s["gross_anchor_p95"],
                     "gross_max": s["gross_anchor_max"], "sA": s["A_mean"], "sB95": s["B_p95"],
                     "sBmx": s["B_max"],
                     "A_B%g_mean": s["A_mean_post"]["mean"], "A_B%g_max": s["A_mean_post"]["max"],
                     "B95_B%g_p95": s["B_p95_post"]["p95"], "B95_B%g_max": s["B_p95_post"]["max"],
                     "Bmx_B%g_max": s["B_max_post"]["max"]})
    print(pd.DataFrame(rows).to_string(index=False))

    print("\n### MUC (net/coin, net/tick, net/1dv-gross) @ f=0,006")
    rows = []
    for K in KS:
        r = L[K]
        rows.append({"K": K, "coin@.006": round(100 * r["metrics"]["net_coin|0.006"]["mean"], 4),
                     "tick@.006": round(100 * r["metrics"]["net_tick|0.006"]["mean"], 4),
                     "gr1dv@.006": round(100 * r["metrics"]["net_gr1dv|0.006"]["mean"], 5),
                     "gr1dv@.004": round(100 * r["metrics"]["net_gr1dv|0.004"]["mean"], 5),
                     "gr1dv@.008": round(100 * r["metrics"]["net_gr1dv|0.008"]["mean"], 5),
                     "BE_coin%": round(100 * r["be_fee_coin"], 4),
                     "BE_tick/order%": round(100 * r["be_fee_tick_per_order"], 4)})
    print(pd.DataFrame(rows).to_string(index=False))

    print("\n### DELTA vs K=8 — net_gr1dv (bat bien size, ratio paired)  ['*' ngoai raw95]")
    for f in (0.004, 0.006, 0.008):
        line = []
        for K in KS:
            if K == 8:
                continue
            v = out["delta_vs_K8"]["A_mean"]["K%d" % K]["d_net_gr1dv|%.3f" % f]
            line.append("K%-2d %+.2e%s[%.1e,%.1e]" % (K, v["mean"], "*" if v["out_raw"] else " ",
                                                     v["raw"][0], v["raw"][1]))
        print("  f=%.3f | %s" % (f, " | ".join(line)))

    for meth in METHODS:
        print("\n### net/tick SAU SIZE (pct equity/tick) — cach " + meth)
        rows = []
        for K in KS:
            sK = out["size"]["K%d" % K][meth]
            d = {"K": K, "size": sK}
            for f in (0.006,):
                lv = L[K]["sized"][meth]["sized_net_tick|%.3f" % f]
                d["sized@.006"] = "%+.4f%s" % (lv["mean"], "*" if lv["out_both"] else "")
            if K != 8:
                dd = out["delta_vs_K8"][meth]["K%d" % K]
                for f in (0.000, 0.006):
                    v = dd["d_sized_net_tick|%.3f" % f]
                    d["d@%.3f" % f] = "%+.4f [%+.4f,%+.4f]%s" % (
                        v["mean"], v["k5"][0], v["k5"][1], "*" if v["out_both"] else "")
            rows.append(d)
        print(pd.DataFrame(rows).to_string(index=False))

    print("\n### LUAT §8")
    for k, v in out["rule"].items():
        print("  %-16s f006_ngoai=%s f000_ngoai=%s => %s" % (
            k, v["d_sized_net_tick_f006_outside"], v["d_sized_net_tick_f000_outside"], v["verdict"]))


if __name__ == "__main__":
    main()
