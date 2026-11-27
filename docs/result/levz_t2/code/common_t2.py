"""LEVZ T2 shared constants, grid, loaders (PREREG_LEVZ_T2 @b0515b3c). B1 / T1 / tier-1 code imported READ-ONLY by file path
(never modified). Entry types (prereg sec 2): E0 (B1 entry), EL_b (limit at p0 (1 + b)), EB (24 h low breakdown), EO_x (OI down x %
from its max since the signal). Exits (sec 3): 195 B1 + 8 PART + 8 STATE (T1) = 211. Grid: 7 entries x 3 zmin x 3 K x 211 = 13 293."""
import importlib.util
import itertools
import logging
import os
import sys
sys.dont_write_bytecode = True
import numpy as np

BASE = '/home/ubuntu/claude_master/w3/levz_t2'
WORK = BASE + '/work'
OUT = BASE + '/out'
T1CODE = '/home/ubuntu/claude_master/w3/levz_t1/code'
T1WORK = '/home/ubuntu/claude_master/w3/levz_t1/work'
T1OUT = '/home/ubuntu/claude_master/w3/levz_t1/out'
OIDIR = '/home/ubuntu/claude_master/w3/levz/work'      # tier-1 hourly OI (oi_YYYY-MM.parquet: sym, h, x = log OI, tsr)
REAL_KEY = 'I_HAVE_A1_PASS'


def _imp(name, path):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


C1 = _imp('common_t1', T1CODE + '/common_t1.py')     # same module name T1 modules use internally
CB = C1.CB                                            # B1 common_b1


def b1(name):
    return C1.b1(name)


def t1(name):
    return C1.load(name)


def load(name):
    """levz_t2/code/<name>.py by file path (module name t2_<name>)."""
    return _imp('t2_' + name, os.path.join(os.path.dirname(os.path.abspath(__file__)), name + '.py'))


def setup_log(name):
    root = logging.getLogger()
    if not root.handlers:
        logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s %(message)s')
    return logging.getLogger('levz_t2.' + name)


def require_real(argv):
    if '--real' not in argv or argv[argv.index('--real') + 1:argv.index('--real') + 2] != [REAL_KEY]:
        raise SystemExit('LOCKED: real-data run needs --real %s (after A1 code audit PASS)' % REAL_KEY)


def shard_arg(argv):
    if '--shard' not in argv:
        return (0, 1)
    a, b = argv[argv.index('--shard') + 1].split('/')
    s = (int(a), int(b))
    assert 0 <= s[0] < s[1]
    return s


# ---------------------------------------------------------------- time / prices
M = CB.M
H = CB.H
H0, NH, NMIN, HMAX, NPATH = CB.H0, CB.NH, CB.NMIN, CB.HMAX, CB.NPATH
WIN_H = 48                       # waiting window 48 h from the signal
WIN_MIN = WIN_H * 60             # 2 880
MKT_SLIP = 0.001                 # market entries (EB, EO, placebo): sell at close x (1 - 0.001)
HW = HMAX + 2                    # hourly arrays width 722: entry minute offset r <= 59 inside hour kb => exit hour <= kb + 721
NPATH2 = (HW - 1) * 60 + 1       # kb-aligned path length 43 261

# ---------------------------------------------------------------- entry types (prereg sec 2)
ENTRIES = ('E0', 'EL_1', 'EL_2', 'EL_3', 'EB', 'EO_3', 'EO_5')
NEW_ENTRIES = ENTRIES[1:]
EL_B = {'EL_1': 0.01, 'EL_2': 0.02, 'EL_3': 0.03}
EO_X = {'EO_3': 0.03, 'EO_5': 0.05}
EB_LOOKBACK = 24

# ---------------------------------------------------------------- exits (sec 3)
ZS = (2.5, 3.0, 3.5)
KS = (3, 5, 10)
XFAMS = ('B1', 'PART', 'STATE')


def exit_list():
    """211 exits: (xfam, xi, params) in fixed order; B1 xi = common_b1.XCFGS index; PART / STATE xi = T1 fam_cfgs index."""
    out = [('B1', i, dict(SL=x[0], H=x[1], arm=x[2], gap=x[3])) for i, x in enumerate(CB.XCFGS)]
    out += [('PART', i, dict(x)) for i, x in enumerate(C1.fam_cfgs('PART'))]
    out += [('STATE', i, dict(x)) for i, x in enumerate(C1.fam_cfgs('STATE'))]
    assert len(out) == 211
    return out


XLIST = exit_list()
PCOLS = ('SL', 'H', 'arm', 'gap', 's', 'zo')


def all_cfgs(entries=ENTRIES):
    """full grid: entry x zmin x K x exit; cfg_id = index in the FULL grid (stable under entry subsets)."""
    res = []
    for i, (e, z, K, (xf, xi, xp)) in enumerate(itertools.product(ENTRIES, ZS, KS, XLIST)):
        if e not in entries:
            continue
        d = dict(cfg_id=i, entry=e, W=7, zmin=z, K=K, xfam=xf, xi=xi)
        for p in PCOLS:
            d[p] = float(xp[p]) if p in xp else np.nan
        res.append(d)
    return res


N_TOTAL = len(ENTRIES) * len(ZS) * len(KS) * len(XLIST)
assert N_TOTAL == 13293
N_PER_ENTRY = N_TOTAL // len(ENTRIES)    # 1 899


def cand_classes(cz=None):
    """W7_E0 classes of cand_b1: {zmin: (k, c, s, cid_b1)} and the union (sorted unique cid_b1) -> (k, c)."""
    if cz is None:
        cz = np.load(CB.WORK + '/cand_b1.npz')
    cls = {z: tuple(np.asarray(cz['W7_E0_%.1f_%s' % (z, s)]) for s in ('k', 'c', 's', 'cid')) for z in ZS}
    ucid = np.unique(np.concatenate([cls[z][3] for z in ZS]))
    uk, uc = np.asarray(cz['U_k'])[ucid], np.asarray(cz['U_c'])[ucid]
    return cls, ucid, uk, uc


def year_of_k(k):
    import pandas as pd
    return pd.to_datetime(H0 + np.asarray(k, dtype=np.int64) * H, unit='ms').year.values
