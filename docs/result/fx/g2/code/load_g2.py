"""FX G2 loader (PREREG_FX_G2 sec 1-3 + MASTER chot). Re-uses the audited G1 loader (FX quote direction, OECD rates,
cutoff guard, --holdout token, is_real flag) by import; adds BIS REER monthly (narrow basket) with the same cutoff guard.
"""
import argparse
import csv
import logging
import os
import sys

import numpy as np
import pandas as pd

G1_CODE = os.environ.get("G1_CODE", os.path.expanduser("~/claude_master/w3/fx/g1/code"))
if G1_CODE not in sys.path:
    sys.path.insert(0, G1_CODE)
import load_g1 as L1  # noqa: E402

LOG = logging.getLogger("g2.load")
DEFAULT_DATA = L1.DEFAULT_DATA
DEFAULT_REER = os.path.join(DEFAULT_DATA, "bis_reer_monthly.csv")
DEFAULT_CUTOFF = L1.DEFAULT_CUTOFF
CCYS = L1.CCYS
AREA = {"EUR": "XM", "JPY": "JP", "GBP": "GB", "CHF": "CH", "CAD": "CA", "AUD": "AU", "NZD": "NZ", "NOK": "NO",
        "SEK": "SE"}
BASKET = "N"   # narrow (27 economies), from 1964 for all 10 areas (bis_inventory.md)


def read_reer(path, cutoff, basket=BASKET):
    """bis_reer_monthly.csv columns: area, basket, month (YYYY-MM), reer[, unit, status]. Rows with month after the cutoff
    month are skipped before the value is parsed. Returns DataFrame PeriodIndex(M) x ccy (only the 9 G2 currencies)."""
    cm = pd.Timestamp(cutoff).to_period("M")
    inv = {a: c for c, a in AREA.items()}
    recs, dropped = {}, 0
    with open(path, newline="") as fh:
        for row in csv.DictReader(fh):
            if row["basket"] != basket or row["area"] not in inv:
                continue
            m = pd.Period(row["month"], "M")
            if m > cm:
                dropped += 1
                continue
            s = row["reer"].strip()
            recs[(m, inv[row["area"]])] = np.nan if s in ("", ".", "NaN") else float(s)
    LOG.info("read %s basket %s: %d values kept, %d rows > cutoff skipped", os.path.basename(path), basket, len(recs),
             dropped)
    if not recs:
        return pd.DataFrame(columns=CCYS, dtype=float)
    s = pd.Series(recs)
    df = s.unstack()
    df.index = pd.PeriodIndex(df.index, freq="M")
    return df.reindex(columns=CCYS).sort_index()


def load(data_dir=DEFAULT_DATA, cutoff=DEFAULT_CUTOFF, holdout=None, reer_path=None):
    """G1 loader (cutoff + holdout guard, is_real=True) + data.reer (None if the REER file is missing)."""
    d = L1.load(data_dir, cutoff, holdout)
    rp = reer_path or os.path.join(data_dir, "bis_reer_monthly.csv")
    if os.path.exists(rp):
        d.reer = read_reer(rp, d.cutoff)
        assert len(d.reer) == 0 or d.reer.index.max().to_timestamp() <= d.cutoff
    else:
        LOG.warning("REER file %s missing -> value-filter configs unavailable (trend only)", rp)
        d.reer = None
    return d


def universe_g2(data):
    """Per month m: G1 universe (rate(m-1) for ccy and USD, >= 1 valid price in m, no run > 3 missing days) AND a valid
    price on the signal row T(m) itself (prereg G2 sec 3: 'ty gia hop le o ngay can bang')."""
    if "u2" in data._cache:
        return data._cache["u2"]
    out = []
    for mi in data.months():
        if mi.T is None:
            out.append(mi)
            continue
        u = [c for c in mi.univ if data.valid[mi.T, data.ccys.index(c)]]
        out.append(mi._replace(univ=u, r={c: mi.r[c] for c in u}))
    data._cache["u2"] = out
    return out


def main():
    ap = argparse.ArgumentParser(description="G2 loader summary (no returns)")
    ap.add_argument("--data", default=DEFAULT_DATA)
    ap.add_argument("--reer", default=None)
    ap.add_argument("--cutoff", default=DEFAULT_CUTOFF)
    ap.add_argument("--holdout", default=None)
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    d = load(a.data, a.cutoff, a.holdout, a.reer)
    by = {}
    for mi in universe_g2(d):
        if mi.m >= pd.Period("1975-01", "M"):
            by.setdefault(mi.m.year, []).append(len(mi.univ))
    for y, v in sorted(by.items()):
        LOG.info("universe %d: min %d max %d", y, min(v), max(v))
    if d.reer is not None:
        LOG.info("REER %s..%s, ccys %s", d.reer.index.min(), d.reer.index.max(), list(d.reer.columns))


if __name__ == "__main__":
    main()
