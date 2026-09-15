"""Bang THEO QUY cho GD92 (rerun tren wfo_ds_x1_2021) vs T170. KHONG chay sim moi.

Quy uoc (ghi ro vi KHAC bang theo NAM da bao cao truoc):
  - leg duoc gan vao quy theo NGAY DONG (cot `end`), khong phai ngay mo  -> "leg dong trong quy"
  - ret/maxDD/uw tinh tren equity that (b+unP) trong sim.out
  - uw_days_in_quarter = so ngay trong quy ma equity < dinh chay cua TOAN CHUOI
    (khong phai dinh trong quy) -> nho vay dot UW dai xuyen bien gioi hien ra tung quy
  - maxDD_pct = drawdown sau nhat TRONG quy, so voi dinh chay trong chinh quy do
"""
import re, sys
import numpy as np, pandas as pd

B = "/home/ubuntu/java/devrun"
RX = re.compile(r"Update (\d{8}) \d\d:\d\d => b:(-?[\d.]+).*?unP:\s*(-?[\d.]+)")
RUNS = [("GD92", "GD_GD92_2021"), ("T170", "X1_GS_T170_2021")]

def equity(tag):
    rows = []
    with open(f"{B}/{tag}/logs/sim.out", "rb") as f:
        for ln in f:
            m = RX.search(ln.decode("utf8", "ignore"))
            if m: rows.append((m.group(1), float(m.group(2)) + float(m.group(3))))
    e = pd.DataFrame(rows, columns=["d", "eq"]).drop_duplicates("d", keep="last")
    e["d"] = pd.to_datetime(e.d, format="%Y%m%d")
    return e.set_index("d")["eq"]

def trades(tag):
    d = pd.read_csv(f"{B}/{tag}/storage/printDone.csv", on_bad_lines="skip")
    d.columns = [c.strip() for c in d.columns]
    for c in ("profit", "pnl", "margin"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d = d.dropna(subset=["profit"])
    d["tend"] = pd.to_datetime(d["end"].astype(str), format="%Y%m%d %H:%M", errors="coerce")
    return d.dropna(subset=["tend"])

def spells(uw, idx):
    """Tra ve list (start, end, ndays) cac dot underwater lien tuc."""
    out, grp = [], (~uw).cumsum()
    for _, g in uw.groupby(grp):
        g = g[g]
        if len(g): out.append((g.index[0], g.index[-1], int(len(g))))
    return out

rows, spell_info = [], {}
for name, tag in RUNS:
    s, d = equity(tag), trades(tag)
    gmax = s.cummax()
    uw = s < gmax
    sp = [x for x in spells(uw, s.index) if x[2] >= 1]
    spell_info[name] = sorted(sp, key=lambda x: -x[2])
    # gan moi ngay vao dot UW nao (chi danh dau dot >= 90 ngay)
    day2spell = {}
    for i, (a, b, n) in enumerate(sorted(sp, key=lambda x: x[0])):
        if n >= 90:
            for dt in pd.date_range(a, b):
                day2spell[dt] = (a, b, n)
    for q, seq in s.groupby(s.index.to_period("Q")):
        sub = d[d.tend.dt.to_period("Q") == q]
        ddq = (seq / seq.cummax() - 1) * 100
        uwq = uw.reindex(seq.index)
        tags_ = {day2spell[dt] for dt in seq.index if dt in day2spell}
        if tags_:
            a, b, n = sorted(tags_, key=lambda x: -x[2])[0]
            note = f"thuoc dot UW dai {n}d ({a.date()}->{b.date()})"
        else:
            note = ""
        rows.append(dict(config=name, year=q.year, quarter=f"Q{q.quarter}",
            n=len(sub),
            win_pct=round(100.0 * (sub.profit > 0).mean(), 2) if len(sub) else np.nan,
            tsloss_pct=round(100.0 * (sub.status == "STOP_LOSS_DONE").mean(), 2) if len(sub) else np.nan,
            meanP_pct=round(float(sub.profit.mean()), 3) if len(sub) else np.nan,
            pnl_usd=round(float(sub.pnl.sum()), 0) if len(sub) else 0.0,
            ret_pct=round((seq.iloc[-1] / seq.iloc[0] - 1) * 100, 2),
            maxDD_pct=round(float(ddq.min()), 2),
            uw_days_in_quarter=int(uwq.sum()),
            note=note))

out = pd.DataFrame(rows)
p = "/home/ubuntu/src/BinanceFuturesJava/research/analysis/gd92_t170_quarterly.csv"
out.to_csv(p, index=False)
print("WROTE", p, len(out), "dong")
print()
for k, v in spell_info.items():
    print(f"=== {k}: cac dot UW dai nhat ===")
    for a, b, n in v[:5]:
        print(f"    {n:4d} ngay  {a.date()} -> {b.date()}")
print()
print(out.to_string(index=False))
