#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tong hop provenance + JSON nho cho RESULT_DEVEXPORT_202609_AUDIT.
  python3 devexport_finalize.py --export <csv.gz> --verify <v1.json> [<v2.json>] --join <join.json> --out <out.json>
"""
import argparse, gzip, hashlib, json, os
import pandas as pd


def sha256(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            b = fh.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--export", required=True)
    ap.add_argument("--verify", nargs="*", default=[])
    ap.add_argument("--join", default=None)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    rep = {}
    with gzip.open(a.export, "rt") as fh:
        head = fh.readline().strip()
        n = 0
        ts0 = ts1 = None
        md0 = 0
        for line in fh:
            n += 1
            p = line.split(",", 1)[0]
            if ts0 is None:
                ts0 = p
            ts1 = p
            if line.rstrip().endswith(",0"):
                md0 += 1
    rep["export"] = {"path": a.export, "sha256": sha256(a.export), "rows": n,
                     "cols": head.count(",") + 1, "header": head,
                     "ts_min": int(ts0), "ts_max": int(ts1), "md_src0_rows": md0,
                     "bytes_gz": os.path.getsize(a.export)}
    rep["verify"] = []
    for v in a.verify:
        if os.path.exists(v):
            d = json.load(open(v))
            rep["verify"].append({"file": os.path.basename(v),
                                  "joined": d.get("joined"), "n_feat_lech": d.get("n_feat_lech"),
                                  "verdict": d.get("verdict"),
                                  "regime_match": d.get("regime_match"),
                                  "lech_feats": [k for k, f in d.get("feats", {}).items() if not f.get("pass")]})
    if a.join and os.path.exists(a.join):
        j = json.load(open(a.join))
        rep["join_live"] = {k: j[k] for k in ("live_rows", "export_rows", "pairs", "verdict",
                                              "top_suspects", "live_hosts") if k in j}
    json.dump(rep, open(a.out, "w"), indent=1)
    print(json.dumps(rep, indent=1)[:2500])


if __name__ == "__main__":
    main()
