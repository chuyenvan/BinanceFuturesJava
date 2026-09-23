"""EXIT FIT — BUOC 1b: CONG PARITY (harness offline vs printDone T170).

Chay:  python3 parity.py
PASS/FAIL theo nguong da chot trong docs/PREREG_EXIT_FIT.md muc 2.3.
Ket qua chi tiet: /home/ubuntu/exitfit/parity_detail.csv
"""
import csv
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import exit_engine as E  # noqa: E402

OUT = "/home/ubuntu/exitfit"


def main():
    clusters = E.load_clusters()
    bars = E.load_bars()
    pol = E.make_p0()
    rows = []
    bad_bar = 0
    for cl in clusters:
        if cl["cid"] not in bars:
            bad_bar += 1
            continue
        res = E.simulate(cl, bars, pol)
        if not res["ok"]:
            bad_bar += 1
            continue
        rows.extend(res["rows"])
    print("legs replayed=%d  (clusters thieu nen=%d)" % (len(rows), bad_bar))

    n = len(rows)
    ok_status = 0
    ok_min = 0
    ok_min2 = 0
    ok_tp = 0
    ok_tp_exact = 0
    dpnl = []
    mism = []
    for r in rows:
        tm = r["csv_end_ts"]
        if r["status"] == r["csv_status"]:
            ok_status += 1
        dmin = abs(r["end"] - tm) / 60000.0
        if dmin < 0.5:
            ok_min += 1
        if dmin <= 2.0:
            ok_min2 += 1
        tick = float(E.TICKS.get(r["sym"], 0) or 0)
        # tick khong co trong pin (symbol delist/moi) => normalizePrice KHONG lam gi
        #   => hai ben phai TRUNG float32; dung eps tuong doi nho thay cho "1 tick".
        tol = tick if tick > 0 else max(1e-9, 1e-7 * abs(r["csv_tp"]))
        if abs(r["tp"] - r["csv_tp"]) <= tol + 1e-12:
            ok_tp += 1
        if r["tp"] == r["csv_tp"]:
            ok_tp_exact += 1
        delta = r["pnl_nofund"] - (r["csv_pnl"] + r["csv_funding"])
        dpnl.append(delta)
        if r["status"] != r["csv_status"] or dmin >= 0.5 or abs(delta) > 1.0:
            mism.append((r, dmin, delta))
    dpnl = np.abs(np.asarray(dpnl))
    med = float(np.median(dpnl))
    frac1 = float(np.mean(dpnl <= 1.0))
    print("status match      %6.2f%%  (>=99.0)" % (100.0 * ok_status / n))
    print("exit minute exact %6.2f%%  (>=97.0)" % (100.0 * ok_min / n))
    print("exit minute <=2'  %6.2f%%  (>=99.0)" % (100.0 * ok_min2 / n))
    print("priceTP match     %6.2f%%  (>=95.0)   [float32 y nguyen %.2f%%]" %
          (100.0 * ok_tp / n, 100.0 * ok_tp_exact / n))
    print("|dPnL nofund| med %6.4f USDT (<=0.02)   frac<=1USDT %6.2f%% (>=95.0)" % (med, 100 * frac1))
    checks = [
        (100.0 * ok_status / n >= 99.0, "status"),
        (100.0 * ok_min / n >= 97.0, "exit_minute_exact"),
        (100.0 * ok_min2 / n >= 99.0, "exit_minute_2pct"),
        (100.0 * ok_tp / n >= 95.0, "priceTP"),
        (med <= 0.02, "pnl_median"),
        (100 * frac1 >= 95.0, "pnl_frac1"),
    ]
    fails = [c[1] for c in checks if not c[0]]
    print("VERDICT: " + ("PASS" if not fails else "FAIL -> " + ",".join(fails)))

    with open(os.path.join(OUT, "parity_detail.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["sym", "ts", "entry", "qty", "status", "csv_status", "rep_end", "csv_end",
                    "dmin", "rep_tp", "csv_tp", "dPnL_nofund", "csv_pnl", "csv_funding", "level"])
        for r in rows:
            tm = r["csv_end_ts"]
            w.writerow([r["sym"], r["ts"], r["entry"], r["qty"], r["status"], r["csv_status"],
                        r["end"], r["csv_end"], abs(r["end"] - tm) / 60000.0, r["tp"], r["csv_tp"],
                        r["pnl_nofund"] - (r["csv_pnl"] + r["csv_funding"]), r["csv_pnl"],
                        r["csv_funding"], r["level"]])
    print("mismatch (status/1-phut/dPnL>1USDT): %d -> xem parity_detail.csv" % len(mism))
    for r, dmin, delta in mism[:15]:
        print("   %-12s %s rep=%s csv=%s dmin=%.0f tp=%.10g/%.10g dPnL=%.4f lvl=%s" %
              (r["sym"], r["ts"], r["status"], r["csv_status"], dmin, r["tp"], r["csv_tp"], delta, r["level"]))


if __name__ == "__main__":
    main()
