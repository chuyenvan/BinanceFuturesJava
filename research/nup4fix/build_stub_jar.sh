#!/bin/bash
# Build jar sim NUP4-fix tu HEAD sach cua worktree, thay hang token Telegram bang "" CHI trong luc build (khong commit),
# roi khoi phuc file => worktree sach. Chay: bash build_stub_jar.sh   (can LIVE_IS_SHADOW_HOST=true, lock Oracle)
set -u
FX=~/claude_master/nup4_fix; W=$FX/wt; cd $W
export LIVE_IS_SHADOW_HOST=true
[ -z "$(git status --porcelain)" ] || { echo "worktree KHONG sach"; exit 2; }
HEAD=$(git rev-parse HEAD)
TG='src/main/java/com/binance/chuyennd/client/P2PTelegramNotifier.java src/main/java/com/binance/chuyennd/utils/Utils.java'
restore() { git checkout -- $TG; }
trap restore EXIT
sed -i -E 's/"[0-9]{8,10}:[A-Za-z0-9_-]{35}"/""/g' $TG
echo "stub tokens left in src: $(grep -cE '[0-9]{8,10}:[A-Za-z0-9_-]{35}' $TG | paste -sd+ | bc)"
flock -w 3600 ~/claude_master/locks/oracle_heavy.lock nice -n 15 /home/ubuntu/tools/apache-maven-3.9.9/bin/mvn -o -q clean package
rc=$?
restore; trap - EXIT
echo "mvn rc=$rc HEAD=$HEAD"
[ $rc -eq 0 ] || exit $rc
JO=${JAR_OUT:-$FX/jar}; mkdir -p $JO && cp target/binance-java-sdk-1.2.4.jar $JO/sim.jar
echo "$HEAD" > $JO/HEAD.txt
sha256sum $JO/sim.jar; md5sum $JO/sim.jar
git status --porcelain | wc -l
