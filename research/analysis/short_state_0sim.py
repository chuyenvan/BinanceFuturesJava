#!/usr/bin/env python3
"""short_state_0sim.py — SHORT + GATE STATE theo TUNG COIN (0-sim, DEV<=2025).

State ex-ante (coin,t): tier(notional 30d: big-alt vs rac) · pump_age · vol_decay(vol7/vol30)
· dd_from_high30 · ret7 · ret30.  Do drift SHORT forward (ret24/72h) + hit-rate + tail(maxFav).
Nguon: CLOSES_1H.bin (state) · ds_label15m/*.pb (forward) · Aerospike kline_1m_opt (notional tier).
Pre-reg: docs/prereg/PREREG_SHORT_STATE.md. Output: out/short_state_0sim.json
"""
import glob, json, os, struct, sys
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd

REPO = "/home/ubuntu/src/BinanceFuturesJava"
H = 3600000
DAY = 86400000
BLOCK_H = 72
NREP = 2000
SEED = 20260905
LEG = 1.21
DEV_END_MS = 1767225600000
CLOSES = "/home/ubuntu/java/fsrun/CLOSES_1H.bin"
LB = "/home/ubuntu/ds_label15m"
MAP = "/home/ubuntu/claudedata/oi/symbol_map.csv"
OUT = os.path.join(REPO, "research/analysis/out/short_state_0sim.json")
TZ7 = timezone(timedelta(hours=7))
PUMP_X = 0.15            # pump >= +15%/24h
TIER_SAMPLE_DAYS = 14    # lay mau notional moi 14 ngay
COST24 = 0.0021          # 0.21%/24h


def _rd_varint(b, i):
    r = 0; s = 0
    while True:
        x = b[i]; i += 1; r |= (x & 0x7F) << s
        if not x & 0x80:
            return r, i
        s += 7


def parse_all_min(buf):
    """ALL symbols -> {sym_bytes:(close,volume)}."""
    out = {}; i = 0; n = len(buf)
    while i < n:
        tag, i = _rd_varint(buf, i)
        if tag == 0x0A:
            ln, i = _rd_varint(buf, i); end = i + ln; j = i
            key = None; c = np.nan; v = 0.0
            while j < end:
                t, j = _rd_varint(buf, j)
                if t == 0x0A:
                    kl, j = _rd_varint(buf, j); key = buf[j:j + kl]; j += kl
                elif t == 0x12:
                    vl, j = _rd_varint(buf, j); vb = buf[j:j + vl]; k = 0
                    while k < len(vb):
                        ft, k = _rd_varint(vb, k); fn = ft >> 3; w = ft & 7
                        if w == 5:
                            val = struct.unpack('<f', vb[k:k + 4])[0]; k += 4
                            if fn == 4:
                                c = val
                            elif fn == 5:
                                v = val
                        elif w == 0:
                            _, k = _rd_varint(vb, k)
                        elif w == 2:
                            l2, k = _rd_varint(vb, k); k += l2
                        else:
                            break
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
            if key is not None:
                out[key] = (c, v)
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


def ci_mean(v, ts):
    v = np.asarray(v, float); ts = np.asarray(ts, np.int64)
    m = np.isfinite(v)
    if m.sum() == 0:
        return dict(mean=float("nan"), raw=[None, None], out_both=False, n=0)
    v, ts = v[m], ts[m]
    bk = ts // (BLOCK_H * H)
    _, inv = np.unique(bk, return_inverse=True)
    sums = np.bincount(inv, weights=v); cnts = np.bincount(inv).astype(float)
    k = cnts > 0; sums, cnts = sums[k], cnts[k]
    nb = len(sums); rng = np.random.default_rng(SEED); out = np.empty(NREP)
    for b in range(NREP):
        p = rng.integers(0, nb, nb); out[b] = sums[p].sum() / cnts[p].sum()
    lo, hi = float(np.percentile(out, 2.5)), float(np.percentile(out, 97.5))
    mu = float(v.mean())
    o1 = lo > 0 or hi < 0
    o2 = (mu - (mu - lo) * LEG) > 0 or (mu + (hi - mu) * LEG) < 0
    return dict(mean=mu, raw=[lo, hi], out_both=bool(o1 and o2), n=int(m.sum()))


def by_year(v, ts):
    y = pd.to_datetime(ts, unit="ms", utc=True).tz_convert("Asia/Bangkok").year.to_numpy()
    o = {}
    for yy in (2022, 2023, 2024, 2025):
        m = (y == yy) & np.isfinite(np.asarray(v, float))
        o[str(yy)] = round(float(np.asarray(v, float)[m].mean()), 6) if m.sum() else None
    return o


def read_bins(path):
    DT = np.dtype([("ts", ">i8"), ("sym", ">i2"), ("c", ">f4")])
    a = np.fromfile(path, dtype=DT)
    return a["ts"].astype(np.int64), a["sym"].astype(np.int64), a["c"].astype(float)


def build_states():
    ts, sym, c = read_bins(CLOSES)
    m = ts < DEV_END_MS
    df = pd.DataFrame({"ctime": ts[m] + H, "sym": sym[m], "close": c[m]})
    df = df.drop_duplicates(["sym", "ctime"], keep="first").sort_values(["sym", "ctime"])
    g = df.groupby("sym", sort=False)
    df["ret"] = g["close"].pct_change()
    df["ret7"] = g["close"].pct_change(168)
    df["ret30"] = g["close"].pct_change(720)
    df["ret24"] = g["close"].pct_change(24)
    df["vol7"] = g["ret"].transform(lambda x: x.rolling(168, min_periods=168).std())
    df["vol30"] = g["ret"].transform(lambda x: x.rolling(720, min_periods=720).std())
    df["dd30"] = df["close"] / g["close"].transform(lambda x: x.rolling(720, min_periods=1).max()) - 1
    # pump_age (ngay tu lan tang >= PUMP_X trong 24h)
    idx = np.arange(len(df))
    pump = (df["ret24"] >= PUMP_X).to_numpy()
    gidx = df.groupby("sym", sort=False).cumcount()
    tmp = np.where(pump, gidx, -1)
    # last pump index per group (cummax of index where pump)
    df["_gidx"] = gidx
    lp = df.assign(_p=tmp).groupby("sym", sort=False)["_p"].cummax()
    df["pump_age_d"] = (gidx - lp.to_numpy()) / 24.0
    df.loc[lp.to_numpy() < 0, "pump_age_d"] = np.inf
    df["vol_decay"] = df["vol7"] / df["vol30"]
    keep = ["ctime", "sym", "ret7", "ret30", "vol_decay", "dd30", "pump_age_d", "vol7", "vol30"]
    return df[keep].dropna(subset=["ret30", "vol_decay"])


def label_files():
    fs = sorted(glob.glob(LB + "/funding_label_*.pb"))
    return [f for f in fs if os.path.basename(f).split("_")[2] < "20260101"]


def build_tier(sym_ids, id2name):
    """notional 30d proxy: lay mau moi TIER_SAMPLE_DAYS ngay, sum V*C theo sym; rank."""
    cache = "/tmp/short_state_tier.parquet"
    if os.path.exists(cache):
        print("tier cache hit", flush=True)
        return pd.read_parquet(cache)
    import aerospike, cramjam
    cli = aerospike.client({"hosts": [("127.0.0.1", 3222)]}).connect()
    dec = cramjam.snappy.decompress_raw
    name2id = {v: int(k) for k, v in id2name.items()}
    days = []
    d0 = datetime(2022, 1, 2, tzinfo=TZ7)
    while d0.timestamp() * 1000 < DEV_END_MS:
        days.append(d0)
        d0 += timedelta(days=TIER_SAMPLE_DAYS)
    rows = []
    for dd in days:
        base = dd.replace(hour=0, minute=0, second=0, microsecond=0)
        keys = [("test", "kline_1m_opt", (base + timedelta(minutes=k)).strftime("%Y%m%d-%H%M"))
                for k in range(1440)]
        try:
            brecs = cli.batch_read(keys).batch_records
        except Exception:
            brecs = []
        val = {}
        for rr in brecs:
            if rr.result == 0 and rr.record is not None:
                _k, _m, b = rr.record
                if b and "data" in b:
                    try:
                        rec = parse_all_min(bytes(dec(b["data"])))
                    except Exception:
                        rec = {}
                    for kb, (c, v) in rec.items():
                        sid = name2id.get(kb.decode())
                        if sid is not None and np.isfinite(c):
                            val[sid] = val.get(sid, 0.0) + c * v
        for sid, nt in val.items():
            rows.append((int(base.timestamp() * 1000), sid, nt))
        print("tier sample %s syms=%d" % (base.date(), len(val)), flush=True)
    t = pd.DataFrame(rows, columns=["ts", "sym", "notional"])
    ranks = t.groupby("ts")["notional"].rank(pct=True)
    t["tier_pct"] = ranks
    t = t[["ts", "sym", "tier_pct", "notional"]]
    t.to_parquet(cache, index=False)
    return t


def metrics(sub, name, res):
    n = len(sub)
    r24 = sub["retEnd_24h"].to_numpy(float)
    r72 = sub["retEnd_72h"].to_numpy(float)
    ts = sub["ts"].to_numpy(np.int64)
    short24 = -r24
    ci = ci_mean(short24, ts)
    mf = sub["maxFav_72h"].to_numpy(float)
    res[name] = {
        "n": int(n), "frac": None,
        "ret24_mean": round(float(np.nanmean(r24)), 6), "ret72_mean": round(float(np.nanmean(r72)), 6),
        "short_net24": round(float(np.nanmean(short24) - COST24), 6),
        "ci24_raw": [round(ci["raw"][0], 6), round(ci["raw"][1], 6)],
        "out_both24": ci["out_both"],
        "hit_short24": round(float(np.mean(r24 < 0)), 4), "hit_short72": round(float(np.mean(r72 < 0)), 4),
        "tail_maxfav_mean": round(float(np.nanmean(mf)), 6),
        "tail_maxfav_p95": round(float(np.nanpercentile(mf, 95)), 6),
        "tail_sl10_rate": round(float(np.mean(mf >= 0.10)), 4),
        "by_year_short24": {k: (round(-v, 6) if v is not None else None)
                            for k, v in by_year(r24, ts).items()},
        "years_pos": sum(1 for v in by_year(r24, ts).values() if v is not None and v < 0),
    }
    return res[name]


def main():
    print("=== SHORT_STATE 0-sim ===", flush=True)
    sys.path.insert(0, os.path.join(REPO, "ml/lib"))
    import funding_label_pb as FLPB
    st = build_states()
    print("states rows=%d" % len(st), flush=True)
    st = st.rename(columns={"ctime": "ts"}).sort_values("ts").reset_index(drop=True)
    smap = pd.read_csv(MAP)
    id2name = dict(zip(smap.symId.astype(int), smap.symbol))
    s2i = dict(zip(smap.symbol, smap.symId.astype(np.int64)))
    tr = build_tier(None, id2name)[["ts", "sym", "tier_pct"]].sort_values("ts").reset_index(drop=True)
    cols = ["tEpochMs", "symbol", "retEnd_24h", "retEnd_72h", "maxFav_24h", "maxFav_72h", "nBars_72h"]
    parts = []
    for fp in label_files():
        d = FLPB.read_label(fp, usecols=cols)
        d = d[d["nBars_72h"] >= 288]
        sid = d.symbol.map(s2i)
        k = sid.notna().to_numpy()
        d = d[k].copy(); d["sym"] = sid[k].to_numpy(np.int64)
        d = d.rename(columns={"tEpochMs": "ts"}).sort_values("ts")
        d = pd.merge_asof(d, st, on="ts", by="sym", direction="backward")
        d = pd.merge_asof(d, tr, on="ts", by="sym", direction="backward")
        d = d.dropna(subset=["ret30", "vol_decay"])
        parts.append(d[["ts", "sym", "retEnd_24h", "retEnd_72h", "maxFav_72h",
                        "tier_pct", "pump_age_d", "vol_decay", "ret30", "dd30"]])
        print("  label %s -> %d" % (os.path.basename(fp), len(d)), flush=True)
    df = pd.concat(parts, ignore_index=True)
    print("final rows=%d tier_nan=%.3f" % (len(df), df["tier_pct"].isna().mean()), flush=True)
    res = {"prereg": "PREREG_SHORT_STATE", "pump_x": PUMP_X, "cost24": COST24, "variants": {}}
    def sel(name, mask):
        metrics(df[mask], name, res["variants"])
        res["variants"][name]["frac"] = round(float(mask.mean()), 4)
    sel("ALL", np.ones(len(df), bool))
    # states
    B = (df["pump_age_d"] > 7) & (df["vol_decay"] < 1.0) & (df["ret30"] < 0) & (df["dd30"] < -0.15)
    A = (df["pump_age_d"] <= 2) | (df["vol_decay"] > 1.5)
    big = df["tier_pct"] >= 0.70
    rac = df["tier_pct"] <= 0.30
    sel("B_xadan", B)
    sel("B_xadan_bigalt", B & big)
    sel("B_xadan_rac", B & rac)
    sel("A_guong", A)
    sel("rac_ALL", rac)
    sel("bigalt_ALL", big)
    sel("deep_dd", df["dd30"] < -0.30)
    sel("vol_decay_lt1", df["vol_decay"] < 1.0)
    sel("vol_decay_gt15", df["vol_decay"] > 1.5)
    sel("ret30_neg", df["ret30"] < 0)
    print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk != "by_year_short24"}
                      for k, v in res["variants"].items()}, indent=1), flush=True)
    json.dump(res, open(OUT, "w"), indent=1, default=str)
    print("wrote", OUT, flush=True)


if __name__ == "__main__":
    main()
