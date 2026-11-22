#!/bin/bash
# LUOT5 1c: Add24DcaAll (ham jar stub) trong bwrap --unshare-net, env = env_used DEV2W (nhu run_dcaprobe.sh).
set -u
D=/dev/shm/add24/b/out_dev2/DEV2W; JAR=/dev/shm/add24/jar/binance-java-sdk-1.2.4.jar_add24_stub_01cfbb43; S=/dev/shm/add24/b/l5
M=$(md5sum < "$JAR" | cut -d' ' -f1); [ "$M" = cf0f479241265de68836716ee66a1866 ] || exit 3
CP="$JAR:$HOME/claude_master/w3/add24/b/classes"
mkdir -p $S/dcaall_wd; cp $HOME/claude_master/w3/add24_wt/tools/e2e/config_replay.properties $S/dcaall_wd/config.properties; cd $S/dcaall_wd
env -i HOME="$HOME" PATH=/usr/bin:/bin LANG=C.UTF-8 bwrap --unshare-net --ro-bind / / --dev /dev --proc /proc --tmpfs /tmp \
  --ro-bind "$D" "$D" --ro-bind /dev/shm/add24/jar /dev/shm/add24/jar --bind /dev/shm/add24/b /dev/shm/add24/b \
  bash -c "set -a; . '$D/env_used.sh'; set +a; export LIVE_IS_SHADOW_HOST=true; exec java -Xmx2g -cp '$CP' com.binance.chuyennd.c3live.e2e.replay.Add24DcaAll $S/cums.csv $S/market.csv $S/closes.csv.gz $S/p15.csv $S/dca_all.csv" 2>&1 | grep -v 'INFO\|WARN\|DEBUG' | tail -3
