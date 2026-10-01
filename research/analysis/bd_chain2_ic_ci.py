#!/usr/bin/env python3
"""BD_CHAIN2 (A, CI nhanh) — bootstrap block-72h cho rank-IC(f, nhan).

Toi uu: rank toan cuc 1 lan (average rank) roi bootstrap PEARSON tren rank (tuong duong
Spearman cho mau day du; dung shortcut chuan cho block bootstrap). 2000 rep, seed 20260905,
inflate x1.21 theo PREREG_BD_CHAIN §4.
Nhan: (a) label_oldbasket (gate store) ; (b) EW retEnd_72h ; (c) EW pathq_72h.
Signal: rateDown15MAvg = down15 tu market.bin sinh lai (f) — baseline f=0 cung nguon ticker.
0-SIM, DEV<=2025-12-31.
"""
import glob
import json
import logging
import os
import struct
import sys

import numpy as np
import pandas as pd
from scipy.stats import rankdata

sys.path.insert(0, "/home/ubuntu/sel1m_code")
from funding_label_pb import read_label  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
LOG = logging.getLogger("bd_chain2_ci")

STORE = "/home/ubuntu/claudedata/gate_dataset_full.csv.gz"
LABDIR = "/home/ubuntu/claudedata/wfo15m/label_ds_15m"
BIN_DIR = "/home/ubuntu/kaggle_bdchain/out"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out", "bd_chain2_ic_ci.json")
Q = 900_000
H = 3_600_000
NREP, SEED, INFLATE = 2000, 20260905, 1.21
DT = np.dtype([("ts", ">i8"), ("down", ">f4"), ("up", ">f4"), ("down15", ">f4")])


def load_bin(tag):
    p = os.path.join(BIN_DIR, tag, "market.bin")
    with open(p, "rb") as f:
        n = int(struct.unpack(">i", f.read(4))[0])
        buf = f.read(n * 20)
    a = np.frombuffer(buf, dtype=DT)
    return pd.DataFrame({"ts": a["ts"].astype(np.int64), "d15": a["down15"].astype(np.float64)})


def boot(x, y, bid):
    """rank-IC diem (Spearman) + CI block-72h (rank->Pearson bootstrap)."""
    rx, ry = rankdata(x), rankdata(y)
    pt = float(np.corrcoef(rx, ry)[0, 1])
    ub, inv = np.unique(bid, return_inverse=True)
    order = np.argsort(inv, kind="stable")
    starts = np.searchsorted(inv[order], np.arange(len(ub)))
    ends = np.append(starts[1:], len(order))
    blocks = [order[s:e] for s, e in zip(starts, ends)]
    rng = np.random.default_rng(SEED)
    nb = len(blocks)
    reps = np.empty(NREP)
    for i in range(NREP):
        pick = rng.integers(0, nb, nb)
        ii = np.concatenate([blocks[j] for j in pick])
        reps[i] = np.corrcoef(rx[ii], ry[ii])[0, 1]
    c = reps.mean()
    lo, hi = np.percentile(reps, [2.5, 97.5])
    return dict(point=pt, lo_raw=float(lo), hi_raw=float(hi),
                lo=float(c + (lo - c) * INFLATE), hi=float(c + (hi - c) * INFLATE),
                contains_zero=bool(lo <= 0 <= hi), n=int(len(x)), n_blocks=nb)


def main():
    res = {"nrep": NREP, "seed": SEED, "inflate": INFLATE, "labels": {}}
    st = pd.read_csv(STORE, usecols=["timestamp", "label_oldbasket"])
    st = st[st.timestamp < int(pd.Timestamp("2026-01-01", tz="Asia/Saigon").timestamp() * 1000)]
    st = st[st.timestamp % Q == 0].rename(columns={"label_oldbasket": "lab"})

    ms = {}
    for tag, f in (("f000", 0.0), ("f050", 0.5), ("f100", 1.0)):
        mb = load_bin(tag)
        # map EXACT minute ts -> down15 (ts da o moc 15' => khop thang)
        ms[f] = dict(zip(mb.ts.values, mb.d15.values))

    LOG.info("nhan (a) label_oldbasket ...")
    out = {}
    for f in (0.0, 0.5, 1.0):
        d = st.copy()
        d["sig"] = d.timestamp.map(ms[f]).astype(float)
        d = d.dropna()
        t = d.timestamp.values
        out[str(f)] = boot(d.sig.values, d.lab.values, (t // (72 * H)).astype(np.int64))
        LOG.info("gate f=%.1f n=%d IC=%+.5f CI[%+.5f,%+.5f]", f, out[str(f)]["n"],
                 out[str(f)]["point"], out[str(f)]["lo"], out[str(f)]["hi"])
    res["labels"]["gate_label_oldbasket"] = out

    LOG.info("nhan (b,c) retEnd_72h / pathq_72h EW ...")
    parts = []
    for p in sorted(glob.glob(os.path.join(LABDIR, "funding_label_15m_*.pb"))):
        if "2026" in os.path.basename(p):
            continue
        L = read_label(p, usecols=["tEpochMs", "retEnd_72h", "maxFav_72h", "maxAdv_72h"])
        L["pathq"] = L["maxFav_72h"] / (L["maxAdv_72h"].abs() + 0.01)
        parts.append(L.groupby("tEpochMs").agg(retEnd=("retEnd_72h", "mean"),
                                               pathq=("pathq", "mean")).reset_index())
    fwd = pd.concat(parts, ignore_index=True)
    fwd["ts15"] = fwd.tEpochMs.astype(np.int64)   # tEpochMs da o moc 15'
    for lab in ("retEnd", "pathq"):
        o = {}
        for f in (0.0, 0.5, 1.0):
            m = fwd[["ts15", lab]].copy()
            m["sig"] = m.ts15.map(ms[f]).astype(float)
            m = m.dropna()
            o[str(f)] = boot(m.sig.values, m[lab].values, (m.ts15.values // (72 * H)).astype(np.int64))
            LOG.info("%s f=%.1f n=%d IC=%+.5f CI[%+.5f,%+.5f]", lab, f, o[str(f)]["n"],
                     o[str(f)]["point"], o[str(f)]["lo"], o[str(f)]["hi"])
        res["labels"][f"{lab}_72h_EW"] = o

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as fh:
        json.dump(res, fh, indent=1, ensure_ascii=False)
    LOG.info("saved %s", OUT)


if __name__ == "__main__":
    main()
