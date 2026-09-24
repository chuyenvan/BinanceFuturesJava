"""F4 - Tang TIMING co phai noi chua alpha? Do OFFLINE thuan (khong Java, khong VAL, khong GPU).

Pre-reg: docs/prereg/PREREG_F4.md (commit 1fa042d). Khong sua tieu chi sau khi thay so.

Don vi quan sat = tick 15m tren LUOI LICH DAY DU cua DEV 2022-01-01..2024-06-30 (87,552 tick),
KHONG phai cand_dev.parquet (chi co 4,639 tick p15>=0.008). Luoi mo rong dung lai tu dung
3 nguon goc ma ledger.py dung: wfo_gate_pred.csv + predwf_G015x26 + label_15m/*.pb.

Y_tick = mean(g1lite) cua top-8 coin theo score_g015 tang dan trong tick.
5 ung vien: p15 | br_lag3 | mkt_vol7 | mkt_dd7 | p15_ma24h  (+ br_lag4 CHAN DOAN, khong du thi).
CI: moving-block bootstrap khoi 72h (288 tick), 2000 rep, seed 20260905, do rong x f=1.21.
"""
import glob
import logging
import os
import sys

import numpy as np
import pandas as pd
from scipy import stats

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
L = logging.getLogger("f4")

sys.path.insert(0, "/home/ubuntu/featv2")
sys.path.insert(0, "/home/ubuntu/sel1m_code")
sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
import gate_cfg  # noqa: E402
from funding_label_pb import read_label  # noqa: E402

Q = 900_000              # 15 phut
H = 3_600_000
TZ = 7 * H               # gio VN
BLOCK = 288              # 72h = 288 tick 15m
NREP = 2000
SEED = 20260905
FCOV = 1.21              # he so hieu chinh coverage, COV_RESULT.md muc 4
TOPK = 8
GOOD = 0.07
MA24 = 96                # 24h = 96 tick

DEV0 = int(pd.Timestamp("2022-01-01").value // 1e6) - TZ
DEV1 = int(pd.Timestamp("2024-07-01").value // 1e6) - TZ

GATE_CSV = "/home/ubuntu/claudedata/wfo_gate_pred.csv"
PRED_DIR = "/home/ubuntu/claudedata/predwf_G015x26"
LABEL_GLOB = "/home/ubuntu/label_15m/funding_label_202[2-4]*.pb"
SYMMAP = "/home/ubuntu/selector_pred_out/symbol_map.csv"
BREADTH = "/home/ubuntu/featv2/GATE_BREADTH_DAILY.csv"
FEATV2 = "/home/ubuntu/featv2/feat_v2.parquet"
CACHE = "/home/ubuntu/ledger/f4_ticks.parquet"

CANDS = ["p15", "br_lag3", "mkt_vol7", "mkt_dd7", "p15_ma24h"]
DIAG = ["br_lag4"]


# ------------------------------------------------------------------ luoi tick
def load_gate():
    G = (pd.read_csv(GATE_CSV, usecols=["timestamp", "predReturn15M"])
         .rename(columns={"timestamp": "ts", "predReturn15M": "p15"}))
    G = G[(G.ts % Q == 0) & (G.ts >= DEV0) & (G.ts < DEV1)]
    G = G.drop_duplicates("ts").sort_values("ts").reset_index(drop=True)
    full = np.arange(G.ts.min(), G.ts.max() + Q, Q)
    L.info("gate: tick=%d | luoi lien tuc ky vong=%d | thieu=%d",
           len(G), len(full), len(full) - len(G))
    G["p15_ma24h"] = G.p15.rolling(MA24, min_periods=MA24).mean()
    L.info("p15: mean=%.5f sd=%.5f | mo(>=0.008)=%d (%.2f%%)",
           G.p15.mean(), G.p15.std(), (G.p15 >= 0.008).sum(), 100 * (G.p15 >= 0.008).mean())
    return G


def load_preds():
    dt = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("p0", ">f4"),
                   ("p1", ">f4"), ("p2", ">f4"), ("p3", ">f4")])
    out = []
    for f in sorted(glob.glob(PRED_DIR + "/predict_wf_*.bin")):
        a = np.fromfile(f, dtype=dt)
        ts = a["ts"].astype(np.int64)
        m = (ts >= DEV0) & (ts < DEV1) & (ts % Q == 0)
        if not m.any():
            continue
        out.append(pd.DataFrame({"ts": ts[m],
                                 "sym": a["sym"][m].astype(np.int32),
                                 "p_g015": a["p0"][m].astype(np.float32)}))
    P = pd.concat(out, ignore_index=True).drop_duplicates(["ts", "sym"])
    L.info("preds G015: rows=%d ticks=%d syms=%d", len(P), P.ts.nunique(), P.sym.nunique())
    return P


def build_panel(G, P):
    """Gop nhan + pred + p15 theo tung file pb, chi giu TONG HOP muc tick."""
    mp = pd.read_csv(SYMMAP)
    sym2id = dict(zip(mp.symbol, mp.symId))
    p15map = G.set_index("ts").p15
    dthr_cache = {}
    rows = []
    for f in sorted(glob.glob(LABEL_GLOB)):
        Lb = read_label(f, usecols=["tEpochMs", "symbol", "maxFav_72h",
                                    "retEnd_72h", "nBars_72h"])
        Lb = Lb[(Lb.tEpochMs % Q == 0) & (Lb.tEpochMs >= DEV0) & (Lb.tEpochMs < DEV1)]
        Lb = Lb[Lb.nBars_72h >= 288]
        if not len(Lb):
            continue
        Lb["sym"] = Lb.symbol.map(sym2id)
        Lb = Lb.dropna(subset=["sym"])
        Lb["sym"] = Lb.sym.astype(np.int32)
        Lb = Lb.rename(columns={"tEpochMs": "ts"})[
            ["ts", "sym", "maxFav_72h", "retEnd_72h"]]
        D = Lb.merge(P, on=["ts", "sym"], how="inner")
        if not len(D):
            continue
        D["p15"] = D.ts.map(p15map)
        D = D.dropna(subset=["p15"])
        D["g1lite"] = np.where(D.maxFav_72h >= 0.05,
                               D.maxFav_72h - np.minimum(0.5 * D.maxFav_72h, 0.08),
                               D.retEnd_72h)
        D["score_g015"] = 1.0 - D.p_g015.astype(np.float64)
        D["dyn_thr"] = gate_cfg.dyn_thr(D.score_g015.values)
        D["gate_ok"] = D.p15.values >= D.dyn_thr.values
        D["good"] = D.maxFav_72h >= GOOD
        D = D.sort_values(["ts", "score_g015"], kind="mergesort")
        D["rk"] = D.groupby("ts").cumcount()
        agg = D.groupby("ts").agg(ncoin=("sym", "size"), npass=("gate_ok", "sum"))
        t8 = D[D.rk < TOPK].groupby("ts").agg(
            Y=("g1lite", "mean"), Y2=("good", "mean"))
        t3 = D[D.rk < 3].groupby("ts").agg(Y3=("g1lite", "mean"))
        rows.append(agg.join(t8).join(t3))
        L.info("  %s -> tick=%d coin/tick med=%.0f",
               os.path.basename(f), len(agg), agg.ncoin.median())
        del D, Lb
    T = pd.concat(rows).groupby(level=0).first().reset_index()
    L.info("panel tho: tick=%d", len(T))
    return T


# ------------------------------------------------------- bien ung vien timing
def add_market_feats(T, G):
    T = T.merge(G[["ts", "p15", "p15_ma24h"]], on="ts", how="left")
    T["dt"] = pd.to_datetime(T.ts + TZ, unit="ms")
    T = T.sort_values("ts").reset_index(drop=True)

    B = pd.read_csv(BREADTH, parse_dates=["date"]).sort_values("date")
    # br_lag3: dung nguyen cot cua GATE_BREADTH_DAILY (= br.shift(3)), asof BACKWARD.
    b3 = B[["date", "f_br_lag3"]].dropna().rename(columns={"f_br_lag3": "br_lag3"})
    T = pd.merge_asof(T, b3, left_on="dt", right_on="date", direction="backward")
    T = T.drop(columns=["date"])
    # br_lag4 (CHAN DOAN, khong du thi): br cua ngay D' cuoi cung thoa D'+4ngay <= t.
    b4 = B[["date", "br"]].copy()
    b4["avail"] = b4.date + pd.Timedelta(days=4)
    b4 = b4[["avail", "br"]].rename(columns={"br": "br_lag4"}).sort_values("avail")
    T = pd.merge_asof(T, b4, left_on="dt", right_on="avail", direction="backward")
    T = T.drop(columns=["avail"])

    F = pd.read_parquet(FEATV2, columns=["ts", "vol_7d", "dd_7d"])
    F = F[(F.ts >= DEV0 - 7 * 24 * H) & (F.ts < DEV1)]
    Fa = F.groupby("ts").agg(mkt_vol7=("vol_7d", "mean"), mkt_dd7=("dd_7d", "mean"))
    Fa = Fa.reset_index().sort_values("ts")
    Fa["dt"] = pd.to_datetime(Fa.ts + TZ, unit="ms")
    L.info("feat_v2: gio=%d %s -> %s", len(Fa), Fa.dt.min(), Fa.dt.max())
    T = pd.merge_asof(T, Fa[["dt", "mkt_vol7", "mkt_dd7"]], on="dt", direction="backward")
    for c in CANDS + DIAG:
        L.info("  %-11s nan=%5d (%.2f%%)  mean=%+.5f sd=%.5f",
               c, T[c].isna().sum(), 100 * T[c].isna().mean(), T[c].mean(), T[c].std())
    return T


def get_panel(force=False):
    if os.path.exists(CACHE) and not force:
        T = pd.read_parquet(CACHE)
        L.info("panel tu cache: %s tick=%d", CACHE, len(T))
        return T
    G = load_gate()
    P = load_preds()
    T = build_panel(G, P)
    del P
    T = add_market_feats(T, G)
    T.to_parquet(CACHE)
    L.info("luu %s", CACHE)
    return T


# -------------------------------------------------------------- rank-IC + CI
def spear(x, y):
    return stats.spearmanr(x, y).statistic


def blocks_index(n, rng, nrep, blk=BLOCK):
    nb = int(np.ceil(n / blk))
    starts = rng.integers(0, n - blk + 1, size=(nrep, nb))
    off = np.arange(blk)
    for i in range(nrep):
        yield (starts[i][:, None] + off).ravel()[:n]


def boot_ic(V, y, nrep=NREP, seed=SEED):
    """Moving-block bootstrap, COMMON RANDOM NUMBERS cho moi bien trong V."""
    n = len(y)
    rng = np.random.default_rng(seed)
    names = list(V.keys())
    out = {k: np.empty(nrep) for k in names}
    for r, idx in enumerate(blocks_index(n, rng, nrep)):
        yr = stats.rankdata(y[idx])
        yc = yr - yr.mean()
        den_y = np.sqrt((yc * yc).sum())
        for k in names:
            xr = stats.rankdata(V[k][idx])
            xc = xr - xr.mean()
            d = den_y * np.sqrt((xc * xc).sum())
            out[k][r] = (xc @ yc) / d if d > 0 else np.nan
        if (r + 1) % 500 == 0:
            L.info("  bootstrap %d/%d", r + 1, nrep)
    return out


def ci_widen(lo, hi, point, f=FCOV):
    """Gian do rong CI quanh diem uoc luong theo he so coverage f."""
    return point - f * (point - lo), point + f * (hi - point)


def contest(T, cols, label="PRIMARY Y_tick", ycol="Y"):
    m = T[cols + [ycol]].notna().all(axis=1)
    S = T[m].sort_values("ts").reset_index(drop=True)
    y = S[ycol].values.astype(float)
    V = {c: S[c].values.astype(float) for c in cols}
    L.info("=== %s: n=%d tick (%.1f%% cua %d) | khoi 72h => %d khoi ===",
           label, len(S), 100 * len(S) / len(T), len(T), len(S) // BLOCK)
    pt = {c: spear(V[c], y) for c in cols}
    yr = pd.to_datetime(S.ts + TZ, unit="ms").dt.year
    by = {c: {int(v): spear(V[c][(yr == v).values], y[(yr == v).values])
              for v in sorted(yr.unique())} for c in cols}
    bo = boot_ic(V, y)
    inc = "p15"
    L.info("%-11s %8s %8s %19s %8s | %8s %8s %8s %6s",
           "bien", "rankIC", "|IC|", "CI95(|IC|) x1.21", "sd_boot",
           "IC2022", "IC2023", "IC2024", "dau")
    res = {}
    for c in cols:
        a = np.abs(bo[c])
        lo, hi = np.nanpercentile(a, [2.5, 97.5])
        lo, hi = ci_widen(lo, hi, abs(pt[c]))
        sg = [np.sign(by[c][v]) for v in by[c]]
        cons = "OK" if len(set(sg)) == 1 else "LECH"
        res[c] = dict(ic=pt[c], aic=abs(pt[c]), lo=lo, hi=hi,
                      sd=np.nanstd(a), yr=by[c], cons=cons)
        L.info("%-11s %+8.4f %8.4f  [%+.4f,%+.4f] %8.4f | %+8.4f %+8.4f %+8.4f %6s",
               c, pt[c], abs(pt[c]), lo, hi, np.nanstd(a),
               by[c].get(2022, np.nan), by[c].get(2023, np.nan),
               by[c].get(2024, np.nan), cons)
    L.info("--- HIEU so voi incumbent %s (cung 2000 rep, common random numbers) ---", inc)
    L.info("%-11s %9s %19s %7s %6s %s", "bien", "d=|IC|-|ICp15|",
           "CI95(d) x1.21", "P(d>0)", "dau", "PHAN QUYET")
    for c in cols:
        if c == inc:
            continue
        d = np.abs(bo[c]) - np.abs(bo[inc])
        dp = res[c]["aic"] - res[inc]["aic"]
        lo, hi = np.nanpercentile(d, [2.5, 97.5])
        lo, hi = ci_widen(lo, hi, dp)
        a_ok = lo > 0
        b_ok = res[c]["cons"] == "OK"
        verdict = "DANH BAI" if (a_ok and b_ok) else (
            "KHONG (dau lech)" if a_ok else "KHONG")
        res[c]["dlo"], res[c]["dhi"], res[c]["dp"] = lo, hi, dp
        res[c]["verdict"] = verdict
        L.info("%-11s %+9.4f  [%+.4f,%+.4f] %7.3f %6s %s",
               c, dp, lo, hi, float(np.mean(d > 0)), res[c]["cons"], verdict)
    return res, S


def false_negative(T):
    L.info("=== FALSE NEGATIVE: phan bo Y_tick o tick DONG vs MO (CA HAI dinh nghia) ===")
    S = T[T.Y.notna()].copy()
    L.info("tick co Y_tick = %d / %d luoi", len(S), len(T))
    defs = {
        "Gate-A  p15>=0.008 (tai lap 92.2%% gio-entry)": S.p15 >= 0.008,
        "Gate-B  co >=1 coin qua gate_dyn_ok (tai lap 61.5%%)": S.npass >= 1,
    }
    qs = [10, 25, 50, 75, 90]
    for name, opn in defs.items():
        o, c = S[opn], S[~opn]
        m = o.Y.median()
        q = float((c.Y > m).mean())
        miss = q * len(c)
        L.info("--- %s ---", name)
        L.info("  tick MO=%d (%.2f%%)  DONG=%d (%.2f%%)",
               len(o), 100 * len(o) / len(S), len(c), 100 * len(c) / len(S))
        L.info("  median(Y|MO)=%+.5f  mean(Y|MO)=%+.5f  mean(Y|DONG)=%+.5f  d=%+.5f",
               m, o.Y.mean(), c.Y.mean(), o.Y.mean() - c.Y.mean())
        L.info("  q = P(Y|DONG > median(Y|MO)) = %.4f", q)
        L.info("  KHOI LUONG bo lo = q x n_DONG = %.0f tick  |  0.5 x n_MO = %.0f  |  ty so = %.2fx",
               miss, 0.5 * len(o), miss / (0.5 * len(o)))
        L.info("  percentile Y  MO  : %s",
               {f"p{p}": round(float(np.percentile(o.Y, p)), 5) for p in qs})
        L.info("  percentile Y  DONG: %s",
               {f"p{p}": round(float(np.percentile(c.Y, p)), 5) for p in qs})
        L.info("  P(good) top-8  MO=%.4f DONG=%.4f | Y3(top-3) MO=%+.5f DONG=%+.5f",
               o.Y2.mean(), c.Y2.mean(), o.Y3.mean(), c.Y3.mean())
        ks = stats.ks_2samp(o.Y.values, c.Y.values)
        L.info("  KS 2-sample D=%.4f (n_eff nho hon n rat nhieu -> KHONG doc p-value)", ks.statistic)


def wfo_model(T):
    """DUNG MOT model khai bao trong pre-reg: XGBRegressor CPU, 5 bien, WFO quy, purge 72h."""
    try:
        from xgboost import XGBRegressor
    except Exception as e:
        L.warning("khong co xgboost (%s) => KHONG train. Ghi la khong train.", e)
        return None
    m = T[CANDS + ["Y"]].notna().all(axis=1)
    S = T[m].sort_values("ts").reset_index(drop=True)
    S["qtr"] = pd.to_datetime(S.ts + TZ, unit="ms").dt.to_period("Q")
    qs = sorted(S.qtr.unique())
    L.info("=== MODEL (pre-reg muc 6): XGBRegressor cpu/hist, WFO %d quy, purge 72h ===", len(qs))
    S["pred"] = np.nan
    for i, q in enumerate(qs):
        if i == 0:
            continue
        te = (S.qtr == q).values
        tr = (S.qtr < q).values
        t0 = S.ts[te].min()
        tr = tr & (S.ts.values < t0 - BLOCK * Q)   # purge 72h truoc ranh gioi
        if tr.sum() < 500:
            continue
        mdl = XGBRegressor(n_estimators=300, max_depth=4, learning_rate=0.05,
                           subsample=0.8, colsample_bytree=0.8, random_state=42,
                           tree_method="hist", device="cpu", n_jobs=4, verbosity=0)
        mdl.fit(S.loc[tr, CANDS].values, S.loc[tr, "Y"].values)
        S.loc[te, "pred"] = mdl.predict(S.loc[te, CANDS].values)
        L.info("  quy %s: train=%d test=%d", q, int(tr.sum()), int(te.sum()))
    O = S[S.pred.notna()].reset_index(drop=True)
    L.info("OOS tick=%d (%.1f%% cua %d)", len(O), 100 * len(O) / len(S), len(S))
    y = O.Y.values.astype(float)
    V = {"model": O.pred.values.astype(float), "p15": O.p15.values.astype(float)}
    pt = {k: spear(V[k], y) for k in V}
    yr = pd.to_datetime(O.ts + TZ, unit="ms").dt.year
    by = {k: {int(v): spear(V[k][(yr == v).values], y[(yr == v).values])
              for v in sorted(yr.unique())} for k in V}
    bo = boot_ic(V, y)
    for k in V:
        a = np.abs(bo[k])
        lo, hi = ci_widen(*np.nanpercentile(a, [2.5, 97.5]), abs(pt[k]))
        L.info("%-6s rankIC=%+.4f |IC|=%.4f CI95x1.21=[%+.4f,%+.4f] | theo nam %s",
               k, pt[k], abs(pt[k]), lo, hi,
               {a2: round(b2, 4) for a2, b2 in by[k].items()})
    d = np.abs(bo["model"]) - np.abs(bo["p15"])
    dp = abs(pt["model"]) - abs(pt["p15"])
    lo, hi = ci_widen(*np.nanpercentile(d, [2.5, 97.5]), dp)
    sg = set(np.sign(list(by["model"].values())))
    ok = (lo > 0) and (len(sg) == 1)
    L.info("HIEU model - p15 (chi tren %d tick OOS): d=%+.4f CI95x1.21=[%+.4f,%+.4f] "
           "P(d>0)=%.3f dau=%s => %s", len(O), dp, lo, hi, float(np.mean(d > 0)),
           "OK" if len(sg) == 1 else "LECH", "DANH BAI" if ok else "KHONG")
    return dict(ic=pt, ci=(lo, hi), d=dp, by=by, n=len(O))


def main():
    L.info("F4 TIMING - pre-reg docs/prereg/PREREG_F4.md commit 1fa042d")
    gate_cfg.describe()
    T = get_panel(force="--rebuild" in sys.argv)
    L.info("=== 0. LUOI TICK ===")
    L.info("tick=%d | co Y_tick=%d (%.2f%%) | ncoin med=%.0f min=%.0f",
           len(T), T.Y.notna().sum(), 100 * T.Y.notna().mean(),
           T.ncoin.median(), T.ncoin.min())
    bad = (T.ncoin < TOPK).values
    L.info("tick bi loai vi <%d coin = %d (pre-reg muc 2: tick hop le)", TOPK, int(bad.sum()))
    T.loc[bad, ["Y", "Y2", "Y3"]] = np.nan
    L.info("Y_tick: %s", T.Y.describe().round(5).to_dict())
    L.info("gate MO: A(p15>=0.008)=%d  B(npass>=1)=%d",
           int((T.p15 >= 0.008).sum()), int((T.npass >= 1).sum()))
    res, S = contest(T, CANDS, "PRIMARY  Y_tick = mean(g1lite) top-8")
    L.info("=== CHAN DOAN br_lag4 (sach ro ri, KHONG du thi) ===")
    contest(T, ["p15", "br_lag3", "br_lag4"], "CHAN DOAN br_lag3 vs br_lag4")
    for yc, nm in (("Y2", "SECONDARY  P(maxFav_72h>=0.07) top-8"),
                   ("Y3", "SECONDARY  mean(g1lite) top-3")):
        L.info("=== %s (bao cao, KHONG dung de chon) ===", nm)
        contest(T, CANDS, nm, ycol=yc)
    false_negative(T)
    wfo_model(T)
    L.info("F4 DONE")


if __name__ == "__main__":
    main()
