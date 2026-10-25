"""SYMLIFE A1: bang lifecycle PIT tu Vision listing (+ raw kline 2021-12..2025-12 do chinh xac phut).
Doc lap. ts int64 ms UTC. Output: symlife_wk/lifecycle.parquet + repo docs/result/symlife/lifecycle_usdt.csv"""
import os, json, re, datetime as dt, numpy as np, pandas as pd
WK = os.path.expanduser("~/claude_master/symlife_wk")
OUTR = os.path.expanduser("~/claude_master/vz_e1_wt/docs/result/symlife"); os.makedirs(OUTR, exist_ok=True)
L = json.load(open(WK + "/vision_listing.json"))
D, M = L["daily"], L["monthly"]
DAY = 86400000


def dms(s):
    return int(dt.datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=dt.timezone.utc).timestamp() * 1000)


btc = set(D["BTCUSDT"])
# ngay toan cuc co du lieu (>= 50% symbol song co file) -> loai ngay Vision thieu toan cuc khoi "gap"
cnt = {}
for s, ds in D.items():
    for d in ds:
        cnt[d] = cnt.get(d, 0) + 1
last_global = max(btc)
print("vision listed_at", L["listed_at_utc"], "BTC last", last_global, "n daily syms", len(D))
rows = []
for s in sorted(set(D) | set(M)):
    ds = D.get(s, []); ms = M.get(s, [])
    r = dict(symbol=s, usdt_perp=bool(re.fullmatch(r"[^_]+USDT", s)) and not s.endswith("SETTLED"),
             ascii=bool(re.fullmatch(r"[A-Z0-9]+", s)), n_days=len(ds),
             first_day=ds[0] if ds else None, last_day=ds[-1] if ds else None,
             first_month=ms[0] if ms else None, last_month=ms[-1] if ms else None)
    if ds:
        a, b = dms(ds[0]), dms(ds[-1])
        have = set(ds)
        allday = [(dt.datetime.utcfromtimestamp((a + i * DAY) / 1000)).strftime("%Y-%m-%d") for i in range((b - a) // DAY + 1)]
        miss = [d for d in allday if d not in have and d in btc]   # thieu rieng symbol (BTC co)
        # gom run lien tiep
        runs, cur = [], []
        for d in miss:
            if cur and dms(d) - dms(cur[-1]) == DAY:
                cur.append(d)
            else:
                if cur: runs.append(cur)
                cur = [d]
        if cur: runs.append(cur)
        big = [x for x in runs if len(x) >= 3]
        r.update(n_miss_days=len(miss), max_gap_days=max((len(x) for x in runs), default=0), n_gaps_ge3=len(big),
                 gaps_ge3=";".join(f"{x[0]}..{x[-1]}({len(x)})" for x in big)[:500])
    # first theo monthly (co the som hon daily)
    if ms and ds and ms[0] < ds[0][:7]:
        r["monthly_earlier"] = True
    rows.append(r)
T = pd.DataFrame(rows)
T["alive_now"] = T.last_day == last_global
# raw do chinh xac phut (chi USDT, 2021-12..2025-12)
R = pd.read_parquet(WK + "/raw_daycov.parquet")
R["sym"] = R.sym.where(R.sym.str.endswith("USDT"), R.sym + "USDT")
Rt = R[R.n_trade_pos > 0]
agg = R.groupby("sym").agg(raw_first_ts=("first_ts", "min"), raw_last_ts=("last_ts", "max"), raw_n_days=("day", "size"))
agg2 = Rt.groupby("sym").agg(raw_first_trade_day=("day", "min"), raw_last_trade_day=("day", "max"))
T = T.merge(agg, left_on="symbol", right_index=True, how="left").merge(agg2, left_on="symbol", right_index=True, how="left")
RAW_END = dms("2025-12-31") + DAY - 60000
RAW_BEG = dms("2021-12-01")
# first_ts/last_ts PIT: phut neu raw phu bien, nguoc lai bien ngay Vision
def pit(row):
    f = dms(row.first_day) if isinstance(row.first_day, str) else None
    l = dms(row.last_day) + DAY - 60000 if isinstance(row.last_day, str) else None
    if isinstance(row.first_month, str) and (f is None or row.first_month < row.first_day[:7]):
        f = dms(row.first_month + "-01")
    if pd.notna(row.raw_first_ts) and row.raw_first_ts > RAW_BEG + DAY:
        f = int(row.raw_first_ts)
    if pd.notna(row.raw_last_ts) and row.raw_last_ts < RAW_END - DAY and l is not None and l <= RAW_END:
        l = int(row.raw_last_ts)
    return pd.Series(dict(first_ts=f, last_ts=l))
T[["first_ts", "last_ts"]] = T.apply(pit, axis=1)
T["first_ts"] = T.first_ts.astype("Int64"); T["last_ts"] = T.last_ts.astype("Int64")
# kiem tra cheo raw vs vision (ngay)
u = T[T.usdt_perp & T.raw_last_ts.notna()].copy()
u["raw_last_day"] = pd.to_datetime(u.raw_last_ts, unit="ms").dt.strftime("%Y-%m-%d")
u["raw_first_day"] = pd.to_datetime(u.raw_first_ts, unit="ms").dt.strftime("%Y-%m-%d")
inr = u[(u.last_day <= "2025-12-31")]
d_last = (pd.to_datetime(inr.raw_last_day) - pd.to_datetime(inr.last_day)).dt.days
print("V-cross last_day raw-vision (delisted <=2025-12):", d_last.value_counts().sort_index().to_dict())
inf = u[(u.first_day >= "2021-12-02")]
d_first = (pd.to_datetime(inf.raw_first_day) - pd.to_datetime(inf.first_day)).dt.days
print("V-cross first_day raw-vision (listed >=2021-12-02):", d_first.value_counts().sort_index().to_dict())
bad = inr[d_last.abs() > 1][["symbol", "first_day", "last_day", "raw_first_day", "raw_last_day"]]
print("lech last >1 ngay:", len(bad)); print(bad.head(30).to_string())
T.to_parquet(WK + "/lifecycle.parquet", index=False)
U = T[T.usdt_perp].copy()
U["first_utc"] = pd.to_datetime(U.first_ts, unit="ms"); U["last_utc"] = pd.to_datetime(U.last_ts, unit="ms")
cols = ["symbol", "ascii", "first_day", "last_day", "first_utc", "last_utc", "alive_now", "n_days", "n_miss_days", "max_gap_days", "n_gaps_ge3", "gaps_ge3", "first_month", "last_month"]
U[cols].to_csv(OUTR + "/lifecycle_usdt.csv", index=False)
print("USDT perp:", len(U), "alive_now:", int(U.alive_now.sum()), "non-ascii:", int((~U.ascii).sum()), "gap>=3:", int((U.n_gaps_ge3 > 0).sum()))
print(U[U.n_gaps_ge3 > 0][["symbol", "first_day", "last_day", "gaps_ge3"]].to_string())
print("non-USDT/other:", T[~T.usdt_perp].symbol.str.replace(r"[0-9_]+$", "", regex=True).str[-8:].value_counts().head(10).to_dict())
