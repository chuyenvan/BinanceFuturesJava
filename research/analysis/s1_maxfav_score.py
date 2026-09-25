#!/usr/bin/env python3
"""s1_maxfav_score.py — CHẤM 2 THƯỚC cho PREREG_S1_MAXFAV (VIỆC 2).

Dùng NGUYÊN `model_ruler` (`tick_metrics`/`summarize`/`delta`/`ci_mean`) — KHÔNG viết lại chỉ số.
KHÔNG train, KHÔNG sim: chỉ đọc bins ĐÃ CÓ + nhãn `.pb` (cột `maxFav_*` có sẵn) — DEV only.

3 thước NHÃN: `g1lite` (hàm của `maxFav_72h`, như RESULT_H72) · `maxFav_72h` · `maxFav_4h`
2 thước TIỀN: `retEnd_72h` · `retEnd_4h` (gross; `netm8` tự trừ phí 0,008 trong `tick_metrics`)

Điểm lấy theo RULER (khai báo trước, PREREG_S1_MAXFAV §4):
  ruler `*72` : arm CÓ slot 3 (`MFC72`,`MFB72`) lấy slot 3; mọi arm khác (kể cả đối chứng) lấy slot 0
               ⇒ so sánh CROSS-HORIZON đúng như tiền lệ RESULT_H72 §5/RESULT_MONEY_RANKER §5.
  ruler `*4`  : tất cả lấy slot 0.

Chạy: python3 s1_maxfav_score.py --arms MFC72,MFB72,MFC4 --bins-root /home/ubuntu/mfout/mf \
        --k 3 --out docs/result/s1_maxfav_score.json
"""
import argparse
import json
import os
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, "/home/ubuntu/sel1m_code")
import model_ruler as MR                       # noqa: E402
import c3_rates as C                           # noqa: E402

LABELS = "/home/ubuntu/label_15m"
CACHE = "/tmp/mfs/cache"
TMP = "/tmp/mfs"
os.makedirs(CACHE, exist_ok=True)

HI_ARMS = {"MFC72", "MFB72"}          # arm co DIEM o slot 3 (72h)
LBLCOLS = ["retEnd_72h", "maxFav_72h", "retEnd_4h", "maxFav_4h"]
KEYCOL = "retEnd_72h"                 # tap dong = retEnd_72h notna (chuan vong nay; ghep cap)

# ruler -> (h, cot y, cot yb, phep so, nguong yb, dung slot 3?)
RULERS = {
    "g1lite72":  ("72h", "g1lite",      "g1lite",      ">",  0.015, True),
    "lab72":     ("72h", "maxFav_72h",  "maxFav_72h",  ">=", 0.070, True),
    "money72":   ("72h", "retEnd_72h",  "retEnd_72h",  ">",  0.015, True),
    "lab4":      ("4h",  "maxFav_4h",   "maxFav_4h",   ">=", 0.070, False),
    "money4":    ("4h",  "retEnd_4h",   "retEnd_4h",   ">",  0.015, False),
}
NHAN_RULERS = ("g1lite72", "lab72", "lab4")
TIEN_RULERS = ("money72", "money4")
METRICS = ["ic", "pacc", "dec_mono", "dec_rho", "glift8", "netm8",
           "auc8", "auc8c", "lift8", "base"]
RULE = ("ic", "pacc", "dec_mono")
ECON = ("glift8", "netm8")
LEG = 1.21                              # do rong legacy (so cuc bo)
CUT224 = int(pd.Timestamp("2022-04-01", tz="UTC").value // 10**6) - 7 * 3600000


def mk(v, infl):
    """1 chi so -> mean + co 'ngoai CI' (raw / honest(k) / legacy 1.21) + huong."""
    mu = float(v["mean"]); raw = [float(x) for x in v["raw"]]
    ah = [mu + (raw[0] - mu) * infl, mu + (raw[1] - mu) * infl]
    al = [mu + (raw[0] - mu) * LEG, mu + (raw[1] - mu) * LEG]
    o_raw = bool(raw[0] > 0 or raw[1] < 0)
    o_hn = bool(ah[0] > 0 or ah[1] < 0)
    o_lg = bool(al[0] > 0 or al[1] < 0)
    return {"mean": round(mu, 6), "raw": o_raw, "honest": bool(o_raw and o_hn),
            "legacy121": bool(o_raw and o_lg), "dir": (1 if mu > 0 else -1),
            "ci_raw": [round(raw[0], 6), round(raw[1], 6)],
            "ci_honest": [round(ah[0], 6), round(ah[1], 6)]}


def load_all_labels():
    LK, LV = MR.load_labels(LABELS, LBLCOLS, key_col=KEYCOL)
    mf, re_ = LV["maxFav_72h"], LV["retEnd_72h"]
    LV["g1lite"] = np.where(mf >= 0.05, mf - np.minimum(0.5 * mf, 0.08), re_)
    return LK, LV


def ruler_frames(bins, arm, rul, LK, LV, folds):
    """Per-tick metrics cua 1 arm tren 1 ruler (streaming theo fold).

    Slot: ruler 72h -> arm thuoc HI_ARMS lay slot 3 (diem cua chinh horizon do); moi arm khac
    (doi chung + arm 4h) lay slot 0 => CROSS-HORIZON, khai bao truoc (PREREG_S1_MAXFAV §4).
    """
    h, ycol, ybcol, ybop, ybthr, hi = RULERS[rul]
    slot = 3 if (hi and arm in HI_ARMS) else 0
    parts = []
    for f in folds:
        bp = os.path.join(bins, "predict_wf_%s.bin" % f)
        if not os.path.exists(bp):
            continue
        arr = np.fromfile(bp, dtype=MR.BIN_DT)
        ts = arr["ts"].astype(np.int64); sy = arr["sym"].astype(np.int64)
        p = (arr["p"] if slot == 0 else arr["z"][:, slot - 1]).astype(np.float32).astype(np.float64)
        if not np.isfinite(p).any():
            del arr
            print("  [N/A]   %-8s %-9s fold %s: slot %d TOAN NaN" % (
                os.path.basename(bins), rul, f, slot), flush=True)
            return None
        key = ts * 1024 + sy
        ip = np.clip(np.searchsorted(LK, key), 0, len(LK) - 1)
        hit = LK[ip] == key

        def _take(col):
            v = np.full(len(key), np.nan)
            v[hit] = LV[col][ip[hit]]
            return v
        y = _take(ycol); raw = _take(ybcol)
        yb = np.where(raw >= ybthr if ybop == ">=" else raw > ybthr, 1.0, 0.0)
        m = np.isfinite(y) & np.isfinite(p) & np.isfinite(raw)
        tm, _ = MR.tick_metrics(ts[m], p[m], y[m], yb[m])
        tm["fold"] = f
        parts.append(tm)
        del arr, p, key
    if not parts:
        return None
    return pd.concat(parts, ignore_index=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", required=True)
    ap.add_argument("--bins-root", default="/home/ubuntu/mfout/mf")
    ap.add_argument("--controls", default="45deploy,A45,V5,V1")
    ap.add_argument("--rulers", default="g1lite72,lab72,money72,lab4,money4")
    ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--folds", default="", help="danh sach fold ngan cach dau phay (mac dinh = 16 fold)")
    ap.add_argument("--out", default=os.path.join(TMP, "s1_maxfav_score.json"))
    a = ap.parse_args()

    infl = C.inflate(a.k)
    print("### k=%d honest inflate=%.6f | block=%dh nrep=%d seed=%d | LEG=%.2f" % (
        a.k, infl, C.BLOCK_H, C.NREP, C.SEED, LEG), flush=True)

    bins_of = {}
    for n in [x for x in a.controls.split(",") if x]:
        bins_of[n] = dict(MR.PATHS)[n][0] if n in dict(MR.PATHS) else None
    NEW = [x for x in a.arms.split(",") if x]
    for n in NEW:
        bins_of[n] = os.path.join(a.bins_root, n)
    for n, bd in bins_of.items():
        print("### ARM %-8s bins=%s exists=%s" % (n, bd, bool(bd and os.path.exists(
            os.path.join(bd, "predict_wf_20220101.bin")))), flush=True)

    LK, LV = load_all_labels()
    folds = ([x for x in a.folds.split(",") if x] if a.folds else MR.FOLDS)

    T = {}
    for rul in [x for x in a.rulers.split(",") if x]:
        for arm, bd in bins_of.items():
            if bd is None:
                continue
            if rul.startswith(("g1lite", "lab7", "money7")) and arm not in HI_ARMS:
                pass          # cross-horizon: doi chung/arm 4h -> slot 0 (khai bao §4)
            cp = os.path.join(CACHE, "%s_%s_k%d_%d.parquet" % (arm, rul, a.k, len(folds)))
            if os.path.exists(cp):
                T[(arm, rul)] = pd.read_parquet(cp)
                continue
            print("  [calc]  %-8s %-9s ..." % (arm, rul), end="", flush=True)
            d = ruler_frames(bd, arm, rul, LK, LV, folds)
            if d is None:
                T[(arm, rul)] = None
                print(" N/A", flush=True)
                continue
            d.to_parquet(cp, index=False)
            T[(arm, rul)] = d
            print(" n_tick=%d coin/tick=%.1f" % (len(d), d.n_coin.mean()), flush=True)

    out = {"k": a.k, "inflate_honest": infl, "arms": list(bins_of), "rulers": list(RULERS),
           "hi_arms": sorted(HI_ARMS), "summary": {}, "delta": {}, "rule": {}}
    for (arm, rul), d in T.items():
        if d is None:
            continue
        for setname, sub in (("all16", d), ("ge202204", d[d.ts >= CUT224])):
            s = MR.summarize(sub, arm, METRICS, 1.0)
            out["summary"]["%s|%s|%s" % (arm, rul, setname)] = {
                "n_tick": s["n_tick"], "n_coin": round(s["n_coin_mean"], 2),
                "metrics": {m: mk(v, infl) for m, v in s["metrics"].items()}}

    for rul in [x for x in a.rulers.split(",") if x]:
        for arm in NEW:
            d = T.get((arm, rul))
            if d is None:
                continue
            for ctl in [x for x in a.controls.split(",") if x]:
                c = T.get((ctl, rul))
                if c is None:
                    continue
                for setname, dd, cc in (("all16", d, c), ("ge202204", d[d.ts >= CUT224],
                                                           c[c.ts >= CUT224])):
                    dl = MR.delta(dd, cc, METRICS, "%s-%s" % (arm, ctl))
                    out["delta"]["%s|%s|%s|%s" % (arm, ctl, rul, setname)] = {
                        "n_tick_common": dl["n_tick_common"],
                        "metrics": {m: mk(v, infl) for m, v in dl["metrics"].items()}}
    # kiem HOP LE cua thuoc: A45-45deploy (buoc retrain) va V5-V1 (buoc nhieu)
    for rul in [x for x in a.rulers.split(",") if x]:
        for pair in (("A45", "45deploy"), ("V5", "V1")):
            x, y = T.get((pair[0], rul)), T.get((pair[1], rul))
            if x is None or y is None:
                continue
            dl = MR.delta(x, y, METRICS, "%s-%s" % pair)
            out["delta"]["%s|%s|%s|all16" % (pair[0], pair[1], rul)] = {
                "n_tick_common": dl["n_tick_common"],
                "metrics": {m: mk(v, infl) for m, v in dl["metrics"].items()}}

    # ---- LUAT PREREG_S1_MAXFAV §5 ----
    for rul in [x for x in a.rulers.split(",") if x]:
        for arm in NEW:
            if T.get((arm, rul)) is None:
                continue
            troc = {}
            for ctl in ("A45", "V5"):
                dk = "%s|%s|%s|all16" % (arm, ctl, rul)
                if dk not in out["delta"]:
                    continue
                troc[ctl] = {m: bool(out["delta"][dk]["metrics"][m]["honest"]
                                     and out["delta"][dk]["metrics"][m]["dir"] == 1)
                             for m in RULE + ECON if m in out["delta"][dk]["metrics"]}
            st = out["summary"].get("%s|%s|all16" % (arm, rul), {})
            netm8 = st.get("metrics", {}).get("netm8", {}).get("mean")
            if rul in NHAN_RULERS:
                ok = len(troc) == 2 and all(all(v.get(m, False) for m in RULE)
                                            for v in troc.values())
                out["rule"]["%s|%s|A" % (arm, rul)] = {"troc": troc, "netm8": netm8, "PASS": bool(ok)}
            else:
                ok = (len(troc) == 2 and all(all(v.get(m, False) for m in ECON)
                                             for v in troc.values())
                      and netm8 is not None and netm8 > 0)
                out["rule"]["%s|%s|B" % (arm, rul)] = {"troc": troc, "netm8": netm8, "PASS": bool(ok)}

    json.dump(out, open(a.out, "w"), indent=1, default=str)
    print("\n### JSON -> %s" % a.out, flush=True)

    print("\n### BANG (mean | * = ngoai CA HAI do rong raw+honest(k=%d))" % a.k)
    for rul in [x for x in a.rulers.split(",") if x]:
        print("  -- ruler %s --" % rul)
        for arm in list(bins_of):
            st = out["summary"].get("%s|%s|all16" % (arm, rul))
            if not st:
                continue
            cells = []
            for m in ("ic", "pacc", "dec_mono", "glift8", "netm8"):
                v = st["metrics"].get(m)
                cells.append("%s=%s" % (m, "-" if v is None else
                                        ("%+.4f%s" % (v["mean"], "*" if v["honest"] else
                                                      ("+" if v["legacy121"] else "")))))
            print("    %-8s n_tick=%-5d %s" % (arm, st["n_tick"], " ".join(cells)))
    print("\n### LUAT")
    for kk, vv in sorted(out["rule"].items()):
        print("  %-24s PASS=%s netm8=%s" % (kk, vv["PASS"], vv["netm8"]))


if __name__ == "__main__":
    main()
