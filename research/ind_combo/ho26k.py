"""IND_COMBO P0 (prereg vz_e1_wt 14ed6c00) kernel ind-ho26: dung nen 1h tu vz-kline1m-2026 (2026-01..06) cho HO MO TA.
Output /kaggle/working/ho26_1h.parquet (sym, th=gio DONG ms, o,h,l,c,qv, sr, sr2, n = tong r, r^2, so phut r 1m trong gio)
       /kaggle/working/ho26_ew.parquet (ts phut, ew = TB log-ret 1m tru BTC/ETH, qv>0 2 nen, cat +-0.5)."""
import glob
import json
import logging
import time

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("ho26")
M1, H = 60000, 3600000
F = {p.split("kline1m-")[-1][:7]: p for p in glob.glob("/kaggle/input/**/kline1m-2026-*.parquet", recursive=True)}
log.info("files %s", sorted(F))
MON = ["2026-%02d" % m for m in range(1, 7)]
assert all(m in F for m in MON), "thieu thang"
sch = pq.ParquetFile(F[MON[0]]).schema_arrow
names = [x.name for x in sch]
log.info("schema %s", [(x.name, str(x.type)) for x in sch])


def pick(*c):
    for x in c:
        if x in names:
            return x
    raise SystemExit("khong thay cot %s" % (c,))


CT, CS = pick("ts", "open_time", "t"), pick("sym", "symbol")
CO, CH, CL, CC = pick("open", "o"), pick("high", "h"), pick("low", "l"), pick("close", "c")
CQ = pick("quote_volume", "qv", "quoteVolume", "quote_asset_volume")
out, ew = [], []
t0 = time.time()
for ym in MON:
    d = pq.read_table(F[ym], columns=[CT, CS, CO, CH, CL, CC, CQ]).to_pandas()
    d.columns = ["ts", "sym", "o", "h", "l", "c", "qv"]
    d["sym"] = d["sym"].astype(str)
    d["ts"] = d["ts"].astype(np.int64)
    if d["ts"].max() < 10 ** 12:
        d["ts"] *= 1000
    d = d.drop_duplicates(["sym", "ts"], keep="last").sort_values(["sym", "ts"]).reset_index(drop=True)
    for c in ("o", "h", "l", "c", "qv"):
        d[c] = d[c].astype(np.float64)
    same = (d["sym"].values[1:] == d["sym"].values[:-1]) & (np.diff(d["ts"].values) == M1)
    lr = np.full(len(d), np.nan)
    with np.errstate(divide="ignore", invalid="ignore"):
        lr[1:] = np.where(same, np.log(d["c"].values[1:] / d["c"].values[:-1]), np.nan)
    d["r"] = lr
    d["th"] = (d["ts"] // H) * H + H
    g = d.groupby(["sym", "th"], sort=True)
    a = g.agg(o=("o", "first"), h=("h", "max"), l=("l", "min"), c=("c", "last"), qv=("qv", "sum")).reset_index()
    rr = d[np.isfinite(d["r"])]
    rr = rr.assign(r2=rr["r"] ** 2)
    b = rr.groupby(["sym", "th"]).agg(sr=("r", "sum"), sr2=("r2", "sum"), n=("r", "size")).reset_index()
    a = a.merge(b, on=["sym", "th"], how="left")
    out.append(a)
    okq = np.zeros(len(d), bool)
    okq[1:] = same & (d["qv"].values[1:] > 0) & (d["qv"].values[:-1] > 0)
    e = d[okq & ~d["sym"].isin(["BTCUSDT", "ETHUSDT"]).values & np.isfinite(lr)]
    ew.append(e.assign(r=e["r"].clip(-0.5, 0.5)).groupby("ts")["r"].mean().rename("ew").reset_index())
    log.info("%s rows %d sym %d gio %d %ds", ym, len(d), d["sym"].nunique(), len(a), round(time.time() - t0))
    del d, rr, e
A = pd.concat(out, ignore_index=True)
A.to_parquet("/kaggle/working/ho26_1h.parquet", index=False)
E = pd.concat(ew, ignore_index=True)
E.to_parquet("/kaggle/working/ho26_ew.parquet", index=False)
json.dump(dict(n=len(A), nsym=int(A.sym.nunique()), th0=int(A.th.min()), th1=int(A.th.max()), n_ew=len(E)),
          open("/kaggle/working/ho26_meta.json", "w"))
log.info("HO26_DONE %d", len(A))
