#!/usr/bin/env python3
"""ECMEAS (D) equity MTM PHUT 2022-01-01 -> 2025-12-31 +07 = thuoc nsel_score_b (scorer B NSEL / COVERAGE_M2):
realized ghi tai phut end + unrealized q*(close1m - entry). Gia = ticker sim (zip ~/tickexport/up_zip wfo-ticker-2021-2025,
giai nen ecm_tk). Tu kiem: nsel-nen-s* vs NSEL_RESULT_B.json (arm nen), gqsf-* vs COVERAGE_M2_BASE json.
Usage: python3 ecm_mtm_d.py out.json tag1 tag2 ...
"""
import json, logging, os, sys
from multiprocessing import Pool
import numpy as np
import pandas as pd

R_ = "/home/ubuntu/src/BinanceFuturesJava"
sys.path.insert(0, R_ + "/research/analysis")
import nsel_score_b as B  # noqa: E402

B.TICKER = "/home/ubuntu/claude_master/1013/ecm/ecm_tk"
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("ecm_mtm_d")


def ld(tag):
    d = pd.read_csv(os.path.join(B.OUT, tag, "storage/printDone.csv"), index_col=False)
    d.columns = [c.strip() for c in d.columns]
    d["sym"] = d["sym"].astype(str).str.strip()
    r = json.load(open(os.path.join(B.OUT, tag, "result.json")))
    d["ts"] = B.parse_min(d.start.astype(str).str.strip())
    d["te"] = B.parse_min(d.end.astype(str).str.strip())
    d["q"] = d.margin / d.entry
    d["sym_t"] = d.sym + "USDT"
    return dict(tag=tag, arm=tag, seed=0, df=d, res=r)


def year_dd(run, U):
    d, res = run["df"], run["res"]
    real = np.zeros(B.NM)
    ie = (d.te.to_numpy() - B.T0) // 60000
    pnl = d.pnl.to_numpy(dtype=float)
    ok = (ie >= 0) & (ie < B.NM)
    np.add.at(real, ie[ok], pnl[ok])
    eq = float(res["equity_start"]) + pnl[ie < 0].sum() + np.cumsum(real) + U
    out = {}
    for y in B.YEARS:
        a, b = B.ymin(y), min(B.ymin(y + 1), B.NM)
        e = eq[a:b]
        dd = e / np.maximum.accumulate(e) - 1.0
        out[str(y)] = dict(maxdd=100 * float(dd.min()), roi=100 * (float(e[-1]) / float(e[0]) - 1.0),
                           trough=str(pd.Timestamp(B.T0 + (a + int(dd.argmin())) * 60000 + B.TZ_MS, unit="ms"))[:16])
    return out


def main():
    out, tags = sys.argv[1], sys.argv[2:]
    runs = [ld(t) for t in tags]
    cols = {k: [] for k in ["run", "sym", "entry", "q", "s", "e"]}
    for ri, rn in enumerate(runs):
        d = rn["df"]
        cols["run"].append(np.full(len(d), ri))
        cols["sym"].append(d.sym_t.to_numpy())
        cols["entry"].append(d.entry.to_numpy(dtype=float))
        cols["q"].append(d.q.to_numpy(dtype=float))
        cols["s"].append(((d.ts - B.T0) // 60000).to_numpy())
        cols["e"].append(((d.te - B.T0) // 60000).to_numpy())
    for k in cols:
        B.G[k] = np.concatenate(cols[k])
    B.G["R"] = len(runs)
    days = [x.strftime("%Y%m%d") for x in pd.date_range("2021-12-31", "2025-12-31", freq="D")]
    U = np.zeros((len(runs), B.NM))
    miss = legmin = 0
    nofile = []
    with Pool(B.NWORK) as pool:
        for i, o in enumerate(pool.imap_unordered(B.work, days, chunksize=4)):
            g, Uo = o["g0"], o["U"]
            lo, hi = max(0, -g), min(Uo.shape[1], B.NM - g)
            if hi > lo:
                U[:, g + lo:g + hi] += Uo[:, lo:hi]
            miss += o["miss"]
            legmin += o["legmin"]
            if o["nofile"]:
                nofile.append(o["day"])
            if i % 200 == 0:
                log.info("day %d/%d", i, len(days))
    chk = dict(miss_leg_minutes=int(miss), leg_minutes=int(legmin), miss_frac=miss / max(legmin, 1),
               ticker_days_missing=sorted(nofile), ticker_dir=B.TICKER)
    log.info("check %s", chk)
    res = {"window": "2022-01-01 00:00..2025-12-31 23:59 +07", "checks": chk, "runs": {}}
    for ri, rn in enumerate(runs):
        r = B.metrics(rn, U[ri])
        r["year"] = year_dd(rn, U[ri])
        res["runs"][rn["tag"]] = r
        log.info("%s cagr22=%.2f dd22=%.2f cal=%.3f devEq=%.3f%% log med/max=%.4f/%.4f%%", rn["tag"], r["cagr22"], r["maxdd22"],
                 r["calmar22"], r["eq_dev_pct"], r["logchk_med_abs_pct"], r["logchk_max_abs_pct"])
    json.dump(res, open(out, "w"), indent=1, default=float)
    log.info("WROTE %s", out)


if __name__ == "__main__":
    main()
