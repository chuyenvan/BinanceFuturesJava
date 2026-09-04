"""G015 REBUILD — tai lap DETERMINISTIC tren CPU, sinh bins predict_wf_*.bin MOI.
Xem docs/PREREG_G015REBUILD.md. CHI DEV. KHONG ghi de bins cu. KHONG rebuild OI (chi doc + ghim sha).
Env: OUT_DIR (bat buoc), G015_NJOBS (mac dinh 4).
"""
import os, sys, glob, json, time, struct, hashlib, logging
import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("rebuild")
sys.path.insert(0, "/home/ubuntu/sel1m_code")
from tool1_col import read_tool1
import funding_label_pb as FLPB
from scipy.stats import spearmanr

OUT = os.environ["OUT_DIR"]
os.makedirs(OUT, exist_ok=True)
SCRATCH = os.environ.get("SCRATCH", "/home/ubuntu/g015/scratch")
os.makedirs(SCRATCH, exist_ok=True)
T1_DIR = "/home/ubuntu/ds_feat15m"
LB_DIR = "/home/ubuntu/label_15m"
OI_FILE = "/home/ubuntu/claudedata/oi/oi_percoin_full.bin"
MAP_CSV = "/home/ubuntu/claudedata/oi/symbol_map.csv"
POOL = "/home/ubuntu/g015/pool/pool_dev.parquet"
SHA_OI = "e3887f63097299655213f8382ca7e473e126ee4d7ddf69a39658942651b305ec"

GRID_MS = 15 * 60_000
TZ = 7 * 3_600_000
OI_TOL = 2 * 3_600_000
PURGE_MS = 288 * GRID_MS
H_MIN, WIN = 240, 0.06
NEED = H_MIN // 15
NEST, SEED = 400, 42
NJOBS = int(os.environ.get("G015_NJOBS", "4"))
OI_NAMES = ["oi_delta24h", "oi_z", "ls_global", "ls_toptrader", "taker_buy"]
OI_DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("oi", ">f4", 5)])
NF = 45
CUT_DATES = ["20220101", "20220401", "20220701", "20221001", "20230101",
             "20230401", "20230701", "20231001", "20240101", "20240401"]
TS_HI = int(pd.Timestamp("2024-07-01", tz="UTC").value // 10**6) - TZ


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""):
            h.update(b)
    return h.hexdigest()


def load_oi():
    d = sha256(OI_FILE)
    assert d == SHA_OI, "FILE OI KHONG PHAI BAN SACH: %s" % d
    log.info("OI sha256 KHOP ban sach: %s", d)
    a = np.memmap(OI_FILE, dtype=OI_DT, mode="r")
    o = np.array(a[np.asarray(a["ts"]) < TS_HI])
    del a
    log.info("OI giu %d ban ghi (< %s)", len(o), pd.to_datetime(TS_HI, unit="ms"))
    return o


def t1_files():
    fs = sorted(glob.glob(T1_DIR + "/features_*.t1c.gz"))
    fs = [f for f in fs if os.path.basename(f).split("_")[1] < "20240701"]
    assert fs, "khong thay Tool1"
    return fs


def build_features(oi, smap):
    fs = t1_files()
    years = sorted(set(os.path.basename(f).split("_")[1][:4] for f in fs))
    mm = SCRATCH + "/xall.f32"
    fh = open(mm, "wb")
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
        np.ascontiguousarray(mg[cols].to_numpy(np.float32)).tofile(fh)
        ts_p.append(mg["ts"].to_numpy(np.int64))
        sym_p.append(mg["symId"].to_numpy(np.int32))
        off += len(mg)
        log.info("  nam %s: tool1=%d oi=%d -> %d (off=%d)", yr, len(a), len(oc), len(mg), off)
        del a, F, O, t, o, mg, oc
    fh.close()
    X = np.memmap(mm, dtype=np.float32, mode="r", shape=(off, NF))
    ts_all = np.concatenate(ts_p)
    sym_all = np.concatenate(sym_p)
    assert np.all(np.diff(ts_all) >= 0), "ts khong tang dan"
    log.info("Xall %d x %d (sha xall.f32=%s)", off, NF, sha256(mm))
    return X, ts_all, sym_all, mm


def load_labels(smap):
    fs = sorted(glob.glob(LB_DIR + "/funding_label_202[1-4]*.pb"))
    fs = [f for f in fs if os.path.basename(f).split("_")[2] < "20240701"]
    m0 = FLPB.meta(fs[0])
    assert int(m0["step_min"]) == 15, "LABEL step != 15"
    s2i = dict(zip(smap.symbol, smap.symId.astype(np.int32)))
    parts = []
    for fp in fs:
        d = FLPB.read_label(fp, usecols=["tEpochMs", "symbol", "maxFav_4h", "nBars_4h"])
        d = d[(d.nBars_4h >= NEED) & d.maxFav_4h.notna()]
        sid = d.symbol.map(s2i)
        k = sid.notna().to_numpy()
        ts = d.tEpochMs.to_numpy(np.int64)[k]
        keep = ts < TS_HI
        parts.append(pd.DataFrame({"ts": ts[keep], "symId": sid[k].to_numpy(np.int32)[keep],
                                   "y": (d.maxFav_4h.to_numpy(np.float64)[k][keep] >= WIN).astype(np.int8)}))
        del d
    L = pd.concat(parts, ignore_index=True)
    log.info("Label 4h: %d dong base=%.4f", len(L), float(L.y.mean()))
    return L


def join_labels(ts_all, sym_all, L):
    key = ts_all * 1024 + sym_all.astype(np.int64)
    srt = np.argsort(key, kind="stable")
    ks = key[srt]
    assert not np.any(np.diff(ks) == 0), "Xall trung (ts,symId)"
    kl = L.ts.to_numpy(np.int64) * 1024 + L.symId.to_numpy(np.int64)
    ip = np.clip(np.searchsorted(ks, kl), 0, len(ks) - 1)
    hit = ks[ip] == kl
    pos = srt[ip[hit]]
    y = L.y.to_numpy(np.int8)[hit]
    tsh = L.ts.to_numpy(np.int64)[hit]
    o = np.argsort(tsh, kind="stable")
    log.info("join label: %d/%d khop", int(hit.sum()), len(L))
    return pos[o], y[o], tsh[o]


def write_bin(path, ts, sid, p):
    with open(path, "wb") as fo:
        nan = float("nan")
        buf = bytearray()
        for i in range(len(ts)):
            buf += struct.pack(">qh4f", int(ts[i]), int(sid[i]), float(p[i]), nan, nan, nan)
        fo.write(buf)
        fo.flush()
        os.fsync(fo.fileno())
    log.info("ghi %s: %d rec (%d B)", os.path.basename(path), len(ts), len(ts) * 26)


def main():
    t00 = time.time()
    log.info("REBUILD CPU | OUT=%s NJOBS=%d NEST=%d SEED=%d", OUT, NJOBS, NEST, SEED)
    smap = pd.read_csv(MAP_CSV)
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
    # pool de cham rho
    pool = pd.read_parquet(POOL)
    kp = pool.ts.to_numpy(np.int64) * 1024 + pool.sym.to_numpy(np.int64)
    pred_pool = np.full(len(pool), np.nan, dtype=np.float64)
    foldrec = {}
    for fi, c in enumerate(cutoffs):
        tr_cut = c - PURGE_MS
        cdt = pd.to_datetime(c + TZ, unit="ms").normalize()
        b_hi = int((cdt + pd.DateOffset(months=3)).value // 10**6) - TZ
        ie = int(np.searchsorted(lab_ts, tr_cut, "left"))
        assert ie > 5000 and lab_ts[ie - 1] < c, "fold %d train/leak" % fi
        tp = np.sort(lab_pos[:ie])
        ty = lab_y[np.argsort(lab_pos[:ie], kind="stable")]
        lo = int(np.searchsorted(ts_all, c, "left"))
        hi = int(np.searchsorted(ts_all, b_hi, "left"))
        assert hi > lo, "fold %d OOS rong" % fi
        pos = float(ty.mean())
        Xtr = np.asarray(X[tp])
        clf = xgb.XGBClassifier(n_estimators=NEST, max_depth=5, learning_rate=0.05,
                                subsample=0.8, colsample_bytree=0.8, min_child_weight=20,
                                scale_pos_weight=(1 - pos) / max(pos, 1e-6),
                                eval_metric="auc", n_jobs=NJOBS, tree_method="hist",
                                random_state=SEED)
        clf.fit(Xtr, ty, verbose=False)
        Xoo = np.asarray(X[lo:hi])
        pv = clf.predict_proba(Xoo)[:, 1].astype(np.float32)
        ots = ts_all[lo:hi]
        osy = sym_all[lo:hi]
        write_bin(OUT + "/predict_wf_%s.bin" % CUT_DATES[fi], ots, osy, pv)
        # map vao pool
        ko = ots * 1024 + osy.astype(np.int64)
        so = np.argsort(ko, kind="stable")
        kso = ko[so]
        ipp = np.clip(np.searchsorted(kso, kp), 0, len(kso) - 1)
        h = kso[ipp] == kp
        pred_pool[h] = pv[so[ipp[h]]]
        foldrec[CUT_DATES[fi]] = {"n_train": int(len(tp)), "pos": pos, "n_oos": int(hi - lo),
                                  "p_mean": float(pv.mean()), "p_std": float(pv.std()),
                                  "sha_bin": sha256(OUT + "/predict_wf_%s.bin" % CUT_DATES[fi])}
        log.info("fold %d %s n_tr=%d pos=%.4f n_oos=%d p_mean=%.5f", fi, CUT_DATES[fi],
                 len(tp), pos, hi - lo, float(pv.mean()))
        del Xtr, Xoo, clf
    del X
    try:
        os.remove(mm)
    except OSError:
        pass
    m = pool.g1lite.notna().to_numpy() & np.isfinite(pred_pool)
    assert m.all(), "co dong pool khong co pred: %d" % int((~m).sum())
    y = pool.g1lite.to_numpy(np.float64)
    rho = float(spearmanr(pred_pool, y).correlation)
    yr = pd.to_datetime(pool.ts.to_numpy(), unit="ms").year
    peryr = {str(u): float(spearmanr(pred_pool[yr == u], y[yr == u]).correlation)
             for u in sorted(set(yr.tolist()))}
    np.save(OUT + "/pred_pool.npy", pred_pool.astype(np.float32))
    summ = {"rho": rho, "rho_year": peryr, "n_pool": int(len(pool)), "folds": foldrec,
            "njobs": NJOBS, "nest": NEST, "seed": SEED, "xgb": xgb.__version__,
            "minutes": round((time.time() - t00) / 60, 1)}
    json.dump(summ, open(OUT + "/rebuild_summary.json", "w"), indent=1)
    log.info("RHO=%.5f peryr=%s | %.1f phut -> %s", rho, peryr, (time.time() - t00) / 60, OUT)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        raise
