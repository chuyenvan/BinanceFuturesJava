#!/usr/bin/env python3
"""Cham MTM ghep cap arm vs B0 (n4f-b0-*): CAGR_DEV (2022-01-01..2026-01-01 +07, tu equity MTM cuoi ngay +07),
maxDD MTM DEV (dd_dev phut tu mtm_result), Calmar = CAGR/|DD|; win tuy chon (R3b: 2023..2026). Futility: >=2/4 seed dCalmar<=0 => DUNG.
Usage: r3_score.py <arm_prefix vd r3g3> <out.json> [win_start YYYY-MM-DD] [win_end]"""
import glob, json, logging, sys
import numpy as np, pandas as pd
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("r3score")
SEEDN = {"a1": 42, "s7": 7, "s13": 13, "s21": 21, "s99": 99, "s123": 123, "s777": 777, "s2024": 2024}
arm, out = sys.argv[1], sys.argv[2]
w0, w1 = (sys.argv[3], sys.argv[4]) if len(sys.argv) > 4 else ("2022-01-01", "2026-01-01")
RES = ["/home/ubuntu/claude_master/nup4_fix/results", "/home/ubuntu/claude_master/res1109/r3_gate/results"]
DAY0 = pd.Timestamp(__import__("re").search(r'DAY0 = pd.Timestamp\("([^"]+)"\)', open("/home/ubuntu/claude_master/res1109/r3_gate/orch/mtm_kernel.py").read()).group(1))
R, D = {}, {}
for p in sorted(glob.glob(RES[0] + "/n4f-mtm-b*/mtm_result.json")) + sorted(glob.glob(RES[1] + "/r3*-mtm-*/mtm_result.json")):
    r = json.load(open(p)); d = json.load(open(p.replace("mtm_result.json", "mtm_eq_daily_close07.json")))
    assert r["ok"], p
    for k, v in r["runs"].items():
        R.setdefault(k, v); D.setdefault(k, d[k])
dates = [(DAY0 + pd.Timedelta(days=i)).strftime("%Y-%m-%d") for i in range(max(len(v) for v in D.values()))]


def metr(tag):
    eq = np.array(D[tag]); r = R[tag]
    i0, i1 = dates.index(w0) - 1, dates.index(w1) - 1          # cuoi ngay truoc w0 .. cuoi ngay truoc w1
    yrs = (pd.Timestamp(w1) - pd.Timestamp(w0)).days / 365.25
    cagr = ((eq[i1] / eq[i0]) ** (1 / yrs) - 1) * 100
    seg = eq[i0:i1 + 1]
    dd_d = float((seg / np.maximum.accumulate(seg) - 1).min() * 100)
    dd = r["dd_dev"] if (w0, w1) == ("2022-01-01", "2026-01-01") else dd_d
    yr = {}
    for y in range(int(w0[:4]), int(w1[:4])):
        a, b = dates.index("%d-01-01" % y) - 1, dates.index("%d-01-01" % (y + 1)) - 1
        yr[y] = round(float(eq[b] - eq[a]), 1)
    return dict(cagr=round(cagr, 3), dd=round(dd, 3), dd_daily=round(dd_d, 3), calmar=round(cagr / abs(dd), 4), n_legs=r["n_legs"],
                missing=r["missing"], pnl_year=yr, ho_pnl=round(float(eq[-1] - eq[dates.index("2026-01-01") - 1]), 1))


rows = {}
for sn, s in SEEDN.items():
    t = "%s-%s" % (arm, sn)
    if t not in R:
        continue
    a, b = metr(t), metr("n4f-b0-" + sn)
    rows[sn] = dict(arm=a, b0=b, d_calmar=round(a["calmar"] - b["calmar"], 4), d_cagr=round(a["cagr"] - b["cagr"], 3),
                    d_dd=round(a["dd"] - b["dd"], 3), d_ho_pnl=round(a["ho_pnl"] - b["ho_pnl"], 1),
                    d_year={y: round(a["pnl_year"][y] - b["pnl_year"][y], 1) for y in a["pnl_year"]})
first4 = [s for s in ("a1", "s7", "s21", "s99") if s in rows]
nonpos = sum(1 for s in first4 if rows[s]["d_calmar"] <= 0)
res = dict(arm=arm, window=[w0, w1], seeds=rows, futility=dict(seeds=first4, n_dcalmar_le0=nonpos,
           STOP=bool(len(first4) == 4 and nonpos >= 2)))
json.dump(res, open(out, "w"), indent=1)
for s, v in rows.items():
    log.info("%s dCalmar %+.4f dCAGR %+.3f dDD %+.3f legs %d vs %d", s, v["d_calmar"], v["d_cagr"], v["d_dd"], v["arm"]["n_legs"], v["b0"]["n_legs"])
log.info("FUTILITY %s", res["futility"])
