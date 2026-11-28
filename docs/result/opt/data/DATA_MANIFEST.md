# DATA_MANIFEST PROGRAM_OPT (FINAL 2026-11-28 ~14:30 UTC)
All ts = UTC ms; bar ts = OPEN time. Nothing >= 2026-01-01 stored (V2 ge_2026=0; no filename with 2026 under raw/).
Per-file sha256/rows: state/MANIFEST_FILES.json (merged files) and state/trades_manifest.csv (one line per day file).
trades_manifest.csv sha256 = 9f04a4fbd4d8e3f9e1d550787789693371f95b80824e178256d94178bc98dc55

| set | path | files | rows | span (UTC) | size | sha256 |
|---|---|---|---|---|---|---|
| D2 option trades | raw/trades/<CUR>/<YYYY-MM>/<CUR>_<day>.parquet | 5 024 (BTC 2 557, ETH 2 467) | 36 717 392 (BTC 21 578 349, ETH 15 139 043) | BTC 2019-01-01 00:03:31.703 .. 2025-12-31 23:58:17.074; ETH 2019-04-01 00:28:49.524 .. 2025-12-31 23:57:38.226 | 961M | see trades_manifest.csv |
| D1 DVOL 1h | raw/dvol_1h.parquet | 1 | 83 712 (2x41 856) | 2021-03-24 00:00 .. 2025-12-31 23:00 | 1.0 MB | 5d5d93ec... |
| D1 DVOL 1D | raw/dvol_1d.parquet | 1 | 3 488 | 2021-03-24 .. 2025-12-31 | 66 KB | 05a22fd6... |
| D5 instruments | raw/instruments_option.parquet | 1 | 221 068 | created < 2026 | 0.8 MB | 00dbdf8a... |
| D5 delivery | raw/delivery_prices.parquet | 1 | 4 542 (btc 2 351 from 2016-03-18, eth 2 191 from 2019-03-29) | ..2025-12-31 | 38 KB | 3ee6649b... |
| D4 BTCUSDT 1h/1m/funding | raw/binance_perp_BTCUSDT_{1h,1m,funding}.parquet | 3 | 52 608 / 3 156 480 / 6 576 | 2020-01-01 .. 2025-12-31 | 3.8 MB / 130 MB / 77 KB | d93d549e / 78b2c2b5 / 813d77db |
| D4 ETHUSDT 1h/1m/funding | raw/binance_perp_ETHUSDT_{1h,1m,funding}.parquet | 3 | 52 608 / 3 156 480 / 6 576 | 2020-01-01 .. 2025-12-31 | 3.6 MB / 130 MB / 77 KB | daeeae61 / 4a583ad9 / 67190303 |
| D3 EOH | raw/binance_eoh/*.zip + .CHECKSUM; raw/binance_eoh_summary.parquet | 545 zips | 2 005 810 (ETH 979 331, BTC 796 972, BNB 147 799, XRP 65 244, DOGE 16 464) | 2023-05-18 .. 2023-10-23 | 139 MB zips + 138 MB | 81abf3cd... ; 545/545 checksum ok |
| D3 BVOL 1h | raw/binance_bvol_1h/<SYM>_<day>.parquet -> raw/binance_bvol_1h.parquet | per-day + 1 | 43 357 (BTC 21 679, ETH 21 678) | 2023-06-20 00:00 .. 2025-12-14 06:00 | 1.4 MB | a9756120... |
(full sha256 in state/MANIFEST_FILES.json)

## Verify (all PASS)
V6 fake-API 160 cases + stuck/edge/empty; real 2 days: one-pass == interrupted+resume == count10000 (identical hash). state/VERIFY_V6.json
FULL (state/VERIFY_FULL.json, seed 20261128): V1 0 instruments with trade_seq gaps, 0 dup/backward (BTC 79 646 instr, ETH 80 056); V2 all 0; V3 30/30 (2019..2025-04); V5 159 702 names 100% match; V4 no zero-trade day, no missing day file.
Bounds (state/CHECK_BOUNDS.json): API recount == stored (same trade_id set): BTC 2022-06-30 10 204, 2022-07-01 10 793, BTC 2025-12-31 8 525, ETH 2025-12-31 3 270, BTC 2019-01-01 253, ETH 2019-04-01 98.
DVOL 0 gaps; 1D close == 1h 23:00 close 3488/3488. D4 2022 1h close vs res1109 kl 8760/8760 exact (BTC, ETH); funding exactly 3/day, no missing day.

## Known limits
- iv == 0 in 0.2-1.6% of trades every year; iv > 400 0.04-0.2%; ETH iv capped 500 (2019-20), 999 seen 2024, q99.9 509 in 2025. Filter in features.
- iv / index_price / mark_price never null. Sparse fields: block_trade_id / block_trade_leg_count (~98% null 2025), combo_id (from 2022 only; ~98% null 2025), combo_trade_id, liquidation (99.6-99.8% null 2025), block_rfq_id (99.5%+ null, recent only), contracts (null in older years). extra column always null (no unknown keys).
- trade_seq first value != 1 for 137 BTC / 64 ETH instruments listed before the pull start (expected).
- Binance Vision UM klines start 2020-01 (no 2019-12).
- Vision 1m files contain FLAT zero-volume filler bars (holes), not missing rows: BTC 369 zero-trade minutes (13 runs), ETH 302 (40 runs); runs >= 5 min shared by both: 2021-03-02 01:01 (59m), 2022-05-01 22:26 (29), 2022-05-28 16:40 (35), 2023-09-12 08:34 (19), 2024-10-28 16:21 (14) and 20:00 (74), 2025-01-29 01:23 (13), 2025-08-29 06:19 (18); BTC only 2023-11-10 15:07 (99m). Consequence: the only BTC 1h-vs-1m(:59) close mismatch is 2023-11-10 15:00 (1h close 37092.6 vs 1m 37118.4, 1h vol 13 405 vs 1m sum 1 352) = 1m source hole, the 1h file is self-consistent. Also 16 BTC hours where 1h trades/volume != sum of 1m (small, e.g. 2021-01-12 06:00 179 140 vs 178 607) -> treat Vision 1h and 1m as separate sources; use 1h for hourly grid; for Kenh A entry at 1m close skip/flag zero-volume minutes.
- BVOL: 120 (BTC) / 121 (ETH) missing hours, 118 / 259 hours with < 3 500 points; data on Vision ends 2025-12-14 06:00 then resumes 2026 (not fetched).
- R0 minor breach (ERRATA2 by MASTER): BVOL listing initially unfiltered -> zip BTCBVOLUSDT 2026-01-05 downloaded into RAM, 0 rows kept, empty parquet deleted; listing now filtered <= 2025-12-31.
- AUX_BINANCE.json lacks D4 entries (lost on rerun); D4 numbers are here, in logs/aux_binance.log and state/CHECK_D4.json.
