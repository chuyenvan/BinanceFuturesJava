#!/usr/bin/env python3
"""short_v3bc_analyze.py — gộp 3 seed + áp LUẬT §6 (PREREG_SHORT_V3/V3B/V3C) cho smv3b.json.

Loại khỏi GO: mọi cấu hình LOOKAHEAD (diag_* dùng maxAdv/maxFav tương lai).
"""
import argparse
import json

LEG = 1.21
BASELINE = "base_T72_C30"
LOOKAHEAD_PREFIX = ("diag_",)
LOOKAHEAD = {"diag_smooth_T72_C30", "diag_smoothhoi_T72_C30", "L1b_diag_smoothhoi_C30"}


def agg(arms, name):
    v = [a[name] for a in arms if name in a and "err" not in a[name]]
    if not v:
        return None
    n = len(v)
    net_pre = sum(x["net_pre"]["mean"] for x in v) / n
    net_post = sum(x["net_post"]["mean"] for x in v) / n
    lo = sum(x["net_post"]["raw"][0] for x in v) / n
    hi = sum(x["net_post"]["raw"][1] for x in v) / n
    o1 = lo > 0 or hi < 0
    ilo, ihi = net_post - (net_post - lo) * LEG, net_post + (hi - net_post) * LEG
    o2 = ilo > 0 or ihi < 0
    by = {}
    for y in ("2022", "2023", "2024", "2025"):
        vals = [x["by_year_post"][y] for x in v if x["by_year_post"].get(y) is not None]
        by[y] = round(sum(vals) / len(vals), 6) if vals else None
    return {"n_seed": n, "n_kept": int(sum(x["n_kept"] for x in v) / n),
            "kept_frac_uni": round(sum(x["kept_frac"] for x in v) / n, 4),
            "net_pre": round(net_pre, 6), "net_post": round(net_post, 6),
            "raw": [round(lo, 6), round(hi, 6)], "infl": [round(ilo, 6), round(ihi, 6)],
            "out_raw": bool(o1), "out_legacy": bool(o2), "out_both": bool(o1 and o2),
            "winrate": round(sum(x["winrate"] for x in v) / n, 4),
            "yrs_pos_post": round(sum(x["yrs_pos_post"] for x in v) / n, 2),
            "ratio_med": round(sum(x["ratio_med"] for x in v) / n, 4),
            "hoi_med": round(sum(x["hoi_med"] for x in v) / n, 4),
            "fund_mean": round(sum(x["fund_mean"] for x in v) / n, 6), "by_year_post": by}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--score", default="/tmp/smv3b.json")
    ap.add_argument("--out", default="docs/result/RESULT_SHORT_V3B.json")
    a = ap.parse_args()
    sc = json.load(open(a.score))
    arms = list(sc["arms"].values())
    res = {"prereg": ["docs/prereg/PREREG_SHORT_V3B.md", "docs/prereg/PREREG_SHORT_V3C.md"],
           "steer": "owner 2026-10-01 06:32", "n_arm_seed": len(arms), "configs": {}}
    for nm in sc["configs"]:
        res["configs"][nm] = agg(arms, nm)
    base = res["configs"][BASELINE]
    res["baseline"] = base
    go = False
    for nm, c in res["configs"].items():
        if c is None:
            res["configs"][nm] = None
            continue
        la = nm in LOOKAHEAD or nm.startswith(LOOKAHEAD_PREFIX) or "diag" in nm
        A = c["out_both"] and c["net_post"] > 0
        B = c["yrs_pos_post"] >= 3
        C = c["winrate"] >= 0.55 and c["winrate"] >= base["winrate"] + 0.05
        c["A"] = bool(A and not la); c["B"] = bool(B); c["C"] = bool(C)
        c["GO"] = bool(A and B and C and not la); c["lookahead"] = bool(la)
        go = go or c["GO"]
    res["VERDICT"] = "GO" if go else "NO-GO/NULL"
    cand = [(nm, c["net_post"], c["out_both"], c["yrs_pos_post"], c["winrate"])
            for nm, c in res["configs"].items() if c and not c["lookahead"]]
    res["best_tradeable"] = max(cand, key=lambda t: t[1]) if cand else None
    json.dump(res, open(a.out, "w"), indent=1, default=str)
    print("VERDICT:", res["VERDICT"], "| baseline wr", base["winrate"], "net_post", base["net_post"])
    print("%-24s %7s %8s %8s %6s %6s %5s %5s %5s" % ("config", "n_kept", "net_pre", "net_post",
                                                      "outb", "winr", "yrs+", "A", "GO"))
    for nm, c in res["configs"].items():
        if c is None:
            print("%-24s VOID (kept=0)" % nm); continue
        print("%-24s %7d %+8.5f %+8.5f %6s %6.3f %5.2f %5s %5s%s"
              % (nm, c["n_kept"], c["net_pre"], c["net_post"], c["out_both"], c["winrate"],
                 c["yrs_pos_post"], c["A"], c["GO"], " [LA]" if c["lookahead"] else ""))
    print("-> %s" % a.out)


if __name__ == "__main__":
    main()
