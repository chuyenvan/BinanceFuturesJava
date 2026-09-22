#!/usr/bin/env python3
"""RANGE4H_TOPK — sinh grid moc 4h cho luat quay vong LONG top-K BIEN DO NEN 4h RONG NHAT.

Pre-reg: docs/PREREG_RANGE4H_TOPK.md (commit 62e01bf, chot TRUOC khi chay; KHONG sua thiet ke).

Moc 4h (00/04/08/12/16/20 UTC): r % 240 == 0 (phut tuong doi so voi BASE=2021-01-01).
Bien xep hang (predictor, causal):
    range4h(sym, r) = (max_{t in [r-240, r-1]} high_t - min_{t in [r-240, r-1]} low_t) / open_{r-240}
  = bien do nen 4h DA DONG ket thuc tai moc r (khong chua phut r); LOAI neu open<=0 hoac so nen
    1m trong cua so < 200/240.
Xep hang GIAM DAN => top-K bien do LON NHAT. Moi dong = (moc r, symbol) voi:
  raw240 = close(r+240)/close(r)-1 ; raw1440 = close(r+1440)/close(r)-1 (PHU, HOLD 24h);
  slip = 0.5*(high-low)/close tai nen 1m moc r ; f_cum = cum funding event co ts in (r, r+hold]
  (convention (m_e, m_x], event tai moc exit DUOC tinh) ; sd = short_delist flag.

Neo MOM15 (PREREG §6b): dung lai /tmp/funding_factor/cache2.npz (total_rows, fire8, M-LEVEL rows)
va tinh lai net M-LEVEL 24h (ref +1,6690% DEV @0,10%) — y het vong funding-topk.

Thuan Python, 0-sim, khong Java, khong push. Chi DOC raw/<sym>.f32 + Aerospike funding_data.
Trung gian: $R4H_OUT/mark_grid4h.npz (resume: partial.npz moi 150 symbol).
"""
import os
import glob
import json
import logging
import time
from datetime import datetime, timezone

import numpy as np
import pandas as pd

import aerospike
import cramjam

RAW = os.environ.get("R4H_RAW", "/home/ubuntu/claudedata/rvb_1m/raw")
OUT = os.environ.get("R4H_OUT", "/tmp/range4h_topk")
CACHE2 = os.environ.get("R4H_CACHE2", "/tmp/funding_factor/cache2.npz")
AERO_NS = "test"
AERO_SET = "funding_data"
RESUME = os.environ.get("R4H_RESUME", "0") == "1"
os.makedirs(OUT, exist_ok=True)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                    handlers=[logging.StreamHandler(), logging.FileHandler(OUT + "/range4h.log")])
log = logging.getLogger("r4h")

# ---- LOCKED params (PREREG §3-§6) ----
LEVEL_MIN = 240                      # moc 4h
HOLDS = (240, 1440)                  # HOLD chinh (1 chu ky 4h) + PHU (24h)
HOLDS_ANCHOR = (240, 1440, 4320)     # neo MOM15 (y het vong truoc)
MIN_BARS = 200                       # so nen 1m toi thieu trong cua so 240'
MIN_SYM = 50
FUND_MS_MIN = 1609459200000          # 2021-01-01 00:00:00 UTC
FUND_MS_MAX = 1767225600000          # 2026-01-01 00:00:00 UTC
UTC = timezone.utc
DT = np.dtype([("ts", "<i4"), ("o", "<f4"), ("h", "<f4"), ("l", "<f4"), ("c", "<f4"), ("v", "<f4")])

BASE = int(datetime(2021, 1, 1, tzinfo=UTC).timestamp() // 60)      # 26824320
SAMPLE_END = int(datetime(2026, 1, 1, tzinfo=UTC).timestamp() // 60)
NMIN = SAMPLE_END - BASE
assert BASE % LEVEL_MIN == 0, "BASE phai chia het cho 240"
NBLK = NMIN // LEVEL_MIN                                            # 10956 block 4h
# moc r co cua so nen hop le: r = LEVEL*k, k >= 1 (can nen [r-240, r-1]) va r + 240 <= NMIN-1
MARKS = np.arange(LEVEL_MIN, NMIN - LEVEL_MIN + 1, LEVEL_MIN, dtype=np.int64)
BLK_OF_MARK = MARKS // LEVEL_MIN - 1                                # block nen dung cho tung moc
assert len(MARKS) == NBLK - 1


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
    o = a["o"][idx].astype(np.float64)
    h = a["h"][idx].astype(np.float64)
    l = a["l"][idx].astype(np.float64)
    c = a["c"][idx].astype(np.float64)
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


def anchor_rows(ts_rel, o, h, l, c, m_e, ft, fr, cum):
    """Returns cho M-LEVEL MOM15 (HOLD 3 muc) — y het funding_topk_rotate.anchor_rows."""
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
    slip[keep] = 0.5 * (h[epos[keep]] - l[epos[keep]]) / entry[keep]
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


def dense_grid(ts, o, h, l, c, ft, fr, cum):
    """Grid moc 4h cho 1 symbol. Tra dict cac mang (da loc eligible HOLD 240)."""
    Od = np.full(NMIN, np.nan, dtype=np.float32)
    Hd = np.full(NMIN, np.nan, dtype=np.float32)
    Ld = np.full(NMIN, np.nan, dtype=np.float32)
    Cd = np.full(NMIN, np.nan, dtype=np.float32)
    pos = (ts - BASE).astype(np.int64)
    Od[pos] = o.astype(np.float32)
    Hd[pos] = h.astype(np.float32)
    Ld[pos] = l.astype(np.float32)
    Cd[pos] = c.astype(np.float32)

    # --- bien do nen 4h da dong: block b = [240b, 240b+239] la cua so cho moc r=240(b+1) ---
    H2 = Hd.reshape(NBLK, LEVEL_MIN)
    L2 = Ld.reshape(NBLK, LEVEL_MIN)
    cnt = np.isfinite(H2).sum(axis=1).astype(np.int64)
    big = np.where(np.isfinite(H2), H2.astype(np.float64), -np.inf)
    small = np.where(np.isfinite(L2), L2.astype(np.float64), np.inf)
    hi = np.nanmax(big, axis=1)
    lo = np.nanmin(small, axis=1)
    o_open = Od.reshape(NBLK, LEVEL_MIN)[:, 0].astype(np.float64)
    okwin = (cnt >= MIN_BARS) & np.isfinite(o_open) & (o_open > 0)
    rng_blk = np.where(okwin, (hi - lo) / np.where(o_open > 0, o_open, np.nan), np.nan)

    rng = rng_blk[BLK_OF_MARK]
    diag = {"n_win_short": int((cnt[BLK_OF_MARK] < MIN_BARS).sum()),
            "n_open_bad": int((~np.isfinite(o_open[BLK_OF_MARK]) | (o_open[BLK_OF_MARK] <= 0)).sum())}

    # --- bar vao lenh tai moc r + exit (convention: nen cuoi cung co du lieu <= r+hold) ---
    validC = np.isfinite(Cd)
    ar = np.arange(NMIN, dtype=np.int64)
    last_valid = np.maximum.accumulate(np.where(validC, ar, -1))

    entry_ok = validC[MARKS]
    entry = Cd[MARKS].astype(np.float64)
    slip = np.where(entry_ok, 0.5 * (Hd[MARKS].astype(np.float64) - Ld[MARKS].astype(np.float64)) / entry, np.nan)

    out = {"mark": MARKS.astype(np.int32), "rng": rng.astype(np.float32),
           "entry_ok": entry_ok, "slip": slip.astype(np.float32), "entry": entry}
    keep_any = entry_ok & np.isfinite(rng)
    for hd in HOLDS:
        tgt = np.minimum(MARKS + hd, NMIN - 1)
        cens = (MARKS + hd) > (NMIN - 1)
        eidx = last_valid[tgt]
        ok = (~cens) & (eidx > MARKS) & entry_ok
        rawv = np.full(len(MARKS), np.nan)
        good = ok & (entry > 0)
        rawv[good] = Cd[eidx[good]].astype(np.float64) / entry[good] - 1.0
        sd = np.zeros(len(MARKS), dtype=np.int8)
        sd[ok] = (eidx[ok] <= np.searchsorted(ts, MARKS[ok], side="left")).astype(np.int8)
        out["raw%d" % hd] = rawv.astype(np.float32)
        out["sd%d" % hd] = sd
        if ft is not None and len(ft):
            t_e = (BASE + MARKS) * 60000
            t_x = (BASE + (MARKS + hd)) * 60000
            lo_i = np.searchsorted(ft, t_e, side="right")
            hi_i = np.searchsorted(ft, t_x, side="right")
            fv = cum[hi_i] - cum[lo_i]
            out["fund%d" % hd] = fv.astype(np.float32)
        else:
            out["fund%d" % hd] = np.full(len(MARKS), np.nan, dtype=np.float32)
        keep_any &= ok
    keep_any &= np.isfinite(out["fund240"])
    return out, keep_any, diag


def main():
    files = sorted(glob.glob(RAW + "/*.f32"))
    log.info("symbols=%d BASE=%d NMIN=%d marks=%d", len(files), BASE, NMIN, len(MARKS))

    # ---- neo reference (cache2) ----
    a_ml_min = a_ml_sym = None
    ref_total_rows = ref_fire8 = -1
    if os.path.exists(CACHE2):
        z = np.load(CACHE2)
        ref_total_rows = int(z["total_rows"])
        ref_fire8 = int(len(z["fire8"]))
        a_ml_min, a_ml_sym = z["ml_min"], z["ml_sym"]
        log.info("cache2 ref: total_rows=%d fire8=%d ml=%d", ref_total_rows, ref_fire8, len(a_ml_min))
    else:
        log.warning("cache2 NOT found (%s) => neo MOM15 khong tinh duoc", CACHE2)

    cli = aerospike.client({"hosts": [("127.0.0.1", 3222)], "policies": {"timeout": 60000}}).connect()
    fcache = {}
    if a_ml_sym is not None:
        slot_m = np.argsort(a_ml_sym, kind="stable")
        bounds_m = np.searchsorted(a_ml_sym[slot_m], np.arange(len(files) + 1))

    keys = ("mark", "sym", "rng", "raw240", "raw1440", "slip", "fund240", "fund1440", "sd240", "sd1440")
    G = {k: [] for k in keys}
    A = {k: [] for k in ("raw", "slip", "fund", "valid", "sd", "sym", "min")}
    start_i = 0
    stats = {"n_fund_ok": 0, "n_mark_rows": 0, "n_win_short": 0, "n_open_bad": 0,
             "n_bar_miss": 0, "n_cens": 0, "n_rng_valid": 0, "n_elig": 0, "n_delist": 0,
             "n_nofund_rows": 0, "n_mom_symbols": 0}
    t_all = time.time()

    if RESUME and os.path.exists(OUT + "/partial.npz"):
        z = np.load(OUT + "/partial.npz")
        start_i = int(z["upto"])
        for k in keys:
            G[k] = [z["g_" + k]]
        for k in ("raw", "slip", "fund", "valid", "sd", "sym", "min"):
            if ("a_" + k) in z.files:
                A[k] = [z["a_" + k]]
        for k in stats:
            if ("s_" + k) in z.files:
                stats[k] = int(z["s_" + k])
        log.info("RESUME tu symbol %d (rows=%d)", start_i, sum(len(x) for x in G["mark"]))

    for i, p in enumerate(files):
        if i < start_i:
            continue
        sym = os.path.basename(p)[:-4]
        r = load_sym(p)
        if r is None:
            continue
        ts, o, h, l, c = r
        ts_rel = (ts - BASE).astype(np.int64)
        fnd = load_funding(cli, sym, fcache)
        if fnd is not None:
            stats["n_fund_ok"] += 1
        ft, fr, cum = (fnd if fnd is not None else (None, None, None))

        g, keep, diag = dense_grid(ts, o, h, l, c, ft, fr, cum)
        stats["n_mark_rows"] += len(g["mark"])
        stats["n_bar_miss"] += int((~g["entry_ok"]).sum())
        stats["n_win_short"] += diag["n_win_short"]
        stats["n_open_bad"] += diag["n_open_bad"]
        if fnd is None:
            stats["n_nofund_rows"] += int(len(g["mark"]))
        stats["n_rng_valid"] += int(np.isfinite(g["rng"]).sum())
        stats["n_elig"] += int(keep.sum())
        stats["n_cens"] += int(((MARKS + LEVEL_MIN) > (NMIN - 1)).sum())
        if keep.sum():
            stats["n_delist"] += int(g["sd240"][keep].sum())
            G["mark"].append(g["mark"][keep].astype(np.int32))
            G["sym"].append(np.full(int(keep.sum()), i, dtype=np.int16))
            for k in ("rng", "raw240", "raw1440", "slip", "fund240", "fund1440"):
                G[k].append(g[k][keep])
            G["sd240"].append(g["sd240"][keep])
            G["sd1440"].append(g["sd1440"][keep])

        # ---- neo MOM15 ----
        if a_ml_sym is not None:
            i0, i1 = bounds_m[i], bounds_m[i + 1]
            if i1 > i0:
                rows = slot_m[i0:i1]
                m_e = a_ml_min[rows].astype(np.int64)
                raw, slip, fund, val, sd = anchor_rows(ts_rel, o, h, l, c, m_e, ft, fr, cum)
                if raw.shape[1]:
                    stats["n_mom_symbols"] += 1
                    A["raw"].append(raw); A["slip"].append(slip); A["fund"].append(fund)
                    A["valid"].append(val); A["sd"].append(sd)
                    A["sym"].append(np.full(len(m_e), i, dtype=np.int16))
                    A["min"].append((m_e + BASE).astype(np.int32))

        if i % 50 == 0:
            log.info("sym %d/%d el=%.0fs rows=%d elig=%d", i, len(files), time.time() - t_all,
                     sum(len(x) for x in G["mark"]), stats["n_elig"])
        if i % 150 == 0:
            try:
                ax = {"raw": 1, "fund": 1}
                np.savez(OUT + "/partial.npz", upto=np.array(i + 1),
                         **{"g_" + k: np.concatenate(v) for k, v in G.items() if v},
                         **{"a_" + k: np.concatenate(v, axis=ax.get(k, 0)) for k, v in A.items() if v},
                         **{"s_" + k: np.array(v) for k, v in stats.items()})
            except Exception as e:
                log.warning("checkpoint fail: %s", e)
    cli.close()
    log.info("load done el=%.0fs funding_ok=%d/%d stats=%s", time.time() - t_all,
             stats["n_fund_ok"], len(files), stats)

    out = {k: np.concatenate(v) for k, v in G.items()}
    log.info("grid: rows=%d marks_uniq=%d", len(out["mark"]), len(np.unique(out["mark"])))
    np.savez(OUT + "/mark_grid4h.npz",
             g_mark=out["mark"], g_sym=out["sym"], g_rng=out["rng"], g_raw240=out["raw240"],
             g_raw1440=out["raw1440"], g_slip=out["slip"], g_fund240=out["fund240"],
             g_fund1440=out["fund1440"], g_sd240=out["sd240"], g_sd1440=out["sd1440"],
             n_sym=np.array(len(files)), base=np.array(BASE), nmin=np.array(NMIN),
             marks=np.array(MARKS), min_sym=np.array(MIN_SYM), level_min=np.array(LEVEL_MIN),
             min_bars=np.array(MIN_BARS), holds=np.array(HOLDS),
             ref_total_rows=np.array(ref_total_rows), ref_fire8=np.array(ref_fire8),
             **{"stat_" + k: np.array(v) for k, v in stats.items()})
    if A["raw"]:
        np.savez(OUT + "/anchor_mom15.npz",
                 m_raw=np.concatenate(A["raw"], axis=1), m_slip=np.concatenate(A["slip"]),
                 m_fund=np.concatenate(A["fund"], axis=1), m_valid=np.concatenate(A["valid"]),
                 m_sd=np.concatenate(A["sd"]), m_sym=np.concatenate(A["sym"]),
                 m_min=np.concatenate(A["min"]), holds=np.array(HOLDS_ANCHOR))
        log.info("anchor rows=%d", int(np.concatenate(A["raw"], axis=1).shape[1]))
    open(OUT + "/RANGE4H_DONE", "w").write(
        "ok rows=%d marks=%d funding_ok=%d\n" % (len(out["mark"]), len(np.unique(out["mark"])), stats["n_fund_ok"]))
    log.info("saved mark_grid4h.npz el=%.0fs", time.time() - t_all)


if __name__ == "__main__":
    main()
