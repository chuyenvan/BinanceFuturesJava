"""DD_THROTTLE_METRICS (TASK B2 Buoc 3) - tinh u1/u3/u4 cho T170/gate-1.0(T100)/DT/R0.

TAI DUNG NGUYEN VAN cac ham cua bigdown_struct.py (icc_for, n_eff, maxdd_decomp, label_trades,
build_bd_flags, load_trades_utc, hourly_grid) va c3_rates.py (equity, stats) - KHONG sua 2 file
goc do. u2 (khau vi + CAGR CI theo nam) tinh rieng bang x1_rates.py --appetite current --k <k>
va cagr_ci_t170.py --k <k> (xem docs/result/RESULT_DD_THROTTLE.md).

GHI CHU QUAN TRONG: theo cong thuc noi suy log-tuyen tinh khoa trong docs/prereg/PREREG_DD_THROTTLE.md
muc 3.2 (tai su dung nguyen ven tu docs/prereg/PREREG_REGIME_GATE.md muc 3), voi n_total(DT) do duoc
tu sim thuc te, g0 tinh ra lam tron 2 chu so = 1.00 - TRUNG voi gate-1.0/T100 (SIM_GATE_DYN_SCALE
mac dinh = 1.00 khong dat). Ly do: DT la co che SIZE-only (khong doi tap lenh duoc admit), nen
n_total(DT) ~ n_total(gate-1.0) mot cach TU NHIEN (2568 vs 2559, lech 0.35%) - hoan toan khac
TASK B2 Buoc 2 (R la co che ADMISSION-thay-doi-tap-lenh nen n_total(R) lech xa gate-1.0). Vi vay
R0 (doi chung "giam deu khop so lenh voi DT") KHONG can chay sim rieng - no CHINH LA gate-1.0/T100
da co san. Bien TAGS duoi day phan anh dieu nay: R0 tro thang toi tag T100.

Chay: cd /home/ubuntu/src/BinanceFuturesJava/research/analysis && python3 dd_throttle_metrics.py
Ghi: out/dd_throttle_metrics.json
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
log = logging.getLogger("dd_throttle")

TAGS = {
    "T170": "X1_GS_T170_2021",
    "T100": "X1_C3_FULL_2021",
    "DT": "X1_C3_FULL_2021_DT",
    "R0": "X1_C3_FULL_2021",   # = T100 (xem GHI CHU o dau file - g0 noi suy ra 1.00)
}
OUT_JSON = os.path.join(HERE, "out", "dd_throttle_metrics.json")


def uw_longest(tag):
    """Do dai chuoi UW (ngay am lien tuc) dai nhat + ngay bat dau/ket thuc."""
    s = C.equity(tag)
    uw = s < s.cummax()
    grp = (~uw).cumsum()
    run_len = uw.groupby(grp).sum()
    best_grp = run_len.idxmax()
    longest = int(run_len.max())
    idx_in_run = s.index[(grp == best_grp) & uw]
    return dict(longest_days=longest, start=str(idx_in_run.min().date()) if len(idx_in_run) else None,
                end=str(idx_in_run.max().date()) if len(idx_in_run) else None)


def main():
    os.makedirs(os.path.join(HERE, "out"), exist_ok=True)
    grid, px = B.hourly_grid()
    flags, extra = B.build_bd_flags(grid, px)
    flag_bd1a = flags["BD1a_5pct24h"]
    log.info("grid n=%d BD1a_frac=%.4f", len(grid), flag_bd1a.mean())

    result = {}
    done_tags = {}
    for name, tag in TAGS.items():
        if tag in done_tags:
            result[name] = done_tags[tag]
            log.info("%s: (alias cua tag da tinh %s = %s)", name, done_tags[tag]["tag"], tag)
            continue
        d = B.load_trades_utc(tag)
        out = {"tag": tag, "n_rows": len(d), "n_episodes": int(d.groupby(["sym", "end"]).ngroups)}
        cohort_day = d.t0.dt.floor("1D")
        icc_row = B.icc_for(d, "roi", cohort_day)
        out["icc_roi_day"] = icc_row
        out["n_eff"] = B.n_eff(d, cohort_day, icc_row["icc"] if icc_row else None)
        enter, exposed = B.label_trades(d, grid, flag_bd1a)
        d2 = d.copy()
        d2["exposed_bd"] = exposed
        d2["enter_bd"] = enter
        out["n_exposed_bd"] = int(exposed.sum())
        out["maxdd"] = B.maxdd_decomp(tag, grid, flag_bd1a, d2)
        out["uw_longest"] = uw_longest(tag)
        s = C.stats(tag)
        out["cagr"] = s["cagr"]
        out["maxDD_stats"] = s["maxDD"]
        out["uw_stats"] = s["uw"]
        out["yr"] = s["yr"]
        result[name] = out
        done_tags[tag] = out
        neff = out["n_eff"]["n_eff_total"]
        log.info("%s(tag=%s): n=%d ep=%d icc=%.4f n_eff_total=%.2f maxDD=%.3f%% UW=%d(stats)/%s(longest) "
                  "CAGR=%.2f%%",
                  name, tag, out["n_rows"], out["n_episodes"],
                  icc_row["icc"] if icc_row and icc_row["icc"] is not None else -1.0,
                  neff if neff is not None else -1.0,
                  out["maxDD_stats"], out["uw_stats"], out["uw_longest"]["longest_days"],
                  out["cagr"])

    # u1: n_eff_total(DT) >= 1.5 * n_eff_total(T170)
    neff_t170 = result["T170"]["n_eff"]["n_eff_total"]
    neff_dt = result["DT"]["n_eff"]["n_eff_total"]
    u1_thr = 1.5 * neff_t170
    u1_pass = bool(neff_dt >= u1_thr)

    # u3: maxDD(DT) >= -14.8% (i.e. khong te hon -14.8) VA UW(DT) <= 115
    maxdd_t170 = result["T170"]["maxDD_stats"]
    uw_t170 = result["T170"]["uw_stats"]
    maxdd_dt = result["DT"]["maxDD_stats"]
    uw_dt = result["DT"]["uw_stats"]
    u3_maxdd_thr = -14.8
    u3_uw_thr = 115
    u3_pass = bool(maxdd_dt >= u3_maxdd_thr and uw_dt <= u3_uw_thr)

    # u4: UW(DT) < UW(R0) VA UW(DT) < UW(gate-1.0 khong throttle) - R0 == T100 nen 2 dieu kien
    #     TRUNG NHAU trong vong nay (xem GHI CHU dau file).
    uw_r0 = result["R0"]["uw_stats"]
    uw_t100 = result["T100"]["uw_stats"]
    longest_dt = result["DT"]["uw_longest"]["longest_days"]
    longest_r0 = result["R0"]["uw_longest"]["longest_days"]
    u4_pass = bool(uw_dt < uw_r0 and uw_dt < uw_t100)
    u4_note = "R0 == T100 trong vong nay (g0 noi suy = 1.00) nen u4 thuc chat la 1 dieu kien (UW(DT) < UW(T100))"

    result["gate"] = dict(
        u1_thr=u1_thr, u1_pass=u1_pass, neff_dt=neff_dt, neff_t170=neff_t170,
        u3_maxdd_thr=u3_maxdd_thr, u3_uw_thr=u3_uw_thr, u3_pass=u3_pass,
        maxdd_dt=maxdd_dt, uw_dt=uw_dt,
        u4_pass=u4_pass, uw_r0=uw_r0, uw_t100=uw_t100,
        longest_dt=longest_dt, longest_r0=longest_r0, u4_note=u4_note,
        du_bao_xac_nhan=bool(uw_dt >= uw_t100),
    )
    with open(OUT_JSON, "w") as f:
        json.dump(result, f, indent=2, default=str)
    log.info("DONE -> %s", OUT_JSON)
    log.info("GATE u1=%s u3=%s u4=%s | du_bao_MASTER_xac_nhan(UW(DT)>=UW(T100))=%s",
              u1_pass, u3_pass, u4_pass, result["gate"]["du_bao_xac_nhan"])


if __name__ == "__main__":
    main()
