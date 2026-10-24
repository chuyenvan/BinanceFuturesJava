"""FEE0_RESCORE Q4 (E1 H-F imbalance M15, imb_dev15, h=12h) tren universe USDC-M PIT.
Usage: f0_q4.py build_c | build_e | pnl
C: USDC-M 1m (Vision monthly, tai theo symbol roi xoa zip). E: 5 symbol launch (BTC ETH BNB SOL XRP) USDT-M ~/vz_e1/raw 2022-2023."""
import glob, json, logging, os, shutil, sys, urllib.request, urllib.error
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f0_common as F  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("q4")
H = 12 * 3_600_000
MIN_QV = 50000.0
WS = (5, 15, 30)
RAW = os.path.expanduser("~/vz_e1/raw")
E_SYMS = ["BTC", "ETH", "BNB", "SOL", "XRP"]
MONTHS_C = [f"{y}-{m:02d}" for y in (2024, 2025, 2026) for m in range(1, 13) if (y, m) <= (2026, 9)]
URL = "https://data.binance.vision/data/futures/um/monthly/klines/{s}/1m/{s}-1m-{m}.zip"


def moc_table(M, sym, t_end):
    """M: ts int64 sorted unique, close high low qv tbqv. returns moc rows with features + fwd low/high + exit close."""
    M = M.sort_values("ts").reset_index(drop=True)
    assert M.ts.is_unique and M.ts.dtype == np.int64
    qv = M.qv.replace(0, np.nan)
    imb = 2.0 * M.tbqv / qv - 1.0
    prev = imb.shift(1).rolling(15, min_periods=1).mean()
    M = M.assign(imb=imb, imbd=imb - prev)
    t0, t1 = int(M.ts.iloc[0]), int(M.ts.iloc[-1])
    grid = np.arange(t0, t1 + F.MIN, F.MIN, dtype=np.int64)
    pos = np.searchsorted(grid, M.ts.to_numpy())
    lo = np.full(len(grid), np.nan); hi = np.full(len(grid), np.nan); cl = np.full(len(grid), np.nan)
    lo[pos] = M.low.to_numpy(); hi[pos] = M.high.to_numpy(); cl[pos] = M.close.to_numpy()
    mk = (M.ts // F.MIN) % 15 == 0
    R = M.loc[mk, ["ts", "close", "qv", "imbd"]].reset_index(drop=True)
    gi = np.searchsorted(grid, R.ts.to_numpy())
    for w in WS:
        # bars opened in [ts+1m, ts+1m+w)
        lw = pd.Series(lo[::-1]).rolling(w, min_periods=1).min().to_numpy()[::-1]
        hw = pd.Series(hi[::-1]).rolling(w, min_periods=1).max().to_numpy()[::-1]
        j = gi + 1; okj = j < len(grid)
        a = np.full(len(R), np.nan); b = np.full(len(R), np.nan)
        a[okj] = lw[j[okj]]; b[okj] = hw[j[okj]]
        R[f"lo{w}"] = a; R[f"hi{w}"] = b
    je = gi + H // F.MIN
    ok = (je < len(grid)) & (R.ts.to_numpy() + H <= t_end)
    ex = np.full(len(R), np.nan); ex[ok] = cl[je[ok]]
    R["exit"] = ex
    R["sym"] = sym
    return R


def build_c():
    L = json.load(open(F.WK + "/usdc_listing.json"))
    outs = []
    tmp = F.WK + "/q4tmp"
    for s in sorted(L):
        os.makedirs(tmp, exist_ok=True)
        for m in MONTHS_C:
            try:
                urllib.request.urlretrieve(URL.format(s=s, m=m), f"{tmp}/{s}-{m}.zip")
            except urllib.error.HTTPError:
                pass
        if not glob.glob(tmp + "/*.zip"):
            log.info("%s no data", s); continue
        M = F.load_usdc_m1(s, tmp)
        R = moc_table(M[["ts", "close", "high", "low", "qv", "tbqv"]], s, F.ms("2026-10-01") - F.MIN)
        log.info("%s bars %d first %s mocs %d", s, len(M), pd.to_datetime(M.ts.iloc[0], unit="ms"), len(R))
        outs.append(R)
        shutil.rmtree(tmp)
    pd.concat(outs, ignore_index=True).to_parquet(F.WK + "/q4_moc_c.parquet")


def build_e():
    outs = []
    parts = []
    for p in sorted(glob.glob(RAW + "/kline1m-202[23]-*.parquet")):
        x = pd.read_parquet(p, columns=["ts", "sym", "close", "high", "low", "quote_volume", "taker_buy_quote", "active"],
                            filters=[("sym", "in", [a + "USDT" for a in E_SYMS])])
        x["sym"] = x.sym.astype(str)
        parts.append(x)
    X = pd.concat(parts, ignore_index=True).rename(columns={"quote_volume": "qv", "taker_buy_quote": "tbqv"})
    X["ts"] = X.ts.astype(np.int64)
    for s, g in X.groupby("sym"):
        g = g.drop_duplicates("ts")
        R = moc_table(g[["ts", "close", "high", "low", "qv", "tbqv"]], s, F.ms("2024-01-01") - F.MIN)
        act = g.set_index("ts").active.reindex(R.ts).fillna(False).to_numpy(bool)
        R = R[act].reset_index(drop=True)
        log.info("E %s bars %d mocs %d", s, len(g), len(R)); outs.append(R)
    pd.concat(outs, ignore_index=True).to_parquet(F.WK + "/q4_moc_e.parquet")


def legs(R):
    d = R[(R.qv >= MIN_QV)].dropna(subset=["imbd", "exit", "close"]).copy()
    d["nu"] = d.groupby("ts").sym.transform("count")
    d["rk"] = d.groupby("ts").imbd.rank(pct=True)
    d["q"] = np.clip(np.ceil(d.rk * 5.0), 1, 5).astype(int)
    has = d.groupby("ts").q.agg(lambda q: (q == 1).any() and (q == 5).any())
    d = d[d.ts.isin(has[has].index) & d.q.isin([1, 5])].copy()
    d["side"] = np.where(d.q == 1, 1, -1)   # IC am: imb_dev15 thap -> long
    n = d.groupby(["ts", "q"]).sym.transform("count")
    d["w"] = 1.0 / (48 * 2 * n)
    return d.reset_index(drop=True)


def pnl():
    days = pd.date_range("2021-01-02", "2026-09-30", freq="D")
    res, D = {}, {}
    usdc_first = {}
    allr = []
    for per, path, quote in (("E", "/q4_moc_e.parquet", "USDT"), ("C", "/q4_moc_c.parquet", "USDC")):
        R = pd.read_parquet(F.WK + path)
        if per == "C":
            usdc_first = R.groupby("sym").ts.min().to_dict()
            R = R[(R.ts >= F.ms(F.C0))]
        else:
            R = R[(R.ts >= F.ms("2022-01-01")) & (R.ts < F.ms("2024-01-01"))]
        d = legs(R)
        side = d.side.to_numpy(float)
        g = side * (d.exit.to_numpy() / d.close.to_numpy() - 1)
        fu = np.zeros(len(d))
        for s, ix in d.groupby("sym").groups.items():
            base = s[:-4]
            fts, fr = F.load_funding(base + "USDT", base + "USDC" if quote == "USDC" else None, usdc_first.get(s) if quote == "USDC" else None)
            ix = np.asarray(ix)
            fu[ix] = side[ix] * F.fund_sum(fts, fr, d.ts.to_numpy(np.int64)[ix] + F.MIN, d.ts.to_numpy(np.int64)[ix] + H + F.MIN)
        hs = d.sym.map(lambda s: F.HS.get(s.replace("USDT", "USDC"), F.HS["ALT_DEFAULT"])).to_numpy(float)
        mods = {"gross": g, "M0": g - fu, "M2": g - 2 * (F.TAKER + hs) - fu}
        for w in WS:
            fill = np.where(side > 0, d[f"lo{w}"].to_numpy() < d.close.to_numpy(), d[f"hi{w}"].to_numpy() > d.close.to_numpy())
            r = g - F.AS_BPS * 1e-4 - (F.TAKER + hs) - fu
            r = np.where(fill, r, 0.0)
            mods[f"M1_W{w}"] = r
            res.setdefault(per, {})[f"fill_W{w}"] = float(fill.mean())
        dayx = ((d.ts.to_numpy(np.int64) + H + F.MIN) // F.DAY) * F.DAY
        for k, r in mods.items():
            D.setdefault(k, []).append(pd.Series(r * d.w.to_numpy(), index=pd.to_datetime(dayx, unit="ms")))
        res[per].update({"n_legs": int(len(d)), "n_mocs": int(d.ts.nunique()), "n_univ_median": float(d.nu.median()),
                         "gross_leg_bps": float(g.mean() * 1e4), "fund_leg_bps": float(fu.mean() * 1e4), "hs_mean_bps": float(hs.mean() * 1e4)})
        log.info("Q4 %s %s", per, res[per])
    out = {}
    for k, v in D.items():
        s = pd.concat(v).groupby(level=0).sum().reindex(days, fill_value=0.0)
        s[s.index < pd.Timestamp("2022-01-01")] = np.nan  # E Q4 chi 2022-2023 (du lieu)
        out[f"Q4|{k}"] = s
        res[k] = F.split(s.dropna())
        log.info("Q4 %s E %+.2f C %+.2f", k, res[k]["E"]["sharpe"], res[k]["C"]["sharpe"])
    pd.DataFrame(out).to_parquet(F.WK + "/q4_daily.parquet")
    json.dump(res, open(F.WK + "/q4_res.json", "w"), indent=1)


if __name__ == "__main__":
    {"build_c": build_c, "build_e": build_e, "pnl": pnl}[sys.argv[1]]()
