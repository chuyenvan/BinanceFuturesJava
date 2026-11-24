#!/usr/bin/env python3
"""ADD24 R-LIVE fixture builder cua so OW2 (prereg s5): CHI chay khi P1 dat (owner duyet) - p1_gate.
1) T_cut (P7): 2026-11-24 07:00 +07 neu pull242/2026-11-23/COMPLETE; khong => moc 07:00 cua ngay COMPLETE gan nhat truoc do (+1 ngay).
2) Tai Vision UM 1m (klines + markPriceKlines) cho symbol can (sel rank<=24 o moi phut co SUBMIT + symbol live + BTCUSDT) vao
   /dev/shm/add24/vision/<kind>/<UTC day>/<SYM>.zip (chi ngay OW2; thieu => liet ke, V2).
3) prep_fixture.py (def1f034) voi VIS = thu muc tai o (2), --start 2026-11-19 09:31 --end T_cut --buffer-day 2026-11-19 --exinfo <EXINFO>.
4) mark.csv.gz (symbol,t,o,h,l,c) tu markPriceKlines; manifest_ow2.json (sha256 moi dau vao, V1).
usage: rlive_fixture.py --out /dev/shm/add24/fx_ow2 --live <parse dir> --exinfo <json.gz> [--tcut-override 'YYYY-MM-DD HH:MM' (chi errata)]
"""
import argparse, csv, glob, gzip, hashlib, io, json, logging, os, re, sys, time, urllib.parse, urllib.request, zipfile
from datetime import datetime, timedelta, timezone

H = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, H); sys.path.insert(0, os.path.join(H, '..', '..', 'e2e'))
from p1_gate import require_p1

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger('fx')
TZ7 = timezone(timedelta(hours=7))
PULL = os.path.expanduser('~/claude_master/pull242')
VBASE = 'https://data.binance.vision/data/futures/um/daily'
OW2_START = '2026-11-19 09:31'


def tcut():
    if os.path.exists(PULL + '/2026-11-23/COMPLETE'):
        return '2026-11-24 07:00', '2026-11-23'
    days = sorted(d for d in os.listdir(PULL) if d.startswith('2026-11-') and '2026-11-19' <= d <= '2026-11-23'
                  and os.path.exists('%s/%s/COMPLETE' % (PULL, d)))
    if not days:
        raise SystemExit('TU CHOI: khong co ngay pull COMPLETE trong OW2')
    d = datetime.strptime(days[-1], '%Y-%m-%d') + timedelta(days=1)
    return d.strftime('%Y-%m-%d') + ' 07:00', days[-1]


def exinfo_gz(src, dst):
    """[ERRATA6 P2] prep_fixture.py (def1f034) doc --exinfo bang gzip.open; EXINFO (ERRATA1 E-A7) la .json THO => nen ban sao
    (mtime=0) cho prep; noi dung giai nen = NGUYEN BYTE goc (assert). Tra (duong dan cho prep, sha256 goc)."""
    raw = open(src, 'rb').read()
    sha = hashlib.sha256(raw).hexdigest()
    if raw[:2] == b'\x1f\x8b':
        return src, hashlib.sha256(gzip.decompress(raw)).hexdigest()
    with open(dst, 'wb') as fh, gzip.GzipFile(filename='', mode='wb', fileobj=fh, mtime=0) as fo:
        fo.write(raw)
    if gzip.open(dst, 'rb').read() != raw:
        raise SystemExit('TU CHOI (ERRATA6): ban gzip exinfo khac nguyen ban')
    return dst, sha


def live_ingest_ok(sym):
    """[ERRATA6 U1] CHEP NGUYEN dieu kien ingest live TickerIngestor2AerospikeNew.java:134 (symbol = getString("symbol").toUpperCase();
    symbol.endsWith("USDT") && symbol.matches("^[A-Z0-9]+$") && !Constants.diedSymbol.contains(symbol)); cung regex o :517, :557.
    diedSymbol KHONG ap o day: rig tu loai (MarketReplay:107, Constants.diedSymbol production)."""
    u = sym.upper()
    return u.endswith('USDT') and re.fullmatch('[A-Z0-9]+', u) is not None


def onboard_map(ex):
    """[ERRATA6 B1] symbol -> (onboardDate, deliveryDate, status) tu EXINFO (0 = khong co)."""
    return {x['symbol']: (int(x.get('onboardDate') or 0), int(x.get('deliveryDate') or 0), x.get('status')) for x in ex.get('symbols', [])}


def vision_explained(item, onb):
    """[ERRATA6 B1] 'SYM@YYYY-MM-DD' (ngay UTC) thieu tren Vision la GIAI THICH DUOC (tat dinh, chi tu EXINFO) khi: symbol niem yet
    (onboardDate) SAU khi ngay do ket thuc, hoac symbol khong TRADING va deliveryDate <= dau ngay do (huy niem yet truoc ngay)."""
    s, d = item.rsplit('@', 1)
    d0 = int(datetime.strptime(d, '%Y-%m-%d').replace(tzinfo=timezone.utc).timestamp() * 1000); d1 = d0 + 86400000
    o, dl, st = onb.get(s, (0, 0, None))
    return bool((o and o >= d1) or (st is not None and st != 'TRADING' and dl and dl <= d0))


def ms7(s):
    return int(datetime.strptime(s, '%Y-%m-%d %H:%M').replace(tzinfo=TZ7).timestamp() * 1000)


def fetch(kind, sym, day, root):
    p = '%s/%s/%s/%s.zip' % (root, kind, day, sym)
    if os.path.exists(p):
        return p
    os.makedirs(os.path.dirname(p), exist_ok=True)
    q = urllib.parse.quote(sym)   # [ERRATA6 B1] symbol khong ASCII (5 symbol TRADING trong EXINFO) => URL ma hoa %, truoc day loi im lang
    url = '%s/%s/%s/1m/%s-1m-%s.zip' % (VBASE, kind, q, q, day)
    for i in range(3):
        try:
            with urllib.request.urlopen(url, timeout=60) as r:
                data = r.read()
            open(p + '.tmp', 'wb').write(data); os.replace(p + '.tmp', p)
            return p
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
        except Exception as e:
            log.warning('fetch %s %s: %s', url, i, e); time.sleep(3)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True); ap.add_argument('--live', required=True); ap.add_argument('--exinfo', required=True)
    ap.add_argument('--tcut-override', default='')
    a = ap.parse_args()
    why = require_p1()
    if not a.out.startswith('/dev/shm/add24/'):
        raise SystemExit('TU CHOI: fixture chi o /dev/shm/add24')
    end, dcomp = (a.tcut_override, 'override') if a.tcut_override else tcut()
    exi, exsha = exinfo_gz(a.exinfo, a.out.rstrip('/') + '_exinfo.json.gz')
    S, E = ms7(OW2_START), ms7(end)
    vroot = '/dev/shm/add24/vision'
    d0 = datetime.fromtimestamp(S / 1000, timezone.utc).date(); d1 = datetime.fromtimestamp((E - 1) / 1000, timezone.utc).date()
    udays = [(d0 + timedelta(days=i)).strftime('%Y-%m-%d') for i in range((d1 - d0).days + 1)]
    sub = list(csv.DictReader(open(a.live + '/submit.csv')))
    smin = {int(r['cid'].split('-')[-2]) * 60000 for r in sub}
    pdays = [(datetime.strptime(OW2_START[:10], '%Y-%m-%d') + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(-1, 6)]
    allsym, cand = set(['BTCUSDT']), set(r['symbol'] for r in sub)
    for d in pdays:
        for f in glob.glob('%s/%s/dumps/sel_dump_*.csv.gz' % (PULL, d)):
            with gzip.open(f, 'rt') as fh:
                r = csv.reader(fh); next(r, None)
                for x in r:
                    if len(x) >= 6 and S <= int(x[0]) < E:
                        allsym.add(x[1])
                        if int(x[0]) in smin and int(x[3]) <= 24:
                            cand.add(x[1])
    # mkt.csv.gz (dieu kien thi truong DCA/BIG_DOWN, ERRATA1 N6) can TOAN universe => tai kline moi symbol PERPETUAL USDT TRADING cua exinfo
    ex = json.load(gzip.open(a.exinfo, 'rt') if a.exinfo.endswith('.gz') else open(a.exinfo))
    allsym |= {x['symbol'] for x in ex.get('symbols', []) if x.get('contractType') == 'PERPETUAL' and x.get('quoteAsset') == 'USDT'
               and x.get('status') == 'TRADING'}
    # [ERRATA6 U1] universe rig = universe ingest live: symbol live khong ingest (vd 5 symbol ten khong ASCII) => LOAI, khong tai
    noingest = sorted(x for x in allsym | cand if not live_ingest_ok(x))
    allsym -= set(noingest); cand -= set(noingest)
    miss = {'klines': [], 'markPriceKlines': []}
    for s in sorted(allsym):
        for d in udays:
            if not fetch('klines', s, d, vroot):
                miss['klines'].append(s + '@' + d)
    for s in sorted(cand | {'BTCUSDT'}):
        for d in udays:
            if not fetch('markPriceKlines', s, d, vroot):
                miss['markPriceKlines'].append(s + '@' + d)
    # [ERRATA6 B1] Vision thieu (404 / loi mang sau 3 lan) ma KHONG giai thich duoc tu EXINFO => DUNG truoc prep / lane / cham
    onb = onboard_map(ex)
    unexp = {k: [x for x in v if not vision_explained(x, onb)] for k, v in miss.items()}
    if any(unexp.values()):
        jf = a.out.rstrip('/') + '_vision_missing.json'
        json.dump({'missing': miss, 'unexplained': unexp}, open(jf, 'w'), indent=1)
        raise SystemExit('TU CHOI (ERRATA6 B1): Vision thieu khong giai thich: klines %d markPriceKlines %d (%s)'
                         % (len(unexp['klines']), len(unexp['markPriceKlines']), jf))
    import prep_fixture as P
    P.VIS = vroot + '/klines'
    sys.argv = ['prep_fixture.py', '--out', a.out, '--start', OW2_START, '--end', end, '--buffer-day', '2026-11-19', '--exinfo', exi]
    P.main()
    if hashlib.sha256(open(a.out + '/exinfo.json', 'rb').read()).hexdigest() != exsha:
        raise SystemExit('TU CHOI (ERRATA6): fx/exinfo.json khac sha256 EXINFO goc')
    n = 0
    with gzip.open(a.out + '/mark.csv.gz', 'wt') as fo:
        w = csv.writer(fo, lineterminator='\n'); w.writerow(['symbol', 't', 'o', 'h', 'l', 'c'])
        for s in sorted(cand | {'BTCUSDT'}):
            for d in udays:
                p = '%s/markPriceKlines/%s/%s.zip' % (vroot, d, s)
                if not os.path.exists(p):
                    continue
                with zipfile.ZipFile(p) as z, z.open(z.namelist()[0]) as fh:
                    for x in csv.reader(io.TextIOWrapper(fh)):
                        if x and x[0][:1].isdigit() and S - 5 * 60000 <= int(x[0]) < E:
                            w.writerow([s, int(x[0]), x[1], x[2], x[3], x[4]]); n += 1
    man = {'p1': why, 'START': S, 'END': E, 'tcut': end, 'tcut_from_complete_day': dcomp, 'udays': udays, 'symbols_klines': len(allsym),
           'exinfo_src': a.exinfo, 'exinfo_src_sha256': exsha, 'exinfo_passed_to_prep': exi,
           'symbols_mark': len(cand) + 1, 'mark_rows': n, 'missing': miss, 'missing_unexplained': unexp, 'excluded_not_live_ingest': noingest,
           'sha256': {f: hashlib.sha256(open(os.path.join(a.out, f), 'rb').read()).hexdigest() for f in sorted(os.listdir(a.out))}}
    json.dump(man, open(a.out + '/manifest_ow2.json', 'w'), indent=1)
    log.info('fixture OW2 xong tcut=%s miss_k=%d miss_m=%d', end, len(miss['klines']), len(miss['markPriceKlines']))


if __name__ == '__main__':
    main()
