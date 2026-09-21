"""REGIME_UPDOWN_METRICS (TASK B2 Buoc 4) - tinh u1/u3/u4 cho T170/gate-1.0(T100)/R/RA12/RA14.

TAI DUNG NGUYEN VAN cac ham cua bigdown_struct.py (icc_for, n_eff, maxdd_decomp, label_trades,
build_bd_flags, load_trades_utc, hourly_grid) va c3_rates.py (equity, stats) - KHONG sua 2 file
goc. u2/u5 (khau vi + CAGR per-year) tinh RIENG bang x1_rates.py --appetite current --k <k>
(bang RATE THEO NAM + RANG BUOC CUNG THEO NAM), chay o mot buoc khac (khong lap lai o day).

Chay: cd /home/ubuntu/src/BinanceFuturesJava/research/analysis && python3 regime_updown_metrics.py
Ghi: out/regime_updown_metrics.json
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
log = logging.getLogger("regime_updown")

TAGS = {
    "T170": "X1_GS_T170_2021",
    "T100": "X1_C3_FULL_2021",
    "R": "X1_C3_FULL_2021_REGIME_R",
    "RA12": "X1_C3_FULL_2021_REGIME_RA12",
    "RA14": "X1_C3_FULL_2021_REGIME_RA14",
}
OUT_JSON = os.path.join(HERE, "out", "regime_updown_metrics.json")


def uw_longest_bd_share(tag):
    """Do dai chuoi UW (ngay am lien tuc) dai nhat toan cua so - dung cho u4."""
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
    """UW (chuoi am lien tuc dai nhat) TRONG TUNG NAM rieng - dung cho u4 (2022, 2025)."""
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

    # u1: breadth RA12 vs T170
    neff_t170 = result["T170"]["n_eff"]["n_eff_total"]
    neff_ra12 = result["RA12"]["n_eff"]["n_eff_total"]
    u1_thr = 1.5 * neff_t170
    u1_pass = bool(neff_ra12 >= u1_thr)
    # u3: RA12 vs T170 (khong xau hon 25%)
    maxdd_t170 = result["T170"]["maxDD_stats"]
    uw_t170 = result["T170"]["uw_stats"]
    maxdd_ra12 = result["RA12"]["maxDD_stats"]
    uw_ra12 = result["RA12"]["uw_stats"]
    u3_maxdd_thr = maxdd_t170 * 1.25
    u3_uw_thr = uw_t170 * 1.25
    u3_pass = bool(maxdd_ra12 >= u3_maxdd_thr and uw_ra12 <= u3_uw_thr)
    # u4: RA12 vs R nam 2025 (up-gate chat hon cuu duoc 2025), va RA12 vs T170 nam 2022 (giu bear)
    uw_ra12_2025 = result["RA12"]["uw_by_year"].get("2025")
    uw_r_2025 = result["R"]["uw_by_year"].get("2025")
    uw_ra12_2022 = result["RA12"]["uw_by_year"].get("2022")
    uw_t170_2022 = result["T170"]["uw_by_year"].get("2022")
    u4_2025_pass = bool(uw_ra12_2025 is not None and uw_r_2025 is not None and uw_ra12_2025 < uw_r_2025)
    if uw_t170_2022 and uw_t170_2022 > 0:
        rel_diff_2022 = abs(uw_ra12_2022 - uw_t170_2022) / uw_t170_2022
    else:
        rel_diff_2022 = None
    u4_2022_pass = bool(rel_diff_2022 is not None and rel_diff_2022 <= 0.05)
    u4_pass = bool(u4_2025_pass and u4_2022_pass)
    # u5: CAGR nam 2023/2024 RA12 >= 90% gate-1.0(T100)
    yr_ra12 = result["RA12"]["yr"]
    yr_t100 = result["T100"]["yr"]
    u5_2023 = yr_ra12.get("2023", float("nan")) >= 0.90 * yr_t100.get("2023", float("nan"))
    u5_2024 = yr_ra12.get("2024", float("nan")) >= 0.90 * yr_t100.get("2024", float("nan"))
    u5_pass = bool(u5_2023 and u5_2024)

    result["gate"] = dict(
        u1_thr=u1_thr, u1_pass=u1_pass, neff_ra12=neff_ra12, neff_t170=neff_t170,
        u3_maxdd_thr=u3_maxdd_thr, u3_uw_thr=u3_uw_thr, u3_pass=u3_pass,
        maxdd_ra12=maxdd_ra12, uw_ra12=uw_ra12,
        u4_pass=u4_pass, u4_2025_pass=u4_2025_pass, u4_2022_pass=u4_2022_pass,
        uw_ra12_2025=uw_ra12_2025, uw_r_2025=uw_r_2025,
        uw_ra12_2022=uw_ra12_2022, uw_t170_2022=uw_t170_2022, rel_diff_2022=rel_diff_2022,
        u5_pass=u5_pass, u5_2023=(yr_ra12.get("2023"), yr_t100.get("2023")),
        u5_2024=(yr_ra12.get("2024"), yr_t100.get("2024")),
    )
    with open(OUT_JSON, "w") as f:
        json.dump(result, f, indent=2, default=str)
    log.info("DONE -> %s", OUT_JSON)
    log.info("GATE(RA12) u1=%s u3=%s u4=%s (2025=%s 2022=%s) u5=%s",
              u1_pass, u3_pass, u4_pass, u4_2025_pass, u4_2022_pass, u5_pass)


if __name__ == "__main__":
    main()
