#!/usr/bin/env python3
"""R1_ROBUST — robustness cua fade R1 khi cham theo NGAY (0-sim). Pre-reg: docs/prereg/PREREG_R1_ROBUST.md (9ce3c459).
Doc per-trade CSV R1 (n 10 991) + R1c (n 10 977) + data/meta/symbol_lineage_v2.csv. Khong stream 1m, khong Java, khong 242.
Out: docs/result/RESULT_R1_ROBUST.json + .md
"""
import os, sys, json, logging
import numpy as np, pandas as pd

REPO = "/home/ubuntu/src/BinanceFuturesJava"
CSV = os.path.expanduser("~/claude_master/1002/r1_cache/trades_r1.csv")
CSVC = os.path.expanduser("~/claude_master/1002/r1c_cache/trades_r1c.csv")
LIN = os.path.join(REPO, "data/meta/symbol_lineage_v2.csv")
OUTJ = os.path.join(REPO, "docs/result/RESULT_R1_ROBUST.json")
OUTM = os.path.join(REPO, "docs/result/RESULT_R1_ROBUST.md")
MIN, H72, DAY = 60000, 72 * 3600000, 86400000
NREP, SEED, INFL = 2000, 20260905, 1.89
SHORT = ["S_A4", "S_A12", "S_A24", "S_B4", "S_B12", "S_B24"]
MAIN = ["S_B24", "S_B12"]
YE = (2022, 2023, 2024, 2025)
CRASH = ["2025-10-10", "2024-08-05"]
DEV_DAYS = pd.date_range("2022-01-01", "2025-12-31", freq="D")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("r1_robust")


def boot(v, blk):
    """Block/cluster bootstrap y het R1 ci_block: resample block co hoan lai, stat = Ssum/Scount."""
    v = np.asarray(v, np.float64)
    _, inv = np.unique(np.asarray(blk, np.int64), return_inverse=True)
    sums = np.bincount(inv, weights=v); cnts = np.bincount(inv).astype(np.float64)
    rng = np.random.default_rng(SEED); nb = len(sums)
    bs = np.empty(NREP)
    for b in range(NREP):
        p = rng.integers(0, nb, nb)
        bs[b] = sums[p].sum() / cnts[p].sum()
    lo, hi = float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))
    mu = float(v.mean())
    return dict(mean=mu, raw=[lo, hi], infl=[mu - (mu - lo) * INFL, mu + (hi - mu) * INFL], nblock=int(nb),
                bvar=float(bs.var(ddof=1)))


def years_pos(v, yr):
    ym = {int(y): float(v[yr == y].mean()) for y in YE if (yr == y).any()}
    return ym, int(sum(m > 0 for m in ym.values()))


def daily(df, c):
    g = df.groupby("day")[c + "_net"]
    d = pd.DataFrame(dict(sum=g.sum(), n=g.size(), mean=g.mean()))
    d["year"] = pd.to_datetime(d.index * DAY, unit="ms", utc=True).year
    return d


def dayw(d):
    v = d["mean"].to_numpy(float)
    ci = boot(v, (d.index.to_numpy(np.int64) * DAY) // H72)
    ym, yp = years_pos(v, d["year"].to_numpy())
    return dict(ndays=len(d), mean=ci["mean"], median=float(np.median(v)), ci72_raw=ci["raw"], ci72_infl=ci["infl"],
                yearly=ym, years_pos=yp)


def pooled(df, c, blk="b72"):
    v = df[c + "_net"].to_numpy(float)
    ci = boot(v, df[blk].to_numpy())
    ym, yp = years_pos(v, df["year"].to_numpy())
    return dict(n=len(v), mean=ci["mean"], ci_raw=ci["raw"], ci_infl=ci["infl"], nblock=ci["nblock"], bvar=ci["bvar"],
                yearly=ym, years_pos=yp, sl_rate=float((df[c + "_r"] == 1).mean()))


def m1(df, c):
    return dayw(daily(df, c))


def m2(df, c):
    d = daily(df, c).sort_index()
    out = {}
    for key, rank in (("abs_sum", d["sum"].abs()), ("n", d["n"])):
        order = rank.sort_values(ascending=False, kind="mergesort").index  # hoa -> ngay som hon truoc (index da sort)
        for k in (1, 3, 5, 10):
            drop = order[:k]
            r = df[~df.day.isin(drop)]
            dd = d.drop(drop)
            out["%s_k%d" % (key, k)] = dict(dropped=[str(pd.Timestamp(x * DAY, unit="ms").date()) for x in drop],
                                            dropped_sum=float(d.loc[drop, "sum"].sum()), dropped_n=int(d.loc[drop, "n"].sum()),
                                            n=len(r), pooled_mean=float(r[c + "_net"].mean()), dayw_mean=float(dd["mean"].mean()))
    return out


def m3(df, c):
    d = daily(df, c)
    tot_s, tot_n = float(d["sum"].sum()), int(d["n"].sum())
    nn = d["n"].to_numpy()
    top = d.sort_values("n", ascending=False, kind="mergesort").head(10)
    res = dict(dev_days=len(DEV_DAYS), days_with_trade=len(d), days_without=len(DEV_DAYS) - len(d),
               per_day=dict(mean=float(nn.mean()), median=float(np.median(nn)), p90=float(np.percentile(nn, 90)),
                            p99=float(np.percentile(nn, 99)), max=int(nn.max())),
               total_sum=tot_s,
               top10_by_n=dict(days=[str(pd.Timestamp(x * DAY, unit="ms").date()) for x in top.index],
                               n_each=[int(x) for x in top["n"]], sum_each=[float(x) for x in top["sum"]],
                               pct_n=float(top["n"].sum() / tot_n), pct_sum=float(top["sum"].sum() / tot_s)))
    cr = {}
    for s in CRASH:
        di = int(pd.Timestamp(s, tz="UTC").value // 10**6 // DAY)
        x = df[df.day == di]
        cr[s] = dict(n=len(x), sum=float(x[c + "_net"].sum()), mean=float(x[c + "_net"].mean()) if len(x) else None,
                     sl_rate=float((x[c + "_r"] == 1).mean()) if len(x) else None,
                     pct_total_sum=float(x[c + "_net"].sum() / tot_s))
    cdays = [int(pd.Timestamp(s, tz="UTC").value // 10**6 // DAY) for s in CRASH]
    r = df[~df.day.isin(cdays)]
    res["crash_days"] = cr
    res["excl_crash"] = dict(n=len(r), pooled_mean=float(r[c + "_net"].mean()))
    return res


def to_min(s):
    t = pd.to_datetime(s, utc=True, errors="coerce")
    out = np.full(len(t), np.nan)
    ok = ~t.isna()
    out[ok.to_numpy()] = (t[ok].astype("int64") // 10**6 // MIN).to_numpy()  # pandas 2: datetime64[ns, UTC] -> ns
    return out


def m4(df, c, lin, base):
    L = lin.set_index("symbol")
    st = df.sym.map(L["status"])
    fr = df.sym.map(L["fr_min"]); lr = df.sym.map(L["lr_min"])
    miss = st.isna()
    r_stat = st.isin(["index", "stable/fiat-like"])
    ent = df.t.to_numpy(np.int64) + 1
    ext = df[c + "_k"].to_numpy(np.int64)
    r_head = (~fr.isna()) & (ent < fr.fillna(-1).to_numpy())
    r_tail = (~lr.isna()) & (ext > lr.fillna(np.inf).to_numpy())
    bad = r_stat | r_head | r_tail
    r = df[~bad.to_numpy()]
    p = pooled(r, c)
    p.pop("bvar")
    syms = sorted(df.loc[bad.to_numpy(), "sym"].unique().tolist())
    return dict(n_missing_lineage=int(miss.sum()), missing_syms=sorted(df.loc[miss.to_numpy(), "sym"].unique().tolist()),
                n_excl_status=int(r_stat.sum()), n_excl_head=int(r_head.sum()), n_excl_tail=int(r_tail.sum()),
                n_excl_total=int(bad.sum()), excl_syms=syms,
                excl_sum=float(df.loc[bad.to_numpy(), c + "_net"].sum()),
                excl_mean=float(df.loc[bad.to_numpy(), c + "_net"].mean()) if bad.any() else None,
                clean=p, delta_mean_pp=(p["mean"] - base["mean"]) * 100)


def m5(df, c):
    d = df.groupby("day").agg(n=("t", "size"))
    df = df.assign(ntd=df.day.map(d["n"]), sl=(df[c + "_r"] == 1))
    bins = [(1, 1), (2, 4), (5, 9), (10, 19), (20, 49), (50, 10**9)]
    bk = {}
    for a, b in bins:
        x = df[(df.ntd >= a) & (df.ntd <= b)]
        lab = "%d-%s" % (a, b if b < 10**9 else "inf")
        bk[lab] = dict(days=int(x.day.nunique()), n=len(x), sl_rate=float(x.sl.mean()) if len(x) else None,
                       mean=float(x[c + "_net"].mean()) if len(x) else None, sum=float(x[c + "_net"].sum()),
                       sl_sum=float(x.loc[x.sl, c + "_net"].sum()))
    q90 = float(np.percentile(d["n"], 90))
    hi = df.ntd >= q90
    dsl = df.groupby("day").sl.agg(["sum", "mean", "size"])
    top10 = dsl.sort_values("sum", ascending=False, kind="mergesort").head(10)
    g3 = dsl[dsl["size"] >= 3]
    rho = float(pd.Series(g3["size"]).corr(pd.Series(g3["mean"]), method="spearman"))
    big = df.ntd >= 20
    return dict(sl_rate_all=float(df.sl.mean()), n_sl=int(df.sl.sum()), buckets=bk,
                top10pct_days=dict(q90_n=q90, ndays=int((d["n"] >= q90).sum()), pct_trades=float(hi.mean()),
                                   pct_sl=float(df.loc[df.sl, "ntd"].ge(q90).mean()),
                                   sl_rate_in=float(df.loc[hi, "sl"].mean()), sl_rate_out=float(df.loc[~hi, "sl"].mean())),
                top10_days_by_sl=dict(days=[str(pd.Timestamp(x * DAY, unit="ms").date()) for x in top10.index],
                                      sl_each=[int(x) for x in top10["sum"]], n_each=[int(x) for x in top10["size"]],
                                      pct_sl=float(top10["sum"].sum() / df.sl.sum())),
                spearman_ntd_slrate_days_ge3=dict(rho=rho, ndays=len(g3)),
                sl_sum_total=float(df.loc[df.sl, c + "_net"].sum()),
                sl_sum_ntd_ge20=float(df.loc[df.sl & big, c + "_net"].sum()),
                pct_sl_in_ntd_ge20=float(big[df.sl].mean()), pct_trades_ntd_ge20=float(big.mean()))


def m6(df, c, p72, pday):
    v = df[c + "_net"].to_numpy(float)
    x = v - v.mean()
    s2 = float(v.var(ddof=1))
    g = pd.DataFrame(dict(day=df.day.to_numpy(), x=x, x2=x * x)).groupby("day").agg(sx=("x", "sum"), sx2=("x2", "sum"), m=("x", "size"))
    num = float((g.sx ** 2 - g.sx2).sum()); den = float((g.m * (g.m - 1)).sum()) * s2
    icc = num / den
    mw = float((g.m ** 2).sum() / g.m.sum())
    deff = 1 + (mw - 1) * icc
    n = len(v); viid = s2 / n
    return dict(n=n, ndays=len(g), icc_within_day=icc, m_bar_w=mw, deff=deff, n_eff_icc=n / deff,
                n_eff_boot_day=n * viid / pday["bvar"], n_eff_boot_72h=n * viid / p72["bvar"],
                se_iid=viid ** .5, se_day=pday["bvar"] ** .5, se_72h=p72["bvar"] ** .5)


def m7(df):
    rows = {}
    for c in SHORT:
        v = df[c + "_net"].to_numpy(float)
        ym, yp = years_pos(v, df["year"].to_numpy())
        c72 = boot(v, df["b72"].to_numpy()); cd = boot(v, df["day"].to_numpy())
        br = [b for b in SHORT if b[2] == c[2]]
        g5 = sum(df[b + "_net"].mean() > 0 for b in br) >= 2
        lm = float(df["L" + c[1:] + "_net"].mean())
        G = dict(G2=yp >= 3, G3=len(v) >= 1500, G4=float((df[c + "_r"] == 1).mean()) <= .25, G5=bool(g5), G6=lm <= 0)
        g1_72 = c72["mean"] > 0 and c72["raw"][0] > 0 and c72["infl"][0] > 0
        g1_d = cd["mean"] > 0 and cd["raw"][0] > 0 and cd["infl"][0] > 0
        rest = all(G.values())
        rows[c] = dict(mean=c72["mean"], ci72_raw=c72["raw"], ci72_infl=c72["infl"], ciday_raw=cd["raw"], ciday_infl=cd["infl"],
                       nday=cd["nblock"], years_pos=yp, sl_rate=float((df[c + "_r"] == 1).mean()), long_mean=lm,
                       G1_72h=bool(g1_72), G1_day=bool(g1_d), **{k: bool(x) for k, x in G.items()},
                       GO_72h=bool(g1_72 and rest), GO_day=bool(g1_d and rest), changed=bool(g1_72 != g1_d))
    return rows


def posthoc(df, c):
    """NGOAI pre-reg (them sau khi thay top-|SumPnL| toan ngay AM): bo top-k ngay DUONG nhat; mean theo bucket n/ngay (chi bao cao)."""
    d = daily(df, c).sort_index()
    order = d["sum"].sort_values(ascending=False, kind="mergesort").index
    res = {}
    for k in (1, 3, 5, 10):
        r = df[~df.day.isin(order[:k])]
        res["drop_top_pos_k%d" % k] = dict(dropped=[str(pd.Timestamp(x * DAY, unit="ms").date()) for x in order[:k]],
                                           dropped_sum=float(d.loc[order[:k], "sum"].sum()), n=len(r),
                                           pooled_mean=float(r[c + "_net"].mean()))
    return res


def main():
    df = pd.read_csv(CSV)
    log.info("R1 trades %d", len(df))
    ems = (df.t.to_numpy(np.int64) + 2) * MIN - 1
    df["ems"] = ems; df["b72"] = ems // H72; df["day"] = ems // DAY
    df["year"] = pd.to_datetime(ems, unit="ms", utc=True).year
    assert df.ems.max() <= pd.Timestamp("2025-12-31 23:59:59", tz="UTC").value // 10**6, "DEV > 2025"
    out = dict(prereg="docs/prereg/PREREG_R1_ROBUST.md@9ce3c459", src_r1="3fea4f50", n=len(df))
    # parity bat buoc
    p = boot(df["S_B24_net"].to_numpy(float), df["b72"].to_numpy())
    par = dict(mean=p["mean"], raw=p["raw"], target_mean=0.00170, target_raw=[-0.00030, 0.00369])
    ok = abs(p["mean"] - 0.0017) < 1.5e-5 and abs(p["raw"][0] + 0.0003) < 1.5e-5 and abs(p["raw"][1] - 0.00369) < 1.5e-5
    rc = pd.read_csv(CSVC)
    mg = rc.merge(df[["sym", "t", "S_B24_net"]], on=["sym", "t"], how="left")
    par["r1c_n"] = len(rc); par["r1c_unmatched"] = int(mg.S_B24_net.isna().sum())
    par["r1c_tk24_maxabsdiff"] = float((mg.S_TK24_net - mg.S_B24_net).abs().max())
    ok = ok and par["r1c_unmatched"] == 0 and par["r1c_tk24_maxabsdiff"] <= 1e-9
    par["PASS"] = bool(ok)
    out["parity"] = par
    log.info("parity %s", par)
    if not ok:
        json.dump(out, open(OUTJ, "w"), indent=1); log.error("PARITY FAIL -> VOID"); sys.exit(2)
    lin = pd.read_csv(LIN)
    lin["fr_min"] = to_min(lin["first_real_ts"]); lin["lr_min"] = to_min(lin["last_real_ts"])
    rcm = rc.assign(ems=(rc.t.to_numpy(np.int64) + 2) * MIN - 1)
    rcm["day"] = rcm.ems // DAY
    r1c = {}
    for c in ("S_TK24", "S_LM24"):
        x = rcm[rcm[c + "_net"].notna()]
        r1c[c] = dict(n=len(x), pooled_mean=float(x[c + "_net"].mean()), **dayw(daily(x, c)))
    out["r1c_dayw"] = r1c
    for c in MAIN:
        p72 = pooled(df, c, "b72"); pday = pooled(df, c, "day")
        res = dict(base=dict(n=p72["n"], mean=p72["mean"], ci72_raw=p72["ci_raw"], ci72_infl=p72["ci_infl"],
                             ciday_raw=pday["ci_raw"], ciday_infl=pday["ci_infl"], yearly=p72["yearly"], sl_rate=p72["sl_rate"]))
        res["m1_dayweighted"] = m1(df, c)
        res["m2_drop_topk"] = m2(df, c)
        res["m3_perday"] = m3(df, c)
        res["m4_lineage"] = m4(df, c, lin, p72)
        res["m5_sl_by_day"] = m5(df, c)
        res["m6_cluster"] = m6(df, c, p72, pday)
        d1 = res["m1_dayweighted"]["mean"] > 0 and res["m1_dayweighted"]["years_pos"] >= 3
        d2 = all(v["pooled_mean"] > 0 for v in res["m2_drop_topk"].values())
        d3 = res["m4_lineage"]["clean"]["mean"] > 0
        res["verdict"] = dict(D1=bool(d1), D2=bool(d2), D3=bool(d3), BEN=bool(d1 and d2 and d3))
        out[c] = res
        log.info("%s verdict %s", c, res["verdict"])
    out["m7_gates"] = m7(df)
    for c in MAIN:
        out[c]["posthoc_NOT_PREREG"] = posthoc(df, c)
    json.dump(out, open(OUTJ, "w"), indent=1, default=float)
    log.info("wrote %s", OUTJ)


if __name__ == "__main__":
    main()
