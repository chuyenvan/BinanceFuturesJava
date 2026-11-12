"""R1 PHA0: dem leg theo level + PnL trong printDone B0 x14 (DEV + HO). Chi doc."""
import glob
import logging
import sys

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
log = logging.getLogger("r1")
rows = []
for pat in sys.argv[1:]:
    for d in sorted(glob.glob("/home/ubuntu/kaggle_sim/out/" + pat)):
        f = d + "/storage/printDone.csv"
        try:
            x = pd.read_csv(f, index_col=False, usecols=["sym", "level", "pnl", "start", "symbolPred"])
        except Exception as e:  # noqa: BLE001
            log.info("SKIP %s %s", d, e)
            continue
        x["pnl"] = pd.to_numeric(x["pnl"], errors="coerce")
        tag = d.rsplit("/", 1)[-1]
        g = x.groupby("level")["pnl"].agg(["count", "sum", "mean"])
        tot_n, tot_p = len(x), x["pnl"].sum()
        for lv, r in g.iterrows():
            rows.append(dict(tag=tag, level=lv, n=int(r["count"]), n_share=r["count"] / tot_n,
                             pnl=r["sum"], pnl_share=r["sum"] / tot_p if tot_p else float("nan"), mean=r["mean"]))
        log.info("%s n=%d pnl=%.0f start=%s..%s", tag, tot_n, tot_p, x["start"].min(), x["start"].max())
df = pd.DataFrame(rows)
pd.set_option("display.width", 200)
log.info("\n%s", df.to_string(float_format=lambda v: "%.3f" % v))
log.info("\nMEAN theo level:\n%s", df.assign(grp=df.tag.str.contains("-ho-")).groupby(["grp", "level"])[["n", "n_share", "pnl", "pnl_share", "mean"]].mean().to_string(float_format=lambda v: "%.3f" % v))
