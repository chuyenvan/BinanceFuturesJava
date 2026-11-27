"""LEVZ B4 shared constants, grid, loaders (PREREG_X3_1127 PHAN A). B1 / T1 / T2 code imported READ-ONLY by file path (never modified).
DCA kinds (A2): NONE (n_add 0) + n_add in {1, 2} x a in {5 %, 10 %}. Exits (A3): SL s in {15 %, 30 %} from AVERAGE COST; trailing
(arm 5 / gap 3; arm 10 / gap 5) from average cost, or STATE (z_out 0, T1 definition); max hold H in {72, 168} h from the first leg.
Grid (A4): 5 DCA x 2 SL x 3 exit x 2 H = 60 exit cfgs (xi) x 3 zmin x 3 K = 540 cfgs. Pool W7_E0 of cand_b1 (A1)."""
import importlib.util
import itertools
import logging
import os
import sys
sys.dont_write_bytecode = True
import numpy as np

BASE = '/home/ubuntu/claude_master/w3/levz_b4'
WORK = BASE + '/work'
OUT = BASE + '/out'
T1CODE = '/home/ubuntu/claude_master/w3/levz_t1/code'
T1WORK = '/home/ubuntu/claude_master/w3/levz_t1/work'
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
    """levz_b4/code/<name>.py by file path (module name b4_<name>)."""
    return _imp('b4_' + name, os.path.join(os.path.dirname(os.path.abspath(__file__)), name + '.py'))


def setup_log(name):
    root = logging.getLogger()
    if not root.handlers:
        logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s %(message)s')
    return logging.getLogger('levz_b4.' + name)


def require_real(argv):
    if '--real' not in argv or argv[argv.index('--real') + 1:argv.index('--real') + 2] != [REAL_KEY]:
        raise SystemExit('LOCKED: real-data run needs --real %s (after A1 code audit PASS)' % REAL_KEY)


FEE = 0.0007
SL_SLIP = CB.SL_SLIP          # 0.003
TR_SLIP = CB.TR_SLIP          # 0.001 (B1 trailing exit)
H0, NH, HMAX, NPATH = CB.H0, CB.NH, CB.HMAX, CB.NPATH
BIG = 1 << 30
LIM_TOL = 1e-12               # limit fill: close >= level (1 - 1e-12) (MASTER 2026-11-27; level is a float product)
# reason codes = T1 codes (rt) -> port codes via C1.RT2RS
RT_SL, RT_TRAIL, RT_TIME, RT_MISS, RT_EOD, RT_STATE = C1.RT_SL, C1.RT_TRAIL, C1.RT_TIME, C1.RT_MISS, C1.RT_EOD, C1.RT_STATE
RTNAMES = C1.RTNAMES

DCAS = (('NONE', 0, 0.0), ('D1_5', 1, 0.05), ('D1_10', 1, 0.10), ('D2_5', 2, 0.05), ('D2_10', 2, 0.10))
DNAMES = tuple(d[0] for d in DCAS)
SLS = (0.15, 0.30)
EXITS = (('TR5_3', 0.05, 0.03), ('TR10_5', 0.10, 0.05), ('STATE', 0.0, 0.0))
ENAMES = tuple(e[0] for e in EXITS)
STATE_ZO = 0.0
HS = (72, 168)
ZS = (2.5, 3.0, 3.5)
KS = (3, 5, 10)


def exit_list():
    """60 exit cfgs in fixed order (xi): DCA x SL x exit x H."""
    out = []
    for (dn, n, a), s, (en, arm, gap), hh in itertools.product(DCAS, SLS, EXITS, HS):
        out.append(dict(dca=dn, n_add=n, a=a, s=s, ex=en, arm=arm, gap=gap, H=hh))
    assert len(out) == 60
    return out


XLIST = exit_list()
NX = len(XLIST)


def all_cfgs():
    """540 cfgs: exit cfg x zmin x K; cfg_id = index."""
    res = []
    for i, (xi, z, K) in enumerate(itertools.product(range(NX), ZS, KS)):
        d = dict(cfg_id=i, xi=xi, W=7, E='E0', zmin=z, K=K)
        d.update(XLIST[xi])
        res.append(d)
    assert len(res) == 540
    return res


N_TOTAL = 540
N_PER_DCA = N_TOTAL // len(DCAS)    # 108


def cand_classes(cz=None):
    """W7_E0 classes of cand_b1: {zmin: (k, c, s, cid_b1)}; union ucid (sorted unique B1 cid) and its (k, c)."""
    if cz is None:
        cz = np.load(CB.WORK + '/cand_b1.npz')
    cls = {z: tuple(np.asarray(cz['W7_E0_%.1f_%s' % (z, s)]) for s in ('k', 'c', 's', 'cid')) for z in ZS}
    ucid = np.unique(np.concatenate([cls[z][3] for z in ZS]))
    uk, uc = np.asarray(cz['U_k'])[ucid], np.asarray(cz['U_c'])[ucid]
    return cls, ucid, uk, uc


def year_of_k(k):
    import pandas as pd
    return pd.to_datetime(H0 + np.asarray(k, dtype=np.int64) * CB.H, unit='ms').year.values
