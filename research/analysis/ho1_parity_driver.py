#!/usr/bin/env python3
"""HO1 B8 — parity seal DONG (SIM_END_DATE=20251231) + hieu chuan net015. Pre-reg 35d03784 + ADDENDUM-1.
Kernel = tools/kaggle_sim.py HEAD (NOWRITE242) + khoi pred_ds cua gate_ablation_driver (kiem md5 pred) [+ khoi funding_ds cho CAL].
  C1 = B0 K16 phi goc (jar b7c89f09)       vs de-p1 650c386f (moi cot printDone; cot volume so so hoc)
  C2 = K24+skipFull phi goc                == gqsf-a1 ad26fd55
  C3 = M2 stress (NSEL + penalty 0.01675)  == nsel-m2-s42 cbc067f7
  CAL = C1 voi funding.bin co doan bins fold 20251001 = f18-retrain (M-cal2: lenh 2025Q4 doi / n C1 2025Q4 > 1% => DUNG)
Usage: python3 ho1_parity_driver.py upload NAME | dsstatus NAME | submit TAG.. --code-sha SHA | status | fetch TAG.. | compare"""
import argparse
import csv
import hashlib
import json
import logging
import os
import sys
import time

REPO = "/home/ubuntu/src/BinanceFuturesJava"
sys.path.insert(0, REPO)
sys.path.insert(0, os.path.join(REPO, "research/analysis"))
import gate_ablation_driver as GA  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("ho1par")
H = "/home/ubuntu/claude_master/1003/ho1"
KG = H + "/kaggle"
OUT = "/home/ubuntu/kaggle_sim/out/%s/"
BUNDLE, JAR_DS, TICK26 = "sim-ho26-bundle", "sim-jar-nsel", "wfo-ticker-2026h1"
JAR_SHA = "b7c89f097241763bb240c24b411a66531b41dad12b1716f13237537386de62c2"
NSEL = {"NSEL_ADD_ENABLED": "true", "NSEL_ADD_TOPK": 32, "SIM_NSEL_ADD_ROLLING_PCT": "0.999915",
        "SIM_NSEL_ADD_ROLLING_DAYS": 90, "SIM_NSEL_CORE_ADD": "true", "NSEL_CORE_ADD_MAX_PER_CLUSTER": 1,
        "NSEL_ADD_F1_MIN_BARRET": "-0.01"}
K24 = dict(GA.B0OV, SELECTOR_RANK_TOPK=24, GATE_QUOTA_SKIP_WHEN_FULL="true")
CONF = {"ho1-c1": (dict(GA.B0OV), "de-p1", "650c386f0d0dfea334af9d55ca2f21d4"),
        "ho1-c2": (K24, "gqsf-a1", "ad26fd55f0bb5db32038ec8b357cf8e7"),
        "ho1-c3": (dict(K24, **NSEL, SIM_CRASH_ENTRY_PENALTY="0.01675"), "nsel-m2-s42", "cbc067f717fa6bd06779c149d71e2e07"),
        "ho1-cal": (dict(GA.B0OV), "ho1-c1", None)}
FUND_BLOCK = r'''# [HO1 CAL 2026-10-09] funding_ds: thay funding.bin (doan bins fold 20251001 = f18-retrain) -> viet lai md5_funding.
if CFG.get("funding_ds"):
    _fc = [c for c in sorted(glob.glob(IN + "/**/funding.bin", recursive=True)) if ("/" + CFG["funding_ds"] + "/") in c]
    if not _fc:
        LOG.error("MISSING funding.bin cho funding_ds=%r", CFG["funding_ds"])
        sys.exit(1)
    _ovf = os.path.join(WORK, "wfo_ds_fund")
    os.makedirs(_ovf, exist_ok=True)
    for _nm in ("market.bin", "pred.bin"):
        if not os.path.lexists(os.path.join(_ovf, _nm)):
            os.symlink(os.path.realpath(os.path.join(DS, _nm)), os.path.join(_ovf, _nm))
    os.symlink(_fc[0], os.path.join(_ovf, "funding.bin"))
    _fl, _nr = [], 0
    for _ln in open(os.path.join(DS, "manifest.txt")):
        if _ln.startswith("md5_funding="):
            _fl.append("md5_funding=" + CFG["funding_md5"] + "\n")
            _nr += 1
        else:
            _fl.append(_ln)
    assert _nr == 1, _nr
    with open(os.path.join(_ovf, "manifest.txt"), "w") as _f:
        _f.writelines(_fl)
    LOG.info("funding_ds=%s -> WFO_DATA_DIR %s md5_funding=%s", CFG["funding_ds"], _ovf, CFG["funding_md5"])
    DS = _ovf
'''


def template():
    t = GA.template()
    assert t.count(GA.PATCH_ANCHOR) == 1
    return t.replace(GA.PATCH_ANCHOR, FUND_BLOCK + GA.PATCH_ANCHOR)


def md5f(p):
    return GA.md5f(p)


def upload(a):
    ks = GA.ks_mod()
    for name in a.names:
        fol = KG + "/" + name
        assert os.path.exists(fol + "/dataset-metadata.json"), fol
        t0 = time.time()
        r = ks._api().dataset_create_new(fol, public=False, quiet=True, dir_mode="skip")
        log.info("UPLOAD %s -> %s (%.0fs)", name, getattr(r, "url", r), time.time() - t0)
        for _ in range(240):
            try:
                st = str(ks._api().dataset_status(ks.USER + "/" + name)).lower()
            except Exception as e:  # noqa: BLE001
                st = "err:%s" % e
            if st == "ready":
                break
            time.sleep(30)
        log.info("DATASET %s status %s", name, st)


def submit(a):
    ks = GA.ks_mod()
    st = json.load(open(KG + "/stage_manifest.json"))
    base = st["bundle"]["pred.bin"]["md5"]
    assert base == st["preds"]["42"]
    log.info("free_slots=%d", ks.free_slots())
    for tag in a.tags:
        ov = dict(CONF[tag][0])
        ref = ks.kernel_ref(tag)
        folder = os.path.join(ks.WORKDIR, ks.slug(tag))
        os.makedirs(folder, exist_ok=True)
        cfg = {"tag": tag, "profile": GA.PROFILE, "overrides": ov, "sim_end_date": "20251231", "xmx": "22g",
               "timeout_s": 7800, "code_sha": a.code_sha, "bins_ds": "", "jar_ds": JAR_DS, "market_ds": "",
               "market_align": False, "extra_env": {}, "ticker_min_days": ks.TICKER_MIN_DAYS,
               "pred_ds": "ho26-pred-s42", "want_pred_md5": st["preds"]["42"], "want_pred_base": base}
        dss = [ks.USER + "/" + BUNDLE] + ks.TICKER_DS + [ks.USER + "/" + TICK26, ks.USER + "/" + JAR_DS,
                                                          ks.USER + "/ho26-pred-s42"]
        if tag == "ho1-cal":
            cj = json.load(open(H + "/cal/funding_cal.bin.json"))
            cfg.update(funding_ds="ho26-cal-funding", funding_md5=cj["md5"])
            dss.append(ks.USER + "/ho26-cal-funding")
        with open(os.path.join(folder, "run.py"), "w") as f:
            f.write(template().replace("__CFG_JSON__", repr(json.dumps(cfg))))
        md = {"id": ref, "title": ref.split("/")[1], "code_file": "run.py", "language": "python",
              "kernel_type": "script", "is_private": True, "enable_gpu": False, "enable_internet": True,
              "dataset_sources": dss, "competition_sources": [], "kernel_sources": []}
        with open(os.path.join(folder, "kernel-metadata.json"), "w") as f:
            json.dump(md, f, indent=1)
        r = ks._api().kernels_push(folder)
        log.info("PUSHED %s %s ov=%s ds=%s", tag, getattr(r, "url", r), json.dumps(ov), dss)


def status(a):
    ks = GA.ks_mod()
    for t in a.tags or list(CONF):
        try:
            log.info("%s %s", t, ks._status(ks.kernel_ref(t)))
        except Exception as e:  # noqa: BLE001
            log.info("%s chua co (%s)", t, str(e)[:80])


def fetch(a):
    ks = GA.ks_mod()
    for t in a.tags:
        o = ks.fetch(t)
        log.info("%s %s", t, json.dumps(o.get("result"), default=str)[:700])


def rows(tag):
    with open(OUT % tag + "storage/printDone.csv", newline="") as f:
        r = list(csv.reader(f))
    return r[0], r[1:]


def cmp_c1(tag, ref):
    h1, r1 = rows(tag)
    h0, r0 = rows(ref)
    out = dict(header_equal=h1 == h0, n=len(r1), n_ref=len(r0), col_diff={})
    if h1 != h0 or len(r1) != len(r0):
        out["pass"] = False
        return out
    vi = h0.index("volume")
    for i in range(len(h0)):
        if not h0[i]:
            continue
        if i == vi:
            d = sum(1 for a, b in zip(r1, r0) if abs(float(a[i]) - float(b[i])) > 1e-9 * max(1.0, abs(float(b[i]))))
        else:
            d = sum(1 for a, b in zip(r1, r0) if a[i] != b[i])
        if d:
            out["col_diff"][h0[i]] = d
    out["volume_text_diff"] = sum(1 for a, b in zip(r1, r0) if a[vi] != b[vi])
    out["pass"] = not out["col_diff"]
    return out


def q4keys(tag):
    h, r = rows(tag)
    si, ti = h.index("sym"), h.index("start")
    lo, hi = 1759251600000, 1767200400000          # 2025-10-01 / 2026-01-01 00:00 +07
    return {(x[si], x[ti]) for x in r if lo <= int(float(x[ti])) < hi}


def compare(a):
    res = {}
    for tag, (_, ref, want) in CONF.items():
        p = OUT % tag + "storage/printDone.csv"
        if not os.path.exists(p):
            res[tag] = "chua co"
            continue
        rj = json.load(open(OUT % tag + "result.json"))
        r = dict(md5=md5f(p), n=rj.get("n_trades"), jar_ok=rj.get("jar_sha256") == JAR_SHA, mapper=rj.get("symbol_mapper"),
                 pred_used=rj.get("pred_md5_used"), date_last=rj.get("date_last"))
        if tag == "ho1-c1":
            r["vs_ref"] = cmp_c1(tag, ref)
            r["pass"] = bool(r["vs_ref"]["pass"] and r["jar_ok"])
        elif tag == "ho1-cal":
            A, B = q4keys("ho1-c1"), q4keys(tag)
            r.update(n_c1_q4=len(A), n_cal_q4=len(B), symdiff=len(A ^ B), frac=len(A ^ B) / max(1, len(A)))
            r["stop"] = r["frac"] > 0.01
        else:
            r["want"] = want
            r["pass"] = bool(r["md5"] == want and r["jar_ok"])
        res[tag] = r
        log.info("%s %s", tag, json.dumps(r, default=str))
    json.dump(res, open(H + "/parity.json", "w"), indent=1, default=str)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd")
    ap.add_argument("names", nargs="*")
    ap.add_argument("--code-sha", dest="code_sha", default="")
    a = ap.parse_args()
    a.tags = a.names
    dict(upload=upload, submit=submit, status=status, fetch=fetch, compare=compare)[a.cmd](a)
