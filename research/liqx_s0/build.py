"""LIQX_S0 step 2: bucket table (sym x 5-min T) for samples A/B (Tardis day-01 2022-2025).
Window [T-5m, T); OI snapshots at T-5m and T (metrics create_time); closes of 1m bars open_time T-6m and T-1m;
taker sums over bars open_time T-5m..T-1m. All ts int64 ms UTC. Prereg docs/prereg/PREREG_LIQX_S0.md."""
import pyarrow.parquet as pq, pandas as pd, numpy as np, os
WK = os.path.expanduser("~/claude_master/liqx_wk")
KL = "/home/ubuntu/vz_e1/raw/kline1m-%04d-%02d.parquet"
MET = "/home/ubuntu/vz/out/metrics5m/%04d/%04d-%02d.parquet"
TAR = WK + "/tardis/liquidations_%04d-%02d-01_PERPETUALS.csv.gz"
DAY, B5 = 86_400_000, 300_000


def ms(y, m, d=1):
    return int(pd.Timestamp(year=y, month=m, day=d, tz="UTC").value // 1_000_000)


def universe(dq, d0):
    w = dq[(dq.day >= d0 - 30 * DAY) & (dq.day < d0)]
    s = w.groupby("sym").qv.sum().sort_values(ascending=False)
    top = s.index[:100].tolist()
    return {sym: i + 1 for i, sym in enumerate(top)}


def read_kline(paths, syms, lo, hi):
    out = []
    for p in paths:
        t = pq.read_table(p, columns=["ts", "sym", "close", "quote_volume", "taker_buy_quote"],
                          filters=[("ts", ">=", lo), ("ts", "<", hi)]).to_pandas()
        t["sym"] = t.sym.astype(str)
        out.append(t[t.sym.isin(syms)])
    k = pd.concat(out, ignore_index=True)
    assert k.ts.dtype == np.int64
    assert not k.duplicated(["sym", "ts"]).any()
    return k


def grid_for(d0, uni):
    T = d0 + B5 * np.arange(1, 289, dtype=np.int64)
    g = pd.DataFrame({"sym": np.repeat(list(uni), len(T)), "T": np.tile(T, len(uni))})
    g["rank"] = g.sym.map(uni).astype("int64")
    return g


def attach(g, k, met, liq, d0):
    """k: kline (sym,ts,close,quote_volume,taker_buy_quote); met: (sym,ts,oi,oi_value); liq: (sym,ts_ms,side,notional)."""
    m = met.rename(columns={"ts": "T", "oi": "oi1", "oi_value": "oiv1"})
    g = g.merge(m, on=["sym", "T"], how="left")
    m0 = met.assign(T=met.ts + B5).drop(columns="ts").rename(columns={"oi": "oi0", "oi_value": "oiv0"})
    g = g.merge(m0, on=["sym", "T"], how="left")
    c1 = k[["sym", "ts", "close"]].assign(T=k.ts + 60_000).drop(columns="ts").rename(columns={"close": "c1"})
    c0 = k[["sym", "ts", "close"]].assign(T=k.ts + 360_000).drop(columns="ts").rename(columns={"close": "c0"})
    g = g.merge(c1, on=["sym", "T"], how="left").merge(c0, on=["sym", "T"], how="left")
    kb = k.assign(T=(k.ts // B5 + 1) * B5)
    s = kb.groupby(["sym", "T"]).agg(nbar=("ts", "size"), qv=("quote_volume", "sum"), tbq=("taker_buy_quote", "sum")).reset_index()
    g = g.merge(s, on=["sym", "T"], how="left")
    lb = liq.assign(T=(liq.ts_ms // B5 + 1) * B5)
    for side, nm in (("long", "liq_long"), ("short", "liq_short")):
        x = lb[lb.side == side].groupby(["sym", "T"]).agg(**{nm: ("notional", "sum"), "n_" + side: ("notional", "size")}).reset_index()
        g = g.merge(x, on=["sym", "T"], how="left")
        g[nm] = g[nm].fillna(0.0)
        g["n_" + side] = g["n_" + side].fillna(0).astype("int64")
    g["nbar"] = g.nbar.fillna(0).astype("int64")
    g["valid"] = g[["oiv0", "oiv1", "c0", "c1"]].notna().all(axis=1) & (g.nbar == 5)
    g["day"] = np.int64(d0)
    assert g["T"].dtype == np.int64 and g["day"].dtype == np.int64
    return g


def main():
    dq = pd.read_parquet(WK + "/daily_qv.parquet")
    res, log = [], []
    for y in range(2022, 2026):
        for m in range(1, 13):
            d0 = ms(y, m)
            uni = universe(dq, d0)
            py, pm = (y, m - 1) if m > 1 else (y - 1, 12)
            k = read_kline([KL % (py, pm), KL % (y, m)], set(uni), d0 - 360_000, d0 + DAY)
            met = pq.read_table(MET % (y, y, m), columns=["ts", "sym", "oi", "oi_value"],
                                filters=[("ts", ">=", d0), ("ts", "<=", d0 + DAY)]).to_pandas()
            met["sym"] = met.sym.astype(str)
            met = met[met.sym.isin(set(uni))]
            assert met.ts.dtype == np.int64 and not met.duplicated(["sym", "ts"]).any()
            t = pd.read_csv(TAR % (y, m), dtype={"timestamp": "int64"})
            liq = pd.DataFrame({"sym": t.symbol, "ts_ms": (t.timestamp // 1000).astype("int64"),
                                "side": t.side.map({"sell": "long", "buy": "short"}).fillna("unknown"),
                                "notional": t.price * t.amount})
            assert liq.ts_ms.min() >= d0 and liq.ts_ms.max() < d0 + DAY
            nunk = int((liq.side == "unknown").sum())
            g = attach(grid_for(d0, uni), k, met, liq, d0)
            g["sample"] = "A" if y <= 2023 else "B"
            kc = k[(k.ts >= d0)].groupby("sym").size()
            liq_in = liq[liq.sym.isin(set(uni))]
            log.append(dict(day=pd.Timestamp(d0, unit="ms").date().isoformat(), n_uni=len(uni),
                            sym_kline1440=int((kc == 1440).sum()), sym_with_met=met.sym.nunique(),
                            valid=int(g.valid.sum()), buckets=len(g), liq_rows_all=len(liq), liq_rows_uni=len(liq_in),
                            liq_long_usd_uni=float(liq_in[liq_in.side == "long"].notional.sum()),
                            liq_long_usd_all=float(liq[liq.side == "long"].notional.sum()), unknown_side=nunk))
            print(log[-1], flush=True)
            res.append(g)
    G = pd.concat(res, ignore_index=True)
    G.to_parquet(WK + "/buckets_AB.parquet", index=False)
    pd.DataFrame(log).to_csv(WK + "/build_AB_log.csv", index=False)
    print("done", len(G), int(G.valid.sum()))


if __name__ == "__main__":
    main()
