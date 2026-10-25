#!/usr/bin/env bash
# =============================================================================
# canary_step.sh <K> — chay lai 1 kich ban G-CANARY (sau khi MASTER cho phep), hoac SETUP (CROSSED/1x cho 2 symbol canary).
#   YES=1 bash ops/c3live/canary/canary_step.sh K4
#   K = SETUP | K1..K8 | K6 (OPEN+RESTART) | K6B (OPEN+doi ten so+RESTART+dong tay) | K7B | K6_OPEN K6_RESTART K6B_OPEN K6B_RESTART (tung nua)
#   K1 + tiem timeout MO-5 (1 lan / phien, cong cu tu choi lan 2): YES=1 CANARY_INJECT_TIMEOUT=1 bash canary_step.sh K1
# KHONG DAT (buoc giao dich) => tu flatten 2 symbol canary. Ket qua: "KET QUA: DAT|TRUOT|TU_CHOI".
# =============================================================================
. "$(cd "$(dirname "$0")" && pwd)/canary_lib.sh"
K=$(echo "${1:-}" | tr '[:lower:]' '[:upper:]')
cl_init "step_${K:-none}"
case "$K" in
  SETUP|K1|K2|K3|K4|K5|K6|K6B|K7|K7B|K8|K6_OPEN|K6_RESTART|K6B_OPEN|K6B_RESTART) ;;
  *) die "thieu/sai buoc '$K' (SETUP K1..K8 K6 K6B K7B K6_OPEN K6_RESTART K6B_OPEN K6B_RESTART)" ;;
esac
need_yes "$( [ "$K" = SETUP ] && echo "doi marginType/leverage 2 symbol canary" || echo "gui LENH THAT (tien that)")" "$K"
[[ "${CANARY_INJECT_TIMEOUT:-0}" =~ ^[01]$ ]] || die "CANARY_INJECT_TIMEOUT chi 0/1"
cl_time_gate die
cl_gates
cl_check_242 dry
cl_push_logback
cl_macro "$K"; RC=$?
V=$(cl_verdict $RC)
say "$K: $V ($CL_LAST_RESULT)"
case "$K" in
  SETUP|K6_OPEN|K6B_OPEN) ;;   # SETUP khong mo vi the; *_OPEN co chu dich de vi the cho buoc RESTART
  *) if [ "$RC" != 0 ]; then
       say "buoc khong DAT — dong het vi the 2 symbol canary (flatten)"
       cl_run "" flatten; RF=$?
       say "flatten: $(cl_verdict $RF) ($CL_LAST_RESULT)"
       [ "$RF" = 0 ] || say "!! flatten KHONG DAT — owner chay ngay: YES=1 bash $(dirname "$0")/canary_flatten.sh ; bao MASTER"
     fi ;;
esac
say "KET QUA: $V"
say "Log: $CL_LOG"
[ "$RC" = 0 ]
