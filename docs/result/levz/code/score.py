"""Tables + C1..C8 + VERDICT (prereg sec 6). usage: python3 score.py <explore|all>  -> out/tables_<mode>.md, out/score.json (all)"""
import json
import logging
import os
import sys
import levz as L

L.C.setup_log()
log = logging.getLogger('score')


def f(v, k=4, pct=True):
    if v is None or (isinstance(v, float) and v != v):
        return 'NA'
    return ('%.' + str(k) + 'f%%') % (100 * v) if pct else ('%.' + str(k) + 'f') % v


def load(p):
    fn = '%s/summary_%s.json' % (L.OUT, p)
    return json.load(open(fn)) if os.path.exists(fn) else None


def table(s, keys, lines, title):
    lines.append('### %s - %s' % (title, s['period']))
    lines.append('| nhanh | n | mean net_ex24 | median | CI95 | p1 | p_holm | MDE80 | net tho24 | net_ex4 | net_ex72 | net4 | net72 | net_ex24 stress | net24 stress | drop top5 | MAE>=10% | MAE>=20% | fund24 | E1 xac nhan / lag |')
    lines.append('|' + '---|' * 20)
    for k in keys:
        b = s['branches'].get(k) or s['desc'].get(k)
        if not b or not b.get('n'):
            lines.append('| %s | 0 |' % k)
            continue
        lines.append('| %s | %d | %s | %s | [%s ; %s] | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |' % (
            k, b['n'], f(b['mean_net_ex_24']), f(b['median_net_ex_24']), f(b['ci_lo']), f(b['ci_hi']), f(b['p'], 4, False),
            f(b.get('p_holm'), 4, False), f(b['mde80']), f(b['mean_net_24']), f(b['mean_net_ex_4']), f(b['mean_net_ex_72']),
            f(b['mean_net_4']), f(b['mean_net_72']), f(b['mean_net_ex_stress_24']), f(b['mean_net_stress_24']),
            f(b['mean_net_ex_24_drop_top5']), f(b.get('mae10_24'), 1), f(b.get('mae20_24'), 1), f(b['mean_fund_24']),
            '%s/%s, %sh' % (b.get('e1_confirmed', '-'), b.get('n_t0_episodes'), b.get('e1_lag_median_h', '-'))))
    lines.append('')
    lines.append('Theo nam (t0) mean net_ex24 (n):')
    for k in keys:
        b = s['branches'].get(k) or s['desc'].get(k)
        if b and b.get('by_year'):
            lines.append('- %s: ' % k + ', '.join('%s %s (%d)' % (y, f(v['mean_net_ex_24']), v['n']) for y, v in sorted(b['by_year'].items())))
    lines.append('')


def main(mode):
    ex = load('explore')
    co = load('confirm') if mode == 'all' else None
    lines = []
    for s in [x for x in (ex, co) if x]:
        table(s, L.MAIN, lines, 'GIA THUYET A1-A4')
        table(s, sorted(s['desc']), lines, 'CHI MO TA (khong dung de tuyen bo)')
        lines.append('V4 %s: ```%s```' % (s['period'], json.dumps(s['v4'], sort_keys=True)))
        lines.append('')
    sc = {}
    if co:
        for k in L.MAIN:
            e, c = ex['branches'][k], co['branches'][k]
            yrs = {}
            yrs.update(e.get('by_year', {}))
            yrs.update(c.get('by_year', {}))
            npos = sum(1 for y in ('2022', '2023', '2024', '2025') if y in yrs and yrs[y]['n'] > 0 and yrs[y]['mean_net_ex_24'] > 0)
            mae = c.get('mae10_24')
            r = {
                'C1': bool(c.get('n') and c['mean_net_ex_24'] > 0 and c['p_holm'] < 0.05),
                'C2': bool(e.get('n') and e['mean_net_ex_24'] > 0),
                'C3': bool(e.get('n', 0) >= 150 and c.get('n', 0) >= 150),
                'C4': npos >= 3,
                'C5': bool(c.get('n') and c['mean_net_ex_24_drop_top5'] > 0),
                'C6': bool(c.get('n') and c['mean_net_24'] > 0),
                'C7': ('TRUOT' if (mae is not None and mae > 0.30) else 'CHUA_KET_LUAN_proxy_close') if c.get('n') else False,
                'C8': bool(c.get('n') and c['mean_net_ex_stress_24'] > 0),
                'years_pos': npos, 'n_explore': e.get('n', 0), 'n_confirm': c.get('n', 0), 'mae10_24_close_proxy_confirm': mae}
            hard = [r[x] for x in ('C1', 'C2', 'C3', 'C4', 'C5', 'C6', 'C8')]
            r['all_except_C7'] = all(hard)
            r['branch_verdict'] = 'CO CUA (dieu kien C7 chua kiem duoc - bao MASTER)' if all(hard) and r['C7'] != 'TRUOT' else 'TRUOT'
            sc[k] = r
        sc['VERDICT'] = 'NO-GO (DONG ho LEVZ)' if all(sc[k]['branch_verdict'] == 'TRUOT' for k in L.MAIN) else 'CAN MASTER XEM (co nhanh dat moi tieu chi tru C7)'
        lines.append('### C1-C8')
        lines.append('| nhanh | C1 | C2 | C3 | C4 | C5 | C6 | C7 | C8 | ket luan |')
        lines.append('|---|---|---|---|---|---|---|---|---|---|')
        for k in L.MAIN:
            r = sc[k]
            tf = lambda v: v if isinstance(v, str) else ('DAT' if v else 'TRUOT')
            lines.append('| %s | %s |' % (k, ' | '.join(tf(r[x]) for x in ('C1', 'C2', 'C3', 'C4', 'C5', 'C6', 'C7', 'C8')) + ' | ' + r['branch_verdict']))
        lines.append('')
        lines.append('VERDICT: ' + sc['VERDICT'])
        json.dump(sc, open('%s/score.json' % L.OUT, 'w'), indent=1, sort_keys=True, default=float)
    open('%s/tables_%s.md' % (L.OUT, mode), 'w').write('\n'.join(lines) + '\n')
    log.info('score %s written', mode)


if __name__ == '__main__':
    main(sys.argv[1])
