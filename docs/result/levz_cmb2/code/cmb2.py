"""CMB2 (PREREG_X3_1127 part B): long DEV (4 seeds, hourly MTM from levz_an A1) + short chosen WITHOUT look-ahead (T1 WFO top-1
STATE / PART, gate NONE; 2024 cfg = report_t1 wfo.2024.chosen run on F2, 2025 cfg = wfo.2025.chosen run on F3; 2022-23 no short).
Combination = levz_an A1 method (c1_combo.py): per-day additive relative paths r_comb = r_long + m * r_short on common equity,
rebalanced daily (approximation of sizing the short on combined equity), m = 1. Short MTM hourly from B1 port ledger (mk/hm arrays).
In-sample reference (labelled): best DEV_ret config of each family (gate NONE), DEV contiguous 2022-2025."""
import sys, os, json, logging
sys.dont_write_bytecode = True
import numpy as np, pandas as pd
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s',
                    handlers=[logging.FileHandler('/home/ubuntu/claude_master/w3/levz_cmb2/logs/cmb2.log'), logging.StreamHandler()])
log = logging.getLogger('cmb2')
sys.path.insert(0, '/home/ubuntu/claude_master/w3/levz_t1/code')
import common_t1 as C
sys.path.pop(0)
OUT = '/home/ubuntu/claude_master/w3/levz_cmb2/out'
CB = C.CB
P = C.b1('port')
XB1 = C.b1('exits')
E = C.load('exits_t1')
S = P.S
H0, H, M, CUT, DEV0 = 1638316800000, 3600000, 60000, 1767225600000, 1640995200000
assert CB.H0 == H0
RUNS = ('c0s42', 'c0s7', 'c0s123', 'c0s13')
LD = '/home/ubuntu/claude_master/w3/p15_stab/s2/k/%s'
m_ = 1.0

g = pd.read_parquet(C.OUT + '/grid_t1.parquet').set_index('cfg_id')
rep = json.load(open(C.OUT + '/report_t1.json'))
zt = XB1.load_table()
hourly = {kk: zt[kk] for kk in ('mk', 'hm', 'fh', 'fc', 'p0')}
czf = np.load(CB.WORK + '/cand_b1.npz')
T = {}
def tab(f):
    if f not in T:
        T[f] = E.load_family(f, hourly)
        assert (T[f]['k'] == zt['k']).all() and (T[f]['c'] == zt['c']).all()
    return T[f]
def cand(z):
    return P.CandB1(*(czf['W7_E0_%.1f_%s' % (z, s)] for s in ('k', 'c', 's', 'cid')))
def kr(a, b):
    return S.kidx(S.ms(a)), S.kidx(S.ms(b)) - 1
def runc(cid, a, b):
    r = g.loc[cid]
    assert r['gate'] == 'NONE' and r['W'] == 7 and r['E'] == 'E0'
    k0, kl = kr(a, b)
    tr, eq, met = P.run(int(r['K']), cand(float(r['zmin'])), E.view(r['fam'], tab(r['fam']), int(r['xi'])), k0, kl)
    return tr, eq, met

# ---------------- short variants
CHK = {}
VAR = {}
for fam in ('STATE', 'PART'):
    w = rep['fam'][fam + '|NONE']['measures']['wfo']
    segs = []
    for y, fold, a, b in ((2024, 'F2', '2024-01-01', '2025-01-01'), (2025, 'F3', '2025-01-01', '2026-01-01')):
        cid = int(w[str(y)]['chosen'])
        tr, eq, met = runc(cid, a, b)
        ref = float(w[str(y)]['top1']['rets'][0])
        CHK['%s_%d' % (fam, y)] = dict(cfg_id=cid, select_folds=w[str(y)]['select_folds'], test=w[str(y)]['test_fold'],
                                      ret=met['ret'], report_top1=ref, grid=float(g.loc[cid, fold + '_ret']), n=int(met['n']),
                                      cfg={kk: (None if pd.isna(g.loc[cid, kk]) else g.loc[cid, kk]) for kk in ('fam', 'xi', 'zmin', 'K', 's', 'H', 'zo', 'R')})
        assert abs(met['ret'] - ref) < 1e-9 and abs(met['ret'] - CHK['%s_%d' % (fam, y)]['grid']) < 1e-9
        log.info('short %s %d cfg %d ret %.6f (report %.6f) n %d', fam, y, cid, met['ret'], ref, met['n'])
        segs.append((eq, tr))
    VAR['CMB-' + fam] = segs
    sub = g[(g['fam'] == fam) & (g['gate'] == 'NONE')]
    best = int(sub['DEV_ret'].idxmax())
    tr, eq, met = runc(best, '2022-01-01', '2026-01-01')
    assert abs(met['ret'] - float(g.loc[best, 'DEV_ret'])) < 1e-9
    CHK['INS_' + fam] = dict(cfg_id=best, ret_dev=met['ret'], n=int(met['n']),
                             cfg={kk: (None if pd.isna(g.loc[best, kk]) else g.loc[best, kk]) for kk in ('fam', 'xi', 'zmin', 'K', 's', 'H', 'zo')})
    VAR['INS-' + fam] = [(eq, tr)]
    log.info('in-sample %s cfg %d DEV ret %.4f', fam, best, met['ret'])

# ---------------- time grid (as A1 c1_combo)
tms = H0 + np.arange((DEV0 - H0) // H, (CUT - H0) // H, dtype=np.int64) * H
n = len(tms); tt = pd.to_datetime(tms, unit='ms', utc=True)
starts = np.flatnonzero(tt.hour == 0); ends = np.concatenate([starts[1:], [n - 1]]); di = np.searchsorted(starts, np.arange(n), 'right') - 1
days = tt[starts]

def short_series(segs):
    e = np.full(n, 10000.0); x = np.zeros(n); scale = 1.0
    trs = []
    for eq, tr in segs:
        idx = np.searchsorted(tms, eq['t'].values); assert (tms[idx] == eq['t'].values).all()
        e[idx] = eq['eq'].values * scale; x[idx] = np.nan_to_num(eq['expo'].values)
        if len(segs) > 1:
            assert abs(eq['eq'].values[0] - 10000.0) < 1e-6
        scale = e[idx[-1]] / 10000.0
        trs.append(tr)
    # carry flat after segment ends (none here: F3 ends at CUT-H)
    return e, x, pd.concat(trs, ignore_index=True)

def rel_day(e):
    base = e[starts][di]
    r = e / base - 1
    rd = e[ends] / e[starts] - 1
    return np.where(np.isfinite(r), r, 0.0), np.where(np.isfinite(rd), rd, 0.0)

def comb(rel, rd):
    cs = np.concatenate([[1.0], np.cumprod(1 + rd)])[:-1]
    return cs[di] * (1 + rel)

def mdd(e):
    e = np.asarray(e, float); return float(np.max(1 - e / np.maximum.accumulate(e)))

def metrics(cv):
    dv = np.append(cv[starts], cv[-1])
    cagr = (dv[-1] / dv[0]) ** (365.25 / (len(dv) - 1)) - 1
    dd = mdd(cv)
    yr = {}
    for y in (2022, 2023, 2024, 2025):
        a = np.flatnonzero(tt == pd.Timestamp('%d-01-01' % y, tz='UTC'))[0]
        z = np.flatnonzero(tt == pd.Timestamp('%d-01-01' % (y + 1), tz='UTC'))[0] if y < 2025 else n - 1
        yr[y] = float(cv[z] / cv[a] - 1)
    i24 = np.flatnonzero(tt == pd.Timestamp('2024-01-01', tz='UTC'))[0]
    return dict(cagr=cagr, mdd_h=dd, calmar=cagr / dd, mdd_h_2425=mdd(cv[i24:]), **{'r%d' % y: v for y, v in yr.items()})

SV = {v: short_series(s) for v, s in VAR.items()}
LH = pd.read_parquet('/home/ubuntu/claude_master/w3/levz_an/a1/out/long_hourly.parquet')
LM = json.load(open('/home/ubuntu/claude_master/w3/levz_an/a1/out/long_metrics.json'))['metrics']
syms = json.load(open('/home/ubuntu/claude_master/w3/levz2/work/sig_meta.json'))['syms']
col = {s: i for i, s in enumerate(syms)}

def tparse(s, sh):
    t = pd.to_datetime(s.astype(str).str.strip(), format='%Y%m%d %H:%M') + pd.Timedelta(hours=sh)
    return t.values.astype('datetime64[ms]').astype(np.int64)

rows, mon_rows, conf = [], [], []
for rn in RUNS:
    q = LH[(LH['run'] == rn) & (LH['t'] >= tms[0]) & (LH['t'] <= tms[-1])]
    assert len(q) == n and (q['t'].values == tms).all()
    le, lx, lnop = q['eq_mtm'].values, q['expo_mtm'].values, q['nopen'].values
    relL, rdL = rel_day(le)
    cL = comb(relL, rdL)
    ML = metrics(cL)
    # validation vs A1 audited numbers
    assert abs(ML['cagr'] - LM[rn]['cagr']) < 2e-3, (ML['cagr'], LM[rn]['cagr'])
    assert abs(ML['mdd_h'] - LM[rn]['mdd_mtm_hourly']) < 2e-3, (ML['mdd_h'], LM[rn]['mdd_mtm_hourly'])
    rows.append(dict(run=rn, var='LONG', **ML, gmax=float(lx.max()), both_h=0, n_short=0, conf_entry=0, conf_any=0,
                     a1_cagr=LM[rn]['cagr'], a1_mdd_h=LM[rn]['mdd_mtm_hourly']))
    d = pd.read_csv(LD % rn + '/storage/printDone.csv')
    d = d.loc[:, ~d.columns.str.startswith('Unnamed')]
    d['c'] = d['sym'].astype(str).add('USDT').map(col).fillna(-1).astype(int)
    d['ts'] = tparse(d['start'], -7); d['te'] = tparse(d['end'], -7)
    legs = {c: gg[['ts', 'te']].values for c, gg in d[d['c'] >= 0].groupby('c')}
    monL = pd.Series(rdL, index=days).add(1).resample('MS').prod() - 1
    for v, (se, sx, tr) in SV.items():
        relS, rdS = rel_day(se)
        cC = comb(relL + m_ * relS, rdL + m_ * rdS)
        MC = metrics(cC)
        gx = lx + m_ * sx
        te_ = H0 + tr['ke'].values * H + M
        tx_ = H0 + tr['kx'].values * H
        ce = ca = 0
        for c, a, b in zip(tr['c'].values, te_, tx_):
            L = legs.get(int(c))
            if L is None:
                continue
            ce += int(((L[:, 0] <= a) & (L[:, 1] > a)).any())
            ca += int(((L[:, 0] < b) & (L[:, 1] > a)).any())
        rows.append(dict(run=rn, var=v, **MC, gmax=float(gx.max()), g_gt1=int((gx > 1).sum()), both_h=int(((lnop > 0) & (sx > 0)).sum()),
                         short_h=int((sx > 0).sum()), n_short=len(tr), conf_entry=ce, conf_any=ca,
                         contrib={y: MC['r%d' % y] - ML['r%d' % y] for y in (2022, 2023, 2024, 2025)}))
        monS = pd.Series(rdS, index=days).add(1).resample('MS').prod() - 1
        monC = pd.Series(rdL + m_ * rdS, index=days).add(1).resample('MS').prod() - 1
        if v.startswith('CMB'):
            w3 = monS[monS.index.year >= 2024].nsmallest(3)
            for t_, r_ in w3.items():
                mon_rows.append(dict(run=rn, var=v, month=str(t_.date())[:7], short=float(r_), long=float(monL[t_]), comb=float(monC[t_])))
R = pd.DataFrame(rows)
R.to_json(OUT + '/cmb2_rows.json', orient='records', indent=1, default_handler=str)
pd.DataFrame(mon_rows).to_csv(OUT + '/cmb2_worst_months.csv', index=False)
json.dump(CHK, open(OUT + '/cmb2_check.json', 'w'), indent=1, default=float)
pd.set_option('display.width', 250); pd.set_option('display.max_columns', 40)
cols = ['run', 'var', 'cagr', 'mdd_h', 'calmar', 'mdd_h_2425', 'r2022', 'r2023', 'r2024', 'r2025', 'gmax', 'g_gt1', 'both_h', 'short_h', 'n_short', 'conf_entry', 'conf_any']
print(R[cols].round(4).to_string())
print(R.groupby('var')[['cagr', 'mdd_h', 'calmar', 'mdd_h_2425', 'r2022', 'r2023', 'r2024', 'r2025', 'gmax', 'both_h', 'conf_entry']].mean().round(4).to_string())
print(R[['run', 'var', 'contrib']].to_string())
print(pd.DataFrame(mon_rows).round(4).to_string())
print(json.dumps(CHK, default=float, indent=0))
log.info('cmb2 done')
