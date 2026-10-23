#!/usr/bin/env python3
"""OB_SR 09: render markdown tables for the result doc."""
import json
import os

import numpy as np
import pandas as pd

OUT = os.path.dirname(os.path.abspath(__file__))
FEAT = ["A%d" % k for k in (1, 2, 3, 5)] + ["B%d" % k for k in (1, 2, 3, 5)] + \
       ["R%d" % k for k in (1, 2, 3, 5)] + ["wA%d" % k for k in (1, 2, 3, 5)] + ["wB%d" % k for k in (1, 2, 3, 5)]
OUTS = {"entry": ["arm168", "mfe24_bps", "mfe72_bps"], "arm": ["gb_med", "pt_med"],
        "h168": ["extra24_bps", "extra72_bps"]}
NAME = {"arm168": "arm168", "mfe24_bps": "MFE24", "mfe72_bps": "MFE72",
        "gb_med": "giveback", "pt_med": "PnL trail", "extra24_bps": "extra24", "extra72_bps": "extra72"}


def f(v):
    return "—" if pd.isna(v) else ("%+.3f" % v)


def main():
    ic = pd.read_csv(OUT + "/ic.csv")
    st = json.load(open(OUT + "/stats.json"))
    ci = pd.read_csv(OUT + "/ci_top.csv")
    ep = pd.read_csv(OUT + "/ic_episode.csv")
    dec = json.load(open(OUT + "/deciles_2024.json"))
    L = []
    L.append("### Phủ dữ liệu (V3)\n")
    L.append("| Mốc | Năm | cụm (anchor) | có bookDepth | phủ |")
    L.append("|---|---|---|---|---|")
    for p in ("entry", "arm", "h168"):
        for y in (2023, 2025, 2024):
            k = "%s_%d" % (p, y)
            if k in st["coverage"]:
                c = st["coverage"][k]
                L.append("| %s | %d | %d | %d | %.1f%% |" % (p, y, c["n"], c["ok"], 100 * c["frac"]))
    L.append("")
    for p, outs in OUTS.items():
        for o in outs:
            z = ic[(ic.point == p) & (ic.out == o)].pivot_table(index="feat", columns="year", values="ic")
            if not len(z):
                continue
            L.append("### %s × %s (Spearman, đơn vị anchor)\n" % (p, NAME[o]))
            L.append("| feature | 2023 | 2025 | 2024 (kiểm) | gộp 23+25 | n2024 |")
            L.append("|---|---|---|---|---|---|")
            nn = ic[(ic.point == p) & (ic.out == o) & (ic.year == 2024)].set_index("feat")["n"]
            for ft in FEAT:
                if ft in z.index:
                    r = z.loc[ft]
                    n24 = int(nn.get(ft, 0))
                    L.append("| %s | %s | %s | %s | %s | %d |" % (
                        ft, f(r.get(2023)), f(r.get(2025)), f(r.get(2024)), f(r.get(2325)), n24))
            L.append("")
    L.append("### Top 6 combo mỗi mốc theo |IC 2024| — CI bootstrap theo ngày\n")
    L.append("| mốc | feature | outcome | IC2024 | CI95 2024 | n | IC gộp 23+25 | CI95 gộp |")
    L.append("|---|---|---|---|---|---|---|---|")
    for r in ci.itertuples():
        L.append("| %s | %s | %s | %+.3f | [%+.3f; %+.3f] | %d | %+.3f | [%+.3f; %+.3f] |" % (
            r.point, r.feat, NAME.get(r.out, r.out), r.ic2024, r.ci_lo, r.ci_hi, r.n2024,
            r.ic_pool, r.pool_lo, r.pool_hi))
    L.append("")
    L.append("### IC tách đợt sập / thường — các ô |IC| ≥ 0,10 (2024)\n")
    L.append("| mốc | feature | outcome | nhóm | n | IC |")
    L.append("|---|---|---|---|---|---|")
    e = ep[(ep.year == 2024) & (ep.ic.abs() >= 0.10)].sort_values("ic", key=abs, ascending=False)
    for r in e.itertuples():
        L.append("| %s | %s | %s | %s | %d | %+.3f |" % (
            r.point, r.feat, NAME.get(r.out, r.out), "sập" if r.episode == 1 else "thường", r.n, r.ic))
    L.append("")
    L.append("### Decile 2024 — các combo |IC2024| ≥ 0,08\n")
    for d in dec:
        L.append("- **%s × %s × %s** (n=%d, IC=%+.3f): decile thấp→cao = %s; spread = %+.1f; notional median = %.0f USD" % (
            d["point"], d["feat"], NAME.get(d["out"], d["out"]), d["n"], d["ic"],
            ", ".join("%.1f" % x for x in d["dec"]), d["spread"], d["med_notional"]))
    open(OUT + "/tables.md", "w").write("\n".join(L))
    print("wrote tables.md", len(L), "lines")
    # summary stats for the doc
    P = ic.pivot_table(index=["point", "feat", "out"], columns="year", values="ic").reset_index()
    P["minabs"] = P[[2023, 2025, 2024]].abs().min(axis=1)
    P["samesign"] = (np.sign(P[2023]) == np.sign(P[2025])) & (np.sign(P[2025]) == np.sign(P[2024]))
    print("combos", len(P), "same sign", int(P["samesign"].sum()), "max minabs", P["minabs"].max())
    print(P.sort_values("minabs", ascending=False).head(5)[["point", "feat", "out", 2023, 2025, 2024, "minabs", "samesign"]].to_string(index=False))


if __name__ == "__main__":
    main()
