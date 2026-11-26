"""Verify the UTC+7 claim for printDone start times: compare leg entry price with the 1m close at candidate offsets
(UTC = start - 7 h, and alternatives). Output out/c_tzcheck.json."""
import sys
import os
import json
import logging
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import an_common as A
import numpy as np
import pandas as pd

log = logging.getLogger('levz_an.tz')


def main():
    A.setup_log('c_tzcheck')
    CB, P, X = A.b1()
    C1 = np.load(CB.WORK + '/close1m.npy', mmap_mode='r')
    lg = pd.read_parquet(A.OUT + '/c_long_legs.parquet')
    lg = lg[(lg['run'] == 'c0s42') & (lg['c'] >= 0) & (lg['ts'] >= A.DEV0 + 86400000)].sample(400, random_state=1)
    res = {}
    for off_h in (-7, -6, 0, 7):          # extra shift relative to the -7 h already applied
        errs = []
        for r in lg.itertuples(index=False):
            t = r.ts + off_h * A.H
            j = (t - A.H0) // A.M
            if j < 1 or j + 1 >= C1.shape[1]:
                continue
            px = np.asarray(C1[r.c, j - 1:j + 2], dtype=np.float64)
            errs.append(float(np.min(np.abs(px / r.entry - 1))))
        e = np.array(errs)
        res[str(off_h)] = dict(n=len(e), med_abs_err=float(np.median(e)), frac_lt_0p2pct=float((e < 0.002).mean()))
    log.info('tz %s', res)
    with open(A.OUT + '/c_tzcheck.json', 'w') as fh:
        json.dump(res, fh, indent=1)


if __name__ == '__main__':
    main()
