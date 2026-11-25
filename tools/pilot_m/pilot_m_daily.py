#!/usr/bin/env python3
# pilot_m_daily.py - bo cham HANG NGAY phan "CHI LOG" cua PREREG_PILOT_M (commit 2a21fe35633c85ca1357992a6882de3e9f520030).
# Chi doc: pull242/<D>/ (+ pull cac ngay truoc tu --state-start de dung trang thai cum luy ke, prereg muc 0)
#          va ~/claude_master/deploy/golive_monitor_cron.log (K2). Khong mang, khong ket noi 242, chi stdlib.
# An toan: truong tien (eq=, realized=, phi=, tmb...) chi dung trong bo nho; moi dong log ghi ra deu qua san().
# Bang muc -> ham -> dong prereg: README_PILOT_M.md.
import argparse
import bisect
import datetime as dt
import glob
import gzip
import hashlib
import json
import logging
import math
import os
import re
import struct
import sys
import tempfile
import time
from decimal import Decimal, InvalidOperation

LOG = logging.getLogger('pilot_m')
PREREG_SHA = '2a21fe35+E1+E2'   # prereg 2a21fe35 + ERRATA1 c0f35f3c + ERRATA2 efc4f9c1
TZ7 = dt.timezone(dt.timedelta(hours=7))
DAT, VP, KCSK, KCD, KCDC = 'DAT', 'VI_PHAM', 'KHONG_CO_SU_KIEN', 'KHONG_CHAM_DUOC', 'KCD_CAU_TRUC'
PRIO = {VP: 4, KCD: 3, KCDC: 2, KCSK: 1, DAT: 0}
XANH, VANG, DO = 'XANH', 'VANG', 'DO'
BPRIO = {XANH: 0, VANG: 1, DO: 2}
H = 3600000
DAY_MS = 86400000
FAR = 1 << 62
PILOT_DAY = dt.date(2026, 11, 26)
STATE_START_DEFAULT = '2026-11-21'
MX_CUM_START = '2026-11-24 07:00'
LEVELS = [-0.5, -0.75, -0.9]            # prereg muc 4 (banner [LIVE-DCA-GRID] levels)
LOOKAHEAD_MS = 2 * H                    # doc them toi da 2 h sau cua so trong CHINH file pull ngay D
UNPARSED_MAX = 0.001                    # 0,1 % (fail-closed)
KCDC_TOOL = 'chua co cong cu Vision/rig duoc A1 duyet'
OFFICIAL_DIR = os.path.expanduser('~/claude_master/v12/pilot_m')
DEF_PULL = os.path.expanduser('~/claude_master/pull242')
DEF_CRON = os.path.expanduser('~/claude_master/deploy/golive_monitor_cron.log')
JAR = '01cfbb43'
MAX_LIST = 200
I10_CODE = {'TRAILING_STOP', 'TIME_STOP_168H', 'TRAILING_IMMEDIATE', 'STOP_LOST_61S', 'EXTERNAL', 'DELIST_SETTLE',
            'LIQUIDATION', 'ADL', 'LOST_FOREIGN', 'GHOST_CLEAR_OWNER', 'BOT_CLOSE'}
I10_OK = {'TRAILING_STOP', 'TIME_STOP_168H', 'TRAILING_IMMEDIATE'}
I8_TRAIL = {'TRAILING_STOP', 'TRAILING_IMMEDIATE', 'STOP_LOST_61S'}
I8_PRE_OK = {'TIME_STOP_168H'}   # DELIST_SETTLE chi khi --delist-noted (E4)
DO_REASONS = {'LIQUIDATION', 'ADL', 'STOP_LOST_61S', 'LOST_FOREIGN'}

# ------------------------------------------------------------------ an toan du lieu
_SIG = re.compile(r'signature=[^&\s"]*')
_TOK = re.compile(r'[0-9]{8,10}:[A-Za-z0-9_-]{30,}')
_MONEY = re.compile(r'\b(realized|phi|pnl\w*|tmb\w*|eq\w*|acct_eq|acct_peak|funding|availableBalance|avail\w*|bal|balance|'
                    r'margin\w*|wallet\w*|upnl|upl\w*|fee|rp|so_du\w*|chot|moc|chuyen|dinh)=[^\s,;)\]]*', re.I)
_WB = re.compile(r'(?i)\b[A-Z0-9_]*(?:WALLET|BALANCE)[A-Z0-9_]*=[^\s,;)\]]*')
_EQP = re.compile(r'(eq = C3_CAPITAL \+ \()[^)]*\)')
_PEAK = re.compile(r'\bpeak=[^\s,;)\]]*')
_TT_PRIV = re.compile(r'\b(dd|key)=[^\s]*')


def san(s):
    """Loc 1 dong truoc khi giu/ghi: bo truong tien/so du, signature, token Telegram."""
    if s is None:
        return None
    if 'Telegram respon' in s:
        s = s.split('Telegram respon')[0] + 'Telegram respon <REDACTED>'
    if '[C3-LIVE-EQ]' in s:
        i = s.index('[C3-LIVE-EQ]')
        s = s[:i] + ('[C3-LIVE-EQ] CANH BAO ky quy <REDACTED>' if 'CANH BAO ky quy' in s else '[C3-LIVE-EQ] <REDACTED>')
    s = _SIG.sub('signature=<SIG>', s)
    s = _TOK.sub('<TOKEN>', s)
    s = _MONEY.sub(lambda m: m.group(1) + '=<X>', s)
    s = _WB.sub(lambda m: m.group(0).split('=', 1)[0] + '=<X>', s)
    s = _EQP.sub(lambda m: m.group(1) + '<X>)', s)
    if '[KILLSW]' in s or 'TOM TAT' in s:
        s = _PEAK.sub('peak=<X>', s)
    if 'TOM TAT' in s:
        s = _TT_PRIV.sub(lambda m: m.group(1) + '=<X>', s)
    return s[:700]


# ------------------------------------------------------------------ thoi gian
def ms_local(s):
    s = s.strip()
    for f in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d %H:%M'):
        try:
            return int(dt.datetime.strptime(s, f).replace(tzinfo=TZ7).timestamp() * 1000)
        except ValueError:
            pass
    raise ValueError('thoi gian sai dinh dang (+07 yyyy-mm-dd HH:MM): %s' % s)


def fmt(ms):
    if ms is None:
        return None
    return dt.datetime.fromtimestamp(ms / 1000.0, TZ7).strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]


def day_lo(d):
    return int(dt.datetime(d.year, d.month, d.day, 7, 0, tzinfo=TZ7).timestamp() * 1000)


def minute_str(ms):
    return dt.datetime.fromtimestamp(ms / 1000.0, TZ7).strftime('%Y%m%d %H:%M')


def utc_day(ms):
    return dt.datetime.fromtimestamp(ms / 1000.0, dt.timezone.utc).date().isoformat()


def dec(s):
    try:
        return Decimal(s)
    except (InvalidOperation, TypeError, ValueError):
        return None


def flt(s):
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def f32(x):
    return struct.unpack('f', struct.pack('f', x))[0]


def trail_sl(entry, peak, gap=0.03, give=1.0):
    """TradeUtils.trailFromCap :52-58 + TrailingStopManager arm (entry * (1f + rate)) tinh float32."""
    e = f32(entry)
    p = f32(peak)
    g = min(f32(p * f32(give)), f32(gap))
    rate = f32(p - g)
    q = f32(rate / f32(0.005))
    r = math.floor(q + 0.5)          # Math.round(float) = floor(x + 0.5)
    rate = f32(r * f32(0.005))
    return f32(e * f32(1.0 + rate))


def pct(vals, p):
    if not vals:
        return None
    v = sorted(vals)
    k = max(0, min(len(v) - 1, int(math.ceil(p * len(v))) - 1))
    return v[k]


def median(vals):
    if not vals:
        return None
    v = sorted(vals)
    n = len(v)
    return v[n // 2] if n % 2 else (v[n // 2 - 1] + v[n // 2]) / 2.0


# ------------------------------------------------------------------ mau dong log
HDR = re.compile(r'^(\d\d)/(\d\d)/(\d{4}) (\d\d):(\d\d):(\d\d)\.(\d{3}) +([A-Z]+) +\[([^\]]*)\] (\S+): ?(.*)$')
_DC = {}


def hdr_ms(m):
    k = (m.group(3), m.group(2), m.group(1))
    b = _DC.get(k)
    if b is None:
        b = int(dt.datetime(int(k[0]), int(k[1]), int(k[2]), tzinfo=TZ7).timestamp() * 1000)
        _DC[k] = b
    return b + ((int(m.group(4)) * 60 + int(m.group(5))) * 60 + int(m.group(6))) * 1000 + int(m.group(7))


def _F(name, pre, cont, rx, lg=None):
    return {'name': name, 'pre': pre, 'cont': cont, 'rx': re.compile(rx), 'lg': lg,
            'marker': pre if pre else cont[0]}


# Thu tu quan trong: mau cu the dung truoc mau long (STOP).
FAMS = [
    _F('SUBMIT', '[C3-LIVE] SUBMIT ', (), r'^\[C3-LIVE\] SUBMIT (\S+) (\S+) SUBMITTED cid=(c3-(\S+)-(\d+)-(\d+)) qty=(\S+) '
       r'budget=(\S+) legIdx=(\d+) notional=(\S+) U_before=(\S+)\s*$'),
    _F('FILL_EXEC', '[C3-LIVE-EXEC] FILL ', (), r'^\[C3-LIVE-EXEC\] FILL (\S+) (c3-\S+) qty=(\S+) avg=(\S+) ref=(\S+) slip=(\S+)'),
    _F('FILL_STREAM', '[C3-LIVE-FILL] xac nhan qua stream ', (),
       r'^\[C3-LIVE-FILL\] xac nhan qua stream (\S+) (c3-\S+) qty=(\S+) avg=(\S+) ref=(\S+)'),
    _F('LEG_END', '[C3-LIVE-FILL] leg ', ('khong khop => huy giu cho',),
       r'^\[C3-LIVE-FILL\] leg (\S+) (c3-\S+) ket thuc (\S+) khong khop => huy giu cho'),
    _F('EXEC_END', '[C3-LIVE-EXEC] ', ('=> huy giu cho',),
       r'^\[C3-LIVE-EXEC\] (?:executor tu choi cid=(c3-\S+) |(\S+) (c3-\S+) .*)=> huy giu cho'),
    _F('PXCORR', '[C3-LIVE-', ('PX_CORRECTED',), r'^\[C3-LIVE-(?:EXEC|FILL)\] (\S+) (c3-\S+) PX_CORRECTED (?:\S+ )?-> (\S+)'),
    _F('ARM', '[C3-LIVE-TRAIL] arm ', (), r'^\[C3-LIVE-TRAIL\] arm (\S+) entry=(\S+) px=(\S+) peak=(\S+) SL=(\S+)\s*$'),
    _F('TS', '[C3-LIVE-TRAIL] TIME-STOP ', (),
       r'^\[C3-LIVE-TRAIL\] TIME-STOP (\S+) entry=(\S+) px=(\S+) gio_giu=(\S+) => dong MARKET reduce-only'),
    _F('RST', '[C3-LIVE-TRAIL] ', ('khong con arm (DCA reset)',),
       r'^\[C3-LIVE-TRAIL\] (\S+) khong con arm \(DCA reset\) => huy stop (\S+)'),
    _F('E4130', '[C3-LIVE-TRAIL] ', ('(-4130)',), r'^\[C3-LIVE-TRAIL\] (\S+) san tu choi stop closePosition thu 2 \(-4130\)'),
    _F('E2021', '[C3-LIVE-TRAIL] ', ('(-2021',), r'^\[C3-LIVE-TRAIL\] (\S+) stop (\S+) se kich ngay \(-2021'),
    _F('STOPERR', '[C3-LIVE-TRAIL] ', (' dat stop ', '=> thu lai nhip sau'),
       r'^\[C3-LIVE-TRAIL\] (\S+) dat stop (\S+) loi (.*) => thu lai nhip sau'),
    _F('CANCERR', '[C3-LIVE-TRAIL] ', (' huy stop ', ' loi => thu lai nhip sau'),
       r'^\[C3-LIVE-TRAIL\] (\S+) huy stop (\S+) loi => thu lai nhip sau'),
    _F('STOP', '[C3-LIVE-TRAIL] ', (' stop=', ' cid=c3s-'),
       r'^\[C3-LIVE-TRAIL\] (\S+) (\S+) stop=(\S+) cid=(c3s-\S+) mode=(closePosition|qty\+reduceOnly) \(cu=(\S+) (\S+)\)\s*$'),
    _F('ALGO', '[C3-LIVE-FILL] ALGO_UPDATE ', (), r'^\[C3-LIVE-FILL\] ALGO_UPDATE (\S+) caid=(\S*) X=(\S*) ai=(\S*)\s*$'),
    _F('SFIL', '[C3-LIVE-FILL] ', (' stop khop ',), r'^\[C3-LIVE-FILL\] (\S+) stop khop (\S+)@(\S+) \(stop=(\S+) truot=(\S+)\)'),
    _F('CLOS', '[C3-LIVE] cum ', (' DA DONG tren san',), r'^\[C3-LIVE\] cum (\S+) DA DONG tren san \(([^)]*)\) qty=(\S+)'),
    _F('BOOK', '[C3-LIVE-BOOK] dong cum ', (),
       r'^\[C3-LIVE-BOOK\] dong cum (\S+) ly do=(\S+) legs=(\d+) qty=(\S+) avg=(\S+) exitQty=(\S+)'),
    _F('VIAM', '[C3-LIVE] vi the AM (short)', (), r'^\[C3-LIVE\] vi the AM \(short\) (\S+)'),
    _F('MERGED_ON', '[C3-LIVE] KHAN: ', (' MERGED',), r'^\[C3-LIVE\] KHAN: (\S+) MERGED'),
    _F('MERGED_OFF', '[C3-LIVE] ', (' het MERGED:',), r'^\[C3-LIVE\] (\S+) het MERGED:'),
    _F('RECON_H', '[C3-LIVE-RECON] HOURLY', (),
       r'^\[C3-LIVE-RECON\] HOURLY khop: doi chieu qty c3 \((\d+) cum\) lech max=(\S+?)(.*?) streak=(\d+)\s*$'),
    _F('RECON_LECH', '[C3-LIVE-RECON] LECH QTY c3', (), r'^\[C3-LIVE-RECON\] LECH QTY c3'),
    _F('RECON_VANLECH', '[C3-LIVE-RECON] van lech qty', (), r'^\[C3-LIVE-RECON\] van lech qty'),
    _F('LOPB', '[C3-LIVE-RECON] ', (': cum so vua chot nhung ',), r'^\[C3-LIVE-RECON\] (\S+): cum so vua chot nhung .*\(lop B\)'),
    _F('GOB', '[C3-LIVE-RECON] ', (': 2 lan doc phang',), r'^\[C3-LIVE-RECON\] (\S+): 2 lan doc phang .*GO chan rieng symbol \(lop B\)'),
    _F('TSX_FLAG', '[TS-EXT] flag day=', (), r'^\[TS-EXT\] flag day=(\d{4}-\d\d-\d\d) flag=(\S+) .*final=(true|false)\s*$'),
    _F('TSX_STATUS', '[TS-EXT] status ', (), r'^\[TS-EXT\] status now=\S+ flagToday=(\S+) '),
    _F('TSX_DEFER', '[TS-EXT] defer-START ', (), r'^\[TS-EXT\] defer-START (\S+) age_h=(\d+) flag=(\S+)'),
    _F('TSX_NOFLAG', '[TS-EXT] chua co co ngay', (), r'^\[TS-EXT\] chua co co ngay'),
    _F('KS_HOURLY', '[KILLSW] HOURLY ', (),
       r'^\[KILLSW\] HOURLY hour=(\S+) .* eq=(\S+) peak=\S+ dd=(\S+)(?: acct_eq=\S+ acct_peak=\S+ acct_dd=(\S+))?(?: latch=(\S+))?'),
    _F('C2WARN', '[KILLSW] C2_WARN', (), r'^\[KILLSW\] C2_WARN symbol=(\S+) side=(\S+) adverse=(\S+) warn>(\S+) slip>(\S+)'),
    _F('LATCH', '[KILLSW] LATCH', (), r'^\[KILLSW\] LATCH (?:action=(\S+) \(truoc \S+\) code=(\S+)|them code=(\S+))'),
    _F('BANNER', '[C3-LIVE] khoi dong adapter=', (),
       r'^\[C3-LIVE\] khoi dong adapter=(\S+) .*\bcum=(\d+) .*\bc3_capital=(\S+) .*\bkillSwitchArmed=(\S+) X14=(\S+)', 'C3LiveRuntime'),
    _F('MAINCLASS', 'MainClass: ', (), r'^MainClass: (\S+)'),
    _F('RECOV', '[C3-LIVE] khoi phuc sau restart: ', (), r'^\[C3-LIVE\] khoi phuc sau restart: con (\d+) leg treo'),
    _F('RECON_START', '[C3-LIVE] reconcile khoi dong ', (), r'^\[C3-LIVE\] reconcile khoi dong (\S+)'),
    _F('AIPASS', None, ('AI PASS [',), r'AI PASS \[(\S+)\] Reason: (.*) symbolPred: (\S+)\s*$'),
    _F('SKIPORD', None, ('SKIP ORDER [',), r'SKIP ORDER \[(\S+) (\S+)\] due to (.*)$'),
    _F('DCAGRID', '[LIVE-DCA-GRID] site=', (), r'^\[LIVE-DCA-GRID\] site=(\S+) (?:due=\[(.*)\]|live-only due=(\S+))\s*$'),
    _F('MKT', 'Market level', (),
       r'^Market level(?: change: (\d{8} \d\d:\d\d) level: (\S+) symbols:\S*|:(\d{8} \d\d:\d\d) (\S+) (\S+)(?: .*)?)\s*$'),
    _F('EQWARN', '[C3-LIVE-EQ] CANH BAO ky quy', (), r'^\[C3-LIVE-EQ\] CANH BAO ky quy'),
    _F('NOPRICE', '[C3-LIVE] khong doc duoc gia realtime', (), r'^\[C3-LIVE\] khong doc duoc gia realtime'),
]
# Mau dong KHONG thuoc ho cham (trich tu code 4fdda6f8, chuoi literal co tien to A1 T1); so khop tien to, {} = bat ky.
OTHER_TPL = [
    '[C3-LIVE-BOOK] FILE SO HONG {} ({}) => FAIL-CLOSED: chan mo moi; sao luu {}. Can reconcile/owner.',
    '[C3-LIVE-BOOK] KHONG GHI DUOC {}: {} => FAIL-CLOSED (chan mo moi toi khi ghi lai duoc)',
    '[C3-LIVE-BOOK] R1: {} execQty={} nhung avgPx={} => KHONG huy giu cho, giu leg cho gia that/gia tam',
    '[C3-LIVE-BOOK] chua co file {} => so rong',
    '[C3-LIVE-BOOK] ghi lai duoc {} => het fail-closed persist',
    '[C3-LIVE-BOOK] khong ghi duoc ledger {}: {}',
    '[C3-LIVE-BOOK] nap {} cum ({} leg chua giai quyet) tu {}',
    '[C3-LIVE-EXEC] loi khong mong doi cid={}: {}',
    '[C3-LIVE-EXEC] onCostGiveUp loi {}',
    '[C3-LIVE-EXEC] {} {} ACK thieu avgPrice => gia {} tu {} sau {} ms',
    '[C3-LIVE-EXEC] {} {} PX_PROVISIONAL qty={} gia tam={} (mark; cho gia that)',
    '[C3-LIVE-EXEC] {} {} bu phi {} khop qua userTrades (stream khong ghi)',
    '[C3-LIVE-EXEC] {} {} executedQty={} nhung KHONG co ca gia tam => giu UNKNOWN (R1: khong huy)',
    '[C3-LIVE-EXEC] {} {} orderId={} bu phi THAT BAI sau {} lan => phi so co the THIEU (KIEM)',
    '[C3-LIVE-EXEC] {} {} queryOrder xac nhan KHONG co sau cua so an toan => gui lai CUNG cid (lan {})',
    '[C3-LIVE-EXEC] {} {} so khong ghi duoc truoc khi gui => KHONG gui, huy giu cho',
    '[C3-LIVE-EXEC] {} {} tra lai san sau trang thai khong ro: status={} execQty={}',
    '[C3-LIVE-EXEC] {} {} trang thai {} khong ket luan => UNKNOWN',
    '[C3-LIVE-EXEC] {} {} userTrades loi {} => bu phi thu lai sau',
    '[C3-LIVE-EXEC] {} {} {} nhung executedQty=0 => UNKNOWN, tra lai san (KHONG huy)',
    '[C3-LIVE-EXEC] {} {} {} nhung executedQty={} => UNKNOWN, tra lai san',
    "[C3-LIVE-FILL] ACCOUNT_UPDATE ly do={} doi so du on dinh {} => ghi 'chuyen tien' cho doi chieu equity",
    '[C3-LIVE-FILL] ACCOUNT_UPDATE {} doi so du tai san KHONG on dinh {} bc={} => khong quy USD (doi chieu ',
    '[C3-LIVE-FILL] khong lay duoc gia {}USDT (ngoai khoa) => phi se ghi than trong neu khong co gia cu',
    '[C3-LIVE-FILL] leg {} {} trang thai {} khong ket luan => giu leg',
    '[C3-LIVE-FILL] loi xu ly su kien {}: {}',
    '[C3-LIVE-FILL] {} cum da dong (stream toi truoc) => KHONG ghi khop khoi phuc',
    '[C3-LIVE-FILL] {} cum da dong ({}) nhung GIU {} stop c3s- (vi the san chua phang / doc loi)',
    '[C3-LIVE-FILL] {} khong doc duoc stop mo ({}) => Reconciler se don stop mo coi',
    '[C3-LIVE-FILL] {} khop t={} DA GHI (khoi phuc REST toi truoc) => bo qua ghi lai',
    '[C3-LIVE-FILL] {} khop vao t={} phi {} USD ghi qua REST (userTrades; stream khong ghi)',
    '[C3-LIVE-FILL] {} khop {}: rp san {} khac rp c3 {} (gia vao c3 {}) \u2014 doi chieu',
    '[C3-LIVE-FILL] {} stop closePosition {} {} sau khi da gui lenh dong {} (closeSent {} <= su kien {}) => binh',
    '[C3-LIVE-FILL] {} stop {} ket thuc {} nhung so khong giu cum (da dong) => bo qua',
    '[C3-LIVE-FILL] {} stop {} {} khi vi the da phang => binh thuong',
    '[C3-LIVE-FILL] {} vi the san = 0 nhung con leg mua treo => cho executor giai quyet',
    '[C3-LIVE-FILL] {} {} FILLED z={} nhung thieu ca ap/L => giu leg unresolved, cho executor giai gia',
    '[C3-LIVE-FILL] {} {} {} nhung z=0 => giu leg cho executor tra san (khong huy)',
    '[C3-LIVE-RECON] CHAN vao lenh ({}): {}{}',
    '[C3-LIVE-RECON] GIU stop c3s- (vi the con / doc loi): {}',
    '[C3-LIVE-RECON] GO chan mo moi (EQUITY_MISMATCH) sau khi dat lai moc',
    '[C3-LIVE-RECON] LECH EQUITY > ',
    '[C3-LIVE-RECON] NHAC (6h): VAN chan mo moi TOAN HE (UNKNOWN_POSITION) vi ',
    '[C3-LIVE-RECON] TU CHOI yeu cau reanchor: c3_live doi chieu theo QTY c3 (khong co moc equity/tmb)',
    '[C3-LIVE-RECON] dat moc doi chieu equity = ',
    '[C3-LIVE-RECON] equity khop lai ',
    '[C3-LIVE-RECON] fallback REST: {}',
    '[C3-LIVE-RECON] hang gio (qty c3) loi {}',
    '[C3-LIVE-RECON] hang gio loi {}',
    '[C3-LIVE-RECON] hang gio: khong doc duoc positions ({}) => bo luot',
    '[C3-LIVE-RECON] het vi the la => GO chan mo moi (UNKNOWN_POSITION)',
    '[C3-LIVE-RECON] huy stop dang giu (nay da phang): {}',
    '[C3-LIVE-RECON] huy stop mo coi: {}',
    '[C3-LIVE-RECON] khoi dong: ',
    '[C3-LIVE-RECON] khoi dong: khong doc duoc san ({}) => CHAN mo moi toi khi doi chieu duoc',
    '[C3-LIVE-RECON] owner GO cum ma ',
    '[C3-LIVE-RECON] qty c3 khop lai ',
    '[C3-LIVE-RECON] van lech equity: {}',
    '[C3-LIVE-RECON] vi the LA tren tai khoan c3_live: ',
    '[C3-LIVE-RECON] vi the la {} vang o lan doc nay => CHUA go chan (can lan doc xac nhan sau >= {} ms)',
    '[C3-LIVE-RECON] {} MERGED: san {} != so c3 {} => GIU so c3 (khong san thang)',
    '[C3-LIVE-RECON] {} tim bang chung thoat c3 loi {}',
    '[C3-LIVE-RECON] {} xu ly LOST_FOREIGN loi {}',
    '[C3-LIVE-RECON] {}: chan rieng (lop B) qua ',
    '[C3-LIVE-RECON] {}: cum so da chot > {} ms ma account VAN con vi the => leo thang UNKNOWN toan he',
    '[C3-LIVE-RECON] {}: cum so da chot > {} ms ma san VAN con vi the {} => leo thang UNKNOWN toan he',
    '[C3-LIVE-TRAIL] chua co SymbolRules => CHUA dat duoc stop tren san (vd {})',
    '[C3-LIVE-TRAIL] loi ensureStop {}: {}',
    '[C3-LIVE-TRAIL] loi nhip {}: {}',
    '[C3-LIVE-TRAIL] {} MERGED: thay stop closePosition {} bang stop qty reduceOnly (gia {})',
    '[C3-LIVE-TRAIL] {} SO KHONG GHI DUOC (dia day/loi IO) => VAN dat stop ',
    '[C3-LIVE-TRAIL] {} dat stop {} loi {} => tra san sau',
    '[C3-LIVE-TRAIL] {} dat stop {} trang thai khong ro ({}) => tra san sau {} ms',
    '[C3-LIVE-TRAIL] {} so khong ghi duoc => van dat stop {} tren san',
    '[C3-LIVE-TRAIL] {} stop moi {} CHUA xac nhan NEW (status={}, khong thay trong openStops sau 2 lan) => GIU ca',
    '[C3-LIVE-TRAIL] {} stop pending {} CO tren san ({}) => nhan lam stop active',
    '[C3-LIVE-TRAIL] {} stop pending {} KHONG co tren san => bo, dat lai nhip sau',
    '[C3-LIVE-TRAIL] {} stop pending {} tren san = {} => bo, dat lai nhip sau',
    '[KILLSW] A40 equity khong co/khong hop le (',
    '[KILLSW] AUTO_RELEASE codes=',
    '[KILLSW] BAT mode=act (c3_live): C1/C2/C3/C5 => latch NO_NEW_ENTRY (C1/C3/C5 tu go); C4 = cong suat ',
    '[KILLSW] BAT mode={} CHI LOG (khong doi quyet dinh). Nguong: C1 lag>{}s|miss>{}%|no_data>{}s; ',
    '[KILLSW] BLOCK_DCA symbol=',
    '[KILLSW] BLOCK_NEW_ENTRY symbol=',
    '[KILLSW] C4_CAPACITY OFF open=',
    '[KILLSW] C4_CAPACITY ON open=',
    '[KILLSW] C4_CAPACITY chan MO CUM MOI symbol=',
    '[KILLSW] C6 c3_live: equity khong hop le (',
    '[KILLSW] CLEAR code=',
    '[KILLSW] FAIL-CLOSED file latch ',
    "[KILLSW] LIVE_KILLSW_MODE='",
    "[KILLSW] LIVE_KILLSW_MODE=act BI TU CHOI o profile '",
    '[KILLSW] LIVE_KILLSW_MODE=act o c3_live: hanh dong CHUA cai trong',
    '[KILLSW] LIVE_PROFILE=c3_live nhung kill-switch KHONG o mode act (hieu luc={}) => KHONG co bao ve tu',
    '[KILLSW] NAP LATCH tu ',
    '[KILLSW] RESET boi owner (',
    '[KILLSW] acct_peak trong ',
    '[KILLSW] chua co file latch ',
    '[KILLSW] file dinh ',
    '[KILLSW] file latch ',
    '[KILLSW] file latch co C4 => bo (C4 la dieu kien cong suat, khong latch) => latch=',
    '[KILLSW] file reset ',
    '[KILLSW] gan EquitySource (A40 DD<=',
    '[KILLSW] khong doc duoc file dinh ',
    '[KILLSW] khong ghi duoc file dinh ',
    '[KILLSW] khong ghi duoc file latch ',
    '[KILLSW] mode=act KHONG co file latch => latch KHONG song qua restart',
    '[KILLSW] nap dinh equity ',
    '[KILLSW] nap file latch ',
    '[KILLSW] reset_peak: khong xoa duoc file dinh ',
    '[KILLSW] {} code={} mode=',
    "[KILLSW] {}='{}' khong hop le (can [{}, {}]) => dung mac dinh {}",
    "[KILLSW] {}='{}' khong hop le (can so nguyen [{}, {}]) => dung mac dinh {}",
    '[KILLSW] {}={} TRUNG file dinh so giay {} => dung {}',
    '[TS-EXT] BAT {}=1 profile=c3_shadow|c3_live baseH={} extH={} thr={} minN={} file={} days_loaded={}',
    '[TS-EXT] TAT: {}={} nhung profile on={} live={} (chi bat cho LIVE_PROFILE=c3_shadow|c3_live)',
    '[TS-EXT] cho nen 23:59 UTC ngay {} (since={}m)',
    '[TS-EXT] day {} sum_ew={} n_min={} src=aero',
    '[TS-EXT] defer-END {} age_h={} reason={} (keo dai {}h)',
    '[TS-EXT] defer-END {} age_h={} reason={} -> CUT time-stop (keo dai {}h)',
    '[TS-EXT] khong ghi duoc {}: {}',
    '[TS-EXT] khong nap duoc {}: {}',
    '[TS-EXT] khong tao duoc thu muc {}',
    '[TS-EXT] loi refresh: {}',
    '[TS-EXT] nap {} ngay tu {}',
    '[TS-EXT] ngay {} chi co {} phut EW (< {}) - giu trong RAM, khong ghi file',
    '[TS-EXT] {} la LEGACY - khong keo dai (time-stop nhu v11b)',
]

A1_PFX = sorted(['[C3-LIVE] cum ', '[C3-LIVE] SUBMIT ', '[C3-LIVE-TRAIL] ', '[C3-LIVE-FILL] ', '[C3-LIVE-BOOK] ', '[C3-LIVE-EXEC] ',
                 '[C3-LIVE-RECON] ', '[TS-EXT] ', '[KILLSW] '], key=len, reverse=True)


def _tpl_rx(t):
    return re.compile('^' + '.*?'.join(re.escape(p) for p in t.split('{}')))


OTHER_RX = [_tpl_rx(t) for t in OTHER_TPL]
PFX_FAM = dict((p, {'name': 'PFX:' + p.strip(), 'marker': p}) for p in A1_PFX)
DESC_FAMS = {'MKT', 'AIPASS', 'SKIPORD', 'DCAGRID'}     # E9: chi ho mo ta co dung sai 0,1 %
for _f in FAMS:
    _f['pfx'] = next((p for p in A1_PFX if (_f['pre'] or '').startswith(p)), None)
FAM_BY = {f['name']: f for f in FAMS}
GLOBAL_FAMS = {'BANNER', 'KS_HOURLY', 'C2WARN', 'MAINCLASS', 'RECON_H', 'EQWARN'}
# dem chuoi con (khong can parse), tuple = moi chuoi phai co
SUBS = [('ERROR', (' ERROR ',)), ('KHAN', ('KHAN',)), ('LECH_QTY', ('LECH QTY',)), ('VAN_LECH', ('van lech qty',)),
        ('CHAN_VAO', ('CHAN vao lenh',)), ('LEO_THANG', ('leo thang UNKNOWN',)),
        ('KHONG_KHOP', ('[C3-LIVE-EXEC]', ' KHONG khop')), ('E4130', ('(-4130)',)), ('E2021', ('(-2021',)),
        ('GUI_LAI', ('gui lai CUNG cid',)), ('UNKNOWN', ('=> UNKNOWN',)), ('TU_CHOI', ('TU CHOI',)),
        ('C2_WARN', ('[KILLSW] C2_WARN',)), ('LATCH', ('[KILLSW] LATCH',))]
TRIG = ('[C3-LIVE', '[TS-EXT]', '[KILLSW]', 'AI PASS [', 'SKIP ORDER [', '[LIVE-DCA-GRID]', 'Market level', 'MainClass: ',
        ' ERROR ', 'KHAN', 'TU CHOI', '=> UNKNOWN')


def classify(msg, lg):
    """-> (fam, match) | (fam, None) = khong parse | (None, None) = khong quan tam.
    T1/E9: dong bat dau bang tien to A1 ma khong khop ho nao va khong khop mau khac da biet (OTHER_TPL) => khong parse cua
    gia-ho 'PFX:<tien to>' (tinh vao moi ho co tien to do)."""
    first = None
    for f in FAMS:
        if f['pre'] is not None and not msg.startswith(f['pre']):
            continue
        ok = True
        for c in f['cont']:
            if c not in msg:
                ok = False
                break
        if not ok:
            continue
        if f['lg'] and not lg.endswith(f['lg']):
            continue
        m = f['rx'].search(msg)
        if m:
            return f, m
        if first is None:
            first = f
    if first is not None:
        return first, None
    for p in A1_PFX:
        if msg.startswith(p):
            for rx in OTHER_RX:
                if rx.match(msg):
                    return None, None
            return PFX_FAM[p], None
    return None, None


# ------------------------------------------------------------------ doc 1 ngay pull
class DayData(object):
    def __init__(self, d):
        self.D = d
        self.ok = False
        self.reason = ''
        self.lo = day_lo(d)
        self.hi = self.lo + DAY_MS
        self.horizon = self.lo
        self.events = []
        self.subs = dict((k, []) for k, _ in SUBS)
        self.parsed = {}
        self.unparsed = {}
        self.unparsed_ex = {}
        self.hours = [0] * 24
        self.files = []
        self.dup = 0
        self.nwin = 0


def scan_day(pull_root, d, cap, lookahead, gstore, seq):
    dd = DayData(d)
    base = os.path.join(pull_root, d.isoformat())
    if not os.path.isdir(base):
        dd.reason = 'thieu thu muc pull242/%s' % d
        return dd
    if not os.path.isfile(os.path.join(base, 'COMPLETE')):
        dd.reason = 'pull242/%s chua COMPLETE' % d
        return dd
    files = sorted(glob.glob(os.path.join(base, 'logs', 'full.log*.gz')))
    if not files:
        dd.reason = 'thieu pull242/%s/logs/full.log*.gz' % d
        return dd
    dd.files = [os.path.basename(p) for p in files]
    la_hi = min(cap, dd.hi + LOOKAHEAD_MS) if lookahead else min(cap, dd.hi)
    dstr = d.strftime('%d/%m/%Y')
    d1str = (d + dt.timedelta(days=1)).strftime('%d/%m/%Y')
    capkey = dt.datetime.fromtimestamp(cap / 1000.0, TZ7).strftime('%Y%m%d%H') if cap < FAR else '9999999999'
    seen = set() if len(files) > 1 else None
    last_t = None
    for p in files:
        try:
            fh = gzip.open(p, 'rt', encoding='utf-8', errors='replace')
        except OSError as e:
            dd.reason = 'khong mo duoc %s: %s' % (os.path.basename(p), e)
            return dd
        st = 0
        hh = 0
        try:
            for raw in fh:
                raw = raw.rstrip('\r\n')
                hdr = (len(raw) >= 24 and raw[2] == '/' and raw[5] == '/' and raw[13] == ':' and raw[19] == '.')
                if hdr:
                    key = raw[6:10] + raw[3:5] + raw[0:2] + raw[11:13]
                    if key > capkey:
                        st = -1
                        continue
                    try:
                        hh = int(raw[11:13])
                    except ValueError:
                        hdr = False
                    pre = raw[:10]
                    if pre == dstr:
                        st = 1 if hh >= 7 else 0
                    elif pre == d1str:
                        st = 1 if hh < 7 else 2
                    else:
                        st = 0
                elif st == -1:
                    continue
                if st == 2 and la_hi <= dd.hi:
                    continue
                if hdr and st == 1:
                    dd.hours[(hh - 7) % 24] += 1
                    dd.nwin += 1
                trig = False
                for x in TRIG:
                    if x in raw:
                        trig = True
                        break
                if not trig:
                    continue
                m = HDR.match(raw) if hdr else None
                t = None
                if m is not None:
                    t = hdr_ms(m)
                    if t >= cap:
                        continue
                    if st == 2 and t >= la_hi:
                        continue
                # bo dem chuoi con (chi cua so, ca dong noi tiep)
                if st == 1 or st == 2:
                    for kname, needles in SUBS:
                        ok = True
                        for nd in needles:
                            if nd not in raw:
                                ok = False
                                break
                        if ok:
                            dd.subs[kname].append((t, st == 2, raw))
                if m is None:
                    if st == 1:
                        for f in FAMS:
                            if f['marker'] in raw:
                                dd.unparsed[f['name']] = dd.unparsed.get(f['name'], 0) + 1
                                dd.unparsed_ex.setdefault(f['name'], san(raw))
                                break
                    continue
                msg = m.group(11)
                lg = m.group(10)
                f, fm = classify(msg, lg)
                if f is None:
                    continue
                if fm is None:
                    if st == 1:
                        dd.unparsed[f['name']] = dd.unparsed.get(f['name'], 0) + 1
                        dd.unparsed_ex.setdefault(f['name'], san(raw))
                    continue
                if f['name'] in GLOBAL_FAMS:
                    gk = (t, raw)
                    if gk not in gstore['seen']:
                        gstore['seen'].add(gk)
                        gstore.setdefault(f['name'], []).append({'t': t, 'g': fm.groups(), 'raw': raw, 'thr': m.group(9)})
                if st != 1 and st != 2:
                    continue
                if seen is not None:
                    if raw in seen:
                        dd.dup += 1
                        continue
                    seen.add(raw)
                if st == 1:
                    dd.parsed[f['name']] = dd.parsed.get(f['name'], 0) + 1
                seq[0] += 1
                dd.events.append({'t': t, 'f': f['name'], 'g': fm.groups(), 'thr': m.group(9), 'lvl': m.group(8),
                                  'raw': raw, 'la': st == 2, 'w': False, 'seq': seq[0]})
                if last_t is None or t > last_t:
                    last_t = t
        except (OSError, EOFError) as e:
            dd.reason = 'loi doc %s: %s' % (os.path.basename(p), e)
            return dd
        finally:
            fh.close()
    dd.horizon = min(la_hi, (last_t + 1) if last_t is not None else dd.lo)
    dd.ok = True
    return dd


def fam_bad(dd, names):
    """E9: ho dung cham co >= 1 dong khong parse trong cua so => ly do (KHONG_CHAM_DUOC); ho mo ta: dung sai 0,1 %."""
    keys = []
    for n in names:
        keys.append(n)
        f = FAM_BY.get(n)
        if f is not None and f.get('pfx'):
            keys.append('PFX:' + f['pfx'].strip())
    for n in dict.fromkeys(keys):
        u = dd.unparsed.get(n, 0)
        if u == 0:
            continue
        tot = u + dd.parsed.get(n, 0)
        if n in DESC_FAMS and u <= UNPARSED_MAX * tot:
            continue
        return 'dong %s khong parse duoc %d/%d (vd: %s)' % (n, u, tot, dd.unparsed_ex.get(n, ''))
    return None


# ------------------------------------------------------------------ trang thai cum (pass 1)
class Leg(object):
    __slots__ = ('cid', 'k', 'lvl', 't', 'dts', 'qty', 'st', 'avg', 'ref', 'tc', 'pxc', 'cl')

    def __init__(self, cid, k, lvl, t, dts, qty, cl):
        self.cid, self.k, self.lvl, self.t, self.dts, self.qty, self.cl = cid, k, lvl, t, dts, qty, cl
        self.st = 'P'
        self.avg = self.ref = self.tc = self.pxc = None


class Clu(object):
    def __init__(self, sym, t0, ev):
        self.sym, self.t0, self.ev0 = sym, t0, ev
        self.legs = {}
        self.phase = 0
        self.ph_armed = False
        self.ph_lastP = None
        self.active = None
        self.first_arm = None
        self.closing = False
        self.closed = None
        self.clos = []
        self.books = []
        self.sfils = []
        self.ts = []
        self.cancelled = False
        self.arm_ts = []
        self.rst_ts = []
        self.sfil_full = None

    def nconf(self):
        return sum(1 for l in self.legs.values() if l.st == 'C')

    def pending(self):
        return any(l.st == 'P' for l in self.legs.values())

    def conf_qty(self):
        s = Decimal(0)
        for l in self.legs.values():
            if l.st == 'C' and l.qty is not None:
                s += l.qty
        return s

    def leg_k(self, k):
        for l in self.legs.values():
            if l.k == k:
                return l
        return None


class State(object):
    def __init__(self):
        self.open = {}
        self.clusters = []
        self.cid2leg = {}
        self.buf_conf = {}
        self.conf_lines = {}
        self.end_lines = {}
        self.px_last = {}
        self.algo = {}
        self.by_f = {}
        self.last_closed = {}
        self.merged = set()


def run_state(events):
    S = State()
    for ev in events:
        f = ev['f']
        g = ev['g']
        t = ev['t']
        S.by_f.setdefault(f, []).append(ev)
        if f == 'SUBMIT':
            sym, lvl, cid = g[0], g[1], g[2]
            k = int(g[8])
            cl = S.open.get(sym)
            ev['holding_before'] = cl is not None
            ev['conf_before'] = cl.nconf() if cl else 0
            ev['prev_conf'] = False
            if k > 0 and cl is not None:
                pl = cl.leg_k(k - 1)
                ev['prev_conf'] = pl is not None and pl.st == 'C'
            if k == 0 and cl is None:
                cl = Clu(sym, t, ev)
                S.open[sym] = cl
                S.clusters.append(cl)
            ev['cl'] = cl
            leg = Leg(cid, k, lvl, t, int(g[4]) * 60000, dec(g[6]), cl)
            if cl is not None:
                cl.legs[cid] = leg
            S.cid2leg[cid] = leg
            ev['leg'] = leg
            for cev in S.buf_conf.pop(cid, []):
                _apply_conf(S, cev, leg)
        elif f in ('FILL_EXEC', 'FILL_STREAM'):
            cid = g[1]
            S.conf_lines.setdefault(cid, []).append(ev)
            leg = S.cid2leg.get(cid)
            if leg is None:
                S.buf_conf.setdefault(cid, []).append(ev)
            else:
                _apply_conf(S, ev, leg)
        elif f in ('LEG_END', 'EXEC_END'):
            cid = g[1] if f == 'LEG_END' else (g[0] or g[2])
            ev['cid'] = cid
            S.end_lines.setdefault(cid, []).append(ev)
            leg = S.cid2leg.get(cid)
            if leg is not None and leg.st == 'P':
                leg.st = 'X'
                cl = leg.cl
                if cl is not None and leg.k == 0 and cl.nconf() == 0 and S.open.get(cl.sym) is cl:
                    cl.cancelled = True
                    del S.open[cl.sym]
        elif f == 'PXCORR':
            S.px_last[g[1]] = flt(g[2])
            leg = S.cid2leg.get(g[1])
            if leg is not None:
                leg.pxc = flt(g[2])
        elif f == 'MERGED_ON':
            S.merged.add(g[0])
        elif f == 'MERGED_OFF':
            S.merged.discard(g[0])
        elif f == 'ARM':
            cl = S.open.get(g[0])
            ev['cl'] = cl
            ev['dup_arm'] = False
            ev['active_before'] = cl.active if cl else None
            if cl is not None:
                ev['dup_arm'] = cl.ph_armed
                cl.ph_armed = True
                cl.arm_ts.append(t)
                if cl.first_arm is None:
                    cl.first_arm = t
        elif f == 'STOP':
            cl = S.open.get(g[0])
            ev['cl'] = cl
            ev['armed'] = cl is not None and cl.first_arm is not None
            ev['P_prev'] = None
            if cl is not None:
                if g[1] in ('ARM', 'MOVE'):
                    ev['P_prev'] = cl.ph_lastP
                    cl.ph_lastP = dec(g[2])
                cl.active = g[3]
        elif f == 'RST':
            cl = S.open.get(g[0])
            ev['cl'] = cl
            if cl is not None:
                cl.rst_ts.append(t)
                cl.phase += 1
                cl.ph_armed = False
                cl.ph_lastP = None
                cl.active = None
        elif f == 'TS':
            cl = S.open.get(g[0])
            ev['cl'] = cl
            if cl is not None:
                cl.closing = True
                cl.ts.append(ev)
        elif f == 'SFIL':
            cl = S.open.get(g[0])
            ev['cl'] = cl
            ev['armed'] = cl is not None and cl.first_arm is not None
            if cl is not None:
                cl.closing = True
                cl.sfils.append(ev)
                sf = sum((dec(x['g'][1]) or Decimal(0)) for x in cl.sfils)
                if cl.sfil_full is None and cl.nconf() > 0 and sf >= cl.conf_qty():
                    cl.sfil_full = ev
                    ev['sfil_full'] = True
        elif f == 'BOOK':
            # E6: BOOK in cung luong closedOnExchange voi CLOS => cum dong tai BOOK neu CLOS chua toi
            cl = S.open.pop(g[0], None)
            if cl is not None:
                if cl.closed is None:
                    cl.closed = t
                S.last_closed[g[0]] = cl
            else:
                cl = S.last_closed.get(g[0])
            ev['cl'] = cl
            if cl is not None:
                cl.books.append(ev)
        elif f == 'CLOS':
            cl = S.open.pop(g[0], None)
            if cl is None:
                cl = S.last_closed.get(g[0])
            ev['cl'] = cl
            ev['armed'] = cl is not None and cl.first_arm is not None
            ev['active_cid'] = cl.active if cl else None
            if cl is not None:
                cl.clos.append(ev)
                if cl.closed is None:
                    cl.closed = t
                S.last_closed[g[0]] = cl
        elif f == 'RECON_H':
            n = 0
            for c in S.open.values():
                if c.nconf() > 0 and not c.pending() and not c.closing and c.sym not in S.merged:
                    n += 1
            ev['n_exp'] = n
        elif f == 'ALGO':
            S.algo.setdefault(g[1], []).append(ev)
    return S


def _apply_conf(S, ev, leg):
    g = ev['g']
    if leg.st != 'C':
        leg.st = 'C'
        leg.avg = flt(g[3])
        leg.ref = flt(g[4])
        leg.tc = ev['t']
        q = dec(g[2])
        if q is not None:
            leg.qty = q


# ------------------------------------------------------------------ ket qua 1 muc
def evrec(t, sym, why, raws):
    if isinstance(raws, (list, tuple)):
        raws = ' || '.join(san(r) for r in raws if r)
    else:
        raws = san(raws)
    return {'t': fmt(t), 'symbol': sym, 'ly_do': why, 'dong_log': raws}


class Item(object):
    def __init__(self, name):
        self.name = name
        self.n = 0
        self.viol = []
        self.kcd = []
        self.forced = None
        self.reason = ''
        self.extra = {}
        self.tags = set()
        self.bac_override = None

    def add(self, status, t=None, sym=None, why='', raws=None):
        self.n += 1
        if status == VP:
            self.viol.append(evrec(t, sym, why, raws))
        elif status == KCD:
            self.kcd.append(evrec(t, sym, why, raws))

    def force(self, status, reason):
        self.forced = status
        self.reason = reason

    def status(self):
        if self.forced:
            return self.forced
        if self.viol:
            return VP
        if self.kcd:
            return KCD
        if self.n == 0:
            return KCSK
        return DAT

    def to_json(self):
        st = self.status()
        d = {'trang_thai': st, 'mau': self.n, 'so_vi_pham': len(self.viol), 'so_khong_cham_duoc': len(self.kcd),
             'su_kien_vi_pham': self.viol[:MAX_LIST], 'su_kien_khong_cham_duoc': self.kcd[:MAX_LIST]}
        if self.reason:
            d['ly_do'] = self.reason
        if self.tags:
            d['nhan'] = sorted(self.tags)
        if self.extra:
            d['mo_ta'] = self.extra
        return d


def merge_status(sts):
    best = DAT
    for s in sts:
        if PRIO[s] > PRIO[best]:
            best = s
    return best


# ------------------------------------------------------------------ ngu canh cham
class Ctx(object):
    pass


def load_sel(pull_root, d):
    p = os.path.join(pull_root, d.isoformat(), 'dumps')
    files = sorted(glob.glob(os.path.join(p, 'sel_dump_*.csv.gz')))
    if not files:
        return None
    sel = {}
    for fp in files:
        with gzip.open(fp, 'rt', encoding='utf-8', errors='replace') as fh:
            head = None
            for line in fh:
                parts = line.rstrip('\r\n').split(',')
                if head is None:
                    head = parts
                    try:
                        it, isym, irk = head.index('ts'), head.index('symbol'), head.index('rank')
                    except ValueError:
                        return None
                    continue
                try:
                    sel.setdefault(int(parts[it]), {})[parts[isym]] = int(parts[irk])
                except (ValueError, IndexError):
                    continue
    return sel


def W(C, f):
    return [e for e in C.S.by_f.get(f, []) if e['w']]


def symidx(C, f, sym):
    k = (f, sym)
    r = C.sidx.get(k)
    if r is None:
        r = [e for e in C.S.by_f.get(f, []) if e['g'] and e['g'][0] == sym]
        C.sidx[k] = r
    return r


def state_guard(C, it, fams):
    bad = fam_bad(C.dd, fams)
    if bad:
        it.force(KCD, bad)
        return True
    if not C.state_ok:
        it.force(KCD, C.state_reason)
        return True
    return False


# ------------------------------------------------------------------ M-E0 (prereg 1.3)
def chk_ME0(C):
    it = Item('M-E0')
    if state_guard(C, it, ['SUBMIT', 'FILL_EXEC', 'FILL_STREAM', 'LEG_END', 'EXEC_END', 'MKT']):
        return it
    S = C.S
    bd_min = set()
    bd_sym = set()
    for e in S.by_f.get('MKT', []):
        g = e['g']
        if g[0] is not None and g[1] == 'BIG_DOWN':
            bd_min.add(g[0])
        if g[2] is not None and g[3] == 'BIG_DOWN':
            bd_sym.add((g[2], g[4]))
    for ev in W(C, 'SUBMIT'):
        g = ev['g']
        sym, lvl, cid, csym, bar, ck, k, t = g[0], g[1], g[2], g[3], int(g[4]), int(g[5]), int(g[8]), ev['t']
        dts = bar * 60000
        v, kc = [], []
        if csym != sym or ck != k:
            v.append('(a) cid khong khop symbol/legIdx')
        if not (dts + 60000 <= t <= dts + 180000):
            v.append('(a) dong log ngoai [dts+60s;dts+180s], dts=%s' % fmt(dts))
        if k == 0:
            if lvl == 'PREDICT_SYMBOL_TRADE':
                if C.sel is None:
                    kc.append('(b) thieu sel_dump')
                elif dts not in C.sel:
                    kc.append('(b) sel_dump khong co ts=dts')
                else:
                    r = C.sel[dts].get(sym)
                    if r is None or r > 24:
                        v.append('(b) sel_dump ts=dts rank=%s' % r)
            elif lvl == 'BIG_DOWN':
                ms = minute_str(dts)
                if ms not in bd_min and (ms, sym) not in bd_sym:
                    v.append('(b) khong co dong Market level BIG_DOWN cung phut')
            else:
                v.append('(b) level leg 0 = %s ngoai {PREDICT_SYMBOL_TRADE, BIG_DOWN}' % lvl)
            if ev['holding_before']:
                v.append('(c) leg 0 khi dang co cum mo cung symbol')
        dl = t + 300000
        confs = [e for e in S.conf_lines.get(cid, []) if dts <= e['t'] <= dl]
        ends = [e for e in S.end_lines.get(cid, []) if dts <= e['t'] <= dl]
        nn = len(confs) + len(ends)
        if nn > 1:
            v.append('(d) %d dong xac nhan + %d dong ket thuc trong 300 s' % (len(confs), len(ends)))
        elif dl > C.horizon:
            kc.append('(d) het du lieu truoc t+300 s')
        elif nn == 0:
            v.append('(d) khong co dong xac nhan khop / ket thuc trong 300 s')
        raws = [ev['raw']] + [e['raw'] for e in confs + ends]
        it.add(VP if v else (KCD if kc else DAT), t, sym, '; '.join(v + kc), raws)
    return it


# ------------------------------------------------------------------ M-I
def chk_I3(C):
    it = Item('I3')
    if state_guard(C, it, ['STOP', 'RST', 'CLOS', 'ARM']):
        return it
    tol = Decimal('0.999999999')
    for ev in W(C, 'STOP'):
        g = ev['g']
        if g[1] != 'MOVE':
            continue
        P, Pp = dec(g[2]), ev['P_prev']
        if ev['cl'] is None:
            it.add(VP, ev['t'], g[0], 'MOVE khong thuoc cum mo nao', ev['raw'])
        elif Pp is None:
            it.add(VP, ev['t'], g[0], 'MOVE khong co STOP truoc trong cung pha arm', ev['raw'])
        elif not (P > Pp and P * Decimal(1000) >= Pp * Decimal(1001) * tol):
            it.add(VP, ev['t'], g[0], 'P=%s khong >= P_truoc=%s + 1 tick va x1,001' % (P, Pp), ev['raw'])
        else:
            it.add(DAT)
    return it


def first_algo(C, cid, x, lo, hi):
    for a in C.S.algo.get(cid, []):
        if a['g'][2] == x and lo <= a['t'] <= hi:
            return a
    return None


def chk_I4(C):
    it = Item('I4')
    if state_guard(C, it, ['ARM', 'STOP', 'ALGO', 'CLOS', 'STOPERR', 'E4130']):
        return it
    hz = C.horizon
    for ev in W(C, 'ARM'):
        sym, t = ev['g'][0], ev['t']
        sarm = [e for e in symidx(C, 'STOP', sym) if e['g'][1] == 'ARM' and e['t'] >= t]
        ok = [e for e in sarm if e['t'] <= t + 61000]
        if ok:
            it.add(DAT)
            continue
        if t + 61000 > hz:
            it.add(KCD, t, sym, '(a) het du lieu truoc ARM+61 s', ev['raw'])
            continue
        nxt = sarm[0] if sarm else None
        errs = [e for e in symidx(C, 'STOPERR', sym) if e['t'] >= t and (nxt is None or e['t'] <= nxt['t'])]
        old = ev.get('active_before')
        if not errs:
            it.add(VP, t, sym, '(a) khong co STOP ARM trong 61 s', ev['raw'])
        elif old is None:
            it.add(VP, t, sym, '(a) qua 61 s (co loi dat stop) va khong co stop cu hieu luc', [ev['raw']] + [e['raw'] for e in errs[:3]])
        else:
            nn = first_algo(C, nxt['g'][3], 'NEW', nxt['t'] - 5000, FAR) if nxt else None
            lim = nn['t'] if nn else hz
            canc = first_algo(C, old, 'CANCELED', 0, lim)
            if canc:
                it.add(VP, t, sym, '(a) stop cu %s bi CANCELED truoc khi stop moi NEW' % old, [ev['raw'], canc['raw']])
            else:
                it.add(DAT)
    for ev in W(C, 'STOP'):
        g = ev['g']
        if g[1] not in ('ARM', 'MOVE'):
            continue
        t, cid = ev['t'], g[3]
        if first_algo(C, cid, 'NEW', t - 5000, t + 61000):
            it.add(DAT)
        elif t + 61000 > hz:
            it.add(KCD, t, g[0], '(b) het du lieu truoc STOP+61 s', ev['raw'])
        else:
            it.add(VP, t, g[0], '(b) cid %s khong co ALGO X=NEW trong [t-5s;t+61s]' % cid, ev['raw'])
        if g[5] != 'null':
            cl = ev['cl']
            tc = cl.closed if (cl is not None and cl.closed is not None and cl.closed <= hz) else None
            canc = first_algo(C, g[5], 'CANCELED', 0, tc if tc is not None else hz)
            if canc:
                it.add(DAT)
            elif tc is not None:
                it.add(VP, t, g[0], '(c) stop bi thay %s khong co ALGO X=CANCELED truoc CLOS' % g[5], ev['raw'])
            else:
                it.add(KCD, t, g[0], '(c) cum chua dong, chua thay CANCELED cua %s' % g[5], ev['raw'])
    for ev in W(C, 'CLOS'):
        if ev['g'][1] != 'TRAILING_STOP':
            continue
        # ERRATA1 E3: ALGO cua cid STOP cuoi truoc CLOS, X in {TRIGGERING, TRIGGERED}, trong [t_CLOS-61 s; t_CLOS+61 s]
        act = ev.get('active_cid')
        trig = None
        if act:
            trig = (first_algo(C, act, 'TRIGGERING', ev['t'] - 61000, ev['t'] + 61000)
                    or first_algo(C, act, 'TRIGGERED', ev['t'] - 61000, ev['t'] + 61000))
        if trig:
            it.add(DAT)
        elif act is not None and ev['t'] + 61000 > hz:
            it.add(KCD, ev['t'], ev['g'][0], '(d) het du lieu tim ALGO TRIGGERED', ev['raw'])
        else:
            it.add(VP, ev['t'], ev['g'][0], '(d) CLOS TRAILING_STOP khong co ALGO X=TRIGGERED cua stop dang hieu luc %s' % act, ev['raw'])
    for ev in W(C, 'E4130'):
        sym, t = ev['g'][0], ev['t']
        rep = [e for e in symidx(C, 'STOP', sym) if t < e['t'] <= t + 20000]
        if rep:
            it.add(DAT)
        elif t + 20000 > hz:
            it.add(KCD, t, sym, 'L-K: het du lieu truoc -4130+20 s', ev['raw'])
        else:
            it.add(VP, t, sym, 'L-K: -4130 khong co stop thay the trong 20 s', ev['raw'])
    return it


def chk_I8(C):
    it = Item('I8')
    if state_guard(C, it, ['ARM', 'STOP', 'SFIL', 'CLOS']):
        return it
    for ev in W(C, 'STOP'):
        if ev['g'][1] not in ('ARM', 'MOVE'):
            continue
        if ev['armed']:
            it.add(DAT)
        else:
            it.add(VP, ev['t'], ev['g'][0], 'STOP truoc dong ARM dau tien cua cum', ev['raw'])
    for ev in W(C, 'SFIL'):
        if ev['armed']:
            it.add(DAT)
        else:
            it.add(VP, ev['t'], ev['g'][0], 'SFIL truoc dong ARM dau tien cua cum', ev['raw'])
    for ev in W(C, 'CLOS'):
        r, sym = ev['g'][1], ev['g'][0]
        if ev['armed']:
            it.add(DAT)
        elif r in I8_TRAIL:
            it.add(VP, ev['t'], sym, 'CLOS %s truoc ARM' % r, ev['raw'])
        elif (r in I8_PRE_OK or r.startswith('FLATTEN') or (r == 'EXTERNAL' and sym in C.ext_noted)
              or (r == 'DELIST_SETTLE' and sym in C.delist_noted)):
            it.add(DAT)
        else:
            it.add(VP, ev['t'], sym, 'CLOS truoc ARM ly do %s khong thuoc tap cho phep' % r, ev['raw'])
    return it


def chk_I9(C, i3):
    it = Item('I9')
    if state_guard(C, it, ['ARM', 'STOP', 'RST', 'CLOS']):
        return it
    it.n += i3.n
    it.viol.extend(dict(v, ly_do='(a)=I3: ' + v['ly_do']) for v in i3.viol)
    it.kcd.extend(i3.kcd)
    if i3.forced:
        it.force(i3.forced, i3.reason)
    for ev in W(C, 'ARM'):
        g = ev['g']
        e, pk, sl = flt(g[1]), flt(g[3]), flt(g[4])
        if e is None or pk is None or sl is None:
            it.add(VP, ev['t'], g[0], '(b) truong ARM khong doc duoc', ev['raw'])
            continue
        F = trail_sl(e, pk)
        rel = abs(f32(sl) - F) / abs(F) if F else 1.0
        if rel > 1e-6:
            it.add(VP, ev['t'], g[0], '(b) SL=%s != F(peak)=%r (rel %.3g)' % (g[4], F, rel), ev['raw'])
        else:
            it.add(DAT)
        if ev.get('dup_arm'):
            it.add(VP, ev['t'], g[0], '(c) dong ARM lan 2 trong cung pha', ev['raw'])
        elif ev['cl'] is None:
            it.add(VP, ev['t'], g[0], '(c) ARM khong thuoc cum mo nao', ev['raw'])
    return it


def win_clusters(C):
    """Cum co su kien DONG trong cua so (E6): CLOS, BOOK, hoac SFIL lam tong qty SFIL >= qty cum. -> [(su kien dau, cum)]."""
    evs = [e for e in C.S.by_f.get('CLOS', []) + C.S.by_f.get('BOOK', []) + C.S.by_f.get('SFIL', [])
           if e['w'] and (e['f'] != 'SFIL' or e.get('sfil_full'))]
    evs.sort(key=lambda e: (e['t'], e['seq']))
    out, seen = [], set()
    for ev in evs:
        cl = ev.get('cl')
        key = id(cl) if cl is not None else ('none', ev['seq'])
        if key in seen:
            continue
        seen.add(key)
        out.append((ev, cl))
    return out


def chk_I10(C):
    it = Item('I10')
    if state_guard(C, it, ['CLOS', 'BOOK', 'SFIL']):
        return it
    hz = C.horizon
    for ev, cl in win_clusters(C):
        sym = ev['g'][0]
        if cl is None:
            it.add(VP, ev['t'], sym, 'su kien dong cum (%s) khong thuoc cum mo nao' % ev['f'], ev['raw'])
            continue
        v, kc = [], []
        clos, books = cl.clos, cl.books
        for b in books:   # E6: moi BOOK dung 1 CLOS cung symbol trong +-600 s
            n = [c for c in symidx(C, 'CLOS', sym) if abs(c['t'] - b['t']) <= 600000]
            if len(n) != 1:
                if not n and b['t'] + 600000 > hz:
                    kc.append('BOOK: het du lieu tim CLOS +600 s')
                else:
                    v.append('BOOK co %d dong CLOS trong +-600 s' % len(n))
        for c in clos:    # va nguoc lai
            n = [b for b in symidx(C, 'BOOK', sym) if abs(b['t'] - c['t']) <= 600000]
            if len(n) != 1:
                if not n and c['t'] + 600000 > hz:
                    kc.append('CLOS: het du lieu tim BOOK +600 s')
                else:
                    v.append('CLOS co %d dong BOOK trong +-600 s' % len(n))
        if cl.sfil_full is not None:
            sfe = cl.sfil_full
            n = [c for c in symidx(C, 'CLOS', sym) if abs(c['t'] - sfe['t']) <= 600000]
            if not n:
                if sfe['t'] + 600000 > hz:
                    kc.append('SFIL du qty: het du lieu tim CLOS 600 s')
                else:
                    v.append('SFIL du qty cum ma khong co CLOS trong 600 s')
        if len(clos) > 1:
            v.append('%d dong CLOS cho 1 cum' % len(clos))
        if len(books) > 1:
            v.append('%d dong BOOK cho 1 cum' % len(books))
        r = clos[0]['g'][1] if clos else (books[0]['g'][1] if books else None)
        if clos and books and books[0]['g'][1] != clos[0]['g'][1]:
            v.append('BOOK ly do=%s khac CLOS (%s)' % (books[0]['g'][1], clos[0]['g'][1]))
        if r is not None:
            if not (r in I10_CODE or r.startswith('FLATTEN')):
                v.append('ly do %s ngoai tap code' % r)
            if not (r in I10_OK or r.startswith('FLATTEN') or (r == 'EXTERNAL' and sym in C.ext_noted)
                    or (r == 'DELIST_SETTLE' and sym in C.delist_noted)):
                v.append('ly do %s khong thuoc tap DAT' % r)
            if r in DO_REASONS:
                it.tags.add('CLOS_' + r)
        raws = [e['raw'] for e in clos] + [e['raw'] for e in books] + ([cl.sfil_full['raw']] if cl.sfil_full else [])
        it.add(VP if v else (KCD if kc else DAT), ev['t'], sym, '; '.join(v + kc), raws)
    return it


def chk_I11(C):
    it = Item('I11')
    if state_guard(C, it, ['CLOS', 'RECON_H', 'RECON_LECH', 'RECON_VANLECH', 'LOPB', 'GOB']):
        return it
    S = C.S
    rec = sorted(S.by_f.get('RECON_H', []) + S.by_f.get('RECON_LECH', []) + S.by_f.get('RECON_VANLECH', []),
                 key=lambda e: (e['t'], e['seq']))
    rts = [e['t'] for e in rec]
    bad = [(t, raw) for (t, la, raw) in C.dd.subs['LEO_THANG'] + C.dd.subs['LECH_QTY'] if t is not None and not la]
    for ev, cl in win_clusters(C):
        sym, tc = ev['g'][0], ev['t']
        v, kc = [], []
        i = bisect.bisect_right(rts, tc)
        nxt = rec[i] if i < len(rec) else None
        raws = [ev['raw']]
        if nxt is None or nxt['t'] > C.horizon:
            kc.append('(a) chua co dong RECON hang gio sau CLOS trong du lieu')
        else:
            raws.append(nxt['raw'])
            if nxt['f'] != 'RECON_H' or 'LECH' in nxt['g'][2]:
                v.append('(a) dong RECON ke tiep khong phai HOURLY khop / co LECH')
            elif int(nxt['g'][0]) != nxt['n_exp']:
                v.append('(a) RECON n=%s != so cum mo theo log %d' % (nxt['g'][0], nxt['n_exp']))
        bb = [b for b in bad if tc <= b[0] <= tc + 24 * H]
        if bb:
            v.append('(b) %d dong leo thang UNKNOWN / LECH QTY trong 24 h sau CLOS' % len(bb))
            raws += [b[1] for b in bb[:3]]
        it.add(VP if v else (KCD if kc else DAT), tc, sym, '; '.join(v + kc), raws)
    # (b) mang sang: CLOS ngay truoc, 24 h phu vao ngay D
    for cl in S.clusters:
        if cl.closed is None or not (C.lo - 24 * H <= cl.closed < C.lo):
            continue
        bb = [b for b in bad if cl.closed <= b[0] <= cl.closed + 24 * H]
        it.add(VP if bb else DAT, cl.closed, cl.sym, '(b) mang sang tu CLOS ngay truoc' if bb else '',
               [b[1] for b in bb[:3]] if bb else None)
    # (c) lop B: cham vao ngay co han 2 h
    for ev in S.by_f.get('LOPB', []):
        dl = ev['t'] + 2 * H
        if not (C.lo <= dl < C.hi):
            continue
        sym = ev['g'][0]
        go = [e for e in symidx(C, 'GOB', sym) if ev['t'] < e['t'] <= dl]
        if go:
            it.add(DAT)
        elif dl > C.horizon:
            it.add(KCD, ev['t'], sym, '(c) het du lieu truoc han 2 h', ev['raw'])
        else:
            it.add(VP, ev['t'], sym, '(c) lop B khong co dong GO chan rieng symbol trong 2 h', ev['raw'])
    return it


def chk_I12(C):
    it = Item('I12')
    if state_guard(C, it, ['CLOS', 'BOOK', 'SFIL', 'VIAM']):
        return it
    for ev, cl in win_clusters(C):
        sym = ev['g'][0]
        if cl is None:
            it.add(VP, ev['t'], sym, 'su kien dong cum khong thuoc cum mo nao', ev['raw'])
            continue
        v, kc = [], []
        if len(cl.clos) > 1:
            v.append('(a) %d dong CLOS cho 1 cum' % len(cl.clos))
        if cl.clos:
            q_cl = dec(cl.clos[0]['g'][2])
        elif cl.books:
            q_cl = dec(cl.books[0]['g'][3])
        else:
            q_cl = cl.conf_qty()
        minleg = None
        for l in cl.legs.values():
            if l.st == 'C' and l.qty is not None and (minleg is None or l.qty < minleg):
                minleg = l.qty
        for b in cl.books:   # E11
            ex, q = dec(b['g'][5]), dec(b['g'][3])
            if ex is None or q is None:
                kc.append('(b) BOOK khong doc duoc qty')
            elif ex > q:
                if minleg is not None and ex > q + minleg:
                    v.append('(b) exitQty %s > qty %s + leg nho nhat %s' % (ex, q, minleg))
                else:
                    kc.append('(b) qty %s < exitQty %s <= qty + leg nho nhat: thieu stepSize (E11)' % (q, ex))
        sf = Decimal(0)
        for x in cl.sfils:
            y = dec(x['g'][1])
            if y is not None:
                sf += y
        if q_cl is not None and sf > q_cl:
            v.append('(d) tong qty SFIL %s > qty cum %s' % (sf, q_cl))
        raws = [e['raw'] for e in cl.clos] + [e['raw'] for e in cl.books] + [e['raw'] for e in cl.sfils]
        it.add(VP if v else (KCD if kc else DAT), ev['t'], sym, '; '.join(v + kc), raws)
    for ev in W(C, 'VIAM'):
        it.add(VP, ev['t'], ev['g'][0], '(c) dong vi the AM (short)', ev['raw'])
        it.tags.add('VI_THE_AM')
    return it


# ------------------------------------------------------------------ M-T (prereg muc 3)
def chk_MT(C):
    it = Item('M-T')
    if state_guard(C, it, ['SUBMIT', 'TS', 'CLOS', 'TSX_FLAG', 'TSX_DEFER', 'ARM']):
        return it
    S = C.S
    flags = S.by_f.get('TSX_FLAG', [])
    hz = C.horizon

    def flag_at(day_iso, t):
        best = None
        for e in flags:
            if e['g'][0] == day_iso and e['t'] <= t:
                best = e
        return best

    def fval(e):
        v = e['g'][1]
        return 'OFF' if v.startswith('NA') else v     # E13: NA(->OFF) = OFF

    def unarmed_at(cl, due):                          # E7
        arms = [a for a in cl.arm_ts if a <= due]
        if not arms:
            return True
        return any(arms[-1] < r <= due for r in cl.rst_ts)

    def pending_ok(t):
        u = dt.datetime.fromtimestamp(t / 1000.0, dt.timezone.utc)
        if u.hour == 0 and u.minute < 22:
            return True
        for b in C.banners:
            if 0 <= t - b['t'] <= 20 * 60000:
                return True
        return False

    def eval_A(cl, m, raws):
        tsl = [e for e in cl.ts if m - 2000 < e['t'] <= m + 120000]
        ctl = [e for e in cl.clos if e['g'][1] == 'TIME_STOP_168H' and e['t'] <= m + 600000]
        raws += [e['raw'] for e in tsl + ctl]
        if tsl and ctl:
            return DAT, ''
        if m + 600000 > hz:
            return KCD, '(A) het du lieu truoc moc+600 s'
        if not tsl:
            return VP, '(A) flag OFF: khong co dong TIME-STOP trong (moc-2s;moc+120s], moc=%s' % fmt(m)
        return VP, '(A) khong co CLOS TIME_STOP_168H <= moc+600 s'

    def next_off(after, upto):
        for e in flags:
            if after < e['t'] <= upto and fval(e) == 'OFF' and e['g'][0] == utc_day(e['t']):
                return e['t']
        return None

    def eval_B(cl, m, raws):
        defs = [e for e in symidx(C, 'TSX_DEFER', cl.sym) if e['thr'] == 'C3LIVE-OPS' and m - 2000 < e['t'] <= m + 120000]
        raws += [e['raw'] for e in defs]
        moc = min(x for x in (next_off(m, min(hz, C.hi)), cl.t0 + 504 * H) if x is not None)
        early = [e for e in cl.ts + [c for c in cl.clos if c['g'][1] == 'TIME_STOP_168H']
                 if m - 2000 < e['t'] < moc - 2000 and e['t'] <= hz]
        if early:
            raws += [e['raw'] for e in early]
            return VP, '(B) flag ON/PENDING nhung co TIME-STOP/CLOS truoc khi doi OFF / 504 h'
        if not defs:
            if m + 120000 > hz:
                return KCD, '(B) het du lieu truoc moc+120 s'
            return VP, '(B) flag ON/PENDING nhung khong co defer-START [C3LIVE-OPS] trong (due-2s;due+120s]'
        if C.lo <= moc < C.hi:
            return eval_A(cl, moc, raws)
        return DAT, ''

    def eval_at(cl, m):
        raws = [cl.ev0['raw']]
        fe = flag_at(utc_day(m), m + 120000)
        fl = fval(fe) if fe else None
        if fe:
            raws.append(fe['raw'])
        if fl is None:
            mode = 'B' if pending_ok(m) else 'A'
        elif fl == 'OFF':
            mode = 'A'
        elif fl == 'ON':
            mode = 'B'
        elif fl == 'PENDING':
            if not pending_ok(m):
                return VP, 'flag PENDING ngoai cua so hop le', raws
            mode = 'B'
        else:
            return KCD, 'flag=%s (khong phai ON/OFF)' % fl, raws
        st, why = eval_A(cl, m, raws) if mode == 'A' else eval_B(cl, m, raws)
        return st, why, raws

    for cl in S.clusters:
        if cl.cancelled:
            continue
        due = cl.t0 + 168 * H
        if due >= C.hi:
            continue
        if not unarmed_at(cl, due):
            continue
        for e in cl.ts + [c for c in cl.clos if c['g'][1] == 'TIME_STOP_168H']:
            if e['w'] and e['t'] <= due - 2000:
                it.add(VP, e['t'], cl.sym, 'TIME-STOP / CLOS TIME_STOP_168H som hon due-2s (due=%s)' % fmt(due), e['raw'])
        if cl.closed is not None and cl.closed <= due - 2000:
            continue
        if C.lo <= due < C.hi:
            st, why, raws = eval_at(cl, due)
            it.add(st, due, cl.sym, why, raws)
        elif due < C.lo and (cl.closed is None or cl.closed >= C.lo):
            # dang hoan tu ngay truoc: moc moi (doi OFF / 504 h) roi vao ngay D, hoac dong trong ngay D
            moc = min(x for x in (next_off(C.lo - 1, min(hz, C.hi)), cl.t0 + 504 * H) if x is not None)
            raws = [cl.ev0['raw']]
            early = [e for e in cl.ts + [c for c in cl.clos if c['g'][1] == 'TIME_STOP_168H']
                     if e['w'] and e['t'] < moc - 2000]
            if early:
                it.add(VP, early[0]['t'], cl.sym, '(B) dong khi chua doi OFF / chua 504 h', raws + [e['raw'] for e in early])
            elif C.lo <= moc < C.hi:
                st, why = eval_A(cl, moc, raws)
                it.add(st, moc, cl.sym, why, raws)
    return it


# ------------------------------------------------------------------ M-D D1 (prereg muc 4)
def chk_D1(C):
    it = Item('D1')
    if state_guard(C, it, ['SUBMIT', 'FILL_EXEC', 'FILL_STREAM', 'AIPASS', 'DCAGRID', 'PXCORR']):
        return it
    xs = []
    for ev in W(C, 'SUBMIT'):
        g = ev['g']
        if g[1] != 'DCA_LEVEL1':
            continue
        sym, k, t, dts = g[0], int(g[8]), ev['t'], int(g[4]) * 60000
        cl, leg = ev['cl'], ev['leg']
        v, kc = [], []
        raws = [ev['raw']]
        if cl is None:
            it.add(VP, t, sym, 'leg DCA khi khong co cum dang giu', raws)
            continue
        if not (1 <= k <= 3) or k != ev['conf_before']:
            v.append('(b) legIdx=%d, so leg da xac nhan khop=%d' % (k, ev['conf_before']))
        if not ev['prev_conf']:
            v.append('(d) leg truoc chua xac nhan khop')
        l0 = cl.leg_k(0)
        avg0 = None
        if l0 is not None and l0.st == 'C':
            avg0 = l0.pxc if l0.pxc is not None else l0.avg
        if avg0 is None:
            v.append('(a) leg 0 chua xac nhan khop (khong co avg)')
        elif leg.st == 'X':
            pass    # E8: leg DCA ket thuc khong khop => (a) khong ap dung, khong KCD
        elif leg.ref is None:
            if leg.st == 'P' and t + 300000 > C.horizon:
                kc.append('(a) chua co dong xac nhan leg DCA (het du lieu)')
            else:
                kc.append('(a) leg DCA khong co dong xac nhan => khong co ref')
        elif 1 <= k <= 3:
            r = leg.ref / avg0 - 1.0
            if not (r <= LEVELS[k - 1] + 1e-6):
                v.append('(a) ref/avg0-1=%.6f > level[%d]=%s' % (r, k - 1, LEVELS[k - 1]))
        grid = []
        for e in C.S.by_f.get('DCAGRID', []):
            if dts + 60000 <= e['t'] <= t:
                gg = e['g']
                if (gg[1] is not None and sym in [x.strip() for x in gg[1].split(',')]) or gg[2] == sym:
                    grid.append(e)
        if not grid:
            v.append('(c) khong co dong [LIVE-DCA-GRID] site= due=/live-only due= co symbol trong [dts+60s;t_SUBMIT]')
        else:
            raws.append(grid[0]['raw'])
        ps = [e for e in symidx(C, 'AIPASS', sym) if dts + 60000 <= e['t'] <= t and e['g'][2] == 'null'
              and e['g'][1].startswith('PERFECT: 15M(')]
        if not ps:
            v.append('(e) khong co dong AI PASS ... PERFECT: 15M(x%) symbolPred: null trong [dts+60s;t_SUBMIT]')
        else:
            raws.append(ps[-1]['raw'])
            mm = re.search(r'15M\(([-0-9.]+)%\)', ps[-1]['g'][1])
            if mm:
                xs.append({'t': fmt(t), 'symbol': sym, 'legIdx': k, 'x_15M_pct': flt(mm.group(1))})
        it.add(VP if v else (KCD if kc else DAT), t, sym, '; '.join(v + kc), raws)
    it.extra['gia_tri_15M_leg_DCA'] = xs
    rej = [e for e in C.S.by_f.get('SKIPORD', []) if e['w'] and e['g'][1] == 'DCA_LEVEL1'
           and e['g'][2].startswith('AI REJECT')]
    it.extra['so_dong_SKIP_ORDER_DCA_REJECT'] = len(rej)
    if rej:
        it.extra['dong_REJECT_dau_tien'] = san(rej[0]['raw'])
    return it


# ------------------------------------------------------------------ M-S muc cung (prereg muc 5)
def banner_at(C, t):
    i = bisect.bisect_right(C.banner_ts, t) - 1
    return (i, C.banners[i]) if i >= 0 else (-1, None)


def chk_MS(C):
    """ERRATA1 E1/E5: S1 r_cap, S2 r_hi, S3 r_lo (VANG EQ_DUOI), S4 notional, S5/S6 KCD_CAU_TRUC, S7 b, S8 legIdx, S9 U."""
    it = Item('M-S')
    if state_guard(C, it, ['SUBMIT', 'KS_HOURLY', 'BANNER', 'EQWARN']):
        return it
    ks = C.gstore.get('KS_HOURLY', [])
    eqw = [e['t'] for e in C.gstore.get('EQWARN', [])]
    rdist = []
    tags = set()
    hard = 0
    s1b = 0

    def tier(r):
        return abs(r - 1.2) <= 0.02 or abs(r - 0.5) <= 0.02
    for ev in W(C, 'SUBMIT'):
        g = ev['g']
        sym, t, k = g[0], ev['t'], int(g[8])
        q, b, n, u = dec(g[6]), flt(g[7]), dec(g[9]), flt(g[10])
        ji, bn = banner_at(C, t)
        raws = [ev['raw']]
        if bn is None:
            it.add(KCD, t, sym, 'khong tim thay banner khoi dong JVM dang chay (C3_CAPITAL)', raws)
            continue
        cap = flt(bn['g'][2])
        if b is None or u is None or q is None or n is None or cap is None:
            it.add(KCD, t, sym, 'truong SUBMIT/banner khong doc duoc', raws)
            continue
        v, kc, tg = [], [], []
        if u >= 0.6:
            v.append('(S9) U_before=%s >= 0,6 ma van SUBMIT' % g[10])
        else:
            c_ng = b / (0.0225 * (1.0 - u / 0.6))
            rcap = c_ng / cap
            rdist.append(rcap - 1.0)
            if rcap > 1.2 * (1 + 1e-6):                    # ERRATA2 F2
                v.append('(S1) r_cap=%.6f > 1,2 x (1+1e-6)' % rcap)
            elif rcap > 1 + 1e-6:
                tg.append('TIER')
                s1b += 1
                ev['_s1b'] = '(S1b) r_cap=%.6f trong (1+1e-6 ; 1,2 x (1+1e-6)]' % rcap
            same = [x for x in ks if bisect.bisect_right(C.banner_ts, x['t']) - 1 == ji]
            prev = [x for x in same if x['t'] <= t]
            nxt = [x for x in same if t < x['t'] <= C.horizon]
            br = ([prev[-1]] if prev else []) + ([nxt[0]] if nxt else [])
            eqs = [flt(x['g'][1]) for x in br if flt(x['g'][1]) is not None]
            if not eqs:
                kc.append('(S2)(S3) khong co dong [KILLSW] HOURLY cung JVM bao quanh')
            else:
                r_hi = c_ng / min(cap, max(eqs))
                r_lo = c_ng / min(cap, min(eqs))
                if r_hi > 1.02:
                    if tier(r_hi):
                        tg.append('TIER')
                    else:
                        v.append('(S2) r_hi=%.6f > 1,02' % r_hi)
                if r_lo < 0.98:
                    if tier(r_lo):
                        tg.append('TIER')
                    elif any(t - 24 * H <= x <= t for x in eqw):
                        tg.append('AVAIL')
                    else:
                        tg.append('EQ_DUOI')
        if float(n) > b * (1 + 1e-9):
            v.append('(S4) notional > budget')
        if b > 0.045 * cap * 1.2 or b < 5 * 0.5:
            v.append('(S7) budget ngoai [2,5 ; 0,045 x C3_CAPITAL x 1,2]')
        if k == 0 and ev['holding_before']:
            v.append('(S8) leg 0 khi dang giu')
        if k > 0 and k != ev['conf_before']:
            v.append('(S8) DCA legIdx=%d != legCount=%d' % (k, ev['conf_before']))
        if v or tg:
            it.add(VP, t, sym, '; '.join(v + ([ev['_s1b']] if ev.get('_s1b') else []) + (['VANG ' + '/'.join(tg)] if tg else [])), raws)
            if tg:
                it.viol[-1]['nhan'] = tg
                tags.update(tg)
            if v:
                hard += 1
                it.viol[-1]['cung'] = True
        elif kc:
            it.add(KCD, t, sym, '; '.join(kc), raws)
        else:
            it.add(DAT)
    it.tags.update(tags)
    it.extra['hard_VI_PHAM'] = hard
    it.extra['so_leg_S1b_TIER'] = s1b
    it.extra['S5_S6'] = KCDC + ' (R3: chua co quy trinh chep exchangeInfo hang ngay)'
    it.extra['theo_doi_C_ngam_tren_C3CAP_tru_1'] = (
        {'n': len(rdist), 'min': min(rdist), 'median': median(rdist), 'max': max(rdist)} if rdist else {'n': 0})
    it.extra['theo_doi_L_S_L_S2'] = KCDC + ' (' + KCDC_TOOL + ')'
    return it


# ------------------------------------------------------------------ M-X (prereg muc 6)
def chk_MX(C):
    it = Item('M-X')
    bad = fam_bad(C.dd, ['FILL_EXEC', 'FILL_STREAM', 'SFIL', 'C2WARN', 'PXCORR', 'TS', 'BOOK'])
    if bad:
        it.force(KCD, bad)
        return it
    S = C.S
    c2w, c2s, src = 0.017, 0.025, 'mac dinh code (CHUA XAC NHAN, chua co dong C2_WARN)'
    cw = sorted(C.gstore.get('C2WARN', []), key=lambda e: e['t'])
    if cw:
        c2w, c2s = flt(cw[0]['g'][3]), flt(cw[0]['g'][4])
        src = 'dong [KILLSW] C2_WARN dau tien %s' % fmt(cw[0]['t'])
    allslip = []
    seen = set()
    for e in sorted(S.by_f.get('FILL_EXEC', []) + S.by_f.get('FILL_STREAM', []), key=lambda x: (x['t'], x['seq'])):
        cid = e['g'][1]
        if cid in seen or e['la']:
            continue
        seen.add(cid)
        avg, ref = flt(e['g'][3]), flt(e['g'][4])
        px = S.px_last.get(cid)
        if px is not None:
            avg = px
        if avg is None or not ref:
            continue
        allslip.append((e['t'], avg / ref - 1.0, e))
    day = [x for x in allslip if x[2]['w']]
    cum0 = ms_local(MX_CUM_START)
    cum = [x[1] for x in allslip if cum0 <= x[0] < C.hi]
    big = [x for x in allslip if x[1] > c2s]
    vang = []
    for x in day:
        it.add(DAT)
        if x[1] > c2w:
            vang.append(evrec(x[0], x[2]['g'][0], 's_in=%.5f > c2Warn %.4f' % (x[1], c2w), x[2]['raw']))
    for x in day:
        if x[1] > c2s:
            win = [y for y in big if x[0] - 24 * H <= y[0] <= x[0]]
            if len(win) >= 2:
                vang.append(evrec(x[0], x[2]['g'][0], '>= 2 su kien s_in > c2Slip trong 24 h truot (%d)' % len(win), x[2]['raw']))
    mc = median(cum)
    if len(cum) >= 10 and mc is not None and mc > 0.003:
        vang.append(evrec(None, None, 'median s_in luy ke %.1f bps > 30 bps (n=%d) => bao owner g_exec' % (mc * 1e4, len(cum)), None))
        it.n += 1
    it.viol.extend(vang)
    ds = [x[1] for x in day]
    tr = [flt(e['g'][4]) for e in S.by_f.get('SFIL', []) if e['w'] and flt(e['g'][4]) is not None]
    tso = []
    for e in S.by_f.get('TS', []):
        cl = e.get('cl')
        if e['w'] and cl is not None and cl.books:
            ea = re.search(r'exitAvg=(\S+)', cl.books[-1]['raw'])
            px = flt(e['g'][2])
            if ea and px:
                tso.append(1.0 - flt(ea.group(1)) / px)

    def stat(v):
        if not v:
            return {'n': 0}
        return {'n': len(v), 'median_bps': median(v) * 1e4, 'p90_bps': pct(v, 0.9) * 1e4, 'max_bps': max(v) * 1e4}
    it.extra = {
        'nguong': {'c2Warn': c2w, 'c2Slip': c2s, 'nguon': src},
        'truot_vao_ngay': stat(ds), 'truot_vao_luy_ke_tu_2026-11-24': stat(cum),
        'so_leg_s_in_gt_0.017': sum(1 for v in ds if v > 0.017), 'so_leg_s_in_gt_0.025': sum(1 for v in ds if v > 0.025),
        'so_su_kien_gt_c2Slip_24h_truot_max': max([len([y for y in big if x[0] - 24 * H <= y[0] <= x[0]]) for x in day] or [0]),
        'truot_ra_trailing': stat(tr), 'truot_ra_time_stop': stat(tso),
        'dem': dict((k, sum(1 for (t, la, r) in C.dd.subs[k] if not la)) for k in
                    ('KHONG_KHOP', 'E4130', 'E2021', 'GUI_LAI', 'UNKNOWN', 'TU_CHOI', 'C2_WARN', 'LATCH')),
    }
    return it


# ------------------------------------------------------------------ M-K (prereg muc 8)
def exp_cap(C, t):
    if C.D < PILOT_DAY:
        return 1000.0
    if C.D > PILOT_DAY:
        return 5000.0
    return 5000.0 if (C.pilot_on is not None and t >= C.pilot_on) else 1000.0


def down_hours(C):
    return sum(1 for x in C.dd.hours if x == 0)


def chk_K1(C):
    it = Item('K1')
    bad = fam_bad(C.dd, ['BANNER', 'RECOV', 'RECON_START', 'MAINCLASS'])
    if bad:
        it.force(KCD, bad)
        return it
    bns = [b for b in C.banners if C.lo <= b['t'] < C.hi]
    if C.D == PILOT_DAY and C.pilot_on is None:
        it.force(KCD, 'ngay 2026-11-26 thieu --pilot-on-start (khung owner)')
        return it
    S = C.S
    for i, b in enumerate(bns):
        g = b['g']
        v = []
        if C.D == PILOT_DAY:
            if not (C.pilot_on <= b['t'] <= C.pilot_on + H):
                v.append('restart ngoai khung owner [pilot_on; +60 phut]')
        else:
            v.append('co banner khoi dong JVM (restart) trong ngay D')
        if g[0] != 'LIVE':
            v.append('adapter=%s' % g[0])
        if flt(g[2]) != exp_cap(C, b['t']):
            v.append('c3_capital=%s != %s' % (g[2], exp_cap(C, b['t'])))
        if g[3] != 'true' or g[4] != 'true':
            v.append('killSwitchArmed=%s X14=%s' % (g[3], g[4]))
        nb = bns[i + 1]['t'] if i + 1 < len(bns) else FAR
        rs = [e for e in S.by_f.get('RECON_START', []) if b['t'] <= e['t'] < nb and e['g'][0] == 'XONG']
        rv = [e for e in S.by_f.get('RECOV', []) if b['t'] - 60000 <= e['t'] < nb and e['g'][0] == '0']
        if not rs:
            v.append('khong co "reconcile khoi dong XONG" sau banner')
        if not rv:
            v.append('khong co "khoi phuc sau restart: con 0 leg treo"')
        it.add(VP if v else DAT, b['t'], None, '; '.join(v), b['raw'])
    if C.D == PILOT_DAY:
        if not any(C.pilot_on <= b['t'] <= C.pilot_on + H for b in bns):
            it.add(VP, C.pilot_on, None, 'ngay 26/11: khong co restart trong khung owner', None)
    elif not bns:
        it.add(DAT)
    return it


def chk_K3(C):
    it = Item('K3')
    bad = fam_bad(C.dd, ['RECON_H', 'RECON_LECH', 'RECON_VANLECH', 'BANNER'])
    if bad:
        it.force(KCD, bad)
        return it
    allr = sorted(C.gstore.get('RECON_H', []), key=lambda e: e['t'])
    win = [e for e in allr if C.lo <= e['t'] < C.hi]
    need = max(0, 23 - down_hours(C))
    it.add(VP if len(win) < need else DAT, C.lo, None,
           'chi %d dong HOURLY khop < %d' % (len(win), need) if len(win) < need else '', None)
    for e in win:
        i = allr.index(e)
        prev = allr[i - 1] if i > 0 else None
        s = int(e['g'][3])
        if prev is None:
            it.add(KCD, e['t'], None, 'khong co dong RECON truoc de so streak', e['raw'])
            continue
        if any(prev['t'] < b['t'] <= e['t'] for b in C.banners):
            okk, exp = (s == 1), 1
        else:
            okk, exp = (s == int(prev['g'][3]) + 1), int(prev['g'][3]) + 1
        if okk:
            it.add(DAT)
        else:
            it.add(VP, e['t'], None, 'streak=%d, ky vong %d (tang dung 1 / ve 1 sau restart)' % (s, exp), [prev['raw'], e['raw']])
    for kname in ('LECH_QTY', 'VAN_LECH', 'CHAN_VAO', 'LEO_THANG'):
        for (t, la, raw) in C.dd.subs[kname]:
            if not la:
                it.add(VP, t, None, 'dong "%s"' % kname, raw)
    return it


def chk_K4(C):
    it = Item('K4')
    bad = fam_bad(C.dd, ['TSX_FLAG', 'TSX_STATUS', 'TSX_NOFLAG'])
    if bad:
        it.force(KCD, bad)
        return it
    S = C.S
    dday = C.D.isoformat()
    bns = [b['t'] for b in C.banners if C.lo <= b['t'] < C.hi]
    fl = [e for e in S.by_f.get('TSX_FLAG', []) if e['w'] and e['g'][0] == dday]
    okf = [e for e in fl if e['g'][1] in ('ON', 'OFF') and (e['t'] < C.lo + 25 * 60000 or any(e['t'] > b for b in bns))]
    it.add(DAT if okf else VP, C.lo, None, '' if okf else 'khong co dong [TS-EXT] flag day=%s flag=(ON|OFF) hop le' % dday,
           fl[0]['raw'] if fl else None)
    it.extra['flag'] = okf[0]['g'][1] if okf else None
    for e in S.by_f.get('TSX_NOFLAG', []):
        if e['w']:
            it.add(VP, e['t'], None, 'dong "[TS-EXT] chua co co ngay"', e['raw'])
    nst = sum(1 for e in S.by_f.get('TSX_STATUS', []) if e['w'])
    need = max(0, 23 - down_hours(C))
    it.add(DAT if nst >= need else VP, C.lo, None, '' if nst >= need else 'chi %d dong [TS-EXT] status < %d' % (nst, need), None)
    it.extra['so_dong_status'] = nst
    return it


def chk_K5(C):
    it = Item('K5')
    p = os.path.join(C.pull_root, C.D.isoformat(), 'check.txt')
    if not os.path.isfile(p):
        it.force(KCD, 'thieu check.txt')
        return it
    kv = {}
    with open(p, encoding='utf-8', errors='replace') as fh:
        for line in fh:
            line = line.rstrip('\r\n')
            if '=' in line:
                a, b = line.split('=', 1)
                kv[a.strip()] = b.strip()
    v = []
    st = kv.get('STATUS')
    nb = len([b for b in C.banners if C.lo <= b['t'] < C.hi])
    if C.D == PILOT_DAY and st == 'INCOMPLETE':
        allowed = ('feat_minutes', 'sel_minutes', 'psym_feat_minutes', 'psym_pred_minutes')
        for part in [x for x in kv.get('fails', '').split(';') if x.strip()]:
            name, _, val = part.partition('=')
            name = name.strip()
            try:
                num = int(val.split('/')[0])
            except ValueError:
                num = -1
            if name not in allowed:
                v.append('fails ngoai danh sach chap nhan: %s' % part)
            elif num < 1440 - 20 * nb:
                v.append('%s=%s < 1440 - 20 x %d' % (name, val, nb))
        try:
            if int(kv.get('log_max_gap_min', '999')) > 15:
                v.append('log_max_gap_min=%s > 15' % kv.get('log_max_gap_min'))
        except ValueError:
            v.append('log_max_gap_min khong doc duoc')
    else:
        if st != 'OK':
            v.append('STATUS=%s' % st)
        if kv.get('fails', None) != '':
            v.append('fails=%s' % kv.get('fails'))
    for kname in ('missing', 'errors'):
        if kv.get(kname, None) != '':
            v.append('%s=%s' % (kname, kv.get(kname)))
    if kv.get('log_minutes') != '1440':
        v.append('log_minutes=%s' % kv.get('log_minutes'))
    it.add(VP if v else DAT, C.lo, None, '; '.join(v), None)
    return it


def chk_K6(C):
    it = Item('K6')
    bad = fam_bad(C.dd, ['LATCH'])
    if bad:
        it.force(KCD, bad)
        return it
    dd = C.dd
    ne = [(t, r) for (t, la, r) in dd.subs['ERROR'] if not la]
    nk = [(t, r) for (t, la, r) in dd.subs['KHAN'] if not la]
    nl = [(t, r) for (t, la, r) in dd.subs['LATCH'] if not la]
    it.add(DAT if not ne else VP, C.lo, None, '' if not ne else '%d dong " ERROR "' % len(ne), [r for _, r in ne[:3]])
    it.add(DAT if not nk else VP, C.lo, None, '' if not nk else '%d dong chua "KHAN"' % len(nk), [r for _, r in nk[:3]])
    it.add(DAT if not nl else VP, C.lo, None, '' if not nl else '%d dong "[KILLSW] LATCH"' % len(nl), [r for _, r in nl[:3]])
    for e in C.S.by_f.get('LATCH', []):
        if not e['w']:
            continue
        code = e['g'][1] or e['g'][2]
        it.tags.add('LATCH_FLATTEN' if code in ('C6', 'A40') else 'LATCH_NO_NEW_ENTRY')
    it.extra = {'ERROR': len(ne), 'KHAN': len(nk), 'LATCH': len(nl)}
    return it


TT = re.compile(r'^\[(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)\] TOM TAT: (.*)$')


def parse_tt(body):
    i = body.find('khan_canh_bao=')
    kcb = body[i + len('khan_canh_bao='):].strip() if i >= 0 else None
    head = body[:i] if i >= 0 else body
    kv = {}
    for tok in head.split():
        if '=' in tok:
            a, b = tok.split('=', 1)
            kv[a] = b
    kv['khan_canh_bao'] = kcb
    return kv


def read_cron(C):
    """Doc golive_monitor_cron.log.1 roi .log (E2); bo moi dong >= --max-ts truoc khi parse. -> (dong TOM TAT, t_cuoi, so khong parse)."""
    caps = fmt(C.cap)[:19] if C.cap < FAR else '9999'
    rows, seen, last, unp = [], set(), None, 0
    for p in (C.cron + '.1', C.cron):
        if not os.path.isfile(p):
            continue
        with open(p, encoding='utf-8', errors='replace') as fh:
            for raw in fh:
                if not raw.startswith('[20') or len(raw) < 21:
                    continue
                ts = raw[1:20]
                if ts >= caps:
                    continue
                try:
                    t = ms_local(ts)
                except ValueError:
                    continue
                if last is None or t > last:
                    last = t
                if 'TOM TAT:' not in raw:
                    continue
                raw = raw.rstrip('\r\n')
                if raw in seen:
                    continue
                seen.add(raw)
                m = TT.match(raw)
                if not m:
                    if C.lo <= t < C.hi:
                        unp += 1
                    continue
                rows.append((t, parse_tt(m.group(2)), raw))
    rows.sort(key=lambda x: x[0])
    return rows, last, unp


def chk_K2(C):
    """ERRATA1 E2: chi xet dong TOM TAT HOP LE (adapter va C3_CAPITAL khong rong) cho (a)(c)(d); (b) moi dong."""
    it = Item('K2')
    if C.D == PILOT_DAY and C.pilot_on is None:
        it.force(KCD, 'ngay 2026-11-26 thieu --pilot-on-start')
        return it
    if not os.path.isfile(C.cron):
        it.force(KCD, 'thieu cron log monitor')
        return it
    rows, last, unp = read_cron(C)
    win = [x for x in rows if C.lo <= x[0] < C.hi]
    if unp and unp > UNPARSED_MAX * (unp + len(win)):
        it.force(KCD, 'dong TOM TAT khong parse duoc %d/%d' % (unp, unp + len(win)))
        return it

    def valid(kv):
        return bool(kv.get('adapter')) and bool(kv.get('C3_CAPITAL'))
    ex_lo = ex_hi = None
    if C.D == PILOT_DAY:
        ex_lo = C.pilot_on
        ex_hi = C.pilot_on + H
        back = [x for x in win if x[0] >= ex_lo and valid(x[1]) and x[1].get('push') == 'ON'
                and flt(x[1].get('C3_CAPITAL')) == 5000.0]
        if back and back[0][0] <= ex_lo + H:
            ex_hi = back[0][0]
        else:
            it.add(VP, ex_lo, None, 'ngay 26/11: qua 60 phut sau pilot_on chua co TOM TAT push=ON va C3_CAPITAL=5000', None)

    def exempt(t):
        if ex_lo is not None and ex_lo <= t < ex_hi:
            return True
        return C.drain is not None and C.drain[0] <= t <= C.drain[1]

    def overl(a, b):
        if ex_lo is not None and a < ex_hi and b > ex_lo:
            return True
        return C.drain is not None and a < C.drain[1] and b > C.drain[0]
    pre = [x for x in rows if x[0] < C.lo and valid(x[1])]
    pv = pre[-1] if pre else None
    invalid = 0
    latch_bad = False
    for (t, kv, raw) in win:
        ok = valid(kv)
        if not ok:
            invalid += 1
        if exempt(t):
            continue
        v, kc = [], []
        if kv.get('latch') != 'NONE':                         # (b) moi dong
            v.append('latch=%s' % kv.get('latch'))
            latch_bad = True
        if kv.get('khan') == 'KHAN':
            v.append('khan=KHAN')
        if kv.get('jar') and kv.get('jar') != JAR:
            v.append('jar=%s' % kv.get('jar'))
        if ok:                                                 # (a) dong hop le
            if kv.get('adapter') != 'live':
                v.append('adapter=%s' % kv.get('adapter'))
            if flt(kv.get('C3_CAPITAL')) != exp_cap(C, t):
                v.append('C3_CAPITAL=%s != %s' % (kv.get('C3_CAPITAL'), exp_cap(C, t)))
            if kv.get('push') != 'ON' and not (C.drain is not None and C.drain[0] <= t <= C.drain[1]):
                v.append('push=%s' % kv.get('push'))
            if 'deadman' not in kv:
                kc.append('dong TOM TAT hop le thieu truong deadman=')
            elif kv.get('deadman') != 'OK':
                v.append('deadman=%s' % kv.get('deadman'))
            if kv.get('khan_canh_bao') is None:
                kc.append('thieu truong khan_canh_bao=')
            if pv is not None and not exempt(pv[0]):          # (c) 2 dong HOP LE lien tiep
                for fld in ('khan_canh_bao', 'khan'):
                    a, bb = kv.get(fld), pv[1].get(fld)
                    if a not in (None, '0') and a == bb:
                        v.append('%s=%s o 2 dong hop le lien tiep' % (fld, a))
        it.add(VP if v else (KCD if kc else DAT), t, None, '; '.join(v + kc), raw)
        if ok:
            pv = (t, kv, raw)
    # (d) khoang trong giua 2 dong HOP LE > 10 phut, ca dau ngay va cuoi ngay
    prev_t = pre[-1][0] if pre else C.lo
    for (t, kv, raw) in win:
        if not valid(kv):
            continue
        if t - prev_t > 10 * 60000 and not overl(prev_t, t):
            it.add(VP, t, None, '(d) khoang trong %d s giua 2 dong TOM TAT hop le (tu %s)' % ((t - prev_t) // 1000, fmt(prev_t)), raw)
        prev_t = t
    # E2 'toi min(D+1 07:00, thoi diem cuoi cua cron log da doc)': hieu la thoi diem DOC cron log (cham_luc, chan boi --max-ts),
    # khong phai dong cuoi trong file (monitor chet => khong co dong moi). Xem DE NGHI ERRATA2.
    end_t = min(C.hi, C.cap, C.now)
    if end_t - prev_t > 10 * 60000 and not overl(prev_t, end_t):
        it.add(VP, end_t, None, '(d) khoang trong cuoi ngay %d s (tu dong hop le cuoi %s toi %s)'
               % ((end_t - prev_t) // 1000, fmt(prev_t), fmt(end_t)), None)
    else:
        it.add(DAT)
    if latch_bad:
        it.tags.add('LATCH_NOT_NONE_BAO_OWNER_NGAY')
    it.extra = {'so_dong_TOM_TAT': len(win), 'so_luot_doc_hong': invalid,
                'cron_cuoi': fmt(last) if last is not None else None}
    return it


# ------------------------------------------------------------------ bac (prereg muc 10) + bao cao (muc 9)
DO_ITEMS = {'I3', 'I4', 'I8', 'I9', 'I10', 'I11', 'I12', 'M-T', 'D1', 'K3'}
VANG_ITEMS = {'M-E0', 'M-X', 'K1', 'K2', 'K4', 'K5', 'K6'}
KCDC_ITEMS = [('M-E', KCDC_TOOL), ('I1', KCDC_TOOL), ('I2', KCDC_TOOL), ('I5', KCDC_TOOL), ('I6', KCDC_TOOL),
              ('I7', KCDC_TOOL), ('D2', KCDC_TOOL), ('D3', KCDC_TOOL), ('D4', KCDC_TOOL), ('L-S', KCDC_TOOL),
              ('L-S2', KCDC_TOOL), ('M-G', KCDC_TOOL), ('K7', 'Q4: oracle_seen chi ghi tren 242; bang chung gian tiep = K2 deadman=OK')]


def bac_of(name, it, C):
    st = it.status()
    if st == VP:
        if name == 'M-S':
            return DO if it.extra.get('hard_VI_PHAM') else VANG
        if name == 'K6':
            return DO if 'LATCH_FLATTEN' in it.tags else VANG
        if name in DO_ITEMS:
            return DO
        if name in VANG_ITEMS:
            return VANG
    if st == KCD:
        lim = ms_local((C.D + dt.timedelta(days=3)).isoformat() + ' 09:00')
        if C.now > lim:
            return VANG
    return XANH


def sha12(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        h.update(fh.read())
    return h.hexdigest()[:12]


def atomic_write(path, text, no_overwrite):
    if no_overwrite and os.path.exists(path):
        raise SystemExit('DA CO %s - lan cham da lam giu nguyen (prereg muc 0), khong ghi de' % path)
    d = os.path.dirname(path)
    fd, tmp = tempfile.mkstemp(prefix='.pm_', dir=d)
    with os.fdopen(fd, 'w', encoding='ascii', errors='replace') as fh:
        fh.write(text)
    os.replace(tmp, path)


def equity_line(C):
    ks = [x for x in C.gstore.get('KS_HOURLY', []) if C.lo <= x['t'] < C.hi]
    if not ks:
        return 'equity (mo ta, khong dung cham): khong co dong [KILLSW] HOURLY trong ngay D'
    ks.sort(key=lambda x: x['t'])
    last = ks[-1]['g']
    dds = [flt(x['g'][2]) for x in ks if flt(x['g'][2]) is not None]
    d = flt(last[2])
    return ('equity (mo ta, khong dung cham, chi ti le): dd=%s acct_dd=%s min_dd_ngay=%s cach_A40=%s' %
            (last[2], last[3], ('%.4f' % min(dds)) if dds else '-', ('%.4f' % (d + 0.40)) if d is not None else '-'))


def build(args):
    D = dt.date.fromisoformat(args.date)
    cap = ms_local(args.max_ts) if args.max_ts else FAR
    now = ms_local(args.now) if args.now else int(time.time() * 1000)
    me = os.path.abspath(__file__)
    C = Ctx()
    C.D, C.cap, C.now, C.pull_root, C.cron = D, cap, now, args.pull_root, args.cron_log
    C.pilot_on = ms_local(args.pilot_on_start) if args.pilot_on_start else None
    C.ext_noted = set(x for x in (args.external_noted or '').split(',') if x)
    C.delist_noted = set(x for x in (args.delist_noted or '').split(',') if x)
    C.drain = None
    if args.drain_window:
        a, b = args.drain_window.split(';')
        C.drain = (ms_local(a), ms_local(b))
    C.gstore = {'seen': set()}
    seq = [0]
    t0 = time.time()
    ss = dt.date.fromisoformat(args.state_start)
    C.state_ok, C.state_reason = True, ''
    prior = []
    d = ss
    while d < D:
        pd = scan_day(args.pull_root, d, cap, False, C.gstore, seq)
        if not pd.ok:
            C.state_ok, C.state_reason = False, 'trang thai cum luy ke: ' + pd.reason
        else:
            b = fam_bad(pd, ['SUBMIT', 'FILL_EXEC', 'FILL_STREAM', 'LEG_END', 'EXEC_END', 'ARM', 'STOP', 'RST', 'CLOS', 'BOOK', 'TS'])
            if b:
                C.state_ok, C.state_reason = False, 'trang thai cum luy ke (%s): %s' % (d, b)
        prior.extend(pd.events)
        LOG.info('ngay truoc %s: ok=%s su_kien=%d', d, pd.ok, len(pd.events))
        d += dt.timedelta(days=1)
    dd = scan_day(args.pull_root, D, cap, True, C.gstore, seq)
    C.dd = dd
    C.lo, C.hi = dd.lo, dd.hi
    C.horizon = dd.horizon
    for e in dd.events:
        e['w'] = (not e['la']) and dd.lo <= e['t'] < dd.hi
    events = prior + dd.events
    events.sort(key=lambda e: (e['t'], e['seq']))
    C.S = run_state(events)
    C.sidx = {}
    C.banners = sorted(C.gstore.get('BANNER', []), key=lambda e: e['t'])
    C.banner_ts = [b['t'] for b in C.banners]
    C.sel = load_sel(args.pull_root, D) if dd.ok else None
    items = {}
    if dd.ok:
        items['M-E0'] = chk_ME0(C)
        i3 = chk_I3(C)
        items['I3'] = i3
        items['I4'] = chk_I4(C)
        items['I8'] = chk_I8(C)
        items['I9'] = chk_I9(C, i3)
        items['I10'] = chk_I10(C)
        items['I11'] = chk_I11(C)
        items['I12'] = chk_I12(C)
        items['M-T'] = chk_MT(C)
        items['D1'] = chk_D1(C)
        items['M-S'] = chk_MS(C)
        items['M-X'] = chk_MX(C)
        items['K1'] = chk_K1(C)
        items['K3'] = chk_K3(C)
        items['K4'] = chk_K4(C)
        items['K5'] = chk_K5(C)
        items['K6'] = chk_K6(C)
    else:
        for n in ('M-E0', 'I3', 'I4', 'I8', 'I9', 'I10', 'I11', 'I12', 'M-T', 'D1', 'M-S', 'M-X', 'K1', 'K3', 'K4', 'K5', 'K6'):
            it = Item(n)
            it.force(KCD, dd.reason)
            items[n] = it
    items['K2'] = chk_K2(C)
    for n, why in KCDC_ITEMS:
        it = Item(n)
        it.force(KCDC, why)
        items[n] = it
    bacs = dict((n, bac_of(n, it, C)) for n, it in items.items())
    day_bac = XANH
    for b in bacs.values():
        if BPRIO[b] > BPRIO[day_bac]:
            day_bac = b
    C.elapsed = time.time() - t0
    return C, items, bacs, day_bac, sha12(me)


def render(C, items, bacs, day_bac, tool, prev_json):
    st = dict((n, it.status()) for n, it in items.items())
    vang2 = []
    if prev_json:
        pb = prev_json.get('bac_muc', {})
        pst = dict((n, v.get('trang_thai')) for n, v in prev_json.get('muc', {}).items())
        vang2 = sorted(n for n, b in bacs.items() if b == VANG and pb.get(n) == VANG and st[n] != KCDC and pst.get(n) != KCDC)
    owner_now = sorted(t for n in ('K6', 'K2') for t in items[n].tags if t in ('LATCH_NO_NEW_ENTRY', 'LATCH_NOT_NONE_BAO_OWNER_NGAY'))
    cham_luc = fmt(C.now)[:19].replace(' ', 'T') + '+07:00'
    j = {'dau': 'PILOT-M D=%s cham_luc=%s bac=%s prereg=%s cong_cu=%s' % (C.D, cham_luc, day_bac, PREREG_SHA, tool),
         'D': C.D.isoformat(), 'prereg': PREREG_SHA, 'cong_cu_sha256_12': tool, 'cham_luc': cham_luc, 'bac': day_bac,
         'bac_muc': bacs, 'muc': dict((n, it.to_json()) for n, it in items.items()),
         'hai_ngay_vang_lien_tiep_cung_muc': vang2, 'bao_owner_ngay': owner_now,
         'du_lieu': {'pull_ok': C.dd.ok, 'ly_do_pull': C.dd.reason, 'files': C.dd.files, 'so_dong_cua_so': C.dd.nwin,
                     'dong_parse_theo_mau': C.dd.parsed, 'dong_khong_parse_theo_mau': C.dd.unparsed,
                     'vi_du_khong_parse': C.dd.unparsed_ex, 'dong_trung_bo': C.dd.dup,
                     'horizon': fmt(C.horizon), 'trang_thai_cum_ok': C.state_ok, 'ly_do_trang_thai': C.state_reason,
                     'max_ts': fmt(C.cap) if C.cap < FAR else None, 'gio_khong_co_dong': [i for i, x in enumerate(C.dd.hours) if x == 0],
                     'thoi_gian_chay_s': round(C.elapsed, 1)}}
    mi = ['I1', 'I2', 'I3', 'I4', 'I5', 'I6', 'I7', 'I8', 'I9', 'I10', 'I11', 'I12']
    mk = ['K1', 'K2', 'K3', 'K4', 'K5', 'K6', 'K7']

    def short(it):
        s = it.status()
        if s in (KCD, KCDC):
            return it.reason or (it.kcd[0]['ly_do'] if it.kcd else '')
        if s == VP and it.viol:
            return it.viol[0]['ly_do']
        return ''
    msx = items['M-X'].extra if items['M-X'].extra else {}
    tv = msx.get('truot_vao_ngay', {})
    rows = [
        ('M-E', st['M-E'], '-', '-', KCDC_TOOL),
        ('M-E0', st['M-E0'], items['M-E0'].n, 'vi_pham=%d' % len(items['M-E0'].viol), short(items['M-E0'])),
        ('M-I', merge_status(st[x] for x in mi), sum(items[x].n for x in mi),
         'VP:%s KCD:%s KCD_CAU_TRUC:I1,I2,I5,I6,I7' % (','.join(x for x in mi if st[x] == VP) or '-',
                                                       ','.join(x for x in mi if st[x] == KCD) or '-'),
         '; '.join('%s=%s' % (x, st[x]) for x in mi if x not in ('I1', 'I2', 'I5', 'I6', 'I7'))),
        ('M-T', st['M-T'], items['M-T'].n, 'vi_pham=%d' % len(items['M-T'].viol), short(items['M-T'])),
        ('M-D', merge_status([st['D1'], st['D2'], st['D3'], st['D4']]), items['D1'].n,
         'D1=%s x15M=%s' % (st['D1'], [x['x_15M_pct'] for x in items['D1'].extra.get('gia_tri_15M_leg_DCA', [])]),
         'D2,D3,D4 KCD_CAU_TRUC; ' + short(items['D1'])),
        ('M-S', merge_status([st['M-S'], KCDC]), items['M-S'].n,
         'cung=%s nhan=%s' % (st['M-S'], ','.join(sorted(items['M-S'].tags)) or '-'),
         '(4)(5) + theo doi L-S/L-S2 KCD_CAU_TRUC; ' + short(items['M-S'])),
        ('M-X', st['M-X'], items['M-X'].n,
         'n=%s med=%s p90=%s max=%s bps' % (tv.get('n'), _r(tv.get('median_bps')), _r(tv.get('p90_bps')), _r(tv.get('max_bps'))),
         short(items['M-X'])),
        ('M-G', st['M-G'], '-', '-', KCDC_TOOL),
        ('M-K', merge_status(st[x] for x in mk), '-', ' '.join('%s=%s' % (x, st[x]) for x in mk),
         'flag X14=%s; %s' % (items['K4'].extra.get('flag') if items['K4'].extra else None,
                              '; '.join('%s: %s' % (x, short(items[x])) for x in mk if st[x] in (VP, KCD)))),
    ]
    vp = sorted(n for n in st if st[n] == VP)
    kc = sorted(n for n in st if st[n] == KCD)
    body = ['Bac ngay: %s. Muc VI_PHAM: %s. Muc KHONG_CHAM_DUOC: %s. Muc chi-log cham tu dong; muc can Vision/rig = KCD_CAU_TRUC.'
            % (day_bac, ', '.join(vp) or 'khong', ', '.join(kc) or 'khong')]
    if vang2:
        body.append('Hai ngay VANG lien tiep cung muc: %s => MASTER de xuat owner xem xet nhu DO.' % ', '.join(vang2))
    if owner_now:
        body.append('BAO OWNER NGAY: %s.' % ', '.join(owner_now))
    if not C.dd.ok:
        body.append('Pull: %s.' % C.dd.reason)
    md = [j['dau'], '']
    md += body
    md += ['', '| Muc | Trang thai | Mau | So chinh | Ghi chu |', '|---|---|---|---|---|']
    for r in rows:
        md.append('| %s |' % ' | '.join(str(x).replace('|', '/')[:300] for x in r))
    md += ['', equity_line(C) if C.dd.ok else 'equity: khong co du lieu pull', '',
           'kiem_cheo: CHUA - MASTER tu tinh lai >= 3 so tu log goc truoc khi bao owner (prereg muc 9)', '',
           'Chi tiet tung su kien: D_%s.json' % C.D.strftime('%Y%m%d')]
    return j, '\n'.join(md) + '\n'


def _r(x):
    return None if x is None else round(x, 1)


def official_time_ok(d, now_ms):
    """ERRATA2 F1: lan cham chinh thuc chi chay SAU D+1 07:10 +07."""
    return now_ms >= ms_local((d + dt.timedelta(days=1)).isoformat() + ' 07:10')


def main(argv=None):
    ap = argparse.ArgumentParser(description='PILOT-M cham hang ngay (chi log). Xem README_PILOT_M.md')
    ap.add_argument('date', help='ngay cham D (yyyy-mm-dd), cua so [D 07:00; D+1 07:00) +07')
    ap.add_argument('--official', action='store_true', help='ghi vao ~/claude_master/v12/pilot_m/ (BAT BUOC de ghi chinh thuc)')
    ap.add_argument('--out-dir', help='thu muc ghi khi KHONG --official')
    ap.add_argument('--pilot-on-start', help='"yyyy-mm-dd HH:MM" +07 - gio bat dau lenh pilot_on (ngay 2026-11-26)')
    ap.add_argument('--pull-root', default=DEF_PULL)
    ap.add_argument('--cron-log', default=DEF_CRON)
    ap.add_argument('--state-start', default=STATE_START_DEFAULT)
    ap.add_argument('--max-ts', help='"yyyy-mm-dd HH:MM" +07: bo MOI dong co thoi gian >= moc (chong nhin truoc khi thu)')
    ap.add_argument('--now', help='"yyyy-mm-dd HH:MM" +07: gia lap cham_luc (chi de test luat D+3)')
    ap.add_argument('--external-noted', help='SYM,SYM: cum dong EXTERNAL da co ghi chep owner cung ngay')
    ap.add_argument('--delist-noted', help='SYM,SYM: MASTER co ghi chep thong bao huy niem yet cua san (E4, DELIST_SETTLE)')
    ap.add_argument('--drain-window', help='"yyyy-mm-dd HH:MM;yyyy-mm-dd HH:MM": khung owner da drain co ghi chep (K2)')
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s', stream=sys.stderr)
    if args.official:
        if args.out_dir and os.path.realpath(args.out_dir) != os.path.realpath(OFFICIAL_DIR):
            LOG.error('--official khong di cung --out-dir khac')
            return 2
        if args.max_ts or args.now or args.pull_root != DEF_PULL or args.cron_log != DEF_CRON or args.state_start != STATE_START_DEFAULT:
            LOG.error('--official khong cho phep --max-ts / --now / --pull-root / --cron-log / --state-start khac mac dinh')
            return 2
        if not official_time_ok(dt.date.fromisoformat(args.date), int(time.time() * 1000)):
            LOG.error('--official TU CHOI: chua toi D+1 07:10 +07 (ERRATA2 F1)')
            return 2
        out = OFFICIAL_DIR
    else:
        if not args.out_dir:
            LOG.error('thieu --out-dir (hoac --official)')
            return 2
        out = args.out_dir
        if os.path.realpath(out) == os.path.realpath(OFFICIAL_DIR):
            LOG.error('ghi vao %s BAT BUOC --official', OFFICIAL_DIR)
            return 2
    os.makedirs(out, exist_ok=True)
    C, items, bacs, day_bac, tool = build(args)
    prev_p = os.path.join(out, 'D_%s.json' % (C.D - dt.timedelta(days=1)).strftime('%Y%m%d'))
    prev_json = None
    if os.path.isfile(prev_p):
        try:
            with open(prev_p, encoding='utf-8') as fh:
                prev_json = json.load(fh)
        except (OSError, ValueError):
            prev_json = None
    j, md = render(C, items, bacs, day_bac, tool, prev_json)
    stem = os.path.join(out, 'D_%s' % C.D.strftime('%Y%m%d'))
    atomic_write(stem + '.json', json.dumps(j, ensure_ascii=True, indent=1, sort_keys=True) + '\n', args.official)
    atomic_write(stem + '.md', md, args.official)
    LOG.info('%s | %.1f s | %s', j['dau'], C.elapsed, ' '.join('%s=%s' % (n, items[n].status()) for n in sorted(items)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
