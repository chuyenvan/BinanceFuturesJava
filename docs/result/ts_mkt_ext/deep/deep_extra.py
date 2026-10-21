#!/usr/bin/env python3
"""TS_MKT_EXT DEEP - bo sung mo ta: (1) tach dPnL = direct (cum hoan) + sizing (lai kep: size theo so du lon hon)
+ phan du (slot/von/lenh khac); (2) direct theo nam dong; (3) bang cum hoan HO theo seed. Doc deep.json +
deferred_clusters.csv, ghi deep_extra.json + deep_extra.md."""
import json
import logging
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import deep_analysis as A  # noqa: E402  (import gvz_mtm truoc R ben trong)

log = logging.getLogger("deep_extra")
HERE = A.HERE


def bal_at(d, cap0, t):
    """so du thuc hien (cap0 + PnL cac leg da dong truoc t) tai cac moc t (local)."""
    te = np.sort(d["te"].to_numpy())
    cp = np.concatenate([[0.0], np.cumsum(d.sort_values("te")["pnl"].to_numpy())])
    return cap0 + cp[np.searchsorted(te, t, side="left")]


def main():
    DF = pd.read_csv(HERE + "/deferred_clusters.csv", dtype={"seed": str})
    DF["t0"] = pd.to_datetime(DF["t0"])
    DF["te"] = pd.to_datetime(DF["te"])
    out = {"decomp": {}, "direct_by_year": {}}
    md = ["\n### Tách ΔPnL: direct (cụm hoãn) + sizing (lãi kép) + phần dư\n",
          "| Phạm vi | ΔPnL tổng med [min; max] | direct | sizing ước tính | phần dư | direct % tổng (med) |", "|---|---|---|---|---|---|"]
    for scope, seeds, a, b in (("DEV", A.DEVS, "2021-07-01", "2026-01-01"), ("HO", [str(s) for s in A.HOS], "2026-01-01", "2026-10-01")):
        rows = []
        for s in seeds:
            if scope == "DEV":
                tp, tx, cap0 = "gqsf-" + s.lower(), "tsx-x14-" + s.lower(), A.CAP0
            else:
                tp, tx = "ho4-k24-b-s%s" % s, "tsx-ho-x14-s%s" % s
                cap0 = float(json.load(open(A.KS + tp + "/result.json"))["equity_start"])
            dp, dx = A.load(tp), A.load(tx)
            A0, B0 = pd.Timestamp(a), pd.Timestamp(b)
            g = DF[(DF["scope"] == scope) & (DF["seed"] == s)]
            tot = float(dx.loc[(dx["te"] >= A0) & (dx["te"] < B0), "pnl"].sum() - dp.loc[(dp["te"] >= A0) & (dp["te"] < B0), "pnl"].sum())
            direct = float(g.loc[(g["te"] >= A0) & (g["te"] < B0), "delta"].sum())
            keys = set(zip(g["sym"], g["t0"]))
            cp = A.clusters(dp)
            excl = cp[[k in keys for k in zip(cp["sym"], cp["t0"])]][["sym", "te"]]
            L = dp[(dp["te"] >= A0) & (dp["te"] < B0)].merge(excl.assign(_x=1), on=["sym", "te"], how="left")
            L = L[L["_x"].isna()]
            t = L["ts"].to_numpy()
            ratio = bal_at(dx, cap0, t) / bal_at(dp, cap0, t)
            sizing = float((L["pnl"].to_numpy() * (ratio - 1)).sum())
            rows.append(dict(seed=s, total=tot, direct=direct, sizing=sizing, resid=tot - direct - sizing,
                             ratio_end=float(ratio[-1]) if len(ratio) else 1.0))
            yy = g.assign(y=g["te"].dt.year).groupby("y")["delta"].sum()
            out["direct_by_year"].setdefault(scope, {})[s] = {int(k): float(v) for k, v in yy.items()}
        out["decomp"][scope] = rows
        m = {k: A.mmm([r[k] for r in rows]) for k in ("total", "direct", "sizing", "resid")}
        sh = A.mmm([100 * r["direct"] / r["total"] for r in rows])
        md.append("| %s | %s | %s | %s | %s | %s |" % (scope, A.mm(m["total"], 0, True), A.mm(m["direct"], 0, True),
                                                       A.mm(m["sizing"], 0, True), A.mm(m["resid"], 0, True), A.mm(sh, 0)))
        log.info("DECOMP %s %s", scope, {k: [round(x) for x in v] for k, v in m.items()})
    yrs = sorted({y for v in out["direct_by_year"]["DEV"].values() for y in v})
    md.append("\nDirect Δ (cụm hoãn) theo năm đóng, med [min; max] 8 seed: " + "; ".join(
        "%d %s" % (y, A.mm(A.mmm([out["direct_by_year"]["DEV"][s].get(y, 0.0) for s in A.DEVS]), 0, True)) for y in yrs))
    h = DF[(DF["scope"] == "HO") & (DF["seed"] == "42")].sort_values("t0")
    md.append("\n### Cụm hoãn HO seed 42 (đủ danh sách; các seed khác trong deferred_clusters.csv)\n")
    md.append("| Symbol | Vào (+07) | leg | Thoát | Giữ thêm (h) | PnL@168h | PnL thực | Δ |\n|---|---|---|---|---|---|---|---|")
    for _, r in h.iterrows():
        md.append("| %s | %s | %d | %s | %.0f | %.0f | %.0f | %+.0f |" % (r["sym"], str(r["t0"])[:16], r["n"], r["exit"], r["extra_h"],
                                                                     r["pnl168"], r["pnl"], r["delta"]))
    pool = DF.groupby(["scope", "exit"]).agg(n=("delta", "size"), saved=("delta", lambda v: 100 * (v > 0).mean()),
                                             mean=("delta", "mean"), med=("delta", "median"), sum=("delta", "sum"),
                                             extra_h=("extra_h", "mean")).reset_index()
    md.append("\n### Cụm hoãn theo cách thoát (gộp 8 seed)\n\n| Phạm vi | Thoát | n | % cứu | Δ TB | Δ median | ΣΔ | giữ thêm TB (h) |\n|---|---|---|---|---|---|---|---|")
    for _, r in pool.iterrows():
        md.append("| %s | %s | %d | %.0f | %+.1f | %+.1f | %+.0f | %.0f |" % (r["scope"], r["exit"], r["n"], r["saved"], r["mean"], r["med"],
                                                                     r["sum"], r["extra_h"]))
    out["exit_pool"] = pool.to_dict("records")
    json.dump(out, open(HERE + "/deep_extra.json", "w"), indent=1, default=str)
    open(HERE + "/deep_extra.md", "w").write("\n".join(md))
    log.info("WROTE deep_extra")


if __name__ == "__main__":
    main()
