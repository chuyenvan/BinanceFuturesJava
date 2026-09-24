"""Bo chi tiet theo QUY cho selector ladder: equity tu sim.out + trade stats tu printDone.csv.
Usage: python3 qret_ladder.py [TAG ...]   (mac dinh: 10 tag cua ladder)
Sinh ra bang trong docs/analysis/SELECTOR_LADDER_Q.md."""
import re
import sys
import logging
import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

B = "/home/ubuntu/java/devrun"
QS = ['2022Q1', '2022Q2', '2022Q3', '2022Q4', '2023Q1',
      '2023Q2', '2023Q3', '2023Q4', '2024Q1', '2024Q2',
      '2024Q3', '2024Q4', '2025Q1', '2025Q2', '2025Q3', '2025Q4']
DEFAULT = ["v2_g1", "v3_g1", "map_vol7d_g1", "G1_giveback5", "map_s1a_g1",
           "map_s1a2_g1", "C3", "C2_g015", "C2a", "C2b"]
RX = re.compile(r"Update (\d{8}) \d\d:\d\d => b:(-?\d+).*?unP:\s*(-?\d+)")


def equity(tag):
    """Equity cuoi ngay = b + unP, doc tu logs/sim.out."""
    rows = []
    with open(f"{B}/{tag}/logs/sim.out", errors="ignore") as fh:
        for line in fh:
            m = RX.search(line)
            if m:
                rows.append((m.group(1), int(m.group(2)) + int(m.group(3))))
    e = pd.DataFrame(rows, columns=["d", "equity"]).drop_duplicates("d", keep="last")
    e["d"] = pd.to_datetime(e.d, format="%Y%m%d")
    return e.set_index("d").equity


def trades(tag):
    """printDone.csv: margin = entry*quantity (leverage 1), profit = % gia, pnl = USDT."""
    d = pd.read_csv(f"{B}/{tag}/storage/printDone.csv", on_bad_lines="skip")
    for c in ("entry", "profit", "quantity", "margin", "pnl"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d["ts"] = pd.to_datetime(d["start"], format="%Y%m%d %H:%M", errors="coerce")
    d["q"] = d.ts.dt.to_period("Q").astype(str)
    d["ts_loss"] = d.status == "STOP_LOSS_DONE"   # = time-stop 168h, KHONG phai SL
    return d.dropna(subset=["q"])


def row(vals, fmt):
    return " ".join(format(v, fmt) for v in vals)


def main(tags):
    for t in tags:
        s = equity(t)
        qe = s.resample("QE").last()
        q0 = pd.concat([pd.Series([s.iloc[0]], index=[s.index[0]]), qe]).iloc[:-1]
        qr = dict(zip((str(p) for p in qe.index.to_period("Q")),
                      (qe.values / q0.values - 1) * 100))
        dd = (s / s.cummax() - 1) * 100
        uw = s < s.cummax()
        longest = int(uw.groupby((~uw).cumsum()).sum().max())
        d = trades(t)
        g = d.groupby("q").agg(n=("profit", "size"), tsl=("ts_loss", "mean"),
                               marg=("margin", "median"), medP=("profit", "median"),
                               pnl=("pnl", "sum"))
        log.info("\n== %s END=%.0f n=%d TSloss=%.1f%% margin_med=%.0f "
                 "medP=%.2f meanP=%.2f sumPNL=%.0f maxDD=%.1f UW=%d",
                 t, s.iloc[-1], len(d), 100 * d.ts_loss.mean(), d.margin.median(),
                 d.profit.median(), d.profit.mean(), d.pnl.sum(), dd.min(), longest)
        nan = float("nan")
        log.info("  ret%%   : %s", row([qr.get(q, nan) for q in QS], "+6.1f"))
        log.info("  n      : %s", row([int(g.n.get(q, 0)) for q in QS], "6d"))
        log.info("  TSloss%%: %s", row([100 * g.tsl.get(q, nan) for q in QS], "6.1f"))
        log.info("  margin : %s", row([g.marg.get(q, nan) for q in QS], "6.0f"))
        log.info("  medP   : %s", row([g.medP.get(q, nan) for q in QS], "6.2f"))
        log.info("  sumPNL : %s", row([g.pnl.get(q, nan) for q in QS], "6.0f"))
    log.info("\nQS = %s", QS)


if __name__ == "__main__":
    main(sys.argv[1:] or DEFAULT)
