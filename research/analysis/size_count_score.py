"""SIZE-COUNT scorer — docs/prereg/PREREG_SIZE_COUNT_HARNESS.md.

Cham DOC LAP voi truc: doc `printDone.csv` + `sim.out` cua tung chan Kaggle
(/home/ubuntu/kaggle_sim/out/<tag>/), KHONG cham gi khac.

Ra:
  (a) %PnL tu top-1% leg   |  (b') bo top-50% leg => PnL > 0 ?
  q* (bo bao nhieu % leg thi PnL con lai = 0)
  Bo 4 THUOC CHUAN: wl_ratio . tf_5 . loss_mean . conc_5  (+ median/leg du bi)
  tf_10 . TF50 . TF50/(n/2) . mean|lo|/mean lai . sign%
  Rui ro (appetite latest): maxDD<=40 . UW<=250 . qmin>=-20 . 0 nam am . conc 1 coin<=15 . gross<=70
  GROSS (hau kiem): TB + MAX, va he so bu de giu <=70% theo tung tick
  5 rate + CI (block-72h, 2000 rep, seed 20260905, inflate(k)); luat siet §10.2

Usage:
  python3 size_count_score.py [--base cd-sel15] [--k 4] [--json OUT.json] TAG [TAG ...]
"""
import argparse
import json
import math
import os
import sys

sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
import numpy as np
import pandas as pd
import gd92xexit_score as G

KOUT = "/home/ubuntu/kaggle_sim/out"
SEED = 20260905
NREP = 2000
BLOCK_H = 72
ANCHOR = pd.Timestamp("2021-07-01")

# appetite latest (x1_rates.APPETITES) + rao moi
DD_MAX, UW_MAX, Q_MIN, CONC_MAX, GROSS_MAX, FEE = 40.0, 250, -20.0, 15.0, 70.0, 0.006
RAIL_A_TOP1 = 15.0          # %PnL top-1% leg <= 15
RAIL_B_DROP = 50.0          # bo top-50% leg => PnL > 0

RATE_KEYS = ["win%", "TSloss%", "mP|SM", "mP|SL", "meanP", "mMargin"]
# huong TOT cua tung rate (chi de dem "ngoai CI cung huong tot")
RATE_GOOD = {"win%": +1, "TSloss%": -1, "mP|SM": +1, "mP|SL": +1, "meanP": +1, "mMargin": 0}
FREQ_GROUP = {"win%", "TSloss%"}      # toi da 1 rate nhom nay duoc tinh


def legs(tag):
    d = G.trades(tag).copy()
    d["blk2"] = ((d.ts - ANCHOR) / pd.Timedelta(hours=BLOCK_H)).astype(int)
    return d


def eq_series(tag):
    return G.equity(tag)


# ---------- thieu do duoi (tail) tren pnl USDT -----------------------------
def tail(d):
    p = d["pnl"].to_numpy(float)
    p = p[np.isfinite(p)]
    n = len(p)
    out = dict(n=int(n))
    if n == 0:
        return out
    s = np.sort(p)[::-1]                       # giam dan
    tot = s.sum()
    k1 = max(1, int(math.ceil(0.01 * n)))
    k5 = max(1, int(math.ceil(0.05 * n)))
    k10 = max(1, int(math.ceil(0.10 * n)))
    kh = int(n // 2)
    out.update(
        sum_pnl=float(tot),
        top1_share=float(100.0 * s[:k1].sum() / tot) if tot != 0 else float("nan"),
        conc_5=float(100.0 * s[:k5].sum() / tot) if tot != 0 else float("nan"),
        tf_5=float(s[k5:].mean()) if n > k5 else float("nan"),
        tf_10=float(s[k10:].mean()) if n > k10 else float("nan"),
        TF50=float(s[kh:].sum()),              # bo top-50% => tong nua duoi
        mean_lower=float(s[kh:].mean()),       # TF50/(n/2)
        median=float(np.median(p)),
        sign_pct=float(100.0 * (p > 0).mean()),
        win_mean=float(p[p > 0].mean()) if (p > 0).any() else float("nan"),
        loss_mean=float(p[p < 0].mean()) if (p < 0).any() else float("nan"),
        asym=float(abs(p[p < 0].mean()) / p[p > 0].mean()) if (p > 0).any() and (p < 0).any() else float("nan"),
    )
    out["wl_ratio"] = float(1.0 / out["asym"]) if out.get("asym") else float("nan")
    # q*: bo bao nhieu % leg (tu lon nhat) thi tong con lai <= 0
    csum = np.cumsum(s)
    ks = np.where(csum >= tot)[0]
    out["q_star"] = float(100.0 * (ks[0] + 1) / n) if len(ks) else float("nan")
    return out


# ---------- gross (hau kiem) tu ledger + equity ngay -----------------------
def gross(d, eq):
    d = d.dropna(subset=["t_end"]).copy()
    d = d[pd.to_numeric(d["margin"], errors="coerce").notna()]
    if len(d) == 0:
        return dict(gross_mean=float("nan"), gross_max=float("nan"), coin_max=0, coin_mean=float("nan"))
    dts = (d["ts"] - d["ts"].min()).dt.total_seconds()
    dte = (d["t_end"] - d["ts"].min()).dt.total_seconds()
    ev = []
    for (a, b, m, sym) in zip(dts.to_numpy(float), dte.to_numpy(float), d["margin"].to_numpy(float),
                              d["sym"].to_numpy()):
        if not np.isfinite(a) or not np.isfinite(b) or b < a or not np.isfinite(m):
            continue
        ev.append((a, m, sym, +1))
        ev.append((b, m, sym, -1))
    if not ev:
        return dict(gross_mean=float("nan"), gross_max=float("nan"), coin_max=0, coin_mean=float("nan"))
    ev.sort(key=lambda x: (x[0], -x[3]))
    eqidx = eq.copy()
    eqidx.index = eqidx.index
    t0 = d["ts"].min()

    def eq_at(sec):
        day = (t0 + pd.Timedelta(seconds=sec)).normalize()
        v = eqidx.reindex([day], method="ffill")
        return float(v.iloc[0]) if len(v) and np.isfinite(v.iloc[0]) else float(eqidx.iloc[0])

    run_m, open_syms = 0.0, {}
    wgross, wtime = 0.0, 0.0
    gmax, cmax = 0.0, 0
    wcoin, wt = 0.0, 0.0
    prev = None
    for (t, m, sym, sign) in ev:
        if prev is not None and t > prev:
            e = eq_at(prev)
            g = run_m / e if e > 0 else float("nan")
            if np.isfinite(g):
                dt = t - prev
                wgross += g * dt
                wtime += dt
                gmax = max(gmax, g)
            wcoin += len(open_syms) * (t - prev)
            wt += (t - prev)
            cmax = max(cmax, len(open_syms))
        if sign > 0:
            run_m += m
            open_syms[sym] = open_syms.get(sym, 0) + 1
        else:
            run_m -= m
            open_syms[sym] = open_syms.get(sym, 0) - 1
            if open_syms[sym] <= 0:
                open_syms.pop(sym, None)
        prev = t
    return dict(gross_mean=float(100.0 * wgross / wtime) if wtime > 0 else float("nan"),
                gross_max=float(100.0 * gmax), coin_max=int(cmax),
                coin_mean=float(wcoin / wt) if wt > 0 else float("nan"))


# ---------- 5 rate + CI (paired block-72h) ---------------------------------
def rates(d):
    p = d["pnl"]
    sm = p[d.status == "STOP_MARKET_DONE"]
    sl = p[d.status == "STOP_LOSS_DONE"]
    return {
        "win%": 100.0 * (p > 0).mean() if len(d) else float("nan"),
        "TSloss%": 100.0 * (d.status == "STOP_LOSS_DONE").mean() if len(d) else float("nan"),
        "mP|SM": float(sm.mean()) if len(sm) else float("nan"),
        "mP|SL": float(sl.mean()) if len(sl) else float("nan"),
        "meanP": float(p.mean()) if len(d) else float("nan"),
        "mMargin": float(d["margin"].mean()) if len(d) else float("nan"),
    }


def ci_pair(ta, tb, width):
    da, db = legs(ta), legs(tb)
    blocks = np.union1d(da.blk2.unique(), db.blk2.unique())
    ga = {k: v for k, v in da.groupby("blk2")}
    gb = {k: v for k, v in db.groupby("blk2")}
    rng = np.random.default_rng(SEED)
    obs = {k: rates(da)[k] - rates(db)[k] for k in RATE_KEYS}
    draws = {k: [] for k in RATE_KEYS}
    for _ in range(NREP):
        pick = rng.choice(blocks, size=len(blocks), replace=True)
        sa = pd.concat([ga[b] for b in pick if b in ga]) if any(b in ga for b in pick) else da.iloc[:0]
        sb = pd.concat([gb[b] for b in pick if b in gb]) if any(b in gb for b in pick) else db.iloc[:0]
        ra, rb = rates(sa), rates(sb)
        for k in RATE_KEYS:
            draws[k].append(ra[k] - rb[k])
    out = {}
    for k in RATE_KEYS:
        arr = np.asarray(draws[k], float)
        arr = arr[np.isfinite(arr)]
        if len(arr) == 0:
            out[k] = (obs[k], float("nan"), float("nan"), False)
            continue
        lo, hi = np.percentile(arr, [2.5, 97.5])
        c = (lo + hi) / 2.0
        lo, hi = c - (c - lo) * width, c + (hi - c) * width
        out[k] = (float(obs[k]), float(lo), float(hi), not (lo <= 0.0 <= hi))
    return out


def rail_rule(ci):
    """Luat siet §10.2: >=2 rate ngoai CI cung huong TOT; toi da 1 rate nhom tan suat; KHONG tinh meanP."""
    good, freq_used = [], 0
    for k in RATE_KEYS:
        if k in ("meanP", "mMargin"):
            continue
        obs, lo, hi, sig = ci[k]
        if not sig:
            continue
        dirc = np.sign(obs)
        isgood = (dirc == RATE_GOOD[k])
        if isgood:
            if k in FREQ_GROUP:
                freq_used += 1
                if freq_used > 1:
                    continue
            good.append(k)
    return good


def arm_report(tag, base_tag):
    d = legs(tag)
    eq = eq_series(tag)
    s = G.summary(tag)
    t = tail(d)
    g = gross(d, eq)
    yd = G.yearly_detail(tag)
    bad = []
    for y, v in sorted(yd.items()):
        if v.get("ret", 0) <= 0:
            bad.append("%s:ret<=0" % y)
        if v.get("maxDD", 0) < -DD_MAX:
            bad.append("%s:DD%.1f" % (y, v["maxDD"]))
        if v.get("uw", 0) > UW_MAX:
            bad.append("%s:UW%d" % (y, v["uw"]))
        if v.get("qmin", 0) < Q_MIN:
            bad.append("%s:qmin%.1f" % (y, v["qmin"]))
    r = dict(
        tag=tag, n=t["n"], ndays=s["ndays"], eq_end=s["end"], cagr=s["cagr"],
        entry_day=s["n"] / s["ndays"], entry_month=s["n"] / s["ndays"] * 365.25 / 12.0,
        maxDD=s["maxDD"], uw=s["uw"], qmin=s["qmin"], conc=s["conc"],
        hold_med=s["hold_med"],
        top1_share=t.get("top1_share"), conc_5=t.get("conc_5"), tf_5=t.get("tf_5"),
        tf_10=t.get("tf_10"), TF50=t.get("TF50"), mean_lower=t.get("mean_lower"),
        q_star=t.get("q_star"), median=t.get("median"), wl_ratio=t.get("wl_ratio"),
        loss_mean=t.get("loss_mean"), asym=t.get("asym"), sign_pct=t.get("sign_pct"),
        win_mean=t.get("win_mean"),
        gross_mean=g["gross_mean"], gross_max=g["gross_max"], coin_max=g["coin_max"],
        coin_mean=g["coin_mean"],
        rail_A=bool(t.get("top1_share") is not None and t["top1_share"] <= RAIL_A_TOP1),
        rail_B=bool(t.get("TF50") is not None and t["TF50"] > 0),
        rail_old_pass=(not bad), rail_old_bad=bad,
    )
    return r


def fmt(x, nd=3):
    return "-" if x is None or (isinstance(x, float) and not np.isfinite(x)) else ("%%.%df" % nd) % x


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("tags", nargs="+")
    ap.add_argument("--base", default="cd-sel15")
    ap.add_argument("--k", type=int, default=4)
    ap.add_argument("--json", default="/home/ubuntu/kaggle_sim/out/size_count_score.json")
    a = ap.parse_args()
    width = 1.0 if a.k <= 1 else math.sqrt(2.0 * math.log(a.k))

    print("=" * 120)
    print("SIZE-COUNT SCORE | base=%s | k=%d inflate=%.4f | appetite latest (DD<=%.0f UW<=%d qmin>=%.0f "
          "conc<=%.0f gross<=%.0f) | rao moi: top-1%%<=%.0f & bo-%.0f%%>0"
          % (a.base, a.k, width, DD_MAX, UW_MAX, Q_MIN, CONC_MAX, GROSS_MAX, RAIL_A_TOP1, RAIL_B_DROP))

    rows = {}
    for t in a.tags:
        try:
            rows[t] = arm_report(t, a.base)
        except Exception as e:
            print("  %-10s KHONG DOC DUOC: %s" % (t, e))

    hdr = ("%-10s %5s %7s %7s %8s %8s %6s %6s %6s %7s %7s %8s %8s %8s %8s %8s %8s"
           % ("tag", "n", "entry/m", "CAGR%", "maxDD%", "UW", "qmin", "conc%", "coin#", "grossT", "grossM",
              "%top1", "bỏ50", "TF50", "meanlwr", "q*%", "wl_ratio"))
    print("\n" + hdr)
    for t in a.tags:
        r = rows.get(t)
        if not r:
            continue
        print("%-10s %5d %7s %+7s %8s %8d %6s %6s %6s %7s %7s %8s %8s %8s %8s %8s %8s" % (
            r["tag"], r["n"], fmt(r["entry_month"], 2), fmt(r["cagr"], 2), fmt(r["maxDD"], 2), r["uw"],
            fmt(r["qmin"], 2), fmt(r["conc"], 2), "%s/%s" % (r["coin_max"], fmt(r["coin_mean"], 1)),
            fmt(r["gross_mean"], 1), fmt(r["gross_max"], 1),
            fmt(r["top1_share"], 2), fmt(r["TF50"], 0), fmt(r["TF50"], 0), fmt(r["mean_lower"], 2),
            fmt(r["q_star"], 1), fmt(r["wl_ratio"], 3)))

    print("\n" + "-" * 120)
    print("BỘ 4 THƯỚC CHUẨN + dự bị | asym=mean|lo|/mean lai | sign%=win%")
    print("%-10s %8s %8s %10s %8s %8s %8s %8s %8s" % ("tag", "wl_ratio", "tf_5", "loss_mean", "conc_5", "median", "asym", "sign%", "tf_10"))
    for t in a.tags:
        r = rows.get(t)
        if not r:
            continue
        print("%-10s %8s %8s %10s %8s %8s %8s %8s %8s" % (
            t, fmt(r["wl_ratio"], 3), fmt(r["tf_5"], 2), fmt(r["loss_mean"], 1),
            fmt(r["conc_5"], 1), fmt(r["median"], 2), fmt(r["asym"], 3),
            fmt(r["sign_pct"], 2), fmt(r["tf_10"], 2)))

    print("\n" + "-" * 120)
    print("RÀO (a)/(b′) + rào cũ (appetite latest) + gross")
    print("%-10s %8s %8s %10s %10s %10s %8s" % ("tag", "a<=15", "b'>0", "rao cu", "grossT<=70", "grossM<=70", "gio_x7"))
    for t in a.tags:
        r = rows.get(t)
        if not r:
            continue
        x7 = 70.0 / r["gross_max"] if (r["gross_max"] and r["gross_max"] > 0) else float("nan")
        print("%-10s %8s %8s %10s %10s %10s %8s" % (
            t, "PASS" if r["rail_A"] else "FAIL", "PASS" if r["rail_B"] else "FAIL",
            "PASS" if r["rail_old_pass"] else "FAIL",
            "PASS" if (r["gross_mean"] and r["gross_mean"] <= GROSS_MAX) else "FAIL",
            "PASS" if (r["gross_max"] and r["gross_max"] <= GROSS_MAX) else "FAIL",
            fmt(min(1.0, x7), 3) if np.isfinite(x7) else "-"))
        if r["rail_old_bad"]:
            print("%-10s   vi pham cu: %s" % ("", " ".join(r["rail_old_bad"])))

    print("\n" + "-" * 120)
    print("5 RATE + CI vs %s (block-72h, %d rep, seed %d, inflate(k=%d)=%.4f)" % (a.base, NREP, SEED, a.k, width))
    ci_all = {}
    for t in a.tags:
        if t == a.base or t not in rows:
            continue
        ci = ci_pair(t, a.base, width)
        ci_all[t] = {k: [round(v[0], 4), round(v[1], 4), round(v[2], 4), bool(v[3])] for k, v in ci.items()}
        good = rail_rule(ci)
        print("  %-10s outCI=%s | huong TOT ngoai CI (luat siet §10.2) = %s => %s" % (
            t, [k for k in RATE_KEYS if ci[k][3]], good,
            "DAT (>=2)" if len(good) >= 2 else "KHONG (<2)"))
        for k in RATE_KEYS:
            o, lo, hi, sig = ci[k]
            print("      %-8s %+9.3f [%+9.3f ; %+9.3f] %s" % (k, o, lo, hi, "NGOAI" if sig else "-"))

    out = dict(base=a.base, k=a.k, inflate=width, arms=rows, ci=ci_all,
               rails=dict(a=RAIL_A_TOP1, b=RAIL_B_DROP, dd=DD_MAX, uw=UW_MAX, q=Q_MIN,
                          conc=CONC_MAX, gross=GROSS_MAX, fee=FEE))
    with open(a.json, "w") as f:
        json.dump(out, f, indent=1)
    print("\nJSON: %s" % a.json)


if __name__ == "__main__":
    main()
