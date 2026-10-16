"""REX Buoc 0 (PREREG_REX_S0.md): panel ngay feature + target. Usage: rex_s0.py [met|build|all]"""
import glob
import json
import logging
import os
import sys

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

sys.path.insert(0, os.path.expanduser("~/claude_master/vz_e1_wt/research/screen"))
import sw_run as S  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("rex0")
OUT = os.path.expanduser("~/claude_master/rex")
CUT = 84_600_000  # 23:30 UTC trong ngay (ms)


def met_daily():
    rows = []
    for f in sorted(glob.glob(OUT + "/met/metrics5m-*.parquet")):
        pf = pq.ParquetFile(f)
        for i in range(pf.num_row_groups):
            t = pf.read_row_group(i, columns=["ts", "sym", "oi_value", "toptrader_ls_sum", "ls_cnt", "taker_ls_vol"]).to_pandas()
            t = t[(t.ts % 86_400_000) <= CUT]
            if t.empty:
                continue
            assert ((t.ts % 86_400_000) <= CUT).all()
            t["day"] = pd.to_datetime(t.ts // 86_400_000 * 86_400_000, unit="ms")
            t = t.sort_values(["sym", "ts"])
            g = t.groupby(["sym", "day"])
            d = g[["oi_value", "toptrader_ls_sum", "ls_cnt"]].last()
            d["tkls"] = g.taker_ls_vol.mean()
            d["met_last_ts"] = g.ts.max()
            rows.append(d.reset_index())
        log.info("met %s xong, %d khoi", os.path.basename(f), len(rows))
    M = pd.concat(rows).drop_duplicates(["sym", "day"], keep="last")
    M.to_parquet(OUT + "/met_daily.parquet")
    log.info("met_daily %d dong %d sym %s..%s", len(M), M.sym.nunique(), M.day.min(), M.day.max())


def load_k1d():
    rows = []
    for d in sorted(glob.glob(S.W + "/k1d/*")):
        s = os.path.basename(d)
        if not s.endswith("USDT") or s[:-4] in S.STABLE:
            continue
        for p in sorted(glob.glob(d + "/*.zip")):
            try:
                x = S.read_zip(p)
            except Exception:  # noqa: BLE001
                continue
            x["sym"] = s
            rows.append(x)
    D = pd.concat(rows, ignore_index=True)
    D.columns = ["ot", "open", "high", "low", "close", "vol", "ct", "qv", "n", "tbv", "tbq", "sym"]
    D["day"] = pd.to_datetime(D.ot, unit="ms").dt.floor("D")
    D = D.drop_duplicates(["sym", "day"])[["sym", "day", "open", "high", "low", "close", "qv", "tbq"]]
    F = pd.read_parquet(S.W + "/d1.parquet", columns=["sym", "day", "fund_day"])
    return D.merge(F, on=["sym", "day"], how="left")


def wide(D, col, idx):
    return D.pivot(index="day", columns="sym", values=col).reindex(idx)


def build():
    D = load_k1d()
    idx = pd.date_range(D.day.min(), D.day.max(), freq="D")
    C, H, L, Q, TB = (wide(D, c, idx) for c in ("close", "high", "low", "qv", "tbq"))
    FD = wide(D, "fund_day", idx).fillna(0.0)
    M = pd.read_parquet(OUT + "/met_daily.parquet")
    M = M[M.sym.isin(C.columns)]
    OIv, TLS, GLS, TK = (M.pivot(index="day", columns="sym", values=c).reindex(index=idx, columns=C.columns)
                         for c in ("oi_value", "toptrader_ls_sum", "ls_cnt", "tkls"))
    CF = C.ffill()
    R = np.log(C / C.shift(1))
    first = C.apply(lambda s: s.first_valid_index())
    qv30 = Q.rolling(30, min_periods=20).median()
    age = pd.DataFrame({s: (idx - first[s]).days for s in C.columns}, index=idx)
    U = (qv30 >= 20e6) & (age >= 60) & C.notna()
    btc = R["BTCUSDT"]
    f = {}
    for k in (1, 3, 7, 14, 28, 56, 90):
        f[f"mom{k}"] = C / C.shift(k) - 1
    beta = R.rolling(90, min_periods=60).cov(btc).div(btc.rolling(90, min_periods=60).var(), axis=0)
    f["rmom28"] = f["mom28"] - beta.mul(f["mom28"]["BTCUSDT"], axis=0)
    f["vol7"] = R.rolling(7, min_periods=6).std(); f["vol30"] = R.rolling(30, min_periods=25).std()
    f["atr14"] = ((H - L) / C).rolling(14, min_periods=12).mean()
    f["dvol30"] = R.where(R < 0).rolling(30, min_periods=8).std()
    f["skew30"] = R.rolling(30, min_periods=25).skew()
    f["max30"] = R.rolling(30, min_periods=25).max(); f["min30"] = R.rolling(30, min_periods=25).min()
    f["up30"] = (R > 0).astype(float).where(R.notna()).rolling(30, min_periods=25).mean()
    f["lqv30"] = np.log(qv30)
    f["vs3"] = Q.rolling(3).sum() / (Q.rolling(30, min_periods=20).mean() * 3)
    f["vs7"] = Q.rolling(7).sum() / (Q.rolling(90, min_periods=60).mean() * 7)
    f["amih30"] = (R.abs() / Q).rolling(30, min_periods=20).mean() * 1e9
    for k, mp in ((7, 6), (30, 24), (90, 72), (365, 300)):
        f[f"dhi{k}"] = C / H.rolling(k, min_periods=mp).max() - 1
    for k, mp in ((7, 6), (30, 24), (90, 72)):
        f[f"dlo{k}"] = C / L.rolling(k, min_periods=mp).min() - 1
    ma20 = C.rolling(20, min_periods=18).mean(); ma50 = C.rolling(50, min_periods=45).mean()
    f["ma20"] = C / ma20; f["ma50"] = C / ma50; f["ma2050"] = ma20 / ma50
    for k in (1, 3, 7):
        f[f"tbr{k}"] = TB.rolling(k).sum() / Q.rolling(k).sum()
    f["dtbr"] = f["tbr3"] - TB.rolling(30, min_periods=25).sum() / Q.rolling(30, min_periods=25).sum()
    f7 = FD.rolling(7).sum()
    f["f1"] = FD; f["f7"] = f7
    f["fz"] = (f7 - f7.rolling(90, min_periods=60).mean()) / f7.rolling(90, min_periods=60).std()
    f["df7"] = f7 - f7.shift(7)
    for k in (1, 3, 7):
        f[f"doi{k}"] = OIv / OIv.shift(k) - 1
    f["oiqv"] = OIv / Q.rolling(7, min_periods=6).mean()
    f["tls"] = TLS; f["dtls7"] = TLS - TLS.shift(7); f["gls"] = GLS; f["tkls"] = TK
    # boi canh (h)
    ctx = pd.DataFrame({"btc_mom7": f["mom7"]["BTCUSDT"], "btc_mom28": f["mom28"]["BTCUSDT"], "btc_vol30": f["vol30"]["BTCUSDT"],
                        "br50": (C > ma50).where(U).mean(axis=1), "disp7": f["mom7"].where(U).std(axis=1),
                        "mfund": f7.where(U).median(axis=1), "n_univ": U.sum(axis=1)})
    # target
    tg = {}
    for h in (1, 3, 7):
        y = CF.shift(-h) / C - 1
        y = y.where(U)
        tg[f"y{h}"] = y
        tg[f"yx{h}"] = y.sub(y.median(axis=1), axis=0)
        tg[f"yb{h}"] = y.sub(y["BTCUSDT"], axis=0)
        tg[f"rk{h}"] = y.rank(axis=1, pct=True)
        lo = pd.concat([L.shift(-j) for j in range(1, h + 1)]).groupby(level=0).min().reindex(idx)
        hi = pd.concat([H.shift(-j) for j in range(1, h + 1)]).groupby(level=0).max().reindex(idx)
        tg[f"mae{h}"] = lo / C - 1; tg[f"mfe{h}"] = hi / C - 1
        tg[f"ff{h}"] = (C.shift(-h).isna() & CF.shift(-h).notna()).astype(float)
    return D, C, U, f, ctx, tg, idx


FAM = {"a": ["mom1", "mom3", "mom7", "mom14", "mom28", "mom56", "mom90", "rmom28"],
       "b": ["vol7", "vol30", "atr14", "dvol30"], "c": ["skew30", "max30", "min30", "up30"],
       "d": ["lqv30", "vs3", "vs7", "amih30"],
       "e": ["dhi7", "dhi30", "dhi90", "dhi365", "dlo7", "dlo30", "dlo90", "ma20", "ma50", "ma2050"],
       "f": ["tbr1", "tbr3", "tbr7", "dtbr"], "g": ["f1", "f7", "fz", "df7", "doi1", "doi3", "doi7", "oiqv", "tls", "dtls7", "gls", "tkls"]}
LONGLB = {"mom90", "dhi90", "dhi365", "dlo90", "vs7", "fz", "rmom28"}  # lookback > 56 ngay (addendum 0)


def assemble(C, U, f, ctx, tg):
    st = U.stack(); st = st[st]
    keys = st.index
    P = pd.DataFrame(index=keys)
    for k, F in f.items():
        P[k] = F.stack(dropna=False).reindex(keys).values
        P["r_" + k] = F.where(U).rank(axis=1, pct=True).stack(dropna=False).reindex(keys).values
    for k, F in tg.items():
        P[k] = F.stack(dropna=False).reindex(keys).values
    P.index.names = ["day", "sym"]
    P = P.reset_index().merge(ctx.rename_axis("day").reset_index(), on="day", how="left")
    return P


def checks(D, P, idx):
    res = {}
    # V2 tinh lai doc lap tu du lieu tho dang dai
    rng = np.random.default_rng(1016)
    cand = P[(P.day >= "2022-02-01") & (P.day <= "2026-09-20") & P.doi1.notna()]
    smp = cand.iloc[rng.choice(len(cand), 30, replace=False)]
    Dl = D.set_index(["sym", "day"]).sort_index()
    M = pd.read_parquet(OUT + "/met_daily.parquet").set_index(["sym", "day"])
    errs = []
    for _, r in smp.iterrows():
        s, d = r.sym, r.day
        g = Dl.loc[s]
        c = g.close
        exp = {"mom7": c[d] / c[d - pd.Timedelta(days=7)] - 1,
               "tbr3": g.tbq[d - pd.Timedelta(days=2):d].sum() / g.qv[d - pd.Timedelta(days=2):d].sum(),
               "f7": g.fund_day[d - pd.Timedelta(days=6):d].fillna(0).sum(),
               "doi1": M.at[(s, d), "oi_value"] / M.at[(s, d - pd.Timedelta(days=1)), "oi_value"] - 1,
               "dhi30": c[d] / g.high[d - pd.Timedelta(days=29):d].max() - 1,
               "y3": c[d + pd.Timedelta(days=3)] / c[d] - 1 if (d + pd.Timedelta(days=3)) in c.index else np.nan}
        for k, v in exp.items():
            if not np.isnan(v):
                errs.append((k, s, str(d.date()), float(abs(r[k] - v) / max(abs(v), 1e-12))))
    mx = max(e[3] for e in errs)
    res["V2"] = {"n": len(errs), "max_rel_err": mx, "pass": mx <= 1e-9, "worst": sorted(errs, key=lambda e: -e[3])[:3]}
    # V3 do phu
    cov = {}
    ok = True
    for fam, cols in FAM.items():
        y0 = "2022-01-01" if fam == "g" else "2021-04-01"
        sub = P[P.day >= y0]
        for c in cols:
            byy = sub.groupby(sub.day.dt.year)[c].apply(lambda x: float(x.notna().mean()))
            cov[c] = {int(k): round(v, 4) for k, v in byy.items()}
            thr = 0.85 if (fam == "g" and c not in ("f1", "f7", "df7")) else 0.98
            if c not in LONGLB and byy.min() < thr:
                ok = False
    res["V3"] = {"pass": ok, "cov": cov}
    nu = P.groupby("day").size().reindex(idx[(idx >= "2021-03-01")]).fillna(0)
    ffr = float(P[["ff1", "ff3", "ff7"]].max(axis=1).mean())
    res["V4"] = {"univ_min_from_2021_03": int(nu.min()), "ff_frac": ffr, "pass": nu.min() >= 30 and ffr <= 0.01}
    big = P[P.y1.abs() > 1.0][["day", "sym", "y1"]]
    res["V5"] = {"n_abs_y1_gt_100pct": int(len(big)), "list": [(str(a.date()), b, round(c, 3)) for a, b, c in big.values[:40]]}
    return res


def main(what):
    if what in ("met", "all"):
        met_daily()
    if what in ("build", "all"):
        D, C, U, f, ctx, tg, idx = build()
        P = assemble(C, U, f, ctx, tg)
        P.to_parquet(OUT + "/panel.parquet")
        log.info("panel %d dong, %d cot, %s..%s", len(P), P.shape[1], P.day.min(), P.day.max())
        res = checks(D, P, idx)
        res["VERDICT"] = "PASS" if all(res[k]["pass"] for k in ("V2", "V3", "V4")) else "FAIL"
        json.dump(res, open(OUT + "/s0_checks.json", "w"), indent=1, default=str)
        log.info("V2 %s", {k: res["V2"][k] for k in ("n", "max_rel_err", "pass", "worst")})
        log.info("V3 pass %s | V4 %s | V5 n %d | VERDICT %s", res["V3"]["pass"], res["V4"], res["V5"]["n_abs_y1_gt_100pct"], res["VERDICT"])
        for c, v in res["V3"]["cov"].items():
            log.info("COV %-7s %s", c, v)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "all")
