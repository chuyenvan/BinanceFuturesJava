"""LEVZ B4 report (PREREG_X3_1127 A6). Per DCA kind: share of cfgs with profit F1 / F2 / F3 / DEV [in-sample], WFO top-1 + top-20
median 2024 / 2025 vs NONE (main control, same procedure), concentration, worst slot loss, criteria V-a..V-e and the verdict;
reference rows B1 / T1 (audited numbers quoted). criteria(): pure function (used by test h).
usage: python3 code/report_b4.py --real I_HAVE_A1_PASS -> out/report_b4.{json,md}  |  --fake KIND --seed S -> out/fake/report_*"""
import json
import os
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common_b4 as C
sys.path.pop(0)
import numpy as np

log = C.setup_log('report')
REF = ['B1 (moc, da audit): WFO top-20 trung vi 2024 -23,0 %, 2025 +6,1 %; ti le co lai F1 / F2 / F3 64 % / 20 % / 84 %',
       'T1 (moc, da audit): khong ho nao DAT; PART / STATE 2024 ~ hoa, phu thuoc vai lenh']
V_OK, V_PART, V_NO = 'DCA DAT', 'CO CAI THIEN', 'KHONG HON KHONG-DCA'
YS = ('2024', '2025')


def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return float('nan')


def t20(sel):
    w = sel['wfo']
    return {Y: _f(w[Y]['top20_valid'].get('median_ret')) if w[Y]['scored'] else float('nan') for Y in YS}


def criteria(sel_d, sel_none):
    """A6 for one DCA kind. Kind cannot score year Y => V-a (and V-b) False for Y. NONE cannot score Y => V-b baseline 0 for Y
    (PREREG_X3_1127_ERRATA1 E1)."""
    a, a0 = t20(sel_d), t20(sel_none)
    d = sel_d['describe']
    conc = sel_d.get('conc', {})
    V = {}
    V['V-a'] = all(np.isfinite(a[Y]) and a[Y] > 0 for Y in YS)
    # ERRATA1 E1: NONE cannot score year Y (rule empty) => V-b baseline for Y = 0 (no trades); NONE scored => top-20 vs top-20
    base = {Y: a0[Y] if np.isfinite(a0[Y]) else 0.0 for Y in YS}
    V['V-b'] = all(np.isfinite(a[Y]) and a[Y] > base[Y] for Y in YS)
    V['V-c'] = all(d[f]['frac_pos'] >= 0.5 for f in ('F1', 'F2', 'F3'))
    V['V-d'] = all(Y in conc and conc[Y]['net_without_best5'] > 0 for Y in YS)
    V['V-e'] = all(Y in conc and conc[Y]['worst_slot'] is not None and -conc[Y]['worst_slot'] <= 1.5 * conc[Y]['s'] for Y in YS)
    if all(V.values()):
        v = V_OK
    elif V['V-a'] and V['V-b']:
        v = V_PART
    else:
        v = V_NO
    notes = ['kieu DCA khong cham duoc nam %s => V-a False' % Y for Y in YS if not np.isfinite(a[Y])]
    for Y in YS:
        if not np.isfinite(a0[Y]):
            notes.append('KHONG DCA khong cham duoc nam %s => moc V-b nam %s = 0 (ERRATA1 E1); mo ta (khong dung trong tieu chi): '
                         'trung vi loi suat nam %s cua toan bo %d cau hinh KHONG DCA = %s'
                         % (Y, Y, Y, int(sel_none.get('n_cfg', C.N_PER_DCA)), sel_none['wfo'][Y].get('kind_median_test')))
    return dict(V=V, verdict=v, top20=a, top20_NONE=a0, vb_base=base, notes=notes)


def build(sel):
    rows = {}
    for dn in C.DNAMES:
        s = sel[dn]
        o = dict(describe=s['describe'], wfo={Y: dict(top1=s['wfo'][Y]['top1'].get('median_ret'),
                 top20_median=s['wfo'][Y]['top20_valid'].get('median_ret'), kind_median=s['wfo'][Y]['kind_median_test'],
                 n_valid=s['wfo'][Y]['n_valid'], scored=s['wfo'][Y]['scored']) for Y in YS}, conc=s.get('conc', {}))
        if dn != 'NONE':
            o.update(criteria(s, sel['NONE']))
        rows[dn] = o
    return rows


def to_md(rows, tag=''):
    L = ['# REPORT_B4 %s(CHUA AUDIT) - DCA cho lenh short LEVZ' % tag, '',
         '| kieu | co lai F1/F2/F3 | DEV tv [in-sample] | WFO24 top1 / top20 tv | WFO25 top1 / top20 tv | lo te nhat cho 24/25 | V-a..V-e | ket luan |',
         '|---|---|---|---|---|---|---|---|']
    for dn, o in rows.items():
        d, w, c = o['describe'], o['wfo'], o['conc']
        u = ''.join('x' if o['V'][k] else '.' for k in ('V-a', 'V-b', 'V-c', 'V-d', 'V-e')) if dn != 'NONE' else '-'
        ws = '/'.join(str(c[Y]['worst_slot']) if Y in c else '-' for Y in YS)
        L.append('| %s | %.2f/%.2f/%.2f | %.4f [in-sample] | %s / %s | %s / %s | %s | %s | %s |' % (
            dn, d['F1']['frac_pos'], d['F2']['frac_pos'], d['F3']['frac_pos'], d['DEV']['median_ret'], w['2024']['top1'],
            w['2024']['top20_median'], w['2025']['top1'], w['2025']['top20_median'], ws, u, o.get('verdict', 'doi chung chinh')))
    for dn, o in rows.items():
        for n in o.get('notes', []):
            L.append('- %s: %s' % (dn, n))
    L += [''] + ['- ' + r for r in REF]
    return '\n'.join(L) + '\n'


def main(argv):
    if '--fake' in argv:
        kind, seed = argv[argv.index('--fake') + 1], int(argv[argv.index('--seed') + 1])
        src, dst, tag = C.OUT + '/fake/select_%s_%d.json' % (kind, seed), C.OUT + '/fake/report_%s_%d' % (kind, seed), '[FAKE %s %d] ' % (kind, seed)
    else:
        C.require_real(argv)
        src, dst, tag = C.OUT + '/select_b4.json', C.OUT + '/report_b4', ''
    with open(src) as fh:
        sel = json.load(fh)
    rows = build(sel)
    with open(dst + '.json', 'w') as fh:
        json.dump(rows, fh, indent=1, default=float)
    with open(dst + '.md', 'w') as fh:
        fh.write(to_md(rows, tag))
    log.info('report_b4 written %s (CHUA AUDIT)', dst)


if __name__ == '__main__':
    main(sys.argv[1:])
