#!/usr/bin/env python3
"""TSX (PREREG_PARITY_V11_WINDOW §4 dong TSX): dung bin Vision daily cho 1 khoang ngay + universe live,
chay code live AltEwIndex/TsMktExt (tsxoff.TsxLiveOffline) => S_j + flag, so voi [TS-EXT] tren 242.
argv: day_from day_to   (vd 2026-10-20 2026-10-21)
"""
import io
import json
import os
import sys
import zipfile

import numpy as np
import pandas as pd

W = os.path.expanduser("~/claude_master/parity_v11w")
TSX = os.path.expanduser("~/claude_master/v11_tsx/off")
uni = [x.strip() for x in open(W + "/univ/u_d21.txt") if x.strip()]
days = list(pd.date_range(sys.argv[1], sys.argv[2], freq="D"))
rows = []
miss = {}
for d in days:
    ds = d.strftime("%Y-%m-%d")
    n = 0
    for s in uni:
        p = "%s/vision/klines_1m/%s/%s.zip" % (W, ds, s)
        if not os.path.exists(p):
            miss[ds] = miss.get(ds, 0) + 1
            continue
        with zipfile.ZipFile(p) as z:
            raw = z.read(z.namelist()[0]).decode()
        lines = [ln for ln in raw.splitlines() if ln and ln[0].isdigit()]
        a = np.array([ln.split(",") for ln in lines])
        rows.append(pd.DataFrame({"ts": a[:, 0].astype(np.int64), "sym": s,
                                  "close": a[:, 4].astype(np.float64),
                                  "quote_volume": a[:, 7].astype(np.float64)}))
        n += 1
    print(ds, "syms", n)
t = pd.concat(rows, ignore_index=True).drop_duplicates(["sym", "ts"], keep="last").sort_values(["sym", "ts"])
syms = sorted(t.sym.unique())
idx = {s: i for i, s in enumerate(syms)}
out = W + "/work/tsx_%s_%s.bin" % (sys.argv[1], sys.argv[2])
o = np.lexsort((t.sym.map(idx).to_numpy(np.int32), t.ts.to_numpy(np.int64)))
with open(out, "wb") as f:
    np.array([len(t)], dtype="<i8").tofile(f)
    t.ts.to_numpy(np.int64)[o].astype("<i8").tofile(f)
    t.sym.map(idx).to_numpy(np.int32)[o].astype("<i4").tofile(f)
    t.close.to_numpy(np.float64)[o].astype("<f8").tofile(f)
    t.quote_volume.to_numpy(np.float64)[o].astype("<f8").tofile(f)
open(W + "/work/tsx_syms.txt", "w").write("\n".join(syms) + "\n")
print("bin", out, "rows", len(t), "syms", len(syms), "missing", miss,
      "ts", pd.to_datetime(t.ts.min(), unit="ms"), pd.to_datetime(t.ts.max(), unit="ms"))
