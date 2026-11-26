#!/usr/bin/env python3
# run_mutants.py - dung lai 17 mutant SONG trong A1_PILOT_M_TOOL + 3 mutant ERRATA2 (S1, S1b, chan gio official; mutant chi kiem bang ham thuan, KHONG chay --official), chay TOAN BO pm_tests.py tren tung mutant.
# Goi tu run_mutants.sh <thu_muc_tam>. Mutant giet = bo test FAIL (>= 1 ca). In bang mutant -> ca test giet.
import concurrent.futures
import logging
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(os.path.dirname(HERE), 'pilot_m_daily.py')
LOG = logging.getLogger('mutants')
MUT = [
    ('M01_I4a_bo', [("        sarm = [e for e in symidx(C, 'STOP', sym) if e['g'][1] == 'ARM' and e['t'] >= t]",
                     "        it.add(DAT)\n        continue\n        sarm = []")]),
    ('M02_I4b_bo_han_61s', [("        if first_algo(C, cid, 'NEW', t - 5000, t + 61000):", "        if first_algo(C, cid, 'NEW', t - 5000, FAR):")]),
    ('M03_I4c_luon_DAT', [("            if canc:\n                it.add(DAT)\n            elif tc is not None:",
                           "            if True:\n                it.add(DAT)\n            elif tc is not None:")]),
    ('M04_I4d_bo', [("        if trig:\n            it.add(DAT)\n        elif act is not None", "        if True:\n            it.add(DAT)\n        elif act is not None")]),
    ('M05_I8_bo_SFIL_truoc_ARM', [("    for ev in W(C, 'SFIL'):\n        if ev['armed']:", "    for ev in W(C, 'SFIL'):\n        if True:")]),
    ('M06_I10_bo_ly_do_BOOK_eq_CLOS', [("        if clos and books and books[0]['g'][1] != clos[0]['g'][1]:", "        if False:")]),
    ('M07_I11b_bo_leo_thang', [("        if bb:\n            v.append('(b)", "        if False:\n            v.append('(b)")]),
    ('M08_I12d_bo_tong_SFIL', [("        if q_cl is not None and sf > q_cl:", "        if False:")]),
    ('M09_MT_bo_yeu_cau_CLOS', [("        if tsl and ctl:", "        if tsl:")]),
    ('M10_MT_bo_som_hon_due', [("            elif e['w'] and e['t'] <= due - 2000:", "            elif False:")]),
    ('M11_D1a_bo_level', [("            if not (r <= LEVELS[k - 1] + 1e-6):", "            if False:")]),
    ('M12_MS_bo_S7', [("        if b > 0.045 * cap * 1.2 or b < 5 * 0.5:", "        if False:")]),
    ('M13_ME0_bo_c', [("            if ev['holding_before']:\n                v.append('(c)", "            if False:\n                v.append('(c)")]),
    ('M14_K2_bo_khoang_trong_10p', [("        if t - prev_t > 10 * 60000 and not overl(prev_t, t):", "        if False:"),
                                    ("    if end_t - prev_t > 10 * 60000 and not overl(prev_t, end_t):", "    if False:")]),
    ('M15_K3_bo_streak', [("        if okk:\n            it.add(DAT)", "        if True:\n            it.add(DAT)")]),
    ('M16_K4_bo_chua_co_co_ngay', [("    for e in S.by_f.get('TSX_NOFLAG', []):\n        if e['w']:", "    for e in S.by_f.get('TSX_NOFLAG', []):\n        if False:")]),
    ('M17_K5_bo_log_minutes', [("    if kv.get('log_minutes') != '1440':", "    if False:")]),
    ('M18_S1_nguong_1_thay_1_2', [("            if rcap > 1.2 * (1 + 1e-6):", "            if rcap > 1 + 1e-6:")]),
    ('M19_S1b_bo', [("            elif rcap > 1 + 1e-6:", "            elif False:")]),
    ('X01_I10_bo_han_600s', [("                if not any(abs(c['t'] - b['t']) <= 600000 for c in clos):", "                if False:"),
                              ("                if not any(abs(b['t'] - c['t']) <= 600000 for b in books):", "                if False:"),
                              ("        if cl.sfil_full is not None and clos and not any(abs(c['t'] - cl.sfil_full['t']) <= 600000 for c in clos):",
                               "        if False:")]),
    ('X04_dung_sai_0_1pc_moi_ho', [("        if n in DESC_FAMS and u <= UNPARSED_MAX * tot:", "        if u <= UNPARSED_MAX * tot:")]),
    ('H1_bo', [("            if e['w'] and armed_at(cl, (e['t'], e['seq'])):", "            if False:")]),
    ('H2_latch_rong_van_xet', [("        if kv.get('latch') and kv.get('latch') != 'NONE':", "        if kv.get('latch') != 'NONE':")]),
    ('H3_mo_coi_thanh_DAT', [("            it.add(VP, ev['t'], sym, 'H3: %s mo coi", "            it.add(DAT)\n            continue\n            it.add(VP, ev['t'], sym, 'H3: %s mo coi")]),
    ('B1_khan_rong_van_xet', [("            if a not in (None, '', '0') and a == bb:", "            if a not in (None, '0') and a == bb:")]),
    ('Y01_armed_at_arms0', [("        return bool(arms) and not any(arms[-1] < r <= key for r in cl.rst_ts)",
                             "        return bool(arms) and not any(arms[0] < r <= key for r in cl.rst_ts)")]),
    ('Y03_ARM_sau_van_tinh', [("        arms = [a for a in cl.arm_ts if a <= key]\n        return bool(arms)", "        arms = list(cl.arm_ts)\n        return bool(arms)")]),
    ('Y05_H1_chi_arm_tai_due', [("            if e['w'] and armed_at(cl, (e['t'], e['seq'])):", "            if e['w'] and armed_at(cl, (due, FAR)):")]),
    ('Y20_so_theo_ms', [("        return any(arms[-1] < r <= key for r in cl.rst_ts)", "        return any(arms[-1][0] < r[0] <= due for r in cl.rst_ts)")]),
    ('Y07_MT_CLOS_900s', [("e['g'][1] == 'TIME_STOP_168H' and e['t'] <= m + 600000]", "e['g'][1] == 'TIME_STOP_168H' and e['t'] <= m + 900000]")]),
    ('Y08_MT_KCD_60s', [("        if m + 600000 > hz:", "        if m + 60000 > hz:")]),
    ('Y12_I10_900s', [("                if not any(abs(c['t'] - b['t']) <= 600000 for c in clos):", "                if not any(abs(c['t'] - b['t']) <= 900000 for c in clos):"),
                      ("                if not any(abs(b['t'] - c['t']) <= 600000 for b in books):", "                if not any(abs(b['t'] - c['t']) <= 900000 for b in books):")]),
    ('Y13_I10_KCD_60s', [("            if last + 600000 > hz:", "            if last + 60000 > hz:")]),
    ('Y14_bo_2_BOOK', [("        if len(books) > 1:", "        if False:")]),
    ('Y15_bo_2_CLOS', [("        if len(clos) > 1:", "        if False:")]),
    ('Y19_bo_SFIL_khong_CLOS', [("        if cl.sfil_full is not None and clos and not any(abs(c['t'] - cl.sfil_full['t']) <= 600000 for c in clos):", "        if False:")]),
    ('Y17_UNPARSED_5pc', [("UNPARSED_MAX = 0.001 ", "UNPARSED_MAX = 0.05  ")]),
    ('Y18_K2_bo_chan_khong_parse', [("    if unp and unp > UNPARSED_MAX * (unp + len(win)):", "    if False:")]),
    ('M20_official_bo_chan_gio', [("    return now_ms >= ms_local((d + dt.timedelta(days=1)).isoformat() + ' 07:10')", "    return True")]),
]


def one(tmp, name, reps):
    src = open(SRC).read()
    for a, b in reps:
        if src.count(a) != 1:
            return name, None, 'KHONG AP DUNG DUOC (%d lan)' % src.count(a)
        src = src.replace(a, b)
    d = os.path.join(tmp, name)
    os.makedirs(os.path.join(d, 'work'))
    mp = os.path.join(d, 'pilot_m_daily.py')
    with open(mp, 'w') as fh:
        fh.write(src)
    env = dict(os.environ, PM_TOOL=mp)
    r = subprocess.run([sys.executable, '-I', os.path.join(HERE, 'pm_tests.py'), os.path.join(d, 'work')], env=env,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    fails = re.findall(r'^ERROR FAIL (\S+)', r.stderr, re.M)
    return name, r.returncode != 0, fails


def main():
    logging.basicConfig(level=logging.INFO, format='%(message)s', stream=sys.stderr)
    tmp = sys.argv[1]
    with concurrent.futures.ThreadPoolExecutor(max_workers=int(os.environ.get('PM_PAR', '4'))) as ex:
        res = list(ex.map(lambda m: one(tmp, m[0], m[1]), MUT))
    killed = 0
    for name, k, fails in res:
        if k:
            killed += 1
        LOG.info('%s | %s | %s', name, 'GIET' if k else ('SONG' if k is False else 'LOI'),
                 ', '.join(fails) if isinstance(fails, list) else fails)
    LOG.info('MUTANT GIET %d/%d', killed, len(MUT))
    return 0 if killed == len(MUT) else 1


if __name__ == '__main__':
    sys.exit(main())
