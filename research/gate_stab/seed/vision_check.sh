#!/bin/bash
# vision_check.sh — ADD3/ADD4: kiem Vision da co monthly 2026-10 (klines + fundingRate) va daily metrics 2026-10-31 chua.
# Exit 0 = san sang chay chuoi Kaggle Q4; 2 = chua.
U=https://data.binance.vision/data/futures/um
ok=1
for p in monthly/fundingRate/BTCUSDT/BTCUSDT-fundingRate-2026-10.zip monthly/fundingRate/ETHUSDT/ETHUSDT-fundingRate-2026-10.zip \
         monthly/klines/BTCUSDT/1m/BTCUSDT-1m-2026-10.zip monthly/klines/SOLUSDT/1m/SOLUSDT-1m-2026-10.zip \
         daily/metrics/BTCUSDT/BTCUSDT-metrics-2026-10-31.zip; do
  c=$(curl -s -o /dev/null -w '%{http_code}' --max-time 30 -I $U/$p); echo "$c $p"; [ "$c" = "200" ] || ok=0
done
[ $ok = 1 ] && { echo "VISION_READY"; exit 0; } || { echo "VISION_NOT_READY"; exit 2; }
