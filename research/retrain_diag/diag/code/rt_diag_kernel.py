#!/usr/bin/env python3
"""rt_diag_kernel.py - PREREG_RETRAIN_DIAG 436977c1 muc 2.2 D-ruler + D-src(b) (Tang A, luat 12; KHONG PnL, KHONG sim, KHONG train).
HOLDOUT_UNSEAL_2026_1121 (U4a) + OWNER_DECISION_PILOT_1121 c3a9f01b. Nhan Vision Q3 (ho4p1-x26-q3), chi ts + horizon <= S4 (khong dung gia >= 10-01).
Dinh nghia (ghi truoc khi chay):
 p15   : score p15 (1m, market-level) vs label_oldbasket (gate.csv Q3); ts in [S3, S4-1d). IC = Spearman toan cua so; tail@q = mean(label | p15 >= q-quantile)
         - mean(label). Hieu T1-live: bootstrap khoi tuan (2000, seed 20261121) cua IC tinh lai tren hang toan cuc.
 net015: score p0 RAW fold 20260701 (live cut20251231 RAW_L vs T1 RAW_N); y = retEnd_4h (nBars_4h >= 16), yb = retEnd_4h > 0.015; ts < S4-4h.
 S1    : score p0 bins A3 0701 (Lane L = S1 live + RAW_L vs lane S = S1 T1 + RAW_L; cung multiset/tick => chi khac THU TU S1);
         y = g1lite (maxFav_72h >= 0.05 ? x - min(0.5x, 0.08) : retEnd_72h; nBars_72h >= 288), yb = maxFav_72h >= 0.07 (Y1 touch); ts < S4-72h.
         + bang phu nhan 4h (retEnd_4h > 0.015) cho S1.
 Per tick (>= 9 coin co nhan): ic = Spearman; auc = Mann-Whitney ca tick; prec8 = mean yb top-8 (score giam, tie theo sym); lift8 = prec8 - mean yb tick.
 Hieu T1 - live ghep cap theo tick (cung tap dong); CI80/CI95 bootstrap khoi tuan (tuan = (ts - S3)//7d), 2000 rep, seed 20261121.
 Loai 8 id symbol map 863 co > 1 symbol. D-src(b): permutation trong moi gio (ts_h) qua cac coin, nhom cot S1 (seed 20261121) -> giam ic / lift8."""
import glob, hashlib, json, logging, os, subprocess, sys
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout, force=True)
L = logging.getLogger("rtdiag")
L.info("HOLDOUT_UNSEAL_REF HOLDOUT_UNSEAL_2026_1121 (U4a) OWNER_DECISION_PILOT_1121 c3a9f01b PREREG_RETRAIN_DIAG 436977c1")
WK = "/kaggle/working"; RES = {"unseal_ref": "HOLDOUT_UNSEAL_2026_1121 (U4a)"}
S3, S4 = 1782838800000, 1790787600000
H, D, WEEK = 3600000, 86400000, 7 * 86400000
SEED = 20261121; NREP = 2000
KEEP = ["vol_7d", "dd_7d", "rk_dd_7d", "hrs_since_high_7d", "ret_3d", "rk_ret_3d", "ret_14d", "ls_global", "rk_oi_delta24h"]


def save():
    json.dump(RES, open(WK + "/result.json", "w"), indent=1, default=str)


def hsh(p, a="md5"):
    x = hashlib.new(a)
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            x.update(b)
    return x.hexdigest()


def one(pat, src):
    c = sorted(p for p in glob.glob("/kaggle/input/**/" + pat, recursive=True) if ("/" + src + "/") in p and os.path.isfile(p))
    assert len(c) == 1, (pat, src, c)
    return c[0]


subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "xgboost==3.2.0", "pandas==2.3.3", "numpy==2.2.6", "pyarrow==25.0.1"])
import numpy as np, pandas as pd, struct  # noqa: E402
sys.path.insert(0, os.path.dirname(one("funding_label_pb.py", "sel1m-code")))
import funding_label_pb as FL  # noqa: E402
BR = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("p0", ">f4"), ("p1", ">f4"), ("p2", ">f4"), ("p3", ">f4")])
PR = np.dtype([("ts", ">i8"), ("p15", ">f4"), ("risk", ">f4")])


def boot(d, wk):
    """mean d + CI bootstrap khoi tuan."""
    rng = np.random.default_rng(SEED)
    u = np.unique(wk); S = np.array([d[wk == w].sum() for w in u]); N = np.array([(wk == w).sum() for w in u])
    idx = rng.integers(0, len(u), size=(NREP, len(u)))
    m = S[idx].sum(1) / N[idx].sum(1)
    return {"mean": float(d.mean()), "ci80": [float(np.quantile(m, .1)), float(np.quantile(m, .9))],
            "ci95": [float(np.quantile(m, .025)), float(np.quantile(m, .975))], "n_ticks": int(len(d)), "n_weeks": int(len(u))}


def tick(ts, s, y, yb):
    d = pd.DataFrame({"ts": ts, "s": s, "y": y, "yb": yb, "sym": np.arange(len(ts))})
    d = d[d.groupby("ts").s.transform("size") >= 9].copy()
    G = d.groupby("ts")
    d["rs"] = G.s.rank(method="average"); d["ry"] = G.y.rank(method="average")
    G = d.groupby("ts")
    a1 = G.rs.transform("mean"); a2 = G.ry.transform("mean")
    d["n_"] = (d.rs - a1) * (d.ry - a2); d["s1_"] = (d.rs - a1) ** 2; d["s2_"] = (d.ry - a2) ** 2; d["srp"] = d.rs * d.yb
    G = d.groupby("ts")
    ic = G.n_.sum() / np.sqrt(G.s1_.sum() * G.s2_.sum())
    sz = G.size().astype(float); npos = G.yb.sum(); nneg = sz - npos
    auc = (G.srp.sum() - npos * (npos + 1) / 2.0) / (npos * nneg).replace(0, np.nan)
    base = G.yb.mean()
    S = d.sort_values(["ts", "s", "sym"], ascending=[True, False, True], kind="stable")
    S["cc"] = S.groupby("ts").cumcount()
    prec8 = S[S.cc < 8].groupby("ts").yb.mean().reindex(sz.index)
    return pd.DataFrame({"ic": ic, "auc": auc, "prec8": prec8, "lift8": prec8 - base, "base": base})


def compare(name, A, B):
    """A = live, B = T1: DataFrame theo tick (cung index)."""
    j = A.join(B, lsuffix="_live", rsuffix="_t1", how="inner")
    wk = ((j.index.values.astype(np.int64) - S3) // WEEK)
    out = {"live": {k: float(A[k].mean()) for k in ("ic", "auc", "prec8", "lift8", "base")},
           "t1": {k: float(B[k].mean()) for k in ("ic", "auc", "prec8", "lift8", "base")}, "diff_t1_minus_live": {}}
    for k in ("ic", "auc", "prec8", "lift8"):
        dd = (j[k + "_t1"] - j[k + "_live"]).to_numpy(); ok = np.isfinite(dd)
        out["diff_t1_minus_live"][k] = boot(dd[ok], wk[ok])
    RES[name] = out; save(); L.info("%s %s", name, json.dumps(out)[:1500])


def labels(cols):
    p = one("funding_label_20260701_to_20261001.pb", "ho4p1-x26-q3")
    RES.setdefault("inputs", {})["label_md5"] = hsh(p)
    d = FL.read_label(p, usecols=["tEpochMs", "symbol"] + cols)
    mp = pd.read_csv(one("symbol_map_863.csv", "ho4p1-code"))
    cnt = mp.groupby("symId").symbol.nunique(); multi = set(cnt[cnt > 1].index.astype(int))
    mp = mp[~mp.symId.isin(multi)]
    s2i = dict(zip(mp.symbol, mp.symId.astype(np.int64)))
    sid = d.symbol.map(s2i); k = sid.notna().to_numpy()
    out = pd.DataFrame({"ts": d.tEpochMs.to_numpy(np.int64)[k], "sym": sid[k].astype(np.int64).to_numpy()})
    for c in cols:
        out[c] = d[c].to_numpy(np.float64)[k]
    RES["inputs"]["multi_ids_excluded"] = sorted(int(x) for x in multi)
    return out.drop_duplicates(["ts", "sym"], keep=False)


def scored(path, lab, ycol, ybf, tmax):
    b = np.fromfile(path, dtype=BR)
    s = pd.DataFrame({"ts": b["ts"].astype(np.int64), "sym": b["sym"].astype(np.int64), "s": b["p0"].astype(np.float64)})
    m = s.merge(lab, on=["ts", "sym"], how="inner")
    m = m[(m.ts >= S3) & (m.ts < tmax) & np.isfinite(m.s) & np.isfinite(m[ycol])]
    yb = ybf(m)
    return m.ts.to_numpy(), m.s.to_numpy(), m[ycol].to_numpy(), yb, m[["ts", "sym"]]


def ruler_bins(name, pl, pt, lab, ycol, ybf, tmax, filt):
    a = scored(pl, lab, ycol, ybf, tmax); b = scored(pt, lab, ycol, ybf, tmax)
    ka = a[4].reset_index(drop=True); kb = b[4].reset_index(drop=True)
    assert len(ka) == len(kb) and (ka.values == kb.values).all(), name + ": tap dong khac"
    RES.setdefault("rows", {})[name] = int(len(ka))
    compare(name, tick(*a[:4]), tick(*b[:4]))


def main():
    # ---- p15
    pl = one("pred_2026.bin", "ho5-a3-data26"); pt = one("pred_2026.bin", "rt-chain-n26")
    RES["inputs"] = {"p15_live_md5": hsh(pl), "p15_t1_md5": hsh(pt)}
    assert RES["inputs"]["p15_live_md5"] == "64f66a15e0c6d7268da805e3df428760" and RES["inputs"]["p15_t1_md5"] == "c1b00ba995d26df2641e89180f96c204"
    def rp(p):
        raw = open(p, "rb").read(); n = struct.unpack(">i", raw[:4])[0]; return np.frombuffer(raw[4:4 + 16 * n], dtype=PR)
    a, b = rp(pl), rp(pt)
    g = pd.read_csv(one("gate.csv*", "ho4p1-x26-q3"), usecols=["timestamp", "label_oldbasket"])
    P = pd.DataFrame({"ts": a["ts"].astype(np.int64), "live": a["p15"].astype(np.float64), "t1": b["p15"].astype(np.float64)})
    P = P.merge(g.rename(columns={"timestamp": "ts"}), on="ts")
    P = P[(P.ts >= S3) & (P.ts < S4 - D) & np.isfinite(P.label_oldbasket)].reset_index(drop=True)
    ry = P.label_oldbasket.rank().to_numpy(); rl = P.live.rank().to_numpy(); rt = P.t1.rank().to_numpy()
    wk = ((P.ts.values - S3) // WEEK); u = np.unique(wk)
    def ic(ii):
        return np.corrcoef(rl[ii], ry[ii])[0, 1], np.corrcoef(rt[ii], ry[ii])[0, 1]
    rng = np.random.default_rng(SEED); groups = [np.where(wk == w)[0] for w in u]; bs = []
    for _ in range(NREP):
        ii = np.concatenate([groups[j] for j in rng.integers(0, len(u), len(u))]); x, y = ic(ii); bs.append(y - x)
    i0 = ic(np.arange(len(P)))
    def tail(col, q):
        t = P[col] >= P[col].quantile(q); return float(P.label_oldbasket[t].mean() - P.label_oldbasket.mean())
    RES["p15"] = {"n_min": int(len(P)), "ic_live": float(i0[0]), "ic_t1": float(i0[1]),
                  "diff_ic": {"mean": float(i0[1] - i0[0]), "ci80": [float(np.quantile(bs, .1)), float(np.quantile(bs, .9))],
                              "ci95": [float(np.quantile(bs, .025)), float(np.quantile(bs, .975))]},
                  "tail_live": {str(q): tail("live", q) for q in (.99, .999)}, "tail_t1": {str(q): tail("t1", q) for q in (.99, .999)}}
    save(); L.info("p15 %s", json.dumps(RES["p15"]))
    # ---- nhan 15'
    lab = labels(["retEnd_4h", "nBars_4h", "maxFav_72h", "retEnd_72h", "nBars_72h"])
    lab["g1lite"] = np.where(lab.maxFav_72h >= 0.05, lab.maxFav_72h - np.minimum(0.5 * lab.maxFav_72h, 0.08), lab.retEnd_72h)
    l4 = lab[lab.nBars_4h >= 16]; l72 = lab[lab.nBars_72h >= 288]
    y4 = lambda m: (m.retEnd_4h > 0.015).astype(float).to_numpy()
    y1 = lambda m: (m.maxFav_72h >= 0.07).astype(float).to_numpy()
    RAWL = one("predict_wf_20260701.bin", "ho5-a3-chain26"); RAWN = one("predict_wf_20260701.bin", "rt-chain-n26")
    BL = one("predict_wf_20260701.bin", "ho5-a3-data26"); BS = one("predict_wf_20260701.bin", "rt-s-data26")
    RES["inputs"].update(rawL_md5=hsh(RAWL), rawN_md5=hsh(RAWN), binsL_sha=hsh(BL, "sha256"), binsS_sha=hsh(BS, "sha256"))
    assert RES["inputs"]["rawN_md5"] == "e72532c68d8425a74b7f3f7df9c8865f" and RES["inputs"]["rawL_md5"] == "53cdea815ffc3f090704b02bfb4a6534"
    assert RES["inputs"]["binsS_sha"] == "aafc626627906fc609902555189bf4d1ce824a9bbda94071217931b1cc47e727"
    ruler_bins("net015_4h", RAWL, RAWN, l4, "retEnd_4h", y4, S4 - 4 * H, None)
    ruler_bins("S1_g1lite_72h", BL, BS, l72, "g1lite", y1, S4 - 72 * H, None)
    ruler_bins("S1_4h", BL, BS, l4, "retEnd_4h", y4, S4 - 4 * H, None)
    # ---- D-src(b): permutation nhom cot S1 (trong moi gio, qua coin), universe = dong RAW_L co diem S1 hop le
    import xgboost as xgb
    F = pd.read_parquet(one("feat_v2_26.parquet", "ho4p1-chain-y26"))
    F["sym"] = F.sym.astype(np.int64); F = F[(F.ts >= S3) & (F.ts < S4)].reset_index(drop=True)
    RES["inputs"]["feat_rows_q3"] = int(len(F))
    lt = l72.copy(); lt["ts_h"] = (lt.ts // H) * H
    raw = np.fromfile(RAWL, dtype=BR); R = pd.DataFrame({"ts": raw["ts"].astype(np.int64), "sym": raw["sym"].astype(np.int64)})
    R = R[R.ts < S4 - 72 * H]; R["ts_h"] = (R.ts // H) * H
    R = R.merge(lt[["ts", "sym", "g1lite", "maxFav_72h"]], on=["ts", "sym"])
    rng = np.random.default_rng(SEED)
    groups = {"none": [], "rk_oi_delta24h": ["rk_oi_delta24h"], "rk_other": ["rk_dd_7d", "rk_ret_3d"], "ls_global": ["ls_global"],
              "non_rk_rest": ["vol_7d", "dd_7d", "hrs_since_high_7d", "ret_3d", "ret_14d"]}
    out = {}
    for mn in ("s1_live.json", "s1_t1.json"):
        bst = xgb.Booster(); bst.load_model(one(mn, "rt-diag-code"))
        RES["inputs"][mn] = hsh(one(mn, "rt-diag-code"), "sha256")
        out[mn] = {}
        for gname, cols in groups.items():
            rng = np.random.default_rng(SEED)  # cung hoan vi cho live va T1
            X = F[["ts", "sym"] + KEEP].copy()
            for c in cols:
                X[c] = X.groupby("ts")[c].transform(lambda v: v.to_numpy()[rng.permutation(len(v))])
            xx = X[KEEP].to_numpy(np.float32); an = np.isnan(xx).all(1)
            sc = bst.predict(xgb.DMatrix(xx, feature_names=KEEP)); sc[an] = np.nan  # v2: predict CAO = tot (a3lib: score=-predict, sort tang)
            S = pd.DataFrame({"ts_h": X.ts.values, "sym": X.sym.values, "s": sc})
            m = R.merge(S, on=["ts_h", "sym"]); m = m[np.isfinite(m.s)]
            t = tick(m.ts.to_numpy(), m.s.to_numpy(), m.g1lite.to_numpy(), (m.maxFav_72h >= 0.07).astype(float).to_numpy())
            out[mn][gname] = {k: float(t[k].mean()) for k in ("ic", "lift8", "prec8")}
            out[mn][gname]["n_rows"] = int(len(m))
        for gname in groups:
            if gname != "none":
                out[mn][gname]["drop_ic"] = out[mn]["none"]["ic"] - out[mn][gname]["ic"]
                out[mn][gname]["drop_lift8"] = out[mn]["none"]["lift8"] - out[mn][gname]["lift8"]
        RES["dsrc_perm"] = out; save()
    L.info("dsrc %s", json.dumps(out)[:3000])


if __name__ == "__main__":
    try:
        main()
    except Exception:
        import traceback
        RES["error"] = traceback.format_exc()[-3000:]; save(); raise
    save(); L.info("RESULT %s", json.dumps(RES, default=str)[:20000])
