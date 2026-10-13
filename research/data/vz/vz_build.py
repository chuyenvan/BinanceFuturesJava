"""B3 - parse Vision zips -> monthly parquet (zstd 6, one row group per symbol).

Usage: vz_build.py <ds> <YYYY-MM>   ds in {kline1m,basis1m,metrics5m,funding}
"""
import argparse
import glob
import json
import os
import sys
import time
import zipfile

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from vz_common import (
    DS_SOURCES,
    OUT_DIR,
    STATE_DIR,
    TMP_DIR,
    open_gz_csv_writer,
    setup_logging,
    sha256_file,
    TYPES,
)

log = setup_logging("build")

SYM_DICT = pa.dictionary(pa.int32(), pa.string())

SCHEMAS = {
    "kline1m": pa.schema([
        ("ts", pa.int64()), ("sym", SYM_DICT),
        ("open", pa.float64()), ("high", pa.float64()), ("low", pa.float64()),
        ("close", pa.float64()), ("volume", pa.float64()), ("quote_volume", pa.float64()),
        ("n_trades", pa.int32()), ("taker_buy_base", pa.float64()),
        ("taker_buy_quote", pa.float64()),
    ]),
    "basis1m": pa.schema([
        ("ts", pa.int64()), ("sym", SYM_DICT),
        ("prem_open", pa.float64()), ("prem_high", pa.float64()),
        ("prem_low", pa.float64()), ("prem_close", pa.float64()),
        ("mark_close", pa.float64()), ("index_close", pa.float64()),
    ]),
    "metrics5m": pa.schema([
        ("ts", pa.int64()), ("sym", SYM_DICT),
        ("oi", pa.float64()), ("oi_value", pa.float64()),
        ("toptrader_ls_cnt", pa.float64()), ("toptrader_ls_sum", pa.float64()),
        ("ls_cnt", pa.float64()), ("taker_ls_vol", pa.float64()),
    ]),
    "funding": pa.schema([
        ("ts", pa.int64()), ("sym", SYM_DICT),
        ("interval_h", pa.int16()), ("rate", pa.float64()),
    ]),
}

KLINE_POS = ["open_time", "open", "high", "low", "close", "volume", "close_time",
             "quote_volume", "count", "taker_buy_volume", "taker_buy_quote_volume", "ignore"]
METRICS_POS = ["create_time", "symbol", "sum_open_interest", "sum_open_interest_value",
               "count_toptrader_long_short_ratio", "sum_toptrader_long_short_ratio",
               "count_long_short_ratio", "sum_taker_long_short_vol_ratio"]
FUNDING_POS = ["calc_time", "funding_interval_hours", "last_funding_rate"]

COUNT = {"micro_fixed": 0, "dupes": 0, "files": 0, "rows_in": 0}


def read_csv_zip(path, pos, has_header=None):
    with zipfile.ZipFile(path) as z:
        member = z.namelist()[0]
        with z.open(member) as fh:
            df = pd.read_csv(fh, header=None, dtype=str, keep_default_na=False)
    if has_header is None:
        try:
            float(df.iloc[0, 0])
            has_header = False
        except (ValueError, IndexError):
            has_header = True
    if has_header:
        df = df.iloc[1:].reset_index(drop=True)
    ncol = len(pos)
    if df.shape[1] < ncol:
        pos = pos[: df.shape[1]]
    df = df.iloc[:, : len(pos)]
    df.columns = pos
    df = df.astype(float, errors="ignore")
    return df


def fix_ts(series):
    s = pd.to_numeric(series, errors="coerce")
    if (s > 1e14).any():
        COUNT["micro_fixed"] += 1
        s = s / 1000.0
    return s.round().astype("int64")


def files_by_sym(src_types, ym):
    out = {}
    for st in src_types:
        d = os.path.join(TMP_DIR, st, ym)
        for p in sorted(glob.glob(os.path.join(d, "*.zip"))):
            sym = os.path.basename(p).split("-")[0]
            out.setdefault(sym, {}).setdefault(st, []).append(p)
    return out


def build_kline(sym, paths):
    df = read_csv_zip(paths["kline1m"][0], KLINE_POS)
    COUNT["files"] += 1
    COUNT["rows_in"] += len(df)
    out = pd.DataFrame({
        "ts": fix_ts(df["open_time"]),
        "sym": sym,
        "open": pd.to_numeric(df["open"]), "high": pd.to_numeric(df["high"]),
        "low": pd.to_numeric(df["low"]), "close": pd.to_numeric(df["close"]),
        "volume": pd.to_numeric(df["volume"]), "quote_volume": pd.to_numeric(df["quote_volume"]),
        "n_trades": pd.to_numeric(df["count"]).fillna(0).astype("int32"),
        "taker_buy_base": pd.to_numeric(df["taker_buy_volume"]),
        "taker_buy_quote": pd.to_numeric(df["taker_buy_quote_volume"]),
    })
    return out


def _px(path, pos):
    df = read_csv_zip(path, pos)
    COUNT["files"] += 1
    COUNT["rows_in"] += len(df)
    return df


def build_basis(sym, paths):
    prem = _px(paths["premiumIndex1m"][0], KLINE_POS)
    mark = _px(paths["markPrice1m"][0], KLINE_POS)
    idx = _px(paths["indexPrice1m"][0], KLINE_POS)
    p = pd.DataFrame({"ts": fix_ts(prem["open_time"]), "prem_open": pd.to_numeric(prem["open"]),
                      "prem_high": pd.to_numeric(prem["high"]), "prem_low": pd.to_numeric(prem["low"]),
                      "prem_close": pd.to_numeric(prem["close"])})
    m = pd.DataFrame({"ts": fix_ts(mark["open_time"]), "mark_close": pd.to_numeric(mark["close"])})
    i = pd.DataFrame({"ts": fix_ts(idx["open_time"]), "index_close": pd.to_numeric(idx["close"])})
    out = p.merge(m, on="ts", how="outer").merge(i, on="ts", how="outer")
    out["sym"] = sym
    return out


def build_metrics(sym, paths):
    frs = []
    for p in sorted(paths["metrics"]):
        df = _px(p, METRICS_POS)
        frs.append(df)
    df = pd.concat(frs, ignore_index=True)
    ts = pd.to_datetime(df["create_time"], utc=True, errors="coerce")
    out = pd.DataFrame({
        "ts": (ts.astype("int64") // 10**6),
        "sym": sym,
        "oi": pd.to_numeric(df["sum_open_interest"], errors="coerce"),
        "oi_value": pd.to_numeric(df["sum_open_interest_value"], errors="coerce"),
        "toptrader_ls_cnt": pd.to_numeric(df["count_toptrader_long_short_ratio"], errors="coerce"),
        "toptrader_ls_sum": pd.to_numeric(df["sum_toptrader_long_short_ratio"], errors="coerce"),
        "ls_cnt": pd.to_numeric(df["count_long_short_ratio"], errors="coerce"),
        "taker_ls_vol": pd.to_numeric(df["sum_taker_long_short_vol_ratio"], errors="coerce"),
    })
    return out


def build_funding(sym, paths):
    df = _px(paths["fundingRate"][0], FUNDING_POS)
    out = pd.DataFrame({
        "ts": fix_ts(df["calc_time"]),
        "sym": sym,
        "interval_h": pd.to_numeric(df["funding_interval_hours"], errors="coerce").fillna(8).astype("int16"),
        "rate": pd.to_numeric(df["last_funding_rate"], errors="coerce"),
    })
    return out


BUILDERS = {"kline1m": build_kline, "basis1m": build_basis,
            "metrics5m": build_metrics, "funding": build_funding}
NEEDED = {"kline1m": ["kline1m"], "basis1m": ["premiumIndex1m", "markPrice1m", "indexPrice1m"],
          "metrics5m": ["metrics"], "funding": ["fundingRate"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("ds")
    ap.add_argument("month")
    args = ap.parse_args()
    ds, ym = args.ds, args.month
    year = ym[:4]
    schema = SCHEMAS[ds]
    builder = BUILDERS[ds]
    paths = files_by_sym(NEEDED[ds], ym)
    syms = sorted(s for s, d in paths.items() if all(k in d for k in NEEDED[ds]))
    log.info("ds=%s month=%s symbols=%d", ds, ym, len(syms))
    outdir = os.path.join(OUT_DIR, ds, year)
    os.makedirs(outdir, exist_ok=True)
    outpath = os.path.join(outdir, ym + ".parquet")

    t0 = time.time()
    writer = pq.ParquetWriter(outpath, schema, compression="zstd", compression_level=6)
    rows_out = 0
    per_sym = []
    for i, sym in enumerate(syms, 1):
        df = builder(sym, paths[sym])
        df = df.dropna(subset=["ts"]).copy()
        df["ts"] = df["ts"].astype("int64")
        before = len(df)
        df = df.sort_values("ts", kind="mergesort").drop_duplicates("ts", keep="last")
        COUNT["dupes"] += before - len(df)
        df = df[list(schema.names)]
        table = pa.Table.from_pandas(df, schema=schema, preserve_index=False)
        writer.write_table(table)
        rows_out += len(df)
        per_sym.append((sym, len(df)))
        if i % 100 == 0:
            log.info("ds=%s %d/%d symbols rows=%d", ds, i, len(syms), rows_out)
    writer.close()
    dur = time.time() - t0
    sha = sha256_file(outpath)
    size = os.path.getsize(outpath)

    # entry manifest (sym,rows) for vz-symbols / registry
    mpath = os.path.join(OUT_DIR, ds, year, ym + ".symbols.csv.gz")
    with open_gz_csv_writer(mpath) as fh:
        fh.write("sym,rows\n")
        for s, n in per_sym:
            fh.write("%s,%d\n" % (s, n))

    res = {"ds": ds, "month": ym, "n_sym": len(syms), "rows": rows_out,
           "dupes_dropped": COUNT["dupes"], "files": COUNT["files"],
           "rows_in": COUNT["rows_in"], "micro_fixed_files": COUNT["micro_fixed"],
           "parquet_bytes": size, "sha256": sha, "seconds": round(dur, 1)}
    st_path = os.path.join(STATE_DIR, "build", ds, ym + ".json")
    os.makedirs(os.path.dirname(st_path), exist_ok=True)
    with open(st_path, "w") as fh:
        json.dump(res, fh, indent=1)
    log.info("ds=%s month=%s DONE rows=%d sym=%d bytes=%d dup=%d micro=%d sz=%.1fs sha=%s",
             ds, ym, rows_out, len(syms), size, COUNT["dupes"], COUNT["micro_fixed"], dur, sha[:12])
    if not os.environ.get("VZ_KEEP_ZIP"):
        removed = 0
        for st in NEEDED[ds]:
            for p in glob.glob(os.path.join(TMP_DIR, st, ym, "*.zip")):
                os.remove(p)
                removed += 1
        log.info("ds=%s month=%s removed %d zips", ds, ym, removed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
