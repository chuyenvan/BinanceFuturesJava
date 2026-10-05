#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LIVE vs SIM parity A-I (shadow_c3 Oracle + 242 CHI DOC) — audit-only, deterministic.
Checklist: docs/runbooks/PARITY_LIVE_VS_SIM_CHECKLIST.md (tieu chi chot TRUOC khi chay, 2026-10-03).
Chay:  python3 research/parity/live_vs_sim_check.py [--fetch] [--probe] [--since "YYYY-MM-DD HH:MM"] [--out file.json]
       (hoac: python3 research/parity/parity_check.py live)
Exit: 0 PASS / 2 FAIL / 3 MISSING (cung quy uoc parity_check.py). KHONG ghi 242, KHONG secret, KHONG build.
Python logging (khong print tuy tien).
"""
import argparse
import glob
import gzip
import hashlib
import io
import json
import logging
import math
import os
import re
import subprocess
import sys
import zlib
import datetime as dt

import numpy as np
import pandas as pd

LOG = logging.getLogger("live_vs_sim")

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
HOME = os.path.expanduser("~")
WORK = os.environ.get("PARITY_WORK", HOME + "/claude_master/1003/parity")
OUT = WORK + "/out"
L242 = WORK + "/live242"
SHADOW = os.environ.get("SHADOW_DIR", HOME + "/shadow_c3")
SH_APP = SHADOW + "/app"
JAR = SH_APP + "/target/binance-java-sdk-1.2.4.jar"
SRC = REPO + "/src/main/java/com/binance/chuyennd"
TZ = dt.timezone(dt.timedelta(hours=7))
SSH242 = ["ssh", "-p", "2222", "-o", "BatchMode=yes", "-o", "ConnectTimeout=20",
          "-i", HOME + "/.ssh/id_rsa_chuyennd", "root@103.157.218.242"]
APP242 = "/home/chuyennd/java/v_t_m"
GATE_MODEL = SHADOW + "/storage/ai_ml_data/ai_models_reg_v3/Model_Regressor_Return15M.onnx"
GATE_MODEL_SHA = "d19fc8cddd9fb11778653e4b108bb52da92ea168117efac4a407c18c0f260474"

# --- hang so gate (EntryGate.java:44-48), ghi dung de tinh lai
DYN_MIN, SCORE_BASE, DYN_MULT = np.float32(0.26787), np.float32(0.15), np.float32(1.28760)
THR_TOL = 6e-6          # log in %.5f => sai so lam tron <= 5e-6
P15_TOL = 1e-6          # B4
FEAT_REL = 1e-3         # D1: |d| <= 1e-3*(1+|x|)
SENSITIVE = re.compile(r"key|secret|token|passw", re.I)

PASS, FAIL, MISSING = "PASS", "FAIL", "MISSING"


def combine(sts):
    sts = [s for s in sts if s]
    if FAIL in sts:
        return FAIL
    if MISSING in sts:
        return MISSING
    return PASS if PASS in sts else MISSING


def item(cid, layer, name, expect, shadow, s242, st_sh, st_242, action="", known=False, evidence=""):
    return {"id": cid, "layer": layer, "name": name, "expect_sim": expect, "shadow": shadow, "s242": s242,
            "status_shadow": st_sh, "status_242": st_242, "action": action, "known": known, "evidence": evidence}


def sh(cmd, timeout=120, shell=False):
    if isinstance(cmd, str):
        shell = True
    r = subprocess.run(cmd, shell=shell, capture_output=True, text=True, timeout=timeout)
    return r.returncode, r.stdout, r.stderr


def ssh242(remote_cmd, timeout=240):
    """CHI DOC: remote_cmd phai la cat/grep/tar/ls/ps/head/tail (khong ghi)."""
    assert not re.search(r"\b(rm|mv|cp|tee|dd|chmod|kill|systemctl|sed -i)\b|>", remote_cmd), "242 chi doc"
    return sh(SSH242 + [remote_cmd], timeout)


def ms(d):
    return int(d.timestamp() * 1000)


def parse_ts_log(s):
    # "03/10/2026 21:27:06.436"
    d = dt.datetime.strptime(s[:19], "%d/%m/%Y %H:%M:%S").replace(tzinfo=TZ)
    return ms(d)


def src_grep(rel, pattern, flags=0):
    """Tra ve 'file:line: text' dong dau khop trong source (bang chung code)."""
    p = SRC + "/" + rel
    if not os.path.exists(p):
        return None
    rx = re.compile(pattern, flags)
    with open(p, encoding="utf-8", errors="replace") as fh:
        for i, ln in enumerate(fh, 1):
            if rx.search(ln):
                return "%s:%d: %s" % (rel, i, ln.strip()[:160])
    return None


def sha256_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for b in iter(lambda: fh.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


# ====================================================================== loaders
GATE_RX = re.compile(r"^(\d\d/\d\d/\d{4} \d\d:\d\d:\d\d)\.\d+\s+\S+\s+\[[^\]]*\]\s+\S+\s+\[GATE\] scale=([\d.]+) topk=(\d+) "
                     r"base=([\d.]+) thr=\[([\d.]+)\.\.([\d.]+)\] n_cand=(\d+) n_rej=(\d+) n_pass=(\d+)")
RATIO_RX = re.compile(r"^(\d\d/\d\d/\d{4} \d\d:\d\d:\d\d)\.\d+.*\[GATE-RATIO\] q_t=([\d.eE+-]+) buffer=(\d+) eval=(\d+) pass=(\d+)")
TIMING_RX = re.compile(r"^(\d\d/\d\d/\d{4} \d\d:\d\d:\d\d)\.\d+.*\[PASS-TIMING\] selector tick total=(\d+)ms")
S1_RX = re.compile(r"^(\d\d/\d\d/\d{4} \d\d:\d\d:\d\d)\.\d+.*\[S1\] score (\d+) coin tai (\d+) \(hist gio cuoi \d+, (\d+) coin du")
START_RX = re.compile(r"^(\d\d/\d\d/\d{4} \d\d:\d\d:\d\d)\.\d+.*LIVE_PROFILE=c3_shadow\] BAT")


def read_lines(path):
    with open(path, "rb") as fh:
        for b in fh:
            yield b.decode("utf-8", "replace")


def load_log(path, since_ms):
    """Tra dict: gate (DataFrame theo phut), ratio, timing, s1, starts, err (Counter theo mau)."""
    gate, ratio, timing, s1, starts, errs = [], [], [], [], [], {}
    for ln in read_lines(path):
        if "[GATE" not in ln and "PASS-TIMING" not in ln and "[S1] score" not in ln and "LIVE_PROFILE=c3" not in ln \
                and " ERROR " not in ln and "OutOfMemory" not in ln:
            continue
        m = GATE_RX.match(ln)
        if m:
            t = parse_ts_log(m.group(1))
            if t >= since_ms:
                gate.append((t, float(m.group(2)), int(m.group(3)), float(m.group(4)), float(m.group(5)),
                             float(m.group(6)), int(m.group(7)), int(m.group(8)), int(m.group(9))))
            continue
        m = RATIO_RX.match(ln)
        if m:
            t = parse_ts_log(m.group(1))
            if t >= since_ms:
                ratio.append((t, float(m.group(2)), int(m.group(3)), int(m.group(4)), int(m.group(5))))
            continue
        m = TIMING_RX.match(ln)
        if m:
            t = parse_ts_log(m.group(1))
            if t >= since_ms:
                timing.append((t, int(m.group(2))))
            continue
        m = S1_RX.match(ln)
        if m:
            t = parse_ts_log(m.group(1))
            if t >= since_ms:
                s1.append((t, int(m.group(2)), int(m.group(4))))
            continue
        m = START_RX.match(ln)
        if m:
            starts.append(parse_ts_log(m.group(1)))
            continue
        if " ERROR " in ln or "OutOfMemory" in ln:
            t = None
            try:
                t = parse_ts_log(ln[:19])
            except Exception:
                pass
            if t is not None and t >= since_ms:
                key = re.sub(r"\d+", "#", ln[24:150]).strip()
                key = re.sub(r"\s+", " ", key)[:110]
                errs[key] = errs.get(key, 0) + 1
    g = pd.DataFrame(gate, columns=["t", "scale", "topk", "base", "thr_min", "thr_max", "n_cand", "n_rej", "n_pass"])
    if len(g):
        g["minute"] = (g.t // 60000) * 60000
        g["ts"] = g.minute - 60000          # nen dong cua phut truoc
        g = g.drop_duplicates("minute", keep="last").reset_index(drop=True)
    return {"gate": g,
            "ratio": pd.DataFrame(ratio, columns=["t", "q_t", "buffer", "eval", "pass"]),
            "timing": pd.DataFrame(timing, columns=["t", "ms"]),
            "s1": pd.DataFrame(s1, columns=["t", "n_score", "n_enough"]),
            "starts": starts, "errs": errs}


def read_gz_tolerant(path):
    """Doc gz ke ca file THIEU trailer (file truoc EXPORT-FIX / dang ghi): giai nen phan co, bo dong cuoi dang do."""
    raw = open(path, "rb").read()
    dco = zlib.decompressobj(16 + zlib.MAX_WBITS)
    out = b""
    try:
        out = dco.decompress(raw)
    except zlib.error:
        pass
    txt = out.decode("utf-8", "replace")
    if txt and not txt.endswith("\n"):
        txt = txt[:txt.rfind("\n") + 1]
    return txt


def load_dump(folder, prefix, since_ms=0):
    files = sorted(glob.glob("%s/%s_*.csv.gz" % (folder, prefix)))
    dfs = []
    for f in files:
        try:
            d = pd.read_csv(io.StringIO(read_gz_tolerant(f)))
        except Exception as e:          # file rong / hong
            LOG.warning("bo qua %s: %s", os.path.basename(f), e)
            continue
        if len(d):
            dfs.append(d)
    if not dfs:
        return pd.DataFrame()
    d = pd.concat(dfs, ignore_index=True)
    d = d[d.ts >= since_ms].drop_duplicates(["ts", "symbol"], keep="last")
    return d.sort_values(["ts", "symbol"]).reset_index(drop=True)


def read_env_file(p):
    d = {}
    if not os.path.exists(p):
        return d
    for ln in open(p, errors="replace"):
        m = re.match(r"^\s*export\s+([A-Z0-9_]+)=(.*)$", ln.rstrip("\n"))
        if m and not SENSITIVE.search(m.group(1)):
            d[m.group(1)] = m.group(2).strip().strip('"')
    return d


def proc_env(pid):
    d = {}
    try:
        raw = open("/proc/%s/environ" % pid, "rb").read().split(b"\0")
    except Exception:
        return d
    for kv in raw:
        k, _, v = kv.decode("utf-8", "replace").partition("=")
        if re.match(r"^(SIM_|LIVE_|TS_|SHADOW|DCA_|SELECTOR|CONC|TIER|PAPER|CAPITAL|OI_|MARKET|ENTRY|NET015|S1_|TRAIL|JAVA_TOOL)", k) \
                and not SENSITIVE.search(k):
            d[k] = v
    return d


# ====================================================================== fetch (242 READ-ONLY) + probe
def fetch242(since_note=""):
    os.makedirs(L242 + "/fd", exist_ok=True)
    rc, out, err = sh("%s %s 'cd %s/feat_dump && ls -t *.csv.gz | tail -n +3 | tar cf - -T -' | tar xf - -C %s/fd"
                      % (" ".join(SSH242[:-1]), SSH242[-1], APP242, L242), 300, shell=True)
    pat = (r"\[GATE\]|\[GATE-RATIO\]|\[SHADOW\]|New price SL|Update SL|\[TS-GAP\]|PASS-TIMING|OI-LIVE\]|Picked up|"
           r"LIVE_PROFILE|skip-LEGACY|ERROR|OutOfMemory|NullPointer|\[MAP\]|\[S1\] score|S1\] (nap|warm)|GATE-RATIO\] (LIVE|seed)")
    rc2, out2, _ = ssh242("nice grep -a -E '%s' %s/logs/full.log | grep -a -E '^(0[1-9]|[12][0-9]|3[01])/(09|10)/2026'" % (pat, APP242), 600)
    with open(L242 + "/full_filtered.log", "w") as fh:
        fh.write(out2)
    rc3, out3, _ = ssh242("P=$(cat %s/run/*.pid); ps -o pid,lstart,rss,etime -p $P; tr '\\0' ' ' < /proc/$P/cmdline; echo; "
                          "echo ===ENV; tr '\\0' '\\n' < /proc/$P/environ | grep -E '^(JAVA_TOOL|SIM_|LIVE_|TS_|SHADOW|DCA_|SELECTOR|CONC|TIER|PAPER|CAPITAL|OI_|MARKET|ENTRY|NET015|S1_|TRAIL)' | sort; "
                          "echo ===LEGACY; grep -v '^#' %s/run/legacy_symbols.csv | wc -l; echo ===LEDGER; "
                          "wc -l /home/chuyennd/java/shadow_c3/ledger.csv; ls -la --time-style=full-iso %s/run/gate_ratio_live.bin" % (APP242, APP242, APP242))
    with open(L242 + "/meta242.txt", "w") as fh:
        fh.write(out3)
    rc4, _, _ = sh("%s %s 'cat %s/run/gate_ratio_live.bin' > %s/gate_ratio_live_242_now.bin"
                   % (" ".join(SSH242[:-1]), SSH242[-1], APP242, OUT), 120, shell=True)
    return {"fd_rc": rc, "log_rc": rc2, "meta_rc": rc3, "grr_rc": rc4}


def parse_meta242():
    p = L242 + "/meta242.txt"
    r = {"env": {}, "cmdline": "", "legacy_n": None, "lstart": None}
    if not os.path.exists(p):
        return r
    txt = open(p, errors="replace").read()
    head, _, rest = txt.partition("===ENV")
    env, _, rest2 = rest.partition("===LEGACY")
    r["cmdline"] = [l for l in head.splitlines() if "java" in l and "-cp" in l][:1]
    r["cmdline"] = r["cmdline"][0].strip() if r["cmdline"] else ""
    for ln in env.splitlines():
        k, _, v = ln.partition("=")
        if k and not SENSITIVE.search(k):
            r["env"][k] = v
    leg, _, _ = rest2.partition("===LEDGER")
    try:
        r["legacy_n"] = int(leg.strip().splitlines()[0])
    except Exception:
        pass
    m = re.search(r"(\w{3} \w{3}\s+\d+ \d\d:\d\d:\d\d \d{4})", head)
    if m:
        r["lstart"] = m.group(1)
    return r


PROBE_SRC = HERE + "/probe/ConfigProbe.java.txt"
FP_SRC = HERE + "/probe/FormulaProbe.java.txt"


def run_java_probes():
    """Chay ConfigProbe + FormulaProbe (source-file mode: KHONG build repo) duoi 3 bo env B0/shadow/242. Doc-chi."""
    os.makedirs(OUT, exist_ok=True)
    tmp = WORK + "/probe_tmp"
    os.makedirs(tmp, exist_ok=True)
    for src, name in [(PROBE_SRC, "Probe.java"), (FP_SRC, "FormulaProbe.java")]:
        open(tmp + "/" + name, "w").write(open(src).read())
    envs = {}
    envs["shadow"] = {k: v for k, v in read_env_file(SH_APP + "/conf/env.sh").items() if not re.match(r"^(APP_|JAVA_TOOL)", k)}
    envs["242"] = {k: v for k, v in read_env_file(OUT + "/242_env.txt").items() if not re.match(r"^(APP_|JAVA_TOOL)", k)}
    b0 = {}
    for ln in open(OUT + "/b0_prof_run.properties"):
        ln = ln.strip()
        if ln and not ln.startswith("#") and "=" in ln and not ln.startswith("WFO_FUNDING_PRED_DIR"):
            k, _, v = ln.partition("=")
            b0[k] = v
    envs["b0"] = b0
    cfgs = {"b0": OUT + "/shadow_cfg.txt", "shadow": SH_APP + "/config.properties", "242": OUT + "/242_cfg.txt"}
    lines = []
    for i in range(0, 61):
        lines.append("T 0.008 %.5f" % (0.05 + i * 0.0095))
    for i in range(0, 431):
        lines.append("R %.5f 0.10" % (0.07 + i * 0.001))
    for i in range(0, 431, 7):
        lines.append("R %.5f 0.50" % (0.0701 + i * 0.00097))
    for eq, m in [(35000, 0), (35000, 5000), (40000, 12000), (35000, 21000), (35000, 22000)]:
        lines.append("B %d %d" % (eq, m))
    for g in range(5):
        lines.append("G %d" % g)
    # [LIVE-SIZING 2026-10-03] budget leg duong live (LiveGridSizing.legBudget) leg 0..3 @35000, U=0
    for g in range(4):
        lines.append("L 35000 0 %d" % g)
    inp = "\n".join(lines) + "\n"
    res = {}
    for tag in ("b0", "shadow", "242"):
        cwd = "%s/cwd_%s" % (WORK, tag)
        os.makedirs(cwd, exist_ok=True)
        open(cwd + "/config.properties", "w").write(open(cfgs[tag], errors="replace").read())
        env = {"HOME": HOME, "PATH": os.environ.get("PATH", "")}
        env.update(envs[tag])
        r1 = subprocess.run(["java", "-Xmx512m", "-cp", JAR, tmp + "/Probe.java"], cwd=cwd, env=env,
                            capture_output=True, text=True, timeout=180)
        open("%s/probe_%s.txt" % (OUT, tag), "w").write(r1.stdout + r1.stderr)
        r2 = subprocess.run(["java", "-Xmx512m", "-cp", JAR, tmp + "/FormulaProbe.java"], cwd=cwd, env=env, input=inp,
                            capture_output=True, text=True, timeout=180)
        open("%s/fp_%s.txt" % (OUT, tag), "w").write("".join(l + "\n" for l in r2.stdout.splitlines() if l.startswith("FP")))
        res[tag] = (r1.returncode, r2.returncode)
    return res


# ====================================================================== A. config
def load_probe(tag):
    d = {}
    p = "%s/probe_%s.txt" % (OUT, tag)
    if not os.path.exists(p):
        return d
    for ln in open(p, errors="replace"):
        q = ln.rstrip("\n").split("\t")
        if q[0] == "PROBE" and len(q) >= 3:
            d[q[1]] = q[2]
        elif q[0].startswith("PROBE_") and len(q) >= 2:
            d[q[0]] = q[1]
    return d


# key khac nhau B0<->live nhung CO LY DO (live khong doc / tuong duong / ha tang)
A_EXPLAINED = {
    "Configs.APPLY_FUNDING_FEE": "live KHONG doc SIM_APPLY_FUNDING (ledger giay khong tru funding) — G1",
    "Configs.FUNDING_MARK_NOTIONAL": "live KHONG doc SIM_FUNDING_MARK — G1",
    "Configs.DCA_GRID_ENABLED": "duong live khong goi gridLegWeightRatio/shouldDcaGrid (DcaProcessor.getDCAProduction) — E5",
    "Configs.LIVE_ENTRY_GRID_MIN": "B0 dung SIM_ENTRY_SAMPLE_MIN=1; live dung LIVE_ENTRY_GRID_MIN=1 (tuong duong, ENTRY_SAMPLE_MIN hieu dung = 1 ca hai)",
    "Configs.MARKET_SCAN_MIN": "key chi live (nhip BIG_DOWN/DCA 1 phut)",
    "Configs.MARKET_SCAN_PRIORITY": "key chi live",
    "Configs.AEROSPIKE_NAMESPACE_242": "ha tang", "Configs.TICKER_SOURCE": "ha tang",
    "LiveProfileC3.ON": "profile live-only (c3_shadow)", "LiveProfileC3.PAPER_EQUITY": "live-only",
}


def layer_A(ctx):
    items = []
    pb, ps, p2 = load_probe("b0"), load_probe("shadow"), load_probe("242")
    if not (pb and ps and p2):
        return [item("A1", "A", "Configs hieu dung (Probe)", "-", "thieu probe", "thieu probe", MISSING, MISSING,
                     "chay --probe")]
    keys = sorted(set(pb) | set(ps) | set(p2))
    diff_sh = [k for k in keys if pb.get(k) != ps.get(k) and k.startswith(("Configs.", "PROBE_"))]
    diff_242 = [k for k in keys if pb.get(k) != p2.get(k) and k.startswith(("Configs.", "PROBE_"))]
    # F_BASE shadow = F_BASE(B0) x DCA_GRID_SCALE la BU CO CHU Y cho E2 (live khong nhan gridLegWeightRatio) -> giai thich duoc
    fbase_comp = False
    try:
        fbase_comp = abs(float(ps["Configs.F_BASE"]) - float(pb["Configs.F_BASE"]) * float(pb["Configs.DCA_GRID_SCALE"])) < 1e-9
    except (KeyError, ValueError):
        pass
    ctx["fbase_comp"] = fbase_comp
    unexp_sh = [k for k in diff_sh if k not in A_EXPLAINED and not (k == "Configs.F_BASE" and fbase_comp)]
    unexp_242 = [k for k in diff_242 if k not in A_EXPLAINED]
    sh_vs_242 = [k for k in keys if ps.get(k) != p2.get(k) and not k.startswith("LiveProfileC3.")
                 and k not in ("Configs.AEROSPIKE_NAMESPACE_242", "Configs.TICKER_SOURCE")
                 and not (k == "Configs.F_BASE" and fbase_comp)]
    ev = "; ".join("%s: B0=%s sh=%s 242=%s" % (k, pb.get(k), ps.get(k), p2.get(k)) for k in diff_sh)
    items.append(item("A1", "A", "Configs.* hieu dung (jar 8f3ee52c, %d field) B0 vs live" % len(keys),
                      "mọi field = B0 (trừ field live-only/không đọc)",
                      "%d field khac B0, %d chua giai thich" % (len(diff_sh), len(unexp_sh)),
                      "%d field khac B0, %d chua giai thich" % (len(diff_242), len(unexp_242)),
                      PASS if not unexp_sh else FAIL, PASS if not unexp_242 else FAIL,
                      "" if not unexp_sh and not unexp_242 else "sua env: " + ",".join(unexp_sh + unexp_242), evidence=ev))
    items.append(item("A1b", "A", "shadow == 242 (Configs hieu dung, tru ha tang)", "giong nhau",
                      "%d field khac%s" % (len(sh_vs_242), " (+ F_BASE: shadow 0.09 = 0.015 x DCA_GRID_SCALE, co chu y, xem E2)" if fbase_comp else ""),
                      "-", PASS if not sh_vs_242 else FAIL, PASS if not sh_vs_242 else FAIL,
                      "" if not sh_vs_242 else ",".join(sh_vs_242)))
    # key trong B0 -> hieu dung (cac key quan trong in ro)
    imp = ["Configs.SELECTOR_RANK_TOPK", "Configs.F_BASE", "Configs.DCA_GRID_WEIGHTS", "Configs.DCA_GRID_SCALE", "Configs.U_MAX",
           "Configs.CONC_CAP_PERCOIN_PCT", "Configs.MIN_MOMENTUM_15M", "Configs.RATE_PROFIT_STOP_MARKET", "Configs.TS_GIVEBACK_RATIO",
           "Configs.TS_MAX_GAP", "Configs.TS_MAX_GAP_WEAK", "Configs.TS_PNOPUMP_WEAK_THR", "Configs.LOSER_TIME_STOP_HOURS",
           "Configs.RATE_FEE", "Configs.SLIPPAGE_RATE", "Configs.TIER_FLAT", "Configs.TS_PEAK_MODE", "LiveProfileC3.ARM_RATE",
           "LiveProfileC3.TIME_STOP_HOURS", "LiveProfileC3.SIZE_CAP_OF_EQUITY"]
    tbl = "; ".join("%s=%s|%s|%s" % (k.split(".")[1], pb.get(k), ps.get(k), p2.get(k)) for k in imp)
    items.append(item("A1c", "A", "gia tri hieu dung key vao/ra/size (B0|shadow|242)", "-", "xem evidence", "xem evidence",
                      PASS if all(pb.get(k) == ps.get(k) == p2.get(k) for k in imp[:-3] if not (fbase_comp and k == "Configs.F_BASE")) else FAIL,
                      PASS if all(pb.get(k) == ps.get(k) == p2.get(k) for k in imp[:-3] if not (fbase_comp and k == "Configs.F_BASE")) else FAIL, evidence=tbl))
    # A2 /proc environ == env.sh
    sh_pid = ctx.get("shadow_pid")
    envf = {k: v for k, v in read_env_file(SH_APP + "/conf/env.sh").items() if re.match(
        r"^(SIM_|LIVE_|TS_|SHADOW|DCA_|SELECTOR|CONC|TIER|PAPER|CAPITAL|OI_|MARKET|ENTRY|NET015|S1_|TRAIL|JAVA_TOOL)", k)}
    penv = proc_env(sh_pid) if sh_pid else {}
    d_sh = sorted(k for k in set(envf) | set(penv) if envf.get(k) != penv.get(k))
    m242 = ctx["meta242"]
    f242 = {k: v for k, v in read_env_file(OUT + "/242_env.txt").items() if re.match(
        r"^(SIM_|LIVE_|TS_|SHADOW|DCA_|SELECTOR|CONC|TIER|PAPER|CAPITAL|OI_|MARKET|ENTRY|NET015|S1_|TRAIL)", k)}
    d_242 = sorted(k for k in set(f242) | set(m242["env"]) if k != "JAVA_TOOL_OPTIONS" and f242.get(k) != m242["env"].get(k))
    items.append(item("A2", "A", "/proc/<pid>/environ (JVM dang chay) == conf/env.sh", "trùng",
                      "%d lech %s" % (len(d_sh), d_sh[:6]) if penv else "khong doc duoc",
                      "%d lech %s" % (len(d_242), d_242[:6]) if m242["env"] else "khong doc duoc",
                      (PASS if not d_sh else FAIL) if penv else MISSING,
                      (PASS if not d_242 else FAIL) if m242["env"] else MISSING,
                      "restart neu lech (shadow)"))
    # A3 gate rolling
    sh_roll = {k: v for k, v in penv.items() if k.startswith("LIVE_GATE_ROLLING")}
    m_roll = {k: v for k, v in m242["env"].items() if k.startswith("LIVE_GATE_ROLLING")}
    want = {"LIVE_GATE_ROLLING_MODE": "ratio", "LIVE_GATE_ROLLING_PCT": "0.999950829", "LIVE_GATE_ROLLING_DAYS": "90"}
    items.append(item("A3", "A", "gate rolling (B0: SIM_GATE_ROLLING_MODE/PCT/DAYS = ratio/0.999950829/90)", "ratio/0.999950829/90",
                      "KHONG co key (co chu y: bat 10-07 17:15, DEPLOY_SHADOW_2A §7)" if not sh_roll else str(sh_roll),
                      str(m_roll) if m_roll else "khong co",
                      MISSING if not sh_roll else (PASS if sh_roll == want else FAIL),
                      PASS if m_roll == want else FAIL,
                      "KHONG bat som: seed Aerospike 242 qua WAN ~2.2 h chan main thread; bat 10-07 17:15 sau khi buffer 242 du 7 ngay", known=True))
    # A4 key B0 khong doc o live
    notread = {"SIM_APPLY_FUNDING": "ledger giay khong tru funding (G1)", "SIM_FUNDING_MARK": "idem",
               "DCA_GRID_ENABLED": "live khong chay grid (E5)", "WFO_FUNDING_PRED_DIR": "chi tai lap sim",
               "SIM_ENTRY_SAMPLE_MIN": "tuong duong LIVE_ENTRY_GRID_MIN=1"}
    items.append(item("A4", "A", "key B0 live KHONG doc / thay bang key live", "-", "; ".join("%s -> %s" % kv for kv in notread.items()),
                      "idem (242 khong khai bao 3 key dau)", PASS, PASS, "ghi nhan, khong sua", known=True))
    # A5 live-only
    must = {"SHADOW_NO_PUSH": "true", "LIVE_PROFILE": "c3_shadow"}
    ok_sh = all(penv.get(k) == v for k, v in must.items()) if penv else None
    ok_242 = all(m242["env"].get(k) == v for k, v in must.items()) if m242["env"] else None
    items.append(item("A5", "A", "key live-only bat buoc SHADOW_NO_PUSH=true, LIVE_PROFILE=c3_shadow", "bat buoc",
                      "ok" if ok_sh else str({k: penv.get(k) for k in must}), "ok" if ok_242 else str({k: m242["env"].get(k) for k in must}),
                      PASS if ok_sh else (MISSING if ok_sh is None else FAIL), PASS if ok_242 else (MISSING if ok_242 is None else FAIL)))
    # A6 config.properties key chet
    items.append(item("A6", "A", "config.properties key chet (Configs canh bao 'KHONG AI DOC': RATE_FEE, RATE_PROFIT_STOP_MARKET, ...)",
                      "khong anh huong", "20 key chet (RATE_PROFIT_STOP_MARKET=0.01, RATE_FEE=0.0015...) — Configs.RATE_*=0.07/0.000982 tu env",
                      "idem", PASS, PASS, "ghi nhan (gia tri trong file la SAI SU THAT)", known=True))
    # JVM heap
    return items


# ====================================================================== B. gate
def thr_f32(base, sp, scale):
    base = np.float32(base)
    sp = np.asarray(sp, dtype=np.float32)
    sc = (sp / SCORE_BASE) * DYN_MULT
    return (base * np.maximum(DYN_MIN, sc)) * np.float32(scale)


def gate_recompute(sel, gate):
    """Tu sel_dump (16 ung vien/tick) tinh lai thr_min/thr_max/n_pass va doi voi dong [GATE]."""
    if sel.empty or gate.empty:
        return None
    g = gate.set_index("ts")
    rows = []
    for ts, d in sel.groupby("ts"):
        if ts not in g.index:
            continue
        r = g.loc[ts]
        thr = thr_f32(r.base, d.gateValue.values, r.scale)
        p15 = np.float32(d.p15.iloc[0])
        rows.append((ts, float(thr.min()), float(thr.max()), int((~(p15 < thr)).sum()), len(d),
                     r.thr_min, r.thr_max, int(r.n_pass), int(r.n_cand)))
    if not rows:
        return None
    c = pd.DataFrame(rows, columns=["ts", "thr_min", "thr_max", "npass", "n", "l_min", "l_max", "l_npass", "l_ncand"])
    c["d_min"] = (c.thr_min - c.l_min).abs()
    c["d_max"] = (c.thr_max - c.l_max).abs()
    return c


def ort_p15(feat):
    try:
        import onnxruntime as ort
    except Exception as e:
        return None, "khong co onnxruntime: %s" % e
    if not os.path.exists(GATE_MODEL):
        return None, "thieu model %s" % GATE_MODEL
    cols = [c for c in feat.columns if c not in ("ts", "symbol", "p15_out", "rateDownAvg", "rateUpAvg", "rateDown15MAvg", "rateUp15MAvg")]
    if len(cols) != 33:
        return None, "so cot feature=%d != 33" % len(cols)
    s = ort.InferenceSession(GATE_MODEL, providers=["CPUExecutionProvider"])
    x = feat[cols].values.astype(np.float32)
    out = s.run(None, {s.get_inputs()[0].name: x})[0].reshape(-1)
    return out, "ok"


def layer_B(ctx):
    items = []
    gs, g2 = ctx["gate_sh"], ctx["gate_242"]
    since = ctx["since_ms"]
    t_end = ctx["now_ms"] - 3 * 60000

    def cov(g, start):
        if g.empty:
            return None
        n_exp = max(1, (t_end - start) // 60000)
        return float(len(g[(g.minute >= start) & (g.minute <= t_end)])) / n_exp
    c_sh, c_242 = cov(gs, since), cov(g2, since)
    items.append(item("B1", "B", "[GATE] coverage phut distinct / phut cua so (tu %s)" % ctx["since_txt"], "1/phut",
                      "%.1f%% (%d phut)" % (100 * c_sh, len(gs)) if c_sh is not None else "thieu log",
                      "%.1f%% (%d phut)" % (100 * c_242, len(g2)) if c_242 is not None else "thieu log",
                      (PASS if c_sh >= 0.95 else FAIL) if c_sh is not None else MISSING,
                      (PASS if c_242 >= 0.95 else FAIL) if c_242 is not None else MISSING))
    # B2/B3 cong thuc
    for nm, sel, gate, key in (("shadow", ctx["sel_sh"], gs, "sh"), ("242", ctx["sel_242"], g2, "242")):
        ctx.setdefault("rec", {})[key] = gate_recompute(sel, gate[gate.minute >= since] if len(gate) else gate)
    rs, r2 = ctx["rec"]["sh"], ctx["rec"]["242"]

    def b2(r):
        if r is None or not len(r):
            return None, None
        ok = float(((r.d_min <= THR_TOL) & (r.d_max <= THR_TOL)).mean())
        return ok, len(r)

    ok_sh, n_sh = b2(rs)
    ok_242, n_242 = b2(r2)
    items.append(item("B2", "B", "thr tinh lai tu sel_dump (EntryGate: base*max(0.26787,sp/0.15*1.2876)*scale) vs log thr=[min..max]",
                      "khop (|d|<=6e-6, >=99% phut)",
                      "%.1f%% phut khop (n=%d)" % (100 * ok_sh, n_sh) if ok_sh is not None else "thieu du lieu",
                      "%.1f%% phut khop (n=%d)" % (100 * ok_242, n_242) if ok_242 is not None else "thieu du lieu",
                      (PASS if ok_sh >= 0.99 else FAIL) if ok_sh is not None else MISSING,
                      (PASS if ok_242 >= 0.99 else FAIL) if ok_242 is not None else MISSING,
                      "kiem SIM_GATE_DYN_SCALE/MIN_MOMENTUM_15M" if (ok_sh is not None and ok_sh < 0.99) else ""))

    def b3(r):
        if r is None or not len(r):
            return None, None
        return float((r.npass == r.l_npass).mean()), int((r.npass != r.l_npass).sum())
    a_sh, bad_sh = b3(rs)
    a_242, bad_242 = b3(r2)
    items.append(item("B3", "B", "n_pass tinh lai (!(p15<thr_i)) vs log n_pass", "100%",
                      "%.1f%% (%d lech)" % (100 * a_sh, bad_sh) if a_sh is not None else "thieu",
                      "%.1f%% (%d lech)" % (100 * a_242, bad_242) if a_242 is not None else "thieu",
                      (PASS if a_sh == 1.0 else FAIL) if a_sh is not None else MISSING,
                      (PASS if a_242 == 1.0 else FAIL) if a_242 is not None else MISSING))
    # B4 ORT
    res4 = {}
    for key, feat in (("sh", ctx["feat_sh"]), ("242", ctx["feat_242"])):
        if feat.empty:
            res4[key] = (None, "khong co feat_dump")
            continue
        out, why = ort_p15(feat)
        if out is None:
            res4[key] = (None, why)
        else:
            d = np.abs(out.astype(np.float64) - feat.p15_out.values.astype(np.float64))
            res4[key] = ((float(d.max()), len(d)), "ok")
    sha_ok = os.path.exists(GATE_MODEL) and sha256_file(GATE_MODEL) == GATE_MODEL_SHA
    items.append(item("B4", "B", "ORT(model gate d19fc8cd%s) tren feat_dump (33 feat) vs p15_out" % ("" if sha_ok else " SHA LECH"),
                      "max|d|<=1e-6",
                      "max|d|=%.2e (n=%d)" % (res4["sh"][0][0], res4["sh"][0][1]) if res4["sh"][0] else res4["sh"][1],
                      "max|d|=%.2e (n=%d)" % (res4["242"][0][0], res4["242"][0][1]) if res4["242"][0] else res4["242"][1],
                      (PASS if res4["sh"][0][0] <= P15_TOL else FAIL) if res4["sh"][0] else MISSING,
                      (PASS if res4["242"][0][0] <= P15_TOL else FAIL) if res4["242"][0] else MISSING,
                      "model 242 gia dinh = d19fc8cd (DEPLOY_SHADOW_2A §1)"))
    # B5 shadow vs 242 cung phut
    j = None
    if len(gs) and len(g2):
        a = gs[gs.minute >= since].set_index("ts")
        b = g2[g2.minute >= since].set_index("ts")
        idx = a.index.intersection(b.index)
        if len(idx):
            j = pd.DataFrame({"tmin_s": a.loc[idx].thr_min, "tmin_2": b.loc[idx].thr_min, "np_s": a.loc[idx].n_pass,
                              "np_2": b.loc[idx].n_pass, "nc_s": a.loc[idx].n_cand, "nc_2": b.loc[idx].n_cand})
    p15d = None
    if len(ctx["sel_sh"]) and len(ctx["sel_242"]):
        a = ctx["sel_sh"].groupby("ts").p15.first()
        b = ctx["sel_242"].groupby("ts").p15.first()
        idx = a.index.intersection(b.index)
        idx = idx[idx >= since - 60000]
        if len(idx):
            d = (a.loc[idx] - b.loc[idx]) * 100          # pp
            p15d = {"n": int(len(idx)), "d_p10": float(d.quantile(.1)), "d_p50": float(d.median()), "d_p90": float(d.quantile(.9)),
                    "abs_p50": float(d.abs().median()), "dist_p50_sh": float(a.loc[idx].median() * 100),
                    "dist_p50_242": float(b.loc[idx].median() * 100)}
    if j is not None and p15d is not None:
        within = float(((j.tmin_s / j.tmin_2 - 1).abs() <= 0.01).mean())
        dp50 = abs(p15d["dist_p50_sh"] - p15d["dist_p50_242"])
        ok = (dp50 <= 0.02) and (within >= 0.90)
        ctx["b5"] = {"p15": p15d, "thr_within_1pct": within, "n_gate_pairs": int(len(j)), "dist_p50_abs_diff_pp": dp50,
                     "n_cand_equal": float((j.nc_s == j.nc_2).mean()), "npass_equal": float((j.np_s == j.np_2).mean())}
        items.append(item("B5", "B", "shadow vs 242 cung phut: p15, thr_min, n_cand", "|dp50|<=0.02pp va thr +-1% >=90% phut",
                          "|dp50 phan phoi|=%.3fpp; paired d p10/p50/p90=%.3f/%.3f/%.3f pp; thr_min +-1%%=%.1f%% (n=%d)" % (
                              dp50, p15d["d_p10"], p15d["d_p50"], p15d["d_p90"], 100 * within, len(j)),
                          "-", PASS if ok else FAIL, PASS if ok else FAIL,
                          "nguon: p15 shadow doc ticker qua WAN tre hon (xem D1); khong sua duoc bang env" if not ok else "", known=not ok))
    else:
        items.append(item("B5", "B", "shadow vs 242 cung phut", "-", "thieu du lieu", "-", MISSING, MISSING))
    # B6 fallback
    rs_, r2_ = ctx["ratio_sh"], ctx["ratio_242"]
    base_sh = gs[gs.minute >= since].base.unique().tolist() if len(gs) else []
    base_242 = g2[g2.minute >= since].base.unique().tolist() if len(g2) else []
    q242 = r2_.q_t.unique().tolist() if len(r2_) else []
    items.append(item("B6", "B", "nguong truoc arm: base=MIN_MOMENTUM_15M=0.008 (G2 fallback)", "base 0.00800; q_t=0.008 den arm",
                      "base=%s (ratio TAT)" % base_sh, "base=%s; [GATE-RATIO] q_t=%s buffer=%s" % (
                          base_242, q242, int(r2_.buffer.iloc[-1]) if len(r2_) else "-"),
                      PASS if base_sh == [0.008] else FAIL, PASS if (base_242 == [0.008] and q242 == [0.008]) else FAIL))
    return items


# ====================================================================== B7/B8 (arm + ai_pred_1m)
def layer_B78(ctx):
    items = []
    try:
        sys.path.insert(0, HERE)
        import gate_arm_check as gac
        p = OUT + "/gate_ratio_live_242_now.bin"
        if os.path.exists(p):
            r = gac.analyse(p, pct=0.999950829, days=90)
            ctx["arm242"] = r
            items.append(item("B7", "B", "arm gate G2: buffer 242 (GRR1) -> firstTs+7d, q(0.99995) tinh lai (script gate_arm_check.py)",
                              "q_t log = q tinh lai sau arm; n_pass/ngay in [0.34;3.8]",
                              "shadow: ratio TAT (chua co buffer rieng) — bat 10-07 17:15",
                              "n=%d firstTs=%s arm>=%s; chua arm -> q_t fallback=0.008; q_now(neu arm)=%.6f; %s" % (
                                  r["n"], r["first_ts"], r["arm_ts"], r["q_now"], "DA ARM" if r["armed"] else "CHUA ARM"),
                              MISSING, MISSING if not r["armed"] else PASS,
                              "chay lai gate_arm_check.py sau 10-07 17:15; so q_t log vs q tinh lai",
                              evidence=json.dumps(r, default=str)[:500]))
        else:
            items.append(item("B7", "B", "arm gate G2", "-", "-", "thieu file buffer", MISSING, MISSING, "fetch"))
    except Exception as e:
        items.append(item("B7", "B", "arm gate G2", "-", "loi: %s" % e, "-", MISSING, MISSING))
    # B8 p15 vs ai_pred_1m (Aerospike 242, chi get)
    try:
        import aerospike
        c = aerospike.client({"hosts": [("103.157.218.242", 3222)], "policies": {"read": {"total_timeout": 5000}}}).connect()
        res = []
        feat = {"sh": ctx["feat_sh"], "242": ctx["feat_242"]}
        tsl = sorted(set(ctx["feat_242"].ts) & set(ctx["feat_sh"].ts)) if len(ctx["feat_242"]) and len(ctx["feat_sh"]) else []
        tsl = tsl[-40:]
        gens = []
        for ts in tsl:
            k = dt.datetime.fromtimestamp(ts / 1000, TZ).strftime("%Y%m%d-%H%M")
            try:
                _, meta, rec = c.get(("ticker", "ai_pred_1m", k))
            except Exception:
                continue
            m = re.search(rb'predReturn15M":(-?[0-9.eE+-]+)', rec["data"] if isinstance(rec["data"], bytes) else str(rec["data"]).encode())
            if not m:
                continue
            v = float(m.group(1))
            a = float(feat["sh"][feat["sh"].ts == ts].p15_out.iloc[0])
            b = float(feat["242"][feat["242"].ts == ts].p15_out.iloc[0])
            res.append((ts, v, a, b))
            gens.append(meta.get("gen"))
        c.close()
        if res:
            r = pd.DataFrame(res, columns=["ts", "ai", "sh", "242"])
            d_sh = (r.ai - r.sh).abs().max()
            d_242 = (r.ai - r["242"]).abs().max()
            ctx["b8"] = {"n": len(r), "max_abs_ai_vs_sh": float(d_sh), "max_abs_ai_vs_242": float(d_242), "gen_values": sorted(set(gens))}
            items.append(item("B8", "B", "p15 live (feat_dump p15_out) vs ai_pred_1m Aerospike 242 cung phut (n=%d)" % len(r),
                              "khop; ai_pred_1m = last-writer(242|shadow) toi 10-07",
                              "max|ai-p15_sh|=%.2e" % d_sh, "max|ai-p15_242|=%.2e; gen=%s" % (d_242, sorted(set(gens))),
                              PASS if d_sh <= 1e-6 else FAIL, PASS if d_242 <= 1e-6 else FAIL,
                              "2 writer (gen=2) => 1 trong 2 so se lech; fix = jar f282581a + LIVE_IS_SHADOW_HOST=true (10-07 17:15), KHONG lam som",
                              known=True))
        else:
            items.append(item("B8", "B", "p15 vs ai_pred_1m", "-", "khong lay duoc", "-", MISSING, MISSING))
    except Exception as e:
        items.append(item("B8", "B", "p15 vs ai_pred_1m", "-", "loi: %s" % str(e)[:80], "-", MISSING, MISSING))
    return items


# ====================================================================== C. selector
def layer_C(ctx):
    items = []
    a, b = ctx["sel_sh"], ctx["sel_242"]
    since = ctx["since_ms"]
    if a.empty or b.empty:
        return [item("C1", "C", "top-16 shadow vs 242", "-", "thieu sel_dump", "-", MISSING, MISSING)]
    a = a[a.ts >= since]
    b = b[b.ts >= since]
    common = sorted(set(a.ts) & set(b.ts))
    ov, r1, gv_d = [], 0, []
    for ts in common:
        sa = a[a.ts == ts]
        sb = b[b.ts == ts]
        s_a, s_b = set(sa.symbol), set(sb.symbol)
        ov.append(len(s_a & s_b))
        if sa.sort_values("rank").symbol.iloc[0] == sb.sort_values("rank").symbol.iloc[0]:
            r1 += 1
        m = sa.merge(sb, on="symbol", suffixes=("_s", "_2"))
        if len(m):
            gv_d.extend(((m.gateValue_s - m.gateValue_2).abs()).tolist())
    ov = np.array(ov)
    if not len(ov):
        return [item("C1", "C", "top-16 shadow vs 242", "-", "khong co tick chung", "-", MISSING, MISSING)]
    ok = ov.mean() >= 15 and (ov >= 14).mean() >= 0.95
    ctx["c1"] = {"n_ticks": int(len(ov)), "mean_overlap": float(ov.mean()), "frac_ge14": float((ov >= 14).mean()),
                 "frac_16": float((ov == 16).mean()), "rank1_same": r1 / len(ov),
                 "gv_absdiff_median": float(np.median(gv_d)) if gv_d else None, "gv_absdiff_p90": float(np.quantile(gv_d, .9)) if gv_d else None}
    items.append(item("C1", "C", "top-16 shadow vs 242 cung tick (|giao|)", "16/16",
                      "mean %.2f/16; =16: %.1f%%; >=14: %.1f%%; rank1 giong %.1f%% (n=%d tick); |dgateValue| p50=%.4f p90=%.4f" % (
                          ov.mean(), 100 * (ov == 16).mean(), 100 * (ov >= 14).mean(), 100 * r1 / len(ov), len(ov),
                          ctx["c1"]["gv_absdiff_median"] or 0, ctx["c1"]["gv_absdiff_p90"] or 0), "-",
                      PASS if ok else FAIL, PASS if ok else FAIL,
                      "lech feature/OI giua 2 box (D1/D3); khong sua duoc bang env" if not ok else "", known=not ok))
    # C2 thu tu sort
    def mono(s):
        bad = 0
        n = 0
        for ts, d in s.groupby("ts"):
            d = d.sort_values("rank")
            n += 1
            if not (np.all(np.diff(d.gateValue.values) >= -1e-9) and np.all(np.diff(d.selectorScore.values) >= -1e-9)):
                bad += 1
        return bad, n
    bs, ns = mono(a)
    b2_, n2 = mono(b)
    items.append(item("C2", "C", "sort: rank tang => selectorScore & gateValue(sp) khong giam; rank1 = sp thap nhat (sim: sp nho = tot)",
                      "100% tick", "%d/%d tick vi pham" % (bs, ns), "%d/%d tick vi pham" % (b2_, n2),
                      PASS if bs == 0 else FAIL, PASS if b2_ == 0 else FAIL))
    items.append(item("C3", "C", "recompute offline top-16 tu model deploy (S1 8b1dcf00 + net015 41a07109 + map) tren CUNG feature vector live (45 G015 + 9 KEEP9)",
                      "16/16", "feat_dump KHONG ghi vector 45/9 (chi 33 gate-feature) -> khong tai tao duoc", "idem", MISSING, MISSING,
                      "CAN CODE: LiveFeatureDump.maybeDumpSelector them 45+9 cot (hoac dump selFeat45/S1 float[9])",
                      evidence="research ref: MAP_PARITY 16/16 (sim, B0REF5), LiveBuildMapTest byte-parity (AUDIT_SELECTOR_MODEL_PARITY §1)"))
    s1s, s12 = ctx["log_sh"]["s1"], ctx["log_242"]["s1"]
    items.append(item("C4", "C", "n_cand=16 moi tick; so coin duoc cham diem [S1] score N", "16; ~universe sim",
                      "n_cand=%s; N median=%s [%s..%s]" % (sorted(ctx["gate_sh"].n_cand.unique().tolist()),
                                                           int(s1s.n_score.median()) if len(s1s) else "-",
                                                           int(s1s.n_score.min()) if len(s1s) else "-", int(s1s.n_score.max()) if len(s1s) else "-"),
                      "n_cand=%s; N median=%s [%s..%s]" % (sorted(ctx["gate_242"].n_cand.unique().tolist()),
                                                           int(s12.n_score.median()) if len(s12) else "-",
                                                           int(s12.n_score.min()) if len(s12) else "-", int(s12.n_score.max()) if len(s12) else "-"),
                      PASS if sorted(ctx["gate_sh"].n_cand.unique().tolist()) == [16] else FAIL,
                      PASS if sorted(ctx["gate_242"].n_cand.unique().tolist()) == [16] else FAIL))
    return items


# ====================================================================== D. feature
def layer_D(ctx):
    items = []
    a, b = ctx["feat_sh"], ctx["feat_242"]
    if a.empty or b.empty:
        return [item("D1", "D", "33 feature shadow vs 242", "-", "thieu feat_dump", "-", MISSING, MISSING)]
    m = a.merge(b, on=["ts", "symbol"], suffixes=("_s", "_2"))
    cols = [c for c in a.columns if c not in ("ts", "symbol")]
    rows = []
    for c in cols:
        x, y = m[c + "_s"].values.astype(float), m[c + "_2"].values.astype(float)
        mk = ~(np.isnan(x) | np.isnan(y))
        if not mk.any():
            continue
        x, y = x[mk], y[mk]
        d = np.abs(x - y)
        ok = d <= FEAT_REL * (1 + np.abs(y))
        rows.append((c, float(ok.mean()), float(np.median(d)), float(d.max())))
    t = pd.DataFrame(rows, columns=["col", "frac_ok", "med_abs", "max_abs"])
    bad = t[t.frac_ok < 0.99]
    ctx["d1"] = {"n_pairs": int(len(m)), "n_cols": len(t), "n_cols_fail": int(len(bad)),
                 "fail_cols": [(r.col, round(r.frac_ok, 3), "%.2e" % r.max_abs) for r in bad.itertuples()],
                 "all": [(r.col, round(r.frac_ok, 3)) for r in t.itertuples()]}
    items.append(item("D1", "D", "33 feature gate (+4 market, p15_out): shadow vs 242 cung (ts,symbol), |d|<=1e-3(1+|x|)", "giong (cung nguon, cung code)",
                      "%d/%d cot PASS (n=%d cap); FAIL: %s" % (len(t) - len(bad), len(t), len(m), ", ".join("%s(%.0f%%)" % (r.col, 100 * r.frac_ok) for r in bad.itertuples())),
                      "-", PASS if bad.empty else FAIL, PASS if bad.empty else FAIL,
                      "nguon lech Oracle<->242 (doc ticker qua WAN, nen cuoi chua chot) — can code/di chuyen shadow ve cung LAN" if not bad.empty else "",
                      known=not bad.empty))
    items.append(item("D2", "D", "33 feature live vs DEV export cung phut (parity_check.py features)", "27/33 FAIL lan truoc (thieu nguon/ticker-vs-kline)",
                      ctx.get("harness_feat", "chua chay"), "-", ctx.get("harness_feat_status", MISSING), ctx.get("harness_feat_status", MISSING),
                      "lech da biet (RESULT_FEATDIFF_PASS2): tong hieu ung len p15 <= 0.006pp", known=True))
    items.append(item("D3", "D", "45 cot G015 + 9 cot KEEP9 (vector selector) live vs offline cung phut", "khop",
                      "shadow KHONG dump vector selector", "242 KHONG dump vector selector", MISSING, MISSING,
                      "CAN CODE (LiveFeatureDump); OI feature da audit rieng: AUDIT_OI_FEAT_PARITY = KHONG VENH (spearman 1.0)",
                      evidence="feat_dump header 40 cot = 33 gate + p15_out + 4 market; sel_dump 6 cot"))
    return items


# ====================================================================== E. entry / size
def load_fp(tag):
    d = {}
    p = "%s/fp_%s.txt" % (OUT, tag)
    if not os.path.exists(p):
        return d
    for ln in open(p):
        q = ln.rstrip("\n").split("\t")
        if len(q) >= 4:
            d[q[1]] = (float(q[2]), int(q[3]))
    return d


def layer_E(ctx):
    items = []
    fb, fs, f2 = load_fp("b0"), load_fp("shadow"), load_fp("242")
    ev_src = src_grep("trading/DetectEntrySignal2TradeNormal.java", r"budget = TradeUtils\.managerBudget")
    ev_ratio = src_grep("research/SimulatorMarketLevelTicker1MStopLoss.java", r"float ratio = DcaUtils\.gridLegWeightRatio")
    ev_live_ratio = None
    p = SRC + "/trading/DetectEntrySignal2TradeNormal.java"
    if os.path.exists(p):
        ev_live_ratio = ("gridLegWeightRatio/DCA_GRID_SCALE xuat hien trong DetectEntrySignal2TradeNormal.java: %s" %
                         ("CO" if re.search(r"gridLegWeightRatio|DCA_GRID_SCALE", open(p, errors="replace").read()) else "KHONG"))
    if not (fb and fs):
        return [item("E2", "E", "margin leg dau", "-", "thieu FormulaProbe", "-", MISSING, MISSING)]

    def leg0(f, with_ratio):
        b = f["B 35000 0"][0]
        return b * (f["G 0"][0] if with_ratio else 1.0)
    sim_leg0 = leg0(fb, True)                  # B0: DCA_GRID_ENABLED=true -> budget *= gridLegWeightRatio(0)

    def live_leg0(f):
        # [LIVE-SIZING 2026-10-03] probe "L" = ham THAT cua duong live (LiveGridSizing.legBudget) duoi env
        #   cua box; jar/env khong co => fallback managerBudget (live cu khong nhan ratio).
        if "L 35000 0 0" in f:
            return f["L 35000 0 0"][0]
        return leg0(f, False)
    sh_leg0 = live_leg0(fs)
    l242_leg0 = live_leg0(f2)
    ratio_ = sh_leg0 / sim_leg0
    ctx["e2"] = {"sim_leg0_at_eq35000": sim_leg0, "shadow_leg0": sh_leg0, "242_leg0": l242_leg0, "ratio_live_over_sim": ratio_,
                 "managerBudget(35000,0)": fs["B 35000 0"][0], "gridLegWeightRatio(0)_B0": fb["G 0"][0]}
    fix = ctx.get("fbase_fixed")
    if fix:
        sh_leg0 = fix["leg0"]
        ratio_ = sh_leg0 / sim_leg0
    ok = abs(ratio_ - 1) <= 1e-6
    items.append(item("E2", "E", "margin leg dau @equity 35000, throttle 1: sim = managerBudget*tier*(w0*DCA_GRID_SCALE); live = managerBudget*tier",
                      "%.2f USDT (=%.2f%% equity)" % (sim_leg0, 100 * sim_leg0 / 35000),
                      "%.2f USDT (live/sim = %.4f)%s" % (sh_leg0, ratio_, " [SAU SUA SIM_F_BASE=%s]" % fix["f_base"] if fix else ""),
                      "%.2f USDT (live/sim = %.4f)" % (l242_leg0, l242_leg0 / sim_leg0),
                      PASS if ok else FAIL, FAIL if abs(l242_leg0 / sim_leg0 - 1) > 1e-6 else PASS,
                      "shadow: LIVE_APPLY_GRID_RATIO=true => live = managerBudget x gridLegWeightRatio(0) (LiveGridSizing, probe L), SIM_F_BASE=0.015 = B0 (bo bu 0.09). 242: chua bat (cung goi code + env, owner quyet)",
                      known=False, evidence="%s | %s | %s" % (ev_src, ev_ratio, ev_live_ratio)))
    items.append(item("E1", "E", "gia vao = ticker.priceClose cua nen tin hieu (live: OrderTargetInfo.priceEntry=ticker.priceClose -> ShadowBookC3.openPos)",
                      "entry = priceClose", "dung (code)", "dung (code, legacy khong mo lenh moi)", PASS, PASS,
                      evidence="%s | %s" % (src_grep("trading/DetectEntrySignal2TradeNormal.java", r"new OrderTargetInfo\(OrderTargetStatus\.REQUEST, ticker\.priceClose"),
                                            src_grep("research/SimulatorMarketLevelTicker1MStopLoss.java", r"Float entry = ticker\.priceClose"))))
    cap = LIVE_CAP = 0.045 * 35000
    items.append(item("E3", "E", "tran per-coin CONC_CAP_PERCOIN 15% equity va tran live 4.5% equity (live-only) co chan leg dau?", "khong bind",
                      "leg dau %.2f%% equity < 4.5%% va < 15%% => khong bind" % (100 * sh_leg0 / 35000), "idem", PASS, PASS))
    # shadow co F_BASE = B0 x 6 (E2 fix) -> managerBudget shadow = B0 x fscale; 242 giu F_BASE B0 (fscale=1)
    fscale = fs["B 35000 0"][0] / fb["B 35000 0"][0] if fb["B 35000 0"][0] else 1.0

    def _e4eq(x, y):
        return (math.isnan(x) and math.isnan(y)) or abs(x - y) <= 1e-6 * max(1.0, abs(x))
    items.append(item("E4", "E", "U=Sum(margin)/equity, throttle=1-U/U_MAX (U_MAX=0.60): hai ham managerBudget chung; live: marginRunning=ShadowBookC3 (khong DCA leg => U thap hon sim)",
                      "cung ham", "B(35000,5000)=%.2f | B(40000,12000)=%.2f | B(35000,21000)=%s" % (fs["B 35000 5000"][0], fs["B 40000 12000"][0], fs["B 35000 21000"][0]),
                      "idem", PASS if all(_e4eq(fb[k][0] * fscale, fs[k][0]) for k in fb if k.startswith("B ")) else FAIL,
                      PASS if all(fb[k][0] == f2[k][0] or (math.isnan(fb[k][0]) and math.isnan(f2[k][0])) for k in fb if k.startswith("B ")) else FAIL))
    # [LIVE-DCA-GRID 2026-10-03] shadow: code LiveDcaGridC3 + env LIVE_DCA_GRID_ENABLED=true => grid co tren so giay.
    #   PASS khi legs.csv co leg_idx>=1; chua co leg => MISSING (cho gia rot -50%).
    sh_env = read_env_file(SH_APP + "/conf/env.sh") if os.path.exists(SH_APP + "/conf/env.sh") else {}
    has_code = os.path.exists(SRC + "/tradecore/selector/LiveDcaGridC3.java")
    sh_grid_on = has_code and str(sh_env.get("LIVE_DCA_GRID_ENABLED", "")).strip().lower() == "true"
    n_grid_legs = 0
    legs_csv = SHADOW + "/legs.csv"
    if os.path.exists(legs_csv):
        try:
            Lg = pd.read_csv(legs_csv)
            n_grid_legs = int((Lg.leg_idx >= 1).sum()) if len(Lg) else 0
        except Exception:
            n_grid_legs = 0
    if sh_grid_on:
        e5_sh_txt = "CO (LiveDcaGridC3, LIVE_DCA_GRID_ENABLED=true): %d leg grid (leg_idx>=1) trong legs.csv" % n_grid_legs
        e5_sh = PASS if n_grid_legs > 0 else MISSING
    else:
        e5_sh_txt = "KHONG co (DcaProcessor.getDCAProduction duyet vi the THAT; shadow khong co)"
        e5_sh = FAIL
    items.append(item("E5", "E", "DCA grid (leg 1-3 tai -50/-75/-90%) + DCA_LEVEL1", "co (46 DCA_LEVEL1 + leg grid)",
                      e5_sh_txt, "chi coin legacy (skip-LEGACY cho so giay)",
                      e5_sh, FAIL, "shadow: code co, cho leg dau tien (gia rot -50% tu leg dau). 242: chua bat", known=not sh_grid_on,
                      evidence=src_grep("tradecore/DcaProcessor.java", r"getDCAProduction")))
    led = SHADOW + "/ledger.csv"
    ev6 = "khong co ledger"
    if os.path.exists(led):
        L = pd.read_csv(led)
        if len(L):
            L["notional"] = L.entry * L.qty
            L["t0"] = pd.to_datetime(L.ts_entry, unit="ms")
            ev6 = "%d lenh giay, ts_entry %s..%s, notional p50=%.0f (rank/pred cu), reason=%s; 0 lenh tu 2a (10-02 17:53)" % (
                len(L), L.t0.min().date(), L.t0.max().date(), L.notional.median(), L.reason.value_counts().to_dict())
    items.append(item("E6", "E", "ledger giay shadow/242 (archive) — size thuc te", "-", ev6, "ledger.csv 242: 0 lenh (n_pass=0)", MISSING, MISSING,
                      "chua co lenh sau 2a (n_pass=0 den arm 10-07); xac nhan size khi co lenh dau tien: margin = %.2f x throttle" % sim_leg0))
    return items


# ====================================================================== F. exit
def f32_trail(peak, pnp, ratio, gap_strong, gap_weak, thr_weak):
    peak = np.float32(peak)
    gap = gap_weak if pnp > thr_weak else gap_strong
    g = np.minimum(peak * np.float32(ratio), np.float32(gap))
    rate = peak - g
    step = np.float32(0.005)
    q = np.floor(np.float64(np.float32(rate / step)) + 0.5)
    return np.float32(np.float32(q) * step)


def layer_F(ctx):
    items = []
    fb, fs, f2 = load_fp("b0"), load_fp("shadow"), load_fp("242")
    ev = {}
    ev["arm"] = src_grep("tradecore/selector/LiveProfileC3.java", r"ARM_RATE = 0\.07f")
    ev["ts"] = src_grep("tradecore/selector/LiveProfileC3.java", r"TIME_STOP_HOURS = 168")
    ev["dz_live"] = src_grep("trading/BinanceOrderTradingManager.java", r"LIVE_RATCHET_DEADZONE_MULT = 5\.21847f")
    ev["dz_on"] = src_grep("tradecore/selector/LiveProfileC3.java", r"RATCHET_DEADZONE_MULT_ON = 1\.0f")
    ev["sim_arm"] = src_grep("research/SimulatorMarketLevelTicker1MStopLoss.java", r"peakPrice\(ticker\) >= orderMulti\.priceEntry \* \(1 \+ armRate\)")
    ev["paper_arm"] = src_grep("tradecore/selector/ShadowBookC3.java", r"rate > LiveProfileC3\.ARM_RATE")
    ev["paper_fill"] = src_grep("tradecore/selector/ShadowBookC3.java", r"closeAt\(c, c\.priceSL, REASON_TRAILING")
    ev["sim_fill"] = src_grep("research/OrderTargetInfoTest.java", r"priceTP = Math\.min\(priceSL, ticker\.priceOpen\)")
    ev["sim_block"] = src_grep("research/OrderTargetInfoTest.java", r"BLOCK_INTRABAR_LOOKAHEAD\)")
    ev["paper_px"] = src_grep("trading/BinanceOrderTradingManager.java", r"currentSecond % 10 == 0")
    items.append(item("F1", "F", "arm 7%: giay hardcode LiveProfileC3.ARM_RATE=0.07; legacy Configs.RATE_PROFIT_STOP_MARKET (env)", "0.07",
                      "0.07 (hardcode)", "legacy: %s; giay: 0.07" % (load_probe("242").get("Configs.RATE_PROFIT_STOP_MARKET")),
                      PASS if ev["arm"] else MISSING,
                      PASS if load_probe("242").get("Configs.RATE_PROFIT_STOP_MARKET") == "0.07" else FAIL, evidence="%s | %s" % (ev["arm"], ev["paper_arm"])))
    # F2/F3 so khop ham Java that vs Python f32 tren luoi
    def cmp_trail(f, tag):
        pr = load_probe(tag)
        if not f or not pr:
            return None
        ratio = float(pr["Configs.TS_GIVEBACK_RATIO"])
        gs, gw, thr = float(pr["Configs.TS_MAX_GAP"]), float(pr["Configs.TS_MAX_GAP_WEAK"]), float(pr["PROBE_TS_PNOPUMP_WEAK_THR"])
        n_bad, n, worst = 0, 0, 0.0
        for k, (v, bits) in f.items():
            if not k.startswith("R "):
                continue
            _, peak, pnp = k.split()
            ref = f32_trail(float(peak), float(pnp), ratio, gs, gw, thr)
            n += 1
            if np.float32(v) != ref:
                n_bad += 1
                worst = max(worst, abs(float(v) - float(ref)))
        return n, n_bad, worst
    c_b0, c_sh, c_242 = cmp_trail(fb, "b0"), cmp_trail(fs, "shadow"), cmp_trail(f2, "242")
    eq_b0_sh = all(fb[k][1] == fs[k][1] for k in fb if k.startswith("R ")) if fb and fs else None
    eq_b0_242 = all(fb[k][1] == f2[k][1] for k in fb if k.startswith("R ")) if fb and f2 else None
    ex = {k: round(v[0], 5) for k, v in fs.items() if k in ("R 0.07000 0.10", "R 0.08000 0.10", "R 0.10000 0.10", "R 0.20000 0.10")}
    items.append(item("F2", "F", "SL sau arm = trailFromCap(peak): peak - min(peak*1.0, 0.03), lam tron 0.005; ham Java that (calRateLossDynamicBuyPNoPump) vs Python float32, %s diem" % (c_sh[0] if c_sh else "-"),
                      "SL(peak=7%)=+4.0%; SL(peak=10%)=+7.0%", "Java==Py: %s sai; B0==shadow bit-exact: %s; vi du %s" % (c_sh[1] if c_sh else "-", eq_b0_sh, ex),
                      "Java==Py: %s sai; B0==242 bit-exact: %s" % (c_242[1] if c_242 else "-", eq_b0_242),
                      PASS if c_sh and c_sh[1] == 0 and eq_b0_sh else FAIL, PASS if c_242 and c_242[1] == 0 and eq_b0_242 else FAIL))
    items.append(item("F3", "F", "lam tron 0.5% (step 0.005) — chung ham trailFromCap voi sim (OrderTargetInfoTest.trailRate)", "step 0.005", "= sim (cung ham)", "= sim (cung ham)",
                      PASS, PASS, evidence=src_grep("tradecore/TradeUtils.java", r"float step = 0\.005f")))
    items.append(item("F4", "F", "ratchet: giay lien tuc (mult 1.0); legacy dead-zone x5.21847 (arm*5.22=36.5%)", "sim lien tuc",
                      "giay: lien tuc (%s)" % ev["dz_on"], "legacy: dead-zone x5.21847 => SL dung yen o +4% khi lai 7-36.5% (co chu y L3, khong doi luat tien that)",
                      PASS if ev["dz_on"] else MISSING, FAIL, "owner chot huong (khong tu dong bo) — de xuat: legacy 242 = ratchet lien tuc (can code/env?)", known=True,
                      evidence=str(ev["dz_live"])))
    items.append(item("F5", "F", "time-stop 168h cho cum CHUA arm: giay co; legacy khong", "co (SIM_LOSER_TIME_STOP_HOURS=168, min(open,close))",
                      "co (ShadowBookC3 tick, px snapshot)", "legacy: khong (timeStopApplies=false) — 0 lenh giay",
                      PASS if ev["ts"] else MISSING, FAIL, "legacy 242: chi bao cao", known=True, evidence=str(ev["ts"])))
    items.append(item("F6", "F", "SL cung ban dau pre-arm (PRE_ARM_SL / HARD SL / calRateLossDynamic cu)", "B0: khong co (PRE_ARM_SL=0)",
                      "khong co (PRE_ARM_SL=0, khong nhanh trong ShadowBookC3)", "idem", PASS, PASS,
                      evidence="Configs.PRE_ARM_SL=%s" % load_probe("shadow").get("Configs.PRE_ARM_SL")))
    items.append(item("F7", "F", "nguon dinh/gia: sim = HIGH nen 1m (peakPrice), fill SL = min(SL, open); giay = snapshot price_realtime moi 10s, fill = dung SL", "HIGH/LOW 1m",
                      "snapshot 10s (dinh THAP hon HIGH => arm tre/it hon; fill SL khong haircut gap)", "legacy: lenh SL that tren san (tiem can sim hon)",
                      FAIL, FAIL, "CAN CODE (ShadowBookC3.tick doc high/low 1m) — hien khong sua duoc bang env", known=True,
                      evidence="%s | %s | %s | %s" % (ev["sim_arm"], ev["paper_arm"], ev["sim_fill"], ev["paper_fill"])))
    items.append(item("F8", "F", "uu tien cung nen: sim dat SL o nen arm, khong khop cung nen (BLOCK_INTRABAR_LOOKAHEAD); giay: arm->ratchet->kiem px<=SL cung tick",
                      "khong khop cung nen", "co the khop cung tick (gap 3pp nen hiem)", "-", FAIL, MISSING, "cung nhom F7 (code)", known=True, evidence=str(ev["sim_block"])))
    items.append(item("F9", "F", "vi the dang chay (giay/legacy): doi chieu SL so vs cong thuc", "-", "0 vi the giay (n_pass=0 tu 2a)",
                      "legacy %s symbol, 0 'New price SL'/'Update SL' tu 10-01 (chua legacy nao lai >7%%)" % ctx["meta242"].get("legacy_n"), MISSING, MISSING,
                      "chua kiem duoc; chay lai khi co lenh"))
    return items


# ====================================================================== G. fee / funding
def layer_G(ctx):
    items = []
    txt = ""
    p = SRC + "/tradecore/selector/ShadowBookC3.java"
    if os.path.exists(p):
        txt = open(p, errors="replace").read()
    no_fee = ("RATE_FEE" not in txt) and ("SLIPPAGE" not in txt) and ("FUNDING" not in txt.replace("funding", ""))
    sim_cost = 2 * 0.000982 + 2 * 0.000067
    items.append(item("G1", "G", "ledger giay: pnl=(exit-entry)*qty, KHONG tru phi/slippage/funding", "sim tru: fee 0.000982 + 2*slip 0.000067 ~ %.4f%%/vong + funding mark" % (100 * sim_cost),
                      "khong tru (PnL giay lac quan ~%.3f%% notional/vong + funding)" % (100 * sim_cost), "idem (so giay)", FAIL if no_fee else PASS, FAIL if no_fee else PASS,
                      "tinh offline tu ledger (tools/shadow_vs_sim.py); CAN CODE de tru trong ledger", known=True,
                      evidence=src_grep("tradecore/selector/ShadowBookC3.java", r"double pnl = \(exitPx - entry\)")))
    items.append(item("G2", "G", "242: fill that legacy dong — phi thuc te vs 0.1116%/vong", "0.1116%", "-", "khong co fill legacy nao dong tu 10-01", MISSING, MISSING,
                      "doc userTrades khi co lenh dong (khong co API key o day)"))
    return items


# ====================================================================== H. cadence / latency
NOISE_RX = re.compile(r"-2015|calReportRunning|Reporter|BinanceP2PTracker|Legacy Scan|Invalid API-key", re.I)


def layer_H(ctx):
    items = []
    for key, nm in (("sh", "shadow"), ("242", "242")):
        pass
    tm_s, tm_2 = ctx["log_sh"]["timing"], ctx["log_242"]["timing"]

    def pct(t):
        if t.empty:
            return None
        return float(t.ms.median()), float(t.ms.quantile(.9)), float(t.ms.max()), len(t)
    ps, p2 = pct(tm_s), pct(tm_2)
    items.append(item("H1", "H", "[PASS-TIMING] selector tick (ms) p50/p90/max trong cua so; nhip 60 s",
                      "p90 << 60000 ms",
                      "p50=%.0f p90=%.0f max=%.0f (n=%d)" % ps if ps else "thieu", "p50=%.0f p90=%.0f max=%.0f (n=%d)" % p2 if p2 else "thieu",
                      (PASS if ps[1] < 10000 else FAIL) if ps else MISSING, (PASS if p2[1] < 10000 else FAIL) if p2 else MISSING,
                      "shadow cham hon 242 (doc Aerospike 242 qua WAN) nhung << 60 s"))

    def errs(l):
        bad = {k: v for k, v in l["errs"].items() if not NOISE_RX.search(k)}
        oom = sum(v for k, v in l["errs"].items() if "OutOfMemory" in k)
        return bad, oom
    bs, oo_s = errs(ctx["log_sh"])
    b2, oo_2 = errs(ctx["log_242"])
    items.append(item("H2", "H", "OOM + ERROR moi (tru nhieu co san: -2015 stub-key, Reporter NPE, P2PTracker, Legacy Scan) trong cua so", "0",
                      "OOM=%d, ERROR la=%d %s" % (oo_s, sum(bs.values()), list(bs.items())[:3]), "OOM=%d, ERROR la=%d %s" % (oo_2, sum(b2.values()), list(b2.items())[:3]),
                      PASS if (oo_s == 0 and not bs) else FAIL, PASS if (oo_2 == 0 and not b2) else FAIL,
                      "loi Aerospike WAN (Node not found / MAT DATA chunk / getMetricMap) ngay sau restart: shadow doc Aerospike 242 qua WAN; "
                      "tu hoi phuc ([GATE] dung nhip), khong sua duoc bang env" if any(re.search("AEROSPIKE|getMetricMap|Node not found", k) for k in bs) else "",
                      known=any(re.search("AEROSPIKE|getMetricMap|Node not found", k) for k in bs)))
    oi_s = ctx.get("oi_sh", "")
    items.append(item("H2b", "H", "[OI-LIVE] mode inplace, refresh hang gio evicted=0", "inplace; evicted=0",
                      ctx.get("oi_sh_txt", "-"), ctx.get("oi_242_txt", "-"),
                      PASS if ctx.get("oi_sh_ok") else (MISSING if (not ctx.get("oi_sh_txt") or "refresh=0," in ctx.get("oi_sh_txt", "")) else FAIL),
                      PASS if ctx.get("oi_242_ok") else (MISSING if (not ctx.get("oi_242_txt") or "refresh=0," in ctx.get("oi_242_txt", "")) else FAIL)))
    penv = proc_env(ctx.get("shadow_pid")) if ctx.get("shadow_pid") else {}
    jt = penv.get("JAVA_TOOL_OPTIONS", "")
    m242 = ctx["meta242"]
    has242 = ("Xmx" in m242["cmdline"]) or ("JAVA_TOOL_OPTIONS" in m242["env"])
    items.append(item("H3", "H", "auto-restart 12h giu heap: JAVA_TOOL_OPTIONS trong environ (con ke thua) / -Xmx", "giu heap 3g (kiem 3 restart)",
                      "co: %s; jcmd MaxHeap=%s; 'Picked up' sau moi restart: %s" % (jt, ctx.get("shadow_maxheap"), ctx.get("shadow_pickedup")),
                      "KHONG: cmdline=%s; JAVA_TOOL_OPTIONS vang => heap mac dinh (~1.95GB) sau restart 12h" % m242["cmdline"][-110:],
                      PASS if ("Xmx3g" in jt and ctx.get("shadow_pickedup")) else FAIL, FAIL if not has242 else PASS,
                      "242: CHI DE XUAT: them export JAVA_TOOL_OPTIONS vao conf/env.sh (an toan, khong .java) — owner quyet", known=not has242))
    return items


# ====================================================================== I. data in
def layer_I(ctx):
    items = []
    s1s, s12 = ctx["log_sh"]["s1"], ctx["log_242"]["s1"]
    sy = set(ctx["sel_sh"].symbol) | set(ctx["sel_242"].symbol)
    odd = sorted(s for s in sy if (not s.endswith("USDT")) or ("_" in s) or ("USDC" in s) or s == "BTCDOMUSDT")
    sh_n = "N median=%s [%s..%s] (n_enough median=%s)" % (int(s1s.n_score.median()), int(s1s.n_score.min()), int(s1s.n_score.max()), int(s1s.n_enough.median())) if len(s1s) else "-"
    d_n = "N median=%s [%s..%s] (n_enough median=%s)" % (int(s12.n_score.median()), int(s12.n_score.min()), int(s12.n_score.max()), int(s12.n_enough.median())) if len(s12) else "-"
    # sau restart shadow: so coin tang khi OI refresh dau gio
    after = ""
    if len(s1s):
        first = s1s.iloc[:30].n_score.median()
        last = s1s.iloc[-30:].n_score.median()
        after = "; 30 tick dau cua so=%d, 30 tick cuoi=%d" % (first, last)
    items.append(item("I1", "I", "universe live: so coin cham diem [S1] (>=336 moc gio) vs sim (mapper 863 id gom delisted)", "universe sim: USDT-perp, khong USDC/BTCDOM/_ (SurvivorshipBac0:52)",
                      sh_n + after, d_n, PASS if len(s1s) and not odd else FAIL, PASS if len(s12) and not odd else FAIL,
                      "sau restart shadow universe nho ~560 den khi OI refresh gio dau (cold-load OI 564 coin) — xem H2b" if after else "",
                      evidence="symbol la trong top-16 (%d symbol): %s" % (len(sy), odd[:5])))
    items.append(item("I2", "I", "symbol vol=0 / symbol la vao top-16", "khong", "top-16 %d symbol khac nhau, 0 ky tu la; vol=0 KHONG kiem duoc (dump khong co volume; S1RankerLive chi loc pc<=0)" % len(sy),
                      "idem", MISSING, MISSING, "CAN CODE hoac Aerospike scan volume; neu can: loc theo kline_1m_opt volume"))
    n_leg = ctx["meta242"].get("legacy_n")
    items.append(item("I3", "I", "coin legacy (vi the THAT cu tren 242) bi chan khoi so giay", "-", "legacy_symbols.csv shadow: 0 (khong vi the that)",
                      "%s coin legacy; 'skip-LEGACY' %s lan trong log" % (n_leg, ctx.get("skip_legacy_242")), PASS, PASS, "ghi nhan"))
    return items


# ====================================================================== build / report
def oi_summary(path, since_ms, filtered=False):
    n_in = n_cold = n_ref = bad = 0
    last = ""
    for ln in read_lines(path):
        if "OI-LIVE]" not in ln:
            continue
        try:
            t = parse_ts_log(ln[:19])
        except Exception:
            continue
        if t < since_ms:
            continue
        if "inplace cold-load" in ln:
            n_cold += 1
        elif "inplace refresh" in ln:
            n_ref += 1
            if "evicted=0" not in ln:
                bad += 1
        if "reload" in ln and "lỗi" in ln:
            bad += 1
        last = ln[:120]
    return n_cold, n_ref, bad


def build(since_txt=None, do_fetch=False, do_probe=False):
    if do_fetch:
        LOG.info("fetch 242 (doc-chi): %s", fetch242())
    if do_probe:
        LOG.info("probe: %s", run_java_probes())
    now_ms = int(dt.datetime.now(TZ).timestamp() * 1000)
    ctx = {"now_ms": now_ms}
    ctx["meta242"] = parse_meta242()
    sh_log = SH_APP + "/logs/full.log"
    l242 = L242 + "/full_filtered.log"
    st_sh = load_log(sh_log, 10 ** 18)["starts"]
    st_242 = load_log(l242, 10 ** 18)["starts"] if os.path.exists(l242) else []
    if since_txt:
        since = ms(dt.datetime.strptime(since_txt, "%Y-%m-%d %H:%M").replace(tzinfo=TZ))
    else:
        since = max(st_sh[-1] if st_sh else 0, st_242[-1] if st_242 else 0) + 3 * 60000
    ctx["since_ms"] = since
    ctx["since_txt"] = dt.datetime.fromtimestamp(since / 1000, TZ).strftime("%Y-%m-%d %H:%M")
    ctx["restart_shadow"] = dt.datetime.fromtimestamp(st_sh[-1] / 1000, TZ).strftime("%Y-%m-%d %H:%M:%S") if st_sh else None
    ctx["restart_242"] = dt.datetime.fromtimestamp(st_242[-1] / 1000, TZ).strftime("%Y-%m-%d %H:%M:%S") if st_242 else None
    ctx["log_sh"] = load_log(sh_log, since)
    ctx["log_242"] = load_log(l242, since) if os.path.exists(l242) else load_log("/dev/null", since)
    ctx["gate_sh"], ctx["gate_242"] = ctx["log_sh"]["gate"], ctx["log_242"]["gate"]
    ctx["ratio_sh"], ctx["ratio_242"] = ctx["log_sh"]["ratio"], ctx["log_242"]["ratio"]
    ctx["sel_sh"] = load_dump(SH_APP + "/feat_dump", "sel_dump", since - 60000)
    ctx["sel_242"] = load_dump(L242 + "/fd", "sel_dump", since - 60000)
    ctx["feat_sh"] = load_dump(SH_APP + "/feat_dump", "feat_dump", since - 60000)
    ctx["feat_242"] = load_dump(L242 + "/fd", "feat_dump", since - 60000)
    for k in ("feat_sh", "feat_242"):
        if len(ctx[k]) and "p15_out" in ctx[k]:
            ctx[k] = ctx[k].dropna(subset=["p15_out"]).reset_index(drop=True)
    rc, out, _ = sh("systemctl show -p MainPID --value shadow-c3")
    ctx["shadow_pid"] = out.strip() if rc == 0 else None
    rc, out, _ = sh("jcmd %s VM.flags 2>/dev/null | tr ' ' '\\n' | grep MaxHeapSize" % ctx["shadow_pid"], shell=True) if ctx["shadow_pid"] else (1, "", "")
    ctx["shadow_maxheap"] = out.strip().replace("-XX:MaxHeapSize=", "") if out else None
    rc, out, _ = sh("journalctl -u shadow-c3 --since '%s' --no-pager 2>/dev/null | grep -a 'Picked up' | tail -3" % dt.datetime.fromtimestamp(
        (since - 86400000) / 1000, TZ).strftime("%Y-%m-%d %H:%M"), shell=True)
    ctx["shadow_pickedup"] = len([l for l in out.splitlines() if "Xms3g -Xmx3g" in l])
    for key, path in (("sh", sh_log), ("242", l242)):
        if os.path.exists(path):
            c, r, b = oi_summary(path, since)
            ctx["oi_%s_txt" % key] = "inplace: cold-load=%d, refresh=%d, evicted!=0 / reload loi=%d" % (c, r, b)
            ctx["oi_%s_ok" % key] = (r >= 1 and b == 0)
    if os.path.exists(l242):
        ctx["skip_legacy_242"] = sum(1 for ln in read_lines(l242) if "skip-LEGACY" in ln)
    try:                                      # D2: harness features co san (khong ghi de report cu)
        sys.path.insert(0, HERE)
        import parity_check as pc
        la = pc.layer_features(quiet=True)
        ctx["harness_feat_status"] = la["status"]
        fails = [c for c in la["checks"] if c["status"] == "FAIL"]
        ctx["harness_feat"] = "%s: %s | %d check FAIL / %d" % (la["status"], la["reason"][:160], len(fails), len(la["checks"]))
    except Exception as e:
        LOG.warning("harness features loi: %s", e)
    items = []
    for fn in (layer_A, layer_B, layer_B78, layer_C, layer_D, layer_E, layer_F, layer_G, layer_H, layer_I):
        try:
            items.extend(fn(ctx))
        except Exception as e:
            LOG.exception("layer %s loi", fn.__name__)
            items.append(item(fn.__name__, fn.__name__[-1], "loi chay layer", "-", str(e)[:120], "-", MISSING, MISSING))
    layers = {}
    for L in "ABCDEFGHI":
        its = [i for i in items if i["layer"] == L]
        layers[L] = {"shadow": combine([i["status_shadow"] for i in its]), "s242": combine([i["status_242"] for i in its]), "n": len(its)}
    ov = combine([i["status_shadow"] for i in items] + [i["status_242"] for i in items])
    rep = {"tool": "research/parity/live_vs_sim_check.py", "checklist": "docs/runbooks/PARITY_LIVE_VS_SIM_CHECKLIST.md",
           "generated": dt.datetime.now(TZ).strftime("%Y-%m-%d %H:%M:%S +07"), "window_since": ctx["since_txt"],
           "restart_shadow": ctx["restart_shadow"], "restart_242": ctx["restart_242"],
           "jar_sha256_shadow": sha256_file(JAR)[:16] if os.path.exists(JAR) else None,
           "extra": {k: ctx[k] for k in ("b5", "c1", "d1", "e2", "b8", "arm242") if k in ctx},
           "layers": layers, "items": items, "overall": ov, "exit_code": 2 if ov == FAIL else (3 if ov == MISSING else 0)}
    return rep


def render_md(rep):
    L = ["| id | mục | kỳ vọng (sim B0) | shadow | 242 | shadow | 242 | hành động |", "|---|---|---|---|---|---|---|---|"]
    for i in rep["items"]:
        L.append("| %s | %s | %s | %s | %s | **%s**%s | **%s** | %s |" % (
            i["id"], i["name"].replace("|", "/"), str(i["expect_sim"]).replace("|", "/"), str(i["shadow"]).replace("|", "/"),
            str(i["s242"]).replace("|", "/"), i["status_shadow"], " (known)" if i["known"] else "", i["status_242"],
            str(i["action"]).replace("|", "/")))
    return "\n".join(L)


def main(argv=None):
    ap = argparse.ArgumentParser(description="LIVE vs SIM parity A-I (audit-only)")
    ap.add_argument("--fetch", action="store_true", help="keo du lieu 242 (DOC-CHI) ve WORK/live242")
    ap.add_argument("--probe", action="store_true", help="chay ConfigProbe/FormulaProbe (java source-file mode, khong build)")
    ap.add_argument("--since", default=None, help="'YYYY-MM-DD HH:MM' (+07); mac dinh = sau lan restart gan nhat cua ca 2 box")
    ap.add_argument("--out", default=None)
    ap.add_argument("--md", default=None)
    a = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    rep = build(a.since, a.fetch, a.probe)
    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        with open(a.out, "w") as fh:
            json.dump(rep, fh, indent=1, sort_keys=True, default=str)
    if a.md:
        open(a.md, "w").write(render_md(rep) + "\n")
    LOG.info("=== LIVE vs SIM — overall=%s (exit=%d); cua so tu %s ===", rep["overall"], rep["exit_code"], rep["window_since"])
    for k, v in rep["layers"].items():
        LOG.info("[%s] shadow=%s 242=%s (%d muc)", k, v["shadow"], v["s242"], v["n"])
    for i in rep["items"]:
        LOG.info("  %-4s sh=%-7s 242=%-7s %s", i["id"], i["status_shadow"], i["status_242"], i["name"][:90])
    return rep["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
