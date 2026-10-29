#!/usr/bin/env python3
"""HO2026_NOTF cham (PREREG 96164b72 §6-§7). Buoc 1 'mtm': equity MTM phut = ham scorer A HO4 qua ecm_mtm_h (them cua so H1
= dinh nghia HO4_RESULT_A) cho 48 run (A0 goc + A1 nt-*). Buoc 2 'score': V4, D1-D5. Chi doc printDone/result.json."""
import json, os, sys
import numpy as np
import pandas as pd
W = "/home/ubuntu/claude_master/ho_tradfi_wk"
OUT = "/home/ubuntu/kaggle_sim/out/"
SEEDS = [42, 7, 13, 21, 99, 123, 777, 2024]
X = set(open(W + "/X_notf_v2.txt").read().split())
A0 = {"k24s": "ho4-k24-s-s%d", "k24b": "ho4-k24-b-s%d", "x14": "tsx-ho-x14-s%d"}
A1 = {"k24s": "nt-k24-s-s%d", "k24b": "nt-k24-b-s%d", "x14": "nt-x14-s%d"}
WINS = ("W9", "H1", "Q3")


def mtm():
    # Theo lenh MASTER: import gvz_mtm truoc khi cham (gvz_mtm chi monkeypatch reset_rule_score; duong cham HO4 la ho4_score_a)
    sys.path.insert(0, "/home/ubuntu/claude_master/gvz")
    import gvz_mtm  # noqa: F401
    sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
    import ecm_mtm_h as M
    M.WINS["H1"] = ("2026-01-01 00:00", "2026-07-01 00:00")
    tags = [v % s for d in (A0, A1) for v in d.values() for s in SEEDS]
    sys.argv = ["ecm_mtm_h", W + "/notf_mtm.json"] + tags
    M.main()


def legs(tag):
    d = pd.read_csv(OUT + tag + "/storage/printDone.csv", index_col=False, dtype=str)
    d = d[(d.start >= "20260101 00:00") & (d.start < "20261001 00:00")].copy()
    d["S"] = d.sym.str.strip() + "USDT"
    d["pnl"] = d.pnl.astype(float)
    d["win"] = np.where(d.start < "20260701", "H1", "Q3")
    d["key"] = d.S + "|" + d.start
    return d


def score():
    M = json.load(open(W + "/notf_mtm.json"))["runs"]
    out = {"V4": {}, "D1": {}, "D2": {}, "D3": {}, "D4": {}, "D5": {}, "table": {}}
    # V4: eqcheck + tai lap so goc
    ec = {t: r["eqcheck"] for t, r in M.items()}
    out["V4"]["eqcheck_all_ok"] = all(str(v.get("final_ok")) == "True" and v.get("upd_vs_result") is True for v in ec.values())
    out["V4"]["eqcheck_bad"] = [t for t, v in ec.items() if not (str(v.get("final_ok")) == "True" and v.get("upd_vs_result") is True)]
    out["V4"]["mtm_check"] = json.load(open(W + "/notf_mtm.json"))["mtm_check"]
    out["V4"]["eqcheck_sample"] = ec.get("nt-k24-s-s42")
    H = json.load(open("/home/ubuntu/claude_master/vz_e1_wt/docs/result/ho4/HO4_RESULT_A.json"))["metrics"]
    T = json.load(open("/home/ubuntu/claude_master/tsx/ho/ho_mtm.json"))["runs"]
    mism = []
    for s in SEEDS:
        for fee, c in (("s", "k24s"), ("b", "k24b")):
            for w in WINS:
                ref = H["k24|%s|%d|%s" % (fee, s, w)]
                me = M[A0[c] % s][w]
                for k in ("n", "sum_pnl", "roi", "maxdd"):
                    if abs(float(ref[k]) - float(me[k])) > 1e-6 * max(1, abs(float(ref[k]))):
                        mism.append((A0[c] % s, w, k, ref[k], me[k]))
        for w in ("W9", "Q3"):
            for k in ("n", "sum_pnl", "roi", "maxdd"):
                if abs(float(T["tsx-ho-x14-s%d" % s][w][k]) - float(M["tsx-ho-x14-s%d" % s][w][k])) > 1e-6 * max(1, abs(float(T["tsx-ho-x14-s%d" % s][w][k]))):
                    mism.append(("tsx-ho-x14-s%d" % s, w, k))
    out["V4"]["orig_reproduced"] = not mism
    out["V4"]["mismatch"] = mism[:10]
    # bang
    for c in A0:
        for w in WINS:
            for arm, D in (("A0", A0), ("A1", A1)):
                v = [M[D[c] % s][w] for s in SEEDS]
                out["table"]["%s|%s|%s" % (c, w, arm)] = dict(
                    sum_pnl=float(np.mean([x["sum_pnl"] for x in v])), n_pos=int(sum(x["sum_pnl"] > 0 for x in v)),
                    roi=float(np.mean([x["roi"] for x in v])), maxdd=float(np.mean([x["maxdd"] for x in v])),
                    n=float(np.mean([x["n"] for x in v])), roi_by_seed=[round(x["roi"], 3) for x in v], pnl_by_seed=[round(x["sum_pnl"], 1) for x in v])
            a, b = out["table"]["%s|%s|A0" % (c, w)], out["table"]["%s|%s|A1" % (c, w)]
            out["table"]["%s|%s|delta" % (c, w)] = dict(
                d_roi_pp=b["roi"] - a["roi"], d_maxdd_pp=b["maxdd"] - a["maxdd"], d_sum_pnl=b["sum_pnl"] - a["sum_pnl"],
                d_roi_by_seed=[round(y - x, 3) for x, y in zip(a["roi_by_seed"], b["roi_by_seed"])])
    # D1
    for w in WINS:
        for arm, D in (("A0", A0), ("A1", A1)):
            v = [M[D["k24s"] % s][w]["sum_pnl"] for s in SEEDS]
            out["D1"]["%s|%s" % (w, arm)] = dict(mean=float(np.mean(v)), n_pos=int(sum(x > 0 for x in v)), E0=bool(np.mean(v) > 0 and sum(x > 0 for x in v) >= 6))
    keep = all(out["D1"]["%s|A1" % w]["E0"] == out["D1"]["%s|A0" % w]["E0"] for w in ("W9", "H1"))
    out["D1"]["verdict"] = "HO4 vung voi TF" if keep else "DOI -> bao MASTER, so go-live lay A1"
    # D2 (luat tsx_ho_score y nguyen)
    for arm, D in (("A0", A0), ("A1", A1)):
        dp, dd, dr, defer = {}, {}, {}, {}
        for s in SEEDS:
            b, x = M[D["k24b"] % s]["W9"], M[D["x14"] % s]["W9"]
            dp[s], dd[s], dr[s] = x["sum_pnl"] - b["sum_pnl"], x["maxdd"] - b["maxdd"], x["roi"] - b["roi"]
            rp = (W + "/res/%s.json" % (D["x14"] % s)) if arm == "A1" else "/home/ubuntu/claude_master/tsx/ho/res_tsx-ho-x14-s%d.json" % s
            defer[s] = json.load(open(rp))["tsx"][3]
        mp, md = float(np.mean(list(dp.values()))), float(np.mean(list(dd.values())))
        n_ge0, n_gt0 = sum(v >= 0 for v in dp.values()), sum(v > 0 for v in dp.values())
        s5 = sum(v > 0 for v in defer.values()) >= 6
        if not s5:
            vd = "NON-INFORMATIVE"
        elif (mp < 0 and n_gt0 <= 3) or md < -2.0:
            vd = "REJECT"
        elif mp > 0 and n_ge0 >= 6 and md >= -1.0:
            vd = "CONFIRM"
        else:
            vd = "INCONCLUSIVE"
        d2rule = bool(mp > 0 and n_ge0 == 8 and md >= -1.0)
        out["D2"][arm] = dict(verdict_tsx_score=vd, prereg_D2_confirm=d2rule, mean_dPnL=mp, mean_dMaxDD=md, mean_dROI=float(np.mean(list(dr.values()))),
                              n_ge0=n_ge0, n_gt0=n_gt0, defer=defer, dPnL={s: round(v, 1) for s, v in dp.items()})
    # D3
    d3 = {c: dict(d_roi=out["table"]["%s|W9|delta" % c]["d_roi_pp"], d_dd=out["table"]["%s|W9|delta" % c]["d_maxdd_pp"]) for c in ("k24s", "x14")}
    out["D3"] = dict(vals=d3, immaterial=bool(all(abs(v["d_roi"]) <= 1.0 and abs(v["d_dd"]) <= 1.0 for v in d3.values())))
    out["D4"] = {c: {arm: out["table"]["%s|Q3|%s" % (c, arm)] for arm in ("A0", "A1")} for c in A0}
    # D5
    for c in A0:
        agg = {w: dict(tf_removed_n=0, tf_removed_pnl=0.0, repl_n=0, repl_pnl=0.0, lost_crypto_n=0, lost_crypto_pnl=0.0, common_n=0) for w in ("W9", "H1", "Q3")}
        per_seed = {}
        for s in SEEDS:
            a, b = legs(A0[c] % s), legs(A1[c] % s)
            assert not b.S.isin(X).any()
            ka, kb = set(a.key), set(b.key)
            ps = {}
            for w in ("W9", "H1", "Q3"):
                aw = a if w == "W9" else a[a.win == w]
                bw = b if w == "W9" else b[b.win == w]
                tf = aw[aw.S.isin(X)]
                rep = bw[~bw.key.isin(ka)]
                lost = aw[(~aw.S.isin(X)) & (~aw.key.isin(kb))]
                g = agg[w]
                g["tf_removed_n"] += len(tf); g["tf_removed_pnl"] += tf.pnl.sum()
                g["repl_n"] += len(rep); g["repl_pnl"] += rep.pnl.sum()
                g["lost_crypto_n"] += len(lost); g["lost_crypto_pnl"] += lost.pnl.sum()
                g["common_n"] += int(bw.key.isin(ka).sum())
                ps[w] = dict(tf=len(tf), tf_pnl=round(tf.pnl.sum(), 1), repl=len(rep), repl_pnl=round(rep.pnl.sum(), 1), lost=len(lost), lost_pnl=round(lost.pnl.sum(), 1))
            per_seed[s] = ps
        out["D5"][c] = dict(agg={w: {k: (round(v, 1) if isinstance(v, float) else v) for k, v in g.items()} for w, g in agg.items()}, per_seed=per_seed)
    json.dump(out, open(W + "/notf_score.json", "w"), indent=1, default=str)
    print(json.dumps({k: out[k] for k in ("V4", "D1", "D2", "D3")}, indent=1, default=str)[:6000])
    for c in A0:
        for w in WINS:
            a, b, d = (out["table"]["%s|%s|%s" % (c, w, x)] for x in ("A0", "A1", "delta"))
            print("%-5s %s A0 roi %.2f dd %.2f pnl %.0f (%d/8) | A1 roi %.2f dd %.2f pnl %.0f (%d/8) | dROI %+.2f dDD %+.2f" % (
                c, w, a["roi"], a["maxdd"], a["sum_pnl"], a["n_pos"], b["roi"], b["maxdd"], b["sum_pnl"], b["n_pos"], d["d_roi_pp"], d["d_maxdd_pp"]))
    print(json.dumps({c: out["D5"][c]["agg"] for c in A0}, indent=0))


if __name__ == "__main__":
    {"mtm": mtm, "score": score}[sys.argv[1]]()
