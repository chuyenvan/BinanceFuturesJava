#!/usr/bin/env python3
"""HO4-P1 orchestrator (PREREG_HOLDOUT2026H1 ADDENDUM-6 §6.6/§6.8, mau ho26_queue.py). CHI chay + parity, KHONG cham.
Pha 0: parity seal DONG (SIM_END_DATE=20251231) ho4p1-c1 (B0 K16 s42 phi goc vs de-p1 moi cot, mien tru in float32 trung bit)
       va ho4p1-c2 (K24+skipFull s42 phi goc, md5 == gqsf-a1 ad26fd55) voi bo artefact Vision moi (market/pred/funding/ticker).
       PASS ca 2 moi sang pha 1; FAIL => DUNG.
Pha 1: 32 kernel ho4-<cfg>-<b|s>-s<seed> = {b0,k24} x {b phi goc, s SIM_CRASH_ENTRY_PENALTY=0.01675} x 8 seed, jar b7c89f09,
       SIM_END_DATE=20261001, HOLDOUT_UNSEAL chi trong extra_env, ticker_min_days 2099, ticker 2026 273/273 md5 raw trong kernel.
       Xen ke theo seed (4 kernel cung seed lien nhau). <= 2 kernel song song (dem ca tai khoan).
KHONG doc eq/PnL, KHONG mo printDone/equity 2026: chi md5(printDone) + n_trades + check cau hinh.
queue_status.tsv: slug, status, md5_printDone, n, parity, time. Resume tu state.json. Input chot: arts.json (ho4p1_arts.py).
Usage: cd ~/claude_master/1011/ho4p1/q && setsid nohup python3 <repo>/research/analysis/ho4p1_queue.py > queue.out 2>&1 < /dev/null &"""
import csv, glob, hashlib, json, logging, os, re, subprocess, sys, time
R = "/home/ubuntu/src/BinanceFuturesJava"
sys.path.insert(0, R)
sys.path.insert(0, R + "/research/analysis")
import gate_ablation_driver as GA  # noqa: E402
D = "/home/ubuntu/claude_master/1011/ho4p1/q"
os.makedirs(D, exist_ok=True)
log = logging.getLogger("ho4p1q")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout, force=True)
_fh = logging.FileHandler(D + "/queue_py.log")
_fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
logging.getLogger().addHandler(_fh)
STATE, TSV = D + "/state.json", D + "/queue_status.tsv"
OUT = "/home/ubuntu/kaggle_sim/out/%s/"
MAX_PAR, POLL_S = 2, 120
BUNDLE, JAR_DS = "sim-ho26a-bundle", "sim-jar-nsel"
JAR_SHA = "b7c89f097241763bb240c24b411a66531b41dad12b1716f13237537386de62c2"
PRED_BASE = "22f69456381d9d1abd1592382c3b0319"
UNSEAL = "I_UNDERSTAND_THIS_BURNS_HOLDOUT_2026"
SEEDS = [42, 7, 13, 21, 99, 123, 777, 2024]
PEN = "0.01675"
B0 = dict(GA.B0OV)
K24 = dict(B0, SELECTOR_RANK_TOPK=24, GATE_QUOTA_SKIP_WHEN_FULL="true")
CFGS = {"b0": B0, "k24": K24}
PARITY = {"ho4p1-c1": (B0, "de-p1", "650c386f0d0dfea334af9d55ca2f21d4"),
          "ho4p1-c2": (K24, "gqsf-a1", "ad26fd55f0bb5db32038ec8b357cf8e7")}
ARTS = json.load(open("/home/ubuntu/claude_master/1011/ho4p1/arts.json"))
CHAIN, TKK = ARTS["chain_slug"], ARTS["tk_slug"]
assert len(ARTS["preds"]) == 8 and len(ARTS["tk_md5"]) == 273 and len(ARTS["bins_md5"]) == 3
SEAL, S_LO = 1767200400000, 1751302800000
FUND = {"lo": SEAL, "hi": 9 * 10**15, "self_lo": S_LO, "self_hi": SEAL,
        "self_folds": ["predict_wf_20250701.bin", "predict_wf_20251001.bin"],
        "new_folds": ["predict_wf_20260101.bin", "predict_wf_20260401.bin", "predict_wf_20260701.bin"],
        "bins_ds": "bins", "bins_md5": ARTS["bins_md5"]}
CODE_SHA = subprocess.run(["git", "-C", R, "rev-parse", "--short=8", "HEAD"], capture_output=True, text=True).stdout.strip()
BLK = open(R + "/research/analysis/ho4p1_tk_block.py").read() + open(R + "/research/analysis/ho4p1_fund_block.py").read()


def template():
    t = GA.template()
    assert t.count(GA.PATCH_ANCHOR) == 1
    t = t.replace(GA.PATCH_ANCHOR, BLK + GA.PATCH_ANCHOR)
    assert "NOWRITE_HOST" in t and "SYMBOL_MAPPER_PREFLIGHT_FAIL" in t and "TICKER_HO4P1_FAIL" in t and "FUND_HO4_OK" in t
    assert t.index("PRED_MD5_BASE") < t.index("TICKER_HO4P1_FAIL") < t.index("FUND_HO4_OK") < t.index(GA.PATCH_ANCHOR)
    compile(t.replace("__CFG_JSON__", repr("{}")), "kernel", "exec")
    return t


def build_queue():
    q = [(t, 0, dict(ov), 42, "20251231", False) for t, (ov, _, _) in PARITY.items()]
    for s in SEEDS:
        for c in ("b0", "k24"):
            q.append(("ho4-%s-b-s%d" % (c, s), 1, dict(CFGS[c]), s, "20261001", True))
            q.append(("ho4-%s-s-s%d" % (c, s), 1, dict(CFGS[c], SIM_CRASH_ENTRY_PENALTY=PEN), s, "20261001", True))
    for tg in ("ho4p1-dev-k24-s-s42", "ho4p1-dev-b0-s-s42"):         # P3-DEV chi bao (ho4p1_simdev.py)
        q.append((tg, 2, {}, 42, "20260101", False))
    return q


def push(ks, tag, ov, seed, end, unseal):
    ref = ks.kernel_ref(tag)
    folder = os.path.join(ks.WORKDIR, ks.slug(tag))
    os.makedirs(folder, exist_ok=True)
    cfg = {"tag": tag, "profile": GA.PROFILE, "overrides": dict(ov), "sim_end_date": end, "xmx": "22g",
           "timeout_s": 10800, "code_sha": CODE_SHA, "bins_ds": "", "jar_ds": JAR_DS, "market_ds": CHAIN,
           "market_align": False, "extra_env": ({"HOLDOUT_UNSEAL": UNSEAL} if unseal else {}),
           "ticker_min_days": 2099, "pred_ds": "pred_s%d" % seed, "want_pred_md5": ARTS["preds"][str(seed)],
           "want_pred_base": PRED_BASE, "tk_ho4p1": {"src": TKK, "md5": ARTS["tk_md5"]}, "fund_rebuild_ho4p1": FUND}
    with open(os.path.join(folder, "run.py"), "w") as f:
        f.write(template().replace("__CFG_JSON__", repr(json.dumps(cfg))))
    dss = [ks.USER + "/" + BUNDLE] + ks.TICKER_DS + [ks.USER + "/" + JAR_DS]
    md = {"id": ref, "title": ref.split("/")[1], "code_file": "run.py", "language": "python",
          "kernel_type": "script", "is_private": True, "enable_gpu": False, "enable_internet": True,
          "dataset_sources": dss, "competition_sources": [], "kernel_sources": [ks.USER + "/" + CHAIN, ks.USER + "/" + TKK]}
    with open(os.path.join(folder, "kernel-metadata.json"), "w") as f:
        json.dump(md, f, indent=1)
    r = ks._api().kernels_push(folder)
    log.info("PUSHED %s %s seed=%d end=%s unseal=%s ov=%s", tag, getattr(r, "url", r), seed, end, unseal, json.dumps(ov))


def md5f(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


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


def check(tag, ov, seed, unseal):
    o = OUT % tag
    try:
        rj = json.load(open(o + "result.json"))
    except Exception as e:  # noqa: BLE001
        return False, {"result_json": "thieu %s" % str(e)[:60]}, None, None
    pdp = o + "storage/printDone.csv"
    md5 = md5f(pdp) if os.path.exists(pdp) else None
    n = rj.get("n_trades")
    chk = {"ok": rj.get("ok") is True, "jar": rj.get("jar_sha256") == JAR_SHA}
    mp = rj.get("symbol_mapper")
    chk["mapper"] = isinstance(mp, int) and mp >= 800
    got = rj.get("overrides") or {}
    chk["ov"] = set(got) == set(ov) and all(str(got[k]) == str(v) for k, v in ov.items())
    txt = kernel_text(tag)
    chk["ov_log"] = ("overrides=" + json.dumps(dict(ov))) in txt
    chk["pred"] = rj.get("pred_md5_used") == ARTS["preds"][str(seed)] and rj.get("pred_md5_base") == PRED_BASE
    chk["n"] = bool(n) and n > 0 and md5 is not None
    chk["tk"] = "TICKER_HO4P1 ok=273 bad=0 miss=0 extra=0 other=0" in txt
    chk["fund"] = "FUND_HO4_OK" in txt and "FUND_HO4_SELFCHECK keys_equal=True" in txt
    chk["market"] = ("market_ds=" + CHAIN) in txt
    pens = [float(x) for x in re.findall(r"\[CRASH-PENALTY\] SUMMARY penalty=([0-9.eE+-]+)", txt)]
    if "SIM_CRASH_ENTRY_PENALTY" in ov:
        chk["pen"] = bool(pens) and all(abs(p - float(ov["SIM_CRASH_ENTRY_PENALTY"])) < 1e-12 for p in pens)
    else:
        chk["pen"] = all(p == 0.0 for p in pens)
    chk["unseal"] = ("HOLDOUT_UNSEAL DUNG" in txt) == bool(unseal)
    return all(chk.values()), chk, md5, n


def load_state():
    return json.load(open(STATE)) if os.path.exists(STATE) else {}


def save_state(st):
    tmp = STATE + ".tmp"
    json.dump(st, open(tmp, "w"), indent=1)
    os.replace(tmp, STATE)


def tsv_row(tag, status, md5, n, par):
    new = not os.path.exists(TSV)
    with open(TSV, "a") as f:
        if new:
            f.write("slug\tstatus\tmd5_printDone\tn\tparity\ttime\n")
        f.write("\t".join(str(x) for x in (tag, status, md5, n, par, time.strftime("%Y-%m-%d %H:%M:%S"))) + "\n")


def rows(tag):
    with open(OUT % tag + "storage/printDone.csv", newline="") as f:
        r = list(csv.reader(f))
    return r[0], r[1:]


def f32eq(a, b):
    import numpy as np
    try:
        return bool(np.float32(float(a)) == np.float32(float(b)))
    except ValueError:
        return False


def cmp_c1(tag, ref):
    h1, r1 = rows(tag)
    h0, r0 = rows(ref)
    out = dict(header_equal=h1 == h0, n=len(r1), n_ref=len(r0), col_diff={}, f32_print_only={})
    if h1 != h0 or len(r1) != len(r0):
        out["pass"] = False
        return out
    for i, nm in enumerate(h0):
        d = f = 0
        for a, b in zip(r1, r0):
            if a[i] != b[i]:
                if f32eq(a[i], b[i]):
                    f += 1
                else:
                    d += 1
        if d:
            out["col_diff"][nm or "#%d" % i] = d
        if f:
            out["f32_print_only"][nm or "#%d" % i] = f
    out["pass"] = not out["col_diff"]
    return out


def parity_verdict(st):
    res = {}
    for tag, (_, ref, want) in PARITY.items():
        r = dict(state=st[tag]["state"], md5=st[tag].get("md5"), n=st[tag].get("n"), checks=st[tag].get("chk"))
        if tag == "ho4p1-c1":
            r["vs_ref"] = cmp_c1(tag, ref) if st[tag]["state"] == "PASS" else None
            r["ref_md5"] = md5f(OUT % ref + "storage/printDone.csv")
            r["pass"] = bool(r["state"] == "PASS" and r["vs_ref"]["pass"])
        else:
            r["want"] = want
            r["pass"] = bool(r["state"] == "PASS" and r["md5"] == want)
        res[tag] = r
    res["pass_all"] = all(res[t]["pass"] for t in PARITY)
    json.dump(res, open(D + "/parity_ho4p1.json", "w"), indent=1)
    log.info("PARITY HO4P1: %s", json.dumps({t: res[t]["pass"] for t in PARITY}))
    return res["pass_all"]


def s5_status():
    """ADDENDUM-6 §6.6: chay lai quy chua 2026-03 (q1 vs q1r MANIFEST) + chuoi (chain-y26 vs chain-y26r) md5 trung.
    Doc cong tu pipe_state.json (ho4p1_pipe.py). True/False/None (chua co)."""
    try:
        g = json.load(open("/home/ubuntu/claude_master/1011/ho4p1/pipe_state.json"))["gates"]
    except Exception:  # noqa: BLE001
        return None
    v = [g.get("s5q1"), g.get("s5chain")]
    if any(x is False for x in v):
        return False
    return True if all(x is True for x in v) else None


def running(ks):
    out = []
    for k in ks._api().kernels_list(mine=True, page_size=50):
        try:
            s = ks._status(k.ref)
        except Exception:  # noqa: BLE001
            continue
        if s in ("RUNNING", "QUEUED"):
            out.append((k.ref, s))
    return out


def finish(ks, st, tag, ov, seed, unseal, kstatus):
    if tag.startswith("ho4p1-dev-"):                 # P3-DEV: chi tai output, so sanh rieng (ho4p1_simdev.py compare)
        try:
            ks.fetch(tag)
        except Exception as e:  # noqa: BLE001
            log.warning("fetch %s loi %s", tag, str(e)[:200])
        st[tag].update(state="PASS" if kstatus == "COMPLETE" else "FAIL", kstatus=kstatus)
        tsv_row(tag, kstatus, None, None, "P3-DEV")
        return
    try:
        ks.fetch(tag)
    except Exception as e:  # noqa: BLE001
        log.warning("fetch %s loi %s", tag, str(e)[:200])
    ok, chk, md5, n = check(tag, ov, seed, unseal)
    s = st[tag]
    s.update(md5=md5, n=n, chk=chk, kstatus=kstatus, done_at=time.strftime("%Y-%m-%d %H:%M:%S"))
    if kstatus == "COMPLETE" and ok:
        s["state"] = "PASS"
        tsv_row(tag, kstatus, md5, n, "PASS")
        log.info("DONE %s PASS md5=%s n=%s", tag, md5, n)
        return
    infra = (kstatus != "COMPLETE") or not chk.get("ok") or not chk.get("mapper") or not chk.get("n")
    if infra and s["pushes"] < 2:
        s["state"] = "retry"
        tsv_row(tag, kstatus, md5, n, "RETRY")
        log.warning("LOI HA TANG %s status=%s chk=%s -> retry (cfg y het)", tag, kstatus, chk)
        return
    s["state"] = "FAIL"
    tsv_row(tag, kstatus, md5, n, "FAIL")
    log.error("DONE %s FAIL status=%s chk=%s", tag, kstatus, chk)


def main():
    ks = GA.ks_mod()
    queue = build_queue()
    spec = {t: (ph, ov, s, e, u) for t, ph, ov, s, e, u in queue}
    st = load_state()
    st.setdefault("_phase", 0)
    for t, *_ in queue:
        st.setdefault(t, {"state": "todo", "pushes": 0})
    save_state(st)
    log.info("QUEUE %d kernel (code_sha %s, chain %s, tk %s): %s", len(queue), CODE_SHA, CHAIN, TKK, [t for t, *_ in queue])
    while True:
        mine_active = 0
        for t, *_ in queue:
            s = st[t]
            if s["state"] != "pushed":
                continue
            try:
                kst = ks._status(ks.kernel_ref(t))
            except Exception as e:  # noqa: BLE001
                log.info("status %s loi %s", t, str(e)[:100])
                mine_active += 1
                continue
            young = time.time() - s.get("pushed_epoch", 0) < 300
            if kst in ks.TERMINAL and not young:
                ph, ov, seed, end, u = spec[t]
                finish(ks, st, t, ov, seed, u, kst)
                save_state(st)
            else:
                mine_active += 1
        phase = st["_phase"]
        if phase == 0 and all(st[t]["state"] in ("PASS", "FAIL") for t in PARITY):
            s5 = s5_status()
            if s5 is None and all(st[t]["state"] == "PASS" for t in PARITY):
                log.info("C1/C2 xong, CHO S5 (q1r + chain-y26r md5) truoc khi mo pha 1")
                time.sleep(POLL_S)
                continue
            if parity_verdict(st) and s5 is True:
                st["_phase"] = 1
                save_state(st)
                log.info("PARITY PASS -> MO SEAL: pha 1 (32 kernel holdout)")
                continue
            st["_phase"] = -1
            save_state(st)
            log.error("PARITY FAIL -> DUNG, KHONG day kernel holdout (bao MASTER)")
            break
        todo = [t for t, ph, *_ in queue if ph == max(phase, 0) and st[t]["state"] in ("todo", "retry")]
        if phase == 1 and not todo and mine_active == 0:
            st["_phase"] = 2
            save_state(st)
            log.info("PHA 1 XONG -> pha 2 (2 sim DEV P3-DEV, chi bao)")
            continue
        if phase == 2 and not todo and mine_active == 0:
            break
        if todo and mine_active < MAX_PAR:
            try:
                run = running(ks)
            except Exception as e:  # noqa: BLE001
                log.warning("running() loi %s", str(e)[:100])
                run = [("?", "?")] * MAX_PAR
            log.info("tai khoan running/queued=%d %s", len(run), run)
            if len(run) < MAX_PAR:
                t = todo[0]
                ph, ov, seed, end, u = spec[t]
                assert (ph == 1) == u and (u is False or st["_phase"] == 1), "unseal chi o pha 1 sau parity PASS"
                try:
                    if ph == 2:
                        import ho4p1_simdev as SDV
                        SDV.submit(t)
                    else:
                        push(ks, t, ov, seed, end, u)
                    st[t]["pushes"] += 1
                    st[t]["state"] = "pushed"
                    st[t]["pushed_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
                    st[t]["pushed_epoch"] = time.time()
                except Exception as e:  # noqa: BLE001
                    log.error("push %s loi %s", t, str(e)[:300])
                    st[t]["pushes"] += 1
                    st[t]["state"] = "FAIL" if st[t]["pushes"] >= 2 else "retry"
                    if st[t]["state"] == "FAIL":
                        tsv_row(t, "PUSH_ERROR", None, None, "FAIL")
                save_state(st)
                time.sleep(90)
                continue
        time.sleep(POLL_S)
    log.info("QUEUE KET THUC phase=%s: %s", st["_phase"], {t: st[t]["state"] for t, *_ in queue})


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "dry":
        t = template()
        log.info("DRY template ok %d bytes, queue %s", len(t), [x[0] for x in build_queue()])
    else:
        main()
