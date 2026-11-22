#!/bin/bash
# ADD24 (ban sao run_lane.sh def1f034, CHI doi: jar = STUB ADD24 + md5 mong doi tu manifest stub; java trong bwrap --unshare-net;
#   cho phep fixture fx1105 (C0b, khong phai luot chinh thuc can khoa); E2E_JAR_MD5 truyen cho ReplayMain).
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
JAR=/dev/shm/add24/jar/binance-java-sdk-1.2.4.jar_add24_stub_01cfbb43
SMAN=$HOME/claude_master/w3/add24/a/stub_manifest.json
EXP=$(python3 -c "import json;print(json.load(open('$SMAN'))['stub_md5'])") || { echo "TU CHOI: khong doc duoc manifest stub"; exit 3; }
[ "$EXP" = "${ADD24_STUB_MD5:-cf0f479241265de68836716ee66a1866}" ] || { echo "TU CHOI: manifest stub md5 $EXP != ADD24_STUB_MD5"; exit 3; }
M=$(md5sum < "$JAR" | cut -d' ' -f1)
[ "$M" = "$EXP" ] || { echo "TU CHOI: md5 jar $M != $EXP"; exit 3; }
# fixture DEV 10-30: ban goc e2e1105/fx + ban mo rong ERRATA1 e2e_v12/fx1030 (= ban goc + mkt.csv.gz + ts_ext.csv)
if [ "$FX" != "$HOME/claude_master/e2e1105/fx" ] && [ "$FX" != "$HOME/claude_master/e2e_v12/fx1030" ] && [ "$FX" != "$HOME/claude_master/e2e_v12/fx1105" ] && [ "${E2E_OFFICIAL:-0}" != 1 ]; then
  echo "TU CHOI: fixture $FX khac fixture dev ma khong co E2E_OFFICIAL=1 (luot chinh thuc chi sau A1 duyet)"; exit 4
fi
[ -d "$W/target/test-classes/com/binance/chuyennd/c3live/e2e/replay" ] || { echo "TU CHOI: chua build test-classes"; exit 5; }
D=$OUT/$NAME; mkdir -p "$D"; rm -rf "$D/wd" "$D/run"; mkdir -p "$D/wd"
# [ERRATA1 E5] KHONG chep config.properties worktree: dung file khai bao tools/e2e/config_replay.properties (nhan tung key)
cp "$W/tools/e2e/config_replay.properties" "$D/wd/config.properties"
# [ERRATA3 E9] CHI luot R-OLD: C3_EXCLUDE_LEGACY_HELD=true + danh sach LEGACY cua NGAY fixture (pull242/<ngay START +07>:
#   run/legacy_symbols.csv neu co, nguoc lai dong log [LEGACY] managed cuoi cung <= START) ghi vao run/legacy_symbols.csv cua
#   cwd jar (= LegacySymbols.DEFAULT_FILE, duong production). Nguon + md5 => $D/legacy_E9.json -> result.json (legacy_E9).
#   Cac luot khac: false (prereg muc 1). Khong lap duoc danh sach => TU CHOI (exit 6).
EXCL=false; LEGMETA=""
if [ "$NAME" = R-OLD ]; then
  EXCL=true; LEGMETA="$D/legacy_E9.json"
  FXS=$(python3 -c "import json;print(json.load(open('$FX/manifest.json'))['START'])")
  FXE=$(python3 -c "import json;print(json.load(open('$FX/manifest.json'))['END'])")
  mkdir -p "$D/wd/run"
  python3 "$W/tools/e2e/legacy_src.py" --start "$FXS" --end "$FXE" --out-csv "$D/wd/run/legacy_symbols.csv" --out-json "$LEGMETA" \
    > "$D/legacy_E9.log" 2>&1 || { echo "TU CHOI: khong lap duoc danh sach LEGACY (ERRATA3 E9) - xem $D/legacy_E9.log"; exit 6; }
  cat "$D/legacy_E9.log"
fi
LABELS=${LABELS_1105:-$W/tools/e2e/labels_1105.csv}
WTK=$(grep -oE '^[A-Z0-9_]+=' "$W/config.properties" | tr -d '=' | sort | tr '\n' ',')
if [ "$FLAGS" = on ]; then AG=true; else AG=false; fi
OVR="LIVE_ADAPTER,C3_CAPITAL,LIVE_APPLY_GRID_RATIO,LIVE_DCA_GRID_ENABLED,C3_EXCLUDE_LEGACY_HELD,LIVE_IS_SHADOW_HOST,LIVE_GATE_ROLLING_FILE,LIVE_TS_MKT_EXT"
# [ADD24] override KHAI TRUOC bo sung (file ADD24_OVR_FILE, dong "export K=V"; ghi vao env_used SAU cac override chuan => thang)
if [ -n "${ADD24_OVR_FILE:-}" ]; then
  [ -f "$ADD24_OVR_FILE" ] || { echo "TU CHOI: thieu $ADD24_OVR_FILE"; exit 3; }
  OVR="$OVR,$(grep -oE '^export [A-Z0-9_]+=' "$ADD24_OVR_FILE" | cut -c8- | tr -d '=' | paste -sd, -)"
fi
{
  echo "# env luot $NAME (danh sach trang 242 + override khai truoc) $(date -Is)"
  grep -E '^(export )?[A-Z0-9_]+=' "$ENV242"
  echo "export LIVE_ADAPTER=dry"
  echo "export C3_CAPITAL=$CAP"
  echo "export LIVE_APPLY_GRID_RATIO=$AG"
  echo "export LIVE_DCA_GRID_ENABLED=$AG"
  echo "export C3_EXCLUDE_LEGACY_HELD=$EXCL   # [ERRATA3 E9] true CHI o R-OLD"
  echo "export LIVE_IS_SHADOW_HOST=true"
  echo "export E2E_JAR_MD5=$EXP   # ADD24 stub"
  echo "export LIVE_GATE_ROLLING_FILE=$D/run/gate_ratio_live.bin"
  echo "export LIVE_TS_MKT_EXT=0   # LECH khai bao: X14 can ALT_EW Aerospike (khong co trong replay) - prereg §7"
  echo "export E2E_WT_CFG_KEYS=$WTK E2E_ERRATA=${E2E_ERRATA:-} E2E_OFFICIAL_LOCK=${E2E_OFFICIAL_LOCK:-}"
  echo "export E2E_LEGACY_META=$LEGMETA E2E_LABELS_FILE=$LABELS"
  echo "export E2E_RUN=$NAME E2E_VENUE=$VENUE E2E_FX_DIR=$FX E2E_OUT=$OUT E2E_ENV242=$ENV242 E2E_OVERRIDES=$OVR"
  for kv in "$@"; do echo "export $kv"; done
  [ -n "${ADD24_OVR_FILE:-}" ] && { echo "# ADD24 override khai truoc: $ADD24_OVR_FILE md5=$(md5sum < "$ADD24_OVR_FILE" | cut -c1-32)"; grep -E '^export [A-Z0-9_]+=' "$ADD24_OVR_FILE"; }
} > "$D/env_used.sh"
CP="$JAR:$W/target/test-classes"
echo "luot=$NAME venue=$VENUE C3_CAPITAL=$CAP flags=$FLAGS fx=$FX out=$D"
cd "$D/wd"
env -i HOME="$HOME" PATH=/usr/bin:/bin LANG=C.UTF-8 bwrap --unshare-net --die-with-parent --ro-bind / / --dev /dev --proc /proc --tmpfs /tmp \
  --bind "$D" "$D" --bind /dev/shm/add24 /dev/shm/add24 \
  bash -c "set -a; . '$D/env_used.sh'; set +a; export LIVE_IS_SHADOW_HOST=true; exec java -Xmx3g -cp '$CP' com.binance.chuyennd.c3live.e2e.replay.ReplayMain" \
  > "$D/run.log" 2>&1
RC=$?
sed -i -E 's/[0-9]{8,10}:[A-Za-z0-9_-]{30,}/<TOKEN>/g' "$D/run.log"
echo "RC=$RC log=$D/run.log"; exit $RC
