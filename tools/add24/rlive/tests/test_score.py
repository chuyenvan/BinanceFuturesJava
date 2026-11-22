#!/usr/bin/env python3
"""ADD24 test bat buoc A1 (ERRATA3 C) cho bo cham R-LIVE tren du lieu TONG HOP (khong du lieu that):
(a) lech o mau nho => FAIL (khong INSUFFICIENT); (b) rig thua arm / stop / thoat / DCA => FAIL; (c) fill den SAU SUBMIT => U_before nhat quan
(margin pending); (e) tiem lech vao tung loai dong live => bo cham bat; (f) dong [C3-LIVE*] la => V4b bao. Exit 0 neu moi test dat."""
import copy, csv, gzip, json, os, shutil, subprocess, sys, tempfile
H = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, H)
import ref_size as RS
from datetime import datetime, timedelta, timezone
TZ7 = timezone(timedelta(hours=7)); MIN = 60000
S = int(datetime(2026, 1, 1, 0, 0, tzinfo=TZ7).timestamp() * 1000); E = S + 120 * MIN
START, END = '2026-01-01 00:00', '2026-01-01 02:00'
SYMS = ['AAAUSDT', 'BBBUSDT']


def wcsv(p, hdr, rows, gz=False):
    f = gzip.open(p, 'wt') if gz else open(p, 'w')
    w = csv.writer(f, lineterminator='\n'); w.writerow(hdr.split(',')); w.writerows(rows); f.close()


def base(root):
    fx, lv, rg = root + '/fx', root + '/live', root + '/rig'
    for d in (fx, lv, rg):
        os.makedirs(d)
    wcsv(fx + '/sel.csv.gz', 'ts,symbol,selectorScore,rank,gateValue,p15', [[t, s, 1, i + 1, 0.1, 0.01] for t in range(S, E, MIN) for i, s in enumerate(SYMS)], True)
    bars = []
    for s in SYMS:
        for t in range(S - 10 * MIN, E + 10 * MIN, MIN):
            hi = 0.1072 if (s == 'AAAUSDT' and t == S + 30 * MIN) else 0.1005
            bars.append([s, t, 0.1, hi, 0.0995, 0.1])
    wcsv(fx + '/klines.csv.gz', 'symbol,t,o,h,l,c', bars, True)
    json.dump({'symbols': [{'symbol': s, 'filters': [{'filterType': 'LOT_SIZE', 'stepSize': '1'}, {'filterType': 'PRICE_FILTER', 'tickSize': '0.0001'}]}
                           for s in SYMS]}, open(fx + '/exinfo.json', 'w'))
    d0 = S + 10 * MIN
    b1 = float(RS.budget(1000.0, 0.0, 0)); q1 = int(b1 / 0.1); n1 = q1 * 0.1
    u2 = n1 / 1000.0; b2 = float(RS.budget(1000.0, u2, 0)); q2 = int(b2 / 0.1); n2 = q2 * 0.1
    t1, t2 = d0 + MIN + 6000, d0 + MIN + 6400
    cid1, cid2 = 'c3-AAAUSDT-%d-0' % (d0 // MIN), 'c3-BBBUSDT-%d-0' % (d0 // MIN)
    L = {'submit.csv': ('log_ms,symbol,level,outcome,cid,qty,budget,legIdx,notional,U_before,file',
                        [[t1, 'AAAUSDT', 'PREDICT_SYMBOL_TRADE', 'SUBMITTED', cid1, q1, b1, 0, n1, 0.0, 'f'],
                         [t2, 'BBBUSDT', 'PREDICT_SYMBOL_TRADE', 'SUBMITTED', cid2, q2, b2, 0, n2, u2, 'f']]),
         # (c) khop cua leg 1 den SAU SUBMIT leg 2, gia khac sizing
         'fill_stream.csv': ('log_ms,via,symbol,cid,qty,avg,ref,file', [[t2 + 500, 'stream', 'AAAUSDT', cid1, q1, 0.1003, 0.1, 'f'],
                                                                          [t2 + 900, 'stream', 'BBBUSDT', cid2, q2, 0.1001, 0.1, 'f']]),
         'trail_arm.csv': ('log_ms,symbol,entry,px,peak,SL,file', [[S + 31 * MIN + 6000, 'AAAUSDT', 0.1, 0.1072, 0.1072, 0.104, 'f']]),
         'trail_stop.csv': ('log_ms,symbol,act,stop,cid,mode,file', [[S + 31 * MIN + 7000, 'AAAUSDT', 'ARM', 0.104, 'c3s-AAAUSDT-1-1', 'closePosition', 'f']]),
         'book_close.csv': ('log_ms,symbol,reason,legs,qty,avg,exitQty,exitAvg,realized,fee,file', []),
         'tick_dts.csv': ('dts', [[t] for t in range(S, E, MIN)])}
    for f, (h, r) in L.items():
        wcsv(lv + '/' + f, h, r)
    R = {'legs.csv': ('decision_ts,submit_ms,symbol,level,outcome,cid,qty,budget,margin_before,capital,ref_px,sizing_px,leg_idx,tick,detail,eq,eq_at,dca_tag',
                      [[d0, t1, 'AAAUSDT', 'PREDICT_SYMBOL_TRADE', 'SUBMITTED', cid1, q1, b1, 0, 1000, 0.1, 0.1, 0, 0.0001, '', 1000, 0, ''],
                       [d0, t2, 'BBBUSDT', 'PREDICT_SYMBOL_TRADE', 'SUBMITTED', cid2, q2, b2, n1, 1000, 0.1, 0.1, 0, 0.0001, '', 1000, 0, '']]),
         'events.csv': ('ms,t7,type,symbol,value,detail', [[S + 31 * MIN, '-', 'TRAIL_ARM', 'AAAUSDT', 0.0001, ''],
                                                           [S + 31 * MIN + 1000, '-', 'TRAIL_STOP_PLACED', 'AAAUSDT', 0.104, 'ARM']]),
         'fills.csv': ('ms,symbol,side,qty,price,cid,rp,fee', [])}
    for f, (h, r) in R.items():
        wcsv(rg + '/' + f, h, r)
    json.dump({'errors': [], 'ks_any_latch': False}, open(rg + '/result.json', 'w'))
    open(rg + '/run.log', 'w').write('ok\n')
    return fx, lv, rg


def score(fx, lv, rg, out):
    p = subprocess.run([sys.executable, H + '/rlive_score.py', '--live', lv, '--rig', rg, '--fx', fx, '--cap', '1000', '--start', START,
                        '--end', END, '--out', out], capture_output=True, text=True)
    if p.returncode != 0:
        print(p.stderr[-2000:]); raise SystemExit('score loi')
    return json.load(open(out + '/score.json'))


def edit(p, fn):
    r = list(csv.DictReader(open(p))); h = list(r[0].keys()) if r else open(p).readline().strip().split(',')
    r = fn(r)
    with open(p, 'w') as f:
        w = csv.DictWriter(f, fieldnames=h, lineterminator='\n'); w.writeheader(); w.writerows(r)


def addrow(p, row):
    with open(p, 'a') as f:
        csv.writer(f, lineterminator='\n').writerow(row)


RES = []


def check(name, cond, detail):
    RES.append((name, bool(cond), detail)); print(('OK   ' if cond else 'FAIL ') + name + ' | ' + json.dumps(detail))


def case(name, mut, expect):
    root = tempfile.mkdtemp(dir='/dev/shm/add24')
    try:
        fx, lv, rg = base(root)
        mut(fx, lv, rg)
        s = score(fx, lv, rg, root + '/o')
        st = s['status']
        check(name, all(st[k] == v for k, v in expect.items()), {k: st[k] for k in expect})
        return s
    finally:
        shutil.rmtree(root)


def main():
    # goc: khong lech => khong FAIL nao (mau nho => INSUFFICIENT), L-S 0 fail (c)
    s = case('goc_khong_lech_INS', lambda *a: None, {'L-E': 'INSUFFICIENT', 'L-S': 'INSUFFICIENT', 'L-S2': 'INSUFFICIENT', 'L-T': 'INSUFFICIENT',
                                                    'L-SL': 'INSUFFICIENT', 'L-K': 'PASS'})
    check('c_fill_sau_submit_U_nhat_quan', s['L-S']['fail'] == 0 and s['L-S']['n'] == 2, s['L-S'])
    # (a) lech o mau nho
    case('a1_rig_budget_lech_3e-3', lambda fx, lv, rg: edit(rg + '/legs.csv', lambda r: [dict(x, budget=float(x['budget']) * 1.003) if x['symbol'] == 'BBBUSDT' else x for x in r]),
         {'L-S2': 'FAIL'})
    case('a2_rig_thieu_1_SUBMIT', lambda fx, lv, rg: edit(rg + '/legs.csv', lambda r: r[:1]), {'L-E': 'FAIL', 'L-N': 'PASS'})
    case('a3_live_U_before_sai', lambda fx, lv, rg: edit(lv + '/submit.csv', lambda r: [dict(x, U_before=float(x['U_before']) * 1.01) if x['symbol'] == 'BBBUSDT' else x for x in r]),
         {'L-S': 'FAIL'})
    # (b) rig thua
    case('b1_rig_thua_arm', lambda fx, lv, rg: addrow(rg + '/events.csv', [S + 80 * MIN, '-', 'TRAIL_ARM', 'BBBUSDT', 0, '']), {'L-T': 'FAIL'})
    case('b2_rig_thua_stop', lambda fx, lv, rg: addrow(rg + '/events.csv', [S + 90 * MIN, '-', 'TRAIL_STOP_PLACED', 'BBBUSDT', 0.098, '']), {'L-SL': 'FAIL'})
    case('b3_rig_thua_thoat', lambda fx, lv, rg: addrow(rg + '/fills.csv', [S + 95 * MIN, 'AAAUSDT', 'SELL', 225, 0.104, 'c3s-AAAUSDT-1-1', 0, 0]), {'L-X': 'FAIL'})
    case('b4_rig_thua_DCA', lambda fx, lv, rg: addrow(rg + '/legs.csv', [S + 60 * MIN, S + 61 * MIN, 'AAAUSDT', 'DCA_LEVEL1', 'SUBMITTED', 'c3-AAAUSDT-x-1', 100, 10, 22, 1000, 0.1, 0.1, 1, 0.0001, '', 1000, 0, '']),
         {'L-D': 'FAIL', 'L-E': 'FAIL'})
    # (e) tiem lech vao tung loai dong live
    case('e1_SUBMIT_budget', lambda fx, lv, rg: edit(lv + '/submit.csv', lambda r: [dict(x, budget=float(x['budget']) * 1.01) for x in r]), {'L-S': 'FAIL', 'L-S2': 'FAIL'})
    case('e2_SUBMIT_thua_live', lambda fx, lv, rg: addrow(lv + '/submit.csv', [S + 50 * MIN + 66000, 'BBBUSDT', 'PREDICT_SYMBOL_TRADE', 'SUBMITTED', 'c3-BBBUSDT-%d-0' % ((S + 50 * MIN) // MIN), 100, 10, 0, 10, 0.05, 'f']),
         {'L-E': 'FAIL'})
    case('e3_arm_lech_4_phut', lambda fx, lv, rg: edit(lv + '/trail_arm.csv', lambda r: [dict(x, log_ms=int(x['log_ms']) + 4 * MIN) for x in r]), {'L-T': 'FAIL'})
    case('e4_stop_gia_lech_1pct', lambda fx, lv, rg: edit(lv + '/trail_stop.csv', lambda r: [dict(x, stop=float(x['stop']) * 1.01) for x in r]), {'L-SL': 'FAIL'})
    case('e5_stop_kieu_khong_4130', lambda fx, lv, rg: edit(lv + '/trail_stop.csv', lambda r: [dict(x, mode='qty+reduceOnly') for x in r]), {'L-SL': 'FAIL'})
    def e6(fx, lv, rg):
        addrow(lv + '/book_close.csv', [S + 95 * MIN + 3000, 'AAAUSDT', 'TRAIL', 1, 225, 0.1, 225, 0.1, 0, 0, 'f'])
        addrow(rg + '/fills.csv', [S + 95 * MIN, 'AAAUSDT', 'SELL', 225, 0.104, 'c3s-AAAUSDT-1-1', 0, 0])
    case('e6_thoat_gia_lech_-3.8pct', e6, {'L-X': 'FAIL'})
    case('e7_thoat_live_thua', lambda fx, lv, rg: addrow(lv + '/book_close.csv', [S + 95 * MIN, 'AAAUSDT', 'TIME_STOP_168H', 1, 225, 0.1, 225, 0.1, 0, 0, 'f']), {'L-X': 'FAIL'})
    case('e8_DCA_live_thua', lambda fx, lv, rg: addrow(lv + '/submit.csv', [S + 60 * MIN + 66000, 'AAAUSDT', 'DCA_LEVEL1', 'SUBMITTED', 'c3-AAAUSDT-%d-1' % ((S + 60 * MIN) // MIN), 100, 10, 1, 10, 0.05, 'f']),
         {'L-D': 'FAIL'})
    def e9(fx, lv, rg):
        open(lv + '/order_4130.csv', 'w').write('log_ms,cid,symbol,file\n%d,c3s-BBBUSDT-1-2,BBBUSDT,f\n' % (S + 100 * MIN))
    case('e9_4130_khong_thay_stop', e9, {'L-K': 'FAIL'})
    # nhan: lech co nhan khong lam FAIL (N9 EQ cua so 120 s, N3 khong tick) - kiem gan nhan dung chieu
    def n9(fx, lv, rg):
        addrow(rg + '/legs.csv', [S + 70 * MIN, S + 71 * MIN, 'BBBUSDT', 'PREDICT_SYMBOL_TRADE', 'SUBMITTED', 'c3-BBBUSDT-y-0', 100, 10, 22, 1000, 0.1, 0.1, 0, 0.0001, '', 1000, 0, ''])
        open(lv + '/eq_unavail.csv', 'w').write('log_ms,file\n%d,f\n' % (S + 70 * MIN + 100000))
    s9 = case('n9_cua_so_120s_giai_thich', n9, {'L-E': 'INSUFFICIENT'})
    check('n9_label', s9['labels_n']['N9'] == 1, s9['labels_n'])
    def n3live(fx, lv, rg):
        addrow(lv + '/submit.csv', [S + 50 * MIN + 66000, 'BBBUSDT', 'PREDICT_SYMBOL_TRADE', 'SUBMITTED', 'c3-BBBUSDT-%d-0' % ((S + 50 * MIN) // MIN), 100, 10, 0, 10, 0.05, 'f'])
        edit(lv + '/tick_dts.csv', lambda r: [x for x in r if int(x['dts']) != S + 50 * MIN])
    case('n3_khong_ap_cho_live_co_rig_khong', n3live, {'L-E': 'FAIL'})
    # ---- luot 4: test cua A1 (r2/a1_tests.py) tai lap + ERRATA4 C1/C2 + N12 + L-D REF gia
    def a1_1(fx, lv, rg):
        addrow(rg + '/legs.csv', [S + 40 * MIN, S + 41 * MIN, 'BBBUSDT', 'DCA_LEVEL1', 'SUBMITTED', 'c3-BBBUSDT-z-1', 100, 10, 22, 1000, 0.1, 0.1, 1, 0.0001, '', 1000, 0, ''])
    case('A1-1_rig_DCA_thua_mau_nho', a1_1, {'L-E': 'FAIL', 'L-D': 'FAIL'})
    def a1_1b(fx, lv, rg):
        addrow(lv + '/book_close.csv', [S + 95 * MIN + 3000, 'AAAUSDT', 'TRAIL', 1, 225, 0.1, 225, 0.1039, 0, 0, 'f'])
        addrow(rg + '/fills.csv', [S + 98 * MIN, 'AAAUSDT', 'SELL', 225, 0.1039, 'c3s-AAAUSDT-1-1', 0, 0])
    case('A1-1b_thoat_lech_3_phut_khong_REF', a1_1b, {'L-X': 'FAIL'})
    case('A1-2_rig_thua_stop_trong_2p_cua_stop_live', lambda fx, lv, rg: addrow(rg + '/events.csv', [S + 32 * MIN, '-', 'TRAIL_STOP_PLACED', 'AAAUSDT', 0.105, 'MOVE']),
         {'L-SL': 'FAIL'})
    def n9c(fx, lv, rg):
        addrow(rg + '/legs.csv', [S + 70 * MIN, S + 71 * MIN, 'BBBUSDT', 'PREDICT_SYMBOL_TRADE', 'SUBMITTED', 'c3-BBBUSDT-y-0', 100, 10, 22, 1000, 0.1, 0.1, 0, 0.0001, '', 1000, 0, ''])
        open(lv + '/eq_unavail.csv', 'w').write('log_ms,file\n%d,f\n' % (S + 70 * MIN + 100000))
    def a1_3(fx, lv, rg):        # cum rig N9 DONG luc S+75 => arm/stop rig BBB S+110 NGOAI cum => KHONG ke thua => FAIL
        n9c(fx, lv, rg)
        addrow(rg + '/fills.csv', [S + 75 * MIN, 'BBBUSDT', 'SELL', 100, 0.1, 'c3s-BBBUSDT-y-1', 0, 0])
        addrow(rg + '/events.csv', [S + 110 * MIN, '-', 'TRAIL_ARM', 'BBBUSDT', 0, ''])
        addrow(rg + '/events.csv', [S + 110 * MIN + 1000, '-', 'TRAIL_STOP_PLACED', 'BBBUSDT', 0.098, 'ARM'])
    case('A1-3_arm_stop_rig_ngoai_cum_N9_FAIL', a1_3, {'L-T': 'FAIL', 'L-SL': 'FAIL'})
    def c1_in(fx, lv, rg):       # cum rig N9 CHUA dong => arm + stop rig BBB trong cum => ke_thua N9 (khong FAIL)
        n9c(fx, lv, rg)
        addrow(rg + '/events.csv', [S + 90 * MIN, '-', 'TRAIL_ARM', 'BBBUSDT', 0, ''])
        addrow(rg + '/events.csv', [S + 90 * MIN + 1000, '-', 'TRAIL_STOP_PLACED', 'BBBUSDT', 0.098, 'ARM'])
    sc = case('C1_trong_cum_N9_ke_thua', c1_in, {'L-T': 'INSUFFICIENT', 'L-SL': 'INSUFFICIENT'})
    check('C1_dem_ke_thua', sc['inherit_n']['ke_thua'] == 2, sc['inherit_n'])
    case('A1-3b_arm_rig_truoc_cum_N9', lambda fx, lv, rg: (n9c(fx, lv, rg), addrow(rg + '/events.csv', [S + 50 * MIN, '-', 'TRAIL_ARM', 'BBBUSDT', 0, ''])),
         {'L-T': 'FAIL'})
    def c1_side(fx, lv, rg):     # sai phia: arm LIVE BBB trong khoang cum RIG N9 => khong ke thua
        n9c(fx, lv, rg)
        addrow(lv + '/trail_arm.csv', [S + 90 * MIN + 6000, 'BBBUSDT', 0.1, 0.1072, 0.1072, 0.104, 'f'])
    case('C1_sai_phia_FAIL', c1_side, {'L-T': 'FAIL'})
    def c1_root_unexp(fx, lv, rg):   # cum rig thua KHONG nhan (UNEXPLAINED) => arm cua no khong ke thua
        addrow(rg + '/legs.csv', [S + 70 * MIN, S + 71 * MIN, 'BBBUSDT', 'PREDICT_SYMBOL_TRADE', 'SUBMITTED', 'c3-BBBUSDT-y-0', 100, 10, 22, 1000, 0.1, 0.1, 0, 0.0001, '', 1000, 0, ''])
        addrow(rg + '/events.csv', [S + 90 * MIN, '-', 'TRAIL_ARM', 'BBBUSDT', 0, ''])
    case('C1_goc_khong_nhan_khong_ke_thua', c1_root_unexp, {'L-T': 'FAIL', 'L-E': 'FAIL'})
    def c1_matched(fx, lv, rg):  # (e) cum AAA leg 0 KHOP => arm rig thua tren AAA khong ke thua (co N9 o phut khac)
        open(lv + '/eq_unavail.csv', 'w').write('log_ms,file\n%d,f\n' % (S + 10 * MIN + 30000))
        addrow(rg + '/events.csv', [S + 60 * MIN, '-', 'TRAIL_ARM', 'AAAUSDT', 0, ''])
    case('C1_cum_khop_khong_ke_thua', c1_matched, {'L-T': 'FAIL'})
    # ---- luot 5 (ERRATA5): tier3 TIEM theo vet => rig van DCA = KHONG GIAI THICH; > 3 cum tiem => L-D INSUFFICIENT khong phu; N6 = [GATE] n_skipfull
    def t3_rig_dca(fx, lv, rg):
        addrow(rg + '/legs.csv', [S + 60 * MIN, S + 61 * MIN, 'AAAUSDT', 'DCA_LEVEL1', 'SUBMITTED', 'c3-AAAUSDT-x-1', 100, 10, 22, 1000, 0.1, 0.1, 1, 0.0001, '', 1000, 0, ''])
        open(lv + '/skip.csv', 'w').write('log_ms,symbol,level,outcome,file\n%d,AAAUSDT,DCA_LEVEL1,TIER3_DCA,f\n' % (S + 61 * MIN + 6000))
    case('tier3_rig_van_DCA_FAIL', t3_rig_dca, {'L-D': 'FAIL'})
    def t3_many(fx, lv, rg):
        open(lv + '/skip.csv', 'w').write('log_ms,symbol,level,outcome,file\n' + ''.join('%d,%s,DCA_LEVEL1,TIER3_DCA,f\n' % (S + (61 + i) * MIN + 6000, s_)
                                                                                    for i, s_ in enumerate(['CCCUSDT', 'DDDUSDT', 'EEEUSDT', 'FFFUSDT'])))
    st = case('tier3_4_cum_L-D_INS_khong_phu', t3_many, {'L-D': 'INSUFFICIENT'})
    check('tier3_no_cover', st['L-D_no_cover'] is True, {'no_cover': st['L-D_no_cover']})
    def n6(fx, lv, rg):
        addrow(rg + '/legs.csv', [S + 70 * MIN, S + 71 * MIN, 'BBBUSDT', 'PREDICT_SYMBOL_TRADE', 'SUBMITTED', 'c3-BBBUSDT-y-0', 100, 10, 22, 1000, 0.1, 0.1, 0, 0.0001, '', 1000, 0, ''])
        open(lv + '/gate.csv', 'w').write('log_ms,n_cand,n_rej,n_pass,n_skipfull,u,file\n%d,5,5,0,3,0.6100,f\n' % (S + 71 * MIN + 6000))
    s6 = case('N6_GATE_n_skipfull', n6, {'L-E': 'INSUFFICIENT'})
    check('N6_label', s6['labels_n']['N6'] == 1, s6['labels_n'])
    def n6_no(fx, lv, rg):
        addrow(rg + '/legs.csv', [S + 70 * MIN, S + 71 * MIN, 'BBBUSDT', 'PREDICT_SYMBOL_TRADE', 'SUBMITTED', 'c3-BBBUSDT-y-0', 100, 10, 22, 1000, 0.1, 0.1, 0, 0.0001, '', 1000, 0, ''])
        open(lv + '/gate.csv', 'w').write('log_ms,n_cand,n_rej,n_pass,n_skipfull,u,file\n%d,5,5,0,0,0.1000,f\n' % (S + 71 * MIN + 6000))
    case('N6_n_skipfull_0_FAIL', n6_no, {'L-E': 'FAIL'})
    def ldref(fx, lv, rg):       # DCA live bac 1 khi gia CHUA giam 50 % => L-D REF FAIL (rig cung co leg => cap khop)
        addrow(lv + '/submit.csv', [S + 60 * MIN + 66000, 'AAAUSDT', 'DCA_LEVEL1', 'SUBMITTED', 'c3-AAAUSDT-%d-1' % ((S + 60 * MIN) // MIN), 100, 10, 1, 10, 0.05, 'f'])
        addrow(rg + '/legs.csv', [S + 60 * MIN, S + 61 * MIN, 'AAAUSDT', 'DCA_LEVEL1', 'SUBMITTED', 'c3-AAAUSDT-%d-1' % ((S + 60 * MIN) // MIN), 100, 10, 22, 1000, 0.1, 0.1, 1, 0.0001, '', 1000, 0, ''])
    sr = case('L-D_REF_gia_DCA_truoc_bac_FAIL', ldref, {'L-D': 'FAIL'})
    check('L-D_REF_dem', sr['L-D']['ref_gia_bad'] == 1, sr['L-D'])
    bad = [n for n, ok, _ in RES if not ok]
    json.dump({'n': len(RES), 'fail': bad, 'results': [{'test': n, 'ok': ok, 'detail': d} for n, ok, d in RES]},
              open(os.environ.get('TEST_OUT', '/dev/shm/add24/test_score.json'), 'w'), indent=1)
    print('TONG %d test, FAIL %d %s' % (len(RES), len(bad), bad))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
