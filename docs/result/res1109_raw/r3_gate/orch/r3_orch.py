#!/usr/bin/env python3
"""NUP4-fix orchestrator TAT DINH (PREREG_NUP4 ADDENDUM-2, commit 6011cefb). Viet boi audit Opus 10-31; claw KHONG chay.

  python3 nup4_orch.py run      # vong lap: B0 jar dataset -> B1 gate s42 -> B2 B0 7 seed + Pha 1a -> B3 MTM -> B4 tong hop
  python3 nup4_orch.py dry      # in ke hoach, sec check, Kaggle auth, kiem du lieu tham chieu, selftest MTM; KHONG push
  python3 nup4_orch.py status
Dung o cuoi Pha 1a (KHONG tu chay 1b). Moi loi (kernel ERROR, check lech, md5 lech, missing>0) => _halt, thoat.
Resume: chay lai 'run' (bo qua run DONE theo state). _halt chi go bang 'clearhalt' sau khi MASTER xem.
Oracle: chi poll >= 60 s/lan, keo file nho theo regex, khong Aerospike, khong cron. Ngay 2026-11-03 (+07): chi poll.
"""
import datetime as dt
import hashlib
import json
import logging
import os
import re
import shutil
import signal
import subprocess
import sys
import time

FX = "/home/ubuntu/claude_master/res1109/r3_gate"
OD = FX + "/orch_m2r"      # [ADD-3] chay lai 8 run M2 + MTM (resume rieng)
RES = FX + "/results"
STATE = OD + "/state.json"
MANIFEST = OD + "/manifest.jsonl"
os.makedirs(OD, exist_ok=True)
os.makedirs(RES, exist_ok=True)

R = "/home/ubuntu/src/BinanceFuturesJava"
sys.path.insert(0, R)
sys.path.insert(0, R + "/research/analysis")
import gate_ablation_driver as GA  # noqa: E402
import ho4p1_queue as Q            # noqa: E402
import gate_skipfull_driver as G   # noqa: E402

KS = Q.GA.ks_mod()                 # tools/kaggle_sim.py HEAD (guard NOWRITE242 da assert)
USER = KS.USER

# logger RIENG (propagate=False) dat SAU moi import => module khac goi basicConfig(force=True) khong xoa duoc.
log = logging.getLogger("r3orch")
log.setLevel(logging.INFO)
log.propagate = False
for _h in list(log.handlers):
    log.removeHandler(_h)
_fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
for _h in (logging.FileHandler(OD + "/orch.log"), logging.StreamHandler(sys.stdout)):
    _h.setFormatter(_fmt)
    log.addHandler(_h)

# ---------------------------------------------------------------- retry Kaggle (3 lan trong <= 10 phut)
RETRY_WAITS = (30, 90, 240)          # backoff giua cac lan: tong 6 phut < 10 phut


class Fatal(RuntimeError):
    """Loi KHONG tam thoi (4xx khac 403/429...) => khong retry."""


def _http_code(ex):
    for a in ("status", "status_code"):
        v = getattr(ex, a, None)
        if isinstance(v, int):
            return v
    r = getattr(ex, "response", None)
    v = getattr(r, "status_code", None) or getattr(r, "status", None)
    if isinstance(v, int):
        return v
    m = re.search(r"\((\d{3})\)", str(ex)) or re.search(r"\b(\d{3}) Client Error|\b(\d{3}) Server Error", str(ex))
    if m:
        return int([g for g in m.groups() if g][0])
    return None


def transient(ex, retry403=True):
    if isinstance(ex, Fatal):
        return False
    c = _http_code(ex)
    if c is None:
        return True                    # mang/timeout/protocol: coi la tam thoi
    return (c == 403 and retry403) or c in (408, 429) or c >= 500


def kcall(desc, fn, *a, retry403=True, **kw):
    """Goi Kaggle voi retry: lan 1 + 3 lan thu lai (cho 30/90/240 s). Loi khong tam thoi => nem ngay."""
    for i in range(len(RETRY_WAITS) + 1):
        try:
            return fn(*a, **kw)
        except Exception as ex:  # noqa: BLE001
            if not transient(ex, retry403) or i == len(RETRY_WAITS):
                log.error("KAGGLE %s THAT BAI (lan %d, code=%s): %s", desc, i + 1, _http_code(ex), str(ex)[:200])
                raise
            log.warning("KAGGLE %s loi tam thoi (lan %d, code=%s) — cho %ds: %s", desc, i + 1, _http_code(ex),
                        RETRY_WAITS[i], str(ex)[:120])
            time.sleep(RETRY_WAITS[i])

# ---------------------------------------------------------------- hang so (chot truoc khi chay)
JAR = FX + "/jar/sim.jar"
JAR_SHA = "9f2401096930d114b11662185c2d2f580720343e186a5fc19676903076df9498"
CODE_SHA = "12f3b1b641d05f0d97ca8b8fa47adfbf08007703"       # fix/nup4-audit (build_stub_jar.sh, full test)
JAR_DS = "sim-jar-r3g3"
PROF = "/home/ubuntu/kaggle_sim/push_jar_nsel/prof_r4_kg0_k16_f015_g155.properties"
SEC1 = "/home/ubuntu/claude_master/vz_e1_wt/research/nup3/jar_sec_check.py"
SEC2 = "/home/ubuntu/claude_master/nup4_fix/jar_sec_check_tg.py"
ARTS = json.load(open("/home/ubuntu/claude_master/ho_tradfi_wk/arts_nt.json"))
CHAIN, TKK = ARTS["chain_slug"], ARTS["tk_slug"]
FUND = dict(Q.FUND, bins_md5=ARTS["bins_md5"])
END = "20261001"
MAXPAR, POLL_S = 1, 120
KOUT = "/home/ubuntu/kaggle_sim/out/"
GQ_CSV = "/home/ubuntu/claude_master/vz_e1_wt/docs/result/golive_quarterly/quarterly_x14_by_seed.csv"
KLINE_DS = [USER + "/vz-kline1m-%d" % y for y in range(2021, 2027)]
MTM_SRC = OD + "/mtm_kernel.py"
MTM_BATCH, MTM_TOL_PP = 9, 0.01
NO_HEAVY_DAY = "2026-11-03"
PRIO = "/home/ubuntu/claude_master/locks/kaggle_priority"   # co file => KHONG push (job seed gate dry 11-03 uu tien)
FETCH403_MAX_S = 7200                                       # 403 khi tai output = chua san sang; toi da 2 h/kernel
_PRIO_LOG = {"t": 0.0}
RES_MAX_MB = 200
FETCH_RX = (r"^(result\.json|prof_run\.properties|storage/(printDone\.csv|equity_day\.csv|equity_summary\.json|"
            r"leg_owner\.csv|merge_log\.csv|sleeve_summary\.json)|mtm_result\.json|mtm_eq_daily_close07\.json)$")

FLAGS25 = json.load(open("/home/ubuntu/claude_master/tsx/flags.json"))["ranges"]
FLAGS26 = "20260205-20260214,20260216-20260217,20260224-20260225,20260606-20260607,20260610-20260611"
X14 = FLAGS25 + "," + FLAGS26
BASE = dict(GA.B0OV, SELECTOR_RANK_TOPK=24, GATE_QUOTA_SKIP_WHEN_FULL="true",
            SIM_LOSER_TS_EXT_HOURS=336, SIM_LOSER_TS_EXT_DAYS=X14, KILLSW_A40_DD=0.40)
SLV = dict(SLEEVE_ENABLED="true", SLEEVE_PCT=0.99985, SLEEVE_U_MAX=0.35, SLEEVE_ARM="V1",
           SLEEVE_BURST_N=10, SLEEVE_BURST_MIN=60)
ARMS = {"b0": dict(BASE, SLEEVE_ENABLED="false", MERGE_MODE="NONE"),
        "s1b": dict(BASE, SLEEVE_SIZE_MULT=0.574, MERGE_MODE="NONE", **SLV),
        "m1a": dict(BASE, SLEEVE_SIZE_MULT=0.574, MERGE_MODE="M1", **SLV),
        "m1b": dict(BASE, SLEEVE_SIZE_MULT=0.45, MERGE_MODE="M1", **SLV),
        "m2a": dict(BASE, SLEEVE_SIZE_MULT=0.574, MERGE_MODE="M2", **SLV),
        "m2b": dict(BASE, SLEEVE_SIZE_MULT=0.45, MERGE_MODE="M2", **SLV)}
# [R3] prereg PREREG_R3_GATE_FAMILY b901016e: g0 = b0 tren jar R3 (kiem byte-identical n4f-b0); g3 = MTF-OR {1,15} c=0,5 minCov 12
ARMS["g0"] = dict(ARMS["b0"])
ARMS["g3"] = dict(ARMS["b0"], SIM_GATE_MTF_W=15, SIM_GATE_MTF_C=0.5, SIM_GATE_MTF_MINCOV=12)
SEED_NAME = {42: "a1", 7: "s7", 13: "s13", 21: "s21", 99: "s99", 123: "s123", 777: "s777", 2024: "s2024"}
P1A_SEEDS = [42, 7, 21, 99]
B0_REST = [7, 21, 99, 13, 123, 777, 2024]
VARIANTS = ["s1b", "m1a", "m1b", "m2a", "m2b"]


def kslug(tag):
    """slug KERNEL tren Kaggle (co tien to 'sim-'). KS.slug() KHONG co tien to — dung no goi API = 403 (sai id)."""
    return KS.kernel_ref(tag).split("/")[1]


def tag_of(arm, seed):
    return "r3%s-%s" % (arm, SEED_NAME[seed])


def plan():
    """[ADD-3] gate = n4f-b0-a1 (DONE, chep tu orch cu, chi lam doi chung MTM) + 8 run M2 moi (jar sua active-id)."""
    P = [dict(tag="n4f-b0-a1", arm="b0", seed=42, phase="gate")]
    P += [dict(tag="n4g-%s-%s" % (a, SEED_NAME[s_]), arm=a, seed=s_, phase="p1a") for s_ in P1A_SEEDS for a in ("m2a", "m2b")]
    return P


def mtm_batches():
    tags = [e["tag"] for e in plan()]
    gate = tags[0]
    rest = tags[1:]
    out = []
    for i in range(0, len(rest), MTM_BATCH):
        out.append(dict(tag="n4g-mtm-b%d" % (len(out) + 1), runs=[gate] + rest[i:i + MTM_BATCH]))
    return out


def now7():
    return dt.datetime.utcnow() + dt.timedelta(hours=7)


def light_only():
    if os.environ.get("NUP4_ALLOW_1103") == "1":      # MASTER go cam 11-03 (deploy dry xong 10:38)
        return False
    return now7().strftime("%Y-%m-%d") == NO_HEAVY_DAY


def load_state():
    return json.load(open(STATE)) if os.path.exists(STATE) else {}


def save_state(st):
    tmp = STATE + ".tmp"
    json.dump(st, open(tmp, "w"), indent=1)
    os.replace(tmp, STATE)


def halt(st, why):
    st["_halt"] = {"why": why, "at": now7().strftime("%F %T")}
    save_state(st)
    log.error("HALT: %s", why)


def fhash(p, algo):
    h = hashlib.new(algo)
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def sec_check(jar, tag):
    j1, j2 = OD + "/sec1_%s.json" % tag, OD + "/sec2_%s.json" % tag
    r1 = subprocess.call([sys.executable, "-I", SEC1, jar, j1], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    with open(j2, "w") as f:
        r2 = subprocess.call([sys.executable, "-I", SEC2, jar], stdout=f, stderr=subprocess.DEVNULL)
    ok1 = r1 == 0 and json.load(open(j1)).get("ok") is True
    ok2 = r2 == 0 and all(v["ok"] for v in json.load(open(j2)).values())
    log.info("SEC %s jar_sec_check=%s tg=%s", tag, ok1, ok2)
    return ok1 and ok2


# ---------------------------------------------------------------- B0: dataset jar
def jards(dry=False):
    assert fhash(JAR, "sha256") == JAR_SHA, "jar sha lech JAR_SHA"
    assert fhash(PROF, "md5") == G.PROF_MD5, "profile md5 lech"
    if not sec_check(JAR, "build"):
        raise RuntimeError("SEC CHECK jar build FAIL")
    if dry:
        return True
    fol = OD + "/ds_" + JAR_DS
    if not os.path.exists(fol + "/JAR_SHA.json"):
        os.makedirs(fol, exist_ok=True)
        shutil.copy(JAR, fol + "/sim.jar")
        shutil.copy(PROF, fol + "/" + os.path.basename(PROF))
        assert fhash(fol + "/sim.jar", "sha256") == JAR_SHA
        if not sec_check(fol + "/sim.jar", "upload"):
            raise RuntimeError("SEC CHECK jar upload FAIL")
        json.dump({"sim.jar_sha256": JAR_SHA, "profile": os.path.basename(PROF), "privateconfig": "STUB",
                   "telegram": "STUB", "code_sha": CODE_SHA}, open(fol + "/JAR_SHA.json", "w"))
        json.dump({"title": JAR_DS, "id": USER + "/" + JAR_DS, "licenses": [{"name": "CC0-1.0"}]},
                  open(fol + "/dataset-metadata.json", "w"))
        r = kcall("dataset_create", KS._api().dataset_create_new, fol, public=False, quiet=True, dir_mode="skip")
        log.info("dataset %s (private) -> %s", JAR_DS, getattr(r, "url", r))
    for _ in range(60):
        try:
            s = str(kcall("dataset_status", KS._api().dataset_status, USER + "/" + JAR_DS))
        except Exception as e:  # noqa: BLE001
            s = "err " + str(e)[:60]
        if "ready" in s.lower():
            return True
        time.sleep(60)
    raise RuntimeError("dataset jar khong ready")


# ---------------------------------------------------------------- push sim
def template():
    t = GA.template()
    assert t.count(GA.PATCH_ANCHOR) == 1
    t = t.replace(GA.PATCH_ANCHOR, Q.BLK + GA.PATCH_ANCHOR)
    assert "TICKER_HO4P1_FAIL" in t and "FUND_HO4_OK" in t and "NOWRITE_HOST" in t
    compile(t.replace("__CFG_JSON__", repr("{}")), "kernel", "exec")
    return t


def sim_cfg(e):
    return {"tag": e["tag"], "profile": GA.PROFILE, "overrides": ARMS[e["arm"]], "sim_end_date": END, "xmx": "22g",
            "timeout_s": 10800, "code_sha": CODE_SHA, "bins_ds": "", "jar_ds": JAR_DS, "market_ds": CHAIN,
            "market_align": False, "extra_env": {"HOLDOUT_UNSEAL": Q.UNSEAL}, "ticker_min_days": 2099,
            "pred_ds": "pred_s%d" % e["seed"], "want_pred_md5": ARTS["preds"][str(e["seed"])],
            "want_pred_base": Q.PRED_BASE, "tk_ho4p1": {"src": TKK, "md5": ARTS["tk_md5"]},
            "fund_rebuild_ho4p1": FUND}


def kpush(tag, code, md):
    folder = os.path.join(KS.WORKDIR, KS.slug(tag))
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, "run.py"), "w") as f:
        f.write(code)
    json.dump(md, open(os.path.join(folder, "kernel-metadata.json"), "w"), indent=1)
    def _once():
        try:
            st_ = KS._status(KS.kernel_ref(tag))
        except Exception:  # noqa: BLE001
            st_ = None
        if st_ in ("RUNNING", "QUEUED", "COMPLETE"):
            log.warning("kpush %s: kernel da ton tai (%s) sau lan thu truoc => khong push lai", tag, st_)
            return
        r = KS._api().kernels_push(folder)
        err = getattr(r, "error", None) or getattr(r, "errorMessage", None)
        if err or not getattr(r, "url", None):
            raise Fatal("kernels_push %s bi tu choi: %s" % (tag, err or r))
    kcall("push " + tag, _once)


def push_sim(st, e):
    ref = KS.kernel_ref(e["tag"])
    code = template().replace("__CFG_JSON__", repr(json.dumps(sim_cfg(e))))
    md = {"id": ref, "title": ref.split("/")[1], "code_file": "run.py", "language": "python",
          "kernel_type": "script", "is_private": True, "enable_gpu": False, "enable_internet": True,
          "dataset_sources": [USER + "/" + Q.BUNDLE] + KS.TICKER_DS + [USER + "/" + JAR_DS],
          "competition_sources": [], "kernel_sources": [USER + "/" + CHAIN, USER + "/" + TKK]}
    kpush(e["tag"], code, md)
    st[e["tag"]] = dict(state="PUSHED", kind="sim", arm=e["arm"], seed=e["seed"], phase=e["phase"], ref=ref,
                        at=now7().strftime("%F %T"), t=time.time())
    save_state(st)
    with open(MANIFEST, "a") as f:
        f.write(json.dumps(dict(tag=e["tag"], ref=ref, arm=e["arm"], seed=e["seed"], phase=e["phase"],
                                overrides=ARMS[e["arm"]], jar_ds=JAR_DS, jar_sha256=JAR_SHA, code_sha=CODE_SHA,
                                chain=CHAIN, tk=TKK, pred_md5=ARTS["preds"][str(e["seed"])], end=END,
                                at=now7().strftime("%F %T"))) + "\n")
    log.info("PUSHED %s (%s seed=%s phase=%s)", e["tag"], e["arm"], e["seed"], e["phase"])


def push_mtm(st, b):
    refs = {}
    for t in b["runs"]:
        refs[t] = kslug(t)          # duong mount kernel_sources: /kaggle/input/**/<sim-...>/
    ctl = {}
    rows = {r["seed"]: r for r in __import__("csv").DictReader(open(GQ_CSV))
            if r["phase"] == "DEV" and r["period"] == "DEV_2022_25"}
    for t in b["runs"]:
        e = st[t]
        if e["arm"] in ("b0", "g0"):   # [R3] g0 = B0 tren jar R3 (byte-identical n4f-b0-a1 da kiem)
            ctl[t] = float(rows[SEED_NAME[e["seed"]].upper()]["dd_q"])
    cfg = {"tags": b["runs"], "slug": refs, "controls": ctl, "tol_pp": MTM_TOL_PP,
           "win_dev": ["2022-01-01", "2026-01-01"], "win_ho": ["2026-01-01", "2026-10-01"],
           "end_local": "2026-10-01 00:00"}
    code = open(MTM_SRC).read().replace("__CFG_JSON__", repr(json.dumps(cfg)))
    compile(code, "mtm", "exec")
    ref = KS.kernel_ref(b["tag"])
    md = {"id": ref, "title": ref.split("/")[1], "code_file": "run.py", "language": "python",
          "kernel_type": "script", "is_private": True, "enable_gpu": False, "enable_internet": False,
          "dataset_sources": KLINE_DS, "competition_sources": [],
          "kernel_sources": [KS.kernel_ref(t) for t in b["runs"]]}
    kpush(b["tag"], code, md)
    st[b["tag"]] = dict(state="PUSHED", kind="mtm", runs=b["runs"], controls=ctl, ref=ref,
                        at=now7().strftime("%F %T"), t=time.time())
    save_state(st)
    with open(MANIFEST, "a") as f:
        f.write(json.dumps(dict(tag=b["tag"], ref=ref, kind="mtm", runs=b["runs"], controls=ctl,
                                mtm_src_md5=fhash(MTM_SRC, "md5"), at=now7().strftime("%F %T"))) + "\n")
    log.info("PUSHED %s (MTM %d run, %d doi chung)", b["tag"], len(b["runs"]), len(ctl))


# ---------------------------------------------------------------- fetch + check
def fetch_small(tag):
    return kcall("fetch " + tag, _fetch_small_once, tag)


def _fetch_small_once(tag):
    import requests
    out = os.path.join(RES, tag)
    os.makedirs(out, exist_ok=True)
    a = KS._api()
    resp = a.process_response(a.kernel_output_with_http_info(USER, kslug(tag)))
    got = []
    for it in resp["files"]:
        fn = it["fileName"]
        if not re.search(FETCH_RX, fn):
            continue
        p = os.path.join(out, fn)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with requests.get(it["url"], stream=True, timeout=600) as r:
            r.raise_for_status()
            with open(p, "wb") as f:
                for b in r.iter_content(1 << 20):
                    f.write(b)
        got.append(fn)
    tot = sum(os.path.getsize(os.path.join(dp, f)) for dp, _, fs in os.walk(RES) for f in fs) / 1e6
    log.info("FETCH %s: %s (results tong %.1f MB)", tag, got, tot)
    if tot > RES_MAX_MB:
        raise RuntimeError("results > %d MB" % RES_MAX_MB)
    return out


def prof(o):
    out = {}
    p = o + "/prof_run.properties"
    if os.path.exists(p):
        for ln in open(p):
            if "=" in ln and not ln.startswith("#"):
                k, v = ln.rstrip("\n").split("=", 1)
                out[k.strip()] = v.strip()
    return out


def dev_md5(path):
    L = open(path, "rb").read().splitlines(keepends=True)
    dev = [ln for ln in L[1:] if ln.decode(errors="ignore").split(",")[6:7]
           and ln.decode(errors="ignore").split(",")[6] < "20260101"]
    return hashlib.md5(L[0] + b"".join(dev)).hexdigest(), len(dev)


def verify_sim(st, tag):
    """None = chua du dieu kien (cho B0 cung seed); True = DONE; str = ly do HALT."""
    e = st[tag]
    o = os.path.join(RES, tag)
    try:
        rj = json.load(open(o + "/result.json"))
    except Exception:  # noqa: BLE001
        return "khong co result.json"
    if rj.get("ok") is not True:
        return "result.ok != True"
    if rj.get("jar_sha256") != JAR_SHA:
        return "jar_sha256 lech: %s" % rj.get("jar_sha256")
    pr = prof(o)
    bad = [k for k, v in ARMS[e["arm"]].items()
           if pr.get(k) != ("true" if v is True else "false" if v is False else str(v))]
    if bad:
        return "override khong vao profile: %s" % bad
    pd_ = o + "/storage/printDone.csv"
    try:
        es = json.load(open(o + "/storage/equity_summary.json"))
    except Exception:  # noqa: BLE001
        return "khong co equity_summary.json"
    if not os.path.exists(pd_) or abs(float(es.get("killsw_thr", -1)) - 0.40) > 1e-4:
        return "thieu printDone hoac killsw_thr != 0.40 (%s)" % es.get("killsw_thr")
    chk = {"killsw_triggers": es.get("killsw_triggers"), "killsw_blocked": es.get("killsw_blocked"),
           "maxdd_close_pct": es.get("maxdd_close_pct"), "maxdd_mtm_low_pct": es.get("maxdd_mtm_low_pct")}
    sn = SEED_NAME[e["seed"]]
    if e["arm"] == "b0":
        m, n = dev_md5(pd_)
        mr, nr = dev_md5(KOUT + "tsx-x14-%s/storage/printDone.csv" % sn)
        chk.update(g_dev=m, g_dev_ref=mr, n_dev=n)
        if m != mr:
            return "G-DEV lech tsx-x14-%s: %s != %s (%d vs %d dong)" % (sn, m, mr, n, nr)
        if e["phase"] == "gate":
            a, b = fhash(pd_, "md5"), fhash(KOUT + "n4b-b0union-a1/storage/printDone.csv", "md5")
            chk.update(full_md5=a, full_ref_n4b=b)
            if a != b:
                return "GATE: printDone khong trung byte n4b-b0union-a1 (%s != %s)" % (a, b)
    else:
        b0t = tag_of("b0", e["seed"])
        if st.get(b0t, {}).get("state") != "DONE":
            return None
        L = open(pd_, "rb").read().splitlines(keepends=True)
        base = [ln for ln in L if not ln.rstrip().endswith(b"book=sleeve")]
        nsl = len(L) - len(base)
        chk.update(n_rows=len(L) - 1, n_sleeve_rows=nsl)
        if e["arm"] == "s1b":
            bb = open(os.path.join(RES, b0t, "storage/printDone.csv"), "rb").read()
            if b"".join(base) != bb:
                return "G-INV S1b-SEP: phan nen != B0 %s" % b0t
            chk["g_inv"] = True
        else:
            if int(es.get("merge_overlap_ticks", -1)) != 0:
                return "merge_overlap_ticks = %s (phai 0)" % es.get("merge_overlap_ticks")
            lo = os.path.join(o, "storage/leg_owner.csv")
            if not os.path.exists(lo) or not os.path.exists(os.path.join(o, "storage/merge_log.csv")):
                return "thieu leg_owner/merge_log"
            n_owner = sum(1 for _ in open(lo)) - 1
            chk["n_leg_owner"] = n_owner
            if n_owner != len(L) - 1:
                return "so leg_owner %d != so dong printDone %d" % (n_owner, len(L) - 1)
    e["check"] = chk
    return True


def verify_mtm(st, tag):
    p = os.path.join(RES, tag, "mtm_result.json")
    try:
        r = json.load(open(p))
    except Exception:  # noqa: BLE001
        return "khong co mtm_result.json"
    miss = {k: v["missing"] for k, v in r["runs"].items() if v["missing"]}
    if miss:
        return "MTM missing > 0: %s" % miss
    badc = {k: (v["dd_dev"], v["ref"]) for k, v in r["controls"].items() if not v["ok"]}
    if badc or not r["controls"]:
        return "MTM doi chung lech (> %.3f pp) hoac khong co: %s" % (MTM_TOL_PP, badc)
    if not r.get("ok"):
        return "MTM ok=False (eq_end != CAP0+sum pnl?)"
    st[tag]["check"] = {k: dict(dd_dev=v["dd_dev"], dd_ho=v["dd_ho"]) for k, v in r["runs"].items()}
    return True


def poll(st):
    """Status (retry 3 lan/10 phut) cho kernel CHUA ket thuc; kernel COMPLETE cho tai: 403 = output chua san sang,
    thu lai MOI vong toi FETCH403_MAX_S roi moi HALT; loi khac (sau retry) => HALT."""
    for tag, e in list(st.items()):
        if tag.startswith("_") or e.get("state") != "PUSHED":
            continue
        s = e.get("kstatus")
        if s not in KS.TERMINAL:
            try:
                s = kcall("status " + tag, KS._status, e["ref"])
            except Exception as ex:  # noqa: BLE001
                halt(st, "status %s loi sau retry: %s" % (tag, str(ex)[:200]))
                return
            if s not in KS.TERMINAL:
                continue
            e["kstatus"] = s
            e["t_terminal"] = time.time()
            save_state(st)
            log.info("%s ket thuc: %s", tag, s)
        if light_only():
            continue
        if s != "COMPLETE":
            try:
                _fetch_small_once(tag)          # lay file nho de chan doan, loi thi bo qua
            except Exception:  # noqa: BLE001
                pass
            halt(st, "kernel %s ket thuc %s" % (tag, s))
            return
        try:
            kcall("fetch " + tag, _fetch_small_once, tag, retry403=False)
        except Exception as ex:  # noqa: BLE001
            if _http_code(ex) == 403:
                t0 = e.setdefault("fetch403_since", time.time())
                save_state(st)
                waited = time.time() - t0
                if waited > FETCH403_MAX_S:
                    halt(st, "fetch %s van 403 sau %d phut" % (tag, waited // 60))
                    return
                log.info("fetch %s: 403 (output chua san sang) — thu lai vong sau (da cho %d phut)", tag, waited // 60)
                continue
            halt(st, "fetch %s loi: %s" % (tag, str(ex)[:200]))
            return
        e["state"] = "FETCHED"
        e.pop("fetch403_since", None)
        save_state(st)


def verify(st):
    for tag, e in list(st.items()):
        if tag.startswith("_") or e.get("state") != "FETCHED":
            continue
        v = verify_sim(st, tag) if e["kind"] == "sim" else verify_mtm(st, tag)
        if v is None:
            continue
        if v is not True:
            halt(st, "%s: %s" % (tag, v))
            return
        e["state"] = "DONE"
        save_state(st)
        log.info("DONE %s %s", tag, json.dumps(e.get("check"))[:400])


def account_running():
    return KS.MAX_CONCURRENT - kcall("free_slots", KS.free_slots)


def adopt_or_push(st, tag, pushfn):
    try:
        s = KS._status(KS.kernel_ref(tag))
    except Exception:  # noqa: BLE001
        s = None
    if s in ("RUNNING", "QUEUED", "COMPLETE"):
        log.warning("%s da ton tai tren Kaggle (%s) nhung khong co trong state => NHAN (khong push lai)", tag, s)
        return "adopt", s
    pushfn()
    return "push", None


def schedule(st):
    sims = plan()
    if os.path.exists(PRIO):
        if time.time() - _PRIO_LOG["t"] > 600:
            log.warning("co %s => KHONG push kernel moi (van poll/tai)", PRIO)
            _PRIO_LOG["t"] = time.time()
        return
    ours = [t for t, v in st.items() if not t.startswith("_") and v.get("state") == "PUSHED"
            and v.get("kstatus") not in KS.TERMINAL]          # dang chay that; kernel cho tai KHONG chan push
    if len(ours) >= MAXPAR:
        return
    gate = sims[0]["tag"]
    if st.get(gate, {}).get("state") != "DONE":
        todo = [sims[0]] if gate not in st else []
    else:
        todo = [e for e in sims[1:] if e["tag"] not in st]
    if not todo and all(st.get(e["tag"], {}).get("state") == "DONE" for e in sims):
        todo = [dict(b, kind="mtm") for b in mtm_batches() if b["tag"] not in st]
    for e in todo:
        if len(ours) >= MAXPAR or account_running() >= MAXPAR:    # kiem account qua API moi lan push
            return
        if e.get("kind") == "mtm":
            how, s = adopt_or_push(st, e["tag"], lambda: push_mtm(st, e))
            if how == "adopt":
                st[e["tag"]] = dict(state="PUSHED", kind="mtm", runs=e["runs"], ref=KS.kernel_ref(e["tag"]), t=time.time())
        else:
            how, s = adopt_or_push(st, e["tag"], lambda: push_sim(st, e))
            if how == "adopt":
                st[e["tag"]] = dict(state="PUSHED", kind="sim", arm=e["arm"], seed=e["seed"], phase=e["phase"],
                                    ref=KS.kernel_ref(e["tag"]), t=time.time())
        save_state(st)
        ours.append(e["tag"])
        time.sleep(30)


_AR = {"t": 0.0, "v": 0}


def account_running_cached():
    if time.time() - _AR["t"] > 600:
        _AR["v"], _AR["t"] = account_running(), time.time()
    return _AR["v"]


# ---------------------------------------------------------------- B4 tong hop (chi so tho, KHONG cham cong)
def summarize(st):
    import csv
    mt = {}
    for b in mtm_batches():
        p = os.path.join(RES, b["tag"], "mtm_result.json")
        if os.path.exists(p):
            mt.update(json.load(open(p))["runs"])
    rows = {}
    for e in plan():
        o = os.path.join(RES, e["tag"])
        cl, pnl, n = {}, {}, 0
        with open(o + "/storage/printDone.csv", newline="") as f:
            r = csv.reader(f)
            h = next(r)
            i = {k: j for j, k in enumerate(h)}
            for x in r:
                if len(x) <= i["pnl"]:
                    continue
                y = x[i["start"]][:4]
                bk = "S" if x[-1].strip() == "book=sleeve" else "B"
                cl.setdefault(y, set()).add((bk, x[i["sym"]], x[i["end"]]))
                pnl[y] = pnl.get(y, 0.0) + float(x[i["pnl"]])
                n += 1
        rows[e["tag"]] = dict(arm=e["arm"], seed=e["seed"], phase=e["phase"], n_rows=n,
                              clusters_by_year={y: len(v) for y, v in sorted(cl.items())},
                              pnl_by_year={y: round(v, 2) for y, v in sorted(pnl.items())},
                              check=st[e["tag"]].get("check"), mtm=mt.get(e["tag"]))
    json.dump(dict(note="CHI SO THO Pha 1a + B0-A1 8 seed — KHONG cham G1-G5 (MASTER audit roi chon 1b theo prereg)",
                   jar_sha256=JAR_SHA, code_sha=CODE_SHA, runs=rows), open(RES + "/summary_m2r.json", "w"), indent=1)
    log.info("summary -> %s/summary_m2r.json", RES)


# ---------------------------------------------------------------- vong lap
_STOP = {"v": False}


def _sig(*_):
    _STOP["v"] = True
    log.warning("nhan SIGTERM — dung sau vong hien tai (kernel Kaggle dang chay van chay, resume sau)")


def run():
    signal.signal(signal.SIGTERM, _sig)
    signal.signal(signal.SIGINT, _sig)
    st = load_state()
    if st.get("_halt"):
        log.error("dang HALT (%s) — MASTER xem roi 'clearhalt'", st["_halt"])
        return 2
    if st.get("_done"):
        log.info("Pha 1a da XONG (%s) — khong lam gi them", st["_done"])
        return 0
    if not light_only():
        jards()
    log.info("RUN bat dau: %d sim + %d MTM, MAXPAR=%d, poll %ds", len(plan()), len(mtm_batches()), MAXPAR, POLL_S)
    while not _STOP["v"]:
        try:
            st = load_state()
            poll(st)
            if not st.get("_halt"):
                verify(st)
            if st.get("_halt"):
                return 2
            names = [e["tag"] for e in plan()] + [b["tag"] for b in mtm_batches()]
            if all(st.get(t, {}).get("state") == "DONE" for t in names):
                summarize(st)
                st["_done"] = now7().strftime("%F %T")
                save_state(st)
                log.info("PHA 1a XONG — DUNG (khong tu chay 1b). Ket qua: %s", RES)
                return 0
            if not light_only():
                schedule(st)
            act = [t for t, v in st.items() if not t.startswith("_") and v.get("state") == "PUSHED"
                   and v.get("kstatus") not in KS.TERMINAL]
            pend = [t for t, v in st.items() if not t.startswith("_") and v.get("state") == "PUSHED"
                    and v.get("kstatus") in KS.TERMINAL]
            if pend:
                log.info("cho tai output: %s", pend)
            done = sum(1 for t in names if st.get(t, {}).get("state") == "DONE")
            log.info("loop: DONE %d/%d, dang chay %s", done, len(names), act)
        except Exception as ex:  # noqa: BLE001  (da qua retry trong kcall => dung han)
            halt(load_state(), "loi vong lap (sau retry): %s" % str(ex)[:300])
            return 2
        for _ in range(POLL_S // 5):
            if _STOP["v"]:
                break
            time.sleep(5)
    return 0


def status():
    st = load_state()
    print("halt:", st.get("_halt"), "| done:", st.get("_done"))
    for t in [e["tag"] for e in plan()] + [b["tag"] for b in mtm_batches()]:
        v = st.get(t, {})
        print("%-18s %-8s %-9s %s" % (t, v.get("state", "-"), v.get("kstatus", ""), v.get("at", "")))


def clearhalt():
    st = load_state()
    h = st.pop("_halt", None)
    save_state(st)
    log.warning("clearhalt (truoc: %s)", h)


# ---------------------------------------------------------------- DRY
def selftest_mtm():
    """MTM tren du lieu tong hop: eq cuoi = CAP0 + sum pnl, missing dem dung, DD dung."""
    import importlib.util
    import numpy as np
    import pandas as pd
    spec = importlib.util.spec_from_file_location("mtmk", MTM_SRC)
    M = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(M)
    # 2 leg: AAA mo 2021-07-01 10:00 +07 (03:00 UTC) dong 2021-07-02 07:00 +07 (00:00 UTC — ca 'dong 00:00 UTC')
    d = pd.DataFrame(dict(sym=["AAA", "BBB"], start=["20210701 10:00", "20210701 12:00"],
                          end=["20210702 07:00", "20210701 13:00"], quantity=[2.0, 1.0], entry=[10.0, 5.0],
                          pnl=[4.0, -1.0], margin=[20.0, 5.0]))
    p = OD + "/_selftest_pd.csv"
    d.to_csv(p, index=False)
    L = M.load_legs(p)
    t0 = int(pd.Timestamp("2021-07-01").value // 10 ** 6)
    ts = t0 + np.arange(2 * 1440, dtype=np.int64) * 60000
    px = {"AAAUSDT": (ts, np.where(np.arange(2 * 1440) < 600, 10.0, 8.0))}     # BBB khong co gia => missing
    res = M.equity_series({"x": L}, 3 * 1440, lambda ym, syms: {s: px[s] for s in syms if s in px})
    eq, miss = res["x"]
    ok_end = abs(eq[-1] - (35000 + 3.0)) < 1e-9
    # phut 600 UTC tro di: AAA gia 8 => u = 2*(8-10) = -4
    ok_u = abs(eq[100] - 35000.0) < 1e-9 and abs(eq[700] - (35000 - 1.0 - 4.0)) < 1e-9   # BBB -1 da dong luc 06:00
    ok_close00 = abs(eq[1440] - (35000 - 1.0 + 4.0)) < 1e-9   # leg dong dung 00:00 UTC ngay 2 da vao realized
    ok_miss = miss == 1
    log.info("SELFTEST MTM: eq_end=%s u=%s dong00UTC=%s missing=%s (=%d)", ok_end, ok_u, ok_close00, ok_miss, miss)
    os.remove(p)
    return ok_end and ok_u and ok_close00 and ok_miss


def dry():
    ok = True
    print("=== KE HOACH (khong push) ===")
    for e in plan():
        ov = ARMS[e["arm"]]
        extra = {k: v for k, v in ov.items() if k not in ARMS["b0"] or ARMS["b0"][k] != v}
        print("%-14s %-5s seed=%-5d phase=%-4s %s" % (e["tag"], e["arm"], e["seed"], e["phase"], extra))
    for b in mtm_batches():
        print("%-14s MTM legacy (%d run, gom gate doi chung): %s" % (b["tag"], len(b["runs"]), b["runs"]))
    print("BASE chung: KILLSW_A40_DD=%s, X14 %d khoang, end=%s, jar_ds=%s (private)" %
          (BASE["KILLSW_A40_DD"], len(X14.split(",")), END, JAR_DS))
    print("=== JAR + SEC CHECK ===")
    try:
        jards(dry=True)
        print("jar sha256 OK, profile md5 OK, sec check 2 script SACH")
    except Exception as ex:  # noqa: BLE001
        ok = False
        print("JAR/SEC FAIL:", ex)
    print("=== KAGGLE AUTH / TRANG THAI ===")
    try:
        a = KS._api()
        ex_ds = [str(d.ref) for d in a.dataset_list(mine=True, search=JAR_DS)]
        print("auth OK; dataset %s da co: %s" % (JAR_DS, USER + "/" + JAR_DS in ex_ds))
        print("kernel dang chay tren account:", account_running())
        exist = []
        for t in [e["tag"] for e in plan()] + [b["tag"] for b in mtm_batches()]:
            try:
                exist.append((t, KS._status(KS.kernel_ref(t))))
            except Exception:  # noqa: BLE001
                pass
        print("kernel n4f-* da ton tai:", exist or "khong")
        g = plan()[0]["tag"]
        if any(t == g for t, _ in exist):
            n = len(a.process_response(a.kernel_output_with_http_info(USER, kslug(g)))["files"])
            print("liet ke output %s qua kslug=%s: %d file (duong tai cua orchestrator)" % (g, kslug(g), n))
            ok = ok and n > 0
        print("slug MTM khop duong mount:", all(("/" + kslug(t) + "/") in ("/kaggle/input/x/" + KS.kernel_ref(t).split("/")[1] + "/storage")
                                               for t in [e["tag"] for e in plan()]))
        for ds in KLINE_DS:
            fs = a.dataset_list_files(ds)
            names = sorted(os.path.basename(getattr(f, "name", None) or str(f)) for f in (getattr(fs, "files", None) or []))
            months = [n for n in names if n.startswith("kline1m-")]
            print("%s: %d file %s..%s" % (ds, len(months), months[:1], months[-1:]))
        need = pd_months()
        have = set()
        for ds in KLINE_DS:
            fs = a.dataset_list_files(ds)
            have |= {os.path.basename(getattr(f, "name", None) or str(f))[8:15] for f in (getattr(fs, "files", None) or [])}
        miss = [m for m in need if m not in have]
        print("thang gia can 2021-07..2026-09: thieu %s" % (miss or "0"))
        ok = ok and not miss
    except Exception as ex:  # noqa: BLE001
        ok = False
        print("KAGGLE FAIL:", str(ex)[:300])
    print("=== THAM CHIEU LOCAL ===")
    import csv
    rows = {r["seed"]: r for r in csv.DictReader(open(GQ_CSV)) if r["phase"] == "DEV" and r["period"] == "DEV_2022_25"}
    for s, sn in SEED_NAME.items():
        p = KOUT + "tsx-x14-%s/storage/printDone.csv" % sn
        m, n = dev_md5(p) if os.path.exists(p) else ("THIEU", 0)
        print("tsx-x14-%-5s G-DEV md5 %s (%d dong)  MTM doi chung dd_q DEV_2022_25 = %s" %
              (sn, m, n, rows.get(sn.upper(), {}).get("dd_q")))
        ok = ok and m != "THIEU" and sn.upper() in rows
    p = KOUT + "n4b-b0union-a1/storage/printDone.csv"
    print("gate full-file ref n4b-b0union-a1 md5:", fhash(p, "md5") if os.path.exists(p) else "THIEU")
    print("=== TEMPLATE + SELFTEST ===")
    try:
        compile(template().replace("__CFG_JSON__", repr(json.dumps(sim_cfg(plan()[0])))), "sim", "exec")
        compile(open(MTM_SRC).read().replace("__CFG_JSON__", repr("{}")), "mtm", "exec")
        print("sim template + MTM kernel compile OK")
        st_ok = selftest_mtm()
        print("selftest MTM:", st_ok)
        ok = ok and st_ok
    except Exception as ex:  # noqa: BLE001
        ok = False
        print("TEMPLATE/SELFTEST FAIL:", ex)
    print("=== UOC LUONG ===")
    print("28 sim x ~45-60 phut (n4b: 42 phut) = ~21-28 gio-kernel; 2 song song => ~11-14 gio; MTM 3 kernel ~1-2 gio.")
    print("ngay %s chi poll: %s" % (NO_HEAVY_DAY, light_only()))
    print("DRY KET QUA:", "OK" if ok else "CO LOI")
    return 0 if ok else 1


def pd_months():
    out, m = [], dt.date(2021, 7, 1)
    while m <= dt.date(2026, 9, 1):
        out.append(m.strftime("%Y-%m"))
        m = dt.date(m.year + (m.month == 12), m.month % 12 + 1, 1)
    return out


if __name__ == "__main__":
    c = sys.argv[1] if len(sys.argv) > 1 else ""
    f = {"run": run, "dry": dry, "status": status, "clearhalt": clearhalt}.get(c)
    if not f:
        sys.exit(__doc__)
    sys.exit(f() or 0)
