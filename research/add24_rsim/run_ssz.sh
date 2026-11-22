#!/bin/bash
# S-SZ: goi ham size cua jar STUB (Add24SszProbe) voi env cua luot rig (env_used.sh). usage: run_ssz.sh <RUN_DIR> <FX_DIR>
set -u
D=$1; FX=$2
JAR=/dev/shm/add24/jar/binance-java-sdk-1.2.4.jar_add24_stub_01cfbb43
M=$(md5sum < "$JAR" | cut -d' ' -f1); [ "$M" = cf0f479241265de68836716ee66a1866 ] || { echo "TU CHOI md5 stub"; exit 3; }
CP="$JAR:$HOME/claude_master/w3/add24_wt/target/test-classes:$HOME/claude_master/w3/add24/b/classes"
mkdir -p "$D/ssz_wd"; cp "$HOME/claude_master/w3/add24_wt/tools/e2e/config_replay.properties" "$D/ssz_wd/config.properties"; cd "$D/ssz_wd"
env -i HOME="$HOME" PATH=/usr/bin:/bin LANG=C.UTF-8 bwrap --unshare-net --die-with-parent --ro-bind / / --dev /dev --proc /proc --tmpfs /tmp \
  --bind "$D" "$D" --ro-bind /dev/shm/add24/jar /dev/shm/add24/jar --bind /dev/shm/add24/b /dev/shm/add24/b \
  bash -c "set -a; . '$D/env_used.sh'; set +a; export LIVE_IS_SHADOW_HOST=true; exec java -Xmx512m -cp '$CP' com.binance.chuyennd.c3live.e2e.replay.Add24SszProbe '$FX/ssz_in.csv' '$D/ssz_jar.csv'" > "$D/ssz.log" 2>&1
echo "RC=$?"
