#!/usr/bin/env python3
"""ECMEAS (H) equity MTM PHUT HO4 = goi thang ham cua research/analysis/ho4_score_a.py (scorer A HO4, score_A_defs):
gia close 1m Binance Vision futures/um (sha256 .CHECKSUM), duoi settle ho4p1_excl26, cua so W9/Q1/Q2/Q3 (+07).
Cache gia rieng ecm_px (xoa duoc). Tu kiem: ho4-k24-{b,s}-s* phai trung HO4_RESULT_A.json (n, sum_pnl, roi, maxdd).
Usage: python3 ecm_mtm_h.py out.json tag1 tag2 ...
"""
import json, logging, os, sys
import numpy as np

R_ = "/home/ubuntu/src/BinanceFuturesJava"
sys.path.insert(0, R_ + "/research/analysis")
import ho4_score_a as SA  # noqa: E402

SA.PX = "/home/ubuntu/claude_master/1013/ecm/ecm_px"
WINS = {"W9": ("2026-01-01 00:00", "2026-10-01 00:00"), "Q1": ("2026-01-01 00:00", "2026-04-01 00:00"),
        "Q2": ("2026-04-01 00:00", "2026-07-01 00:00"), "Q3": ("2026-07-01 00:00", "2026-10-01 00:00")}
KEEP = ["n", "sum_pnl", "n_close", "roi", "maxdd", "dd_peak", "dd_trough", "sharpe", "sortino", "cagr_ann", "eq0", "eq1",
        "pct_day_entry", "pct_time_pos", "open_at_end", "open_at_start", "roi_m", "pnl_m", "n_m"]
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", stream=sys.stdout, force=True)
log = logging.getLogger("ecm_mtm_h")


def main():
    out, tags = sys.argv[1], sys.argv[2:]
    os.makedirs(SA.PX, exist_ok=True)
    W = SA.W
    W["dry"], W["DL"] = False, "20260930"
    W["T0"] = min(SA.ms_local(v[0]) for v in WINS.values())
    W["NW"] = (max(SA.ms_local(v[1]) for v in WINS.values()) - W["T0"]) // 60000
    W["win"] = {k: (int((SA.ms_local(a) - W["T0"]) // 60000), int((SA.ms_local(b) - SA.ms_local(a)) // 60000),
                    int((SA.ms_local(b) - SA.ms_local(a)) // 86400000), SA.pd.Timestamp(a).normalize())
                for k, (a, b) in WINS.items()}
    D, UPS, RJ, drop = {}, {}, {}, 0
    for t in tags:
        D[t], dr = SA.load(t)
        drop += dr
        UPS[t] = SA.updates(t)
        RJ[t] = json.load(open(SA.OUT + t + "/result.json"))
    NE = W["NW"]
    for t in tags:
        ls = [u for u in UPS[t] if u[0][:8] == str(RJ[t].get("date_last"))]
        if ls:
            NE = max(NE, (ls[-1][1] - W["T0"]) // 60000 + 1)
    W["NE"] = int(min(NE, W["NW"] + 2 * 1440))
    U, mt = SA.build(tags, D, 8)
    res = {"wins": WINS, "price_source": "Binance Vision futures/um klines 1m close", "mtm_check": mt, "dropped": drop,
           "runs": {}}
    for i, t in enumerate(tags):
        eq = SA.equity(D[t], RJ[t]["equity_start"], U[i])
        ec = SA.eqcheck(eq, UPS[t], RJ[t])
        r = {"eqcheck": ec}
        for wk in WINS:
            m, _ = SA.metr(D[t], eq, wk)
            r[wk] = {k: m[k] for k in KEEP}
            log.info("METR %-14s %s n=%d pnl=%.0f roi=%.2f dd=%.2f", t, wk, m["n"], m["sum_pnl"], m["roi"], m["maxdd"])
        res["runs"][t] = r
    json.dump(res, open(out, "w"), indent=1, default=str)
    log.info("WROTE %s", out)


if __name__ == "__main__":
    main()
