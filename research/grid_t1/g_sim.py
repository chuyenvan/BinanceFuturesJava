#!/usr/bin/env python3
"""ctypes wrapper for grid_engine.c + simulation helpers."""
import ctypes
import os
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
LIB = ctypes.CDLL(os.path.join(HERE, "libgridsim.so"))


class SimArgs(ctypes.Structure):
    _fields_ = [
        ("o", ctypes.POINTER(ctypes.c_float)),
        ("h", ctypes.POINTER(ctypes.c_float)),
        ("l", ctypes.POINTER(ctypes.c_float)),
        ("c", ctypes.POINTER(ctypes.c_float)),
        ("ro", ctypes.POINTER(ctypes.c_float)),
        ("rh", ctypes.POINTER(ctypes.c_float)),
        ("rl", ctypes.POINTER(ctypes.c_float)),
        ("rc", ctypes.POINTER(ctypes.c_float)),
        ("n", ctypes.c_int),
        ("ts0", ctypes.c_int64),
        ("i_hist", ctypes.c_int),
        ("i_start", ctypes.c_int),
        ("i_end", ctypes.c_int),
        ("mode", ctypes.c_int),
        ("variant", ctypes.c_int),
        ("boot", ctypes.c_int),
        ("fee", ctypes.c_double),
        ("fee_taker", ctypes.c_double),
        ("M", ctypes.c_double),
        ("fts", ctypes.POINTER(ctypes.c_int64)),
        ("frat", ctypes.POINTER(ctypes.c_double)),
        ("nf", ctypes.c_int),
        ("day_ts", ctypes.POINTER(ctypes.c_int64)),
        ("day_eq", ctypes.POINTER(ctypes.c_double)),
        ("maxday", ctypes.c_int),
        ("stats", ctypes.POINTER(ctypes.c_double)),
        ("seed", ctypes.c_uint64),
    ]


LIB.grid_sim_args.argtypes = [ctypes.POINTER(SimArgs)]
LIB.grid_sim_args.restype = ctypes.c_int

FP = ctypes.POINTER(ctypes.c_float)


def _fp(a, keep):
    if a is None:
        return ctypes.cast(None, FP)
    a = np.ascontiguousarray(a, dtype=np.float32)
    keep.append(a)
    return a.ctypes.data_as(FP)


def _ip(a, keep):
    a = np.ascontiguousarray(a, dtype=np.int64)
    keep.append(a)
    return a.ctypes.data_as(ctypes.POINTER(ctypes.c_int64))


def _dp(a, keep):
    a = np.ascontiguousarray(a, dtype=np.float64)
    keep.append(a)
    return a.ctypes.data_as(ctypes.POINTER(ctypes.c_double))


def ratios(o, h, l, c):
    cp = np.ascontiguousarray(c, dtype=np.float32)
    prev = np.empty_like(cp); prev[1:] = cp[:-1]; prev[0] = cp[0]
    return tuple(np.ascontiguousarray(x) for x in
                 ((o / prev).astype(np.float32), (h / prev).astype(np.float32),
                  (l / prev).astype(np.float32), (c / prev).astype(np.float32)))


def run(o, h, l, c, ts0, i_hist, i_start, i_end, mode, variant=0, boot=False,
        fee=2e-4, fee_taker=5e-4, M=1.0, fts=None, frat=None, seed=0, ratios_pre=None):
    n = len(c)
    maxday = (i_end - i_start) // 1440 + 3
    day_ts = np.zeros(maxday, np.int64)
    day_eq = np.zeros(maxday, np.float64)
    stats = np.zeros(20, np.float64)
    if fts is None:
        fts = np.zeros(0, np.int64); frat = np.zeros(0, np.float64)
    if boot:
        ro, rh, rl, rc = ratios_pre if ratios_pre is not None else ratios(o, h, l, c)
    else:
        ro = rh = rl = rc = None
    keep = []
    a = SimArgs(_fp(o, keep), _fp(h, keep), _fp(l, keep), _fp(c, keep),
                _fp(ro, keep), _fp(rh, keep), _fp(rl, keep), _fp(rc, keep),
                n, int(ts0), int(i_hist), int(i_start), int(i_end),
                int(mode), int(variant), int(bool(boot)),
                float(fee), float(fee_taker), float(M),
                _ip(np.asarray(fts, np.int64), keep), _dp(np.asarray(frat, np.float64), keep), len(fts),
                _ip(day_ts, keep), _dp(day_eq, keep), maxday, _dp(stats, keep),
                ctypes.c_uint64(seed))
    nd = LIB.grid_sim_args(ctypes.byref(a))
    if nd < 0:
        raise RuntimeError("grid_sim failed")
    return day_ts[:nd], day_eq[:nd], stats
