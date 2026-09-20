"""UW_SOURCE (TASK B2 Buoc 1, docs/PREREG_UW_DIAG.md) - UW that su den tu dau?
CHI DOC printDone.csv/sim.out cua T170 (X1_GS_T170_2021), gate-1.0 baseline
(X1_C3_FULL_2021) va P3 (X1_C3_FULL_2021_PACING_P3) + CLOSES_1H.bin (qua
bigdown_struct.hourly_grid). KHONG chay sim, KHONG xgboost, KHONG sua .java.
TAI DUNG NGUYEN VAN bigdown_struct.py/c3_rates.py (KHONG sua 2 file do).
Dung module logging, cam print().
Chay: cd /home/ubuntu/src/BinanceFuturesJava && python3 research/analysis/uw_source.py
Ghi: research/analysis/out/uw_source.json
"""
import json
import logging
import os
import sys
import numpy as np
import pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bigdown_struct as B  # noqa: E402  (tai dung: hourly_grid, build_bd_flags, load_trades_utc,
                             #              label_trades, block_boot_mean, new_entry_counts)
import c3_rates as C  # noqa: E402  (trades/equity)
logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("uw_source")
TAGS = {
    "T170": "X1_GS_T170_2021",
    "T100": "X1_C3_FULL_2021",
    "P3": "X1_C3_FULL_2021_PACING_P3",
}
OUT_JSON = os.path.join(HERE, "out", "uw_source.json")
GMT7_MS = 7 * 3600 * 1000
# --------------------------------------------------------------- EntryGate formula (TAI HIEN,
# CHI DOC, khong sua src/): EntryGate.java DYN_MIN/SCORE_BASE/DYN_MULT + Configs.MIN_MOMENTUM_15M.
# thr(symbolPred) = thrBase * max(DYN_MIN, (symbolPred/SCORE_BASE)*DYN_MULT) * gateScale
# PASS <=> pred15m >= thr.  gateScale = 1.0 (T100/P3) hoac 1.70 (T170).
THR_BASE = 0.008          # SIM_MIN_MOMENTUM_15M (x1_c3_full*.properties VA x1_gs_t170.properties)
DYN_MIN = 0.26787
SCORE_BASE = 0.15
DYN_MULT = 1.28760
GATE_100, GATE_170 = 1.0, 1.70
# =================================================================== UW streak finder
def uw_streaks(s):
    """RLE cac chuoi ngay lien tuc s < s.cummax(). Tra list dict sap xep dai->ngan."""
    peak = s.cummax()
    dd = (s / peak - 1.0) * 100.0
    uw = (s < peak).to_numpy()
    idx = s.index
    n = len(uw)
    streaks = []
    i = 0
    while i < n:
        if uw[i]:
            j = i
            while j + 1 < n and uw[j + 1]:
                j += 1
            seg = dd.iloc[i:j + 1]
            trough_pos = int(np.argmin(seg.values))
            streaks.append({
                "start": str(idx[i].date()), "end": str(idx[j].date()),
                "length_days": int(j - i + 1), "depth_pct": float(seg.min()),
                "trough_date": str(idx[i + trough_pos].date()),
            })
            i = j + 1
        else:
            i += 1
    streaks.sort(key=lambda r: -r["length_days"])
    return streaks
def overlap_mask(d, t0_ms, t1_ms):
    """True cho cac dong co [s_ms,e_ms] giao voi [t0_ms,t1_ms] (ca 2 dau bao gom)."""
    return (d["s_ms"].to_numpy() <= t1_ms) & (d["e_ms"].to_numpy() >= t0_ms)
def date_to_ms_utc(datestr, end_of_day=False):
    ts = pd.Timestamp(datestr)
    if end_of_day:
        ts = ts + pd.Timedelta(days=1) - pd.Timedelta(milliseconds=1)
    return int(ts.value // 10 ** 6) - GMT7_MS  # equity date la GMT+7; quy doi ve UTC ms moc grid
# =================================================================== Q2 BTC regime
def btc_daily_regime(grid, px):
    """Chuoi BTC theo ngay LOCAL (GMT+7, khop lich equity): close cuoi ngay, MA200, dd tu dinh
    365d, tre 30d/60d (TRAILING, causal - dung duoc lam dinh nghia regime cho pacing buoc 2)."""
    local_day = pd.to_datetime(grid + GMT7_MS, unit="ms").floor("D")
    s = pd.Series(px, index=local_day)
    daily_close = s.groupby(level=0).last().sort_index()
    ma200 = daily_close.rolling(200, min_periods=60).mean()
    roll_max_365 = daily_close.rolling(365, min_periods=30).max()
    dd_from_peak = (daily_close / roll_max_365 - 1.0) * 100.0
    ret30 = daily_close.pct_change(30) * 100.0
    ret60 = daily_close.pct_change(60) * 100.0
    below_ma200 = daily_close < ma200
    return pd.DataFrame({
        "close": daily_close, "ma200": ma200, "below_ma200": below_ma200,
        "dd_from_peak365_pct": dd_from_peak, "ret30_pct": ret30, "ret60_pct": ret60,
    })
def regime_summary(reg_df, start, end):
    seg = reg_df.loc[(reg_df.index >= pd.Timestamp(start)) & (reg_df.index <= pd.Timestamp(end))]
    if len(seg) == 0:
        return None
    return {
        "n_days": int(len(seg)),
        "pct_below_ma200": float(100.0 * seg["below_ma200"].mean()),
        "dd_from_peak365_mean": float(seg["dd_from_peak365_pct"].mean()),
        "dd_from_peak365_min": float(seg["dd_from_peak365_pct"].min()),
        "ret30_mean_pct": float(seg["ret30_pct"].mean(skipna=True)),
        "ret60_mean_pct": float(seg["ret60_pct"].mean(skipna=True)),
        "pct_ret30_negative": float(100.0 * (seg["ret30_pct"] < 0).mean()),
        "close_start": float(seg["close"].iloc[0]), "close_end": float(seg["close"].iloc[-1]),
        "btc_ret_over_window_pct": float(100.0 * (seg["close"].iloc[-1] / seg["close"].iloc[0] - 1.0)),
    }
# =================================================================== Q3 core vs marginal (EntryGate)
def label_core_marginal(d):
    """Phan loai TUNG dong theo dung cong thuc EntryGate.threshold() - KHONG khoa (sym,start).
    Ap dung duoc voi BAT KY tag nao (T100/P3 gate=1.0; doi chieu T170 gate=1.70 de kiem tra).
    """
    sp = pd.to_numeric(d.get("symbolPred"), errors="coerce")
    p15 = pd.to_numeric(d.get("pred15m"), errors="coerce")
    has_scale = sp.notna() & p15.notna()
    scale = np.maximum(DYN_MIN, (sp / SCORE_BASE) * DYN_MULT)
    thr100 = THR_BASE * scale * GATE_100
    thr170 = THR_BASE * scale * GATE_170
    lbl = pd.Series("unscaled", index=d.index)  # symbolPred==null: BIG_DOWN/DCA_LEVEL1/market-leg,
                                                 # KHONG bi gate scale -> co mat o CA T170 lan T100
    lbl[has_scale & (p15 >= thr170)] = "core"          # se qua duoc ca gate 1.70
    lbl[has_scale & (p15 >= thr100) & (p15 < thr170)] = "marginal"  # CHI qua duoc gate 1.0
    lbl[has_scale & (p15 < thr100)] = "below_gate100_anomaly"  # khong nen xay ra neu tag=gate1.0
    return lbl
def bucket_stats(d, lbl, mask=None):
    sub_idx = d.index if mask is None else d.index[mask]
    out = {}
    for name in ("core", "marginal", "unscaled", "below_gate100_anomaly"):
        m = (lbl.loc[sub_idx] == name)
        sub = d.loc[sub_idx[m]]
        if len(sub) == 0:
            out[name] = {"n": 0}
            continue
        obs, lo, hi = B.block_boot_mean(sub)
        out[name] = {
            "n": int(len(sub)), "roi_mean": obs, "roi_ci90_lo": lo, "roi_ci90_hi": hi,
            "loss_rate_pct": float(100.0 * (sub["roi"] < 0).mean()),
            "pnl_sum": float(sub["pnl"].sum()),
            "neg_pnl_sum": float(sub.loc[sub["pnl"] < 0, "pnl"].sum()),
        }
    total_neg = sum(v.get("neg_pnl_sum", 0.0) for v in out.values() if v.get("n", 0) > 0)
    for name, v in out.items():
        if v.get("n", 0) > 0 and total_neg < 0:
            v["pct_of_window_neg_pnl"] = float(100.0 * v["neg_pnl_sum"] / total_neg)
    return out
# =================================================================== Q4 dig-deeper vs oscillate
def streak_dynamics(tag, d, grid, start, end):
    s = C.equity(tag)
    seg = s.loc[(s.index >= pd.Timestamp(start)) & (s.index <= pd.Timestamp(end))]
    rets = seg.pct_change().dropna()
    up_days = int((rets > 0).sum())
    down_days = int((rets < 0).sum())
    flat_days = int((rets == 0).sum())
    # "rally" = >=3 ngay tang lien tuc ma KHONG vuot dinh cu (con trong UW)
    up_run, rallies, cur = [], 0, 0
    for r in rets:
        if r > 0:
            cur += 1
        else:
            if cur >= 3:
                rallies += 1
            cur = 0
    if cur >= 3:
        rallies += 1
    trough_level = float(seg.min())
    peak_before = float(s.loc[:seg.index[0]].max())
    max_partial_recover_pct = float(100.0 * (seg.max() - trough_level) / (peak_before - trough_level)) \
        if peak_before > trough_level else None
    t0_ms = date_to_ms_utc(start)
    t1_ms = date_to_ms_utc(end, end_of_day=True)
    opened_in = d[(d["s_ms"] >= t0_ms) & (d["s_ms"] <= t1_ms)]
    opened_out = d[(d["s_ms"] < t0_ms) | (d["s_ms"] > t1_ms)]
    hold_in = ((opened_in["e_ms"] - opened_in["s_ms"]) / 86400000.0)
    hold_out = ((opened_out["e_ms"] - opened_out["s_ms"]) / 86400000.0)
    n_days_window = max(1, (pd.Timestamp(end) - pd.Timestamp(start)).days + 1)
    overall_days = max(1, (d["s_ms"].max() - d["s_ms"].min()) / 86400000.0)
    return {
        "window_days": int(len(seg)), "up_days": up_days, "down_days": down_days,
        "flat_days": flat_days, "pct_up_days": float(100.0 * up_days / max(1, len(rets))),
        "daily_ret_std_pct": float(rets.std() * 100.0),
        "overall_daily_ret_std_pct": float(s.pct_change().dropna().std() * 100.0),
        "n_rallies_ge3d": rallies,
        "max_partial_recovery_pct_of_depth": max_partial_recover_pct,
        "n_opened_in_window": int(len(opened_in)),
        "opened_per_day_in_window": float(len(opened_in) / n_days_window),
        "opened_per_day_overall": float(len(d) / overall_days),
        "mean_holding_days_opened_in_window": float(hold_in.mean()) if len(hold_in) else None,
        "mean_holding_days_opened_outside_window": float(hold_out.mean()) if len(hold_out) else None,
    }
# =================================================================== Q5 T170 same window
def t170_behavior_in_window(d170, start, end):
    t0_ms = date_to_ms_utc(start)
    t1_ms = date_to_ms_utc(end, end_of_day=True)
    opened_in = d170[(d170["s_ms"] >= t0_ms) & (d170["s_ms"] <= t1_ms)]
    opened_out = d170[(d170["s_ms"] < t0_ms) | (d170["s_ms"] > t1_ms)]
    n_days_window = max(1, (pd.Timestamp(end) - pd.Timestamp(start)).days + 1)
    overall_days = max(1, (d170["s_ms"].max() - d170["s_ms"].min()) / 86400000.0)
    hold_in = ((opened_in["e_ms"] - opened_in["s_ms"]) / 86400000.0)
    hold_all = ((d170["e_ms"] - d170["s_ms"]) / 86400000.0)
    return {
        "n_opened_in_window": int(len(opened_in)),
        "opened_per_day_in_window": float(len(opened_in) / n_days_window),
        "opened_per_day_overall": float(len(d170) / overall_days),
        "admission_ratio_in_vs_overall": float((len(opened_in) / n_days_window) /
                                                (len(d170) / overall_days)) if len(d170) else None,
        "mean_holding_days_opened_in_window": float(hold_in.mean()) if len(hold_in) else None,
        "mean_holding_days_overall": float(hold_all.mean()) if len(hold_all) else None,
        "n_opened_out_window": int(len(opened_out)),
    }
def main():
    os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
    log.info("=== UW_SOURCE: nap grid gio + BTC ===")
    grid, px = B.hourly_grid()
    flags, extra = B.build_bd_flags(grid, px)
    flag_bd1a = flags["BD1a_5pct24h"]
    reg = btc_daily_regime(grid, px)
    trades, equities = {}, {}
    for name, tag in TAGS.items():
        trades[name] = B.load_trades_utc(tag)
        equities[name] = C.equity(tag)
        log.info("%s: n_rows=%d equity_days=%d", name, len(trades[name]), len(equities[name]))
    result = {"gate_formula": {"THR_BASE": THR_BASE, "DYN_MIN": DYN_MIN,
                                "SCORE_BASE": SCORE_BASE, "DYN_MULT": DYN_MULT}}
    # ---- Q1: chuoi UW dai nhat moi tag
    uw_by_tag = {name: uw_streaks(equities[name]) for name in TAGS}
    result["uw_streaks_top5"] = {name: uw_by_tag[name][:5] for name in TAGS}
    log.info("Q1 top streak T170=%s", uw_by_tag["T170"][0] if uw_by_tag["T170"] else None)
    log.info("Q1 top streak T100=%s", uw_by_tag["T100"][0] if uw_by_tag["T100"] else None)
    log.info("Q1 top streak P3=%s", uw_by_tag["P3"][0] if uw_by_tag["P3"] else None)
    top100 = uw_by_tag["T100"][0]
    topP3 = uw_by_tag["P3"][0]
    top170 = uw_by_tag["T170"][0]
    # ---- Q2: regime BTC trong chuoi UW dai nhat cua T100 va P3 (+ doi chieu T170)
    result["q2_regime"] = {
        "T100_longest_streak": regime_summary(reg, top100["start"], top100["end"]),
        "P3_longest_streak": regime_summary(reg, topP3["start"], topP3["end"]),
        "T170_longest_streak": regime_summary(reg, top170["start"], top170["end"]),
        "T170_during_T100_window": regime_summary(reg, top100["start"], top100["end"]),
    }
    # ---- Q3: core vs marginal trong chuoi UW dai nhat (T100 va P3)
    q3 = {}
    for name in ("T100", "P3"):
        d = trades[name].copy()
        lbl = label_core_marginal(d)
        top = uw_by_tag[name][0]
        t0_ms = date_to_ms_utc(top["start"])
        t1_ms = date_to_ms_utc(top["end"], end_of_day=True)
        mask_in = overlap_mask(d, t0_ms, t1_ms)
        mask_out = ~mask_in
        q3[name] = {
            "window": [top["start"], top["end"]],
            "n_overlap_window": int(mask_in.sum()),
            "label_counts_overlap": lbl.loc[d.index[mask_in]].value_counts().to_dict(),
            "label_counts_overall": lbl.value_counts().to_dict(),
            "bucket_stats_in_window": bucket_stats(d, lbl, mask_in),
            "bucket_stats_outside_window": bucket_stats(d, lbl, mask_out),
        }
        log.info("Q3 %s label_counts_overlap=%s", name, q3[name]["label_counts_overlap"])
    result["q3_core_vs_marginal"] = q3
    # ---- Q4: dao sau hay khong phuc hoi (T100 va P3, tren chinh chuoi UW cua tung tag)
    result["q4_dynamics"] = {
        "T100": streak_dynamics(TAGS["T100"], trades["T100"], grid, top100["start"], top100["end"]),
        "P3": streak_dynamics(TAGS["P3"], trades["P3"], grid, topP3["start"], topP3["end"]),
    }
    # ---- Q5: T170 lam gi khac trong CUNG cua so lich (dung window cua T100, la nguon UW=248)
    result["q5_t170_same_window"] = {
        "window_used": [top100["start"], top100["end"]],
        "t170": t170_behavior_in_window(trades["T170"], top100["start"], top100["end"]),
        "t170_own_longest_streak": top170,
    }
    with open(OUT_JSON, "w") as f:
        json.dump(result, f, indent=2, default=str)
    log.info("DONE -> %s", OUT_JSON)
if __name__ == "__main__":
    main()
