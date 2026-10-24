"""LIQX_S1 step 1: per month -> coin buckets (S1/coin/YYYY-MM.parquet), convention table (S1/conv/), universe (S1/uni/).
Usage: python3 s1_build.py YYYY-MM [YYYY-MM ...]  (default: all 2022-01..2025-12)."""
import json
import sys
import time
import numpy as np
import pandas as pd
from common import (S1, WK, DAY, B5, M1, MAJ, ms, months, nxt, universe, read_kline, read_metrics,
                    detect_conv, apply_conv, build_buckets, maxrss_mb)
import os

for d in ("coin", "conv", "uni", "log"):
    os.makedirs(S1 + "/" + d, exist_ok=True)


def one(y, m, dq):
    t0 = time.time()
    M, Mn = ms(y, m), ms(*nxt(y, m))
    uni, score = universe(dq, M)
    assert len(uni) == 100
    kl = read_kline(set(uni), M - DAY - 10 * M1, Mn + DAY + 10 * M1)
    met = read_metrics(set(uni), M - DAY, Mn + DAY)
    ddays = list(range(M - DAY, Mn + DAY, DAY))
    conv = detect_conv(met, kl, ddays)
    meff, cnt = apply_conv(met, conv)
    meff = meff[(meff.ts >= M - B5) & (meff.ts <= Mn)]
    bdays = list(range(M, Mn, DAY))
    g = build_buckets(kl, meff, uni, bdays)
    rk = {s: i + 1 for i, s in enumerate(uni)}
    g["rank"] = g.sym.map(rk).astype("int16")
    g["alt"] = ~g.sym.isin(MAJ)
    g["sym"] = g.sym.astype("category")
    tag = "%04d-%02d" % (y, m)
    g.to_parquet(S1 + "/coin/%s.parquet" % tag, index=False, compression="zstd")
    conv.to_parquet(S1 + "/conv/%s.parquet" % tag, index=False)
    json.dump({"uni": uni, "score": {s: score[s] for s in uni}}, open(S1 + "/uni/%s.json" % tag, "w"))
    cin = conv[(conv.day >= M) & (conv.day < Mn)]
    vs = g.groupby(["sym", "day"], observed=True).valid.sum()
    miss = vs[vs < 288]
    log = dict(month=tag, n_uni=len(uni), kl_rows=len(kl), met_rows=len(met),
               conv_NEW=int((cin.conv == "NEW").sum()), conv_OLD=int((cin.conv == "OLD").sum()),
               conv_AMBIG=int((cin.conv == "AMBIG").sum()),
               via_price=int((cin.via == "price").sum()), **cnt,
               buckets=len(g), valid=int(g.valid.sum()), symday=int(len(vs)), symday_lt288=int(len(miss)),
               symday_0=int((vs == 0).sum()),
               miss_days={str(pd.Timestamp(d, unit="ms").date()): int(n) for d, n in
                          miss.reset_index().groupby("day").size().items() if n >= 5},
               maxrss_mb=round(maxrss_mb(), 1), sec=round(time.time() - t0, 1))
    json.dump(log, open(S1 + "/log/%s.json" % tag, "w"))
    print(json.dumps(log), flush=True)


def main():
    dq = pd.read_parquet(WK + "/daily_qv.parquet")
    assert dq.day.dtype == np.int64
    if len(sys.argv) > 1:
        ml = [tuple(int(x) for x in a.split("-")) for a in sys.argv[1:]]
    else:
        ml = months()
    for y, m in ml:
        one(y, m, dq)


if __name__ == "__main__":
    main()
