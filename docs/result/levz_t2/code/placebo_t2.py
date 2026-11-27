"""LEVZ T2 placebo (PREREG_LEVZ_T2 sec 4 (iv) + ADD1 M3). For each NEW entry type e (6) and rep r:
kind 'time' (main, 100 reps): every candidate FILLED for e (entry_t2) is re-entered at a minute drawn uniformly among the minutes
  60 k + i, i in 1..2880 (< data end), that have a REAL 1m bar; market sell at that close x (1 - 0.001). Same candidates / count.
kind 'perm' (descriptive, 20 reps): delays d (minutes) of the filled candidates are permuted WITHIN the signal calendar year; entry at
  60 k + d_perm if that minute is real, else the next real minute <= 60 k + 2880, else dropped (count logged); market x (1 - 0.001).
Then: exit table (exits_t2.compute, same engines), the full grid of e (3 zmin x 3 K x 211 = 1 899 configs, grid_t2 / port UNCHANGED),
WFO statistic select_t2.wfo_stat (top-20 median 2024 + 2025 over scored years). One part per (kind, e, rep); resumable;
seed default_rng([SEED, kind index, entry index, rep]) only => --shard i/n (task index % n == i) gives identical parts.
p (summary, needs the REAL grid): p = (1 + #{reps >= real}) / (1 + nrep); a rep missing a year the real entry type scored counts as
NOT >= real; real scored no year => p = NaN (U-c fails) (ADD1 M3).
LOCKED: python3 code/placebo_t2.py --real I_HAVE_A1_PASS [--kind time|perm] [--nrep N] [--entries ...] [--nproc N] [--shard i/n]
        [--out DIR]   (parts in DIR/placebo_t2_parts; default out/; on Kaggle use --out /kaggle/working/out)
        python3 code/placebo_t2.py --summary --real I_HAVE_A1_PASS     (p-values -> out/placebo_t2.json)"""
import glob
import json
import os
import sys
import time
sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common_t2 as C
sys.path.pop(0)
import numpy as np
import pandas as pd

log = C.setup_log('placebo')
CB = C.CB
SEED = 20261127
KINDS = ('time', 'perm')
NREP = {'time': 100, 'perm': 20}
G = {}


def draw_time(src, k, c, rng):
    """uniform real minute in 60 k + 1 .. 60 k + 2880 per candidate. Returns abs minutes (-1 if none)."""
    out = np.full(len(k), -1, dtype=np.int64)
    for i in range(len(k)):
        a = 60 * int(k[i]) + 1
        ok = np.flatnonzero(src.real(int(c[i]), a, a + C.WIN_MIN))
        if len(ok):
            out[i] = a + int(ok[rng.integers(len(ok))])
    return out


def draw_perm(src, k, c, d, rng):
    yr = C.year_of_k(k)
    dp = np.array(d, dtype=np.int64)
    for y in np.unique(yr):
        ix = np.flatnonzero(yr == y)
        dp[ix] = d[ix][rng.permutation(len(ix))]
    out = np.full(len(k), -1, dtype=np.int64)
    for i in range(len(k)):
        base = 60 * int(k[i])
        a = base + int(dp[i])
        ok = np.flatnonzero(src.real(int(c[i]), a, base + C.WIN_MIN + 1))
        if len(ok):
            out[i] = a + int(ok[0])
    return out


def rng_for(kind, e, r):
    return np.random.default_rng([SEED, KINDS.index(kind), C.ENTRIES.index(e), int(r)])


def filled(en, e):
    idx = np.flatnonzero(en[e + '_m'] >= 0)
    return idx, en['k'][idx], en['c'][idx], (en[e + '_m'][idx] - 60 * en['k'][idx])


def one_rep(kind, e, r, ctx_extra=None):
    """one placebo rep -> dict (no file IO). G must hold src, st, conds, en, cls."""
    t0 = time.time()
    XT = C.load('exits_t2')
    GR = C.load('grid_t2')
    SEL = C.load('select_t2')
    rng = rng_for(kind, e, r)
    idx, k, c, d = filled(G['en'], e)
    ms = draw_time(G['src'], k, c, rng) if kind == 'time' else draw_perm(G['src'], k, c, d, rng)
    ok = ms >= 0
    px = np.array([float(G['src'].close(int(cc), int(m), int(m) + 1)[0]) * (1.0 - C.MKT_SLIP) for cc, m in zip(c[ok], ms[ok])])
    out = XT.compute(G['st'], ms[ok], c[ok], px, G['conds'])
    out['k'], out['cid_b1'] = k[ok], G['en']['cid_b1'][idx[ok]]
    t1 = time.time()
    ctx = GR.build_ctx({e: out}, G['cls'], (e,))
    rows = [GR.run_cfg(ctx, cfg) for cfg in GR.task_order(C.all_cfgs((e,)))]
    GR._VC.clear()
    df = pd.DataFrame(rows).sort_values('cfg_id').reset_index(drop=True)
    st = SEL.wfo_stat(SEL.wfo(df))
    return dict(kind=kind, entry=e, rep=int(r), seed='%d_%d_%d_%d' % (SEED, KINDS.index(kind), C.ENTRIES.index(e), r),
                n_filled=int(len(k)), n_used=int(ok.sum()), n_dropped=int((~ok).sum()),
                med_delay_min=float(np.median(ms[ok] - 60 * k[ok])) if ok.any() else np.nan,
                wfo_sum=st['wfo_sum'], scored='/'.join(st['scored_years']), top20_2024=st['top20_2024'],
                top20_2025=st['top20_2025'], sec_exits=t1 - t0, sec_total=time.time() - t0)


def _work(t):
    return one_rep(*t)


def tasks(kinds, entries, nrep):
    return [(kd, e, r) for kd in kinds for r in range(nrep.get(kd, NREP[kd])) for e in entries]


def run(kinds, entries, nrep, parts, nproc=1, shard=(0, 1)):
    os.makedirs(parts, exist_ok=True)
    done = set()
    for f in glob.glob(parts + '/*.parquet'):
        x = pd.read_parquet(f, columns=['kind', 'entry', 'rep'])
        done |= set(zip(x['kind'], x['entry'], x['rep']))
    allt = tasks(kinds, entries, nrep)
    todo = [t for i, t in enumerate(allt) if i % shard[1] == shard[0] and t not in done]
    log.info('placebo_t2 todo=%d done=%d shard=%s', len(todo), len(done), shard)
    t0 = time.time()
    pool = None
    if nproc <= 1:
        it = map(_work, todo)
    else:
        import multiprocessing as mp
        pool = mp.get_context('fork').Pool(nproc)
        it = pool.imap_unordered(_work, todo, chunksize=1)
    try:
        for i, res in enumerate(it):
            fn = '%s/%s_%s_%04d.parquet' % (parts, res['kind'], res['entry'], res['rep'])
            pd.DataFrame([res]).to_parquet(fn + '.tmp', index=False)
            os.replace(fn + '.tmp', fn)
            log.info('placebo_t2 %d/%d %s %s %d %.1fs (rep %.1fs)', i + 1, len(todo), res['kind'], res['entry'], res['rep'],
                     time.time() - t0, res['sec_total'])
    finally:
        if pool is not None:
            pool.close()
            pool.join()
    return len(todo)


def setup(src=None, st=None, conds=None, en=None, cls=None):
    EN = C.load('entry_t2')
    XT = C.load('exits_t2')
    G['src'] = src if src is not None else EN.Src()
    G['st'] = st if st is not None else C.b1('exits').Store()
    G['conds'] = conds if conds is not None else XT.load_conds()
    G['en'] = en if en is not None else EN.load_entries()
    G['cls'] = cls if cls is not None else C.cand_classes()[0]


def p_value(rows, real):
    """ADD1 M3: real = dict(wfo_sum, scored_years). rows: placebo records."""
    ry = list(real['scored_years'])
    if not ry or not np.isfinite(real['wfo_sum']):
        return float('nan'), 0
    ge = 0
    for r in rows:
        sc = set(str(r['scored']).split('/')) if r['scored'] else set()
        if not set(ry) <= sc:
            continue
        v = float(sum(r['top20_%s' % Y] for Y in ry))
        ge += int(v >= real['wfo_sum'])
    return (1.0 + ge) / (1.0 + len(rows)), ge


def summarize(parts, real_stats, nrep=NREP):
    df = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(parts + '/*.parquet'))], ignore_index=True)
    df = df.drop_duplicates(['kind', 'entry', 'rep'])
    res = {}
    for kd in KINDS:
        for e in C.NEW_ENTRIES:
            d = df[(df['kind'] == kd) & (df['entry'] == e)]
            if not len(d):
                continue
            p, ge = p_value(d.to_dict('records'), real_stats[e])
            res['%s|%s' % (kd, e)] = dict(nrep=int(len(d)), complete=bool(len(d) == nrep[kd]), p=p, n_ge=ge,
                                          real=real_stats[e], q05_50_95=[float(x) for x in np.nanquantile(d['wfo_sum'], [.05, .5, .95])]
                                          if d['wfo_sum'].notna().any() else None,
                                          scored_counts={str(a): int(b) for a, b in d['scored'].value_counts().items()},
                                          n_dropped_max=int(d['n_dropped'].max()))
    return res


def main(argv):
    C.require_real(argv)
    out = argv[argv.index('--out') + 1] if '--out' in argv else C.OUT
    parts = out + '/placebo_t2_parts'
    if '--summary' in argv:
        with open(C.OUT + '/select_t2.json') as fh:
            sel = json.load(fh)
        res = summarize(parts, {e: sel[e]['stat'] for e in C.NEW_ENTRIES})
        with open(C.OUT + '/placebo_t2.json.tmp', 'w') as fh:
            json.dump(dict(seed=SEED, nrep=NREP, res=res), fh, indent=1, default=float)
        os.replace(C.OUT + '/placebo_t2.json.tmp', C.OUT + '/placebo_t2.json')
        log.info('placebo_t2 summary done (CHUA AUDIT)')
        return
    kinds = (argv[argv.index('--kind') + 1],) if '--kind' in argv else KINDS
    entries = tuple(argv[argv.index('--entries') + 1].split(',')) if '--entries' in argv else C.NEW_ENTRIES
    assert set(entries) <= set(C.NEW_ENTRIES)
    nrep = dict(NREP)
    if '--nrep' in argv:
        for kd in kinds:
            nrep[kd] = int(argv[argv.index('--nrep') + 1])
    nproc = int(argv[argv.index('--nproc') + 1]) if '--nproc' in argv else 1
    setup()
    run(kinds, entries, nrep, parts, nproc, C.shard_arg(argv))


if __name__ == '__main__':
    main(sys.argv[1:])
