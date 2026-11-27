#!/usr/bin/env python3
"""G4 events (prereg sec 3 + ERRATA4 N4). Per pair:
- r1 = log(c_i / c_{i-1}) only when bars are 1 minute apart. Session = NY date of (t + 7 h) (17:00 NY boundary); sessions with
  < 60 bars are not trading days. sigma1(session j) = pooled std of r1 over the 20 PREVIOUS trading sessions (ddof=1); undefined
  if any of them, or session j, lies in an excluded pair-year (N3) -> no events in the first 20 sessions after an excluded year.
- r_N(i) = log(c_i / c_j), j = last bar with t_j <= t_i - N. Window rejected if any bar in (j, i] follows a gap > 5 min, or
  t_i is < 30 min after a gap > 60 min (N4). sigma_N = sigma1 * sqrt(N); z = r_N / sigma_N.
- L event: z <= -T; S event: z >= +T. Entry bar = i + 1 (close of NEXT minute) must exist, be <= 5 min after bar i, not in the
  rollover window 16:55-17:15 NY, not in an excluded pair-year. sigma60 (for exits) = sigma1 * sqrt(60) of the event session.
No returns here."""
import argparse
import logging
import os

import numpy as np
import pandas as pd

import load_g4

LOG = logging.getLogger("g4.sig")
NT = [(15, 4.0), (60, 3.0), (60, 4.0)]
SIDES = {"L": 1, "S": -1}
TSS = [240, 1440]
SIG_DAYS = 20
TRAIN = ("2005-01-01", "2012-12-31")
WFO = ("2013-01-01", "2019-12-31")


def tmin(s):
    return int(pd.Timestamp(s).value // 60 // 10 ** 9)


def session_sigma(d):
    """Per-bar sigma1 (NaN where undefined), computed from PREVIOUS sessions only."""
    c, t, sess, bad = d["c"], d["t"], d["sess"], d["bad"]
    r1 = np.full(len(c), np.nan)
    ok = d["dt"] == 1
    r1[ok] = np.log(c[ok] / c[np.flatnonzero(ok) - 1])
    u, inv, cnt = np.unique(sess, return_inverse=True, return_counts=True)
    v = np.isfinite(r1)
    s1 = np.bincount(inv, weights=np.where(v, r1, 0.0), minlength=len(u))
    s2 = np.bincount(inv, weights=np.where(v, r1 * r1, 0.0), minlength=len(u))
    nn = np.bincount(inv, weights=v.astype(float), minlength=len(u))
    sbad = np.bincount(inv, weights=bad.astype(float), minlength=len(u)) > 0
    trade = cnt >= load_g4.MIN_SESSION_BARS
    ti = np.flatnonzero(trade)  # trading sessions in order
    S1, S2, NN, B = (np.concatenate([[0.0], np.cumsum(x[ti])]) for x in (s1, s2, nn, sbad.astype(float)))
    sig_t = np.full(len(ti), np.nan)
    k = np.arange(len(ti))
    m = k >= SIG_DAYS
    a, b = k[m] - SIG_DAYS, k[m]
    n_ = NN[b] - NN[a]
    mean = (S1[b] - S1[a]) / np.maximum(n_, 1)
    var = ((S2[b] - S2[a]) - n_ * mean ** 2) / np.maximum(n_ - 1, 1)
    good = (B[b] - B[a] == 0) & ~sbad[ti[m]] & (n_ > 1)
    sig_t[m] = np.where(good, np.sqrt(np.maximum(var, 0)), np.nan)
    sig_s = np.full(len(u), np.nan)
    sig_s[ti] = sig_t
    return sig_s[inv], dict(sessions=u, trading=trade, sig_session=sig_s)


def zscore(d, N, sig1):
    t, c = d["t"], d["c"]
    j = np.searchsorted(t, t - N, side="right") - 1
    valid = j >= 0
    jj = np.maximum(j, 0)
    g5 = np.concatenate([[0], np.cumsum(d["gap5"].astype(np.int64))])
    i = np.arange(len(t))
    gap_in = (g5[i + 1] - g5[jj + 1]) > 0  # any bar in (j, i] follows a gap > 5 min
    r = np.log(c / c[jj])
    z = r / (sig1 * np.sqrt(N))
    ok = valid & ~gap_in & ~d["after60"] & np.isfinite(z)
    return np.where(ok, z, np.nan)


def prepare(d):
    if "_sig1" not in d:
        d["_sig1"], d["_sess"] = session_sigma(d)
        n = len(d["t"])
        e_ok = np.zeros(n, bool)
        e_ok[:-1] = (d["dt"][1:] <= 5) & ~d["roll"][1:] & ~d["bad"][1:]
        e_ok[max(n - 2, 0):] = False  # entry bar must not be the last bar of the data
        d["_entry_ok"] = e_ok & ~d["bad"]
    return d


def events(d, side, N, T):
    """Event bar indices i (entry at i + 1), sorted."""
    prepare(d)
    key = ("_z", N)
    if key not in d:
        d[key] = zscore(d, N, d["_sig1"])
    z = d[key]
    hit = (z <= -T) if side == "L" else (z >= T)
    return np.flatnonzero(hit & d["_entry_ok"])


def configs():
    out = []
    for side in ("L", "S"):
        for N, T in NT:
            for TS in TSS:
                out.append(dict(name="%s-%d-%g-%dh" % (side, N, T, TS // 60), side=side, N=N, T=T, TS=TS))
    return out


def count_events(data):
    """Counts only: event bars and episode starts (event bar whose previous bar is not an event) per config x pair x year."""
    rows = []
    for p, d in data["pairs"].items():
        for side in ("L", "S"):
            for N, T in NT:
                ev = events(d, side, N, T)
                ep = ev[np.concatenate([[True], np.diff(ev) > 1])] if len(ev) else ev
                for nm, arr in (("event_bars", ev), ("episodes", ep)):
                    yrs = pd.Series(d["year"][arr]).value_counts()
                    for y, n in yrs.items():
                        rows.append(dict(pair=p, side=side, N=N, T=T, kind=nm, year=int(y), n=int(n)))
    df = pd.DataFrame(rows)
    df["period"] = np.where(df["year"] <= 2012, "TRAIN", "WFO")
    return df


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--count", action="store_true")
    ap.add_argument("--out", default=os.path.expanduser("~/claude_master/w3/fx/g4/out"))
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    data = load_g4.load()
    if a.count:
        df = count_events(data)
        df.to_csv(os.path.join(a.out, "event_counts_g4_by_pair_year.csv"), index=False)
        s = df.groupby(["side", "N", "T", "kind", "period"])["n"].sum().unstack(["kind", "period"])
        s.to_csv(os.path.join(a.out, "event_counts_g4_summary.csv"))
        for r in s.reset_index().itertuples(index=False):
            LOG.info("%s", r)


if __name__ == "__main__":
    main()
