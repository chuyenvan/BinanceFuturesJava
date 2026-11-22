#!/usr/bin/env python3
"""ADD24 cong C0 (a)-(e) + C0b (tai lap luot 11-05 tren stub so voi output 11-17). Ghi C0.json, C0B.json (may doc duoc).
Khong doc noi dung 8 entry key cua jar goc (chi ten + CRC/size central dir). Khong in gia / PnL: lech chi in (file, khoa dong, cot).
usage: c0_check.py --run <out_dir luot stub> --ref <out1105_1117_0132> --c0 C0.json --c0b C0B.json [--classes76 dir]
"""
import argparse, csv, gzip, hashlib, io, json, logging, os, re, subprocess, sys, zipfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from keyrx import KEYRX, ORIG, ORIG_MD5, KSE, KSE_MD5, STUB

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
log = logging.getLogger('c0')
SEC = '/home/ubuntu/claude_master/vz_e1_wt/research/nup3/jar_sec_check.py'
LANES = ['R0', 'S-DCA', 'FIN-INJ']
CMP_FILES = ['legs.csv', 'outcomes.csv', 'events.csv', 'fills.csv', 'fin_excl.csv', 'trace_dec.csv.gz']
NET_RX = re.compile(r'(ConnectException|UnknownHostException|NoRouteToHost|Network is unreachable|SocketTimeoutException|'
                    r'Connection refused|connect timed out|SSLHandshake|api\.binance|fapi\.binance|api\.telegram)', re.I)
BANNERS = {'LIVE-SIZING': r'\[LIVE-SIZING\] LIVE_APPLY_GRID_RATIO=true', 'LIVE-DCA-GRID': r'\[LIVE-DCA-GRID\] LIVE_DCA_GRID_ENABLED=true',
           'MINUTE-FIN': r'\[MINUTE-FIN\] BAT', 'GATE-RATIO': r'\[GATE-RATIO\] LIVE BAT'}


def md5f(p, algo='md5'):
    h = hashlib.new(algo)
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def jar_gate():
    r = {}
    r['orig_md5'] = md5f(ORIG); r['stub_md5'] = md5f(STUB); r['stub_sha256'] = md5f(STUB, 'sha256')
    r['stub_mode'] = oct(os.stat(STUB).st_mode & 0o777)
    zo, zs = zipfile.ZipFile(ORIG), zipfile.ZipFile(STUB)
    no, ns = [i.filename for i in zo.infolist()], [i.filename for i in zs.infolist()]
    keys = [n for n in no if KEYRX.match(n)]
    r['a_entries_orig'] = len(no); r['a_entries_stub'] = len(ns); r['a_order_equal'] = (no == ns)
    same = diff = 0; dl = []
    for n in no:
        if n in keys or n.endswith('/'):
            continue
        if hashlib.md5(zo.read(n)).hexdigest() == hashlib.md5(zs.read(n)).hexdigest():
            same += 1
        else:
            diff += 1; dl.append(n)
    r['b_nonkey_same'] = same; r['b_nonkey_diff'] = diff; r['b_diff_list'] = dl[:20]
    r['b_key_names'] = keys; r['b_n_key'] = len(keys)
    r['c_kse_md5_stub'] = hashlib.md5(zs.read(KSE)).hexdigest(); r['c_ok'] = r['c_kse_md5_stub'] == KSE_MD5
    p = subprocess.run([sys.executable, '-I', SEC, STUB], capture_output=True, text=True)
    try:
        sec = json.loads(p.stdout)
    except Exception:
        sec = {'ok': False, 'raw_rc': p.returncode}
    r['sec_check'] = {k: sec.get(k) for k in ('ok', 'privateconfig_runs_ge20_other', 'privateconfig_max_run_len',
                                              'com_binance_classes_with_64alnum', 'lib_classes_with_64alnum_other', 'classes_scanned')}
    r['ok'] = (r['orig_md5'] == ORIG_MD5 and r['a_order_equal'] and diff == 0 and len(keys) == 8 and r['c_ok']
               and sec.get('ok') is True and r['stub_mode'] == '0o600')
    return r


def classes76(d):
    """bien dich 76134a52 (stub PrivateConfig) vs jar goc: com/binance/** - key chi so CRC/size (khong doc)."""
    zo = zipfile.ZipFile(ORIG); oi = {i.filename: i for i in zo.infolist()}
    same = diff = miss = ksame = kdiff = 0; dl = []
    for root, _, fs in os.walk(d):
        for fn in fs:
            if not fn.endswith('.class'):
                continue
            rel = os.path.relpath(os.path.join(root, fn), d)
            if not rel.startswith('com/binance/'):
                continue
            if rel not in oi:
                miss += 1; continue
            if KEYRX.match(rel):
                b = open(os.path.join(root, fn), 'rb').read()
                import zlib
                if (zlib.crc32(b) & 0xffffffff) == oi[rel].CRC and len(b) == oi[rel].file_size:
                    ksame += 1
                else:
                    kdiff += 1; dl.append('KEY ' + rel)
                continue
            if hashlib.md5(open(os.path.join(root, fn), 'rb').read()).hexdigest() == hashlib.md5(zo.read(rel)).hexdigest():
                same += 1
            else:
                diff += 1; dl.append(rel)
    return {'nonkey_same': same, 'nonkey_diff': diff, 'not_in_jar': miss, 'key_crc_same': ksame, 'key_crc_diff': kdiff, 'diff_list': dl[:20]}


def probe(p):
    r = {'file': p, 'classes': [], 'net_probe': None}
    for ln in open(p):
        ln = ln.strip()
        if not ln.startswith('{'):
            continue
        d = json.loads(ln)
        if 'class' in d:
            r['classes'].append(d)
        elif 'net_probe' in d:
            r['net_probe'] = d['net_probe']; r['from_stub_n'] = d['from_stub_n']; r['n'] = d['n']
        else:
            r['env'] = d
    zs = zipfile.ZipFile(STUB)
    r['md5_match_stub_entry'] = sum(1 for c in r['classes'] if hashlib.md5(zs.read(c['class'].replace('.', '/') + '.class')).hexdigest() == c['md5'])
    r['ok'] = (r.get('from_stub_n') == 12 and r.get('n') == 12 and r['md5_match_stub_entry'] == 12 and r['net_probe'] is not None
               and r['net_probe'].startswith('FAIL') and r.get('env', {}).get('shadow_host') == 'true')
    return r


def lane_gate(d):
    r = {}
    lg = open(os.path.join(d, 'run.log'), errors='replace').read()
    r['banners'] = {k: bool(re.search(v, lg)) for k, v in BANNERS.items()}
    r['net_lines'] = sum(1 for ln in lg.splitlines() if NET_RX.search(ln))
    res = json.load(open(os.path.join(d, 'result.json')))
    jc = res.get('jar_check', {}); ec = res.get('env_check', {})
    r['jar_check_ok'] = jc.get('ok'); r['jar_md5'] = jc.get('jar_md5'); r['classes_from_jar'] = jc.get('classes_from_jar')
    miss = {k: v for k, v in ec.items() if re.search(r'(missing|thieu|absent)', k, re.I)}
    r['env_missing_fields'] = miss
    r['env_missing_n'] = sum(len(v) if isinstance(v, (list, dict)) else (0 if not v else 1) for v in miss.values())
    r['env_check_ok'] = ec.get('ok')
    r['errors'] = len(res.get('errors', [])); r['log_errors'] = len(res.get('log_errors', [])); r['violations'] = len(res.get('violations', {}))
    env = open(os.path.join(d, 'env_used.sh')).read()
    r['env_shadow_true'] = 'export LIVE_IS_SHADOW_HOST=true' in env; r['env_adapter_dry'] = 'export LIVE_ADAPTER=dry' in env
    r['ok'] = (all(r['banners'].values()) and r['net_lines'] == 0 and r['jar_check_ok'] is True and r['env_missing_n'] == 0
               and r['env_shadow_true'] and r['env_adapter_dry'] and r['errors'] == 0)
    return r


def rows(p):
    if not os.path.exists(p):
        return None
    f = gzip.open(p, 'rt') if p.endswith('.gz') else open(p)
    return list(csv.reader(f))


def cmp_file(a, b, fname):
    ra, rb = rows(a), rows(b)
    if ra is None or rb is None:
        return {'file': fname, 'ok': False, 'why': 'missing', 'a': ra is not None, 'b': rb is not None}
    hdr = ra[0]
    out = {'file': fname, 'rows_stub': len(ra) - 1, 'rows_1117': len(rb) - 1, 'header_equal': ra[0] == rb[0], 'mism': 0, 'max_rel_budget': 0.0,
           'examples': []}
    bi = hdr.index('budget') if 'budget' in hdr else -1
    for i in range(1, max(len(ra), len(rb))):
        x = ra[i] if i < len(ra) else None
        y = rb[i] if i < len(rb) else None
        if x is None or y is None or len(x) != len(y):
            out['mism'] += 1
            if len(out['examples']) < 5:
                out['examples'].append({'row': i, 'why': 'row_missing_or_len'})
            continue
        bad = []
        for j, (u, v) in enumerate(zip(x, y)):
            if u == v:
                continue
            if j == bi:
                try:
                    rel = abs(float(u) - float(v)) / max(abs(float(v)), 1e-300)
                    out['max_rel_budget'] = max(out['max_rel_budget'], rel)
                    if rel <= 1e-9:
                        continue
                except ValueError:
                    pass
            bad.append(hdr[j] if j < len(hdr) else str(j))
        if bad:
            out['mism'] += 1
            if len(out['examples']) < 5:
                out['examples'].append({'row': i, 'key': x[:1] + x[2:4] if len(x) > 3 else x[:1], 'cols': bad})
    out['ok'] = out['header_equal'] and out['mism'] == 0 and out['rows_stub'] == out['rows_1117']
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--run', required=True); ap.add_argument('--ref', required=True)
    ap.add_argument('--c0', required=True); ap.add_argument('--c0b', required=True)
    ap.add_argument('--classes76', default='/dev/shm/add24/build/src76/target/classes')
    ap.add_argument('--probe', required=True)
    a = ap.parse_args()
    c0 = {'gate': 'C0', 'prereg': 'PREREG_PARITY_V12_DRY_ADDENDUM24_PILOTFID 6ee84f17 s3 + P5', 'run_dir': a.run}
    c0['jar'] = jar_gate(); log.info('jar ok=%s', c0['jar']['ok'])
    c0['classes76_vs_orig'] = classes76(a.classes76) if os.path.isdir(a.classes76) else 'SKIP(no build dir)'
    c0['probe_d_e'] = probe(a.probe); log.info('probe ok=%s', c0['probe_d_e']['ok'])
    c0['lanes'] = {ln: lane_gate(os.path.join(a.run, ln)) for ln in LANES}
    c0['ok'] = c0['jar']['ok'] and c0['probe_d_e']['ok'] and all(v['ok'] for v in c0['lanes'].values())
    c0['verdict'] = 'PASS' if c0['ok'] else 'FAIL'
    json.dump(c0, open(a.c0, 'w'), indent=1)
    c0b = {'gate': 'C0b', 'ref_dir': a.ref, 'run_dir': a.run, 'stub_md5': c0['jar']['stub_md5'], 'lanes': {}}
    n_legs = 0
    for ln in LANES:
        L = {}
        for f in CMP_FILES:
            L[f] = cmp_file(os.path.join(a.run, ln, f), os.path.join(a.ref, ln, f), f)
        ra = json.load(open(os.path.join(a.run, ln, 'result.json'))); rb = json.load(open(os.path.join(a.ref, ln, 'result.json')))
        keys = ['outcomes', 'stats', 'X10', 'ks_action_final', 'ks_any_latch', 'violations', 'errors', 'market', 'appended_r']
        L['result_json_equal'] = {k: ra.get(k) == rb.get(k) for k in keys}
        L['ok'] = all(v['ok'] for k, v in L.items() if k.endswith('.csv') or k.endswith('.gz')) and all(L['result_json_equal'].values())
        n_legs += L['legs.csv'].get('rows_stub', 0)
        c0b['lanes'][ln] = L
    c0b['legs_total'] = n_legs
    c0b['ok'] = all(v['ok'] for v in c0b['lanes'].values()) and n_legs >= 24
    c0b['verdict'] = 'PASS' if c0b['ok'] else 'FAIL'
    json.dump(c0b, open(a.c0b, 'w'), indent=1)
    print('C0', c0['verdict'], 'C0b', c0b['verdict'], 'legs', n_legs)
    return 0 if (c0['ok'] and c0b['ok']) else 1


if __name__ == '__main__':
    sys.exit(main())
