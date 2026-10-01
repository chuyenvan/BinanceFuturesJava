# PARITY REPORT — shadow/242 ↔ BACKTEST

> Sinh boi `research/parity/parity_check.py` (deterministic). Pre-reg: `docs/prereg/PREREG_PARITY_HARNESS.md`.

- **Tong ket: `FAIL`** (exit_code=2)

- 2026 = HOLDOUT: chi do/doi chieu (audit-only), KHONG chon tham so


## Input (md5)

| label | path | md5 | bytes |
|---|---|---|---|
| baseline_profile | `/home/ubuntu/src/BinanceFuturesJava/profiles/g2_flat3.properties` | c6d4ef57ecee25c663d2d396ac574c30 | 5307 |
| live_cfg_snapshot | `/home/ubuntu/src/BinanceFuturesJava/research/parity/data/live_242_config.snapshot` | c977f4b9e23876cbded26741aac7469b | 2059 |
| live_log_summary | `/home/ubuntu/src/BinanceFuturesJava/research/parity/data/live_242_log_summary.json` | 2a748017bbc710ee7605c3e945412171 | 346 |
| dev_export | `/home/ubuntu/claudedata/devexport_202609/devexport_20260701_20260928_FULL.csv.gz` | f8cb50f79d5f4098192af6e55e42e3fb | 14610639 |

## Tang

| tang | trang thai | ly do |
|---|---|---|
| **config** | PASS | khop |
| **features** | FAIL | 27/33 feature lech (exact<=1e-08, inline<=1e-03; o nguong may 29/33) |
| **gate** | MISSING | 242 gate=ratio, thr 0.0339 > p15_max 0.0150 => n_pass=0 (baseline=ratio) |
| **marketparams** | MISSING | 4/4 field: rateDownAvg/rateUpAvg/rateDown15MAvg khop muc nhieu ticker-vs-kline (LIVE&DEV, max|d|~7e-4..2e-3, corr>0.99); rateUp15MAvg=0 ca 2 phia (khong duoc calMarketData tinh); nguong MATCH default; flip LIVE=0/0, DEV(stress)=0/1 |
| **selector** | MISSING | MISSING cung-tick: đo được phía LIVE (artifact 20260928: 249 tick, 163520 dong), thiếu đối ứng cung-tick DEV |
| **entry** | FAIL | entry lech: LIVE=0 vs BACKTEST(G2)>=1 |
| **exit** | MISSING | MISSING: khong co lenh dong (gate chan truoc) |

### config — PASS

- metrics: `{"lech": 0, "match": 27, "missing": 0}`

- [PASS] input.baseline: profile 31 key
- [PASS] input.live: snapshot 242 71 key non-secret
- [PASS] config.key_parity: MATCH=27 LECH=0 MISSING=0 (khong tinh SKIP)

| key | profile | LIVE | verdict |
|---|---|---|---|
| `SELECTOR_RANK_TOPK` | 16 | 16 | MATCH |
| `SELECTOR_ONLY_ENTRY` | 0 | 0 | MATCH |
| `SIM_MIN_MOMENTUM_15M` | 0.008 | 0.008 | MATCH |
| `SIM_GATE_ROLLING_MODE` | ratio | ratio | MATCH |
| `SIM_GATE_ROLLING_DAYS` | 90 | 90 | MATCH |
| `SIM_GATE_ROLLING_PCT` | 0.999950829 | 0.999950829 | MATCH |
| `SIM_GATE_DYN_SCALE` | 1.55 | 1.55 | MATCH |
| `SIM_RATE_PROFIT_STOP_MARKET` | 0.07 | 0.07 | MATCH |
| `TS_GIVEBACK_RATIO` | 1.0 | 1.0 | MATCH |
| `SIM_TS_MAX_GAP` | 0.03 | 0.03 | MATCH |
| `SIM_TS_MAX_GAP_WEAK` | 0.03 | 0.03 | MATCH |
| `SIM_TS_GIVEBACK` | 1 | 1 | MATCH |
| `SIM_LOSER_TIME_STOP_HOURS` | 168 | 168 | MATCH |
| `DCA_GRID_SCALE` | 6.0 | 6.0 | MATCH |
| `DCA_GRID_WEIGHTS` | 1,1,1,1 | 1,1,1,1 | MATCH |
| `TIER_FLAT` | 1 | 1 | MATCH |
| `SIM_F_BASE` | 0.015 | 0.015 | MATCH |
| `CAPITAL_START` | 35000 | 35000 | MATCH |
| `SIM_RATE_FEE` | 0.000982 | 0.000982 | MATCH |
| `SIM_SLIPPAGE_RATE` | 0.000067 | 0.000067 | MATCH |
| `SIM_FIX_B1` | true | true | MATCH |
| `SIM_FIX_B2` | true | true | MATCH |
| `SIM_FIX_B3` | true | true | MATCH |
| `SIM_BREAKER_MODE` | OFF | OFF | MATCH |
| `CONC_CAP_PERCOIN_ENABLED` | true | true | MATCH |
| `CONC_CAP_PERCOIN_PCT` | 0.15 | 0.15 | MATCH |
| `SIM_ENTRY_SAMPLE_MIN` | 1 | 1 | MATCH |

### features — FAIL

- metrics: `{"fail_groups": {"i-nhieu-ticker-vs-kline": 15, "i-ti-so-nhay (nhieu ticker-vs-kline)": 5, "ii-export-thieu-nguon(=0) + logic con lai": 1, "iii-nghi-logic/tap-hop (can control cung-nguon)": 6}, "feat_fail": 27, "feat_fail_machine_tol": 29, "files": 6, "inline_minutes": 1426, "pairs": 385, "reconstructed": ["momentum15M", "momentum1M", "momentumAcceleration"], "symbols": ["BTCUSDT"], "tol": 1e-08, "tol_inline": 0.001, "truncated_files": 6}`

- [PASS] input.integrity: LIVE files=6 (thieu-trailer=6, sync-flush-tail=6 — GOC VIEC1: file thieu gz trailer=6/6, tail sync-flush(00 00 FF FF)=6/6 => writer da flush() nhung KHONG finalize: src/main/java/com/binance/chuyennd/ai_ml/features/export/entry/LiveFeatureDump.java:133-146 (syncFlush=true) + close():148-155 CHI goi khi du REMAINING/200MB; KHONG co shutdown hook => JVM restart giua chung => thieu trailer => harness phuc hoi dong hoan chinh bang partial-inflate), pairs=385
- [PASS] input.inline_source: tai tao inline 1426 phut (md_inline<-kline 242)
- [PASS] input.pair: 385 cap (ts) giao
- [PASS] output.nan: NaN LIVE bất thường=0
- [FAIL] output.feature_parity: 27/33 feature vuot nguong (exact<=1e-08 / inline<=1e-03); o nguong MAY (1e-08): 29/33 vuot

| feature | n | max\|Δ\| | mean\|Δ\| | corr | exp0 | status | nhom (VIEC4) |
|---|---|---|---|---|---|---|---|
| momentum1M | 385 | 7.492e-04 | 5.296e-05 | 0.9942 | 0.00e+00 | PASS | ok |
| momentum5M | 385 | 0.002 | 1.683e-04 | 0.9311 | 0.00e+00 | FAIL | i-nhieu-ticker-vs-kline |
| momentum15M | 385 | 7.399e-04 | 5.833e-05 | 0.9995 | 0.00e+00 | PASS | ok |
| momentum1H | 385 | 0.001 | 8.774e-05 | 0.9967 | 0.00e+00 | FAIL | i-nhieu-ticker-vs-kline |
| momentum4H | 385 | 6.870e-04 | 2.792e-05 | 0.9998 | 0.00e+00 | FAIL | i-nhieu-ticker-vs-kline |
| momentum24H | 385 | 6.810e-04 | 2.773e-05 | 0.9998 | 0.00e+00 | FAIL | i-nhieu-ticker-vs-kline |
| momentumAcceleration | 385 | 0.002 | 1.804e-04 | 0.9945 | 0.00e+00 | FAIL | ii-export-thieu-nguon(=0) + logic con lai |
| trendStrengthETH | 385 | 0.002 | 9.887e-05 | 0.9975 | 0.00e+00 | FAIL | i-nhieu-ticker-vs-kline |
| trendConsistency | 385 | 2.000 | 0.135 | 0.8560 | 0.00e+00 | FAIL | i-nhieu-ticker-vs-kline |
| volatility1M | 385 | 0.002 | 1.883e-04 | 0.5200 | 0.00e+00 | FAIL | iii-nghi-logic/tap-hop (can control cung-nguon) |
| volatility15M | 385 | 0.001 | 1.177e-04 | 0.5457 | 0.00e+00 | FAIL | iii-nghi-logic/tap-hop (can control cung-nguon) |
| volatility1H | 385 | 4.806e-04 | 9.015e-05 | 0.4743 | 0.00e+00 | FAIL | iii-nghi-logic/tap-hop (can control cung-nguon) |
| volatility24H | 385 | 1.247e-05 | 3.402e-06 | 0.9861 | 0.00e+00 | FAIL | i-nhieu-ticker-vs-kline |
| volatilityTermStructure | 385 | 1.300 | 0.238 | 0.5300 | 0.00e+00 | FAIL | iii-nghi-logic/tap-hop (can control cung-nguon) |
| advanceDeclineRatio | 385 | 6.637 | 0.204 | 0.9839 | 0.00e+00 | FAIL | i-ti-so-nhay (nhieu ticker-vs-kline) |
| percentAboveMA20 | 385 | 0.646 | 0.058 | 0.9029 | 0.00e+00 | FAIL | i-nhieu-ticker-vs-kline |
| volumeRatioUpDown | 385 | 236.264 | 2.014 | 0.6357 | 0.00e+00 | FAIL | i-ti-so-nhay (nhieu ticker-vs-kline) |
| marketBreadthStrength | 385 | 0.263 | 0.017 | 0.9942 | 0.00e+00 | FAIL | i-nhieu-ticker-vs-kline |
| btcDominance | 385 | 0.646 | 0.065 | 0.5611 | 0.00e+00 | FAIL | i-ti-so-nhay (nhieu ticker-vs-kline) |
| rsi14 | 385 | 40.294 | 4.167 | 0.8620 | 0.00e+00 | FAIL | i-nhieu-ticker-vs-kline |
| volumeSpike | 385 | 122.710 | 1.328 | 0.6939 | 0.00e+00 | FAIL | i-ti-so-nhay (nhieu ticker-vs-kline) |
| distMA20 | 385 | 0.003 | 3.227e-04 | 0.8526 | 0.00e+00 | FAIL | i-nhieu-ticker-vs-kline |
| fundingRateRaw | 385 | 4.619e-05 | 1.791e-05 | 0.8970 | 0.00e+00 | FAIL | i-nhieu-ticker-vs-kline |
| fundingRateAvg24H | 385 | 1.352e-05 | 7.152e-06 | 0.0389 | 0.00e+00 | FAIL | iii-nghi-logic/tap-hop (can control cung-nguon) |
| fundingRateTrend | 385 | 3.267e-05 | 1.076e-05 | 0.9368 | 0.00e+00 | FAIL | i-nhieu-ticker-vs-kline |
| hourOfDay | 385 | 0.000e+00 | 0.000e+00 | 1.0000 | 0.00e+00 | PASS | ok |
| dayOfWeek | 385 | 0.000e+00 | 0.000e+00 | nan | 0.00e+00 | PASS | ok |
| weekOfMonth | 385 | 0.000e+00 | 0.000e+00 | nan | 0.00e+00 | PASS | ok |
| monthOfYear | 385 | 0.000e+00 | 0.000e+00 | nan | 0.00e+00 | PASS | ok |
| basketMomentum15M | 385 | 0.020 | 0.002 | 0.5453 | 0.00e+00 | FAIL | iii-nghi-logic/tap-hop (can control cung-nguon) |
| basketMomentum1H | 385 | 0.020 | 0.002 | 0.7035 | 0.00e+00 | FAIL | i-nhieu-ticker-vs-kline |
| basketRsi14 | 385 | 29.961 | 3.023 | 0.8615 | 0.00e+00 | FAIL | i-nhieu-ticker-vs-kline |
| basketVolSpike | 385 | 79.601 | 1.022 | 0.1042 | 0.00e+00 | FAIL | i-ti-so-nhay (nhieu ticker-vs-kline) |

### gate — MISSING

- metrics: `{"baseline_mode": "ratio", "gate_npass_total": 0, "live_mode": "ratio", "p15_dev": {"dev": {"n": 2500260, "p15_max": 0.12261255830526352, "p15_mean": 0.005854084683967189, "p15_min": 0.002019499894231558, "p15_q": {"0.5": 0.005452214973047376, "0.99": 0.013078836379572755, "0.999": 0.028179553244261704, "0.9999": 0.06818976540344729}, "risk_mean": -0.017001774267111417, "ts0": 1617210000000, "ts1": 1767225540000}, "live_window": [1790559600000, 1790617260000], "overlap_live_minutes": 0}, "p15_live_max": 0.0150123108, "thr_applied_max": 0.04702, "thr_applied_min": 0.03388}`

- [PASS] input.live: LIVE p15 n=502 max=0.01501
- [PASS] gate.repro: n_pass log=0; p15_max=0.01501 < thr_min=0.03388 => dong nhat (0 pass)
- [PASS] gate.mode_parity: LIVE gate mode=ratio vs BASELINE=ratio
- [PASS] gate.p15_dev.csv: dump p15 DEV (nguon KHONG-ONNX pred.bin) -> p15_dev.csv (n=2500260)
- [PASS] gate.p15_dev.stats: DEV p15: n=2500260 ts 1617210000000..1767225540000; min=0.0020 q0.5=0.00545 q0.99=0.0131 q0.999=0.0282 max=0.1226
- [MISSING] gate.p15_dev_parity: pred.bin(DEV<=2025-12-31) KHONG phu cua so LIVE(2026-09-28) => giao=0 phut, khong so cung phut duoc (2026 = holdout) => giu MISSING + ly do; de xuat: xuat p15 ra kline LIVE

### marketparams — MISSING

- metrics: `{"dev_flips": {"bigdown_a": 0, "bigdown_b": 0, "bigdown_flips": 0, "dca_a": 1, "dca_b": 0, "dca_flips": 1}, "dev_store": {"n": 1376, "rateDown15MAvg_corr": 0.9977090169770493, "rateDown15MAvg_maxabs": 0.0020271385816998146, "rateDownAvg_corr": 0.9969522638229248, "rateDownAvg_maxabs": 0.000978882038359503, "rateUpAvg_corr": 0.997266262938794, "rateUpAvg_maxabs": 0.0006197462125881411}, "fields_measured_4": 4, "inline_minutes": 1426, "live_minutes": 502, "marketparams_csv": "/home/ubuntu/src/BinanceFuturesJava/research/parity/data/marketparams_inline.csv", "thr_live_overrides": {}, "thresholds": [{"default": -0.03157, "key": "MS_DOWN_BIG_AVG", "live": "(unset)", "profile": "(unset)", "verdict": "MATCH-DEFAULT"}, {"default": -0.03157, "key": "MS_DOWN_BIG_AVG_DCA", "live": "(unset)", "profile": "(unset)", "verdict": "MATCH-DEFAULT"}, {"default": 0.02046, "key": "MS_UP_BIG_THRES", "live": "(unset)", "profile": "(unset)", "verdict": "MATCH-DEFAULT"}]}`

- [PASS] input.live: LIVE feat_dump: 502 phut (momentum1M=rateDownAvg, momentum15M=rateDown15MAvg)
- [PASS] input.pair: 502 phut giao (LIVE vs inline=cung thuat toan calMarketData)
- [PASS] mp.fields_live_vs_inline: LIVE vs inline: rateDownAvg max|d|=7.492e-04 corr=0.99485 ; rateDown15MAvg max|d|=7.399e-04 corr=0.99958 (rateUpAvg: feat_dump KHONG xuat -> do o phia DEV store ben duoi)
- [PASS] mp.decision_flips_live: BIG_DOWN flip=0 (live=0 inline=0); DCA flip=0 (live=0 inline=0)
- [PASS] mp.dev_store: market.bin(DEV store) vs inline @2025-10-10: n=1376; rateDownAvg max|d|=9.789e-04 corr=0.9970; rateUpAvg max|d|=6.197e-04 corr=0.9973; rateDown15MAvg max|d|=2.027e-03 corr=0.9977; BIG_DOWN flip=0 DCA flip=1
- [PASS] mp.csv_export: xuat 4 field ra CSV (tuong duong --md-inline): marketparams_inline.csv (K=rateDownAvg,rateUpAvg,rateDown15MAvg,rateUp15MAvg) — rateUp15MAvg=0 (khong tinh)
- [PASS] mp.fields4: 4/4 field market DO DUOC (rateDownAvg/rateUpAvg/rateDown15MAvg max|d|<=~1e-3 muc nhieu; rateUp15MAvg=0 ca 2 phia). LIVE-side truc tiep: 2/4 (dump thieu cot rateUpAvg/rateUp15MAvg)
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
| rateUpAvg | market.bin[1] | 1376 | 6.197e-04 | 1.475e-04 | 0.9973 | PASS |
| rateUp15MAvg | - | 1376 | 0.000e+00 | 0.000e+00 | 1.0000 | PASS |
| THR:MS_DOWN_BIG_AVG | MS_DOWN_BIG_AVG | 0 | 0.000e+00 | 0.000e+00 | 1.0000 | MATCH-DEFAULT |
| THR:MS_DOWN_BIG_AVG_DCA | MS_DOWN_BIG_AVG_DCA | 0 | 0.000e+00 | 0.000e+00 | 1.0000 | MATCH-DEFAULT |
| THR:MS_UP_BIG_THRES | MS_UP_BIG_THRES | 0 | 0.000e+00 | 0.000e+00 | 1.0000 | MATCH-DEFAULT |

### selector — MISSING

- metrics: `{"dev_selector": {"first_len": 110, "n": 2301065, "ts0": 1625072400000, "ts1": 1767200400000}, "feat_dump_cols": 36, "has_selector_col": false, "live_artifact_day": "20260928", "live_rows": 163520, "live_syms_per_tick": [533, 719], "live_ticks": 249, "selector_csv": "/home/ubuntu/src/BinanceFuturesJava/research/parity/data/selector_live.csv"}`

- [MISSING] input.live_col: feat_dump KHONG co cot selectorScore/rank (cot hien co: 36)
- [PASS] input.artifact: artifact LIVE 20260928/* : ticks=249 rows=163520 syms/tick=533..719 -> selector_live.csv (RAW, khong ONNX)
- [PASS] input.dev_source: nguon selector DEV = funding.bin (n=2301065 ts 1625072400000..1767200400000) — KHONG-ONNX
- [MISSING] output.compare: funding.bin(1625072400000..1767200400000) KHONG phu cua so LIVE(1790559600000..1790617260000) => KHONG so cung tick; de xuat: them cot selectorScore+rank vao feat_dump (ca live lan export)

### entry — FAIL

- metrics: `{"backtest_entries_min": 1, "gate_all_zero": true, "gate_lines": 2834, "live_entries": 0, "window_candidates": 502}`

- [PASS] input.live: 2834 dong [GATE], all n_pass=0=True, ledger trades=0? next
- [PASS] entry.live_consistency: n_pass=0 nhat quan voi p15_max=0.01501 < thr=0.03388
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
| gz_writer_finalize | PASS | tai lap: buggy(no-close) decompress_ok=False tail=0000ffff | fixed(close) ok=True | file that khop True |
