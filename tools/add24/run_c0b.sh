#!/bin/bash
# ADD24 C0 + C0b - 1 lenh, tai lap: bash tools/add24/run_c0b.sh
# Tao stub neu /dev/shm mat (tat dinh, md5 phai = cf0f4792...), build test-classes neu thieu, chay R0 / S-DCA / FIN-INJ tren fx1105
# (moc nhu 11-17) bang STUB trong bwrap --unshare-net, probe C0 (d)(e), roi c0_check.py -> add24/a/C0.json + C0B.json.
set -u
T=$(cd "$(dirname "$0")" && pwd); W=$(cd "$T/../.." && pwd)
A=$HOME/claude_master/w3/add24/a; mkdir -p $A ~/claude_master/locks
STUB=/dev/shm/add24/jar/binance-java-sdk-1.2.4.jar_add24_stub_01cfbb43
EXPM=${ADD24_STUB_MD5:-cf0f479241265de68836716ee66a1866}
export LIVE_IS_SHADOW_HOST=true
DF=$(df -BM --output=avail / | tail -1 | tr -dc 0-9); [ "$DF" -ge 15300 ] || { echo "DUNG: dia $DF MB < 15300"; exit 8; }
AV=$(awk '/MemAvailable/{print int($2/1024)}' /proc/meminfo); [ "$AV" -ge 4000 ] || { echo "DUNG: RAM $AV MB < 4000"; exit 8; }
if [ ! -f $STUB ] || [ "$(md5sum < $STUB | cut -d' ' -f1)" != "$EXPM" ]; then bash $T/make_stub.sh || exit 9; fi
[ "$(md5sum < $STUB | cut -d' ' -f1)" = "$EXPM" ] || { echo "TU CHOI: stub md5 != $EXPM"; exit 9; }
[ -f $W/target/test-classes/com/binance/chuyennd/c3live/e2e/add24/C0Probe.class ] || bash $T/build_wt.sh || exit 9
TS=$(date +%m%d_%H%M%S); OUT=/dev/shm/add24/c0b/$TS; mkdir -p $OUT
export E2E_FX_DIR=$HOME/claude_master/e2e_v12/fx1105 E2E_OUT=$OUT E2E_ENV242=$HOME/claude_master/e2e_v12/env242_whitelist.raw
export LABELS_1105=$W/tools/e2e/labels_1105.csv
H="flock -w 3600 $HOME/claude_master/locks/oracle_heavy.lock nice -n 10"
$H $T/run_lane_stub.sh R0      FAKE 10000 on                              | tee -a $OUT/run_all.txt
$H $T/run_lane_stub.sh S-DCA   FAKE 10000 on E2E_SDCA_AT=1793894400000    | tee -a $OUT/run_all.txt
$H $T/run_lane_stub.sh FIN-INJ FAKE 10000 on E2E_FIN_INJ_AT=1793836800000 | tee -a $OUT/run_all.txt
$H env -i HOME=$HOME PATH=/usr/bin:/bin LANG=C.UTF-8 LIVE_IS_SHADOW_HOST=true LIVE_ADAPTER=dry \
  bwrap --unshare-net --die-with-parent --ro-bind / / --dev /dev --proc /proc --tmpfs /tmp --bind /dev/shm/add24 /dev/shm/add24 \
  java -Xmx512m -cp "$STUB:$W/target/test-classes" com.binance.chuyennd.c3live.e2e.add24.C0Probe $STUB > $OUT/c0probe.jsonl 2>&1
python3 -I $T/c0_check.py --run $OUT --ref $HOME/claude_master/e2e_v12/out1105_1117_0132 --c0 $A/C0.json --c0b $A/C0B.json --probe $OUT/c0probe.jsonl
RC=$?
# luu ban nho len dia (khong luu market/appended/trace lon)
K=$A/c0b_$TS; mkdir -p $K
for L in R0 S-DCA FIN-INJ; do mkdir -p $K/$L; cp $OUT/$L/{legs.csv,outcomes.csv,events.csv,fills.csv,fin_excl.csv,result.json,run.log,env_used.sh} $K/$L/ 2>/dev/null; done
cp $OUT/c0probe.jsonl $OUT/run_all.txt $K/
echo "C0/C0b RC=$RC out=$OUT keep=$K"; exit $RC
