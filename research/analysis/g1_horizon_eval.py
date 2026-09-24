"""G1_HORIZON — cham diem giai doan 1: G72 vs G4_repro tren OOS DEV.

Theo docs/prereg/PREREG_G1.md muc 4-6. CHI DEV. Khong sim, khong VAL, khong GPU.
usage: python3 g1_horizon_eval.py <dirA> <dirB>   (A = G4_repro, B = G72)
Moi dir phai co pred_pool.npy thang hang voi pool_dev.parquet.
"""
import glob
import json
import logging
import os
import sys

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                    stream=sys.stdout)
log = logging.getLogger("g1eval")
sys.path.insert(0, "/home/ubuntu/sel1m_code")
import funding_label_pb as FLPB  # noqa: E402
from scipy.stats import rankdata  # noqa: E402

POOL = "/home/ubuntu/g015/pool/pool_dev.parquet"
LB_DIR = "/home/ubuntu/label_15m"
MAP_CSV = "/home/ubuntu/claudedata/oi/symbol_map.csv"
H_LAB, WIN_LAB, NEED_LAB = 72, 0.07, 288
BLOCK_MS = 72 * 3_600_000
NBOOT, SEED, FWIDE = 2000, 20260906, 1.21
NBIN = 4096


def load_y72(ts, sym):
    """Y72 = 1[maxFav_72h >= 0.07] join vao (ts,sym) cua pool. -1 = khong co nhan."""
    smap = pd.read_csv(MAP_CSV)
    s2i = dict(zip(smap.symbol, smap.symId.astype(np.int64)))
    key = ts * 1024 + sym
    srt = np.argsort(key, kind="stable")
    ks = key[srt]
    assert not np.any(np.diff(ks) == 0), "pool trung (ts,sym)"
    y = np.full(len(ts), -1, dtype=np.int8)
    lo, hi = int(ts.min()), int(ts.max())
    fs = sorted(glob.glob(LB_DIR + "/funding_label_202[1-4]*.pb"))
    fs = [f for f in fs if os.path.basename(f).split("_")[2] < "20240701"]
    cf, cn = "maxFav_%dh" % H_LAB, "nBars_%dh" % H_LAB
    nhit = 0
    for fp in fs:
        d = FLPB.read_label(fp, usecols=["tEpochMs", "symbol", cf, cn])
        d = d[(d[cn] >= NEED_LAB) & d[cf].notna()]
        sid = d.symbol.map(s2i)
        m = sid.notna().to_numpy()
        t = d.tEpochMs.to_numpy(np.int64)[m]
        k = (t >= lo) & (t <= hi)
        if not k.any():
            del d
            continue
        kl = t[k] * 1024 + sid[m].to_numpy(np.int64)[k]
        yv = (d[cf].to_numpy(np.float64)[m][k] >= WIN_LAB).astype(np.int8)
        ip = np.clip(np.searchsorted(ks, kl), 0, len(ks) - 1)
        h = ks[ip] == kl
        y[srt[ip[h]]] = yv[h]
        nhit += int(h.sum())
        del d
    log.info("join nhan: %d dong pool co Y72 (%.4f), tong khop %d",
             int((y >= 0).sum()), float((y >= 0).mean()), nhit)
    return y


def auc_exact(p, y):
    r = rankdata(p)
    npos = float(y.sum())
    nneg = float(len(y) - npos)
    return float((r[y == 1].sum() - npos * (npos + 1) / 2.0) / (npos * nneg))


def bin_counts(b, y, blk, nblk):
    """Ma tran dem (nblk, NBIN, 2) theo khoi 72h."""
    idx = (blk.astype(np.int64) * NBIN + b.astype(np.int64)) * 2 + y.astype(np.int64)
    c = np.bincount(idx, minlength=nblk * NBIN * 2).astype(np.float32)
    return c.reshape(nblk, NBIN * 2)


def auc_from_counts(v):
    """v shape (R, NBIN*2) -> AUC moi hang (Mann-Whitney, ties xu ly 0.5 trong bin)."""
    w = v.reshape(-1, NBIN, 2)
    cn, cp = w[:, :, 0], w[:, :, 1]
    cum = np.cumsum(cn, axis=1) - cn
    num = (cp * (cum + 0.5 * cn)).sum(axis=1)
    return num / (cp.sum(axis=1) * cn.sum(axis=1))


def blk_stats(x, y, blk, nblk):
    """Thong ke du Pearson theo khoi -> (nblk, 6): n, Sx, Sy, Sxx, Syy, Sxy."""
    o = np.empty((nblk, 6), dtype=np.float64)
    o[:, 0] = np.bincount(blk, minlength=nblk)
    o[:, 1] = np.bincount(blk, weights=x, minlength=nblk)
    o[:, 2] = np.bincount(blk, weights=y, minlength=nblk)
    o[:, 3] = np.bincount(blk, weights=x * x, minlength=nblk)
    o[:, 4] = np.bincount(blk, weights=y * y, minlength=nblk)
    o[:, 5] = np.bincount(blk, weights=x * y, minlength=nblk)
    return o


def pearson_from_stats(s):
    n, sx, sy, sxx, syy, sxy = [s[..., i] for i in range(6)]
    cov = sxy / n - (sx / n) * (sy / n)
    vx = sxx / n - (sx / n) ** 2
    vy = syy / n - (sy / n) ** 2
    return cov / np.sqrt(vx * vy)


def ci(v, pt):
    lo, hi = np.percentile(v, [2.5, 97.5])
    return float(pt - FWIDE * (pt - lo)), float(pt + FWIDE * (hi - pt)), float(v.std(ddof=1))


def main():
    dA, dB = sys.argv[1], sys.argv[2]
    pool = pd.read_parquet(POOL, columns=["ts", "sym", "g1lite"])
    ts = pool.ts.to_numpy(np.int64)
    sym = pool.sym.to_numpy(np.int64)
    g1 = pool.g1lite.to_numpy(np.float64)
    del pool
    pA = np.load(dA + "/pred_pool.npy").astype(np.float64)
    pB = np.load(dB + "/pred_pool.npy").astype(np.float64)
    assert len(pA) == len(ts) and len(pB) == len(ts), "pred khong thang hang pool"
    log.info("pool %d dong | A=%s B=%s", len(ts), dA, dB)
    y = load_y72(ts, sym)
    m = (y >= 0) & np.isfinite(g1) & np.isfinite(pA) & np.isfinite(pB)
    log.info("giu %d/%d dong (%.4f)", int(m.sum()), len(m), float(m.mean()))
    ts, g1, pA, pB = ts[m], g1[m], pA[m], pB[m]
    y = y[m].astype(np.int64)
    blk = ((ts - ts.min()) // BLOCK_MS).astype(np.int64)
    nblk = int(blk.max()) + 1
    log.info("n=%d  base(Y72)=%.4f  nblk72h=%d", len(y), float(y.mean()), nblk)

    edges = np.quantile(np.concatenate([pA, pB]), np.linspace(0, 1, NBIN + 1)[1:-1])
    cA = bin_counts(np.searchsorted(edges, pA, side="right"), y, blk, nblk)
    cB = bin_counts(np.searchsorted(edges, pB, side="right"), y, blk, nblk)
    del edges

    aucA, aucB = auc_exact(pA, y), auc_exact(pB, y)
    aucAb = float(auc_from_counts(cA.sum(axis=0, keepdims=True))[0])
    aucBb = float(auc_from_counts(cB.sum(axis=0, keepdims=True))[0])
    log.info("AUC chinh xac A=%.6f B=%.6f | binned A=%.6f B=%.6f | sai so binning %.2e / %.2e",
             aucA, aucB, aucAb, aucBb, abs(aucA - aucAb), abs(aucB - aucBb))

    rA, rB = rankdata(pA), rankdata(pB)
    del pA, pB
    rY, rG = rankdata(y), rankdata(g1)
    del g1
    S = {"AY": blk_stats(rA, rY, blk, nblk), "BY": blk_stats(rB, rY, blk, nblk),
         "AG": blk_stats(rA, rG, blk, nblk), "BG": blk_stats(rB, rG, blk, nblk)}
    del rA, rB, rY, rG
    pt = {k: float(pearson_from_stats(v.sum(axis=0))) for k, v in S.items()}
    log.info("spearman(pt): A-Y72=%.6f B-Y72=%.6f | A-g1lite=%.6f B-g1lite=%.6f",
             pt["AY"], pt["BY"], pt["AG"], pt["BG"])

    rng = np.random.default_rng(SEED)
    M = np.zeros((NBOOT, nblk), dtype=np.float32)
    for i in range(NBOOT):
        M[i] = np.bincount(rng.integers(0, nblk, nblk), minlength=nblk)
    bA = auc_from_counts(M @ cA)
    bB = auc_from_counts(M @ cB)
    del cA, cB
    bs = {k: pearson_from_stats(M.astype(np.float64) @ v) for k, v in S.items()}

    out = {"n": int(len(y)), "nblk": nblk, "base_y72": float(y.mean()),
           "nboot": NBOOT, "seed": SEED, "f_wide": FWIDE, "nbin": NBIN,
           "auc_bin_err": [abs(aucA - aucAb), abs(aucB - aucBb)], "rows": {}}

    def emit(tag, ptv, bv):
        lo, hi, sd = ci(bv, ptv)
        out["rows"][tag] = {"pt": ptv, "lo": lo, "hi": hi, "sd_boot": sd}
        log.info("%-18s pt=%+.6f CI95x1.21=[%+.6f, %+.6f] sd_boot=%.6f",
                 tag, ptv, lo, hi, sd)

    emit("AUC_A_Y72", aucA, bA)
    emit("AUC_B_Y72", aucB, bB)
    emit("d_AUC_B-A", aucB - aucA, bB - bA)
    emit("SP_A_Y72", pt["AY"], bs["AY"])
    emit("SP_B_Y72", pt["BY"], bs["BY"])
    emit("d_SP_Y72_B-A", pt["BY"] - pt["AY"], bs["BY"] - bs["AY"])
    emit("SP_A_g1lite", pt["AG"], bs["AG"])
    emit("SP_B_g1lite", pt["BG"], bs["BG"])
    emit("d_SP_g1_B-A", pt["BG"] - pt["AG"], bs["BG"] - bs["AG"])

    r = out["rows"]["d_AUC_B-A"]
    gate = bool(aucB > aucA and (r["lo"] > 0 or r["hi"] < 0))
    out["gate_pass"] = gate
    out["p_dpos"] = float((bB - bA > 0).mean())
    log.info("P(d_AUC>0)=%.4f", out["p_dpos"])
    log.info("CONG GO/NO-GO: %s", "PASS" if gate else "FAIL (null, dung, khong chay sim)")
    json.dump(out, open("/home/ubuntu/g72/g1_eval.json", "w"), indent=1)
    log.info("-> /home/ubuntu/g72/g1_eval.json")


if __name__ == "__main__":
    main()
