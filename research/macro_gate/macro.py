#!/usr/bin/env python3
"""MACRO_GATE P0 (prereg vz_e1_wt 24104dd6 docs/prereg/PREREG_MACRO_GATE.md). Usage: macro.py data | explore | confirm
data   : parse ETF 2 nguon (Yahoo chart v8 adjclose + Nasdaq api), doi chieu, BTC ngay tu store 1h, tin hieu S1-S4,V4,V3,E theo ngay
         quyet dinh (UTC), kiem causal + kiem tay 10 ngay. KHONG doc Y.
explore: dung lai bang leg/cum bang ind_build.load_legs (IND_COMBO 14ed6c00), gan trang thai o phut DAU cum; CHI doc Y EXPLORE;
         X-only cho CONFIRM (tan suat, episode, so khoi thang, MDE80) -> selection.json.
confirm: CONFIRM ung vien + track G + mo ta (bullish, E, HO 2026) -> confirm.json."""
import glob
import json
import logging
import os
import sys

import numpy as np
import pandas as pd
from scipy.stats import norm

sys.path.insert(0, "/home/ubuntu/claude_master/vz_e1_wt/research/ind_combo")
import ind_build as IB  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("macro")
W = os.path.expanduser("~/claude_master/macro1114/")
RAW, OUT = W + "raw/", W + "out/"
NB, RNG = 2000, 20261115
DAY, H, M1 = 86400000, 3600000, 60000
TZ = 7 * H
CORE = ["QQQ", "XLP", "GLD", "UUP"]
ETF = ["IBIT", "FBTC", "ARKB", "BITB", "HODL", "BRRR"]
TESTS = ["S1", "S2", "S3", "S4", "V4", "V3"]
YB = {2022: 1640970000000, 2023: 1672506000000, 2024: 1704042000000, 2025: 1735664400000, 2026: 1767200400000, 2027: 1782838800000}
BTCINFO = {}
G_SEEDS = ["S42", "S7", "S13", "S21", "S99", "S123", "S777", "S2024"]


def jdump(o, f):
    json.dump(o, open(OUT + f, "w"), indent=1, default=lambda x: x.item() if hasattr(x, "item") else str(x))


# ---------------------------------------------------------------- data
def num(s):
    if s is None:
        return np.nan
    s = str(s).replace("$", "").replace(",", "").strip()
    try:
        return float(s)
    except ValueError:
        return np.nan


def load_yahoo(t):
    r = json.load(open(RAW + "yahoo_%s.json" % t))["chart"]["result"][0]
    q = r["indicators"]["quote"][0]
    d = pd.DataFrame(dict(date=pd.to_datetime(np.array(r["timestamp"]) * 1000, unit="ms").normalize(),
                          close=pd.to_numeric(pd.Series(q["close"]), errors="coerce"),
                          vol=pd.to_numeric(pd.Series(q["volume"]), errors="coerce"),
                          adj=pd.to_numeric(pd.Series(r["indicators"]["adjclose"][0]["adjclose"]), errors="coerce")))
    d = d.dropna(subset=["close", "adj"]).drop_duplicates("date", keep="last").set_index("date").sort_index()
    ev = r.get("events", {})
    divs = {pd.Timestamp(int(k) * 1000, unit="ms").normalize(): v["amount"] for k, v in ev.get("dividends", {}).items()}
    spl = len(ev.get("splits", {}))
    return d, divs, spl


def load_nasdaq(t):
    rows = json.load(open(RAW + "nasdaq_%s.json" % t))["data"]["tradesTable"]["rows"]
    d = pd.DataFrame(dict(date=pd.to_datetime([x["date"] for x in rows], format="%m/%d/%Y"),
                          close=[num(x["close"]) for x in rows], vol=[num(x["volume"]) for x in rows]))
    return d.dropna(subset=["close"]).drop_duplicates("date").set_index("date").sort_index()


def btc_daily():
    mp = pd.read_csv("/home/ubuntu/selector_pred_out/symbol_map.csv")
    bid = int(mp.symId[mp.symbol.astype(str) == "BTCUSDT"].iloc[0])
    dt = np.dtype([("t", ">i8"), ("s", ">i2"), ("o", ">f4"), ("h", ">f4"), ("l", ">f4"), ("c", ">f4"), ("v", ">f4")])
    a = np.memmap("/home/ubuntu/java/fsrun/OHLCV_1H_v2.bin", dtype=dt, mode="r")
    m = np.asarray(a["s"]) == bid
    th, c = np.asarray(a["t"][m]).astype(np.int64), np.asarray(a["c"][m]).astype(np.float64)
    del a
    hs = pd.Series(c, index=th)
    ho = "/home/ubuntu/claude_master/ind1114/ho26out/ho26_1h.parquet"
    src2 = 0
    if os.path.exists(ho):
        x = pd.read_parquet(ho, columns=["sym", "th", "c"])
        x = x[(x.sym == "BTCUSDT") & (x.th > hs.index.max())]
        src2 = len(x)
        hs = pd.concat([hs, pd.Series(x.c.to_numpy(np.float64), index=x.th.to_numpy(np.int64))])
    hs = hs[~hs.index.duplicated(keep="first")].sort_index()
    day = (hs.index.to_numpy() - 1) // DAY  # gio dong (D, D+1] -> ngay D
    cnt = pd.Series(1, index=day).groupby(level=0).sum()
    last = hs.groupby(day).last()
    lastt = pd.Series(hs.index.to_numpy(), index=day).groupby(level=0).max()
    ok = (cnt == 24) & (lastt == (lastt.index.to_numpy() + 1) * DAY)
    cl = last[ok]
    cl.index = pd.to_datetime(cl.index.to_numpy() * DAY, unit="ms")
    BTCINFO.update(store_days=len(cl), store_missing_days=int((~ok).sum()), store_last=str(cl.index.max().date()))
    vf = RAW + "btc1d_vision.csv"
    if os.path.exists(vf):  # 2026H1: nen 1d BTCUSDT UM tu data.binance.vision (checksum OK), chi noi SAU ngay cuoi store
        v = pd.read_csv(vf, header=None, usecols=[0, 4, 6])
        v = v[v[6] == v[0] + DAY - 1]
        vs = pd.Series(v[4].to_numpy(np.float64), index=pd.to_datetime(v[0].to_numpy(), unit="ms"))
        com = cl.index.intersection(vs.index)
        BTCINFO.update(overlap_days=len(com), overlap_rel_maxdiff=float((cl.reindex(com) / vs.reindex(com) - 1).abs().max()))
        add = vs[vs.index > cl.index.max()]
        cl = pd.concat([cl, add])
        BTCINFO["vision_days_added"] = len(add)
    log.info("BTC ngay %d, %s..%s %s", len(cl), cl.index.min(), cl.index.max(), BTCINFO)
    return cl


def state(v, up, dn, reverse=False):
    """1 bullish, -1 defensive, 0 neutral, nan thieu. reverse: gia tri cao = defensive (S4)."""
    s = np.where(np.isnan(v), np.nan, 0.0)
    if not reverse:
        s = np.where(v >= up, 1.0, np.where(v <= dn, -1.0, s))
    else:
        s = np.where(v >= up, -1.0, np.where(v <= dn, 1.0, s))
    return np.where(np.isnan(v), np.nan, s)


def vote(cols):
    b = sum((c == 1).astype(int) for c in cols)
    d = sum((c == -1).astype(int) for c in cols)
    anynan = np.any([np.isnan(c) for c in cols], axis=0)
    s = np.where(b >= d + 2, 1.0, np.where(d >= b + 2, -1.0, 0.0))
    return np.where(anynan, np.nan, s)


def build_signals(Y, btc):
    """Y: dict t -> DataFrame (adj, close, vol) theo phien. Tra bang ngay quyet dinh dd (UTC) + bang phien."""
    cal = pd.date_range("2021-11-01", "2026-07-01", freq="D")
    sess = Y["QQQ"].index
    for t in CORE:
        sess = sess.intersection(Y[t].index)
    r20 = {t: Y[t].adj.reindex(sess) / Y[t].adj.reindex(sess).shift(20) - 1 for t in CORE}
    S = pd.DataFrame(index=sess)
    S["qqq20"], S["xlp20"], S["gld20"], S["uup20"] = r20["QQQ"], r20["XLP"], r20["GLD"], r20["UUP"]
    S["S2v"] = S.qqq20
    S["S3v"] = S.qqq20 - S.xlp20
    S["S4v"] = np.maximum(S.gld20, S.uup20)
    # E: diem dong ETF moi phien
    esc = pd.DataFrame(index=sess)
    for t in ETF:
        if t not in Y:
            continue
        y = Y[t]
        sc = 100 * (y.close / y.close.shift(1) - 1) * (y.vol / y.vol.shift(1).rolling(5).mean())
        esc[t] = sc.reindex(sess)
    nin = (esc >= 2.5).sum(1)
    nout = (esc <= -2.5).sum(1)
    tot = esc.sum(1, min_count=1)
    nval = esc.notna().sum(1)
    S["E"] = np.where(nval == 0, np.nan, np.where((nin >= nout + 2) & (tot > 0), 1.0, np.where((nout >= nin + 2) & (tot < 0), -1.0, 0.0)))
    S["E_nval"] = nval
    # map ngay quyet dinh dd -> phien MY cuoi cung < dd (phien D dung tu 00:00 UTC D+1)
    D = pd.DataFrame(index=cal)
    pos = np.searchsorted(sess.values, cal.values, "left") - 1
    D["sess"] = np.where(pos >= 0, sess.values[np.clip(pos, 0, len(sess) - 1)], np.datetime64("NaT"))
    for c in ["qqq20", "xlp20", "gld20", "uup20", "S2v", "S3v", "S4v", "E", "E_nval"]:
        D[c] = np.where(pos >= 0, S[c].to_numpy()[np.clip(pos, 0, len(sess) - 1)], np.nan)
    # BTC: nen ngay dd-1 da dong
    b7 = btc / btc.shift(7) - 1
    b7 = b7[(btc.index.to_series().diff(7) == pd.Timedelta(days=7)).to_numpy()]
    D["btc_day"] = cal - pd.Timedelta(days=1)
    D["S1v"] = b7.reindex(D.btc_day).to_numpy()
    D["S1"] = state(D.S1v.to_numpy(), 0.04, -0.04)
    D["S2"] = state(D.S2v.to_numpy(), 0.03, -0.03)
    D["S3"] = state(D.S3v.to_numpy(), 0.02, -0.02)
    D["S4"] = state(D.S4v.to_numpy(), 0.03, 0.0, reverse=True)
    D["V4"] = vote([D[c].to_numpy() for c in ("S1", "S2", "S3", "S4")])
    D["V3"] = vote([D[c].to_numpy() for c in ("S2", "S3", "S4")])
    return D, S


def hand_check(D, Ynq_raw, btc, rng):
    """kiem tay 10 ngay ngau nhien: tinh lai bang vong lap tu JSON raw (Yahoo adj) + store BTC, doc lap code vector."""
    raw = {}
    for t in CORE:
        r = json.load(open(RAW + "yahoo_%s.json" % t))["chart"]["result"][0]
        rows = []
        for ts, a in zip(r["timestamp"], r["indicators"]["adjclose"][0]["adjclose"]):
            if a is not None:
                rows.append((pd.Timestamp(ts * 1000, unit="ms").normalize(), a))
        raw[t] = rows
    idx = D.index[(D.index >= "2022-01-01") & (D.index < "2026-07-01")]
    pick = sorted(rng.choice(len(idx), 10, replace=False))
    out, ok = [], True
    for k in pick:
        dd = idx[k]
        vals = {}
        for t in CORE:
            prev = [(d, a) for d, a in raw[t] if d < dd]  # phien truoc ngay quyet dinh (UTC)
            vals[t] = prev[-1][1] / prev[-21][1] - 1
            last_sess = prev[-1][0]
        b0 = btc.get(dd - pd.Timedelta(days=1))
        b7 = btc.get(dd - pd.Timedelta(days=8))
        s1 = b0 / b7 - 1
        s = dict(S1v=s1, S2v=vals["QQQ"], S3v=vals["QQQ"] - vals["XLP"], S4v=max(vals["GLD"], vals["UUP"]))
        st = dict(S1=1 if s1 >= .04 else (-1 if s1 <= -.04 else 0), S2=1 if s["S2v"] >= .03 else (-1 if s["S2v"] <= -.03 else 0),
                  S3=1 if s["S3v"] >= .02 else (-1 if s["S3v"] <= -.02 else 0), S4=-1 if s["S4v"] >= .03 else (1 if s["S4v"] <= 0 else 0))
        b = sum(1 for v in st.values() if v == 1)
        d_ = sum(1 for v in st.values() if v == -1)
        v4 = 1 if b >= d_ + 2 else (-1 if d_ >= b + 2 else 0)
        b3 = sum(1 for kk in ("S2", "S3", "S4") if st[kk] == 1)
        d3 = sum(1 for kk in ("S2", "S3", "S4") if st[kk] == -1)
        v3 = 1 if b3 >= d3 + 2 else (-1 if d3 >= b3 + 2 else 0)
        row = D.loc[dd]
        match = all(abs(s[c] - row[c]) < 1e-9 for c in s) and all(st[c] == row[c] for c in st) and v4 == row.V4 and v3 == row.V3
        match = match and (pd.Timestamp(row.sess) == last_sess) and last_sess < dd
        ok &= bool(match)
        out.append(dict(dd=str(dd.date()), sess=str(last_sess.date()), btc_day=str((dd - pd.Timedelta(days=1)).date()),
                        **{c: round(float(v), 5) for c, v in s.items()}, **st, V4=v4, V3=v3, match=bool(match)))
    return out, ok


def data():
    os.makedirs(OUT, exist_ok=True)
    rep = dict(src={}, cmp={}, flags=[])
    Y, NQ = {}, {}
    for t in CORE + ETF:
        if not os.path.exists(RAW + "yahoo_%s.json" % t):
            rep["flags"].append("THIEU_YAHOO_%s" % t)
            continue
        y, divs, spl = load_yahoo(t)
        Y[t] = y
        info = dict(yahoo_n=len(y), first=str(y.index.min().date()), last=str(y.index.max().date()), n_div=len(divs), n_split=spl)
        if os.path.exists(RAW + "nasdaq_%s.json" % t):
            n = load_nasdaq(t)
            NQ[t] = n
            info.update(nasdaq_n=len(n), nasdaq_first=str(n.index.min().date()), nasdaq_last=str(n.index.max().date()))
            com = y.index.intersection(n.index)
            info["common"] = len(com)
            info["only_yahoo"] = int(len(y.index.difference(n.index)))
            info["only_nasdaq"] = int(len(n.index.difference(y.index)))
            # cung co so: gia dong CHUA dieu chinh co tuc (Yahoo close vs Nasdaq close)
            yc, nc = y.close.reindex(com), n.close.reindex(com)
            ry, rn = yc / yc.shift(20) - 1, nc / nc.shift(20) - 1
            dif = (100 * (ry - rn)).abs().dropna()
            info["r20_raw_n"] = len(dif)
            info["r20_raw_frac_le_0p5pp"] = round(float((dif <= 0.5).mean()), 5)
            info["r20_raw_maxdiff_pp"] = round(float(dif.max()), 4)
            info["close_rel_maxdiff"] = round(float((yc / nc - 1).abs().max()), 6)
            # adj Yahoo vs Nasdaq tho (anh huong co tuc, mo ta)
            ya = y.adj.reindex(com)
            ra = ya / ya.shift(20) - 1
            dA = (100 * (ra - rn)).abs().dropna()
            info["r20_adjY_vs_rawN_frac_le_0p5pp"] = round(float((dA <= 0.5).mean()), 5)
            vv = (y.vol.reindex(com) / n.vol.reindex(com) - 1).abs().dropna()
            info["vol_rel_diff_median"] = round(float(vv.median()), 4)
            info["vol_rel_diff_frac_le_5pct"] = round(float((vv <= 0.05).mean()), 4)
            if info["r20_raw_frac_le_0p5pp"] < 0.99:
                rep["flags"].append("LECH_2NGUON_%s" % t)
        else:
            rep["flags"].append("MOT_NGUON_%s" % t)
        rep["src"][t] = info
    for t in CORE:
        if t not in Y:
            log.error("THIEU du lieu bat buoc %s -> DUNG", t)
            jdump(rep, "data.json")
            sys.exit(2)
    btc = btc_daily()
    D, S = build_signals(Y, btc)
    # sensitivity: tin hieu tu Nasdaq tho (khong dieu chinh) cho QQQ/XLP/GLD/UUP
    if all(t in NQ for t in CORE):
        YN = {t: NQ[t].assign(adj=NQ[t].close) for t in CORE}
        DN, _ = build_signals(YN, btc)
        rng_ = (D.index >= "2022-01-01") & (D.index < "2026-07-01")
        rep["state_agree_nasdaq_raw"] = {c: round(float((D[c][rng_] == DN[c][rng_]).mean()), 4) for c in ("S2", "S3", "S4", "V4", "V3")}
    # causal: phien dung < ngay quyet dinh; btc_day = dd-1
    sess = pd.to_datetime(D.sess)
    rep["causal_sess_lt_dd"] = bool((sess.dropna() < D.index[sess.notna()]).all())
    rep["causal_btcday"] = bool(((D.index - D.btc_day) == pd.Timedelta(days=1)).all())
    hc, hok = hand_check(D, NQ, btc, np.random.default_rng(RNG))
    rep["hand_check"] = hc
    rep["hand_check_ok"] = bool(hok)
    rng_ = (D.index >= "2022-01-01") & (D.index < "2026-07-01")
    rep["nan_days_2022_2026H1"] = {c: int(D[c][rng_].isna().sum()) for c in TESTS}
    rep["btc_days"] = len(btc)
    rep["btc_info"] = BTCINFO
    rep["E_first_valid_dd"] = str(D.index[(D.E_nval > 0).to_numpy()].min().date())
    D.to_parquet(OUT + "sig_daily.parquet")
    S.to_parquet(OUT + "sig_sess.parquet")
    jdump(rep, "data.json")
    log.info("DATA %s", json.dumps({k: v for k, v in rep.items() if k != "hand_check"}, default=str)[:3000])
    if not hok or not rep["causal_sess_lt_dd"] or not rep["causal_btcday"]:
        log.error("KIEM CAUSAL/TAY THAT BAI")
        sys.exit(3)


# ---------------------------------------------------------------- legs
def legs():
    L = IB.load_legs()
    u = np.unique(L.M.to_numpy())
    cid = np.cumsum(np.r_[True, np.diff(u) > 60 * M1])
    L["clu"] = cid[np.searchsorted(u, L.M.to_numpy())]
    first = L.groupby("clu").M.min()
    L["Mf"] = L.clu.map(first)
    L["cyr"] = pd.to_datetime(L.Mf.to_numpy() + TZ, unit="ms").year
    L["dd"] = pd.to_datetime((L.Mf.to_numpy() // DAY) * DAY, unit="ms")  # ngay quyet dinh UTC cua phut dau cum
    # khoi thang theo +07 (nhat quan nam +07 cua IND_COMBO)
    ft = pd.to_datetime(L.Mf.to_numpy() + TZ, unit="ms")
    L["mon"] = ft.year * 100 + ft.month
    ref = {"per": {"E": 10256, "C": 11298, "H": 2275}, "clu": {"E": 117, "C": 113, "H": 29}}
    got = {"per": L.per.value_counts().to_dict(), "clu": {p: int(L[L.per == p].clu.nunique()) for p in "ECH"}}
    ok = all(got["per"][p] == ref["per"][p] and got["clu"][p] == ref["clu"][p] for p in "ECH")
    X = pd.read_parquet("/home/ubuntu/claude_master/ind1114/legs_x.parquet", columns=["seed", "sym", "M", "y", "clu"])
    same = len(X) == len(L) and np.array_equal(X.M.to_numpy(), L.M.to_numpy()) and np.allclose(X.y.to_numpy(), L.y.to_numpy(), equal_nan=True) \
        and np.array_equal(X.clu.to_numpy(), L.clu.to_numpy())
    log.info("legs %s clusters %s khop IND_COMBO %s, trung legs_x.parquet %s", got["per"], got["clu"], ok, same)
    if not ok:
        log.error("SO LEG/CUM KHONG KHOP IND_COMBO -> DUNG")
        sys.exit(4)
    D = pd.read_parquet(OUT + "sig_daily.parquet")
    for c in TESTS + ["E"]:
        L[c] = D[c].reindex(L.dd).to_numpy()
    return L, D, dict(got=got, match_ind_combo=ok, match_legs_x=bool(same))


def month_boot(mon_idx, nm):
    rng = np.random.default_rng(RNG)
    return np.stack([np.bincount(rng.integers(0, nm, nm), minlength=nm) for _ in range(NB)]).astype(np.float64)


def m1_stat(df, mask, Wm, months):
    """m1 = mean y(D) - mean y(N), CI90 bootstrap khoi thang."""
    mi = np.searchsorted(months, df.mon.to_numpy())
    y = df.y.to_numpy()
    nm = len(months)
    sD, nD = np.bincount(mi[mask], y[mask], nm), np.bincount(mi[mask], minlength=nm).astype(float)
    sN, nN = np.bincount(mi[~mask], y[~mask], nm), np.bincount(mi[~mask], minlength=nm).astype(float)
    if nD.sum() == 0 or nN.sum() == 0:
        return dict(m1=np.nan, ci90=[np.nan, np.nan], se=np.nan)
    pt = sD.sum() / nD.sum() - sN.sum() / nN.sum()
    with np.errstate(all="ignore"):
        bs = (Wm @ sD) / (Wm @ nD) - (Wm @ sN) / (Wm @ nN)
    lo, hi = np.nanpercentile(bs, [5, 95])
    return dict(m1=round(float(pt), 4), ci90=[round(float(lo), 4), round(float(hi), 4)], se=round(float(np.nanstd(bs)), 4),
                p1=float(norm.cdf(pt / np.nanstd(bs))) if np.nanstd(bs) > 0 else np.nan, nan_draws=int(np.isnan(bs).sum()))


def episodes(D, col, val, clu_days, lo, hi):
    """so chuoi ngay lien tiep co trang thai val (trong [lo,hi)) chua >= 1 ngay co cum; tra (so, list (start,end))."""
    s = D[col]
    s = s[(s.index >= lo) & (s.index < hi)]
    on = (s == val).to_numpy()
    eps = []
    i = 0
    idx = s.index
    while i < len(on):
        if on[i]:
            j = i
            while j + 1 < len(on) and on[j + 1]:
                j += 1
            if any(idx[i] <= d <= idx[j] for d in clu_days):
                eps.append((idx[i], idx[j]))
            i = j + 1
        else:
            i += 1
    return eps


def eval_test(L, D, per, col, val, with_y=True):
    df = L[L.per == per].reset_index(drop=True)
    months = np.unique(df.mon.to_numpy())
    Wm = month_boot(None, len(months))
    mask = (df[col].to_numpy() == val)
    cl = df.groupby("clu").agg(dd=("dd", "first"), st=(col, "first"), yr=("cyr", "first"))
    lo = cl.dd.min() - pd.Timedelta(days=40)
    hi = cl.dd.max() + pd.Timedelta(days=40)
    eps = episodes(D, col, val, set(cl.dd[cl.st == val]), lo, hi)
    r = dict(n_leg=len(df), n_clu=len(cl), n_months=len(months), pct_leg=round(100 * float(mask.mean()), 2),
             pct_clu=round(100 * float((cl.st == val).mean()), 2), n_ep=len(eps), nan_leg=int(np.isnan(df[col].to_numpy()).sum()))
    eyr = {}
    for y in sorted(cl.yr.unique()):
        dys = set(cl.dd[(cl.st == val) & (cl.yr == y)])
        eyr[str(y)] = sum(1 for a, b in eps if any(a <= d <= b for d in dys))
    r["n_ep_yr"] = eyr
    r["pct_leg_yr"] = {str(y): round(100 * float(mask[df.yr.to_numpy() == y].mean()), 2) for y in sorted(df.yr.unique())}
    if with_y:
        r.update(m1_stat(df, mask, Wm, months))
        r["m2"] = round(float(df.pnl.to_numpy()[mask].sum()) / 8.0, 1)
        r["m2_yr"] = {str(y): round(float(df.pnl.to_numpy()[mask & (df.yr.to_numpy() == y)].sum()) / 8.0, 1) for y in sorted(df.yr.unique())}
        r["sum_check"] = abs(sum(r["m2_yr"].values()) - r["m2"]) < 1.0
        yrs = {}
        for y in sorted(df.yr.unique()):
            dy = df[df.yr == y].reset_index(drop=True)
            my = dy[col].to_numpy() == val
            yrs[str(y)] = dict(mean_D=round(float(dy.y[my].mean()), 3) if my.any() else None, mean_N=round(float(dy.y[~my].mean()), 3),
                               n_D=int(my.sum()), m1=round(float(dy.y[my].mean() - dy.y[~my].mean()), 3) if my.any() else None)
        r["yr"] = yrs
        s42 = df[df.seed == 42]
        m42 = s42[col].to_numpy() == val
        r["seed42_m1"] = round(float(s42.y[m42].mean() - s42.y[~m42].mean()), 3) if m42.any() else None
    return r


# ---------------------------------------------------------------- track G
def g_load(D):
    Y = pd.read_parquet("/home/ubuntu/claude_master/res1109/r5_quality/out/r5q_y.parquet", columns=["ts", "y72"])
    rows = []
    for s in G_SEEDS:
        z = np.load("/home/ubuntu/claude_master/ind1114/g2_%s.npz" % s)
        rows.append(pd.DataFrame(dict(seed=s, ts=z["ts"], pas=z["pas"], mrq=z["mrq"])))
    G = pd.concat(rows, ignore_index=True).merge(Y, on="ts", how="left")
    G["y72"] *= 100.0
    dd = pd.to_datetime((G.ts.to_numpy() // DAY) * DAY, unit="ms")
    for c in ("V4", "V3"):
        G[c] = D[c].reindex(dd).to_numpy()
    G["yr"] = np.select([G.ts < YB[y + 1] for y in (2022, 2023, 2024, 2025)], [2022, 2023, 2024, 2025], 0)
    G["per"] = np.where(G.ts < YB[2024], "E", "C")
    ft = pd.to_datetime(G.ts.to_numpy() + TZ, unit="ms")
    G["mon"] = ft.year * 100 + ft.month
    return G


def declust(df):
    out = []
    for s, g in df.sort_values(["seed", "ts"]).groupby("seed"):
        t = g.ts.to_numpy()
        out.append(g[np.r_[True, np.diff(t) > 60 * M1]])
    return pd.concat(out) if out else df.iloc[:0]


def wdiff(A, B, months, Wm):
    nm = len(months)
    ia, ib = np.searchsorted(months, A.mon.to_numpy()), np.searchsorted(months, B.mon.to_numpy())
    sA, nA = np.bincount(ia, A.y72.to_numpy(), nm), np.bincount(ia, minlength=nm).astype(float)
    sB, nB = np.bincount(ib, B.y72.to_numpy(), nm), np.bincount(ib, minlength=nm).astype(float)
    pt = sA.sum() / nA.sum() - sB.sum() / nB.sum()
    with np.errstate(all="ignore"):
        bs = (Wm @ sA) / (Wm @ nA) - (Wm @ sB) / (Wm @ nB)
    lo, hi = np.nanpercentile(bs, [5, 95])
    return float(pt), [float(lo), float(hi)], float(np.nanstd(bs))


def g_eval(G, per, years=None):
    X = G[(G.per == per) & np.isfinite(G.y72)]
    if years is not None:
        X = X[X.yr.isin(years)]
    months = np.unique(X.mon.to_numpy())
    Wm = month_boot(None, len(months))
    P = declust(X[X.pas])
    res = {}
    for c in ("V4", "V3"):
        r = {}
        st = X[c].to_numpy()
        for b in (0.85, 0.70):
            nm = (~X.pas.to_numpy()) & (X.mrq.to_numpy() >= b) & (X.mrq.to_numpy() < 1.0) & (st == 1)
            A = declust(X[nm])
            if len(A) < 5 or len(P) < 5:
                r["relax_%.2f" % b] = dict(n_nm=len(A), note="qua it")
                continue
            d, ci, se = wdiff(A, P, months, Wm)
            r["relax_%.2f" % b] = dict(delta=round(d, 3), ci90=[round(ci[0], 3), round(ci[1], 3)], se=round(se, 3),
                                       y_nm_fav=round(float(A.y72.mean()), 3), y_pass=round(float(P.y72.mean()), 3), n_nm=len(A), n_pass=len(P),
                                       p_ni=float(norm.sf((d + 1.0) / se)) if se > 0 else np.nan)
        pa = X.pas.to_numpy()
        A, B = declust(X[pa & (st == -1)]), declust(X[pa & (st != -1)])
        if len(A) >= 5 and len(B) >= 5:
            d, ci, se = wdiff(A, B, months, Wm)
            r["veto"] = dict(delta=round(d, 3), ci90=[round(ci[0], 3), round(ci[1], 3)], se=round(se, 3), n_adv=len(A), n_rest=len(B),
                             p=float(norm.cdf(d / se)) if se > 0 else np.nan)
        else:
            r["veto"] = dict(n_adv=len(A), note="qua it")
        res[c] = r
    return res


def g_pick(gE):
    cand = []
    for c, r in gE.items():
        a, b = r.get("relax_0.85", {}), r.get("relax_0.70", {})
        if "delta" in a and "delta" in b and all(x["delta"] >= 0 and x["ci90"][0] > -1 and x["y_nm_fav"] > 0 for x in (a, b)):
            cand.append(("relax", c, min(a["delta"], b["delta"])))
        v = r.get("veto", {})
        if "delta" in v and v["delta"] < 0 and v["ci90"][1] < 0:
            cand.append(("veto", c, abs(v["delta"])))
    cand.sort(key=lambda x: -x[2])
    return cand[:1]


# ---------------------------------------------------------------- explore / confirm
def explore():
    L, D, chk = legs()
    rep = dict(legs=chk, tests={}, freq={})
    # tan suat trang thai theo nam (X-only, theo ngay quyet dinh, 2022..2026H1) va theo leg
    rng_ = (D.index >= "2022-01-01") & (D.index < "2026-07-01")
    Dd = D[rng_]
    for c in TESTS + ["E"]:
        rep["freq"][c] = {str(y): dict(def_pct_days=round(100 * float((Dd[c][Dd.index.year == y] == -1).mean()), 1),
                                       bull_pct_days=round(100 * float((Dd[c][Dd.index.year == y] == 1).mean()), 1),
                                       def_pct_legs=round(100 * float((L[c][L.yr == y] == -1).mean()), 1))
                          for y in (2022, 2023, 2024, 2025, 2026)}
    r1 = {c: eval_test(L, D, "E", c, -1.0) for c in TESTS}
    r2 = {c: eval_test(L, D, "E", c, -1.0) for c in TESTS}
    rep["boot_reproducible"] = json.dumps(r1, sort_keys=True, default=str) == json.dumps(r2, sort_keys=True, default=str)
    rep["tests"]["E"] = r1
    rep["tests"]["C_xonly"] = {c: eval_test(L, D, "C", c, -1.0, with_y=False) for c in TESTS}
    # MDE80 (se khoi EXPLORE * sqrt(nB_E/nB_C))
    z = norm.ppf(0.90) + norm.ppf(0.80)
    mde = {}
    for c in TESTS:
        se = r1[c].get("se", np.nan)
        nbE, nbC = r1[c]["n_months"], rep["tests"]["C_xonly"][c]["n_months"]
        seC = se * np.sqrt(nbE / nbC) if se == se else np.nan
        mde[c] = dict(se_C=round(float(seC), 4), mde80=round(float(z * seC), 3),
                      mde80_holm2=round(float((norm.ppf(1 - 0.05) + norm.ppf(0.80)) * seC), 3))
    rep["mde80"] = mde
    cand = []
    for c in TESTS:
        r = r1[c]
        ok = (r["m1"] == r["m1"]) and r["m1"] < 0 and r["ci90"][1] < 0 and r["m2"] <= 0 and 5 <= r["pct_leg"] <= 50 and r["n_ep"] >= 4
        r["candidate_rule"] = bool(ok)
        if ok:
            cand.append((r["m2"], c))
    cand.sort()
    rep["candidates_S"] = [c for _, c in cand[:2]]
    G = g_load(D)
    gE1, gE2 = g_eval(G, "E"), g_eval(G, "E")
    rep["G_boot_reproducible"] = json.dumps(gE1, sort_keys=True, default=str) == json.dumps(gE2, sort_keys=True, default=str)
    rep["G_E"] = gE1
    rep["G_n"] = {p: dict(rows=int((G.per == p).sum()), pas=int((G.pas & (G.per == p)).sum()), y72_nan=int(G.y72[G.per == p].isna().sum()),
                          v4_nan=int(G.V4[G.per == p].isna().sum())) for p in "EC"}
    rep["candidates_G"] = g_pick(gE1)
    jdump(rep, "selection.json")
    log.info("EXPLORE xong: S %s G %s, boot tai lap %s/%s", rep["candidates_S"], rep["candidates_G"], rep["boot_reproducible"], rep["G_boot_reproducible"])


def holm(ps, a=0.10, m=None):
    m = m or len(ps)
    o = np.argsort(ps)
    rej = np.zeros(len(ps), bool)
    for k, i in enumerate(o):
        if ps[i] <= a / (m - k):
            rej[i] = True
        else:
            break
    return rej


def confirm():
    sel = json.load(open(OUT + "selection.json"))
    L, D, chk = legs()
    rep = dict(candidates_S=sel["candidates_S"], candidates_G=sel["candidates_G"], S={}, G={}, desc={})
    cs = sel["candidates_S"]
    for c in cs:
        rep["S"][c] = eval_test(L, D, "C", c, -1.0)
    if cs:
        rej = holm(np.array([rep["S"][c]["p1"] for c in cs]), 0.10)
        for c, rj in zip(cs, rej):
            r = rep["S"][c]
            eyr = r["n_ep_yr"]
            yr_ok = all(r["m2_yr"][y] <= 0 for y in ("2024", "2025") if eyr.get(y, 0) >= 3)
            r["crit"] = dict(m1_neg=r["m1"] < 0, ci_excl0=r["ci90"][1] < 0, holm=bool(rj), m2_pooled=r["m2"] <= 0, m2_years=yr_ok,
                             ep4=r["n_ep"] >= 4, pct=5 <= r["pct_leg"] <= 50)
            r["DAT"] = bool(all(r["crit"].values()))
    # track G CONFIRM
    G = g_load(D)
    for kind, c, _ in sel["candidates_G"]:
        a = g_eval(G, "C")[c]
        yrs = {str(y): g_eval(G, "C", [y])[c] for y in (2024, 2025)}
        if kind == "relax":
            ps = [a[b].get("p_ni", 1.0) for b in ("relax_0.85", "relax_0.70")]
            rej = holm(np.array(ps + [1.0, 1.0]), 0.10, m=4)[:2]
            cond = all("delta" in a[b] and a[b]["delta"] >= 0 and a[b]["ci90"][0] > -1 and a[b]["y_nm_fav"] > 0 for b in ("relax_0.85", "relax_0.70"))
            yok = all("delta" in yrs[y][b] and yrs[y][b]["delta"] >= 0 for y in yrs for b in ("relax_0.85", "relax_0.70"))
            dat = bool(rej.all() and cond and yok)
        else:
            v = a["veto"]
            rej = holm(np.array([v.get("p", 1.0), 1.0, 1.0, 1.0]), 0.10, m=4)[:1]
            cond = "delta" in v and v["delta"] < 0 and v["ci90"][1] < 0
            yok = all("delta" in yrs[y]["veto"] and yrs[y]["veto"]["delta"] < 0 for y in yrs)
            dat = bool(rej.all() and cond and yok)
        rep["G"]["%s_%s" % (kind, c)] = dict(C=a, yrs=yrs, holm=[bool(x) for x in rej], cond=bool(cond), yrs_ok=bool(yok), DAT=dat)
    # mo ta: 6 kiem defensive o C (khong dung quyet dinh ngoai ung vien) + HO; chieu bullish; E
    rep["desc"]["def_C_all6"] = {c: eval_test(L, D, "C", c, -1.0) for c in TESTS}
    rep["desc"]["def_H"] = {c: eval_test(L, D, "H", c, -1.0) for c in TESTS}
    rep["desc"]["bull"] = {p: {c: eval_test(L, D, p, c, 1.0) for c in TESTS} for p in "ECH"}
    rep["desc"]["E_out"] = {p: eval_test(L, D, p, "E", -1.0) for p in "CH"}
    rep["desc"]["E_in"] = {p: eval_test(L, D, p, "E", 1.0) for p in "CH"}
    rep["desc"]["G_C_all"] = g_eval(G, "C")
    jdump(rep, "confirm.json")
    log.info("CONFIRM xong: %s", {c: rep["S"][c].get("DAT") for c in cs})


if __name__ == "__main__":
    {"data": data, "explore": explore, "confirm": confirm}[sys.argv[1]]()
