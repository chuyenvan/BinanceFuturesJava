#!/usr/bin/env bash
# test_cleanup_docker_log_242.sh — test GIA (khong cham 242). Chay: bash ops/c3live/test/test_cleanup_docker_log_242.sh <tmp>
set -u
HERE=$(cd "$(dirname "$0")/.." && pwd); CL=$HERE/cleanup_docker_log_242.sh
W=${1:?thu muc tam}; rm -rf "$W"; mkdir -p "$W"; W=$(cd "$W" && pwd)
PASS=0; FAILN=0
chk() { if eval "$2"; then PASS=$((PASS+1)); echo "  [PASS] $1"; else FAILN=$((FAILN+1)); echo "  [FAIL] $1"; fi; }
TAG=fakedk$$
mk() {
  pkill -f "$TAG" 2>/dev/null; sleep 0.2; rm -rf "$W/c" "$W/logdir"; mkdir -p "$W/logdir"
  for c in stopped1 running1 recent1 open1 "sp ace"; do mkdir -p "$W/c/$c"; seq 1 50000 > "$W/c/$c/$c-json.log"; touch -d '60 days ago' "$W/c/$c/$c-json.log"
    echo '{"State":{"Running":false},"Name":"/n_'"$c"'","Config":{"Image":"img"}}' > "$W/c/$c/config.v2.json"; done
  echo '{"State":{"Running":true},"Name":"/r"}' > "$W/c/running1/config.v2.json"
  touch "$W/c/recent1/recent1-json.log"
  setsid bash -c "exec 3<'$W/c/open1/open1-json.log'; exec -a 'sleep $TAG' sleep 600" >/dev/null 2>&1 < /dev/null & sleep 0.3
}
export SSH_242="bash -c" CL_DOCKER_DIR="$W/c" CL_LOGDIR="$W/logdir" CL_DAEMON_NAMES="nomatch_dk"
sz() { stat -c %s "$W/c/$1/$1-json.log"; }
echo "== cleanup_docker_log_242"
mk
OUT=$(bash "$CL" 2>&1); RC=$?
chk "DRY: SE truncate stopped1 + 'sp ace', GIU running/recent/open, khong doi gi" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'SE truncate stopped1' && echo \"\$OUT\" | grep -q 'SE truncate sp ace' && echo \"\$OUT\" | grep -q 'GIU (container khong xac nhan DA DUNG) running1' && echo \"\$OUT\" | grep -q 'GIU (ghi trong 30 ngay) recent1' && echo \"\$OUT\" | grep -q 'GIU (dang mo) open1' && [ \$(sz stopped1) -gt 0 ]"
OUT=$(bash "$CL" --apply 2>&1); RC=$?
chk "APPLY: truncate dung 2 file, giu 3 file, thu muc/config con nguyen" "[ $RC = 0 ] && [ \$(sz stopped1) = 0 ] && [ \"\$(stat -c %s '$W/c/sp ace/sp ace-json.log')\" = 0 ] && [ \$(sz running1) -gt 0 ] && [ \$(sz recent1) -gt 0 ] && [ \$(sz open1) -gt 0 ] && [ -f '$W/c/stopped1/config.v2.json' ]"
mk; mkdir -p "$W/noproc"
OUT=$(CL_PROC="$W/noproc" bash "$CL" --apply 2>&1); RC=$?
chk "khong doc duoc /proc => ABORT, khong truncate" "[ $RC != 0 ] && echo \"\$OUT\" | grep -q 'ABORT/FAIL: khong doc duoc' && [ \$(sz stopped1) -gt 0 ]"
ln -sf "$(command -v sleep)" "$W/dkgia$$"; setsid "$W/dkgia$$" 600 >/dev/null 2>&1 < /dev/null & DKP=$!; sleep 0.3
OUT=$(CL_DAEMON_NAMES="dkgia$$" bash "$CL" --apply 2>&1); RC=$?; kill $DKP 2>/dev/null
chk "dockerd dang chay => ABORT, khong truncate" "[ $RC != 0 ] && echo \"\$OUT\" | grep -q 'DANG CHAY' && [ \$(sz stopped1) -gt 0 ]"
pkill -f "$TAG" 2>/dev/null
echo "TEST $( [ $FAILN = 0 ] && echo PASS || echo FAIL ) $PASS/$((PASS+FAILN))"
[ $FAILN = 0 ]
