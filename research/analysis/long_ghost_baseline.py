#!/usr/bin/env python3
"""AUDIT LONG_GHOST_BASELINE (2026-10-03) — 0-sim, chi doc artifact co san. Thuan Python offline tren Oracle.

L0  symbol "ma" (gio/phut settle vol=0 sau last_real_ts, lineage data/meta/symbol_lineage_v2.csv):
    scan   : ticker 1m (kaggle_data_hpo/daily == Kaggle wfo-ticker-*, byte-identical) -> dem symbol-phut ma theo nam,
             ty le ma trong universe tung phut; dong thoi tra nen quyet dinh (open/close/vol) cho moi leg cua 5 cau hinh
             (phuc vu leg-ma + uoc crash-penalty bar_ret<=-1%, dinh nghia y het SimulatorMarketLevelTicker1MStopLoss:1390)
    ghost  : lenh sim vao/giu symbol SAU last_real_ts (printDone 5 cau hinh)
    label  : cand_dev_x1 (nhan retEnd/maxFav 72h) dong ma theo fold; rank-IC S1 (pred_s1a2x1) giu vs loai dong ma;
             CLOSES_1H v1 vs v2 (fwd 4/24/72h)
L5  cham lai chuoi T170 -> R0(B*) -> R4 -> G2 -> B0 bang thuoc dung:
    mtm    : maxDD MTM phut (reset_rule_score.run_mtm, cua so toan ky + 2022+), T170 hieu chinh phi 0,8% -> 0,1116%
    l5     : CAGR/maxDD/Calmar_MTM/Sharpe/vol/exposure/beta, theo nam, n/nam, Sum notional, %PnL 0h, crash-leg;
             paired circular block-10d bootstrap return NGAY vs B0 (NREP 2000, seed 20260905), raw va CUNG EXPOSURE (B0 x c,
             c CHOT tu exposure TB truoc khi so Calmar)
Usage: python3 long_ghost_baseline.py {scan,ghost,label,pb,mtm,l5,extra|all} [--workers 3]
pb     : nhan .pb ds_label15m (nguon S1/G015) dong ma / cua so cat ngay chet
extra  : leg index/stable, 24h truoc chet, mo hinh slippage $co-dinh & sqrt-impact, sanity BTC
"""
import argparse, gzip, hashlib, json, logging, math, os, sys, time
from multiprocessing import Pool
import numpy as np, pandas as pd

REPO = "/home/ubuntu/src/BinanceFuturesJava"
sys.path.insert(0, os.path.join(REPO, "research/analysis"))
import reset_rule_score as R  # noqa: E402
import jbin  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("lgb")
WORK = "/home/ubuntu/claude_master/1003/lgb"
os.makedirs(WORK, exist_ok=True)
LIN = os.path.join(REPO, "data/meta/symbol_lineage_v2.csv")
TICK = "/home/ubuntu/kaggle_data_hpo"
KOUT = "/home/ubuntu/kaggle_sim/out"
CAND = "/home/ubuntu/ledger/cand_dev_x1.parquet"
PRED = "/home/ubuntu/ledger/pred_s1a2x1.parquet"
V1, V2 = "/home/ubuntu/java/fsrun/CLOSES_1H.bin", "/home/ubuntu/java/fsrun/CLOSES_1H_v2.bin"
TZ = pd.Timedelta(hours=7)
MIN = 60000
DEV_END = pd.Timestamp("2026-01-01")
C_TRUE = 0.001116           # phi thuc/vong do nguoc tren 2517 lenh B0 (AUDIT_G2FLAT3 Q5)
SEED, NREP, BL = 20260905, 2000, 10
CFG = {  # ten -> (tag Kaggle, md5 printDone ky vong hoac None)
    "T170": ("t170-x1-2021", None),
    "R0": ("p2-r0-base", "d297ce6b"),
    "R4": ("p2-r4-base", "06fd6e9a"),
    "G2": ("gdv2-g2", "853aaa08"),
    "B0": ("de-p1", "650c386f"),
}
ORDER = ["T170", "R0", "R4", "G2", "B0"]
PEN = (0.0069, 0.0150)


def jdump(o, name):
    p = os.path.join(WORK, name)
    json.dump(o, open(p, "w"), indent=1, default=lambda x: float(x) if isinstance(x, (np.floating, np.integer)) else str(x))
    log.info("wrote %s", p)


def lineage():
    L = pd.read_csv(LIN)
    L["last_ms"] = pd.to_datetime(L.last_real_ts).astype("int64") // 10**6
    L["first_ms"] = pd.to_datetime(L.first_real_ts).astype("int64") // 10**6
    # con song toi het DEV <=> last_real >= 2025-12-31 23:00
    L["dead_in_dev"] = L.last_ms < int(pd.Timestamp("2025-12-31 23:00").value // 10**6)
    return L


def md5(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 20), b""):
            h.update(ch)
    return h.hexdigest()


def legs(name):
    tag = CFG[name][0]
    d = R.load_legs(tag)
    d["tsu"] = d.ts - TZ
    d["teu"] = d.te - TZ
    d["m0"] = d.tsu.astype("int64") // 10**6
    d["m1"] = d.teu.astype("int64") // 10**6
    return d


# ======================================================================= scan (ticker)
_G = {}


def _init(lin, q):
    _G["lin"], _G["q"] = lin, q


def _scan_day(day):
    p = os.path.join(TICK, "ticker_%s.bin.gz" % day)
    if not os.path.exists(p):
        return day, None
    lin = _G["lin"]
    t0 = int(pd.Timestamp(day).value // 10**6)
    qd = _G["q"].get(day, {})            # minute_ms -> list[(cfg, idx, sym)]
    per = {}                             # sym -> [n, vol0, ghost, ghost_vol0, ghost_volpos]
    ms_tot, ms_gh, ms_n = 0, 0, 0
    gmax = 0
    ans = []
    with gzip.open(p, "rb") as f:
        b = f.read()
    for k, v in jbin.iter_minutes(b):
        if k < t0 or k >= t0 + 1440 * MIN:
            continue
        ng = 0
        for s, tup in v.items():
            a = per.get(s)
            if a is None:
                a = per[s] = [0, 0, 0, 0, 0]
            vz = tup[5] == 0
            a[0] += 1
            if vz:
                a[1] += 1
            lm = lin.get(s)
            if lm is not None and k > lm:
                ng += 1
                a[2] += 1
                if vz:
                    a[3] += 1
                else:
                    a[4] += 1
        ms_tot += len(v); ms_gh += ng; ms_n += 1
        gmax = max(gmax, ng)
        for (cfg, idx, sym) in qd.get(k, ()):
            tup = v.get(sym + "USDT")
            ans.append((cfg, idx, None if tup is None else (tup[4], tup[3], tup[5])))   # open, close, vol
    return day, dict(per=per, ms_tot=ms_tot, ms_gh=ms_gh, ms_n=ms_n, gmax=gmax, ans=ans)


def stage_scan(workers):
    L = lineage()
    lin = dict(zip(L.symbol, L.last_ms))
    q = {}
    for name in ORDER:
        d = legs(name)
        for i, (s, m) in enumerate(zip(d.sym, d.m0)):
            day = pd.Timestamp(int(m), unit="ms").strftime("%Y%m%d")
            q.setdefault(day, {}).setdefault(int(m), []).append((name, i, s))
    days = [x.strftime("%Y%m%d") for x in pd.date_range("2021-01-01", "2025-12-31", freq="D")]
    if os.environ.get("LGB_SMOKE"):
        days = [x for x in days if x[:6] in ("202505", "202110")][:int(os.environ["LGB_SMOKE"])]
    yr = {}
    persym = {}
    daily_share = {}
    ans = {n: {} for n in ORDER}
    missing = []
    t00 = time.time()
    with Pool(workers, initializer=_init, initargs=(lin, q)) as pool:
        for j, (day, r) in enumerate(pool.imap_unordered(_scan_day, days, chunksize=4)):
            if r is None:
                missing.append(day); continue
            y = day[:4]
            Y = yr.setdefault(y, dict(sym_min=0, vol0=0, ghost=0, ghost_vol0=0, ghost_volpos=0, minutes=0, days=0,
                                      ghost_sym_max_minute=0))
            Y["days"] += 1; Y["minutes"] += r["ms_n"]; Y["ghost_sym_max_minute"] = max(Y["ghost_sym_max_minute"], r["gmax"])
            for s, a in r["per"].items():
                Y["sym_min"] += a[0]; Y["vol0"] += a[1]; Y["ghost"] += a[2]; Y["ghost_vol0"] += a[3]; Y["ghost_volpos"] += a[4]
                P = persym.setdefault(s, [0, 0, 0, 0, 0])
                for i in range(5):
                    P[i] += a[i]
            daily_share[day] = (r["ms_gh"] / r["ms_tot"]) if r["ms_tot"] else 0.0
            for (cfg, idx, val) in r["ans"]:
                ans[cfg][idx] = val
            if j % 100 == 0:
                log.info("scan %d/%d %.0fs", j, len(days), time.time() - t00)
    for y, Y in yr.items():
        Y["ghost_share_symmin_pct"] = 100.0 * Y["ghost"] / Y["sym_min"]
        Y["vol0_share_pct"] = 100.0 * Y["vol0"] / Y["sym_min"]
        ds = [v for k, v in daily_share.items() if k[:4] == y]
        Y["ghost_share_universe_daily_mean_pct"] = 100.0 * float(np.mean(ds))
        Y["ghost_share_universe_daily_max_pct"] = 100.0 * float(np.max(ds))
    ghost_syms = {s: dict(sym_min=a[0], ghost=a[2], ghost_vol0=a[3], ghost_volpos=a[4]) for s, a in persym.items() if a[2] > 0}
    nolin = sorted(s for s in persym if s not in lin)
    out = dict(years=yr, n_days=len(days) - len(missing), missing_days=missing, n_sym_ticker=len(persym),
               n_sym_with_ghost_min=len(ghost_syms), ghost_syms=ghost_syms, sym_not_in_lineage=nolin,
               daily_ghost_share={k: daily_share[k] for k in sorted(daily_share)},
               secs=time.time() - t00)
    jdump(out, "scan.json")
    pd.to_pickle(ans, os.path.join(WORK, "legbars.pkl"))


# ======================================================================= ghost trades
def stage_ghost():
    L = lineage().set_index("symbol")
    bars = pd.read_pickle(os.path.join(WORK, "legbars.pkl"))
    out = {}
    for name in ORDER:
        tag = CFG[name][0]
        d = legs(name)
        key = d.sym + "USDT"
        d["last_ms"] = key.map(L.last_ms.where(L.dead_in_dev, np.inf))
        d["status_lin"] = key.map(L.status)
        nolin = int((~key.isin(L.index)).sum())
        lm = d.last_ms.fillna(np.inf)
        d["g_entry"] = d.m0 > lm                       # vao SAU phut that cuoi
        d["g_hold"] = (d.m0 <= lm) & (d.m1 > lm)        # dang giu khi hop dong ngung
        d["near7"] = (lm - d.m0 <= 7 * 86400000) & (lm - d.m0 >= 0) & L.reindex(key).dead_in_dev.fillna(False).values
        last_day = d.te.max()
        d["stuck_end"] = d.te >= last_day - pd.Timedelta(hours=1)
        fee = R.LEGACY if name == "T170" else C_TRUE
        # bar quyet dinh (startTime == start): validate gia vao == close nen
        b = bars.get(name, {})
        o = np.array([b.get(i, None)[0] if b.get(i) else np.nan for i in range(len(d))], float)
        c = np.array([b.get(i, None)[1] if b.get(i) else np.nan for i in range(len(d))], float)
        v = np.array([b.get(i, None)[2] if b.get(i) else np.nan for i in range(len(d))], float)
        d["bar_ret"] = (c - o) / o
        d["bar_vol"] = v
        match = np.abs(c / d.entry.values - 1) < 2e-4
        def summ(m):
            x = d[m]
            return dict(n=int(len(x)), pnl=float(x.pnl.sum()), notional=float(x.notional.sum()),
                        fee_est=float(x.notional.sum() * fee), syms=sorted(x.sym.unique().tolist())[:30],
                        rows=[(r.sym, str(r.ts), str(r.te), r.status, round(float(r.pnl), 1), r.status_lin)
                              for r in x.head(15).itertuples()])
        # implied cost (kiem phi T170 0,8%)
        imp = ((d.quantity * (d.tp - d.entry) - d.pnl - d.funding) / d.notional).replace([np.inf, -np.inf], np.nan)
        out[name] = dict(tag=tag, md5=md5(os.path.join(KOUT, tag, "storage/printDone.csv")), n=int(len(d)),
                         no_lineage=nolin, implied_cost_median=float(imp.median()),
                         implied_cost_p5_p95=[float(imp.quantile(.05)), float(imp.quantile(.95))],
                         ghost_entry=summ(d.g_entry), ghost_hold=summ(d.g_hold), near_death_7d=summ(d.near7),
                         stuck_end=summ(d.stuck_end), stuck_end_ghost=summ(d.stuck_end & (d.g_entry | d.g_hold)),
                         bar_found=int(np.isfinite(c).sum()), bar_entry_match=int(match.sum()),
                         bar_vol0=int((v == 0).sum()), sum_pnl=float(d.pnl.sum()))
        log.info("%s n=%d ghost_entry=%d ghost_hold=%d near7=%d stuck=%d match=%d/%d nolin=%d imp=%.5f", name, len(d),
                 d.g_entry.sum(), d.g_hold.sum(), d.near7.sum(), d.stuck_end.sum(), match.sum(), len(d), nolin, imp.median())
        d.to_pickle(os.path.join(WORK, "legs_%s.pkl" % name))
    jdump(out, "ghost.json")


# ======================================================================= label / selector
def _ic(df, f, r, min_n=10):
    d = df[["ts", f, r]].dropna()
    d = d.assign(cf=d.groupby("ts")[f].rank(), cr=d.groupby("ts")[r].rank())
    d["cf"] -= d.groupby("ts").cf.transform("mean"); d["cr"] -= d.groupby("ts").cr.transform("mean")
    g = d.assign(cov=d.cf * d.cr, vf=d.cf ** 2, vr=d.cr ** 2).groupby("ts").agg(cov=("cov", "sum"), vf=("vf", "sum"),
                                                                                  vr=("vr", "sum"), n=("cf", "size"))
    g = g[(g.n >= min_n) & (g.vf > 0) & (g.vr > 0)]
    return g["cov"] / np.sqrt(g.vf * g.vr)


def _bci(s, blk_h=72, infl=1.0):
    s = s.dropna()
    if len(s) == 0:
        return dict(mean=float("nan"))
    blk = (s.index.values // (blk_h * 3600000))
    gb = s.groupby(blk).mean(); cn = s.groupby(blk).size()
    rng = np.random.default_rng(SEED)
    bv, cv = gb.values, cn.values
    dr = np.empty(NREP)
    for i in range(NREP):
        p = rng.integers(0, len(bv), len(bv))
        dr[i] = (bv[p] * cv[p]).sum() / cv[p].sum()
    lo, hi = np.percentile(dr, [2.5, 97.5]); m = float(s.mean())
    return dict(mean=m, lo=float(m - (m - lo) * infl), hi=float(m + (hi - m) * infl), n_ts=int(len(s)), K=int(len(bv)))


def stage_label():
    L = lineage()
    lastm = dict(zip(L.symId, L.last_ms)); dead = dict(zip(L.symId, L.dead_in_dev))
    # last_real cua mã con song bi kiem duyet tai het DEV -> chi tinh ma/partial cho ma CHET trong DEV
    lastm = {k: (v if dead[k] else np.inf) for k, v in lastm.items()}
    out = {}
    c = pd.read_parquet(CAND, columns=["ts", "sym", "retEnd_72h", "maxFav_72h", "maxAdv_72h", "nBars_72h", "p15"])
    c["last_ms"] = c.sym.map(lastm)
    out["cand_rows"] = int(len(c)); out["cand_no_lineage"] = int(c.last_ms.isna().sum())
    lm = c.last_ms.fillna(np.inf)
    c["g_full"] = c.ts > lm                         # quyet dinh SAU phut that cuoi
    c["g_part"] = (c.ts <= lm) & (c.ts + 72 * 3600000 > lm)   # cua so nhan 72h cat qua ngay chet
    c["q"] = (pd.to_datetime(c.ts, unit="ms") + TZ).dt.to_period("Q").astype(str)
    c["y"] = c.q.str[:4]
    gs = c.groupby("q").agg(n=("ts", "size"), full=("g_full", "sum"), part=("g_part", "sum"))
    gs["full_pct"] = 100 * gs.full / gs.n; gs["part_pct"] = 100 * gs.part / gs.n
    out["cand_by_quarter"] = gs.reset_index().to_dict("records")
    gy = c.groupby("y").agg(n=("ts", "size"), full=("g_full", "sum"), part=("g_part", "sum"))
    out["cand_by_year"] = gy.reset_index().to_dict("records")
    gf = c[c.g_full]
    out["cand_ghost_label"] = dict(n=int(len(gf)), ret0_frac=float((gf.retEnd_72h.abs() < 1e-9).mean()) if len(gf) else None,
                                   maxfav0_frac=float((gf.maxFav_72h.abs() < 1e-9).mean()) if len(gf) else None,
                                   nbars_med=float(gf.nBars_72h.median()) if len(gf) else None,
                                   syms=sorted(L.set_index("symId").reindex(gf.sym.unique()).symbol.dropna().tolist()),
                                   ret_all_mean=float(c.retEnd_72h.mean()), ret_ghost_mean=float(gf.retEnd_72h.mean()) if len(gf) else None,
                                   pos015_all=float((c.retEnd_72h > 0.015).mean()),
                                   pos015_ghost=float((gf.retEnd_72h > 0.015).mean()) if len(gf) else None)
    # train set theo cutoff quy (expanding, purge 72h) - % dong ma trong train
    cuts = pd.date_range("2022-01-01", "2025-10-01", freq="QS")
    tr = []
    ts_local = pd.to_datetime(c.ts, unit="ms") + TZ
    for cu in cuts:
        m = ts_local < cu - pd.Timedelta(hours=72)
        tr.append(dict(cutoff=str(cu.date()), n_train=int(m.sum()), full=int((m & c.g_full).sum()),
                       part=int((m & c.g_part).sum()), full_pct=100 * float((m & c.g_full).sum()) / max(1, int(m.sum())),
                       part_pct=100 * float((m & c.g_part).sum()) / max(1, int(m.sum()))))
    out["train_by_cutoff"] = tr
    # ---- S1 pred panel x nhan cand
    p = pd.read_parquet(PRED)
    p["last_ms"] = p.sym.map(lastm)
    plm = p.last_ms.fillna(np.inf)
    p["g_full"] = p.ts > plm
    p["g_part"] = (p.ts <= plm) & (p.ts + 72 * 3600000 > plm)
    p["y"] = (pd.to_datetime(p.ts, unit="ms") + TZ).dt.year
    out["pred_rows"] = int(len(p)); out["pred_full"] = int(p.g_full.sum()); out["pred_part"] = int(p.g_part.sum())
    out["pred_by_year"] = p.groupby("y").agg(n=("ts", "size"), full=("g_full", "sum"), part=("g_part", "sum")).reset_index().to_dict("records")
    # top-K chua dong ma? (score THAP = tot)
    p["rk"] = p.groupby("ts").score.rank(method="first")
    for K in (8, 16):
        out["pred_topk%d_full" % K] = int((p.g_full & (p.rk <= K)).sum())
        out["pred_topk%d_part" % K] = int((p.g_part & (p.rk <= K)).sum())
    j = p.merge(c[["ts", "sym", "retEnd_72h", "maxFav_72h"]], on=["ts", "sym"], how="left")
    out["pred_label_join"] = int(j.retEnd_72h.notna().sum())
    j["s1"] = -j.score
    ic = {}
    for lab in ("retEnd_72h", "maxFav_72h"):
        keep = _ic(j, "s1", lab)
        dfull = _ic(j[~j.g_full], "s1", lab)
        dall = _ic(j[~(j.g_full | j.g_part)], "s1", lab)
        res = {}
        for nm, s in (("keep", keep), ("drop_full", dfull), ("drop_full_part", dall)):
            res[nm] = _bci(s, infl=1.21)
            yy = (pd.to_datetime(s.index, unit="ms") + TZ).year
            res[nm]["by_year"] = {int(k): float(v) for k, v in s.groupby(yy).mean().items()}
        for nm, s in (("drop_full", dfull), ("drop_full_part", dall)):
            dd = (s - keep).dropna()
            res["diff_" + nm] = _bci(dd, infl=1.21)
            res["diff_" + nm]["n_ts_changed"] = int((dd.abs() > 1e-12).sum())
        ic[lab] = res
    out["s1_ic_cand"] = ic
    jdump(out, "label_part1.json")
    del c, j
    # ---- CLOSES_1H v1 vs v2: fwd 4/24/72h, S1 asof (trend_rank_ic)
    import trend_rank_ic as T
    T.HORIZONS = (4, 24, 72)
    res2 = {}
    for nm, path in (("v1", V1), ("v2", V2)):
        T.CLOSES = path
        df = T.load_closes()
        df = df[np.isfinite(df.close)].reset_index(drop=True) if nm == "v2" else df
        df = T.add_forward(df)
        df = T.add_s1(df)
        df = df[(df.ctime <= T.DECISION_MAX) & df.s1.notna()]
        r = {}
        for h in T.HORIZONS:
            s = T._ic_series(df, "s1", "ret%d" % h)
            r["h%d" % h] = T.block_ci(s)
            yy = pd.to_datetime(s.index, unit="ms").year
            r["h%d" % h]["by_year"] = {int(k): float(v) for k, v in s.groupby(yy).mean().items()}
            r["h%d_series" % h] = s
        r["n_rows"] = int(len(df))
        res2[nm] = r
        del df
    out2 = {}
    for h in (4, 24, 72):
        a, b = res2["v1"]["h%d_series" % h], res2["v2"]["h%d_series" % h]
        dd = (b - a).dropna()
        out2["h%d" % h] = dict(v1=res2["v1"]["h%d" % h], v2=res2["v2"]["h%d" % h], diff_v2_minus_v1=T.block_ci(dd),
                               n_snap_changed=int((dd.abs() > 1e-12).sum()))
    out2["n_rows_v1"], out2["n_rows_v2"] = res2["v1"]["n_rows"], res2["v2"]["n_rows"]
    out["s1_ic_closes"] = out2
    jdump(out, "label.json")



# ======================================================================= .pb nhan 15m (ds_label15m, nguon bins S1/G015)
def stage_pb():
    import glob
    sys.path.insert(0, "/home/ubuntu/sel1m_code")
    import funding_label_pb as FLPB
    L = lineage()
    lastm = {s_: (v if dd else np.inf) for s_, v, dd in zip(L.symbol, L.last_ms, L.dead_in_dev)}
    fs = sorted(f for f in glob.glob("/home/ubuntu/ds_label15m/funding_label_*.pb") if ".part" not in f)
    want = ["tEpochMs", "symbol", "retEnd_4h", "nBars_4h", "maxFav_4h", "retEnd_72h", "maxFav_72h", "nBars_72h"]
    rows = []
    for fp in fs:
        try:
            d = FLPB.read_label(fp, usecols=want)
        except Exception as e:  # cot thieu -> doc het roi loc
            log.info("pb %s usecols loi %s -> doc het", fp, e)
            d = FLPB.read_label(fp)
        d = d[d.tEpochMs < int(DEV_END.value // 10**6)]
        if len(d) == 0:
            continue
        lm = d.symbol.map(lastm)
        nolin = lm.isna() & ~d.symbol.isin(L.symbol)
        lmf = lm.fillna(np.inf)
        full = d.tEpochMs > lmf
        part4 = (d.tEpochMs <= lmf) & (d.tEpochMs + 4 * 3600000 > lmf)
        part72 = (d.tEpochMs <= lmf) & (d.tEpochMs + 72 * 3600000 > lmf)
        ok4 = (d.get("nBars_4h", pd.Series(0, index=d.index)) >= 16) & d.get("retEnd_4h", pd.Series(np.nan, index=d.index)).notna()
        ok72 = d.get("retEnd_72h", pd.Series(np.nan, index=d.index)).notna()
        r = dict(file=os.path.basename(fp), n=int(len(d)), no_lineage=int(nolin.sum()),
                 no_lineage_syms=int(d.symbol[nolin].nunique()), full=int(full.sum()), full_ok4=int((full & ok4).sum()),
                 full_ok72=int((full & ok72).sum()), part4=int(part4.sum()), part72=int(part72.sum()), ok4=int(ok4.sum()))
        if full.any() and "retEnd_4h" in d:
            g = d[full & ok4]
            r["full_ret4_zero_frac"] = float((g.retEnd_4h.abs() < 1e-9).mean()) if len(g) else None
            r["full_pos015_4h"] = float((g.retEnd_4h > 0.015).mean()) if len(g) else None
            r["all_pos015_4h"] = float((d.retEnd_4h[ok4] > 0.015).mean())
            r["full_syms"] = int(g.symbol.nunique())
        rows.append(r)
        log.info("pb %s", r)
        del d
    tot = {k: int(sum(r.get(k, 0) for r in rows)) for k in ("n", "no_lineage", "full", "full_ok4", "full_ok72", "part4", "part72", "ok4")}
    jdump(dict(files=rows, total=tot, cols=want), "pb.json")

# ======================================================================= MTM phut
def stage_mtm(workers):
    import feat_add_v1_score  # noqa: F401  (MTMState cua so 2022+)
    R.MTM_COSTS = {"asis": R.LEGACY, "c0111": C_TRUE}
    L = {n: R.load_legs(CFG[n][0]) for n in ORDER}
    res = R.run_mtm(L, workers=workers, chunk=30)
    jdump(res, "mtm.json")


# ======================================================================= L5
def hourly_expo(d):
    h0 = pd.Timestamp("2021-07-01"); nh = int((pd.Timestamp("2026-01-01") - h0) / pd.Timedelta(hours=1))
    ex = np.zeros(nh + 1)
    s = ((d.ts - h0) / pd.Timedelta(hours=1)).astype(int).clip(0, nh).values
    e = ((d.te - h0) / pd.Timedelta(hours=1)).astype(int).clip(0, nh).values
    np.add.at(ex, s, d.notional.values); np.add.at(ex, e, -d.notional.values)
    ex = np.cumsum(ex)[:nh]
    return pd.Series(ex, pd.date_range(h0, periods=nh, freq="h")).resample("D").mean()


def eqstats(eq, expo=None):
    eq = eq.astype(float); r = eq.pct_change().dropna()
    yrs = (eq.index[-1] - eq.index[0]).days / 365.25
    cagr = ((eq.iloc[-1] / eq.iloc[0]) ** (1 / yrs) - 1) * 100
    dd = (eq / eq.cummax() - 1) * 100
    uw = eq < eq.cummax(); uwmax = int(uw.groupby((~uw).cumsum()).sum().max())
    o = dict(cagr=float(cagr), maxdd_daily=float(dd.min()), calmar_daily=float(cagr / abs(dd.min())), uw_daily=uwmax,
             sharpe=float(r.mean() / r.std() * math.sqrt(365)), vol_ann=float(r.std() * math.sqrt(365) * 100),
             final=float(eq.iloc[-1]), start=float(eq.iloc[0]))
    if expo is not None:
        x = expo.reindex(eq.index).fillna(0) / eq.shift(1).bfill()
        o.update(expo_mean=float(x.mean()), expo_max=float(x.max()))
    return o


def cal_of(r):
    eq = np.cumprod(1 + r); yrs = len(r) / 365.25
    cagr = (eq[-1] ** (1 / yrs) - 1) * 100
    pk = np.maximum.accumulate(np.concatenate(([1.0], eq)))[1:]
    mdd = ((eq / pk - 1) * 100).min()
    sh = r.mean() / r.std() * math.sqrt(365)
    return (cagr / abs(mdd) if mdd < 0 else np.nan), cagr, mdd, sh, r.std() * math.sqrt(365) * 100


INFL3 = math.sqrt(2.0 * math.log(3))   # 1,4823: inflate CI k=3 (RESULT_PNL_RULER)
SLIPS = (0.003, 0.007, 0.014)


def btc_daily(index):
    """close BTC 1h (CLOSES_1H v2) -> close cuoi ngay gio VN, reindex theo ngay equity."""
    L = lineage()
    bid = int(L.loc[L.symbol == "BTCUSDT", "symId"].iloc[0])
    DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("c", ">f4")])
    a = np.fromfile(V2, dtype=DT)
    m = (a["sym"].astype(np.int64) == bid) & np.isfinite(a["c"].astype(float))
    s = pd.Series(a["c"][m].astype(float), index=pd.to_datetime(a["ts"][m].astype(np.int64) + 3600000, unit="ms") + TZ)
    del a
    s = s[~s.index.duplicated()].sort_index()
    return s.resample("D").last().reindex(index).ffill()


def episodes_top(d, pnl, k=5):
    """episode = cum ngay dong lenh (te) noi khoang trong <= 2 ngay (dinh nghia reset_rule_score.episode_drop3)."""
    ted = d.te.dt.normalize()
    u = np.sort(ted.unique())
    if len(u) == 0:
        return dict(n_ep=0)
    gid = np.concatenate(([0], np.cumsum(np.diff(u) / np.timedelta64(1, "D") > 2)))
    mp = dict(zip(u, gid))
    sums = pd.Series(np.asarray(pnl, float)).groupby(ted.map(mp).values).sum().sort_values(ascending=False)
    tot = float(sums.sum())
    return dict(n_ep=int(len(sums)), top5_pnl=float(sums.iloc[:k].sum()), top5_share_pct=100 * float(sums.iloc[:k].sum()) / tot,
                top1_share_pct=100 * float(sums.iloc[0]) / tot, ex_top5_pnl=tot - float(sums.iloc[:k].sum()))


def ci_infl(obs, lo, hi, f=INFL3):
    return [float(obs - (obs - lo) * f), float(obs + (hi - obs) * f)]


def stage_l5():
    mt = json.load(open(os.path.join(WORK, "mtm.json")))
    D, Lg, EQ, EX, ST = {}, {}, {}, {}, {}
    # T170 = artifact phi cu 0,8%/vong (t170-x1-2021); T170c = cung lenh, hieu chinh phi ve 0,1116% (tuyen tinh, KHONG compound)
    # R0 = p2-r0-base: x1_gs_t170 + override DCA 1,1,1,1 / scale 6 / cap 15% @ fee 0,000982 -> KHONG phai T170 (DCA 1,1,3,8)
    names = ["T170", "T170c", "R0", "R4", "G2", "B0"]
    for n in ORDER:
        Lg[n] = pd.read_pickle(os.path.join(WORK, "legs_%s.pkl" % n))
        D[n] = R.load_daily(CFG[n][0])
    Lg["T170c"], D["T170c"] = Lg["T170"], D["T170"]
    days = None
    for n in names:
        e = R.daily_adj(Lg[n], D[n], C_TRUE) if n == "T170c" else D[n]["equity"].astype(float)
        EQ[n] = e
        days = e.index if days is None else days.intersection(e.index)
    for n in names:
        EQ[n] = EQ[n].loc[days]
        EX[n] = hourly_expo(Lg[n])
    out = dict(window=[str(days[0].date()), str(days[-1].date())], n_days=len(days), c_true=C_TRUE, infl_k3=INFL3)
    btc = btc_daily(days)
    rbtc = btc.pct_change().dropna()
    rb = EQ["B0"].pct_change().dropna()
    yrs = (days[-1] - days[0]).days / 365.25
    for n in names:
        d = Lg[n]
        s = eqstats(EQ[n], EX[n])
        mk = "c0111" if n == "T170c" else "asis"
        m = mt["T170" if n == "T170c" else n][mk]
        s["maxdd_mtm"] = m["dd_total"]; s["uw_mtm_days"] = m["uw_total_days"]
        s["calmar_mtm"] = s["cagr"] / abs(m["dd_total"])
        s["dd_mtm_year"] = m["dd_year"]; s["uw_mtm_year"] = m.get("uw_year")
        e22 = EQ[n][EQ[n].index >= "2021-12-31"]
        s22 = eqstats(e22)
        s["cagr_2022p"] = s22["cagr"]; s["maxdd_mtm_2022p"] = m["dd_win"]; s["calmar_mtm_2022p"] = s22["cagr"] / abs(m["dd_win"])
        s["uw_mtm_2022p_days"] = m.get("uw_win_days")
        ra = EQ[n].pct_change().dropna()
        s["beta_vs_B0"] = float(np.cov(ra, rb)[0, 1] / rb.var())
        s["corr_vs_B0"] = float(np.corrcoef(ra, rb)[0, 1])
        jb = pd.concat([ra, rbtc], axis=1, join="inner").dropna()
        s["beta_vs_BTC"] = float(np.cov(jb.iloc[:, 0], jb.iloc[:, 1])[0, 1] / jb.iloc[:, 1].var())
        s["corr_vs_BTC"] = float(jb.corr().iloc[0, 1])
        pnl = (d.pnl + (R.LEGACY - C_TRUE) * d.notional) if n == "T170c" else d.pnl
        s.update(n=int(len(d)), n_per_year=len(d) / yrs, sum_notional=float(d.notional.sum()),
                 notional_mean=float(d.notional.mean()), sum_pnl=float(pnl.sum()),
                 pnl_per_trade=float(pnl.mean()), pnl_per_notional_bp=1e4 * float(pnl.sum() / d.notional.sum()),
                 notional_over_pnl=float(d.notional.sum() / pnl.sum()), win_rate=float((pnl > 0).mean()))
        s["episodes"] = episodes_top(d, pnl)
        h0 = d.time_order <= 0
        s["pnl0h"] = float(pnl[h0].sum()); s["n0h"] = int(h0.sum()); s["share0h_pct"] = 100 * float(pnl[h0].sum()) / float(pnl.sum())
        cr = d.bar_ret <= -0.01
        s["crash_legs"] = int(cr.sum()); s["crash_legs_pct"] = 100 * float(cr.mean())
        s["crash_notional_share_pct"] = 100 * float(d.notional[cr].sum() / d.notional.sum())
        for p_ in PEN:
            dp = -p_ * float((d.notional[cr] + pnl[cr]).sum())
            s["pen%.4f_dPnL" % p_] = dp
            s["pen%.4f_dPnL_pct_sumpnl" % p_] = 100 * dp / float(pnl.sum())
        s["slip"] = {("%.3f" % sl): dict(dPnL=-sl * float(d.notional.sum()), pnl_after=float(pnl.sum()) - sl * float(d.notional.sum()),
                                          pct_sumpnl=-100 * sl * float(d.notional.sum()) / float(pnl.sum())) for sl in SLIPS}
        s["slip_zero_edge"] = float(pnl.sum() / d.notional.sum())   # s lam SumPnL = 0
        yy = {}
        for y in (2021, 2022, 2023, 2024, 2025):
            ey = EQ[n][(EQ[n].index >= "%d-12-31" % (y - 1)) & (EQ[n].index <= "%d-12-31" % y)]
            roi = (ey.iloc[-1] / ey.iloc[0] - 1) * 100
            ddy = float((ey / ey.cummax() - 1).min() * 100)
            ddm = m["dd_year"].get(str(y), float("nan"))
            dy = d[d.ts.dt.year == y]
            yy[y] = dict(roi=float(roi), dd_daily=ddy, dd_mtm=ddm, calmar_mtm=float(roi / abs(ddm)) if ddm else None,
                         n=int(len(dy)), notional=float(dy.notional.sum()), pnl=float(pnl[dy.index].sum()),
                         share0h_pct=100 * float(pnl[dy.index][dy.time_order <= 0].sum() / pnl[dy.index].sum()) if len(dy) else None)
        s["years"] = yy
        ST[n] = s
        log.info("%s cagr %.2f ddMTM %.2f calmar %.3f n %d expo %.3f betaBTC %.3f top5ep %.1f%%", n, s["cagr"], s["maxdd_mtm"],
                 s["calmar_mtm"], s["n"], s["expo_mean"], s["beta_vs_BTC"], s["episodes"]["top5_share_pct"])
    out["stats"] = ST
    # ---- slippage hoa von vs B0 (tuyen tinh): s* = (PnL_B0 - PnL_X) / (Not_B0 - Not_X)
    be = {}
    for n in names:
        if n == "B0":
            continue
        dp = ST["B0"]["sum_pnl"] - ST[n]["sum_pnl"]; dn = ST["B0"]["sum_notional"] - ST[n]["sum_notional"]
        be[n] = dict(dPnL_B0_minus_X=dp, dNotional_B0_minus_X=dn, s_breakeven=(dp / dn) if dn > 0 else None,
                     note="X vuot B0 khi slippage/vong > s_breakeven" if dn > 0 and dp > 0 else "xem dau")
    out["slip_breakeven_vs_B0"] = be
    # ---- c CHOT tu exposure TB (truoc khi so Calmar)
    C = {n: ST[n]["expo_mean"] / ST["B0"]["expo_mean"] for n in names if n != "B0"}
    out["c_locked_expo"] = C
    jdump(dict(c_locked_expo=C, note="chot truoc khi tinh bootstrap/Calmar cung exposure"), "c_locked.json")
    rbv = rb.values; nn = len(rbv)
    rng = np.random.default_rng(SEED)
    starts = [rng.integers(0, nn, size=int(math.ceil(nn / BL))) for _ in range(NREP)]
    IX = [(st[:, None] + np.arange(BL)[None, :]).ravel()[:nn] % nn for st in starts]
    lab = ["dCalmar", "dCAGR", "dMaxDD", "dSharpe", "dVol"]

    def pair(ra, rbase, c):
        obs = [a - b for a, b in zip(cal_of(ra), cal_of(c * rbase))]
        dr = np.array([[a - b for a, b in zip(cal_of(ra[ix]), cal_of(c * rbase[ix]))] for ix in IX])
        o = dict(c=float(c))
        for k, nm in enumerate(lab):
            lo, hi = [float(x) for x in np.nanpercentile(dr[:, k], [2.5, 97.5])]
            o[nm] = float(obs[k]); o[nm + "_ci"] = [lo, hi]; o[nm + "_ci_infl"] = ci_infl(obs[k], lo, hi)
            o[nm + "_p_gt0"] = float(np.nanmean(dr[:, k] > 0))
        return o
    BOOT = {}
    for n in names:
        if n == "B0":
            continue
        ra = EQ[n].pct_change().dropna().values
        BOOT[n] = {}
        for vn, c in (("raw", 1.0), ("same_expo", C[n])):
            o = pair(ra, rbv, c)
            b0c = cal_of(c * rbv)
            ddm_b0c = ST["B0"]["maxdd_mtm"] * b0c[2] / cal_of(rbv)[2]   # xap xi ddMTM(B0xc)
            o.update(B0c_cagr=float(b0c[1]), B0c_maxdd_daily=float(b0c[2]), B0c_calmar_mtm_approx=float(b0c[1] / abs(ddm_b0c)),
                     dCalmar_mtm_approx=float(ST[n]["calmar_mtm"] - b0c[1] / abs(ddm_b0c)))
            BOOT[n][vn] = o
            log.info("%s %s c=%.3f dCAGR %.2f %s dCalmar %.3f %s infl %s", n, vn, c, o["dCAGR"], o["dCAGR_ci"], o["dCalmar"],
                     o["dCalmar_ci"], o["dCalmar_ci_infl"])
        yo = {}
        for y in (2021, 2022, 2023, 2024, 2025):
            sel = (EQ[n].index[1:] >= "%d-01-01" % y) & (EQ[n].index[1:] <= "%d-12-31" % y)
            a = cal_of(ra[sel]); b1 = cal_of(rbv[sel]); bc = cal_of(C[n] * rbv[sel])
            yo[y] = dict(roi_x=float(np.prod(1 + ra[sel]) - 1) * 100, roi_b0=float(np.prod(1 + rbv[sel]) - 1) * 100,
                         roi_b0c=float(np.prod(1 + C[n] * rbv[sel]) - 1) * 100, dd_x=float(a[2]), dd_b0=float(b1[2]), dd_b0c=float(bc[2]))
        BOOT[n]["years"] = yo
    out["boot_vs_B0"] = BOOT
    out["boot_cfg"] = dict(block_days=BL, nrep=NREP, seed=SEED, infl_k3=INFL3,
                           scheme="circular block 10 ngay, cung chi so cho X va B0 (ghep cap); Calmar/maxDD tren eq NGAY (b+unP)")
    # ---- R4 vs R0 (luat n primary) va T170c vs R0, cung thuoc
    ra0 = EQ["R0"].pct_change().dropna().values
    rr = {}
    for x in ("R4", "T170c"):
        rx = EQ[x].pct_change().dropna().values
        cx = ST[x]["expo_mean"] / ST["R0"]["expo_mean"]
        rr[x + "_vs_R0"] = {vn: pair(rx, ra0, c) for vn, c in (("raw", 1.0), ("same_expo", cx))}
    out["vs_R0"] = rr
    jdump(out, "l5.json")


# ======================================================================= extra (L0 index/24h, L5 mo hinh slippage khac)
IDX_PREFIX = ("BTCDOM", "FOOTBALL", "BLUEBIRD", "DEFI", "PAXG", "XAU", "XAG", "XPT", "USDC", "TUSD", "FDUSD", "BUSD", "USDP")


def stage_extra():
    o = {"legs": {}}
    P = {}
    for n in ORDER:
        d = pd.read_pickle(os.path.join(WORK, "legs_%s.pkl" % n))
        pnl = (d.pnl + (R.LEGACY - C_TRUE) * d.notional) if n == "T170" else d.pnl   # T170 -> T170c
        P[n] = (d, pnl)
        ix = d.sym.str.startswith(IDX_PREFIX) | d.sym.str.contains("_")
        w24 = (d.last_ms - d.m0 <= 86400000) & (d.last_ms - d.m0 >= 0)
        rows = lambda m: [(r.sym, str(r.ts), str(r.te), r.status, round(float(r.pnl), 1)) for r in d[m].itertuples()]
        o["legs"][n] = dict(index_legs=int(ix.sum()), index_syms=sorted(d.sym[ix].unique().tolist()), index_pnl=float(pnl[ix].sum()),
                            index_notional=float(d.notional[ix].sum()), index_rows=rows(ix),
                            win24h_before_death=int(w24.sum()), win24h_pnl=float(pnl[w24].sum()), win24h_rows=rows(w24),
                            ghost_hold_funding=float(d.funding[d.g_hold].sum()), funding_total=float(d.funding.sum()),
                            drop_index_and_ghosthold_dPnL=-float(pnl[ix | d.g_hold].sum()),
                            drop_pct_sumpnl=-100 * float(pnl[ix | d.g_hold].sum()) / float(pnl.sum()))
    # mo hinh slippage: (a) % notional (tuyen tinh, = l5), (b) $ co dinh / lenh, (c) impact sqrt: s_i = k*sqrt(notional_i/1000)
    b0, pb0 = P["B0"]
    S15 = lambda d: float((d.notional ** 1.5).sum() / math.sqrt(1000.0))
    o["slip_models_vs_B0"] = {}
    for n in ORDER:
        if n == "B0":
            continue
        d, p = P[n]
        dp = float(pb0.sum() - p.sum())
        dn_cnt = len(b0) - len(d)
        ds15 = S15(b0) - S15(d)
        o["slip_models_vs_B0"][n + ("c" if n == "T170" else "")] = dict(
            dPnL_B0_minus_X=dp, fixed_usd_breakeven=(dp / dn_cnt) if dn_cnt > 0 else None,
            fixed_usd_breakeven_pct_B0_notional_mean=(100 * dp / dn_cnt / float(b0.notional.mean())) if dn_cnt > 0 else None,
            S15_B0=S15(b0), S15_X=S15(d), sqrt_k_breakeven=(dp / ds15) if ds15 > 0 else None,
            sqrt_note="B0 thang voi moi k" if ds15 <= 0 and dp > 0 else "")
    # BTC sanity (cho beta)
    eq = R.load_daily(CFG["B0"][0])["equity"].astype(float)
    bt = btc_daily(eq.index)
    o["btc_sanity"] = dict(n=int(bt.notna().sum()), first=float(bt.dropna().iloc[0]), last=float(bt.dropna().iloc[-1]),
                           ret_std_ann=float(bt.pct_change().std() * math.sqrt(365) * 100),
                           corr_B0_daily=float(pd.concat([eq.pct_change(), bt.pct_change()], axis=1).dropna().corr().iloc[0, 1]),
                           frac_days_B0_flat=float((eq.pct_change().abs() < 1e-12).mean()))
    jdump(o, "extra.json")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("stage"); ap.add_argument("--workers", type=int, default=3)
    a = ap.parse_args()
    st = ["scan", "ghost", "label", "pb", "mtm", "l5", "extra"] if a.stage == "all" else a.stage.split(",")
    for s in st:
        t = time.time()
        {"scan": lambda: stage_scan(a.workers), "ghost": stage_ghost, "label": stage_label,
         "mtm": lambda: stage_mtm(a.workers), "l5": stage_l5, "pb": stage_pb, "extra": stage_extra}[s]()
        log.info("stage %s done %.0fs", s, time.time() - t)
