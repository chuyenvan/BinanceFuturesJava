#!/usr/bin/env python3
"""HO4-P0b Q1: phan du Tool1 co phai do LUONG TU HOA THEO CHUNK cua T1C2 (Tool1ColSink: int16 theo min/max cua chinh
chunk 200k dong) khong? (a) theo ngay: t1 vs DEV (cung diem bat dau 10-01, chunk 1-3 trung nhau, chunk cuoi khac do
t1 dung o 10-16); (b) dung sai = 1 buoc luong tu (range cot/65535, range tren cua so) thay cho 1e-6.
Chi ty le, cua so 2025. Usage: ho4b_t1q.py <t1x_out_dir> <out.json>"""
import glob, json, logging, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
ARGV = sys.argv[:]
sys.argv = ["x", "-", "-", "-"]
import ho4b_detcmp as D  # noqa: E402
sys.argv = ARGV
log = logging.getLogger("ho4b_t1q")


def cmp(A, B, tag, res):
    (ka, fa), (kb, fb) = A, B
    com, ia, ib = np.intersect1d(ka, kb, return_indices=True)
    xa, xb = fa[ia].astype(np.float64), fb[ib].astype(np.float64)
    strict = np.zeros_like(xa, dtype=bool); loose = np.zeros_like(xa, dtype=bool)
    for j in range(xa.shape[1]):
        strict[:, j] = D.okc(xa[:, j], xb[:, j])
        fin = np.isfinite(xb[:, j])
        rng = float(np.nanmax(xb[fin, j]) - np.nanmin(xb[fin, j])) if fin.any() else 0.0
        step = rng / 65535.0
        loose[:, j] = (np.abs(xa[:, j] - xb[:, j]) <= 1.01 * step + 1e-6 * np.maximum(1.0, np.abs(xb[:, j]))) | (np.isnan(xa[:, j]) & np.isnan(xb[:, j]))
    day = (com // 10000 - D.TLO) // 86400000
    r = {"n": int(len(com)), "strict": round(float(strict.mean()), 5), "loose_1step": round(float(loose.mean()), 5),
         "strict_by_day": {int(d): round(float(strict[day == d].mean()), 4) for d in np.unique(day)},
         "loose_cols_bad": {int(j): round(float(loose[:, j].mean()), 4) for j in range(xa.shape[1]) if loose[:, j].mean() < 0.999}}
    res[tag] = r
    log.info("%s %s", tag, r)


def main():
    od, out = sys.argv[1], sys.argv[2]
    t1 = D.load_t1(glob.glob(os.path.join(od, "t1", "*.t1c.gz"))[0])
    t1e = D.load_t1(glob.glob(os.path.join(od, "t1e", "*.t1c.gz"))[0])
    dev = D.load_t1(os.path.join(D.G.T1_DIR, "features_20251001_to_20260101*"))
    res = {}
    cmp(t1, dev, "t1_vs_dev", res)
    cmp(t1e, dev, "t1e_vs_dev", res)
    cmp(t1, t1e, "t1_vs_t1e", res)
    with open(out, "w") as f:
        json.dump(res, f, indent=1)


if __name__ == "__main__":
    main()
