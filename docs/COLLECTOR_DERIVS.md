# Binance Futures Derivatives Collector

Long-horizon collector of Open Interest, funding rate, long/short ratios and
liquidations from Binance USDT-M Futures **public REST/WS only** (no API key,
no orders). Purpose: accumulate 6-12 months of data to train a collapse model.

Runs on the **Oracle research box** (161.118.212.3, `instance-20260622-1647`).
Does NOT touch the 242 live box.

## Reachability (recon)
Oracle -> Binance fapi, all HTTP 200:
- `/fapi/v1/time` = 200
- `/fapi/v1/openInterest` = 200
- `/futures/data/openInterestHist` = 200
- `/fapi/v1/premiumIndex` = 200
- `/futures/data/globalLongShortAccountRatio` = 200
- PyPI = 200, `fstream.binance.com` WS host reachable.

## Universe
USDT-M PERPETUAL, status=TRADING via `/fapi/v1/exchangeInfo`: **528 symbols**.

## Endpoints used (public, no key)
| Data | Endpoint | Call shape |
|------|----------|-----------|
| Open Interest | `/fapi/v1/openInterest?symbol=` | per-symbol, instantaneous (contracts) |
| Funding + mark/index | `/fapi/v1/premiumIndex` | 1 call, all symbols (lastFundingRate) |
| Global L/S acct ratio | `/futures/data/globalLongShortAccountRatio?period=5m&limit=1` | per-symbol |
| Top L/S position ratio | `/futures/data/topLongShortPositionRatio?period=5m&limit=1` | per-symbol |
| Liquidations | `wss://fstream.binance.com/ws/!forceOrder@arr` | realtime stream |

Notional USD is derived at load time = openInterest * markPrice (same cycle).

## Storage layout
`/home/ubuntu/derivs_store/YYYYMMDD/` (UTC date), one CSV per data type:
- `oi.csv`      : cycle_ts,cycle_iso,symbol,openInterest,time
- `funding.csv` : cycle_ts,cycle_iso,symbol,markPrice,indexPrice,lastFundingRate,nextFundingTime
- `lsr_global.csv` : cycle_ts,cycle_iso,symbol,longAccount,shortAccount,longShortRatio,timestamp
- `lsr_top.csv`    : cycle_ts,cycle_iso,symbol,longAccount,shortAccount,longShortRatio,timestamp
- `liquidations.csv` : event_time,symbol,side,order_type,time_in_force,orig_qty,price,avg_price,order_status,last_filled_qty,filled_accum_qty,trade_time

`cycle_ts` = floor(now/300)*300 (unix, 5-min bucket). Idempotent per cycle via
`.last_cycle` marker; `flock` on `/tmp/collect_derivs.lock` prevents overlap.
Days older than today are gzipped automatically (`compress_old`).

## Frequency
- OI / funding / LSR: every 5 min via cron (`*/5 * * * *`).
- Liquidations: continuous WS listener (watchdog `run_liq.sh`, `@reboot` cron).

## Storage estimate (measured)
Per full 5-min cycle uncompressed ~161 KB; gzip ratio ~4.3-5.2x.
- Uncompressed: ~46 MB/day (kept only for the current day).
- Gzipped (older days): ~9 MB/day -> ~1.7 GB / 6 months, ~3.3 GB / 12 months.
- Liquidations: variable, small (a few MB/day even in high-vol).

Disk at setup: 194G total, 22G free (89% used). 12 months of gzipped derivs
(~3.3 GB) fits comfortably. compress_old keeps only 1 uncompressed day.

## Files
- `research/pipeline/collector/collect_derivs.py` - 5-min REST collector.
- `research/pipeline/collector/liq_ws.py` - liquidation WS listener.
- `research/pipeline/collector/run_liq.sh` - watchdog wrapper.

## Cron (Oracle, existing shadow_c3 cron preserved)
```
*/5 * * * * /usr/bin/python3 .../collect_derivs.py >> derivs_store/cron.out 2>&1
@reboot /bin/bash .../run_liq.sh >/dev/null 2>&1
```

## Safety
Public endpoints only, no API key, no orders, no writes to 242 live, no git push.
