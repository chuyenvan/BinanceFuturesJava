#!/usr/bin/env python3
"""gate_topk_train.py — Train lai gate G015 tren LABEL "top-K outcome".

Y tuong (huong TOPK_LABEL): thay vi train gate tren TOAN BO pool voi nhan 4h-net,
train gate CHI tren tap top-K cua S1 (moi tick lay K coin score THAP nhat), voi nhan
la KET CUC THAT g1lite: y = (g1lite > 0). Muc tieu: gate hoc phan biet trong chinh
population ma no se duoc dung (top-K S1), thay vi tren pool bat can xung.

SELF-CONTAINED. KHONG sua g015_net_train.py. Chi doc data + build feature cho ~44k
dong top-K (KHONG build full pool -> khong OOM), train XGBClassifier giu DUNG hyperparam
+ WFO + PURGE + TZ cua g015_net_train.py, ghi bins, va so AUC OOS voi gate CU.

Nguon recipe (khong doan): research/pipeline/g015_net_train.py
  - ms(), GRID_MS, TZ, OI_TOL, OI_NAMES, OI_DT, NF=45, build_matrix(), write_bin()
  - hyperparam XGB (dong ~265-268), WFO purge 288 buoc = 72h, OOS 3 thang.

CHAY:  python3 research/pipeline/g5/gate_topk_train.py
"""
import argparse, gc, glob, hashlib, json, logging, os, struct, sys, time
import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
log = logging.getLogger("gate_topk")
sys.path.insert(0, os.environ.get("SEL1M_CODE", "/home/ubuntu/sel1m_code"))
from tool1_col import read_tool1

# ---- hang so: LAY Y NGUYEN tu g015_net_train.py -------------------------------
T1_DIR = os.environ.get("T1_DIR", "/home/ubuntu/ds_feat15m")
OI_FILE = os.environ.get("OI_FILE", "/home/ubuntu/claudedata/oi/oi_percoin_full.bin")
MAP_CSV = os.environ.get("MAP_CSV", "/home/ubuntu/claudedata/oi/symbol_map.csv")

GRID_MIN = 15
GRID_MS = GRID_MIN * 60_000
TZ = 7 * 3_600_000
OI_TOL = 2 * 3_600_000
PURGE_STEPS = 288
PURGE_MS = PURGE_STEPS * GRID_MS          # 72h
OOS_MONTHS = 3
OI_NAMES = ["oi_delta24h", "oi_z", "ls_global", "ls_toptrader", "taker_buy"]
OI_DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("oi", ">f4", 5)])
NF = 45
NEST, SEED = 400, 42

# 10 cut WFO (yeu cau nhiem vu) — trung 10 file bin gate cu 2022/2023/2024
CUT_DATES = ["20220101", "20220401", "20220701", "20221001", "20230101",
             "20230401", "20230701", "20231001", "20240101", "20240401"]

# S1 pred (score thap=tot); nhan g1lite; gate cu
S1_FILES = ["/home/ubuntu/ledger/pred_s1a2x1.parquet",
            "/home/ubuntu/ledger/pred_s1a2x1_y21.parquet"]
CAND_FILE = "/home/ubuntu/ledger/cand_dev_x1.parquet"
OLDGATE_DIR = "/home/ubuntu/claudedata/predwf_G015x26"
OLDGATE_DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("p0", ">f4"),
                       ("a", ">f4"), ("b", ">f4"), ("c", ">f4")])


def ms(datestr):
    """YYYYMMDD -> epoch ms cua 00:00 GMT+7 (giong g015_net_train.ms)."""
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


def write_bin(path, ts, sid, p):
    """Giong g015_net_train.write_bin: struct '>qh4f' (ts,symId,p, 3*nan)."""
    nan = float("nan")
    with open(path, "wb") as fo:
        buf = bytearray()
        for i in range(len(ts)):
            buf += struct.pack(">qh4f", int(ts[i]), int(sid[i]), float(p[i]), nan, nan, nan)
        fo.write(buf)
        fo.flush()
        os.fsync(fo.fileno())
    log.info("ghi %s: %d rec = %d bytes", path, len(ts), len(ts) * 26)


def build_topk_labels(k, hi_ms):
    """(A) top-K outcome label. Concat 2 file S1, moi tick lay K coin score THAP nhat
    (rank method='first' ascending <= K), join g1lite, y=(g1lite>0). Loc ts < hi_ms.
    Tra DataFrame cot ts, symId, y."""
    parts = [pd.read_parquet(p, columns=["ts", "sym", "score"]) for p in S1_FILES]
    s = pd.concat(parts, ignore_index=True)
    log.info("S1: %d dong (%s), %d tick", len(s),
             " + ".join(os.path.basename(p) for p in S1_FILES), s.ts.nunique())
    s["rk"] = s.groupby("ts")["score"].rank(method="first", ascending=True)
    tk = s.loc[s.rk <= k, ["ts", "sym"]].copy()
    tk = tk[tk.ts < hi_ms]
    tk = tk.rename(columns={"sym": "symId"})
    tk["symId"] = tk["symId"].astype(np.int32)
    tk["ts"] = tk["ts"].astype(np.int64)
    c = pd.read_parquet(CAND_FILE, columns=["ts", "sym", "g1lite"])
    c = c.rename(columns={"sym": "symId"})
    c["symId"] = c["symId"].astype(np.int32)
    c["ts"] = c["ts"].astype(np.int64)
    m = tk.merge(c, on=["ts", "symId"], how="left")
    na = int(m.g1lite.isna().sum())
    if na:
        log.info("CANH BAO: %d/%d dong top-K thieu g1lite -> loai khoi nhan", na, len(m))
    m = m.dropna(subset=["g1lite"])
    m["y"] = (m["g1lite"] > 0).astype(np.int8)
    m = m[["ts", "symId", "y"]].drop_duplicates(subset=["ts", "symId"])
    log.info("top-K label (K=%d): %d dong | base y=%.4f", k, len(m), float(m.y.mean()))
    return m.reset_index(drop=True)


def build_features(topk, years):
    """(build 45 cot) CHI cho cac dong (ts,symId) trong top-K -> tranh OOM.
    Byte-giong build_matrix() cua g015_net_train: merge_asof backward tol=OI_TOL by symId,
    40 cot Tool1 (theo ridx) + 5 cot OI. Merge_asof cho tung dong left doc lap nen loc
    left truoc KHONG doi ket qua OI cua cac dong giu lai.
    Tra DataFrame ts, symId, f0..f44."""
    ao = np.memmap(OI_FILE, dtype=OI_DT, mode="r")
    smap = pd.read_csv(MAP_CSV)
    log.info("OI memmap=%d rec | build feature cho %d dong top-K | years=%s",
             len(ao), len(topk), years)
    out = []
    tot_hit = 0
    for yr in years:
        lo = int(pd.Timestamp(yr + "-01-01", tz="UTC").value // 10 ** 6)
        hi = int(pd.Timestamp(str(int(yr) + 1) + "-01-01", tz="UTC").value // 10 ** 6)
        tky = topk[(topk.ts >= lo) & (topk.ts < hi)][["ts", "symId"]]
        if len(tky) == 0:
            log.info("  nam %s: 0 dong top-K, bo qua", yr)
            continue
        a = read_tool1(os.path.join(T1_DIR, "features_%s*" % yr), grid_ms=GRID_MS)
        F = a["f"]
        t = pd.DataFrame({"ts": a["ts"].astype(np.int64),
                          "symId": a["sym"].astype(np.int32),
                          "ridx": np.arange(len(a), dtype=np.int64)})
        # loc left ve top-K TRUOC merge_asof (khong doi gia tri OI cua dong giu lai)
        t = t.merge(tky, on=["ts", "symId"], how="inner")
        # OI slice nam nay: giong build_matrix (aots>=lo-OI_TOL & aots<hi)
        aots = np.asarray(ao["ts"])
        msk = (aots >= lo - OI_TOL) & (aots < hi)
        del aots
        aoc = np.array(ao[msk])
        del msk
        o = pd.DataFrame({"ts": aoc["ts"].astype(np.int64),
                          "symId": aoc["sym"].astype(np.int32)})
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
        df = pd.DataFrame({"ts": mg["ts"].to_numpy(np.int64),
                           "symId": mg["symId"].to_numpy(np.int32)})
        for j in range(NF):
            df["f%d" % j] = Xy[:, j]
        out.append(df)
        tot_hit += n
        log.info("  nam %s: tool1=%d, top-K yeu cau=%d -> co feature=%d", yr, len(a), len(tky), n)
        del a, F, mg, Xy
        gc.collect()
    del ao
    feats = pd.concat(out, ignore_index=True).sort_values("ts").reset_index(drop=True)
    log.info("Features top-K: %d dong x %d cot (yeu cau %d, khop %d)",
             len(feats), NF, len(topk), tot_hit)
    return feats


def read_oldgate(cut):
    p = os.path.join(OLDGATE_DIR, "predict_wf_%s.bin" % cut)
    if not os.path.exists(p):
        return None
    a = np.fromfile(p, dtype=OLDGATE_DT)
    return pd.DataFrame({"ts": a["ts"].astype(np.int64),
                         "symId": a["sym"].astype(np.int32),
                         "p0": a["p0"].astype(np.float32)})


def auc(y, p):
    from sklearn.metrics import roc_auc_score
    y = np.asarray(y); p = np.asarray(p)
    m = ~np.isnan(p)
    if m.sum() < 10 or len(np.unique(y[m])) < 2:
        return float("nan"), int(m.sum())
    return float(roc_auc_score(y[m], p[m])), int(m.sum())


def main():
    ap = argparse.ArgumentParser(description="Gate G015 train tren top-K outcome label")
    ap.add_argument("--out-dir", default="/home/ubuntu/gate_topk")
    ap.add_argument("--k", type=int, default=8)
    a = ap.parse_args()
    t00 = time.time()
    os.makedirs(a.out_dir, exist_ok=True)

    import xgboost as xgb
    log.info("gate_topk_train | K=%d | out=%s | xgb=%s | sklearn AUC", a.k, a.out_dir, xgb.__version__)
    log.info("WFO %d cut | PURGE=%dh | OOS=%d thang | TZ=+%dh | NF=%d",
             len(CUT_DATES), PURGE_MS // 3_600_000, OOS_MONTHS, TZ // 3_600_000, NF)

    hi_all = 0
    for f in CUT_DATES:
        c = ms(f)
        cdt = pd.to_datetime(c + TZ, unit="ms").normalize()
        hi_all = max(hi_all, int((cdt + pd.DateOffset(months=OOS_MONTHS)).value // 10 ** 6) - TZ)
    yrs = years_needed(hi_all)

    # (A) label top-K
    topk = build_topk_labels(a.k, hi_all)
    # build feature chi cho top-K
    feats = build_features(topk, yrs)
    # gan nhan y vao feature (moi dong feature deu la top-K)
    df = feats.merge(topk, on=["ts", "symId"], how="inner").sort_values("ts").reset_index(drop=True)
    log.info("Ma tran train/OOS top-K: %d dong (co feature + co nhan)", len(df))
    ts_all = df["ts"].to_numpy(np.int64)
    sym_all = df["symId"].to_numpy(np.int32)
    y_all = df["y"].to_numpy(np.int8)
    X_all = df[["f%d" % j for j in range(NF)]].to_numpy(np.float32)
    assert np.all(np.diff(ts_all) >= 0), "ts khong tang dan"

    # (B)+(C) train + bins theo fold; (D) danh gia
    rows = []           # bang so sanh
    oos_all_p, oos_all_y, oos_all_ts = [], [], []
    old_all_p, old_all_y, old_all_ts = [], [], []
    summary = {"k": a.k, "xgb": xgb.__version__, "cuts": CUT_DATES, "folds": {}}

    for f in CUT_DATES:
        fidx = CUT_DATES.index(f)
        c = ms(f)
        cdt = pd.to_datetime(c + TZ, unit="ms").normalize()
        b_hi = int((cdt + pd.DateOffset(months=OOS_MONTHS)).value // 10 ** 6) - TZ
        tr_cut = c - PURGE_MS
        tr = np.flatnonzero(ts_all < tr_cut)
        oo = np.flatnonzero((ts_all >= c) & (ts_all < b_hi))
        if len(tr) < 5000 or len(oo) == 0 or len(np.unique(y_all[tr])) < 2:
            log.info("fold %d %s: BO (train=%d, oos=%d)", fidx, f, len(tr), len(oo))
            continue
        assert int(ts_all[tr].max()) < c, "LEAK fold %d" % fidx
        pos = float(y_all[tr].mean())
        spw = (1 - pos) / max(pos, 1e-6)
        clf = xgb.XGBClassifier(n_estimators=NEST, max_depth=5, learning_rate=0.05,
                                subsample=0.8, colsample_bytree=0.8, min_child_weight=20,
                                scale_pos_weight=spw, eval_metric="auc", n_jobs=-1,
                                tree_method="hist", random_state=SEED, device="cpu")
        clf.fit(X_all[tr], y_all[tr], verbose=False)
        p = clf.predict_proba(X_all[oo])[:, 1].astype(np.float32)
        yo = y_all[oo]
        outp = os.path.join(a.out_dir, "predict_wf_%s.bin" % f)
        write_bin(outp, ts_all[oo], sym_all[oo], p)
        au_new, _ = auc(yo, p)

        # gate CU tren CUNG population top-K OOS
        old = read_oldgate(f)
        au_old, n_old = (float("nan"), 0)
        if old is not None:
            oj = pd.DataFrame({"ts": ts_all[oo], "symId": sym_all[oo], "y": yo}) \
                .merge(old, on=["ts", "symId"], how="left")
            au_old, n_old = auc(oj["y"].to_numpy(), oj["p0"].to_numpy())
            old_all_p.append(oj["p0"].to_numpy()); old_all_y.append(oj["y"].to_numpy())
            old_all_ts.append(ts_all[oo])

        rows.append((fidx, f, len(tr), len(oo), float(yo.mean()), au_new, au_old, n_old))
        oos_all_p.append(p); oos_all_y.append(yo); oos_all_ts.append(ts_all[oo])
        summary["folds"][f] = {"fold_idx": fidx, "n_train": int(len(tr)),
                               "n_oos": int(len(oo)), "base_rate": float(yo.mean()),
                               "pos_train": pos, "spw": spw, "auc_new": au_new,
                               "auc_old": au_old, "n_old_matched": int(n_old),
                               "sha_bin": sha256(outp)}
        log.info("fold %d %s: train=%d oos=%d base=%.4f AUC_new=%.4f AUC_old=%.4f",
                 fidx, f, len(tr), len(oo), float(yo.mean()), au_new, au_old)
        del clf, p
        gc.collect()

    # tong hop
    yv = np.concatenate(oos_all_y); pv = np.concatenate(oos_all_p); tv = np.concatenate(oos_all_ts)
    au_new_tot, _ = auc(yv, pv)
    if old_all_y:
        yo2 = np.concatenate(old_all_y); po2 = np.concatenate(old_all_p); to2 = np.concatenate(old_all_ts)
        au_old_tot, n_old_tot = auc(yo2, po2)
    else:
        yo2 = po2 = to2 = np.array([]); au_old_tot, n_old_tot = float("nan"), 0

    def by_year(ts, y, p):
        yr = pd.to_datetime(ts, unit="ms").year
        r = {}
        for Y in sorted(set(yr)):
            m = yr == Y
            r[int(Y)] = auc(y[m], p[m])[0]
        return r

    yr_new = by_year(tv, yv, pv)
    yr_old = by_year(to2, yo2, po2) if len(to2) else {}

    log.info("")
    log.info("================ BANG SO SANH AUC OOS top-K (gate MOI vs CU) ================")
    log.info("%-5s %-9s %8s %8s %9s %9s %9s %8s", "fold", "cut", "n_train", "n_oos",
             "base_y", "AUC_new", "AUC_old", "n_old")
    for (fi, cut, ntr, noo, br, an, ao_, nold) in rows:
        log.info("%-5d %-9s %8d %8d %9.4f %9.4f %9.4f %8d", fi, cut, ntr, noo, br, an, ao_, nold)
    log.info("%-15s %8s %8d %9.4f %9.4f %9.4f %8d", "TONG", "", len(yv),
             float(yv.mean()), au_new_tot, au_old_tot, n_old_tot)
    log.info("")
    log.info("Theo NAM  AUC_new: %s", {y: round(v, 4) for y, v in yr_new.items()})
    log.info("Theo NAM  AUC_old: %s", {y: round(v, 4) for y, v in yr_old.items()})

    summary["auc_new_total"] = au_new_tot
    summary["auc_old_total"] = au_old_tot
    summary["n_old_matched_total"] = int(n_old_tot)
    summary["base_rate_total"] = float(yv.mean())
    summary["auc_new_by_year"] = {int(y): v for y, v in yr_new.items()}
    summary["auc_old_by_year"] = {int(y): v for y, v in yr_old.items()}
    sp = os.path.join(a.out_dir, "summary.json")
    with open(sp, "w") as fo:
        json.dump(summary, fo, indent=1)
    log.info("summary -> %s", sp)
    log.info("thoi gian: %.1f phut", (time.time() - t00) / 60)
    log.info("DONE")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        raise
