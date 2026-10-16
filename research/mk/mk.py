"""MK ho #2 (PREREG_MK.md): sleeve maker BTC S1 (21-23 UTC) va S7 (cuoi tuan) voi khop maker bao thu tren 1m."""
import json
import logging
import os
import sys

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("mk")
W = os.path.expanduser("~/claude_master/1016/screen")
OUT = os.path.expanduser("~/claude_master/mk"); os.makedirs(OUT, exist_ok=True)
MK, TK, SL = 0.0002, 0.0005, 0.0002
WAIT = 10


def sessions(M, kind):
    days = pd.date_range(M.index.min().normalize() + pd.Timedelta(days=1), M.index.max().normalize() - pd.Timedelta(days=4), freq="D")
    out = []
    for d in days:
        if kind == "S1":
            out.append((d + pd.Timedelta(hours=21), d + pd.Timedelta(hours=23)))
        elif kind == "S7" and d.weekday() == 4:
            t0 = pd.Timestamp(d.date()).tz_localize("America/New_York") + pd.Timedelta(hours=16)
            t1 = pd.Timestamp((d + pd.Timedelta(days=3)).date()).tz_localize("America/New_York") + pd.Timedelta(hours=10)
            out.append((t0.tz_convert("UTC").tz_localize(None), t1.tz_convert("UTC").tz_localize(None)))
    return out


def sim(M, ses, fund_daily):
    rows = []
    for t0, t1 in ses:
        try:
            p0 = M.close.at[t0 - pd.Timedelta(minutes=1)]; p1 = M.close.at[t1 - pd.Timedelta(minutes=1)]
        except KeyError:
            continue
        w0 = M.loc[t0:t0 + pd.Timedelta(minutes=WAIT - 1)]; w1 = M.loc[t1:t1 + pd.Timedelta(minutes=WAIT - 1)]
        if len(w0) < WAIT or len(w1) < WAIT:
            continue
        nf = sum(1 for h in (0, 8, 16) for dd in pd.date_range(t0.normalize(), t1.normalize())
                 if t0 < dd + pd.Timedelta(hours=h) <= t1)
        f = fund_daily.reindex(pd.date_range(t0.normalize(), t1.normalize())).fillna(0).mean() / 3 * nf
        taker = p1 / p0 - 1 - 2 * (TK + SL) - f
        mk_always = p1 / p0 - 1 - 2 * MK - f
        fill_in = bool((w0.low < p0).any())
        if not fill_in:
            rows.append((t0, t1, taker, mk_always, 0.0, False, False, p1 / p0 - 1)); continue
        fill_out = bool((w1.high > p1).any())
        if fill_out:
            r = p1 / p0 - 1 - 2 * MK - f
        else:
            pe = w1.close.iloc[-1]
            r = pe / p0 - 1 - MK - TK - SL - f
        rows.append((t0, t1, taker, mk_always, r, True, not fill_out, p1 / p0 - 1))
    return pd.DataFrame(rows, columns=["t0", "t1", "taker", "mk_always", "mk_cons", "filled", "mkt_exit", "raw"])


def daily(df, col):
    s = df.groupby(df.t1.dt.normalize())[col].sum()
    idx = pd.date_range(df.t1.min().normalize(), df.t1.max().normalize())
    return s.reindex(idx).fillna(0.0)


def stats(r):
    eq = (1 + r).cumprod()
    yr = {int(y): round(float(g.sum()), 4) for y, g in r.groupby(r.index.year)}
    return {"sh": float(r.mean() / r.std() * np.sqrt(365)), "ann": float(r.mean() * 365), "maxdd": float((eq / eq.cummax() - 1).min()), "year_sum": yr,
            "year_sh": {int(y): round(float(g.mean() / g.std() * np.sqrt(365)), 2) for y, g in r.groupby(r.index.year) if g.std() > 0}}


def main():
    M = pd.read_parquet(W + "/m1_BTCUSDT.parquet")
    D = pd.read_parquet(W + "/d1.parquet", columns=["sym", "day", "fund_day"])
    fd = D[D.sym == "BTCUSDT"].set_index("day").fund_day
    res = {}
    for kind in ("S1", "S7"):
        df = sim(M, sessions(M, kind), fd)
        o = {k: stats(daily(df, k)) for k in ("taker", "mk_always", "mk_cons")}
        o["fill_rate"] = float(df.filled.mean()); o["mkt_exit_rate"] = float(df[df.filled].mkt_exit.mean())
        o["missed_raw_mean"] = float(df[~df.filled].raw.mean()); o["filled_raw_mean"] = float(df[df.filled].raw.mean()); o["n"] = int(len(df))
        c = o["mk_cons"]
        o["gates"] = {"G1": c["sh"] >= 0.5, "G2": sum(v > 0 for v in c["year_sum"].values()) >= 5 and c["year_sum"].get(2024, -1) > 0 and c["year_sum"].get(2025, -1) > 0,
                      "G3": o["fill_rate"] >= 0.6, "G4": c["maxdd"] >= -0.25}
        o["verdict"] = "GO" if all(o["gates"].values()) else "NO-GO"
        res[kind + "M"] = o
        for k in ("taker", "mk_always", "mk_cons"):
            log.info("%s %-9s Sh %+.2f ann %+.1f%% dd %.2f yr_sum %s yr_sh %s", kind, k, o[k]["sh"], 100 * o[k]["ann"], o[k]["maxdd"], o[k]["year_sum"], o[k]["year_sh"])
        log.info("%s n %d fill %.3f mkt_exit %.3f | raw khop %+.4f%% vs bo lo %+.4f%% | gates %s -> %s", kind, o["n"], o["fill_rate"], o["mkt_exit_rate"],
                 100 * o["filled_raw_mean"], 100 * o["missed_raw_mean"], o["gates"], o["verdict"])
        df.to_csv(OUT + f"/mk_{kind}.csv", index=False)
    json.dump(res, open(OUT + "/mk_result.json", "w"), indent=1, default=str)


if __name__ == "__main__":
    main()
