"""TREND_T1 step 1: resample kline 1m -> daily (UTC) + hourly boundary prices. Streaming per month.
Outputs (WK=~/claude_master/trend_t1_wk):
  daily/YYYY-MM.parquet : sym, day(int64 ms 00:00 UTC), n_rows, n_active, close (close of last row of day),
                          ts_last, px01 (close of first row with minute>=1), px01_min, px01_active,
                          qv (sum quote_volume), first_active_ts, last_active_ts
  hourly/YYYY-MM.parquet: sym, t (int64 ms, = open_ts of hh:59 bar + 60000, i.e. price AT hour boundary), p (close)
Assertions: ts int64, ts%60000==0, no dup (sym,ts), n_rows<=1440 per sym-day.
"""
import os, sys, json, time
import numpy as np, pandas as pd, pyarrow.parquet as pq

RAW = "/home/ubuntu/vz_e1/raw/kline1m-%s.parquet"
WK = os.path.expanduser("~/claude_master/trend_t1_wk")
DAY = 86400000
MIN = 60000

def months():
    y, m = 2021, 12
    while (y, m) <= (2025, 12):
        yield "%04d-%02d" % (y, m)
        m += 1
        if m == 13: y, m = y + 1, 1

def do_month(mo):
    t0 = time.time()
    t = pq.read_table(RAW % mo, columns=["ts", "sym", "close", "quote_volume", "active"])
    assert str(t.schema.field("ts").type) == "int64", t.schema
    symcol = t.column("sym").combine_chunks()
    if hasattr(symcol, "dictionary"):
        dic = np.array(symcol.dictionary.to_pylist(), dtype=object)
        codes = symcol.indices.to_numpy(zero_copy_only=False).astype(np.int64)
    else:
        u, codes = np.unique(np.array(symcol.to_pylist(), dtype=object), return_inverse=True)
        dic = u; codes = codes.astype(np.int64)
    ts = t.column("ts").to_numpy().astype(np.int64, copy=False)
    assert ts.dtype == np.int64
    close = t.column("close").to_numpy()
    qv = t.column("quote_volume").to_numpy()
    act = t.column("active").to_numpy(zero_copy_only=False).astype(bool)
    del t
    assert (ts % MIN == 0).all(), "ts not minute aligned"
    o = np.lexsort((ts, codes))
    ts = ts[o]; codes = codes[o]; close = close[o]; qv = qv[o]; act = act[o]
    del o
    # dup check
    same = (np.diff(codes) == 0) & (np.diff(ts) == 0)
    assert not same.any(), "dup (sym,ts)"
    day = (ts // DAY) * DAY
    minute = (ts - day) // MIN
    key = codes * 10**6 + (day // DAY)
    st = np.concatenate([[0], np.flatnonzero(np.diff(key)) + 1])
    en = np.concatenate([st[1:], [len(ts)]])
    n_rows = en - st
    assert (n_rows <= 1440).all(), "more than 1440 rows per day"
    gkey = key[st]
    n_active = np.add.reduceat(act.astype(np.int64), st)
    qv_sum = np.add.reduceat(qv, st)
    close_last = close[en - 1]; ts_last = ts[en - 1]
    # px01: first row with minute>=1 within group
    m1 = minute >= 1
    idx1 = np.flatnonzero(m1)
    k1 = key[idx1]
    # first occurrence per key
    u1, f1 = np.unique(k1, return_index=True)
    pos = np.searchsorted(u1, gkey)
    has1 = (pos < len(u1)) & (u1[np.minimum(pos, len(u1) - 1)] == gkey)
    r1 = idx1[f1[np.minimum(pos, len(u1) - 1)]]
    px01 = np.where(has1, close[r1], np.nan)
    px01_min = np.where(has1, minute[r1], -1)
    px01_act = np.where(has1, act[r1], False)
    # active first/last ts
    ia = np.flatnonzero(act)
    ka = key[ia]
    ua, fa = np.unique(ka, return_index=True)
    ua2, la = np.unique(ka[::-1], return_index=True)
    la = len(ka) - 1 - la
    pa = np.searchsorted(ua, gkey); hasa = (pa < len(ua)) & (ua[np.minimum(pa, len(ua) - 1)] == gkey)
    fat = np.where(hasa, ts[ia[fa[np.minimum(pa, len(ua) - 1)]]], -1)
    lat = np.where(hasa, ts[ia[la[np.minimum(pa, len(ua) - 1)]]], -1)
    d = pd.DataFrame(dict(sym=dic[codes[st]].astype(str), day=day[st].astype(np.int64), n_rows=n_rows.astype(np.int32),
                          n_active=n_active.astype(np.int32), close=close_last, ts_last=ts_last.astype(np.int64),
                          px01=px01, px01_min=px01_min.astype(np.int16), px01_active=px01_act.astype(bool), qv=qv_sum,
                          first_active_ts=fat.astype(np.int64), last_active_ts=lat.astype(np.int64)))
    assert d.day.dtype == np.int64 and d.ts_last.dtype == np.int64
    assert not d.duplicated(["sym", "day"]).any()
    d.to_parquet(os.path.join(WK, "daily", mo + ".parquet"), index=False)
    # hourly boundary prices: rows with minute%60==59
    ih = np.flatnonzero(minute % 60 == 59)
    h = pd.DataFrame(dict(sym=dic[codes[ih]].astype(str), t=(ts[ih] + MIN).astype(np.int64), p=close[ih]))
    assert h.t.dtype == np.int64
    h.to_parquet(os.path.join(WK, "hourly", mo + ".parquet"), index=False)
    ndays = int((day.max() - day.min()) // DAY + 1)
    rep = dict(month=mo, rows=int(len(ts)), syms=int(len(dic[np.unique(codes)])), sym_days=int(len(d)),
               full1440=int((d.n_rows == 1440).sum()), partial=int((d.n_rows < 1440).sum()),
               px01_not_min1=int((d.px01_min != 1).sum()), days=ndays, hourly_rows=int(len(h)), secs=round(time.time() - t0, 1))
    print(json.dumps(rep), flush=True)
    return rep

if __name__ == "__main__":
    os.makedirs(os.path.join(WK, "daily"), exist_ok=True)
    os.makedirs(os.path.join(WK, "hourly"), exist_ok=True)
    reps = []
    for mo in months():
        if os.path.exists(os.path.join(WK, "daily", mo + ".parquet")) and os.path.exists(os.path.join(WK, "hourly", mo + ".parquet")):
            continue
        reps.append(do_month(mo))
    json.dump(reps, open(os.path.join(WK, "resample_report_%d.json" % int(time.time())), "w"), indent=1)
    print("DONE")
