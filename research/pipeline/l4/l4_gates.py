#!/usr/bin/env python3
"""L4 — CHAM CONG REPLAY. Doc output cua L4ReplayHarness roi so voi bins.

REF: `symbolPred` chuan cua sim = 1 - p0(predwf_map_s1a2_x1)  (WfoDataset:248 DAO DAU).
"""
import os, sys, logging
import numpy as np, pandas as pd
from scipy.stats import spearmanr
logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("l4g")
D = os.environ.get("L4_OUT", "/home/ubuntu/l4")
ROW = np.dtype([("ts", ">i8"), ("symId", ">i4"), ("hasScore", ">i4"),
                ("pwin", ">f4"), ("pmap", ">f4"), ("s1", ">f4")])
OUT = np.dtype([("ts", ">i8"), ("symId", ">i4"), ("rank", ">i4"),
                ("pred", ">f4"), ("pmapBins", ">f4")])
TOPK = 8


def stat(name, a, b):
    m = np.isfinite(a) & np.isfinite(b)
    sp = spearmanr(a[m], b[m]).correlation
    d = np.abs(a[m].astype(np.float64) - b[m].astype(np.float64))
    log.info("  %-34s n=%d spearman=%.6f max|d|=%.3e med|d|=%.3e", name, m.sum(), sp, d.max(),
             np.median(d))
    return sp, d.max()


def topk_overlap(df, ca, cb, k=TOPK):
    """Ty le trung tap top-k MOI TICK (k coin symbolPred THAP nhat = sim chon)."""
    hit = tot = 0
    per = []
    for _, g in df.groupby("ts"):
        A = set(g.nsmallest(k, ca).symId)
        B = set(g.nsmallest(k, cb).symId)
        hit += len(A & B); tot += len(B); per.append(len(A & B) / float(len(B)))
    return hit / float(tot), float(np.mean(per)), len(per)


def multiset_gap(df, ca, cb):
    mx = 0.0
    for _, g in df.groupby("ts"):
        a = np.sort(g[ca].to_numpy(np.float64)); b = np.sort(g[cb].to_numpy(np.float64))
        mx = max(mx, float(np.abs(a - b).max()))
    return mx


def main():
    r = np.fromfile(os.path.join(D, "rows.bin"), dtype=ROW)
    base = pd.DataFrame({k: np.asarray(r[k]).astype(
        np.int64 if r[k].dtype.kind == "i" else np.float64) for k in ROW.names})
    base["ref"] = (np.float32(1.0) - base.pmap.to_numpy(np.float32)).astype(np.float64)
    n = len(base)
    log.info("REPLAY: %d dong | %d tick | %d coin | hasScore=%.4f",
             n, base.ts.nunique(), base.symId.nunique(), base.hasScore.mean())
    log.info("LECH VU TRU: dong KHONG co score S1 (build_map giu nguyen p) = %d (%.2f%%)",
             int((base.hasScore == 0).sum()), 100.0 * (base.hasScore == 0).mean())

    pj = os.path.join(D, "pwin_java.f32")
    if os.path.exists(pj):
        log.info("\n== CONG A: net015 ONNX trong JAVA vs bins predwf_G015x26 (P(win)) ==")
        pw = np.fromfile(pj, dtype=">f4").astype(np.float64)
        stat("pwin_java vs pwin_bins", pw, base.pwin.to_numpy(np.float64))
        sj = np.fromfile(os.path.join(D, "s1_java.f32"), dtype=">f4").astype(np.float64)
        m = base.hasScore.to_numpy() == 1
        log.info("\n== CONG A2: S1 ONNX trong JAVA vs pred_s1a2x1.parquet (score) ==")
        stat("s1_java vs s1_parquet", sj[m], base.s1.to_numpy(np.float64)[m])

    for tag in ("MAPONLY", "E2E"):
        f = os.path.join(D, "out_%s.bin" % tag)
        if not os.path.exists(f):
            log.info("\n(thieu %s)", f); continue
        o = np.fromfile(f, dtype=OUT)
        assert len(o) == n
        assert (np.asarray(o["ts"]).astype(np.int64) == base.ts.to_numpy()).all()
        assert (np.asarray(o["symId"]).astype(np.int64) == base.symId.to_numpy()).all()
        df = base.copy()
        df["live"] = np.asarray(o["pred"]).astype(np.float64)
        df["rank"] = np.asarray(o["rank"]).astype(np.int64)
        log.info("\n================ ARM %s ================", tag)
        sub = df[df.hasScore == 1]
        stat("symbolPred_live vs bins (co score)", sub.live.to_numpy(), sub.ref.to_numpy())
        stat("symbolPred_live vs bins (TOAN BO)", df.live.to_numpy(), df.ref.to_numpy())
        sp_t = []
        for _, g in sub.groupby("ts"):
            sp_t.append(spearmanr(g.live, g.ref).correlation)
        log.info("  spearman PER-TICK: min=%.6f  p05=%.6f  trung binh=%.6f  (%d tick)",
                 np.min(sp_t), np.percentile(sp_t, 5), np.mean(sp_t), len(sp_t))
        ov, per, nt = topk_overlap(df, "live", "ref")
        log.info("  top-%d trung (toan tick): %.4f%%  (trung binh/tick %.4f%%, %d tick)",
                 TOPK, 100 * ov, 100 * per, nt)
        ovs, pers, _ = topk_overlap(sub, "live", "ref")
        log.info("  top-%d trung (chi coin co score): %.4f%%  (tb/tick %.4f%%)", TOPK, 100 * ovs,
                 100 * pers)
        log.info("  multiset per-tick max|d| (co score) = %.3e", multiset_gap(sub, "live", "ref"))
        q = np.percentile(df.live, [10, 50, 90])
        qb = np.percentile(df.ref, [10, 50, 90])
        log.info("  symbolPred p10/50/90 live = %.4f / %.4f / %.4f", *q)
        log.info("  symbolPred p10/50/90 bins = %.4f / %.4f / %.4f", *qb)
        t8l = np.concatenate([g.nsmallest(TOPK, "live").live.to_numpy() for _, g in df.groupby("ts")])
        t8b = np.concatenate([g.nsmallest(TOPK, "ref").ref.to_numpy() for _, g in df.groupby("ts")])
        log.info("  [DAI x26] symbolPred cua TOP-%d/tick  live p10/50/90 = %.4f / %.4f / %.4f",
                 TOPK, *np.percentile(t8l, [10, 50, 90]))
        log.info("  [DAI x26] symbolPred cua TOP-%d/tick  bins p10/50/90 = %.4f / %.4f / %.4f",
                 TOPK, *np.percentile(t8b, [10, 50, 90]))


if __name__ == "__main__":
    main()
