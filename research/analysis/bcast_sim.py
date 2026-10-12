#!/usr/bin/env python3
"""BCAST (PREREG_BACKCAST_RESERVOIR 596c1ef8 §5): sim KY THUAT duy nhat `bcast-tech` tren kho 2020 — CHI kiem sim chay duoc.
Template = gate_ablation_driver.template() (tools/kaggle_sim.py HEAD NOWRITE242 + pred_ds) + khoi BCAST (TIME_RUN, ticker kho md5)
+ ho4p1_fund_block.py (funding.bin dung trong kernel tu bins kho; tu kiem DEV giu nguyen). KHONG mo printDone/equity:
output tai thang vao ~/kaggle_sim/sealed/bcast-tech (chmod 700); chi doc md5 + so dong printDone + cac khoa ky thuat cua result.json.
Usage: bcast_sim.py push <arts.json> | fetch | check"""
import glob, hashlib, json, logging, os, re, subprocess, sys
R = "/home/ubuntu/src/BinanceFuturesJava"
sys.path.insert(0, R)
sys.path.insert(0, R + "/research/analysis")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout)
log = logging.getLogger("bcast_sim")
import gate_ablation_driver as GA  # noqa: E402
import bcast_exp_kernel as E  # noqa: E402
TAG, SEALED = "bcast-tech", "/home/ubuntu/kaggle_sim/sealed/bcast-tech"
W = "/home/ubuntu/claude_master/1012/bcast"
BUNDLE, JAR_DS = "sim-ho26a-bundle", "sim-jar-nsel"
JAR_SHA = "b7c89f097241763bb240c24b411a66531b41dad12b1716f13237537386de62c2"
PRED_BASE = "22f69456381d9d1abd1592382c3b0319"
S_LO = 1577811600000
BLK_BCAST = r'''# [BCAST 596c1ef8] TIME_RUN kho 2020: sua TIME_RUN trong BAN COPY config.properties cua BUNDLE (bundle giu nguyen);
#   chon dung file cua bundle (kernel_sources exporter cung co config.properties). Ticker: CHI file tu kernel exporter kho, md5 RAW.
_TR = CFG.get("bcast_time_run") or ""
if _TR:
    _cc = [c for c in sorted(glob.glob(IN + "/**/config.properties", recursive=True)) if ("/" + CFG["bcast_bundle"] + "/") in c]
    if len(_cc) != 1:
        LOG.error("BCAST_CFG_FAIL %s", _cc); sys.exit(2)
    _o, _n = [], 0
    for _ln in open(_cc[0], "rb").read().splitlines(True):
        if re.match(rb"\s*TIME_RUN\s*=", _ln):
            _o.append(b"TIME_RUN=" + _TR.encode() + (b"\r\n" if _ln.endswith(b"\r\n") else b"\n")); _n += 1
        else:
            _o.append(_ln)
    if _n != 1:
        LOG.error("BCAST_TIME_RUN_FAIL n=%d", _n); sys.exit(2)
    os.makedirs("/tmp/bcast_cfg", exist_ok=True)
    open("/tmp/bcast_cfg/config.properties", "wb").write(b"".join(_o))
    LOG.info("BCAST_TIME_RUN=%s cfg_goc=%s cfgp_truoc=%s", _TR, _cc[0], cfgp)
    cfgp = "/tmp/bcast_cfg/config.properties"
_TB = CFG.get("tk_bcast") or {}
if _TB:
    import gzip as _gz
    _want = _TB["md5"]
    _all = [p for p in glob.glob(IN + "/**/ticker_2*.bin*", recursive=True) if os.path.isfile(p)]
    _mine = {os.path.basename(p).replace(".gz", ""): p for p in _all if ("/" + _TB["src"] + "/") in p}
    _other = [p for p in _all if ("/" + _TB["src"] + "/") not in p]
    def _rawmd5(_p):
        return _h3.md5(_gz.open(_p).read() if _p.endswith(".gz") else open(_p, "rb").read()).hexdigest()
    _tok = [n for n in sorted(_want) if n in _mine and _rawmd5(_mine[n]) == _want[n]]
    _tmiss = [n for n in sorted(_want) if n not in _mine]
    _textra = sorted(n for n in _mine if n not in _want)
    LOG.info("TICKER_BCAST ok=%d bad=%d miss=%d extra=%d other=%d", len(_tok), len(_want) - len(_tok) - len(_tmiss), len(_tmiss),
             len(_textra), len(_other))
    if len(_tok) != len(_want) or _textra or _other:
        LOG.error("TICKER_BCAST_FAIL"); sys.exit(1)
'''


def template():
    t = GA.template()
    fb = open(R + "/research/analysis/ho4p1_fund_block.py").read()
    # [BCAST] lo = 2020 < moi ban ghi bundle => doan tu kiem DEV [self_lo, self_hi) nam trong vong "mid" (khong phai prefix):
    #   thu _rs ca o vong mid (logic tu kiem + du lieu giu nguyen; ban goc chi thu o prefix -> n_old=0 -> FAIL gia).
    o1 = """        if _t >= _hi:
            break
        _p += 12 + 8 * _c; _nmid += 1"""
    n1 = """        if _t >= _hi:
            break
        if _slo <= _t < _shi:
            _rs[_t] = _oraw[_p:_p + 12 + 8 * _c]
        _p += 12 + 8 * _c; _nmid += 1"""
    assert fb.count(o1) == 1
    blk = BLK_BCAST + fb.replace(o1, n1)
    assert t.count(GA.PATCH_ANCHOR) == 1
    t = t.replace(GA.PATCH_ANCHOR, blk + GA.PATCH_ANCHOR)
    assert "NOWRITE_HOST" in t and "SYMBOL_MAPPER_PREFLIGHT_FAIL" in t and "FUND_HO4_OK" in t and "TICKER_BCAST_FAIL" in t
    assert t.index("PRED_MD5_BASE") < t.index("BCAST_TIME_RUN") < t.index("FUND_HO4_OK") < t.index(GA.PATCH_ANCHOR)
    assert t.index(GA.PATCH_ANCHOR) < t.index("NOWRITE_HOST = ")
    compile(t.replace("__CFG_JSON__", repr("{}")), "kernel", "exec")
    return t


def push(artsp):
    import tools.kaggle_sim as ks
    act = E.active()
    if len(act) >= 2 or any("/bcast-" in x for x in act):
        log.error("KHONG DAY: dang chay %s", act); sys.exit(3)
    A = json.load(open(artsp))
    assert len(A["tk_md5"]) == 369 and len(A["bins_md5"]) == 4
    fund = {"lo": S_LO, "hi": 9 * 10**15, "self_lo": 1751302800000, "self_hi": 1767200400000,
            "self_folds": ["predict_wf_20250701.bin", "predict_wf_20251001.bin"],
            "new_folds": sorted(A["bins_md5"]), "bins_ds": "bins", "bins_md5": A["bins_md5"]}
    code_sha = subprocess.run(["git", "-C", R, "rev-parse", "--short=8", "HEAD"], capture_output=True, text=True).stdout.strip()
    cfg = {"tag": TAG, "profile": GA.PROFILE, "overrides": dict(GA.B0OV), "sim_end_date": "20210101", "xmx": "22g",
           "timeout_s": 10800, "code_sha": code_sha, "bins_ds": "", "jar_ds": JAR_DS, "market_ds": A["chain_slug"],
           "market_align": False, "extra_env": {}, "ticker_min_days": 369, "pred_ds": "pred_s42",
           "want_pred_md5": A["pred_s42"], "want_pred_base": PRED_BASE, "bcast_time_run": "20200101", "bcast_bundle": BUNDLE,
           "tk_bcast": {"src": A["x_slug"], "md5": A["tk_md5"]}, "fund_rebuild_ho4p1": fund}
    folder = os.path.join(W, "kaggle", TAG)
    os.makedirs(folder, exist_ok=True)
    open(folder + "/run.py", "w").write(template().replace("__CFG_JSON__", repr(json.dumps(cfg))))
    md = {"id": ks.USER + "/" + TAG, "title": TAG, "code_file": "run.py", "language": "python", "kernel_type": "script",
          "is_private": True, "enable_gpu": False, "enable_internet": True,
          "dataset_sources": [ks.USER + "/" + BUNDLE, ks.USER + "/" + JAR_DS], "competition_sources": [],
          "kernel_sources": [ks.USER + "/" + A["chain_slug"], ks.USER + "/" + A["x_slug"]]}
    json.dump(md, open(folder + "/kernel-metadata.json", "w"), indent=1)
    json.dump(cfg, open(W + "/cfg_bcast-tech.json", "w"), indent=1)
    r = ks._api().kernels_push(folder)
    log.info("PUSHED %s %s (active truoc %s)", TAG, getattr(r, "url", r), act)


def fetch():
    import requests
    os.makedirs(SEALED, exist_ok=True)
    os.chmod(os.path.dirname(SEALED), 0o700) if os.path.basename(os.path.dirname(SEALED)) == "sealed" else None
    os.chmod(SEALED, 0o700)
    a = E.api()
    resp = a.process_response(a.kernel_output_with_http_info(E.USER, TAG))
    for it in resp["files"]:
        p = os.path.join(SEALED, it["fileName"])
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with requests.get(it["url"], stream=True, timeout=600) as r:
            r.raise_for_status()
            with open(p, "wb") as f:
                for b in r.iter_content(1 << 22):
                    f.write(b)
    if resp.get("log"):
        open(os.path.join(SEALED, TAG + ".log"), "w").write(resp["log"])
    subprocess.run(["chmod", "-R", "go-rwx", SEALED], check=True)
    log.info("FETCHED %d file -> %s (chmod 700)", len(resp["files"]), SEALED)


ALLOWED = ("tag", "java_rc", "secs", "ok", "n_trades", "symbol_mapper", "jar_sha256", "pred_md5_base", "pred_md5_used",
           "date_first", "date_last", "overrides", "profile_hash")
MARKERS = {"tk": r"TICKER_BCAST ok=369 bad=0 miss=0 extra=0 other=0", "time_run": r"BCAST_TIME_RUN=20200101 ",
           "fund_self": r"FUND_HO4_SELFCHECK keys_equal=True", "fund_ok": r"FUND_HO4_OK md5_funding=(\w+)",
           "fund_cnt": r"FUND_HO4 prefix=(\d+) mid_old=(\d+) mid_new=(\d+) suffix=(\d+)", "market": r"market_ds=bcast-ch20-a",
           "mapper": r"Loaded Symbol Mapper: (\d+) symbols", "nowrite": r"NOWRITE242 AEROSPIKE_HOST"}


def md5f(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def check():
    """Chi khoa ky thuat; KHONG doc truong equity/b, KHONG in dong log nao."""
    rj = json.load(open(SEALED + "/result.json"))
    out = {k: rj.get(k) for k in ALLOWED}
    txt = ""
    for p in [SEALED + "/logs/sim.out", SEALED + "/" + TAG + ".log"]:
        if os.path.exists(p):
            raw = open(p, errors="ignore").read()
            try:
                raw = "".join(x.get("data", "") for x in json.loads(raw))
            except Exception:  # noqa: BLE001
                pass
            txt += raw
    mk = {}
    for k, rx in MARKERS.items():
        m = re.search(rx, txt)
        mk[k] = (list(m.groups()) if m.groups() else True) if m else False
    pd_ = SEALED + "/storage/printDone.csv"
    n_lines = sum(1 for _ in open(pd_, "rb")) if os.path.exists(pd_) else None
    out.update(markers=mk, printDone_md5=md5f(pd_) if os.path.exists(pd_) else None, printDone_lines=n_lines,
               files=sorted(os.path.relpath(p, SEALED) for p in glob.glob(SEALED + "/**/*", recursive=True) if os.path.isfile(p)))
    chk = dict(ok=out["ok"] is True, jar=out["jar_sha256"] == JAR_SHA, mapper=isinstance(out["symbol_mapper"], int) and out["symbol_mapper"] >= 800,
               tk=bool(mk["tk"]), time_run=bool(mk["time_run"]), fund=bool(mk["fund_self"]) and bool(mk["fund_ok"]),
               market=bool(mk["market"]), pred_base=out["pred_md5_base"] == PRED_BASE, n=bool(out["n_trades"]),
               date_first=str(out["date_first"]).startswith("202001"), date_last=str(out["date_last"])[:4] == "2020" or str(out["date_last"]) == "20210101")
    out["chk"] = chk
    out["pass"] = all(chk.values())
    json.dump(out, open(W + "/bcast_tech_check.json", "w"), indent=1, sort_keys=True)
    log.info("CHECK pass=%s chk=%s rc=%s n=%s lines=%s md5=%s", out["pass"], chk, out["java_rc"], out["n_trades"], n_lines, out["printDone_md5"])


if __name__ == "__main__":
    {"push": lambda: push(sys.argv[2]), "fetch": fetch, "check": check}[sys.argv[1]]()
