#!/bin/bash
# LUOT7 EB25: Add24PriceDue (ham jar stub DcaUtils.shouldDcaGrid, env DEV2W, bwrap). usage: run_pricedue.sh lo_ms hi_ms out.csv [cums.csv] [closes.csv.gz]
set -u
B=$HOME/claude_master/w3/add24/b; S=/dev/shm/add24/b; DW=$S/out_dev2/DEV2W; JAR=/dev/shm/add24/jar/binance-java-sdk-1.2.4.jar_add24_stub_01cfbb43
M=$(md5sum < "$JAR" | cut -d' ' -f1); [ "$M" = cf0f479241265de68836716ee66a1866 ] || exit 3
C=${4:-$B/l6_inputs/cums.csv}; K=${5:-$S/l5/closes.csv.gz}
mkdir -p $S/l7/wd; cp $HOME/claude_master/w3/add24_wt/tools/e2e/config_replay.properties $S/l7/wd/config.properties
env -i HOME="$HOME" PATH=/usr/bin:/bin LANG=C.UTF-8 bwrap --unshare-net --ro-bind / / --dev /dev --proc /proc --tmpfs /tmp --ro-bind /dev/shm/add24/jar /dev/shm/add24/jar --bind /dev/shm/add24/b /dev/shm/add24/b \
  bash -c "set -a; . '$DW/env_used.sh'; set +a; export LIVE_IS_SHADOW_HOST=true; cd $S/l7/wd; exec java -Xmx2g -cp '$JAR:$B/classes' com.binance.chuyennd.c3live.e2e.replay.Add24PriceDue $C $K $1 $2 $3" 2>&1 | grep 'ADD24PRICEDUE\|Exception'
