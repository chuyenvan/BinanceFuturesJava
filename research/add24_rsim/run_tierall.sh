#!/bin/bash
set -u
B=$HOME/claude_master/w3/add24/b; S=/dev/shm/add24/b; DAYS=$(cat $S/l5/days.txt)
JAR=/dev/shm/add24/jar/binance-java-sdk-1.2.4.jar_add24_stub_01cfbb43
M=$(md5sum < "$JAR" | cut -d' ' -f1); [ "$M" = cf0f479241265de68836716ee66a1866 ] || exit 3
CP="$JAR:$B/classes"
cd /tmp && /home/ubuntu/xgb-env/bin/python3 $B/kg_tk_stream.py $S/l5/tk $DAYS > $B/kg_stream.log 2>&1 &
env -i HOME="$HOME" PATH=/usr/bin:/bin LANG=C.UTF-8 bwrap --unshare-net --ro-bind / / --dev /dev --proc /proc --tmpfs /tmp \
  --ro-bind /dev/shm/add24/jar /dev/shm/add24/jar --bind /dev/shm/add24/b /dev/shm/add24/b \
  bash -c "export LIVE_IS_SHADOW_HOST=true; exec nice -n 10 java -Xmx1500m -cp '$CP' com.binance.chuyennd.c3live.e2e.replay.Add24TierAll $S/l5/tk $DAYS $S/l5/watch.csv $S/l5" > $B/tierall.log 2>&1
echo "java rc=$?" >> $B/tierall.log
wait
