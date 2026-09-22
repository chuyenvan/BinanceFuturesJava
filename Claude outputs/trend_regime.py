"""TREND_REGIME (TASK B2 Buoc 5, Buoc 1, docs/PREREG_TREND_REGIME_DIAG.md) - do detector
production TrendDetector.isBtc/EthTrendBuyProduction (SMA7/100, khung 1D+4H, OR; lay lai NGUYEN
VAN tu commit 157cf4d, da xoa o HEAD) lam regime filter thay MA200-trailing. HOAN TOAN 0-sim:
KHONG chay Java, KHONG xgboost, KHONG build, KHONG sua .java.

Nguon du lieu: CHI DOC research/analysis/trend_rank_ic.load_closes() (CLOSES_1H.bin, loc
ts<2026-01-01 = HOLDOUT rule, NGUYEN VAN khong sua) + research/analysis/bigdown_struct
.load_trades_utc/block_boot_mean/phi_for (doc printDone.csv/sim.out cua T100=X1_C3_FULL_2021,
NGUYEN VAN khong sua 2 file goc do). Dung module logging, cam print().

Chay: cd /home/ubuntu/src/BinanceFuturesJava && python3 research/analysis/trend_regime.py
Ghi: research/analysis/out/trend_regime.json
"""
import json
import logging
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import trend_rank_ic as T  # noqa: E402  (load_closes)
import bigdown_struct as B  # noqa: E402  (load_trades_utc, block_boot_mean, phi_for)

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("trend_regime")

OUT_JSON = os.path.join(HERE, "out", "trend_regime.json")
DAY_MS = 86400000
H4_MS = 4 * 3600 * 1000
SYM_BTC, SYM_ETH = 1, 2
SMA_SHORT = 7
SMA_LONG_MAIN = 100
MIN_PERIODS_FLOOR = 30  # nhu regime_build_ma200.py, cho phep SMA "chua du N" o dau lich su

TAG_T100 = "X1_C3_FULL_2021"

SIM0 = "2021-07-01"
SIM1 = "2025-12-31"

UW2022 = ("2021-11-16", "2022-07-21")   # gate-1.0/P3, TASK B2 Buoc 1 (khong tinh lai)
UW2025 = ("2025-03-04", "2025-10-16")   # gate-1.0/T100, chan doan UW-2025 (khong tinh lai)

MA200_UP_PCT_REF = {"2021": 64.7, "2022": 0.0, "2023": 80.3, "2024": 80.1, "2025": 73.4}
GATE_THRESHOLD_PCT = 60.0


def day_id(datestr):
    return int(pd.Timestamp(datestr, tz="UTC").value // 10 ** 6 // DAY_MS)


def sym_frame(df, sym):
    d = df[df["sym"] == sym].sort_values("ctime")
    return d


def to_period_series(d, period_ms):
    period = (d["ctime"].to_numpy() // period_ms).astype(np.int64)
    s = pd.Series(d["close"].to_numpy(), index=period)
    return s.groupby(level=0).last().sort_index()


def causal_sma_diff(period_close, short, long_, min_floor=MIN_PERIODS_FLOOR):
    """period_close: Series index=period-id lien tuc tang dan (co the co gap thua).
    Tra Series full_range -> (SMA_short - SMA_long) da SHIFT 1 ky (causal: gia tri tai period p
    chi dung close cua period < p). NaN neu chua du du lieu."""
    full_idx = np.arange(int(period_close.index.min()), int(period_close.index.max()) + 1)
    s = period_close.reindex(full_idx)
    mp_s = min(short, min_floor)
    mp_l = min(long_, min_floor)
    sma_s = s.rolling(short, min_periods=mp_s).mean().shift(1)
    sma_l = s.rolling(long_, min_periods=mp_l).mean().shift(1)
    return (sma_s - sma_l)


def detector_up_symbol(daily_close, h4_close, short, long_, day_range, timeframe="1D+4H-OR"):
    """day_range: array cac day_id can tra ket qua. timeframe in
    {'1D-only','4H-only','1D+4H-OR'}.

    Dung DUNG ngu nghia Java: neu 1 thanh phan thieu du lieu (chua du warmup), thanh phan do
    KHONG lam detector_up=True (giong `maDif==null` bi bo qua trong dieu kien OR cua
    TrendDetector). Tra (up: bool ndarray, n_missing_1d: int, n_missing_4h: int) de bao cao
    minh bach so ngay thieu du lieu causal (voi min_periods_floor=30, trong SIM range thuc te
    con so nay ~0 vi co >=181 ngay lich su truoc SIM0)."""
    diff_1d = diff_4h = None
    n_missing_1d = n_missing_4h = 0
    up_1d = up_4h = np.zeros(len(day_range), dtype=bool)
    if timeframe in ("1D-only", "1D+4H-OR"):
        diff_1d = causal_sma_diff(daily_close, short, long_).reindex(day_range)
        n_missing_1d = int(diff_1d.isna().sum())
        up_1d = (diff_1d.to_numpy(dtype=float) > 0)
    if timeframe in ("4H-only", "1D+4H-OR"):
        bucket0_of_day = day_range * 6
        diff_4h = causal_sma_diff(h4_close, short, long_).reindex(bucket0_of_day)
        n_missing_4h = int(diff_4h.isna().sum())
        up_4h = (diff_4h.to_numpy(dtype=float) > 0)
    if timeframe == "1D-only":
        res = up_1d
    elif timeframe == "4H-only":
        res = up_4h
    else:
        res = up_1d | up_4h
    return res, n_missing_1d, n_missing_4h


def pct_up_by_year(up_bool_arr, day_range):
    dates = pd.to_datetime(day_range.astype(np.int64) * DAY_MS, unit="ms")
    df = pd.DataFrame({"up": up_bool_arr.astype(float)}, index=dates)
    out = {}
    for y, g in df.groupby(df.index.year):
        v = g["up"]
        out[str(y)] = dict(n=int(len(v)), pct_up=float(100.0 * v.mean()) if len(v) else None)
    return out


def window_pct_notup(up_bool_arr, day_range, start, end):
    d0, d1 = day_id(start), day_id(end)
    m = (day_range >= d0) & (day_range <= d1)
    v = up_bool_arr.astype(float)[m]
    if len(v) == 0:
        return dict(n_days=0, pct_notup=None)
    return dict(n_days=int(len(v)), pct_notup=float(100.0 * (1.0 - v.mean())))


def main():
    os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
    log.info("=== TREND_REGIME: nap CLOSES_1H.bin (BTC/ETH) ===")
    df = T.load_closes()
    btc = sym_frame(df, SYM_BTC)
    eth = sym_frame(df, SYM_ETH)
    log.info("BTC n=%d ETH n=%d ctime %s -> %s", len(btc), len(eth),
              pd.Timestamp(df.ctime.min(), unit="ms"), pd.Timestamp(df.ctime.max(), unit="ms"))

    btc_daily = to_period_series(btc, DAY_MS)
    btc_4h = to_period_series(btc, H4_MS)
    eth_daily = to_period_series(eth, DAY_MS)
    eth_4h = to_period_series(eth, H4_MS)

    day0, day1 = day_id(SIM0), day_id(SIM1)
    day_range = np.arange(day0, day1 + 1)
    log.info("SIM range %s..%s = %d ngay", SIM0, SIM1, len(day_range))

    result = {"meta": {"sim0": SIM0, "sim1": SIM1, "sma_short": SMA_SHORT,
                        "sma_long_main": SMA_LONG_MAIN, "min_periods_floor": MIN_PERIODS_FLOOR,
                        "uw2022_window": list(UW2022), "uw2025_window": list(UW2025),
                        "ma200_up_pct_ref_task_b2_buoc4": MA200_UP_PCT_REF,
                        "gate_threshold_pct": GATE_THRESHOLD_PCT}}

    # ---------------------------------------------------------------- 1. detector chinh (BTC/ETH/OR)
    up_btc, miss_btc_1d, miss_btc_4h = detector_up_symbol(
        btc_daily, btc_4h, SMA_SHORT, SMA_LONG_MAIN, day_range, "1D+4H-OR")
    up_eth, miss_eth_1d, miss_eth_4h = detector_up_symbol(
        eth_daily, eth_4h, SMA_SHORT, SMA_LONG_MAIN, day_range, "1D+4H-OR")
    up_or = up_btc | up_eth
    log.info("thieu du lieu causal (min_periods_floor=%d, ky vong ~0 trong SIM range): "
              "BTC 1d=%d 4h=%d | ETH 1d=%d 4h=%d",
              MIN_PERIODS_FLOOR, miss_btc_1d, miss_btc_4h, miss_eth_1d, miss_eth_4h)

    result["pct_up_by_year"] = {
        "BTC": pct_up_by_year(up_btc, day_range),
        "ETH": pct_up_by_year(up_eth, day_range),
        "BTC_OR_ETH": pct_up_by_year(up_or, day_range),
    }
    for nm, s in (("BTC", up_btc), ("ETH", up_eth), ("BTC_OR_ETH", up_or)):
        py = result["pct_up_by_year"][nm]
        log.info("%%up/nam (%s): %s", nm,
                  {y: py[y]["pct_up"] for y in sorted(py)})

    # ---------------------------------------------------------------- 2. phu chuoi UW
    result["uw_coverage"] = {}
    for nm, s in (("BTC", up_btc), ("ETH", up_eth), ("BTC_OR_ETH", up_or)):
        result["uw_coverage"][nm] = {
            "UW2022": window_pct_notup(s, day_range, *UW2022),
            "UW2025": window_pct_notup(s, day_range, *UW2025),
        }
        log.info("phu not-up (%s): UW2022=%s UW2025=%s", nm,
                  result["uw_coverage"][nm]["UW2022"], result["uw_coverage"][nm]["UW2025"])

    # ---------------------------------------------------------------- 3a. edge doc lap: forward return BTC
    full_idx_btc = np.arange(int(btc_daily.index.min()), int(btc_daily.index.max()) + 1)
    btc_full = btc_daily.reindex(full_idx_btc)
    close_by_day = dict(zip(full_idx_btc, btc_full.to_numpy()))

    def fwd_ret(h):
        out = np.full(len(day_range), np.nan)
        for i, d in enumerate(day_range):
            c0 = close_by_day.get(d - 1)
            c1 = close_by_day.get(d - 1 + h)
            if c0 is not None and c1 is not None and np.isfinite(c0) and np.isfinite(c1) and c0 != 0:
                out[i] = c1 / c0 - 1.0
        return out

    fwd1 = fwd_ret(1)
    fwd7 = fwd_ret(7)

    def grp_stats(mask_up, arr):
        v_up = arr[mask_up & np.isfinite(arr)]
        v_dn = arr[(~mask_up) & np.isfinite(arr)]
        return dict(
            up=dict(n=int(len(v_up)), mean_pct=float(100 * v_up.mean()) if len(v_up) else None,
                     std_pct=float(100 * v_up.std()) if len(v_up) else None),
            notup=dict(n=int(len(v_dn)), mean_pct=float(100 * v_dn.mean()) if len(v_dn) else None,
                       std_pct=float(100 * v_dn.std()) if len(v_dn) else None),
        )

    result["forward_return_btc"] = {}
    for nm, s in (("BTC", up_btc), ("ETH", up_eth), ("BTC_OR_ETH", up_or)):
        result["forward_return_btc"][nm] = {
            "fwd1d": grp_stats(s, fwd1),
            "fwd7d": grp_stats(s, fwd7),
        }
    log.info("forward return BTC theo detector_up (BTC-detector, chinh): fwd1d=%s fwd7d=%s",
              result["forward_return_btc"]["BTC"]["fwd1d"], result["forward_return_btc"]["BTC"]["fwd7d"])

    # ---------------------------------------------------------------- 3b. edge doc lap: ROI so T100 theo regime
    trades = B.load_trades_utc(TAG_T100)
    entry_day = (trades["s_ms"].to_numpy() // DAY_MS).astype(np.int64)
    day_to_pos = {int(d): i for i, d in enumerate(day_range)}
    up_btc_np = up_btc.astype(float)
    up_eth_np = up_eth.astype(float)
    up_or_np = up_or.astype(float)

    def regime_of(arr_np, day_arr):
        out = np.full(len(day_arr), np.nan)
        for i, d in enumerate(day_arr):
            pos = day_to_pos.get(int(d))
            if pos is not None:
                out[i] = arr_np[pos]
        return out

    trades["loss"] = (trades["roi"] < 0).astype(int)
    result["t100_by_regime"] = {}
    for nm, arr_np in (("BTC", up_btc_np), ("ETH", up_eth_np), ("BTC_OR_ETH", up_or_np)):
        reg = regime_of(arr_np, entry_day)
        valid = np.isfinite(reg)
        sub = trades.loc[valid].copy()
        reg_v = reg[valid]
        out = {}
        for lbl, m in (("up", reg_v > 0.5), ("notup", reg_v <= 0.5)):
            s2 = sub.loc[m]
            obs, lo, hi = B.block_boot_mean(s2)
            phi = B.phi_for(s2, "loss") if len(s2) >= 4 else dict(phi=None, J=0, phat=None)
            out[lbl] = dict(n=int(len(s2)), roi_mean_pct=(obs * 100 if obs is not None else None),
                             roi_ci90_lo_pct=(lo * 100 if lo is not None else None),
                             roi_ci90_hi_pct=(hi * 100 if hi is not None else None),
                             loss_rate_pct=float(100.0 * s2["loss"].mean()) if len(s2) else None,
                             phi_loss=phi.get("phi"))
        result["t100_by_regime"][nm] = out
        log.info("T100 ROI theo regime (%s): up=%s notup=%s", nm, out["up"], out["notup"])

    # ---------------------------------------------------------------- 4. sweep MO TA (BTC), khong chon winner
    sweep_rows = []
    for long_ in (50, 100, 150, 200):
        for tf in ("1D-only", "4H-only", "1D+4H-OR"):
            s, _, _ = detector_up_symbol(btc_daily, btc_4h, SMA_SHORT, long_, day_range, tf)
            dates = pd.to_datetime(day_range.astype(np.int64) * DAY_MS, unit="ms")
            m2025 = dates.year == 2025
            v = s.astype(float)[m2025]
            pct_notup_2025 = float(100.0 * (1.0 - v.mean())) if len(v) else None
            sweep_rows.append(dict(sma_short=SMA_SHORT, sma_long=long_, timeframe=tf,
                                    pct_notup_2025=pct_notup_2025, n_days_2025=int(len(v))))
    result["sweep_pct_notup_2025"] = sweep_rows
    log.info("Sweep %%2025-notup (BTC, SMA_SHORT=7): %s", sweep_rows)

    # ---------------------------------------------------------------- 5. cong GO/NO-GO (khoa PREREG)
    cov_btc = result["uw_coverage"]["BTC"]
    p2022 = cov_btc["UW2022"]["pct_notup"]
    p2025 = cov_btc["UW2025"]["pct_notup"]
    go = bool(p2022 is not None and p2025 is not None
              and p2022 >= GATE_THRESHOLD_PCT and p2025 >= GATE_THRESHOLD_PCT)
    result["gate_verdict"] = dict(
        detector="BTC", config="SMA7/100, 1D+4H-OR",
        pct_notup_uw2022=p2022, pct_notup_uw2025=p2025,
        threshold_pct=GATE_THRESHOLD_PCT, go=go,
    )
    log.info("GATE VERDICT: %s", result["gate_verdict"])

    with open(OUT_JSON, "w") as f:
        json.dump(result, f, indent=2, default=str)
    log.info("DONE -> %s", OUT_JSON)


if __name__ == "__main__":
    main()
