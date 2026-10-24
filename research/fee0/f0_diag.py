"""FEE0 chan doan MO TA (khong phai phep thu): phan ra gross/lenh S1, S7 theo khop/khong khop (W=15) -> chi phi chon loc cua luat xuyen muc."""
import json, os, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import f0_common as F  # noqa: E402
import f0_run as R  # noqa: E402

out = {}
for a in ("BTC", "ETH"):
    X, T, t_usdc = F.exec_frame(a)
    fts, fr = F.load_funding(a + "USDT", a + "USDC", t_usdc)
    tr = R.trades(a, T)
    for s in ("S1", "S7"):
        t = tr[tr.sig == s].reset_index(drop=True)
        c = F.costs(t, X, fts, fr, F.HS[a + "USDC"])
        for p, (t0, t1) in {"E": ("2021-01-01", "2024-01-01"), "C": ("2024-01-01", "2026-10-01")}.items():
            m = ((t.t_in >= F.ms(t0)) & (t.t_in < F.ms(t1))).to_numpy()
            f = c["fill_W15"] & m
            o = {"gross_all_bps": float(np.nanmean(c["gross"][m]) * 1e4), "gross_filled_bps": float(np.nanmean(c["gross"][f]) * 1e4),
                 "gross_unfilled_bps": float(np.nanmean(c["gross"][m & ~c["fill_W15"]]) * 1e4), "fill": float(f.sum() / m.sum()),
                 "cost_M1_bps": 2 + 4 + F.HS[a + "USDC"] * 1e4, "fund_bps": float(np.nanmean(c["fund"][m]) * 1e4)}
            out[f"{s}_{a}_{p}"] = o
            print(f"{s}_{a} {p}", {k: round(v, 3) for k, v in o.items()})
json.dump(out, open(F.WK + "/diag.json", "w"), indent=1)
