#!/usr/bin/env python3
"""chain_n_audit.py -- AUDIT CHAIN_N 2026-10-03 (0-sim, CHI DOC artifact co san).

Stage:
  ticks  : giai phau nhip vao lenh B0 (de-p1): tick/ngay/khoang trong, lenh/ngay-co-lenh, theo level/nam.
  pairs  : "lenh THEM" khi mo rong n tren cac run DA CO (khop sym|start|level): bao nhieu, chat luong, roi
           vao ngay da co lenh hay ngay moi (thuoc do size-neutral = profit %/lenh; CI bootstrap cum NGAY).
  gatelog: dong [GATE-RATIO] seen/pass theo quy tu sim.out (n selector = quota (1-pct) x luong ung vien).
  proxy  : gate PROXY cap PHUT tren p15_dev (quantile cuon 90d, tinh lai moi gio, causal, warm-up 7d):
           hieu chuan so phut-mo = so phut-vao selector B0 (1x), roi 2x/3x: phut mo THEM roi vao ngay nao.
           Chi DEM tick, KHONG PnL. Proxy bo qua he so symbolPred (factor) => kiem bang recall vs B0.
  dip    : dem su kien coin -8%/1h (close 1h v2, cooldown 24h) + ret 24h/72h tho vs EW cung cua so
           (MO TA de dinh co n cho huong "dip theo coin"; khong exit, khong phi, khong SL).
Usage: python3 chain_n_audit.py [OUT_JSON]
"""
import sys, json, hashlib, subprocess, math, re
import numpy as np, pandas as pd

REPO = "/home/ubuntu/src/BinanceFuturesJava"
OUT = "/home/ubuntu/kaggle_sim/out"
P15 = REPO + "/research/parity/data/p15_dev.csv"
V2 = "/home/ubuntu/java/fsrun/CLOSES_1H_v2.bin"
V2_MD5 = "58f56069e8e1a7c739011ddfa13e9636"
B0 = "de-p1"
B0_MD5 = "650c386f0d0dfea334af9d55ca2f21d4"
SEED, NREP = 20260905, 2000
TZ = pd.Timedelta(hours=7)
H, D = 3600000, 86400000
DEV0_UTC = int((pd.Timestamp("2021-07-01") - TZ).value // 10**6)
DEV1_UTC = int((pd.Timestamp("2025-12-31") - TZ).value // 10**6)
JOUT = sys.argv[1] if len(sys.argv) > 1 else REPO + "/docs/audit/AUDIT_CHAIN_AND_N_20261003.json"
R = {"meta": {"seed": SEED, "nrep": NREP, "b0": B0}}


def md5(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def q(a, ps=(50, 75, 90, 99)):
    a = np.asarray(a, float)
    if len(a) == 0:
        return None
    return {f"p{p}": round(float(np.percentile(a, p)), 3) for p in ps} | {"max": round(float(a.max()), 3),
                                                                        "mean": round(float(a.mean()), 3)}


def load_pd(tag):
    p = f"{OUT}/{tag}/storage/printDone.csv"
    d = pd.read_csv(p)
    d.columns = [c.strip() for c in d.columns]
    d = d[d.side == "BUY"].copy()
    d["t0"] = pd.to_datetime(d["start"], format="%Y%m%d %H:%M")          # GMT+7
    d["ms"] = ((d["t0"] - TZ).astype("datetime64[ns]").astype("int64") // 10**6).astype(np.int64)
    d["day"] = d["t0"].dt.normalize()
    d["yr"] = d["t0"].dt.year
    d["sl"] = (d["status"] == "STOP_LOSS_DONE").astype(int)
    d["win"] = (d["profit"] > 0).astype(int)
    k = d["sym"] + "|" + d["start"] + "|" + d["level"]
    d["key"] = k + "#" + d.groupby(k).cumcount().astype(str)
    return d, md5(p)


def boot_day_mean(x, day, nrep=NREP, seed=SEED):
    """CI95 cua mean(x) bootstrap theo CUM NGAY (resample ngay co lenh)."""
    x = np.asarray(x, float)
    if len(x) < 5:
        return None
    codes, uniq = pd.factorize(day)
    s = np.bincount(codes, weights=x)
    c = np.bincount(codes)
    rng = np.random.default_rng(seed)
    nd = len(s)
    idx = rng.integers(0, nd, size=(nrep, nd))
    m = s[idx].sum(1) / c[idx].sum(1)
    return [round(float(np.percentile(m, 2.5)), 3), round(float(np.percentile(m, 97.5)), 3)]


# ======================================================================= ticks
def gaps_h(ms_sorted):
    g = np.diff(np.asarray(ms_sorted, np.int64)) / H
    return g


def bursts(ms_sorted, sep_min=60):
    """gom tick cach nhau <= sep_min phut thanh 1 'dot'; tra ve mang thoi diem bat dau dot."""
    ms = np.asarray(ms_sorted, np.int64)
    if len(ms) == 0:
        return ms
    newb = np.concatenate([[True], np.diff(ms) > sep_min * 60000])
    return ms[newb]


def stage_ticks(d):
    out = {}
    ndays_cal = (pd.Timestamp("2025-12-31") - pd.Timestamp("2021-07-01")).days
    out["calendar_days"] = ndays_cal
    for name, sub in [("all", d), ("selector", d[d.level == "PREDICT_SYMBOL_TRADE"]),
                      ("big_down", d[d.level == "BIG_DOWN"]), ("dca1", d[d.level == "DCA_LEVEL1"])]:
        ticks = np.sort(sub["ms"].unique())
        b = bursts(ticks)
        per_tick = sub.groupby("ms").size()
        per_day = sub.groupby("day").size()
        o = {"n": int(len(sub)), "n_tick_minutes": int(len(ticks)), "n_days": int(sub["day"].nunique()),
             "n_bursts_60m": int(len(b)), "trades_per_tick": q(per_tick.values),
             "trades_per_day_with_trade": q(per_day.values),
             "gap_between_ticks_h": q(gaps_h(ticks)), "gap_between_bursts_h": q(gaps_h(b)),
             "gap_between_trade_days_d": q(np.diff(np.sort(sub["day"].unique())).astype("timedelta64[h]").astype(float) / 24.0),
             "mean_profit_pct": round(float(sub["profit"].mean()), 3) if len(sub) else None}
        if len(sub):
            top10 = per_day.sort_values(ascending=False)
            k = max(1, int(round(0.1 * len(top10))))
            o["share_trades_top10pct_days"] = round(float(top10.iloc[:k].sum() / top10.sum()), 3)
            pnl_day = sub.groupby("day")["pnl"].sum().reindex(top10.index[:k])
            o["share_pnl_top10pct_days_by_n"] = round(float(pnl_day.sum() / sub["pnl"].sum()), 3)
        yr = {}
        for y, s2 in sub.groupby("yr"):
            yr[int(y)] = {"n": int(len(s2)), "days": int(s2["day"].nunique()), "ticks": int(s2["ms"].nunique()),
                          "bursts": int(len(bursts(np.sort(s2["ms"].unique())))),
                          "n_per_day_with_trade": round(len(s2) / max(1, s2["day"].nunique()), 2),
                          "mean_profit_pct": round(float(s2["profit"].mean()), 3)}
        o["by_year"] = yr
        out[name] = o
    # thoi gian co >= 1 lenh mo (phut), dung start/end GMT+7
    te = pd.to_datetime(d["end"], format="%Y%m%d %H:%M")
    s = ((d["t0"] - pd.Timestamp("2021-07-01")).dt.total_seconds() // 60).astype(np.int64).to_numpy()
    e = ((te - pd.Timestamp("2021-07-01")).dt.total_seconds() // 60).astype(np.int64).to_numpy()
    T = ndays_cal * 1440
    arr = np.zeros(T + 2, np.int32)
    np.add.at(arr, np.clip(s, 0, T), 1)
    np.add.at(arr, np.clip(e, 0, T), -1)
    op = np.cumsum(arr)[:T]
    out["frac_time_ge1_open"] = round(float((op > 0).mean()), 4)
    out["frac_days_any_open"] = round(float((op.reshape(ndays_cal, 1440).max(1) > 0).mean()), 4)
    # profit theo so lenh cung tick (do dong) -- mo ta
    pt = d.groupby("ms").size().rename("nt")
    dd = d.join(pt, on="ms")
    cut = pd.cut(dd["nt"], [0, 1, 3, 7, 15, 1000], labels=["1", "2-3", "4-7", "8-15", ">15"])
    out["profit_by_tick_crowd"] = {str(k): {"n": int(len(g)), "mean_profit": round(float(g["profit"].mean()), 3),
                                            "sl_pct": round(100 * float(g["sl"].mean()), 2)}
                                   for k, g in dd.groupby(cut, observed=True)}
    R["ticks"] = out
    a = out["all"]
    print(f"[ticks] n {a['n']} ticks {a['n_tick_minutes']} days {a['n_days']} bursts {a['n_bursts_60m']} "
          f"gap_ticks_h {a['gap_between_ticks_h']} timeopen {out['frac_time_ge1_open']}")


# ======================================================================= pairs
PAIRS = [
    ("de-p1", "de-p2", "B0 K16 -> K24 (FLAT3, F0.015)"),
    ("de-p1", "de-p3", "B0 K16 -> K32 (FLAT3, F0.015)"),
    ("de-p1", "de-p5", "B0 K16 -> K32 F0.0075"),
    ("gdv2-g2", "gdv2-g1", "G2 W90 -> G1 W30 (cung pct; TS0.5)"),
    ("gdv2-g0", "gdv2-g2", "R4 (scale1.55) -> G2 (rolling W90)"),
    ("gdv2-g0", "gd92-r4-d1", "R4 -> D1 (x1.55 + q0.92)"),
    ("gdv2-g0", "gd92-r4-d2", "R4 -> D2 (x1.00 + q0.92, mo)"),
    ("kg0-g170", "kg0-g140", "scale 1.70 -> 1.40 (phi LEGACY 0.8%)"),
    ("kg0-g170", "kg0-g100", "scale 1.70 -> 1.00 (phi LEGACY 0.8%)"),
]


def stage_pairs(cache):
    res = []
    for bt, at, lab in PAIRS:
        b, hb = cache(bt)
        a, ha = cache(at)
        kb, ka = set(b.key), set(a.key)
        m = a[a.key.isin(kb)]
        oa = a[~a.key.isin(kb)].copy()
        ob = b[~b.key.isin(ka)]
        bdays = set(b["day"])
        oa["on_base_day"] = oa["day"].isin(bdays)
        btick = set(b["ms"])
        oa["on_base_tick"] = oa["ms"].isin(btick)
        o = {"base": bt, "arm": at, "label": lab, "md5_base": hb, "md5_arm": ha,
             "n_base": int(len(b)), "n_arm": int(len(a)), "matched": int(len(m)),
             "only_arm": int(len(oa)), "only_base": int(len(ob)),
             "mean_profit_base_all": round(float(b.profit.mean()), 3),
             "mean_profit_matched_arm": round(float(m.profit.mean()), 3),
             "only_arm_mean_profit": round(float(oa.profit.mean()), 3) if len(oa) else None,
             "only_arm_median_profit": round(float(oa.profit.median()), 3) if len(oa) else None,
             "only_arm_ci_dayboot": boot_day_mean(oa.profit, oa.day),
             "only_arm_win_pct": round(100 * float(oa.win.mean()), 2) if len(oa) else None,
             "only_arm_sl_pct": round(100 * float(oa.sl.mean()), 2) if len(oa) else None,
             "only_arm_sum_pnl": round(float(oa.pnl.sum()), 1),
             "only_base_mean_profit": round(float(ob.profit.mean()), 3) if len(ob) else None,
             "only_base_sum_pnl": round(float(ob.pnl.sum()), 1),
             "base_sum_pnl": round(float(b.pnl.sum()), 1), "arm_sum_pnl": round(float(a.pnl.sum()), 1),
             "marginal_roi_per_trade": round(float((a.profit.sum() - b.profit.sum()) / max(1, len(a) - len(b))), 3)
             if len(a) != len(b) else None,
             "only_arm_frac_on_base_day": round(float(oa.on_base_day.mean()), 3) if len(oa) else None,
             "only_arm_frac_on_base_tick": round(float(oa.on_base_tick.mean()), 3) if len(oa) else None,
             "only_arm_new_days": int(oa.loc[~oa.on_base_day, "day"].nunique()),
             "arm_days": int(a.day.nunique()), "base_days": int(b.day.nunique())}
        for flag, g in [("base_day", oa[oa.on_base_day]), ("new_day", oa[~oa.on_base_day])]:
            o[f"only_arm_{flag}"] = {"n": int(len(g)),
                                     "mean_profit": round(float(g.profit.mean()), 3) if len(g) else None,
                                     "ci_dayboot": boot_day_mean(g.profit, g.day),
                                     "sl_pct": round(100 * float(g.sl.mean()), 2) if len(g) else None,
                                     "sum_pnl": round(float(g.pnl.sum()), 1)}
        o["only_arm_by_level"] = {k: {"n": int(len(g)), "mean_profit": round(float(g.profit.mean()), 3)}
                                  for k, g in oa.groupby("level")}
        o["only_arm_by_year"] = {int(k): {"n": int(len(g)), "mean_profit": round(float(g.profit.mean()), 3),
                                          "sum_pnl": round(float(g.pnl.sum()), 1)} for k, g in oa.groupby("yr")}
        res.append(o)
        print(f"[pairs] {lab}: n {o['n_base']}->{o['n_arm']} only_arm {o['only_arm']} mean {o['only_arm_mean_profit']} "
              f"CI {o['only_arm_ci_dayboot']} SL {o['only_arm_sl_pct']} on_base_day {o['only_arm_frac_on_base_day']} "
              f"newdays {o['only_arm_new_days']} | base mean {o['mean_profit_base_all']}")
    R["pairs"] = res


# ======================================================================= gatelog
RXG = re.compile(r"GATE-RATIO (on|off) pct=([\d.]+) days=(\d+) seen=(\d+) pass=(\d+) rho=([\d.eE-]+)")


def stage_gatelog():
    out = {}
    for t in ["de-p1", "de-p2", "de-p3", "de-p5", "gdv2-g0", "gdv2-g1", "gdv2-g2"]:
        p = f"{OUT}/{t}/logs/sim.out"
        try:
            ln = subprocess.run(["grep", "-a", "-m1", "GATE-RATIO.*seen=", p], capture_output=True, text=True).stdout
        except Exception as e:
            ln = ""
        mm = RXG.search(ln)
        if not mm:
            out[t] = None
            continue
        qs = dict((k, [int(x) for x in v.split("/")]) for k, v in re.findall(r"(\d{4}Q\d):(\d+/\d+)", ln))
        out[t] = {"mode": mm.group(1), "pct": float(mm.group(2)), "days": int(mm.group(3)),
                  "seen": int(mm.group(4)), "pass": int(mm.group(5)), "rho": float(mm.group(6)),
                  "pass_by_q": {k: v[0] for k, v in qs.items()},
                  "seen_per_min": round(int(mm.group(4)) / (1644 * 1440), 2)}
        print(f"[gatelog] {t}: {out[t]['mode']} pct {out[t]['pct']} W{out[t]['days']} seen {out[t]['seen']} "
              f"pass {out[t]['pass']} rho {out[t]['rho']:.3e} seen/min {out[t]['seen_per_min']}")
    R["gatelog"] = out


# ======================================================================= proxy
def day7(ms):
    return pd.to_datetime(np.asarray(ms, np.int64) + 7 * H, unit="ms").normalize()


def stage_proxy(b0):
    h5 = md5(P15)
    R["meta"]["p15_dev_md5"] = h5
    df = pd.read_csv(P15, usecols=["ts", "predReturn15M"])
    ts = df.ts.to_numpy(np.int64)
    v = df.predReturn15M.to_numpy(np.float64)
    ok = np.isfinite(v)
    ts, v = ts[ok], v[ok]
    o = np.argsort(ts, kind="stable")
    ts, v = ts[o], v[o]
    keep = np.concatenate([[True], np.diff(ts) > 0])
    ts, v = ts[keep], v[keep]
    sel = (ts >= DEV0_UTC) & (ts < DEV1_UTC)
    ts, v = ts[sel], v[sel]
    first = int(ts[0])
    warm_end = first + 7 * D
    hours = np.unique(ts // H) * H
    F = np.unique(np.round(np.logspace(-5, -2, 61), 10))
    KMAX = int(math.ceil(F.max() * 90 * 1440)) + 10
    thr = np.full((len(hours), len(F)), np.inf)
    selm = b0.loc[b0.level == "PREDICT_SYMBOL_TRADE", "ms"].to_numpy(np.int64)
    sel_ms = np.unique(selm)
    pos = np.searchsorted(ts, sel_ms)
    posc = np.minimum(pos, len(ts) - 1)
    found = ts[posc] == sel_ms
    by_hour = {}
    for msx, pz in zip(sel_ms[found], posc[found]):
        by_hour.setdefault(int(msx // H * H), []).append((int(msx), float(v[pz])))
    topfrac = {}
    lo_i = np.searchsorted(ts, hours - 90 * D, "left")
    hi_i = np.searchsorted(ts, hours, "left")
    for i, h in enumerate(hours):
        if h < warm_end:
            continue
        lo, hi = int(lo_i[i]), int(hi_i[i])
        m = hi - lo
        if m < 1000:
            continue
        w = v[lo:hi]
        kk = min(KMAX, m)
        top = np.sort(np.partition(w, m - kk)[m - kk:])[::-1]
        k = np.floor((1.0 - F) * (m - 1)).astype(np.int64)
        j = np.minimum(m - 1 - k, kk - 1)
        thr[i] = top[j]
        if int(h) in by_hour:
            for msx, val in by_hour[int(h)]:
                cnt = int(np.searchsorted(-top, -val, "right"))
                topfrac[msx] = cnt / m if cnt < kk else float("nan")
    hidx = np.searchsorted(hours, ts // H * H)
    counts = np.array([int((v >= thr[hidx, jj]).sum()) for jj in range(len(F))])
    sel_post = sel_ms[sel_ms >= warm_end]
    N1 = len(sel_post)
    out = {"n_minutes": int(len(ts)), "warm_end_utc_ms": warm_end, "b0_sel_entry_minutes_post_warm": int(N1),
           "b0_sel_entry_minutes_with_p15": int(found.sum()), "grid_f": [float(x) for x in F],
           "grid_pass_minutes": [int(x) for x in counts]}
    tf = np.array([topfrac.get(int(x), np.nan) for x in sel_post])
    out["b0_entry_p15_topfrac"] = {"n": int(len(tf)), "n_beyond_kmax": int(np.isnan(tf).sum()),
                                   "quantiles": q(tf[np.isfinite(tf)], (10, 25, 50, 75, 90, 95))}
    b0_days = set(b0["day"])
    sel_days = set(day7(sel_post))
    levels = {}
    base_set = None
    base_days = None
    for mult in [1, 2, 3, 5]:
        idx = int(np.argmin(np.abs(counts - mult * N1)))
        P = ts[v >= thr[hidx, idx]]
        pdays = day7(P)
        dset = set(pdays)
        yrs = pd.Series(pdays).dt.year
        b = bursts(P)
        wk = set(pd.Series(pdays).dt.to_period("W"))
        L = {"f": float(F[idx]), "pct_equiv_minute": 1 - float(F[idx]), "pass_minutes": int(len(P)),
             "mult_vs_b0": round(len(P) / N1, 3), "pass_days": int(len(dset)), "weeks": int(len(wk)),
             "days_by_year": {int(k): int(g.nunique()) for k, g in pd.Series(pdays).groupby(yrs)},
             "minutes_by_year": {int(k): int(len(g)) for k, g in pd.Series(pdays).groupby(yrs)},
             "gap_pass_minutes_h": q(gaps_h(P)), "bursts_60m": int(len(b)), "gap_bursts_h": q(gaps_h(b)),
             "recall_b0_sel_minute": round(float(np.isin(sel_post, P).mean()), 3),
             "recall_b0_sel_day": round(len(sel_days & dset) / max(1, len(sel_days)), 3),
             "frac_pass_days_that_are_b0_days": round(len(dset & b0_days) / max(1, len(dset)), 3),
             "b0_tf_le_f": round(float(np.nanmean(tf <= F[idx])), 3)}
        if mult == 1:
            base_set, base_days = set(P.tolist()), dset
        else:
            new = np.array([x for x in P.tolist() if x not in base_set], np.int64)
            nd = day7(new)
            nds = pd.Series(nd)
            L["new_minutes"] = int(len(new))
            L["new_frac_on_b0_day"] = round(float(nds.isin(b0_days).mean()), 3) if len(new) else None
            L["new_frac_on_L1_day"] = round(float(nds.isin(base_days).mean()), 3) if len(new) else None
            L["new_days_not_b0"] = int(len(set(nd) - b0_days))
            L["new_days_not_L1"] = int(len(set(nd) - base_days))
            L["new_days_not_b0_by_year"] = {int(k): int(g.nunique()) for k, g in
                                            nds[~nds.isin(b0_days)].groupby(nds[~nds.isin(b0_days)].dt.year)}
            L["new_bursts_60m"] = int(len(bursts(np.sort(new))))
        levels[f"x{mult}"] = L
        print(f"[proxy] x{mult}: f {F[idx]:.2e} passmin {len(P)} ({len(P)/N1:.2f}x) days {len(dset)} weeks {len(wk)} "
              f"recall_min {L['recall_b0_sel_minute']} recall_day {L['recall_b0_sel_day']} "
              f"gap_h {L['gap_pass_minutes_h']} " + (f"new_on_b0day {L.get('new_frac_on_b0_day')} newdays {L.get('new_days_not_b0')}" if mult > 1 else ""))
    out["levels"] = levels
    print("[proxy] b0 topfrac", out["b0_entry_p15_topfrac"])
    R["proxy"] = out


# ======================================================================= dip (per-coin -8%/1h)
def stage_dip(b0):
    h2 = md5(V2)
    assert h2 == V2_MD5, h2
    R["meta"]["closes_v2_md5"] = h2
    a = np.fromfile(V2, dtype=np.dtype([("ts", ">i8"), ("sym", ">i2"), ("c", ">f4")]))
    ts = a["ts"].astype(np.int64)
    sid = a["sym"].astype(np.int64)
    c = a["c"].astype(np.float64)
    m = (ts >= DEV0_UTC - 2 * D) & (ts < DEV1_UTC + 4 * D)
    ts, sid, c = ts[m], sid[m], c[m]
    T = np.unique(ts)
    S = np.unique(sid)
    C = np.full((len(T), len(S)), np.nan, np.float32)
    C[np.searchsorted(T, ts), np.searchsorted(S, sid)] = c
    del a
    with np.errstate(divide="ignore", invalid="ignore"):
        r1 = C[1:] / C[:-1] - 1.0
    r1 = np.vstack([np.full((1, len(S)), np.nan, np.float32), r1])
    contiguous = np.concatenate([[False], np.diff(T) == H])
    r1[~contiguous] = np.nan
    ev_t, ev_s = np.where(r1 <= -0.08)
    inwin = (T[ev_t] >= DEV0_UTC) & (T[ev_t] < DEV1_UTC)
    ev_t, ev_s = ev_t[inwin], ev_s[inwin]
    o = np.lexsort((ev_t, ev_s))
    ev_t, ev_s = ev_t[o], ev_s[o]
    keep = np.ones(len(ev_t), bool)
    last = {}
    for i, (t, s) in enumerate(zip(ev_t, ev_s)):
        if s in last and T[t] - T[last[s]] < D:
            keep[i] = False
        else:
            last[s] = t
    ev_t, ev_s = ev_t[keep], ev_s[keep]
    nmkt = (r1 <= -0.08).sum(1)
    res = {"n_events": int(len(ev_t))}
    rows = []
    for hz in (24, 72):
        tt = ev_t + hz
        okk = tt < len(T)
        fwd = np.full(len(ev_t), np.nan)
        ew = np.full(len(ev_t), np.nan)
        with np.errstate(divide="ignore", invalid="ignore"):
            fwd[okk] = C[tt[okk], ev_s[okk]] / C[ev_t[okk], ev_s[okk]] - 1
            Rall = C[tt[okk]] / C[ev_t[okk]] - 1
            ew[okk] = np.nanmean(np.where(np.abs(Rall) < 5, Rall, np.nan), axis=1)
        rows.append((hz, fwd, ew))
    days = day7(T[ev_t])
    dfe = pd.DataFrame({"day": days, "yr": days.year, "nmkt": nmkt[ev_t],
                        "f24": rows[0][1] * 100, "x24": (rows[0][1] - rows[0][2]) * 100,
                        "f72": rows[1][1] * 100, "x72": (rows[1][1] - rows[1][2]) * 100})
    dfe["kind"] = np.where(dfe.nmkt >= 10, "market(>=10 coin cung gio)", np.where(dfe.nmkt <= 2, "idio(<=2)", "mid(3-9)"))
    b0_days = set(b0["day"])
    dfe["on_b0_day"] = dfe.day.isin(b0_days)
    def summ(g):
        o = {"n": int(len(g)), "days": int(g.day.nunique())}
        for col in ["f24", "x24", "f72", "x72"]:
            x = g[col].dropna()
            o[col] = {"mean": round(float(x.mean()), 3) if len(x) else None,
                      "median": round(float(x.median()), 3) if len(x) else None,
                      "p5": round(float(np.percentile(x, 5)), 2) if len(x) else None,
                      "ci_dayboot": boot_day_mean(x, g.loc[x.index, "day"])}
        return o
    res["all"] = summ(dfe)
    res["by_kind"] = {k: summ(g) for k, g in dfe.groupby("kind")}
    res["by_year"] = {int(k): {"n": int(len(g)), "days": int(g.day.nunique()),
                               "x72_mean": round(float(g.x72.mean()), 3)} for k, g in dfe.groupby("yr")}
    res["frac_on_b0_day"] = round(float(dfe.on_b0_day.mean()), 3)
    res["idio_not_b0_day"] = summ(dfe[(dfe.kind == "idio(<=2)") & (~dfe.on_b0_day)])
    pdy = dfe.groupby("day").size()
    res["events_per_event_day"] = q(pdy.values)
    R["dip"] = res
    print(f"[dip] n {res['n_events']} days {res['all']['days']} on_b0_day {res['frac_on_b0_day']} "
          f"x72 {res['all']['x72']} | kinds " + str({k: (v['n'], v['x72']['mean'], v['x72']['ci_dayboot']) for k, v in res['by_kind'].items()}))


# ======================================================================= gaterep (tai lap gate GDV2 cap ung vien)
BINS = ["/home/ubuntu/kaggle_sim/s3moc21", "/home/ubuntu/predwf_map_s1a2_x1"]
REC = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("p0", ">f4"), ("p1", ">f4"), ("p2", ">f4"), ("p3", ">f4")])
MAPF = "/home/ubuntu/selector_pred_out/symbol_map.csv"
DYN_MIN, SCORE_BASE, DYN_MULT = 0.26787, 0.15, 1.28760
RHO = 4.9171e-5          # = 1 - 0.99995083 (RESULT_GDV2_EVEN, do tu G0)
KTOP, TOPB = 16, 700     # top-K selector; so phan tu giu moi khoi gio/ngay (>= k lon nhat can)


def load_top16():
    import glob
    fs = []
    for dd in BINS:
        fs += glob.glob(dd + "/predict_wf_*.bin")
    fs = sorted(fs, key=lambda x: x.split("/")[-1])
    assert len(fs) == 18, len(fs)
    T, SP, SY = [], [], []
    for f in fs:
        a = np.fromfile(f, dtype=REC)
        p0 = a["p0"].astype(np.float32)
        ok = ~np.isnan(p0)
        ts = a["ts"][ok].astype(np.int64)
        sc = (np.float32(1.0) - p0[ok]).astype(np.float32)
        sy = a["sym"][ok].astype(np.int32)
        o = np.lexsort((sc, ts))
        ts, sc, sy = ts[o], sc[o], sy[o]
        u, st = np.unique(ts, return_index=True)
        grp = np.repeat(np.arange(len(u)), np.diff(np.append(st, len(ts))))
        rk = np.arange(len(ts)) - st[grp]
        k = rk < KTOP
        M = np.full((len(u), KTOP), np.nan, np.float32)
        S = np.full((len(u), KTOP), -1, np.int32)
        M[grp[k], rk[k]] = sc[k]
        S[grp[k], rk[k]] = sy[k]
        T.append(u); SP.append(M); SY.append(S)
    return np.concatenate(T), np.vstack(SP), np.vstack(SY)


def stage_gaterep(b0):
    T15, SP, SY = load_top16()
    df = pd.read_csv(P15, usecols=["ts", "predReturn15M"])
    ts = df.ts.to_numpy(np.int64); v = df.predReturn15M.to_numpy(np.float64)
    ok = np.isfinite(v); ts, v = ts[ok], v[ok]
    o = np.argsort(ts, kind="stable"); ts, v = ts[o], v[o]
    keep = np.concatenate([[True], np.diff(ts) > 0]); ts, v = ts[keep], v[keep]
    sel = (ts >= DEV0_UTC) & (ts < DEV1_UTC); ts, v = ts[sel], v[sel]
    fi = np.searchsorted(T15, ts, "right") - 1
    okf = (fi >= 0) & (ts - T15[np.maximum(fi, 0)] <= 60 * 60000)
    ts, v, fi = ts[okf], v[okf], fi[okf]
    fac = np.maximum(DYN_MIN, (SP[fi] / SCORE_BASE) * DYN_MULT)       # (N,16)
    r = (v[:, None] / fac).astype(np.float64)                         # NaN neu thieu ung vien
    # KHOA SYMBOL: coin dang co vi the trong B0 (moi level) KHONG la ung vien (sim: isSymbolRunning) =>
    #   khong noteCandidate, khong pass. Khoa trong (start, end) theo phut (thoat xu ly truoc entry cung phut).
    mp = pd.read_csv(MAPF)
    id2s = dict(zip(mp.symId.astype(int), mp.symbol.astype(str).str.replace("USDT$", "", regex=True)))
    s2id = {s: i for i, s in id2s.items()}
    te = ((pd.to_datetime(b0["end"], format="%Y%m%d %H:%M") - TZ).astype("datetime64[ns]").astype("int64") // 10**6).to_numpy()
    nlock, unk = 0, 0
    SYf = SY[fi]
    for sym, s0, e0 in zip(b0["sym"].tolist(), b0["ms"].tolist(), te.tolist()):
        sid = s2id.get(sym)
        if sid is None:
            unk += 1
            continue
        a_, b_ = np.searchsorted(ts, s0, "right"), np.searchsorted(ts, e0, "left")
        if b_ <= a_:
            continue
        msk = SYf[a_:b_] == sid
        r[a_:b_][msk] = np.nan
        nlock += int(msk.sum())
    del SYf
    hold_ms = int(np.median(b0.loc[b0.level == "PREDICT_SYMBOL_TRADE", "time_order"].to_numpy(float)) * H)
    valid = np.isfinite(r)
    hid = ts // H
    hu, hst = np.unique(hid, return_index=True)
    hend = np.append(hst[1:], len(ts))
    htop, hcnt = [], np.zeros(len(hu), np.int64)
    for i in range(len(hu)):
        x = r[hst[i]:hend[i]][valid[hst[i]:hend[i]]]
        hcnt[i] = len(x)
        if len(x) > TOPB:
            x = np.partition(x, len(x) - TOPB)[len(x) - TOPB:]
        htop.append(x)
    hcum = np.concatenate([[0], np.cumsum(hcnt)])
    hms = hu * H
    dkey = hms // D
    du, dst = np.unique(dkey, return_index=True)
    dend = np.append(dst[1:], len(hu))
    dtop = []
    for i in range(len(du)):
        x = np.concatenate(htop[dst[i]:dend[i]])
        if len(x) > TOPB:
            x = np.partition(x, len(x) - TOPB)[len(x) - TOPB:]
        dtop.append(x)
    first = int(ts[0]); warm_end = first + 7 * D
    MULTS = [1, 2, 3, 5]
    thr = np.full((len(hu), len(MULTS)), np.inf)
    for i in range(len(hu)):
        h = int(hms[i])
        if h < warm_end:
            thr[i, :] = 0.008 * 1.55          # fallback base (thr = 0.008*factor*gs => r >= 0.0124)
            continue
        lo = int(np.searchsorted(hms, h - 90 * D, "left"))
        m = int(hcum[i] - hcum[lo])
        if m < 1000:
            continue
        # khoi: ngay TRON nam trong [lo, i) dung dtop; gio le dung htop
        d_lo = int(np.searchsorted(du, (hms[lo] + D - 1) // D)) if hms[lo] % D else int(np.searchsorted(du, hms[lo] // D))
        d_hi = int(np.searchsorted(du, h // D))            # ngay hien tai (chua tron) loai
        parts = []
        if d_hi > d_lo:
            parts += dtop[d_lo:d_hi]
            h_a = int(dst[d_lo]); h_b = int(dend[d_hi - 1]) if d_hi - 1 < len(dend) else i
            parts += htop[lo:h_a] + htop[h_b:i]
        else:
            parts += htop[lo:i]
        x = np.concatenate(parts)
        for jm, mu in enumerate(MULTS):
            pct = 1.0 - mu * RHO
            k = int(math.floor(pct * (m - 1)))
            j = m - 1 - k
            assert j < len(x)
            thr[i, jm] = -np.partition(-x, j)[j]
    hidx = np.searchsorted(hu, hid)
    selb = b0[b0.level == "PREDICT_SYMBOL_TRADE"]
    b0_pairs = set(zip(selb["ms"].tolist(), selb["sym"].tolist()))
    b0_min = set(selb["ms"].tolist())
    b0_days = set(b0["day"])
    out = {"n_minutes": int(len(ts)), "n_ts15": int(len(T15)), "cand_values": int(hcum[-1]),
           "cand_per_min": round(float(hcum[-1] / len(ts)), 2), "warm_end_ms": warm_end, "levels": {},
           "b0_lock_cells": nlock, "b0_sym_unmapped": unk, "hold_ms_synth": hold_ms}
    prev = None; prev_days = None
    for jm, mu in enumerate(MULTS):
        pm = r >= thr[hidx, jm][:, None]
        rows, cols = np.where(pm)
        raw_pass = int(len(rows))
        # khoa tong hop: pass cua coin vua vao (gia lap) bi khoa hold_ms (median giu lenh selector B0)
        lk = {}
        keep_i = []
        for ii, (rw, cl) in enumerate(zip(rows.tolist(), cols.tolist())):
            sid = int(SY[fi[rw], cl]); t = int(ts[rw])
            if lk.get(sid, -1) > t:
                continue
            lk[sid] = t + hold_ms
            keep_i.append(ii)
        rows, cols = rows[keep_i], cols[keep_i]
        pms = ts[rows]
        psy = [id2s.get(int(s), "?") for s in SY[fi[rows], cols]]
        pairs = set(zip(pms.tolist(), psy))
        pmin = np.unique(pms)
        pdays = day7(pmin); dset = set(pdays)
        L = {"pct": 1.0 - mu * RHO, "raw_pass_unlocked_by_b0": raw_pass, "entries_synth_lock": int(len(rows)),
             "cand_pass": int(len(rows)), "pass_minutes": int(len(pmin)),
             "pass_days": int(len(dset)), "weeks": int(len(set(pd.Series(pdays).dt.to_period("W")))),
             "days_by_year": {int(k): int(g.nunique()) for k, g in pd.Series(pdays).groupby(pd.Series(pdays).dt.year)},
             "pass_by_year": {int(k): int(c) for k, c in zip(*np.unique(day7(pms).year, return_counts=True))},
             "gap_pass_minutes_h": q(gaps_h(pmin)), "bursts_60m": int(len(bursts(pmin))),
             "gap_bursts_h": q(gaps_h(bursts(pmin))),
             "recall_b0_sel_pair": round(len(b0_pairs & pairs) / len(b0_pairs), 3),
             "recall_b0_sel_minute": round(len(b0_min & set(pmin.tolist())) / len(b0_min), 3),
             "recall_b0_sel_day": round(len(set(selb["day"]) & dset) / selb["day"].nunique(), 3),
             "frac_pass_days_b0_days": round(len(dset & b0_days) / max(1, len(dset)), 3),
             "cand_pass_per_pass_day": q(pd.Series(day7(pms)).value_counts().values)}
        if prev is not None:
            new = pairs - prev
            nms = np.array([p[0] for p in new], np.int64)
            nd = pd.Series(day7(nms))
            L["new_cand_pass"] = int(len(new))
            L["new_frac_on_b0_day"] = round(float(nd.isin(b0_days).mean()), 3)
            L["new_frac_on_x1_day"] = round(float(nd.isin(prev_days).mean()), 3)
            L["new_days_not_b0"] = int(len(set(nd) - b0_days))
            L["new_days_not_b0_by_year"] = {int(k): int(g.nunique()) for k, g in
                                            nd[~nd.isin(b0_days)].groupby(nd[~nd.isin(b0_days)].dt.year)}
        else:
            prev, prev_days = pairs, dset
        out["levels"][f"x{mu}"] = L
        print(f"[gaterep] x{mu}: cand_pass {L['cand_pass']} min {L['pass_minutes']} days {L['pass_days']} weeks {L['weeks']} "
              f"recall pair/min/day {L['recall_b0_sel_pair']}/{L['recall_b0_sel_minute']}/{L['recall_b0_sel_day']} "
              f"gap_h {L['gap_pass_minutes_h']} " + (f"new {L.get('new_cand_pass')} on_b0day {L.get('new_frac_on_b0_day')} newdays {L.get('new_days_not_b0')}" if mu > 1 else ""))
    R["gaterep"] = out


def main():
    cache_d = {}
    def cache(t):
        if t not in cache_d:
            cache_d[t] = load_pd(t)
        return cache_d[t]
    b0, hb = cache(B0)
    assert hb == B0_MD5, hb
    R["meta"]["b0_md5"] = hb
    assert len(b0) == 2517, len(b0)
    stages = sys.argv[2].split(",") if len(sys.argv) > 2 else ["ticks", "pairs", "gatelog", "proxy", "dip", "gaterep"]
    if "ticks" in stages: stage_ticks(b0)
    if "pairs" in stages: stage_pairs(cache)
    if "gatelog" in stages: stage_gatelog()
    if "proxy" in stages: stage_proxy(b0)
    if "dip" in stages: stage_dip(b0)
    if "gaterep" in stages: stage_gaterep(b0)
    with open(JOUT, "w") as f:
        json.dump(R, f, indent=1, ensure_ascii=False, default=str)
    print("wrote", JOUT, md5(JOUT))


if __name__ == "__main__":
    main()
