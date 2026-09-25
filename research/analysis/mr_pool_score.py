#!/usr/bin/env python3
"""mr_pool_score.py — BẢNG PHỤ của PREREG_MONEY_RANKER §4.2: chấm trong **POOL ỨNG VIÊN** (top-K S1).

Vì sao cần: model nhãn (b) **chỉ thấy ~top-K/255 coin mỗi tick khi train** ⇒ điểm của nó trên coin NGOÀI pool
là **ngoại suy**. Bảng chính (§3) là bảng QUYẾT ĐỊNH (mọi coin, so được với mọi số cũ); bảng này là
**đối chiếu công bằng trong pool** — cùng chỉ số, cùng CI, chỉ khác TẬP DÒNG.

Dùng NGUYÊN `model_ruler.tick_metrics` / `ci_mean` (không viết lại chỉ số).

Chạy: python3 mr_pool_score.py --arms MRB8,MRB32 --pool top8,top32 --bins-root /tmp/mrbins
"""
import argparse
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import model_ruler as MR                       # noqa: E402

LABELS = "/home/ubuntu/label_15m"
MRBINS = "/tmp/mrbins"
POOL = "/tmp/mrbins/pool"                      # key S1 top-K (int64 = ts*1024+symId)
CONTROLS = ["45deploy", "A45", "V5", "V1"]
INFL = 1.177410
M = ["ic", "pacc", "dec_mono", "dec_rho", "glift8", "netm8", "auc8", "auc8c", "lift8", "base"]


def pool_keys(K):
    """top-K theo diem S1 moi tick (score THAP = TOT) — GIONG mr_label_build.load_candidates."""
    d = pd.read_parquet("/home/ubuntu/ledger/pred_s1a2x1.parquet", columns=["ts", "sym", "score"])
    d = d.sort_values(["ts", "score"], ascending=[True, True], kind="stable")
    d = d.groupby("ts", sort=True).head(K)
    return np.sort((d.ts.to_numpy(np.int64) * 1024 + d.sym.to_numpy(np.int64)))


def ticks_pool(bins_dir, poolK, folds, slot, h_lab, y_kind):
    ycol = ("maxFav_%s" % h_lab) if y_kind == "maxfav" else ("retEnd_%s" % h_lab)
    cols = list(dict.fromkeys(["retEnd_" + h_lab, "nBars_" + h_lab, ycol]))
    LK, LV = MR.load_labels(LABELS, cols)
    PK = pool_keys(poolK)
    cdir = "/tmp/mrscore/pcache"
    os.makedirs(cdir, exist_ok=True)
    out = []
    for f in folds:
        bp = os.path.join(bins_dir, "predict_wf_%s.bin" % f)
        if not os.path.exists(bp):
            continue
        cp = os.path.join(cdir, "%s_%s_%s.parquet" % (os.path.basename(bins_dir), poolK, f))
        if os.path.exists(cp):
            out.append(pd.read_parquet(cp))
            continue
        arr = np.fromfile(bp, dtype=MR.BIN_DT)
        ts = arr["ts"].astype(np.int64); sy = arr["sym"].astype(np.int64)
        p = (arr["p"] if slot == 0 else arr["z"][:, slot - 1]).astype(np.float32).astype(np.float64)
        key = ts * 1024 + sy
        ip = np.clip(np.searchsorted(LK, key), 0, len(LK) - 1)
        hit = LK[ip] == key
        y = np.full(len(key), np.nan); y[hit] = LV[ycol][ip[hit]]
        iq = np.clip(np.searchsorted(PK, key), 0, len(PK) - 1)
        inpool = PK[iq] == key
        m = hit & inpool & np.isfinite(y) & np.isfinite(p)
        R, _ = MR.tick_metrics(ts[m], p[m], y[m], None)
        R["fold"] = f
        R.to_parquet(cp, index=False)
        out.append(R)
        del arr
    return pd.concat(out, ignore_index=True) if out else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", required=True)
    ap.add_argument("--pool", default="top8,top32")
    ap.add_argument("--bins-root", default=MRBINS)
    ap.add_argument("--out", default="/tmp/mrscore/pool.json")
    ap.add_argument("--no-controls", action="store_true")
    a = ap.parse_args()
    bins = {}
    for n in [x for x in a.arms.split(",") if x]:
        bins[n] = os.path.join(a.bins_root, n)
    for n in ([] if a.no_controls else CONTROLS):
        bins[n] = dict(MR.PATHS)[n][0]
    res = {"summary": {}, "delta": {}}
    folds16 = MR.FOLDS
    for pk in a.pool.split(","):
        K = int(pk.replace("top", ""))
        T = {}
        for arm, bd in bins.items():
            slot = 3 if arm == "MRA72" else 0
            T[arm] = ticks_pool(bd, K, folds16, slot, "4h", "retend")
            s = MR.summarize(T[arm], arm, M, INFL) if T[arm] is not None else None
            if s is None:
                print("[%s] %-9s KHONG CO DONG TRONG POOL" % (pk, arm), flush=True)
                continue
            res["summary"]["%s|%s" % (arm, pk)] = {
                "n_tick": s["n_tick"], "n_coin": round(float(s["n_coin_mean"]), 2),
                "metrics": {m: {"mean": round(v["mean"], 6), "infl": [round(x, 6) for x in v["infl"]],
                                "strict": bool(MR.decide(v)[2])} for m, v in s["metrics"].items()}}
            print("[%s] %-9s n_tick=%d n_coin=%.1f ic=%+.5f pacc=%.5f dec_mono=%.5f netm8=%+.5f"
                  % (pk, arm, s["n_tick"], s["n_coin_mean"],
                     s["metrics"]["ic"]["mean"], s["metrics"]["pacc"]["mean"],
                     s["metrics"]["dec_mono"]["mean"], s["metrics"]["netm8"]["mean"]), flush=True)
        for arm in [x for x in a.arms.split(",") if x]:
            for ctl in CONTROLS:
                if ctl not in T:
                    continue
                d = MR.delta(T[arm], T[ctl], M, "%s-%s" % (arm, ctl))
                res["delta"]["%s|%s|%s" % (arm, ctl, pk)] = {
                    "n_tick_common": d["n_tick_common"],
                    "metrics": {m: {"mean": round(v["mean"], 6), "out_both": bool(v["out_both"]),
                                    "dir": int(v["direction"])}
                                for m, v in d["metrics"].items()}}
    json.dump(res, open(a.out, "w"), indent=1, default=str)
    print("-> %s" % a.out, flush=True)


if __name__ == "__main__":
    main()
