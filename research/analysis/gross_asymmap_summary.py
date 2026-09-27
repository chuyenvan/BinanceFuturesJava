"""gross_asymmap_summary.py — build docs/result/gross_asymmap_summary.json (small)."""
import json
import numpy as np
import pandas as pd

DEV = '/home/ubuntu/src/BinanceFuturesJava/'
poolK = {8: (24.409, 42, 48.82, 84.00), 12: (33.692, 53, 67.38, 106.00)}


def main():
    df = pd.read_json(DEV + 'docs/result/gross_asymmap.json')
    df = df[df.asym.notna()].copy()
    df['profitable'] = df.sum_pnl > 0
    df['pass_a'] = (df.top1_share <= 15) & df.profitable
    df['pass_b'] = df.TF50 > 0
    out = {
        'n_runs_scanned': int(len(pd.read_json(DEV + 'docs/result/gross_asymmap.json'))),
        'n_scored': int(len(df)),
        'roots': df.groupby('root').size().to_dict(),
        'pass_a_meaningful': int(df.pass_a.sum()),
        'pass_b': int(df.pass_b.sum()),
        'pass_both': int((df.pass_a & df.pass_b).sum()),
        'asym_min_all': float(df.asym.min()),
        'asym_min_all_tag': df.loc[df.asym.idxmin(), 'tag'],
        'asym_min_profitable': float(df[df.profitable].asym.min()),
        'asym_min_profitable_tag': df[df.profitable].sort_values('asym').iloc[0]['tag'],
        'asym_lt_1': int((df.asym < 1).sum()),
        'asym_lt_1_profitable': int(((df.asym < 1) & df.profitable).sum()),
        'asym_med': float(df.asym.median()),
        'asym_med_x1_gs_t170': float(df[df.profile == 'x1_gs_t170'].asym.median()),
        'asym_min_x1_gs_t170': float(df[df.profile == 'x1_gs_t170'].asym.min()),
        'gross_new_max_over_70': int((df.gross_max > 70).sum()),
        'gross_new_max_over_70_kaggle': int((df[df.root.str.contains('kaggle')].gross_max > 70).sum()),
        'gross_new_max_max': float(df.gross_max.max()),
        'gross_corr_new_vs_oldledger_mean': float(
            df.gross_mean.corr(df.old_gross_mean)),
        'gross_med_ratio_new_over_oldledger': float(
            (df.gross_mean / df.old_gross_mean).median()),
        'partA_cd_sel15': {'G_new_mean': 1.741, 'G_new_max': 49.532,
                           'G_old_ledger_mean': 1.061, 'G_old_ledger_max': 48.00,
                           'G_old_pool_mean': 48.82, 'G_old_pool_max': 84.00,
                           'd_mean_ledger': 0.531, 'd_max_ledger': 24,
                           'd_mean_pool': 24.409, 'd_max_pool': 42,
                           'ratio_pool_mean_over_new': round(48.82 / 1.741, 1),
                           'ratio_pool_mean_over_oldledger': round(48.82 / 1.061, 1)},
        'pool_K': poolK,
        'tf50_max': float(df.TF50.max()),
        'structure': {
            'sign_le45': {'n': int((df.sign_pct <= 45).sum()),
                          'asym_min': float(df[df.sign_pct <= 45].asym.min()),
                          'asym_med': float(df[df.sign_pct <= 45].asym.median())},
            'sign_gt80': {'n': int((df.sign_pct > 80).sum()),
                          'asym_min': float(df[df.sign_pct > 80].asym.min()),
                          'asym_med': float(df[df.sign_pct > 80].asym.median())},
            'sl3_family': df[df.tag.str.startswith('sl3')][
                ['tag', 'n', 'asym', 'sign_pct', 'top1_share', 'TF50']].to_dict('records'),
            'time_stop_0': df[df.tag.isin(['xs-a1', 'xs-a2', 'xs-a3'])][
                ['tag', 'n', 'asym', 'sign_pct', 'top1_share', 'TF50', 'hold_med']].to_dict('records'),
        },
        'tried_knobs': {'SIM_PRE_ARM_SL': [-0.03, -0.07],
                        'SIM_LOSER_TIME_STOP_HOURS': [0, 96, 120],
                        'TS_GIVEBACK_RATIO': [1, 2, 5],
                        'SELECTOR_RANK_TOPK': [3, 8, 16, 32]},
    }
    with open(DEV + 'docs/result/gross_asymmap_summary.json', 'w') as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
    print(json.dumps(out, indent=1, ensure_ascii=False))


if __name__ == '__main__':
    main()
