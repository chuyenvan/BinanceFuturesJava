"""FEE0 step0 data: download USDC-M 1m monthly klines (BTC/ETH), fundingRate monthly (all 40 USDC + BTC/ETH USDT), probe bookTicker/sizes."""
import json, os, sys, urllib.request, urllib.error
D = "https://data.binance.vision/data/futures/um"
WK = os.path.expanduser("~/claude_master/fee0_wk")
L = json.load(open(WK + "/usdc_listing.json"))
months = [f"{y}-{m:02d}" for y in (2024, 2025, 2026) for m in range(1, 13) if (y, m) <= (2026, 9)]


def get(url, dst):
    if os.path.exists(dst) and os.path.getsize(dst) > 0:
        return True
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    try:
        b = urllib.request.urlopen(url, timeout=120).read()
    except urllib.error.HTTPError as e:
        print("MISS", e.code, url); return False
    open(dst, "wb").write(b); return True


def head(url):
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=60)
        return int(r.headers.get("Content-Length", 0))
    except urllib.error.HTTPError as e:
        return -e.code


if sys.argv[1] == "btceth":
    for s in ("BTCUSDC", "ETHUSDC"):
        for m in months:
            get(f"{D}/monthly/klines/{s}/1m/{s}-1m-{m}.zip", f"{WK}/k1m/{s}/{s}-1m-{m}.zip")
    print("btceth done")
elif sys.argv[1] == "funding":
    for s in list(L) + ["BTCUSDT", "ETHUSDT"]:
        for m in months:
            get(f"{D}/monthly/fundingRate/{s}/{s}-fundingRate-{m}.zip", f"{WK}/fund/{s}/{s}-fundingRate-{m}.zip")
    print("funding done")
elif sys.argv[1] == "probe":
    tot = 0
    for s in L:
        sz = head(f"{D}/monthly/klines/{s}/1m/{s}-1m-2025-06.zip"); tot += max(sz, 0)
        print(s, "1m 2025-06 zip bytes", sz)
    print("sum one month all USDC", tot)
    for s in ("BTCUSDC", "ETHUSDC", "BTCUSDT"):
        for d in ("2024-01-10", "2024-02-15", "2024-03-20"):
            print(s, d, "bookTicker", head(f"{D}/daily/bookTicker/{s}/{s}-bookTicker-{d}.zip"))
