#!/usr/bin/env python3
"""PARITY_V12_DRY — verdict ngay (PREREG 3c7dae05 + ADD1..ADD7). Lop phu len day_report.day_status (logic v1.1, giu nguyen):
 - universe A1: khong co exchangeInfo PIT (§2.2) => phan phu thuoc universe = KHONG DO DUOC
 - ngay co restart/deploy JVM v_t_m (§5.2, ADD6 §2) => toi da XAM, KHONG SACH
 - kiem tap coin dang giu (ADD1): held trong top-K == bo_dang_giu [GATE-PRE] moi phut; lech => XAM
 - KPI/T-BOOK: truoc re-seed (khong co [GATE-SEED] nap seed) => "KHONG SO DUOC (ADD6)"
 - ngay sach §5 (kiem co hoc tu log cua so): restart, OI-GUARD, KLINE_STALE, FEAT-PIPE gap, MAPPER, LATCH, exinfo state;
   collectData chua keo => "CHUA DO" => sach = CHUA XAC DINH
 - nhom H (tu deploy) / nhom K (tu sau re-seed) theo ADD6 §3
argv: round day1 [day2 ...]  -> docs/result/parity_v12_<round>/parity_v12_<round>.json"""
import glob
import gzip
import json
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import day_report as DR  # noqa: E402  (ROOT = parity_v12w)
from pv_cfg import WINDOW_START, day_ms, DAYMS, cfg as PVCFG, jars as PVJARS  # noqa: E402
import gmicro  # noqa: E402

ROOT, REPO = DR.ROOT, DR.REPO
KD = "KHONG DO DUOC"
RANK = {"DAT": 0, "XAM": 1, "TRUOT": 2}


def worst(a, b):
    """gop nhan: TRUOT > XAM > DAT; KHONG DO DUOC giu kem."""
    return a if RANK.get(a.split()[0], 1) >= RANK.get(b.split()[0], 1) else b


def log_counts(live):
    p = live + "/log_window.gz"
    if not os.path.exists(p):
        return None
    keys = {"OI-GUARD": rb"\[OI-GUARD", "KLINE_STALE": rb"KLINE_STALE", 
            "MAPPER_local": rb"\[MAPPER\].*(CUC BO|UNKNOWN-)", "MAPPER_REFRESH": rb"\[MAPPER-REFRESH\]", "MAPPER_DUP": rb"\[MAPPER-DUP\]",
            "LATCH": rb"LATCH", "EXINFO_STALE": rb"\[UNIVERSE-A1\].*STALE", "GATE_SEED": rb"\[GATE-SEED\]",
            "FEAT_DUMP_budget": rb"(DU TICK|CHAM TRAN)", "MainClass": rb"MainClass:"}
    rx = {k: re.compile(v) for k, v in keys.items()}
    out = {k: 0 for k in keys}
    dup_sets = set()
    with gzip.open(p, "rb") as f:
        for ln in f:
            for k, r in rx.items():
                if r.search(ln):
                    out[k] += 1
                    if k == "MAPPER_DUP":
                        m = re.search(rb"\{[^}]*\}", ln)
                        dup_sets.add(m.group(0).decode(errors="ignore") if m else "?")
    out["MAPPER_DUP_sets"] = sorted(dup_sets)
    # [FEAT-PIPE] bo dem TICH LUY tu luc khoi dong => lay tang trong ngay theo doan (ticks giam = restart, bat dau lai tu 0)
    fp = re.compile(rb"\[FEAT-PIPE\] ticks=(\d+) partial=(\d+) md_null=\d+ gap_minutes=(\d+) catchup=\d+ no_snap=(\d+)")
    segs, prev = [], None
    with gzip.open(p, "rb") as f:
        for ln in f:
            m = fp.search(ln)
            if m:
                tk, bad = int(m.group(1)), int(m.group(2)) + int(m.group(3)) + int(m.group(4))
                if prev is None or tk < prev:
                    segs.append([bad, bad, prev is not None])   # doan moi sau restart: dem tu 0
                segs[-1][1] = bad
                prev = tk
    out["FEAT_PIPE_bad"] = int(sum((b - a) + (a if new else 0) for a, b, new in segs))
    return out


def v12_day(d):
    tag = d.replace("-", "")
    work, run, live = ROOT + "/d/%s/work" % d, ROOT + "/d/%s/runs" % d, ROOT + "/d/%s/live" % d
    st = DR.day_status(work, run, tag)
    J = lambda n: DR.L("%s/%s_%s.json" % (work, n, tag))
    uni, lo, gv, cov = J("universe"), J("live_only"), J("gv_p2"), J("coverage")
    rs = DR.L(work + "/restarts.json") or {}
    v = {"v11_status": st}
    # universe A1
    no_exinfo = uni is not None and uni.get("exinfo") is None
    v["universe_A1"] = (KD + " (khong co exchangeInfo PIT §2.2)") if no_exinfo else ("co" if uni else KD)
    # held check (ADD1)
    hc = (gv or lo or {}).get("held_check_V12")
    v["held_check"] = hc
    held_ok = hc is not None and hc["minutes_join"] > 0 and hc["minutes_eq"] == hc["minutes_join"]
    # restart / deploy
    d0 = day_ms(d)
    inday = rs.get("in_day") or []
    deploy_day = d0 <= WINDOW_START < d0 + DAYMS
    pc = PVCFG(d)                                   # [ADD11] jar cua ngay, ngay swap
    v["jar"], v["premarket_excl"], v["swap_day"] = pc["JAR"], pc["PREMARKET_EXCL"], pc["swap_day"]
    deploy_day = deploy_day or pc["swap_day"]       # ngay swap r4n->r4q = XAM (ADD11 §1)
    v["restart_in_day"] = inday
    v["deploy_day"] = deploy_day
    # log sach
    lc = log_counts(live)
    v["log_counts"] = lc
    reseed = bool(lc and lc["GATE_SEED"] > 0)
    v["KPI_TBOOK"] = "SO DUOC (sau re-seed)" if reseed else "KHONG SO DUOC (truoc re-seed, ADD6 §1)"
    clean = {"pull_complete": bool(cov and not cov.get("pull_incomplete")),
             "no_restart": not inday and not deploy_day,
             "no_oi_guard": bool(lc) and lc["OI-GUARD"] == 0,
             "no_kline_stale": bool(lc) and lc["KLINE_STALE"] == 0,
             "no_featpipe_bad": bool(lc) and lc["FEAT_PIPE_bad"] == 0,
             "mapper_ok": bool(lc) and lc["MAPPER_local"] == 0 and lc["MAPPER_REFRESH"] == 0
             and all(s.replace(" ", "") in ("{1=[BTCUSDT,XUSDT]}",) for s in lc["MAPPER_DUP_sets"]),
             "no_latch": bool(lc) and lc["LATCH"] == 0,
             "no_exinfo_stale": bool(lc) and lc["EXINFO_STALE"] == 0,
             "featdump_budget_ok": bool(lc) and lc["FEAT_DUMP_budget"] == 0,
             "collectData_restart_le2": (J("collect") or {}).get("collectData_restart_le2")}   # None = CHUA DO
    v["clean_checks"] = clean
    if any(x is False for x in clean.values()):
        v["ngay_sach"] = "KHONG SACH (%s)" % ",".join(k for k, x in clean.items() if x is False)
    elif any(x is None for x in clean.values()):
        v["ngay_sach"] = "CHUA XAC DINH (%s chua do)" % ",".join(k for k, x in clean.items() if x is None)
    else:
        v["ngay_sach"] = "SACH"
    v["collect"] = J("collect")
    r456 = DR.L(ROOT + "/r456.json") or {}
    v["R4_R6"] = {k: (r456.get(k) or {}).get("PASS") for k in ("R4", "R5", "R6")}
    # verdict
    tot = st["ket_luan"].split(" (so bo")[0]
    notes = []
    if no_exinfo and not tot.startswith("TRUOT"):
        tot = KD + " (mot phan)" + (" + XAM" if "XAM" in tot else "")
        notes.append("universe A1 khong do duoc")
    if (inday or deploy_day) and not tot.startswith("TRUOT"):
        if tot.startswith("DAT"):
            tot = "XAM"
        elif "XAM" not in tot:
            tot += " + XAM"
        notes.append("ngay restart/deploy => toi da XAM (§5.2, ADD6)")
    if hc is not None and not held_ok and not tot.startswith("TRUOT"):
        if tot.startswith("DAT"):
            tot = "XAM"
        notes.append("tap coin dang giu lech [GATE-PRE] => XAM (dieu tra)")
    if not all(v["R4_R6"].values()) and not tot.startswith("TRUOT"):
        notes.append("R4-R6 (§6) chua dat/chua chay %s => khong duoc DAT" % v["R4_R6"])
        if tot.startswith("DAT"):
            tot = "XAM"
    v["ket_luan"] = tot
    v["ghi_chu"] = notes
    v["nhom_H_tinh"] = (not deploy_day) and v["ngay_sach"].startswith("SACH")
    v["nhom_K_tinh"] = reseed and v["nhom_H_tinh"]
    v["SACH_ADD11"] = gmicro.is_sach(v)
    # [ADD12 §1] SACH-T: co hoc DAT + §5 SACH + khong lop phu V12; chi con funding so bo va/hoac TSX vision nan; K5 = 0
    mech = all(str(st.get(k, "")).startswith("DAT") for k in ("P1", "P1m", "S1_I", "S1_m", "GV_I", "P2", "P3", "CTL"))
    gl = str(st.get("GATE_LOG_n_pass") or "").split("/")
    gate_full = len(gl) == 2 and gl[0] == gl[1] and gl[0].isdigit() and int(gl[0]) > 0
    tsx_ok = str(st.get("TSX", "")).startswith("DAT") or str(st.get("TSX", "")).startswith(KD + " (vision=nan")
    k5_ok = (st.get("K5_official") or 0) == 0 and st.get("K5_official") is not None
    sT = {"co_hoc_DAT": mech, "gate_log_du": gate_full, "tsx_DAT_hoac_vision_nan": tsx_ok, "K5_bang_0": k5_ok,
          "ngay_sach_SACH": v["ngay_sach"] == "SACH", "pull_complete": not st.get("pull_incomplete"),
          "khong_lop_phu_V12": not notes, "khong_TRUOT": not tot.startswith("TRUOT")}
    v["SACH_T_checks"] = sT
    v["SACH_T"] = all(sT.values()) and not v["SACH_ADD11"]
    v["needs_M_regrade"] = v["SACH_ADD11"] or v["SACH_T"]
    return v, work, run


def main():
    rnd, days = sys.argv[1], sys.argv[2:]
    out = REPO + "/docs/result/parity_v12_%s" % rnd
    os.makedirs(out, exist_ok=True)
    res = {"round": rnd, "prereg": "PREREG_PARITY_V12_DRY 3c7dae05 + ADD1..ADD12", "window_start_ms": WINDOW_START, "days": {}}
    for d in days:
        v, work, run = v12_day(d)
        res["days"][d] = v
        od = out + "/" + d
        os.makedirs(od, exist_ok=True)
        for p in glob.glob(work + "/*_%s.json" % d.replace("-", "")) + [work + "/restarts.json", work + "/p3_q.csv"]:
            if os.path.exists(p):
                shutil.copy(p, od)
    json.dump(res, open(out + "/parity_v12_%s.json" % rnd, "w"), indent=1, default=str)
    # [ADD11 §4] G-MICRO tren moi ngay da cham (ban moi nhat moi ngay)
    sw = [j for j in PVJARS() if j["name"] != "r4n"]
    sm, sinfo = gmicro.smoke(ROOT, sw[0]["start_ms"]) if sw else (None, {"chua_swap": True})
    gm = gmicro.count(gmicro.collect(REPO), sm)
    gm["smoke_info"] = sinfo
    json.dump(gm, open(REPO + "/docs/result/parity_v12_gmicro.json", "w"), indent=1, default=str)
    print("G-MICRO:", gm["G_MICRO"], "sach=", gm["sach"])
    print(json.dumps({d: {k: x[k] for k in ("ket_luan", "ngay_sach", "KPI_TBOOK", "ghi_chu")} for d, x in res["days"].items()},
                     indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
