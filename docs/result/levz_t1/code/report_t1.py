"""LEVZ T1 report (PREREG_LEVZ_T1 sec 4-5): measures (select_t1) + random control (rand_t1.json) + concentration re-runs of the WFO
top-1 of each year (test fold) -> criteria T-a..T-e and verdict per family (gate NONE only); G_EW14 numbers are descriptive and carry
the label 'gate hau kiem'. B1 audited anchors printed alongside. Exit reasons of re-run trades = REAL T1 reasons (tp / be / state ...).
REAL DATA LOCK: python3 code/report_t1.py --real I_HAVE_A1_PASS  -> out/report_t1.json, out/report_t1.md"""
import os
import sys
import json
import logging
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common_t1 as C
sys.path.pop(0)
import numpy as np
import pandas as pd

log = logging.getLogger('levz_t1.report')
SEL = C.load('select_t1')
G = C.load('grid_t1')
B1_ANCHOR = dict(wfo2024_top20_median=-0.230, wfo2025_top20_median=0.061, frac_pos_F1=0.64, frac_pos_F2=0.20, frac_pos_F3=0.84)
FAMS = ('BRK', 'VOL', 'PART', 'STATE', 'HEDGE')


def criteria(meas, rnd, conc):
    w = meas['wfo']
    d = meas['describe']
    ta = all(w[Y]['reachable'] and w[Y]['top20_valid'].get('median_ret', -1) > 0 for Y in ('2024', '2025'))
    tb = all(d[f]['frac_pos'] >= 0.5 for f in ('F1', 'F2', 'F3'))
    tc = rnd is not None and rnd['p'] <= 0.05
    td = d['median_n_2024_2025'] >= 100
    te = all(conc.get(Y) is not None and conc[Y]['net_without_best5'] > 0 for Y in ('2024', '2025'))
    v = 'HO DAT' if (ta and tb and tc and td and te) else ('CO CAI THIEN, CHUA DU' if ta else 'KHONG HON B1')
    return dict(T_a=ta, T_b=tb, T_c=tc, T_d=td, T_e=te, verdict=v)


def build(grid, rand_res, ctx):
    meas = SEL.measures(grid)
    rep = dict(n_cfg_total=int(len(grid)), b1_anchor=B1_ANCHOR, fam={})
    rows = grid.set_index('cfg_id')
    for key, m in meas.items():
        fam, g = key.split('|')
        conc = {}
        for Y, folds, test in SEL.WFO:
            cid = m['wfo'][Y]['chosen']
            if cid is None:
                conc[Y] = None
                continue
            cfg = rows.loc[cid].to_dict()
            cfg['cfg_id'] = cid
            conc[Y] = SEL.concentration(ctx, cfg, test)
            conc[Y]['cfg'] = {kk: (v if not isinstance(v, (np.floating, np.integer)) else v.item()) for kk, v in cfg.items()
                              if kk in ('fam', 'xi', 'zmin', 'K', 'gate', 's', 'R', 'H', 'a', 'zo', 'base', 'bxi', 'inst', 'h')}
        r = rand_res.get(key) if rand_res else None
        ent = dict(measures=m, random=r, concentration=conc, label=m['label'])
        if g == 'NONE':
            ent['criteria'] = criteria(m, r, conc)
        rep['fam'][key] = ent
    return rep


def to_md(rep):
    L = ['# report_t1 - LEVZ T1 (PREREG_LEVZ_T1 + ADD1) - CHUA AUDIT', '',
         'Tong so cau hinh: %d. Moc B1 (da audit): %s' % (rep['n_cfg_total'], json.dumps(rep['b1_anchor'])), '',
         '| ho / gate | nhan | lai% F1 | F2 | F3 | DEV | tv ret F1 | F2 | F3 | WFO24 top1 | WFO24 top20 tv | WFO25 top1 | WFO25 top20 tv'
         ' | p ngau nhien | T-a | T-b | T-c | T-d | T-e | ket luan |', '|' + '---|' * 20]

    def f(x):
        return '-' if x is None else ('%.3f' % x if isinstance(x, float) else str(x))
    for key, e in rep['fam'].items():
        m = e['measures']
        d, w = m['describe'], m['wfo']
        t1 = [w[Y]['top1'].get('median_ret') if w[Y]['top1'].get('n') else None for Y in ('2024', '2025')]
        t20 = [w[Y]['top20_valid'].get('median_ret') if w[Y]['reachable'] else ('khong cham duoc %s' % Y) for Y in ('2024', '2025')]
        cr = e.get('criteria', {})
        L.append('| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |' % (
            key.replace('|', ' / '), e['label'] or '-', f(d['F1']['frac_pos']), f(d['F2']['frac_pos']), f(d['F3']['frac_pos']), f(d['DEV']['frac_pos']),
            f(d['F1']['median_ret']), f(d['F2']['median_ret']), f(d['F3']['median_ret']), f(t1[0]), f(t20[0]), f(t1[1]), f(t20[1]),
            f(e['random']['p'] if e['random'] else None), f(cr.get('T_a')), f(cr.get('T_b')), f(cr.get('T_c')), f(cr.get('T_d')),
            f(cr.get('T_e')), cr.get('verdict', 'mo ta (gate hau kiem)')))
    L += ['', '## Tap trung / ly do thoat THAT (top-1 WFO, fold kiem)']
    for key, e in rep['fam'].items():
        for Y, c in e['concentration'].items():
            if c:
                L.append('- %s %s %s: n=%d, bo 5%% lenh loi nhat con %.1f (tong %.1f, hedge %.1f), lenh te nhat %s, lenh/nam %.1f, ly do %s' % (
                    key.replace('|', ' / '), Y, json.dumps(c['cfg']), c['n'], c['net_without_best5'], c['net_total'], c['hedge_pnl'],
                    f(c['worst_trade_ret']), c['trades_per_year'] or 0.0, json.dumps(c['reasons_real'])))
    return '\n'.join(L) + '\n'


def write(rep, prefix):
    with open(prefix + '.json', 'w') as fh:
        json.dump(rep, fh, indent=1, default=str)
    with open(prefix + '.md', 'w') as fh:
        fh.write(to_md(rep))


def main(argv):
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    if len(argv) < 2 or argv[0] != '--real':
        raise SystemExit('usage: report_t1.py --real %s' % G.LOCK)
    ctx = G.build_real(argv[1])
    grid = pd.read_parquet(C.OUT + '/grid_t1.parquet')
    assert len(grid) == C.n_total()
    with open(C.OUT + '/rand_t1.json') as fh:
        rnd = json.load(fh)['res']
    write(build(grid, rnd, ctx), C.OUT + '/report_t1')
    log.info('report_t1 written (CHUA AUDIT)')


if __name__ == '__main__':
    main(sys.argv[1:])
