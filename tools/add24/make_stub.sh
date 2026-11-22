#!/bin/bash
# ADD24: tao lai jar STUB (tat dinh). 1 lenh: bash tools/add24/make_stub.sh
# - nguon 76134a52 (git archive tu repo, KHONG dung toi worktree c3_hotfix) + PrivateConfig STUB -> mvn -o compile trong /dev/shm (CAM package)
# - make_stub.py: thay 8 entry key, chep nguyen byte nen phan con lai.
set -u
T=$(cd "$(dirname "$0")" && pwd); W=$(cd "$T/../.." && pwd)
A=$HOME/claude_master/w3/add24/a
B=/dev/shm/add24/build/src76
export LIVE_IS_SHADOW_HOST=true MAVEN_OPTS=-Xmx2g
MVN=/home/ubuntu/tools/apache-maven-3.9.9/bin/mvn
mkdir -p $A /dev/shm/add24/jar ~/claude_master/locks; chmod 700 /dev/shm/add24 /dev/shm/add24/jar
DF=$(df -BM --output=avail / | tail -1 | tr -dc 0-9); [ "$DF" -ge 15300 ] || { echo "DUNG: dia $DF MB < 15300"; exit 8; }
if [ "${SKIP_BUILD:-0}" != 1 ]; then
  rm -rf $B; mkdir -p $B
  git -C $HOME/src/BinanceFuturesJava archive 76134a52 pom.xml src/main | tar -x -C $B || exit 9
  [ ! -e $B/src/main/java/com/binance/chuyennd/config/PrivateConfig.java ] || { echo "TU CHOI: archive co PrivateConfig.java"; exit 9; }
  mkdir -p $B/src/main/java/com/binance/chuyennd/config
  cp $T/stub/PrivateConfig.java.stub $B/src/main/java/com/binance/chuyennd/config/PrivateConfig.java
  ( cd $B && flock -w 3600 $HOME/claude_master/locks/oracle_heavy.lock nice -n 10 $MVN -o -q -T 1 compile > $A/stub_compile.log 2>&1 ); RC=$?
  echo "mvn compile RC=$RC" | tee -a $A/stub_compile.log; [ $RC = 0 ] || exit 10
fi
python3 -I $T/make_stub.py --classes $B/target/classes --keys-manifest $A/stub_keys_manifest.json --out-manifest $A/stub_manifest.json
