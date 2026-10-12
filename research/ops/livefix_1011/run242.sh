#!/bin/bash
# Chay 1 script buoc (w*_242.sh / r_*_242.sh) TREN 242 qua 'bash -s'; log tee vao deploy/logs. Exit = exit cua script.
# Bien moi truong cho script 242 (vd MAPPER_RESTORE=YES) truyen qua tham so 2: run242.sh r_rollback_242.sh "MAPPER_RESTORE=YES"
source /home/ubuntu/claude_master/1011/livefix/deploy/dep_env.sh
[ -f "$1" ] || { echo "thieu script $1"; exit 2; }
L=$LOGD/$(basename "$1" .sh)_$(date +%Y%m%d_%H%M%S).log
$S242 "${2:-} bash -s" < "$1" 2>&1 | tee "$L"
rc=${PIPESTATUS[0]}
echo "== rc=$rc log=$L"
exit $rc
