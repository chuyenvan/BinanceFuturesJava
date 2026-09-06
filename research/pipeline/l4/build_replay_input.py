#!/usr/bin/env python3
"""L4 — dung INPUT cho cong REPLAY 3 ngay DEV cua LiveBuildMap.

Xuat ra /home/ubuntu/l4/:
  rows.bin    n x (ts i8, symId i4, hasScore i4, pwin_bins f4, pmap_bins f4, s1score f4)  [big-endian]
  x45.f32     n x 45 float32 (big-endian) — feature net015 dung THU TU g015_net_train.py
  x9.f32      n x 9  float32 (big-endian) — feature S1 dung THU TU S1FeatureLive.FEATURE_ORDER
THU TU DONG = THU TU DONG CUA FILE BINS (khong sort lai) => tie-break cua rank(method="first")
doi chung duoc voi Python.
"""
import os, sys, glob, logging
import numpy as np, pandas as pd
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("l4in")
sys.path.insert(0, os.environ.get("SEL1M_CODE", "/home/ubuntu/sel1m_code"))
from tool1_col import read_tool1

TZ = 7 * 3_600_000
OI_TOL = 2 * 3_600_000
OI_FILE = "/home/ubuntu/claudedata/oi/oi_percoin_full.bin"
MAP_CSV = "/home/ubuntu/claudedata/oi/symbol_map.csv"
OI_NAMES = ["oi_delta24h", "oi_z", "ls_global", "ls_toptrader", "taker_buy"]
OI_DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("oi", ">f4", 5)])
BIN_DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("p0", ">f4"), ("p1", ">f4"), ("p2", ">f4"), ("p3", ">f4")])
S1_FEATS = ["vol_7d", "dd_7d", "rk_dd_7d", "hrs_since_high_7d", "ret_3d", "rk_ret_3d",
            "ret_14d", "ls_global", "rk_oi_delta24h"]
DAYS = os.environ.get("L4_DAYS", "2025-11-03,2025-11-17,2025-12-08").split(",")
OUT = os.environ.get("L4_OUT", "/home/ubuntu/l4")
FOLD = os.environ.get("L4_FOLD", "20251001")


def day_range(d):
    lo = int(pd.Timestamp(d, tz="UTC").value // 10 ** 6) - TZ
    return lo, lo + 86_400_000


def main():
    os.makedirs(OUT, exist_ok=True)
    G = np.fromfile("/home/ubuntu/claudedata/predwf_G015x26/predict_wf_%s.bin" % FOLD, dtype=BIN_DT)
    M = np.fromfile("/home/ubuntu/predwf_map_s1a2_x1/predict_wf_%s.bin" % FOLD, dtype=BIN_DT)
    assert len(G) == len(M) and (G["ts"] == M["ts"]).all() and (G["sym"] == M["sym"]).all()
    ts = G["ts"].astype(np.int64)
    keep = np.zeros(len(ts), dtype=bool)
    for d in DAYS:
        lo, hi = day_range(d)
        keep |= (ts >= lo) & (ts < hi)
    idx = np.flatnonzero(keep)                      # GIU THU TU DONG CUA FILE
    log.info("bins %d dong -> chon %d dong cho %s", len(ts), len(idx), DAYS)
    df = pd.DataFrame({"ts": ts[idx], "symId": G["sym"][idx].astype(np.int32),
                       "pwin": G["p0"][idx].astype(np.float32),
                       "pmap": M["p0"][idx].astype(np.float32),
                       "row": np.arange(len(idx), dtype=np.int64)})
    log.info("tick: %d  coin: %d", df.ts.nunique(), df.symId.nunique())

    # ---- s1 score (pred_s1a2x1.parquet: ts,sym,score) ----
    SC = pd.read_parquet("/home/ubuntu/ledger/pred_s1a2x1.parquet")
    SC = SC.rename(columns={"sym": "symId"})
    df = df.merge(SC, on=["ts", "symId"], how="left")
    df["hasScore"] = df.score.notna().astype(np.int32)
    log.info("co score: %.4f", df.hasScore.mean())

    # ---- 45 feature (Tool1 40 + 5 OI) — Y HET g015_net_train.build_matrix ----
    lo_all = int(df.ts.min()) - OI_TOL
    hi_all = int(df.ts.max()) + 1
    a = read_tool1("/home/ubuntu/ds_feat15m/features_20251001*", grid_ms=900_000)
    log.info("tool1 rows %d", len(a))
    F = a["f"]
    ao = np.memmap(OI_FILE, dtype=OI_DT, mode="r")
    aots = np.asarray(ao["ts"])
    msk = (aots >= lo_all) & (aots < hi_all)
    del aots
    aoc = np.array(ao[msk]); del msk, ao
    t = pd.DataFrame({"ts": a["ts"].astype(np.int64), "symId": a["sym"].astype(np.int32),
                      "ridx": np.arange(len(a), dtype=np.int64)})
    t = t[(t.ts >= int(df.ts.min())) & (t.ts <= int(df.ts.max()))]
    o = pd.DataFrame({"ts": aoc["ts"].astype(np.int64), "symId": aoc["sym"].astype(np.int32)})
    O = np.asarray(aoc["oi"], dtype=np.float32)
    for j, nm in enumerate(OI_NAMES):
        o[nm] = O[:, j]
    del aoc, O
    t = t.sort_values("ts").reset_index(drop=True)
    o = o.sort_values("ts").reset_index(drop=True)
    mg = pd.merge_asof(t, o, on="ts", by="symId", direction="backward", tolerance=OI_TOL)
    smap = pd.read_csv(MAP_CSV)
    mg = mg.merge(smap, on="symId", how="left").dropna(subset=["symbol"])
    log.info("merged feature rows %d", len(mg))
    X = np.empty((len(mg), 45), dtype=np.float32)
    X[:, :40] = F[mg["ridx"].to_numpy()]
    X[:, 40:] = mg[OI_NAMES].to_numpy(np.float32)
    fmap = pd.DataFrame({"ts": mg.ts.to_numpy(np.int64), "symId": mg.symId.to_numpy(np.int32),
                         "fi": np.arange(len(mg), dtype=np.int64)})
    df = df.merge(fmap, on=["ts", "symId"], how="left")
    miss = df.fi.isna().sum()
    log.info("dong bins KHONG co feature 45: %d (%.4f%%)", miss, 100.0 * miss / len(df))
    df["fi"] = df.fi.fillna(-1).astype(np.int64)

    # ---- 9 feature S1 (feat_v2_x1 theo moc GIO) ----
    FV = pd.read_parquet("/home/ubuntu/featv2/feat_v2_x1.parquet")
    FV = FV.rename(columns={"ts": "ts_h", "sym": "symId"})
    df["ts_h"] = (df.ts // 3_600_000) * 3_600_000
    df = df.merge(FV[["ts_h", "symId"] + S1_FEATS], on=["ts_h", "symId"], how="left")
    log.info("dong co du 9 feature S1: %.4f", df[S1_FEATS].notna().all(axis=1).mean())

    df = df.sort_values("row").reset_index(drop=True)      # KHOI PHUC thu tu dong bins
    n = len(df)
    rec = np.zeros(n, dtype=np.dtype([("ts", ">i8"), ("symId", ">i4"), ("hasScore", ">i4"),
                                      ("pwin", ">f4"), ("pmap", ">f4"), ("s1", ">f4")]))
    rec["ts"] = df.ts.to_numpy(np.int64)
    rec["symId"] = df.symId.to_numpy(np.int32)
    rec["hasScore"] = df.hasScore.to_numpy(np.int32)
    rec["pwin"] = df.pwin.to_numpy(np.float32)
    rec["pmap"] = df.pmap.to_numpy(np.float32)
    rec["s1"] = df.score.fillna(np.nan).to_numpy(np.float32)
    rec.tofile(os.path.join(OUT, "rows.bin"))
    x45 = np.full((n, 45), np.nan, dtype=np.float32)
    ok = df.fi.to_numpy() >= 0
    x45[ok] = X[df.fi.to_numpy()[ok]]
    x45.astype(">f4").tofile(os.path.join(OUT, "x45.f32"))
    df[S1_FEATS].to_numpy(np.float32).astype(">f4").tofile(os.path.join(OUT, "x9.f32"))
    log.info("GHI %s: rows.bin(%d) x45.f32 x9.f32", OUT, n)
    print("L4_INPUT_OK n=%d ticks=%d hasScore=%.4f featOk=%.4f" %
          (n, df.ts.nunique(), df.hasScore.mean(), ok.mean()))


if __name__ == "__main__":
    main()
