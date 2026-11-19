#!/usr/bin/env bash
# =============================================================================
# gridtest_phase_b.sh - [GRIDTEST] PHA B: tra gate + K ve production (khong mo leg0 moi qua gate ha), GIU DCA nong (-1/-2/-3 %) de cum dang
#   mo nhoi leg 1-3. env.sh = BASE + khoi "# GRIDTEST <TS_A> pha B <TS>" (chi DCA_GRID_LEVELS). Restart lan 2.
#   DRY=1 bash gridtest_phase_b.sh (MAC DINH) | DRY=0 bash gridtest_phase_b.sh (khung :10-:44, go YES)
# TU CHOI neu: khong o pha A; env.sh != ban pha A (md5 ghi trong state); jar != hotfix; co KILL_SWITCH (phanh/owner => xu ly + gridtest_off.sh);
#   latch/PAUSE; adapter/von sai; 3 key process != gia tri pha A; cron watch / monitor khong song.
# Hong SAU khi dung bot => env.sh = BASE (production) + start, GIU KILL_SWITCH + KHAN (exit 2). Hau kiem truot => GIU KS + KHAN (khong restart them).
# =============================================================================
. "$(cd "$(dirname "$0")" && pwd)/gridtest_common.sh"
gt_manifest_check "$0" || exit 1
gt_init gridtest_phase_b
[ "$C3_ACCOUNT" = SUB ] || die "chi ho tro C3_ACCOUNT=SUB"
gt_op_lock
[ "$(gt_sv GT_PHASE)" = A ] || die "GT_PHASE=$(gt_sv GT_PHASE) (phai A) - $GT_STATE"
TSA=$(gt_sv GT_TS_A); BASE=$(gt_sv GT_BASE); BMD5=$(gt_sv GT_BASE_MD5); EXPCUR=$(gt_sv GT_CUR_MD5)
pre_b() {
  GT_BASE_PATH=$BASE; gt_pre_base b
  chk "env.sh = ban pha A (md5 $(gx ENVSH_MD5 | cut -c1-12) = ${EXPCUR:0:12}), dung 1 khoi GRIDTEST" '[ "$(gx ENVSH_MD5)" = "$EXPCUR" ] && [ "$(gx GT_BLOCKS)" = 1 ]'
  chk "BASE $BASE tren 242 md5 = ${BMD5:0:12}" '[ "$(gx BASE_MD5)" = "$BMD5" ]'
  chk "3 key PROCESS = pha A: $(gx GP_LIVE_GATE_ROLLING_PCT) / $(gx GP_SELECTOR_RANK_TOPK) / $(gx GP_DCA_GRID_LEVELS)" 'gt_keys_ok GP "$GT_PCT_TEST" "$GT_TOPK_TEST" "$GT_LEVELS_TEST"'
  chk "cron gridtest_watch dang cai" 'gt_watch_cron_has'
  chk "gridtest_watch khong hong (khong co $GT_SDIR/WATCH_BROKEN)" '[ ! -e "$GT_SDIR/WATCH_BROKEN" ]'
  say "INFO so c3: $(sv BOOK_CUM) cum (pha B DCA nong cho cac cum nay)"
}
pre_b
[ "$F" = 0 ] || die "kiem truoc co muc FAIL (xem tren)"
BLK=$(gt_block_b "$TSA" "$TS" | base64 -w0)
say "--- KE HOACH pha B: env.sh = BASE (${BMD5:0:12}) + khoi:"; gt_block_b "$TSA" "$TS" | sed 's/^/      /'
say "--- => LIVE_GATE_ROLLING_PCT + SELECTOR_RANK_TOPK ve gia tri BASE (production $GT_PCT_PROD / $GT_TOPK_PROD), DCA_GRID_LEVELS van $GT_LEVELS_TEST"
say "--- KS(token) -> PAUSE -> .lock watchdog -> stop -> env moi -> start -> hau kiem -> go KS -> PUSH ON. Han pha B ${GT_PHASE_B_MAX_H} h"
[ "$DRY" = 1 ] && { say "DRY=1: dung o day, KHONG ghi gi len 242. (DRY PASS)"; exit 0; }
gl_time
gl_yes "GRIDTEST PHA B: gate + K ve production, GIU DCA nong. Bot tat ~20-90 s."
trap '' INT TERM
gl_time
pre_b
[ "$F" = 0 ] || die "kiem lai sau YES co muc FAIL - khong doi gi"
NEW=$(gt_newmd5 "$BASE" "$BLK") || NEW=""
[[ "$NEW" =~ ^[0-9a-f]{32}$ ]] || die "khong tinh duoc md5 env moi (bot KHONG dung)"
gt_state_set GT_PHASE B_START; gt_state_set GT_TS_B "$TS"
GTR_KSP=strict; GTR_CUR=$CURMD5; GTR_NEW=$NEW; GTR_BASE=$BASE; GTR_BASEMD5=$BMD5; GTR_BLK=$BLK
gt_run_restart; rc=$?
if [ "$rc" = 3 ]; then gt_state_set GT_PHASE A; say "KET QUA: TU_CHOI truoc khi dung bot: $(echo "$RS" | grep '^FAIL' | head -2 | tr '\n' ' ') - van pha A"; exit 1; fi
if [ "$rc" = 4 ]; then
  M="pha B: doi env FAIL sau khi dung bot ($(echo "$RS" | grep '^FAIL' | head -2 | tr '\n' ' '))"
  if gt_run_restore "$M"; then gt_state_set GT_PHASE B; gt_state_set GT_CUR_MD5 "$BMD5"; gt_pause_clear
    khan "$M => da KHOI PHUC env production (BASE) + start, GIU run/KILL_SWITCH (cum test con => owner quyet theo prereg muc 7; roi gridtest_off.sh GT_FORCE_KEEP neu can)"; fi
  gt_ks_ensure khoi_phuc_loi; gt_pause_clear; khan "$M VA khoi phuc loi => GIU KS. Kiem golive_monitor.sh ; BASE $A/$BASE"
fi
GTC_PCT=$GT_PCT_PROD; GTC_TOPK=$GT_TOPK_PROD; GTC_LEV=$GT_LEVELS_TEST; GTC_LEVLOG=$GT_LEVELS_LOG_TEST; GTC_KS=mine
gt_state_set GT_CUR_MD5 "$NEW"; gt_state_set GT_PHASE B; gt_state_set GT_T_B "$(date +%s)"; gt_state_set GT_SL_B "$SL"
if ! gl_postloop GT_CHK; then
  gt_ks_ensure hau_kiem_b_truot; gt_pause_clear
  khan "pha B: hau kiem TRUOT ($(echo "$RESULT" | grep '^FAIL\|^WAIT' | tr '\n' ' ' | cut -c1-200)) => GIU run/KILL_SWITCH (khong mo moi, khong DCA). Kiem; tra: gridtest_off.sh"
fi
gt_release_and_push; rc=$?; gt_pause_clear
case $rc in
  0) say "=== XONG PHA B: gate/K production, DCA nong, PUSH ON. Theo doi: bash $GT_HERE/gridtest_watch.sh ; het han/het cum: bash $GT_HERE/gridtest_off.sh"
     tg "[gridtest] PHA B TS=$TS: gate/K production, DCA nong, PUSH ON. Log $LOG" || :; exit 0 ;;
  1) khan "pha B: env da doi nhung con KILL_SWITCH KHAC => bot khong mo/DCA. Kiem" ;;
  *) khan "pha B: hau kiem DAT nhung KHONG thay PUSH ON / khong go duoc KS => da dat lai KS" ;;
esac
