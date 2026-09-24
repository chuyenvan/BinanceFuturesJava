"""BETA_DECOMP_T170 - phan tach ALPHA (selector S1) vs BETA (BTC market timing
qua gate SIM_GATE_DYN_SCALE) cho T170 va doi chung X1_C3_FULL.

Cau hoi nghien cuu: CAGR ~29%/nam cua T170 chu yeu la alpha xep hang coin (S1)
hay chi la beta thi truong BTC duoc gate bat/tat dung luc?

LUAT DOC D (PRE-DECLARED boi MASTER, chep NGUYEN VAN, KHONG duoc doi sau khi
thay so - xem bien READING_RULE_D o duoi va docs/analysis/ANALYSIS_BETA_DECOMP_T170.md):
"(i) Neu phan beta >= 60% tong loi nhuan log VA |t(alpha)| < 2 => nhan CHU YEU
BETA (toi uu selector S1 tiep la toi uu sai cho; san pham that dang van hanh la
mot chien luoc BTC-beta co timing qua gate). (ii) Neu phan beta <= 40% VA
|t(alpha)| >= 2 => nhan CHU YEU ALPHA. (iii) Cac truong hop con lai => nhan HON
HOP, bao ro ti le %." Khong duoc ket luan gi them ngoai 3 nhan nay o phan D.

Nguon du lieu (CHI DOC, khong sua):
  - equity ngay: java/devrun/<TAG>/logs/sim.out, dong
    'Update YYYYMMDD HH:MM => b:<B> ... unP:<U>'; equity = B+U, ban ghi CUOI
    CUNG moi ngay. TAI SU DUNG research/analysis/c3_rates.py::equity() (khong
    tu viet parser moi).
  - lenh: java/devrun/<TAG>/storage/printDone.csv. TAI SU DUNG
    research/analysis/c3_rates.py::trades() (leg/blk deu tu day, on_bad_lines
    ='skip'). Cot 'margin' trong file nay THUC RA la notional = quantity*entry
    (doi chieu voi MaeDistributionProbe.java: c.notional += o.quantity *
    o.priceEntry; kiem tra so hoc tren 3 dong dau printDone.csv khop notional
    tinh tay trong pham vi lam tron gia). c3_rates.py cung dung thang cot nay
    (r["margin"] = d.margin.mean()) ma khong chia them cho don bay => day la
    "cach c3_rates.py dang tinh" duoc pre-reg yeu cau tai su dung.
  - gia dong BTC 1h: java/fsrun/CLOSES_1H.bin. TAI SU DUNG
    research/analysis/trend_rank_ic.py::load_closes() (dtype
    [('ts','>i8'),('sym','>i2'),('c','>f4')], ctime = open_time + 1h, quy uoc
    causal). symId cua BTCUSDT = 1 (selector_pred_out/symbol_map.csv).

Moc ghep thoi gian (DA KIEM TRA truoc khi chay toan bo - xem
docs/analysis/ANALYSIS_BETA_DECOMP_T170.md muc "kiem tra mui gio"):
  - JVM sim chay voi -Duser.timezone=Asia/Ho_Chi_Minh => nhan 'Update YYYYMMDD'
    trong sim.out LA LICH GMT+7.
  - Tang ngay: gia BTC dung cho ngay D = close 1h co ctime <= 00:00 UTC ngay D
    (= 07:00 GMT+7 ngay D, dung boi de bai). Kiem tra thuc te tren 10 mau dau/
    cuoi cua T170: delta_h = 0.0 (khop CHINH XAC, khong lech gio).
  - Tang lenh: cot start/end trong printDone.csv la GIO GMT+7 NAIVE (vd
    '20251201 07:09'). Quy doi UTC = gio_naive - 7h, roi tim gia BTC dong 1h
    GAN NHAT <= moc do (ham btc_at_or_before, searchsorted side='right'-1).
  - Ngay-co-vi-the-mo (sanity check): dung LICH GMT+7 truc tiep tu start/end
    cua printDone.csv (KHONG quy doi UTC) vi day la CUNG he quy chieu voi nhan
    'Update YYYYMMDD' trong sim.out (ca hai deu la lich JVM Asia/Ho_Chi_Minh).

Chay (idempotent, khong sua du lieu nguon):
  cd /home/ubuntu/src/BinanceFuturesJava && python3 research/analysis/beta_decomp_t170.py
Ghi ra: /home/ubuntu/s1hpo/beta_decomp.json (scratch tren Oracle, khong commit git).

LUAT REPO: dung module logging, KHONG dung print().
"""
import json
import logging
import os
import sys

import numpy as np
import pandas as pd
import statsmodels.api as sm

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import c3_rates as C  # noqa: E402  (tai su dung equity()/trades())
from trend_rank_ic import load_closes  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("beta_decomp")

TAGS = {"T170": "X1_GS_T170_2021", "BASELINE": "X1_C3_FULL_2021"}
WIN_START = pd.Timestamp("2021-07-01")
WIN_END = pd.Timestamp("2025-12-31 23:59:59")
YEARS = (2021, 2022, 2023, 2024, 2025)
HAC_LAGS = 5
BTC_SYM_ID = 1
OUT_JSON = "/home/ubuntu/s1hpo/beta_decomp.json"
MIN_N_OLS = 10

READING_RULE_D = (
    "(i) Neu phan beta >= 60% tong loi nhuan log VA |t(alpha)| < 2 => nhan "
    "CHU YEU BETA (toi uu selector S1 tiep la toi uu sai cho; san pham that "
    "dang van hanh la mot chien luoc BTC-beta co timing qua gate). "
    "(ii) Neu phan beta <= 40% VA |t(alpha)| >= 2 => nhan CHU YEU ALPHA. "
    "(iii) Cac truong hop con lai => nhan HON HOP, bao ro ti le %. Khong duoc "
    "ket luan gi them ngoai 3 nhan nay o phan D."
)


def load_btc_series():
    btc = load_closes()
    btc = btc[btc["sym"] == BTC_SYM_ID].sort_values("ctime").reset_index(drop=True)
    return btc["ctime"].to_numpy(dtype=np.int64), btc["close"].to_numpy(dtype=np.float64)


CTIME, CLOSE = load_btc_series()


def btc_at_or_before(target_ms):
    """Gia dong BTC 1h GAN NHAT co ctime <= target_ms (vector hoa)."""
    target_ms = np.asarray(target_ms, dtype=np.int64)
    idx = np.searchsorted(CTIME, target_ms, side="right") - 1
    ok = (idx >= 0) & (target_ms >= CTIME[0])
    idx_c = np.clip(idx, 0, len(CLOSE) - 1)
    return np.where(ok, CLOSE[idx_c], np.nan)


def ols_hac(y, x, lags=HAC_LAGS):
    y = np.asarray(y, dtype=float)
    x = np.asarray(x, dtype=float)
    m = np.isfinite(y) & np.isfinite(x)
    y, x = y[m], x[m]
    n = len(y)
    if n < MIN_N_OLS or np.std(x) == 0:
        return {"n": n, "alpha": float("nan"), "beta": float("nan"),
                "r2": float("nan"), "t_alpha": float("nan"), "t_beta": float("nan"),
                "note": "N<%d hoac x khong bien thien" % MIN_N_OLS}
    X = sm.add_constant(x)
    fit = sm.OLS(y, X).fit(cov_type="HAC", cov_kwds={"maxlags": lags})
    return {"n": n, "alpha": float(fit.params[0]), "beta": float(fit.params[1]),
            "r2": float(fit.rsquared), "t_alpha": float(fit.tvalues[0]),
            "t_beta": float(fit.tvalues[1])}


def ols_cluster(y, x, groups):
    """OLS voi cluster-robust SE theo ngay vao lenh (thay the HAC o tang lenh,
    dung ho tro san co cua statsmodels; xem gioi han trong doc .md)."""
    y = np.asarray(y, dtype=float)
    x = np.asarray(x, dtype=float)
    groups = np.asarray(groups)
    m = np.isfinite(y) & np.isfinite(x)
    y, x, groups = y[m], x[m], groups[m]
    n = len(y)
    if n < MIN_N_OLS or np.std(x) == 0:
        return {"n": n, "a": float("nan"), "b": float("nan"), "r2": float("nan"),
                "t_a": float("nan"), "t_b": float("nan"), "n_clusters": 0,
                "note": "N<%d hoac x khong bien thien" % MIN_N_OLS}
    X = sm.add_constant(x)
    try:
        fit = sm.OLS(y, X).fit(cov_type="cluster", cov_kwds={"groups": groups})
    except Exception:
        fit = sm.OLS(y, X).fit(cov_type="HAC", cov_kwds={"maxlags": HAC_LAGS})
    return {"n": n, "a": float(fit.params[0]), "b": float(fit.params[1]),
            "r2": float(fit.rsquared), "t_a": float(fit.tvalues[0]),
            "t_b": float(fit.tvalues[1]), "n_clusters": int(len(np.unique(groups)))}


def pct_beta_of_total(beta, sum_r_b, sum_r_s):
    if not np.isfinite(beta) or abs(sum_r_s) < 1e-6:
        return float("nan")
    return float(100.0 * beta * sum_r_b / sum_r_s)


def daily_frame(tag):
    e = C.equity(tag)
    e = e[(e.index >= WIN_START) & (e.index <= WIN_END)]
    target_ms = e.index.values.astype("datetime64[ms]").astype(np.int64)
    btc_px = btc_at_or_before(target_ms)
    df = pd.DataFrame({"equity": e.values.astype(float), "btc": btc_px}, index=e.index)
    df["r_s"] = np.log(df["equity"] / df["equity"].shift(1))
    df["r_b"] = np.log(df["btc"] / df["btc"].shift(1))
    return df


def position_open_mask(tag, day_index):
    """True neu ngay (lich GMT+7, dung he quy chieu voi 'Update YYYYMMDD' trong
    sim.out) nam trong [start,end] cua IT NHAT 1 lenh dang mo."""
    d = C.trades(tag)
    start_d = pd.to_datetime(d["start"].str.slice(0, 8), format="%Y%m%d")
    end_d = pd.to_datetime(d["end"].str.slice(0, 8), format="%Y%m%d")
    open_days = set()
    for s, en in zip(start_d, end_d):
        for dd in pd.date_range(s, en, freq="D"):
            open_days.add(dd)
    return pd.Series(day_index.isin(open_days), index=day_index)


def _add_pct_and_dualbeta(res, sub):
    sum_rs = float(sub["r_s"].sum())
    res["sum_r_s"] = sum_rs
    res["alpha_annual_pct"] = res["alpha"] * 365 * 100 if np.isfinite(res["alpha"]) else float("nan")
    res["pct_beta_of_total"] = pct_beta_of_total(res["beta"], float(sub["r_b"].sum()), sum_rs)
    up = sub[sub.r_b > 0]
    down = sub[sub.r_b <= 0]
    res_up = ols_hac(up["r_s"], up["r_b"])
    res_dn = ols_hac(down["r_s"], down["r_b"])
    res["beta_up"] = res_up["beta"]
    res["beta_down"] = res_dn["beta"]
    res["n_up"] = res_up["n"]
    res["n_down"] = res_dn["n"]
    return res


def decomp_daily(tag, label):
    df = daily_frame(tag)
    out = {}
    for yr in YEARS:
        sub = df[df.index.year == yr].dropna(subset=["r_s", "r_b"])
        res = ols_hac(sub["r_s"], sub["r_b"])
        res = _add_pct_and_dualbeta(res, sub)
        out[str(yr)] = res

    full = df.dropna(subset=["r_s", "r_b"])
    res_full = ols_hac(full["r_s"], full["r_b"])
    res_full = _add_pct_and_dualbeta(res_full, full)
    out["FULL"] = res_full

    # sanity check pre-declared: ngay CO vi the mo vs KHONG co vi the nao mo
    open_mask = position_open_mask(tag, full.index)
    d_open = full[open_mask.values]
    d_noopen = full[~open_mask.values]
    res_open = ols_hac(d_open["r_s"], d_open["r_b"])
    res_noopen = ols_hac(d_noopen["r_s"], d_noopen["r_b"])
    out["SANITY_POSITION_OPEN"] = res_open
    out["SANITY_NO_POSITION"] = res_noopen
    log.info("[%s] sanity ngay KHONG-vi-the-mo: n=%d beta=%s (ky vong ~0)",
             label, res_noopen["n"], res_noopen.get("beta"))

    # sanity: sum(r_s) phai telescope ve dung log-return toan ky cua equity
    e0, e1 = full["equity"].iloc[0], full["equity"].iloc[-1]
    log.info("[%s] sanity sum(r_s)=%.6f vs ln(equity_end/equity_start)=%.6f",
              label, full["r_s"].sum(), np.log(e1 / e0))
    return out


def trade_frame(tag):
    d = C.trades(tag).copy()
    start = pd.to_datetime(d["start"], format="%Y%m%d %H:%M")
    end = pd.to_datetime(d["end"], format="%Y%m%d %H:%M")
    start_utc_ms = (start - pd.Timedelta(hours=7)).values.astype("datetime64[ms]").astype(np.int64)
    end_utc_ms = (end - pd.Timedelta(hours=7)).values.astype("datetime64[ms]").astype(np.int64)
    d["r_btc_hold"] = np.log(btc_at_or_before(end_utc_ms) / btc_at_or_before(start_utc_ms))
    d["entry_day_gmt7"] = start.dt.floor("D")
    d["year"] = start.dt.year
    d["start_ts"] = start
    # notional = margin (cach c3_rates.py dang dung / doi chieu MaeDistributionProbe.java)
    d["notional"] = d["margin"]
    d["pnl_btc_only"] = d["notional"] * d["r_btc_hold"]
    return d[(start >= WIN_START) & (start <= WIN_END)]


def _trade_group_stats(sub):
    res = ols_cluster(sub["profit"], sub["r_btc_hold"], sub["entry_day_gmt7"])
    pos = sub[sub.r_btc_hold > 0]
    neg = sub[sub.r_btc_hold <= 0]
    res["n_pos"] = int(len(pos))
    res["n_neg"] = int(len(neg))
    res["sum_pnl_pos"] = float(pos["pnl"].sum()) if len(pos) else float("nan")
    res["sum_pnl_neg"] = float(neg["pnl"].sum()) if len(neg) else float("nan")
    res["winrate_pos_pct"] = float(100.0 * (pos["profit"] > 0).mean()) if len(pos) else float("nan")
    res["winrate_neg_pct"] = float(100.0 * (neg["profit"] > 0).mean()) if len(neg) else float("nan")
    res["sum_pnl_actual"] = float(sub["pnl"].sum())
    res["sum_pnl_btc_only"] = float(sub["pnl_btc_only"].sum())
    return res


def decomp_trades(tag, label):
    d = trade_frame(tag)
    out = {}
    for yr in YEARS:
        sub = d[d.year == yr]
        out[str(yr)] = _trade_group_stats(sub)
    out["FULL"] = _trade_group_stats(d)
    return out


def label_D(pct_beta_full, t_alpha_full):
    if np.isfinite(pct_beta_full) and np.isfinite(t_alpha_full) \
            and pct_beta_full >= 60 and abs(t_alpha_full) < 2:
        return "CHU YEU BETA"
    if np.isfinite(pct_beta_full) and np.isfinite(t_alpha_full) \
            and pct_beta_full <= 40 and abs(t_alpha_full) >= 2:
        return "CHU YEU ALPHA"
    return "HON HOP"


def main():
    result = {
        "reading_rule_D": READING_RULE_D,
        "window": [str(WIN_START.date()), str(WIN_END.date())],
        "hac_lags_daily": HAC_LAGS,
        "trade_se": "cluster-robust theo ngay vao lenh (statsmodels cov_type=cluster)",
        "btc_sym_id": BTC_SYM_ID,
        "notional_definition": "cot 'margin' trong printDone.csv (= quantity*entry, doi chieu MaeDistributionProbe.java)",
    }
    for label, tag in TAGS.items():
        log.info("############ %s (%s) ############", label, tag)
        log.info("=== TANG NGAY ===")
        daily = decomp_daily(tag, label)
        for k in list(YEARS) + ["FULL", "SANITY_POSITION_OPEN", "SANITY_NO_POSITION"]:
            v = daily[str(k)] if str(k) in daily else daily[k]
            log.info("  %-22s n=%-5s alpha=%-10s beta=%-8s r2=%-6s t_a=%-7s pct_beta=%-7s bUp=%-7s bDn=%-7s",
                      k, v.get("n"),
                      round(v["alpha"], 6) if np.isfinite(v.get("alpha", float("nan"))) else "nan",
                      round(v.get("beta", float("nan")), 4) if np.isfinite(v.get("beta", float("nan"))) else "nan",
                      round(v.get("r2", float("nan")), 4) if np.isfinite(v.get("r2", float("nan"))) else "nan",
                      round(v.get("t_alpha", float("nan")), 3) if np.isfinite(v.get("t_alpha", float("nan"))) else "nan",
                      round(v.get("pct_beta_of_total", float("nan")), 1) if np.isfinite(v.get("pct_beta_of_total", float("nan"))) else "nan",
                      round(v.get("beta_up", float("nan")), 4) if np.isfinite(v.get("beta_up", float("nan"))) else "nan",
                      round(v.get("beta_down", float("nan")), 4) if np.isfinite(v.get("beta_down", float("nan"))) else "nan")

        log.info("=== TANG LENH ===")
        trd = decomp_trades(tag, label)
        for k in list(YEARS) + ["FULL"]:
            v = trd[str(k)]
            log.info("  %-8s n=%-5s a=%-9s b=%-9s r2=%-6s t_b=%-7s nclu=%-4s "
                      "pnl_act=%-10s pnl_btc=%-10s winPos=%-6s winNeg=%-6s",
                      k, v.get("n"),
                      round(v.get("a", float("nan")), 4) if np.isfinite(v.get("a", float("nan"))) else "nan",
                      round(v.get("b", float("nan")), 4) if np.isfinite(v.get("b", float("nan"))) else "nan",
                      round(v.get("r2", float("nan")), 4) if np.isfinite(v.get("r2", float("nan"))) else "nan",
                      round(v.get("t_b", float("nan")), 3) if np.isfinite(v.get("t_b", float("nan"))) else "nan",
                      v.get("n_clusters"),
                      round(v.get("sum_pnl_actual", float("nan")), 1),
                      round(v.get("sum_pnl_btc_only", float("nan")), 1),
                      round(v.get("winrate_pos_pct", float("nan")), 1) if np.isfinite(v.get("winrate_pos_pct", float("nan"))) else "nan",
                      round(v.get("winrate_neg_pct", float("nan")), 1) if np.isfinite(v.get("winrate_neg_pct", float("nan"))) else "nan")

        result[label] = {"tag": tag, "daily": daily, "trade": trd}

    full_t170 = result["T170"]["daily"]["FULL"]
    lbl = label_D(full_t170["pct_beta_of_total"], full_t170["t_alpha"])
    result["LABEL_D_T170"] = lbl
    log.info("############################################################")
    log.info("NHAN D CHO T170: %s (pct_beta_toan_ky=%.1f%%, t_alpha_toan_ky=%.3f)",
              lbl, full_t170["pct_beta_of_total"], full_t170["t_alpha"])
    log.info("############################################################")

    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w") as f:
        json.dump(result, f, indent=2, default=str)
    log.info("wrote %s", OUT_JSON)


if __name__ == "__main__":
    main()
