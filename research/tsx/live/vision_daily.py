#!/usr/bin/env python3
"""Vision UM 1m DAILY (data.binance.vision, file tinh) -> bin cung dinh dang tsx_prep.py cho TsxLiveOffline.
argv: ym day_from day_to  (vd 2026-10 2026-10-01 2026-10-19). Universe = active_2026-09 (Vision) U record 242 (cache 10-13..17)."""
import concurrent.futures as cf, io, logging, os, sys, time, urllib.request, zipfile  # noqa: E401

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout)
log = logging.getLogger("vd")
W = "/home/ubuntu/claude_master/v11_tsx/off/"
ym, d0, d1 = sys.argv[1:4]
days = [d.strftime("%Y-%m-%d") for d in pd.date_range(d0, d1, freq="D")]
syms = sorted(set(open(W + "active_2026-09.txt").read().split())
              | set(open(W + "cache_out/cache_1791922800000_1792198740000_syms.txt").read().split()))
URL = "https://data.binance.vision/data/futures/um/daily/klines/{s}/1m/{s}-1m-{d}.zip"


def get(sd):
    s, d = sd
    for k in range(3):
        try:
            with urllib.request.urlopen(URL.format(s=urllib.request.quote(s), d=d), timeout=30) as r:
                b = r.read()
            with zipfile.ZipFile(io.BytesIO(b)) as z:
                raw = z.read(z.namelist()[0]).decode()
            lines = [ln for ln in raw.splitlines() if ln and ln[0].isdigit()]
            a = np.array([ln.split(",") for ln in lines])
            return s, d, a[:, 0].astype(np.int64), a[:, 4].astype(np.float64), a[:, 7].astype(np.float64), 200
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return s, d, None, None, None, 404
            time.sleep(1 + k)
        except Exception:  # noqa: BLE001
            time.sleep(1 + k)
    return s, d, None, None, None, -1


jobs = [(s, d) for d in days for s in syms]
rows, st = [], {}
with cf.ThreadPoolExecutor(24) as ex:
    for s, d, ts, c, q, code in ex.map(get, jobs):
        st[code] = st.get(code, 0) + 1
        if ts is not None:
            rows.append(pd.DataFrame({"ts": ts, "sym": s, "close": c, "quote_volume": q}))
log.info("http %s", st)
if st.get(-1):
    log.warning("loi tai %d file", st[-1])
t = pd.concat(rows, ignore_index=True)
t = t.drop_duplicates(["sym", "ts"], keep="last").sort_values(["sym", "ts"], kind="mergesort").reset_index(drop=True)
SY = W + "syms.txt"
allsy = [s.strip() for s in open(SY)]
idx = {s: i for i, s in enumerate(allsy)}
for s in pd.unique(t["sym"]):
    if s not in idx:
        idx[s] = len(allsy)
        allsy.append(s)
open(SY, "w").write("\n".join(allsy) + "\n")
ids = t["sym"].map(idx).to_numpy(np.int32)
ts = t["ts"].to_numpy(np.int64)
o = np.lexsort((ids, ts))
out = W + "bin/%s_vd.bin" % ym
os.makedirs(W + "bin", exist_ok=True)
with open(out, "wb") as f:
    np.array([len(t)], dtype="<i8").tofile(f)
    ts[o].astype("<i8").tofile(f)
    ids[o].astype("<i4").tofile(f)
    t["close"].to_numpy(np.float64)[o].astype("<f8").tofile(f)
    t["quote_volume"].to_numpy(np.float64)[o].astype("<f8").tofile(f)
live = set(open(W + "cache_out/cache_1791922800000_1792198740000_syms.txt").read().split())
notlive = sorted(set(pd.unique(t["sym"])) - live)
open(W + "excl_notlive_%s.txt" % ym, "w").write("\n".join(notlive) + "\n")
log.info("vd %s rows=%d nsym=%d notlive=%d ts0=%s ts1=%s", ym, len(t), t["sym"].nunique(), len(notlive),
         pd.to_datetime(ts.min(), unit="ms"), pd.to_datetime(ts.max(), unit="ms"))
