#!/usr/bin/env python3
"""HO1 B4c — pool S1 2026 + S1 predict-only (s1a2x1_cut20251231.json). Pre-reg 35d03784 + ADDENDUM-1 §4.
Pool(tick) = coin co ban ghi nhan tai tick 15' gate MO (p15 >= 0.008) voi nBars_72h >= 288 — CHI doc tEpochMs/symbol/nBars_72h
(khong doc gia tri outcome 2026). Tick mo 2026 = p15 seed 42 (pred.bin B2, model cut 2026-01-01 +07).
Cong (tren 2025Q4, DEV):
  G-B4p: pool theo dinh nghia availability vs ledger DEV cand_dev_x1 g1lite.notna(): Jaccard >= 0,99.
  G-B4b: S1 cut20251001 + feature cua so -> == pred_s1a2x1.parquet (spearman >= 0,999999, max|d| <= 1e-6).
SEAL: khong in thong ke gia tri 2026. Usage: python3 ho1_s1_2026.py <feat.parquet> <out_pred.parquet>"""
import glob
import json
import logging
import struct
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/home/ubuntu/sel1m_code")
from funding_label_pb import read_label  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("ho1s1")
H, Q = 3600000, 900000
LBDIR = "/home/ubuntu/ds_label15m"
MAP = "/home/ubuntu/selector_pred_out/symbol_map.csv"
GATE_DEV = "/home/ubuntu/claudedata/wfo_gate_pred.csv"
PRED42 = "/home/ubuntu/claude_master/1003/ho1/gate/pred_s42/pred.bin"
LEDGER = "/home/ubuntu/ledger/cand_dev_x1.parquet"
PRED_DEV = "/home/ubuntu/ledger/pred_s1a2x1.parquet"
M1001 = "/home/ubuntu/s1_model/s1a2x1_cut20251001.json"
M1231, M1231_SHA = "/home/ubuntu/s1_model/s1a2x1_cut20251231.json", "af706dc654c96f075caddc5f4153c768eec0732a28340cf9adbd6a6f791d8bf1"
KEEP = ["vol_7d", "dd_7d", "rk_dd_7d", "hrs_since_high_7d", "ret_3d", "rk_ret_3d", "ret_14d", "ls_global", "rk_oi_delta24h"]
Q4_LO = int(pd.Timestamp("2025-09-30 17:00").value // 10**6)
SEAL7 = int(pd.Timestamp("2025-12-31 17:00").value // 10**6)
END7 = int(pd.Timestamp("2026-06-30 17:00").value // 10**6)


def avail_pool(open_ts, files):
    mp = pd.read_csv(MAP)
    s2i = dict(zip(mp.symbol, mp.symId))
    parts = []
    for f in files:
        L = read_label(f, usecols=["tEpochMs", "symbol", "nBars_72h"])
        L = L[(L.tEpochMs % Q == 0) & L.tEpochMs.isin(open_ts)]
        L = L[L.nBars_72h >= 288]
        L["sym"] = L.symbol.map(s2i)
        L = L.dropna(subset=["sym"])
        parts.append(pd.DataFrame({"ts": L.tEpochMs.astype(np.int64).to_numpy(), "sym": L.sym.astype(np.int64).to_numpy()}))
    return pd.concat(parts).drop_duplicates(["ts", "sym"]).sort_values(["ts", "sym"]).reset_index(drop=True)


def score(model, D, F):
    import xgboost as xgb
    D = D.assign(ts_h=(D.ts // H) * H).merge(F.rename(columns={"ts": "ts_h"}), on=["ts_h", "sym"], how="left")
    b = xgb.Booster()
    b.load_model(model)
    dm = xgb.DMatrix(D[KEEP].to_numpy(dtype=np.float32), feature_names=list(KEEP))
    D["score"] = -b.predict(dm)
    return D, float(D.vol_7d.notna().mean())


def gates(F):
    from scipy.stats import spearmanr
    G = pd.read_csv(GATE_DEV, usecols=["timestamp", "predReturn15M"]).rename(columns={"timestamp": "ts", "predReturn15M": "p15"})
    G = G[(G.ts % Q == 0) & (G.ts >= Q4_LO) & (G.ts < SEAL7)].drop_duplicates("ts")
    A = avail_pool(G[G.p15 >= 0.008].ts.values, sorted(glob.glob(LBDIR + "/funding_label_20251001*.pb")))
    D = pd.read_parquet(LEDGER, columns=["ts", "sym", "g1lite"])
    D = D[(D.ts >= Q4_LO) & (D.ts < SEAL7) & D.g1lite.notna()][["ts", "sym"]].astype(np.int64)
    ka, kd = set(zip(A.ts, A.sym)), set(zip(D.ts, D.sym))
    gp = dict(n_avail=len(ka), n_dev=len(kd), inter=len(ka & kd), jaccard=len(ka & kd) / max(1, len(ka | kd)))
    gp["pass"] = gp["jaccard"] >= 0.99
    log.info("G-B4p: %s", gp)
    S, cov = score(M1001, D, F)
    R = pd.read_parquet(PRED_DEV)
    R = R[(R.ts >= Q4_LO) & (R.ts < SEAL7)][["ts", "sym", "score"]]
    M = S[["ts", "sym", "score"]].merge(R, on=["ts", "sym"], suffixes=("_n", "_d"))
    gb = dict(n_new=int(len(S)), n_ref=int(len(R)), n_join=int(len(M)), feat_cov=cov,
              spearman=float(spearmanr(M.score_n, M.score_d).correlation),
              max_abs=float(np.abs(M.score_n - M.score_d).max()))
    gb["pass"] = bool(gb["n_join"] == gb["n_ref"] == gb["n_new"] and gb["spearman"] >= 0.999999 and gb["max_abs"] <= 1e-6)
    log.info("G-B4b: %s", gb)
    return gp, gb


def sha256f(p):
    import hashlib
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def main():
    featp, out = sys.argv[1], sys.argv[2]
    F = pd.read_parquet(featp, columns=["ts", "sym"] + KEEP)
    F["sym"] = F.sym.astype(np.int64)
    gp, gb = gates(F)
    meta = dict(prereg="35d03784+ADD1", G_B4p=gp, G_B4b=gb)
    json.dump(meta, open(out + ".json", "w"), indent=1)
    if not (gp["pass"] and gb["pass"]):
        log.error("G-B4p/G-B4b FAIL -> DUNG")
        sys.exit(2)
    raw = open(PRED42, "rb").read()
    n = struct.unpack(">i", raw[:4])[0]
    a = np.frombuffer(raw[4:4 + 16 * n], dtype=np.dtype([("ts", ">i8"), ("p15", ">f4"), ("r", ">f4")]))
    ts = a["ts"].astype(np.int64)
    m = (ts >= SEAL7) & (ts < END7) & (ts % Q == 0)
    open_ts = ts[m][a["p15"][m].astype(np.float32) >= np.float32(0.008)]
    files = sorted(glob.glob(LBDIR + "/funding_label_2026*.pb"))
    A = avail_pool(open_ts, files)
    assert sha256f(M1231) == M1231_SHA
    S, cov = score(M1231, A, F)
    S[["ts", "sym", "score"]].to_parquet(out, index=False)
    meta["pool_2026"] = dict(label_files=[f.split("/")[-1] for f in files], n_rows=int(len(S)), n_ticks=int(S.ts.nunique()),
                             ts_min=int(S.ts.min()), ts_max=int(S.ts.max()), feat_cov=cov,
                             nan_score=int(S.score.isna().sum()), model_sha256=M1231_SHA, out=out, out_sha256=sha256f(out))
    json.dump(meta, open(out + ".json", "w"), indent=1)
    log.info("POOL/S1 2026: %s", meta["pool_2026"])


if __name__ == "__main__":
    main()
