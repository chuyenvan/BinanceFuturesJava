"""TREND_T1: print markdown tables from run/results.json (no new computation of PnL)."""
import json, os
import numpy as np, pandas as pd
WK = os.path.expanduser("~/claude_master/trend_t1_wk")
R = json.load(open(WK + "/run/results.json"))
U = json.load(open(WK + "/run/universe_funding.json"))
f = lambda x, n=2: ("%." + str(n) + "f") % x
print("| Biến thể | Kỳ | Sharpe | maxDD | CAGR | p95 ctrl | med ctrl | corr X14 | Sh ghép | Sh X14 | DD ghép | DD X14 | Sh cost×2 |")
print("|---|---|---|---|---|---|---|---|---|---|---|---|---|")
for v, r in R.items():
    for k in ("dev", "test"):
        s = r["stats"][k]; x = r["x14"]["s2024"][k]
        print("| %s | %s | %s | %s%% | %s%% | %s | %s | %s | %s | %s | %s%% | %s%% | %s |" % (v, k.upper(), f(s["sharpe"]), f(100 * s["maxdd"], 1), f(100 * s["cagr"], 1),
              f(r["control_p95"][k]), f(r["control_median"][k]), f(x["corr"]), f(x["sh_comb"]), f(x["sh_x14"]), f(100 * x["dd_comb"], 1), f(100 * x["dd_x14"], 1), f(r["stats_cost2"][k]["sharpe"])))
print()
print("| Biến thể | G1 | G2 | G3 | G4 | G5 | G6 | Verdict | seeds G4 pass | seeds G5 pass |")
print("|---|---|---|---|---|---|---|---|---|---|")
for v, r in R.items():
    g = r["gates"]
    print("| %s | %s | %s | %s | %s | %s | %s | **%s** | %d/8 | %d/8 |" % (v, *["Đạt" if g[k] else "Trượt" for k in ("G1", "G2", "G3", "G4", "G5", "G6")], r["verdict"],
          sum(x["G4"] for x in r["seed_pass"].values()), sum(x["G5"] for x in r["seed_pass"].values())))
print()
print("| Biến thể | Kỳ | exposure ngày % | gross TB | turnover/năm | lệnh/năm | % ngày X14 không leg | trend có vị thế trong ngày X14 không leg % |")
print("|---|---|---|---|---|---|---|---|")
for v, r in R.items():
    for k in ("dev", "test"):
        d = r["desc"][k]
        print("| %s | %s | %s | %s | %s | %s | %s | %s |" % (v, k.upper(), f(d["exposure_days_pct"], 1), f(d["gross_avg"]), f(d["turnover_per_yr"], 1), f(d["trades_per_yr"], 0), f(d["x14_noleg_pct_of_days"], 1), f(d["trend_pos_on_x14_noleg_pct"], 1)))
print()
print("| Biến thể | Sh 2022(5-12) | Sh 2023 | Sh 2024 | Sh 2025 | n lệnh | forced | scaled |")
print("|---|---|---|---|---|---|---|---|")
for v, r in R.items():
    y = r["sharpe_year"]
    print("| %s | %s | %s | %s | %s | %d | %d | %d |" % (v, f(y["2022"]), f(y["2023"]), f(y["2024"]), f(y["2025"]), r["n_trades"], r["n_forced"], r["n_scaled"]))
print()
for v, r in R.items():
    for k in ("dev", "test"):
        c = r["coin"][k]
        print("%s %s top: %s | bottom: %s" % (v, k, ", ".join("%s %+.3f" % (a, b) for a, b in c["top"].items()), ", ".join("%s %+.3f" % (a, b) for a, b in c["bottom"].items())))
print()
for v, r in R.items():
    print(v, "per-seed corr dev/test:", {s: (round(x["dev"]["corr"], 3), round(x["test"]["corr"], 3)) for s, x in r["x14"].items()})
    print(v, "per-seed Sh comb-X14 dev/test:", {s: (round(x["dev"]["sh_comb"] - x["dev"]["sh_x14"], 3), round(x["test"]["sh_comb"] - x["test"]["sh_x14"], 3)) for s, x in r["x14"].items()})
print("x14 window", R["V1"]["x14"]["s2024"]["dev"]["first"], R["V1"]["x14"]["s2024"]["dev"]["last"], R["V1"]["x14"]["s2024"]["test"]["first"], R["V1"]["x14"]["s2024"]["test"]["last"])
fr = U["funding"]; print("funding", {k: v for k, v in fr.items() if k != "u_default_list"}, fr["u_default_list"])
fe = pd.read_parquet(WK + "/run/funding_events_used.parquet")
print("price fallback events by sym (top)", fe[fe.p.isna()].sym.value_counts().head(10).to_dict())
