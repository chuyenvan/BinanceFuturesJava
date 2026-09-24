#!/usr/bin/env python3
"""g015_net_train_add.py — BAN MO RONG cua `g015_net_train.py` cho STAGE 2 (them COT o CUOI vector).

Sinh ra bang: copy NGUYEN VAN `research/pipeline/g015_net_train.py` (sha256 goc
`b48c4812e905ae7909d578c5a4be0f9a188461c163ea121fe17e24a2a81d0bc8` = `train/g015_net_train_v0_snapshot.py`)
roi sua DUNG 4 diem, ghi ro o day:
  (1) them hang so NF_BASE/ADD_REAL/ADD_NOISE ; NF = 45 hoac 55 luc chay;
  (2) `--add-feats <parquet>`: gan 5 cot THAT (idx 45..49) tu parquet (join theo key `ts*1024+symId`)
      + 5 cot NHIEU (idx 50..54) sinh trong kernel voi DUNG NaN-mask cua 5 cot that (assert 100%);
  (3) `--arms "TAG:drop_cols;..."`: train NHIEU bien the tren CUNG mot lan dung ma tran
      (V0 = moc PHAI cung buoi/kernel voi cac bien the khac — PREREG_STAGE2_FEATVAR §6);
  (4) `--out-root <dir>`: moi arm ghi vao `<out-root>/<TAG>/`.
Mac dinh KHONG co `--add-feats` va KHONG co `--arms` => hanh vi GOC y nguyen (NF=45, 1 arm, 1 out-dir).

Pre-reg: docs/prereg/PREREG_STAGE2_FEATVAR.md. KHONG cham ONNX/NUM_FEATURES/extractFeatures45/LIVE.
KHONG sim. Moi thu khac (nhan, fold, purge, seed, hyperparam, write_bin) GIU Y NGUYEN ban goc.

--- docstring goc ---
g015_net_train.py — TRAINER tai dung cua `predwf_G015x26` (= net015).

Ban SAO cua `research/pipeline/g72_train.py`, chi doi DUNG hai phan:
  (1) NHAN: `y = (retEnd_4h > NET_THR)` voi NET_THR = 0.015  (LABEL_MODE=net)
      thay cho `y = (maxFav_4h >= 0.06)` cua g72. Base rate 4h = 0.1849 (khong phai 0.0457).
  (2) HYPERPARAM/WFO: 18 cutoff 20220101..20260401 (FIRST_CUTOFF=20220101, OOS_MONTHS=3,
      PURGE_STEPS=288 buoc x 15m = 72h, TZ=+7h), luu model per-fold, chon device.

Nguon cua recipe (KHONG doan): `docs/experiment/G015_RECIPE.md` muc 2. Rut tu
  - log kernel goc `claudedata/predwf_G015/selector-15mtr-pred15-net015-gpu.log`
  - 18 model JSON `claudedata/predwf_G015/model_f{0..17}_4h.json`
  - kernel stage `kB15/net008/selector-15mtr-pred15-net008-gpu.py` (mtime 2026-08-14 14:04)
  - ban trainer con giu `claudedata/gen_funding_wf_predictions_1m.py` (2026-08-10)

Trainer goc ban 2026-08-14 DA MAT (xem `docs/experiment/G3_X26_RECOVERY.md` muc 8). Day la ban TAI DUNG.
Script nay TRAIN THAT. Muon chi PREDICT lai tu 18 model da luu -> `g015x26_train.py`.

DUONG BUILD FEATURE: memory-light (merge_asof chi tren (ts,symId) + 5 cot OI, 40 cot Tool1
gather bang ridx) — da chung minh byte-identical voi duong 45-cot-pandas o fold 20240101
(`docs/experiment/G3_X26_RECOVERY.md` muc 6.1). Ly do: Oracle 23 GB bi OOM-kill im lang o duong nang.

CHAY:
  python3 g015_net_train.py --fold 20240101 --device cuda --save-model --out-dir /duong/dan
  python3 g015_net_train.py --fold all --device cpu --out-dir /duong/dan
"""
import argparse, ctypes, gc, glob, hashlib, json, logging, os, struct, sys, time
import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("g015net")
sys.path.insert(0, os.environ.get("SEL1M_CODE", "/home/ubuntu/sel1m_code"))
from tool1_col import read_tool1
import funding_label_pb as FLPB

PIPELINE_VERSION = "wfo-selector-v2-1m-canonical-20260804"
# Duong dan mac dinh = Oracle. Override qua env de chay o noi khac (vd Kaggle /kaggle/input).
T1_DIR = os.environ.get("T1_DIR", "/home/ubuntu/ds_feat15m")
LB_DIR = os.environ.get("LB_DIR", "/home/ubuntu/label_15m")
OI_FILE = os.environ.get("OI_FILE", "/home/ubuntu/claudedata/oi/oi_percoin_full.bin")
MAP_CSV = os.environ.get("MAP_CSV", "/home/ubuntu/claudedata/oi/symbol_map.csv")
SEL1M_CODE = os.environ.get("SEL1M_CODE", "/home/ubuntu/sel1m_code")

GRID_MIN = int(os.environ.get("GRID_MIN", "15"))
GRID_MS = GRID_MIN * 60_000
TZ = 7 * 3_600_000
OI_TOL = 2 * 3_600_000
PURGE_STEPS = 288
PURGE_MS = PURGE_STEPS * GRID_MS
OOS_MONTHS = 3
H_BASE_MIN = {"4h": 240}
NEED = H_BASE_MIN["4h"] // GRID_MIN          # 16 buoc
OI_NAMES = ["oi_delta24h", "oi_z", "ls_global", "ls_toptrader", "taker_buy"]
OI_DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("oi", ">f4", 5)])
NF = 45
# --- STAGE 2 (PREREG_STAGE2_FEATVAR §1): cot APPEND vao CUOI vector -------------------------
NF_BASE = 45
ADD_REAL = [45, 46, 47, 48, 49]
ADD_NOISE = [50, 51, 52, 53, 54]
ADD_NAMES = ["rvol7d", "mom30d", "mom7d", "daysSinceHigh30D", "oi_delta7d"]
NOISE_SEED = 20260924          # seed sinh nhieu (KHAC seed 42 cua train) — PREREG §3(d)
ADD_FILE = ""                  # --add-feats ; rong = khong them cot (hanh vi goc)
ADD_TAB = None                 # (key da sort, values float32) — nap MOT lan
ADD_HITS = []                  # [(so dong khop, so dong nam)] theo tung nam
BASE_SHA = "b48c4812e905ae7909d578c5a4be0f9a188461c163ea121fe17e24a2a81d0bc8"  # g015_net_train.py goc


def load_add_table(path):
    """Nap parquet cot APPEND (ts, symId, 5 cot) -> (key da sort, values float32).
    Join theo key `ts*1024 + symId` giong `train_rows` (KHONG merge_asof) => KHONG doi tap dong."""
    import pyarrow.parquet as pq
    d = pq.read_table(path, columns=["ts", "symId"] + ADD_NAMES).to_pandas()
    key = d.ts.to_numpy(np.int64) * 1024 + d.symId.to_numpy(np.int64)
    o = np.argsort(key, kind="stable")
    key = key[o]
    assert not np.any(np.diff(key) == 0), "prefeat co (ts,symId) trung"
    V = d[ADD_NAMES].to_numpy(np.float32)[o]
    log.info("ADD-FEATS %s: %d dong %s | nan_rate=%s", os.path.basename(path), len(key),
             ADD_NAMES, np.round(np.isnan(V).mean(0), 4).tolist())
    return key, V


def add_columns(Xy, ts_row, sym_row, yidx):
    """Gan cot 45..49 (that, tu parquet) + 50..54 (nhieu dung DUNG mask cua 45..49) vao Xy."""
    keyp, V = ADD_TAB
    n = len(ts_row)
    key = ts_row.astype(np.int64) * 1024 + sym_row.astype(np.int64)
    ip = np.clip(np.searchsorted(keyp, key), 0, len(keyp) - 1)
    hit = keyp[ip] == key
    vals = np.full((n, len(ADD_REAL)), np.float32("nan"), dtype=np.float32)
    vals[hit] = V[ip[hit]]
    Xy[:, ADD_REAL] = vals
    ADD_HITS.append((int(hit.sum()), int(n)))
    for j, ci in enumerate(ADD_REAL):
        rng = np.random.default_rng([NOISE_SEED, yidx, j])
        v = rng.standard_normal(n).astype(np.float32)
        m = np.isnan(Xy[:, ci])
        v[m] = np.float32("nan")
        Xy[:, ADD_NOISE[j]] = v
        assert np.array_equal(np.isnan(Xy[:, ADD_NOISE[j]]), m), \
            "MASK NHIEU LECH cot %d nam %d" % (ci, yidx)
    return int(hit.sum())


CUT_DATES = ["20210401", "20210701", "20211001",  # DEV2021 (docs/prereg/PREREG_DEV2021.md): fold 2021 moi
             "20220101", "20220401", "20220701", "20221001", "20230101", "20230401",
             "20230701", "20231001", "20240101", "20240401", "20240701", "20241001",
             "20250101", "20250401", "20250701", "20251001", "20251231", "20260101", "20260401"]
NEST, SEED = 400, 42


def ms(datestr):
    """YYYYMMDD -> epoch ms cua 00:00 GMT+7 (dung quy uoc cutoff cua pipeline goc)."""
    d = pd.Timestamp("%s-%s-%s" % (datestr[:4], datestr[4:6], datestr[6:8]), tz="UTC")
    return int(d.value // 10 ** 6) - TZ


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 24), b""):
            h.update(b)
    return h.hexdigest()


def years_needed(hi_ms):
    """Cac nam Tool1 phai doc: tu 2021 den nam chua (hi_ms - 1)."""
    y0 = 2021
    y1 = int(pd.to_datetime(hi_ms - 1, unit="ms").year)
    return [str(y) for y in range(y0, y1 + 1)]


def build_matrix(years, scratch):
    """Dung ma tran feature 45 cot cho cac nam yeu cau, ghi ra memmap tren dia.
    Tra ve (X_memmap, ts_all, sym_all, path). Duong memory-light (ridx gather)."""
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
        Xy[:, 40:NF_BASE] = mg[OI_NAMES].to_numpy(np.float32)
        if ADD_FILE:
            add_columns(Xy, mg["ts"].to_numpy(np.int64), mg["symId"].to_numpy(np.int32), len(ts_p))
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


def load_labels(mode, thr, hi_ms):
    """NHAN. mode='net' -> y = (retEnd_4h > thr)   [= recipe THAT cua x26]
              mode='maxfav' -> y = (maxFav_4h >= thr)  [= recipe cua predwf_G015_v2 / g72]
    Loc chung: nBars_4h >= 16 va cot nhan notna (y het pipeline goc)."""
    col = "retEnd_4h" if mode == "net" else "maxFav_4h"
    fs = sorted(glob.glob(LB_DIR + "/funding_label_*.pb"))
    fs = [f for f in fs if os.path.basename(f).split("_")[2] < "20260701"]
    m0 = FLPB.meta(fs[0])
    assert int(m0["step_min"]) == GRID_MIN, "LABEL step != %d" % GRID_MIN
    log.info("Label meta OK (tu file .pb): step_min=%d, scale=%d, horizons=%s, %d file",
             m0["step_min"], m0["scale"], m0["horizons"], len(fs))
    smap = pd.read_csv(MAP_CSV)
    s2i = dict(zip(smap.symbol, smap.symId.astype(np.int32)))
    parts, tot = [], 0
    for fp in fs:
        d = FLPB.read_label(fp, usecols=["tEpochMs", "symbol", col, "nBars_4h"])
        tot += len(d)
        d = d[(d["nBars_4h"] >= NEED) & d[col].notna()]
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
    log.info("Label 4h (%s thr=%.4f): %d rows | base=%.4f", mode, thr, len(L), float(L.y.mean()))
    return L


def train_rows(ts_all, sym_all, L, tr_cut):
    """Vi tri cac dong feature co nhan va ts < tr_cut, GIU THU TU VI TRI (= thu tu ts tang dan)
    — khop `tr_meta.merge(labels, how='inner')` cua pipeline goc (merge giu thu tu frame TRAI)."""
    key = ts_all * 1024 + sym_all.astype(np.int64)
    srt = np.argsort(key, kind="stable")
    ks = key[srt]
    assert not np.any(np.diff(ks) == 0), "Xall trung (ts,symId)"
    kl = L.ts.to_numpy(np.int64) * 1024 + L.symId.to_numpy(np.int64)
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


def parse_arms(s):
    """'V0:0,1;V1:2,3' -> [('V0','0,1'),('V1','2,3')]. 'V0:' = khong bo cot nao."""
    out = []
    for part in s.split(";"):
        part = part.strip()
        if not part:
            continue
        tag, _, dc = part.partition(":")
        out.append((tag.strip(), dc.strip()))
    assert out, "arms rong"
    return out


def main():
    global ADD_FILE, ADD_TAB, NF
    ap = argparse.ArgumentParser(description="Trainer net015 + cot APPEND (Stage 2)")
    ap.add_argument("--fold", default="20240101",
                    help="cutoff YYYYMMDD, danh sach ngan cach dau phay, hoac 'all'")
    ap.add_argument("--device", default="cpu", choices=["cpu", "cuda"],
                    help="XGB_DEVICE. Ban goc x26 chay 'cuda' (Kaggle GPU)")
    ap.add_argument("--out-dir", default="/home/ubuntu/g4/net015_out")
    ap.add_argument("--out-root", default="", help="STAGE2: moi arm ghi vao <out-root>/<TAG>/")
    ap.add_argument("--scratch", default=None, help="mac dinh = <out-root|out-dir>/scratch")
    ap.add_argument("--save-model", action="store_true", help="luu model_f<i>_4h.json")
    ap.add_argument("--label-mode", default="net", choices=["net", "maxfav"])
    ap.add_argument("--thr", type=float, default=0.015, help="NET_THR (net) hoac WIN (maxfav)")
    ap.add_argument("--njobs", type=int, default=int(os.environ.get("G015_NJOBS", "-1")))
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--nest", type=int, default=NEST)
    ap.add_argument("--keep-scratch", action="store_true")
    ap.add_argument("--drop-cols", default="",
                    help="G015ABL: chi so cot BO khoi X truoc khi train/predict, cach nhau dau phay. "
                         "Mac dinh rong = giu du cot (honh vi goc khi khong --add-feats).")
    ap.add_argument("--add-feats", default="",
                    help="STAGE2: parquet (ts, symId, 5 cot) -> gan cot 45..49 + nhieu 50..54 (cung mask). "
                         "Rong = KHONG them cot (NF=45, hanh vi goc).")
    ap.add_argument("--arms", default="",
                    help="STAGE2: 'TAG:drop_cols;TAG2:drop_cols2' -> train nhieu bien the tren CUNG "
                         "mot lan dung ma tran (moc V0 phai cung kernel). Rong = 1 arm (--drop-cols).")
    a = ap.parse_args()

    ADD_FILE = a.add_feats
    NF = NF_BASE + (len(ADD_REAL) + len(ADD_NOISE) if ADD_FILE else 0)
    arms = parse_arms(a.arms) if a.arms else [("", a.drop_cols)]
    arm_keep = {}
    for tag, dc in arms:
        ds = set(int(x) for x in dc.split(",") if x.strip() != "")
        assert all(0 <= i < NF for i in ds), "drop-cols phai trong [0,%d)" % NF
        arm_keep[tag] = (ds, [i for i in range(NF) if i not in ds])
        log.info("ARM %s: drop=%s -> giu %d/%d cot", tag or "(single)", sorted(ds),
                 len(arm_keep[tag][1]), NF)
    if ADD_FILE:
        ADD_TAB = load_add_table(ADD_FILE)

    t00 = time.time()
    folds = CUT_DATES if a.fold == "all" else [x.strip() for x in a.fold.split(",") if x.strip()]
    for f in folds:
        assert f in CUT_DATES, "fold %s khong nam trong cutoff" % f
    root = a.out_root or a.out_dir
    os.makedirs(root, exist_ok=True)
    scratch = a.scratch or os.path.join(root, "scratch")
    os.makedirs(scratch, exist_ok=True)
    log.info("PIPELINE_VERSION=%s | GRID_MIN=%d | PURGE=%dh | OOS_MONTHS=%d | TZ=+%dh",
             PIPELINE_VERSION, GRID_MIN, PURGE_MS // 3_600_000, OOS_MONTHS, TZ // 3_600_000)
    log.info("STAGE2 ADD TRAIN | folds=%s device=%s njobs=%d nest=%d seed=%d label=%s thr=%.4f "
             "NF=%d add=%s arms=%d", folds, a.device, a.njobs, a.nest, a.seed, a.label_mode, a.thr,
             NF, os.path.basename(a.add_feats), len(arms))

    hi_all = 0
    for f in folds:
        c = ms(f)
        cdt = pd.to_datetime(c + TZ, unit="ms").normalize()
        hi_all = max(hi_all, int((cdt + pd.DateOffset(months=OOS_MONTHS)).value // 10 ** 6) - TZ)
    yrs = years_needed(hi_all)
    X, ts_all, sym_all, mm = build_matrix(yrs, scratch)
    if ADD_FILE:
        tot_hit = sum(h for h, _ in ADD_HITS)
        tot_row = sum(n for _, n in ADD_HITS)
        log.info("ADD-FEATS hit tong: %d/%d = %.4f (theo nam %s)", tot_hit, tot_row,
                 tot_hit / max(tot_row, 1), ADD_HITS)
    L = load_labels(a.label_mode, a.thr, hi_all)

    import xgboost as xgb
    log.info("xgboost %s | device=%s", xgb.__version__, a.device)
    ALL = {}
    for tag, dc in arms:
        drop_set, keep_idx = arm_keep[tag]
        out_dir = os.path.join(root, tag) if tag else a.out_dir
        os.makedirs(out_dir, exist_ok=True)
        summary = {}
        for f in folds:
            fidx = CUT_DATES.index(f)
            c = ms(f)
            cdt = pd.to_datetime(c + TZ, unit="ms").normalize()
            b_hi = int((cdt + pd.DateOffset(months=OOS_MONTHS)).value // 10 ** 6) - TZ
            tr_cut = c - PURGE_MS
            tp, ty = train_rows(ts_all, sym_all, L, tr_cut)
            assert len(tp) >= 5000 and len(np.unique(ty)) == 2, "fold %d train it" % fidx
            assert int(ts_all[tp].max()) < c, "LEAK fold %d" % fidx
            lo = int(np.searchsorted(ts_all, c, "left"))
            hi = int(np.searchsorted(ts_all, b_hi, "left"))
            assert hi > lo, "fold %d OOS rong" % fidx
            pos = float(ty.mean())
            spw = (1 - pos) / max(pos, 1e-6)
            Xtr = np.asarray(X[tp])[:, keep_idx]
            clf = xgb.XGBClassifier(n_estimators=a.nest, max_depth=5, learning_rate=0.05,
                                    subsample=0.8, colsample_bytree=0.8, min_child_weight=20,
                                    scale_pos_weight=spw, eval_metric="auc", n_jobs=a.njobs,
                                    tree_method="hist", random_state=a.seed, device=a.device)
            clf.fit(Xtr, ty, verbose=False)
            del Xtr
            if a.save_model:
                mp = os.path.join(out_dir, "model_f%d_4h.json" % fidx)
                clf.save_model(mp)
                log.info("arm %s fold %d 4h: SAVED model -> %s", tag, fidx, os.path.basename(mp))
            log.info("arm %s fold %d 4h: train %d (ts_max=%s<cutoff) pos=%.4f spw=%.6f nfeat=%d",
                     tag, fidx, len(tp), pd.to_datetime(int(ts_all[tp].max()), unit="ms"), pos, spw,
                     len(keep_idx))
            Xoo = np.asarray(X[lo:hi])[:, keep_idx]
            pv = clf.predict_proba(Xoo)[:, 1].astype(np.float32)
            del Xoo, clf
            outp = os.path.join(out_dir, "predict_wf_%s.bin" % f)
            write_bin(outp, ts_all[lo:hi], sym_all[lo:hi], pv)
            summary[f] = {"fold_idx": fidx, "n_train": int(len(tp)), "pos": pos, "spw": spw,
                          "n_oos": int(hi - lo), "p_mean": float(pv.mean()),
                          "p_std": float(pv.std()), "sha_bin": sha256(outp)}
            log.info("arm %s fold %d %s p_mean=%.6f p_std=%.6f n_oos=%d", tag, fidx, f,
                     float(pv.mean()), float(pv.std()), int(hi - lo))
            del pv
            gc.collect()
            try:
                ctypes.CDLL("libc.so.6").malloc_trim(0)
            except Exception:
                pass
        meta = {"pipeline_version": PIPELINE_VERSION, "label_mode": a.label_mode, "thr": a.thr,
                "device": a.device, "njobs": a.njobs, "seed": a.seed, "nest": a.nest,
                "xgb": xgb.__version__, "purge_steps": PURGE_STEPS, "oos_months": OOS_MONTHS,
                "grid_min": GRID_MIN, "folds": summary, "drop_cols": sorted(drop_set),
                "keep_idx": keep_idx, "num_feature": len(keep_idx), "arm": tag,
                "add_feats": a.add_feats, "add_names": ADD_NAMES if ADD_FILE else [],
                "noise_seed": NOISE_SEED if ADD_FILE else None, "base_trainer_sha256": BASE_SHA,
                "minutes": round((time.time() - t00) / 60, 1)}
        with open(os.path.join(out_dir, "net_train_summary.json"), "w") as fo:
            json.dump(meta, fo, indent=1)
        ALL[tag] = meta
        log.info("ARM %s DONE (%.1f phut) -> %s", tag, (time.time() - t00) / 60, out_dir)

    # ---- CROSS-ARM CHECK (PREREG §3(a)): n_train/pos/spw/n_oos PHAI khop tuyet doi voi moc ----
    mism = {}
    tags = [t for t, _ in arms]
    base = tags[0]
    for f in folds:
        b = ALL[base]["folds"][f]
        for t in tags[1:]:
            x = ALL[t]["folds"][f]
            for k in ("n_train", "pos", "spw", "n_oos"):
                if x[k] != b[k]:
                    mism.setdefault(f, {})[t] = {k: [b[k], x[k]]}
    if mism:
        log.error("CROSS_ARM_MISMATCH (LOI CO CHE, khong phai ket qua): %s", json.dumps(mism))
    else:
        log.info("CROSS_ARM_OK: n_train/pos/spw/n_oos KHOP TUYET DOI giua %d arm x %d fold",
                 len(tags), len(folds))
    cross = {"base_arm": base, "arms": tags, "folds": folds, "mismatch": mism,
             "k_multiplicity": len(tags), "add_hits": ADD_HITS if ADD_FILE else None}
    with open(os.path.join(root, "stage2_summary.json"), "w") as fo:
        json.dump({"cross_arm": cross, "arms": {t: ALL[t] for t in tags}}, fo, indent=1)
    del X
    if not a.keep_scratch:
        try:
            os.remove(mm)
        except OSError:
            pass
    log.info("DONE %.1f phut -> %s", (time.time() - t00) / 60, root)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        raise
