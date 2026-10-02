#!/bin/bash
# READ-ONLY: cmdline day du cua JVM trading + ingestor (kiem -Xmx sau auto-restart)
for p in $(pgrep -f 'BinanceOrderTradingManager|BinanceDataIngestor'); do
  echo "PID $p: $(tr '\0' ' ' < /proc/$p/cmdline | cut -c1-400)"
  grep -E 'VmRSS|VmHWM' /proc/$p/status
done
grep -a -E 'restart|Restart' /home/chuyennd/java/v_t_m/logs/full.log | grep -a '^02/10/2026' | tail -4 | cut -c1-200
