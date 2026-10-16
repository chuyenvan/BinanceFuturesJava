"""CVX tai du lieu (PREREG_CVX.md b01558e1). Usage: cv_data.py [vision|coinbase|upbit|bybit|all]. KHONG goi Binance REST."""
import io
import json
import logging
import os
import sys
import time
import urllib.request
import zipfile
from datetime import datetime, timedelta, timezone

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("cvd")
W = os.path.expanduser("~/claude_master/1016/cvx")
SW = os.path.expanduser("~/claude_master/1016/screen")
os.makedirs(W, exist_ok=True)
T0 = datetime(2021, 1, 1, tzinfo=timezone.utc)
T1 = datetime(2026, 10, 1, tzinfo=timezone.utc)
UA = {"User-Agent": "Mozilla/5.0 research"}


def get(url, tries=6):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001
            code = getattr(e, "code", None)
            if code == 404:
                return None
            time.sleep(1.5 * (i + 1))
            log.warning("retry %s %s %s", i, code, url[:120])
    raise RuntimeError("fail " + url)


def vision():
    for s in ("BTCUSDT", "ETHUSDT"):
        parts = []
        d = datetime(2021, 1, 1)
        while d < datetime(2026, 10, 1):
            ym = d.strftime("%Y-%m")
            b = get(f"https://data.binance.vision/data/spot/monthly/klines/{s}/1h/{s}-1h-{ym}.zip")
            if b:
                with zipfile.ZipFile(io.BytesIO(b)) as z:
                    x = pd.read_csv(io.BytesIO(z.read(z.namelist()[0])), header=None)
                if not str(x.iloc[0, 0]).strip().isdigit():
                    x = x.iloc[1:]
                x = x.iloc[:, [0, 4]].astype(float)
                x.columns = ["ot", "close"]
                x["ot"] = x.ot.where(x.ot < 1e14, x.ot / 1000)
                parts.append(x)
            d = (d.replace(day=28) + timedelta(days=4)).replace(day=1)
        M = pd.concat(parts)
        M["t"] = pd.to_datetime(M.ot, unit="ms")
        M = M.drop_duplicates("t").set_index("t").sort_index()[["close"]]
        M.to_parquet(f"{W}/bn_spot_1h_{s}.parquet")
        log.info("vision %s %d gio %s..%s", s, len(M), M.index.min(), M.index.max())


def coinbase():
    for p in ("BTC-USD", "ETH-USD"):
        rows = []
        t = T0
        while t < T1:
            e = min(t + timedelta(hours=300), T1)
            u = f"https://api.exchange.coinbase.com/products/{p}/candles?granularity=3600&start={t:%Y-%m-%dT%H:%M:%SZ}&end={e:%Y-%m-%dT%H:%M:%SZ}"
            rows += json.loads(get(u))
            t = e
            time.sleep(0.2)
        M = pd.DataFrame(rows, columns=["ts", "low", "high", "open", "close", "vol"])
        M["t"] = pd.to_datetime(M.ts, unit="s")
        M = M.drop_duplicates("t").set_index("t").sort_index()[["close", "vol"]]
        M = M[(M.index >= "2021-01-01") & (M.index < "2026-10-01")]
        M.to_parquet(f"{W}/cb_1h_{p}.parquet")
        log.info("coinbase %s %d gio", p, len(M))


def bn_syms():
    D = pd.read_parquet(SW + "/d1.parquet", columns=["sym"])
    return sorted(D.sym.unique())


def base_of(sym):
    b = sym[:-4]
    for pre, f in (("1000000", 1e6), ("1000", 1e3)):
        if b.startswith(pre) and len(b) > len(pre):
            return b[len(pre):], f
    return b, 1.0


def upbit():
    mk = {x["market"][4:] for x in json.loads(get("https://api.upbit.com/v1/market/all")) if x["market"].startswith("KRW-")}
    pairs = []
    for s in bn_syms():
        b, f = base_of(s)
        if b in mk:
            pairs.append((s, b, f))
    log.info("upbit: %d KRW market, trung Binance %d", len(mk), len(pairs))
    rows = []
    for k, (s, b, f) in enumerate(pairs):
        to = T1
        while True:
            u = f"https://api.upbit.com/v1/candles/days?market=KRW-{b}&count=200&to={to:%Y-%m-%dT%H:%M:%S}Z"
            x = json.loads(get(u))
            time.sleep(0.13)
            if not x:
                break
            for c in x:
                rows.append((s, b, f, c["candle_date_time_utc"][:10], c["trade_price"], c["candle_acc_trade_price"]))
            first = min(c["candle_date_time_utc"] for c in x)
            to = datetime.fromisoformat(first).replace(tzinfo=timezone.utc)
            if to <= T0 or len(x) < 200:
                break
        if k % 20 == 0:
            log.info("upbit %d/%d %s rows %d", k, len(pairs), b, len(rows))
    U = pd.DataFrame(rows, columns=["sym", "base", "fac", "day", "close_krw", "turnover_krw"])
    U["day"] = pd.to_datetime(U.day)
    U = U.drop_duplicates(["sym", "day"])
    U = U[(U.day >= "2021-01-01") & (U.day < "2026-10-01")]
    U.to_parquet(W + "/upbit_1d.parquet")
    log.info("upbit xong %d dong %d sym", len(U), U.sym.nunique())


def bybit():
    syms, cur = [], ""
    while True:
        x = json.loads(get(f"https://api.bybit.com/v5/market/instruments-info?category=linear&limit=1000&cursor={cur}"))["result"]
        syms += [i["symbol"] for i in x["list"] if i.get("quoteCoin") == "USDT" and i.get("contractType") == "LinearPerpetual"]
        cur = x.get("nextPageCursor") or ""
        if not cur:
            break
    common = sorted(set(syms) & set(bn_syms()))
    log.info("bybit %d perp USDT, trung Binance %d", len(syms), len(common))
    rows = []
    t0 = int(T0.timestamp() * 1000)
    for k, s in enumerate(common):
        end = int(T1.timestamp() * 1000)
        while True:
            x = json.loads(get(f"https://api.bybit.com/v5/market/funding/history?category=linear&symbol={s}&endTime={end}&limit=200"))["result"]["list"]
            time.sleep(0.06)
            if not x:
                break
            ts = [int(i["fundingRateTimestamp"]) for i in x]
            rows += [(s, int(i["fundingRateTimestamp"]), float(i["fundingRate"])) for i in x]
            end = min(ts) - 1
            if end < t0 or len(x) < 200:
                break
        if k % 25 == 0:
            log.info("bybit %d/%d %s rows %d", k, len(common), s, len(rows))
    B = pd.DataFrame(rows, columns=["sym", "ts", "rate"]).drop_duplicates(["sym", "ts"])
    B["day"] = pd.to_datetime(B.ts, unit="ms").dt.floor("D")
    B = B[(B.day >= "2021-01-01") & (B.day < "2026-10-01")]
    B.to_parquet(W + "/bybit_funding.parquet")
    log.info("bybit xong %d dong %d sym", len(B), B.sym.nunique())


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    for name, fn in (("vision", vision), ("coinbase", coinbase), ("upbit", upbit), ("bybit", bybit)):
        if what in (name, "all"):
            fn()
