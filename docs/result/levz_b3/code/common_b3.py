"""LEVZ B3 shared constants + loaders (PREREG_LEVZ_B3 @30a8c413). B0 (levz2), B1 (levz_b1), B2 (levz_b2) code is imported
read-only BY FILE PATH (never edited). Data < 2026-01-01 UTC only (CUT of B1)."""
import os
import sys
import importlib.util
sys.dont_write_bytecode = True
import numpy as np

BASE = '/home/ubuntu/claude_master/w3/levz_b3'
WORK = BASE + '/work'
OUT = BASE + '/out'
B1CODE = '/home/ubuntu/claude_master/w3/levz_b1/code'
B2CODE = '/home/ubuntu/claude_master/w3/levz_b2/code'
B1WORK = '/home/ubuntu/claude_master/w3/levz_b1/work'
B1OUT = '/home/ubuntu/claude_master/w3/levz_b1/out'
B2WORK = '/home/ubuntu/claude_master/w3/levz_b2/work'
L1WORK = '/home/ubuntu/claude_master/w3/levz/work'
W = 7
E = 'E0'
ZMIN = 1.5                 # pool (prereg sec 2)
ZLEV = 2.5                 # 'LEV' state (prereg sec 4 market features)
REG_Z = (2.5, 3.0, 3.5)    # regression subsets vs cand_b1.npz
DOT_GAP_H = 24             # same coin, gap < 24 h => same dot
C0_TOTAL = 600
C0_LAST = 300
YEARS_TEST = (2024, 2025)
TRAIN_START = '2022-01-01'


def b1(name):
    """B1 module by file path; same module names B1 uses internally (common_b1, port, exits, ...)."""
    if name in sys.modules:
        return sys.modules[name]
    if name == 'common_b1':
        spec = importlib.util.spec_from_file_location('common_b1', os.path.join(B1CODE, 'common_b1.py'))
        mod = importlib.util.module_from_spec(spec)
        sys.modules['common_b1'] = mod
        spec.loader.exec_module(mod)
        return mod
    CB = b1('common_b1')
    return CB.load(name)


def b2(name):
    mn = 'b2_' + name
    if mn in sys.modules:
        return sys.modules[mn]
    sys.path.insert(0, B2CODE)
    try:
        spec = importlib.util.spec_from_file_location(mn, os.path.join(B2CODE, name + '.py'))
        mod = importlib.util.module_from_spec(spec)
        sys.modules[mn] = mod
        spec.loader.exec_module(mod)
    finally:
        if sys.path and sys.path[0] == B2CODE:
            sys.path.pop(0)
    return mod


def b3(name):
    mn = 'b3_' + name
    if mn in sys.modules:
        return sys.modules[mn]
    spec = importlib.util.spec_from_file_location(mn, os.path.join(os.path.dirname(os.path.abspath(__file__)), name + '.py'))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mn] = mod
    spec.loader.exec_module(mod)
    return mod


CB = b1('common_b1')
H0, H, CUT, NH = CB.H0, CB.H, CB.CUT, CB.NH


def ms(s):
    import pandas as pd
    return int(pd.Timestamp(s, tz='UTC').value // 10**6)


def kidx(t_ms):
    return int((t_ms - H0) // H)


def year_k0(y):
    return kidx(ms('%d-01-01' % y))


def year_of_k(k):
    """UTC calendar year of hour index k (array ok)."""
    t = (H0 + np.asarray(k, dtype=np.int64) * H).astype('datetime64[ms]')
    return t.astype('datetime64[Y]').astype(np.int64) + 1970


def quarter_of_k(k):
    t = (H0 + np.asarray(k, dtype=np.int64) * H).astype('datetime64[ms]')
    m = t.astype('datetime64[M]').astype(np.int64)      # months since 1970-01
    return (m // 3).astype(np.int64)                      # calendar-quarter id
