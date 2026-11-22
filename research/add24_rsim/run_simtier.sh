#!/bin/bash
# LUOT6 1a: Add24SimTierCode - tier LUOI sim bang code a8690d46 (simcls/ truoc jar stub) tai 2 moc cap nhat 2026 cua sim. bwrap --unshare-net.
set -u
B=$HOME/claude_master/w3/add24/b; S=/dev/shm/add24/b
JAR=/dev/shm/add24/jar/binance-java-sdk-1.2.4.jar_add24_stub_01cfbb43
M=$(md5sum < "$JAR" | cut -d' ' -f1); [ "$M" = cf0f479241265de68836716ee66a1866 ] || exit 3
CP="$B/simcls:$JAR:$B/classes"
F="$S/tk_l6/ticker_20260118.bin.gz,$S/tk_l6/ticker_20260119.bin.gz"
for d in 23 24 25 26 27 28 29 30 31; do F="$F,$S/tk26/ticker_202601$d.bin.gz"; done
for d in 01 02 03 04 05; do F="$F,$S/tk26/ticker_202602$d.bin.gz"; done
mkdir -p $S/l6
env -i HOME="$HOME" PATH=/usr/bin:/bin LANG=C.UTF-8 bwrap --unshare-net --ro-bind / / --dev /dev --proc /proc --tmpfs /tmp \
  --ro-bind /dev/shm/add24/jar /dev/shm/add24/jar --bind /dev/shm/add24/b /dev/shm/add24/b \
  bash -c "export LIVE_IS_SHADOW_HOST=true; exec java -Xmx2g -cp '$CP' com.binance.chuyennd.c3live.e2e.replay.Add24SimTierCode $HOME/claude_master/w3/ho5/mapper/ov_idtostr.tsv '$F' 1768780800000,1770325200000 $S/l6/simtier_code.csv" 2>&1 | grep -v ' INFO \| DEBUG ' | tail -25
