#!/bin/bash
set -u
JAR=/dev/shm/add24/jar/binance-java-sdk-1.2.4.jar_add24_stub_01cfbb43
M=$(md5sum < "$JAR" | cut -d' ' -f1); [ "$M" = cf0f479241265de68836716ee66a1866 ] || exit 3
CP="$JAR:$HOME/claude_master/w3/add24/b/classes"
OUT=/dev/shm/add24/b/tierprobe; mkdir -p $OUT; cd $OUT
env -i HOME="$HOME" PATH=/usr/bin:/bin LANG=C.UTF-8 bwrap --unshare-net --die-with-parent --ro-bind / / --dev /dev --proc /proc --tmpfs /tmp \
  --ro-bind /dev/shm/add24/jar /dev/shm/add24/jar --bind /dev/shm/add24/b /dev/shm/add24/b \
  bash -c "export LIVE_IS_SHADOW_HOST=true; exec java -Xmx3g -cp '$CP' com.binance.chuyennd.c3live.e2e.replay.Add24TierProbe /dev/shm/add24/b/tk26 FIGHTUSDT,SPACEUSDT $1" > $OUT/tier.txt 2> $OUT/tier.err
echo rc=$?
