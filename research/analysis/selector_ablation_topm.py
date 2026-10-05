#!/usr/bin/env python3
"""SELECTOR_ABLATION_R50 — sinh bins selector R<M>s<seed>: hoan vi bo-4 (p0..p3) CHI trong top-M cua moi ts.

Pre-reg: docs/prereg/PREREG_SELECTOR_ABLATION_R50.md. KHONG sua .java.
Thu tu DUNG nhu sim: score = float32(1) - float32(p0) (WfoDataset.buildFundingFromWfFiles:248, s3_funding.py:92),
preprocessFundingData sort score TANG; selectCands lay K=16 phan tu dau; BIG_DOWN (getTopSymbolArray) duyet TreeMap
score TANG => "top-M" = M dong score THAP nhat = p0 (P(win)) CAO nhat trong ts (the: thu tu record). Dong p0 NaN
(sim bo) khong co hang, giu nguyen. Ngoai top-M: byte-identical. Tap coin top-M moi ts GIU NGUYEN, chi thu tu trong
top-M bi xao => top-16 PREDICT (va coin BIG_DOWN) = tap con NGAU NHIEN cua top-M cua B0.
Kernel goi SAS.src_files / SAS.sha256_concat / SAS.gen_arm (module nay duoc import duoi ten SAS) — sha phai trung Oracle.

Lenh (Oracle): gen [--arm A] --out DIR ; sanity --out DIR
"""
import argparse
import json
import logging
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import selector_ablation_scores as S  # noqa: E402
from selector_ablation_scores import read_rec, sha256_concat, src_files  # noqa: E402,F401

log = logging.getLogger("sel_abl_topm")
ARMS_M = {"R50s42": (50, 42), "R50s7": (50, 7), "R100s42": (100, 42), "R100s7": (100, 7)}
SRC = S.SRC
SHA_P0 = S.SHA_P0
CACHE = "/home/ubuntu/claude_master/1003/sa50"


def rank_in_ts(a):
    """Hang 0.. trong moi ts theo score = float32(1) - p0 TANG (the: thu tu record); dong NaN -> -1."""
    ts = a["ts"].astype(np.int64)
    p0 = a["p0"].astype(np.float32)
    ok = np.isfinite(p0)
    sc = np.where(ok, (np.float32(1.0) - p0).astype(np.float64), np.inf)
    idx = np.arange(len(a))
    o = np.lexsort((idx, sc, ~ok, ts))
    tso = ts[o]
    start = np.r_[0, np.flatnonzero(np.diff(tso)) + 1]
    gs = np.repeat(start, np.diff(np.r_[start, len(tso)]))
    r = np.empty(len(a), dtype=np.int64)
    r[o] = np.arange(len(a)) - gs
    r[~ok] = -1
    return r


def transform_topm(a, M, rng):
    """Hoan vi ngau nhien bo-4 gia tri giua cac dong top-M CUNG ts; dong khac giu nguyen."""
    ts = a["ts"].astype(np.int64)
    idx = np.arange(len(a))
    r = rank_in_ts(a)
    top = (r >= 0) & (r < M)
    key = np.where(top, ts, -1 - idx)            # dong ngoai top-M: khoa rieng => tu anh xa ve chinh no
    u = rng.random(len(a))                       # luon rut du n so => tat dinh theo file
    src = np.lexsort((u, key))
    dst = np.lexsort((idx, key))
    return S.permute_rows(a, src, dst)


def gen_arm(arm, files, out_dir, liq_dir=None):
    """Sinh 18 file cho arm vao out_dir. Tra (sha256_concat, list path). liq_dir bo qua (giu chu ky SA_BLOCK)."""
    M, seed = ARMS_M[arm]
    os.makedirs(out_dir, exist_ok=True)
    rng = np.random.default_rng(seed)
    outs = []
    for f in files:
        b = transform_topm(read_rec(f), M, rng)
        o = os.path.join(out_dir, os.path.basename(f))
        b.tofile(o)
        outs.append(o)
    sha = sha256_concat(outs)
    log.info("GEN arm=%s M=%d seed=%d files=%d sha256=%s -> %s", arm, M, seed, len(outs), sha, out_dir)
    return sha, outs


def _sorted_bytes(x):
    o = np.lexsort((x["p3"], x["p2"], x["p1"], x["p0"], x["ts"]))
    y = x[o]
    return b"".join(y[c].tobytes() for c in ("ts", "p0", "p1", "p2", "p3"))


def _spearman_top(ts, x, y):
    """Spearman trung binh trong ts (nhom >= 5 dong) giua x va y — vectorized."""
    import pandas as pd
    d = pd.DataFrame({"ts": ts, "x": x, "y": y})
    g0 = d.groupby("ts")
    d["rx"] = g0["x"].rank()
    d["ry"] = g0["y"].rank()
    mx, my = g0["rx"].transform("mean"), g0["ry"].transform("mean")
    d["cxy"], d["cxx"], d["cyy"] = (d.rx - mx) * (d.ry - my), (d.rx - mx) ** 2, (d.ry - my) ** 2
    s = d.groupby("ts")[["cxy", "cxx", "cyy"]].sum()
    n = d.groupby("ts").size()
    c = s.cxy / np.sqrt(s.cxx * s.cyy)
    c = c[(n >= 5) & (s.cxx > 0) & (s.cyy > 0)]
    return float(c.mean()), int(len(c))


def _boundary_ties(a, r, M):
    """So ts co diem hang M-1 == hang M (tie dung bien top-M; tie-break theo thu tu record)."""
    import pandas as pd
    sc = (np.float32(1.0) - a["p0"].astype(np.float32))
    ts = a["ts"].astype(np.int64)
    s1 = pd.Series(sc[r == M - 1], index=ts[r == M - 1])
    s2 = pd.Series(sc[r == M], index=ts[r == M])
    j = s1.to_frame("a").join(s2.to_frame("b"), how="inner")
    return int((j.a == j.b).sum())


def _universe(files):
    import pandas as pd
    tss, ns = [], []
    for f in files:
        a = read_rec(f)
        ok = np.isfinite(a["p0"].astype(np.float32))
        t, c = np.unique(a["ts"][ok].astype(np.int64), return_counts=True)
        tss.append(t)
        ns.append(c)
    t, n = np.concatenate(tss), np.concatenate(ns)
    yr = np.asarray(pd.to_datetime(t, unit="ms").year)
    out = {}
    for y in [None] + sorted(set(yr.tolist())):
        m = np.ones(len(t), bool) if y is None else yr == y
        out["all" if y is None else str(y)] = dict(
            n_ts=int(m.sum()), q05_25_50_75_95=[int(np.percentile(n[m], q)) for q in (5, 25, 50, 75, 95)],
            pct_ts_n_le16=float(100 * (n[m] <= 16).mean()), pct_ts_n_le50=float(100 * (n[m] <= 50).mean()),
            pct_ts_n_le100=float(100 * (n[m] <= 100).mean()))
    return out


def stage_sanity(out_root, sample=("20220101", "20240701", "20251001")):
    """Kiem bins da sinh o out_root/<arm>/. Ghi CACHE/sanity.json."""
    import glob
    files = src_files(SRC)
    res = {"sha_src": sha256_concat(files), "arms": {}, "checks": {}, "universe": _universe(files)}
    res["checks"]["src_sha_eq_P0"] = res["sha_src"] == SHA_P0
    ok_all = True
    for arm, (M, seed) in ARMS_M.items():
        d = os.path.join(out_root, arm)
        outs = sorted(glob.glob(os.path.join(d, "predict_wf_*.bin")))
        r = dict(M=M, seed=seed, sha=sha256_concat(outs), files=len(outs), per_file={})
        tot = dict(n_top=0, n_top_p0_changed=0, topset_mismatch_rows=0, boundary_tie_ts=0)
        for f in files:
            nm = os.path.basename(f)
            a, b = read_rec(f), read_rec(os.path.join(d, nm))
            same_keys = bool(len(a) == len(b) and np.array_equal(a["ts"], b["ts"]) and np.array_equal(a["sym"], b["sym"]))
            same_ms = _sorted_bytes(a) == _sorted_bytes(b)
            nan_same = bool(np.array_equal(np.isnan(a["p0"].astype(float)), np.isnan(b["p0"].astype(float))))
            ra, rb = rank_in_ts(a), rank_in_ts(b)
            ta, tb = (ra >= 0) & (ra < M), (rb >= 0) & (rb < M)
            out_same = a[~ta].tobytes() == b[~ta].tobytes()
            mism = int((ta != tb).sum())
            ties = _boundary_ties(a, ra, M)
            pf = dict(n=int(len(a)), n_top=int(ta.sum()), same_keys=same_keys, same_multiset=bool(same_ms),
                      nan_pos_same=nan_same, outside_topM_byte_identical=bool(out_same), topset_mismatch_rows=mism,
                      boundary_tie_ts=ties, frac_top_p0_changed=float(np.mean(a["p0"][ta] != b["p0"][ta])))
            if nm[11:19] in sample:
                pf["spearman_top_vs_P0"], pf["n_ts"] = _spearman_top(a["ts"][ta].astype(np.int64),
                                                                     a["p0"][ta].astype(float), b["p0"][ta].astype(float))
            r["per_file"][nm] = pf
            tot["n_top"] += pf["n_top"]
            tot["n_top_p0_changed"] += int(np.sum(a["p0"][ta] != b["p0"][ta]))
            tot["topset_mismatch_rows"] += mism
            tot["boundary_tie_ts"] += ties
            ok_all &= same_keys and bool(same_ms) and nan_same and bool(out_same) and mism <= 2 * ties
        r["totals"] = tot
        res["arms"][arm] = r
        log.info("SANITY %s sha=%s files=%d totals=%s", arm, r["sha"][:16], r["files"], tot)
    res["checks"]["all_keys_multiset_nan_outside_topset"] = bool(ok_all)
    for M in (50, 100):
        nm = "predict_wf_20240701.bin"
        x = read_rec(os.path.join(out_root, "R%ds42" % M, nm))
        y = read_rec(os.path.join(out_root, "R%ds7" % M, nm))
        ra = rank_in_ts(read_rec(os.path.join(SRC[0], nm)) if os.path.exists(os.path.join(SRC[0], nm))
                        else read_rec([f for f in files if f.endswith(nm)][0]))
        t = (ra >= 0) & (ra < M)
        res["checks"]["diff_s42_s7_M%d_frac_top_p0" % M] = float(np.mean(x["p0"][t] != y["p0"][t]))
    res["checks"]["seeds_differ"] = all(res["checks"]["diff_s42_s7_M%d_frac_top_p0" % M] > 0.5 for M in (50, 100))
    shas = [res["arms"][k]["sha"] for k in ARMS_M]
    res["checks"]["sha_distinct_and_ne_P0"] = len(set(shas)) == len(shas) and SHA_P0 not in shas
    res["checks"]["files_18"] = all(res["arms"][k]["files"] == 18 for k in ARMS_M)
    res["ok"] = all(v for k, v in res["checks"].items() if not k.startswith("diff_"))
    os.makedirs(CACHE, exist_ok=True)
    json.dump(res, open(os.path.join(CACHE, "sanity.json"), "w"), indent=1)
    log.info("SANITY checks %s universe_all %s -> ok=%s", json.dumps(res["checks"]), res["universe"]["all"], res["ok"])
    return res


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["gen", "sanity"])
    ap.add_argument("--arm", choices=list(ARMS_M))
    ap.add_argument("--out", default=os.path.join(CACHE, "bins"))
    a = ap.parse_args()
    if a.cmd == "gen":
        arms = [a.arm] if a.arm else list(ARMS_M)
        shas = {"P0": SHA_P0}
        for arm in arms:
            shas[arm] = gen_arm(arm, src_files(SRC), os.path.join(a.out, arm))[0]
        json.dump(shas, open(os.path.join(a.out, "sha256.json"), "w"), indent=1)
    else:
        sys.exit(0 if stage_sanity(a.out)["ok"] else 3)


if __name__ == "__main__":
    main()
