"""LEVZ T1 shared constants, grids, loaders (PREREG_LEVZ_T1 @186f2a5a). B1/B2 code imported read-only by file path."""
import os
import sys
import importlib.util
import itertools
sys.dont_write_bytecode = True
import numpy as np

BASE = '/home/ubuntu/claude_master/w3/levz_t1'
WORK = BASE + '/work'
OUT = BASE + '/out'
B1 = '/home/ubuntu/claude_master/w3/levz_b1'
B1CODE = B1 + '/code'
B2CODE = '/home/ubuntu/claude_master/w3/levz_b2/code'
L2 = '/home/ubuntu/claude_master/w3/levz2'
B3SEL = '/home/ubuntu/claude_master/w3/levz_b3/out/exitsel_b3.json'


def b1(name):
    """import levz_b1/code/<name>.py under module name <name> (same names B1 uses internally; same as B2 b2c.b1)."""
    if name in sys.modules:
        return sys.modules[name]
    sys.path.insert(0, B1CODE)
    try:
        if name == 'common_b1':
            import common_b1 as m
            return m
        return b1('common_b1').load(name)
    finally:
        if sys.path and sys.path[0] == B1CODE:
            sys.path.pop(0)


def b2(name):
    """B2 modules (mkt, opts) via B2's own loader (module names b2_<name>)."""
    sys.path.insert(0, B2CODE)
    try:
        import b2c
    finally:
        sys.path.pop(0)
    return b2c.b2(name)


def load(name):
    """import levz_t1/code/<name>.py by file path (module name t1_<name>)."""
    mn = 't1_' + name
    if mn in sys.modules:
        return sys.modules[mn]
    spec = importlib.util.spec_from_file_location(mn, os.path.join(os.path.dirname(os.path.abspath(__file__)), name + '.py'))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mn] = mod
    spec.loader.exec_module(mod)
    return mod


CB = b1('common_b1')
H0, NH, NPATH, HMAX = CB.H0, CB.NH, CB.NPATH, CB.HMAX
SL_SLIP = CB.SL_SLIP          # 0.003, also used for the PART break-even stop (market order)
FEE = 0.0007
EXPO = 0.60
# T1 reason codes (rt) and their mapping onto the B1 port reason codes (rs; port.py prints CB.RNAMES[rs])
RT_SL, RT_TRAIL, RT_TIME, RT_MISS, RT_EOD, RT_TP, RT_STATE, RT_BE = 0, 1, 2, 3, 4, 5, 6, 7
RTNAMES = ('sl', 'trail', 'time', 'miss', 'eod', 'tp', 'state', 'be')
RT2RS = np.array([CB.R_SL, CB.R_TRAIL, CB.R_TIME, CB.R_MISS, CB.R_EOD, CB.R_TRAIL, CB.R_TIME, CB.R_SL], dtype=np.int8)

# ---------------------------------------------------------------- family grids (prereg sec 3), fixed order = xi
BRK_S = (0.03, 0.05, 0.08, 0.12, 0.15, 0.20)
BRK_R = (0.5, 1.0, 1.5, 2.0, 3.0)
BRK_H = (24, 72, 168)
VOL_A = (1.0, 1.5, 2.0, 3.0)
VOL_R = (1.0, 2.0, 3.0, 0.0)          # 0.0 = no TP
VOL_H = (24, 72, 168)
VOL_WIN = 168
VOL_FLOOR, VOL_CAP = 0.02, 0.50
VOL_MINRET = 24                       # CHOICES_T1: < 24 valid hourly returns => SL = cap
PART_S = (0.05, 0.08, 0.12, 0.15)
PART_H = (72, 168)
PART_FRAC = 0.5
PART_TPX = 3.0
STATE_Z = (0.0, 1.0)
STATE_SL = (0.15, 0.30)
STATE_H = (168, 720)
STATE_F = 0.0001
HEDGE_H = (0.5, 1.0)
HEDGE_INST = ('BTC', 'BTCETH')
ZS = (2.5, 3.0, 3.5)
KS = (3, 5, 10)
GATES = ('NONE', 'G_EW14')
B1REF = {'cfg4107': 4107}             # B1 grid cfg_id; xi derived below


def fam_cfgs(fam):
    if fam == 'BRK':
        out = [dict(s=s, R=R, H=h) for s in BRK_S for R in BRK_R for h in BRK_H]
    elif fam == 'VOL':
        out = [dict(a=a, R=R, H=h) for a in VOL_A for R in VOL_R for h in VOL_H]
    elif fam == 'PART':
        out = [dict(s=s, H=h) for s in PART_S for h in PART_H]
    elif fam == 'STATE':
        out = [dict(zo=z, s=s, H=h) for z in STATE_Z for s in STATE_SL for h in STATE_H]
    else:
        raise KeyError(fam)
    return out


NFAM = {'BRK': 90, 'VOL': 48, 'PART': 8, 'STATE': 8}
for _f, _n in NFAM.items():
    assert len(fam_cfgs(_f)) == _n


def b1_xi_of_cfg(cfg_id):
    """xi of a B1 grid cfg_id (grid_b1.all_cfgs order W, E, zmin, K, SL, H, trail)."""
    W, E, z, K, sl, hh, tr = list(itertools.product((14, 7), ('E0', 'E1'), (2.5, 3.0, 3.5), (3, 5, 10), CB.SLS, CB.HS,
                                                   CB.TRAILS))[cfg_id]
    return CB.xidx(sl, hh, tr[0], tr[1])


def hedge_bases():
    """HEDGE base exits: every BRK xi + 3 B1 references (cfg 4107; B3 exit_2024 xi 170; exit_2025 xi 72)."""
    import json
    with open(B3SEL) as fh:
        b3 = json.load(fh)
    x24, x25 = int(b3['exit_2024']['xi']), int(b3['exit_2025']['xi'])
    assert (x24, x25) == (170, 72), (x24, x25)
    out = [('BRK', i) for i in range(NFAM['BRK'])]
    out += [('B1', b1_xi_of_cfg(4107)), ('B1', x24), ('B1', x25)]
    return out


def hedge_cfgs():
    return [dict(base=b, bxi=x, inst=ins, h=h) for (b, x) in hedge_bases() for ins in HEDGE_INST for h in HEDGE_H]


def all_cfgs():
    """full T1 grid: family x exit cfg x zmin x K x gate (W = 7, E = E0 fixed). cfg_id = index."""
    res = []
    for fam in ('BRK', 'VOL', 'PART', 'STATE', 'HEDGE'):
        xs = hedge_cfgs() if fam == 'HEDGE' else fam_cfgs(fam)
        for xi, x in enumerate(xs):
            for z in ZS:
                for K in KS:
                    for g in GATES:
                        d = dict(fam=fam, xi=xi, W=7, E='E0', zmin=z, K=K, gate=g)
                        d.update(x)
                        res.append(d)
    for i, d in enumerate(res):
        d['cfg_id'] = i
    return res


def n_total():
    return len(all_cfgs())
