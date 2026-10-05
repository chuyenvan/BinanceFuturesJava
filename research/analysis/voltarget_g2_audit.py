#!/usr/bin/env python3
"""AUDIT VOLTARGET_G2 (2026-10-02) — doi khang, 0-sim, chi doc artifact Kaggle da co (vt-g2-b0, vt-g2-coin).
(A) thuoc ghep cap theo lenh (long_levers_paired_ruler): size-neutral / raw / leverage-matched (equity-normalized)
(B) equity-level: CAGR, maxDD ngay, Calmar, UW, Sharpe, vol, exposure TB; B0 scale tuyen tinh ve cung exposure/vol/beta
(C) paired bootstrap ngay (block 10d) cho dCalmar(COIN - B0xc), alpha
(D) multiplier VT uoc luong theo lenh vs loi nhuan/notional (quintile)
"""
import sys, json, math
import numpy as np, pandas as pd
sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
import reset_rule_score as R

B, A = "vt-g2-b0", "vt-g2-coin"
SEED, NREP = 20260905, 2000
OUT = sys.argv[1] if len(sys.argv) > 1 else "/tmp/audit_vt_g2.json"
MTM_MIN = {B: -17.680376897627216, A: -12.768153974505914}   # cache /tmp/voltarget_g2_mtm.json (driver)
res = {}

L = {t: R.load_legs(t) for t in (B, A)}
D = {t: R.load_daily(t) for t in (B, A)}
for t in (B, A):
    L[t]["key"] = L[t].sym + "|" + L[t].start.astype(str) + "|" + L[t].level.astype(str)
    print(t, "rows", len(L[t]), "dupkeys", L[t].key.duplicated().sum(), "days", len(D[t]),
          "eq_last", D[t].equity.iloc[-1])


def prev_eq(t, ts):
    """equity (b+unP) cua NGAY TRUOC ngay vao lenh (causal), khong co -> CAP0"""
    e = D[t]["equity"]
    idx = np.searchsorted(e.index.values, ts.dt.normalize().values, side="left") - 1
    v = np.where(idx >= 0, e.values[np.clip(idx, 0, len(e) - 1)], R.CAP0)
    return v


for t in (B, A):
    L[t]["E0"] = prev_eq(t, L[t]["ts"])
    L[t]["pnl_ret"] = L[t]["profit"] / 100.0 * L[t]["notional"]
    L[t]["g"] = L[t]["pnl"] / L[t]["E0"]
    L[t]["expo"] = L[t]["notional"] / L[t]["E0"]
b = L[B].drop_duplicates("key").set_index("key"); a = L[A].drop_duplicates("key").set_index("key")
com = b.index.intersection(a.index); ob = b.index.difference(a.index); oa = a.index.difference(b.index)
dp = (a.loc[com, "profit"] - b.loc[com, "profit"])
res["match"] = dict(n_b=len(b), n_a=len(a), n_common=len(com), only_b=len(ob), only_a=len(oa),
                    frac_profit_changed=float((dp.abs() > 1e-6).mean()), sum_abs_dprofit_pct=float(dp.abs().sum()),
                    pnl_col_vs_profitxnotional_corr=float(np.corrcoef(b.pnl, b.pnl_ret)[0, 1]))

# ---------------- (D) multiplier VT theo lenh: w = N_a/N_b ; m = w / (E_a/E_b) (bo troi equity)
w = a.loc[com, "notional"] / b.loc[com, "notional"]
m = w / (a.loc[com, "E0"] / b.loc[com, "E0"])
res["mult"] = dict(w_q=[float(x) for x in np.percentile(w, [5, 25, 50, 75, 95])], m_mean=float(m.mean()),
                   m_q=[float(x) for x in np.percentile(m, [1, 5, 25, 50, 75, 95, 99])],
                   frac_m_at_lo=float((m < 0.52).mean()), frac_m_at_hi=float((m > 1.95).mean()),
                   frac_m_lt1=float((m < 1).mean()),
                   expo_ratio_trade=float(a.expo.sum() / b.expo.sum()))
q = pd.qcut(m, 5, labels=False, duplicates="drop")
tab = []
for k in sorted(q.unique()):
    ix = q[q == k].index
    tab.append(dict(q=int(k), n=len(ix), m_mean=float(m[ix].mean()), profit_mean_b0=float(b.loc[ix, "profit"].mean()),
                    profit_med_b0=float(b.loc[ix, "profit"].median()), g_sum_b0=float(b.loc[ix, "g"].sum()),
                    sl_rate=float((b.loc[ix, "profit"] < 0).mean())))
res["mult_quintile"] = tab
from scipy.stats import spearmanr
res["mult_vs_profit_spearman"] = float(spearmanr(m, b.loc[com, "profit"]).correlation)


# ---------------- (A) thuoc ghep cap theo lenh, block-72h theo gio vao
def blk(ts):
    return ((ts - pd.Timestamp("2021-07-01")).dt.total_seconds() // (72 * 3600)).astype(int)


def boot_sum(t0, v, seed=SEED):
    df = pd.DataFrame({"blk": blk(pd.Series(t0)).values, "v": np.asarray(v, float)})
    s = df.groupby("blk").v.sum().values
    rng = np.random.default_rng(seed)
    bs = np.array([s[rng.integers(0, len(s), len(s))].sum() for _ in range(NREP)])
    lo, hi = np.percentile(bs, [2.5, 97.5])
    return dict(obs=float(s.sum()), ci95=[float(lo), float(hi)], halfwidth=float((hi - lo) / 2), K=len(s),
                contains0=bool(lo <= 0 <= hi))


t0c = b.loc[com, "ts"]
# P1 size-neutral (dung cong thuc AUDIT_LONG_LEVERS)
v1 = (a.loc[com, "profit"] - b.loc[com, "profit"]) / 100 * b.loc[com, "notional"]
v1 = pd.concat([v1, -(b.loc[ob, "pnl_ret"]), a.loc[oa, "pnl_ret"]])
t1 = pd.concat([t0c, b.loc[ob, "ts"], a.loc[oa, "ts"]])
res["P1_size_neutral_USDT"] = boot_sum(t1, v1)
# P2 raw (khong size-neutral) USDT
v2 = pd.concat([a.loc[com, "pnl_ret"] - b.loc[com, "pnl_ret"], -(b.loc[ob, "pnl_ret"]), a.loc[oa, "pnl_ret"]])
res["P2_raw_USDT"] = boot_sum(t1, v2)
# P3 leverage-matched, equity-normalized: g_a - c*g_b ; c = ty le exposure (sum N/E)
c_exp = float(a.expo.sum() / b.expo.sum())
ga, gb = a.loc[com, "g"], b.loc[com, "g"]
c_ols = float((ga * gb).sum() / (gb * gb).sum())
for nm, c in (("c_expo", c_exp), ("c_ols", c_ols), ("c_mean_m", float(m.mean()))):
    v3 = pd.concat([ga - c * gb, -(c * b.loc[ob, "g"]), a.loc[oa, "g"]]) * 100   # don vi: %-equity
    r = boot_sum(t1, v3); r["c"] = c
    res["P3_levmatched_pct_equity_" + nm] = r
res["P3_note"] = "sum g = tong dong gop pct-equity (khong compound); B0 sum g = %.2f%%, COIN sum g = %.2f%%" % (
    100 * b.g.sum(), 100 * a.g.sum())


# ---------------- (B) equity-level (daily b+unP)
def hourly_expo(t):
    d = L[t]
    h0 = pd.Timestamp("2021-07-01"); nh = int((pd.Timestamp("2026-01-01") - h0) / pd.Timedelta(hours=1))
    ex = np.zeros(nh + 1)
    s = ((d.ts - h0) / pd.Timedelta(hours=1)).astype(int).clip(0, nh).values
    e = ((d.te - h0) / pd.Timedelta(hours=1)).astype(int).clip(0, nh).values
    np.add.at(ex, s, d.notional.values); np.add.at(ex, e, -d.notional.values)
    ex = np.cumsum(ex)[:nh]
    idx = pd.date_range(h0, periods=nh, freq="h")
    return pd.Series(ex, idx).resample("D").mean()


def stats(eq, expo=None):
    eq = eq.astype(float)
    r = eq.pct_change().dropna()
    yrs = (eq.index[-1] - eq.index[0]).days / 365.25
    cagr = ((eq.iloc[-1] / eq.iloc[0]) ** (1 / yrs) - 1) * 100
    dd = (eq / eq.cummax() - 1) * 100
    uw = eq < eq.cummax(); uwmax = int(uw.groupby((~uw).cumsum()).sum().max())
    o = dict(cagr=float(cagr), maxdd_daily=float(dd.min()), calmar_daily=float(cagr / abs(dd.min())), uw_max_days=uwmax,
             sharpe=float(r.mean() / r.std() * math.sqrt(365)), vol_ann=float(r.std() * math.sqrt(365) * 100),
             sortino=float(r.mean() / r[r < 0].std() * math.sqrt(365)), final=float(eq.iloc[-1]))
    if expo is not None:
        x = (expo.reindex(eq.index).fillna(0) / eq.shift(1).bfill())
        o.update(expo_mean=float(x.mean()), expo_mean_active=float(x[x > 0].mean()), frac_days_flat=float((x <= 0).mean()))
    return o


EQ = {t: D[t]["equity"] for t in (B, A)}
common_days = EQ[B].index.intersection(EQ[A].index)
EQ = {t: EQ[t].loc[common_days] for t in EQ}
EX = {t: hourly_expo(t) for t in (B, A)}
S = {t: stats(EQ[t], EX[t]) for t in (B, A)}
for t in (B, A):
    S[t]["maxdd_mtm_min"] = MTM_MIN[t]; S[t]["calmar_mtm_min"] = S[t]["cagr"] / abs(MTM_MIN[t])
res["equity"] = S
rb, ra = EQ[B].pct_change().dropna(), EQ[A].pct_change().dropna()
beta = float(np.cov(ra, rb)[0, 1] / rb.var()); alpha_d = float(ra.mean() - beta * rb.mean())
res["regress_daily"] = dict(beta=beta, alpha_ann_pct=alpha_d * 365 * 100, r2=float(np.corrcoef(ra, rb)[0, 1] ** 2),
                            te_ann_pct=float((ra - beta * rb).std() * math.sqrt(365) * 100))


def scaled(rser, c, e0=R.CAP0):
    return pd.Series(e0 * np.cumprod(1 + c * rser.values), rser.index)


cands = dict(c_expo_daily=S[A]["expo_mean"] / S[B]["expo_mean"], c_vol=S[A]["vol_ann"] / S[B]["vol_ann"], c_beta=beta,
             c_expo_trade=c_exp, c_mean_m=float(m.mean()))
# CAGR-matched va DD-matched (giai bang luoi)
grid = np.linspace(0.3, 1.2, 1801)
cg = [stats(scaled(rb, c))["cagr"] for c in grid]
cands["c_cagr_match"] = float(grid[np.argmin(np.abs(np.array(cg) - S[A]["cagr"]))])
dg = [stats(scaled(rb, c))["maxdd_daily"] for c in grid]
cands["c_dd_match"] = float(grid[np.argmin(np.abs(np.array(dg) - S[A]["maxdd_daily"]))])
LM = {}
for nm, c in cands.items():
    s = stats(scaled(rb, c)); s["c"] = float(c)
    s["dCalmar_daily_COIN_minus"] = S[A]["calmar_daily"] - s["calmar_daily"]
    # minute-MTM DD cua B0xc xap xi = MTM_min(B0) * (ddDaily(B0xc)/ddDaily(B0))
    s["maxdd_mtm_min_approx"] = MTM_MIN[B] * s["maxdd_daily"] / S[B]["maxdd_daily"]
    s["calmar_mtm_approx"] = s["cagr"] / abs(s["maxdd_mtm_min_approx"])
    s["dCalmar_mtm_COIN_minus"] = S[A]["calmar_mtm_min"] - s["calmar_mtm_approx"]
    LM[nm] = s
res["levmatched_B0"] = LM


def scaled(rser, c, e0=None):   # noqa: F811  (co diem dau = equity ngay 0 de CAGR khop)
    e0 = float(EQ[B].iloc[0]) if e0 is None else e0
    v = np.concatenate(([e0], e0 * np.cumprod(1 + c * rser.values)))
    return pd.Series(v, EQ[B].index[:len(v)])


cg = [stats(scaled(rb, c))['cagr'] for c in grid]
cands['c_cagr_match'] = float(grid[np.argmin(np.abs(np.array(cg) - S[A]['cagr']))])
dg = [stats(scaled(rb, c))['maxdd_daily'] for c in grid]
cands['c_dd_match'] = float(grid[np.argmin(np.abs(np.array(dg) - S[A]['maxdd_daily']))])
for nm, c in cands.items():   # tinh lai voi diem dau dung
    s = stats(scaled(rb, c)); s["c"] = float(c)
    s["dCalmar_daily_COIN_minus"] = S[A]["calmar_daily"] - s["calmar_daily"]
    s["maxdd_mtm_min_approx"] = MTM_MIN[B] * s["maxdd_daily"] / S[B]["maxdd_daily"]
    s["calmar_mtm_approx"] = s["cagr"] / abs(s["maxdd_mtm_min_approx"])
    s["dCalmar_mtm_COIN_minus"] = S[A]["calmar_mtm_min"] - s["calmar_mtm_approx"]
    LM[nm] = s
res["levmatched_B0"] = LM


# ---------------- (C) paired circular block bootstrap tren return NGAY (block 10d)
def cal_of(r):
    eq = np.cumprod(1 + r)
    yrs = len(r) / 365.25
    cagr = (eq[-1] ** (1 / yrs) - 1) * 100
    pk = np.maximum.accumulate(np.concatenate(([1.0], eq)))[1:]
    mdd = ((eq / pk - 1) * 100).min()
    return cagr / abs(mdd) if mdd < 0 else np.nan, cagr, mdd


ra_v, rb_v = ra.values, rb.values
n = len(ra_v); BL = 10
rng = np.random.default_rng(SEED)
starts = [rng.integers(0, n, size=int(math.ceil(n / BL))) for _ in range(NREP)]
BOOT = {}
for nm, c in [("c1_raw", 1.0)] + [(k, cands[k]) for k in ("c_expo_daily", "c_beta", "c_cagr_match", "c_dd_match")]:
    dc, dcg, dmd, dal = [], [], [], []
    for st in starts:
        ix = (st[:, None] + np.arange(BL)[None, :]).ravel()[:n] % n
        x, y = ra_v[ix], c * rb_v[ix]
        ca, ga_, ma = cal_of(x); cb, gb_, mb = cal_of(y)
        dc.append(ca - cb); dcg.append(ga_ - gb_); dmd.append(ma - mb); dal.append((x - y).mean() * 365 * 100)
    ca, ga_, ma = cal_of(ra_v); cb, gb_, mb = cal_of(c * rb_v)
    pc = lambda arr: [float(v) for v in np.nanpercentile(arr, [2.5, 97.5])]
    BOOT[nm] = dict(c=float(c), dCalmar_obs=float(ca - cb), dCalmar_ci95=pc(dc), dCAGR_obs=float(ga_ - gb_),
                    dCAGR_ci95=pc(dcg), dMaxDD_obs=float(ma - mb), dMaxDD_ci95=pc(dmd),
                    dMeanRet_ann_obs=float((ra_v - c * rb_v).mean() * 365 * 100), dMeanRet_ann_ci95=pc(dal),
                    p_dCalmar_gt0=float(np.nanmean(np.array(dc) > 0)))
res["boot_daily_block10"] = BOOT

# ---------------- T2 (bo sung, khong co trong pre-reg) qua core_metrics
for t in (B, A):
    mm = R.core_metrics(t, L[t], D[t], "legacy")
    res.setdefault("tier_extra", {})[t] = {k: mm[k] for k in ("q_star", "top1_pct", "ep_sum", "n_ep", "gross_max",
                                                              "gross_mean", "conc_max", "maxdd_daily", "uw_daily", "cagr")}
json.dump(res, open(OUT, "w"), indent=1, default=float)
print(json.dumps(res, indent=1, default=float))
