"""Dung kernel Kaggle A1: chen danh sach chan (sym, t0 ms UTC, entry) nam kham pha 2022+2024 — KHONG kem pnl."""
import json
import logging
import os
import sys

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
log = logging.getLogger("a1b")
PD = os.path.expanduser("~/kaggle_sim/out/gqsf-a1/storage/printDone.csv")
OUT = os.path.expanduser("~/claude_master/1016/a1/kernel_odd")
os.makedirs(OUT, exist_ok=True)
d = pd.read_csv(PD, index_col=False)
d = d[d.level != "DCA_LEVEL1"].copy()
d["t0"] = pd.to_datetime(d["start"], format="%Y%m%d %H:%M") - pd.Timedelta(hours=7)
d["n"] = d.groupby("t0").sym.transform("size")
d = d[(d.n >= 6) & (d.t0.dt.year.isin([2021, 2023, 2025]))]
legs = [{"sym": s, "t0": int(t.value // 10**6), "entry": float(e)} for s, t, e in zip(d.sym, d.t0, d.entry)]
log.info("chan %d, dot %d, theo nam %s", len(legs), d.t0.nunique(), d.t0.dt.year.value_counts().to_dict())
body = open("/tmp/a1_kernel_body.py", encoding="utf-8").read()
src = "# A1 perp discount — feature theo chan (PREREG_VZ_A1_PERP_DISCOUNT c4de0684). Khong co pnl.\n" \
      "LEGS = r'''" + json.dumps(legs) + "'''\n" + body
open(os.path.join(OUT, "a1-feat.py"), "w", encoding="utf-8").write(src)
srcs = [f"chuyendinh/vz-basis1m-{y}" for y in (2021, 2022, 2023, 2024, 2025)] + \
       [f"chuyendinh/vz-kline1m-{y}" for y in (2021, 2022, 2023, 2024, 2025)]
meta = {"id": "chuyendinh/vz-a1-feat-odd", "title": "vz-a1-feat-odd", "code_file": "a1-feat.py", "language": "python",
        "kernel_type": "script", "is_private": True, "enable_gpu": False, "enable_tpu": False,
        "enable_internet": False, "dataset_sources": srcs, "competition_sources": [], "kernel_sources": []}
json.dump(meta, open(os.path.join(OUT, "kernel-metadata.json"), "w"), indent=1)
log.info("kernel o %s", OUT)
