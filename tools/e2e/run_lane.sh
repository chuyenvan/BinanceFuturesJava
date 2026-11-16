#!/bin/bash
# E2E_REPLAY_V12 - chay 1 luot replay bang JAR LIVE nguyen byte + test-classes (prereg §1/§4).
# usage: run_lane.sh <NAME> <FAKE|DRY> <C3_CAPITAL> <on|off> [E2E_SDCA_AT=ms] [E2E_FIN_INJ_AT=ms] [E2E_END=ms]
#   on/off = LIVE_APPLY_GRID_RATIO + LIVE_DCA_GRID_ENABLED (override khai truoc; R-OLD = off)
# env tuy chon: E2E_FX_DIR (mac dinh fixture DEV 10-30), E2E_OUT, E2E_ENV242, E2E_JAR, E2E_OFFICIAL=1 (bat buoc khi fixture != dev)
# Env tien trinh java = env -i + DANH SACH TRANG 242 (file grep ten cu the) + override khai truoc. Khong doc file bi mat.
set -u
NAME=$1; VENUE=$2; CAP=$3; FLAGS=$4; shift 4
W=$(cd "$(dirname "$0")/../.." && pwd)
FX=${E2E_FX_DIR:-$HOME/claude_master/e2e_v12/fx1030}
OUT=${E2E_OUT:-$HOME/claude_master/e2e_v12/out}
ENV242=${E2E_ENV242:-$HOME/claude_master/e2e_v12/env242_whitelist.raw}
JAR=${E2E_JAR:-$HOME/claude_master/v12/jar/binance-java-sdk-1.2.4.jar_v12_r4u3fin2}
EXP=641803565297d4065d90245e04a00f11
M=$(md5sum < "$JAR" | cut -d' ' -f1)
[ "$M" = "$EXP" ] || { echo "TU CHOI: md5 jar $M != $EXP"; exit 3; }
# fixture DEV 10-30: ban goc e2e1105/fx + ban mo rong ERRATA1 e2e_v12/fx1030 (= ban goc + mkt.csv.gz + ts_ext.csv)
if [ "$FX" != "$HOME/claude_master/e2e1105/fx" ] && [ "$FX" != "$HOME/claude_master/e2e_v12/fx1030" ] && [ "${E2E_OFFICIAL:-0}" != 1 ]; then
  echo "TU CHOI: fixture $FX khac fixture dev ma khong co E2E_OFFICIAL=1 (luot chinh thuc chi sau A1 duyet)"; exit 4
fi
[ -d "$W/target/test-classes/com/binance/chuyennd/c3live/e2e/replay" ] || { echo "TU CHOI: chua build test-classes"; exit 5; }
D=$OUT/$NAME; mkdir -p "$D"; rm -rf "$D/wd" "$D/run"; mkdir -p "$D/wd"
# [ERRATA1 E5] KHONG chep config.properties worktree: dung file khai bao tools/e2e/config_replay.properties (nhan tung key)
cp "$W/tools/e2e/config_replay.properties" "$D/wd/config.properties"
WTK=$(grep -oE '^[A-Z0-9_]+=' "$W/config.properties" | tr -d '=' | sort | tr '\n' ',')
if [ "$FLAGS" = on ]; then AG=true; else AG=false; fi
OVR="LIVE_ADAPTER,C3_CAPITAL,LIVE_APPLY_GRID_RATIO,LIVE_DCA_GRID_ENABLED,C3_EXCLUDE_LEGACY_HELD,LIVE_IS_SHADOW_HOST,LIVE_GATE_ROLLING_FILE,LIVE_TS_MKT_EXT"
{
  echo "# env luot $NAME (danh sach trang 242 + override khai truoc) $(date -Is)"
  grep -E '^(export )?[A-Z0-9_]+=' "$ENV242"
  echo "export LIVE_ADAPTER=dry"
  echo "export C3_CAPITAL=$CAP"
  echo "export LIVE_APPLY_GRID_RATIO=$AG"
  echo "export LIVE_DCA_GRID_ENABLED=$AG"
  echo "export C3_EXCLUDE_LEGACY_HELD=false"
  echo "export LIVE_IS_SHADOW_HOST=true"
  echo "export LIVE_GATE_ROLLING_FILE=$D/run/gate_ratio_live.bin"
  echo "export LIVE_TS_MKT_EXT=0   # LECH khai bao: X14 can ALT_EW Aerospike (khong co trong replay) - prereg §7"
  echo "export E2E_WT_CFG_KEYS=$WTK E2E_ERRATA=${E2E_ERRATA:-} E2E_OFFICIAL_LOCK=${E2E_OFFICIAL_LOCK:-}"
  echo "export E2E_RUN=$NAME E2E_VENUE=$VENUE E2E_FX_DIR=$FX E2E_OUT=$OUT E2E_ENV242=$ENV242 E2E_OVERRIDES=$OVR"
  for kv in "$@"; do echo "export $kv"; done
} > "$D/env_used.sh"
CP="$JAR:$W/target/test-classes"
echo "luot=$NAME venue=$VENUE C3_CAPITAL=$CAP flags=$FLAGS fx=$FX out=$D"
cd "$D/wd"
env -i HOME="$HOME" PATH=/usr/bin:/bin LANG=C.UTF-8 bash -c "set -a; . '$D/env_used.sh'; set +a; exec java -Xmx3g -cp '$CP' com.binance.chuyennd.c3live.e2e.replay.ReplayMain" \
  > "$D/run.log" 2>&1
RC=$?
sed -i -E 's/[0-9]{8,10}:[A-Za-z0-9_-]{30,}/<TOKEN>/g' "$D/run.log"
echo "RC=$RC log=$D/run.log"; exit $RC
