"""REX S1 chan doan HAU KIEM (chi DEV 2022-2024, khong phai phep thu): vi sao IC manh ma top-10 khong ra tien."""
import logging
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/claude_master/vz_e1_wt/research/rex"))
import rex_s1 as S1  # noqa: E402

log = logging.getLogger("rex1d")
P = S1.load()
P = P[(P.day >= S1.DEV0) & (P.day <= S1.DEV1)]
RET, FD = S1.wide_px()
for name in ("C1", "C3", "C7"):
    h = int(name[1:])
    pr = pd.read_parquet(S1.OUT + f"/pred_s1_{name}.parquet")
    pr = pr[(pr.day >= S1.DEV0) & (pr.day <= S1.DEV1)]
    j = pr.merge(P[["day", "sym", f"y{h}", "r_vol30", "lqv30"]], on=["day", "sym"])
    j["dec"] = j.groupby("day").score.transform(lambda s: pd.qcut(s.rank(method="first"), 10, labels=False))
    g = j.groupby("dec").agg(mean=(f"y{h}", "mean"), med=(f"y{h}", "median"), win=(f"y{h}", lambda x: float((x > 0).mean())),
                             rvol=("r_vol30", "mean"), lqv=("lqv30", "mean"))
    log.info("%s decile (DEV): mean y%d / median / win%% / rank vol30 / log qv\n%s", name, h, g.round(4).to_string())
    for k in (10, 20):
        pf0 = S1.portfolio(pr, P, h, RET, FD, k=k, ca=0.0)
        pf1 = S1.portfolio(pr, P, h, RET, FD, k=k, ca=0.001)
        log.info("%s top%d gross exc Sh %+.2f %s | net exc %+.2f | gross excb %+.2f | turn %.2f", name, k, S1.sstats(pf0.exc, S1.DEV0, S1.DEV1)["sh"],
                 S1.sstats(pf0.exc, S1.DEV0, S1.DEV1).get("by_year_sh"), S1.sstats(pf1.exc, S1.DEV0, S1.DEV1)["sh"],
                 S1.sstats(pf0.excb, S1.DEV0, S1.DEV1)["sh"], pf1.turn.mean())
    # dao: bottom decile (de xem chan short / bo loai)
    neg = pr.assign(score=-pr.score)
    pfb = S1.portfolio(neg, P, h, RET, FD, k=10, ca=0.0)
    log.info("%s BOTTOM10 gross exc Sh %+.2f ann %+.1f%% %s", name, S1.sstats(pfb.exc, S1.DEV0, S1.DEV1)["sh"], 100 * S1.sstats(pfb.exc, S1.DEV0, S1.DEV1).get("ann", 0),
             S1.sstats(pfb.exc, S1.DEV0, S1.DEV1).get("by_year_sh"))
uni = P.groupby("day").y1.agg(["mean", "median"])
log.info("universe y1 DEV: mean %.5f median %.5f (chenh/ngay %.5f) | BTC y1 mean %.5f", uni["mean"].mean(), uni["median"].mean(),
         (uni["mean"] - uni["median"]).mean(), P[P.sym == "BTCUSDT"].y1.mean())
