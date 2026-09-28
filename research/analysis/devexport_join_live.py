#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""GHEP CAP (ts,symbol) giua feat_dump LIVE va export DEV 2026-07->09 (AUDIT-ONLY).

Pre-reg: docs/prereg/PREREG_DEVEXPORT_202609_AUDIT.md §6
  python3 devexport_join_live.py --export <export.csv.gz> --live <dumps...> [--json out.json]

- Align theo TEN (V3FULL), khong theo vi tri.
- So mean/std/p50/p99/min/max/NaN-rate + shift_sd + tail_ratio + rank-corr.
- Nguong "du mau": >=200 cap (ts,symbol) ghep duoc.
"""
import argparse
import glob
import io
import json
import os
import sys
import zlib

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from feat_diff_live_vs_dev import V3FULL  # nguon su that thu tu ten


def read_gz_partial(path):
    """Doc gz dang ghi (co the truncated) -> DataFrame."""
    with open(path, "rb") as fh:
        data = fh.read()
    d = zlib.decompressobj(16 + zlib.MAX_WBITS)
    try:
        out = d.decompress(data)
    except zlib.error:
        out = b""
    lines = out.decode("utf-8", errors="replace").split("\n")[:-1]
    if not lines:
        return pd.DataFrame()
    return pd.read_csv(io.StringIO("\n".join(lines) + "\n"), on_bad_lines="skip")


def load_live(paths):
    parts = []
    for p in paths:
        for f in sorted(glob.glob(p)):
            try:
                d = read_gz_partial(f)
                if len(d):
                    d["__src"] = os.path.basename(f)
                    parts.append(d)
            except Exception as e:
                print("skip", f, e)
    if not parts:
        return pd.DataFrame()
    d = pd.concat(parts, ignore_index=True)
    d["ts"] = d["ts"].astype(np.int64) // 60000 * 60000
    return d


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--export", required=True)
    ap.add_argument("--live", nargs="+", required=True)
    ap.add_argument("--json")
    a = ap.parse_args()

    exp = pd.read_csv(a.export)
    live = load_live(a.live)
    print("export rows=%d | live rows=%d" % (len(exp), len(live)))
    if len(live) == 0:
        print("KHONG co du lieu live"); return 2
    if len(exp) == 0:
        print("KHONG co du lieu export"); return 2
    print("live ts %d..%d symbols=%s hosts=%s" % (
        live.ts.min(), live.ts.max(), sorted(live.symbol.unique())[:5], sorted(live.__src.unique())))
    print("export ts %d..%d" % (exp.ts.min(), exp.ts.max()))

    live["ts"] = live.ts.astype(np.int64)
    exp["ts"] = exp.ts.astype(np.int64)
    m = live.merge(exp, on="ts", suffixes=("_l", "_e"), how="inner")
    # chi giu cap symbol trung (export la feature thi truong, khong co cot symbol)
    n_distinct = int(m.ts.nunique())
    print("ghep duoc %d dong live (trong do %d phut PHAN BIET) [live x export]" % (len(m), n_distinct))
    by_host = live[live.ts.isin(m.ts.unique())].groupby("__src").size().to_dict()
    print("theo host:", by_host)
    rep = {"live_rows": int(len(live)), "export_rows": int(len(exp)), "pairs": int(len(m)),
           "distinct_ts": n_distinct, "rows_by_host": {k: int(v) for k, v in by_host.items()},
           "live_hosts": sorted(live.__src.unique().tolist()), "feats": {}}
    if len(m) < 200:
        rep["verdict"] = "CHUA DU MAU (<200 cap) — chi de nghi"
    if len(m) == 0:
        rep["need_more"] = "0 cap: dump live phai roi vao cua so export (2026-07-01..2026-09-28 +07)"
        if a.json:
            json.dump(rep, open(a.json, "w"), indent=1)
        print(json.dumps(rep, indent=1))
        return 1

    rows = []
    for c in V3FULL:
        if c + "_l" not in m or c + "_e" not in m:
            continue
        x = m[c + "_l"].to_numpy(float)
        y = m[c + "_e"].to_numpy(float)
        nanl = float(np.mean(~np.isfinite(x)))
        nane = float(np.mean(~np.isfinite(y)))
        x = np.nan_to_num(x); y = np.nan_to_num(y)
        sd = y.std(ddof=1) if len(y) > 2 else 0.0
        shift = (x.mean() - y.mean()) / sd if sd > 0 else float("nan")
        p99 = np.percentile(y, 99) if len(y) else 0.0
        tail = (x.max() / p99) if p99 not in (0, np.nan) else float("nan")
        r = np.corrcoef(x, y)[0, 1] if len(x) > 2 and x.std() > 0 and y.std() > 0 else float("nan")
        rows.append(dict(feature=c, n=len(x), nan_live=nanl, nan_exp=nane,
                         mean_live=x.mean(), mean_exp=y.mean(), sd_exp=sd, shift_sd=shift,
                         p50_live=np.median(x), p50_exp=np.median(y),
                         max_live=x.max(), p99_exp=p99, tail_ratio=tail, rank_corr=r))
        rep["feats"][c] = {k: (float(v) if isinstance(v, (int, float, np.floating)) else v)
                           for k, v in rows[-1].items()}
    t = pd.DataFrame(rows)
    t["abs_shift"] = t.shift_sd.abs()
    t = t.sort_values("abs_shift", ascending=False)
    pd.set_option("display.width", 200)
    print(t[["feature", "mean_live", "mean_exp", "shift_sd", "tail_ratio", "nan_live", "nan_exp",
             "rank_corr"]].to_string(index=False, float_format=lambda v: "%.6g" % v))
    # nghiem pham: |shift_sd|>=1.0 va NaN-rate 2 phia bang nhau
    sus = t[(t.abs_shift >= 1.0) & (np.abs(t.nan_live - t.nan_exp) < 1e-9)]
    print("\nTOP NGHI PHAM (|shift_sd|>=1.0 va NaN-rate khop):")
    print(sus[["feature", "mean_live", "mean_exp", "shift_sd", "tail_ratio"]].to_string(
        index=False, float_format=lambda v: "%.6g" % v))
    rep["top_suspects"] = sus.feature.tolist()
    rep["verdict"] = ("DU MAU" if len(m) >= 200 else "CHUA DU MAU (<200 cap) — chi de nghi")
    if a.json:
        json.dump(rep, open(a.json, "w"), indent=1)
    return 0


if __name__ == "__main__":
    sys.exit(main())
