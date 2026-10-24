"""FEE0 step0 (c)(d): USDC-M vs USDT-M price agreement (BTC/ETH) + spread (Vision bookTicker 2024Q1) + depth (bookDepth).
No PnL. Usage: f0_step0.py c | d"""
import glob, io, json, os, sys, zipfile, urllib.request
import numpy as np, pandas as pd
WK = os.path.expanduser("~/claude_master/fee0_wk")
SCR = os.path.expanduser("~/claude_master/1016/screen")
D = "https://data.binance.vision/data/futures/um"
COLS = ["ot", "open", "high", "low", "close", "vol", "ct", "qv", "n", "tbv", "tbqv", "ig"]


def read_k(p):
    with zipfile.ZipFile(p) as z:
        b = z.read(z.namelist()[0])
    x = pd.read_csv(io.BytesIO(b), header=None, dtype=str)
    if not x.iloc[0, 0].strip().isdigit():
        x = x.iloc[1:]
    x.columns = COLS[: x.shape[1]]
    out = pd.DataFrame({"ts": x.ot.astype(np.int64)})
    for c in ("open", "high", "low", "close", "vol", "qv", "tbv", "tbqv"):
        out[c] = x[c].astype(np.float64).to_numpy()
    return out


def load_usdc(s):
    M = pd.concat([read_k(p) for p in sorted(glob.glob(f"{WK}/k1m/{s}/*.zip"))], ignore_index=True)
    M = M.drop_duplicates("ts").sort_values("ts").reset_index(drop=True)
    assert M.ts.dtype == np.int64 and (M.ts % 60000 == 0).all()
    return M


def step_c():
    res = {}
    for a in ("BTC", "ETH"):
        U = load_usdc(a + "USDC")
        T = pd.read_parquet(f"{SCR}/m1_{a}USDT.parquet")
        T = pd.DataFrame({"ts": (T.index.values.astype("datetime64[ms]").astype(np.int64)), "close": T.close.values})
        t0 = int(U.ts.iloc[0]); t1 = int(U.ts.iloc[-1])
        exp = (t1 - t0) // 60000 + 1
        J = U[["ts", "close"]].merge(T, on="ts", suffixes=("_c", "_t"))
        J = J.set_index("ts")
        lr = np.log(J).diff().dropna()
        r = {"usdc_first_ts": t0, "usdc_first_utc": str(pd.to_datetime(t0, unit="ms")), "usdc_last_utc": str(pd.to_datetime(t1, unit="ms")),
             "usdc_bars": int(len(U)), "usdc_bars_expected": int(exp), "usdc_coverage": float(len(U) / exp), "joined": int(len(J))}
        r["corr_1m"] = float(lr.close_c.corr(lr.close_t))
        for h, lab in ((60, "1h"), (15, "15m"), (1440, "1d")):
            g = J[(J.index // 60000) % h == 0]
            g = g[np.diff(np.r_[g.index[0] - h * 60000, g.index]) == h * 60000]
            lg = np.log(g).diff().dropna()
            r["corr_" + lab] = float(lg.close_c.corr(lg.close_t))
            r["te_bps_" + lab] = float((lg.close_c - lg.close_t).std() * 1e4)
        dev = np.log(J.close_c / J.close_t) * 1e4
        r["dev_bps_median"] = float(dev.median()); r["absdev_bps_p50"] = float(dev.abs().median())
        r["absdev_bps_p99"] = float(dev.abs().quantile(0.99)); r["absdev_bps_max"] = float(dev.abs().max())
        dd = dev.groupby(dev.index // 86400000).mean()
        r["daily_mean_dev_bps_min_max"] = [float(dd.min()), float(dd.max())]
        res[a] = r; print(a, r)
    json.dump(res, open(WK + "/step0_c.json", "w"), indent=1)


def bt_spread(s, d):
    p = f"{WK}/bt/{s}-{d}.zip"
    os.makedirs(WK + "/bt", exist_ok=True)
    urllib.request.urlretrieve(f"{D}/daily/bookTicker/{s}/{s}-bookTicker-{d}.zip", p)
    out = []
    with zipfile.ZipFile(p) as z:
        with z.open(z.namelist()[0]) as f:
            for ch in pd.read_csv(f, chunksize=2_000_000, usecols=["best_bid_price", "best_ask_price", "transaction_time"]):
                b, a = ch.best_bid_price.to_numpy(float), ch.best_ask_price.to_numpy(float)
                sec = ch.transaction_time.to_numpy(np.int64) // 1000
                rs = (a - b) / ((a + b) / 2) * 1e4
                out.append(pd.DataFrame({"sec": sec, "rs": rs}))
    os.remove(p)
    x = pd.concat(out).groupby("sec").rs.last()
    return {"n_sec": int(len(x)), "spread_bps_p50": float(x.median()), "spread_bps_mean": float(x.mean()), "spread_bps_p90": float(x.quantile(0.9))}


def bd_depth(s, d):
    p = f"{WK}/bt/{s}-bd-{d}.zip"
    urllib.request.urlretrieve(f"{D}/daily/bookDepth/{s}/{s}-bookDepth-{d}.zip", p)
    x = pd.read_csv(p); os.remove(p)
    g = x.groupby("percentage").notional.median()
    return {str(k): float(v) for k, v in g.items()}


def step_d():
    syms_bt = ["BTCUSDC", "ETHUSDC", "BTCUSDT", "ETHUSDT", "SOLUSDC", "XRPUSDC", "BNBUSDC", "DOGEUSDC", "LINKUSDC", "SUIUSDC", "1000PEPEUSDC", "AVAXUSDC", "WLDUSDC", "ORDIUSDC", "1000SHIBUSDC"]
    days = ["2024-02-14", "2024-03-13", "2024-03-27"]
    res = {"bookTicker": {}, "bookDepth": {}}
    for s in syms_bt:
        for d in days:
            if s.startswith("1000SHIB") and d < "2024-03-28":
                continue
            try:
                res["bookTicker"][f"{s}|{d}"] = bt_spread(s, d); print(s, d, res["bookTicker"][f"{s}|{d}"], flush=True)
            except Exception as e:  # noqa: BLE001
                print("FAIL", s, d, e, flush=True)
    for s in ("BTCUSDC", "BTCUSDT", "ETHUSDC", "ETHUSDT", "SOLUSDC", "SOLUSDT"):
        for d in ("2024-03-13", "2025-06-11", "2026-03-11", "2026-09-16"):
            try:
                res["bookDepth"][f"{s}|{d}"] = bd_depth(s, d); print(s, d, res["bookDepth"][f"{s}|{d}"].get("1.0"), res["bookDepth"][f"{s}|{d}"].get("-1.0"), flush=True)
            except Exception as e:  # noqa: BLE001
                print("FAIL bd", s, d, e, flush=True)
    json.dump(res, open(WK + "/step0_d.json", "w"), indent=1)


{"c": step_c, "d": step_d}[sys.argv[1]]()
