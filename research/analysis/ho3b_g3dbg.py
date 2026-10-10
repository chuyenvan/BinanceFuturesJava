import sys, numpy as np, pandas as pd
sys.path.insert(0, "/home/ubuntu/claude_master/1003/ho3b")
import ho3b_gate3 as G3
H = 3600000
lo = int(pd.Timestamp("2025-12-01").value // 10**6); hi = lo + 2 * 86400000
G3.MODE = "pinned"; a = G3.read_oi_comb(lo, hi)
G3.MODE = "rebuilt"; b = G3.read_oi_comb(lo, hi)
print("pinned rows", len(a), "rebuilt-mode rows", len(b))
ka = a["ts"].astype(np.int64) * 10000 + a["sym"]; kb = b["ts"].astype(np.int64) * 10000 + b["sym"]
print("keys equal", np.array_equal(np.sort(ka), np.sort(kb)))
oa, ob = np.argsort(ka), np.argsort(kb)
print("vals equal", np.array_equal(a["oi"][oa].view(np.uint32), b["oi"][ob].view(np.uint32)))
print("dtype", a.dtype, b.dtype)
