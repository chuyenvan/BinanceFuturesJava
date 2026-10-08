#!/usr/bin/env python3
"""NSEL scorer B (doc lap) — docs/prereg/PREREG_NSEL.md (9986c929) §4–§6.

Tu dung tu printDone.csv + result.json + nen 1m (chi dung jbin.iter_minutes de DOC du lieu).
Gia dinh (ghi ro):
  - printDone `start`/`end` = gio GMT+7 (Utils.normalizeDateYYYYMMDDHHmm); ticker key = ms UTC.
    Kiem tra thuc nghiem: |entry/close(start) - 1| theo shift 7h vs 0h (in ra log).
  - pnl printDone = calTp() = q*(exit-entry) - fee - slippage - funding; ghi nhan TRON tai phut `end`.
  - Chan dang mo phut m neu start <= m < end; unrealized = q*(close_1m(m) - entry), q = margin/entry
    (margin = calMargin = notional 1x). Khong tru phi/funding cho phan chua dong.
  - Thieu gia: ffill trong ngay; truoc gia dau tien trong ngay -> dung entry (unrealized 0), dem lai.
  - Cua so 2022-01-01 00:00 -> 2025-12-31 23:59 +07; CAGR nam = 1461/365.25 = 4.0.
"""
import gzip
import json
import logging
import os
import re
import sys
from multiprocessing import Pool

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import jbin  # noqa: E402  (chi phan doc nen 1m)

log = logging.getLogger("nsel_score_b")
OUT = "/home/ubuntu/kaggle_sim/out"
TICKER = "/home/ubuntu/kaggle_data_hpo"
QUEUE = "/home/ubuntu/claude_master/1008/nsel_impl/queue_status.tsv"
SEEDS = [42, 7, 13, 21, 99, 123, 777, 2024]
ARMS = ["nen", "m1", "m2"]
TZ_MS = 7 * 3600 * 1000
T0 = int(pd.Timestamp("2022-01-01").value // 10 ** 6) - TZ_MS      # 2021-12-31 17:00Z
T1 = int(pd.Timestamp("2026-01-01").value // 10 ** 6) - TZ_MS      # mo (exclusive)
NM = (T1 - T0) // 60000                                            # 2,103,840 phut
YEARS = [2022, 2023, 2024, 2025]
T_CRIT = 1.894578605                                               # t(0.95; df 7) = 1 - 0.10/2
NWORK = 3


def parse_min(s):
    """'20251201 07:09' (+07) -> ms UTC."""
    return pd.to_datetime(s, format="%Y%m%d %H:%M").astype("int64") // 10 ** 6 - TZ_MS


def parity_pass():
    q = pd.read_csv(QUEUE, sep="\t")
    q["tag"] = q.slug.str.replace("sim-", "", regex=False)
    last = q.drop_duplicates("tag", keep="last").set_index("tag")
    return {t: (r.status == "COMPLETE" and r.parity == "PASS", r.md5_printDone)
            for t, r in last.iterrows()}


def load_runs():
    """Tra ve list run (tag, arm, seed, df, result) — chi seed co du 3 arm PASS."""
    pp = parity_pass()
    runs, seeds_ok = [], []
    for s in SEEDS:
        tags = ["nsel-%s-s%d" % (a, s) for a in ARMS]
        if all(pp.get(t, (False,))[0] for t in tags):
            seeds_ok.append(s)
        else:
            log.warning("seed %d thieu/FAIL parity -> loai ca cap", s)
    for s in seeds_ok:
        for a in ARMS:
            tag = "nsel-%s-s%d" % (a, s)
            d = pd.read_csv(os.path.join(OUT, tag, "storage/printDone.csv"), index_col=False)
            r = json.load(open(os.path.join(OUT, tag, "result.json")))
            d["ts"] = parse_min(d.start)
            d["te"] = parse_min(d.end)
            d["q"] = d.margin / d.entry
            d["sym_t"] = d.sym + "USDT"
            runs.append(dict(tag=tag, arm=a, seed=s, df=d, res=r))
    return runs, seeds_ok


G = {}   # mang chan toan cuc (fork) : run, sym, entry, q, s, e (phut toan cuc tu T0)


def work(day):
    dms = int(pd.Timestamp(day).value // 10 ** 6)
    g0 = (dms - T0) // 60000
    R = G["R"]
    m = (G["s"] < g0 + 1440) & (G["e"] > g0) & (G["e"] > G["s"])
    idx = np.nonzero(m)[0]
    U = np.zeros((R, 1440))
    out = dict(day=day, g0=g0, U=U, miss=0, legmin=0, rel7=[], rel0=[], nofile=0)
    if len(idx) == 0:
        return out
    syms = sorted(set(G["sym"][idx]))
    si = {s: i for i, s in enumerate(syms)}
    P = np.full((len(syms), 1440), np.nan)
    p = os.path.join(TICKER, "ticker_%s.bin.gz" % day)
    if os.path.exists(p):
        with gzip.open(p, "rb") as f:
            for k, v in jbin.iter_minutes(f.read()):
                j = (k - dms) // 60000
                if 0 <= j < 1440:
                    for s, i in si.items():
                        t = v.get(s)
                        if t is not None:
                            P[i, j] = t[3]          # close (tuple: start,max,min,close,open,vol)
    else:
        out["nofile"] = 1
    raw = P.copy()
    P = pd.DataFrame(P).ffill(axis=1).to_numpy()
    for li in idx:
        i = si[G["sym"][li]]
        s, e, en, q = G["s"][li], G["e"][li], G["entry"][li], G["q"][li]
        a, b = max(s, g0) - g0, min(e, g0 + 1440) - g0
        pr = P[i, a:b]
        nn = np.isnan(pr)
        out["miss"] += int(nn.sum())
        out["legmin"] += b - a
        pr = np.where(nn, en, pr)
        U[G["run"][li], a:b] += q * (pr - en)
        if g0 <= s < g0 + 1440:
            c7 = raw[i, s - g0]
            if np.isfinite(c7):
                out["rel7"].append(en / c7 - 1.0)
            j0 = s - g0 + 420                      # neu `start` la UTC thi phut that = s + 7h
            if j0 < 1440 and np.isfinite(raw[i, j0]):
                out["rel0"].append(en / raw[i, j0] - 1.0)
    # chi giu phut trong cua so
    lo, hi = max(0, -g0), min(1440, NM - g0)
    out["U"] = U[:, lo:hi] if hi > lo else np.zeros((R, 0))
    out["g0"] = g0 + lo
    return out


def ymin(y):
    """Chi so phut toan cuc cua 00:00 ngay 1/1 nam y (+07)."""
    return (int(pd.Timestamp("%d-01-01" % y).value // 10 ** 6) - TZ_MS - T0) // 60000


def metrics(run, U):
    d, res = run["df"], run["res"]
    cap0 = float(res["equity_start"])
    real = np.zeros(NM)
    ie = (d.te.to_numpy() - T0) // 60000
    pnl = d.pnl.to_numpy(dtype=float)
    base = cap0 + pnl[ie < 0].sum()
    ok = (ie >= 0) & (ie < NM)
    np.add.at(real, ie[ok], pnl[ok])
    eq = base + np.cumsum(real) + U
    dd = eq / np.maximum.accumulate(eq) - 1.0
    cagr = (eq[-1] / eq[0]) ** (1.0 / 4.0) - 1.0
    mdd = float(dd.min())
    ins = (d.ts >= T0) & (d.ts < T1)
    inse = (d.te >= T0) & (d.te < T1)
    r = dict(arm=run["arm"], seed=run["seed"], tag=run["tag"],
             n_yr=float(ins.sum()) / 4.0, sum_pnl=float(d.pnl[inse].sum()),
             cagr22=100 * cagr, maxdd22=100 * mdd, calmar22=cagr / abs(mdd),
             eq_win0=float(eq[0]), eq_win1=float(eq[-1]),
             eq_dd_min_ts=str(pd.Timestamp(T0 + int(dd.argmin()) * 60000 + TZ_MS, unit="ms")))
    for y in YEARS:
        a, b = ymin(y), min(ymin(y + 1), NM) - 1
        r["roi_%d" % y] = 100 * (eq[b] / eq[a] - 1.0)
    # tu kiem 1: so voi log Java 'Update YYYYMMDD HH:MM => b:.. unP:..' (b + unP, moc ngay)
    rx = re.compile(r"Update (\d{8} \d{2}:\d{2}) => b:\s*(-?\d+).*?unP:\s*(-?\d+)")
    dev = []
    with open(os.path.join(OUT, run["tag"], "logs/full.log"), errors="replace") as f:
        for line in f:
            mm = rx.search(line)
            if mm:
                k = (int(parse_min(pd.Series([mm.group(1)]))[0]) - T0) // 60000
                if 0 <= k < NM:
                    j = float(mm.group(2)) + float(mm.group(3))
                    dev.append((eq[k] - j) / j)
    dev = np.abs(np.array(dev)) if dev else np.array([np.nan])
    r["logchk_n"] = int(len(dev))
    r["logchk_med_abs_pct"] = 100 * float(np.median(dev))
    r["logchk_max_abs_pct"] = 100 * float(np.max(dev))
    # tu kiem
    eq_all = cap0 + pnl.sum()
    r["eq_final_closed"] = float(eq_all)
    r["eq_result"] = float(res["equity_final"])
    r["eq_dev_pct"] = 100 * (eq[-1] / float(res["equity_final"]) - 1.0)
    r["open_at_end"] = int(((d.ts < T1) & (d.te >= T1)).sum())
    r["n_rows"] = int(len(d))
    r["n_result"] = int(res["n_trades"])
    return r


def delta_stats(x):
    x = np.asarray(x, dtype=float)
    n = len(x)
    sd = float(x.std(ddof=1)) if n > 1 else float("nan")
    mu = float(x.mean())
    return dict(mean=mu, sd=sd, npos=int((x > 0).sum()), n=n,
                lb=mu - T_CRIT * sd / np.sqrt(n))


KEYS = ["n_yr", "sum_pnl", "cagr22", "maxdd22", "calmar22"] + ["roi_%d" % y for y in YEARS]


def verdict(arm, rows, deltas):
    dl = deltas[arm]
    mean_cal = {a: np.mean([r["calmar22"] for r in rows if r["arm"] == a]) for a in ARMS}
    v = {}
    v["G1"] = dict(ok=dl["n_yr"]["mean"] >= 500, val=dl["n_yr"]["mean"], rule="mean dn >= +500/yr")
    v["G2"] = dict(ok=dl["sum_pnl"]["mean"] >= 0 and dl["sum_pnl"]["lb"] >= -8000,
                   val=[dl["sum_pnl"]["mean"], dl["sum_pnl"]["lb"]], rule="mean>=0 & LB>=-8k")
    worst = min(r["maxdd22"] for r in rows if r["arm"] == arm)
    v["G3"] = dict(ok=worst >= -40.0 and dl["maxdd22"]["mean"] >= -8.0,
                   val=[worst, dl["maxdd22"]["mean"]], rule="maxDD<=40% moi seed & mean dDD>=-8pp")
    v["G4"] = dict(ok=mean_cal[arm] >= 0.85 * mean_cal["nen"],
                   val=[mean_cal[arm], 0.85 * mean_cal["nen"]], rule="mean Calmar22 >= 0.85*NEN")
    ym = [dl["roi_%d" % y]["mean"] for y in YEARS]
    v["G5"] = dict(ok=sum(x >= 0 for x in ym) >= 2 and min(ym) >= -8.0, val=ym,
                   rule=">=2/4 nam mean dROI>=0 & khong nam < -8pp")
    v["G6"] = dict(ok=None, val="do scorer A/MASTER", rule="khop noi J-A..J-F")
    v["GO_G1_G5"] = all(v[g]["ok"] for g in ["G1", "G2", "G3", "G4", "G5"])
    for g in v:
        if isinstance(v[g], dict) and isinstance(v[g]["ok"], (np.bool_,)):
            v[g]["ok"] = bool(v[g]["ok"])
    v["GO_G1_G5"] = bool(v["GO_G1_G5"])
    return v


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    repo = os.path.abspath(os.path.join(HERE, "..", ".."))
    outdir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(repo, "docs", "result")
    runs, seeds_ok = load_runs()
    log.info("seeds_ok=%s runs=%d", seeds_ok, len(runs))
    cols = {k: [] for k in ["run", "sym", "entry", "q", "s", "e"]}
    for ri, rn in enumerate(runs):
        d = rn["df"]
        cols["run"].append(np.full(len(d), ri))
        cols["sym"].append(d.sym_t.to_numpy())
        cols["entry"].append(d.entry.to_numpy(dtype=float))
        cols["q"].append(d.q.to_numpy(dtype=float))
        cols["s"].append(((d.ts - T0) // 60000).to_numpy())
        cols["e"].append(((d.te - T0) // 60000).to_numpy())
    for k in cols:
        G[k] = np.concatenate(cols[k])
    G["R"] = len(runs)
    days = [x.strftime("%Y%m%d") for x in pd.date_range("2021-12-31", "2025-12-31", freq="D")]
    U = np.zeros((len(runs), NM))
    miss = legmin = nofile = 0
    rel7, rel0 = [], []
    with Pool(NWORK) as pool:
        for i, o in enumerate(pool.imap_unordered(work, days, chunksize=4)):
            g, Uo = o["g0"], o["U"]
            lo, hi = max(0, -g), min(Uo.shape[1], NM - g)
            if hi > lo:
                U[:, g + lo:g + hi] += Uo[:, lo:hi]
            miss += o["miss"]
            legmin += o["legmin"]
            nofile += o["nofile"]
            rel7 += o["rel7"]
            rel0 += o["rel0"]
            if i % 100 == 0:
                log.info("day %d/%d", i, len(days))
    a7, a0 = np.abs(np.array(rel7)), np.abs(np.array(rel0))
    chk = dict(miss_leg_minutes=int(miss), leg_minutes=int(legmin),
               miss_frac=miss / max(legmin, 1), ticker_days_missing=int(nofile),
               tz_check_median_abs_rel_shift7=float(np.median(a7)), n7=int(len(a7)),
               tz_check_median_abs_rel_shift0=float(np.median(a0)), n0=int(len(a0)))
    log.info("check %s", chk)
    rows = [metrics(rn, U[ri]) for ri, rn in enumerate(runs)]
    for r in rows:
        log.info("%s n/yr=%.0f pnl=%.0f cagr=%.2f dd=%.2f cal=%.3f devEq=%.3f%% n=%d/%d log med/max=%.4f/%.4f%%",
                 r["tag"], r["n_yr"], r["sum_pnl"], r["cagr22"], r["maxdd22"],
                 r["calmar22"], r["eq_dev_pct"], r["n_rows"], r["n_result"],
                 r["logchk_med_abs_pct"], r["logchk_max_abs_pct"])
    by = {(r["arm"], r["seed"]): r for r in rows}
    deltas = {}
    for a in ["m1", "m2"]:
        deltas[a] = {k: delta_stats([by[(a, s)][k] - by[("nen", s)][k] for s in seeds_ok])
                     for k in KEYS}
    verd = {a: verdict(a, rows, deltas) for a in ["m1", "m2"]}
    res = dict(scorer="B", prereg="docs/prereg/PREREG_NSEL.md@9986c929", seeds=seeds_ok,
               t_crit=T_CRIT, window="2022-01-01 00:00..2025-12-31 23:59 +07",
               checks=chk, rows=rows, deltas=deltas, verdict=verd)
    os.makedirs(outdir, exist_ok=True)
    with open(os.path.join(outdir, "NSEL_RESULT_B.json"), "w") as f:
        json.dump(res, f, indent=1, default=float)
    write_md(os.path.join(outdir, "NSEL_RESULT_B.md"), res)
    log.info("verdict %s", json.dumps(verd, default=float))


def f2(x, n=2):
    return ("%%.%df" % n) % x


def write_md(path, res):
    L = ["# NSEL — kết quả scorer B (độc lập)", "",
         "Prereg: `%s` §4–§6. Script: `research/analysis/nsel_score_b.py` (không import script phân tích; "
         "chỉ `jbin.iter_minutes` để đọc nến 1m `/home/ubuntu/kaggle_data_hpo`). Seed: %s. t(0,95; df 7) = %.4f."
         % (res["prereg"], res["seeds"], res["t_crit"]), "",
         "## Giả định", "",
         "- `start`/`end` printDone = giờ +07; ticker key = ms UTC (kiểm thực nghiệm bên dưới).",
         "- pnl printDone = calTp() (đã trừ fee, slippage, funding; penalty nằm trong entry) ghi nhận tại phút `end`.",
         "- Chân mở ở phút m nếu start ≤ m < end; unrealized = q·(close1m − entry), q = margin/entry (1x).",
         "- Thiếu giá: ffill trong ngày, trước giá đầu ngày dùng entry. CAGR22 = (E_end/E_start)^(1/4) − 1.",
         "- maxDD22, ROI theo năm tính trên equity MTM phút trong cửa sổ; Δ = arm − NỀN-S cùng seed.", "",
         "## Tự kiểm", ""]
    c = res["checks"]
    L += ["- Phút-chân thiếu giá: %d / %d (%.4f%%); ngày thiếu file ticker: %d."
          % (c["miss_leg_minutes"], c["leg_minutes"], 100 * c["miss_frac"], c["ticker_days_missing"]),
          "- TZ: median |entry/close(start)−1| với giả định +07 = %.5f (n=%d); nếu start là UTC = %.5f (n=%d)."
          % (c["tz_check_median_abs_rel_shift7"], c["n7"], c["tz_check_median_abs_rel_shift0"], c["n0"]), "",
          "| run | eq MTM cuối cửa sổ | eq result.json | lệch % | chân mở qua cuối | n printDone | n result "
          "| log b+unP: n mốc | median lệch % | max lệch % |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for r in res["rows"]:
        L.append("| %s | %.0f | %.0f | %.4f | %d | %d | %d | %d | %.4f | %.4f |" % (
            r["tag"], r["eq_win1"], r["eq_result"], r["eq_dev_pct"], r["open_at_end"],
            r["n_rows"], r["n_result"], r["logchk_n"], r["logchk_med_abs_pct"], r["logchk_max_abs_pct"]))
    L += ["", "## Bảng seed × arm", "",
          "| arm | seed | n/năm | ΣPnL22–25 | CAGR22 % | maxDD22 % | Calmar22 | ROI22 | ROI23 | ROI24 | ROI25 |",
          "|---|---|---|---|---|---|---|---|---|---|---|"]
    for a in ARMS:
        for r in [x for x in res["rows"] if x["arm"] == a]:
            L.append("| %s | %d | %.0f | %.0f | %.2f | %.2f | %.3f | %.2f | %.2f | %.2f | %.2f |" % (
                a, r["seed"], r["n_yr"], r["sum_pnl"], r["cagr22"], r["maxdd22"], r["calmar22"],
                r["roi_2022"], r["roi_2023"], r["roi_2024"], r["roi_2025"]))
        sub = [x for x in res["rows"] if x["arm"] == a]
        L.append("| **%s mean** | | %.0f | %.0f | %.2f | %.2f | %.3f | %.2f | %.2f | %.2f | %.2f |" % tuple(
            [a] + [np.mean([x[k] for x in sub]) for k in KEYS]))
    L += ["", "## Δ ghép cặp vs NỀN-S (mean, sd, #Δ>0, cận dưới một phía)", "",
          "| arm | chỉ số | mean | sd | #Δ>0 | LB |", "|---|---|---|---|---|---|"]
    for a in ["m1", "m2"]:
        for k in KEYS:
            s = res["deltas"][a][k]
            L.append("| %s | %s | %.3f | %.3f | %d/%d | %.3f |" % (a, k, s["mean"], s["sd"], s["npos"],
                                                                 s["n"], s["lb"]))
    L += ["", "## Verdict §6 (G6 do scorer A/MASTER)", "", "| arm | G | PASS | giá trị | luật |",
          "|---|---|---|---|---|"]
    for a in ["m1", "m2"]:
        for g in ["G1", "G2", "G3", "G4", "G5", "G6"]:
            v = res["verdict"][a][g]
            val = v["val"] if isinstance(v["val"], str) else json.dumps(v["val"], default=float)
            L.append("| %s | %s | %s | %s | %s |" % (a, g, v["ok"], val, v["rule"]))
        L.append("| %s | G1–G5 | **%s** | | |" % (a, res["verdict"][a]["GO_G1_G5"]))
    open(path, "w").write("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
