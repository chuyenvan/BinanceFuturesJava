#!/usr/bin/env python3
"""Dem kernel RUNNING/QUEUED toan tai khoan (20 kernel chay gan nhat). In: n_active + danh sach."""
import sys
from kaggle.api.kaggle_api_extended import KaggleApi
a = KaggleApi(); a.authenticate()
act = []
for k in a.kernels_list(mine=True, page_size=20, sort_by="dateRun"):
    try:
        r = a.kernels_status(k.ref)
        st = str(r.get("status") if isinstance(r, dict) else getattr(r, "status", r)).split(".")[-1].upper()
    except Exception as e:  # noqa: BLE001
        st = "ERR"
    if st in ("RUNNING", "QUEUED"):
        act.append((k.ref, st))
print("ACTIVE", len(act), act)
