#!/usr/bin/env python3
"""R1 cham C1 (A0 - A1 NET, 8 cap), C2 (A0 - A2 RND, 4 cap), C3 (A1 - A2, chi bao cao) theo PREREG_R1_S1_ABLATION §6
(44acf9cd + ADD1 ce321bd3 + ADD2 93b60422). MTM nhu r1_score (gvz_mtm, kline1m tai lai), A0 = cache tsx (G-P0 PASS).
C1 'S1 CON dong gop': mean dCAGR22 > 0, can duoi CI95 > 0, >= 6/8 seed duong, >= 3/4 nam 2022-25 duong
   (nam: mean qua seed cua chenh loi nhuan nam roi_year; bao kem chenh sum_pnl nam).
C1 'S1 KHONG con dong gop': TOST — CI90 paired-t nam trong [-1.5; +1.5] pp. Con lai: KHONG KET LUAN.
C2: can duoi CI95 (A0 - A2) > 0 => thu tu selector con la lever o K24."""
import json
import logging
import math
import os
import sys

import numpy as np

sys.path.insert(0, "/home/ubuntu/claude_master/res1109/r1_s1")
import r1_score as S  # noqa: E402  (patch kp -> kl/, import R/F3/N/MT)

R, F3, N, MT = S.R, S.F3, S.N, S.MT
D = S.D
log = logging.getLogger("r1score2")
SEEDS8 = S.SEEDS
SEEDS4 = ["A1", "S7", "S13", "S21"]
T975 = {3: 3.182, 7: 2.365}
T95 = {3: 2.353, 7: 1.895}
F = ("cagr22", "dd_mtm22", "calmar22", "uw_mtm22", "n_per_year", "sum_pnl_2022_25")


def ci(x, t):
    n = len(x)
    hw = t[n - 1] * float(np.std(x, ddof=1)) / math.sqrt(n)
    return [float(np.mean(x) - hw), float(np.mean(x) + hw)]


def main():
    assert R._work is MT._work_vision
    st = json.load(open(D + "/orch2_state.json"))["done"]
    s1 = [s for s in SEEDS8 if st.get("r1-a1-" + s.lower(), {}).get("valid")]
    s2 = [s for s in SEEDS4 if st.get("r1-a2-" + s.lower(), {}).get("valid")]
    log.info("A1 hop le %s | A2 hop le %s", s1, s2)
    keys = {}
    for s in SEEDS8:
        keys["A0_" + s] = "tsx-x14-" + s.lower()
    for s in s1:
        keys["A1_" + s] = "r1-a1-" + s.lower()
    for s in s2:
        keys["A2_" + s] = "r1-a2-" + s.lower()
    for k, t in keys.items():
        N.TAG[k], N.DESC[k] = t, "R1 " + k
    legs = {k: R.load_legs(t) for k, t in keys.items()}
    daily = {k: R.load_daily(t) for k, t in keys.items()}
    md5 = {k: R.md5_of(t) for k, t in keys.items()}
    mf = D + "/mtm_r1.json"
    raw = json.load(open(mf)) if os.path.exists(mf) else {}
    tsx = json.load(open("/home/ubuntu/claude_master/tsx/mtm_vision.json"))
    for s in SEEDS8:
        assert tsx["X14_" + s]["md5"] == md5["A0_" + s]
        raw["A0_" + s] = tsx["X14_" + s]
    miss = {k: legs[k] for k in keys if k not in raw or raw[k].get("md5") != md5[k]}
    log.info("MTM can tinh: %s", sorted(miss))
    if miss:
        new = R.run_mtm(miss, workers=3, chunk=30)
        for k, v in new.items():
            v["md5"] = md5[k]
            raw[k] = v
        json.dump(raw, open(mf, "w"))
    assert all(raw[k]["legacy"]["missing"] == 0 for k in keys), "MTM thieu gia"
    M = {k: N.arm_metrics(R, F3, k, legs[k], daily[k], raw[k]["legacy"]) for k in keys}
    out = dict(prereg=["44acf9cd", "ce321bd3", "93b60422"], seeds_A1=s1, seeds_A2=s2)

    def pair(a, b, seeds, t):
        d = np.array([M[a + "_" + s]["cagr22"] - M[b + "_" + s]["cagr22"] for s in seeds])
        dd = np.array([M[a + "_" + s]["dd_mtm22"] - M[b + "_" + s]["dd_mtm22"] for s in seeds])
        yr = {y: float(np.mean([M[a + "_" + s]["roi_year"].get(y, np.nan) - M[b + "_" + s]["roi_year"].get(y, np.nan)
                                for s in seeds])) for y in (2022, 2023, 2024, 2025)}
        yp = {y: float(np.mean([M[a + "_" + s]["per_year"][y]["sum_pnl"] - M[b + "_" + s]["per_year"][y]["sum_pnl"]
                                for s in seeds])) for y in (2022, 2023, 2024, 2025)}
        return dict(n=len(seeds), mean=float(d.mean()), ci95=ci(d, T975), ci90=ci(d, T95), per_seed=d.tolist(),
                    pos=int((d > 0).sum()), dDD_mean=float(dd.mean()), dDD_ci95=ci(dd, T975), d_roi_year=yr,
                    d_pnl_year=yp, years_pos=int(sum(v > 0 for v in yr.values())))

    if len(s1) == 8:
        c1 = pair("A0", "A1", s1, None)
        con = c1["mean"] > 0 and c1["ci95"][0] > 0 and c1["pos"] >= 6 and c1["years_pos"] >= 3
        khong = c1["ci90"][0] >= -1.5 and c1["ci90"][1] <= 1.5
        c1["verdict"] = "S1 CON DONG GOP" if con else ("S1 KHONG CON DONG GOP" if khong else "KHONG KET LUAN")
        out["C1"] = c1
        log.info("C1 %s mean=%.2f ci95=%s ci90=%s pos=%d/8 years_pos=%d d_roi_year=%s dDD=%.2f", c1["verdict"], c1["mean"],
                 [round(x, 2) for x in c1["ci95"]], [round(x, 2) for x in c1["ci90"]], c1["pos"], c1["years_pos"],
                 {y: round(v, 2) for y, v in c1["d_roi_year"].items()}, c1["dDD_mean"])
    if len(s2) == 4:
        c2 = pair("A0", "A2", s2, None)
        c2["verdict"] = "THU TU SELECTOR CON LA LEVER" if c2["ci95"][0] > 0 else "KHONG CHUNG MINH DUOC"
        out["C2"] = c2
        log.info("C2 %s mean=%.2f ci95=%s pos=%d/4", c2["verdict"], c2["mean"], [round(x, 2) for x in c2["ci95"]], c2["pos"])
        if all("A1_" + s in M for s in s2):
            c3 = pair("A1", "A2", s2, None)
            out["C3"] = c3
            log.info("C3 (chi bao cao) mean=%.2f ci95=%s", c3["mean"], [round(x, 2) for x in c3["ci95"]])
    gate = {}
    for tag, v in st.items():
        g, g0 = v["gate"], v["gate_ref"]
        gate[tag] = dict(d_n_pass=g["n_pass"] / g0["n_pass"] - 1, d_ratio_pass=g["ratio_pass"] / g0["ratio_pass"] - 1)
        gate[tag]["G_GATE_2pct"] = abs(gate[tag]["d_n_pass"]) <= 0.02 and abs(gate[tag]["d_ratio_pass"]) <= 0.02
    out["gate"] = gate
    out["agg"] = {arm: {f: float(np.mean([M[arm + "_" + s][f] for s in ss])) for f in F}
                  for arm, ss in (("A0", SEEDS8), ("A1", s1), ("A2", s2)) if ss}
    out["rows"] = {k: {f: M[k][f] for f in F} for k in M}
    for arm, a in out["agg"].items():
        log.info("AGG %s %s", arm, {k: round(v, 2) for k, v in a.items()})
    log.info("G-GATE pass %d/%d", sum(1 for v in gate.values() if v["G_GATE_2pct"]), len(gate))
    json.dump(out, open(D + "/r1_c1c2.json", "w"), indent=1, default=float)


if __name__ == "__main__":
    main()
