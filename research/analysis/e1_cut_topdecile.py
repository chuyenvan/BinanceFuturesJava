#!/usr/bin/env python3
"""e1_cut_topdecile.py — PREREG_E1_CUT_TOPDECILE (docs/prereg/PREREG_E1_CUT_TOPDECILE.md).

CAT "THAP PHAN VI TREN" cua S1/OFI: bo top-x% coin theo diem (diem chuan hoa chieu: CAO = TOT)
trong tung tick, roi chon top-8 con lai; do lai bang THUOC TANG ENTRY + tang TIEN (net_tick/TF50/asym).

Offline Python, 0 train/sim. DEV only (<= 2025-12-31). KHONG cham 242/ONNX/LIVE. KHONG push du lieu.
CI: block-72h PAIRED, 2000 rep, seed 20260905, inflate(k). Delta vs muc cat 0% (cung ma tran block).

Usage: python3 e1_cut_topdecile.py [--out docs/result/e1_cut_topdecile.json]
"""
import argparse
import json
import os
import sys
import time

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import c3_rates as C                                       # noqa: E402
import model_ruler as MR                                   # noqa: E402

POOL = "/home/ubuntu/mr_kaggle/ds_mr_labels/label_b_pnl.parquet"
SRC = {
    "S1": "/home/ubuntu/ledger/pred_s1a2x1.parquet",
    "ofi_candidate": "/home/ubuntu/s1hpo/kaggle_ofi_train_v2/out/pred_ofi_candidate_v2.parquet",
    "ofi_baseline_fresh": "/home/ubuntu/s1hpo/kaggle_ofi_train_v2/out/pred_baseline_fresh.parquet",
    "ofi_noise": "/home/ubuntu/s1hpo/kaggle_ofi_train_v2/out/pred_ofi_noise_v2.parquet",
}
# 6 doi tuong BINS chi dung de tai lap TAP TICK DUNG CHUNG cua entry_rulers.py (10 doi tuong)
BINS = {
    "45deploy": "/home/ubuntu/claudedata/predwf_G015x26",
    "A44": "/home/ubuntu/ruler_bins/g015p2-arm44-gpu/stage2/A44",
    "A45": "/home/ubuntu/ruler_bins/g015p2-arm44-gpu/stage2/A45",
    "V1": "/home/ubuntu/ruler_bins/g015p2-stage2-featvar-gpu/stage2/V1",
    "V5": "/home/ubuntu/ruler_bins/g015p2-stage2-featvar-gpu/stage2/V5",
    "MRA4": "/tmp/mrbins/MRA4",
}
OBJS = ["S1", "ofi_candidate", "ofi_baseline_fresh", "ofi_noise"]
ORIENT = {o: -1 for o in OBJS}                             # score = -pred => THAP = TOT
CUTS = [0.0, 0.05, 0.10, 0.20]
F = 0.006
K = 8
BLOCK_H = 72
NREP = 2000
SEED = 20260905
K_MAIN = 12                                                # 3 muc cat x 4 doi tuong
K_ALT = 3
H = 3600000
# sanity: RESULT_ENTRY_RULERS §2 (winrate, pnl_vol_norm) @ cut 0%
SANITY = {"S1": (0.7925, 0.1067), "ofi_candidate": (0.7944, 0.1131),
          "ofi_baseline_fresh": (0.7912, 0.1030), "ofi_noise": (0.7921, 0.1075)}
METRICS = ["winrate", "pnl_vol_norm", "net_tick", "TF50", "asym"]
BETTER = {"winrate": 1, "pnl_vol_norm": 1, "net_tick": 1, "TF50": 1, "asym": -1}
# 1 = cao hon TOT ; -1 = thap hon TOT (asym: nho hon = duoi loi nhe hon = TOT)


def log(*a):
    print(*a, flush=True)


def kcut(c):
    return int(np.ceil(c * 32))


def load_pool():
    d = pd.read_parquet(POOL, columns=["ts", "symId", "gross", "exit_ts", "rank"])
    d = d.sort_values(["ts", "rank"], kind="stable").reset_index(drop=True)
    ts = d.ts.to_numpy(np.int64)
    ticks = np.unique(ts)
    return dict(ts=ts, sym=d.symId.to_numpy(np.int64), gross=d.gross.to_numpy(np.float64),
                tick=np.searchsorted(ticks, ts), ticks=ticks)


def map_score(P, path):
    key = P["ts"] * 1024 + P["sym"]
    order = np.argsort(key, kind="stable")
    ks = key[order]
    d = pd.read_parquet(path, columns=["ts", "sym", "score"])
    k = d.ts.to_numpy(np.int64) * 1024 + d.sym.to_numpy(np.int64)
    v = d.score.to_numpy(np.float64)
    del d
    ip = np.clip(np.searchsorted(ks, k), 0, len(ks) - 1)
    hit = ks[ip] == k
    S = np.full(len(key), np.nan)
    S[order[ip[hit]]] = v[hit]
    del k, v, ip, hit, ks, order
    return S


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="docs/result/e1_cut_topdecile.json")
    ap.add_argument("--no-ref10", action="store_true",
                    help="khong tai lap tap tick 10 doi tuong (dung 4 doi tuong) — chi de debug")
    a = ap.parse_args()
    t0 = time.time()
    P = load_pool()
    nt0 = len(P["ticks"])
    log("### pool rows=%d tick=%d sym=%d" % (len(P["gross"]), nt0, len(np.unique(P["sym"]))))
    SC = {}
    for o in OBJS:
        S = map_score(P, SRC[o])
        SC[o] = S * ORIENT[o]                              # CAO = TOT
        log("  ### score %-20s phu=%.2f%%" % (o, 100 * np.isfinite(S).mean()))
    # tick dung chung cho ca 4 doi tuong
    m = np.ones(nt0, bool)
    for o in OBJS:
        m &= np.isfinite(SC[o].reshape(nt0, -1)).all(1)
    if not a.no_ref10:
        # tai lap CHINH XAC tap tick dung chung cua entry_rulers.py (10 doi tuong)
        key = P["ts"] * 1024 + P["sym"]
        order = np.argsort(key, kind="stable")
        ks = key[order]
        for o, dp in BINS.items():
            Fb = np.zeros(len(P["gross"]), bool)
            for f in MR.FOLDS:
                bp = os.path.join(dp, "predict_wf_%s.bin" % f)
                if not os.path.exists(bp):
                    continue
                arr = np.fromfile(bp, dtype=MR.BIN_DT)
                kk = arr["ts"].astype(np.int64) * 1024 + arr["sym"].astype(np.int64)
                ip = np.clip(np.searchsorted(ks, kk), 0, len(ks) - 1)
                hit = ks[ip] == kk
                Fb[order[ip[hit]]] = True
                del arr, kk, ip, hit
            m &= Fb.reshape(nt0, -1).all(1)
            log("  ### ref10 bins %-10s tick_du=%d" % (o, int(m.sum())))
        log("  ### tick dung chung (10 doi tuong, entry_rulers): %d / %d (bo %d)" %
            (int(m.sum()), nt0, nt0 - int(m.sum())))
    ticks = P["ticks"][m]
    log("  ### tick dung chung: %d / %d (bo %d)" % (len(ticks), nt0, nt0 - len(ticks)))
    keep = np.isin(P["ts"], ticks)
    ts = P["ts"][keep]
    t2 = np.unique(ts)
    sym = P["sym"][keep]
    gross = P["gross"][keep]
    tick = np.searchsorted(t2, ts)
    SC = {o: SC[o][keep] for o in OBJS}
    nt = len(t2)
    nx = 32
    log("  ### after filter rows=%d tick=%d" % (len(gross), nt))

    net = gross - F
    GM = gross.reshape(nt, nx)
    NET = net.reshape(nt, nx)
    # sigma_sym: std gross cua coin tren toan mau
    d = pd.DataFrame({"s": sym, "g": gross})
    sd = d.groupby("s")["g"].std().to_dict()
    sig = np.array([sd.get(s, np.nan) for s in sym], np.float64)
    sig = np.where(np.isfinite(sig) & (sig > 1e-9), sig, np.nan).reshape(nt, nx)
    log("  ### sigma_sym finite=%.1f%% median=%.4f" % (100 * np.isfinite(sig).mean(), np.nanmedian(sig)))

    # block bootstrap
    inv = np.unique(t2 // (BLOCK_H * H), return_inverse=True)[1]
    nb = int(inv.max()) + 1
    BI = np.random.default_rng(SEED).integers(0, nb, (NREP, nb))
    tcnt = np.bincount(inv, minlength=nb).astype(np.float64)
    log("  ### blocks(72h)=%d reps=%d seed=%d nt=%d" % (nb, NREP, SEED, nt))

    def blk(v):
        return np.bincount(inv, weights=np.asarray(v, np.float64), minlength=nb)

    def blk_leg(v, idx):
        return np.bincount(idx, weights=np.asarray(v, np.float64), minlength=nb)

    def ci_sum(v, point, k):
        lo, hi = np.percentile(v, 2.5), np.percentile(v, 97.5)
        infl = C.inflate(k)
        ilo, ihi = point - (point - lo) * infl, point + (hi - point) * infl
        orw = bool(lo > 0 or hi < 0)
        oi = bool(ilo > 0 or ihi < 0)
        return {"point": round(float(point), 8), "raw": [round(float(lo), 8), round(float(hi), 8)],
                "infl": [round(float(ilo), 8), round(float(ihi), 8)],
                "out_raw": orw, "out_infl": oi, "out": bool(orw and oi),
                "width": round(float(hi - lo), 8),
                "width_rel": round(float((hi - lo) / abs(point)) if abs(point) > 1e-12 else 1e9, 4),
                "dir": int(np.sign(point))}

    # ---- tinh cho tung (obj, cut) ----
    BL = {}       # (obj,cut) -> dict of per-block numerator/denom arrays
    PT = {}
    for o in OBJS:
        SM = SC[o].reshape(nt, nx)
        order = np.argsort(-SM, axis=1, kind="stable")
        for c in CUTS:
            kc = kcut(c)
            sel = order[:, kc:kc + K]
            sn = np.take_along_axis(NET, sel, axis=1)      # (nt,K)
            ss = np.take_along_axis(sig, sel, axis=1)
            pos_t = (sn > 0).sum(1).astype(np.float64)
            pvn_t = np.nansum(np.where(np.isfinite(ss), sn / ss, 0.0), axis=1)
            sn_t = sn.sum(1)
            flat = sn.reshape(-1)
            ft = np.repeat(np.arange(nt), K)
            ftb = inv[ft]
            N = flat.size
            rk = np.argsort(np.argsort(flat, kind="stable"), kind="stable")
            keep50 = rk < N - int(np.ceil(0.5 * N))
            kh = np.where(keep50, flat, 0.0)
            neg = flat < 0
            LL = np.where(neg, -flat, 0.0)
            WW = np.where(~neg & (flat != 0), flat, 0.0)
            BL[(o, c)] = {
                "pos": blk(pos_t), "cnt": K * tcnt,
                "pvn": blk(pvn_t),
                "sn": blk(sn_t),
                "tf50": blk_leg(kh, ftb),
                "ll": blk_leg(LL, ftb), "ln": blk_leg(neg.astype(np.float64), ftb),
                "ww": blk_leg(WW, ftb), "wn": blk_leg((flat > 0).astype(np.float64), ftb),
            }
            PT[(o, c)] = {
                "winrate": float(pos_t.sum() / (K * nt)),
                "pnl_vol_norm": float(pvn_t.sum() / (K * nt)),
                "net_tick": float(sn_t.sum() / nt),
                "TF50": float(kh.sum()),
                "asym": float((LL.sum() / max(neg.sum(), 1)) / (WW.sum() / max((flat > 0).sum(), 1))),
            }
        del SM, order
        log("  ### calc %s %.0fs" % (o, time.time() - t0))

    def rep(o, c, r):
        b = BL[(o, c)]
        if r == "winrate":
            return b["pos"][BI].sum(1) / b["cnt"][BI].sum(1)
        if r == "pnl_vol_norm":
            return b["pvn"][BI].sum(1) / b["cnt"][BI].sum(1)
        if r == "net_tick":
            return b["sn"][BI].sum(1) / nt
        if r == "TF50":
            return b["tf50"][BI].sum(1)
        if r == "asym":
            return (b["ll"][BI].sum(1) / b["ln"][BI].sum(1)) / (b["ww"][BI].sum(1) / b["wn"][BI].sum(1))

    res = {"prereg": "PREREG_E1_CUT_TOPDECILE.md", "f": F, "K": K, "block_h": BLOCK_H,
           "nrep": NREP, "seed": SEED, "k_main": K_MAIN, "k_alt": K_ALT,
           "infl_main": C.inflate(K_MAIN), "infl_alt": C.inflate(K_ALT),
           "cuts": CUTS, "kcut": {str(c): kcut(c) for c in CUTS},
           "n_tick": nt, "n_leg": len(gross), "objs": OBJS,
           "level": {}, "delta": {}, "sanity": {}, "verdict": {}}
    for o in OBJS:
        res["level"][o] = {str(c): {r: ci_sum(rep(o, c, r), PT[(o, c)][r], K_ALT) for r in METRICS}
                           for c in CUTS}
        res["sanity"][o] = {}
        for r, i in (("winrate", 0), ("pnl_vol_norm", 1)):
            got = PT[(o, 0.0)][r]
            res["sanity"][o][r] = {"got": round(got, 6), "want": SANITY[o][i],
                                   "ok": bool(abs(got - SANITY[o][i]) <= 1e-4)}
    # delta vs cut 0%
    for o in OBJS:
        for c in CUTS[1:]:
            key = "%s|%d%%" % (o, int(c * 100))
            res["delta"].setdefault(key, {})
            for r in METRICS:
                dd = rep(o, c, r) - rep(o, 0.0, r)
                ptd = PT[(o, c)][r] - PT[(o, 0.0)][r]
                res["delta"][key][r] = ci_sum(dd, ptd, K_MAIN)
    # verdict theo luat §6
    san_ok = all(v["ok"] for o in OBJS for v in res["sanity"][o].values())
    res["sanity_all_ok"] = bool(san_ok)
    V = {}
    for o in OBJS:
        V[o] = {}
        for c in CUTS[1:]:
            key = "%s|%d%%" % (o, int(c * 100))
            dn = res["delta"][key]["net_tick"]
            dw = res["delta"][key]["winrate"]
            dp = res["delta"][key]["pnl_vol_norm"]
            a_ok = bool(dn["out"] and dn["dir"] > 0)
            b_ok = ((not dw["out"]) or dw["dir"] > 0) and ((not dp["out"]) or dp["dir"] > 0)
            V[o][str(c)] = {"a_net_tick_tot_ngoaiCI": a_ok, "b_wr_pvn_khong_xau": b_ok,
                            "THAT": bool(a_ok and b_ok)}
    res["verdict"] = {"per": V,
                      "any_TRUE": bool(any(v["THAT"] for o in V for v in V[o].values())),
                      "any_a": bool(any(v["a_net_tick_tot_ngoaiCI"] for o in V for v in V[o].values()))}
    with open(a.out, "w") as fh:
        json.dump(res, fh, separators=(",", ":"), default=str)
    log("### JSON -> %s (%.1f KB) | %.0fs" % (a.out, os.path.getsize(a.out) / 1e3, time.time() - t0))
    # ---- stdout tom tat ----
    log("\n=== SANITY cut 0% (winrate, pnl_vol_norm) ===")
    for o in OBJS:
        log("  %-20s %s" % (o, res["sanity"][o]))
    log("\n=== LEVEL (cut x metric) ===")
    for c in CUTS:
        log("-- cut %d%% (k_cut=%d)" % (int(c * 100), kcut(c)))
        for o in OBJS:
            log("   %-20s %s" % (o, " ".join("%s=%+.5f" % (r, PT[(o, c)][r]) for r in METRICS)))
    log("\n=== DELTA vs 0%% (ngoai CI raw&infl k=%d ?) ===" % K_MAIN)
    for key in res["delta"]:
        log("  %-24s %s" % (key, " ".join(
            "%s=%+.5f%s" % (r, res["delta"][key][r]["point"],
                            "*" if res["delta"][key][r]["out"] else "") for r in METRICS)))
    log("\n=== VERDICT ===")
    for o in OBJS:
        log("  %-20s %s" % (o, V[o]))
    log("  any_a=%s any_TRUE=%s" % (res["verdict"]["any_a"], res["verdict"]["any_TRUE"]))


if __name__ == "__main__":
    main()
