import urllib.request, urllib.parse, json, os, csv, time, collections, datetime

OUT = r"E:\educa\source\github\20260415\BinanceFuturesJava\_wfotmp\holdout\raw"
INV = r"E:\educa\source\github\20260415\BinanceFuturesJava\_wfotmp\holdout\inventory.csv"
os.makedirs(OUT, exist_ok=True)

SYMS = [
    # ---- chi so co phieu (13) ----
    ("^GSPC", "S&P 500", "equity", "My"),
    ("^NDX", "Nasdaq 100", "equity", "My"),
    ("^DJI", "Dow Jones 30", "equity", "My"),
    ("^RUT", "Russell 2000", "equity", "My"),
    ("^GDAXI", "DAX", "equity", "Duc"),
    ("^FTSE", "FTSE 100", "equity", "Anh"),
    ("^FCHI", "CAC 40", "equity", "Phap"),
    ("^STOXX50E", "Euro Stoxx 50", "equity", "EU"),
    ("^N225", "Nikkei 225", "equity", "Nhat"),
    ("^HSI", "Hang Seng", "equity", "HK"),
    ("^AXJO", "ASX 200", "equity", "Uc"),
    ("^KS11", "KOSPI", "equity", "Han"),
    ("^GSPTSE", "TSX Composite", "equity", "Canada"),
    # ---- hang hoa (13) ----
    ("GC=F", "Vang", "commodity", "COMEX"),
    ("SI=F", "Bac", "commodity", "COMEX"),
    ("PL=F", "Bach kim", "commodity", "NYMEX"),
    ("HG=F", "Dong", "commodity", "COMEX"),
    ("CL=F", "Dau tho WTI", "commodity", "NYMEX"),
    ("BZ=F", "Dau Brent", "commodity", "ICE"),
    ("NG=F", "Khi dot", "commodity", "NYMEX"),
    ("ZC=F", "Ngo", "commodity", "CBOT"),
    ("ZW=F", "Lua mi", "commodity", "CBOT"),
    ("ZS=F", "Dau nanh", "commodity", "CBOT"),
    ("SB=F", "Duong", "commodity", "ICE"),
    ("KC=F", "Ca phe", "commodity", "ICE"),
    ("CT=F", "Bong", "commodity", "ICE"),
    # ---- tien te (8) ----
    ("EURUSD=X", "EUR/USD", "fx", "-"),
    ("JPY=X", "USD/JPY", "fx", "-"),
    ("GBPUSD=X", "GBP/USD", "fx", "-"),
    ("AUDUSD=X", "AUD/USD", "fx", "-"),
    ("CAD=X", "USD/CAD", "fx", "-"),
    ("CHF=X", "USD/CHF", "fx", "-"),
    ("NZDUSD=X", "NZD/USD", "fx", "-"),
    ("SEK=X", "USD/SEK", "fx", "-"),
    # ---- trai phieu / lai suat (6) ----
    ("ZN=F", "HD tuong lai TP My 10y", "bond", "CBOT"),
    ("ZB=F", "HD tuong lai TP My 30y", "bond", "CBOT"),
    ("TLT", "ETF TP My 20y+ (tong LN)", "bond", "NASDAQ"),
    ("IEF", "ETF TP My 7-10y (tong LN)", "bond", "NASDAQ"),
    ("LQD", "ETF TP doanh nghiep", "bond", "NYSE"),
    ("HYG", "ETF TP loi suat cao", "bond", "NYSE"),
]

BASE = ("https://query1.finance.yahoo.com/v8/finance/chart/%s"
        "?period1=-2208988800&period2=9999999999&interval=1d&includeAdjustedClose=true")


def get(sym):
    url = BASE % urllib.parse.quote(sym)
    for i in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            return json.loads(urllib.request.urlopen(req, timeout=45).read())
        except Exception as e:
            time.sleep(3 * (i + 1))
    return None


print("nguon: Yahoo Finance chart API | khung: daily | dung gia DIEU CHINH khi co")
print("truy van %d ma" % len(SYMS))
print()
print("%-11s %-26s %-10s %-8s %7s %-11s %-11s %5s %5s %6s" % (
    "ma", "ten", "lop", "san", "so nen", "tu ngay", "den ngay", "nam", "gap", "|r|max"))
rows = []
for sym, name, cls, ex in SYMS:
    j = get(sym)
    if not j or not j.get("chart", {}).get("result"):
        print("%-11s %-26s %-10s %-8s  LOI / khong co du lieu" % (sym, name, cls, ex))
        continue
    r0 = j["chart"]["result"][0]
    ts = r0.get("timestamp") or []
    ind = r0.get("indicators", {})
    adj = None
    if ind.get("adjclose"):
        adj = ind["adjclose"][0].get("adjclose")
    px = adj if adj else ind["quote"][0].get("close")
    src = "adjclose" if adj else "close"
    pairs = [(t, p) for t, p in zip(ts, px) if p is not None and p > 0]
    if len(pairs) < 500:
        print("%-11s %-26s %-10s %-8s  QUA NGAN (%d nen), bo" % (sym, name, cls, ex, len(pairs)))
        continue
    EPOCH = datetime.datetime(1970, 1, 1)
    dates = [(EPOCH + datetime.timedelta(seconds=int(t))).strftime("%Y-%m-%d")
             for t, _ in pairs]
    vals = [p for _, p in pairs]
    # kiem tra chat luong
    dd = [datetime.date(*map(int, d.split("-"))) for d in dates]
    gaps = max((dd[i + 1] - dd[i]).days for i in range(len(dd) - 1))
    rmax = max(abs(vals[i + 1] / vals[i] - 1) for i in range(len(vals) - 1))
    p = os.path.join(OUT, sym.replace("^", "IDX_").replace("=", "_") + ".csv")
    with open(p, "w", newline="") as f:
        w = csv.writer(f); w.writerow(["date", "close"])
        for d, v in zip(dates, vals):
            w.writerow([d, v])
    yrs = round((dd[-1] - dd[0]).days / 365.25, 1)
    print("%-11s %-26s %-10s %-8s %7d %-11s %-11s %5.1f %5d %5.0f%%  %s" % (
        sym, name, cls, ex, len(vals), dates[0], dates[-1], yrs, gaps, rmax * 100, src))
    rows.append([sym, name, cls, ex, len(vals), dates[0], dates[-1], yrs, gaps,
                 round(rmax * 100, 1), src])
    time.sleep(0.5)

print()
print("TAI DUOC %d / %d ma" % (len(rows), len(SYMS)))
c = collections.Counter(r[2] for r in rows)
print("Theo lop tai san:", dict(c))
tot = sum(r[4] for r in rows)
print("Tong so nen: %d  (~%.0f nam-tai-san giao dich)" % (tot, tot / 252.0))
print("Nam som nhat: %s | tre nhat: %s" % (min(r[5] for r in rows), max(r[6] for r in rows)))
with open(INV, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["symbol", "name", "class", "exchange", "bars", "start", "end",
                "years", "max_gap_days", "max_abs_daily_ret_pct", "price_source"])
    for r in rows:
        w.writerow(r)
print("Inventory ghi ra:", INV)
print("DONE")
