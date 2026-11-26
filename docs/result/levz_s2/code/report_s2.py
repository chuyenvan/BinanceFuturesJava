"""LEVZ S2 step 6: report (PREREG_LEVZ_S2 sec 5, 6) per set + REF. Criteria S-a..S-e (with MASTER decision on CHOICES #5: only
SCORED test years count; S-a: 3 scored -> >= 2 of 3 top-20 medians > 0 AND their sum > 0; 2 scored -> both > 0; < 2 scored -> FAIL;
S-d / S-e evaluated on scored years, < 2 scored -> FAIL (CHOICES #11)). Selection = select_b1.rule unchanged ('gop nam train' = min over
the train folds, as B1 combined F1 + F2). Every DEV / p_max number is labelled [in-sample].
LOCKED: --real I_HAVE_A1_PASS.  usage: python3 code/report_s2.py --real I_HAVE_A1_PASS"""
import json
import math
import os
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common_s2 as CM
sys.path.pop(0)
import numpy as np
import pandas as pd
CB, P, X, SIM = CM.b1()
GR = CM.s2('grid_s2')
log = CM.setup_log('report_s2')
TY = ('2023', '2024', '2025')
FB = {n: (k0, kl) for n, k0, kl in GR.FB}


def ledger(cands, T, row, fold):
    k0, kl = FB[fold]
    xv = P.XView(T, CB.xidx(row['SL'], row['H'], row['arm'], row['gap']))
    tr, eq, m = P.run(int(row['K']), cands[row['set']], xv, k0, kl)
    return tr, m


def s_a(med):
    """S-a on SCORED years only (ERRATA): 3 scored -> >= 2 of 3 medians > 0 AND sum > 0; 2 scored -> both > 0; < 2 -> False."""
    v = [float(x) for x in med.values()]
    if len(v) == 3:
        return sum(x > 0 for x in v) >= 2 and sum(v) > 0
    if len(v) == 2:
        return all(x > 0 for x in v)
    return False


B1_REF_NOTE = ('REF khong cham du nam qua quy trinh S2 => doi chieu lay tu B1 (da audit): WFO top-20 2024 -23,0 %, 2025 +6,1 %, '
               'khong co 2023 - QUY TRINH KHAC (ERRATA2 F2)')


def criteria(s, g, sel, rnd, cands, T):
    w = sel[s]
    sc = w['scored_years']
    med = {Y: w[Y]['top20'].get('median_ret') for Y in sc}
    sa = s_a(med)
    frac = {f: float((g[f + '_ret'] > 0).mean()) for f in ('Y22', 'Y23', 'Y24', 'Y25')}
    sb = sum(v >= 0.5 for v in frac.values()) >= 3
    pw = rnd.get(s, {}).get('p_wfo')
    scc = pw is not None and not (isinstance(pw, float) and math.isnan(pw)) and pw <= 0.05
    gi = g.set_index('cfg_id')
    trs, n_ok, dd_ok, top1 = [], True, True, {}
    for Y in sc:
        f = CM.FOLD_OF_YEAR[int(Y)]
        row = gi.loc[w[Y]['chosen']].to_dict()
        row['cfg_id'] = w[Y]['chosen']
        tr, m = ledger(cands, T, row, f)
        tr['year'] = Y
        trs.append(tr)
        n_ok &= len(tr) >= 30
        dd_ok &= m['maxdd_worst'] <= 0.25
        top1[Y] = dict(cfg_id=int(row['cfg_id']), K=int(row['K']), SL=row['SL'], H=int(row['H']), arm=row['arm'], gap=row['gap'],
                       n=int(len(tr)), ret=m['ret'], maxdd_worst=m['maxdd_worst'])
    led = pd.concat(trs, ignore_index=True) if trs else pd.DataFrame(columns=['net'])
    if len(led):
        n5 = int(np.ceil(0.05 * len(led)))
        rest = float(led['net'].sort_values(ascending=False).iloc[n5:].sum())
    else:
        rest = float('nan')
    sd = len(sc) >= 2 and n_ok and rest > 0
    se = len(sc) >= 2 and dd_ok
    if sa and sb and scc and sd and se:
        verdict = 'TAP DAT'
    elif sa and scc:
        verdict = 'CO CAI THIEN, CHUA DU'
    else:
        verdict = 'KHONG HON D0'
    return dict(scored_years=sc, top20_median=med, S_a=bool(sa), frac_pos_by_year=frac, S_b=bool(sb), p_wfo=pw, S_c=bool(scc),
                top1=top1, ledger_net_without_best5pct=rest, S_d=bool(sd), S_e=bool(se), verdict=verdict,
                grid_median={Y: w[Y]['grid_median'] for Y in TY}, top1_ret={Y: w[Y]['top1'].get('median_ret') for Y in TY},
                insample=dict(label='[in-sample]', p_max=rnd.get(s, {}).get('p_max_insample'),
                              max_dev_ret_over_dd=rnd.get(s, {}).get('real_max_dev_insample'))), led


def describe(s, g, led, ref_led, cand_info):
    d = {'counts': cand_info.get('sets', {}).get(s) if cand_info else None}
    if len(led):
        syms = None
        led = led.copy()
        led['month'] = pd.to_datetime(CB.H0 + led['ke'].values * CB.H, unit='ms').strftime('%Y-%m')
        d['top1_trades'] = int(len(led))
        d['share_funding_pos'] = float((led['funding'] > 0).mean())
        d['funding_received'] = float(led.loc[led['funding'] > 0, 'funding'].sum())
        d['funding_paid'] = float(led.loc[led['funding'] < 0, 'funding'].sum())
        d['pnl_by_month'] = {k: float(v) for k, v in led.groupby('month')['net'].sum().items()}
        bc = led.groupby('c')['net'].sum().abs().sort_values(ascending=False)
        d['top5_coin_share_abs_net'] = float(bc.head(5).sum() / bc.sum()) if bc.sum() > 0 else None
        d['top5_coin_share_trades'] = float(led['c'].value_counts().head(5).sum() / len(led))
        if ref_led is not None and len(ref_led):
            a = set(zip(led['c'], led['ke']))
            b = set(zip(ref_led['c'], ref_led['ke']))
            d['overlap_trades_with_REF_top1'] = float(len(a & b) / len(a))
    pm = {}
    for f in ('Y22', 'Y23', 'Y24', 'Y25'):
        pm[f] = {p: {str(v): float(x) for v, x in g.groupby(p)[f + '_ret'].median().items()} for p in ('H', 'SL', 'arm', 'K')}
    d['param_map_median_ret'] = pm
    r = g[[f + '_ret' for f in ('Y22', 'Y23', 'Y24', 'Y25')]].rank()
    d['spearman_cfg_rank_between_years'] = {a + '_' + b: float(np.corrcoef(r[a + '_ret'], r[b + '_ret'])[0, 1])
                                            for a, b in (('Y22', 'Y23'), ('Y23', 'Y24'), ('Y24', 'Y25'), ('Y22', 'Y25'))}
    return d


def build(df, sel, rnd, cands, T, cand_info=None, sets=None):
    sets = sets or list(sel)
    res, leds = {}, {}
    for s in sets:
        g = df[df['set'] == s].reset_index(drop=True)
        res[s], leds[s] = criteria(s, g, sel, rnd, cands, T)
    ref = leds.get('REF')
    for s in sets:
        res[s]['describe'] = describe(s, df[df['set'] == s], leds[s], ref if s != 'REF' else None, cand_info)
    if 'REF' in res and len(res['REF']['scored_years']) < 3:
        res['REF']['b1_reference'] = B1_REF_NOTE
    return res


def write_md(res, path):
    L = ['# REPORT_S2 (CHUA AUDIT) - tieu chi S-a..S-e (PREREG_LEVZ_S2 sec 5) + REF', '',
         'Chon cau hinh = select_b1.rule NGUYEN VEN; "gop nam train" = min qua cac fold train (nhu B1 gop F1 + F2). Chi tinh cac nam CHAM DUOC.', '',
         '| tap | nam cham | top20 med 2023/24/25 | S-a | S-b | p_wfo | S-c | S-d | S-e | ket luan | p_max [in-sample] |',
         '|---|---|---|---|---|---|---|---|---|---|---|']
    for s, r in res.items():
        med = '/'.join(('%.3f' % r['top20_median'][Y]) if Y in r['top20_median'] else 'n/a' for Y in TY)
        L.append('| %s | %d | %s | %s | %s | %s | %s | %s | %s | %s | %s |' % (
            s, len(r['scored_years']), med, r['S_a'], r['S_b'], r['p_wfo'], r['S_c'], r['S_d'], r['S_e'], r['verdict'],
            r['insample']['p_max']))
    if 'REF' in res and len(res['REF']['scored_years']) < 3:
        L += ['', '**' + B1_REF_NOTE + '** (REF cham duoc: %s)' % (res['REF']['scored_years'] or 'khong nam nao')]
    L += ['', 'p_wfo (ERRATA2 F1): luot ngau nhien chi cong tren DUNG cac nam tap that cham duoc; thieu nam nao => KHONG >= that.',
          'Chi tiet (top-1, mo ta muc 6, ban do tham so, tuong quan thu hang): report_s2.json']
    with open(path, 'w') as fh:
        fh.write('\n'.join(L) + '\n')


def main():
    CM.require_real(sys.argv)
    df = pd.read_parquet(CM.OUT + '/grid_s2.parquet')
    with open(CM.OUT + '/select_s2.json') as fh:
        sel = json.load(fh)
    with open(CM.OUT + '/rand_s2.json') as fh:
        rnd = json.load(fh)['res']
    with open(CM.OUT + '/cand_s2.json') as fh:
        ci = json.load(fh)
    T = X.load_table(CM.WORK + '/exits_s2.npz')
    cands = GR.load_cands(CM.WORK + '/cand_s2.npz')
    res = build(df, sel, rnd, cands, T, ci, list(CM.SETS))
    with open(CM.OUT + '/report_s2.json', 'w') as fh:
        json.dump(res, fh, indent=1, default=float)
    write_md(res, CM.OUT + '/REPORT_S2.md')
    log.info('report_s2 done (CHUA AUDIT)')


if __name__ == '__main__':
    main()
