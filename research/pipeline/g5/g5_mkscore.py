"""G5 — doi pool_<tag>.parquet (ts,sym,p) thanh ledger/pred_g5_<tag>.parquet (ts,sym,score).
score = -p  (quy uoc c4_build_map.py: score THAP = TOT; p CAO = TOT).
Chi giu dong nam trong 16 fold DEV. Xem docs/PREREG_G5.md muc 5."""
import logging, os, sys
import pandas as pd
logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
LOG = logging.getLogger("g5mk")
POOL = "/home/ubuntu/g5/pool"
LED = "/home/ubuntu/ledger"
for tag in sys.argv[1:]:
    p = os.path.join(POOL, "pool_%s.parquet" % tag)
    D = pd.read_parquet(p)
    S = pd.DataFrame({"ts": D.ts.astype("int64"), "sym": D.sym.astype("int64"),
                      "score": (-D.p.astype("float64"))})
    S = S.drop_duplicates(["ts", "sym"])
    o = os.path.join(LED, "pred_g5_%s.parquet" % tag)
    S.to_parquet(o, index=False)
    LOG.info("%-14s rows=%d ticks=%d -> %s", tag, len(S), S.ts.nunique(), o)
