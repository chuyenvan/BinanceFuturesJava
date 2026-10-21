#!/usr/bin/env python3
"""TS_MKT_EXT DEEP - phan tich MO TA tren ket qua da co (P0 vs X14, DEV 8 seed + HO W9 8 seed).
KHONG doi luat, KHONG tune; 2020 khong dung. Dau vao: printDone (kaggle_sim/out), eq phut tu deep_mtm_{dev,ho}.py
(gvz_mtm / ecm_mtm_h, da tu kiem = mtm_vision.json / ho_mtm.json), ALT_EW index (edge_attr/index.npz + ew_2026.npz),
gia Vision 1m (vz_e1/raw, gvz/k2021, ecm_px). Out: deep.json + deep_tables.md (thu muc nay).
"""
import hashlib
import json
import logging
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "/home/ubuntu/claude_master/gvz")
import gvz_mtm as MT  # noqa: E402,F401  (PHAI truoc R: patch nguon gia Vision)
import reset_rule_score as R  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("deep")
HERE = os.path.dirname(os.path.abspath(__file__))
C = "/home/ubuntu/claude_master/tsx/deep_cache"
KS = "/home/ubuntu/kaggle_sim/out/"
TSX = "/home/ubuntu/claude_master/tsx"
DEVS = ["A1", "S7", "S13", "S21", "S99", "S123", "S777", "S2024"]
HOS = [42, 7, 13, 21, 99, 123, 777, 2024]
H7 = pd.Timedelta(hours=7)
FEE_IN = 0.001116  # pnl = q*(tp-entry) - FEE_IN*q*entry - funding (fit tren printDone, resid max 2e-4 USD)
TS_MIN = 168 * 60
EXT_MAX_MIN = 504 * 60
CAP0 = float(R.CAP0)
DAY0 = pd.Timestamp(R.DAY0)
T0HO = pd.Timestamp("2026-01-01 00:00")  # local +07, index 0 cua eq_ho
PER_DEV = [("2021H2", "2021-07-01", "2022-01-01"), ("2022", "2022-01-01", "2023-01-01"), ("2023", "2023-01-01", "2024-01-01"),
           ("2024", "2024-01-01", "2025-01-01"), ("2025", "2025-01-01", "2026-01-01"), ("DEV", "2021-07-01", "2026-01-01")]
PER_HO = [("2026W9", "2026-01-01", "2026-10-01")]
# nhan su kien theo NGAY BAT DAU dot (goi y mo ta, chua kiem nguon; 2026 khong xac minh)
LABEL = [("2021-09-01", "2021-09-30", "TQ cấm crypto 24/09/2021, Evergrande (sau sập 07/09)"),
         ("2021-12-01", "2021-12-31", "dư chấn flash crash 04/12/2021"),
         ("2022-01-15", "2022-02-10", "bán tháo 01/2022 (Fed hawkish, đáy 24/01)"),
         ("2022-04-25", "2022-06-10", "LUNA/UST 05/2022"), ("2022-06-11", "2022-06-30", "Celsius/3AC 06/2022"),
         ("2022-11-01", "2022-12-31", "FTX 11/2022"), ("2023-03-01", "2023-03-31", "SVB/USDC depeg 03/2023"),
         ("2024-04-10", "2024-05-15", "alt sập 04/2024 (Iran–Israel 13/04, halving 20/04)"),
         ("2024-06-15", "2024-07-31", "alt bleed 06/2024 + Mt.Gox/Đức bán 07/2024"),
         ("2024-08-01", "2024-08-31", "yen carry unwind 05/08/2024"),
         ("2024-12-15", "2025-01-10", "điều chỉnh sau FOMC 18/12/2024"),
         ("2025-01-21", "2025-02-28", "DeepSeek 27/01, thuế quan 03/02, Bybit hack 21/02/2025"),
         ("2025-03-01", "2025-03-31", "bán tháo 03/2025 (thuế quan)"),
         ("2025-04-01", "2025-04-30", "thuế quan 'Liberation Day' 02–09/04/2025"),
         ("2025-06-15", "2025-06-30", "Mỹ không kích Iran 21–22/06/2025"),
         ("2025-10-01", "2025-10-25", "sập thanh lý 10–11/10/2025 + dư chấn"),
         ("2025-10-26", "2025-12-31", "bán tháo 11/2025"), ("2026-01-01", "2026-12-31", "(2026: chưa xác minh)")]


def lab(ts):
    for a, b, s in LABEL:
        if pd.Timestamp(a) <= ts <= pd.Timestamp(b):
            return s
    return "(không rõ)"


# ------------------------------------------------------------------ ALT_EW + co
def ew_dd():
    a = np.load("/home/ubuntu/claude_master/edge_attr/index.npz")
    b = np.load(TSX + "/ho/ew_out/ew_2026.npz")
    ta, ra, tb, rb = a["ew_ts"].astype(np.int64), a["ew_r"], b["ew_ts"].astype(np.int64), b["ew_r"]
    hi = int(pd.Timestamp("2026-01-01").value // 10 ** 6)
    ts = np.concatenate([ta[ta < hi], tb[tb >= hi]])
    r = np.concatenate([ra[ta < hi], rb[tb >= hi]])
    L = pd.Series(np.cumsum(r.astype(np.float64)), index=pd.to_datetime(ts, unit="ms"))
    eod = L.groupby(L.index.floor("D")).last()
    return np.exp(eod - eod.rolling(31, min_periods=1).max()) - 1  # index = ngay UTC d (co ap cho d+1)


def ranges_of(days):
    rng, st, pv = [], None, None
    for d in days:
        if st is None:
            st = pv = d
        elif d == pv + pd.Timedelta(days=1):
            pv = d
        else:
            rng.append((st, pv))
            st = pv = d
    if st is not None:
        rng.append((st, pv))
    return rng


def rstr(rng):
    return ",".join("%s-%s" % (x.strftime("%Y%m%d"), y.strftime("%Y%m%d")) for x, y in rng)


def flags(dd):
    fd = sorted(dd[dd <= -0.30].index + pd.Timedelta(days=1))
    dev = [d for d in fd if pd.Timestamp("2021-07-01") <= d <= pd.Timestamp("2025-12-31")]
    ho = [d for d in fd if pd.Timestamp("2026-01-01") <= d <= pd.Timestamp("2026-09-30")]
    rd, rh = ranges_of(dev), ranges_of(ho)
    pre = json.load(open(TSX + "/flags.json"))
    hof = json.load(open(TSX + "/ho/ho_flags.json"))
    chk = dict(dev_days=len(dev), dev_ranges=len(rd), dev_sha_ok=hashlib.sha256(rstr(rd).encode()).hexdigest() == pre["sha256"],
               dev_str_ok=rstr(rd) == pre["ranges"], ho_days=len(ho), ho_ranges=len(rh), ho_str_ok=rstr(rh) == hof["ranges"])
    log.info("FLAGS %s", chk)
    assert chk["dev_str_ok"] and chk["ho_str_ok"], "co tinh lai KHONG khop prereg"
    return set(dev), set(ho), rd, rh, chk


# ------------------------------------------------------------------ lenh / cum
def load(tag):
    d = pd.read_csv(KS + tag + "/storage/printDone.csv", index_col=False)
    d.columns = [c.strip() for c in d.columns]
    for c in ("quantity", "entry", "margin", "pnl", "profit", "tp", "funding"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d = d.dropna(subset=["pnl", "margin"]).copy()
    d["sym"] = d["sym"].astype(str).str.strip()
    d["status"] = d["status"].astype(str).str.strip()
    d["ts"] = pd.to_datetime(d["start"], format="%Y%m%d %H:%M")
    d["te"] = pd.to_datetime(d["end"], format="%Y%m%d %H:%M")
    d["notional"] = d["quantity"] * d["entry"]
    return d.sort_values(["ts", "sym"], kind="mergesort").reset_index(drop=True)


def clusters(d):
    """cum = (sym, end): cac leg DCA dong cung phut; anchor = leg dau (clusterFirstLegTime)."""
    g = d.groupby(["sym", "te"], sort=False)
    c = g.agg(t0=("ts", "min"), st=("status", "first"), nst=("status", "nunique"), n=("sym", "size"),
              pnl=("pnl", "sum"), notional=("notional", "sum")).reset_index()
    assert (c["nst"] == 1).all()
    c["age_min"] = (c["te"] - c["t0"]) // pd.Timedelta(minutes=1)
    c["mark_u"] = c["t0"] - H7 + pd.Timedelta(minutes=TS_MIN + 1)  # tick dau tien tuoi > 168h (UTC)
    c["mark_day"] = c["mark_u"].dt.normalize()
    return c


def px_batch(q, ho):
    """gia cat gia dinh tai phut UTC q.tu cho q.sym: DEV = min(open, close) nen 1m Vision (= quy uoc cat time-stop
    trong sim); HO = min(close[m-1], close[m]) (cache ecm_px chi co close). Tra np.array cung thu tu q."""
    q = q.reset_index(drop=True).copy()
    q["ms"] = (q["tu"].astype("int64") // 10 ** 6).astype(np.int64)
    q["s"] = q["sym"] + "USDT"
    q["ym"] = q["tu"].dt.strftime("%Y-%m")
    out = np.full(len(q), np.nan)
    for ym, g in q.groupby("ym"):
        if ho:
            for s, gg in g.groupby("s"):
                fn = "/home/ubuntu/claude_master/1013/ecm/ecm_px/%s_%s.npz" % (s, ym)
                if not os.path.exists(fn):
                    continue
                z = np.load(fn)
                ot, cc = z["ot"], z["c"]
                i = np.searchsorted(ot, gg["ms"].to_numpy())
                for j, ii, m in zip(gg.index, i, gg["ms"].to_numpy()):
                    if ii < len(ot) and ot[ii] == m:
                        out[j] = min(cc[ii], cc[ii - 1]) if ii > 0 else cc[ii]
            continue
        x = pd.read_parquet(MT.kp(ym), columns=["ts", "sym", "open", "close"])
        x["sym"] = x["sym"].astype(str)
        x = x[x["sym"].isin(set(g["s"]))].drop_duplicates(["sym", "ts"], keep="last")
        x["px"] = np.minimum(x["open"], x["close"])
        m = g.reset_index().merge(x[["sym", "ts", "px"]], left_on=["s", "ms"], right_on=["sym", "ts"], how="left")
        out[m["index"].to_numpy()] = m["px"].to_numpy()
    return out


# ------------------------------------------------------------------ equity phut
def eq_dev():
    z = np.load(C + "/eq_dev.npz")
    out = {}
    for k in z.files:
        if k.endswith("__m0"):
            continue
        m0 = int(z[k + "__m0"][0])
        out[k] = (z[k].astype(np.float64), DAY0 + pd.Timedelta(minutes=m0))  # truc UTC
    return out


def eq_ho():
    z = np.load(C + "/eq_ho.npz")
    return {k: (z[k].astype(np.float64), T0HO) for k in z.files if not k.startswith("__")}  # truc local +07


def open_notional(d, n, base, utc):
    """notional mo theo phut tren truc eq (base = moc phut 0; utc=True -> truc UTC)."""
    sh = H7 if utc else pd.Timedelta(0)
    a = ((d["ts"] - sh - base) // pd.Timedelta(minutes=1)).to_numpy(np.int64)
    b = ((d["te"] - sh - base) // pd.Timedelta(minutes=1)).to_numpy(np.int64)
    a, b = np.clip(a, 0, n), np.clip(b, 0, n)
    x = np.zeros(n + 1)
    np.add.at(x, a, d["notional"].to_numpy(float))
    np.add.at(x, b, -d["notional"].to_numpy(float))
    return np.cumsum(x)[:n]


# ------------------------------------------------------------------ chi so ky
def ddx(e):
    pk = np.maximum.accumulate(e)
    x = e / pk - 1.0
    j = int(np.argmin(x))
    i = int(np.argmax(e[:j + 1]))
    return float(x[j] * 100), i, j


def period(run, a, b):
    """run: dict(d, c, eq, base, on). Giao dich theo ngay DONG (local +07); MTM tren truc cua eq (DEV UTC, HO +07)."""
    d, c, eq, base, on = run["d"], run["c"], run["eq"], run["base"], run["on"]
    A, B = pd.Timestamp(a), pd.Timestamp(b)
    L = d[(d["te"] >= A) & (d["te"] < B)]
    K = c[(c["te"] >= A) & (c["te"] < B)]
    bal0 = run["cap0"] + float(d.loc[d["te"] < A, "pnl"].sum())
    i0 = max(0, int((A - base) // pd.Timedelta(minutes=1)))
    i1 = min(len(eq), int((B - base) // pd.Timedelta(minutes=1)))
    e = eq[i0:i1]
    dd, ip, it = ddx(e)
    ed = e[1439::1440] if len(e) >= 1440 else e[-1:]
    ddd = ddx(np.concatenate([e[:1], ed]))[0]
    ndays = (i1 - i0) / 1440.0
    ret = e[-1] / e[0] - 1.0
    ann = (1 + ret) ** (365.25 / ndays) - 1
    mons = pd.date_range(base + pd.Timedelta(minutes=i0), base + pd.Timedelta(minutes=i1 - 1), freq="MS")
    edges = [i0] + [int((m - base) // pd.Timedelta(minutes=1)) for m in mons if (m - base) // pd.Timedelta(minutes=1) > i0] + [i1 - 1]
    mr = []
    for x0, x1 in zip(edges[:-1], edges[1:]):
        mr.append(((base + pd.Timedelta(minutes=x0)).strftime("%Y-%m"), float((eq[x1] / eq[x0] - 1) * 100)))
    wm = min(mr, key=lambda t: t[1])
    hh = K["age_min"].to_numpy() / 60.0
    ex = on[i0:i1:60] / e[::60]
    return dict(n_cl=int(len(K)), n_leg=int(len(L)), n_batch=int(K["t0"].nunique()),
                win=float(100 * (L["profit"] > 0).mean()) if len(L) else np.nan, pnl=float(L["pnl"].sum()),
                roi=float(100 * L["pnl"].sum() / bal0), dd=dd, dd_day=ddd,
                dd_peak=str(base + pd.Timedelta(minutes=i0 + ip))[:16], dd_trough=str(base + pd.Timedelta(minutes=i0 + it))[:16],
                ret_mtm=float(100 * ret), calmar=float(100 * ann / abs(dd)) if dd < 0 else np.nan,
                worst_m=wm[0], worst_m_pct=wm[1], hold_mean=float(hh.mean()) if len(hh) else np.nan,
                hold_p90=float(np.percentile(hh, 90)) if len(hh) else np.nan,
                n168=int((K["age_min"] >= TS_MIN).sum()),
                ncut=int(((K["st"] == "STOP_LOSS_DONE") & (K["age_min"] >= TS_MIN)).sum()),
                exp_mean=float(100 * ex.mean()), exp_max=float(100 * ex.max()))


# ------------------------------------------------------------------ cum duoc HOAN
def deferred(run, p0c, fl, rng, dd, ho):
    """cum X14 tuoi > 168h+1' co moc 168h roi vao ngay co (UTC); loai cum da arm truoc 168h (P0 cung sym+anchor giu
    > 168h ma KHONG bi cat SL). PnL@168h = pnl + q*(px168 - tp) + funding*(1 - frac thoi gian toi moc)."""
    d, c = run["d"], run["c"]
    cand = c[(c["age_min"] > TS_MIN + 1) & c["mark_day"].isin(fl)].copy()
    pm = p0c.set_index(["sym", "t0"])
    armed = []
    for s, t0 in zip(cand["sym"], cand["t0"]):
        k = (s, t0)
        if k in pm.index:
            r = pm.loc[k]
            r = r.iloc[0] if isinstance(r, pd.DataFrame) else r
            armed.append(bool(r["age_min"] > TS_MIN + 1 and r["st"] != "STOP_LOSS_DONE"))
        else:
            armed.append(False)
    cand["armed_pre"] = armed
    cand["p0_match"] = [(s, t) in pm.index for s, t in zip(cand["sym"], cand["t0"])]
    df = cand[~cand["armed_pre"]].copy().reset_index(drop=True)
    df["px168"] = px_batch(df[["sym"]].assign(tu=df["mark_u"]), ho)
    legs = d.merge(df[["sym", "te", "px168", "mark_u"]], on=["sym", "te"], how="inner")
    mk = legs["mark_u"] + H7
    frac = ((mk - legs["ts"]) / (legs["te"] - legs["ts"])).clip(0, 1)
    legs["pnl168"] = legs["pnl"] + legs["quantity"] * (legs["px168"] - legs["tp"]) + legs["funding"] * (1 - frac)
    p168 = legs.groupby(["sym", "te"])["pnl168"].sum()
    df["pnl168"] = [p168.get((s, t), np.nan) for s, t in zip(df["sym"], df["te"])]
    df["delta"] = df["pnl"] - df["pnl168"]
    df["extra_h"] = (df["age_min"] - TS_MIN) / 60.0
    teu = df["te"] - H7
    off = teu.dt.normalize()
    cat = np.where(df["st"] != "STOP_LOSS_DONE", "arm_trail",
                   np.where(df["age_min"] >= EXT_MAX_MIN, "cut_504h",
                            np.where((teu == off) & ~off.isin(fl), "cut_flag_off", "sl_other")))
    df["exit"] = cat
    starts = [r[0] for r in rng]
    df["ep"] = [next((i for i, (x, y) in enumerate(rng) if x <= m <= y), -1) for m in df["mark_day"]]
    # ngay sat nguong (co ON tu dd trong [-0.33, -0.30]) trong khoang hoan
    marg = set(dd[(dd >= -0.33) & (dd <= -0.30)].index + pd.Timedelta(days=1))
    df["marg_first"] = df["mark_day"].isin(marg)
    df["marg_any"] = [any(x in marg for x in pd.date_range(m, min(o, m + pd.Timedelta(days=14)), freq="D"))
                      for m, o in zip(df["mark_day"], off)]
    del starts
    return df, dict(cand=int(len(cand)), armed_pre=int(cand["armed_pre"].sum()), n=int(len(df)),
                    p0_match=int(df["p0_match"].sum()), px_nan=int(df["px168"].isna().sum()),
                    cut=int((df["st"] == "STOP_LOSS_DONE").sum()))


def px_check(run, ho):
    """kiem quy uoc gia: leg P0 thuoc cum bi cat time-stop dung 168h+1' -> px(moc) phai = tp cua leg."""
    c = run["c"]
    k = c[(c["st"] == "STOP_LOSS_DONE") & (c["age_min"] == TS_MIN + 1)]
    L = run["d"].merge(k[["sym", "te", "mark_u"]], on=["sym", "te"])
    px = px_batch(L[["sym"]].assign(tu=L["mark_u"]), ho)
    rel = np.abs(px / L["tp"].to_numpy() - 1)
    ok = rel[~np.isnan(rel)]
    return dict(n=int(len(L)), nan=int(np.isnan(rel).sum()), match_1e4=float((ok < 1e-4).mean()) if len(ok) else None,
                median_rel=float(np.median(ok)) if len(ok) else None, p95_rel=float(np.percentile(ok, 95)) if len(ok) else None)


# ------------------------------------------------------------------ tong hop
def mmm(v):
    v = np.asarray([x for x in v if x is not None and not (isinstance(x, float) and np.isnan(x))], float)
    return [float(np.median(v)), float(v.min()), float(v.max())] if len(v) else [np.nan] * 3


def mode(v):
    return pd.Series(list(v)).mode().iloc[0]


def events_of(rng, gap=14):
    """gop cac khoang co cach nhau <= gap ngay thanh 1 'su kien' (mo ta; gap = do dai gia han toi da 14 ngay)."""
    ev = []
    for i, (a, b) in enumerate(rng):
        if ev and (a - ev[-1]["end"]).days - 1 <= gap:
            ev[-1]["end"] = b
            ev[-1]["eps"].append(i)
        else:
            ev.append(dict(start=a, end=b, eps=[i]))
    return ev


def seg_delta(rp, rx, bounds):
    """dPnL thuc hien (X14 - P0) theo doan [bounds_k, bounds_k+1) tren gio dong UTC; tong = tong dPnL."""
    out = []
    for a, b in zip(bounds[:-1], bounds[1:]):
        f = lambda r: float(r["d"].loc[((r["d"]["te"] - H7) >= a) & ((r["d"]["te"] - H7) < b), "pnl"].sum())  # noqa: E731
        out.append(f(rx) - f(rp))
    return out


def win_stats(run, a, b, utc_axis):
    """DD MTM (reset dau cua so) + so cum/leg vao moi trong [a, b) UTC."""
    base, eq = run["base"], run["eq"]
    sh = pd.Timedelta(0) if utc_axis else -H7  # truc local: a_local = a_utc + 7h
    i0 = max(0, int((a - sh - base) // pd.Timedelta(minutes=1)))
    i1 = min(len(eq), int((b - sh - base) // pd.Timedelta(minutes=1)))
    dd = ddx(eq[i0:i1])[0] if i1 > i0 + 1 else np.nan
    c = run["c"]
    t0u = c["t0"] - H7
    nc = c[(t0u >= a) & (t0u < b)]
    du = run["d"]["ts"] - H7
    return dict(dd=dd, ret=float(100 * (eq[i1 - 1] / eq[i0] - 1)) if i1 > i0 else np.nan, new_cl=int(len(nc)),
                new_leg=int(((du >= a) & (du < b)).sum()), keys=set(zip(nc["sym"], nc["t0"])),
                pnl_new=dict(zip(zip(nc["sym"], nc["t0"]), nc["pnl"])))


def flag_exposure(run, fl, utc_axis, dfx=None):
    base, eq, on = run["base"], run["eq"], run["on"]
    idx = np.arange(0, len(eq), 60)
    t = base + pd.to_timedelta(idx, unit="m")
    tu = t if utc_axis else t - H7
    m = np.isin(tu.normalize().values, np.array(sorted(fl), dtype="datetime64[ns]"))
    ex = on[idx] / eq[idx]
    r = dict(exp_flag_mean=float(100 * ex[m].mean()) if m.any() else np.nan, exp_flag_max=float(100 * ex[m].max()) if m.any() else np.nan,
             exp_noflag_mean=float(100 * ex[~m].mean()), hours_flag=int(m.sum()))
    if dfx is not None and len(dfx):
        L = run["d"].merge(dfx[["sym", "te", "mark_u"]], on=["sym", "te"])
        sh = H7 if utc_axis else pd.Timedelta(0)
        a = ((L["mark_u"] + H7 - sh - base) // pd.Timedelta(minutes=1)).to_numpy(np.int64)
        b = ((L["te"] - sh - base) // pd.Timedelta(minutes=1)).to_numpy(np.int64)
        a, b = np.clip(a, 0, len(eq)), np.clip(b, 0, len(eq))
        x = np.zeros(len(eq) + 1)
        np.add.at(x, a, L["notional"].to_numpy(float))
        np.add.at(x, b, -L["notional"].to_numpy(float))
        lk = np.cumsum(x)[:len(eq)][idx] / eq[idx]
        r["locked_flag_mean"] = float(100 * lk[m].mean()) if m.any() else np.nan
        r["locked_max"] = float(100 * lk.max())
    return r


def validate(runs, dd):
    import flat3_crashpen_driver as F3
    import n700_driver as N
    ref = json.load(open(TSX + "/ts_mkt_ext.json"))
    mv = json.load(open(TSX + "/mtm_vision.json"))
    hoj = json.load(open(TSX + "/ho/ts_mkt_ext_ho.json"))
    V = dict(dev={}, ho={})
    for s in DEVS:
        row = {}
        for arm, k in (("P0", "OFF_"), ("X14", "X14_")):
            r = runs[("DEV", arm, s)]
            N.TAG[k + s], N.DESC[k + s] = r["tag"], "deep"
            m = N.arm_metrics(R, F3, k + s, R.load_legs(r["tag"]), R.load_daily(r["tag"]), mv[k + s]["legacy"])
            i22 = int((pd.Timestamp("2022-01-01") - r["base"]) // pd.Timedelta(minutes=1))
            dd22 = ddx(r["eq"][i22:])[0]
            ddy = {y: ddx(r["eq"][max(0, int((pd.Timestamp("%d-01-01" % y) - r["base"]) // pd.Timedelta(minutes=1))):
                                   int((pd.Timestamp("%d-01-01" % (y + 1)) - r["base"]) // pd.Timedelta(minutes=1))])[0]
                   for y in range(2021, 2026)}
            row[arm] = dict(sum_pnl=float(r["d"]["pnl"].sum()), cagr22=m["cagr22"], dd22_arm=m["dd_mtm22"], dd22_eq=dd22,
                            calmar22=m["calmar22"], dd_year_eq=ddy,
                            dd_year_ref={int(y): v for y, v in mv[k + s]["legacy"]["dd_year"].items()})
        rf = ref["rows"][s]
        row["ref"] = dict(cagr22=rf["cagr22"], dd22=rf["dd_mtm22"], sum_pnl=rf["sum_pnl"])
        V["dev"][s] = row
    d = V["dev"]
    agg = dict(dPnL=float(np.mean([d[s]["X14"]["sum_pnl"] - d[s]["P0"]["sum_pnl"] for s in DEVS])),
               cagr22_P0=float(np.mean([d[s]["P0"]["cagr22"] for s in DEVS])),
               cagr22_X14=float(np.mean([d[s]["X14"]["cagr22"] for s in DEVS])),
               dd22_P0=float(np.mean([d[s]["P0"]["dd22_eq"] for s in DEVS])),
               dd22_X14=float(np.mean([d[s]["X14"]["dd22_eq"] for s in DEVS])),
               max_abs_cagr22_vs_ref=float(max(abs(d[s][a]["cagr22"] - d[s]["ref"]["cagr22"][i]) for s in DEVS
                                                for i, a in enumerate(("P0", "X14")))),
               max_abs_dd22_vs_ref=float(max(abs(d[s][a]["dd22_eq"] - d[s]["ref"]["dd22"][i]) for s in DEVS
                                              for i, a in enumerate(("P0", "X14")))),
               max_abs_pnl_vs_ref=float(max(abs(d[s][a]["sum_pnl"] - d[s]["ref"]["sum_pnl"][i]) for s in DEVS
                                             for i, a in enumerate(("P0", "X14")))),
               max_abs_ddyear_vs_ref=float(max(abs(d[s][a]["dd_year_eq"][y] - d[s][a]["dd_year_ref"][y]) for s in DEVS
                                                for a in ("P0", "X14") for y in range(2021, 2026))))
    agg["ok"] = bool(abs(agg["dPnL"] - ref["agg"]["X14"]["sum_pnl"] + ref["agg"]["OFF"]["sum_pnl"]) <= 0.01 * abs(agg["dPnL"])
                     and agg["max_abs_cagr22_vs_ref"] <= 0.1 and agg["max_abs_dd22_vs_ref"] <= 0.1
                     and agg["max_abs_ddyear_vs_ref"] <= 0.1)
    V["dev_agg"] = agg
    hrows = {}
    for s in HOS:
        rr = {}
        for arm in ("P0", "X14"):
            p = period(runs[("HO", arm, str(s))], "2026-01-01", "2026-10-01")
            rr[arm] = dict(pnl=p["pnl"], roi=p["roi"], dd=p["dd"])
        rows = hoj["rows"][str(s)]["W9"]
        rr["ref"] = dict(pnl=rows["sum_pnl"], roi=rows["roi"], dd=rows["maxdd"])
        hrows[s] = rr
    V["ho"] = hrows
    ha = dict(dPnL=float(np.mean([hrows[s]["X14"]["pnl"] - hrows[s]["P0"]["pnl"] for s in HOS])),
              roi_P0=float(np.mean([hrows[s]["P0"]["roi"] for s in HOS])),
              dROI=float(np.mean([hrows[s]["X14"]["roi"] - hrows[s]["P0"]["roi"] for s in HOS])),
              dDD=float(np.mean([hrows[s]["X14"]["dd"] - hrows[s]["P0"]["dd"] for s in HOS])),
              max_abs_pnl=float(max(abs(hrows[s][a]["pnl"] - hrows[s]["ref"]["pnl"][i]) for s in HOS for i, a in enumerate(("P0", "X14")))),
              max_abs_roi=float(max(abs(hrows[s][a]["roi"] - hrows[s]["ref"]["roi"][i]) for s in HOS for i, a in enumerate(("P0", "X14")))),
              max_abs_dd=float(max(abs(hrows[s][a]["dd"] - hrows[s]["ref"]["dd"][i]) for s in HOS for i, a in enumerate(("P0", "X14")))))
    ha["ok"] = bool(abs(ha["dPnL"] - hoj["mean_dPnL"]) <= 0.01 * abs(hoj["mean_dPnL"]) and ha["max_abs_roi"] <= 0.1
                    and ha["max_abs_dd"] <= 0.1 and abs(ha["roi_P0"] - hoj["base_roi_W9_mean"]) <= 0.1)
    V["ho_agg"] = ha
    log.info("VALIDATE DEV %s", agg)
    log.info("VALIDATE HO %s", ha)
    return V


def build(dd):
    E, EH = eq_dev(), eq_ho()
    runs = {}
    for s in DEVS:
        for arm, k, tag in (("P0", "OFF_", "gqsf-" + s.lower()), ("X14", "X14_", "tsx-x14-" + s.lower())):
            d = load(tag)
            eq, base = E[k + s]
            runs[("DEV", arm, s)] = dict(tag=tag, d=d, c=clusters(d), eq=eq, base=base, on=open_notional(d, len(eq), base, True),
                                         cap0=CAP0, utc=True)
    for s in HOS:
        for arm, tag in (("P0", "ho4-k24-b-s%d" % s), ("X14", "tsx-ho-x14-s%d" % s)):
            d = load(tag)
            eq, base = EH[tag]
            cap0 = float(json.load(open(KS + tag + "/result.json"))["equity_start"])
            runs[("HO", arm, str(s))] = dict(tag=tag, d=d, c=clusters(d), eq=eq, base=base,
                                             on=open_notional(d, len(eq), base, False), cap0=cap0, utc=False)
    return runs


FIELDS = ["n_cl", "n_batch", "n_leg", "win", "pnl", "roi", "dd", "dd_day", "calmar", "worst_m_pct", "hold_mean", "hold_p90",
          "n168", "ncut", "exp_mean", "exp_max"]


def year_tables(runs):
    T = {}
    for scope, seeds, pers in (("DEV", DEVS, PER_DEV), ("HO", [str(s) for s in HOS], PER_HO)):
        for name, a, b in pers:
            P = {arm: {s: period(runs[(scope, arm, s)], a, b) for s in seeds} for arm in ("P0", "X14")}
            row = {}
            for f in FIELDS:
                row[f] = dict(P0=mmm([P["P0"][s][f] for s in seeds]), X14=mmm([P["X14"][s][f] for s in seeds]),
                              D=mmm([P["X14"][s][f] - P["P0"][s][f] for s in seeds]))
            for arm in ("P0", "X14"):
                row["worst_m_" + arm] = mode(P[arm][s]["worst_m"] for s in seeds)
                row["dd_peak_" + arm] = mode(P[arm][s]["dd_peak"][:10] for s in seeds)
                row["dd_trough_" + arm] = mode(P[arm][s]["dd_trough"][:10] for s in seeds)
            row["per_seed_dpnl"] = {s: P["X14"][s]["pnl"] - P["P0"][s]["pnl"] for s in seeds}
            T[name] = row
            log.info("YEAR %s pnl P0 %s X14 %s D %s dd P0 %s X14 %s", name, row["pnl"]["P0"], row["pnl"]["X14"], row["pnl"]["D"],
                     row["dd"]["P0"], row["dd"]["X14"])
    return T


def defer_all(runs, dd, fdev, fho, rdev, rho):
    DF, CHK = [], {}
    par = json.load(open(TSX + "/parity.json"))
    for scope, seeds, fl, rng, ho in (("DEV", DEVS, fdev, rdev, False), ("HO", [str(s) for s in HOS], fho, rho, True)):
        for s in seeds:
            rx, rp = runs[(scope, "X14", s)], runs[(scope, "P0", s)]
            df, ck = deferred(rx, rp["c"], fl, rng, dd, ho)
            if scope == "DEV":
                j = par[rx["tag"]]["tsx"]
                ck["java_clusters"], ck["java_cut"] = j[1], j[2]
            else:
                j = json.load(open(TSX + "/ho/res_%s.json" % rx["tag"]))["tsx"]
                ck["java_clusters"], ck["java_cut"] = j[3], j[4]
            CHK[scope + "_" + s] = ck
            log.info("DEFER %s %s %s", scope, s, ck)
            DF.append(df.assign(scope=scope, seed=s))
    return pd.concat(DF, ignore_index=True), CHK


def defer_summary(DF):
    out = {}
    for scope, g0 in DF.groupby("scope"):
        per = {}
        for s, g in g0.groupby("seed"):
            per[s] = dict(n=len(g), saved_pct=float(100 * (g["delta"] > 0).mean()), sum_delta=float(g["delta"].sum()),
                          mean_delta=float(g["delta"].mean()), med_delta=float(g["delta"].median()),
                          worst=float(g["delta"].min()), best=float(g["delta"].max()), pnl=float(g["pnl"].sum()),
                          pnl168=float(g["pnl168"].sum()), extra_h_mean=float(g["extra_h"].mean()),
                          **{"exit_" + k: int(v) for k, v in g["exit"].value_counts().items()},
                          **{"dsum_" + k: float(v) for k, v in g.groupby("exit")["delta"].sum().items()},
                          **{"saved_" + k: float(100 * v) for k, v in g.groupby("exit")["delta"].apply(lambda x: (x > 0).mean()).items()})
        keys = sorted({k for v in per.values() for k in v})
        out[scope] = dict(per_seed=per, agg={k: mmm([per[s].get(k, 0) for s in per]) for k in keys},
                          pooled=dict(n=int(len(g0)), saved_pct=float(100 * (g0["delta"] > 0).mean()),
                                      p5=float(g0["delta"].quantile(0.05)), p95=float(g0["delta"].quantile(0.95)),
                                      worst5=g0.nsmallest(5, "delta")[["seed", "sym", "t0", "delta", "pnl168", "pnl", "exit", "extra_h"]]
                                      .astype(str).to_dict("records")))
    return out


def episodes(runs, DF, dd, rng, scope, seeds, t_end):
    """dPnL theo dot co (khoang ngay ON lien tuc) va theo su kien (gop gap <= 14 ngay):
    direct = sum(PnL thuc - PnL@168h) cua cum hoan co moc 168h trong dot; seg = dPnL thuc hien theo doan
    [bat dau dot k, bat dau dot k+1) (gom ca path divergence; tong cac doan + doan truoc dot dau = tong dPnL)."""
    ev = events_of(rng)
    res = {}
    for lvl, units in (("ep", [dict(start=a, end=b, eps=[i]) for i, (a, b) in enumerate(rng)]), ("ev", ev)):
        bounds = [pd.Timestamp("2021-01-01")] + [u["start"] for u in units] + [pd.Timestamp(t_end)]
        S, D, TOT = {}, {}, {}
        for s in seeds:
            rp, rx = runs[(scope, "P0", s)], runs[(scope, "X14", s)]
            sd = seg_delta(rp, rx, bounds)
            S[s] = sd[1:]
            pre = sd[0]
            TOT[s] = float(sum(sd))
            g = DF[(DF["scope"] == scope) & (DF["seed"] == s)]
            D[s] = [float(g[g["ep"].isin(u["eps"])]["delta"].sum()) for u in units]
            if abs(pre) > 1e-6:
                log.warning("%s %s %s dPnL truoc dot dau = %.2f (khac 0)", scope, lvl, s, pre)
        rows = []
        for i, u in enumerate(units):
            days = pd.date_range(u["start"] - pd.Timedelta(days=1), u["end"], freq="D")
            ddmin = float(dd.reindex(days).min())
            nd = int(sum((b - a).days + 1 for j, (a, b) in enumerate(rng) if j in u["eps"]))
            g = DF[(DF["scope"] == scope) & DF["ep"].isin(u["eps"])]
            rows.append(dict(i=i, start=str(u["start"].date()), end=str(u["end"].date()), n_on=nd, dd_min=ddmin,
                             label=lab(u["start"]), n_def=mmm([int((g["seed"] == s).sum()) for s in seeds]),
                             direct=mmm([D[s][i] for s in seeds]), seg=mmm([S[s][i] for s in seeds]),
                             loo_seg=mmm([TOT[s] - S[s][i] for s in seeds]),
                             loo_seg_pos=int(sum(TOT[s] - S[s][i] > 0 for s in seeds)),
                             loo_dir=mmm([sum(D[s]) - D[s][i] for s in seeds]),
                             loo_dir_pos=int(sum(sum(D[s]) - D[s][i] > 0 for s in seeds))))
        conc = {}
        for key, X in (("seg", S), ("direct", D)):
            t1, t3, l1, l3 = [], [], [], []
            for s in seeds:
                v = np.sort(np.asarray(X[s]))[::-1]
                tot = float(np.sum(X[s]))
                t1.append(v[0] / tot if tot else np.nan)
                t3.append(v[:3].sum() / tot if tot else np.nan)
                l1.append(tot - v[0])
                l3.append(tot - v[:3].sum())
            conc[key] = dict(top1_share=mmm(t1), top3_share=mmm(t3), loo_top1=mmm(l1), loo_top3=mmm(l3),
                             loo_top1_pos=int(sum(x > 0 for x in l1)), loo_top3_pos=int(sum(x > 0 for x in l3)),
                             total=mmm([np.sum(X[s]) for s in seeds]),
                             n_units_pos_med=int(np.sum(np.median(np.array([X[s] for s in seeds]), axis=0) > 0)),
                             n_units_neg_med=int(np.sum(np.median(np.array([X[s] for s in seeds]), axis=0) < 0)))
        res[lvl] = dict(rows=rows, conc=conc, total=mmm(list(TOT.values())))
    return res


def risk(runs, DF, rng, fl, scope, seeds):
    ev = events_of(rng)
    utc = scope == "DEV"
    out = dict(events=[])
    fe = {arm: [] for arm in ("P0", "X14")}
    for s in seeds:
        fe["P0"].append(flag_exposure(runs[(scope, "P0", s)], fl, utc))
        g = DF[(DF["scope"] == scope) & (DF["seed"] == s)]
        fe["X14"].append(flag_exposure(runs[(scope, "X14", s)], fl, utc, g))
    out["flag_exposure"] = {arm: {k: mmm([x.get(k, np.nan) for x in fe[arm]]) for k in fe[arm][0]} for arm in fe}
    out["flag_exposure"]["D_mean"] = mmm([fe["X14"][i]["exp_flag_mean"] - fe["P0"][i]["exp_flag_mean"] for i in range(len(seeds))])
    for u in ev:
        a, b = u["start"], u["end"] + pd.Timedelta(days=15)
        W = {arm: [win_stats(runs[(scope, arm, s)], a, b, utc) for s in seeds] for arm in ("P0", "X14")}
        p0only = [len(W["P0"][i]["keys"] - W["X14"][i]["keys"]) for i in range(len(seeds))]
        x14only = [len(W["X14"][i]["keys"] - W["P0"][i]["keys"]) for i in range(len(seeds))]
        p0only_pnl = [sum(v for k, v in W["P0"][i]["pnl_new"].items() if k not in W["X14"][i]["keys"]) for i in range(len(seeds))]
        x14only_pnl = [sum(v for k, v in W["X14"][i]["pnl_new"].items() if k not in W["P0"][i]["keys"]) for i in range(len(seeds))]
        out["events"].append(dict(start=str(u["start"].date()), end=str(u["end"].date()), win_end=str(b.date()),
                                  dd_P0=mmm([w["dd"] for w in W["P0"]]), dd_X14=mmm([w["dd"] for w in W["X14"]]),
                                  dd_D=mmm([W["X14"][i]["dd"] - W["P0"][i]["dd"] for i in range(len(seeds))]),
                                  ret_D=mmm([W["X14"][i]["ret"] - W["P0"][i]["ret"] for i in range(len(seeds))]),
                                  new_P0=mmm([w["new_cl"] for w in W["P0"]]), new_X14=mmm([w["new_cl"] for w in W["X14"]]),
                                  new_D=mmm([W["X14"][i]["new_cl"] - W["P0"][i]["new_cl"] for i in range(len(seeds))]),
                                  p0only=mmm(p0only), x14only=mmm(x14only), p0only_pnl=mmm(p0only_pnl),
                                  x14only_pnl=mmm(x14only_pnl)))
    return out


def near(runs, DF, dd, scope, seeds, fl):
    lo, hi = (pd.Timestamp("2021-06-30"), pd.Timestamp("2025-12-30")) if scope == "DEV" else \
        (pd.Timestamp("2025-12-31"), pd.Timestamp("2026-09-29"))
    x = dd[(dd.index >= lo) & (dd.index <= hi)]
    on_m = x[(x >= -0.33) & (x <= -0.30)]
    off_m = x[(x > -0.30) & (x <= -0.27)]
    yrs = sorted(set((x.index + pd.Timedelta(days=1)).year))
    by = {int(y): dict(on_marg=int(((on_m.index + pd.Timedelta(days=1)).year == y).sum()),
                       off_marg=int(((off_m.index + pd.Timedelta(days=1)).year == y).sum()),
                       on=int((((x <= -0.30)) & ((x.index + pd.Timedelta(days=1)).year == y)).sum())) for y in yrs}
    offd = set(off_m.index + pd.Timedelta(days=1))
    g = DF[DF["scope"] == scope]
    r = dict(by_year=by, n_on_marg=int(len(on_m)), n_off_marg=int(len(off_m)),
             first_marg_n=mmm([int(g[(g["seed"] == s) & g["marg_first"]].shape[0]) for s in seeds]),
             first_marg_delta=mmm([float(g[(g["seed"] == s) & g["marg_first"]]["delta"].sum()) for s in seeds]),
             any_marg_n=mmm([int(g[(g["seed"] == s) & g["marg_any"]].shape[0]) for s in seeds]),
             any_marg_delta=mmm([float(g[(g["seed"] == s) & g["marg_any"]]["delta"].sum()) for s in seeds]))
    cut = []
    for s in seeds:
        c = runs[(scope, "X14", s)]["c"]
        k = c[(c["st"] == "STOP_LOSS_DONE") & (c["age_min"] == TS_MIN + 1) & c["mark_day"].isin(offd)]
        cut.append((len(k), float(k["pnl"].sum()), float(k["notional"].sum())))
    r["offmarg_cut168_n"] = mmm([c[0] for c in cut])
    r["offmarg_cut168_pnl"] = mmm([c[1] for c in cut])
    r["offmarg_cut168_notional"] = mmm([c[2] for c in cut])
    return r


# ------------------------------------------------------------------ markdown
def f3(v, nd=1, sign=False):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "–"
    s = ("%+." if sign else "%.") + str(nd) + "f"
    return (s % v).replace(".", ",") if nd else (s % v)


def mm(x, nd=1, sign=False):
    return "%s [%s; %s]" % (f3(x[0], nd, sign), f3(x[1], nd, sign), f3(x[2], nd, sign))


NAMES = [("n_cl", "Số cụm (đóng)", 0), ("n_batch", "Số đợt vào (anchor phân biệt)", 0), ("n_leg", "Số leg", 0),
         ("win", "Win rate leg %", 1), ("pnl", "PnL USD (thực hiện)", 0), ("roi", "ROI % (PnL / số dư đầu kỳ)", 2),
         ("dd", "maxDD MTM phút %", 2), ("dd_day", "maxDD EOD %", 2), ("calmar", "Calmar (ret MTM năm hoá / |DD phút|)", 2),
         ("worst_m_pct", "Tháng tệ nhất % (MTM)", 2), ("hold_mean", "Giữ TB (h, cụm)", 1), ("hold_p90", "Giữ p90 (h)", 1),
         ("n168", "Cụm chạm ≥168h", 0), ("ncut", "Cụm bị cắt time-stop (SL, ≥168h)", 0),
         ("exp_mean", "Phơi nhiễm TB % (notional mở/equity, giờ)", 1), ("exp_max", "Phơi nhiễm max %", 1)]


def md(J):
    o = []
    for name in [p[0] for p in PER_DEV] + [p[0] for p in PER_HO]:
        T = J["years"][name]
        o.append("\n### %s\n\n| Chỉ số | P0 med [min; max] | X14 med [min; max] | Δ (X14−P0) med [min; max] |\n|---|---|---|---|" % name)
        for f, lb, nd in NAMES:
            o.append("| %s | %s | %s | %s |" % (lb, mm(T[f]["P0"], nd), mm(T[f]["X14"], nd), mm(T[f]["D"], nd, True)))
        o.append("| DD đỉnh→đáy (mode seed) | %s → %s | %s → %s | |" % (T["dd_peak_P0"], T["dd_trough_P0"], T["dd_peak_X14"], T["dd_trough_X14"]))
        o.append("| Tháng tệ nhất (mode) | %s | %s | |" % (T["worst_m_P0"], T["worst_m_X14"]))
    o.append("\n### ΔPnL theo seed × kỳ (USD)\n\n| Seed | " + " | ".join(p[0] for p in PER_DEV[:-1]) + " | DEV | HO seed | 2026W9 |\n|---|" + "---|" * (len(PER_DEV) + 2))
    neg = 0
    for s, h in zip(DEVS, HOS):
        cells = [J["years"][p[0]]["per_seed_dpnl"][s] for p in PER_DEV]
        hc = J["years"]["2026W9"]["per_seed_dpnl"][str(h)]
        neg += sum(c < 0 for c in cells[:-1]) + (hc < 0)
        o.append("| %s | %s | %d | %s |" % (s, " | ".join(f3(c, 0, True) for c in cells), h, f3(hc, 0, True)))
    o.append("\nÔ âm (5 kỳ DEV × 8 + W9 × 8 = 48 ô): **%d**" % neg)
    J["neg_cells"] = neg
    return "\n".join(o)


def md_eps(E, title):
    o = ["\n### %s — theo đợt cờ (khoảng ON liên tục)\n" % title,
         "| # | Đợt (UTC) | ngày ON | dd ALT_EW min | Sự kiện (gợi ý) | cụm hoãn/seed | Δ direct (med [min; max]) | Δ đoạn (med [min; max]) | LOO đoạn med (seed>0) |",
         "|---|---|---|---|---|---|---|---|---|"]
    for r in E["ep"]["rows"]:
        o.append("| %d | %s→%s | %d | %s | %s | %s | %s | %s | %s (%d/8) |" % (
            r["i"], r["start"], r["end"], r["n_on"], f3(100 * r["dd_min"], 1), r["label"], mm(r["n_def"], 0),
            mm(r["direct"], 0, True), mm(r["seg"], 0, True), f3(r["loo_seg"][0], 0, True), r["loo_seg_pos"]))
    o.append("\n#### %s — theo sự kiện (gộp các đợt cách nhau ≤ 14 ngày)\n" % title)
    o.append("| # | Sự kiện (UTC) | ngày ON | dd min | Nhãn | cụm hoãn/seed | Δ direct | Δ đoạn | LOO đoạn med (seed>0) | LOO direct med (seed>0) |")
    o.append("|---|---|---|---|---|---|---|---|---|---|")
    for r in E["ev"]["rows"]:
        o.append("| %d | %s→%s | %d | %s | %s | %s | %s | %s | %s (%d/8) | %s (%d/8) |" % (
            r["i"], r["start"], r["end"], r["n_on"], f3(100 * r["dd_min"], 1), r["label"], f3(r["n_def"][0], 0),
            mm(r["direct"], 0, True), mm(r["seg"], 0, True), f3(r["loo_seg"][0], 0, True), r["loo_seg_pos"],
            f3(r["loo_dir"][0], 0, True), r["loo_dir_pos"]))
    for lvl in ("ep", "ev"):
        for k in ("seg", "direct"):
            c = E[lvl]["conc"][k]
            o.append("- %s/%s: tổng %s; tỉ trọng top-1 %s %%, top-3 %s %%; bỏ top-1 → %s (%d/8 >0); bỏ top-3 → %s (%d/8 >0); "
                     "đơn vị Δmed>0: %d, <0: %d" % (lvl, k, mm(c["total"], 0, True), mm([100 * x for x in c["top1_share"]], 0),
                                                    mm([100 * x for x in c["top3_share"]], 0), mm(c["loo_top1"], 0, True),
                                                    c["loo_top1_pos"], mm(c["loo_top3"], 0, True), c["loo_top3_pos"],
                                                    c["n_units_pos_med"], c["n_units_neg_med"]))
    return "\n".join(o)


def main():
    assert R._work is MT._work_vision, "gvz_mtm chua patch R"
    mc = json.load(open(C + "/mtm_check_dev.json"))
    mh = json.load(open(C + "/mtm_check_ho.json"))
    assert mc["ok"] and mh["ok"], "eq cache chua tu kiem OK"
    dd = ew_dd()
    fdev, fho, rdev, rho, fchk = flags(dd)
    runs = build(dd)
    J = dict(mtm_cache=dict(dev_ok=mc["ok"], ho_ok=mh["ok"], ho_miss=mh["mtm_check"]["miss"]), flags=fchk)
    J["validate"] = validate(runs, dd)
    J["px_check"] = dict(DEV_A1=px_check(runs[("DEV", "P0", "A1")], False), HO_42=px_check(runs[("HO", "P0", "42")], True))
    log.info("PXCHECK %s", J["px_check"])
    J["years"] = year_tables(runs)
    DF, J["defer_check"] = defer_all(runs, dd, fdev, fho, rdev, rho)
    J["defer"] = defer_summary(DF)
    DF.assign(t0=DF["t0"].astype(str), te=DF["te"].astype(str), mark_u=DF["mark_u"].astype(str),
              mark_day=DF["mark_day"].dt.date.astype(str))[
        ["scope", "seed", "sym", "t0", "te", "n", "st", "exit", "age_min", "extra_h", "mark_u", "mark_day", "ep", "px168",
         "pnl168", "pnl", "delta", "notional", "p0_match", "marg_first", "marg_any"]].to_csv(HERE + "/deferred_clusters.csv", index=False)
    J["episodes"] = dict(DEV=episodes(runs, DF, dd, rdev, "DEV", DEVS, "2026-01-01"),
                         HO=episodes(runs, DF, dd, rho, "HO", [str(s) for s in HOS], "2026-10-02"))
    J["risk"] = dict(DEV=risk(runs, DF, rdev, fdev, "DEV", DEVS), HO=risk(runs, DF, rho, fho, "HO", [str(s) for s in HOS]))
    J["near"] = dict(DEV=near(runs, DF, dd, "DEV", DEVS, fdev), HO=near(runs, DF, dd, "HO", [str(s) for s in HOS], fho))
    fy = {}
    for d in sorted(fdev | fho):
        fy[str(d.year)] = fy.get(str(d.year), 0) + 1
    J["flag_days_by_year"] = fy
    txt = md(J) + md_eps(J["episodes"]["DEV"], "DEV") + md_eps(J["episodes"]["HO"], "HO 2026")
    open(HERE + "/deep_tables.md", "w").write(txt)
    json.dump(J, open(HERE + "/deep.json", "w"), indent=1, default=str)
    dd.rename("dd").to_frame().assign(flag_next=dd <= -0.30).to_csv(HERE + "/altew_dd_daily.csv")
    log.info("WROTE deep.json, deep_tables.md, deferred_clusters.csv, altew_dd_daily.csv")


if __name__ == "__main__":
    main()
