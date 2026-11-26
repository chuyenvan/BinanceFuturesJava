#!/usr/bin/env python3
"""G3 evaluation (prereg sec 4, 6, 7). Direction chosen ONLY on TRAIN per group (sign of mean TRAIN daily return of
W52/H4 under H_TD; tie -> no trading for that group), frozen for WFO. Config per group = best TRAIN Sharpe of its 4 configs.
Combined = equal mean of the 3 selected configs over the common WFO window 2013-01..2019-12.
Every TRAIN figure is tagged [in-sample]. Real data needs --real I_HAVE_A1_PASS. Never reads >= 2020 (loader cutoff).
"""
import argparse
import hashlib
import json
import logging
import math
import os

import numpy as np
import pandas as pd

import load_g3
import sig_g3
import sim_g3

LOG = logging.getLogger("g3.eval")
CONFIGS = [(52, 1), (52, 4), (156, 1), (156, 4)]
COMMON_WFO = ("2013-01-01", "2019-12-31")
N_RAND_MIN = 500
SEED = 20261126


def _sl(s, a, e):
    return s[(s.index >= pd.Timestamp(a)) & (s.index <= pd.Timestamp(e))]


def max_dd(r):
    eq = 1.0 + r.cumsum()
    peak = np.maximum.accumulate(np.maximum(eq.values, 1.0))
    return float(np.max((peak - eq.values) / peak)) if len(eq) else 0.0


def sharpe(r):
    sd = r.std(ddof=1)
    return float(r.mean() / sd * math.sqrt(252)) if len(r) > 2 and sd > 0 else float("nan")


def drop_top_weeks(r, frac=0.05):
    wk = r.resample("W-FRI").sum()
    k = int(math.ceil(frac * len(wk)))
    return float(wk.sort_values().iloc[:len(wk) - k].sum()) if len(wk) else 0.0


def metrics(res, a, e, trades_in=None):
    d = _sl(res["daily"], a, e)
    r = d["ret"]
    yrs = max(len(r) / 252.0, 1e-9)
    tr = res["trades"]
    tr = tr[(tr["entry_date"] >= pd.Timestamp(a)) & (tr["entry_date"] <= pd.Timestamp(e))]
    dd = max_dd(r)
    ann = float(r.mean() * 252) if len(r) else 0.0
    pc = _sl(res["per_ccy"], a, e).sum()
    tot = float(pc.sum())
    return dict(ann_ret=ann, ann_vol=float(r.std(ddof=1) * math.sqrt(252)) if len(r) > 2 else float("nan"),
                sharpe=sharpe(r), maxdd=dd, calmar=(ann / dd if dd > 0 else float("nan")),
                skew_daily=float(r.skew()) if len(r) > 2 else float("nan"), hit_rate=float((tr["net_ret_unit"] > 0).mean())
                if len(tr) else float("nan"), n_trades=int(len(tr)), turnover_per_yr=float(d["turnover"].sum() / yrs),
                mean_daily=float(r.mean()) if len(r) else 0.0, price_ann=float(d["price"].mean() * 252),
                swap_ann=float(d["swap"].mean() * 252), margin_ann=float(d["margin"].mean() * 252),
                cost_ann=float(d["cost"].mean() * 252), drop5pct_weeks_sum=drop_top_weeks(r),
                max_ccy_share=(float(pc.max() / tot) if tot > 0 else float("nan")),
                max_ccy=(str(pc.idxmax()) if len(pc) else ""))


D9_MIN = 150


def d9_ok(n):
    return n >= D9_MIN


def perm_p(rand_stats, real_stat):
    """ERRATA3 K1: p = (1 + #(rand >= real)) / (N + 1)."""
    r = np.asarray(rand_stats, dtype=float)
    return float((1 + np.sum(r >= real_stat)) / (len(r) + 1))


def shift_pool(data, book, direction, H, a, e):
    """K4 (descriptive): per ccy, the real signal sequence over its eligible weeks in [a, e]."""
    el = book[book["eligible"] & (book["entry_date"] >= pd.Timestamp(a)) & (book["entry_date"] <= pd.Timestamp(e))]
    out = []
    for c, g in el.groupby("ccy", sort=True):
        ex = sim_g3.first_valid_vec(data, g["ccy"].values, pd.DatetimeIndex(g["anchor"]) + pd.Timedelta(days=7 * H))
        out.append(dict(ccy=c, report_date=g["date"].values, anchor=g["anchor"].values, entry_date=g["entry_date"].values,
                        exit_date=ex.values, N=g["N_dt"].values.astype(float), s=direction * g["signal"].values.astype(float)))
    return dict(cells=out, H=H)


def shift_tranches(pool, rng):
    """Circular shift of each ccy's signal sequence by a random lag (keeps clustering of signals)."""
    parts = []
    for c in pool["cells"]:
        L = len(c["s"])
        s = np.roll(c["s"], int(rng.integers(1, L)) if L > 1 else 0)
        m = s != 0
        parts.append(pd.DataFrame(dict(ccy=c["ccy"], report_date=c["report_date"][m], anchor=c["anchor"][m],
                                       entry_date=c["entry_date"][m], exit_date=c["exit_date"][m], sign=s[m],
                                       w=s[m] / (c["N"][m] * pool["H"]), z=np.nan)))
    if not parts:
        return pd.DataFrame(columns=["ccy", "entry_date", "exit_date", "w", "sign", "anchor", "report_date", "z"])
    return pd.concat(parts, ignore_index=True)


def choose_direction(train_ret, train_end):
    """Uses ONLY the TRAIN slice. +1 H_TD, -1 H_ND, 0 tie -> no trading."""
    assert len(train_ret) == 0 or train_ret.index.max() <= pd.Timestamp(train_end), "direction choice saw post-TRAIN data"
    mu = float(train_ret.mean()) if len(train_ret) else 0.0
    return 1 if mu > 0 else (-1 if mu < 0 else 0)


def random_pool(data, book, real_tr, H, a, e):
    """Precompute candidates: eligible weeks of each ccy-year in [a, e] and the real signs of that ccy-year."""
    elig = book[book["eligible"] & (book["entry_date"] >= pd.Timestamp(a)) & (book["entry_date"] <= pd.Timestamp(e))]
    elig = elig.reset_index(drop=True)
    ex = sim_g3.first_valid_vec(data, elig["ccy"].values, pd.DatetimeIndex(elig["anchor"]) + pd.Timedelta(days=7 * H))
    arr = dict(ccy=elig["ccy"].values, report_date=elig["date"].values, anchor=elig["anchor"].values,
               entry_date=elig["entry_date"].values, exit_date=ex.values, N=elig["N_dt"].values.astype(float))
    ey = pd.DatetimeIndex(elig["entry_date"]).year.values
    cells = []
    rt = real_tr.assign(year=pd.DatetimeIndex(real_tr["entry_date"]).year)
    for (ccy, yr), g in rt.groupby(["ccy", "year"], sort=True):
        cand = np.flatnonzero((arr["ccy"] == ccy) & (ey == yr))
        cells.append((cand, g["sign"].values.astype(float)))
    return dict(arr=arr, cells=cells, H=H)


def random_tranches(pool, rng):
    """Same #trades per ccy x year, same H, random entry weeks among eligible weeks of that ccy-year, signs permuted
    (keeps the real long/short ratio)."""
    idx, sg = [], []
    for cand, signs in pool["cells"]:
        kk = len(signs)
        idx.append(cand[np.sort(rng.choice(len(cand), size=kk, replace=kk > len(cand)))])
        sg.append(rng.permutation(signs))
    if not idx:
        return pd.DataFrame(columns=["ccy", "entry_date", "exit_date", "w", "sign", "anchor", "report_date", "z"])
    i = np.concatenate(idx)
    s = np.concatenate(sg)
    A = pool["arr"]
    return pd.DataFrame(dict(ccy=A["ccy"][i], report_date=A["report_date"][i], anchor=A["anchor"][i],
                             entry_date=A["entry_date"][i], exit_date=A["exit_date"][i], sign=s,
                             w=s / (A["N"][i] * pool["H"]), z=np.nan))


def carry_tranches(data, tr):
    rates = data["rates"]
    m1 = (pd.DatetimeIndex(tr["anchor"]).to_period("M") - 1).to_timestamp()
    rr = rates.reindex(m1)
    d = np.array([rr[c].values[i] - rr["USD"].values[i] for i, c in enumerate(tr["ccy"].values)])
    s = np.sign(np.nan_to_num(d))
    out = tr.copy()
    out["sign"] = s
    out["w"] = s * np.abs(tr["w"].values)
    return out[out["sign"] != 0]


def ic_by_year(data, book, a, e):
    b = book[book["eligible"] & (book["entry_date"] >= pd.Timestamp(a)) & (book["entry_date"] <= pd.Timestamp(e))]
    px = data["px"]
    out = {}
    for hw in (1, 4):
        x1 = sim_g3.first_valid_vec(data, b["ccy"].values, pd.DatetimeIndex(b["entry_date"]) + pd.Timedelta(days=7 * hw))
        p0 = np.array([px.at[t, c] for t, c in zip(b["entry_date"], b["ccy"])])
        p1 = np.array([px.at[t, c] if not pd.isna(t) else np.nan for t, c in zip(x1, b["ccy"])])
        f = pd.DataFrame(dict(z=b["z"].values, fwd=np.log(p1 / p0), yr=pd.DatetimeIndex(b["entry_date"]).year)).dropna()
        out["ic_%dw" % hw] = {int(y): float(g["z"].rank().corr(g["fwd"].rank())) for y, g in f.groupby("yr") if len(g) > 5}
    return out


def buy_hold(data, a, e):
    r = _sl(data["px"].pct_change(fill_method=None).mean(axis=1, skipna=True).fillna(0.0), a, e)
    return dict(ann_ret=float(r.mean() * 252), sharpe=sharpe(r), maxdd=max_dd(r))


def evaluate_group(data, g, n_rand, seed):
    P = sig_g3.PERIODS[g]
    (ta, te), (wa, we) = P["train"], P["wfo"]
    books = {W: sig_g3.build_book(data, g, W) for W in sig_g3.WS}
    tr_tr = sim_g3.make_tranches(data, books[52], 4, +1, start=ta, end=te)
    train_ret = _sl(sim_g3.simulate(data, tr_tr, close_at=te)["daily"]["ret"], ta, te)
    direction = choose_direction(train_ret, te)
    cfg = {}
    for W, H in CONFIGS:
        d_use = direction if direction != 0 else 1
        t_tr = sim_g3.make_tranches(data, books[W], H, d_use, start=ta, end=te)
        t_wf = sim_g3.make_tranches(data, books[W], H, d_use, start=wa, end=we)
        if direction == 0:
            t_tr, t_wf = t_tr.iloc[:0], t_wf.iloc[:0]
        r_tr = sim_g3.simulate(data, t_tr, close_at=te)
        r_wf = sim_g3.simulate(data, t_wf, close_at=we)  # K3: only WFO entries, force-closed at WFO end
        cfg[(W, H)] = dict(tr=t_wf, res=r_wf, train=metrics(r_tr, ta, te), wfo=metrics(r_wf, wa, we))
    order = sorted(CONFIGS, key=lambda c: (-(cfg[c]["train"]["sharpe"] if np.isfinite(cfg[c]["train"]["sharpe"]) else -1e9),
                                           CONFIGS.index(c)))
    sel = order[0]
    S = cfg[sel]
    W, H = sel
    tr_w = S["tr"]
    res2 = sim_g3.simulate(data, tr_w, cost_mult=2.0, close_at=we)
    wfo2 = metrics(res2, wa, we)
    wfo_net = metrics(sim_g3.simulate(data, tr_w, netting=True, close_at=we), wa, we)  # descriptive only (ERRATA2 J5)
    real_stat = sharpe(_sl(S["res"]["daily"]["ret"], wa, we))
    rng = np.random.default_rng(seed)
    rand_stats, rand_daily = [], []
    pool = random_pool(data, books[W], tr_w, H, wa, we)
    for _ in range(n_rand):
        rtr = random_tranches(pool, rng)
        rr = _sl(sim_g3.simulate(data, rtr, close_at=we)["daily"]["ret"], wa, we)
        rand_stats.append(sharpe(rr) if len(rtr) else 0.0)
        rand_daily.append(rr.values)
    rand_stats = np.nan_to_num(np.array(rand_stats), nan=0.0)
    p = perm_p(rand_stats, real_stat) if direction != 0 and np.isfinite(real_stat) else float("nan")
    # K4 descriptive: circular block shift control (not a criterion)
    sp = shift_pool(data, books[W], direction, H, wa, we)
    rng2 = np.random.default_rng(seed + 1000)
    shift_stats, shift_daily = [], []
    for _ in range(n_rand):
        st = shift_tranches(sp, rng2)
        rr = _sl(sim_g3.simulate(data, st, close_at=we)["daily"]["ret"], wa, we)
        shift_stats.append(sharpe(rr) if len(st) else 0.0)
        shift_daily.append(rr.values)
    shift_stats = np.nan_to_num(np.array(shift_stats), nan=0.0)
    p_shift = perm_p(shift_stats, real_stat) if direction != 0 and np.isfinite(real_stat) else float("nan")
    carry = metrics(sim_g3.simulate(data, carry_tranches(data, tr_w), close_at=we), wa, we) if len(tr_w) else None
    w52h4 = cfg[(52, 4)]["wfo"]["mean_daily"]
    tpy = S["tr"].assign(year=pd.DatetimeIndex(S["tr"]["entry_date"]).year).groupby(["ccy", "year"]).size()
    sw = S["wfo"]
    D = dict(D1=sw["sharpe"] > 0.3, D2=(p <= 0.05) if np.isfinite(p) else False, D3=sw["maxdd"] <= 0.25,
             D4=sum(cfg[c]["wfo"]["ann_ret"] > 0 for c in CONFIGS) >= 3, D6=sw["drop5pct_weeks_sum"] > 0,
             D7=wfo2["ann_ret"] > 0, D8=bool(w52h4 > 0), D9=d9_ok(sw["n_trades"]))
    D = {k: bool(v) for k, v in D.items()}
    return dict(group=g, direction={1: "H_TD", -1: "H_ND", 0: "TIE_NO_TRADE"}[direction],
                direction_basis_train_mean_daily_in_sample=float(train_ret.mean()) if len(train_ret) else 0.0,
                selected="W%d_H%d" % sel, configs={"W%d_H%d" % c: dict(train_in_sample=cfg[c]["train"], wfo=cfg[c]["wfo"])
                                                    for c in CONFIGS},
                wfo_cost_x2=wfo2, wfo_netting_descriptive_only=wfo_net, random=dict(n=n_rand, real_sharpe_wfo_entries=real_stat, p=p,
                                              rand_sharpe_mean=float(rand_stats.mean()) if n_rand else float("nan")),
                block_shift_DESCRIPTIVE_NOT_CRITERION=dict(n=n_rand, p=p_shift),
                carry_control_wfo=carry, buy_hold_wfo=buy_hold(data, wa, we), buy_hold_train_in_sample=buy_hold(data, ta, te),
                ic_train_in_sample=ic_by_year(data, books[W], ta, te), ic_wfo=ic_by_year(data, books[W], wa, we),
                trades_per_ccy_year={"%s_%d" % k: int(v) for k, v in tpy.items()}, criteria=D,
                conclusion=conclude(D, direction),
                _sel_daily=_sl(S["res"]["daily"]["ret"], *COMMON_WFO), _sel_daily_x2=_sl(res2["daily"]["ret"], *COMMON_WFO),
                _rand_common=[pd.Series(x, index=_sl(S["res"]["daily"]["ret"], wa, we).index) for x in rand_daily],
                _shift_common=[pd.Series(x, index=_sl(S["res"]["daily"]["ret"], wa, we).index) for x in shift_daily],
                _tr_sel=S["tr"], _wfo_ret={c: cfg[c]["wfo"]["ann_ret"] for c in CONFIGS})


def conclude(D, direction=1):
    if direction == 0:
        return "KHONG GIAO DICH (hoa chieu TRAIN)"
    if not D["D9"]:
        return "KHONG DU MAU"
    if all(D[k] for k in ("D1", "D2", "D3", "D4", "D6", "D7", "D8", "D9")):
        return "DAT"
    if D["D1"] and D["D2"]:
        return "CO TIN HIEU, CHUA DU"
    return "KHONG DAT"


def evaluate(data, n_rand=N_RAND_MIN, seed=SEED, allow_small=False):
    if n_rand < N_RAND_MIN and not allow_small:
        raise ValueError("prereg needs >= %d random draws" % N_RAND_MIN)
    G = {}
    for i, g in enumerate(load_g3.GROUPS):
        G[g] = evaluate_group(data, g, n_rand, seed + i)
    a, e = COMMON_WFO
    comb = pd.concat([G[g]["_sel_daily"] for g in G], axis=1).fillna(0.0).mean(axis=1)
    comb2 = pd.concat([G[g]["_sel_daily_x2"] for g in G], axis=1).fillna(0.0).mean(axis=1)
    rs = []
    for i in range(n_rand):
        rr = pd.concat([_sl(G[g]["_rand_common"][i], a, e) if G[g]["_rand_common"] else comb * 0 for g in G],
                       axis=1).fillna(0.0).mean(axis=1)
        rs.append(sharpe(rr))
    rs = np.nan_to_num(np.array(rs), nan=0.0)
    cs = sharpe(comb)
    p = perm_p(rs, cs) if np.isfinite(cs) else float("nan")
    ss = []
    for i in range(n_rand):
        rr = pd.concat([_sl(G[g]["_shift_common"][i], a, e) if G[g]["_shift_common"] else comb * 0 for g in G],
                       axis=1).fillna(0.0).mean(axis=1)
        ss.append(sharpe(rr))
    p_shift = perm_p(np.nan_to_num(np.array(ss), nan=0.0), cs) if np.isfinite(cs) else float("nan")
    ntr = sum(int(((G[g]["_tr_sel"]["entry_date"] >= pd.Timestamp(a)) & (G[g]["_tr_sel"]["entry_date"] <= pd.Timestamp(e))).sum())
              for g in G)
    n_pos = sum(int(v > 0) for g in G for v in G[g]["_wfo_ret"].values())
    D = dict(D1=cs > 0.3, D2=(p <= 0.05) if np.isfinite(p) else False, D3=max_dd(comb) <= 0.25, D4=n_pos >= 0.6 * 12,
             D6=drop_top_weeks(comb) > 0, D7=float(comb2.mean()) > 0,
             D8=sum(G[g]["criteria"]["D8"] for g in G if G[g]["direction"] != "TIE_NO_TRADE") >= 2, D9=d9_ok(ntr))
    D = {k: bool(v) for k, v in D.items()}
    med = float(np.median([v for g in G for v in G[g]["_wfo_ret"].values()]))
    combined = dict(window=COMMON_WFO, ann_ret=float(comb.mean() * 252), sharpe=cs, maxdd=max_dd(comb),
                    drop5pct_weeks_sum=drop_top_weeks(comb), cost_x2_ann_ret=float(comb2.mean() * 252), random_p=p,
                    block_shift_p_DESCRIPTIVE_NOT_CRITERION=p_shift,
                    n_trades=ntr, n_configs_wfo_pos=n_pos, median_wfo_ann_ret_12=med, criteria=D, conclusion=conclude(D))
    out = {g: {k: v for k, v in G[g].items() if not k.startswith("_")} for g in G}
    return dict(groups=out, combined=combined, n_rand=n_rand, seed=seed,
                n_trials_for_dsr=dict(configs=12, direction_choices=3))


def _fmt(v):
    return "%.4f" % v if isinstance(v, float) else str(v)


def to_markdown(rep):
    L = ["# G3 eval (TRAIN numbers tagged [in-sample])", ""]
    for g, r in rep["groups"].items():
        L.append("## %s: direction %s (TRAIN mean daily %s [in-sample]); selected %s; conclusion %s" % (
            g, r["direction"], _fmt(r["direction_basis_train_mean_daily_in_sample"]), r["selected"], r["conclusion"]))
        L.append("| config | TRAIN Sharpe [in-sample] | TRAIN ann_ret [in-sample] | WFO Sharpe | WFO ann_ret | WFO maxDD | WFO trades |")
        L.append("|---|---|---|---|---|---|---|")
        for c, m in r["configs"].items():
            L.append("| %s | %s [in-sample] | %s [in-sample] | %s | %s | %s | %d |" % (
                c, _fmt(m["train_in_sample"]["sharpe"]), _fmt(m["train_in_sample"]["ann_ret"]), _fmt(m["wfo"]["sharpe"]),
                _fmt(m["wfo"]["ann_ret"]), _fmt(m["wfo"]["maxdd"]), m["wfo"]["n_trades"]))
        L.append("random p=%s; cost x2 WFO ann_ret=%s; criteria %s" % (_fmt(r["random"]["p"]), _fmt(r["wfo_cost_x2"]["ann_ret"]),
                                                                    r["criteria"]))
        L.append("")
    c = rep["combined"]
    L.append("## combined %s..%s: Sharpe %s ann_ret %s maxDD %s p %s trades %d; criteria %s; conclusion %s" % (
        c["window"][0], c["window"][1], _fmt(c["sharpe"]), _fmt(c["ann_ret"]), _fmt(c["maxdd"]), _fmt(c["random_p"]),
        c["n_trades"], c["criteria"], c["conclusion"]))
    return "\n".join(L) + "\n"


def dumps(rep):
    return json.dumps(rep, sort_keys=True, default=str, indent=1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--real", default=None)
    ap.add_argument("--nrand", type=int, default=N_RAND_MIN)
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--out", default=os.path.expanduser("~/claude_master/w3/fx/g3/out"))
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    sim_g3.unlock_real(a.real)  # raises before loading data
    data = load_g3.load()
    rep = evaluate(data, a.nrand, a.seed)
    s = dumps(rep)
    open(os.path.join(a.out, "eval_g3.json"), "w").write(s)
    open(os.path.join(a.out, "eval_g3.md"), "w").write(to_markdown(rep))
    LOG.info("wrote eval_g3.json sha256=%s", hashlib.sha256(s.encode()).hexdigest())


if __name__ == "__main__":
    main()
