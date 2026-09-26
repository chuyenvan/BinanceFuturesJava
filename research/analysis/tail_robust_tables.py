#!/usr/bin/env python3
"""tail_robust_tables.py — in BANG gon tu /tmp/trr/rep_*.json (doc ket qua, khong do lai)."""
import json
import sys

import numpy as np

RUL = ["median", "tf_5", "wmean_p1p99", "tf_1", "tmean_5", "sign_frac", "conc_5", "conc_1",
       "ic_med", "loss_mean", "max_loss", "wl_ratio", "hhi_gain", "tf_10", "wmean_p5p95",
       "tmean_1", "ic_wmean"]
POS = {"tf_5", "tf_1", "tf_10", "wmean_p1p99", "wmean_p5p95", "tmean_1", "tmean_5", "median",
       "sign_frac", "ic_wmean", "ic_med", "wl_ratio"}       # THUOC: lon hon = tot hon
MAIN = "72_2000_20260905"


def fmt(v, nd=5):
    return ("%+." + str(nd) + "f") % v


def load(p):
    return json.load(open(p))


def table_level(J, objs, cfgs=("72_2000_20260905",)):
    print("\n### LEVEL (point | raw95 | ngoai CI(k=17) | do rong/|point|) — pool %s, %d tick" % (
        J["n_tick"], J["n_tick"]))
    print("%-20s %s" % ("object|thuoc", "  ".join("%-26s" % c for c in cfgs)))
    for o in objs:
        for r in RUL:
            ms = J["level"][o]["metrics"].get(r)
            if not ms:
                continue
            cells = []
            for c in cfgs:
                v = ms.get(c)
                if not v:
                    cells.append("%-26s" % "-")
                    continue
                star = "*" if v["out"] else ("+" if v["out_raw"] else " ")
                cells.append(("%s%s[%s,%s]w%.2f" % (
                    fmt(v["point"]), star, fmt(v["raw"][0], 4), fmt(v["raw"][1], 4),
                    v["width_rel"]))[:26].ljust(26))
            print("%-20s %s" % ("%s|%s" % (o, r), "  ".join(cells)))


def table_delta(J, pairs, ruls=RUL):
    print("\n### DELTA (point, dau, * = NGOAI CI o cau hinh chinh) — %s" % MAIN)
    print("%-26s %s" % ("cap|thuoc", "  ".join("%-16s" % r for r in ruls)))
    for p in pairs:
        if p not in J["delta"]:
            continue
        for r in ruls:
            ms = J["delta"][p]["metrics"].get(r, {})
            v = ms.get(MAIN)
            if not v:
                continue
            print("%-26s %-16s %s [%s,%s] w%.2f %s" % (
                p, r, fmt(v["point"]), fmt(v["raw"][0], 4), fmt(v["raw"][1], 4),
                v["width_rel"], "*NGOAI" if v["out"] else ""))


def table_ci(J, objs, ruls=("median", "tf_5", "wmean_p1p99", "conc_1")):
    print("\n### BANG CI DAY DU (point | raw95 | do rong tuong doi) theo 18 cau hinh")
    for o in objs:
        for r in ruls:
            ms = J["level"][o]["metrics"].get(r)
            if not ms:
                continue
            row = []
            for c in sorted(ms, key=lambda x: (int(x.split("_")[0]), int(x.split("_")[1]),
                                               int(x.split("_")[2]))):
                v = ms[c]
                row.append("%s:%s[%s,%s]w%.2f" % (c, fmt(v["point"], 4), fmt(v["raw"][0], 4),
                                                  fmt(v["raw"][1], 4), v["width_rel"]))
            print("  %-20s %-12s %s" % (o, r, " | ".join(row)))


if __name__ == "__main__":
    J = load(sys.argv[1])
    mode = sys.argv[2] if len(sys.argv) > 2 else "full"
    objs = J["objs"]
    print("### D1 (alpha khong-duoi: Δ vs CA 45deploy VA V1, ngoai CI, cung dau, >=2 thuoc)")
    for o, v in J["D1"].items():
        print("   %-20s n=%d %s %s" % (o, v["n"], v["thuoc_dat"], "QUA" if v["qua_D1"] else ""))
    print("\n### D2 (hieu chuan THUOC bang 2 doi chung bat buoc)")
    for r, v in J["D2"].items():
        print("   %-14s %-20s %s" % (r, ",".join(v["doi_chung_ngoai_CI"]) or "-",
                                     "PHAN GIAI DUOC" if v["phan_giai_duoc"] else "<<< BAT NHIEU"))
    if mode == "full":
        table_level(J, objs)
        table_delta(J, ["A45-45deploy", "V5-V1", "A44-45deploy", "MRA4-A45", "MRA4-45deploy",
                        "S1-45deploy", "S1-V1", "ofi_candidate-45deploy", "ofi_candidate-V1",
                        "ofi_candidate-ofi_baseline_fresh", "ofi_candidate-ofi_noise"])
    else:
        table_delta(J, ["A45-45deploy", "V5-V1", "MRB8-A45", "MRB8-45deploy", "MRB32-A45",
                        "MRB32-45deploy", "MRB32-MRB8"])
        table_level(J, objs)
