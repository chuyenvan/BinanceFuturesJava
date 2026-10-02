#!/usr/bin/env python3
"""audit_short_state_beta.py — AUDIT_SHORT_REVIEW_20261002 (0-sim, chi doc, nhe).

Tach BETA thi truong khoi drift SHORT cua tap STATE B (RESULT_SHORT_STATE A2), dung lai NGUYEN
build_states() cua short_state_0sim.py (causal, ctime = ts+1h). Forward 24h lay tu CLOSES_1H
(khong dung .pb) => so tuyet doi chi de doi chieu, cot quan trong la EXCESS so EW universe cung gio.
Bao: gross short, excess short (= -(r_coin - r_EW)), CI block-72h (ham ci_mean goc), theo nam,
beta OLS cua chuoi trung binh/gio, n_eff = N*(SE_iid/SE_block)^2. DEV 2022-01-01..2025-12-31.
KHONG sua thiet ke goc, KHONG tune, KHONG cham 2026.
"""
import json, logging, os, sys
import numpy as np
import pandas as pd

REPO = "/home/ubuntu/src/BinanceFuturesJava"
sys.path.insert(0, os.path.join(REPO, "research/analysis"))
import short_state_0sim as SS  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
L = logging.getLogger("audit")
H = 3600000
T0 = 1640995200000  # 2022-01-01 UTC
OUT = "/home/ubuntu/claude_master/1002/audit_short_state_beta.json"
COST = 0.00112


def fwd24():
    ts, sym, c = SS.read_bins(SS.CLOSES)
    m = ts < SS.DEV_END_MS
    d = pd.DataFrame({"ctime": ts[m] + H, "sym": sym[m], "close": c[m]})
    d = d.drop_duplicates(["sym", "ctime"], keep="first").sort_values(["sym", "ctime"])
    g = d.groupby("sym", sort=False)
    c24 = g["close"].shift(-24)
    t24 = g["ctime"].shift(-24)
    ok = (t24 - d["ctime"]) == 24 * H
    d["f24"] = np.where(ok, c24 / d["close"] - 1.0, np.nan)
    return d[["ctime", "sym", "f24"]]


def se_iid(v):
    v = v[np.isfinite(v)]
    return float(v.std(ddof=1) / np.sqrt(len(v)))


def summarize(name, sub, res):
    ts = sub["ctime"].to_numpy(np.int64)
    gs = -sub["f24"].to_numpy(float)          # short gross
    ex = -(sub["f24"] - sub["ew"]).to_numpy(float)  # short excess vs EW cung gio
    cg = SS.ci_mean(gs, ts)
    ce = SS.ci_mean(ex, ts)
    se_b = (ce["raw"][1] - ce["raw"][0]) / 3.92
    neff = len(ex) * (se_iid(ex) / se_b) ** 2 if se_b > 0 else float("nan")
    nblk = len(np.unique(ts // (72 * H)))
    # beta: trung binh theo gio cua tap vs EW
    hm = sub.groupby("ctime").agg(b=("f24", "mean"), u=("ew", "first"))
    X = np.vstack([np.ones(len(hm)), hm["u"].to_numpy()]).T
    coef = np.linalg.lstsq(X, hm["b"].to_numpy(), rcond=None)[0]
    res[name] = {
        "n": int(len(sub)), "n_hours": int(len(hm)), "n_blocks72h": int(nblk),
        "short_gross_pct": round(100 * float(np.nanmean(gs)), 4),
        "short_gross_ci_pct": [round(100 * x, 4) for x in cg["raw"]],
        "short_net112_pct": round(100 * (float(np.nanmean(gs)) - COST), 4),
        "short_excess_pct": round(100 * float(np.nanmean(ex)), 4),
        "short_excess_ci_pct": [round(100 * x, 4) for x in ce["raw"]],
        "excess_out_both": ce["out_both"],
        "by_year_gross_pct": {k: (round(100 * v, 4) if v is not None else None)
                              for k, v in SS.by_year(gs, ts).items()},
        "by_year_excess_pct": {k: (round(100 * v, 4) if v is not None else None)
                               for k, v in SS.by_year(ex, ts).items()},
        "beta_hourly_mean_vs_EW": round(float(coef[1]), 4),
        "alpha_24h_pct_from_ols(short)": round(-100 * float(coef[0]), 4),
        "n_eff_excess": round(float(neff), 1),
    }
    L.info("%s %s", name, json.dumps(res[name]))


def main():
    st = SS.build_states()
    L.info("states rows=%d", len(st))
    fw = fwd24()
    d = st.merge(fw, on=["ctime", "sym"], how="inner")
    d = d[(d["ctime"] >= T0) & np.isfinite(d["f24"])].copy()
    ew = d.groupby("ctime")["f24"].transform("mean")
    d["ew"] = ew
    L.info("rows DEV22-25=%d", len(d))
    res = {"note": "forward tu CLOSES_1H (gio), khong .pb; doi chieu RESULT_SHORT_STATE", "variants": {}}
    B = (d["pump_age_d"] > 7) & (d["vol_decay"] < 1.0) & (d["ret30"] < 0) & (d["dd30"] < -0.15)
    B_ev = (d["pump_age_d"] > 18) & (d["vol_decay"] < 1.0) & (d["ret30"] < 0) & (d["dd30"] < -0.20)
    A_ev = (d["pump_age_d"] <= 18) | (d["ret7"] >= 0.50)
    for nm, mk in [("ALL", np.ones(len(d), bool)), ("B_xadan", B), ("B_ev_xadan", B_ev), ("A_ev_guong", A_ev)]:
        summarize(nm, d[mk], res["variants"])
    json.dump(res, open(OUT, "w"), indent=1)
    L.info("wrote %s", OUT)


if __name__ == "__main__":
    main()
