#!/usr/bin/env python3
"""HO4: liet ke dataset Kaggle cua tai khoan (ten, size) — de chon input cho kernel lat DEV."""
import logging, sys
from kaggle.api.kaggle_api_extended import KaggleApi
logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
a = KaggleApi(); a.authenticate()
for p in range(1, 8):
    L = a.dataset_list(mine=True, page=p)
    if not L:
        break
    for d in L:
        logging.info("%s %s %s", d.ref, getattr(d, "total_bytes", getattr(d, "totalBytes", "")), getattr(d, "last_updated", getattr(d, "lastUpdated", "")))
