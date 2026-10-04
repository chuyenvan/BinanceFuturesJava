#!/usr/bin/env python3
"""GATE_QUOTA_SKIPFULL (Pha E chuong trinh GATE). Pre-reg docs/prereg/PREREG_GATE_QUOTA_SKIPFULL.md (19072857).

Jar branch feat/gate-quota-skipfull (dataset sim-jar-gqsf). P0 = B0@K16 OFF (cong ff3ce513); ON = 8 seed @K24 +
GATE_QUOTA_SKIP_WHEN_FULL=true, ghep cap voi run OFF da co (n700-a1, gabl-seed7, gsb-s*).
Usage: jards | p0 --code-sha SHA | submit ARM.. --code-sha SHA | status [ARM..] | fetch ARM.. | parity | score
"""
import argparse
import hashlib
import json
import logging
import math
import os
import re
import shutil
import sys
import time

import numpy as np
import pandas as pd

REPO = "/home/ubuntu/src/BinanceFuturesJava"
HERE = os.path.join(REPO, "research/analysis")
sys.path.insert(0, REPO)
sys.path.insert(0, HERE)
import gate_ablation_driver as GA  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("gqsf")

D = "/home/ubuntu/claude_master/1004/gqsf"
JAR_DS = "sim-jar-gqsf"
JAR_SHA = open(D + "/jar.sha256").read().split()[0] if os.path.exists(D + "/jar.sha256") else None
PROF = "/home/ubuntu/kaggle_sim/jar_gdv2/prof_r4_kg0_k16_f015_g155.properties"
PROF_MD5 = "0e0caef09e47931b706c696d587a5184"
P0_TAG, P0_WANT = "gqsf-p0", "ff3ce513"
SEEDS = ["A1", "S7", "S13", "S21", "S99", "S123", "S777", "S2024"]
OFF = {"A1": "n700-a1", "S7": "gabl-seed7", **{s: "gsb-" + s.lower() for s in SEEDS[2:]}}
ON = {s: "gqsf-" + s.lower() for s in SEEDS}
KEY = "GATE_QUOTA_SKIP_WHEN_FULL"
OV_ON = dict(GA.B0OV, SELECTOR_RANK_TOPK=24, **{KEY: "true"})
K_INFL = 8
INFL = math.sqrt(2.0 * math.log(K_INFL))
T975_DF7 = 2.364624
SD_OFF_PREREG, CAL_OFF_PREREG = 3.58, 1.529
DISK_MIN_MB = 500
JSON_OUT = os.path.join(REPO, "docs/result/gate_skipfull.json")
GSB_MTM = "/home/ubuntu/claude_master/1004/gsb/mtm.json"
TOPK_WANT = "24"
MTM_FILE = D + "/mtm.json"
# [K16 bo sung] PREREG_GATE_QUOTA_SKIPFULL_K16.md: 3 seed @K16 (profile g2_flat3), OFF = jar moi key vang.
K16 = "--k16" in sys.argv
if K16:
    SEEDS = ["A1", "S21", "S7"]
    ON = {s: "gqsf16-" + s.lower() for s in SEEDS}
    OFF = {"A1": P0_TAG, "S21": "gqsf16off-s21", "S7": "gqsf16off-s7"}
    OV_ON = dict(GA.B0OV, **{KEY: "true"})
    TOPK_WANT = "16"
    K_INFL = 3
    INFL = math.sqrt(2.0 * math.log(K_INFL))
    SD_OFF_PREREG, CAL_OFF_PREREG = None, None
    MTM_FILE = D + "/mtm_k16.json"


def pred_of(s):
    """(dataset, md5) cua pred; A1 = pred.bin goc trong bundle (dataset None)."""
    if s == "A1":
        return None, GA.PRED0_MD5
    if s == "S7":
        return "gate-abl-seed7", json.load(open("/home/ubuntu/claude_master/1004/gabl/pred_SEED7/meta.json"))["md5"]
    return "gate-sb-" + s.lower(), json.load(open("/home/ubuntu/claude_master/1004/gsb/pred_%s/meta.json" % s))["md5"]


def disk(tag=""):
    mb = shutil.disk_usage("/home/ubuntu").free // (1 << 20)
    log.info("DF %s avail=%d MB", tag, mb)
    if mb < DISK_MIN_MB:
        log.error("DIA < %d MB -> DUNG", DISK_MIN_MB)
        sys.exit(3)
    return mb


def jards(a=None):
    ks = GA.ks_mod()
    disk("truoc jards")
    fol = D + "/ds_" + JAR_DS
    assert os.path.exists(fol + "/sim.jar") and GA.md5f(PROF) == PROF_MD5
    sha = hashlib.sha256(open(fol + "/sim.jar", "rb").read()).hexdigest()
    assert sha == JAR_SHA, (sha, JAR_SHA)
    shutil.copy(PROF, fol + "/" + os.path.basename(PROF))
    json.dump({"title": JAR_DS, "id": ks.USER + "/" + JAR_DS, "licenses": [{"name": "CC0-1.0"}]},
              open(fol + "/dataset-metadata.json", "w"))
    r = ks._api().dataset_create_new(fol, public=False, quiet=True, dir_mode="skip")
    log.info("dataset %s -> %s (jar %s)", JAR_DS, getattr(r, "url", r), sha)
    for _ in range(60):
        try:
            st = ks._api().dataset_status(ks.USER + "/" + JAR_DS)
        except Exception as e:  # noqa: BLE001
            st = "err:%s" % e
        log.info("dataset status %s", st)
        if str(st).lower() == "ready":
            return
        time.sleep(30)


def p0(a):
    ks = GA.ks_mod()
    disk("truoc p0")
    r = ks.submit(P0_TAG, GA.PROFILE, dict(GA.B0OV), jar_ds=JAR_DS, bundle_ds=GA.BUNDLE, sim_end_date="20251231",
                  xmx="22g", timeout_s=5400, code_sha=a.code_sha)
    log.info("PUSHED P0 %s ov=%s", r, json.dumps(GA.B0OV))


def submit(a):
    ks = GA.ks_mod()
    assert a.code_sha and JAR_SHA
    disk("truoc submit")
    log.info("free_slots=%d", ks.free_slots())
    for s in a.arms:
        tag = OFF[s] if a.off else ON[s]
        ov = dict(GA.B0OV) if a.off else dict(OV_ON)
        assert not (a.off and tag == P0_TAG)
        dsn, md5 = pred_of(s)
        if dsn is None:
            r = ks.submit(tag, GA.PROFILE, ov, jar_ds=JAR_DS, bundle_ds=GA.BUNDLE, sim_end_date="20251231",
                          xmx="22g", timeout_s=7200, code_sha=a.code_sha)
            log.info("PUSHED %s %s ov=%s", tag, r, json.dumps(ov))
            continue
        ref = ks.kernel_ref(tag)
        folder = os.path.join(ks.WORKDIR, ks.slug(tag))
        os.makedirs(folder, exist_ok=True)
        cfg = {"tag": tag, "profile": GA.PROFILE, "overrides": ov, "sim_end_date": "20251231", "xmx": "22g",
               "timeout_s": 7200, "code_sha": a.code_sha, "bins_ds": "", "jar_ds": JAR_DS, "market_ds": "",
               "market_align": False, "extra_env": {}, "ticker_min_days": ks.TICKER_MIN_DAYS,
               "pred_ds": dsn, "want_pred_md5": md5, "want_pred_base": GA.PRED0_MD5}
        with open(os.path.join(folder, "run.py"), "w") as f:
            f.write(GA.template().replace("__CFG_JSON__", repr(json.dumps(cfg))))
        md = {"id": ref, "title": ref.split("/")[1], "code_file": "run.py", "language": "python",
              "kernel_type": "script", "is_private": True, "enable_gpu": False, "enable_internet": True,
              "dataset_sources": [ks.USER + "/" + GA.BUNDLE] + ks.TICKER_DS + [ks.USER + "/" + JAR_DS, ks.USER + "/" + dsn],
              "competition_sources": [], "kernel_sources": []}
        with open(os.path.join(folder, "kernel-metadata.json"), "w") as f:
            json.dump(md, f, indent=1)
        r = ks._api().kernels_push(folder)
        log.info("PUSHED %s %s pred=%s md5=%s ov=%s", tag, getattr(r, "url", r), dsn, md5, json.dumps(ov))


def status(a):
    ks = GA.ks_mod()
    for t in ([ON[s] for s in a.arms] if a.arms else [P0_TAG] + list(ON.values())):
        try:
            log.info("%s %s", t, ks._status(ks.kernel_ref(t)))
        except Exception as e:  # noqa: BLE001
            log.info("%s chua co (%s)", t, str(e)[:80])


def fetch(a):
    ks = GA.ks_mod()
    for x in a.arms:
        disk("truoc fetch " + x)
        t = P0_TAG if x == "P0" else (OFF[x] if a.off else ON[x])
        o = ks.fetch(t)
        log.info("%s %s", t, json.dumps(o.get("result"), default=str)[:600])


def logtxt(tag):
    out = ""
    for fn in ("logs/full.log", "logs/sim.out"):
        p = GA.OUT % tag + fn
        if os.path.exists(p):
            with open(p, errors="ignore") as f:
                out += f.read()
    return out


def offline_line(tag):
    v = [ln for ln in logtxt(tag).splitlines() if "md5 verified" in ln and "pred=" in ln]
    return v[-1].split("LOAD offline OK")[-1] if v else None


def parity(a=None):
    import reset_rule_score as R
    res = {}
    t0 = P0_TAG
    if os.path.exists(GA.OUT % t0 + "storage/printDone.csv"):
        rj = GA.result_json(t0)
        m = R.md5_of(t0)
        res["P0"] = dict(ok=bool(m.startswith(P0_WANT) and rj.get("jar_sha256") == JAR_SHA and rj.get("ok") is True),
                         md5=m, n=rj.get("n_trades"), eq=rj.get("equity_final"), jar=rj.get("jar_sha256"))
        log.info("PARITY P0 %s", res["P0"])
    for s in SEEDS:
        tag = ON[s]
        if not os.path.exists(GA.OUT % tag + "storage/printDone.csv"):
            continue
        rj, pr, txt = GA.result_json(tag), GA.prof_run(tag), logtxt(tag)
        dsn, md5 = pred_of(s)
        ver = [ln for ln in txt.splitlines() if "md5 verified" in ln and "pred=" in ln]
        sk = re.findall(r"skipFull=(\d+)", txt)
        chk = dict(jar=rj.get("jar_sha256") == JAR_SHA, mapper=(rj.get("symbol_mapper") or 0) >= 800,
                   topk24=pr.get("SELECTOR_RANK_TOPK") == TOPK_WANT, key_on=pr.get(KEY) == "true", ok=rj.get("ok") is True,
                   b0ov=all(pr.get(k) == str(v) for k, v in GA.B0OV.items()),
                   log_key="[GATE-QUOTA] SKIP_WHEN_FULL=ON" in txt, skip_count=bool(sk),
                   # A1 (pred goc trong bundle): dong Java "LOAD offline OK ... (md5 verified)" khong in md5 -> so
                   # NGUYEN dong (bo timestamp) voi run OFF n700-a1 cung bundle (sua checker sau lan chay dau, khong doi run)
                   pred=(bool(ver) and ver[-1].split("LOAD offline OK")[-1] == offline_line(OFF[s])) if dsn is None else
                   (rj.get("pred_md5_used") == md5 and rj.get("pred_md5_base") == GA.PRED0_MD5))
        res[s] = dict(ok=all(chk.values()), checks=chk, md5=R.md5_of(tag), n=rj.get("n_trades"),
                      eq=rj.get("equity_final"), skip_full=int(sk[-1]) if sk else None, pred_md5=md5,
                      secs=rj.get("secs"), date_last=rj.get("date_last"))
        log.info("PARITY %-6s %s n=%s eq=%s skipFull=%s %s", s, "PASS" if res[s]["ok"] else "*** VOID ***",
                 res[s]["n"], res[s]["eq"], res[s]["skip_full"], chk)
    if K16:
        for s in SEEDS:
            tag = OFF[s]
            if tag == P0_TAG or not os.path.exists(GA.OUT % tag + "storage/printDone.csv"):
                continue
            rj, pr = GA.result_json(tag), GA.prof_run(tag)
            dsn, md5 = pred_of(s)
            chk = dict(jar=rj.get("jar_sha256") == JAR_SHA, topk=pr.get("SELECTOR_RANK_TOPK") == TOPK_WANT,
                       key_absent=KEY not in pr, ok=rj.get("ok") is True,
                       b0ov=all(pr.get(k) == str(v) for k, v in GA.B0OV.items()),
                       pred=rj.get("pred_md5_used") == md5 and rj.get("pred_md5_base") == GA.PRED0_MD5)
            res["OFF_" + s] = dict(ok=all(chk.values()), checks=chk, md5=R.md5_of(tag), n=rj.get("n_trades"),
                                   eq=rj.get("equity_final"))
            log.info("PARITY OFF_%-5s %s %s", s, "PASS" if res["OFF_" + s]["ok"] else "*** VOID ***", res["OFF_" + s])
    json.dump(res, open(D + ("/parity_k16.json" if K16 else "/parity.json"), "w"), indent=1)
    return res


def stats(v):
    v = np.asarray(v, float)
    return dict(mean=float(v.mean()), sd=float(v.std(ddof=1)), min=float(v.min()), max=float(v.max()), n=int(len(v)))


def cagr_from(eq, a, b):
    e = eq.copy()
    e.index = pd.to_datetime(e.index)
    x0, x1 = e[e.index <= pd.Timestamp(a)].iloc[-1], e[e.index <= pd.Timestamp(b)]
    yrs = (x1.index[-1] - pd.Timestamp(a)).days / 365.25
    return float(100 * ((x1.iloc[-1] / x0) ** (1 / yrs) - 1))


def year_ret(eq):
    e = eq.copy()
    e.index = pd.to_datetime(e.index)
    out, prev = {}, float(e[e.index <= "2021-12-31"].iloc[-1])
    for y in (2022, 2023, 2024, 2025):
        v = float(e[e.index <= "%d-12-31" % y].iloc[-1])
        out[y], prev = 100 * (v / prev - 1), v
    return out


def tagof(k):
    return OFF[k[4:]] if k.startswith("OFF_") else ON[k[3:]]


def score(a):
    import reset_rule_score as R
    import feat_add_v1_score as F  # noqa: F401  (side effect: MTMState cua so 2022+)
    import flat3_crashpen_driver as F3
    import selector_ablation_driver as SAD
    import n700_driver as N
    R.MTM_COSTS = {"legacy": R.LEGACY}
    SAD.INFL = INFL
    par = parity()
    assert par.get("P0", {}).get("ok"), "P0 chua PASS -> khong cham"
    ok = [s for s in SEEDS if par.get(s, {}).get("ok") and (not K16 or OFF[s] == P0_TAG or par.get("OFF_" + s, {}).get("ok"))]
    void = [s for s in SEEDS if s not in ok]
    keys = ["OFF_" + s for s in ok] + ["ON_" + s for s in ok]
    for k in keys:
        N.TAG[k], N.DESC[k] = tagof(k), "GATE_QUOTA_SKIPFULL " + k
    legs, daily, md5 = {}, {}, {}
    for k in keys:
        legs[k], daily[k], md5[k] = R.load_legs(tagof(k)), R.load_daily(tagof(k)), R.md5_of(tagof(k))
    raw = json.load(open(MTM_FILE)) if os.path.exists(MTM_FILE) else {}
    gm = json.load(open(GSB_MTM))
    for s in ok:
        if "OFF_" + s not in raw and gm.get(s, {}).get("md5") == md5["OFF_" + s]:
            raw["OFF_" + s] = gm[s]
    miss = {k: legs[k] for k in keys if k not in raw or raw[k].get("md5") != md5[k]}
    log.info("MTM cache %s; can tinh %s", sorted(raw), sorted(miss))
    if miss:
        new = R.run_mtm(miss, workers=a.workers, chunk=30)
        for k, vv in new.items():
            vv["md5"] = md5[k]
            raw[k] = vv
        disk("truoc ghi mtm")
        json.dump(raw, open(MTM_FILE, "w"))
    M = {}
    for k in keys:
        M[k] = N.arm_metrics(R, F3, k, legs[k], daily[k], raw[k]["legacy"])
        M[k]["md5"] = md5[k]
        M[k]["gate_minutes"] = GA.gate_minutes(tagof(k))
        M[k]["cagr23"] = cagr_from(daily[k]["equity"], "2022-12-31", "2025-12-30")
        M[k]["yret"] = year_ret(daily[k]["equity"])
    con = {}
    for s in ok:
        e0 = daily["OFF_" + s]["equity"][daily["OFF_" + s]["equity"].index >= GA.W0]
        e1 = daily["ON_" + s]["equity"][daily["ON_" + s]["equity"].index >= GA.W0]
        assert len(e0) == len(e1) and (e0.index == e1.index).all(), ("lech ngay", s)
        obs, bs = SAD.daily_boot({"P0": e0, "ON": e1})
        con[s] = {m: SAD.ci_of(obs["ON"][m] - obs["P0"][m], bs["ON"][m] - bs["P0"][m]) for m in ("cagr", "mdd", "calmar")}
    finish(M, con, par, ok, void)


def finish(M, con, par, ok, void):
    n = len(ok)
    on = lambda s, m: M["ON_" + s][m]  # noqa: E731
    off = lambda s, m: M["OFF_" + s][m]  # noqa: E731
    d22 = np.array([on(s, "cagr22") - off(s, "cagr22") for s in ok])
    d23 = np.array([on(s, "cagr23") - off(s, "cagr23") for s in ok])
    if n == 8:
        tc = T975_DF7
    elif n == 3:
        tc = 4.302653
    else:
        from scipy import stats as _st
        tc = float(_st.t.ppf(0.975, n - 1))
    hw = tc * d22.std(ddof=1) / math.sqrt(n)
    band = {side: {m: stats([M[side + "_" + s][m] for s in ok]) for m in
                   ("cagr22", "calmar22", "dd_mtm22", "dd_mtm", "uw_mtm22", "n_per_year", "cagr23")}
            for side in ("OFF", "ON")}
    rule = dict(
        C1=dict(mean=float(d22.mean()), ci=[float(d22.mean() - hw), float(d22.mean() + hw)], t=tc,
                ok=bool(d22.mean() > 0 and d22.mean() - hw > 0)),
        C2=dict(sd_on=band["ON"]["cagr22"]["sd"], sd_off_prereg=SD_OFF_PREREG, sd_off_calc=band["OFF"]["cagr22"]["sd"],
                ok=bool(band["ON"]["cagr22"]["sd"] < (SD_OFF_PREREG or band["OFF"]["cagr22"]["sd"]))),
        C3=dict(worst_dd=min(min(on(s, "dd_mtm"), on(s, "dd_mtm22")) for s in ok),
                ok=all(abs(on(s, "dd_mtm")) <= 40 and abs(on(s, "dd_mtm22")) <= 40 for s in ok)),
        C4=dict(mean_on=band["ON"]["calmar22"]["mean"], thr=0.9 * (CAL_OFF_PREREG or band["OFF"]["calmar22"]["mean"]),
                mean_off_calc=band["OFF"]["calmar22"]["mean"],
                ok=bool(band["ON"]["calmar22"]["mean"] >= 0.9 * (CAL_OFF_PREREG or band["OFF"]["calmar22"]["mean"]))),
        C5=dict(mean_d_cagr23=float(d23.mean()), ok=bool(d23.mean() >= -1.0)))
    rule["GO"] = bool(n == len(SEEDS) and all(rule[c]["ok"] for c in ("C1", "C2", "C3", "C4", "C5")))
    rows = {}
    for s in ok:
        gm0, gm1 = M["OFF_" + s]["gate_minutes"]["per_year"], M["ON_" + s]["gate_minutes"]["per_year"]
        rows[s] = dict(cagr22=[off(s, "cagr22"), on(s, "cagr22")], dd22=[off(s, "dd_mtm22"), on(s, "dd_mtm22")],
                       dd_all=[off(s, "dd_mtm"), on(s, "dd_mtm")], cal22=[off(s, "calmar22"), on(s, "calmar22")],
                       uw22=[off(s, "uw_mtm22"), on(s, "uw_mtm22")], n_yr=[off(s, "n_per_year"), on(s, "n_per_year")],
                       min_year={y: [gm0.get(y), gm1.get(y)] for y in GA.YEARS},
                       cagr23=[off(s, "cagr23"), on(s, "cagr23")],
                       yret={y: [M["OFF_" + s]["yret"][y], M["ON_" + s]["yret"][y]] for y in GA.YEARS},
                       skip_full=par[s]["skip_full"], boot=con[s])
        r = rows[s]
        log.info("ROW %-5s CAGR22 %6.2f->%6.2f (%+5.2f) dd22 %6.2f->%6.2f ddAll %6.2f->%6.2f Cal %5.3f->%5.3f UW %4.0f->%4.0f "
                 "n/y %4.0f->%4.0f min22 %s->%s C23 %+5.2f skip %s bootCAGR %+.2f infl[%+.2f;%+.2f]", s,
                 *r["cagr22"], r["cagr22"][1] - r["cagr22"][0], *r["dd22"], *r["dd_all"], *r["cal22"], *r["uw22"],
                 *r["n_yr"], gm0.get(2022), gm1.get(2022), r["cagr23"][1] - r["cagr23"][0], r["skip_full"],
                 con[s]["cagr"]["d"], *con[s]["cagr"]["ci_infl"])
        log.info("YRET %-5s %s", s, {y: [round(v[0], 2), round(v[1], 2)] for y, v in r["yret"].items()})
    for side in ("OFF", "ON"):
        log.info("BAND %s %s", side, json.dumps({m: {k: round(v, 3) for k, v in x.items()} for m, x in band[side].items()}))
    log.info("RULE %s", json.dumps(rule))
    js = dict(prereg="docs/prereg/PREREG_GATE_QUOTA_SKIPFULL.md", prereg_commit="19072857", jar_ds=JAR_DS,
              jar_sha256=JAR_SHA, kaggle_sim_md5=GA.KS_MD5_WANT, k_infl=K_INFL, inflate=INFL, nrep=2000, seed=20260905,
              block_days=10, window="2022-01-01..2025-12-30 (rebase 2021-12-31)", tags=dict(on=ON, off=OFF, p0=P0_TAG),
              void=void, parity=par, rows=rows, band=band, d_cagr22=d22.tolist(), d_cagr23=d23.tolist(), rule=rule,
              metrics=M)
    disk("truoc ghi json")
    if K16:
        js["prereg"], js["note"] = "docs/prereg/PREREG_GATE_QUOTA_SKIPFULL_K16.md", "n=3, df 2: chi bao cao"
        base = json.load(open(JSON_OUT))
        base["k16"] = js
        js = base
    json.dump(js, open(JSON_OUT, "w"), indent=1, ensure_ascii=False, default=str)
    log.info("JSON -> %s", JSON_OUT)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd")
    ap.add_argument("arms", nargs="*")
    ap.add_argument("--code-sha", default="")
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--off", action="store_true")
    ap.add_argument("--k16", action="store_true")
    a = ap.parse_args()
    for s in a.arms:
        assert s in SEEDS or s == "P0", s
    fn = {"jards": jards, "p0": p0, "submit": submit, "status": status, "fetch": fetch, "parity": parity,
          "score": score, "df": lambda _a: disk("df")}
    fn[a.cmd](a)


if __name__ == "__main__":
    main()
