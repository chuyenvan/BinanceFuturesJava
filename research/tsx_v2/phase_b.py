#!/usr/bin/env python3
"""TSX_V2 Phase B theo PREREG_TSX_V2 (commit 6b7ab1a8). Replay DEV 8 seed, direct dPnL/seed so X14.
B1 tran 336/420h; B2 rho<=1.5/2.5; B3 reb<0.10/0.20; B4 thr{-0.25,-0.30,-0.35} x L{20,30,45}. Kiem K1-K7 truoc khi bao.
"""
import json
import logging
import sys

import numpy as np
import pandas as pd

import common as CM
import engine as EN

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("B")
OUTD = CM.D + "/out"
PREREG = "6b7ab1a8"
NS = len(CM.SEEDS)


def b3_days(eod, base_days, r):
    bs = set(base_days)
    out = []
    for D in base_days:
        F = D
        while F - pd.Timedelta(days=1) in bs:
            F -= pd.Timedelta(days=1)
        seg = eod[(eod.index >= F - pd.Timedelta(days=1)) & (eod.index <= D - pd.Timedelta(days=1))]
        reb = np.exp(eod.get(D - pd.Timedelta(days=1)) - seg.min()) - 1
        if reb < r:
            out.append(D)
    return out


def main():
    C, keys, arr, fund = CM.load_all()
    tk = CM.ticks()
    W = CM.Wins(keys, arr, fund, tk, True, CM.nofund_syms(C))
    eod = CM.ew_eod()
    base, ok = CM.base_flags_check(eod)
    assert ok
    eps = CM.episodes(eod)
    A = pd.read_pickle(CM.D + "/cache/phaseA.pkl")
    X = C[C["arm"] == "X14"].reset_index(drop=True)
    assert len(A) == len(X) and (A["sym"].to_numpy() == X["sym"].to_numpy()).all() and (A["te"].to_numpy() == X["te"].to_numpy()).all()
    rho = A["rho"].to_numpy()
    full = np.ones(len(X), bool)
    V = {}  # name -> (days, cap_j, eligible mask, family)
    V["BASE"] = (base, CM.CAP504, full, "base")
    V["B1a_336h"] = (base, 336 * 60, full, "B1")
    V["B1b_420h"] = (base, 420 * 60, full, "B1")
    V["B2a_k1.5"] = (base, CM.CAP504, rho <= 1.5, "B2")
    V["B2b_k2.5"] = (base, CM.CAP504, rho <= 2.5, "B2")
    V["B3a_r0.10"] = (b3_days(eod, base, 0.10), CM.CAP504, full, "B3")
    V["B3b_r0.20"] = (b3_days(eod, base, 0.20), CM.CAP504, full, "B3")
    for thr in (-0.25, -0.30, -0.35):
        for L in (20, 30, 45):
            V["B4_%.2f_%d" % (thr, L)] = (CM.flag_days(eod, thr, L), CM.CAP504, full, "B4")
    # kiem (khong dem ledger)
    K = {"K_B1_504": (base, CM.CAP504, full), "K_B3_inf": (b3_days(eod, base, np.inf), CM.CAP504, full),
         "K_B2_inf": (base, CM.CAP504, rho <= np.inf)}

    def run(days, cap, elig):
        ds = CM.dayints(days)
        out = np.empty(len(X))
        jj = np.empty(len(X), np.int64)
        op = 0
        for i, r in enumerate(X.itertuples()):
            res = EN.replay(W.get(r.wid), r.legs, dayset=ds, cap_j=cap, eligible=bool(elig[i]))
            out[i], jj[i] = res["pnl"], res["j"]
            op += int(res["open"])
        return out, jj, op

    P, J, OP = {}, {}, {}
    for k, (d, cap, el, fam) in V.items():
        P[k], J[k], OP[k] = run(d, cap, el)
        log.info("chay %s: %d ngay ON, open %d", k, len(d), OP[k])
    pcut = A["pnl_cut"].to_numpy()
    chk = dict(K1_vs_phaseA=float(np.abs(P["BASE"] - A["pnl_x14"].to_numpy()).max()),
               K1_vs_printDone_rel_ok=float(np.mean(np.abs(P["BASE"] - X["pnl"].to_numpy()) <= 1e-3 * np.maximum(np.abs(X["pnl"].to_numpy()), 1))),
               K2_B4_base_identical=bool(np.array_equal(P["B4_-0.30_30"], P["BASE"]) and np.array_equal(J["B4_-0.30_30"], J["BASE"])),
               K7_open=int(sum(OP.values())))
    for k, (d, cap, el) in K.items():
        p, j, _ = run(d, cap, el)
        chk[k] = bool(np.array_equal(p, P["BASE"]) and np.array_equal(j, J["BASE"]))
    chk["K6_on_days"] = {k: len(v[0]) for k, v in V.items()}
    log.info("KIEM %s", chk)
    assert chk["K1_vs_phaseA"] <= 1e-6 and chk["K1_vs_printDone_rel_ok"] == 1.0 and chk["K2_B4_base_identical"]
    assert chk["K_B1_504"] and chk["K_B3_inf"] and chk["K_B2_inf"] and chk["K7_open"] == 0
    seeds = X["seed"].to_numpy()
    ep = A["ep"].to_numpy()
    lab = {i: "%s..%s" % (a.strftime("%Y-%m-%d"), b.strftime("%Y-%m-%d")) for i, (a, b) in enumerate(eps)}
    iL = next(i for i, (a, b) in enumerate(eps) if a <= pd.Timestamp("2022-05-12") <= b)
    i6 = next(i for i, (a, b) in enumerate(eps) if a <= pd.Timestamp("2024-06-25") <= b)
    xd = P["BASE"] - pcut
    defm = A["deferred"].to_numpy()
    D_L = float(xd[defm & (ep == iL)].sum() / NS)
    D_6 = float(xd[defm & (ep == i6)].sum() / NS)
    log.info("X14 direct LUNA %.1f 06/2024 %.1f (Phase A: +1625 / -249)", D_L, D_6)
    rng = np.random.default_rng(20261022)
    R = dict(prereg=PREREG, checks=chk, x14_direct_luna=D_L, x14_direct_0624=D_6, ep_luna=lab[iL], ep_0624=lab[i6], variants={})
    cl = pd.DataFrame(dict(seed=seeds, sym=X["sym"], te=X["te"], ep=[lab.get(e, "-") for e in ep], pnl_x14=P["BASE"], pnl_cut=pcut))
    for k in V:
        d = P[k] - P["BASE"]
        cl["d_" + k] = d
        aff = (np.abs(d) > 1e-9) | (J[k] != J["BASE"])
        assert not (aff & (ep < 0)).any(), "cum ngoai dot bi anh huong"
        ps = {s: float(d[seeds == s].sum()) for s in CM.SEEDS}
        tot = float(np.mean(list(ps.values())))
        de = {}
        for e in sorted(set(ep[aff])):
            de[e] = float(d[ep == e].sum() / NS)
        loo = {lab[e]: tot - v for e, v in de.items()}
        units = np.array(list(de.values())) if de else np.zeros(0)
        if len(units):
            bs = rng.choice(units, size=(10000, len(units)), replace=True).sum(axis=1)
            ci = [float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))]
        else:
            ci = [0.0, 0.0]
        dP0 = P[k] - pcut
        psP0 = {s: float(dP0[seeds == s].sum()) for s in CM.SEEDS}
        R["variants"][k] = dict(family=V[k][3], on_days=len(V[k][0]), delta_mean=tot, delta_seed=ps,
                                n_pos_seed=int(sum(v > 0 for v in ps.values())),
                                n_aff_seed=float(aff.sum() / NS), delta_ep={lab[e]: v for e, v in de.items()},
                                loo_min=float(min(loo.values())) if loo else 0.0, loo_min_ep=min(loo, key=loo.get) if loo else None,
                                n_ep=len(de), ci95=ci, d_luna=float(de.get(iL, 0.0)), d_0624=float(de.get(i6, 0.0)),
                                dP0_mean=float(np.mean(list(psP0.values()))), dP0_npos=int(sum(v > 0 for v in psP0.values())),
                                dP0_seed=psP0)
    # luat chon B1-B3
    fam = {"B1": ["B1a_336h", "B1b_420h"], "B2": ["B2a_k1.5", "B2b_k2.5"], "B3": ["B3a_r0.10", "B3b_r0.20"]}
    cands = []
    for f, ks in fam.items():
        for k in ks:
            v = R["variants"][k]
            other = [x for x in ks if x != k][0]
            c = dict(i=v["n_pos_seed"] == 8, ii=v["loo_min"] > 1e-6 and v["n_ep"] > 0, iii=v["ci95"][0] > 0,
                     iv=v["d_luna"] >= -0.20 * abs(D_L) and v["d_0624"] >= -0.20 * abs(D_6),
                     v=R["variants"][other]["delta_mean"] > 0)
            v["rule"] = c
            v["candidate"] = bool(all(c.values()))
            if v["candidate"]:
                cands.append(k)
    pick = max(cands, key=lambda k: R["variants"][k]["delta_mean"]) if cands else None
    R["candidates"] = cands
    R["pick"] = pick
    # B4 plateau
    g = {}
    for thr in (-0.25, -0.30, -0.35):
        for L in (20, 30, 45):
            v = R["variants"]["B4_%.2f_%d" % (thr, L)]
            g["%.2f/%d" % (thr, L)] = dict(d=v["delta_mean"], dP0=v["dP0_mean"], dP0_npos=v["dP0_npos"], on=v["on_days"], aff=v["n_aff_seed"])
    nb = ["-0.30/30", "-0.25/30", "-0.35/30", "-0.30/20", "-0.30/45"]
    R["B4_grid"] = g
    R["B4_plateau_ok"] = bool(all(g[x]["dP0"] > 0 and g[x]["dP0_npos"] == 8 for x in nb))
    json.dump(R, open(OUTD + "/phaseB.json", "w"), indent=1, default=str)
    cl.to_csv(OUTD + "/phaseB_clusters.csv", index=False)
    for k, v in R["variants"].items():
        log.info("%-14s ON %3d | d %+8.1f (%d/8) aff %6.1f | LOO min %+8.1f [%s] | CI95 [%+.0f, %+.0f] n_ep %d | LUNA %+7.1f 06/24 %+7.1f | dP0 %+8.1f (%d/8) %s %s",
                 k, v["on_days"], v["delta_mean"], v["n_pos_seed"], v["n_aff_seed"], v["loo_min"], v["loo_min_ep"], v["ci95"][0], v["ci95"][1],
                 v["n_ep"], v["d_luna"], v["d_0624"], v["dP0_mean"], v["dP0_npos"], v.get("rule", ""), "CAND" if v.get("candidate") else "")
    log.info("ung vien %s -> chon %s | B4 plateau %s", cands, pick, R["B4_plateau_ok"])


if __name__ == "__main__":
    main()
