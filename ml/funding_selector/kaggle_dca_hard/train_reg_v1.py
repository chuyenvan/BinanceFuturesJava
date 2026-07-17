#!/usr/bin/env python3
# TASK-157 — Label reward-penalty cho che do DCA-CUNG (thuong cham +3%/4h, phat theo do am tai moc 4h).
#   U = X_REWARD                     neu maxFav_4h >= 0.03 (nBars_4h >= 16)
#   U = y * min(retEnd_4h, 0)        neu khong hit (ve hoa/duong -> 0, khong phat)
# Train 4 model CUNG data/split: binary(maxFav3, baseline = label v6 task 155) + reg(U) voi y in {1.0,1.5,2.0}.
# Do edge tren TEST 12 thang: top-5 moi ky-4h khong chong lan (methodology task 153) + random baseline.
# U_eval CO DINH (x=0.02, y=1.5) cho MOI model — tach label train khoi thuoc do.
# Kaggle: dataset tu giai nen .gz -> .bin; mount thay doi -> glob de quy, khong hardcode path.
import os, glob

def find1(p):
    m = sorted(glob.glob(p, recursive=True))
    assert m, f"KHONG TIM THAY: {p}"
    return m[0]

os.environ.setdefault("TOOL1_GLOB", "/kaggle/input/**/ff_*.bin")
os.environ.setdefault("OI_FILE", find1("/kaggle/input/**/oi_percoin_full.bin") if glob.glob("/kaggle/input/**/oi_percoin_full.bin", recursive=True) else "")
os.environ.setdefault("LABEL_CSV", find1("/kaggle/input/**/funding_label.csv") if glob.glob("/kaggle/input/**/funding_label.csv", recursive=True) else "")
os.environ.setdefault("MAP_CSV", find1("/kaggle/input/**/symbol_map.csv") if glob.glob("/kaggle/input/**/symbol_map.csv", recursive=True) else "")
os.environ.setdefault("OUT_DIR", "/kaggle/working")

import gzip, json, logging
import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("dca_hard_157")

# ===== Hang so label (pre-register task 157 — KHONG doi sau khi nhin so) =====
TP = 0.03                      # nguong cham thanh cong trong 4h
X_REWARD = 0.02                # thuong khi hit: arm SL+1% -> thuc nhan ky vong ~+2% sau phi
Y_GRID = [1.0, 1.5, 2.0]       # he so phat do am tai moc 4h (DCA cung nhan doi exposure)
EVAL_X, EVAL_Y = 0.02, 1.5     # utility CO DINH de cham diem moi model
H_MS = 4 * 3600 * 1000         # ky = block 4h khong chong lan
NEED_BARS = 16                 # nBars_4h >= 16 (du cua so 4h tren luoi 15m)
TOPN = 5
RANDOM_REPS = 20
GRID_MS = 15 * 60 * 1000
OI_NAMES = ["oi_delta24h", "oi_z", "ls_global", "ls_toptrader", "taker_buy"]
FEAT = [f"f{j}" for j in range(40)] + OI_NAMES

TOOL1_DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("f", ">f4", 40)])
OI_DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("oi", ">f4", 5)])

TOOL1_GLOB = os.environ["TOOL1_GLOB"]
OI_FILE = os.environ["OI_FILE"]
LABEL_CSV = os.environ["LABEL_CSV"]
MAP_CSV = os.environ["MAP_CSV"]
OUT_DIR = os.environ.get("OUT_DIR", ".")
OI_TOL_MS = int(os.environ.get("OI_TOL_MS", str(2 * 60 * 60 * 1000)))
SEED = int(os.environ.get("SEED", "42"))
SMOKE = os.environ.get("SMOKE", "0") == "1"
N_ESTIMATORS = int(os.environ.get("N_ESTIMATORS", "400"))
os.makedirs(OUT_DIR, exist_ok=True)


def _read(path, dt, item, grid=False):
    raw = open(path, "rb").read()
    if path.endswith(".gz"):
        raw = gzip.decompress(raw)
    assert len(raw) % item == 0, f"{path}: len {len(raw)} khong chia het {item}"
    a = np.frombuffer(raw, dtype=dt)
    if grid:
        a = a[(a["ts"] % GRID_MS) == 0]
    return a


def load_tool1():
    files = sorted(glob.glob(TOOL1_GLOB, recursive=True))
    assert files, f"Tool1 khong thay: {TOOL1_GLOB}"
    parts = [_read(fp, TOOL1_DT, 170, grid=True) for fp in files]
    a = np.concatenate(parts)
    df = pd.DataFrame({"ts": a["ts"].astype(np.int64), "symId": a["sym"].astype(np.int32)})
    F = np.asarray(a["f"], dtype=np.float32)
    for j in range(40):
        df[f"f{j}"] = F[:, j]
    log.info("Tool1 (15m grid): %d rows | %d symId | ts[%s..%s]", len(df), df.symId.nunique(),
             pd.to_datetime(df.ts.min(), unit="ms"), pd.to_datetime(df.ts.max(), unit="ms"))
    return df.sort_values("ts").reset_index(drop=True)


def load_oi():
    a = _read(OI_FILE, OI_DT, 30)
    df = pd.DataFrame({"ts": a["ts"].astype(np.int64), "symId": a["sym"].astype(np.int32)})
    O = np.asarray(a["oi"], dtype=np.float32)
    for j, nm in enumerate(OI_NAMES):
        df[nm] = O[:, j]
    log.info("OI: %d rows | %d symId", len(df), df.symId.nunique())
    return df.sort_values("ts").reset_index(drop=True)


def load_labels():
    cols = ["tEpochMs", "symbol", "maxFav_4h", "retEnd_4h", "nBars_4h"]
    df = pd.read_csv(LABEL_CSV, usecols=cols, on_bad_lines="skip").rename(columns={"tEpochMs": "ts"})
    n0 = len(df)
    df = df[(df["nBars_4h"] >= NEED_BARS) & df["maxFav_4h"].notna() & df["retEnd_4h"].notna()].copy()
    df["hit"] = (df["maxFav_4h"] >= TP).astype(np.int8)
    df["loss4h"] = np.minimum(df["retEnd_4h"].values, 0.0).astype(np.float32)  # phan am tai moc DCA cung
    log.info("Label 4h: %d/%d rows hop le | base_rate(hit +3%%)=%.4f | %%fail co retEnd<0=%.4f | "
             "loss4h fail p50=%.4f p90=%.4f",
             len(df), n0, df["hit"].mean(),
             float((df.loc[df.hit == 0, "retEnd_4h"] < 0).mean()),
             float(df.loc[df.hit == 0, "loss4h"].quantile(0.50)),
             float(df.loc[df.hit == 0, "loss4h"].quantile(0.10)))
    return df[["ts", "symbol", "hit", "retEnd_4h", "loss4h"]]


def utility(hit, loss4h, x, y):
    return np.where(hit == 1, x, y * loss4h).astype(np.float32)


def build_dataset():
    t = load_tool1()
    o = load_oi()
    mp = pd.read_csv(MAP_CSV)
    merged = pd.merge_asof(t, o, on="ts", by="symId", direction="backward", tolerance=OI_TOL_MS)
    merged = merged.merge(mp, on="symId", how="left").dropna(subset=["symbol"])
    lb = load_labels()
    ds = merged.merge(lb, on=["symbol", "ts"], how="inner")
    del t, o, merged, lb
    for y in Y_GRID:
        u = utility(ds["hit"].values, ds["loss4h"].values, X_REWARD, y)
        log.info("U(x=%.2f,y=%.1f): mean=%.5f p10=%.4f p50=%.4f p90=%.4f", X_REWARD, y,
                 float(u.mean()), float(np.percentile(u, 10)), float(np.percentile(u, 50)),
                 float(np.percentile(u, 90)))
    log.info("Dataset ghep: %d rows | n_sym=%d | base_rate=%.4f", len(ds), ds.symbol.nunique(),
             float(ds.hit.mean()))
    return ds.sort_values("ts").reset_index(drop=True)


def time_split(ds):
    MO = 30 * 24 * 3600 * 1000
    test_months = int(os.environ.get("TEST_MONTHS", "12"))
    val_months = int(os.environ.get("VAL_MONTHS", "6"))
    tmax = ds.ts.max()
    test_start = tmax - test_months * MO
    val_start = test_start - val_months * MO
    purge = NEED_BARS * GRID_MS
    tr = ds[ds.ts < val_start - purge]
    va = ds[(ds.ts >= val_start) & (ds.ts < test_start - purge)]
    te = ds[ds.ts >= test_start]
    assert len(tr) and len(va) and len(te), "split rong"
    assert tr.ts.max() < va.ts.min() and va.ts.max() < te.ts.min(), "LEAK: split khong tang theo ts"
    log.info("split tr/va/te = %d/%d/%d | test tu %s", len(tr), len(va), len(te),
             pd.to_datetime(te.ts.min(), unit="ms"))
    return tr, va, te


def pick_metrics(g):
    """Cham 1 tap pick: precision hit, U_eval trung binh, do am fail trung binh."""
    hit = g["hit"].values
    ue = utility(hit, g["loss4h"].values, EVAL_X, EVAL_Y)
    fails = g[g.hit == 0]
    return {"n": int(len(g)), "precision": float(hit.mean()), "u_eval": float(ue.mean()),
            "loss_fail": float(fails["loss4h"].mean()) if len(fails) else 0.0,
            "n_fail": int(len(fails))}


def agg_picks(frames):
    allp = pd.concat(frames, ignore_index=True)
    return pick_metrics(allp)


def eval_top5_blocks(te, score, name):
    """Moi ky = block 4h khong chong lan (epoch-aligned), top-5 theo score."""
    d = te[["ts", "hit", "loss4h"]].copy()
    d["score"] = score
    d["blk"] = d.ts // H_MS
    picks = []
    for _, g in d.groupby("blk"):
        if len(g) < TOPN:
            continue
        picks.append(g.nlargest(TOPN, "score"))
    m = agg_picks(picks)
    m["name"] = name
    m["n_ky"] = len(picks)
    log.info("[%s] n_ky=%d n_pick=%d precision=%.4f u_eval=%.5f loss_fail=%.4f",
             name, m["n_ky"], m["n"], m["precision"], m["u_eval"], m["loss_fail"])
    return m


def eval_random_blocks(te):
    rng = np.random.default_rng(SEED)
    d = te[["ts", "hit", "loss4h"]].copy()
    d["blk"] = d.ts // H_MS
    groups = [g for _, g in d.groupby("blk") if len(g) >= TOPN]
    precs, ues, losses = [], [], []
    for _ in range(RANDOM_REPS):
        picks = [g.iloc[rng.choice(len(g), TOPN, replace=False)] for g in groups]
        m = agg_picks(picks)
        precs.append(m["precision"]); ues.append(m["u_eval"]); losses.append(m["loss_fail"])
    m = {"name": "random", "n_ky": len(groups), "precision": float(np.mean(precs)),
         "u_eval": float(np.mean(ues)), "loss_fail": float(np.mean(losses))}
    log.info("[random x%d] n_ky=%d precision=%.4f u_eval=%.5f loss_fail=%.4f",
             RANDOM_REPS, m["n_ky"], m["precision"], m["u_eval"], m["loss_fail"])
    return m


def quarterly(te, score, name):
    d = te[["ts", "hit", "loss4h"]].copy()
    d["score"] = score
    d["blk"] = d.ts // H_MS
    d["q"] = pd.to_datetime(d.ts, unit="ms").dt.to_period("Q").astype(str)
    out = {}
    for q, gq in d.groupby("q"):
        picks = [g.nlargest(TOPN, "score") for _, g in gq.groupby("blk") if len(g) >= TOPN]
        if picks:
            out[q] = {k: round(v, 5) for k, v in agg_picks(picks).items()}
    log.info("[%s] per-quarter precision: %s", name, {q: v["precision"] for q, v in out.items()})
    return out


def run():
    ds = build_dataset()
    if SMOKE:
        json.dump({"smoke": True, "rows": int(len(ds))}, open(os.path.join(OUT_DIR, "smoke.json"), "w"))
        log.info("SMOKE OK")
        return
    import xgboost as xgb
    tr, va, te = time_split(ds)
    del ds
    Xtr, Xva, Xte = tr[FEAT], va[FEAT], te[FEAT]

    scores = {}
    # 1) baseline binary maxFav3 (label v6 — task 155)
    pos = tr.hit.mean()
    clf = xgb.XGBClassifier(n_estimators=N_ESTIMATORS, max_depth=5, learning_rate=0.05,
                            subsample=0.8, colsample_bytree=0.8, min_child_weight=20,
                            scale_pos_weight=(1 - pos) / max(pos, 1e-6), eval_metric="auc",
                            n_jobs=-1, tree_method="hist", random_state=SEED)
    clf.fit(Xtr, tr.hit, eval_set=[(Xva, va.hit)], verbose=False)
    scores["binary_maxfav3"] = clf.predict_proba(Xte)[:, 1]
    log.info("train binary_maxfav3 XONG")

    # 2) reg utility theo tung y
    for y in Y_GRID:
        utr = utility(tr.hit.values, tr.loss4h.values, X_REWARD, y)
        uva = utility(va.hit.values, va.loss4h.values, X_REWARD, y)
        reg = xgb.XGBRegressor(n_estimators=N_ESTIMATORS, max_depth=5, learning_rate=0.05,
                               subsample=0.8, colsample_bytree=0.8, min_child_weight=20,
                               objective="reg:squarederror", eval_metric="rmse",
                               n_jobs=-1, tree_method="hist", random_state=SEED)
        reg.fit(Xtr, utr, eval_set=[(Xva, uva)], verbose=False)
        scores[f"reg_y{y}"] = reg.predict(Xte)
        log.info("train reg_y%.1f XONG", y)

    # 3) cham diem TEST: top-5/ky-4h + random + theo quy
    table = {name: eval_top5_blocks(te, sc, name) for name, sc in scores.items()}
    table["random"] = eval_random_blocks(te)
    quarters = {name: quarterly(te, sc, name) for name, sc in scores.items()}

    # 4) verdict PRE-REGISTER (chot truoc trong tasks/157, cham bang code — khong hau chinh)
    b = table["binary_maxfav3"]; r0 = table["random"]
    verdict = {}
    for y in Y_GRID:
        m = table[f"reg_y{y}"]
        c1 = m["u_eval"] - b["u_eval"] >= 0.001                       # +0.10d% utility moi pick
        c2 = abs(m["loss_fail"]) <= 0.9 * abs(b["loss_fail"])          # fail nong hon >=10% tuong doi
        c3 = m["precision"] >= b["precision"] - 0.05                   # precision khong tut qua 5d%
        c4 = (b["precision"] - r0["precision"] >= 0.10) and (m["precision"] - r0["precision"] >= 0.10)
        verdict[f"reg_y{y}"] = {"c1_u_eval": bool(c1), "c2_loss_fail": bool(c2),
                                "c3_precision": bool(c3), "c4_vs_random": bool(c4),
                                "PASS": bool(c1 and c2 and c3 and c4)}
    verdict["DANG_DI_TIEP"] = bool(any(v["PASS"] for v in verdict.values() if isinstance(v, dict)))
    log.info("VERDICT_PRE_REGISTER: %s", json.dumps(verdict))

    out = {"task": 157, "label": {"tp": TP, "x_reward": X_REWARD, "y_grid": Y_GRID,
                                  "eval_x": EVAL_X, "eval_y": EVAL_Y},
           "test_from": str(pd.to_datetime(te.ts.min(), unit="ms")),
           "test_to": str(pd.to_datetime(te.ts.max(), unit="ms")),
           "n_train": int(len(tr)), "n_val": int(len(va)), "n_test": int(len(te)),
           "seed": SEED, "table": table, "per_quarter": quarters, "verdict": verdict}
    json.dump(out, open(os.path.join(OUT_DIR, "task157_result.json"), "w"), indent=2)
    log.info("XONG -> %s/task157_result.json", OUT_DIR)


run()
