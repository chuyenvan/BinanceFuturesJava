"""VZ E1 - one extra pass over 2024 to build the non-crash event sets used by
T4 (funding settlements), T5 (extreme basis) and the listing-age series for T6.

Writes
  ~/vz_e1/out/e1_t4_funding_events.parquet    (settlements + returns around them)
  ~/vz_e1/out/e1_t5_basis_events.parquet      (|prem z7|>3, merged 60'/symbol)
  ~/vz_e1/out/e1_sym_life_2024.parquet        (first/last ts+close per symbol)
  ~/vz_e1/out/e1_listing_drift.parquet        (1/3/7/30d drift after a 2024 listing)

Same cost/statistics conventions as e1_core. Deterministic.
"""
import os
import time

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

import e1_data
import e1_core
from e1_common import FEE_2LEG, OUT, bucket_of, cost_of, ensure_dirs, setup_logging, write_json

log = setup_logging("e1_families", "e1_families_pass.log")

BUCKET_EVENT = 0            # funding / basis events are not crash candles -> NC
NC_COST = cost_of(BUCKET_EVENT)
NC_COST_STRESS = cost_of(BUCKET_EVENT, stress=True)
Z_THRESH = 3.0
MERGE_MS = 60 * 60 * 1000
DRIFT_DAYS = (1, 3, 7, 30)


def _asof(ts, ref):
    return int(np.searchsorted(ts, ref, side="right") - 1)


def _read(path, cols, lo, hi):
    d = pq.read_table(path, columns=cols).to_pandas()
    d = d[(d.ts >= lo) & (d.ts <= hi)]
    return d


def run():
    ensure_dirs()
    t0 = time.time()
    fdf = pd.read_parquet(e1_data.funding_year("2024")).sort_values(["sym", "ts"], kind="stable")
    fund_by_sym = {s: g for s, g in fdf.groupby("sym", sort=False)}
    btc_series = None
    fund_rows, basis_rows, life_rows, drift_rows = [], [], [], []
    snap_rows = []
    life = {}
    pending_drift = {}   # sym -> {"t0": ts, "c0": close, "need": {h: True}}
    for month in e1_core.MONTHS_2024:
        m_start, m_end = e1_core.month_bounds(month)
        mi = e1_core.MONTHS_2024.index(month)
        lo = m_start - 7 * 86_400_000
        kl = _read(e1_data.kline_month(month), ["ts", "sym", "open", "close", "quote_volume"], lo, m_end)
        ba = _read(e1_data.basis_month(month), ["ts", "sym", "prem_close"], lo, m_end)
        if mi < 11:
            nxt_m = e1_core.MONTHS_2024[mi + 1]
            kl = pd.concat([kl, _read(e1_data.kline_month(nxt_m), ["ts", "sym", "open", "close",
                            "quote_volume"], m_end, m_end + 4 * 3_600_000)], ignore_index=True)
            ba = pd.concat([ba, _read(e1_data.basis_month(nxt_m), ["ts", "sym", "prem_close"],
                                      m_end, m_end + 4 * 3_600_000)], ignore_index=True)
        kl = kl.sort_values(["sym", "ts"], kind="stable")
        g = kl.groupby("sym", sort=False)
        idx = {}
        month_hi = m_end - 1
        for sym, gg in g:
            gg2 = gg[gg.ts < m_end]
            if len(gg2):
                snap_rows.append({"sym": sym, "month": month,
                                  "close_first": float(gg2.close.to_numpy()[0]),
                                  "close_last": float(gg2.close.to_numpy()[-1]),
                                  "last_ts": int(gg2.ts.to_numpy()[-1])})
            idx[sym] = (gg.ts.to_numpy(np.int64), gg.close.to_numpy(np.float64),
                        gg.open.to_numpy(np.float64))
            tmin = int(gg.ts.to_numpy()[0]); tmax = int(gg.ts.to_numpy()[-1])
            if sym not in life:
                life[sym] = [tmin, tmax, float(gg.close.to_numpy()[0])]
                # a symbol whose first 2024 bar is after 2024-01-01 was listed in 2024
                if tmin > 1704067200000:
                    pending_drift[sym] = {"t0": tmin, "c0": float(gg.close.to_numpy()[0]),
                                          "need": {h: True for h in DRIFT_DAYS}}
            else:
                life[sym][1] = max(life[sym][1], tmax)
        # BTC series for the funding-regime split
        btc_ts = btc_cl = None
        btc_part = kl[kl.sym == "BTCUSDT"].sort_values("ts")
        if len(btc_part):
            btc_ts = btc_part.ts.to_numpy(np.int64)
            btc_cl = btc_part.close.to_numpy(np.float64)
        # ---- T4 funding settlements ----
        fev = fdf[(fdf.ts >= m_start) & (fdf.ts < m_end)]
        ba_g = ba.groupby("sym", sort=False)
        ba_idx = {s: (gg.ts.to_numpy(np.int64), gg.prem_close.to_numpy(np.float64))
                  for s, gg in ba_g}
        for sym, evs in fev.groupby("sym", sort=False):
            if sym not in idx:
                continue
            kts, kcl, _kop = idx[sym]
            bts, bpr = ba_idx.get(sym, (np.array([], dtype=np.int64), np.array([])))
            for ts in evs.ts.to_numpy(np.int64):
                i = _asof(kts, ts)
                if i < 0 or kts[i] != ts:
                    continue
                c0 = kcl[i]
                jb = _asof(kts, ts - 3_600_000)
                j60 = _asof(kts, ts + 3_600_000)
                j240 = _asof(kts, ts + 4 * 3_600_000)
                p8 = np.nan
                if bts.size:
                    lo8 = _asof(bts, ts - 8 * 3_600_000)
                    hi8 = _asof(bts, ts - 60_000)
                    if hi8 > lo8 >= 0:
                        seg = bpr[lo8:hi8 + 1]
                        seg = seg[np.isfinite(seg)]
                        if seg.size:
                            p8 = float(seg.mean())
                rate = float(evs.loc[evs.ts == ts, "rate"].iloc[0])
                ih = int(evs.loc[evs.ts == ts, "interval_h"].iloc[0])
                btc24 = np.nan
                if btc_ts is not None:
                    i24 = _asof(btc_ts, ts - 86_400_000)
                    ib = _asof(btc_ts, ts)
                    if i24 >= 0 and ib >= 0 and btc_cl[i24] > 0:
                        btc24 = btc_cl[ib] / btc_cl[i24] - 1.0
                fund_rows.append({
                    "btc_ret_24h": btc24,
                    "sym": sym, "ts": int(ts), "rate": rate, "interval_h": ih,
                    "prem_mean8": p8,
                    "ret_pre": (kcl[jb] / c0 - 1.0) if (jb >= 0 and jb != i and c0) else np.nan,
                    "ret_60": (kcl[j60] / c0 - 1.0) if (j60 > i and c0) else np.nan,
                    "ret_240": (kcl[j240] / c0 - 1.0) if (j240 > i and c0) else np.nan})
        # ---- T5 extreme basis ----
        for sym, gg in ba.groupby("sym", sort=False):
            gg = gg.sort_values("ts")
            pz = _prem_z7(gg.prem_close.to_numpy(np.float64))
            ts_arr = gg.ts.to_numpy(np.int64)
            sel = (np.abs(pz) > Z_THRESH) & (ts_arr >= m_start) & (ts_arr < m_end)
            if not sel.any() or sym not in idx:
                continue
            kts, kcl, kop = idx[sym]
            cand_ts = ts_arr[sel]
            keep = []
            last = None
            for t in cand_ts:
                if last is None or (t - last) >= MERGE_MS:
                    keep.append(t)
                last = t
            for ts in keep:
                i = _asof(ts_arr, ts)
                jb = _asof(kts, ts)
                j15 = _asof(kts, ts + 15 * 60_000)
                j60 = _asof(kts, ts + 60 * 60_000)
                j240 = _asof(kts, ts + 4 * 3_600_000)
                if jb < 0 or kts[jb] != ts:
                    continue
                c0 = kcl[jb]
                b15 = _asof(ts_arr, ts + 15 * 60_000)
                b60 = _asof(ts_arr, ts + 60 * 60_000)
                basis_rows.append({
                    "sym": sym, "ts": int(ts), "prem_z7": float(pz[i]),
                    "prem_close": float(gg.prem_close.to_numpy()[i]),
                    "dprem_15": (float(gg.prem_close.to_numpy()[b15] - gg.prem_close.to_numpy()[i])
                                 if b15 > i else np.nan),
                    "dprem_60": (float(gg.prem_close.to_numpy()[b60] - gg.prem_close.to_numpy()[i])
                                 if b60 > i else np.nan),
                    "ret_60": (kcl[j60] / c0 - 1.0) if (j60 > jb and c0) else np.nan,
                    "ret_240": (kcl[j240] / c0 - 1.0) if (j240 > jb and c0) else np.nan,
                    "bar_ret": (float(np.float32(kcl[jb]) / np.float32(kop[jb]) - 1.0)
                                if kop[jb] else np.nan)})
        # ---- listing drift (symbols first seen inside 2024) ----
        for sym, p in list(pending_drift.items()):
            if sym not in idx:
                continue
            kts, kcl, _kop = idx[sym]
            for h in DRIFT_DAYS:
                if not p["need"][h]:
                    continue
                tgt = p["t0"] + h * 86_400_000
                j = _asof(kts, tgt)
                if tgt <= m_end and j >= 0 and p["c0"]:
                    drift_rows.append({"sym": sym, "t0": p["t0"], "h_days": h,
                                       "ret": float(kcl[j] / p["c0"] - 1.0)})
                    p["need"][h] = False
            if not any(p["need"].values()):
                pending_drift.pop(sym)
        e1_data.release(e1_core.MONTHS_2024[mi - 1]) if mi > 0 else None
        log.info("families month %s fund=%d basis=%d drift=%d elapsed=%.0fs",
                 month, len(fund_rows), len(basis_rows), len(drift_rows), time.time() - t0)
        del kl, ba, idx, ba_idx
    out = {}
    for name, rows in (("e1_t4_funding_events", fund_rows),
                       ("e1_t5_basis_events", basis_rows),
                       ("e1_listing_drift", drift_rows),
                       ("e1_month_snap", snap_rows)):
        df = pd.DataFrame(rows)
        pq.write_table(pa.Table.from_pandas(df, preserve_index=False),
                       os.path.join(OUT, name + ".parquet"), compression="zstd")
        out[name] = len(df)
    life_df = pd.DataFrame([{"sym": s, "first_ts": v[0], "last_ts": v[1], "first_close": v[2]}
                            for s, v in life.items()])
    pq.write_table(pa.Table.from_pandas(life_df, preserve_index=False),
                   os.path.join(OUT, "e1_sym_life_2024.parquet"), compression="zstd")
    log.info("families pass done %s life=%d", out, len(life_df))
    return out


def _prem_z7(v):
    s = pd.Series(v)
    m = s.shift(1).rolling(7 * 1440, min_periods=1440).mean()
    sd = s.shift(1).rolling(7 * 1440, min_periods=1440).std()
    return ((s - m) / sd).to_numpy()


if __name__ == "__main__":
    run()
