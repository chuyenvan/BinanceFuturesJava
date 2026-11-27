#!/usr/bin/env python3
"""G4 loader (PREREG_FX_G4 + ERRATA4 N1-N5). M1 BID bars (ts = bar OPEN time, UTC) per pair from parquet; HARD cutoff via
parquet filter (rows > cutoff never read); pair-years of N3 flagged bad; gaps > 5 / > 60 min flagged; NY clock fields;
trading sessions (17:00 NY boundary) and OECD rates for swap. Time unit: int64 minutes since 1970-01-01 UTC."""
import argparse
import logging
import os

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

LOG = logging.getLogger("g4.load")
DATA_DIR = os.path.expanduser("~/claude_master/w3/fx/data")
DEFAULT_CUTOFF = "2019-12-31"
HOLDOUT_START = pd.Timestamp("2020-01-01")
HOLDOUT_TOKEN = "I_HAVE_OWNER_OK"
PAIRS = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD"]
# pip, round-trip pips, minimum round-trip fraction (ERRATA2 J1: max(3 pip, 3 bp); EURUSD 0.8 pip only); base/quote OECD rate ids
PAIR = {"EURUSD": dict(pip=1e-4, rt_pips=0.8, rt_min=0.0, base="EZ", quote="US"),
        "GBPUSD": dict(pip=1e-4, rt_pips=3.0, rt_min=3e-4, base="GB", quote="US"),
        "USDJPY": dict(pip=1e-2, rt_pips=3.0, rt_min=3e-4, base="US", quote="JP"),
        "AUDUSD": dict(pip=1e-4, rt_pips=3.0, rt_min=3e-4, base="AU", quote="US")}
# ERRATA4 N3 (DATA_REPORT_3.md FAIL list, frozen): pair-years excluded entirely
EXCLUDED = {(p, y) for p in PAIRS for y in (2007, 2008)} | {("GBPUSD", 2009), ("USDJPY", 2009), ("AUDUSD", 2006)}
MIN_SESSION_BARS = 60


def check_cutoff(cutoff, holdout=None):
    c = pd.Timestamp(cutoff)
    if c >= HOLDOUT_START and holdout != HOLDOUT_TOKEN:
        raise PermissionError("cutoff %s touches HOLDOUT; requires --holdout %s (owner only)" % (c.date(), HOLDOUT_TOKEN))
    return c


def rt_cost(pair, price):
    """Round-trip cost as a fraction of notional at quote price `price`."""
    s = PAIR[pair]
    return np.maximum(s["rt_pips"] * s["pip"] / np.asarray(price, float), s["rt_min"])


def ny_fields(tmin):
    ts = pd.to_datetime(np.asarray(tmin, dtype="int64") * 60, unit="s", utc=True).tz_convert("America/New_York")
    mod = (ts.hour * 60 + ts.minute).values.astype(np.int32)
    sess = (ts + pd.Timedelta(hours=7)).normalize().tz_localize(None).values.astype("datetime64[D]")  # 17:00 NY boundary
    return mod, sess


def build_pair(pair, t, o, h, l, c, year_utc=None):
    """Derived per-bar fields from raw arrays (also used for synthetic data in tests)."""
    t = np.asarray(t, dtype=np.int64)
    n = len(t)
    dt = np.empty(n, dtype=np.int64)
    dt[0] = 10 ** 9
    dt[1:] = np.diff(t)
    if (dt[1:] <= 0).any():
        raise ValueError("timestamps not strictly increasing")
    mod, sess = ny_fields(t)
    if year_utc is None:
        year_utc = pd.to_datetime(t * 60, unit="s").year.values
    bad = np.zeros(n, bool)
    for (p, y) in EXCLUDED:
        if p == pair:
            bad |= year_utc == y
    g60_time = np.where(dt > 60, t, np.iinfo(np.int64).min // 2)
    last_g60 = np.maximum.accumulate(g60_time)
    after60 = (t - last_g60) < 30  # within 30 min after a gap > 60 min (incl. week open)
    roll = (mod >= 16 * 60 + 55) & (mod < 17 * 60 + 15)
    return dict(pair=pair, t=t, o=np.asarray(o, float), h=np.asarray(h, float), l=np.asarray(l, float),
                c=np.asarray(c, float), dt=dt, gap5=dt > 5, gap60=dt > 60, after60=after60, roll=roll, mod=mod, sess=sess,
                bad=bad, year=year_utc)


def rollover_table(rates, pair, start="2004-12-01", end="2020-01-31"):
    """17:00 NY rollover instants (Mon-Fri; Friday weight 3) with daily swap diff (base - quote)/100/360, rate of month m-1."""
    d = pd.bdate_range(start, end)
    inst = (pd.DatetimeIndex(d) + pd.Timedelta(hours=17)).tz_localize("America/New_York").tz_convert("UTC")
    tmin = (inst.tz_localize(None).values.astype("datetime64[s]").astype(np.int64) // 60)
    w = np.where(d.dayofweek == 4, 3.0, 1.0)
    m1 = (d.to_period("M") - 1).to_timestamp()
    s = PAIR[pair]
    rb = rates.reindex(m1)[s["base"]].values
    rq = rates.reindex(m1)[s["quote"]].values
    diff = (rb - rq) / 100.0 / 360.0
    miss = int(np.isnan(diff).sum())
    diff = np.nan_to_num(diff) * w
    return dict(t=tmin, cdiff=np.concatenate([[0.0], np.cumsum(diff)]), cw=np.concatenate([[0.0], np.cumsum(w)]),
                missing=miss)


def read_rates(data_dir, cutoff):
    out = {}
    for rid in ("US", "EZ", "GB", "JP", "AU"):
        df = pd.read_csv(os.path.join(data_dir, "derived", "FRED_IR3TIB01%sM156N.csv" % rid))
        df["date"] = pd.to_datetime(df["date"])
        df = df[df["date"] <= cutoff]
        out[rid] = pd.Series(pd.to_numeric(df["v"], errors="coerce").values, index=df["date"])
    return pd.DataFrame(out)


def load(pairs=PAIRS, cutoff=DEFAULT_CUTOFF, holdout=None, data_dir=DATA_DIR, real=True):
    c = check_cutoff(cutoff, holdout)
    lim = pd.Timestamp(c.date()) + pd.Timedelta(days=1)  # rows with ts < cutoff_day + 1 day
    rates = read_rates(data_dir, c)
    data = dict(pairs={}, rates=rates, cutoff=c, real=real)
    for p in pairs:
        f = os.path.join(data_dir, "derived", "m1", "%s_M1_2005_2019.parquet" % p)
        tb = pq.read_table(f, columns=["ts_utc", "open", "high", "low", "close"],
                           filters=[("ts_utc", "<", pd.Timestamp(lim, tz="UTC"))])
        df = tb.to_pandas()
        t = df["ts_utc"].values.astype("datetime64[m]").astype(np.int64)
        if len(t) and t.max() >= lim.value // 60 // 10 ** 9:
            raise AssertionError("cutoff leak")
        d = build_pair(p, t, df["open"].values, df["high"].values, df["low"].values, df["close"].values)
        d["roll_tab"] = rollover_table(rates, p)
        data["pairs"][p] = d
        LOG.info("%s: %d bars %s..%s; bad(N3) %d bars; gaps>5 %d; gaps>60 %d", p, len(t),
                 pd.to_datetime(t[0] * 60, unit="s"), pd.to_datetime(t[-1] * 60, unit="s"), int(d["bad"].sum()),
                 int(d["gap5"].sum()), int(d["gap60"].sum()))
    return data


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cutoff", default=DEFAULT_CUTOFF)
    ap.add_argument("--holdout", default=None)
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    load(cutoff=a.cutoff, holdout=a.holdout)


if __name__ == "__main__":
    main()
