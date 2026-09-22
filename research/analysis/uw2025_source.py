"""UW2025_SOURCE - chan doan nguon UW-2025 (doc lap voi BTC-trend), theo
docs/PREREG_UW2025_DIAG.md. CHI DOC printDone.csv/sim.out cua T170 (X1_GS_T170_2021), gate-1.0
(X1_C3_FULL_2021), R (X1_C3_FULL_2021_REGIME_R) + CLOSES_1H.bin. KHONG chay sim, KHONG xgboost,
KHONG sua .java. TAI DUNG NGUYEN VAN uw_source.py/bigdown_struct.py/hedge_overlay_a.py/c3_rates.py
(KHONG sua cac file do). Dung module logging, cam print().

Chay: cd /home/ubuntu/src/BinanceFuturesJava && python3 research/analysis/uw2025_source.py
Ghi: research/analysis/out/uw2025_source.json
"""
import json
import logging
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bigdown_struct as B          # noqa: E402  (hourly_grid, build_bd_flags, load_universe_breadth,
                                     #              equity_at_grid, block_boot_mean, load_trades_utc)
import c3_rates as C                # noqa: E402  (trades, equity)
import uw_source as U                # noqa: E402  (uw_streaks, btc_daily_regime, regime_summary,
                                     #              label_core_marginal, date_to_ms_utc, overlap_mask)
from hedge_overlay_a import sum_notional_on_grid  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("uw2025_source")

TAGS = {"T170": "X1_GS_T170_2021", "T100": "X1_C3_FULL_2021", "R": "X1_C3_FULL_2021_REGIME_R"}
OUT_JSON = os.path.join(HERE, "out", "uw2025_source.json")
YEAR2025_START, YEAR2025_END = "2025-01-01", "2025-12-31"


def streaks_overlapping_2025(streaks):
    return [s for s in streaks if not (s["end"] < YEAR2025_START or s["start"] > YEAR2025_END)]


# ------------------------------------------------------------------ Q2 nhung chi so MOI
def market_env_window(reg_df, grid, breadth_t, breadth_v, start, end):
    base = U.regime_summary(reg_df, start, end)
    if base is None:
        return None
    seg = reg_df.loc[(reg_df.index >= pd.Timestamp(start)) & (reg_df.index <= pd.Timestamp(end))]
    close = seg["close"].to_numpy()
    rets = pd.Series(close).pct_change().dropna().to_numpy()
    realized_vol = float(np.std(rets) * 100.0) if len(rets) else None
    range_pct = float(100.0 * (close.max() - close.min()) / close[0]) if len(close) else None
    net_ret = base["btc_ret_over_window_pct"]
    chop_ratio = float(range_pct / abs(net_ret)) if (range_pct is not None and abs(net_ret) > 1e-9) else float("inf")
    signs = np.sign(rets)
    signs = signs[signs != 0]
    n_flips = int((np.diff(signs) != 0).sum()) if len(signs) > 1 else 0
    n_days = max(1, (pd.Timestamp(end) - pd.Timestamp(start)).days + 1)
    flips_per_30d = float(30.0 * n_flips / n_days)
    t0_ms = U.date_to_ms_utc(start)
    t1_ms = U.date_to_ms_utc(end, end_of_day=True)
    m = (breadth_t >= t0_ms) & (breadth_t <= t1_ms)
    breadth_mean = float(np.mean(breadth_v[m])) if m.sum() else None
    base.update({
        "realized_vol_daily_pct": realized_vol,
        "realized_vol_annualized_pct": (realized_vol * (365.0 ** 0.5)) if realized_vol is not None else None,
        "range_pct": range_pct,
        "chop_ratio": chop_ratio,
        "n_sign_flips_per_30d": flips_per_30d,
        "breadth_pct_red_mean": breadth_mean,
    })
    label = "KHAC"
    if net_ret is not None and abs(net_ret) < 15 and chop_ratio >= 2.0 and 30 <= base["pct_below_ma200"] <= 70:
        label = "CHOP_KHONG_XUHUONG"
    elif net_ret is not None and net_ret <= -15 and base["pct_below_ma200"] < 50:
        label = "DOWNTREND_NHE_MA200_KHONG_BAT"
    base["classification"] = label
    return base


# ------------------------------------------------------------------ Q3 concurrency
def concurrent_series(d, grid):
    s_idx = np.clip(np.searchsorted(grid, d["s_ms"].to_numpy(), side="right") - 1, 0, len(grid) - 1)
    e_idx = np.clip(np.searchsorted(grid, d["e_ms"].to_numpy(), side="right") - 1, 0, len(grid) - 1)
    delta = np.zeros(len(grid) + 1, dtype=np.float64)
    np.add.at(delta, s_idx, 1.0)
    np.add.at(delta, np.minimum(e_idx + 1, len(grid)), -1.0)
    return np.cumsum(delta)[:-1]


def exposure_stats(name_desc, k, ratio, mask):
    kk, rr = k[mask], ratio[mask]
    rr = rr[np.isfinite(rr)]

    def s(a):
        if len(a) == 0:
            return None
        return {"mean": float(np.mean(a)), "median": float(np.median(a)),
                "p90": float(np.percentile(a, 90)), "max": float(np.max(a)), "n_hours": int(len(a))}
    return {"desc": name_desc, "k_concurrent": s(kk), "notional_over_equity": s(rr)}


# ------------------------------------------------------------------ Q4 quality/drift by year
def year_quality(d, tag_name):
    out = {}
    for yr in (2021, 2022, 2023, 2024, 2025):
        sub = d[d["t0"].dt.year == yr]
        if len(sub) == 0:
            out[str(yr)] = {"n": 0}
            continue
        obs, lo, hi = B.block_boot_mean(sub)
        out[str(yr)] = {
            "n": int(len(sub)), "roi_mean": obs, "roi_ci90_lo": lo, "roi_ci90_hi": hi,
            "win_rate_pct": float(100.0 * (sub["roi"] > 0).mean()),
        }
    return out


def year_quality_marginal(d):
    lbl = U.label_core_marginal(d)
    out = {}
    for yr in (2021, 2022, 2023, 2024, 2025):
        sub = d[(d["t0"].dt.year == yr) & (lbl == "marginal")]
        if len(sub) == 0:
            out[str(yr)] = {"n": 0}
            continue
        obs, lo, hi = B.block_boot_mean(sub)
        out[str(yr)] = {
            "n": int(len(sub)), "roi_mean": obs, "roi_ci90_lo": lo, "roi_ci90_hi": hi,
            "win_rate_pct": float(100.0 * (sub["roi"] > 0).mean()),
        }
    # gop 2021-2024 lam mau doi chieu
    sub_hist = d[(d["t0"].dt.year.isin([2021, 2022, 2023, 2024])) & (lbl == "marginal")]
    obs, lo, hi = B.block_boot_mean(sub_hist)
    out["2021_2024_pooled"] = {
        "n": int(len(sub_hist)), "roi_mean": obs, "roi_ci90_lo": lo, "roi_ci90_hi": hi,
        "win_rate_pct": float(100.0 * (sub_hist["roi"] > 0).mean()) if len(sub_hist) else None,
    }
    return out


# ------------------------------------------------------------------ Q5 counterfactual cap
def retroactive_cap(d, equity_grid_t, equity_grid_v, cap_type, cap_value):
    """d da sort theo s_ms tang dan. Tra ve (admitted_mask, synthetic_equity_series)."""
    n = len(d)
    s_ms = d["s_ms"].to_numpy()
    e_ms = d["e_ms"].to_numpy()
    notional = d["notional"].to_numpy()
    pnl = d["pnl"].to_numpy()
    order = np.argsort(s_ms, kind="mergesort")
    open_end = []   # list cua (e_ms, notional) dang mo, giu tho de don gian (so luong nho, ~2500)
    admitted = np.zeros(n, dtype=bool)
    for i in order:
        # bo lenh da dong khoi tap dang mo
        open_end = [(e, nt) for (e, nt) in open_end if e >= s_ms[i]]
        cur_count = len(open_end)
        cur_notional = sum(nt for _, nt in open_end)
        eq_now_idx = np.searchsorted(equity_grid_t, s_ms[i], side="right") - 1
        eq_now = equity_grid_v[max(0, min(eq_now_idx, len(equity_grid_v) - 1))]
        if cap_type == "count":
            ok = (cur_count + 1) <= cap_value
        else:  # notional
            ok = (eq_now <= 0) or ((cur_notional + notional[i]) / eq_now) <= cap_value
        if ok:
            admitted[i] = True
            open_end.append((e_ms[i], notional[i]))
    E0 = float(C.equity(TAGS["T100"]).iloc[0])
    adm = d.loc[admitted].copy()
    adm = adm.sort_values("e_ms")
    exit_day = pd.to_datetime(adm["e_ms"] + 7 * 3600 * 1000, unit="ms").dt.floor("D")
    daily_pnl = adm.groupby(exit_day)["pnl"].sum()
    full_idx = C.equity(TAGS["T100"]).index
    daily_pnl = daily_pnl.reindex(full_idx, fill_value=0.0)
    synth = E0 + daily_pnl.cumsum()
    return admitted, synth


def main():
    os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
    log.info("=== UW2025_SOURCE: nap grid gio + BTC + breadth ===")
    grid, px = B.hourly_grid()
    reg = U.btc_daily_regime(grid, px)
    breadth_t, breadth_v = B.load_universe_breadth()

    trades, equities = {}, {}
    for name, tag in TAGS.items():
        trades[name] = B.load_trades_utc(tag)
        equities[name] = C.equity(tag)
        log.info("%s: n_rows=%d equity_days=%d", name, len(trades[name]), len(equities[name]))

    result = {}

    # ---- Q1
    streaks = {name: U.uw_streaks(equities[name]) for name in TAGS}
    streaks_2025 = {name: streaks_overlapping_2025(streaks[name]) for name in TAGS}
    result["q1_streaks_2025"] = streaks_2025
    result["q1_streaks_top5_all"] = {name: streaks[name][:5] for name in TAGS}
    for name in TAGS:
        log.info("Q1 %s n_streaks_overlap_2025=%d longest=%s", name, len(streaks_2025[name]),
                  streaks_2025[name][0] if streaks_2025[name] else None)

    win_T100 = streaks_2025["T100"][0]
    win_R = streaks_2025["R"][0]
    win_T170_2025 = streaks_2025["T170"][0] if streaks_2025["T170"] else None
    result["q1_windows_used"] = {"T100": win_T100, "R": win_R, "T170_2025": win_T170_2025}

    # ---- Q2 market env: T100_win, R_win, T170 same-calendar-as-T100_win, T170 own-2025-window
    result["q2_market_env"] = {
        "T100_win": market_env_window(reg, grid, breadth_t, breadth_v, win_T100["start"], win_T100["end"]),
        "R_win": market_env_window(reg, grid, breadth_t, breadth_v, win_R["start"], win_R["end"]),
        "T170_same_calendar_as_T100_win": market_env_window(reg, grid, breadth_t, breadth_v,
                                                             win_T100["start"], win_T100["end"]),
        "T170_own_2025_window": (market_env_window(reg, grid, breadth_t, breadth_v,
                                                     win_T170_2025["start"], win_T170_2025["end"])
                                  if win_T170_2025 else None),
    }
    log.info("Q2 T100_win classification=%s", result["q2_market_env"]["T100_win"]["classification"])

    # ---- Q3 concurrency
    eq_t100_grid = B.equity_at_grid(TAGS["T100"], grid)
    notional_t100 = sum_notional_on_grid(trades["T100"], grid)
    ratio_t100 = np.where(np.isfinite(eq_t100_grid) & (eq_t100_grid > 0),
                           notional_t100 / eq_t100_grid, np.nan)
    k_t100 = concurrent_series(trades["T100"], grid)

    eq_t170_grid = B.equity_at_grid(TAGS["T170"], grid)
    notional_t170 = sum_notional_on_grid(trades["T170"], grid)
    ratio_t170 = np.where(np.isfinite(eq_t170_grid) & (eq_t170_grid > 0),
                           notional_t170 / eq_t170_grid, np.nan)
    k_t170 = concurrent_series(trades["T170"], grid)

    eq_r_grid = B.equity_at_grid(TAGS["R"], grid)
    notional_r = sum_notional_on_grid(trades["R"], grid)
    ratio_r = np.where(np.isfinite(eq_r_grid) & (eq_r_grid > 0), notional_r / eq_r_grid, np.nan)
    k_r = concurrent_series(trades["R"], grid)

    t0_100 = U.date_to_ms_utc(win_T100["start"]); t1_100 = U.date_to_ms_utc(win_T100["end"], True)
    t0_r = U.date_to_ms_utc(win_R["start"]); t1_r = U.date_to_ms_utc(win_R["end"], True)
    mask_in_100 = (grid >= t0_100) & (grid <= t1_100)
    mask_out_100 = ~mask_in_100
    mask_in_r = (grid >= t0_r) & (grid <= t1_r)

    # moc so sanh phu: cua so UW-2022 that (Buoc 1) cho T100
    t0_22 = U.date_to_ms_utc("2021-11-16"); t1_22 = U.date_to_ms_utc("2022-07-21", True)
    mask_2022_100 = (grid >= t0_22) & (grid <= t1_22)

    result["q3_exposure"] = {
        "T100_in_win2025": exposure_stats("T100 trong T100_win (2025)", k_t100, ratio_t100, mask_in_100),
        "T100_outside_2025win": exposure_stats("T100 ngoai T100_win", k_t100, ratio_t100, mask_out_100),
        "T100_in_uw2022": exposure_stats("T100 trong cua so UW-2022 (Buoc1, moc doi chieu)",
                                          k_t100, ratio_t100, mask_2022_100),
        "T170_same_calendar_as_T100win": exposure_stats("T170 cung lich T100_win", k_t170, ratio_t170, mask_in_100),
        "R_in_Rwin2025": exposure_stats("R trong R_win (2025)", k_r, ratio_r, mask_in_r),
    }

    # ---- Q4 quality by year
    result["q4_quality_by_year"] = {
        "T100": year_quality(trades["T100"], "T100"),
        "T170": year_quality(trades["T170"], "T170"),
        "R": year_quality(trades["R"], "R"),
    }
    result["q4_marginal_by_year_T100"] = year_quality_marginal(trades["T100"])
    log.info("Q4 marginal 2025 vs pooled: %s vs %s",
              result["q4_marginal_by_year_T100"]["2025"], result["q4_marginal_by_year_T100"]["2021_2024_pooled"])

    # ---- Q5 retroactive cap counterfactual
    d100 = trades["T100"].sort_values("s_ms").reset_index(drop=True)
    n_total = len(d100)
    eq100 = equities["T100"]
    eq_grid_t = eq100.index.values.astype("datetime64[ms]").astype(np.int64) - 7 * 3600 * 1000
    order = np.argsort(eq_grid_t)
    eq_grid_t = eq_grid_t[order]
    eq_grid_v = eq100.to_numpy(dtype=np.float64)[order]

    q5 = {}
    scenarios = [("count", k) for k in (3, 4, 5, 6, 8)] + [("notional", x) for x in (0.15, 0.25, 0.35, 0.45)]
    for cap_type, cap_val in scenarios:
        admitted, synth = retroactive_cap(d100, eq_grid_t, eq_grid_v, cap_type, cap_val)
        st = U.uw_streaks(synth)
        st2025 = streaks_overlapping_2025(st)
        n_dropped = int((~admitted).sum())
        dropped_in_win = int(((~admitted) & ((d100["s_ms"] >= t0_100) & (d100["s_ms"] <= t1_100))).sum())
        key = "%s_%s" % (cap_type, cap_val)
        q5[key] = {
            "cap_type": cap_type, "cap_value": cap_val,
            "n_dropped_total": n_dropped, "pct_dropped_total": float(100.0 * n_dropped / n_total),
            "n_dropped_in_T100win": dropped_in_win,
            "n_dropped_outside_T100win": n_dropped - dropped_in_win,
            "uw2025_longest_after_cap": st2025[0] if st2025 else None,
            "uw_overall_longest_after_cap": st[0] if st else None,
            "final_synth_equity": float(synth.iloc[-1]),
        }
        log.info("Q5 %s: dropped=%d(%.1f%%) uw2025=%s", key, n_dropped, q5[key]["pct_dropped_total"],
                  st2025[0]["length_days"] if st2025 else None)
    result["q5_retroactive_cap"] = q5

    passing = [v for v in q5.values()
               if v["uw2025_longest_after_cap"] is not None
               and v["uw2025_longest_after_cap"]["length_days"] <= 200
               and v["pct_dropped_total"] <= 50.0]
    result["q5_verdict"] = {
        "conc_cap_has_potential": bool(len(passing) > 0),
        "passing_scenarios": [{"cap_type": v["cap_type"], "cap_value": v["cap_value"],
                                "pct_dropped_total": v["pct_dropped_total"],
                                "uw2025_days": v["uw2025_longest_after_cap"]["length_days"]}
                               for v in passing],
    }
    log.info("Q5 VERDICT conc_cap_has_potential=%s n_passing=%d",
              result["q5_verdict"]["conc_cap_has_potential"], len(passing))

    with open(OUT_JSON, "w") as f:
        json.dump(result, f, indent=2, default=str)
    log.info("DONE -> %s", OUT_JSON)


if __name__ == "__main__":
    main()
