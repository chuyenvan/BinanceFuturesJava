#!/usr/bin/env python3
"""Tong hop 1 luot cham (vd D2 = 2026-10-22 + 2026-10-23) theo PREREG_PARITY_V11_WINDOW (481701b2) + ADDENDUM1
(fea9fb97): verdict tung ngay TINH TU SO (khong go tay) + tich luy cua so (gom D1 ADDENDUM1). Copy artefact nho vao
docs/result/parity_v11_<round>/<ngay>/. argv: round day1 [day2 ...]   (vd: d2 2026-10-22 2026-10-23)"""
import glob
import gzip
import json
import os
import shutil
import sys

import numpy as np
import pandas as pd

ROOT = os.path.expanduser("~/claude_master/parity_v11w")
REPO = os.path.expanduser("~/claude_master/vz_e1_wt")
rnd, days = sys.argv[1], sys.argv[2:]
OUT = REPO + "/docs/result/parity_v11_%s" % rnd
SMALL = ["coverage", "universe", "gate", "fund", "net", "s1", "gv_p2", "p3", "s1v", "tsx", "labels", "kprime", "live_only"]


def L(p):
    return json.load(open(p)) if os.path.exists(p) else None


def rq08_off(work):
    p = work + "/p2_pairs.csv.gz"
    if not os.path.exists(p):
        lo = glob.glob(work + "/live_only_*.json")
        if lo:   # Vision chua co: chi phia live
            x = json.load(open(lo[0]))["P2_live_side"]
            return {"ge09_live": x["n_rq_ge_09_live"], "ge09_off": None, "ge08_live": x["n_rq_ge_08_live"], "ge08_off": None,
                    "max_live": x["max_rq_live"], "max_off": None, "n_pairs": x["n_pairs"], "n_pass_live": x["n_pass_live"],
                    "note": "chi phia live (Vision ngay D chua co)"}
        return None
    x = pd.read_csv(p, usecols=["rl", "ro"])
    return {"ge09_live": int((x.rl >= 0.9).sum()), "ge09_off": int((x.ro >= 0.9).sum()),
            "ge08_live": int((x.rl >= 0.8).sum()), "ge08_off": int((x.ro >= 0.8).sum()),
            "max_live": float(x.rl.max()), "max_off": float(x.ro.max()), "n_pairs": int(len(x))}


def day_status(work, run, tag):
    J = lambda n: L("%s/%s_%s.json" % (work, n, tag))
    g, s1, gv, p3, tsx, kp, lo = J("gate"), J("s1"), J("gv_p2"), J("p3"), J("tsx"), J("kprime"), J("live_only")
    cg, cf = L(run + "/cmp_ctl_gate.json"), L(run + "/cmp_ctl_fund.json")
    KD = "KHONG DO DUOC"
    st = {}
    st["P1"] = (KD if g is None else ("DAT" if g["P1"]["PASS"] else "TRUOT"))
    p1m = g["P1m"] if g else (lo["P1m"] if lo else None)
    st["P1m"] = KD if p1m is None else ("DAT" if p1m["frac_le_1e-6"] == 1.0 else "XAM")
    st["S1_I"] = KD if s1 is None else ("DAT" if s1["S1_I"]["frac"] == 1.0 else "XAM")
    st["S1_m"] = KD if s1 is None else ("DAT" if s1["S1_m"]["frac_le_1e-6"] == 1.0 else "XAM")
    gvi = gv["GV_I"] if gv else (lo["GV_I"] if lo else None)
    st["GV_I"] = KD if gvi is None else ("DAT" if gvi["frac_le1e-6"] == 1.0 else "XAM")
    if gv is None:
        st["P2"] = KD
    else:
        p2 = gv["P2"]
        st["P2"] = ("TRUOT" if p2["n_flip_heavy"] > 0 else
                    ("DAT (yeu: 0 cap r/q>=0,9)" if p2["n_rq_ge_09_live"] + p2["n_rq_ge_09_off"] == 0 else "DAT"))
    gl = gv["GATE_LOG"] if gv else (lo["GATE_LOG"] if lo else None)
    st["GATE_LOG_n_pass"] = None if gl is None else "%d/%d" % (gl["n_match"], gl["n_minutes_join"])
    st["P3"] = (KD if p3 is None else (KD + " (thieu gio %s)" % p3["hours_missing_utc"] if p3["hours_missing_utc"] else
                                       ("DAT" if p3["n_rel_gt_1e-6"] == 0 else "TRUOT")))
    st["TSX"] = KD if tsx is None else tsx["flag_status"]
    if cg is None or cf is None:
        st["CTL"] = KD
    else:
        st["CTL"] = "DAT" if (cg["rows_bit_nonfund"] == 1.0 and cf["rows_tol_nonfund"] == 1.0) else "TRUOT (dung do)"
    st["K5_Kprime"] = None if kp is None else len(kp["K5_minutes"])
    core = [st[k] for k in ("P1", "P2", "P3", "TSX", "S1_I", "GV_I", "CTL")]
    if any(x.startswith("TRUOT") for x in core):
        tot = "TRUOT"
    elif any(x.startswith(KD) for x in core):
        tot = KD + " (mot phan)"
        if any(x.startswith("XAM") for x in core) or (st["K5_Kprime"] or 0) > 0:
            tot += " + XAM"
    elif any(x.startswith("XAM") for x in core) or st["K5_Kprime"] is None or st["K5_Kprime"] > 0:
        tot = "XAM"
    else:
        tot = "DAT"
    st["ket_luan"] = tot + " (so bo cho phan funding; phan quyet chinh thuc P1/P2-funding o luot M)"
    return st


res = {"round": rnd, "prereg": "481701b2 + ADDENDUM1 fea9fb97", "days": {}, "cumulative": {}}
os.makedirs(OUT, exist_ok=True)
for d in days:
    tag = d.replace("-", "")
    work, run = ROOT + "/d/%s/work" % d, ROOT + "/d/%s/runs" % d
    st = day_status(work, run, tag)
    res["days"][d] = {"status": st, "rq": rq08_off(work)}
    od = OUT + "/" + d
    os.makedirs(od, exist_ok=True)
    for n in SMALL:
        p = "%s/%s_%s.json" % (work, n, tag)
        if os.path.exists(p):
            shutil.copy(p, od)
    for p in [work + "/restarts.json", work + "/segs.json", work + "/kprime_groups.json", work + "/p3_q.csv",
              run + "/cmp_ctl_gate.json", run + "/cmp_ctl_fund.json", run + "/r0.json", run + "/harness_%s.json" % tag,
              run + "_drop/drop_runs.json"]:
        if os.path.exists(p):
            shutil.copy(p, od + "/" + os.path.basename(p))
# D1 (ADDENDUM1, chinh thuc) + nhan K' ap lai (chi nhan)
d1 = L(REPO + "/docs/result/parity_v11_d1/parity_v11_d1_add1.json")
kp1 = L(ROOT + "/regr_d1/work/kprime_d1.json")
rq1 = rq08_off(ROOT + "/regr_d1/work")
res["D1"] = {"status_official_add1": d1["status_sua"]["ket_luan_luot_D"] if d1 else None,
             "K5_Kprime_relabel_only": len(kp1["K5_minutes"]) if kp1 else None, "rq": rq1}
od = OUT + "/2026-10-21_relabel"
os.makedirs(od, exist_ok=True)
for p in (ROOT + "/regr_d1/work/kprime_d1.json", ROOT + "/regr_d1/work/kprime_groups.json",
          ROOT + "/regr_d1/work/regress_d1.json", ROOT + "/runs/d21_drop/drop_runs.json"):
    if os.path.exists(p):
        shutil.copy(p, od + "/" + os.path.basename(p))
# tich luy
allrq = [x for x in [rq1] + [res["days"][d]["rq"] for d in days] if x]
full = [x for x in allrq if x.get("ge09_off") is not None]
res["cumulative"]["P2_pairs_both_sides_measured"] = {k: int(sum(x[k] for x in full)) for k in
                                                     ("n_pairs", "ge09_live", "ge09_off", "ge08_live", "ge08_off")}
res["cumulative"]["P2_pairs_live_side_all_days"] = {k: int(sum(x[k] for x in allrq)) for k in ("n_pairs", "ge09_live", "ge08_live")}
res["cumulative"]["P2_max_rq"] = {"live": max(x["max_live"] for x in allrq), "off": max(x["max_off"] for x in full)}
res["cumulative"]["days_measured"] = ["2026-10-21"] + days
res["cumulative"]["verdicts"] = {"2026-10-21": res["D1"]["status_official_add1"], **{d: res["days"][d]["status"]["ket_luan"] for d in days}}
json.dump(res, open(OUT + "/parity_v11_%s.json" % rnd, "w"), indent=1, default=str)
print(json.dumps(res, indent=1, default=str))
