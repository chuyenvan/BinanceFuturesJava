#!/bin/bash
# 3b: chay Add24DcaProbe (ham jar stub) trong bwrap, env = env_used cua luot DEV2W. usage: run_dcaprobe.sh <market> <sim|rig> <sym> <first> <t0> <tEnd>
set -u
D=/dev/shm/add24/b/out_dev2/DEV2W; JAR=/dev/shm/add24/jar/binance-java-sdk-1.2.4.jar_add24_stub_01cfbb43
M=$(md5sum < "$JAR" | cut -d' ' -f1); [ "$M" = cf0f479241265de68836716ee66a1866 ] || exit 3
CP="$JAR:$HOME/claude_master/w3/add24_wt/target/test-classes:$HOME/claude_master/w3/add24/b/classes"
mkdir -p $D/probe_wd; cp $HOME/claude_master/w3/add24_wt/tools/e2e/config_replay.properties $D/probe_wd/config.properties; cd $D/probe_wd
env -i HOME="$HOME" PATH=/usr/bin:/bin LANG=C.UTF-8 bwrap --unshare-net --die-with-parent --ro-bind / / --dev /dev --proc /proc --tmpfs /tmp \
  --bind "$D" "$D" --ro-bind /dev/shm/add24/jar /dev/shm/add24/jar --bind /dev/shm/add24/b /dev/shm/add24/b \
  bash -c "set -a; . '$D/env_used.sh'; set +a; export LIVE_IS_SHADOW_HOST=true; exec java -Xmx512m -cp '$CP' com.binance.chuyennd.c3live.e2e.replay.Add24DcaProbe '$1' '$2' /dev/shm/add24/b/fx_dev2/klines.csv.gz '$3' '$4' '$5' '$6' /dev/shm/add24/b/p15_0130_0207.csv" 2>&1 | grep -v 'INFO\|WARN\|DEBUG' | tail -3
