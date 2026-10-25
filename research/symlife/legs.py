"""SYMLIFE A3: kiem leg printDone X14 (8 seed) vs lifecycle PIT (theo GIAO DICH). Doc lap (khong import pipeline).
printDone start/end = gio +07 -> UTC = -7h. notional = quantity*entry (lev 1). DEV = entry 2022-01-01..2025-12-31 UTC."""
import os, glob, re, numpy as np, pandas as pd
WK = os.path.expanduser("~/claude_master/symlife_wk")
OUTR = os.path.expanduser("~/claude_master/vz_e1_wt/docs/result/symlife")
T = pd.read_parquet(WK + "/lifecycle.parquet").set_index("symbol")
R = pd.read_parquet(WK + "/raw_daycov.parquet")
R["sym"] = R.sym.where(R.sym.str.endswith("USDT"), R.sym + "USDT")
tradedays = R[R.n_trade_pos > 0].groupby("sym").day.apply(lambda x: set(x.tolist())).to_dict()
DIED = "GAIB,STPT,SNT,MBL,RAD,IDEX,GLMR,MDT,AUDIO,BLUEBIRD,FOOTBALL,ANT,DGB,STRAX,COCOS,RAY,FTT,SC,HNT,BTCST,BTS,TOMO,SRM,USDC,BTCDOM,WAVES,GAL,RNDR,FRONT,MATIC,XEM,ORBS,LOOM,OCEAN,DAR,KEY,STMX,AGIX,COMBO,BOND,UNFI,REN,REEF,BNX,LINA,BLZ,KLAY,OMG,FTM,AMB,VIDT,NULS,TROY,BAL,BADGER,ALPACA,EOS,NEIROETH,UXLINK,HIFI,BAKE,SLERF,FLM,KDA,PERP,MYRO,1000X,XCN,PONKE,SWELL,QUICK,SXP,MILK,OBOL,TOKEN,SKATE,REI,FIS,VOXEL,BID,DMC,ZRC,TANSSI,42,COMMON,CUDIS,EPT,ACA,CHESS,DATA,DF,GHST,NKN,RVV,YALA,VFY,1000WHY,BDXN,A2Z,FORTH,HOOK,LRC,NTRN,RDNT,UTK,BIFI,FIO,FUN,OXT,WAN,DEGO,DENT,TRU,B3,DEGEN,ZKJ,IR,DAM,VINE,AI,ATA,FARM,MLN,PHB,SYS,COS,D,HIGH,MBOX,ACX,HFT,PIVX,PYR,VANRY,VIC,ICX,SCRT,STORJ,BTTC,POWR,PROMPT,PUMPBTC,1000000BOB".split(",")
assert len(DIED) == 143
DIEDU = set(s + "USDT" for s in DIED)
H7 = 7 * 3600000; DAY = 86400000
HOLE = (pd.Timestamp("2022-02-26").value // 10**6, pd.Timestamp("2022-03-01").value // 10**6)   # lo raw chung ~50 symbol
out = []
for f in sorted(glob.glob(os.path.expanduser("~/kaggle_sim/out/tsx-x14-*/storage/printDone.csv"))):
    P = pd.read_csv(f, index_col=False)
    P.columns = [c.strip() for c in P.columns]
    P = P[[c for c in P.columns if c]]
    P["seed"] = f.split("/")[-3].replace("tsx-x14-", "")
    out.append(P)
P = pd.concat(out, ignore_index=True)
P["symbol"] = P.sym.astype(str).str.strip() + "USDT"
P["t_in"] = (pd.to_datetime(P.start.astype(str).str.strip(), format="%Y%m%d %H:%M").astype("int64") // 10**6 - H7).astype("int64")
P["t_out"] = (pd.to_datetime(P.end.astype(str).str.strip(), format="%Y%m%d %H:%M").astype("int64") // 10**6 - H7).astype("int64")
P["notional"] = P.quantity.astype(float) * P.entry.astype(float)
P["pnl"] = P.pnl.astype(float)
print("legs", len(P), P.groupby("seed").size().to_dict())
print("t_in range", pd.to_datetime(P.t_in.min(), unit="ms"), pd.to_datetime(P.t_in.max(), unit="ms"))
DEV = (P.t_in >= pd.Timestamp("2022-01-01").value // 10**6) & (P.t_in < pd.Timestamp("2026-01-01").value // 10**6)
P = P[DEV].copy().reset_index(drop=True)
print("DEV legs", len(P), "status", P.status.value_counts().to_dict())
P["in_vision"] = P.symbol.isin(T.index)
P["first_ts"] = P.symbol.map(T.first_trade_ts.astype("float"))
P["last_ts"] = P.symbol.map(T.last_trade_ts.astype("float")).fillna(np.inf)
P["alive_now"] = P.symbol.map(T.status_now == "TRADING")
P["last_utc"] = P.symbol.map(T.last_utc.astype(str))
P["died_live"] = P.symbol.isin(DIEDU)
P["e_before_first"] = P.t_in < P.first_ts
P["e_after_last"] = P.t_in > P.last_ts
P["x_after_last"] = (P.t_out > P.last_ts) & ~P.e_after_last
P["early7d"] = (P.t_in - P.first_ts) < 7 * DAY
P["early30d"] = (P.t_in - P.first_ts) < 30 * DAY
P["in_day"] = P.t_in // DAY
P["notrade_day"] = [(d not in tradedays.get(s, ())) for s, d in zip(P.symbol, P.in_day)]
P["in_hole"] = (P.t_in >= HOLE[0]) & (P.t_in < HOLE[1])
gap = {}
for s, g in T.trade_gaps_ge3_raw.dropna().items():
    iv = []
    for part in (g or "").split(";"):
        m = re.match(r"(\d{4}-\d{2}-\d{2})\.\.(\d{4}-\d{2}-\d{2})", part)
        if m and m.group(1) != "2022-02-26":
            iv.append((pd.Timestamp(m.group(1)).value // 10**6, pd.Timestamp(m.group(2)).value // 10**6 + DAY))
    if iv:
        gap[s] = iv
P["in_gap"] = [any(a <= t < b for a, b in gap.get(s, [])) for s, t in zip(P.symbol, P.t_in)]
P["hold_over_gap"] = [any(t0 < a < t1 for a, b in gap.get(s, [])) for s, t0, t1 in zip(P.symbol, P.t_in, P.t_out)]
N, NP, NN = len(P), P.pnl.sum(), P.notional.sum()
def summ(mask, name):
    q = P[mask]
    return dict(check=name, legs=len(q), legs_pct=round(100 * len(q) / N, 2), notional=round(q.notional.sum()), notional_pct=round(100 * q.notional.sum() / NN, 2),
                pnl=round(q.pnl.sum()), pnl_pct_of_total=round(100 * q.pnl.sum() / NP, 2), n_sym=q.symbol.nunique())
na = P.alive_now.fillna(False).astype(bool)
S = [summ(np.ones(N, bool), "ALL DEV (8 seed)"), summ(~P.in_vision, "symbol khong co tren Vision"),
     summ(P.died_live, "symbol thuoc DIED live (143)"),
     summ(P.died_live & na, "  DIED live nhung con giao dich 2026-10-23"),
     summ(P.died_live & ~na, "  DIED live & da ngung"),
     summ(~na, "symbol da ngung (moi luc) tai 2026-10-23"),
     summ(~na & ~P.died_live, "  da ngung nhung KHONG thuoc DIED live"),
     summ(P.e_before_first, "LOI: entry < first_trade_ts"), summ(P.e_after_last, "LOI: entry > last_trade_ts"),
     summ(P.x_after_last, "exit > last_trade_ts (giu qua delist)"),
     summ(P.in_gap, "LOI: entry trong gap giao dich>=3 ngay (relist)"),
     summ(P.hold_over_gap, "giu vi the qua gap giao dich>=3 ngay"),
     summ(P.notrade_day, "entry vao ngay symbol 0 giao dich (raw)"),
     summ(P.in_hole, "entry trong lo raw 2022-02-26..28"),
     summ(P.early7d, "entry < 7 ngay sau niem yet"), summ(P.early30d, "entry < 30 ngay sau niem yet")]
S = pd.DataFrame(S)
print(S.to_string())
S.to_csv(OUTR + "/legs_checks.csv", index=False)
ps = P.groupby("seed").apply(lambda q: pd.Series(dict(legs=len(q), died_leg_pct=100 * q.died_live.mean(), died_pnl_pct=100 * q[q.died_live].pnl.sum() / q.pnl.sum(),
                                                      x_after_pnl=q[q.x_after_last].pnl.sum(), early7_pnl=q[q.early7d].pnl.sum(), tot_pnl=q.pnl.sum())))
print(ps.round(2).to_string()); print("mean", ps.mean().round(2).to_dict())
x = P[P.x_after_last][["seed", "symbol", "start", "end", "status", "entry", "tp", "notional", "pnl", "last_utc"]].copy()
x["hold_after_last_h"] = ((P.loc[x.index, "t_out"] - P.loc[x.index, "last_ts"]) / 3600000).round(1)
x["pnl_pct"] = (100 * x.pnl / x.notional).round(2)
print("EXIT AFTER LAST:"); print(x.sort_values(["symbol", "seed"]).to_string())
x.to_csv(OUTR + "/legs_exit_after_delist.csv", index=False)
e = P[P.e_before_first | P.e_after_last | P.in_gap | P.hold_over_gap | ~P.in_vision | P.notrade_day][["seed", "symbol", "start", "end", "status", "entry", "tp", "notional", "pnl", "e_before_first", "e_after_last", "in_gap", "hold_over_gap", "in_vision", "notrade_day", "in_hole"]]
print("VIOLATIONS:"); print(e.to_string()[:8000])
e.to_csv(OUTR + "/legs_violations.csv", index=False)
d7 = P[P.early7d].groupby("symbol").agg(legs=("pnl", "size"), pnl=("pnl", "sum"), first=("first_ts", "first"), tin=("t_in", "min"))
d7["first"] = pd.to_datetime(d7["first"], unit="ms"); d7["tin"] = pd.to_datetime(d7.tin, unit="ms")
print("EARLY7D per symbol:"); print(d7.sort_values("legs", ascending=False).head(25).to_string())
st = P[P.died_live].groupby("symbol").agg(legs=("pnl", "size"), pnl=("pnl", "sum"), alive=("alive_now", "first"), last=("last_utc", "first"))
print("DIED-live symbols traded in sim:"); print(st.sort_values("legs", ascending=False).to_string())
st.to_csv(OUTR + "/legs_died_live_by_symbol.csv")
P.to_parquet(WK + "/legs_checked.parquet", index=False)
