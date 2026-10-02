#!/bin/bash
# READ-ONLY probe 242 — chi cat/grep/tail/ls/sha256sum/ps/free. KHONG sua gi.
A=/home/chuyennd/java/v_t_m
cd $A || exit 1
L=logs/full.log
echo "@@DATE"; date '+%F %T %z'
echo "@@JAR"; sha256sum target/binance-java-sdk-1.2.4.jar; ls -la --time-style=long-iso target/ | grep -i jar
echo "@@ENV"; grep -v -i -E "key|secret|passw|token" conf/env.sh | grep -E "^export |^[A-Z_]+="
echo "@@CONF"; grep -v -i -E "key|secret|passw|token" config.properties | grep -E "^[A-Za-z_.]+="
echo "@@PS"; ps -eo pid,etimes,etime,rss,vsz,pcpu,args --sort=-rss | grep -i java | grep -v grep | cut -c1-260
echo "@@FREE"; free -m; uptime; df -h / | tail -1
echo "@@MODELS"; ls -la --time-style=long-iso ../storage/ai_ml_data/ai_models_reg_v3/ 2>&1 | head -30
sha256sum ../storage/ai_ml_data/ai_models_reg_v3/*.onnx 2>&1 | head -20
ls -la --time-style=long-iso ../storage/c3_models/ 2>&1 | head -20
sha256sum ../storage/c3_models/*.onnx 2>&1 | head -10
echo "@@RUN"; ls -la --time-style=long-iso run/ 2>&1 | head -40
grep -vc '^#' run/legacy_symbols.csv
echo "@@LOGS"; ls -la --time-style=long-iso logs/ | head -40
echo "@@LOGFIRST"; head -2 $L | cut -c1-220; echo "@@LOGLAST"; tail -2 $L | cut -c1-220
echo "@@COUNTS"
for p in "OutOfMemoryError" "Exception" " ERROR " "\[GATE\]" "GATE-RATIO" "n_pass=0" "Create order market" "Place order" "New price SL" "Update SL" "TS-GAP" "would-BUY" "SHADOW\] arm" "SHADOW\] closed" "skip-LEGACY" "c3_shadow\] BAT" "OI-LIVE" "PASS-TIMING"; do
  echo "$p => $(grep -ac -- "$p" $L)"; done
echo "@@GATE_TAIL"; grep -a '\[GATE\]' $L | tail -3 | cut -c1-300
echo "@@GATERATIO_TAIL"; grep -a 'GATE-RATIO' $L | tail -6 | cut -c1-300
echo "@@STARTS"; grep -a 'c3_shadow\] BAT' $L | cut -c1-40
echo "@@LEGACY"; grep -a '\[LEGACY\] managed' $L | tail -1 | cut -c1-90
echo "@@OILIVE"; grep -a 'OI-LIVE' $L | tail -5 | cut -c1-250
echo "@@PASSTIMING"; grep -a 'PASS-TIMING' $L | tail -3 | cut -c1-250
echo "@@EXC"; grep -a -E 'Exception|OutOfMemory| ERROR ' $L | cut -c24-150 | sort | uniq -c | sort -rn | head -15
echo "@@FEATDUMP"; find /home/chuyennd/java -maxdepth 4 -name 'feat_dump_*' 2>/dev/null | sort | tail -3; find /home/chuyennd/java -maxdepth 4 -name 'feat_dump_*' 2>/dev/null | wc -l
find /home/chuyennd/java -maxdepth 4 -name 'sel_dump_*' 2>/dev/null | wc -l
du -sch $(find /home/chuyennd/java -maxdepth 4 -name 'feat_dump_*' 2>/dev/null) 2>/dev/null | tail -1
echo "@@END"
