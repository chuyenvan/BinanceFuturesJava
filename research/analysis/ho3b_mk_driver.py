#!/usr/bin/env python3
"""HO3b cong 4 (ADDENDUM-4 §4b, 62c0cd67): 2 kernel kinh te H1 ho3b-mk-{k24,b0}-s-s42 voi market.bin inline (Java Kernel A)
+ pred.bin s42 (momentum inline) + funding.bin dung lai TRONG kernel tren luoi market moi. Template = tools/kaggle_sim.py HEAD
(GA.template, guard NOWRITE242) + TICKER26 (ho26_queue) + FUND_REBUILD. So voi ho26-*-s-s42 theo thuoc §4b.
Usage: ho3b_mk_driver.py submit <tag> | status <tag> | fetch <tag> | compare"""
import csv, glob, hashlib, json, logging, os, re, subprocess, sys, time
R = "/home/ubuntu/src/BinanceFuturesJava"
sys.path.insert(0, R); sys.path.insert(0, R + "/research/analysis")
import gate_ablation_driver as GA  # noqa: E402
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout)
log = logging.getLogger("ho3b_mkd")
W = "/home/ubuntu/claude_master/1003/ho3b"
OUT = "/home/ubuntu/kaggle_sim/out/%s/"
BUNDLE, JAR_DS, TICK26 = "sim-ho26a-bundle", "sim-jar-nsel", "wfo-ticker-2026h1"
JAR_SHA = "b7c89f097241763bb240c24b411a66531b41dad12b1716f13237537386de62c2"
UNSEAL = "I_UNDERSTAND_THIS_BURNS_HOLDOUT_2026"
PEN = "0.01675"
PRED_BASE = "22f69456381d9d1abd1592382c3b0319"
SEAL7 = 1767200400000
B0 = dict(GA.B0OV)
K24 = dict(B0, SELECTOR_RANK_TOPK=24, GATE_QUOTA_SKIP_WHEN_FULL="true")
SPEC = {"ho3b-mk-k24-s-s42": (dict(K24, SIM_CRASH_ENTRY_PENALTY=PEN), "ho26-k24-s-s42"),
        "ho3b-mk-b0-s-s42": (dict(B0, SIM_CRASH_ENTRY_PENALTY=PEN), "ho26-b0-s-s42")}
T26 = json.load(open("/home/ubuntu/claude_master/1003/ho1/ticker26_oracle_gunzip_md5.json"))
MK = json.load(open(W + "/mk/mk_build.json"))
CODE_SHA = subprocess.run(["git", "-C", R, "rev-parse", "--short=8", "HEAD"], capture_output=True, text=True).stdout.strip()


def t26_block():
    s = open(R + "/research/analysis/ho26_queue.py").read()
    i = s.index("T26_BLOCK = r'''") + len("T26_BLOCK = r'''")
    return s[i:s.index("'''", i)]


def fund_block():
    b1 = open(W + "/ho3b_fund_block.py").read()
    b1 = b1.split("    if not _pre_ok or _miss or _diff:")[0]
    return b1 + open(W + "/ho3b_fund_block2.py").read()


def template():
    t = GA.template()
    assert t.count(GA.PATCH_ANCHOR) == 1
    t = t.replace(GA.PATCH_ANCHOR, t26_block() + fund_block() + GA.PATCH_ANCHOR)
    assert "NOWRITE_HOST" in t and "SYMBOL_MAPPER_PREFLIGHT_FAIL" in t and "TICKER26_MD5_FAIL" in t
    assert "FUND_REBUILD_OK" in t and t.index("PRED_MD5_BASE") < t.index("FUND_REBUILD_OK")
    compile(t.replace("__CFG_JSON__", repr("{}")), "kernel", "exec")
    return t


def submit(tag):
    ks = GA.ks_mod()
    ov, _ = SPEC[tag]
    ref = ks.kernel_ref(tag)
    folder = os.path.join(ks.WORKDIR, ks.slug(tag))
    os.makedirs(folder, exist_ok=True)
    cfg = {"tag": tag, "profile": GA.PROFILE, "overrides": dict(ov), "sim_end_date": "20260701", "xmx": "22g",
           "timeout_s": 7800, "code_sha": CODE_SHA, "bins_ds": "", "jar_ds": JAR_DS, "market_ds": "ho3b-mkt-h1",
           "market_align": False, "extra_env": {"HOLDOUT_UNSEAL": UNSEAL}, "ticker_min_days": 2007,
           "pred_ds": "ho3b-pred-mk-s42", "want_pred_md5": MK["pred"]["md5"], "want_pred_base": PRED_BASE,
           "t26_md5": T26, "fund_rebuild": {"need_bins": ["predict_wf_20251001.bin", "predict_wf_20260101.bin", "predict_wf_20260401.bin"], "end": 1782864000000, "seal7": SEAL7}}
    open(os.path.join(folder, "run.py"), "w").write(template().replace("__CFG_JSON__", repr(json.dumps(cfg))))
    dss = [ks.USER + "/" + BUNDLE] + ks.TICKER_DS + [ks.USER + "/" + d for d in
                                                     (TICK26, JAR_DS, "ho3b-pred-mk-s42", "ho3b-mkt-h1")]
    md = {"id": ref, "title": ref.split("/")[1], "code_file": "run.py", "language": "python",
          "kernel_type": "script", "is_private": True, "enable_gpu": False, "enable_internet": True,
          "dataset_sources": dss, "competition_sources": [], "kernel_sources": []}
    json.dump(md, open(os.path.join(folder, "kernel-metadata.json"), "w"), indent=1)
    r = ks._api().kernels_push(folder)
    log.info("PUSHED %s %s ov=%s", tag, getattr(r, "url", r), json.dumps(ov))


def status(tag):
    ks = GA.ks_mod()
    log.info("STATUS %s %s", tag, ks._status(ks.kernel_ref(tag)))


def kernel_text(tag):
    o, out = OUT % tag, ""
    for fn in ("logs/full.log", "logs/sim.out"):
        if os.path.exists(o + fn):
            out += open(o + fn, errors="ignore").read()
    for p in glob.glob(o + "*.log"):
        try:
            out += "".join(x.get("data", "") for x in json.load(open(p)))
        except Exception:  # noqa: BLE001
            out += open(p, errors="ignore").read()
    return out


def fetch(tag):
    ks = GA.ks_mod()
    ks.fetch(tag)
    ov, _ = SPEC[tag]
    o = OUT % tag
    rj = json.load(open(o + "result.json"))
    txt = kernel_text(tag)
    got = rj.get("overrides") or {}
    pens = [float(x) for x in re.findall(r"\[CRASH-PENALTY\] SUMMARY penalty=([0-9.eE+-]+)", txt)]
    chk = dict(ok=rj.get("ok") is True, jar=rj.get("jar_sha256") == JAR_SHA,
               mapper=isinstance(rj.get("symbol_mapper"), int) and rj["symbol_mapper"] >= 800,
               ov=set(got) == set(ov) and all(str(got[k]) == str(v) for k, v in ov.items()),
               pred=rj.get("pred_md5_used") == MK["pred"]["md5"] and rj.get("pred_md5_base") == PRED_BASE,
               t26="TICKER26_MD5 ok=181 bad=0 miss=0 extra=0" in txt, fund="FUND_REBUILD_OK" in txt,
               market="market_ds=ho3b-mkt-h1" in txt, unseal="HOLDOUT_UNSEAL DUNG" in txt,
               nsel="[NSEL] on=false" in txt, pen=bool(pens) and all(abs(p - float(PEN)) < 1e-12 for p in pens),
               n=bool(rj.get("n_trades")))
    fl = [l for l in txt.splitlines() if "FUND_REBUILD" in l][:6]
    pdp = o + "storage/printDone.csv"
    res = dict(tag=tag, chk=chk, ok_all=all(chk.values()), n=rj.get("n_trades"),
               md5=hashlib.md5(open(pdp, "rb").read()).hexdigest() if os.path.exists(pdp) else None, fund_log=fl)
    json.dump(res, open(W + "/mk/check_%s.json" % tag, "w"), indent=1)
    log.info("CHECK %s", json.dumps(res))


def load_pd(tag):
    import pandas as pd
    d = pd.read_csv(OUT % tag + "storage/printDone.csv", index_col=False)
    d.columns = [c.strip() for c in d.columns]
    for c in ("entry", "margin", "pnl"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d = d.dropna(subset=["entry", "margin", "pnl"]).copy()
    d["sym"] = d["sym"].astype(str).str.strip()
    d["st"] = d["start"].astype(str).str.strip()
    d["en"] = d["end"].astype(str).str.strip()
    return d


def tmin(s):
    import pandas as pd
    return (pd.to_datetime(s, format="%Y%m%d %H:%M").astype("int64") // 60_000_000_000).to_numpy()


def compare():
    A, B = "20260101 00:00", "20260701 00:00"
    out = {}
    for tag, (_, ref) in SPEC.items():
        n, o = load_pd(tag), load_pd(ref)
        nw = n[(n.st >= A) & (n.st < B)]
        ow = o[(o.st >= A) & (o.st < B)]
        tn, to = tmin(nw.st), tmin(ow.st)
        used = set()
        byso = {}
        for i, (s, t) in enumerate(zip(ow.sym.tolist(), to.tolist())):
            byso.setdefault(s, []).append((t, i))
        match = 0
        for s, t in sorted(zip(nw.sym.tolist(), tn.tolist()), key=lambda x: x[1]):
            for (t2, i) in byso.get(s, []):
                if i not in used and abs(t2 - t) <= 1:
                    used.add(i); match += 1
                    break
        pn = float(n[(n.en >= A) & (n.en < B)].pnl.sum())
        po = float(o[(o.en >= A) & (o.en < B)].pnl.sum())
        r = dict(ref=ref, n_new=int(len(nw)), n_ho26=int(len(ow)), n_match=match,
                 match_rate=match / max(len(nw), len(ow), 1), sum_pnl_s_new=pn, sum_pnl_s_ho26=po,
                 rel_dpnl=abs(pn - po) / abs(po) if po else None)
        r["pass"] = bool(r["match_rate"] >= 0.95 and r["rel_dpnl"] is not None and r["rel_dpnl"] <= 0.05)
        out[tag] = r
    out["PASS"] = all(out[t]["pass"] for t in SPEC)
    json.dump(out, open(W + "/mk/gate4.json", "w"), indent=1)
    log.info("GATE4 %s", json.dumps(out))


if __name__ == "__main__":
    c = sys.argv[1]
    {"submit": lambda: submit(sys.argv[2]), "status": lambda: status(sys.argv[2]), "fetch": lambda: fetch(sys.argv[2]),
     "compare": compare, "template": lambda: print(len(template()))}[c]()
