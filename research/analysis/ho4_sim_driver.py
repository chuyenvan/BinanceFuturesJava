#!/usr/bin/env python3
"""HO4-P3 cong sim (ADDENDUM-5 §5.3, 31e3c9e7): 2 kernel DEV `ho4-dev-{k24,b0}-s-s42` = cau hinh ho26-*-s-s42, SIM_END_DATE=20260101,
KHONG HOLDOUT_UNSEAL, thay tren S: ticker ngay UTC 2025-07-01..12-31 (kernel ho4-tk-copy, dung lai tu Vision), market.bin
(ho4-dev-mkt), pred.bin s42 (ho4-dev-pred), funding.bin dung lai TRONG kernel tu bins ho4-dev-bins (FUND_REBUILD_HO4 + tu kiem).
Template = tools/kaggle_sim.py HEAD (GA.template, guard NOWRITE242). So voi ho26-*-s-s42 dong start < 2026-01-01 00:00 +07.
Usage: ho4_sim_driver.py tkcopy | submit <tag> | status <tag> | fetch <tag> | compare"""
import hashlib, json, logging, os, re, subprocess, sys
R = "/home/ubuntu/src/BinanceFuturesJava"
sys.path.insert(0, R); sys.path.insert(0, R + "/research/analysis")
import gate_ablation_driver as GA  # noqa: E402
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout)
log = logging.getLogger("ho4_sim")
W = "/home/ubuntu/claude_master/1010/ho4"
OUT = "/home/ubuntu/kaggle_sim/out/%s/"
BUNDLE, JAR_DS = "sim-ho26a-bundle", "sim-jar-nsel"
JAR_SHA = "b7c89f097241763bb240c24b411a66531b41dad12b1716f13237537386de62c2"
PEN = "0.01675"
PRED_BASE = "22f69456381d9d1abd1592382c3b0319"
S_LO, S_HI = 1751302800000, 1767200400000
B0 = dict(GA.B0OV)
K24 = dict(B0, SELECTOR_RANK_TOPK=24, GATE_QUOTA_SKIP_WHEN_FULL="true")
SPEC = {"ho4-dev-k24-s-s42": (dict(K24, SIM_CRASH_ENTRY_PENALTY=PEN), "ho26-k24-s-s42"),
        "ho4-dev-b0-s-s42": (dict(B0, SIM_CRASH_ENTRY_PENALTY=PEN), "ho26-b0-s-s42")}
CODE_SHA = subprocess.run(["git", "-C", R, "rev-parse", "--short=8", "HEAD"], capture_output=True, text=True).stdout.strip()
TKCOPY = r'''"""HO4: copy ticker dung lai ngay UTC 2025-07-01..2025-12-31 tu output kernel ho4-dev-x (bo thang 6, khong config)."""
import glob, os, shutil, logging, sys, hashlib, json
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout)
fs = sorted(p for p in glob.glob("/kaggle/input/**/ticker_2025*.bin*", recursive=True) if "/ho4-dev-x/" in p)
keep = [p for p in fs if "20250701" <= os.path.basename(p)[7:15] <= "20251231"]
os.makedirs("/kaggle/working/tk", exist_ok=True)
man = {}
for p in keep:
    d = "/kaggle/working/tk/" + os.path.basename(p)
    shutil.copyfile(p, d)
    man[os.path.basename(p)] = hashlib.md5(open(d, "rb").read()).hexdigest()
json.dump(man, open("/kaggle/working/tk_md5.json", "w"), indent=0)
logging.info("TKCOPY %d/%d file", len(keep), len(fs))
'''


def E():
    sys.path.insert(0, W)
    import ho4_exp_kernel as e
    return e


def tkcopy():
    e = E()
    act = e.active()
    assert len(act) < 2, act
    fol = os.path.join(W, "kaggle", "ho4-tk-copy")
    os.makedirs(fol, exist_ok=True)
    open(os.path.join(fol, "run.py"), "w").write(TKCOPY)
    md = {"id": "chuyendinh/ho4-tk-copy", "title": "ho4-tk-copy", "code_file": "run.py", "language": "python",
          "kernel_type": "script", "is_private": True, "enable_gpu": False, "enable_internet": False,
          "dataset_sources": [], "competition_sources": [], "kernel_sources": ["chuyendinh/ho4-dev-x"]}
    json.dump(md, open(os.path.join(fol, "kernel-metadata.json"), "w"), indent=1)
    r = e.api().kernels_push(fol)
    log.info("PUSHED tkcopy %s", getattr(r, "url", r))


def template():
    t = GA.template()
    blk = open(W + "/ho4_fund_block.py").read()
    assert t.count(GA.PATCH_ANCHOR) == 1
    t = t.replace(GA.PATCH_ANCHOR, blk + GA.PATCH_ANCHOR)
    assert "NOWRITE_HOST" in t and "SYMBOL_MAPPER_PREFLIGHT_FAIL" in t and "FUND_HO4_OK" in t
    assert t.index("PRED_MD5_BASE") < t.index("FUND_HO4_OK") < t.index(GA.PATCH_ANCHOR)
    compile(t.replace("__CFG_JSON__", repr("{}")), "kernel", "exec")
    return t


def submit(tag):
    ks = GA.ks_mod()
    e = E()
    act = e.active()
    if len(act) >= 2:
        log.error("DA CO %d kernel dang chay %s", len(act), act); sys.exit(3)
    ch = json.load(open(W + "/chain/chain.json"))
    bm = json.load(open(W + "/chain/bins_md5.json"))
    ov, _ = SPEC[tag]
    ref = ks.kernel_ref(tag)
    folder = os.path.join(ks.WORKDIR, ks.slug(tag))
    os.makedirs(folder, exist_ok=True)
    cfg = {"tag": tag, "profile": GA.PROFILE, "overrides": dict(ov), "sim_end_date": "20260101", "xmx": "22g",
           "timeout_s": 7800, "code_sha": CODE_SHA, "bins_ds": "", "jar_ds": JAR_DS, "market_ds": "ho4-dev-mkt",
           "market_align": False, "extra_env": {}, "ticker_min_days": 1826,
           "pred_ds": "ho4-dev-pred", "want_pred_md5": ch["P_p15"]["pred_md5"], "want_pred_base": PRED_BASE,
           "fund_rebuild_ho4": {"lo": S_LO, "hi": S_HI, "folds": ["predict_wf_20250701.bin", "predict_wf_20251001.bin"],
                                "bins_ds": "ho4-dev-bins", "bins_md5": bm}}
    open(os.path.join(folder, "run.py"), "w").write(template().replace("__CFG_JSON__", repr(json.dumps(cfg))))
    tds = [d for d in ks.TICKER_DS if not d.endswith("/wfo-ticker-2025h2")]
    assert len(tds) == len(ks.TICKER_DS) - 1
    dss = [ks.USER + "/" + BUNDLE] + tds + [ks.USER + "/" + d for d in (JAR_DS, "ho4-dev-mkt", "ho4-dev-pred", "ho4-dev-bins")]
    md = {"id": ref, "title": ref.split("/")[1], "code_file": "run.py", "language": "python",
          "kernel_type": "script", "is_private": True, "enable_gpu": False, "enable_internet": True,
          "dataset_sources": dss, "competition_sources": [], "kernel_sources": ["chuyendinh/ho4-tk-copy"]}
    json.dump(md, open(os.path.join(folder, "kernel-metadata.json"), "w"), indent=1)
    r = ks._api().kernels_push(folder)
    log.info("PUSHED %s %s ov=%s", tag, getattr(r, "url", r), json.dumps(ov))


def status(tag):
    ks = GA.ks_mod()
    log.info("STATUS %s %s", tag, ks._status(ks.kernel_ref(tag)))


def kernel_text(tag):
    import glob
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
    ch = json.load(open(W + "/chain/chain.json"))
    pens = [float(x) for x in re.findall(r"\[CRASH-PENALTY\] SUMMARY penalty=([0-9.eE+-]+)", txt)]
    chk = dict(ok=rj.get("ok") is True, jar=rj.get("jar_sha256") == JAR_SHA,
               mapper=isinstance(rj.get("symbol_mapper"), int) and rj["symbol_mapper"] >= 800,
               ov=set(got) == set(ov) and all(str(got[k]) == str(v) for k, v in ov.items()),
               pred=rj.get("pred_md5_used") == ch["P_p15"]["pred_md5"] and rj.get("pred_md5_base") == PRED_BASE,
               fund="FUND_HO4_OK" in txt and "FUND_HO4_SELFCHECK keys_equal=True" in txt,
               market="market_ds=ho4-dev-mkt" in txt, no_unseal="HOLDOUT_UNSEAL DUNG" not in txt,
               pen=bool(pens) and all(abs(p - float(PEN)) < 1e-12 for p in pens), n=bool(rj.get("n_trades")))
    res = dict(tag=tag, chk=chk, ok_all=all(chk.values()), n=rj.get("n_trades"),
               fund_lines=[l[-220:] for l in txt.splitlines() if "FUND_HO4" in l][:6],
               ticker_line=[l[-200:] for l in txt.splitlines() if "ticker=" in l][:2])
    json.dump(res, open(W + "/check_%s.json" % tag, "w"), indent=1)
    log.info("FETCH %s %s", tag, json.dumps(res)[:1500])


def rows(path):
    L = open(path, errors="ignore").read().splitlines()
    hdr = L[0].split(",")
    i_st, i_en, i_sym, i_pnl = hdr.index("start"), hdr.index("end"), hdr.index("sym"), hdr.index("pnl")
    out = []
    for ln in L[1:]:
        p = ln.split(",")
        if len(p) <= i_pnl:
            continue
        out.append((ln, p[i_sym], p[i_st].strip(), p[i_en].strip(), float(p[i_pnl])))
    return out


def tmin(s):
    import datetime
    return int(datetime.datetime.strptime(s, "%Y%m%d %H:%M").timestamp() // 60)


def compare():
    """Thuoc §5.3: md5 dong start < 2026-01-01 00:00 +07; neu khac: trung lenh start in S (sym, |dstart|<=1') >= 99% VA
    |dSumPnL_S| <= 1% (end in S). Dong start < 2025-07-01 phai trung tung dong. KHONG doc so 2026."""
    SEAL, SLO = "20260101 00:00", "20250701 00:00"
    res = {}
    for tag, (_, ref) in SPEC.items():
        pn, pr = OUT % tag + "storage/printDone.csv", OUT % ref + "storage/printDone.csv"
        if not os.path.exists(pn):
            res[tag] = dict(missing=True); continue
        A = [r for r in rows(pn) if r[2] < SEAL]
        B = [r for r in rows(pr) if r[2] < SEAL]
        md = lambda X: hashlib.md5("\n".join(x[0] for x in X).encode()).hexdigest()
        pre_a, pre_b = [x[0] for x in A if x[2] < SLO], [x[0] for x in B if x[2] < SLO]
        r = dict(n_new=len(A), n_ref=len(B), md5_new=md(A), md5_ref=md(B), pre_rows_equal=pre_a == pre_b,
                 n_pre=len(pre_b))
        r["md5_equal"] = r["md5_new"] == r["md5_ref"]
        a = sorted([(x[1], tmin(x[2])) for x in A if x[2] >= SLO], key=lambda z: z[1])
        b = sorted([(x[1], tmin(x[2])) for x in B if x[2] >= SLO], key=lambda z: z[1])
        used, m = set(), 0
        idx = {}
        for j, (s, t) in enumerate(b):
            idx.setdefault(s, []).append((t, j))
        for s, t in a:
            for tb, j in idx.get(s, []):
                if j not in used and abs(tb - t) <= 1:
                    used.add(j); m += 1; break
        r.update(n_new_S=len(a), n_ref_S=len(b), matched=m, match_frac=m / max(1, len(a), len(b)))
        pa = sum(x[4] for x in A if SLO <= x[3] < SEAL); pb = sum(x[4] for x in B if SLO <= x[3] < SEAL)
        r["dpnl_rel"] = abs(pa - pb) / max(abs(pb), 1e-9)
        r["pass"] = bool(r["pre_rows_equal"] and (r["md5_equal"] or (r["match_frac"] >= 0.99 and r["dpnl_rel"] <= 0.01)))
        res[tag] = r
        log.info("SIM %s %s", tag, r)
    res["pass"] = all(v.get("pass") for k, v in res.items() if isinstance(v, dict))
    json.dump(res, open(W + "/sim_gate.json", "w"), indent=1)


if __name__ == "__main__":
    a = sys.argv[1]
    if a == "tkcopy":
        tkcopy()
    elif a == "compare":
        compare()
    else:
        {"submit": submit, "status": status, "fetch": fetch}[a](sys.argv[2])
