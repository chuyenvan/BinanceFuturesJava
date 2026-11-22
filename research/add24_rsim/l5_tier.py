#!/usr/bin/env python3
"""ADD24 LUOT5 1a/1c/1e (DEV-B). Tier CU cua sim (cap nhat chi khi createOrder qua gate roi vao getCoinTier o phut %60==0)
vs tier DUNG theo gio (nhip production) tinh tu ticker CUA SIM (ho4p1-tk26). KHONG PnL: E chi dung noi bo de tinh U va % von.
In: l5/cums.csv, l5/dca_all.csv (Add24DcaAll), l5/tier_hourly.csv.gz, printDone. Out: l5/tier_impact.json + bang text (stdout)."""
import csv, gzip, json, logging, statistics as st, sys
from collections import defaultdict
from bisect import bisect_right
from datetime import datetime, timezone, timedelta
logging.basicConfig(level=logging.INFO, format='%(message)s'); L = logging.getLogger()
TZ7 = timezone(timedelta(hours=7)); S = '/dev/shm/add24/b/l5'; HR = 3600000; MIN = 60000; UMAX = 0.6; CAP0 = 35000.0
d7 = lambda s: int(datetime.strptime(s, '%Y%m%d %H:%M').replace(tzinfo=TZ7).timestamp() * 1000)
f7 = lambda ms: datetime.fromtimestamp(ms / 1000, TZ7).strftime('%Y-%m-%d %H:%M')
qq = lambda ms: '%dQ%d' % (datetime.fromtimestamp(ms / 1000, TZ7).year, (datetime.fromtimestamp(ms / 1000, TZ7).month - 1) // 3 + 1)
LO = int(datetime(2026, 1, 1, tzinfo=TZ7).timestamp() * 1000); HI = int(datetime(2026, 9, 30, 23, 59, tzinfo=TZ7).timestamp() * 1000)
LO25 = int(datetime(2025, 10, 1, tzinfo=TZ7).timestamp() * 1000)
PD = '/home/ubuntu/claude_master/w3/ho5/out/ho5-a3-l26-s123/storage/printDone.csv'
# --- tier theo gio: tap symbol KHONG T3 (rank < int(n*0.8)); vang mat = UNKNOWN -> T3
ok = {}
with gzip.open(S + '/tier_hourly.csv.gz', 'rt') as f:
    for ln in f:
        h, s, r, n = ln.rstrip().split(',')
        h = int(h)
        if int(r) < int(int(n) * 0.80): ok.setdefault(h, set()).add(s)
        else: ok.setdefault(h, set())
hours = sorted(ok)
def t3_at_hour(sym, h):
    if h not in ok: return None
    return sym not in ok[h]
fresh_t3 = lambda sym, t: t3_at_hour(sym, (t // HR) * HR)
# --- printDone: legs, realized (noi bo) cho E, margin running cho U
legs = []
for r in csv.DictReader(open(PD)):
    legs.append(dict(sym=r['sym'] + 'USDT', s=d7(r['start']), e=d7(r['end']), lv=r['level'], m=float(r['margin']), pnl=float(r['pnl'])))
close_ev = sorted((x['e'], x['pnl']) for x in legs); cts = [c[0] for c in close_ev]; cum = []
acc = 0.0
for c in close_ev: acc += c[1]; cum.append(acc)
def E_at(t):  # 35000 + realized (khong MTM) -- noi bo, KHONG in
    i = bisect_right(cts, t - 1); return CAP0 + (cum[i - 1] if i else 0.0)
def U_at(t):
    mr = sum(x['m'] for x in legs if x['s'] <= t < x['e']); return mr / E_at(t)
# --- moc cap nhat tier sim: (A) leg printDone o phut %60==0
upd_pd = sorted({x['s'] for x in legs if x['s'] % HR == 0})
# --- cums + dca_all
cums = {}
for r in csv.DictReader(open(S + '/cums.csv')):
    ls = [(int(a.split(':')[0]), a.split(':')[1], float(a.split(':')[2])) for a in r['legs'].split(';')]
    cums[r['cid']] = dict(sym=r['sym'], t0=int(r['t0']), te=int(r['tEnd']), legs=ls, sim_dca=[x[0] for x in ls[1:]], m0=ls[0][2], lv0=r['lv0'])
elig = defaultdict(list)
for r in csv.DictReader(open(S + '/dca_all.csv')):
    elig[r['cid']].append((int(r['t']), int(r['mask'])))
for c in elig.values(): c.sort()
def lc_sim(c, t):  # legCount sim truoc phut t (leg DCA o chinh phut t chua tinh)
    return 1 + sum(1 for x in c['sim_dca'] if x < t)
# (B) ung vien DCA cua sim o phut %60==0 (qua gate, cham bac voi legCount sim) -> vao createOrder -> getCoinTier -> cap nhat
upd_dca = sorted({t for cid, ev in elig.items() for t, mk in ev if t % HR == 0 and (mk >> (lc_sim(cums[cid], t) - 1)) & 1})
upd = sorted(set(upd_pd) | set(upd_dca))
def last_upd(t):
    i = bisect_right(upd, t); return upd[i - 1] if i else None
def stale_t3(sym, t):
    u = last_upd(t); return None if u is None else t3_at_hour(sym, u)
# ---------- 1a
rows_a = []; prev = None
for u in [x for x in upd if LO25 <= x <= HI]:
    src = ('PD' if u in upd_pd else '') + ('+DCA' if u in upd_dca else '')
    rows_a.append((f7(u), round((u - prev) / 86400000, 2) if prev else None, src)); prev = u
def stale_days(t): u = last_upd(t); return None if u is None else (t - u) / 86400000
pr_ts = [x['s'] for x in legs if LO <= x['s'] <= HI and x['lv'] == 'PREDICT_SYMBOL_TRADE']
dca_ts = [x['s'] for x in legs if LO <= x['s'] <= HI and x['lv'] == 'DCA_LEVEL1']
el_ts = [t for ev in elig.values() for t, _ in ev if LO <= t <= HI]
def stats(v):
    v = [x for x in v if x is not None]
    return dict(n=len(v), mean=round(st.mean(v), 2), median=round(st.median(v), 2), max=round(max(v), 2)) if v else dict(n=0)
A = dict(moments=rows_a, n_2026=sum(1 for u in upd if LO <= u <= HI), n_from_pd=len([u for u in upd_pd if LO <= u <= HI]), n_from_dca=len([u for u in upd_dca if LO <= u <= HI]),
         stale_at_predict=stats([stale_days(t) for t in pr_ts]), stale_at_sim_dca_leg=stats([stale_days(t) for t in dca_ts]),
         stale_at_dca_eligible_minute=stats([stale_days(t) for t in el_ts]))
# ---------- 1c: duong sim (tier cu) va duong production (tier dung), moi cum
def walk(c, ev, tierfn, follow_sim=False):
    lc = 1; out = []; blocked = []; ublk = 0
    for t, mk in ev:
        if t < LO or t > HI: continue
        if follow_sim: lc = lc_sim(c, t)
        if not (mk >> (lc - 1)) & 1: continue
        t3 = tierfn(c['sym'], t)
        if t3 is None or t3: blocked.append(t); continue
        if U_at(t) >= UMAX: ublk += 1; continue
        if not follow_sim: out.append(t); lc += 1
        else:
            out.append(t)
    return out, blocked, ublk
val = dict(match=0, miss=0, detail=[])
res = []
for cid, c in cums.items():
    ev = elig.get(cid, [])
    # validate: mo hinh tier cu tai tao leg DCA thuc cua sim?
    for k, s in enumerate(c['sim_dca']):
        lc = k + 1
        cand = [t for t, mk in ev if (mk >> (lc - 1)) & 1 and (k == 0 or t > c['sim_dca'][k - 1]) and t <= s]
        firstok = None
        for t in cand:
            t3 = stale_t3(c['sym'], t)
            if t3 is False and U_at(t) < UMAX: firstok = t; break
        if firstok == s: val['match'] += 1
        else: val['miss'] += 1; val['detail'].append((cid, f7(s), f7(firstok) if firstok else None, len(cand)))
    sim_legs = c['sim_dca']
    prod_legs, _, ub = walk(c, ev, fresh_t3)
    # su kien phut: sim chan (tier cu T3) nhung tier dung khong T3, va nguoc lai, tren cac phut du dieu kien (theo legCount sim)
    m_i = m_ii = m_same = 0
    for t, mk in ev:
        if t < LO or t > HI: continue
        lc = lc_sim(c, t)
        if not (mk >> (lc - 1)) & 1 or U_at(t) >= UMAX: continue
        a, b = stale_t3(c['sym'], t), fresh_t3(c['sym'], t)
        if a is None or b is None: continue
        if a and not b: m_i += 1
        elif b and not a: m_ii += 1
        else: m_same += 1
    res.append(dict(cid=cid, sym=c['sym'], t0=c['t0'], q=qq(c['t0']), sim=sim_legs, prod=prod_legs, m0=c['m0'], m_i=m_i, m_ii=m_ii, m_same=m_same,
                    sim_m=[x[2] for x in c['legs'][1:]]))
# phan loai theo leg index
def pctE(m, t): return 100.0 * m / E_at(t)
ratio = [x[2] / E_at(x[0]) for c in cums.values() for x in c['legs'][1:]]
med_ratio = st.median(ratio) if ratio else None
Q = defaultdict(lambda: dict(i_cum=set(), i_leg=0, i_pct=0.0, i_earlier_h=[], i_never=0, ii_cum=set(), ii_leg=0, ii_pct=0.0, ii_later_h=[], ii_never=0,
                             same_cum=set(), same_leg=0, min_i=0, min_ii=0, min_same=0, list_i=[], list_ii=[]))
for r in res:
    q = Q[r['q']]; q['min_i'] += r['m_i']; q['min_ii'] += r['m_ii']; q['min_same'] += r['m_same']
    n = max(len(r['sim']), len(r['prod']))
    for k in range(n):
        s = r['sim'][k] if k < len(r['sim']) else None; p = r['prod'][k] if k < len(r['prod']) else None
        if s is not None and p is not None and s == p: q['same_cum'].add(r['cid']); q['same_leg'] += 1; continue
        if p is not None and (s is None or p < s):
            q['i_cum'].add(r['cid']); q['i_leg'] += 1
            mm = r['sim_m'][k] if k < len(r['sim_m']) else med_ratio * E_at(p)
            q['i_pct'] += pctE(mm, p)
            if s is None: q['i_never'] += 1
            else: q['i_earlier_h'].append(round((s - p) / HR, 2))
            q['list_i'].append('%s %s leg%d prod=%s sim=%s' % (r['sym'], f7(r['t0'])[:10], k + 1, f7(p), f7(s) if s else '-'))
        else:
            q['ii_cum'].add(r['cid']); q['ii_leg'] += 1
            q['ii_pct'] += pctE(r['sim_m'][k], s)
            if p is None: q['ii_never'] += 1
            else: q['ii_later_h'].append(round((p - s) / HR, 2))
            q['list_ii'].append('%s %s leg%d sim=%s prod=%s' % (r['sym'], f7(r['t0'])[:10], k + 1, f7(s), f7(p) if p else '-'))
C = {}
for k in sorted(Q):
    q = Q[k]
    C[k] = dict(i_cums=len(q['i_cum']), i_legs=q['i_leg'], i_pct_von_sum=round(q['i_pct'], 2), i_sim_never=q['i_never'], i_earlier_h=q['i_earlier_h'],
                ii_cums=len(q['ii_cum']), ii_legs=q['ii_leg'], ii_pct_von_sum=round(q['ii_pct'], 2), ii_prod_never=q['ii_never'], ii_later_h=q['ii_later_h'],
                same_cums=len(q['same_cum']), same_legs=q['same_leg'], minutes_i=q['min_i'], minutes_ii=q['min_ii'], minutes_same=q['min_same'],
                list_i=q['list_i'], list_ii=q['list_ii'])
# 1e OW1: cum co leg0 06-25
E1 = [dict(cid=r['cid'], sim=[f7(x) for x in r['sim']], prod=[f7(x) for x in r['prod']],
           tier_at_sim_legs=[dict(t=f7(x), last_upd=f7(last_upd(x)), stale_t3=stale_t3(r['sym'], x), fresh_t3=fresh_t3(r['sym'], x)) for x in r['sim']],
           first_elig=[(f7(t), mk, stale_t3(r['sym'], t), fresh_t3(r['sym'], t)) for t, mk in elig.get(r['cid'], [])[:12]])
      for r in res if r['sim'] and f7(r['t0']).startswith('2026-06-25')]
out = dict(A=A, validate=val, C=C, med_dca_margin_ratio_E=med_ratio, n_cums=len(cums), n_cums_with_elig=sum(1 for c in cums if elig.get(c)),
           n_sim_dca_legs=sum(len(c['sim_dca']) for c in cums.values()), E1=E1)
json.dump(out, open(S + '/tier_impact.json', 'w'), indent=1)
L.info(json.dumps(dict(A={k: v for k, v in A.items() if k != 'moments'}, validate=dict(match=val['match'], miss=val['miss'], detail=val['detail'][:10]),
                       C={k: {kk: vv for kk, vv in v.items() if not kk.startswith('list')} for k, v in C.items()}, n_cums=out['n_cums'],
                       n_cums_with_elig=out['n_cums_with_elig'], n_sim_dca_legs=out['n_sim_dca_legs']), indent=0))
