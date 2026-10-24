"""FEE0 V4 (kiem tay 5 lenh maker) + V5 (look-ahead S8 / Q4-E). Doc du lieu tho truc tiep."""
import glob, io, json, os, zipfile
import numpy as np, pandas as pd
WK = os.path.expanduser("~/claude_master/fee0_wk")
MS = 60000
out = {}
# ---- V4
pick = json.load(open(WK + "/v4_pick.json"))
U = []
for p in sorted(glob.glob(WK + "/k1m/BTCUSDC/*.zip")):
    with zipfile.ZipFile(p) as z:
        x = pd.read_csv(io.BytesIO(z.read(z.namelist()[0])), header=None, dtype=str)
    x = x[x[0].str.isdigit()]
    U.append(pd.DataFrame({"ts": x[0].astype(np.int64), "high": x[2].astype(float), "low": x[3].astype(float), "close": x[4].astype(float)}))
U = pd.concat(U).drop_duplicates("ts").set_index("ts").sort_index()
hs = json.load(open(WK + "/half_spread.json"))["BTCUSDC"]
v4 = []
for k in pick:
    t = k["t_in"]; p0 = U.close[t - MS]
    w = U.loc[t: t + 14 * MS]
    assert len(w) == 15 and w.index[0] == t
    first = next((int(i) for i, l in w.low.items() if l < p0), None)
    fill = first is not None
    r = (U.close[k["t_out"] - MS] / p0 - 1) - 0.0002 - 0.0004 - hs if fill else None
    rec = {"sig": k["sig"], "t_in_utc": str(pd.to_datetime(t, unit="ms")), "P0": p0, "min_low_15": float(w.low.min()),
           "first_through_utc": str(pd.to_datetime(first, unit="ms")) if fill else None, "fill_hand": fill, "fill_pipe": k["fill_W15"],
           "r_hand_exfund": r, "r_pipe": k["r_M1"], "agree": fill == k["fill_W15"]}
    v4.append(rec); print("V4", rec)
# them lenh KHONG khop: tim bang luat tay tren S1_BTC ky C (USDC), doi chieu pipeline daily = 0 dung ngay do
S = pd.read_parquet(WK + "/s_daily.parquet")["S1_BTC|M1_W15"]
nf = 0
for d in pd.date_range("2024-01-05", "2026-09-30", freq="D"):
    t = int((d + pd.Timedelta(hours=21)).value // 1_000_000); p0 = U.close[t - MS]
    w = U.loc[t: t + 14 * MS]
    if (w.low < p0).any():
        continue
    rec = {"sig": "S1_BTC", "t_in_utc": str(d + pd.Timedelta(hours=21)), "P0": p0, "min_low_15": float(w.low.min()), "fill_hand": False,
           "pipe_daily_M1": float(S.get(d, np.nan)), "agree": S.get(d, np.nan) == 0.0}
    v4.append(rec); print("V4", rec); nf += 1
    if nf == 3:
        break
out["V4"] = v4
out["V4_PASS"] = all(r["agree"] for r in v4)
# ---- V5 S8: imb chi tu nen t (cat du lieu tai t)
m = pd.read_parquet(os.path.expanduser("~/claude_master/1016/screen/m1_BTCUSDT.parquet"))
ts = m.index.asi8 // 1_000_000
rng = np.random.default_rng(7)
cand = np.where(((ts // MS) % 60 == 0) & ((ts // 3_600_000) % 4 == 0))[0]
bad = 0
for i in rng.choice(cand, 200, replace=False):
    cut = m.iloc[: i + 1]                     # du lieu <= t
    v = (2 * cut.tbv.iloc[-1] - cut.vol.iloc[-1]) / cut.vol.iloc[-1]
    v_full = (2 * m.tbv.iloc[i] - m.vol.iloc[i]) / m.vol.iloc[i]
    bad += int(np.sign(v) != np.sign(v_full))
out["V5_S8_mismatch_of_200"] = bad
# ---- V5 Q4-E: imb_dev15 tu du lieu cat tai ts; fwd window chi nen >= ts+1m; exit = close nen ts+12h
E = pd.read_parquet(WK + "/q4_moc_e.parquet")
smp = E.sample(150, random_state=11)
raw = {}
mis = {"imbd": 0, "lo15": 0, "exit": 0}
for _, r in smp.iterrows():
    mth = pd.to_datetime(r.ts, unit="ms").strftime("%Y-%m")
    key = (mth, r.sym)
    if key not in raw:
        nxt = (pd.Timestamp(mth + "-01") + pd.offsets.MonthBegin(1)).strftime("%Y-%m")
        xs = [pd.read_parquet(os.path.expanduser(f"~/vz_e1/raw/kline1m-{mm}.parquet"), columns=["ts", "sym", "close", "low", "quote_volume", "taker_buy_quote"],
                              filters=[("sym", "==", r.sym)]) for mm in (mth, nxt) if os.path.exists(os.path.expanduser(f"~/vz_e1/raw/kline1m-{mm}.parquet"))]
        x = pd.concat(xs); x["ts"] = x.ts.astype(np.int64)
        raw[key] = x.drop_duplicates("ts").sort_values("ts").reset_index(drop=True)
    x = raw[key]
    past = x[x.ts <= r.ts].tail(16)
    if len(past) < 16 or past.ts.iloc[-1] != r.ts or past.ts.iloc[0] < x.ts.iloc[0]:
        continue
    imb = 2 * past.taker_buy_quote / past.quote_volume.replace(0, np.nan) - 1
    imbd = imb.iloc[-1] - imb.iloc[:-1].mean()
    if np.isfinite(r.imbd) and abs(imbd - r.imbd) > 1e-12:
        mis["imbd"] += 1
    fw = x[(x.ts >= r.ts + MS) & (x.ts < r.ts + 16 * MS)]
    if len(fw) and np.isfinite(r.lo15) and abs(fw.low.min() - r.lo15) > 1e-12:
        mis["lo15"] += 1
    ex = x[x.ts == r.ts + 12 * 3_600_000]
    if len(ex) and np.isfinite(r.exit) and abs(ex.close.iloc[0] - r.exit) > 1e-12:
        mis["exit"] += 1
out["V5_Q4E_mismatch_of_150"] = mis
out["V5_PASS"] = bad == 0 and sum(mis.values()) == 0
print(json.dumps({k: v for k, v in out.items() if k != "V4"}))
json.dump(out, open(WK + "/v45.json", "w"), indent=1, default=str)
