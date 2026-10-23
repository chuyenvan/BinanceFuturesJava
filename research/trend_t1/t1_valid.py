"""TREND_T1 validation (pipeline side): V1 look-ahead x3, V2 asserts summary, single-coin runs for V3 (compared by t1_indep.py)."""
import os, sys, json, copy
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import t1_core as C
OUT = os.path.join(C.WK, "valid"); os.makedirs(OUT, exist_ok=True)
rep = {}
d = C.load_daily()
# V2 summary
rep["V2"] = dict(ts_int64=str(d.day.dtype) == "int64" and str(d.ts_last.dtype) == "int64", max_rows=int(d.n_rows.max()),
                 sym_days=int(len(d)), partial_days=int((d.n_rows < 1440).sum()), dup=int(d.duplicated(["sym", "day"]).sum()),
                 px01_not_min1=int((d.px01_min != 1).sum()))
P = C.build_panel(d); I = C.indicators(P); inU, mem = C.universe(P)
base_tr = {}; base_log = {}
for v in C.VARIANTS:
    lg = []; base_tr[v] = C.select(v, P, I, inU, log=lg); base_log[v] = lg
# V1 look-ahead
cuts = ["2022-08-15", "2023-03-31", "2024-01-07", "2024-11-30", "2025-06-15"]
v1 = {}
for cut in cuts:
    cms = int(pd.Timestamp(cut).value // 10**6)
    dd = d.copy()
    m = dd.day > cms
    for col in ("close", "px01", "qv"):
        dd.loc[m, col] = dd.loc[m, col] * 3.0
    P2 = C.build_panel(dd); I2 = C.indicators(P2); inU2, mem2 = C.universe(P2)
    ci = int((cms - C.DAY0) // C.DAY)
    ok = {}
    umon_ok = all(mem2[k] == mem[k] for k in mem if pd.Timestamp(k + "-01") <= pd.Timestamp(cut) + pd.Timedelta(days=1))
    for v in C.VARIANTS:
        lg2 = []; tr2 = C.select(v, P2, I2, inU2, log=lg2)
        L1 = [x for x in base_log[v] if x["d"] <= ci]; L2 = [x for x in lg2 if x["d"] <= ci]
        e1 = sorted((t["s"], t["din"]) for t in base_tr[v] if t["din"] <= ci + 1)
        e2 = sorted((t["s"], t["din"]) for t in tr2 if t["din"] <= ci + 1)
        x1 = sorted((t["s"], t["din"], t["dout"], t["forced"]) for t in base_tr[v] if t["dout"] is not None and t["dout"] <= ci + 1)
        x2 = sorted((t["s"], t["din"], t["dout"], t["forced"]) for t in tr2 if t["dout"] is not None and t["dout"] <= ci + 1)
        # also: changed data after cut must change something later (sanity that the test bites) -> compare logs after cut
        after_diff = sum(1 for a, b in zip([x for x in base_log[v] if x["d"] > ci], [x for x in lg2 if x["d"] > ci]) if a != b)
        ok[v] = dict(log_equal=L1 == L2, n_log=len(L1), entries_equal=e1 == e2, n_entries=len(e1), exits_equal=x1 == x2, n_exits=len(x1), after_cut_days_differ=after_diff)
    v1[cut] = dict(universe_equal=umon_ok, variants=ok)
    print(cut, umon_ok, {v: (o["log_equal"], o["entries_equal"], o["exits_equal"], o["after_cut_days_differ"]) for v, o in ok.items()}, flush=True)
rep["V1"] = v1
rep["V1_pass"] = all(x["universe_equal"] and all(o["log_equal"] and o["entries_equal"] and o["exits_equal"] for o in x["variants"].values()) for x in v1.values())
# single-coin runs (for V3 independent check)
usyms = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]
F0, Fr, fev, frep = C.funding(P, usyms)
for s in usyms:
    inUs, _ = C.universe(P, force=[s])
    for v in ("V1", "V3"):
        tr = C.select(v, P, I, inUs)
        R = C.run_engine(tr, P, I, F0, Fr, v)
        pd.DataFrame(dict(day=R["days"], E=R["E"], ret=R["ret"])).to_parquet(os.path.join(OUT, "single_%s_%s.parquet" % (v, s)), index=False)
        pd.DataFrame([dict(din=int(P["days"][t["din"]]), dout=(int(P["days"][t["dout"]]) if t["dout"] is not None else -1), q=t["q"], px_in=t["px_in"], px_out=t["px_out"], fund=t["fund"], pnl=t["pnl"]) for t in tr]).to_csv(os.path.join(OUT, "single_trades_%s_%s.csv" % (v, s)), index=False)
        print("single", v, s, len(tr), "E_end", R["E"][-1], flush=True)
json.dump(rep, open(os.path.join(OUT, "valid_pipeline.json"), "w"), indent=1, default=str)
print("V1_pass", rep["V1_pass"], "V2", rep["V2"])
