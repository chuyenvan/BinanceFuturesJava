# OFI V3 UNIVERSE -- build hourly OFI_1h / aggressive_buy_ratio_1h features from Binance Vision
# monthly aggTrades bulk CSV, cho PHAM VI MO RONG chot trong docs/PREREG_S1_FREE_OFI_V3_UNIVERSE.md
# (toan bo symbol trong symbol_map.csv co >=1 thang aggTrades monthly trong 2021-07..2025-12,
# KHONG loc theo thanh khoan). Chia 10 shard can bang theo MB (ofi_v3_shards.json); moi kernel
# Kaggle chay 1 shard. LOGIC TINH OFI Y HET research/pipeline/x1/kaggle_ofi/ofi_build_feat.py
# (cung URL, cung cot, cung query duckdb, cung cong thuc ofi_1h/aggr_buy_ratio_1h, cung NaN rule).
# Khac biet DUY NHAT so voi ban 15-sym: (1) danh sach symbol lay tu shard, (2) logging thay print,
# (3) xoa ca file CSV da giai nen neu loi giua chung (tranh day dia), (4) summary ghi them shard id.
import json
import logging
import os
import subprocess
import sys
import time
import zipfile

subprocess.run([sys.executable, "-m", "pip", "install", "-q", "requests", "duckdb"], check=False)
import requests  # noqa: E402
import duckdb  # noqa: E402
import pandas as pd  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout)
log = logging.getLogger("ofi_v3_build")

SHARD_ID = __SHARD_ID__  # thay bang so nguyen 0..9 khi sinh kernel (gen_kernels_v3.py)
SHARDS = json.loads(r'''__SHARDS_JSON__''')

WORK = "/kaggle/working"
os.makedirs(WORK, exist_ok=True)
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) ofi-stage-b-build/1.0"}
BASE = "https://data.binance.vision/data/futures/um/monthly/aggTrades"

SYM2ID = {s: int(i) for s, i in SHARDS[str(SHARD_ID)]}
MONTHS = [str(p) for p in pd.period_range("2021-07", "2025-12", freq="M")]
SAFETY_LIMIT_SEC = float(os.environ.get("OFI_SAFETY_LIMIT_SEC", 3.5 * 3600))
log.info("SHARD %d: %d symbols, %d months, safety %.0fs", SHARD_ID, len(SYM2ID), len(MONTHS),
         SAFETY_LIMIT_SEC)

t_start = time.time()
agg_rows = []   # list of dataframes (ts_h, sym, buy_vol, sell_vol, n)
log_records = []
stopped_early = False
done_syms = []

for sym, symid in SYM2ID.items():
    for month in MONTHS:
        elapsed = time.time() - t_start
        if elapsed > SAFETY_LIMIT_SEC:
            stopped_early = True
            log.info("SAFETY LIMIT reached (%.0fs > %.0fs) -- stopping before %s %s",
                     elapsed, SAFETY_LIMIT_SEC, sym, month)
            break
        url = f"{BASE}/{sym}/{sym}-aggTrades-{month}.zip"
        zpath = f"{WORK}/tmp.zip"
        csv_path = None
        rec = dict(sym=sym, symid=symid, month=month, url=url)
        t0 = time.time()
        try:
            r = requests.get(url, headers=HEADERS, timeout=180, stream=True)
            rec["status"] = r.status_code
            if r.status_code != 200:
                rec["ok"] = False
                rec["sec"] = time.time() - t0
                log_records.append(rec)
                log.info("%s %s SKIP status=%s (%.2fs)", sym, month, r.status_code, rec["sec"])
                continue
            with open(zpath, "wb") as f:
                for chunk in r.iter_content(1 << 16):
                    if chunk:
                        f.write(chunk)
            t_dl = time.time() - t0
            t1 = time.time()
            with zipfile.ZipFile(zpath) as z:
                name = z.namelist()[0]
                z.extract(name, WORK)
            csv_path = f"{WORK}/{name}"
            t_unzip = time.time() - t1
            with open(csv_path, "r") as f:
                first_line = f.readline().strip()
            skip = 1 if first_line.lower().startswith("agg") else 0
            t2 = time.time()
            con = duckdb.connect()
            q = f"""
            SELECT CAST(floor(column6 / 3600000.0) * 3600000 AS BIGINT) AS ts_h,
                   SUM(CASE WHEN LOWER(CAST(column7 AS VARCHAR)) IN ('false','0')
                            THEN column3 ELSE 0 END) AS buy_vol,
                   SUM(CASE WHEN LOWER(CAST(column7 AS VARCHAR)) IN ('true','1')
                            THEN column3 ELSE 0 END) AS sell_vol,
                   COUNT(*) AS n
            FROM read_csv('{csv_path}', header=false, skip={skip},
                           columns={{'column1':'BIGINT','column2':'DOUBLE','column3':'DOUBLE',
                                     'column4':'BIGINT','column5':'BIGINT','column6':'BIGINT',
                                     'column7':'VARCHAR'}})
            GROUP BY ts_h
            """
            out = con.execute(q).fetchdf()
            con.close()
            out["sym"] = symid
            t_agg = time.time() - t2
            agg_rows.append(out[["ts_h", "sym", "buy_vol", "sell_vol", "n"]])
            os.remove(zpath)
            os.remove(csv_path)
            rec.update(ok=True, dl_sec=t_dl, unzip_sec=t_unzip, agg_sec=t_agg,
                       n_hours=len(out), n_trades=int(out.n.sum()))
            log_records.append(rec)
            log.info("%s %s OK dl=%.1fs unzip=%.1fs agg=%.1fs hours=%d trades=%d elapsed_total=%.0fs",
                     sym, month, t_dl, t_unzip, t_agg, len(out), int(out.n.sum()), elapsed)
        except Exception as e:  # noqa: BLE001
            rec.update(ok=False, err=str(e), sec=time.time() - t0)
            log_records.append(rec)
            log.info("%s %s ERROR %s", sym, month, e)
            for p in (zpath, csv_path):
                if p and os.path.exists(p):
                    try:
                        os.remove(p)
                    except Exception:  # noqa: BLE001
                        pass
    else:
        done_syms.append(sym)
        if agg_rows:
            chk = pd.concat(agg_rows, ignore_index=True)
            chk.to_parquet(f"{WORK}/ofi_hourly_raw_checkpoint.parquet")
        with open(f"{WORK}/ofi_build_log.json", "w") as f:
            json.dump(log_records, f, indent=2, default=str)
        continue
    break  # safety limit hit in inner loop -> also break outer loop

t_total = time.time() - t_start
log.info("=== LOOP DONE, elapsed %.0fs, stopped_early=%s ===", t_total, stopped_early)

if agg_rows:
    RAW = pd.concat(agg_rows, ignore_index=True)
    RAW = RAW.groupby(["ts_h", "sym"], as_index=False)[["buy_vol", "sell_vol", "n"]].sum()
else:
    RAW = pd.DataFrame(columns=["ts_h", "sym", "buy_vol", "sell_vol", "n"])

RAW["ofi_1h"] = (RAW.buy_vol - RAW.sell_vol) / (RAW.buy_vol + RAW.sell_vol)
RAW["aggr_buy_ratio_1h"] = RAW.buy_vol / (RAW.buy_vol + RAW.sell_vol)
RAW.loc[(RAW.buy_vol + RAW.sell_vol) <= 0, ["ofi_1h", "aggr_buy_ratio_1h"]] = None

FEAT = RAW.rename(columns={"ts_h": "ts"})[["ts", "sym", "ofi_1h", "aggr_buy_ratio_1h"]]
FEAT.to_parquet(f"{WORK}/ofi_feat_x1.parquet")
RAW.to_parquet(f"{WORK}/ofi_hourly_raw.parquet")

with open(f"{WORK}/ofi_build_log.json", "w") as f:
    json.dump(log_records, f, indent=2, default=str)

n_ok = sum(1 for r in log_records if r.get("ok"))
n_skip = sum(1 for r in log_records if r.get("ok") is False and "status" in r and r.get("status") != 200)
n_err = sum(1 for r in log_records if r.get("ok") is False and "err" in r)
summary = dict(
    shard=SHARD_ID, n_symbols_in_shard=len(SYM2ID), n_symbols_completed=len(done_syms),
    symbols_not_completed=[s for s in SYM2ID if s not in done_syms],
    symids_not_completed=[SYM2ID[s] for s in SYM2ID if s not in done_syms],
    n_symbol_months_attempted=len(log_records), n_ok=n_ok, n_skip_404=n_skip, n_err=n_err,
    err_records=[r for r in log_records if r.get("ok") is False and "err" in r],
    total_elapsed_sec=t_total, stopped_early=stopped_early,
    n_feature_rows=len(FEAT), n_symbols_with_data=int(FEAT.sym.nunique()) if len(FEAT) else 0,
    ts_min=int(FEAT.ts.min()) if len(FEAT) else None,
    ts_max=int(FEAT.ts.max()) if len(FEAT) else None,
)
with open(f"{WORK}/ofi_build_summary.json", "w") as f:
    json.dump(summary, f, indent=2, default=str)
log.info("=== SUMMARY ===\n%s", json.dumps(summary, indent=2, default=str))
log.info("DONE")
sys.exit(0)
