"""VZ AUDIT B4 - data pass (B1/B2-unit/B3): per-month source checks.

Downloads (idempotent, into ~/vz_e1/raw) every kline month 2021-12..2025-12 and
records, per month:
  B3  column order + index of taker_buy_volume / taker_buy_quote (header check)
  B2  ts unit (ms vs us) inferred from the ts magnitude + expected ms for the month
  B1  distribution of taker_buy_quote/quote_volume (median, p1, p99), plus the
      fraction of rows with taker_buy_quote == 0 / == quote_volume, and qv == 0
Also reports n_rows / n_syms per month.

Read-only apart from the lake download cache. Writes
~/vz_e1/reports/audit_b4_data.json. No year outside 2021-12..2025-12 is touched.
"""
import json
import os
import time

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

import e1_data
from e1_common import REPORT, setup_logging, write_json

log = setup_logging("e1_audit_b4_data", "e1_audit_b4_data.log")

MONTHS = ["2021-12"] + ["%04d-%02d" % (y, m) for y in (2022, 2023, 2024, 2025)
                        for m in range(1, 13)]
# expected start-of-month ms (UTC) so a ms/us mix is obvious
def month_ms(month):
    y, m = int(month[:4]), int(month[5:7])
    return int(pd.Timestamp(year=y, month=m, day=1, tz="UTC").timestamp() * 1000)


def scan_month(month):
    path = e1_data.month_path(month, "kline", fetch=True)
    pf = pq.ParquetFile(path)
    names = pf.schema_arrow.names
    rec = {"month": month, "file": os.path.basename(path), "size_mb": round(os.path.getsize(path) / 1e6, 1),
           "n_cols": len(names), "columns": names,
           "taker_buy_volume_idx": names.index("taker_buy_volume") if "taker_buy_volume" in names else None,
           "taker_buy_quote_idx": names.index("taker_buy_quote") if "taker_buy_quote" in names else None,
           "has_header": True, "n_rows": pf.metadata.num_rows, "n_rowgroups": pf.metadata.num_row_groups}
    t = pq.read_table(path, columns=["ts", "sym", "quote_volume", "taker_buy_quote"])
    ts = t.column("ts").to_numpy()
    rec["ts_min"] = int(ts.min()); rec["ts_max"] = int(ts.max())
    exp = month_ms(month)
    # ms timestamps are ~1e12, us ~1e15
    unit = "us" if rec["ts_min"] > 1e14 else "ms"
    rec["ts_unit"] = unit
    rec["ts_start_matches_month"] = bool(
        (abs(rec["ts_min"] - exp) < 86_400_000) if unit == "ms"
        else (abs(rec["ts_min"] - exp * 1000) < 86_400_000 * 1000))
    qv = t.column("quote_volume").to_numpy().astype(np.float64)
    tbq = t.column("taker_buy_quote").to_numpy().astype(np.float64)
    syms = t.column("sym").to_pandas()
    rec["n_syms"] = int(syms.nunique())
    ok = qv > 0
    ratio = np.full(len(qv), np.nan)
    ratio[ok] = tbq[ok] / qv[ok]
    fin = np.isfinite(ratio)
    rec["n_finite_ratio"] = int(fin.sum())
    if fin.any():
        r = ratio[fin]
        rec["ratio_median"] = float(np.median(r))
        rec["ratio_p01"] = float(np.percentile(r, 1))
        rec["ratio_p99"] = float(np.percentile(r, 99))
        rec["frac_taker_buy_quote_zero"] = float((r == 0).mean())
        rec["frac_equal_quote_volume"] = float((r == 1).mean())
    rec["frac_quote_volume_zero"] = float((~ok).mean())
    return rec


def main():
    out = {"months": [], "n_months": len(MONTHS)}
    done = {}
    prev = os.path.join(REPORT, "audit_b4_data.json")
    if os.path.exists(prev):
        try:
            done = {r["month"]: r for r in json.load(open(prev)).get("months", [])}
            log.info("resume: %d month(s) already scanned", len(done))
        except Exception as e:  # noqa: BLE001
            log.warning("resume json unreadable: %s", e)
    t0 = time.time()
    for m in MONTHS:
        if m in done:
            out["months"].append(done[m])
            continue
        rec = scan_month(m)
        out["months"].append(rec)
        log.info("B1/B2/B3 %s unit=%s cols=%d tbq_idx=%s rows=%d med=%.4f p01=%.4f p99=%.4f fz=%.4f fe=%.4f qv0=%.5f (%.0fs)",
                 m, rec["ts_unit"], rec["n_cols"], rec["taker_buy_quote_idx"], rec["n_rows"],
                 rec.get("ratio_median", float("nan")), rec.get("ratio_p01", float("nan")),
                 rec.get("ratio_p99", float("nan")), rec.get("frac_taker_buy_quote_zero", float("nan")),
                 rec.get("frac_equal_quote_volume", float("nan")), rec["frac_quote_volume_zero"],
                 time.time() - t0)
        out["months"].sort(key=lambda r: r["month"])
        write_json(os.path.join(REPORT, "audit_b4_data.json"), out)
    out["months"].sort(key=lambda r: r["month"])
    write_json(os.path.join(REPORT, "audit_b4_data.json"), out)
    print(json.dumps({"n_months": len(out["months"]), "months": [m["month"] for m in out["months"]]}))
    return out


if __name__ == "__main__":
    main()
