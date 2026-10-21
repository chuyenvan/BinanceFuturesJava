#!/usr/bin/env python3
"""T_OOS2: tai file Kaggle goc (Bitstamp 1-min) vao thu muc rieng. Khong doc noi dung. Usage: python3 t_oos2_kaggle_dl.py RAWDIR"""
import logging
import os
import sys

from kaggle.api.kaggle_api_extended import KaggleApi

log = logging.getLogger("kgdl")


def main():
    raw = sys.argv[1]
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout)
    os.makedirs(raw, exist_ok=True)
    a = KaggleApi()
    a.authenticate()
    a.dataset_download_file("mczielinski/bitcoin-historical-data", "btcusd_1-min_data.csv", path=raw, force=True, quiet=True)
    for n in sorted(os.listdir(raw)):
        log.info("%s %d bytes", n, os.path.getsize(os.path.join(raw, n)))


if __name__ == "__main__":
    main()
