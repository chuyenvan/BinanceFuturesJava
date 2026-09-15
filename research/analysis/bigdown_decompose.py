"""AUDIT: tach dong gop BIG_DOWN (khong qua gate) vs entry thuong (qua gate) o 3 config scale."""
import sys
import numpy as np
import pandas as pd
sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
import c3_rates as C

TAGS = [("T100", "X1_C3_FULL_2021"), ("T130", "X1_GS_T130_2021"), ("T170", "X1_GS_T170_2021")]
CAP0 = 35000.0

def prep(tag):
    d = C.trades(tag)
    return d.assign(st=pd.to_datetime(d["start"], format="%Y%m%d %H:%M", errors="coerce"),
                    en=pd.to_datetime(d["end"],   format="%Y%m%d %H:%M", errors="coerce"))

def curve(d):
    """equity tong hop = CAP0 + cumsum(pnl) theo NGAY DONG lenh (xap xi: bo qua compounding/margin path)."""
    s = d.groupby(d.en.dt.normalize()).pnl.sum().sort_index().cumsum() + CAP0
    idx = pd.date_range(s.index.min(), s.index.max(), freq="D")
    return s.reindex(idx).ffill()

def risk(s):
    dd = (s / s.cummax() - 1) * 100
    uw = s < s.cummax()
    out = {"maxDD": dd.min(), "UW": int(uw.groupby((~uw).cumsum()).sum().max()) if len(uw) else 0,
           "end": s.iloc[-1], "yr": {}, "uw_yr": {}, "dd_yr": {}, "qmin": None}
    qs = []
    for y, sy in s.groupby(s.index.year):
        u = sy < sy.cummax()
        out["yr"][y] = (sy.iloc[-1]/sy.iloc[0]-1)*100
        out["uw_yr"][y] = int(u.groupby((~u).cumsum()).sum().max()) if len(u) else 0
        out["dd_yr"][y] = ((sy/sy.cummax()-1)*100).min()
        qe = sy.resample("QE").last()
        q0 = pd.concat([pd.Series([sy.iloc[0]], index=[sy.index[0]]), qe]).iloc[:-1]
        qs += list((qe.values/q0.values-1)*100)
    out["qmin"] = min(qs) if qs else float("nan")
    return out

print("=== 1+2. PHAN RA THEO NGUON LEG (pnl USD, theo nam dong lenh) ===")
print("%-6s %-22s %6s %10s %9s | %s" % ("cfg","nhom","n","pnl","pnl/leg","pnl theo nam 2021..2025"))
data = {}
for nm, tag in TAGS:
    d = prep(tag); data[nm] = d
    for grp in ("PREDICT_SYMBOL_TRADE", "BIG_DOWN", "DCA_LEVEL1"):
        g = d[d.level == grp]
        yr = g.groupby(g.en.dt.year).pnl.sum()
        print("%-6s %-22s %6d %10.0f %9.1f | %s" % (nm, grp, len(g), g.pnl.sum(),
              g.pnl.sum()/len(g) if len(g) else 0,
              "  ".join("%d:%+8.0f" % (y, yr.get(y, 0)) for y in range(2021, 2026))))
    tot = d.pnl.sum()
    ent = d[d.level == "PREDICT_SYMBOL_TRADE"].pnl.sum()
    bdn = d[d.level != "PREDICT_SYMBOL_TRADE"].pnl.sum()
    print("%-6s %-22s %6d %10.0f %9s | ENTRY %.1f%% / KHONG-QUA-GATE-SCALE %.1f%%" % (
        nm, "TONG", len(d), tot, "", 100*ent/tot, 100*bdn/tot))
    print()

print("=== 3. SO LAN BIG_DOWN KICH HOAT + CONCURRENCY ===")
print("%-6s %8s %10s %10s %10s %9s %9s" % ("cfg","n_leg_BD","n_tick_BD","n_ngay_BD","n_coin_BD","conc_tb","n_cum"))
for nm, _ in TAGS:
    d = data[nm]; bd = d[d.level == "BIG_DOWN"]
    cl = d.groupby(["sym","end"]).agg(s0=("st","min")).reset_index()
    cl["e0"] = pd.to_datetime(cl["end"], format="%Y%m%d %H:%M", errors="coerce")
    cl = cl.dropna(subset=["e0"])
    ev = pd.concat([pd.Series(1, index=cl.s0), pd.Series(-1, index=cl.e0)]).sort_index()
    occ = ev.cumsum().resample("1h").last().ffill().fillna(0)
    print("%-6s %8d %10d %10d %10d %9.2f %9d" % (nm, len(bd), bd.st.nunique(),
          bd.st.dt.normalize().nunique(), bd.sym.nunique(), occ.mean(), len(cl)))
print()

print("=== 4. DUNG LAI EQUITY CHI TU ENTRY THUONG (loai BIG_DOWN + DCA_LEVEL1) ===")
print("   [xap xi: CAP0=35000 + cumsum(pnl) theo ngay dong lenh; BO QUA compounding va margin path]")
print("%-6s %-12s %9s %8s %7s %8s | %s" % ("cfg","tap","equity","maxDD%","UW","qmin%","ret theo nam 2021..2025"))
res = {}
for nm, _ in TAGS:
    d = data[nm]
    for lbl, sub in (("ALL(kiem tra)", d), ("ENTRY-ONLY", d[d.level == "PREDICT_SYMBOL_TRADE"])):
        r = risk(curve(sub)); res[(nm, lbl)] = r
        print("%-6s %-12s %9.0f %8.2f %7d %8.2f | %s" % (nm, lbl, r["end"], r["maxDD"], r["UW"], r["qmin"],
              "  ".join("%d:%+6.1f" % (y, r["yr"].get(y, float('nan'))) for y in range(2021, 2026))))
    print()

print("=== 4b. HARD-CONSTRAINT tren ENTRY-ONLY (maxDD<=15, UW<=120, nam>=0, quy>=-5) ===")
print("%-6s %s" % ("cfg", "  ".join("%d: DD/UW/ret" % y for y in range(2021, 2026))))
for nm, _ in TAGS:
    r = res[(nm, "ENTRY-ONLY")]
    cells = []; ok = True
    for y in range(2021, 2026):
        dd, uw, ry = r["dd_yr"].get(y), r["uw_yr"].get(y), r["yr"].get(y)
        bad = (dd < -15) or (uw > 120) or (ry < 0)
        ok &= not bad
        cells.append("%d:%6.2f/%3d/%+6.1f%s" % (y, dd, uw, ry, "*" if bad else " "))
    ok &= r["qmin"] >= -5
    print("%-6s %s  qmin=%.2f  => %s" % (nm, " ".join(cells), r["qmin"], "PASS" if ok else "**FAIL**"))
