#!/usr/bin/env python3
"""ECMEAS scorer (PREREG_ENTRYCOST_MEASURE 48ff35a5) - chi DO. 3 bien the x 2 cua so x 8 seed.
bucket = SIM_ENTRY_COST_MODE=bucket thuc (ec-s-s42 + ecm-d-s*, ecm-h-s*); goc = phi goc (gqsf-*, ho4-k24-b-*);
stress = SIM_CRASH_ENTRY_PENALTY 0.01675 (nsel-nen-s*, ho4-k24-s-*). Nen KHONG chay lai: chi doc printDone/sim.out co san.
SigmaPnL = Sum pnl dong printDone co end trong cua so (y score_A_defs HO4); n = dong co start trong cua so.
Equity MTM PHUT: (D) ecm_mtm_d.json (thuoc nsel_score_b / COVERAGE_M2, ticker sim 2022-25); (H) ecm_mtm_h.json
(ham ho4_score_a, gia Vision). MTM NGAY 07:00 (b+unP dong 'Update' sim.out) chi cho 2021H2 + so sanh phu.
Delta ghep cap: mean/sd/min/max + CI95 paired t (df k-1) qua seed.
Usage: python3 ecm_score.py [out_json] [out_md]
"""
import csv, hashlib, json, logging, re, statistics as S, sys

O = "/home/ubuntu/kaggle_sim/out/"
W = "/home/ubuntu/claude_master/1013/ecm"
SEEDS = [42, 7, 13, 21, 99, 123, 777, 2024]
CAP = 35000.0
TCRIT = {1: 12.7062, 2: 4.3027, 3: 3.1824, 4: 2.7764, 5: 2.5706, 6: 2.4469, 7: 2.3646}  # t 0,975
RX_UPD = re.compile(r"Update (\d{8} \d{2}:\d{2}) => b:\s*(-?\d+).*?unP:\s*(-?\d+)")
RX_SUM = re.compile(r"\[ENTRY-COST\] SUMMARY mode=(\w+) .*?legs=\[([^\]]*)\] usd=\[([^\]]*)\] legsTotal=(\d+) usdTotal=([0-9.]+)")
RX_YR = re.compile(r"\[ENTRY-COST\] YEAR (\d{4}) legs=\[([^\]]*)\] usd=\[([^\]]*)\]")
YEARS = ["2021", "2022", "2023", "2024", "2025"]
QS = {"Q1": ("20260101 00:00", "20260401 00:00"), "Q2": ("20260401 00:00", "20260701 00:00"),
      "Q3": ("20260701 00:00", "20261001 00:00")}
W9 = ("20260101 00:00", "20261001 00:00")
DFULL = ("20210701 00:00", "20260101 00:00")
D22 = ("20220101 00:00", "20260101 00:00")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout)
log = logging.getLogger("ecms")


def tags(win, var, s):
    if win == "D":
        return {"bucket": "ec-s-s42" if s == 42 else "ecm-d-s%d" % s,
                "goc": "gqsf-a1" if s == 42 else "gqsf-s%d" % s, "stress": "nsel-nen-s%d" % s}[var]
    return {"bucket": "ecm-h-s%d" % s, "goc": "ho4-k24-b-s%d" % s, "stress": "ho4-k24-s-s%d" % s}[var]


def md5f(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def load(tag):
    o = O + tag + "/"
    rows = []
    with open(o + "storage/printDone.csv", newline="") as f:
        for r in csv.DictReader(f):
            rows.append((r["start"].strip(), r["end"].strip(), float(r["pnl"])))
    rj = json.load(open(o + "result.json"))
    txt = open(o + "logs/sim.out", errors="ignore").read()
    upd = {}
    for m in RX_UPD.finditer(txt):
        upd[m.group(1)] = float(m.group(2)) + float(m.group(3))
    upd = sorted(upd.items())
    ec = {}
    m = None
    for m in RX_SUM.finditer(txt):
        pass
    if m:
        ec["mode"] = m.group(1)
        ec["legs"] = [int(x) for x in m.group(2).split(",")]
        ec["usd"] = [float(x) for x in m.group(3).split(",")]
        ec["legsTotal"], ec["usdTotal"] = int(m.group(4)), float(m.group(5))
        ec["year"] = {}
        for y in RX_YR.finditer(txt):
            ec["year"][y.group(1)] = {"legs": [int(x) for x in y.group(2).split(",")],
                                      "usd": [float(x) for x in y.group(3).split(",")]}
    return {"tag": tag, "rows": rows, "rj": rj, "upd": upd, "ec": ec, "md5": md5f(o + "storage/printDone.csv")}


def win(run, a, b):
    """n (start in [a,b)), spnl (end in [a,b)), E MTM ngay (Update trong [a,b)): E0, maxDD (dinh reset dau cua so)."""
    n = sum(1 for s, e, p in run["rows"] if a <= s < b)
    sp = sum(p for s, e, p in run["rows"] if a <= e < b)
    pts = [(k, v) for k, v in run["upd"] if a <= k < b]
    if not pts:
        return {"n": n, "spnl": sp, "E0": None, "maxdd": None, "npts": 0}
    peak, dd, kp, kt = pts[0][1], 0.0, pts[0][0], pts[0][0]
    cur_peak_k = pts[0][0]
    for k, v in pts:
        if v > peak:
            peak, cur_peak_k = v, k
        x = v / peak - 1.0
        if x < dd:
            dd, kp, kt = x, cur_peak_k, k
    return {"n": n, "spnl": sp, "E0": pts[0][1], "Elast": pts[-1][1], "maxdd": dd * 100.0, "dd_peak": kp, "dd_trough": kt,
            "npts": len(pts)}


def cagr(e1, e0, days):
    return ((e1 / e0) ** (365.25 / days) - 1.0) * 100.0


def metr_D(run, mt):
    """mt = ecm_mtm_d runs[tag] (MTM PHUT 2022-25, thuoc nsel_score_b). 2021H2: chi MTM ngay (khong co ticker 1m 2021)."""
    f = win(run, *DFULL)
    e_end = CAP + f["spnl"]
    m = {"n": f["n"], "spnl": f["spnl"], "roi35": f["spnl"] / CAP * 100.0, "cagr": cagr(e_end, CAP, 1645),
         "E_end": e_end, "cagr22": mt["cagr22"], "maxdd22": mt["maxdd22"], "calmar22": mt["calmar22"],
         "dd22_trough": mt["eq_dd_min_ts"], "maxdd_day_full": f["maxdd"], "dd_day_full_trough": f["dd_trough"],
         "maxdd22_day": win(run, *D22)["maxdd"]}
    m["year"] = {}
    for y in YEARS:
        a = ("%s0701 00:00" if y == "2021" else "%s0101 00:00") % y
        w = win(run, a, "%d0101 00:00" % (int(y) + 1))
        if y == "2021":
            m["year"][y] = {"n": w["n"], "spnl": w["spnl"], "maxdd": w["maxdd"], "roi": (w["Elast"] / CAP - 1) * 100,
                            "src": "MTM ngay 07:00"}
        else:
            yy = mt["year"][y]
            m["year"][y] = {"n": w["n"], "spnl": w["spnl"], "maxdd": yy["maxdd"], "roi": yy["roi"], "trough": yy["trough"],
                            "src": "MTM phut", "maxdd_day": w["maxdd"]}
    m["chk_eq"] = run["rj"].get("equity_final") - (CAP + sum(p for _, _, p in run["rows"]))
    m["mtm_chk"] = {k: mt[k] for k in ("eq_dev_pct", "logchk_med_abs_pct", "logchk_max_abs_pct", "sum_pnl", "n_rows", "n_result")}
    return m


def metr_H(run, mt):
    """mt = ecm_mtm_h runs[tag] (MTM PHUT, ham ho4_score_a, gia Vision)."""
    w = win(run, *W9)
    x = mt["W9"]
    m = {"n": x["n"], "spnl": x["sum_pnl"], "roi35": x["sum_pnl"] / CAP * 100.0, "roi": x["roi"], "E0": x["eq0"],
         "cagr_ann": x["cagr_ann"], "maxdd": x["maxdd"], "calmar": x["cagr_ann"] / abs(x["maxdd"]), "sharpe": x["sharpe"],
         "dd_peak": x["dd_peak"], "dd_trough": x["dd_trough"], "maxdd_day": w["maxdd"], "spnl_chk": w["spnl"], "n_chk": w["n"]}
    m["q"] = {q: {"n": mt[q]["n"], "spnl": mt[q]["sum_pnl"], "roi": mt[q]["roi"], "maxdd": mt[q]["maxdd"]} for q in QS}
    m["chk_eq"] = run["rj"].get("equity_final") - (CAP + sum(p for _, _, p in run["rows"]))
    m["eqcheck"] = mt["eqcheck"]
    return m


def st(xs):
    xs = [x for x in xs if x is not None]
    if not xs:
        return None
    return {"mean": S.mean(xs), "sd": S.stdev(xs) if len(xs) > 1 else 0.0, "min": min(xs), "max": max(xs), "k": len(xs),
            "pos": sum(1 for x in xs if x > 0)}


def f0(x, d=0):
    if x is None:
        return "—"
    s = ("{:,.%df}" % d).format(x).replace(",", " ")
    return s.replace(".", ",")


def ms(d, k=0):
    return "%s ± %s [%s..%s]" % (f0(d["mean"], k), f0(d["sd"], k), f0(d["min"], k), f0(d["max"], k))


def main():
    import subprocess
    out_json = sys.argv[1] if len(sys.argv) > 1 else W + "/ecm_score.json"
    out_md = sys.argv[2] if len(sys.argv) > 2 else W + "/ecm_score.md"
    ho4a = json.loads(subprocess.run(["git", "-C", "/home/ubuntu/src/BinanceFuturesJava", "show",
                                      "module:docs/result/ho4/HO4_RESULT_A.json"], capture_output=True, text=True).stdout)
    nsb = {r["tag"]: r for r in json.load(open("/home/ubuntu/src/BinanceFuturesJava/docs/result/NSEL_RESULT_B.json"))["rows"]}
    MT = {"D": json.load(open(W + "/ecm_mtm_d.json")), "H": json.load(open(W + "/ecm_mtm_h.json"))}
    R = {"D": {}, "H": {}}
    runs = {}
    val = []
    for k, x in MT["D"]["checks"].items():
        log.info("MTM D check %s=%s", k, x)
    val.append(("mtm_d", "miss_frac phut-chan thieu gia < 1%", MT["D"]["checks"]["miss_frac"] < 0.01))
    val.append(("mtm_h", "Vision fetch fail == 0 va miss == 0", MT["H"]["mtm_check"]["fetch"]["fail"] == 0
                and MT["H"]["mtm_check"]["miss"] == 0))
    for wn in ("D", "H"):
        for v in ("bucket", "goc", "stress"):
            R[wn][v] = {}
            for s in SEEDS:
                t = tags(wn, v, s)
                try:
                    run = load(t)
                except Exception as e:  # noqa: BLE001
                    log.warning("thieu %s: %s", t, str(e)[:80])
                    continue
                runs[t] = run
                if t not in MT[wn]["runs"]:
                    log.warning("thieu MTM %s", t)
                    continue
                m = metr_D(run, MT[wn]["runs"][t]) if wn == "D" else metr_H(run, MT[wn]["runs"][t])
                if wn == "D":
                    mc = m["mtm_chk"]
                    val.append((t, "MTM: |E cuoi phut - equity_final| <= 0,01%", abs(mc["eq_dev_pct"]) <= 0.01))
                    val.append((t, "MTM: Σpnl cua so 2022-25 khop / n_rows==n_result", mc["n_rows"] == mc["n_result"]))
                    if t in nsb:
                        val.append((t, "cagr22/maxdd22/calmar22 == NSEL_RESULT_B (thuoc + ticker trung)",
                                    all(abs(nsb[t][k] - m[k]) < 1e-6 for k in ("cagr22", "maxdd22", "calmar22"))))
                else:
                    val.append((t, "MTM: E phut cuoi vs equity_final <= 0,01% (eqcheck)", m["eqcheck"]["final_dev_pct"] is not None
                                and abs(float(m["eqcheck"]["final_dev_pct"])) <= 0.01))
                    val.append((t, "Σpnl/n W9 MTM == printDone truc tiep", abs(m["spnl"] - m["spnl_chk"]) < 0.01 and m["n"] == m["n_chk"]))
                m.update(tag=t, md5=run["md5"], n_rows=len(run["rows"]), n_trades=run["rj"].get("n_trades"),
                         jar=(run["rj"].get("jar_sha256") or "")[:8], ec=run["ec"], npts=len(run["upd"]))
                R[wn][v][s] = m
                val.append((t, "n_rows==n_trades", m["n_rows"] == m["n_trades"]))
                if wn == "D":
                    val.append((t, "|eq_final-(35000+Σpnl)|<=1", abs(m["chk_eq"]) <= 1.0))
                if v == "bucket":
                    val.append((t, "SUMMARY mode=bucket", run["ec"].get("mode") == "bucket"))
                    val.append((t, "legsTotal==n_rows", run["ec"].get("legsTotal") == m["n_rows"]))
                    kp = "/home/ubuntu/claude_master/1012/ecost/ec_S_result.json" if t == "ec-s-s42" else W + "/res/%s.json" % t
                    kr = json.load(open(kp))
                    m["kchk"] = {"src": kp, "chk": kr["chk"], "md5": kr["md5_printDone"], "jar": kr["jar_sha"]}
                    val.append((t, "kernel 12/12 check sim true", len(kr["chk"]) == 12 and all(x is True for x in kr["chk"].values())))
                    val.append((t, "jar sha 246087fb", kr["jar_sha"].startswith("246087fb") and run["rj"]["jar_sha256"] == kr["jar_sha"]))
                    val.append((t, "md5 kernel-check == md5 scorer", kr["md5_printDone"] == run["md5"]))
                    if t == "ec-s-s42":
                        val.append((t, "seed42 D tai lap n=3529 md5 d1d804be", m["n_rows"] == 3529 and run["md5"].startswith("d1d804be")))
                else:
                    val.append((t, "khong co log ENTRY-COST SUMMARY", not run["ec"]))
                if wn == "H" and v != "bucket":
                    fee = "b" if v == "goc" else "s"
                    for wk, mm in (("W9", m), ("Q3", m["q"]["Q3"])):
                        ref = ho4a["metrics"]["k24|%s|%d|%s" % (fee, s, wk)]
                        val.append((t, "%s Σpnl/n/roi/maxDD phut == HO4_RESULT_A" % wk,
                                    abs(ref["sum_pnl"] - mm["spnl"]) < 0.01 and ref["n"] == mm["n"]
                                    and abs(ref["roi"] - mm["roi"]) < 1e-6 and abs(ref["maxdd"] - mm["maxdd"]) < 1e-6))
    return R, runs, val, ho4a, out_json, out_md


VN = {"bucket": "bucket thực", "goc": "phí gốc", "stress": "stress 1,675%"}
BK = ["NC", "C1", "C2", "C4"]


def col(R, wn, v, key, sub=None):
    out = []
    for s in SEEDS:
        m = R[wn][v].get(s)
        if m is None:
            out.append(None)
            continue
        x = m
        for k in ([sub] if isinstance(sub, str) else (sub or [])):
            x = x[k]
        out.append(x[key] if x is not None else None)
    return out


def paired(R, wn, key, ref, sub=None):
    a, b = col(R, wn, "bucket", key, sub), col(R, wn, ref, key, sub)
    d = [x - y for x, y in zip(a, b) if x is not None and y is not None]
    if not d:
        return None
    r = st(d)
    if r["k"] > 1:
        h = TCRIT[r["k"] - 1] * r["sd"] / r["k"] ** 0.5
        r["ci95"] = [r["mean"] - h, r["mean"] + h]
    return r


def ci(p, d=0):
    return "" if not p or "ci95" not in p else " · CI95 [%s; %s]" % (f0(p["ci95"][0], d), f0(p["ci95"][1], d))


def report(R, runs, val, ho4a):
    L = []
    agg = {"D": {}, "H": {}}
    spec = {"D": [("n", "n chân (2021-07→2025)", 0), ("spnl", "ΣPnL USD (2021-07→2025)", 0), ("roi35", "ROI/35k %", 1),
                  ("cagr", "CAGR 2021-07→2025 % (realized, 4,50 năm)", 2), ("cagr22", "CAGR 2022–25 % (MTM phút)", 2),
                  ("maxdd22", "maxDD MTM phút 2022–25 %", 2), ("calmar22", "Calmar MTM 2022–25", 3),
                  ("maxdd_day_full", "maxDD MTM ngày 07:00 2021-07→2025 % (phụ)", 2)],
            "H": [("n", "n chân (start∈W9)", 0), ("spnl", "ΣPnL W9 USD", 0), ("roi35", "ROI/35k %", 1),
                  ("roi", "ROI MTM E1/E0 %", 2), ("cagr_ann", "CAGR năm hoá %", 2), ("maxdd", "maxDD MTM phút %", 2),
                  ("calmar", "Calmar MTM (CAGR năm hoá/|maxDD|)", 3), ("sharpe", "Sharpe ngày", 2)]}
    for wn in ("D", "H"):
        L.append("\n### %s — mean ± sd [min..max] qua seed\n" % ("(D) DEV 2021-07-01 → 2025-12-31" if wn == "D" else "(H) HO4 W9 2026-01-01 → 10-01"))
        L.append("| chỉ số | " + " | ".join(VN[v] for v in ("bucket", "goc", "stress")) + " |")
        L.append("|---|---|---|---|")
        for key, lab, d in spec[wn]:
            cells = []
            for v in ("bucket", "goc", "stress"):
                xs = [x for x in col(R, wn, v, key) if x is not None]
                if xs:
                    agg[wn].setdefault(v, {})[key] = st(xs)
                    cells.append(ms(agg[wn][v][key], d) + ("" if len(xs) == 8 else " (k=%d)" % len(xs)))
                else:
                    cells.append("—")
            L.append("| %s | %s |" % (lab, " | ".join(cells)))
        L.append("\n**Δ ghép cặp seed (bucket − nền)**: mean ± sd [min..max], số seed Δ>0, CI95 paired t (df k−1)\n")
        L.append("| chỉ số | bucket − phí gốc | bucket − stress |")
        L.append("|---|---|---|")
        for key, lab, d in spec[wn]:
            cells = []
            for ref in ("goc", "stress"):
                p = paired(R, wn, key, ref)
                agg[wn].setdefault("d_" + ref, {})[key] = p
                cells.append("—" if p is None else ms(p, d) + " · %d/%d" % (p["pos"], p["k"]) + ci(p, d))
            L.append("| %s | %s |" % (lab, " | ".join(cells)))
    return L, agg


def report2(R, runs, val, agg):
    L = []
    L.append("\n### (D) theo năm — mean qua seed (ΣPnL theo end, n theo start; ROI/maxDD = MTM phút, đỉnh reset đầu năm; 2021 = 07-01→12-31, MTM NGÀY 07:00 vì không có ticker 1m 2021)\n")
    L.append("| năm | ΣPnL bucket | ΣPnL gốc | ΣPnL stress | Δ b−gốc (seed>0) | Δ b−stress (seed>0) | n b/gốc/stress | ROI MTM b/gốc/stress % | maxDD b/gốc/stress % | chân bucket NC/C1/C2/C4 | USD bucket NC/C1/C2/C4 (Σ) |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|")
    agg["D"]["year"] = {}
    for y in YEARS:
        r = {}
        for v in ("bucket", "goc", "stress"):
            r[v] = {k: st([x for x in col(R, "D", v, k, ["year", y]) if x is not None]) for k in ("spnl", "n", "maxdd", "roi")}
        dg, dsx = paired(R, "D", "spnl", "goc", ["year", y]), paired(R, "D", "spnl", "stress", ["year", y])
        legs = [S.mean([R["D"]["bucket"][s]["ec"]["year"][y]["legs"][i] for s in R["D"]["bucket"]]) for i in range(4)]
        usd = [S.mean([R["D"]["bucket"][s]["ec"]["year"][y]["usd"][i] for s in R["D"]["bucket"]]) for i in range(4)]
        agg["D"]["year"][y] = {"var": r, "d_goc": dg, "d_stress": dsx, "legs_mean": legs, "usd_mean": usd}
        L.append("| %s | %s | %s | %s | %s (%d/%d) | %s (%d/%d) | %s/%s/%s | %s/%s/%s | %s/%s/%s | %s | %s (%s) |" % (
            y, f0(r["bucket"]["spnl"]["mean"]), f0(r["goc"]["spnl"]["mean"]), f0(r["stress"]["spnl"]["mean"]),
            f0(dg["mean"]) + ci(dg), dg["pos"], dg["k"], f0(dsx["mean"]) + ci(dsx), dsx["pos"], dsx["k"],
            f0(r["bucket"]["n"]["mean"]), f0(r["goc"]["n"]["mean"]), f0(r["stress"]["n"]["mean"]),
            f0(r["bucket"]["roi"]["mean"], 1), f0(r["goc"]["roi"]["mean"], 1), f0(r["stress"]["roi"]["mean"], 1),
            f0(r["bucket"]["maxdd"]["mean"], 2), f0(r["goc"]["maxdd"]["mean"], 2), f0(r["stress"]["maxdd"]["mean"], 2),
            "/".join(f0(x) for x in legs), "/".join(f0(x) for x in usd), f0(sum(usd))))
    L.append("\n### (H) theo quý 2026 — mean qua seed (ΣPnL theo end, n theo start; ROI/maxDD MTM phút Vision, đỉnh reset đầu quý)\n")
    L.append("| quý | ΣPnL bucket [min..max] | ΣPnL gốc | ΣPnL stress | Δ b−gốc (seed>0) | Δ b−stress (seed>0) | seed bucket>0 | n b/gốc/stress | ROI MTM b/gốc/stress % | maxDD b/gốc/stress % |")
    L.append("|---|---|---|---|---|---|---|---|---|---|")
    agg["H"]["q"] = {}
    for q in (QS if R["H"]["bucket"] else []):
        r = {v: {k: st([x for x in col(R, "H", v, k, ["q", q]) if x is not None]) for k in ("spnl", "n", "maxdd", "roi")}
             for v in ("bucket", "goc", "stress")}
        dg, dsx = paired(R, "H", "spnl", "goc", ["q", q]), paired(R, "H", "spnl", "stress", ["q", q])
        agg["H"]["q"][q] = {"var": r, "d_goc": dg, "d_stress": dsx}
        L.append("| %s | %s [%s..%s] | %s | %s | %s (%d/%d) | %s (%d/%d) | %d/%d | %s/%s/%s | %s/%s/%s | %s/%s/%s |" % (
            q, f0(r["bucket"]["spnl"]["mean"]), f0(r["bucket"]["spnl"]["min"]), f0(r["bucket"]["spnl"]["max"]),
            f0(r["goc"]["spnl"]["mean"]), f0(r["stress"]["spnl"]["mean"]), f0(dg["mean"]) + ci(dg), dg["pos"], dg["k"],
            f0(dsx["mean"]) + ci(dsx), dsx["pos"], dsx["k"], r["bucket"]["spnl"]["pos"], r["bucket"]["spnl"]["k"],
            f0(r["bucket"]["n"]["mean"]), f0(r["goc"]["n"]["mean"]), f0(r["stress"]["n"]["mean"]),
            f0(r["bucket"]["roi"]["mean"], 2), f0(r["goc"]["roi"]["mean"], 2), f0(r["stress"]["roi"]["mean"], 2),
            f0(r["bucket"]["maxdd"]["mean"], 2), f0(r["goc"]["maxdd"]["mean"], 2), f0(r["stress"]["maxdd"]["mean"], 2)))
    return L


def report3(R, runs, val, agg):
    L = []
    L.append("\n### Chân + chi phí vào USD theo bucket (bản bucket; mean ± sd qua seed)\n")
    L.append("| cửa sổ | nguồn log | " + " | ".join("chân %s" % b for b in BK) + " | " + " | ".join("USD %s" % b for b in BK) + " | Σ USD | USD/chân |")
    L.append("|---|---|" + "---|" * 10)
    agg["bk"] = {}
    for wn, src in (("D", "SUMMARY (2021-07→2025-12)"), ("H", "YEAR 2026 (entry 2026-01→09)")):
        rs = list(R[wn]["bucket"].values())
        if not rs:
            continue
        g = (lambda m: m["ec"]) if wn == "D" else (lambda m: m["ec"]["year"]["2026"])
        legs = [st([g(m)["legs"][i] for m in rs]) for i in range(4)]
        usd = [st([g(m)["usd"][i] for m in rs]) for i in range(4)]
        tot = st([sum(g(m)["usd"]) for m in rs])
        per = st([sum(g(m)["usd"]) / sum(g(m)["legs"]) for m in rs])
        agg["bk"][wn] = {"legs": legs, "usd": usd, "usd_total": tot, "usd_per_leg": per, "src": src}
        L.append("| %s | %s | %s | %s | %s | %s |" % (wn, src, " | ".join(ms(x) for x in legs), " | ".join(ms(x) for x in usd),
                                                      ms(tot), ms(per, 2)))
    hb = [R["H"]["bucket"][s]["spnl"] for s in SEEDS if s in R["H"]["bucket"]]
    if hb:
        e0 = {"mean_spnl": S.mean(hb), "pos": sum(1 for x in hb if x > 0), "k": len(hb),
              "pass": S.mean(hb) > 0 and sum(1 for x in hb if x > 0) >= 6}
        agg["E0_H"] = e0
        L.append("\n**E0 trên H (bucket, báo, không quyết)**: mean ΣPnL W9 = %s; seed > 0 = %d/%d ⇒ %s.\n" % (
            f0(e0["mean_spnl"]), e0["pos"], e0["k"], "ĐẠT" if e0["pass"] else "KHÔNG ĐẠT"))
    L.append("\n### Từng run\n")
    L.append("| cửa sổ | biến thể | seed | tag | md5 printDone | n | ΣPnL | maxDD MTM phút % (D: 2022–25) | Calmar MTM | jar |")
    L.append("|---|---|---|---|---|---|---|---|---|---|")
    for wn in ("D", "H"):
        for v in ("bucket", "goc", "stress"):
            for s in SEEDS:
                m = R[wn][v].get(s)
                if m:
                    dd, ca = (m["maxdd22"], m["calmar22"]) if wn == "D" else (m["maxdd"], m["calmar"])
                    L.append("| %s | %s | %d | `%s` | `%s` | %d | %s | %s | %s | %s |" % (
                        wn, VN[v], s, m["tag"], m["md5"][:8], m["n"], f0(m["spnl"]), f0(dd, 2), f0(ca, 3), m["jar"]))
    bad = [x for x in val if not x[2]]
    L.append("\n### Tự kiểm scorer: %d/%d đạt%s\n" % (len(val) - len(bad), len(val), "" if not bad else " — LỖI: " + "; ".join("%s %s" % (a, b) for a, b, _ in bad)))
    return L


if __name__ == "__main__":
    R, runs, val, ho4a, oj, om = main()
    L, agg = report(R, runs, val, ho4a)
    L += report2(R, runs, val, agg)
    L += report3(R, runs, val, agg)
    hm = [R["H"][v][s]["maxdd"] - R["H"][v][s]["maxdd_day"] for v in R["H"] for s in SEEDS if s in R["H"][v]]
    dm = [R["D"][v][s]["maxdd22"] - R["D"][v][s]["maxdd22_day"] for v in R["D"] for s in SEEDS if s in R["D"][v]]
    agg["mtm_gap"] = {"H": st(hm), "D22": st(dm)}
    L.append("Phụ: maxDD MTM phút − maxDD MTM ngày 07:00 (cùng run, cùng cửa sổ): H W9 %s pp; D 2022–25 %s pp — "
             "MTM ngày đánh giá THẤP DD, chỉ dùng cho 2021H2.\n" % (ms(agg["mtm_gap"]["H"], 2), ms(agg["mtm_gap"]["D22"], 2)))
    strip = {wn: {v: {str(s): {k: x for k, x in m.items() if k != "ec"} | {"ec": m["ec"]} for s, m in R[wn][v].items()}
                  for v in R[wn]} for wn in R}
    json.dump({"prereg": "docs/prereg/PREREG_ENTRYCOST_MEASURE.md@48ff35a5", "runs": strip, "agg": agg,
               "validation": [{"tag": a, "check": b, "ok": c} for a, b, c in val]}, open(oj, "w"), indent=1, default=str)
    open(om, "w").write("\n".join(L) + "\n")
    log.info("WROTE %s %s md5 %s ; val %d/%d", oj, om, md5f(oj), sum(1 for x in val if x[2]), len(val))
