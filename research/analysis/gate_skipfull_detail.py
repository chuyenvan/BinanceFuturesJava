#!/usr/bin/env python3
"""GATE_SKIPFULL_DETAIL (2026-10-05): bang NAM/QUY C0..C5 cho GATE_QUOTA_SKIP_WHEN_FULL vs baseline.

CHI tinh tu output Kaggle CO SAN (~/kaggle_sim/out): 0 sim, 0 Java, 0 tune. Dinh nghia = gate_skipfull_driver /
n700_driver / reset_rule_score (phi legacy as-is, MTM phut tu ticker 1m). Tu kiem: tong 2022-25 + so theo nam phai
khop docs/result/gate_skipfull.json (+ cache MTM cu) TRUOC khi xuat bang; lech => dung.
Usage: python3 research/analysis/gate_skipfull_detail.py [--workers 3]
"""
import argparse
import json
import logging
import os
import re
import sys

import numpy as np
import pandas as pd

REPO = "/home/ubuntu/src/BinanceFuturesJava"
sys.path.insert(0, REPO)
sys.path.insert(0, REPO + "/research/analysis")
import reset_rule_score as R  # noqa: E402
import feat_add_v1_score as F  # noqa: E402,F401  (side effect: MTMStateW -> dd_win/uw_win_days cua so 2022+)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("gsd")
R.MTM_COSTS = {"legacy": R.LEGACY}

OUT = "/home/ubuntu/kaggle_sim/out/%s/"
W0 = pd.Timestamp("2021-12-31")
LO, HI, END = pd.Timestamp("2022-01-01"), pd.Timestamp("2025-12-31"), pd.Timestamp("2026-01-01")
YEARS = ["2022", "2023", "2024", "2025"]
QS = ["%sQ%d" % (y, q) for y in YEARS for q in (1, 2, 3, 4)]
MONTHS = ["2022-%02d" % m for m in range(5, 10)]
SEEDS = ["A1", "S7", "S13", "S21", "S99", "S123", "S777", "S2024"]
OFF = {"A1": "n700-a1", "S7": "gabl-seed7", **{s: "gsb-" + s.lower() for s in SEEDS[2:]}}
ON = {s: "gqsf-" + s.lower() for s in SEEDS}
C0, C5 = "gqsf-p0", "gqsf16-a1"
CFG = {"C0": [C0], "C1": [OFF["A1"]], "C2": [ON["A1"]], "C3": [OFF[s] for s in SEEDS], "C4": [ON[s] for s in SEEDS]}
CN = list(CFG)
MD5_ONLY = ["n700-b0ref", "de-p1", C5]
D = "/home/ubuntu/claude_master/1005/gsd"
MTM_CACHE = D + "/mtm_detail.json"
REF = REPO + "/docs/result/gate_skipfull.json"
OLD_MTM = ["/home/ubuntu/claude_master/1004/gqsf/mtm.json", "/home/ubuntu/claude_master/1004/gqsf/mtm_k16.json",
           "/home/ubuntu/claude_master/1004/gsb/mtm.json"]
JSON_OUT = REPO + "/docs/result/gate_skipfull_detail.json"
CSV_OUT = REPO + "/docs/result/gate_skipfull_detail_equity.csv"
MD_OUT = D + "/tables.md"


class MTMStateD(R.MTMState):
    """+ state theo QUY (dinh reset dau quy, cung cach dd_year) + MTM cuoi ngay / min ngay (ngay UTC)."""

    def __init__(self):
        super().__init__()
        self.pq, self.dclose, self.dmin = {}, {}, {}

    def feed(self, m_global, eq):
        super().feed(m_global, eq)
        day = (pd.Timestamp(R.DAY0) + pd.Timedelta(minutes=int(m_global))).normalize()
        v = np.asarray(eq["legacy"], float)
        k = "%dQ%d" % (day.year, (day.month - 1) // 3 + 1)
        if k not in self.pq:
            self.pq[k] = [float(v[0]), 0.0, 0, 0]
        MTMStateD._consume(v, self.pq[k])
        ds = day.strftime("%Y-%m-%d")
        self.dclose[ds], self.dmin[ds] = float(v[-1]), float(v.min())


_prev_res = R._mtm_result


def _res_d(st):
    out = _prev_res(st)
    out["legacy"].update(dd_q={k: float(v[1]) for k, v in st.pq.items()},
                         uw_q={k: float(v[3]) / 1440.0 for k, v in st.pq.items()}, dclose=st.dclose, dmin=st.dmin)
    return out


R.MTMState, R._mtm_result = MTMStateD, _res_d


def bounds(p):
    if len(p) == 4:
        s = pd.Timestamp(p + "-01-01")
        return s, s + pd.DateOffset(years=1)
    if "Q" in p:
        s = pd.Timestamp(int(p[:4]), 3 * (int(p[5]) - 1) + 1, 1)
        return s, s + pd.DateOffset(months=3)
    s = pd.Timestamp(p + "-01")
    return s, s + pd.DateOffset(months=1)


def gate_log(tag):
    """dong [GATE-RATIO] cuoi: pass theo quy + skipFull (tong; Java chi log tong)."""
    line = ""
    for fn in ("logs/full.log", "logs/sim.out"):
        p = OUT % tag + fn
        if os.path.exists(p):
            with open(p, errors="ignore") as f:
                for ln in f:
                    if "[GATE-RATIO] GATE-RATIO on" in ln:
                        line = ln
    q = {a: int(b) for a, b in re.findall(r"(\d{4}Q\d):(\d+)/\d+", line)}
    sk = re.findall(r"skipFull=(\d+)", line)
    return q, (int(sk[-1]) if sk else None)


def entry_minutes(tag):
    """= gate_ablation_driver.gate_minutes: phut start duy nhat cua leg PREDICT_SYMBOL_TRADE."""
    d = pd.read_csv(OUT % tag + "storage/printDone.csv", on_bad_lines="skip")
    d.columns = [c.strip() for c in d.columns]
    d = d[d["level"].astype(str).str.strip() == "PREDICT_SYMBOL_TRADE"]
    t = pd.to_datetime(d["start"], format="%Y%m%d %H:%M", errors="coerce").dropna()
    return t.drop_duplicates()


def open_grid(legs):
    """= n700_driver.conc_exposure(t0=2022-01-01): so lenh mo dong thoi tren luoi PHUT (gio local)."""
    lo = max(LO, legs["ts"].min().floor("min"))
    hi = min(legs["te"].max().ceil("min"), HI)
    T = int((hi - lo) / pd.Timedelta(minutes=1)) + 1
    a = np.clip(((legs["ts"] - lo) // pd.Timedelta(minutes=1)).to_numpy().astype(np.int64), 0, T)
    b = np.clip(((legs["te"] - lo) // pd.Timedelta(minutes=1)).to_numpy().astype(np.int64), 0, T)
    cnt = np.zeros(T + 1)
    np.add.at(cnt, a, 1)
    np.add.at(cnt, b, -1)
    return np.cumsum(cnt)[:T], lo, T


def closed(g):
    """lenh DONG trong ky (theo te): n, SigmaPnL, win, SL (STOP_LOSS_DONE), meanP (profit %), PnL lenh 0h (time_order<=0)."""
    n, tot = len(g), float(g["pnl"].sum())
    h = g[g["time_order"] <= 0]
    return dict(n=int(n), pnl=tot, win=float(100 * (g["profit"] > 0).mean()) if n else None,
                sl=float(100 * (g["status"].astype(str) == "STOP_LOSS_DONE").mean()) if n else None,
                meanP=float(g["profit"].mean()) if n else None, pnl0=float(h["pnl"].sum()),
                share0=float(100 * h["pnl"].sum() / tot) if n and tot != 0 else None)


def tag_metrics(tag, legs, daily, L):
    e = daily["equity"].astype(float).copy()
    e.index = pd.to_datetime(e.index)
    em = entry_minutes(tag)
    c, lo, T = open_grid(legs)
    gq, skip = gate_log(tag)
    per = {}
    for p in YEARS + QS + MONTHS:
        s, x = bounds(p)
        r = closed(legs[(legs["te"] >= s) & (legs["te"] < x)])
        e0, e1 = float(e[e.index < s].iloc[-1]), float(e[e.index < x].iloc[-1])
        r.update(eq0=e0, eq1=e1, roi=100 * (e1 / e0 - 1), gmin=int(((em >= s) & (em < x)).sum()))
        i0 = int(np.clip((s - lo) // pd.Timedelta(minutes=1), 0, T))
        i1 = int(np.clip((x - lo) // pd.Timedelta(minutes=1), 0, T))
        cc = c[i0:i1]
        r.update(op95=float(np.percentile(cc, 95)) if len(cc) else None, opmax=int(cc.max()) if len(cc) else None)
        if len(p) == 4:
            r.update(dd=L["dd_year"].get(p), uw=L["uw_year"].get(p),
                     gpass=sum(gq.get(q, 0) for q in QS if q[:4] == p) if gq else None)
        elif "Q" in p:
            r.update(dd=L["dd_q"].get(p), uw=L["uw_q"].get(p), gpass=gq.get(p))
        else:
            r.update(dd=None, uw=None, gpass=None)
        per[p] = r
    d22 = daily.loc[W0:]
    q = d22["equity"].astype(float)
    yrs = (d22.index[-1] - d22.index[0]).days / 365.25
    cagr22 = float(100 * ((q.iloc[-1] / q.iloc[0]) ** (1 / yrs) - 1))
    cl = legs[(legs["te"] >= LO) & (legs["te"] < END)]
    tot = closed(cl)
    tot.update(cagr22=cagr22, dd22=L["dd_win"], uw22=L["uw_win_days"], calmar22=cagr22 / abs(L["dd_win"]),
               dd_all=L["dd_total"], n_per_year=len(cl) / 4.0, eq_final=float(daily["equity"].iloc[-1]),
               op95=float(np.percentile(c, 95)), opmax=int(c.max()),
               gmin_per_year=int(((em >= LO) & (em < END)).sum()) / 4.0, skipFull=skip, n_all=int(len(legs)),
               gpass_total=sum(gq.get(k, 0) for k in QS) if gq else None)
    return dict(tag=tag, per=per, tot=tot)


def validate(TM, ref):
    """so lai voi gate_skipfull.json (K24: metrics; C0: k16.metrics.OFF_A1) + dd/uw nam voi cache MTM cu (cung md5)."""
    rm = {OFF[s]: ref["metrics"]["OFF_" + s] for s in SEEDS}
    rm.update({ON[s]: ref["metrics"]["ON_" + s] for s in SEEDS})
    rm[C0] = ref["k16"]["metrics"]["OFF_A1"]
    old = {}
    for p in OLD_MTM:
        for v in json.load(open(p)).values():
            old[v.get("md5")] = v["legacy"]
    bad, cnt = [], [0]

    def chk(tag, name, a, b, tol=1e-6):
        cnt[0] += 1
        if a is None or b is None or not np.isfinite(float(a)) or abs(float(a) - float(b)) > tol * max(1.0, abs(float(b))):
            bad.append((tag, name, a, b))

    for tag, m in TM.items():
        x, t = rm[tag], m["tot"]
        for a, b in (("cagr22", "cagr22"), ("dd22", "dd_mtm22"), ("uw22", "uw_mtm22"), ("calmar22", "calmar22"),
                     ("n_per_year", "n_per_year"), ("eq_final", "equity"), ("pnl", "sum_pnl_2022_25"),
                     ("win", "win22"), ("sl", "sl22"), ("dd_all", "dd_mtm")):
            chk(tag, a, t[a], x[b])
        chk(tag, "op95", t["op95"], x["conc22"]["open_p95"])
        chk(tag, "opmax", t["opmax"], x["conc22"]["open_max"])
        chk(tag, "share0", t["share0"], x["hour0_2022_25"]["share0"])
        if tag != C0:
            chk(tag, "gmin_mean", t["gmin_per_year"], x["gate_minutes"]["mean"])
        for y in YEARS:
            py, ry = m["per"][y], x["per_year"][y]
            for a, b in (("n", "n"), ("pnl", "sum_pnl"), ("win", "win"), ("sl", "sl"), ("meanP", "roi_lenh"),
                         ("roi", "roi_year"), ("dd", "dd_mtm_year")):
                chk(tag, y + "." + a, py[a], ry[b])
            if tag != C0:
                chk(tag, y + ".gmin", py["gmin"], x["gate_minutes"]["per_year"][y])
            o = old.get(m["md5"])
            if o:
                chk(tag, y + ".uw_oldcache", py["uw"], o["uw_year"][y])
                chk(tag, y + ".dd_oldcache", py["dd"], o["dd_year"][y])
        # quy: tong quy = nam (n, pnl, phut vao), ROI ghep quy = ROI nam
        for y in YEARS:
            qs = [q for q in QS if q[:4] == y]
            chk(tag, y + ".n=sumQ", sum(m["per"][q]["n"] for q in qs), m["per"][y]["n"])
            chk(tag, y + ".pnl=sumQ", sum(m["per"][q]["pnl"] for q in qs), m["per"][y]["pnl"])
            chk(tag, y + ".gmin=sumQ", sum(m["per"][q]["gmin"] for q in qs), m["per"][y]["gmin"])
            chk(tag, y + ".roi=prodQ", 100 * (np.prod([1 + m["per"][q]["roi"] / 100 for q in qs]) - 1), m["per"][y]["roi"])
            chk(tag, y + ".dd<=minQ", min(m["per"][q]["dd"] for q in qs) >= m["per"][y]["dd"] - 1e-9, True)
    return cnt[0], bad


def f(x, d=2, sign=False):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "—"
    return (("%+." if sign else "%.") + str(d) + "f") % x


def stat(v):
    v = [float(z) for z in v if z is not None and np.isfinite(float(z))]
    if not v:
        return None
    return dict(mean=float(np.mean(v)), min=min(v), max=max(v), sd=float(np.std(v, ddof=1)) if len(v) > 1 else 0.0)


def row(cells):
    return "| " + " | ".join(str(c) for c in cells) + " |"


def tbl(head, rows):
    return [row(head), row(["---"] * len(head))] + [row(r) for r in rows] + [""]


class Agg:
    def __init__(self, TM):
        self.TM = TM

    def get(self, t, p, m):
        return (self.TM[t]["tot"] if p == "tot" else self.TM[t]["per"][p]).get(m)

    def A(self, c, p, m):
        return stat([self.get(t, p, m) for t in CFG[c]])

    def mv(self, c, p, m):
        s = self.A(c, p, m)
        return s["mean"] if s else None

    def dif(self, a, b, p, m):
        x, y = self.mv(a, p, m), self.mv(b, p, m)
        return None if x is None or y is None else x - y

    def paired(self, p, m):
        v = [self.get(ON[s], p, m) - self.get(OFF[s], p, m) for s in SEEDS
             if self.get(ON[s], p, m) is not None and self.get(OFF[s], p, m) is not None]
        return stat(v)

    def opc(self, c, p):
        d = 1 if len(CFG[c]) > 1 else 0
        return f(self.mv(c, p, "op95"), d) + "/" + f(self.mv(c, p, "opmax"), d)


YM = [("n", "n", 0), ("pnl", "ΣPnL", 0), ("roi", "ROI %", 2), ("win", "win %", 1), ("sl", "SL %", 1),
      ("meanP", "meanP %", 3), ("dd", "maxDD %", 2), ("uw", "UW ng", 1), ("op", "mở p95/max", None),
      ("gmin", "phút vào", 0), ("gpass", "pass gate", 0), ("share0", "ΣPnL 0h %", 1)]
QG = [[("roi", "ROI %", 2), ("dd", "maxDD %", 2), ("uw", "UW ng", 1)],
      [("n", "n", 0), ("pnl", "ΣPnL", 0), ("win", "win %", 1)],
      [("sl", "SL %", 1), ("meanP", "meanP %", 3), ("share0", "ΣPnL 0h %", 1)],
      [("op", "mở p95/max", None), ("gmin", "phút vào", 0), ("gpass", "pass gate", 0)]]
DM = [("n", "n", 0), ("pnl", "ΣPnL", 0), ("roi", "ROI pp", 2), ("win", "win pp", 1), ("sl", "SL pp", 1),
      ("meanP", "meanP pp", 3), ("dd", "maxDD pp", 2), ("uw", "UW ng", 1), ("gmin", "phút vào", 0)]
TD = [("n_per_year", "n/năm", 0), ("pnl", "ΣPnL", 0), ("cagr22", "CAGR22 pp", 2), ("calmar22", "Calmar22", 3),
      ("dd22", "maxDD22 pp", 2), ("uw22", "UW22 ng", 1), ("win", "win pp", 1), ("sl", "SL pp", 1),
      ("gmin_per_year", "phút vào/năm", 0)]


def cell(G, c, p, k, d):
    return G.opc(c, p) if k == "op" else f(G.mv(c, p, k), d)


def tables(G, m5):
    L = ["## 2. Theo NĂM (C3/C4 = trung bình 8 seed; min..max ở bảng 2b)", ""]
    rows = [[y, c] + [cell(G, c, y, k, d) for k, _, d in YM] for y in YEARS for c in CN]
    L += tbl(["năm", "cfg"] + [lab for _, lab, _ in YM], rows)

    def mm(c, p, k, d):
        s = G.A(c, p, k)
        return f(s["min"], d) + ".." + f(s["max"], d) if s else "—"
    L += ["### 2b. Dải 8 seed theo năm (min..max)", ""]
    rows = [[y, c, mm(c, y, "n", 0), mm(c, y, "pnl", 0), mm(c, y, "roi", 2), mm(c, y, "dd", 2), mm(c, y, "uw", 1),
             mm(c, y, "gmin", 0)] for y in YEARS for c in ("C3", "C4")]
    L += tbl(["năm", "cfg", "n", "ΣPnL", "ROI %", "maxDD %", "UW ng", "phút vào"], rows)
    L += ["## 3. Theo QUÝ (cột = chỉ số × cfg; C3/C4 = trung bình 8 seed)", ""]
    for gi, g in enumerate(QG):
        L += ["### 3%s. %s" % ("abcd"[gi], " · ".join(lab for _, lab, _ in g)), ""]
        head = ["quý"] + ["%s %s" % (lab, c) for _, lab, _ in g for c in CN]
        L += tbl(head, [[q] + [cell(G, c, q, k, d) for k, _, d in g for c in CN] for q in QS])
    L += ["## 4. Tổng 2022–25 (C3/C4: mean [min; max])", ""]

    def mc(c, k, d):
        s = G.A(c, "tot", k)
        if not s:
            return "—"
        return f(s["mean"], d) if len(CFG[c]) == 1 else "%s [%s; %s]" % (f(s["mean"], d), f(s["min"], d), f(s["max"], d))
    TC = [("cagr22", "CAGR22 %", 2), ("calmar22", "Calmar22", 3), ("dd22", "maxDD22 %", 2), ("uw22", "UW22 ng", 1),
          ("n_per_year", "n/năm", 0), ("eq_final", "eq cuối", 0), ("pnl", "ΣPnL 22–25", 0), ("win", "win %", 1),
          ("sl", "SL %", 1), ("op", "mở p95/max", None), ("gmin_per_year", "phút vào/năm", 0),
          ("share0", "ΣPnL 0h %", 1), ("skipFull", "skipFull", 0)]
    rows = [[c] + [G.opc(c, "tot") if k == "op" else mc(c, k, d) for k, _, d in TC] for c in CN]
    rows.append(["C5"] + ["= C0 (md5 %s = %s, byte-identical)" % (m5[C5][:8], m5[C0][:8])] + [""] * (len(TC) - 1))
    L += tbl(["cfg"] + [lab for _, lab, _ in TC], rows)
    L += ["## 5. Δ theo năm (pp cho %; cặp = ON−OFF cùng seed, mean ± sd, n=8)", ""]
    rows = []
    for y in YEARS + ["tot"]:
        ms = DM if y != "tot" else TD
        if y == "tot":
            L += tbl(["năm", "Δ"] + [lab for _, lab, _ in DM], rows)
            rows = []
            L += ["### 5b. Δ tổng 2022–25", ""]
        lab_y = y if y != "tot" else "2022–25"
        for a, b in (("C2", "C0"), ("C2", "C1"), ("C4", "C3")):
            rows.append([lab_y, a + "−" + b] + [f(G.dif(a, b, y, k), d, True) for k, _, d in ms])
        pr = [G.paired(y, k) for k, _, _ in ms]
        rows.append([lab_y, "cặp ON−OFF 8 seed"] +
                    [(f(s["mean"], d, True) + " ± " + f(s["sd"], d)) if s else "—" for s, (_, _, d) in zip(pr, ms)])
    L += tbl(["kỳ", "Δ"] + [lab for _, lab, _ in TD], rows)
    L += ["## 6. Từng seed: ROI năm OFF→ON, maxDD22, skipFull (K24)", ""]
    rows = []
    for s in SEEDS:
        a, b = G.TM[OFF[s]], G.TM[ON[s]]
        rows.append([s] + ["%s → %s" % (f(a["per"][y]["roi"]), f(b["per"][y]["roi"])) for y in YEARS] +
                    ["%s → %s" % (f(a["tot"]["cagr22"]), f(b["tot"]["cagr22"])),
                     "%s → %s" % (f(a["tot"]["dd22"]), f(b["tot"]["dd22"])), f(b["tot"]["skipFull"], 0)])
    L += tbl(["seed"] + ["ROI %s" % y for y in YEARS] + ["CAGR22", "maxDD22", "skipFull ON"], rows)
    L += ["## 7. Cơ chế 05–09/2022 theo THÁNG: C1 (K24 OFF s42) vs C2 (K24 ON s42)", ""]
    rows = [[mo] + [cell(G, c, mo, k, d) for k, d in (("n", 0), ("pnl", 0), ("roi", 2), ("gmin", 0), ("op", None))
                    for c in ("C1", "C2")] for mo in MONTHS]
    L += tbl(["tháng"] + ["%s %s" % (lab, c) for lab in ("n", "ΣPnL", "ROI %", "phút vào", "mở p95/max")
                          for c in ("C1", "C2")], rows)
    t1, t2 = G.TM[CFG["C1"][0]], G.TM[CFG["C2"][0]]
    L += ["pass gate (log Java, theo quý) C1→C2: 2022Q2 %s→%s, 2022Q3 %s→%s; skipFull C2 tổng cả run = %s "
          "(Java chỉ log tổng, không có theo tháng/quý)." % (t1["per"]["2022Q2"]["gpass"], t2["per"]["2022Q2"]["gpass"],
                                                            t1["per"]["2022Q3"]["gpass"], t2["per"]["2022Q3"]["gpass"],
                                                            t2["tot"]["skipFull"]), ""]
    o, n = G.TM[OFF["S21"]], G.TM[ON["S21"]]
    L += ["### 7b. Đối chứng cơ chế (ngoài C0..C4): seed S21 K24 OFF vs ON (skipFull lớn nhất)", ""]
    rows = [[mo] + ["%s → %s" % (f(o["per"][mo][k], d), f(n["per"][mo][k], d))
                    for k, d in (("n", 0), ("pnl", 0), ("roi", 2), ("gmin", 0))] for mo in MONTHS]
    L += tbl(["tháng", "n OFF→ON", "ΣPnL OFF→ON", "ROI % OFF→ON", "phút vào OFF→ON"], rows)
    L += ["pass gate S21 OFF→ON: 2022Q2 %s→%s, 2022Q3 %s→%s; skipFull ON = %s." % (
        o["per"]["2022Q2"]["gpass"], n["per"]["2022Q2"]["gpass"], o["per"]["2022Q3"]["gpass"],
        n["per"]["2022Q3"]["gpass"], n["tot"]["skipFull"]), ""]
    return L


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=3)
    a = ap.parse_args()
    os.makedirs(D, exist_ok=True)
    tags = sorted({t for v in CFG.values() for t in v})
    legs = {t: R.load_legs(t) for t in tags}
    daily = {t: R.load_daily(t) for t in tags}
    m5 = {t: R.md5_of(t) for t in tags + MD5_ONLY}
    log.info("MD5 %s", {t: v[:8] for t, v in m5.items()})
    assert m5[C0].startswith("ff3ce513") and m5[C5] == m5[C0], "C0/C5 md5 sai"
    raw = json.load(open(MTM_CACHE)) if os.path.exists(MTM_CACHE) else {}
    miss = {t: legs[t] for t in tags if raw.get(t, {}).get("md5") != m5[t]}
    if miss:
        log.info("MTM phut can tinh %d tag: %s", len(miss), sorted(miss))
        new = R.run_mtm(miss, workers=a.workers, chunk=30)
        for t, v in new.items():
            v["md5"] = m5[t]
            raw[t] = v
        json.dump(raw, open(MTM_CACHE, "w"))
    TM = {}
    for t in tags:
        L = raw[t]["legacy"]
        for k in ("dd_year", "uw_year"):
            L[k] = {str(kk): vv for kk, vv in L[k].items()}
        TM[t] = tag_metrics(t, legs[t], daily[t], L)
        TM[t]["md5"] = m5[t]
    nchk, bad = validate(TM, json.load(open(REF)))
    log.info("VALIDATE %d check, %d lech", nchk, len(bad))
    for b in bad[:60]:
        log.info("LECH %s", b)
    if bad:
        log.error("TU KIEM LECH -> DUNG, khong xuat bang")
        sys.exit(2)
    G = Agg(TM)
    keys = sorted({k for t in tags for p in TM[t]["per"].values() for k in p})
    tkeys = sorted({k for t in tags for k in TM[t]["tot"]})
    cfg = {c: {p: {k: G.A(c, p, k) for k in keys} for p in YEARS + QS + MONTHS} for c in CN}
    for c in CN:
        cfg[c]["tot"] = {k: G.A(c, "tot", k) for k in tkeys}
    paired = {p: {k: G.paired(p, k) for k in keys} for p in YEARS + QS}
    paired["tot"] = {k: G.paired("tot", k) for k in tkeys}
    js = dict(title="GATE_SKIPFULL_DETAIL", date="2026-10-05", source_results=["f089f37d", "4d408243"],
              note="chi tinh tu output Kaggle co san; phi legacy as-is; MTM phut (reset_rule_score); 0 sim",
              cfg_tags=CFG, on=ON, off=OFF, c5=C5, md5=m5, validation=dict(n_checks=nchk, mismatches=bad),
              cfg=cfg, paired_on_minus_off=paired, per_tag={t: dict(md5=TM[t]["md5"], tot=TM[t]["tot"], per=TM[t]["per"])
                                                            for t in tags})
    json.dump(js, open(JSON_OUT, "w"), indent=1, ensure_ascii=False, default=str)
    rows = []
    days = sorted(raw[C0]["legacy"]["dclose"])
    for ds in days:
        rows.append([ds] + [round(raw[CFG[c][0]]["legacy"][k].get(ds, np.nan), 1) for c in ("C0", "C1", "C2")
                            for k in ("dclose", "dmin")])
    pd.DataFrame(rows, columns=["date_utc", "C0_mtm_close", "C0_mtm_min", "C1_mtm_close", "C1_mtm_min", "C2_mtm_close",
                                "C2_mtm_min"]).to_csv(CSV_OUT, index=False)
    with open(MD_OUT, "w") as fo:
        fo.write("\n".join(tables(G, m5)))
    log.info("OUT %s %s %s", JSON_OUT, CSV_OUT, MD_OUT)


if __name__ == "__main__":
    main()
