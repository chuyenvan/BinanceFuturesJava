"""LEVZ B1 shared constants + loaders (PREREG_LEVZ_B1 @54f40792). B0 code (w3/levz2/code) is imported read-only by file path."""
import os
import sys
import importlib.util
import json
sys.dont_write_bytecode = True
import numpy as np

BASE = '/home/ubuntu/claude_master/w3/levz_b1'
WORK = BASE + '/work'
OUT = BASE + '/out'
L2 = '/home/ubuntu/claude_master/w3/levz2'
L2CODE = L2 + '/code'
KL = '/home/ubuntu/claude_master/res1109/r1_s1/kl/kline1m-%s.parquet'
M = 60000
H = 3600000
H0 = 1638316800000        # 2021-12-01 00:00 UTC
CUT = 1767225600000       # 2026-01-01 00:00 UTC
NMIN = (CUT - H0) // M    # 2 148 480 minutes
NH = (CUT - H0) // H      # 35 808 hours
HMAX = 720                # max hold hours
NPATH = HMAX * 60 + 1     # path minutes 0..43200
MISS_MIN = 1440           # missing run > 24 h => exit (the 1441st missing minute)
SL_SLIP = 0.003
TR_SLIP = 0.001
SLS = (0.15, 0.30, 0.50)
HS = (24, 72, 168, 336, 720)
ARMS = (0.03, 0.05, 0.07, 0.10)
GAPS = (0.02, 0.03, 0.05)
TRAILS = ((0.0, 0.0),) + tuple((a, g) for a in ARMS for g in GAPS)   # 13; (0,0) = off
R_SL, R_TRAIL, R_TIME, R_MISS, R_EOD = 0, 1, 2, 3, 4
RNAMES = ('sl', 'trail', 'time', 'miss', 'eod')


def exit_cfgs():
    """195 exit configs, fixed order: SL x H x trail. index = xi."""
    out = []
    for sl in SLS:
        for hh in HS:
            for a, g in TRAILS:
                out.append((sl, hh, a, g))
    assert len(out) == 195
    return out


XCFGS = exit_cfgs()


def xidx(sl, hh, a, g):
    return XCFGS.index((float(sl), int(hh), float(a), float(g)))


def load_b0(name):
    """import levz2/code/<name>.py as module levz2_<name> (same naming as B0 so siblings are shared)."""
    mn = 'levz2_' + name
    if mn in sys.modules:
        return sys.modules[mn]
    spec = importlib.util.spec_from_file_location(mn, os.path.join(L2CODE, name + '.py'))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mn] = mod
    spec.loader.exec_module(mod)
    return mod


def meta():
    with open(L2 + '/work/sig_meta.json') as fh:
        m = json.load(fh)
    assert m['H0'] == H0 and m['NH'] == NH
    return m


def ym_list():
    out = []
    y, mo = 2021, 12
    while (y, mo) <= (2025, 12):
        out.append('%04d-%02d' % (y, mo))
        mo += 1
        if mo == 13:
            y, mo = y + 1, 1
    return out


def load(name):
    """import levz_b1/code/<name>.py by file path under module name <name> (never via sys.path)."""
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, os.path.join(os.path.dirname(os.path.abspath(__file__)), name + '.py'))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod
