#!/usr/bin/env python3
"""audit_pnl_ro.py — VIỆC 3 của PREREG_AUDIT_PNL: TÁCH NGUỒN GIÁ TRỊ CỦA RỔ.

Cùng LUẬT THOÁT (P0, pred=None, E=close(t)) + cùng cửa sổ, chỉ đổi CÁCH CHỌN RỔ, trên 200 tick
ngẫu nhiên (SEED_C):
  R1 = top-32 theo S1 (đọc từ nhãn (b), KHÔNG sim lại)      R2 = ngẫu nhiên 32 coin/tick
  R3 = toàn thị trường (mọi coin có điểm S1 tại tick)        R4 = bottom-32 theo S1
Báo mean(gross) từng rổ + CI khối-72h + HIỆU GHÉP CẶP theo tick + thành phần status.
Chỉ ĐỌC. Không train/sim hệ thống/push.
"""
import json
import os
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import audit_pnl_lib as A                       # noqa: E402

os.makedirs(A.OUT, exist_ok=True)
T0 = time.time()
BLOCK_MS = 72 * A.HOUR
NREP, SEED_BOOT = 2000, 20260905
N_TICK = 200
K = 32


def ci_mean(v, ts, nrep=NREP, seed=SEED_BOOT):
    b = np.asarray(ts, np.int64) // BLOCK_MS
    _, inv = np.unique(b, return_inverse=True)
    s = np.bincount(inv, weights=np.asarray(v, float)); c = np.bincount(inv).astype(float)
    m = c > 0; s, c = s[m], c[m]
    rng = np.random.default_rng(seed); out = np.empty(nrep)
    for i in range(nrep):
        p = rng.integers(0, len(s), len(s)); out[i] = s[p].sum() / c[p].sum()
    mu = float(np.asarray(v, float).mean())
    return dict(mean=mu, raw=[float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))],
                n_block=int(len(s)))


def ci_diff_paired(v, ts, nrep=NREP, seed=SEED_BOOT):
    """CI khối-72h của TRUNG BÌNH của `v` (= hiệu ghép cặp theo tick), có báo cả sàn/chặt 1.21."""
    r = ci_mean(v, ts, nrep, seed)
    lo, hi = r["raw"]
    f = 1.21
    return dict(mean=r["mean"], raw=[lo, hi],
                ci121=[r["mean"] - (r["mean"] - lo) * f, r["mean"] + (hi - r["mean"]) * f],
                outside_121=bool((r["mean"] - (r["mean"] - lo) * f) > 0 or (r["mean"] + (hi - r["mean"]) * f) < 0),
                outside_raw=bool(lo > 0 or hi < 0), n_block=r["n_block"])


def one_tick(args):
    ts, syms, r2, r4 = args
    d0 = A.day_of(ts)
    days = list(range(d0, d0 + 9))
    need = {d: set(syms) for d in days}
    bars = A.load_days(days, need, workers=1)
    rows = {}
    for sym in syms:
        arr, _ = A.assemble(bars, sym, days)
        if arr is None:
            continue
        r = A.replay(sym, arr[0], arr[1], ts)
        if r is None:
            continue
        rows[sym] = (r["gross"], r["status"])
    del bars
    return ts, rows, int(len(syms)), int(len(rows)), r2, r4


def basket(rows, syms):
    v = [rows[s][0] for s in syms if s in rows]
    return np.array(v, float) if v else np.array([], float)


def main():
    lab = pd.read_parquet(A.LABEL, columns=["ts", "symId", "sym", "rank", "gross", "status"])
    pool_ticks = np.sort(lab.ts.unique())
    rng = np.random.default_rng(A.SEED_C)
    pick = rng.choice(pool_ticks, N_TICK, replace=False)
    pick = np.sort(pick)
    A.log("V3: %d tick mẫu (trong %d tick của pool)", len(pick), len(pool_ticks))

    s1 = pd.read_parquet(A.S1_PARQUET, columns=["ts", "sym", "score"])
    s1 = s1[s1.ts.isin(set(pick.tolist()))]
    smap = pd.read_csv(A.MAP_CSV)[["symId", "symbol"]]
    s1 = s1.rename(columns={"sym": "symId"}).merge(smap, on="symId", how="left")
    n_unmap = int(s1.symbol.isna().sum())
    s1 = s1.dropna(subset=["symbol"])
    A.log("universe S1 trên mẫu: %d dòng | coin/tick mean=%.1f | chưa map=%d",
          len(s1), len(s1) / max(s1.ts.nunique(), 1), n_unmap)

    # R1 (từ nhãn) + R4 (bottom-32) + R2 (ngẫu nhiên 32) theo từng tick
    lab_t = lab[lab.ts.isin(set(pick.tolist()))]
    R1 = {t: g for t, g in lab_t[lab_t["rank"] < K].groupby("ts").gross.mean().items()}
    tasks = []
    for i, t in enumerate(pick):
        u = s1[s1.ts == t].sort_values(["score", "symId"], kind="stable")
        if not len(u):
            continue
        allsym = u.symbol.tolist()
        b32 = u.tail(K).symbol.tolist()                       # điểm CAO = xấu
        rt = np.random.default_rng([A.SEED_C, int(i)])        # TÁI LẬP theo TICK (không phụ thuộc thứ tự)
        r2 = rt.choice(allsym, size=min(K, len(allsym)), replace=False).tolist()
        tasks.append((int(t), allsym, r2, b32))
    A.log("tick có universe: %d", len(tasks))

    out = []
    CACHE_T = os.path.join(A.OUT, "ro_ticks.pkl")
    done = {}
    if os.path.exists(CACHE_T):
        import pickle
        done = pickle.load(open(CACHE_T, "rb"))
        A.log("V3: dùng lại %d tick đã lưu", len(done))
    todo = [t for t in tasks if t[0] not in done]
    out = list(done.values())
    with Pool(4) as p:
        for i, (t, rows, nu, ns, r2, r4) in enumerate(p.imap_unordered(one_tick, todo, chunksize=1)):
            out.append(dict(ts=int(t), rows=rows, n_univ=nu, n_sim=ns, r2=r2, r4=r4))
            done[int(t)] = out[-1]
            if i % 10 == 0:
                A.log("  tick %d/%d (%.0fs)", i + 1, len(todo), time.time() - T0)
                import pickle
                pickle.dump(done, open(CACHE_T, "wb"), protocol=4)
    out = sorted(out, key=lambda x: x["ts"])
    A.log("sim xong %d tick, %.0fs", len(out), time.time() - T0)

    rec = {"R1": [], "R2": [], "R3": [], "R4": [], "R1resim": [], "ts": []}
    comp = {k: {} for k in ("R1", "R2", "R3", "R4")}
    n_noentry = 0
    for o in out:
        rows, t = o["rows"], o["ts"]
        r1syms = lab_t[(lab_t.ts == t) & (lab_t["rank"] < K)].sym.tolist()
        r3 = [g for g, s in rows.values()]
        rec["ts"].append(t)
        rec["R1"].append(R1[t])
        rec["R2"].append(basket(rows, o["r2"]).mean() if len(basket(rows, o["r2"])) else np.nan)
        rec["R3"].append(np.mean(r3) if r3 else np.nan)
        rec["R4"].append(basket(rows, o["r4"]).mean() if len(basket(rows, o["r4"])) else np.nan)
        rr = basket(rows, r1syms)
        rec["R1resim"].append(rr.mean() if len(rr) else np.nan)
        n_noentry += o["n_univ"] - o["n_sim"]
        for k, syml in (("R1", r1syms), ("R2", o["r2"]), ("R4", o["r4"])):
            for g, s in ((rows[x][0], rows[x][1]) for x in syml if x in rows):
                d = comp[k].setdefault(s, [0, 0.0]); d[0] += 1; d[1] += g
        for g, s in rows.values():
            d = comp["R3"].setdefault(s, [0, 0.0]); d[0] += 1; d[1] += g

    ts = np.array(rec["ts"], np.int64)
    res = {"meta": {"n_tick": len(out), "n_universe_mean": float(np.mean([o["n_univ"] for o in out])),
                    "n_noentry": n_noentry, "seed": A.SEED_C, "K": K,
                    "bins_identity": "local ticker bins md5 == Kaggle wfo-ticker-* (đã neo)"},
           "baskets": {}, "paired": {}, "composition": {}, "gates": {}}
    for k in ("R1", "R2", "R3", "R4", "R1resim"):
        v = np.array(rec[k], float)
        m = np.isfinite(v)
        res["baskets"][k] = dict(ci_mean(v[m], ts[m]), n=int(m.sum()))
    for k, (a, b) in {"R1-R3": ("R1", "R3"), "R2-R3": ("R2", "R3"), "R1-R2": ("R1", "R2"),
                      "R1-R4": ("R1", "R4"), "R1resim-R1": ("R1resim", "R1")}.items():
        d = np.array(rec[a], float) - np.array(rec[b], float)
        m = np.isfinite(d)
        res["paired"][k] = ci_diff_paired(d[m], ts[m])
    for k, d in comp.items():
        tot = sum(x[0] for x in d.values())
        res["composition"][k] = {s: dict(share=round(x[0] / tot, 4), gross_mean=round(x[1] / x[0], 5))
                                 for s, x in sorted(d.items())}
    # cổng tự-kiểm
    res["gates"] = {
        "R2_vs_R3_paired_should_be_~0": res["paired"]["R2-R3"],
        "R1resim_vs_R1_label_should_be_~0": res["paired"]["R1resim-R1"],
    }
    json.dump(res, open(os.path.join(A.OUT, "ro.json"), "w"), indent=1, default=str)
    A.log("WRITE %s/ro.json (%.0fs)", A.OUT, time.time() - T0)
    print(json.dumps(res["baskets"], indent=1, default=str))
    print(json.dumps(res["paired"], indent=1, default=str))


if __name__ == "__main__":
    main()
