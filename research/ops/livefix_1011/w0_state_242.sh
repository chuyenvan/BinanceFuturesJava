# [242, CHI DOC] trang thai truoc deploy. Khong in config/env bi mat.
V=/home/chuyennd/java/v_t_m; C=/home/chuyennd/java/collectData
echo "date: $(date '+%F %T %z')"
echo "units: trading=$(systemctl is-active h242-trading) ingest=$(systemctl is-active h242-ingest)"
for A in $V $C; do
  echo "$A jar=$(sha256sum < $A/target/binance-java-sdk-1.2.4.jar | cut -c1-16) staged=$( [ -f $A/target/binance-java-sdk-1.2.4.jar.livefix_new ] && sha256sum < $A/target/binance-java-sdk-1.2.4.jar.livefix_new | cut -c1-16 || echo none)"
  grep -a 'Restart: ' $A/logs/full.log | tail -1 | cut -c1-90
done
echo "buffer: $(ls -la $V/run/gate_ratio_live.bin | awk '{print $5, $6, $7, $8}') staged=$(ls $V/run/gate_ratio_live.bin.livefix_new 2>/dev/null || echo none)"
grep -a 'LEGACY\] managed' $V/logs/full.log | tail -1 | cut -c1-80
echo "java procs (main class):"; ps -eo pid,args | grep '[j]ava' | grep -o 'com\.binance\.[A-Za-z0-9_.]*' | sort | uniq -c
ls /root/mapper_backup_livefix_* /root/livefix_1011.ts 2>/dev/null
df -h / | tail -1
