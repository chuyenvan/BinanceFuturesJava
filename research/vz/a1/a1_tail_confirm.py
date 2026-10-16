"""A1-TAIL xac nhan (PREREG_VZ_A1_TAIL_CONFIRM). Usage: a1_tail_confirm.py <feat.csv> <run> <years csv> <out.json>"""
import json
import logging
import os
import sys

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
log = logging.getLogger("tailc")
FEAT, RUN, YEARS, OUT = sys.argv[1], sys.argv[2], [int(y) for y in sys.argv[3].split(",")], sys.argv[4]
THR = 0.004
d = pd.read_csv(os.path.expanduser(f"~/kaggle_sim/out/{RUN}/storage/printDone.csv"), index_col=False)
d = d[d.level != "DCA_LEVEL1"].copy()
d["t0"] = (pd.to_datetime(d["start"], format="%Y%m%d %H:%M") - pd.Timedelta(hours=7)).astype("int64") // 10**6
d["n"] = d.groupby("t0").sym.transform("size")
d["year"] = pd.to_datetime(d.t0, unit="ms").dt.year
d = d[(d.n >= 6) & d.year.isin(YEARS)].copy()
F = pd.read_csv(FEAT)
m = d.merge(F, on=["sym", "t0"], how="left")
lags = {k: float(F[k].median()) for k in ["lag-2", "lag-1", "lag0", "lag1", "lag2"]}
chk = {"V1": bool((m.max_ts_used.dropna() <= m.t0[m.max_ts_used.notna()]).all()),
       "V2": float(m.v2.mean()), "V3_lags": lags,
       "V3_ok": bool(lags["lag0"] == max(lags.values()) and lags["lag0"] > 0.3),
       "V4": float((m.F1.notna() & m.F2.notna()).mean())}
chk["pass"] = chk["V1"] and chk["V2"] >= 0.95 and chk["V3_ok"] and chk["V4"] >= 0.90
log.info("[%s %s] chan %d dot %d | kiem %s", RUN, YEARS, len(m), m.t0.nunique(), chk)
res = {"run": RUN, "years": YEARS, "check": chk}
if not chk["pass"]:
    log.error("KIEM FAIL -> dung"); json.dump(res, open(OUT, "w"), indent=1); sys.exit(2)
B = m.groupby("t0").agg(pnl=("pnl", "sum"), margin=("margin", "sum"), F1=("F1", "median"),
                        year=("year", "first"), n=("sym", "size")).reset_index()
B["ret"] = B.pnl / B.margin
B["flag"] = B.F1 > THR
fl, un = B[B.flag], B[~B.flag]
res.update({"n_bursts": int(len(B)), "n_flag": int(len(fl)), "frac_flag": float(B.flag.mean()),
            "pnl_flag": float(fl.pnl.sum()), "pnl_all": float(B.pnl.sum()),
            "ret_flag_mean": float(fl.ret.mean()) if len(fl) else None, "ret_unflag_mean": float(un.ret.mean()),
            "by_year": {int(y): {"n": int(len(g)), "n_flag": int(g.flag.sum()), "pnl_flag": float(g[g.flag].pnl.sum())}
                        for y, g in B.groupby("year")},
            "flagged": fl.assign(t=pd.to_datetime(fl.t0, unit="ms").astype(str))[["t", "n", "ret", "pnl", "F1"]].round(5).to_dict("records")})
if len(fl) < 2:
    v = "KHONG_KET_LUAN"
elif fl.pnl.sum() < 0 and fl.ret.mean() < un.ret.mean() - 0.05 and B.flag.mean() <= 0.10:
    v = "XAC_NHAN"
else:
    v = "BAC_BO"
res["verdict"] = v
log.info("dot %d, co %d (%.1f%%), PnL co %+.0f / tong %+.0f, ret TB co %s vs khong %+.3f -> %s",
         len(B), len(fl), 100 * B.flag.mean(), fl.pnl.sum(), B.pnl.sum(),
         "%+.3f" % fl.ret.mean() if len(fl) else "-", un.ret.mean(), v)
log.info("theo nam %s", res["by_year"])
log.info("dot co:\n%s", pd.DataFrame(res["flagged"]).to_string(index=False) if len(fl) else "(khong)")
log.info("F1 dot q90 %.4f q95 %.4f q99 %.4f max %.4f", *B.F1.quantile([.9, .95, .99, 1.0]))
json.dump(res, open(OUT, "w"), indent=1, default=float)
