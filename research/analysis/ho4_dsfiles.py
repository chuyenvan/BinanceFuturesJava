#!/usr/bin/env python3
"""HO4: liet ke file trong cac dataset Kaggle (ten, size). Usage: ho4_dsfiles.py ds1 ds2 ..."""
import logging, sys
from kaggle.api.kaggle_api_extended import KaggleApi
logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
a = KaggleApi(); a.authenticate()
for d in sys.argv[1:]:
    try:
        r = a.dataset_list_files("chuyendinh/" + d)
        fs = r.files
        logging.info("%s: %d file: %s", d, len(fs), [(f.name, getattr(f, "totalBytes", getattr(f, "total_bytes", ""))) for f in fs[:12]])
    except Exception as e:  # noqa: BLE001
        logging.info("%s ERR %s", d, e)
