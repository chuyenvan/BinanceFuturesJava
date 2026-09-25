#!/usr/bin/env python3
"""mr_pnl_score.py — chấm TRỰC TIẾP trên **PnL của LUẬT THOÁT** (PREREG_PNL_RULER).

Khác các vòng trước: `y` KHÔNG phải `retEnd_h` mà là **`gross` của chính luật thoát** (nhãn (b) đã build,
`label_b_pnl.parquet` — KHÔNG build lại). Dùng NGUYÊN `model_ruler.tick_metrics` / `summarize` / `delta` /
`ci_mean` (không viết lại chỉ số nào).

2 thước: `P32` (pool top-32 S1, chọn thật 32→8) · `P8` (pool top-8, `top-8` = cả tick ⇒ `glift8 ≡ 0`).
`yb = (y > 0)`. `glift8`/`gross8` bất biến với phí; `netm8(f) = gross8 − f` (bảng phí ở RESULT).

Chạy: python3 mr_pnl_score.py --out /tmp/mrpnp/pnl.json
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

LABEL = "/tmp/mrout/mrout/label_b_pnl.parquet"
MRBINS = "/tmp/mrbins"
CACHE = "/tmp/mrpnp/cache"
ARMS = ["MRA4", "MRB8", "MRB32"]
CONTROLS = ["45deploy", "A45", "V5", "V1"]
FEES = [0.0, 0.004, 0.008, 0.012]
LEG = 1.21                                     # width luat (nhu cac vong truoc) — KHONG noi
K3, K6 = 3.0, 6.0                              # inflate(k) sensitivity
M = ["ic", "pacc", "dec_mono", "dec_rho", "glift8", "gross8", "gross_all", "netbase",
     "base", "auc8", "auc8c", "lift8", "n8", "n_coin"]
RULE = ("ic", "pacc", "dec_mono")


def mk(v):
    """1 chi so -> dict mean + 4 co 'ngoai CI' (raw / 1.21 / inflate k=3 / k=6) + huong."""
    mu, raw = float(v["mean"]), [float(x) for x in v["raw"]]
    out = {"mean": round(mu, 6), "hi121": [round(mu + (raw[0] - mu) * LEG, 6),
                                           round(mu + (raw[1] - mu) * LEG, 6)]}
    for nm, k in (("raw", 1.0), ("k3", K3), ("k6", K6)):
        lo, hi = mu + (raw[0] - mu) * k, mu + (raw[1] - mu) * k
        out[nm] = bool(lo > 0 or hi < 0)
        out[nm + "_band"] = [round(lo, 6), round(hi, 6)]
    out["strict"] = bool(out["raw"] and out["k3"])      # LUAT: chat
    out["out_k6"] = bool(out["raw"] and out["k6"])
    out["dir"] = 1 if mu > 0 else -1
    out["n"] = int(v.get("n", 0))
    return out


def label_keys(K):
    """(keys sorted, y) cho pool top-K (rank < K). y = `gross` (KHONG dung cot `net`)."""
    d = pd.read_parquet(LABEL, columns=["ts", "symId", "rank", "gross"])
    if K:
        d = d[d["rank"] < K]
    key = (d.ts.to_numpy(np.int64) * 1024 + d.symId.to_numpy(np.int64))
    o = np.argsort(key, kind="stable")
    return key[o], d.gross.to_numpy(np.float64)[o]


def cache_path(arm, K, f):
    return os.path.join(CACHE, "%s_%s_%s.parquet" % (arm, K, f))


def frames(arm, bins_dir, K, folds, slot=0):
    LK, YV = label_keys(K)
    out = []
    for f in folds:
        bp = os.path.join(bins_dir, "predict_wf_%s.bin" % f)
        if not os.path.exists(bp):
            print("    [thieu bins] %s %s" % (arm, f), flush=True)
            continue
        cp = cache_path(arm, K, f)
        if os.path.exists(cp):
            out.append(pd.read_parquet(cp))
            continue
        arr = np.fromfile(bp, dtype=MR.BIN_DT)
        ts = arr["ts"].astype(np.int64)
        sy = arr["sym"].astype(np.int64)
        p = (arr["p"] if slot == 0 else arr["z"][:, slot - 1]).astype(np.float32).astype(np.float64)
        key = ts * 1024 + sy
        ip = np.clip(np.searchsorted(LK, key), 0, len(LK) - 1)
        hit = LK[ip] == key
        y = np.full(len(key), np.nan)
        y[hit] = YV[ip[hit]]
        m = hit & np.isfinite(p) & np.isfinite(y)
        ym = y[m]
        R, _ = MR.tick_metrics(ts[m], p[m], ym, (ym > 0).astype(np.float64))
        R["fold"] = f
        R.to_parquet(cp, index=False)
        print("    [calc] %-7s P%-2d %s: %d dong, %d tick" % (arm, K, f, int(m.sum()), len(R)),
              flush=True)
        del arr
        out.append(R)
    return pd.concat(out, ignore_index=True) if out else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--arms", default=",".join(ARMS))
    ap.add_argument("--bins-root", default=MRBINS)
    ap.add_argument("--out", default="/tmp/mrpnp/pnl.json")
    ap.add_argument("--folds", default="")
    a = ap.parse_args()
    os.makedirs(CACHE, exist_ok=True)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    folds = [x for x in a.folds.split(",") if x] or MR.FOLDS
    arms = [x for x in a.arms.split(",") if x]
    bins = {n: os.path.join(a.bins_root, n) for n in arms}
    for n in CONTROLS:
        bins[n] = MR.PATHS[n][0]
    for n in CONTROLS:
        if n not in arms:
            pass
    print("### ARMS %s + CTL %s | folds=%d" % (arms, CONTROLS, len(folds)), flush=True)

    T = {}
    for K in (32, 8):
        for arm, bd in bins.items():
            T[(arm, K)] = frames(arm, bd, K, folds)
        print("  P%d xong" % K, flush=True)

    res = {"label": LABEL, "fees": FEES, "FEES_NOTE": "netm8(f) = gross8 - f ; phi hoa von = gross8",
           "arms": list(bins), "controls": CONTROLS, "legend": {"strict": "ngoai CI 1.21",
           "k3": "ngoai CI inflate(k=3)", "k6": "ngoai CI inflate(k=6)"},
           "summary": {}, "delta": {}, "fee": {}, "rule": {}, "validity": {}}
    for (arm, K), d in T.items():
        if d is None or not len(d):
            print("  [N/A] %s P%d" % (arm, K), flush=True)
            continue
        s = MR.summarize(d, arm, M, MR.C.inflate(K3))
        tag = "%s|P%d" % (arm, K)
        res["summary"][tag] = {"n_tick": s["n_tick"], "n_coin": round(float(s["n_coin_mean"]), 2),
                               "metrics": {m: mk(v) for m, v in s["metrics"].items()}}
        # bang PHI (muc tuyet doi)
        g8 = float(d.gross8.mean())
        ga = float(d.gross_all.mean())
        pw = MR.ci_mean(d.gross8.to_numpy(), d.ts.to_numpy(), MR.C.inflate(K3))
        pwl = MR.ci_mean(d.gross_all.to_numpy(), d.ts.to_numpy(), MR.C.inflate(K3))
        res["fee"][tag] = {"gross8": g8, "gross8_raw95": [round(float(x), 6) for x in pw["raw"]],
                           "gross8_ci_1.21": [round(mk(pw)["hi121"][0], 6),
                                              round(mk(pw)["hi121"][1], 6)],
                           "gross_tick_raw95": [round(float(x), 6) for x in pwl["raw"]],
                           "gross_tick": ga, "break_even_fee_top8": g8,
                           "break_even_fee_tick": ga,
                           "net8": {("%.3f" % f): g8 - f for f in FEES},
                           "net_tick": {("%.3f" % f): ga - f for f in FEES}}
    for arm in arms:
        for ctl in CONTROLS:
            for K in (32, 8):
                A, B = T.get((arm, K)), T.get((ctl, K))
                if A is None or B is None:
                    continue
                dl = MR.delta(A, B, M, "%s-%s" % (arm, ctl))
                res["delta"]["%s|%s|P%d" % (arm, ctl, K)] = {
                    "n_tick_common": dl["n_tick_common"],
                    "metrics": {m: dict(mk(dict(mean=v["mean"], raw=v["raw"],
                                                infl=v["infl"], n=dl["n_tick_common"])),
                                        out_both=bool(v["out_both"]))
                                for m, v in dl["metrics"].items()}}
    # kiem hop le: A45-45deploy, V5-V1
    for a1, a2 in (("A45", "45deploy"), ("V5", "V1")):
        for K in (32, 8):
            A, B = T.get((a1, K)), T.get((a2, K))
            if A is None or B is None:
                continue
            dl = MR.delta(A, B, M, "%s-%s" % (a1, a2))
            res["validity"]["%s-%s|P%d" % (a1, a2, K)] = {
                "n_tick_common": dl["n_tick_common"],
                "metrics": {m: mk(dict(mean=v["mean"], raw=v["raw"], infl=v["infl"],
                                       n=dl["n_tick_common"])) for m, v in dl["metrics"].items()}}
    # LUAT §8
    for arm in arms:
        k = "%s|P32" % arm
        s = res["summary"].get(k)
        if not s:
            continue
        base = {m: bool(s["metrics"][m]["mean"] > (0.5 if m != "ic" else 0)) for m in RULE}
        rec = {"truc_3_chi_so": base, "vs": {}}
        for ctl in ("A45", "V5"):
            dk = "%s|%s|P32" % (arm, ctl)
            if dk in res["delta"]:
                rec["vs"][ctl] = {m: bool(res["delta"][dk]["metrics"][m]["strict"]
                                          and res["delta"][dk]["metrics"][m]["dir"] == 1)
                                  for m in RULE}
        g = s["metrics"]["glift8"]
        dg = {ctl: res["delta"].get("%s|%s|P32" % (arm, ctl), {}).get("metrics", {}).get("glift8")
              for ctl in ("A45", "V5")}
        f0 = 0.008
        fr_ = res["fee"][k]
        nm = mk({"mean": fr_["gross8"] - f0,
                 "raw": [x - f0 for x in fr_["gross8_raw95"]],
                 "infl": [x - f0 for x in fr_["gross8_ci_1.21"]], "n": 0})
        rec["kinh_te"] = {"glift8_mean": g["mean"], "glift8_strict": g["strict"],
                          "netm8_0.008": round(fr_["gross8"] - f0, 6),
                          "netm8_pos_strict": bool(nm["strict"] and nm["dir"] == 1),
                          "netm8_k3": bool(nm["k3"] and nm["dir"] == 1)}
        rec["LIFT_KINH_TE"] = bool(all(v is not None and v["strict"] and v["dir"] == 1
                                      for v in dg.values()) and len(dg) == 2)
        res["rule"][k] = rec

    json.dump(res, open(a.out, "w"), indent=1, default=str)
    print("\nJSON -> %s" % a.out, flush=True)

    # ---- bang gon ----
    rows = []
    for tag, s in sorted(res["summary"].items()):
        r = {"arm|thuoc": tag, "n_tick": s["n_tick"]}
        for m in ("ic", "pacc", "dec_mono", "dec_rho", "glift8", "auc8c"):
            v = s["metrics"][m]
            r[m] = "%+.5f%s" % (v["mean"], "*" if v["strict"] else ("+" if v["k3"] else ""))
        r["gross8"] = "%+.5f" % res["fee"][tag]["gross8"]
        r["gross_tick"] = "%+.5f" % res["fee"][tag]["gross_tick"]
        rows.append(r)
    print("\n### P32/P8 (gross8 = muc gross cua top-8; gross_tick = moc tick; * = ngoai CI 1.21)")
    print(pd.DataFrame(rows).to_string(index=False))

    print("\n### BANG PHI netm8(f) = gross8 - f  [%/luot]")
    fr = []
    for tag, s in sorted(res["fee"].items()):
        d = {"arm|thuoc": tag, "gross8(%)": round(100 * s["gross8"], 4),
             "BE_top8(%)": round(100 * s["break_even_fee_top8"], 4),
             "BE_tick(%)": round(100 * s["break_even_fee_tick"], 4)}
        for f in FEES:
            d["net@%.3f(%%/luot)" % f] = round(100 * s["net8"]["%.3f" % f], 4)
        fr.append(d)
    print(pd.DataFrame(fr).to_string(index=False))

    print("\n### Δ glift8/gross8 (ghep cap tick chung) — 'o' = ngoai CI 1.21")
    dr = []
    for tag, d in sorted(res["delta"].items()):
        if not tag.endswith("P32"):
            continue
        r = {"cap|P32": tag, "n_common": d["n_tick_common"]}
        for m in ("glift8", "gross8", "ic", "pacc", "dec_mono"):
            v = d["metrics"][m]
            r[m] = "%+.5f%s" % (v["mean"], "*" if v["strict"] else ("+" if v["k3"] else ""))
        dr.append(r)
    print(pd.DataFrame(dr).to_string(index=False))

    print("\n### KIEM HOP LE (Δ phai ~0, trong CI)")
    for tag, d in sorted(res["validity"].items()):
        print("  %-22s n=%d | %s" % (tag, d["n_tick_common"],
              " ".join("%s=%+.5f%s" % (m, d["metrics"][m]["mean"],
                                       "*" if d["metrics"][m]["strict"] else "")
                       for m in ("ic", "pacc", "dec_mono", "glift8"))))


if __name__ == "__main__":
    main()
