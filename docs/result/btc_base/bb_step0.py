#!/usr/bin/env python3
"""BTC_BASE buoc 0 (khao sat, CHUA do hieu qua overlay): tai lap B0 (V1), phu gia (V2), phan phoi n_t crash-buy, du lieu BTC/ETH."""
import json
import logging
import sys

import numpy as np

sys.path.insert(0, "/home/ubuntu/claude_master/btc_base")
import bb_core as C  # noqa: E402  (bb_core import gvz_mtm truoc)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout)
log = logging.getLogger("bb0")


def main():
    out = {"dev": {}, "ho": {}}
    ecm = json.load(open("/home/ubuntu/claude_master/vz_e1_wt/docs/result/RESULT_ENTRYCOST_MEASURE.json"))["runs"]["D"]["bucket"]
    hom = json.load(open("/home/ubuntu/claude_master/tsx/ho/ho_mtm.json"))["runs"]
    d = C.dev_legs()
    arrs = C.dev_closes(d)
    nmD = C.WIN["D"]["a1"] - C.WIN["D"]["a0"]
    PD = C.load_px("D")
    for s in C.SEEDS:
        x = d[d.seed == s].reset_index(drop=True)
        S = C.Seed(x, [arrs[k] for k in x.key], C.CAP, nmD, lim=60)
        r = C.simulate(S, PD, C.WIN["D"]["a0"], {"kind": "B0"})
        assert np.abs(r["E"] - S.E0).max() < 1e-6
        m = C.metrics(r, S, PD, "D")
        E = ecm[str(s)]
        v1 = dict(cagr22=m["cagr22"], cagr22_ecm=E["cagr22"], dd22=m["dd_min_22"], dd22_ecm=E["maxdd22"],
                  spnl=m["pnl_total"], spnl_ecm=E["spnl"])
        v1["ok"] = abs(v1["cagr22"] - v1["cagr22_ecm"]) <= 0.3 and abs(v1["dd22"] - v1["dd22_ecm"]) <= 0.3
        out["dev"][str(s)] = dict(V1=v1, V2=dict(legs=S.n, legmin=S.legmin, legs_noprice=S.legs_noprice,
                                                   miss_after_ffill60=S.miss_after_ffill),
                                  nt=C.nt_stats(S), corr=C.corr_info(S, PD, C.WIN["D"]["a0"]),
                                  b0={k: m[k] for k in ("cagr22", "cagr_full", "dd_min_full", "dd_hour_full", "dd_day_full",
                                                        "dd_rule", "dd_min_22", "calmar22", "worst_month", "worst_month_at",
                                                        "dd_peak", "dd_trough", "pnl22_total", "dd22_min")})
        log.info("DEV s%s V1 %s V2 %s nt %s", s, v1, out["dev"][str(s)]["V2"], out["dev"][str(s)]["nt"])
    nmH = C.WIN["H"]["a1"] - C.WIN["H"]["a0"]
    PH = C.load_px("H")
    for s in C.SEEDS:
        x, eq0 = C.ho_legs(s)
        x = x[x.m0 < nmH].reset_index(drop=True)
        carr = C.ho_closes(x, nmH)
        S = C.Seed(x, carr, eq0, nmH, lim=None)
        r = C.simulate(S, PH, C.WIN["H"]["a0"], {"kind": "B0"})
        m = C.metrics(r, S, PH, "H")
        h = hom["ho4-k24-b-s%d" % s]["W9"]
        v1 = dict(roi=m["roi"], roi_ref=h["roi"], dd=m["dd_min_full"], dd_ref=h["maxdd"], eq0=float(S.E0[0]), eq0_ref=h["eq0"])
        v1["ok"] = abs(v1["roi"] - v1["roi_ref"]) <= 0.3 and abs(v1["dd"] - v1["dd_ref"]) <= 0.3
        out["ho"][str(s)] = dict(V1=v1, V2=dict(legs=S.n, legmin=S.legmin, legs_noprice=S.legs_noprice,
                                                  miss_after_ffill=S.miss_after_ffill), nt=C.nt_stats(S))
        log.info("HO s%s V1 %s V2 %s nt %s", s, v1, out["ho"][str(s)]["V2"], out["ho"][str(s)]["nt"])
    for win in ("dev", "ho"):
        keys = list(out[win]["42"]["nt"].keys())
        out[win + "_nt_agg"] = {k: [float(np.median([out[win][str(s)]["nt"][k] for s in C.SEEDS])),
                                    float(np.min([out[win][str(s)]["nt"][k] for s in C.SEEDS])),
                                    float(np.max([out[win][str(s)]["nt"][k] for s in C.SEEDS]))] for k in keys}
        out[win + "_V1_all"] = all(out[win][str(s)]["V1"]["ok"] for s in C.SEEDS)
        log.info("%s nt agg (median,min,max) %s V1_all %s", win, out[win + "_nt_agg"], out[win + "_V1_all"])
    out["px_report"] = json.load(open(C.W + "/px_report.json"))
    z = np.load(C.W + "/px_btceth.npz")
    t0 = int(z["t0"])
    for win in ("D", "H"):
        a0, a1 = C.WIN[win]["a0"], C.WIN[win]["a1"]
        b = z["btc"][a0 - t0:a1 - t0]
        out["btc_" + win] = dict(first=float(b[0]), last=float(b[-1]), ret=float(100 * (b[-1] / b[0] - 1)),
                                 dd_min=C.dd_of(b)[0], dd_hour=C.dd_of(b[59::60])[0])
    json.dump(out, open(C.W + "/step0.json", "w"), indent=1, default=float)
    log.info("STEP0_DONE btc_D %s btc_H %s", out["btc_D"], out["btc_H"])


if __name__ == "__main__":
    main()
