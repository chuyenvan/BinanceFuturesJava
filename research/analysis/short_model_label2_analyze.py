#!/usr/bin/env python3
"""short_model_label2_analyze.py — tong hop ket qua PREREG_SHORT_LABEL2 (0-sim, chay tren Oracle).

Doc `sm_label2_score.json` (+ `sm_label2b_score.json`) sinh boi kernel Kaggle, + baseline
`docs/result/RESULT_SHORT_MODEL.json` (nhan cu E=inf). Ap LUAT §7 cua PREREG_SHORT_LABEL2:
  A: rank-IC > 0 ngoai CI (raw & x1,21), mean-seed
  B: ton tai (config, C in {+20%, +30%}): net K=8 DA CREDIT FUNDING (delta_f=-0,585%/72h raw)
     > 0 ngoai CI (raw & x1,21) & >=3/4 nam duong
Xuat bang gon + RESULT_SHORT_LABEL2.json. KHONG cham 2026, KHONG push du lieu.
"""
import argparse
import json
import os

DF_RAW = -0.00585          # short TRA funding, mean %/72h (RESULT_SHORT_DEEP §4)
DF_CLIP = -0.00452
LEG = 1.21


def arm_cfg(tag):
    # PA_t15_E3_S42 / PW_t15_E10_S7 / PN_t15_E10_S13
    p = tag.split("_")
    return p[0], p[1], p[2], p[3]


def out_both(ic):
    return bool(ic.get("out_raw")) and bool(ic.get("out_legacy"))


def mean_lo_hi(d):
    return (sum(d["raw"][0] for d in d) / len(d), sum(d["raw"][1] for d in d) / len(d))


def agg_seeds(arms, tags):
    ic_vals = [arms[t]["ic"]["mean"] for t in tags]
    los = [arms[t]["ic"]["raw"][0] for t in tags]
    his = [arms[t]["ic"]["raw"][1] for t in tags]
    ic_mean = sum(ic_vals) / len(ic_vals)
    lo, hi = sum(los) / len(los), sum(his) / len(his)
    ic_out_raw = lo > 0 or hi < 0
    ilo, ihi = ic_mean - (ic_mean - lo) * LEG, ic_mean + (hi - ic_mean) * LEG
    ic_out_leg = ilo > 0 or ihi < 0
    return {"ic_mean": ic_mean, "ic_raw": [lo, hi], "ic_out_raw": ic_out_raw,
            "ic_out_legacy": ic_out_leg, "ic_out_both": ic_out_raw and ic_out_leg,
            "per_seed_ic": {t: arms[t]["ic"]["mean"] for t in tags}}


def cut_agg(arms, tags, C):
    nets = [arms[t]["cuts"]["%.2f" % C]["net"]["mean"] for t in tags]
    los = [arms[t]["cuts"]["%.2f" % C]["net"]["raw"][0] for t in tags]
    his = [arms[t]["cuts"]["%.2f" % C]["net"]["raw"][1] for t in tags]
    rates = [arms[t]["cuts"]["%.2f" % C]["cut_rate"] for t in tags]
    m = sum(nets) / len(nets)
    lo, hi = sum(los) / len(los), sum(his) / len(his)
    o1 = lo > 0 or hi < 0
    ilo, ihi = m - (m - lo) * LEG, m + (hi - m) * LEG
    o2 = ilo > 0 or ihi < 0
    yrs = {}
    for y in ("2022", "2023", "2024", "2025"):
        vs = [arms[t]["cuts"]["%.2f" % C]["by_year_net"][y] for t in tags
              if arms[t]["cuts"]["%.2f" % C]["by_year_net"].get(y) is not None]
        yrs[y] = (sum(vs) / len(vs)) if vs else None
    return {"net_mean_seed": m, "net_raw": [lo, hi], "out_raw": o1, "out_legacy": o2,
            "out_both": o1 and o2, "cut_rate_mean_seed": sum(rates) / len(rates),
            "by_year": yrs}


def funding(net, cut_by_year):
    """Credit funding phang: net_funded = net + DF_RAW (<0 = chi phi)."""
    return net + DF_RAW, {y: (v + DF_RAW if v is not None else None)
                          for y, v in cut_by_year.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--score", default="sm_label2_score.json")
    ap.add_argument("--score-b", default="sm_label2b_score.json")
    ap.add_argument("--baseline", default="docs/result/RESULT_SHORT_MODEL.json")
    ap.add_argument("--out", default="docs/result/RESULT_SHORT_LABEL2.json")
    a = ap.parse_args()

    res = {"delta_funding_raw": DF_RAW, "delta_funding_clip": DF_CLIP, "configs": {}}
    if os.path.exists(a.score):
        s = json.load(open(a.score))
        arms = s["arms"]
        # gom tag theo (mode,thr,E)
        groups = {}
        for t in arms:
            if "error" in arms[t]:
                continue
            mode, thr, e, seed = arm_cfg(t)
            groups.setdefault((mode, thr, e), []).append(t)
        for (mode, thr, e), ts in sorted(groups.items()):
            ts.sort(key=lambda x: int(x.split("_")[-1].lstrip("S")))
            g = {"n_seed": len(ts), "tags": ts}
            g.update(agg_seeds(arms, ts))
            g["cuts"] = {}
            for C in (0.20, 0.30, 0.50, 0.90):
                key = "%.2f" % C
                if key not in arms[ts[0]]["cuts"]:
                    continue
                c = cut_agg(arms, ts, C)
                fn, fy = funding(c["net_mean_seed"], c["by_year"])
                c["net_funded_mean_seed"] = fn
                c["by_year_funded"] = fy
                c["years_pos_funded"] = sum(1 for v in fy.values() if v is not None and v > 0)
                c["B_pass"] = bool(c["out_both"] and fn > 0 and c["years_pos_funded"] >= 3)
                g["cuts"][key] = c
            g["A_pass"] = bool(g["ic_mean"] > 0 and g["ic_out_both"])
            res["configs"]["%s|%s|%s" % (mode, thr, e)] = g
    if os.path.exists(a.score_b):
        sb = json.load(open(a.score_b))
        res["controls_raw"] = {t: {"ic": sb["arms"][t]["ic"]["mean"],
                                   "ic_out_both": out_both(sb["arms"][t]["ic"]),
                                   "cut30_rate": sb["arms"][t]["cuts"].get("0.30", {}).get("cut_rate"),
                                   "cut30_net": sb["arms"][t]["cuts"].get("0.30", {}).get("net", {}).get("mean"),
                                   "by_year_cut30": sb["arms"][t]["cuts"].get("0.30", {}).get("by_year_net")}
                               for t in sb["arms"] if "error" not in sb["arms"][t]}

    # baseline (E=inf) tu RESULT_SHORT_MODEL
    if os.path.exists(a.baseline):
        b = json.load(open(a.baseline))
        res["baseline_Einf"] = {"A_rank_ic": b["A_rank_ic"], "B_econ_cut": b["B_econ_cut"],
                                "no_cut": b["no_cut"], "cut_rates_mean": b["cut_rates_mean"],
                                "VERDICT": b["VERDICT"]}

    # VERDICT
    go = False
    reason = []
    for k, g in res["configs"].items():
        if not g["A_pass"]:
            reason.append("%s: A FAIL (IC %+0.5f out_both=%s)" % (k, g["ic_mean"], g["ic_out_both"]))
            continue
        for C, c in g["cuts"].items():
            if c["B_pass"]:
                go = True
                reason.append("%s cut %s: B PASS funded net %+0.5f yrs+ %d" %
                              (k, C, c["net_funded_mean_seed"], c["years_pos_funded"]))
        if not any(c["B_pass"] for c in g["cuts"].values()):
            reason.append("%s: A PASS nhung B FAIL (funded net<=0 hoac <3/4 nam %s)" %
                          (k, {C: (round(c["net_funded_mean_seed"], 5), c["years_pos_funded"])
                               for C, c in g["cuts"].items()}))
    res["VERDICT"] = "GO" if go else "NO-GO/NULL"
    res["verdict_reason"] = reason
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    json.dump(res, open(a.out, "w"), indent=1, default=str)
    print("VERDICT:", res["VERDICT"])
    for r in reason:
        print("  -", r)
    for k, g in res["configs"].items():
        print("%-14s IC=%+0.5f out_both=%s" % (k, g["ic_mean"], g["ic_out_both"]))
        for C, c in g["cuts"].items():
            print("    C+%s cutrate=%.4f net=%+0.5f raw[%+0.5f,%+0.5f] ob=%s funded=%+0.5f yrs+=%d by=%s"
                  % (C, c["cut_rate_mean_seed"], c["net_mean_seed"], c["net_raw"][0], c["net_raw"][1],
                     c["out_both"], c["net_funded_mean_seed"], c["years_pos_funded"],
                     {y: (round(v, 4) if v is not None else None) for y, v in c["by_year"].items()}))
    print("-> %s" % a.out)


if __name__ == "__main__":
    main()
