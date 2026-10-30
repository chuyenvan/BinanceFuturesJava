#!/usr/bin/env python3
"""Unit test guard PREREG_PARITY_V11_WINDOW §7 trong day_report.day_status.

PREREG §7: "Thieu file cua 1 ngay => ngay do = KHONG DO DUOC (ghi ro, khong coi la DAT)".
Truoc 2026-10-30, day_status() khong doc coverage_<tag>.json nen mot ngay pull242 INCOMPLETE
ma cac nguong do duoc deu DAT van duoc ghi DAT. Test nay khoa hanh vi:

  ca 1: INCOMPLETE + cac nguong DAT  -> "KHONG DO DUOC (mot phan) + XAM" (toi da XAM)
  ca 2: INCOMPLETE + P1 TRUOT        -> giu "TRUOT" (TRUOT xau hon XAM, khong bi nang len)
  ca 3: COMPLETE   + cac nguong DAT  -> "DAT" (khong regression)

Chay: python3 research/parity_v11/py/test_day_report_guard.py
"""
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import day_report as DR  # noqa: E402


def fixture(root, tag, p1_pass, incomplete):
    work, run = root + "/work", root + "/runs"
    os.makedirs(work, exist_ok=True)
    os.makedirs(run, exist_ok=True)
    J = lambda p, o: json.dump(o, open(p, "w"))

    J(work + "/coverage_%s.json" % tag, {"pull_incomplete": incomplete})
    J(work + "/gate_%s.json" % tag, {"P1": {"PASS": p1_pass}, "P1m": {"frac_le_1e-6": 1.0}})
    J(work + "/s1_%s.json" % tag, {"S1_I": {"frac": 1.0}, "S1_m": {"frac_le_1e-6": 1.0}})
    J(work + "/gv_p2_%s.json" % tag, {"GV_I": {"frac_le1e-6": 1.0},
                                      "P2": {"n_flip_heavy": 0, "n_rq_ge_09_live": 1, "n_rq_ge_09_off": 1},
                                      "GATE_LOG": {"n_match": 5, "n_minutes_join": 5}})
    J(work + "/p3_%s.json" % tag, {"n_rel_gt_1e-6": 0, "hours_missing_utc": []})
    J(work + "/tsx_%s.json" % tag, {"flag_status": "DAT"})
    J(work + "/kprime_%s.json" % tag, {"K5_minutes": []})
    J(run + "/cmp_ctl_gate.json", {"rows_bit_nonfund": 1.0})
    J(run + "/cmp_ctl_fund.json", {"rows_tol_nonfund": 1.0})
    return work, run


def run_case(name, p1_pass, incomplete, prefix, extra=None):
    with tempfile.TemporaryDirectory() as root:
        tag = "20261025"
        work, run = fixture(root, tag, p1_pass, incomplete)
        st = DR.day_status(work, run, tag)
        kl = st["ket_luan"]
        assert kl.startswith(prefix), "%s: ket_luan=%r khong bat dau bang %r" % (name, kl, prefix)
        assert st["pull_incomplete"] is incomplete, name
        if extra:
            extra(st)
        print("PASS %-38s -> %s" % (name, kl.split(" (")[0]))
        return st


if __name__ == "__main__":
    # ca 1: du lieu thieu, do duoc het -> toi da XAM, khong duoc DAT
    s1 = run_case("ca1 INCOMPLETE + DAT", True, True, "KHONG DO DUOC (mot phan) + XAM")
    assert s1.get("giam_do_truoc_guard") == "DAT", s1
    # ca 2: du lieu thieu nhung co TRUOT that -> giu TRUOT (xau hon XAM)
    run_case("ca2 INCOMPLETE + P1 TRUOT", False, True, "TRUOT")
    # ca 3: du lieu du -> DAT (khong regression)
    run_case("ca3 COMPLETE + DAT", True, False, "DAT")
    print("ALL 3 CASES PASS")
