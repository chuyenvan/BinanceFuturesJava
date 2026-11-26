"""LEVZ S2 shared constants + loaders (PREREG_LEVZ_S2 @74ec941e). B1 / B0 / tier-1 code imported READ-ONLY by file path."""
import importlib.util
import logging
import os
import sys
sys.dont_write_bytecode = True

BASE = '/home/ubuntu/claude_master/w3/levz_s2'
WORK = BASE + '/work'
OUT = BASE + '/out'
B1CODE = '/home/ubuntu/claude_master/w3/levz_b1/code'
LEVZ_CODE = '/home/ubuntu/claude_master/w3/levz/code'
SIGCOUNT = '/home/ubuntu/claude_master/w3/levz_rev/sigcount/out'
REAL_KEY = 'I_HAVE_A1_PASS'
SETS = ('REF', 'P5', 'P5b', 'P6a', 'P6b')
KS = (3, 5, 10)
YFOLDS = (('DEV', '2022-01-01', '2026-01-01'), ('Y22', '2022-01-01', '2023-01-01'), ('Y23', '2023-01-01', '2024-01-01'),
          ('Y24', '2024-01-01', '2025-01-01'), ('Y25', '2025-01-01', '2026-01-01'))
YEARS = (2022, 2023, 2024, 2025)
FOLD_OF_YEAR = {2022: 'Y22', 2023: 'Y23', 2024: 'Y24', 2025: 'Y25'}


def setup_log(name):
    root = logging.getLogger()
    if not root.handlers:
        os.makedirs(OUT, exist_ok=True)
        logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s %(message)s',
                            handlers=[logging.FileHandler('%s/%s.log' % (OUT, name)), logging.StreamHandler()])
    return logging.getLogger('levz_s2.' + name)


def imp(name, path):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def b1():
    """returns (CB, P=port, X=exits, SIM=B0 sim) imported read-only from B1 / B0."""
    CB = imp('common_b1', B1CODE + '/common_b1.py')
    sys.path.insert(0, B1CODE)
    try:
        P = CB.load('port')
        X = CB.load('exits')
    finally:
        sys.path.pop(0)
    return CB, P, X, CB.load_b0('sim')


def s2(name):
    return imp(name, os.path.join(os.path.dirname(os.path.abspath(__file__)), name + '.py'))


def require_real(argv):
    if '--real' not in argv or argv[argv.index('--real') + 1:argv.index('--real') + 2] != [REAL_KEY]:
        raise SystemExit('LOCKED: real-data run needs --real %s (after A1 code audit PASS)' % REAL_KEY)
