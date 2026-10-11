# BUOC 4 [242, GHI symbol_mapper] SymbolMapperRepairTool check -> plan -> apply (backup JSON) -> check. CHI khi 2 app DA DUNG.
# Chay tu thu muc v_t_m (config.properties = Aerospike 242 nhu live; khong LIVE_IS_SHADOW_HOST => Live242WriteGuard cho ghi).
# Rollback: r_rollback_242.sh voi MAPPER_RESTORE=YES (tool restore tu /root/mapper_backup_livefix_<TS>.json).
V=/home/chuyennd/java/v_t_m; cd $V || exit 1
TS=$(cat /root/livefix_1011.ts) || { echo "ABORT thieu TS (chay w1 truoc)"; exit 2; }
J=$V/target/binance-java-sdk-1.2.4.jar.livefix_new
T="java -Xmx512m -cp $J com.binance.chuyennd.aerospike.tools.SymbolMapperRepairTool"
nT=$(pgrep -fc 'com.binance.chuyennd.trading.BinanceOrderTradingManager'); nI=$(pgrep -fc 'com.binance.chuyennd.websocket.BinanceDataIngestor')
[ "$nT" = 0 ] && [ "$nI" = 0 ] || { echo "ABORT app 242 van chay (JVM cu giu counter=933 se cap id trung)"; exit 2; }
P=/root/livefix_mapper_$TS; BK=/root/mapper_backup_livefix_$TS.json
$T check > ${P}_check0.log 2>&1; RC=$?
grep -a 'MAPPER-CHECK' ${P}_check0.log | cut -c1-500
if [ $RC = 0 ]; then echo "mapper DA sach id trung — bo qua apply"; echo "== W2 OK (skip)"; exit 0; fi
[ $RC = 3 ] || { echo "ABORT check rc=$RC (xem ${P}_check0.log)"; exit 3; }
$T plan > ${P}_plan.log 2>&1; grep -a 'MAPPER-PLAN' ${P}_plan.log | cut -c1-700
grep -q 'MAPPER-PLAN\] 16 symbol' ${P}_plan.log || { echo "ABORT plan khong phai 16 symbol — MASTER xem lai truoc khi apply"; exit 4; }
[ -e $BK ] && { echo "ABORT backup da ton tai $BK"; exit 4; }
MAPPER_REPAIR_CONFIRM=YES $T apply $BK > ${P}_apply.log 2>&1; RA=$?
grep -a 'backup\|MAPPER-REPAIR\|Exception' ${P}_apply.log | cut -c1-300
[ $RA = 0 ] && grep -q 'MAPPER-REPAIR\] OK' ${P}_apply.log || { echo "ABORT apply rc=$RA (CAS xung dot / loi) — mapper KHONG doi neu khong co dong OK"; exit 5; }
ls -la $BK
$T check > ${P}_check1.log 2>&1; RC1=$?
grep -a 'MAPPER-CHECK' ${P}_check1.log | cut -c1-300
[ $RC1 = 0 ] || { echo "ABORT check sau apply rc=$RC1"; exit 6; }
echo "== W2 OK (mapper sach, backup $BK)"
