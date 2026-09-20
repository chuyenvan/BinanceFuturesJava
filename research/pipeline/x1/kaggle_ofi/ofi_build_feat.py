# OFI Stage B -- build hourly OFI_1h / aggressive_buy_ratio_1h features from Binance
# Vision monthly aggTrades bulk CSV, for the 15-symbol scope chosen in
# docs/PREREG_S1_FREE_OFI.md (Stage A feasibility). Streaming-through: download one
# monthly zip, unzip, duckdb-aggregate to (ts_h, sym) buy/sell volume, delete raw file,
# checkpoint after every symbol. Self-contained Kaggle CPU kernel, enable_internet=true.
import json
import os
import subprocess
import sys
import time
import zipfile

subprocess.run([sys.executable, "-m", "pip", "install", "-q", "requests", "duckdb"], check=False)
import requests  # noqa: E402
import duckdb  # noqa: E402
import pandas as pd  # noqa: E402

WORK = "/kaggle/working"
os.makedirs(WORK, exist_ok=True)
HEADERS = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) ofi-stage-b-build/1.0"}
BASE = "https://data.binance.vision/data/futures/um/monthly/aggTrades"

# 15 symbol, chon theo PREREG_S1_FREE_OFI.md (top-15 theo count trong
# PROPOSAL_MICROSTRUCTURE_DATA.md muc 2.1, da loai 8 memecoin niem yet muon).
SYM2ID = {
    "AIAUSDT": 525, "PEOPLEUSDT": 113, "UNFIUSDT": 77, "ALCHUSDT": 360, "MASKUSDT": 101,
    "MYXUSDT": 462, "BLZUSDT": 53, "ALICEUSDT": 85, "COAIUSDT": 531, "EVAAUSDT": 544,
    "RSRUSDT": 48, "1000PEPEUSDT": 166, "WIFUSDT": 226, "CHRUSDT": 83, "SOLUSDT": 49,
}
MONTHS = [str(p) for p in pd.period_range("2021-07", "2025-12", freq="M")]
SAFETY_LIMIT_SEC = float(os.environ.get("OFI_SAFETY_LIMIT_SEC", 3.5 * 3600))

t_start = time.time()
agg_rows = []   # list of dataframes (ts_h, sym, buy_vol, sell_vol, n)
log_records = []
stopped_early = False

for sym, symid in SYM2ID.items():
    for month in MONTHS:
        elapsed = time.time() - t_start
        if elapsed > SAFETY_LIMIT_SEC:
            stopped_early = True
            print(f"SAFETY LIMIT reached ({elapsed:.0f}s > {SAFETY_LIMIT_SEC:.0f}s) -- "
                  f"stopping before {sym} {month}", flush=True)
            break
        url = f"{BASE}/{sym}/{sym}-aggTrades-{month}.zip"
        zpath = f"{WORK}/tmp.zip"
        rec = dict(sym=sym, symid=symid, month=month, url=url)
        t0 = time.time()
        try:
            r = requests.get(url, headers=HEADERS, timeout=180, stream=True)
            rec["status"] = r.status_code
            if r.status_code != 200:
                rec["ok"] = False
                rec["sec"] = time.time() - t0
                log_records.append(rec)
                print(f"{sym} {month} SKIP status={r.status_code} ({rec['sec']:.2f}s)", flush=True)
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
            out["sym"] = symid
            t_agg = time.time() - t2
            agg_rows.append(out[["ts_h", "sym", "buy_vol", "sell_vol", "n"]])
            os.remove(zpath)
            os.remove(csv_path)
            rec.update(ok=True, dl_sec=t_dl, unzip_sec=t_unzip, agg_sec=t_agg,
                       n_hours=len(out), n_trades=int(out.n.sum()))
            log_records.append(rec)
            print(f"{sym} {month} OK dl={t_dl:.1f}s unzip={t_unzip:.1f}s agg={t_agg:.1f}s "
                  f"hours={len(out)} trades={int(out.n.sum())} elapsed_total={elapsed:.0f}s",
                  flush=True)
        except Exception as e:
            rec.update(ok=False, err=str(e), sec=time.time() - t0)
            log_records.append(rec)
            print(f"{sym} {month} ERROR {e}", flush=True)
            for p in (zpath,):
                if os.path.exists(p):
                    try:
                        os.remove(p)
                    except Exception:
                        pass
    else:
        # inner loop completed without break -> continue outer loop
        # checkpoint after each symbol
        if agg_rows:
            chk = pd.concat(agg_rows, ignore_index=True)
            chk.to_parquet(f"{WORK}/ofi_hourly_raw_checkpoint.parquet")
        with open(f"{WORK}/ofi_build_log.json", "w") as f:
            json.dump(log_records, f, indent=2, default=str)
        continue
    break  # safety limit hit in inner loop -> also break outer loop

t_total = time.time() - t_start
print(f"=== LOOP DONE, elapsed {t_total:.0f}s, stopped_early={stopped_early} ===", flush=True)

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
    n_symbol_months_attempted=len(log_records), n_ok=n_ok, n_skip_404=n_skip, n_err=n_err,
    total_elapsed_sec=t_total, stopped_early=stopped_early,
    n_feature_rows=len(FEAT), n_symbols_with_data=int(FEAT.sym.nunique()) if len(FEAT) else 0,
    ts_min=int(FEAT.ts.min()) if len(FEAT) else None,
    ts_max=int(FEAT.ts.max()) if len(FEAT) else None,
)
with open(f"{WORK}/ofi_build_summary.json", "w") as f:
    json.dump(summary, f, indent=2, default=str)
print("=== SUMMARY ===", flush=True)
print(json.dumps(summary, indent=2, default=str), flush=True)
print("DONE", flush=True)
sys.exit(0)
