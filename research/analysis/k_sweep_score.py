#!/usr/bin/env python3
"""k_sweep_score.py — PREREG_K_SWEEP: noi `K` (top-K S1 moi tick) tren thuoc TIEN = nhan (b).

DUONG RE: pool P32 da la top-32 S1 moi tick => top-K cat ra TU CHINH POOL (cot `rank`), KHONG chay
lai exit engine, KHONG train, KHONG sim. Chi doc 1 parquet.

Chi so (chot truoc o PREREG §3):
  net_coin_K(f)  = mean_t mean_{i in topK}(gross_i - f)            (net/coin/vong)
  net_tick_K(f)  = mean_t sum_{i in topK}(gross_i - f)             (net/tick, tong RO)
  net_gross_K(f) = sum_t sum_{i in topK}(gross_i - f) / sum_t e_t  (net/1 don vi gross)  <-- QUYET DINH
  e_t = so vi the dang mo tai tick t ; lift_K = mean_t(mean_topK) - mean_t(mean ca pool)
CI: khoi 72h, NREP=2000, SEED=20260905 (c3_rates); luat inflate(k=5)=1,7941 + 1,21 legacy.

Chay: python3 k_sweep_score.py --out docs/result/k_sweep.json
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

LABEL = "/tmp/mrout/mrout/label_b_pnl.parquet"
SHA = "1d42b7f67466ca4ea9e8e74c4efe3c0a8664bde8a850a9f855209ef24927bb13"
KS = [8, 10, 12, 16, 32]
FEES = [0.0, 0.004, 0.008, 0.012]
INFL5 = float(np.sqrt(2.0 * np.log(5.0)))        # 1,7941 — k = 5 muc da thu
H = 3600000                                      # 1h (ms) — nhu stage2_score


def mk(v, ts):
    """mean + CI raw / inflate(5) / 1,21 + co 'ngoai CI' (dung nguyen MR.ci_mean)."""
    ci = MR.ci_mean(np.asarray(v, np.float64), np.asarray(ts, np.int64), inflate=INFL5)
    mu = float(ci["mean"])
    raw = [float(x) for x in ci["raw"]]
    b5 = [float(x) for x in ci["honest_infl"]]
    b121 = [float(x) for x in ci["infl"]]
    return {"mean": round(mu, 6), "raw": [round(x, 6) for x in raw],
            "k5": [round(x, 6) for x in b5], "leg121": [round(x, 6) for x in b121],
            "out_raw": bool(raw[0] > 0 or raw[1] < 0),
            "out5": bool(b5[0] > 0 or b5[1] < 0),
            "out121": bool(b121[0] > 0 or b121[1] < 0),
            "strict": bool((raw[0] > 0 or raw[1] < 0) and (b5[0] > 0 or b5[1] < 0)),
            "dir": 1 if mu > 0 else -1, "n": int(ci["n"])}


def ratio_stat(num, den, BI, nb):
    """reps cua R = sum(num)/sum(den) tren cung bo khoi (paired) + diem toan mau."""
    nn = np.bincount(BI[0], weights=num, minlength=nb) if False else None
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", default=LABEL)
    ap.add_argument("--out", default="docs/result/k_sweep.json")
    ap.add_argument("--ks", default=",".join(map(str, KS)))
    ap.add_argument("--fees", default=",".join(map(str, FEES)))
    a = ap.parse_args()
    ks = [int(x) for x in a.ks.split(",") if x]
    fees = [float(x) for x in a.fees.split(",") if x]
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)

    d = pd.read_parquet(a.label, columns=["ts", "symId", "rank", "gross", "exit_ts", "hold_min"])
    d = d.sort_values(["ts", "rank"], kind="stable").reset_index(drop=True)
    ticks = np.sort(d.ts.unique().astype(np.int64))
    nt = len(ticks)
    NS = int(d["rank"].max()) + 1
    assert len(d) == nt * NS, "pool khong vuong %d" % NS
    TS = d.ts.to_numpy(np.int64).reshape(nt, NS)
    G = d.gross.to_numpy(np.float64).reshape(nt, NS)
    assert (TS[:, 0][:, None] == TS).all(), "ts khong dong nhat trong tick"
    assert (d["rank"].to_numpy().reshape(nt, NS) == np.arange(NS)).all(), "rank khong 0..31"
    tsv = TS[:, 0]
    tsflat = d.ts.to_numpy(np.int64)
    exflat = d.exit_ts.to_numpy(np.int64)
    symflat = d.symId.to_numpy(np.int64)
    rankflat = d["rank"].to_numpy()
    holdflat = d.hold_min.to_numpy(np.float64)
    pool_t = G.mean(1)

    # ---- khoi 72h (giong stage2_score.block_boot_mean) ----
    bk = (tsv // (C.BLOCK_H * H))
    _, inv = np.unique(bk, return_inverse=True)
    nb = int(inv.max()) + 1
    BI = np.random.default_rng(C.SEED).integers(0, nb, (C.NREP, nb))
    bcnt = BI.shape[1]

    def counts(x):
        return np.bincount(inv, weights=x, minlength=nb)

    print("### pool %s: %d dong, %d tick x %d | gross_pool=%.6f | khoi=%d nrep=%d seed=%d" % (
        os.path.basename(a.label), len(d), nt, NS, pool_t.mean(), nb, C.NREP, C.SEED), flush=True)

    out = {"label": a.label, "sha256": SHA, "n_rows": int(len(d)), "n_tick": nt, "n_slot": NS,
           "gross_pool": round(float(pool_t.mean()), 6), "ks": ks, "fees": fees,
           "inflate_k5": round(INFL5, 6), "leg121": round(float(MR.G.LEGACY), 4),
           "block_h": C.BLOCK_H, "nrep": C.NREP, "seed": C.SEED, "n_block": nb,
           "level": {}, "delta_vs_K8": {}, "rule": {}}
    L, E = {}, {}

    for K in ks:
        m = rankflat < K
        ti, ei, sy, hm = tsflat[m], exflat[m], symflat[m], holdflat[m]
        sel = G[:, :K]
        mg = sel.mean(1)                      # mean gross top-K / tick
        sg = sel.sum(1)                       # sum gross top-K / tick
        # e_t = # vi the dang mo
        aa = np.searchsorted(ticks, ti, "left")
        bb = np.searchsorted(ticks, ei, "left")
        ca = np.bincount(aa, minlength=nt + 1)[:nt]
        cb = np.bincount(bb, minlength=nt + 1)[:nt]
        e = (np.cumsum(ca) - np.cumsum(cb)).astype(np.float64)
        # coin PHAN BIET / do trung
        cnt = bb - aa
        tot = int(cnt.sum())
        tri = np.repeat(np.arange(len(aa)), cnt)
        base = np.repeat(aa, cnt) + np.arange(tot) - np.repeat(np.cumsum(cnt) - cnt, cnt)
        dt = (pd.DataFrame({"t": base.astype(np.int32), "s": sy[tri].astype(np.int32)})
              .drop_duplicates().groupby("t").size()
              .reindex(range(nt), fill_value=0).to_numpy(np.float64))
        conc = np.divide(np.bincount(base, minlength=nt).astype(np.float64), dt,
                         out=np.zeros(nt), where=dt > 0)
        del tri, base
        E[K] = e
        rec = {"e_mean": round(float(e.mean()), 3), "e_max": int(e.max()),
               "e_p95": round(float(np.percentile(e, 95)), 1),
               "d_mean": round(float(dt.mean()), 2), "d_max": int(dt.max()),
               "d_p95": round(float(np.percentile(dt, 95)), 1),
               "overlap_mean": round(float(conc.mean()), 3), "overlap_max": round(float(conc.max()), 2),
               "hold_med_min": float(np.median(hm)), "metrics": {}}
        for f in fees:
            nc = mg - f
            ns = sg - f * K
            r_t = ns / e.mean()
            # ratio reps (paired blocks)
            nb_num = counts(ns)
            nb_den = counts(e)
            reps = nb_num[BI].sum(1) / nb_den[BI].sum(1)
            rec["metrics"]["net_coin|%.3f" % f] = mk(nc, tsv)
            rec["metrics"]["net_tick|%.3f" % f] = mk(ns, tsv)
            rec["metrics"]["net_gross|%.3f" % f] = dict(
                mean=round(float(ns.sum() / e.sum()), 8),
                raw=[round(float(np.percentile(reps, 2.5)), 8),
                     round(float(np.percentile(reps, 97.5)), 8)],
                out_raw=bool(np.percentile(reps, 2.5) > 0 or np.percentile(reps, 97.5) < 0),
                coef_variation_exposure=round(float(np.std(nb_den[BI].sum(1)) / nb_den.sum()), 6))
            rec["metrics"]["fd_net_gross|%.3f" % f] = mk(r_t, tsv)   # do nhay: mau so co dinh
            rec["_reps|%.3f" % f] = reps
        rec["metrics"]["lift"] = mk(mg - pool_t, tsv)
        L[K] = rec

    # ---- neo %equity ----
    sA = 700.0 / 35000.0
    sB = 0.56 / max(L[8]["e_max"], 1)
    for K in ks:
        r = L[K]
        r["gross_pct_anchorA"] = {"s_per_order": round(sA, 4),
                                  "mean": round(100 * r["e_mean"] * sA, 1),
                                  "p95": round(100 * r["e_p95"] * sA, 1),
                                  "max": round(100 * r["e_max"] * sA, 1)}
        r["gross_pct_anchorB"] = {"s_per_order": round(sB, 5),
                                  "mean": round(100 * r["e_mean"] * sB, 1),
                                  "p95": round(100 * r["e_p95"] * sB, 1),
                                  "max": round(100 * r["e_max"] * sB, 1)}
        r["size_keep_gross_vs_K8"] = round(L[8]["e_mean"] / r["e_mean"], 4)
        # POST-HOC (khong co trong PREREG §7): quy doi %equity tren so coin PHAN BIET (d)
        # thay vi so vi the (e) — moc noi suy voi quan sat 'gross 54-58%' cua LIVE.
        r["POSTHOC_gross_pct_on_distinct"] = {
            "anchorA_2pct": {"mean": round(100 * r["d_mean"] * sA, 1),
                             "p95": round(100 * r["d_p95"] * sA, 1),
                             "max": round(100 * r["d_max"] * sA, 1)},
            "anchorB": {"mean": round(100 * r["d_mean"] * sB, 1),
                        "p95": round(100 * r["d_p95"] * sB, 1),
                        "max": round(100 * r["d_max"] * sB, 1)}}
        out["level"]["K%d" % K] = {k: v for k, v in r.items() if not k.startswith("_")}

    # ---- DELTA vs K = 8 (ghep cap) ----
    for K in ks:
        if K == 8:
            continue
        dd = {}
        for f in fees:
            ncK, nc8 = G[:, :K].mean(1) - f, G[:, :8].mean(1) - f
            nsK, ns8 = G[:, :K].sum(1) - f * K, G[:, :8].sum(1) - f * 8
            dd["d_net_coin|%.3f" % f] = mk(ncK - nc8, tsv)
            dd["d_net_tick|%.3f" % f] = mk(nsK - ns8, tsv)
            dR = L[K]["_reps|%.3f" % f] - L[8]["_reps|%.3f" % f]
            mu = float(nsK.sum() / E[K].sum() - ns8.sum() / E[8].sum())
            r5 = [float(np.percentile(dR, 2.5)), float(np.percentile(dR, 97.5))]
            dd["d_net_gross|%.3f" % f] = dict(
                mean=round(mu, 8), raw=[round(x, 8) for x in r5],
                k5=[round(mu - (mu - r5[0]) * INFL5, 8), round(mu + (r5[1] - mu) * INFL5, 8)],
                leg121=[round(mu - (mu - r5[0]) * float(MR.G.LEGACY), 8),
                        round(mu + (r5[1] - mu) * float(MR.G.LEGACY), 8)],
                out_raw=bool(r5[0] > 0 or r5[1] < 0),
                out5=bool((mu - (mu - r5[0]) * INFL5 > 0) or (mu + (r5[1] - mu) * INFL5 < 0)),
                strict=bool((r5[0] > 0 or r5[1] < 0) and
                            ((mu - (mu - r5[0]) * INFL5 > 0) or (mu + (r5[1] - mu) * INFL5 < 0))),
                dir=1 if mu > 0 else -1, test="ratio bootstrap ghep cap 72h (cung BI nhu level)")
        dd["d_lift"] = mk((G[:, :K].mean(1) - pool_t) - (G[:, :8].mean(1) - pool_t), tsv)
        dd["d_e"] = mk((E[K] - E[8]), tsv)
        out["delta_vs_K8"]["K%d" % K] = dd

    # ---- LUAT §8 (chot TRUOC) ----
    for K in ks:
        if K == 8:
            continue
        dd = out["delta_vs_K8"]["K%d" % K]
        g0, g8, lf = dd["d_net_gross|0.000"], dd["d_net_gross|0.008"], dd["d_lift"]
        better = bool(g0["dir"] == 1 and g8["dir"] == 1 and g0["strict"] and g8["strict"])
        lift_drop = bool(lf["strict"] and lf["dir"] == -1)
        fd0, fd8 = dd["d_net_coin|0.000"], dd["d_net_coin|0.008"]
        out["rule"]["K%d" % K] = {
            "net_gross_better_f0_f008_outside_CI_k5": better,
            "net_coin_delta_f0": fd0["mean"], "net_coin_delta_f008": fd8["mean"],
            "net_coin_delta_outside_CI_k5": bool(fd0["strict"] or fd8["strict"]),
            "lift_drop_outside_CI_k5": lift_drop,
            "verdict": "NANG K" if (better and not lift_drop) else
                       ("TRADE-OFF (giu 8)" if better else "GIU K=8")}

    json.dump(out, open(a.out, "w"), indent=1, default=str)
    print("JSON -> %s (%.1f KB)" % (a.out, os.path.getsize(a.out) / 1024.0), flush=True)

    # ---- bang gon ----
    rows = []
    for K in ks:
        r = L[K]
        row = {"K": K, "e_mean": r["e_mean"], "e_max": r["e_max"], "e_p95": r["e_p95"],
               "coin_pb": r["d_mean"], "trung": r["overlap_mean"],
               "gross%A_max": r["gross_pct_anchorA"]["max"], "gross%B_max": r["gross_pct_anchorB"]["max"],
               "size_giu_gross": r["size_keep_gross_vs_K8"]}
        for f in fees:
            row["coin@%.3f" % f] = round(100 * r["metrics"]["net_coin|%.3f" % f]["mean"], 4)
            row["tick@%.3f" % f] = round(100 * r["metrics"]["net_tick|%.3f" % f]["mean"], 3)
            row["gr1dv@%.3f" % f] = round(100 * r["metrics"]["net_gross|%.3f" % f]["mean"], 4)
            row["fd_gr1dv@%.3f" % f] = round(100 * r["metrics"]["fd_net_gross|%.3f" % f]["mean"], 4)
        row["lift"] = round(100 * r["metrics"]["lift"]["mean"], 4)
        rows.append(row)
    P = pd.DataFrame(rows)
    print("\n### MUC: net/coin (%/vong) | net/tick (%/tick) | net/1dv-gross (%)")
    print(P[["K", "e_mean", "coin@0.000", "coin@0.008", "tick@0.000", "tick@0.008",
             "gr1dv@0.000", "gr1dv@0.004", "gr1dv@0.008", "gr1dv@0.012", "fd_gr1dv@0.008",
             "lift"]].to_string(index=False))
    print("\n### RUI RO")
    print(P[["K", "e_mean", "e_max", "e_p95", "coin_pb", "trung", "gross%A_max", "gross%B_max",
             "size_giu_gross"]].to_string(index=False))
    print("\n### RUI RO (POST-HOC: quy doi %equity tren so COIN PHAN BIET — moc noi suy voi 54-58% cua LIVE)")
    dr2 = []
    for K in ks:
        r = L[K]
        h = r["POSTHOC_gross_pct_on_distinct"]
        dr2.append({"K": K, "d_mean": r["d_mean"], "d_p95": r["d_p95"], "d_max": r["d_max"],
                    "A2pct_mean": h["anchorA_2pct"]["mean"], "A2pct_p95": h["anchorA_2pct"]["p95"],
                    "A2pct_max": h["anchorA_2pct"]["max"], "B_mean": h["anchorB"]["mean"],
                    "B_p95": h["anchorB"]["p95"], "B_max": h["anchorB"]["max"]})
    print(pd.DataFrame(dr2).to_string(index=False))
    print("\n### LIFT@K (mean_topK - mean ca pool) + CI k=5")
    for K in ks:
        v = L[K]["metrics"]["lift"]
        print("  K=%-2d lift=%+.5f%% CI5=[%+.5f%%,%+.5f%%] out_raw=%s out5=%s" % (
            K, 100 * v["mean"], 100 * v["raw"][0], 100 * v["raw"][1], v["out_raw"], v["out5"]))
    print("\n### PHI HOA VON (mean gross tren 1 don vi gross, %/tick/1dv)")
    for K in ks:
        r = L[K]
        be = r["metrics"]["net_gross|0.000"]["mean"]
        be_t = be * 100
        print("  K=%-2d gross1dv(f=0)=%.5f%% ; net_coin BE=%.4f%%/vong ; net_tick BE=%.3f%%/tick" % (
            K, be_t, 100 * r["metrics"]["net_coin|0.000"]["mean"],
            100 * r["metrics"]["net_tick|0.000"]["mean"] / K))
    print("\n### DELTA vs K=8  ('*' = ngoai CI k=5 ; '+' = ngoai raw95)")
    dr = []
    for K in ks:
        if K == 8:
            continue
        dd = out["delta_vs_K8"]["K%d" % K]
        row = {"K": K}
        for f in fees:
            v = dd["d_net_gross|%.3f" % f]
            row["d_gr1dv@%.3f" % f] = "%+.5f%s" % (v["mean"], "*" if v["strict"] else
                                                   ("+" if v["out_raw"] else ""))
        for met in ("d_net_coin", "d_net_tick"):
            for f in (0.0, 0.008):
                v = dd["%s|%.3f" % (met, f)]
                row["%s@%.3f" % (met, f)] = "%+.5f%s" % (v["mean"], "*" if v["strict"] else
                                                         ("+" if v["out_raw"] else ""))
        row["d_lift"] = "%+.5f%s" % (dd["d_lift"]["mean"], "*" if dd["d_lift"]["strict"] else
                                     ("+" if dd["d_lift"]["out_raw"] else ""))
        row["d_e"] = "%+.1f%s" % (dd["d_e"]["mean"], "*" if dd["d_e"]["strict"] else "")
        dr.append(row)
    print(pd.DataFrame(dr).to_string(index=False))
    print("\n### LUAT §8 (chot TRUOC)")
    for k, v in out["rule"].items():
        print("  %-4s better(f0 & f0.008 ngoai CI k=5)=%s | lift_drop(ngoai CI k=5)=%s => %s" %
              (k, v["net_gross_better_f0_f008_outside_CI_k5"], v["lift_drop_outside_CI_k5"], v["verdict"]))
    print("\n### CI cua net_gross (k=5) + CI cua delta")
    for K in ks:
        for f in (0.0, 0.008):
            v = L[K]["metrics"]["net_gross|%.3f" % f]
            s = "  K=%-2d f=%.3f level=%.5f CI5=[%.5f,%.5f] out_raw=%s" % (
                K, f, v["mean"], v["raw"][0], v["raw"][1], v["out_raw"])
            if K != 8:
                u = out["delta_vs_K8"]["K%d" % K]["d_net_gross|%.3f" % f]
                s += " | d=%.5f CI5=[%.5f,%.5f] out5=%s out_raw=%s" % (
                    u["mean"], u["k5"][0], u["k5"][1], u["out5"], u["out_raw"])
            print(s)


if __name__ == "__main__":
    main()
