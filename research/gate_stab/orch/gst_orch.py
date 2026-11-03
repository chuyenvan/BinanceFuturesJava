#!/usr/bin/env python3
"""GATE SEED A (PREREG_PARITY_V12_DRY ADD3 299f00b0 / ADD4 feb32107 / ADD5 5ffb3402) — orchestrator Kaggle Q4.
Chuoi: jar dataset gst-sim-jar -> [gs-oi-c || gs-x26-q4] -> gs-tk26 -> gs-chain-q4 -> sim gs-x14-s42 (dump+trace) -> fetch -> seed + V-OVL.
Tong <= 2 kernel dang chay tren account (dem qua API). Co ~/claude_master/locks/kaggle_priority khi dang push (NUP4 nhuong); xoa khi xong/loi.
Usage: python3 gst_orch.py dry | run | status"""
import atexit, datetime, glob, hashlib, json, logging, os, re, shutil, signal, subprocess, sys, time
G = "/home/ubuntu/claude_master/gst1030"
OD = G + "/orch"
os.makedirs(OD, exist_ok=True)
sys.path.insert(0, "/home/ubuntu/claude_master/ho_tradfi_wk")
import notf_orch as N                                     # noqa: E402  (tai dung KX_NT, CH_NT, RUN_NT, X, ST, CO, q, KS, E)
for h in list(logging.getLogger().handlers):
    logging.getLogger().removeHandler(h)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout, force=True)
_fh = logging.FileHandler(OD + "/orch.log"); _fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
logging.getLogger().addHandler(_fh)
log = logging.getLogger("gst")
E, q, KS, CO, USER = N.E, N.q, N.KS, N.CO, N.USER
E.WD = OD + "/kaggle"; os.makedirs(E.WD, exist_ok=True)
STP = OD + "/state.json"
PRIO = "/home/ubuntu/claude_master/locks/kaggle_priority"
MAXPAR, POLL = 2, 180
H7 = 7 * 3600000
def ms7(y, m, d):
    return int(datetime.datetime(y, m, d, tzinfo=datetime.timezone.utc).timestamp() * 1000) - H7
END3, TCUT = ms7(2026, 10, 1), ms7(2026, 11, 1)
TR_FROM = ms7(2026, 7, 15)
assert END3 == 1790787600000 and TCUT == 1793466000000
JAR = G + "/wt/target/binance-java-sdk-1.2.4.jar"
JAR_SHA = "f2d57e01e77071b4641e06cfce32fd7cbb75afa2e998ad67e332a42c628ea04c"
JDS = "gst-sim-jar"
PROF = "/home/ubuntu/claude_master/tsx/ds_sim-jar-tsx/prof_r4_kg0_k16_f015_g155.properties"
QK4 = dict(N.QK_NT, q4="gs-x26-q4")
SIM = "gs-x14-s42"
DUMP_K, TRACE_K = "/kaggle/working/gate_seed_A.bin", "/kaggle/working/gate_trace_A.csv"
OV = dict(q.CFGS["k24"], SIM_LOSER_TS_EXT_HOURS=336, SIM_LOSER_TS_EXT_DAYS=N.FLAGS1,
          SIM_GATE_DUMP_FILE=DUMP_K, SIM_GATE_DUMP_AT=str(TCUT),
          SIM_GATE_TRACE_FILE=TRACE_K, SIM_GATE_TRACE_FROM=str(TR_FROM), SIM_GATE_TRACE_TO=str(TCUT))


def sha256(p):
    return N.sha256(p)


# ---------------- Vision + cong E ----------------
VS = ("BTCUSDT", "ETHUSDT", "SOLUSDT", "PARTIUSDT", "BLESSUSDT")
OCT = ["2026-10-%02d" % d for d in range(1, 32)]
KMODE = {"m": None}                                     # "monthly" | "daily" | None (chua du)


def _head(paths):
    import urllib.request
    from concurrent.futures import ThreadPoolExecutor
    U = "https://data.binance.vision/data/futures/um/"
    def one(p):
        for a in range(3):
            try:
                return p, urllib.request.urlopen(urllib.request.Request(U + p, method="HEAD", headers={"User-Agent": "gst"}), timeout=30).status
            except Exception as e:  # noqa: BLE001
                c = getattr(e, "code", None)
                if c == 404:
                    return p, 404
                time.sleep(2)
        return p, "err"
    with ThreadPoolExecutor(16) as ex:
        return dict(ex.map(one, paths))


def vision_ready():
    """Kiem DU moi ngay can dung (ADD5 + fix 11-02): klines monthly 2026-10 uu tien (du 5 symbol mau); neu chua co thi daily
    PHAI du 31 ngay lien tuc cho 5 symbol mau; funding monthly 2026-10; metrics daily DU 31 ngay (OI). Tra (ok, thieu, mode)."""
    mon = _head(["monthly/klines/%s/1m/%s-1m-2026-10.zip" % (s, s) for s in VS])
    fund = _head(["monthly/fundingRate/%s/%s-fundingRate-2026-10.zip" % (s, s) for s in VS])
    met = _head(["daily/metrics/%s/%s-metrics-%s.zip" % (s, s, d) for s in VS for d in OCT])
    if all(v == 200 for v in mon.values()):
        mode, kl = "monthly", {}
    else:
        kl = _head(["daily/klines/%s/1m/%s-1m-%s.zip" % (s, s, d) for s in VS for d in OCT])
        mode = "daily" if all(v == 200 for v in kl.values()) else None
    miss = sorted(p for dct in (fund, met, kl) for p, v in dct.items() if v != 200)
    if mode is None:
        miss = sorted(set(miss) | {p for p, v in mon.items() if v != 200})
    ok = mode is not None and all(v == 200 for v in fund.values()) and all(v == 200 for v in met.values())
    KMODE["m"] = mode
    return ok, (miss[:12] + (["... +%d" % (len(miss) - 12)] if len(miss) > 12 else [])), mode


def gate_e():
    g = json.load(open(G + "/seed/gateE.json"))
    return g.get("PASS") is True


# ---------------- kernel builders ----------------
def oi_code():
    src = open("/home/ubuntu/claude_master/1011/ho4p1/kaggle/ho4p1-oi-a/run.py").read()
    a = 'pd.Timestamp("2026-10-04", tz="UTC")'; b = 'LAST_DATE = "2026-10-03"'
    assert src.count(a) == 1 and src.count(b) == 1, (src.count(a), src.count(b))
    return src.replace(a, 'pd.Timestamp("2026-11-01", tz="UTC")').replace(b, 'LAST_DATE = "2026-10-31"')


def x26_cfg():
    c = N.exp_cfg("gs-x26-q4", "q3", True)
    c["tag"] = "gs-x26-q4"
    c["S"] = [END3, TCUT]
    if KMODE["m"] == "monthly":                                        # monthly uu tien
        c["months"], c["days"] = ["2026-09", "2026-10"], []
    else:                                                              # ADD5: daily 10-01..10-31 (chi khi du lien tuc)
        assert KMODE["m"] == "daily", "Vision chua du"
        c["months"], c["days"] = ["2026-09"], list(OCT)
    c["fund_months"] = ["2026-08", "2026-09", "2026-10"]
    c["ingest"] = ["20260901", "20261031"]
    T = {t["name"]: t for t in c["tasks"]}
    assert set(T) == {"mkt", "gate", "t1", "lab"}, set(T)
    T["mkt"]["cfg"]["TIME_RUN"] = "20260901"
    T["gate"]["args"][0:2] = ["20260920", "20261101"]
    T["t1"]["args"][0:2] = ["20261001", "20261101"]
    T["lab"]["args"][0:2] = ["20261001", "20261101"]
    return c


K28_DS = "gst-kline-1028"
K28_ANCHOR = "KL = {}\nfor s in sorted(PARTS):\n"
K28_SRC = '''# [ADD7 53ea666e] ngay 2026-10-28 (Vision thieu) tu REST Oracle, dataset gst-kline-1028, dang zip Vision.
# Kaggle TU GIAI NEN zip khi tao dataset => file thuc te: <S>-1m-2026-10-28/<S>-1m-2026-10-28.csv. Doc ca .zip lan .csv;
# .csv duoc goi lai thanh zip trong bo nho de di CUNG ham _parse (khong doi cach doc cot).
_X28 = sorted(glob.glob("/kaggle/input/**/*-1m-2026-10-28.csv", recursive=True) + glob.glob("/kaggle/input/**/*-1m-2026-10-28.zip", recursive=True))
LOG.info("ADD7 tim thay %d file 10-28, vi du %s", len(_X28), _X28[:1])
_KS = set(ksyms); _n28 = 0; _seen28 = set()
for _p in _X28:
    _s = os.path.basename(_p).split("-1m-")[0]
    if _s not in _KS or _s in _seen28:
        continue
    _seen28.add(_s)
    if _p.endswith(".csv"):
        _bio = io.BytesIO()
        with zipfile.ZipFile(_bio, "w") as _z:
            _z.writestr(os.path.basename(_p), open(_p, "rb").read())
        _r = _parse(_bio.getvalue())
    else:
        _r = _parse(open(_p, "rb").read())
    if _r is not None:
        PARTS.setdefault(_s, []).append(_r); _n28 += 1
RES["steps"]["add7_1028"] = dict(files=len(_X28), used=_n28)
LOG.info("ADD7 10-28 REST: %d file, %d symbol dung", len(_X28), _n28)
assert _n28 >= 500, "ADD7: thieu file 10-28"
'''


def x26_code(cfg):
    kx = N.KX_NT
    assert kx.count(K28_ANCHOR) == 1, "anchor ADD7"
    kx = kx.replace(K28_ANCHOR, K28_SRC + K28_ANCHOR)
    return kx.replace("__CFG_JSON__", repr(json.dumps(cfg))).replace("__JW_SRC__", repr(open(E.JW).read())).replace(
        "__JBIN_SRC__", repr(open(os.path.join(os.path.dirname(E.JW), "jbin.py")).read()))


def k28_ds(dry):
    d = G + "/k1028/zips"
    n = len(glob.glob(d + "/*-1m-2026-10-28.zip"))
    assert n >= 500, ("thieu zip 10-28", n)
    assert json.load(open(G + "/k1028/gateR.json")).get("PASS") is True, "cong R chua PASS"
    if dry or os.path.exists(OD + "/k28_created"):
        log.info("dataset %s: %d zip (%s)", K28_DS, n, "dry" if dry else "da tao"); return
    from kaggle.api.kaggle_api_extended import KaggleApi
    a = KaggleApi(); a.authenticate()
    json.dump({"title": K28_DS, "id": USER + "/" + K28_DS, "licenses": [{"name": "CC0-1.0"}]}, open(d + "/dataset-metadata.json", "w"))
    a.dataset_create_new(d, public=False, quiet=True, dir_mode="skip")
    open(OD + "/k28_created", "w").write(time.strftime("%F %T"))
    for _ in range(60):
        try:
            if "ready" in str(a.dataset_status(USER + "/" + K28_DS)).lower():
                log.info("dataset %s ready (%d zip)", K28_DS, n); return
        except Exception:  # noqa: BLE001
            pass
        time.sleep(30)
    raise SystemExit("dataset 10-28 khong ready")


def tk_days():
    d, out = datetime.date(2026, 1, 1), []
    while d <= datetime.date(2026, 10, 31):
        out.append((d.strftime("%Y%m%d"), "q1" if d.month <= 3 else "q2" if d.month <= 6 else "q3" if d.month <= 9 else "q4"))
        d += datetime.timedelta(days=1)
    assert len(out) == 304
    return out


def tk_code():
    return N.ST.TK.replace("__DAYS__", repr(json.dumps(tk_days()))).replace("__QK__", repr(json.dumps(QK4)))


def chain_src():
    s = N.CH_NT
    R = [('    SEAL, A1, A2, END = 1767200400000, 1774976400000, 1782838800000, 1790787600000\n',
          '    SEAL, A1, A2, END = 1767200400000, 1774976400000, 1782838800000, 1790787600000\n    END4 = %d                                   # GATE SEED Q4 (ADD3)\n' % TCUT),
         ('    U1, U2 = ms_utc("2026-04-01"), ms_utc("2026-07-01")\n',
          '    U1, U2, U3 = ms_utc("2026-04-01"), ms_utc("2026-07-01"), ms_utc("2026-10-01")\n'),
         ('    QB = [("q1", SEAL, A1), ("q2", A1, A2), ("q3", A2, END)]\n',
          '    QB = [("q1", SEAL, A1), ("q2", A1, A2), ("q3", A2, END), ("q4", END, END4)]\n'),
         ('    build_oi(ms_utc("2025-11-01"), SEAL, END + 3 * 86400000)\n',
          '    build_oi(ms_utc("2025-11-01"), SEAL, END4 + 3 * 86400000)\n'),
         ('             ("20260701", A2, END, [(p, 0, U2) for p in tq["q2"]] + [(p, U2, 1 << 62) for p in tq["q3"]]))\n',
          '             ("20260701", A2, END, [(p, 0, U2) for p in tq["q2"]] + [(p, U2, 1 << 62) for p in tq["q3"]]),\n'
          '             ("20261001", END, END4, [(p, 0, U3) for p in tq["q3"]] + [(p, U3, 1 << 62) for p in tq["q4"]]))\n'),
         ('                       (one("CLOSES_1H_vision1m.bin", QS["q3"]), A2, 1 << 62)])\n',
          '                       (one("CLOSES_1H_vision1m.bin", QS["q3"]), A2, END), (one("CLOSES_1H_vision1m.bin", QS["q4"]), END, 1 << 62)])\n'),
         ('ms_utc("2025-11-15"), ms_utc("2026-10-01"), SEAL - 24 * H', 'ms_utc("2025-11-15"), ms_utc("2026-11-01"), SEAL - 24 * H'),
         ('    cuts = ["20260101", "20260401", "20260701"]\n', '    cuts = ["20260101", "20260401", "20260701", "20261001"]\n')]
    for a, b in R:
        assert s.count(a) == 1, ("anchor chain", a[:60], s.count(a))
        s = s.replace(a, b)
    compile(s, "chain_q4", "exec")
    return s


def chain_code():
    cfg = dict(mode="y26", tag="gs-chain-q4", model_sha=CO.MODEL_SHA, pin_sha=CO.PIN_SHA, seeds=[42], q_src=QK4, oi_src="gs-oi-c",
               exclude_syms=sorted(N.X), exclude_md5=N.XMD5)
    return N.RUN_NT.replace("__CFG__", repr(json.dumps(cfg))).replace("__CHSRC__", repr(chain_src()))


def md(tag, internet, dss, kss):
    return {"id": USER + "/" + tag, "title": tag, "code_file": "run.py", "language": "python", "kernel_type": "script",
            "is_private": True, "enable_gpu": False, "enable_internet": internet, "dataset_sources": [USER + "/" + d for d in dss],
            "competition_sources": [], "kernel_sources": [USER + "/" + k for k in kss]}


def build(tag):
    if tag == "gs-oi-c":
        return oi_code(), md(tag, True, ["funding-oi-percoin"], [])
    if tag == "gs-x26-q4":
        c = x26_cfg()
        return x26_code(c), md(tag, True, sorted({c["jar_ds"], c["cfg_ds"], c["as_ds"], c["asdata_ds"], c["dev_market_ds"], K28_DS}), [])
    if tag == "gs-tk26":
        return tk_code(), md(tag, False, [], sorted(QK4.values()))
    if tag == "gs-chain-q4":
        return chain_code(), md(tag, True, ["ho4p1-code", "funding-oi-percoin", "sim-ho26a-bundle", "ho26-pred-s42"],
                                ["gs-oi-c"] + sorted(QK4.values()))
    raise KeyError(tag)


def push_data(tag, dry):
    code, meta = build(tag)
    compile(code, tag, "exec")
    fol = E.WD + "/" + tag; os.makedirs(fol, exist_ok=True)
    open(fol + "/run.py", "w").write(code)
    json.dump(meta, open(fol + "/kernel-metadata.json", "w"), indent=1)
    if dry:
        log.info("DRY %s: run.py %d byte, ds=%s ks=%s", tag, len(code), meta["dataset_sources"], meta["kernel_sources"]); return
    r = E.api().kernels_push(fol)
    url = getattr(r, "url", None)
    assert url, ("push that bai (URL rong)", tag, r)
    log.info("PUSHED %s %s", tag, url)


# ---------------- jar dataset ----------------
def jards(dry):
    assert sha256(JAR) == JAR_SHA, "jar sha"
    d = OD + "/ds_" + JDS
    if dry:
        log.info("DRY jar %s sha ok, se upload dataset %s", JAR, JDS); return
    from kaggle.api.kaggle_api_extended import KaggleApi
    a = KaggleApi(); a.authenticate()
    if not os.path.exists(OD + "/jards_created"):
        shutil.rmtree(d, ignore_errors=True); os.makedirs(d)
        os.link(JAR, d + "/sim.jar"); shutil.copyfile(PROF, d + "/" + os.path.basename(PROF))
        r = subprocess.run([sys.executable, "-I", "/home/ubuntu/claude_master/nup3_wk/jar_sec_check.py", d + "/sim.jar", OD + "/jar_sec.json"],
                           capture_output=True, text=True)
        assert r.returncode == 0 and json.load(open(OD + "/jar_sec.json"))["ok"] is True, "JAR SEC CHECK FAIL -> KHONG UPLOAD"
        json.dump({"title": JDS, "id": USER + "/" + JDS, "licenses": [{"name": "CC0-1.0"}]}, open(d + "/dataset-metadata.json", "w"))
        a.dataset_create_new(d, public=False, quiet=True, dir_mode="skip")
        open(OD + "/jards_created", "w").write(time.strftime("%F %T"))
        log.info("CREATED dataset %s", JDS)
    for _ in range(60):
        try:
            st = str(a.dataset_status(USER + "/" + JDS))
        except Exception as e:  # noqa: BLE001
            st = "err " + str(e)[:40]
        if "ready" in st.lower():
            return
        time.sleep(30)
    raise SystemExit("dataset jar khong ready")


# ---------------- sim ----------------
def arts():
    od = E.WD + "/out/"
    E.fetch("gs-chain-q4", r"(^|/)(MANIFEST\.json|result\.json)$")
    man = json.load(open(od + "gs-chain-q4/out/MANIFEST.json"))
    E.fetch("gs-tk26", r"tk_raw_md5\.json$")
    tkm = json.load(open(od + "gs-tk26/tk_raw_md5.json"))
    assert len(tkm) == 304, len(tkm)
    a = dict(chain_slug="gs-chain-q4", tk_slug="gs-tk26", tk_md5=tkm, preds={"42": man["pred_s42/pred.bin"]["md5"]},
             bins_md5={"predict_wf_%s.bin" % c: man["bins/predict_wf_%s.bin" % c]["md5"] for c in ("20260101", "20260401", "20260701", "20261001")},
             market_md5=man["market.bin"]["md5"])
    json.dump(a, open(OD + "/arts.json", "w"), indent=1)
    return a


def sim_ctx(a):
    q.ARTS, q.CHAIN, q.TKK = a, a["chain_slug"], a["tk_slug"]
    q.FUND = dict(N.FUND0, bins_md5=a["bins_md5"], new_folds=sorted(a["bins_md5"]))
    q.JAR_DS, q.JAR_SHA = JDS, JAR_SHA


def push_sim(dry):
    a = json.load(open(OD + "/arts.json")) if os.path.exists(OD + "/arts.json") else None
    if dry:
        log.info("DRY sim %s ov=%s end=20261101 (arts %s)", SIM, json.dumps(OV), "co" if a else "chua co -> sau chain"); return
    sim_ctx(a)
    q.push(KS, SIM, dict(OV), 42, "20261101", True)


def post_sim():
    o = "/home/ubuntu/kaggle_sim/out/%s/" % SIM
    txt = q.kernel_text(SIM)
    rj = json.load(open(o + "result.json"))
    chk = dict(ok=rj.get("ok") is True, jar=rj.get("jar_sha256") == JAR_SHA,
               tk="TICKER_HO4P1 ok=304 bad=0 miss=0 extra=0 other=0" in txt,
               fund="FUND_HO4_OK" in txt, seed_dump="[GATE-SEED] DA GHI" in txt,
               dump_file=os.path.exists(o + "gate_seed_A.bin") or bool(glob.glob(o + "**/gate_seed_A.bin", recursive=True)),
               trace_file=bool(glob.glob(o + "**/gate_trace_A.csv*", recursive=True)))
    log.info("POST SIM %s", chk)
    return chk


# ---------------- vong lap ----------------
ORDER = ["gs-oi-c", "gs-x26-q4", "gs-tk26", "gs-chain-q4", SIM]
DEPS = {"gs-oi-c": [], "gs-x26-q4": [], "gs-tk26": ["gs-x26-q4"], "gs-chain-q4": ["gs-oi-c", "gs-x26-q4"], SIM: ["gs-tk26", "gs-chain-q4"]}


def prio_on():
    open(PRIO, "w").write("gst_orch pid %d %s\n" % (os.getpid(), time.strftime("%F %T")))


def prio_off(*_):
    try:
        os.remove(PRIO); log.info("XOA %s", PRIO)
    except FileNotFoundError:
        pass


def finish_seed():
    while time.strftime("%Y-%m-%d") == "2026-11-03":            # luat MASTER: 11-03 khong job nang Oracle (gio may = +07)
        log.info("11-03: hoan buoc build_seed/vovl toi 11-04"); time.sleep(1800)
    o = "/home/ubuntu/kaggle_sim/out/%s/" % SIM
    dump = (glob.glob(o + "**/gate_seed_A.bin", recursive=True) or [None])[0]
    tr = (glob.glob(o + "**/gate_trace_A.csv*", recursive=True) or [None])[0]
    shutil.copyfile(dump, G + "/seed/A_dump.bin")
    log.info("A_dump md5 %s", hashlib.md5(open(G + "/seed/A_dump.bin", "rb").read()).hexdigest())
    r = subprocess.run(["bash", G + "/seed/build_seed.sh"], capture_output=True, text=True,
                       env=dict(os.environ, A=G + "/seed/A_dump.bin", TCUT_MS=str(TCUT)))
    log.info("BUILD_SEED rc=%s %s", r.returncode, r.stdout[-1500:])
    L = sorted(glob.glob(G + "/seed/out_*/live_labeled.parquet"))[-1]
    r2 = subprocess.run([sys.executable, G + "/seed/vovl.py", "--trace", tr, "--live-labeled", L, "--tcut-ms", str(TCUT),
                         "--printdone", o + "storage/printDone.csv", "--out", G + "/seed/vovl_A.json"], capture_output=True, text=True)
    log.info("VOVL rc=%s %s", r2.returncode, r2.stdout[-2500:])


def main(dry):
    st = json.load(open(STP)) if os.path.exists(STP) else {}
    for t in ORDER:
        st.setdefault(t, {"state": "todo", "pushes": 0})
    ok, det, mon = vision_ready()
    log.info("VISION ready=%s klines_mode=%s thieu=%s", ok, mon, det)
    assert gate_e(), "cong E (ADD5) chua PASS"
    if not dry and st["gs-x26-q4"]["state"] == "done" and st["gs-tk26"]["state"] == "failed":
        log.error("state cu (x26 thieu 10-28) -> chay 'run_gst.sh rearm' truoc"); return 3
    if not dry:
        seen = 0                                   # can READY 2 lan cach >= 30 phut (cho Vision phat hanh xong moi symbol)
        while seen < 2:
            if ok and KMODE["m"] == "monthly":     # monthly da phat hanh = co dinh, khong can xac nhan lan 2
                break
            if ok:
                seen += 1
                if seen >= 2:
                    break
            else:
                seen = 0
            log.info("cho Vision (ready=%s, lan=%d) ...", ok, seen)
            time.sleep(1800)
            ok, det, mon = vision_ready()
            log.info("VISION ready=%s monthly10=%s %s", ok, mon, det)
    if dry and KMODE["m"] is None:
        KMODE["m"] = "daily"; log.info("DRY: Vision chua du -> compile thu voi mode daily")
    for t in ORDER[:-1]:
        code, meta = build(t); compile(code, t, "exec")
    log.info("build+compile 4 kernel du lieu OK (klines mode=%s); OV sim=%s", KMODE["m"], json.dumps(OV))
    jards(dry)
    k28_ds(dry)
    if dry:
        for t in ORDER[:-1]:
            push_data(t, True)
        push_sim(True)
        try:
            log.info("DRY running tren account: %s", N.running())
        except Exception as e:  # noqa: BLE001
            log.info("DRY running err %s", str(e)[:80])
        return 0
    prio_on(); atexit.register(prio_off)
    signal.signal(signal.SIGTERM, lambda *a: (prio_off(), sys.exit(1)))
    while True:
        for t in ORDER:
            s = st[t]
            if s["state"] != "pushed" or time.time() - s.get("t", 0) < 240:
                continue
            try:
                k = KS._status(KS.kernel_ref(t) if t == SIM else USER + "/" + t)
            except Exception as e:  # noqa: BLE001
                log.info("status %s %s", t, str(e)[:80]); continue
            if k not in KS.TERMINAL:
                continue
            s["kstatus"] = k
            if t == SIM and k == "COMPLETE":
                KS.fetch(t)
                c = post_sim(); s["chk"] = c
                s["state"] = "done" if all(c.values()) else "failed"
            elif k == "COMPLETE":
                s["state"] = "done"
            else:
                s["state"] = "todo" if s["pushes"] < 2 else "failed"
            log.info("KERNEL %s -> %s (%s)", t, s["state"], k)
            json.dump(st, open(STP, "w"), indent=1)
        if any(st[t]["state"] == "failed" for t in ORDER):
            log.error("CO KERNEL FAILED -> DUNG %s", {t: st[t]["state"] for t in ORDER}); return 1
        if st[SIM]["state"] == "done":
            finish_seed(); log.info("XONG"); return 0
        if st["gs-chain-q4"]["state"] == "done" and st["gs-tk26"]["state"] == "done" and not os.path.exists(OD + "/arts.json"):
            arts()
        try:
            busy = N.running()
        except Exception as e:  # noqa: BLE001
            log.warning("running %s", str(e)[:100]); time.sleep(POLL); continue
        for t in ORDER:
            if len(busy) >= MAXPAR:
                break
            s = st[t]
            if s["state"] != "todo" or not all(st[d]["state"] == "done" for d in DEPS[t]):
                continue
            if t == SIM and not os.path.exists(OD + "/arts.json"):
                continue
            try:
                push_sim(False) if t == SIM else push_data(t, False)
                s.update(state="pushed", t=time.time(), at=time.strftime("%F %T")); s["pushes"] += 1
                busy.append(t)
            except Exception as e:  # noqa: BLE001
                log.error("PUSH %s loi %s", t, str(e)[:200])
            json.dump(st, open(STP, "w"), indent=1)
        log.info("busy=%s state=%s", busy, {t: st[t]["state"] for t in ORDER})
        time.sleep(POLL)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "status":
        print(open(STP).read() if os.path.exists(STP) else "chua co state"); sys.exit(0)
    if cmd == "rearm":      # 11-02: x26-q4 thieu 10-28 -> chay lai x26/tk/chain/sim; GIU gs-oi-c done
        st = json.load(open(STP))
        for t in ("gs-x26-q4", "gs-tk26", "gs-chain-q4", SIM):
            st[t] = {"state": "todo", "pushes": 0, "prev": st.get(t)}
        json.dump(st, open(STP, "w"), indent=1)
        for f in (OD + "/arts.json",):
            if os.path.exists(f): os.rename(f, f + ".old_%d" % int(time.time()))
        print({t: st[t]["state"] for t in ORDER}); sys.exit(0)
    try:
        sys.exit(main(cmd == "dry"))
    finally:
        if cmd != "dry":
            prio_off()
