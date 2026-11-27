# DATA_REPORT_2 - BIS REER (G2) + Kaggle M1 source search (G4)
Generated 2026-11-27 by agent. Code: code/fetch_fx.py (BIS target added), code/check_bis.py, code/check_kaggle_sample.py. Provenance: PROVENANCE.md.

## A. BIS WS_EER (G2)
- File: raw/WS_EER_csv_flat.zip, HTTP 200, 6 642 263 bytes, Last-Modified Wed, 25 Nov 2026 12:13:31 GMT, sha256 d39135ce...79dc (full in PROVENANCE.md). Inner WS_EER_csv_flat.csv 297 MB (read streamed, not extracted).
- Filter for REER monthly: `FREQ:Frequency` code M, `EER_TYPE:Type` code R ("R: Real"), `EER_BASKET:Basket` code N ("N: Narrow (27 economies)") or B ("B: Broad (64 economies)"), `REF_AREA:Reference area` code in US XM JP GB CH CA AU NZ NO SE; value `OBS_VALUE:Observation Value`, month `TIME_PERIOD:Time period or range` (YYYY-MM). Values are codes with labels "CODE: label" - split on first ':'.
- Unit (series header rows): "882: Index, 2020 = 100". CPI-based: the file does not say "CPI"; BIS documentation describes real EER as CPI-deflated (not verified from file - VAN CHUA RO trong file, xac nhan tu tai lieu BIS neu can).
- Narrow: all 10 economies 1964-01..2026-10, 754 obs each, 0 missing. Broad: all 10 from 1994-01..2026-10, 394 obs each, 0 missing. XM narrow before 1999 is a BIS synthetic euro-area series.
- 2026-10 value present in a file dated 2026-11-25 => publication lag < 1 month in this vintage (G2 rule 'REER m-1' feasible). No vintages: history may be revised.
- derived/bis_reer_monthly.csv (cut <= 2026-10; columns area, basket, month, reer). NOTE: G2 prereg says DEV must load only < 2020-01-01.
- Terms (https://data.bis.org/help/legal#terms-of-permitted-use-of-bis-statistics, read 2026-11-27): free reuse if BIS cited as source, no implied endorsement, translations flagged unofficial; commercial use allowed only without extra charge for BIS data; API access may be limited/monitored. No bulk-download restriction stated.

## B. Kaggle M1 candidates (G4) - searches: "forex 1 minute", "EURUSD M1", "fx minute", "histdata", "forex tick", "currency intraday"
| rank | dataset | Kaggle license | pairs / tf | years | size | origin | verdict |
|---|---|---|---|---|---|---|---|
| 1 | almirneto/forex-multi-timeframe | CC0-1.0 | 9 sym incl EURUSD GBPUSD USDJPY AUDUSD; M1..D1 | M15 sample: daily 1971-1998, 15-min 1999-01..2024-12-05; M1 range NOT verified | M1 per pair 634-664 MB (4 pairs ~2.6 GB csv) | MT5 terminal export (cols time,tick_volume,spread,real_volume), broker not named; server clock = NY+7h | BEST; conditional |
| 2 | sheldonrobinson/histdata-forex-{eurusd,gbpusd,usdjpy,audusd} | copyright-authors | tick, per month files | 2000-05.. | 0.7-1 GB each | HistData.com | license not open -> no |
| 3 | jkalamar/eurusd-foreign-exchange-fx-intraday-1minute | unknown | EURUSD M1 bid | 2000.. | 388 MB csv | HistData, EST no DST | EUR only, license unknown -> no |
| 4 | risewolves/eurusd-m1-histdata | other | EURUSD M1 | 2006.. | ~16-20 MB/yr | HistData MT format | EUR only, license 'other' -> no |
| 5 | lornet/fx-1-minute-dataset | unknown | EURUSD (+?) M1 | 2000.. | 68 MB | HistData ASCII | license unknown -> no |
| 6 | lemtreursi/lemgendizedforexuniverse | CC BY-NC 4.0 | 16 sym M1.. | 2019.. only | 5 GB | MT5 API / 'synthetic generator' | no 2005-2018, synthetic -> no |
| 7 | mathurinache/dukascopy-forex-tick-data-20082019 | CC-BY-NC-SA-4.0 | tick | 2008-2019 | 60 GB | Dukascopy | excluded by MASTER (Dukascopy) |
| 8 | ankitjha420/forex-eurusd-1m-data-2015-to-2021 | not inspected | EURUSD | 2015-2021 | 30 MB | ? | coverage too short |

### Sample check (1 file, 46.5 MB): almirneto EURUSD/EURUSD_M15.csv (raw/kaggle_sample/, read-only)
- Format: time (epoch s, = date column, 0 mismatch), open, high, low, close, tick_volume, spread (points), real_volume (0). Bid/ask: MT5 bars are normally BID with spread field - not stated by uploader.
- Bars/day 1999-2024: median 96 (full 15-min coverage); 2017-03 all weekdays 96 except Fridays near US/EU DST mismatch (92).
- Week (2015-19, file clock): opens Mon 00:00, last bar Fri 23:45 (some Fri 22:45); 120 h/week => server clock = New York + 7 h (UTC+2 winter / UTC+3 summer, US DST), the common MT broker convention.
- Level vs FRED DEXUSEU, bar closing 12:00 NY, 20 random days 2010-2019: NY+7 hypothesis median |log diff| 0.0146 %, max 0.20 %, 0/20 > 0.5 %; UTC hypothesis worse (0.11 %), NY-clock worse (0.26 %). => clock + level CONSISTENT.
- Pre-1999 rows are daily (spread 50, 1971 start => broker-filled synthetic history) - not usable intraday; irrelevant for 2005-2019.

## Conclusion
- CO NGUON DAT CO DIEU KIEN: almirneto/forex-multi-timeframe (CC0-1.0 on Kaggle, 4 priority pairs, intraday from 1999, clock+level check passes on M15).
- Open conditions for MASTER: (1) M1 file year range not verified (>50 MB; size ~660 MB/pair is consistent with M1 1999-2024 ~9-10M rows); (2) upstream broker unnamed - CC0 granted by uploader, upstream rights unverified (provenance risk); (3) spread column in points varies by year (broker-specific; not usable as real cost).
- Proposed download (NOT RUN, ~2.6 GB, under 4 GB cap; verify sha + chmod after):
  export PATH=$HOME/.local/bin:$PATH; D=~/claude_master/w3/fx/data/raw/kaggle_m1; mkdir -p $D
  for p in EURUSD GBPUSD USDJPY AUDUSD; do nice -n 15 kaggle datasets download almirneto/forex-multi-timeframe -f $p/${p}_M1.csv -p $D; sleep 5; done
  then sha256sum + chmod a-w, convert 2005-01..2019-12 to parquet in derived/, keep raw.
