"""CARRY_OPP buoc du lieu: tin hieu s tu funding (causal), danh sach (sym, thang) can kline, tai Vision 1d spot+perp."""
import concurrent.futures as cf
import glob
import io
import logging
import os
import sys
import time
import urllib.error
import urllib.request
import zipfile

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("co")
W = os.path.expanduser("~/claude_master/1016/carry")
THR = 0.0001
STABLE = ("USDC", "FDUSD", "TUSD", "BUSD", "DAI", "EUR", "PAXG", "WBTC", "USDP", "UST", "AEUR", "XUSD", "USD1", "BFUSD")
URL = {"spot": "https://data.binance.vision/data/spot/monthly/klines/{s}/1d/{s}-1d-{m}.zip",
       "perp": "https://data.binance.vision/data/futures/um/monthly/klines/{s}/1d/{s}-1d-{m}.zip"}


def funding():
    f = pd.concat([pd.read_parquet(p) for p in sorted(glob.glob(W + "/fund/funding-*.parquet"))], ignore_index=True)
    f = f[f.sym.str.endswith("USDT") & ~f.sym.str[:-4].isin(STABLE)]
    f["day"] = pd.to_datetime(f.ts, unit="ms").dt.floor("D")
    daily = f.groupby(["sym", "day"]).rate.sum().rename("fund_day").reset_index()  # funding settle trong ngay UTC
    return daily


def signal(daily):
    out = []
    for s, g in daily.groupby("sym"):
        g = g.set_index("day").fund_day.asfreq("D", fill_value=0.0)
        # s(t) dung funding ngay < t: tong 30 ngay [t-30, t-1] / 90
        sig = g.rolling(30, min_periods=30).sum().shift(1) / 90.0
        out.append(pd.DataFrame({"sym": s, "day": g.index, "fund_day": g.values, "s": sig.values}))
    return pd.concat(out, ignore_index=True)


def get(job):
    kind, s, m = job
    p = f"{W}/k/{kind}/{s}/{m}.zip"
    if os.path.exists(p):
        return job, "have"
    os.makedirs(os.path.dirname(p), exist_ok=True)
    for i in range(3):
        try:
            with urllib.request.urlopen(URL[kind].format(s=s, m=m), timeout=60) as r:
                b = r.read()
            open(p + ".tmp", "wb").write(b); os.replace(p + ".tmp", p)
            return job, "ok"
        except urllib.error.HTTPError as e:
            if e.code == 404:
                open(p + ".404", "w").close() if False else None
                return job, "404"
            time.sleep(2 * (i + 1))
        except Exception:  # noqa: BLE001
            time.sleep(2 * (i + 1))
    return job, "fail"


def main():
    daily = funding()
    S = signal(daily)
    S.to_parquet(W + "/signal.parquet")
    on = S[S.s > THR].copy()
    on["m"] = on.day.dt.strftime("%Y-%m")
    months = set()
    for s, g in on.groupby("sym"):
        for m in g.m.unique():
            p = pd.Period(m, "M")
            months.update({(s, str(p)), (s, str(p - 1))})
    # 2021 cho moi perp (de xep hang thanh khoan G3)
    for s in daily[daily.day.dt.year == 2021].sym.unique():
        for mm in range(1, 13):
            months.add((s, f"2021-{mm:02d}"))
    jobs = sorted({("perp", s, m) for s, m in months} | {("spot", s, m) for s, m in months if m >= "2021-01"})
    jobs = [j for j in jobs if "2021-01" <= j[2] <= "2026-09"]
    log.info("sym co tin hieu bat: %d / %d; (sym,thang) %d; jobs %d", on.sym.nunique(), S.sym.nunique(), len(months), len(jobs))
    st = {}
    with cf.ThreadPoolExecutor(8) as ex:
        for i, (j, r) in enumerate(ex.map(get, jobs)):
            st[r] = st.get(r, 0) + 1
            if i % 2000 == 0:
                log.info("fetch %d/%d %s", i, len(jobs), st)
    log.info("fetch DONE %s", st)


if __name__ == "__main__":
    main()
