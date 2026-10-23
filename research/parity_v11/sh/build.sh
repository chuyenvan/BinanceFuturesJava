#!/bin/bash
# Build harness OFFLINE (PREREG_PARITY_V11_WINDOW §1) tren class cua jar v11c eea5adec. Khong doc/ghi 242.
set -e
J=${JAR:-$HOME/claude_master/v11_tsx/jar/binance-java-sdk-1.2.4.jar_v11c_eea5adec}
R=$HOME/claude_master/vz_e1_wt/research/parity_v11
B=$HOME/claude_master/parity_v11w/build
echo "eea5adecaff93d3fc350e4d13b3ecb2a  $J" | md5sum -c -
python3 $R/py/patch_harness.py $HOME/claude_master/v11_settle/harness/src $R/java
rm -rf $B && mkdir -p $B/cls $B/stubcls
javac -nowarn -encoding UTF-8 -cp $J -d $B/stubcls $R/stub/com/aerospike/client/AerospikeClient.java
javac -nowarn -encoding UTF-8 -cp $J -d $B/cls $R/java/com/binance/chuyennd/aerospike/*.java 2>&1 | grep -v 'Unsafe\|^Note\|warning' || true
ls $B/cls/com/binance/chuyennd/aerospike/ $B/stubcls/com/aerospike/client/
echo "CP_OFF=$B/stubcls:$B/cls:$J" > $B/cp.env
echo "CP_NOSTUB=$B/cls:$J" >> $B/cp.env
echo BUILD_OK
