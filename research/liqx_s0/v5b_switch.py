"""LIQX_S0 V5b: pin the date Vision metrics create_time semantics switched (OI at T vs at T+5m), vs Tardis derivative_ticker OI.
Evidence independent of liquidations. Also 2026-10-01 (daily Vision metrics zip) for sample F."""
import pandas as pd, numpy as np, pyarrow.parquet as pq, os, json, zipfile, io
WK = os.path.expanduser("~/claude_master/liqx_wk"); OUT = os.path.expanduser("~/claude_master/vz_e1_wt/docs/result/liqx_s0")
days = ["2023-10-01", "2023-12-01", "2024-01-01", "2024-02-01", "2024-03-01", "2024-04-01", "2024-05-01", "2024-06-01", "2024-07-01", "2025-01-01", "2026-10-01"]
res = {}
for day in days:
    for sym in ["BTCUSDT", "SOLUSDT"]:
        f = f"{WK}/probe/dt_{sym}_{day}.csv.gz"
        if not os.path.exists(f):
            os.system(f"curl -s -o {f} https://datasets.tardis.dev/v1/binance-futures/derivative_ticker/{day.replace('-', '/')}/{sym}.csv.gz")
        try:
            t = pd.read_csv(f, usecols=["timestamp", "open_interest"]).dropna()
        except Exception as e:
            res[f"{sym}_{day}"] = f"ERR {e}"; continue
        t["ms"] = (t.timestamp // 1000).astype("int64"); t = t.sort_values("ms")
        y, m = int(day[:4]), int(day[5:7]); t0 = int(pd.Timestamp(day, tz="UTC").value // 10**6)
        if y == 2026:
            zf = f"{WK}/probe/{sym}-metrics-{day}.zip"
            if not os.path.exists(zf):
                os.system(f"curl -s -o {zf} https://data.binance.vision/data/futures/um/daily/metrics/{sym}/{sym}-metrics-{day}.zip")
            z = zipfile.ZipFile(zf); d = pd.read_csv(io.BytesIO(z.read(z.namelist()[0])))
            v = pd.DataFrame({"ts": (pd.to_datetime(d.create_time, utc=True).astype("int64") // 10**6).astype("int64"), "oi": d.sum_open_interest})
        else:
            v = pq.read_table(f"/home/ubuntu/vz/out/metrics5m/{y}/{y}-{m:02d}.parquet", columns=["ts", "sym", "oi"],
                              filters=[("ts", ">=", t0), ("ts", "<", t0 + 86400_000)]).to_pandas()
            v = v[v.sym.astype(str) == sym]
        v = v[(v.ts >= t0 + 3600_000) & (v.ts < t0 + 82800_000)]
        e0, e5 = [], []
        for L, acc in ((0, e0), (300_000, e5)):
            for LL in range(L - 30_000, L + 30_001, 10_000):
                idx = np.searchsorted(t.ms.values, v.ts.values + LL, side="right") - 1
                acc.append(float(np.median(np.abs(v.oi.values - t.open_interest.values[idx]) / v.oi.values)))
        # per-row: which lag fits better
        i0 = np.searchsorted(t.ms.values, v.ts.values + 15_000, side="right") - 1
        i5 = np.searchsorted(t.ms.values, v.ts.values + 315_000, side="right") - 1
        a0 = np.abs(v.oi.values - t.open_interest.values[i0]); a5 = np.abs(v.oi.values - t.open_interest.values[i5])
        r = {"err_L0": min(e0), "err_L300": min(e5), "frac_rows_closer_L300": float((a5 < a0).mean()), "n": int(len(v)),
             "verdict": "T+5m" if min(e5) < 0.5 * min(e0) else ("T" if min(e0) < 0.5 * min(e5) else "UNCLEAR")}
        # intraday switch check: first/last half
        h = len(v) // 2
        r["frac_closer_L300_first_half"] = float((a5[:h] < a0[:h]).mean()); r["frac_closer_L300_second_half"] = float((a5[h:] < a0[h:]).mean())
        res[f"{sym}_{day}"] = r; print(sym, day, r, flush=True)
json.dump(res, open(OUT + "/v5b_switch.json", "w"), indent=1)
