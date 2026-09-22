import logging
import sys
sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
import trend_rank_ic as T
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("check")

df = T.load_closes()
for sym, name in ((1, "BTC"), (2, "ETH")):
    d = df[df["sym"] == sym]
    log.info("%s n=%d ctime %s -> %s", name, len(d),
              pd.Timestamp(d.ctime.min(), unit="ms"), pd.Timestamp(d.ctime.max(), unit="ms"))
