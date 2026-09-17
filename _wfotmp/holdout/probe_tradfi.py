import urllib.request, urllib.parse, os, csv, time, io, collections

OUT = r"E:\educa\source\github\20260415\BinanceFuturesJava\_wfotmp\holdout\raw"
os.makedirs(OUT, exist_ok=True)

SYMS = [
    ("^SPX", "S&P 500 (My)", "equity"),
    ("^NDQ", "Nasdaq 100 (My)", "equity"),
    ("^DJI", "Dow Jones (My)", "equity"),
    ("^RUT", "Russell 2000 (My)", "equity"),
    ("^DAX", "DAX (Duc)", "equity"),
    ("^FTM", "FTSE 100 (Anh)", "equity"),
    ("^CAC", "CAC 40 (Phap)", "equity"),
    ("^NKX", "Nikkei 225 (Nhat)", "equity"),
    ("^HSI", "Hang Seng (HK)", "equity"),
    ("^AORD", "All Ordinaries (Uc)", "equity"),
    ("^SMI", "SMI (Thuy Si)", "equity"),
    ("^BVP", "Bovespa (Brazil)", "equity"),
    ("^KOSPI", "KOSPI (Han)", "equity"),
    ("^TSX", "TSX (Canada)", "equity"),
    ("XAUUSD", "Vang", "commodity"),
    ("XAGUSD", "Bac", "commodity"),
    ("CL.F", "Dau tho WTI", "commodity"),
    ("NG.F", "Khi dot", "commodity"),
    ("HG.F", "Dong", "commodity"),
    ("ZC.F", "Ngo", "commodity"),
    ("ZW.F", "Lua mi", "commodity"),
    ("ZS.F", "Dau nanh", "commodity"),
    ("SB.F", "Duong", "commodity"),
    ("KC.F", "Ca phe", "commodity"),
    ("CT.F", "Bong", "commodity"),
    ("PL.F", "Bach kim", "commodity"),
    ("EURUSD", "EUR/USD", "fx"),
    ("USDJPY", "USD/JPY", "fx"),
    ("GBPUSD", "GBP/USD", "fx"),
    ("AUDUSD", "AUD/USD", "fx"),
    ("USDCAD", "USD/CAD", "fx"),
    ("USDCHF", "USD/CHF", "fx"),
    ("NZDUSD", "NZD/USD", "fx"),
    ("USDSEK", "USD/SEK", "fx"),
    ("TLT.US", "ETF trai phieu My 20y+", "bond"),
    ("IEF.US", "ETF trai phieu My 7-10y", "bond"),
    ("LQD.US", "ETF trai phieu DN My", "bond"),
    ("HYG.US", "ETF trai phieu loi suat cao", "bond"),
]

print("nguon: stooq.com | khung: daily | truy van %d ma" % len(SYMS), flush=True)
print("%-9s %-27s %-10s %7s %-11s %-11s %s" % (
    "ma", "ten", "lop", "so nen", "tu ngay", "den ngay", "ghi chu"), flush=True)

rows = []
for sym, name, cls in SYMS:
    url = "https://stooq.com/q/d/l/?s=%s&i=d" % urllib.parse.quote(sym)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        txt = urllib.request.urlopen(req, timeout=40).read().decode("utf-8", "ignore")
    except Exception as e:
        print("%-9s %-27s %-10s %7s %-11s %-11s LOI %s" % (
            sym, name, cls, "-", "-", "-", str(e)[:40]), flush=True)
        continue
    lines = [l for l in txt.strip().splitlines() if l]
    if len(lines) < 3 or not lines[0].lower().startswith("date"):
        print("%-9s %-27s %-10s %7s %-11s %-11s KHONG CO DU LIEU" % (
            sym, name, cls, "-", "-", "-"), flush=True)
        continue
    rd = list(csv.DictReader(io.StringIO(txt)))
    rd = [r for r in rd if r.get("Close") not in (None, "", "-")]
    if len(rd) < 500:
        print("%-9s %-27s %-10s %7d %-11s %-11s QUA NGAN, bo" % (
            sym, name, cls, len(rd), rd[0]["Date"] if rd else "-",
            rd[-1]["Date"] if rd else "-"), flush=True)
        continue
    p = os.path.join(OUT, sym.replace("^", "IDX_").replace(".", "_") + ".csv")
    with open(p, "w", newline="") as f:
        w = csv.writer(f); w.writerow(["date", "close"])
        for r in rd:
            w.writerow([r["Date"], r["Close"]])
    yrs = int(rd[-1]["Date"][:4]) - int(rd[0]["Date"][:4])
    print("%-9s %-27s %-10s %7d %-11s %-11s ~%d nam" % (
        sym, name, cls, len(rd), rd[0]["Date"], rd[-1]["Date"], yrs), flush=True)
    rows.append((sym, name, cls, len(rd), rd[0]["Date"], rd[-1]["Date"], yrs))
    time.sleep(0.4)

print()
print("TAI DUOC %d / %d ma" % (len(rows), len(SYMS)), flush=True)
print("Theo lop:", dict(collections.Counter(r[2] for r in rows)), flush=True)
tot = sum(r[3] for r in rows)
print("Tong so nen: %d  (~%.0f nam-tai-san)" % (tot, tot / 252.0), flush=True)
with open(os.path.join(OUT, "..", "inventory.csv"), "w", newline="") as f:
    w = csv.writer(f); w.writerow(["symbol", "name", "class", "bars", "start", "end", "years"])
    for r in rows:
        w.writerow(r)
print("DONE", flush=True)
