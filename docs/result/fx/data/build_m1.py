#!/usr/bin/env python3
"""G4 M1 pipeline: fetch 4 pairs (Kaggle almirneto/forex-multi-timeframe, CC0 per Kaggle) -> parquet 2005-2019 UTC
-> quality report DATA_REPORT_3.md -> delete own raw M1 CSVs.
Usage: build_m1.py all | fetch | convert | quality | report | cleanup
Timezone: file 'time' = bar OPEN time in broker server clock. Server clock regimes: Berlin (CET) before 2014-11-24, Athens (EET) after; see to_utc
(UTC+2 winter / UTC+3 summer, EU DST rules) => ts_utc = localize(server_naive, 'Europe/Athens') -> UTC.
(Athens-only and NY+6/NY+7 alternatives rejected: check_m1_regime.py)
Rows with UTC >= 2020-01-01 are dropped chunk by chunk right after parsing: never written, counted or printed.
Spread column is NOT kept (not a cost). No returns / signals computed (price LEVEL vs FRED only)."""
import json, logging, os, shutil, subprocess, sys, zipfile
from datetime import datetime, timezone
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import fetch_fx  # provenance helpers

BASE = os.path.expanduser("~/claude_master/w3/fx/data")
RAWD = os.path.join(BASE, "raw", "kaggle_m1")
DER = os.path.join(BASE, "derived", "m1")
PAIRS = ["EURUSD", "GBPUSD", "USDJPY", "AUDUSD"]
DS = "almirneto/forex-multi-timeframe"
DS_UPDATED = "2024-12-05 13:07:58 (kaggle datasets list lastUpdated)"
FRED = {"EURUSD": "DEXUSEU", "GBPUSD": "DEXUSUK", "USDJPY": "DEXJPUS", "AUDUSD": "DEXUSAL"}
START = pd.Timestamp("2005-01-01", tz="UTC")
END = pd.Timestamp("2020-01-01", tz="UTC")
SRV = "Europe/Athens"
NY = "America/New_York"
MIN_FREE = 9 * 1024 ** 3


def csv_path(p):
    return os.path.join(RAWD, "%s_M1.csv" % p)


def dl_cmd(p):
    return "kaggle datasets download %s -f %s/%s_M1.csv -p %s" % (DS, p, p, RAWD)


def free():
    return shutil.disk_usage(BASE).free


def fetch(p):
    os.makedirs(RAWD, exist_ok=True)
    key = "kaggle_m1/%s_M1.csv" % p
    prov = fetch_fx.load_prov()
    f = csv_path(p)
    if os.path.exists(f) and prov.get(key, {}).get("sha256") == fetch_fx.sha256(f):
        logging.info("skip fetch %s (sha matches)", p)
        return
    if free() < MIN_FREE + 0.75 * 1024 ** 3:
        raise SystemExit("ABORT: free disk %.1f GB too low before %s" % (free() / 1024 ** 3, p))
    when = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    env = dict(os.environ, PATH=os.path.expanduser("~/.local/bin") + ":" + os.environ.get("PATH", ""))
    r = subprocess.run(["kaggle", "datasets", "download", DS, "-f", "%s/%s_M1.csv" % (p, p), "-p", RAWD],
                       env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    tail = [l for l in r.stdout.splitlines() if "Warning" not in l and "%" not in l][-2:]
    logging.info("kaggle rc=%s %s", r.returncode, tail)
    if r.returncode != 0:
        raise SystemExit("ABORT: kaggle download failed for %s" % p)
    zinfo = None
    for z in [f + ".zip", os.path.join(RAWD, "%s_M1.zip" % p)]:
        if os.path.exists(z):
            zinfo = {"zip": os.path.basename(z), "zip_bytes": os.path.getsize(z), "zip_sha256": fetch_fx.sha256(z)}
            with zipfile.ZipFile(z) as zz:
                zz.extract("%s_M1.csv" % p, RAWD)
            os.remove(z)
            logging.info("unzipped and removed %s", z)
    os.chmod(f, 0o444)
    prov[key] = {"url": dl_cmd(p) + " (Kaggle dataset %s, license CC0-1.0 per Kaggle; updated %s)" % (DS, DS_UPDATED),
                 "downloaded_utc": when, "bytes": os.path.getsize(f), "sha256": fetch_fx.sha256(f),
                 "http": "kaggle-cli rc=0", "last_modified": DS_UPDATED}
    if zinfo:
        prov[key].update(zinfo)
    fetch_fx.save_prov(prov)
    logging.info("fetched %s bytes=%d free=%.1fGB", p, prov[key]["bytes"], free() / 1024 ** 3)
    if free() < MIN_FREE:
        raise SystemExit("ABORT: free disk below 9 GB after %s" % p)


SWITCH_SRV = pd.Timestamp("2014-11-24 00:00")          # first server-clock bar of the EET regime
SWITCH_UTC = pd.Timestamp("2014-11-23 22:00", tz="UTC")  # = SWITCH_SRV in Europe/Athens
SRV_OLD = "Europe/Berlin"  # CET/CEST (EU DST) before the switch - found from FRED offset scan + DST-mismatch test


def to_utc(srv_naive):
    """server clock -> UTC. Before 2014-11-24 00:00 server = Europe/Berlin (UTC+1/+2, EU DST);
    from then server = Europe/Athens (UTC+2/+3, EU DST)."""
    old = srv_naive < SWITCH_SRV
    a = srv_naive.dt.tz_localize(SRV, ambiguous="NaT", nonexistent="NaT").dt.tz_convert("UTC")
    b = srv_naive.dt.tz_localize(SRV_OLD, ambiguous="NaT", nonexistent="NaT").dt.tz_convert("UTC")
    return b.where(old, a)


def from_utc(ts_utc):
    a = ts_utc.dt.tz_convert(SRV).dt.tz_localize(None)
    b = ts_utc.dt.tz_convert(SRV_OLD).dt.tz_localize(None)
    return b.where(ts_utc < SWITCH_UTC, a)


def convert(p):
    os.makedirs(DER, exist_ok=True)
    out, meta = [], {"pair": p, "nat_tz": 0, "rows_read_lt2005": 0}
    first_srv, has_after = None, False
    lo, hi = pd.Timestamp("2004-12-31"), pd.Timestamp("2020-01-01 04:00")
    for ch in pd.read_csv(csv_path(p), usecols=["time", "open", "high", "low", "close", "tick_volume"], chunksize=2000000):
        srv = pd.to_datetime(ch["time"], unit="s")
        if first_srv is None:
            first_srv = str(srv.iloc[0])
        if (srv >= hi).any():
            has_after = True
        m = (srv >= lo) & (srv < hi)
        meta["rows_read_lt2005"] += int((srv < lo).sum())
        ch, srv = ch[m], srv[m]
        if ch.empty:
            continue
        utc = to_utc(srv)
        meta["nat_tz"] += int(utc.isna().sum())
        keep = utc.notna() & (utc >= START) & (utc < END)
        ch = ch[keep].drop(columns=["time"])
        ch.insert(0, "ts_utc", utc[keep].values)
        out.append(ch)
    d = pd.concat(out, ignore_index=True).sort_values("ts_utc")
    meta["dup_ts"] = int(d["ts_utc"].duplicated().sum())
    d = d.drop_duplicates("ts_utc", keep="first")
    d["ts_utc"] = pd.to_datetime(d["ts_utc"], utc=True)
    step = d["ts_utc"].diff().dt.total_seconds()
    meta.update({"first_row_file_server": first_srv, "has_rows_after_2019": has_after,
                 "first_utc_2005_2019": str(d["ts_utc"].iloc[0]), "last_utc_2005_2019": str(d["ts_utc"].iloc[-1]),
                 "rows_2005_2019": len(d), "median_step_s": float(step.median())})
    d.to_parquet(os.path.join(DER, "%s_M1_2005_2019.parquet" % p), index=False)
    json.dump(meta, open(os.path.join(DER, "meta_%s.json" % p), "w"), indent=1)
    logging.info("converted %s %s", p, meta)


def in_window(ny):
    wd = ny.dt.weekday
    mins = ny.dt.hour * 60 + ny.dt.minute
    return (wd <= 3) | ((wd == 4) & (mins < 1020)) | ((wd == 6) & (mins >= 1020))


def quality(p):
    d = pd.read_parquet(os.path.join(DER, "%s_M1_2005_2019.parquet" % p))
    d = d[d["ts_utc"] < END]
    ny = d["ts_utc"].dt.tz_convert(NY)
    srv = from_utc(d["ts_utc"])
    d["ny"], d["srv"] = ny, srv
    d["win"] = in_window(ny)
    d["gap"] = d["ts_utc"].diff().dt.total_seconds() / 60
    prev_wd = ny.shift(1).dt.weekday
    d["wkd"] = (d["gap"] > 1440) & prev_wd.isin([4, 5])
    fr = pd.read_csv(os.path.join(BASE, "derived", "FRED_%s.csv" % FRED[p]))
    fr["date"] = pd.to_datetime(fr["date"]); fr["x"] = pd.to_numeric(fr["v"], errors="coerce")
    fr = fr[(fr["date"] >= "2005-01-01") & (fr["date"] < "2020-01-01")].dropna(subset=["x"])
    ny_t = pd.to_datetime(fr["date"].dt.strftime("%Y-%m-%d") + " 11:59")
    t_eet = ny_t.dt.tz_localize(NY).dt.tz_convert("UTC")
    t_ny7 = t_eet  # alternatives tested separately: derived/m1/tz_regime_test_preFix_allAthens.csv
    off_ny = ny_t.dt.tz_localize(NY).apply(lambda x: x.utcoffset().total_seconds() / 3600)
    off_srv = ny_t.dt.tz_localize(NY).dt.tz_convert("Europe/Berlin").apply(lambda x: x.utcoffset().total_seconds() / 3600)
    fr["mismatch"] = (off_srv - off_ny).values != 6
    s = d[["ts_utc", "close"]].sort_values("ts_utc")

    def look(t):
        q = pd.DataFrame({"t": t.values, "i": np.arange(len(t))}).sort_values("t")
        q["t"] = pd.to_datetime(q["t"], utc=True)
        m = pd.merge_asof(q, s, left_on="t", right_on="ts_utc", direction="backward", tolerance=pd.Timedelta("5min"))
        return m.sort_values("i")["close"].values

    fr["c_eet"], fr["c_ny7"] = look(t_eet), look(t_ny7)
    fr["ld"] = np.log(fr["c_eet"]) - np.log(fr["x"])
    fr["ld7"] = np.log(fr["c_ny7"]) - np.log(fr["x"])
    rows = []
    for y in range(2005, 2020):
        g = d[d["ny"].dt.year == y]
        exp_idx = pd.date_range("%d-01-01" % y, "%d-01-01" % (y + 1), freq="min", inclusive="left", tz=NY)
        expected = int(in_window(pd.Series(exp_idx)).sum())
        obs = int(g["win"].sum())
        ng = g[~g["wkd"]]
        h, l, o, c = g["high"], g["low"], g["open"], g["close"]
        f = fr[fr["date"].dt.year == y].dropna(subset=["ld"])
        a = f["ld"].abs()
        rows.append(dict(pair=p, year=y, bars=len(g), bars_out_window=int((~g["win"]).sum()), expected_min=expected,
                         missing_pct=round(100 * (1 - obs / expected), 2), gaps_gt5=int((ng["gap"] > 5).sum()),
                         gaps_gt60=int((ng["gap"] > 60).sum()), max_gap_min=float(ng["gap"].max()),
                         hi_lt_lo=int((h < l).sum()), px_le0=int(((g[["open", "high", "low", "close"]] <= 0).any(axis=1)).sum()),
                         range_gt2pct=int((h / l - 1 > 0.02).sum()),
                         oc_outside=int(((o > h + 1e-9) | (o < l - 1e-9) | (c > h + 1e-9) | (c < l - 1e-9)).sum()),
                         fred_n=len(f), fred_med_abs_pct=round(100 * a.median(), 4), fred_p99_abs_pct=round(100 * a.quantile(0.99), 4),
                         fred_gt05=int((a > 0.005).sum()), fred_med_signed_pct=round(100 * f["ld"].median(), 4)))
    q = pd.DataFrame(rows)
    q.to_csv(os.path.join(DER, "quality_%s.csv" % p), index=False)
    mm = fr[fr["mismatch"]].dropna(subset=["ld", "ld7"])
    nm = fr[~fr["mismatch"]].dropna(subset=["ld", "ld7"])
    # Friday last bar before weekend gap, server clock, mismatch vs normal weeks
    nxt_wkd = d["wkd"].shift(-1, fill_value=False)
    lastfri = d[nxt_wkd & (d["ny"].dt.weekday == 4)]
    lf_ny = lastfri["ny"].dt.tz_localize(None)
    off_ny_l = lastfri["ny"].apply(lambda x: x.utcoffset().total_seconds() / 3600)
    off_srv_l = lastfri["ts_utc"].dt.tz_convert("Europe/Berlin").apply(lambda x: x.utcoffset().total_seconds() / 3600)
    mis_l = (off_srv_l - off_ny_l) != 6
    tz = {"pair": p,
          "fri_last_bar_server_mismatch_weeks": lastfri.loc[mis_l, "srv"].dt.strftime("%H:%M").value_counts().head(4).to_dict(),
          "fri_last_bar_server_normal_weeks": lastfri.loc[~mis_l, "srv"].dt.strftime("%H:%M").value_counts().head(4).to_dict(),
          "fri_last_bar_NY_mismatch_weeks": lf_ny[mis_l].dt.strftime("%H:%M").value_counts().head(3).to_dict(),
          "mismatch_days_n": len(mm), "mismatch_med_abs_pct_regime": round(100 * mm["ld"].abs().median(), 4),
          "mismatch_gt05_regime": int((mm["ld"].abs() > 0.005).sum()),
          "normal_days_n": len(nm), "normal_med_abs_pct_regime": round(100 * nm["ld"].abs().median(), 4),
          "fri_last_bar_NY_normal_weeks": lf_ny[~mis_l].dt.strftime("%H:%M").value_counts().head(3).to_dict()}
    json.dump(tz, open(os.path.join(DER, "tzcheck_%s.json" % p), "w"), indent=1)
    big = ng_all = d[(~d["wkd"]) & (d["gap"] > 60)].nlargest(5, "gap")[["ts_utc", "gap"]]
    big.to_csv(os.path.join(DER, "biggaps_%s.csv" % p), index=False)
    logging.info("quality %s done; tz %s", p, tz)


def report():
    L = ["# DATA_REPORT_3 - G4 M1 (Kaggle %s) 2005-2019" % DS, "",
         "Generated by code/build_m1.py. HOLDOUT >= 2020-01-01 UTC never written/counted. Spread column dropped (not a cost).",
         "Kaggle license CC0-1.0 (as shown on Kaggle; uploader-assigned; upstream broker unnamed => internal research only).", "",
         "## Timezone",
         "File `time` = bar OPEN time, broker server clock. M1 RESULT DIFFERS FROM M15 SAMPLE CHECK: server clock has TWO regimes:",
         "- server time < 2014-11-24 00:00: ts_utc = tz_localize(server, 'Europe/Berlin').tz_convert('UTC')  [CET/CEST, UTC+1/+2, EU DST]",
         "- server time >= 2014-11-24 00:00: ts_utc = tz_localize(server, 'Europe/Athens').tz_convert('UTC') [EET/EEST, UTC+2/+3, EU DST]",
         "NY time = ts_utc.tz_convert('America/New_York'). Switch over weekend 2014-11-22/23 (no clock jump inside 2014-11-24..25;",
         "Friday last bar 22:59 server up to 2014-11-21, 23:59 from 2014-11-28). Before the switch the week opens Sun 18:00 NY (not 17:00).",
         "Evidence (run on all-Athens parquet before fix; files derived/m1/*_preFix_allAthens.csv):",
         "- offset scan: 2005-2014 FRED diff minimal at -60 min, 2015-2019 at 0 min; monthly: >=3/4 pairs prefer -60 in every month 2005-01..2014-11, <=1/4 from 2014-12.",
         "- DST-mismatch-days test (median |log diff| %, EURUSD): pre-switch Berlin 0.0077 vs Athens 0.0677 / NY+7 0.0856 / NY+6 0.0689; post-switch Athens 0.0071 vs Berlin 0.0624 / NY+7 0.0665 (NY+6 = Athens in mismatch weeks only; normal weeks 0.0643 vs 0.0073). Same pattern all 4 pairs.",
         "After fix (regime conversion), per pair: Friday last bar (server / NY) and FRED diff on DST-mismatch vs normal days:", ""]
    for p in PAIRS:
        L.append("- %s: %s" % (p, json.load(open(os.path.join(DER, "tzcheck_%s.json" % p)))))
    L += ["", "## Coverage (meta)", ""]
    for p in PAIRS:
        L.append("- %s: %s" % (p, json.load(open(os.path.join(DER, "meta_%s.json" % p)))))
    q = pd.concat([pd.read_csv(os.path.join(DER, "quality_%s.csv" % p)) for p in PAIRS])
    L += ["", "## Pair x year (missing_pct = 1 - bars in window / minutes Sun17:00-Fri17:00 NY; holidays count as missing;"
          " gaps exclude weekend; FRED = log(close of bar 11:59-12:00 NY) - log(FRED H.10), %)", ""]
    cols = list(q.columns)
    L.append("| " + " | ".join(cols) + " |"); L.append("|" + "---|" * len(cols))
    for r in q.itertuples(index=False):
        L.append("| " + " | ".join(str(x) for x in r) + " |")
    L += ["", "## Summary by period", "", "| pair | period | missing_pct | fred_med_abs_pct (median of years) | fred_gt05 days | fred_n | anomalies(hi<lo,px<=0,range>2%,oc_out) |", "|---|---|---|---|---|---|---|"]
    for p in PAIRS:
        for a, b in [(2005, 2009), (2010, 2014), (2015, 2019)]:
            g = q[(q.pair == p) & (q.year >= a) & (q.year <= b)]
            miss = 100 * (1 - (g.expected_min * (1 - g.missing_pct / 100)).sum() / g.expected_min.sum())
            L.append("| %s | %d-%d | %.2f | %.4f | %d | %d | %d,%d,%d,%d |" % (p, a, b, miss, g.fred_med_abs_pct.median(), g.fred_gt05.sum(),
                     g.fred_n.sum(), g.hi_lt_lo.sum(), g.px_le0.sum(), g.range_gt2pct.sum(), g.oc_outside.sum()))
    bad = q[(q.missing_pct > 5) | (q.fred_med_abs_pct > 0.05) | (q.fred_gt05 > 0.02 * q.fred_n) | (q.fred_med_signed_pct.abs() > 0.05)]
    L += ["", "## FAIL list (agent thresholds: missing_pct > 5 OR fred median |diff| > 0.05% OR >2% of days |diff| > 0.5% OR |median signed| > 0.05%)", ""]
    L += ["- %s %d: missing %.2f%%, fred_med_abs %.4f%%, gt05 %d/%d, signed %.4f%%" % (r.pair, r.year, r.missing_pct, r.fred_med_abs_pct,
          r.fred_gt05, r.fred_n, r.fred_med_signed_pct) for r in bad.itertuples()] or ["- none"]
    L += ["", "Largest non-weekend gaps per pair: derived/m1/biggaps_<PAIR>.csv. BID/MID: MT5 bars are BID by platform convention;"
          " a half-spread (~0.005%) is below FRED-noise so cannot be confirmed from FRED (see fred_med_signed_pct)."]
    open(os.path.join(BASE, "DATA_REPORT_3.md"), "w").write("\n".join(L) + "\n")
    logging.info("wrote DATA_REPORT_3.md")


def cleanup():
    prov = fetch_fx.load_prov()
    for p in PAIRS:
        f = csv_path(p)
        key = "kaggle_m1/%s_M1.csv" % p
        if not (os.path.exists(os.path.join(DER, "%s_M1_2005_2019.parquet" % p)) and prov.get(key, {}).get("sha256")):
            logging.error("not deleting %s: parquet or provenance missing", f); continue
        if os.path.exists(f):
            os.remove(f)
            prov[key]["status"] = "da xoa %s; tai lai duoc bang lenh: %s ; kiem sha256 nhu tren" % (
                datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), dl_cmd(p))
            logging.info("deleted %s", f)
    fetch_fx.save_prov(prov)
    logging.info("free disk after cleanup %.1f GB", free() / 1024 ** 3)


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                        handlers=[logging.FileHandler(os.path.join(BASE, "build_m1.log")), logging.StreamHandler(sys.stderr)])
    st = sys.argv[1] if len(sys.argv) > 1 else "all"
    ps = sys.argv[2:] or PAIRS
    if st in ("all", "fetch", "convert"):
        for p in ps:
            if st in ("all", "fetch"):
                fetch(p)
            if st in ("all", "convert"):
                convert(p)
    if st in ("all", "quality"):
        for p in ps:
            quality(p)
    if st in ("all", "report"):
        report()
    if st in ("all", "cleanup"):
        cleanup()
    logging.info("stage %s finished", st)


if __name__ == "__main__":
    main()
