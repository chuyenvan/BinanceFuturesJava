"""SYMLIFE A1 (v2, theo GIAO DICH): lifecycle PIT moi USDT perp.
first_trade_ts/last_trade_ts = phut dau/cuoi co n_trades>0 (raw 2021-12..2025-12 chinh xac phut; 2026: file Vision tai ve;
truoc 2021-12: bien ngay Vision). status_now: TRADING neu file Vision 2026-10-23 co trade. Gap: ngay 0-trade lien tiep >=3
giua first/last trade (raw window) + su kien SETTLED (doi hop dong / relist) tu Vision. Doc lap."""
import os, json, re, datetime as dt, numpy as np, pandas as pd
WK = os.path.expanduser("~/claude_master/symlife_wk")
OUTR = os.path.expanduser("~/claude_master/vz_e1_wt/docs/result/symlife"); os.makedirs(OUTR, exist_ok=True)
L = json.load(open(WK + "/vision_listing.json"))["daily"]
T0 = pd.read_parquet(WK + "/lifecycle.parquet")   # v1 (file-based) - giu cot file
A = pd.read_parquet(WK + "/vision_act.parquet")
LT = json.load(open(WK + "/lt2026.json"))
RT = pd.read_parquet(WK + "/raw_trade_ts.parquet").set_index("sym")
RD = pd.read_parquet(WK + "/raw_daycov.parquet"); RD["sym"] = RD.sym.where(RD.sym.str.endswith("USDT"), RD.sym + "USDT")
DAY = 86400000
def dms(s): return int(dt.datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=dt.timezone.utc).timestamp() * 1000)
RAW_END_DAY = dms("2025-12-31") // DAY
Aix = A.set_index(["sym", "day"])
btc_raw_days = set(RD[RD.sym == "BTCUSDT"].day)
settled = {}
for k, v in L.items():
    if "SETTLED" in k:
        base = re.sub(r"_?SETTLED.*$", "", k)
        settled.setdefault(base, []).append(f"{k}:{v[0]}..{v[-1]}")
rows = []
for _, r in T0[T0.usdt_perp].iterrows():
    s = r.symbol; ds = L.get(s, [])
    o = dict(symbol=s, ascii=r.ascii, file_first_day=r.first_day, file_last_day=r.last_day, n_files=r.n_days)
    # first trade
    if s in RT.index and r.first_day >= "2021-12-02":
        o["first_trade_ts"] = int(RT.loc[s, "raw_ft"]); o["first_src"] = "raw"
    elif (s, r.first_day) in Aix.index and pd.notna(Aix.loc[(s, r.first_day), "ft"]):
        o["first_trade_ts"] = int(Aix.loc[(s, r.first_day), "ft"]); o["first_src"] = "vision_file"
    else:
        o["first_trade_ts"] = dms(r.first_day); o["first_src"] = "vision_day"
    # status/last trade
    rec = Aix.loc[(s, "2026-10-23")] if (s, "2026-10-23") in Aix.index else None
    if rec is not None and rec.n_tr > 0:
        o["status_now"] = "TRADING"; o["last_trade_ts"] = None; o["last_src"] = "alive@2026-10-23"
        o["n_tr_1023"] = int(rec.n_tr)
    else:
        o["status_now"] = "STOPPED"
        lt = LT.get(s)
        if lt:
            o["last_trade_ts"] = int(Aix.loc[(s, lt), "lt"]); o["last_src"] = "vision_bsearch"
        elif s in RT.index and r.first_day <= "2025-12-31":
            o["last_trade_ts"] = int(RT.loc[s, "raw_lt"]); o["last_src"] = "raw"
        else:
            o["last_trade_ts"] = dms(r.last_day) + DAY - 60000; o["last_src"] = "vision_day(chua kiem trade)"
        o["n_tr_1023"] = int(rec.n_tr) if rec is not None else None
    o["zombie_files_after_last"] = (o["status_now"] == "STOPPED") and (r.last_day > dt.datetime.utcfromtimestamp(o["last_trade_ts"] / 1000).strftime("%Y-%m-%d"))
    # gap giao dich trong raw
    q = RD[(RD.sym == s) & (RD.n_trade_pos > 0)].day
    gaps = []
    if len(q):
        td = set(q); a, b = q.min(), q.max(); run = []
        for d in range(a, b + 1):
            if d not in td and d in btc_raw_days:
                run.append(d)
            else:
                if len(run) >= 3: gaps.append((run[0], run[-1]))
                run = []
    o["trade_gaps_ge3_raw"] = ";".join(f"{dt.datetime.utcfromtimestamp(x*86400).date()}..{dt.datetime.utcfromtimestamp(y*86400).date()}({y-x+1})" for x, y in gaps)
    o["settled_events"] = ";".join(settled.get(s, []))
    rows.append(o)
T = pd.DataFrame(rows)
T["first_trade_ts"] = T.first_trade_ts.astype("Int64"); T["last_trade_ts"] = T.last_trade_ts.astype("Int64")
T["first_utc"] = pd.to_datetime(T.first_trade_ts, unit="ms"); T["last_utc"] = pd.to_datetime(T.last_trade_ts, unit="ms")
T.to_parquet(WK + "/lifecycle.parquet", index=False)   # ghi de v1 bang v2 (v1 file-based chi la buoc trung gian)
T.drop(columns=["first_trade_ts", "last_trade_ts"]).to_csv(OUTR + "/lifecycle_usdt.csv", index=False)
print("USDT perp", len(T), T.status_now.value_counts().to_dict(), "non-ascii", int((~T.ascii).sum()))
print("first_src", T.first_src.value_counts().to_dict(), "last_src", T.last_src.value_counts().to_dict())
print("zombie files after last trade:", int(T.zombie_files_after_last.sum()))
print("gaps:"); print(T[T.trade_gaps_ge3_raw != ""][["symbol", "first_utc", "last_utc", "status_now", "trade_gaps_ge3_raw"]].to_string())
print("settled:"); print(T[T.settled_events != ""][["symbol", "first_utc", "last_utc", "status_now", "settled_events"]].to_string())
# kiem doc lap: 20 symbol STOPPED ngau nhien -> file ngay last_trade co trade, ngay sau (neu co file) khong trade
print("STOPPED by year:", T[T.status_now == "STOPPED"].last_utc.dt.year.value_counts().sort_index().to_dict())
print("2026 stopped:"); print(T[(T.status_now == "STOPPED") & (T.last_utc >= "2026-01-01")][["symbol", "last_utc", "file_last_day", "last_src"]].sort_values("last_utc").to_string())
