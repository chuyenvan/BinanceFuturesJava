#!/usr/bin/env python3
"""Tong hop JSON may doc cho docs/result/parity_v11_d1/ (PREREG_PARITY_V11_WINDOW luot D)."""
import json
import os

W = os.path.expanduser("~/claude_master/parity_v11w")
OUT = os.path.expanduser("~/claude_master/vz_e1_wt/docs/result/parity_v11_d1")


def L(n):
    p = W + "/work/" + n
    return json.load(open(p)) if os.path.exists(p) else None


gate, fund, net, s1, gv, p3, lab, s1v = (L("gate_d1.json"), L("fund_d1.json"), L("net_d1.json"),
                                        L("s1_d1.json"), L("gv_p2_d1.json"), L("p3_d1.json"),
                                        L("labels_d1.json"), L("s1v_d1.json"))
ctl_gate = json.load(open(W + "/runs/d21/cmp_ctl_gate.json"))
ctl_fund = json.load(open(W + "/runs/d21/cmp_ctl_fund.json"))
res = {
    "prereg": "docs/prereg/PREREG_PARITY_V11_WINDOW.md (commit 481701b2)",
    "round": "D (D+1, so bo cho phan funding)",
    "day_measured_utc": "2026-10-21",
    "window_ms": [1792543980000, 1792627140000],
    "window_local": "2026-10-21 07:54 -> 2026-10-22 06:59 (+07)",
    "vision": {"2026-10-21": "co (741/741 symbol)", "2026-10-22": "chua co (404 luc 11:16 +07)",
               "2026-10-23": "chua co (404)", "2026-10-20": "co (738/741; 3 symbol niem yet 10-21)"},
    "universe": {"U_D": 741, "nsym_live_dau_ngay": 738, "nsym_live_cuoi_ngay": 741,
                 "symbol_moi_trong_ngay": ["BACUSDT", "CEGUSDT", "IBKRUSDT"]},
    "R0": {"cases": 11, "fail": 0, "note": "chay lai 2026-10-23 11:19 +07; exit 97/98 dung ky vong"},
    "CTL": {"gate_bit_nonfund": ctl_gate["rows_bit_nonfund"], "gate_rows": ctl_gate["rows_both"],
            "gate_only_bt": ctl_gate["only_ref"],
            "fund_tol_nonfund": ctl_fund["rows_tol_nonfund"], "fund_bit_nonfund": ctl_fund["rows_bit_nonfund"],
            "fund_cols_bit_diff": ctl_fund["cols_diff_nonfund"], "fund_only_bt": ctl_fund["only_ref"]},
    "P1F": gate["P1F"], "P1": gate["P1"], "P1m": gate["P1m"], "MD": gate["MD"],
    "FUND": {k: fund[k] for k in ("rows_bt", "rows_live", "rows_join", "bt_rows_missing_in_live", "rows_ok_frac",
                                  "minutes", "minutes_all_ok", "feat_lt_1", "bad_minutes")},
    "NET": net, "S1I": s1["S1_I"], "S1m": s1["S1_m"], "S1I_abs_sel_vs_score_max": s1["S1_I_selectorScore_vs_score"],
    "S1V": s1v, "GV_I": gv["GV_I"], "GV_O": gv["GV_O"], "P2": gv["P2"], "GATE_LOG": gv["GATE_LOG"],
    "P3": {k: p3[k] for k in ("n_hours", "max_rel", "med_rel", "n_rel_gt_1e-6", "buffer", "mismatch")},
    "TSX": {"live_flag_day_20261021": "OFF dd=-0.137179 minN=1436",
            "vision_flag_day_20261021": "OFF dd=-0.13953180083235261 p=-0.06107377071055228 minN=1439",
            "flag_match": True,
            "sum_ew_20261021": {"live": 0.007904351255153473, "vision": 0.00790435470803256, "absdiff": 3.45e-09,
                                "n_min_live": 1440, "n_min_vision": 1440},
            "sum_ew_20261020": {"live": 0.02967805090968105, "vision": 0.029858709490450924,
                                "absdiff": 1.8066e-04, "n_min_live": 1440, "n_min_vision": 1439}},
    "labels": lab,
    "safety": {"write_242": "khong (chi ls/cat/tar/grep/awk/du/find qua ssh)",
               "aerospike_242": "khong (strace BT/NEW2: 0 connect toi 103.157.218.242, 0 AF_INET)",
               "binance_rest": "khong (chi data.binance.vision file tinh)"},
    "status": {
        "P1": "DAT", "P1m": "DAT", "S1_I": "DAT", "S1_m": "DAT", "GV_I": "DAT", "P2": "DAT (yeu: 0 cap r/q>=0,9)",
        "TSX": "DAT (co trung)", "CTL": "DAT (gate bit 100%; fund tol 100%)",
        "P3": "KHONG DAT (23/24 gio <=1e-6; 13:01 rel 4.33e-3)",
        "K5": len(lab["K5"]),
        "ket_luan_luot_D": "TRUOT P3 + XAM (K5=4) theo §5; cac tieu chi khac DAT"},
}
os.makedirs(OUT, exist_ok=True)
json.dump(res, open(OUT + "/parity_v11_d1.json", "w"), indent=1, default=str)
print(json.dumps(res["status"], indent=1))
