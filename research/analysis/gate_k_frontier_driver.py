#!/usr/bin/env python3
"""gate_k_frontier_driver.py -- GATE x K FRONTIER (P0.a: hieu chinh iso-n offline).

Pre-reg: docs/prereg/PREREG_GATE_K_FRONTIER.md (commit 7b899e6e). Brief: Claude outputs/BRIEF_GATE_K_FRONTIER_20261006.md.
P0.a: voi moi (K, target_n/nam), tim pct sao cho so LENH UOC TINH (symbol_pass * ratio) lech <=3% target.
  - ratio lệnh/pass lay tu sim tham chieu n700-a1 (K24 base): n/nam 732.2, offline symbol_pass 2022-2025 = 2653.
  - Thuần offline, 0 PnL, 0 Java/sim/Kaggle. Seed 42 (A1). Reuse tree TopTree de bisect nhanh.
Output: docs/audit/GATE_OFFLINE_ISON_CALIB.json
"""
import json
import logging
import math
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
import gate_offline as G  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("g_k_frontier")

# target n/nam (brief §4 Phase 1). iso-740 = giu nen (~740); iso-1000 = tang n.
ARMS = [("iso-740", 12, 740), ("iso-740", 16, 740), ("iso-740", 32, 740), ("iso-740", 40, 740),
        ("iso-1000", 16, 1000), ("iso-1000", 24, 1000), ("iso-1000", 32, 1000), ("iso-1000", 40, 1000)]
RHO_BASE = 4.9171e-5
REF_N_YR = 732.2           # n700-a1 n/nam (held-rerank result)
JOUT = "/home/ubuntu/src/BinanceFuturesJava/docs/audit/GATE_OFFLINE_ISON_CALIB.json"


def build_candidates(K):
    """Candidates cho A1 (seed 42) voi top-K, cache K_CACHE=48 slice :K."""
    G.K = K
    B = dict(np.load(G.CACHE + "/cand_base.npz"))
    mp = pd.read_csv(G.MAPF)
    s2id = dict(zip(mp.symbol.astype(str).str.replace("USDT$", "", regex=True), mp.symId.astype(int)))
    C = G.build("A1", B, s2id)
    ts, p, SP, valid = C["ts"], C["p15"], C["SP"], C["valid"]
    fac = np.maximum(G.DYN_MIN, (SP / G.SCORE_BASE) * G.DYN_MULT)
    r = p[:, None] / (fac * G.GS)
    rows, cols = np.nonzero(valid)
    vals = r[rows, cols]
    hv = (ts // G.H)[rows]
    first = int(ts[rows[0]])
    ctx = G.mk_tree(vals, hv, 1024)          # reuse qua moi pct
    return C, vals, hv, first, ctx, fac, valid


def symbol_pass_4yr(C, vals, hv, first, ctx, fac, valid, pct):
    q, qh, _ = G.hourly_q(vals, hv, first, 90, float(pct), 1024, ctx)
    warm_h = np.isnan(q)
    qq = np.where(warm_h, G.BASE, q).astype(np.float32)
    idx = np.clip(np.searchsorted(qh, C["ts"] // G.H), 0, len(qh) - 1)
    qm = qq[idx]
    thr = (qm[:, None] * fac) * G.GS
    would = ~np.isnan(C["SP"]) & ~(C["p15"][:, None] < thr)
    P = valid & would
    yr = C["yr"]
    tot = 0
    for y in G.YEARS:
        tot += int(P[yr == y].sum())
    return tot


def est_n_per_yr(sp4, ratio):
    return sp4 * ratio / 4.0


def calibrate():
    # 1) reference ratio (chay 1 lan K24 base)
    C24, vals, hv, first, ctx, fac, valid = build_candidates(24)
    ref_sp = symbol_pass_4yr(C24, vals, hv, first, ctx, fac, valid, G.PCT)
    ratio = REF_N_YR * 4.0 / ref_sp
    log.info("REF K24 base: symbol_pass_4yr=%d -> ratio lenh/pass=%.4f (n/nam %.1f)", ref_sp, ratio, REF_N_YR)

    out = dict(meta=dict(script="gate_k_frontier_driver.calibrate", seed=42, arm="A1",
                         ref_n_yr=REF_N_YR, ref_symbol_pass_4yr=ref_sp, ratio=round(ratio, 6)), arms={})
    for name, K, target in ARMS:
        Ck, vals, hv, first, ctx, fac, valid = build_candidates(K)
        target_sp = target * 4.0 / ratio
        pct = 1 - RHO_BASE * 24.0 / K * (target / 740.0)   # estimate dau (brief §P0.a)
        # bisect pct: est_n giam khi pct tang (monotone)
        lo, hi = 0.99980, 0.999999
        best = pct
        best_dev = None
        for _ in range(25):
            sp = symbol_pass_4yr(Ck, vals, hv, first, ctx, fac, valid, pct)
            n_est = est_n_per_yr(sp, ratio)
            dev = (n_est - target) / target
            if best_dev is None or abs(dev) < abs(best_dev):
                best, best_dev = pct, dev
            if abs(dev) <= 0.03:
                best, best_dev = pct, dev
                break
            if n_est > target:      # qua nhieu lenh -> tang pct (chat hon)
                lo = pct
            else:
                hi = pct
            pct = 0.5 * (lo + hi)
        sp_f = symbol_pass_4yr(Ck, vals, hv, first, ctx, fac, valid, best)
        n_f = est_n_per_yr(sp_f, ratio)
        out["arms"]["%s_K%d" % (name, K)] = dict(name=name, K=K, target_n=target,
                                                 pct=round(best, 9), symbol_pass_4yr=sp_f,
                                                 est_n_yr=round(n_f, 2),
                                                 dev_pct=round(100.0 * (n_f - target) / target, 2))
        log.info("%s K%-2d: pct=%.9f sp4=%d est_n=%.1f dev=%.2f%%", name, K, best, sp_f, n_f,
                 100.0 * (n_f - target) / target)
        del Ck, vals, hv, ctx, fac, valid
    with open(JOUT, "w") as f:
        json.dump(G.tojs(out), f, indent=1, ensure_ascii=False)
    log.info("ghi %s", JOUT)
    print(json.dumps(out["arms"], indent=1))


if __name__ == "__main__":
    calibrate()
