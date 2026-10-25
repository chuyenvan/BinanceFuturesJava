#!/usr/bin/env python3
"""GOLIVE_QUARTERLY kiem tay DOC LAP (chi thu vien chuan: csv, datetime; KHONG import pandas/pipeline/quarterly.py).
Tinh lai cho 2 quy: DEV S7 2022Q2 va HO s42 2026Q1 (gio +07 cua printDone, gan theo gio DONG):
Sigma PnL, so leg dong, so cum (sym, end), so dot vao (anchor = start nho nhat cua cum; dem anchor roi vao quy), win % cum.
So voi quarterly_x14_by_seed.csv. Out: docs/result/golive_quarterly/handcheck.json
"""
import csv
import json
from datetime import datetime

KS = "/home/ubuntu/kaggle_sim/out/"
OUT = "/home/ubuntu/claude_master/vz_e1_wt/docs/result/golive_quarterly/"
CASES = [("tsx-x14-s7", "DEV", "S7", "2022Q2", "20220401 00:00", "20220701 00:00"),
         ("tsx-ho-x14-s42", "HO", "42", "2026Q1", "20260101 00:00", "20260401 00:00")]


def p(s):
    return datetime.strptime(s.strip(), "%Y%m%d %H:%M")


def calc(tag, a, b):
    A, B = p(a), p(b)
    with open(KS + tag + "/storage/printDone.csv", newline="") as fh:
        rd = csv.reader(fh)
        hd = [h.strip() for h in next(rd)]
        ia, ie, ip, isym = hd.index("start"), hd.index("end"), hd.index("pnl"), hd.index("sym")
        legs = [(r[isym].strip(), p(r[ia]), p(r[ie]), float(r[ip])) for r in rd if r and r[ip].strip()]
    pnl, nleg, cl, anc = 0.0, 0, {}, {}
    for sym, ts, te, x in legs:
        k = (sym, te)
        anc[k] = min(anc.get(k, ts), ts)
        if A <= te < B:
            pnl += x
            nleg += 1
            cl[k] = cl.get(k, 0.0) + x
    ent = {t for t in anc.values() if A <= t < B}
    return dict(pnl=pnl, n_leg=nleg, n_cl=len(cl), n_entry=len(ent), win_cl=100.0 * sum(1 for v in cl.values() if v > 0) / len(cl))


def main():
    rows = list(csv.DictReader(open(OUT + "quarterly_x14_by_seed.csv")))
    res = {}
    for tag, ph, seed, q, a, b in CASES:
        h = calc(tag, a, b)
        r = next(x for x in rows if x["phase"] == ph and x["seed"] == seed and x["period"] == q)
        diff = {k: float(r[k]) - h[k] for k in h}
        ok = abs(diff["pnl"]) <= 0.01 and all(abs(diff[k]) == 0 for k in ("n_leg", "n_cl", "n_entry")) and abs(diff["win_cl"]) < 1e-9
        res["%s_%s" % (tag, q)] = dict(hand=h, pipeline={k: float(r[k]) for k in h}, diff=diff, ok=ok)
        print(tag, q, h, "diff", diff, "OK" if ok else "FAIL")
    res["ALL_OK"] = all(v["ok"] for v in res.values())
    json.dump(res, open(OUT + "handcheck.json", "w"), indent=1)
    print("ALL_OK", res["ALL_OK"])


if __name__ == "__main__":
    main()
