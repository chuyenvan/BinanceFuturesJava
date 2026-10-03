#!/usr/bin/env python3
"""GEOM_LIVE — model S1-GEOM cho duong LIVE + parity offline<->live (docs/audit/GEOM_LIVE_IMPL_20261003.md).
feat          : tai lap geom_x1.parquet bang CHINH s1_geom_feat.geom() (WK -> OUT); so md5 voi vong GEOM (6903e178).
train <CUT>   : XGBRanker recipe s1_geom_kernel.py arm G42 (KEEP9+GEOM9, seed 42) device=cpu, fold cutoff CUT
                -> OUT/model/s1geom_g42_cut<CUT>.{json,onnx,manifest.json}; cong mem==json, ONNX vs JSON <= 1e-6;
                xuat mau 18 cot + p_json cho cong Java ORT; CUT=20251001: so voi kout/pred_G42.parquet (GPU Kaggle).
parity <csv> <model.json> <model.onnx> : 9 cot GEOM Java replay (GeomParityProbe) vs geom_mats offline cung gio;
                top-16 tren ung vien ledger: offline (KEEP9+GEOM offline, XGB json) vs replay (KEEP9+GEOM Java, ONNX).
"""
import hashlib, json, logging, os, sys, time
import numpy as np
import pandas as pd
REPO = os.environ.get("GEOM_REPO", "/home/ubuntu/src/BinanceFuturesJava")
sys.path.insert(0, REPO + "/research/analysis")
import s1_geom_feat as SG  # noqa: E402
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout)
log = logging.getLogger("geom_live")
OUT = "/home/ubuntu/claude_master/1003/geom_live"
GEOM_PQ = OUT + "/kds/geom_x1.parquet"
GEOM_MD5_REF = "6903e178f2f27e192701ddb36ba627b8"
KEEP, GEOM = list(SG.KEEP9), list(SG.GEOM)
FE = KEEP + GEOM
H, TZ = 3600000, 7 * 3600000
PURGE = 72 * H
PRED_G42 = "/home/ubuntu/claude_master/1003/geom/kout/pred_G42.parquet"
SYMMAP = "/home/ubuntu/selector_pred_out/symbol_map.csv"


def sha256f(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def feat():
    SG.WK = OUT   # geom() ghi WK/kds/geom_x1.parquet + WK/geom_meta.json -> thu muc RIENG, khong ghi de vong GEOM
    SG.geom()
    m = SG.md5f(GEOM_PQ)
    same = m == GEOM_MD5_REF
    if not same:   # md5 file co the khac do metadata parquet -> so GIA TRI tung bit voi ban Kaggle khong co san; ghi ro
        log.info("md5 khac ref (metadata?) -> can so gia tri")
    log.info("FEAT_DONE md5 %s ref %s %s", m, GEOM_MD5_REF, "MATCH" if same else "KHAC")


def load_D():
    """Y het s1_geom_kernel.kaggle_main (ledger loc g1lite, rel5, join theo gio)."""
    Dd = pd.read_parquet(SG.LEDGER_LITE, columns=["ts", "sym", "g1lite"])
    Dd = Dd[Dd.g1lite.notna()].copy()
    Dd["med"] = Dd.groupby("ts").g1lite.transform("median")
    Dd["rel"] = Dd.g1lite - Dd.med
    Dd["rk"] = Dd.groupby("ts").rel.rank(pct=True, method="first")
    Dd["rel5"] = np.minimum((Dd.rk * 5).astype(int), 4)
    Dd["ts_h"] = (Dd.ts // H) * H
    Dd = Dd.drop(columns=["med", "rel", "rk"])
    F = pd.read_parquet(SG.KEEP9_PQ)
    G = pd.read_parquet(GEOM_PQ, columns=["ts", "sym"] + GEOM)
    assert len(F) == len(G) and (F.ts.to_numpy() == G.ts.to_numpy()).all() and (F.sym.to_numpy() == G.sym.to_numpy()).all()
    F = pd.concat([F, G[GEOM]], axis=1)
    del G
    n0 = len(Dd)
    Dd = Dd.merge(F.rename(columns={"ts": "ts_h"}), on=["ts_h", "sym"], how="left")
    assert len(Dd) == n0
    log.info("pool %s vol_7d %.4f pos24 %.4f", Dd.shape, Dd.vol_7d.notna().mean(), Dd.pos24.notna().mean())
    return Dd


def cut_ms(day):
    c = int(pd.Timestamp(f"{day[:4]}-{day[4:6]}-{day[6:]}").value // 10 ** 6) - TZ
    hi = int((pd.Timestamp(c + TZ, unit="ms") + pd.DateOffset(months=3)).value // 10 ** 6) - TZ
    return c, hi


def to_onnx(m, opath):
    """Nhu x1_s1_save_model.py: dang ky XGBRanker dung converter XGBRegressor (onnxmltools)."""
    import xgboost as xgb
    from onnxmltools.convert.xgboost.operator_converters.XGBoost import convert_xgboost as _conv
    from skl2onnx import convert_sklearn, update_registered_converter
    from skl2onnx.common.data_types import FloatTensorType
    from skl2onnx.common.shape_calculator import calculate_linear_regressor_output_shapes
    update_registered_converter(xgb.XGBRanker, "XGBoostXGBRanker", calculate_linear_regressor_output_shapes, _conv)
    m.get_booster().feature_names = [f"f{i}" for i in range(len(FE))]
    onx = convert_sklearn(m, initial_types=[("input", FloatTensorType([None, len(FE)]))],
                          target_opset={"": 15, "ai.onnx.ml": 2})
    with open(opath, "wb") as f:
        f.write(onx.SerializeToString())


def ort_run(opath, X):
    import onnxruntime as ort
    s = ort.InferenceSession(opath, providers=["CPUExecutionProvider"])
    outs = [np.asarray(s.run(None, {"input": X[i:i + 200000]})[0]).ravel() for i in range(0, len(X), 200000)]
    return np.concatenate(outs)


def top_overlap(df, a, b, k=16):
    """Trung binh |top-k(a) giao top-k(b)|/k moi tick (score THAP = tot), chi tick co >= k dong."""
    ov, same = [], 0
    for _, g in df.groupby("ts"):
        if len(g) < k:
            continue
        x = set(g.nsmallest(k, a).sym)
        y = set(g.nsmallest(k, b).sym)
        ov.append(len(x & y) / k)
        same += int(x == y)
    return dict(n_tick=len(ov), overlap_mean=float(np.mean(ov)) if ov else None,
                overlap_min=float(np.min(ov)) if ov else None, same_set=same)


def train(day):
    import xgboost as xgb
    from scipy.stats import spearmanr
    D = load_D()
    c, hi = cut_ms(day)
    tr = D[D.ts < c - PURGE].sort_values("ts")
    oos = D[(D.ts >= c) & (D.ts < hi)].sort_values("ts")
    del D
    assert tr.ts.max() < c, "LEAK"
    log.info("cut %s train %d (den %s) oos %d", day, len(tr), pd.to_datetime(tr.ts.max(), unit="ms"), len(oos))
    md = OUT + "/model"
    os.makedirs(md, exist_ok=True)
    tag = f"s1geom_g42_cut{day}"
    jpath, opath = f"{md}/{tag}.json", f"{md}/{tag}.onnx"
    m = xgb.XGBRanker(objective="rank:ndcg", n_estimators=300, max_depth=4, learning_rate=0.05, subsample=0.8,
                      colsample_bytree=0.8, min_child_weight=50, n_jobs=4, tree_method="hist", random_state=42,
                      lambdarank_pair_method="topk", lambdarank_num_pair_per_sample=8, device="cpu")
    t0 = time.time()
    m.fit(tr[FE], tr.rel5, qid=pd.factorize(tr.ts, sort=True)[0])
    log.info("fit %.0fs", time.time() - t0)
    m.get_booster().save_model(jpath)
    G = oos if len(oos) >= 20000 else tr.iloc[-200000:]
    X = G[FE].to_numpy(np.float32)
    p_mem = m.predict(G[FE])
    b2 = xgb.Booster()
    b2.load_model(jpath)
    p_json = b2.predict(xgb.DMatrix(X, feature_names=FE))
    to_onnx(m, opath)
    p_onnx = ort_run(opath, X)
    gate = dict(n=int(len(X)), nan_rows=int(np.isnan(X).any(axis=1).sum()),
                max_d_mem_json=float(np.abs(p_mem - p_json).max()), max_d_json_onnx=float(np.abs(p_json - p_onnx).max()))
    gate["PASS"] = bool(gate["max_d_mem_json"] <= 1e-6 and gate["max_d_json_onnx"] <= 1e-6)
    log.info("GATE_MODEL %s", json.dumps(gate))
    # mau cho cong Java ORT (GeomParityProbe onnx): 5000 dong, co ca dong NaN
    rs = np.random.default_rng(20261003)
    idx = np.sort(rs.choice(len(X), min(5000, len(X)), replace=False))
    S = pd.DataFrame(X[idx], columns=FE)
    S.insert(0, "p_json", p_json[idx].astype(np.float64))
    S.to_csv(f"{md}/{tag}.orttest.csv", index=False, float_format="%.9g")
    man = dict(tag=tag, cutoff=day, recipe="s1_geom_kernel.py arm G42 (KEEP9+GEOM9, seed 42) device=cpu",
               features=FE, train_rows=int(len(tr)), train_ts_max=int(tr.ts.max()), purge_ms=PURGE,
               oos_rows=int(len(oos)), xgboost=xgb.__version__, sha256_json=sha256f(jpath),
               sha256_onnx=sha256f(opath), geom_parquet_md5=SG.md5f(GEOM_PQ), gate=gate)
    if os.path.exists(PRED_G42) and G is oos:
        R = pd.read_parquet(PRED_G42)
        R = R[(R.ts >= c) & (R.ts < hi)]
        O = oos[["ts", "sym"]].assign(score_cpu=-p_mem)
        M = R.merge(O, on=["ts", "sym"], how="inner")
        sp_tick = M.groupby("ts").apply(lambda g: spearmanr(g.score, g.score_cpu).correlation if len(g) > 2 else np.nan)
        man["vs_gpu_G42"] = dict(n=int(len(M)), n_ref=int(len(R)), spearman_all=float(spearmanr(M.score, M.score_cpu).correlation),
                                 spearman_tick_mean=float(np.nanmean(sp_tick)), spearman_tick_p05=float(np.nanquantile(sp_tick, 0.05)),
                                 top16=top_overlap(M, "score", "score_cpu"))
        log.info("VS_GPU_G42 %s", json.dumps(man["vs_gpu_G42"]))
    json.dump(man, open(f"{md}/{tag}.manifest.json", "w"), indent=1)
    log.info("TRAIN_DONE %s", json.dumps({k: man[k] for k in ("tag", "sha256_json", "sha256_onnx", "gate")}))
    if not gate["PASS"]:
        sys.exit(3)


def offline_long(hours):
    """GEOM offline (geom_mats tren TOAN store OHLCV_1H_v2) tai cac gio `hours`, moi sym CO record gio do."""
    b = np.fromfile(SG.OHLCV, dtype=SG.DT)
    ts = b["ts"].astype(np.int64)
    sid = b["sym"].astype(np.int64)
    t0, nh = ts.min(), (ts.max() - ts.min()) // H + 1
    syms = np.unique(sid)
    hi, ci = (ts - t0) // H, np.searchsorted(syms, sid)

    def mat(f):
        M = np.full((nh, len(syms)), np.nan)
        M[hi, ci] = b[f].astype(np.float64)
        return M
    Hm, Lm, Cm = mat("h"), mat("l"), mat("c")
    del b
    F = SG.geom_mats(Hm, Lm, Cm)
    rows = []
    for t in hours:
        k = (t - t0) // H
        if k < 0 or k >= nh:
            continue
        anyf = np.zeros(Cm.shape[1], bool)
        for f in GEOM:
            anyf |= np.isfinite(F[f][k])
        j = np.nonzero(np.isfinite(Cm[k]) | anyf)[0]   # nhu bang offline: atr_ratio co the huu han khi gio khong co record
        d = {"ts": np.full(len(j), t, np.int64), "sid": syms[j]}
        for f in GEOM:
            d[f] = F[f][k, j]
        rows.append(pd.DataFrame(d))
    return pd.concat(rows, ignore_index=True)


def parity(jcsv, mjson, monnx):
    import xgboost as xgb
    if os.path.exists(OUT + "/parity/.done") and os.environ.get("GEOM_PARITY_FORCE") != "1":
        log.info("parity da chot (parity/.done) -> bo qua; GEOM_PARITY_FORCE=1 de chay lai")
        return
    J = pd.read_csv(jcsv, float_precision="round_trip")   # Double.toString Java -> doc lai DUNG bit
    mp = pd.read_csv(SYMMAP)
    s2i = dict(zip(mp.symbol, mp.symId))
    J["sid"] = J.sym.map(s2i)
    res = dict(java_rows=int(len(J)), java_hours=int(J.ts_h.nunique()), java_sym_not_in_map=int(J.sid.isna().sum()))
    J = J[J.sid.notna()].copy()
    J["sid"] = J.sid.astype(np.int64)
    O = offline_long(sorted(J.ts_h.unique()))
    M = O.merge(J.rename(columns={"ts_h": "ts"}), on=["ts", "sid"], how="outer", suffixes=("_off", "_jav"), indicator=True)
    res["rows_both"] = int((M._merge == "both").sum())
    res["rows_only_offline"] = int((M._merge == "left_only").sum())
    res["rows_only_java"] = int((M._merge == "right_only").sum())
    X = M[M._merge == "right_only"]
    Lin = pd.read_csv(REPO + "/data/meta/symbol_lineage_v2.csv")
    res["only_java"] = dict(n_sym=int(X.sid.nunique()), syms_in_lineage=int(X.sym.isin(set(Lin.symbol)).sum()),
                            frac_pos24_nan=float(X.pos24_jav.isna().mean()), frac_dist_low24_eq0=float((X.dist_low24_jav == 0).mean()),
                            frac_atr_nan=float(X.atr_ratio_jav.isna().mean()), frac_range7d_eq0=float((X.range7d_jav == 0).mean()),
                            top_syms={str(k): int(v) for k, v in X.sym.value_counts().head(12).items()})
    B = M[M._merge == "both"]
    per = {}
    for f in GEOM:
        a, j = B[f + "_off"].to_numpy(np.float64), B[f + "_jav"].to_numpy(np.float64)
        fa, fj = np.isfinite(a), np.isfinite(j)
        both = fa & fj
        d = np.abs(a[both] - j[both])
        per[f] = dict(n_both_finite=int(both.sum()), nan_off_only=int((~fa & fj).sum()), nan_jav_only=int((fa & ~fj).sum()),
                      max_abs=float(d.max()) if len(d) else None, frac_le_1e6=float((d <= 1e-6).mean()) if len(d) else None)
    res["per_feature_raw"] = per
    # rank: tinh lai rank Java CHI tren universe offline (dong 'both') -> tach loi cong thuc khoi khac biet universe
    B = B.copy()
    rr = {}
    for src, nm in (("pos24", "rk_pos24"), ("dist_low24", "rk_dist_low24"), ("atr_ratio", "rk_atr_ratio")):
        rj = B.groupby("ts")[src + "_jav"].rank(pct=True).to_numpy(np.float64)
        ro = B[nm + "_off"].to_numpy(np.float64)
        ok = np.isfinite(rj) & np.isfinite(ro)
        rr[nm] = dict(n=int(ok.sum()), max_abs=float(np.abs(rj[ok] - ro[ok]).max()) if ok.any() else None,
                      nan_mismatch=int((np.isfinite(rj) != np.isfinite(ro)).sum()))
    res["rank_on_offline_universe"] = rr
    # top-16 tren ung vien ledger (cung pool train): offline (XGB json) vs replay (ONNX + GEOM Java)
    hours = set(J.ts_h.unique().tolist())
    L = pd.read_parquet(SG.LEDGER_LITE, columns=["ts", "sym", "g1lite"])
    L = L[L.g1lite.notna()].copy()
    L["ts_h"] = (L.ts // H) * H
    L = L[L.ts_h.isin(hours)]
    K = pd.read_parquet(SG.KEEP9_PQ)
    K = K[K.ts.isin(hours)].rename(columns={"ts": "ts_h"})
    L = L.merge(K, on=["ts_h", "sym"], how="left", indicator="kkey")
    Go = pd.read_parquet(GEOM_PQ, columns=["ts", "sym"] + GEOM)   # DUNG input train (md5 6903e178)
    Go = Go[Go.ts.isin(hours)].rename(columns={"ts": "ts_h"})
    Gj = J.drop(columns=["sym"]).rename(columns={"sid": "sym"})[["ts_h", "sym"] + GEOM]
    Lo = L.merge(Go, on=["ts_h", "sym"], how="left")
    Lj = L.merge(Gj, on=["ts_h", "sym"], how="left")
    b = xgb.Booster()
    b.load_model(mjson)
    Xo = Lo[FE].to_numpy(np.float32)
    Xj = Lj[FE].to_numpy(np.float32)
    T = L[["ts", "sym"]].copy()
    T["s_off"] = -b.predict(xgb.DMatrix(Xo, feature_names=FE))
    T["s_rep"] = -ort_run(monnx, Xj)
    T["s_off_onnx"] = -ort_run(monnx, Xo)
    res["ledger_rows"] = int(len(T))
    A, Bj = Lo[GEOM].to_numpy(np.float32), Lj[GEOM].to_numpy(np.float32)   # model nhan float32
    diff = ~((A == Bj) | (np.isnan(A) & np.isnan(Bj)))
    rows = np.nonzero(diff.any(axis=1))[0]
    res["ledger_geom_rows_diff"] = int(len(rows))
    ex = []
    for r_ in rows[:6]:
        f_ = [GEOM[c_] for c_ in np.nonzero(diff[r_])[0]]
        ex.append(dict(ts_h=int(Lo.ts_h.iloc[r_]), sym=int(Lo.sym.iloc[r_]), feats=f_,
                       off=[float(Lo[c_].iloc[r_]) for c_ in f_[:3]], jav=[float(Lj[c_].iloc[r_]) for c_ in f_[:3]]))
    res["ledger_geom_diff_examples"] = ex
    sd = T.assign(d=np.abs(T.s_off - T.s_rep)).sort_values("d", ascending=False).head(3)
    res["score_diff_top"] = [dict(ts=int(x.ts), sym=int(x.sym), d=float(x.d)) for x in sd.itertuples()]
    res["ledger_ticks"] = int(T.ts.nunique())
    res["geom_cov_ledger_off"] = float(Lo.pos24.notna().mean())
    res["geom_cov_ledger_java"] = float(Lj.pos24.notna().mean())
    res["score_max_abs_off_vs_rep"] = float(np.abs(T.s_off - T.s_rep).max())
    res["score_max_abs_json_vs_onnx_same_X"] = float(np.abs(T.s_off - T.s_off_onnx).max())
    res["top16_off_vs_rep"] = top_overlap(T, "s_off", "s_rep")
    res["top16_off_vs_onnx_same_X"] = top_overlap(T, "s_off", "s_off_onnx")
    kk = (L.kkey == "both").to_numpy()
    res["ledger_rows_no_keep9_key"] = int((~kk).sum())
    res["ledger_ts_h_no_keep9_key"] = sorted({int(x) for x in L.ts_h[~kk]})[:10]
    res["top16_off_vs_rep_keep9key_only"] = top_overlap(T[kk], "s_off", "s_rep")
    out = OUT + "/parity/parity_result.json"
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump(res, open(out, "w"), indent=1)
    log.info("PARITY %s", json.dumps(res))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "feat":
        feat()
    elif cmd == "train":
        train(sys.argv[2])
    elif cmd == "parity":
        parity(sys.argv[2], sys.argv[3], sys.argv[4])
    else:
        sys.exit(__doc__)
