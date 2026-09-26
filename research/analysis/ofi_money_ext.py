#!/usr/bin/env python3
"""ofi_money_ext.py — PREREG_OFI_MONEY §6 (B2): cham TIEN tren POOL MO RONG.

Pool_ext = P32 (label_b_pnl.parquet, S1 top-32) ∪ TAP COIN MOI (label_b_pnl_ext.parquet,
= candidate top-8 ∪ baseline_fresh top-8 ∪ noise top-8, hop 3 seed 43/44/45, TRU P32).
Ly do: B1 = 99,99 % top-K cua ca 3 arm nam NGOAI P32 (S1 chi chon small/mid-cap, candidate chon major)
=> duong RE tren P32 KHONG do duoc gia tri tien. Day la duong DO DUOC.

Chi so + ap tran 70 % + CI: DUNG NGUYEN ham cua research/analysis/ofi_money_score.py
(mk / mk_ratio / infl_k) => cung mot dinh nghia, cung block-72h/NREP/SEED.

Chay: python3 ofi_money_ext.py --kdirs ... --extra docs/result/label_b_pnl_ext.parquet \
        --out docs/result/ofi_money_ext.json
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
from ofi_money_score import (KS, FEES, F_DEC, S0, CAP, ARMS, KMAP, KSENS,  # noqa: E402
                             infl_k, mk, mk_ratio)

LABEL = "/home/ubuntu/mr_kaggle/ds_mr_labels/label_b_pnl.parquet"
SHA = "1d42b7f67466ca4ea9e8e74c4efe3c0a8664bde8a850a9f855209ef24927bb13"
H = 3600000


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", default=LABEL)
    ap.add_argument("--extra", required=True)
    ap.add_argument("--kdirs", required=True)
    ap.add_argument("--ensemble", default="43,44,45")
    ap.add_argument("--out", default="docs/result/ofi_money_ext.json")
    a = ap.parse_args()
    ens = [int(x) for x in a.ensemble.split(",")]
    kdirs = {int(os.path.basename(d).replace("kout", "")): d for d in a.kdirs.split(",")}

    # ---------- pool mo rong ----------
    c = ["ts", "symId", "gross", "exit_ts"]
    L1 = pd.read_parquet(a.label, columns=c).assign(src="P32")
    L2 = pd.read_parquet(a.extra, columns=c).assign(src="NEW")
    P = pd.concat([L1, L2], ignore_index=True)
    n_new = int((P.src == "NEW").sum())
    before = len(P)
    P = P.drop_duplicates(["ts", "symId"], keep="first").reset_index(drop=True)
    print("### pool_ext: P32=%d + NEW=%d = %d (dup bo=%d) | tick=%d | coin/tick TB=%.1f max=%d" % (
        len(L1), n_new, len(P), before - len(P), P.ts.nunique(), len(P) / P.ts.nunique(),
        P.groupby("ts").size().max()), flush=True)
    ticks = np.sort(P.ts.unique().astype(np.int64))
    nt = len(ticks)
    P = P.sort_values(["ts", "symId"], kind="stable").reset_index(drop=True)
    ti = np.searchsorted(ticks, P.ts.to_numpy(np.int64))
    ci = P.groupby("ts", sort=False).cumcount().to_numpy()
    maxC = int(ci.max()) + 1
    GR = np.full((nt, maxC), np.nan)
    EX = np.full((nt, maxC), -1, np.int64)
    SY = np.full((nt, maxC), -1, np.int64)
    GR[ti, ci] = P.gross.to_numpy(np.float64)
    EX[ti, ci] = P.exit_ts.to_numpy(np.int64)
    SY[ti, ci] = P.symId.to_numpy(np.int64)
    tsv = ticks

    inv = np.unique((tsv // (C.BLOCK_H * H)), return_inverse=True)[1]
    nb = int(inv.max()) + 1
    BI = np.random.default_rng(C.SEED).integers(0, nb, (C.NREP, nb))

    def cnt(x):
        return np.bincount(inv, weights=x, minlength=nb)

    # ---------- diem ----------
    def sc_mat(p):
        S = np.full((nt, maxC), -np.inf)
        pts = p.ts.to_numpy(np.int64)
        i = np.searchsorted(ticks, pts)
        i = np.where((i < nt) & (ticks[np.minimum(i, nt - 1)] == pts), i, -1)
        df = pd.DataFrame({"t": i, "s": p.symId.to_numpy(np.int64), "v": p.score.to_numpy(np.float64)})
        key = pd.DataFrame({"t": np.repeat(np.arange(nt), maxC), "s": SY.reshape(-1),
                            "c": np.tile(np.arange(maxC), nt)})
        key = key[key.s >= 0]
        m = key.merge(df, on=["t", "s"], how="left")
        S[m.t.to_numpy(), m.c.to_numpy()] = m.v.to_numpy()
        return S

    SC = {}
    for arm in ARMS:
        acc = None
        for s in ens:
            p = pd.read_parquet(os.path.join(kdirs[s], KMAP[arm]),
                                columns=["ts", "sym", "score"]).rename(columns={"sym": "symId"})
            v = sc_mat(p)
            acc = v if acc is None else acc + v
        SC[arm] = acc / len(ens)
        del acc

    def arm_series(S):
        out = {}
        order = np.argsort(-S, axis=1, kind="stable")
        sel = np.take_along_axis(GR, order, axis=1)
        selx = np.take_along_axis(EX, order, axis=1)
        sels = np.take_along_axis(SY, order, axis=1)
        vld = ~np.isnan(sel)
        for K in KS:
            mk_ = (order < K) & vld
            nsel = mk_.sum(1)
            sv = np.where(vld, sel, np.nan)[:, :K]
            mg = np.nanmean(np.where(mk_[:, :K], sel[:, :K], np.nan), axis=1)
            sg = np.nansum(np.where(mk_[:, :K], sel[:, :K], np.nan), axis=1)
            mf = mk_.reshape(-1)
            ti_, ei_, sy_ = np.repeat(ticks, maxC)[mf], selx.reshape(-1)[mf], sels.reshape(-1)[mf]
            aa = np.searchsorted(ticks, ti_, "left")
            bb = np.searchsorted(ticks, ei_, "left")
            ca = np.bincount(aa, minlength=nt + 1)[:nt]
            cb = np.bincount(bb, minlength=nt + 1)[:nt]
            e = (np.cumsum(ca) - np.cumsum(cb)).astype(np.float64)
            cc = bb - aa
            tot = int(cc.sum())
            tri = np.repeat(np.arange(len(aa)), cc)
            base = np.repeat(aa, cc) + np.arange(tot) - np.repeat(np.cumsum(cc) - cc, cc)
            dt = (pd.DataFrame({"t": base.astype(np.int32), "s": sy_[tri].astype(np.int32)})
                  .drop_duplicates().groupby("t").size()
                  .reindex(range(nt), fill_value=0).to_numpy(np.float64))
            out[K] = {"mg": mg, "sg": sg, "e": e, "d": dt, "nsel": nsel.astype(float)}
        return out

    AS = {arm: arm_series(SC[arm]) for arm in ARMS}

    out = {"label": a.label, "extra": a.extra, "sha256": SHA, "n_tick": nt,
           "n_row": int(len(P)), "n_new": n_new, "max_coin_per_tick": maxC,
           "ks": KS, "fees": FEES, "f_dec": F_DEC, "s0_per_order": S0, "cap_pct": CAP,
           "ensemble_seeds": ens, "block_h": C.BLOCK_H, "nrep": C.NREP, "seed": C.SEED,
           "n_block": nb, "inflate": {("k%d" % k): round(infl_k(k), 6) for k in KSENS},
           "level": {}, "delta": {}, "per_seed": {}, "rule": {}}

    for arm in ARMS:
        out["level"][arm] = {}
        for K in KS:
            S = AS[arm][K]
            gm = 100 * S0 * S["d"].mean()
            gp = 100 * S0 * np.percentile(S["d"], 95)
            gx = 100 * S0 * S["d"].max()
            sz = {"A_mean": CAP / gm, "B95": CAP / gp, "Bmax": CAP / gx}
            rec = {"e_mean": round(float(S["e"].mean()), 3), "d_mean": round(float(S["d"].mean()), 3),
                   "d_p95": round(float(np.percentile(S["d"], 95)), 1), "d_max": int(S["d"].max()),
                   "nsel_mean": round(float(S["nsel"].mean()), 2),
                   "gross_anchor": {"mean": round(gm, 2), "p95": round(gp, 2), "max": round(gx, 2)},
                   "size": {k2: round(v2, 4) for k2, v2 in sz.items()},
                   "gross_post": {"A_mean": {"mean": 70.0, "max": round(gx * sz["A_mean"], 2)},
                                  "B95": {"p95": 70.0, "max": round(gx * sz["B95"], 2)},
                                  "Bmax": {"max": round(gx * sz["Bmax"], 3)}},
                   "metrics": {}, "_reps": {}, "_nk": {}}
            for f in FEES:
                rec["metrics"]["net_coin|%.3f" % f] = mk(S["mg"] - f, tsv)
                nk = S["sg"] - f * S["nsel"]
                rec["metrics"]["net_tick|%.3f" % f] = mk(nk, tsv)
                for meth in ("A_mean", "B95", "Bmax"):
                    rec["metrics"]["sized_net_tick|%s|%.3f" % (meth, f)] = mk(2.0 * sz[meth] * nk, tsv)
                reps = cnt(nk)[BI].sum(1) / cnt(S["e"])[BI].sum(1)
                rec["metrics"]["net_gr1dv|%.3f" % f] = mk_ratio(reps, float(nk.sum() / S["e"].sum()))
                rec["_reps"]["%.3f" % f] = reps
                rec["_nk"]["%.3f" % f] = nk
            rec["be_fee_coin"] = round(float(S["mg"].mean()), 6)
            out["level"][arm]["K%d" % K] = rec

    PAIRS = [("candidate", "baseline_fresh"), ("candidate", "noise_ofi_check"),
             ("noise_ofi_check", "candidate"), ("baseline_fresh", "noise_ofi_check")]
    for (A, B) in PAIRS:
        tag, out["delta"][tag] = "%s-%s" % (A, B), {}
        for K in KS:
            e = {"d_e": round(float(AS[A][K]["e"].mean() - AS[B][K]["e"].mean()), 3),
                 "d_d": round(float(AS[A][K]["d"].mean() - AS[B][K]["d"].mean()), 3),
                 "d_gross_coin": round(float(np.nanmean(AS[A][K]["mg"] - AS[B][K]["mg"])), 10),
                 "metrics": {}}
            for f in FEES:
                e["metrics"]["dnet_coin|%.3f" % f] = mk(AS[A][K]["mg"] - AS[B][K]["mg"], tsv)
                na = AS[A][K]["sg"] - f * AS[A][K]["nsel"]
                nbb = AS[B][K]["sg"] - f * AS[B][K]["nsel"]
                e["metrics"]["dnet_tick|%.3f" % f] = mk(na - nbb, tsv)
                sa, sb = out["level"][A]["K%d" % K]["size"], out["level"][B]["K%d" % K]["size"]
                for meth in ("A_mean", "B95", "Bmax"):
                    e["metrics"]["dsized_net_tick|%s|%.3f" % (meth, f)] = mk(
                        2.0 * (sa[meth] * na - sb[meth] * nbb), tsv)
                ra = out["level"][A]["K%d" % K]["_reps"]["%.3f" % f]
                rb = out["level"][B]["K%d" % K]["_reps"]["%.3f" % f]
                mu = float(na.sum() / AS[A][K]["e"].sum() - nbb.sum() / AS[B][K]["e"].sum())
                g = mk_ratio(ra - rb, mu)
                g["dir_k5"] = (1 if mu > 0 else -1) if g["out_k5"] else 0
                e["metrics"]["dnet_gr1dv|%.3f" % f] = g
            out["delta"][tag]["K%d" % K] = e

    for (A, B) in [("candidate", "baseline_fresh"), ("candidate", "noise_ofi_check")]:
        g = out["delta"]["%s-%s" % (A, B)]["K8"]["metrics"]["dnet_gr1dv|%.3f" % F_DEC]
        for k in KSENS:
            out["rule"]["%s-%s|k%d" % (A, B, k)] = {
                "dnet_gr1dv": round(g["mean"], 8), "ci": [round(x, 8) for x in g["k%d" % k]],
                "outside_ci": bool(g["out_k%d" % k]), "dir": int(np.sign(g["mean"])),
                "co_gia_tri_tien": bool(g["out_k%d" % k] and g["mean"] > 0)}
    g = out["delta"]["noise_ofi_check-candidate"]["K8"]["metrics"]["dnet_gr1dv|%.3f" % F_DEC]
    out["rule"]["valid_noise_minus_cand"] = {
        "mean": round(g["mean"], 8), "raw": [round(x, 8) for x in g["raw"]],
        "out_k2": bool(g["out_k2"]), "out_k5": bool(g["out_k5"]),
        "positive_outside": bool(g["out_k5"] and g["mean"] > 0)}

    # ---------- per-seed ----------
    for s in ens:
        ASs = {}
        for arm in ARMS:
            p = pd.read_parquet(os.path.join(kdirs[s], KMAP[arm]),
                                columns=["ts", "sym", "score"]).rename(columns={"sym": "symId"})
            ASs[arm] = arm_series(sc_mat(p))
        for (A, B) in [("candidate", "baseline_fresh"), ("candidate", "noise_ofi_check")]:
            K = 8
            na = ASs[A][K]["sg"] - F_DEC * ASs[A][K]["nsel"]
            nbb = ASs[B][K]["sg"] - F_DEC * ASs[B][K]["nsel"]
            ra = cnt(na)[BI].sum(1) / cnt(ASs[A][K]["e"])[BI].sum(1)
            rb = cnt(nbb)[BI].sum(1) / cnt(ASs[B][K]["e"])[BI].sum(1)
            mu = float(na.sum() / ASs[A][K]["e"].sum() - nbb.sum() / ASs[B][K]["e"].sum())
            g = mk_ratio(ra - rb, mu)
            out["per_seed"]["%s-%s|s%d" % (A, B, s)] = {
                "dnet_gr1dv": round(mu, 8), "raw": [round(x, 8) for x in g["raw"]],
                "k5": [round(x, 8) for x in g["k5"]], "out_k5": bool(g["out_k5"]),
                "dnet_coin": round(float(np.nanmean(ASs[A][K]["mg"] - ASs[B][K]["mg"])), 8)}
        del ASs

    # ---------- bang ----------
    print("\n### POOL MO RONG — MUC @ f=0,006 (net_coin %/vong · net_gr1dv · BE_coin · e/d/gTB/gMAX)")
    for arm in ARMS:
        for K in KS:
            r = out["level"][arm]["K%d" % K]
            print("  %-16s K%-2d coin=%+.4f gr1dv=%+.5f BE=%.4f e=%.1f d=%.1f gTB=%.1f gMAX=%.1f nsel=%.1f" % (
                arm, K, 100 * r["metrics"]["net_coin|0.006"]["mean"],
                100 * r["metrics"]["net_gr1dv|0.006"]["mean"], 100 * r["be_fee_coin"],
                r["e_mean"], r["d_mean"], r["gross_anchor"]["mean"], r["gross_anchor"]["max"],
                r["nsel_mean"]))
    print("\n### DELTA @ f=0,006 ('*' = ngoai CI k=5)")
    for (A, B) in PAIRS[:3]:
        tag = "%s-%s" % (A, B)
        for K in KS:
            d = out["delta"][tag]["K%d" % K]["metrics"]
            for m in ("dnet_coin|0.006", "dnet_gr1dv|0.006", "dsized_net_tick|Bmax|0.006"):
                v = d[m]
                print("  %-30s K%-2d %-26s %+.6f%s [%+.6f,%+.6f]" % (
                    tag, K, m, v["mean"], "*" if v["out_k5"] else " ", v["k5"][0], v["k5"][1]))
    print("\n### KIEM dnet_coin(f) doc lap f (candidate-baseline_fresh, K=8)")
    for f in FEES:
        print("   f=%.3f  %+.12f" % (f, out["delta"]["candidate-baseline_fresh"]["K8"]["metrics"]["dnet_coin|%.3f" % f]["mean"]))
    print("\n### LUAT (f=0,006, K=8, tran 70%)")
    for kk, vv in out["rule"].items():
        if isinstance(vv, dict) and "co_gia_tri_tien" in vv:
            print("  %-32s dgr1dv=%+.6f ci=%s => %s" % (kk, vv["dnet_gr1dv"],
                  [round(x, 6) for x in vv["ci"]], "CO" if vv["co_gia_tri_tien"] else "KHONG"))
    print("  valid_noise_minus_cand:", out["rule"]["valid_noise_minus_cand"])
    print("\n### PER-SEED @K=8, f=0,006")
    for kk, vv in out["per_seed"].items():
        print("  %-30s dgr1dv=%+.6f raw[%+.6f,%+.6f] k5=[%+.6f,%+.6f] out=%s  dcoin=%+.6f" % (
            kk, vv["dnet_gr1dv"], vv["raw"][0], vv["raw"][1], vv["k5"][0], vv["k5"][1],
            vv["out_k5"], vv["dnet_coin"]))
    for arm in ARMS:
        for K in KS:
            out["level"][arm]["K%d" % K].pop("_reps", None)
            out["level"][arm]["K%d" % K].pop("_nk", None)
    json.dump(out, open(a.out, "w"), indent=1, default=str)
    print("\nJSON -> %s (%.1f KB)" % (a.out, os.path.getsize(a.out) / 1024.0), flush=True)


if __name__ == "__main__":
    main()
