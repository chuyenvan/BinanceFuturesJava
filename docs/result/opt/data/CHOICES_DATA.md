# CHOICES_DATA (DEV-DATA PROGRAM_OPT, 2026-11-28)
1. D2 pagination: start_timestamp = ts of last trade (inclusive), dedupe trade_id; raise Stuck if >= count trades share one ms (never silent drop). Probe: start AND end are inclusive (logs/probe.log); query end = next day 00:00 (or 2025-12-31 23:59:59.999 on last day) and filter [day, day+1) locally.
2. count: small window used 1000; full run uses 10000 (probe: count=10000 accepted). V6 real test: 2021-05-18/19 identical hash for count 1000 vs 10000 vs interrupted+resumed.
3. Storage: one parquet (zstd) per (currency, day) inside raw/trades/<CUR>/<YYYY-MM>/ = month partition; atomic tmp+rename; checkpoint json written after rename. Not merged to one file per month (merge is optional later, read the directory).
4. Schema fixed: ints trade_seq,timestamp,tick_direction,block_trade_leg_count; floats price,amount,iv,mark_price,index_price,contracts; strings trade_id,instrument_name,direction,block_trade_id,combo_id,combo_trade_id,liquidation,block_rfq_id; any other API key -> json in column 'extra'. Rows sorted by (timestamp, trade_seq, trade_id).
5. Instruments (D5): history host expired=true + expired=false + www expired=false, dedupe by name, rows with creation_timestamp >= 2026-01-01 dropped (R0). No name conflicts.
6. V1 is computed streaming per currency over consecutive days; gaps counted both within a day and across day boundary.
7. BVOL zip never written to disk (verified sha256 in RAM, reduced to 1h, discarded). EOH zips kept with .CHECKSUM.
UNCERTAIN: iv=0.0 exists (q0.1 of BTC 2021/2025, ETH 2021) and ETH iv capped ~500 -> feature code must filter. liquidation field ~10% of BTC trades in May-2021 week (crash week; plausible). trade_seq first value != 1 for instruments born before window (expected). D4 cross-check vs existing Oracle kline NOT done yet.
## Round 2
8. MASTER accepted count=10000 and per-day files.
9. BUG fixed: BVOL/EOH listing had no date filter; one 2026 BVOL zip (BTCBVOLUSDT 2026-01-05) was downloaded into RAM, 0 rows kept, empty parquet deleted. Now listing <= 2025-12-31.
10. AUX_BINANCE.json lost D4 entries on rerun (rep restarted empty, D4 skipped) - D4 numbers are in logs/aux_binance.log and CHECK_D4.json / MANIFEST_FILES.json.
11. D4 1h vs D4 1m(H+59) internal: ETH 100%, BTC 52607/52608 (1 hour differs) - not yet investigated.
## Round 3
12. BTC 1h-vs-1m mismatch explained: Vision 1m has flat zero-volume filler minutes (2023-11-10 15:07-16:45 BTC); 1h file correct. Kept data as published (no repair); documented in DATA_MANIFEST.
