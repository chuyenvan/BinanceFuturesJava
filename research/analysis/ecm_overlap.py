#!/usr/bin/env python3
"""ECMEAS chan doan PHU (khong phai thuoc pre-reg): do trung lenh bucket vs phi goc / stress cung seed.
Muc dich: H khong co parity off jar 246087fb tren cua so 2026 => so ty le trung (sym, start) H voi D; neu jar lam lech
rieng 2026 (vd mapper/universe) se thay symbol chi-co-o-1-ben hoac ty le trung H << D.
Usage: python3 ecm_overlap.py out.json
"""
import csv, json, logging, sys

O = "/home/ubuntu/kaggle_sim/out/"
SEEDS = [42, 7, 13, 21, 99, 123, 777, 2024]
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout)
log = logging.getLogger("ecmov")


def tg(w, v, s):
    if w == "D":
        return {"bucket": "ec-s-s42" if s == 42 else "ecm-d-s%d" % s, "goc": "gqsf-a1" if s == 42 else "gqsf-s%d" % s,
                "stress": "nsel-nen-s%d" % s}[v]
    return {"bucket": "ecm-h-s%d" % s, "goc": "ho4-k24-b-s%d" % s, "stress": "ho4-k24-s-s%d" % s}[v]


def keys(tag, lo, hi):
    out = set()
    with open(O + tag + "/storage/printDone.csv", newline="") as f:
        for r in csv.DictReader(f):
            st = r["start"].strip()
            if lo <= st < hi:
                out.add((r["sym"].strip(), st))
    return out


def main():
    res = {}
    win = {"D": ("20210701 00:00", "20260101 00:00"), "H": ("20260101 00:00", "20261001 00:00")}
    for w, (lo, hi) in win.items():
        res[w] = {}
        for s in SEEDS:
            try:
                k = {v: keys(tg(w, v, s), lo, hi) for v in ("bucket", "goc", "stress")}
            except FileNotFoundError as e:
                log.warning("thieu %s", e)
                continue
            r = {}
            for ref in ("goc", "stress"):
                a, b = k["bucket"], k[ref]
                sa, sb = {x[0] for x in a}, {x[0] for x in b}
                r[ref] = {"n_b": len(a), "n_ref": len(b), "common": len(a & b), "frac": len(a & b) / max(len(a), len(b), 1),
                          "sym_only_bucket": sorted(sa - sb), "sym_only_ref": sorted(sb - sa)}
            res[w][str(s)] = r
            log.info("%s s%d trung goc %.3f (sym chi b %d / chi goc %d) trung stress %.3f", w, s, r["goc"]["frac"],
                     len(r["goc"]["sym_only_bucket"]), len(r["goc"]["sym_only_ref"]), r["stress"]["frac"])
    json.dump(res, open(sys.argv[1], "w"), indent=1)
    log.info("WROTE %s", sys.argv[1])


if __name__ == "__main__":
    main()
