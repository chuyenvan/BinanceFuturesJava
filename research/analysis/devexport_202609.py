#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PORT Python cua `ExportGateDataset.replayToCsv` (export DEV gate 15m v2) — **AUDIT-ONLY**.

Nguon su that (Java, khong sua):
  src/main/java/com/binance/chuyennd/ai_ml/features/export/gate/ExportGateDataset.java:138  (replayToCsv)
  src/main/java/com/binance/chuyennd/ai_ml/features/export/entry/ComprehensiveMarketFeatureExtractor.java
  src/main/java/com/binance/chuyennd/ai_ml/features/export/HistoryManager.java
  src/main/java/com/binance/chuyennd/tradecore/CoinRankManager.java

Pre-reg: docs/prereg/PREREG_DEVEXPORT_202609_AUDIT.md
Phat ra file: ts + 34 cot feature GIONG HET ban DEV (33 so + volatilityRegime, dung TEN/thu tu)
+ cot chan doan `md_src`. KHONG ghi label (khong can cho audit).

  python3 devexport_202609.py --start 20260701 --end 20260928 --out /path/out.csv \
      --cluster local|242 [--verify-csv ~/claudedata/gate15m_v2_full.csv] [--limit-days N]

CHI DOC Aerospike. Khong ghi/sua gi tren host nao.
"""
import argparse
import datetime
import gzip
import hashlib
import os
import struct
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import numpy as np

try:
    import aerospike
except Exception as e:  # pragma: no cover
    print("thieu module aerospike:", e); sys.exit(2)
try:
    import cramjam
except Exception as e:  # pragma: no cover
    print("thieu module cramjam:", e); sys.exit(2)

TZ7 = datetime.timezone(datetime.timedelta(hours=7))
MIN = 60_000
HOUR = 3_600_000
DAY = 86_400_000
MAXC = 1000
RING = 2048
MASK = 2047
CLEANUP_INTERVAL = 24 * HOUR
ZOMBIE_THRESHOLD = 4 * HOUR
WARMUP_HOURS = 48
RANK_MINUTES = 60          # CoinRankManager.number_minute_update
RANK_VOL_WINDOW = 720      # getSumVolume(symId, 720)
FUNDING_MAX_AGE = 24 * HOUR

# --- 34 cot feature cua ban DEV (dung TEN + thu tu) ---
CSV_FEAT_NAMES = [
    "momentum1M", "momentum5M", "momentum15M", "momentum1H", "momentum4H", "momentum24H",
    "momentumAcceleration", "trendStrengthETH", "trendConsistency",
    "volatility1M", "volatility15M", "volatility1H", "volatility24H", "volatilityTermStructure",
    "volatilityRegime",
    "advanceDeclineRatio", "percentAboveMA20", "volumeRatioUpDown", "marketBreadthStrength",
    "btcDominance", "rsi14", "volumeSpike", "distMA20",
    "basketMomentum15M", "basketMomentum1H", "basketRsi14", "basketVolSpike",
    "fundingRateRaw", "fundingRateAvg24H", "fundingRateTrend",
    "hourOfDay", "dayOfWeek", "weekOfMonth", "monthOfYear",
]
assert len(CSV_FEAT_NAMES) == 34

V3FULL = [  # 33 feature theo thu tu model (LIVE dump)
    "momentum1M", "momentum5M", "momentum15M", "momentum1H", "momentum4H", "momentum24H",
    "momentumAcceleration", "trendStrengthETH", "trendConsistency",
    "volatility1M", "volatility15M", "volatility1H", "volatility24H", "volatilityTermStructure",
    "advanceDeclineRatio", "percentAboveMA20", "volumeRatioUpDown", "marketBreadthStrength",
    "btcDominance", "rsi14", "volumeSpike", "distMA20",
    "fundingRateRaw", "fundingRateAvg24H", "fundingRateTrend",
    "hourOfDay", "dayOfWeek", "weekOfMonth", "monthOfYear",
    "basketMomentum15M", "basketMomentum1H", "basketRsi14", "basketVolSpike",
]
assert len(V3FULL) == 33


# --------------------------- Aerospike ---------------------------
class Store:
    def __init__(self, cluster, pool=16):
        self.cluster = cluster
        if cluster == "local":
            self.client = aerospike.client({"hosts": [("127.0.0.1", 3222)]}).connect()
            self.kline_ns, self.fund_ns, self.md_ns = "test", "test", "test"
        elif cluster == "242":
            self.client = aerospike.client({"hosts": [("103.157.218.242", 3222)],
                                            "policies": {"timeout": 8000, "max_retries": 2}}).connect()
            self.kline_ns, self.fund_ns, self.md_ns = "ticker", "ticker", None
        else:
            raise ValueError(cluster)
        self.pool = ThreadPoolExecutor(max_workers=pool)
        self._local_cli = None

    def local(self):
        if self._local_cli is None:
            self._local_cli = aerospike.client({"hosts": [("127.0.0.1", 3222)],
                                                "policies": {"timeout": 4000}}).connect()
        return self._local_cli

    def close(self):
        try:
            self.pool.shutdown(wait=False)
            self.client.close()
            if self._local_cli is not None:
                self._local_cli.close()
        except Exception:
            pass

    def get_kline_day(self, day_start_ms, day_count=1440):
        """Tra ve dict ts->bytes bin 'data' cho 1 ngay (1440 phut, GMT+7)."""
        base = datetime.datetime.fromtimestamp(day_start_ms / 1000, TZ7)
        keys = [(base + datetime.timedelta(minutes=i)).strftime("%Y%m%d-%H%M") for i in range(day_count)]
        cli, ns = self.client, self.kline_ns

        def one(k):
            try:
                r = cli.get((ns, "kline_1m_opt", k))
                return (k, r[2]["data"]) if r else (k, None)
            except Exception:
                return (k, None)

        out = {}
        for k, v in self.pool.map(one, keys):
            if v is not None:
                out[k] = v
        return out

    def get_market_data_day(self, day_start_ms, day_count=1440):
        # market_data_object CHI co tren cum Oracle-local (ns test) — doc tu do bat ke cluster kline
        base = datetime.datetime.fromtimestamp(day_start_ms / 1000, TZ7)
        keys = [(base + datetime.timedelta(minutes=i)).strftime("%Y%m%d-%H%M") for i in range(day_count)]
        cli, ns = self.local(), "test"

        def one(k):
            try:
                r = cli.get((ns, "market_data_object", k))
                if not r:
                    return (k, None)
                d = r[2].get("data")
                if not d or len(d) < 12:
                    return (k, None)
                return (k, struct.unpack_from(">fff", d, 0))
            except Exception:
                return (k, None)

        out = {}
        for k, v in self.pool.map(one, keys):
            if v is not None:
                out[k] = v
        return out

    def get_funding_map(self, symbol, prefer_local=False):
        """Tra ve (times:int64[], rates:float64[]) hoac None."""
        for ns, cli in self._fund_candidates(prefer_local):
            try:
                r = cli.get((ns, "funding_data", symbol))
                if not r:
                    continue
                d = r[2].get("f_data")
                if not d:
                    continue
                import json
                js = bytes(cramjam.snappy.decompress_raw(d))
                m = json.loads(js)
                if not m:
                    continue
                ts = np.fromiter((int(k) for k in m.keys()), dtype=np.int64, count=len(m))
                vs = np.fromiter((float(v) for v in m.values()), dtype=np.float64, count=len(m))
                o = np.argsort(ts)
                return ts[o], vs[o]
            except Exception:
                continue
        return None

    def _fund_candidates(self, prefer_local):
        loc = self.local()
        cands = [("test", loc)]
        if self.cluster == "242":
            cands.append(("ticker", self.client))
        if prefer_local:
            cands.reverse()
        return cands

    def get_symbol_mapper(self):
        for ns, cli in [("test", self.local()), ("test", self.client), ("ticker", self.client)]:
            try:
                r = cli.get((ns, "symbol_mapper", "global_id_map"))
                if r:
                    return dict(r[2]["data"])
            except Exception:
                pass
        return {}


# --------------------------- protobuf parse ---------------------------
def _rv(buf, i):
    r = 0; s = 0
    while True:
        x = buf[i]; i += 1
        r |= (x & 0x7F) << s
        if not x & 0x80:
            return r, i
        s += 7


def parse_minute(data_bytes):
    """Tra ve (syms:list[str], arr:numpy float32 (n,5) [open,high,low,close,usdt]).

    Proto3: field co gia tri 0.0 KHONG duoc serialize => KHONG the khop mau tag co dinh;
    phai field-walk thuc su (giong convertProtoMapToJavaMap/getTickersMap cua Java).
    """
    dec = bytes(cramjam.snappy.decompress_raw(data_bytes))
    buf = memoryview(dec)
    n = len(buf)
    i = 0
    syms = []
    vals = []
    unpack = struct.unpack_from
    while i < n:
        tag, i = _rv(buf, i)
        if tag == 0x0A:
            ln, i = _rv(buf, i)
            end = i + ln
            j = i
            key = None
            arr = None
            while j < end:
                t, j = _rv(buf, j)
                fn = t >> 3
                w = t & 7
                if fn == 1 and w == 2:
                    kl, j = _rv(buf, j)
                    key = bytes(buf[j:j + kl]).decode()
                    j += kl
                elif fn == 2 and w == 2:
                    vl, j = _rv(buf, j)
                    vb = buf[j:j + vl]
                    j += vl
                    a0 = a1 = a2 = a3 = a4 = 0.0
                    k = 0
                    while k < vl:
                        ft, k = _rv(vb, k)
                        f2 = ft >> 3
                        ww = ft & 7
                        if ww == 5:
                            v = unpack("<f", vb, k)[0]; k += 4
                            if f2 == 1: a0 = v
                            elif f2 == 2: a1 = v
                            elif f2 == 3: a2 = v
                            elif f2 == 4: a3 = v
                            elif f2 == 5: a4 = v
                        elif ww == 0:
                            _, k = _rv(vb, k)
                        elif ww == 2:
                            l2, k = _rv(vb, k); k += l2
                        elif ww == 1:
                            k += 8
                        else:
                            break
                    arr = (a0, a1, a2, a3, a4)
                elif w == 0:
                    _, j = _rv(buf, j)
                elif w == 2:
                    l2, j = _rv(buf, j)
                    j += l2
                elif w == 5:
                    j += 4
                elif w == 1:
                    j += 8
                else:
                    break
            i = end
            if key is not None and arr is not None:
                vals.extend(arr)
                syms.append(key if key.endswith("USDT") else key + "USDT")
        else:
            w = tag & 7
            if w == 2:
                l3, i = _rv(buf, i); i += l3
            elif w == 0:
                _, i = _rv(buf, i)
            elif w == 5:
                i += 4
            elif w == 1:
                i += 8
            else:
                break
    if not syms:
        return [], np.zeros((0, 5), dtype=np.float32)
    arr2 = np.array(vals, dtype=np.float32).reshape(-1, 5)
    return syms, arr2


# --------------------------- Engine ---------------------------
class Engine:
    def __init__(self, mapper):
        self.str2id = dict(mapper)
        self.id2str = {v: k for k, v in mapper.items()}
        self.counter = max(mapper.values()) if mapper else 0
        self.ST = np.zeros((MAXC, RING), dtype=np.int64)
        self.OP = np.zeros((MAXC, RING), dtype=np.float32)
        self.HI = np.zeros((MAXC, RING), dtype=np.float32)
        self.LO = np.zeros((MAXC, RING), dtype=np.float32)
        self.CL = np.zeros((MAXC, RING), dtype=np.float32)
        self.VL = np.zeros((MAXC, RING), dtype=np.float32)
        self.HEAD = np.zeros(MAXC, dtype=np.int64)
        self.LASTUPD = np.zeros(MAXC, dtype=np.int64)
        self.GAPFREE = np.ones(MAXC, dtype=bool)
        self.LASTCLEAN = -1
        # rank
        self.top_ids = np.zeros(0, dtype=np.int64)
        self.last_interval = -1
        # funding cache
        self.fund = {}          # sym -> (ts[], rate[])
        self.fund_hour = {}     # (sym, hour_idx) -> (raw, avg24)
        self.fund_cache_t0 = None
        # market data per minute
        self.md = {}

    # --- mapper ---
    def ids_for(self, syms):
        s2i = self.str2id
        ids = np.empty(len(syms), dtype=np.int64)
        new = False
        for k, s in enumerate(syms):
            v = s2i.get(s)
            if v is None:
                self.counter += 1
                v = self.counter
                s2i[s] = v
                self.id2str[v] = s
                new = True
            ids[k] = v
        return ids, new

    # --- history ---
    def update(self, ts, syms, arr):
        ids, _ = self.ids_for(syms)
        keep = ids < MAXC
        if not keep.all():
            ids = ids[keep]; arr = arr[keep]
        if len(ids) == 0:
            return ids
        arr = arr.astype(np.float32, copy=False)
        h = self.HEAD[ids]
        lastslot = (h - 1) & MASK
        same = (h > 0) & (self.ST[ids, lastslot] == ts)
        h = h - same
        slot = h & MASK
        self.ST[ids, slot] = ts
        self.OP[ids, slot] = arr[:, 0]
        self.HI[ids, slot] = arr[:, 1]
        self.LO[ids, slot] = arr[:, 2]
        self.CL[ids, slot] = arr[:, 3]
        self.VL[ids, slot] = arr[:, 4]
        self.HEAD[ids] = h + 1
        self.LASTUPD[ids] = ts
        prev = (h - 1) & MASK
        gap = (h > 0) & (self.ST[ids, prev] + MIN != ts)
        if gap.any():
            self.GAPFREE[ids[gap]] = False
        # cleanup zombie (giong checkAndCleanup/cleanupZombieCoins)
        if self.LASTCLEAN == -1:
            self.LASTCLEAN = ts
        elif ts - self.LASTCLEAN >= CLEANUP_INTERVAL:
            dead = (self.HEAD > 0) & (ts - self.LASTUPD >= ZOMBIE_THRESHOLD)
            if dead.any():
                self.HEAD[dead] = 0
                self.LASTUPD[dead] = 0
                self.GAPFREE[dead] = True
            self.LASTCLEAN = ts
        return ids

    # --- ring helpers ---
    def _pos(self, ids, k):
        """idx (n,k) cua k nen moi nhat + valid mask."""
        h = self.HEAD[ids]
        j = np.arange(k)
        idx = (h[:, None] - 1 - j[None, :]) & MASK
        valid = h[:, None] > j[None, :]
        return idx, valid

    def latest_close(self, ids):
        h = self.HEAD[ids]
        ok = h > 0
        c = np.zeros(len(ids), dtype=np.float64)
        idx = (h - 1) & MASK
        c[ok] = self.CL[ids[ok], idx[ok]]
        return c, ok

    def ret_bulk(self, ids, minutes):
        """getReturn: (close_now - price_at(now-minutes))/price_at ; 0.0 neu thieu."""
        n = len(ids)
        out = np.zeros(n, dtype=np.float64)
        if n == 0:
            return out
        h = self.HEAD[ids].astype(np.int64)
        cnt = np.minimum(h, RING).astype(np.float64)
        nz = h > 0
        cur_slot = (h - 1) & MASK
        cur = np.where(nz, self.CL[ids, cur_slot], 0.0).astype(np.float64)
        j = minutes
        idx = (h - 1 - j) & MASK
        ok = nz & (cur > 0) & (j < cnt)
        past = np.zeros(n, dtype=np.float64)
        past[ok] = self.CL[ids[ok], idx[ok]]
        ok &= past > 0
        out[ok] = (cur[ok] - past[ok]) / past[ok]
        # fallback cho symbol co gap
        bad = np.where(~self.GAPFREE[ids] & nz)[0]
        for b in bad:
            i = int(ids[b])
            p = self._price_at_scan(i, int(self.ST[i, (int(h[b]) - 1) & MASK]) - minutes * MIN)
            if p is not None and p > 0 and cur[b] > 0:
                out[b] = (cur[b] - p) / p
            else:
                out[b] = 0.0
        return out

    def _price_at_scan(self, i, target):
        h = int(self.HEAD[i])
        cnt = int(min(h, RING))
        if cnt == 0:
            return None
        idx = (h - 1 - np.arange(cnt)) & MASK
        st = self.ST[i, idx]
        m = st <= target
        if not m.any():
            return None
        p = int(np.argmax(m))
        if target - int(st[p]) > 1_800_000:
            return None
        return float(self.CL[i, idx[p]])

    def sumv_bulk(self, ids, minutes):
        n = len(ids)
        if n == 0:
            return np.zeros(0, dtype=np.float64)
        h = self.HEAD[ids]
        cnt = np.minimum(h, RING)
        lb = np.minimum(cnt, minutes)
        out = np.zeros(n, dtype=np.float64)
        for j in range(int(lb.max()) if n else 0):
            sel = lb > j
            if not sel.any():
                break
            ii = ids[sel]
            sl = (h[sel] - 1 - j) & MASK
            out[sel] += self.VL[ii, sl].astype(np.float64)
        return out

    def avgv_bulk(self, ids, periods):
        n = len(ids)
        h = self.HEAD[ids]
        cnt = np.minimum(h, RING)
        ok = cnt >= periods
        out = np.zeros(n, dtype=np.float64)
        if not ok.any():
            return out
        # Java: avg = mean cua cac bar ơ vi tri 1..periods (bo nen hien tai, startIndex=head-2)
        idx, valid = self._pos(ids, periods + 1)
        jj = np.arange(periods + 1)
        absidx_ok = ((h[:, None] - 1 - jj[None, :]) >= 0) & valid & (jj[None, :] >= 1)
        v = np.where(absidx_ok, self.VL[ids[:, None], idx], 0.0).astype(np.float64)
        cntv = absidx_ok.sum(axis=1)
        s = v.sum(axis=1)
        res = np.where(cntv > 0, s / np.maximum(cntv, 1), 0.0)
        out[ok] = res[ok]
        return out

    def ma_bulk(self, ids, periods):
        n = len(ids)
        h = self.HEAD[ids]
        cnt = np.minimum(h, RING)
        ok = cnt >= periods
        out = np.full(n, np.nan, dtype=np.float64)
        if not ok.any():
            return out
        idx, valid = self._pos(ids, periods)
        mat = np.where(valid, self.CL[ids[:, None], idx], np.float32(0.0)).astype(np.float32)
        # CO Y: cong float32 TUAN TU (giong Java `sum += priceClose`), KHONG dung pairwise sum
        # cua numpy — vi percentAboveMA20 la mot PHEP DEM, lech 1e-8 o margin se doi ket qua dem.
        seq = np.zeros(n, dtype=np.float32)
        for j in range(periods):
            seq = (seq + mat[:, j]).astype(np.float32)
        res = (seq / np.float32(periods)).astype(np.float64)
        out[ok] = res[ok]
        return out

    def vol_bulk(self, ids, periods):
        n = len(ids)
        h = self.HEAD[ids]
        cnt = np.minimum(h, RING)
        out = np.zeros(n, dtype=np.float64)
        ok = cnt >= 5
        if not ok.any():
            return out
        m = np.minimum(cnt, periods).astype(np.int64)
        kmax = int(m.max())
        if kmax < 2:
            return out
        idx, valid = self._pos(ids, kmax)          # idx[:,k] = nen cach hien tai k
        cl = np.where(valid, self.CL[ids[:, None], idx], np.nan).astype(np.float64)
        # r_k = (close[pos k-1] - close[pos k]) / close[pos k], k = 1..n-1
        newer = cl[:, :-1]
        older = cl[:, 1:]
        kk = np.arange(1, kmax)[None, :]
        used = (kk < m[:, None])
        r = (newer - older) / np.where(older > 0, older, np.nan)
        r = np.where(used & np.isfinite(r), r, np.nan)
        c = np.sum(~np.isnan(r), axis=1)
        s = np.nansum(r, axis=1)
        ss = np.nansum(r * r, axis=1)
        var = np.where(c > 1, (ss - (s * s) / np.maximum(c, 1)) / np.maximum(c - 1, 1), np.nan)
        res = np.sqrt(np.maximum(var, 0.0))
        res = np.where(c < 2, 0.0, res)
        out[ok] = res[ok]
        return np.nan_to_num(out, nan=0.0)

    def rsi_bulk(self, ids, period=14):
        n = len(ids)
        h = self.HEAD[ids]
        cnt = np.minimum(h, RING)
        out = np.full(n, 50.0, dtype=np.float64)
        ok = cnt > period
        if not ok.any():
            return out
        idx, valid = self._pos(ids, period + 1)
        cl = np.where(valid, self.CL[ids[:, None], idx], np.nan).astype(np.float64)
        newer = cl[:, :-1]
        older = cl[:, 1:]
        ch = newer - older
        gain = np.nansum(np.where(ch > 0, ch, 0.0), axis=1)
        loss = np.nansum(np.where(ch < 0, -ch, 0.0), axis=1)
        ag = gain / period
        al = loss / period
        r = np.where(al == 0, 100.0, np.where(ag / np.maximum(al, 1e-30) >= 0,
                                               100.0 - 100.0 / (1.0 + ag / np.where(al == 0, np.nan, al)), 50.0))
        r = np.where(al == 0, 100.0, 100.0 - 100.0 / (1.0 + ag / np.where(al == 0, np.nan, al)))
        r = np.nan_to_num(r, nan=50.0)
        out[ok] = r[ok]
        return out

    # --- CoinRankManager ---
    def update_ranking(self, ts, active_ids):
        if len(active_ids) == 0:
            return
        vols = self.sumv_bulk(active_ids, RANK_VOL_WINDOW).astype(np.float32)
        names = [self.id2str.get(int(i), "") for i in active_ids]
        order = sorted(range(len(active_ids)), key=lambda k: (-float(vols[k]), names[k]))
        total = len(order)
        top_n = total // 2
        self.top_ids = active_ids[np.array(order[:top_n], dtype=np.int64)] if top_n else np.zeros(0, dtype=np.int64)
        self.last_interval = ts // (RANK_MINUTES * MIN)

    def check_rank(self, ts, active_ids):
        if self.last_interval < 0 or len(self.top_ids) == 0:
            self.update_ranking(ts, active_ids)
            return
        key = ts // (RANK_MINUTES * MIN)
        if (ts // MIN) % RANK_MINUTES == 0 and key > self.last_interval:
            self.update_ranking(ts, active_ids)

    # --- funding ---
    def load_fund(self, store, sym):
        if sym in self.fund:
            return self.fund[sym]
        v = store.get_funding_map(sym)
        self.fund[sym] = v
        return v

    def fund_at(self, store, sym, ts, history=None):
        """(value, valid).  value=0.0 khi cach >24h; valid=False khi khong co record."""
        m = history if history is not None else self.load_fund(store, sym)
        if m is None:
            return None
        tarr, rarr = m
        i = int(np.searchsorted(tarr, ts, side="right")) - 1
        if i < 0:
            return None
        if ts - int(tarr[i]) > FUNDING_MAX_AGE:
            return 0.0
        return float(rarr[i])

    def fund_feats(self, store, basket_ids, ts):
        cur_sum = 0.0
        avg_sum = 0.0
        valid = 0
        for i in basket_ids:
            sym = self.id2str.get(int(i))
            if sym is None:
                continue
            m = self.load_fund(store, sym)
            if m is None:
                continue
            c = self.fund_at(store, sym, ts, m)
            if c is None:
                continue
            s24 = 0.0
            c24 = 0
            for k in range(0, 25, 4):
                v = self.fund_at(store, sym, ts - k * HOUR, m)
                if v is not None:
                    s24 += v
                    c24 += 1
            cur_sum += c
            avg_sum += (s24 / c24) if c24 > 0 else c
            valid += 1
        if valid > 0:
            raw = cur_sum / valid
            avg = avg_sum / valid
        else:
            raw = 0.0
            avg = 0.0
        return raw, avg, raw - avg


def time_feats(ts):
    c = datetime.datetime.fromtimestamp(ts / 1000, TZ7)
    # Calendar.DAY_OF_WEEK: Sun=1..Sat=7 ; WEEK_OF_MONTH: tuan bat dau Chu nhat
    dow = (c.weekday() + 1) % 7 + 1
    first = c.replace(day=1)
    wom = ((c.day + ((first.weekday() + 1) % 7)) - 1) // 7 + 1
    return c.hour, dow, wom, c.month


def fnum(v):
    if v is None:
        return "0.000000"
    v = float(v)
    if v != v or v in (float("inf"), float("-inf")):
        return "0.000000"
    return "%.8f" % v


def run(args):
    store = Store(args.cluster)
    mapper = store.get_symbol_mapper()
    if not mapper:
        print("KHONG doc duoc symbol_mapper -> dung"); return 3
    eng = Engine(mapper)
    print("[init] mapper=%d symbols | cluster=%s | %s -> %s" % (len(mapper), args.cluster,
                                                                args.start, args.end))

    start_ms = int(datetime.datetime.strptime(args.start, "%Y%m%d").replace(tzinfo=TZ7).timestamp() * 1000)
    end_ms = int(datetime.datetime.strptime(args.end, "%Y%m%d").replace(tzinfo=TZ7).timestamp() * 1000) + DAY - 1
    warm_ms = start_ms - WARMUP_HOURS * HOUR

    # MD chi co tren cluster local, va chi toi 2026-08-13
    MD_LAST = int(datetime.datetime(2026, 8, 13, 23, 59, tzinfo=TZ7).timestamp() * 1000)

    # Giong Java: Utils.getDate(ms) = (ms / TIME_DAY) * TIME_DAY  => bucket theo NGAY UTC
    day = (start_ms - WARMUP_HOURS * HOUR) // DAY * DAY
    last_day = (end_ms // DAY) * DAY
    fh = gzip.open(args.out, "wt") if args.out.endswith(".gz") else open(args.out, "w")
    fh.write("ts," + ",".join(CSV_FEAT_NAMES) + ",md_src\n")
    nrows = 0
    ndays = 0
    t0 = time.time()
    d = day
    while d <= last_day:
        tday = time.time()
        kl = store.get_kline_day(d)
        md = store.get_market_data_day(d) if (d <= MD_LAST) else {}
        parsed = {}
        for k, v in kl.items():
            ts = None
            try:
                ts = int(datetime.datetime.strptime(k, "%Y%m%d-%H%M").replace(tzinfo=TZ7).timestamp() * 1000)
            except Exception:
                continue
            parsed[ts] = v
        for ts in sorted(parsed.keys()):
            syms, arr = parse_minute(parsed[ts])
            if not syms:
                continue
            active = eng.update(ts, syms, arr)
            eng.check_rank(ts, active)
            if ts < start_ms or ts > end_ms:
                continue
            rate = md.get(datetime.datetime.fromtimestamp(ts / 1000, TZ7).strftime("%Y%m%d-%H%M"))
            row = features_row(eng, store, ts, syms, arr, rate)
            fh.write(",".join(row) + "\n")
            nrows += 1
        ndays += 1
        if ndays % 5 == 0 or ndays == 1:
            print("  day %s rows=%d el=%.0fs (day %.1fs)" % (
                datetime.datetime.fromtimestamp(d / 1000, TZ7).strftime("%Y-%m-%d"), nrows,
                time.time() - t0, time.time() - tday), flush=True)
        d += DAY
    fh.close()
    store.close()
    print("[done] rows=%d days=%d el=%.0fs -> %s" % (nrows, ndays, time.time() - t0, args.out))
    return 0


def features_row(eng, store, ts, syms, arr, rate):
    out = {}
    md_src = 1 if rate is not None else 0
    m1 = float(rate[0]) if rate is not None else 0.0
    m15 = float(rate[2]) if rate is not None else 0.0
    bid = eng.str2id.get("BTCUSDT")
    eid = eng.str2id.get("ETHUSDT")
    btc = np.array([bid], dtype=np.int64)
    m5 = float(eng.ret_bulk(btc, 5)[0])
    m1h = float(eng.ret_bulk(btc, 60)[0])
    m4h = float(eng.ret_bulk(btc, 240)[0])
    m24h = float(eng.ret_bulk(btc, 1440)[0])
    eth1h = float(eng.ret_bulk(np.array([eid], dtype=np.int64), 60)[0])
    v1m = float(eng.vol_bulk(btc, 3)[0])
    v15 = float(eng.vol_bulk(btc, 15)[0])
    v1h = float(eng.vol_bulk(btc, 60)[0])
    v24 = float(eng.vol_bulk(btc, 1440)[0])
    term = (v1h / v24) if v24 != 0 else 0.0
    regime = "HIGH" if v1h > 0.01 else ("LOW" if v1h < 0.002 else "NORMAL")
    rsi = float(eng.rsi_bulk(btc)[0])
    curvol = float(eng.sumv_bulk(btc, 1)[0])
    avgvol = float(eng.avgv_bulk(btc, 20)[0])
    vspike = (curvol / avgvol) if avgvol > 0 else 1.0
    ma20 = float(eng.ma_bulk(btc, 20)[0])
    close, _ = eng.latest_close(btc)
    close = float(close[0])
    dist = ((close - ma20) / ma20) if (ma20 == ma20 and ma20 > 0) else 0.0

    # breadth tren targetBasket
    basket = eng.top_ids
    k_map = dict(zip(syms, range(len(syms))))
    if len(basket) == 0:
        adr, pma, vr, mbs, bdom = 0.0, 0.5, 0.0, 0.5, 0.0
    else:
        bnames = [eng.id2str.get(int(i), "") for i in basket]
        present = [n for n in bnames if n in k_map]
        sel = [k_map[n] for n in present]
        if sel:
            op = arr[sel, 0].astype(np.float64)
            cl = arr[sel, 3].astype(np.float64)
            vol = arr[sel, 4].astype(np.float64)
            up = cl > op
            dn = cl < op
            total = len(sel)
            upc = int(up.sum()); dnc = int(dn.sum())
            upvol = float(vol[up].sum()); dnvol = float(vol[dn].sum())
            bid_p = np.array([eng.str2id[n] for n in present], dtype=np.int64)
            ma = eng.ma_bulk(bid_p, 20)
            above = int(np.nansum((ma == ma) & (cl > ma)))
            adr = (upc / dnc) if dnc > 0 else 10.0
            vr = (upvol / dnvol) if dnvol > 0 else 10.0
            mbs = (upc / total) if total > 0 else 0.5
            pma = (above / total) if total > 0 else 0.5
            bvol = 0.0
            if "BTCUSDT" in k_map:
                bvol = float(arr[k_map["BTCUSDT"], 4])
            bdom = (bvol / (upvol + dnvol)) if (upvol + dnvol) > 0 else 0.0
        else:
            adr, pma, vr, mbs, bdom = 0.0, 0.5, 0.0, 0.5, 0.0

    # basket technical
    if len(basket) == 0:
        b15, b1h, brsi, bvs = m15, m1h, rsi, vspike
    else:
        brs = eng.rsi_bulk(basket)
        b15v = eng.ret_bulk(basket, 15)
        b1hv = eng.ret_bulk(basket, 60)
        bcur = eng.sumv_bulk(basket, 1)
        bavg = eng.avgv_bulk(basket, 20)
        bvs_v = np.where(bavg > 0, bcur / np.where(bavg > 0, bavg, 1.0), 1.0)
        nb = len(basket)
        brsi = float(brs.mean())
        b15 = float(b15v.mean())
        b1h = float(b1hv.mean())
        bvs = float(bvs_v.mean())
        if nb == 0:
            b15, b1h, brsi, bvs = m15, m1h, rsi, vspike
    fraw, favg, ftr = eng.fund_feats(store, basket if len(basket) else btc, ts)
    hh, dow, wom, moy = time_feats(ts)
    vals = {
        "momentum1M": m1, "momentum5M": m5, "momentum15M": m15, "momentum1H": m1h,
        "momentum4H": m4h, "momentum24H": m24h, "momentumAcceleration": m5 - m15,
        "trendStrengthETH": eth1h, "trendConsistency": 1.0 if m5 * m1h > 0 else -1.0,
        "volatility1M": v1m, "volatility15M": v15, "volatility1H": v1h, "volatility24H": v24,
        "volatilityTermStructure": term, "volatilityRegime": regime,
        "advanceDeclineRatio": adr, "percentAboveMA20": pma, "volumeRatioUpDown": vr,
        "marketBreadthStrength": mbs, "btcDominance": bdom, "rsi14": rsi, "volumeSpike": vspike,
        "distMA20": dist, "basketMomentum15M": b15, "basketMomentum1H": b1h,
        "basketRsi14": brsi, "basketVolSpike": bvs, "fundingRateRaw": fraw,
        "fundingRateAvg24H": favg, "fundingRateTrend": ftr,
        "hourOfDay": hh, "dayOfWeek": dow, "weekOfMonth": wom, "monthOfYear": moy,
    }
    row = [str(ts)]
    for nm in CSV_FEAT_NAMES:
        v = vals[nm]
        row.append(v if isinstance(v, str) else fnum(v))
    row.append(str(md_src))
    return row


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--cluster", default="local", choices=["local", "242"])
    return run(ap.parse_args())


if __name__ == "__main__":
    sys.exit(main())
