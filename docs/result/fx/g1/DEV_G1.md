# DEV_G1 - FX G1 carry G10 + rolling vol gate (code + tests; NO real-data backtest run)

Prereg: ~/claude_master/vz_e1_wt/docs/prereg/PREREG_FX_G1.md + PREREG_FX_ERRATA1.md (H1, H2, H6) + PREREG_FX_ERRATA2.md
(J1 cost max(3 pip, 3 bp); J2 FX_VOL all ccys with price; J3 D6; J4 VIX lag; J6 real 2008-10 PnL check by A1-results)
+ PREREG_FX_ERRATA3.md (K1 p=(1+n_ge)/(N+1); K5 descriptive holding-month carry; K6 tests; NHO-7 lock in functions). Choices: CHOICES_G1.md.
Hashes: SHA256SUMS.txt (sha256sum -c SHA256SUMS.txt from this dir).

## Files (code/)
- load_g1.py  loader, quote conversion, cutoff guard (default 2019-12-31; later refused unless --holdout I_HAVE_OWNER_OK),
              monthly universe, ECB flag dates (H1).
- sim_g1.py   12 configs, signal layer (PnL-free) + execution engine; real run locked (--real I_HAVE_A1_PASS).
- eval_g1.py  metrics TRAIN/WFO/halves, selection, controls (buy-hold, no-gate, random 500), D1-D7, verdict; locked.
- test_g1.py  tests (a)-(h).

## One-line commands (from ~/claude_master/w3/fx/g1/code)
- tests:        python3 test_g1.py                      (~3 min; log -> stderr)
- loader check: python3 load_g1.py                      (universe counts only)
- RUN (only after A1 PASS + MASTER go):  python3 eval_g1.py --real I_HAVE_A1_PASS   -> ../out/EVAL_G1.{md,json}
- daily series + ledgers (optional):     python3 sim_g1.py --real I_HAVE_A1_PASS    -> ../out/daily_*, ledger_*

## Test results after ERRATA3 2026-11-27 (out/test_run3.log; run1 pre-ERRATA2, run2 pre-ERRATA3): DONE fails=0, a-i PASS
- a PASS quote direction: 9 DEX* mapped as brief; +1% foreign appreciation -> long return exactly +0.01 via file loader.
- b PASS causality on real data <= 2019-12-31 (positions/gate only): prices/VIX after t and rates of months >= month(t)
       randomised at 6 probe dates x 5 configs -> schedule (targets, gate flags) and v/q/trig arrays up to t unchanged;
       non-vacuous check; q_t unchanged when v_t alone is changed. HANDCHECK 2008-09/10 (universe, d, ranking, weights)
       logged: e.g. end-2008-10 k=2 long NZD,AUD short CAD,JPY (d from 2008-09 rates).
- c PASS hand month (synthetic 2000-02: 2 long / 2 short, entry cost, 2 price jumps, 29 calendar days carry incl.
       margin) equity matches hand formula to 1e-12; J1 hand answers: USDNOK 8.0 one-way 1.5 bp (3 bp floor), USDJPY 80
       1.875 bp (3 pip wins), USDJPY 110 1.5 bp, EURUSD 1.25 0.32 bp.
- d PASS gate: FX_VOL spike -> flat exactly on spike day, x2 cost, reopen exactly at next rebalance; spike on a
       rebalance day -> not opened, reopen next month; N10 inactive with short history; VIX spike day Y -> flat Y+1;
       J2: FX_VOL = hand mean of all ccys with a price on t (ccy without any rate included, missing-price ccy excluded).
- e PASS universe synthetic (rate m-1 missing, USD missing -> empty, 4 missing days out / 3 in, n<2k no trade,
       missing exec price -> next valid day) + real universe == universe_by_month.csv for 312 months 1994-2019.
- f PASS cutoff: cutoff > 2019-12-31 refused (any token except owner flag); rows > cutoff skipped at read; G1Data
       asserts; sim/eval main exit 2 without --real token.
- g PASS synthetic planted premium -> "DAT" (all D1-D7, p=0.000, 500 random); synthetic noise -> "KHONG DAT" (p=0.85).
- h PASS determinism (eval twice identical JSON; sim twice identical).
- i PASS ERRATA3 K6/NHO-7: q_t excludes t at non-max v_t; select by TRAIN only; random + x2 calls use selected k/gate
       (spy); x2 doubles costs; D6 hand series; D1-D7 boundaries; K1 p hand values; simulate/evaluate locked on real data.

## Not done (by brief): no return / Sharpe / statistic computed on real data. Open: real 2008-10 PnL hand check (A1-results, ERRATA2 J6).
