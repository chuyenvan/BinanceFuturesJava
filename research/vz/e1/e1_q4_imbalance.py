"""VZ E1 - Q4: H-F imbalance at the 15' marks -> 4h/12h return (2024, <= 8 variants).

Config frozen in `configs/q4_config.json` (committed BEFORE measuring). Events: the
:00/:15/:30/:45 minute of each symbol with quote_volume >= 50 000 USDT and `active`.
`imb = 2*taker_buy_quote/quote_volume - 1`; `imb_dev15 = imb - mean(imb, 15' before)`.
Outcome: log(close(ts+h)/close(ts)) for h in {4h, 12h} (dropped when ts+h leaves 2024).
Measure: cross-sectional Spearman IC per moc + quintile (by feature) top-bottom spread,
averaged over mocs; CI = day-level block bootstrap (5 days, NREP 2000, seed 20261014).
Cost (NC 0.0007 + round-trip fee 0.000982, Q1) is a uniform shift -> reported for level
means only; IC/spread are cost-invariant by construction.

Limitation: the published H-F uses the first 10 s of trades; here the 1-minute bar is the
closest proxy in the lake -> stated, not corrected.
"""
import json
import os

import numpy as np
import pandas as pd

import e1_data
import e1_ledger
from e1_common import FEE_ROUNDTRIP, OUT, REPORT, SEED, cost_of, setup_logging, write_json
from e1_stats import day_level_boot

log = setup_logging("e1_q4_imbalance", "e1_q4_imbalance.log")
HERE = os.path.dirname(os.path.abspath(__file__))
CONFIG = os.path.join(HERE, "configs", "q4_config.json")
MONTHS = ["2024-%02d" % m for m in range(1, 13)]
MIN_QV = 50000.0
HOUR = 3600_000
COLS = ["ts", "sym", "close", "quote_volume", "taker_buy_quote", "active"]
YEAR_END_MS = 1735689600000 - 1  # 2024-12-31T23:59:59.999Z


def _month_events(month, next_month):
    df = pd.read_parquet(e1_data.month_path(month, "kline"), columns=COLS)
    df = df.sort_values(["sym", "ts"], kind="stable").reset_index(drop=True)
    qv = df.quote_volume.replace(0, np.nan)
    df["imb"] = 2.0 * df.taker_buy_quote / qv - 1.0
    prev = df.groupby("sym", sort=False)["imb"].transform(
        lambda s: s.shift(1).rolling(15, min_periods=1).mean())
    df["imb_dev15"] = df.imb - prev

    parts = [df[["ts", "sym", "close"]]]
    if next_month is not None:
        parts.append(pd.read_parquet(e1_data.month_path(next_month, "kline"),
                                     columns=["ts", "sym", "close"]))
    allf = pd.concat(parts, ignore_index=True).sort_values(["sym", "ts"], kind="stable")
    codes, _ = pd.factorize(allf.sym, sort=False)
    ts_a = allf.ts.to_numpy(np.int64)
    cl_a = allf.close.to_numpy(np.float64)
    bounds = np.concatenate([[0], np.where(np.diff(codes) != 0)[0] + 1, [len(allf)]])
    r4 = np.full(len(allf), np.nan)
    r12 = np.full(len(allf), np.nan)
    for s in range(len(bounds) - 1):
        a, b = bounds[s], bounds[s + 1]
        if b - a < 2:
            continue
        t = ts_a[a:b]
        c = cl_a[a:b]
        t0 = np.searchsorted(t, t)  # identity positions (0..len-1)
        for h, arr in ((4, r4), (12, r12)):
            tgt = t + h * HOUR
            p = np.searchsorted(t, tgt)
            pc = np.clip(p, 0, len(t) - 1)
            ok = (p < len(t)) & (t[pc] == tgt) & (c[pc] > 0) & (tgt <= YEAR_END_MS)
            v = np.full(len(t), np.nan)
            v[ok] = np.log(c[pc][ok] / c[t0][ok])
            arr[a:b] = v
    allf["ret_4h"] = r4
    allf["ret_12h"] = r12
    df = df.merge(allf[["sym", "ts", "ret_4h", "ret_12h"]], on=["sym", "ts"], how="left")
    df["mm"] = (df.ts.to_numpy(np.int64) // 60_000) % 60
    keep = (df["active"].fillna(False).to_numpy(bool)
            & (df["quote_volume"].to_numpy(np.float64) >= MIN_QV))
    ev = df.loc[keep, ["ts", "sym", "mm", "imb", "imb_dev15", "ret_4h", "ret_12h"]].copy()
    ev["day"] = (ev.ts // 86_400_000).astype(np.int64)
    del df, allf
    return ev


def _ic_by_ts(ev, feat, ret):
    d = ev[["ts", feat, ret]].dropna()
    if d.empty:
        return np.array([]), np.array([])
    r = d.groupby("ts")[[feat, ret]].rank()
    rx = r[feat].to_numpy(np.float64)
    ry = r[ret].to_numpy(np.float64)
    d2 = pd.DataFrame({"ts": d.ts.to_numpy(np.int64), "rx": rx, "ry": ry,
                       "rx2": rx * rx, "ry2": ry * ry, "rxy": rx * ry})
    g = d2.groupby("ts", sort=True).sum()
    n = d2.groupby("ts", sort=True).size()
    num = n * g.rxy - g.rx * g.ry
    den = np.sqrt(np.maximum((n * g.rx2 - g.rx ** 2) * (n * g.ry2 - g.ry ** 2), 0.0))
    ic = (num / den).replace([np.inf, -np.inf], np.nan).dropna()
    return ic.to_numpy(np.float64), (ic.index.to_numpy(np.int64) // 86_400_000)


def _spread_by_ts(ev, feat, ret):
    d = ev[["ts", feat, ret]].dropna()
    if d.empty:
        return np.array([]), np.array([])
    d = d.assign(rk=d.groupby("ts")[feat].rank(pct=True))
    d["q"] = np.clip(np.ceil(d.rk * 5.0), 1, 5).astype(int)
    m = d.groupby(["ts", "q"], sort=True)[ret].mean().unstack()
    if 5 in m.columns and 1 in m.columns:
        sp = (m[5] - m[1]).dropna()
        return sp.to_numpy(np.float64), (sp.index.to_numpy(np.int64) // 86_400_000)
    return np.array([]), np.array([])


def _boot_series(vals, days):
    vals = np.asarray(vals, dtype=np.float64)
    days = np.asarray(days, dtype=np.int64)
    ok = np.isfinite(vals) & np.isfinite(days.astype(np.float64))
    vals, days = vals[ok], days[ok]
    if vals.size == 0:
        return {"n": 0}
    boot, _ = day_level_boot(vals, days, np.ones(vals.size, dtype=np.int64), seed=SEED)
    b = boot[1]
    return {"n": int(vals.size), "mean": float(vals.mean()), "median": float(np.median(vals)),
            "hit_rate": float((vals > 0).mean()),
            "ci95_mean": [float(b["ci95_mean"][0]), float(b["ci95_mean"][1])]}


def run():
    cfg = json.load(open(CONFIG))
    keys = ["%s_%dh_%s" % (moc, h, feat)
            for moc in cfg["moc_minutes"] for h in cfg["horizons_h"]
            for feat in ("imb", "imb_dev15")]
    acc = {k: {"ic": [], "icd": [], "sp": [], "spd": [], "n_ev": 0} for k in keys}
    for mi, month in enumerate(MONTHS):
        nxt = MONTHS[mi + 1] if mi + 1 < len(MONTHS) else None
        ev = _month_events(month, nxt)
        for moc, mms in cfg["moc_minutes"].items():
            m = ev[ev.mm == 0] if moc == "M00" else ev[ev.mm.isin(mms)]
            if m.empty:
                continue
            for feat in ("imb", "imb_dev15"):
                for h in cfg["horizons_h"]:
                    k = "%s_%dh_%s" % (moc, h, feat)
                    ret = "ret_%dh" % h
                    ic, icd = _ic_by_ts(m, feat, ret)
                    sp, spd = _spread_by_ts(m, feat, ret)
                    acc[k]["ic"].append(ic)
                    acc[k]["icd"].append(icd)
                    acc[k]["sp"].append(sp)
                    acc[k]["spd"].append(spd)
                    acc[k]["n_ev"] += int(m[ret].notna().sum())
        if mi + 1 < len(MONTHS):
            e1_data.release(month)
        log.info("Q4 month %s moc_rows=%d", month, len(ev))

    out = {}
    for k, a in acc.items():
        moc, h, feat = k.split("_")[0], int(k.split("_")[1][:-1]), k.split("_", 2)[2]
        out[k] = {"moc_set": moc, "feature": feat, "horizon_h": h, "n_events_with_ret": a["n_ev"],
                  "n_mocs": int(sum(len(x) for x in a["ic"])),
                  "ic": _boot_series(np.concatenate(a["ic"]) if a["ic"] else [],
                                     np.concatenate(a["icd"]) if a["icd"] else []),
                  "quintile_spread_gross": _boot_series(np.concatenate(a["sp"]) if a["sp"] else [],
                                                        np.concatenate(a["spd"]) if a["spd"] else []),
                  "cost_nc_roundtrip": cost_of(0)}
    res = {"task": "Q4", "family": "H-F", "config": cfg, "variants": out,
           "fee_roundtrip": FEE_ROUNDTRIP,
           "note": "10s microtrade -> 1-minute bar approximation (limitation); IC/spread cost-invariant"}
    write_json(os.path.join(REPORT, "e1_q4_imbalance.json"), res)
    rows = []
    for k, v in out.items():
        rows.append({"task": "Q4", "family": "H-F", "variant": k, "n": v["n_events_with_ret"],
                     "result": "IC=%.4f CI=%s spread=%.5f CI=%s" % (
                         v["ic"].get("mean", float("nan")), v["ic"].get("ci95_mean"),
                         v["quintile_spread_gross"].get("mean", float("nan")),
                         v["quintile_spread_gross"].get("ci95_mean")), "date": cfg["date"]})
    e1_ledger.append(rows)
    log.info("Q4 done variants=%d", len(out))
    return res


if __name__ == "__main__":
    print(json.dumps(run(), indent=1, default=str))
