#!/usr/bin/env python3
"""GS wave-1 — sinh 256 vector tham so bang Sobol theo PRE-REG (PREREG_GS.md, 2026-09-03).

KHONG duoc doi range / N / thang o day: chung la phan da TIEN-DANG-KY.
Chay:  python3 gen_params.py [OUT=params.jsonl]

Ket qua: 257 dong jsonl.
  - dong dau  id=-1  = DIEM NEO C2b (kiem ha tang: phai tai lap equity 60390)
  - 256 dong sau id=0..255 = mau Sobol (scramble=True, seed=42, random_base2(m=8))

Thu tu chieu = DUNG thu tu bang trong PREREG_GS.md (chieu 0..14). Doi thu tu = doi mau.
"""
import json
import math
import sys

from scipy.stats import qmc

# (ten key, C2b, lo, hi, thang)  — thang: "log" | "lin" | "int" | "logint"
SPEC = [
    ("SIM_MIN_MOMENTUM_15M",        0.008,   0.002, 0.030, "log"),
    ("SIM_AI_DYNAMIC_MULTIPLIER",   1.28760, 0.5,   3.0,   "lin"),
    ("SIM_AI_DYNAMIC_MIN",          0.26787, 0.05,  1.0,   "log"),
    ("SIM_AI_DYNAMIC_MAX",          2.14135, 1.0,   5.0,   "lin"),
    ("SIM_PREDICT_SYMBOL_RATE_MAX", 0.15,    0.05,  0.50,  "log"),
    ("SIM_RATE_PROFIT_STOP_MARKET", 0.07,    0.02,  0.20,  "log"),
    ("TS_GIVEBACK_RATIO",           0.5,     0.2,   0.9,   "lin"),
    ("SIM_TS_MAX_GAP",              0.08,    0.02,  0.20,  "log"),
    ("SIM_TS_MAX_GAP_WEAK",         0.03,    0.01,  0.15,  "log"),
    ("SIM_TS_PNOPUMP_WEAK_THR",     0.29,    0.05,  0.60,  "lin"),
    ("SIM_LOSER_TIME_STOP_HOURS",   168,     24,    720,   "logint"),
    ("SELECTOR_RANK_TOPK",          8,       2,     30,    "int"),
    ("DCA_GRID_SCALE",              1.5,     0.5,   3.0,   "lin"),
    ("SIM_F_BASE",                  0.03,    0.01,  0.08,  "log"),
    ("SIM_U_MAX",                   0.6,     0.3,   0.95,  "lin"),
]

N = 256          # PRE-REG: wave 1 = 256 diem
SEED = 42        # PRE-REG
M = 8            # 2**8 = 256 (random_base2 giu tinh chat balance cua Sobol)


def map_dim(u, lo, hi, scale):
    if scale == "lin":
        return round(lo + u * (hi - lo), 6)
    if scale == "log":
        return round(math.exp(math.log(lo) + u * (math.log(hi) - math.log(lo))), 6)
    if scale == "logint":
        return int(round(math.exp(math.log(lo) + u * (math.log(hi) - math.log(lo)))))
    if scale == "int":
        return int(round(lo + u * (hi - lo)))
    raise ValueError(scale)


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "params.jsonl"
    if len(SPEC) != 15:
        raise SystemExit("PRE-REG yeu cau dung 15 chieu, dang co %d" % len(SPEC))

    sob = qmc.Sobol(d=len(SPEC), scramble=True, seed=SEED)
    pts = sob.random_base2(m=M)
    assert pts.shape == (N, len(SPEC)), pts.shape

    with open(out, "w") as f:
        anchor = {"id": -1}
        for name, c2b, _lo, _hi, _s in SPEC:
            anchor[name] = c2b
        f.write(json.dumps(anchor) + "\n")
        for i in range(N):
            rec = {"id": i}
            for j, (name, _c, lo, hi, sc) in enumerate(SPEC):
                rec[name] = map_dim(float(pts[i][j]), lo, hi, sc)
            f.write(json.dumps(rec) + "\n")
    print("WROTE %s : 1 anchor (id=-1) + %d Sobol (id=0..%d), d=%d seed=%d"
          % (out, N, N - 1, len(SPEC), SEED))


if __name__ == "__main__":
    main()
