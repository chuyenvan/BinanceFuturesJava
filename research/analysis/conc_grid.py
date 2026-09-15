"""Do TAP TRUNG VON theo cum coin: bao nhieu %% equity don vao 1 coin khi nhoi luoi DCA.

Bac grid suy tu printDone.csv: row dau = bac 0; moi row DCA_LEVEL1 ke tiep = bac 1,2,3...
(leg-signal = row leg>0 co level=PREDICT_SYMBOL_TRADE, KHONG an bac ladder).
Usage: python3 conc_grid.py TAG [TAG ...]
"""
import os, re, sys
import pandas as pd
B = "/home/ubuntu/java/devrun"
RX = re.compile(r"Update (\d{8}) \d\d:\d\d => b:(-?[\d.]+).*?unP:\s*(-?[\d.]+)")

def eqseries(tag):
    rows = []
    with open(f"{B}/{tag}/logs/sim.out", "rb") as f:
        for ln in f:
            m = RX.search(ln.decode("utf8", "ignore"))
            if m: rows.append((m.group(1), float(m.group(2)) + float(m.group(3))))
    return pd.DataFrame(rows, columns=["d", "eq"]).drop_duplicates("d", keep="last").set_index("d")["eq"]

def analyse(tag):
    p = f"{B}/{tag}/storage/printDone.csv"
    if not os.path.exists(p): return None, None
    d = pd.read_csv(p, on_bad_lines="skip"); d.columns = [c.strip() for c in d.columns]
    d = d[d["sym"].notna()].copy()
    d["start"] = d["start"].astype(str); d["end"] = d["end"].astype(str)
    d = d.sort_values(["sym", "end", "start"])
    g = d.groupby(["sym", "end"]); d["leg"] = g.cumcount()
    d["isdca"] = (d["level"] == "DCA_LEVEL1") & (d["leg"] > 0)
    d["rung"] = d.groupby(["sym", "end"])["isdca"].cumsum().astype(int)
    d.loc[d["leg"] == 0, "rung"] = 0
    eq = eqseries(tag); d["day"] = d["start"].str.slice(0, 8); d["eq"] = d["day"].map(eq)
    d["pct"] = d["margin"] / d["eq"] * 100
    cm = d.groupby(["sym", "end"]).agg(tot=("margin", "sum"), n=("margin", "size"),
        maxrung=("rung", "max"), pnl=("pnl", "sum"), eq0=("eq", "first"), d0=("day", "first")).reset_index()
    cm["tot_pct"] = cm["tot"] / cm["eq0"] * 100
    return d, cm

if __name__ == "__main__":
    summ = []
    for tag in sys.argv[1:]:
        d, cm = analyse(tag)
        if d is None: print(f"{tag}: MISSING"); continue
        summ.append(dict(tag=tag, clusters=len(cm),
            r1=int((cm.maxrung >= 1).sum()), r2=int((cm.maxrung >= 2).sum()), r3=int((cm.maxrung >= 3).sum()),
            max_cum_pct=round(cm.tot_pct.max(), 2), p99_cum=round(cm.tot_pct.quantile(.99), 2),
            max_leg0_pct=round(d[d.leg == 0].pct.max(), 3),
            pnl_r3=round(cm[cm.maxrung >= 3].pnl.sum(), 0) if (cm.maxrung >= 3).any() else 0.0))
        print(f"\n### {tag}: margin/equity (%) theo BAC GRID")
        print(d.groupby("rung")["pct"].agg(["count", "mean", "median", "max"]).round(3).to_string())
        deep = cm[cm.maxrung >= 2]
        if len(deep):
            print(f"  cum cham bac>=2 ({len(deep)}), top5 theo tot_pct:")
            print(deep.nlargest(5, "tot_pct")[["sym", "d0", "n", "maxrung", "tot", "eq0", "tot_pct", "pnl"]].round(2).to_string(index=False))
    print("\n===== TONG HOP =====")
    print(pd.DataFrame(summ).to_string(index=False))
