"""FS survey 3: doi chieu convention timestamp CLOSES_1H vs Vision 1h kline (co header)."""
import logging, sys, io, zipfile, urllib.request
import numpy as np, pandas as pd
logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
L = logging.getLogger(__name__)

COLS = ["ot", "o", "h", "l", "c", "v", "ct", "qv", "n", "tbv", "tbqv", "ig"]


def get_kl(sym, ym):
    url = ("https://data.binance.vision/data/futures/um/monthly/klines/"
           f"{sym}/1h/{sym}-1h-{ym}.zip")
    raw = urllib.request.urlopen(url, timeout=120).read()
    z = zipfile.ZipFile(io.BytesIO(raw))
    K = pd.read_csv(z.open(z.namelist()[0]), header=None, names=COLS,
                    dtype=str, engine="c")
    K = K[pd.to_numeric(K.ot, errors="coerce").notna()].copy()
    for c in COLS:
        K[c] = pd.to_numeric(K[c], errors="coerce")
    K["ot"] = K.ot.astype(np.int64)
    return K


DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("c", ">f4")])
a = np.fromfile("/home/ubuntu/java/fsrun/CLOSES_1H.bin", dtype=DT)
mp = pd.read_csv("/home/ubuntu/selector_pred_out/symbol_map.csv")
s2i = dict(zip(mp.symbol, mp.symId))

for sname, ym, t0, t1 in (("BTCUSDT", "2022-03", "2022-03-01", "2022-04-01"),
                          ("ETHUSDT", "2023-08", "2023-08-01", "2023-09-01")):
    sid = s2i[sname]
    m = a["sym"].astype(np.int32) == sid
    df = pd.DataFrame({"ts": a["ts"][m].astype(np.int64),
                       "c": a["c"][m].astype(np.float64)})
    lo = int(pd.Timestamp(t0).value // 1e6)
    hi = int(pd.Timestamp(t1).value // 1e6)
    df = df[(df.ts >= lo) & (df.ts < hi)].sort_values("ts")
    K = get_kl(sname, ym)
    L.info("%s closes=%d kline=%d ot %s..%s", sname, len(df), len(K),
           pd.to_datetime(K.ot.min(), unit="ms"), pd.to_datetime(K.ot.max(), unit="ms"))
    for lag, lab in ((0, "ot == ts (bar BAT DAU tai ts -> TUONG LAI)"),
                     (3600000, "ot+1h == ts (bar DONG tai ts -> qua khu, OK)")):
        kk = K[["ot", "c"]].copy()
        kk["ts"] = kk.ot + lag
        j = df.merge(kk[["ts", "c"]].rename(columns={"c": "kc"}), on="ts", how="inner")
        if len(j) == 0:
            L.info("   %s n=0", lab)
            continue
        d = (j.c - j.kc).abs() / j.c
        L.info("   %s n=%d maxrelerr=%.3e mean=%.3e", lab, len(j), d.max(), d.mean())
    L.info("   sample qv=%.0f n=%s tbqv=%.0f", K.qv.iloc[10], K.n.iloc[10], K.tbqv.iloc[10])
L.info("DONE")
