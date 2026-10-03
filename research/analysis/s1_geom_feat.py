#!/usr/bin/env python3
"""S1_FEAT_GEOM — feature (pre-reg docs/prereg/PREREG_S1_FEAT_GEOM.md muc 2-3).
Stage keep9 : chay lai builder co san research/pipeline/x1/x1_feat_v2_build.py (X1_NAME=feat_v2_x1, X1_T_END=2026-01-01),
              CHI doi thu muc ra + luu (ts,sym,KEEP9)->float32; cong tai lap vs ~/s1hpo/kaggle_ds/feat_v2_x1_keep9.parquet
              (tap (ts,sym) trung het + byte-identical tren 1M dong mau rng 20260905). FAIL => exit 3.
Stage geom  : 9 GEOM + noise tu OHLCV_1H_v2.bin, ghep vao dong (ts,sym) cua keep9 -> WK/kds/geom_x1.parquet. Kiem unit/causality/range.
Stage dsup  : tao Kaggle dataset s1-geom-x1-20261003.
"""
import hashlib, json, logging, os, subprocess, sys, time
import numpy as np
import pandas as pd
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout)
log = logging.getLogger("geom_feat")
REPO = "/home/ubuntu/src/BinanceFuturesJava"
BUILDER = os.path.join(REPO, "research/pipeline/x1/x1_feat_v2_build.py")
WK = "/home/ubuntu/claude_master/1003/geom"
KEEP9_PQ = "/home/ubuntu/s1hpo/kaggle_ds/feat_v2_x1_keep9.parquet"
KEEP9_MD5 = "1aa3b97490cb68d6ce654051184eae7c"
OHLCV = "/home/ubuntu/java/fsrun/OHLCV_1H_v2.bin"
LEDGER_LITE = "/home/ubuntu/s1hpo/kaggle_ds/cand_dev_x1_lite.parquet"
KEEP9 = ["vol_7d", "dd_7d", "rk_dd_7d", "hrs_since_high_7d", "ret_3d", "rk_ret_3d", "ret_14d", "ls_global", "rk_oi_delta24h"]
GEOM = ["pos24", "pos7d", "dist_high24", "dist_low24", "atr_ratio", "range7d", "rk_pos24", "rk_dist_low24", "rk_atr_ratio"]
H = 3600000
SEED = 20260905
DS = "s1-geom-x1-20261003"
KAG = "/home/ubuntu/envs/xgb-env/bin/kaggle"
DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("o", ">f4"), ("h", ">f4"), ("l", ">f4"), ("c", ">f4"), ("qv", ">f4")])


def md5f(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def _save_keep9(long, path):
    out = long[["ts", "sym"] + KEEP9].copy()
    for c in KEEP9:
        if out[c].dtype == np.float64:
            out[c] = out[c].astype(np.float32)   # nhu s1hpo/kaggle_ds/make_reduced.py
    out.to_parquet(path, index=False)


def keep9():
    os.environ["X1_NAME"] = "feat_v2_x1"
    os.environ["X1_T_END"] = "1767225600000"
    rb = WK + "/rebuild"
    os.makedirs(rb, exist_ok=True)
    src = open(BUILDER).read()
    a, b = 'OUT="/home/ubuntu/featv2"', 'long.to_parquet(f"{OUT}/{NAME}.parquet",index=False)'
    assert src.count(a) == 1 and src.count(b) == 1, "builder da doi — khong patch duoc"
    src = src.replace(a, 'OUT="%s"' % rb).replace(b, '_save_keep9(long, f"{OUT}/{NAME}.parquet")')
    t0 = time.time()
    if not os.path.exists(rb + "/feat_v2_x1.parquet"):
        g = {"__name__": "__main__", "_save_keep9": _save_keep9}
        exec(compile(src, BUILDER, "exec"), g)
        del g
    log.info("builder xong %.0fs", time.time() - t0)
    gate(rb + "/feat_v2_x1.parquet")


def gate(newp):
    assert md5f(KEEP9_PQ) == KEEP9_MD5, "keep9 parquet goc da doi"
    N = pd.read_parquet(newp)
    O = pd.read_parquet(KEEP9_PQ)
    res = dict(n_new=int(len(N)), n_orig=int(len(O)), dtypes_new={k: str(v) for k, v in N.dtypes.items()},
               dtypes_orig={k: str(v) for k, v in O.dtypes.items()})
    same_keys = len(N) == len(O) and np.array_equal(N.ts.to_numpy(), O.ts.to_numpy()) and np.array_equal(
        N.sym.to_numpy(), O.sym.to_numpy())
    res["keys_identical"] = bool(same_keys)
    rng = np.random.default_rng(SEED)
    ok = same_keys and res["dtypes_new"] == res["dtypes_orig"]
    if same_keys:
        idx = np.sort(rng.choice(len(O), 1_000_000, replace=False))
        mis, mis_all = {}, {}
        for c in KEEP9:
            a = np.ascontiguousarray(N[c].to_numpy(np.float32))
            o = np.ascontiguousarray(O[c].to_numpy(np.float32))
            mis[c] = int((a[idx].view(np.uint32) != o[idx].view(np.uint32)).sum())
            mis_all[c] = int((a.view(np.uint32) != o.view(np.uint32)).sum())
        res["mismatch_1M"], res["mismatch_full_info"] = mis, mis_all
        ok = ok and sum(mis.values()) == 0
    res["PASS"] = bool(ok)
    json.dump(res, open(WK + "/gate_keep9.json", "w"), indent=1)
    log.info("GATE_KEEP9 %s %s", "PASS" if ok else "*** FAIL ***", json.dumps(res))
    if not ok:
        sys.exit(3)


def geom_mats(Hm, Lm, Cm):
    """Ma tran gio x sym (float64, gio thieu = NaN). Rolling tren truc thoi gian, cua so ket thuc tai hang hien tai."""
    def roll(M, n, f):
        return getattr(pd.DataFrame(M).rolling(n, min_periods=n // 2), f)().to_numpy()
    h24, l24 = roll(Hm, 24, "max"), roll(Lm, 24, "min")
    h7, l7 = roll(Hm, 168, "max"), roll(Lm, 168, "min")
    Cp = np.vstack([np.full((1, Cm.shape[1]), np.nan), Cm[:-1]])
    with np.errstate(all="ignore"):
        TR = np.fmax(Hm - Lm, np.fmax(np.abs(Hm - Cp), np.abs(Lm - Cp)))
        a24, a168 = roll(TR, 24, "mean"), roll(TR, 168, "mean")
        r24, r7 = h24 - l24, h7 - l7
        F = {"pos24": np.where(r24 > 0, (Cm - l24) / r24, np.nan), "pos7d": np.where(r7 > 0, (Cm - l7) / r7, np.nan),
             "dist_high24": Cm / h24 - 1, "dist_low24": Cm / l24 - 1,
             "atr_ratio": np.where(a168 > 0, a24 / a168, np.nan), "range7d": r7 / Cm}
    for k in F:
        F[k][~np.isfinite(F[k])] = np.nan
    for src, nm in (("pos24", "rk_pos24"), ("dist_low24", "rk_dist_low24"), ("atr_ratio", "rk_atr_ratio")):
        F[nm] = pd.DataFrame(F[src]).rank(axis=1, pct=True).to_numpy()
    return F


def unit_tests():
    n = 400
    c = 100 + np.arange(n, dtype=float)
    M = c[:, None]
    F = geom_mats(M, M, M)
    t = []
    t.append(abs(F["pos24"][-1, 0] - 1) < 1e-12 and abs(F["dist_high24"][-1, 0]) < 1e-12)
    t.append(abs(F["dist_low24"][-1, 0] - (c[-1] / c[-24] - 1)) < 1e-12)
    t.append(abs(F["range7d"][-1, 0] - (c[-1] - c[-168]) / c[-1]) < 1e-12)
    t.append(abs(F["atr_ratio"][-1, 0] - 1) < 1e-12)   # TR = 1 moi gio (|H - Cprev| = 1)
    hh, ll = c[:, None] + 2, c[:, None] - 2
    F2 = geom_mats(hh, ll, M)
    t.append(abs(F2["pos24"][-1, 0] - (c[-1] - (c[-24] - 2)) / ((c[-1] + 2) - (c[-24] - 2))) < 1e-12)
    t.append(abs(F2["atr_ratio"][-1, 0] - 1) < 1e-12)  # TR = max(4, 3, 5) = 5 deu
    log.info("UNIT %s", t)
    assert all(t), "unit test GEOM FAIL"


def causality(Hm, Lm, Cm, F, n=200):
    """Cat chuoi tai t (chi hang <= t cua 1 sym), tinh lai bang numpy thuan -> so voi bang (float64)."""
    rs = np.random.default_rng(7)
    valid = np.argwhere(np.isfinite(Cm))
    valid = valid[valid[:, 0] >= 400]
    pick = valid[rs.choice(len(valid), n, replace=False)]
    bad = 0

    def win(x, k, mp, f):
        w = x[-k:]
        return f(w) if np.isfinite(w).sum() >= mp else np.nan
    for i, j in pick:
        h, l, c = Hm[:i + 1, j], Lm[:i + 1, j], Cm[:i + 1, j]
        h24, l24 = win(h, 24, 12, np.nanmax), win(l, 24, 12, np.nanmin)
        h7, l7 = win(h, 168, 84, np.nanmax), win(l, 168, 84, np.nanmin)
        cp = np.concatenate([[np.nan], c[:-1]])
        with np.errstate(all="ignore"):
            tr = np.fmax(h - l, np.fmax(np.abs(h - cp), np.abs(l - cp)))
            a24, a168 = win(tr, 24, 12, np.nanmean), win(tr, 168, 84, np.nanmean)
            ref = {"pos24": (c[-1] - l24) / (h24 - l24) if h24 > l24 else np.nan,
                   "dist_low24": c[-1] / l24 - 1, "range7d": (h7 - l7) / c[-1],
                   "atr_ratio": a24 / a168 if a168 > 0 else np.nan, "pos7d": (c[-1] - l7) / (h7 - l7) if h7 > l7 else np.nan}
        for k, v in ref.items():
            g = F[k][i, j]
            if not (np.isnan(v) and np.isnan(g)) and not np.isclose(v, g, rtol=1e-9, atol=1e-12):
                bad += 1
                log.info("  MISMATCH %s i=%d j=%d ref=%r got=%r", k, i, j, v, g)
    log.info("CAUSALITY %d mau x 5 feature: mismatch %d", n, bad)
    return bad


def geom():
    unit_tests()
    b = np.fromfile(OHLCV, dtype=DT)
    ts = b["ts"].astype(np.int64)
    sid = b["sym"].astype(np.int64)
    t0, nh = ts.min(), (ts.max() - ts.min()) // H + 1
    syms = np.unique(sid)
    hi, ci = (ts - t0) // H, np.searchsorted(syms, sid)

    def mat(f):
        M = np.full((nh, len(syms)), np.nan)
        M[hi, ci] = b[f].astype(np.float64)
        return M
    Hm, Lm, Cm = mat("h"), mat("l"), mat("c")
    del b
    log.info("grid %d gio x %d sym", nh, len(syms))
    F = geom_mats(Hm, Lm, Cm)
    bad = causality(Hm, Lm, Cm, F)
    rng_chk = dict(pos24=bool(np.nanmin(F["pos24"]) >= 0 and np.nanmax(F["pos24"]) <= 1),
                   pos7d=bool(np.nanmin(F["pos7d"]) >= 0 and np.nanmax(F["pos7d"]) <= 1),
                   dist_high24=bool(np.nanmax(F["dist_high24"]) <= 1e-7), dist_low24=bool(np.nanmin(F["dist_low24"]) >= -1e-7),
                   rk=bool(all(np.nanmin(F[k]) > 0 and np.nanmax(F[k]) <= 1 for k in GEOM if k.startswith("rk_"))),
                   atr=bool(np.nanmin(F["atr_ratio"]) > 0), range7d=bool(np.nanmin(F["range7d"]) >= 0))
    log.info("RANGE %s", rng_chk)
    assert bad == 0 and all(rng_chk.values()), "GEOM check FAIL"
    del Hm, Lm, Cm
    K = pd.read_parquet(KEEP9_PQ, columns=["ts", "sym"])
    kt, ks_ = K.ts.to_numpy(np.int64), K.sym.to_numpy(np.int64)
    kh = (kt - t0) // H
    kc = np.clip(np.searchsorted(syms, ks_), 0, len(syms) - 1)
    ok = (kt >= t0) & (kh < nh) & ((kt - t0) % H == 0) & (syms[kc] == ks_)
    out = K.copy()
    for k in GEOM:
        v = np.full(len(K), np.nan, np.float32)
        v[ok] = F[k][kh[ok], kc[ok]].astype(np.float32)
        out[k] = v
        del F[k]
    out["noise"] = np.random.default_rng(SEED).standard_normal(len(K)).astype(np.float32)
    os.makedirs(WK + "/kds", exist_ok=True)
    fp = WK + "/kds/geom_x1.parquet"
    out.to_parquet(fp, index=False)
    Ld = pd.read_parquet(LEDGER_LITE)
    Ld = Ld[Ld.g1lite.notna()]
    Ld["ts"] = (Ld.ts // H) * H
    J = Ld[["ts", "sym"]].merge(out, on=["ts", "sym"], how="left")
    meta = dict(path=fp, md5=md5f(fp), n=int(len(out)), keys_in_store=float(ok.mean()),
                cov_keep9_rows={k: float(out[k].notna().mean()) for k in GEOM},
                cov_ledger_rows={k: float(J[k].notna().mean()) for k in GEOM}, n_ledger=int(len(J)),
                causality_mismatch=bad, range=rng_chk, ohlcv_md5=md5f(OHLCV),
                desc={k: [float(x) for x in np.nanquantile(out[k].to_numpy(), [0.01, 0.5, 0.99])] for k in GEOM + ["noise"]})
    json.dump(meta, open(WK + "/geom_meta.json", "w"), indent=1)
    log.info("GEOM_OK %s", json.dumps(meta))


def dsup():
    kd = WK + "/kds"
    json.dump({"title": DS, "id": "chuyendinh/" + DS, "licenses": [{"name": "CC0-1.0"}]}, open(kd + "/dataset-metadata.json", "w"))
    r = subprocess.run([KAG, "datasets", "create", "-p", kd], capture_output=True, text=True)
    log.info("dsup rc %d %s %s", r.returncode, r.stdout[-1500:], r.stderr[-800:])


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    {"keep9": keep9, "geom": geom, "dsup": dsup}.get(cmd, lambda: sys.exit(__doc__))()
