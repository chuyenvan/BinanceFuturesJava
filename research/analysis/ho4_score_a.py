#!/usr/bin/env python3
"""HO4_SCORE_A (2026-10-12): SCORER A holdout HO4 (Vision), 2026-01-01 -> 09-30 +07; cua so W9/H1/Q3; cfg b0/k24.

Pre-reg docs/prereg/PREREG_HOLDOUT2026H1.md §1 + ADD-5 31e3c9e7 + ADD-6 af6d6c94 (§6.2a 923d7643, 95da70a9)
+ ADD-7 106dd923 (§7.5 0b798c10). Dinh nghia docs/result/ho4/score_A_defs.md (commit TRUOC khi doc printDone/equity
2026 cua ho4-*). Luat KHONG doi. Thuoc = ho26_score_a (n theo start, SumPnL theo end, equity MTM phut).
Gia MTM = close 1m Binance Vision futures/um (nguon ticker sim HO4; ticker file khong con tren Oracle).
0 sim, 0 Kaggle, 0 Java, 0 cham 242.
Usage: python3 research/analysis/ho4_score_a.py [--dry] [--defs-commit H] [--note TXT]
  --dry: chay thu tren ho26-{b0,k24}-s-s* (so HO26 da cong bo), chi cua so H1; KHONG doc ho4-*.
"""
import argparse
import hashlib
import io
import json
import logging
import math
import os
import re
import sys
import time
import urllib.error
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import pandas as pd
from scipy import stats

REPO = "/home/ubuntu/src/BinanceFuturesJava"
sys.path.insert(0, REPO + "/research/analysis")
import nsel_score_b as B  # noqa: E402

log = logging.getLogger("ho4_score_a")
OUT = "/home/ubuntu/kaggle_sim/out/"
WD = "/home/ubuntu/claude_master/1012/ho4sa_wd"
PX = WD + "/ho4sa_px"
LOCK = "/home/ubuntu/claude_master/1002/oracle_heavy.lock"
Q4 = "/home/ubuntu/claude_master/1011/ho4p1/q/queue_status.tsv"
Q26 = "/home/ubuntu/claude_master/1009/ho26/queue_status.tsv"
EXCL = REPO + "/docs/result/ho4/ho4p1_excl26.json"
HO26A = REPO + "/docs/result/ho26/HO26_RESULT_A.json"
JSON_OUT = REPO + "/docs/result/ho4/HO4_RESULT_A.json"
MD_OUT = REPO + "/docs/result/ho4/HO4_RESULT_A.md"
VB = "https://data.binance.vision/data/futures/um/"
SEEDS = [42, 7, 13, 21, 99, 123, 777, 2024]
CFGS = ["b0", "k24"]
JAR, PEN = "b7c89f09", 0.01675
TZ_MS = B.TZ_MS
NREP, BSEED, BLOCK = 5000, 20261012, 10
INFL = math.sqrt(2.0 * math.log(3))
EP_GAP = 3
SQ = math.sqrt(365.0)
DEV_REF = dict(sharpe=1.80, cagr=27.6, maxdd=-22.9)
WINS = dict(W9=("2026-01-01 00:00", "2026-10-01 00:00"), H1=("2026-01-01 00:00", "2026-07-01 00:00"),
            Q3=("2026-07-01 00:00", "2026-10-01 00:00"))
TAILP = ["2025-12"] + ["2026-%02d" % m for m in range(1, 10)] + ["2026-10-01", "2026-10-02", "2026-10-03"]
FL = ["n", "sum_pnl", "roi", "maxdd", "sharpe", "sortino", "cagr_ann", "pct_day_entry", "n_ep", "pct_time_pos"]
RX_UPD = re.compile(r"Update (\d{8} \d{2}:\d{2}) => b:\s*(-?\d+).*?unP:\s*(-?\d+)")
W = {}


def ms_local(s):
    """'2026-01-01 00:00' (+07) -> ms UTC."""
    return int(pd.Timestamp(s).value // 10 ** 6) - TZ_MS


def tagf(cfg, fee, s):
    if W["dry"]:
        assert fee == "s"
        return "ho26-%s-s-s%d" % (cfg, s)
    return "ho4-%s-%s-s%d" % (cfg, fee, s)


def tmin(m):
    return str(pd.Timestamp(W["T0"] + int(m) * 60000 + TZ_MS, unit="ms"))[:16]


def md5f(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for ch in iter(lambda: f.read(1 << 20), b""):
            h.update(ch)
    return h.hexdigest()


def queue(path):
    q = {}
    if os.path.exists(path):
        for ln in open(path).read().splitlines()[1:]:
            f = ln.split("\t")
            if len(f) >= 5:
                q[f[0].strip()] = dict(status=f[1].strip(), md5=f[2].strip(), n=f[3].strip(), parity=f[4].strip())
    return q


def updates(tag):
    """dong 'Update YYYYMMDD HH:MM => b: unP:' trong sim.out -> list (key, ms UTC, b+unP), dedupe giu dong cuoi."""
    rows = {}
    with open(OUT + tag + "/logs/sim.out", errors="ignore") as f:
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
    q = Q.get(t, {})
    k24 = cfg == "k24"
    sf = ov_get(ov, "GATE_QUOTA_SKIP_WHEN_FULL")
    chk = dict(ok=rj.get("ok") is True, n=rj.get("n_trades") == nrows,
               queue=q.get("status") == "COMPLETE" and q.get("parity") == "PASS", md5_queue=q.get("md5") == md5,
               jar=str(rj.get("jar_sha256")).startswith(JAR),
               topk=ov_get(ov, "SELECTOR_RANK_TOPK") == "24" if k24 else ov_get(ov, "SELECTOR_RANK_TOPK") in ("", "16"),
               skipfull=(sf == "true") if k24 else sf in ("", "false"),
               nsel=ov_get(ov, "NSEL_ADD_ENABLED") in ("", "false"),
               pen=abs(pen_of(ov) - PEN) < 1e-12 if fee == "s" else pen_of(ov) == 0.0,
               date_last=str(rj.get("date_last")) >= W["DL"])
    res = dict(tag=t, ok=bool(all(chk.values())), checks=chk, md5=md5, n=rj.get("n_trades"), nrows=nrows,
               eq_final=rj.get("equity_final"), eq_start=rj.get("equity_start"), date_last=rj.get("date_last"))
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


def vfile(sym, per):
    return "%s/%s_%s.npz" % (PX, sym, per)


def fetch(job):
    """tai 1 file klines 1m Vision (monthly YYYY-MM / daily YYYY-MM-DD), kiem sha256 .CHECKSUM, luu (ot, close, qv)."""
    sym, per = job
    fn = vfile(sym, per)
    if os.path.exists(fn):
        return sym, per, "cache"
    if os.path.exists(fn + ".404"):
        return sym, per, "404"
    url = VB + "%s/klines/%s/1m/%s-1m-%s.zip" % ("monthly" if len(per) == 7 else "daily", sym, sym, per)
    for k in range(4):
        try:
            raw = urllib.request.urlopen(url, timeout=120).read()
            ck = urllib.request.urlopen(url + ".CHECKSUM", timeout=60).read().decode().split()[0]
            if hashlib.sha256(raw).hexdigest() != ck:
                raise ValueError("sha256 lech")
            z = zipfile.ZipFile(io.BytesIO(raw))
            v = pd.read_csv(z.open(z.namelist()[0]), header=None, usecols=[0, 4, 7], dtype=str)
            v = v.apply(pd.to_numeric, errors="coerce").dropna()
            ot = v[0].to_numpy(np.float64).astype(np.int64)
            ot = np.where(ot > 10 ** 14, ot // 1000, ot)
            np.savez(fn + ".tmp.npz", ot=ot, c=v[4].to_numpy(np.float64), qv=v[7].to_numpy(np.float64), sha=ck)
            os.replace(fn + ".tmp.npz", fn)
            return sym, per, "ok"
        except urllib.error.HTTPError as ex:
            if ex.code == 404:
                open(fn + ".404", "w").close()
                return sym, per, "404"
            time.sleep(5 * (k + 1))
        except Exception as ex:  # noqa: BLE001
            log.info("fetch %s %s lan %d loi %s", sym, per, k, ex)
            time.sleep(5 * (k + 1))
    return sym, per, "fail"


def per_of(day):
    """ngay UTC 'YYYYMMDD' -> file Vision: monthly neu thang <= 2026-09, daily neu sau."""
    return "%s-%s" % (day[:4], day[4:6]) if day[:6] <= "202609" else "%s-%s-%s" % (day[:4], day[4:6], day[6:])


def tail_cut(sym):
    """duoi settle (ADD-6 §6.2-2): chuoi quote_volume == 0 keo toi kline cuoi, >= 1440 phut -> ms phut dau chuoi."""
    ot, qv = [], []
    for p in TAILP:
        if os.path.exists(vfile(sym, p)):
            z = np.load(vfile(sym, p))
            ot.append(z["ot"])
            qv.append(z["qv"])
    if not ot:
        return None
    ot, qv = np.concatenate(ot), np.concatenate(qv)
    o = np.argsort(ot, kind="stable")
    ot, qv = ot[o], qv[o]
    nz = np.nonzero(qv != 0)[0]
    st = int(nz[-1]) + 1 if len(nz) else 0
    return int(ot[st]) if len(ot) - st >= 1440 else None


def build(tags, D, workers):
    """U[run, m] = unrealized MTM phut tren truc [T0, T0 + NE) (= nsel_score_b.work, gia = close 1m Vision)."""
    R, NE = len(tags), W["NE"]
    d0 = pd.Timestamp(W["T0"], unit="ms").normalize()
    d0ms = int(d0.value // 10 ** 6)
    nday = int((W["T0"] + NE * 60000 - 1 - d0ms) // 86400000) + 1
    days = [x.strftime("%Y%m%d") for x in pd.date_range(d0, periods=nday, freq="D")]
    off = int((W["T0"] - d0ms) // 60000)
    legs = pd.concat([D[t].assign(run=i)[["run", "sym_t", "entry", "q", "s", "e"]] for i, t in enumerate(tags)])
    legs = legs[(legs["e"] > legs["s"]) & (legs["s"] < NE) & (legs["e"] > 0)]
    settle = set(json.load(open(EXCL))["settle_tail_symbols"])
    need = {}
    for sym, g in legs.groupby("sym_t"):
        ps = set()
        for a, b in zip(np.maximum(g["s"].to_numpy(), 0), np.minimum(g["e"].to_numpy(), NE)):
            for di in range((off + int(a)) // 1440, (off + int(b) - 1) // 1440 + 1):
                ps.add(per_of(days[di]))
        need[sym] = ps
    jobs = sorted({(s, p) for s, ps in need.items() for p in ps} | {(s, p) for s in need if s in settle for p in TAILP})
    log.info("gia Vision: %d symbol, %d file (gom duoi settle)", len(need), len(jobs))
    st = {}
    t0 = time.time()
    with ThreadPoolExecutor(workers) as ex:
        for i, (s_, p_, r_) in enumerate(ex.map(fetch, jobs)):
            st[(s_, p_)] = r_
            if i % 300 == 0:
                log.info("tai %d/%d %.0fs", i, len(jobs), time.time() - t0)
    cnt = {k: int(sum(1 for v in st.values() if v == k)) for k in ("ok", "cache", "404", "fail")}
    U = np.zeros((R, NE))
    chk = dict(miss=0, legmin=0, nofile=0, nosym=0, tail_legmin=0, days=nday, day0=days[0], day1=days[-1],
               n_sym=len(need), n_files=len(jobs), fetch=cnt, nofile_list=[], tail={})
    for sym, g in legs.groupby("sym_t"):
        P = np.full(nday * 1440, np.nan)
        for p in sorted(need[sym]):
            if not os.path.exists(vfile(sym, p)):
                chk["nofile"] += 1
                chk["nofile_list"].append("%s_%s" % (sym, p))
                continue
            z = np.load(vfile(sym, p))
            i = (z["ot"] - d0ms) // 60000
            k = (i >= 0) & (i < len(P))
            P[i[k]] = z["c"][k]
        ci = None
        if sym in settle:
            cut = tail_cut(sym)
            if cut is not None:
                ci = int((cut - d0ms) // 60000)
                P[max(ci, 0):] = np.nan
                chk["tail"][sym] = str(pd.Timestamp(cut, unit="ms"))[:16] + " UTC"
        A = P.reshape(nday, 1440)
        dayall = np.isnan(A).all(axis=1)
        ii = np.where(np.isnan(A), 0, np.arange(1440)[None, :])
        np.maximum.accumulate(ii, axis=1, out=ii)
        A = A[np.arange(nday)[:, None], ii].ravel()
        touched = np.zeros(nday, bool)
        for r, en, q, s, e in zip(g["run"].to_numpy(), g["entry"].to_numpy(float), g["q"].to_numpy(float),
                                  g["s"].to_numpy(), g["e"].to_numpy()):
            a, b = max(int(s), 0), min(int(e), NE)
            pr = A[off + a: off + b]
            nn = np.isnan(pr)
            chk["miss"] += int(nn.sum())
            chk["legmin"] += int(b - a)
            U[r, a:b] += q * (np.where(nn, en, pr) - en)
            touched[(off + a) // 1440:(off + b - 1) // 1440 + 1] = True
            if ci is not None:
                chk["tail_legmin"] += int(max(0, b - max(a, ci - off)))
        chk["nosym"] += int((dayall & touched).sum())
    log.info("MTM xong: %s", {k: v for k, v in chk.items() if k not in ("nofile_list", "tail")})
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


def metr(d, eq, wk):
    """chi so 1 run tren cua so wk (= ho26_score_a.metr, dich goc ve dau cua so) + do tap trung."""
    off, NW, ND, D0 = W["win"][wk]
    ew = eq[off:off + NW]
    e0 = float(ew[0])
    s, e = d["s"].to_numpy() - off, d["e"].to_numpy() - off
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
    days = pd.date_range(D0, periods=ND, freq="D")
    mid = np.asarray((days.year - days[0].year) * 12 + days.month - days[0].month)
    nmon = int(mid.max()) + 1
    me = np.nonzero(np.asarray(days.is_month_end))[0]
    Em = Ed[me]
    roi_m = 100 * (Em / np.concatenate([[e0], Em[:-1]]) - 1.0)
    Eq = Ed[me[2::3]]
    roi_q = 100 * (Eq / np.concatenate([[e0], Eq[:-1]]) - 1.0)
    de, dc = s[ins] // 1440, e[inse] // 1440
    n_m = np.bincount(mid[de], minlength=nmon)
    pnl_m = np.bincount(mid[dc], weights=pnl[inse], minlength=nmon)
    has = np.bincount(de, minlength=ND) > 0
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
    dE = np.diff(np.concatenate([[e0], Ed]))
    srt = np.sort(dE)[::-1]
    net, pos = float(Ed[-1] - e0), float(dE[dE > 0].sum())
    conc = dict(net_mtm=net, pos_sum=pos, top1_day=str(days[int(np.argmax(dE))].date()))
    for kk in (1, 3, 5):
        tk = float(np.clip(srt[:kk], 0, None).sum())
        conc["top%d" % kk] = tk
        conc["top%d_net" % kk] = tk / net if net > 0 else None
        conc["top%d_pos" % kk] = tk / pos if pos > 0 else None
    m = dict(n=int(ins.sum()), sum_pnl=float(pnl[inse].sum()), n_close=int(inse.sum()),
             roi=100 * (float(ew[-1]) / e0 - 1.0), maxdd=100 * float(dd.min()), dd_peak=tmin(p + off),
             dd_trough=tmin(t + off), sharpe=float(r.mean()) / sd * SQ if sd > 0 else None,
             sortino=float(r.mean()) / dn * SQ if dn > 0 else None, vol=100 * sd * SQ, worst_day=100 * float(r.min()),
             best_day=100 * float(r.max()), cagr_ann=100 * cagr, eq0=e0, eq1=float(ew[-1]),
             roi_m=[float(v) for v in roi_m], n_m=[int(v) for v in n_m], pnl_m=[float(v) for v in pnl_m],
             roi_q=[float(v) for v in roi_q], pct_day_entry=100 * float(has.mean()), n_ep=n_ep,
             ep_trades_mean=float(ep_n.mean()), ep_len_mean=ep_len, gap_max=int(gl.max()) if len(gl) else 0,
             pct_time_pos=100 * float(inp.mean()), open_at_end=int(((s < NW) & (e >= NW)).sum()),
             open_at_start=int(((s < 0) & (e >= 0)).sum()), conc=conc)
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


def pdstr(t):
    x = pd.read_csv(OUT + t + "/storage/printDone.csv", index_col=False, dtype=str, keep_default_na=False)
    x.columns = [c.strip() for c in x.columns]
    for c in x.columns:
        x[c] = x[c].astype(str).str.strip()
    return x


def devcheck():
    """phan truoc 2026 cua ho4-k24-s-s42 vs ho26-k24-s-s42 (cung cau hinh; dau vao DEV trung byte)."""
    th, td = "ho4-k24-s-s42", "ho26-k24-s-s42"
    uh, ud = {k: v for k, _, v in updates(th)}, {k: v for k, _, v in updates(td)}
    com = sorted(k for k in set(uh) & set(ud) if k[:8] <= "20251231")
    df = [abs(uh[k] - ud[k]) for k in com]
    r = dict(pair=[th, td], n_upd_common=len(com), n_upd_diff=int(sum(x > 0 for x in df)),
             max_abs_diff=float(max(df)) if df else None, first_diff=next((k for k in com if uh[k] != ud[k]), None),
             last_common=com[-1] if com else None, last_ho4=uh.get(com[-1]) if com else None,
             last_ho26=ud.get(com[-1]) if com else None)
    ph, pv = pdstr(th), pdstr(td)
    cc = [c for c in pv.columns if c in ph.columns]
    cut = "20260101 00:00"
    a = ph.loc[ph["end"] < cut, cc].agg("|".join, axis=1).value_counts()
    b = pv.loc[pv["end"] < cut, cc].agg("|".join, axis=1).value_counts()
    al = a.reindex(a.index.union(b.index), fill_value=0)
    bl = b.reindex(a.index.union(b.index), fill_value=0)
    oa = set(ph.loc[(ph["start"] < cut) & (ph["end"] >= cut), "sym"] + "|" + ph.loc[(ph["start"] < cut) & (ph["end"] >= cut), "start"])
    ob = set(pv.loc[(pv["start"] < cut) & (pv["end"] >= cut), "sym"] + "|" + pv.loc[(pv["start"] < cut) & (pv["end"] >= cut), "start"])
    r.update(cut_end=cut, cols=len(cc), n_ho4=int(a.sum()), n_ho26=int(b.sum()),
             only_ho4=int((al - bl).clip(lower=0).sum()), only_ho26=int((bl - al).clip(lower=0).sum()),
             open_at_cut=[len(oa), len(ob)], open_at_cut_same=oa == ob)
    r["ok"] = r["n_upd_diff"] == 0 and r["only_ho4"] == 0 and r["only_ho26"] == 0 and r["open_at_cut_same"]
    log.info("DEVCHECK %s", r)
    return r


def match(a, b):
    """ghep 1-1 tham lam theo thoi gian, cung sym, |dstart| <= 1 phut."""
    n = 0
    gb = {k: np.sort(v.to_numpy()) for k, v in b.groupby("sym")["ts"]}
    for k, v in a.groupby("sym")["ts"]:
        x, y = np.sort(v.to_numpy()), gb.get(k)
        if y is None:
            continue
        i = j = 0
        while i < len(x) and j < len(y):
            if abs(int(x[i]) - int(y[j])) <= 60000:
                n, i, j = n + 1, i + 1, j + 1
            elif x[i] < y[j]:
                i += 1
            else:
                j += 1
    return n


def sens(D):
    """do nhay du lieu H1: HO4 (Vision) vs HO26 (242), cung cfg/seed, ban stress."""
    T0, T1 = ms_local(WINS["H1"][0]), ms_local(WINS["H1"][1])
    ref = json.load(open(HO26A))["metrics"] if os.path.exists(HO26A) else {}
    out = {}
    for c in CFGS:
        rows = []
        for s in SEEDS:
            t4, t6 = "ho4-%s-s-s%d" % (c, s), "ho26-%s-s-s%d" % (c, s)
            if t4 not in D or not os.path.exists(OUT + t6 + "/storage/printDone.csv"):
                continue
            rj6 = json.load(open(OUT + t6 + "/result.json"))
            d6, _ = load(t6)
            x = {}
            for k_, d in (("ho4", D[t4]), ("ho26", d6)):
                st_, en_ = d["ts"].to_numpy(), d["te"].to_numpy()
                x[k_] = (int(((st_ >= T0) & (st_ < T1)).sum()), float(d["pnl"].to_numpy(float)[(en_ >= T0) & (en_ < T1)].sum()))
            a = D[t4][(D[t4]["ts"] >= T0) & (D[t4]["ts"] < T1)]
            b = d6[(d6["ts"] >= T0) & (d6["ts"] < T1)]
            nm = match(a, b)
            rf = ref.get("%s|s|%d" % (c, s), {})
            refok = rf.get("n") == x["ho26"][0] and abs(float(rf.get("sum_pnl", 1e18)) - x["ho26"][1]) <= 1e-6 * max(1.0, abs(x["ho26"][1]))
            rows.append(dict(seed=s, ok26=rj6.get("ok") is True, n4=x["ho4"][0], n26=x["ho26"][0], dn=x["ho4"][0] - x["ho26"][0],
                             pnl4=x["ho4"][1], pnl26=x["ho26"][1], dpnl=x["ho4"][1] - x["ho26"][1], nmatch=nm,
                             overlap=100.0 * nm / max(1, len(a), len(b)), ref26_n=rf.get("n"), ref26_pnl=rf.get("sum_pnl"), ref_ok=bool(refok)))
        out[c] = dict(rows=rows, mean_dn=float(np.mean([r["dn"] for r in rows])) if rows else None,
                      mean_dpnl=float(np.mean([r["dpnl"] for r in rows])) if rows else None,
                      mean_overlap=float(np.mean([r["overlap"] for r in rows])) if rows else None,
                      mean_pnl4=float(np.mean([r["pnl4"] for r in rows])) if rows else None,
                      mean_pnl26=float(np.mean([r["pnl26"] for r in rows])) if rows else None,
                      npos_dpnl=int(sum(r["dpnl"] > 0 for r in rows)), ref_ok=all(r["ref_ok"] for r in rows))
        log.info("SENS %s %s", c, {k: v for k, v in out[c].items() if k != "rows"})
    return out


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


def boot(X, seeds):
    """block-10d tren X[seed, ngay]; stat = mean_s sum_d X."""
    X = np.asarray(X, float)
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


def rules(M, fee, ok, wk):
    def v(c, s, f):
        return M[(c, fee, s, wk)][f]
    sE = [s for s in SEEDS if ok.get(("k24", fee, s))]
    sA = [s for s in SEEDS if ok.get(("k24", fee, s)) and ok.get(("b0", fee, s))]
    pe = [v("k24", s, "sum_pnl") for s in sE]
    npe = int(sum(x > 0 for x in pe))
    r = dict(E0=dict(seeds=sE, mean_sum_pnl=float(np.mean(pe)) if pe else None, n_pos=npe, vals=pe,
                     thr="mean SumPnL_S(k24) > 0 VA >= 6/8 seed > 0", ok=bool(pe and np.mean(pe) > 0 and npe >= 6)))
    dP = [v("k24", s, "sum_pnl") - v("b0", s, "sum_pnl") for s in sA]
    dD = [v("k24", s, "maxdd") - v("b0", s, "maxdd") for s in sA]
    r["H-A"] = dict(seeds=sA, mean_dpnl=float(np.mean(dP)) if dP else None, mean_ddd=float(np.mean(dD)) if dD else None,
                    dpnl=dP, ddd=dD, thr="mean dSumPnL_S >= 0 VA mean dmaxDD >= -5pp",
                    ok=bool(dP and np.mean(dP) >= 0 and np.mean(dD) >= -5.0))
    return r


def lomo(M, fee, wk, ss, months):
    rows = []
    for j, mo in enumerate(months):
        vk = [M[("k24", fee, s, wk)]["sum_pnl"] - M[("k24", fee, s, wk)]["pnl_m"][j] for s in ss]
        vb = [M[("b0", fee, s, wk)]["sum_pnl"] - M[("b0", fee, s, wk)]["pnl_m"][j] for s in ss]
        dv = np.subtract(vk, vb)
        rows.append(dict(month=mo, n=len(ss), k24_mean=float(np.mean(vk)), k24_npos=int(sum(x > 0 for x in vk)),
                         d_mean=float(np.mean(dv)), d_npos=int((dv > 0).sum())))
    return dict(rows=rows, min_k24_npos=min(r["k24_npos"] for r in rows), min_k24_mean=min(r["k24_mean"] for r in rows),
                min_d_mean=min(r["d_mean"] for r in rows))


def fm(x, nd=2, sign=False):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "—"
    return ((("%+." if sign else "%.") + str(nd) + "f") % x).replace(".", ",")


def mmm(x, nd=2):
    if x is None:
        return "—"
    return "%s [%s..%s]" % (fm(x["mean"], nd), fm(x["min"], nd), fm(x["max"], nd))


def write_md(js, path):
    o = ["# HO4 — KẾT QUẢ CHẤM SCORER A — holdout Vision 2026-01-01 → 09-30 (W9 / H1 / Q3)", "",
         "Pre-reg `docs/prereg/PREREG_HOLDOUT2026H1.md` §1 + ADD-5 31e3c9e7 + ADD-6 af6d6c94 (§6.2a 923d7643, 95da70a9) + "
         "ADD-7 106dd923 (§7.5 0b798c10). Định nghĩa `docs/result/ho4/score_A_defs.md` + script "
         "`research/analysis/ho4_score_a.py` commit %s TRƯỚC khi đọc printDone/equity 2026 của ho4-*. "
         "JSON `docs/result/ho4/HO4_RESULT_A.json`. Bản CHÍNH = stress `-s-`; `-b-` = phí gốc (mô tả). "
         "Giá MTM = close 1m Binance Vision. 0 sim / Kaggle / Java / 242. Chấm 1 lần; luật không đổi." % js["defs_commit"], ""]
    o += ["## 1. Verdict", "", "| fee | cửa sổ | E0 | k24 mean ΣPnL | seed > 0 | H-A | mean ΔΣPnL (k24−b0) | mean ΔmaxDD pp |",
          "|---|---|---|---|---|---|---|---|"]
    for fee in js["fees"]:
        for wk in js["wins"]:
            e, a = js["rules"][fee][wk]["E0"], js["rules"][fee][wk]["H-A"]
            o.append("| %s | %s | %s | %s | %d/%d | %s | %s | %s |" % (
                fee, wk, "PASS" if e["ok"] else "FAIL", fm(e["mean_sum_pnl"], 0), e["n_pos"], len(e["seeds"]),
                "XÁC NHẬN" if a["ok"] else "KHÔNG xác nhận", fm(a["mean_dpnl"], 0, True), fm(a["mean_ddd"], 2, True)))
    o += ["", "Ngưỡng: E0 mean ΣPnL_S(k24) > 0 VÀ ≥ 6/8 seed > 0; H-A mean ΔΣPnL_S ≥ 0 VÀ mean ΔmaxDD ≥ −5pp. "
          "Fee b chỉ mô tả. Q3 = xác nhận mù duy nhất; H1/W9 không độc lập với HO26 (đã nhìn).", ""]
    o += ["## 2. Bảng cfg × cửa sổ (mean [min..max] qua seed)", "",
          "| cửa sổ | fee | cfg | seed | n | ΣPnL | ROI % | maxDD % | Sharpe | Sortino | CAGR năm hoá % | % ngày có lệnh | % t có vị thế |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for wk in js["wins"]:
        for fee in js["fees"]:
            for c in CFGS:
                A = js["agg"][fee][wk].get(c)
                if A:
                    o.append("| %s | %s | %s | %d | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
                        wk, fee, c, A["n"]["n"], mmm(A["n"], 0), mmm(A["sum_pnl"], 0), mmm(A["roi"]), mmm(A["maxdd"]),
                        mmm(A["sharpe"]), mmm(A["sortino"]), mmm(A["cagr_ann"], 1), mmm(A["pct_day_entry"], 1),
                        mmm(A["pct_time_pos"], 1)))
    o += ["", "Tỉ lệ so DEV baseline stress (Sharpe 1,80 / CAGR 27,6% / maxDD −22,9%; mean qua seed, fee s):"]
    for wk in js["wins"]:
        o.append("- %s: " % wk + "; ".join("%s Sharpe %s, CAGR %s, maxDD %s" % (c, fm(x["sharpe"]), fm(x["cagr"]), fm(x["maxdd"]))
                                          for c, x in js["ratio_dev"][wk].items()))
    o += ["", "### 2.1 Từng seed (fee s)", "", "| cửa sổ | cfg | seed | n | ΣPnL | ROI % | maxDD % | Sharpe | E đầu | E cuối |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for wk in js["wins"]:
        for c in CFGS:
            for s in SEEDS:
                m = js["metrics"].get("%s|s|%d|%s" % (c, s, wk))
                if m:
                    o.append("| %s | %s | %d | %d | %s | %s | %s | %s | %s | %s |" % (
                        wk, c, s, m["n"], fm(m["sum_pnl"], 0), fm(m["roi"]), fm(m["maxdd"]), fm(m["sharpe"]),
                        fm(m["eq0"], 0), fm(m["eq1"], 0)))
    o += ["", "## 3. Δ ghép cặp k24 − b0 theo seed", "",
          "| cửa sổ | fee | trường | mean | sd | min | max | seed Δ>0 | cận dưới t95 | cận dưới inflate k=3 |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for wk in js["wins"]:
        for fee in js["fees"]:
            for f in FL:
                x = js["delta"][fee][wk].get(f)
                if x:
                    o.append("| %s | %s | %s | %s | %s | %s | %s | %d/%d | %s | %s |" % (
                        wk, fee, f, fm(x["mean"], 2, True), fm(x["sd"]), fm(x["min"], 2, True), fm(x["max"], 2, True),
                        x["npos"], x["n"], fm(x["lb"], 2, True), fm(x["lb_infl"], 2, True)))
    o += ["", "## 4. Bootstrap MTM ngày block-10d (NREP %d, seed %d)" % (NREP, BSEED), "",
          "Thống kê = mean qua seed của Σ ngày (USD): `k24` = E1 − E0 MTM của k24; `k24-b0` = Δ(E1 − E0).", "",
          "| cửa sổ | fee | thống kê | obs | CI95 raw | CI95 inflate | p5 | P(≤0) |", "|---|---|---|---|---|---|---|---|"]
    for wk in js["wins"]:
        for fee in js["fees"]:
            for nm, x in js["boot"][fee][wk].items():
                o.append("| %s | %s | %s | %s | [%s; %s] | [%s; %s] | %s | %s |" % (
                    wk, fee, nm, fm(x["obs"], 0, True), fm(x["ci_raw"][0], 0, True), fm(x["ci_raw"][1], 0, True),
                    fm(x["ci_infl"][0], 0, True), fm(x["ci_infl"][1], 0, True), fm(x["p5"], 0, True), fm(x["p_le0"], 4)))
    wm = js["wins"][0]
    mo, ql = js["months"][wm], js["qlab"][wm]
    o += ["", "## 5. Theo tháng (%s, fee s, mean qua seed)" % wm, "", "| | " + " | ".join(mo + ql) + " |",
          "|---|" + "---|" * (len(mo) + len(ql))]
    for c in CFGS:
        A = js["monthly"]["s"][wm].get(c)
        if A:
            o.append("| ROI %% %s | %s |" % (c, " | ".join([fm(x) for x in A["roi_m"]] + [fm(x) for x in A["roi_q"]])))
            o.append("| n %s | %s |%s" % (c, " | ".join(fm(x, 0) for x in A["n_m"]), " |" * len(ql)))
            o.append("| ΣPnL %s | %s |%s" % (c, " | ".join(fm(x, 0) for x in A["pnl_m"]), " |" * len(ql)))
    A = js["monthly_delta"]["s"].get(wm)
    if A:
        o.append("| ΔROI pp k24−b0 (seed>0) | %s |" % " | ".join(
            "%s (%d/%d)" % (fm(x["mean"], 2, True), x["npos"], x["n"]) for x in A["roi_m"] + A["roi_q"]))
    o += ["", "## 6. Độ tập trung (fee s, mean qua seed)", "",
          "| cửa sổ | cfg | E1−E0 MTM | top1/net | top3/net | top5/net | top1/Σngày dương | top3/Σ | top5/Σ |",
          "|---|---|---|---|---|---|---|---|---|"]
    for wk in js["wins"]:
        for c in CFGS:
            x = js["conc"][wk].get(c)
            if x:
                o.append("| %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
                    wk, c, fm(x["net_mtm"], 0), fm(x["top1_net"]), fm(x["top3_net"]), fm(x["top5_net"]),
                    fm(x["top1_pos"]), fm(x["top3_pos"]), fm(x["top5_pos"])))
    o += ["", "Leave-one-month-out (fee s; bỏ pnl các dòng end ∈ tháng bỏ):", "",
          "| cửa sổ | tháng bỏ | k24 mean ΣPnL | k24 seed > 0 | mean Δ(k24−b0) | seed Δ > 0 |", "|---|---|---|---|---|---|"]
    for wk in js["wins"]:
        for r in js["lomo"][wk]["rows"]:
            o.append("| %s | %s | %s | %d/%d | %s | %d/%d |" % (wk, r["month"], fm(r["k24_mean"], 0), r["k24_npos"], r["n"],
                                                             fm(r["d_mean"], 0, True), r["d_npos"], r["n"]))
    S = js.get("sens")
    if S:
        o += ["", "## 7. Độ nhạy dữ liệu H1: HO4 (Vision) − HO26 (kline 242), stress, cùng cfg/seed", "",
              "| cfg | seed | n HO4 | n HO26 | Δn | ΣPnL HO4 | ΣPnL HO26 | ΔΣPnL | trùng lệnh % |", "|---|---|---|---|---|---|---|---|---|"]
        for c in CFGS:
            for r in S[c]["rows"]:
                o.append("| %s | %d | %d | %d | %+d | %s | %s | %s | %s |" % (c, r["seed"], r["n4"], r["n26"], r["dn"], fm(r["pnl4"], 0),
                                                                          fm(r["pnl26"], 0), fm(r["dpnl"], 0, True), fm(r["overlap"], 1)))
            o.append("| %s | mean | | | %s | %s | %s | %s (%d/%d > 0) | %s |" % (
                c, fm(S[c]["mean_dn"], 1, True), fm(S[c]["mean_pnl4"], 0), fm(S[c]["mean_pnl26"], 0), fm(S[c]["mean_dpnl"], 0, True),
                S[c]["npos_dpnl"], len(S[c]["rows"]), fm(S[c]["mean_overlap"], 1)))
        o += ["", "Kiểm chéo n/ΣPnL HO26 tính lại == `HO26_RESULT_A.json`: %s." % (
            "TRÙNG" if all(S[c]["ref_ok"] for c in CFGS) else "LỆCH")]
    o += ["", "## 8. Tự kiểm", ""]
    sc = js["selfcheck"]
    o.append("- Equity cuối E(phút Update cuối của date_last) vs result.equity_final: max |lệch| = %s%% (ngưỡng 0,01%%), run vượt: %s." % (
        fm(sc["final_max_abs_pct"], 4), ", ".join(sc["final_bad"]) or "không"))
    o.append("- E(m) vs b+unP mọi dòng Update trong trục: max của max = %s%%, median của median = %s%%." % (
        fm(sc["upd_max_pct"], 4), fm(sc["upd_med_pct"], 4)))
    o.append("- n_trades result == số dòng printDone: %d/%d run; dòng printDone bỏ do NaN: %d." % (sc["n_ok"], sc["n_runs"], sc["dropped"]))
    mt = sc["mtm"]
    o.append("- Giá Vision: %d symbol, %d file (tải %s); phút-chân thiếu giá %d / %d (%s%%); file thiếu %d; (symbol, ngày) không giá %d; "
             "đuôi settle cắt %d symbol, phút-chân trong đuôi %d; trục %s → %s UTC." % (
                 mt["n_sym"], mt["n_files"], mt["fetch"], mt["miss"], mt["legmin"], fm(100.0 * mt["miss"] / max(1, mt["legmin"]), 4),
                 mt["nofile"], mt["nosym"], len(mt["tail"]), mt["tail_legmin"], mt["day0"], mt["day1"]))
    dv = sc.get("devcheck")
    if dv:
        o.append("- Phần trước 2026 `%s` vs `%s`: Update chung ≤ 20251231 %d dòng, lệch %d (max |Δ| %s, dòng lệch đầu %s); "
                 "equity Update chung cuối %s: HO4 %s / HO26 %s; printDone end < %s: HO4 %d, HO26 %d, chỉ HO4 %d, chỉ HO26 %d; "
                 "lệnh mở qua mốc %s, trùng %s → **%s**." % (
                     dv["pair"][0], dv["pair"][1], dv["n_upd_common"], dv["n_upd_diff"], fm(dv["max_abs_diff"], 0), dv["first_diff"],
                     dv["last_common"], fm(dv["last_ho4"], 0), fm(dv["last_ho26"], 0), dv["cut_end"], dv["n_ho4"], dv["n_ho26"],
                     dv["only_ho4"], dv["only_ho26"], dv["open_at_cut"], dv["open_at_cut_same"], "KHỚP" if dv["ok"] else "LỆCH"))
    if js.get("dry_cmp"):
        o.append("- DRY so HO26_RESULT_A (H1): %s" % json.dumps(js["dry_cmp"]["summary"]))
    o += ["", "## 9. Parity run", "", "| run | kết quả | md5 printDone | n | fail |", "|---|---|---|---|---|"]
    for t, p in js["parity"].items():
        if p.get("missing"):
            o.append("| %s | THIẾU | — | — | — |" % t)
        else:
            o.append("| %s | %s | %s | %s | %s |" % (t, "PASS" if p["ok"] else "FAIL", p["md5"][:8], p["n"],
                                                  ",".join(k for k, v in p["checks"].items() if not v) or "—"))
    o += ["", "## 10. Ghi chú diễn giải (khai trước)", "",
          "- R25/R19: H1 không mù (HO26 H1 đã nhìn trên dữ liệu 242); chỉ Q3 là xác nhận mù; R16: log paper 242 Q3 đã thấy.",
          "- R1/R13: forward test có nhiễm tầng thiết kế; 8 seed chỉ đo nhiễu model gate ⇒ rào cứng + dấu ghép cặp.",
          "- R17: model đông lạnh (gate cut 2026-01-01, net015 cut 2025-10-01, S1 cut 2025-12-31) — drift, đối xứng 2 cfg; không so mức tuyệt đối với DEV.",
          "- ADD-7: gate Q3 lệch từ 2026-07-10 do 8 id mapper trùng (sai lệch đã biết, trùng live trước sửa mapper)."]
    if js.get("notes"):
        o += ["", "Ghi chú sửa lỗi script sau commit defs (không đổi định nghĩa/luật): " + "; ".join(js["notes"])]
    open(path, "w", encoding="utf-8").write("\n".join(o) + "\n")


def jd(o):
    if isinstance(o, np.integer):
        return int(o)
    if isinstance(o, np.floating):
        return float(o)
    if isinstance(o, np.bool_):
        return bool(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    return str(o)


def mean_conc(xs):
    out = {}
    for f in ("net_mtm", "top1_net", "top3_net", "top5_net", "top1_pos", "top3_pos", "top5_pos"):
        v = [x[f] for x in xs if x.get(f) is not None]
        out[f] = float(np.mean(v)) if v else None
        out[f + "_n"] = len(v)
    out["top1_days"] = [x["top1_day"] for x in xs]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--defs-commit", default="?")
    ap.add_argument("--note", action="append", default=[])
    A_ = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s", stream=sys.stdout, force=True)
    os.makedirs(PX, exist_ok=True)
    W["dry"] = A_.dry
    fees = ["s"] if W["dry"] else ["s", "b"]
    wins = {"H1": WINS["H1"]} if W["dry"] else WINS
    W["DL"] = "20260630" if W["dry"] else "20260930"
    W["T0"] = min(ms_local(v[0]) for v in wins.values())
    W["NW"] = (max(ms_local(v[1]) for v in wins.values()) - W["T0"]) // 60000
    W["win"] = {k: (int((ms_local(a) - W["T0"]) // 60000), int((ms_local(b) - ms_local(a)) // 60000),
                    int((ms_local(b) - ms_local(a)) // 86400000), pd.Timestamp(a).normalize()) for k, (a, b) in wins.items()}
    log.info("truc T0 %s, %d phut; cua so %s; dry=%s", tmin(0), W["NW"], {k: v[:3] for k, v in W["win"].items()}, W["dry"])
    Q = queue(Q26 if W["dry"] else Q4)
    par = {(c, f, s): parity(c, f, s, Q) for c in CFGS for f in fees for s in SEEDS}
    ok = {k: v["ok"] for k, v in par.items()}
    keys = [k for k in par if ok[k]]
    tags = sorted({par[k]["tag"] for k in keys})
    log.info("run hop le %d/%d", len(keys), len(par))
    D, drop, UPS, RJ = {}, 0, {}, {}
    for t in tags:
        D[t], dr = load(t)
        drop += dr
        UPS[t] = updates(t)
        RJ[t] = json.load(open(OUT + t + "/result.json"))
    NE = W["NW"]
    for t in tags:
        ls = [u for u in UPS[t] if u[0][:8] == str(RJ[t].get("date_last"))]
        if ls:
            NE = max(NE, (ls[-1][1] - W["T0"]) // 60000 + 1)
    W["NE"] = int(min(NE, W["NW"] + 2 * 1440))
    log.info("truc MTM %d phut (cua so %d)", W["NE"], W["NW"])
    while os.path.exists(LOCK):
        log.info("cho lock %s", LOCK)
        time.sleep(60)
    U, mt = build(tags, D, A_.workers)
    ti = {t: i for i, t in enumerate(tags)}
    EQ = {t: equity(D[t], RJ[t]["equity_start"], U[ti[t]]) for t in tags}
    del U
    EC = {t: eqcheck(EQ[t], UPS[t], RJ[t]) for t in tags}
    M, ED = {}, {}
    for k in keys:
        for wk in wins:
            M[k + (wk,)], ED[k + (wk,)] = metr(D[par[k]["tag"]], EQ[par[k]["tag"]], wk)
            x = M[k + (wk,)]
            log.info("METR %-18s %s n=%d pnl=%.0f roi=%.2f dd=%.2f sh=%s", par[k]["tag"], wk, x["n"], x["sum_pnl"], x["roi"],
                     x["maxdd"], fm(x["sharpe"]))
    fin = {t: EC[t]["final_dev_pct"] for t in tags}
    sc = dict(final_max_abs_pct=max((abs(v) for v in fin.values() if v is not None), default=None),
              final_bad=[t for t in tags if not EC[t]["final_ok"]],
              upd_max_pct=max((EC[t]["max_pct"] for t in tags if EC[t]["max_pct"] is not None), default=None),
              upd_med_pct=float(np.median([EC[t]["med_pct"] for t in tags if EC[t]["med_pct"] is not None])) if tags else None,
              n_ok=int(sum(1 for k in par if not par[k].get("missing") and par[k]["checks"]["n"])), n_runs=len(par),
              dropped=int(drop), mtm=mt, eqcheck=EC, devcheck=None if W["dry"] else devcheck())
    agg, delta, mon, mond, boo, rdev, RL, conc, lom, months, qlab = {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}
    for wk in wins:
        off, NW_, ND_, D0 = W["win"][wk]
        dd_ = pd.date_range(D0, periods=ND_, freq="D")
        months[wk] = [x.strftime("%Y-%m") for x in dd_ if x.is_month_end]
        qlab[wk] = ["Q%d" % ((int(x[5:7]) - 1) // 3 + 1) for x in months[wk][2::3]]
    for fee in fees:
        agg[fee], mon[fee], delta[fee], mond[fee], boo[fee], RL[fee] = {}, {}, {}, {}, {}, {}
        for wk in wins:
            agg[fee][wk], mon[fee][wk] = {}, {}
            for c in CFGS:
                ss = [s for s in SEEDS if ok[(c, fee, s)]]
                agg[fee][wk][c] = {f: summ([M[(c, fee, s, wk)][f] for s in ss]) for f in FL} if ss else None
                if ss:
                    mon[fee][wk][c] = {f: [float(np.mean(x)) for x in zip(*[M[(c, fee, s, wk)][f] for s in ss])]
                                       for f in ("roi_m", "n_m", "pnl_m", "roi_q")}
                if fee == "s" and ss:
                    rdev.setdefault(wk, {})[c] = {f: float(np.mean([M[(c, fee, s, wk)]["ratio_dev"][f] for s in ss
                                                                    if M[(c, fee, s, wk)]["ratio_dev"][f] is not None]))
                                                  for f in ("sharpe", "cagr", "maxdd")}
                    conc.setdefault(wk, {})[c] = mean_conc([M[(c, fee, s, wk)]["conc"] for s in ss])
            ss = [s for s in SEEDS if ok[("k24", fee, s)] and ok[("b0", fee, s)]]
            sk = [s for s in SEEDS if ok[("k24", fee, s)]]
            delta[fee][wk] = {f: summ([(M[("k24", fee, s, wk)][f] - M[("b0", fee, s, wk)][f])
                                       if M[("k24", fee, s, wk)][f] is not None and M[("b0", fee, s, wk)][f] is not None else None
                                       for s in ss]) for f in FL} if ss else {}
            mond[fee][wk] = {f: [summ(list(x)) for x in zip(*[np.subtract(M[("k24", fee, s, wk)][f], M[("b0", fee, s, wk)][f])
                                                             for s in ss])] for f in ("roi_m", "roi_q")} if ss else None

            def de(c, s):
                e0, Ed = ED[(c, fee, s, wk)]
                return np.diff(np.concatenate([[e0], Ed]))
            boo[fee][wk] = {}
            if sk:
                boo[fee][wk]["k24"] = boot([de("k24", s) for s in sk], sk)
            if ss:
                boo[fee][wk]["k24-b0"] = boot([de("k24", s) - de("b0", s) for s in ss], ss)
            RL[fee][wk] = rules(M, fee, ok, wk)
            if fee == "s" and ss:
                lom[wk] = lomo(M, fee, wk, ss, months[wk])
    for fee in fees:
        for wk in wins:
            log.info("LUAT %s %s: E0 %s (mean %.0f, %d/%d) H-A %s (dP %.0f, dDD %.2f)", fee, wk, RL[fee][wk]["E0"]["ok"],
                     RL[fee][wk]["E0"]["mean_sum_pnl"] or 0, RL[fee][wk]["E0"]["n_pos"], len(RL[fee][wk]["E0"]["seeds"]),
                     RL[fee][wk]["H-A"]["ok"], RL[fee][wk]["H-A"]["mean_dpnl"] or 0, RL[fee][wk]["H-A"]["mean_ddd"] or 0)
    dry_cmp = None
    if W["dry"] and os.path.exists(HO26A):
        ref = json.load(open(HO26A))["metrics"]
        rows = {}
        for k in keys:
            rf, x = ref.get("%s|s|%d" % (k[0], k[2])), M[k + ("H1",)]
            if rf:
                rows["%s|%d" % (k[0], k[2])] = {f: (x[f] - rf[f]) if (x[f] is not None and rf.get(f) is not None) else None
                                                for f in ("n", "sum_pnl", "roi", "maxdd", "sharpe", "eq0", "eq1")}
        summary = {f: max((abs(v[f]) for v in rows.values() if v[f] is not None), default=None)
                   for f in ("n", "sum_pnl", "roi", "maxdd", "sharpe", "eq0", "eq1")}
        dry_cmp = dict(rows=rows, summary=summary)
        log.info("DRY so HO26_RESULT_A max|d|: %s", summary)
    js = dict(prereg="docs/prereg/PREREG_HOLDOUT2026H1.md §1 + ADD-5 31e3c9e7 + ADD-6 af6d6c94/923d7643/95da70a9 + ADD-7 106dd923/0b798c10",
              scorer="A", defs="docs/result/ho4/score_A_defs.md", defs_commit=A_.defs_commit, dry=W["dry"], fees=fees,
              wins=list(wins), win_def={k: [v[0], v[1], W["win"][k][2]] for k, v in wins.items()}, price_source="Binance Vision futures/um klines 1m close",
              parity={par[k]["tag"]: par[k] for k in par}, valid={"%s|%s" % (c, f): [s for s in SEEDS if ok[(c, f, s)]] for c in CFGS for f in fees},
              metrics={"%s|%s|%d|%s" % k: M[k] for k in M}, agg=agg, ratio_dev=rdev, delta=delta, rules=RL, boot=boo,
              months=months, qlab=qlab, monthly=mon, monthly_delta=mond, conc=conc, lomo=lom,
              sens=None if W["dry"] else sens(D), selfcheck=sc, dry_cmp=dry_cmp, notes=A_.note,
              rule_inputs={"%s|s|%d|%s" % (c, s, wk): {f: M[(c, "s", s, wk)][f] for f in ("n", "sum_pnl", "maxdd")}
                           for c in CFGS for s in SEEDS for wk in wins if (c, "s", s, wk) in M})
    jo, mo_ = (WD + "/ho4sa_dry.json", WD + "/ho4sa_dry.md") if W["dry"] else (JSON_OUT, MD_OUT)
    json.dump(js, open(jo, "w"), indent=1, default=jd)
    write_md(json.loads(json.dumps(js, default=jd)), mo_)
    log.info("XONG -> %s | selfcheck final max %s bad %s", jo, sc["final_max_abs_pct"], sc["final_bad"])


if __name__ == "__main__":
    main()
