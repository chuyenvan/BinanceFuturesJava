"""Chan doan C2 (khong dung PnL/ket qua): lech close perp/spot theo symbol."""
import logging
import os
import sys

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("cod")
W = os.path.expanduser("~/claude_master/1016/carry")
P = pd.read_parquet(W + "/panel.parquet").dropna(subset=["close_p", "close_s"])
P["dev"] = (P.close_p / P.close_s - 1).abs()
fr = P.groupby("sym").dev.apply(lambda x: (x > 0.02).mean())
med = P.groupby("sym").dev.median()
log.info("so sym %d; ty le ngay lech>2%%: >50%%: %d, 20-50%%: %d, 5-20%%: %d, <5%%: %d", len(fr), (fr > .5).sum(), ((fr > .2) & (fr <= .5)).sum(), ((fr > .05) & (fr <= .2)).sum(), (fr <= .05).sum())
bad = fr[fr > 0.2].index
log.info("sym >20%%: %s", {s: (round(fr[s], 2), round(med[s], 3)) for s in bad})
ok = P[~P.sym.isin(bad)]
log.info("C2 sau khi loai sym >20%%: %.4f (n ngay %d)", (ok.dev <= 0.02).mean(), len(ok))
# lech theo ngay o sym tot: phan bo
log.info("ngay lech>2%% o sym tot theo nam: %s", ok[ok.dev > 0.02].day.dt.year.value_counts().sort_index().to_dict())
log.info("vi du lech lon o sym tot: %s", ok.nlargest(8, "dev")[["sym", "day", "close_p", "close_s", "dev"]].to_string(index=False))
