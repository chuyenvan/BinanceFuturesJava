"""Tong hop MOI config da test trong session -> master_table_all_configs.csv.
KHONG chay sim moi. Doc printDone.csv + sim.out da co."""
import sys
import pandas as pd
sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
import c3_rates as C

DS21 = "wfo_ds_x1_2021(2021-07..2025-12)"
DSX1 = "wfo_ds_x1(2022-01..2025-12)"
CFG = [
 ("T100",            "X1_C3_FULL_2021", DS21, "baseline goc scale=1.00"),
 ("T130",            "X1_GS_T130_2021", DS21, "baseline goc scale=1.30"),
 ("T170",            "X1_GS_T170_2021", DS21, "baseline goc scale=1.70 (INCUMBENT)"),
 ("T100_NOBD",       "NB_T100_NOBD",    DS21, "NOBD: tat BIG_DOWN+DCA_LEVEL1"),
 ("T130_NOBD",       "NB_T130_NOBD",    DS21, "NOBD"),
 ("T170_NOBD",       "NB_T170_NOBD",    DS21, "NOBD"),
 ("GS100",           "DS_GS100",        DS21, "V3 noi gate 1.00 + margin50% + DCA8"),
 ("GS120",           "DS_GS120",        DS21, "V3 noi gate 1.20 + margin50% + DCA8"),
 ("GS140",           "DS_GS140",        DS21, "V3 noi gate 1.40 + margin50% + DCA8"),
 ("GS085",           "DS_GS085",        DS21, "V4-A gate 0.85"),
 ("GS070",           "DS_GS070",        DS21, "V4-A gate 0.70"),
 ("GS055",           "DS_GS055",        DS21, "V4-A gate 0.55"),
 ("K10_GS100",       "DS_K10_GS100",    DS21, "V4-B topK=10 tren nen GS100"),
 ("K12_GS100",       "DS_K12_GS100",    DS21, "V4-B topK=12 tren nen GS100"),
 ("DCA20_GS100V4",   "DS_DCA20_GS100",  DS21, "V4-C X=-20% tren nen GS100"),
 ("DCA25_GS100V4",   "DS_DCA25_GS100",  DS21, "V4-C X=-25% tren nen GS100"),
 ("DCA30_GS100V4",   "DS_DCA30_GS100",  DS21, "V4-C X=-30% tren nen GS100"),
 ("DCA5_T170V1",     "DS_DCA5",         DS21, "V1 X=-5% cooldown60p tren nen T170"),
 ("DCA8_T170V1",     "DS_DCA8",         DS21, "V1 X=-8% cooldown60p tren nen T170"),
 ("DCA12_T170V1",    "DS_DCA12",        DS21, "V1 X=-12% cooldown60p tren nen T170"),
 ("DCA30_T170V2",    "DS_DCA30",        DS21, "V2 X=-30% cooldown24h tren nen T170"),
 ("DCA40_T170V2",    "DS_DCA40",        DS21, "V2 X=-40% cooldown36h tren nen T170"),
 ("DCA50_T170V2",    "DS_DCA50",        DS21, "V2 X=-50% cooldown48h tren nen T170"),
 ("X2H_V1",          "X1_2XH_V1",       DS21, "#52 gate1.30/K12/F0.015"),
 ("X2H_V2",          "X1_2XH_V2",       DS21, "#52 gate1.30/K16/F0.015"),
 ("X2H_V3",          "X1_2XH_V3",       DS21, "#52 gate1.50/K16/F0.015"),
 ("REGIME",          "RG_ADAPTIVE",     DS21, "gate regime-adaptive BTC30d UP1.00/NOTUP1.70"),
 ("GD92",            "X1_C3_FULL_GD92", DSX1, "DATASET KHAC - gate p15 rolling (audit: NULL/nhieu)"),
 ("PARITY_R",        "X1_C3_FULL_PARITY_R", DSX1, "DATASET KHAC - baseline doi chieu cua GD92"),
]

rows = []
for name, tag, ds, note in CFG:
    try:
        d = C.trades(tag); s = C.equity(tag)
    except Exception as e:
        rows.append(dict(config=name, dataset=ds, year="ERROR", note=str(e)[:60])); continue
    e = pd.to_datetime(d["end"], format="%Y%m%d %H:%M", errors="coerce")
    d = d.assign(ey=e.dt.year)
    def emit(year, sub, seq):
        r = C.rates(sub) if len(sub) else None
        dd = (seq/seq.cummax()-1)*100; uw = seq < seq.cummax()
        rows.append(dict(
            config=name, dataset=ds, year=year,
            n=len(sub),
            win_pct   = round(r["win"],2)     if r else "",
            tsloss_pct= round(r["tsloss"],2)  if r else "",
            meanP_pct = round(r["meanP"],3)   if r else "",
            pnl_usd   = round(float(sub.pnl.sum()),0) if len(sub) else 0.0,
            ret_pct   = round((seq.iloc[-1]/seq.iloc[0]-1)*100, 2),
            maxDD_pct = round(dd.min(),2),
            uw_days   = int(uw.groupby((~uw).cumsum()).sum().max()) if len(uw) else 0,
            equity_end= round(float(seq.iloc[-1]),0),
            note=note))
    for y, sy in s.groupby(s.index.year):
        emit(str(y), d[d.ey == y], sy)
    emit("TOTAL", d, s)

df = pd.DataFrame(rows, columns=["config","dataset","year","n","win_pct","tsloss_pct",
                                 "meanP_pct","pnl_usd","ret_pct","maxDD_pct","uw_days",
                                 "equity_end","note"])
out = "/home/ubuntu/src/BinanceFuturesJava/research/analysis/master_table_all_configs.csv"
df.to_csv(out, index=False)
print("WROTE %s : %d dong, %d config" % (out, len(df), df.config.nunique()))
