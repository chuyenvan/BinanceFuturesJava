"""BIGDOWN_STRUCT (TASK A, PREREG_BIGDOWN_STRUCT.md) - bigdown co phai nhan to dong-thua?

CHI DOC printDone.csv/sim.out cua T170 (X1_GS_T170_2021) va T100 (X1_C3_FULL_2021) +
CLOSES_1H.bin. KHONG sua .java, KHONG chay sim, KHONG xgboost. Dung module logging, cam print().

Chay: cd /home/ubuntu/src/BinanceFuturesJava && python3 research/analysis/bigdown_struct.py
Ghi: research/analysis/out/bigdown_struct.json
"""
import ast
import json
import logging
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import c3_rates as C  # noqa: E402  (trades/equity/inflate)
import beta_decomp_t170 as BD  # noqa: E402 (CTIME/CLOSE BTC, btc_at_or_before) - giu import de tai su dung mo hinh nap BTC
from hedge_overlay_a import hourly_grid, sum_notional_on_grid  # noqa: E402
from trend_rank_ic import load_closes  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("bigdown_struct")

TAGS = {"T170": "X1_GS_T170_2021", "T100": "X1_C3_FULL_2021"}
OUT_JSON = os.path.join(HERE, "out", "bigdown_struct.json")
HOUR_MS = 3600 * 1000
GMT7_MS = 7 * HOUR_MS
NREP = 2000
SEED = 20260905


# --------------------------------------------------------------- tai icc_anova NGUYEN VAN
def load_icc_anova():
    src = os.path.join(HERE, "nbets_step3_crosssec.py")
    tree = ast.parse(open(src).read())
    fn = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "icc_anova"]
    if len(fn) != 1:
        raise RuntimeError("khong tim thay icc_anova trong %s" % src)
    ns = {"np": np}
    exec(compile(ast.Module(body=fn, type_ignores=[]), src, "exec"), ns)
    return ns["icc_anova"]


icc_anova = load_icc_anova()


# --------------------------------------------------------------- helpers causal chung
def asof_leq(times_sorted, vals, query_ms):
    """Gia tri GAN NHAT co times_sorted <= query_ms (vector hoa, causal)."""
    query_ms = np.asarray(query_ms, dtype=np.int64)
    idx = np.searchsorted(times_sorted, query_ms, side="right") - 1
    ok = (idx >= 0) & (query_ms >= times_sorted[0])
    idx_c = np.clip(idx, 0, len(vals) - 1)
    return np.where(ok, vals[idx_c], np.nan)


def load_universe_breadth():
    """Tu CLOSES_1H.bin (TOAN BO universe): tai moi ctime, % symbol active co 1h-return < 0."""
    df = load_closes()
    df = df.sort_values(["sym", "ctime"]).reset_index(drop=True)
    close = df["close"].to_numpy()
    ctime = df["ctime"].to_numpy()
    sym = df["sym"].to_numpy()
    n = len(df)
    ret1 = np.full(n, np.nan)
    u, first = np.unique(sym, return_index=True)
    ends = np.append(first[1:], n)
    for s, e in zip(first, ends):
        if e - s < 2:
            continue
        cc = close[s:e]
        ret1[s + 1:e] = cc[1:] / cc[:-1] - 1.0
    ok = np.isfinite(ret1)
    g = pd.DataFrame({"ctime": ctime[ok], "neg": (ret1[ok] < 0).astype(np.int64)})
    agg = g.groupby("ctime")["neg"].agg(["sum", "count"])
    pct_red = (100.0 * agg["sum"] / agg["count"]).sort_index()
    return pct_red.index.to_numpy(dtype=np.int64), pct_red.to_numpy(dtype=np.float64)


# --------------------------------------------------------------- BD1/BD2/BD3 tren grid
def build_bd_flags(grid, px):
    ret24 = np.full(len(px), np.nan)
    ret24[24:] = px[24:] / px[:-24] - 1.0
    ret72 = np.full(len(px), np.nan)
    ret72[72:] = px[72:] / px[:-72] - 1.0
    ret1 = np.full(len(px), np.nan)
    ret1[1:] = px[1:] / px[:-1] - 1.0

    win = 60 * 24
    q05_roll = pd.Series(ret1).rolling(win, min_periods=200).quantile(0.05).shift(1).to_numpy()

    flags = {
        "BD1a_5pct24h": ret24 <= -0.05,
        "BD1b_8pct24h": ret24 <= -0.08,
        "BD1c_10pct72h": ret72 <= -0.10,
        "BD1q_q05_60d": (ret1 <= q05_roll) & np.isfinite(q05_roll),
    }
    bt, bv = load_universe_breadth()
    pct_red_grid = asof_leq(bt, bv, grid)
    for P in (70, 80, 90):
        flags["BD2_%d" % P] = np.where(np.isfinite(pct_red_grid), pct_red_grid, -1) >= P

    sev = np.full(len(px), "", dtype=object)
    a = flags["BD1a_5pct24h"]
    sev[a & (ret24 > -0.08)] = "mild"
    sev[a & (ret24 <= -0.08) & (ret24 > -0.15)] = "moderate"
    sev[a & (ret24 <= -0.15)] = "severe"
    return flags, dict(ret24=ret24, ret72=ret72, ret1=ret1, pct_red=pct_red_grid, sev=sev)


def episodes_of(flag):
    f = flag.astype(bool)
    prev = np.r_[False, f[:-1]]
    return np.where(f & ~prev)[0]


# --------------------------------------------------------------- nhan lenh theo bigdown
def label_trades(d, grid, flag):
    s_idx = np.searchsorted(grid, d["s_ms"].to_numpy(), side="right") - 1
    e_idx = np.searchsorted(grid, d["e_ms"].to_numpy(), side="right") - 1
    s_idx = np.clip(s_idx, 0, len(flag) - 1)
    e_idx = np.clip(e_idx, 0, len(flag) - 1)
    enter = flag[s_idx]
    exposed = np.empty(len(d), dtype=bool)
    for i, (a, b) in enumerate(zip(s_idx, e_idx)):
        lo, hi = (a, b) if a <= b else (b, a)
        exposed[i] = flag[lo:hi + 1].any()
    return enter, exposed


def load_trades_utc(tag):
    d = C.trades(tag).copy()
    d["t0"] = d["ts"]
    d["t1"] = pd.to_datetime(d["end"], format="%Y%m%d %H:%M", errors="coerce")
    d = d.dropna(subset=["t0", "t1"]).reset_index(drop=True)
    d["s_ms"] = d.t0.values.astype("datetime64[ms]").astype(np.int64) - GMT7_MS
    d["e_ms"] = d.t1.values.astype("datetime64[ms]").astype(np.int64) - GMT7_MS
    d["e_ms"] = np.maximum(d["e_ms"], d["s_ms"])
    d["notional"] = d["margin"].astype(float)
    d["roi"] = d["pnl"].astype(float) / d["notional"]
    return d


def new_entry_counts(d, grid):
    idx = np.searchsorted(grid, d["s_ms"].to_numpy(), side="right") - 1
    idx = np.clip(idx, 0, len(grid) - 1)
    return np.bincount(idx, minlength=len(grid)).astype(np.float64)


def equity_at_grid(tag, grid):
    eq = C.equity(tag)
    et = eq.index.values.astype("datetime64[ms]").astype(np.int64)
    ev = eq.to_numpy(dtype=np.float64)
    order = np.argsort(et)
    return asof_leq(et[order], ev[order], grid)


def icc_for(sub, col, cohort_series):
    if len(sub) < 4:
        return None
    groups = [v.values for _, v in sub.groupby(cohort_series)[col]]
    icc, J, N, k0 = icc_anova(groups)
    return dict(icc=(float(icc) if np.isfinite(icc) else None), J=int(J), N=int(N),
                k0=(float(k0) if np.isfinite(k0) else None))


def phi_for(sub, col):
    if len(sub) < 4:
        return dict(phi=None, J=0, phat=None)
    g = sub.groupby(sub.t0.dt.floor("1D"))
    ks = g.size()
    Ls = g[col].sum()
    m = ks >= 3
    ks, Ls = ks[m], Ls[m]
    if len(ks) < 2:
        return dict(phi=None, J=int(len(ks)), phat=None)
    phat = float(Ls.sum()) / float(ks.sum())
    if phat <= 0 or phat >= 1:
        return dict(phi=None, J=int(len(ks)), phat=phat)
    num = ((Ls - ks * phat) ** 2 / (ks * phat * (1 - phat))).sum()
    phi = float(num) / (len(ks) - 1)
    return dict(phi=phi, J=int(len(ks)), phat=phat)


def n_eff(sub, cohort_series, icc):
    g = sub.groupby(cohort_series).size()
    g = g[g >= 2]
    icc2 = max(icc, 0.0) if (icc is not None and np.isfinite(icc)) else 0.0
    ks = g.values.astype(float)
    if len(ks) == 0:
        return dict(n_eff_total=None, n_eff_nbets=None, J=0, kbar=None, cap_1_over_icc=None)
    n_eff_total = float((ks / (1 + (ks - 1) * icc2)).sum())
    kbar = float(ks.mean())
    J = len(ks)
    n_eff_nbets = float(J * kbar / (1 + (kbar - 1) * icc2))
    cap = float(1.0 / icc2) if icc2 > 0 else float("inf")
    return dict(n_eff_total=n_eff_total, n_eff_nbets=n_eff_nbets, J=J, kbar=kbar, cap_1_over_icc=cap)


def maxdd_decomp(tag, grid, flag, d):
    s = C.equity(tag)
    dd = (s / s.cummax() - 1) * 100
    uw = s < s.cummax()
    trough = dd.idxmin()
    peak = s.loc[:trough].idxmax()
    seg = s.loc[peak:trough]
    rday = seg.pct_change().dropna()
    local_day = pd.to_datetime(grid + GMT7_MS, unit="ms").floor("D")
    bd_days = set(pd.DatetimeIndex(local_day[flag]).unique())
    neg = rday[rday < 0]
    contrib = -neg
    is_bd = neg.index.to_series().apply(lambda d0: d0 in bd_days)
    bd_share = float(100.0 * contrib[is_bd].sum() / contrib.sum()) if contrib.sum() > 0 else None
    uw_days = s.index[uw]
    uw_bd_pct = float(100.0 * sum(1 for d0 in uw_days if d0 in bd_days) / len(uw_days)) if len(uw_days) else None
    rall = s.pct_change().dropna()
    worst10 = rall.nsmallest(10)
    top10 = []
    for day, ret in worst10.items():
        is_bdd = day in bd_days
        opened = int((d.t0.dt.floor("1D") == day).sum())
        closed = d[d.t1.dt.floor("1D") == day]
        pct_loss_closed = float((closed.profit < 0).mean() * 100) if len(closed) else None
        top10.append(dict(day=str(day.date()), ret_pct=float(ret * 100), bigdown=bool(is_bdd),
                           n_opened=opened, n_closed=int(len(closed)), pct_closed_loss=pct_loss_closed))
    return dict(maxDD_pct=float(dd.min()), peak=str(peak.date()), trough=str(trough.date()),
                bd_share_of_maxdd_depth_pct=bd_share, uw_days_total=int(uw.sum()),
                uw_days_bd_pct=uw_bd_pct, top10_worst_days=top10)


def bien_set(d170, d100):
    key170 = set(zip(d170["sym"], d170["start"]))
    key100 = set(zip(d100["sym"], d100["start"]))
    match170 = sum(1 for k in zip(d170["sym"], d170["start"]) if k in key100)
    match_rate = match170 / len(d170) if len(d170) else None
    mask = np.array([(s, t) not in key170 for s, t in zip(d100["sym"], d100["start"])])
    return match_rate, d100[mask].copy()


def block_boot_mean(sub, nrep=NREP, seed=SEED):
    if len(sub) == 0:
        return None, None, None
    groups = {k: v["roi"].values for k, v in sub.groupby("blk")}
    blocks = np.array(list(groups.keys()))
    obs = float(sub["roi"].mean())
    if len(blocks) == 0:
        return obs, None, None
    rng = np.random.default_rng(seed)
    draws = np.empty(nrep)
    for i in range(nrep):
        pick = rng.choice(blocks, size=len(blocks), replace=True)
        vals = np.concatenate([groups[b] for b in pick])
        draws[i] = vals.mean() if len(vals) else np.nan
    draws = draws[np.isfinite(draws)]
    lo, hi = np.percentile(draws, [5, 95])
    return obs, float(lo), float(hi)


def pct_stats(arr, flag):
    def s(a):
        a = np.asarray(a, dtype=float)
        return dict(p50=float(np.percentile(a, 50)), p90=float(np.percentile(a, 90)),
                    p99=float(np.percentile(a, 99)), max=float(a.max()), mean=float(a.mean()),
                    n=int(len(a)))
    return dict(bigdown=s(arr[flag]), nonbigdown=s(arr[~flag]))


def rs_stats(a):
    a = a[np.isfinite(a)]
    if len(a) == 0:
        return None
    return dict(p50=float(np.percentile(a, 50)), p90=float(np.percentile(a, 90)),
                p99=float(np.percentile(a, 99)), max=float(np.nanmax(a)), n=int(len(a)))


def main():
    os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
    log.info("=== BIGDOWN_STRUCT: nap grid gio + BTC + breadth ===")
    grid, px = hourly_grid()
    flags, extra = build_bd_flags(grid, px)
    log.info("grid n=%d BD1a_frac=%.4f BD2_80_frac=%.4f BD1q_frac=%.4f",
              len(grid), flags["BD1a_5pct24h"].mean(), flags["BD2_80"].mean(),
              flags["BD1q_q05_60d"].mean())

    result = {"grid_hours": int(len(grid)),
              "flag_frac": {k: float(v.mean()) for k, v in flags.items()}}

    trades = {}
    for name, tag in TAGS.items():
        d = load_trades_utc(tag)
        trades[name] = d
        log.info("%s: n_rows=%d n_episodes=%d", name, len(d),
                  d.groupby(["sym", "end"]).ngroups)

    flag_bd1a = flags["BD1a_5pct24h"]
    sev = extra["sev"]
    run_out = {}
    for name, tag in TAGS.items():
        d = trades[name]
        out = {}
        n_rows = len(d)
        n_ep = d.groupby(["sym", "end"]).ngroups
        out["M1"] = dict(n_rows=n_rows, n_episodes=n_ep, ratio=n_rows / n_ep)

        s_idx0 = np.clip(np.searchsorted(grid, d["s_ms"].to_numpy(), side="right") - 1,
                          0, len(sev) - 1)
        d_sev = sev[s_idx0]
        sev_count = {lvl: int((d_sev == lvl).sum()) for lvl in ("mild", "moderate", "severe")}
        sev_count["none"] = int((d_sev == "").sum())
        loss_by_sev = {}
        for lvl in ("mild", "moderate", "severe", ""):
            m = d_sev == lvl
            if m.sum() >= 5:
                loss_by_sev[lvl or "none"] = float((d.loc[m, "roi"] < 0).mean())
        out["severity_of_entry"] = dict(count=sev_count, loss_rate=loss_by_sev)

        counts1 = new_entry_counts(d, grid)
        counts4 = pd.Series(counts1).rolling(4, min_periods=1).sum().to_numpy()
        ep_first = d[d.leg == 0]
        ecounts1 = new_entry_counts(ep_first, grid)
        ecounts4 = pd.Series(ecounts1).rolling(4, min_periods=1).sum().to_numpy()
        out["M2"] = dict(rows_1h=pct_stats(counts1, flag_bd1a), rows_4h=pct_stats(counts4, flag_bd1a),
                          episodes_1h=pct_stats(ecounts1, flag_bd1a), episodes_4h=pct_stats(ecounts4, flag_bd1a))

        notional_grid = sum_notional_on_grid(d, grid)
        equity_grid = equity_at_grid(tag, grid)
        ratio = np.where(np.isfinite(equity_grid) & (equity_grid > 0),
                          notional_grid / equity_grid, np.nan)
        out["M3"] = dict(bigdown=rs_stats(ratio[flag_bd1a]), nonbigdown=rs_stats(ratio[~flag_bd1a]))
        onset = episodes_of(flag_bd1a)
        pre, p1, p4 = [], [], []
        for i0 in onset:
            if 1 <= i0 and i0 + 4 < len(ratio):
                if np.isfinite(ratio[i0 - 1]) and np.isfinite(ratio[i0 + 4]):
                    pre.append(ratio[i0 - 1])
                    p1.append(ratio[min(i0 + 1, len(ratio) - 1)])
                    p4.append(ratio[i0 + 4])
        out["M3"]["onset_n_episodes"] = int(len(onset))
        out["M3"]["onset_median_pre"] = float(np.median(pre)) if pre else None
        out["M3"]["onset_median_p1h"] = float(np.median(p1)) if p1 else None
        out["M3"]["onset_median_p4h"] = float(np.median(p4)) if p4 else None

        enter, exposed = label_trades(d, grid, flag_bd1a)
        d["enter_bd"] = enter
        d["exposed_bd"] = exposed
        lo_q, hi_q = d.roi.quantile([0.01, 0.99])
        d["roi_w"] = d.roi.clip(lo_q, hi_q)
        p10 = d.roi.quantile(0.10)
        d["loss"] = (d.roi < 0).astype(int)
        d["sevloss"] = (d.roi < p10).astype(int)
        cohorts = {
            "ngay": d.t0.dt.floor("1D"),
            "72h": pd.Series(d.t0.values.astype("datetime64[ns]").astype(np.int64) // (72 * 3600 * 10 ** 9), index=d.index),
            "tuan": pd.Series(d.t0.values.astype("datetime64[ns]").astype(np.int64) // (7 * 24 * 3600 * 10 ** 9), index=d.index),
        }
        splits = {"all": d, "exposed1": d[d.exposed_bd], "exposed0": d[~d.exposed_bd],
                  "enter1": d[d.enter_bd], "enter0": d[~d.enter_bd]}
        icc_table = {}
        for vname in ("roi", "roi_w", "loss", "sevloss"):
            for cname, ckey in cohorts.items():
                for sname, sub in splits.items():
                    key = "%s|%s|%s" % (vname, cname, sname)
                    icc_table[key] = icc_for(sub, vname, ckey.loc[sub.index]) if len(sub) >= 4 else None
        phi_table = {}
        for vname in ("loss", "sevloss"):
            for sname, sub in splits.items():
                phi_table["%s|%s" % (vname, sname)] = phi_for(sub, vname)
        out["M4"] = dict(icc=icc_table, phi=phi_table,
                          n_exposed1=int(d.exposed_bd.sum()), n_exposed0=int((~d.exposed_bd).sum()),
                          n_enter1=int(d.enter_bd.sum()), n_enter0=int((~d.enter_bd).sum()))
        p_e1 = phi_table["loss|exposed1"]["phi"]
        p_e0 = phi_table["loss|exposed0"]["phi"]
        out["M4"]["g1_phi_ratio_loss_exposed"] = (p_e1 / p_e0) if (p_e1 and p_e0) else None

        out["M5"] = maxdd_decomp(tag, grid, flag_bd1a, d)

        icc_row = icc_table["roi|ngay|all"]["icc"] if icc_table["roi|ngay|all"] else None
        out["M6_rows"] = n_eff(d, cohorts["ngay"], icc_row)
        ep = d.groupby(["sym", "end"]).agg(t0=("t0", "min"), pnl=("pnl", "sum"),
                                           margin=("margin", "sum")).reset_index()
        ep["roi"] = ep.pnl / ep.margin
        ep_cohort = ep.t0.dt.floor("1D")
        icc_ep = icc_for(ep, "roi", ep_cohort)
        out["M6_episodes"] = n_eff(ep, ep_cohort, icc_ep["icc"] if icc_ep else None)
        out["M6_episodes"]["icc_roi"] = icc_ep["icc"] if icc_ep else None

        run_out[name] = out

    d170_raw, d100_raw = trades["T170"], trades["T100"]
    match_rate, bien_df = bien_set(d170_raw, d100_raw)
    bien_enter, bien_exposed = label_trades(bien_df, grid, flag_bd1a)
    bien_df = bien_df.copy()
    bien_df["exposed_bd"] = bien_exposed
    bien_df["enter_bd"] = bien_enter
    obs, lo, hi = block_boot_mean(bien_df)
    win_pct = float((bien_df.profit > 0).mean() * 100) if len(bien_df) else None
    icc_bien = icc_for(bien_df, "roi", bien_df.t0.dt.floor("1D")) if len(bien_df) >= 4 else None
    bien_df["loss"] = (bien_df.roi < 0).astype(int)
    phi_bien = phi_for(bien_df, "loss") if len(bien_df) >= 4 else None
    result["M7"] = dict(t170_subset_match_rate=match_rate, n_bien=int(len(bien_df)),
                         roi_mean=obs, roi_ci90_lo=lo, roi_ci90_hi=hi, win_pct=win_pct,
                         icc=icc_bien, phi_loss=phi_bien,
                         pct_enter_bd=float(np.mean(bien_enter) * 100) if len(bien_enter) else None,
                         pct_exposed_bd=float(np.mean(bien_exposed) * 100) if len(bien_exposed) else None)

    result["runs"] = run_out

    d100 = trades["T100"]
    s100 = C.equity(TAGS["T100"])
    dd100 = (s100 / s100.cummax() - 1) * 100
    trough100 = dd100.idxmin()
    peak100 = s100.loc[:trough100].idxmax()
    seg100 = s100.loc[peak100:trough100]
    rday100 = seg100.pct_change().dropna()
    neg100 = rday100[rday100 < 0]
    contrib100 = -neg100
    local_day_all = pd.to_datetime(grid + GMT7_MS, unit="ms").floor("D")
    sens = {}
    for fname, fl in flags.items():
        enter_f, exposed_f = label_trades(d100, grid, fl)
        tmp = d100.copy()
        tmp["exposed_f"] = exposed_f
        tmp["loss"] = (tmp.roi < 0).astype(int)
        phi1 = phi_for(tmp[tmp.exposed_f], "loss")
        phi0 = phi_for(tmp[~tmp.exposed_f], "loss")
        ratio_g1 = (phi1["phi"] / phi0["phi"]) if (phi1["phi"] and phi0["phi"]) else None
        bd_days_f = set(pd.DatetimeIndex(local_day_all[fl]).unique())
        is_bd = contrib100.index.to_series().apply(lambda d0: d0 in bd_days_f)
        g2 = float(100.0 * contrib100[is_bd].sum() / contrib100.sum()) if contrib100.sum() > 0 else None
        sens[fname] = dict(flag_frac=float(fl.mean()), g1_phi_ratio=ratio_g1, g2_pct_maxdd_depth=g2,
                            n_exposed1=int(exposed_f.sum()), phi_exposed1=phi1["phi"], phi_exposed0=phi0["phi"])
    result["sensitivity_T100"] = sens

    g1 = run_out["T100"]["M4"]["g1_phi_ratio_loss_exposed"]
    g2 = run_out["T100"]["M5"]["bd_share_of_maxdd_depth_pct"]
    g3_pass = None
    if result["M7"]["roi_ci90_lo"] is not None and result["M7"]["roi_mean"] is not None:
        g3_pass = bool(result["M7"]["roi_mean"] > 0 and result["M7"]["roi_ci90_lo"] > -0.005)
    result["gate"] = dict(
        g1_phi_ratio_T100=g1, g1_pass=bool(g1 is not None and g1 >= 1.5),
        g2_pct_maxdd_depth_T100=g2, g2_pass=bool(g2 is not None and g2 >= 50.0),
        g3_roi_mean_bien=result["M7"]["roi_mean"],
        g3_ci90=[result["M7"]["roi_ci90_lo"], result["M7"]["roi_ci90_hi"]],
        g3_pass=g3_pass,
        g4_note="ngoai pham vi TASK A - can ket qua A-recon (diem cam admission/sizing OFF byte-identical)",
    )

    with open(OUT_JSON, "w") as f:
        json.dump(result, f, indent=2, default=str)
    log.info("DONE -> %s", OUT_JSON)
    log.info("GATE: g1=%s pass=%s | g2=%s pass=%s | g3_roi=%s ci90=%s pass=%s",
              g1, result["gate"]["g1_pass"], g2, result["gate"]["g2_pass"],
              result["M7"]["roi_mean"], result["gate"]["g3_ci90"], result["gate"]["g3_pass"])


if __name__ == "__main__":
    main()
