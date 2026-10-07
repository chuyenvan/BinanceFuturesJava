#!/usr/bin/env python3
"""K32_CONFIRM (2026-10-07): cham phep thu XAC NHAN arm l2-k32 (K32 pct 0.999915 skipFull ON) tren seed 7/21.

Pre-reg docs/prereg/PREREG_K32_CONFIRM.md (39729383). Thuoc = gkf_rescore.py (1f9e0e2f): goi lai ham cua no
(parity checks, nen 1m, stress COST_TRUTH +1.675%/chan vao nen sap <= -1%, MTM phut, metrics, boot block-10d).
k = 1 (khong inflate; INFL = 1 => ci_infl == ci_raw). Seed 42 chi bao cao (nhiem chon loc).
Usage: python3 research/analysis/k32_confirm.py [--workers 3]
"""
import argparse
import json
import logging
import os
import sys

import numpy as np

REPO = "/home/ubuntu/src/BinanceFuturesJava"
sys.path.insert(0, REPO + "/research/analysis")
import gkf_rescore as G  # noqa: E402

R, N, SAD = G.R, G.N, G.SAD
log = logging.getLogger("k32c")
D = "/home/ubuntu/claude_master/1007/k32c"
JSON_OUT = REPO + "/docs/result/k32_confirm.json"
MD_OUT = D + "/tables.md"
AUDIT = REPO + "/docs/audit/AUDIT_GKF_PHASE1_20261007.json"
GQSF = REPO + "/docs/result/gate_skipfull.json"
G.BAR_CACHE, G.MTM_CACHE = D + "/bar.json", D + "/mtm.json"
G.INFL = SAD.INFL = N.INFL = 1.0
K, PCT = 32, "0.999915000"
# seed -> (arm, nen, pred md5 mong (None = pred goc), khoa ON_* trong gate_skipfull.json)
SEEDS = {"S7": ("k32c-s7", "gqsf-s7", "b737fb6d64d198c14654ea9c92510b36", "ON_S7"),
         "S21": ("k32c-s21", "gqsf-s21", "0b541d2259b31cf2794160e0aeafa3ff", "ON_S21"),
         "S42": ("gkf-l2-k32", "gqsf-a1", None, "ON_A1")}
CONF = ["S7", "S21"]
YEARS = G.YEARS
FLDS = ("cagr22", "calmar22", "dd_mtm22", "uw_mtm22", "n_per_year", "cagr23", "sum_pnl_2022_25", "dd_mtm")


def parity():
    res = {}
    f32 = "%.8f" % float(np.float32(float(PCT)))
    for s, (arm, base, pmd5, _) in SEEDS.items():
        rb = N.result_json(base)
        res[base] = dict(md5=R.md5_of(base), n=rb.get("n_trades"), eq=rb.get("equity_final"),
                         jar=str(rb.get("jar_sha256"))[:8], ok=rb.get("ok") is True)
        rj, pr, txt = N.result_json(arm), N.prof_run(arm), G.logtxt(arm)
        gl = G.gate_line(txt)
        vb = G.vline(G.logtxt(base))
        chk = dict(jar=rj.get("jar_sha256") == G.JAR_SHA, ok=rj.get("ok") is True,
                   date_last=rj.get("date_last") == "20251230", mapper=(rj.get("symbol_mapper") or 0) >= 800,
                   topk=pr.get("SELECTOR_RANK_TOPK") == str(K) and ("SELECTOR_RANK_TOPK=%d " % K) in txt,
                   pct=pr.get("SIM_GATE_ROLLING_PCT") == PCT and ("BAT: mode=ratio pct=" + f32 + " ") in txt,
                   skipfull=pr.get("GATE_QUOTA_SKIP_WHEN_FULL") == "true" and "[GATE-QUOTA] SKIP_WHEN_FULL=ON" in txt,
                   b0ov=all(pr.get(k) == str(v) for k, v in N.B0OV.items() if k != "SIM_GATE_ROLLING_PCT"),
                   pred_vline=G.vline(txt) is not None and G.vline(txt) == vb,
                   pred_md5=(pmd5 is None) or rj.get("pred_md5_used") == pmd5,
                   base_ok=res[base]["ok"])
        res[arm] = dict(seed=s, ok=bool(all(chk.values())), checks=chk, md5=R.md5_of(arm), n=rj.get("n_trades"),
                        eq=rj.get("equity_final"), jar=str(rj.get("jar_sha256"))[:8], pred=rj.get("pred_md5_used"),
                        pct_log=f32, gate=gl)
        log.info("PARITY %s %-11s %s md5=%s n=%s eq=%s jar=%s pred=%s pass=%s skipFull=%s fail=%s | nen %s md5=%s n=%s eq=%s",
                 s, arm, "PASS" if res[arm]["ok"] else "*** VOID ***", res[arm]["md5"][:8], res[arm]["n"], res[arm]["eq"],
                 res[arm]["jar"], str(res[arm]["pred"])[:8], gl["pass_all"], gl["skipFull"],
                 [k for k, v in chk.items() if not v], base, res[base]["md5"][:8], res[base]["n"], res[base]["eq"])
    return res


def seed_cache():
    """khoi tao cache MTM tu gkfscore (gkf-nen md5 == gqsf-a1); km5 kiem md5 nen khong sai duoc."""
    if os.path.exists(G.MTM_CACHE):
        return
    src = json.load(open("/home/ubuntu/claude_master/1007/gkfscore/mtm.json"))
    out = {}
    for a, b in (("gkf-l2-k32", "gkf-l2-k32"), ("gkf-nen", "gqsf-a1")):
        for sfx in ("", "#S"):
            if a + sfx in src:
                out[b + sfx] = src[a + sfx]
    json.dump(out, open(G.MTM_CACHE, "w"))
    log.info("seed MTM cache: %s", sorted(out))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=3)
    a = ap.parse_args()
    par = parity()
    void = [SEEDS[s][0] for s in SEEDS if not par[SEEDS[s][0]]["ok"]]
    assert not void, ("VOID", void)
    tags = [t for s in SEEDS for t in SEEDS[s][:2]]
    legs = {t: R.load_legs(t) for t in tags}
    daily = {t: R.load_daily(t) for t in tags}
    bar = G.load_bars(legs, a.workers)
    conv = {t: G.match_conv(legs[t], bar) for t in tags}
    lags = {}
    for s, (arm, base, _, _) in SEEDS.items():
        lags[s] = 0 if conv[base][0]["match"] >= conv[base][1]["match"] else 1
        log.info("LAG %s = %d %s", s, lags[s], conv[base])
    cr = {}
    for s, (arm, base, _, _) in SEEDS.items():
        for t in (arm, base):
            msk, br, hit = G.crash_mask(legs[t], bar, lags[s])
            st = G.stress_legs(legs[t], msk)
            legs[t + "#S"], daily[t + "#S"] = st, G.stress_daily(daily[t], st)
            w = ((legs[t]["ts"] >= "2022-01-01") & (legs[t]["ts"] < "2026-01-01")).to_numpy()
            cr[t] = dict(n=int(len(msk)), n_crash=int(msk.sum()), n_crash_2225=int((msk & w).sum()),
                         share_crash=float(msk.mean()), share_crash_2225=float(msk[w].mean()),
                         no_bar=int(np.isnan(br).sum()), entry_match=float(hit.mean()),
                         pen_sum_2225=float(st["pen"].to_numpy()[w].sum()), lag=lags[s])
            log.info("CRASH %-11s n=%d crash22-25=%d (%.2f%%) no_bar=%d match=%.4f pen22-25=%.0f", t, cr[t]["n"],
                     cr[t]["n_crash_2225"], 100 * cr[t]["share_crash_2225"], cr[t]["no_bar"], cr[t]["entry_match"],
                     cr[t]["pen_sum_2225"])
    keys = tags + [t + "#S" for t in tags]
    lag_of = {t: lags[s] for s in SEEDS for t in SEEDS[s][:2]}
    km5 = {k: par[k.split("#")[0]]["md5"] + ("#S%.5f:lag%d" % (G.PEN, lag_of[k.split("#")[0]]) if "#S" in k else "")
           for k in keys}
    seed_cache()
    raw = json.load(open(G.MTM_CACHE))
    miss = {k: legs[k] for k in keys if raw.get(k, {}).get("md5") != km5[k]}
    if miss:
        log.info("MTM phut can tinh %d: %s", len(miss), sorted(miss))
        new = R.run_mtm(miss, workers=a.workers, chunk=30)
        for k, v in new.items():
            v["md5"] = km5[k]
            raw[k] = v
        json.dump(raw, open(G.MTM_CACHE, "w"))
    M = {k: G.metrics(k, k.split("#")[0], legs[k], daily[k], raw[k]["legacy"]) for k in keys}
    # tu kiem: seed 42 tai tao AUDIT_GKF_PHASE1 (gkf-nen md5 == gqsf-a1); nen S7/S21 khop gate_skipfull.json
    au, gq = json.load(open(AUDIT))["metrics"], json.load(open(GQSF))["metrics"]
    bad = []
    for mine, ref in (("gkf-l2-k32", au["gkf-l2-k32"]), ("gkf-l2-k32#S", au["gkf-l2-k32#S"]),
                      ("gqsf-a1", au["gkf-nen"]), ("gqsf-a1#S", au["gkf-nen#S"]),
                      ("gqsf-s7", gq["ON_S7"]), ("gqsf-s21", gq["ON_S21"])):
        if mine not in M:
            continue
        for f in FLDS:
            if f in ref and abs(M[mine][f] - ref[f]) > 1e-6 * max(1.0, abs(ref[f])):
                bad.append((mine, f, M[mine][f], ref[f]))
    log.info("TU KIEM: %d lech %s", len(bad), bad)
    assert not bad, "TU KIEM LECH -> DUNG"
    C, OBS = {}, {}
    for s, (arm, base, _, _) in SEEDS.items():
        G.TAGS, G.BASE = [base, arm], base
        for sfx in ("", "#S"):
            obs, con = G.boot(daily, legs, sfx)
            C[arm + sfx] = con[arm + sfx]
            OBS[s + sfx] = obs
    per = {}
    for s, (arm, base, _, _) in SEEDS.items():
        for sfx in ("", "#S"):
            x, b, c = M[arm + sfx], M[base + sfx], C[arm + sfx]
            per[s + sfx] = dict(dPnL=c["pnl"], dCAGR22_boot=c["cagr"], dCAGR22=x["cagr22"] - b["cagr22"],
                                dCAGR23=x["cagr23"] - b["cagr23"], cal_arm=x["calmar22"], cal_nen=b["calmar22"],
                                cal_ratio=x["calmar22"] / b["calmar22"], dd22=(x["dd_mtm22"], b["dd_mtm22"]),
                                dd_all=(x["dd_mtm"], b["dd_mtm"]), dROI={y: x["yret"][y] - b["yret"][y] for y in YEARS},
                                dsum=x["sum_pnl_2022_25"] - b["sum_pnl_2022_25"])
            log.info("SEED %-5s dPnL=%+.0f [%+.0f;%+.0f] dCAGR22=%+.2f [%+.2f;%+.2f] Cal %.3f/%.3f=%.3f dd22 %.2f/%.2f",
                     s + sfx, c["pnl"]["d"], c["pnl"]["ci_raw"][0], c["pnl"]["ci_raw"][1], per[s + sfx]["dCAGR22"],
                     c["cagr"]["ci_raw"][0], c["cagr"]["ci_raw"][1], x["calmar22"], b["calmar22"],
                     per[s + sfx]["cal_ratio"], x["dd_mtm22"], b["dd_mtm22"])
    mroi = {y: float(np.mean([per[s + "#S"]["dROI"][y] for s in CONF])) for y in YEARS}
    ddok = all(M[k]["dd_mtm"] >= -40 and M[k]["dd_mtm22"] >= -40 for k in keys)
    go = dict(c1_dPnL_stress_gt0=all(per[s + "#S"]["dPnL"]["d"] > 0 for s in CONF),
              c2_cal22_stress_ge090=all(per[s + "#S"]["cal_ratio"] >= 0.90 for s in CONF),
              c3_maxDD_le40=bool(ddok),
              c4_mean_dROI_stress_3of4=sum(v >= 0 for v in mroi.values()) >= 3,
              c5_dPnL_base_gt0=all(per[s]["dPnL"]["d"] > 0 for s in CONF))
    verdict = "GO" if all(go.values()) else "NO-GO"
    mean = {sfx or "base": float(np.mean([per[s + sfx]["dCAGR22"] for s in CONF])) for sfx in ("", "#S")}
    log.info("LUAT %s mean_dROI_stress=%s mean_dCAGR22=%s => %s", go, mroi, mean, verdict)
    js = dict(title="RESULT_K32_CONFIRM", prereg="docs/prereg/PREREG_K32_CONFIRM.md", prereg_commit="39729383",
              ruler="gkf_rescore.py (1f9e0e2f), k=1 CI raw, NREP 2000 seed 20260905 block 10d",
              stress=dict(pen=G.PEN, crash_thr=G.CRASH, lags=lags, match_conv=conv, per_tag=cr),
              parity=par, metrics=M, per_seed=per, mean_dROI_stress_S7S21=mroi, mean_dCAGR22_S7S21=mean,
              rules=go, verdict=verdict, boot_obs=OBS)
    json.dump(js, open(JSON_OUT, "w"), indent=1, ensure_ascii=False, default=G.jd)
    fm = G.fm
    L = ["| seed | run | md5 | n | n/năm | CAGR22 b→s | maxDD22 b→s | maxDD all b | Calmar22 b→s | UW22 | 0h% | sập% |",
         "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for s, (arm, base, _, _) in SEEDS.items():
        for t in (arm, base):
            x, y = M[t], M[t + "#S"]
            L.append("| %s | %s | %s | %s | %s | %s→%s | %s→%s | %s | %s→%s | %s | %s | %s |" % (
                s, t, par[t]["md5"][:8], par[t]["n"], fm(x["n_per_year"], 0), fm(x["cagr22"]), fm(y["cagr22"]),
                fm(x["dd_mtm22"]), fm(y["dd_mtm22"]), fm(x["dd_mtm"]), fm(x["calmar22"], 3), fm(y["calmar22"], 3),
                fm(x["uw_mtm22"], 0), fm(x["hour0_2022_25"]["share0"], 1), fm(100 * cr[t]["share_crash_2225"], 1)))
    L += ["", "| seed | bản | ΔPnL22–25 [CI raw] | ΔCAGR22 [CI raw] | Cal×nền | ΔCAGR23 | ΔROI 22/23/24/25 |",
          "|---|---|---|---|---|---|---|"]
    for s in SEEDS:
        for sfx in ("", "#S"):
            p = per[s + sfx]
            L.append("| %s | %s | %s | %s | %s | %s | %s |" % (
                s, "stress" if sfx else "base", G.ci(p["dPnL"], 0), G.ci(p["dCAGR22_boot"]), fm(p["cal_ratio"], 3),
                fm(p["dCAGR23"], 2, True), " / ".join(fm(p["dROI"][y], 2, True) for y in YEARS)))
    L += ["", "mean ΔROI stress S7/S21: " + " / ".join("%d %s" % (y, fm(v, 2, True)) for y, v in mroi.items()),
          "mean ΔCAGR22 S7/S21: base %s, stress %s" % (fm(mean["base"], 2, True), fm(mean["#S"], 2, True)),
          "Luật: " + ", ".join("%s=%s" % (k, "✓" if v else "✗") for k, v in go.items()) + " ⇒ **%s**" % verdict]
    with open(MD_OUT, "w") as fo:
        fo.write("\n".join(L) + "\n")
    log.info("OUT %s %s", JSON_OUT, MD_OUT)


if __name__ == "__main__":
    main()
