# BUOC 3b [242, GHI] dung h242-trading + h242-ingest. Kiem file staged truoc khi dung. Rollback: systemctl start (jar cu chua doi).
V=/home/chuyennd/java/v_t_m; C=/home/chuyennd/java/collectData
SHA=db181d41bd6837752638a63de99a2023cee7ad4b897d6e64924ac3d6c8f21577
for f in $V/target/binance-java-sdk-1.2.4.jar.livefix_new $C/target/binance-java-sdk-1.2.4.jar.livefix_new; do
  [ "$(sha256sum < $f | cut -c1-64)" = "$SHA" ] || { echo "ABORT staged jar sai/thieu $f"; exit 2; }
done
[ -s $V/run/gate_ratio_live.bin.livefix_new ] || { echo "ABORT thieu buffer staged"; exit 2; }
TS=$(date +%Y%m%d_%H%M); echo $TS > /root/livefix_1011.ts; date +%s > /root/livefix_1011.stop_epoch
grep -a 'LEGACY\] managed' $V/logs/full.log | tail -1 | cut -c1-60
echo "STOP_BEGIN $(date '+%F %T') TS=$TS"
systemctl stop h242-trading & systemctl stop h242-ingest & wait
for i in $(seq 1 45); do
  nT=$(pgrep -fc 'com.binance.chuyennd.trading.BinanceOrderTradingManager'); nI=$(pgrep -fc 'com.binance.chuyennd.websocket.BinanceDataIngestor')
  [ "$nT" = 0 ] && [ "$nI" = 0 ] && break; sleep 2
done
echo "STOP_DONE $(date '+%F %T') trading_procs=$nT ingest_procs=$nI units=$(systemctl is-active h242-trading)/$(systemctl is-active h242-ingest)"
[ "$nT" = 0 ] && [ "$nI" = 0 ] || { echo "ABORT van con JVM — KHONG sang buoc 4"; exit 3; }
echo "== W1 OK"
