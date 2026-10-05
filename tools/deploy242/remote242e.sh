#!/bin/bash
# READ-ONLY: pidfile vs PID that; TZ he thong; daemon.sh stop dung pidfile nao
cd /home/chuyennd/java/v_t_m || exit 1
echo "pidfile=$(cat run/com.binance.chuyennd.trading.BinanceOrderTradingManager.pid) real=$(pgrep -f BinanceOrderTradingManager | tr '\n' ' ')"
date +%Z; cat /etc/timezone 2>/dev/null; ls -la /etc/localtime | cut -c1-120
grep -n -E 'pid|kill' bin/daemon.sh | head -15 | cut -c1-160
