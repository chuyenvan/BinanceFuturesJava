#!/usr/bin/env python3
"""UP_TRIG tang A (offline) - dung PREREG_UP_TRIG.md (commit 81f4fbf3). Chay 1 lan, khong tune.
Quy uoc (xac dinh boi V1 probe ut_v1.py): market.bin[t] = tinh tu nen 1m OPEN-TIME t (dong luc t+1').
=> rateUpAvg(t) biet duoc luc t+1'. Vao = close nen ts=t+1' (biet luc t+2'), ra = close nen ts=t+1'+H.
Thoi gian: UTC (kline ts, market.bin ts la epoch ms). printDone start/end la gio +07 -> tru 7h.
Dung: python3 ut_a.py [--test]"""
import json, logging, os, sys, time
import numpy as np, pandas as pd, pyarrow.parquet as pq

TEST = "--test" in sys.argv
OUTD = "/home/ubuntu/claude_master/up_trig"
TAG = "ut_a_test" if TEST else "ut_a"
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s",
                    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler(os.path.join(OUTD, TAG + ".log"), mode="w")])
log = logging.getLogger("ut")
MS = lambda s: int(pd.Timestamp(s).value // 10**6)  # noqa: E731
MIN, G15 = 60000, 900000
T0, TEND = MS("2021-07-01"), MS("2026-01-01")
S_START, S_END = MS("2021-08-01"), TEND
D_END = MS("2024-01-01")
if TEST:
    S_START, S_END = MS("2023-04-01"), MS("2023-05-01")
HS = {"1h": 60, "4h": 240, "24h": 1440}
FEE = 0.001
MS_DOWN_BIG_AVG = np.float32(-0.03157)   # Configs.java:478 default; profile r4_kg0_k16_f015_g155 & gqsf-a1 prof_run KHONG override
DIED = {"BTCDOMUSDT", "USDCUSDT"}         # DIED_SYMBOLS=BTCDOM,USDC (gqsf-a1 config.properties)
EXCL = {"BTCUSDT", "ETHUSDT"} | DIED
K = 24
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
keep = mts < TEND
mts, md, mu = mts[keep], rec["d"][keep].astype(np.float32), rec["u"][keep].astype(np.float32)
del raw, rec
TM0 = MS("2021-01-01")
NM = (TEND - TM0) // MIN
assert mts.min() >= TM0
mi = (mts - TM0) // MIN
U = np.full(NM, np.nan, np.float32); U[mi] = mu
Dn = np.full(NM, np.nan, np.float32); Dn[mi] = md
MBINFO = dict(file=MB, n_rec_total=nrec, n_used_lt2026=int(len(mts)), ts_min=str(pd.to_datetime(mts.min(), unit="ms")),
              ts_max_used=str(pd.to_datetime(mts.max(), unit="ms")), n_missing_minutes_2021_2025=int(NM - len(mts)),
              key_semantics="market.bin[t] = nen 1m open-time t (V1 probe: A khop, B lech)")
log.info("market.bin: %s", MBINFO)

# ---------------- mau ----------------
samp_ts = np.arange(S_START, S_END, G15, dtype=np.int64)
p_idx = (samp_ts - TM0) // MIN          # chi so phut market
g_idx = (samp_ts - T0) // G15           # chi so luoi 15'
NS = len(samp_ts)
x = U[p_idx]

# ---------------- x_r: ECDF rateUpAvg(t) trong [t-90d, t) (moi phut market.bin, chi < t) ----------------
W = 90 * 1440
ndays = NM // 1440
Uday = U[:ndays * 1440].reshape(ndays, 1440)
cnt_le = np.zeros(NS, np.int64); cnt_n = np.zeros(NS, np.int64)
kday = p_idx // 1440; mod = p_idx % 1440
assert (mod % 15 == 0).all()
sorted_days = [np.sort(r[~np.isnan(r)]) for r in Uday]
# ngay day du j trong cua so cua mau ngay k khi k-89 <= j <= k-1
for j in range(ndays):
    lo = np.searchsorted(kday, j + 1, "left"); hi = np.searchsorted(kday, j + 89, "right")
    if hi > lo:
        sd = sorted_days[j]
        cnt_le[lo:hi] += np.searchsorted(sd, x[lo:hi], side="right")
        cnt_n[lo:hi] += len(sd)
# ngay k (phut < mod) va ngay k-90 (phut >= mod)
mins = np.arange(1440)
for k in np.unique(kday):
    sl = np.where(kday == k)[0]
    xs = x[sl][:, None]; ms_ = mod[sl][:, None]
    vk = Uday[k][None, :]
    ok = (mins[None, :] < ms_) & ~np.isnan(vk)
    cnt_le[sl] += (ok & (vk <= xs)).sum(1); cnt_n[sl] += ok.sum(1)
    if k - 90 >= 0:
        v0 = Uday[k - 90][None, :]
        ok0 = (mins[None, :] >= ms_) & ~np.isnan(v0)
        cnt_le[sl] += (ok0 & (v0 <= xs)).sum(1); cnt_n[sl] += ok0.sum(1)
WARM = 14 * 1440
xr = np.where((cnt_n >= WARM) & ~np.isnan(x), cnt_le / np.maximum(cnt_n, 1), np.nan)
# V2: brute force 300 mau
rng = np.random.default_rng(20261020)
chk = rng.choice(np.where(~np.isnan(xr))[0], min(300, int((~np.isnan(xr)).sum())), replace=False)
bad = 0
for i in chk:
    p = p_idx[i]; w = U[p - W:p]; w = w[~np.isnan(w)]
    bad += int(abs((w <= x[i]).sum() / len(w) - xr[i]) > 1e-12 or len(w) != cnt_n[i])
V2 = dict(n_check=int(len(chk)), n_mismatch=bad, window="[t-90d, t) moi phut market.bin (khong gom t)", ecdf="#{w<=x}/n",
          warmup_min_minutes=WARM, n_nan_xr=int(np.isnan(xr).sum()), n_nan_x=int(np.isnan(x).sum()),
          window_n_min=int(cnt_n.min()), window_n_median=float(np.median(cnt_n)))
V2["ok"] = bad == 0
log.info("V2 x_r: %s", V2)

# ---------------- sau sap ----------------
bdm = (~np.isnan(Dn)) & (Dn < MS_DOWN_BIG_AVG)
cs_bd = np.concatenate([[0], np.cumsum(bdm)])
PD = pd.read_csv("/home/ubuntu/kaggle_sim/out/gqsf-a1/storage/printDone.csv", index_col=False)
PD.columns = [c.strip() for c in PD.columns]
PD = PD[[c for c in PD.columns if c]]
PD["level"] = PD["level"].astype(str).str.strip()
PD["t_start"] = pd.to_datetime(PD["start"].astype(str).str.strip(), format="%Y%m%d %H:%M") - pd.Timedelta(hours=7)
PD["t_end7"] = pd.to_datetime(PD["end"].astype(str).str.strip(), format="%Y%m%d %H:%M")
CB = PD[PD["level"] == "BIG_DOWN"].copy()
cbm = np.zeros(NM, bool)
ci = ((CB["t_start"].astype("int64") // 10**6 - TM0) // MIN).to_numpy()
ci = ci[(ci >= 0) & (ci < NM)]; cbm[ci] = True
cs_cb = np.concatenate([[0], np.cumsum(cbm)])
# cua so 24h truoc t: phut [t-1440, t] (gom phut t: nen t dong luc t+1' = luc quyet dinh)
a = np.maximum(p_idx - 1440, 0); b = p_idx + 1
post_bd = (cs_bd[b] - cs_bd[a]) > 0
post_cb = (cs_cb[b] - cs_cb[a]) > 0
post = post_bd | post_cb
POST = dict(MS_DOWN_BIG_AVG=float(MS_DOWN_BIG_AVG), src_thr="Configs.java:478 default (profile r4_kg0_k16_f015_g155 khong override)",
            n_bigdown_minutes=int(bdm.sum()), n_cb_legs=int(len(CB)), cb_start_range=[str(CB["t_start"].min()), str(CB["t_start"].max())],
            window="[t-1440', t] gom t", frac_post=float(post.mean()), frac_post_bd=float(post_bd.mean()), frac_post_cb=float(post_cb.mean()),
            frac_post_cb_only=float((post_cb & ~post_bd).mean()))
log.info("sau sap: %s", POST)
del Uday, sorted_days

# ---------------- kline1m -> luoi 15' ----------------
def kfile(m):
    return f"/home/ubuntu/claude_master/gvz/k2021/kline1m-{m}.parquet" if m < "2021-12" else f"/home/ubuntu/vz_e1/raw/kline1m-{m}.parquet"


months = pd.period_range("2021-07", "2025-12", freq="M").astype(str).tolist()
if TEST:
    months = ["2023-03", "2023-04", "2023-05"]
O0 = np.full((NG, SMAX), np.nan, np.float32)   # open nen ts = moc luoi g
C0 = np.full((NG, SMAX), np.nan, np.float32)   # close nen ts = g
C1 = np.full((NG, SMAX), np.nan, np.float32)   # close nen ts = g + 1'
VQ = np.zeros((NG, SMAX), np.float32)          # sum quote_volume nen ts in [g, g+15')
sym2i = {}
KINFO = dict(months=[], rows=0, rows_inactive=0)
for m in months:
    t1 = time.time()
    df = pq.read_table(kfile(m), columns=["ts", "sym", "open", "close", "quote_volume", "active"]).to_pandas()
    df = df[(df["ts"] >= T0) & (df["ts"] < TEND)]
    cats = df["sym"].cat.categories.astype(str)
    for s in cats:
        if s not in sym2i:
            sym2i[s] = len(sym2i)
    assert len(sym2i) <= SMAX
    gmap = np.array([sym2i[s] for s in cats], np.int64)
    si = gmap[df["sym"].cat.codes.to_numpy()]
    tsv = df["ts"].to_numpy(np.int64)
    g = (tsv - T0) // G15; off = ((tsv - T0) % G15) // MIN
    act = df["active"].to_numpy(bool)
    KINFO["rows"] += int(len(df)); KINFO["rows_inactive"] += int((~act).sum())
    qv = df["quote_volume"].to_numpy(np.float64)
    gmin, gmax = int(g.min()), int(g.max())
    flat = (g - gmin) * SMAX + si
    VQ[gmin:gmax + 1] += np.bincount(flat, weights=qv, minlength=(gmax - gmin + 1) * SMAX).reshape(-1, SMAX).astype(np.float32)
    op, cl = df["open"].to_numpy(np.float64), df["close"].to_numpy(np.float64)
    s0 = (off == 0) & act; O0[g[s0], si[s0]] = op[s0]; C0[g[s0], si[s0]] = cl[s0]
    s1 = (off == 1) & act; C1[g[s1], si[s1]] = cl[s1]
    KINFO["months"].append(m)
    log.info("kline %s rows %d inactive %d nsym_tot %d (%.1fs)", m, len(df), int((~act).sum()), len(sym2i), time.time() - t1)
    del df, tsv, g, off, act, qv, flat, op, cl, si
NSY = len(sym2i)
i2sym = np.array(sorted(sym2i, key=sym2i.get))
KINFO.update(n_sym=NSY, note="hang active=False (khong co giao dich, gia ffill, gom coin da delist) coi la KHONG CO GIA cho gio/vao/ra; "
             "volume cua chung = 0")
O0, C0, C1, VQ = O0[:, :NSY], C0[:, :NSY], C1[:, :NSY], VQ[:, :NSY]
# vol24 tai moc g = sum VQ[g-96 .. g-1] (1440 phut truoc t, khong gom nen t)
V24 = np.zeros((NG, NSY), np.float32)
for c0 in range(0, NSY, 100):
    cs = np.concatenate([np.zeros((1, min(100, NSY - c0))), np.cumsum(VQ[:, c0:c0 + 100].astype(np.float64), axis=0)], axis=0)
    gg = np.arange(NG)
    V24[:, c0:c0 + 100] = (cs[gg] - cs[np.maximum(gg - 96, 0)]).astype(np.float32)
    V24[:96, c0:c0 + 100] = np.nan
del VQ
log.info("kline xong: %s", {k: v for k, v in KINFO.items() if k != "months"})

excl_cols = np.array([s in EXCL for s in i2sym])
btc_col = sym2i.get("BTCUSDT")

# ---------------- gio + return ----------------
RES = {}
CH = 4000
for bk in ("LIQ24", "RISE24"):
    for hn, hm in HS.items():
        RES[(bk, hn)] = dict(gross=np.full(NS, np.nan), nsel=np.zeros(NS, np.int16), nval=np.zeros(NS, np.int16))
for hn, hm in HS.items():
    RES[("BTC", hn)] = dict(gross=np.full(NS, np.nan), nsel=np.zeros(NS, np.int16), nval=np.zeros(NS, np.int16))
for c in range(0, NS, CH):
    gs = g_idx[c:c + CH]
    o0, c0_, c1 = O0[gs], C0[gs], C1[gs]
    have = ~np.isnan(c0_) & ~np.isnan(o0)
    have[:, excl_cols] = False
    r1 = c0_ / o0 - 1.0
    # LIQ24
    v = np.where(have & ~np.isnan(V24[gs]), V24[gs], -np.inf)
    selL = np.argpartition(-v, K, axis=1)[:, :K]
    okL = np.take_along_axis(v, selL, 1) > -np.inf
    # RISE24 (loc nhu cong thuc: bo > +0.3; died da loai)
    rr = np.where(have & (r1 <= 0.3), r1, -np.inf)
    selR = np.argpartition(-rr, K, axis=1)[:, :K]
    okR = np.take_along_axis(rr, selR, 1) > -np.inf
    for hn, hm in HS.items():
        gx = gs + hm // 15
        valid_t = (samp_ts[c:c + CH] + MIN + hm * MIN) < TEND
        gx = np.minimum(gx, NG - 1)
        cx = C1[gx]
        ret = cx / c1 - 1.0
        for bk, sel, ok in (("LIQ24", selL, okL), ("RISE24", selR, okR)):
            rt = np.take_along_axis(ret, sel, 1)
            vv = ok & ~np.isnan(rt)
            n_ok, n_v = ok.sum(1), vv.sum(1)
            gr = np.where(n_v > 0, np.where(vv, rt, 0).sum(1) / np.maximum(n_v, 1), np.nan)
            gr[~valid_t] = np.nan
            RES[(bk, hn)]["gross"][c:c + CH] = gr
            RES[(bk, hn)]["nsel"][c:c + CH] = np.where(valid_t, n_ok, 0)
            RES[(bk, hn)]["nval"][c:c + CH] = np.where(valid_t, n_v, 0)
        rb = ret[:, btc_col].astype(np.float64); rb[~valid_t] = np.nan
        RES[("BTC", hn)]["gross"][c:c + CH] = rb
        RES[("BTC", hn)]["nsel"][c:c + CH] = valid_t.astype(np.int16)
        RES[("BTC", hn)]["nval"][c:c + CH] = (valid_t & ~np.isnan(rb)).astype(np.int16)
    if c == 0:
        # V3 mau: luu vai (mau, coin) de doi chieu parquet
        V3PICK = [(int(c + i), int(selL[i, 0])) for i in range(0, min(CH, len(gs)), max(1, len(gs) // 6))]
log.info("gio xong (%.0fs)", time.time() - t_run)

# V3: doi chieu gia vao/ra voi parquet goc
V3 = []
for i, s in V3PICK:
    t = int(samp_ts[i]); sym = i2sym[s]
    for hn, hm in HS.items():
        te, tx = t + MIN, t + MIN + hm * MIN
        vals = {}
        for lab, tt in (("entry", te), ("exit", tx)):
            mth = pd.to_datetime(tt, unit="ms").strftime("%Y-%m")
            if mth not in months or tt >= TEND:
                vals[lab] = None; continue
            tb = pq.read_table(kfile(mth), columns=["ts", "sym", "close", "active"], filters=[("ts", "=", tt)]).to_pandas()
            tb = tb[(tb["sym"].astype(str) == sym) & tb["active"]]
            vals[lab] = float(tb["close"].iloc[0]) if len(tb) else None
        ge, gx = int(g_idx[i]), int(g_idx[i]) + hm // 15
        mine_e = float(C1[ge, s]); mine_x = float(C1[gx, s]) if gx < NG else None
        V3.append(dict(t=str(pd.to_datetime(t, unit="ms")), sym=sym, H=hn, entry_parquet=vals["entry"], entry_ours=mine_e,
                       exit_parquet=vals["exit"], exit_ours=mine_x,
                       ok=bool((vals["entry"] is None or abs(vals["entry"] - mine_e) <= 1e-6 * abs(vals["entry"]))
                               and (vals["exit"] is None or mine_x is None or abs(vals["exit"] - mine_x) <= 1e-6 * abs(vals["exit"])))))
V3ok = all(r["ok"] for r in V3)
log.info("V3 gia vao=close nen ts t+1', ra=close nen ts t+1'+H: %d dong doi chieu, ok=%s", len(V3), V3ok)
del O0, C0, C1, V24

# ---------------- bang mau ----------------
E = pd.DataFrame(dict(ts=samp_ts, x=x.astype(np.float64), xr=xr, post=post, post_bd=post_bd, post_cb=post_cb,
                      win_n=cnt_n))
E["t"] = pd.to_datetime(E["ts"], unit="ms")
E["period"] = np.where(E["ts"] < D_END, "D", "C")
E["year"] = E["t"].dt.year
E["day"] = E["t"].dt.floor("D")
for (bk, hn), r in RES.items():
    E[f"g_{bk}_{hn}"] = r["gross"]; E[f"nsel_{bk}_{hn}"] = r["nsel"]; E[f"nval_{bk}_{hn}"] = r["nval"]
BASKETS = ["LIQ24", "RISE24", "BTC"]
MISS = {}
for bk in BASKETS:
    for hn in HS:
        ns, nv = E[f"nsel_{bk}_{hn}"].sum(), E[f"nval_{bk}_{hn}"].sum()
        MISS[f"{bk}_{hn}"] = dict(n_coin_sel=int(ns), n_coin_valid=int(nv), frac_missing=float(1 - nv / max(ns, 1)),
                                  n_sample_nan=int(E[f"g_{bk}_{hn}"].isna().sum()),
                                  frac_sample_lt24=float((E[f"nsel_{bk}_{hn}"] < K).mean()) if bk != "BTC" else None)
log.info("ti le thieu coin: %s", MISS)


def stats(r, day):
    m = ~np.isnan(r)
    r, day = r[m], day[m]
    n = len(r)
    if n == 0:
        return dict(n=0)
    mu = float(r.mean())
    e = r - mu
    sg = pd.Series(e).groupby(day.values if hasattr(day, "values") else day).sum().to_numpy()
    G = len(sg)
    tt = tg = np.nan
    if G > 1 and n > 1:
        V = G / (G - 1) * float((sg ** 2).sum()) / n ** 2
        if V > 0:
            tt, tg = (mu - FEE) / np.sqrt(V), mu / np.sqrt(V)
    net = r - FEE
    return dict(n=n, n_day=G, gross=mu, net=mu - FEE, median_net=float(np.median(net)), win_net=float((net > 0).mean()),
                t_cl=float(tt), t_cl_gross=float(tg))


# Buoc 1: decile x_r cutoff theo D
mD = (E["period"] == "D") & E["xr"].notna()
CUT_XR = [float(v) for v in np.quantile(E.loc[mD, "xr"], np.arange(1, 10) / 10)]
CUT_X = [float(v) for v in np.quantile(E.loc[(E["period"] == "D") & E["x"].notna(), "x"], np.arange(1, 10) / 10)]
QX = {q: float(np.quantile(E.loc[(E["period"] == "D") & E["x"].notna(), "x"], q)) for q in (0.99, 0.999)}
E["dec_xr"] = np.where(E["xr"].notna(), np.searchsorted(CUT_XR, E["xr"].fillna(0), side="right") + 1, 0)
E["dec_x"] = np.where(E["x"].notna(), np.searchsorted(CUT_X, E["x"].fillna(0), side="right") + 1, 0)
log.info("cutoff decile x_r (D): %s", np.round(CUT_XR, 4).tolist())
log.info("cutoff decile x (D): %s ; x q99/q999 (D): %s", np.round(CUT_X, 6).tolist(), QX)


def classes(var):
    if var == "xr":
        cl = {f"d{k}": E["dec_xr"] == k for k in range(1, 11)}
        cl["ge0.99"] = E["xr"] >= 0.99; cl["ge0.999"] = E["xr"] >= 0.999
    else:
        cl = {f"d{k}": E["dec_x"] == k for k in range(1, 11)}
        cl["geQ99D"] = E["x"] >= QX[0.99]; cl["geQ999D"] = E["x"] >= QX[0.999]
    return cl


REG = {"all": np.ones(len(E), bool), "em": ~E["post"].to_numpy(), "post": E["post"].to_numpy()}
TAB1 = {}
for var in ("xr", "x"):
    cls = classes(var)
    TAB1[var] = {}
    for per in ("D", "C"):
        mp = (E["period"] == per).to_numpy()
        for rg, mr in REG.items():
            for cn, mc in cls.items():
                mm = mp & mr & mc.to_numpy()
                for bk in BASKETS:
                    for hn in HS:
                        key = f"{per}|{rg}|{cn}|{bk}|{hn}"
                        TAB1[var][key] = stats(E.loc[mm, f"g_{bk}_{hn}"].to_numpy(), E.loc[mm, "day"])
for var in ("xr",):
    for per in ("D", "C"):
        for rg in ("all", "em", "post"):
            log.info("==== B1 %s %s %s (net TB %% | t_cl | n) ====", var, per, rg)
            for cn in classes(var):
                row = []
                for bk in BASKETS:
                    for hn in HS:
                        s = TAB1[var][f"{per}|{rg}|{cn}|{bk}|{hn}"]
                        row.append("%s%s %+.3f%% t%+.1f n%d" % (bk[:3], hn, 100 * s.get("net", np.nan), s.get("t_cl", np.nan), s["n"]) if s["n"] else f"{bk[:3]}{hn} -")
                log.info("%-8s %s", cn, " | ".join(row))

# ---------------- Buoc 2: luat rolling (chon tren D) ----------------
def events(bk, hn, q):
    hm = HS[hn]
    col = f"g_{bk}_{hn}"
    m = (E["xr"] >= q) & (~E["post"]) & E[col].notna()
    ev = E.loc[m, ["ts", "t", "day", "period", "year", "x", "xr", col]].sort_values("ts")
    keep, last = [], -10**18
    for tsv in ev["ts"].to_numpy():
        if tsv - last >= hm * MIN:
            keep.append(True); last = tsv
        else:
            keep.append(False)
    ev = ev[np.array(keep, bool)].rename(columns={col: "gross"})
    ev["net"] = ev["gross"] - FEE
    ev["cand"] = f"{bk}|{hn}|{q}"
    return ev


CANDS = [(bk, hn, q) for bk in ("LIQ24", "RISE24") for hn in HS for q in (0.99, 0.999)]
EVS, B2D = {}, {}
for c in CANDS:
    ev = events(*c)
    EVS[c] = ev
    d = ev[ev["period"] == "D"]
    B2D["|".join(map(str, c))] = stats(d["gross"].to_numpy(), d["day"])
    s = B2D["|".join(map(str, c))]
    log.info("B2 D %-22s n %4d net %+.3f%% med %+.3f%% win %.1f%% t_cl %+.2f", "|".join(map(str, c)), s["n"],
             100 * s.get("net", np.nan), 100 * s.get("median_net", np.nan), 100 * s.get("win_net", np.nan), s.get("t_cl", np.nan))
elig = [(B2D[k]["net"], k) for k in B2D if B2D[k]["n"] >= 50 and B2D[k]["net"] > 0]
elig.sort(reverse=True)
RULE = dict(eligible_D=[dict(cand=k, net=v) for v, k in elig])
if not elig:
    RULE.update(selected=None, verdict="DONG - khong ung vien D (>=50 su kien, net>0)")
    SEL = None
else:
    sk = elig[0][1]
    SEL = [c for c in CANDS if "|".join(map(str, c)) == sk][0]
    ev = EVS[SEL]; ec = ev[ev["period"] == "C"]
    sc = stats(ec["gross"].to_numpy(), ec["day"])
    yr = {int(y): stats(g["gross"].to_numpy(), g["day"]) for y, g in ec.groupby("year")}
    c1 = sc["n"] > 0 and sc["net"] > 0
    c2 = sc["n"] > 0 and sc["t_cl"] > 2
    c3 = all(y in yr and yr[y]["n"] > 0 and yr[y]["net"] > 0 for y in (2024, 2025))
    c4 = sc["n"] >= 30
    RULE.update(selected=sk, D=B2D[sk], C=sc, C_by_year=yr, c_net_pos=bool(c1), c_t_gt2=bool(c2), c_pos_2024_2025=bool(c3), c_n_ge30=bool(c4),
                verdict="DAT D+C -> viet prereg tang B" if (c1 and c2 and c3 and c4) else "DONG - dat D nhung truot C")
log.info("LUAT: %s", RULE)

# ---------------- mo ta: tuong quan PnL ngay voi crash-buy ----------------
CB["d7"] = CB["t_end7"].dt.floor("D")
cbd = CB.groupby("d7")["pnl"].sum()
CORR = {}
if SEL is not None:
    ev = EVS[SEL].copy()
    ev["d7"] = (ev["t"] + pd.Timedelta(minutes=1 + HS[SEL[1]]) + pd.Timedelta(hours=7)).dt.floor("D")
    for per, (a_, b_) in {"D": ("2021-08-01", "2023-12-31"), "C": ("2024-01-01", "2025-12-31")}.items():
        days = pd.date_range(a_, b_, freq="D")
        s1 = ev.groupby("d7")["net"].sum().reindex(days, fill_value=0.0)
        s2 = cbd.reindex(days, fill_value=0.0)
        both = (s1 != 0) | (s2 != 0)
        CORR[per] = dict(pearson_all_days=float(np.corrcoef(s1, s2)[0, 1]) if s1.std() > 0 and s2.std() > 0 else None,
                         spearman_all_days=float(s1.rank().corr(s2.rank())),
                         pearson_active_days=float(np.corrcoef(s1[both], s2[both])[0, 1]) if both.sum() > 2 else None,
                         n_days=int(len(days)), n_ev_days=int((s1 != 0).sum()), n_cb_days=int((s2 != 0).sum()),
                         n_overlap_days=int(((s1 != 0) & (s2 != 0)).sum()))
    CORR["note"] = ("ung vien: 1 don vi/su kien, PnL net theo ngay +07 cua thoi diem ra; crash-buy: sum pnl chan BIG_DOWN gqsf-a1 theo ngay dong (end +07); "
                    "gqsf-a1 pham vi start " + str(PD["t_start"].min()) + ".." + str(PD["t_start"].max()))
log.info("tuong quan crash-buy: %s", CORR)

V4 = dict(cutoff_decile_from="D only", candidate_selection_from="D only; C chi tinh cho ung vien da chon",
          D_rows_in_cutoff=int(mD.sum()))
OUT = dict(prereg="PREREG_UP_TRIG.md@81f4fbf3", test=TEST, run_s=time.time() - t_run, market_bin=MBINFO, kline=KINFO,
           conventions=dict(time="UTC", key="market.bin[t]=nen open-time t; vao close nen t+1', ra close nen t+1'+H",
                            fee=FEE, sample="moi 15' tu 2021-08-01 den 2025-12-31, bo mau co t+1'+H >= 2026-01-01",
                            liq24="24 coin sum quote_volume nen [t-1440', t) lon nhat, co gia (active) tai t; tru BTC/ETH/BTCDOM/USDC",
                            rise24="24 coin r=close/open-1 nen t lon nhat, bo r>0.3, co gia tai t; tru BTC/ETH/BTCDOM/USDC",
                            missing="coin thieu close (active) tai t+1' hoac t+1'+H -> bo khoi gio (khong bu)",
                            win="ti le net>0", t_cl="SE cum theo ngay UTC cua t (CR1 G/(G-1))", dedup="giu su kien dau, bo su kien t < t_giu + H"),
           V1=json.load(open(os.path.join(OUTD, "ut_v1_probe.json"))) if os.path.exists(os.path.join(OUTD, "ut_v1_probe.json")) else None,
           V2=V2, V3=dict(rows=V3, ok=V3ok), V4=V4, post=POST, missing=MISS, cut_xr_D=CUT_XR, cut_x_D=CUT_X, q_x_D=QX,
           n_samples=dict(total=int(len(E)), D=int((E["period"] == "D").sum()), C=int((E["period"] == "C").sum()),
                          xr_valid=int(E["xr"].notna().sum()), em=int((~E["post"]).sum())),
           table1=TAB1, step2_D=B2D, rule=RULE, corr_crashbuy=CORR)
json.dump(OUT, open(os.path.join(OUTD, TAG + ".json"), "w"), indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
EV = pd.concat([EVS[c] for c in CANDS], ignore_index=True)
EV.to_parquet(os.path.join(OUTD, TAG + "_events.parquet"))
E.drop(columns=["t", "day"]).to_parquet(os.path.join(OUTD, TAG + "_samples.parquet"))
log.info("ghi %s (%.0fs)", os.path.join(OUTD, TAG + ".json"), time.time() - t_run)
