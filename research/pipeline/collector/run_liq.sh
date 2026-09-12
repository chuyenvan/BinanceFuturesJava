#!/bin/bash
# Watchdog wrapper: keep liq_ws.py alive
DEST=/home/ubuntu/src/BinanceFuturesJava/research/pipeline/collector
while true; do
  /usr/bin/python3 "$DEST/liq_ws.py" >> /home/ubuntu/derivs_store/liq_wrap.out 2>&1
  sleep 5
done
