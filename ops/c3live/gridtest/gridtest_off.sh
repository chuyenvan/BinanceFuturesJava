#!/usr/bin/env bash
# =============================================================================
# gridtest_off.sh - [GRIDTEST] TRA CAU HINH production: env.sh = BASE (xoa DUNG khoi GRIDTEST; kiem md5 = BASE) + restart + go cron watch.
#   DRY=1 bash gridtest_off.sh (MAC DINH) | DRY=0 bash gridtest_off.sh (khung :10-:44, go YES)
#   Mac dinh TU CHOI neu so/san c3 CON cum / vi the / lenh / algo (prereg muc 7). GT_FORCE_KEEP=1 (owner + MASTER) = giu cum: cum test song
#   duoi luat production (bac DCA con lai tinh tu firstEntry: legCount=1 -> -50 %, 2 -> -75 %, 3 -> -90 %, 4 -> het; time-stop 168 h).
#   KILL_SWITCH co san (phanh gridtest_watch / owner drain) => GIU NGUYEN (bot len van drain). GT_RELEASE_BRAKE=1 => go RIENG KS cua phanh
#   (token 'gridtest_watch <TS_A> ...') SAU khi tra cau hinh DAT. KHONG bao gio go KS khac.
# Hong SAU khi dung bot => start lai voi BASE (KS giu) + KHAN.
# =============================================================================
. "$(cd "$(dirname "$0")" && pwd)/gridtest_common.sh"
gt_manifest_check "$0" || exit 1
gt_init gridtest_off
[ "$C3_ACCOUNT" = SUB ] || die "chi ho tro C3_ACCOUNT=SUB"
gt_op_lock
PH=$(gt_sv GT_PHASE)
case "$PH" in A|B|A_FAIL|B_START|OFF_START) ;; *) die "khong co phien gridtest dang mo (GT_PHASE=${PH:-chua_co}, $GT_STATE)";; esac
TSA=$(gt_sv GT_TS_A); BASE=$(gt_sv GT_BASE); BMD5=$(gt_sv GT_BASE_MD5); EXPCUR=$(gt_sv GT_CUR_MD5)
[ -n "$BASE" ] && [[ "$BMD5" =~ ^[0-9a-f]{32}$ ]] || die "state thieu GT_BASE/GT_BASE_MD5"
ALREADY=0
pre_off() {
  GT_BASE_PATH=$BASE; gt_pre_base off
  chk "BASE $BASE tren 242 md5 = ${BMD5:0:12}" '[ "$(gx BASE_MD5)" = "$BMD5" ]'
  if [ "$(gx ENVSH_MD5)" = "$BMD5" ] && [ "$(gx GT_BLOCKS)" = 0 ]; then ALREADY=1; say "INFO env.sh DA = BASE (production) - chi kiem process + go cron"
  else chk "env.sh = ban gridtest cuoi (md5 ${EXPCUR:0:12}), dung 1 khoi GRIDTEST (khong ai sua ngoai)" '[ "$(gx ENVSH_MD5)" = "$EXPCUR" ] && [ "$(gx GT_BLOCKS)" = 1 ]'; fi
  if gt_flat; then say "OK   so + san c3 FLAT"
  elif [ "${GT_FORCE_KEEP:-0}" = 1 ]; then say "WARN so/san c3 CON cum/vi the - GT_FORCE_KEEP=1: GIU (cum song duoi luat production; ghi vao bao cao)"
  else say "FAIL so/san c3 CON cum/vi the/lenh (dong het theo prereg muc 7 / U1, hoac GT_FORCE_KEEP=1)"; F=1; fi
}
pre_off
[ "$F" = 0 ] || die "kiem truoc co muc FAIL (xem tren)"
if [ "$ALREADY" = 1 ]; then
  gt_keys_ok GP "$GT_PCT_PROD" "$GT_TOPK_PROD" none || die "env.sh = BASE nhung process CHUA (3 key process khac production) - can restart: lien he MASTER"
  [ "$DRY" = 1 ] && { say "DRY=1: env + process da production; se go cron watch. (DRY PASS)"; exit 0; }
  gt_watch_cron_remove && say "OK go cron gridtest_watch" || die "go cron watch loi"
  gt_state_set GT_PHASE OFF; gt_state_set GT_TS_OFF "$TS"; say "=== DA XONG (khong restart)"; exit 0
fi
KSO=$(gx KS_HEAD)
say "--- KE HOACH: env.sh = BASE ${BMD5:0:12} (xoa khoi GRIDTEST) -> restart (KS: $([ "$(sv KILLSW_FILE)" = 1 ] && echo "GIU KS co san '$KSO'" || echo "token rieng")) -> hau kiem production -> go cron watch -> PUSH ON (neu khong co KS khac)"
[ "${GT_RELEASE_BRAKE:-0}" = 1 ] && say "--- GT_RELEASE_BRAKE=1: sau khi DAT se go KS cua PHANH neu token = 'gridtest_watch $TSA ...'"
[ "$DRY" = 1 ] && { say "DRY=1: dung o day, KHONG ghi gi len 242. (DRY PASS)"; exit 0; }
gl_time
gl_yes "GRIDTEST OFF: tra env production + restart (bot tat ~20-90 s)."
trap '' INT TERM
gl_time
pre_off
[ "$F" = 0 ] || die "kiem lai sau YES co muc FAIL - khong doi gi"
[ "$ALREADY" = 1 ] && die "env.sh vua thanh BASE (ai do da sua?) - chay lai"
gt_state_set GT_PHASE_BEFORE_OFF "$PH"; gt_state_set GT_PHASE OFF_START
GTR_KSP=keep; GTR_CUR=$CURMD5; GTR_NEW=$BMD5; GTR_BASE=$BASE; GTR_BASEMD5=$BMD5; GTR_BLK=none
gt_run_restart; rc=$?
if [ "$rc" = 3 ]; then gt_state_set GT_PHASE "$PH"; say "KET QUA: TU_CHOI truoc khi dung bot: $(echo "$RS" | grep '^FAIL' | head -2 | tr '\n' ' ') - khong doi gi"; exit 1; fi
if [ "$rc" = 4 ]; then
  M="off: buoc doi env FAIL sau khi dung bot ($(echo "$RS" | grep '^FAIL' | head -2 | tr '\n' ' '))"
  gt_run_restore "$M" || { gt_ks_ensure khoi_phuc_loi; gt_pause_clear; khan "$M VA start lai loi => GIU KS. Kiem golive_monitor.sh"; }
fi
KSMODE=mine; echo "$RS" | grep -q '^INFO KILL_SWITCH_khac_dang_dat' && KSMODE=other
gt_set_prod_chk "$KSMODE"
if ! gl_postloop GT_CHK; then
  gt_ks_ensure hau_kiem_off_truot; gt_pause_clear; gt_state_set GT_PHASE OFF_FAIL
  khan "off: hau kiem TRUOT ($(echo "$RESULT" | grep '^FAIL\|^WAIT' | tr '\n' ' ' | cut -c1-200)) => GIU run/KILL_SWITCH. Kiem golive_monitor.sh"
fi
gt_state_set GT_CUR_MD5 "$BMD5"; gt_state_set GT_PHASE OFF; gt_state_set GT_TS_OFF "$TS"; gt_state_set GT_T_OFF "$(date +%s)"
gt_watch_cron_remove && say "OK go cron gridtest_watch" || say "!! go cron gridtest_watch LOI - go tay dong '$GT_CRON_TAG'"
if [ "${GT_RELEASE_BRAKE:-0}" = 1 ]; then
  s242 "cd $A && grep -q '^gridtest_watch $TSA ' run/KILL_SWITCH 2>/dev/null && mv -f run/KILL_SWITCH run/KILL_SWITCH.gtbrake_$TS; true" && say "INFO KS phanh (neu co) da go"
fi
if [ "$KSMODE" = mine ]; then gt_release_and_push; rc=$?; else
  if s242 "[ -e $A/run/KILL_SWITCH ]"; then rc=1; else rc=9; fi; fi
gt_pause_clear
case $rc in
  0) say "=== XONG OFF: env production, PUSH ON, cron watch da go. Bao cao: bash $GT_HERE/gridtest_report.sh"; tg "[gridtest] OFF TS=$TS: env production, PUSH ON. Log $LOG" || :; exit 0 ;;
  1) say "=== XONG OFF: env production; KILL_SWITCH KHAC van GIU => bot DRAIN. Mo lai: MODE=undrain bash $GT_OPS/golive_live_off.sh (sau khi MASTER xem) / GT_RELEASE_BRAKE=1"
     tg "[gridtest] OFF TS=$TS: env production, KS khac van giu (drain). Log $LOG" || :; exit 0 ;;
  9) say "=== XONG OFF: env production; KS da go (phanh) - bot se PUSH ON. Kiem golive_monitor.sh"; exit 0 ;;
  *) khan "off: env production DAT nhung KHONG thay PUSH ON / khong go duoc KS => da dat lai KS" ;;
esac
