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
| **features** | FAIL | 27/33 feature lech (exact<=1e-08, inline<=1e-03; o nguong may 29/33) |
| **gate** | FAIL | 242 gate=fixed, thr 0.0326 > p15_max 0.0150 => n_pass=0 (baseline=ratio) |
| **marketparams** | MISSING | field: rateDownAvg/rateDown15MAvg khop muc nhieu (<1e-3); rateUpAvg MISSING (khong dump); nguong MATCH default; flip LIVE=0/0, DEV(stress)=0/1 |
| **selector** | MISSING | MISSING: thieu nguon selector doi ung (khong co cot score/rank) |
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

- metrics: `{"feat_fail": 27, "feat_fail_machine_tol": 29, "files": 6, "inline_minutes": 1426, "pairs": 385, "reconstructed": ["momentum15M", "momentum1M", "momentumAcceleration"], "symbols": ["BTCUSDT"], "tol": 1e-08, "tol_inline": 0.001, "truncated_files": 6}`

- [PASS] input.integrity: LIVE files=6 (cut cut=6 — GOC: writer Java khong finalize GZIPOutputStream (thieu gz trailer; da xac minh tren CA file 242 moi nhat 20261001_090200) => harness phuc hoi dong hoan chinh bang partial-inflate), pairs=385
- [PASS] input.inline_source: tai tao inline 1426 phut (md_inline<-kline 242)
- [PASS] input.pair: 385 cap (ts) giao
- [PASS] output.nan: NaN LIVE bất thường=0
- [FAIL] output.feature_parity: 27/33 feature vuot nguong (exact<=1e-08 / inline<=1e-03); o nguong MAY (1e-08): 29/33 vuot

| feature | n | max\|Δ\| | mean\|Δ\| | corr | status |
|---|---|---|---|---|---|
| momentum1M | 385 | 7.492e-04 | 5.296e-05 | 0.9942 | PASS |
| momentum5M | 385 | 0.002 | 1.683e-04 | 0.9311 | FAIL |
| momentum15M | 385 | 7.399e-04 | 5.833e-05 | 0.9995 | PASS |
| momentum1H | 385 | 0.001 | 8.774e-05 | 0.9967 | FAIL |
| momentum4H | 385 | 6.870e-04 | 2.792e-05 | 0.9998 | FAIL |
| momentum24H | 385 | 6.810e-04 | 2.773e-05 | 0.9998 | FAIL |
| momentumAcceleration | 385 | 0.002 | 1.804e-04 | 0.9945 | FAIL |
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
- [MISSING] gate.p15_dev_parity: nguon p15 DEV KHONG-ONNX = pred.bin (n=2500260, ts 1617210000000..1767225540000). Cua so LIVE 1790559600000..1790617260000: giao=KHONG => KHONG so cung phut duoc => MISSING (2026=holdout, ngoai DEV<=2025-12-31)

### marketparams — MISSING

- metrics: `{"dev_flips": {"bigdown_a": 0, "bigdown_b": 0, "bigdown_flips": 0, "dca_a": 1, "dca_b": 0, "dca_flips": 1}, "dev_store": {"n": 1376, "rateDown15MAvg_corr": 0.9977090169770493, "rateDown15MAvg_maxabs": 0.0020271385816998146, "rateDownAvg_corr": 0.9969522638229248, "rateDownAvg_maxabs": 0.000978882038359503}, "inline_minutes": 1426, "live_minutes": 502, "thr_live_overrides": {}, "thresholds": [{"default": -0.03157, "key": "MS_DOWN_BIG_AVG", "live": "(unset)", "profile": "(unset)", "verdict": "MATCH-DEFAULT"}, {"default": -0.03157, "key": "MS_DOWN_BIG_AVG_DCA", "live": "(unset)", "profile": "(unset)", "verdict": "MATCH-DEFAULT"}, {"default": 0.02046, "key": "MS_UP_BIG_THRES", "live": "(unset)", "profile": "(unset)", "verdict": "MATCH-DEFAULT"}]}`

- [PASS] input.live: LIVE feat_dump: 502 phut (momentum1M=rateDownAvg, momentum15M=rateDown15MAvg)
- [PASS] input.pair: 502 phut giao (LIVE vs inline=cung thuat toan calMarketData)
- [MISSING] mp.fields_live_vs_inline: 2/4 field do duoc: rateDownAvg max|d|=7.492e-04 corr=0.99485 ; rateDown15MAvg max|d|=7.399e-04 corr=0.99958
- [PASS] mp.decision_flips_live: BIG_DOWN flip=0 (live=0 inline=0); DCA flip=0 (live=0 inline=0)
- [PASS] mp.dev_store: market.bin(DEV store) vs inline @2025-10-10: n=1376; rateDownAvg max|d|=9.789e-04 corr=0.9970; rateDown15MAvg max|d|=2.027e-03 corr=0.9977; BIG_DOWN flip=0 DCA flip=1
- [MISSING] mp.live_vs_store_sameminute: LIVE(2026-09) vs market.bin(<=2025-12-31): giao=0 phut => khong so truc tiep cung phut duoc; dung inline lam cau noi (ca 2 phia khop ~1e-3)
- [PASS] mp.thresholds: 3 nguong: 242 & baseline deu UNSET -> cung default Java (-0.03157/-0.03157/0.02046)

nguong (242 vs baseline vs default Java):

| key | profile | LIVE | default | verdict |
|---|---|---|---|---|
| `MS_DOWN_BIG_AVG` | (unset) | (unset) | -0.03157 | MATCH-DEFAULT |
| `MS_DOWN_BIG_AVG_DCA` | (unset) | (unset) | -0.03157 | MATCH-DEFAULT |
| `MS_UP_BIG_THRES` | (unset) | (unset) | 0.02046 | MATCH-DEFAULT |

| field | col | n | max\|Δ\| | mean\|Δ\| | corr | status |
|---|---|---|---|---|---|---|
| rateDownAvg | momentum1M | 502 | 7.492e-04 | 4.477e-05 | 0.9949 | PASS |
| rateDown15MAvg | momentum15M | 502 | 7.399e-04 | 5.591e-05 | 0.9996 | PASS |
| rateUpAvg | - | 0 | - | - | - | MISSING |
| rateUp15MAvg | - | 0 | - | - | - | N/A |
| THR:MS_DOWN_BIG_AVG | MS_DOWN_BIG_AVG | 0 | 0.000e+00 | 0.000e+00 | 1.0000 | MATCH-DEFAULT |
| THR:MS_DOWN_BIG_AVG_DCA | MS_DOWN_BIG_AVG_DCA | 0 | 0.000e+00 | 0.000e+00 | 1.0000 | MATCH-DEFAULT |
| THR:MS_UP_BIG_THRES | MS_UP_BIG_THRES | 0 | 0.000e+00 | 0.000e+00 | 1.0000 | MATCH-DEFAULT |

### selector — MISSING

- metrics: `{"feat_dump_cols": 36, "has_selector_col": false}`

- [MISSING] input.live: feat_dump co cot selectorScore/rank? KHONG (cot hien co: 36)
- [MISSING] input.artifact: artifact selector LIVE = Java-serialized HashMap<String,Float> (242 storage/data/predictionSymbol/*) — lan ghi CUOI 2026-08-20, KHONG phu cua so LIVE 2026-09-28; khong co artifact selector BACKTEST cung tick.
- [MISSING] output.compare: khong so duoc score/rank tung tick. De xuat: them cot selectorScore+rank vao feat_dump CSV (CA live lan export) => khi do harness do duoc rank-overlap/top-K parity khong can ONNX.

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
