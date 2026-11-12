#!/usr/bin/env python3
"""R4: liet ke dataset kline1m cua toi + kernel dang chay (chi doc)."""
import logging
import sys

sys.path.insert(0, "/home/ubuntu/claude_master/ho_tradfi_wk")
logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("probe")
from kaggle.api.kaggle_api_extended import KaggleApi  # noqa: E402

a = KaggleApi()
a.authenticate()
for x in a.dataset_list(mine=True, search="kline1m"):
    log.info("DS %s", x.ref)
for x in a.dataset_list(mine=True, search="gsm-s4"):
    log.info("DS %s", x.ref)
try:
    import notf_orch as N
    log.info("RUNNING %s", N.running())
except Exception as e:  # noqa: BLE001
    log.info("running? loi %s", e)
