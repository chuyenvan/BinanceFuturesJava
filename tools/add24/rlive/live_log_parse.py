#!/usr/bin/env python3
"""ADD24 R-LIVE: parser log live (pull242/<D>/logs/full.log@*.gz; log CONG DON - bo trung theo nguyen dong).
Che do:
  --mode format : CHI dem (P1 cho phep truoc khi owner duyet): moi loai dong -> so dong co tag (grep doc lap) vs so dong regex
                  doc duoc; KHONG ghi gia tri, KHONG in dong. Ghi counts.json.
  --mode full   : (can P1: ADD24_P1_APPROVED, tru khi cua so ket thuc <= 2026-11-15 = du lieu fixture 11-05/10-30 da dung)
                  ghi submits.csv, fills.csv, trail.csv, e4130.csv, block.csv (tiem rig), jvm.csv, skips.csv, rejects.csv,
                  equnavail.csv, gaps.csv + counts.json (V4).
Moc phut: decision_ts = barMin trong cid * 60000 (cid c3-SYM-<barMin>-<leg>); dong MINUTE-* "phut=YYYYMMDD HH:MM" (+07) = phut quyet dinh
(CHUA XAC MINH tren log co SUBMIT cung phut - xem ERRATA_PROPOSED_A).
usage: live_log_parse.py --days 2026-11-19,2026-11-20 --start "2026-11-19 09:31" --end "2026-11-24 07:00" --out DIR --mode format|full
"""
import argparse, csv, glob, gzip, json, logging, os, re, sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from p1_gate import require_p1

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger('llp')
TZ7 = timezone(timedelta(hours=7))
PULL = os.path.expanduser('~/claude_master/pull242')
TS = re.compile(r'^(\d\d/\d\d/\d{4} \d\d:\d\d:\d\d)\.(\d{3}) ')
# (ten, tag dem doc lap (chuoi con), regex)
RX = [
    ('SUBMIT', '[C3-LIVE] SUBMIT ', re.compile(r'\[C3-LIVE\] SUBMIT (\S+) (\S+) (\S+) cid=(\S+) qty=(\S+) budget=(\S+)'
                                             r'(?: legIdx=(\d+))?(?: notional=(\S+))?(?: U_before=(\S+))?')),
    ('FILL_STREAM', '[C3-LIVE-FILL] xac nhan', re.compile(r'\[C3-LIVE-FILL\] xac nhan qua (\S+) (\S+) (\S+) qty=(\S+) avg=(\S+)(?: ref=(\S+))?')),
    ('FILL_STOP', 'stop khop', re.compile(r'\[C3-LIVE-FILL\] (\S+) stop khop (\S+)@(\S+) \(stop=(\S+) truot=(\S+)\)')),
    ('ALGO', '[C3-LIVE-FILL] ALGO_UPDATE', re.compile(r'\[C3-LIVE-FILL\] ALGO_UPDATE (\S+) caid=(\S+) X=(\S+)')),
    ('TRAIL_arm', '[C3-LIVE-TRAIL] arm ', re.compile(r'\[C3-LIVE-TRAIL\] arm (\S+) entry=(\S+) px=(\S+) peak=(\S+) SL=(\S+)')),
    ('TRAIL_STOP', ' stop=', re.compile(r'\[C3-LIVE-TRAIL\] (\S+) (ARM|MOVE) stop=(\S+) cid=(\S+) mode=(\S+)')),
    ('TRAIL_4130', 'san tu choi stop closePosition', re.compile(r'\[C3-LIVE-TRAIL\] (\S+) san tu choi stop closePosition')),
    ('TIME_STOP', '[C3-LIVE-TRAIL] TIME-STOP', re.compile(r'\[C3-LIVE-TRAIL\] TIME-STOP (\S+) entry=(\S+) px=(\S+) gio_giu=(\d+)')),
    ('ORDER_4130', '[C3-LIVE-ORDER]', re.compile(r'\[C3-LIVE-ORDER\] .*?cid=(\S+) .*?sym=(\S+) .*?status=ERROR .*?err=\S*-4130')),
    ('INC_MIN', '[MINUTE-INCOMPLETE] phut=', re.compile(r'\[MINUTE-INCOMPLETE\] phut=(\d{8} \d\d:\d\d) .*?ly_do=(\S+)')),
    ('INC_LEG', '[MINUTE-INCOMPLETE] chan lenh moi', re.compile(r'\[MINUTE-INCOMPLETE\] chan lenh moi (\S+) (\S+) \(phut (\d{8} \d\d:\d\d)')),
    ('FIN_EXCL', '[MINUTE-FIN-EXCL]', re.compile(r'\[MINUTE-FIN-EXCL\] chan leg (\S+) (\S+) \(phut (\d{8} \d\d:\d\d)')),
    ('JVM_START', 'MainClass: com.binance.chuyennd.trading.BinanceOrderTradingManager', re.compile(r'MainClass: (\S+)')),
    ('SKIP_PAPER', 'skipFull', re.compile(r'(skipFull|liveBookFull|U_MAX)\S*.*?([A-Z0-9]{2,}USDT)')),
    ('SKIP_PAPER2', 'liveBookFull', re.compile(r'(liveBookFull).*?([A-Z0-9]{2,}USDT)')),
    ('REJECT', 'REJECT', re.compile(r'(REJECT\S*).*?([A-Z0-9]{2,}USDT)')),
    ('EXPIRED', 'EXPIRED', re.compile(r'(EXPIRED).*?([A-Z0-9]{2,}USDT)')),
    ('TUCHOI_CID', 'tu choi cid=', re.compile(r'tu choi cid=(\S+)')),
    ('EQ_UNAVAIL', '[C3-LIVE-EQ] positions() loi', re.compile(r'\[C3-LIVE-EQ\] positions\(\) loi')),
    ('KHAN', 'KHAN', re.compile(r'KHAN')),
    ('FUNDING', '[C3-LIVE-EQ] funding c3', re.compile(r'\[C3-LIVE-EQ\] funding c3 (\S+) \((\d+) dong\) => cong don (\S+)')),
    ('KS_LATCH', 'LATCH', re.compile(r'\[KILLSW\].*LATCH')),
]


def ms7(s, fmt):
    return int(datetime.strptime(s, fmt).replace(tzinfo=TZ7).timestamp() * 1000)


def lines(days):
    files = sorted(set(sum([glob.glob(PULL + '/%s/logs/full.log@*.gz' % d) for d in days], [])))
    seen = set()
    for f in files:
        with gzip.open(f, 'rt', errors='replace') as fh:
            for ln in fh:
                if ln in seen:
                    continue
                seen.add(ln)
                yield f, ln
    log.info('files=%d unique_lines=%d', len(files), len(seen))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--days', required=True); ap.add_argument('--start', required=True); ap.add_argument('--end', required=True)
    ap.add_argument('--out', required=True); ap.add_argument('--mode', choices=['format', 'full'], required=True)
    a = ap.parse_args()
    S, E = ms7(a.start, '%Y-%m-%d %H:%M'), ms7(a.end, '%Y-%m-%d %H:%M')
    if a.mode == 'full' and E > ms7('2026-11-15 07:00', '%Y-%m-%d %H:%M'):
        log.info('P1: %s', require_p1())
    os.makedirs(a.out, exist_ok=True)
    days = a.days.split(',')
    cnt = {n: {'tag_lines': 0, 'parsed': 0} for n, _, _ in RX}
    rows = {n: [] for n, _, _ in RX}
    minutes_seen = set()
    for f, ln in lines(days):
        m = TS.match(ln)
        if not m:
            continue
        t = ms7(m.group(1), '%d/%m/%Y %H:%M:%S') + int(m.group(2))
        if t < S or t >= E:
            continue
        minutes_seen.add(t // 60000)
        for n, tag, rx in RX:
            if tag in ln:
                cnt[n]['tag_lines'] += 1
                g = rx.search(ln)
                if g:
                    cnt[n]['parsed'] += 1
                    if a.mode == 'full':
                        rows[n].append([t] + [x if x is not None else '' for x in g.groups()] + [os.path.basename(f)])
    nmin = (E - S) // 60000
    gaps = [mn * 60000 for mn in range(S // 60000, E // 60000) if mn not in minutes_seen]
    res = {'mode': a.mode, 'days': days, 'start': S, 'end': E, 'counts': cnt, 'minutes_window': nmin,
           'minutes_without_any_log_line': len(gaps),
           'parse_rate_ok': {n: (c['tag_lines'] == c['parsed']) for n, c in cnt.items()}}
    if a.mode == 'full':
        hdr = {'SUBMIT': 'log_ms,symbol,level,outcome,cid,qty,budget,legIdx,notional,U_before,file',
               'FILL_STREAM': 'log_ms,via,symbol,cid,qty,avg,ref,file', 'FILL_STOP': 'log_ms,symbol,qty,px,stop,slip,file',
               'ALGO': 'log_ms,symbol,caid,X,file', 'TRAIL_arm': 'log_ms,symbol,entry,px,peak,SL,file',
               'TRAIL_STOP': 'log_ms,symbol,act,stop,cid,mode,file', 'TRAIL_4130': 'log_ms,symbol,file',
               'TIME_STOP': 'log_ms,symbol,entry,px,hours,file', 'ORDER_4130': 'log_ms,cid,symbol,file',
               'INC_MIN': 'log_ms,phut,ly_do,file', 'INC_LEG': 'log_ms,level,symbol,phut,file', 'FIN_EXCL': 'log_ms,level,symbol,phut,file',
               'JVM_START': 'log_ms,main,file'}
        for n, r in rows.items():
            with open(os.path.join(a.out, n.lower() + '.csv'), 'w') as fh:
                fh.write(hdr.get(n, 'log_ms,' + ','.join('g%d' % i for i in range(1, 1 + max([len(x) - 2 for x in r] or [0]))) + ',file') + '\n')
                csv.writer(fh, lineterminator='\n').writerows(r)
        # block.csv cho rig (tiem MINUTE-*): decision_ts,symbol,level,kind
        blk = set()
        for r in rows['INC_MIN']:
            blk.add((ms7(r[1], '%Y%m%d %H:%M'), '*', '*', 'MINUTE-INCOMPLETE'))
        for r in rows['INC_LEG']:
            blk.add((ms7(r[3], '%Y%m%d %H:%M'), r[2], r[1], 'MINUTE-INCOMPLETE-LEG'))
        for r in rows['FIN_EXCL']:
            blk.add((ms7(r[3], '%Y%m%d %H:%M'), r[2], r[1], 'MINUTE-FIN-EXCL'))
        with open(os.path.join(a.out, 'block.csv'), 'w') as fh:
            fh.write('decision_ts,symbol,level,kind\n')
            csv.writer(fh, lineterminator='\n').writerows(sorted(blk))
        with open(os.path.join(a.out, 'gaps.csv'), 'w') as fh:
            fh.write('minute_ms\n' + ''.join('%d\n' % g for g in gaps))
        res['submits_unique_cid'] = len({r[4] for r in rows['SUBMIT']})
        res['block_rows'] = len(blk)
    json.dump(res, open(os.path.join(a.out, 'counts.json'), 'w'), indent=1)
    print(json.dumps({'counts': {k: v for k, v in cnt.items() if v['tag_lines']}, 'gaps': len(gaps), 'minutes': nmin}, indent=0))


if __name__ == '__main__':
    main()
