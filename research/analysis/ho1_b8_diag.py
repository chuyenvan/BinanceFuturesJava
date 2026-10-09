#!/usr/bin/env python3
"""HO1 B8 chan doan (seal DONG, chi cua so DEV): C1 vs de-p1 tung o lech (float32 cung bit?), CAL vs C1 (truoc Q4 trung? Q4 lech theo thang)."""
import csv, json, logging
import numpy as np
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
O = "/home/ubuntu/kaggle_sim/out/%s/storage/printDone.csv"
R = "/home/ubuntu/src/BinanceFuturesJava"


def rows(t):
    r = list(csv.reader(open(O % t)))
    return r[0], r[1:]


h, a = rows("ho1-c1")
h0, b = rows("de-p1")
assert h == h0 and len(a) == len(b)
cells = []
for i, (x, y) in enumerate(zip(a, b)):
    for j in range(len(h)):
        if x[j] != y[j]:
            cells.append(dict(row=i, sym=x[0], start=x[6], col=h[j], c1=x[j], dev=y[j],
                              f32_equal=bool(np.float32(x[j]) == np.float32(y[j]))))
c1 = dict(n=len(a), cells_diff=len(cells), cols=sorted({c["col"] for c in cells}),
          all_f32_equal=all(c["f32_equal"] for c in cells), cells=cells)
_, c = rows("ho1-cal")
si, li = h.index("start"), h.index("level")
pre = lambda rr: sorted(tuple(x) for x in rr if x[si].strip() < "20251001 00:00")
k = lambda x: (x[0], x[si].strip(), x[li])
qa = {k(x) for x in a if x[si].strip() >= "20251001 00:00"}
qc = {k(x) for x in c if x[si].strip() >= "20251001 00:00"}
mon = {}
for s, idx in ((qa - qc, 0), (qc - qa, 1)):
    for x in s:
        mon.setdefault(x[1][:6], [0, 0])[idx] += 1
cal = dict(preQ4_identical=pre(a) == pre(c), n_preQ4=len(pre(a)), n_c1=len(a), n_cal=len(c), q4_c1=len(qa), q4_cal=len(qc),
           only_c1=len(qa - qc), only_cal=len(qc - qa), symdiff=len(qa ^ qc), frac_q4=len(qa ^ qc) / len(qa),
           frac_all_dev=len(qa ^ qc) / len(a), by_month_only_c1_only_cal=mon, stop=len(qa ^ qc) / len(a) > 0.01)
out = dict(c1=c1, cal=cal)
json.dump(out, open(R + "/docs/result/ho1/b8_diag.json", "w"), indent=1)
logging.info("C1 %s", json.dumps({k_: v for k_, v in c1.items() if k_ != "cells"}))
logging.info("CAL %s", json.dumps(cal))
