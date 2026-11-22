#!/usr/bin/env python3
"""ADD24 R-LIVE: parser log live (pull242/<D>/logs/full.log@*.gz; log CONG DON - bo trung theo nguyen dong).
Quy tac = dinh dang LOG trong ma nguon jar 76134a52 (file:dong ghi canh moi quy tac). Moi dong co '[C3-LIVE' KHONG khop quy tac nao
=> dem theo tag + dang rut gon (so -> 9, symbol -> SYM) vao unmatched (ERRATA3 A5 / V4b).
Che do:
  --mode format : CHI dem (P1): moi quy tac -> tag_lines (dong chua MOI chuoi tag) va parsed (regex doc duoc); unmatched; KHONG ghi gia tri.
  --mode full   : (can P1 tru khi cua so ket thuc <= 2026-11-15 hoac --log-files test) ghi CSV moi quy tac + block.csv + tick.csv + counts.json.
Moc phut: decision_ts = barMin cid x 60000; "phut=" cua MINUTE-* = dts (+07) (ERRATA1 E-A10 / ERRATA2 s4).
usage: live_log_parse.py --days D1,D2 | --log-files f1.gz,f2 --start "YYYY-MM-DD HH:MM" --end "..." --out DIR --mode format|full [--dump-rules]
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
P = r'(\d{8} \d\d:\d\d)'
# (ten, tag = tuple chuoi con PHAI co het, regex, header csv, nguon code 76134a52)
RULES = [
    ('SUBMIT', ('[C3-LIVE] SUBMIT ',), r'\[C3-LIVE\] SUBMIT (\S+) (\S+) (\S+) cid=(\S+) qty=(\S+) budget=(\S+)(?: legIdx=(\d+))?(?: notional=(\S+))?(?: U_before=(\S+))?',
     'symbol,level,outcome,cid,qty,budget,legIdx,notional,U_before', 'C3LiveEntry SUBMIT'),
    ('KHONG_VAO', ('[C3-LIVE] KHONG vao lenh ',), r'\[C3-LIVE\] KHONG vao lenh (\S+) (\S+) (\S+)', 'symbol,level,outcome', 'C3LiveEntry:316'),
    ('SKIP', ('[C3-LIVE] skip ',), r'\[C3-LIVE\] skip (\S+) (\S+) (\S+)', 'symbol,level,outcome', 'C3LiveEntry:320'),
    ('FILL_STREAM', ('[C3-LIVE-FILL] xac nhan',), r'\[C3-LIVE-FILL\] xac nhan qua (\S+) (\S+) (\S+) qty=(\S+) avg=(\S+)(?: ref=(\S+))?',
     'via,symbol,cid,qty,avg,ref', 'FillAccounting:202'),
    ('FILL_REST', ('[C3-LIVE-FILL]', 'ghi qua REST'), r'\[C3-LIVE-FILL\] (\S+) khop vao t=(\S+) phi (\S+) USD ghi qua REST', 'symbol,tradeId,fee', 'FillAccounting:618'),
    ('EXEC_BU_PHI', ('[C3-LIVE-EXEC]', 'bu phi'), r'\[C3-LIVE-EXEC\] (\S+) (\S+) bu phi (\S+) khop qua userTrades', 'symbol,cid,n', 'C3LiveOrderExecutor:219'),
    ('EXEC_KHONG_KHOP', ('[C3-LIVE-EXEC]', 'KHONG khop'), r'\[C3-LIVE-EXEC\] (\S+) (\S+) KHONG khop \((\S+)', 'symbol,cid,kind', 'C3LiveOrderExecutor:304'),
    ('LEG_KHONG_KHOP', ('[C3-LIVE-FILL] leg ', 'khong khop'), r'\[C3-LIVE-FILL\] leg (\S+) (\S+) ket thuc (\S+) khong khop', 'symbol,cid,status', 'FillAccounting:211'),
    ('EXEC_ACK', ('[C3-LIVE-EXEC]', 'ACK thieu avgPrice'), r'\[C3-LIVE-EXEC\] (\S+) (\S+) ACK thieu avgPrice => gia (\S+) tu (\S+) sau (\S+) ms',
     'symbol,cid,px,src,ms', 'C3LiveOrderExecutor:411'),
    ('EXEC_FILL', ('[C3-LIVE-EXEC] FILL ',), r'\[C3-LIVE-EXEC\] FILL (\S+) (\S+) qty=(\S+) avg=(\S+) ref=(\S+) slip=(\S+)', 'symbol,cid,qty,avg,ref,slip',
     'C3LiveOrderExecutor:435'),
    ('CUM_DA_DONG', ('[C3-LIVE] cum ', 'DA DONG tren san'), r'\[C3-LIVE\] cum (\S+) DA DONG tren san \(([^)]*)\) qty=(\S+)', 'symbol,reason,qty', 'FillAccounting:421'),
    ('SCOPE_TUCHOI', ('[C3-LIVE-SCOPE] TU CHOI',), r'\[C3-LIVE-SCOPE\] TU CHOI (\S+) (\S+):', 'api,symbol', 'C3ScopedGateway:112'),
    ('STOPGUARD', ('[C3-LIVE-STOPGUARD] huy stop',), r'huy stop (\S+) (\S+)', 'symbol,cid', 'OwnStopGuard:136'),
    ('TRAIL_STOP_ERR', ('[C3-LIVE-TRAIL]', ' dat stop c3s-'), r'\[C3-LIVE-TRAIL\] (\S+) dat stop (\S+) (loi|trang thai khong ro)', 'symbol,cid,kind',
     'TrailingStopManager:362-370'),
    ('ORDER', ('[C3-LIVE-ORDER] ts=',), r'cid=(\S+) oid=(\S+) sym=(\S+) side=(\S+) type=(\S+) qty=(\S+) px=(\S+) status=(\S+)',
     'cid,oid,symbol,side,type,qty,px,status', 'OrderAuditLog:11'),
    ('FILL_STOP', ('[C3-LIVE-FILL]', 'stop khop'), r'\[C3-LIVE-FILL\] (\S+) stop khop (\S+)@(\S+) \(stop=(\S+) truot=(\S+)\)', 'symbol,qty,px,stop,slip', 'FillAccounting:233'),
    ('ALGO', ('[C3-LIVE-FILL] ALGO_UPDATE',), r'\[C3-LIVE-FILL\] ALGO_UPDATE (\S+) caid=(\S+) X=(\S+)', 'symbol,caid,X', 'FillAccounting'),
    ('TRAIL_arm', ('[C3-LIVE-TRAIL] arm ',), r'\[C3-LIVE-TRAIL\] arm (\S+) entry=(\S+) px=(\S+) peak=(\S+) SL=(\S+)', 'symbol,entry,px,peak,SL', 'TrailingStopManager:211'),
    ('TRAIL_STOP', ('[C3-LIVE-TRAIL]', ' stop=', ' cid=', ' mode='), r'\[C3-LIVE-TRAIL\] (\S+) (\S+) stop=(\S+) cid=(\S+) mode=(\S+)', 'symbol,act,stop,cid,mode',
     'TrailingStopManager:331'),
    ('TRAIL_4130', ('[C3-LIVE-TRAIL]', 'san tu choi stop closePosition'), r'\[C3-LIVE-TRAIL\] (\S+) san tu choi stop closePosition', 'symbol', 'TrailingStopManager:348'),
    ('EXIT_2021', ('[C3-LIVE-TRAIL]', '-2021'), r'\[C3-LIVE-TRAIL\] (\S+) stop (\S+) se kich ngay \(-2021', 'symbol,cid', 'TrailingStopManager:355'),
    ('TIME_STOP', ('[C3-LIVE-TRAIL] TIME-STOP',), r'\[C3-LIVE-TRAIL\] TIME-STOP (\S+) entry=(\S+) px=(\S+) gio_giu=(\d+)', 'symbol,entry,px,hours', 'TrailingStopManager:226'),
    ('UNARM', ('[C3-LIVE-TRAIL]', 'khong con arm'), r'\[C3-LIVE-TRAIL\] (\S+) khong con arm', 'symbol', 'TrailingStopManager:244'),
    ('BOOK_CLOSE', ('[C3-LIVE-BOOK] dong cum',), r'dong cum (\S+) ly do=(\S+) legs=(\S+) qty=(\S+) avg=(\S+) exitQty=(\S+) exitAvg=(\S+) realized=(\S+) phi=(\S+)',
     'symbol,reason,legs,qty,avg,exitQty,exitAvg,realized,fee', 'LiveBookC3:737'),
    ('CLOSE_DA_DONG', ('[C3-LIVE-CLOSE]', 'DA DONG'), r'\[C3-LIVE-CLOSE\] (\S+) DA DONG \(([^)]*)\)', 'symbol,reason', 'C3LiveFlattener:271'),
    ('CLOSE_KHONG_KHOP', ('[C3-LIVE-CLOSE]', 'khong khop'), r'\[C3-LIVE-CLOSE\] (\S+) (\S+) khong khop', 'symbol,cid', 'C3LiveFlattener:182'),
    ('ORDER_4130', ('[C3-LIVE-ORDER]', '-4130'), r'\[C3-LIVE-ORDER\] .*?cid=(\S+) .*?sym=(\S+) .*?status=ERROR .*?err=\S*-4130', 'cid,symbol', 'OrderAuditLog'),
    ('ORDER_REJECTED', ('[C3-LIVE-ORDER]', 'status=REJECTED'), r'\[C3-LIVE-ORDER\] .*?cid=(\S+) .*?sym=(\S+) .*?status=REJECTED', 'cid,symbol', 'OrderAuditLog'),
    ('ORDER_EXPIRED', ('[C3-LIVE-ORDER]', 'status=EXPIRED'), r'\[C3-LIVE-ORDER\] .*?cid=(\S+) .*?sym=(\S+) .*?status=EXPIRED', 'cid,symbol', 'OrderAuditLog'),
    ('TUCHOI_CID', ('tu choi cid=',), r'tu choi cid=(\S+)', 'cid', 'prereg N4'),
    ('INC_MIN', ('[MINUTE-INCOMPLETE] phut=',), r'\[MINUTE-INCOMPLETE\] phut=' + P + r' (?:.*?ly_do=(\S+))?', 'phut,ly_do', 'MinuteCompletenessGuard:423/:482'),
    ('INC_LEG', ('[MINUTE-INCOMPLETE] chan lenh moi',), r'\[MINUTE-INCOMPLETE\] chan lenh moi (\S+) (\S+) \(phut ' + P, 'level,symbol,phut', 'DetectEntrySignal2TradeNormal:1273'),
    ('FIN_EXCL', ('[MINUTE-FIN-EXCL] chan leg',), r'\[MINUTE-FIN-EXCL\] chan leg (\S+) (\S+) \(phut ' + P, 'level,symbol,phut', 'DetectEntrySignal2TradeNormal:1352'),
    ('FIN_EXCL_MIN', ('[MINUTE-FIN-EXCL] phut=',), r'\[MINUTE-FIN-EXCL\] phut=' + P + r' loai=(\d+) .*? ds=(\S+) =>', 'phut,loai,ds', 'MinuteCompletenessGuard:415'),
    ('JVM_START', ('MainClass: com.binance.chuyennd.trading.BinanceOrderTradingManager',), r'MainClass: (\S+)', 'main', 'Utils (khoi dong)'),
    ('GATE', ('[GATE] scale=',), r'\[GATE\] scale=\S+ topk=\d+ base=\S+ thr=\[\S*\] n_cand=(\d+) n_rej=(\d+) n_pass=(-?\d+)(?: n_skipfull=(\d+) u=(\S+))?',
     'n_cand,n_rej,n_pass,n_skipfull,u', 'DetectEntrySignal2TradeNormal:670 LiveBookU.gateLine (so day = SO GIAY, ERRATA5 D1)'),
    ('TICK', ('Btc ticker size',), r'Btc ticker size: .*-> ' + P, 'dts', 'DetectEntrySignal2TradeNormal:266'),
    ('SKIP_PAPER', ('skipFull',), r'(skipFull).*?([A-Z0-9]{2,}USDT)', 'kind,symbol', 'ShadowBookC3'),
    ('SKIP_PAPER2', ('liveBookFull',), r'(liveBookFull).*?([A-Z0-9]{2,}USDT)', 'kind,symbol', 'ShadowBookC3'),
    ('EQ_UNAVAIL', ('[C3-LIVE-EQ] positions() loi',), r'\[C3-LIVE-EQ\] positions\(\) loi', '', 'C3MainEquity:157 (N9)'),
    ('EQ_NOEQ', ('[C3-LIVE-EQ]', 'khong co equity'), r'\[C3-LIVE-EQ\] (.*?) => khong co equity', 'why_head', 'C3MainEquity:157 / C3LiveEquity:82'),
    ('EQ_ACCOUNT', ('[C3-LIVE-EQ] account() loi',), r'\[C3-LIVE-EQ\] account\(\) loi', '', 'C3MainEquity:199'),
    ('EQ_KYQUY', ('[C3-LIVE-EQ] CANH BAO ky quy',), r'\[C3-LIVE-EQ\] CANH BAO ky quy', '', 'C3MainEquity:174 (K7)'),
    ('FUNDING', ('[C3-LIVE-EQ] funding c3',), r'\[C3-LIVE-EQ\] funding c3 (\S+) \((\d+) dong\) => cong don (\S+)', 'add,n,cum', 'C3MainEquity:247'),
    ('KHAN', ('KHAN',), r'KHAN', '', 'alerts'),
    ('KS_LATCH', ('[KILLSW]', 'LATCH'), r'\[KILLSW\].*LATCH', '', 'OpsHooks'),
]
RULES = [(n, t, re.compile(r), h, src) for n, t, r, h, src in RULES]
TAGRX = re.compile(r'\[C3-LIVE[A-Z0-9-]*\]')
# dong [C3-LIVE*] CHI thong tin (khoi dong / HOURLY / ket noi / doi chieu) - KHONG dung cho cham; dem rieng theo dang (A1 xem), khong tinh unmatched
INFO_RX = re.compile(r'(\[C3-LIVE\] HOURLY|\[C3-LIVE\] khoi dong adapter|\[C3-LIVE\] client san sang|\[C3-LIVE-BOOK\] chua co file|\[C3-LIVE\] UNIVERSE_A1='
                     r'|\[C3-LIVE-ALERT\]|\[C3-LIVE-STREAM\]|\[C3-LIVE\] nap SymbolRules|\[C3-LIVE\] khoi phuc sau restart|\[C3-LIVE-SCOPE\] LEGACY tren'
                     r'|\[C3-LIVE\] \[C3-LIVE-SCOPE\] LEGACY|\[C3-LIVE-SCOPE\] doc toan tai khoan|\[C3-LIVE-RECON\]|\[C3-LIVE\] reconcile khoi dong'
                     r'|\[C3-LIVE-EQ\] nap trang thai|\[C3-LIVE\] PUSH doi trang thai|\[C3-LIVE\] -1021 timestamp'
                     r'|\[C3-LIVE\] exchangeInfo |\[C3-LIVE\] DRY tren tai khoan|\[C3-LIVE-BOOK\] nap \d+ cum)')
MASK = [(re.compile(r'[A-Z0-9]+USDT'), 'SYM'), (re.compile(r'c3s?-SYM-\S+'), 'CID'), (re.compile(r'\d'), '9')]


def ms7(s, fmt):
    return int(datetime.strptime(s, fmt).replace(tzinfo=TZ7).timestamp() * 1000)


def has(ln, tag):
    return all(x in ln for x in tag)


def shape(ln, tag):
    i = ln.find(tag)
    s = ln[i:i + 70]
    for rx, rp in MASK:
        s = rx.sub(rp, s)
    return ' '.join(s.split()[:5])


def files_of(a):
    if a.log_files:
        return a.log_files.split(',')
    return sorted(set(sum([glob.glob(PULL + '/%s/logs/full.log@*.gz' % d) for d in a.days.split(',')], [])))


def lines(files):
    seen = set()
    for f in files:
        op = gzip.open if f.endswith('.gz') else open
        with op(f, 'rt', errors='replace') as fh:
            for ln in fh:
                if ln in seen:
                    continue
                seen.add(ln)
                yield f, ln
    log.info('files=%d unique_lines=%d', len(files), len(seen))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--days', default=''); ap.add_argument('--log-files', default='')
    ap.add_argument('--start', default=''); ap.add_argument('--end', default=''); ap.add_argument('--out', default='')
    ap.add_argument('--mode', choices=['format', 'full'], default='format'); ap.add_argument('--dump-rules', action='store_true')
    a = ap.parse_args()
    if a.dump_rules:
        print(json.dumps([{'name': n, 'tags': list(t), 'src': s} for n, t, _, _, s in RULES]))
        return
    S, E = ms7(a.start, '%Y-%m-%d %H:%M'), ms7(a.end, '%Y-%m-%d %H:%M')
    # [ERRATA4 C4] --log-files KHONG bo qua P1 khi file nam duoi pull242 (realpath) va cua so ket thuc sau 2026-11-15
    under_pull = (not a.log_files) or any(os.path.realpath(f).startswith(os.path.realpath(PULL) + os.sep) for f in files_of(a))
    if a.mode == 'full' and under_pull and E > ms7('2026-11-15 07:00', '%Y-%m-%d %H:%M'):
        log.info('P1: %s', require_p1())
    os.makedirs(a.out, exist_ok=True)
    cnt = {n: {'tag_lines': 0, 'parsed': 0} for n, *_ in RULES}
    rows = {n: [] for n, *_ in RULES}
    unmatched, info, minutes_seen = {}, {}, set()
    for f, ln in lines(files_of(a)):
        m = TS.match(ln)
        if not m:
            continue
        t = ms7(m.group(1), '%d/%m/%Y %H:%M:%S') + int(m.group(2))
        if t < S or t >= E:
            continue
        minutes_seen.add(t // 60000)
        hit = False
        for n, tag, rx, _, _ in RULES:
            if has(ln, tag):
                cnt[n]['tag_lines'] += 1
                g = rx.search(ln)
                if g:
                    cnt[n]['parsed'] += 1; hit = True
                    if a.mode == 'full':
                        rows[n].append([t] + [x if x is not None else '' for x in g.groups()] + [os.path.basename(f)])
        if not hit:
            tm = TAGRX.search(ln)
            if tm and INFO_RX.search(ln):
                k = shape(ln, tm.group(0)); info[k] = info.get(k, 0) + 1
            elif tm:
                k = shape(ln, tm.group(0))
                unmatched[k] = unmatched.get(k, 0) + 1
    gaps = [mn * 60000 for mn in range(S // 60000, E // 60000) if mn not in minutes_seen]
    res = {'mode': a.mode, 'files': [os.path.basename(x) for x in files_of(a)], 'start': S, 'end': E, 'counts': cnt,
           'minutes_window': (E - S) // 60000, 'minutes_without_any_log_line': len(gaps),
           'parse_rate_ok': {n: (c['tag_lines'] == c['parsed']) for n, c in cnt.items()},
           'unmatched_c3live_lines': sum(unmatched.values()), 'unmatched_by_shape': unmatched, 'info_lines_by_shape': info,
           'rules_src': {n: s for n, _, _, _, s in RULES}}
    if a.mode == 'full':
        for n, _, _, h, _ in RULES:
            with open(os.path.join(a.out, n.lower() + '.csv'), 'w') as fh:
                fh.write('log_ms' + (',' + h if h else '') + ',file\n')
                csv.writer(fh, lineterminator='\n').writerows(rows[n])
        blk = set()
        for r in rows['INC_MIN']:
            blk.add((ms7(r[1], '%Y%m%d %H:%M'), '*', '*', 'MINUTE-INCOMPLETE'))
        for r in rows['INC_LEG']:
            blk.add((ms7(r[3], '%Y%m%d %H:%M'), r[2], r[1], 'MINUTE-INCOMPLETE-LEG'))
        for r in rows['FIN_EXCL_MIN']:
            for sym in r[3].split(','):
                if sym.endswith('USDT'):
                    blk.add((ms7(r[1], '%Y%m%d %H:%M'), sym, '*', 'MINUTE-FIN-EXCL-MIN'))
        # [ERRATA5 D1] so day THEO VET: dong [GATE] in o tick phut dts+1 (cung tick voi 'Btc ticker -> dts') => dts = phut log - 1'
        for r in rows['GATE']:
            if r[4] and int(r[4]) > 0:
                blk.add(((int(r[0]) // 60000 - 1) * 60000, 'FULL', '*', 'GATE_SKIPFULL'))
        # [ERRATA5 B(i)] tier3 THEO VET: '[C3-LIVE] skip SYM DCA_* TIER3_DCA' (C3LiveEntry:243 -> :320) in o tick dts+1 => chan (dts, SYM, level)
        for n in ('SKIP', 'KHONG_VAO'):
            for r in rows[n]:
                if r[3] == 'TIER3_DCA':
                    blk.add(((int(r[0]) // 60000 - 1) * 60000, r[1], r[2], 'TIER3_DCA'))
        for r in rows['FIN_EXCL']:
            blk.add((ms7(r[3], '%Y%m%d %H:%M'), r[2], r[1], 'MINUTE-FIN-EXCL'))
        with open(os.path.join(a.out, 'block.csv'), 'w') as fh:
            fh.write('decision_ts,symbol,level,kind\n')
            csv.writer(fh, lineterminator='\n').writerows(sorted(blk))
        with open(os.path.join(a.out, 'tick_dts.csv'), 'w') as fh:
            fh.write('dts\n' + ''.join('%d\n' % x for x in sorted({ms7(r[1], '%Y%m%d %H:%M') for r in rows['TICK']})))
        with open(os.path.join(a.out, 'gaps.csv'), 'w') as fh:
            fh.write('minute_ms\n' + ''.join('%d\n' % g for g in gaps))
        res['block_rows'] = len(blk)
    json.dump(res, open(os.path.join(a.out, 'counts.json'), 'w'), indent=1)
    print(json.dumps({'nonzero': {k: v for k, v in cnt.items() if v['tag_lines']}, 'unmatched': sum(unmatched.values())}))


if __name__ == '__main__':
    main()
