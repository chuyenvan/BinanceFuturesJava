# DEV_G2 - FX G2 TSMOM + REER value filter (code + tests; NO real-data backtest run)

Prereg: ~/claude_master/vz_e1_wt/docs/prereg/PREREG_FX_G2.md (incl. "CHOT CUA MASTER") + PREREG_FX_ERRATA1-3.md.
Choices: CHOICES_G2.md. Hashes: SHA256SUMS.txt. Imports audited G1 code from ~/claude_master/w3/fx/g1/code (unchanged;
sha256 listed in SHA256SUMS.txt).
REER: data/derived/bis_reer_monthly.csv present (area, basket, month, reer, unit, status; narrow N 1964-01.., broad B
1994-01..); loader uses basket N, cut at the cutoff month before parsing values.

## One-line commands (from ~/claude_master/w3/fx/g2/code)
- tests:     python3 test_g2.py            (~4 min)
- loader:    python3 load_g2.py            (universe counts, REER range; no returns)
- RUN only after A1 PASS + MASTER go:  python3 eval_g2.py --real I_HAVE_A1_PASS  -> ../out/EVAL_G2.{md,json}
- optional:  python3 sim_g2.py --real I_HAVE_A1_PASS  -> ../out/daily_*, ledger_*

## Tests (out/test_run.log)
- a quote direction: fake FRED files, every ccy appreciating vs USD -> s = +1 for L1/L3/L12/C for all 9 DEX codes.
- b causality on REAL data <= 2019-12-31 (signal layer only): prices after t, rates and REER months >= month(t)
    randomised at 6 dates -> signal records (T, exec row, universe, signs, vol63, REER m-1, 60m mean, rates) and 12
    config sign matrices up to t unchanged; non-vacuous; exec row = T+1 everywhere. HANDCHECK 2008-09/10 logged.
- c hand month (synthetic, 2 ccys, L1): inverse-vol weights from hand vol, next-day execution, costs, swap, price
    jumps -> equity matches to 1e-12; sizing hand answers (4/7, -2/7, 1/7).
- d value filter hand answers both sides (X 10 / 20 %), REER m-1 used (not m), 60-month mean incl. m-1.
- e circular shift keeps months-with-position per ccy, k in [12, n-12]; iid control; p = (1+n_ge)/(N+1);
    D5 drops best months; D1-D6 boundaries.
- f cutoff > 2019-12-31 refused; rows > cutoff skipped (FRED, rates, REER); simulate/evaluate locked on loaded data;
    CLI exit 2 without --real.
- g synthetic planted trend -> DAT; pure noise -> KHONG DAT (N shift = 1000).
- h selection by TRAIN only (+ tie order); x2 passes cost_mult 2 for selected config and doubles cost per unit traded;
    shift runs use selected config from 2005-12; determinism.

## Not done: no return / statistic on real data. Open: A1 code audit; real 2008-10 PnL hand check (A1-results).
