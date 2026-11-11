#!/usr/bin/env python3
"""R5_SIGNAL_QUALITY buoc 1 (prereg docs/prereg/PREREG_R5_SIGNAL_QUALITY.md 200a29a3) §1,§3,§4: 12 bien the p15 theo phut
cho 8 seed + K (so phut B0 pass) theo giai doan/nam + bang ro top-24 sp cho kernel fwd. Khong tinh Y/PnL o day."""
import json
import logging
import shutil
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/home/ubuntu/claude_master/vz_e1_wt/research/analysis")
import gate_offline as GO  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("r5sig")
R3 = "/home/ubuntu/claude_master/res1109/r3_gate/"
OUT = "/home/ubuntu/claude_master/res1109/r5_quality/"
SEEDS = {"S42": "a1", "S7": "s7", "S13": "s13", "S21": "s21", "S99": "s99", "S123": "s123", "S777": "s777", "S2024": "s2024"}
GO.SEEDS = {k: (int(k[1:]), R3 + "pred/pred_s%s.bin" % k[1:], "n4f-b0-" + v) for k, v in SEEDS.items()}
GO.OUTK = "/home/ubuntu/claude_master/nup4_fix/results/"
M1 = 60000
YB = {2022: 1640970000000, 2023: 1672506000000, 2024: 1704042000000, 2025: 1735664400000, 2026: 1767200400000}
DEV0, DEV1 = YB[2022], YB[2026]
VARS = ["RAW", "MEAN5", "MEAN15", "MEAN60", "MEAN240", "EWMA5", "EWMA15", "EWMA60", "MED15", "MAX15", "MIN15", "SUR60"]


def guard():
    fr = int(open("/proc/meminfo").read().split("MemAvailable:")[1].split()[0]) // 1024
    du = shutil.disk_usage("/home/ubuntu")
    log.info("MemAvailable %d MB, disk free %.1f GB", fr, du.free / 1e9)
    assert fr >= 4000 and du.free >= 15e9, "DUNG: thieu RAM/dia"


def variants(pts, p15, ts):
    n = int((pts[-1] - pts[0]) // M1) + 1
    a = np.full(n, np.nan)
    a[(pts - pts[0]) // M1] = p15.astype(np.float64)
    s = pd.Series(a)
    sh = s.shift(1)
    cols = {
        "RAW": s,
        "MEAN5": s.rolling(5, min_periods=4).mean(),
        "MEAN15": s.rolling(15, min_periods=12).mean(),
        "MEAN60": s.rolling(60, min_periods=48).mean(),
        "MEAN240": s.rolling(240, min_periods=192).mean(),
        "EWMA5": s.ewm(halflife=5, adjust=True, ignore_na=True).mean(),
        "EWMA15": s.ewm(halflife=15, adjust=True, ignore_na=True).mean(),
        "EWMA60": s.ewm(halflife=60, adjust=True, ignore_na=True).mean(),
        "MED15": s.rolling(15, min_periods=12).median(),
        "MAX15": s.rolling(15, min_periods=12).max(),
        "MIN15": s.rolling(15, min_periods=12).min(),
        "SUR60": s - sh.rolling(60, min_periods=48).mean(),
    }
    i = (ts - pts[0]) // M1
    ok = (i >= 0) & (i < n)
    ii = np.clip(i, 0, n - 1)
    V = np.full((len(ts), len(VARS)), np.nan, np.float32)
    for k, name in enumerate(VARS):
        x = cols[name].to_numpy()[ii]
        x[~ok] = np.nan
        # EWMA: chi hop le khi p15(t) co mat (cung phut xet)
        V[:, k] = x.astype(np.float32)
    return V


def main():
    guard()
    B = dict(np.load(GO.CACHE + "/cand_base.npz"))
    mp = pd.read_csv(GO.MAPF)
    s2id = dict(zip(mp.symbol.astype(str).str.replace("USDT$", "", regex=True), mp.symId.astype(int)))
    id2s = {v: k + "USDT" for k, v in s2id.items()}
    # bang ro top-24 sp (giong moi seed)
    mts, fi = B["mts"], B["fi"]
    m = (mts >= DEV0) & (mts < DEV1)
    SY = B["SY15"][fi[m]][:, :GO.K].astype(np.int32)
    SPn = B["SP15"][fi[m]][:, :GO.K]
    SY[np.isnan(SPn)] = -1
    bk = pd.DataFrame(SY.astype(np.int16), columns=["b%d" % j for j in range(GO.K)])
    bk.insert(0, "ts", mts[m].astype(np.int64))
    bk.to_parquet(OUT + "r5q_basket.parquet", index=False)
    pd.DataFrame(dict(sid=list(id2s.keys()), sym=list(id2s.values()))).to_csv(OUT + "r5q_symmap.csv", index=False)
    log.info("ro: %d phut DEV, coin/phut median %.0f", len(bk), float(np.median((SY >= 0).sum(1))))
    Kinfo = {}
    for s in SEEDS:
        C = GO.build(s, B, s2id)
        pts, p15 = GO.load_pred(GO.SEEDS[s][1])
        ts = C["ts"]
        G = GO.run_g2(C, J=256)
        pm = G["P"].any(1)
        dm = (ts >= DEV0) & (ts < DEV1)
        V = variants(pts, p15, ts[dm])
        np.savez(OUT + "sig_%s.npz" % s, ts=ts[dm], V=V, b0=pm[dm])
        Kinfo[s] = {"disc": int(pm[(ts >= YB[2022]) & (ts < YB[2024])].sum()), "conf": int(pm[(ts >= YB[2024]) & (ts < YB[2026])].sum())}
        for y in (2022, 2023, 2024, 2025):
            Kinfo[s][str(y)] = int(pm[(ts >= YB[y]) & (ts < YB[y + 1])].sum())
        log.info("%s: phut DEV %d, K %s, NaN/bien the %s", s, int(dm.sum()), Kinfo[s], np.isnan(V).sum(0).tolist())
        del C, G
    json.dump(dict(prereg="200a29a3", vars=VARS, K=Kinfo), open(OUT + "sig_meta.json", "w"), indent=1)
    log.info("XONG buoc tin hieu")


if __name__ == "__main__":
    main()
