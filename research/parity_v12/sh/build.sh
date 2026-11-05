#!/bin/bash
# Build harness OFFLINE PARITY_V12_DRY §1 (OFF-BT-A1/OFF-NEW2-A1) tren class cua JAR DRY DANG CHAY (r4n fb6711ef). Khong doc/ghi 242.
set -e
export LIVE_IS_SHADOW_HOST=true
J=${JAR:-$HOME/claude_master/v12/jar/binance-java-sdk-1.2.4.jar_v12_r4n}
JMD5=${JAR_MD5:-fb6711efe473e0e0a5b0ca9813c62af3}
R=$HOME/claude_master/vz_e1_wt/research/parity_v12
B=${B:-$HOME/claude_master/parity_v12w/build}   # [ADD11] build_<jar> cho jar khac r4n
echo "$JMD5  $J" | md5sum -c -
python3 $R/py/patch_harness.py $HOME/claude_master/v11_settle/harness/src $R/java
rm -rf $B && mkdir -p $B/cls $B/stubcls
javac -nowarn -encoding UTF-8 -cp $J -d $B/stubcls $R/stub/com/aerospike/client/AerospikeClient.java
javac -nowarn -encoding UTF-8 -cp $J -d $B/cls $R/java/com/binance/chuyennd/aerospike/*.java 2>&1 | grep -v 'Unsafe\|^Note\|warning' || true
ls $B/cls/com/binance/chuyennd/aerospike/ $B/stubcls/com/aerospike/client/
echo "CP_OFF=$B/stubcls:$B/cls:$J" > $B/cp.env
echo "CP_NOSTUB=$B/cls:$J" >> $B/cp.env
echo "JAR_MD5=$JMD5" >> $B/cp.env
echo BUILD_OK
