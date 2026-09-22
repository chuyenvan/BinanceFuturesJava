"""BREADTH_GATE_METRICS (TASK B2 Buoc 6, docs/PREREG_BREADTH_GATE_SIM.md) - tinh u1/u3/u4 cho
T170/gate-1.0(T100)/BR/BR0.

TAI DUNG NGUYEN VAN cac ham cua bigdown_struct.py (icc_for, n_eff, maxdd_decomp, label_trades,
build_bd_flags, load_trades_utc, hourly_grid) va c3_rates.py (equity, stats) - KHONG sua 2 file
goc. u2/u5 (khau vi + CAGR per-year) tinh RIENG bang x1_rates.py --appetite current --k 2 (chay o
mot buoc khac, khong lap lai o day).

Chay: cd /home/ubuntu/src/BinanceFuturesJava/research/analysis && python3 breadth_gate_metrics.py
Ghi: out/breadth_gate_metrics.json
"""
import json
import logging
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bigdown_struct as B  # noqa: E402
import c3_rates as C  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("breadth_gate")

TAGS = {
    "T170": "X1_GS_T170_2021",
    "T100": "X1_C3_FULL_2021",
    "BR": "X1_C3_FULL_2021_REGIME_BR",
    "BR0": "X1_C3_FULL_2021_REGIME_BR0",
}
OUT_JSON = os.path.join(HERE, "out", "breadth_gate_metrics.json")


def uw_longest_bd_share(tag):
    """Do dai chuoi UW (ngay am lien tuc) dai nhat toan cua so."""
    s = C.equity(tag)
    uw = s < s.cummax()
    grp = (~uw).cumsum()
    run_len = uw.groupby(grp).sum()
    if run_len.max() == 0:
        return dict(longest_days=0, start=None, end=None)
    best_grp = run_len.idxmax()
    longest = int(run_len.max())
    idx_in_run = s.index[(grp == best_grp) & uw]
    return dict(longest_days=longest, start=str(idx_in_run.min().date()) if len(idx_in_run) else None,
                end=str(idx_in_run.max().date()) if len(idx_in_run) else None)


def uw_by_year(tag):
    """UW (chuoi am lien tuc dai nhat) TRONG TUNG NAM rieng."""
    s = C.equity(tag)
    out = {}
    for y, sy in s.groupby(s.index.year):
        uw = sy < sy.cummax()
        uwmax = int(uw.groupby((~uw).cumsum()).sum().max()) if len(uw) else 0
        out[str(y)] = uwmax
    return out


def main():
    os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
    grid, px = B.hourly_grid()
    flags, extra = B.build_bd_flags(grid, px)
    flag_bd1a = flags["BD1a_5pct24h"]
    log.info("grid n=%d BD1a_frac=%.4f", len(grid), flag_bd1a.mean())

    result = {}
    for name, tag in TAGS.items():
        d = B.load_trades_utc(tag)
        out = {"tag": tag, "n_rows": len(d), "n_episodes": int(d.groupby(["sym", "end"]).ngroups)}
        cohort_day = d.t0.dt.floor("1D")
        icc_row = B.icc_for(d, "roi", cohort_day)
        out["icc_roi_day"] = icc_row
        out["n_eff"] = B.n_eff(d, cohort_day, icc_row["icc"] if icc_row else None)
        enter, exposed = B.label_trades(d, grid, flag_bd1a)
        d = d.copy()
        d["exposed_bd"] = exposed
        d["enter_bd"] = enter
        out["n_exposed_bd"] = int(exposed.sum())
        out["maxdd"] = B.maxdd_decomp(tag, grid, flag_bd1a, d)
        out["uw_longest"] = uw_longest_bd_share(tag)
        out["uw_by_year"] = uw_by_year(tag)
        s = C.stats(tag)
        out["cagr"] = s["cagr"]
        out["maxDD_stats"] = s["maxDD"]
        out["uw_stats"] = s["uw"]
        out["yr"] = s["yr"]
        result[name] = out
        neff = out["n_eff"]["n_eff_total"]
        log.info("%s: n=%d ep=%d icc=%.4f n_eff_total=%.2f maxDD=%.3f%% UW=%d CAGR=%.2f%% "
                  "uw_longest=%s uw_by_year=%s",
                  name, out["n_rows"], out["n_episodes"],
                  icc_row["icc"] if icc_row and icc_row["icc"] is not None else -1.0,
                  neff if neff is not None else -1.0,
                  out["maxDD_stats"], out["uw_stats"], out["cagr"], out["uw_longest"],
                  out["uw_by_year"])

    # u1: breadth BR vs T170
    neff_t170 = result["T170"]["n_eff"]["n_eff_total"]
    neff_br = result["BR"]["n_eff"]["n_eff_total"]
    u1_thr = 1.5 * neff_t170
    u1_pass = bool(neff_br >= u1_thr)

    # u3: BR vs T170 (khong xau hon 25%)
    maxdd_t170 = result["T170"]["maxDD_stats"]
    uw_t170 = result["T170"]["uw_stats"]
    maxdd_br = result["BR"]["maxDD_stats"]
    uw_br = result["BR"]["uw_stats"]
    u3_maxdd_thr = maxdd_t170 * 1.25
    u3_uw_thr = uw_t170 * 1.25
    u3_pass = bool(maxdd_br >= u3_maxdd_thr and uw_br <= u3_uw_thr)

    # u4: UW(BR) < UW(BR0) toan ky VA UW_2025(BR) < UW_2025(BR0)
    uw_br0 = result["BR0"]["uw_stats"]
    uw_br_2025 = result["BR"]["uw_by_year"].get("2025")
    uw_br0_2025 = result["BR0"]["uw_by_year"].get("2025")
    u4_overall_pass = bool(uw_br < uw_br0)
    u4_2025_pass = bool(uw_br_2025 is not None and uw_br0_2025 is not None and uw_br_2025 < uw_br0_2025)
    u4_pass = bool(u4_overall_pass and u4_2025_pass)

    # u5: CAGR nam 2023/2024 BR >= 90% gate-1.0(T100)
    yr_br = result["BR"]["yr"]
    yr_t100 = result["T100"]["yr"]
    u5_2023 = yr_br.get("2023", float("nan")) >= 0.90 * yr_t100.get("2023", float("nan"))
    u5_2024 = yr_br.get("2024", float("nan")) >= 0.90 * yr_t100.get("2024", float("nan"))
    u5_pass = bool(u5_2023 and u5_2024)

    result["gate"] = dict(
        u1_thr=u1_thr, u1_pass=u1_pass, neff_br=neff_br, neff_t170=neff_t170,
        u3_maxdd_thr=u3_maxdd_thr, u3_uw_thr=u3_uw_thr, u3_pass=u3_pass,
        maxdd_br=maxdd_br, uw_br=uw_br,
        u4_pass=u4_pass, u4_overall_pass=u4_overall_pass, u4_2025_pass=u4_2025_pass,
        uw_br0=uw_br0, uw_br_2025=uw_br_2025, uw_br0_2025=uw_br0_2025,
        u5_pass=u5_pass, u5_2023=(yr_br.get("2023"), yr_t100.get("2023")),
        u5_2024=(yr_br.get("2024"), yr_t100.get("2024")),
    )
    with open(OUT_JSON, "w") as f:
        json.dump(result, f, indent=2, default=str)
    log.info("DONE -> %s", OUT_JSON)
    log.info("GATE(BR) u1=%s u3=%s u4=%s (overall=%s 2025=%s) u5=%s",
              u1_pass, u3_pass, u4_pass, u4_overall_pass, u4_2025_pass, u5_pass)


if __name__ == "__main__":
    main()
