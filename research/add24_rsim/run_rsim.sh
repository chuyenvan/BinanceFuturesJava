#!/bin/bash
# ADD24 R-SIM (DEV-B): chay Add24RsimMain (harness CrashDayRig cua DEV-A, KHONG sua) voi jar STUB trong bwrap --unshare-net.
# usage: run_rsim.sh <NAME> <FX_DIR> <OUT_ROOT>   (OW1 chi qua run_official_rsim.sh co khoa)
set -u
NAME=$1; FX=$2; OUT=$3
W=$HOME/claude_master/w3/add24_wt
MYC=$HOME/claude_master/w3/add24/b/classes
ENV242=$HOME/claude_master/e2e_v12/env242_whitelist.raw
JAR=/dev/shm/add24/jar/binance-java-sdk-1.2.4.jar_add24_stub_01cfbb43
SMAN=$HOME/claude_master/w3/add24/a/stub_manifest.json
EXP=$(python3 -c "import json;print(json.load(open('$SMAN'))['stub_md5'])") || exit 3
[ "$EXP" = cf0f479241265de68836716ee66a1866 ] || { echo "TU CHOI: manifest stub md5 $EXP"; exit 3; }
M=$(md5sum < "$JAR" | cut -d' ' -f1); [ "$M" = "$EXP" ] || { echo "TU CHOI: md5 stub $M"; exit 3; }
[ -d "$W/target/test-classes/com/binance/chuyennd/c3live/e2e/replay" ] || { echo "TU CHOI: chua build test-classes DEV-A"; exit 5; }
TSX=$(python3 -c "import json;print(json.load(open('$HOME/claude_master/tsx/ho/ho_flags.json'))['ranges'])")
D=$OUT/$NAME; mkdir -p "$D"; rm -rf "$D/wd" "$D/run"; mkdir -p "$D/wd" "$D/run"
cp "$W/tools/e2e/config_replay.properties" "$D/wd/config.properties"
OVR="LIVE_ADAPTER,C3_CAPITAL,LIVE_APPLY_GRID_RATIO,LIVE_DCA_GRID_ENABLED,C3_EXCLUDE_LEGACY_HELD,LIVE_IS_SHADOW_HOST,LIVE_GATE_ROLLING_FILE,LIVE_TS_MKT_EXT,LIVE_TS_EXT_FILE"
{
  echo "# env R-SIM $NAME (danh sach trang 242 11-16 + override khai truoc) $(date -Is)"
  grep -E '^(export )?[A-Z0-9_]+=' "$ENV242"
  echo "export LIVE_ADAPTER=dry"
  echo "export C3_CAPITAL=10000"
  echo "export LIVE_APPLY_GRID_RATIO=true"
  echo "export LIVE_DCA_GRID_ENABLED=true"
  echo "export C3_EXCLUDE_LEGACY_HELD=false"
  echo "export LIVE_IS_SHADOW_HOST=true"
  echo "export LIVE_GATE_ROLLING_FILE=$D/run/gate_ratio_live.bin"
  echo "export LIVE_TS_MKT_EXT=1   # R-SIM: co TS_EXT = SIM_LOSER_TS_EXT_DAYS 2026 (ho_flags.json) nap vao TsMktExt jar"
  echo "export LIVE_TS_EXT_FILE=$D/run/ts_ext_unused.csv"
  echo "export ADD24_TSX_DAYS=$TSX"
  echo "export ADD24_SIMTIER=${ADD24_SIMTIER:-}   # ERRATA4 1a: tier luoi sim (L12); rong = tat"
  echo "export ADD24_WARM=$FX/warm.csv.gz ADD24_FOLLOW=$FX/follow.csv ADD24_INTRABAR=${ADD24_INTRABAR:-sim}"
  echo "export E2E_RUN=$NAME E2E_VENUE=FAKE E2E_FX_DIR=$FX E2E_OUT=$OUT E2E_ENV242=$ENV242 E2E_OVERRIDES=$OVR E2E_JAR_MD5=$EXP"
} > "$D/env_used.sh"
CP="$JAR:$W/target/test-classes:$MYC"
echo "R-SIM run=$NAME fx=$FX out=$D"
cd "$D/wd"
env -i HOME="$HOME" PATH=/usr/bin:/bin LANG=C.UTF-8 bwrap --unshare-net --die-with-parent --ro-bind / / --dev /dev --proc /proc --tmpfs /tmp \
  --bind "$D" "$D" --ro-bind /dev/shm/add24/jar /dev/shm/add24/jar --bind /dev/shm/add24/b /dev/shm/add24/b \
  bash -c "set -a; . '$D/env_used.sh'; set +a; export LIVE_IS_SHADOW_HOST=true; exec java -Xmx3g -cp '$CP' com.binance.chuyennd.c3live.e2e.replay.Add24RsimMain" \
  > "$D/run.log" 2>&1
RC=$?
sed -i -E 's/[0-9]{8,10}:[A-Za-z0-9_-]{30,}/<TOKEN>/g' "$D/run.log"
echo "RC=$RC log=$D/run.log"; exit $RC
