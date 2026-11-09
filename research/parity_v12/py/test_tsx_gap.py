#!/usr/bin/env python3
"""[ADD16] test TSX lap 10-28: (1) vis_path: 10-28 -> REST, ngay khac -> Vision; (2) dung lai S_2026-10-27 trong scratch
trung bit cache that (ngay khong lien quan khong doi); (3) S_2026-10-28 dung duoc, du 1440 phut; S_2026-10-29 du 1440 phut.
Chi ghi vao thu muc scratch (argv[1])."""
import os
import shutil
import sys
os.environ.setdefault("PV_DAY", "2026-11-07")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import day_tsx as M  # noqa: E402
import pandas as pd  # noqa: E402

S = sys.argv[1]
REAL = M.TSXD
ok = []
ok.append(M.vis_path("2026-10-28", "BTCUSDT").endswith("k1028/zips/BTCUSDT-1m-2026-10-28.zip"))
ok.append(M.vis_path("2026-10-27", "BTCUSDT") == "%s/2026-10-27/BTCUSDT.zip" % M.C["VIS"])
shutil.rmtree(S, ignore_errors=True)
os.makedirs(S)
M.TSXD = S
uni = M.uni_all()
a = M.s_day("2026-10-27", uni)
b = pd.read_csv(REAL + "/S_2026-10-27.csv")
ok.append(a.equals(b))
c = M.s_day("2026-10-28", uni)
ok.append(c is not None and int(c.n_min.iloc[0]) == 1440)
d = M.s_day("2026-10-29", uni)
ok.append(d is not None and int(d.n_min.iloc[0]) == 1440)
print("S_10-28", None if c is None else c.to_dict("records"))
print("S_10-29", None if d is None else d.to_dict("records"))
print("cases", ok)
print("TEST_TSX_GAP", "PASS" if all(ok) else "FAIL")
