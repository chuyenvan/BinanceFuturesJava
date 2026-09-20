"""CAGR_CI_T170 (TASK B t2 - CAGR floor) - CI block-72h (~3 ngay) cho CAGR cua T170, dung
lam san so sanh CAGR cac bien the P0/P3 (khong duoc thap hon can duoi CI nay).

TAI DUNG: C.equity() (c3_rates.py), C.inflate(k) (chuan hoa CI_INFLATE_STANDARDIZATION).
Phuong phap: block bootstrap tren log-return NGAY (block=3 ngay ~ 72h, khop tinh than block-72h
dung xuyen suot repo), 2000 rep, seed C.SEED, doi mau CO HOAN LAI cac khoi de tai tao 1 duong
tuong duong tong thoi gian, tinh CAGR annualize theo DO DAI duong resample (365.25/len(path)),
lay percentile 2.5/97.5 roi nhan he so inflate(k).

Chay: cd .../research/analysis && python3 cagr_ci_t170.py --k 2 TAG [TAG2 ...]
"""
import sys

import numpy as np

sys.path.insert(0, "/home/ubuntu/src/BinanceFuturesJava/research/analysis")
import c3_rates as C

BLOCK_DAYS = 3   # ~72h tren luoi ngay


def cagr_ci(tag, k, nrep=2000, seed=C.SEED):
    s = C.equity(tag)
    logret = np.log(s.values[1:] / s.values[:-1])
    n = len(logret)
    nblk = int(np.ceil(n / BLOCK_DAYS))
    blocks = [logret[i * BLOCK_DAYS:(i + 1) * BLOCK_DAYS] for i in range(nblk)]
    years = (s.index[-1] - s.index[0]).days / 365.25
    obs_cagr = ((s.iloc[-1] / s.iloc[0]) ** (1 / years) - 1) * 100
    rng = np.random.default_rng(seed)
    draws = np.empty(nrep)
    for i in range(nrep):
        pick = rng.integers(0, nblk, size=nblk)
        path = np.concatenate([blocks[p] for p in pick])
        total_log = path.sum()
        draws[i] = (np.exp(total_log * 365.25 / len(path)) - 1) * 100 if len(path) else np.nan
    draws = draws[np.isfinite(draws)]
    lo, hi = np.percentile(draws, [2.5, 97.5])
    c = (lo + hi) / 2.0
    infl = C.inflate(k)
    lo_i, hi_i = c - (c - lo) * infl, c + (hi - c) * infl
    return dict(tag=tag, cagr_obs=float(obs_cagr), ci95_lo=float(lo), ci95_hi=float(hi),
                ci95_lo_inflated=float(lo_i), ci95_hi_inflated=float(hi_i), k=k, infl=infl,
                years=float(years), n_daily_ret=int(n))


def main():
    argv = list(sys.argv[1:])
    i = argv.index("--k")
    k = int(argv[i + 1])
    del argv[i:i + 2]
    for tag in argv:
        r = cagr_ci(tag, k)
        print("%-40s CAGR=%.3f%%  CI95=[%.3f,%.3f]  CI95_inflated(k=%d)=[%.3f,%.3f]" %
              (r["tag"], r["cagr_obs"], r["ci95_lo"], r["ci95_hi"], r["k"],
               r["ci95_lo_inflated"], r["ci95_hi_inflated"]))


if __name__ == "__main__":
    main()
