"""FS buoc 3: dong goi bang train duy nhat cho Kaggle -> /home/ubuntu/fs/pack/fsdata.parquet
Chi DEV. Khong ghi de artifact nao."""
import logging, sys, os
import numpy as np, pandas as pd
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout)
L = logging.getLogger(__name__)
H = 3600000
LED = "/home/ubuntu/ledger"
PK = "/home/ubuntu/fs/pack"
os.makedirs(PK, exist_ok=True)
KEEP9 = ["vol_7d", "dd_7d", "rk_dd_7d", "hrs_since_high_7d", "ret_3d", "rk_ret_3d",
         "ret_14d", "ls_global", "rk_oi_delta24h"]

D = pd.read_parquet(f"{LED}/cand_dev.parquet",
                    columns=["ts", "sym", "g1lite", "retEnd_72h", "maxFav_72h"])
L.info("cand_dev %s", D.shape)
D = D[D.g1lite.notna()].copy()
L.info("sau loc g1lite %s ts %s..%s", D.shape,
       pd.to_datetime(D.ts.min(), unit="ms"), pd.to_datetime(D.ts.max(), unit="ms"))
assert D.ts.max() < 1719792000000, "LEAK: co ts >= 2024-07-01"
D["ts_h"] = (D.ts // H) * H

F = pd.read_parquet("/home/ubuntu/featv2/feat_v2.parquet", columns=["ts", "sym"] + KEEP9)
L.info("feat_v2 %s", F.shape)
D = D.merge(F.rename(columns={"ts": "ts_h"}), on=["ts_h", "sym"], how="left")
L.info("join base: co vol_7d %.4f", D.vol_7d.notna().mean())

FS = pd.read_parquet("/home/ubuntu/fs/feat_fs.parquet")
CAND = [c for c in FS.columns if c.startswith("fs_")]
L.info("feat_fs %s cands=%d", FS.shape, len(CAND))
D = D.merge(FS.rename(columns={"ts": "ts_h"}), on=["ts_h", "sym"], how="left")
for c in CAND:
    L.info("  cover %s = %.4f", c, D[c].notna().mean())

PL = pd.read_parquet(f"{LED}/path_labels.parquet")
L.info("path_labels cols %s rows %d", list(PL.columns), len(PL))
pc = [c for c in PL.columns if "replay" in c.lower()]
L.info("cot replay: %s", pc)
D = D.merge(PL[["ts", "sym"] + pc], on=["ts", "sym"], how="left")
for c in pc:
    L.info("  cover %s = %.4f", c, D[c].notna().mean())

D.to_parquet(f"{PK}/fsdata.parquet", index=False)
S = pd.read_parquet(f"{LED}/pred_s1a2.parquet")
S.to_parquet(f"{PK}/pred_s1a2_ref.parquet", index=False)
L.info("pack rows=%d cols=%d size=%.1f MB", len(D), D.shape[1],
       os.path.getsize(f"{PK}/fsdata.parquet") / 1e6)
L.info("DONE")
