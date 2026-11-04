#!/usr/bin/env python3
"""ADDENDUM1 PARITY_V11_WINDOW D1: JSON may doc goc (ab5bbe44) vs sua; verdict tinh tu so (khong go tay).
Doc work/*.json (chay lai sau fix) + docs/result/parity_v11_d1/parity_v11_d1.json (goc)."""
import json
import os

W = os.path.expanduser("~/claude_master/parity_v11w")
OUT = os.path.expanduser("~/claude_master/vz_e1_wt/docs/result/parity_v11_d1")
J = lambda n: json.load(open(W + "/work/" + n))
orig = json.load(open(OUT + "/parity_v11_d1.json"))
gate, fund, net, s1, gv, p3, lab = (J("gate_d1.json"), J("fund_d1.json"), J("net_d1.json"), J("s1_d1.json"),
                                    J("gv_p2_d1.json"), J("p3_d1.json"), J("labels_d1.json"))
ctl_g = json.load(open(W + "/runs/d21/cmp_ctl_gate.json"))
ctl_f = json.load(open(W + "/runs/d21/cmp_ctl_fund.json"))

st = {}
st["P1"] = "DAT" if gate["P1"]["PASS"] else "TRUOT"
st["P1m"] = "DAT" if gate["P1m"]["frac_le_1e-6"] == 1.0 else "XAM"
st["S1_I"] = "DAT" if s1["S1_I"]["frac"] == 1.0 else "XAM"
st["S1_m"] = "DAT" if s1["S1_m"]["frac_le_1e-6"] == 1.0 else "XAM"
st["GV_I"] = "DAT" if gv["GV_I"]["frac_le1e-6"] == 1.0 else "XAM"
p2 = gv["P2"]
st["P2"] = ("TRUOT" if p2["n_flip_heavy"] > 0 else
            ("DAT (yeu: 0 cap r/q>=0,9 => chua thuc su duoc thu)" if p2["n_rq_ge_09_live"] + p2["n_rq_ge_09_off"] == 0
             else "DAT"))
st["GATE_LOG_n_pass"] = "%d/%d" % (gv["GATE_LOG"]["n_match"], gv["GATE_LOG"]["n_minutes_join"])
st["P3"] = ("KHONG DO DUOC (thieu gio %s)" % p3["hours_missing_utc"] if p3["hours_missing_utc"] else
            ("DAT" if p3["n_rel_gt_1e-6"] == 0 else "TRUOT"))
st["TSX"] = "DAT" if orig["TSX"]["flag_match"] else "TRUOT"
ctl_ok = (ctl_g["rows_bit_nonfund"] == 1.0) and (ctl_f["rows_tol_nonfund"] == 1.0)   # ty le (0..1), khong phai so dong
st["CTL"] = "DAT" if ctl_ok else "TRUOT (dung do)"
st["K5"] = len(lab["K5"])
core = [st["P1"], st["P2"], st["P3"], st["TSX"], st["S1_I"], st["GV_I"], st["CTL"]]
if any(x.startswith("TRUOT") for x in core):
    tot = "TRUOT"
elif any(x.startswith("KHONG DO DUOC") for x in core):
    tot = "KHONG DO DUOC (mot phan)"
elif any(x.startswith("XAM") for x in core) or st["K5"] > 0:
    tot = "XAM"
else:
    tot = "DAT"
st["ket_luan_luot_D"] = tot + " (so bo cho phan funding: phan quyet chinh thuc P1/P2-funding o luot M)"

o = orig
cmp = {
    "P1": {"goc": o["P1"], "sua": gate["P1"]},
    "P1F": {"goc": {k: o["P1F"][k] for k in ("ALL30", "n_bad_minutes")}, "sua": {k: gate["P1F"][k] for k in ("ALL30", "n_bad_minutes")}},
    "FUND": {"goc": {k: o["FUND"][k] for k in ("rows_join", "rows_ok_frac", "minutes", "minutes_all_ok")},
             "sua": {k: fund[k] for k in ("rows_join", "rows_ok_frac", "minutes", "minutes_all_ok")}},
    "NET": {"goc": {k: o["NET"][k] for k in ("rows", "net015_le1e-6", "minutes", "minutes_all_ok", "max_absdiff")},
            "sua": {k: net[k] for k in ("rows", "net015_le1e-6", "minutes", "minutes_all_ok", "max_absdiff")}},
    "S1_I": {"goc": o["S1I"]["frac"], "sua": s1["S1_I"]["frac"], "minutes_sua": s1["S1_I"]["minutes"]},
    "GV_I": {"goc": o["GV_I"], "sua": gv["GV_I"]}, "GV_O": {"goc": o["GV_O"], "sua": gv["GV_O"]},
    "P2": {"goc": {k: o["P2"][k] for k in ("n_pairs", "n_flip", "n_flip_heavy", "max_rq_live", "max_rq_off", "n_rq_ge_09_live")},
           "sua": {k: p2[k] for k in ("n_pairs", "n_minutes", "minutes_dropped", "q_src_minutes", "n_flip", "n_flip_heavy",
                                      "max_rq_live", "max_rq_off", "n_rq_ge_09_live", "n_rq_ge_09_off", "n_rq_ge_08_live")}},
    "GATE_LOG": {"goc": o["GATE_LOG"], "sua": gv["GATE_LOG"]},
    "P3": {"goc": o["P3"], "sua": {k: v for k, v in p3.items() if k != "pre_window_lines"}},
    "labels": {"goc": {"counts": o["labels"]["counts"], "K5": o["labels"]["K5"]},
               "sua": {k: lab[k] for k in ("n_bad_minutes", "counts", "K5", "bad_by_source", "universe_change_marks",
                                           "K3_cover_window")}},
}
res = {"addendum": "PARITY_V11_WINDOW_D1_ADDENDUM1", "prereg": "docs/prereg/PREREG_PARITY_V11_WINDOW.md (481701b2), KHONG doi",
       "result_goc": "ab5bbe44", "ly_do": ["OC1023 CRIT-1 map gio q", "OC1023 CRIT-2 nhan K3", "OC1023 MAJ-1 thieu log 10-22 00:00-07:05",
                                          "MIN match6, P2 offline dung q log", "phat hien them: 7 file psym 10-22 00:00-00:06 co san nhung khong giai ma",
                                          "phat hien them: [GATE] log map theo phut ghi log (lech 1 tick)",
                                          "phat hien them: nguon phut lech §5 thieu MD/P1/S1-V"],
       "status_sua": st, "status_goc": o["status"], "so_sanh": cmp,
       "CTL": o["CTL"], "TSX": o["TSX"]}
json.dump(res, open(OUT + "/parity_v11_d1_add1.json", "w"), indent=1, default=str)
print(json.dumps(st, indent=1))
