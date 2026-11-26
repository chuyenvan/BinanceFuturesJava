"""A step 2: descriptive anatomy of the short system from out/a_trades.parquet + out/a_eq_hourly.parquet.
Outputs out/a_summary.json, out/a_monthly.parquet, out/a_coin.parquet, out/a_family_year.parquet, out/a_family_2024m.parquet,
out/a_2024_trades.parquet."""
import sys
import os
import json
import logging
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import an_common as A
import numpy as np
import pandas as pd

log = logging.getLogger('levz_an.a_an')
FEATS = ('z_oi', 'z_f', 'f', 'doi24', 'r24', 'qv30', 'age_d', 'hod', 'btc7', 'ew7')


def eq_daily(eqh):
    e = eqh.copy()
    e['d'] = A.dts(e['t']).floor('D')
    d = e.groupby('d').agg(eq=('eq', 'last'), expo=('expo', 'mean'), expo_max=('expo', 'max'),
                           idle=('n_open', lambda x: float((x == 0).mean())))
    return d


def yearly(tr, eqh):
    e = eqh.set_index(A.dts(eqh['t']))['eq']
    out = {}
    prev = 10000.0
    for y in (2022, 2023, 2024, 2025):
        s = e[e.index.year == y]
        end = float(s.iloc[-1])
        pk = np.maximum.accumulate(np.concatenate([[prev], s.values]))
        dd = float(np.max(1 - np.concatenate([[prev], s.values]) / pk))
        t = tr[tr['year_x'] == y]
        ex = eqh[A.dts(eqh['t']).year == y]
        out[y] = dict(ret=end / prev - 1, maxdd_h=dd, n_exit=int(len(t)), net=float(t['net'].sum()), win=float((t['net'] > 0).mean()) if len(t) else None,
                      mean_ret=float(t['ret'].mean()) if len(t) else None, n_sl=int((t['reason'] == 'sl').sum()),
                      idle=float((ex['n_open'] == 0).mean()), expo_mean=float(ex['expo'].mean()), fund=float(t['funding'].sum()), fees=float(t['fees'].sum()))
        prev = end
    return out


def conc(t):
    by = t.groupby('sym')['net'].sum().sort_values(ascending=False)
    tot = float(t['net'].sum())
    gp = float(t.loc[t['net'] > 0, 'net'].sum())
    nt = len(t)
    top5p = int(np.ceil(0.05 * nt))
    srt = t['net'].sort_values(ascending=False)
    return dict(n_trades=nt, n_coins=int(by.size), total=tot, top5_coins=float(by.head(5).sum()), top10_coins=float(by.head(10).sum()),
                top5_names=by.head(5).index.tolist(), bottom5_names=by.tail(5).index.tolist(), bottom5=float(by.tail(5).sum()),
                ex_top5=tot - float(by.head(5).sum()), ex_top10=tot - float(by.head(10).sum()),
                top5pct_trades_n=top5p, top5pct_trades=float(srt.head(top5p).sum()), ex_top5pct_trades=tot - float(srt.head(top5p).sum()),
                gross_profit=gp, gross_loss=float(t.loc[t['net'] <= 0, 'net'].sum()))


def reason(t):
    o = {}
    for r, s in t.groupby('reason'):
        o[r] = dict(n=int(len(s)), share=len(s) / len(t), net=float(s['net'].sum()), mean_ret=float(s['ret'].mean()),
                    win=float((s['net'] > 0).mean()), hold_h_med=float(s['hold_h'].median()))
    return o


def dist(t):
    q = (0.05, 0.25, 0.5, 0.75, 0.95)
    return dict(ret_q={str(x): float(t['ret'].quantile(x)) for x in q}, ret_mean=float(t['ret'].mean()), win=float((t['net'] > 0).mean()),
                avg_win=float(t.loc[t['ret'] > 0, 'ret'].mean()), avg_loss=float(t.loc[t['ret'] <= 0, 'ret'].mean()),
                hold_h_q={str(x): float(t['hold_h'].quantile(x)) for x in q}, mae_q={str(x): float(t['mae'].quantile(x)) for x in q},
                mae_win_med=float(t.loc[t['ret'] > 0, 'mae'].median()), fund_total=float(t['funding'].sum()),
                fund_per_notional_mean=float((t['funding'] / t['notional_in']).mean()), fees_total=float(t['fees'].sum()),
                gross_total=float(t['gross'].sum()))


def streaks(t):
    s = (t.sort_values(['kx', 'ke'])['reason'] == 'sl').astype(int).values
    best = cur = 0
    runs = []
    for v in s:
        cur = cur + 1 if v else 0
        if v == 0 and best:
            pass
        best = max(best, cur)
    # loss streaks
    l = (t.sort_values(['kx', 'ke'])['net'] <= 0).astype(int).values
    bl = cl = 0
    for v in l:
        cl = cl + 1 if v else 0
        bl = max(bl, cl)
    return dict(max_consec_sl=int(best), max_consec_loss=int(bl))


def winloss(t):
    o = {}
    for y, s in t.groupby('year'):
        w, l = s[s['net'] > 0], s[s['net'] <= 0]
        o[int(y)] = {f: dict(win_med=float(w[f].median()) if len(w) else None, loss_med=float(l[f].median()) if len(l) else None,
                             spear=float(s[[f, 'ret']].corr(method='spearman').iloc[0, 1]) if len(s) > 5 else None)
                     for f in FEATS}
        o[int(y)]['_n'] = dict(win=int(len(w)), loss=int(len(l)))
    return o


def y2024(t):
    s = t[t['year_x'] == 2024].copy()
    o = {}
    o['n'] = int(len(s))
    o['month'] = {str(k): dict(n=int(len(v)), net=float(v['net'].sum()), n_sl=int((v['reason'] == 'sl').sum()))
                  for k, v in s.groupby(A.dts(s['t_exit']).strftime('%Y-%m'))}
    by = s.groupby('sym')['net'].agg(['sum', 'count']).sort_values('sum')
    o['worst_coins'] = [(i, float(r['sum']), int(r['count'])) for i, r in by.head(10).iterrows()]
    o['best_coins'] = [(i, float(r['sum']), int(r['count'])) for i, r in by.tail(5).iterrows()]
    o['reason'] = reason(s)
    o['streaks'] = streaks(s)
    sl = s[s['reason'] == 'sl']
    o['sl_time_h_q'] = {str(x): float(sl['hold_h'].quantile(x)) for x in (0.1, 0.25, 0.5, 0.75, 0.9)} if len(sl) else None
    o['sl_within_1h'] = int((sl['hold_h'] <= 1).sum())
    o['sl_within_6h'] = int((sl['hold_h'] <= 6).sum())
    loss = s[s['net'] <= 0]
    o['loss_mae_q'] = {str(x): float(loss['mae'].quantile(x)) for x in (0.25, 0.5, 0.75, 0.9)} if len(loss) else None
    o['loss_hold_h_med'] = float(loss['hold_h'].median()) if len(loss) else None
    # market state at entry by year, winners vs losers
    mk = {}
    for y, v in t.groupby('year'):
        w, l = v[v['net'] > 0], v[v['net'] <= 0]
        mk[int(y)] = dict(btc7_all=float(v['btc7'].median()), ew7_all=float(v['ew7'].median()), btc7_win=float(w['btc7'].median()),
                          btc7_loss=float(l['btc7'].median()), ew7_win=float(w['ew7'].median()), ew7_loss=float(l['ew7'].median()),
                          n_win=int(len(w)), n_loss=int(len(l)))
    o['mkt_by_year'] = mk
    return o


def main():
    A.setup_log('a_analyze')
    tr = pd.read_parquet(A.OUT + '/a_trades.parquet')
    eq = pd.read_parquet(A.OUT + '/a_eq_hourly.parquet')
    with open(A.OUT + '/a_check.json') as fh:
        ck = json.load(fh)
    fam = ck['family']
    g = pd.read_parquet('/home/ubuntu/claude_master/w3/levz_b1/out/grid_b1_scored.parquet').set_index('cfg_id')
    tr['K'] = tr['cfg_id'].map(g['K']).astype(int)
    tr['contrib'] = tr['ret'] * 0.60 / tr['K']
    S = {}
    mon = []
    coins = []
    for cfg in A.REF:
        t = tr[tr['cfg_id'] == cfg]
        e = eq[eq['cfg_id'] == cfg]
        d = {}
        d['yearly'] = yearly(t, e)
        d['conc_all'] = conc(t)
        d['conc_by_year'] = {int(y): conc(v) for y, v in t.groupby('year_x')}
        d['reason'] = reason(t)
        d['reason_by_year'] = {int(y): reason(v) for y, v in t.groupby('year_x')}
        d['dist'] = dist(t)
        d['dist_by_year'] = {int(y): dist(v) for y, v in t.groupby('year_x')}
        d['streaks_by_year'] = {int(y): streaks(v) for y, v in t.groupby('year_x')}
        d['idle_all'] = float((e['n_open'] == 0).mean())
        d['y2024'] = y2024(t)
        d['winloss'] = winloss(t)
        S[cfg] = d
        ed = eq_daily(e)
        em = ed['eq'].groupby(ed.index.strftime('%Y-%m')).last()
        mr = em / em.shift(1).fillna(10000.0) - 1
        tm = t.groupby(A.dts(t['t_exit']).strftime('%Y-%m')).agg(n_exit=('net', 'size'), net=('net', 'sum'), n_sl=('reason', lambda x: int((x == 'sl').sum())))
        te = t.groupby(A.dts(t['t_entry']).strftime('%Y-%m')).size().rename('n_entry')
        mm = pd.DataFrame({'ret_mtm': mr}).join(tm).join(te).fillna(0)
        mm['cfg_id'] = cfg
        mon.append(mm.reset_index().rename(columns={'index': 'ym'}))
        cc = t.groupby(['year_x', 'sym']).agg(net=('net', 'sum'), n=('net', 'size')).reset_index()
        cc['cfg_id'] = cfg
        coins.append(cc)
    pd.concat(mon).to_parquet(A.OUT + '/a_monthly.parquet', index=False)
    pd.concat(coins).to_parquet(A.OUT + '/a_coin.parquet', index=False)
    # family (50)
    F = tr[tr['cfg_id'].isin(fam)]
    fy = []
    for cfg in fam:
        e = eq[eq['cfg_id'] == cfg]
        t = F[F['cfg_id'] == cfg]
        yy = yearly(t, e)
        row = dict(cfg_id=cfg, W=int(g.loc[cfg, 'W']), E=g.loc[cfg, 'E'], zmin=float(g.loc[cfg, 'zmin']), K=int(g.loc[cfg, 'K']),
                   SL=float(g.loc[cfg, 'SL']), H=int(g.loc[cfg, 'H']), arm=float(g.loc[cfg, 'arm']), gap=float(g.loc[cfg, 'gap']),
                   idle=float((e['n_open'] == 0).mean()), n=int(len(t)))
        c = conc(t)
        row.update(top5_coin_share=c['top5_coins'] / c['total'] if c['total'] else np.nan, ex_top5=c['ex_top5'],
                   ex_top5pct_trades=c['ex_top5pct_trades'], total=c['total'])
        for y in yy:
            row['ret_%d' % y] = yy[y]['ret']
            row['n_%d' % y] = yy[y]['n_exit']
            row['maxdd_%d' % y] = yy[y]['maxdd_h']
        fy.append(row)
    fy = pd.DataFrame(fy)
    fy.to_parquet(A.OUT + '/a_family_year.parquet', index=False)
    f24 = F[F['year_x'] == 2024]
    m24 = f24.groupby(['cfg_id', A.dts(f24['t_exit']).strftime('%Y-%m')])['contrib'].sum().unstack(fill_value=0.0)
    m24.to_parquet(A.OUT + '/a_family_2024m.parquet')
    c24 = f24.groupby('sym')['contrib'].sum().sort_values() / len(fam)
    S['family'] = dict(cfgs=fam, n_cfg=len(fam),
                       params={k: fy[k].value_counts().to_dict() for k in ('W', 'E', 'zmin', 'K', 'SL', 'H')},
                       trail=fy.groupby(['arm', 'gap']).size().rename('n').reset_index().to_dict('records'),
                       ret_year_median={y: float(fy['ret_%d' % y].median()) for y in (2022, 2023, 2024, 2025)},
                       ret_year_min={y: float(fy['ret_%d' % y].min()) for y in (2022, 2023, 2024, 2025)},
                       ret_year_max={y: float(fy['ret_%d' % y].max()) for y in (2022, 2023, 2024, 2025)},
                       n_year_median={y: float(fy['n_%d' % y].median()) for y in (2022, 2023, 2024, 2025)},
                       idle_median=float(fy['idle'].median()), top5_coin_share_median=float(fy['top5_coin_share'].median()),
                       frac_ex_top5_pos=float((fy['ex_top5'] > 0).mean()), frac_ex_top5pct_trades_pos=float((fy['ex_top5pct_trades'] > 0).mean()),
                       m2024_contrib_median=m24.median().to_dict(), m2024_frac_neg=(m24 < 0).mean().to_dict(),
                       coin2024_worst=[(i, float(v)) for i, v in c24.head(10).items()], coin2024_best=[(i, float(v)) for i, v in c24.tail(5).items()],
                       reason_all={r: float(v) for r, v in F.groupby('reason').size().div(len(F)).items()},
                       n_unique_entries=int(F[['sym', 'ke']].drop_duplicates().shape[0]))
    # REF 3550 vs family overlap in 2024
    with open(A.OUT + '/a_summary.json', 'w') as fh:
        json.dump(S, fh, indent=1, default=lambda x: x.item() if hasattr(x, 'item') else str(x))
    log.info('a_analyze done')


if __name__ == '__main__':
    main()
