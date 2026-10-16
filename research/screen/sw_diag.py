"""SCREEN_WIDE chan doan (MO TA, khong them phep thu): X9/X1/X2 theo nam, tuyet doi vs vuot ro, tre 1 ngay, phi maker;
TS S1/S7 phi maker. Dung lai ham trong sw_run.py."""
import logging
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.expanduser("~/claude_master/vz_e1_wt/research/screen"))
import sw_run as S  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("swd")
D = pd.read_parquet(S.W + "/d1.parquet")
C = D.pivot(index="day", columns="sym", values="close").sort_index()
Q = D.pivot(index="day", columns="sym", values="qv").reindex(C.index)
FD = D.pivot(index="day", columns="sym", values="fund_day").reindex(C.index).fillna(0.0)
first = C.apply(lambda s: s.first_valid_index())
qv30 = Q.rolling(30, min_periods=20).median()
feats = {"X9": C / C.rolling(365, min_periods=365).max(), "X1": C / C.shift(21) - 1, "X2": C / C.shift(7) - 1}


def run(k, lag=0, fee=S.FEE):
    F = feats[k]; rows = []; prev = set()
    for t in [d for d in C.index if d.weekday() == 0 and pd.Timestamp("2021-03-01") <= d <= pd.Timestamp("2026-09-21")]:
        tm1 = t - pd.Timedelta(days=1); ent = tm1 + pd.Timedelta(days=lag); t6 = t + pd.Timedelta(days=6 + lag)
        if t6 not in C.index:
            continue
        age_ok = first[first <= t - pd.Timedelta(days=60)].index
        u = qv30.loc[tm1]; u = u[u >= 20e6].index.intersection(age_ok)
        hold = (C.loc[t6] / C.loc[ent] - 1)[u].dropna()
        if len(hold) < 30:
            continue
        fs = FD.loc[ent + pd.Timedelta(days=1):t6, hold.index].sum()
        f = F.loc[tm1, hold.index].dropna()
        n = max(3, len(f) // 10); top = set(f.nlargest(n).index)
        to = 1 - len(top & prev) / n; prev = top
        absr = (hold[list(top)] - fs[list(top)]).mean() - to * 2 * fee
        rows.append((t, absr, absr - hold.mean(), hold.mean(), len(hold), to))
    return pd.DataFrame(rows, columns=["t", "abs", "exc", "bench", "nu", "to"]).set_index("t")


for k in feats:
    for lag, fee, tag in [(0, S.FEE, "goc"), (1, S.FEE, "tre1ngay"), (0, 0.0002, "maker")]:
        r = run(k, lag, fee)
        y = r.groupby(r.index.year).agg(abs_=("abs", "sum"), exc=("exc", "sum"), bench=("bench", "sum"))
        sE = S.split(r.exc, 52)
        log.info("%s %-8s exc E Sh %+.2f C Sh %+.2f | abs E Sh %+.2f C Sh %+.2f | TO tb %.2f | theo nam (tong tuan) abs/exc/bench: %s", k, tag,
                 sE["E"]["sharpe"], sE["C"]["sharpe"], S.split(r["abs"], 52)["E"]["sharpe"], S.split(r["abs"], 52)["C"]["sharpe"], r.to.mean(),
                 {int(i): (round(a, 2), round(b, 2), round(c, 2)) for i, (a, b, c) in y.iterrows()})
# TS phi maker
S.FEE = 0.0002
for sym in ("BTCUSDT",):
    o = S.ts_family(sym)
    for k in ("S1", "S2", "S3", "S6", "S7"):
        log.info("maker %s %s E Sh %+.2f ann %+.1f%% | C Sh %+.2f ann %+.1f%%", sym[:3], k, o[k]["E"]["sharpe"], 100 * o[k]["E"]["ann"], o[k]["C"]["sharpe"], 100 * o[k]["C"]["ann"])
