#!/usr/bin/env python3
"""ADD24 cong V10 (ERRATA3 A4 + ERRATA4 C3). So (ts, r) rig nap vao buffer gate voi buffer live (file gate_ratio_live cua lan pull SAU cua so).
V10a (truot => HUY): mien = phut ma rig va live co CUNG tap dang giu (giao voi ung vien phut do) VA cung trang thai so day, HOAC phut truoc
  lech L-E dau tien: multiset r (bit float32) phai TRUNG va lech dem = 0.
[ERRATA7] mien V10a GIU NGUYEN; DIEU KIEN DAT cua mot phut m trong mien (L = multiset ban ghi live tai m, R = cua rig):
  (1) L == R (bit); HOAC (2) L la tap con bit-exact cua R (multiset) VA tap symbol cua R\L == S_m = held_live(m) \ held_rig(m) (cung nguon
  trang thai nhu V10_diag); symbol co PHUT CHUYEN TRANG THAI (live: mo/dong cum roi vao phut m-1, m, m+1; rig: co 'held' trong trace_dec doi
  o phut m-1, m, m+1 so voi phut co trace truoc do) duoc nam o MOT TRONG HAI phia. Symbol cua ban ghi rig = trace_dec hang held=0 (assert
  multiset r_bits == appended.csv.gz tung phut; khac => phut truot). V10a ok <=> 0 phut khong dat. Nen END-1' bi bo ca hai phia (E-A11).
V10b (bao cao): phut lech dem NGOAI mien V10a -> outside_domain_mismatch_minutes; rlive_score.py --v10 xet thuoc cum lech co nhan, con lai =
  lech L-N KHONG GIAI THICH. Chi dem / so bit - khong in gia tri r.
Dang giu live phut m = cum live co leg 0 SUBMIT truoc m+60 s va chua dong (dong dong cum) tai m+60 s (gate phut m chay o giay ~6 phut sau).
So day live = tong notional leg mo / cap >= U_MAX (xap xi; rig: co bookfull trong trace_dec).
usage: v10_buffer.py --rig <lane dir> --live <parse dir> --live-buffer <pull>/run/gate_ratio_live.bin.gz --start --end --cap --out V10.json
"""
import argparse, csv, gzip, itertools, json, os, shutil, sys, tempfile
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
import numpy as np

sys.path.insert(0, os.path.expanduser('~/claude_master/1016/grr'))
import grr_lib  # noqa: E402
TZ7 = timezone(timedelta(hours=7)); MIN = 60000


def ms7(s):
    return int(datetime.strptime(s, '%Y-%m-%d %H:%M').replace(tzinfo=TZ7).timestamp() * 1000)


def bits(x):
    return int(np.array([x], dtype=np.float32).view(np.int32)[0])


def rig_extra_sets(L, rows, cap=4096):
    """[ERRATA7] L: list r_bits live tai phut m; rows: [(symbol, r_bits)] ban ghi rig tai m (moi symbol 1 ban ghi).
    Tra None neu L KHONG la tap con multiset cua R; 'AMBIG' neu qua nhieu cach gan; nguoc lai tap cac tap symbol co the cua R\\L
    (khi nhieu symbol cung r_bits thi moi cach chon deu duoc xet)."""
    Lc, Rc = Counter(L), Counter(b for _, b in rows)
    if any(Rc[b] < n for b, n in Lc.items()):
        return None
    out = {frozenset()}
    for b in sorted(Rc):
        k = Rc[b] - Lc.get(b, 0)
        if k <= 0:
            continue
        syms = sorted(s for s, bb in rows if bb == b)
        out = {o | frozenset(c) for o in out for c in itertools.combinations(syms, k)}
        if len(out) > cap:
            return 'AMBIG'
    return out


def minute_rule(L, R, rows, S_m, flex):
    """[ERRATA7] dieu kien DAT cua mot phut trong mien V10a. L, R: list r_bits (live, rig); rows: [(symbol, r_bits)] cua rig;
    S_m: set symbol live giu/cho ma rig khong giu; flex: set symbol co phut chuyen trang thai (m-1..m+1) o live hoac rig.
    Tra (kieu, ly_do, X): kieu in {'eq', 'subset', 'subset_trans', None}; X = tap symbol R\\L da chon (None neu khong co)."""
    if sorted(L) == sorted(R):
        return 'eq', '', frozenset()
    if Counter(b for _, b in rows) != Counter(R):
        return None, 'rig_trace_khac_appended', None
    sets = rig_extra_sets(L, rows)
    if sets is None:
        return None, 'L_khong_la_tap_con_R', None
    if sets == 'AMBIG':
        return None, 'gan_symbol_mo_ho', None
    S_m, flex = frozenset(S_m), frozenset(flex)
    for X in sorted(sets, key=sorted):
        if X == S_m:
            return 'subset', '', X
    for X in sorted(sets, key=sorted):
        if X - flex == S_m - flex:
            return 'subset_trans', '', X
    return None, 'symbol_thua_khac_S_m', min(sets, key=sorted)


def flex_at(t, lev, rtr):
    """[ERRATA7] symbol co phut chuyen trang thai tai t-1', t, t+1' (lev: live phut moc mo/dong; rtr: rig phut 'held' doi)."""
    return set().union(*(lev.get(t + d, set()) | rtr.get(t + d, set()) for d in (-MIN, 0, MIN)))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--rig', required=True); ap.add_argument('--live', required=True); ap.add_argument('--live-buffer', required=True)
    ap.add_argument('--start', required=True); ap.add_argument('--end', required=True); ap.add_argument('--cap', type=float, default=1000.0)
    ap.add_argument('--u-max', type=float, default=0.6); ap.add_argument('--out', required=True)
    a = ap.parse_args()
    S, E = ms7(a.start), ms7(a.end)
    E1 = E - MIN   # [ERRATA7] bo nen END-1' ca hai phia (E-A11: rig khong decide nen cuoi)
    rig = defaultdict(list)
    for x in csv.DictReader(gzip.open(a.rig + '/appended.csv.gz', 'rt')):
        t = int(x['ts'])
        if S <= t < E1:
            rig[t].append(int(x['r_bits']))
    d = tempfile.mkdtemp(dir='/dev/shm/add24')
    try:
        p = os.path.join(d, 'b.bin')
        with gzip.open(a.live_buffer, 'rb') as fi, open(p, 'wb') as fo:
            shutil.copyfileobj(fi, fo)
        ts, r, bad = grr_lib.load(p)
    finally:
        shutil.rmtree(d)
    live = defaultdict(list)
    m = (ts >= S) & (ts < E1)
    for t, v in zip(ts[m], r[m]):
        live[int(t)].append(bits(v))
    # trang thai rig theo phut (trace_dec): ung vien, dang giu, so day
    cand, rheld, rfull, rrows = defaultdict(set), defaultdict(set), {}, defaultdict(list)
    for x in csv.DictReader(gzip.open(a.rig + '/trace_dec.csv.gz', 'rt')):
        t = int(x['ts'])
        if not (S <= t < E1):
            continue
        cand[t].add(x['symbol'])
        if x['held'] == '1':
            rheld[t].add(x['symbol'])
        else:
            rrows[t].append((x['symbol'], int(x['r_bits'])))   # [ERRATA7] ban ghi rig nap buffer (held=0) - chi de biet symbol
        rfull[t] = rfull.get(t, False) or x['bookfull'] == '1'
    # cum live
    sub = [x for x in csv.DictReader(open(a.live + '/submit.csv')) if x['outcome'] == 'SUBMITTED']
    closes = sorted((int(x['log_ms']), x['symbol']) for x in csv.DictReader(open(a.live + '/book_close.csv'))) if os.path.exists(a.live + '/book_close.csv') else []
    cl, openc = [], {}
    for t_, kind, x in sorted([(int(x['log_ms']), 0, x) for x in sub] + [(c[0], 1, c) for c in closes], key=lambda z: (z[0], z[1])):
        if kind == 0:
            c = openc.get(x['symbol'])
            if c is None:
                c = {'symbol': x['symbol'], 't0': t_, 'tc': None, 'legs': []}; openc[x['symbol']] = c; cl.append(c)
            c['legs'].append((t_, float(x['notional'] or 0)))
        else:
            c = openc.pop(x[1], None)
            if c:
                c['tc'] = x[0]
    # lech L-E dau tien (khoa (dts, symbol, level, legIdx))
    gp = os.path.join(a.live, 'gate.csv')
    lfull_g = {(int(x['log_ms']) // MIN - 1) * MIN for x in csv.DictReader(open(gp)) if x.get('n_skipfull') and int(x['n_skipfull']) > 0} if os.path.exists(gp) else None
    lk = {(int(x['cid'].split('-')[-2]) * MIN, x['symbol'], x['level'], int(x['legIdx'] or x['cid'].split('-')[-1])) for x in sub}
    rk = {(int(x['decision_ts']), x['symbol'], x['level'], int(x['leg_idx'])) for x in csv.DictReader(open(a.rig + '/legs.csv')) if x['outcome'] == 'SUBMITTED'}
    dif = [k[0] for k in lk ^ rk if S <= k[0] < E]
    first_dev = min(dif) if dif else E
    # [ERRATA7] phut chuyen trang thai: live = phut cua moc mo (leg dau) / dong cum; rig = phut 'held' doi so voi phut co trace truoc do
    lev = defaultdict(set)
    for c in cl:
        lev[c['t0'] // MIN * MIN].add(c['symbol'])
        if c['tc'] is not None:
            lev[c['tc'] // MIN * MIN].add(c['symbol'])
    rtr, prev = defaultdict(set), None
    for t in sorted(cand):
        if prev is not None:
            rtr[t] = rheld.get(t, set()) ^ rheld.get(prev, set())
        prev = t
    dom, in_bad, out_bad, n_dom = [], 0, [], 0
    diag = []
    kinds = Counter(); fails = []; n_nbe = 0
    for t in sorted(set(live) | set(rig) | set(cand)):
        tg = t + MIN
        lheld = {c['symbol'] for c in cl if c['t0'] < tg and (c['tc'] is None or c['tc'] > tg)}
        lfull = sum(n for c in cl if c['t0'] < tg and (c['tc'] is None or c['tc'] > tg) for (tt, n) in c['legs'] if tt < tg) / a.cap >= a.u_max
        if lfull_g is not None:
            lfull = t in lfull_g          # [ERRATA5 D1] so day = SO GIAY theo dong [GATE] n_skipfull > 0
        same = (lheld & cand.get(t, set())) == rheld.get(t, set()) and lfull == rfull.get(t, False)
        A_, B_ = sorted(live.get(t, [])), sorted(rig.get(t, []))
        if t < first_dev or same:
            n_dom += 1
            hl, hr = lheld & cand.get(t, set()), rheld.get(t, set())
            S_m = hl - hr
            flex = flex_at(t, lev, rtr)
            kind, why, X = minute_rule(A_, B_, rrows.get(t, []), S_m, flex)
            kinds[kind or 'fail'] += 1
            if A_ != B_:
                n_nbe += 1
                # chan doan (ERRATA5 B(ii)): tap r lech theo phut (bit), trang thai giu / so day hai ben - khong gia / kich thuoc lenh
                diag.append({'ts': t, 'n_live': len(A_), 'n_rig': len(B_), 'r_bits_chi_live': sorted(set(A_) - set(B_))[:30],
                             'r_bits_chi_rig': sorted(set(B_) - set(A_))[:30], 'held_live': sorted(hl),
                             'held_rig': sorted(hr), 'full_live': lfull, 'full_rig': rfull.get(t, False),
                             'e7_kieu': kind, 'e7_ly_do': why, 'e7_S_m': sorted(S_m), 'e7_X': sorted(X) if X is not None else None,
                             'e7_flex': sorted(flex & (S_m | (X or set())))})
            if kind is None:
                in_bad += 1; dom.append(t)
                fails.append({'ts': t, 'ly_do': why, 'n_live': len(A_), 'n_rig': len(B_), 'S_m': sorted(S_m),
                              'X': sorted(X) if X is not None else None, 'flex': sorted(flex & (S_m | (X or set())))})
        elif len(A_) != len(B_) or A_ != B_:
            out_bad.append(t)
    n_l = sum(len(v) for v in live.values()); n_r = sum(len(v) for v in rig.values())
    res = {'window': [S, E], 'window_eff_end': E1, 'live_records': n_l, 'rig_records': n_r, 'first_L_E_dev': first_dev, 'domain_minutes': n_dom,
           'V10a_mismatch_minutes': in_bad, 'V10a_first': dom[:20], 'outside_domain_mismatch_minutes': out_bad,
           'live_buffer_bad_frames': bad, 'live_buffer': a.live_buffer}
    res['V10a_rule'] = 'ERRATA7: (1) L==R bit; hoac (2) L tap con bit cua R va symbol(R\\L) == S_m (symbol chuyen trang thai m+-1 tu do)'
    res['V10a_pass_eq'] = kinds['eq']; res['V10a_pass_subset'] = kinds['subset']; res['V10a_pass_subset_trans'] = kinds['subset_trans']
    res['V10a_not_bitexact_minutes'] = n_nbe; res['V10a_fail'] = fails[:200]; res['V10a_fail_n'] = len(fails)
    res['V10a_ok'] = in_bad == 0 and bad == 0
    res['ok'] = res['V10a_ok']
    json.dump(res, open(a.out, 'w'), indent=1)
    json.dump(diag, open(a.out.replace('.json', '') + '_diag.json', 'w'), indent=0)
    res['diag_file'] = a.out.replace('.json', '') + '_diag.json'
    print(json.dumps({k: res[k] for k in ('V10a_ok', 'live_records', 'rig_records', 'domain_minutes', 'V10a_mismatch_minutes', 'V10a_pass_eq',
                                          'V10a_pass_subset', 'V10a_pass_subset_trans', 'V10a_not_bitexact_minutes')} | {'outside_n': len(out_bad)}))
    return 0 if res['ok'] else 1


if __name__ == '__main__':
    sys.exit(main())
