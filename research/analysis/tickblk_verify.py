"""tickblk_verify.py — TU-KIEM DOC LAP (thuan Python) cho `TickWeakBlock` (docs/PREREG_TICK_BLOCK.md).

Doc truc tiep `market.bin` (nguon sim da doc), tai lap cong thuc trong code Java:
  mo hinh quantile CUON 30 ngay TRUOC, tinh lai moi ngay UTC, vi tri `floor(q*(n-1))` tren mang da sort;
  `DEPTH/DROP15M` chan khi `x >= q0.75`, `BREADTH` chan khi `x <= q0.25` (chi tinh khi n >= MIN_SAMPLES).

Hai che do khoi tao buffer:
  `zero` = `new float[]` cua Java (0.0f — BAN CHAY 1, CO LOI: warm-up bi vo hieu)
  `nan`  = thiet ke pre-reg (`PREREG_TICK_BLOCK` §1.2 — chua du mau thi KHONG chan)

So voi file phut bi chan that do sim ghi (`<out>/storage/tickblk_blocked_min.csv`) => do "lech vong lap"
+ do dung luong cua loi warm-up (`|A \\ B|`).

Usage:
  python3 research/analysis/tickblk_verify.py DEPTH     tickblk-depth      [zero|nan]
  python3 research/analysis/tickblk_verify.py DROP15M   tickblk-drop15     [zero|nan]
  python3 research/analysis/tickblk_verify.py DEPTH     --ab               # so zero-init vs NaN-init
"""
import sys

import numpy as np
import pandas as pd

MB = "/home/ubuntu/wfo_ds_x1_2021/market.bin"
OUT = "/home/ubuntu/kaggle_sim/out"
WIN, PCT, MIN_SAMPLES, MPD, DAY = 30, 25, 20160, 1440, 86400000
# big-endian: Java DataOutputStream (xem WfoDataset.readMarket)
DT = np.dtype([("ts", ">i8"), ("down", ">f4"), ("up", ">f4"), ("down15", ">f4")])

# Cua so sim cua T170/X1 (local GMT+7). Ket thuc = 2025-12-31 (ngay cuoi CUNG duoc xu ly la 2025-12-30).
START = "2021-07-01"
END = "2025-12-31"


def load():
    with open(MB, "rb") as f:
        n = int(np.frombuffer(f.read(4), dtype=">i4")[0])
        a = np.frombuffer(f.read(n * 20), dtype=DT)
    ts = a["ts"].astype(np.int64)
    lab = pd.to_datetime(ts, unit="ms", utc=True).tz_convert("Asia/Saigon").strftime("%Y%m%d %H:%M")
    return ts, a, lab


def replica(ts, x, mode, zero_init, lab):
    """Tra ve (tap phut bi chan, so phut xu ly, nguong cuoi)."""
    buf = np.zeros((WIN + 1) * MPD) if zero_init else np.full((WIN + 1) * MPD, np.nan)
    day = np.floor_divide(ts, DAY)
    lo = int(pd.Timestamp(START, tz="Asia/Saigon").timestamp() * 1000)
    hi = int(pd.Timestamp(END, tz="Asia/Saigon").timestamp() * 1000)
    keep = np.nonzero((ts >= lo) & (ts < hi))[0]
    cur, thr, nmin = None, np.nan, 0
    out = set()
    for i in keep:
        d = int(day[i])
        if cur is None or d != cur:
            cur = d
            cb = d % (WIN + 1)
            vals = np.concatenate([buf[b * MPD:(b + 1) * MPD] for b in range(WIN + 1) if b != cb])
            vals = vals[~np.isnan(vals)]
            if len(vals) >= MIN_SAMPLES:
                vals.sort()
                q = (PCT / 100.0) if mode == "BREADTH" else (1 - PCT / 100.0)
                thr = vals[int(np.floor(q * (len(vals) - 1)))]
            else:
                thr = np.nan
        buf[(d % (WIN + 1)) * MPD + ((int(ts[i]) // 60000) % MPD)] = x[i]
        nmin += 1
        if not np.isnan(thr) and (x[i] <= thr if mode == "BREADTH" else x[i] >= thr):
            out.add(lab[i])
    return out, nmin, thr


def main():
    mode = sys.argv[1].upper()
    ts, a, lab = load()
    x = a["down"].astype(np.float64) if mode == "DEPTH" else a["down15"].astype(np.float64)

    if sys.argv[2] == "--ab":
        A, nA, tA = replica(ts, x, mode, True, lab)
        B, nB, tB = replica(ts, x, mode, False, lab)
        print("%s: 0-init chan %d (thrLast=%.6f) | NaN-init chan %d (thrLast=%.6f)"
              % (mode, len(A), tA, len(B), tB))
        d = sorted(A ^ B)
        print("|A xor B| = %d  (A\\B=%d, B\\A=%d)" % (len(d), len(A - B), len(B - A)))
        if d:
            print("   tu %s den %s" % (d[0], d[-1]))
            print(pd.Series([m[:6] for m in d]).value_counts().sort_index().to_string())
        return

    tag, zero = sys.argv[2], (len(sys.argv) < 4 or sys.argv[3] != "nan")
    P, nmin, thr = replica(ts, x, mode, zero, lab)
    J = set(pd.read_csv("%s/%s/storage/tickblk_blocked_min.csv" % (OUT, tag))["minute"].astype(str))
    print("%s tag=%s init=%s: replica=%d phut (thrLast=%.6f, xu ly %d) | java=%d"
          % (mode, tag, "zero" if zero else "nan", len(P), thr, nmin, len(J)))
    print("  giao=%d | chi replica=%d | chi java=%d  (lech bien cua so + ngay 2021-06-30)"
          % (len(P & J), len(P - J), len(J - P)))


if __name__ == "__main__":
    main()
