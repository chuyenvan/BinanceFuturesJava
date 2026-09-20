"""PACING_TASKB_METRICS (TASK B) - tinh t1/t3/t4 cho T170/T100/P0/P3.

TAI DUNG NGUYEN VAN cac ham cua bigdown_struct.py (icc_for, n_eff, maxdd_decomp, label_trades,
build_bd_flags, load_trades_utc, hourly_grid) - KHONG sua bigdown_struct.py. t2 (khau vi + CAGR
CI) tinh rieng bang x1_rates.py (research/analysis/x1_rates.py --appetite current --k 2).

Chay: cd /home/ubuntu/src/BinanceFuturesJava/research/analysis && python3 pacing_taskb_metrics.py
Ghi: out/pacing_taskb_metrics.json
"""
import json
import logging
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bigdown_struct as B  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("pacing_taskb")

TAGS = {
    "T170": "X1_GS_T170_2021",
    "T100": "X1_C3_FULL_2021",
    "P0": "X1_C3_FULL_2021_PACING_P0",
    "P3": "X1_C3_FULL_2021_PACING_P3",
}
OUT_JSON = os.path.join(HERE, "out", "pacing_taskb_metrics.json")


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
        result[name] = out
        neff = out["n_eff"]["n_eff_total"]
        bdshare = out["maxdd"]["bd_share_of_maxdd_depth_pct"]
        log.info("%s: n=%d ep=%d icc=%.4f n_eff_total=%.2f maxDD=%.3f%% bd_share=%s%%",
                  name, out["n_rows"], out["n_episodes"],
                  icc_row["icc"] if icc_row and icc_row["icc"] is not None else -1.0,
                  neff if neff is not None else -1.0,
                  out["maxdd"]["maxDD_pct"], ("%.2f" % bdshare) if bdshare is not None else "NA")

    with open(OUT_JSON, "w") as f:
        json.dump(result, f, indent=2, default=str)
    log.info("wrote %s", OUT_JSON)


if __name__ == "__main__":
    main()
