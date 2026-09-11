"""Ra 2,266 lenh X1_C3_FULL (canonical, PARITY_R): co pattern collapse nhu shadow live 07-11/09 khong?"""
import logging, sys, numpy as np, pandas as pd
logging.basicConfig(level=logging.INFO, format="%(message)s"); L = logging.getLogger("dc")
F = "/home/ubuntu/java/devrun/X1_C3_FULL_PARITY_R/storage/printDone.csv"
d = pd.read_csv(F, usecols=lambda c: c and not c.startswith("Unnamed"))
d["ts"] = pd.to_datetime(d.start, format="%Y%m%d %H:%M"); d["te"] = pd.to_datetime(d.end, format="%Y%m%d %H:%M")
d["yr"] = d.ts.dt.year; d["q"] = d.ts.dt.to_period("Q").astype(str); d["hold"] = (d.te - d.ts).dt.total_seconds()/3600
d["sl"] = d.status.eq("STOP_LOSS_DONE"); d["ret"] = d.profit
L.info("n=%d  status=%s  level=%s", len(d), d.status.value_counts().to_dict(), d.level.value_counts().to_dict())

def blk(g):
    w = g.ret > 0
    return pd.Series({"n": len(g), "win%": 100*w.mean(), "SL%": 100*g.sl.mean(),
        "meanRet_win": g.ret[w].mean(), "meanRet_loss": g.ret[~w].mean(), "medRet": g.ret.median(),
        "p5": g.ret.quantile(.05), "min": g.ret.min(), "n<-20%": (g.ret < -20).sum(), "n<-40%": (g.ret < -40).sum(),
        "hold_med": g.hold.median(), "hold>=96h%": 100*(g.hold >= 96).mean(), "hold>=168h%": 100*(g.hold >= 167).mean(),
        "pnl_SM": g.pnl[~g.sl].sum(), "pnl_SL": g.pnl[g.sl].sum(), "pnl": g.pnl.sum()})
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 30)
L.info("\n== THEO NAM (all level) ==\n%s", d.groupby("yr").apply(blk).round(2).to_string())
L.info("\n== 2025 THEO QUY ==\n%s", d[d.yr == 2025].groupby("q").apply(blk).round(2).to_string())
L.info("\n== 2025 THEO QUY, chi PREDICT_SYMBOL_TRADE ==\n%s", d[(d.yr == 2025) & (d.level == "PREDICT_SYMBOL_TRADE")].groupby("q").apply(blk).round(2).to_string())

# lenh song qua 96h (tuong duong 'con mo sau 4 ngay' o live): ket cuc the nao
s = d[d.hold >= 96]
L.info("\n== LENH SONG >=96h: n=%d (%.1f%% tong), SL%%=%.1f, meanRet=%.2f, medRet=%.2f, pnl=%.0f ==",
       len(s), 100*len(s)/len(d), 100*s.sl.mean(), s.ret.mean(), s.ret.median(), s.pnl.sum())
L.info("%s", s.groupby("yr").apply(lambda g: pd.Series({"n": len(g), "SL%": 100*g.sl.mean(), "meanRet": g.ret.mean(), "n<-20%": (g.ret < -20).sum(), "pnl": g.pnl.sum()})).round(2).to_string())

# re-entry chain: cung sym, vao lai trong <=24h sau khi lenh truoc DONG (hoac chong lan)
d = d.sort_values(["sym", "ts"]).reset_index(drop=True)
d["prev_end"] = d.groupby("sym").te.shift(1); d["prev_ret"] = d.groupby("sym").ret.shift(1)
gap = (d.ts - d.prev_end).dt.total_seconds()/3600
d["reentry"] = gap.notna() & (gap <= 24)
d["chain"] = (~d.reentry).cumsum()
cl = d.groupby("chain").agg(sym=("sym", "first"), n=("sym", "size"), yr=("yr", "first"), last_ret=("ret", "last"), last_sl=("sl", "last"), pnl=("pnl", "sum"), first=("ts", "first"))
L.info("\n== RE-ENTRY: %d/%d lenh (%.1f%%) la vao lai cung coin <=24h sau lenh truoc; theo nam:\n%s", d.reentry.sum(), len(d), 100*d.reentry.mean(),
       d.groupby("yr").apply(lambda g: pd.Series({"reentry%": 100*g.reentry.mean(), "ret_fresh": g.ret[~g.reentry].mean(), "ret_reentry": g.ret[g.reentry].mean(), "SL%_fresh": 100*g.sl[~g.reentry].mean(), "SL%_reentry": 100*g.sl[g.reentry].mean()})).round(2).to_string())
L.info("\n== CHAIN dai >=3: %d chain; lenh CUOI chain ket thuc SL (bag) = %.1f%%, meanRet lenh cuoi=%.2f; pnl chain tong=%.0f ==",
       (cl.n >= 3).sum(), 100*cl[cl.n >= 3].last_sl.mean(), cl[cl.n >= 3].last_ret.mean(), cl[cl.n >= 3].pnl.sum())
L.info("phan phoi do dai chain: %s", cl.n.value_counts().sort_index().to_dict())
L.info("top chain dai nhat:\n%s", cl.sort_values("n", ascending=False).head(12).to_string())
L.info("\n== so sanh: last_ret cua chain>=3 vs lenh don (chain=1): %.2f vs %.2f; SL%%: %.1f vs %.1f",
       cl[cl.n >= 3].last_ret.mean(), cl[cl.n == 1].last_ret.mean(), 100*cl[cl.n >= 3].last_sl.mean(), 100*cl[cl.n == 1].last_sl.mean())

# book theo ngay: so lenh mo, va % lenh dang mo se ket thuc SL (eventual), mean eventual ret
days = pd.date_range(d.ts.min().normalize(), d.te.max().normalize(), freq="D")
rows = []
for D in days:
    o = d[(d.ts <= D) & (d.te > D)]
    if len(o): rows.append({"day": D, "open": len(o), "evSL%": 100*o.sl.mean(), "evRet": o.ret.mean(), "age_med": (D - o.ts).dt.total_seconds().median()/3600})
bk = pd.DataFrame(rows).set_index("day")
L.info("\n== BOOK THEO NGAY: open (med/p90/max) va eventual SL%% cua lenh dang mo, theo nam ==\n%s",
       bk.groupby(bk.index.year).agg(open_med=("open", "median"), open_p90=("open", lambda x: x.quantile(.9)), open_max=("open", "max"), evSL_med=("evSL%", "median"), evSL_p90=("evSL%", lambda x: x.quantile(.9)), evRet_med=("evRet", "median"), evRet_min=("evRet", "min")).round(1).to_string())
L.info("\n== 20 ngay book te nhat (evSL%% cao, >=8 lenh mo) ==\n%s", bk[bk.open >= 8].sort_values("evSL%", ascending=False).head(20).round(1).to_string())
L.info("\n== ngay co >=4 lenh dong SL (collapse day) ==\n%s", d[d.sl].groupby(d.te.dt.normalize()).agg(nSL=("sl", "size"), pnl=("pnl", "sum"), syms=("sym", lambda x: ",".join(x))).query("nSL>=4").to_string())
L.info("\n== concentration: top sym theo nam ==")
for y, g in d.groupby("yr"):
    vc = g.sym.value_counts().head(6); L.info("%s: %s | top6 share=%.1f%%", y, vc.to_dict(), 100*vc.sum()/len(g))
