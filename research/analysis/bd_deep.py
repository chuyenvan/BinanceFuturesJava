"""BD_DEEP - dao sau `rateDown15MAvg` (DownAvg15M): cach tinh, y nghia, va cac NUT co the chinh.

0-SIM THUAN PYTHON: KHONG chay Java, KHONG build, KHONG xgboost, KHONG cham 2026.
Nguon: market.bin (2554812 phut: ts, down, up, down15) + ticker_*.bin.gz (raw per-coin 1M) khi can.
Dung module logging, cam print().

Usage:
  python3 research/analysis/bd_deep.py dist        # phan bo + tan suat vuot nguong (toan DEV)
  python3 research/analysis/bd_deep.py sweep       # quet nguong (signal-level, tren market.bin)
  python3 research/analysis/bd_deep.py parity YYYYMMDD   # tai lap calMarketData 1 ngay vs market.bin
  python3 research/analysis/bd_deep.py defn        # quet N / cua so / dinh nghia tren mau ngay
"""
import gzip
import json
import logging
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("bd_deep")

OUT_DIR = os.path.join(HERE, "out")
os.makedirs(OUT_DIR, exist_ok=True)

MB = "/home/ubuntu/wfo_ds_x1_2021/market.bin"
TICKDIR = "/home/ubuntu/java/simulator/kaggle_data_hpo"
DAY_MS = 86400000
GMT7 = 7 * 3600 * 1000
DT = np.dtype([("ts", ">i8"), ("down", ">f4"), ("up", ">f4"), ("down15", ">f4")])

DEV_LO = int(pd.Timestamp("2021-07-01", tz="Asia/Saigon").timestamp() * 1000)
DEV_HI = int(pd.Timestamp("2025-12-31", tz="Asia/Saigon").timestamp() * 1000)

THR_BD = -0.03157      # Configs.MS_DOWN_BIG_AVG
THR_DCA = -0.03157     # Configs.MS_DOWN_BIG_AVG_DCA
N_MAIN = 100           # period truyen vao calRateChangeAvg
WIN_MAIN = 15          # Configs.NUMBER_TICKER_CAL_RATE_CHANGE


def load_market():
    with open(MB, "rb") as f:
        n = int(np.frombuffer(f.read(4), dtype=">i4")[0])
        a = np.frombuffer(f.read(n * 20), dtype=DT)
    ts = a["ts"].astype(np.int64)
    keep = (ts >= DEV_LO) & (ts < DEV_HI)
    return ts[keep], a["down"][keep].astype(np.float64), a["up"][keep].astype(np.float64), a["down15"][keep].astype(np.float64)


def pct(x, q):
    return float(np.percentile(x, q))


def episodes(mask):
    """So lan doi trang thai ON (0->1)."""
    if not mask.any():
        return 0
    return int(np.count_nonzero(mask & ~np.concatenate([[False], mask[:-1]])))


def run_dist():
    ts, down, up, d15 = load_market()
    log.info("DEV minutes = %d  (%s .. %s GMT+7)", len(ts),
             pd.to_datetime(ts[0], unit="ms", utc=True).tz_convert("Asia/Saigon"),
             pd.to_datetime(ts[-1], unit="ms", utc=True).tz_convert("Asia/Saigon"))
    res = {"n_minutes": int(len(ts))}
    for name, x in (("rateDownAvg", down), ("rateUpAvg", up), ("rateDown15MAvg", d15)):
        q = {f"p{p}": pct(x, p) for p in (1, 5, 25, 50, 75, 95, 99)}
        res[name] = dict(q, min=float(x.min()), max=float(x.max()), mean=float(x.mean()),
                         n_neg=int((x < 0).sum()))
        log.info("%-15s p1=%.5f p5=%.5f p50=%.5f p95=%.5f p99=%.5f max=%.4f", name,
                 q["p1"], q["p5"], q["p50"], q["p95"], q["p99"], x.max())

    # tan suat vuot nguong
    bd = down < THR_BD
    dca15 = d15 < THR_DCA
    dca_dn = down < THR_DCA / 3
    res["freq"] = {
        "BIG_DOWN(rateDownAvg<%.5f)" % THR_BD: dict(frac=float(bd.mean()), minutes=int(bd.sum()), episodes=episodes(bd)),
        "DCA15(rateDown15MAvg<%.5f)" % THR_DCA: dict(frac=float(dca15.mean()), minutes=int(dca15.sum()), episodes=episodes(dca15)),
        "DCA_dn(rateDownAvg<%.5f)" % (THR_DCA / 3): dict(frac=float(dca_dn.mean()), minutes=int(dca_dn.sum()), episodes=episodes(dca_dn)),
        "DCA_or": dict(frac=float((dca15 | dca_dn).mean()), minutes=int((dca15 | dca_dn).sum()), episodes=episodes(dca15 | dca_dn)),
    }
    for k, v in res["freq"].items():
        log.info("%-34s frac=%.4f%% ($%.0f/%d) minutes=%d episodes=%d", k, v["frac"] * 100, v["frac"] * 100, 100, v["minutes"], v["episodes"])

    # tuong quan
    res["corr"] = {
        "down_vs_down15": float(np.corrcoef(down, d15)[0, 1]),
        "down_vs_up": float(np.corrcoef(down, up)[0, 1]),
    }
    # dong thoi BIG_DOWN va DCA15
    res["both_on_frac"] = float((bd & dca15).mean())
    log.info("corr(down,down15)=%.4f  corr(down,up)=%.4f  both_on=%.4f%%",
             res["corr"]["down_vs_down15"], res["corr"]["down_vs_up"], res["both_on_frac"] * 100)
    json.dump(res, open(os.path.join(OUT_DIR, "bd_deep_dist.json"), "w"), indent=1)
    log.info("-> %s", os.path.join(OUT_DIR, "bd_deep_dist.json"))


def run_sweep():
    ts, down, up, d15 = load_market()
    # quet nguong cho rateDownAvg (BIG_DOWN) va rateDown15MAvg (DCA)
    grid = [-0.02, -0.025, -0.03157, -0.035, -0.04, -0.045, -0.05, -0.05514, -0.06, -0.07, -0.08, -0.10]
    res = {"grid": grid, "down": {}, "down15": {}}
    for thr in grid:
        for key, arr, dst in (("down", down, "down"), ("down15", d15, "down15")):
            m = arr < thr
            dst = res[dst]
            dst["%.5f" % thr] = dict(frac=float(m.mean()), minutes=int(m.sum()), episodes=episodes(m))
    for key in ("down", "down15"):
        log.info("== %s ==", key)
        for thr in grid:
            v = res[key]["%.5f" % thr]
            log.info("  thr=%+.5f frac=%6.3f%% minutes=%7d episodes=%5d", thr, v["frac"] * 100, v["minutes"], v["episodes"])
    json.dump(res, open(os.path.join(OUT_DIR, "bd_deep_sweep.json"), "w"), indent=1)
    log.info("-> %s", os.path.join(OUT_DIR, "bd_deep_sweep.json"))


CLOSES = "/home/ubuntu/java/fsrun/CLOSES_1H.bin"
HOUR_MS = 3600 * 1000
SEAL_2026 = int(pd.Timestamp("2026-01-01", tz="UTC").timestamp() * 1000)


def run_link():
    """Quan he BIG_DOWN/DCA voi BTC (1H) + regime MA200 - 0-sim, CHI DOC CLOSES_1H.bin."""
    DTc = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("c", ">f4")])
    a = np.fromfile(CLOSES, dtype=DTc)
    ts = a["ts"].astype(np.int64)
    sym = a["sym"].astype(np.int64)
    c = a["c"].astype(np.float64)
    m = (ts < SEAL_2026) & (sym == 1)
    bt = ts[m] + HOUR_MS
    bc = c[m]
    o = np.argsort(bt)
    bt, bc = bt[o], bc[o]
    # MA200 daily causal tren BTC 1H
    s = pd.Series(bc)
    ma = s.rolling(200, min_periods=30).mean().to_numpy()
    bull = bc > ma

    tsd, down, up, d15 = load_market()
    idx = np.searchsorted(bt, tsd, side="right") - 1
    ok = idx >= 1
    ret1h = np.where(ok, bc[np.clip(idx, 0, len(bc) - 1)] / np.where(idx >= 1, bc[np.clip(idx - 1, 0, len(bc) - 1)], np.nan) - 1, np.nan)
    fwd1h = np.where(ok & (idx + 1 < len(bc)), bc[np.clip(idx + 1, 0, len(bc) - 1)] / bc[np.clip(idx, 0, len(bc) - 1)] - 1, np.nan)
    bullm = np.where(ok, bull[np.clip(idx, 0, len(bc) - 1)], np.nan)

    bd = down < THR_BD
    dca = d15 < THR_DCA
    res = {}
    for name, mask in (("ALL", np.ones(len(tsd), bool)), ("BIG_DOWN", bd), ("DCA15", dca)):
        r = ret1h[mask]
        f = fwd1h[mask]
        r = r[~np.isnan(r)]
        f = f[~np.isnan(f)]
        bb = bullm[mask]
        bb = bb[~np.isnan(bb)]
        res[name] = dict(n=int(mask.sum()),
                         btc_ret1h_mean=round(float(r.mean()) * 100, 4),
                         btc_ret1h_p1=round(float(np.percentile(r, 1)) * 100, 4),
                         btc_fwd1h_mean=round(float(f.mean()) * 100, 4),
                         frac_bull=round(float(np.nanmean(bb)) * 100, 2))
        log.info("%-9s n=%6d  BTC ret1h mean=%+.4f%% p1=%+.4f%%  fwd1h mean=%+.4f%%  %%bullMA200=%.1f",
                 name, res[name]["n"], res[name]["btc_ret1h_mean"], res[name]["btc_ret1h_p1"],
                 res[name]["btc_fwd1h_mean"], res[name]["frac_bull"])
    json.dump(res, open(os.path.join(OUT_DIR, "bd_deep_link.json"), "w"), indent=1)
    log.info("-> %s", os.path.join(OUT_DIR, "bd_deep_link.json"))


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "dist"
    if cmd == "dist":
        run_dist()
    elif cmd == "sweep":
        run_sweep()
    elif cmd == "link":
        run_link()
    else:
        raise SystemExit("unknown cmd " + cmd)
