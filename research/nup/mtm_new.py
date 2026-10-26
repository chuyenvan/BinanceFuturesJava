#!/usr/bin/env python3
"""NUP MTM: tinh equity phut cho cac run NUP bang DUNG pipeline GOLIVE_QUARTERLY.

DEV: gvz_mtm + reset_rule_score.run_mtm (import dung thu tu), assert missing=0.
HO : ecm_mtm_h / ho4_score_a tren cache ecm_px (offline), assert miss=nofile=0.
Out: ~/claude_master/nup_wk/{eq_dev.npz, mtm_dev.json, eq_ho.npz, mtm_ho.json}
Usage: python3 mtm_new.py dev <tag...> | ho <tag...>
"""
import json
import logging
import os
import sys

import numpy as np

W = "/home/ubuntu/claude_master/nup_wk"
KS = "/home/ubuntu/kaggle_sim/out/"
CAP0 = 35000.0
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("nup_mtm")


def dev(tags):
    sys.path.insert(0, "/home/ubuntu/claude_master/tsx")
    import tsx_driver as T  # noqa: F401  (path src/research/analysis cho n700/F3)
    sys.path.insert(0, "/home/ubuntu/claude_master/gvz")
    import gvz_mtm as MT  # noqa: E402  (PHAI truoc R)
    import reset_rule_score as R  # noqa: E402
    import flat3_crashpen_driver as F3  # noqa: E402
    import n700_driver as N  # noqa: E402

    assert R._work is MT._work_vision, "gvz_mtm chua patch R"
    REG = []

    class Rec(MT.MTMStateD):
        def __init__(self):
            super().__init__()
            self.rec = {}
            REG.append(self)

        def feed(self, m_global, eq):
            super().feed(m_global, eq)
            self.rec[int(m_global)] = np.asarray(eq["legacy"], np.float32).copy()

    R.MTMState = Rec
    legs = {t: R.load_legs(t) for t in tags}
    daily = {t: R.load_daily(t) for t in tags}
    out = R.run_mtm(legs, workers=3, chunk=30)
    assert len(REG) == len(tags), (len(REG), len(tags))
    miss = {t: int(out[t]["legacy"]["missing"]) for t in tags}
    log.info("MISSING %s", miss)
    assert all(v == 0 for v in miss.values()), "MTM missing: %s" % miss
    arrs, chk = {}, {}
    for t, st in zip(tags, REG):
        ms = sorted(st.rec)
        assert all(b - a == 1440 for a, b in zip(ms, ms[1:])), (t, "ngay khong lien tuc")
        e = np.concatenate([st.rec[m] for m in ms]).astype(np.float64)
        arrs[t] = e
        arrs[t + "__m0"] = np.array([ms[0]], np.int64)
        sp = float(legs[t]["pnl"].sum())
        N.TAG[t], N.DESC[t] = t, "NUP " + t
        M = N.arm_metrics(R, F3, t, legs[t], daily[t], out[t]["legacy"])
        flat = None
        chk[t] = dict(tag=t, md5=R.md5_of(t), missing=int(out[t]["legacy"]["missing"]), n_legs=int(len(legs[t])),
                      m0=int(ms[0]), n_min=int(len(e)), eq_last=float(e[-1]),
                      cap0_plus_sumpnl=float(CAP0 + sp), dd_total=float(out[t]["legacy"]["dd_total"]),
                      dd_win=float(out[t]["legacy"]["dd_win"]), cagr22=float(M["cagr22"]),
                      dd22=float(M["dd_mtm22"]), sum_pnl=float(M["sum_pnl"]))
        log.info("CHK %s %s", t, chk[t])
    np.savez(W + "/eq_dev.npz", **arrs)
    ok = bool(all(v["missing"] == 0 and abs(v["eq_last"] - v["cap0_plus_sumpnl"]) < 0.1 for v in chk.values()))
    json.dump(dict(check=chk, ok=ok), open(W + "/mtm_dev.json", "w"), indent=1)
    log.info("DONE ok=%s", ok)


def ho(tags):
    sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
    import ecm_mtm_h as E  # noqa: E402
    SA = E.SA

    def fetch_offline(job):
        sym, per = job
        fn = SA.vfile(sym, per)
        if os.path.exists(fn):
            return sym, per, "cache"
        if os.path.exists(fn + ".404"):
            return sym, per, "404"
        return sym, per, "fail"

    SA.fetch = fetch_offline
    Wd = SA.W
    Wd["dry"], Wd["DL"] = False, "20260930"
    WINS = E.WINS
    Wd["T0"] = min(SA.ms_local(v[0]) for v in WINS.values())
    Wd["NW"] = (max(SA.ms_local(v[1]) for v in WINS.values()) - Wd["T0"]) // 60000
    Wd["win"] = {k: (int((SA.ms_local(a) - Wd["T0"]) // 60000), int((SA.ms_local(b) - SA.ms_local(a)) // 60000),
                     int((SA.ms_local(b) - SA.ms_local(a)) // 86400000), SA.pd.Timestamp(a).normalize())
                 for k, (a, b) in WINS.items()}
    D, UPS, RJ, drop = {}, {}, {}, 0
    for t in tags:
        D[t], dr = SA.load(t)
        drop += dr
        UPS[t] = SA.updates(t)
        RJ[t] = json.load(open(KS + t + "/result.json"))
    NE = Wd["NW"]
    for t in tags:
        ls = [u for u in UPS[t] if u[0][:8] == str(RJ[t].get("date_last"))]
        if ls:
            NE = max(NE, (ls[-1][1] - Wd["T0"]) // 60000 + 1)
    Wd["NE"] = int(min(NE, Wd["NW"] + 2 * 1440))
    U, mt = SA.build(tags, D, 8)
    log.info("MTM check %s", {k: v for k, v in mt.items() if k not in ("tail", "nofile_list")})
    if mt.get("nofile_list"):
        log.error("NOFILE %s", mt["nofile_list"][:30])
    assert mt["miss"] == 0 and mt["nofile"] == 0 and mt["fetch"]["ok"] == 0 and mt["fetch"]["fail"] == 0, "MTM HO thieu gia"
    arrs, chk = {}, {}
    for i, t in enumerate(tags):
        eq = SA.equity(D[t], RJ[t]["equity_start"], U[i])
        ec = SA.eqcheck(eq, UPS[t], RJ[t])
        arrs[t] = eq.astype(np.float64)
        arrs[t + "__e"] = D[t]["e"].to_numpy(np.int64)
        arrs[t + "__pnl"] = D[t]["pnl"].to_numpy(np.float64)
        chk[t] = dict(len=int(len(eq)), eq_start=float(RJ[t]["equity_start"]), eqcheck=ec, dropped=drop,
                      sum_pnl=float(D[t]["pnl"].sum()))
        log.info("CHK %s %s", t, chk[t])
    arrs["__T0"] = np.array([Wd["T0"]], np.int64)
    np.savez(W + "/eq_ho.npz", **arrs)
    json.dump(dict(T0=int(Wd["T0"]), NE=Wd["NE"], mtm_check={k: v for k, v in mt.items() if k != "tail"},
                   check=chk, ok=bool(mt["miss"] == 0)), open(W + "/mtm_ho.json", "w"), indent=1, default=str)
    log.info("DONE miss=%s", mt["miss"])


if __name__ == "__main__":
    sc = sys.argv[1]
    if sc == "dev":
        dev(sys.argv[2:])
    elif sc == "ho":
        ho(sys.argv[2:])
    else:
        raise SystemExit(__doc__)
