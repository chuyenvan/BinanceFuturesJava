# SCOPING_OPT_1128 - crypto options data, free sources, measured from Oracle 2026-11-28
All calls from may Oracle, no key. Scripts q1*.py..q5b.py in this dir.
## Deribit (all HTTP 200 unless noted)
- DVOL get_volatility_index_data: BTC,ETH daily+hourly from 2021-03-24 00:00. SOL only 2022-05-04..2022-11-25 (206 days, discontinued). USDC 70 rows 2025-03-26..2026-04-29 (junk, 300.0). XRP/BNB/DOGE/MATIC/PAXG: 0 rows.
  res 1 (1s): retention ~30-60d; res 60: ~120-200d; 3600/43200/1D: full. Max 1000 bars/call, continuation = older end_ts (pages backward).
  Hourly BTC+ETH 2021-03-24..2025-12-31 ~ 2 x 41.8k bars = ~84 calls, ~2 min, <5 MB.
  BTC first 3 1D: [1616544000000,84.8,95.94,80.52,95.04],[..,95.03,97.43,87.25,89.74],[..,89.74,89.74,80.22,84.52]
  BTC 2023-06-30 1h: [1688083200000,43.52,43.52,43.3,43.34],[..,43.34,43.37,42.92,42.99],[..,42.99,43.72,42.98,43.62]
- Option trades history.deribit.com get_last_trades_by_currency_and_time: works back to 2016-11-29 (BTC first trade BTC-31MAR17-700-P), ETH 2019-03-21, USDC-settled (SOL/XRP/AVAX/TRX/HYPE/BTC/ETH linear) 2024-03-11. www host returns 0 for old windows.
  Fields: trade_seq,trade_id,timestamp,tick_direction,price,mark_price,iv,instrument_name,index_price,direction,amount; optional contracts,block_trade_id,block_trade_leg_count,combo_id,combo_trade_id,liquidation,block_rfq_id. Sample: sample_trades_btc_2021.json
  Trades/day (2 sampled hours x12, ESTIMATE): 2021-06-16 BTC 5.4k ETH 3.1k; 2023-06-14 BTC 3.0k ETH 4.5k; 2024-06-12 BTC 22.6k ETH 10.4k; 2025-06-11 BTC 17.4k ETH 15.6k; 2022-06-15 >=36k/day BTC+ETH (10h, capped pages).
  Total 2021-2025 BTC+ETH ~25-45M trades; >=25-45k calls (1000/call, has_more + restart from last ts, dedupe trade_id); 20 calls @0.2s = all 200 (no 429). Pull ~3-12h. JSON ~246 B/trade; parquet est ~1.5-3 GB.
- NOT historical: get_mark_price_history expired -> 400 "instrument is not active"; live instrument returned n=0 for all windows tried. get_book_summary_by_instrument expired -> 400. get_order_book expired -> only closed state, no book. get_tradingview_chart_data expired option -> 200 OHLCV (trade-based candles, 1h ok). get_instruments expired=true: www only ~recent (46); history host 126,560 BTC options since 2016-07 (85 MB JSON!). get_delivery_prices btc_usd 2683 days since 2016-03-18.
- Snapshot get_book_summary_by_currency kind=option: BTC 954 instr (517 KB raw/43 KB gz), ETH 754 (405/33 KB), USDC 2836 (1.78 MB/141 KB). Fields: ask_price,bid_price,mid_price,mark_price,mark_iv,open_interest,volume(+usd),underlying_price,underlying_index,interest_rate,last,high,low,price_change,estimated_delivery_price,creation_timestamp. Hourly 1y all three ~1.9 GB gz JSON (less in parquet). Masked sample: masked_book_summary_2lines.json
- get_currencies: 52 currencies; options only under BTC, ETH, USDC (USDC bases: AVAX,BTC,ETH,HYPE,SOL,TRX,XRP).
## Binance
- data.binance.vision data/option/daily only (no monthly): BVOLIndex BTCBVOLUSDT,ETHBVOLUSDT 2023-06-20..2025-02-18 (1s, 86400 rows/day, ~265 MB each). EOHSummary (hourly per-contract: bid/ask, best_buy/sell_iv, mark_iv, greeks, openinterest) BTC,ETH 2023-05-18..2023-10-23 (147 files), BNB 121, XRP 99, DOGE 31 files, same window. Samples sample_binance_*.csv
- eapi exchangeInfo HTTP 200 from Oracle: BTC 640, ETH 576, BNB 150, SOL 92, XRP 48, DOGE 34, XAU 24, XAG 28. klines expired -> 400 -1121; trades expired 400; historicalTrades 404; exerciseHistory returns only recent (endTime 2023/2022 -> []).
## Others
- Tardis free day-1-of-month: GET 302->wasabi, 206 ok; 2019-04-01 275 MB, 2021-03-01 1.2 GB, 2024-01-01 1.87 GB, 2025-12-01 9.07 GB gz; day 2 -> 401. options_chain = tick chain with open_interest,bid/ask px+amount+iv,mark_iv,underlying,greeks. ~80 days total, ~150-250 GB download, must stream+downsample (disk 17 GB).
- OKX opt-summary BTC-USD: 200, 1440 instr, fields markVol,bidVol,askVol,greeks,fwdPx (no OI). Option underlyings: BTC,ETH,SOL,XAU,HYPE. OKX historical files not checked.
- Bybit public.bybit.com: no option folder (/option/ 404). API live options: BTC 750(page),ETH 610,SOL 320,XRP 252,DOGE 224,MNT 264, BNB 0.
