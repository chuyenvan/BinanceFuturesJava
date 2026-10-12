#!/bin/bash
# MASTER 10-12 — BUOC 3a CHI JAR [Oracle -> 242, chi ghi file moi .livefix_new, KHONG dung/doi gi dang chay].
# Buffer gate KHONG thay (buffer dung lai FAIL d2_pass: first_ts / s2 chua arm / s1 match 0,95; q_ratio p50 = 1,0).
source /home/ubuntu/claude_master/1011/livefix/deploy/dep_env.sh
set -e
V=/home/chuyennd/java/v_t_m; C=/home/chuyennd/java/collectData
[ "$(sha256sum < $JAR | cut -c1-64)" = "$JAR_SHA" ] || { echo "jar local sai sha"; exit 2; }
$SCP242 $JAR root@103.157.218.242:$V/target/binance-java-sdk-1.2.4.jar.livefix_new
$SCP242 $JAR root@103.157.218.242:$C/target/binance-java-sdk-1.2.4.jar.livefix_new
$S242 "sha256sum $V/target/binance-java-sdk-1.2.4.jar.livefix_new $C/target/binance-java-sdk-1.2.4.jar.livefix_new" | tee $LOGD/d3j_stage_sha.txt
n=$(grep -c "^$JAR_SHA " $LOGD/d3j_stage_sha.txt)
[ "$n" = 2 ] && echo "== STAGE OK (jar x2)" || { echo "== STAGE SAI SHA"; exit 3; }
