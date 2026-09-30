#!/usr/bin/env python3
"""short_v3_analyze.py — gộp 3 seed + áp LUẬT §6 PREREG_SHORT_V3 (0-sim, chạy trên Oracle).

Đọc `smv3.json` (sinh bởi `short_v3_score.py`) → mean-seed + CI (raw & ×1,21) → RESULT JSON.
N1a (lọc theo f_72h ≥ 0) là LỌC LOOKAHEAD (dùng funding tương lai) ⇒ chỉ báo như CẬN TRÊN,
KHÔNG đủ điều kiện GO. GO chỉ xét cấu hình TRADEABLE (N1b/N2b/P1/P2/C hợp lệ, không lookahead).
"""
import argparse
import json

LEG = 1.21
LOOKAHEAD = {"N1a_k8_T72_C30", "N1a_k8_T72_C50", "C_k3_N1a_regime_C30",
             "C_k2_N1a_regime_C20", "C_k8_N1a_regime_C30"}
BASELINE = "base_k8_T72_C30"


def agg(arms, name):
    v = [a[name] for a in arms if name in a and "err" not in a[name]]
    if not v:
        return None
    n = len(v)
    net_pre = sum(x["net_pre"]["mean"] for x in v) / n
    net_post = sum(x["net_post"]["mean"] for x in v) / n
    net_str = sum(x["net_post_stress"]["mean"] for x in v) / n
    lo = sum(x["net_post"]["raw"][0] for x in v) / n
    hi = sum(x["net_post"]["raw"][1] for x in v) / n
    o1 = lo > 0 or hi < 0
    ilo, ihi = net_post - (net_post - lo) * LEG, net_post + (hi - net_post) * LEG
    o2 = ilo > 0 or ihi < 0
    wr = sum(x["winrate"] for x in v) / n
    yrs = sum(x["yrs_pos_post"] for x in v) / n
    by = {}
    for y in ("2022", "2023", "2024", "2025"):
        vals = [x["by_year_post"][y] for x in v if x["by_year_post"].get(y) is not None]
        by[y] = round(sum(vals) / len(vals), 6) if vals else None
    return {"n_seed": n, "kept_frac": sum(x["kept_frac"] for x in v) / n,
            "net_pre": round(net_pre, 6), "net_post": round(net_post, 6),
            "net_post_stress": round(net_str, 6),
            "raw": [round(lo, 6), round(hi, 6)], "infl": [round(ilo, 6), round(ihi, 6)],
            "out_raw": bool(o1), "out_legacy": bool(o2), "out_both": bool(o1 and o2),
            "winrate": round(wr, 4), "winrate_pre": round(sum(x["winrate_pre"] for x in v) / n, 4),
            "yrs_pos_post": round(yrs, 2), "by_year_post": by,
            "fund_mean": round(sum(x["fund_mean"] for x in v) / n, 6)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--score", default="/tmp/smv3.json")
    ap.add_argument("--out", default="docs/result/RESULT_SHORT_V3.json")
    a = ap.parse_args()
    sc = json.load(open(a.score))
    arms = list(sc["arms"].values())
    names = sc["configs"]
    res = {"prereg": "docs/prereg/PREREG_SHORT_V3.md", "cost": sc["cost"],
           "n_arm_seed": len(arms), "lookahead_configs": sorted(LOOKAHEAD),
           "configs": {}, "verdict_reason": []}
    for nm in names:
        res["configs"][nm] = agg(arms, nm)
    base = res["configs"][BASELINE]
    res["baseline"] = base
    go = False
    for nm, c in res["configs"].items():
        if c is None:
            continue
        A = c["out_both"] and c["net_post"] > 0
        B = c["yrs_pos_post"] >= 3
        C = c["winrate"] >= 0.55 and c["winrate"] >= base["winrate"] + 0.05
        la = nm in LOOKAHEAD
        res["configs"][nm]["A"] = bool(A and not la)
        res["configs"][nm]["B"] = bool(B)
        res["configs"][nm]["C"] = bool(C)
        res["configs"][nm]["GO"] = bool(A and B and C and not la)
        go = go or res["configs"][nm]["GO"]
    res["VERDICT"] = "GO" if go else "NO-GO/NULL"
    res["n_go_tradeable"] = sum(1 for nm, c in res["configs"].items()
                                if c and c.get("GO"))
    res["best_tradeable"] = max(
        [(nm, c["net_post"]) for nm, c in res["configs"].items()
         if c and nm not in LOOKAHEAD and c["net_post"] > -9], key=lambda t: t[1], default=None)
    json.dump(res, open(a.out, "w"), indent=1, default=str)
    print("VERDICT:", res["VERDICT"], "| baseline winrate", base["winrate"],
          "net_pre", base["net_pre"], "net_post", base["net_post"])
    print("%-24s %8s %8s %8s %6s %5s %5s %5s" % ("config", "net_pre", "net_post", "out_both",
                                                  "winr", "yrs+", "A", "GO"))
    for nm, c in res["configs"].items():
        if c is None:
            continue
        print("%-24s %+8.5f %+8.5f %8s %6.3f %5.2f %5s %5s%s"
              % (nm, c["net_pre"], c["net_post"], c["out_both"], c["winrate"], c["yrs_pos_post"],
                 c["A"], c["GO"], " [LOOKAHEAD]" if nm in LOOKAHEAD else ""))
    print("-> %s" % a.out)


if __name__ == "__main__":
    main()
