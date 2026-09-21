"""BREADTH_REGIME (TASK B2 Buoc 5.2, de xuat Uni, docs/PREREG_BREADTH_REGIME_DIAG.md) - do
market-breadth (% coin top-50 tren MA200 cua CHINH no) lam regime filter thay MA200-BTC/
SMA-crossover. HOAN TOAN 0-sim: KHONG chay Java, KHONG xgboost, KHONG build, KHONG sua .java.

Nguon du lieu: CHI DOC research/analysis/trend_rank_ic.load_closes() (CLOSES_1H.bin, loc
ts<2026-01-01 = HOLDOUT rule, NGUYEN VAN khong sua) + research/analysis/bigdown_struct
.load_trades_utc/block_boot_mean/phi_for (doc printDone.csv/sim.out cua T100=X1_C3_FULL_2021,
NGUYEN VAN khong sua 2 file goc do). Universe = symId 1..N theo map_kaggle.csv (PROXY top-N khi
khong co volume trong CLOSES_1H.bin - xem docs/PREREG_BREADTH_REGIME_DIAG.md SS1). Dung module
logging, cam print().

Chay: cd /home/ubuntu/src/BinanceFuturesJava && python3 research/analysis/breadth_regime.py
Ghi: research/analysis/out/breadth_regime.json
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
log = logging.getLogger("breadth_regime")

OUT_JSON = os.path.join(HERE, "out", "breadth_regime.json")
DAY_MS = 86400000
SYM_BTC = 1

MA_MAIN = 200
MIN_PERIODS_FLOOR = 30  # nhu regime_build_ma200.py / trend_regime.py
TOPN_MAIN = 50
THRESHOLD_MAIN = 50.0  # % - nguong CHINH khoa PREREG

TAG_T100 = "X1_C3_FULL_2021"

SIM0 = "2021-07-01"
SIM1 = "2025-12-31"

UW2022 = ("2021-11-16", "2022-07-21")   # gate-1.0/P3, TASK B2 Buoc 1 (khong tinh lai)
UW2025 = ("2025-03-04", "2025-10-16")   # gate-1.0/T100, chan doan UW-2025 (khong tinh lai)

MA200_BTC_NOTUP_PCT_REF = {"2021": 35.3, "2022": 100.0, "2023": 19.7, "2024": 19.9, "2025": 26.6}
TRENDDET_BTC_NOTUP_PCT_REF = {"2021": 20.7, "2022": 60.8, "2023": 13.2, "2024": 15.3, "2025": 32.6}

GATE_THRESHOLD_PCT = 60.0

SWEEP_TOPN = (30, 50, 100)
SWEEP_MA = (100, 200)
SWEEP_THR = (40.0, 50.0, 60.0)


def day_id(datestr):
    return int(pd.Timestamp(datestr, tz="UTC").value // 10 ** 6 // DAY_MS)


def to_period_series(d, period_ms):
    period = (d["ctime"].to_numpy() // period_ms).astype(np.int64)
    s = pd.Series(d["close"].to_numpy(), index=period)
    return s.groupby(level=0).last().sort_index()


def build_daily_close_by_sym(df, symids):
    """Tra dict symId -> Series(index=day_id, value=close cuoi ngay UTC). Bo qua symId khong co
    du lieu trong CLOSES_1H.bin (khong xay ra voi 1..100, chi de an toan)."""
    out = {}
    sub = df[df["sym"].isin(symids)]
    for sid, d in sub.groupby("sym"):
        out[int(sid)] = to_period_series(d, DAY_MS)
    return out


def up_matrix(daily_by_sym, symids, day_range, ma_window, min_floor=MIN_PERIODS_FLOOR):
    """Tra (up_mat, alive_mat): mang float [n_days x n_coins], NaN o cho khong "song"/chua du
    MA. up_mat=1.0/0.0 khi hop le. alive_mat=1.0/0.0 (song hay khong, bat ke MA)."""
    n_days = len(day_range)
    n_coins = len(symids)
    up_mat = np.full((n_days, n_coins), np.nan)
    alive_mat = np.zeros((n_days, n_coins), dtype=bool)
    mp = min(ma_window, min_floor)
    for j, sid in enumerate(symids):
        s = daily_by_sym.get(sid)
        if s is None or len(s) == 0:
            continue
        full_idx = np.arange(int(s.index.min()), int(s.index.max()) + 1)
        sf = s.reindex(full_idx)
        ma = sf.rolling(ma_window, min_periods=mp).mean().shift(1)
        prev = sf.shift(1)
        ma_r = ma.reindex(day_range)
        prev_r = prev.reindex(day_range)
        alive = prev_r.notna().to_numpy()
        valid = alive & ma_r.notna().to_numpy()
        up = np.where(valid, (prev_r.to_numpy(dtype=float) >= ma_r.to_numpy(dtype=float)), np.nan)
        up_mat[:, j] = up
        alive_mat[:, j] = alive
    return up_mat, alive_mat


def breadth_from_up_matrix(up_mat):
    """breadth(D) = 100 * mean(up=1 | hop le) tren cac coin hop le ngay D. NaN neu khong coin nao
    hop le (khong xay ra trong SIM range voi cau hinh chinh)."""
    with np.errstate(invalid="ignore"):
        n_valid = np.sum(~np.isnan(up_mat), axis=1)
        n_up = np.nansum(up_mat, axis=1)
    breadth = np.where(n_valid > 0, 100.0 * n_up / np.maximum(n_valid, 1), np.nan)
    return breadth, n_valid


def pct_notup_by_year(not_up_bool_arr, day_range):
    dates = pd.to_datetime(day_range.astype(np.int64) * DAY_MS, unit="ms")
    df = pd.DataFrame({"notup": not_up_bool_arr.astype(float)}, index=dates)
    out = {}
    for y, g in df.groupby(df.index.year):
        v = g["notup"]
        out[str(y)] = dict(n=int(len(v)), pct_notup=float(100.0 * v.mean()) if len(v) else None)
    return out


def window_pct_notup(not_up_bool_arr, day_range, start, end):
    d0, d1 = day_id(start), day_id(end)
    m = (day_range >= d0) & (day_range <= d1)
    v = not_up_bool_arr.astype(float)[m]
    if len(v) == 0:
        return dict(n_days=0, pct_notup=None)
    return dict(n_days=int(len(v)), pct_notup=float(100.0 * v.mean()))


def main():
    os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
    log.info("=== BREADTH_REGIME: nap CLOSES_1H.bin (top-100 symId de du cho sweep) ===")
    df = T.load_closes()
    max_symid_needed = max(SWEEP_TOPN)
    symids_all = list(range(1, max_symid_needed + 1))
    daily_by_sym = build_daily_close_by_sym(df, symids_all)
    log.info("symId 1..%d: %d co du lieu trong CLOSES_1H.bin (ky vong <= %d)",
              max_symid_needed, len(daily_by_sym), max_symid_needed)

    day0, day1 = day_id(SIM0), day_id(SIM1)
    day_range = np.arange(day0, day1 + 1)
    log.info("SIM range %s..%s = %d ngay", SIM0, SIM1, len(day_range))

    # BTC daily close cho forward-return (symId 1)
    btc_daily = daily_by_sym.get(SYM_BTC)
    full_idx_btc = np.arange(int(btc_daily.index.min()), int(btc_daily.index.max()) + 1)
    btc_full = btc_daily.reindex(full_idx_btc)
    close_by_day = dict(zip(full_idx_btc, btc_full.to_numpy()))

    result = {"meta": {"sim0": SIM0, "sim1": SIM1, "topn_main": TOPN_MAIN, "ma_main": MA_MAIN,
                        "threshold_main_pct": THRESHOLD_MAIN, "min_periods_floor": MIN_PERIODS_FLOOR,
                        "uw2022_window": list(UW2022), "uw2025_window": list(UW2025),
                        "ma200_btc_notup_pct_ref": MA200_BTC_NOTUP_PCT_REF,
                        "trenddet_btc_notup_pct_ref": TRENDDET_BTC_NOTUP_PCT_REF,
                        "gate_threshold_pct": GATE_THRESHOLD_PCT,
                        "universe_proxy": "symId 1..N theo map_kaggle.csv (thu tu niem yet "
                                          "Binance Futures, KHONG phai xep hang volume rolling "
                                          "thuc - xem PREREG SS1)"}}

    # ---------------------------------------------------------------- 1. cau hinh CHINH (top50/MA200/50%)
    symids_main = list(range(1, TOPN_MAIN + 1))
    up_mat_main, alive_mat_main = up_matrix(daily_by_sym, symids_main, day_range, MA_MAIN)
    breadth_main, n_alive_main = breadth_from_up_matrix(up_mat_main)
    not_up_main = breadth_main < THRESHOLD_MAIN

    result["breadth_by_year"] = pct_notup_by_year(not_up_main, day_range)
    log.info("%%not-up/nam (breadth top50/MA200/50%%): %s",
              {y: result["breadth_by_year"][y]["pct_notup"] for y in sorted(result["breadth_by_year"])})
    result["n_alive_coins_stats"] = dict(
        min=int(np.min(n_alive_main)), median=float(np.median(n_alive_main)),
        max=int(np.max(n_alive_main)))
    log.info("so coin 'song' (top50) trong SIM range: min=%d median=%.1f max=%d",
              result["n_alive_coins_stats"]["min"], result["n_alive_coins_stats"]["median"],
              result["n_alive_coins_stats"]["max"])

    # ---------------------------------------------------------------- 2. CONG: %phu UW cua cau hinh CHINH
    cov_uw2022 = window_pct_notup(not_up_main, day_range, *UW2022)
    cov_uw2025 = window_pct_notup(not_up_main, day_range, *UW2025)
    result["uw_coverage_main"] = {"UW2022": cov_uw2022, "UW2025": cov_uw2025}
    log.info("phu not-up (breadth top50/MA200/50%%): UW2022=%s UW2025=%s", cov_uw2022, cov_uw2025)

    go = bool(cov_uw2022["pct_notup"] is not None and cov_uw2025["pct_notup"] is not None
              and cov_uw2022["pct_notup"] >= GATE_THRESHOLD_PCT
              and cov_uw2025["pct_notup"] >= GATE_THRESHOLD_PCT)
    result["gate_verdict"] = dict(
        config="top50/MA200/threshold50%%",
        pct_notup_uw2022=cov_uw2022["pct_notup"], pct_notup_uw2025=cov_uw2025["pct_notup"],
        threshold_pct=GATE_THRESHOLD_PCT, go=go,
    )
    log.info("GATE VERDICT: %s", result["gate_verdict"])

    # ---------------------------------------------------------------- 3a. edge doc lap: forward return BTC
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

    def grp_stats(mask_notup, arr):
        v_up = arr[(~mask_notup) & np.isfinite(arr)]
        v_dn = arr[mask_notup & np.isfinite(arr)]
        return dict(
            up=dict(n=int(len(v_up)), mean_pct=float(100 * v_up.mean()) if len(v_up) else None,
                     std_pct=float(100 * v_up.std()) if len(v_up) else None),
            notup=dict(n=int(len(v_dn)), mean_pct=float(100 * v_dn.mean()) if len(v_dn) else None,
                       std_pct=float(100 * v_dn.std()) if len(v_dn) else None),
        )

    result["forward_return_btc"] = {"fwd1d": grp_stats(not_up_main, fwd1),
                                     "fwd7d": grp_stats(not_up_main, fwd7)}
    log.info("forward return BTC theo breadth-regime (top50/MA200/50%%): fwd1d=%s fwd7d=%s",
              result["forward_return_btc"]["fwd1d"], result["forward_return_btc"]["fwd7d"])

    # ---------------------------------------------------------------- 3b. edge doc lap: ROI so T100 theo regime
    trades = B.load_trades_utc(TAG_T100)
    entry_day = (trades["s_ms"].to_numpy() // DAY_MS).astype(np.int64)
    day_to_pos = {int(d): i for i, d in enumerate(day_range)}

    def regime_of(day_arr):
        out = np.full(len(day_arr), np.nan)
        for i, d in enumerate(day_arr):
            pos = day_to_pos.get(int(d))
            if pos is not None and np.isfinite(breadth_main[pos]):
                out[i] = 0.0 if not_up_main[pos] else 1.0
        return out

    reg = regime_of(entry_day)
    valid = np.isfinite(reg)
    sub = trades.loc[valid].copy()
    reg_v = reg[valid]
    trades["loss"] = (trades["roi"] < 0).astype(int)
    sub["loss"] = (sub["roi"] < 0).astype(int)
    out_t100 = {}
    for lbl, m in (("up", reg_v > 0.5), ("notup", reg_v <= 0.5)):
        s2 = sub.loc[m]
        obs, lo, hi = B.block_boot_mean(s2)
        phi = B.phi_for(s2, "loss") if len(s2) >= 4 else dict(phi=None, J=0, phat=None)
        out_t100[lbl] = dict(n=int(len(s2)), roi_mean_pct=(obs * 100 if obs is not None else None),
                              roi_ci90_lo_pct=(lo * 100 if lo is not None else None),
                              roi_ci90_hi_pct=(hi * 100 if hi is not None else None),
                              loss_rate_pct=float(100.0 * s2["loss"].mean()) if len(s2) else None,
                              phi_loss=phi.get("phi"))
    result["t100_by_regime"] = out_t100
    log.info("T100 ROI theo breadth-regime (top50/MA200/50%%): up=%s notup=%s",
              out_t100["up"], out_t100["notup"])

    # ---------------------------------------------------------------- 4. sweep MO TA, khong chon winner
    sweep_rows = []
    for topn in SWEEP_TOPN:
        symids = list(range(1, topn + 1))
        for ma_w in SWEEP_MA:
            up_mat, _ = up_matrix(daily_by_sym, symids, day_range, ma_w)
            breadth, _ = breadth_from_up_matrix(up_mat)
            for thr in SWEEP_THR:
                notup = breadth < thr
                c22 = window_pct_notup(notup, day_range, *UW2022)
                c25 = window_pct_notup(notup, day_range, *UW2025)
                sweep_rows.append(dict(topn=topn, ma_window=ma_w, threshold_pct=thr,
                                        pct_notup_uw2022=c22["pct_notup"],
                                        pct_notup_uw2025=c25["pct_notup"]))
    result["sweep_uw_coverage"] = sweep_rows
    log.info("Sweep top-N x MA x nguong (%d to hop), cau hinh chinh (50/200/50%%) la o DUY NHAT "
              "dung cho cong GO/NO-GO:", len(sweep_rows))
    for r in sweep_rows:
        log.info("  topN=%3d MA=%3d thr=%4.0f%%  UW2022=%s  UW2025=%s",
                  r["topn"], r["ma_window"], r["threshold_pct"],
                  r["pct_notup_uw2022"], r["pct_notup_uw2025"])

    with open(OUT_JSON, "w") as f:
        json.dump(result, f, indent=2, default=str)
    log.info("DONE -> %s", OUT_JSON)


if __name__ == "__main__":
    main()
