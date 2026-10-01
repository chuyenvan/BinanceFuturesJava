# PARITY REPORT — shadow/242 ↔ BACKTEST

> Sinh boi `research/parity/parity_check.py` (deterministic). Pre-reg: `docs/prereg/PREREG_PARITY_HARNESS.md`.

- **Tong ket: `FAIL`** (exit_code=2)

- 2026 = HOLDOUT: chi do/doi chieu (audit-only), KHONG chon tham so


## Input (md5)

| label | path | md5 | bytes |
|---|---|---|---|
| baseline_profile | `/home/ubuntu/src/BinanceFuturesJava/profiles/g2_flat3.properties` | c6d4ef57ecee25c663d2d396ac574c30 | 5307 |
| live_cfg_snapshot | `/home/ubuntu/src/BinanceFuturesJava/research/parity/data/live_242_config.snapshot` | c3be2af63df2f55792699b149b70a984 | 1623 |
| live_log_summary | `/home/ubuntu/src/BinanceFuturesJava/research/parity/data/live_242_log_summary.json` | b0405433d6bf59c777802fec9337f390 | 346 |
| dev_export | `/home/ubuntu/claudedata/devexport_202609/devexport_20260701_20260928_FULL.csv.gz` | f8cb50f79d5f4098192af6e55e42e3fb | 14610639 |

## Tang

| tang | trang thai | ly do |
|---|---|---|
| **config** | FAIL | 242 KHONG khop baseline: 4 LECH + 18 MISSING key |
| **features** | FAIL | 29/33 feature lech (max|delta|>1e-08) |
| **gate** | FAIL | 242 gate=fixed, thr 0.0326 > p15_max 0.0150 => n_pass=0 (baseline=ratio) |
| **selector** | MISSING | MISSING: thieu nguon selector doi ung |
| **entry** | FAIL | entry lech: LIVE=0 vs BACKTEST(G2)>=1 |
| **exit** | MISSING | MISSING: khong co lenh dong (gate chan truoc) |

### config — FAIL

- metrics: `{"lech": 4, "match": 5, "missing": 18}`

- [PASS] input.baseline: profile 31 key
- [PASS] input.live: snapshot 242 52 key non-secret
- [FAIL] config.key_parity: MATCH=5 LECH=4 MISSING=18 (khong tinh SKIP)

| key | profile | LIVE | verdict |
|---|---|---|---|
| `SELECTOR_RANK_TOPK` | 16 | 16 | MATCH |
| `SELECTOR_ONLY_ENTRY` | 0 | (unset) | MISSING |
| `SIM_MIN_MOMENTUM_15M` | 0.008 | 0.008 | MATCH |
| `SIM_GATE_ROLLING_MODE` | ratio | (unset) | MISSING |
| `SIM_GATE_ROLLING_DAYS` | 90 | (unset) | MISSING |
| `SIM_GATE_ROLLING_PCT` | 0.999950829 | (unset) | MISSING |
| `SIM_GATE_DYN_SCALE` | 1.55 | 1.70 | LECH |
| `SIM_RATE_PROFIT_STOP_MARKET` | 0.07 | 0.05 | LECH |
| `TS_GIVEBACK_RATIO` | 1.0 | (unset; default=0.5) | MISSING |
| `SIM_TS_MAX_GAP` | 0.03 | (unset; default=0.08) | MISSING |
| `SIM_TS_MAX_GAP_WEAK` | 0.03 | (unset; default=0.03) | MATCH-DEFAULT |
| `SIM_TS_GIVEBACK` | 1 | (unset) | MISSING |
| `SIM_LOSER_TIME_STOP_HOURS` | 168 | (unset) | MISSING |
| `DCA_GRID_SCALE` | 6.0 | (unset) | MISSING |
| `DCA_GRID_WEIGHTS` | 1,1,1,1 | 1,0,0,0 | LECH |
| `TIER_FLAT` | 1 | 1 | MATCH |
| `SIM_F_BASE` | 0.015 | (unset; default=0.03) | MISSING |
| `CAPITAL_START` | 35000 | 14000 | LECH |
| `SIM_RATE_FEE` | 0.000982 | (unset; default=0.002) | MISSING |
| `SIM_SLIPPAGE_RATE` | 0.000067 | (unset; default=0.003) | MISSING |
| `SIM_FIX_B1` | true | (unset) | MISSING |
| `SIM_FIX_B2` | true | (unset) | MISSING |
| `SIM_FIX_B3` | true | (unset) | MISSING |
| `SIM_BREAKER_MODE` | OFF | (unset) | MISSING |
| `CONC_CAP_PERCOIN_ENABLED` | true | (unset; default=False) | MISSING |
| `CONC_CAP_PERCOIN_PCT` | 0.15 | (unset) | MISSING |
| `SIM_ENTRY_SAMPLE_MIN` | 1 | 1 | MATCH |

### features — FAIL

- metrics: `{"feat_fail": 29, "files": 6, "pairs": 385, "symbols": ["BTCUSDT"], "tol": 1e-08, "truncated_files": 6}`

- [PASS] input.integrity: LIVE files=6 (cut cut=6, da phuc hoi partial), pairs=385
- [PASS] input.pair: 385 cap (ts) giao
- [PASS] output.nan: NaN LIVE bất thường=0
- [FAIL] output.feature_parity: 29/33 feature vuot nguong max|delta|<=1e-08

| feature | n | max\|Δ\| | mean\|Δ\| | corr | status |
|---|---|---|---|---|---|
| momentum1M | 385 | 0.009 | 0.002 | nan | FAIL |
| momentum5M | 385 | 0.002 | 1.683e-04 | 0.9311 | FAIL |
| momentum15M | 385 | 0.025 | 0.013 | nan | FAIL |
| momentum1H | 385 | 0.001 | 8.774e-05 | 0.9967 | FAIL |
| momentum4H | 385 | 6.870e-04 | 2.792e-05 | 0.9998 | FAIL |
| momentum24H | 385 | 6.810e-04 | 2.773e-05 | 0.9998 | FAIL |
| momentumAcceleration | 385 | 0.025 | 0.013 | -0.2392 | FAIL |
| trendStrengthETH | 385 | 0.002 | 9.887e-05 | 0.9975 | FAIL |
| trendConsistency | 385 | 2.000 | 0.135 | 0.8560 | FAIL |
| volatility1M | 385 | 0.002 | 1.883e-04 | 0.5200 | FAIL |
| volatility15M | 385 | 0.001 | 1.177e-04 | 0.5457 | FAIL |
| volatility1H | 385 | 4.806e-04 | 9.015e-05 | 0.4743 | FAIL |
| volatility24H | 385 | 1.247e-05 | 3.402e-06 | 0.9861 | FAIL |
| volatilityTermStructure | 385 | 1.300 | 0.238 | 0.5300 | FAIL |
| advanceDeclineRatio | 385 | 6.637 | 0.204 | 0.9839 | FAIL |
| percentAboveMA20 | 385 | 0.646 | 0.058 | 0.9029 | FAIL |
| volumeRatioUpDown | 385 | 236.264 | 2.014 | 0.6357 | FAIL |
| marketBreadthStrength | 385 | 0.263 | 0.017 | 0.9942 | FAIL |
| btcDominance | 385 | 0.646 | 0.065 | 0.5611 | FAIL |
| rsi14 | 385 | 40.294 | 4.167 | 0.8620 | FAIL |
| volumeSpike | 385 | 122.710 | 1.328 | 0.6939 | FAIL |
| distMA20 | 385 | 0.003 | 3.227e-04 | 0.8526 | FAIL |
| fundingRateRaw | 385 | 4.619e-05 | 1.791e-05 | 0.8970 | FAIL |
| fundingRateAvg24H | 385 | 1.352e-05 | 7.152e-06 | 0.0389 | FAIL |
| fundingRateTrend | 385 | 3.267e-05 | 1.076e-05 | 0.9368 | FAIL |
| hourOfDay | 385 | 0.000e+00 | 0.000e+00 | 1.0000 | PASS |
| dayOfWeek | 385 | 0.000e+00 | 0.000e+00 | nan | PASS |
| weekOfMonth | 385 | 0.000e+00 | 0.000e+00 | nan | PASS |
| monthOfYear | 385 | 0.000e+00 | 0.000e+00 | nan | PASS |
| basketMomentum15M | 385 | 0.020 | 0.002 | 0.5453 | FAIL |
| basketMomentum1H | 385 | 0.020 | 0.002 | 0.7035 | FAIL |
| basketRsi14 | 385 | 29.961 | 3.023 | 0.8615 | FAIL |
| basketVolSpike | 385 | 79.601 | 1.022 | 0.1042 | FAIL |

### gate — FAIL

- metrics: `{"baseline_mode": "ratio", "gate_npass_total": 0, "live_mode": "fixed", "p15_live_max": 0.0150123108, "thr_applied_max": 0.04375, "thr_applied_min": 0.03257}`

- [PASS] input.live: LIVE p15 n=502 max=0.01501
- [PASS] gate.repro: n_pass log=0; p15_max=0.01501 < thr_min=0.03257 => dong nhat (0 pass)
- [FAIL] gate.mode_parity: LIVE gate mode=fixed vs BASELINE=ratio
- [MISSING] gate.p15_dev_parity: p15 phia BACKTEST can ONNX inference (bi cam) => khong do duoc; de xuat: dump p15/dev CSV

### selector — MISSING

- [MISSING] input.live: artifact selector LIVE la Java-serialized HashMap<String,Float> (storage/data/predictionSymbol/*), khong co score CSV doc duoc; khong co artifact selector BACKTEST cung tick.
- [MISSING] output.compare: khong so duoc score/rank tung tick. De xuat: them cot selectorScore+rank vao feat_dump CSV (hoac dump CSV rieng) cho CA live lan export.

### entry — FAIL

- metrics: `{"backtest_entries_min": 1, "gate_all_zero": true, "gate_lines": 2818, "live_entries": 0, "window_candidates": 502}`

- [PASS] input.live: 2818 dong [GATE], all n_pass=0=True, ledger trades=0? next
- [PASS] entry.live_consistency: n_pass=0 nhat quan voi p15_max=0.01501 < thr=0.03257
- [FAIL] entry.window_parity: LIVE entries=0 vs BACKTEST(G2) expected>=1

### exit — MISSING

- [MISSING] input.live: ledger 242: 0 lenh dong tu 12/09 (gate dong => khong co lenh)
- [MISSING] output.compare: khong co lenh dong de doi chieu exit (FLAT3 vs T0). De xuat: sau khi gate mo, so TS_GIVEBACK_RATIO/SIM_TS_MAX_GAP tren ledger that + printDone.

## Tu kiem harness

| # | status | detail |
|---|---|---|
| deterministic | PASS | 2 lan tinh features => byte-identical (385 cap) |
| injected_shift_fails_right | PASS | tai hourOfDay status=FAIL; FAIL them moi=['hourOfDay'] (mong doi [hourOfDay]; truoc= PASS) |
| missing_column_fails_with_reason | PASS | FAIL=True err=thieu cot detail=thieu cot trong export: momentum5M |
