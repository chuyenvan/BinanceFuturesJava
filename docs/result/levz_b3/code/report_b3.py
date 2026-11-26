"""LEVZ B3 report (PREREG_LEVZ_B3 sec 8, 9 + ERRATA1). Reads <prefix>wfo_b3.json and <prefix>cv_b3.json, writes <prefix>report_b3.md/.json.
Every CV number is tagged "CV - co nhin truoc", every WFO 2024 number "DUOI NGUONG MAU - CHI MO TA", in-sample numbers "in-sample".
Verdict per ERRATA1 E2: all Q1..Q8 + C1 + C2 + C3 => "B3 DAT MUC YEU (1 nam WFO + CV)"; Q1 + Q3 + Q4 => "B3 CO TIN HIEU, CHUA DU";
else "B3 KHONG DAT". Original P1..P8 cannot pass (C0 2024 failed, ERRATA1 E1) - stated, not computed as criteria.
usage: python3 code/report_b3.py [out_prefix]"""
import os
import sys
import json
import logging
sys.dont_write_bytecode = True
_HERE = os.path.dirname(os.path.abspath(__file__))
import importlib.util
_spec = importlib.util.spec_from_file_location('common_b3', os.path.join(_HERE, 'common_b3.py'))
C3 = importlib.util.module_from_spec(_spec)
sys.modules.setdefault('common_b3', C3)
_spec.loader.exec_module(C3)

log = logging.getLogger('levz_b3.report')
T24 = '[DUOI NGUONG MAU - CHI MO TA]'
TCV = '[CV - co nhin truoc]'
TIS = '[in-sample]'
N_TRIALS = '9 bien the x 2 model + 3 doi chung = 21 (+ 10 model mot-seed, + CV C1..C3)'


def verdict(Q, C):
    if all(Q.values()) and all(C.values()):
        return 'B3 DAT MUC YEU (1 nam WFO + CV)'
    if Q['Q1'] and Q['Q3'] and Q['Q4']:
        return 'B3 CO TIN HIEU, CHUA DU'
    return 'B3 KHONG DAT'


def _f(x, n=4):
    return 'NaN' if x is None else ('%.*f' % (n, x) if isinstance(x, float) else str(x))


def year_block(r, tag):
    L = []
    L.append('### %s %s (exit H = %d, train n = %d, test n = %d, C0 = %s)' % (r['label'], tag, r['H_exit'], r['n_train'], r['n_test'],
                                                                              r['C0']))
    L.append('| bien the | ret | n lenh | maxDD xau nhat | n chon | nhan |')
    L.append('|---|---|---|---|---|---|')
    for name, v in r['variants'].items():
        L.append('| %s | %s | %d | %s | %d | %s |' % (name, _f(v['ret']), v['n'], _f(v['maxdd_worst']), v['n_selected'], tag))
    for name, v in r['baselines'].items():
        L.append('| %s | %s | %d | %s | %d | %s |' % (name, _f(v['ret']), v['n'], _f(v['maxdd_worst']), v['n_selected'], tag))
    L.append('- GroupKFold OOF (5 phan theo quy): %s' % ', '.join('n=%d q=%s' % (f['n_val'], f['quarters_val']) for f in r['oof_folds']))
    L.append('- RAND %d luot: p = %s, trung vi ret = %s %s' % (r['rand']['n'], _f(r['rand']['p']), _f(r['rand']['median']), tag))
    L.append('- mot-seed (T20 K5): ret = %s %s' % (', '.join(_f(v['ret']) for v in r['single_seed'].values()), tag))
    L.append('- CHINH: tong net = %s, bo %d lenh loi nhat => %s %s' % (_f(r['main_trades']['net_total'], 2), r['main_trades']['n_top5'],
                                                                     _f(r['main_trades']['net_without_top5'], 2), tag))
    d = r.get('describe')
    if d:
        for kind in ('M1', 'M2'):
            L.append('- %s IC test = %s (CI95 theo dot %s) %s; IC OOF train = %s %s; IC train = %s %s' % (
                kind, _f(d[kind]['ic']), d[kind]['ic_ci95'], tag, _f(d[kind]['ic_oof_train']), TIS, _f(d[kind]['ic_insample_train']), TIS))
        L.append('- IC cua s (doi chung) = %s %s' % (_f(d['BL_s_ic']), tag))
        for kind in ('M1', 'M2'):
            if d[kind]['deciles']:
                L.append('- 10 nhom diem %s (n / TB nhan / TB nhan co trong so): %s %s' % (kind, '; '.join(
                    '%d: %d / %s / %s' % (x['decile'], x['n'], _f(x['mean_label']), _f(x['wmean_label'])) for x in d[kind]['deciles']), tag))
            g = sorted(d[kind]['gain'].items(), key=lambda x: -x[1])[:10]
            L.append('- %s %s top10: %s' % (kind, 'gain' if kind == 'M1' else '|he so|', ', '.join('%s=%.4g' % x for x in g)))
        L.append('- 8 bien the lan can M1: %s %s' % (', '.join('%s=%s' % (n_, _f(v_['ret'])) for n_, v_ in d['neighbours_M1'].items()),
                                                      tag))
        pm = sorted(d['M1']['perm_test']['drop'].items(), key=lambda x: -x[1])[:10]
        L.append('- hoan vi tren nam kiem (giam IC) top10: %s %s' % (', '.join('%s=%.4f' % x for x in pm), tag))
        L.append('- theo thang (CHINH): %s %s' % (', '.join('%s:%.0f' % x for x in d['main_by_month'].items()), tag))
        L.append('- lenh te nhat (net): %s %s' % (', '.join(_f(x['net'], 1) for x in d['main_worst10']), tag))
        L.append('- trung coin: %s %s' % (d['main_same_coin'], tag))
    return L


def counts_block(cand_path, exit_path):
    L = ['## Ung vien, dot, C0, exit_Y (prereg muc 2, 3, 9)', '']
    if os.path.exists(cand_path):
        cj = json.load(open(cand_path))
        L.append('| nam | ung vien | dot cham nam | dot bat dau trong nam |')
        L.append('|---|---|---|---|')
        for y, v in cj['by_year'].items():
            L.append('| %s | %d | %d | %d |' % (y, v['n_cand'], v['n_dots_touching'], v['n_dots_starting']))
        L.append('- tong: %d ung vien, %d dot' % (cj['n_pool'], cj['n_dots']))
        for y, v in cj.get('C0', {}).items():
            L.append('- C0 Y=%s: H=%d, dot train=%d (can >= 600), dot nam %d=%d (can >= 300) => %s %s' % (
                y, v['H_exit'], v['n_train_dots'], int(y) - 1, v['n_lastyear_dots'], 'DAT' if v['C0'] else 'KHONG DAT', v.get('note', '')))
    if os.path.exists(exit_path):
        ej = json.load(open(exit_path))
        for y in (2024, 2025):
            e = ej['exit_%d' % y]
            L.append('- exit_%d: xi=%d SL=%s H=%d arm=%s gap=%s diem=%s (cot %s, %s, %s; hoa %d)' % (
                y, e['xi'], e['SL'], e['H'], e['arm'], e['gap'], _f(e['score']), e['columns_used'], e['agg'], e['rows'], e['n_tied_at_top']))
        L.append('- exit_2023: %s' % ej['exit_2023']['note'])
    return L + ['']


def build(prefix, cand_path=C3.OUT + '/cand_b3.json', exit_path=C3.OUT + '/exitsel_b3.json'):
    W = json.load(open(prefix + 'wfo_b3.json'))
    CV = json.load(open(prefix + 'cv_b3.json'))
    Q = W['Q']
    Cc = dict(C1=CV['C1'], C2=CV['C2'], C3=CV['C3'])
    v = verdict(Q, Cc)
    L = ['# REPORT_B3 (%s) - PREREG_LEVZ_B3 30a8c413 + ERRATA1 308cd1fc' % W['kind'], '',
         '**Ket luan theo ERRATA1 E2: %s**' % v, '',
         '- P1..P8 (2 nam) cua prereg goc: KHONG THE DAT (C0 2024 khong dat, ERRATA1 E1) - khong cham.',
         '- Y = 2023: khong lam (khong du mau, exit_2023 khong tinh duoc dung luat).',
         '- So phep thu: %s.' % N_TRIALS, ''] + counts_block(cand_path, exit_path) + [
         '## (A) WFO 2025 - CHINH THUC (khong nhin truoc)', '']
    L.append('| tieu chi | dat |')
    L.append('|---|---|')
    for kk, x in Q.items():
        L.append('| %s | %s |' % (kk, x))
    L += [''] + year_block(W['years']['2025'], '') + ['']
    L += ['## (B) CV theo quy %s' % TCV, '']
    L.append('| quy | n val | n train | IC (nhan exit_2025) |')
    L.append('|---|---|---|---|')
    for f in CV['folds_exit2025']:
        L.append('| %s | %d | %d | %s %s |' % (f['quarter'], f['n_val'], f['n_train'], _f(f['ic']), TCV))
    L.append('- C1 (IC > 0 o >= 9/12 quy): %s (%d/12) %s' % (CV['C1'], CV['C1_n_pos'], TCV))
    c2 = CV['C2_detail']
    L.append('- C2: pnl 2023/2024/2025 = %s; ret = %s vs BL_S20 %s => %s %s' % (
        ', '.join(_f(c2['pnl'][str(y)] if str(y) in c2['pnl'] else c2['pnl'].get(y), 1) for y in (2023, 2024, 2025)),
        _f(c2['ret']), _f(c2['BL_S20']['ret']), CV['C2'], TCV))
    L.append('- C3 (nhan exit_2024): ret 3 nam = %s => %s %s' % (_f(CV['C3_detail']['ret']), CV['C3'], TCV))
    L += ['', '## WFO 2024 %s' % T24, ''] + (year_block(W['years']['2024'], T24) if '2024' in W['years'] else ['(khong co)'])
    md = '\n'.join(L) + '\n'
    with open(prefix + 'report_b3.md', 'w') as fh:
        fh.write(md)
    with open(prefix + 'report_b3.json', 'w') as fh:
        json.dump(dict(verdict=v, Q=Q, C=Cc, tags=dict(cv=TCV, wfo2024=T24, insample=TIS), n_trials=N_TRIALS), fh, indent=1)
    return v, md


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    pre = sys.argv[1] if len(sys.argv) > 1 else C3.OUT + '/'
    v, _ = build(pre)
    log.info('verdict %s', v)
