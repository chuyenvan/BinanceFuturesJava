#!/usr/bin/env python3
"""HO4-P1: liet ke file (ten, bytes) cua cac dataset Kaggle tham chieu DEV. Usage: ho4p1_dsls.py ds1 ds2 ..."""
import logging, sys
from kaggle.api.kaggle_api_extended import KaggleApi
logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
a = KaggleApi(); a.authenticate()
for d in sys.argv[1:]:
    try:
        fs = a.dataset_list_files("chuyendinh/" + d).files
        logging.info("%s: %s", d, [(f.name, int(f.totalBytes or 0) // 1000000) for f in fs][:40])
    except Exception as e:  # noqa: BLE001
        logging.info("%s: ERR %s", d, str(e)[:100])
