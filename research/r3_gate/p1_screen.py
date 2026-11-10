#!/usr/bin/env python3
"""R3 sang P1 (prereg PREREG_R3_GATE_FAMILY b901016e ?4): CHI DEM (cam pnl/MTM). gate_offline voi pred n4f-b0 (8 seed) +
held = printDone n4f-b0-* (cot sym/start/end/level). Arm: A0, G1 MEAN15, G2 MEAN60, G3 MTF-OR{1,15} c=0,5, G4 LATCH 15'/0,9q.
Luat: Jaccard phut pass median >= 0,90 => LOAI; quota cell DEV arm/A0 median ngoai [0,75;1,25] => LOAI."""
import json, logging, sys
import numpy as np, pandas as pd
sys.path.insert(0, "/home/ubuntu/claude_master/vz_e1_wt/research/analysis")
import gate_offline as GO
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("r3p1")
R3 = "/home/ubuntu/claude_master/res1109/r3_gate/"
SEEDS = {"S42": "a1", "S7": "s7", "S13": "s13", "S21": "s21", "S99": "s99", "S123": "s123", "S777": "s777", "S2024": "s2024"}
GO.SEEDS = {k: (int(k[1:]), R3 + "pred/pred_s%s.bin" % k[1:], "n4f-b0-" + v) for k, v in SEEDS.items()}
GO.OUTK = "/home/ubuntu/claude_master/nup4_fix/results/"
DEV0, DEV1 = 1640970000000, 1767200400000
M1 = 60000
PCT_W = np.float32(1.0 - 0.5 * (1.0 - float(np.float32(GO.PCT))))
J = 256


def smooth(C, pts, p15, W, mincov):
    cs = np.concatenate([[0.0], np.cumsum(p15.astype(np.float64))])
    t = C["ts"]
    lo = np.searchsorted(pts, t - (W - 1) * M1, "left")
    hi = np.searchsorted(pts, t, "right")
    n = hi - lo
    ps = np.where(n >= mincov, ((cs[hi] - cs[lo]) / np.maximum(n, 1)).astype(np.float32), np.float32(np.nan))
    C2 = dict(C)
    C2["p15"] = ps
    C2["valid"] = C["valid"] & np.isfinite(ps)[:, None]
    return C2, float(np.mean(n[(t >= DEV0) & (t < DEV1)] >= mincov))


def latch(C, G0, T=15, h=0.9):
    P0, qm, ts, p = G0["P"], G0["qm"], C["ts"], C["p15"]
    pm = ts[P0.any(1)]
    j = np.searchsorted(pm, ts, "left") - 1
    dt = np.where(j >= 0, ts - pm[np.maximum(j, 0)], 10 ** 15)
    inwin = (dt > 0) & (dt <= T * M1)
    fac = np.maximum(GO.DYN_MIN, (C["SP"] / GO.SCORE_BASE) * GO.DYN_MULT)
    thrL = ((np.float32(h) * qm)[:, None] * fac) * GO.GS
    PL = C["valid"] & inwin[:, None] & ~(p[:, None] < thrL)
    return P0 | PL


def stats(C, P, P0):
    dev = (C["ts"] >= DEV0) & (C["ts"] < DEV1)
    mA, m0 = P.any(1) & dev, P0.any(1) & dev
    inter, uni = int((mA & m0).sum()), int((mA | m0).sum())
    yr = C["yr"]
    by = {int(y): [int(P[dev & (yr == y)].sum()), int(P0[dev & (yr == y)].sum())] for y in (2022, 2023, 2024, 2025)}
    # dot A0 (cum phut pass cach > 60'): trung / tre phut dau
    t0 = C["ts"][m0]; tA = C["ts"][mA]
    st = np.r_[0, np.nonzero(np.diff(t0) > 60 * M1)[0] + 1]
    en = np.r_[st[1:] - 1, len(t0) - 1]
    hit, lag = 0, []
    for a, b in zip(st, en):
        k = np.searchsorted(tA, t0[a] - 60 * M1, "left")
        if k < len(tA) and tA[k] <= t0[b] + 60 * M1:
            hit += 1; lag.append((tA[k] - t0[a]) / M1)
    return dict(cells=int(P[dev].sum()), cells0=int(P0[dev].sum()), quota=round(P[dev].sum() / max(P0[dev].sum(), 1), 4),
                minutes=int(mA.sum()), minutes0=int(m0.sum()), min_ratio=round(mA.sum() / max(m0.sum(), 1), 4),
                jaccard=round(inter / max(uni, 1), 4), by_year=by, eps0=int(len(st)), eps_hit=hit,
                lag_med=float(np.median(lag)) if lag else None)


B = dict(np.load(GO.CACHE + "/cand_base.npz"))
mp = pd.read_csv(GO.MAPF)
s2id = dict(zip(mp.symbol.astype(str).str.replace("USDT$", "", regex=True), mp.symId.astype(int)))
OUT = dict(prereg="b901016e", pct=float(np.float32(GO.PCT)), pct_w=float(PCT_W), J=J, note="offline, khong skipFull, held=printDone n4f-b0", seeds={})
for arm in SEEDS:
    C = GO.build(arm, B, s2id)
    pts, p15 = GO.load_pred(GO.SEEDS[arm][1])
    G0 = GO.run_g2(C, J=J); P0 = G0["P"]
    res = {"A0": stats(C, P0, P0)}
    C15, cov15 = smooth(C, pts, p15, 15, 12)
    G15 = GO.run_g2(C15, J=J)
    res["G1_MEAN15"] = stats(C, G15["P"], P0); res["G1_MEAN15"]["cov_dev"] = round(cov15, 5)
    C60, cov60 = smooth(C, pts, p15, 60, 48)
    res["G2_MEAN60"] = stats(C, GO.run_g2(C60, J=J)["P"], P0); res["G2_MEAN60"]["cov_dev"] = round(cov60, 5)
    Pa = GO.run_g2(C, pct=PCT_W, J=J)["P"]; Pb = GO.run_g2(C15, pct=PCT_W, J=J)["P"]
    res["G3_MTFOR"] = stats(C, Pa | Pb, P0)
    res["G4_LATCH"] = stats(C, latch(C, G0), P0)
    OUT["seeds"][arm] = res
    log.info("%s %s", arm, {k: (v["quota"], v["jaccard"]) for k, v in res.items()})
    del C, C15, C60, G0, G15
summ = {}
for a in ("G1_MEAN15", "G2_MEAN60", "G3_MTFOR", "G4_LATCH"):
    q = np.median([OUT["seeds"][s][a]["quota"] for s in SEEDS]); jj = np.median([OUT["seeds"][s][a]["jaccard"] for s in SEEDS])
    summ[a] = dict(quota_med=round(float(q), 4), jaccard_med=round(float(jj), 4),
                   quota_range=[min(OUT["seeds"][s][a]["quota"] for s in SEEDS), max(OUT["seeds"][s][a]["quota"] for s in SEEDS)],
                   jaccard_range=[min(OUT["seeds"][s][a]["jaccard"] for s in SEEDS), max(OUT["seeds"][s][a]["jaccard"] for s in SEEDS)],
                   PASS=bool(jj < 0.90 and 0.75 <= q <= 1.25))
OUT["summary"] = summ
json.dump(OUT, open(R3 + "p1_r3.json", "w"), indent=1)
log.info("SUMMARY %s", json.dumps(summ))
