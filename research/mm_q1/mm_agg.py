"""MM_Q1 aggregation: tier x period stats, bootstrap CI by calendar hour, criterion, descriptives, validation summaries."""
import os, json, glob, sys
import numpy as np, pandas as pd, pyarrow.parquet as pq
RES = sys.argv[1]   # mm_wk/res (run 1) or mm_wk/res2 (ADDENDUM1 rerun)
OUT = sys.argv[2]
os.makedirs(OUT, exist_ok=True)
TIER = {**{s: "big" for s in ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT"]},
        **{s: "mid" for s in ["NEIROUSDT", "TAOUSDT", "VIRTUALUSDT", "1000SHIBUSDT"]},
        **{s: "small" for s in ["NEOUSDT", "PORTALUSDT", "MASKUSDT", "NXPCUSDT"]}}
LATS = (0, 100, 300); HS = (1, 10, 60, 300); FEE = 0.0002
recs = []
for f in glob.glob(f"{RES}/*/*.json"):
    with open(f) as fh:
        recs.append(json.load(fh))
A = pd.DataFrame([{k: r.get(k) for k in ("sym", "H", "period", "status", "r_btc", "r_sym", "r_sym_src", "r_btc_src", "sec", "wire_bytes")} for r in recs])
rej = A.groupby(["period", "sym", "status"]).size().unstack(fill_value=0)
ok = [r for r in recs if r["status"] == "ok"]
rows = []
for r in ok:
    d = {"sym": r["sym"], "tier": TIER[r["sym"]], "H": int(r["H"]), "period": r["period"], "r_sym": r["r_sym"], "r_btc": r["r_btc"], "r_sym_src": r["r_sym_src"]}
    d.update({k: v for k, v in r["info"].items() if not isinstance(v, (list, tuple))})
    d.update(r["q"]); d.update(r["res"])
    rows.append(d)
T = pd.DataFrame(rows)
assert T.H.dtype == np.int64
T["hod"] = (T.H // 3600000) % 24
T = T.sort_values(["period", "tier", "sym", "H"]).reset_index(drop=True)

def cfg_cols(L, d, rule, h):
    p = [f"L{L}_d{d}_{rule}_{sd}" for sd in ("bid", "ask")]
    return [x + f"_h{h}_sum" for x in p], [x + f"_h{h}_nv" for x in p], [x + "_n" for x in p]

def stats(sub, L=300, d=0, rule="cons", h=60, boot=True):
    sc, nc, fc = cfg_cols(L, d, rule, h)
    S = sub[sc].sum(axis=1).to_numpy(); N = sub[nc].sum(axis=1).to_numpy().astype(float)
    g = pd.DataFrame({"H": sub.H.to_numpy(), "S": S, "N": N}).groupby("H").sum()
    out = {"n_symhours": int(len(sub)), "n_fill": int(sub[fc].sum().sum()), "n_valid": int(N.sum())}
    if N.sum() == 0:
        return out
    gross = S.sum() / N.sum(); out["gross_bps"] = gross * 1e4; out["net_bps"] = (gross - FEE) * 1e4
    out["fills_per_symhour_med"] = float(np.median(sub[fc].sum(axis=1)))
    if boot:
        rng = np.random.default_rng(7)
        Sc = g.S.to_numpy() - FEE * g.N.to_numpy(); Nc = g.N.to_numpy()
        idx = rng.integers(0, len(g), size=(10000, len(g)))
        bs = Sc[idx].sum(axis=1) / Nc[idx].sum(axis=1)
        out["ci_lo_bps"], out["ci_hi_bps"] = (np.percentile(bs, [2.5, 97.5]) * 1e4).tolist()
        out["n_clusters"] = int(len(g))
    return out

summary = {"rejections": {f"{p}|{s}": v for (p, s), v in rej.to_dict("index").items()}}
# criterion table
crit = []
for d in (0, 1):
    for tier in ("big", "mid", "small"):
        row = {"depth": d, "tier": tier}
        okall = True
        for per in ("D", "K"):
            sub = T[(T.tier == tier) & (T.period == per)]
            st = stats(sub, 300, d, "cons", 60)
            v1 = (sub.v1_ok_buy.sum() + sub.v1_ok_sell.sum()) / (sub.v1_n_buy.sum() + sub.v1_n_sell.sum())
            st["v1"] = float(v1)
            row[per] = st
            okp = st.get("net_bps", -1) > 0 and st.get("ci_lo_bps", -1) > 0 and st.get("fills_per_symhour_med", 0) >= 20 and v1 >= 0.99
            row[per + "_pass"] = bool(okp); okall &= okp
        row["pass"] = bool(okall)
        crit.append(row)
summary["criterion"] = crit
# all configs h60 + horizons
allc = []
for per in ("D", "K"):
    for tier in ("big", "mid", "small"):
        sub = T[(T.tier == tier) & (T.period == per)]
        for L in LATS:
            for d in (0, 1):
                for rule in ("cons", "opt"):
                    for h in HS:
                        st = stats(sub, L, d, rule, h, boot=(h == 60))
                        allc.append({"period": per, "tier": tier, "L": L, "d": d, "rule": rule, "h": h, **st})
AC = pd.DataFrame(allc); AC.to_csv(f"{OUT}/configs.csv", index=False)
# per symbol
ps = []
for (per, sym), sub in T.groupby(["period", "sym"]):
    st = stats(sub, 300, 0, "cons", 60)
    ps.append({"period": per, "sym": sym, "tier": TIER[sym], "spread_bps_med": float(sub.spread_bps_med.median()), "spread_ticks_med": float(sub.spread_ticks_med.median()),
               "v1": float((sub.v1_ok_buy.sum() + sub.v1_ok_sell.sum()) / (sub.v1_n_buy.sum() + sub.v1_n_sell.sum())), "v1_min_hour": float(((sub.v1_ok_buy + sub.v1_ok_sell) / (sub.v1_n_buy + sub.v1_n_sell)).min()),
               "crossed_mean": float(sub.crossed_frac.mean()), **st})
PS = pd.DataFrame(ps); PS.to_csv(f"{OUT}/per_symbol.csv", index=False)
# tier spread, hour of day, profit/day
tier_desc = []
for per in ("D", "K"):
    for tier in ("big", "mid", "small"):
        sub = T[(T.tier == tier) & (T.period == per)]
        st = stats(sub, 300, 0, "cons", 60, boot=False)
        hod = {}
        for a, b in ((0, 8), (8, 16), (16, 24)):
            s2 = sub[(sub.hod >= a) & (sub.hod < b)]
            hod[f"{a}-{b}"] = {k: stats(s2, 300, 0, "cons", 60, boot=False).get(k) for k in ("n_symhours", "net_bps", "gross_bps")}
        fph = st.get("fills_per_symhour_med", 0)
        tier_desc.append({"period": per, "tier": tier, "spread_bps_med": float(sub.spread_bps_med.median()), "spread_ticks_med": float(sub.spread_ticks_med.median()),
                          "net_bps": st.get("net_bps"), "fills_per_50min_med": fph,
                          "usd_per_day_per_symbol_100usd_lot": st.get("net_bps", 0) / 1e4 * fph * 24 * 100,
                          "usd_per_day_x1.2": st.get("net_bps", 0) / 1e4 * fph * 1.2 * 24 * 100, "hod": hod})
summary["tier_desc"] = tier_desc
# V1/V2/V5
v = {}
v["V1_per_symhour_min"] = float(((T.v1_ok_buy + T.v1_ok_sell) / (T.v1_n_buy + T.v1_n_sell)).min())
v["V1_per_symhour_p5"] = float(((T.v1_ok_buy + T.v1_ok_sell) / (T.v1_n_buy + T.v1_n_sell)).quantile(0.05))
v["V2_trade_dup"] = int(T.trade_dup.sum()); v["V2_trade_off_tick"] = int(T.trade_off_tick.sum()); v["V2_dup_msgs"] = int(T.dup_msgs.sum())
v["V2_nquote_L0d0_not3000"] = int((T.L0_d0_nquote != 3000).sum()); v["V2_E_inconsistent_rows"] = int(T.E_inconsistent_rows.sum()); v["V2_nonupdate_rows"] = int(T.n_nonupdate_rows.sum())
v["V2_r_sym_src"] = T.r_sym_src.value_counts().to_dict()
if "trade_zero_dropped" in T:
    v["trade_zero_dropped"] = int(T.trade_zero_dropped.sum()); v["trade_na"] = int(T.trade_na.sum()); v["trade_na_nonzero"] = int(T.trade_na_nonzero.sum())
    v["trade_zero_frac_by_tier"] = (T.groupby("tier").trade_zero_dropped.sum() / T.groupby("tier").n_trades_hour.sum()).to_dict()
    ty = set()
    for r in ok:
        ty |= set(r["info"].get("trade_nonmarket_types", []))
    v["trade_nonmarket_types"] = sorted(ty)
v5 = {}
for key, sub in list(T.groupby("tier")) + [("all", T)]:
    as0 = sub.v5_as0.sum() / sub.v5_n.sum(); hs = sub.v5_hs.sum() / sub.v5_n.sum()
    v5[key] = {"n": int(sub.v5_n.sum()), "as0_bps": as0 * 1e4, "halfspread_bps": hs * 1e4, "ratio": float(as0 / -hs), "mid_mk60_bps": float(sub.v5_mk60.sum() / sub.v5_nv60.sum() * 1e4)}
v["V5"] = v5
# V2b: r_sym from chd kline vs Oracle kline (D, kline-sourced)
dd = T[(T.period == "D") & T.r_sym.notna()]
diffs = []
for m, sub in dd.groupby(pd.to_datetime(dd.H, unit="ms").dt.strftime("%Y-%m")):
    k = pq.read_table(f"/home/ubuntu/vz_e1/raw/kline1m-{m}.parquet", columns=["ts", "sym", "open", "close"], filters=[("sym", "in", sorted(sub.sym.unique()))]).to_pandas()
    k["sym"] = k.sym.astype(str); k = k.set_index(["sym", "ts"])
    for _, r in sub.iterrows():
        try:
            o = k.loc[(r.sym, r.H), "open"]; c = k.loc[(r.sym, r.H + 59 * 60000), "close"]
            diffs.append(abs(c / o - 1 - r.r_sym))
        except KeyError:
            diffs.append(np.nan)
diffs = np.array(diffs, float)
v["V2b"] = {"n": int(len(diffs)), "n_missing_oracle": int(np.isnan(diffs).sum()), "max_abs_diff": float(np.nanmax(diffs)) if len(diffs) else None, "n_gt_1e-9": int((diffs > 1e-9).sum())}
summary["validation"] = v
# LIQX_S1 descriptive on D accepted hours
mk = pd.read_parquet("/home/ubuntu/claude_master/liqx_wk/s1/mkt.parquet", columns=["T", "r_mkt", "I_mkt", "mkt_valid"])
mk = mk[(mk["T"] > 1751328000000) & (mk["T"] <= 1767225600000)].set_index("T")
hrs = np.sort(T[T.period == "D"].H.unique()); lx = []
for H in hrs:
    b = mk.reindex(H + np.arange(1, 13, dtype=np.int64) * 300000)
    lx.append({"H": int(H), "n_b": int(b.r_mkt.notna().sum()), "ew1h": float(b.r_mkt.sum()), "Imax": float(b.I_mkt.max())})
LX = pd.DataFrame(lx)
summary["liqx_desc_D"] = {"n_hours": int(len(LX)), "fail_ew": int((LX.ew1h.abs() >= 0.015).sum()), "fail_I": int((LX.Imax >= 0.0064917563071208014).sum()), "incomplete_buckets": int((LX.n_b < 12).sum())}
keep = ["sym", "tier", "period", "H", "hod", "r_sym", "r_btc", "tick", "rows", "n_msgs", "spread_bps_med", "spread_ticks_med", "crossed_frac", "v1_n_buy", "v1_ok_buy", "v1_n_sell", "v1_ok_sell", "n_trades_hour"]
keep += [c for c in T.columns if c.startswith(("L0_", "L100_", "L300_", "v5_"))]
T[keep].to_csv(f"{OUT}/symhour_stats.csv.gz", index=False)
with open(f"{OUT}/summary.json", "w") as f:
    json.dump(summary, f, indent=1, default=float)
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40); pd.set_option("display.max_rows", 400)
print(rej.to_string())
for c in crit:
    print(json.dumps(c))
print(AC[(AC.h == 60)][["period", "tier", "L", "d", "rule", "n_fill", "gross_bps", "net_bps", "ci_lo_bps", "ci_hi_bps", "fills_per_symhour_med"]].round(3).to_string(index=False))
print(AC[(AC.L == 300) & (AC.d == 0) & (AC.rule == "cons")][["period", "tier", "h", "n_valid", "gross_bps", "net_bps"]].round(3).to_string(index=False))
print(PS.round(3).to_string(index=False))
print(json.dumps(tier_desc, default=float))
print(json.dumps(v, default=float)); print(json.dumps(summary["liqx_desc_D"]))
