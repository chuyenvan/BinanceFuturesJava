#!/usr/bin/env python3
"""HO4 scorer B (doc lap). Dinh nghia: docs/result/ho4/score_B_defs.md.
Lenh: fetch (tai Vision 1m cho chan can MTM) | score (cham + JSON/MD).
Khong import/doc scorer khac (ho26_score_*, nsel_score_a, ho4_score_a)."""
import argparse, hashlib, io, json, logging, os, re, sys, zipfile, time
import urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import numpy as np
import pandas as pd

LOG = logging.getLogger("ho4sb")
H = os.path.expanduser("~")
OUT = f"{H}/kaggle_sim/out"
QS = f"{H}/claude_master/1011/ho4p1/q/queue_status.tsv"
WD = f"{H}/claude_master/1012/ho4sb"
CACHE = f"{WD}/vision"
REPO = f"{H}/src/BinanceFuturesJava"
SEEDS = [42, 7, 13, 21, 99, 123, 777, 2024]
CFGS = ["b0", "k24"]
TZ7 = timezone(timedelta(hours=7))
EQ0 = 35000.0
MIN = 60000
DEV = {"sharpe": 1.80, "cagr": 0.276, "maxdd": -0.229}
NREP, BSEED, BLK, INFL = 5000, 20261012, 10, 1.482


def ms7(s):
    return int(datetime.strptime(s, "%Y%m%d %H:%M").replace(tzinfo=TZ7).timestamp() * 1000)


def d7(ms):
    return datetime.fromtimestamp(ms / 1000, TZ7)


G0 = ms7("20251231 00:00")
G1 = ms7("20261003 00:00")
NM = (G1 - G0) // MIN
WIN = {"W9": ("20260101 00:00", "20260930 23:59"),
       "H1": ("20260101 00:00", "20260630 23:59"),
       "Q3": ("20260701 00:00", "20260930 23:59")}


def md5f(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def queue_md5():
    m = {}
    with open(QS) as f:
        next(f)
        for ln in f:
            c = ln.rstrip("\n").split("\t")
            if len(c) >= 5 and c[4] == "PASS":
                m[c[0]] = c[2]
    return m


def run_dir(pre, cfg, fee, seed):
    return f"{OUT}/{pre}-{cfg}-{fee}-s{seed}"


def to_ms(col):
    t = pd.to_datetime(col, format="%Y%m%d %H:%M", errors="coerce")
    v = (t - pd.Timestamp("1970-01-01")) // pd.Timedelta(milliseconds=1)
    return v.astype("float64") - 7 * 3600 * 1000


def load_pd(d):
    df = pd.read_csv(f"{d}/storage/printDone.csv", dtype=str, keep_default_na=False)
    df = df[[c for c in df.columns if not c.startswith("Unnamed")]]
    out = pd.DataFrame({"sym": df["sym"], "side": df["side"], "status": df["status"]})
    for c in ["entry", "quantity", "margin", "pnl"]:
        out[c] = pd.to_numeric(df[c], errors="coerce")
    out["s"] = to_ms(df["start"])
    out["e"] = to_ms(df["end"])
    out["raw"] = df.astype(str).agg(",".join, axis=1)
    bad = int(out["s"].isna().sum() + out["e"].isna().sum() + out["pnl"].isna().sum())
    if bad:
        LOG.warning("%s: %d o start/end/pnl khong doc duoc", d, bad)
    return out


def vsym(s):
    return s if s.endswith("USDT") else s + "USDT"


def months_of(a, b):
    """thang UTC (YYYY-MM) giao [a,b) ms"""
    out, t = [], datetime.fromtimestamp(a / 1000, timezone.utc).replace(day=1, hour=0, minute=0)
    while t.timestamp() * 1000 < b:
        out.append(t.strftime("%Y-%m"))
        t = (t + timedelta(days=32)).replace(day=1)
    return out


VB = "https://data.binance.vision/data/futures/um"


def get_zip(url):
    for k in range(4):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as ex:
            if ex.code == 404:
                return None
            time.sleep(3 * (k + 1))
        except Exception:
            time.sleep(3 * (k + 1))
    raise RuntimeError("tai that bai " + url)


def parse_zip(b):
    z = zipfile.ZipFile(io.BytesIO(b))
    df = pd.read_csv(z.open(z.namelist()[0]), header=None, usecols=[0, 4], dtype=str)
    df = df[df[0].str.match(r"^\d+$")]
    t = df[0].astype("int64").to_numpy()
    t = np.where(t > 10 ** 14, t // 1000, t)  # phong khi micro-giay
    return t, df[4].astype("float64").to_numpy()


def fetch_one(sym, tag):
    p = f"{CACHE}/{sym}_{tag}.npz"
    if os.path.exists(p) or os.path.exists(p + ".none"):
        return tag, "cache"
    kind = "monthly" if len(tag) == 7 else "daily"
    b = get_zip(f"{VB}/{kind}/klines/{sym}/1m/{sym}-1m-{tag}.zip")
    if b is None:
        open(p + ".none", "w").close()
        return tag, "404"
    t, c = parse_zip(b)
    np.savez(p, t=t, c=c)
    return tag, "ok"


def days_of(a, b, month):
    out, t = [], datetime.fromtimestamp(a / 1000, timezone.utc).replace(hour=0, minute=0, second=0)
    while t.timestamp() * 1000 < b:
        if t.strftime("%Y-%m") == month:
            out.append(t.strftime("%Y-%m-%d"))
        t += timedelta(days=1)
    return out


def check_md5_all():
    qm, res = queue_md5(), {}
    for cfg in CFGS:
        for fee in "bs":
            for sd in SEEDS:
                slug = f"ho4-{cfg}-{fee}-s{sd}"
                m = md5f(f"{OUT}/{slug}/storage/printDone.csv")
                res[slug] = {"md5": m, "queue": qm.get(slug), "ok": m == qm.get(slug)}
    nok = sum(v["ok"] for v in res.values())
    LOG.info("md5 printDone khop queue_status: %d/32", nok)
    if nok != 32:
        raise SystemExit("md5 lech -> dung: " + str([k for k, v in res.items() if not v["ok"]]))
    return res


def need_spans():
    """(vsym -> list[(a,b)]) khoang can gia trong luoi G, tu 32 run ho4"""
    sp = {}
    for cfg in CFGS:
        for fee in "bs":
            for sd in SEEDS:
                df = load_pd(run_dir("ho4", cfg, fee, sd))
                e = df["e"].fillna(G1)
                m = (e >= G0) & (df["s"] < G1)
                for sym, s, ee in zip(df["sym"][m], df["s"][m], e[m]):
                    sp.setdefault(vsym(sym), []).append((max(s, G0), min(ee + MIN, G1)))
    return sp


def cmd_fetch(a):
    os.makedirs(CACHE, exist_ok=True)
    check_md5_all()
    sp = need_spans()
    jobs = set()
    for sym, lst in sp.items():
        for a0, b0 in lst:
            for mo in months_of(a0, b0):
                if mo == "2026-10":
                    jobs.update((sym, d) for d in days_of(a0, b0, mo))
                else:
                    jobs.add((sym, mo))
    LOG.info("symbol %d, job thang/ngay %d", len(sp), len(jobs))
    with ThreadPoolExecutor(8) as ex:
        rs = list(ex.map(lambda j: (j[0],) + fetch_one(*j), sorted(jobs)))
    miss = [(s, t) for s, t, st in rs if st == "404"]
    LOG.info("ok/cache %d, 404 %d", len(rs) - len(miss), len(miss))
    fb = set()
    for sym, mo in miss:
        if len(mo) == 7:
            for a0, b0 in sp[sym]:
                fb.update((sym, d) for d in days_of(a0, b0, mo))
    with ThreadPoolExecutor(8) as ex:
        rs2 = list(ex.map(lambda j: (j[0],) + fetch_one(*j), sorted(fb)))
    LOG.info("fallback daily: %d job, 404 %d", len(rs2), sum(st == "404" for _, _, st in rs2))
    json.dump({"symbols": len(sp), "jobs": len(jobs), "miss_monthly": miss,
               "fallback": [list(x) for x in rs2]}, open(f"{WD}/fetch_log.json", "w"))


PX = {}


def price(sym):
    if sym in PX:
        return PX[sym]
    a = np.full(NM, np.nan, dtype=np.float32)
    if os.path.isdir(CACHE):
        for fn in os.listdir(CACHE):
            if fn.startswith(sym + "_") and fn.endswith(".npz"):
                z = np.load(f"{CACHE}/{fn}")
                i = (z["t"] - G0) // MIN
                k = (i >= 0) & (i < NM)
                a[i[k]] = z["c"][k].astype(np.float32)
    raw = a.copy()
    a = pd.Series(a).ffill().to_numpy(dtype=np.float32)
    PX[sym] = (a, raw)
    return PX[sym]


def equity(df, stats):
    """E(m) tren luoi G (float64) + thong ke thieu gia"""
    e = df["e"].to_numpy()
    s = df["s"].to_numpy()
    pnl = df["pnl"].to_numpy()
    done = ~np.isnan(e)
    base = EQ0 + pnl[done & (e < G0)].sum()
    real = np.zeros(NM)
    ie = ((e[done & (e >= G0) & (e < G1)] - G0) // MIN).astype(int)
    np.add.at(real, ie, pnl[done & (e >= G0) & (e < G1)])
    unr = np.zeros(NM)
    ee = np.where(done, e, G1)
    m = (ee > G0) & (s < G1)
    for sym, si, ei, en, q, mg, sd in zip(df["sym"][m], s[m], ee[m], df["entry"][m],
                                          df["quantity"][m], df["margin"][m], df["side"][m]):
        a, raw = price(vsym(sym))
        i0 = int(max(0, (si - G0) // MIN))
        i1 = int(min(NM, (ei - G0) // MIN))
        if i1 <= i0:
            continue
        p = a[i0:i1].astype(np.float64)
        stats["leg_min"] += i1 - i0
        stats["miss_raw"] += int(np.isnan(raw[i0:i1]).sum())
        stats["miss_fill"] += int(np.isnan(p).sum())
        p = np.where(np.isnan(p), en, p)
        qq = q if q > 0 else mg / en
        unr[i0:i1] += (qq if sd != "SELL" else -qq) * (p - en)
    return base + np.cumsum(real) + unr


def idx(ms):
    return int((ms - G0) // MIN)


def day_ends(a_ms, b_ms):
    """chi so phut 23:59 +07 moi ngay trong [a,b]"""
    out, t = [], a_ms + 1439 * MIN
    while t <= b_ms:
        out.append(idx(t))
        t += 1440 * MIN
    return np.array(out)


def win_metrics(df, E, w):
    a_ms, b_ms = ms7(WIN[w][0]), ms7(WIN[w][1])
    ia, ib = idx(a_ms), idx(b_ms)
    e0, e1 = E[ia - 1], E[ib]
    path = np.concatenate([[e0], E[ia:ib + 1]])
    pk = np.maximum.accumulate(path)
    ins = (df["s"] >= a_ms) & (df["s"] <= b_ms)
    ine = (df["e"] >= a_ms) & (df["e"] <= b_ms)
    de = day_ends(a_ms, b_ms)
    ed = np.concatenate([[e0], E[de]])
    r = ed[1:] / ed[:-1] - 1
    nd = len(de)
    dn = np.sqrt(np.mean(np.minimum(r, 0) ** 2))
    sday = pd.Series(((df["s"][ins] - a_ms) // (1440 * MIN)).astype(int)).nunique()
    out = {"n": int(ins.sum()), "spnl": float(df["pnl"][ine].sum()), "e0": float(e0), "e1": float(e1),
           "roi": float(e1 / e0 - 1), "maxdd": float((path / pk - 1).min()),
           "sharpe": float(r.mean() / r.std(ddof=1) * np.sqrt(365)),
           "sortino": float(r.mean() / dn * np.sqrt(365)) if dn > 0 else None,
           "cagr": float((e1 / e0) ** (365 / nd) - 1), "days": nd, "pct_days_trade": sday / nd,
           "dP": (ed[1:] - ed[:-1]).tolist()}
    out["vs_dev"] = {"sharpe": out["sharpe"] / DEV["sharpe"], "cagr": out["cagr"] / DEV["cagr"],
                     "maxdd": out["maxdd"] / DEV["maxdd"]}
    dd = pd.Series(df["pnl"][ine].to_numpy(), index=((df["e"][ine] - a_ms) // (1440 * MIN)).astype(int).to_numpy())
    out["daily_pnl"] = dd.groupby(level=0).sum().reindex(range(nd), fill_value=0.0).tolist()
    return out


def monthly(df, E):
    out = {}
    for mo in range(1, 10):
        a = ms7(f"2026{mo:02d}01 00:00")
        b = (ms7(f"2026{mo + 1:02d}01 00:00") if mo < 12 else None) - MIN
        ins = (df["s"] >= a) & (df["s"] <= b)
        ine = (df["e"] >= a) & (df["e"] <= b)
        out[f"2026-{mo:02d}"] = {"n": int(ins.sum()), "spnl": float(df["pnl"][ine].sum()),
                                 "roi": float(E[idx(b)] / E[idx(a) - 1] - 1)}
    return out


UPD = re.compile(r"Update (\d{8} \d{2}:\d{2}) => b:\s*(-?\d+).*?unP:\s*(-?\d+)")


def upd_lines(d):
    out = []
    with open(f"{d}/logs/sim.out", errors="replace") as f:
        for ln in f:
            if "BudgetManagerSimple: Update" in ln:
                m = UPD.search(ln)
                if m:
                    out.append((m.group(1), int(m.group(2)), int(m.group(3))))
    return out


def eq_check(d, E, df):
    rj = json.load(open(f"{d}/result.json"))
    up = upd_lines(d)
    ef = float(rj["equity_final"])
    last = up[-1]
    rel = []
    for t, b, u in up:
        if t[:8] < "20260101":
            continue
        i = idx(ms7(t))
        if 0 < i < NM:
            v = b + u
            rel.append(min(abs(E[i] - v), abs(E[i - 1] - v)) / v)
    il = idx(ms7(last[0]))
    eb = min(abs(E[il] - ef), abs(E[il - 1] - ef)) / ef if 0 < il < NM else None
    return {"equity_final": ef, "last_upd": last[0], "last_b_unP": last[1] + last[2],
            "final_eq_bunp": abs(last[1] + last[2] - ef) <= 1, "mtm_vs_final_pct": None if eb is None else 100 * eb,
            "pass_001": eb is not None and 100 * eb <= 0.01, "sumpnl_vs_final_pct": 100 * ((EQ0 + df["pnl"].sum()) / ef - 1),
            "n_pd": len(df), "n_result": rj.get("n_trades"), "n_ok": len(df) == rj.get("n_trades"),
            "upd_n": len(rel), "upd_med_pct": 100 * float(np.median(rel)) if rel else None,
            "upd_max_pct": 100 * float(np.max(rel)) if rel else None, "date_last": rj.get("date_last")}


def pre2026():
    a, b = run_dir("ho4", "k24", "s", 42), run_dir("ho26", "k24", "s", 42)
    da, db = load_pd(a), load_pd(b)
    cut = ms7("20251231 23:59")
    ra = set(da["raw"][da["e"] <= cut]); rb = set(db["raw"][db["e"] <= cut])
    sa = set(da["raw"][da["s"] < cut + MIN]); sb = set(db["raw"][db["s"] < cut + MIN])
    ua = [x for x in upd_lines(a) if x[0][:8] <= "20251231"]
    ub = [x for x in upd_lines(b) if x[0][:8] <= "20251231"]
    first = next((i for i, (x, y) in enumerate(zip(ua, ub)) if x != y), None)
    onlya = sorted(sa - sb)[:3]; onlyb = sorted(sb - sa)[:3]
    return {"end_le_20251231": {"ho4": len(ra), "ho26": len(rb), "same": len(ra & rb),
                                "only_ho4": len(ra - rb), "only_ho26": len(rb - ra)},
            "start_lt_2026": {"ho4": len(sa), "ho26": len(sb), "same": len(sa & sb),
                              "only_ho4": len(sa - sb), "only_ho26": len(sb - sa),
                              "ex_only_ho4": onlya, "ex_only_ho26": onlyb},
            "upd_le_20251231": {"ho4": len(ua), "ho26": len(ub), "first_diff": None if first is None else [ua[first], ub[first]],
                                "len_equal": len(ua) == len(ub)}}


def tz_check(dfs):
    r7, ru = [], []
    for df in dfs:
        m = (df["s"] >= G0) & (df["s"] < G1 - 8 * 3600 * 1000)
        for sym, s, en in zip(df["sym"][m], df["s"][m], df["entry"][m]):
            a, raw = price(vsym(sym))
            for off, lst in ((0, r7), (7 * 3600 * 1000, ru)):
                i = idx(s + off)
                if 0 <= i < NM and not np.isnan(raw[i]):
                    lst.append(abs(en / raw[i] - 1))
    return {"plus07_median": float(np.median(r7)), "n7": len(r7),
            "utc_median": float(np.median(ru)), "nu": len(ru)}


def match_legs(x, y):
    """ghep 1-1 (sym, |start| <= 1 phut), tham lam theo start"""
    by = {}
    for sym, s in zip(y["sym"], y["s"]):
        by.setdefault(sym, []).append(s)
    for v in by.values():
        v.sort()
    used, k = set(), 0
    for sym, s in sorted(zip(x["sym"], x["s"]), key=lambda t: t[1]):
        for j, t in enumerate(by.get(sym, [])):
            if abs(t - s) <= MIN and (sym, j) not in used:
                used.add((sym, j)); k += 1
                break
    return k


def sens_h1():
    a, b = ms7(WIN["H1"][0]), ms7(WIN["H1"][1])
    res = {}
    for cfg in CFGS:
        rows = []
        for sd in SEEDS:
            x = load_pd(run_dir("ho4", cfg, "s", sd)); y = load_pd(run_dir("ho26", cfg, "s", sd))
            xs = x[(x["s"] >= a) & (x["s"] <= b)]; ys = y[(y["s"] >= a) & (y["s"] <= b)]
            px_ = x["pnl"][(x["e"] >= a) & (x["e"] <= b)].sum(); py_ = y["pnl"][(y["e"] >= a) & (y["e"] <= b)].sum()
            k = match_legs(xs, ys)
            rows.append({"seed": sd, "spnl_ho4": float(px_), "spnl_ho26": float(py_), "d_spnl": float(px_ - py_),
                         "n_ho4": len(xs), "n_ho26": len(ys), "d_n": len(xs) - len(ys), "match": k,
                         "match_pct_ho4": k / max(len(xs), 1), "match_pct_ho26": k / max(len(ys), 1),
                         "md5_ho26": md5f(run_dir("ho26", cfg, "s", sd) + "/storage/printDone.csv")})
        res[cfg] = rows
    return res


def bootstrap(R, rng, w, fee):
    k = np.array([R[("k24", fee, sd)]["win"][w]["dP"] for sd in SEEDS]).mean(0)
    b = np.array([R[("b0", fee, sd)]["win"][w]["dP"] for sd in SEEDS]).mean(0)
    nd = len(k)
    nb = -(-nd // BLK)
    st = rng.integers(0, nd, size=(NREP, nb))
    ix = ((st[:, :, None] + np.arange(BLK)) % nd).reshape(NREP, -1)[:, :nd]
    out = {}
    for name, v in (("k24", k), ("delta", k - b)):
        obs = float(v.sum()); bs = v[ix].sum(1)
        lo, hi = np.percentile(bs, [2.5, 97.5])
        out[name] = {"obs": obs, "p_le0": float((bs <= 0).mean()), "ci95": [float(lo), float(hi)],
                     "ci95_infl3": [obs + INFL * (lo - obs), obs + INFL * (hi - obs)]}
    return out


def concentration(R, w, fee="s"):
    mos = [m for m in ("2026-%02d" % i for i in range(1, 10))
           if WIN[w][0][:6] <= m.replace("-", "") <= WIN[w][1][:6]]
    rows = []
    for sd in SEEDS:
        r = R[("k24", fee, sd)]
        dp = np.array(r["win"][w]["daily_pnl"]); tot = dp.sum()
        top = np.sort(dp)[::-1]
        sh = {f"top{k}": float(top[:k].sum() / tot) if tot > 0 else None for k in (1, 3, 5)}
        rows.append({"seed": sd, "spnl": float(tot), **sh,
                     "lomo": {m: float(tot - r["monthly"][m]["spnl"]) for m in mos}})
    lomo = {m: {"n_pos": sum(x["lomo"][m] > 0 for x in rows),
                "mean": float(np.mean([x["lomo"][m] for x in rows]))} for m in mos}
    worst = min(lomo, key=lambda m: (lomo[m]["n_pos"], lomo[m]["mean"]))
    return {"seeds": rows, "lomo": lomo, "lomo_worst": worst,
            "mean_top": {k: float(np.mean([x[k] for x in rows if x[k] is not None] or [np.nan])) for k in ("top1", "top3", "top5")}}


KEYS = ["n", "spnl", "roi", "maxdd", "sharpe", "sortino", "cagr", "pct_days_trade"]


def mmm(v):
    v = [x for x in v if x is not None]
    return {"mean": float(np.mean(v)), "min": float(np.min(v)), "max": float(np.max(v))}


def aggregate(R):
    A = {}
    for fee in "sb":
        for w in WIN:
            cell = {}
            for cfg in CFGS:
                cell[cfg] = {k: mmm([R[(cfg, fee, sd)]["win"][w][k] for sd in SEEDS]) for k in KEYS}
                cell[cfg]["per_seed_spnl"] = [R[(cfg, fee, sd)]["win"][w]["spnl"] for sd in SEEDS]
            d = {k: [R[("k24", fee, sd)]["win"][w][k] - R[("b0", fee, sd)]["win"][w][k] for sd in SEEDS]
                 for k in ("n", "spnl", "roi", "maxdd", "sharpe")}
            cell["delta"] = {k: {"per_seed": v, **mmm(v)} for k, v in d.items()}
            ks = cell["k24"]["per_seed_spnl"]
            npos = sum(x > 0 for x in ks)
            e0 = {"mean_spnl": float(np.mean(ks)), "n_pos": npos,
                  "pass": bool(np.mean(ks) > 0 and npos >= 6)}
            dsp, ddd = float(np.mean(d["spnl"])), 100 * float(np.mean(d["maxdd"]))
            ha = {"mean_d_spnl": dsp, "mean_d_maxdd_pp": ddd, "n_seed_d_spnl_ge0": sum(x >= 0 for x in d["spnl"]),
                  "pass": bool(dsp >= 0 and ddd >= -5)}
            cell["E0"], cell["HA"] = e0, ha
            A[f"{fee}_{w}"] = cell
    return A


def cmd_score(a):
    md5s = check_md5_all()
    R, chk, st = {}, {}, {"leg_min": 0, "miss_raw": 0, "miss_fill": 0}
    qdev = []
    for cfg in CFGS:
        for fee in "bs":
            for sd in SEEDS:
                d = run_dir("ho4", cfg, fee, sd)
                df = load_pd(d)
                qdev.append(float(np.nanmax(np.abs(df["quantity"] - df["margin"] / df["entry"]) / df["quantity"])))
                E = equity(df, st)
                R[(cfg, fee, sd)] = {"win": {w: win_metrics(df, E, w) for w in WIN}, "monthly": monthly(df, E)}
                chk[f"ho4-{cfg}-{fee}-s{sd}"] = eq_check(d, E, df)
                LOG.info("%s-%s-s%d xong", cfg, fee, sd)
    tz = tz_check([load_pd(run_dir("ho4", c, "b", s)) for c in CFGS for s in SEEDS])
    A = aggregate(R)
    rng = np.random.default_rng(BSEED)
    BS = {f"{fee}_{w}": bootstrap(R, rng, w, fee) for fee in "sb" for w in WIN}
    CC = {w: concentration(R, w) for w in WIN}
    P = pre2026()
    S = sens_h1()
    res = {"defs": a.defs, "script": "research/analysis/ho4_score_b.py", "md5": md5s, "selfcheck": chk,
           "price_stats": st, "tz": tz, "q_vs_margin_entry_maxrel": max(qdev), "pre2026": P,
           "agg": A, "bootstrap": BS, "concentration": CC, "sens_h1": S,
           "runs": {f"{c}-{f}-s{s}": {"win": {w: {k: v for k, v in R[(c, f, s)]["win"][w].items()
                                                   if k not in ("dP", "daily_pnl")} for w in WIN},
                                      "monthly": R[(c, f, s)]["monthly"]} for (c, f, s) in R}}
    json.dump(res, open(f"{REPO}/docs/result/ho4/HO4_RESULT_B.json", "w"), indent=1, default=float)
    write_md(res)
    LOG.info("xong: JSON + MD")


def f0(x):
    return "—" if x is None else f"{x:,.0f}"


def pc(x, d=1):
    return "—" if x is None else f"{100 * x:.{d}f}%"


def mr(c, k, fmt):
    return f"{fmt(c[k]['mean'])} [{fmt(c[k]['min'])}..{fmt(c[k]['max'])}]"


def write_md(r):
    L = ["# HO4 — kết quả scorer B (độc lập)", "",
         f"Defs: `docs/result/ho4/score_B_defs.md` @ `{r['defs']}`. Script `research/analysis/ho4_score_b.py`. "
         "Pre-reg `PREREG_HOLDOUT2026H1.md` §1 + ADDENDUM-5/6/7. Bản CHÍNH = stress `-s-`; seed 42,7,13,21,99,123,777,2024.", ""]
    L += ["## Verdict (stress)", "", "| cửa sổ | E0: mean ΣPnL_S k24 | #seed>0 | E0 | H-A: mean ΔΣPnL_S | mean ΔmaxDD pp | H-A |", "|---|---|---|---|---|---|---|"]
    for w in WIN:
        c = r["agg"][f"s_{w}"]
        L.append(f"| {w} | {f0(c['E0']['mean_spnl'])} (>0) | {c['E0']['n_pos']}/8 (≥6) | {'PASS' if c['E0']['pass'] else 'FAIL'} | "
                 f"{f0(c['HA']['mean_d_spnl'])} (≥0) | {c['HA']['mean_d_maxdd_pp']:+.2f} (≥−5) | {'XÁC NHẬN' if c['HA']['pass'] else 'KHÔNG'} |")
    for fee, nm in (("s", "stress (CHÍNH)"), ("b", "phí gốc (báo)")):
        L += ["", f"## Bảng {nm}: mean [min..max] 8 seed", "",
              "| cửa sổ | cfg | n | ΣPnL | ROI | maxDD | Sharpe | Sortino | CAGR | % ngày có lệnh |", "|---|---|---|---|---|---|---|---|---|---|"]
        for w in WIN:
            c = r["agg"][f"{fee}_{w}"]
            for cfg in CFGS:
                x = c[cfg]
                L.append(f"| {w} | {cfg} | {mr(x, 'n', f0)} | {mr(x, 'spnl', f0)} | {mr(x, 'roi', pc)} | {mr(x, 'maxdd', pc)} | "
                         f"{mr(x, 'sharpe', lambda v: f'{v:.2f}')} | {mr(x, 'sortino', lambda v: f'{v:.2f}')} | {mr(x, 'cagr', pc)} | {mr(x, 'pct_days_trade', pc)} |")
            dl = c["delta"]
            L.append(f"| {w} | Δk24−b0 | {mr(dl, 'n', f0)} | {mr(dl, 'spnl', f0)} | {mr(dl, 'roi', pc)} | {mr(dl, 'maxdd', pc)} | "
                     f"{mr(dl, 'sharpe', lambda v: f'{v:+.2f}')} | | | |")

    L += ["", "## Theo seed (stress): ΣPnL k24 / b0 / Δ ; maxDD k24 / b0", "", "| seed | " + " | ".join(
        f"{w} ΣPnL k24 | {w} ΣPnL b0 | {w} Δ | {w} DD k24 | {w} DD b0" for w in WIN) + " |", "|---" * 16 + "|"]
    for sd in SEEDS:
        row = [str(sd)]
        for w in WIN:
            k, b = r["runs"][f"k24-s-s{sd}"]["win"][w], r["runs"][f"b0-s-s{sd}"]["win"][w]
            row += [f0(k["spnl"]), f0(b["spnl"]), f0(k["spnl"] - b["spnl"]), pc(k["maxdd"]), pc(b["maxdd"])]
        L.append("| " + " | ".join(row) + " |")
    L += ["", "## So DEV baseline stress (Sharpe 1,80; CAGR 27,6%; maxDD −22,9%) — mean tỉ lệ k24-s", "",
          "| cửa sổ | Sharpe/1,80 | CAGR/27,6% | maxDD/−22,9% |", "|---|---|---|---|"]
    for w in WIN:
        v = [r["runs"][f"k24-s-s{sd}"]["win"][w]["vs_dev"] for sd in SEEDS]
        L.append(f"| {w} | {np.mean([x['sharpe'] for x in v]):.2f} | {np.mean([x['cagr'] for x in v]):.2f} | {np.mean([x['maxdd'] for x in v]):.2f} |")
    L += ["", f"## Bootstrap MTM block-{BLK}d (USD PnL MTM cửa sổ, mean 8 seed; NREP {NREP}, seed {BSEED}; inflate k=3 ×{INFL})", "",
          "| bản | cửa sổ | chuỗi | quan sát | P(≤0) | CI95 | CI95 inflate |", "|---|---|---|---|---|---|---|"]
    for key, v in r["bootstrap"].items():
        fee, w = key.split("_")
        for nm in ("k24", "delta"):
            x = v[nm]
            L.append(f"| {fee} | {w} | {nm} | {f0(x['obs'])} | {x['p_le0']:.4f} | [{f0(x['ci95'][0])}, {f0(x['ci95'][1])}] | "
                     f"[{f0(x['ci95_infl3'][0])}, {f0(x['ci95_infl3'][1])}] |")
    L += ["", "## Theo tháng (stress, mean 8 seed): n / ΣPnL / ROI MTM", "", "| tháng | b0 n | b0 ΣPnL | b0 ROI | k24 n | k24 ΣPnL | k24 ROI | #seed k24>0 |", "|---|---|---|---|---|---|---|---|"]
    for mo in r["runs"]["k24-s-s42"]["monthly"]:
        c = {cfg: [r["runs"][f"{cfg}-s-s{sd}"]["monthly"][mo] for sd in SEEDS] for cfg in CFGS}
        L.append(f"| {mo} | " + " | ".join(f"{np.mean([x['n'] for x in c[cfg]]):.0f} | {f0(np.mean([x['spnl'] for x in c[cfg]]))} | "
                                          f"{pc(np.mean([x['roi'] for x in c[cfg]]))}" for cfg in CFGS)
                 + f" | {sum(x['spnl'] > 0 for x in c['k24'])}/8 |")

    L += ["", "## Độ tập trung (k24-s; ΣPnL theo ngày end)", "", "| cửa sổ | mean top-1 | top-3 | top-5 | LOMO tháng tệ nhất | #seed còn >0 | mean còn |", "|---|---|---|---|---|---|---|"]
    for w, c in r["concentration"].items():
        lw = c["lomo_worst"]
        L.append(f"| {w} | {pc(c['mean_top']['top1'])} | {pc(c['mean_top']['top3'])} | {pc(c['mean_top']['top5'])} | {lw} | "
                 f"{c['lomo'][lw]['n_pos']}/8 | {f0(c['lomo'][lw]['mean'])} |")
    L += ["", "LOMO mọi tháng (W9): " + "; ".join(f"{m}: {v['n_pos']}/8, mean {f0(v['mean'])}" for m, v in r["concentration"]["W9"]["lomo"].items())]
    L += ["", "## Độ nhạy dữ liệu H1: HO4 (Vision) − HO26 (242), stress, cùng seed", "",
          "| cfg | seed | ΣPnL HO4 | ΣPnL HO26 | ΔΣPnL | n HO4 | n HO26 | Δn | trùng lệnh | % n HO4 | % n HO26 |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for cfg, rows in r["sens_h1"].items():
        for x in rows:
            L.append(f"| {cfg} | {x['seed']} | {f0(x['spnl_ho4'])} | {f0(x['spnl_ho26'])} | {f0(x['d_spnl'])} | {x['n_ho4']} | {x['n_ho26']} | "
                     f"{x['d_n']:+d} | {x['match']} | {pc(x['match_pct_ho4'])} | {pc(x['match_pct_ho26'])} |")
        L.append(f"| {cfg} | mean | {f0(np.mean([x['spnl_ho4'] for x in rows]))} | {f0(np.mean([x['spnl_ho26'] for x in rows]))} | "
                 f"{f0(np.mean([x['d_spnl'] for x in rows]))} | | | {np.mean([x['d_n'] for x in rows]):+.1f} | | "
                 f"{pc(np.mean([x['match_pct_ho4'] for x in rows]))} | {pc(np.mean([x['match_pct_ho26'] for x in rows]))} |")
    st, tz, P = r["price_stats"], r["tz"], r["pre2026"]
    L += ["", "## Tự kiểm", "",
          f"- md5 printDone == queue_status: {sum(v['ok'] for v in r['md5'].values())}/32.",
          f"- Giá Vision: phút-chân {st['leg_min']:,}; thiếu giá đúng phút {st['miss_raw']:,} ({pc(st['miss_raw'] / max(st['leg_min'], 1), 4)}); "
          f"sau ffill vẫn thiếu (dùng entry) {st['miss_fill']:,}.",
          f"- TZ (bản -b-): median |entry/close(start)−1| giả định +07 = {tz['plus07_median']:.5f} (n={tz['n7']}); giả định UTC = {tz['utc_median']:.5f} (n={tz['nu']}).",
          f"- max |quantity − margin/entry|/quantity = {r['q_vs_margin_entry_maxrel']:.2e}.",
          f"- Trước 2026 (ho4-k24-s-s42 vs ho26-k24-s-s42): end ≤ 2025-12-31 23:59: {P['end_le_20251231']}; start < 2026: "
          f"{ {k: v for k, v in P['start_lt_2026'].items() if not k.startswith('ex_')} }; log Update ≤ 20251231: {P['upd_le_20251231']}.", "",
          "| run | n pd | n result | equity_final | = b+unP Update cuối | MTM vs final % | ≤0,01% | 35000+Σpnl vs final % | Update ≥2026 n | med % | max % |", "|---|---|---|---|---|---|---|---|---|---|---|"]
    for k, v in r["selfcheck"].items():
        L.append(f"| {k} | {v['n_pd']} | {v['n_result']} | {f0(v['equity_final'])} | {v['final_eq_bunp']} ({v['last_upd']}) | "
                 f"{v['mtm_vs_final_pct']:.4f} | {v['pass_001']} | {v['sumpnl_vs_final_pct']:.3f} | {v['upd_n']} | {v['upd_med_pct']:.4f} | {v['upd_max_pct']:.4f} |")
    open(f"{REPO}/docs/result/ho4/HO4_RESULT_B.md", "w").write("\n".join(L) + "\n")



def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["fetch", "score"])
    ap.add_argument("--defs", default="?", help="hash commit defs")
    a = ap.parse_args()
    os.makedirs(WD, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
                        handlers=[logging.FileHandler(f"{WD}/ho4sb_{a.cmd}.log"), logging.StreamHandler()])
    {"fetch": cmd_fetch, "score": cmd_score}[a.cmd](a)


if __name__ == "__main__":
    main()
