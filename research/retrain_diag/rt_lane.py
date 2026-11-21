#!/usr/bin/env python3
"""rt_lane.py - PREREG_RETRAIN_DIAG (436977c1) muc 2.1: du lieu lane chan doan U4a = TO HOP artefact da co (khong train / khong predict moi).
HOLDOUT_UNSEAL_2026_1121 (U4a). Lane P: pred = Lane N (p15 T1, ts>=S3) + bins Lane L; lane S: pred L + bins0701 = assign(S1 T1, RAW_L);
lane M: pred L + bins0701 = assign(S1 live cut20251231, RAW_N). bins 0101/0401 = Lane L (hard link, sha kiem).
Usage: build <P|S|M> | upload <P|S|M>"""
import hashlib, json, logging, os, sys
import numpy as np
sys.path.insert(0, "/home/ubuntu/claude_master/w3/retrain/work/a3n")
import rt_a3n as R  # noqa: E402  (ham assign/common/a1 - khong sua)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout, force=True)
L = logging.getLogger("rtlane")
L.info("HOLDOUT_UNSEAL_REF HOLDOUT_UNSEAL_2026_1121 (U4a) + OWNER_DECISION_PILOT_1121 c3a9f01b")
O = "/home/ubuntu/claude_master/w3/retrain/out/lane"
DSL = R.DSL
RAW_L = R.FXL + "/ho5-a3-chain26/out/net015/predict_wf_20260701.bin"
RAW_N = "/home/ubuntu/claude_master/w3/retrain/out/k/rt-chain-n26/out_raw/out/net015/predict_wf_20260701.bin"
S1_T1 = "/home/ubuntu/claude_master/w3/retrain/out/s1_t1/s1a2x1_cut20260701.json"
PRED_P = "/home/ubuntu/claude_master/w3/retrain/out/a3n/ds/pred_2026.bin"   # = pred Lane N (a574a2e9): L ts<S3 + p15 T1 ts>=S3
WANT = {"rawL_md5": None, "rawN_md5": "e72532c68d8425a74b7f3f7df9c8865f", "s1t1_sha": "8bb11092dc20db6b4e70aaac29d7aa6293bb272640912e9aea9f008f2316ac88",
        "predP_md5": "a574a2e9b9e3f561c4050b2ccb938bf5"}
DL = json.load(open(R.HO5A3 + "/data26/DATA26.json"))
BL = DL["bins26_sha"]


def per_tick_check(a, b, kind):
    """kind=multiset: moi tick cung multiset p0 (a vs b); kind=order: top-24 sym moi tick (theo p0 giam) trung nhau."""
    import pandas as pd
    A = pd.DataFrame({"ts": a["ts"].astype("i8"), "sym": a["sym"].astype("i8"), "p": a["p0"].astype("f8")})
    B = pd.DataFrame({"ts": b["ts"].astype("i8"), "sym": b["sym"].astype("i8"), "p": b["p0"].astype("f8")})
    if kind == "multiset":
        x = A.sort_values(["ts", "p"]).p.to_numpy(); y = B.sort_values(["ts", "p"]).p.to_numpy()
        return {"rows_eq": len(A) == len(B), "multiset_eq": bool(len(x) == len(y) and np.array_equal(x, y, equal_nan=True))}
    A = A[np.isfinite(A.p)].sort_values(["ts", "p", "sym"], ascending=[True, False, True]); A["r"] = A.groupby("ts").cumcount()
    B = B[np.isfinite(B.p)].sort_values(["ts", "p", "sym"], ascending=[True, False, True]); B["r"] = B.groupby("ts").cumcount()
    ta = A[A.r < 24].groupby("ts").sym.apply(frozenset); tb = B[B.r < 24].groupby("ts").sym.apply(frozenset)
    j = ta.to_frame("a").join(tb.to_frame("b"), how="outer")
    eq = (j.a == j.b)
    return {"ticks": int(len(j)), "top24_set_eq_frac": float(eq.mean())}


def build(lane):
    d = O + "/" + lane.lower() + "/ds"
    os.makedirs(d, exist_ok=True)
    rep = {"lane": lane, "mode": "build"}
    for c in ("20260101", "20260401") + (("20260701",) if lane == "P" else ()):
        dst = d + "/predict_wf_%s.bin" % c
        if not os.path.exists(dst):
            os.link(DSL + "/predict_wf_%s.bin" % c, dst)
    if lane == "P":
        assert R.h(PRED_P) == WANT["predP_md5"]
        if not os.path.exists(d + "/pred_2026.bin"):
            os.link(PRED_P, d + "/pred_2026.bin")
    else:
        if not os.path.exists(d + "/pred_2026.bin"):
            os.link(DSL + "/pred_2026.bin", d + "/pred_2026.bin")
        excl, m863 = R.common(); a1s = R.a1(m863)
        if lane == "S":
            raw, s1 = RAW_L, S1_T1
            assert R.h(S1_T1, "sha256") == WANT["s1t1_sha"]
        else:
            raw, s1 = RAW_N, R.S1OLD
            assert R.h(RAW_N) == WANT["rawN_md5"]
        rep["raw"] = raw; rep["raw_md5"] = R.h(raw); rep["s1"] = s1; rep["s1_sha256"] = R.h(s1, "sha256")
        rep["fold_20260701"] = R.assign(raw, s1, d + "/predict_wf_20260701.bin", excl, a1s)
        new = np.fromfile(d + "/predict_wf_20260701.bin", dtype=R.A.REC)
        if lane == "S":   # cung RAW_L voi Lane L -> multiset moi tick == bins Lane L 0701
            rep["gate_vs_L"] = per_tick_check(new, np.fromfile(DSL + "/predict_wf_20260701.bin", dtype=R.A.REC), "multiset")
            rep["gate_vs_N_order"] = per_tick_check(new, np.fromfile("/home/ubuntu/claude_master/w3/retrain/out/a3n/ds/predict_wf_20260701.bin", dtype=R.A.REC), "order")
        else:             # cung S1 live voi Lane L -> thu tu top-24 moi tick ~ Lane L; multiset == bins Lane N
            rep["gate_vs_L_order"] = per_tick_check(new, np.fromfile(DSL + "/predict_wf_20260701.bin", dtype=R.A.REC), "order")
            rep["gate_vs_N"] = per_tick_check(new, np.fromfile("/home/ubuntu/claude_master/w3/retrain/out/a3n/ds/predict_wf_20260701.bin", dtype=R.A.REC), "multiset")
    rep["pred_md5"] = R.h(d + "/pred_2026.bin")
    rep["bins26_sha"] = {f: R.h(d + "/" + f, "sha256") for f in sorted(os.listdir(d)) if f.startswith("predict_wf_")}
    rep["copy_eq_L"] = {f: rep["bins26_sha"][f] == BL[f] for f in rep["bins26_sha"]}
    json.dump({"pred26_md5": rep["pred_md5"], "bins26_sha": rep["bins26_sha"], "src": "rt_lane.py build " + lane}, open(O + "/DATA26_%s.json" % lane, "w"), indent=1)
    return rep


PAIR = {  # [P2 lane cap] pred / bins 0701 = artefact DA CO (hard link, sha kiem)
    "PS": ("P", "/home/ubuntu/claude_master/w3/retrain/out/lane/s/ds/predict_wf_20260701.bin", "aafc626627906fc609902555189bf4d1ce824a9bbda94071217931b1cc47e727"),
    "PM": ("P", "/home/ubuntu/claude_master/w3/retrain/out/lane/m/ds/predict_wf_20260701.bin", "ea20967bc3ca9028229f37181fb891ef6ec62d636144409f14b93636b3ac1f82"),
    "SM": ("L", "/home/ubuntu/claude_master/w3/retrain/out/a3n/ds/predict_wf_20260701.bin", "bb64cde34cfc38a809f4a3e5922273c8552f96218b9c9df0733df2c2d090446e")}


def build_pair(lane):
    d = O + "/" + lane.lower() + "/ds"
    os.makedirs(d, exist_ok=True)
    pr, b7, want = PAIR[lane]
    for c in ("20260101", "20260401"):
        if not os.path.exists(d + "/predict_wf_%s.bin" % c):
            os.link(DSL + "/predict_wf_%s.bin" % c, d + "/predict_wf_%s.bin" % c)
    if not os.path.exists(d + "/predict_wf_20260701.bin"):
        os.link(b7, d + "/predict_wf_20260701.bin")
    if not os.path.exists(d + "/pred_2026.bin"):
        os.link(PRED_P if pr == "P" else DSL + "/pred_2026.bin", d + "/pred_2026.bin")
    rep = {"lane": lane, "mode": "build", "pred_src": pr, "bins0701_src": b7}
    rep["pred_md5"] = R.h(d + "/pred_2026.bin")
    rep["bins26_sha"] = {f: R.h(d + "/" + f, "sha256") for f in sorted(os.listdir(d)) if f.startswith("predict_wf_")}
    rep["ok"] = (rep["bins26_sha"]["predict_wf_20260701.bin"] == want and rep["pred_md5"] == (WANT["predP_md5"] if pr == "P" else "64f66a15e0c6d7268da805e3df428760")
                 and all(rep["bins26_sha"][f] == BL[f] for f in ("predict_wf_20260101.bin", "predict_wf_20260401.bin")))
    assert rep["ok"], rep
    json.dump({"pred26_md5": rep["pred_md5"], "bins26_sha": rep["bins26_sha"], "src": "rt_lane.py build " + lane}, open(O + "/DATA26_%s.json" % lane, "w"), indent=1)
    return rep


def upload(lane):
    from kaggle.api.kaggle_api_extended import KaggleApi
    d = O + "/" + lane.lower() + "/ds"; slug = "rt-%s-data26" % lane.lower()
    json.dump({"title": slug, "id": "chuyendinh/" + slug, "licenses": [{"name": "CC0-1.0"}]}, open(d + "/dataset-metadata.json", "w"))
    a = KaggleApi(); a.authenticate()
    r = a.dataset_create_new(d, public=False, quiet=True, dir_mode="skip")
    return {"lane": lane, "mode": "upload", "slug": slug, "status": getattr(r, "status", None), "error": getattr(r, "error", None)}


if __name__ == "__main__":
    mode, lane = sys.argv[1], sys.argv[2].upper()
    assert lane in ("P", "S", "M", "PS", "PM", "SM")
    rep = (build_pair(lane) if lane in PAIR else build(lane)) if mode == "build" else upload(lane)
    os.makedirs(O, exist_ok=True)
    json.dump(rep, open(O + "/LANE_%s_%s.json" % (lane, mode), "w"), indent=1, default=str)
    L.info("LANE %s", json.dumps(rep, default=str))
