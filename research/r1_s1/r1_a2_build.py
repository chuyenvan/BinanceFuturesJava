#!/usr/bin/env python3
"""R1 A2 (RND) — prereg 44acf9cd §2: hoan vi bo-4 gia tri (p0..p3) giua cac coin trong CUNG ts, rng 42, ap len A0
(bins DEV predwf_map_s1a2_x1). Chi hoan vi cac dong co p0 huu han; NaN giu nguyen vi tri.
RNG: np.random.default_rng(42) mot lan, duyet 16 file theo ten tang dan; moi file: khoa ngau nhien rng.random(n_huu_han),
sap (ts, khoa) -> gan bo-4 cua dong thu k (theo thu tu ts on dinh) = bo-4 cua dong thu k (theo (ts, khoa)).
Cong G-SAN: multiset bo-4 tung ts trung 100 %, NaN cung vi tri, (ts, sym) va thu tu record giu nguyen."""
import glob
import hashlib
import json
import logging
import os
import sys

import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout)
log = logging.getLogger("a2")
REC = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("p0", ">f4"), ("p1", ">f4"), ("p2", ">f4"), ("p3", ">f4")])
MAP = "/home/ubuntu/predwf_map_s1a2_x1"
OUT = "/home/ubuntu/claude_master/res1109/r1_s1/a2_bins"
P = ("p0", "p1", "p2", "p3")


def main():
    os.makedirs(OUT, exist_ok=True)
    files = sorted(glob.glob(MAP + "/predict_wf_*.bin"))
    assert len(files) == 16, len(files)
    rng = np.random.default_rng(42)
    rep = {"folds": [], "rng": "default_rng(42), 16 file theo ten", "src": MAP}
    for fn in files:
        b = os.path.basename(fn)
        raw = np.fromfile(fn, dtype=REC)
        fin = np.isfinite(raw["p0"].astype("f8"))
        idx = np.where(fin)[0]
        ts = raw["ts"][idx].astype("i8")
        key = rng.random(len(idx))
        a = idx[np.argsort(ts, kind="stable")]          # thu tu theo ts (on dinh)
        bperm = idx[np.lexsort((key, ts))]              # theo (ts, khoa ngau nhien)
        assert np.array_equal(raw["ts"][a], raw["ts"][bperm])
        new = raw.copy()
        for p in P:
            new[p][a] = raw[p][bperm]
        # G-SAN
        assert np.array_equal(new["ts"], raw["ts"]) and np.array_equal(new["sym"], raw["sym"])
        for p in P:
            assert np.array_equal(np.isnan(new[p]), np.isnan(raw[p])), "NaN lech " + p
        T = np.stack([raw["ts"][idx].astype("f8")] + [raw[p][idx].astype("f8") for p in P], 1)
        U = np.stack([new["ts"][idx].astype("f8")] + [new[p][idx].astype("f8") for p in P], 1)
        T = T[np.lexsort(T.T[::-1])]
        U = U[np.lexsort(U.T[::-1])]
        assert np.array_equal(np.nan_to_num(T, nan=-9), np.nan_to_num(U, nan=-9)), "multiset bo-4 lech " + b
        new.tofile(os.path.join(OUT, b))
        r = dict(fold=b[11:19], rows=int(len(raw)), finite=int(len(idx)),
                 changed_frac=float(np.mean(raw["p0"][idx] != new["p0"][idx])), multiset_eq=True, nan_eq=True)
        rep["folds"].append(r)
        log.info("%s", r)
    h = hashlib.sha256()
    for fn in sorted(glob.glob(OUT + "/predict_wf_*.bin")):
        with open(fn, "rb") as f:
            for blk in iter(lambda: f.read(1 << 20), b""):
                h.update(blk)
    rep["a2_bins_sha256_concat"] = h.hexdigest()
    rep["G_SAN"] = True
    json.dump(rep, open(OUT + "/a2_report.json", "w"), indent=1)
    log.info("DONE sha=%s", rep["a2_bins_sha256_concat"])


if __name__ == "__main__":
    main()
