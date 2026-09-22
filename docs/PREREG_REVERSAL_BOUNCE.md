# PREREG — Reversal-Bounce Long (rank-layer edge, 0-sim)

Status: PRE-REGISTERED SPEC. Measurement BLOCKED (1m dataset unreachable — see §7).
Timestamp (UTC): 2026-09-22T05:09:52Z
Agent: executor (Opus 4.8). Design owner: MASTER. Decision owner: Uni.
Scope guard: rank-layer only (forward-return), NO sim engine, NO Java build, SIM_END<=20251231, HOLDOUT 2026 untouched, no shadow-c3/box242 touch, no git push/checkout.

## 1. Mechanism (generalized isBtcTrendReverse -> cross-section)
Source of truth: MarketBigChangeDetector.isBtcTrendReverse(), commit 157cf4d,
src/main/java/com/binance/chuyennd/tradecore/MarketBigChangeDetector.java:197.
Helper: Utils.rateOf2Double(a,b)=(a-b)/b ; getCurrentMinute(t)%15 (GMT+7, but %15 tz-invariant).
Data unit: rolling window of BTC_TREND_REVERSE_DURATION=360 one-minute klines, evaluated
causally on the LAST (closed) candle of each rolling window (advance 1 candle/step).

Per-window algorithm (verbatim from code):
- rateTrend starts at RATE_MAX=0.01, decremented by 0.0005 each outer pass until
  rateTrend < RATE_MIN_TRADE-0.00005 (=0.00595); i.e. tries {0.010,0.0095,...,0.006}.
- For a given rateTrend, scan candles from most-recent (i=0) backward; consider ONLY anchors
  with (index>=i+29) AND (minute%15==14) (last minute of a 15m bucket).
  * ticker  = candle at index-i     (anchor, 15m close)
  * t15m    = candle at index-i-14  (open candle of anchor's own 15m bucket)
  * t30m    = candle at index-i-29  (open candle of the prior 15m bucket)
  * rate = min( (close-t30m.high)/t30m.high , (close-t15m.high)/t15m.high )
  * if rate < -rateTrend  -> priceReverse = t15m.OPEN ; indexMin=i ; break (take MOST RECENT).
  Take the LARGEST rateTrend that yields any anchor.
- FIRE LONG iff:
  (a) lastCandle.close > priceReverse                         (bounced back above reversal open)
  (b) for i in 1..indexMin-1: no candle already closed >= priceReverse (current bar is FIRST reclaim)
- signal strength returned = rateTrend (>=0.006 always, so all fires are tradable).

Plain: coin dropped ~0.6-1.0% below its recent 15m/30m per-minute highs (measured at a 15m close),
then long the FIRST 1m bar that reclaims the open of that dropping 15m candle.

## 2. Locked parameters (production era ~2025-10, commit 157cf4d config.properties). NOT tuned.
- BTC_TREND_REVERSE_RATE_MAX       = 0.01
- BTC_TREND_REVERSE_RATE_MIN       = 0.006
- BTC_TREND_REVERSE_RATE_MIN_TRADE = 0.006
- BTC_TREND_REVERSE_DURATION       = 360 (minutes / rolling window length)
- anchor cadence minute%15==14 ; history req >=29 bars ; rateTrend step 0.0005.
ONLY generalization vs production: universe specialSymbol(BTC) -> cross-section every coin.
No other parameter changed; no post-hoc sweep.

## 3. Universe (truthful, incl. dead coins)
- Source: Aerospike kline_1m_opt (863 symbols, 1m) OR leak-free WFO 1m export.
- MUST include DELISTED/dead symbols via SymbolLifecycleManager (survivorship-free; forced-seller lesson).
- No large-cap cherry-pick. Dead-coin share matters: daily universe_meta.csv = 663 USDT (472 TRADING + 191 BREAK ~= 29% dead).
- Dedup: one signal per coin per non-overlapping episode (suppress re-fire while a fired priceReverse
  level stays reclaimed; natural re-arm only after a NEW deeper anchor forms).

## 4. Forward-return / HOLD
- HOLD = fixed 24h from entry minute (comparable to forced-seller convention). Long-only.
- Entry realistic: production used priceClose reclaim -> model entry = fill at signal-bar close
  (market) OR next-bar open; record both, headline = signal-bar close + taker.

## 5. Cost model (real, not optimistic)
- Fees: taker in + taker out (Binance USDT-M taker 0.05% each leg). If limit-entry variant, maker in.
- Slippage = HALF the true 1m-candle range at entry (small caps ~0.45% breakeven regime).
- Funding: real funding over the 24h hold (sum of 8h funding stamps crossed).
- Report expectancy net of ALL of the above.

## 6. Metrics + GO/NO-GO (locked BEFORE seeing numbers)
Report: expectancy/trade OOS after cost; t-stat + CI via block-bootstrap (episode blocks);
% coins with positive mean; decay by year 2021->2025; win-rate.
Independence vs MOM15/T170: entry-day overlap % with printDone (OLD_PRINTDONE.csv), ICC-by-episode,
share of signals landing on MOM15-IM days (T170 not trading).
- GO: expectancy>0 after real cost AND CI excludes 0 AND %coin+ >50% stable AND no decay-to-negative
  in 2024-2025 AND genuinely independent of MOM15 (low entry-day overlap / mostly on MOM15-quiet days
  / ICC drops clearly). -> propose parallel sim-admission alongside MOM15.
- NO-GO: expectancy<=0 after cost, OR CI contains 0, OR decay-to-negative 2024-25, OR survivorship
  (edge vanishes when dead coins added), OR not independent (clusters with MOM15). -> close reversal-bounce,
  log power_wall (free-data + old-code independent signal sources exhausted).

## 7. Data-access blocker (why measurement not yet run)
- Oracle SSH ubuntu@161.118.212.3:22 UNREACHABLE from container AND from device VM (network unreachable,
  no key present) — matches recent agent failures.
- Dev machine (E:\...\BinanceFuturesJava) has only DAILY universe (_wfotmp/alld, 571 csv), BTC/ETH
  coarse intraday (_wfotmp/tf 15m/1h/4h), and LUNA 1m (luna_csv). NO universe-wide 1m/15m raw OHLC.
- Required 1m raw OHLC lives ONLY in Oracle Aerospike (863 sym) / Oracle exports (/home/ubuntu/claudedata/wfo1m,
  /home/ubuntu/tool1_1m_unf). 15m bars provably CANNOT reproduce the trigger (needs per-minute high/open
  of specific minutes at 15m anchors). Fresh full-universe 1m spot pull is infeasible in-session and would
  reintroduce survivorship (delisted futures gone from public API) -> not run per MASTER "dung guong".
- Measurement will run unchanged (params above) once Oracle 1m is reachable.

## 8. Forecast (pre-registered prior)
Expect small raw bounce edge pre-cost that likely does NOT survive small-cap slippage (~0.45%),
and expect HIGH MOM15 co-clustering (MOM15 printDone <=2025 = 1933 entries on only 72 distinct days;
reversal-bounce also fires on selloff bounces). Prior: NO-GO on independence and/or cost. Stated to avoid hindsight.
