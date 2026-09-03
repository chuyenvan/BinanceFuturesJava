"""G015CUT — train lai G015 cac bien the CAT FEATURE, CHI DEV. Xem docs/PREREG_G015CUT.md.
Khong ghi de gi cua ai; output /kaggle/working. Khong rebuild OI (chi doc file sach).
"""
import os, sys, glob, json, time, hashlib, logging
import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("g015cut")
def _find(name, want_dir=False):
    hits = sorted(glob.glob("/kaggle/input/**/" + name, recursive=True))
    assert hits, "khong thay %s trong /kaggle/input/*/" % name
    return os.path.dirname(hits[0]) if want_dir else hits[0]


sys.path.insert(0, _find("tool1_col.py", True))
from tool1_col import read_tool1
import funding_label_pb as FLPB
from scipy.stats import rankdata

SMOKE = int(os.environ.get("G015_SMOKE", "0"))
OUT = "/kaggle/working"
MM_DIR = "/kaggle/temp"
T1_DIR = _find("features_20220101_to_20220401.t1c*", True)
LB_DIR = _find("funding_label_20220101_to_20220401.pb", True)
OI_DIR = _find("oi_percoin_full.bin", True)
POOL = _find("pool_dev.parquet")
RES = OUT + "/g015cut_results.jsonl"
PRG = OUT + "/g015cut_progress.jsonl"

GRID_MIN = 15
GRID_MS = GRID_MIN * 60_000
TZ = 7 * 3_600_000
OI_TOL = 2 * 3_600_000
PURGE_MS = 288 * GRID_MS               # 72h wall-clock
H_MIN = 240                            # horizon 4h
NEED = H_MIN // GRID_MIN               # nBars_4h >= 16
WIN = 0.06
NEST = 50 if SMOKE else 400
SEED = 42
NREP = 2000
BSEED = 20260903
NCRUDE = 10 if SMOKE else 60

OI_NAMES = ["oi_delta24h", "oi_z", "ls_global", "ls_toptrader", "taker_buy"]
OI_DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("oi", ">f4", 5)])
NF = 47                                # 40 Tool1 + 5 OI + 2 cot nhieu
CUT_DATES = ["20220101", "20220401", "20220701", "20221001", "20230101",
             "20230401", "20230701", "20231001", "20240101", "20240401"]
if SMOKE:
    CUT_DATES = CUT_DATES[:2]
TS_HI = int(pd.Timestamp("2024-07-01", tz="UTC").value // 10**6) - TZ   # 2024-06-30 17:00Z
SHA_OI = "e3887f63097299655213f8382ca7e473e126ee4d7ddf69a39658942651b305ec"
# hang so gate c2b (doc tu research/analysis/gate_cfg.py, chi co can duoi)
GMM, GAMIN, GAMULT, GRMAX = 0.008, 0.26787, 1.2876, 0.15

IDX_T1 = list(range(40))
IDX_OI = list(range(40, 45))
FULL = IDX_T1 + IDX_OI


def _drop(base, rm):
    rm = set(rm)
    return [i for i in base if i not in rm]


VARIANTS = [
    ("full45", FULL),
    ("no_oi", IDX_T1),
    ("noise46_a", FULL + [45]),
    ("noise46_b", FULL + [46]),
    ("no_funding", _drop(FULL, range(17, 26))),
    ("no_basket", _drop(FULL, range(12, 17))),
    ("no_xsec", _drop(FULL, [32, 33, 34])),
    ("no_oi_no_xsec", _drop(IDX_T1, [32, 33, 34])),
    ("oi_only", IDX_OI),
]
if SMOKE:
    VARIANTS = VARIANTS[:3]
VSET = os.environ.get("G015_VSET", "ALL")
if VSET != "ALL":
    _keep = set(VSET.split(","))
    VARIANTS = [v for v in VARIANTS if v[0] in _keep]
    assert len(VARIANTS) == len(_keep), "VSET co ten la"
VNAMES = [v[0] for v in VARIANTS]


def jout(path, obj):
    with open(path, "a") as f:
        f.write(json.dumps(obj) + "\n")
        f.flush()
        os.fsync(f.fileno())


def sha256(p, cap=None):
    h = hashlib.sha256()
    n = 0
    with open(p, "rb") as f:
        while True:
            b = f.read(1 << 24)
            if not b:
                break
            h.update(b)
            n += len(b)
            if cap and n >= cap:
                break
    return h.hexdigest(), n


def load_oi():
    p = OI_DIR + "/oi_percoin_full.bin"
    dig, nb = sha256(p)
    log.info("OI file %s bytes=%d sha256=%s (cho doi %s) KHOP=%s", p, nb, dig, SHA_OI, dig == SHA_OI)
    assert dig == SHA_OI, "FILE OI KHONG PHAI BAN SACH -> VOID (xem docs/OI_FIX_LOG.md)"
    a = np.memmap(p, dtype=OI_DT, mode="r")
    keep = np.asarray(a["ts"]) < TS_HI
    o = np.array(a[keep])
    del a, keep
    log.info("OI: giu %d ban ghi (ts < %s)", len(o), pd.to_datetime(TS_HI, unit="ms"))
    return o


def t1_files():
    fs = sorted(glob.glob(T1_DIR + "/features_*"))
    fs = [f for f in fs if os.path.basename(f).split("_")[1] < "20240701"]
    assert fs, "khong thay Tool1"
    log.info("Tool1 files (%d): %s", len(fs), [os.path.basename(f) for f in fs])
    return fs


def build_features(oi, smap):
    """merge_asof theo TUNG NAM (y canonical), stream ra memmap 47 cot."""
    fs = t1_files()
    years = sorted(set(os.path.basename(f).split("_")[1][:4] for f in fs))
    os.makedirs(MM_DIR, exist_ok=True)
    mm_path = MM_DIR + "/xall.f32"
    fh = open(mm_path, "wb")
    ts_p, sym_p = [], []
    off = 0
    for yr in years:
        yf = [f for f in fs if os.path.basename(f).split("_")[1][:4] == yr]
        parts = [read_tool1(f, grid_ms=GRID_MS) for f in yf]
        a = parts[0] if len(parts) == 1 else np.concatenate(parts)
        del parts
        a = a[a["ts"] < TS_HI]
        lo = int(pd.Timestamp(yr + "-01-01", tz="UTC").value // 10**6)
        hi = int(pd.Timestamp(str(int(yr) + 1) + "-01-01", tz="UTC").value // 10**6)
        oc = oi[(oi["ts"] >= lo - OI_TOL) & (oi["ts"] < hi)]
        t = pd.DataFrame({"ts": a["ts"].astype(np.int64), "symId": a["sym"].astype(np.int32)})
        F = np.asarray(a["f"], dtype=np.float32)
        for j in range(40):
            t["f%d" % j] = F[:, j]
        o = pd.DataFrame({"ts": oc["ts"].astype(np.int64), "symId": oc["sym"].astype(np.int32)})
        O = np.asarray(oc["oi"], dtype=np.float32)
        for j, nm in enumerate(OI_NAMES):
            o[nm] = O[:, j]
        t = t.sort_values("ts").reset_index(drop=True)
        o = o.sort_values("ts").reset_index(drop=True)
        mg = pd.merge_asof(t, o, on="ts", by="symId", direction="backward", tolerance=OI_TOL)
        mg = mg.merge(smap, on="symId", how="left").dropna(subset=["symbol"])
        mg = mg.sort_values("ts").reset_index(drop=True)
        cols = ["f%d" % j for j in range(40)] + OI_NAMES
        blk = np.zeros((len(mg), NF), dtype=np.float32)
        blk[:, :45] = mg[cols].to_numpy(np.float32)
        blk.tofile(fh)
        ts_p.append(mg["ts"].to_numpy(np.int64))
        sym_p.append(mg["symId"].to_numpy(np.int32))
        off += len(mg)
        log.info("  nam %s: tool1=%d oi=%d -> %d (off=%d) oi_nan=%.4f", yr, len(a), len(oc),
                 len(mg), off, float(mg[OI_NAMES[0]].isna().mean()))
        del a, F, O, t, o, mg, blk, oc
    fh.close()
    X = np.memmap(mm_path, dtype=np.float32, mode="r+", shape=(off, NF))
    ts_all = np.concatenate(ts_p)
    sym_all = np.concatenate(sym_p)
    assert np.all(np.diff(ts_all) >= 0), "ts khong tang dan"
    X[:, 45] = np.random.default_rng(101).standard_normal(off).astype(np.float32)
    X[:, 46] = np.random.default_rng(202).standard_normal(off).astype(np.float32)
    X.flush()
    log.info("Xall: %d x %d -> %s", off, NF, mm_path)
    return X, ts_all, sym_all, mm_path


def load_labels(smap):
    fs = sorted(glob.glob(LB_DIR + "/funding_label_202[1-4]*.pb"))
    fs = [f for f in fs if os.path.basename(f).split("_")[2] < "20240701"]
    assert fs, "khong thay label"
    m0 = FLPB.meta(fs[0])
    log.info("label meta: %s", m0)
    assert int(m0["step_min"]) == GRID_MIN, "LABEL/TOOL1 GRID MISMATCH"
    s2i = dict(zip(smap.symbol, smap.symId.astype(np.int32)))
    parts = []
    for fp in fs:
        d = FLPB.read_label(fp, usecols=["tEpochMs", "symbol", "maxFav_4h", "nBars_4h"])
        d = d[(d.nBars_4h >= NEED) & d.maxFav_4h.notna()]
        sid = d.symbol.map(s2i)
        k = sid.notna().to_numpy()
        ts = d.tEpochMs.to_numpy(np.int64)[k]
        keep = ts < TS_HI
        parts.append(pd.DataFrame({
            "ts": ts[keep], "symId": sid[k].to_numpy(np.int32)[keep],
            "y": (d.maxFav_4h.to_numpy(np.float64)[k][keep] >= WIN).astype(np.int8)}))
        del d
    L = pd.concat(parts, ignore_index=True)
    log.info("Label 4h: %d dong | base=%.4f", len(L), float(L.y.mean()))
    return L


def join_labels(ts_all, sym_all, L):
    """Join (ts,symId) bang key int64 + searchsorted (nhe hon pandas merge)."""
    key_all = ts_all * 1024 + sym_all.astype(np.int64)
    srt = np.argsort(key_all, kind="stable")
    ks = key_all[srt]
    assert not np.any(np.diff(ks) == 0), "Xall co (ts,symId) trung lap"
    kl = L.ts.to_numpy(np.int64) * 1024 + L.symId.to_numpy(np.int64)
    ip = np.searchsorted(ks, kl)
    ipc = np.clip(ip, 0, len(ks) - 1)
    hit = ks[ipc] == kl
    pos = srt[ipc[hit]]
    y = L.y.to_numpy(np.int8)[hit]
    tsh = L.ts.to_numpy(np.int64)[hit]
    o = np.argsort(tsh, kind="stable")
    log.info("join label: %d/%d dong label khop Xall", int(hit.sum()), len(L))
    return pos[o], y[o], tsh[o]


def map_pool(ts_all, sym_all, oos_ts, oos_sym, pool):
    """Vi tri cua tung dong pool trong chuoi prediction OOS."""
    ko = oos_ts * 1024 + oos_sym.astype(np.int64)
    srt = np.argsort(ko, kind="stable")
    ks = ko[srt]
    kp = pool.ts.to_numpy(np.int64) * 1024 + pool.sym.to_numpy(np.int64)
    ip = np.clip(np.searchsorted(ks, kp), 0, len(ks) - 1)
    hit = ks[ip] == kp
    log.info("map pool: %d/%d dong pool co prediction", int(hit.sum()), len(pool))
    if not hit.all():
        assert SMOKE, "co dong pool khong co prediction -> VOID"
        log.warning("SMOKE: bo %d dong pool khong co prediction", int((~hit).sum()))
    return srt[ip], hit


def bstats(u, v, bid, nb):
    n = np.bincount(bid, minlength=nb).astype(np.float64)
    return np.stack([n,
                     np.bincount(bid, weights=u, minlength=nb),
                     np.bincount(bid, weights=v, minlength=nb),
                     np.bincount(bid, weights=u * u, minlength=nb),
                     np.bincount(bid, weights=v * v, minlength=nb),
                     np.bincount(bid, weights=u * v, minlength=nb)], axis=1)


def r_from(S):
    n, Sx, Sy, Sxx, Syy, Sxy = [S[..., i] for i in range(6)]
    with np.errstate(invalid="ignore", divide="ignore"):
        cov = Sxy - Sx * Sy / n
        vx = Sxx - Sx * Sx / n
        vy = Syy - Sy * Sy / n
        return cov / np.sqrt(vx * vy)


def mono20(p, y):
    b = pd.qcut(pd.Series(p), 20, labels=False, duplicates="drop")
    m = pd.DataFrame({"b": b, "y": y}).groupby("b").y.mean()
    d = m.diff().dropna()
    return float((d > 0).mean()), int(len(d) + 1)


def dyn_thr(score, c=1.0):
    return c * GMM * np.maximum(GAMIN, score / GRMAX * GAMULT)


def match_c(score, p15, n0):
    lo, hi = 0.05, 20.0
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        n = int((p15 >= dyn_thr(score, mid)).sum())
        if n > n0:
            lo = mid
        else:
            hi = mid
        if abs(n - n0) <= max(1, int(0.005 * n0)):
            return mid, n
    mid = 0.5 * (lo + hi)
    return mid, int((p15 >= dyn_thr(score, mid)).sum())


def main():
    t00 = time.time()
    log.info("SMOKE=%d NEST=%d folds=%s variants=%s", SMOKE, NEST, CUT_DATES, VNAMES)
    smap = pd.read_csv(OI_DIR + "/symbol_map.csv")
    oi = load_oi()
    X, ts_all, sym_all, mm = build_features(oi, smap)
    del oi
    L = load_labels(smap)
    lab_pos, lab_y, lab_ts = join_labels(ts_all, sym_all, L)
    del L
    import xgboost as xgb
    log.info("xgboost %s", xgb.__version__)
    cutoffs = [int(pd.Timestamp("%s-%s-%s" % (c[:4], c[4:6], c[6:8]), tz="UTC").value // 10**6) - TZ
               for c in CUT_DATES]
    preds = dict((v, []) for v in VNAMES)
    oos_ts, oos_sym = [], []
    for fi, c in enumerate(cutoffs):
        tr_cut = c - PURGE_MS
        cdt = pd.to_datetime(c + TZ, unit="ms").normalize()
        b_hi = int((cdt + pd.DateOffset(months=3)).value // 10**6) - TZ
        ie = int(np.searchsorted(lab_ts, tr_cut, "left"))
        assert ie > 5000, "fold %d train it" % fi
        assert lab_ts[ie - 1] < c, "LEAK fold %d" % fi
        tp = np.sort(lab_pos[:ie])
        ty = lab_y[np.argsort(lab_pos[:ie], kind="stable")]
        lo = int(np.searchsorted(ts_all, c, "left"))
        hi = int(np.searchsorted(ts_all, b_hi, "left"))
        assert hi > lo, "fold %d OOS rong" % fi
        pos = float(ty.mean())
        Xtr = np.asarray(X[tp])
        Xoo = np.asarray(X[lo:hi])
        oos_ts.append(ts_all[lo:hi].copy())
        oos_sym.append(sym_all[lo:hi].copy())
        np.save(OUT + "/f%d_ts.npy" % fi, ts_all[lo:hi])
        np.save(OUT + "/f%d_sym.npy" % fi, sym_all[lo:hi])
        log.info("fold %d cut=%s tr_cut=%s n_tr=%d pos=%.4f n_oos=%d", fi, CUT_DATES[fi],
                 pd.to_datetime(tr_cut, unit="ms"), len(tp), pos, hi - lo)
        for vn, cols in VARIANTS:
            t0 = time.time()
            clf = xgb.XGBClassifier(n_estimators=NEST, max_depth=5, learning_rate=0.05,
                                    subsample=0.8, colsample_bytree=0.8, min_child_weight=20,
                                    scale_pos_weight=(1 - pos) / max(pos, 1e-6),
                                    eval_metric="auc", n_jobs=-1, tree_method="hist",
                                    random_state=SEED, device="cuda")
            clf.fit(Xtr[:, cols], ty, verbose=False)
            pv = clf.predict_proba(Xoo[:, cols])[:, 1].astype(np.float32)
            preds[vn].append(pv)
            np.save(OUT + "/f%d_%s.npy" % (fi, vn), pv)
            del clf
            jout(PRG, {"fold": fi, "cut": CUT_DATES[fi], "variant": vn, "n_feat": len(cols),
                       "n_train": int(len(tp)), "pos": pos, "n_oos": int(hi - lo),
                       "sec": round(time.time() - t0, 1), "p_mean": float(pv.mean())})
            log.info("   %-14s nfeat=%2d %.1fs p_mean=%.5f", vn, len(cols),
                     time.time() - t0, float(pv.mean()))
        del Xtr, Xoo
    oos_ts = np.concatenate(oos_ts)
    oos_sym = np.concatenate(oos_sym)
    log.info("train xong %.1f phut", (time.time() - t00) / 60)
    return X, ts_all, sym_all, mm, preds, oos_ts, oos_sym


def score_all(ts_all, sym_all, preds, oos_ts, oos_sym):
    pool = pd.read_parquet(POOL)
    log.info("pool: %d dong ts[%s..%s]", len(pool),
             pd.to_datetime(pool.ts.min(), unit="ms"), pd.to_datetime(pool.ts.max(), unit="ms"))
    assert int(pool.ts.max()) < int(pd.Timestamp("2024-07-15").value // 10**6), "CHAM VALIDATION"
    midx, hit = map_pool(ts_all, sym_all, oos_ts, oos_sym, pool)
    if not hit.all():
        pool = pool[hit].reset_index(drop=True)
        midx = midx[hit]
    ts = pool.ts.to_numpy(np.int64)
    p15 = pool.p15.to_numpy(np.float64)
    y = pool.g1lite.to_numpy(np.float64)
    p_old = pool.p_old.to_numpy(np.float64)
    yr = pd.to_datetime(ts, unit="ms").year.to_numpy()
    ry = rankdata(y)
    ry = (ry - ry.mean()) / len(ry)
    t0 = ts.min()
    BL = {"24h": 24, "72h": 72, "168h": 168}
    bids = dict((k, ((ts - t0) // (v * 3_600_000)).astype(np.int64)) for k, v in BL.items())
    nbs = dict((k, int(b.max()) + 1) for k, b in bids.items())
    log.info("so khoi: %s", nbs)
    n0 = None
    S = {}
    A = {}
    pv_all = {}
    for vn in list(preds.keys()) + ["p_old"]:
        p = p_old if vn == "p_old" else np.concatenate(preds[vn])[midx].astype(np.float64)
        pv_all[vn] = p
        rp = rankdata(p)
        rp = (rp - rp.mean()) / len(rp)
        rho = float(r_from(bstats(rp, ry, np.zeros(len(rp), np.int64), 1)[0]))
        mo, nb20 = mono20(p, y)
        peryr = {}
        for u in sorted(set(yr.tolist())):
            m = yr == u
            peryr[str(u)] = float(np.corrcoef(rankdata(p[m]), rankdata(y[m]))[0, 1])
        sc = 1.0 - p
        adm = p15 >= dyn_thr(sc)
        na = int(adm.sum())
        if vn == "full45":
            n0 = na
        cm, nm = match_c(sc, p15, n0 if n0 else na)
        admm = p15 >= dyn_thr(sc, cm)
        rec = {"variant": vn, "rho": rho, "n": int(len(p)), "mono20": mo, "nb20": nb20,
               "rho_year": peryr, "n_admit": na, "admit_rate": na / len(p),
               "q_admit": float(y[adm].mean()), "match_c": cm, "n_admit_matched": nm,
               "q_admit_matched": float(y[admm].mean()), "pool_mean_g1lite": float(y.mean()),
               "p_mean": float(p.mean()), "p_std": float(p.std())}
        jout(RES, rec)
        log.info("RESULT %-14s rho=%.5f mono=%.2f n_adm=%6d rate=%.5f q=%.5f qm=%.5f c=%.3f",
                 vn, rho, mo, na, na / len(p), float(y[adm].mean()), float(y[admm].mean()), cm)
        S[vn] = dict((k, bstats(rp, ry, bids[k], nbs[k])) for k in BL)
        A[vn] = dict((k, np.stack([np.bincount(bids[k][adm], minlength=nbs[k]).astype(np.float64),
                                   np.bincount(bids[k][adm], weights=y[adm], minlength=nbs[k]),
                                   np.bincount(bids[k][admm], minlength=nbs[k]).astype(np.float64),
                                   np.bincount(bids[k][admm], weights=y[admm], minlength=nbs[k])],
                                  axis=1)) for k in BL)
        np.save(OUT + "/pred_%s.npy" % vn, p.astype(np.float32))
        del rp
    return pool, bids, nbs, S, A, pv_all, y


K_MULT = float(np.sqrt(2.0 * np.log(9.0)))     # 2.0957, M=9 (PREREG section 2)


def boot(bids, nbs, S, A, pv_all, y):
    out = {"k_mult": K_MULT, "n_rep": NREP, "seed": BSEED, "M": 9}
    names = list(S.keys())
    picks_keep = None
    for bl in ("24h", "72h", "168h"):
        nb = nbs[bl]
        alive = np.flatnonzero(S["full45"][bl][:, 0] > 0)
        rng = np.random.default_rng(BSEED)
        picks = rng.integers(0, len(alive), size=(NREP, len(alive)))
        cnt = np.zeros((NREP, len(alive)), dtype=np.float64)
        for i in range(NREP):
            cnt[i] = np.bincount(picks[i], minlength=len(alive))
        if bl == "72h":
            picks_keep = (alive, picks)
        rr = {}
        qq = {}
        qqm = {}
        for vn in names:
            Sv = S[vn][bl][alive]
            rr[vn] = r_from(cnt @ Sv)
            Av = A[vn][bl][alive]
            tot = cnt @ Av
            with np.errstate(invalid="ignore", divide="ignore"):
                qq[vn] = tot[:, 1] / tot[:, 0]
                qqm[vn] = tot[:, 3] / tot[:, 2]
        for vn in names:
            for tag, arr in (("rho", rr), ("q_admit", qq), ("q_admit_matched", qqm)):
                d = arr[vn] - arr["full45"]
                lo, hi = np.percentile(d, [2.5, 97.5])
                sd = float(d.std(ddof=1))
                out["%s|%s|%s" % (vn, tag, bl)] = {
                    "point_v": float(np.nanmean(arr[vn])), "d_mean": float(np.nanmean(d)),
                    "sd": sd, "ci_lo": float(lo), "ci_hi": float(hi),
                    "wide_lo": float(np.nanmean(d) - K_MULT * sd),
                    "wide_hi": float(np.nanmean(d) + K_MULT * sd),
                    "p_d_gt0": float((d > 0).mean()), "n_block": int(len(alive))}
        log.info("boot %s: n_block=%d | sd(d rho) %s", bl, len(alive),
                 dict((v, round(out["%s|rho|%s" % (v, bl)]["sd"], 5)) for v in names))
    return out, picks_keep


def observed(S, A):
    o = {}
    for vn in S:
        for bl in ("24h", "72h", "168h"):
            Sv = S[vn][bl].sum(axis=0)
            Av = A[vn][bl].sum(axis=0)
            o["%s|rho|%s" % (vn, bl)] = float(r_from(Sv))
            o["%s|q_admit|%s" % (vn, bl)] = float(Av[1] / Av[0])
            o["%s|q_admit_matched|%s" % (vn, bl)] = float(Av[3] / Av[2])
    return o


def patch_obs(out, obs):
    """Diem uoc luong = HIEU QUAN SAT DUOC (khong phai trung binh bootstrap)."""
    for k, rec in list(out.items()):
        if "|" not in k:
            continue
        vn, tag, bl = k.split("|")
        base = obs["full45|%s|%s" % (tag, bl)]
        d_obs = obs[k] - base
        rec["point_v_obs"] = obs[k]
        rec["point_full45_obs"] = base
        rec["d_obs"] = d_obs
        rec["wide_lo"] = d_obs - K_MULT * rec["sd"]
        rec["wide_hi"] = d_obs + K_MULT * rec["sd"]
    return out


def crude_check(bids, pv_all, y, picks_keep):
    """Kiem chung xap xi frozen-rank: bootstrap THO (tinh lai spearman tren dong resample)."""
    alive, picks = picks_keep
    bid = bids["72h"]
    order = np.argsort(bid, kind="stable")
    bs = bid[order]
    st = np.searchsorted(bs, np.arange(int(bid.max()) + 2))
    rows = [order[st[b]:st[b + 1]] for b in alive]
    res = {}
    ds = []
    t0 = time.time()
    for i in range(NCRUDE):
        idx = np.concatenate([rows[j] for j in picks[i]])
        yy = rankdata(y[idx])
        r = {}
        for vn in ("full45", "no_oi"):
            r[vn] = float(np.corrcoef(rankdata(pv_all[vn][idx]), yy)[0, 1])
        ds.append(r["no_oi"] - r["full45"])
        del idx, yy
    ds = np.array(ds)
    res["n_rep"] = NCRUDE
    res["sd_crude"] = float(ds.std(ddof=1))
    res["d_mean_crude"] = float(ds.mean())
    res["sec"] = round(time.time() - t0, 1)
    log.info("crude check (%d rep, %.0fs): sd(d)=%.6f mean=%.6f",
             NCRUDE, time.time() - t0, res["sd_crude"], res["d_mean_crude"])
    return res


if __name__ == "__main__":
    try:
        X, ts_all, sym_all, mm, preds, ots, osy = main()
        pool, bids, nbs, S, A, pv_all, yv = score_all(ts_all, sym_all, preds, ots, osy)
        del X, preds
        try:
            os.remove(mm)
        except OSError:
            pass
        try:
            out, pk = boot(bids, nbs, S, A, pv_all, yv)
            out = patch_obs(out, observed(S, A))
            if NCRUDE > 0 and "no_oi" in pv_all and "full45" in pv_all:
                out["crude"] = crude_check(bids, pv_all, yv, pk)
            with open(OUT + "/g015cut_boot.json", "w") as f:
                json.dump(out, f, indent=1)
                f.flush()
                os.fsync(f.fileno())
        except Exception:
            import traceback
            traceback.print_exc()
            log.warning("boot loi -> bo qua, preds da luu")
        np.savez_compressed(OUT + "/blockstats.npz",
                            **dict(("%s_%s" % (v, b), S[v][b]) for v in S for b in S[v]),
                            **dict(("A_%s_%s" % (v, b), A[v][b]) for v in A for b in A[v]))
        log.info("DONE")
    except Exception:
        import traceback
        traceback.print_exc()
        raise
