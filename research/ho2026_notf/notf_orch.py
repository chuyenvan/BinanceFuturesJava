#!/usr/bin/env python3
"""HO2026_NOTF orchestrator (PREREG_HO2026_NOTF 96164b72 + ADDENDUM_TECH). Chi chay + parity + cong, KHONG cham.
Buoc: jar STUB dataset -> [cong A0': a0p-x26-q1 + a0p-{k24-s,k24-b,x14}-s42] || [du lieu A1: nt-x26-q1..3 -> nt-tk26 -> nt-chain-y26
-> nt-v1] -> (cong PASS) 24 sim nt-*. <= MAXPAR kernel toan tai khoan. State resume notf_state.json.
Usage: cd ~/claude_master/ho_tradfi_wk && setsid nohup python3 notf_orch.py run > orch.out 2>&1 < /dev/null &"""
import glob, hashlib, json, logging, os, re, shutil, subprocess, sys, time
W = "/home/ubuntu/claude_master/ho_tradfi_wk"
R = "/home/ubuntu/src/BinanceFuturesJava"
A = R + "/research/analysis"
sys.path.insert(0, R); sys.path.insert(0, A)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("notf")
_fh = logging.FileHandler(W + "/orch.log"); _fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
logging.getLogger().addHandler(_fh)
import ho4p1_exp_kernel as E          # noqa: E402
import ho4p1_stage as ST              # noqa: E402
import ho4p1_chainops as CO           # noqa: E402
import ho4p1_queue as q               # noqa: E402
logging.getLogger().removeHandler(q._fh)
E.WD = W + "/kaggle"
os.makedirs(E.WD, exist_ok=True)
USER = "chuyendinh"
X = open(W + "/X_notf_v2.txt").read().split()
XMD5 = "6e296227a3a4789f7602bcb38e4f00b7"
assert hashlib.md5(("\n".join(sorted(X)) + "\n").encode()).hexdigest() == XMD5 and len(X) == 230 and "MDTUSDT" not in X
JDS = "ho2026-notf-jar-exp"
NJAR = W + "/exp_src/target/binance-java-sdk-1.2.4.jar"
NJAR_SHA = "a485880cf329ae043b03608faa827f39f1a1baf5c6043308bf526b0735c65167"
TSX_JAR = W + "/jarchk/sim-jar-tsx/sim.jar"
FLAGS0 = "20260205-20260214,20260216-20260217,20260224-20260225,20260611-20260611"
FLAGS1 = "20260205-20260214,20260216-20260217,20260224-20260225,20260606-20260607,20260610-20260611"
SEEDS = [42, 7, 13, 21, 99, 123, 777, 2024]
MAXPAR, POLL = 5, 180
WANT0 = {"a0p2-k24-s-s42": "6989a312", "a0p2-k24-b-s42": "7cc8864c", "a0p-x14-s42": "bb609455"}
# ADDENDUM_TECH-2: jar tsx KHONG co SIM_CRASH_ENTRY_PENALTY (a0p-k24-s-s42 = md5 k24-b) -> k24-s/k24-b dung jar STUB build tu df021437 (nguon b7c89f09)
SJDS = "ho2026-notf-sim-jar"
SJAR = W + "/sim_src/target/binance-java-sdk-1.2.4.jar"
SJAR_SHA = "877d9ffade1daac377cb6aea1f070f57de23e5b44b03cd39e024f13ae8baf883"
PROF = "/home/ubuntu/kaggle_sim/push_jar_nsel/prof_r4_kg0_k16_f015_g155.properties"
Q1_MAN = "/home/ubuntu/claude_master/1011/ho4p1/kaggle/out/ho4p1-x26-q1/out/MANIFEST.json"
STP = W + "/notf_state.json"
ARTS0 = json.load(open("/home/ubuntu/claude_master/1011/ho4p1/arts.json"))
FUND0 = dict(q.FUND)
q.JAR_DS = "sim-jar-tsx"


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


TSX_SHA = sha256(TSX_JAR)
assert TSX_SHA.startswith("cc0f9d11"), TSX_SHA
q.JAR_SHA = TSX_SHA


def use_jar(ov):
    if "SIM_LOSER_TS_EXT_HOURS" in ov:
        q.JAR_DS, q.JAR_SHA = "sim-jar-tsx", TSX_SHA
    else:
        q.JAR_DS, q.JAR_SHA = SJDS, SJAR_SHA
KS = q.GA.ks_mod()

# ---------------- exporter kernel (A1: in_uni loai X) ----------------
OLD_UNI = '''def in_uni(s):
    # bo loc LIVE TickerIngestor2AerospikeNew:83/313 (USDT, ^[A-Z0-9]+$, khong diedSymbol) + co trong mapper (quyet dinh 6)
    return s.endswith("USDT") and re.fullmatch(r"[A-Z0-9]+", s) is not None and s not in DIED and s in MAPPER'''
NEW_UNI = '''EXCL = set(CFG["exclude"])                       # HO2026_NOTF: X = TF + INDEX (exchangeInfo 20261027), MDT la crypto
assert hashlib.md5(("\\n".join(sorted(EXCL)) + "\\n").encode()).hexdigest() == CFG["exclude_md5"], "X md5"
RES["exclude_n"] = len(EXCL)
def in_uni(s):
    # bo loc LIVE TickerIngestor2AerospikeNew:83/313 (USDT, ^[A-Z0-9]+$, khong diedSymbol) + co trong mapper (quyet dinh 6) + HO2026_NOTF: s khong thuoc X
    return s.endswith("USDT") and re.fullmatch(r"[A-Z0-9]+", s) is not None and s not in DIED and s in MAPPER and s not in EXCL'''
assert E.KX.count(OLD_UNI) == 1
KX_NT = E.KX.replace(OLD_UNI, NEW_UNI)


def exp_cfg(tag, q_, nt):
    c = json.load(open("/home/ubuntu/claude_master/1011/ho4p1/cfg_ho4p1-x26-%s.json" % q_))
    c["tag"], c["jar_ds"], c["jar_sha"] = tag, JDS, NJAR_SHA
    if nt:
        c["exclude"], c["exclude_md5"] = sorted(X), XMD5
    return c


def push_exp(tag, q_, nt):
    cfg = exp_cfg(tag, q_, nt)
    fol = os.path.join(E.WD, E.slug(tag)); os.makedirs(fol, exist_ok=True)
    code = (KX_NT if nt else E.KX).replace("__CFG_JSON__", repr(json.dumps(cfg))).replace("__JW_SRC__", repr(open(E.JW).read())).replace(
        "__JBIN_SRC__", repr(open(os.path.join(os.path.dirname(E.JW), "jbin.py")).read()))
    compile(code, "k", "exec")
    open(fol + "/run.py", "w").write(code)
    dss = sorted({cfg["jar_ds"], cfg["cfg_ds"], cfg["as_ds"], cfg["asdata_ds"], cfg["dev_market_ds"]})
    md = {"id": USER + "/" + E.slug(tag), "title": E.slug(tag), "code_file": "run.py", "language": "python", "kernel_type": "script",
          "is_private": True, "enable_gpu": False, "enable_internet": True, "dataset_sources": [USER + "/" + d for d in dss],
          "competition_sources": [], "kernel_sources": []}
    json.dump(md, open(fol + "/kernel-metadata.json", "w"), indent=1)
    r = E.api().kernels_push(fol)
    log.info("PUSHED %s %s", tag, getattr(r, "url", r))


QK_NT = {"q1": "nt-x26-q1", "q2": "nt-x26-q2", "q3": "nt-x26-q3"}


def push_tk():
    fol = E.WD + "/nt-tk26"; os.makedirs(fol, exist_ok=True)
    open(fol + "/run.py", "w").write(ST.TK.replace("__DAYS__", repr(json.dumps(ST.days()))).replace("__QK__", repr(json.dumps(QK_NT))))
    md = {"id": USER + "/nt-tk26", "title": "nt-tk26", "code_file": "run.py", "language": "python", "kernel_type": "script",
          "is_private": True, "enable_gpu": False, "enable_internet": False, "dataset_sources": [], "competition_sources": [],
          "kernel_sources": [USER + "/" + k for k in sorted(QK_NT.values())]}
    json.dump(md, open(fol + "/kernel-metadata.json", "w"), indent=1)
    r = E.api().kernels_push(fol)
    log.info("PUSHED nt-tk26 %s", getattr(r, "url", r))


# ---------------- chain (them id X vao tap id loai, nhu 16 id trung) ----------------
CH_SRC = "/home/ubuntu/claude_master/1011/ho4p1/stage/ho4p1-code/ho4p1_chain.py"
assert hashlib.md5(open(CH_SRC, "rb").read()).hexdigest() == "5ec798f74f2e27365a63b0e0598a632d"
_ch = open(CH_SRC).read()
_anchor = 'RES["dup_ids"] = {int(i): sorted(_m863[_m863.symId == i].symbol) for i in sorted(DUP_IDS)}\n'
assert _ch.count(_anchor) == 1
CH_NT = _ch.replace(_anchor, _anchor + '''_XS = CFG["exclude_syms"]                         # HO2026_NOTF: id mapper cua X -> loai khoi OI ghep/Tool1/CLOSES/bins (nhu id trung)
assert hashlib.md5(("\\n".join(sorted(_XS)) + "\\n").encode()).hexdigest() == CFG["exclude_md5"], "X md5"
X_IDS = {int(i) for i in _m863[_m863.symbol.isin(_XS)].symId}
_shared = sorted(int(i) for i in X_IDS if not set(_m863[_m863.symId == i].symbol) <= set(_XS))
assert not _shared, ("id X dung chung voi crypto", _shared)
RES["exclude_ids_n"] = len(X_IDS)
DUP_IDS = DUP_IDS | X_IDS
''')
compile(CH_NT, "chain_nt", "exec")
RUN_NT = r'''"""HO2026_NOTF chain launcher (ho4p1-code + ho4p1_chain.py va them loai id X)"""
import glob, json, logging, os, shutil, subprocess, sys
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout)
CFG = json.loads(__CFG__)
subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "xgboost==3.2.0", "onnxruntime==1.23.2", "pandas==2.3.3",
                       "numpy==2.2.6", "pyarrow==25.0.1"])
c = [p for p in glob.glob("/kaggle/input/**/ho4p1_chain.py", recursive=True) if "/ho4p1-code/" in p]
assert c, "thieu ho4p1-code"
shutil.copytree(os.path.dirname(c[0]), "/tmp/code")
open("/tmp/code/ho4p1_chain_notf.py", "w").write(__CHSRC__)
CFG["code_dir"] = "/tmp/code"
json.dump(CFG, open("/tmp/cfg.json", "w"))
logging.info("INPUT %s", sorted(set(p.split("/")[3] for p in glob.glob("/kaggle/input/*/*"))))
rc = subprocess.call([sys.executable, "-u", "/tmp/code/ho4p1_chain_notf.py", "/tmp/cfg.json"])
logging.info("CHAIN_RC %s", rc)
sys.exit(rc)
'''


def push_chain():
    tag = "nt-chain-y26"
    cfg = dict(mode="y26", tag=tag, model_sha=CO.MODEL_SHA, pin_sha=CO.PIN_SHA, seeds=CO.SEEDS, q_src=QK_NT, oi_src="ho4p1-oi-a",
               exclude_syms=sorted(X), exclude_md5=XMD5)
    fol = E.WD + "/" + tag; os.makedirs(fol, exist_ok=True)
    code = RUN_NT.replace("__CFG__", repr(json.dumps(cfg))).replace("__CHSRC__", repr(CH_NT))
    compile(code, "k", "exec")
    open(fol + "/run.py", "w").write(code)
    dss = ["ho4p1-code", "funding-oi-percoin", "sim-ho26a-bundle"] + ["ho26-pred-s%d" % s for s in CO.SEEDS]
    ks = ["ho4p1-oi-a"] + sorted(QK_NT.values())
    md = {"id": USER + "/" + tag, "title": tag, "code_file": "run.py", "language": "python", "kernel_type": "script",
          "is_private": True, "enable_gpu": False, "enable_internet": True, "dataset_sources": [USER + "/" + d for d in dss],
          "competition_sources": [], "kernel_sources": [USER + "/" + k for k in ks]}
    json.dump(md, open(fol + "/kernel-metadata.json", "w"), indent=1)
    r = E.api().kernels_push(fol)
    log.info("PUSHED %s %s", tag, getattr(r, "url", r))


# ---------------- V1 kernel: so tung o ticker A1 vs goc tren 12 ngay ----------------
V1_DAYS = ["20260115", "20260205", "20260228", "20260315", "20260420", "20260510", "20260602", "20260620", "20260710", "20260805", "20260901", "20260930"]
V1K = r'''"""HO2026_NOTF V1: ticker nt-tk26 vs ho4p1-tk26: 0 symbol X; tap con ngoai X trung tung o (12 ngay)."""
import glob, gzip, json, sys, types
JB = types.ModuleType("jbin"); exec(__JBIN__, JB.__dict__)
X = set(json.loads(__X__)); DAYS = json.loads(__DAYS__)
def load(src, d):
    p = [x for x in glob.glob("/kaggle/input/**/ticker_%s.bin.gz" % d, recursive=True) if "/" + src + "/" in x][0]
    return dict(JB.iter_minutes(gzip.open(p).read()))
out = {}
for d in DAYS:
    a, b = load("nt-tk26", d), load("ho4p1-tk26", d)
    ax = sum(1 for m in a.values() for s in m if s in X)
    bf = {t: {s: v for s, v in m.items() if s not in X} for t, m in b.items()}
    bf = {t: m for t, m in bf.items() if m}
    n_cells = sum(len(m) for m in bf.values())
    same_min = set(a) == set(bf)
    bad = sum(1 for t in set(a) & set(bf) for s in set(a[t]) | set(bf[t]) if a[t].get(s) != bf[t].get(s))
    out[d] = dict(a_x_cells=ax, n_cells_ref_nonx=n_cells, n_cells_a=sum(len(m) for m in a.values()), same_minutes=same_min, bad_cells=bad,
                  b_x_cells=sum(1 for m in b.values() for s in m if s in X))
    print(d, out[d], flush=True)
ok = all(v["a_x_cells"] == 0 and v["same_minutes"] and v["bad_cells"] == 0 and v["n_cells_a"] == v["n_cells_ref_nonx"] for v in out.values())
json.dump(dict(ok=ok, days=out), open("/kaggle/working/v1.json", "w"), indent=1)
print("V1_OK", ok)
sys.exit(0 if ok else 1)
'''


def push_v1():
    tag = "nt-v1"
    fol = E.WD + "/" + tag; os.makedirs(fol, exist_ok=True)
    code = V1K.replace("__JBIN__", repr(open(os.path.join(os.path.dirname(E.JW), "jbin.py")).read())).replace(
        "__X__", repr(json.dumps(sorted(X)))).replace("__DAYS__", repr(json.dumps(V1_DAYS)))
    compile(code, "k", "exec")
    open(fol + "/run.py", "w").write(code)
    md = {"id": USER + "/" + tag, "title": tag, "code_file": "run.py", "language": "python", "kernel_type": "script",
          "is_private": True, "enable_gpu": False, "enable_internet": False, "dataset_sources": [], "competition_sources": [],
          "kernel_sources": [USER + "/nt-tk26", USER + "/ho4p1-tk26"]}
    json.dump(md, open(fol + "/kernel-metadata.json", "w"), indent=1)
    r = E.api().kernels_push(fol)
    log.info("PUSHED %s %s", tag, getattr(r, "url", r))


def make_arts_nt():
    od = E.WD + "/out/"
    E.fetch("nt-chain-y26", r"(^|/)(MANIFEST\.json|result\.json)$")
    man = json.load(open(od + "nt-chain-y26/out/MANIFEST.json"))
    E.fetch("nt-tk26", r"tk_raw_md5\.json$")
    tkm = json.load(open(od + "nt-tk26/tk_raw_md5.json"))
    want, uni = {}, {}
    for q_, k in QK_NT.items():
        E.fetch(k, r"(^|/)(ticker_raw_md5\.json|universe_by_month\.json|universe_excl\.json|MANIFEST\.json)$")
        want[q_] = json.load(open(od + k + "/out/ticker_raw_md5.json"))
        uni[q_] = json.load(open(od + k + "/out/universe_by_month.json"))
    bad = [d for d, q_ in ST.days() if tkm.get("ticker_%s.bin" % d) != want[q_]["ticker_%s.bin" % d]]
    assert not bad and len(tkm) == 273, ("tk md5 != exporter", bad[:5], len(tkm))
    ux = {q_ + ":" + m: sorted(set(v) & set(X)) for q_, u in uni.items() for m, v in u.items()}
    a = dict(chain_slug="nt-chain-y26", tk_slug="nt-tk26", tk_md5=tkm,
             preds={str(s): man["pred_s%d/pred.bin" % s]["md5"] for s in SEEDS},
             bins_md5={"predict_wf_%s.bin" % c: man["bins/predict_wf_%s.bin" % c]["md5"] for c in ("20260101", "20260401", "20260701")},
             market_md5=man["market.bin"]["md5"], universe_x_hits={k: v for k, v in ux.items() if v},
             universe_n={q_ + ":" + m: len(v) for q_, u in uni.items() for m, v in u.items()})
    assert not a["universe_x_hits"], ("V1: symbol X trong universe A1", a["universe_x_hits"])
    json.dump(a, open(W + "/arts_nt.json", "w"), indent=1)
    log.info("ARTS_NT %s", json.dumps({k: v for k, v in a.items() if k not in ("tk_md5",)}))
    return a


# ---------------- sim ----------------
def ctx(kind):
    if kind == "orig":
        q.ARTS, q.CHAIN, q.TKK, q.FUND = ARTS0, ARTS0["chain_slug"], ARTS0["tk_slug"], dict(FUND0)
    else:
        an = json.load(open(W + "/arts_nt.json"))
        q.ARTS, q.CHAIN, q.TKK = an, an["chain_slug"], an["tk_slug"]
        q.FUND = dict(FUND0, bins_md5=an["bins_md5"])


def sim_specs():
    k24 = dict(q.CFGS["k24"])
    sp = {"a0p2-k24-s-s42": ("orig", 42, dict(k24, SIM_CRASH_ENTRY_PENALTY=q.PEN)), "a0p2-k24-b-s42": ("orig", 42, dict(k24)),
          "a0p-x14-s42": ("orig", 42, dict(k24, SIM_LOSER_TS_EXT_HOURS=336, SIM_LOSER_TS_EXT_DAYS=FLAGS0))}
    for s in SEEDS:
        sp["nt-k24-s-s%d" % s] = ("nt", s, dict(k24, SIM_CRASH_ENTRY_PENALTY=q.PEN))
        sp["nt-k24-b-s%d" % s] = ("nt", s, dict(k24))
        sp["nt-x14-s%d" % s] = ("nt", s, dict(k24, SIM_LOSER_TS_EXT_HOURS=336, SIM_LOSER_TS_EXT_DAYS=FLAGS1))
    return sp


def tsx_line(txt):
    m = re.findall(r"\[TSX\] extHours=(\d+) extDays=(\d+) deferTicks=(\d+) deferClusters=(\d+) cutAfterDefer=(\d+)", txt)
    return [int(x) for x in m[-1]] if m else None


def post_sim(tag, kind, seed, ov):
    ctx(kind); use_jar(ov)
    ok, chk, md5, n = q.check(tag, ov, seed, True)
    tl = tsx_line(q.kernel_text(tag))
    r = dict(tag=tag, ok=ok, chk=chk, md5=md5, n=n, tsx=tl)
    if "SIM_LOSER_TS_EXT_HOURS" in ov:
        r["tsx_ok"] = tl is not None and tl[0] == 336
    else:
        r["tsx_ok"] = tl is None or tl[0] == 0
    import pandas as pd
    d = pd.read_csv("/home/ubuntu/kaggle_sim/out/%s/storage/printDone.csv" % tag, index_col=False, dtype=str) if md5 else None
    if d is not None:
        r["x_legs"] = int((d.sym.str.strip() + "USDT").isin(set(X)).sum())
        ref = "ho4-k24-s-s%d" % seed if ov.get("SIM_CRASH_ENTRY_PENALTY") else "ho4-k24-b-s%d" % seed
        b = pd.read_csv("/home/ubuntu/kaggle_sim/out/%s/storage/printDone.csv" % ref, index_col=False, dtype=str)
        cut = "20251224"
        aa = d[d.start < cut].sort_values(list(d.columns)).reset_index(drop=True)
        bb = b[b.start < cut].sort_values(list(b.columns)).reset_index(drop=True)
        r["pre_same_as_" + ref] = bool(aa.equals(bb))
    r["pass"] = bool(ok and r["tsx_ok"] and (kind == "orig" or r.get("x_legs") == 0))
    json.dump(r, open(W + "/res/%s.json" % tag, "w"), indent=1)
    log.info("POST %s pass=%s md5=%s n=%s tsx=%s xlegs=%s chk=%s", tag, r["pass"], md5, n, tl, r.get("x_legs"), chk)
    return r


# ---------------- vong lap ----------------
def running():
    out = []
    for k in KS._api().kernels_list(mine=True, page_size=60, sort_by="dateRun"):
        try:
            s = KS._status(k.ref)
        except Exception:  # noqa: BLE001
            continue
        if s in ("RUNNING", "QUEUED"):
            out.append(k.ref)
    return out


def jards():
    d = W + "/ds_" + JDS
    from kaggle.api.kaggle_api_extended import KaggleApi
    a = KaggleApi(); a.authenticate()
    if not os.path.exists(W + "/jards_created"):
        shutil.rmtree(d, ignore_errors=True); os.makedirs(d)
        os.link(NJAR, d + "/sim.jar")
        assert sha256(d + "/sim.jar") == NJAR_SHA
        r = subprocess.run([sys.executable, "-I", "/home/ubuntu/claude_master/nup3_wk/jar_sec_check.py", d + "/sim.jar", W + "/jar_sec_upload.json"],
                           capture_output=True, text=True)
        assert r.returncode == 0 and json.load(open(W + "/jar_sec_upload.json"))["ok"] is True, "JAR SEC CHECK FAIL -> KHONG UPLOAD"
        json.dump({"sim.jar_sha256": NJAR_SHA, "git": "0594986e", "privateconfig": "STUB"}, open(d + "/JAR_SHA.json", "w"))
        json.dump({"title": JDS, "id": USER + "/" + JDS, "licenses": [{"name": "CC0-1.0"}]}, open(d + "/dataset-metadata.json", "w"))
        a.dataset_create_new(d, public=False, quiet=True, dir_mode="skip")
        log.info("CREATED dataset %s (jar sec ok)", JDS)
        open(W + "/jards_created", "w").write(time.strftime("%F %T"))
    for _ in range(60):
        try:
            st = str(a.dataset_status(USER + "/" + JDS))
        except Exception as e:  # noqa: BLE001
            st = "err " + str(e)[:40]
        if "ready" in st.lower():
            log.info("dataset %s ready", JDS); return True
        time.sleep(30)
    raise SystemExit("dataset jar khong ready")


def jards_sim():
    d = W + "/ds_" + SJDS
    from kaggle.api.kaggle_api_extended import KaggleApi
    a = KaggleApi(); a.authenticate()
    if not os.path.exists(W + "/jards_sim_created"):
        shutil.rmtree(d, ignore_errors=True); os.makedirs(d)
        os.link(SJAR, d + "/sim.jar")
        assert sha256(d + "/sim.jar") == SJAR_SHA
        shutil.copyfile(PROF, d + "/" + os.path.basename(PROF))
        r = subprocess.run([sys.executable, "-I", "/home/ubuntu/claude_master/nup3_wk/jar_sec_check.py", d + "/sim.jar", W + "/sim_jar_sec_upload.json"],
                           capture_output=True, text=True)
        assert r.returncode == 0 and json.load(open(W + "/sim_jar_sec_upload.json"))["ok"] is True, "SIM JAR SEC CHECK FAIL -> KHONG UPLOAD"
        assert not re.search(r"[A-Za-z0-9]{40,}", open(PROF).read()), "prof co chuoi dai nghi van"
        json.dump({"title": SJDS, "id": USER + "/" + SJDS, "licenses": [{"name": "CC0-1.0"}]}, open(d + "/dataset-metadata.json", "w"))
        a.dataset_create_new(d, public=False, quiet=True, dir_mode="skip")
        open(W + "/jards_sim_created", "w").write(time.strftime("%F %T"))
        log.info("CREATED dataset %s (jar sec ok)", SJDS)
    for _ in range(60):
        try:
            st = str(a.dataset_status(USER + "/" + SJDS))
        except Exception as e:  # noqa: BLE001
            st = "err " + str(e)[:40]
        if "ready" in st.lower():
            log.info("dataset %s ready", SJDS); return True
        time.sleep(30)
    raise SystemExit("dataset sim jar khong ready")


def main():
    st = json.load(open(STP)) if os.path.exists(STP) else {}
    os.makedirs(W + "/res", exist_ok=True)
    SP = sim_specs()
    DATA = [("a0p-x26-q1", lambda: push_exp("a0p-x26-q1", "q1", False), []),
            ("nt-x26-q1", lambda: push_exp("nt-x26-q1", "q1", True), []),
            ("nt-x26-q2", lambda: push_exp("nt-x26-q2", "q2", True), []),
            ("nt-x26-q3", lambda: push_exp("nt-x26-q3", "q3", True), []),
            ("nt-tk26", push_tk, ["nt-x26-q1", "nt-x26-q2", "nt-x26-q3"]),
            ("nt-chain-y26", push_chain, ["nt-x26-q1", "nt-x26-q2", "nt-x26-q3"]),
            ("nt-v1", push_v1, ["nt-tk26"])]
    order = [t for t, _, _ in DATA[:1]] + ["a0p2-k24-s-s42", "a0p2-k24-b-s42", "a0p-x14-s42"] + [t for t, _, _ in DATA[1:]]
    for s in SEEDS:
        order += ["nt-k24-s-s%d" % s, "nt-k24-b-s%d" % s, "nt-x14-s%d" % s]
    dspec = {t: (f, deps) for t, f, deps in DATA}
    for t in order:
        st.setdefault(t, {"state": "todo", "pushes": 0})
    st.setdefault("gates", {"a": None, "b": None})
    json.dump(st, open(STP, "w"), indent=1)
    if not st.get("jards"):
        jards(); st["jards"] = True; json.dump(st, open(STP, "w"), indent=1)
    if not st.get("jards_sim"):
        jards_sim(); st["jards_sim"] = True; json.dump(st, open(STP, "w"), indent=1)
    while True:
        # 1) thu ket qua
        for t in order:
            s = st[t]
            if s["state"] != "pushed" or time.time() - s.get("t", 0) < 300:
                continue
            try:
                k = KS._status(KS.kernel_ref(t) if t in SP else USER + "/" + t)
            except Exception as e:  # noqa: BLE001
                log.info("status %s %s", t, str(e)[:80]); continue
            if k not in KS.TERMINAL:
                continue
            s["kstatus"] = k
            if t in SP:
                try:
                    KS.fetch(t)
                except Exception as e:  # noqa: BLE001
                    log.warning("fetch %s %s", t, str(e)[:150])
                kind, seed, ov = SP[t]
                r = post_sim(t, kind, seed, ov)
                infra = (k != "COMPLETE") or not r["chk"].get("ok") or not r["chk"].get("n")
                if r["pass"]:
                    s["state"] = "done"; s["md5"] = r["md5"]
                elif infra and s["pushes"] < 2:
                    s["state"] = "todo"; log.warning("LOI HA TANG %s %s -> day lai 1 lan cfg y het", t, k)
                else:
                    s["state"] = "failed"
            else:
                if k == "COMPLETE":
                    s["state"] = "done"
                elif s["pushes"] < 2:
                    s["state"] = "todo"; log.warning("LOI HA TANG %s %s -> day lai 1 lan", t, k)
                else:
                    s["state"] = "failed"
            log.info("KERNEL %s -> %s (%s)", t, s["state"], k)
            json.dump(st, open(STP, "w"), indent=1)
        # 2) cong
        g = st["gates"]
        if g["a"] is None and st["a0p-x26-q1"]["state"] in ("done", "failed"):
            if st["a0p-x26-q1"]["state"] == "done":
                E.fetch("a0p-x26-q1", r"(^|/)(MANIFEST\.json|result\.json)$")
                ma = json.load(open(E.WD + "/out/a0p-x26-q1/out/MANIFEST.json"))
                mb = json.load(open(Q1_MAN))
                same = sum(1 for k_ in mb if k_ in ma and ma[k_]["md5"] == mb[k_]["md5"])
                g["a"] = bool(set(ma) == set(mb) and same == len(mb))
                g["a_detail"] = dict(n_new=len(ma), n_ref=len(mb), same=same, diff=sorted(k_ for k_ in mb if k_ not in ma or ma[k_]["md5"] != mb[k_]["md5"])[:20])
            else:
                g["a"] = False
            log.info("CONG A0'(a) exporter q1 = %s %s", g["a"], g.get("a_detail"))
            json.dump(st, open(STP, "w"), indent=1)
        if g["b"] is None and all(st[t]["state"] in ("done", "failed") for t in WANT0):
            g["b_detail"] = {t: (st[t].get("md5"), WANT0[t]) for t in WANT0}
            g["b"] = all(st[t]["state"] == "done" and (st[t].get("md5") or "").startswith(WANT0[t]) for t in WANT0)
            log.info("CONG A0'(b) sim s42 = %s %s", g["b"], g["b_detail"])
            json.dump(st, open(STP, "w"), indent=1)
        if g["a"] is False or g["b"] is False:
            log.error("CONG A0' FAIL -> KHONG day sim A1 (prereg §4: can A0' day du). DUNG de MASTER/agent quyet.")
            break
        if st["nt-chain-y26"]["state"] == "done" and st["nt-tk26"]["state"] == "done" and not os.path.exists(W + "/arts_nt.json"):
            make_arts_nt()
        # 3) day
        try:
            busy = running()
        except Exception as e:  # noqa: BLE001
            log.warning("running %s", str(e)[:100]); time.sleep(POLL); continue
        for t in order:
            if len(busy) >= MAXPAR:
                break
            s = st[t]
            if s["state"] != "todo":
                continue
            if t in dspec:
                f, deps = dspec[t]
                if not all(st[d]["state"] == "done" for d in deps):
                    continue
            elif t.startswith("nt-"):
                if not (g["a"] is True and g["b"] is True and os.path.exists(W + "/arts_nt.json") and st["nt-v1"]["state"] == "done"):
                    continue
            try:
                if t in dspec:
                    dspec[t][0]()
                else:
                    kind, seed, ov = SP[t]
                    ctx(kind); use_jar(ov)
                    q.push(KS, t, ov, seed, "20261001", True)
                s.update(state="pushed", t=time.time(), at=time.strftime("%F %T"))
                s["pushes"] += 1
                busy.append(t)
            except Exception as e:  # noqa: BLE001
                log.error("push %s %s", t, str(e)[:300])
                s["pushes"] += 1
                if s["pushes"] >= 2:
                    s["state"] = "failed"
            json.dump(st, open(STP, "w"), indent=1)
            time.sleep(20)
        done = sum(st[t]["state"] in ("done", "failed") for t in order)
        log.info("POLL busy=%d done=%d/%d gates=%s", len(busy), done, len(order), {k_: g[k_] for k_ in ("a", "b")})
        if done == len(order):
            log.info("XONG: %s", {t: st[t]["state"] for t in order})
            break
        time.sleep(POLL)


if __name__ == "__main__":
    if sys.argv[1] == "dry":
        sp = sim_specs()
        for t in ("a0p-x26-q1", "nt-x26-q1"):
            c = exp_cfg(t, "q1", t.startswith("nt"))
            print(t, c["jar_ds"], c["jar_sha"][:8], len(c.get("exclude", [])))
        compile(RUN_NT.replace("__CFG__", repr("{}")).replace("__CHSRC__", repr(CH_NT)), "k", "exec")
        print("specs", len(sp), {k: v[2].get("SIM_LOSER_TS_EXT_DAYS", "")[-20:] for k, v in sp.items() if "x14" in k and k.endswith("s42")})
        print("tsx jar", q.JAR_SHA[:8], "template ok", len(q.template()))
    else:
        main()
