#!/usr/bin/env python3
"""V4 doc lap: chi csv + datetime, KHONG import quarterly/pipeline.
Tinh lai cum/leg/dot/PnL 2022-25 cua 1 run va so voi runs.csv.
Usage: python3 independent_check.py <tag> <seed>
"""
import csv
import datetime as dt
import json
import os
import sys

KS = "/home/ubuntu/kaggle_sim/out/%s/storage/printDone.csv"
RUNS = os.environ.get("NUP_RUNS",
                      "/home/ubuntu/claude_master/vz_e1_wt/docs/result/nup/runs.csv")


def parse(s):
    return dt.datetime.strptime(s.strip(), "%Y%m%d %H:%M")


def main():
    tag, seed = sys.argv[1], sys.argv[2]
    legs = []
    with open(KS % tag, newline="") as f:
        for r in csv.DictReader(f):
            if not r.get("pnl") or not r.get("quantity") or not r.get("entry") or not r.get("end"):
                continue
            legs.append((r["sym"].strip(), parse(r["start"]), parse(r["end"]), float(r["pnl"]), float(r["quantity"]) * float(r["entry"])))
    ys = {}
    for y in (2022, 2023, 2024, 2025):
        a = dt.datetime(y, 1, 1)
        b = dt.datetime(y + 1, 1, 1)
        L = [x for x in legs if a <= x[2] < b]
        groups = {}
        for x in legs:
            groups.setdefault((x[0], x[2]), []).append(x)
        Lg = {k: v for k, v in groups.items() if a <= k[1] < b}
        t0s = {min(z[1] for z in v) for v in groups.values() if a <= min(z[1] for z in v) < b}
        ys[y] = dict(n_cl=len(Lg), n_leg=len(L), n_entry=len(t0s), pnl=sum(x[3] for x in L))
    T = dict(n_cl=sum(ys[y]["n_cl"] for y in ys), n_leg=sum(ys[y]["n_leg"] for y in ys),
             n_entry=sum(ys[y]["n_entry"] for y in ys), pnl=sum(ys[y]["pnl"] for y in ys))
    # so voi runs.csv
    import csv as _csv
    ref = None
    with open(RUNS, newline="") as f:
        for r in _csv.DictReader(f):
            if r["tag"] == tag and r["seed"] == seed and r["period"] == "DEV_2022_25":
                ref = r
                break
    assert ref, "khong thay row trong runs.csv"
    chk = dict(tag=tag, seed=seed, indep=dict(T=T, **{str(y): ys[y] for y in ys}),
               runs=dict(n_cl=int(ref["n_cl"]), n_leg=int(ref["n_leg"]), n_entry=int(ref["n_entry"]), pnl=float(ref["pnl"])),
               diff=dict(n_cl=int(ref["n_cl"]) - T["n_cl"], n_leg=int(ref["n_leg"]) - T["n_leg"],
                         n_entry=int(ref["n_entry"]) - T["n_entry"], pnl=float(ref["pnl"]) - T["pnl"]))
    chk["ok"] = bool(chk["diff"]["n_cl"] == 0 and chk["diff"]["n_leg"] == 0 and chk["diff"]["n_entry"] == 0
                     and abs(chk["diff"]["pnl"]) < 1e-6)
    print(json.dumps(chk, indent=1))
    return 0 if chk["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
