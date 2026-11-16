#!/usr/bin/env python3
"""E2E_REPLAY_V12 ERRATA1 - THU TIEM LECH cho cac tieu chi moi cua bo cham (CHI fixture dev 10-30, sau run_all.sh).
Sua 1 diem tren BAN SAO trong RAM (hoac thu muc tam cho file REF), chay lai ham cham; ky vong FAIL.
  T1 X1: stopPrice jar dat cua 1 cum TRAIL + 3 tick                       (S-TS)  => X1 FAIL
  T2 X1: lenh dong TIME_STOP tre +1 phut                                   (S-TS)  => X1 FAIL
  T3 D1: leg DCA dau dich sang phut st (khong co dieu kien thi truong)      (S-DCA) => D1 FAIL
  T4 D1: REF market: bo co BIG_DOWN/isDcaAlt o 1 phut co leg DCA (giu phut) (S-DCA) => D1 FAIL (chi do dieu kien thi truong)
  T5 D1: REF market: p15 < MIN_MOMENTUM_15M o 1 phut co leg DCA             (S-DCA) => D1 FAIL (chi do cong p15)
  T6 S1/E: E_replay cua 1 leg x (1 + 2e-6)                                  (R0)    => S1 FAIL
  [ERRATA2 E7] T7 X1: cum co nhan ARM_CUNG_NEN (REF-nhip): stopPrice jar +3 tick (S-TS) => X1 FAIL
  T8 X1: doi nhan - bo nhan REF-nhip cua cum co nhan (S-TS) => X1 FAIL;  T9: gan nhan cho 1 cum TRAIL khong nhan => X1 FAIL
  [ERRATA3] T10 S1 U sai nhat quan voi budget (R0); T11 S1 eq_at cache cu nhat quan (R0); T12 D1 S-DCA U sai nhat quan;
  [MASTER N14/N15] T18 eq_at lech moc gia tri dung => KHONG FAIL; T19 gia tri eq x(1+1e-5) => FAIL; T20 LEGACY-11-05
  nguon thieu so dong => FAIL; T21 doi chung co bang chung => chap nhan.
  T13-T16 E2 file nhan (ngoai tap / LEGACY thieu nguon / header sai / thieu file) bi tu choi; T17 E2 R-OLD khong E9 => FAIL.
  (E11a: tools/e2e/test_ref_e11a.py; khoa: tools/e2e/test_official_lock.sh)
argv: --runs DIR --ref DIR --fx DIR --env FILE
"""
import argparse
import copy
import csv
import json
import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import check_v12 as C  # noqa: E402
import ref_v12 as R  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--runs", required=True)
    ap.add_argument("--ref", required=True)
    ap.add_argument("--fx", required=True)
    ap.add_argument("--env", required=True)
    ap.add_argument("--old-checker", default="", help="check_v12.py cu (1302fd81) de minh hoa lo hong da va (cot checker_cu)")
    a = ap.parse_args()
    env = R.load_env(a.env)
    meta, _ = R.load_exinfo(a.fx + "/exinfo.json")
    fxo = C.FX(a.fx)
    rf = lambda n: os.path.join(a.ref, n)  # noqa: E731
    L = {n: C.lane(a.runs, n) for n in ("R0", "S-DCA", "S-TS")}
    res = []

    def rec(name, base, after, note=""):
        res.append((name, base, after, after == C.FAIL, note))

    # ---- T1 / T2 (S-TS)
    Ls = L["S-TS"]
    b1 = C.x1(Ls, rf("S-TS"), meta, fxo)
    base = b1[0] + ("" if b1[0] != C.NS else "(tam=%s)" % b1[1].get("danh_gia_tam"))
    rep, _ = C.clusters_replay(Ls, meta)
    tr = [c for c in rep if c["reason"] == "TRAIL"]
    if tr:
        c0 = tr[0]
        tick = float(meta[c0["symbol"]]["tick"])
        L2 = copy.deepcopy(Ls)
        for e in L2["events"]:
            if e["type"] == "TRAIL_STOP_PLACED" and ("cid=" + c0["exit_cid"]) in e["detail"]:
                e["value"] = repr(float(e["value"]) + 3 * tick)
        r = C.x1(L2, rf("S-TS"), meta, fxo)
        rec("T1 X1 stopPrice +3 tick (%s)" % c0["symbol"], base, r[0], "px_bad=%d" % len(r[1]["px_bad"]))
    ts = [c for c in rep if c["reason"] == "TIME_STOP"]
    if ts:
        c0 = ts[0]
        L2 = copy.deepcopy(Ls)
        for f in L2["fills"]:
            if f["cid"] == c0["exit_cid"]:
                f["ms"] = str(int(f["ms"]) + 60000)
        r = C.x1(L2, rf("S-TS"), meta, fxo)
        rec("T2 X1 TIME_STOP +1 phut (%s)" % c0["symbol"], base, r[0], "ok_phut=%s" % r[1]["ok_phut"])
    # ---- [ERRATA2 E7] T7..T9 (S-TS, cum co nhan ARM_CUNG_NEN do REF-nhip)
    lab = [r for r in b1[1].get("ARM_CUNG_NEN_bao_cao_rieng", [])]
    if lab:
        sym, b0 = lab[0]["cum"]
        c0 = next(c for c in rep if (c["symbol"], c["b0"]) == (sym, b0))
        tick = float(meta[sym]["tick"])
        L2 = copy.deepcopy(Ls)
        for e in L2["events"]:
            if e["type"] == "TRAIL_STOP_PLACED" and ("cid=" + c0["exit_cid"]) in e["detail"]:
                e["value"] = repr(float(e["value"]) + 3 * tick)
        r = C.x1(L2, rf("S-TS"), meta, fxo)
        rec("T7 X1 cum co nhan stopPrice +3 tick (%s)" % sym, base, r[0], "px_bad=%d" % len(r[1]["px_bad"]))
        for tag, newlab in (("T8 X1 REF-nhip bo nhan cum co nhan", "0"), ("T9 X1 REF-nhip gan nhan cum khong nhan", "1")):
            tmp = tempfile.mkdtemp(prefix="e2e3_inj_")
            shutil.copytree(rf("S-TS"), tmp + "/S-TS")
            pth = tmp + "/S-TS/ref_clusters.csv"
            rows = list(csv.DictReader(open(pth)))
            tgt = None
            for row in rows:
                if newlab == "0" and (row["symbol"], int(row["b0"])) == (sym, b0):
                    tgt = row
                elif newlab == "1" and tgt is None and row["nhip_label"] == "0" and row["reason"].startswith("TRAIL"):
                    tgt = row
            tgt["nhip_label"] = newlab
            with open(pth, "w") as fh:
                w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()), lineterminator="\n")
                w.writeheader()
                w.writerows(rows)
            r = C.x1(Ls, tmp + "/S-TS", meta, fxo)
            rec(tag + " (%s)" % tgt["symbol"], base, r[0], "nhan_lech=%d" % len(r[1]["nhan_lech(jar vs REF-nhip)"]))
            shutil.rmtree(tmp)
    else:
        rec("T7-T9 KHONG CO cum co nhan o S-TS", base, "-", "")
    # ---- T3..T5 (S-DCA)
    Ld = L["S-DCA"]
    Ed = C.e_rows(Ld, rf("S-DCA"), fxo)
    bd = C.d1_sdca(Ld, rf("S-DCA"), env, meta, Ed)[0]
    dl = [x for x in Ld["legs"] if x["level"] == "DCA_LEVEL1" and x["outcome"] == "SUBMITTED"]
    st = int(Ld["res"]["injections"]["sdca_st"])
    if dl:
        L2 = copy.deepcopy(Ld)
        x0 = next(x for x in L2["legs"] if x["cid"] == dl[0]["cid"])
        x0["decision_ts"] = str(st)
        r = C.d1_sdca(L2, rf("S-DCA"), env, meta, Ed)
        chk = C.dca_leg_checks(x0, C.ref_market(rf("S-DCA")), env, Ed, C.c3cap(Ld))
        rec("T3 D1 leg DCA dich sang phut st=%d" % st, bd, r[0], "dieu_kien_tt(leg)=%s" % chk["dieu_kien_tt"])
        for tag, col, val in (("T4 D1 REF bo co thi truong o phut leg", ("big_a1", "alt_a1"), "0"),
                              ("T5 D1 REF p15 < MIN_MOMENTUM o phut leg", ("p15",), "0.0")):
            tmp = tempfile.mkdtemp(prefix="e2e2_inj_")
            shutil.copytree(rf("S-DCA"), tmp + "/S-DCA")
            p = tmp + "/S-DCA/ref_market.csv"
            rows = list(csv.DictReader(open(p)))
            for row in rows:
                if int(row["b"]) == int(dl[0]["decision_ts"]):
                    for c in col:
                        row[c] = val
            with open(p, "w") as fh:
                w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()), lineterminator="\n")
                w.writeheader()
                w.writerows(rows)
            r = C.d1_sdca(Ld, tmp + "/S-DCA", env, meta, Ed)
            rec(tag + " b=%s" % dl[0]["decision_ts"], bd, r[0])
            shutil.rmtree(tmp)
    # ---- T6 (R0)
    L0 = L["R0"]
    E0 = C.e_rows(L0, rf("R0"), fxo)
    bs = C.s1(L0, env, meta, E0)[0]
    L2 = copy.deepcopy(L0)
    x0 = next(x for x in L2["legs"] if x["outcome"] == "SUBMITTED")
    x0["eq"] = repr(float(x0["eq"]) * (1 + 2e-6))
    r = C.s1(L2, env, meta, C.e_rows(L2, rf("R0"), fxo))
    rec("T6 S1/E E_replay x(1+2e-6) leg %s" % x0["cid"], bs, r[0], "E_bad=%d" % r[1]["E"]["n_bad(>1e-6)"])
    # ================= [ERRATA3 E9/E10/E11] tiem moi (vong 4) =================
    old = None
    if a.old_checker and os.path.isfile(a.old_checker):
        import importlib.util
        spec = importlib.util.spec_from_file_location("check_v12_old", a.old_checker)
        old = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(old)

    def oldres(fn):
        try:
            return fn()
        except Exception as e:  # noqa: BLE001
            return "loi:%s" % type(e).__name__
    # T10 S1: U sai NHAT QUAN (margin_before +300, budget + qty tinh lai theo U sai) (R0)
    subs = [x for x in L0["legs"] if x["outcome"] == "SUBMITTED"]
    tgt = subs[1]
    L2 = copy.deepcopy(L0)
    x0 = next(x for x in L2["legs"] if x["cid"] == tgt["cid"])
    mb = float(x0["margin_before"]) + 300.0
    capj = float(x0["capital"])
    li = int(x0["leg_idx"] or 0)
    nb = R.budget(R.params(env, capj, "on"), mb, li)
    x0["margin_before"], x0["budget"] = repr(mb), repr(float(nb))
    m = meta[x0["symbol"]]
    x0["qty"] = str(R.floor_to(float(nb) / float(x0["sizing_px"]), m["step"]))
    E2_ = C.e_rows(L2, rf("R0"), fxo)
    r = C.s1(L2, env, meta, E2_)
    o = oldres(lambda: old.s1(L2, env, meta, old.e_rows(L2, rf("R0"), fxo))[0]) if old else "-"
    rec("T10 S1 U sai nhat quan (mb+300, budget/qty theo U sai) %s" % x0["cid"], bs, r[0],
        "U_bad=%d checker_cu=%s" % (r[1]["U(E10)"]["n_bad(>1e-6)"], o))
    # T11 S1: eq_at jar = cache CU (-60 s), eq NHAT QUAN voi khop san tai thoi diem do (R0)
    fills0 = R.load_fills(L0["dir"] + "/fills.csv")
    fct0, flat0 = C.lane_fct_flat(L0, rf("R0"))
    mark0 = R.make_mark(fxo.raw_bar_fn(flat0), fct0)
    best = None
    for x in subs:
        at = int(x["eq_at"])
        e1_, e0_ = R.equity_at(fills0, at, mark0, C.c3cap(L0)), R.equity_at(fills0, at - 60000, mark0, C.c3cap(L0))
        if abs(e1_ - e0_) / e1_ > 1e-5:
            best = (x["cid"], at - 60000, e0_)
            break
    if best is None:
        x = subs[-1]
        best = (x["cid"], int(x["eq_at"]) - 60000, R.equity_at(fills0, int(x["eq_at"]) - 60000, mark0, C.c3cap(L0)))
    L2 = copy.deepcopy(L0)
    x0 = next(x for x in L2["legs"] if x["cid"] == best[0])
    x0["eq_at"], x0["eq"] = str(best[1]), repr(best[2])
    r = C.s1(L2, env, meta, C.e_rows(L2, rf("R0"), fxo))
    o = oldres(lambda: old.s1(L2, env, meta, old.e_rows(L2, rf("R0"), fxo))[0]) if old else "-"
    rec("T11 S1 eq_at cache cu -60 s, eq nhat quan %s" % best[0], bs, r[0], "E_bad=%d checker_cu=%s" % (r[1]["E"]["n_bad(>1e-6)"], o))
    # [MASTER N14] T18 S1: eq_at jar lech MOC (-1500 ms) nhung GIA TRI eq dung => KHONG FAIL, chi bao cao lech moc
    L2 = copy.deepcopy(L0)
    x0 = next(x for x in L2["legs"] if x["cid"] == subs[0]["cid"])
    x0["eq_at"] = str(int(x0["eq_at"]) - 1500)
    r = C.s1(L2, env, meta, C.e_rows(L2, rf("R0"), fxo))
    mo = r[1]["E"]["eq_at_lech_moc(BAO CAO, N14)"]
    res.append(("T18 S1 eq_at lech moc -1500 ms, gia tri dung %s" % x0["cid"], bs, r[0], r[0] == bs and r[0] != C.FAIL
                and mo["n_submit_lech_moc"] >= 1, "KY VONG KHONG FAIL; lech_moc n=%d max=%d ms" % (mo["n_submit_lech_moc"], mo["max_abs_lech_ms"])))
    # [MASTER N14] T19 S1: GIA TRI eq lech 1e-5 (moc dung) => FAIL
    L2 = copy.deepcopy(L0)
    x0 = next(x for x in L2["legs"] if x["cid"] == subs[0]["cid"])
    x0["eq"] = repr(float(x0["eq"]) * (1 + 1e-5))
    r = C.s1(L2, env, meta, C.e_rows(L2, rf("R0"), fxo))
    rec("T19 S1 gia tri eq x(1+1e-5) %s" % x0["cid"], bs, r[0], "E_bad=%d" % r[1]["E"]["n_bad(>1e-6)"])
    # T12 D1 S-DCA: leg DCA U sai nhat quan
    L2 = copy.deepcopy(Ld)
    x0 = next(x for x in L2["legs"] if x["cid"] == dl[0]["cid"])
    mb = float(x0["margin_before"]) + 300.0
    nb = R.budget(R.params(env, float(x0["capital"]), "on"), mb, int(x0["leg_idx"]))
    x0["margin_before"], x0["budget"] = repr(mb), repr(float(nb))
    r = C.d1_sdca(L2, rf("S-DCA"), env, meta, C.e_rows(L2, rf("S-DCA"), fxo))
    o = oldres(lambda: old.d1_sdca(L2, rf("S-DCA"), env, meta, old.e_rows(L2, rf("S-DCA"), fxo))[0]) if old else "-"
    rec("T12 D1 S-DCA leg DCA U sai nhat quan %s" % x0["cid"], bd, r[0], "checker_cu=%s" % o)
    # T13..T16 E2 nhan (labels_check)
    tmp = tempfile.mkdtemp(prefix="e2e4_lab_")
    ok0 = C.labels_check(os.path.join(os.path.dirname(os.path.abspath(__file__)), "labels_1105.csv"))
    for tag, body in (("T13 E2 nhan ngoai tap khai truoc", "symbol,label,nguon\nAIOUSDT,LEGACY-MOI,x\n"),
                      ("T14 E2 LEGACY-11-05 thieu nguon dong log", "symbol,label,nguon\nAIOUSDT,LEGACY-11-05,\n"),
                      ("T20 E2 LEGACY-11-05 nguon khong co so dong", "symbol,label,nguon\nAIOUSDT,LEGACY-11-05,pull242/x/full.log.gz\n"),
                      ("T15 E2 header sai (them nhan sau, khong cot nguon)", "symbol,label\nAIOUSDT,EXCHANGEINFO\n"),
                      ("T16 E2 file nhan khong ton tai", None)):
        pth = tmp + "/lab.csv"
        if os.path.exists(pth):
            os.remove(pth)
        if body is not None:
            open(pth, "w").write(body)
        ok, _, det = C.labels_check(pth)
        res.append((tag, "PASS" if ok0[0] else "FAIL", "FAIL" if not ok else "PASS", not ok, "; ".join(det["loi"])[:90]))
    # [MASTER N15] T21 doi chung: LEGACY-11-05 CO bang chung '<log>:<dong>' => file nhan duoc CHAP NHAN (ky vong KHONG tu choi)
    open(tmp + "/lab.csv", "w").write("symbol,label,nguon\nAIOUSDT,LEGACY-11-05,pull242/2026-11-05/logs/full.log@x.gz:12345\n")
    ok, _, det = C.labels_check(tmp + "/lab.csv")
    res.append(("T21 E2 doi chung LEGACY-11-05 co bang chung log:dong", "-", "PASS" if ok else "FAIL", ok, "; ".join(det["loi"])[:90]))
    # T17 E2: R-OLD khong chay voi C3_EXCLUDE_LEGACY_HELD=true (manifest gia START=11-05, KHONG du lieu 11-05)
    open(tmp + "/manifest.json", "w").write(json.dumps({"START": C.T1105}))
    Lo = C.lane(a.runs, "R-OLD")
    Lo2 = copy.deepcopy(Lo)
    if Lo2["res"] is not None:
        (Lo2["res"].setdefault("legacy_E9", {}))["jar_excludeLegacyHeld"] = False
    r = C.e2(Lo2, tmp, tmp + "/dry.csv", os.path.join(os.path.dirname(os.path.abspath(__file__)), "labels_1105.csv"))
    res.append(("T17 E2 R-OLD thieu C3_EXCLUDE_LEGACY_HELD=true", "-", r[0], r[0] == C.FAIL, r[1].get("loi", "")[:80]))
    shutil.rmtree(tmp)
    print("%-52s %-22s %-8s %s" % ("tiem", "goc", "sau", "FAIL dung?"))
    for n, b, af, ok, note in res:
        print("%-52s %-22s %-8s %s %s" % (n, b, af, "OK" if ok else "KHONG", note))
    print("TONG: %d/%d tiem DUNG ky vong (FAIL; rieng T18/T21 ky vong KHONG FAIL)" % (sum(1 for z in res if z[3]), len(res)))


if __name__ == "__main__":
    main()
