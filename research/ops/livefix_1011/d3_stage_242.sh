#!/bin/bash
# BUOC 3a [Oracle -> 242, chi GHI FILE MOI hau to .livefix_new — KHONG dung/doi gi dang chay]
# Chep jar moi (trading + collectData) + buffer live_new.bin; kiem sha tren 242. Rollback: xoa *.livefix_new.
source /home/ubuntu/claude_master/1011/livefix/deploy/dep_env.sh
set -e
V=/home/chuyennd/java/v_t_m; C=/home/chuyennd/java/collectData
[ "$(sha256sum < $JAR | cut -c1-64)" = "$JAR_SHA" ] || { echo "jar local sai sha"; exit 2; }
python3 $DEP/d2_pass.py $G/live_new.json $G/s1_new.json $G/s2_new.json >/dev/null || { echo "buoc 2 chua PASS"; exit 2; }
BSHA=$(sha256sum < $G/live_new.bin | cut -c1-64)
$SCP242 $JAR root@103.157.218.242:$V/target/binance-java-sdk-1.2.4.jar.livefix_new
$SCP242 $JAR root@103.157.218.242:$C/target/binance-java-sdk-1.2.4.jar.livefix_new
$SCP242 $G/live_new.bin root@103.157.218.242:$V/run/gate_ratio_live.bin.livefix_new
$S242 "sha256sum $V/target/binance-java-sdk-1.2.4.jar.livefix_new $C/target/binance-java-sdk-1.2.4.jar.livefix_new $V/run/gate_ratio_live.bin.livefix_new" | tee $LOGD/d3_stage_sha.txt
n=$(grep -c "^$JAR_SHA " $LOGD/d3_stage_sha.txt); m=$(grep -c "^$BSHA " $LOGD/d3_stage_sha.txt)
[ "$n" = 2 ] && [ "$m" = 1 ] && echo "== STAGE OK (jar x2 + buffer)" || { echo "== STAGE SAI SHA"; exit 3; }
