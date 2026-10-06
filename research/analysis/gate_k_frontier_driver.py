#!/usr/bin/env python3
"""gate_k_frontier_driver.py -- GKF P0.a: hieu chinh iso-n offline (THUC THI: claw).

Pre-reg: docs/prereg/PREREG_GATE_K_FRONTIER.md (MASTER, commit 4e4fc975). Brief: Claude outputs/BRIEF_GATE_K_FRONTIER_20261006.md.
Quy tac (§4 P0.a, CO DINH):
  - pass_target(n_t) = pass_NEN_s42 * n_t / 736, n_t in {736, 1000}.
  - Tim pct sao cho pass offline 2022-2025 lech <= 1% pass_target (bisection tren rho=1-pct,
    khoi tao rho0 = 4.9171e-5 * 24/K * n_t/736). Lam tron pct 9 chu so.
  - Validate (truoc khi dung): offline pass lech <= 2% so sim o n700-a1, n700-a2, NEN seed 42.
Xuat: docs/audit/GATE_OFFLINE_ISON_CALIB.json + bang ADDENDUM-1.
Thuan offline, 0 PnL, 0 Java/sim/Kaggle. Seed 42 (A1).
"""
import json
import logging
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
import gate_offline as G  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("g_k_frontier")

N_BASE = 736
RHO_BASE = 4.9171e-5
ARMS = [("iso-736", 12, 736), ("iso-736", 16, 736), ("iso-736", 32, 736), ("iso-736", 40, 736),
        ("iso-1000", 16, 1000), ("iso-1000", 24, 1000), ("iso-1000", 32, 1000), ("iso-1000", 40, 1000)]
P0B = ("P0.b-K48", 48, 1000)     # P0.b: K48 @ pct iso-1000 (chan doan, khong cham GO)
JOUT = "/home/ubuntu/src/BinanceFuturesJava/docs/audit/GATE_OFFLINE_ISON_CALIB.json"
REF = [("n700-a1", 24, 0.999950829, "n700-a1"), ("n700-a2", 16, 0.99985, "n700-a2"),
       ("gqsf-a1", 24, 0.999950829, "gqsf-a1")]


def build_candidates(K, pd_tag=None):
    """Candidates cho A1 (seed 42) voi top-K (cache K_CACHE=48, slice :K). pd_tag = nguon printDone lock."""
    G.K = K
    B = dict(np.load(G.CACHE + "/cand_base.npz"))
    mp = pd.read_csv(G.MAPF)
    s2id = dict(zip(mp.symbol.astype(str).str.replace("USDT$", "", regex=True), mp.symId.astype(int)))
    C = G.build("A1", B, s2id, pd_tag)
    ts, p, SP, valid = C["ts"], C["p15"], C["SP"], C["valid"]
    fac = np.maximum(G.DYN_MIN, (SP / G.SCORE_BASE) * G.DYN_MULT)
    r = p[:, None] / (fac * G.GS)
    rows, cols = np.nonzero(valid)
    vals = r[rows, cols]
    hv = (ts // G.H)[rows]
    first = int(ts[rows[0]])
    ctx = G.mk_tree(vals, hv, 1024)
    return C, vals, hv, first, ctx, fac, valid


def gate_passes(C, vals, hv, first, ctx, fac, valid, pct):
    q, qh, _ = G.hourly_q(vals, hv, first, 90, float(pct), 1024, ctx)
    qq = np.where(np.isnan(q), G.BASE, q).astype(np.float32)
    idx = np.clip(np.searchsorted(qh, C["ts"] // G.H), 0, len(qh) - 1)
    thr = (qq[idx][:, None] * fac) * G.GS
    would = ~np.isnan(C["SP"]) & ~(C["p15"][:, None] < thr)
    return valid & would


def pass_2225(C, P):
    s = (C["yr"] >= 2022) & (C["yr"] <= 2025)
    return int(P[s].sum())


def k_eff(C, K):
    nc = (~np.isnan(C["SP"])).sum(1)
    return dict(mean=round(float(nc.mean()), 3), p50=int(np.percentile(nc, 50)),
                frac_tick_lt_K=round(float((nc < K).mean()), 5))


def validate():
    out = {}
    for tag, K, pct, pt in REF:
        C, vals, hv, first, ctx, fac, valid = build_candidates(K, pt)
        P = gate_passes(C, vals, hv, first, ctx, fac, valid, pct)
        sl = G.simlog(tag)
        pa = int(P.sum())
        out[tag] = dict(K=K, pct=pct, off_pass_all=pa, sim_pass=sl["pass_"],
                        dev_pct=round(100.0 * (pa - sl["pass_"]) / max(1, sl["pass_"]), 3),
                        ok=abs(pa - sl["pass_"]) / max(1, sl["pass_"]) <= 0.02)
        log.info("VALIDATE %s K%d: off %d vs sim %d = %+.3f%% => %s", tag, K, pa, sl["pass_"],
                 out[tag]["dev_pct"], "OK" if out[tag]["ok"] else "FAIL")
        del C, vals, hv, ctx, fac, valid
    return out


def calibrate():
    C, vals, hv, first, ctx, fac, valid = build_candidates(24)
    P = gate_passes(C, vals, hv, first, ctx, fac, valid, G.PCT)
    pass_base = pass_2225(C, P)
    log.info("pass_NEN_s42 (K24 base, 2022-2025) = %d", pass_base)
    del C, vals, hv, ctx, fac, valid, P

    out = dict(meta=dict(script="gate_k_frontier_driver", seed=42, arm="A1", pass_nen_s42=pass_base,
                         n_base=N_BASE, rho_base=RHO_BASE), arms={})
    for name, K, n_t in ARMS + [P0B]:
        C, vals, hv, first, ctx, fac, valid = build_candidates(K)
        target = pass_base * n_t / N_BASE
        rho0 = RHO_BASE * 24.0 / K * (n_t / N_BASE)
        lo, hi = 0.99, 0.999999999
        pct = 1.0 - rho0
        best, best_dev = pct, None
        for _ in range(48):
            p = pass_2225(C, gate_passes(C, vals, hv, first, ctx, fac, valid, pct))
            dev = (p - target) / target
            if best_dev is None or abs(dev) < abs(best_dev):
                best, best_dev = pct, dev
            if abs(dev) <= 0.01:
                break
            if p > target:
                lo = max(lo, pct)
            else:
                hi = min(hi, pct)
            pct = 0.5 * (lo + hi)
        pct_r = round(best, 9)
        P = gate_passes(C, vals, hv, first, ctx, fac, valid, pct_r)
        p4 = pass_2225(C, P)
        ke = k_eff(C, K)
        mins = {int(y): int(P[(C["yr"] == y)].any(1).sum()) for y in G.YEARS}
        out["arms"]["%s_K%d" % (name, K)] = dict(
            name=name, K=K, n_t=n_t, pct=("%.9f" % pct_r), pass_target=round(target, 1), pass_2225=p4,
            dev_pct=round(100.0 * (p4 - target) / target, 2), reached=abs(p4 - target) / target <= 0.01,
            minute_open_per_year=mins, minutes_open_2225=sum(mins.values()), k_eff=ke)
        log.info("%s K%-2d n_t=%d: pct=%.9f pass4=%d target=%.0f dev=%+.2f%% %s | K_eff=%.1f (%.1f%% tick<K)",
                 name, K, n_t, pct_r, p4, target, 100.0 * (p4 - target) / target,
                 "" if abs(p4 - target) / target <= 0.01 else "(FLOOR/unreach)", ke["mean"],
                 100.0 * ke["frac_tick_lt_K"])
        del C, vals, hv, ctx, fac, valid, P
    return out


if __name__ == "__main__":
    st = sys.argv[1] if len(sys.argv) > 1 else "all"
    out = {}
    if st in ("validate", "all"):
        out["validate"] = validate()
    if st in ("calibrate", "all"):
        out.update(calibrate())
    with open(JOUT, "w") as f:
        json.dump(G.tojs(out), f, indent=1, ensure_ascii=False)
    log.info("ghi %s", JOUT)
    print(json.dumps(out, indent=1, ensure_ascii=False))
