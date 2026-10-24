"""Build docs/result/MM_Q1.md tables from artefacts (run2 = ADDENDUM1, run1 = before)."""
import json, glob, os
import pandas as pd
R = "/home/ubuntu/claude_master/vz_e1_wt/docs/result/mm_q1"
S2 = json.load(open(f"{R}/summary.json")); S1 = json.load(open(f"{R}/run1_before_addendum/summary.json"))
C2 = pd.read_csv(f"{R}/configs.csv"); C1 = pd.read_csv(f"{R}/run1_before_addendum/configs.csv")
P2 = pd.read_csv(f"{R}/per_symbol.csv")
f = lambda x, n=2: "—" if x is None or x != x else f"{x:.{n}f}"
out = []
def crit_table(S, title):
    out.append(f"\n**{title}** (L = 300 ms, cons, h = 60 s; bps/fill; CI 95 % bootstrap theo giờ lịch)\n")
    out.append("| d | tier | kỳ | n sym-giờ | n fill | gross | net | CI95 net | fill/giờ trung vị (3 000 s) | V1 | đạt? |")
    out.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for c in S["criterion"]:
        for per in ("D", "K"):
            s = c[per]
            out.append(f"| d{c['depth']} | {c['tier']} | {per} | {s['n_symhours']} | {s['n_fill']} | {f(s['gross_bps'])} | {f(s['net_bps'])} | [{f(s['ci_lo_bps'])}, {f(s['ci_hi_bps'])}] | {f(s['fills_per_symhour_med'],1)} | {f(s['v1']*100,2)} % | {'CÓ' if c[per+'_pass'] else 'KHÔNG'} |")
crit_table(S2, "Bảng 1 — Tiêu chí, lần chạy 2 (ADDENDUM1, CHÍNH THỨC)")
crit_table(S1, "Bảng 1b — Tiêu chí, lần chạy 1 (TRƯỚC sửa bug; chỉ để so)")
out.append("\n**Bảng 2 — Mọi cấu hình ở h = 60 s, lần chạy 2** (net bps/fill [CI95]; fill/giờ trung vị)\n")
out.append("| kỳ | tier | L ms | d | rule | gross | net [CI95] | fill/giờ |")
out.append("|---|---|---|---|---|---|---|---|")
for _, r in C2[C2.h == 60].iterrows():
    out.append(f"| {r.period} | {r.tier} | {r.L} | d{r.d} | {r.rule} | {f(r.gross_bps)} | {f(r.net_bps)} [{f(r.ci_lo_bps)}, {f(r.ci_hi_bps)}] | {f(r.fills_per_symhour_med,1)} |")
out.append("\n**Bảng 3 — Theo horizon (L300, cons, d0), lần chạy 2: gross = adverse selection trước phí**\n")
out.append("| kỳ | tier | h=1 s | h=10 s | h=60 s | h=300 s |")
out.append("|---|---|---|---|---|---|")
x = C2[(C2.L == 300) & (C2.d == 0) & (C2.rule == "cons")]
for (per, tier), g in x.groupby(["period", "tier"], sort=False):
    g = g.set_index("h")
    out.append(f"| {per} | {tier} | " + " | ".join(f"{f(g.loc[h,'gross_bps'])} / {f(g.loc[h,'net_bps'])}" for h in (1, 10, 60, 300)) + " |")
out.append("\n(ô = gross / net, bps/fill)\n")
out.append("\n**Bảng 4 — Theo symbol (L300, cons, d0, h60), lần chạy 2**\n")
out.append("| kỳ | symbol | tier | spread trung vị bps (tick) | V1 % (min giờ) | fill/giờ | gross | net [CI95] |")
out.append("|---|---|---|---|---|---|---|---|")
for _, r in P2.sort_values(["period", "tier", "sym"]).iterrows():
    out.append(f"| {r.period} | {r.sym} | {r.tier} | {f(r.spread_bps_med,3)} ({f(r.spread_ticks_med,1)}) | {f(r.v1*100,2)} ({f(r.v1_min_hour*100,1)}) | {f(r.fills_per_symhour_med,1)} | {f(r.gross_bps)} | {f(r.net_bps)} [{f(r.ci_lo_bps)}, {f(r.ci_hi_bps)}] |")
out.append("\n**Bảng 5 — Mô tả tier: spread, giờ trong ngày (UTC), lợi nhuận/ngày thô (1 lot 100 USD/fill, KHÔNG tính inventory risk), lần chạy 2**\n")
out.append("| kỳ | tier | spread bps | net h60 [0,8) | [8,16) | [16,24) | fill/giờ | USD/ngày/symbol (×1,2) |")
out.append("|---|---|---|---|---|---|---|---|")
for t in S2["tier_desc"]:
    h = t["hod"]
    out.append(f"| {t['period']} | {t['tier']} | {f(t['spread_bps_med'],3)} | {f(h['0-8']['net_bps'])} | {f(h['8-16']['net_bps'])} | {f(h['16-24']['net_bps'])} | {f(t['fills_per_50min_med'],1)} | {f(t['usd_per_day_per_symbol_100usd_lot'],0)} ({f(t['usd_per_day_x1.2'],0)}) |")
v = S2["validation"]; v1 = S1["validation"]
out.append("\n**Bảng 6 — V5 (quote tại mid, L0): AS0 = side×(giá trade − m)/m; tỉ lệ = AS0/(−nửa spread)**\n")
out.append("| tier | lần 2: AS0 bps | nửa spread bps | tỉ lệ | lần 1: tỉ lệ |")
out.append("|---|---|---|---|---|")
for k in ("big", "mid", "small", "all"):
    a = v["V5"][k]; b = v1["V5"][k]
    out.append(f"| {k} | {f(a['as0_bps'],3)} | {f(a['halfspread_bps'],3)} | {f(a['ratio'],3)} | {f(b['ratio'],1)} |")
rej = pd.DataFrame(S2["rejections"]).T.fillna(0).astype(int)
rej.index.name = "kỳ|symbol"
out.append("\n**Bảng 7 — Ứng viên giờ đã duyệt theo lý do (lần chạy 2)**\n")
out.append("| kỳ\\|symbol | " + " | ".join(rej.columns) + " |")
out.append("|" + "---|" * (len(rej.columns) + 1))
for i, r in rej.iterrows():
    out.append(f"| {i} | " + " | ".join(str(x) for x in r.values) + " |")
open("/home/ubuntu/claude_master/mm_wk/report_tables.md", "w").write("\n".join(out) + "\n")
print(json.dumps({k: v[k] for k in v if k != "V5"}, default=float))
print(json.dumps(S2["liqx_desc_D"]))
