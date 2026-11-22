#!/usr/bin/env python3
"""[LUOT8 R7] Test tong hop bo cham R-SIM: tiem lech vao BAN SAO output DEV (mac dinh DEV7_sim) roi chay score_rsim + classify_sx + verdict_rsim.
(a) 1 lenh PREDICT sim bi jar REJECT (trace pass->0); (b) 1 khop thoat +3'; (c) 1 size x1,01 (ssz_jar f_jar); (d) 1 ly do thoat doi (them
TRAIL_TIME_STOP tai phut khop cua 1 cum TRAIL); (e) 1 cum mat (xoa leg SUBMITTED); (f) rig them 1 leg DCA SUBMITTED trong cum sim;
(g) khong tiem. Ky vong: a-f => FAIL, g => nhu goc. usage: test_inject.py <D_src> <FX> <vtier.json> <lo> <hi> <quarter> <work_dir>"""
import csv, gzip, json, os, shutil, subprocess, sys, logging
logging.basicConfig(level=logging.INFO, format='%(message)s'); L = logging.getLogger()
SRC, FX, VT, lo, hi, Q, W = sys.argv[1:8]
B = os.path.dirname(os.path.abspath(__file__))
FILES = ['legs.csv', 'fills.csv', 'events.csv', 'trace_dec.csv.gz', 'ssz_jar.csv', 'gates.json', 'add24_meta.txt', 'outcomes.csv', 'market.csv']
sc0 = json.load(open(SRC + '/score.json'))
sub = [o for o in sc0['rows'] if o.get('rig') == 'SUBMITTED' and o.get('rig_why') == 'TRAIL' and o['sim_why'] == 'TRAIL' and not o['dca'] and o['dmin'] == 0]
pick = sub[len(sub) // 2]
def rd(p): return list(csv.DictReader(open(p)))
def wr(p, rows, fn):
    with open(p, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fn); w.writeheader(); [w.writerow(r) for r in rows]
def prep(name):
    d = os.path.join(W, name); shutil.rmtree(d, ignore_errors=True); os.makedirs(d)
    for f in FILES:
        if os.path.exists(os.path.join(SRC, f)): shutil.copy(os.path.join(SRC, f), d)
    return d
legs0 = rd(SRC + '/legs.csv'); lf = list(legs0[0].keys())
leg_pick = [x for x in legs0 if x['symbol'] == pick['sym'] and x['outcome'] == 'SUBMITTED' and x['level'] != 'DCA_LEVEL1']
t0 = int(leg_pick[0]['decision_ts']); cid = leg_pick[0]['cid']
def inj(name, d):
    if name == 'a':
        sp = [o for o in sc0['rows'] if o['level'] == 'PREDICT_SYMBOL_TRADE' and o.get('rig') == 'SUBMITTED'][0]
        rows = []; fn = None; hit = 0
        with gzip.open(d + '/trace_dec.csv.gz', 'rt') as f:
            r = csv.DictReader(f); fn = r.fieldnames
            leg = [x for x in legs0 if x['symbol'] == sp['sym'] and x['level'] == 'PREDICT_SYMBOL_TRADE' and x['outcome'] == 'SUBMITTED'][0]
            for x in r:
                if x['symbol'] == sp['sym'] and x['ts'] == leg['decision_ts'] and x['pass'] == '1': x['pass'] = '0'; hit += 1
                rows.append(x)
        with gzip.open(d + '/trace_dec.csv.gz', 'wt', newline='') as f:
            w = csv.DictWriter(f, fieldnames=fn); w.writeheader(); [w.writerow(x) for x in rows]
        return 'REJECT %s %s rows=%d' % (sp['sym'], sp['start'], hit)
    if name == 'b':
        fl = rd(d + '/fills.csv'); n = 0
        for f in fl:
            if f['symbol'] == pick['sym'] and f['side'] == 'SELL' and int(f['ms']) == pick['rig_exit_ms']: f['ms'] = str(int(f['ms']) + 180000); n += 1
        wr(d + '/fills.csv', fl, list(fl[0].keys())); return 'EXIT+3 %s %s n=%d' % (pick['sym'], pick['start'], n)
    if name == 'c':
        sj = rd(d + '/ssz_jar.csv'); sj[0]['f_jar'] = repr(float(sj[0]['f_jar']) * 1.01); wr(d + '/ssz_jar.csv', sj, list(sj[0].keys()))
        return 'SIZE x1.01 %s %s' % (sj[0]['symbol'], sj[0]['ts'])
    if name == 'd':
        ev = rd(d + '/events.csv'); ev.append(dict(ms=str(pick['rig_exit_ms']), t7='', type='TRAIL_TIME_STOP', symbol=pick['sym'], value='0', detail='INJECT'))
        wr(d + '/events.csv', ev, list(ev[0].keys())); return 'REASON->TIME_STOP %s %s' % (pick['sym'], pick['start'])
    if name == 'e':
        lg = [x for x in rd(d + '/legs.csv') if not (x['cid'] == cid)]; wr(d + '/legs.csv', lg, lf); return 'DROP leg %s' % cid
    if name == 'f':
        lg = rd(d + '/legs.csv'); x = dict(leg_pick[0]); x['level'] = 'DCA_LEVEL1'; x['decision_ts'] = str(t0 + 3600000); x['cid'] = cid[:-2] + '-1'; x['leg_idx'] = '1'
        lg.append(x); wr(d + '/legs.csv', lg, lf); return 'RIG DCA extra %s %d' % (pick['sym'], t0 + 3600000)
    return 'none'
out = {}
for name in ('a', 'b', 'c', 'd', 'e', 'f', 'g'):
    d = prep('inj_' + name); what = inj(name, d)
    sargs = ['python3', B + '/score_rsim.py', d, FX, lo, hi, '--vtier', VT, '--json', d + '/score.json'] + (['--quarter', Q] if Q != '-' else [])
    subprocess.run(sargs, stdout=open(d + '/score.txt', 'w'), stderr=subprocess.STDOUT, check=True)
    subprocess.run(['python3', B + '/classify_sx.py', d, FX, lo, hi, 'sim'], stdout=open(d + '/classify.txt', 'w'), stderr=subprocess.STDOUT, check=True)
    subprocess.run(['python3', B + '/verdict_rsim.py', d, FX, VT], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    v = json.load(open(d + '/verdict_rsim.json'))
    out[name] = dict(inject=what, result=v['RESULT']['result'], bb=v['RESULT']['bb'])
    L.info('%s %-42s -> %s %s', name, what, v['RESULT']['result'], json.dumps(v['RESULT']['bb']))
ok = all(out[k]['result'] == 'FAIL' for k in 'abcdef')
out['ALL_A_F_FAIL'] = ok
json.dump(out, open(os.path.join(W, 'test_inject.json'), 'w'), indent=1)
L.info('ALL_A_F_FAIL %s', ok)
