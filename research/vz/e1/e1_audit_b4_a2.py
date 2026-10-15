"""VZ AUDIT B4 - A2 pass: compare the T9 exploration path with the confirm path.

Numbers only: the exploration event set/net (T9: `e1_events_2024.parquet` built by
`e1_core.build` + `e1_t9_events_net1440.parquet` computed by `e1_t9.measure`) vs
the confirm-engine rebuild (`audit_b4_events_2024.parquet` from
`e1_core.build_year_events`, built by e1_audit_b4_events.py).

Reports, for 2024: event-set symmetric difference, bucket mismatch, max |dtss_reversal|,
max |dnet_1440| / NaN mismatch, and the structural differences (from code reading).
Read-only; writes ~/vz_e1/reports/audit_b4_a2.json.
"""
import json
import os

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

from e1_common import OUT, REPORT, setup_logging, write_json

log = setup_logging("e1_audit_b4_a2", "e1_audit_b4_a2.log")
T9_EVENTS = os.path.join(OUT, "e1_events_2024.parquet")
T9_NET = os.path.join(OUT, "e1_t9_events_net1440.parquet")
CF_EVENTS = os.path.join(OUT, "audit_b4_events_2024.parquet")
TOL = 1e-9


def maxdiff(a, b):
    a = np.asarray(a, np.float64)
    b = np.asarray(b, np.float64)
    fin = np.isfinite(a) & np.isfinite(b)
    nanmis = int((np.isfinite(a) != np.isfinite(b)).sum())
    return {"n": int(fin.sum()), "max_abs_diff": float(np.max(np.abs(a[fin] - b[fin])))
            if fin.any() else None, "nan_mismatch": nanmis}


def main():
    t9 = pq.read_table(T9_EVENTS, columns=["sym", "ts", "taker_sell_share", "tss_5",
                                           "net_240", "net_stress_240"]).to_pandas()
    t9["tss_reversal"] = t9.taker_sell_share - t9.tss_5
    t9["ts"] = t9.ts.astype(np.int64)
    net = pq.read_table(T9_NET, columns=["sym", "ts", "net_1440", "net_stress_1440"]).to_pandas()
    net["ts"] = net.ts.astype(np.int64)
    cf = pd.read_parquet(CF_EVENTS)
    cf["ts"] = cf.ts.astype(np.int64)

    k9 = set(zip(t9.sym.astype(str), t9.ts))
    kc = set(zip(cf.sym.astype(str), cf.ts))
    m = cf.merge(t9[["sym", "ts", "tss_reversal", "net_240", "net_stress_240"]],
                 on=["sym", "ts"], how="inner", suffixes=("_cf", "_t9"))
    mn = cf.merge(net, on=["sym", "ts"], how="inner", suffixes=("_cf", "_t9"))
    res = {
        "n_t9_events": int(len(t9)), "n_confirm_engine_events": int(len(cf)),
        "n_common": int(len(m)),
        "only_in_t9": int(len(k9 - kc)), "only_in_confirm": int(len(kc - k9)),
        "event_set_identical": bool(k9 == kc),
        "tss_reversal": maxdiff(m.tss_reversal_cf, m.tss_reversal_t9),
        "net_240": maxdiff(m.net_240_cf, m.net_240_t9),
        "net_stress_240": maxdiff(m.net_stress_240_cf, m.net_stress_240_t9),
        "net_1440": maxdiff(mn.net_1440_cf, mn.net_1440_t9),
        "net_stress_1440": maxdiff(mn.net_stress_1440_cf, mn.net_stress_1440_t9),
    }
    # bucket is stored in the T9 event parquet; compare it on the common rows
    t9b = pq.read_table(T9_EVENTS, columns=["sym", "ts", "close", "open", "bucket"]).to_pandas()
    t9b["ts"] = t9b.ts.astype(np.int64)
    mm = cf.merge(t9b[["sym", "ts", "bucket"]], on=["sym", "ts"], how="inner",
                  suffixes=("_cf", "_t9"))
    res["bucket_mismatch"] = int((mm.bucket_cf.to_numpy() != mm.bucket_t9.to_numpy()).sum())
    res["A2_tolerance"] = TOL
    res["A2_numeric_pass"] = bool(
        res["event_set_identical"] and res["bucket_mismatch"] == 0
        and (res["tss_reversal"]["max_abs_diff"] or 0) <= TOL
        and res["tss_reversal"]["nan_mismatch"] == 0
        and (res["net_1440"]["max_abs_diff"] or 0) <= TOL
        and res["net_1440"]["nan_mismatch"] == 0)

    res["structural_differences"] = [
        "lookback cho feature: e1_core.build LOOKBACK_MS=7 ngay vs build_year_events "
        "lookback_days=30 (chi anh huong vung dem cua rolling; tss_5 chi lui 1 nen)",
        "e1_core.month_events (2024) merge them basis1m + metrics5m + funding va ghi "
        "panel/DOI/volz/prem_z7; month_events_year (xac nhan) CHI doc kline1m, cac cot "
        "basis = NaN (B4 chi dung tss_reversal tu kline)",
        "gross 60/240: cung _asof + dieu kien ts_a[jj]==ts+h; gross_1440 chi co o "
        "month_events_year (2024 goc khong tinh 1440 trong builder)",
        "net_1440 cua T9 duoc tinh NGOAI builder bang reader rieng (e1_t9.frame_for: "
        "pq.read_table thang tren parquet thang, KHONG loc anomalies.csv, float64) va "
        "ghep left-join (sym,ts); runner xac nhan tinh gross_1440 TRONG builder qua "
        "SymIndex (co loc anomalies.csv)",
        "bucket: T9 lay cot bucket co san trong e1_events_2024.parquet; runner tinh lai "
        "bucket_of(close,open) tren cung hang (cung ham, float32)",
        "thu tu/sap xep: ca hai sort (ts,sym) truoc khi tra parquet; bootstrap theo NGAY "
        "UTC nen thu tu trong ngay khong anh huong",
        "cau hinh bien the: T9 doc hi/lo tu configs/t9_config.json (B4 5/1); runner lay "
        "tu e1_t3.VAR_BY_NAME (V2 5/1) va doi chieu edges voi configs/t3_thresholds.json",
        "pham vi ngay: T9 ghep net_1440 bang left-join (giu ca su kien thieu 24h, net=NaN); "
        "runner loc np.isfinite(net_1440) truoc khi danh gia (cung tap huu han)",
    ]
    write_json(os.path.join(REPORT, "audit_b4_a2.json"), res)
    log.info("A2 pass=%s maxdiff_tss=%s maxdiff_net1440=%s", res["A2_numeric_pass"],
             res["tss_reversal"]["max_abs_diff"], res["net_1440"]["max_abs_diff"])
    print(json.dumps(res, indent=1, default=str))


if __name__ == "__main__":
    main()
