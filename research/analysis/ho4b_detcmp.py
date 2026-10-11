#!/usr/bin/env python3
"""HO4-P0b Q1: so output kernel ho4b-det (2 lan cung input; gate them khoi dau som) va ho4b-d1x (bo 10 symbol chi-file)
voi nhau va voi DEV tren cung cua so. Thuoc: gate 33 V3FULL rel 1e-6; Tool1 40 cot rel 1e-6 (hop khoa); nhan (tEpochMs,symbol)
+ nBars_72h; market tap phut + gia tri. Chi dem/ty le. Usage: ho4b_detcmp.py <det_out_dir> <d1x_out_dir|-> <out.json>"""
import glob, json, logging, os, struct, sys
import numpy as np
import pandas as pd
R = "/home/ubuntu/src/BinanceFuturesJava"
sys.path.insert(0, R); sys.path.insert(0, R + "/research/pipeline"); sys.path.insert(0, R + "/research/analysis"); sys.path.insert(0, "/home/ubuntu/sel1m_code")
import g015_net_train as G  # noqa: E402
import gate_ablation_driver as GA  # noqa: E402
from funding_label_pb import read_label  # noqa: E402
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("ho4b_dc")
DET, D1X, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
GLO, GHI = 1759165200000, 1760547600000      # gate: 2025-09-30 00:00 .. 2025-10-16 00:00 +07 (sau warm-up ca 2 lan)
TLO, THI = 1759276800000, 1760572800000      # Tool1: 2025-10-01 00:00 .. 2025-10-16 00:00 UTC
LLO, LHI = 1759276800000, 1759968000000      # nhan: 2025-10-01 .. 2025-10-09 00:00 UTC (du 72h nhin truoc trong end=10-12)
RES = {}


def okc(a, b):
    return (np.abs(a - b) <= 1e-6 * np.maximum(1.0, np.abs(b))) | (np.isnan(a) & np.isnan(b))


def load_gate(p):
    d = pd.read_csv(p, usecols=["timestamp"] + GA.V3FULL)
    return d[(d.timestamp >= GLO) & (d.timestamp < GHI)].drop_duplicates("timestamp").set_index("timestamp").sort_index()


def cmp_gate(a, b):
    idx = a.index.union(b.index); com = a.index.intersection(b.index)
    per, bad = {}, (len(idx) - len(com)) * len(GA.V3FULL)
    for c in GA.V3FULL:
        ok = okc(a.loc[com, c].to_numpy(np.float64), b.loc[com, c].to_numpy(np.float64))
        per[c] = round(float(ok.mean()), 4); bad += int((~ok).sum())
    return dict(rows_a=len(a), rows_b=len(b), common=len(com), ok_frac=1 - bad / max(1, len(idx) * len(GA.V3FULL)),
                cols_bad={c: v for c, v in per.items() if v < 0.999})


def load_t1(p):
    x = G.read_tool1(p, grid_ms=G.GRID_MS)
    t = x["ts"].astype(np.int64)
    x = x[(t >= TLO) & (t < THI)]
    k = x["ts"].astype(np.int64) * 10000 + x["sym"].astype(np.int64)
    o = np.argsort(k, kind="stable")
    return k[o], np.asarray(x["f"], dtype=np.float64)[o]


def cmp_t1(A, B):
    (ka, fa), (kb, fb) = A, B
    com, ia, ib = np.intersect1d(ka, kb, return_indices=True)
    bad, col = (len(ka) + len(kb) - 2 * len(com)) * fa.shape[1], {}
    for j in range(fa.shape[1]):
        ok = okc(fa[ia, j], fb[ib, j]); col[j] = round(float(ok.mean()), 4); bad += int((~ok).sum())
    cells = (len(ka) + len(kb) - len(com)) * fa.shape[1]
    return dict(keys_a=int(len(ka)), keys_b=int(len(kb)), common=int(len(com)), ok_frac=1 - bad / max(cells, 1),
                cols_bad={int(j): v for j, v in col.items() if v < 0.999})


def load_lab(files):
    d = pd.concat([read_label(f, usecols=["tEpochMs", "symbol", "nBars_72h"]) for f in files])
    return d[(d.tEpochMs >= LLO) & (d.tEpochMs < LHI) & (d.tEpochMs % 900000 == 0)]


def cmp_lab(a, b):
    M = a.merge(b, on=["tEpochMs", "symbol"], how="outer", suffixes=("_a", "_b"), indicator=True)
    both = M[M._merge == "both"]
    return dict(rows_a=int(len(a)), rows_b=int(len(b)), common=int(len(both)), only_a=int((M._merge == "left_only").sum()),
                only_b=int((M._merge == "right_only").sum()), eq_frac_common=float((both.nBars_72h_a == both.nBars_72h_b).mean()),
                eq_frac_union=float((both.nBars_72h_a == both.nBars_72h_b).sum() / max(1, len(M))))


def rd_mkt(p):
    with open(p, "rb") as f:
        n = struct.unpack(">i", f.read(4))[0]
        a = np.frombuffer(f.read(20 * n), dtype=np.dtype([("ts", ">i8"), ("v", "V12")]))
    return a["ts"].astype(np.int64), a["v"]


def main():
    f = lambda d, pat: (sorted(glob.glob(os.path.join(d, pat))) or [None])[0]
    # market: 2 lan cung input
    t1, v1 = rd_mkt(f(DET, "mkt1.bin")); t2, v2 = rd_mkt(f(DET, "mkt2.bin"))
    lo, hi = 1756659600000, 1761930000000       # 2025-09-01 .. 2025-11-01 +07
    s1, s2 = set(t1[(t1 >= lo) & (t1 < hi)].tolist()), set(t2[(t2 >= lo) & (t2 < hi)].tolist())
    com = s1 & s2
    d1 = dict(zip(t1.tolist(), v1.tolist())); d2 = dict(zip(t2.tolist(), v2.tolist()))
    RES["market_run1_vs_run2"] = dict(n1=len(s1), n2=len(s2), common=len(com), only1=len(s1 - s2), only2=len(s2 - s1),
                                      val_equal_common=float(np.mean([d1[t] == d2[t] for t in com])) if com else None,
                                      minutes_window=int((hi - lo) // 60000))
    log.info("market %s", RES["market_run1_vs_run2"])
    G1, G2, G3 = (load_gate(f(DET, "g%d/*.csv*" % i)) for i in (1, 2, 3))
    GD = load_gate(GA.STORE)
    RES["gate_g1_vs_g2_same_input"] = cmp_gate(G1, G2)
    RES["gate_g1_vs_g3_start_earlier"] = cmp_gate(G1, G3)
    RES["gate_g1_vs_dev"] = cmp_gate(G1, GD)
    if D1X != "-" and f(D1X, "g1/*.csv*"):
        RES["gate_d1x_vs_dev"] = cmp_gate(load_gate(f(D1X, "g1/*.csv*")), GD)
    for k in [k for k in RES if k.startswith("gate")]:
        log.info("%s %s", k, RES[k])
    T1, T2 = load_t1(f(DET, "t1/*.t1c*")), load_t1(f(DET, "t2/*.t1c*"))
    TD = load_t1(os.path.join(G.T1_DIR, "features_20251001_to_20260101*"))
    RES["tool1_t1_vs_t2"] = cmp_t1(T1, T2)
    RES["tool1_t1_vs_dev"] = cmp_t1(T1, TD)
    if D1X != "-" and f(D1X, "t1/*.t1c*"):
        RES["tool1_d1x_vs_dev"] = cmp_t1(load_t1(f(D1X, "t1/*.t1c*")), TD)
    del T1, T2, TD
    for k in [k for k in RES if k.startswith("tool1")]:
        log.info("%s %s", k, RES[k])
    L1, L2 = load_lab(glob.glob(os.path.join(DET, "l1/*.pb"))), load_lab(glob.glob(os.path.join(DET, "l2/*.pb")))
    LD = load_lab(["/home/ubuntu/ds_label15m/funding_label_20251001_to_20260101.pb"])
    RES["label_l1_vs_l2"] = cmp_lab(L1, L2)
    RES["label_l1_vs_dev"] = cmp_lab(L1, LD)
    if D1X != "-" and glob.glob(os.path.join(D1X, "l1/*.pb")):
        RES["label_d1x_vs_dev"] = cmp_lab(load_lab(glob.glob(os.path.join(D1X, "l1/*.pb"))), LD)
    for k in [k for k in RES if k.startswith("label")]:
        log.info("%s %s", k, RES[k])
    json.dump(RES, open(OUT, "w"), indent=1, default=str)


if __name__ == "__main__":
    main()
