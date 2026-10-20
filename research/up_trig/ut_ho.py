#!/usr/bin/env python3
"""UP_TRIG HOLDOUT 2026 - dung PREREG_UP_TRIG.md ADDENDUM 1 (commit 0205d8f3). Chay 1 lan, khong tune.
Luat dong bang: RISE24, H=24h, x_r>=0.99, chi 'em', bo trung 24h, vao close nen t+1', ra close nen t+1'+24h, phi 0.10%.
Logic gio / x_r / post / stats y het ut_a.py (tang A). Gio UTC."""
import glob, json, logging, os, sys, time, zipfile
import numpy as np, pandas as pd, pyarrow.parquet as pq

OUTD = "/home/ubuntu/claude_master/up_trig"
KL = OUTD + "/kl"
os.makedirs(KL, exist_ok=True)
TEST = "--test" in sys.argv
TAG = "ut_ho_test" if TEST else "ut_ho"
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s",
                    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler(os.path.join(OUTD, TAG + ".log"), mode="w")])
log = logging.getLogger("ho")
MS = lambda s: int(pd.Timestamp(s).value // 10**6)  # noqa: E731
MIN, G15 = 60000, 900000
TM0 = MS("2025-09-01")              # dau chuoi phut market (>= 90 ngay truoc 2026-01-01)
T0 = MS("2025-12-01")               # dau luoi 15' gia (can 24h volume truoc 2026-01-01; RISE24 khong can, giu cho dong bo)
TEND = MS("2026-10-01")
S_START = MS("2026-01-01")
OV_A, OV_B = MS("2026-07-01"), MS("2026-08-13")   # cua so chong lan 2026-07-01..08-12
HM = 1440
FEE = 0.001
Q = 0.99
K = 24
MS_DOWN_BIG_AVG = np.float32(-0.03157)
DIED = {"BTCDOMUSDT", "USDCUSDT"}
EXCL = {"BTCUSDT", "ETHUSDT"} | DIED
NM = (TEND - TM0) // MIN
NG = (TEND - T0) // G15
SMAX = 1200
t_run = time.time()

# ---------------- market.bin ----------------
MB = "/home/ubuntu/marketdump/market.bin"
raw = np.fromfile(MB, dtype=np.uint8)
nrec = int(np.frombuffer(raw[:4].tobytes(), dtype=">i4")[0])
assert len(raw) == 4 + nrec * 20
rec = np.frombuffer(raw[4:].tobytes(), dtype=np.dtype([("ts", ">i8"), ("d", ">f4"), ("u", ">f4"), ("d15", ">f4")]))
mts = rec["ts"].astype(np.int64)
assert (np.diff(mts) > 0).all() and (mts % MIN == 0).all()
k_ = (mts >= TM0) & (mts < TEND)
mts, md, mu = mts[k_], rec["d"][k_].astype(np.float32), rec["u"][k_].astype(np.float32)
MB_LAST = int(mts.max())
del raw, rec
U_mb = np.full(NM, np.nan, np.float32); D_mb = np.full(NM, np.nan, np.float32)
U_mb[(mts - TM0) // MIN] = mu; D_mb[(mts - TM0) // MIN] = md
m26 = mts >= S_START
MBINFO = dict(file=MB, last_ts=str(pd.to_datetime(MB_LAST, unit="ms")), n_2026=int(m26.sum()),
              n_missing_2026_to_last=int((MB_LAST - S_START) // MIN + 1 - m26.sum()),
              n_missing_lookback_2025_09_12=int((S_START - TM0) // MIN - (~m26).sum()))
log.info("market.bin: %s", MBINFO)

# ---------------- kline: local 2025-12 + Kaggle 2026-01..09 ----------------
from kaggle.api.kaggle_api_extended import KaggleApi  # noqa: E402
A = KaggleApi(); A.authenticate()


def kpath(ym):
    if ym < "2026":
        return f"/home/ubuntu/vz_e1/raw/kline1m-{ym}.parquet", False
    p = f"{KL}/kline1m-{ym}.parquet"
    if not os.path.exists(p):
        A.dataset_download_file("chuyendinh/vz-kline1m-2026", f"kline1m-{ym}.parquet", path=KL, quiet=True)
        for z in glob.glob(KL + "/*.zip"):
            with zipfile.ZipFile(z) as f:
                f.extractall(KL)
            os.remove(z)
    return p, True


def market_from_minutes(tsv, si, o, c, nsym, btc_i, died_mask):
    """Tinh lai rateDownAvg/rateUpAvg moi phut, dung cong thuc da kiem V1 (ut_v1.py): nen open-time t, moi dong (ca inactive),
    bo diedSymbol, bo r<-0.15 khi BTC>-0.004, bo r>0.3, TreeMap gop khoa trung, top100 cap size*4/5, tong float32."""
    tmin = int(tsv.min()); n = int((tsv.max() - tmin) // MIN) + 1
    mi = (tsv - tmin) // MIN
    R = np.full((n, nsym), np.nan, np.float32)
    r = (( c.astype(np.float32).astype(np.float64) - o.astype(np.float32).astype(np.float64)) / o.astype(np.float32).astype(np.float64)).astype(np.float32)
    R[mi, si] = r
    present = np.zeros(n, bool); present[mi] = True
    rb = R[:, btc_i].copy() if btc_i is not None else np.zeros(n, np.float32)
    rb = np.where(np.isnan(rb), np.float32(0), rb)
    R[:, died_mask] = np.nan
    R[(rb[:, None] > -0.004) & (R < -0.15)] = np.nan
    R[R > 0.3] = np.nan

    def avg(X):  # X: moi hang, gia tri (key) -> trung binh 'period' key nho nhat theo thu tu TreeMap
        S = np.sort(X, axis=1)
        dup = np.zeros_like(S, bool); dup[:, 1:] = S[:, 1:] == S[:, :-1]
        S[dup] = np.nan
        S = np.sort(S, axis=1)
        nu = (~np.isnan(S)).sum(1)
        per = np.minimum(100, nu * 4 // 5)
        cs = np.cumsum(np.nan_to_num(S, nan=0.0).astype(np.float32), axis=1, dtype=np.float32)
        cnt = np.maximum(per, 1)  # Java: per=0 -> vong lap van cong 1 phan tu roi break (counter>=0) -> chia 1
        val = cs[np.arange(len(S)), np.minimum(cnt, S.shape[1]) - 1] / cnt.astype(np.float32)
        val[nu == 0] = 0.0
        return val
    down = avg(R)
    up = -avg(-R)
    t_out = tmin + np.arange(n, dtype=np.int64) * MIN
    return t_out[present], down[present].astype(np.float32), up[present].astype(np.float32)


months = ["2025-12"] + [f"2026-{m:02d}" for m in range(1, 10)]
if TEST:
    months = ["2025-12", "2026-07"]
O0 = np.full((NG, SMAX), np.nan, np.float32); C0 = np.full((NG, SMAX), np.nan, np.float32)
C1 = np.full((NG, SMAX), np.nan, np.float32)
U_rc = np.full(NM, np.nan, np.float32); D_rc = np.full(NM, np.nan, np.float32)
sym2i = {}
KINFO = dict(months={}, rows=0, rows_inactive=0)
V3RAW = []
rng = np.random.default_rng(20261020)
for ym in months:
    t1 = time.time()
    p, dl = kpath(ym)
    pf = pq.ParquetFile(p)
    cols = pf.schema_arrow.names
    want = ["ts", "sym", "open", "close", "quote_volume", "active"] + (["n_trades"] if "active" not in cols and "n_trades" in cols else [])
    df = pq.read_table(p, columns=[c for c in want if c in cols]).to_pandas()
    if "active" not in df.columns:   # fallback (ghi ro trong KINFO): active = co giao dich
        df["active"] = (df["n_trades"] > 0) if "n_trades" in df.columns else (df["quote_volume"] > 0)
    if df["sym"].dtype.name != "category":
        df["sym"] = df["sym"].astype("category")
    df = df[(df["ts"] >= T0) & (df["ts"] < TEND)]
    cats = df["sym"].cat.categories.astype(str)
    for s in cats:
        if s not in sym2i:
            sym2i[s] = len(sym2i)
    assert len(sym2i) <= SMAX
    gmap = np.array([sym2i[s] for s in cats], np.int64)
    si = gmap[df["sym"].cat.codes.to_numpy()]
    tsv = df["ts"].to_numpy(np.int64)
    assert (tsv % MIN == 0).all()
    act = df["active"].to_numpy(bool)
    op, cl = df["open"].to_numpy(np.float64), df["close"].to_numpy(np.float64)
    g = (tsv - T0) // G15; off = ((tsv - T0) % G15) // MIN
    s0 = (off == 0) & act; O0[g[s0], si[s0]] = op[s0]; C0[g[s0], si[s0]] = cl[s0]
    s1 = (off == 1) & act; C1[g[s1], si[s1]] = cl[s1]
    for j in rng.choice(np.where(s1)[0], 5, replace=False):
        V3RAW.append(dict(ts=int(tsv[j]), sym=str(cats[df["sym"].cat.codes.iloc[j]]), close=float(cl[j]), g=int(g[j]), s=int(si[j])))
    if ym >= "2026":
        nsy = len(sym2i)
        died_mask = np.array([s in DIED for s in sorted(sym2i, key=sym2i.get)])
        tt, dd, uu = market_from_minutes(tsv, si, op, cl, nsy, sym2i.get("BTCUSDT"), died_mask)
        U_rc[(tt - TM0) // MIN] = uu; D_rc[(tt - TM0) // MIN] = dd
    KINFO["months"][ym] = dict(file=p, downloaded=dl, cols=cols, rows=int(len(df)), inactive=int((~act).sum()),
                               ts_min=str(pd.to_datetime(tsv.min(), unit="ms")), ts_max=str(pd.to_datetime(tsv.max(), unit="ms")),
                               nsym=int(len(cats)), size=os.path.getsize(p))
    KINFO["rows"] += int(len(df)); KINFO["rows_inactive"] += int((~act).sum())
    log.info("kline %s %s (%.0fs)", ym, KINFO["months"][ym], time.time() - t1)
    del df, tsv, act, op, cl, g, off, si
    if dl and not (TEST or ym == "2026-07"):
        os.remove(p)
if not TEST and os.path.exists(f"{KL}/kline1m-2026-07.parquet"):
    os.remove(f"{KL}/kline1m-2026-07.parquet")
NSY = len(sym2i)
i2sym = np.array(sorted(sym2i, key=sym2i.get))
O0, C0, C1 = O0[:, :NSY], C0[:, :NSY], C1[:, :NSY]
V3 = dict(n=len(V3RAW), ok=bool(all(abs(float(C1[r["g"], r["s"]]) - r["close"]) <= 1e-6 * abs(r["close"]) for r in V3RAW)))
log.info("V3 (close nen ts g+1' trong luoi = parquet goc, %d dong ngau nhien): %s", V3["n"], V3["ok"])

# ---------------- chong lan market.bin vs tinh lai (2026-07-01..08-12) ----------------
def ovl(a, b):
    i0, i1 = (a - TM0) // MIN, (b - TM0) // MIN
    m = ~np.isnan(U_mb[i0:i1]) & ~np.isnan(U_rc[i0:i1])
    eu = np.abs(U_mb[i0:i1][m] - U_rc[i0:i1][m]); ed = np.abs(D_mb[i0:i1][m] - D_rc[i0:i1][m])
    return dict(n_min=int(m.sum()), n_mb_only=int((~np.isnan(U_mb[i0:i1]) & np.isnan(U_rc[i0:i1])).sum()),
                n_rc_only=int((np.isnan(U_mb[i0:i1]) & ~np.isnan(U_rc[i0:i1])).sum()),
                up_abs_med=float(np.median(eu)), up_abs_p99=float(np.quantile(eu, 0.99)), up_abs_max=float(eu.max()),
                up_corr=float(np.corrcoef(U_mb[i0:i1][m], U_rc[i0:i1][m])[0, 1]),
                up_exact_frac=float((eu == 0).mean()),
                down_abs_med=float(np.median(ed)), down_abs_p99=float(np.quantile(ed, 0.99)), down_abs_max=float(ed.max()),
                down_corr=float(np.corrcoef(D_mb[i0:i1][m], D_rc[i0:i1][m])[0, 1]),
                bigdown_mb=int((D_mb[i0:i1][m] < MS_DOWN_BIG_AVG).sum()), bigdown_rc=int((D_rc[i0:i1][m] < MS_DOWN_BIG_AVG).sum()))


OVL = dict(official_2026_07_01__08_12=ovl(OV_A, OV_B), extra_2026_01_01__08_12=ovl(S_START, OV_B))
log.info("chong lan: %s", OVL)

# chuoi cuoi: market.bin toi phut cuoi cua no, sau do tinh lai
i_last = (MB_LAST - TM0) // MIN
U = U_mb.copy(); Dn = D_mb.copy()
U[i_last + 1:] = U_rc[i_last + 1:]; Dn[i_last + 1:] = D_rc[i_last + 1:]
SER = dict(rc_from=str(pd.to_datetime(MB_LAST + MIN, unit="ms")), n_rc_used=int((~np.isnan(U_rc[i_last + 1:])).sum()),
           n_missing_after=int(np.isnan(U[i_last + 1:]).sum()))
log.info("chuoi ghep: %s", SER)


# ---------------- x_r (y het ut_a: ECDF #{w<=x}/n tren [t-90d, t), warm-up 14d) ----------------
def xr_of(Useries, samp_ts):
    p_idx = (samp_ts - TM0) // MIN
    x = Useries[p_idx]
    ndays = NM // 1440
    Uday = Useries[:ndays * 1440].reshape(ndays, 1440)
    cnt_le = np.zeros(len(p_idx), np.int64); cnt_n = np.zeros(len(p_idx), np.int64)
    kday = p_idx // 1440; mod = p_idx % 1440
    sd_ = [np.sort(r[~np.isnan(r)]) for r in Uday]
    for j in range(ndays):
        lo = np.searchsorted(kday, j + 1, "left"); hi = np.searchsorted(kday, j + 89, "right")
        if hi > lo:
            cnt_le[lo:hi] += np.searchsorted(sd_[j], x[lo:hi], side="right"); cnt_n[lo:hi] += len(sd_[j])
    mins = np.arange(1440)
    for k in np.unique(kday):
        sl = np.where(kday == k)[0]
        xs = x[sl][:, None]; ms_ = mod[sl][:, None]
        vk = Uday[k][None, :]; ok = (mins[None, :] < ms_) & ~np.isnan(vk)
        cnt_le[sl] += (ok & (vk <= xs)).sum(1); cnt_n[sl] += ok.sum(1)
        v0 = Uday[k - 90][None, :]; ok0 = (mins[None, :] >= ms_) & ~np.isnan(v0)
        cnt_le[sl] += (ok0 & (v0 <= xs)).sum(1); cnt_n[sl] += ok0.sum(1)
    xr = np.where((cnt_n >= 14 * 1440) & ~np.isnan(x), cnt_le / np.maximum(cnt_n, 1), np.nan)
    return x, xr, cnt_n


samp_ts = np.arange(S_START, TEND, G15, dtype=np.int64)
samp_ts = samp_ts[samp_ts + MIN + HM * MIN < TEND]          # bo mau co t+1'+24h > 2026-09-30 23:59
p_idx = (samp_ts - TM0) // MIN; g_idx = (samp_ts - T0) // G15
x, xr, cnt_n = xr_of(U, samp_ts)
# V2 brute force
chk = rng.choice(np.where(~np.isnan(xr))[0], 300, replace=False); bad = 0
for i in chk:
    p = p_idx[i]; w = U[p - 90 * 1440:p]; w = w[~np.isnan(w)]
    bad += int(abs((w <= x[i]).sum() / len(w) - xr[i]) > 1e-12)
V2 = dict(n_check=300, n_mismatch=bad, n_nan_xr=int(np.isnan(xr).sum()), window_n_min=int(cnt_n.min()), ok=bad == 0)
log.info("V2: %s", V2)
# doi trang thai x_r>=0.99 khi thay nguon trong cua so chong lan
U_alt = U.copy(); i0, i1 = (OV_A - TM0) // MIN, (OV_B - TM0) // MIN
U_alt[i0:i1] = np.where(np.isnan(U_rc[i0:i1]), U[i0:i1], U_rc[i0:i1])
ms_ov = (samp_ts >= OV_A) & (samp_ts < OV_B)
_, xr_alt, _ = xr_of(U_alt, samp_ts[ms_ov])
f_mb = xr[ms_ov] >= Q; f_rc = xr_alt >= Q
OVL["flag_switch_xr_ge_0.99"] = dict(n_samples=int(ms_ov.sum()), n_flag_mb=int(f_mb.sum()), n_flag_rc=int(f_rc.sum()),
                                      n_switch=int((f_mb != f_rc).sum()), frac_switch=float((f_mb != f_rc).mean()),
                                      xr_abs_diff_med=float(np.nanmedian(np.abs(xr[ms_ov] - xr_alt))),
                                      xr_abs_diff_max=float(np.nanmax(np.abs(xr[ms_ov] - xr_alt))))
log.info("doi trang thai x_r>=0.99 khi thay nguon (cua so chong lan): %s", OVL["flag_switch_xr_ge_0.99"])

# ---------------- sau sap ----------------
bdm = (~np.isnan(Dn)) & (Dn < MS_DOWN_BIG_AVG)
cs_bd = np.concatenate([[0], np.cumsum(bdm)])
PD = pd.read_csv("/home/ubuntu/kaggle_sim/out/ho4-k24-b-s42/storage/printDone.csv", index_col=False)
PD.columns = [c.strip() for c in PD.columns]
PD["level"] = PD["level"].astype(str).str.strip()
PD["t_start"] = pd.to_datetime(PD["start"].astype(str).str.strip(), format="%Y%m%d %H:%M") - pd.Timedelta(hours=7)
CB = PD[PD["level"] == "BIG_DOWN"].copy()
cbm = np.zeros(NM, bool)
ci = ((CB["t_start"].astype("int64") // 10**6 - TM0) // MIN).to_numpy(); ci = ci[(ci >= 0) & (ci < NM)]; cbm[ci] = True
cs_cb = np.concatenate([[0], np.cumsum(cbm)])
a_ = np.maximum(p_idx - 1440, 0); b_ = p_idx + 1
post_bd = (cs_bd[b_] - cs_bd[a_]) > 0; post_cb = (cs_cb[b_] - cs_cb[a_]) > 0; post = post_bd | post_cb
CB26 = CB[CB["t_start"] >= pd.Timestamp("2025-12-31")]
POST = dict(printDone="ho4-k24-b-s42", n_cb_legs_total=int(len(CB)), n_cb_legs_ge_2025_12_31=int(len(CB26)),
            cb_start_range=[str(CB["t_start"].min()), str(CB["t_start"].max())], pd_start_max=str(PD["t_start"].max()),
            n_bigdown_minutes_2026=int(bdm[(S_START - TM0) // MIN:].sum()),
            frac_post=float(post.mean()), frac_post_bd=float(post_bd.mean()), frac_post_cb=float(post_cb.mean()),
            frac_cb_only=float((post_cb & ~post_bd).mean()), frac_bd_only=float((post_bd & ~post_cb).mean()))
log.info("sau sap: %s", POST)
if TEST:   # chay thu: chi kiem code + chong lan, KHONG tinh return holdout (tranh nhin ket qua truoc khi chay that)
    json.dump(dict(test=True, market_bin=MBINFO, overlap=OVL, series=SER, V2=V2, V3=V3, post=POST, kline=KINFO),
              open(os.path.join(OUTD, TAG + ".json"), "w"), indent=1, default=str)
    log.info("TEST xong (%.0fs)", time.time() - t_run)
    sys.exit(0)

# ---------------- gio RISE24 + BTC, H=24h (y het ut_a) ----------------
excl_cols = np.array([s in EXCL for s in i2sym]); btc_col = sym2i["BTCUSDT"]
NS = len(samp_ts)
gR = np.full(NS, np.nan); gB = np.full(NS, np.nan); nsel = np.zeros(NS, np.int16); nval = np.zeros(NS, np.int16)
SELSYM = [None] * NS
for c in range(0, NS, 4000):
    gs = g_idx[c:c + 4000]
    o0, c0_, c1 = O0[gs], C0[gs], C1[gs]
    have = ~np.isnan(c0_) & ~np.isnan(o0); have[:, excl_cols] = False
    r1 = c0_ / o0 - 1.0
    rr = np.where(have & (r1 <= 0.3), r1, -np.inf)
    sel = np.argpartition(-rr, K, axis=1)[:, :K]
    ok = np.take_along_axis(rr, sel, 1) > -np.inf
    ret = C1[gs + HM // 15] / c1 - 1.0
    rt = np.take_along_axis(ret, sel, 1); vv = ok & ~np.isnan(rt)
    n_ok, n_v = ok.sum(1), vv.sum(1)
    gR[c:c + 4000] = np.where(n_v > 0, np.where(vv, rt, 0).sum(1) / np.maximum(n_v, 1), np.nan)
    nsel[c:c + 4000] = n_ok; nval[c:c + 4000] = n_v
    gB[c:c + 4000] = ret[:, btc_col]
    for i in range(len(gs)):
        SELSYM[c + i] = ",".join(i2sym[sel[i][vv[i]]])
E = pd.DataFrame(dict(ts=samp_ts, x=x.astype(np.float64), xr=xr, post=post, post_bd=post_bd, post_cb=post_cb,
                      g_RISE24=gR, g_BTC=gB, nsel=nsel, nval=nval, coins=SELSYM))
E["t"] = pd.to_datetime(E["ts"], unit="ms"); E["day"] = E["t"].dt.floor("D"); E["month"] = E["t"].dt.strftime("%Y-%m")
MISS = dict(frac_coin_missing=float(1 - nval.sum() / max(nsel.sum(), 1)), n_sample_nan=int(np.isnan(gR).sum()),
            n_btc_nan=int(np.isnan(gB).sum()), frac_lt24=float((nsel < K).mean()))
log.info("thieu coin: %s", MISS)


def stats(r, day):
    m = ~np.isnan(r); r, day = r[m], np.asarray(day)[m]
    n = len(r)
    if n == 0:
        return dict(n=0)
    mu = float(r.mean()); e = r - mu
    sg = pd.Series(e).groupby(day).sum().to_numpy(); G = len(sg)
    tt = tg = np.nan
    if G > 1 and n > 1:
        V = G / (G - 1) * float((sg ** 2).sum()) / n ** 2
        if V > 0:
            tt, tg = (mu - FEE) / np.sqrt(V), mu / np.sqrt(V)
    net = r - FEE
    return dict(n=n, n_day=G, gross=mu, net=mu - FEE, median_net=float(np.median(net)), win_net=float((net > 0).mean()),
                t_cl=float(tt), t_cl_gross=float(tg))


def dedup(m):
    ev = E.loc[m].sort_values("ts")
    keep, last = [], -10**18
    for tsv in ev["ts"].to_numpy():
        if tsv - last >= HM * MIN:
            keep.append(True); last = tsv
        else:
            keep.append(False)
    return ev[np.array(keep, bool)].copy()


# ---------------- luat dong bang ----------------
EV = dedup((E["xr"] >= Q) & (~E["post"]) & E["g_RISE24"].notna())
EV["net"] = EV["g_RISE24"] - FEE
EV["ex_btc_gross"] = EV["g_RISE24"] - EV["g_BTC"]
S = stats(EV["g_RISE24"].to_numpy(), EV["day"])
exb = EV["ex_btc_gross"].dropna()
sx = stats(exb.to_numpy() + FEE, EV.loc[exb.index, "day"])  # t cua excess (gross) = t_cl cua (excess+FEE)-FEE
EXB = dict(n=int(len(exb)), mean=float(exb.mean()), median=float(exb.median()), t_cl=sx.get("t_cl"),
           btc_gross_mean=float(EV["g_BTC"].mean()))
c_n, c_net, c_t, c_ex = S["n"] >= 20, S["n"] > 0 and S["net"] > 0, S["n"] > 0 and S["t_cl"] >= 1.65, EXB["n"] > 0 and EXB["mean"] > 0
if S["n"] > 0 and S["net"] <= 0:
    verdict = "REJECT (net TB <= 0) -> DONG UP_TRIG"
elif c_n and c_net and c_t and c_ex:
    verdict = "CONFIRM -> viet prereg tang B"
else:
    verdict = "INCONCLUSIVE -> DONG UP_TRIG"
RULE = dict(rule="RISE24|24h|0.99|em|dedup24h", stats=S, excess_vs_btc=EXB, c_n_ge20=bool(c_n), c_net_pos=bool(c_net),
            c_t_ge1_65=bool(c_t), c_excess_pos=bool(c_ex), verdict=verdict)
log.info("KET LUAN: %s", RULE)

# ---------------- mo ta ----------------
srt = np.sort(EV["net"].to_numpy())
DESC = dict(
    by_month={m: dict(n=int(len(g)), net=float(g["net"].mean()), ex_btc=float(g["ex_btc_gross"].mean())) for m, g in EV.groupby("month")},
    ex_top5=float(srt[:-5].mean()) if len(srt) > 5 else None, top5=[float(v) for v in srt[-5:]], bottom5=[float(v) for v in srt[:5]],
    trim1=float(srt[max(1, round(0.01 * len(srt))):-max(1, round(0.01 * len(srt)))].mean()) if len(srt) > 10 else None,
    xr_quantiles={str(q): float(np.nanquantile(E["xr"], q)) for q in (0.1, 0.5, 0.9, 0.99)},
    frac_xr_ge_0_99=float((E["xr"] >= Q).mean()), frac_xr_ge_0_99_em=float(((E["xr"] >= Q) & ~E["post"]).mean()),
    n_samples=int(len(E)), n_samples_ge_q=int((E["xr"] >= Q).sum()), n_samples_ge_q_em=int(((E["xr"] >= Q) & ~E["post"]).sum()),
    n_samples_ge_q_post=int(((E["xr"] >= Q) & E["post"]).sum()), samples_ge_q_by_month=E[E["xr"] >= Q].groupby("month").size().to_dict())
m_post = (E["xr"] >= Q) & E["post"]
DESC["post_ge_0_99_samples"] = stats(E.loc[m_post, "g_RISE24"].to_numpy(), E.loc[m_post, "day"])
EVP = dedup(m_post & E["g_RISE24"].notna())
DESC["post_ge_0_99_dedup24h"] = stats(EVP["g_RISE24"].to_numpy(), EVP["day"])
DESC["post_ge_0_99_dedup24h_ex_btc"] = float((EVP["g_RISE24"] - EVP["g_BTC"]).mean()) if len(EVP) else None
m_em = (E["xr"] >= Q) & ~E["post"]
DESC["em_ge_0_99_samples_nodedup"] = stats(E.loc[m_em, "g_RISE24"].to_numpy(), E.loc[m_em, "day"])
DESC["base_all_samples_RISE24"] = stats(E["g_RISE24"].to_numpy(), E["day"])
DESC["base_all_samples_BTC_gross_mean"] = float(np.nanmean(E["g_BTC"]))
log.info("mo ta: %s", json.dumps(DESC, default=float))
log.info("su kien:\n%s", EV[["t", "x", "xr", "g_RISE24", "g_BTC", "net", "nval"]].to_string())

OUT = dict(prereg="PREREG_UP_TRIG.md ADDENDUM 1 @0205d8f3", run_s=time.time() - t_run, market_bin=MBINFO, series=SER, overlap=OVL,
           kline=KINFO, V2=V2, V3=V3, post=POST, missing=MISS, rule=RULE, desc=DESC,
           conventions=dict(time="UTC", key="nen open-time t; vao close nen t+1', ra close nen t+1'+24h", fee=FEE,
                            sample="moi 15' tu 2026-01-01, bo mau co nen ra > 2026-09-30 23:59",
                            rc_formula="ut_v1.py (moi dong ke ca inactive, bo died, loc BTC/-0.15, bo >0.3, TreeMap unique, top100 cap 4/5, float32)",
                            t_cl="cum theo ngay UTC, CR1", excess="RISE24 gross - BTC gross cung su kien"))
json.dump(OUT, open(os.path.join(OUTD, TAG + ".json"), "w"), indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
EV.drop(columns=["day"]).to_parquet(os.path.join(OUTD, TAG + "_events.parquet"))
E.drop(columns=["t", "day"]).to_parquet(os.path.join(OUTD, TAG + "_samples.parquet"))
log.info("ghi xong (%.0fs)", time.time() - t_run)
