"""LIQX_S1 descriptive extras (post-result, NOT used for verdict): ON/EXH by year, MKT episodes with vs without X14 legs (A only),
convention census totals. Out: art/desc.json"""
import json
import numpy as np
import pandas as pd

S1 = "/home/ubuntu/claude_master/liqx_wk/s1"


def st(x):
    x = pd.Series(x).dropna()
    return dict(n=int(len(x)), mean=float(x.mean()) if len(x) else None, median=float(x.median()) if len(x) else None,
                hit=float((x > 0.002).mean()) if len(x) else None)


em = pd.read_csv(S1 + "/art/episodes_mkt_main.csv")
em["year"] = em.T_on_utc.str[:4]
out = {"by_year": {}}
for y, g in em.groupby("year"):
    out["by_year"][y] = dict(n=int(len(g)), ON_r1440=st(g.on_r1440), EXH_r1440=st(g.ex_r1440), diff=st(g.ex_r1440 - g.on_r1440),
                             ON_r4320=st(g.on_r4320), rank_exh_mean=float(g.rank_exh.mean()), rank_on_mean=float(g.rank_on.mean()),
                             dur_median=float(g.dur_min.median()), merged_frac=float((g.n_merged > 1).mean()))
x = pd.read_csv(S1 + "/art/x14A_legs.csv")
ea = em[em.period == "A"].copy()
has = set(x[x.ep_mkt >= 0].ep_mkt)
ea["x14"] = ea.ep.isin(has)
out["A_with_x14"] = dict(ON_r1440=st(ea[ea.x14].on_r1440), ON_r4320=st(ea[ea.x14].on_r4320), depth_median=float(ea[ea.x14].depth.median()))
out["A_without_x14"] = dict(ON_r1440=st(ea[~ea.x14].on_r1440), ON_r4320=st(ea[~ea.x14].on_r4320), depth_median=float(ea[~ea.x14].depth.median()))
E = pd.read_parquet(S1 + "/episodes.parquet")
m = E[(E.level == "MKT") & (E.variant == "main")]
out["lag_exh_min_quantiles"] = ((m.T_exh - m.T_on) / 60000).quantile([.1, .25, .5, .75, .9, 1]).to_dict()
out["lag_peak_min_quantiles"] = ((m.T_peak - m.T_on) / 60000).quantile([.5, .75, .9, 1]).to_dict()
out["exh_before_peak_frac"] = float((m.T_exh < m.T_peak).mean())
out["dur_min_quantiles"] = ((m.T_end - m.T_on) / 60000).quantile([.25, .5, .75, .9, 1]).to_dict()
c = E[(E.level == "COIN") & (E.variant == "main")]
out["coin_lag_exh_min_quantiles"] = ((c.T_exh - c.T_on) / 60000).quantile([.25, .5, .75, .9]).to_dict()
out["coin_eps_per_coin_median"] = float(c.groupby("sym").size().median())
json.dump(out, open(S1 + "/art/desc.json", "w"), indent=1, default=float)
print(json.dumps(out, indent=1, default=float))
