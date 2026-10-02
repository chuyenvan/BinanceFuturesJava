# AUDIT SHORT_V3_R3 (doi khang) — chi doc, khong sua repo. Out -> /home/ubuntu/claude_master/1002/audit_r3_*
import sys, os, json, time, logging
import numpy as np, pandas as pd
REPO = "/home/ubuntu/src/BinanceFuturesJava"
sys.path.insert(0, os.path.join(REPO, "research/analysis"))
import short_v2_p0a_statemap as P
import short_v3_r3_breakdown as R
OUTD = "/home/ubuntu/claude_master/1002"
R.OUT_JSON = OUTD + "/audit_r3_rerun.json"; R.OUT_MD = OUTD + "/audit_r3_rerun.md"
logging.basicConfig(level=logging.WARNING)
t00 = time.time()
A = {}
# ---------- 1. tai lap ----------
res, df = R.run(); res = R.tables(res, df)
json.dump(res, open(R.OUT_JSON, "w"), indent=1, ensure_ascii=False, default=float)
new = json.load(open(R.OUT_JSON))
old = json.load(open(os.path.join(REPO, "docs/result/RESULT_SHORT_V3_R3.json")))
diffs = []
def cmp(a, b, p=""):
    if isinstance(a, dict):
        for k in set(a) | set(b):
            if k not in a or k not in b: diffs.append((p + "/" + str(k), "missing")); continue
            cmp(a[k], b[k], p + "/" + str(k))
    elif isinstance(a, list):
        if len(a) != len(b): diffs.append((p, "len")); return
        for i, (x, y) in enumerate(zip(a, b)): cmp(x, y, p + "[%d]" % i)
    elif isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool):
        if not (abs(a - b) <= 1e-9 * max(1, abs(a)) or (a != a and b != b)): diffs.append((p, a, b))
    else:
        if a != b: diffs.append((p, a, b))
cmp(old, new)
A["repro_ndiff"] = len(diffs); A["repro_diffs_head"] = diffs[:20]
print("REPRO ndiff", len(diffs), diffs[:10], "%.0fs" % (time.time() - t00), flush=True)

# ---------- 2. BRK doc lap (numpy, khong rolling) ----------
C, names, t_start = P.load_hourly()
close, qv, lastc, nrec, coins = P.panels(C, names, t_start)
I = R.indicators(close, qv, coins)
cl = close[coins].to_numpy(float); q = qv[coins].to_numpy(float); q = np.where(q > 0, q, np.nan)
idx = close.index
i0 = idx.searchsorted(P.DEV0); i1 = idx.searchsorted(P.DEV1)
nd, nc = cl.shape
rawB = np.zeros((nd, nc), bool); rawN = np.zeros((nd, nc), bool); E = np.zeros((nd, nc), bool)
for i in range(i0, i1 + 1):
    prev = cl[i - 30:i]; qp = q[i - 30:i]
    okp = np.isfinite(prev).all(0)
    lo = np.where(okp, np.nanmin(np.where(np.isfinite(prev), prev, np.inf), 0), np.nan)
    cntq = np.isfinite(qp).sum(0)
    with np.errstate(all="ignore"):
        med = np.where(cntq >= 20, np.nanmedian(qp, 0), np.nan)
    e = np.isfinite(cl[i]) & np.isfinite(cl[i - 1]) & okp & np.isfinite(med) & np.isfinite(q[i])
    r1 = cl[i] / cl[i - 1] - 1
    core = e & (cl[i] <= lo) & (r1 <= -0.05)
    E[i] = e; rawN[i] = core; rawB[i] = core & (q[i] >= 2 * med)
def cool(raw):
    out = np.zeros_like(raw)
    for j in range(raw.shape[1]):
        last = -10**9
        for i in np.where(raw[:, j])[0]:
            if i - last >= 8: out[i, j] = True; last = i
    return out
eB = cool(rawB); eN = cool(rawN)
A["indep_vs_script"] = {k: int((a != I[k].to_numpy(bool)).sum()) for k, a in
                        dict(E=E, rawB=rawB, rawN=rawN, entB=eB, entN=eN).items()}
A["n"] = dict(E=int(E.sum()), rawB=int(rawB.sum()), entB=int(eB.sum()), rawN=int(rawN.sum()), entN=int(eN.sum()))
print("INDEP", A["indep_vs_script"], A["n"], flush=True)
# tinh huong bien: close_d == lo30 (dang thuc), r1 dung -5%
lo30 = I["lo30"].to_numpy(float)
A["brk_close_eq_lo30"] = int((eB & (cl == lo30)).sum())
# ---------- 3. chat luong quoteVol (nrec/nmin) tren BRK ----------
Q = P.load_qv()
nr = Q.groupby("date")["nrec"].max().reindex(idx)
nm = Q.pivot_table(index="date", columns="sym", values="nmin", aggfunc="sum").reindex(index=idx, columns=coins).to_numpy(float)
nrv = nr.to_numpy(float)
bi, bj = np.where(eB)
nr_d = nrv[bi]; nm_d = nm[bi, bj]
nr_prevmin = np.array([np.nanmin(nrv[i - 30:i]) for i in bi])
nr_prevmed = np.array([np.nanmedian(nrv[i - 30:i]) for i in bi])
A["qv_quality_BRK"] = dict(n=int(len(bi)), d_nrec_lt1440=int((nr_d < 1440).sum()), d_nrec_lt1380=int((nr_d < 1380).sum()),
                           coin_nmin_lt1380=int((nm_d < 1380).sum()), prev30_nrec_median_lt1380=int((nr_prevmed < 1380).sum()),
                           prev30_any_nrec_lt1000=int((nr_prevmin < 1000).sum()))
# lastc (Aerospike) vs close panel (CLOSES_1H) tren BRK
lc = lastc.reindex(index=idx, columns=coins).to_numpy(float)
rel = np.abs(lc[bi, bj] / cl[bi, bj] - 1)
A["close_vs_aerospike_lastc_BRK"] = dict(med=float(np.nanmedian(rel)), p99=float(np.nanpercentile(rel, 99)), gt1pct=int((rel > 0.01).sum()),
                                         nan=int(np.isnan(rel).sum()))
print("QV", A["qv_quality_BRK"], A["close_vs_aerospike_lastc_BRK"], flush=True)

# ---------- 4. outcome doc lap cho BRK (T=3,7) + bien the SL tai close gio cham ----------
cumF, hasF = P.funding_cum(names, t_start, C.shape[0])
n2c = {n: j for j, n in enumerate(names)}
rows = []
for i, j in zip(bi, bj):
    d = idx[i]; s = coins[j]; cj = n2c.get(s, -1)
    if cj < 0: continue
    t0 = int((d + pd.Timedelta(days=1)).value // 10**6); h0 = (t0 - t_start) // P.H
    p0 = float(C[h0, cj])
    for T in (3, 7):
        L = 24 * T
        if t0 + L * P.H > P.DEV_END_MS: continue
        w = C[h0 + 1:h0 + L + 1, cj].astype(float)
        fin = np.isfinite(w)
        if not fin.any() or not np.isfinite(p0): continue
        last = w[np.where(fin)[0][-1]]
        ret = last / p0 - 1
        k = np.where(fin & (w >= 1.1 * p0))[0]
        sl = len(k) > 0
        kx = k[0] + 1 if sl else L
        fund = cumF[h0 + kx, cj] - cumF[h0, cj]; ff = cumF[h0 + L, cj] - cumF[h0, cj]
        pnl = (-0.102 if sl else -ret) - P.FEE + fund
        pnl_slc = (-(w[k[0]] / p0 - 1) if sl else -ret) - P.FEE + fund       # SL khop tai close gio cham (gap)
        rows.append(dict(date=d, sym=s, T=T, ret=ret, sl=sl, pnl=pnl, pnl_slc=pnl_slc, pnl_nosl=-ret - P.FEE + ff,
                         slret=(w[k[0]] / p0 - 1) if sl else np.nan))
X = pd.DataFrame(rows)
m = df[df.B][["date", "sym", "T", "ret", "pnl", "pnl_nosl", "excess", "sq_all_day"]].merge(X, on=["date", "sym", "T"], suffixes=("_s", "_i"), how="outer", indicator=True)
A["outcome_merge"] = m["_merge"].value_counts().to_dict()
A["outcome_maxabs"] = {c: float(np.nanmax(np.abs(m[c + "_s"].astype(float) - m[c + "_i"].astype(float)))) for c in ("ret", "pnl", "pnl_nosl")}
print("OUTCOME", A["outcome_merge"], A["outcome_maxabs"], flush=True)

# ---------- 5. excess_short doc lap + bien the ----------
EX = {}
for T in (3, 7):
    x = df[df["T"] == T]
    g = x.groupby("date")
    mu = g["ret"].mean(); med = g["ret"].median(); s_ = g["ret"].sum(); c_ = g["ret"].count()
    b = x[x.B]
    allm = b.date.map(mu).to_numpy(); allmed = b.date.map(med).to_numpy()
    # leave-out: ALL cung ngay KHONG gom chinh cac BRK cua ngay do
    bs = b.groupby("date")["ret"].agg(["sum", "count"])
    lo_mu = ((s_.reindex(bs.index) - bs["sum"]) / (c_.reindex(bs.index) - bs["count"]))
    allm_lo = b.date.map(lo_mu).to_numpy()
    r = b.ret.to_numpy(float)
    EX[T] = dict(bleed_BRK=float(r.mean()), ALL_matched_bleed=float(allm.mean()),
                 excess_short_indep=float((allm - r).mean()), excess_short_script=float(-b.excess.mean()),
                 excess_short_leaveout=float((allm_lo - r).mean()), excess_short_vs_median=float((allmed - r).mean()),
                 excess_short_dayweighted=float(pd.Series(allm - r).groupby(b.date.to_numpy()).mean().mean()),
                 excess_short_ci_raw=res["A"]["BRK|%d" % T].get("ci_raw_excess_short"))
A["excess"] = EX
print("EXCESS", EX, flush=True)

# ---------- 6. inflate: cac quy uoc ----------
import math

fac = {"P0A_zk_div_1.96_k2(=0.60)": math.sqrt(2 * math.log(2)) / 1.959964, "raw(1.0)": 1.0,
       "Bonferroni_k2(z.9875/1.96=1.143)": 2.241403 / 1.959964, "R3_x1.18": 1.18,
       "P0A_k13(1.156)": math.sqrt(2 * math.log(13)) / 1.959964, "R1_style_x1.89": math.sqrt(2 * math.log(6))}
INF = {}
for T in (3, 7):
    a = res["A"]["BRK|%d" % T]; mu = a["netproxy"]; lo, hi = a["ci_raw"]
    INF[T] = {k: [mu - (mu - lo) * f, mu + (hi - mu) * f] for k, f in fac.items()}
    INF[T]["G1_netproxy_gt_0p5"] = mu > 0.005
A["inflate"] = INF

# ---------- 7. SL sensitivity + cum ngay ----------
SLS = {}
for T in (3, 7):
    b = X[X["T"] == T]
    lo, hi, _, _ = P.ci_block(b.pnl_slc.to_numpy(float), b.date)
    SLS[T] = dict(n=len(b), netproxy=float(b.pnl.mean()), netproxy_SLatClose=float(b.pnl_slc.mean()), ci_SLatClose=[lo, hi],
                  netproxy_noSL=float(b.pnl_nosl.mean()), mean_slret=float(b.slret.mean()), p95_slret=float(np.nanpercentile(b.slret, 95)),
                  max_slret=float(np.nanmax(b.slret)), max_ret=float(b.ret.max()))
    dd = b.groupby("date").agg(n=("pnl", "size"), pnl=("pnl", "mean"), ret=("ret", "mean")).sort_values("n", ascending=False)
    SLS[T]["n_days"] = int(len(dd)); SLS[T]["top5_days"] = [(str(i.date()), int(r.n), round(float(r.pnl), 4), round(float(r.ret), 4)) for i, r in dd.head(5).iterrows()]
    SLS[T]["share_top1"] = float(dd.n.iloc[0] / dd.n.sum()); SLS[T]["share_top10"] = float(dd.n.head(10).sum() / dd.n.sum())
    top1 = dd.index[0]
    SLS[T]["netproxy_excl_top1day"] = float(b[b.date != top1].pnl.mean())
    SLS[T]["netproxy_excl_top10days"] = float(b[~b.date.isin(dd.index[:10])].pnl.mean())
    SLS[T]["netproxy_dayweighted"] = float(dd.pnl.mean())
    SLS[T]["netproxy_noSL_dayweighted"] = float(b.groupby("date").pnl_nosl.mean().mean())
    # bootstrap theo NGAY (cluster ngay) cho tham khao
    dsum = b.groupby("date").pnl.sum().to_numpy(); dcnt = b.groupby("date").pnl.size().to_numpy().astype(float)
    rng = np.random.default_rng(20260905); ix = rng.integers(0, len(dsum), (2000, len(dsum)))
    bsd = dsum[ix].sum(1) / dcnt[ix].sum(1)
    SLS[T]["ci_dayclustered"] = [float(np.percentile(bsd, 2.5)), float(np.percentile(bsd, 97.5))]
    # nam theo SL-at-close
    SLS[T]["years_pos_SLatClose"] = int(sum(b[b.date.dt.year == y].pnl_slc.mean() > 0 for y in (2022, 2023, 2024, 2025)))
A["SL_and_cluster"] = SLS
print("SL", json.dumps(SLS, default=str)[:3000], flush=True)

# ---------- 8. bull/notbull: tai lap + vai tro ----------
A["C_slices_bull"] = {k: dict(n=v.get("n"), netproxy=v.get("netproxy"), ci_raw=v.get("ci_raw")) for k, v in res["C_slices"].items() if "bull" in k}
b7 = df[df.B & (df["T"] == 7)]
A["bull_nan_BRK7"] = int(b7.bull.isna().sum())
A["bull_days_BRK7"] = int(b7[b7.bull == 1.0].date.nunique())
# ALL cung ngay trong lat bull: BRK co tach khoi ALL khong?
x7 = df[df["T"] == 7]; mu7 = x7.groupby("date").ret.mean()
bb = b7[b7.bull == 1.0]
A["bull_slice_ALLmatched_bleed"] = float(bb.date.map(mu7).mean()); A["bull_slice_BRK_bleed"] = float(bb.ret.mean())
A["elapsed_s"] = time.time() - t00
json.dump(A, open(OUTD + "/audit_r3_extra.json", "w"), indent=1, default=str)
print("DONE %.0fs" % A["elapsed_s"])
