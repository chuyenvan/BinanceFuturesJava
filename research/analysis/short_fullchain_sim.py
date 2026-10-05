#!/usr/bin/env python3
"""short_fullchain_sim.py — BUOC 3 (SHORT_FULLCHAIN): SIM SHORT tren DUONG GIA 1m (first-hit THAT).

Chot TRUOC: docs/prereg/PREREG_SHORT_FULLCHAIN.md (9ac83699). KHONG sua .java; stream Aerospike
test.kline_1m_opt (khong ghi dia). Pick = S1 panel decile 0 (ung vien SHORT) moi tick 15m.
Exit = TRAILING T{3,5,8%} x SL cung {10,15,20%} x time-stop {24,72h}; uu tien SL khi cung nen.
Phi base 0,112%; funding pro-rata -0,585%/72h. CI block-72h (2000 rep, seed 20260905, x1.21).
Nhanh: A = khong gate ; B = gate CHAN (bo g<=q10) ; C = gate THUAN (chi g>=q90).
"""
import argparse, json, os, struct, sys, time
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
FUND72 = 0.00585
TS_GRID = ((24, 1440), (72, 4320))
TRAILS = (0.03, 0.05, 0.08)
SLS = (0.10, 0.15, 0.20, 0.30, 0.50, 1.00)   # AMENDMENT A1: 1.00 = no-stop (chi TRAILING/time-stop)
DEV_END_MS = int(datetime(2025, 12, 31, tzinfo=timezone.utc).timestamp() * 1000)
TZ7 = timezone(timedelta(hours=7))


# ───────────── protobuf parsers (copy tu short_pathexit_sim.py, nguon da kiem mae=0) ─────────────
def _rd_varint(b, i):
    r = 0; s = 0
    while True:
        x = b[i]; i += 1; r |= (x & 0x7F) << s
        if not x & 0x80:
            return r, i
        s += 7


def parse_needed(buf, need):
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


# ───────────── exit grid ─────────────
def _ffill(a):
    a = a.copy()
    idx = np.where(~np.isnan(a), np.arange(len(a)), 0)
    np.maximum.accumulate(idx, out=idx)
    return a[idx]


COMBOS = [(T, SL, TS) for T in TRAILS for SL in SLS for TS in (24, 72)]


def exits(hh, ll, cc, P):
    """Tra {combo:(pnl,held_min)}. Trailing+SL cung+time-stop. Uu tien SL khi cung nen."""
    if not np.isfinite(P) or P <= 0 or np.isnan(hh).all():
        return {c: (np.nan, 4320.0) for c in COMBOS}
    hh = _ffill(hh); ll = _ffill(ll); cc = _ffill(cc)
    n = len(hh)
    runmin = np.fmin.accumulate(ll)
    BIG = 10 ** 9
    sl_idx = {}
    for SL in SLS:
        s = hh >= P * (1 + SL)
        sl_idx[SL] = int(np.argmax(s)) if s.any() else BIG
    tr_idx = {}
    tr_lvl = {}
    for T in TRAILS:
        lvl = runmin * (1 + T)
        s = hh >= lvl
        if s.any():
            i = int(np.argmax(s)); tr_idx[T] = i; tr_lvl[T] = float(lvl[i])
        else:
            tr_idx[T] = BIG; tr_lvl[T] = None
    out = {}
    for (T, SL, TS) in COMBOS:
        nn = TS * 60
        a = sl_idx[SL] if sl_idx[SL] < nn else BIG
        b = tr_idx[T] if tr_idx[T] < nn else BIG
        if a < BIG and a <= b:
            out[(T, SL, TS)] = (-SL, float(a + 1))
        elif b < BIG:
            out[(T, SL, TS)] = (-(tr_lvl[T] / P - 1), float(b + 1))
        else:
            out[(T, SL, TS)] = (-(cc[min(nn, n) - 1] / P - 1), float(nn))
    return out


# ───────────── picks ─────────────
def build_picks(panel, min_coin=10):
    sp = pd.read_parquet(panel)
    sp["s1"] = -sp["score"].astype(np.float64)
    sp = sp.sort_values(["ts", "s1"]).reset_index(drop=True)
    n = sp.groupby("ts")["s1"].transform("size")
    sp = sp[n >= min_coin]
    sp["rk"] = sp.groupby("ts")["s1"].rank(method="first")
    sp["q"] = sp.groupby("ts")["rk"].transform(lambda x: pd.qcut(x, 10, labels=False))
    d0 = sp[sp["q"] == 0].copy()
    return d0[["ts", "sym"]].reset_index(drop=True)


# ───────────── CI / agg ─────────────
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
    nb = len(sums)
    rng = np.random.default_rng(SEED)
    out = np.empty(NREP)
    for b in range(NREP):
        pick = rng.integers(0, nb, nb)
        out[b] = sums[pick].sum() / cnts[pick].sum()
    lo, hi = float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))
    mu = float(v.mean())
    ilo, ihi = mu - (mu - lo) * LEG, mu + (hi - mu) * LEG
    o1 = lo > 0 or hi < 0; o2 = ilo > 0 or ihi < 0
    return dict(mean=mu, raw=[lo, hi], n=int(m.sum()), out_raw=bool(o1), out_both=bool(o1 and o2))


def by_year(vals, ts):
    o = {}
    tt = pd.to_datetime(ts, unit="ms", utc=True).tz_convert("Asia/Bangkok").year.to_numpy()
    vv = np.asarray(vals, np.float64)
    for yr in (2022, 2023, 2024, 2025):
        m = (tt == yr) & np.isfinite(vv)
        o[str(yr)] = round(float(vv[m].mean()), 6) if m.sum() else None
    return o


def agg(pnl, held, ts):
    pnl = np.asarray(pnl, np.float64); held = np.asarray(held, np.float64)
    if len(pnl) == 0:
        return {"n_pick": 0, "net": None, "ci_raw": [None, None], "out_raw": False,
                "out_both": False, "winrate": None, "mean_held_h": None, "max_loss": None,
                "by_year": {}, "years_pos": 0}
    net = pnl - COST_BASE - FUND72 * (held / 4320.0)
    fin = np.isfinite(net)
    pt = pd.DataFrame({"ts": ts[fin], "v": net[fin]}).groupby("ts")["v"].mean()
    ci = ci_mean(pt.to_numpy(), pt.index.to_numpy(np.int64))
    npos = sum(1 for v in by_year(net, ts).values() if v is not None and v > 0)
    return {"n_pick": int(fin.sum()), "net": round(ci["mean"], 6),
            "ci_raw": [round(ci["raw"][0], 6), round(ci["raw"][1], 6)],
            "out_raw": ci["out_raw"], "out_both": ci["out_both"],
            "winrate": round(float((net[fin] > 0).mean()), 4),
            "mean_held_h": round(float(held[fin].mean() / 60.0), 2),
            "max_loss": round(float(net[fin].min()), 6),
            "by_year": by_year(net, ts), "years_pos": npos}


# ───────────── stream sim ─────────────
def sim(picks, id2name, gate_min, thresholds, aero, years, max_days=0):
    import aerospike, cramjam
    _h, _p = aero.split(":")
    cli = aerospike.client({"hosts": [(_h, int(_p))]}).connect()
    dec = cramjam.snappy.decompress_raw
    id2name_b = {int(k): v.encode() for k, v in id2name.items()}
    sym2id = {v: int(k) for k, v in id2name.items()}
    # ticks keyed theo PHUT VAO = ts//60000 + 14 ; entryP doc close tai phut do
    ticks = defaultdict(list)
    for ts, s in zip(picks["ts"].to_numpy(), picks["sym"].to_numpy()):
        ticks[int(ts) // 60000 + 14].append(int(s))
    all_m0 = sorted(ticks)
    union = sorted({s for v in ticks.values() for s in v})
    rows = {s: i for i, s in enumerate(union)}
    rec_pnl = {c: [] for c in COMBOS}
    rec_held = {c: [] for c in COMBOS}
    rec_ts = []; rec_sym = []; rec_g = []
    for rng_start, rng_end, y in years:
        base_m = int(rng_start.timestamp() // 60)
        nmin = int(round((rng_end - rng_start).total_seconds() // 60)) + 1
        arr = np.full((len(union), nmin, 3), np.nan, np.float32)
        sel = [m0 for m0 in all_m0 if base_m <= m0 and (m0 + 4320) <= (base_m + nmin - 1)]
        tset = set(sel)
        if max_days:
            tset = set(sorted(tset)[:max_days])
        rc = defaultdict(int); active_b = set(); add_ptr = rem_ptr = 0
        entryP = {}; t0 = time.time()
        ndays = (nmin + 1439) // 1440
        if max_days:
            ndays = min(ndays, max_days + 83)     # smoke: chi stream du 72h sau pick cuoi
        done = 0
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
                need = active_b if not cur else (active_b | {id2name_b[s] for s in cur})
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
                    for s in ticks[m]:
                        v = rec.get(id2name_b[s])
                        if v is not None:
                            entryP[(m, s)] = v[2]
                while add_ptr < len(sel) and sel[add_ptr] <= m - 1:
                    for s in ticks[sel[add_ptr]]:
                        rc[s] += 1; active_b.add(id2name_b[s])
                    add_ptr += 1
                while rem_ptr < len(sel) and sel[rem_ptr] <= m - 1 - 4320:
                    for s in ticks[sel[rem_ptr]]:
                        rc[s] -= 1
                        if rc[s] == 0:
                            del rc[s]; active_b.discard(id2name_b[s])
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
                    for s in ticks[m0f]:
                        P = entryP.get((m0f, s), np.nan)
                        row = rows[s]
                        ex = exits(arr[row, i0:i0 + 4320, 0], arr[row, i0:i0 + 4320, 1],
                                   arr[row, i0:i0 + 4320, 2], P)
                        g = gate_min.get(m0f, np.nan)
                        rec_ts.append((m0f - 14) * 60000); rec_sym.append(s); rec_g.append(g)
                        for c in COMBOS:
                            pn, hd = ex[c]
                            rec_pnl[c].append(pn); rec_held[c].append(hd)
                        done += 1
            if di % 20 == 0:
                print("  y=%d day %d/%d done=%d %.0fs" % (y, di, ndays, done, time.time() - t0),
                      flush=True)
        print("YEAR %d DONE done=%d %.0fs" % (y, done, time.time() - t0), flush=True)
    return rec_ts, rec_sym, rec_g, rec_pnl, rec_held


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--panel", default="/home/ubuntu/ledger/pred_s1a2x1.parquet")
    ap.add_argument("--gate-csv", default="/home/ubuntu/src/BinanceFuturesJava/research/parity/data/p15_dev.csv")
    ap.add_argument("--map-csv", default="/home/ubuntu/claudedata/oi/symbol_map.csv")
    ap.add_argument("--aero", default="127.0.0.1:3222")
    ap.add_argument("--years", default="2022,2023,2024,2025")
    ap.add_argument("--max-days", type=int, default=0)
    ap.add_argument("--out", default="")
    ap.add_argument("--raw-out", default="")   # npz per-pick (de merge nhieu phien)
    a = ap.parse_args()
    t0 = time.time()
    pk = build_picks(a.panel)
    pk = pk[(pk["ts"] + 72 * H) <= DEV_END_MS].reset_index(drop=True)
    print("picks decile0 n=%d ts %s..%s" % (len(pk), pk.ts.min(), pk.ts.max()), flush=True)
    g = pd.read_csv(a.gate_csv, usecols=["ts", "predRisk4H"])
    g["min"] = g["ts"] // 60000
    gmin = g.groupby("min")["predRisk4H"].first()
    gate_min = gmin.to_dict()
    q10 = float(gmin.quantile(0.10)); q90 = float(gmin.quantile(0.90))
    print("gate q10=%.6f q90=%.6f" % (q10, q90), flush=True)
    smap = pd.read_csv(a.map_csv)
    id2name = dict(zip(smap.symId.astype(int), smap.symbol))
    years = [(datetime(int(x), 1, 1, tzinfo=TZ7),
              datetime(int(x), 12, 31, 23, 59, tzinfo=TZ7) if int(x) == 2025
              else datetime(int(x) + 1, 1, 3, 0, 0, tzinfo=TZ7), int(x))
             for x in a.years.split(",")]
    rec_ts, rec_sym, rec_g, rec_pnl, rec_held = sim(pk, id2name, gate_min, None, a.aero,
                                                    years, max_days=a.max_days)
    if a.raw_out:
        np.savez(a.raw_out, ts=np.asarray(rec_ts, np.int64), g=np.asarray(rec_g, np.float32),
                 pnl=np.asarray([rec_pnl[c] for c in COMBOS], np.float32).T,
                 held=np.asarray([rec_held[c] for c in COMBOS], np.float32).T,
                 combos=np.array(["%d|%d|%d" % (int(c[0] * 100), int(c[1] * 100), c[2])
                                  for c in COMBOS]))
        print("RAW -> %s n=%d" % (a.raw_out, len(rec_ts)), flush=True)
        if not a.out:
            return
    rec_ts = np.asarray(rec_ts, np.int64); rec_g = np.asarray(rec_g, np.float64)
    keep = {"A_all": np.ones(len(rec_ts), bool),
            "B_CHAN_q10": ~(rec_g <= q10),
            "C_THUAN_q90": (rec_g >= q90),
            "D_NGHICH_q10": (rec_g <= q10)}   # exploratory (buoc 2 cho thay day la huong CO tin hieu)
    miss_g = ~np.isfinite(rec_g)
    res = {"prereg": "PREREG_SHORT_FULLCHAIN", "cost_base": COST_BASE, "fund72": FUND72,
           "gate": {"q10": q10, "q90": q90, "nan_gate_frac": round(float(miss_g.mean()), 5)},
           "n_pick_total": int(len(rec_ts)), "picks_ts_range": [int(rec_ts.min()), int(rec_ts.max())],
           "variants": {}}
    for vn, mask in keep.items():
        mask = mask & np.isfinite(rec_g)
        block = {"n_pick": int(mask.sum()), "frac": round(float(mask.mean()), 4), "grid": {}}
        for c in COMBOS:
            pnl = np.asarray(rec_pnl[c], np.float64)[mask]
            held = np.asarray(rec_held[c], np.float64)[mask]
            key = "T%d_SL%d_TS%dh" % (int(c[0] * 100), int(c[1] * 100), c[2])
            block["grid"][key] = agg(pnl, held, rec_ts[mask])
        res["variants"][vn] = block
        # in tom tat nhanh
        print("VARIANT %s n=%d frac=%.3f" % (vn, block["n_pick"], block["frac"]), flush=True)
    # so to hop GO (A: net>0 & out_both & >=3/4 nam)
    go = []
    for vn in keep:
        for k, r in res["variants"][vn]["grid"].items():
            if r["net"] is not None and r["net"] > 0 and r["out_both"] and r["years_pos"] >= 3:
                go.append((vn, k, r["net"], r["years_pos"]))
    res["go_configs"] = go
    print("GO configs:", go, flush=True)
    json.dump(res, open(a.out, "w"), indent=1, default=str)
    print("JSON -> %s (%.0fs)" % (a.out, time.time() - t0), flush=True)


if __name__ == "__main__":
    main()
