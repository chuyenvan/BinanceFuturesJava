"""So sanh O1 vs O2 (Oracle-Oracle) va O1 vs K1 (Oracle-Kaggle) o n_jobs=1.
Doc 5 chi so cho tung cap, dung dinh nghia giong compare_parity_kaggle.py, cong them
phep do CHINH: bit-identical cua cot score (rank trong tick) sau khi sort (ts,sym)."""
import json
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

OUT = "/home/ubuntu/s1hpo"
# pred_baseline18_n1_{o1,o2}.parquet / kaggle chi co ts,sym,score,fold -- g1lite lay rieng
# tu file ledger rut gon (dung chung cho ca 3 lan chay).
G1 = pd.read_parquet(f"{OUT}/kaggle_ds/cand_dev_x1_lite.parquet", columns=["ts", "sym", "g1lite"])

o1 = pd.read_parquet(f"{OUT}/pred_baseline18_n1_o1.parquet", columns=["ts", "sym", "score"])
o2 = pd.read_parquet(f"{OUT}/pred_baseline18_n1_o2.parquet", columns=["ts", "sym", "score"])
k1 = pd.read_parquet(f"{OUT}/kaggle_kernel_det/out/pred_baseline18_n1_kaggle.parquet",
                      columns=["ts", "sym", "score"])
o1 = o1.merge(G1, on=["ts", "sym"], how="left")
# g1lite CHI gan vao o1 (khong gan o2/k1) de tranh trung ten cot khi merge trong compare_pair --
# nhan g1lite giong het nhau qua ca 3 lan chay (cung ledger), nen dung mot ban la du.

print("o1 shape", o1.shape, "o2 shape", o2.shape, "k1 shape", k1.shape)


def compare_pair(a, b, name_a, name_b):
    m = a.merge(b, on=["ts", "sym"], suffixes=("_a", "_b"), how="inner")
    n_a, n_b, n_join = len(a), len(b), len(m)

    m_sorted = m.sort_values(["ts", "sym"]).reset_index(drop=True)
    sc_a = m_sorted["score_a"].to_numpy()
    sc_b = m_sorted["score_b"].to_numpy()
    bit_identical = bool(np.array_equal(sc_a, sc_b))
    max_abs_delta = float(np.max(np.abs(sc_a - sc_b))) if len(sc_a) else float("nan")

    sp_global = float(spearmanr(m.score_a, m.score_b).correlation)

    m["rk_a"] = m.groupby("ts").score_a.rank(method="first")
    m["rk_b"] = m.groupby("ts").score_b.rank(method="first")

    def _sp1(g):
        if len(g) < 3:
            return np.nan
        return spearmanr(g.score_a, g.score_b).correlation

    intick = m.groupby("ts")[["score_a", "score_b"]].apply(_sp1).dropna()
    intick_median = float(intick.median())
    intick_min = float(intick.min())
    rank_exact_match_frac = float((m.rk_a == m.rk_b).mean())

    result = dict(
        pair=f"{name_a}_vs_{name_b}",
        n_a=n_a, n_b=n_b, n_join=n_join,
        bit_identical_score=bit_identical,
        max_abs_delta_score=max_abs_delta,
        spearman_global=sp_global,
        intick_spearman_median=intick_median,
        intick_spearman_min=intick_min,
        n_ticks_intick=int(len(intick)),
        rank_exact_match_frac=rank_exact_match_frac,
    )

    if "g1lite" in m.columns:
        def edge5(df, score_col):
            rk = df.groupby("ts")[score_col].rank(method="first")
            top5 = df[rk <= 5]
            e = top5.groupby("ts").g1lite.mean() - df.groupby("ts").g1lite.mean()
            return e

        e_a = edge5(m, "score_a")
        e_b = edge5(m, "score_b")
        edge5_a_pct = float(100 * e_a.mean())
        edge5_b_pct = float(100 * e_b.mean())
        result["edge5_a_pct"] = edge5_a_pct
        result["edge5_b_pct"] = edge5_b_pct
        result["edge5_diff_pp"] = edge5_b_pct - edge5_a_pct

    return result


o1o2 = compare_pair(o1, o2, "O1", "O2")
# k1 khong co g1lite (chi ts,sym,score) -- merge se tu dong giu g1lite tu o1 (khong trung ten)
o1k1 = compare_pair(o1, k1, "O1", "K1")

result = dict(O1_vs_O2=o1o2, O1_vs_K1=o1k1)
print(json.dumps(result, indent=2))
with open(f"{OUT}/determinism.json", "w") as f:
    json.dump(result, f, indent=2)
print("WROTE", f"{OUT}/determinism.json")
