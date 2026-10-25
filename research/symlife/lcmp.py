"""SYMLIFE B2: live s1 universe (pull242) vs Vision TRADING moi ngay UTC 2026-10-21..23. Doc lap."""
import os, json, numpy as np, pandas as pd
WK = os.path.expanduser("~/claude_master/symlife_wk")
OUTR = os.path.expanduser("~/claude_master/vz_e1_wt/docs/result/symlife")
A = pd.read_parquet(WK + "/vision_act.parquet")
T = pd.read_parquet(WK + "/lifecycle.parquet").set_index("symbol")
LS = pd.read_parquet(WK + "/live_syms.parquet")
LG = pd.read_parquet(WK + "/legs_checked.parquet")
legs_by = LG.groupby("symbol").agg(sim_legs=("pnl", "size"), sim_pnl=("pnl", "sum"))
exec(open(WK + "/died.py").read())   # DIEDU
rows = []
for D in ["2026-10-21", "2026-10-22", "2026-10-23"]:
    a = A[(A.day == D) & A.ok]
    D0 = pd.Timestamp(D).value // 10**6
    vis_tr = set(a[a.n_tr > 0].sym)
    full = set(a[(a.n_tr > 0) & (a["lt"] >= D0 + 86400000 - 3600000)].sym)   # con trade gio cuoi ngay
    zomb = set(a[a.n_tr == 0].sym)
    live = set(LS[(LS.src == "s1") & (LS.day == D)].symbol)
    nmin = LS[(LS.src == "s1") & (LS.day == D)].set_index("symbol").n_min
    miss = sorted(vis_tr - live); extra = sorted(live - vis_tr)
    print(f"== {D}: vision_trading={len(vis_tr)} (trade toi gio cuoi {len(full)}), zombie_files={len(zomb)}, live_s1={len(live)}, THIEU={len(miss)}, THUA={len(extra)}")
    for s in miss:
        r = T.loc[s] if s in T.index else None
        rows.append(dict(day=D, kind="THIEU", symbol=s, in_died=s in DIEDU, ascii=bool(r.ascii) if r is not None else None,
                         first_utc=str(r.first_utc) if r is not None else None, n_tr_day=int(a.set_index("sym").n_tr.get(s, 0)),
                         live_n_min=0, sim_legs=int(legs_by.sim_legs.get(s, 0)), sim_pnl=round(float(legs_by.sim_pnl.get(s, 0.0)), 1)))
    for s in extra:
        r = T.loc[s] if s in T.index else None
        rows.append(dict(day=D, kind="THUA", symbol=s, in_died=s in DIEDU, ascii=None, first_utc=str(r.first_utc) if r is not None else "khong co tren Vision",
                         n_tr_day=int(a.set_index("sym").n_tr.get(s, -1)) if s in set(a.sym) else -1, live_n_min=int(nmin.get(s, 0)),
                         sim_legs=int(legs_by.sim_legs.get(s, 0)), sim_pnl=round(float(legs_by.sim_pnl.get(s, 0.0)), 1)))
    # symbol live co nhung it phut (song nhung bi rot nhieu phut)
    lowcov = nmin[(nmin < 1200) & nmin.index.isin(vis_tr)]
    print("  live co nhung <1200 phut/ngay:", len(lowcov), "median n_min live:", int(nmin.median()))
    print("  vi du it phut:", lowcov.sort_values().head(10).to_dict())
X = pd.DataFrame(rows)
X.to_csv(OUTR + "/live_vs_vision_1021_1023.csv", index=False)
pd.set_option("display.width", 250)
print(X.to_string())
# tong hop theo symbol
g = X.groupby(["kind", "symbol"]).agg(days=("day", "size"), in_died=("in_died", "first"), first_utc=("first_utc", "first"), sim_legs=("sim_legs", "first"), sim_pnl=("sim_pnl", "first")).reset_index()
print(g.to_string())
# DIED vs Vision now
st = T.status_now
died_alive = sorted(s for s in DIEDU if st.get(s) == "TRADING")
died_missing = sorted(s for s in DIEDU if s not in T.index)
stopped_not_died = sorted(s for s in T.index[(st == "STOPPED")] if s not in DIEDU and T.loc[s, "last_utc"] >= pd.Timestamp("2024-01-01"))
print("DIED nhung dang TRADING 10-23:", died_alive, [(s, int(A[(A.sym == s) & (A.day == "2026-10-23")].n_tr.iloc[0])) for s in died_alive])
print("DIED khong co tren Vision:", died_missing)
print("STOPPED (last>=2024) khong co trong DIED:", len(stopped_not_died))
print(T.loc[stopped_not_died, ["last_utc", "file_last_day"]].sort_values("last_utc").to_string())
