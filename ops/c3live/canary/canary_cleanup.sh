#!/usr/bin/env bash
# =============================================================================
# canary_cleanup.sh — ket thuc phien: xac nhan 0 vi the / 0 algo / 0 lenh tren TOAN tai khoan con (chi doc), roi doi ten
# run/canary/ -> run/canary_done_<TS>/ tren 242 (giu nguyen bang chung). KHONG dung JVM dry, khong restart gi.
#   YES=1 bash ops/c3live/canary/canary_cleanup.sh          (chay canary_report.sh TRUOC de lay bang chung)
# Ket qua: "KET QUA: DAT|TRUOT|TU_CHOI".
# =============================================================================
. "$(cd "$(dirname "$0")" && pwd)/canary_lib.sh"
cl_init cleanup
need_yes "doi ten thu muc run/canary tren 242"
cl_check_242
cl_push_logback
cl_run "" cleanup; RC=$?
V=$(cl_verdict $RC)
say "cleanup (0 vi the / 0 algo / 0 lenh): $V ($CL_LAST_RESULT)"
if [ "$V" != DAT ]; then
  say "KHONG doi ten run/canary (con vi the/lenh?) — chay canary_flatten.sh roi lai cleanup; bao MASTER"
  say "KET QUA: $V"; say "Log: $CL_LOG"; exit 3
fi
R=$($SSH_242 "cd $A && [ \$(pgrep -fc '$MAIN_PAT') = 0 ] && [ -d $CDIR ] && [ ! -e run/canary_done_$TS ] && mv $CDIR run/canary_done_$TS && echo DOI_TEN_XONG" < /dev/null)
[ "$R" = DOI_TEN_XONG ] || { say "khong doi ten duoc $CDIR (JVM canary dang chay?)"; say "KET QUA: TRUOT"; exit 3; }
ok "$A/$CDIR -> $A/run/canary_done_$TS (bao cao lai: bash $(dirname "$0")/canary_report.sh run/canary_done_$TS)"
say "KET QUA: DAT"
say "Log: $CL_LOG"
