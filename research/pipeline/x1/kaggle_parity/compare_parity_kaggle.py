"""So sanh pred_baseline18.parquet (Oracle) vs pred_baseline18_kaggle.parquet (Kaggle) --
do 4 con so "venh moi truong" theo dung dinh nghia da dung trong gate_reproduction
(research/analysis/s1_hpo_bag_featgrp.py): spearman toan cuc, rank-in-tick median/min,
rank_exact_match_frac, chenh edge5 tong (Kaggle - Oracle) theo pp."""
import json
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

OUT = "/home/ubuntu/s1hpo"
oracle = pd.read_parquet(f"{OUT}/pred_baseline18.parquet", columns=["ts", "sym", "g1lite", "score"])
kaggle = pd.read_parquet(f"{OUT}/kaggle_kernel/out/pred_baseline18_kaggle.parquet",
                          columns=["ts", "sym", "score"])

print("oracle shape", oracle.shape, "kaggle shape", kaggle.shape)

m = oracle.merge(kaggle, on=["ts", "sym"], suffixes=("_oracle", "_kaggle"), how="inner")
n_oracle, n_kaggle, n_join = len(oracle), len(kaggle), len(m)
sp_global = float(spearmanr(m.score_oracle, m.score_kaggle).correlation)

m["rk_oracle"] = m.groupby("ts").score_oracle.rank(method="first")
m["rk_kaggle"] = m.groupby("ts").score_kaggle.rank(method="first")


def _sp1(g):
    if len(g) < 3:
        return np.nan
    return spearmanr(g.score_oracle, g.score_kaggle).correlation


intick = m.groupby("ts")[["score_oracle", "score_kaggle"]].apply(_sp1).dropna()
intick_median = float(intick.median())
intick_min = float(intick.min())
rank_exact_match_frac = float((m.rk_oracle == m.rk_kaggle).mean())


def edge5(df, score_col):
    rk = df.groupby("ts")[score_col].rank(method="first")
    top5 = df[rk <= 5]
    e = top5.groupby("ts").g1lite.mean() - df.groupby("ts").g1lite.mean()
    return e


e_oracle = edge5(m, "score_oracle")
e_kaggle = edge5(m, "score_kaggle")
edge5_oracle_pct = float(100 * e_oracle.mean())
edge5_kaggle_pct = float(100 * e_kaggle.mean())
edge5_diff_pp = edge5_kaggle_pct - edge5_oracle_pct

result = dict(
    n_oracle=n_oracle, n_kaggle=n_kaggle, n_join=n_join,
    spearman_global=sp_global,
    intick_spearman_median=intick_median,
    intick_spearman_min=intick_min,
    n_ticks_intick=int(len(intick)),
    rank_exact_match_frac=rank_exact_match_frac,
    edge5_oracle_pct=edge5_oracle_pct,
    edge5_kaggle_pct=edge5_kaggle_pct,
    edge5_diff_pp=edge5_diff_pp,
)
print(json.dumps(result, indent=2))
with open(f"{OUT}/kaggle_ds/parity_result.json", "w") as f:
    json.dump(result, f, indent=2)
