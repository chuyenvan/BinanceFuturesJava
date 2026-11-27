#!/usr/bin/env python3
"""G4 evaluation (prereg sec 3, 5, 6; ERRATA4 N5; lessons ERRATA1-3). 12 configs; selection = best TRAIN monthly Sharpe
(tie: shorter TS, then higher T). TRAIN / WFO by ENTRY time; each trade's full PnL booked at its exit month.
D2 control (prereg sec 5) = circular DAY shift per pair inside WFO (keeps time of day, clusters, count, side, exits, costs);
secondary (MASTER brief, descriptive) = random entry same pair / same UTC hour / same month / same count.
p = (1 + n_ge) / (N + 1). Every TRAIN figure tagged [in-sample]. Real data needs --real I_HAVE_A1_PASS."""
import argparse
import hashlib
import json
import logging
import math
import os

import numpy as np
import pandas as pd

import load_g4
import sig_g4
import sim_g4

LOG = logging.getLogger("g4.eval")
N_MIN = 500
SEED = 20261127
D7_MIN = 150


def perm_p(r, real):
    r = np.asarray(r, float)
    return float((1 + np.sum(r >= real)) / (len(r) + 1))


def month_index(tm):
    ts = pd.to_datetime(np.asarray(tm, np.int64) * 60, unit="s")
    return (ts.year * 12 + ts.month - 1).values


def period_months(a, e):
    a, e = pd.Timestamp(a), pd.Timestamp(e)
    return np.arange(a.year * 12 + a.month - 1, e.year * 12 + e.month)


def to_df(data, res):
    w = 1.0 / len(data["pairs"])
    rows = []
    for p, r in res.items():
        d = data["pairs"][p]
        if not len(r["entry"]):
            continue
        rows.append(pd.DataFrame(dict(pair=p, t_entry=d["t"][r["entry"]], t_exit=d["t"][r["exit"]] + 1,
                                      hour=pd.to_datetime(d["t"][r["entry"]] * 60, unit="s").hour,
                                      net=r["net"] * w, gross=r["gross"] * w, cost=r["cost"] * w, swap=r["swap"] * w,
                                      net_unit=r["net"], gross_unit=r["gross"], reason=r["reason"])))
    if not rows:
        return pd.DataFrame(columns=["pair", "t_entry", "t_exit", "hour", "net", "gross", "cost", "swap", "net_unit",
                                     "gross_unit", "reason"])
    return pd.concat(rows, ignore_index=True)


def sel_period(df, a, e):
    return df[(df["t_entry"] >= sig_g4.tmin(a)) & (df["t_entry"] < sig_g4.tmin(e) + 1440)]


def monthly(df, a, e):
    mi = period_months(a, e)
    s = pd.Series(0.0, index=mi)
    if len(df):
        g = pd.Series(df["net"].values, index=month_index(df["t_exit"].values)).groupby(level=0).sum()
        s = s.add(g.reindex(mi).fillna(0.0), fill_value=0.0)
    return s


def sharpe_m(s):
    sd = s.std(ddof=1)
    return float(s.mean() / sd * math.sqrt(12)) if len(s) > 2 and sd > 0 else float("nan")


def drop_top(s, frac=0.05):
    k = int(math.ceil(frac * len(s)))
    return float(s.sort_values().iloc[:len(s) - k].sum())


def max_dd_realized(df):
    if not len(df):
        return 0.0
    eq = 1.0 + df.sort_values("t_exit")["net"].cumsum().values
    pk = np.maximum.accumulate(np.maximum(eq, 1.0))
    return float(np.max((pk - eq) / pk))


def max_dd_mtm(data, res, a, e):
    """maxDD on minute mark-to-market equity of trades entered in [a, e]."""
    w = 1.0 / len(data["pairs"])
    T, V = [], []
    lo, hi = sig_g4.tmin(a), sig_g4.tmin(e) + 1440
    for p, r in res.items():
        d = data["pairs"][p]
        for q, (tt, vv) in enumerate(r["paths"]):
            if lo <= d["t"][r["entry"][q]] < hi:
                T.append(tt)
                V.append(np.diff(np.concatenate([[0.0], vv])) * w)
    if not T:
        return 0.0
    T = np.concatenate(T)
    V = np.concatenate(V)
    o = np.argsort(T, kind="stable")
    eq = 1.0 + np.cumsum(V[o])
    pk = np.maximum.accumulate(np.maximum(eq, 1.0))
    return float(np.max((pk - eq) / pk))


def metrics(df, a, e):
    x = sel_period(df, a, e)
    s = monthly(x, a, e)
    yrs = len(s) / 12.0
    pos = x["net_unit"][x["net_unit"] > 0]
    neg = x["net_unit"][x["net_unit"] <= 0]
    return dict(n_trades=int(len(x)), sharpe_m=sharpe_m(s), ann_ret=float(s.sum() / yrs) if yrs else 0.0,
                total=float(s.sum()), maxdd_realized=max_dd_realized(x),
                mean_bp_after_cost=float(x["net_unit"].mean() * 1e4) if len(x) else float("nan"),
                mean_bp_before_cost=float(x["gross_unit"].mean() * 1e4) if len(x) else float("nan"),
                hit=float((x["net_unit"] > 0).mean()) if len(x) else float("nan"),
                payoff=float(pos.mean() / -neg.mean()) if len(pos) and len(neg) and neg.mean() < 0 else float("nan"),
                worst_bp=float(x["net_unit"].min() * 1e4) if len(x) else float("nan"),
                exit_share={k: float(v) for k, v in x["reason"].value_counts(normalize=True).items()},
                per_pair_total={k: float(v) for k, v in x.groupby("pair")["net"].sum().items()},
                per_year_trades={int(k): int(v) for k, v in pd.Series(pd.to_datetime(x["t_entry"] * 60, unit="s").dt.year)
                                 .value_counts().items()},
                per_hour_trades={int(k): int(v) for k, v in x["hour"].value_counts().items()},
                drop5pct_months_sum=drop_top(s), _monthly=s)


def choose(cfgs, train):
    """Uses TRAIN metrics only. Highest TRAIN monthly Sharpe; tie -> shorter TS, then higher T, then grid order."""
    def key(i):
        sh = train[i]["sharpe_m"]
        return (-(sh if np.isfinite(sh) else -1e9), cfgs[i]["TS"], -cfgs[i]["T"], i)
    return min(range(len(cfgs)), key=key)


def _valid_entry(d):
    return d["_entry_ok"] & np.isfinite(d["_sig1"])


def shift_pool(data, real_events, a, e):
    pool = {}
    for p, d in data["pairs"].items():
        ss = d["_sess"]
        ok = ss["trading"] & np.isfinite(ss["sig_session"])
        dates = ss["sessions"][ok]
        sd = pd.DatetimeIndex(dates)
        m = (sd >= pd.Timestamp(a)) & (sd <= pd.Timestamp(e))
        dates = dates[m]
        start = (pd.DatetimeIndex(dates).tz_localize("America/New_York") - pd.Timedelta(hours=7)).tz_convert("UTC")
        st = start.tz_localize(None).values.astype("datetime64[m]").astype(np.int64)
        ev = real_events.get(p, np.array([], np.int64))
        pos = np.searchsorted(dates, d["sess"][ev])
        okp = (pos < len(dates)) & (dates[np.minimum(pos, len(dates) - 1)] == d["sess"][ev])
        pool[p] = dict(start=st, pos=pos[okp], off=d["t"][ev[okp]] - st[pos[okp]], S=len(dates))
    return pool


def shift_draw(data, pool, side, TS, rng, cost_mult=1.0):
    out = {}
    for p, d in data["pairs"].items():
        P = pool[p]
        if P["S"] < 2 or not len(P["pos"]):
            out[p] = None
            continue
        k = int(rng.integers(1, P["S"]))
        np_ = (P["pos"] + k) % P["S"]
        tgt = P["start"][np_] + P["off"]
        b = np.searchsorted(d["t"], tgt)
        b = np.minimum(b, len(d["t"]) - 1)
        ok = (d["t"][b] - tgt <= 5) & (d["t"][b] >= tgt) & _valid_entry(d)[b]
        b = b[ok]
        out[p] = sim_g4.trades_batch(d, b + 1, side, d["_sig1"][b] * np.sqrt(60), TS, cost_mult) if len(b) else None
        if out[p] is not None:
            out[p]["entry"] = b + 1
    return out


def random_pool(data, real_events, a, e):
    pool = {}
    for p, d in data["pairs"].items():
        tt = d["t"]
        cand = np.flatnonzero(_valid_entry(d) & (tt >= sig_g4.tmin(a)) & (tt < sig_g4.tmin(e) + 1440))
        key = month_index(tt[cand]) * 24 + pd.to_datetime(tt[cand] * 60, unit="s").hour.values
        o = np.argsort(key, kind="stable")
        ev = real_events.get(p, np.array([], np.int64))
        rk = month_index(tt[ev]) * 24 + pd.to_datetime(tt[ev] * 60, unit="s").hour.values
        ks = key[o]
        pool[p] = dict(cand=cand[o], lo=np.searchsorted(ks, rk, "left"), hi=np.searchsorted(ks, rk, "right"), rk=rk)
    return pool


def random_draw(data, pool, side, TS, rng, cost_mult=1.0):
    out = {}
    for p, d in data["pairs"].items():
        P = pool[p]
        ok = P["hi"] > P["lo"]
        if not ok.any():
            out[p] = None
            continue
        j = P["lo"][ok] + (rng.random(ok.sum()) * (P["hi"][ok] - P["lo"][ok])).astype(np.int64)
        b = P["cand"][j]
        out[p] = sim_g4.trades_batch(d, b + 1, side, d["_sig1"][b] * np.sqrt(60), TS, cost_mult)
        out[p]["entry"] = b + 1
    return out


def draw_sharpe(data, draw, a, e):
    return sharpe_m(monthly(to_df(data, {p: r for p, r in draw.items() if r is not None}), a, e))


def conclude(D):
    if not D["D7"]:
        return "KHONG DU MAU"
    if all(D.values()):
        return "DAT"
    if D["D1"] and D["D2"]:
        return "CO TIN HIEU, CHUA DU"
    return "KHONG DAT"


def evaluate(data, n_rand=N_MIN, seed=SEED, allow_small=False, d2="shift"):
    if n_rand < N_MIN and not allow_small:
        raise ValueError("prereg needs >= %d draws" % N_MIN)
    ta, te = sig_g4.TRAIN
    wa, we = sig_g4.WFO
    cfgs = sig_g4.configs()
    dfs, tr, wf = [], [], []
    for c in cfgs:
        df = to_df(data, sim_g4.run_config(data, c))
        dfs.append(df)
        tr.append(metrics(df, ta, te))
        wf.append(metrics(df, wa, we))
    si = choose(cfgs, tr)
    c = cfgs[si]
    side = sig_g4.SIDES[c["side"]]
    res = sim_g4.run_config(data, c, want_path=True)
    dd_w = max_dd_mtm(data, res, wa, we)
    dd_t = max_dd_mtm(data, res, ta, te)
    x2 = metrics(to_df(data, sim_g4.run_config(data, c, cost_mult=2.0)), wa, we)
    real_ev = {}
    for p, r in res.items():
        tt = data["pairs"][p]["t"]
        m = (tt[r["event"]] >= sig_g4.tmin(wa)) & (tt[r["event"]] < sig_g4.tmin(we) + 1440)
        real_ev[p] = r["event"][m]
    real_s = wf[si]["sharpe_m"]
    rng = np.random.default_rng(seed)
    sp = shift_pool(data, real_ev, wa, we)
    sh = np.nan_to_num([draw_sharpe(data, shift_draw(data, sp, side, c["TS"], rng), wa, we) for _ in range(n_rand)])
    rp = random_pool(data, real_ev, wa, we)
    rng2 = np.random.default_rng(seed + 1)
    rd = np.nan_to_num([draw_sharpe(data, random_draw(data, rp, side, c["TS"], rng2), wa, we) for _ in range(n_rand)])
    p_shift = perm_p(sh, real_s) if np.isfinite(real_s) else float("nan")
    p_rand = perm_p(rd, real_s) if np.isfinite(real_s) else float("nan")
    p_d2 = p_shift if d2 == "shift" else p_rand
    W = wf[si]
    D = dict(D1=W["sharpe_m"] > 0.3, D2=p_d2 <= 0.05, D3=dd_w <= 0.25, D4=sum(m["total"] > 0 for m in wf) >= 0.6 * 12,
             D5=W["drop5pct_months_sum"] > 0, D6=x2["total"] > 0, D7=W["n_trades"] >= D7_MIN)
    D = {k: bool(v) for k, v in D.items()}
    strip = lambda m: {k: v for k, v in m.items() if not k.startswith("_")}
    return dict(selected=c["name"], selected_index=si,
                configs={cfgs[i]["name"]: dict(train_in_sample=strip(tr[i]), wfo=strip(wf[i])) for i in range(12)},
                selected_wfo=dict(strip(W), maxdd_mtm=dd_w), selected_train_in_sample=dict(maxdd_mtm=dd_t),
                wfo_cost_x2=strip(x2), median_wfo_total_12=float(np.median([m["total"] for m in wf])),
                controls=dict(n=n_rand, d2_basis=d2, p_day_shift=p_shift, p_random_same_hour_month=p_rand,
                              shift_mean_sharpe=float(np.mean(sh)), random_mean_sharpe=float(np.mean(rd))),
                criteria=D, conclusion=conclude(D), n_trials_for_dsr=12)


def to_markdown(rep):
    L = ["# G4 eval (TRAIN numbers tagged [in-sample])", "selected %s; conclusion %s; criteria %s" % (
        rep["selected"], rep["conclusion"], rep["criteria"]), "controls %s" % rep["controls"], "",
         "| config | TRAIN Sharpe_m [in-sample] | TRAIN trades [in-sample] | WFO Sharpe_m | WFO total | WFO trades | WFO bp/trade |",
         "|---|---|---|---|---|---|---|"]
    for k, v in rep["configs"].items():
        a, b = v["train_in_sample"], v["wfo"]
        L.append("| %s | %.3f [in-sample] | %d [in-sample] | %.3f | %.4f | %d | %.2f |" % (
            k, a["sharpe_m"], a["n_trades"], b["sharpe_m"], b["total"], b["n_trades"], b["mean_bp_after_cost"]))
    return "\n".join(L) + "\n"


def dumps(rep):
    return json.dumps(rep, sort_keys=True, default=str, indent=1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--real", default=None)
    ap.add_argument("--nrand", type=int, default=N_MIN)
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--d2", default="shift", choices=("shift", "random"))
    ap.add_argument("--out", default=os.path.expanduser("~/claude_master/w3/fx/g4/out"))
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    sim_g4.unlock_real(a.real)
    data = load_g4.load()
    rep = evaluate(data, a.nrand, a.seed, d2=a.d2)
    s = dumps(rep)
    open(os.path.join(a.out, "eval_g4.json"), "w").write(s)
    open(os.path.join(a.out, "eval_g4.md"), "w").write(to_markdown(rep))
    LOG.info("wrote eval_g4.json sha256=%s", hashlib.sha256(s.encode()).hexdigest())


if __name__ == "__main__":
    main()
