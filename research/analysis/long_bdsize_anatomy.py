#!/usr/bin/env python3
"""AUDIT LONG_BDSIZE_ANATOMY 2026-10-03 — 0-sim, CHI DOC (khong Java, khong Kaggle, DEV <= 2025-12-31).

L3a  Cham lai BD_SIZE_ADAPT (4 run Oracle java/devrun, nen = T170 parity md5 efb793e2, KHONG phai B0)
     bang thuoc dung: (i) bootstrap return NGAY MTM (b+unP tu sim.out) GHEP CAP block-10d, NREP 2000,
     seed 20260905: dCAGR, dmaxDD, dCalmar_MTM, Sharpe, exposure TB, beta(BTC); (ii) cung exposure
     (nen x c, c = expoTB_variant/expoTB_nen, chot truoc boot); (iii) theo nam; (iv) dPnL ghep cap theo lenh
     (size-neutral, khop sym|start|level) tach "chon lenh" khoi "size".
L3b  Giai phau PnL B0 (kaggle_sim/out/de-p1, md5 650c386f) theo gio UTC/VN, thu, thu tu trong episode
     (episode = cum entry cach nhau < 72h), so lenh mo luc vao, ret BTC 1h/4h luc vao, tier quoteVol (ngay UTC
     truoc), tuoi listing (lineage v2), vao lai cung coin trong 72h. CI block-72h (luoi toan mau) cua mean ROI;
     ung vien loai bo: dPnL = -SumPnL lat + CI + theo nam. Xac minh mui gio printDone bang CLOSES_1H_v2.
Usage: python3 long_bdsize_anatomy.py OUT_JSON
"""
import sys, json, hashlib, re, math
import numpy as np, pandas as pd

REPO = "/home/ubuntu/src/BinanceFuturesJava"
SEED, NREP = 20260905, 2000
DEV = "/home/ubuntu/java/devrun"
BD = {"PARITY": "X1_GS_T170_2021_BD_PARITY", "DOWN50": "X1_GS_T170_2021_BD_DOWN50",
      "DOWN25": "X1_GS_T170_2021_BD_DOWN25", "UP50": "X1_GS_T170_2021_BD_UP50"}
BD_MD5 = {"PARITY": "efb793e2468ca3a7318da0f0ad23d4fc", "DOWN50": "976de01219f1805359234e32e90c4201",
          "DOWN25": "fa2876cf8cfc8f4b1ecafb2280c53e1c", "UP50": "f7d31da258ce750b606863936d1a61c5"}
B0 = "/home/ubuntu/kaggle_sim/out/de-p1"
B0_MD5_PREFIX = "650c386f"
V2 = "/home/ubuntu/java/fsrun/CLOSES_1H_v2.bin"
V2_MD5 = "58f56069e8e1a7c739011ddfa13e9636"
MAP = "/home/ubuntu/selector_pred_out/symbol_map.csv"
LIN = REPO + "/data/meta/symbol_lineage_v2.csv"
QVDIR = "/home/ubuntu/claude_master/1002/p0a_cache/qv"
TZ_H = 7
H = 3600000
RX = re.compile(r"Update (\d{8}) \d\d:\d\d => b:\s*(-?\d+).*?unP:\s*(-?\d+)")
DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("c", ">f4")])
ANCHOR = pd.Timestamp("2021-07-01")
OUT = sys.argv[1] if len(sys.argv) > 1 else "/tmp/long_bdsize_anatomy.json"
R = {"meta": {"seed": SEED, "nrep": NREP}}


def md5(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def load_pd(path):
    d = pd.read_csv(path)
    d.columns = [c.strip() for c in d.columns]
    d = d[d.side == "BUY"].copy()
    d["ts"] = pd.to_datetime(d.start, format="%Y%m%d %H:%M")
    d["te"] = pd.to_datetime(d.end, format="%Y%m%d %H:%M")
    d["notional"] = d.quantity * d.entry
    d["key"] = d.sym + "|" + d.start + "|" + d.level
    d["blk"] = ((d.ts - ANCHOR).dt.total_seconds() // (72 * 3600)).astype(int)
    return d.sort_values("ts", kind="mergesort").reset_index(drop=True)


def load_daily(run):
    rows = []
    with open(run + "/logs/sim.out", errors="ignore") as fh:
        for line in fh:
            m = RX.search(line)
            if m:
                rows.append((m.group(1), int(m.group(2)), int(m.group(3))))
    e = pd.DataFrame(rows, columns=["d", "b", "unP"]).drop_duplicates("d", keep="last")
    e["t"] = pd.to_datetime(e.d, format="%Y%m%d")      # snapshot 07:00 GMT+7 == 00:00 UTC cung ngay
    e = e.set_index("t").sort_index()
    return (e.b + e.unP).astype(float)


def load_v2():
    a = np.fromfile(V2, dtype=DT)
    return pd.DataFrame({"ts": a["ts"].astype(np.int64), "sid": a["sym"].astype(np.int64),
                         "c": a["c"].astype(np.float64)})


# ======================================================================= L3a helpers
def exposure_daily(d, eq):
    """gross notional mo TB theo phut trong ngay UTC [d, d+1) / equity snapshot d (00:00 UTC)."""
    t0 = eq.index[0]
    T = len(eq) * 1440
    s = (((d.ts - pd.Timedelta(hours=TZ_H)) - t0).dt.total_seconds() // 60).astype(np.int64).clip(0, T)
    e = (((d.te - pd.Timedelta(hours=TZ_H)) - t0).dt.total_seconds() // 60).astype(np.int64).clip(0, T)
    arr = np.zeros(T + 1)
    np.add.at(arr, s.to_numpy(), d.notional.to_numpy())
    np.add.at(arr, e.to_numpy(), -d.notional.to_numpy())
    op = np.cumsum(arr)[:T].reshape(len(eq), 1440).mean(1)
    return op / eq.to_numpy()


def mets(r):
    r = np.asarray(r, float)
    p = np.cumprod(1 + r)
    pk = np.maximum.accumulate(np.concatenate([[1.0], p]))[1:]
    dd = min(0.0, float((p / pk - 1).min()))
    cagr = p[-1] ** (365.0 / len(r)) - 1
    sd = r.std(ddof=1)
    return {"cagr": 100 * cagr, "maxdd": 100 * dd, "calmar": cagr / abs(dd) if dd < 0 else float("nan"),
            "sharpe": float(r.mean() / sd * math.sqrt(365)) if sd > 0 else float("nan"),
            "ret": 100 * (p[-1] - 1)}


def beta(r, x):
    x = np.asarray(x, float); r = np.asarray(r, float)
    ok = np.isfinite(x) & np.isfinite(r)
    return float(np.cov(r[ok], x[ok])[0, 1] / np.var(x[ok], ddof=1))


def block_idx(T, B, rng):
    nb = int(math.ceil(T / B))
    picks = rng.integers(0, nb, nb)
    return np.concatenate([np.arange(p * B, min(p * B + B, T)) for p in picks])


def ci(a):
    a = np.asarray(a, float); a = a[np.isfinite(a)]
    lo, hi = np.percentile(a, [2.5, 97.5])
    return [float(lo), float(hi)]


def paired_trades(b, x, mask_b=None, mask_x=None):
    """dPnL size-neutral (khop sym|start|level): common (p_x-p_b)/100*N_b; chi-x +p_x/100*N_x; chi-b -p_b/100*N_b.
    CI block-72h theo gio vao (anchor 2021-07-01), NREP 2000, seed."""
    b = b if mask_b is None else b[mask_b]
    x = x if mask_x is None else x[mask_x]
    b = b.drop_duplicates("key").set_index("key"); x = x.drop_duplicates("key").set_index("key")
    cm = b.index.intersection(x.index); ob = b.index.difference(x.index); oa = x.index.difference(b.index)
    dm = (x.loc[cm, "profit"] - b.loc[cm, "profit"]) / 100 * b.loc[cm, "notional"]
    t = pd.concat([pd.DataFrame({"blk": b.loc[cm, "blk"], "v": dm, "yr": b.loc[cm, "ts"].dt.year}),
                   pd.DataFrame({"blk": b.loc[ob, "blk"], "v": -(b.loc[ob, "profit"] / 100 * b.loc[ob, "notional"]),
                                 "yr": b.loc[ob, "ts"].dt.year}),
                   pd.DataFrame({"blk": x.loc[oa, "blk"], "v": x.loc[oa, "profit"] / 100 * x.loc[oa, "notional"],
                                 "yr": x.loc[oa, "ts"].dt.year})])
    s = t.groupby("blk").v.sum()
    allb = np.arange(0, max(b.blk.max(), x.blk.max()) + 1)
    s = s.reindex(allb, fill_value=0.0).to_numpy()
    rng = np.random.default_rng(SEED)
    bs = np.array([s[rng.integers(0, len(s), len(s))].sum() for _ in range(NREP)])
    act = float(x.pnl.sum() - b.pnl.sum())
    # thanh phan size tren lenh khop: (N_x - N_b) * p_x/100
    size_c = float(((x.loc[cm, "notional"] - b.loc[cm, "notional"]) * x.loc[cm, "profit"] / 100).sum())
    return {"n_b": int(len(b)), "n_x": int(len(x)), "n_common": int(len(cm)), "n_only_b": int(len(ob)),
            "n_only_x": int(len(oa)), "frac_common_profit_changed": float((dm.abs() > 1e-9).mean()) if len(dm) else 0.0,
            "d_size_neutral": float(t.v.sum()), "ci95": ci(bs), "d_matched_only": float(dm.sum()),
            "d_actual_pnl": act, "size_component_matched": size_c,
            "notional_ratio_matched": float(x.loc[cm, "notional"].sum() / b.loc[cm, "notional"].sum()) if len(cm) else float("nan"),
            "by_year_size_neutral": {str(k): float(v) for k, v in t.groupby("yr").v.sum().items()}}


# ======================================================================= L3a
def run_l3a(btc_daily):
    A = {"base": "PARITY (X1_GS_T170_2021, nen T170 — KHONG phai B0; BD_SIZE_ADAPT chua tung chay tren B0)",
         "source": "Oracle java/devrun (ca 4 run cung nguon Oracle, TICKER_SOURCE=file)"}
    L, E, X = {}, {}, {}
    for k, tag in BD.items():
        p = f"{DEV}/{tag}/storage/printDone.csv"
        h = md5(p)
        A.setdefault("md5", {})[k] = h
        assert h == BD_MD5[k], (k, h)
        L[k] = load_pd(p)
        E[k] = load_daily(f"{DEV}/{tag}")
        X[k] = exposure_daily(L[k], E[k])
    idx = E["PARITY"].index
    for k in E:
        assert E[k].index.equals(idx), k
    bt = btc_daily.reindex(idx)
    rb_btc = (bt / bt.shift(1) - 1).to_numpy()[1:]
    Rr = {k: (E[k] / E[k].shift(1) - 1).to_numpy()[1:] for k in E}
    Xe = {k: X[k][:-1] for k in X}          # exposure ngay i dung cho return i->i+1
    T = len(Rr["PARITY"])
    A["n_days"] = T; A["date_first"] = str(idx[0].date()); A["date_last"] = str(idx[-1].date())
    pt = {}
    for k in Rr:
        m = mets(Rr[k]); m["expo_mean"] = float(np.mean(Xe[k])); m["beta_btc"] = beta(Rr[k], rb_btc)
        m["equity_final"] = float(E[k].iloc[-1]); m["n_trades"] = int(len(L[k]))
        m["sum_pnl"] = float(L[k].pnl.sum())
        bd = L[k][L[k].level == "BIG_DOWN"]
        m["bd_n"] = int(len(bd)); m["bd_sum_pnl"] = float(bd.pnl.sum()); m["bd_notional_mean"] = float(bd.notional.mean())
        pt[k] = m
    A["point"] = pt
    cfac = {k: pt[k]["expo_mean"] / pt["PARITY"]["expo_mean"] for k in Rr if k != "PARITY"}
    A["c_expo"] = cfac
    # bootstrap ghep cap block-10d
    rng = np.random.default_rng(SEED)
    keys = ["cagr", "maxdd", "calmar", "sharpe"]
    D = {k: {m: [] for m in keys + ["beta", "expo"]} for k in cfac}
    DS = {k: {m: [] for m in keys} for k in cfac}
    for _ in range(NREP):
        ii = block_idx(T, 10, rng)
        mb = mets(Rr["PARITY"][ii])
        bb = beta(Rr["PARITY"][ii], rb_btc[ii])
        for k, c in cfac.items():
            mv = mets(Rr[k][ii]); ms = mets(c * Rr["PARITY"][ii])
            for m in keys:
                D[k][m].append(mv[m] - mb[m]); DS[k][m].append(mv[m] - ms[m])
            D[k]["beta"].append(beta(Rr[k][ii], rb_btc[ii]) - bb)
            D[k]["expo"].append(float(np.mean(Xe[k][ii]) - np.mean(Xe["PARITY"][ii])))
    out = {}
    for k, c in cfac.items():
        ms_pt = mets(c * Rr["PARITY"])
        o = {"vs_base": {}, "vs_base_same_expo": {"c": c, "scaled_base_point": ms_pt}}
        for m in keys:
            o["vs_base"][m] = {"obs": pt[k][m] - pt["PARITY"][m], "ci95": ci(D[k][m])}
            o["vs_base_same_expo"][m] = {"obs": pt[k][m] - ms_pt[m], "ci95": ci(DS[k][m])}
        o["vs_base"]["beta"] = {"obs": pt[k]["beta_btc"] - pt["PARITY"]["beta_btc"], "ci95": ci(D[k]["beta"])}
        o["vs_base"]["expo"] = {"obs": pt[k]["expo_mean"] - pt["PARITY"]["expo_mean"], "ci95": ci(D[k]["expo"])}
        out[k] = o
    A["paired_daily"] = out
    # (iii) theo nam
    yrs = sorted(set(idx[1:].year))
    Y = {}
    for y in yrs:
        msk = (idx[1:].year == y)
        row = {}
        for k in Rr:
            row[k] = mets(Rr[k][msk])
        for k, c in cfac.items():
            row[k + "_scaledbase"] = mets(c * Rr["PARITY"][msk])
        Y[str(y)] = row
    A["by_year"] = Y
    # (iv) ghep cap theo lenh
    pr = {}
    for k in cfac:
        pr[k] = {"all": paired_trades(L["PARITY"], L[k]),
                 "bd_only": paired_trades(L["PARITY"], L[k], L["PARITY"].level == "BIG_DOWN", L[k].level == "BIG_DOWN"),
                 "non_bd": paired_trades(L["PARITY"], L[k], L["PARITY"].level != "BIG_DOWN", L[k].level != "BIG_DOWN")}
    A["paired_trades"] = pr
    return A


# ======================================================================= L3b
def tz_check(d, v2, n2s):
    """Can gia: entry vs close 1h v2 cua nen chua phut vao, theo gia thuyet offset h (UTC = local - h)."""
    s2i = {v: k for k, v in n2s.items()}
    d = d.copy()
    d["sid"] = (d.sym + "USDT").map(s2i)
    cand = d[(d.ts.dt.minute >= 57) & d.sid.notna()].index.to_numpy()
    rng = np.random.default_rng(SEED)
    pick = np.sort(rng.choice(cand, 20, replace=False))
    sids = set(d.sid.dropna().astype(int))
    vv = v2[v2.sid.isin(sids) & np.isfinite(v2.c)].set_index(["sid", "ts"]).c
    res = {}
    for h in range(-9, 10):
        utc = d.ts - pd.Timedelta(hours=h)
        cts = (utc.dt.floor("h") + pd.Timedelta(hours=1)).astype("int64") // 10**6
        key = list(zip(d.sid.fillna(-1).astype(int), cts))
        c = vv.reindex(pd.MultiIndex.from_tuples(key)).to_numpy()
        rel = np.abs(d.entry.to_numpy() / c - 1)
        sel = rel[pick]; allm = rel[cand]
        res[str(h)] = {"pick20_median_rel": float(np.nanmedian(sel)), "pick20_n_lt_0.5pct": int(np.nansum(sel < 0.005)),
                       "pick20_n_found": int(np.isfinite(sel).sum()),
                       "all_min57_median_rel": float(np.nanmedian(allm)), "all_min57_n": int(np.isfinite(allm).sum())}
    best = min(res, key=lambda h: res[h]["pick20_median_rel"])
    rows20 = d.loc[pick, ["sym", "start", "entry"]].copy()
    utc = rows20.start.pipe(pd.to_datetime, format="%Y%m%d %H:%M") - pd.Timedelta(hours=7)
    cts = (utc.dt.floor("h") + pd.Timedelta(hours=1)).astype("int64") // 10**6
    rows20["close_v2_h7"] = vv.reindex(pd.MultiIndex.from_tuples(list(zip(d.loc[pick, "sid"].astype(int), cts)))).to_numpy()
    return {"by_offset": res, "best_offset_h": int(best),
            "sample20": rows20.astype({"entry": float}).to_dict(orient="records")}


def build_features(d, v2, n2s):
    s2i = {v: k for k, v in n2s.items()}
    d = d.copy()
    d["utc"] = d.ts - pd.Timedelta(hours=TZ_H)
    d["ute"] = d.te - pd.Timedelta(hours=TZ_H)
    d["hour_utc"] = d.utc.dt.hour
    d["wd_utc"] = d.utc.dt.dayofweek
    # episode: entry cach entry truoc < 72h => cung episode
    t = d.utc.to_numpy()
    gap = np.diff(t).astype("timedelta64[m]").astype(float) / 60.0
    ep = np.concatenate([[0], np.cumsum(gap >= 72)])
    d["ep"] = ep
    d["ep_rank"] = d.groupby("ep").utc.rank(method="min").astype(int)
    d["ep_ord_b"] = pd.cut(d.ep_rank, [0, 5, 20, 10**9], labels=["1-5", "6-20", ">20"])
    # so lenh dang mo luc vao (gom chinh no + lenh cung phut): ts_j <= ts_i < te_j
    ts_ = d.utc.to_numpy().astype("datetime64[m]").astype(np.int64)
    te_ = d.ute.to_numpy().astype("datetime64[m]").astype(np.int64)
    so = np.sort(ts_); se = np.sort(te_)
    d["n_open"] = np.searchsorted(so, ts_, side="right") - np.searchsorted(se, ts_, side="right")
    d["n_open_b"] = pd.cut(d.n_open, [0, 5, 15, 30, 10**9], labels=["1-5", "6-15", "16-30", ">30"])
    # BTC ret 1h/4h: nen da dong gan nhat (close ts <= entry utc)
    btc = v2[(v2.sid == 1) & np.isfinite(v2.c)].set_index("ts").c
    c0 = (d.utc.dt.floor("h")).astype("int64") // 10**6
    p0 = btc.reindex(c0).to_numpy(); p1 = btc.reindex(c0 - H).to_numpy(); p4 = btc.reindex(c0 - 4 * H).to_numpy()
    d["btc1h"] = 100 * (p0 / p1 - 1); d["btc4h"] = 100 * (p0 / p4 - 1)
    d["btc1h_b"] = pd.cut(d.btc1h, [-1e9, -2, -1, -0.3, 0.3, 1e9], labels=["<=-2", "(-2,-1]", "(-1,-0.3]", "(-0.3,0.3]", ">0.3"])
    d["btc4h_b"] = pd.cut(d.btc4h, [-1e9, -4, -2, -0.5, 0.5, 1e9], labels=["<=-4", "(-4,-2]", "(-2,-0.5]", "(-0.5,0.5]", ">0.5"])
    # tier quoteVol: qv ngay UTC truoc ngay vao (causal)
    import glob
    qv = pd.concat([pd.read_parquet(f, columns=["date", "sym", "qv"]) for f in sorted(glob.glob(QVDIR + "/*.parquet"))])
    qv = qv.drop_duplicates(["date", "sym"]).set_index(["sym", "date"]).qv
    key = pd.MultiIndex.from_arrays([d.sym + "USDT", d.utc.dt.normalize() - pd.Timedelta(days=1)])
    d["qv_prev"] = qv.reindex(key).to_numpy()
    d["qv_b"] = pd.cut(d.qv_prev, [-1, 5e6, 2e7, 1e8, 1e15], labels=["<5M", "5-20M", "20-100M", ">=100M"]).astype(object)
    d.loc[d.qv_prev.isna(), "qv_b"] = "NA"
    # tuoi listing (lineage v2 first_real_ts, UTC)
    lin = pd.read_csv(LIN)
    fr = pd.to_datetime(lin.set_index("symbol").first_real_ts)
    d["first_real"] = (d.sym + "USDT").map(fr)
    d["age_d"] = (d.utc - d.first_real).dt.total_seconds() / 86400
    d["age_b"] = pd.cut(d.age_d, [-1e9, 30, 180, 1e9], labels=["<30d", "30-180d", ">180d"]).astype(object)
    d.loc[d.age_d.isna(), "age_b"] = "NA"
    # 78 ma left-censored (first_real <= 2021-01-01, truoc dau du lieu) => tuoi >= 181 ngay khi vao (>= 2021-07-01)
    lc = set(lin.loc[lin.first_real_src.astype(str).str.startswith("left_censored"), "symbol"])
    d.loc[(d.sym + "USDT").isin(lc) & d.age_d.isna(), "age_b"] = ">180d"
    # vao lai cung coin trong 72h: co lenh truoc cung coin (entry som hon) ma te >= entry - 72h
    re_ = np.zeros(len(d), bool)
    for s, g in d.groupby("sym"):
        g = g.sort_values("utc")
        mx = g.ute.cummax().shift(1)
        same_t = g.utc.duplicated(keep="first")    # cung phut: lenh truoc "chua vao truoc"
        flag = (mx >= g.utc - pd.Timedelta(hours=72)) & ~same_t
        re_[g.index.to_numpy()] = flag.fillna(False).to_numpy()
    d["reentry"] = np.where(re_, "re-entry<=72h", "first")
    d["yr"] = d.utc.dt.year
    return d


DIMS = [("hour_utc", "gio vao UTC (VN = UTC+7)"), ("wd_utc", "thu trong tuan (UTC, 0=Mon)"),
        ("ep_ord_b", "thu tu lenh trong episode (<72h)"), ("n_open_b", "so lenh dang mo luc vao (gom chinh no)"),
        ("btc1h_b", "ret BTC 1h luc vao (%)"), ("btc4h_b", "ret BTC 4h luc vao (%)"),
        ("qv_b", "tier quoteVol ngay UTC truoc (USD)"), ("age_b", "tuoi listing (lineage v2)"),
        ("reentry", "vao lai cung coin trong 72h")]
PRE_NAMED = [("ep_ord_b", ">20"), ("n_open_b", ">30"), ("age_b", "<30d"), ("reentry", "re-entry<=72h")]


def run_l3b(d):
    B = {}
    nblk = int(d.blk.max()) + 1
    rng = np.random.default_rng(SEED)
    W = np.stack([np.bincount(rng.integers(0, nblk, nblk), minlength=nblk) for _ in range(NREP)]).astype(float)
    bi = d.blk.to_numpy()
    prof = d.profit.to_numpy(float); pnl = d.pnl.to_numpy(float)
    S_all = W @ np.bincount(bi, prof, nblk); N_all = W @ np.bincount(bi, minlength=nblk).astype(float)
    TOT = float(pnl.sum()); NT = len(d); MU = float(prof.mean())
    B["total"] = {"n": NT, "sum_pnl": TOT, "mean_roi": MU, "win": float((pnl > 0).mean() * 100),
                  "sl_rate": float((d.status == "STOP_LOSS_DONE").mean() * 100), "n_blocks72": nblk}
    k_cells = 0
    tabs = {}
    K = int(sum(d[dim].astype(str).nunique() for dim, _ in DIMS))
    INF = math.sqrt(2 * math.log(K))

    def infl(c):
        m = (c[0] + c[1]) / 2
        return [m - (m - c[0]) * INF, m + (c[1] - m) * INF]
    for dim, lab in DIMS:
        rows = {}
        for v, g in d.groupby(dim, observed=True):
            k_cells += 1
            m = (d[dim] == v).to_numpy()
            n = int(m.sum())
            s_b = np.bincount(bi[m], prof[m], nblk); n_b = np.bincount(bi[m], minlength=nblk).astype(float)
            p_b = np.bincount(bi[m], pnl[m], nblk)
            Sb = W @ s_b; Nb = W @ n_b
            with np.errstate(invalid="ignore", divide="ignore"):
                mean_bs = Sb / Nb
                rest_bs = (S_all - Sb) / (N_all - Nb)
            row = {"n": n, "sum_pnl": float(pnl[m].sum()), "pct_sum_pnl": float(100 * pnl[m].sum() / TOT),
                   "mean_roi": float(prof[m].mean()), "win": float(100 * (pnl[m] > 0).mean()),
                   "sl_rate": float(100 * (d.status.to_numpy()[m] == "STOP_LOSS_DONE").mean()),
                   "excess_pnl": float(pnl[m].sum() - n / NT * TOT)}
            if n >= 100:
                row["ci_mean_roi"] = ci(mean_bs)
                row["d_vs_rest"] = float(prof[m].mean() - prof[~m].mean())
                row["ci_d_vs_rest"] = ci(mean_bs - rest_bs)
                row["ci_sum_pnl"] = ci(W @ p_b)
                lo, hi = row["ci_mean_roi"]
                row["mean_sig"] = "POS" if lo > 0 else ("NEG" if hi < 0 else "0")
                lo2, hi2 = row["ci_d_vs_rest"]
                row["rest_sig"] = "BETTER" if lo2 > 0 else ("WORSE" if hi2 < 0 else "0")
                row["big_and_sig"] = bool(abs(row["pct_sum_pnl"]) >= 10 and row["mean_sig"] != "0")
                row["ci_mean_roi_infl"] = infl(row["ci_mean_roi"])
                row["ci_d_vs_rest_infl"] = infl(row["ci_d_vs_rest"])
                lo3, hi3 = row["ci_d_vs_rest_infl"]
                row["rest_sig_infl"] = "BETTER" if lo3 > 0 else ("WORSE" if hi3 < 0 else "0")
            if dim == "hour_utc":
                row["hour_vn"] = int((int(v) + 7) % 24)
            rows[str(v)] = row
        tabs[dim] = {"label": lab, "rows": rows}
    B["tables"] = tabs
    B["k_cells"] = k_cells
    assert k_cells == K, (k_cells, K)
    allrows = [(dim, v, r) for dim in tabs for v, r in tabs[dim]["rows"].items() if r["n"] >= 100]
    top = sorted(allrows, key=lambda x: -abs(x[2]["excess_pnl"]))[:8]
    B["top_excess"] = [{"slice": f"{dm}={v}", "n": r["n"], "sum_pnl": r["sum_pnl"], "excess_pnl": r["excess_pnl"],
                        "mean_roi": r["mean_roi"], "d_vs_rest": r["d_vs_rest"], "ci_d_vs_rest": r["ci_d_vs_rest"],
                        "ci_d_vs_rest_infl": r["ci_d_vs_rest_infl"], "rest_sig": r["rest_sig"],
                        "rest_sig_infl": r["rest_sig_infl"]} for dm, v, r in top]
    B["infl_k"] = math.sqrt(2 * math.log(k_cells))
    # ung vien loai bo: pre-named + moi o n>=100 co mean NEG hoac WORSE vs rest
    cands = list(PRE_NAMED)
    for dim, _ in DIMS:
        for v, r in tabs[dim]["rows"].items():
            if r["n"] >= 100 and (r.get("mean_sig") == "NEG" or r.get("rest_sig") == "WORSE") and (dim, v) not in cands:
                cands.append((dim, v))
    EX = {}
    for dim, v in cands:
        m = (d[dim].astype(str) == v).to_numpy()
        if m.sum() == 0:
            EX[f"{dim}={v}"] = {"n": 0}
            continue
        p_b = np.bincount(bi[m], pnl[m], nblk)
        dd = -(W @ p_b)
        g = d[m]
        EX[f"{dim}={v}"] = {"n": int(m.sum()), "pre_named": (dim, v) in PRE_NAMED,
                            "d_pnl_if_excluded": float(-pnl[m].sum()), "ci95": ci(dd),
                            "d_pnl_pct_of_total": float(-100 * pnl[m].sum() / TOT),
                            "mean_roi": float(prof[m].mean()), "win": float(100 * (pnl[m] > 0).mean()),
                            "by_year": {str(k): float(-x) for k, x in g.groupby("yr").pnl.sum().items()},
                            "n_by_year": {str(k): int(x) for k, x in g.groupby("yr").size().items()},
                            "d_equal_notional_1k": float(-(prof[m] / 100 * 1000).sum())}
    B["exclusion_candidates"] = EX
    return B


def main():
    h2 = md5(V2)
    assert h2 == V2_MD5, h2
    R["meta"]["closes_v2_md5"] = h2
    v2 = load_v2()
    mp = pd.read_csv(MAP)
    n2s = dict(zip(mp.symId.astype(int), mp.symbol.astype(str)))
    # BTC daily close tai 00:00 UTC (== snapshot sim.out 07:00 GMT+7)
    btc = v2[(v2.sid == 1) & np.isfinite(v2.c)]
    btc_daily = pd.Series(btc.c.to_numpy(), index=pd.to_datetime(btc.ts, unit="ms")).loc[lambda s: s.index.hour == 0]
    # ---- L3b
    p = B0 + "/storage/printDone.csv"
    hb = md5(p)
    assert hb.startswith(B0_MD5_PREFIX), hb
    R["meta"]["b0_md5"] = hb
    d = load_pd(p)
    R["tz_check"] = tz_check(d, v2, n2s)
    print("TZ best offset:", R["tz_check"]["best_offset_h"],
          {h: round(x["pick20_median_rel"] * 100, 3) for h, x in R["tz_check"]["by_offset"].items()})
    assert R["tz_check"]["best_offset_h"] == TZ_H
    f = build_features(d, v2, n2s)
    R["coverage"] = {"btc1h_nan": int(f.btc1h.isna().sum()), "qv_NA": int((f.qv_b == "NA").sum()),
                     "age_NA": int((f.age_b == "NA").sum()), "n_episodes": int(f.ep.nunique())}
    R["l3b"] = run_l3b(f)
    T = R["l3b"]
    print("L3b total", T["total"], "k_cells", T["k_cells"], "coverage", R["coverage"])
    for dim, tb in T["tables"].items():
        print("\n##", dim, tb["label"])
        for v, r in tb["rows"].items():
            s = "n=%5d sum=%9.0f (%6.1f%%) mean=%6.2f win=%5.1f SL=%5.1f" % (r["n"], r["sum_pnl"], r["pct_sum_pnl"],
                                                                         r["mean_roi"], r["win"], r["sl_rate"])
            if "ci_mean_roi" in r:
                s += " ci[%5.2f;%5.2f] %s | d_rest %+5.2f [%5.2f;%5.2f] %s | sumCI[%7.0f;%7.0f]" % (
                    *r["ci_mean_roi"], r["mean_sig"], r["d_vs_rest"], *r["ci_d_vs_rest"], r["rest_sig"], *r["ci_sum_pnl"])
            print("  %-14s %s" % (v, s))
    print("\n## top excess (k=%d infl=%.3f)" % (T["k_cells"], T["infl_k"]))
    for t in T["top_excess"]:
        print(" ", json.dumps(t))
    print("\n## exclusion candidates")
    for k, e in T["exclusion_candidates"].items():
        print(" ", k, json.dumps(e))
    # ---- L3a
    R["l3a"] = run_l3a(btc_daily)
    A = R["l3a"]
    print("\n## L3a point")
    for k, m in A["point"].items():
        print(" ", k, {x: (round(y, 4) if isinstance(y, float) else y) for x, y in m.items()})
    print("c_expo", A["c_expo"])
    for k, o in A["paired_daily"].items():
        print(" ", k, json.dumps(o))
    for k, o in A["paired_trades"].items():
        print(" ", k, json.dumps(o))
    for y, row in A["by_year"].items():
        print(" ", y, {k: (round(v["ret"], 2), round(v["maxdd"], 2), round(v["calmar"], 2)) for k, v in row.items()})
    json.dump(R, open(OUT, "w"), indent=1, default=str)
    print("WROTE", OUT)


if __name__ == "__main__":
    main()
