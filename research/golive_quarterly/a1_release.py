#!/usr/bin/env python3
"""GOLIVE_QUARTERLY 2026 + ECMEAS(H) — BAN A1 (phat hanh lai theo HO2026_NOTF D3).

Dung DUNG pipeline goc:
  - MTM phut: research/golive_quarterly/mtm_ho.py (ecm_mtm_h / ho4_score_a, gia close 1m Vision, cache ecm_px, offline)
  - Bang quy : research/golive_quarterly/quarterly.py (build()/metrics(), quy uoc quy +07, ph0 = 2026-01-01)
Chi doi TAG nguon: A0 tsx-ho-x14-s* -> A1 nt-x14-s*; co X14 = 18 ngay / 5 khoang ghi trong result.json cua A1.
Khong chay kernel moi, khong tai du lieu moi (fetch offline; fail>0 => dung).
Out: docs/result/golive_quarterly_a1/{quarterly_a1_by_seed.csv, summary_a1.json, ecm_h_a1.json}
"""
import json, logging, os, sys
import numpy as np
import pandas as pd

REPO = "/home/ubuntu/claude_master/vz_e1_wt"
sys.path.insert(0, REPO + "/research/golive_quarterly")
sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
import ecm_mtm_h as E  # noqa: E402
import quarterly as Q  # noqa: E402

SA = E.SA
log = logging.getLogger("gq_a1")
OUTD = REPO + "/docs/result/golive_quarterly_a1"
WK = "/home/ubuntu/claude_master/golive_quarterly_a1_wk"
SEEDS = [42, 7, 13, 21, 99, 123, 777, 2024]
TAGS = ["nt-x14-s%d" % s for s in SEEDS]
P0 = {s: "nt-k24-b-s%d" % s for s in SEEDS}
NOTF = "/home/ubuntu/claude_master/ho_tradfi_wk/notf_mtm.json"


def fetch_offline(job):
    sym, per = job
    fn = SA.vfile(sym, per)
    if os.path.exists(fn):
        return sym, per, "cache"
    if os.path.exists(fn + ".404"):
        return sym, per, "404"
    return sym, per, "fail"


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout, force=True)
    os.makedirs(OUTD, exist_ok=True); os.makedirs(WK, exist_ok=True)
    SA.fetch = fetch_offline
    W = SA.W
    W["dry"], W["DL"] = False, "20260930"
    WINS = E.WINS
    W["T0"] = min(SA.ms_local(v[0]) for v in WINS.values())
    W["NW"] = (max(SA.ms_local(v[1]) for v in WINS.values()) - W["T0"]) // 60000
    W["win"] = {k: (int((SA.ms_local(a) - W["T0"]) // 60000), int((SA.ms_local(b) - SA.ms_local(a)) // 60000),
                    int((SA.ms_local(b) - SA.ms_local(a)) // 86400000), SA.pd.Timestamp(a).normalize())
                for k, (a, b) in WINS.items()}
    D, UPS, RJ, drop = {}, {}, {}, 0
    for t in TAGS + list(P0.values()):
        D[t], dr = SA.load(t)
        drop += dr
        UPS[t] = SA.updates(t)
        RJ[t] = json.load(open(SA.OUT + t + "/result.json"))
    NE = W["NW"]
    for t in TAGS:
        ls = [u for u in UPS[t] if u[0][:8] == str(RJ[t].get("date_last"))]
        if ls:
            NE = max(NE, (ls[-1][1] - W["T0"]) // 60000 + 1)
    W["NE"] = int(min(NE, W["NW"] + 2 * 1440))
    U, mt = SA.build(TAGS, D, 8)
    log.info("MTM check %s", {k: v for k, v in mt.items() if k not in ("tail", "nofile_list")})
    assert mt["miss"] == 0 and mt["nofile"] == 0 and mt["fetch"]["ok"] == 0 and mt["fetch"]["fail"] == 0, "MTM thieu gia / co tai mang"
    ref = json.load(open(NOTF))["runs"]
    eqs, metr, chk = {}, {}, {}
    for i, t in enumerate(TAGS):
        eq = SA.equity(D[t], RJ[t]["equity_start"], U[i])
        ec = SA.eqcheck(eq, UPS[t], RJ[t])
        assert str(ec.get("final_ok")) == "True" and ec.get("upd_vs_result") is True, (t, ec)
        eqs[t] = eq.astype(np.float64)
        metr[t] = {}
        dif = 0.0
        for wk in ("W9", "Q1", "Q2", "Q3"):
            m, _ = SA.metr(D[t], eq, wk)
            metr[t][wk] = m
            for k in ("n", "sum_pnl", "roi", "maxdd"):
                dif = max(dif, abs(float(m[k]) - float(ref[t][wk][k])))
        chk[t] = dict(ref_maxabs_notf=dif, eqcheck=ec, len=int(len(eq)))
        log.info("CHK %s %s", t, chk[t])
    assert all(c["ref_maxabs_notf"] < 1e-6 for c in chk.values()), "MTM A1 khong tai lap notf_mtm"
    # --- bang quy: dung build()/metrics() goc, co X14 = 18 ngay tu result.json A1
    FH = Q.flagset(RJ[TAGS[0]]["overrides"]["SIM_LOSER_TS_EXT_DAYS"])
    ranges = RJ[TAGS[0]]["overrides"]["SIM_LOSER_TS_EXT_DAYS"]
    for t in TAGS:
        assert RJ[t]["overrides"]["SIM_LOSER_TS_EXT_DAYS"] == ranges, t
    log.info("X14 A1: %s -> %d ngay", ranges, len(FH))
    rows, CHK = [], {}
    for t, s in zip(TAGS, SEEDS):
        r = Q.build(t, P0[s], eqs[t], Q.HO_L0 - Q.H7, FH)
        CHK[t] = r["chk"]
        for name, a, b, k in Q.HO_PER:
            rows.append(dict(phase="HO", seed=str(s), period=name, kind=k, start=str(a.date()), end=str(b.date()),
                             **Q.metrics(r, a, b, k, Q.HO_L0, FH)))
        log.info("BUILD %s %s", t, r["chk"])
    df = pd.DataFrame(rows)
    df.to_csv(OUTD + "/quarterly_a1_by_seed.csv", index=False)
    # median/min/max qua 8 seed cho tung period (KHONG cong don cac cot)
    agg = {}
    for per in [p[0] for p in Q.HO_PER]:
        g = df[df.period == per]
        agg[per] = {c: dict(median=float(g[c].median()), min=float(g[c].min()), max=float(g[c].max()))
                    for c in ("n_entry", "n_cl", "n_leg", "win_cl", "pnl_per_cl", "pnl", "roi", "cagr_ann", "ret_mtm",
                              "dd_q", "dd_cum", "calmar", "exp_mean", "exp_max", "npos_max", "hold_med_h", "ex_trail",
                              "ex_ts168", "ex_x14", "ex_other", "fee", "funding", "flat_days", "noentry_days", "flag_days")}
    V = dict(seeds=SEEDS, tags=TAGS, x14_ranges=ranges, x14_days=len(FH), mtm_check={k: v for k, v in mt.items() if k != "tail"},
             chk=CHK, axis_ok=bool(all(v["flat_maxabs"] < 0.1 for v in CHK.values())))
    json.dump(dict(summary=agg, validate=V), open(OUTD + "/summary_a1.json", "w"), indent=1, default=str)
    # --- ECMEAS (H): chi so scorer HO4 theo cua so (W9/Q1/Q2/Q3) + H1 = Q1+Q2
    ecm = {}
    for t, s in zip(TAGS, SEEDS):
        ecm[str(s)] = {}
        for wk in ("W9", "Q1", "Q2", "Q3"):
            ecm[str(s)][wk] = {k: metr[t][wk][k] for k in E.KEEP}
    json.dump(ecm, open(OUTD + "/ecm_h_a1.json", "w"), indent=1, default=str)
    log.info("DONE rows=%d", len(df))


if __name__ == "__main__":
    main()
