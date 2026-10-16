"""SCREEN_WIDE tang 1 (PREREG_SCREEN_WIDE.md 3e701549 + addendum 1 fc9bed24). Usage: sw_run.py [load|check|run]
Chi tiet thuc thi (addendum 2, khai TRUOC khi chay run):
- Gia tai thoi diem T = close cua nen 1m co open_time = T-1 phut. ET = America/New_York (co DST). S4-S7 chi xet thu Hai-Sau, KHONG loai ngay le NYSE.
- TS: moi lenh dung toan bo von, PnL ghi vao ngay thoat; Sharpe = mean/sd PnL ngay (moi ngay lich) * sqrt(365).
- X: tuan bat dau thu Hai t, tin hieu dung du lieu toi close ngay t-1, giu tu close t-1 toi close t+6; Sharpe tuan * sqrt(52).
  Chi phi long-only = (1-overlap) * 0,10% ; L/S = tong 2 chan. Funding: long tra, short nhan.
- G: khong vao lai cung coin trong 30 ngay sau khi thoat; tin hieu tai close ngay t vao lenh tai close t.
"""
import glob
import io
import json
import logging
import os
import sys
import zipfile

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("sw")
W = os.path.expanduser("~/claude_master/1016/screen")
CARRY = os.path.expanduser("~/claude_master/1016/carry")
STABLE = ("USDC", "FDUSD", "TUSD", "BUSD", "DAI", "EUR", "PAXG", "WBTC", "USDP", "UST", "AEUR", "XUSD", "USD1", "BFUSD")
E0, E1, C0, C1 = "2021-01-01", "2023-12-31", "2024-01-01", "2026-09-30"
FEE = 0.0005  # moi chieu taker


def read_zip(p):
    with zipfile.ZipFile(p) as z:
        b = z.read(z.namelist()[0])
    x = pd.read_csv(io.BytesIO(b), header=None)
    if not str(x.iloc[0, 0]).strip().isdigit():
        x = x.iloc[1:]
    return x.iloc[:, :11].astype(float)


def load():
    rows = []
    for d in sorted(glob.glob(W + "/k1d/*")):
        s = os.path.basename(d)
        if not s.endswith("USDT") or s[:-4] in STABLE:
            continue
        for p in sorted(glob.glob(d + "/*.zip")):
            try:
                x = read_zip(p)
            except Exception:  # noqa: BLE001
                continue
            x["sym"] = s
            rows.append(x)
    D = pd.concat(rows, ignore_index=True)
    D.columns = ["ot", "open", "high", "low", "close", "vol", "ct", "qv", "n", "tbv", "tbqv", "sym"]
    D["day"] = pd.to_datetime(D.ot, unit="ms").dt.floor("D")
    D = D.drop_duplicates(["sym", "day"])[["sym", "day", "open", "high", "low", "close", "qv"]]
    S = pd.read_parquet(CARRY + "/signal.parquet")[["sym", "day", "fund_day"]]
    D = D.merge(S, on=["sym", "day"], how="left")
    D.to_parquet(W + "/d1.parquet")
    for s in ("BTCUSDT", "ETHUSDT"):
        parts = [read_zip(p) for p in sorted(glob.glob(f"{W}/k1m/{s}/*.zip"))]
        M = pd.concat(parts, ignore_index=True)
        M.columns = ["ot", "open", "high", "low", "close", "vol", "ct", "qv", "n", "tbv", "tbqv"]
        M["t"] = pd.to_datetime(M.ot, unit="ms")
        M = M.drop_duplicates("t").set_index("t").sort_index()[["open", "high", "low", "close", "vol", "tbv"]]
        M.to_parquet(f"{W}/m1_{s}.parquet")
    log.info("load xong: d1 %d dong, %d sym", len(D), D.sym.nunique())


def check():
    D = pd.read_parquet(W + "/d1.parquet")
    M = pd.read_parquet(W + "/m1_BTCUSDT.parquet")
    full = pd.date_range(M.index.min(), M.index.max(), freq="1min")
    d1 = float(len(M) / len(full))
    last = M.close.resample("D").last()
    b = D[D.sym == "BTCUSDT"].set_index("day").close
    j = pd.concat([last.rename("m"), b.rename("d")], axis=1).dropna()
    d2 = float(((j.m / j.d - 1).abs() <= 1e-6).mean())
    res = {"D1_minute_coverage": d1, "D2_daily_eq_last_minute": d2, "n_sym": int(D.sym.nunique()), "days": [str(D.day.min()), str(D.day.max())]}
    log.info("CHECK %s", res)
    json.dump(res, open(W + "/check.json", "w"), indent=1)


# ---------------- thuoc do ----------------
def stats(r, ann):
    r = r.dropna()
    if len(r) < 10 or r.std() == 0:
        return {"sharpe": 0.0, "ann": 0.0, "maxdd": 0.0, "n": int(len(r))}
    eq = (1 + r).cumprod()
    return {"sharpe": float(r.mean() / r.std() * np.sqrt(ann)), "ann": float(r.mean() * ann),
            "maxdd": float((eq / eq.cummax() - 1).min()), "n": int(len(r))}


def split(r, ann):
    return {"E": stats(r[(r.index >= E0) & (r.index <= E1)], ann), "C": stats(r[(r.index >= C0) & (r.index <= C1)], ann)}


# ---------------- TS tren BTC/ETH ----------------
def ts_family(sym):
    M = pd.read_parquet(f"{W}/m1_{sym}.parquet")
    px = M.close.copy(); px.index = px.index + pd.Timedelta(minutes=1)  # gia tai T
    px = px[~px.index.duplicated()]
    fund = pd.concat([pd.read_parquet(p) for p in sorted(glob.glob(CARRY + "/fund/funding-*.parquet"))])
    fund = fund[fund.sym == sym].copy(); fund["t"] = pd.to_datetime(fund.ts, unit="ms"); fund = fund.set_index("t").rate.sort_index()
    days = pd.date_range("2021-01-02", "2026-09-30", freq="D")
    p00 = px.reindex(days).ffill()
    dret = p00.pct_change()
    vol30 = dret.rolling(30).std(); volmed = vol30.rolling(365, min_periods=180).median()
    ma20 = p00.rolling(20).mean()

    def P(t):
        return px.get(t, np.nan)

    def trade(t0, t1, side=1, with_fund=False):
        a, b = P(t0), P(t1)
        if not (np.isfinite(a) and np.isfinite(b)):
            return np.nan
        r = side * (b / a - 1) - 2 * FEE
        if with_fund:
            r -= side * fund[(fund.index > t0) & (fund.index <= t1)].sum()
        return r

    out = {}
    recs = {k: [] for k in ["S1", "S2", "S3", "S4", "S5", "S6", "S7"]}
    for d in days:
        t21, t23 = d + pd.Timedelta(hours=21), d + pd.Timedelta(hours=23)
        r1 = trade(t21, t23)
        recs["S1"].append((t23.floor("D"), r1))
        if np.isfinite(vol30.get(d, np.nan)) and np.isfinite(volmed.get(d, np.nan)) and vol30[d] > volmed[d]:
            recs["S2"].append((t23.floor("D"), r1))
        if np.isfinite(ma20.get(d, np.nan)) and p00[d] > ma20[d]:
            recs["S3"].append((t23.floor("D"), r1))
        et = pd.Timestamp(d.date()).tz_localize("America/New_York")
        wd = et.weekday()
        if wd <= 4:
            def u(h, m=0, base=et):
                return (base + pd.Timedelta(hours=h, minutes=m)).tz_convert("UTC").tz_localize(None)
            prev = et - pd.Timedelta(days=1)
            onfh = P(u(10)) / P(u(16, 0, prev)) - 1
            if np.isfinite(onfh) and onfh > 0:
                recs["S4"].append((u(17).floor("D"), trade(u(16, 30), u(17))))
            slh = P(u(16, 30)) / P(u(16)) - 1
            if np.isfinite(slh) and slh < 0:
                recs["S5"].append((u(17).floor("D"), trade(u(16, 30), u(17))))
            if wd in (4, 0, 1):
                nxt = et + pd.Timedelta(days=3 if wd == 4 else 1)
                t_in, t_out = u(16), u(10, 0, nxt)
                hist = [P(u(16, 0, et - pd.Timedelta(days=k))) for k in range(1, 11)]
                if np.isfinite(P(t_in)) and np.nanmax(hist) <= P(t_in):
                    recs["S6"].append((t_out.floor("D"), trade(t_in, t_out, with_fund=True)))
            if wd == 4:
                t_in, t_out = u(16), u(10, 0, et + pd.Timedelta(days=3))
                recs["S7"].append((t_out.floor("D"), trade(t_in, t_out, with_fund=True)))
    for k, v in recs.items():
        r = pd.DataFrame(v, columns=["day", "r"]).dropna().groupby("day").r.sum().reindex(days, fill_value=0.0)
        out[k] = split(r, 365); out[k]["n_trades"] = len(v)
    # S8 quarter-hour imbalance, luoi 4h
    bars = M[(M.index.minute == 0) & (M.index.hour % 4 == 0)]
    imb = (2 * bars.tbv - bars.vol) / bars.vol
    rows = []
    for t, v in imb.items():
        if not np.isfinite(v) or v == 0:
            continue
        a, b = P(t + pd.Timedelta(minutes=1)), P(t + pd.Timedelta(hours=4))
        if np.isfinite(a) and np.isfinite(b):
            rows.append((t.floor("D"), np.sign(v) * (b / a - 1) - 2 * FEE))
    r8 = pd.DataFrame(rows, columns=["day", "r"]).groupby("day").r.sum().reindex(days, fill_value=0.0)
    sE = split(r8, 365)["E"]["sharpe"]
    sign = 1 if sE >= 0 else -1
    # dau theo E: neu am, dao dau (chi phi van tru 2 chieu)
    if sign < 0:
        rows2 = [(d0, -(x + 2 * FEE) - 2 * FEE) for d0, x in rows]
        r8 = pd.DataFrame(rows2, columns=["day", "r"]).groupby("day").r.sum().reindex(days, fill_value=0.0)
    out["S8"] = split(r8, 365); out["S8"]["sign_from_E"] = sign; out["S8"]["n_trades"] = len(rows)
    return out


# ---------------- X cat ngang ----------------
def x_family():
    D = pd.read_parquet(W + "/d1.parquet")
    C = D.pivot(index="day", columns="sym", values="close").sort_index()
    Q = D.pivot(index="day", columns="sym", values="qv").reindex(C.index)
    FD = D.pivot(index="day", columns="sym", values="fund_day").reindex(C.index).fillna(0.0)
    R = C.pct_change()
    first = C.apply(lambda s: s.first_valid_index())
    qv30 = Q.rolling(30, min_periods=20).median()
    feats = {
        "X1": C / C.shift(21) - 1, "X2": C / C.shift(7) - 1, "X3": -(C / C.shift(7) - 1), "X4": -qv30,
        "X5": -FD.rolling(7).sum(), "X6": -R.rolling(30, min_periods=25).std(), "X7": -R.rolling(30, min_periods=25).max(),
        "X8": Q.rolling(7).sum() / (Q.rolling(90, min_periods=60).sum() / 90 * 7), "X9": C / C.rolling(365, min_periods=365).max(),
    }
    btc = R["BTCUSDT"]
    cov = R.rolling(90, min_periods=60).cov(btc); var = btc.rolling(90, min_periods=60).var()
    feats["X10"] = -(cov.div(var, axis=0))
    mondays = [d for d in C.index if d.weekday() == 0 and pd.Timestamp("2021-03-01") <= d <= pd.Timestamp("2026-09-21")]
    out, nuniv = {}, []
    prev_top = {k: set() for k in feats}; prev_bot = {k: set() for k in feats}
    recs = {k: [] for k in feats}
    for t in mondays:
        tm1 = t - pd.Timedelta(days=1); t6 = t + pd.Timedelta(days=6)
        if tm1 not in C.index or t6 not in C.index:
            continue
        age_ok = first[first <= t - pd.Timedelta(days=60)].index
        u = qv30.loc[tm1]; u = u[(u >= 20e6)].index.intersection(age_ok)
        hold = (C.loc[t6] / C.loc[tm1] - 1)[u].dropna()
        fsum = FD.loc[t:t6, hold.index].sum()
        nuniv.append(len(hold))
        if len(hold) < 30:
            continue
        bench = hold.mean()
        for k, F in feats.items():
            f = F.loc[tm1, hold.index].dropna()
            if len(f) < 30:
                continue
            n = max(3, len(f) // 10)
            top = set(f.nlargest(n).index); bot = set(f.nsmallest(n).index)
            to_t = 1 - len(top & prev_top[k]) / n; to_b = 1 - len(bot & prev_bot[k]) / n
            rt = (hold[list(top)] - fsum[list(top)]).mean(); rb = (hold[list(bot)] - fsum[list(bot)]).mean()
            lo = rt - bench - to_t * 2 * FEE
            ls = (hold[list(top)] - fsum[list(top)]).mean() - (hold[list(bot)] - fsum[list(bot)]).mean() - (to_t + to_b) * 2 * FEE
            recs[k].append((t, lo, ls))
            prev_top[k], prev_bot[k] = top, bot
    for k, v in recs.items():
        df = pd.DataFrame(v, columns=["t", "lo", "ls"]).set_index("t")
        out[k + "_LO"] = split(df.lo, 52); out[k + "_LS"] = split(df.ls, 52)
    out["_univ_min"] = int(np.min(nuniv)) if nuniv else 0
    return out


# ---------------- G grid ----------------
def g_family(variant):
    D = pd.read_parquet(W + "/d1.parquet")
    C = D.pivot(index="day", columns="sym", values="close").sort_index()
    H = D.pivot(index="day", columns="sym", values="high").reindex(C.index)
    L = D.pivot(index="day", columns="sym", values="low").reindex(C.index)
    Q = D.pivot(index="day", columns="sym", values="qv").reindex(C.index)
    FD = D.pivot(index="day", columns="sym", values="fund_day").reindex(C.index).fillna(0.0)
    first = C.apply(lambda s: s.first_valid_index())
    mx365 = C.rolling(365, min_periods=365).max()
    mx120 = C.rolling(120, min_periods=120).max()
    hi30 = C.shift(1).rolling(30).max(); ma50 = C.rolling(50).mean()
    qv30 = Q.rolling(30, min_periods=20).median()
    # dinh 365 ngay nam cach >= 120 ngay  <=>  max 120 ngay gan nhat < max 365 ngay
    setup = (C <= 0.35 * mx365) & (mx120 < mx365) & (qv30 >= 10e6)
    rev = (C > hi30) & (C > ma50)
    sig = setup if variant == "G1b" else (setup & rev)
    use_stop = variant != "G1c"
    cash, pos, last_exit, curve, ntr, nstop = 1.0, {}, {}, [], 0, 0
    for d in C.index:
        if d < pd.Timestamp("2021-01-01"):
            continue
        for s in list(pos):
            p = pos[s]
            h, l, c = H.at[d, s], L.at[d, s], C.at[d, s]
            if not np.isfinite(c):
                continue
            qty = sum(lv["q"] for lv in p["lv"] if lv["held"])
            p["pc"] -= qty * c * FD.at[d, s]
            for lv in p["lv"]:
                lv["new"] = False
                if not lv["held"] and l <= lv["px"]:
                    lv.update(held=True, q=lv["N"] / lv["px"], fill=lv["px"], new=True)
                    p["pc"] -= lv["N"] * (1 + FEE)
            for lv in p["lv"]:
                if lv["held"] and not lv["new"] and h >= lv["fill"] * 1.10:
                    p["pc"] += lv["q"] * lv["fill"] * 1.10 * (1 - FEE)
                    lv.update(held=False, q=0.0)
            p["age"] += 1
            reason = None
            if use_stop and c < p["entry"] * 0.70:
                reason = "stop"
            elif c > p["entry"] * 1.50:
                reason = "tp"
            elif p["age"] >= 90:
                reason = "time"
            if reason:
                qty = sum(lv["q"] for lv in p["lv"] if lv["held"])
                cash += p["pc"] + qty * c * (1 - FEE)
                ntr += 1; nstop += reason == "stop"; last_exit[s] = d; del pos[s]

        def equity():
            v = cash
            for s2, p2 in pos.items():
                c2 = C.at[d, s2]
                q2 = sum(lv["q"] for lv in p2["lv"] if lv["held"])
                v += p2["pc"] + (q2 * c2 if np.isfinite(c2) else q2 * p2["lastc"])
                if np.isfinite(c2):
                    p2["lastc"] = c2
            return v
        if len(pos) < 10:
            row = sig.loc[d]
            cands = [s for s in row[row].index if s not in pos and pd.notna(first[s]) and first[s] <= d - pd.Timedelta(days=365)
                     and (s not in last_exit or (d - last_exit[s]).days >= 30)]
            eq_now = equity()
            for s in cands[: 10 - len(pos)]:
                slot = eq_now / 10; c = C.at[d, s]
                lv = [{"px": c * (1 - 0.06 * k), "N": slot / 5, "held": False, "q": 0.0, "new": False} for k in range(5)]
                lv[0].update(held=True, q=lv[0]["N"] / c, fill=c, new=True)
                cash -= slot
                pos[s] = {"entry": c, "lv": lv, "age": 0, "pc": slot - lv[0]["N"] * (1 + FEE), "lastc": c}
        curve.append((d, equity(), len(pos)))
    E = pd.DataFrame(curve, columns=["day", "equity", "n"]).set_index("day")
    r = E.equity.pct_change().fillna(0.0)
    o = split(r, 365); o["n_exits"] = ntr; o["n_stop"] = nstop; o["pct_days_in"] = float((E.n > 0).mean())
    o["final_equity"] = float(E.equity.iloc[-1])
    return o


def run():
    chk = json.load(open(W + "/check.json"))
    res = {"check": chk}
    for s in ("BTCUSDT", "ETHUSDT"):
        res["TS_" + s] = ts_family(s)
        for k, v in res["TS_" + s].items():
            log.info("%s %-3s E Sh %+.2f ann %+.1f%% | C Sh %+.2f ann %+.1f%% | n %s", s[:3], k, v["E"]["sharpe"], 100 * v["E"]["ann"], v["C"]["sharpe"], 100 * v["C"]["ann"], v.get("n_trades"))
    res["X"] = x_family()
    for k, v in res["X"].items():
        if k.startswith("_"):
            continue
        log.info("%-7s E Sh %+.2f ann %+.1f%% | C Sh %+.2f ann %+.1f%%", k, v["E"]["sharpe"], 100 * v["E"]["ann"], v["C"]["sharpe"], 100 * v["C"]["ann"])
    for g in ("G1", "G1b", "G1c"):
        v = g_family(g); res[g] = v
        log.info("%-4s E Sh %+.2f ann %+.1f%% dd %.1f%% | C Sh %+.2f ann %+.1f%% dd %.1f%% | exits %d stop %d in %.0f%%", g, v["E"]["sharpe"], 100 * v["E"]["ann"], 100 * v["E"]["maxdd"],
                 v["C"]["sharpe"], 100 * v["C"]["ann"], 100 * v["C"]["maxdd"], v["n_exits"], v["n_stop"], 100 * v["pct_days_in"])
    surv = []
    def ok(v):
        e, c = v["E"], v["C"]
        return e["sharpe"] > 0.5 and c["sharpe"] > 0.5 and c["ann"] > 0
    for k, v in res["TS_BTCUSDT"].items():
        if ok(v): surv.append("BTC_" + k)
    for k, v in res["X"].items():
        if not k.startswith("_") and ok(v): surv.append(k)
    for g in ("G1", "G1b", "G1c"):
        if ok(res[g]): surv.append(g)
    res["survivors"] = surv
    log.info("SONG SOT: %s", surv)
    json.dump(res, open(W + "/screen_result.json", "w"), indent=1, default=float)


if __name__ == "__main__":
    {"load": load, "check": check, "run": run}[sys.argv[1]]()
