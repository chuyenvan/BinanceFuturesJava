"""VZ E1 core - event engine for the 2024 exploration.

Builds the standard `crash` event set from vz-kline1m-2024 (+ basis1m-2024,
metrics5m 2024, funding 2024), computes features known at t_dec and forward
outcomes net of the EXEC bucket cost + 2-leg fee, and writes
  ~/vz_e1/out/e1_events_2024.parquet   (one row per event)
  ~/vz_e1/out/e1_panel_2024.parquet    (offset profile for H-A, T2)

Deterministic (fixed seed, no randomness) so two runs give the same md5.
Features use only data with ts <= t_dec (T1-V a).

The lake is sorted by (sym, ts) with one row group per symbol, so a month is
processed symbol by symbol (pass 1 = candidate minutes, pass 2 = per-symbol
feature frame). RSS stays low while Phase 1 runs.
"""
import argparse
import os
import time

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

import e1_data
from e1_common import (CRASH_BAR_RET, FIRST_TS_2024_MS, HORIZONS_MIN,
                       MERGE_GAP_MS, MIN_QUOTE_VOLUME, OUT, bucket_of, cost_of,
                       ensure_dirs, md5_file, setup_logging)

log = setup_logging("e1_core", "e1_core.log")

MONTHS_2024 = ["2024-%02d" % m for m in range(1, 13)]
KLINE_COLS = ["ts", "sym", "open", "high", "low", "close", "volume",
              "quote_volume", "n_trades", "taker_buy_quote", "active"]
BASIS_COLS = ["ts", "sym", "prem_close", "mark_close", "index_close"]
CAND_COLS = ["ts", "sym", "open", "close", "quote_volume", "active"]
LOOKBACK_MS = 7 * 86_400_000
FWD_MS = 4 * 3_600_000
PANEL_OFFS = list(range(-60, 241, 5))


def month_bounds(month):
    y, m = int(month[:4]), int(month[5:7])
    start = int(pd.Timestamp(year=y, month=m, day=1, tz="UTC").timestamp() * 1000)
    end = int(pd.Timestamp(year=y + (1 if m == 12 else 0),
                           month=1 if m == 12 else m + 1, day=1, tz="UTC").timestamp() * 1000)
    return start, end


def _asof(ts, ref):
    return int(np.searchsorted(ts, ref, side="right") - 1)


class SymIndex:
    """Row-group index for a (sym, ts)-sorted parquet file (1 row group = 1 sym)."""

    def __init__(self, path):
        self.path = path
        # rows listed in the dataset's anomalies.csv (validate/V3) are skipped here,
        # the single choke point every kline/basis read goes through
        self.bad = e1_data.anomalies_for_path(path)
        self.pf = pq.ParquetFile(path)
        md = self.pf.metadata
        self.nrg = md.num_row_groups
        self.offsets = np.concatenate(
            [[0], np.cumsum([md.row_group(i).num_rows for i in range(self.nrg)])]).astype(np.int64)
        col = pq.read_table(path, columns=["sym"]).column("sym").combine_chunks()
        if isinstance(col, pa.DictionaryArray):
            self.dict = np.array(col.dictionary.to_pylist(), dtype=object)
            codes = col.indices.to_numpy()
        else:
            vals = col.to_pandas().to_numpy()
            self.dict, codes = np.unique(vals, return_inverse=True)
        self.rg_sym = self.dict[codes[self.offsets[:self.nrg]]]
        tsmin = np.full(self.nrg, -1, dtype=np.int64)
        for i in range(self.nrg):
            st = md.row_group(i).column(0).statistics
            if st is not None and st.has_min_max:
                tsmin[i] = st.min
        self.rg_ts_min = tsmin

    def rgs_for(self, sym):
        return range(int(np.searchsorted(self.rg_sym, sym, side="left")),
                     int(np.searchsorted(self.rg_sym, sym, side="right")))

    def read_sym(self, sym, columns, ts_lo=None, ts_hi=None):
        rgs = list(self.rgs_for(sym))
        if not rgs:
            return None
        tabs = [self.pf.read_row_group(i, columns=columns) for i in rgs]
        d = pa.concat_tables(tabs).to_pandas()
        if ts_lo is not None:
            d = d[d.ts >= ts_lo]
        if ts_hi is not None:
            d = d[d.ts <= ts_hi]
        if self.bad and len(d):
            keep = np.fromiter(((str(s), int(t)) not in self.bad
                                for s, t in zip(d["sym"], d["ts"])), bool, len(d))
            if not keep.all():
                log.info("anomalies: dropped %d row(s) of %s", int((~keep).sum()), sym)
                d = d[keep]
        return d if len(d) else None


def compute_features(fr):
    """Causal features on one symbol's sorted frame (rollings look backwards)."""
    fr = fr.sort_values("ts", kind="stable").reset_index(drop=True)
    qv = fr.quote_volume.replace(0, np.nan)
    fr["taker_sell_share"] = 1.0 - fr.taker_buy_quote / qv
    fr["log_vol"] = np.log1p(fr.volume.clip(lower=0))
    for w in (5, 15):
        fr["tss_%d" % w] = fr.taker_sell_share.shift(1).rolling(w, min_periods=1).mean()
    fr["volz60"] = ((fr.log_vol - fr.log_vol.shift(1).rolling(60, min_periods=10).mean())
                    / fr.log_vol.shift(1).rolling(60, min_periods=10).std())
    for h in (15, 60, 240):
        fr["ret_pre_%d" % h] = fr.close / fr.close.shift(h) - 1.0
    pm = fr.prem_close.shift(1).rolling(7 * 1440, min_periods=1440).mean()
    ps = fr.prem_close.shift(1).rolling(7 * 1440, min_periods=1440).std()
    fr["prem_z7"] = (fr.prem_close - pm) / ps
    fr["mark_index_gap"] = fr.mark_close / fr.index_close - 1.0
    return fr


def load_metrics():
    df = pq.read_table(e1_data.metrics_year("2024"),
                       columns=["ts", "sym", "oi", "oi_value"]).to_pandas()
    df = df.sort_values(["sym", "ts"], kind="stable")
    out = {}
    for sym, g in df.groupby("sym", sort=False):
        out[sym] = (g.ts.to_numpy(np.int64), g.oi.to_numpy(np.float64),
                    g.oi_value.to_numpy(np.float64))
    log.info("metrics5m symbols=%d rows=%d", len(out), len(df))
    del df
    return out


def load_funding():
    df = pd.read_parquet(e1_data.funding_year("2024")).sort_values(["sym", "ts"], kind="stable")
    out = {}
    for sym, g in df.groupby("sym", sort=False):
        out[sym] = (g.ts.to_numpy(np.int64), g.rate.to_numpy(np.float64))
    log.info("funding symbols=%d rows=%d", len(out), len(df))
    del df
    return out


def _metrics_at(metrics, sym, ts):
    rec = metrics.get(sym)
    if rec is None:
        return None
    ts_a, oi_a, oiv_a = rec
    k = _asof(ts_a, ts)
    return None if k < 0 else (ts_a, oi_a, oiv_a, k)


def candidates(cur_index, m_start, m_end):
    cand = pq.read_table(cur_index.path, columns=CAND_COLS).to_pandas()
    cand = cand[(cand.ts >= m_start) & (cand.ts < m_end)]
    cand = cand[cand.active.fillna(False).astype(bool) & (cand.quote_volume >= MIN_QUOTE_VOLUME)]
    br32 = ((cand.close.astype(np.float32) - cand.open.astype(np.float32))
            / cand.open.astype(np.float32))
    cand = cand[br32 <= np.float32(CRASH_BAR_RET)].sort_values(["sym", "ts"], kind="stable")
    if cand.empty:
        return cand
    syms = cand.sym.to_numpy(); tss = cand.ts.to_numpy(np.int64)
    keep = np.zeros(len(cand), dtype=bool)
    ps, pt = None, None
    for i in range(len(cand)):
        if syms[i] != ps or (tss[i] - pt) >= MERGE_GAP_MS:
            keep[i] = True
        ps, pt = syms[i], tss[i]
    return cand[keep]


def month_dayvol(cur_index, m_start, m_end):
    """Per (symbol, UTC day) quote volume sum - liquidity terciles for T5."""
    t = pq.read_table(cur_index.path, columns=["ts", "sym", "quote_volume"]).to_pandas()
    t = t[(t.ts >= m_start) & (t.ts < m_end)]
    t["day"] = (t.ts // 86_400_000).astype(np.int64)
    g = t.groupby(["sym", "day"], as_index=False).quote_volume.sum()
    del t
    return g


def month_events(month, metrics, funding, indexes):
    m_start, m_end = month_bounds(month)
    kidx, _bidx = indexes["cur"]
    cand = candidates(kidx, m_start, m_end)
    log.info("month %s candidates=%d", month, len(cand))
    if cand.empty:
        return pd.DataFrame(), pd.DataFrame()
    rows, panel_rows = [], []
    for sym, grp in cand.groupby("sym", sort=False):
        kparts = []
        bparts = []
        for key, lo, hi in (("prev", m_start - LOOKBACK_MS, None),
                            ("cur", m_start - LOOKBACK_MS, None),
                            ("next", m_end, m_end + FWD_MS)):
            pair = indexes.get(key)
            if pair is None:
                continue
            sidx, bidx = pair
            d = sidx.read_sym(sym, KLINE_COLS, ts_lo=lo, ts_hi=hi)
            if d is not None:
                kparts.append(d)
            b = bidx.read_sym(sym, BASIS_COLS, ts_lo=lo, ts_hi=hi)
            if b is not None:
                bparts.append(b)
        if not kparts:
            continue
        kl = pd.concat(kparts, ignore_index=True)
        ba = pd.concat(bparts, ignore_index=True) if bparts else pd.DataFrame(columns=BASIS_COLS)
        fr = compute_features(kl.merge(ba, on=["sym", "ts"], how="left", sort=False))
        ts_a = fr.ts.to_numpy(np.int64)
        cl_a = fr.close.to_numpy(np.float64)
        hi_a = fr.high.to_numpy(np.float64)
        lo_a = fr.low.to_numpy(np.float64)
        pz_a = fr.prem_z7.to_numpy(np.float64)
        vz_a = fr.volz60.to_numpy(np.float64)
        tss_a = fr.taker_sell_share.to_numpy(np.float64)
        for ts in grp.ts.to_numpy(np.int64):
            k = int(np.searchsorted(ts_a, ts))
            if k >= len(ts_a) or ts_a[k] != ts:
                continue
            c0 = cl_a[k]
            out = {}
            for h in HORIZONS_MIN:
                jj = _asof(ts_a, ts + h * 60_000)
                out["gross_%d" % h] = (float(np.log(cl_a[jj] / c0))
                                       if jj > k and ts_a[jj] == ts + h * 60_000 and cl_a[jj] > 0
                                       else np.nan)
            for h, tag in ((60, "60"), (240, "240")):
                jj = _asof(ts_a, ts + h * 60_000)
                out["mfe_%s" % tag] = float(hi_a[k + 1:jj + 1].max() / c0 - 1.0) if jj > k else np.nan
                out["mae_%s" % tag] = float(lo_a[k + 1:jj + 1].min() / c0 - 1.0) if jj > k else np.nan
            r = fr.iloc[k]
            row = {"sym": sym, "ts": int(ts), "open": float(r.open), "close": float(r.close),
                   "high": float(r.high), "low": float(r.low),
                   "quote_volume": float(r.quote_volume),
                   "taker_sell_share": float(r.taker_sell_share),
                   "tss_5": float(r.tss_5), "tss_15": float(r.tss_15),
                   "volz60": float(r.volz60),
                   "ret_pre_15": float(r.ret_pre_15), "ret_pre_60": float(r.ret_pre_60),
                   "ret_pre_240": float(r.ret_pre_240),
                   "prem_close": float(r.prem_close), "prem_z7": float(r.prem_z7),
                   "mark_index_gap": float(r.mark_index_gap)}
            row.update(out)
            rows.append(row)
            for off in PANEL_OFFS:
                jj = _asof(ts_a, ts + off * 60_000)
                if jj < 0 or ts_a[jj] != ts + off * 60_000:
                    continue
                panel_rows.append((sym, int(ts), off,
                                   float(cl_a[jj] / c0 - 1.0) if c0 else np.nan,
                                   float(pz_a[jj]), float(vz_a[jj]), float(tss_a[jj])))
    ev = pd.DataFrame(rows)
    ev = add_metrics_funding(ev, metrics, funding)
    btc = kidx.read_sym("BTCUSDT", KLINE_COLS, ts_lo=m_start - LOOKBACK_MS, ts_hi=m_end + FWD_MS)
    ev = add_btc_rets(ev, btc)
    panel = pd.DataFrame(panel_rows, columns=["sym", "ts", "off", "ret_cum",
                                              "prem_close", "volz60", "tss"])
    panel["doi_cum"] = _panel_doi(panel, metrics)
    return ev, panel


def add_metrics_funding(ev, metrics, funding):
    n = len(ev)
    oi = np.full(n, np.nan); oiv = np.full(n, np.nan)
    d15 = np.full(n, np.nan); d60 = np.full(n, np.nan)
    frr = np.full(n, np.nan); mf = np.full(n, np.nan)
    for i, (s, ts) in enumerate(zip(ev.sym.to_numpy(), ev.ts.to_numpy(np.int64))):
        m = _metrics_at(metrics, s, ts)
        if m is not None:
            ts_a, oi_a, oiv_a, k = m
            oi[i] = oi_a[k]; oiv[i] = oiv_a[k]
            for h, out in ((15, d15), (60, d60)):
                k2 = _asof(ts_a, ts - h * 60_000)
                if k2 >= 0 and oi_a[k2] != 0:
                    out[i] = oi_a[k] / oi_a[k2] - 1.0
        f = funding.get(s)
        if f is not None:
            fts, frate = f
            k = _asof(fts, ts)
            if k >= 0:
                frr[i] = frate[k]
                nx = np.searchsorted(fts, ts, side="right")
                if nx < len(fts):
                    mf[i] = (fts[nx] - ts) / 60000.0
    ev["oi"] = oi; ev["oi_value"] = oiv
    ev["doi_15"] = d15; ev["doi_60"] = d60
    ev["funding_rate"] = frr; ev["mins_to_funding"] = mf
    return ev


def _panel_doi(panel, metrics):
    out = np.full(len(panel), np.nan)
    for i, (s, ts, off) in enumerate(zip(panel.sym.to_numpy(),
                                         panel.ts.to_numpy(np.int64),
                                         panel.off.to_numpy(np.int64))):
        rec = metrics.get(s)
        if rec is None:
            continue
        mts, moi, _ = rec
        kk = _asof(mts, ts + off * 60_000)
        k0 = _asof(mts, ts)
        if kk >= 0 and k0 >= 0 and moi[k0] != 0:
            out[i] = moi[kk] / moi[k0] - 1.0
    return out


def add_btc_rets(ev, btc):
    r15 = np.full(len(ev), np.nan); r60 = np.full(len(ev), np.nan)
    if btc is not None and len(btc):
        bts = btc.ts.to_numpy(np.int64); bcl = btc.close.to_numpy(np.float64)
        for i, ts in enumerate(ev.ts.to_numpy(np.int64)):
            k = _asof(bts, ts)
            if k < 0:
                continue
            for h, out in ((15, r15), (60, r60)):
                j = _asof(bts, ts - h * 60_000)
                if j >= 0 and bcl[j] > 0:
                    out[i] = bcl[k] / bcl[j] - 1.0
    ev["btc_ret_15"] = r15; ev["btc_ret_60"] = r60
    return ev


def _load_index(month, store):
    """Return (kline_index, basis_index) for a month, cached in `store`."""
    if month not in store:
        store[month] = (SymIndex(e1_data.kline_month(month)),
                        SymIndex(e1_data.basis_month(month)))
    return store[month]


# ------------------------------------------------------------------ multi-year engine
# Reuses the 2024 event definition (`candidates`) and feature code
# (`compute_features`, unchanged) to build one confirmation year from kline1m.
KLINE_COLS_NEED = ["ts", "sym", "open", "high", "low", "close", "volume",
                   "quote_volume", "taker_buy_quote", "active"]
FWD_MAX_MS = 1440 * 60_000  # 24h, so a Dec event's ts+1440' resolves inside the year


def year_months(year):
    return ["%04d-%02d" % (year, m) for m in range(1, 13)]


def _load_kline_index(month, store, fetch=True):
    """Kline-only SymIndex for a month, cached in `store` (no basis/metrics)."""
    if month not in store:
        store[month] = SymIndex(e1_data.month_path(month, "kline", fetch=fetch))
    return store[month]


def _features_kline(fr):
    """e1_core.compute_features on a kline-only frame (basis columns as NaN).

    B4 (V2_tss_reversal_q5) consumes only `tss_reversal` = taker_sell_share - tss_5,
    both from kline; the basis-derived columns stay NaN and are unused.
    """
    fr = fr.sort_values("ts", kind="stable").reset_index(drop=True)
    for c in ("prem_close", "mark_close", "index_close"):
        if c not in fr.columns:
            fr[c] = np.nan
    return compute_features(fr)


def month_events_year(month, indexes, lookback_ms):
    """Crash events for one month with net 60'/240'/1440' (real + stress)."""
    m_start, m_end = month_bounds(month)
    cand = candidates(indexes["cur"], m_start, m_end)
    if cand.empty:
        return pd.DataFrame()
    rows = []
    for sym, grp in cand.groupby("sym", sort=False):
        kparts = []
        for key, lo, hi in (("prev", m_start - lookback_ms, None),
                            ("cur", m_start - lookback_ms, None),
                            ("next", m_end, m_end + FWD_MAX_MS)):
            sidx = indexes.get(key)
            if sidx is None:
                continue
            d = sidx.read_sym(sym, KLINE_COLS_NEED, ts_lo=lo, ts_hi=hi)
            if d is not None:
                kparts.append(d)
        if not kparts:
            continue
        fr = _features_kline(pd.concat(kparts, ignore_index=True))
        ts_a = fr.ts.to_numpy(np.int64)
        cl_a = fr.close.to_numpy(np.float64)
        for ts in grp.ts.to_numpy(np.int64):
            k = int(np.searchsorted(ts_a, ts))
            if k >= len(ts_a) or ts_a[k] != ts:
                continue
            c0 = cl_a[k]
            r = fr.iloc[k]
            row = {"sym": sym, "ts": int(ts), "open": float(r.open), "close": float(c0),
                   "high": float(r.high), "low": float(r.low),
                   "quote_volume": float(r.quote_volume),
                   "taker_sell_share": float(r.taker_sell_share), "tss_5": float(r.tss_5)}
            row["tss_reversal"] = row["taker_sell_share"] - row["tss_5"]
            for h in (60, 240, 1440):
                jj = _asof(ts_a, ts + h * 60_000)
                row["gross_%d" % h] = (float(np.log(cl_a[jj] / c0))
                                       if jj > k and ts_a[jj] == ts + h * 60_000
                                       and cl_a[jj] > 0 and c0 > 0 else np.nan)
            rows.append(row)
    ev = pd.DataFrame(rows)
    if ev.empty:
        return ev
    ev["bar_ret"] = ev.close / ev.open - 1.0
    ev["bucket"] = [bucket_of(c, o) for c, o in zip(ev.close, ev.open)]
    for h in (60, 240, 1440):
        ev["net_%d" % h] = ev["gross_%d" % h] - [cost_of(b) for b in ev.bucket]
        ev["net_stress_%d" % h] = ev["gross_%d" % h] - [cost_of(b, True) for b in ev.bucket]
    ev["month"] = month
    ev["day"] = (ev.ts // 86_400_000).astype(np.int64)
    return ev


def build_year_events(year, lookback_days=30, prior_lookback=True, release=True,
                      fetch=True):
    """E1 crash events for one year, kline only, net 60'/240'/1440' (real + stress).

    `prior_lookback=False` keeps the feature frame inside `year` (used by the
    2024 smoke so no data outside 2024 is read). An event whose ts+1440' runs
    past the year end keeps net_1440 = NaN; the next year is never read.
    """
    months = year_months(year)
    lookback_ms = int(lookback_days * 86_400_000)
    indexes = {}
    parts = []
    for mi, month in enumerate(months):
        if mi == 0:
            prev = ("%04d-12" % (year - 1)) if prior_lookback else None
        else:
            prev = months[mi - 1]
        local = {}
        if prev is not None:
            local["prev"] = _load_kline_index(prev, indexes, fetch=fetch)
        local["cur"] = _load_kline_index(month, indexes, fetch=fetch)
        if mi + 1 < len(months):
            local["next"] = _load_kline_index(months[mi + 1], indexes, fetch=fetch)
        d = month_events_year(month, local, lookback_ms)
        if len(d):
            parts.append(d)
        if release and prev is not None:
            e1_data.release(prev)
            indexes.pop(prev, None)
        log.info("year %d %s events=%d", year, month, len(d))
    ev = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()
    if len(ev):
        ev = ev.sort_values(["ts", "sym"], kind="stable").reset_index(drop=True)
    return ev


def build(months=MONTHS_2024):
    ensure_dirs()
    t0 = time.time()
    log.info("loading metrics + funding")
    metrics = load_metrics()
    funding = load_funding()
    indexes = {}
    first_seen = {}
    events_parts, panel_parts, dayvol_parts = [], [], []
    for month in months:
        mi = MONTHS_2024.index(month)
        prev = MONTHS_2024[mi - 1] if mi > 0 else None
        nxt = MONTHS_2024[mi + 1] if mi < len(MONTHS_2024) - 1 else None
        local = {}
        if prev is not None:
            local["prev"] = _load_index(prev, indexes)
        local["cur"] = _load_index(month, indexes)
        if nxt is not None:
            local["next"] = _load_index(nxt, indexes)
        cur = local["cur"][0]
        for rg in range(cur.nrg):
            s = cur.rg_sym[rg]
            t = cur.rg_ts_min[rg]
            if t >= 0 and (s not in first_seen or t < first_seen[s]):
                first_seen[s] = int(t)
        ev, panel = month_events(month, metrics, funding, local)
        if len(ev):
            events_parts.append(ev)
            panel_parts.append(panel)
        dayvol_parts.append(month_dayvol(cur, *month_bounds(month)))
        log.info("month %s events=%d elapsed=%.1fs", month, len(ev), time.time() - t0)
        # release no-longer-needed files (keep cur for the next month's lookback)
        if prev is not None:
            e1_data.release(prev)
            indexes.pop(prev, None)
    ev = pd.concat(events_parts, ignore_index=True) if events_parts else pd.DataFrame()
    ev = ev.sort_values(["ts", "sym"], kind="stable").reset_index(drop=True)
    ev["bar_ret"] = ev.close / ev.open - 1.0
    ev["bucket"] = [bucket_of(c, o) for c, o in zip(ev.close, ev.open)]
    ev["month"] = pd.to_datetime(ev.ts, unit="ms", utc=True).dt.strftime("%Y-%m")
    ev["day"] = (ev.ts // 86_400_000).astype(np.int64)
    age, known = [], []
    for s, ts in zip(ev.sym.to_numpy(), ev.ts.to_numpy(np.int64)):
        f = first_seen.get(s)
        age.append((ts - f) / 86_400_000.0 if f is not None else np.nan)
        known.append(bool(f is not None and f > FIRST_TS_2024_MS))
    ev["sym_age_days"] = age
    ev["age_known"] = known
    for h in HORIZONS_MIN:
        ev["net_%d" % h] = ev["gross_%d" % h] - [cost_of(b) for b in ev.bucket]
        ev["net_stress_%d" % h] = ev["gross_%d" % h] - [cost_of(b, True) for b in ev.bucket]
    panel = pd.concat(panel_parts, ignore_index=True) if panel_parts else pd.DataFrame()
    dayvol = pd.concat(dayvol_parts, ignore_index=True) if dayvol_parts else pd.DataFrame()
    return ev, panel, dayvol


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--months", default=",".join(MONTHS_2024))
    ap.add_argument("--out-suffix", default="")
    args = ap.parse_args()
    months = [m for m in args.months.split(",") if m]
    ev, panel, dayvol = build(months)
    evp = os.path.join(OUT, "e1_events_2024%s.parquet" % args.out_suffix)
    panp = os.path.join(OUT, "e1_panel_2024%s.parquet" % args.out_suffix)
    dvp = os.path.join(OUT, "e1_dayvol_2024%s.parquet" % args.out_suffix)
    pq.write_table(pa.Table.from_pandas(ev, preserve_index=False), evp, compression="zstd")
    pq.write_table(pa.Table.from_pandas(panel, preserve_index=False), panp, compression="zstd")
    pq.write_table(pa.Table.from_pandas(dayvol, preserve_index=False), dvp, compression="zstd")
    log.info("wrote %s rows=%d md5=%s", evp, len(ev), md5_file(evp))
    log.info("wrote %s rows=%d md5=%s", panp, len(panel), md5_file(panp))
    log.info("events/month:\n%s", ev.groupby("month").size().to_string())
    log.info("bucket dist:\n%s", ev.groupby("bucket").size().to_string())
    return ev, panel


if __name__ == "__main__":
    main()
