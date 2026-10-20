#!/usr/bin/env python3
"""TS_MKT_EXT live offline (a): parquet Kaggle vz-kline1m-<ym> -> bin cho TsxLiveOffline (Java live code).
Dung DUNG read_month cua edge_attr_build.py (trich ast, giong tsx_ew_local.py). Bin: int64 n | ts<i8 | id<i4 | close<f8 | qv<f8,
sap theo (ts, id). Xoa parquet sau moi thang."""
import ast, glob, logging, os, sys, zipfile  # noqa: E401

import numpy as np
import pandas as pd  # noqa: F401
import pyarrow.parquet as pq  # noqa: F401

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout)
log = logging.getLogger("tsxprep")
W = "/home/ubuntu/claude_master/v11_tsx/off"
KL, BIN = W + "/kl", W + "/bin"
os.makedirs(KL, exist_ok=True)
os.makedirs(BIN, exist_ok=True)
MIN = 60000
src = open("/home/ubuntu/claude_master/edge_attr/edge_attr_build.py").read()
for n in ast.parse(src).body:
    if isinstance(n, ast.FunctionDef) and n.name == "read_month":
        exec(compile(ast.get_source_segment(src, n), "eab", "exec"), globals())

from kaggle.api.kaggle_api_extended import KaggleApi  # noqa: E402
A = KaggleApi()
A.authenticate()


def kp(ym):
    p = KL + "/kline1m-%s.parquet" % ym
    if not os.path.exists(p):
        A.dataset_download_file("chuyendinh/vz-kline1m-%s" % ym[:4], "kline1m-%s.parquet" % ym, path=KL, quiet=True)
        for z in glob.glob(KL + "/*.zip"):
            with zipfile.ZipFile(z) as f:
                f.extractall(KL)
            os.remove(z)
    return p if os.path.exists(p) else None


SY = W + "/syms.txt"
syms = [s.strip() for s in open(SY)] if os.path.exists(SY) else []
idx = {s: i for i, s in enumerate(syms)}
for ym in sys.argv[1:]:
    out = BIN + "/%s.bin" % ym
    if os.path.exists(out):
        log.info("skip %s", ym)
        continue
    t = read_month(ym)  # noqa: F821
    if t is None:
        raise SystemExit("MISS " + ym)
    for s in pd.unique(t["sym"]):
        if s not in idx:
            idx[s] = len(syms)
            syms.append(s)
    ids = t["sym"].map(idx).to_numpy(np.int32)
    ts = t["ts"].to_numpy(np.int64)
    o = np.lexsort((ids, ts))
    with open(out + ".tmp", "wb") as f:
        np.array([len(t)], dtype="<i8").tofile(f)
        ts[o].astype("<i8").tofile(f)
        ids[o].astype("<i4").tofile(f)
        t["close"].to_numpy(np.float64)[o].astype("<f8").tofile(f)
        t["quote_volume"].to_numpy(np.float64)[o].astype("<f8").tofile(f)
    os.rename(out + ".tmp", out)
    last = ts.max()
    act = sorted(pd.unique(t["sym"][ts >= last - 59 * MIN]))
    open(W + "/active_%s.txt" % ym, "w").write("\n".join(act) + "\n")
    open(SY, "w").write("\n".join(syms) + "\n")
    suf = pd.Series(pd.unique(t["sym"])).str.extract(r"(USDT|USDC|BUSD)$")[0].fillna("OTHER").value_counts().to_dict()
    log.info("prep %s rows=%d nsym=%d suffix=%s ts0=%s ts1=%s", ym, len(t), t["sym"].nunique(), suf,
             pd.to_datetime(ts.min(), unit="ms"), pd.to_datetime(ts.max(), unit="ms"))
    for p in glob.glob(KL + "/kline1m-%s.parquet" % ym):
        os.remove(p)
