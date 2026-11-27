"""LEVZ T2 report (PREREG_LEVZ_T2 sec 4-5). Per entry type: fill rate per signal year, median delay, share of configs with profit in
F1 / F2 / F3 / DEV [in-sample], WFO top-1 + top-20 median 2024 / 2025 vs the entry median, placebo p (time; perm descriptive),
concentration, criteria U-a..U-f and the verdict; reference rows B1 / T1 (audited numbers quoted from the prereg).
criteria(): pure function used by the report and by test g.
usage: python3 code/report_t2.py --real I_HAVE_A1_PASS   (needs out/select_t2.json, out/placebo_t2.json) -> out/report_t2.{json,md}"""
import json
import os
import sys
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common_t2 as C
sys.path.pop(0)
import numpy as np

log = C.setup_log('report')
REF = ['B1 (moc, da audit): WFO top-20 trung vi 2024 -23,0 %, 2025 +6,1 %; ti le co lai F1 / F2 / F3 64 % / 20 % / 84 %',
       'T1 (moc, da audit): khong ho nao DAT; PART / STATE 2024 ~ hoa, phu thuoc vai lenh']
V_OK, V_PART, V_NO = 'KIEU VAO DAT', 'CO CAI THIEN, CHUA DU', 'KHONG HON E0'


def _f(x):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return float('nan')
    return x


def criteria(sel_e, sel_e0, p, complete):
    """sel_e / sel_e0: select_t2.measures()[e] (with 'conc'); p: placebo time p-value; complete: placebo time has ALL its reps
    (100). Returns dict U-a..U-f (bool) + notes + verdict (A1 N1 / N2)."""
    w, w0 = sel_e['wfo'], sel_e0['wfo']
    t20 = {Y: _f(w[Y]['top20_valid'].get('median_ret')) if w[Y]['scored'] else float('nan') for Y in ('2024', '2025')}
    t20e0 = {Y: _f(w0[Y]['top20_valid'].get('median_ret')) if w0[Y]['scored'] else float('nan') for Y in ('2024', '2025')}
    d = sel_e['describe']
    U = {}
    U['U-a'] = all(np.isfinite(t20[Y]) and t20[Y] > 0 for Y in t20)
    U['U-b'] = all(d[f]['frac_pos'] >= 0.5 for f in ('F1', 'F2', 'F3'))
    notes = []
    U['U-c'] = bool(complete and np.isfinite(_f(p)) and _f(p) <= 0.05)          # A1 N1
    if not complete:
        notes.append('placebo chua du luot => U-c = False')
    U['U-d'] = d['median_n_2024_2025'] >= 100
    conc = sel_e.get('conc', {})
    U['U-e'] = all(Y in conc and conc[Y]['net_without_best5'] > 0 for Y in ('2024', '2025'))
    # U-f (A1 N2, CHOICES 15): a year E0 could not score is NOT evaluable => U-f False (conservative)
    U['U-f'] = all(np.isfinite(t20[Y]) and np.isfinite(t20e0[Y]) and t20[Y] > t20e0[Y] for Y in t20)
    for Y in t20:
        if not np.isfinite(t20e0[Y]):
            notes.append('E0 khong cham duoc %s => U-f khong danh gia duoc (False)' % Y)
    if all(U.values()):
        v = V_OK
    elif U['U-a'] and U['U-c'] and U['U-f']:
        v = V_PART
    else:
        v = V_NO
    return dict(U=U, verdict=v, top20=t20, top20_E0=t20e0, notes=notes)


def fill_stats(en):
    yr = C.year_of_k(en['k'])
    out = {}
    for e in C.ENTRIES:
        m = en[e + '_m'] >= 0
        d = (en[e + '_m'][m] - 60 * en['k'][m]) / 60.0
        r = en[e + '_px'][m] / en['p0'][m]
        out[e] = dict(by_year={int(y): float(m[yr == y].mean()) for y in np.unique(yr)}, fill=float(m.mean()),
                      delay_h_median=float(np.median(d)) if m.any() else None,
                      px_over_p0_q=[float(x) for x in np.quantile(r, [0, 0.01, 0.5, 0.99, 1])] if m.any() else None)
    return out


def build(sel, plc, en):
    rows = {}
    for e in C.ENTRIES:
        s = sel[e]
        o = dict(fill=fill_stats(en)[e], describe=s['describe'], wfo={Y: dict(top1=s['wfo'][Y]['top1'].get('median_ret'),
                 top20_median=s['wfo'][Y]['top20_valid'].get('median_ret'), entry_median=s['wfo'][Y]['entry_median_test'],
                 n_valid=s['wfo'][Y]['n_valid'], scored=s['wfo'][Y]['scored']) for Y in ('2024', '2025')},
                 conc=s.get('conc', {}), stat=s['stat'])
        if e != 'E0':
            pt = plc.get('time|' + e, {})
            o['p_time'] = pt.get('p', float('nan'))
            o['p_time_complete'] = pt.get('complete', False)
            o['p_perm'] = plc.get('perm|' + e, {}).get('p', float('nan'))
            o.update(criteria(s, sel['E0'], o['p_time'], bool(o['p_time_complete'])))
        rows[e] = o
    return rows


def to_md(rows):
    L = ['# REPORT_T2 (CHUA AUDIT) - doi diem vao lenh short LEVZ', '']
    L += ['| kieu | khop | tre tv (h) | co lai F1/F2/F3 | DEV [in-sample] | WFO24 top1 / top20 tv | WFO25 top1 / top20 tv | p time | p perm | U-a..U-f | ket luan |',
          '|---|---|---|---|---|---|---|---|---|---|---|']
    for e, o in rows.items():
        d = o['describe']
        w = o['wfo']
        u = ''.join('x' if o.get('U', {}).get(k) else '.' for k in ('U-a', 'U-b', 'U-c', 'U-d', 'U-e', 'U-f')) if e != 'E0' else '-'
        L.append('| %s | %.3f | %s | %.2f/%.2f/%.2f | %.4f [in-sample] | %s / %s | %s / %s | %s | %s | %s | %s |' % (
            e, o['fill']['fill'], o['fill']['delay_h_median'], d['F1']['frac_pos'], d['F2']['frac_pos'], d['F3']['frac_pos'],
            d['DEV']['median_ret'], w['2024']['top1'], w['2024']['top20_median'], w['2025']['top1'], w['2025']['top20_median'],
            o.get('p_time', '-'), o.get('p_perm', '-'), u, o.get('verdict', 'moc doi chieu')))
    for e, o in rows.items():
        for n in o.get('notes', []):
            L.append('- %s: %s' % (e, n))
    L += [''] + ['- ' + r for r in REF]
    return '\n'.join(L) + '\n'


def main(argv):
    C.require_real(argv)
    with open(C.OUT + '/select_t2.json') as fh:
        sel = json.load(fh)
    with open(C.OUT + '/placebo_t2.json') as fh:
        plc = json.load(fh)['res']
    en = C.load('entry_t2').load_entries()
    rows = build(sel, plc, en)
    with open(C.OUT + '/report_t2.json', 'w') as fh:
        json.dump(rows, fh, indent=1, default=float)
    with open(C.OUT + '/report_t2.md', 'w') as fh:
        fh.write(to_md(rows))
    log.info('report_t2 written (CHUA AUDIT)')


if __name__ == '__main__':
    main(sys.argv[1:])
