"""SHORTVOL_T0 validation V1v, V3v (raw print for hand check), V4v, V5v. V2v is sv_indep.py."""
import os, json, hashlib
import numpy as np, pandas as pd, pyarrow.parquet as pq
WK = os.path.expanduser("~/claude_master/shortvol_t0_wk")
R = json.load(open(os.path.join(WK, "run", "run.json")))
DAY = 86400000
out = {}
# V1v
for sym in ["BTCUSDT", "ETHUSDT"]:
    g = pd.read_parquet(os.path.join(WK, "close1m_%s.parquet" % sym))
    assert g.ts.dtype == np.int64 and g.ts.is_unique and len(g) == 2105280 and (np.diff(g.ts.values) == 60000).all()
    out["V1v_" + sym] = dict(n1m=int(len(g)), filled=int(g.filled.sum()), ts_dtype=str(g.ts.dtype))
for cur in ["BTC", "ETH"]:
    w = pd.read_csv(os.path.join(WK, "run", "weekly_%s.csv" % cur)); d = pd.read_csv(os.path.join(WK, "run", "daily_%s.csv" % cur))
    assert len(w) == 208 and len(d) == 1431 and w.mon_ms.dtype == np.int64 and d.day_ms.dtype == np.int64
    assert (pd.to_datetime(w.mon_ms, unit="ms").dt.dayofweek == 0).all()
    out["V1v_" + cur] = dict(weeks=len(w), vrp_days=len(d), first_week=str(pd.to_datetime(w.mon_ms.iloc[0], unit="ms").date()), last_week=str(pd.to_datetime(w.mon_ms.iloc[-1], unit="ms").date()),
                             first_day=str(pd.to_datetime(d.day_ms.iloc[0], unit="ms").date()), last_day=str(pd.to_datetime(d.day_ms.iloc[-1], unit="ms").date()))
print("V1v", out)
# V3v raw print
h = {c: pd.read_csv(os.path.join(WK, "dvol", "dvol_%s_3600.csv" % c)).set_index("ts").close for c in ["BTC", "ETH"]}
for cur in ["BTC", "ETH"]:
    w = pd.read_csv(os.path.join(WK, "run", "weekly_%s.csv" % cur)); w["mon"] = pd.to_datetime(w.mon_ms, unit="ms").dt.strftime("%Y-%m-%d")
    for m in ["2022-05-09", "2023-06-05", "2025-10-06"]:
        mt = pd.Timestamp(m); t8 = int((mt + pd.Timedelta(hours=8)).value // 10**6); tT = t8 + 7 * DAY
        rows = []
        for t in [t8, tT]:
            ym = pd.to_datetime(t, unit="ms").strftime("%Y-%m")
            k = pq.read_table("/home/ubuntu/vz_e1/raw/kline1m-%s.parquet" % ym, columns=["ts", "sym", "close"], filters=[("sym", "=", cur + "USDT"), ("ts", "=", t)]).to_pandas()
            assert len(k) == 1; rows.append(float(k.close.iloc[0]))
        dv00 = float(h[cur].loc[int(mt.value // 10**6) - 3600000])  # hourly candle 23:00 of Sunday closes at 00:00 Monday
        r = w[w.mon == m].iloc[0]
        print("V3v", cur, m, "raw S0 %.4f ST %.4f dvol00(1h) %.2f | pipe S0 %.4f ST %.4f sigma %.4f prem %.4f fee_leg %.6f pnl %.6f recent %s overlap %s rx14 %.5f"
              % (rows[0], rows[1], dv00, r.S0, r.ST, r.sigma, r.prem, r.fee_leg, r.pnl, r.recent, r.overlap, r.rx14))
        assert abs(rows[0] - r.S0) < 1e-9 and abs(rows[1] - r.ST) < 1e-9 and abs(dv00 / 100 - r.sigma) < 1e-12
# V4v
for cur in ["BTC", "ETH"]:
    s = R[cur]["rv_sanity"]; ok = 0.5 <= s["ratio_1m_5m"] <= 2 and 0.5 <= s["ratio_d_5m"] <= 2
    print("V4v", cur, s, "PASS" if ok else "FAIL"); assert ok
# V5v
for cur in ["BTC", "ETH"]:
    d = pd.read_csv(os.path.join(WK, "dvol", "dvol_%s_1D.csv" % cur))
    exp = np.arange(1638316800000, 1767052800000 + 1, DAY)
    miss = sorted(set(exp) - set(d.ts)); assert d.ts.dtype == np.int64
    print("V5v", cur, "rows", len(d), "exp", len(exp), "missing", miss, "dup", int(d.ts.duplicated().sum()), "ts%day!=0", int((d.ts % DAY != 0).sum()),
          "sha256", hashlib.sha256(open(os.path.join(WK, "dvol", "dvol_%s_1D.csv" % cur), "rb").read()).hexdigest())
    assert not miss and not d.ts.duplicated().any() and (d.ts % DAY == 0).all()
print("VALID PASS")
