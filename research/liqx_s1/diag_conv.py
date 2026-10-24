"""LIQX_S1 diag (before any return): calibrate implied-price fallback against taker verdict; AMBIG census."""
import glob
import numpy as np
import pandas as pd

S1 = "/home/ubuntu/claude_master/liqx_wk/s1"
c = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(S1 + "/conv/*.parquet"))], ignore_index=True)
c = c.drop_duplicates(["sym", "day"])
c["ym"] = pd.to_datetime(c.day, unit="ms").dt.strftime("%Y-%m")
c["pr"] = c.perr_new / c.perr_old  # >1 favours OLD
tk = c[(c.via == "taker")]
print("taker-decided:", tk.groupby("conv").size().to_dict())
for thr in (2, 3, 5, 10):
    for conv in ("OLD", "NEW"):
        z = tk[(tk.conv == conv) & (tk.n_p >= 144)]
        agree = (z.pr > thr) if conv == "OLD" else (z.pr < 1 / thr)
        wrong = (z.pr < 1 / thr) if conv == "OLD" else (z.pr > thr)
        print("thr", thr, conv, "n", len(z), "agree", round(agree.mean(), 4), "WRONG", int(wrong.sum()), "undecided", round(1 - agree.mean() - wrong.mean(), 4))
a = c[c.conv == "AMBIG"]
print("AMBIG", len(a), "n_t==0", int((a.n_t == 0).sum()), "n_p<144", int((a.n_p < 144).sum()))
print("AMBIG pr quantiles", a.pr.quantile([0, .01, .05, .1, .5, .9, .99, 1]).round(3).to_dict())
print(a.groupby("ym").size().to_string())
print("AMBIG n_rows<144", int((a.n_rows < 144).sum()))
