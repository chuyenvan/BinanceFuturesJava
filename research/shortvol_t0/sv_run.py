"""SHORTVOL_T0 run (prereg docs/prereg/PREREG_SHORTVOL_T0.md, commit 73a23fae).
Inputs: WK/close1m_{SYM}.parquet, WK/dvol/dvol_{CUR}_1D.csv, WK/x14_daily.parquet, WK/x14_legs.parquet (from sv_prep.py / sv_fetch_dvol.py).
Outputs: WK/run/run.json, WK/run/weekly_{CUR}.csv, WK/run/daily_{CUR}.csv
"""
import os, json
import numpy as np, pandas as pd
WK = os.path.expanduser("~/claude_master/shortvol_t0_wk")
OUT = os.path.join(WK, "run"); os.makedirs(OUT, exist_ok=True)
MIN, FIVE, DAY, H = 60000, 300000, 86400000, 3600000
T0 = 1640908800000          # 2021-12-31 00:00 grid start
D0 = 1640995200000          # 2022-01-01 00:00
NDAYS = 1461                # 2022-01-01 .. 2025-12-31
NVRP30 = 1431               # t = 2022-01-01 .. 2025-12-01
NVRP7 = 1454                # t = 2022-01-01 .. 2025-12-24
MON0 = 1641168000000        # 2022-01-03 00:00 (Monday)
NWEEK = 208
SEED_MED = "s2024"
SLIP = 0.05
ms2s = lambda x: str(pd.to_datetime(int(x), unit="ms"))

def ann_sh(r):
    r = np.asarray(r, float); return float(r.mean() / r.std(ddof=1) * np.sqrt(52))
def mdd(r):
    eq = np.concatenate([[1.0], np.cumprod(1 + np.asarray(r, float))]); return float((eq / np.maximum.accumulate(eq) - 1).min())

def close_grid(sym):
    g = pd.read_parquet(os.path.join(WK, "close1m_%s.parquet" % sym))
    assert g.ts.dtype == np.int64 and len(g) == 1462 * 1440 and g.ts.iloc[0] == T0 and (np.diff(g.ts.values) == MIN).all()
    return g.close.values.astype(float), int(g.filled.sum())

def px_at(c, t_ms):  # price at instant t = close of 1m candle ts = t - 1min
    i = (np.asarray(t_ms, np.int64) - MIN - T0) // MIN; assert ((np.asarray(t_ms) - T0) % MIN == 0).all(); return c[i]
def candle_close(c, ts):  # close of 1m candle with open ts
    i = (np.asarray(ts, np.int64) - T0) // MIN; return c[i]

def rv_daily_sums(c):
    days = D0 + DAY * np.arange(NDAYS, dtype=np.int64)
    # 5m
    marks = np.arange(D0, D0 + NDAYS * DAY + 1, FIVE, dtype=np.int64)
    p5 = px_at(c, marks); r5 = np.diff(np.log(p5)); end5 = marks[1:]
    dix5 = (end5 - 1 - D0) // DAY
    n5 = np.bincount(dix5, minlength=NDAYS); assert len(n5) == NDAYS and (n5 == 288).all()
    s5 = np.bincount(dix5, weights=r5 ** 2, minlength=NDAYS)
    # 1m
    m1 = np.arange(D0, D0 + NDAYS * DAY + 1, MIN, dtype=np.int64)
    p1 = px_at(c, m1); r1 = np.diff(np.log(p1)); dix1 = (m1[1:] - 1 - D0) // DAY
    n1 = np.bincount(dix1, minlength=NDAYS); assert (n1 == 1440).all()
    s1 = np.bincount(dix1, weights=r1 ** 2, minlength=NDAYS)
    # daily 00:00 -> 00:00
    pd_ = px_at(c, np.append(days, days[-1] + DAY)); rd = np.diff(np.log(pd_)); sd = rd ** 2
    return days, s5, s1, sd

def rv_window(s, N, n_t):
    cs = np.concatenate([[0.0], np.cumsum(s)])
    i = np.arange(n_t); return 100 * np.sqrt(365.0 / N * (cs[i + N] - cs[i]))

def load_dvol(cur):
    d = pd.read_csv(os.path.join(WK, "dvol", "dvol_%s_1D.csv" % cur), dtype={"ts": np.int64})
    assert d.ts.dtype == np.int64 and d.ts.is_unique and (d.ts % DAY == 0).all()
    return pd.Series(d.close.values.astype(float), index=d.ts.values + DAY)  # value at 00:00 UTC of day ts+1

x14 = pd.read_parquet(os.path.join(WK, "x14_daily.parquet")); assert x14.day_ms.dtype == np.int64
legs = pd.read_parquet(os.path.join(WK, "x14_legs.parquet")); assert legs.start_ms.dtype == np.int64
LS, LE = legs.start_ms.values, legs.end_ms.values
mons = MON0 + 7 * DAY * np.arange(NWEEK, dtype=np.int64)
assert all(pd.to_datetime(m, unit="ms").dayofweek == 0 for m in mons) and ms2s(mons[-1]).startswith("2025-12-22")
tsell = mons + 8 * H
recent = np.array([bool(((LS > t - 7 * DAY) & (LS <= t)).any()) for t in tsell])
overlap = np.array([bool(((LS < t + 7 * DAY) & (LE >= t)).any()) for t in tsell])
def x14_week(seed):
    e = x14[x14.seed == seed].set_index("day_ms")["E"].astype(float)
    a = e.reindex(mons).values; b = e.reindex(mons + 7 * DAY).values
    assert not np.isnan(a).any() and not np.isnan(b).any(); return b / a - 1
RX = {sd: x14_week(sd) for sd in sorted(x14.seed.unique())}
yrs_w = np.array([pd.to_datetime(m, unit="ms").year for m in mons])
per2 = {"2022-23": yrs_w <= 2023, "2024-25": yrs_w >= 2024}
assert per2["2022-23"].sum() == 104 and per2["2024-25"].sum() == 104

def wstats(r, yrs):
    r = np.asarray(r, float)
    w, l = r[r > 0], r[r <= 0]
    return dict(n=int(len(r)), mean_pct=float(r.mean() * 100), sharpe_ann=ann_sh(r), mdd=mdd(r),
                year_mean_pct={int(y): float(r[yrs == y].mean() * 100) for y in sorted(set(yrs))},
                win_rate=float((r > 0).mean()), payoff_ratio=float(w.mean() / abs(l.mean())) if len(l) and len(w) else None,
                q=dict(zip(["p1", "p5", "p25", "p50", "p75", "p95", "p99"], [float(x * 100) for x in np.percentile(r, [1, 5, 25, 50, 75, 95, 99])])),
                worst_pct=float(r.min() * 100), best_pct=float(r.max() * 100), sum_pct=float(r.sum() * 100))

R = {"prereg_commit": "73a23fae", "n_legs_union": int(len(legs)), "weeks_recent_x14": int(recent.sum()), "weeks_overlap_x14": int(overlap.sum())}
for cur in ["BTC", "ETH"]:
    sym = cur + "USDT"
    c, nfill = close_grid(sym)
    days, s5, s1, sd = rv_daily_sums(c)
    dv = load_dvol(cur)
    dvt = dv.reindex(days).values; assert not np.isnan(dvt).any()
    rv30 = rv_window(s5, 30, NVRP30); rv7 = rv_window(s5, 7, NVRP7)
    rv30_1m = rv_window(s1, 30, NVRP30); rv30_d = rv_window(sd, 30, NVRP30)
    vrp30 = dvt[:NVRP30] - rv30; vrp7 = dvt[:NVRP7] - rv7
    yrs = np.array([pd.to_datetime(d, unit="ms").year for d in days])
    y30, y7 = yrs[:NVRP30], yrs[:NVRP7]
    mon_idx = np.array([pd.to_datetime(d, unit="ms").strftime("%Y-%m") for d in days[:NVRP30]])
    um = sorted(set(mon_idx)); assert len(um) == 48
    bs, bc = np.array([vrp30[mon_idx == m].sum() for m in um]), np.array([(mon_idx == m).sum() for m in um])
    rng = np.random.default_rng(20261024); boot = np.empty(10000)
    for b in range(10000):
        ix = rng.integers(0, 48, 48); boot[b] = bs[ix].sum() / bc[ix].sum()
    ci = [float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))]
    ym30 = {int(y): float(vrp30[y30 == y].mean()) for y in [2022, 2023, 2024, 2025]}
    V1 = sum(v > 0 for v in ym30.values()) >= 3 and vrp30.mean() > 0 and ci[0] > 0
    pd.DataFrame(dict(day_ms=days[:NVRP30], dvol=dvt[:NVRP30], rv30=rv30, rv30_1m=rv30_1m, rv30_d=rv30_d, vrp30=vrp30)).to_csv(os.path.join(OUT, "daily_%s.csv" % cur), index=False)
    # weekly straddle proxy
    S0 = candle_close(c, tsell); ST = candle_close(c, tsell + 7 * DAY)
    sig = dv.reindex(mons).values / 100; assert not np.isnan(sig).any()
    def pnl(slip):
        P = 0.8 * sig * np.sqrt(7 / 365) * S0
        f = np.minimum(0.00024 * S0, 0.10 * P / 2)
        return (P - 2 * f - slip * P - np.abs(ST - S0)) / S0, P, f
    r, P, f = pnl(SLIP)
    rc = np.where(recent, 0.0, r)
    st, stc = wstats(r, yrs_w), wstats(rc, yrs_w)
    stc_traded = wstats(r[~recent], yrs_w[~recent])
    def v2(s): return sum(v > 0 for v in s["year_mean_pct"].values()) >= 3 and s["sharpe_ann"] >= 0.8
    V2, V3 = v2(st), v2(stc)
    # X14 overlap
    rx = RX[SEED_MED]
    comb = 0.8 * rx + 0.2 * r
    v4 = {k: dict(dd_x14=mdd(rx[m]), dd_comb=mdd(comb[m]), sh_x14=ann_sh(rx[m]), sh_comb=ann_sh(comb[m]), corr=float(np.corrcoef(r[m], rx[m])[0, 1])) for k, m in per2.items()}
    V4 = all(v["dd_comb"] >= v["dd_x14"] - 0.03 for v in v4.values())
    v4_seeds = {sd: {k: dict(dd_x14=mdd(RX[sd][m]), dd_comb=mdd((0.8 * RX[sd] + 0.2 * r)[m]), ok=mdd((0.8 * RX[sd] + 0.2 * r)[m]) >= mdd(RX[sd][m]) - 0.03) for k, m in per2.items()} for sd in RX}
    worst = np.argsort(r)[:10]
    worst_tab = [dict(mon=ms2s(mons[i])[:10], pnl_pct=float(r[i] * 100), move_pct=float((ST[i] / S0[i] - 1) * 100), dvol=float(sig[i] * 100),
                      prem_pct=float(P[i] / S0[i] * 100), x14_overlap=bool(overlap[i]), x14_recent=bool(recent[i]), x14_ret_pct=float(rx[i] * 100)) for i in worst]
    ev = {}
    for name, dstr in [("LUNA", "2022-05-09"), ("FTX", "2022-11-07"), ("2025-10-10", "2025-10-06")]:
        i = int(np.where(np.array([ms2s(m)[:10] for m in mons]) == dstr)[0][0])
        ev[name] = dict(mon=dstr, pnl_pct=float(r[i] * 100), move_pct=float((ST[i] / S0[i] - 1) * 100), dvol=float(sig[i] * 100), rank_worst=int((r < r[i]).sum() + 1),
                        x14_overlap=bool(overlap[i]), x14_recent=bool(recent[i]), x14_ret_pct=float(rx[i] * 100))
    sens = {str(s): wstats(pnl(s)[0], yrs_w) for s in [0.02, 0.10]}
    R[cur] = dict(
        n_filled_minutes=nfill,
        vrp30=dict(n=int(NVRP30), mean=float(vrp30.mean()), ci95=ci, year_mean=ym30, frac_pos=float((vrp30 > 0).mean()),
                   dvol_mean=float(dvt[:NVRP30].mean()), rv30_mean=float(rv30.mean()),
                   year_dvol={int(y): float(dvt[:NVRP30][y30 == y].mean()) for y in [2022, 2023, 2024, 2025]},
                   year_rv30={int(y): float(rv30[y30 == y].mean()) for y in [2022, 2023, 2024, 2025]}),
        vrp7=dict(n=int(NVRP7), mean=float(vrp7.mean()), year_mean={int(y): float(vrp7[y7 == y].mean()) for y in [2022, 2023, 2024, 2025]}, frac_pos=float((vrp7 > 0).mean())),
        rv_sanity=dict(rv5_mean=float(rv30.mean()), rv1m_mean=float(rv30_1m.mean()), rvd_mean=float(rv30_d.mean()),
                       ratio_1m_5m=float((rv30_1m / rv30).mean()), ratio_d_5m=float((rv30_d / rv30).mean())),
        straddle=st, control=stc, control_traded_only=stc_traded, n_skipped=int(recent.sum()),
        prem_mean_pct=float((P / S0).mean() * 100), fee_mean_pct=float((2 * f / S0).mean() * 100), fee_cap_hit=int((0.00024 * S0 > 0.10 * P / 2).sum()),
        payoff_mean_pct=float((np.abs(ST - S0) / S0).mean() * 100),
        x14=dict(seed=SEED_MED, per=v4, corr_full=float(np.corrcoef(r, rx)[0, 1]),
                 x14_full=dict(sh=ann_sh(rx), dd=mdd(rx)), comb_full=dict(sh=ann_sh(comb), dd=mdd(comb)),
                 sv_sum_pct_overlap=float(r[overlap].sum() * 100), sv_sum_pct_no=float(r[~overlap].sum() * 100),
                 sv_mean_pct_overlap=float(r[overlap].mean() * 100), sv_mean_pct_no=float(r[~overlap].mean() * 100),
                 n_overlap=int(overlap.sum()), worst10_in_overlap=int(overlap[worst].sum()), worst10_in_recent=int(recent[worst].sum()),
                 seeds_v4=v4_seeds),
        worst10=worst_tab, events=ev, slip_sens=sens,
        verdict=dict(V1=bool(V1), V2=bool(V2), V3=bool(V3), V4=bool(V4), GO=bool(V1 and V2 and V3 and V4)))
    pd.DataFrame(dict(mon_ms=mons, tsell_ms=tsell, S0=S0, ST=ST, sigma=sig, prem=P, fee_leg=f, pnl=r, pnl_ctrl=rc, recent=recent, overlap=overlap, rx14=rx)).to_csv(os.path.join(OUT, "weekly_%s.csv" % cur), index=False)
    print(cur, json.dumps(R[cur]["verdict"]), "VRP30 mean %.3f CI %s years %s" % (vrp30.mean(), ci, ym30), flush=True)
    print(cur, "straddle", {k: st[k] for k in ["mean_pct", "sharpe_ann", "year_mean_pct", "win_rate", "worst_pct"]}, flush=True)
    print(cur, "control", {k: stc[k] for k in ["mean_pct", "sharpe_ann", "year_mean_pct"]}, "skipped", int(recent.sum()), flush=True)
    print(cur, "V4", v4, flush=True)
json.dump(R, open(os.path.join(OUT, "run.json"), "w"), indent=1, default=float)
