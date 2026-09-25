#!/usr/bin/env python3
"""money_ranker_score.py — CHẤM 2 THƯỚC cho PREREG_MONEY_RANKER (VIỆC 4).

Dùng NGUYÊN `model_ruler` (ruler_raw / tick_metrics / summarize / delta / ci_mean) — KHÔNG viết lại
chỉ số. KHÔNG train, KHÔNG sim: chỉ đọc bins ĐÃ CÓ + nhãn `.pb`.

2 thước:
  TIỀN : `y = retEnd_h` (h theo `--label-horizon`), nhãn cổng = `retEnd_h > 0,015`
  NHÃN  : `y = maxFav_h` (CHẠM)
Điểm lấy ở slot tốt nhất có thật của từng arm (`MRA72` = slot 3; còn lại slot 0) — khai báo rõ.

Chạy: python3 money_ranker_score.py --arms MRA4,MRB8,MRB32,MRA72 --out /tmp/mrscore/score.json
"""
import argparse
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import model_ruler as MR                       # noqa: E402

LEG = 1.21        # model_ruler.G.LEGACY — do rong de 'ngoai CI' cua `decide()`


def _mk(v):
    """Gon hoa 1 chi so: mean + 3 co 'ngoai CI' (raw / strict 1.21 / honest k=2) + huong."""
    o1, o2, o3, dr = decide2(v["mean"], v["raw"], v["infl"])
    return {"mean": round(v["mean"], 6), "raw": o1, "w121": o2, "strict": o2, "honest": o3,
            "dir": dr, "infl": [round(x, 6) for x in v["infl"]],
            "hi": [round(v["mean"] + (v["infl"][0] - v["mean"]) * INFL / LEG, 6),
                   round(v["mean"] + (v["infl"][1] - v["mean"]) * INFL / LEG, 6)]}


def decide2(mean, raw, infl):
    """(ngoai_raw, ngoai_legacy_1.21, ngoai_inflate_k2, huong).
    `honest` = raw + do rong inflate(k=2) (PREREG_MONEY_RANKER §2); `strict` = `model_ruler.decide`
    (dung 1.21 — RONG HON ⇒ CHAT HON). Luat dung ban CHAT (`strict`) de khong bi coi la noi nguong.
    """
    o1 = raw[0] > 0 or raw[1] < 0
    o2 = infl[0] > 0 or infl[1] < 0
    hi = [mean + (infl[0] - mean) * INFL / LEG, mean + (infl[1] - mean) * INFL / LEG]
    o3 = hi[0] > 0 or hi[1] < 0
    return bool(o1), bool(o2), bool(o1 and o3), (1 if mean > 0 else -1)

# nho dem `load_labels` (doc .pb ~48M dong) — 32 luot cham se doc lai 32 lan neu khong cache
_LBL_MEMO = {}
_LBL_ORIG = MR.load_labels


def _cached_load_labels(labels_dir, cols, key_col=None):
    k = (labels_dir, tuple(cols), key_col)
    if k not in _LBL_MEMO:
        _LBL_MEMO[k] = _LBL_ORIG(labels_dir, cols, key_col)
    return _LBL_MEMO[k]


MR.load_labels = _cached_load_labels

LABELS = "/home/ubuntu/label_15m"
TMP = "/tmp/mrscore"
CACHE = os.path.join(TMP, "cache")
os.makedirs(CACHE, exist_ok=True)

SLOT3 = {"MRA72"}          # arm co DIEM o slot 3 (72h)
CUT15 = int(pd.Timestamp("2022-04-01", tz="UTC").value // 10**6) - 7 * 3600000
RULE = ("pacc", "ic", "dec_mono")
EXTRA = ("dec_rho", "glift8", "netm8", "auc8", "lift8", "base")
INFL = 1.177410           # inflate(k=2) — in lai tu c3_rates


def ticks_for(arm, bins, ruler, folds):
    """ruler: 'money4' | 'money72' | 'lab4' | 'lab72'."""
    folds = [f for f in folds if os.path.exists(os.path.join(bins, "predict_wf_%s.bin" % f))]
    cp = os.path.join(CACHE, "%s_%s.parquet" % (arm, ruler))
    if os.path.exists(cp):
        d = pd.read_parquet(cp)
        print("  [cache] %-8s %-8s n_tick=%d" % (arm, ruler, len(d)), flush=True)
        return d
    h_lab = "72h" if ruler.endswith("72") else "4h"
    h_pt = "72h" if (ruler.endswith("72") and arm in SLOT3) else "4h"
    y_kind = "maxfav" if ruler.startswith("lab") else "retend"
    R, _aux = MR.ruler_raw(bins, LABELS, folds, False, h_pt, h_lab, "y2", y_kind)
    if R is None:
        print("  [N/A]   %-8s %-8s (khong co diem/nhan)" % (arm, ruler), flush=True)
        return None
    d = R["self"]
    d.to_parquet(cp, index=False)
    print("  [calc]  %-8s %-8s pt=%s lab=%s y=%s n_tick=%d n_coin=%.1f"
          % (arm, ruler, h_pt, h_lab, y_kind, len(d), d.n_coin.mean()), flush=True)
    return d


def summ(d, inflate=INFL):
    if d is None:
        return None
    cols = [m for m in (RULE + EXTRA if d.shape[1] else []) if m in d.columns]
    s = MR.summarize(d, "x", cols, inflate)
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", required=True)
    ap.add_argument("--bins-root", default="/tmp/mrbins")
    ap.add_argument("--controls", default="45deploy,A45,V5,V1")
    ap.add_argument("--rulers", default="money4,money72,lab4,lab72")
    ap.add_argument("--out", default=os.path.join(TMP, "score.json"))
    a = ap.parse_args()

    bins_of = {}
    NEWARMS = [x for x in a.arms.split(",") if x.strip()]
    for n in a.controls.split(","):
        bins_of[n] = dict(MR.PATHS)[n][0] if n in MR.PATHS else None
    for n in NEWARMS:
        bins_of[n] = os.path.join(a.bins_root, n)
    need = [n for n in bins_of if bins_of[n] is None or not os.path.exists(
        os.path.join(bins_of[n], "predict_wf_20220101.bin"))]
    print("### ARMS: %s | THIEU BINS: %s" % (list(bins_of), need), flush=True)
    folds = MR.FOLDS

    T = {}          # (arm, ruler) -> per-tick frame
    RULERS = [x for x in a.rulers.split(",") if x]
    for ruler in RULERS:
        for arm, bd in bins_of.items():
            if bd is None:
                continue
            T[(arm, ruler)] = ticks_for(arm, bd, ruler, folds)

    out = {"arms": list(bins_of), "controls": a.controls.split(","), "inflate_k2": INFL,
           "summary": {}, "delta": {}, "rule": {}}
    for (arm, ruler), d in T.items():
        if d is None:
            continue
        for setname, sub in (("all16", d), ("ge202204", d[d.ts >= CUT15])):
            s = summ(sub)
            out["summary"]["%s|%s|%s" % (arm, ruler, setname)] = {
                "n_tick": s["n_tick"], "n_coin": round(float(s["n_coin_mean"]), 2),
                "metrics": {m: _mk(v) for m, v in s["metrics"].items()}}

    for ruler in RULERS:
        for arm in NEWARMS:
            d = T.get((arm, ruler))
            if d is None:
                continue
            for ctl in [x for x in a.controls.split(",") if x]:
                c = T.get((ctl, ruler))
                if c is None:
                    continue
                for setname, dd, cc in (("all16", d, c),
                                        ("ge202204", d[d.ts >= CUT15], c[c.ts >= CUT15])):
                    dl = MR.delta(dd, cc, list(RULE) + list(EXTRA), "%s-%s" % (arm, ctl))
                    out["delta"]["%s|%s|%s|%s" % (arm, ctl, ruler, setname)] = {
                        "n_tick_common": dl["n_tick_common"],
                        "metrics": {m: _mk(v) for m, v in dl["metrics"].items()}}

    # ---- LUAT §6 ----
    print("\n### LUAT §6 (co ky nang tien = pacc>0.5 & ic>0 & dec_mono>0.5 & CA 3 ngoai CI vs CA HAI "
          "doi chung A45,V5)", flush=True)
    for ruler in [x for x in RULERS if x.startswith("money")]:
        for arm in NEWARMS:
            key = "%s|%s|all16" % (arm, ruler)
            s = out["summary"].get(key)
            if not s:
                continue
            base = {"pacc": s["metrics"]["pacc"]["mean"] > 0.5,
                    "ic": s["metrics"]["ic"]["mean"] > 0,
                    "dec_mono": s["metrics"]["dec_mono"]["mean"] > 0.5}
            dlt, dlt_h = {}, {}
            for ctl in ("A45", "V5"):
                dk = "%s|%s|%s|all16" % (arm, ctl, ruler)
                if dk in out["delta"]:
                    dlt[ctl] = {m: bool(out["delta"][dk]["metrics"].get(m, {}).get("strict")
                                        and out["delta"][dk]["metrics"].get(m, {}).get("dir") == 1)
                                for m in RULE}
                    dlt_h[ctl] = {m: bool(out["delta"][dk]["metrics"].get(m, {}).get("honest")
                                          and out["delta"][dk]["metrics"].get(m, {}).get("dir") == 1)
                                  for m in RULE}
            ok = all(base.values()) and len(dlt) == 2 and all(
                all(v.values()) for v in dlt.values())
            out["rule"][key] = {"truc": base, "ngoai_CI_vs_A45_V5": dlt,
                                "ngoai_CI_vs_A45_V5_honest_k2": dlt_h, "PASS": bool(ok)}
            print("  %-7s %-8s truc=%s | vs A45 %s | vs V5 %s => %s"
                  % (arm, ruler, base, dlt.get("A45"), dlt.get("V5"), "PASS" if ok else "NOT"), flush=True)

    json.dump(out, open(a.out, "w"), indent=1, default=str)
    print("\nJSON -> %s" % a.out, flush=True)

    # ---- bang gon ----
    print("\n### BANG (mean | 'o' = ngoai CI) — thước TIỀN / NHÃN")
    rows = []
    for key, s in sorted(out["summary"].items()):
        r = {"arm|ruler|set": key, "n_tick": s["n_tick"]}
        for m in ("ic", "pacc", "dec_mono", "dec_rho", "glift8", "netm8", "auc8", "lift8", "base"):
            v = s["metrics"].get(m)
            r[m] = ("%+.5f%s" % (v["mean"], "*" if v["strict"] else ("+" if v["honest"] else ""))
                    ) if v else "-"
        rows.append(r)
    print(pd.DataFrame(rows).to_string(index=False))


if __name__ == "__main__":
    main()
