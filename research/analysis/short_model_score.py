#!/usr/bin/env python3
"""short_model_score.py — CHẤM ĐIỂM cho PREREG_SHORT_MODEL (0-sim, offline; chạy in-kernel trên Kaggle).

Đọc `predict_wf_*.bin` (slot 3 = head 72h) của từng arm + nhãn `.pb` (retEnd_72h / maxFav_72h /
nBars_72h), rồi đo — NGUYÊN các chỉ số đã khóa trong `docs/prereg/PREREG_SHORT_MODEL.md` §6:

  1. rank-IC = Spearman(score, -retEnd_72h) per-tick rồi mean (score cao = kỳ vọng GIẢM).
  2. decile 0..9 theo score trong tick: mean retEnd_72h + net short (-ret - cost).
  3. top-K=8 theo score mỗi tick: gross/net short (hướng NGUỘC) + bản arm LONG (hướng long).
  4. CẮT CỨNG C ∈ {+30,+50,+90}%: pnl = -C nếu maxFav_72h >= C ngược lại -retEnd_72h;
     báo cut-rate, net, max lỗ sau cắt, p99 lỗ trước cắt.
  5. CI: block-72h bootstrap (NREP=2000, SEED=20260905), 'ngoài CI' = ngoài raw VÀ nhân ×1,21 (legacy).
  6. Bền vững theo năm 2022..2025.

Chạy:  python3 short_model_score.py --bins-root DIR --arms SHORT42:SHORT,LONG42:LONG --out out.json
"""
import argparse
import glob
import json
import os
import sys
import time

import numpy as np
import pandas as pd

H = 3600000
BLOCK_H = 72
NREP = 2000
SEED = 20260905
LEG = 1.21
LABEL_H = 72
NEED = 288                      # nBars_72h >= 288 (4320 phut / 15m)
RES = 1024

# ─────────────────────────── đọc dữ liệu ───────────────────────────

_BIN_DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("p0", ">f4"), ("p1", ">f4"),
                    ("p2", ">f4"), ("p3", ">f4")])


def read_bins(fold_files):
    """Đọc mọi predict_wf_*.bin -> (ts int64, symId int32, p float32) tại SLOT 3 (head 72h)."""
    ts_l, sy_l, p_l = [], [], []
    for fp in fold_files:
        a = np.fromfile(fp, dtype=_BIN_DT)
        if not len(a):
            continue
        ts_l.append(a["ts"].astype(np.int64))
        sy_l.append(a["sym"].astype(np.int32))
        p_l.append(a["p3"].astype(np.float32))
    if not ts_l:
        return None
    return (np.concatenate(ts_l), np.concatenate(sy_l), np.concatenate(p_l))


def load_labels(lb_dir, map_csv):
    """Nhãn DEV (ts, symId, retEnd_72h, maxFav_72h, nBars_72h) từ .pb. Lọc nBars>=NEED + notna.

    Import `funding_label_pb` từ SEL1M_CODE (như trainer)."""
    import funding_label_pb as FLPB
    smap = pd.read_csv(map_csv)
    s2i = dict(zip(smap.symbol, smap.symId.astype(np.int32)))
    fs = sorted(glob.glob(lb_dir + "/funding_label_*.pb"))
    fs = [f for f in fs if os.path.basename(f).split("_")[2] < "20260701"]
    ts_l, sy_l, re_l, mf_l = [], [], [], []
    for fp in fs:
        d = FLPB.read_label(fp, usecols=["tEpochMs", "symbol",
                                         "retEnd_%dh" % LABEL_H, "maxFav_%dh" % LABEL_H,
                                         "nBars_%dh" % LABEL_H])
        d = d[(d["nBars_%dh" % LABEL_H] >= NEED) & d["retEnd_%dh" % LABEL_H].notna()]
        sid = d.symbol.map(s2i)
        k = sid.notna().to_numpy()
        ts_l.append(d.tEpochMs.to_numpy(np.int64)[k])
        sy_l.append(sid[k].to_numpy(np.int32))
        re_l.append(d["retEnd_%dh" % LABEL_H].to_numpy(np.float32)[k])
        mf_l.append(d["maxFav_%dh" % LABEL_H].to_numpy(np.float32)[k])
    ts = np.concatenate(ts_l); sy = np.concatenate(sy_l)
    re = np.concatenate(re_l); mf = np.concatenate(mf_l)
    key = ts * RES + sy
    o = np.argsort(key, kind="stable")
    return key[o], ts[o], sy[o], re[o], mf[o]


def attach(key_lbl, re_lbl, mf_lbl, ts, sym):
    """Inner join bins ↔ nhãn theo key ts*1024+symId (searchsorted)."""
    key = ts * RES + sym.astype(np.int64)
    ip = np.clip(np.searchsorted(key_lbl, key), 0, len(key_lbl) - 1)
    hit = key_lbl[ip] == key
    return hit, ip


# ─────────────────────────── CI ───────────────────────────


def ci_mean(v, ts):
    v = np.asarray(v, dtype=np.float64)
    ts = np.asarray(ts, dtype=np.int64)
    m = np.isfinite(v)
    if m.sum() == 0:
        return dict(mean=float("nan"), raw=[float("nan")] * 2, infl=[float("nan")] * 2,
                    out_raw=False, out_legacy=False, out_both=False, n=0)
    v, ts = v[m], ts[m]
    bk = ts // (BLOCK_H * H)
    _, inv = np.unique(bk, return_inverse=True)
    sums = np.bincount(inv, weights=v)
    cnts = np.bincount(inv).astype(np.float64)
    k = cnts > 0
    sums, cnts = sums[k], cnts[k]
    n = len(sums)
    rng = np.random.default_rng(SEED)
    out = np.empty(NREP)
    for b in range(NREP):
        pick = rng.integers(0, n, n)
        out[b] = sums[pick].sum() / cnts[pick].sum()
    lo, hi = float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))
    mu = float(v.mean())
    ilo, ihi = mu - (mu - lo) * LEG, mu + (hi - mu) * LEG
    o1 = lo > 0 or hi < 0
    o2 = ilo > 0 or ihi < 0
    return dict(mean=mu, raw=[lo, hi], infl=[ilo, ihi], n=int(m.sum()),
                out_raw=bool(o1), out_legacy=bool(o2), out_both=bool(o1 and o2))


# ─────────────────────────── chấm 1 arm ───────────────────────────


def score_arm(name, bins_dir, folds, lbl, costs, cuts, k_sel, direction, main_cost):
    key_lbl, ts_lbl, sy_lbl, re_lbl, mf_lbl = lbl
    files = [os.path.join(bins_dir, "predict_wf_%s.bin" % f) for f in folds]
    files = [f for f in files if os.path.exists(f)]
    if not files:
        return {"arm": name, "error": "no bins", "n_files": 0}
    t0 = time.time()
    ts, sym, p = read_bins(files)
    hit, ip = attach(key_lbl, re_lbl, mf_lbl, ts, sym)
    ts, sym, p = ts[hit], sym[hit], p[hit]
    ret = re_lbl[ip[hit]].astype(np.float64)
    mfav = mf_lbl[ip[hit]].astype(np.float64)
    ok = np.isfinite(p) & np.isfinite(ret) & np.isfinite(mfav)
    ts, p, ret, mfav = ts[ok], p[ok], ret[ok], mfav[ok]
    del hit, ip
    df = pd.DataFrame({"ts": ts, "p": p.astype(np.float64), "ret": ret, "mfav": mfav})
    n_rows, n_tick = len(df), df.ts.nunique()
    # rank trong tick
    g = df.groupby("ts", sort=False)
    df["n"] = g["p"].transform("size")
    df["r"] = g["p"].rank(method="first")                 # 1 = score thấp nhất
    df["dec"] = np.minimum(((df["r"] - 1) / df["n"] * 10).astype(np.int64), 9)
    df["rk_ret"] = g["ret"].rank(method="first")
    # rank-IC per tick: Spearman(p, -ret) = -corr(rank p, rank ret)
    x = df["r"].to_numpy(); y = df["rk_ret"].to_numpy()
    tmp = pd.DataFrame({"ts": df["ts"].to_numpy(), "x": x, "y": y,
                        "x2": x * x, "y2": y * y, "xy": x * y})
    agg = tmp.groupby("ts", sort=False).agg(sr=("x", "sum"), sy=("y", "sum"),
                                             sxx=("x2", "sum"), syy=("y2", "sum"),
                                             sxy=("xy", "sum"), n=("x", "size"))
    del tmp, x, y
    num = agg.n * agg.sxy - agg.sr * agg.sy
    den = np.sqrt((agg.n * agg.sxx - agg.sr ** 2) * (agg.n * agg.syy - agg.sy ** 2))
    ic_t = (-num / den.replace(0, np.nan)).dropna()
    ic = ci_mean(ic_t.to_numpy(), ic_t.index.to_numpy(np.int64))
    ic["n_tick"] = int(len(ic_t))
    # decile
    dec_ret = df.groupby("dec")["ret"].mean()
    dec_net = (-dec_ret) - main_cost
    # top-K theo score (r cao nhất) = ứng viên SHORT
    sel = df["r"] > (df["n"] - k_sel)
    S = df.loc[sel, ["ts", "p", "ret", "mfav"]].copy()
    df.drop(columns=["rk_ret"], inplace=True, errors="ignore")
    out = {"arm": name, "n_rows": int(n_rows), "n_tick": int(n_tick), "n_sel": int(len(S)),
           "n_files": len(files), "direction": direction, "seconds_read": round(time.time() - t0, 1),
           "ic": ic,
           "decile_ret": {int(k): round(float(v), 6) for k, v in dec_ret.items()},
           "decile_net_short": {int(k): round(float(v), 6) for k, v in dec_net.items()}}
    # top-K series per tick
    yrs = pd.to_datetime(S["ts"], unit="ms", utc=True).dt.tz_convert("Asia/Bangkok").dt.year.to_numpy()

    def by_year(series_vals, series_ts):
        o = {}
        for yr in (2022, 2023, 2024, 2025):
            m = (series_ts >= int(pd.Timestamp("%d-01-01" % yr, tz="Asia/Bangkok").value // 10**6)) & \
                (series_ts < int(pd.Timestamp("%d-01-01" % (yr + 1), tz="Asia/Bangkok").value // 10**6))
            o[yr] = round(float(np.asarray(series_vals)[m].mean()), 6) if m.sum() else None
        return o

    if direction == "short":
        gross_all = -S["ret"]
        own = "short"
    else:
        gross_all = S["ret"]
        own = "long"
    g_sum = S.groupby("ts")["ret"].mean()
    # per-tick gross (own direction)
    if own == "short":
        pt_gross = (-g_sum).to_numpy()
    else:
        pt_gross = g_sum.to_numpy()
    pt_ts = g_sum.index.to_numpy(np.int64)
    out["k%d" % k_sel] = {
        "own": own,
        "gross": ci_mean(pt_gross, pt_ts),
        "net": ci_mean(pt_gross - main_cost, pt_ts),
        "net_stress": ci_mean(pt_gross - costs["stress"], pt_ts),
        "by_year_net": by_year(pt_gross - main_cost, pt_ts),
        "tail_precut": {"p99": round(float(np.percentile(gross_all, 1)), 6),
                        "max_loss": round(float(gross_all.min()), 6)},
    }
    # CẮT CỨNG (chỉ có nghĩa cho SHORT: lỗ khi coin TĂNG >= C)
    tail = (-S["ret"]).to_numpy()                 # pnl short khi KHÔNG cắt
    cutres = {}
    for C in cuts:
        stopped = S["mfav"].to_numpy() >= C
        pnl = np.where(stopped, -C, -S["ret"].to_numpy())
        pt = pd.DataFrame({"ts": S["ts"].to_numpy(), "pnl": pnl}).groupby("ts")["pnl"].mean()
        val = pt.to_numpy() - main_cost
        cutres["%.2f" % C] = {
            "cut_rate": round(float(stopped.mean()), 6), "n_cut": int(stopped.sum()),
            "gross": ci_mean(pt.to_numpy(), pt.index.to_numpy(np.int64)),
            "net": ci_mean(val, pt.index.to_numpy(np.int64)),
            "net_stress": ci_mean(pt.to_numpy() - costs["stress"], pt.index.to_numpy(np.int64)),
            "by_year_net": by_year(val, pt.index.to_numpy(np.int64)),
            "p99_loss": round(float(np.percentile(pnl, 1)), 6),
            "max_loss": round(float(pnl.min()), 6),
        }
    out["cuts"] = cutres
    # mirror: với arm LONG, thêm "đảo dấu" (short đúng các pick long) để đối chiếu vòng trước
    if direction == "long":
        pt_m = (-g_sum).to_numpy()
        out["mirror_short"] = {"gross": ci_mean(pt_m, pt_ts), "net": ci_mean(pt_m - main_cost, pt_ts)}
    # đuôi trái của arm short (rủi ro KHÔNG cắt)
    out["short_tail"] = {"p01": round(float(np.percentile(tail, 1)), 6),
                         "p99": round(float(np.percentile(tail, 99)), 6),
                         "max_loss": round(float(tail.min()), 6),
                         "mean": round(float(tail.mean()), 6)}
    del df, S
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bins-root", required=True)
    ap.add_argument("--arms", required=True, help="TAG:DIR:DIRECTION,... vd SHORT42:SHORT,short,LONG42:LONG,long")
    ap.add_argument("--labels-dir", default="/kaggle/input")
    ap.add_argument("--map-csv", default="")
    ap.add_argument("--folds", default="20220101,20220401,20220701,20221001,20230101,20230401,"
                                      "20230701,20231001,20240101,20240401,20240701,20241001,"
                                      "20250101,20250401,20250701,20251001")
    ap.add_argument("--cost-base", type=float, default=0.00112)
    ap.add_argument("--cost-stress", type=float, default=0.00150)
    ap.add_argument("--k", type=int, default=8)
    ap.add_argument("--cuts", default="0.30,0.50,0.90")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    folds = [x.strip() for x in a.folds.split(",") if x.strip()]
    cuts = tuple(float(x) for x in a.cuts.split(",") if x.strip())
    costs = {"base": a.cost_base, "stress": a.cost_stress}

    if not a.map_csv:
        cand = glob.glob("/kaggle/input/**/symbol_map.csv", recursive=True)
        a.map_csv = cand[0]
    lbdir = a.labels_dir
    if not glob.glob(lbdir + "/**/funding_label_*.pb", recursive=True)[:1]:
        cand = glob.glob("/kaggle/input/**/funding_label_*.pb", recursive=True)
        lbdir = os.path.dirname(sorted(cand)[0])
    sys.path.insert(0, os.path.dirname(glob.glob("/kaggle/input/**/tool1_col.py", recursive=True)[0]))
    print("### labels=%s | map=%s" % (lbdir, a.map_csv), flush=True)
    t0 = time.time()
    lbl = load_labels(lbdir, a.map_csv)
    print("### nhãn: %d dòng (%.1f phút)" % (len(lbl[0]), (time.time() - t0) / 60), flush=True)

    arms = []
    for spec in a.arms.split(","):
        spec = spec.strip()
        if not spec:
            continue
        tag, d, dr = spec.split(":")
        arms.append((tag, os.path.join(a.bins_root, d), dr))
    res = {"cut_levels": list(cuts), "k_sel": a.k, "cost_base": a.cost_base,
           "cost_stress": a.cost_stress, "block_h": BLOCK_H, "nrep": NREP, "seed": SEED,
           "legacy_inflate": LEG, "arms": {}}
    for tag, dirp, dr in arms:
        print("### arm %s (%s) <- %s" % (tag, dr, dirp), flush=True)
        res["arms"][tag] = score_arm(tag, dirp, folds, lbl, costs, cuts, a.k, dr, a.cost_base)
        r = res["arms"][tag]
        if "error" in r:
            print("  ERR", r, flush=True)
            continue
        print("  n_rows=%d n_tick=%d IC=%.5f raw=%s out_raw=%s out_leg=%s"
              % (r["n_rows"], r["n_tick"], r["ic"]["mean"], [round(x, 5) for x in r["ic"]["raw"]],
                 r["ic"]["out_raw"], r["ic"]["out_legacy"]), flush=True)
        kk = r["k%d" % a.k]
        print("  K%d(%s) net=%.5f raw=%s by_year=%s" % (a.k, kk["own"], kk["net"]["mean"],
              [round(x, 5) for x in kk["net"]["raw"]], kk["by_year_net"]), flush=True)
        for C, c in r["cuts"].items():
            print("  CUT +%s: rate=%.4f net=%.5f raw=%s by_year=%s" % (C, c["cut_rate"],
                  c["net"]["mean"], [round(x, 5) for x in c["net"]["raw"]], c["by_year_net"]), flush=True)
        del r
    json.dump(res, open(a.out, "w"), indent=1, default=str)
    print("### JSON -> %s (%.1f phút)" % (a.out, (time.time() - t0) / 60), flush=True)


if __name__ == "__main__":
    main()
