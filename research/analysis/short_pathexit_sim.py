#!/usr/bin/env python3
"""short_pathexit_sim.py — PREREG_SHORT_PATHEXIT: do 3 kieu THOAT tren DUONG GIA 1m.

  (i)   CUT C          : cat cung khi coin TANG >= C  (nhu vong truoc)
  (ii)  LABEL(thr,E)   : THOAT KHOP NHAN — TP tai -thr, stop tai +E (1m path, first-hit)
  (iii) NOSTOP         : giu den het h
  (iv)  TRAIL T        : trailing stop T tu day loi

Nguon gia: Aerospike test.kline_1m_opt (key YYYYMMDD-HHMM TZ+7, snappy+pb {sym:[O,H,L,C,V]}).
Stream 1 lan, buffer truot 72h, KHONG ghi dia. Train (bins) chi o Kaggle.

Chay:
  python3 short_pathexit_sim.py --bins-root DIR --arms TAG:DIR,TAG:DIR --labels-dir DIR \
      --map-csv F --out out.json --mode pb|sim|both
"""
import argparse, glob, json, os, struct, sys, time
from collections import defaultdict
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

H = 3600000
BLOCK_H = 72
NREP = 2000
SEED = 20260905
LEG = 1.21
COST_BASE = 0.00112
COST_STRESS = 0.00150
FUND72 = 0.00585          # short TRA funding (%/72h)
K_SEL = 8
NEED = 288                # nBars_72h >= 288
RES = 1024
TZ7 = timezone(timedelta(hours=7))
DEV_END_MS = int(datetime(2026, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)
H_MIN = {"12h": 720, "24h": 1440, "72h": 4320}

_BIN_DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("p0", ">f4"), ("p1", ">f4"),
                    ("p2", ">f4"), ("p3", ">f4")])


# ─────────────────────────── 1m parse ───────────────────────────
def _rd_varint(b, i):
    r = 0; s = 0
    while True:
        x = b[i]; i += 1; r |= (x & 0x7F) << s
        if not x & 0x80:
            return r, i
        s += 7


def parse_needed(buf, need):
    """Chi decode cac symbol trong `need` (bytes) -> {sym_bytes:(h,l,c)}. Bo qua sym khac."""
    out = {}; i = 0; n = len(buf)
    while i < n:
        tag, i = _rd_varint(buf, i)
        if tag == 0x0A:
            ln, i = _rd_varint(buf, i); end = i + ln; j = i
            key = None; h = l = c = 0.0; got = False
            while j < end:
                t, j = _rd_varint(buf, j)
                if t == 0x0A:
                    kl, j = _rd_varint(buf, j); key = buf[j:j + kl]; j += kl
                    got = key in need
                elif t == 0x12:
                    vl, j = _rd_varint(buf, j)
                    if got:
                        vb = buf[j:j + vl]; k = 0
                        while k < len(vb):
                            ft, k = _rd_varint(vb, k); fn = ft >> 3; w = ft & 7
                            if w == 5:
                                val = struct.unpack('<f', vb[k:k + 4])[0]; k += 4
                                if fn == 2:
                                    h = val
                                elif fn == 3:
                                    l = val
                                elif fn == 4:
                                    c = val
                            elif w == 0:
                                _, k = _rd_varint(vb, k)
                            elif w == 2:
                                l2, k = _rd_varint(vb, k); k += l2
                            else:
                                break
                        out[key] = (h, l, c)
                    j += vl
                else:
                    w = t & 7
                    if w == 2:
                        l3, j = _rd_varint(buf, j); j += l3
                    elif w == 0:
                        _, j = _rd_varint(buf, j)
                    elif w == 5:
                        j += 4
                    elif w == 1:
                        j += 8
                    else:
                        break
            i = end
        else:
            w = tag & 7
            if w == 2:
                ln, i = _rd_varint(buf, i); i += ln
            elif w == 0:
                _, i = _rd_varint(buf, i)
            elif w == 5:
                i += 4
            elif w == 1:
                i += 8
            else:
                break
    return out


THRS_GRID = (0.015, 0.03, 0.07)
ES_GRID = (0.03, 0.05, 0.10)
HS_GRID = (("12h", 720), ("24h", 1440), ("72h", 4320))


def _exit_grid(hh, ll, cc, P, thr, E, hs):
    """Tra {(h_name,thr,E): (pnl,held)} voi first-hit CHINH XAC tren duong 1m."""
    if np.isnan(hh).all() or not np.isfinite(P) or P <= 0:
        return None
    hh = _ffill(hh); ll = _ffill(ll); cc = _ffill(cc)
    cmin = np.minimum.accumulate(ll)
    cmax = np.maximum.accumulate(hh)
    out = {}
    for hn, n in hs:
        hh_w, ll_w, cc_w = hh[:n], ll[:n], cc[:n]
        itp = int(np.argmax(np.minimum.accumulate(ll_w) <= P * (1 - thr))) if (np.minimum.accumulate(ll_w) <= P * (1 - thr)).any() else 10 ** 9
        isl = int(np.argmax(np.maximum.accumulate(hh_w) >= P * (1 + E))) if (np.maximum.accumulate(hh_w) >= P * (1 + E)).any() else 10 ** 9
        if isl <= itp and isl < 10 ** 9:
            out[(hn, thr, E)] = (-E, float(isl + 1))
        elif itp < 10 ** 9:
            out[(hn, thr, E)] = (thr, float(itp + 1))
        else:
            out[(hn, thr, E)] = (-(cc_w[-1] / P - 1), float(n))
    return out


def parse_min(buf):
    out = {}; i = 0; n = len(buf)
    while i < n:
        tag, i = _rd_varint(buf, i)
        if tag == 0x0A:
            ln, i = _rd_varint(buf, i); entry = buf[i:i + ln]; i += ln
            j = 0; key = None; vals = [0.0] * 5
            while j < len(entry):
                t, j = _rd_varint(entry, j)
                if t == 0x0A:
                    kl, j = _rd_varint(entry, j); key = entry[j:j + kl].decode(); j += kl
                elif t == 0x12:
                    vl, j = _rd_varint(entry, j); vb = entry[j:j + vl]; j += vl
                    k = 0
                    while k < len(vb):
                        ft, k = _rd_varint(vb, k); fn = ft >> 3; w = ft & 7
                        if w == 5:
                            vals[fn - 1] = struct.unpack('<f', vb[k:k + 4])[0]; k += 4
                        elif w == 0:
                            _, k = _rd_varint(vb, k)
                        elif w == 2:
                            l2, k = _rd_varint(vb, k); k += l2
                        else:
                            break
                    if key is not None:
                        out[key] = vals
                else:
                    w = t & 7
                    if w == 2:
                        l3, j = _rd_varint(entry, j); j += l3
                    elif w == 0:
                        _, j = _rd_varint(entry, j)
                    elif w == 5:
                        j += 4
                    elif w == 1:
                        j += 8
                    else:
                        break
        else:
            w = tag & 7
            if w == 2:
                ln, i = _rd_varint(buf, i); i += ln
            elif w == 0:
                _, i = _rd_varint(buf, i)
            elif w == 5:
                i += 4
            elif w == 1:
                i += 8
            else:
                break
    return out


# ─────────────────────────── IO ───────────────────────────
def read_bins(fold_files):
    ts_l, sy_l, p_l = [], [], []
    for fp in fold_files:
        a = np.fromfile(fp, dtype=_BIN_DT)
        if not len(a):
            continue
        ts_l.append(a["ts"].astype(np.int64)); sy_l.append(a["sym"].astype(np.int32))
        p_l.append(a["p3"].astype(np.float32))
    if not ts_l:
        return None
    return np.concatenate(ts_l), np.concatenate(sy_l), np.concatenate(p_l)


def load_labels(lb_dir, map_csv, hs=("12h", "24h", "72h")):
    import funding_label_pb as FLPB
    smap = pd.read_csv(map_csv)
    s2i = dict(zip(smap.symbol, smap.symId.astype(np.int32)))
    fs = sorted(glob.glob(lb_dir + "/funding_label_*.pb"))
    fs = [f for f in fs if os.path.basename(f).split("_")[2] < "20260101"]
    fs = [f for f in fs if os.path.basename(f).split("_")[2] < "20260101"]
    parts = []
    for fp in fs:
        cols = ["tEpochMs", "symbol"]
        for h in hs:
            cols += ["retEnd_%s" % h, "maxFav_%s" % h, "maxAdv_%s" % h,
                     "tHitFav_%s" % h, "tHitAdv_%s" % h, "nBars_%s" % h]
        d = FLPB.read_label(fp, usecols=cols)
        d = d[d["nBars_72h"] >= NEED]
        parts.append(d)
        print("   label %s %d" % (os.path.basename(fp), len(d)), flush=True)
    d = pd.concat(parts, ignore_index=True) if len(parts) > 1 else parts[0]
    sid = d.symbol.map(s2i)
    k = sid.notna().to_numpy()
    d = d[k]
    ts = d.tEpochMs.to_numpy(np.int64)
    sym = sid[k].to_numpy(np.int32)
    out = {"key": ts * RES + sym, "ts": ts, "sym": sym}
    for h in hs:
        for c in ("retEnd", "maxFav", "maxAdv", "tHitFav", "tHitAdv"):
            out["%s_%s" % (c, h)] = d["%s_%s" % (c, h)].to_numpy(np.float32)
    o = np.argsort(out["key"], kind="stable")
    for k2 in out:
        out[k2] = out[k2][o]
    return out


def attach(key_lbl, ts, sym):
    key = ts * RES + sym.astype(np.int64)
    ip = np.clip(np.searchsorted(key_lbl, key), 0, len(key_lbl) - 1)
    return key_lbl[ip] == key, ip


# ─────────────────────────── CI / agg ───────────────────────────
def ci_mean(v, ts):
    v = np.asarray(v, np.float64); ts = np.asarray(ts, np.int64)
    m = np.isfinite(v)
    if m.sum() == 0:
        return dict(mean=float("nan"), raw=[None, None], out_raw=False, out_both=False, n=0)
    v, ts = v[m], ts[m]
    bk = ts // (BLOCK_H * H)
    _, inv = np.unique(bk, return_inverse=True)
    sums = np.bincount(inv, weights=v); cnts = np.bincount(inv).astype(np.float64)
    k = cnts > 0; sums, cnts = sums[k], cnts[k]
    n = len(sums)
    rng = np.random.default_rng(SEED)
    out = np.empty(NREP)
    for b in range(NREP):
        pick = rng.integers(0, n, n)
        out[b] = sums[pick].sum() / cnts[pick].sum()
    lo, hi = float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))
    mu = float(v.mean())
    ilo, ihi = mu - (mu - lo) * LEG, mu + (hi - mu) * LEG
    o1 = lo > 0 or hi < 0; o2 = ilo > 0 or ihi < 0
    return dict(mean=mu, raw=[lo, hi], infl=[ilo, ihi], n=int(m.sum()),
                out_raw=bool(o1), out_legacy=bool(o2), out_both=bool(o1 and o2))


def by_year(vals, ts):
    o = {}
    tt = pd.to_datetime(ts, unit="ms", utc=True).tz_convert("Asia/Bangkok").year.to_numpy()
    for yr in (2022, 2023, 2024, 2025):
        m = tt == yr
        o[str(yr)] = round(float(np.asarray(vals)[m].mean()), 6) if m.sum() else None
    return o


def agg_rule(pnl, ts, held_min, funding="prorata"):
    pnl = np.asarray(pnl, np.float64)
    fn = FUND72 if funding == "flat" else FUND72 * (np.asarray(held_min, np.float64) / 4320.0)
    net = pnl - COST_BASE - fn
    pt = pd.DataFrame({"ts": ts, "v": net}).groupby("ts")["v"].mean()
    ci = ci_mean(pt.to_numpy(), pt.index.to_numpy(np.int64))
    return {"net": ci, "by_year_net": by_year(pt.to_numpy(), pt.index.to_numpy(np.int64)),
            "winrate": round(float((net > 0).mean()), 4),
            "mean_held_h": round(float(np.asarray(held_min).mean() / 60.0), 2),
            "p01": round(float(np.percentile(net, 1)), 6),
            "max_loss": round(float(net.min()), 6)}


# ─────────────────────────── picks ───────────────────────────
def build_picks(tag, bins_dir, folds, lbl):
    files = [os.path.join(bins_dir, "predict_wf_%s.bin" % f) for f in folds]
    files = [f for f in files if os.path.exists(f)]
    ts, sym, p = read_bins(files)
    hit, ip = attach(lbl["key"], ts, sym)
    ts, sym, p, ip = ts[hit], sym[hit], p[hit], ip[hit]
    okk = np.isfinite(p)
    ts, sym, p, ip = ts[okk], sym[okk], p[okk], ip[okk]
    df = pd.DataFrame({"ts": ts, "sym": sym, "p": p.astype(np.float64), "ip": ip})
    g = df.groupby("ts", sort=False)
    df["n"] = g["p"].transform("size")
    df["r"] = g["p"].rank(method="first")
    sel = df["r"] > (df["n"] - K_SEL)
    return df.loc[sel, ["ts", "sym", "ip"]].reset_index(drop=True)


def pb_rules(pk, lbl, thr, E, h="72h"):
    ip = pk["ip"].to_numpy()
    ret = lbl["retEnd_%s" % h][ip].astype(np.float64)
    mfav = lbl["maxFav_%s" % h][ip].astype(np.float64)
    madv = lbl["maxAdv_%s" % h][ip].astype(np.float64)
    tfav = lbl["tHitFav_%s" % h][ip].astype(np.float64)
    tadv = lbl["tHitAdv_%s" % h][ip].astype(np.float64)
    hl = H_MIN[h]
    d = {"NOSTOP": (-ret, np.full(len(ret), float(hl)))}
    for C in (0.20, 0.30, 0.50, 0.90):
        s = mfav >= C
        d["CUT%d" % int(C * 100)] = (np.where(s, -C, -ret), np.where(s, tfav, hl))
    tp = madv <= -thr
    sl = mfav >= E
    pnl = np.where(tp, thr, -ret)
    pnl = np.where(sl & ~tp, -E, pnl)
    both = tp & sl
    pnl = np.where(both, np.where(tadv < tfav, -E, thr), pnl)
    held = np.where(sl & ~tp, tfav, np.where(tp, tadv, hl))
    d["LABEL"] = (pnl, held)
    return d, {"ambig_frac": float(both.mean()), "tp_frac": float(tp.mean()),
               "sl_frac": float(sl.mean())}


# ─────────────────────────── 1m sim ───────────────────────────
def _ffill(a):
    a = a.copy()
    idx = np.where(~np.isnan(a), np.arange(len(a)), 0)
    np.maximum.accumulate(idx, out=idx)
    return a[idx]


def _exit_pick(hh, ll, cc, P, thr, E, C, T):
    """hh,ll,cc float arrays (window). Tra (pnl, held_min, reason)."""
    v = ~np.isnan(hh)
    if v.sum() < 2 or not np.isfinite(P) or P <= 0:
        return {k: (np.nan, 4320.0, "miss") for k in ("CUT", "LABEL", "TRAIL", "NOSTOP")}
    hh, ll, cc = _ffill(hh), _ffill(ll), _ffill(cc)
    n = len(hh)
    last = cc[-1]
    chg = last / P - 1
    # CUT
    hi_c = P * (1 + C)
    s = hh >= hi_c
    if s.any():
        pnl_c, held_c, rc = -C, float(np.argmax(s) + 1), "cut"
    else:
        pnl_c, held_c, rc = -chg, float(n), "hold"
    # LABEL
    sl = hh >= P * (1 + E); tp = ll <= P * (1 - thr)
    isl = int(np.argmax(sl)) if sl.any() else 10 ** 9
    itp = int(np.argmax(tp)) if tp.any() else 10 ** 9
    if isl <= itp and isl < 10 ** 9:
        pnl_l, held_l, rl = -E, float(isl + 1), "sl"
    elif itp < 10 ** 9:
        pnl_l, held_l, rl = thr, float(itp + 1), "tp"
    else:
        pnl_l, held_l, rl = -chg, float(n), "hold"
    # TRAIL
    runmin = np.fmin.accumulate(ll)
    lvl = runmin * (1 + T)
    st = hh >= lvl
    if st.any():
        i = int(np.argmax(st))
        pnl_t, held_t, rt = -(lvl[i] / P - 1), float(i + 1), "trail"
    else:
        pnl_t, held_t, rt = -chg, float(n), "hold"
    return dict(CUT=(pnl_c, held_c, rc), LABEL=(pnl_l, held_l, rl), TRAIL=(pnl_t, held_t, rt),
                NOSTOP=(-chg, float(n), "hold"))


def sim_1m(picks_by_tag, id2name, sym_ids_needed, aero, years, thrE, C=0.20, T=0.05,
           max_ticks=0, max_days=0, ranges=None, grid=False):
    import aerospike, cramjam
    _h, _p = aero.split(":")
    cli = aerospike.client({"hosts": [(_h, int(_p))]}).connect()
    dec = cramjam.snappy.decompress_raw
    id2name_b = {int(k): v.encode() for k, v in id2name.items()}
    ticks = {}
    for tag, pk in picks_by_tag.items():
        for ts, s in zip(pk["ts"].to_numpy(), pk["sym"].to_numpy()):
            # t = OPEN time cua nen 15m; close(t) = phut cuoi nen = m0+14 (khop .pb, do that)
            ticks.setdefault(int(ts) // 60000 + 14, []).append((tag, int(s)))
    all_m0 = sorted(ticks)
    if max_ticks:
        all_m0 = all_m0[:max_ticks]
    union = sorted(sym_ids_needed)
    rows = {s: i for i, s in enumerate(union)}
    out = {tag: defaultdict(list) for tag in picks_by_tag}
    COMBOS = [(hn, thr, E) for hn, _n in HS_GRID for thr in THRS_GRID for E in ES_GRID]
    n_tick = len(all_m0)
    gsum = {cb: np.zeros(n_tick) for cb in COMBOS} if grid else None
    gcnt = {cb: np.zeros(n_tick) for cb in COMBOS} if grid else None
    gheld = {cb: np.zeros(n_tick) for cb in COMBOS} if grid else None
    tsi = {m0: i for i, m0 in enumerate(all_m0)}
    DBG = [0]
    if ranges is None:
        ranges = []
        for y in years:
            ranges.append((datetime(y, 1, 1, tzinfo=TZ7),
                           datetime(y, 12, 31, 23, 59, tzinfo=TZ7) if y == 2025
                           else datetime(y + 1, 1, 3, 0, 0, tzinfo=TZ7), y))
    for rng_start, rng_end, y in ranges:
        base_m = int(rng_start.timestamp() // 60)
        nmin = int(round((rng_end - rng_start).total_seconds() // 60)) + 1
        arr = np.full((len(union), nmin, 3), np.nan, np.float32)
        sel = [m0 for m0 in all_m0 if base_m <= m0 and (m0 + 4320) <= (base_m + nmin - 1)]
        tset = set(sel)
        if max_days:
            tset = set(sorted(tset)[:max_days])
        rc = defaultdict(int)
        active_b = set()
        add_ptr = rem_ptr = 0
        entryP = {}
        t0 = time.time()
        ndays = (nmin + 1439) // 1440
        for di in range(ndays):
            keys = []
            for k in range(1440):
                mm = di * 1440 + k
                if mm >= nmin:
                    break
                keys.append(("test", "kline_1m_opt",
                             (rng_start + timedelta(minutes=mm)).strftime("%Y%m%d-%H%M")))
            try:
                brecs = cli.batch_read(keys).batch_records
            except Exception:
                brecs = []
            for k in range(len(keys)):
                mi = di * 1440 + k
                m = base_m + mi
                cur = ticks.get(m)
                need = active_b if not cur else (active_b | {id2name_b[s] for _t, s in cur})
                rec = {}
                if k < len(brecs):
                    rr = brecs[k]
                    if rr.result == 0 and rr.record is not None:
                        _kk, _meta, bins = rr.record
                        if bins and "data" in bins:
                            try:
                                rec = parse_needed(bytes(dec(bins["data"])), need)
                            except Exception:
                                rec = {}
                if m in tset and rec:
                    for _tag, s in ticks[m]:
                        v = rec.get(id2name_b[s])
                        if v is not None:
                            entryP[(m, s)] = v[2]
                while add_ptr < len(sel) and sel[add_ptr] <= m - 1:
                    for _tag, s in ticks[sel[add_ptr]]:
                        rc[s] += 1
                        active_b.add(id2name_b[s])
                    add_ptr += 1
                while rem_ptr < len(sel) and sel[rem_ptr] <= m - 1 - 4320:
                    for _tag, s in ticks[sel[rem_ptr]]:
                        rc[s] -= 1
                        if rc[s] == 0:
                            del rc[s]
                            active_b.discard(id2name_b[s])
                    rem_ptr += 1
                if rec and rc:
                    rl, hh, ll_, cc_ = [], [], [], []
                    for s in rc:
                        v = rec.get(id2name_b[s])
                        if v is None:
                            continue
                        rl.append(rows[s]); hh.append(v[0]); ll_.append(v[1]); cc_.append(v[2])
                    if rl:
                        ri = np.asarray(rl)
                        arr[ri, mi, 0] = hh; arr[ri, mi, 1] = ll_; arr[ri, mi, 2] = cc_
                m0f = m - 4320
                if m0f in tset:
                    i0 = m0f + 1 - base_m
                    if os.environ.get("DBG") and not DBG[0]:
                        s0 = ticks[m0f][0][1]
                        print("DBG m0f", m0f, "in tset; entry m0 minute present?", (m0f in tset),
                              "entryP", entryP.get((m0f, s0)), "rec_at_m0_empty?",
                              "n_entryP", len(entryP), flush=True)
                        DBG[0] = 1
                    for tag, s in ticks[m0f]:
                        P = entryP.get((m0f, s), np.nan)
                        row = rows[s]
                        hh_w = arr[row, i0:i0 + 4320, 0]
                        ll_w = arr[row, i0:i0 + 4320, 1]
                        cc_w = arr[row, i0:i0 + 4320, 2]
                        thr, E = thrE.get(tag, (0.015, 0.10))
                        r = _exit_pick(hh_w, ll_w, cc_w, P, thr, E, C, T)
                        for rule, (pnl, held, reason) in r.items():
                            out[tag][rule].append((m0f, pnl, held, reason, s))
                        if grid and tag == list(picks_by_tag)[0]:
                            ii = tsi[m0f]
                            for thr in THRS_GRID:
                                for E in ES_GRID:
                                    gg = _exit_grid(hh_w, ll_w, cc_w, P, thr, E, HS_GRID)
                                    if gg is None:
                                        gg = {(hn, thr, E): (np.nan, 4320.0)
                                              for hn, _n in HS_GRID}
                                    for (hn, _t, _e), (pn, hd) in gg.items():
                                        cb = (hn, thr, E)
                                        gsum[cb][ii] += pn; gcnt[cb][ii] += 1; gheld[cb][ii] += hd
            if di % 10 == 0:
                print("  y=%d day %d/%d %.0fs" % (y, di, ndays, time.time() - t0), flush=True)
        print("YEAR %d DONE nmin=%d %.0fs" % (y, nmin, time.time() - t0), flush=True)
        # (ket qua da gom trong out theo tung pick)
    if grid:
        grid_res = {cb: (gsum[cb], gcnt[cb], gheld[cb]) for cb in COMBOS}
        return out, grid_res, np.array(all_m0, np.int64) * 60000
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bins-root", required=True)
    ap.add_argument("--arms", required=True)
    ap.add_argument("--labels-dir", default="/home/ubuntu/ds_label15m")
    ap.add_argument("--map-csv", default="/home/ubuntu/claudedata/oi/symbol_map.csv")
    ap.add_argument("--folds", default="20220101,20220401,20220701,20221001,20230101,20230401,"
                                      "20230701,20231001,20240101,20240401,20240701,20241001,"
                                      "20250101,20250401,20250701,20251001")
    ap.add_argument("--out", required=True)
    ap.add_argument("--mode", default="pb", choices=["pb", "sim", "both"])
    ap.add_argument("--aero", default="127.0.0.1:3222")
    ap.add_argument("--years", default="2022,2023,2024,2025")
    ap.add_argument("--max-ticks", type=int, default=0)
    ap.add_argument("--max-days", type=int, default=0)
    ap.add_argument("--sim-start", default="")
    ap.add_argument("--sim-end", default="")
    ap.add_argument("--grid", action="store_true")
    a = ap.parse_args()
    folds = [x.strip() for x in a.folds.split(",") if x.strip()]
    sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/ml/lib")
    t0 = time.time()
    lbl = load_labels(a.labels_dir, a.map_csv, ("12h", "24h", "72h"))
    print("labels %d (%.0fs)" % (len(lbl["key"]), time.time() - t0), flush=True)
    smap = pd.read_csv(a.map_csv)
    id2name = dict(zip(smap.symId.astype(int), smap.symbol))
    arms = []
    for spec in a.arms.split(","):
        spec = spec.strip()
        if spec:
            tag, d = spec.split(":")
            arms.append((tag, os.path.join(a.bins_root, d)))
    res = {"k_sel": K_SEL, "cost_base": COST_BASE, "fund72": FUND72,
           "prereg": "PREREG_SHORT_PATHEXIT", "arms": {}}
    picks = {}
    # thr/E tuy arm
    thrE = {"PA_t15_E10_S42": (0.015, 0.10), "PA_t15_E10_S7": (0.015, 0.10)}
    for tag, dirp in arms:
        pk = build_picks(tag, dirp, folds, lbl)
        pk = pk[(pk["ts"] + 72 * H) <= DEV_END_MS].reset_index(drop=True)
        picks[tag] = pk
        print("arm %s picks %d" % (tag, len(pk)), flush=True)
        te = thrE.get(tag, (0.015, 0.10))
        res["arms"][tag] = {"n_pick": int(len(pk)), "thr": te[0], "E": te[1]}
    if a.mode in ("pb", "both"):
        for tag, dirp in arms:
            pk = picks[tag]
            te = thrE.get(tag, (0.015, 0.10))
            d, info = pb_rules(pk, lbl, te[0], te[1], "72h")
            ts = pk["ts"].to_numpy()
            res["arms"][tag]["pb72"] = {r: agg_rule(v[0], ts, v[1]) for r, v in d.items()}
            res["arms"][tag]["pb72_info"] = info
        # SWEEP (pb proxy): h x thr x E
        sweep = {}
        for h in ("12h", "24h", "72h"):
            for thr in (0.015, 0.03, 0.07):
                for E in (0.03, 0.05, 0.10):
                    key = "%s_t%d_E%d" % (h, int(thr * 1000), int(E * 100))
                    ent = {}
                    for tag in arms:
                        pk = picks[tag[0]]
                        d, _ = pb_rules(pk, lbl, thr, E, h)
                        pnl, held = d["LABEL"]
                        ag = agg_rule(pnl, pk["ts"].to_numpy(), held)
                        ent[tag[0]] = {"net": ag["net"]["mean"], "out_both": ag["net"]["out_both"],
                                       "years_pos": sum(1 for v in ag["by_year_net"].values()
                                                        if v is not None and v > 0),
                                       "by_year": ag["by_year_net"]}
                    sweep[key] = ent
        res["sweep_pb"] = sweep
    if a.mode in ("sim", "both"):
        need = sorted({int(s) for pk in picks.values() for s in pk["sym"].to_numpy()})
        print("sim: %d syms, %d picks" % (len(need), sum(len(p) for p in picks.values())), flush=True)
        years = [int(x) for x in a.years.split(",")]
        ranges = None
        if a.sim_start:
            rs = datetime.strptime(a.sim_start, "%Y-%m-%d").replace(tzinfo=TZ7)
            re_ = datetime.strptime(a.sim_end, "%Y-%m-%d").replace(tzinfo=TZ7)
            ranges = [(rs, re_, rs.year)]
        outp = sim_1m(picks, id2name, need, a.aero, years, thrE, max_ticks=a.max_ticks,
                      max_days=a.max_days, ranges=ranges, grid=a.grid)
        if a.grid:
            outp, grid_res, tick_ts = outp
            key0 = list(picks)[0]
            gsw = {}
            for (hn, thr, E), (ss, cc_, hh_) in grid_res.items():
                m = cc_ > 0
                if m.sum() == 0:
                    continue
                pt = ss[m] / cc_[m]
                ts_pt = tick_ts[m]
                hd = hh_[m] / cc_[m]
                net = pt - COST_BASE - FUND72 * (hd / float(dict(HS_GRID)[hn]))
                ci = ci_mean(net, ts_pt)
                gsw["%s_t%d_E%d" % (hn, int(thr * 1000), int(E * 100))] = {
                    key0: {"net": round(float(net.mean()), 6), "out_both": ci["out_both"],
                           "raw": [round(ci["raw"][0], 6), round(ci["raw"][1], 6)],
                           "by_year": by_year(net, ts_pt),
                           "years_pos": sum(1 for vv in by_year(net, ts_pt).values()
                                            if vv is not None and vv > 0),
                           "winrate": round(float((net > 0).mean()), 4),
                           "mean_held_h": round(float(hd.mean() / 60.0), 2)}}
            res["sweep_sim"] = gsw
        for tag in outp:
            res["arms"][tag]["sim1m"] = {}
            for rule in ("CUT", "LABEL", "TRAIL", "NOSTOP"):
                recs = outp[tag][rule]
                if not recs:
                    continue
                m0 = np.array([r[0] for r in recs], np.int64)
                ts = m0 * 60000
                pnl = np.array([r[1] for r in recs], np.float64)
                held = np.array([r[2] for r in recs], np.float64)
                reason = [r[3] for r in recs]
                ag = agg_rule(pnl, ts, held, "prorata")
                ag["reason_frac"] = {k: round(reason.count(k) / len(reason), 4)
                                     for k in set(reason)}
                # cross-check: .pb retEnd tren DUNG pick da mo phong
                sym_a = np.array([r[4] for r in recs], np.int32)
                kk = (m0 - 14) * 60000 * RES + sym_a.astype(np.int64)
                ipp = np.clip(np.searchsorted(lbl["key"], kk), 0, len(lbl["key"]) - 1)
                hitm = lbl["key"][ipp] == kk
                if hitm.any():
                    ag["pb_ret_same_mean"] = round(float(
                        lbl["retEnd_72h"][ipp[hitm]].astype(np.float64).mean()), 6)
                    ag["pb_maxfav_same_mean"] = round(float(
                        lbl["maxFav_72h"][ipp[hitm]].astype(np.float64).mean()), 6)
                    ag["pb_cutfrac20_same"] = round(float(
                        (lbl["maxFav_72h"][ipp[hitm]] >= 0.20).mean()), 6)
                    ag["pb_cut20_same_mean"] = round(float(np.where(
                        lbl["maxFav_72h"][ipp[hitm]] >= 0.20, -0.20,
                        -lbl["retEnd_72h"][ipp[hitm]].astype(np.float64)).mean()), 6)
                res["arms"][tag]["sim1m"][rule] = ag
    json.dump(res, open(a.out, "w"), indent=1, default=str)
    print("JSON -> %s (%.0fs)" % (a.out, time.time() - t0), flush=True)


if __name__ == "__main__":
    main()
