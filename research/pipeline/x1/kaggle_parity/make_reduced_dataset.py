import pandas as pd, numpy as np, os, json, hashlib
KEEP9 = ["vol_7d","dd_7d","rk_dd_7d","hrs_since_high_7d","ret_3d","rk_ret_3d",
         "ret_14d","ls_global","rk_oi_delta24h"]
OUT="/home/ubuntu/s1hpo/kaggle_ds"
os.makedirs(OUT, exist_ok=True)

print("reading feat_v2_x1.parquet (ts,sym+KEEP9)...", flush=True)
F = pd.read_parquet("/home/ubuntu/featv2/feat_v2_x1.parquet", columns=["ts","sym"]+KEEP9)
for c in KEEP9:
    if F[c].dtype == np.float64:
        F[c] = F[c].astype(np.float32)
print("F shape", F.shape, F.dtypes.to_dict(), flush=True)
F.to_parquet(f"{OUT}/feat_v2_x1_keep9.parquet", index=False)
print("wrote feat_v2_x1_keep9.parquet", os.path.getsize(f"{OUT}/feat_v2_x1_keep9.parquet"), flush=True)
del F

print("reading cand_dev_x1.parquet (ts,sym,g1lite)...", flush=True)
D = pd.read_parquet("/home/ubuntu/ledger/cand_dev_x1.parquet", columns=["ts","sym","g1lite"])
print("D shape", D.shape, flush=True)
D.to_parquet(f"{OUT}/cand_dev_x1_lite.parquet", index=False)
print("wrote cand_dev_x1_lite.parquet", os.path.getsize(f"{OUT}/cand_dev_x1_lite.parquet"), flush=True)

def md5_of(p):
    h=hashlib.md5()
    with open(p,"rb") as f:
        for chunk in iter(lambda: f.read(1<<20), b""):
            h.update(chunk)
    return h.hexdigest()

meta = dict(
    keep9_shape=list(D.shape),
    files={
        "feat_v2_x1_keep9.parquet": dict(size=os.path.getsize(f"{OUT}/feat_v2_x1_keep9.parquet"),
                                          md5=md5_of(f"{OUT}/feat_v2_x1_keep9.parquet")),
        "cand_dev_x1_lite.parquet": dict(size=os.path.getsize(f"{OUT}/cand_dev_x1_lite.parquet"),
                                          md5=md5_of(f"{OUT}/cand_dev_x1_lite.parquet")),
    }
)
with open(f"{OUT}/reduce_meta.json","w") as f:
    json.dump(meta, f, indent=2)
print(json.dumps(meta, indent=2))
