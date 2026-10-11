#!/usr/bin/env python3
"""HO4-P1 P3-DEV sim (ADDENDUM-6 §6.3, CHI BAO): 2 kernel DEV `ho4p1-dev-{k24,b0}-s-s42` = cau hinh ho26-*-s-s42,
SIM_END_DATE=20260101, KHONG HOLDOUT_UNSEAL; thay tren S: ticker ngay UTC 2025-07-01..12-31 (kernel ho4p1-tkdev tu det-a),
market.bin (chdet-a), pred.bin s42 xap xi (a) (ho4p1-devcmp), funding.bin dung TRONG kernel tu bins chdet-a (FUND_REBUILD_HO4P1:
lo=S_LO, hi=SEAL; tu kiem tren [2025-01-01, S_LO) voi bins DEV fold 20250101/20250401). So voi ho26-*-s-s42 dong start < SEAL.
Usage: ho4p1_simdev.py tkdev | submit <tag> | fetch <tag> | compare"""
import hashlib, json, logging, os, subprocess, sys
R = "/home/ubuntu/src/BinanceFuturesJava"
sys.path.insert(0, R); sys.path.insert(0, R + "/research/analysis")
import gate_ablation_driver as GA  # noqa: E402
import ho4_sim_driver as SD  # noqa: E402
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout)
log = logging.getLogger("ho4p1_simdev")
W = "/home/ubuntu/claude_master/1011/ho4p1"
OUT = "/home/ubuntu/kaggle_sim/out/%s/"
BUNDLE, JAR_DS = "sim-ho26a-bundle", "sim-jar-nsel"
PEN = "0.01675"
PRED_BASE = "22f69456381d9d1abd1592382c3b0319"
S_LO, SEAL = 1751302800000, 1767200400000
B0 = dict(GA.B0OV)
K24 = dict(B0, SELECTOR_RANK_TOPK=24, GATE_QUOTA_SKIP_WHEN_FULL="true")
SPEC = {"ho4p1-dev-k24-s-s42": (dict(K24, SIM_CRASH_ENTRY_PENALTY=PEN), "ho26-k24-s-s42"),
        "ho4p1-dev-b0-s-s42": (dict(B0, SIM_CRASH_ENTRY_PENALTY=PEN), "ho26-b0-s-s42")}
CODE_SHA = subprocess.run(["git", "-C", R, "rev-parse", "--short=8", "HEAD"], capture_output=True, text=True).stdout.strip()
TKDEV = SD.TKCOPY.replace("/ho4-dev-x/", "/ho4p1-det-a/").replace('"""HO4:', '"""HO4-P1:')


def tkdev():
    import ho4p1_exp_kernel as E
    assert len(E.active()) < 2
    fol = W + "/kaggle/ho4p1-tkdev"
    os.makedirs(fol, exist_ok=True)
    open(fol + "/run.py", "w").write(TKDEV)
    md = {"id": "chuyendinh/ho4p1-tkdev", "title": "ho4p1-tkdev", "code_file": "run.py", "language": "python", "kernel_type": "script",
          "is_private": True, "enable_gpu": False, "enable_internet": False, "dataset_sources": [], "competition_sources": [],
          "kernel_sources": ["chuyendinh/ho4p1-det-a"]}
    json.dump(md, open(fol + "/kernel-metadata.json", "w"), indent=1)
    r = E.api().kernels_push(fol)
    log.info("PUSHED tkdev %s", getattr(r, "url", r))


def template():
    t = GA.template()
    blk = open(R + "/research/analysis/ho4p1_fund_block.py").read()
    t = t.replace(GA.PATCH_ANCHOR, blk + GA.PATCH_ANCHOR)
    assert "NOWRITE_HOST" in t and "FUND_HO4_OK" in t and t.index("PRED_MD5_BASE") < t.index("FUND_HO4_OK") < t.index(GA.PATCH_ANCHOR)
    compile(t.replace("__CFG_JSON__", repr("{}")), "kernel", "exec")
    return t


def submit(tag):
    import ho4p1_exp_kernel as E
    ks = GA.ks_mod()
    assert len(E.active()) < 2
    E.fetch("ho4p1-devcmp", r"(^|/)devcmp\.json$")
    E.fetch("ho4p1-chdet-a", r"(^|/)MANIFEST\.json$")
    dc = json.load(open(W + "/kaggle/out/ho4p1-devcmp/out/devcmp.json"))
    man = json.load(open(W + "/kaggle/out/ho4p1-chdet-a/out/MANIFEST.json"))
    ov, _ = SPEC[tag]
    ref = ks.kernel_ref(tag)
    folder = os.path.join(ks.WORKDIR, ks.slug(tag))
    os.makedirs(folder, exist_ok=True)
    fund = {"lo": S_LO, "hi": SEAL, "self_lo": 1735664400000, "self_hi": S_LO,
            "self_folds": ["predict_wf_20250101.bin", "predict_wf_20250401.bin"],
            "new_folds": ["predict_wf_20250701.bin", "predict_wf_20251001.bin"], "bins_ds": "bins",
            "bins_md5": {"predict_wf_%s.bin" % c: man["bins/predict_wf_%s.bin" % c]["md5"] for c in ("20250701", "20251001")}}
    cfg = {"tag": tag, "profile": GA.PROFILE, "overrides": dict(ov), "sim_end_date": "20260101", "xmx": "22g",
           "timeout_s": 7800, "code_sha": CODE_SHA, "bins_ds": "", "jar_ds": JAR_DS, "market_ds": "ho4p1-chdet-a",
           "market_align": False, "extra_env": {}, "ticker_min_days": 1826, "pred_ds": "pred_simdev",
           "want_pred_md5": dc["pred_simdev"]["md5"], "want_pred_base": PRED_BASE, "fund_rebuild_ho4p1": fund}
    open(os.path.join(folder, "run.py"), "w").write(template().replace("__CFG_JSON__", repr(json.dumps(cfg))))
    tds = [d for d in ks.TICKER_DS if not d.endswith("/wfo-ticker-2025h2")]
    md = {"id": ref, "title": ref.split("/")[1], "code_file": "run.py", "language": "python", "kernel_type": "script",
          "is_private": True, "enable_gpu": False, "enable_internet": True,
          "dataset_sources": [ks.USER + "/" + BUNDLE] + tds + [ks.USER + "/" + JAR_DS], "competition_sources": [],
          "kernel_sources": ["chuyendinh/ho4p1-tkdev", "chuyendinh/ho4p1-chdet-a", "chuyendinh/ho4p1-devcmp"]}
    json.dump(md, open(os.path.join(folder, "kernel-metadata.json"), "w"), indent=1)
    r = ks._api().kernels_push(folder)
    log.info("PUSHED %s %s", tag, getattr(r, "url", r))


def compare():
    SD.SPEC.clear(); SD.SPEC.update(SPEC)
    SD.W = W
    SD.compare()


if __name__ == "__main__":
    a = sys.argv[1]
    if a == "tkdev":
        tkdev()
    elif a == "compare":
        compare()
    elif a == "fetch":
        GA.ks_mod().fetch(sys.argv[2])
    else:
        submit(sys.argv[2])
