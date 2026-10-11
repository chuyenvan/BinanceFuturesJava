# BUOC 6a [242, GHI] start ingest roi trading; ghi so dong log truoc start (w5 chi doc phan moi). Rollback: r_rollback_242.sh.
V=/home/chuyennd/java/v_t_m; C=/home/chuyennd/java/collectData
echo "$(wc -l < $V/logs/full.log) $(wc -l < $C/logs/full.log)" > /root/livefix_1011.loglines
systemctl start h242-ingest; sleep 3; systemctl start h242-trading
sleep 8
echo "START $(date '+%F %T') units=$(systemctl is-active h242-trading)/$(systemctl is-active h242-ingest)"
nT=$(pgrep -fc 'com.binance.chuyennd.trading.BinanceOrderTradingManager'); nI=$(pgrep -fc 'com.binance.chuyennd.websocket.BinanceDataIngestor')
S=$(cat /root/livefix_1011.stop_epoch 2>/dev/null || echo 0); echo "trading_procs=$nT ingest_procs=$nI downtime~$(( $(date +%s) - S ))s"
[ "$nT" -ge 1 ] && [ "$nI" -ge 1 ] && echo "== W4 OK (doi 3-5 phut roi chay w5_verify_242.sh)" || { echo "== W4 FAIL — xem logs/full.log, can nhac rollback"; exit 3; }
