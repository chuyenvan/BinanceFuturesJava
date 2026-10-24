"""FEE0 V3: tai lap DOC LAP PnL ngay S7_BTC C_M1 (W=15) - khong import pipeline. Python thuan + zipfile/csv; pandas chi de doc parquet."""
import csv, glob, io, json, os, zipfile
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import pandas as pd

WK = os.path.expanduser("~/claude_master/fee0_wk")
NY = ZoneInfo("America/New_York")
UTC = timezone.utc
MS = 60000

# 1m bars: dict open_ts -> (high, low, close)
m = pd.read_parquet(os.path.expanduser("~/claude_master/1016/screen/m1_BTCUSDT.parquet"))
usdt_ts = [int(t) // 1_000_000 for t in m.index.asi8]
bars = {}
uc = {}
for p in sorted(glob.glob(WK + "/k1m/BTCUSDC/*.zip")):
    with zipfile.ZipFile(p) as z:
        for row in csv.reader(io.TextIOWrapper(z.open(z.namelist()[0]))):
            if not row[0].isdigit():
                continue
            uc[int(row[0])] = (float(row[2]), float(row[3]), float(row[4]))
first_usdc = min(uc)
for t, h, l, c in zip(usdt_ts, m.high.values, m.low.values, m.close.values):
    if t < first_usdc:
        bars[t] = (float(h), float(l), float(c))
bars.update(uc)

# funding: USDT lake truoc first_usdc, USDC Vision tu first_usdc
fund = []
for p in sorted(glob.glob(os.path.expanduser("~/claude_master/1016/carry/fund/funding-*.parquet"))):
    f = pd.read_parquet(p)
    f = f[f.sym == "BTCUSDT"]
    fund += [(int(a), float(b)) for a, b in zip(f.ts, f.rate) if int(a) < first_usdc]
for p in sorted(glob.glob(WK + "/fund/BTCUSDC/*.zip")):
    with zipfile.ZipFile(p) as z:
        r = list(csv.reader(io.TextIOWrapper(z.open(z.namelist()[0]))))
    hdr = r[0]; i_t = hdr.index("calc_time"); i_r = hdr.index("last_funding_rate")
    fund += [(int(x[i_t]), float(x[i_r])) for x in r[1:] if int(x[i_t]) >= first_usdc]
fund = sorted(set(fund))
hs = json.load(open(WK + "/half_spread.json"))["BTCUSDC"]

pnl = {}
d = datetime(2021, 1, 2)
while d <= datetime(2026, 9, 30):
    if d.weekday() == 4:
        mid = datetime(d.year, d.month, d.day, tzinfo=NY).astimezone(UTC)   # 00:00 ET -> UTC, roi cong thoi gian TUYET DOI
        tin = int((mid + timedelta(hours=16)).timestamp() * 1000)
        tout = int((mid + timedelta(hours=72 + 10)).timestamp() * 1000)
        if (tin - MS) in bars and (tout - MS) in bars:
            p0 = bars[tin - MS][2]; p1 = bars[tout - MS][2]
            filled = any(bars[tin + k * MS][1] < p0 for k in range(15) if (tin + k * MS) in bars)
            if filled:
                fr = sum(r for t, r in fund if tin < t <= tout)
                r = (p1 / p0 - 1) - 0.0002 - (0.0004 + hs) - fr
                day = datetime.fromtimestamp(tout / 1000, UTC).strftime("%Y-%m-%d")
                pnl[day] = pnl.get(day, 0.0) + r
    d += timedelta(days=1)

S = pd.read_parquet(WK + "/s_daily.parquet")["S7_BTC|M1_W15"]
mx = 0.0; nd = 0
for day, v in S.items():
    a = pnl.get(day.strftime("%Y-%m-%d"), 0.0)
    mx = max(mx, abs(a - v)); nd += 1
extra = [k for k in pnl if pd.Timestamp(k) not in S.index]
res = {"V3_max_abs_diff": mx, "days": nd, "n_filled_trades_indep": len(pnl), "days_not_in_pipeline": extra, "PASS": mx < 1e-9 and not extra}
print(res)
json.dump(res, open(WK + "/v3.json", "w"), indent=1)
