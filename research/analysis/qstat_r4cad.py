#!/usr/bin/env python3
"""QSTAT_R4CAD — bang theo QUY/NAM cho C0/C1 (R4 cadence). THUAN PYTHON OFFLINE.

Doc printDone.csv + sim.out cua 2 tag, in bang quy/nam (n, sel/BD/DCA, win%, TSloss%,
meanP%, mP|SM, mP|SL, PnL, funding, margin TB, ROI%, equity, maxDD ngay, UW ngay).

Usage: python3 qstat_r4cad.py <tag0> <tag1>
"""
import collections
import csv
import logging
import re
import sys

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("qstat_r4cad")

OUT = "/home/ubuntu/kaggle_sim/out"


def load(tag):
    base = OUT + "/%s/" % tag
    eq = collections.OrderedDict()
    pat = re.compile(r'Update (\d{8}) \d\d:\d\d => b:\s*(-?[\d.]+).*?unP:\s*(-?[\d.]+)')
    for line in open(base + "logs/sim.out", errors="ignore"):
        if "BudgetManagerSimple: Update" not in line:
            continue
        m = pat.search(line)
        if m:
            eq[m.group(1)] = float(m.group(2)) + float(m.group(3))
    days = list(eq.keys())
    rows = list(csv.DictReader(open(base + "storage/printDone.csv")))
    T = collections.defaultdict(list)
    for r in rows:
        try:
            r["_p"] = float(r["profit"])
            r["_pnl"] = float(r["pnl"])
            r["_m"] = float(r["margin"])
            r["_f"] = float(r["funding"] or 0)
        except Exception:
            continue
        T[q_of(r["end"][:8])].append(r)
    return eq, days, T, rows


def q_of(d):
    return "%sQ%d" % (d[:4], (int(d[4:6]) - 1) // 3 + 1)


def ddstats(ds, eq):
    peak = None
    mdd = 0
    uw = 0
    cur = 0
    best = 0
    for d in ds:
        v = eq[d]
        if peak is None or v >= peak:
            peak = v
            cur = 0
        else:
            cur += 1
        mdd = min(mdd, v / peak - 1)
        best = max(best, cur)
    return mdd * 100, best


def table(eq, days, T, key_fn, label):
    groups = collections.OrderedDict()
    for d in days:
        groups.setdefault(key_fn(d), []).append(d)
    out = []
    prev_end = 35000.0
    for g, ds in groups.items():
        tr = [r for k, v in T.items() if (k[:4] == g if label == "Y" else k == g) for r in v]
        n = len(tr)
        lv = collections.Counter(r["level"] for r in tr)
        win = 100 * sum(r["_pnl"] > 0 for r in tr) / n if n else float("nan")
        tsl = 100 * sum(r["status"] == "STOP_LOSS_DONE" for r in tr) / n if n else float("nan")
        meanP = sum(r["_p"] for r in tr) / n if n else float("nan")
        sm = [r["_p"] for r in tr if r["status"] == "STOP_MARKET_DONE"]
        sl = [r["_p"] for r in tr if r["status"] == "STOP_LOSS_DONE"]
        pnl = sum(r["_pnl"] for r in tr)
        fund = sum(r["_f"] for r in tr)
        mar = sum(r["_m"] for r in tr) / n if n else 0
        end = eq[ds[-1]]
        roi = (end / prev_end - 1) * 100
        mdd, uw = ddstats(ds, eq)
        out.append((g, n, lv.get("PREDICT_SYMBOL_TRADE", 0), lv.get("BIG_DOWN", 0),
                    lv.get("DCA_LEVEL1", 0), win, tsl, meanP,
                    (sum(sm) / len(sm)) if sm else float("nan"),
                    (sum(sl) / len(sl)) if sl else float("nan"),
                    pnl, fund, mar, roi, end, mdd, uw))
        prev_end = end
    return out


def emit(title, rows):
    hdr = ("| %s | n | sel | BD | DCA | win%% | TSloss%% | meanP%% | mP|SM%% | mP|SL%% | "
           "PnL | funding | marginTB | ROI%% | eqCuoi | maxDD%% | UW |" % title)
    log.info(hdr)
    log.info("|" + "---|" * 17)
    for r in rows:
        log.info("| %s | %d | %d | %d | %d | %.2f | %.2f | %.3f | %.2f | %.2f | "
                 "%.1f | %.1f | %.0f | %.2f | %.0f | %.2f | %d |", *r)


def main():
    t0, t1 = sys.argv[1], sys.argv[2]
    eq0, days0, T0, rows0 = load(t0)
    eq1, days1, T1, rows1 = load(t1)
    log.info("=== %s (C0) vs %s (C1) ===", t0, t1)
    log.info("C0 n_total=%d eq=%.0f | C1 n_total=%d eq=%.0f",
             len(rows0), eq0[days0[-1]], len(rows1), eq1[days1[-1]])
    log.info("")
    log.info("--- C0 (R4, nhip 1') ---")
    emit("quy", table(eq0, days0, T0, q_of, "Q"))
    log.info("")
    log.info("--- C1 (R4, selector 15') ---")
    emit("quy", table(eq1, days1, T1, q_of, "Q"))
    log.info("")
    log.info("--- theo NAM ---")
    emit("nam C0", table(eq0, days0, T0, lambda d: d[:4], "Y"))
    log.info("")
    emit("nam C1", table(eq1, days1, T1, lambda d: d[:4], "Y"))


if __name__ == "__main__":
    main()
