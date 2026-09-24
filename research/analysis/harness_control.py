#!/usr/bin/env python3
"""HARNESS_CONTROL — sinh tin hieu cho phep hieu chuan (calibration) bo do.

A/ POSITIVE CONTROL: MOM15 (market-level alias SMALL_DOWN_15M = rateDown15MAvg < -0.028)
   -> ev1.csv (k=1, dung live SMALL_DOWN_15M) + ev2.csv (k=2, so tao-voi-tao voi vong truoc)
B/ NEGATIVE CONTROL (placebo "day-permute": giu symbol + giu chinh xac phut-trong-ngay, ngay
   ngau nhien deu tren DEV) -> placebo.npz (net [N_ev1, 200]); B-secondary "same-minute random
   symbol" -> pool.npz
C/ MDE: chay tren chuoi placebo (script stats).

Pre-reg: docs/prereg/PREREG_HARNESS_CONTROL.md (commit 9611823) — commit TRUOC khi chay; khong sua thiet ke.
Thuan Python, 0-sim, khong Java, khong push, khong cham 2026.
Nguon: raw/<sym>.f32 = Aerospike set kline_1m_opt da extract causal (cung nguon BD/MOM15);
funding = Aerospike funding_data (chi DOC).

Output /tmp/harness_ctl/{ev1.csv,ev2.csv,pool.npz,placebo.npz,rd15.npz,fires_k*.npy,SIG_DONE}
"""
import os
import glob
import json
import logging
import sys
import time
from datetime import datetime, timezone

import numpy as np

RAW = "/home/ubuntu/claudedata/rvb_1m/raw"
OUT = "/tmp/harness_ctl"
os.makedirs(OUT, exist_ok=True)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("hctl")

# ---- LOCKED params (PREREG §2/§3/§4) ----
HOLD = 1440
TAKER = 0.0005
FEE = TAKER * 2          # 0.10% (mo + dong)
SLIP = 0.5
KTOP = 100
KFRAC = 4 / 5
MIN_SYM = 50
MOM15_THR = -0.028
NREP_PLACEBO = 200
SEED = 20260905

UTC = timezone.utc
DT = np.dtype([("ts", "<i4"), ("o", "<f4"), ("h", "<f4"), ("l", "<f4"), ("c", "<f4"), ("v", "<f4")])


def min_of(y, mo, d):
    return int(datetime(y, mo, d, tzinfo=UTC).timestamp() // 60)


BASE = min_of(2021, 1, 1)
DEV_START = min_of(2022, 1, 1)
DEV_END = min_of(2024, 7, 1)          # exclusive -> DEV = 2022-01-01..2024-06-30
SAMPLE_END = min_of(2026, 1, 1)       # exclusive
NMIN = SAMPLE_END - BASE
D0 = DEV_START - BASE
D1 = DEV_END - BASE
FILES = sorted(glob.glob(RAW + "/*.f32"))


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


def derive(o, h, c):
    """rc = C/O-1 ; d15 = C/max(H,15)-1 (chep nguyen bigup_mediumdown.py)."""
    with np.errstate(invalid="ignore", divide="ignore"):
        rc = np.where(o > 0, c / o - 1.0, np.nan).astype(np.float32)
    n = len(h)
    d15 = np.full(n, np.nan, dtype=np.float32)
    if n >= 15:
        win = np.lib.stride_tricks.sliding_window_view(h, 15)
        mx = win.max(axis=1)
        with np.errstate(invalid="ignore", divide="ignore"):
            d15[14:] = np.where(mx > 0, c[14:] / mx - 1.0, np.nan).astype(np.float32)
    return rc, d15


def per_minute_stats(sorted_vals, offsets, cnt, nmin, block=40000):
    """bottom-k mean moi phut, k = min(100, floor(n*4/5)) — CHEP NGUYEN bigup_mediumdown.py."""
    maxc = int(cnt.max())
    lo_arr = np.full(nmin, np.nan, dtype=np.float32)
    dense = np.empty((block, maxc), dtype=np.float32)
    for b0 in range(0, nmin, block):
        b1 = min(b0 + block, nmin)
        B = b1 - b0
        cb = cnt[b0:b1]
        tot = int(cb.sum())
        dens = dense[:B]
        dens[:] = np.nan
        if tot:
            rows = np.repeat(np.arange(B), cb)
            cols = np.arange(tot) - np.repeat(offsets[b0:b1] - offsets[b0], cb)
            dens[rows, cols] = sorted_vals[offsets[b0]:offsets[b0] + tot]
        dens.sort(axis=1)
        cs = np.cumsum(dens, axis=1, dtype=np.float32)
        kk = np.minimum(KTOP, (cb * KFRAC).astype(np.int64))
        ok = kk >= 1
        idxk = np.clip(kk - 1, 0, maxc - 1)
        lo = np.full(B, np.nan, dtype=np.float32)
        if ok.any():
            r = np.where(ok)[0]
            lo[r] = cs[r, idxk[r]] / kk[r]
        lo_arr[b0:b1] = lo
    return lo_arr


def stage_agg_fire():
    """pass1 (count) + pass2 (scatter d15) -> rd15 -> fire MOM15 -> chon event top-k co lock."""
    log.info("symbols=%d NMIN=%d", len(FILES), NMIN)
    cnt = np.zeros(NMIN, dtype=np.int64)
    t0 = time.time()
    for i, p in enumerate(FILES):
        r = load_sym(p)
        if r is None:
            continue
        ts, o, h, l, c = r
        rc, d15 = derive(o, h, c)
        rel = (ts - BASE).astype(np.int64)
        use = np.isfinite(rc) & np.isfinite(d15)
        cnt += np.bincount(rel[use], minlength=NMIN)
        if i % 150 == 0:
            log.info("pass1 %d/%d el=%.0fs", i, len(FILES), time.time() - t0)
    offsets = np.zeros(NMIN + 1, dtype=np.int64)
    np.cumsum(cnt, out=offsets[1:])
    total = int(offsets[-1])
    log.info("pass1 done total_rows=%d el=%.0fs", total, time.time() - t0)

    d15_s = np.empty(total, dtype=np.float32)
    sym_s = np.empty(total, dtype=np.int16)
    cur = np.zeros(NMIN, dtype=np.int64)
    t0 = time.time()
    for i, p in enumerate(FILES):
        r = load_sym(p)
        if r is None:
            continue
        ts, o, h, l, c = r
        rc, d15 = derive(o, h, c)
        rel = (ts - BASE).astype(np.int64)
        use = np.isfinite(rc) & np.isfinite(d15)
        rel = rel[use]
        if len(rel) == 0:
            continue
        dest = offsets[rel] + cur[rel]
        cur[rel] += 1
        d15_s[dest] = d15[use]
        sym_s[dest] = i
        if i % 150 == 0:
            log.info("pass2 %d/%d el=%.0fs", i, len(FILES), time.time() - t0)
    log.info("pass2 done el=%.0fs", time.time() - t0)

    t0 = time.time()
    rd15 = per_minute_stats(d15_s, offsets, cnt, NMIN)
    log.info("rd15 done el=%.0fs", time.time() - t0)
    nfire = int((np.isfinite(rd15) & (cnt >= MIN_SYM) & (rd15 < MOM15_THR)).sum())
    log.info("rateDown15MAvg: finite=%d | < %.3f: %d phut (%.4f%% cua NMIN)",
             int(np.isfinite(rd15).sum()), MOM15_THR, nfire, 100.0 * nfire / NMIN)
    np.savez_compressed(OUT + "/rd15.npz", rd15=rd15, cnt=cnt.astype(np.int32))

    ok = np.isfinite(rd15) & (cnt >= MIN_SYM) & (rd15 < MOM15_THR)
    F = np.flatnonzero(ok)
    res = {}
    for k in (1, 2):
        unlock = np.full(len(FILES), -1, dtype=np.int64)
        rows = []
        t0 = time.time()
        for n, m in enumerate(F):
            a = int(offsets[m])
            b = int(offsets[m + 1])
            if b - a < 1:
                continue
            cand = d15_s[a:b]
            syms = sym_s[a:b]
            order = np.argsort(cand, kind="stable")
            picked = 0
            for oi in order:
                s = int(syms[oi])
                if unlock[s] > m:
                    continue
                unlock[s] = m + HOLD
                rows.append((m + BASE, s))
                picked += 1
                if picked >= k:
                    break
            if n % 25000 == 0:
                log.info("k=%d fire %d/%d events=%d el=%.0fs", k, n, len(F), len(rows), time.time() - t0)
        res[k] = np.array(rows, dtype=np.int64).reshape(-1, 2)
        dev = int(((res[k][:, 0] >= DEV_START) & (res[k][:, 0] < DEV_END)).sum()) if len(res[k]) else 0
        log.info("k=%d events=%d (DEV=%d)", k, len(res[k]), dev)
        np.save(OUT + "/fires_k%d.npy" % k, res[k])
    open(OUT + "/AGG_DONE", "w").write("ok\n")


def funding_lookup():
    import aerospike
    import cramjam
    cli = aerospike.client({"hosts": [("127.0.0.1", 3222)]}).connect()
    cache = {}

    def get(name):
        if name in cache:
            return cache[name]
        try:
            k = cli.get(("test", "funding_data", name))
            bd = k[2]
            if not bd or "f_data" not in bd:
                cache[name] = None
                return None
            d = json.loads(bytes(cramjam.snappy.decompress_raw(bd["f_data"])))
            arr = sorted((int(t), float(r)) for t, r in d.items())
            cache[name] = (np.array([x[0] for x in arr], dtype=np.int64),
                           np.array([x[1] for x in arr], dtype=np.float64))
            return cache[name]
        except Exception as e:
            log.warning("funding %s fail %r", name, e)
            cache[name] = None
            return None
    return cli, get


def build_symbol(path, get_fund):
    """dense arrays + prev-present + funding cumulative cho 1 symbol."""
    r = load_sym(path)
    if r is None:
        return None
    ts, o, h, l, c = r
    rc, d15 = derive(o, h, c)
    valid = np.isfinite(rc) & np.isfinite(d15)
    rel = (ts - BASE).astype(np.int64)
    span = int(rel[-1]) + 1
    cD = np.full(span, np.nan, dtype=np.float32)
    hD = np.full(span, np.nan, dtype=np.float32)
    lD = np.full(span, np.nan, dtype=np.float32)
    cD[rel] = c
    hD[rel] = h
    lD[rel] = l
    pres = np.zeros(span, dtype=bool)
    pres[rel[valid]] = True
    idx = np.where(pres, np.arange(span, dtype=np.int64), -1)
    prev_local = np.maximum.accumulate(idx)
    prev_full = np.full(NMIN, -1, dtype=np.int64)
    prev_full[:span] = prev_local
    if span < NMIN:
        prev_full[span:] = prev_local[-1]
    fr = get_fund(os.path.basename(path)[:-4])
    cum = np.zeros(span + 1, dtype=np.float64)
    if fr is not None:
        ft_ms, fval = fr
        fp = (ft_ms // 60000) - BASE
        sel = (fp >= 0) & (fp < span)
        if sel.any():
            fsum = np.zeros(span, dtype=np.float64)
            np.add.at(fsum, fp[sel], fval[sel])
            cum[1:] = np.cumsum(fsum)
    return dict(cD=cD, hD=hD, lD=lD, pres=pres, prev_full=prev_full, cum=cum, span=span)


def returns_for(epos_arr, S):
    """tra (raw, slip, fund, net, hold, cens) cho dense-index entry epos_arr (harness §2)."""
    epos_arr = np.asarray(epos_arr, dtype=np.int64)
    n = len(epos_arr)
    raw = np.full(n, np.nan)
    slip = np.full(n, np.nan)
    fund = np.full(n, np.nan)
    net = np.full(n, np.nan)
    hold = np.zeros(n, dtype=np.int64)
    cens = epos_arr + HOLD > NMIN - 1
    ep = epos_arr[~cens]
    if len(ep) == 0:
        return raw, slip, fund, net, hold, cens
    xpos = S["prev_full"][ep + HOLD]
    good = xpos > ep
    if good.any():
        e = ep[good]
        xp = xpos[good]
        entry = S["cD"][e].astype(np.float64)
        exitp = S["cD"][xp].astype(np.float64)
        r = exitp / entry - 1.0
        sl = SLIP * (S["hD"][e].astype(np.float64) - S["lD"][e].astype(np.float64)) / entry
        fu = S["cum"][xp] - S["cum"][e]
        src = np.flatnonzero(~cens)[good]
        raw[src] = r
        slip[src] = sl
        fund[src] = fu
        net[src] = r - FEE - sl - fu
        hold[src] = xp - e
    return raw, slip, fund, net, hold, cens


def emit(fh, name, emin, S):
    epos = emin - BASE
    keep = (epos >= 0) & (epos < S["span"]) & S["pres"][np.clip(epos, 0, S["span"] - 1)]
    epos = epos[keep]
    emin = emin[keep]
    if len(epos) == 0:
        return 0, 0, 0
    raw, slip, fund, net, hold, cens = returns_for(epos, S)
    nw = ncens = nshort = 0
    for j in range(len(epos)):
        if cens[j]:
            ncens += 1
            continue
        if not np.isfinite(net[j]):
            continue
        xp = int(S["prev_full"][epos[j] + HOLD])
        exv = float(S["cD"][xp]) if xp > epos[j] else np.nan
        yr = int(datetime.utcfromtimestamp(int(emin[j]) * 60).strftime("%Y"))
        if hold[j] < HOLD:
            nshort += 1
        fh.write("%s,%d,%d,%.8g,%.8g,%d,%d,%.6f,%.6f,%.6f,%.6f\n" % (
            name, int(emin[j]), yr, float(S["cD"][epos[j]]), exv,
            int(hold[j]), 1 if hold[j] < HOLD else 0, raw[j], slip[j], fund[j], net[j]))
        nw += 1
    return nw, ncens, nshort


def stage_events():
    f1 = np.load(OUT + "/fires_k1.npy")
    f2 = np.load(OUT + "/fires_k2.npy")
    ev1_by_sym, ev2_by_sym = {}, {}
    for (m, s) in f1:
        ev1_by_sym.setdefault(int(s), []).append(int(m))
    for (m, s) in f2:
        ev2_by_sym.setdefault(int(s), []).append(int(m))
    E_minutes = np.unique(f1[:, 0])
    is_E = np.zeros(NMIN, dtype=bool)
    is_E[E_minutes - BASE] = True   # f1[:,0] la phut tuyet doi; is_E danh theo offset tu BASE
    log.info("primary events=%d syms=%d distinct event minutes=%d", len(f1), len(ev1_by_sym), len(E_minutes))

    cli, get_fund = funding_lookup()
    h1 = open(OUT + "/ev1.csv", "w")
    h2 = open(OUT + "/ev2.csv", "w")
    hdr = "sym,entry_ts,year,entry,exit,hold,delist,raw_ret,slip,funding,net_ret\n"
    h1.write(hdr)
    h2.write(hdr)

    rngs = [np.random.default_rng(SEED + rr + 1) for rr in range(NREP_PLACEBO)]

    pool_min, pool_sym, pool_net = [], [], []
    plac_net, plac_min, plac_sym = [], [], []
    n_cens = n_short = 0
    t0 = time.time()
    for i, p in enumerate(FILES):
        name = os.path.basename(p)[:-4]
        evs1 = ev1_by_sym.get(i)
        evs2 = ev2_by_sym.get(i)
        if not evs1 and not evs2 and len(E_minutes) == 0:
            continue
        S = build_symbol(p, get_fund)
        if S is None:
            continue
        if evs1:
            w, c_, s_ = emit(h1, name, np.array(sorted(evs1), dtype=np.int64), S)
            n_cens += c_
            n_short += s_
        if evs2:
            emit(h2, name, np.array(sorted(evs2), dtype=np.int64), S)
        # (b) pool for B-secondary
        pp = np.flatnonzero(is_E[:S["span"]] & S["pres"])
        if len(pp):
            raw, slip, fund, net, hold, cens = returns_for(pp, S)
            good = np.isfinite(net)
            if good.any():
                pool_min.append((pp[good] + BASE).astype(np.int32))
                pool_sym.append(np.full(int(good.sum()), i, dtype=np.int16))
                pool_net.append(net[good].astype(np.float32))
        # (c) placebo day-permute (chi tren event cua A-PRIMARY)
        if evs1:
            for m in sorted(evs1):
                p_i = m - BASE
                off = p_i % 1440
                start = D0 + ((off - D0) % 1440)
                ps = np.arange(start, D1, 1440, dtype=np.int64)
                ps = ps[(ps + HOLD <= NMIN - 1) & (ps < S["span"]) & (ps != p_i)]
                ps = ps[S["pres"][ps]]
                if len(ps) == 0:
                    plac_net.append(np.full(NREP_PLACEBO, np.nan, dtype=np.float32))
                else:
                    draws = np.array([rngs[rr].integers(0, len(ps)) for rr in range(NREP_PLACEBO)],
                                     dtype=np.int64)
                    raw, slip, fund, net, hold, cens = returns_for(ps[draws], S)
                    plac_net.append(net.astype(np.float32))
                plac_min.append(m)
                plac_sym.append(i)
        if i % 100 == 0:
            log.info("pass3 %d/%d %s el=%.0fs pool_rows=%d", i, len(FILES), name, time.time() - t0,
                     int(sum(len(x) for x in pool_min)))
    h1.close()
    h2.close()
    cli.close()

    pm = np.concatenate(pool_min) if pool_min else np.zeros(0, dtype=np.int32)
    ps_ = np.concatenate(pool_sym) if pool_sym else np.zeros(0, dtype=np.int16)
    pn = np.concatenate(pool_net) if pool_net else np.zeros(0, dtype=np.float32)
    np.savez(OUT + "/pool.npz", minute=pm, sym=ps_, net=pn)
    np.savez(OUT + "/placebo.npz", net=np.array(plac_net, dtype=np.float32),
             minute=np.array(plac_min, dtype=np.int64), sym=np.array(plac_sym, dtype=np.int64))
    log.info("pool rows=%d ; placebo events=%d ; ev1 cens=%d short_delist=%d",
             len(pm), len(plac_min), n_cens, n_short)
    open(OUT + "/SIG_DONE", "w").write("done\n")


if __name__ == "__main__":
    stage = sys.argv[1] if len(sys.argv) > 1 else "all"
    if stage in ("all", "agg"):
        stage_agg_fire()
    if stage in ("all", "events"):
        stage_events()
