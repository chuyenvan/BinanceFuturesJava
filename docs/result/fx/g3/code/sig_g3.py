#!/usr/bin/env python3
"""G3 signals: rolling z of x over W weeks (prereg sec 4 + ERRATA1 H4/H5), weekly book of eligible ccy-weeks.
- anchor(T) = T + 7 calendar days; entry = first business day >= anchor with a valid FRED price for that ccy (H5 + G1 sec 3).
- report T EXCLUDED if listed in cot_release_exceptions with actual_pub > T + 6 days (H5).
- window for z at T: reports r of same ccy with T - 7W < r <= T, x not NaN, published BEFORE anchor (pub(r) <= anchor - 1 day);
  normal reports assumed published <= r + 6 days; if > W reports (date jitter) keep latest W.
  z defined only if n >= 95 % * W (H4); no interpolation; sd ddof=1; sd == 0 -> undefined.
- eligible ccy-week: z defined, not excluded, OECD rate of ccy AND USD for month(anchor)-1 present, entry price found within 7 days.
- N_dt = number of eligible ccys of that group/W at that report date; signal = +1 if z >= 1.5, -1 if z <= -1.5, else 0.
No returns are computed here.
"""
import argparse
import logging
import os

import numpy as np
import pandas as pd

import load_g3

LOG = logging.getLogger("g3.sig")
THRESH = 1.5
COVER = 0.95
WS = (52, 156)
PERIODS = {
    "NonComm_LEG": dict(train=("1993-01-01", "2005-12-31"), wfo=("2006-01-01", "2019-12-31")),
    "LevFunds_TFF": dict(train=("2006-06-01", "2012-12-31"), wfo=("2013-01-01", "2019-12-31")),
    "AssetMgr_TFF": dict(train=("2006-06-01", "2012-12-31"), wfo=("2013-01-01", "2019-12-31")),
}
D7 = pd.Timedelta(days=7)
D6 = pd.Timedelta(days=6)


def pub_dates(report_dates, exceptions):
    """Actual publication date if listed in exceptions, else nominal T + 3 (normal Friday; assumed <= T + 6)."""
    ex = dict(zip(exceptions["report_date"], exceptions["pub"])) if len(exceptions) else {}
    rd = pd.DatetimeIndex(report_dates)
    return pd.DatetimeIndex([ex.get(t, t + pd.Timedelta(days=3)) for t in rd])


def excluded_set(exceptions):
    if not len(exceptions):
        return set()
    m = exceptions["pub"] > exceptions["report_date"] + D6
    return set(exceptions.loc[m, "report_date"])


def zscores(xdf, W, exceptions):
    """xdf: columns date, ccy, x. Returns per (ccy, date): x, z, n_win, anchor, excluded, win_max_pub, win_min_date."""
    excl = excluded_set(exceptions)
    out = []
    need = COVER * W - 1e-9
    for ccy, d in xdf.sort_values(["ccy", "date"]).groupby("ccy", sort=True):
        dates = pd.DatetimeIndex(d["date"].values)
        x = d["x"].values.astype(float)
        pub = pub_dates(dates, exceptions)
        dn = dates.values
        for k in range(len(d)):
            t = dates[k]
            anchor = t + D7
            ex = t in excl
            z, n, mp, md = np.nan, 0, pd.NaT, pd.NaT
            if not ex and np.isfinite(x[k]):
                lo = np.searchsorted(dn, (t - W * D7).to_datetime64(), side="right")
                idx = np.arange(lo, k + 1)
                ok = np.isfinite(x[idx]) & (pub.values[idx] <= (anchor - pd.Timedelta(days=1)).to_datetime64())
                idx = idx[ok]
                if len(idx) > W:
                    idx = idx[-W:]
                n = len(idx)
                if n and idx[-1] == k and n >= need:
                    win = x[idx]
                    sd = win.std(ddof=1)
                    if sd > 0:
                        z = (x[k] - win.mean()) / sd
                    mp = pd.Timestamp(pub.values[idx].max())
                    md = pd.Timestamp(dn[idx[0]])
            out.append((t, ccy, x[k], z, n, anchor, ex, mp, md))
    return pd.DataFrame(out, columns=["date", "ccy", "x", "z", "n_win", "anchor", "excluded", "win_max_pub", "win_min_date"])


def first_valid_on_or_after(px, ccy, t, max_days=None):
    s = px[ccy]
    v = s.index[s.notna().values]
    i = v.searchsorted(t, side="left")
    if i >= len(v):
        return pd.NaT
    e = v[i]
    if max_days is not None and e > t + pd.Timedelta(days=max_days):
        return pd.NaT
    return e


def rate_ok(rates, ccy, t):
    m1 = (pd.Timestamp(t).to_period("M") - 1).to_timestamp()
    if m1 not in rates.index:
        return False
    return bool(np.isfinite(rates.at[m1, ccy]) and np.isfinite(rates.at[m1, "USD"]))


def signal_from_z(z, eligible):
    z = np.asarray(z, dtype=float)
    el = np.asarray(eligible, dtype=bool)
    s = np.zeros(len(z), dtype=int)
    s[el & (z >= THRESH)] = 1
    s[el & (z <= -THRESH)] = -1
    return s


def build_book(data, group, W):
    zs = zscores(data["cot"][group][["date", "ccy", "x"]], W, data["exceptions"])
    px, rates = data["px"], data["rates"]
    entry, rok = [], []
    for r in zs.itertuples():
        ok_r = rate_ok(rates, r.ccy, r.anchor)
        rok.append(ok_r)
        entry.append(first_valid_on_or_after(px, r.ccy, r.anchor, max_days=7) if (np.isfinite(r.z) and ok_r) else pd.NaT)
    zs["rate_ok"] = rok
    zs["entry_date"] = pd.DatetimeIndex(entry)
    zs["eligible"] = zs["z"].notna() & (~zs["excluded"]) & zs["rate_ok"] & zs["entry_date"].notna()
    zs["N_dt"] = zs.groupby("date")["eligible"].transform("sum").astype(int)
    zs["signal"] = signal_from_z(zs["z"].values, zs["eligible"].values)
    zs["group"] = group
    zs["W"] = W
    return zs.sort_values(["date", "ccy"]).reset_index(drop=True)


def count_events(data):
    rows = []
    for g in load_g3.GROUPS:
        for W in WS:
            b = build_book(data, g, W)
            for per, (a, e) in PERIODS[g].items():
                m = b["eligible"] & (b["entry_date"] >= a) & (b["entry_date"] <= e)
                rows.append(dict(group=g, W=W, period=per, eligible_ccy_weeks=int(m.sum()),
                                 n_absz_ge_1_5=int((m & (b["signal"] != 0)).sum()),
                                 per_ccy=";".join("%s:%d" % (c, n) for c, n in
                                                  b[m & (b["signal"] != 0)].groupby("ccy").size().items())))
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", action="store_true", help="count |z|>=1.5 events per group x W x period (counts only)")
    ap.add_argument("--cutoff", default=load_g3.DEFAULT_CUTOFF)
    ap.add_argument("--holdout", default=None)
    ap.add_argument("--out", default=os.path.expanduser("~/claude_master/w3/fx/g3/out/event_counts_g3.csv"))
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    data = load_g3.load(a.cutoff, a.holdout)
    if a.count:
        c = count_events(data)
        c.to_csv(a.out, index=False)
        for r in c.itertuples():
            LOG.info("%s W%d %s eligible=%d |z|>=1.5=%d (%s)", r.group, r.W, r.period, r.eligible_ccy_weeks, r.n_absz_ge_1_5,
                     r.per_ccy)


if __name__ == "__main__":
    main()
