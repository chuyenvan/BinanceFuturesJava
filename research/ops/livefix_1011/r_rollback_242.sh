# ROLLBACK 242 [GHI]: dung 2 app -> jar .bak_livefix_<TS> (sha b0f23b7d) + buffer .bak_livefix_<TS> -> start.
# Mapper: MAC DINH GIU ban da sua (jar cu b0f23b7d chay dung voi id duy nhat: counter=max=949, khong fail-fast).
# Chi khi MASTER muon tra NGUYEN trang mapper: run242.sh r_rollback_242.sh "MAPPER_RESTORE=YES"
#   => tool restore (jar moi .livefix_new) tu /root/mapper_backup_livefix_<TS>.json (8 id trung QUAY LAI; jar cu khong fail-fast).
V=/home/chuyennd/java/v_t_m; C=/home/chuyennd/java/collectData
TS=$(cat /root/livefix_1011.ts) || { echo "thieu TS"; exit 2; }
echo "ROLLBACK_BEGIN $(date '+%F %T') TS=$TS MAPPER_RESTORE=${MAPPER_RESTORE:-NO}"
systemctl stop h242-trading & systemctl stop h242-ingest & wait
for i in $(seq 1 45); do
  nT=$(pgrep -fc 'com.binance.chuyennd.trading.BinanceOrderTradingManager'); nI=$(pgrep -fc 'com.binance.chuyennd.websocket.BinanceDataIngestor')
  [ "$nT" = 0 ] && [ "$nI" = 0 ] && break; sleep 2
done
[ "$nT" = 0 ] && [ "$nI" = 0 ] || { echo "ABORT van con JVM"; exit 3; }
for A in $V $C; do
  J=$A/target/binance-java-sdk-1.2.4.jar
  if [ -e $J.bak_livefix_$TS ]; then cp -p $J.bak_livefix_$TS $J; fi
  echo "$A jar=$(sha256sum < $J | cut -c1-16)"
done
B=$V/run/gate_ratio_live.bin; [ -e $B.bak_livefix_$TS ] && cp -p $B.bak_livefix_$TS $B && echo "buffer <- bak_livefix_$TS"
if [ "${MAPPER_RESTORE:-NO}" = YES ]; then
  cd $V && MAPPER_REPAIR_CONFIRM=YES java -Xmx512m -cp $V/target/binance-java-sdk-1.2.4.jar.livefix_new \
    com.binance.chuyennd.aerospike.tools.SymbolMapperRepairTool restore /root/mapper_backup_livefix_$TS.json /root/mapper_prerestore_livefix_$TS.json \
    > /root/livefix_mapper_${TS}_restore.log 2>&1; echo "restore rc=$?"
  grep -a 'MAPPER-RESTORE\|Exception' /root/livefix_mapper_${TS}_restore.log | cut -c1-300
fi
echo "$(wc -l < $V/logs/full.log) $(wc -l < $C/logs/full.log)" > /root/livefix_1011.loglines
systemctl start h242-ingest; sleep 3; systemctl start h242-trading; sleep 8
echo "ROLLBACK_DONE $(date '+%F %T') units=$(systemctl is-active h242-trading)/$(systemctl is-active h242-ingest)"
echo "Kiem: grep 'SimpleSymbolMapper initialized' logs/full.log | tail -1 (jar cu: Total 933, Next ID 950 neu giu mapper sua; 934 neu restore)"
