#!/usr/bin/env python3
"""ofi_money_score.py — PREREG_OFI_MONEY (docs/prereg/PREREG_OFI_MONEY.md).

Cau hoi: OFI candidate co TAO RA GIA TRI TIEN khong (ngoai CI), duoi tran gross 70% CUNG + phi 0,6%/vong?

Duong RE: pool P32 /home/ubuntu/mr_kaggle/ds_mr_labels/label_b_pnl.parquet (KHONG build lai nhan).
Diem: kernel chuyendinh/ofi-v3-ms-s<seed> (pred_ofi_candidate_v2 / pred_baseline_fresh / pred_ofi_noise_v2).
Chi so + ap tran 70% + CI: COPY NGUYEN tu research/analysis/cap70_fee06.py / mr_pnl_score.py
(model_ruler.ci_mean -> stage2_score.block_boot_mean + c3_rates; BLOCK_H=72 NREP=2000 SEED=20260905).

Chay:
  python3 ofi_money_score.py --kdirs /tmp/kout42,/tmp/kout43,/tmp/kout44,/tmp/kout45 \
      --ensemble 43,44,45 --out docs/result/ofi_money.json
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
F_DEC = 0.006                                    # phi QUYET DINH
S0 = 0.02                                        # neo POST-HOC 2,0 %equity/lenh
CAP = 70.0                                       # tran gross %equity (owner 26/09)
KMAP = {"candidate": "pred_ofi_candidate_v2.parquet",
        "baseline_fresh": "pred_baseline_fresh.parquet",
        "noise_ofi_check": "pred_ofi_noise_v2.parquet"}
ARMS = ["candidate", "baseline_fresh", "noise_ofi_check"]
H = 3600000
KSENS = [2, 5, 10]


def infl_k(k):
    return float(np.sqrt(2.0 * np.log(k))) if k > 1 else 1.0


def mk(v, ts, bad=None):
    """CI block-72h cho TRUNG BINH (raw + inflate theo nhieu k)."""
    ci = MR.ci_mean(np.asarray(v, np.float64), np.asarray(ts, np.int64), inflate=1.0)
    mu = float(ci["mean"])
    lo, hi = float(ci["raw"][0]), float(ci["raw"][1])
    out = {"mean": mu, "raw": [lo, hi], "n": int(ci["n"])}
    for k in KSENS:
        il = mu - (mu - lo) * infl_k(k)
        ih = mu + (hi - mu) * infl_k(k)
        out["k%d" % k] = [il, ih]
        out["out_k%d" % k] = bool((lo > 0 or hi < 0) and (il > 0 or ih < 0))
        out["out_raw_k%d" % k] = bool(lo > 0 or hi < 0)
    return out


def mk_ratio(reps, mu):
    lo, hi = float(np.percentile(reps, 2.5)), float(np.percentile(reps, 97.5))
    out = {"mean": mu, "raw": [lo, hi]}
    for k in KSENS:
        il = mu - (mu - lo) * infl_k(k)
        ih = mu + (hi - mu) * infl_k(k)
        out["k%d" % k] = [il, ih]
        out["out_k%d" % k] = bool((lo > 0 or hi < 0) and (il > 0 or ih < 0))
        out["out_raw_k%d" % k] = bool(lo > 0 or hi < 0)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--label", default=LABEL)
    ap.add_argument("--kdirs", required=True)
    ap.add_argument("--ensemble", default="43,44,45")
    ap.add_argument("--out", default="docs/result/ofi_money.json")
    a = ap.parse_args()
    ens = [int(x) for x in a.ensemble.split(",")]
    kdirs = {int(os.path.basename(d).replace("kout", "")): d for d in a.kdirs.split(",")}
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)

    # ---------- pool P32 ----------
    d = pd.read_parquet(a.label, columns=["ts", "symId", "rank", "gross", "exit_ts", "hold_min"])
    d = d.sort_values(["ts", "rank"], kind="stable").reset_index(drop=True)
    ticks = np.sort(d.ts.unique().astype(np.int64))
    nt = len(ticks)
    NS = int(d["rank"].max()) + 1
    assert len(d) == nt * NS and NS == 32, "pool khong vuong %d" % NS
    tsv = d.ts.to_numpy(np.int64).reshape(nt, NS)[:, 0]
    G = d.gross.to_numpy(np.float64).reshape(nt, NS)
    tsflat = d.ts.to_numpy(np.int64)
    exflat = d.exit_ts.to_numpy(np.int64)
    symflat = d.symId.to_numpy(np.int64)
    pool_t = G.mean(1)
    print("### pool %s: %d dong, %d tick x %d | gross_pool=%.6f" % (
        os.path.basename(a.label), len(d), nt, NS, pool_t.mean()), flush=True)

    inv = np.unique((tsv // (C.BLOCK_H * H)), return_inverse=True)[1]
    nb = int(inv.max()) + 1
    BI = np.random.default_rng(C.SEED).integers(0, nb, (C.NREP, nb))

    def cnt(x):
        return np.bincount(inv, weights=x, minlength=nb)

    # ---------- tin hieu: doc pred 1 lan / (arm,seed); ensemble = trung binh ----------
    raw = {}
    for s in sorted(set(ens + [42])):
        if s not in kdirs:
            continue
        for arm in ARMS:
            p = pd.read_parquet(os.path.join(kdirs[s], KMAP[arm]), columns=["ts", "sym", "score"])
            raw[(arm, s)] = p.rename(columns={"sym": "symId"})
    have_seeds = sorted({s for (_, s) in raw})

    univ = None
    for (arm, s), p in raw.items():
        u = np.unique(p.symId.to_numpy())
        univ = u if univ is None else np.union1d(univ, u)
    UIDX = pd.Index(univ)
    TPOS = pd.Series(np.arange(nt), index=ticks)

    def to_mat(p):
        """pred -> (nt, n_univ) diem; NaN neu thieu."""
        M = np.full((nt, len(univ)), np.nan)
        pts = p.ts.to_numpy(np.int64)
        i = np.searchsorted(ticks, pts)
        i = np.where((i < nt) & (ticks[np.minimum(i, nt - 1)] == pts), i, -1)
        j = UIDX.get_indexer(p.symId.to_numpy())
        ok = (i >= 0) & (j >= 0)
        M[i[ok], j[ok]] = p.score.to_numpy(np.float64)[ok]
        return M

    # ---------- B1: top-K cua arm NGOAI P32 ----------
    PIN = np.zeros((nt, len(univ)), bool)
    PIN[np.repeat(np.arange(nt), NS), UIDX.get_indexer(symflat)] = True
    from collections import defaultdict
    p32cnt = defaultdict(int)
    for x in symflat:
        p32cnt[x] += 1
    print("### P32: %d sym duy nhat tren %d tick; universe pred = %d sym" % (
        len(p32cnt), nt, len(univ)), flush=True)
    b1 = {}
    for arm in ARMS:
        M = to_mat(raw[(arm, ens[0])])
        order = np.argsort(-np.where(np.isnan(M), -np.inf, M), axis=1, kind="stable")
        b1[arm] = {}
        for K in KS:
            top = order[:, :K]
            inside = np.take_along_axis(PIN, top, axis=1).sum()
            b1[arm]["K%d" % K] = {"n_top": int(top.size), "n_inside": int(inside),
                                  "pct_outside": round(100.0 * (top.size - inside) / top.size, 3)}
        del M, order
    print("\n### B1 — % top-K nam NGOAI P32 (pre-reg: top-8 > 10 % => co 'KHONG DO DUOC het')")
    for arm in ARMS:
        print("  %-16s %s" % (arm, "  ".join("K%d=%.1f%%" % (K, b1[arm]["K%d" % K]["pct_outside"])
                                             for K in KS)), flush=True)

    # ---------- chon top-K + chi so ----------
    def arm_series(sco):
        out = {}
        order = np.argsort(-sco, axis=1, kind="stable")
        sels = np.take_along_axis(G, order, axis=1)
        rowbase = np.arange(nt)[:, None] * NS
        for K in KS:
            topk = order[:, :K]                      # CHI SO COT GOC cua top-K (dung Thu tu diem)
            mf = np.zeros(nt * NS, bool)
            mf[(rowbase + topk).reshape(-1)] = True
            ti, ei, sy = tsflat[mf], exflat[mf], symflat[mf]
            sv = sels[:, :K]
            mg, sg = sv.mean(1), sv.sum(1)
            aa = np.searchsorted(ticks, ti, "left")
            bb = np.searchsorted(ticks, ei, "left")
            ca = np.bincount(aa, minlength=nt + 1)[:nt]
            cb = np.bincount(bb, minlength=nt + 1)[:nt]
            e = (np.cumsum(ca) - np.cumsum(cb)).astype(np.float64)
            c = bb - aa
            tot = int(c.sum())
            tri = np.repeat(np.arange(len(aa)), c)
            base = np.repeat(aa, c) + np.arange(tot) - np.repeat(np.cumsum(c) - c, c)
            dt = (pd.DataFrame({"t": base.astype(np.int32), "s": sy[tri].astype(np.int32)})
                  .drop_duplicates().groupby("t").size()
                  .reindex(range(nt), fill_value=0).to_numpy(np.float64))
            out[K] = {"mg": mg, "sg": sg, "e": e, "d": dt}
        return out

    # diem ensemble DUNG tren pool (reshape theo d); da kiem phu 100 %
    key = d[["ts", "symId"]]
    SCP = {}
    for arm in ARMS:
        acc = None
        for s in ens:
            m = key.merge(raw[(arm, s)], on=["ts", "symId"], how="left")
            assert m.score.notna().all(), "%s seed %d thieu diem tren pool" % (arm, s)
            v = m.score.to_numpy(np.float64).reshape(nt, NS)
            acc = v if acc is None else acc + v
        SCP[arm] = acc / len(ens)

    AS = {arm: arm_series(SCP[arm]) for arm in ARMS}

    out = {"label": a.label, "sha256": SHA, "n_rows": int(len(d)), "n_tick": nt, "n_slot": NS,
           "gross_pool": round(float(pool_t.mean()), 6), "ks": KS, "fees": FEES, "f_dec": F_DEC,
           "s0_per_order": S0, "cap_pct": CAP, "ensemble_seeds": ens, "universe_syms": int(len(univ)),
           "block_h": C.BLOCK_H, "nrep": C.NREP, "seed": C.SEED, "n_block": nb,
           "inflate": {("k%d" % k): round(infl_k(k), 6) for k in KSENS},
           "B1_topk_outside_p32": b1, "level": {}, "delta": {}, "per_seed": {}, "rule": {}}

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
                   "gross_anchor": {"mean": round(gm, 2), "p95": round(gp, 2), "max": round(gx, 2)},
                   "size": {kk: round(vv, 4) for kk, vv in sz.items()},
                   "gross_post": {"A_mean": {"mean": 70.0, "max": round(gx * sz["A_mean"], 2)},
                                  "B95": {"p95": 70.0, "max": round(gx * sz["B95"], 2)},
                                  "Bmax": {"max": round(gx * sz["Bmax"], 3)}},
                   "metrics": {}, "_reps": {}}
            for f in FEES:
                rec["metrics"]["net_coin|%.3f" % f] = mk(S["mg"] - f, tsv)
                nk = S["sg"] - f * K
                rec["metrics"]["net_tick|%.3f" % f] = mk(nk, tsv)
                for meth in ("A_mean", "B95", "Bmax"):
                    rec["metrics"]["sized_net_tick|%s|%.3f" % (meth, f)] = mk(2.0 * sz[meth] * nk, tsv)
                reps = cnt(nk)[BI].sum(1) / cnt(S["e"])[BI].sum(1)
                rec["metrics"]["net_gr1dv|%.3f" % f] = mk_ratio(reps, float(nk.sum() / S["e"].sum()))
                rec["_reps"]["%.3f" % f] = reps
                rec["_nk|%.3f" % f] = nk
            rec["be_fee_coin"] = round(float(S["mg"].mean()), 6)
            out["level"][arm]["K%d" % K] = rec

    # ---------- DELTA ghep cap theo tick ----------
    PAIRS = [("candidate", "baseline_fresh"), ("candidate", "noise_ofi_check"),
             ("noise_ofi_check", "candidate"), ("baseline_fresh", "noise_ofi_check")]
    for (A, B) in PAIRS:
        tag, out["delta"][tag] = "%s-%s" % (A, B), {}
        for K in KS:
            e = {"d_e": round(float(AS[A][K]["e"].mean() - AS[B][K]["e"].mean()), 3),
                 "d_d": round(float(AS[A][K]["d"].mean() - AS[B][K]["d"].mean()), 3),
                 "d_gross_coin": round(float(AS[A][K]["mg"].mean() - AS[B][K]["mg"].mean()), 10),
                 "metrics": {}}
            for f in FEES:
                e["metrics"]["dnet_coin|%.3f" % f] = mk(AS[A][K]["mg"] - AS[B][K]["mg"], tsv)
                na = out["level"][A]["K%d" % K]["_nk|%.3f" % f]
                nbb = out["level"][B]["K%d" % K]["_nk|%.3f" % f]
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

    # ---------- LUAT ----------
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

    # ---------- per-seed (phu) ----------
    for s in have_seeds:
        ASs = {}
        for arm in ARMS:
            m = key.merge(raw[(arm, s)], on=["ts", "symId"], how="left")
            if m.score.isna().any():
                continue
            ASs[arm] = arm_series(m.score.to_numpy(np.float64).reshape(nt, NS))
        if len(ASs) < 3:
            continue
        for arm in ARMS:
            K = 8
            S = ASs[arm][K]
            out["per_seed"]["%s|s%d|net_coin" % (arm, s)] = round(float((S["mg"] - F_DEC).mean()), 8)
            out["per_seed"]["%s|s%d|net_gr1dv" % (arm, s)] = round(
                float((S["sg"] - F_DEC * K).sum() / S["e"].sum()), 8)
        for (A, B) in [("candidate", "baseline_fresh"), ("candidate", "noise_ofi_check")]:
            K = 8
            na = ASs[A][K]["sg"] - F_DEC * K
            nbb = ASs[B][K]["sg"] - F_DEC * K
            ra = cnt(na)[BI].sum(1) / cnt(ASs[A][K]["e"])[BI].sum(1)
            rb = cnt(nbb)[BI].sum(1) / cnt(ASs[B][K]["e"])[BI].sum(1)
            mu = float(na.sum() / ASs[A][K]["e"].sum() - nbb.sum() / ASs[B][K]["e"].sum())
            g = mk_ratio(ra - rb, mu)
            out["per_seed"]["%s-%s|s%d" % (A, B, s)] = {
                "dnet_gr1dv": round(mu, 8), "raw": [round(x, 8) for x in g["raw"]],
                "k5": [round(x, 8) for x in g["k5"]], "out_k5": bool(g["out_k5"])}
        del ASs

    # ---------- bang in ----------
    print("\n### MUC @ f=0,006  (net_coin %/vong · net_gr1dv · BE_coin %/vong · e/d/gross TB/MAX)")
    for arm in ARMS:
        for K in KS:
            r = out["level"][arm]["K%d" % K]
            print("  %-16s K%-2d coin=%+.4f  gr1dv=%+.5f  BE=%.4f  e=%.1f d=%.1f gTB=%.1f gMAX=%.1f" % (
                arm, K, 100 * r["metrics"]["net_coin|0.006"]["mean"],
                100 * r["metrics"]["net_gr1dv|0.006"]["mean"], 100 * r["be_fee_coin"],
                r["e_mean"], r["d_mean"], r["gross_anchor"]["mean"], r["gross_anchor"]["max"]))

    print("\n### DELTA @ f=0,006 ('*' = ngoai CI k=5)")
    for (A, B) in PAIRS[:3]:
        tag = "%s-%s" % (A, B)
        for K in KS:
            dd = out["delta"][tag]["K%d" % K]["metrics"]
            c, g = dd["dnet_coin|0.006"], dd["dnet_gr1dv|0.006"]
            print("  %-30s K%-2d dcoin=%+.5f%s[%+.5f,%+.5f] dgr1dv=%+.5f%s[%+.5f,%+.5f]" % (
                tag, K, c["mean"], "*" if c["out_k5"] else " ", c["k5"][0], c["k5"][1],
                g["mean"], "*" if g["out_k5"] else " ", g["k5"][0], g["k5"][1]))

    print("\n### KIEM dnet_coin(f) doc lap f (candidate-baseline_fresh, K=8)")
    for f in FEES:
        print("   f=%.3f  %+.12f" % (f, out["delta"]["candidate-baseline_fresh"]["K8"]["metrics"]["dnet_coin|%.3f" % f]["mean"]))

    print("\n### net/tick SAU size (%equity/tick) @ f=0,006 — 3 cach ap tran")
    for arm in ARMS:
        for K in KS:
            r = out["level"][arm]["K%d" % K]
            print("  %-16s K%-2d  A=%.4f  B95=%.4f  Bmax=%.4f  (size %.3f/%.3f/%.3f)" % (
                arm, K, 100 * r["metrics"]["sized_net_tick|A_mean|0.006"]["mean"],
                100 * r["metrics"]["sized_net_tick|B95|0.006"]["mean"],
                100 * r["metrics"]["sized_net_tick|Bmax|0.006"]["mean"],
                r["size"]["A_mean"], r["size"]["B95"], r["size"]["Bmax"]))

    print("\n### LUAT (f=0,006, K=8, tran 70%)")
    for kk, vv in out["rule"].items():
        if isinstance(vv, dict) and "co_gia_tri_tien" in vv:
            print("  %-32s dgr1dv=%+.5f ci=%s => %s" % (
                kk, vv["dnet_gr1dv"], [round(x, 5) for x in vv["ci"]],
                "CO" if vv["co_gia_tri_tien"] else "KHONG"))
    print("  valid_noise_minus_cand:", out["rule"]["valid_noise_minus_cand"])

    print("\n### PER-SEED dnet_gr1dv @K=8, f=0,006")
    for kk, vv in out["per_seed"].items():
        if "-" in kk:
            print("  %-30s %+.6f raw[%+.6f,%+.6f] k5=[%+.6f,%+.6f] out=%s" % (
                kk, vv["dnet_gr1dv"], vv["raw"][0], vv["raw"][1], vv["k5"][0], vv["k5"][1], vv["out_k5"]))

    # bo mang bootstrap trung gian (_reps/_nk) truoc khi ghi — JSON nho
    for _arm in ARMS:
        for _K in KS:
            out["level"][_arm]["K%d" % _K].pop("_reps", None)
            out["level"][_arm]["K%d" % _K].pop("_nk", None)
    json.dump(out, open(a.out, "w"), indent=1, default=str)
    print("\nJSON -> %s (%.1f KB)" % (a.out, os.path.getsize(a.out) / 1024.0), flush=True)


if __name__ == "__main__":
    main()
