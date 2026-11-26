"""LEVZ B2 shared: path setup + loaders. B1 code (w3/levz_b1/code) and tier-1 common (w3/levz/code) are imported read-only."""
import os
import sys
import importlib.util
sys.dont_write_bytecode = True

BASE = '/home/ubuntu/claude_master/w3/levz_b2'
WORK = BASE + '/work'
OUT = BASE + '/out'
B1CODE = '/home/ubuntu/claude_master/w3/levz_b1/code'
L1CODE = '/home/ubuntu/claude_master/w3/levz/code'
HERE = os.path.dirname(os.path.abspath(__file__))


def b1(name):
    """import levz_b1/code/<name>.py under module name <name> (same names B1 uses internally)."""
    if name in sys.modules:
        return sys.modules[name]
    sys.path.insert(0, B1CODE)
    try:
        if name == 'common_b1':
            import common_b1 as m
            return m
        CB = b1('common_b1')
        return CB.load(name)
    finally:
        if sys.path and sys.path[0] == B1CODE:
            sys.path.pop(0)


def l1common():
    """frozen tier-1 common.py (readers with ts < 2026 asserts)."""
    if 'levz1_common' in sys.modules:
        return sys.modules['levz1_common']
    spec = importlib.util.spec_from_file_location('levz1_common', os.path.join(L1CODE, 'common.py'))
    mod = importlib.util.module_from_spec(spec)
    sys.modules['levz1_common'] = mod
    spec.loader.exec_module(mod)
    return mod


def b2(name):
    mn = 'b2_' + name
    if mn in sys.modules:
        return sys.modules[mn]
    spec = importlib.util.spec_from_file_location(mn, os.path.join(HERE, name + '.py'))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mn] = mod
    spec.loader.exec_module(mod)
    return mod
