"""W1 sweep — RATE tren printDone.csv + equity path tu sim.out.

Bao cho moi tag: n, win%, TSloss% (STOP_LOSS_DONE = time-stop 168h),
mean(profit|STOP_MARKET_DONE), mean(profit|STOP_LOSS_DONE), mean(margin),
maxDD, underwater (ngay), return tung quy, ret nam, equity cuoi.
Usage: python3 w1_rates.py TAG [TAG ...]
"""
import logging
import re
import sys

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

B = "/home/ubuntu/java/devrun"
RX = re.compile(r"Update (\d{8}) \d\d:\d\d => b:(-?\d+).*?unP:\s*(-?\d+)")
QS = ['2022Q1', '2022Q2', '2022Q3', '2022Q4', '2023Q1',
      '2023Q2', '2023Q3', '2023Q4', '2024Q1', '2024Q2']


def equity(tag):
    rows = []
    with open(f"{B}/{tag}/logs/sim.out", errors="ignore") as fh:
        for line in fh:
            m = RX.search(line)
            if m:
                rows.append((m.group(1), int(m.group(2)) + int(m.group(3))))
    e = pd.DataFrame(rows, columns=["d", "equity"]).drop_duplicates("d", keep="last")
    e["d"] = pd.to_datetime(e.d, format="%Y%m%d")
    return e.set_index("d").equity


def stats(tag):
    d = pd.read_csv(f"{B}/{tag}/storage/printDone.csv", on_bad_lines="skip")
    for c in ("profit", "margin", "pnl"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d = d.dropna(subset=["profit"])
    s = equity(tag)
    qe = s.resample("QE").last()
    q0 = pd.concat([pd.Series([s.iloc[0]], index=[s.index[0]]), qe]).iloc[:-1]
    qr = dict(zip((str(p) for p in qe.index.to_period("Q")),
                  (qe.values / q0.values - 1) * 100))
    ye = s.resample("YE").last()
    y0 = pd.concat([pd.Series([s.iloc[0]], index=[s.index[0]]), ye]).iloc[:-1]
    yr = dict(zip((str(p.year) for p in ye.index.to_period("Y")),
                  (ye.values / y0.values - 1) * 100))
    dd = (s / s.cummax() - 1) * 100
    uw = s < s.cummax()
    longest = int(uw.groupby((~uw).cumsum()).sum().max())
    sm = d[d.status == "STOP_MARKET_DONE"].profit
    sl = d[d.status == "STOP_LOSS_DONE"].profit
    return {
        "tag": tag, "n": len(d),
        "win": 100.0 * (d.profit > 0).mean(),
        "tsloss": 100.0 * (d.status == "STOP_LOSS_DONE").mean(),
        "mp_sm": sm.mean() if len(sm) else float("nan"),
        "n_sm": len(sm),
        "mp_sl": sl.mean() if len(sl) else float("nan"),
        "n_sl": len(sl),
        "meanP": d.profit.mean(), "medP": d.profit.median(),
        "margin": d.margin.mean(), "margin_med": d.margin.median(),
        "maxDD": dd.min(), "uw": longest, "end": s.iloc[-1],
        "qr": qr, "yr": yr,
        "qmin": min(qr.values()), "neg_year": [y for y, v in yr.items() if v < 0],
    }


def main(tags):
    rows = [stats(t) for t in tags]
    log.info("%-14s %5s %6s %7s %8s %8s %8s %9s %8s %6s %8s",
             "tag", "n", "win%", "TSloss%", "mP|SM", "mP|SL", "meanP",
             "mMargin", "maxDD%", "UW", "equity")
    for r in rows:
        log.info("%-14s %5d %6.2f %7.2f %8.3f %8.3f %8.3f %9.0f %8.2f %6d %8.0f",
                 r["tag"], r["n"], r["win"], r["tsloss"], r["mp_sm"], r["mp_sl"],
                 r["meanP"], r["margin"], r["maxDD"], r["uw"], r["end"])
    log.info("")
    log.info("%-14s %s", "quy%", " ".join(f"{q:>7}" for q in QS))
    for r in rows:
        log.info("%-14s %s", r["tag"],
                 " ".join(f"{r['qr'].get(q, float('nan')):7.1f}" for q in QS))
    log.info("")
    for r in rows:
        log.info("%-14s nam=%s qmin=%.1f neg_year=%s n_SM=%d n_SL=%d medP=%.3f margin_med=%.0f",
                 r["tag"], {k: round(v, 1) for k, v in r["yr"].items()},
                 r["qmin"], r["neg_year"], r["n_sm"], r["n_sl"],
                 r["medP"], r["margin_med"])
    log.info("")
    log.info("HARD CONSTRAINTS: maxDD<=15 UW<=120 no_neg_year qmin>=-5 n>=600")
    for r in rows:
        bad = []
        if r["maxDD"] < -15:
            bad.append(f"maxDD={r['maxDD']:.2f}")
        if r["uw"] > 120:
            bad.append(f"UW={r['uw']}")
        if r["neg_year"]:
            bad.append(f"neg_year={r['neg_year']}")
        if r["qmin"] < -5:
            bad.append(f"qmin={r['qmin']:.1f}")
        if r["n"] < 600:
            bad.append(f"n={r['n']}")
        log.info("%-14s %s", r["tag"], "PASS" if not bad else "FAIL " + " ".join(bad))


if __name__ == "__main__":
    main(sys.argv[1:])
