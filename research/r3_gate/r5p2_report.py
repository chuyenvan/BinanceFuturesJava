#!/usr/bin/env python3
"""R5P2 bao cao bat buoc (prereg f2222d05 §5) cho 4 seed: hop le run, leg PREDICT theo nam, skipFull (log GATE-RATIO),
do tre vao lenh vs A0 (dot leg PREDICT A0 cach >60', leg dau arm trong [s-60', s+240']). Output r5p2_report.json."""
import json, logging, re, sys
import numpy as np, pandas as pd, requests
sys.path.insert(0, "/home/ubuntu/claude_master/res1109/r3_gate/orch")
sys.path.insert(0, "/home/ubuntu/claude_master/vz_e1_wt/research/analysis")
import r3_orch_q as Q
import gate_offline as GO
logging.basicConfig(level=logging.INFO)
OD = "/home/ubuntu/claude_master/res1109/r3_gate/"
SEEDS = ["a1", "s7", "s21", "s99"]
a = Q.KS._api()


def get(tag, slug, want):
    r = a.process_response(a.kernel_output_with_http_info(user_name="chuyendinh", kernel_slug=slug))
    out = {}
    for f in r["files"]:
        if f["fileName"] in want:
            out[f["fileName"]] = requests.get(f["url"], timeout=600).content
    return out, r.get("log") or ""


def gate_stats(full):
    m = re.findall(rb"GATE-RATIO (on|off) pct=\S+ days=\d+ seen=(\d+) pass=(\d+)[^\n]*?skipFull=(\d+)", full)
    if not m:
        return None
    on, seen, pas, sk = m[-1]
    return dict(seen=int(seen), pass_=int(pas), skipFull=int(sk))


def legs(pdb):
    d = pd.read_csv(pd.io.common.BytesIO(pdb), on_bad_lines="skip")
    d.columns = [c.strip() for c in d.columns]
    d = d[d["level"].astype(str).str.strip() == "PREDICT_SYMBOL_TRADE"].copy()
    d["s_ms"] = GO.to_ms(d["start"])
    d["yr"] = pd.to_datetime(d["s_ms"] + 7 * 3600000, unit="ms").dt.year
    return d


def lag(d0, d1):
    t0 = np.sort(d0[(d0.yr >= 2022) & (d0.yr <= 2025)].s_ms.unique()); t1 = np.sort(d1.s_ms.unique())
    st = np.r_[0, np.nonzero(np.diff(t0) > 60 * 60000)[0] + 1]
    hit, L = 0, []
    for i in st:
        s = t0[i]; k = np.searchsorted(t1, s - 60 * 60000)
        if k < len(t1) and t1[k] <= s + 240 * 60000:
            hit += 1; L.append((t1[k] - s) / 60000)
    return dict(eps_a0=int(len(st)), captured=round(hit / len(st), 3), lag_med=float(np.median(L)) if L else None,
                lag_p25=float(np.percentile(L, 25)) if L else None, lag_p75=float(np.percentile(L, 75)) if L else None)


R = {}
for sn in SEEDS:
    b0, _ = get("n4f-b0-" + sn, "sim-n4f-b0-" + sn, {"storage/printDone.csv", "logs/full.log"})
    d0 = legs(b0["storage/printDone.csv"]); g0 = gate_stats(b0.get("logs/full.log", b""))
    for arm in ("m1", "m0"):
        tag = "r3%s-%s" % (arm, sn)
        f, lg = get(tag, Q.kslug(tag), {"storage/printDone.csv", "logs/full.log", "result.json", "prof_run.properties"})
        rj = json.loads(f["result.json"]); prof = dict(l.split("=", 1) for l in f["prof_run.properties"].decode().splitlines() if "=" in l and not l.startswith("#"))
        d1 = legs(f["storage/printDone.csv"]); g1 = gate_stats(f["logs/full.log"])
        ascheck = re.search(r"AS_FILE_CHECK OK ([^\"\\\\]*)", lg)
        R[tag] = dict(ok=rj.get("ok"), jar=rj.get("jar_sha256") == Q.JAR_SHA,
                      ov_ok=all(prof.get(k) == str(v) for k, v in Q.ARMS[arm].items() if "GATE" in k),
                      as_check=ascheck.group(1) if ascheck else None,
                      legs_year={int(y): int((d1.yr == y).sum()) for y in range(2022, 2026)},
                      legs_year_a0={int(y): int((d0.yr == y).sum()) for y in range(2022, 2026)},
                      gate=g1, gate_a0=g0,
                      skipfull_share=round(g1["skipFull"] / max(g1["pass_"] + g1["skipFull"], 1), 4) if g1 else None,
                      skipfull_share_a0=round(g0["skipFull"] / max(g0["pass_"] + g0["skipFull"], 1), 4) if g0 else None,
                      lag=lag(d0, d1))
        logging.info("%s %s", tag, R[tag])
json.dump(R, open(OD + "r5p2_report.json", "w"), indent=1)
