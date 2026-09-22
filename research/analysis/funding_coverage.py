#!/usr/bin/env python3
"""BUOC 0 — KIEM DU LIEU FUNDING (Aerospike set funding_data, bin f_data = Snappy(JSON ts->rate)).

Chi DOC. Khong do hieu ung. Xuat: /tmp/funding_factor/coverage.csv + coverage_summary.txt
"""
import json
import os
import sys
import logging
from datetime import datetime, timezone

import numpy as np
import aerospike
import cramjam

NS = os.environ.get("AERO_NS", "test")
SET = "funding_data"
HOST = os.environ.get("AEROSPIKE_HOST", "103.157.218.242")
PORT = int(os.environ.get("AEROSPIKE_PORT", "3222"))
OUT = os.environ.get("FF_OUT", "/tmp/funding_factor")
os.makedirs(OUT, exist_ok=True)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("cov")

UTC = timezone.utc


def main():
    hosts = [("127.0.0.1", PORT)]
    try:
        cli = aerospike.client({"hosts": hosts, "policies": {"timeout": 60000}}).connect()
    except Exception as e:
        log.warning("127.0.0.1 fail (%s) -> thu %s", e, HOST)
        cli = aerospike.client({"hosts": [(HOST, PORT)], "policies": {"timeout": 60000}}).connect()
    log.info("connected; scanning %s.%s ...", NS, SET)

    rows = []
    nrec = 0
    nfail = 0

    def cb(res):
        nonlocal nrec, nfail
        key, meta, record = res
        nrec += 1
        sym = key[2].decode() if isinstance(key[2], bytes) else str(key[2])
        try:
            bd = record.get("f_data")
            if bd is None:
                rows.append((sym, -1, 0, 0, 0.0, 0.0, "f_map/legacy?"))
                return
            d = json.loads(bytes(cramjam.snappy.decompress_raw(bytes(bd))))
            ts = np.array(sorted(int(k) for k in d), dtype=np.int64)
            rr = np.array([float(d[str(t)]) for t in ts], dtype=np.float64)
            if len(ts) == 0:
                rows.append((sym, -1, 0, 0, 0.0, 0.0, "empty"))
                return
            gaps = np.diff(ts) / 3600000.0
            med = float(np.median(gaps)) if len(gaps) else float("nan")
            rows.append((sym, len(ts), int(ts[0]), int(ts[-1]), float(np.mean(rr)), med, "ok"))
        except Exception as e:
            nfail += 1
            rows.append((sym, -2, 0, 0, 0.0, 0.0, "decode_err:%s" % type(e).__name__))

    scan = cli.scan(NS, SET)
    scan.select("f_data")
    scan.foreach(cb)
    cli.close()
    log.info("scan done: nrec=%d nfail=%d", nrec, nfail)

    ok = [r for r in rows if r[6] == "ok"]
    t0 = min(r[2] for r in ok) if ok else 0
    t1 = max(r[3] for r in ok) if ok else 0

    with open(OUT + "/coverage.csv", "w") as f:
        f.write("symbol,n,ts_first_ms,ts_last_ms,rate_mean,median_gap_h,status\n")
        for r in sorted(rows):
            f.write("%s,%d,%d,%d,%.10f,%.4f,%s\n" % r)

    gaps_all = np.array([r[5] for r in ok])
    ns = np.array([r[1] for r in ok])
    lines = []
    lines.append("symbols_total=%d ok=%d fail=%d" % (len(rows), len(ok), nfail))
    lines.append("time_range=%s .. %s" % (
        datetime.fromtimestamp(t0 / 1000, UTC).isoformat(),
        datetime.fromtimestamp(t1 / 1000, UTC).isoformat()))
    lines.append("n_events per symbol: min=%d p10=%.0f median=%.0f p90=%.0f max=%d sum=%d" % (
        ns.min(), np.percentile(ns, 10), np.median(ns), np.percentile(ns, 90), ns.max(), ns.sum()))
    lines.append("median_gap_h across symbols: median=%.4f p10=%.4f p90=%.4f  (=8h => 8.0)" % (
        np.median(gaps_all), np.percentile(gaps_all, 10), np.percentile(gaps_all, 90)))
    # gap distribution on a sample of symbols
    lines.append("status_counts=%s" % {s: sum(1 for r in rows if r[6] == s) for s in set(r[6] for r in rows)})
    txt = "\n".join(lines)
    open(OUT + "/coverage_summary.txt", "w").write(txt + "\n")
    log.info("coverage summary:\n%s", txt)

    # mau vai record (chi cau truc, khong in gia tri nhay cam)
    if ok:
        r = ok[0]
        log.info("sample row: sym=%s n=%d first=%s last=%s mean=%.8f medgap=%.3fh",
                 r[0], r[1], datetime.fromtimestamp(r[2] / 1000, UTC).isoformat(),
                 datetime.fromtimestamp(r[3] / 1000, UTC).isoformat(), r[4], r[5])


if __name__ == "__main__":
    main()
