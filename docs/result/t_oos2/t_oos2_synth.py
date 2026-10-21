#!/usr/bin/env python3
"""Tao du lieu TONG HOP (khong phai gia that) dang file Kaggle de kiem parser t_oos2_data_btc.py. Usage: python3 t_oos2_synth.py OUTDIR"""
import logging
import os
import sys
import zipfile

import numpy as np
import pandas as pd

log = logging.getLogger("synth")


def main():
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout)
    rng = np.random.default_rng(7)
    days = pd.date_range("2013-06-25", "2021-03-31", freq="D")
    rows, px, price = [], {}, 100.0
    for dd in days:
        base = int(dd.timestamp())
        price *= float(np.exp(rng.normal(0, 0.02)))
        px[dd.date()] = price
        for k, sec in enumerate((0, 600, 40000, 86399 - 60 * int(rng.integers(0, 90)))):
            rows.append((float(base + sec - sec % 60), price, price, price, price * (1 + 0.0001 * k), 1.0))
    d = pd.DataFrame(rows, columns=["Timestamp", "Open", "High", "Low", "Close", "Volume"])
    d.loc[d.sample(50, random_state=1).index, ["Open", "High", "Low", "Close"]] = np.nan
    d.to_csv(os.path.join(out, "synth_1min.csv"), index=False)
    with zipfile.ZipFile(os.path.join(out, "synth_1min.zip"), "w", zipfile.ZIP_DEFLATED) as z:
        z.write(os.path.join(out, "synth_1min.csv"), "btcusd_1-min_data.csv")
    dx = pd.DataFrame({"date": pd.date_range("2017-08-17", "2018-12-31").date})
    dx["close"] = [px[x] * 1.002 for x in dx["date"]]
    dx.to_csv(os.path.join(out, "synth_binance.csv"), index=False)
    log.info("rows=%d", len(d))


if __name__ == "__main__":
    main()
