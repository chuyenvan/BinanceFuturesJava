#!/usr/bin/env python3
"""HO4-P0: liet ke symbol co lenh DEV trong lat 2025-07-01..2025-12-31 (+07) tu printDone DEV (start < 2026-01-01).
Chi dem lenh/symbol (KHONG doc pnl). Usage: ho4_devsyms.py <out.json>"""
import json, logging, sys
import pandas as pd
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout)
log = logging.getLogger("ho4_devsyms")
OUT = "/home/ubuntu/kaggle_sim/out/%s/storage/printDone.csv"
RUNS = ["ho26-k24-s-s42", "ho26-b0-s-s42", "gqsf-a1", "de-p1", "nsel-m2-s42", "ho1-c1", "ho1-c2", "ho1-c3"]
res, allsym = {}, set()
for r in RUNS:
    try:
        d = pd.read_csv(OUT % r, index_col=False, usecols=["sym", "start"])
    except Exception as e:  # noqa: BLE001
        log.info("skip %s %s", r, e)
        continue
    st = d["start"].astype(str).str.strip()
    m = (st >= "20250701 00:00") & (st < "20260101 00:00")
    m2 = (st >= "20251121 00:00") & (st < "20260101 00:00")
    s = sorted(set(d.loc[m, "sym"].astype(str)))
    res[r] = dict(n_slice=int(m.sum()), n_after_1121=int(m2.sum()), n_sym=len(s), last_start=str(st[st < "20260101 00:00"].max()))
    if r in ("ho26-k24-s-s42", "ho26-b0-s-s42", "gqsf-a1", "de-p1", "nsel-m2-s42"):
        allsym |= set(s)
    log.info("%s %s", r, res[r])
res["union_syms"] = sorted(allsym)
res["n_union"] = len(allsym)
json.dump(res, open(sys.argv[1], "w"), indent=1)
log.info("union %d symbol", len(allsym))
