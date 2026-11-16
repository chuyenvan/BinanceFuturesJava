#!/usr/bin/env python3
"""E2E_REPLAY_V12 ERRATA1 - THU TIEM LECH cho cac tieu chi moi cua bo cham (CHI fixture dev 10-30, sau run_all.sh).
Sua 1 diem tren BAN SAO trong RAM (hoac thu muc tam cho file REF), chay lai ham cham; ky vong FAIL.
  T1 X1: stopPrice jar dat cua 1 cum TRAIL + 3 tick                       (S-TS)  => X1 FAIL
  T2 X1: lenh dong TIME_STOP tre +1 phut                                   (S-TS)  => X1 FAIL
  T3 D1: leg DCA dau dich sang phut st (khong co dieu kien thi truong)      (S-DCA) => D1 FAIL
  T4 D1: REF market: bo co BIG_DOWN/isDcaAlt o 1 phut co leg DCA (giu phut) (S-DCA) => D1 FAIL (chi do dieu kien thi truong)
  T5 D1: REF market: p15 < MIN_MOMENTUM_15M o 1 phut co leg DCA             (S-DCA) => D1 FAIL (chi do cong p15)
  T6 S1/E: E_replay cua 1 leg x (1 + 2e-6)                                  (R0)    => S1 FAIL
argv: --runs DIR --ref DIR --fx DIR --env FILE
"""
import argparse
import copy
import csv
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
    print("%-52s %-22s %-8s %s" % ("tiem", "goc", "sau", "FAIL dung?"))
    for n, b, af, ok, note in res:
        print("%-52s %-22s %-8s %s %s" % (n, b, af, "OK" if ok else "KHONG", note))
    print("TONG: %d/%d tiem bi bat (FAIL)" % (sum(1 for z in res if z[3]), len(res)))


if __name__ == "__main__":
    main()
