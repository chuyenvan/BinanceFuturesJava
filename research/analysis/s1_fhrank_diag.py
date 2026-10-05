#!/usr/bin/env python3
"""S1_FIRSTHIT_RANK — chan doan tang model (pre-reg §8): xs-rank-corr + overlap top-16 giua cac cap arm
(seed vs seed, FHL vs FHP, CTRL vs CTRL). Ghi /home/ubuntu/claude_master/1003/fhr/model_pairs.json."""
import json, logging, sys
import numpy as np
import pandas as pd
sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
import s1_fhrank_sim as S  # noqa: E402
log = logging.getLogger("fhr_diag")
PAIRS = [("FHP42", "FHP7"), ("FHL42", "FHL7"), ("FHL42", "FHP42"), ("FHL7", "FHP7"), ("K42", "S7"),
         ("FHP42", "K42"), ("FHL42", "K42")]


def main():
    arms = sorted({a for p in PAIRS for a in p})
    M = None
    for a in arms:
        P = S.load_pred(a).rename(columns={"score": a})
        M = P if M is None else M.merge(P, on=["ts", "sym"], how="inner")
    g = M.groupby("ts")
    tick = M.ts.to_numpy()
    R = {a: g[a].rank(method="average").to_numpy() for a in arms}
    T = {a: g[a].rank(method="first").to_numpy() for a in arms}
    n = g.ts.size()
    out = {}
    for x, y in PAIRS:
        xs = S.tick_corr(tick, R[x], R[y])
        ov = pd.Series((T[x] <= 16) & (T[y] <= 16)).groupby(tick).sum() / 16.0
        ov = ov[n.reindex(ov.index).to_numpy() > 16]
        out[x + "~" + y] = dict(xs=S.agg(xs), top16_overlap=S.agg(ov))
        log.info("PAIR %-12s xs %.4f top16 %.3f", x + "~" + y, xs.mean(), ov.mean())
    json.dump(out, open(S.D + "/model_pairs.json", "w"), indent=1)


if __name__ == "__main__":
    main()
