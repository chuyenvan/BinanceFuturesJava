"""LIQX_S0 forward sample F (2026-10-16..22): Vision daily 1m klines + daily metrics, real liq = own forceOrder collector."""
import pandas as pd, numpy as np, os, sys, zipfile, io, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build import attach, grid_for, DAY, B5, FIX, SUFFIX
WK = os.path.expanduser("~/claude_master/liqx_wk"); FW = WK + "/fwd"
COL = os.path.expanduser("~/collect/liq")
DAYS = ["2026-10-%02d" % d for d in range(16, 23)]


def rzip(p, names):
    if not os.path.exists(p):
        return None
    z = zipfile.ZipFile(p); txt = z.read(z.namelist()[0]).decode()
    lines = [l for l in txt.splitlines() if l and l[0].isdigit()]
    return pd.read_csv(io.StringIO("\n".join(lines)), header=None, names=names)


KN = ["open_time", "open", "high", "low", "close", "volume", "close_time", "quote_volume", "count", "tbv", "taker_buy_quote", "ignore"]
MN = ["create_time", "symbol", "oi", "oi_value", "a", "b", "c", "d"]


def dms(s):
    return int(pd.Timestamp(s, tz="UTC").value // 1_000_000)


def main():
    uni_df = pd.read_csv(FW + "/uni_F.csv")
    uni = dict(zip(uni_df.sym, uni_df["rank"]))
    res, log = [], []
    for D in DAYS:
        d0 = dms(D); dprev = pd.Timestamp(d0 - DAY, unit="ms").date().isoformat(); dnext = pd.Timestamp(d0 + DAY, unit="ms").date().isoformat()
        ks, ms_ = [], []
        for s in uni:
            for dd in (dprev, D):
                k = rzip(f"{FW}/k1m/{s}-{dd}.zip", KN)
                if k is not None:
                    ks.append(pd.DataFrame({"sym": s, "ts": k.open_time.astype("int64"), "close": k.close,
                                            "quote_volume": k.quote_volume, "taker_buy_quote": k.taker_buy_quote}))
            for dd in ((dprev, D) if FIX else (D, dnext)):
                m = rzip(f"{FW}/met/{s}-{dd}.zip", MN)
                if m is not None:
                    ts = (pd.to_datetime(m.create_time, utc=True).astype("int64") // 1_000_000).astype("int64")
                    if FIX:  # ADDENDUM: 2026 Vision metrics = snapshot at create_time+5m (v5b_switch.json BTC 2026-10-01)
                        ts = ts + B5
                    ms_.append(pd.DataFrame({"sym": s, "ts": ts, "oi": m.oi, "oi_value": m.oi_value}))
        k = pd.concat(ks, ignore_index=True); k = k[(k.ts >= d0 - 360_000) & (k.ts < d0 + DAY)]
        met = pd.concat(ms_, ignore_index=True); met = met[(met.ts >= d0) & (met.ts <= d0 + DAY)].sort_values(["sym", "ts"])
        ndup_m = int(met.duplicated(["sym", "ts"]).sum()); met = met.drop_duplicates(["sym", "ts"])
        assert k.ts.dtype == np.int64 and met.ts.dtype == np.int64 and not k.duplicated(["sym", "ts"]).any()
        c = pd.read_csv(f"{COL}/{D}.csv.gz", dtype={"event_time": "int64", "trade_time": "int64"})
        nonfill = int((c.status != "FILLED").sum())
        cf = c[c.status == "FILLED"]
        liq = pd.DataFrame({"sym": cf.symbol, "ts_ms": cf.trade_time.astype("int64"),
                            "side": cf.side.map({"SELL": "long", "BUY": "short"}), "notional": cf.avg_price * cf.filled_qty})
        liq = liq[(liq.ts_ms >= d0) & (liq.ts_ms < d0 + DAY)]
        g = attach(grid_for(d0, uni), k, met, liq, d0)
        # collector gaps > 180 s (all symbols) using neighbour days too
        ev = [c.trade_time.values]
        for dd in (dprev, dnext):
            p = f"{COL}/{dd}.csv.gz"
            if os.path.exists(p):
                ev.append(pd.read_csv(p, usecols=["trade_time"]).trade_time.values.astype("int64"))
        ev = np.sort(np.concatenate(ev)); dt = np.diff(ev); gi = np.where(dt > 180_000)[0]
        gaps = [(int(ev[i]), int(ev[i + 1])) for i in gi if ev[i + 1] > d0 and ev[i] < d0 + DAY]
        bad = np.zeros(len(g), bool)
        for a, b in gaps:
            bad |= (g["T"].values - B5 < b) & (g["T"].values > a)
        g["gap"] = bad; g["valid"] = g.valid & ~bad
        g["sample"] = "F"
        # cross-check Vision close vs collector kline close
        ck = pd.read_csv(f"{COL}/kline1m/{D}.csv.gz", usecols=["open_time", "symbol", "close"])
        ck = ck[ck.symbol.isin(set(uni))].drop_duplicates(["symbol", "open_time"])
        mm = ck.merge(k, left_on=["symbol", "open_time"], right_on=["sym", "ts"], how="inner")
        match = float((np.abs(mm.close_x - mm.close_y) <= 1e-12 * np.abs(mm.close_y) + 1e-12).mean()) if len(mm) else float("nan")
        log.append(dict(day=D, n_uni=len(uni), sym_kline=int(k[k.ts >= d0].groupby("sym").size().eq(1440).sum()),
                        sym_met=int(met.sym.nunique()), met_dup=ndup_m, valid=int(g.valid.sum()), buckets=len(g),
                        gaps=[(pd.Timestamp(a, unit="ms").strftime("%H:%M:%S"), round((b - a) / 1000)) for a, b in gaps],
                        gap_buckets=int(bad.sum()), liq_rows=len(liq), nonfilled=nonfill,
                        liq_rows_uni=int(liq.sym.isin(set(uni)).sum()), close_xcheck_n=len(mm), close_xcheck_match=match))
        print(log[-1], flush=True)
        res.append(g)
    G = pd.concat(res, ignore_index=True)
    G.to_parquet(WK + "/buckets_F%s.parquet" % SUFFIX, index=False)
    json.dump(log, open(WK + "/build_F_log%s.json" % SUFFIX, "w"), indent=1)


if __name__ == "__main__":
    main()
