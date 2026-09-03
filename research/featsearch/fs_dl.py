"""FS buoc 2a: tai kline 1h tu data.binance.vision -> cache npz theo symbol.
Khong ghi CSV ra dia: giai nen trong bo nho, parse, luu npz nen.
Chi tai thang can (2021-01..2024-06). Universe = symbol co trong CLOSES_1H 2021-01..2024-07."""
import logging, sys, os, io, zipfile, urllib.request, urllib.error, time
import concurrent.futures as cf
import numpy as np, pandas as pd
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout)
L = logging.getLogger(__name__)

OUT = "/home/ubuntu/fs/kl"
os.makedirs(OUT, exist_ok=True)
COLS = ["ot", "o", "h", "l", "c", "v", "ct", "qv", "n", "tbv", "tbqv", "ig"]
KEEP = ["ot", "o", "h", "l", "c", "v", "qv", "n", "tbqv"]
MONTHS = [f"{y}-{m:02d}" for y in (2021, 2022, 2023) for m in range(1, 13)]
MONTHS += [f"2024-{m:02d}" for m in range(1, 7)]

DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("c", ">f4")])
a = np.fromfile("/home/ubuntu/java/fsrun/CLOSES_1H.bin", dtype=DT)
ts = a["ts"].astype(np.int64)
sy = a["sym"].astype(np.int32)
m = (ts >= 1609459200000) & (ts < 1719792000000)
uids = np.unique(sy[m])
mp = pd.read_csv("/home/ubuntu/selector_pred_out/symbol_map.csv")
i2s = dict(zip(mp.symId, mp.symbol))
UNI = [(int(s), i2s[int(s)]) for s in uids if int(s) in i2s]
L.info("universe %d symbol, %d thang", len(UNI), len(MONTHS))
del a, ts, sy


def one_month(sname, ym):
    url = ("https://data.binance.vision/data/futures/um/monthly/klines/"
           f"{sname}/1h/{sname}-1h-{ym}.zip")
    for att in range(3):
        try:
            raw = urllib.request.urlopen(url, timeout=90).read()
            break
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            time.sleep(1 + att)
        except Exception:
            time.sleep(1 + att)
    else:
        L.info("FAIL %s %s", sname, ym)
        return None
    z = zipfile.ZipFile(io.BytesIO(raw))
    K = pd.read_csv(z.open(z.namelist()[0]), header=None, names=COLS, dtype=str)
    K = K[pd.to_numeric(K.ot, errors="coerce").notna()]
    if len(K) == 0:
        return None
    out = {}
    out["ot"] = pd.to_numeric(K.ot).astype(np.int64).to_numpy()
    for c in KEEP[1:]:
        out[c] = pd.to_numeric(K[c], errors="coerce").astype(np.float32).to_numpy()
    return out


def one_sym(sid, sname):
    f = f"{OUT}/{sid}.npz"
    if os.path.exists(f):
        return sid, -1
    parts = [one_month(sname, ym) for ym in MONTHS]
    parts = [p for p in parts if p is not None]
    if not parts:
        np.savez_compressed(f, ot=np.zeros(0, np.int64))
        return sid, 0
    d = {k: np.concatenate([p[k] for p in parts]) for k in KEEP}
    o = np.argsort(d["ot"], kind="stable")
    d = {k: v[o] for k, v in d.items()}
    _, keep = np.unique(d["ot"], return_index=True)
    d = {k: v[keep] for k, v in d.items()}
    np.savez_compressed(f, **d)
    return sid, len(d["ot"])


t0 = time.time()
done = 0
with cf.ThreadPoolExecutor(max_workers=10) as ex:
    futs = [ex.submit(one_sym, sid, sn) for sid, sn in UNI]
    for fu in cf.as_completed(futs):
        sid, n = fu.result()
        done += 1
        if done % 25 == 0:
            L.info("%d/%d done, last sid=%d n=%d, %.0fs",
                   done, len(UNI), sid, n, time.time() - t0)
sz = sum(os.path.getsize(f"{OUT}/{f}") for f in os.listdir(OUT))
L.info("DONE %d symbol, cache %.1f MB, %.0fs", len(UNI), sz / 1e6, time.time() - t0)
