#!/usr/bin/env python3
"""T_OOS2 data A: Bitstamp BTCUSD 1-min (Kaggle mczielinski/bitcoin-historical-data) -> close ngay UTC 2013-07-01..2017-07-31 (+ xcheck 2017-08-17..2017-12-31 so voi Binance).
KHOA NIEM PHONG: file goc chua du lieu den nay (gom 2020+). Script chi doc cot Timestamp,Close theo chunk; moi dong co ts >= HARD_CAP (2018-01-01 UTC) bi BO NGAY,
khong dem gia, khong tinh gi; chi dem so dong bi bo. Khong ghi dong nao >= HARD_CAP ra dia. File zip/csv goc bi XOA sau khi ghi sha256 (neu --delete-raw).
Quy tac close ngay: Close cua bar co ts lon nhat trong ngay UTC (khong lap phut thieu); ngay khong co bar nao = ngay thieu -> ffill close ngay truoc,
tong ngay thieu > 5 hoac chuoi lien tiep > 3 => DUNG (exit 2, khong ghi CSV sach). xcheck: median |close_Bitstamp/close_Binance-1| > 1 % => DUNG.
Usage: python3 -I t_oos2_data_btc.py RAW(zip|csv) OUTDIR BINANCE_CLEAN_CSV [--delete-raw]"""
import hashlib
import io
import json
import logging
import os
import sys
import zipfile

import numpy as np
import pandas as pd

log = logging.getLogger("toos2btc")


def utc(s):
    return int(pd.Timestamp(s, tz="UTC").timestamp())


WARM_LO = utc("2013-07-01")
MAIN_LAST = "2017-07-31"
MAIN_FIRST = "2013-07-01"
XC_LO, XC_FIRST, XC_LAST = utc("2017-08-17"), "2017-08-17", "2017-12-31"
HARD_CAP = utc("2018-01-01")
MAX_MISSING, MAX_RUN = 5, 3


def open_raw(path):
    if path.endswith(".zip"):
        zf = zipfile.ZipFile(path)
        names = [n for n in zf.namelist() if n.lower().endswith(".csv")]
        assert len(names) == 1, names
        return zf.open(names[0]), names[0]
    return open(path, "rb"), os.path.basename(path)


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def extract(path):
    """Tra DataFrame (ts int giay, close) chi gom ts trong [WARM_LO, HARD_CAP)."""
    fh, inner = open_raw(path)
    keep, n_in, n_drop_cap, n_drop_early, n_nan = [], 0, 0, 0, 0
    cols_checked = False
    for ch in pd.read_csv(fh, usecols=lambda c: c.strip().lower() in ("timestamp", "close"), chunksize=1_000_000):
        ch.columns = [c.strip().lower() for c in ch.columns]
        if not cols_checked:
            assert set(ch.columns) == {"timestamp", "close"}, ch.columns
            cols_checked = True
        ts = ch["timestamp"].to_numpy(float)
        n_in += len(ch)
        ts = np.where(ts > 1e11, ts / 1000.0, ts)             # phong truong hop ms
        m_cap = ts >= HARD_CAP
        n_drop_cap += int(m_cap.sum())
        m_early = ts < WARM_LO
        n_drop_early += int(m_early.sum())
        m = ~(m_cap | m_early)
        sub = pd.DataFrame({"ts": np.floor(ts[m]).astype("int64"), "close": ch["close"].to_numpy(float)[m]})
        n_nan += int(sub["close"].isna().sum())
        keep.append(sub.dropna())
    d = pd.concat(keep, ignore_index=True)
    assert len(d) > 0
    dup = int(d["ts"].duplicated().sum())
    d = d.sort_values("ts", kind="mergesort").drop_duplicates("ts", keep="last").reset_index(drop=True)
    assert int(d["ts"].max()) < HARD_CAP
    info = dict(inner_name=inner, rows_total_scanned=n_in, rows_dropped_ge_hardcap_unseen=n_drop_cap, rows_dropped_before_warmup=n_drop_early,
                rows_kept=len(d), nan_close_dropped=n_nan, dup_ts_dropped=dup)
    return d, info


def daily(d, first, last):
    d = d.copy()
    d["day"] = d["ts"] // 86400
    g = d.groupby("day")
    out = pd.DataFrame({"close": g["close"].last(), "last_ts": g["ts"].max(), "nbars": g["ts"].size()})
    out.index = pd.to_datetime(out.index * 86400, unit="s").date
    full = pd.date_range(first, last, freq="D").date
    out = out[(out.index >= full[0]) & (out.index <= full[-1])]
    missing = sorted(set(full) - set(out.index))
    # chuoi lien tiep
    run, mx = 0, 0
    miss_set = set(missing)
    for dt in full:
        run = run + 1 if dt in miss_set else 0
        mx = max(mx, run)
    return out, full, missing, mx


def main():
    raw, outdir, binance_csv = sys.argv[1:4]
    delete_raw = "--delete-raw" in sys.argv[4:]
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout)
    os.makedirs(outdir, exist_ok=True)
    rep = dict(raw_name=os.path.basename(raw), raw_bytes=os.path.getsize(raw), raw_sha256=sha256_file(raw))
    d, info = extract(raw)
    rep.update(info)
    log.info("extract: %s", info)
    dm, full, missing, mx = daily(d[d["ts"] < utc("2017-08-01")], MAIN_FIRST, MAIN_LAST)
    rep.update(expected_days=len(full), rows_days=len(dm), missing_days=[str(x) for x in missing], max_missing_run=mx)
    log.info("main days expected=%d have=%d missing=%s maxrun=%d", len(full), len(dm), rep["missing_days"], mx)
    if len(missing) > MAX_MISSING or mx > MAX_RUN:
        json.dump(rep, open(os.path.join(outdir, "btc_data_report_STOP.json"), "w"), indent=1)
        log.error("STOP theo prereg: ngay thieu %d (>%d) hoac chuoi %d (>%d)", len(missing), MAX_MISSING, mx, MAX_RUN)
        sys.exit(2)
    clean = dm.reindex(full)
    clean["close"] = clean["close"].ffill()
    assert clean["close"].notna().all() and (clean["close"] > 0).all()
    clean.index.name = "date"
    qa = clean.copy()
    qa["filled"] = clean["nbars"].isna()
    qa["last_gap_min"] = (((pd.to_datetime(pd.Series(clean.index)) - pd.Timestamp("1970-01-01")).dt.total_seconds().to_numpy() + 86399 - clean["last_ts"].to_numpy(float)) / 60.0).round(1)
    clean[["close"]].reset_index().to_csv(os.path.join(outdir, "btc_bitstamp_1d_clean.csv"), index=False)
    qa.reset_index().to_csv(os.path.join(outdir, "btc_bitstamp_1d_qa.csv"), index=False)
    gap = qa["last_gap_min"].dropna()
    ret = clean["close"].pct_change().abs().dropna()
    rep["qa"] = dict(nbars_median=float(qa["nbars"].median()), days_nbars_lt720=int((qa["nbars"] < 720).sum()), days_last_gap_gt360min=int((gap > 360).sum()),
                     last_gap_min_median=float(gap.median()), last_gap_min_p99=float(gap.quantile(0.99)), last_gap_min_max=float(gap.max()),
                     days_abs_ret_gt30pct=int((ret > 0.30).sum()), max_abs_daily_ret=float(ret.max()), close_min=float(clean["close"].min()),
                     close_max=float(clean["close"].max()))
    log.info("qa: %s", rep["qa"])
    # xcheck vs Binance (chi bao cao + dung neu median > 1 %)
    dx, fullx, missx, _ = daily(d[(d["ts"] >= XC_LO) & (d["ts"] < HARD_CAP)], XC_FIRST, XC_LAST)
    bn = pd.read_csv(binance_csv)
    bn["date"] = pd.to_datetime(bn["date"]).dt.date
    bn = bn.set_index("date")["close"]
    cm = dx.join(bn.rename("bn"), how="inner")
    rel = (cm["close"] / cm["bn"] - 1.0).abs()
    rep["xcheck"] = dict(days=len(cm), missing_bitstamp=[str(x) for x in missx], median_abs_rel=float(rel.median()), p95_abs_rel=float(rel.quantile(0.95)),
                         max_abs_rel=float(rel.max()), days_gt3pct=int((rel > 0.03).sum()))
    log.info("xcheck: %s", rep["xcheck"])
    dx.reindex(fullx)[["close"]].ffill().rename_axis("date").reset_index().to_csv(os.path.join(outdir, "btc_bitstamp_1d_xcheck.csv"), index=False)
    # luu minute extract (chi < 2018-01-01) de tai lap
    d.to_csv(os.path.join(outdir, "btc_bitstamp_1m_2013-07_2017-12.csv.gz"), index=False, compression="gzip")
    rep["clean_sha256"] = sha256_file(os.path.join(outdir, "btc_bitstamp_1d_clean.csv"))
    rep["minute_extract_sha256"] = sha256_file(os.path.join(outdir, "btc_bitstamp_1m_2013-07_2017-12.csv.gz"))
    json.dump(rep, open(os.path.join(outdir, "btc_data_report.json"), "w"), indent=1)
    if rep["xcheck"]["median_abs_rel"] > 0.01:
        log.error("STOP theo prereg: xcheck median %.4f > 1 %%", rep["xcheck"]["median_abs_rel"])
        sys.exit(3)
    if delete_raw:
        os.remove(raw)
        log.info("da xoa raw (sha256 %s)", rep["raw_sha256"])
    log.info("DATA_DONE clean_sha256=%s", rep["clean_sha256"])


if __name__ == "__main__":
    main()
