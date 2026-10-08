#!/usr/bin/env python3
"""HO1 B5b — funding.bin (bins selector 15' forward-fill -> moi phut market) bang Python, y het
WfoDataset.buildFundingFromWfFiles(horizonIdx=0) + forwardFillToGrid(stale 15') + HoldoutSeal.trimMap + writeFunding.
Pre-reg docs/prereg/PREREG_HOLDOUT2026H1.md (35d03784) §2.4.
  regen : cong G-B5f — tai sinh funding.bin DEV tu 18 bins DEV + luoi market.bin DEV, cat >= SEAL_MS (UTC),
          so md5 8e57d900 (chi tinh md5 streaming, khong ghi dia).
  build : funding.bin holdout = 18 bins DEV + bins 2026 (--extra DIR) tren luoi market.bin holdout, cat >= --end;
          assert phan ban ghi ts < 2026-01-01 00:00 +07 == DEV (byte).
Usage: python3 ho1_funding_build.py regen | build --extra DIR --market FILE --out FILE
"""
import argparse
import glob
import hashlib
import json
import logging
import os
import struct
import sys

import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("ho1fnd")

DEV_BINS = "/home/ubuntu/predwf_map_s1a2_x1_2021"
DEV_DS = "/home/ubuntu/wfo_ds_x1_2021"
DEV_FUND_MD5 = "8e57d900d5c54c744bfcaf5c9b27fc93"
SEAL_UTC = 1767225600000
SEAL7 = SEAL_UTC - 7 * 3600000
STALE = 15 * 60000
DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("p0", ">f4"), ("p1", ">f4"), ("p2", ">f4"), ("p3", ">f4")])


def md5f(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def manifest_md5s():
    out = {}
    for ln in open(DEV_DS + "/manifest.txt"):
        if ln.startswith("predictWf."):
            k, v = ln.strip()[len("predictWf."):].split("=", 1)
            out[k] = v.split(";")[0].split(":")[1]
    return out


def load_bins(files):
    """-> u (tick ts tang dan), cnt, blocks (bytes BE i64 encoded/tick), meta. Thu tu trong tick = thu tu doc file."""
    T, E, ranges, meta = [], [], [], []
    for f in files:
        a = np.fromfile(f, dtype=DT)
        assert os.path.getsize(f) == a.size * 26
        ts = a["ts"].astype(np.int64)
        lo, hi = int(ts.min()), int(ts.max())
        for (l2, h2, n2) in ranges:
            assert not (lo <= h2 and l2 <= hi), ("OVERLAP", f, n2)
        ranges.append((lo, hi, os.path.basename(f)))
        p = a["p0"].astype(np.float32)
        ok = ~np.isnan(p)
        score = (np.float32(1.0) - p[ok]).astype(np.float32)
        enc = (a["sym"][ok].astype(np.int64) << 32) | score.view(np.uint32).astype(np.int64)
        T.append(ts[ok])
        E.append(enc)
        meta.append(dict(name=os.path.basename(f), md5=md5f(f), nrec=int(a.size), nan=int((~ok).sum()), ts_min=lo, ts_max=hi,
                         span_days=(hi - lo) // 86400000))
        log.info("bins %s rec=%d nan=%d span=%dd", meta[-1]["name"], a.size, meta[-1]["nan"], meta[-1]["span_days"])
    T, E = np.concatenate(T), np.concatenate(E)
    o = np.argsort(T, kind="stable")
    T, E = T[o], E[o]
    u, st, cnt = np.unique(T, return_index=True, return_counts=True)
    EB = E.astype(">i8").tobytes()
    blocks = [EB[s * 8:(s + c) * 8] for s, c in zip(st, cnt)]
    return u, cnt, blocks, meta


def market_keys(p):
    raw = open(p, "rb").read()
    n = struct.unpack(">i", raw[:4])[0]
    a = np.frombuffer(raw[4:4 + 20 * n], dtype=np.dtype([("ts", ">i8"), ("v", "V12")]))
    k = a["ts"].astype(np.int64)
    assert (np.diff(k) > 0).all()
    return k


def emit(u, cnt, blocks, grid, end, sink, seal7_track=False):
    """forwardFillToGrid + trim (ts < end) + writeFunding, day ra sink(bytes). Tra (n, n_before_first, n_stale, off_seal7)."""
    j = np.searchsorted(u, grid, side="right") - 1
    valid = (j >= 0)
    stale = valid & ((grid - u[np.clip(j, 0, None)]) > STALE)
    keep = valid & ~stale & (grid < end)
    n = int(keep.sum())
    sink(struct.pack(">i", n))
    off, off7 = 4, None
    buf = []
    size = 0
    for t, jj in zip(grid[keep].tolist(), j[keep].tolist()):
        if seal7_track and off7 is None and t >= SEAL7:
            off7 = off
        b = struct.pack(">qi", t, int(cnt[jj])) + blocks[jj]
        buf.append(b)
        size += len(b)
        off += len(b)
        if size > (64 << 20):
            sink(b"".join(buf))
            buf, size = [], 0
    if buf:
        sink(b"".join(buf))
    if seal7_track and off7 is None:
        off7 = off
    return n, int((~valid).sum()), int(stale.sum()), off7


def dev_files():
    fs = sorted(glob.glob(DEV_BINS + "/predict_wf_*.bin"))
    mm = manifest_md5s()
    assert len(fs) == 18 and set(os.path.basename(f) for f in fs) == set(mm)
    return fs, mm


def regen():
    fs, mm = dev_files()
    u, cnt, blocks, meta = load_bins(fs)
    assert all(m["md5"] == mm[m["name"]] for m in meta), "md5 bins DEV lech manifest"
    grid = market_keys(DEV_DS + "/market.bin")
    h = hashlib.md5()
    n, nb, ns, off7 = emit(u, cnt, blocks, grid, SEAL_UTC, h.update, seal7_track=True)
    g = dict(n=n, before_first=nb, stale=ns, raw15m=int(len(u)), md5=h.hexdigest(), want=DEV_FUND_MD5,
             off_seal7=off7)
    g["pass"] = g["md5"] == DEV_FUND_MD5
    log.info("G-B5f tai sinh funding.bin DEV: %s", g)
    os.makedirs("/home/ubuntu/claude_master/1003/ho1/ds", exist_ok=True)
    json.dump(dict(G_B5f=g, bins=meta), open("/home/ubuntu/claude_master/1003/ho1/ds/funding_regen.json", "w"), indent=1)
    return g


def build(extra, market, out, end):
    fs, mm = dev_files()
    xs = sorted(glob.glob(extra + "/predict_wf_*.bin"))
    assert xs, "khong co bins 2026"
    u, cnt, blocks, meta = load_bins(fs + xs)
    assert all(m["md5"] == mm[m["name"]] for m in meta if m["name"] in mm)
    for m in meta:
        assert m["span_days"] <= 100, ("span", m)
    grid = market_keys(market)
    with open(out, "wb") as f:
        n, nb, ns, off7 = emit(u, cnt, blocks, grid, end, f.write, seal7_track=True)
    # DEV prefix: ban ghi ts < SEAL7 phai == DEV funding.bin (cung offset, bo header)
    h_new, h_dev = hashlib.md5(), hashlib.md5()
    with open(out, "rb") as f1, open(DEV_DS + "/funding.bin", "rb") as f2:
        f1.seek(4)
        f2.seek(4)
        left = off7 - 4
        while left > 0:
            k = min(left, 1 << 24)
            h_new.update(f1.read(k))
            h_dev.update(f2.read(k))
            left -= k
    res = dict(n=n, before_first=nb, stale=ns, raw15m=int(len(u)), off_seal7=off7, md5_prefix_new=h_new.hexdigest(),
               md5_prefix_dev=h_dev.hexdigest(), md5=md5f(out), bytes=os.path.getsize(out), end=end, bins=meta)
    res["prefix_equal"] = res["md5_prefix_new"] == res["md5_prefix_dev"]
    log.info("BUILD funding holdout: %s", {k: v for k, v in res.items() if k != "bins"})
    assert res["prefix_equal"], "phan DEV cua funding.bin moi != DEV"
    json.dump(res, open(out + ".json", "w"), indent=1)
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["regen", "build"])
    ap.add_argument("--extra")
    ap.add_argument("--market")
    ap.add_argument("--out")
    ap.add_argument("--end", type=int, default=1782864000000)
    a = ap.parse_args()
    if a.mode == "regen":
        sys.exit(0 if regen()["pass"] else 2)
    build(a.extra, a.market, a.out, a.end)
