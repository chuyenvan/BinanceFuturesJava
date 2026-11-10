#!/usr/bin/env python3
"""R1 cham C-LIVE (A3 vs A0, 8 cap) theo PREREG_R1_S1_ABLATION (44acf9cd) + ADD1 (ce321bd3) + ADD2 (93b60422).
Metric: CAGR22, maxDD MTM 2022-25 (gvz_mtm Vision, kline1m tai lai tu Kaggle vz-kline1m-*, sha khop README).
Cong truoc khi cham: G-P0 (orch_state), G-MTM (tinh lai A0_A1 bang gia tai lai == cache tsx), missing=0.
Usage: python3 r1_score.py [--arms A3]"""
import json
import logging
import math
import os
import sys

import numpy as np

D = "/home/ubuntu/claude_master/res1109/r1_s1"
KL = D + "/kl"
sys.path.insert(0, "/home/ubuntu/claude_master/iso")
sys.path.insert(0, "/home/ubuntu/claude_master/gvz")
import gvz_mtm as MT  # noqa: E402

MT.kp = lambda ym: os.path.join("/home/ubuntu/claude_master/gvz/k2021" if ym < "2021-12" else KL, "kline1m-%s.parquet" % ym)
import reset_rule_score as R  # noqa: E402
import flat3_crashpen_driver as F3  # noqa: E402
import n700_driver as N  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("r1score")
SEEDS = ["A1", "S7", "S13", "S21", "S99", "S123", "S777", "S2024"]
T975 = {n: v for n, v in zip(range(2, 9), (12.706, 4.303, 3.182, 2.776, 2.571, 2.447, 2.365))}
F = ("cagr22", "dd_mtm22", "dd_mtm", "calmar22", "uw_mtm22", "n_per_year", "sum_pnl", "sum_pnl_2022_25")


def ci(x):
    n = len(x)
    if n < 2:
        return [float("nan"), float("nan")]
    hw = T975[n] * float(np.std(x, ddof=1)) / math.sqrt(n)
    return [float(np.mean(x) - hw), float(np.mean(x) + hw)]


def main():
    assert R._work is MT._work_vision
    st = json.load(open(D + "/orch_state.json"))["done"]
    p0 = st.get("r1-p0-a1", {})
    assert p0.get("G_P0") is True, "G-P0 chua PASS -> khong tai dung A0"
    seeds = [s for s in SEEDS if st.get("r1-a3-" + s.lower(), {}).get("valid")]
    log.info("seed A3 hop le: %s", seeds)
    keys = {}
    for s in seeds:
        keys["A0_" + s] = "tsx-x14-" + s.lower()
        keys["A3_" + s] = "r1-a3-" + s.lower()
    keys["A0CHK_A1"] = "tsx-x14-a1"
    for k, t in keys.items():
        N.TAG[k], N.DESC[k] = t, "R1 " + k
    legs = {k: R.load_legs(t) for k, t in keys.items()}
    daily = {k: R.load_daily(t) for k, t in keys.items()}
    md5 = {k: R.md5_of(t) for k, t in keys.items()}
    mf = D + "/mtm_r1.json"
    raw = json.load(open(mf)) if os.path.exists(mf) else {}
    tsx = json.load(open("/home/ubuntu/claude_master/tsx/mtm_vision.json"))
    for s in seeds:
        c = tsx.get("X14_" + s, {})
        assert c.get("md5") == md5["A0_" + s], "cache tsx lech md5 " + s
        raw["A0_" + s] = c
    miss = {k: legs[k] for k in keys if k not in raw or raw[k].get("md5") != md5[k]}
    log.info("MTM can tinh: %s", sorted(miss))
    if miss:
        new = R.run_mtm(miss, workers=3, chunk=30)
        for k, v in new.items():
            v["md5"] = md5[k]
            raw[k] = v
        json.dump(raw, open(mf, "w"))
    assert all(raw[k]["legacy"]["missing"] == 0 for k in keys), "MTM thieu gia"
    # G-MTM: gia tai lai tai lap dung cache tsx
    a, b = raw["A0CHK_A1"]["legacy"], tsx["X14_A1"]["legacy"]
    diffs = {}
    for kk in a:
        if isinstance(a[kk], (int, float)) and isinstance(b.get(kk), (int, float)):
            diffs[kk] = abs(float(a[kk]) - float(b[kk]))
    g_mtm = bool(diffs) and max(diffs.values()) <= 1e-9
    log.info("G-MTM %s maxdiff=%s", g_mtm, max(diffs.values()) if diffs else None)
    assert g_mtm, "G-MTM truot: gia tai lai khong tai lap cache tsx"
    M = {k: N.arm_metrics(R, F3, k, legs[k], daily[k], raw[k]["legacy"]) for k in keys if k != "A0CHK_A1"}
    dcg = np.array([M["A3_" + s]["cagr22"] - M["A0_" + s]["cagr22"] for s in seeds])
    ddd = np.array([M["A3_" + s]["dd_mtm22"] - M["A0_" + s]["dd_mtm22"] for s in seeds])
    mc, md = float(dcg.mean()), float(ddd.mean())
    if mc < -2 or md < -3:
        verdict = "XAU HON" + (" ve DD" if mc >= -2 else "")
    elif mc > 2:
        verdict = "TOT HON"
    elif abs(mc) <= 2 and abs(md) <= 3:
        verdict = "TUONG DUONG"
    else:
        verdict = "KHAC (|dCAGR|<=2, DD nong hon >3pp)"
    yrs = {}
    for y in (2022, 2023, 2024, 2025):
        yrs[y] = [M["A3_" + s]["per_year"][y]["sum_pnl"] - M["A0_" + s]["per_year"][y]["sum_pnl"] for s in seeds]
    ov = {}
    for s in seeds:
        la, lb = legs["A0_" + s], legs["A3_" + s]
        ka = set(zip(la["sym"].astype(str), la["ts"]))
        kb = set(zip(lb["sym"].astype(str), lb["ts"]))
        ov[s] = len(ka & kb) / max(1, len(ka | kb))
    gate = {s: dict(a3=st["r1-a3-" + s.lower()]["gate"], a0=st["r1-a3-" + s.lower()]["gate_ref"]) for s in seeds}
    for s in seeds:
        g = gate[s]
        gate[s]["d_n_pass"] = g["a3"]["n_pass"] / g["a0"]["n_pass"] - 1
        gate[s]["d_ratio_pass"] = g["a3"]["ratio_pass"] / g["a0"]["ratio_pass"] - 1
        gate[s]["G_GATE_2pct"] = abs(gate[s]["d_n_pass"]) <= 0.02 and abs(gate[s]["d_ratio_pass"]) <= 0.02
        log.info("ROW %-5s CAGR22 %.2f->%.2f DD22 %.2f->%.2f Cal %.3f->%.3f n/y %.0f->%.0f overlap %.3f gate dn=%.4f dr=%.4f", s,
                 M["A0_" + s]["cagr22"], M["A3_" + s]["cagr22"], M["A0_" + s]["dd_mtm22"], M["A3_" + s]["dd_mtm22"],
                 M["A0_" + s]["calmar22"], M["A3_" + s]["calmar22"], M["A0_" + s]["n_per_year"], M["A3_" + s]["n_per_year"],
                 ov[s], gate[s]["d_n_pass"], gate[s]["d_ratio_pass"])
    agg = {arm: {f: float(np.mean([M[arm + "_" + s][f] for s in seeds])) for f in F} for arm in ("A0", "A3")}
    out = dict(prereg=["44acf9cd", "ce321bd3", "93b60422"], n_seeds=len(seeds), seeds=seeds, verdict_C_LIVE=verdict,
               dCAGR22=dict(mean=mc, ci95=ci(dcg), per_seed=dcg.tolist(), pos=int((dcg > 0).sum())),
               dDD22=dict(mean=md, ci95=ci(ddd), per_seed=ddd.tolist()),
               dPnL_year=yrs, overlap=ov, gate=gate, agg=agg, G_P0=True, G_MTM=g_mtm,
               rows={s: {f: [M["A0_" + s][f], M["A3_" + s][f]] for f in F} for s in seeds})
    log.info("AGG %s", json.dumps(agg))
    log.info("C-LIVE %s dCAGR22 mean=%.2f ci95=%s pos=%d/%d | dDD22 mean=%.2f ci95=%s", verdict, mc, out["dCAGR22"]["ci95"],
             out["dCAGR22"]["pos"], len(seeds), md, out["dDD22"]["ci95"])
    json.dump(out, open(D + "/r1_clive.json", "w"), indent=1, default=float)


if __name__ == "__main__":
    main()
