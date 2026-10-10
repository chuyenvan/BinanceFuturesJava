#!/usr/bin/env python3
"""HO26_SCORE_A (2026-10-10): SCORER A (cham chinh thuc, 1 lan) holdout 2026H1.

Pre-reg docs/prereg/PREREG_HOLDOUT2026H1.md (35d03784 + ADD-1 0e3282a6 + ADD-2 1682a311/2691816d/8fe35b23) §1.
Dinh nghia: docs/result/ho26/score_A_defs.md (commit TRUOC khi doc output 2026). Luat KHONG doi, khong tune.
0 sim, 0 Kaggle, 0 Java, 0 cham 242. Thuoc MTM phut = nsel_score_b (TZ_MS, parse_min, TICKER, jbin);
Sharpe/Sortino/dot = quy uoc coverage_m2_base.
Usage: python3 research/analysis/ho26_score_a.py [--workers 3] [--dryrun-dev]
  --dryrun-dev: chay thu duong code tren run DEV nsel-nen/nsel-m2, cua so 2025H1; KHONG doc ho26-*; ghi WD/dryrun.*
"""
import argparse
import gzip
import hashlib
import json
import logging
import math
import os
import re
import sys
import time
from multiprocessing import Pool

import numpy as np
import pandas as pd
from scipy import stats

REPO = "/home/ubuntu/src/BinanceFuturesJava"
sys.path.insert(0, REPO + "/research/analysis")
import nsel_score_b as B  # noqa: E402
import jbin  # noqa: E402

log = logging.getLogger("ho26_score_a")
OUT = "/home/ubuntu/kaggle_sim/out/"
WD = "/home/ubuntu/claude_master/1010/ho26_score_a"
LOCK = "/home/ubuntu/claude_master/1002/oracle_heavy.lock"
QUEUE = "/home/ubuntu/claude_master/1009/ho26/queue_status.tsv"
JSON_OUT = REPO + "/docs/result/ho26/HO26_RESULT_A.json"
MD_OUT = REPO + "/docs/result/ho26/HO26_RESULT_A.md"
SEEDS = [42, 7, 13, 21, 99, 123, 777, 2024]
CFGS = ["b0", "k24", "m2"]
FEES = ["s", "b"]
PAIRS = [("k24", "b0"), ("m2", "k24")]
JAR, PEN = "b7c89f09", 0.01675
TZ_MS = B.TZ_MS
NREP, BSEED, BLOCK = 2000, 20260905, 10
INFL = math.sqrt(2.0 * math.log(3))
EP_GAP = 3
SQ = math.sqrt(365.0)
DEV_REF = dict(sharpe=1.80, cagr=27.6, maxdd=-22.9)
DEVCHK = ("ho26-k24-s-s42", "nsel-nen-s42")
RX_UPD = re.compile(r"Update (\d{8} \d{2}:\d{2}) => b:\s*(-?\d+).*?unP:\s*(-?\d+)")
FL = ["n", "sum_pnl", "roi", "maxdd", "sharpe", "sortino", "cagr_ann", "pct_day_entry", "n_ep", "pct_time_pos"]
G = {}
W = {}


def ms_local(s):
    """'2026-01-01 00:00' (+07) -> ms UTC."""
    return int(pd.Timestamp(s).value // 10 ** 6) - TZ_MS


def tagf(cfg, fee, s):
    if W.get("dry"):
        t = "nsel-m2-s%d" % s if cfg == "m2" else "nsel-nen-s%d" % s
        assert not t.startswith("ho26")
        return t
    return "ho26-%s-%s-s%d" % (cfg, fee, s)


def tmin(m):
    return str(pd.Timestamp(W["T0"] + int(m) * 60000 + TZ_MS, unit="ms"))[:16]


def md5f(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 20), b""):
            h.update(ch)
    return h.hexdigest()


def queue():
    q = {}
    if os.path.exists(QUEUE):
        for ln in open(QUEUE).read().splitlines()[1:]:
            f = ln.split("\t")
            if len(f) >= 5:
                q[f[0].strip()] = dict(status=f[1].strip(), md5=f[2].strip(), n=f[3].strip(), parity=f[4].strip())
    return q


def updates(tag):
    """dong 'Update YYYYMMDD HH:MM => b: unP:' trong sim.out -> list (key, ms UTC, b+unP), dedupe giu dong cuoi."""
    p = OUT + tag + "/logs/sim.out"
    rows = {}
    with open(p, errors="ignore") as f:
        for ln in f:
            m = RX_UPD.search(ln)
            if m:
                rows[m.group(1)] = float(m.group(2)) + float(m.group(3))
    ks = sorted(rows)
    tms = B.parse_min(pd.Series(ks)).to_numpy() if ks else np.array([], np.int64)
    return [(k, int(t), rows[k]) for k, t in zip(ks, tms)]


def ov_get(ov, k):
    v = ov.get(k, "")
    return "" if v is None else str(v).strip().lower()


def pen_of(ov):
    v = ov_get(ov, "SIM_CRASH_ENTRY_PENALTY")
    try:
        return float(v) if v else 0.0
    except ValueError:
        return float("nan")


def parity(cfg, fee, s, Q):
    t = tagf(cfg, fee, s)
    pp, rp = OUT + t + "/storage/printDone.csv", OUT + t + "/result.json"
    if not (os.path.exists(pp) and os.path.exists(rp)):
        return dict(tag=t, ok=False, missing=True)
    rj = json.load(open(rp))
    ov = dict(rj.get("overrides") or {})
    with open(pp, errors="ignore") as f:
        f.readline()
        nrows = sum(1 for ln in f if ln.strip())
    md5 = md5f(pp)
    chk = dict(ok=rj.get("ok") is True, n=rj.get("n_trades") == nrows)
    if not W.get("dry"):
        q = Q.get(t, {})
        k24 = cfg in ("k24", "m2")
        chk.update(queue=q.get("status") == "COMPLETE" and q.get("parity") == "PASS", md5_queue=q.get("md5") == md5,
                   jar=str(rj.get("jar_sha256")).startswith(JAR),
                   topk=ov_get(ov, "SELECTOR_RANK_TOPK") == "24" if k24 else ov_get(ov, "SELECTOR_RANK_TOPK") in ("", "16"),
                   skipfull=ov_get(ov, "GATE_QUOTA_SKIP_WHEN_FULL") == "true" if k24 else
                   ov_get(ov, "GATE_QUOTA_SKIP_WHEN_FULL") in ("", "false"),
                   nsel=ov_get(ov, "NSEL_ADD_ENABLED") == "true" if cfg == "m2" else ov_get(ov, "NSEL_ADD_ENABLED") in ("", "false"),
                   pen=abs(pen_of(ov) - PEN) < 1e-12 if fee == "s" else pen_of(ov) == 0.0,
                   date_last=str(rj.get("date_last")) >= "20260630")
    res = dict(tag=t, ok=bool(all(chk.values())), checks=chk, md5=md5, n=rj.get("n_trades"), nrows=nrows,
               eq_final=rj.get("equity_final"), eq_start=rj.get("equity_start"), date_last=rj.get("date_last"),
               jar=str(rj.get("jar_sha256"))[:8])
    log.info("PARITY %-18s %s md5=%s n=%s fail=%s", t, "PASS" if res["ok"] else "*** FAIL ***", md5[:8], res["n"],
             [k for k, v in chk.items() if not v])
    return res


def load(tag):
    d = pd.read_csv(OUT + tag + "/storage/printDone.csv", index_col=False)
    d.columns = [c.strip() for c in d.columns]
    for c in ("entry", "margin", "pnl", "quantity"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    n0 = len(d)
    d = d.dropna(subset=["entry", "margin", "pnl"]).copy()
    d["sym"] = d["sym"].astype(str).str.strip()
    d["ts"] = B.parse_min(d["start"].astype(str).str.strip()).to_numpy()
    d["te"] = B.parse_min(d["end"].astype(str).str.strip()).to_numpy()
    d["s"] = (d["ts"] - W["T0"]) // 60000
    d["e"] = (d["te"] - W["T0"]) // 60000
    d["q"] = d["margin"] / d["entry"]
    d["sym_t"] = d["sym"] + "USDT"
    return d.reset_index(drop=True), n0 - len(d)


def work(day):
    """1 ngay ticker UTC: unrealized/phut theo run (= nsel_score_b.work, truc goc T0 = dau cua so)."""
    dms = int(pd.Timestamp(day).value // 10 ** 6)
    g0 = (dms - W["T0"]) // 60000
    m = (G["s"] < g0 + 1440) & (G["e"] > g0) & (G["e"] > G["s"])
    idx = np.nonzero(m)[0]
    U = np.zeros((G["R"], 1440))
    out = dict(miss=0, legmin=0, nofile=0, nosym=0)
    if len(idx):
        syms = sorted(set(G["sym"][idx].tolist()))
        si = {s: i for i, s in enumerate(syms)}
        P = np.full((len(syms), 1440), np.nan)
        p = os.path.join(B.TICKER, "ticker_%s.bin.gz" % day)
        if os.path.exists(p):
            with gzip.open(p, "rb") as f:
                for k, v in jbin.iter_minutes(f.read()):
                    j = (k - dms) // 60000
                    if 0 <= j < 1440:
                        for s, i in si.items():
                            t = v.get(s)
                            if t is not None:
                                P[i, j] = t[3]
        else:
            out["nofile"] = 1
        out["nosym"] = int(np.isnan(P).all(axis=1).sum())
        P = pd.DataFrame(P).ffill(axis=1).to_numpy()
        for li in idx:
            i = si[G["sym"][li]]
            s, e, en, q = int(G["s"][li]), int(G["e"][li]), G["entry"][li], G["q"][li]
            a, b = max(s, g0) - g0, min(e, g0 + 1440) - g0
            pr = P[i, a:b]
            nn = np.isnan(pr)
            out["miss"] += int(nn.sum())
            out["legmin"] += int(b - a)
            U[G["run"][li], a:b] += q * (np.where(nn, en, pr) - en)
    lo, hi = max(0, -g0), min(1440, W["NE"] - g0)
    hi = max(hi, lo)
    out["U"] = U[:, lo:hi]
    out["g0"] = g0 + lo
    return out


def build(tags, D, workers):
    cols = {k: [] for k in ("run", "sym", "entry", "q", "s", "e")}
    for ri, t in enumerate(tags):
        d = D[t]
        cols["run"].append(np.full(len(d), ri))
        cols["sym"].append(d["sym_t"].to_numpy())
        cols["entry"].append(d["entry"].to_numpy(float))
        cols["q"].append(d["q"].to_numpy(float))
        cols["s"].append(d["s"].to_numpy(np.int64))
        cols["e"].append(d["e"].to_numpy(np.int64))
    for k in cols:
        G[k] = np.concatenate(cols[k])
    G["R"] = len(tags)
    t_a = pd.Timestamp(W["T0"], unit="ms").normalize()
    t_b = pd.Timestamp(W["T0"] + (W["NE"] - 1) * 60000, unit="ms").normalize()
    days = [x.strftime("%Y%m%d") for x in pd.date_range(t_a, t_b, freq="D")]
    U = np.zeros((len(tags), W["NE"]))
    chk = dict(miss=0, legmin=0, nofile=0, nosym=0, days=len(days), day0=days[0], day1=days[-1])
    t0 = time.time()
    with Pool(workers) as pool:
        for i, o in enumerate(pool.imap_unordered(work, days, chunksize=2)):
            g, n = o["g0"], o["U"].shape[1]
            U[:, g:g + n] += o["U"]
            for k in ("miss", "legmin", "nofile", "nosym"):
                chk[k] += o[k]
            if i % 30 == 0:
                log.info("ngay %d/%d %.0fs", i, len(days), time.time() - t0)
    return U, chk


def equity(d, eq_start, Ur):
    """= nsel_score_b.metrics: realized ghi tron tai phut end + unrealized phut."""
    ie = d["e"].to_numpy()
    pnl = d["pnl"].to_numpy(float)
    real = np.zeros(W["NE"])
    ok = (ie >= 0) & (ie < W["NE"])
    np.add.at(real, ie[ok], pnl[ok])
    return float(eq_start) + pnl[ie < 0].sum() + np.cumsum(real) + Ur


def runs_of(b):
    x = np.diff(np.concatenate([[0], np.asarray(b, np.int8), [0]]))
    st = np.nonzero(x == 1)[0]
    return st, np.nonzero(x == -1)[0] - st


def metr(d, eq):
    NW, ND = W["NW"], W["ND"]
    ew = eq[:NW]
    e0 = float(ew[0])
    s, e = d["s"].to_numpy(), d["e"].to_numpy()
    pnl = d["pnl"].to_numpy(float)
    ins, inse = (s >= 0) & (s < NW), (e >= 0) & (e < NW)
    Ed = ew[1439::1440]
    assert len(Ed) == ND, len(Ed)
    r = Ed / np.concatenate([[e0], Ed[:-1]]) - 1.0
    pk = np.maximum.accumulate(ew)
    dd = ew / pk - 1.0
    t = int(dd.argmin())
    p = int(np.argmax(ew[:t + 1]))
    sd = float(r.std(ddof=1))
    dn = float(np.sqrt(np.mean(np.minimum(r, 0) ** 2)))
    days = pd.date_range(W["D0"], periods=ND, freq="D")
    mid = np.asarray((days.year - days[0].year) * 12 + days.month - days[0].month)
    nmon = int(mid.max()) + 1
    me = np.nonzero(np.asarray(days.is_month_end))[0]
    Em = Ed[me]
    roi_m = 100 * (Em / np.concatenate([[e0], Em[:-1]]) - 1.0)
    qe = me[2::3]
    Eq = Ed[qe]
    roi_q = 100 * (Eq / np.concatenate([[e0], Eq[:-1]]) - 1.0)
    de, dc = s[ins] // 1440, e[inse] // 1440
    n_m = np.bincount(mid[de], minlength=nmon)
    pnl_m = np.bincount(mid[dc], weights=pnl[inse], minlength=nmon)
    cnt = np.bincount(de, minlength=ND)
    has = cnt > 0
    ed = np.nonzero(has)[0]
    if len(ed):
        brk = np.concatenate([[False], np.diff(ed) - 1 >= EP_GAP])
        epi = np.cumsum(brk)
        n_ep = int(epi[-1]) + 1
        epd = np.full(ND, -1)
        epd[ed] = epi
        ep_n = np.bincount(epd[de], minlength=n_ep)
        ep_st, ep_en = ed[np.concatenate([[True], brk[1:]])], ed[np.concatenate([brk[1:], [True]])]
        ep_len = float((ep_en - ep_st + 1).mean())
    else:
        n_ep, ep_n, ep_len = 0, np.zeros(1), 0.0
    _, gl = runs_of(~has)
    x = np.zeros(NW + 1)
    a_, b_ = np.clip(s, 0, NW), np.clip(e, 0, NW)
    k = b_ > a_
    np.add.at(x, a_[k], 1.0)
    np.add.at(x, b_[k], -1.0)
    inp = np.cumsum(x[:-1]) > 0.5
    cagr = (float(ew[-1]) / e0) ** (365.25 / ND) - 1.0
    m = dict(n=int(ins.sum()), sum_pnl=float(pnl[inse].sum()), n_close=int(inse.sum()),
             roi=100 * (float(ew[-1]) / e0 - 1.0), maxdd=100 * float(dd.min()), dd_peak=tmin(p), dd_trough=tmin(t),
             sharpe=float(r.mean()) / sd * SQ if sd > 0 else None, sortino=float(r.mean()) / dn * SQ if dn > 0 else None,
             vol=100 * sd * SQ, worst_day=100 * float(r.min()), best_day=100 * float(r.max()), cagr_ann=100 * cagr,
             eq0=e0, eq1=float(ew[-1]), roi_m=[float(v) for v in roi_m], n_m=[int(v) for v in n_m],
             pnl_m=[float(v) for v in pnl_m], roi_q=[float(v) for v in roi_q],
             pct_day_entry=100 * float(has.mean()), n_ep=n_ep, ep_trades_mean=float(ep_n.mean()), ep_len_mean=ep_len,
             gap_max=int(gl.max()) if len(gl) else 0, pct_time_pos=100 * float(inp.mean()),
             open_at_end=int(((s < NW) & (e >= NW)).sum()), open_at_start=int(((s < 0) & (e >= 0)).sum()))
    m["ratio_dev"] = dict(sharpe=m["sharpe"] / DEV_REF["sharpe"] if m["sharpe"] is not None else None,
                          cagr=m["cagr_ann"] / DEV_REF["cagr"], maxdd=m["maxdd"] / DEV_REF["maxdd"])
    return m, (e0, Ed.copy())


def eqcheck(eq, ups, rj):
    """E(phut Update) vs b+unP; E(phut Update cuoi co ngay = date_last) vs result.equity_final."""
    dev, fin = [], None
    for k, tms, v in ups:
        j = (tms - W["T0"]) // 60000
        if 0 <= j < W["NE"] and v != 0:
            dev.append(abs(eq[j] / v - 1.0))
    dl = str(rj.get("date_last"))
    last = [u for u in ups if u[0][:8] == dl]
    if last:
        j = (last[-1][1] - W["T0"]) // 60000
        if 0 <= j < W["NE"] and rj.get("equity_final"):
            fin = 100 * (eq[j] / float(rj["equity_final"]) - 1.0)
    upd_final = last[-1][2] if last else None
    return dict(n_upd=len(dev), med_pct=100 * float(np.median(dev)) if dev else None,
                max_pct=100 * float(np.max(dev)) if dev else None, final_dev_pct=fin,
                final_ok=fin is not None and abs(fin) <= 0.01, upd_last=last[-1][0] if last else None,
                upd_last_eq=upd_final, upd_vs_result=(upd_final == float(rj["equity_final"]))
                if (upd_final is not None and rj.get("equity_final") is not None) else None)


def devcheck():
    """phan truoc 2026 cua ho26-k24-s-s42 vs nsel-nen-s42 (cung cau hinh DEV)."""
    th, td = DEVCHK
    uh, ud = {k: v for k, _, v in updates(th)}, {k: v for k, _, v in updates(td)}
    com = sorted(k for k in set(uh) & set(ud) if k[:8] <= "20251231")
    df = [abs(uh[k] - ud[k]) for k in com]
    r = dict(n_upd_common=len(com), n_upd_diff=int(sum(x > 0 for x in df)), max_abs_diff=float(max(df)) if df else None,
             first_diff=next((k for k in com if uh[k] != ud[k]), None),
             ho_20251230=uh.get(next((k for k in sorted(uh) if k.startswith("20251230")), ""), None),
             dev_20251230=ud.get(next((k for k in sorted(ud) if k.startswith("20251230")), ""), None),
             ho_20251231=uh.get(next((k for k in sorted(uh) if k.startswith("20251231")), ""), None),
             dev_20251231=ud.get(next((k for k in sorted(ud) if k.startswith("20251231")), ""), None),
             dev_last_upd=sorted(ud)[-1] if ud else None)
    ph = pd.read_csv(OUT + th + "/storage/printDone.csv", index_col=False, dtype=str)
    pdv = pd.read_csv(OUT + td + "/storage/printDone.csv", index_col=False, dtype=str)
    for x in (ph, pdv):
        x.columns = [c.strip() for c in x.columns]
        for c in x.columns:
            x[c] = x[c].astype(str).str.strip()
    cc = [c for c in pdv.columns if c in ph.columns]
    cut = "20251230 07:00"
    a = ph.loc[ph["end"] < cut, cc].agg("|".join, axis=1).value_counts()
    b = pdv.loc[pdv["end"] < cut, cc].agg("|".join, axis=1).value_counts()
    al = a.reindex(a.index.union(b.index), fill_value=0)
    bl = b.reindex(a.index.union(b.index), fill_value=0)
    r.update(cut_end=cut, cols=len(cc), n_ho=int(a.sum()), n_dev=int(b.sum()),
             only_ho=int((al - bl).clip(lower=0).sum()), only_dev=int((bl - al).clip(lower=0).sum()),
             cols_only_ho=[c for c in ph.columns if c not in cc], cols_only_dev=[c for c in pdv.columns if c not in ph.columns])
    r["ok"] = r["n_upd_diff"] == 0 and r["only_ho"] == 0 and r["only_dev"] == 0
    log.info("DEVCHECK %s", r)
    return r


def summ(v):
    v = np.asarray([x for x in v if x is not None], float)
    n = len(v)
    if n == 0:
        return None
    sd = float(v.std(ddof=1)) if n > 1 else float("nan")
    tq = float(stats.t.ppf(0.95, n - 1)) if n > 1 else float("nan")
    hw = tq * sd / math.sqrt(n) if n > 1 else float("nan")
    return dict(n=n, mean=float(v.mean()), sd=sd, min=float(v.min()), max=float(v.max()), npos=int((v > 0).sum()),
                lb=float(v.mean() - hw), lb_infl=float(v.mean() - hw * INFL), vals=[float(x) for x in v])


def boot(ED, a, b, fee, seeds):
    """MTM ngay block-10d ghep cap: stat = mean_s sum_d (dE_a - dE_b) = mean_s delta(E1 - E0)."""
    X = []
    for s in seeds:
        (a0, Ea), (b0, Eb) = ED[(a, fee, s)], ED[(b, fee, s)]
        X.append(np.diff(np.concatenate([[a0], Ea])) - np.diff(np.concatenate([[b0], Eb])))
    X = np.array(X)
    T = X.shape[1]
    nb = int(math.ceil(T / BLOCK))
    rng = np.random.default_rng(BSEED)
    bs = np.empty(NREP)
    for i in range(NREP):
        st = rng.integers(0, T - BLOCK + 1, size=nb)
        bs[i] = X[:, (st[:, None] + np.arange(BLOCK)[None, :]).ravel()[:T]].sum(axis=1).mean()
    obs = float(X.sum(axis=1).mean())
    lo, hi = np.percentile(bs, [2.5, 97.5])
    return dict(obs=obs, per_seed=[float(x) for x in X.sum(axis=1)], ci_raw=[float(lo), float(hi)],
                ci_infl=[float(obs - (obs - lo) * INFL), float(obs + (hi - obs) * INFL)],
                p5=float(np.percentile(bs, 5)), p_le0=float(np.mean(bs <= 0)), T=T, nrep=NREP, seed=BSEED, seeds=seeds)


def rules(M, fee, ok):
    def v(c, s, f):
        return M[(c, fee, s)][f]
    sE = [s for s in SEEDS if ok[("k24", fee, s)]]
    sA = [s for s in SEEDS if ok[("k24", fee, s)] and ok[("b0", fee, s)]]
    sB = [s for s in SEEDS if ok[("k24", fee, s)] and ok[("m2", fee, s)]]
    r = {}
    pe = [v("k24", s, "sum_pnl") for s in sE]
    npe = int(sum(x > 0 for x in pe))
    r["E0"] = dict(seeds=sE, mean_sum_pnl=float(np.mean(pe)) if pe else None, n_pos=npe, vals=pe,
                   thr="mean SumPnL_S(k24) > 0 VA >= 6/8 seed > 0", ok=bool(pe and np.mean(pe) > 0 and npe >= 6))
    dP = [v("k24", s, "sum_pnl") - v("b0", s, "sum_pnl") for s in sA]
    dD = [v("k24", s, "maxdd") - v("b0", s, "maxdd") for s in sA]
    r["H-A"] = dict(seeds=sA, mean_dpnl=float(np.mean(dP)) if dP else None, mean_ddd=float(np.mean(dD)) if dD else None,
                    dpnl=dP, ddd=dD, thr="mean dSumPnL_S >= 0 VA mean dmaxDD >= -5pp",
                    ok=bool(dP and np.mean(dP) >= 0 and np.mean(dD) >= -5.0))
    dn = [v("m2", s, "n") - v("k24", s, "n") for s in sB]
    dP = [v("m2", s, "sum_pnl") - v("k24", s, "sum_pnl") for s in sB]
    dD = [v("m2", s, "maxdd") - v("k24", s, "maxdd") for s in sB]
    kb = [v("k24", s, "sum_pnl") for s in sB]
    thr = -0.10 * float(np.mean(kb)) if kb else None
    per = [dp >= -0.10 * k for dp, k in zip(dP, kb)]
    c1 = bool(dn and np.mean(dn) >= 200)
    c2 = bool(dP and np.mean(dP) >= thr)
    c3 = bool(dD and np.mean(dD) >= -8.0)
    c4 = int(sum(per)) >= 5
    r["H-B"] = dict(seeds=sB, mean_dn=float(np.mean(dn)) if dn else None, mean_dpnl=float(np.mean(dP)) if dP else None,
                    thr_dpnl=thr, mean_k24_pnl=float(np.mean(kb)) if kb else None, mean_ddd=float(np.mean(dD)) if dD else None,
                    n_seed_ok=int(sum(per)), per_seed_ok=per, dn=dn, dpnl=dP, ddd=dD,
                    c=dict(dn=c1, dpnl=c2, ddd=c3, seeds=c4),
                    thr="mean dn >= +200 VA mean dSumPnL_S >= -10% mean SumPnL_S(k24) VA mean dmaxDD >= -8pp VA >= 5/8 seed",
                    ok=bool(c1 and c2 and c3 and c4))
    return r


def fm(x, nd=2, sign=False):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "—"
    return ((("%+." if sign else "%.") + str(nd) + "f") % x).replace(".", ",")


def mmm(x, nd=2):
    if x is None:
        return "—"
    return "%s [%s..%s]" % (fm(x["mean"], nd), fm(x["min"], nd), fm(x["max"], nd))


def write_md(js, path):
    o = ["# HO26 — KẾT QUẢ CHẤM SCORER A (chính thức) — holdout 2026H1", "",
         "Pre-reg `docs/prereg/PREREG_HOLDOUT2026H1.md` (35d03784 + ADD-1 0e3282a6 + ADD-2 1682a311/2691816d/8fe35b23) §1. "
         "Định nghĩa `docs/result/ho26/score_A_defs.md` + script `research/analysis/ho26_score_a.py` commit %s TRƯỚC khi đọc "
         "output 2026. JSON `docs/result/ho26/HO26_RESULT_A.json`. 0 sim, 0 Kaggle, 0 Java, 0 chạm 242. Chấm 1 lần; luật không đổi." % js["defs_commit"],
         "", "Cửa sổ %s → %s (+07, %d ngày). Bản CHÍNH = stress `-s-` (1,675%% in-sim); `-b-` = phí gốc (báo kèm)." % (
             js["window"][0], js["window"][1], js["window"][2]), ""]
    o += ["## 1. Verdict (bản CHÍNH, stress)", ""]
    R = js["rules"]["s"]
    e, a, b = R["E0"], R["H-A"], R["H-B"]
    o.append("- **E0 %s**: k24 mean ΣPnL_S = %s (> 0); seed > 0: %d/%d (≥ 6)." % (
        "PASS" if e["ok"] else "FAIL", fm(e["mean_sum_pnl"], 0), e["n_pos"], len(e["seeds"])))
    o.append("- **H-A %s**: mean ΔΣPnL_S (k24−b0) = %s (≥ 0); mean ΔmaxDD = %s pp (≥ −5)." % (
        "XÁC NHẬN" if a["ok"] else "KHÔNG xác nhận", fm(a["mean_dpnl"], 0, True), fm(a["mean_ddd"], 2, True)))
    o.append("- **H-B %s**: mean Δn = %s (≥ +200) %s; mean ΔΣPnL_S = %s (≥ %s = −10%% × %s) %s; mean ΔmaxDD = %s pp (≥ −8) %s; "
             "seed đạt %d/%d (≥ 5) %s." % (
                 "XÁC NHẬN" if b["ok"] else "KHÔNG xác nhận", fm(b["mean_dn"], 1, True), "✓" if b["c"]["dn"] else "✗",
                 fm(b["mean_dpnl"], 0, True), fm(b["thr_dpnl"], 0, True), fm(b["mean_k24_pnl"], 0), "✓" if b["c"]["dpnl"] else "✗",
                 fm(b["mean_ddd"], 2, True), "✓" if b["c"]["ddd"] else "✗", b["n_seed_ok"], len(b["seeds"]),
                 "✓" if b["c"]["seeds"] else "✗"))
    Rb = js["rules"]["b"]
    o += ["", "Phí gốc (mô tả, cùng biểu thức): E0 %s (mean %s, %d/%d); H-A %s (ΔΣPnL %s, ΔDD %s); H-B %s (Δn %s, ΔΣPnL %s vs %s, ΔDD %s, %d/%d)." % (
        "PASS" if Rb["E0"]["ok"] else "FAIL", fm(Rb["E0"]["mean_sum_pnl"], 0), Rb["E0"]["n_pos"], len(Rb["E0"]["seeds"]),
        "đạt" if Rb["H-A"]["ok"] else "không", fm(Rb["H-A"]["mean_dpnl"], 0, True), fm(Rb["H-A"]["mean_ddd"], 2, True),
        "đạt" if Rb["H-B"]["ok"] else "không", fm(Rb["H-B"]["mean_dn"], 1, True), fm(Rb["H-B"]["mean_dpnl"], 0, True),
        fm(Rb["H-B"]["thr_dpnl"], 0, True), fm(Rb["H-B"]["mean_ddd"], 2, True), Rb["H-B"]["n_seed_ok"], len(Rb["H-B"]["seeds"])), ""]
    o += ["## 2. Bảng 3 cfg (mean [min..max] qua seed hợp lệ)", "",
          "| fee | cfg | seed | n | ΣPnL | ROI % | maxDD % | Sharpe | Sortino | CAGR năm hoá % | % ngày có lệnh | số đợt | % t có vị thế |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for fee in FEES:
        for c in CFGS:
            A = js["agg"][fee][c]
            if not A:
                continue
            o.append("| %s | %s | %d | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
                fee, c, A["n"]["n"], mmm(A["n"], 0), mmm(A["sum_pnl"], 0), mmm(A["roi"]), mmm(A["maxdd"]), mmm(A["sharpe"]),
                mmm(A["sortino"]), mmm(A["cagr_ann"], 1), mmm(A["pct_day_entry"], 1), mmm(A["n_ep"], 1), mmm(A["pct_time_pos"], 1)))
    o += ["", "Tỉ lệ holdout/DEV (DEV baseline stress Sharpe 1,80 / CAGR 27,6% / maxDD −22,9%; mean qua seed, fee s): " + "; ".join(
        "%s Sharpe %s, CAGR %s, maxDD %s" % (c, fm(js["ratio_dev"][c]["sharpe"]), fm(js["ratio_dev"][c]["cagr"]), fm(js["ratio_dev"][c]["maxdd"]))
        for c in CFGS if js["ratio_dev"].get(c)), ""]
    o += ["### 2.1 Từng seed (fee s)", "", "| cfg | seed | n | ΣPnL | ROI % | maxDD % | Sharpe | E0 (MTM 01-01) | E1 |", "|---|---|---|---|---|---|---|---|---|"]
    for c in CFGS:
        for s in SEEDS:
            m = js["metrics"].get("%s|s|%d" % (c, s))
            if m:
                o.append("| %s | %d | %d | %s | %s | %s | %s | %s | %s |" % (c, s, m["n"], fm(m["sum_pnl"], 0), fm(m["roi"]), fm(m["maxdd"]),
                         fm(m["sharpe"]), fm(m["eq0"], 0), fm(m["eq1"], 0)))
    o += ["", "## 3. Δ ghép cặp theo seed", "", "| fee | cặp | trường | mean | sd | min | max | seed Δ>0 | cận dưới t95 | cận dưới inflate k=3 |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for fee in FEES:
        for pr, D in js["delta"][fee].items():
            for f in FL:
                x = D.get(f)
                if x:
                    o.append("| %s | %s | %s | %s | %s | %s | %s | %d/%d | %s | %s |" % (fee, pr, f, fm(x["mean"], 2, True), fm(x["sd"]),
                             fm(x["min"], 2, True), fm(x["max"], 2, True), x["npos"], x["n"], fm(x["lb"], 2, True), fm(x["lb_infl"], 2, True)))
    o += ["", "## 4. Bootstrap MTM ngày block-10d (Δ(E1−E0) MTM USD, mean qua seed; NREP 2000, seed 20260905; inflate √(2 ln 3))", "",
          "| fee | cặp | obs | CI95 raw | CI95 inflate | p5 | P(≤0) |", "|---|---|---|---|---|---|---|"]
    for fee in FEES:
        for pr, x in js["boot"][fee].items():
            o.append("| %s | %s | %s | [%s; %s] | [%s; %s] | %s | %s |" % (fee, pr, fm(x["obs"], 0, True), fm(x["ci_raw"][0], 0, True),
                     fm(x["ci_raw"][1], 0, True), fm(x["ci_infl"][0], 0, True), fm(x["ci_infl"][1], 0, True), fm(x["p5"], 0, True), fm(x["p_le0"], 3)))
    mo = js["months"]
    o += ["", "## 5. Theo tháng / quý (fee s)", "", "| | " + " | ".join(mo) + " | Q1 | Q2 |", "|---|" + "---|" * (len(mo) + 2)]
    for c in CFGS:
        A = js["monthly"]["s"].get(c)
        if A:
            o.append("| ROI %% %s | %s | %s |" % (c, " | ".join(fm(x) for x in A["roi_m"]), " | ".join(fm(x) for x in A["roi_q"])))
            o.append("| n %s | %s | | |" % (c, " | ".join(fm(x, 0) for x in A["n_m"])))
            o.append("| ΣPnL %s | %s | | |" % (c, " | ".join(fm(x, 0) for x in A["pnl_m"])))
    for pr, A in js["monthly_delta"]["s"].items():
        o.append("| ΔROI pp %s | %s | %s |" % (pr, " | ".join("%s (%d/%d)" % (fm(x["mean"], 2, True), x["npos"], x["n"]) for x in A["roi_m"]),
                 " | ".join("%s (%d/%d)" % (fm(x["mean"], 2, True), x["npos"], x["n"]) for x in A["roi_q"])))
    o += ["", "## 6. Tự kiểm", ""]
    sc = js["selfcheck"]
    o.append("- Equity cuối E(phút Update cuối) vs result.equity_final: max |lệch| = %s%% (ngưỡng 0,01%%), run vượt: %s." % (
        fm(sc["final_max_abs_pct"], 4), ", ".join(sc["final_bad"]) or "không"))
    o.append("- E(m) vs b+unP mọi dòng Update trong trục: max của max = %s%%, median của median = %s%%." % (
        fm(sc["upd_max_pct"], 4), fm(sc["upd_med_pct"], 4)))
    o.append("- n_trades result == số dòng printDone: %d/%d run; dòng printDone bỏ do NaN: %d." % (sc["n_ok"], sc["n_runs"], sc["dropped"]))
    o.append("- Giá MTM: phút-chân thiếu giá %d / %d (%s%%), ngày thiếu file ticker %d, (symbol, ngày) không có giá nào %d; trục %s → %s UTC." % (
        sc["mtm"]["miss"], sc["mtm"]["legmin"], fm(100.0 * sc["mtm"]["miss"] / max(1, sc["mtm"]["legmin"]), 4), sc["mtm"]["nofile"],
        sc["mtm"]["nosym"], sc["mtm"]["day0"], sc["mtm"]["day1"]))
    dv = sc.get("devcheck")
    if dv:
        o.append("- Phần trước 2026 `%s` vs `%s`: Update chung ≤ 20251231 %d dòng, lệch %d (max |Δ| %s, dòng lệch đầu %s); "
                 "equity Update 20251230: HO %s / DEV %s; 20251231: HO %s / DEV %s; printDone end < %s: HO %d, DEV %d, chỉ HO %d, chỉ DEV %d → %s." % (
                     DEVCHK[0], DEVCHK[1], dv["n_upd_common"], dv["n_upd_diff"], fm(dv["max_abs_diff"], 0), dv["first_diff"],
                     fm(dv["ho_20251230"], 0), fm(dv["dev_20251230"], 0), fm(dv["ho_20251231"], 0), fm(dv["dev_20251231"], 0),
                     dv["cut_end"], dv["n_ho"], dv["n_dev"], dv["only_ho"], dv["only_dev"], "KHỚP" if dv["ok"] else "LỆCH"))
    o += ["", "## 7. Parity run", "", "| run | kết quả | md5 printDone | n | fail |", "|---|---|---|---|---|"]
    for t, p in js["parity"].items():
        if p.get("missing"):
            o.append("| %s | THIẾU | — | — | — |" % t)
        else:
            o.append("| %s | %s | %s | %s | %s |" % (t, "PASS" if p["ok"] else "FAIL", p["md5"][:8], p["n"],
                     ",".join(k for k, v in p["checks"].items() if not v) or "—"))
    o += ["", "## 8. Ghi chú diễn giải (khai trước, pre-reg §6)", "",
          "- R1/R13: holdout = forward test có nhiễm tầng thiết kế; 8 seed chỉ đo nhiễu model gate; 6 tháng ≈ 1/9 DEV ⇒ chỉ rào cứng + dấu ghép cặp.",
          "- R9: model đông lạnh ≤ 2025 cho 2 quý (net015 phương án A còn cũ hơn 3–9 tháng) — đối xứng 3 cfg; không so mức tuyệt đối với DEV."]
    if js.get("notes"):
        o += ["", "Ghi chú sửa lỗi script sau commit defs (không đổi định nghĩa/luật): " + "; ".join(js["notes"])]
    open(path, "w", encoding="utf-8").write("\n".join(o) + "\n")


def jd(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    return str(o)


def take_lock():
    while os.path.exists(LOCK):
        log.info("cho lock %s", LOCK)
        time.sleep(60)
    with open(LOCK, "w") as f:
        f.write("ho26_score_a %d %s\n" % (os.getpid(), time.ctime()))


def drop_lock():
    if os.path.exists(LOCK):
        os.remove(LOCK)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--dryrun-dev", action="store_true")
    ap.add_argument("--defs-commit", default="?")
    ap.add_argument("--note", action="append", default=[])
    A_ = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout, force=True)
    os.makedirs(WD, exist_ok=True)
    W["dry"] = A_.dryrun_dev
    w0, w1 = ("2025-01-01 00:00", "2025-07-01 00:00") if W["dry"] else ("2026-01-01 00:00", "2026-07-01 00:00")
    W["T0"], W["T1"] = ms_local(w0), ms_local(w1)
    W["NW"] = (W["T1"] - W["T0"]) // 60000
    W["ND"] = W["NW"] // 1440
    W["D0"] = pd.Timestamp(w0).normalize()
    log.info("cua so %s -> %s (+07): %d phut, %d ngay, dry=%s", w0, w1, W["NW"], W["ND"], W["dry"])
    Q = queue()
    par = {(c, f, s): parity(c, f, s, Q) for c in CFGS for f in FEES for s in SEEDS}
    ok = {k: v["ok"] for k, v in par.items()}
    keys = [k for k in par if ok[k]]
    tags = sorted({par[k]["tag"] for k in keys})
    log.info("run hop le %d/%d; tag doc %d", len(keys), len(par), len(tags))
    D, drop, UPS, RJ = {}, 0, {}, {}
    for t in tags:
        D[t], dr = load(t)
        drop += dr
        UPS[t] = updates(t)
        RJ[t] = json.load(open(OUT + t + "/result.json"))
    NE = W["NW"]
    if not W["dry"]:
        for t in tags:
            dl = str(RJ[t].get("date_last"))
            ls = [u for u in UPS[t] if u[0][:8] == dl]
            if ls:
                NE = max(NE, (ls[-1][1] - W["T0"]) // 60000 + 1)
        NE = min(NE, W["NW"] + 2 * 1440)
    W["NE"] = int(NE)
    log.info("truc MTM %d phut (cua so %d)", W["NE"], W["NW"])
    cache = WD + ("/U_dry.npz" if W["dry"] else "/U_ho26.npz")
    sig = hashlib.md5(("|".join("%s:%s" % (t, par[[k for k in keys if par[k]["tag"] == t][0]]["md5"]) for t in tags)
                       + "|%d|%d" % (W["T0"], W["NE"])).encode()).hexdigest()
    if os.path.exists(cache) and str(np.load(cache)["sig"]) == sig:
        z = np.load(cache)
        U, mt = z["U"].astype(float), json.loads(str(z["chk"]))
        log.info("U: dung cache %s", cache)
    else:
        take_lock()
        try:
            U, mt = build(tags, D, A_.workers)
        finally:
            drop_lock()
        np.savez(cache, U=U.astype(np.float32), sig=sig, chk=json.dumps(mt))
    ti = {t: i for i, t in enumerate(tags)}
    EQ = {t: equity(D[t], RJ[t]["equity_start"], U[ti[t]]) for t in tags}
    del U
    M, ED, EC = {}, {}, {}
    for t in tags:
        EC[t] = eqcheck(EQ[t], UPS[t], RJ[t])
    for k in keys:
        M[k], ED[k] = metr(D[par[k]["tag"]], EQ[par[k]["tag"]])
        log.info("METR %-18s n=%d pnl=%.0f roi=%.2f dd=%.2f sh=%s", par[k]["tag"], M[k]["n"], M[k]["sum_pnl"], M[k]["roi"],
                 M[k]["maxdd"], fm(M[k]["sharpe"]))
    fin = {t: EC[t]["final_dev_pct"] for t in tags}
    sc = dict(final_max_abs_pct=max((abs(v) for v in fin.values() if v is not None), default=None),
              final_bad=[t for t in tags if not EC[t]["final_ok"]],
              upd_max_pct=max((EC[t]["max_pct"] for t in tags if EC[t]["max_pct"] is not None), default=None),
              upd_med_pct=float(np.median([EC[t]["med_pct"] for t in tags if EC[t]["med_pct"] is not None])) if tags else None,
              n_ok=int(sum(1 for k in par if not par[k].get("missing") and par[k]["checks"]["n"])), n_runs=len(par),
              dropped=int(drop), mtm=mt, eqcheck=EC, devcheck=None if W["dry"] else devcheck())
    agg, delta, mon, mond, boo, rdev = {}, {}, {}, {}, {}, {}
    for fee in FEES:
        agg[fee], mon[fee], delta[fee], mond[fee], boo[fee] = {}, {}, {}, {}, {}
        for c in CFGS:
            ss = [s for s in SEEDS if ok[(c, fee, s)]]
            agg[fee][c] = {f: summ([M[(c, fee, s)][f] for s in ss]) for f in FL} if ss else None
            if ss:
                mon[fee][c] = {f: [float(np.mean(x)) for x in zip(*[M[(c, fee, s)][f] for s in ss])]
                               for f in ("roi_m", "n_m", "pnl_m", "roi_q")}
            if fee == "s" and ss:
                rdev[c] = {f: float(np.mean([M[(c, fee, s)]["ratio_dev"][f] for s in ss
                                             if M[(c, fee, s)]["ratio_dev"][f] is not None])) for f in ("sharpe", "cagr", "maxdd")}
        for a, b in PAIRS:
            pr = "%s-%s" % (a, b)
            ss = [s for s in SEEDS if ok[(a, fee, s)] and ok[(b, fee, s)]]
            if not ss:
                continue
            delta[fee][pr] = {f: summ([(M[(a, fee, s)][f] - M[(b, fee, s)][f])
                                       if M[(a, fee, s)][f] is not None and M[(b, fee, s)][f] is not None else None
                                       for s in ss]) for f in FL}
            mond[fee][pr] = {f: [summ(list(x)) for x in zip(*[np.subtract(M[(a, fee, s)][f], M[(b, fee, s)][f]) for s in ss])]
                             for f in ("roi_m", "roi_q")}
            boo[fee][pr] = boot(ED, a, b, fee, ss)
    RL = {fee: rules(M, fee, ok) for fee in FEES}
    months = [x.strftime("%Y-%m") for x in pd.date_range(W["D0"], periods=W["ND"], freq="D") if x.is_month_end]
    js = dict(prereg="docs/prereg/PREREG_HOLDOUT2026H1.md 35d03784 + 0e3282a6 + 1682a311/2691816d/8fe35b23", scorer="A",
              defs="docs/result/ho26/score_A_defs.md", defs_commit=A_.defs_commit, dry=W["dry"],
              window=[w0, w1, W["ND"]], parity={par[k]["tag"] + ("" if not W["dry"] else "|%s|%s" % k[:2]): par[k] for k in par},
              valid={"%s|%s" % (c, f): [s for s in SEEDS if ok[(c, f, s)]] for c in CFGS for f in FEES},
              metrics={"%s|%s|%d" % k: M[k] for k in M}, agg=agg, ratio_dev=rdev, delta=delta, rules=RL, boot=boo,
              months=months, monthly=mon, monthly_delta=mond, selfcheck=sc, notes=A_.note,
              rule_inputs={"%s|s|%d" % (c, s): {f: M[(c, "s", s)][f] for f in ("n", "sum_pnl", "maxdd")}
                           for c in CFGS for s in SEEDS if (c, "s", s) in M})
    jo, mo = (WD + "/dryrun.json", WD + "/dryrun.md") if W["dry"] else (JSON_OUT, MD_OUT)
    os.makedirs(os.path.dirname(jo), exist_ok=True)
    json.dump(js, open(jo, "w"), indent=1, default=jd)
    write_md(json.loads(json.dumps(js, default=jd)), mo)
    log.info("XONG -> %s | E0 %s H-A %s H-B %s (s) | selfcheck final max %s bad %s", jo, RL["s"]["E0"]["ok"], RL["s"]["H-A"]["ok"],
             RL["s"]["H-B"]["ok"], sc["final_max_abs_pct"], sc["final_bad"])


if __name__ == "__main__":
    main()
