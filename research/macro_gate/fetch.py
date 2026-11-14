#!/usr/bin/env python3
"""MACRO_GATE P0 (prereg vz_e1_wt 24104dd6 §1): tai OHLCV ngay ETF tu 2 nguon cong khai khong key (Yahoo chart v8, Nasdaq api).
Luu raw JSON vao ~/claude_master/macro1114/raw/. Khong doc Y."""
import json
import logging
import os
import time
import subprocess

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("fetch")
R = os.path.expanduser("~/claude_master/macro1114/raw/")
TIC = ["QQQ", "XLP", "GLD", "UUP", "IBIT", "FBTC", "ARKB", "BITB", "HODL", "BRRR"]
P1, P2 = 1633046400, 1782864000  # 2021-10-01 .. 2026-07-01 UTC
HD = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36",
      "Accept": "application/json, text/plain, */*", "Accept-Language": "en-US,en;q=0.9"}


def get(url, out):
    for k in range(3):
        try:
            cmd = ["curl", "-s", "-m", "60", "--compressed", "-A", HD["User-Agent"], "-H", "Accept: " + HD["Accept"],
                   "-H", "Accept-Language: " + HD["Accept-Language"], url]
            b = subprocess.run(cmd, capture_output=True, timeout=90).stdout
            json.loads(b)
            open(out, "wb").write(b)
            log.info("OK %s %d bytes", os.path.basename(out), len(b))
            return True
        except Exception as e:  # noqa: BLE001
            log.warning("loi %s lan %d: %s", os.path.basename(out), k, e)
            time.sleep(3 + 5 * k)
    return False


def main():
    os.makedirs(R, exist_ok=True)
    for t in TIC:
        get("https://query1.finance.yahoo.com/v8/finance/chart/%s?period1=%d&period2=%d&interval=1d&events=div%%7Csplit&includeAdjustedClose=true" % (t, P1, P2),
            R + "yahoo_%s.json" % t)
        time.sleep(1)
        get("https://api.nasdaq.com/api/quote/%s/historical?assetclass=etf&fromdate=2021-10-01&todate=2026-06-30&limit=9999" % t,
            R + "nasdaq_%s.json" % t)
        time.sleep(1)
        get("https://api.nasdaq.com/api/quote/%s/dividends?assetclass=etf" % t, R + "nasdaqdiv_%s.json" % t)
        time.sleep(1)


if __name__ == "__main__":
    main()
