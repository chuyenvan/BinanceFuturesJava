import sys, glob
import numpy as np, pandas as pd
sys.path.insert(0, "/home/ubuntu/claude_master/1003/ho3b")
import ho3b_slice_cmp as S
kr, fr = S.t1(S.os.path.join(S.G.T1_DIR, "features_20260101_to_20260401*"), S.T0, S.T1)
iqr = np.nanpercentile(fr, 75, axis=0) - np.nanpercentile(fr, 25, axis=0)
kn, fn = S.t1(glob.glob(S.OUTK + "/out/t1u/*.t1c*")[0], S.T0, S.T1)
com, ir, inn = np.intersect1d(kr, kn, return_indices=True)
bad = np.zeros(len(com), bool)
for j in range(fr.shape[1]):
    a, b = fn[inn, j], fr[ir, j]
    t = 1e-2 * iqr[j] if iqr[j] > 0 else 1e-6 * np.maximum(1, np.abs(b))
    bad |= ~((np.abs(a - b) <= t) | (np.isnan(a) & np.isnan(b)))
day = pd.to_datetime(com // 10000, unit="ms", utc=True).tz_convert("Asia/Ho_Chi_Minh").strftime("%m-%d")
print("row-bad by day", pd.Series(bad).groupby(np.asarray(day)).mean().round(4).to_dict())
late = np.asarray(com // 10000) >= S.T0 + 2 * 86400000
cells_ok = []
for j in range(fr.shape[1]):
    a, b = fn[inn, j][late], fr[ir, j][late]
    t = 1e-2 * iqr[j] if iqr[j] > 0 else 1e-6 * np.maximum(1, np.abs(b))
    cells_ok.append(((np.abs(a - b) <= t) | (np.isnan(a) & np.isnan(b))).mean())
print("cell ok frac tu 03-03 07:00:", round(float(np.mean(cells_ok)), 6), "worst", sorted(enumerate(np.round(cells_ok, 5)), key=lambda x: x[1])[:4])
