#!/usr/bin/env python3
"""ADD24 ERRATA7 unit test (du lieu TONG HOP): V10a dieu kien (1)/(2) + phut chuyen trang thai; V6 expect theo phut co input; V4b quy tac
EQ_INCOME_ERR (C3MainEquity:218). Exit 0 neu moi test dat."""
import json, os, subprocess, sys, tempfile
H = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, H)
import v10_buffer as V
import rlive_gates as G
MIN = 60000
res = {}
# ---- V10a
rows = [('AAAUSDT', 10), ('BBBUSDT', 20), ('CCCUSDT', 30)]
R = [10, 20, 30]
res['eq'] = V.minute_rule([10, 20, 30], R, rows, set(), set())[0] == 'eq'
res['eq_bo_qua_S_m'] = V.minute_rule([10, 20, 30], R, rows, {'CCCUSDT'}, set())[0] == 'eq'
res['subset_dung_S_m'] = V.minute_rule([10, 20], R, rows, {'CCCUSDT'}, set())[0] == 'subset'
res['subset_2_symbol'] = V.minute_rule([10], R, rows, {'BBBUSDT', 'CCCUSDT'}, set())[0] == 'subset'
k = V.minute_rule([10, 20], R, rows, {'BBBUSDT'}, set())
res['thua_ngoai_S_m_truot'] = k[0] is None and k[1] == 'symbol_thua_khac_S_m'
res['S_m_rong_thua_truot'] = V.minute_rule([10, 20], R, rows, set(), set())[0] is None
res['S_m_thua_symbol_truot'] = V.minute_rule([10, 20], R, rows, {'CCCUSDT', 'BBBUSDT'}, set())[0] is None
k = V.minute_rule([10, 20, 40], R, rows, set(), set())
res['L_co_ban_ghi_R_khong_truot'] = k[0] is None and k[1] == 'L_khong_la_tap_con_R'
k = V.minute_rule([10, 21], R, rows, {'CCCUSDT'}, set())     # 1 ulp float32 (bit + 1)
res['lech_1_ulp_truot'] = k[0] is None and k[1] == 'L_khong_la_tap_con_R'
k = V.minute_rule([10, 20, 20], R, rows, set(), set())       # multiset: L 2 ban sao, R 1
res['multiset_dem_truot'] = k[0] is None
k = V.minute_rule([10, 20], [10, 20, 30], [('AAAUSDT', 10), ('BBBUSDT', 20)], {'CCCUSDT'}, set())
res['rig_trace_khac_appended_truot'] = k[0] is None and k[1] == 'rig_trace_khac_appended'
# chuyen trang thai: S_m = {B, C}, rig thua chi C; B chuyen trang thai => dat; B khong chuyen => truot
res['trans_cho_phep_thieu'] = V.minute_rule([10, 20], R, rows, {'BBBUSDT', 'CCCUSDT'}, {'BBBUSDT'})[0] == 'subset_trans'
res['trans_cho_phep_thua'] = V.minute_rule([10], R, rows, {'CCCUSDT'}, {'BBBUSDT'})[0] == 'subset_trans'
res['trans_khong_flex_truot'] = V.minute_rule([10, 20], R, rows, {'BBBUSDT', 'CCCUSDT'}, set())[0] is None
res['trans_flex_symbol_khac_truot'] = V.minute_rule([10, 20], R, rows, {'BBBUSDT', 'CCCUSDT'}, {'AAAUSDT'})[0] is None
# r_bits trung giua 2 symbol: chon duoc cach gan khop S_m
rd = [('AAAUSDT', 10), ('BBBUSDT', 10)]
res['bits_trung_gan_duoc'] = V.minute_rule([10], [10, 10], rd, {'BBBUSDT'}, set())[0] == 'subset'
# cua so chuyen trang thai +-1 phut
m = 100 * MIN
lev = {m + MIN: {'XUSDT'}}; rtr = {m - MIN: {'YUSDT'}}
res['flex_m_cong_1'] = 'XUSDT' in V.flex_at(m, lev, {}) and 'YUSDT' in V.flex_at(m, {}, rtr)
res['flex_m_cong_2_khong'] = not V.flex_at(m, {m + 2 * MIN: {'XUSDT'}}, {m - 2 * MIN: {'YUSDT'}})
res['flex_dung_phut'] = V.flex_at(m, {m: {'XUSDT'}}, {m: {'YUSDT'}}) == {'XUSDT', 'YUSDT'}
# ---- V6
x = G.v6_lane(6773, 0, 6774, 7049)
res['v6_dat_N1_va_phut_cuoi'] = x['ok'] and x['n_N1'] == 275 and x['n_last'] == 1 and x['expect_window'] == 7049
res['v6_dat_du_phut'] = G.v6_lane(6774, 0, 6774, 7049)['ok']
res['v6_thieu_2_truot'] = not G.v6_lane(6772, 0, 6774, 7049)['ok']
res['v6_exception_truot'] = not G.v6_lane(6773, 1, 6774, 7049)['ok']
res['v6_thua_truot'] = not G.v6_lane(6775, 0, 6774, 7049)['ok']
res['v6_none_truot'] = not G.v6_lane(None, 0, 6774, 7049)['ok']
res['v6_cu_expect_cua_so_truot'] = not G.v6_lane(6773, 0, 7049, 7049)['ok']
# ---- V4b (parser + v4b.sh tren log tong hop, ngoai pull242 => khong can P1)
os.makedirs('/dev/shm/add24', exist_ok=True)
d = tempfile.mkdtemp(dir='/dev/shm/add24', prefix='te7.')
base = ('01/01/2026 00:22:00.000 WARN  [x] c.b.c.c.r.C3MainEquity: [C3-LIVE-EQ] doc income FUNDING_FEE loi '
        'com.binance.chuyennd.c3live.api.GatewayException: x => thu lai sau 600 s\n'
        '01/01/2026 00:23:00.000 INFO  [x] c.b.c.c.r.C3MainEquity: [C3-LIVE-EQ] funding c3 +0.01 (2 dong) => cong don 0.02\n')
for name, extra in (('ok', ''), ('bad', '01/01/2026 00:24:00.000 WARN  [x] c.b.c.c.r.C3MainEquity: [C3-LIVE-EQ] doc income KHAC loi x\n')):
    open(d + '/%s.log' % name, 'w').write(base + extra)
    subprocess.run([sys.executable, '-I', H + '/live_log_parse.py', '--log-files', d + '/%s.log' % name, '--start', '2026-01-01 00:00',
                    '--end', '2026-01-01 02:00', '--out', d + '/p_' + name, '--mode', 'full'], capture_output=True)
    subprocess.run(['bash', H + '/v4b.sh', d + '/p_%s/counts.json' % name, '2026-01-01 00:00', '2026-01-01 02:00', d + '/v4b_%s.json' % name,
                    d + '/%s.log' % name], capture_output=True)
c = json.load(open(d + '/p_ok/counts.json'))
vo, vb = json.load(open(d + '/v4b_ok.json')), json.load(open(d + '/v4b_bad.json'))
res['v4b_eq_income_parsed'] = c['counts']['EQ_INCOME_ERR'] == {'tag_lines': 1, 'parsed': 1} and c['unmatched_c3live_lines'] == 0
res['v4b_eq_income_khong_la_info'] = not c['info_lines_by_shape']
res['v4b_ok_PASS'] = vo['ok'] is True and vo['rules']['EQ_INCOME_ERR'] == {'grep': 1, 'tag_lines': 1, 'parsed': 1, 'ok': True}
res['v4b_dong_EQ_la_van_FAIL'] = vb['ok'] is False and vb['unmatched_c3live_lines'] == 1
subprocess.run(['rm', '-rf', d])
res['ok'] = all(res.values())
print(json.dumps(res, indent=0))
sys.exit(0 if res['ok'] else 1)
