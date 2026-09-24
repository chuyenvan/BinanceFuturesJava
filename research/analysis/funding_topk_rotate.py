#!/usr/bin/env python3
"""FUNDING_TOPK_ROTATE — sinh grid moc 8h cho luat quay vong LONG top-K funding nho nhat.

Pre-reg: docs/prereg/PREREG_FUNDING_TOPK_ROTATE.md (commit 55b8280, chot TRUOC khi chay; KHONG sua thiet ke).

Moc 8h (00/08/16 UTC): r % 480 == 0 (phut tuong doi so voi BASE=2021-01-01).
Moi dong = (moc r, symbol) voi: f_entry = rate event funding cuoi cung co ts <= r*60000 (causal,
predictor); raw = close(r+480)/close(r)-1; slip = 0.5*(high-low)/close tai nen moc r;
f_cum = cum event co ts in (r*60000, (r+480)*60000]  (event tai moc exit DUOC tinh — convention
vong truoc (m_e, m_x]); delist flag.

Neo MOM15 (§7b): dung lai /tmp/funding_factor/cache2.npz (total_rows, fire8, M-LEVEL rows) va tinh
lai net M-LEVEL 24h (ref +1,6690% DEV @0,10%).

Thuan Python, 0-sim, khong Java, khong push. Chi DOC raw/<sym>.f32 + Aerospike funding_data.
Trung gian: $TKR_OUT/mark_grid.npz (resume: partial.npz moi 150 symbol).
"""
import os
import glob
import json
import logging
import time
from datetime import datetime, timezone

import numpy as np

import aerospike
import cramjam

RAW = os.environ.get("TKR_RAW", "/home/ubuntu/claudedata/rvb_1m/raw")
OUT = os.environ.get("TKR_OUT", "/tmp/funding_topk")
CACHE2 = os.environ.get("TKR_CACHE2", "/tmp/funding_factor/cache2.npz")
AERO_NS = "test"
AERO_SET = "funding_data"
os.makedirs(OUT, exist_ok=True)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                    handlers=[logging.StreamHandler(), logging.FileHandler(OUT + "/rotate.log")])
log = logging.getLogger("tkr")

# ---- LOCKED params (PREREG §3-§6) ----
LEVEL_MIN = 480                      # moc 8h
HOLDS_ANCHOR = (240, 1440, 4320)     # neo MOM15
ORDER_ANCHOR = 1
LOCK_ANCHOR = 1440
MIN_SYM = 50
FUND_MS_MIN = 1609459200000          # 2021-01-01 00:00:00 UTC
FUND_MS_MAX = 1767225600000          # 2026-01-01 00:00:00 UTC
UTC = timezone.utc
DT = np.dtype([("ts", "<i4"), ("o", "<f4"), ("h", "<f4"), ("l", "<f4"), ("c", "<f4"), ("v", "<f4")])

BASE = int(datetime(2021, 1, 1, tzinfo=UTC).timestamp() // 60)      # 26824320
SAMPLE_END = int(datetime(2026, 1, 1, tzinfo=UTC).timestamp() // 60)
NMIN = SAMPLE_END - BASE
assert BASE % LEVEL_MIN == 0, "BASE phai chia het cho 480"
MARKS = np.arange(0, NMIN - LEVEL_MIN + 1, LEVEL_MIN, dtype=np.int64)   # 5478 moc
assert len(MARKS) == NMIN // LEVEL_MIN, "so moc phai = NMIN/480"


def load_sym(path):
    a = np.fromfile(path, dtype=DT)
    if len(a) < 30:
        return None
    ts = a["ts"].astype(np.int64)
    order = np.argsort(ts, kind="stable")
    ts = ts[order]
    a = a[order]
    _, idx = np.unique(ts, return_index=True)
    ts = ts[idx]
    o = a["o"][idx].astype(np.float32)
    h = a["h"][idx].astype(np.float32)
    l = a["l"][idx].astype(np.float32)
    c = a["c"][idx].astype(np.float32)
    m = (ts >= BASE) & (ts < SAMPLE_END)
    ts, o, h, l, c = ts[m], o[m], h[m], l[m], c[m]
    if len(ts) < 30:
        return None
    return ts, o, h, l, c


def load_funding(cli, sym, cache):
    if sym in cache:
        return cache[sym]
    try:
        kkey = cli.get((AERO_NS, AERO_SET, sym))
        bd = kkey[2]
        if not bd or "f_data" not in bd:
            cache[sym] = None
            return None
        d = json.loads(bytes(cramjam.snappy.decompress_raw(bytes(bd["f_data"]))))
        arr = sorted((int(t), float(r)) for t, r in d.items() if int(t) >= FUND_MS_MIN)
        ts = np.array([x[0] for x in arr], dtype=np.int64)
        fr = np.array([x[1] for x in arr], dtype=np.float64)
        keep = ts < FUND_MS_MAX
        ts, fr = ts[keep], fr[keep]
        cum = np.concatenate(([0.0], np.cumsum(fr)))
        cache[sym] = (ts, fr, cum)
        return cache[sym]
    except Exception as e:
        log.warning("funding load fail %s: %s", sym, type(e).__name__)
        cache[sym] = None
        return None


def cadence_of(ft):
    if ft is None or len(ft) < 3:
        return 0            # unknown
    d = np.diff(ft)
    med = float(np.median(d))
    if med <= 5.0 * 3600 * 1000:
        return 4            # cadence 4h
    if med <= 10.0 * 3600 * 1000:
        return 8            # cadence 8h
    return 99


def anchor_rows(ts_rel, o, h, l, c, m_e, ft, fr, cum):
    """Returns cho M-LEVEL MOM15 (HOLD 3 muc) — y het funding_factor.returns_for."""
    n = len(m_e)
    H = len(HOLDS_ANCHOR)
    raw = np.full((H, n), np.nan, dtype=np.float32)
    fund = np.full((H, n), np.nan, dtype=np.float32)
    slip = np.full(n, np.nan, dtype=np.float32)
    valid = np.zeros(n, dtype=np.int8)
    sd = np.zeros(n, dtype=np.int8)
    if n == 0 or ft is None:
        return raw, slip, fund, valid, sd
    epos = np.searchsorted(ts_rel, m_e)
    ok = (epos < len(ts_rel)) & (ts_rel[np.clip(epos, 0, len(ts_rel) - 1)] == m_e)
    epos, m_e = epos[ok], m_e[ok]
    n = len(m_e)
    if n == 0:
        return raw[:, :0], slip[:0], fund[:, :0], valid[:0], sd[:0]
    entry = c[epos].astype(np.float64)
    keep = entry > 0
    slip[keep] = 0.5 * (h[epos[keep]].astype(np.float64) - l[epos[keep]].astype(np.float64)) / entry[keep]
    t_e = (BASE + m_e) * 60000
    lo = np.searchsorted(ft, t_e, side="right")
    for j, hd in enumerate(HOLDS_ANCHOR):
        m_x = m_e + hd
        cens = m_x > (NMIN - 1)
        ep_end = np.searchsorted(ts_rel, m_x, side="right") - 1
        ep_end = np.clip(ep_end, 0, len(ts_rel) - 1)
        end = c[ep_end].astype(np.float64)
        rr = keep & (~cens)
        raw[j, rr] = end[rr] / entry[rr] - 1.0
        hi = np.searchsorted(ft, (BASE + m_x[rr]) * 60000, side="right")
        fund[j, rr] = cum[hi] - cum[lo[rr]]
        valid[rr] |= (1 << j)
        sd[rr] |= ((ep_end[rr] <= epos[rr]).astype(np.int8))
    return raw, slip, fund, valid, sd


def main():
    files = sorted(glob.glob(RAW + "/*.f32"))
    log.info("symbols=%d BASE=%d NMIN=%d MARKS=%d", len(files), BASE, NMIN, len(MARKS))
    marks_abs = (BASE + MARKS).astype(np.int64)
    t_all = time.time()

    # ---- neo reference (cache2) ----
    anchor_ok = 0
    if os.path.exists(CACHE2):
        z = np.load(CACHE2)
        ref_total_rows = int(z["total_rows"])
        ref_fire8 = int(len(z["fire8"]))
        a_ml_min, a_ml_sym = z["ml_min"], z["ml_sym"]
        anchor_ok = 1
        log.info("cache2 ref: total_rows=%d fire8=%d ml=%d", ref_total_rows, ref_fire8, len(a_ml_min))
    else:
        a_ml_min = a_ml_sym = None
        ref_total_rows = ref_fire8 = -1
        log.warning("cache2 NOT found (%s) => neo MOM15 khong tinh duoc", CACHE2)

    cli = aerospike.client({"hosts": [("127.0.0.1", 3222)], "policies": {"timeout": 60000}}).connect()
    fcache = {}
    if a_ml_sym is not None:
        slot_m = np.argsort(a_ml_sym, kind="stable")
        bounds_m = np.searchsorted(a_ml_sym[slot_m], np.arange(len(files) + 1))

    # ---- accumulators (grid) ----
    G = {k: [] for k in ("mark", "sym", "f", "raw", "slip", "fund", "sd")}
    # ---- accumulators (anchor) ----
    A = {k: [] for k in ("raw", "slip", "fund", "valid", "sd", "f", "sym", "min")}
    cad = np.zeros(len(files), dtype=np.int8)
    n_fund_ok = 0
    n_mark_candle = 0
    n_mark_rows = 0

    for i, p in enumerate(files):
        sym = os.path.basename(p)[:-4]
        r = load_sym(p)
        if r is None:
            continue
        ts, o, h, l, c = r
        ts_rel = (ts - BASE).astype(np.int64)
        fnd = load_funding(cli, sym, fcache)
        if fnd is not None:
            n_fund_ok += 1
        ft, fr, cum = (fnd if fnd is not None else (None, None, None))
        cad[i] = cadence_of(ft)

        # ---- grid moc 8h ----
        pos = np.searchsorted(ts, marks_abs)
        posc = np.clip(pos, 0, len(ts) - 1)
        at_mark = (pos < len(ts)) & (ts[posc] == marks_abs)
        n_mark_candle += int(at_mark.sum())
        ep = pos[at_mark]
        mr = MARKS[at_mark]
        if len(mr):
            n_mark_rows += len(mr)
            m_x = mr + LEVEL_MIN
            cens = m_x > (NMIN - 1)
            ep_end = np.clip(np.searchsorted(ts_rel, m_x, side="right") - 1, 0, len(ts_rel) - 1)
            entry = c[ep].astype(np.float64)
            ok = (~cens) & (entry > 0) & (ts_rel[ep_end] > mr)
            ep, mr, m_x, ep_end = ep[ok], mr[ok], m_x[ok], ep_end[ok]
            entry = entry[ok]
            if len(mr):
                end = c[ep_end].astype(np.float64)
                raw = (end / entry - 1.0).astype(np.float32)
                slip = (0.5 * (h[ep].astype(np.float64) - l[ep].astype(np.float64)) / entry).astype(np.float32)
                sd = (ep_end <= ep).astype(np.int8)
                if ft is not None:
                    lo = np.searchsorted(ft, (BASE + mr) * 60000, side="right")
                    hi = np.searchsorted(ft, (BASE + m_x) * 60000, side="right")
                    fund = (cum[hi] - cum[lo]).astype(np.float32)
                    idx = lo - 1
                    f_e = np.full(len(mr), np.nan, dtype=np.float32)
                    good = idx >= 0
                    f_e[good] = fr[idx[good]].astype(np.float32)
                else:
                    fund = np.full(len(mr), np.nan, dtype=np.float32)
                    f_e = np.full(len(mr), np.nan, dtype=np.float32)
                G["mark"].append(mr.astype(np.int32))
                G["sym"].append(np.full(len(mr), i, dtype=np.int16))
                G["f"].append(f_e)
                G["raw"].append(raw)
                G["slip"].append(slip)
                G["fund"].append(fund)
                G["sd"].append(sd)

        # ---- neo MOM15 (M-LEVEL rows cua symbol nay) ----
        if a_ml_sym is not None:
            i0, i1 = bounds_m[i], bounds_m[i + 1]
            if i1 > i0:
                rows = slot_m[i0:i1]
                m_e = a_ml_min[rows].astype(np.int64)
                if ft is not None:
                    raw, slip, fund, val, sd = anchor_rows(ts_rel, o, h, l, c, m_e, ft, fr, cum)
                    if raw.shape[1]:
                        A["raw"].append(raw); A["slip"].append(slip); A["fund"].append(fund)
                        A["valid"].append(val); A["sd"].append(sd)
                        idx = np.searchsorted(ft, (BASE + m_e) * 60000, side="right") - 1
                        f_e = np.full(len(m_e), np.nan, dtype=np.float32)
                        good = idx >= 0
                        f_e[good] = fr[idx[good]].astype(np.float32)
                        A["f"].append(f_e)
                        A["sym"].append(np.full(len(m_e), i, dtype=np.int16))
                        A["min"].append(m_e.astype(np.int32) + BASE)

        if i % 50 == 0:
            log.info("sym %d/%d el=%.0fs rows=%d", i, len(files), time.time() - t_all, n_mark_rows)
        if i % 150 == 0 and len(G["mark"]):
            try:
                np.savez(OUT + "/partial.npz",
                         **{k: np.concatenate(v) for k, v in G.items()}, upto=np.array(i))
            except Exception as e:
                log.warning("checkpoint fail: %s", type(e).__name__)
    cli.close()
    log.info("load done el=%.0fs funding_ok=%d/%d mark_rows=%d mark_candle=%d",
             time.time() - t_all, n_fund_ok, len(files), n_mark_rows, n_mark_candle)

    out = {k: np.concatenate(v) for k, v in G.items()}
    log.info("grid: rows=%d marks_uniq=%d", len(out["mark"]), len(np.unique(out["mark"])))
    np.savez(OUT + "/mark_grid.npz",
             g_mark=out["mark"], g_sym=out["sym"], g_f=out["f"], g_raw=out["raw"],
             g_slip=out["slip"], g_fund=out["fund"], g_sd=out["sd"],
             cadence=cad, n_sym=np.array(len(files)), base=np.array(BASE),
             nmin=np.array(NMIN), marks=np.array(MARKS), min_sym=np.array(MIN_SYM),
             holds_anchor=np.array(HOLDS_ANCHOR), level_min=np.array(LEVEL_MIN),
             ref_total_rows=np.array(ref_total_rows), ref_fire8=np.array(ref_fire8),
             anchor_ok=np.array(anchor_ok))
    if A["raw"]:
        np.savez(OUT + "/anchor_mom15.npz",
                 m_raw=np.concatenate(A["raw"], axis=1), m_slip=np.concatenate(A["slip"]),
                 m_fund=np.concatenate(A["fund"], axis=1), m_valid=np.concatenate(A["valid"]),
                 m_sd=np.concatenate(A["sd"]), m_f=np.concatenate(A["f"]),
                 m_sym=np.concatenate(A["sym"]), m_min=np.concatenate(A["min"]),
                 holds=np.array(HOLDS_ANCHOR))
        log.info("anchor rows=%d", int(np.concatenate(A["raw"], axis=1).shape[1]))
    open(OUT + "/ROTATE_DONE", "w").write(
        "ok rows=%d marks=%d funding_ok=%d\n" % (len(out["mark"]), len(np.unique(out["mark"])), n_fund_ok))
    log.info("saved mark_grid.npz el=%.0fs", time.time() - t_all)


if __name__ == "__main__":
    main()
