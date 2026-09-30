#!/usr/bin/env python3
"""short_model_judge.py — áp LUẬT §7 PREREG_SHORT_MODEL lên `sm_score.json` (cơ học, không nhìn mắt).

  A (tín hiệu): mean-seed rank-IC > 0 VÀ mọi seed có IC out_both (ngoài raw + ×1,21).
  B (kinh tế):  tồn tại C* ∈ {+30,+50,+90}%: net(K_sel, C*) mean-seed > 0, mọi seed out_both,
                và mean-seed net > 0 ở >=3/4 năm (2022..2025).
  GO = A AND B. Ngược lại NO-GO/NULL (không vùng xám).
Lệnh: python3 short_model_judge.py --json /tmp/smout/sm_score.json
"""
import argparse
import json
import statistics as st


def seeds_short(arms):
    return sorted([k for k in arms if k.startswith("SHORT")])


def mean(xs):
    xs = [x for x in xs if x is not None]
    return float(st.mean(xs)) if xs else float("nan")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", required=True)
    a = ap.parse_args()
    J = json.load(open(a.json))
    arms = J["arms"]
    ks = J["k_sel"]
    sh = seeds_short(arms)
    out = {"n_seed": len(sh), "seeds": sh, "detail": {}}

    # ---- A ----
    ic_all = []
    ic_ok = True
    for s in sh:
        ic = arms[s]["ic"]
        ic_all.append(ic["mean"])
        ic_ok &= bool(ic["mean"] > 0 and ic["out_raw"] and ic["out_legacy"])
        out["detail"][s] = {"ic_mean": round(ic["mean"], 6), "ic_raw": ic["raw"],
                            "ic_out_raw": ic["out_raw"], "ic_out_legacy": ic["out_legacy"],
                            "IC>0&out_both": bool(ic["mean"] > 0 and ic["out_raw"] and ic["out_legacy"])}
    A_ic_mean = mean(ic_all)
    A = bool(A_ic_mean > 0 and ic_ok)
    out["A"] = {"ic_mean_seed": round(A_ic_mean, 6), "all_seed_positive_out_both": bool(ic_ok),
                "PASS": A}

    # ---- B ----
    good = {k: v for k, v in arms.items() if k.startswith("SHORT") and "error" not in v}
    B_detail = {}
    B_any = False
    for C in list(next(iter(good.values()))["cuts"].keys()):
        nets, oks, yr_mean = [], True, {}
        for s in sh:
            c = arms[s]["cuts"][C]
            nets.append(c["net"]["mean"])
            oks &= bool(c["net"]["mean"] > 0 and c["net"]["out_raw"] and c["net"]["out_legacy"])
            for y in (2022, 2023, 2024, 2025):
                v = c["by_year_net"].get(str(y), c["by_year_net"].get(y))
                yr_mean.setdefault(y, []).append(v)
        ymean = {y: mean(v) for y, v in yr_mean.items()}
        yr_pos = sum(1 for y in (2022, 2023, 2024, 2025) if ymean.get(y, float("nan")) > 0)
        nmean = mean(nets)
        ok = bool(nmean > 0 and oks and yr_pos >= 3)
        B_detail[C] = {"net_mean_seed": round(nmean, 6), "all_seed_positive_out_both": bool(oks),
                       "years_net_pos": yr_pos, "year_mean": {str(k): round(v, 6) for k, v in ymean.items()},
                       "PASS": ok}
        B_any |= ok
    out["B"] = {"scope": "SHORT arm (chi ap cho cat cung)", "by_cut": B_detail, "PASS": bool(B_any)}

    # đối chiếu đối xứng
    lk = [k for k in arms if k.startswith("LONG")]
    if lk:
        L = arms[lk[0]]
        out["LONG_mirror"] = {"ic": round(L["ic"]["mean"], 6),
                              "k%d_net_long" % ks: round(L["k%d" % ks]["net"]["mean"], 6),
                              "mirror_short_net": round(L.get("mirror_short", {}).get("net", {}).get("mean", float("nan")), 6)}
    out["VERDICT"] = "GO" if (A and B_any) else "NO-GO/NULL"
    json.dump(out, open(a.json.replace(".json", "_verdict.json"), "w"), indent=1)
    print(json.dumps(out, indent=1))
    print("\n=> VERDICT:", out["VERDICT"])


if __name__ == "__main__":
    main()
