"""gross_asymmap_report.py — tables from docs/result/gross_asymmap.json (no sim)."""
import sys
import numpy as np
import pandas as pd

RAIL_A = 15.0
END_DEV = 20251231


def main(path='docs/result/gross_asymmap.json'):
    df = pd.read_json(path)
    for c in ['d_first', 'd_last', 'd_last_end']:
        df[c + 'i'] = pd.to_numeric(df[c], errors='coerce')
    pd.set_option('display.width', 240)
    pd.set_option('display.max_columns', 40)
    print('=== N=%d | roots:' % len(df))
    print(df.groupby('root').size().to_string())
    over = df[df['d_last_endi'] > END_DEV]
    print('over 2025-12-31 (t_end): %d %s' % (len(over), over.tag.tolist()[:10]))
    print('asym NaN=%d | gross_mean NaN=%d | old_gross_mean NaN=%d | d_last NaN=%d' % (
        df.asym.isna().sum(), df.gross_mean.isna().sum(),
        df.old_gross_mean.isna().sum(), df.d_lasti.isna().sum()))
    d = df[df.asym.notna()].copy()
    print('\n=== N scored (asym ok) = %d' % len(d))
    # rails
    d['pass_a'] = d.top1_share <= RAIL_A
    d['pass_b'] = d.TF50 > 0
    d['pass_both'] = d.pass_a & d.pass_b
    print('PASS (a) top1<=15: %d | PASS (b\') TF50>0: %d | PASS CA HAI: %d' % (
        d.pass_a.sum(), d.pass_b.sum(), d.pass_both.sum()))
    print('\n=== LOWEST asym (all) ===')
    cols = ['tag', 'root', 'n', 'asym', 'wl_ratio', 'sign_pct', 'top1_share', 'TF50',
            'conc_5', 'loss_mean', 'hold_med', 'gross_max', 'pass_a', 'pass_b']
    print(d.sort_values('asym')[cols].head(25).to_string(index=False))
    print('\n=== asym<1.3 count: %d | asym<1.0: %d' % ((d.asym < 1.3).sum(), (d.asym < 1.0).sum()))
    print('\n=== asym distribution ===')
    print(d.asym.describe(percentiles=[.05, .25, .5, .75, .95]).to_string())
    # by root
    print('\n=== by root ===')
    g = d.groupby('root').agg(n=('asym', 'size'), asym_min=('asym', 'min'),
                              asym_med=('asym', 'median'), pass_a=('pass_a', 'sum'),
                              pass_b=('pass_b', 'sum'), pass_both=('pass_both', 'sum'))
    print(g.to_string())
    # pass-both list
    print('\n=== PASS BOTH (a)+(b\') ===')
    print(d[d.pass_both][cols].sort_values('asym').to_string(index=False))
    print('\n=== PASS (b\') only, sorted by top1 ===')
    print(d[d.pass_b & ~d.pass_a][cols].sort_values('top1_share').head(20).to_string(index=False))
    # structure: hold, multi-leg, ts_loss, topk, cadence, profile
    print('\n=== asym vs structure bins ===')
    d['hold_bin'] = pd.cut(d.hold_med, [0, 60, 360, 1440, 1e9],
                           labels=['<1h', '1-6h', '6-24h', '>24h'])
    print(d.groupby('hold_bin', observed=True).agg(n=('asym', 'size'), asym_min=('asym', 'min'),
                                                   asym_med=('asym', 'median')).to_string())
    d['dca_bin'] = pd.cut(d.multi_leg_frac, [-.01, .001, .05, 1],
                          labels=['no-multi-leg', 'few', 'many'])
    print(d.groupby('dca_bin', observed=True).agg(n=('asym', 'size'), asym_min=('asym', 'min'),
                                                  asym_med=('asym', 'median')).to_string())
    print('\nkaggle profiles:')
    print(d[d.root.str.contains('kaggle')].groupby('profile').agg(
        n=('asym', 'size'), asym_min=('asym', 'min'), asym_med=('asym', 'median'),
        pass_a=('pass_a', 'sum'), pass_b=('pass_b', 'sum')).to_string())
    return df, d


if __name__ == '__main__':
    main(*sys.argv[1:])
