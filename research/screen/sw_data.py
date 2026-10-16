"""SCREEN_WIDE du lieu: Vision BTC/ETH 1m monthly + moi perp USDT 1d monthly (theo khoang song tu funding lake)."""
import concurrent.futures as cf
import glob
import logging
import os
import sys
import time
import urllib.error
import urllib.request

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("swd")
W = os.path.expanduser("~/claude_master/1016/screen")
CARRY = os.path.expanduser("~/claude_master/1016/carry")
U1M = "https://data.binance.vision/data/futures/um/monthly/klines/{s}/1m/{s}-1m-{m}.zip"
U1D = "https://data.binance.vision/data/futures/um/monthly/klines/{s}/1d/{s}-1d-{m}.zip"


def get(job):
    url, p = job
    if os.path.exists(p) or os.path.exists(p + ".404"):
        return "have"
    os.makedirs(os.path.dirname(p), exist_ok=True)
    for i in range(4):
        try:
            with urllib.request.urlopen(url, timeout=90) as r:
                b = r.read()
            open(p + ".tmp", "wb").write(b); os.replace(p + ".tmp", p)
            return "ok"
        except urllib.error.HTTPError as e:
            if e.code == 404:
                open(p + ".404", "w").close()
                return "404"
            time.sleep(2 * (i + 1))
        except Exception:  # noqa: BLE001
            time.sleep(2 * (i + 1))
    return "fail"


def main():
    months = [str(p) for p in pd.period_range("2021-01", "2026-09", freq="M")]
    jobs = [(U1M.format(s=s, m=m), f"{W}/k1m/{s}/{m}.zip") for s in ("BTCUSDT", "ETHUSDT") for m in months]
    f = pd.concat([pd.read_parquet(p) for p in sorted(glob.glob(CARRY + "/fund/funding-*.parquet"))])
    f = f[f.sym.str.endswith("USDT")]
    span = f.groupby("sym").ts.agg(["min", "max"])
    for s, r in span.iterrows():
        a = pd.Timestamp(r["min"], unit="ms").to_period("M"); b = pd.Timestamp(r["max"], unit="ms").to_period("M")
        for m in pd.period_range(max(a, pd.Period("2020-12", "M")), min(b, pd.Period("2026-09", "M")), freq="M"):
            m = str(m)
            src = f"{CARRY}/k/perp/{s}/{m}.zip"
            dst = f"{W}/k1d/{s}/{m}.zip"
            if os.path.exists(src) and not os.path.exists(dst):
                os.makedirs(os.path.dirname(dst), exist_ok=True); os.link(src, dst)
            jobs.append((U1D.format(s=s, m=m), dst))
    log.info("jobs %d (1m %d)", len(jobs), 2 * len(months))
    st = {}
    with cf.ThreadPoolExecutor(8) as ex:
        for i, r in enumerate(ex.map(get, jobs)):
            st[r] = st.get(r, 0) + 1
            if i % 4000 == 0:
                log.info("%d/%d %s", i, len(jobs), st)
    log.info("DONE %s", st)


if __name__ == "__main__":
    main()
