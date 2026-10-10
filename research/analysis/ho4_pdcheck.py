#!/usr/bin/env python3
"""HO4: kiem bien SEAL trong printDone ho26 s42 (chi dem dong, khong doc pnl)."""
import logging, sys
import pandas as pd
logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
for r in ["ho26-k24-s-s42", "ho26-b0-s-s42"]:
    d = pd.read_csv("/home/ubuntu/kaggle_sim/out/%s/storage/printDone.csv" % r, index_col=False, usecols=["sym", "start", "end", "status"])
    st, en = d["start"].astype(str).str.strip(), d["end"].astype(str).str.strip()
    a = st < "20260101 00:00"
    logging.info("%s rows=%d start<SEAL=%d start<SEAL&end>=SEAL=%d status_counts_dev=%s last_end_dev=%s", r, len(d), a.sum(),
                 (a & (en >= "20260101 00:00")).sum(), d.loc[a, "status"].value_counts().to_dict(), en[a].max())
