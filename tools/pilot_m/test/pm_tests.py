#!/usr/bin/env python3
# pm_tests.py - du lieu log TONG HOP (tu sinh, dung dinh dang live) + test tiem loi cho pilot_m_daily.py.
# Chi stdlib, logging (khong print). Goi tu test_pilot_m_daily.sh: python3 -I pm_tests.py <thu_muc_tam>
import datetime as dt
import gzip
import json
import logging
import math
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLDIR = os.path.dirname(HERE)
TOOL = os.environ.get('PM_TOOL') or os.path.join(TOOLDIR, 'pilot_m_daily.py')   # PM_TOOL: chay tren mutant
sys.path.insert(0, TOOLDIR)
import importlib.util  # noqa: E402
_sp = importlib.util.spec_from_file_location('pilot_m_daily', TOOL)
P = importlib.util.module_from_spec(_sp)
_sp.loader.exec_module(P)  # ham thuan (trail_sl, official_time_ok) lay tu CHINH cong cu dang test (ke ca mutant)

LOG = logging.getLogger('pm_test')
H = 3600000
M = 60000
LEAK_RX = re.compile(r'\b(realized|phi|tmb0|tmb|eq|acct_eq|acct_peak)=(?!<X>)')
LEAK_TOK = ['10012.34', '10035.85', '10234.56', '999.12', '1.0800', '0.0236', '-2.0400', 'abcdef123SIG',
            '1234567890:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA', '1234.56', '1240.11', '1200.77', '33.33', '5.55',
            '10000.00094380', '12.34 + 56.78']


def ts(t):
    return dt.datetime.fromtimestamp(t / 1000.0, P.TZ7).strftime('%d/%m/%Y %H:%M:%S.%f')[:-3]


def L(t, msg, thr='pool-1-thread-1', lg='c.b.c.c.e.C3LiveEntry', lvl='INFO'):
    return (t, '%s %-5s [%s] %s: %s' % (ts(t), lvl, thr, lg, msg))


OK = 'OkHttp https://fstream.binance.com/...'
FA = 'c.b.c.c.f.FillAccounting'
TSM = 'c.b.c.c.e.TrailingStopManager'
DET = 'c.b.c.t.DetectEntrySignal2TradeNormal'


class Scn(object):
    def __init__(self, D, ss):
        self.D, self.ss = D, ss
        self.logs, self.sel, self.check, self.complete, self.nopull = {}, {}, {}, {}, set()
        self.cron = []
        self.no_cron = False
        self.cron_split = None     # t: dong TOM TAT < t ghi vao cron.log.1
        self.no_cron1 = False
        self.iv = []          # khoang cum mo (t_xac_nhan, t_dong) cho n cua RECON

    def add(self, day, item):
        self.logs.setdefault(day, []).append(item)

    def write(self, root):
        pr = os.path.join(root, 'pull242')
        d = self.ss
        while d <= self.D:
            if d not in self.nopull:
                base = os.path.join(pr, d.isoformat())
                os.makedirs(os.path.join(base, 'logs'), exist_ok=True)
                os.makedirs(os.path.join(base, 'dumps'), exist_ok=True)
                with gzip.open(os.path.join(base, 'logs', 'full.log@1_1.gz'), 'wt', encoding='utf-8') as fh:
                    for _, line in sorted(self.logs.get(d, []), key=lambda x: x[0]):
                        fh.write(line + '\n')
                with gzip.open(os.path.join(base, 'dumps', 'sel_dump_%s_065000.csv.gz' % d.strftime('%Y%m%d')), 'wt') as fh:
                    fh.write('ts,symbol,selectorScore,rank,gateValue,p15\n')
                    for (t, s, r) in self.sel.get(d, []):
                        fh.write('%d,%s,-0.8,%d,0.3,0.006\n' % (t, s, r))
                ck = {'STATUS': 'OK', 'D': d.isoformat(), 'missing': '', 'fails': '', 'errors': '', 'log_minutes': '1440',
                      'log_max_gap_min': '0'}
                ck.update(self.check.get(d, {}))
                with open(os.path.join(base, 'check.txt'), 'w') as fh:
                    for kk, vv in ck.items():
                        fh.write('%s=%s\n' % (kk, vv))
                if self.complete.get(d, True):
                    with open(os.path.join(base, 'COMPLETE'), 'w') as fh:
                        fh.write('x\n')
            d += dt.timedelta(days=1)
        if not self.no_cron:
            rows = sorted(self.cron, key=lambda x: x[0])
            sp = self.cron_split
            if sp is not None and not self.no_cron1:
                with open(os.path.join(root, 'cron.log.1'), 'w') as fh:
                    for t, line in rows:
                        if t < sp:
                            fh.write(line + '\n')
            with open(os.path.join(root, 'cron.log'), 'w') as fh:
                for t, line in rows:
                    if sp is None or t >= sp:
                        fh.write(line + '\n')

    def n_at(self, t):
        return sum(1 for a, b in self.iv if a <= t < b)


def banner(t, cap, thr='ThreadManagerOrder'):
    m = ('[C3-LIVE] khoi dong adapter=LIVE gateway=c3scope book=run/c3live_book.json cum=1 leg_treo=0 c3_capital=%s '
         'tai_khoan=CHINH(pham vi c3) killSwitchArmed=true X14=true stream=live' % cap)
    return [L(t, m, thr, 'c.b.c.c.r.C3LiveRuntime', 'WARN'), L(t, '[C3-LIVE-ALERT] ' + m, thr, 'c.b.c.c.a.C3LiveAlerts', 'WARN')]


def heartbeat(s, d, flag='OFF', recon_skip=(), restart=None, eq_after=None, ks_eq=1000.0, n_off=None, prior=True,
              tt=None, eq_fn=None, ks_none=False, streak_jump=None, tt_drop=None):
    """KILLSW / RECON / TS-EXT / filler cho cua so ngay d (+ dong truoc cua so, + lookahead 80 phut)."""
    lo = P.day_lo(d)
    if prior:
      if True:
        s.add(d, L(lo - 49 * M, '[C3-LIVE-RECON] HOURLY khop: doi chieu qty c3 (%d cum) lech max=0.0000%% streak=100'
                   % s.n_at(lo - 49 * M), 'C3LIVE-OPS', 'c.b.c.c.r.Reconciler'))
      if not ks_none:
        s.add(d, L(lo - 60 * M + 6, '[KILLSW] HOURLY hour=x mode=act C1=0/0 C2=NA (met/edge) | lag_s=6 miss=0/517 api=positions '
                   'consec=0 order429=0 open=0 U=0.0000 eq=%.2f peak=%.2f dd=0.0000 acct_eq=10012.34 acct_peak=10035.85 '
                   'acct_dd=-0.0023 latch=NONE' % (ks_eq, ks_eq), 'C3LIVE-OPS', 'c.b.c.o.OpsHooks'))
    streak = 100
    for i in range(24):
        h0 = lo + i * H
        eq = eq_after if (eq_after is not None and restart is not None and h0 > restart) else ks_eq
        if eq_fn is not None and eq_fn(i) is not None:
            eq = eq_fn(i)
        if not ks_none:
          s.add(d, L(h0 + 6, '[KILLSW] HOURLY hour=x mode=act C1=0/0 C2=NA (met/edge) | lag_s=6 miss=0/517 api=positions '
                   'consec=0 order429=0 open=0 U=0.0000 eq=%.2f peak=%.2f dd=-0.0010 acct_eq=10012.34 acct_peak=10035.85 '
                   'acct_dd=-0.0023 latch=NONE' % (eq, eq), 'C3LIVE-OPS', 'c.b.c.o.OpsHooks'))
        s.add(d, L(h0 + 49000, '[TS-EXT] status now=x flagToday=%s dd=-0.27 deferring=0 []' % flag, 'TS-EXT', 'c.b.c.t.s.TsMktExt'))
        tr = h0 + 11 * M + 13000
        if restart is not None and restart < tr and (tr - H) < restart:
            streak = 0
        if i not in recon_skip:
            streak += 2 if streak_jump == i else 1
            n = s.n_at(tr) + (1 if (n_off is not None and n_off == i) else 0)
            s.add(d, L(tr, '[C3-LIVE-RECON] HOURLY khop: doi chieu qty c3 (%d cum) lech max=0.0000%% streak=%d' % (n, streak),
                       'C3LIVE-OPS', 'c.b.c.c.r.Reconciler'))
        for j in range(0, 60, 10):
            tm = h0 + j * M + 6000
            s.add(d, L(tm, 'Market level change: %s level: null symbols:500' % P.minute_str(tm - 66000), lg=DET))
    if flag == 'NA':
        s.add(d, L(lo + 3 * M + 48000, '[TS-EXT] flag day=%s flag=NA(->OFF) reason=thieu src=aero:1d final=false' % d.isoformat(),
                   'TS-EXT', 'c.b.c.t.s.TsMktExt', 'WARN'))
    elif flag is not None:
        s.add(d, L(lo + 3 * M + 48000, '[TS-EXT] flag day=%s flag=%s dd=-0.27 altEwIdx=0.73 P=-0.26 max30=0.05 '
                   'max30Day=2026-10-21 minN=1403 src=aero:1d final=false' % (d.isoformat(), flag), 'TS-EXT', 'c.b.c.t.s.TsMktExt'))
    for j in range(0, 80, 10):
        tm = lo + 24 * H + j * M + 6000
        s.add(d, L(tm, 'Market level change: %s level: null symbols:500' % P.minute_str(tm - 66000), lg=DET))
    # cron TOM TAT moi 2 phut
    t = lo - 10 * M
    while t < lo + 24 * H:
        kv = {'adapter': 'live', 'C3_CAPITAL': '1000', 'push': 'ON', 'latch': 'NONE', 'jar': '01cfbb43', 'khan': '0',
              'deadman': 'OK', 'khan_canh_bao': '0'}
        if tt:
            kv.update(tt(t) or {})
        if kv.get('_invalid'):
            kv.update({'adapter': '', 'C3_CAPITAL': '', 'push': 'OFF'})
        line = ('[%s] TOM TAT: adapter=%s C3_CAPITAL=%s push=%s latch=%s so_c3=1cum LEGACY=43 mem=1970MB jar=%s pause=0 '
                'tre_gia=0/60 deadman=%s tk=SUB key=43820b5b tmb=10234.56 dd=-0.0011 khan=%s eq=999.12 tmb0=10000.00 '
                'khan_canh_bao=%s' % (dt.datetime.fromtimestamp((t + 10000) / 1000.0, P.TZ7).strftime('%Y-%m-%d %H:%M:%S'),
                                      kv['adapter'], kv['C3_CAPITAL'], kv['push'], kv['latch'], kv['jar'], kv['deadman'],
                                      kv['khan'], kv['khan_canh_bao']))
        if not (tt_drop and tt_drop[0] <= t < tt_drop[1]):
            s.cron.append((t, line))
        t += 2 * M


def f9(x):
    return '%.9g' % x


def clean(o=None):
    """Kich ban SACH: D=2026-11-25, state tu D-7. Cum A (PREDICT, arm, trailing), B (BIG_DOWN + DCA leg 1), T (time-stop 168 h).
    o: tuy chon tiem loi (xem main)."""
    o = o or {}
    D = dt.date(2026, 11, 25)
    d7 = D - dt.timedelta(days=7)
    s = Scn(D, d7)
    lo, lo7 = P.day_lo(D), P.day_lo(d7)
    for d in [d7 + dt.timedelta(days=i) for i in range(7)]:
        s.add(d, L(P.day_lo(d) + H, 'Market level change: x level: null symbols:500', lg=DET))
    for x in banner(lo7 - 43 * M, '1000.0'):
        s.add(d7, x)
    # ---- cum T (mo D-7, due trong ngay D)
    dtsT = lo7 + 3 * H - M
    t0 = dtsT + 67000
    s.add(d7, L(t0, '[C3-LIVE] SUBMIT SYMTUSDT PREDICT_SYMBOL_TRADE SUBMITTED cid=c3-SYMTUSDT-%d-0 qty=40 budget=22.5 legIdx=0 '
                'notional=20.0 U_before=0.0' % (dtsT // M)))
    s.add(d7, L(t0 + 500, '[C3-LIVE-FILL] xac nhan qua stream SYMTUSDT c3-SYMTUSDT-%d-0 qty=40 avg=0.5 ref=0.4995' % (dtsT // M), OK, FA))
    if o.get('mt_arm_rst') or o.get('mt_arm_only'):
        d6 = d7 + dt.timedelta(days=1)
        ta = P.day_lo(d6) + 2 * H
        s.add(d6, L(ta, '[C3-LIVE-TRAIL] arm SYMTUSDT entry=0.5 px=0.536 peak=0.072 SL=0.52', 'C3LIVE-OPS', TSM))
        if o.get('mt_arm_rst'):
            s.add(d6, L(ta + H, '[C3-LIVE-TRAIL] SYMTUSDT khong con arm (DCA reset) => huy stop null', 'C3LIVE-OPS', TSM))
    due = t0 + 168 * H
    flag = o.get('flag', 'OFF')
    s.add(D, L(due + 5000, '[TS-EXT] defer-START SYMTUSDT age_h=168 flag=ON day=%s' % D, 'pool-3-thread-1', 'c.b.c.t.s.TsMktExt'))
    if flag in ('OFF', 'NA'):
        tts = due + (300000 if o.get('mt_late') else (-60000 if o.get('mt_early') else 10000))
        s.add(D, L(tts, '[C3-LIVE-TRAIL] TIME-STOP SYMTUSDT entry=0.5 px=0.45 gio_giu=168 => dong MARKET reduce-only', 'C3LIVE-OPS', TSM, 'WARN'))
        if not o.get('mt_no_clos'):
            s.add(D, L(tts + 5000, '[C3-LIVE-BOOK] dong cum SYMTUSDT ly do=TIME_STOP_168H legs=1 qty=40 avg=0.5 exitQty=40 exitAvg=0.449 '
                       'realized=-2.0400 phi=0.0090', OK, 'c.b.c.c.b.LiveBookC3'))
            s.add(D, L(tts + 5100, '[C3-LIVE] cum SYMTUSDT DA DONG tren san (TIME_STOP_168H) qty=40 avg=0.5 => da cap nhat so', OK, FA))
            s.iv.append((t0 + 500, tts + 5000))
        else:
            s.iv.append((t0 + 500, tts))
    else:
        s.iv.append((t0 + 500, P.FAR))
        if o.get('mt_ops_defer'):
            s.add(D, L(due + 6000, '[TS-EXT] defer-START SYMTUSDT age_h=168 flag=ON day=%s' % D, 'C3LIVE-OPS', 'c.b.c.t.s.TsMktExt'))
    # ---- cum A
    dtsA = lo + H
    tA = dtsA + (200000 if o.get('me0_late') else 67100)
    bA = dtsA // M
    s.sel.setdefault(D, []).append((dtsA, 'SYMAUSDT', 3))
    s.add(D, L(tA, '[C3-LIVE] SUBMIT SYMAUSDT PREDICT_SYMBOL_TRADE SUBMITTED cid=c3-SYMAUSDT-%d-0 qty=100 budget=%s legIdx=0 '
               'notional=%s U_before=0.0' % (bA, o.get('sa_budget', '22.5'), o.get('sa_notional', '22.45'))))
    avgA = '0.2290' if o.get('mx_slip') else '0.2250'
    s.add(D, L(tA + 400, '[C3-LIVE-FILL] xac nhan qua stream SYMAUSDT c3-SYMAUSDT-%d-0 qty=100 avg=%s ref=0.2245' % (bA, avgA), OK, FA))
    if o.get('eqwarn'):
        s.add(D, L(lo + 30 * M, '[C3-LIVE-EQ] CANH BAO ky quy tai khoan chinh: availableBalance=111.11 < 2 x margin c3 22.22',
                   'C3LIVE-OPS', 'c.b.c.c.r.C3MainEquity', 'WARN'))
    tArm = lo + 2 * H
    peak = P.f32((P.f32(0.241) - P.f32(0.225)) / P.f32(0.225))
    sl = P.trail_sl(0.225, peak)
    if o.get('bad_sl'):
        sl = sl * 1.01
    s.add(D, L(tArm, '[C3-LIVE-TRAIL] arm SYMAUSDT entry=0.225 px=0.241 peak=%s SL=%s' % (f9(peak), f9(sl)), 'C3LIVE-OPS', TSM))
    if o.get('dup_arm'):
        s.add(D, L(tArm + 30 * M, '[C3-LIVE-TRAIL] arm SYMAUSDT entry=0.225 px=0.241 peak=%s SL=%s' % (f9(peak), f9(sl)), 'C3LIVE-OPS', TSM))
    P1 = math.floor(P.trail_sl(0.225, peak) * 10000) / 10000.0
    cid1 = 'c3s-SYMAUSDT-%d-1' % (tArm // M)
    tS1 = tArm + (90000 if o.get('stop_arm_late') else 200)
    s.add(D, L(tS1 - 20, '[C3-LIVE-FILL] ALGO_UPDATE SYMAUSDT caid=%s X=NEW ai=' % cid1, OK, FA))
    s.add(D, L(tS1, '[C3-LIVE-TRAIL] SYMAUSDT ARM stop=%.4f cid=%s mode=closePosition (cu=null 0.0)' % (P1, cid1), 'C3LIVE-OPS', TSM))
    tM = lo + 3 * H
    P2 = P1 + (0.0001 if o.get('i3_small') else 0.002)
    cid2 = 'c3s-SYMAUSDT-%d-2' % (tM // M)
    if not o.get('no_algo_new'):
        s.add(D, L(tM + (70000 if o.get('algo_new_late') else 185), '[C3-LIVE-FILL] ALGO_UPDATE SYMAUSDT caid=%s X=NEW ai=' % cid2, OK, FA))
    s.add(D, L(tM + 200, '[C3-LIVE-TRAIL] SYMAUSDT MOVE stop=%.4f cid=%s mode=qty+reduceOnly (cu=%s %.4f)' % (P2, cid2, cid1, P1), 'C3LIVE-OPS', TSM))
    if o.get('trail_trunc'):
        s.add(D, L(tM + 300, '[C3-LIVE-TRAIL] SYMAUSDT MOVE sto', 'C3LIVE-OPS', TSM))
    if not o.get('no_cancel_old'):
        s.add(D, L(tM + 280, '[C3-LIVE-FILL] ALGO_UPDATE SYMAUSDT caid=%s X=CANCELED ai=' % cid1, OK, FA))
    tX = lo + 4 * H
    R = o.get('clos_reason', 'TRAILING_STOP')
    trig = o.get('trig', 'both')
    if trig == 'both':
        s.add(D, L(tX + 90, '[C3-LIVE-FILL] ALGO_UPDATE SYMAUSDT caid=%s X=TRIGGERING ai=' % cid2, OK, FA))
    s.add(D, L(tX + 100, '[C3-LIVE-FILL] SYMAUSDT stop khop 100@%.4f (stop=%.4f truot=0.00085)' % (P2 - 0.0002, P2), OK, FA))
    if o.get('sfil_extra'):
        s.add(D, L(tX + 150, '[C3-LIVE-FILL] SYMAUSDT stop khop 100@%.4f (stop=%.4f truot=0.00085)' % (P2 - 0.0002, P2), OK, FA))
    if not o.get('b12'):
        s.add(D, L(tX + 190, '[C3-LIVE-BOOK] dong cum SYMAUSDT ly do=%s legs=1 qty=100 avg=0.225 exitQty=100 exitAvg=%.4f realized=1.0800 '
                   'phi=0.0236' % (o.get('book_reason', R), P2 - 0.0002), OK, 'c.b.c.c.b.LiveBookC3'))
        if o.get('b2'):
            s.add(D, L(tX + 298, '[C3-LIVE] cum SYMAUSDT DA DO', OK, FA))
        elif not o.get('b1'):
            s.add(D, L(tX + 298, '[C3-LIVE] cum SYMAUSDT DA DONG tren san (%s) qty=100 avg=0.225 => da cap nhat so, xu ly 1 stop' % R, OK, FA))
    if trig in ('both', 'only_triggered'):
        s.add(D, L(tX + 299, '[C3-LIVE-FILL] ALGO_UPDATE SYMAUSDT caid=%s X=TRIGGERED ai=1' % cid2, OK, FA))
    if trig == 'late':
        s.add(D, L(tX + 70000, '[C3-LIVE-FILL] ALGO_UPDATE SYMAUSDT caid=%s X=TRIGGERED ai=1' % cid2, OK, FA))
    s.add(D, L(tX + 299, '[C3-LIVE-FILL] ALGO_UPDATE SYMAUSDT caid=%s X=FINISHED ai=1' % cid2, OK, FA))
    s.iv.append((tA + 400, tX + 100 if o.get('b12') else tX + 190))
    if o.get('leo_thang'):
        s.add(D, L(tX + 2 * H, '[C3-LIVE-RECON] SYMAUSDT: cum so da chot > 600000 ms ma san VAN con vi the 100 => leo thang UNKNOWN toan he',
                   'C3LIVE-OPS', 'c.b.c.c.r.Reconciler', 'ERROR'))
    # ---- cum B (BIG_DOWN) + DCA leg 1
    dtsB = lo + 5 * H
    tB = dtsB + 67000
    bB = dtsB // M
    if not o.get('no_bigdown'):
        s.add(D, L(dtsB + 66000, 'Market level change: %s level: BIG_DOWN symbols:500' % P.minute_str(dtsB), lg=DET))
    s.add(D, L(tB, '[C3-LIVE] SUBMIT SYMBUSDT BIG_DOWN SUBMITTED cid=c3-SYMBUSDT-%d-0 qty=10 budget=22.5 legIdx=0 notional=22.0 '
               'U_before=0.0' % bB))
    s.add(D, L(tB + 800, '[C3-LIVE-EXEC] FILL SYMBUSDT c3-SYMBUSDT-%d-0 qty=10 avg=2.2000 ref=2.1900 slip=0.00457' % bB,
               'C3LIVE-EXEC', 'c.b.c.c.e.C3LiveOrderExecutor'))
    tBend = P.FAR
    if o.get('delist'):
        tBend = lo + 16 * H
        s.add(D, L(tBend, '[C3-LIVE-BOOK] dong cum SYMBUSDT ly do=DELIST_SETTLE legs=2 qty=30 avg=1.4 exitQty=30 exitAvg=1.0 '
                   'realized=-9.9 phi=0.01', OK, 'c.b.c.c.b.LiveBookC3'))
        s.add(D, L(tBend + 100, '[C3-LIVE] cum SYMBUSDT DA DONG tren san (DELIST_SETTLE) qty=30 avg=1.4 => da cap nhat so', OK, FA))
    s.iv.append((tB + 800, tBend))
    if o.get('sfil_pre_arm'):
        s.add(D, L(lo + 10 * H, '[C3-LIVE-FILL] SYMBUSDT stop khop 1@1.0000 (stop=1.0000 truot=0.0)', OK, FA))
    dtsC = lo + 7 * H
    bC = dtsC // M
    s.add(D, L(dtsC + 66000, '[LIVE-DCA-GRID] site=x due=[SYMBUSDT]', lg=DET))
    if not o.get('no_aipass'):
        s.add(D, L(dtsC + 66300, u'\u2705 AI PASS [SYMBUSDT] Reason: PERFECT: 15M(1.03%) symbolPred: null', lg=DET))
    kC = o.get('dca_k', 1)
    s.add(D, L(dtsC + 67000, '[C3-LIVE] SUBMIT SYMBUSDT DCA_LEVEL1 SUBMITTED cid=c3-SYMBUSDT-%d-%d qty=20 budget=%s legIdx=%d '
               'notional=%s U_before=%s' % (bC, kC, o.get('dca_budget', '21.675'), kC, o.get('dca_notional', '21.0'), o.get('dca_u', '0.022'))))
    if o.get('dca_nofill'):
        s.add(D, L(dtsC + 67600, '[C3-LIVE-FILL] leg SYMBUSDT c3-SYMBUSDT-%d-%d ket thuc EXPIRED khong khop => huy giu cho' % (bC, kC), OK, FA, 'WARN'))
    else:
        s.add(D, L(dtsC + 67600, '[C3-LIVE-FILL] xac nhan qua stream SYMBUSDT c3-SYMBUSDT-%d-%d qty=20 avg=1.0505 ref=%s'
                   % (bC, kC, o.get('dca_ref', '1.0500')), OK, FA))
    if o.get('hold_leg0'):
        dtsH = lo + 8 * H
        s.add(D, L(dtsH + 66000, 'Market level change: %s level: BIG_DOWN symbols:500' % P.minute_str(dtsH), lg=DET))
        s.add(D, L(dtsH + 67000, '[C3-LIVE] SUBMIT SYMBUSDT BIG_DOWN SUBMITTED cid=c3-SYMBUSDT-%d-0 qty=10 budget=22.5 legIdx=0 '
                   'notional=22.0 U_before=0.0' % (dtsH // M)))
        s.add(D, L(dtsH + 67600, '[C3-LIVE-FILL] xac nhan qua stream SYMBUSDT c3-SYMBUSDT-%d-0 qty=10 avg=1.05 ref=1.05' % (dtsH // M), OK, FA))
    # ---- tiem them
    if o.get('vi_am'):
        s.add(D, L(lo + 9 * H, '[C3-LIVE] vi the AM (short) SYMBUSDT pa=-1 => KHAN', OK, FA, 'ERROR'))
    if o.get('stop_pre_arm'):
        cidb = 'c3s-SYMBUSDT-%d-1' % ((lo + 10 * H) // M)
        s.add(D, L(lo + 10 * H - 20, '[C3-LIVE-FILL] ALGO_UPDATE SYMBUSDT caid=%s X=NEW ai=' % cidb, OK, FA))
        s.add(D, L(lo + 10 * H, '[C3-LIVE-TRAIL] SYMBUSDT ARM stop=1.0000 cid=%s mode=closePosition (cu=null 0.0)' % cidb, 'C3LIVE-OPS', TSM))
    if o.get('garbage_submit'):
        s.add(D, L(lo + 11 * H, '[C3-LIVE] SUBMIT SYMZUSDT ??? hong dinh dang'))
    if o.get('err_line'):
        s.add(D, L(lo + 12 * H, 'loi gi do signature=abcdef123SIG token 1234567890:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA',
                   'main', 'c.b.c.u.Utils', 'ERROR'))
    if o.get('lech_equity'):
        s.add(D, L(lo + 12 * H, '[C3-LIVE-RECON] LECH EQUITY > 1.0% => CHAN mo moi (tu go khi khop 2 lan lien tiep): equity_so=1234.56 '
                   'tmb=1240.11 lech=0.4500% (moc=1200.77 chot=33.33 phi=1.11 funding=0.22 chuyen=0.00 upl_so=5.55)',
                   'C3LIVE-OPS', 'c.b.c.c.r.Reconciler', 'ERROR'))
        s.add(D, L(lo + 12 * H + 1000, 'tk con BFUSD_WALLET=10000.00094380 eq = C3_CAPITAL + (12.34 + 56.78) so_du=77.77',
                   'main', 'c.b.c.u.Utils', 'ERROR'))
    if o.get('latch_a40'):
        s.add(D, L(lo + 12 * H, '[KILLSW] LATCH action=FLATTEN (truoc NONE) code=A40 codes=[A40] detail=dd | DONG HET',
                   'C3LIVE-OPS', 'c.b.c.o.OpsHooks', 'WARN'))
    if o.get('noflag_line'):
        s.add(D, L(lo + 13 * H, '[TS-EXT] chua co co ngay 20417 sau han (since=30m, start=600m) -> OFF', 'TS-EXT', 'c.b.c.t.s.TsMktExt', 'WARN'))
    restart = None
    if o.get('banner_in_day'):
        restart = lo + 8 * H
        for x in banner(restart, '1000.0'):
            s.add(D, x)
        s.add(D, L(restart + 13000, '[C3-LIVE] khoi phuc sau restart: con 0 leg treo', 'C3LIVE-OPS', 'c.b.c.c.r.C3LiveRuntime', 'WARN'))
        s.add(D, L(restart + 13100, '[C3-LIVE] reconcile khoi dong XONG', 'C3LIVE-OPS', 'c.b.c.c.r.C3LiveRuntime', 'WARN'))
    tt = o.get('tt')
    if o.get('tt_push_off'):
        tt = lambda t: {'push': 'OFF'} if t == lo + 6 * H else None  # noqa: E731
    heartbeat(s, D, flag=(None if o.get('no_flag') else flag), recon_skip=o.get('recon_skip', ()), restart=restart,
              n_off=o.get('n_off'), tt=tt, eq_fn=o.get('eq_fn'), ks_none=o.get('ks_none', False),
              streak_jump=o.get('streak_jump'), tt_drop=o.get('tt_drop'))
    if o.get('tt_stop_after') is not None:
        s.cron = [x for x in s.cron if x[0] < o['tt_stop_after']]
    if o.get('cron_split') is not None:
        s.cron_split = o['cron_split']
        s.no_cron1 = bool(o.get('no_cron1'))
    if o.get('check'):
        s.check[D] = o['check']
    return s


def p26(o=None):
    o = o or {}
    D = dt.date(2026, 11, 26)
    s = Scn(D, D)
    lo = P.day_lo(D)
    for x in banner(lo - 3 * H, '1000.0'):
        s.add(D, x)
    rs = lo + 2 * H + 31 * M       # 09:31
    s.add(D, L(rs, 'MainClass: com.binance.chuyennd.trading.BinanceOrderTradingManager APPDir: ./run', 'main', 'c.b.c.u.Utils'))
    for x in banner(rs + 12000, '5000.0'):
        s.add(D, x)
    s.add(D, L(rs + 25000, '[C3-LIVE] khoi phuc sau restart: con 0 leg treo', 'C3LIVE-OPS', 'c.b.c.c.r.C3LiveRuntime', 'WARN'))
    s.add(D, L(rs + 25100, '[C3-LIVE] reconcile khoi dong XONG', 'C3LIVE-OPS', 'c.b.c.c.r.C3LiveRuntime', 'WARN'))
    dts = lo + 2 * H + 44 * M     # 09:44
    s.sel.setdefault(D, []).append((dts, 'SYMPUSDT', 5))
    s.add(D, L(dts + 67000, '[C3-LIVE] SUBMIT SYMPUSDT PREDICT_SYMBOL_TRADE SUBMITTED cid=c3-SYMPUSDT-%d-0 qty=50 budget=112.5 '
               'legIdx=0 notional=112.0 U_before=0.0' % (dts // M)))
    s.add(D, L(dts + 67500, '[C3-LIVE-FILL] xac nhan qua stream SYMPUSDT c3-SYMPUSDT-%d-0 qty=50 avg=2.24 ref=2.2399' % (dts // M), OK, FA))
    s.iv.append((dts + 67500, P.FAR))
    ps = P.ms_local('2026-11-26 09:20')

    def tt(t):
        if t < ps:
            return None
        if t < rs + 4 * M:
            return {'push': 'OFF', 'C3_CAPITAL': '5000'}
        return {'C3_CAPITAL': '5000'}
    heartbeat(s, D, restart=rs, eq_after=5000.0, tt=tt)
    s.check[D] = {'STATUS': 'INCOMPLETE', 'fails': 'feat_minutes=1430/1440;sel_minutes=1430/1440'}
    return s


def empty(D=dt.date(2026, 11, 25), check=None):
    s = Scn(D, D)
    for x in banner(P.day_lo(D) - 3 * H, '1000.0'):
        s.add(D, x)
    heartbeat(s, D)
    if check:
        s.check[D] = check
    return s


# ------------------------------------------------------------------ chay
class Runner(object):
    def __init__(self, tmp):
        self.tmp = tmp
        self.n = 0
        self.ok = 0
        self.fail = []

    def run(self, name, s, extra=(), out=None, keep=False):
        root = os.path.join(self.tmp, name)
        if os.path.isdir(root) and not keep:
            shutil.rmtree(root)
        os.makedirs(root, exist_ok=True)
        s.write(root)
        out = out or os.path.join(root, 'out')
        cmd = [sys.executable, '-I', TOOL, s.D.isoformat(), '--out-dir', out, '--pull-root', os.path.join(root, 'pull242'),
               '--cron-log', os.path.join(root, 'cron.log'), '--state-start', s.ss.isoformat(), '--now', '%s 12:00' % (s.D + dt.timedelta(days=1))]
        cmd += list(extra)
        if '--now' in extra:
            i = cmd.index('--now')
            del cmd[i:i + 2]
        r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        if r.returncode != 0:
            LOG.error('%s: tool rc=%d %s', name, r.returncode, r.stderr[-1500:])
            return None, None
        stem = os.path.join(out, 'D_%s' % s.D.strftime('%Y%m%d'))
        with open(stem + '.json') as fh:
            j = json.load(fh)
        with open(stem + '.md') as fh:
            md = fh.read()
        return j, md

    def check(self, name, cond, msg=''):
        self.n += 1
        if cond:
            self.ok += 1
            LOG.info('PASS %s', name)
        else:
            self.fail.append(name)
            LOG.error('FAIL %s %s', name, msg)


def st(j, k):
    return j['muc'][k]['trang_thai'] if j else None


def leak(j, md):
    blob = json.dumps(j) + (md or '')
    bad = [x for x in LEAK_TOK if x in blob]
    m = LEAK_RX.search(blob)
    if m:
        bad.append(m.group(0))
    return bad


def main():
    logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s', stream=sys.stderr)
    tmp = sys.argv[1]
    R = Runner(tmp)
    lo = P.day_lo(dt.date(2026, 11, 25))
    # neo that: SL BLESS / JCT 21/11 (A1 da tinh lai)
    pk = P.f32((P.f32(0.014932) - P.f32(0.013952)) / P.f32(0.013952))
    R.check('neo_I9b_BLESS_21_11', P.trail_sl(0.013952, pk) == P.f32(0.014510079))
    pk = P.f32((P.f32(0.001597) - P.f32(0.001462)) / P.f32(0.001462))
    R.check('neo_I9b_JCT_21_11', P.trail_sl(0.001462, pk) == P.f32(0.0015497198))
    items = ['M-E0', 'I3', 'I4', 'I8', 'I9', 'I10', 'I11', 'I12', 'M-T', 'D1', 'M-S', 'M-X', 'K1', 'K2', 'K3', 'K4', 'K5', 'K6']
    # (a) sach
    j, md = R.run('clean', clean())
    for k in items:
        R.check('a_sach_%s_DAT' % k, st(j, k) == 'DAT', '%s=%s %s' % (k, st(j, k), j and json.dumps(j['muc'][k])[:400]))
    R.check('a_sach_bac_XANH', j and j['bac'] == 'XANH', j and j['bac'])
    R.check('a_dong_dau_md', md is not None and re.match(r'^PILOT-M D=2026-11-25 cham_luc=\S+ bac=XANH prereg=2a21fe35\+E1\+E2 cong_cu=[0-9a-f]{12}\n', md) is not None)
    R.check('a_ALGO_NEW_truoc_STOP_20ms_DAT', st(j, 'I4') == 'DAT')
    R.check('a_BIG_DOWN_leg0_ME0_DAT', st(j, 'M-E0') == 'DAT' and j['muc']['M-E0']['mau'] == 3)
    R.check('a_defer_so_giay_bo_qua_MT_DAT', st(j, 'M-T') == 'DAT' and j['muc']['M-T']['mau'] == 1)
    R.check('a_D1_ghi_15M', j and j['muc']['D1']['mo_ta']['gia_tri_15M_leg_DCA'][0]['x_15M_pct'] == 1.03)
    R.check('a_MS_S5_S6_KCD_CAU_TRUC', j and 'KCD_CAU_TRUC' in j['muc']['M-S']['mo_ta']['S5_S6'])
    # (b) tiem: (ten, tuy chon, muc, trang thai ky vong, bac muc ky vong | None, tham so them, chi_1_muc)
    S7 = {'dca_budget': '2.0', 'dca_u': '0.5466666667', 'dca_notional': '1.9'}
    inj = [
        ('ME0_tre', {'me0_late': 1}, 'M-E0', 'VI_PHAM', 'VANG', [], True),
        ('ME0_BIG_DOWN_thieu_Market_level', {'no_bigdown': 1}, 'M-E0', 'VI_PHAM', 'VANG', [], True),
        ('ME0c_leg0_khi_dang_giu', {'hold_leg0': 1}, 'M-E0', 'VI_PHAM', 'VANG', [], False),
        ('I3_move_nho', {'i3_small': 1}, 'I3', 'VI_PHAM', 'DO', [], False),
        ('I4a_STOP_ARM_sau_61s', {'stop_arm_late': 1}, 'I4', 'VI_PHAM', 'DO', [], True),
        ('I4b_ALGO_NEW_sau_61s', {'algo_new_late': 1}, 'I4', 'VI_PHAM', 'DO', [], True),
        ('I4b_thieu_ALGO_NEW', {'no_algo_new': 1}, 'I4', 'VI_PHAM', 'DO', [], True),
        ('I4c_thieu_CANCELED_stop_cu', {'no_cancel_old': 1}, 'I4', 'VI_PHAM', 'DO', [], True),
        ('I4d_khong_TRIGGER', {'trig': 'none'}, 'I4', 'VI_PHAM', 'DO', [], True),
        ('I4d_TRIGGERED_sau_70s', {'trig': 'late'}, 'I4', 'VI_PHAM', 'DO', [], True),
        ('E3_I4d_chi_TRIGGERED_sau_CLOS_1ms', {'trig': 'only_triggered'}, 'I4', 'DAT', None, [], True),
        ('I8_stop_truoc_arm', {'stop_pre_arm': 1}, 'I8', 'VI_PHAM', 'DO', [], True),
        ('I8_SFIL_truoc_arm', {'sfil_pre_arm': 1}, 'I8', 'VI_PHAM', 'DO', [], True),
        ('I9_SL_sai', {'bad_sl': 1}, 'I9', 'VI_PHAM', 'DO', [], True),
        ('I9_arm_2_lan', {'dup_arm': 1}, 'I9', 'VI_PHAM', 'DO', [], False),
        ('I10_STOP_LOST_61S', {'clos_reason': 'STOP_LOST_61S'}, 'I10', 'VI_PHAM', 'DO', [], True),
        ('I10_BOOK_ly_do_khac_CLOS', {'book_reason': 'TIME_STOP_168H'}, 'I10', 'VI_PHAM', 'DO', [], True),
        ('B1_dong_cum_khong_CLOS', {'b1': 1}, 'I10', 'VI_PHAM', 'DO', [], True),
        ('B2_CLOS_bi_cat', {'b2': 1}, 'I10', 'KHONG_CHAM_DUOC', None, [], False),
        ('B12_SFIL_du_qty_khong_CLOS', {'b12': 1}, 'I10', 'VI_PHAM', 'DO', [], True),
        ('I11a_n_sai', {'n_off': 4}, 'I11', 'VI_PHAM', 'DO', [], True),
        ('I11b_leo_thang', {'leo_thang': 1}, 'I11', 'VI_PHAM', 'DO', [], False),
        ('I12c_vi_the_am', {'vi_am': 1}, 'I12', 'VI_PHAM', 'DO', [], False),
        ('I12d_tong_SFIL', {'sfil_extra': 1}, 'I12', 'VI_PHAM', 'DO', [], True),
        ('MT_TS_muon', {'mt_late': 1}, 'M-T', 'VI_PHAM', 'DO', [], True),
        ('MT_TS_som_hon_due', {'mt_early': 1}, 'M-T', 'VI_PHAM', 'DO', [], True),
        ('MT_khong_CLOS', {'mt_no_clos': 1}, 'M-T', 'VI_PHAM', 'DO', [], True),
        ('MT_flag_ON_chi_defer_so_giay', {'flag': 'ON'}, 'M-T', 'VI_PHAM', 'DO', [], True),
        ('MT_flag_ON_defer_C3LIVE_OPS', {'flag': 'ON', 'mt_ops_defer': 1}, 'M-T', 'DAT', None, [], True),
        ('E13_MT_flag_NA_la_OFF', {'flag': 'NA'}, 'M-T', 'DAT', None, [], False),
        ('E7_MT_arm_roi_RST_van_time_stop', {'mt_arm_rst': 1}, 'M-T', 'DAT', None, [], True),
        ('E7_MT_arm_khong_RST_khong_cham', {'mt_arm_only': 1}, 'M-T', 'KHONG_CO_SU_KIEN', None, [], True),
        ('D1a_level', {'dca_ref': '1.5'}, 'D1', 'VI_PHAM', 'DO', [], True),
        ('D1e_thieu_AI_PASS', {'no_aipass': 1}, 'D1', 'VI_PHAM', 'DO', [], True),
        ('E8_D1_leg_DCA_khong_khop', {'dca_nofill': 1}, 'D1', 'DAT', None, [], True),
        ('S1_r_cap_1_0_DAT', {'sa_budget': '22.5'}, 'M-S', 'DAT', None, [], True),
        ('S1b_r_cap_1_01_VANG', {'sa_budget': '22.725'}, 'M-S', 'VI_PHAM', 'VANG', [], True),
        ('S1b_r_cap_1_1_kem_S2_DO', {'sa_budget': '24.75'}, 'M-S', 'VI_PHAM', 'DO', [], True),
        ('S1b_r_cap_1_2_VANG', {'sa_budget': '27.0'}, 'M-S', 'VI_PHAM', 'VANG', [], True),
        ('S1_r_cap_1_21_DO', {'sa_budget': '27.225'}, 'M-S', 'VI_PHAM', 'DO', [], True),
        ('S2_r_hi', {'eq_fn': lambda i: 980.0 if i in (1, 2) else None}, 'M-S', 'VI_PHAM', 'DO', [], True),
        ('S3_EQ_DUOI', {'sa_budget': '20.25', 'sa_notional': '20.2'}, 'M-S', 'VI_PHAM', 'VANG', [], True),
        ('S3_AVAIL', {'sa_budget': '20.25', 'sa_notional': '20.2', 'eqwarn': 1}, 'M-S', 'VI_PHAM', 'VANG', [], True),
        ('S2_TIER', {'eq_fn': lambda i: 833.33 if i in (7, 8) else None}, 'M-S', 'VI_PHAM', 'VANG', [], True),
        ('S4_notional', {'sa_notional': '22.6'}, 'M-S', 'VI_PHAM', 'DO', [], True),
        ('S7_budget_nho', S7, 'M-S', 'VI_PHAM', 'DO', [], True),
        ('S8_legIdx', {'dca_k': 2}, 'M-S', 'VI_PHAM', 'DO', [], False),
        ('S9_U_0_6', {'dca_u': '0.6'}, 'M-S', 'VI_PHAM', 'DO', [], True),
        ('S1b_DCA_tierMul_1_2_VANG', {'dca_budget': '26.01'}, 'M-S', 'VI_PHAM', 'VANG', [], True),
        ('S2S3_khong_HOURLY_cung_JVM', {'ks_none': 1}, 'M-S', 'KHONG_CHAM_DUOC', None, [], True),
        ('MS_budget_lon', {'dca_budget': '25.0'}, 'M-S', 'VI_PHAM', 'DO', [], True),
        ('MX_truot_vao', {'mx_slip': 1}, 'M-X', 'VI_PHAM', 'VANG', [], True),
        ('K1_restart', {'banner_in_day': 1}, 'K1', 'VI_PHAM', 'VANG', [], True),
        ('K2_push_OFF_dong_hop_le', {'tt_push_off': 1}, 'K2', 'VI_PHAM', 'VANG', [], True),
        ('E2_K2_1_luot_doc_hong_DAT', {'tt': lambda t: {'_invalid': 1} if t == lo + 6 * H else None}, 'K2', 'DAT', None, [], True),
        ('E2_K2_2_luot_doc_hong_lien_tiep_DAT', {'tt': lambda t: {'_invalid': 1} if lo + 6 * H <= t <= lo + 6 * H + 2 * M else None},
         'K2', 'DAT', None, [], True),
        ('E2_K2_doc_hong_12_phut_khoang_trong', {'tt': lambda t: {'_invalid': 1} if lo + 6 * H <= t <= lo + 6 * H + 10 * M else None},
         'K2', 'VI_PHAM', 'VANG', [], True),
        ('K2_khoang_trong_20_phut', {'tt_drop': (lo + 6 * H, lo + 6 * H + 20 * M)}, 'K2', 'VI_PHAM', 'VANG', [], True),
        ('B10_monitor_chet_tu_15h', {'tt_stop_after': lo + 8 * H}, 'K2', 'VI_PHAM', 'VANG', [], True),
        ('B11_cron_xoay_doc_log1_DAT', {'cron_split': lo + 8 * H}, 'K2', 'DAT', None, [], True),
        ('B11_cron_xoay_thieu_log1', {'cron_split': lo + 8 * H, 'no_cron1': 1}, 'K2', 'VI_PHAM', 'VANG', [], True),
        ('K3_thieu_RECON', {'recon_skip': (14, 15, 16)}, 'K3', 'VI_PHAM', 'DO', [], True),
        ('K3_streak_nhay', {'streak_jump': 10}, 'K3', 'VI_PHAM', 'DO', [], True),
        ('K4_thieu_flag', {'no_flag': 1}, 'K4', 'VI_PHAM', 'VANG', [], True),
        ('K4_chua_co_co_ngay', {'noflag_line': 1}, 'K4', 'VI_PHAM', 'VANG', [], True),
        ('K5_STATUS', {'check': {'STATUS': 'INCOMPLETE', 'fails': 'feat_minutes=1300/1440'}}, 'K5', 'VI_PHAM', 'VANG', [], True),
        ('K5_log_minutes', {'check': {'log_minutes': '1430'}}, 'K5', 'VI_PHAM', 'VANG', [], True),
        ('K6_ERROR_sig_token', {'err_line': 1}, 'K6', 'VI_PHAM', 'VANG', [], True),
        ('K6_LECH_EQUITY_WALLET_san', {'lech_equity': 1}, 'K6', 'VI_PHAM', 'VANG', [], True),
        ('K6_LATCH_A40', {'latch_a40': 1}, 'K6', 'VI_PHAM', 'DO', [], True),
        ('E9_dong_TRAIL_bi_cat', {'trail_trunc': 1}, 'I3', 'KHONG_CHAM_DUOC', None, [], False),
        ('E9_dong_SUBMIT_hong', {'garbage_submit': 1}, 'M-E0', 'KHONG_CHAM_DUOC', None, [], False),
        ('E4_DELIST_khong_ghi_chep', {'delist': 1}, 'I10', 'VI_PHAM', 'DO', [], False),
        ('E4_DELIST_co_ghi_chep', {'delist': 1}, 'I10', 'DAT', None, ['--delist-noted', 'SYMBUSDT'], True),
    ]
    for name, o, item, exp, bac, extra, only in inj:
        j, md = R.run('b_' + name, clean(o), extra)
        R.check('b_%s_%s_%s' % (name, item, exp), st(j, item) == exp, j and json.dumps(j['muc'][item])[:700])
        if bac:
            R.check('b_%s_bac_%s' % (name, bac), j is not None and j['bac_muc'].get(item) == bac and (j['bac'] == bac or not only),
                    j and (j['bac_muc'].get(item), j['bac']))
        if j and only:
            others = [kk for kk in items if kk != item and st(j, kk) not in ('DAT', 'KHONG_CO_SU_KIEN')]
            R.check('b_%s_chi_muc_%s' % (name, item), not others, [(kk, st(j, kk)) for kk in others])
        R.check('b_%s_khong_ro_tien' % name, j is not None and not leak(j, md), j and leak(j, md))
        if name == 'E4_DELIST_khong_ghi_chep':
            R.check('E4_DELIST_khong_ghi_chep_I8_VI_PHAM', st(j, 'I8') == 'VI_PHAM')
        if name == 'E4_DELIST_co_ghi_chep':
            R.check('E4_DELIST_co_ghi_chep_I8_DAT', st(j, 'I8') == 'DAT')
        if name in ('S3_EQ_DUOI', 'S3_AVAIL', 'S2_TIER'):
            tag = {'S3_EQ_DUOI': 'EQ_DUOI', 'S3_AVAIL': 'AVAIL', 'S2_TIER': 'TIER'}[name]
            R.check('%s_nhan_%s' % (name, tag), j and tag in j['muc']['M-S'].get('nhan', []), j and j['muc']['M-S'].get('nhan'))
        if name.startswith('S1b') and j:
            R.check('%s_nhan_TIER_S1b' % name, 'TIER' in j['muc']['M-S'].get('nhan', [])
                    and any('(S1b)' in v['ly_do'] for v in j['muc']['M-S']['su_kien_vi_pham']), j['muc']['M-S'])
        if name == 'S1b_r_cap_1_1_kem_S2_DO' and j:
            R.check('S1b_1_1_co_S2', any('(S2)' in v['ly_do'] for v in j['muc']['M-S']['su_kien_vi_pham']))
        if name.startswith('S') and name[1].isdigit() and 'b' not in name.split('_')[0] and j and exp == 'VI_PHAM' and bac == 'DO':
            code = '(' + name.split('_')[0] + ')'
            R.check('%s_ly_do_%s' % (name, code), any(code in v['ly_do'] for v in j['muc']['M-S']['su_kien_vi_pham']),
                    [v['ly_do'] for v in j['muc']['M-S']['su_kien_vi_pham']])
        if name == 'E2_K2_1_luot_doc_hong_DAT':
            R.check('E2_dem_luot_doc_hong', j and j['muc']['K2']['mo_ta']['so_luot_doc_hong'] == 1)
    # (c) ngay rong
    j, _ = R.run('c_rong', empty())
    for kk in ['M-E0', 'I3', 'I4', 'I8', 'I9', 'I10', 'I11', 'I12', 'M-T', 'D1', 'M-S', 'M-X']:
        R.check('c_rong_%s_KCSK' % kk, st(j, kk) == 'KHONG_CO_SU_KIEN', st(j, kk))
    R.check('c_rong_K_DAT', all(st(j, kk) == 'DAT' for kk in ('K1', 'K2', 'K3', 'K4', 'K5', 'K6')),
            [(kk, st(j, kk)) for kk in ('K1', 'K2', 'K3', 'K4', 'K5', 'K6')])
    # (d) thieu du lieu
    s = empty()
    s.nopull.add(s.D)
    j, _ = R.run('d_thieu_pull', s)
    R.check('d_thieu_pull_KCD', all(st(j, kk) == 'KHONG_CHAM_DUOC' for kk in items if kk != 'K2'), [(kk, st(j, kk)) for kk in items])
    R.check('d_thieu_pull_K2_van_cham', st(j, 'K2') == 'DAT')
    R.check('d_thieu_pull_bac_XANH_truoc_D3', j and j['bac'] == 'XANH')
    s = empty()
    s.nopull.add(s.D)
    j, _ = R.run('d_thieu_pull_qua_D3', s, ['--now', '2026-11-28 09:01'])
    R.check('d_thieu_pull_qua_D3_VANG', j and j['bac'] == 'VANG' and j['bac_muc']['M-E0'] == 'VANG')
    s = empty()
    s.complete[s.D] = False
    j, _ = R.run('d_thieu_COMPLETE', s)
    R.check('d_thieu_COMPLETE_KCD', all(st(j, kk) == 'KHONG_CHAM_DUOC' for kk in items if kk != 'K2'))
    s = empty()
    s.no_cron = True
    j, _ = R.run('d_thieu_cron', s)
    R.check('d_thieu_cron_K2_KCD', st(j, 'K2') == 'KHONG_CHAM_DUOC')
    s = clean()
    s.nopull.add(s.D - dt.timedelta(days=3))
    j, _ = R.run('d_thieu_pull_ngay_truoc', s)
    R.check('d_thieu_pull_ngay_truoc_trang_thai_KCD', st(j, 'I10') == 'KHONG_CHAM_DUOC' and st(j, 'M-T') == 'KHONG_CHAM_DUOC'
            and st(j, 'K5') == 'DAT')
    # ngay 26/11
    j, _ = R.run('p26_ok', p26(), ['--pilot-on-start', '2026-11-26 09:20'])
    for kk in ('K1', 'K2', 'K5', 'K3', 'M-S', 'M-E0'):
        R.check('p26_%s_DAT' % kk, st(j, kk) == 'DAT', '%s %s' % (st(j, kk), j and json.dumps(j['muc'][kk])[:500]))
    j, _ = R.run('p26_thieu_tham_so', p26())
    R.check('p26_thieu_pilot_on_K2_K1_KCD', st(j, 'K2') == 'KHONG_CHAM_DUOC' and st(j, 'K1') == 'KHONG_CHAM_DUOC')
    j, _ = R.run('p26_restart_ngoai_khung', p26(), ['--pilot-on-start', '2026-11-26 12:00'])
    R.check('p26_restart_ngoai_khung_K1_VI_PHAM', st(j, 'K1') == 'VI_PHAM')
    j, _ = R.run('p26_restart_61_phut_sau_pilot_on', p26(), ['--pilot-on-start', '2026-11-26 08:30'])
    R.check('E12_K1_khung_60_phut', st(j, 'K1') == 'VI_PHAM')
    # 2 ngay VANG lien tiep cung muc
    D0 = dt.date(2026, 11, 25)
    bad = {'STATUS': 'INCOMPLETE', 'fails': 'x=1'}
    s1 = empty(D0 - dt.timedelta(days=1), bad)
    s2 = empty(D0, bad)
    s2.ss = D0 - dt.timedelta(days=1)
    s2.logs.update(s1.logs)
    s2.check.update(s1.check)
    s2.cron = s1.cron + s2.cron
    out2 = os.path.join(tmp, 'vang2', 'out')
    R.run('vang2', s1, out=out2)
    j, _ = R.run('vang2', s2, out=out2, keep=True)
    R.check('hai_ngay_VANG_K5', j and 'K5' in j['hai_ngay_vang_lien_tiep_cung_muc'], j and j['hai_ngay_vang_lien_tiep_cung_muc'])
    # san() truc tiep
    for line in ('[C3-LIVE-RECON] LECH EQUITY > 1.0% => CHAN: equity_so=1234.56 tmb=1240.11 lech=0.45% (moc=1200.77 chot=33.33 '
                 'phi=1.11 funding=0.22 chuyen=0.00 upl_so=5.55)', '== tk con: BFUSD_WALLET=10000.00094380 so_du=77.77 dinh=88.88',
                 'x eq = C3_CAPITAL + (12.34 + 56.78) y'):
        out = P.san(line)
        R.check('san_%s' % line[:20].replace(' ', '_'), not any(x in out for x in ('1234.56', '1240.11', '1200.77', '33.33', '5.55',
                                                                                 '10000.00094380', '77.77', '88.88', '12.34', '0.22')), out)
    # chan ghi chinh thuc
    r = subprocess.run([sys.executable, '-I', TOOL, '2026-11-25', '--out-dir', P.OFFICIAL_DIR], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    R.check('official_dir_khong_co_co_official_bi_chan', r.returncode == 2)
    r = subprocess.run([sys.executable, '-I', TOOL, '2026-11-25', '--official', '--max-ts', '2026-11-24 07:00'],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    R.check('official_cung_max_ts_bi_chan', r.returncode == 2)
    # F1: kiem ham chan gio bang gio TIEM (chi trong test, khong chay --official that)
    R.check('F1_moc_0710', P.official_time_ok(dt.date(2026, 11, 24), P.ms_local('2026-11-25 07:10'))
            and not P.official_time_ok(dt.date(2026, 11, 24), P.ms_local('2026-11-25 07:09')))
    src = open(TOOL).read()
    R.check('F1_main_goi_chan_gio', "if not official_time_ok(dt.date.fromisoformat(args.date), int(time.time() * 1000)):" in src)
    LOG.info('KET QUA %d/%d', R.ok, R.n)
    if R.fail:
        LOG.error('FAIL: %s', ', '.join(R.fail))
    return 0 if not R.fail else 1


if __name__ == '__main__':
    sys.exit(main())
