#!/usr/bin/env python3
"""UP_TRIG2 tang A - PREREG_UP_TRIG2.md (commit 90be57a5). Chay 1 lan, khong tune.
Su kien: dung lai x_r/post cua ut_a (2021-08..2025) va ut_ho (2026, nguon ghep market.bin + tinh lai) - cung code UP_TRIG.
Gio UTC. Vao close nen t+1', ra close nen t+1'+24h, phi 0.10%."""
import glob, json, logging, os, sys, time, zipfile
import numpy as np, pandas as pd, pyarrow.parquet as pq

OUTD = "/home/ubuntu/claude_master/up_trig"; KL = OUTD + "/kl"; os.makedirs(KL, exist_ok=True)
TAG = "ut2_a"
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s",
                    handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler(os.path.join(OUTD, TAG + ".log"), mode="w")])
log = logging.getLogger("ut2")
MS = lambda s: int(pd.Timestamp(s).value // 10**6)  # noqa: E731
MIN, G15 = 60000, 900000
T0, TEND = MS("2021-07-01"), MS("2026-10-01")
D_END, C_END = MS("2024-01-01"), MS("2026-01-01")
S1_D0 = MS("2022-01-01")
HM, FEE = 1440, 0.001
EXCL = {"BTCUSDT", "ETHUSDT", "BTCDOMUSDT", "USDCUSDT"}
NG = (TEND - T0) // G15; SMAX = 1300
t_run = time.time()

# ---------------- mau + su kien (dung lai ut_a / ut_ho) ----------------
SA = pd.read_parquet(OUTD + "/ut_a_samples.parquet", columns=["ts", "xr", "post", "g_RISE24_24h"]).rename(columns={"g_RISE24_24h": "gR24"})
SH = pd.read_parquet(OUTD + "/ut_ho_samples.parquet", columns=["ts", "xr", "post", "g_RISE24"]).rename(columns={"g_RISE24": "gR24"})


def dedup(S, q):
    ev = S[(S["xr"] >= q) & (~S["post"]) & S["gR24"].notna()].sort_values("ts")
    keep, last = [], -10**18
    for tsv in ev["ts"].to_numpy():
        ok = tsv - last >= HM * MIN
        keep.append(ok)
        if ok:
            last = tsv
    return ev[np.array(keep, bool)]


E99 = pd.concat([dedup(SA, 0.99), dedup(SH, 0.99)]); E95 = pd.concat([dedup(SA, 0.95), dedup(SH, 0.95)])
# V3: trung tap su kien UP_TRIG goc
EA = pd.read_parquet(OUTD + "/ut_a_events.parquet"); EA = EA[EA["cand"] == "RISE24|24h|0.99"]
EH = pd.read_parquet(OUTD + "/ut_ho_events.parquet")
orig = set(EA["ts"].astype(np.int64)) | set(EH["ts"].astype(np.int64))
V3 = dict(n_E99=int(len(E99)), n_orig=len(orig), same_set=set(E99["ts"].astype(np.int64)) == orig)
log.info("V3 su kien x_r>=0.99 trung UP_TRIG goc (ut_a+ut_ho): %s", V3)
assert V3["same_set"]
E95 = E95.assign(K=np.where(E95["xr"] >= 0.99, 24, 5))
log.info("E95: n %d (K=24: %d, K=5: %d)", len(E95), int((E95["K"] == 24).sum()), int((E95["K"] == 5).sum()))
EVTS = np.union1d(E99["ts"].to_numpy(np.int64), E95["ts"].to_numpy(np.int64))

# ---------------- gia: kline 2021-07..2025-12 local, 2026-01..09 Kaggle ----------------
A = None


def kpath(ym):
    global A
    if ym < "2021-12":
        return f"/home/ubuntu/claude_master/gvz/k2021/kline1m-{ym}.parquet", False
    if ym < "2026":
        return f"/home/ubuntu/vz_e1/raw/kline1m-{ym}.parquet", False
    p = f"{KL}/kline1m-{ym}.parquet"
    if not os.path.exists(p):
        if A is None:
            from kaggle.api.kaggle_api_extended import KaggleApi
            A = KaggleApi(); A.authenticate()
        A.dataset_download_file("chuyendinh/vz-kline1m-2026", f"kline1m-{ym}.parquet", path=KL, quiet=True)
        for z in glob.glob(KL + "/*.zip"):
            with zipfile.ZipFile(z) as f:
                f.extractall(KL)
            os.remove(z)
    return p, True


months = pd.period_range("2021-07", "2026-09", freq="M").astype(str).tolist()
TEST = "--test" in sys.argv
if TEST:
    months = months[:3]
O0 = np.full((NG, SMAX), np.nan, np.float32); C0 = np.full((NG, SMAX), np.nan, np.float32); C1 = np.full((NG, SMAX), np.nan, np.float32)
sym2i = {}
for ym in months:
    t1 = time.time()
    p, dl = kpath(ym)
    df = pq.read_table(p, columns=["ts", "sym", "open", "close", "active"]).to_pandas()
    if df["sym"].dtype.name != "category":
        df["sym"] = df["sym"].astype("category")
    df = df[(df["ts"] >= T0) & (df["ts"] < TEND) & df["active"].to_numpy(bool)]
    cats = df["sym"].cat.categories.astype(str)
    for s in cats:
        if s not in sym2i:
            sym2i[s] = len(sym2i)
    assert len(sym2i) <= SMAX
    si = np.array([sym2i[s] for s in cats], np.int64)[df["sym"].cat.codes.to_numpy()]
    tsv = df["ts"].to_numpy(np.int64); g = (tsv - T0) // G15; off = ((tsv - T0) % G15) // MIN
    op, cl = df["open"].to_numpy(np.float64), df["close"].to_numpy(np.float64)
    s0 = off == 0; O0[g[s0], si[s0]] = op[s0]; C0[g[s0], si[s0]] = cl[s0]
    s1 = off == 1; C1[g[s1], si[s1]] = cl[s1]
    del df, tsv, g, off, op, cl, si
    if dl:
        os.remove(p)
    log.info("kline %s nsym %d (%.0fs)", ym, len(sym2i), time.time() - t1)
NSY = len(sym2i); i2sym = np.array(sorted(sym2i, key=sym2i.get))
O0, C0, C1 = O0[:, :NSY], C0[:, :NSY], C1[:, :NSY]
excl = np.array([s in EXCL for s in i2sym]); btc = sym2i["BTCUSDT"]

# ---------------- S1 REX ----------------
P1 = pd.read_parquet("/home/ubuntu/claude_master/rex/pred_s1.parquet")
P1["dayms"] = P1["day"].astype("int64") // 10**6
S1 = {d: g for d, g in P1.groupby("dayms")}
S1INFO = dict(file="/home/ubuntu/claude_master/rex/pred_s1.parquet", day_min=str(P1["day"].min()), day_max=str(P1["day"].max()),
              n_sym=int(P1["sym"].nunique()),
              direction="lon = tot (s1_diag.log: decile 9 y cao nhat, decile 0 thap nhat; portfolio REX lay top score)",
              timing="score ngay d dung de giu close d -> close d+1 trong REX (rex_s1.py portfolio) => biet tai cuoi ngay d; dung ngay (t UTC)-1")

# ---------------- gio cho tung su kien ----------------
def baskets(ts):
    g = (ts - T0) // G15; gx = g + HM // 15
    o0, c0, c1, cx = O0[g], C0[g], C1[g], C1[gx]
    r1 = c0 / o0 - 1.0
    ret = cx / c1 - 1.0
    have = ~np.isnan(o0) & ~np.isnan(c0) & ~excl
    rr = np.where(have & (r1 <= 0.3), r1, -np.inf)
    order = np.argsort(-rr, kind="stable")
    out = {}

    def take(idx):
        idx = np.asarray(idx, np.int64)
        v = ret[idx]; ok = ~np.isnan(v)
        return (float(v[ok].mean()) if ok.any() else np.nan), int(len(idx)), int(ok.sum()), list(i2sym[idx[ok]]), [float(x) for x in v[ok]]
    for k in (5, 10, 24):
        top = order[:k]; top = top[rr[top] > -np.inf]
        out[f"RISE{k}"] = take(top)
    d1 = (ts // 86400000) * 86400000 - 86400000
    sc = S1.get(d1)
    for k in (10, 24):
        if sc is None or ts < S1_D0:
            out[f"S1REX{k}"] = (np.nan, 0, 0, [], []); continue
        ss = sc[sc["sym"].isin(sym2i.keys()) & ~sc["sym"].isin(EXCL)].copy()
        ss["i"] = ss["sym"].map(sym2i)
        ss = ss[~np.isnan(c1[ss["i"].to_numpy()])]                 # co gia vao (close t+1')
        top = ss.sort_values("score", ascending=False, kind="stable")["i"].to_numpy()[:k]
        out[f"S1REX{k}"] = take(top)                                # thieu gia ra -> bo coin (khong bu), nhu UP_TRIG
    out["BTC"] = (float(ret[btc]), 1, int(~np.isnan(ret[btc])), ["BTCUSDT"], [float(ret[btc])])
    out["_s1day"] = str(pd.to_datetime(d1, unit="ms").date())
    return out


B = {int(t): baskets(int(t)) for t in EVTS}
log.info("gio xong %d su kien (%.0fs)", len(B), time.time() - t_run)
# kiem chung: RISE24 tinh lai = gR24 cua ut_a/ut_ho
gr = pd.concat([SA, SH]).set_index("ts")["gR24"]
dif = [abs(B[t]["RISE24"][0] - gr.loc[t]) for t in E99["ts"].astype(np.int64)]
CHK = dict(n=len(dif), max_abs_diff_RISE24_vs_orig=float(np.nanmax(dif)))
log.info("kiem RISE24 tinh lai vs goc: %s", CHK)
if TEST:
    ok = [t for t in E99["ts"].astype(np.int64) if not np.isnan(B[t]["RISE24"][0])]
    log.info("TEST: %d su kien co gio; vi du %s", len(ok), {k: v[:3] for k, v in B[ok[0]].items() if k != "_s1day"} if ok else None)
    sys.exit(0)


# ---------------- thong ke ----------------
def per_of(ts):
    return np.where(ts < D_END, "D", np.where(ts < C_END, "C", "2026"))


def stats(r, day):
    m = ~np.isnan(r); r, day = r[m], np.asarray(day)[m]; n = len(r)
    if n == 0:
        return dict(n=0)
    mu = float(r.mean()); e = r - mu
    sg = pd.Series(e).groupby(day).sum().to_numpy(); G = len(sg); tt = np.nan
    if G > 1:
        V = G / (G - 1) * float((sg ** 2).sum()) / n ** 2
        tt = (mu - FEE) / np.sqrt(V) if V > 0 else np.nan
    net = np.sort(r - FEE)
    return dict(n=n, net=mu - FEE, median_net=float(np.median(net)), win=float((net > 0).mean()), t_cl=float(tt),
                ex_top5=float(net[:-5].mean()) if n > 5 else None)


VAR = {"V1_RISE5": ("E99", lambda o, k: o["RISE5"]), "V2_RISE10": ("E99", lambda o, k: o["RISE10"]),
       "V3_S1REX10": ("E99", lambda o, k: o["S1REX10"]), "V4_S1REX24": ("E99", lambda o, k: o["S1REX24"]),
       "V5_RISE_SCALED": ("E95", lambda o, k: o[f"RISE{k}"])}
ROWS, TAB, PRINT3 = [], {}, {}
for v, (es, f) in VAR.items():
    E = E99 if es == "E99" else E95
    for _, e in E.iterrows():
        t = int(e["ts"]); k = int(e["K"]) if es == "E95" else None
        g, nsel, nval, coins, rets = f(B[t], k)
        ROWS.append(dict(var=v, ts=t, xr=float(e["xr"]), K=k, gross=g, btc=B[t]["BTC"][0], nsel=nsel, nval=nval,
                         coins=",".join(coins), s1day=B[t]["_s1day"]))
R = pd.DataFrame(ROWS)
R["t"] = pd.to_datetime(R["ts"], unit="ms"); R["day"] = R["t"].dt.floor("D"); R["year"] = R["t"].dt.year
R["period"] = per_of(R["ts"].to_numpy())
R["ex_btc"] = R["gross"] - R["btc"]
# D cua V3/V4 bat dau 2022-01
R.loc[R["var"].str.startswith(("V3", "V4")) & (R["ts"] < S1_D0), "period"] = "preD"
for v in VAR:
    TAB[v] = {}
    for per in ("D", "C", "2026"):
        g = R[(R["var"] == v) & (R["period"] == per)]
        s = stats(g["gross"].to_numpy(), g["day"])
        x = g["ex_btc"].dropna()
        s.update(ex_btc_gross=float(x.mean()) if len(x) else None, frac_coin_missing=float(1 - g["nval"].sum() / max(g["nsel"].sum(), 1)),
                 n_empty=int(g["gross"].isna().sum()),
                 by_year={int(y): dict(n=int(len(gg)), net=float(gg["gross"].mean() - FEE)) for y, gg in g.groupby("year") if gg["gross"].notna().any()})
        TAB[v][per] = s
    gg = R[(R["var"] == v) & R["gross"].notna()].head(3)
    PRINT3[v] = gg[["t", "xr", "K", "nsel", "nval", "gross", "btc", "s1day", "coins"]].astype(str).to_dict("records")
for v in VAR:
    for per in ("D", "C", "2026"):
        s = TAB[v][per]
        if s["n"]:
            log.info("%-15s %-4s n %4d net %+.3f%% med %+.3f%% win %.1f%% t %+.2f exBTC %+.3f%% exTop5 %s nam %s", v, per, s["n"], 100 * s["net"],
                     100 * s["median_net"], 100 * s["win"], s["t_cl"], 100 * s["ex_btc_gross"],
                     None if s["ex_top5"] is None else "%+.3f%%" % (100 * s["ex_top5"]), {y: "%d:%+.2f%%" % (d["n"], 100 * d["net"]) for y, d in s["by_year"].items()})
        else:
            log.info("%-15s %-4s n 0", v, per)
    log.info("V1 in 3 su kien %s: %s", v, PRINT3[v])
# V2
s1chk = R[R["var"].str.startswith(("V3", "V4")) & R["gross"].notna()]
V2 = dict(n=int(len(s1chk)), all_s1day_eq_tday_minus1=bool((pd.to_datetime(s1chk["s1day"]) == s1chk["day"] - pd.Timedelta(days=1)).all()))
log.info("V2 S1 ngay t-1: %s", V2)

# ---------------- luat (chon tren D) ----------------
elig = sorted([(TAB[v]["D"]["net"], v) for v in VAR if TAB[v]["D"]["n"] >= 50 and TAB[v]["D"]["net"] > 0], reverse=True)
RULE = dict(eligible_D=[dict(var=v, net=x, n=TAB[v]["D"]["n"]) for x, v in elig])
if not elig:
    RULE.update(selected=None, verdict="DONG ho UP_TRIG (khong bien the D >=50 su kien & net>0)")
else:
    v = elig[0][1]; c = TAB[v]["C"]
    by = c["by_year"]
    conds = dict(net_pos=c["n"] > 0 and c["net"] > 0, t_gt2=c["n"] > 0 and c["t_cl"] > 2,
                 pos_2024_2025=all(y in by and by[y]["net"] > 0 for y in (2024, 2025)), n_ge30=c["n"] >= 30,
                 ex_btc_pos=c.get("ex_btc_gross") is not None and c["ex_btc_gross"] > 0)
    RULE.update(selected=v, D=TAB[v]["D"], C=c, conds={k: bool(x) for k, x in conds.items()},
                verdict="DAT -> chi de xuat forward paper log" if all(conds.values()) else "TRUOT C -> DONG ho UP_TRIG vinh vien")
log.info("LUAT: %s", RULE)
V4 = dict(selection_uses="TAB[*]['D'] only", C_used_only_for="bien the da chon", y2026="chi mo ta")
OUT = dict(prereg="PREREG_UP_TRIG2.md@90be57a5", run_s=time.time() - t_run, V1_print3=PRINT3, V2=V2, V3=V3, V4=V4, check_rise24=CHK,
           s1=S1INFO, n_E99=int(len(E99)), n_E95=int(len(E95)), table=TAB, rule=RULE,
           conventions=dict(events="x_r/post tu ut_a_samples (2021-08..2025) va ut_ho_samples (2026); bo trung 24h rieng tung nguon",
                            s1_basket="top-K score ngay t-1 trong coin co gia vao (active close t+1'), tru BTC/ETH/BTCDOM/USDC; thieu gia ra -> bo coin, khong bu",
                            rise="nhu ut_a: r nen t, bo r>0.3, co gia (active) tai t", D_V3V4="2022-01..2023-12"))
json.dump(OUT, open(os.path.join(OUTD, TAG + ".json"), "w"), indent=1, default=lambda o: o.item() if hasattr(o, "item") else str(o))
R.drop(columns=["day"]).to_parquet(os.path.join(OUTD, TAG + "_events.parquet"))
log.info("ghi xong (%.0fs)", time.time() - t_run)
