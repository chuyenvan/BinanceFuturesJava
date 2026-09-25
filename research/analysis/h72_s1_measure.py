#!/usr/bin/env python3
"""h72_s1_measure.py — VIỆC 0 + VIỆC 2 của PREREG_H72: chấm RANKER SỐNG (S1) ở `h = 72h`, 3 nhãn.

Điểm S1 ĐÃ CÓ theo `(ts, symId)` (`/home/ubuntu/ledger/pred_s1a2x1.parquet`, `score` THẤP = TỐT)
=> KHÔNG train (VIỆC 0 = CÓ). Nhãn `*_72h` đọc thẳng từ `/home/ubuntu/label_15m/*.pb`.
Chỉ số dùng LẠI NGUYÊN `model_ruler.tick_metrics` (không viết lại). CI block-72h `inflate(k)`.
KHÔNG train, KHÔNG sim, KHÔNG Java, KHÔNG chạm 2026/HoldoutSeal. DEV only.

Chạy: python3 -u research/analysis/h72_s1_measure.py [--k 2] [--t1 2026-01-01]
"""
import argparse
import glob
import logging
import os
import sys
import time

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, "/home/ubuntu/sel1m_code")
import model_ruler as R                    # noqa: E402  (tick_metrics/ci_mean — dung lai)
import c3_rates as C                       # noqa: E402
from funding_label_pb import read_label    # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
LOG = logging.getLogger("h72")
OUT = "/home/ubuntu/.cache"

S1 = "/home/ubuntu/ledger/pred_s1a2x1.parquet"
LB = "/home/ubuntu/label_15m"
MAP = "/home/ubuntu/selector_pred_out/symbol_map.csv"
Q = 900000
TZ = 7 * 3600000
COLS = None
NEED = None
METRICS = ["ic", "pacc", "dec_mono", "dec_rho", "glift8", "netm8",
           "auc8", "lift8", "lift12", "lift16", "dec_rho_lab", "base"]
NB_NEED = {4: 16, 72: 288}


def ms(y, m, d):
    return int(pd.Timestamp("%s-%s-%s" % (y, m, d), tz="UTC").value // 10**6) - TZ


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=2)
    ap.add_argument("--h", type=int, default=72, choices=[4, 72],
                    help="horizon cua nhan (AMEND PREREG_H72 §11)")
    ap.add_argument("--t0", default="2022-01-01")
    ap.add_argument("--t1", default="2026-01-01")
    a = ap.parse_args()
    T0 = ms(*a.t0.split("-"))
    T1 = ms(*a.t1.split("-"))
    global COLS, NEED
    H = int(a.h)
    COLS = ["retEnd_%dh" % H, "maxFav_%dh" % H, "nBars_%dh" % H]
    NEED = NB_NEED[H]
    LEG = {4: "retEnd_4h", 72: "retEnd_72h"}[H]
    LMAX = {4: "maxFav_4h", 72: "maxFav_72h"}[H]
    LOG.info("PREREG_H72 | h=%dh | S1=%s | k=%d (inflate=%.6f) | ts in [%s, %s)",
             H, os.path.basename(S1), a.k, C.inflate(a.k), a.t0, a.t1)

    D = pd.read_parquet(S1)
    D = D[(D.ts >= T0) & (D.ts < T1)]
    D["sym"] = D.sym.astype(np.int64)
    LOG.info("S1 rows %d | tick %d | coin/tick %.1f", len(D), D.ts.nunique(),
             len(D) / max(D.ts.nunique(), 1))
    mp = pd.read_csv(MAP)
    s2i = dict(zip(mp.symbol, mp.symId.astype(np.int64)))

    parts = []
    for f in sorted(glob.glob(LB + "/funding_label_*.pb")):
        L = read_label(f, usecols=["tEpochMs", "symbol"] + COLS)
        L = L[(L.tEpochMs >= T0 - 0) & (L.tEpochMs < T1) & (L.tEpochMs % Q == 0)]
        if len(L) == 0:
            continue
        L = L[L[COLS[0]].notna()]
        L["sym"] = L.symbol.map(s2i)
        L = L.dropna(subset=["sym"])
        if len(L) == 0:
            continue
        L["sym"] = L.sym.astype(np.int64)
        parts.append(L.drop(columns=["symbol"]).rename(columns={"tEpochMs": "ts"}))
    Lb = pd.concat(parts, ignore_index=True)
    Lb = Lb[Lb[COLS[2]] >= NEED]
    LOG.info("label rows nBars_%dh>=%d: %d", H, NEED, len(Lb))
    J = D.merge(Lb, on=["ts", "sym"], how="inner")
    LOG.info("JOINED %d rows | tick %d | coin/tick %.1f", len(J), J.ts.nunique(),
             len(J) / max(J.ts.nunique(), 1))
    assert len(J) > 0, "JOIN rong"

    J["g1lite"] = np.where(J[LMAX] >= 0.05,
                           J[LMAX] - np.minimum(0.5 * J[LMAX], 0.08),
                           J[LEG])
    # nhan (ii)/(iii) theo `h`; nhan cua CONG cho tung thuoc (chot o PREREG_H72 §4/§3)
    Y_LAB = [LEG, LMAX]
    def yb_of(name, d):
        if name == LMAX:
            return (d[LMAX] >= 0.07).to_numpy(np.float64)
        return (d[name].to_numpy(np.float64) > R.THR).astype(np.float64)

    LABELS = ["g1lite"] + Y_LAB
    NAME = {"g1lite": "(i) g1lite [nhan live ranker]", LEG: "(ii) %s [TIEN net]" % LEG,
            LMAX: "(iii) %s [CHAM]" % LMAX}
    res = {}
    for lab in LABELS:
        d = J[["ts", "sym", "score", lab]].dropna()
        tm, _aux = R.tick_metrics(d.ts.to_numpy(), (-d.score).to_numpy(),
                                  d[lab].to_numpy(np.float64), yb_in=yb_of(lab, d))
        res[lab] = tm
        LOG.info("[%s] n_tick=%d coin/tick=%.1f", NAME[lab], len(tm), tm.n_coin.mean())

    # ---- bang AGG + CI ----
    rows = []
    for lab in LABELS:
        tm = res[lab]
        for m in METRICS:
            if m not in tm.columns:
                continue
            ci = R.ci_mean(tm[m].to_numpy(), tm.ts.to_numpy(), inflate=C.inflate(a.k))
            o1, o2, both, _ = R.decide(ci)
            rows.append(dict(nhan=lab, metric=m, mean=ci["mean"], lo=ci["raw"][0], hi=ci["raw"][1],
                             out_both=both, n=ci["n"]))
    T = pd.DataFrame(rows)
    pd.set_option("display.width", 220)
    LOG.info("\n=== S1 @ h=%dh | 3 nhan | block-72h CI NREP=%d SEED=%d inflate(k=%d)=%.4f ===",
             H, C.NREP, C.SEED, a.k, C.inflate(a.k))
    LOG.info("\n%s", T.assign(
        mean=T["mean"].round(5), lo=T["lo"].round(5), hi=T["hi"].round(5)).to_string(index=False))

    os.makedirs(OUT, exist_ok=True)
    op = os.path.join(OUT, "h72_s1_ticks.parquet")
    for lab in LABELS:
        t = res[lab].copy()
        t["nhan"] = lab
        t.to_parquet(os.path.join(OUT, "h%d_s1_%s_ticks.parquet" % (H, lab)), index=False)
    T.to_csv(os.path.join(OUT, "h%d_s1_agg.csv" % H), index=False)
    LOG.info("saved %s | h%d_s1_agg.csv", op, H)


if __name__ == "__main__":
    main()
