#!/usr/bin/env python3
"""FEAT_ADD_V1 — cham 2 arm (B0 = G2+FLAT3, V1 = G2+FLAT3 + bins V1) theo docs/prereg/PREREG_FEAT_ADD_V1.md
(md5 9ce3d65868c053ceaa564c184e6245ff, chot TRUOC). §9 k=1 => inflate 1.0.

THUAN PYTHON OFFLINE (KHONG Java/sim). DEV <= 2025-12-30. Tai dung reset_rule_score (load_legs/load_daily/
core_metrics/run_mtm) + boot_pair (episode) cua reset_rule_gdv2_p3, cung khuon trail2_g2_driver.py.

CUA SO SO SANH = 2022-01-01..2025-12-30 (bins V1 chi phu 2022+; 2 fold 2021H2 cua V1 = bins MOC => 2021H2 giong het
giua 2 arm, equity tai 2021-12-31 bang nhau -> cua so 2022+ la so sanh sach). Chi tiet thi hanh (KHONG doi thiet ke):
 * CAGR/quy/nam/qmin: tren equity ngay tu 2021-12-31 (co so) .. 2025-12-30.
 * maxDD/UW MTM phut: chuoi phut chay tu 2021-07-01 (positions 2021 mo dang do dang), DD/UW cua cua so RESET dinh
   tai dau ngay 2022-01-01 UTC (state.win). dd_year = nam UTC 2022..2025.
 * Bootstrap: chi lenh vao >= 2022-01-01; CAP0 = equity tai 2021-12-31; NREP 2000 seed 20260905; INFL = 1.0.
 * Verdict "thang" (chot TRUOC khi xem so): can T1 dat & (Cal_V1 > Cal_B0 hoac (n_w cao hon & Cal_V1 >= 0.90 Cal_B0))
   & CI ΔCalmar_MTM block-72h VA episode DEU co can duoi > 0 (doc chat "block-72h + episode").
Cong: B0 printDone md5 = 650c386f..., n 2517, eq 131908 (sai => DUNG).
"""
import argparse
import json
import logging
import math
import os
import subprocess
import sys

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import reset_rule_score as R  # noqa: E402
import reset_rule_gdv2_p3 as P  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("featv1score")

WIN0 = pd.Timestamp("2022-01-01")
PRE = pd.Timestamp("2021-12-31")
TAGS = {"B0": "featv1-b0", "V1": "featv1-v1"}
REFS = {"OLD_MOC": "featv1-ref-s3moc", "OLD_V1": "featv1-ref-s3v1"}   # nen KEEPLEG0 cu (S3), dung layout symlink
PARITY_MD5, PARITY_N, PARITY_EQ = "650c386f0d0dfea334af9d55ca2f21d4", 2517, 131908
NREP, SEED = 2000, 20260905
INFL = 1.0
CALMAR_MULT = 0.90
YEARS = [2022, 2023, 2024, 2025]
REPO = "/home/ubuntu/src/BinanceFuturesJava"
MASTER = "/home/ubuntu/claude_master/0929"


class MTMStateW(R.MTMState):
    """MTMState + state cua so RESET tai 2022-01-01 UTC."""

    def __init__(self):
        super().__init__()
        self.win = {c: [-np.inf, 0.0, 0, 0] for c in R.MTM_COSTS}

    def feed(self, m_global, eq):
        super().feed(m_global, eq)
        day = (pd.Timestamp(R.DAY0) + pd.Timedelta(minutes=int(m_global))).normalize()
        if day >= WIN0:
            for c in R.MTM_COSTS:
                MTMStateW._consume(np.asarray(eq[c], float), self.win[c])


_orig_res = R._mtm_result


def _res_w(st):
    out = _orig_res(st)
    for c in R.MTM_COSTS:
        out[c]["dd_win"] = float(st.win[c][1])
        out[c]["uw_win_days"] = float(st.win[c][3] / 1440.0)
    return out


R.MTMState = MTMStateW
R._mtm_result = _res_w


def block_boot(dr, db, cap0, nrep=NREP, seed=SEED):
    """PAIRED block-72h (luoi khoi CHUNG blk2, theo ts vao lenh, pnl dong) -> dCalmar/dCAGR/dSum (dr - db)."""
    blocks = np.union1d(dr["blk2"].unique(), db["blk2"].unique())
    idx = {int(b): i for i, b in enumerate(blocks)}
    nb = len(blocks)

    def agg(d):
        bi = np.array([idx[int(b)] for b in d["blk2"].to_numpy()], dtype=np.int64)
        return np.bincount(bi, weights=d["pnl"].to_numpy(float), minlength=nb)

    br, bb = agg(dr), agg(db)
    rng = np.random.default_rng(seed)
    dcal, dcagr, dsum = np.empty(nrep), np.empty(nrep), np.empty(nrep)
    ndays = 3.0 * nb
    for r in range(nrep):
        pick = rng.integers(0, nb, size=nb)
        vals = []
        for b in (br, bb):
            p = b[pick]
            eq = np.concatenate(([cap0], cap0 + np.cumsum(p)))
            mdd = float(((eq / np.maximum.accumulate(eq) - 1) * 100.0).min())
            s = float(p.sum())
            cagr = ((cap0 + s) / cap0) ** (365.25 / ndays) - 1 if (cap0 + s) > 0 else -1.0
            vals += [(cagr * 100) / abs(mdd) if mdd != 0 else np.nan, cagr * 100, s]
        dcal[r], dcagr[r], dsum[r] = vals[0] - vals[3], vals[1] - vals[4], vals[2] - vals[5]
    return dict(cal=dcal, cagr=dcagr, sum=dsum, K=nb)


def ci(a):
    a = np.asarray(a, float)
    a = a[np.isfinite(a)]
    lo, hi = np.percentile(a, [2.5, 97.5])
    return (float(lo), float(hi))     # INFL = 1.0 (k=1) => CI tho


def tier1(m, x):
    yd = {y: v for y, v in x["dd_year"].items() if y in YEARS}
    worst_y = min(yd.values()) if yd else float("nan")
    neg = [y for y in m["neg_year"] if y in {str(v) for v in YEARS}]
    ok = {"maxDD_phut_nam<=40": (bool(worst_y >= -40.0), worst_y),
          "UW<=250": (bool(x["uw_win_days"] <= 250.0), x["uw_win_days"]),
          "quy_xau>=-20": (bool(m["qmin_w"] >= -20.0), m["qmin_w"]),
          "0_nam_am": (len(neg) == 0, neg),
          "conc<=15": (bool(m["conc_max"] <= 15.0), m["conc_max"])}
    return all(v[0] for v in ok.values()), ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mtm-cache", default=MASTER + "/featv1_mtm.json")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--mtm-prime-old", action="store_true", help="chi tinh truoc MTM 2 tag nen cu (S3) roi thoat")
    ap.add_argument("--json", default=REPO + "/docs/result/feat_add_v1.json")
    ap.add_argument("--md", default=REPO + "/docs/result/RESULT_FEAT_ADD_V1.md")
    a = ap.parse_args()
    R.COSTS = {"base": R.LEGACY, "stress": R.LEGACY}
    R.COST_LEVELS = {"legacy": R.LEGACY, "base": R.LEGACY, "stress": R.LEGACY}
    R.MTM_COSTS = {"legacy": R.LEGACY}

    if a.mtm_prime_old:
        import hashlib  # noqa: F401
        lg = {k: R.load_legs(t) for k, t in REFS.items()}
        mm = {k: R.md5_of(t) for k, t in REFS.items()}
        raw = json.load(open(a.mtm_cache)) if os.path.exists(a.mtm_cache) else {}
        miss = {k: lg[k] for k in lg if k not in raw or mm[k] != raw[k].get("md5")}
        if miss:
            new = R.run_mtm(miss, workers=a.workers, chunk=30)
            for k, vv in new.items():
                vv["md5"] = mm[k]
                raw[k] = vv
            json.dump(raw, open(a.mtm_cache, "w"))
        log.info("MTM prime OLD xong: %s", sorted(raw))
        return
    alltags = dict(TAGS)
    have_ref = all(os.path.exists(os.path.join(R.KOUT, t, "storage", "printDone.csv")) for t in REFS.values())
    if have_ref:
        alltags.update(REFS)
    legs, daily, md5 = {}, {}, {}
    for k, t in alltags.items():
        legs[k], daily[k], md5[k] = R.load_legs(t), R.load_daily(t), R.md5_of(t)
        log.info("%-8s %-20s n=%d equity=%.0f md5=%s", k, t, len(legs[k]), daily[k]["equity"].iloc[-1], md5[k][:8])
    n0, eq0f = len(legs["B0"]), float(daily["B0"]["equity"].iloc[-1])
    par = (md5["B0"] == PARITY_MD5 and n0 == PARITY_N and round(eq0f) == PARITY_EQ)
    log.info("PARITY B0: md5=%s n=%d eq=%.0f -> %s", md5["B0"], n0, eq0f, "PASS" if par else "*** FAIL ***")
    if not par:
        json.dump(dict(parity_ok=False, md5=md5, n=n0, eq=eq0f), open(a.json + ".parity_fail", "w"), indent=1)
        log.info("DUNG: parity B0 FAIL — khong cham tiep")
        sys.exit(3)

    # ---- kiem cua so sach: tien to 2021H2 giong het giua B0 va V1
    pre_b = legs["B0"][legs["B0"]["ts"] < WIN0]
    pre_v = legs["V1"][legs["V1"]["ts"] < WIN0]
    cols = ["sym", "start", "end", "pnl", "margin"]
    same_pre = bool(len(pre_b) == len(pre_v) and (pre_b[cols].reset_index(drop=True)
                                                 == pre_v[cols].reset_index(drop=True)).all().all())
    eq_pre = {k: float(daily[k].loc[:PRE, "equity"].iloc[-1]) for k in alltags}
    log.info("2021H2 prefix identical B0/V1: %s (n_pre %d/%d)  eq@2021-12-31: %s", same_pre, len(pre_b), len(pre_v),
             {k: round(v) for k, v in eq_pre.items()})

    # ---- MTM phut (cua so reset 2022)
    raw = json.load(open(a.mtm_cache)) if os.path.exists(a.mtm_cache) else {}
    miss = {k: legs[k] for k in alltags if k not in raw or md5.get(k) != raw[k].get("md5")}
    log.info("MTM cache co %s; can tinh %s", sorted(raw), sorted(miss))
    if miss:
        new = R.run_mtm(miss, workers=a.workers, chunk=30)
        for k, vv in new.items():
            vv["md5"] = md5[k]
            raw[k] = vv
        json.dump(raw, open(a.mtm_cache, "w"))
    mtm = {k: raw[k]["legacy"] for k in alltags}
    for k in mtm:      # json cache doi khoa int -> str
        for f in ("dd_year", "uw_year"):
            mtm[k][f] = {int(y): float(vv) for y, vv in mtm[k][f].items()}

    M, rows = {}, {}
    for k in alltags:
        dw = daily[k].loc[PRE:]
        lw = legs[k][legs[k]["ts"] >= WIN0].reset_index(drop=True)
        m = R.core_metrics(k, lw, dw, "legacy")
        m["qmin_w"] = float(min(v for q, v in m["qr"].items() if q >= "2022Q1"))
        cal = m["cagr"] / abs(mtm[k]["dd_win"]) if mtm[k].get("dd_win") else float("nan")
        t1 = tier1(m, mtm[k])
        M[k] = dict(n_w=int(len(lw)), n_full=int(len(legs[k])), eq_start=eq_pre[k], eq_end=float(dw["equity"].iloc[-1]),
                    cagr_w=m["cagr"], mtm_dd_win=mtm[k]["dd_win"], mtm_uw_win=mtm[k]["uw_win_days"],
                    mtm_dd_year={int(y): v for y, v in mtm[k]["dd_year"].items() if int(y) in YEARS},
                    mtm_uw_year={int(y): v for y, v in mtm[k]["uw_year"].items() if int(y) in YEARS},
                    qmin=m["qmin_w"], yr={y: v for y, v in m["yr"].items() if y in {str(v) for v in YEARS}},
                    qr={q: v for q, v in m["qr"].items() if q >= "2022Q1"}, neg_year=m["neg_year"],
                    conc_max=m["conc_max"], rates=m["rates"], calmar_MTM=float(cal), t1_pass=bool(t1[0]),
                    t1={kk: [vv[0], vv[1]] for kk, vv in t1[1].items()}, md5=md5[k],
                    sum_pnl_w=float(lw["pnl"].sum()), maxdd_daily_w=m["maxdd_daily"])
        rows[k] = lw
        log.info("%-8s n_w=%d eq %.0f->%.0f CAGR %.2f ddMTM %.2f UW %.0f qmin %.2f Cal %.3f T1=%s", k, M[k]["n_w"],
                 M[k]["eq_start"], M[k]["eq_end"], m["cagr"], mtm[k]["dd_win"], mtm[k]["uw_win_days"], m["qmin_w"], cal,
                 "PASS" if t1[0] else "FAIL")

    # ---- bootstrap (V1 - B0)
    cap0 = eq_pre["B0"]
    b = block_boot(rows["V1"], rows["B0"], cap0)
    ci_b = ci(b["cal"])
    P.CAP0 = cap0
    e = P.boot_pair(rows["V1"], rows["B0"], "2025-12-30", nrep=NREP, seed=SEED)
    ci_e = ci(e["cal"])
    d_cal = M["V1"]["calmar_MTM"] - M["B0"]["calmar_MTM"]
    boot = dict(K_block=b["K"], K_episode=e["K"], dCalmar_MTM_obs=float(d_cal),
                block72=dict(ci=ci_b, mean=float(np.nanmean(b["cal"])), contains0=bool(ci_b[0] <= 0 <= ci_b[1]),
                             pos_lo=bool(ci_b[0] > 0), dCAGR_ci=ci(b["cagr"]), dSum_ci=ci(b["sum"])),
                episode=dict(ci=ci_e, mean=float(np.nanmean(e["cal"])), contains0=bool(ci_e[0] <= 0 <= ci_e[1]),
                             pos_lo=bool(ci_e[0] > 0), dCAGR_ci=ci(e["cagr"]), dSum_ci=ci(e["sum"])))

    # ---- verdict theo luat pre-reg
    v, bb = M["V1"], M["B0"]
    cond_cal = v["calmar_MTM"] > bb["calmar_MTM"]
    cond_n = (v["n_w"] > bb["n_w"]) and (v["calmar_MTM"] >= CALMAR_MULT * bb["calmar_MTM"])
    cond_ci = boot["block72"]["pos_lo"] and boot["episode"]["pos_lo"]
    win = bool(v["t1_pass"] and (cond_cal or cond_n) and cond_ci)
    verdict = "V1 THANG B0" if win else "V1 ~ B0 (khong thang)"
    dn_pct = 100.0 * (v["n_full"] - PARITY_N) / PARITY_N
    old = None
    if have_ref:
        o0, o1 = M["OLD_MOC"], M["OLD_V1"]
        old = dict(eq_ratio_end_V1_vs_B0_new=v["eq_end"] / bb["eq_end"] - 1,
                   eq_ratio_end_V1_vs_B0_old=o1["eq_end"] / o0["eq_end"] - 1,
                   pnl_w_ratio_new=v["sum_pnl_w"] / bb["sum_pnl_w"] - 1,
                   pnl_w_ratio_old=o1["sum_pnl_w"] / o0["sum_pnl_w"] - 1,
                   growth_w_new=(v["eq_end"] / v["eq_start"]) / (bb["eq_end"] / bb["eq_start"]) - 1,
                   growth_w_old=(o1["eq_end"] / o1["eq_start"]) / (o0["eq_end"] / o0["eq_start"]) - 1,
                   dCalmar_new=d_cal, dCalmar_old=o1["calmar_MTM"] - o0["calmar_MTM"],
                   dCAGR_new=v["cagr_w"] - bb["cagr_w"], dCAGR_old=o1["cagr_w"] - o0["cagr_w"],
                   dn_new=v["n_w"] - bb["n_w"], dn_old=o1["n_w"] - o0["n_w"])
    out = dict(prereg="docs/prereg/PREREG_FEAT_ADD_V1.md", prereg_md5="9ce3d65868c053ceaa564c184e6245ff",
               window="2022-01-01..2025-12-30", nrep=NREP, seed=SEED, inflate=INFL, parity_ok=True,
               same_2021_prefix=same_pre, eq_pre=eq_pre, dn_pct_full_vs_2517=dn_pct, metrics=M, boot=boot,
               conds=dict(t1_v1=v["t1_pass"], t1_b0=bb["t1_pass"], cal_gt=bool(cond_cal), n_rule=bool(cond_n),
                          ci_both_pos=bool(cond_ci)),
               verdict=verdict, old_vs_new=old, md5=md5)
    os.makedirs(os.path.dirname(a.json), exist_ok=True)
    json.dump(out, open(a.json, "w"), indent=1, ensure_ascii=False, default=str)
    log.info("dCalmar_MTM obs %+.3f | block72 CI [%+.2f,%+.2f] | episode CI [%+.2f,%+.2f] | verdict=%s",
             d_cal, ci_b[0], ci_b[1], ci_e[0], ci_e[1], verdict)

    # ---- ROI distribution (roidist.py, cua so 2022+)
    roi_txt = ""
    try:
        pa, pb = "/tmp/featv1_roi_b0.csv", "/tmp/featv1_roi_v1.csv"
        rows["B0"][["profit", "pnl"]].to_csv(pa, index=False)
        rows["V1"][["profit", "pnl"]].to_csv(pb, index=False)
        roi_txt = subprocess.check_output([sys.executable, MASTER + "/roidist.py", pa, pb, "B0", "V1"],
                                          stderr=subprocess.STDOUT).decode()
    except Exception as ex:  # noqa: BLE001
        roi_txt = "roidist FAIL: %s" % ex
    open(MASTER + "/featv1_roidist.txt", "w").write(roi_txt)

    # ---- markdown tables (quy + nam)
    def fmt(x, nd=2):
        return ("%+." + str(nd) + "f") % x
    qs = sorted(M["B0"]["qr"].keys())
    nq = {k: rows[k].groupby(rows[k]["ts"].dt.to_period("Q").astype(str)).size().to_dict() for k in ("B0", "V1")}
    tq = ["| quy | n B0 | n V1 | ROI% B0 | ROI% V1 | dROI |", "|---|---:|---:|---:|---:|---:|"]
    for q in qs:
        tq.append("| %s | %d | %d | %s | %s | %s |" % (q, nq["B0"].get(q, 0), nq["V1"].get(q, 0), fmt(M["B0"]["qr"][q]),
                                                      fmt(M["V1"]["qr"][q]), fmt(M["V1"]["qr"][q] - M["B0"]["qr"][q])))
    ny = {k: rows[k].groupby(rows[k]["ts"].dt.year).size().to_dict() for k in ("B0", "V1")}
    ty = ["| nam | n B0 | n V1 | ROI% B0 | ROI% V1 | dROI | maxDD phut B0 | maxDD phut V1 | UW ngay B0 | UW ngay V1 |",
          "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for y in YEARS:
        ys = str(y)
        ty.append("| %d | %d | %d | %s | %s | %s | %s | %s | %.0f | %.0f |" % (
            y, ny["B0"].get(y, 0), ny["V1"].get(y, 0), fmt(M["B0"]["yr"][ys]), fmt(M["V1"]["yr"][ys]),
            fmt(M["V1"]["yr"][ys] - M["B0"]["yr"][ys]), fmt(M["B0"]["mtm_dd_year"][y]), fmt(M["V1"]["mtm_dd_year"][y]),
            M["B0"]["mtm_uw_year"][y], M["V1"]["mtm_uw_year"][y]))
    open(MASTER + "/featv1_tables.md", "w").write("\n".join(tq) + "\n\n" + "\n".join(ty) + "\n")
    log.info("\n%s\n\n%s\n\nROIDIST\n%s", "\n".join(tq), "\n".join(ty), roi_txt)


if __name__ == "__main__":
    main()
