"""NUP4-fix MTM kernel (Kaggle) — SINH TU ~/claude_master/nup4_fix/orch/mtm_kernel.py, KHONG sua tay.

MTM legacy phut-close (cong thuc reset_rule_score.run_mtm + gvz_mtm._work_vision, muc phi 'legacy'):
  eq(t) = CAP0 + realized(leg dong truoc ngay UTC) + cumsum(pnl leg dong trong ngay toi phut t) + sum q*(close_t - entry)
  close = kline1m Vision (vz-kline1m-YYYY), ffill/bfill TRONG ngay UTC; symbol khong co gia ca ngay => missing.
Bu leg dong 00:00 UTC (golive_quarterly): leg dong trong ngay lay tu TOAN BO leg (khong chi leg con mo trong ngay).
Leg mo-dong cung phut: dong gop u = 0 (khong tinh missing).
DD cua so (gio +07, nhu golive_quarterly): dinh reset o dau cua so. Doi chung: B0 chi-leg-DEV vs dd_q DEV_2022_25.
"""
import glob
import json
import logging
import os
import sys
import time

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout, force=True)
LOG = logging.getLogger("nup4f-mtm")
CAP0 = 35000.0
DAY0 = pd.Timestamp("2021-07-01")
H7 = pd.Timedelta(hours=7)


def load_legs(path, dev_only=False):
    d = pd.read_csv(path, on_bad_lines="skip", dtype={"start": str, "end": str})
    d.columns = [c.strip() for c in d.columns]
    for c in ("quantity", "entry", "pnl", "margin"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d = d.dropna(subset=["pnl", "margin", "quantity", "entry"]).copy()
    if dev_only:
        d = d[d["start"].astype(str) < "20260101"].copy()
    d["sym"] = d["sym"].astype(str).str.strip()
    ts = pd.to_datetime(d["start"], format="%Y%m%d %H:%M", errors="coerce")
    te = pd.to_datetime(d["end"], format="%Y%m%d %H:%M", errors="coerce")
    d = d.assign(ts=ts, te=te).dropna(subset=["ts", "te"])
    d["m0"] = ((d["ts"] - H7 - DAY0) // pd.Timedelta(minutes=1)).astype(np.int64)
    d["m1"] = ((d["te"] - H7 - DAY0) // pd.Timedelta(minutes=1)).astype(np.int64)
    return d.reset_index(drop=True)


def month_files(root):
    out = {}
    for p in glob.glob(os.path.join(root, "**", "kline1m-*.parquet"), recursive=True):
        ym = os.path.basename(p)[len("kline1m-"):-len(".parquet")]
        out.setdefault(ym, p)
    return out


def equity_series(legsets, nmin, price_month):
    """legsets {key: DataFrame}; price_month(ym, syms) -> {sym: (ts_ms int64[], close float32[])}.
    Tra {key: (eq float64[nmin], missing int)}."""
    eq = {k: np.zeros(nmin, np.float64) for k in legsets}
    miss = {k: 0 for k in legsets}
    real = {k: 0.0 for k in legsets}
    ndays = nmin // 1440
    months = sorted({(DAY0 + pd.Timedelta(days=i)).strftime("%Y-%m") for i in range(ndays)})
    for ym in months:
        d0 = int((pd.Timestamp(ym + "-01") - DAY0) // pd.Timedelta(days=1))
        d1 = int((pd.Timestamp(ym + "-01") + pd.offsets.MonthBegin(1) - DAY0) // pd.Timedelta(days=1))
        d0, d1 = max(d0, 0), min(d1, ndays)
        if d0 >= d1:
            continue
        lo, hi = d0 * 1440, d1 * 1440
        syms = sorted({s + "USDT" for d in legsets.values()
                       for s in d.loc[(d.m0 < hi) & (d.m1 > lo), "sym"].unique()})
        mc = price_month(ym, syms) if syms else {}
        for day in range(d0, d1):
            base = day * 1440
            t0 = int((DAY0 + pd.Timedelta(days=day)).value // 10 ** 6)
            for k, d in legsets.items():
                sub = d[(d.m0 < base + 1440) & (d.m1 > base)]
                u = np.zeros(1440, np.float64)
                if len(sub):
                    need = sorted({s + "USDT" for s in sub["sym"].unique()})
                    C = np.full((len(need), 1440), np.nan, np.float64)
                    for j, s in enumerate(need):
                        if s in mc:
                            ts, cl = mc[s]
                            sel = (ts >= t0) & (ts < t0 + 1440 * 60000)
                            C[j, ((ts[sel] - t0) // 60000).astype(np.int64)] = cl[sel]
                    C = pd.DataFrame(C.T).ffill().bfill().to_numpy().T
                    row = {s: j for j, s in enumerate(need)}
                    for sym, q, e, i0, i1 in zip(sub["sym"], sub["quantity"], sub["entry"],
                                                 np.maximum(sub["m0"].to_numpy() - base, 0),
                                                 np.minimum(sub["m1"].to_numpy() - base, 1440)):
                        if i1 <= i0:
                            continue
                        c = C[row[sym + "USDT"]]
                        if np.isnan(c).all():
                            miss[k] += 1
                            continue
                        u[i0:i1] += q * c[i0:i1] - q * e
                sp = np.zeros(1440, np.float64)
                cl_ = d[(d.m1 >= base) & (d.m1 < base + 1440)]          # BU: moi leg dong trong ngay
                np.add.at(sp, (cl_["m1"].to_numpy() - base).astype(np.int64), cl_["pnl"].to_numpy(np.float64))
                cs = np.cumsum(sp)
                eq[k][base:base + 1440] = CAP0 + real[k] + cs + u
                real[k] += float(cs[-1])
        LOG.info("month %s done (%d sym)", ym, len(syms))
    return {k: (eq[k], miss[k]) for k in legsets}


def dd_window(eq, a_local, b_local):
    i0 = max(int((pd.Timestamp(a_local) - H7 - DAY0) // pd.Timedelta(minutes=1)), 0)
    i1 = min(int((pd.Timestamp(b_local) - H7 - DAY0) // pd.Timedelta(minutes=1)), len(eq))
    v = eq[i0:i1]
    rp = np.maximum.accumulate(v)
    return float((v / rp - 1.0).min() * 100.0)


def main():
    CFG = json.loads(__CFG_JSON__)
    mf = month_files("/kaggle/input")
    LOG.info("kline months: %d (%s..%s)", len(mf), min(mf) if mf else None, max(mf) if mf else None)

    def price_month(ym, syms):
        if ym not in mf:
            LOG.error("THIEU file gia thang %s", ym)
            return {}
        p = pd.read_parquet(mf[ym], columns=["ts", "sym", "close"], filters=[("sym", "in", list(syms))])
        return {s: (g["ts"].to_numpy(np.int64), g["close"].to_numpy(np.float64)) for s, g in p.groupby("sym")}

    pd_paths = glob.glob("/kaggle/input/**/storage/printDone.csv", recursive=True)
    legsets, src = {}, {}
    for tag in CFG["tags"]:
        slug = CFG["slug"][tag]
        hit = [p for p in pd_paths if ("/" + slug + "/") in p]
        if len(hit) != 1:
            raise SystemExit("printDone cho %s: %d file %s" % (tag, len(hit), hit))
        legsets[tag] = load_legs(hit[0])
        src[tag] = hit[0]
        if tag in CFG["controls"]:
            legsets[tag + "__devonly"] = load_legs(hit[0], dev_only=True)
    nmin = int((pd.Timestamp(CFG["end_local"]) - H7 - DAY0) // pd.Timedelta(minutes=1))
    nmin = (nmin // 1440 + 1) * 1440
    t0 = time.time()
    res = equity_series(legsets, nmin, price_month)
    out = {"cfg": CFG, "secs": round(time.time() - t0, 1), "runs": {}, "controls": {}}
    daily = {}
    for k, (eq, miss) in res.items():
        d = legsets[k]
        r = dict(missing=int(miss), n_legs=int(len(d)), sum_pnl=float(d["pnl"].sum()),
                 eq_end=float(eq[-1]), eq_end_minus_cap_pnl=float(eq[-1] - CAP0 - d["pnl"].sum()),
                 dd_dev=dd_window(eq, *CFG["win_dev"]), dd_ho=dd_window(eq, *CFG["win_ho"]),
                 dd_all=dd_window(eq, "2021-07-01 07:00", CFG["end_local"]))
        if k.endswith("__devonly"):
            tag = k[:-len("__devonly")]
            ref = CFG["controls"][tag]
            r.update(ref=ref, diff_pp=abs(r["dd_dev"] - ref), ok=bool(abs(r["dd_dev"] - ref) <= CFG["tol_pp"]
                                                                       and miss == 0))
            out["controls"][tag] = r
        else:
            out["runs"][k] = r
            daily[k] = [round(float(x), 2) for x in eq[1440 - 1 - 7 * 60::1440]]
        LOG.info("RES %s %s", k, json.dumps(r))
    out["ok"] = bool(all(v["missing"] == 0 and abs(v["eq_end_minus_cap_pnl"]) < 0.5 for v in out["runs"].values())
                     and all(v["ok"] for v in out["controls"].values()) and len(out["controls"]) >= 1)
    json.dump(out, open("/kaggle/working/mtm_result.json", "w"), indent=1)
    json.dump(daily, open("/kaggle/working/mtm_eq_daily_close07.json", "w"))
    LOG.info("MTM DONE ok=%s", out["ok"])


if __name__ == "__main__":
    main()
