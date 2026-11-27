"""FX G2 evaluation (PREREG_FX_G2 sec 3 selection, sec 5 metrics/controls, sec 6 criteria D1-D6, MASTER chot).
Re-uses audited G1 metrics / p-value (ERRATA3 K1) / drop-best-months (ERRATA2 J3). Real data locked (real_token).
"""
import argparse
import json
import logging
import math
import os

import numpy as np
import pandas as pd

import load_g2 as L2
import sim_g2 as S2
import sim_g1 as S1
import eval_g1 as E1

LOG = logging.getLogger("g2.eval")
TRAIN = ("1975-01-01", "2005-12-31")
TRAIN_A = ("1975-01-01", "1989-12-31")
TRAIN_B = ("1990-01-01", "2005-12-31")
WFO = ("2006-01-01", "2019-12-31")
WFO_H1 = ("2006-01-01", "2012-12-31")
WFO_H2 = ("2013-01-01", "2019-12-31")
PERIODS = [("2006-01-01", "2008-12-31"), ("2009-01-01", "2012-12-31"), ("2013-01-01", "2019-12-31")]
WFO_SIG_START = pd.Period("2005-12", "M")
N_SHIFT = 1000
N_IID = 1000
SEED = 20261127
IS = "[in-sample]"
D1_SHARPE = 0.3
D2_P = 0.05
D2_MIN_N = 1000
D3_MAXDD = 0.25
D4_FRAC = 0.6
SHIFT_MIN = 12
metrics = E1.metrics
p_value = E1.p_value
drop_best_months = E1.drop_best_months
monthly_returns = E1.monthly_returns


def select(rows):
    """Highest TRAIN Sharpe; ties -> fewer parameters: F0 before V10 before V20, then longer L (L12, L3, L1), C last."""
    fo = {None: 0, 0.10: 1, 0.20: 2}
    so = {"L12": 0, "L3": 1, "L1": 2, "C": 3}
    return sorted(rows, key=lambda r: (-r["train"]["sharpe"], fo[r["X"]], so[r["sig"]]))[0]


def criteria(sharpe, p, n_shift, maxdd, n_pos, n_cfg, drop5_total, x2_cagr):
    return dict(D1=bool(sharpe > D1_SHARPE), D2=bool(n_shift >= D2_MIN_N and p <= D2_P), D3=bool(maxdd <= D3_MAXDD),
                D4=bool(n_pos >= D4_FRAC * n_cfg), D5=bool(drop5_total > 0), D6=bool(x2_cagr > 0))


def verdict_of(D):
    if all(D.values()):
        return "DAT"
    if D["D1"] and D["D2"]:
        return "CO TIN HIEU, CHUA DU"
    return "KHONG DAT"


def circular_shift(S, U, rng, kmin=SHIFT_MIN):
    """Main structure-preserving control: per currency, circularly shift its WFO monthly (post-filter) signal series by
    an independent random k in [kmin, n - kmin]; positions outside the universe of the target month are dropped."""
    n = S.shape[0]
    out = np.zeros_like(S)
    ks = []
    for j in range(S.shape[1]):
        k = int(rng.integers(kmin, n - kmin + 1))
        ks.append(k)
        out[:, j] = np.roll(S[:, j], k)
    return np.where(U, out, 0.0), ks


def iid_signs(U, rng):
    return np.where(U, rng.choice([-1.0, 1.0], size=U.shape), 0.0)


def evaluate(data, n_shift=N_SHIFT, n_iid=N_IID, seed=SEED, real_token=None):
    S1.check_real(data, real_token)

    def sim(*a, **kw):
        return S2.simulate(*a, real_token=real_token, **kw)

    cfgs = [c for c in S2.configs() if c["X"] is None or getattr(data, "reer", None) is not None]
    res_all, rows = {}, []
    for cfg in cfgs:
        res = sim(data, cfg)
        res_all[cfg["name"]] = res
        fl = res["filter"]
        wm = np.array([m >= "2006-01" for m in fl["months"]])
        rows.append(dict(name=cfg["name"], sig=cfg["sig"], X=cfg["X"], train=metrics(data, res, TRAIN),
                         train_7589=metrics(data, res, TRAIN_A), train_9005=metrics(data, res, TRAIN_B),
                         wfo=metrics(data, res, WFO), wfo_h1=metrics(data, res, WFO_H1), wfo_h2=metrics(data, res, WFO_H2),
                         periods={"%s..%s" % p: metrics(data, res, p) for p in PERIODS},
                         pct_filtered_wfo=float(fl["nfilt"][wm].sum() / max(1, fl["nraw"][wm].sum()))))
    sel = select(rows)
    cfg = next(c for c in cfgs if c["name"] == sel["name"])
    LOG.info("selected (TRAIN Sharpe) %s", sel["name"])
    # ---- main control: circular block shift on WFO (same sizing, costs, engine)
    base = sim(data, cfg, start=WFO_SIG_START)
    real_wfo_only = metrics(data, base, WFO)["sharpe"]
    recs = [r for r in S2.signal_table(data) if r["m"] >= WFO_SIG_START]
    S, V, U, _, _ = S2.config_signs(data, cfg, recs)
    rng = np.random.default_rng(seed)
    sh = []
    for _ in range(n_shift):
        So, _k = circular_shift(S, U, rng)
        rr = sim(data, cfg, start=WFO_SIG_START, S_override=So)
        sh.append(metrics(data, rr, WFO).get("sharpe", float("nan")))
    p, n_ge = p_value(sh, real_wfo_only)
    # ---- secondary controls (descriptive)
    rng2 = np.random.default_rng(seed + 1)
    iid = []
    for _ in range(n_iid):
        rr = sim(data, cfg, start=WFO_SIG_START, S_override=iid_signs(U, rng2))
        iid.append(metrics(data, rr, WFO).get("sharpe", float("nan")))
    p_iid, n_ge_iid = p_value(iid, real_wfo_only)
    bh = sim(data, cfg, equal_weight=True, S_override=None)
    ctrl_bh = dict(train=metrics(data, bh, TRAIN), wfo=metrics(data, bh, WFO))
    f0 = next(r for r in rows if r["sig"] == sel["sig"] and r["X"] is None)
    # ---- robustness
    mon = monthly_returns(data, res_all[sel["name"]], WFO)
    drop5_total, n_drop = drop_best_months(mon)
    x2 = sim(data, cfg, cost_mult=2.0)
    x2m = metrics(data, x2, WFO)
    n_pos = sum(1 for r in rows if r["wfo"]["cagr"] > 0)
    D = criteria(sel["wfo"]["sharpe"], p, n_shift, sel["wfo"]["maxdd"], n_pos, len(rows), drop5_total, x2m["cagr"])
    verdict = verdict_of(D)
    vf = {}
    for sname in S2.SIGNALS:
        r0 = next((r for r in rows if r["sig"] == sname and r["X"] is None), None)
        for X in (0.10, 0.20):
            rv = next((r for r in rows if r["sig"] == sname and r["X"] == X), None)
            if r0 and rv:
                vf[rv["name"]] = all(rv[h]["sharpe"] > r0[h]["sharpe"] for h in ("wfo_h1", "wfo_h2"))
    med = {k: float(np.median([r["wfo"][k] for r in rows])) for k in ("sharpe", "cagr", "maxdd", "calmar")}
    out = dict(configs=rows, selected=sel["name"], median_wfo=med, n_configs=len(rows),
               control_shift=dict(n=n_shift, seed=seed, n_ge=n_ge, p=p, real_sharpe_wfo_only=real_wfo_only,
                                  real_sharpe_fullrun=sel["wfo"]["sharpe"], median=float(np.nanmedian(sh)),
                                  p95=float(np.nanquantile(sh, 0.95))),
               control_iid=dict(label="mo ta", n=n_iid, n_ge=n_ge_iid, p=p_iid, median=float(np.nanmedian(iid))),
               control_buyhold=ctrl_bh, control_f0_same_L=dict(name=f0["name"], wfo=f0["wfo"]),
               drop_best5=dict(n_dropped=n_drop, n_months=int(len(mon)), total_ret_rest=drop5_total),
               cost_x2=x2m, D=D, n_pos_wfo=n_pos, verdict=verdict,
               value_filter_improves_both_halves=dict(label="mo ta, ngoai tieu chi", by_config=vf))
    out["_res"] = res_all
    return out


def _f(x, pct=False):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "nan"
    return ("%.2f%%" % (100 * x)) if pct else ("%.3f" % x)


def report_md(out):
    R = ["# EVAL_G2 (TRAIN %s..%s %s; WFO %s..%s)" % (TRAIN[0], TRAIN[1], IS, WFO[0], WFO[1]), "",
         "Excess return vs USD cash at 0; swap from OECD rates m-1 net of 1 %/yr margin. Sharpe on daily returns.", "",
         "| config | TRAIN Sharpe %s | TRAIN 75-89 Sharpe %s | TRAIN 90-05 Sharpe %s | WFO Sharpe | WFO CAGR | WFO maxDD | "
         "H1 Sharpe | H2 Sharpe | 06-08 | 09-12 | 13-19 | WFO turnover/yr | WFO %% filtered |" % (IS, IS, IS),
         "|" + "---|" * 14]
    for r in out["configs"]:
        pr = [r["periods"]["%s..%s" % p]["sharpe"] for p in PERIODS]
        R.append("| %s | %s %s | %s %s | %s %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |" % (
            r["name"], _f(r["train"]["sharpe"]), IS, _f(r["train_7589"]["sharpe"]), IS, _f(r["train_9005"]["sharpe"]), IS,
            _f(r["wfo"]["sharpe"]), _f(r["wfo"]["cagr"], 1), _f(r["wfo"]["maxdd"], 1), _f(r["wfo_h1"]["sharpe"]),
            _f(r["wfo_h2"]["sharpe"]), _f(pr[0]), _f(pr[1]), _f(pr[2]), _f(r["wfo"]["turnover_per_year"]),
            _f(r["pct_filtered_wfo"], 1)))
    R += ["", "Selected (max TRAIN Sharpe %s): **%s**" % (IS, out["selected"]),
          "Median of %d configs on WFO: %s" % (out["n_configs"], json.dumps(out["median_wfo"])),
          "Main control (circular block shift, per ccy, k in [12, n-12]): %s" % json.dumps(out["control_shift"]),
          "Secondary (mo ta) iid random signs: %s" % json.dumps(out["control_iid"]),
          "Secondary (mo ta) buy-hold equal weight: TRAIN %s Sharpe %s / WFO Sharpe %s" % (
              IS, _f(out["control_buyhold"]["train"].get("sharpe")), _f(out["control_buyhold"]["wfo"].get("sharpe"))),
          "Secondary (mo ta) F0 same L %s WFO Sharpe %s" % (out["control_f0_same_L"]["name"],
                                                           _f(out["control_f0_same_L"]["wfo"]["sharpe"])),
          "Drop best 5%% months (WFO): %s" % json.dumps(out["drop_best5"]),
          "Cost x2 (WFO): Sharpe %s CAGR %s" % (_f(out["cost_x2"]["sharpe"]), _f(out["cost_x2"]["cagr"], 1)),
          "Value filter improves Sharpe vs F0 in both WFO halves (mo ta, ngoai tieu chi): %s" % json.dumps(
              out["value_filter_improves_both_halves"]["by_config"]),
          "", "| criterion | pass |", "|---|---|"]
    for k, v in out["D"].items():
        R.append("| %s | %s |" % (k, v))
    R += ["", "**Ket luan: %s**" % out["verdict"]]
    return "\n".join(R) + "\n"


def main():
    ap = argparse.ArgumentParser(description="G2 evaluation")
    ap.add_argument("--real", default=None, help="must be %s (after A1 audit)" % S1.REAL_TOKEN)
    ap.add_argument("--data", default=L2.DEFAULT_DATA)
    ap.add_argument("--reer", default=None)
    ap.add_argument("--out", default=os.path.expanduser("~/claude_master/w3/fx/g2/out"))
    a = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s")
    if a.real != S1.REAL_TOKEN:
        LOG.error("real-data run locked: pass --real %s only after A1 audit PASS", S1.REAL_TOKEN)
        raise SystemExit(2)
    data = L2.load(a.data, reer_path=a.reer)
    out = evaluate(data, real_token=a.real)
    out.pop("_res")
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "EVAL_G2.json"), "w") as fh:
        json.dump(out, fh, indent=1, default=str)
    with open(os.path.join(a.out, "EVAL_G2.md"), "w") as fh:
        fh.write(report_md(out))
    LOG.info("verdict %s", out["verdict"])


if __name__ == "__main__":
    main()
