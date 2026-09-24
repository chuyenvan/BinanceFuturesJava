#!/usr/bin/env python3
"""g5_pool_train.py — TRAINER ung vien NHAN cho G5 (docs/prereg/PREREG_G5.md).

Ban SAO cua `research/pipeline/g015_net_train.py` (sha256 05298cba5578...), THEM DUNG ba thu:
  (1) `--label-h {4,72}`  -> cot nhan `retEnd_{H}h` / `maxFav_{H}h`, loc `nBars_{H}h >= H*60/15`.
  (2) `--pool <parquet>`  -> chi PREDICT tren dong thuoc pool ung vien (cand_dev_x1),
      xuat `pool_<tag>.parquet` (ts,sym,p,fold). XGBoost du doan tung dong doc lap =>
      p tren tap con GIONG HET p tren toan bo roi loc. `c4_build_map.py` chi can THU TU
      cua ung vien tren dong co score; GIA TRI lay tu x26.
  (3) `--out-bins` (tuy chon) van ghi bins 26B.
MOI THU KHAC GIU NGUYEN recipe G015_RECIPE muc 2.
"""
import argparse, glob, hashlib, json, logging, os, struct, sys, time
import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("g5pool")
sys.path.insert(0, os.environ.get("SEL1M_CODE", "/home/ubuntu/sel1m_code"))
from tool1_col import read_tool1
import funding_label_pb as FLPB

PIPELINE_VERSION = "wfo-selector-v2-1m-canonical-20260804"
T1_DIR = os.environ.get("T1_DIR", "/home/ubuntu/ds_feat15m")
LB_DIR = os.environ.get("LB_DIR", "/home/ubuntu/label_15m")
OI_FILE = os.environ.get("OI_FILE", "/home/ubuntu/claudedata/oi/oi_percoin_full.bin")
MAP_CSV = os.environ.get("MAP_CSV", "/home/ubuntu/claudedata/oi/symbol_map.csv")

GRID_MIN = 15
GRID_MS = GRID_MIN * 60_000
TZ = 7 * 3_600_000
OI_TOL = 2 * 3_600_000
PURGE_STEPS = 288
PURGE_MS = PURGE_STEPS * GRID_MS
OOS_MONTHS = 3
OI_NAMES = ["oi_delta24h", "oi_z", "ls_global", "ls_toptrader", "taker_buy"]
OI_DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("oi", ">f4", 5)])
NF = 45
CUT_DATES = ["20220101", "20220401", "20220701", "20221001", "20230101", "20230401",
             "20230701", "20231001", "20240101", "20240401", "20240701", "20241001",
             "20250101", "20250401", "20250701", "20251001", "20260101", "20260401"]
CUT16 = CUT_DATES[:16]
NEST, SEED = 400, 42
KMUL = 1 << 20


def ms(datestr):
    d = pd.Timestamp("%s-%s-%s" % (datestr[:4], datestr[4:6], datestr[6:8]), tz="UTC")
    return int(d.value // 10 ** 6) - TZ


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""):
            h.update(b)
    return h.hexdigest()


def years_needed(hi_ms):
    y1 = int(pd.to_datetime(hi_ms - 1, unit="ms").year)
    return [str(y) for y in range(2021, y1 + 1)]


def build_matrix(years, scratch):
    ao = np.memmap(OI_FILE, dtype=OI_DT, mode="r")
    smap = pd.read_csv(MAP_CSV)
    log.info("MEMMAP-PERYEAR: OI=%d (full-native) years=%s NF=%d", len(ao), years, NF)
    mm = os.path.join(scratch, "_xall_mm.f32")
    fh = open(mm, "wb")
    ts_p, sym_p = [], []
    off = 0
    for yr in years:
        a = read_tool1(os.path.join(T1_DIR, "features_%s*" % yr), grid_ms=GRID_MS)
        F = a["f"]
        lo = int(pd.Timestamp(yr + "-01-01", tz="UTC").value // 10 ** 6)
        hi = int(pd.Timestamp(str(int(yr) + 1) + "-01-01", tz="UTC").value // 10 ** 6)
        aots = np.asarray(ao["ts"])
        msk = (aots >= lo - OI_TOL) & (aots < hi)
        del aots
        aoc = np.array(ao[msk])
        del msk
        t = pd.DataFrame({"ts": a["ts"].astype(np.int64), "symId": a["sym"].astype(np.int32),
                          "ridx": np.arange(len(a), dtype=np.int64)})
        o = pd.DataFrame({"ts": aoc["ts"].astype(np.int64), "symId": aoc["sym"].astype(np.int32)})
        O = np.asarray(aoc["oi"], dtype=np.float32)
        for j, nm in enumerate(OI_NAMES):
            o[nm] = O[:, j]
        del aoc, O
        t = t.sort_values("ts").reset_index(drop=True)
        o = o.sort_values("ts").reset_index(drop=True)
        mg = pd.merge_asof(t, o, on="ts", by="symId", direction="backward", tolerance=OI_TOL)
        del t, o
        mg = mg.merge(smap, on="symId", how="left").dropna(subset=["symbol"])
        mg = mg.sort_values("ts").reset_index(drop=True)
        n = len(mg)
        Xy = np.empty((n, NF), dtype=np.float32)
        Xy[:, :40] = F[mg["ridx"].to_numpy()]
        Xy[:, 40:] = mg[OI_NAMES].to_numpy(np.float32)
        Xy.tofile(fh)
        ts_p.append(mg["ts"].to_numpy(np.int64))
        sym_p.append(mg["symId"].to_numpy(np.int32))
        off += n
        log.info("  nam %s: tool1=%d -> merged=%d (off=%d)", yr, len(a), n, off)
        del a, F, mg, Xy
    fh.close()
    del ao
    X = np.memmap(mm, dtype=np.float32, mode="r", shape=(off, NF))
    ts_all = np.concatenate(ts_p)
    sym_all = np.concatenate(sym_p)
    assert np.all(np.diff(ts_all) >= 0), "ts khong tang dan"
    log.info("Features (memmap-peryear): %d rows x %d cols", off, NF)
    return X, ts_all, sym_all, mm


def load_labels(mode, thr, lab_h, hi_ms):
    col = ("retEnd_%dh" if mode == "net" else "maxFav_%dh") % lab_h
    nbc = "nBars_%dh" % lab_h
    need = lab_h * 60 // GRID_MIN
    fs = sorted(glob.glob(LB_DIR + "/funding_label_*.pb"))
    fs = [f for f in fs if os.path.basename(f).split("_")[2] < "20260701"]
    m0 = FLPB.meta(fs[0])
    assert int(m0["step_min"]) == GRID_MIN, "LABEL step != %d" % GRID_MIN
    log.info("Label meta OK: step_min=%d scale=%d horizons=%s %d file | col=%s need=%d",
             m0["step_min"], m0["scale"], m0["horizons"], len(fs), col, need)
    smap = pd.read_csv(MAP_CSV)
    s2i = dict(zip(smap.symbol, smap.symId.astype(np.int32)))
    parts, tot = [], 0
    for fp in fs:
        d = FLPB.read_label(fp, usecols=["tEpochMs", "symbol", col, nbc])
        tot += len(d)
        d = d[(d[nbc] >= need) & d[col].notna()]
        sid = d.symbol.map(s2i)
        k = sid.notna().to_numpy()
        ts = d.tEpochMs.to_numpy(np.int64)[k]
        v = d[col].to_numpy(np.float64)[k]
        keep = ts < hi_ms
        yv = (v[keep] > thr) if mode == "net" else (v[keep] >= thr)
        parts.append(pd.DataFrame({"ts": ts[keep], "symId": sid[k].to_numpy(np.int32)[keep],
                                   "y": yv.astype(np.int8)}))
        del d
    L = pd.concat(parts, ignore_index=True)
    log.info("Label (protobuf): %d dong tu %d file", tot, len(fs))
    log.info("Label %dh (%s thr=%.4f): %d rows | base=%.4f", lab_h, mode, thr, len(L),
             float(L.y.mean()))
    return L, float(L.y.mean()), len(L)


def train_rows(ts_all, sym_all, L, tr_cut):
    key = ts_all * KMUL + sym_all.astype(np.int64)
    srt = np.argsort(key, kind="stable")
    ks = key[srt]
    assert not np.any(np.diff(ks) == 0), "Xall trung (ts,symId)"
    kl = L.ts.to_numpy(np.int64) * KMUL + L.symId.to_numpy(np.int64)
    lab = np.full(len(ts_all), -1, dtype=np.int8)
    ip = np.clip(np.searchsorted(ks, kl), 0, len(ks) - 1)
    hit = ks[ip] == kl
    lab[srt[ip[hit]]] = L.y.to_numpy(np.int8)[hit]
    sel = (lab >= 0) & (ts_all < tr_cut)
    pos_idx = np.flatnonzero(sel)
    return pos_idx, lab[pos_idx]


def write_bin(path, ts, sid, p):
    nan = float("nan")
    with open(path, "wb") as fo:
        buf = bytearray()
        for i in range(len(ts)):
            buf += struct.pack(">qh4f", int(ts[i]), int(sid[i]), float(p[i]), nan, nan, nan)
        fo.write(buf)
        fo.flush()
        os.fsync(fo.fileno())
    log.info("ghi %s: %d rec = %d bytes", path, len(ts), len(ts) * 26)


def main():
    ap = argparse.ArgumentParser(description="G5 — trainer ung vien nhan, xuat pool preds")
    ap.add_argument("--tag", required=True)
    ap.add_argument("--fold", default="all16")
    ap.add_argument("--device", default="cpu", choices=["cpu", "cuda"])
    ap.add_argument("--out-dir", default="/kaggle/working")
    ap.add_argument("--scratch", default=None)
    ap.add_argument("--pool", default=None)
    ap.add_argument("--label-mode", default="net", choices=["net", "maxfav"])
    ap.add_argument("--label-h", type=int, default=4, choices=[4, 12, 24, 72])
    ap.add_argument("--thr", type=float, default=0.015)
    ap.add_argument("--njobs", type=int, default=int(os.environ.get("G015_NJOBS", "-1")))
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--nest", type=int, default=NEST)
    ap.add_argument("--out-bins", action="store_true")
    ap.add_argument("--save-model", action="store_true")
    ap.add_argument("--keep-scratch", action="store_true")
    a = ap.parse_args()

    t00 = time.time()
    os.makedirs(a.out_dir, exist_ok=True)
    scratch = a.scratch or os.path.join(a.out_dir, "scratch")
    os.makedirs(scratch, exist_ok=True)
    if a.fold == "all16":
        folds = list(CUT16)
    elif a.fold == "all":
        folds = list(CUT_DATES)
    else:
        folds = [x.strip() for x in a.fold.split(",") if x.strip()]
    for f in folds:
        assert f in CUT_DATES, "fold %s khong nam trong 18 cutoff" % f
    log.info("PIPELINE_VERSION=%s | GRID_MIN=%d | PURGE=%dh | OOS_MONTHS=%d | TZ=+%dh",
             PIPELINE_VERSION, GRID_MIN, PURGE_MS // 3_600_000, OOS_MONTHS, TZ // 3_600_000)
    log.info("G5 POOL TRAIN tag=%s folds=%d (%s..%s) device=%s njobs=%d seed=%d "
             "label=%s h=%d thr=%.4f pool=%s", a.tag, len(folds), folds[0], folds[-1],
             a.device, a.njobs, a.seed, a.label_mode, a.label_h, a.thr, a.pool)

    hi_all = 0
    for f in folds:
        c = ms(f)
        cdt = pd.to_datetime(c + TZ, unit="ms").normalize()
        hi_all = max(hi_all, int((cdt + pd.DateOffset(months=OOS_MONTHS)).value // 10 ** 6) - TZ)
    yrs = years_needed(hi_all)
    X, ts_all, sym_all, mm = build_matrix(yrs, scratch)
    L, base_rate, n_lab = load_labels(a.label_mode, a.thr, a.label_h, hi_all)

    pk = None
    if a.pool:
        P = pd.read_parquet(a.pool)
        pk = np.sort(P.ts.to_numpy(np.int64) * KMUL + P.sym.to_numpy(np.int64))
        log.info("POOL keys: %d (%s)", len(pk), a.pool)

    import xgboost as xgb
    log.info("xgboost %s | device=%s", xgb.__version__, a.device)
    summary = {}
    pool_parts = []
    for f in folds:
        fidx = CUT_DATES.index(f)
        c = ms(f)
        cdt = pd.to_datetime(c + TZ, unit="ms").normalize()
        b_hi = int((cdt + pd.DateOffset(months=OOS_MONTHS)).value // 10 ** 6) - TZ
        tr_cut = c - PURGE_MS
        tp, ty = train_rows(ts_all, sym_all, L, tr_cut)
        assert len(tp) >= 5000 and len(np.unique(ty)) == 2, "fold %d train it" % fidx
        ts_max = int(ts_all[tp].max())
        assert ts_max < c, "LEAK fold %d" % fidx
        assert ts_max <= tr_cut, "PURGE VI PHAM fold %d" % fidx
        lo = int(np.searchsorted(ts_all, c, "left"))
        hi = int(np.searchsorted(ts_all, b_hi, "left"))
        assert hi > lo, "fold %d OOS rong" % fidx
        pos = float(ty.mean())
        spw = (1 - pos) / max(pos, 1e-6)
        Xtr = np.asarray(X[tp])
        clf = xgb.XGBClassifier(n_estimators=a.nest, max_depth=5, learning_rate=0.05,
                                subsample=0.8, colsample_bytree=0.8, min_child_weight=20,
                                scale_pos_weight=spw, eval_metric="auc", n_jobs=a.njobs,
                                tree_method="hist", random_state=a.seed, device=a.device)
        clf.fit(Xtr, ty, verbose=False)
        del Xtr
        if a.save_model:
            clf.save_model(os.path.join(a.out_dir, "model_f%d_%s.json" % (fidx, a.tag)))
        log.info("fold %d %s: train %d (ts_max=%s <= purge_end=%s) pos=%.4f spw=%.6f",
                 fidx, f, len(tp), pd.to_datetime(ts_max, unit="ms"),
                 pd.to_datetime(tr_cut, unit="ms"), pos, spw)
        ts_o = ts_all[lo:hi]
        sym_o = sym_all[lo:hi]
        if pk is not None:
            ko = ts_o.astype(np.int64) * KMUL + sym_o.astype(np.int64)
            ipos = np.clip(np.searchsorted(pk, ko), 0, len(pk) - 1)
            sel = pk[ipos] == ko
            idx = np.flatnonzero(sel)
        else:
            idx = np.arange(hi - lo)
        Xsub = np.asarray(X[lo:hi])
        Xoo = Xsub if len(idx) == (hi - lo) else Xsub[idx]
        del Xsub
        pv = clf.predict_proba(Xoo)[:, 1].astype(np.float32)
        del Xoo, clf
        pool_parts.append(pd.DataFrame({"ts": ts_o[idx], "sym": sym_o[idx].astype(np.int32),
                                        "p": pv, "fold": np.int16(fidx)}))
        shab = None
        if a.out_bins and len(idx) == (hi - lo):
            outp = os.path.join(a.out_dir, "predict_wf_%s.bin" % f)
            write_bin(outp, ts_o, sym_o, pv)
            shab = sha256(outp)
        summary[f] = {"fold_idx": fidx, "n_train": int(len(tp)), "pos": pos, "spw": spw,
                      "ts_max": str(pd.to_datetime(ts_max, unit="ms")),
                      "purge_end": str(pd.to_datetime(tr_cut, unit="ms")),
                      "n_oos_all": int(hi - lo), "n_oos_pool": int(len(idx)),
                      "p_mean": float(pv.mean()), "p_std": float(pv.std()),
                      "p10": float(np.percentile(pv, 10)), "p50": float(np.percentile(pv, 50)),
                      "p90": float(np.percentile(pv, 90)), "sha_bin": shab}
        log.info("fold %d %s pool=%d/%d p_mean=%.6f p_std=%.6f p10/50/90=%.4f/%.4f/%.4f",
                 fidx, f, len(idx), hi - lo, float(pv.mean()), float(pv.std()),
                 summary[f]["p10"], summary[f]["p50"], summary[f]["p90"])
        del pv
    del X
    if not a.keep_scratch:
        try:
            os.remove(mm)
        except OSError:
            pass
    PP = pd.concat(pool_parts, ignore_index=True)
    op = os.path.join(a.out_dir, "pool_%s.parquet" % a.tag)
    PP.to_parquet(op, index=False)
    log.info("POOL PRED -> %s rows=%d sha256=%s", op, len(PP), sha256(op))
    meta = {"tag": a.tag, "pipeline_version": PIPELINE_VERSION, "label_mode": a.label_mode,
            "label_h": a.label_h, "thr": a.thr, "base_rate_label": base_rate,
            "n_label_rows": n_lab, "device": a.device, "njobs": a.njobs, "seed": a.seed,
            "nest": a.nest, "xgb": xgb.__version__, "purge_steps": PURGE_STEPS,
            "oos_months": OOS_MONTHS, "grid_min": GRID_MIN, "n_pool_rows": int(len(PP)),
            "pool_sha256": sha256(op), "folds": summary,
            "minutes": round((time.time() - t00) / 60, 1)}
    with open(os.path.join(a.out_dir, "g5_summary_%s.json" % a.tag), "w") as fo:
        json.dump(meta, fo, indent=1)
    log.info("DONE %.1f phut -> %s", (time.time() - t00) / 60, a.out_dir)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        raise
