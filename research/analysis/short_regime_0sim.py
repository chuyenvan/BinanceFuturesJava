#!/usr/bin/env python3
"""short_regime_0sim.py — SHORT + TIN HIEU REGIME THAT (0-sim, nhanh, re).

Muc tieu: xem regime "DOWN" (tu du lieu gia san co) co CAT DUOC DUOI khong.
Pick = PA_t15_E10_S42 (bins Kaggle sm-pathexit co san) top-8/tick; do LABEL-exit
(TP -1,5% / SL +10%) bang nhan .pb (first-hit xap xi). Regime = vai bien the CO DINH
(BTC trend / breadth / vol / drawdown) — KHONG quet mu.
Nguon gia: /home/ubuntu/java/fsrun/CLOSES_1H.bin (DEV<=2025). Output json.
"""
import glob, json, os, struct, sys
import numpy as np
import pandas as pd

REPO = "/home/ubuntu/src/BinanceFuturesJava"
H = 3600000
BLOCK_H = 72
NREP = 2000
SEED = 20260905
LEG = 1.21
COST_BASE = 0.00112
FUND72 = 0.00585
THR, E = 0.015, 0.10
K_SEL = 8
NEED = 288
RES = 1024
DEV_END_MS = 1767225600000          # 2026-01-01 UTC
CLOSES = "/home/ubuntu/java/fsrun/CLOSES_1H.bin"
BINS = "/home/ubuntu/sm_pathexit/sm/PA_t15_E10_S42"
LB = "/home/ubuntu/ds_label15m"
MAP = "/home/ubuntu/claudedata/oi/symbol_map.csv"
OUT = os.path.join(REPO, "research/analysis/out/short_regime_0sim.json")
_BIN_DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("p0", ">f4"), ("p1", ">f4"),
                    ("p2", ">f4"), ("p3", ">f4")])


def ci_mean(v, ts):
    v = np.asarray(v, np.float64); ts = np.asarray(ts, np.int64)
    m = np.isfinite(v)
    if m.sum() == 0:
        return dict(mean=float("nan"), raw=[None, None], out_both=False, n=0)
    v, ts = v[m], ts[m]
    bk = ts // (BLOCK_H * H)
    _, inv = np.unique(bk, return_inverse=True)
    sums = np.bincount(inv, weights=v); cnts = np.bincount(inv).astype(float)
    k = cnts > 0; sums, cnts = sums[k], cnts[k]
    nb = len(sums); rng = np.random.default_rng(SEED)
    out = np.empty(NREP)
    for b in range(NREP):
        p = rng.integers(0, nb, nb)
        out[b] = sums[p].sum() / cnts[p].sum()
    lo, hi = float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))
    mu = float(v.mean())
    o1 = lo > 0 or hi < 0
    o2 = (mu - (mu - lo) * LEG) > 0 or (mu + (hi - mu) * LEG) < 0
    return dict(mean=mu, raw=[lo, hi], out_raw=bool(o1), out_both=bool(o1 and o2), n=int(m.sum()))


def by_year(v, ts):
    y = pd.to_datetime(ts, unit="ms", utc=True).tz_convert("Asia/Bangkok").year.to_numpy()
    o = {}
    for yy in (2022, 2023, 2024, 2025):
        m = (y == yy) & np.isfinite(v)
        o[str(yy)] = round(float(np.asarray(v)[m].mean()), 6) if m.sum() else None
    return o


def read_bins():
    ts_l, sy_l, p_l = [], [], []
    for f in sorted(glob.glob(BINS + "/predict_wf_*.bin")):
        a = np.fromfile(f, dtype=_BIN_DT)
        if not len(a):
            continue
        ts_l.append(a["ts"].astype(np.int64)); sy_l.append(a["sym"].astype(np.int32))
        p_l.append(a["p3"].astype(np.float32))
    ts = np.concatenate(ts_l); sy = np.concatenate(sy_l); p = np.concatenate(p_l)
    df = pd.DataFrame({"ts": ts, "sym": sy, "p": p.astype(float)})
    ok = np.isfinite(df["p"])
    df = df[ok]
    g = df.groupby("ts", sort=False)
    df["n"] = g["p"].transform("size")
    df["r"] = g["p"].rank(method="first")
    pk = df[df["r"] > (df["n"] - K_SEL)][["ts", "sym"]].reset_index(drop=True)
    pk = pk[(pk["ts"] + 72 * H) <= DEV_END_MS].reset_index(drop=True)
    return pk


def load_labels():
    sys.path.insert(0, os.path.join(REPO, "ml/lib"))
    import funding_label_pb as FLPB
    smap = pd.read_csv(MAP)
    s2i = dict(zip(smap.symbol, smap.symId.astype(np.int32)))
    fs = sorted(glob.glob(LB + "/funding_label_*.pb"))
    fs = [f for f in fs if os.path.basename(f).split("_")[2] < "20260101"]
    cols = ["tEpochMs", "symbol", "retEnd_72h", "maxFav_72h", "maxAdv_72h",
            "tHitFav_72h", "tHitAdv_72h", "nBars_72h"]
    parts = []
    for fp in fs:
        d = FLPB.read_label(fp, usecols=cols)
        d = d[d["nBars_72h"] >= NEED]
        parts.append(d)
    d = pd.concat(parts, ignore_index=True)
    sid = d.symbol.map(s2i)
    k = sid.notna().to_numpy()
    d = d[k]
    out = {"key": d.tEpochMs.to_numpy(np.int64) * RES + sid[k].to_numpy(np.int64)}
    for c in ("retEnd_72h", "maxFav_72h", "maxAdv_72h", "tHitFav_72h", "tHitAdv_72h"):
        out[c] = d[c].to_numpy(np.float32)
    o = np.argsort(out["key"], kind="stable")
    for kk in out:
        out[kk] = out[kk][o]
    return out


def attach(key_lbl, ts, sym):
    key = ts * RES + sym.astype(np.int64)
    ip = np.clip(np.searchsorted(key_lbl, key), 0, len(key_lbl) - 1)
    return key_lbl[ip] == key, ip


def build_regime():
    DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("c", ">f4")])
    a = np.fromfile(CLOSES, dtype=DT)
    ts = a["ts"].astype(np.int64); sym = a["sym"].astype(np.int64); c = a["c"].astype(float)
    m = ts < DEV_END_MS
    df = pd.DataFrame({"ctime": ts[m] + H, "sym": sym[m], "close": c[m]})
    df = df.drop_duplicates(["sym", "ctime"], keep="first").sort_values(["sym", "ctime"])
    g = df.groupby("sym", sort=False)
    df["ret"] = g["close"].pct_change()
    df["ret7"] = g["close"].pct_change(168)
    df["vol7"] = g["ret"].transform(lambda x: x.rolling(168, min_periods=168).std())
    br = df.dropna(subset=["ret7"]).groupby("ctime")["ret7"].apply(lambda x: float((x > 0).mean()))
    vm = df.dropna(subset=["vol7"]).groupby("ctime")["vol7"].median()
    b = df[df["sym"] == 1].set_index("ctime")["close"]
    sma = b.rolling(200, min_periods=200).mean()
    r30 = b.pct_change(720)
    dd = b / b.rolling(2160, min_periods=1).max() - 1
    reg = pd.DataFrame({"ts": b.index, "btc": b.to_numpy(), "sma200": sma.to_numpy(),
                        "r30": r30.to_numpy(), "dd": dd.to_numpy()})
    reg["breadth"] = reg["ts"].map(br)
    reg["vol"] = reg["ts"].map(vm)
    vmed = reg["vol"].median()
    R1 = (reg["btc"] < reg["sma200"]) & (reg["r30"] < 0)
    R2 = reg["breadth"] < 0.40
    R3 = R1 & (reg["breadth"] < 0.50)
    R4 = reg["dd"] < -0.20
    R5 = R1 & (reg["vol"] > vmed)
    reg["R1_btc_trend"] = R1; reg["R2_breadth"] = R2; reg["R3_trend_breadth"] = R3
    reg["R4_drawdown"] = R4; reg["R5_trend_vol"] = R5
    return reg, {"vol_med": float(vmed), "dd_peak_win_h": 2160}


def main():
    print("=== SHORT_REGIME 0-sim ===", flush=True)
    pk = read_bins()
    print("picks=%d" % len(pk), flush=True)
    lbl = load_labels()
    hit, ip = attach(lbl["key"], pk["ts"].to_numpy(), pk["sym"].to_numpy())
    pk = pk[hit].reset_index(drop=True); ip = ip[hit]
    print("picks matched labels=%d" % len(pk), flush=True)
    ret = lbl["retEnd_72h"][ip].astype(float)
    mfav = lbl["maxFav_72h"][ip].astype(float)      # duoi len (gia TANG) -> SL
    madv = lbl["maxAdv_72h"][ip].astype(float)      # loi (gia GIAM) -> TP
    tfav = lbl["tHitFav_72h"][ip].astype(float)
    tadv = lbl["tHitAdv_72h"][ip].astype(float)
    hl = 4320.0
    tp = madv <= -THR
    sl = mfav >= E
    both = tp & sl
    sl_first = sl & (~tp | (both & (tfav < tadv)))
    tp_first = tp & (~sl | (both & (tadv <= tfav)))
    pnl = np.where(sl_first, -E, np.where(tp_first, THR, -ret))
    held = np.where(sl_first, tfav, np.where(tp_first, tadv, hl))
    ts = pk["ts"].to_numpy()
    base = {"sl_rate": float(sl_first.mean()), "tp_rate": float(tp_first.mean()),
            "n": int(len(pnl))}
    print("baseline sl_rate=%.4f tp_rate=%.4f" % (base["sl_rate"], base["tp_rate"]), flush=True)
    reg, rmeta = build_regime()
    rg = reg.sort_values("ts")
    cols = ["R1_btc_trend", "R2_breadth", "R3_trend_breadth", "R4_drawdown", "R5_trend_vol"]
    mm = pd.merge_asof(pd.DataFrame({"ts": ts}).sort_values("ts"),
                       rg[["ts"] + cols], on="ts", direction="backward")
    # tra ve thu tu goc
    order = np.argsort(np.argsort(ts, kind="stable"), kind="stable")
    regmap = {c: mm[c].to_numpy()[order] for c in cols}
    res = {"prereg": "PREREG_SHORT_REGIME", "pick_arm": "PA_t15_E10_S42", "thr": THR, "E": E,
           "cost_base": COST_BASE, "fund72": FUND72, "regime_meta": rmeta,
           "baseline": base, "variants": {}}
    # baseline net
    def agg(mask):
        p = pnl[mask]; h = held[mask]; t = ts[mask]
        net = p - COST_BASE - FUND72 * (h / 4320.0)
        ci = ci_mean(net, t)
        return {"n": int(mask.sum()), "frac": round(float(mask.mean()), 4),
                "sl_rate": round(float(sl_first[mask].mean()), 4) if mask.sum() else None,
                "net": round(ci["mean"], 6), "ci_raw": [round(ci["raw"][0], 6), round(ci["raw"][1], 6)],
                "out_both": ci["out_both"], "winrate": round(float((net > 0).mean()), 4),
                "tail_max_loss": round(float(net.min()) if mask.sum() else float("nan"), 6),
                "by_year": by_year(net, t),
                "years_pos": sum(1 for v in by_year(net, t).values() if v is not None and v > 0)}
    res["baseline"]["net"] = agg(np.ones(len(pnl), bool))
    for c in cols:
        rm = np.asarray(regmap[c], dtype=bool)
        rm = np.where(np.isnan(np.asarray(regmap[c], dtype=float)), False, rm)
        res["variants"][c] = agg(rm)
    print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk != "by_year"}
                      for k, v in res["variants"].items()}, indent=1), flush=True)
    print("baseline_net", res["baseline"]["net"], flush=True)
    json.dump(res, open(OUT, "w"), indent=1, default=str)
    print("wrote", OUT, flush=True)


if __name__ == "__main__":
    main()
