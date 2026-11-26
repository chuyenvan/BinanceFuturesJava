"""FX G1 evaluation (PREREG_FX_G1 sec 5 selection, sec 7 metrics/controls, sec 8 criteria D1-D7, ERRATA1 H1).

Real-data run is locked: requires --real I_HAVE_A1_PASS. The core `evaluate(data)` is data-agnostic (used by tests on
synthetic data).
"""
import argparse
import json
import logging
import math
import os

import numpy as np
import pandas as pd

import load_g1 as L
import sim_g1 as S

LOG = logging.getLogger("g1.eval")
TRAIN = ("1994-01-01", "2005-12-31")
WFO = ("2006-01-01", "2019-12-31")
WFO_H1 = ("2006-01-01", "2012-12-31")
WFO_H2 = ("2013-01-01", "2019-12-31")
N_RANDOM = 500
SEED = 20261126
IS = "[in-sample]"
D1_SHARPE = 0.3
D2_P = 0.05
D2_MIN_N = 500
D3_MAXDD = 0.25
D4_FRAC = 0.6


def _slice(data, res, period):
    lo, hi = pd.Timestamp(period[0]), pd.Timestamp(period[1])
    m = (data.dates >= lo) & (data.dates <= hi) & ~np.isnan(res["ret"])
    return m


def metrics(data, res, period, drop_mask=None):
    m = _slice(data, res, period)
    if drop_mask is not None:
        m = m & ~drop_mask
    r = res["ret"][m]
    dts = data.dates[m]
    out = dict(n_days=int(len(r)))
    if len(r) < 2:
        return out
    years = ((dts[-1] - dts[0]).days + 1) / 365.25
    ppy = len(r) / years
    mu, sd = r.mean(), r.std(ddof=1)
    eq = np.cumprod(1 + r)
    peak = np.maximum.accumulate(np.concatenate([[1.0], eq]))[1:]
    dd = float((1 - eq / peak).max())
    cagr = float(eq[-1] ** (1 / years) - 1)
    s = pd.Series(r, index=dts)
    mon = (1 + s).groupby(s.index.to_period("M")).prod() - 1
    yr = (1 + s).groupby(s.index.year).prod() - 1
    out.update(ann_ret_arith=float(mu * ppy), cagr=cagr, ann_vol=float(sd * math.sqrt(ppy)),
               sharpe=float(mu / sd * math.sqrt(ppy)) if sd > 0 else 0.0, maxdd=dd,
               calmar=(cagr / dd if dd > 0 else (float("inf") if cagr > 0 else 0.0)),
               skew_month=float(mon.skew()) if len(mon) > 2 else float("nan"), worst_month=float(mon.min()),
               pct_pos_years=float((yr > 0).mean()), n_months=int(len(mon)))
    st = res["state"][m]
    out["pct_time_gate_closed"] = float(np.mean(st == "gate"))
    tr = res["trades"]
    if len(tr):
        td = pd.to_datetime(tr["date"])
        tm = (td >= pd.Timestamp(period[0])) & (td <= pd.Timestamp(period[1]))
        out["turnover_per_year"] = float(tr.loc[tm, "traded_frac"].sum() / years)
    else:
        out["turnover_per_year"] = 0.0
    ev = res["events"]
    if len(ev):
        ed = pd.to_datetime(ev["date"])
        em = (ev["kind"] == "rebal") & (ed >= pd.Timestamp(period[0]) - pd.Timedelta(days=31)) & (ed <= pd.Timestamp(period[1]))
        out["ccys_per_year"] = {str(y): float(g["n_univ"].mean()) for y, g in ev[em].groupby(ed[em].dt.year)}
    return out


def monthly_returns(data, res, period):
    m = _slice(data, res, period)
    s = pd.Series(res["ret"][m], index=data.dates[m])
    return (1 + s).groupby(s.index.to_period("M")).prod() - 1


def drop_best_months(mon, frac=0.05):
    nd = int(math.ceil(frac * len(mon)))
    kept = mon.sort_values().iloc[:len(mon) - nd]
    return float((1 + kept).prod() - 1), nd


def select(cfg_results):
    """Highest TRAIN Sharpe; ties -> smaller k, then gate OFF first (then GATES order)."""
    def key(c):
        return (-c["train"]["sharpe"], c["k"], S.GATES.index(c["gate"]))
    return sorted(cfg_results, key=key)[0]


def p_value(rnd, real_sharpe):
    """ERRATA3 K1: p = (1 + #(random >= real)) / (N + 1); NaN random Sharpe counted as >= real (conservative)."""
    rnd = np.asarray(rnd, dtype=float)
    n_ge = int(np.sum((rnd >= real_sharpe) | np.isnan(rnd)))
    return (1 + n_ge) / (len(rnd) + 1), n_ge


def criteria(sharpe, p, n_random, maxdd, n_pos, n_cfg, d5, drop5_total, x2_cagr):
    return dict(D1=bool(sharpe > D1_SHARPE), D2=bool(n_random >= D2_MIN_N and p <= D2_P), D3=bool(maxdd <= D3_MAXDD),
                D4=bool(n_pos >= D4_FRAC * n_cfg), D5=bool(d5), D6=bool(drop5_total > 0), D7=bool(x2_cagr > 0))


def verdict_of(D):
    if all(D.values()):
        return "DAT"
    if D["D1"] and D["D2"]:
        return "CO TIN HIEU, CHUA DU"
    return "KHONG DAT"


def evaluate(data, n_random=N_RANDOM, seed=SEED, flags=None, real_token=None):
    S.check_real(data, real_token)

    def sim(*a, **kw):
        return S.simulate(*a, real_token=real_token, **kw)

    res_all, rows = {}, []
    for cfg in S.configs():
        res = sim(data, cfg["k"], cfg["gate"])
        res_all[cfg["name"]] = res
        rows.append(dict(name=cfg["name"], k=cfg["k"], gate=cfg["gate"],
                         train=metrics(data, res, TRAIN), wfo=metrics(data, res, WFO),
                         wfo_h1=metrics(data, res, WFO_H1), wfo_h2=metrics(data, res, WFO_H2)))
    sel = select(rows)
    LOG.info("selected (TRAIN Sharpe) %s", sel["name"])
    k, gate = sel["k"], sel["gate"]
    # controls
    bh = sim(data, 1, None, mode="buyhold")
    ctrl_bh = dict(train=metrics(data, bh, TRAIN), wfo=metrics(data, bh, WFO))
    nogate = next(r for r in rows if r["k"] == k and r["gate"] is None)
    rng = np.random.default_rng(seed)
    rnd = []
    for i in range(n_random):
        rr = sim(data, k, gate, mode="random", rng=rng)
        rnd.append(metrics(data, rr, WFO).get("sharpe", float("nan")))
    rnd = np.array(rnd)
    real_sh = sel["wfo"]["sharpe"]
    p, n_ge = p_value(rnd, real_sh)
    # robustness
    mon = monthly_returns(data, res_all[sel["name"]], WFO)
    drop5_total, n_drop = drop_best_months(mon)
    x2 = sim(data, k, gate, cost_mult=2.0)
    x2m = metrics(data, x2, WFO)
    # D5
    if gate is None:
        gated = [r for r in rows if r["k"] == k and r["gate"] is not None]
        d5_cfg = select(gated)
        d5_note = "selected is gate OFF -> D5 uses best-TRAIN gated config with same k: %s" % d5_cfg["name"]
    else:
        d5_cfg = sel
        d5_note = "selected gated config %s vs k%d_OFF" % (sel["name"], k)
    d5 = all(d5_cfg[h]["calmar"] > nogate[h]["calmar"] for h in ("wfo_h1", "wfo_h2"))
    n_pos = sum(1 for r in rows if r["wfo"]["cagr"] > 0)
    D = criteria(sel["wfo"]["sharpe"], p, n_random, sel["wfo"]["maxdd"], n_pos, len(rows), d5, drop5_total, x2m["cagr"])
    verdict = verdict_of(D)
    # ERRATA3 K5 (descriptive, outside criteria): carry at the holding month's own rates
    hold = sim(data, k, gate, carry_rates="holding")
    k5 = dict(label="mo ta, ngoai tieu chi", config=sel["name"], train=metrics(data, hold, TRAIN),
              wfo=metrics(data, hold, WFO))
    med = {}
    for key in ("sharpe", "cagr", "maxdd", "calmar"):
        med[key] = float(np.median([r["wfo"][key] for r in rows]))
    out = dict(configs=rows, selected=sel["name"], median_wfo_12=med, control_buyhold=ctrl_bh,
               control_nogate=dict(name=nogate["name"], wfo=nogate["wfo"]),
               control_random=dict(n=n_random, seed=seed, n_ge=n_ge, p=p, real_sharpe=real_sh,
                                   rand_median=float(np.median(rnd)), rand_p95=float(np.quantile(rnd, 0.95))),
               drop_best5=dict(n_dropped=n_drop, n_months=int(len(mon)), total_ret_rest=drop5_total),
               cost_x2=x2m, D=D, D5_note=d5_note, n_pos_wfo=n_pos, verdict=verdict, k5_carry_holding_month=k5)
    if flags is not None:
        out["h1_drop_flagged_days"] = dict(n_flag_days_wfo=int(flags[_slice(data, res_all[sel["name"]], WFO)].sum()),
                                           wfo=metrics(data, res_all[sel["name"]], WFO, drop_mask=flags.to_numpy()))
    out["_res"] = res_all
    return out


def _f(x, pct=False):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "nan"
    return ("%.2f%%" % (100 * x)) if pct else ("%.3f" % x)


def report_md(out):
    L_ = ["# EVAL_G1 (TRAIN %s..%s %s; WFO %s..%s)" % (TRAIN[0], TRAIN[1], IS, WFO[0], WFO[1]), ""]
    L_.append("Excess return vs USD cash at 0 (strategy already nets the rate differential). Sharpe on daily returns.")
    L_.append("")
    L_.append("| config | TRAIN Sharpe %s | TRAIN CAGR %s | TRAIN maxDD %s | WFO Sharpe | WFO CAGR | WFO maxDD | WFO Calmar | "
              "H1 Calmar | H2 Calmar | WFO skew_m | WFO worst_m | WFO %%pos_yr | WFO turnover/yr | WFO %%gate |" % (IS, IS, IS))
    L_.append("|" + "---|" * 15)
    for r in out["configs"]:
        t, w = r["train"], r["wfo"]
        L_.append("| %s | %s %s | %s %s | %s %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
            r["name"], _f(t["sharpe"]), IS, _f(t["cagr"], 1), IS, _f(t["maxdd"], 1), IS, _f(w["sharpe"]),
            _f(w["cagr"], 1), _f(w["maxdd"], 1), _f(w["calmar"]), _f(r["wfo_h1"]["calmar"]), _f(r["wfo_h2"]["calmar"]),
            _f(w["skew_month"]), _f(w["worst_month"], 1), _f(w["pct_pos_years"], 1), _f(w["turnover_per_year"]),
            _f(w["pct_time_gate_closed"], 1)))
    L_ += ["", "Selected (max TRAIN Sharpe %s): **%s**" % (IS, out["selected"]),
           "Median of 12 configs on WFO: %s" % json.dumps(out["median_wfo_12"]),
           "Control buy-hold (TRAIN %s / WFO): %s / %s" % (IS, _f(out["control_buyhold"]["train"].get("sharpe")),
                                                          _f(out["control_buyhold"]["wfo"].get("sharpe"))),
           "Control no-gate %s WFO Sharpe: %s" % (out["control_nogate"]["name"], _f(out["control_nogate"]["wfo"]["sharpe"])),
           "Control random: %s" % json.dumps(out["control_random"]),
           "Drop best 5%% months (WFO): %s" % json.dumps(out["drop_best5"]),
           "Cost x2 (WFO): Sharpe %s CAGR %s" % (_f(out["cost_x2"]["sharpe"]), _f(out["cost_x2"]["cagr"], 1)),
           "D5: %s" % out["D5_note"], "", "| criterion | pass |", "|---|---|"]
    for k_, v in out["D"].items():
        L_.append("| %s | %s |" % (k_, v))
    L_ += ["", "**Ket luan: %s**" % out["verdict"]]
    k5 = out["k5_carry_holding_month"]
    L_ += ["", "ERRATA3 K5 (mo ta, ngoai tieu chi): %s with carry at holding-month rates: TRAIN %s Sharpe %s; WFO Sharpe %s "
           "CAGR %s maxDD %s" % (k5["config"], IS, _f(k5["train"].get("sharpe")), _f(k5["wfo"].get("sharpe")),
                                 _f(k5["wfo"].get("cagr"), 1), _f(k5["wfo"].get("maxdd"), 1))]
    if "h1_drop_flagged_days" in out:
        h = out["h1_drop_flagged_days"]
        L_ += ["", "ERRATA1 H1 (descriptive only): WFO excluding %d FRED/ECB-flagged days: Sharpe %s CAGR %s maxDD %s" % (
            h["n_flag_days_wfo"], _f(h["wfo"]["sharpe"]), _f(h["wfo"]["cagr"], 1), _f(h["wfo"]["maxdd"], 1))]
    return "\n".join(L_) + "\n"


def main():
    ap = argparse.ArgumentParser(description="G1 evaluation")
    ap.add_argument("--real", default=None, help="must be %s (after A1 audit)" % S.REAL_TOKEN)
    ap.add_argument("--data", default=L.DEFAULT_DATA)
    ap.add_argument("--out", default=os.path.expanduser("~/claude_master/w3/fx/g1/out"))
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    if a.real != S.REAL_TOKEN:
        LOG.error("real-data run locked: pass --real %s only after A1 audit PASS", S.REAL_TOKEN)
        raise SystemExit(2)
    data = L.load(a.data)
    flags = L.ecb_flag_dates(data, a.data)
    out = evaluate(data, flags=flags, real_token=a.real)
    out.pop("_res")
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "EVAL_G1.json"), "w") as fh:
        json.dump(out, fh, indent=1, default=str)
    with open(os.path.join(a.out, "EVAL_G1.md"), "w") as fh:
        fh.write(report_md(out))
    LOG.info("verdict %s", out["verdict"])


if __name__ == "__main__":
    main()
