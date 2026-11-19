#!/usr/bin/env bash
# =============================================================================
# gridtest_on.sh - [GRIDTEST] PHA A "hot window" tren MICRO-LIVE tk con: them 1 khoi "# GRIDTEST <TS>" cuoi conf/env.sh
#   (LIVE_GATE_ROLLING_PCT=0.99, SELECTOR_RANK_TOPK=1, DCA_GRID_LEVELS=-0.01,-0.02,-0.03) + restart v_t_m (LEGACY cung JVM ngung ~20-90 s).
#   DRY=1 bash gridtest_on.sh      # MAC DINH: kiem (242 CHI DOC + 1 luot doc san chi-doc) + in ke hoach, KHONG ghi gi
#   DRY=0 bash gridtest_on.sh      # khung :10-:44, go YES
# TU CHOI neu: HEAD chua A1 / manifest lech; jar (file + process) != hotfix 01cfbb43..; process chay < 6 h; so/san c3 KHONG FLAT;
#   co run/KILL_SWITCH / latch / PAUSE; adapter != live; C3_CAPITAL != 1000; 3 key != production (0.999950829 / 24 / khong DCA_GRID_LEVELS);
#   env.sh da co khoi GRIDTEST; monitor cron khong song; dang co phien gridtest.
# Trinh tu: BASE = ban sao env.sh (242, md5) -> [1 ssh] KILL_SWITCH(token) -> PAUSE -> cho .lock watchdog -> stop -> env.sh = BASE + khoi A
#   -> start -> hau kiem (process env 3 key + log [GATE-RATIO]/[LIVE-DCA-GRID], jar process, adapter, von, key, stream, recon, LEGACY)
#   -> cai cron gridtest_watch (phanh) + chay thu 1 luot -> go KILL_SWITCH cua minh -> PUSH ON.
# Hong sau khi dung bot => KHOI PHUC env.sh = BASE + start + hau kiem; DAT => go KS cua minh (exit 1); khong => GIU KS + KHAN (exit 2).
# Ma thoat: 0 XONG/DRY PASS | 1 TU CHOI / da khoi phuc | 2 KHAN.
# =============================================================================
. "$(cd "$(dirname "$0")" && pwd)/gridtest_common.sh"
gt_manifest_check "$0" || exit 1
gt_init gridtest_on
[ "$C3_ACCOUNT" = SUB ] || die "chi ho tro C3_ACCOUNT=SUB"
gt_op_lock
case "$(gt_sv GT_PHASE)" in A|B|A_START|B_START|OFF_START) die "dang co phien gridtest (GT_PHASE=$(gt_sv GT_PHASE), $GT_STATE) - dung gridtest_off.sh / gridtest_watch.sh";; esac
pre_on() {
  GT_BASE_PATH=none; gt_pre_base on
  chk "process chay >= ${GT_MIN_UP_S}s (jar hotfix on dinh, khong HB_STALE_KILL) (co $(gx PUP_S)s)" '[ "$(gx PUP_S)" -ge "$GT_MIN_UP_S" ] 2>/dev/null'
  chk "3 key PROCESS = production (PCT=$GT_PCT_PROD TOPK=$GT_TOPK_PROD, khong DCA_GRID_LEVELS): $(gx GP_LIVE_GATE_ROLLING_PCT) / $(gx GP_SELECTOR_RANK_TOPK) / $(gx GP_DCA_GRID_LEVELS)" 'gt_keys_ok GP "$GT_PCT_PROD" "$GT_TOPK_PROD" none'
  chk "3 key env.sh = production: $(gx GS_LIVE_GATE_ROLLING_PCT) / $(gx GS_SELECTOR_RANK_TOPK) / $(gx GS_DCA_GRID_LEVELS)" 'gt_keys_ok GS "$GT_PCT_PROD" "$GT_TOPK_PROD" none'
  chk "env.sh CHUA co khoi GRIDTEST" '[ "$(gx GT_BLOCKS)" = 0 ]'
  chk "cron gridtest_watch CHUA co (sot phien cu?)" '! gt_watch_cron_has'
  chk "so + san c3 FLAT (0 cum, 0 vi the, 0 lenh, 0 algo)" 'gt_flat'
}
pre_on
[ "$F" = 0 ] || die "kiem truoc co muc FAIL (xem tren)"
BLK=$(gt_block_a "$TS" | base64 -w0)
say "--- KE HOACH pha A: BASE=conf/env.sh.gridtest_base_$TS (= env.sh hien tai ${CURMD5:0:12}); them khoi cuoi env.sh:"
gt_block_a "$TS" | sed 's/^/      /'
say "--- KILL_SWITCH token '$NM $TS' -> PAUSE watchdog -> cho .lock -> stop -> env.sh = BASE + khoi -> start -> hau kiem -> cai cron gridtest_watch (1') -> go KS -> PUSH ON"
say "--- phanh (gridtest_watch): leg0 > $GT_HARD_LEG0 | SUBMIT > $GT_HARD_SUBMIT | notional c3 > $GT_HARD_NOTIONAL | lo chua thuc hien < $GT_HARD_UPNL USDT | KHAN log => run/KILL_SWITCH + Telegram"
say "--- leg0 >= $GT_N_LEG0 => owner chay gridtest_phase_b.sh ; han pha A ${GT_PHASE_A_MAX_H} h. Tra cau hinh: gridtest_off.sh"
[ "$DRY" = 1 ] && { say "DRY=1: dung o day, KHONG ghi gi len 242. (DRY PASS)"; exit 0; }
gl_time
gl_yes "GRIDTEST PHA A: lenh THAT tk con (gate pct=$GT_PCT_TEST, K=$GT_TOPK_TEST, DCA $GT_LEVELS_TEST). Bot tat ~20-90 s."
trap '' INT TERM
gl_time
pre_on
[ "$F" = 0 ] || die "kiem lai sau YES co muc FAIL - khong doi gi"
BASE=conf/env.sh.gridtest_base_$TS
BR=$(s242 "cd $A && { [ -e $BASE ] || \cp -p conf/env.sh $BASE; } && M=\$(md5sum < $BASE | cut -c1-32) && [ \"\$M\" = $CURMD5 ] && echo \$M > $BASE.md5 && echo OK_BASE") || BR=""
[ "$BR" = OK_BASE ] || die "khong tao/xac nhan duoc BASE $BASE tren 242 (bot KHONG dung)"
NEW=$(gt_newmd5 "$BASE" "$BLK") || NEW=""
[[ "$NEW" =~ ^[0-9a-f]{32}$ ]] || die "khong tinh duoc md5 env moi (bot KHONG dung)"
gt_state_set GT_PHASE A_START; gt_state_set GT_TS_A "$TS"; gt_state_set GT_BASE "$BASE"; gt_state_set GT_BASE_MD5 "$CURMD5"
gt_state_set GT_L0_A "$L0"; gt_state_set GT_CUR_MD5 "$CURMD5"; gt_state_set GT_HEAD "$_GT_HC"
GTR_KSP=strict; GTR_CUR=$CURMD5; GTR_NEW=$NEW; GTR_BASE=$BASE; GTR_BASEMD5=$CURMD5; GTR_BLK=$BLK
do_restore() {   # pha A: ve production (0 cum) ; DAT => go KS cua minh, exit 1
  gt_watch_cron_remove || say "!! go cron watch loi"
  if ! gt_run_restore "$1"; then gt_ks_ensure khoi_phuc_loi; gt_pause_clear; gt_state_set GT_PHASE A_FAIL
    khan "$1 VA KHOI PHUC LOI => GIU run/KILL_SWITCH. Kiem: bash $GT_OPS/golive_monitor.sh ; BASE $A/$BASE"; fi
  gt_set_prod_chk mine
  if gl_postloop GT_CHK; then
    gt_release_and_push; rc=$?; gt_pause_clear
    gt_state_set GT_PHASE NONE; gt_state_set GT_CUR_MD5 "$CURMD5"
    [ "$rc" = 0 ] && { say "Da KHOI PHUC production (hau kiem DAT, PUSH ON)."; tg "[gridtest] pha A FAIL TS=$TS: $1 => da KHOI PHUC production (PUSH ON). Log $LOG" || :; exit 1; }
    khan "$1; da khoi phuc env production nhung PUSH khong ON / KS (rc=$rc). Kiem golive_monitor.sh"
  fi
  gt_ks_ensure khoi_phuc_hau_kiem_truot; gt_pause_clear; gt_state_set GT_PHASE A_FAIL
  khan "$1 VA hau kiem SAU KHOI PHUC TRUOT ($(echo "$RESULT" | grep '^FAIL\|^WAIT' | tr '\n' ' ' | cut -c1-200)) => GIU run/KILL_SWITCH"
}
gt_run_restart; rc=$?
if [ "$rc" = 3 ]; then gt_state_set GT_PHASE NONE
  say "KET QUA: TU_CHOI truoc khi dung bot: $(echo "$RS" | grep '^FAIL' | head -2 | tr '\n' ' ') - env/bot KHONG doi, KS cua minh da go"; exit 1; fi
[ "$rc" = 4 ] && do_restore "buoc doi env FAIL sau khi dung bot ($(echo "$RS" | grep '^FAIL' | head -2 | tr '\n' ' '))"
GTC_PCT=$GT_PCT_TEST; GTC_TOPK=$GT_TOPK_TEST; GTC_LEV=$GT_LEVELS_TEST; GTC_LEVLOG=$GT_LEVELS_LOG_TEST; GTC_KS=mine
gl_postloop GT_CHK || do_restore "hau kiem pha A TRUOT ($(echo "$RESULT" | grep '^FAIL\|^WAIT' | tr '\n' ' ' | cut -c1-200))"
gt_state_set GT_CUR_MD5 "$NEW"; gt_state_set GT_SINCE_A "$SINCE"; gt_state_set GT_SL_A "$SL"; gt_state_set GT_T_A "$(date +%s)"
gt_state_set GT_PHASE A
gt_watch_cron_install || do_restore "khong cai duoc cron gridtest_watch (phanh)"
WO=$(GT_WATCH_ONCE=1 bash "$GT_HERE/gridtest_watch.sh" 2>&1); echo "$WO" | sed 's/^/   watch: /' | tail -15
echo "$WO" | grep -q '^WATCH_OK' || do_restore "gridtest_watch chay thu KHONG OK (phanh khong hoat dong)"
gt_release_and_push; rc=$?
gt_pause_clear
case $rc in
  0) say "=== XONG PHA A: env test DANG HIEU LUC, PUSH ON, phanh cron 1'. Theo doi: bash $GT_HERE/gridtest_watch.sh ; du leg0 >= $GT_N_LEG0: DRY=0 bash $GT_HERE/gridtest_phase_b.sh"
     tg "[gridtest] PHA A BAT TS=$TS (pct=$GT_PCT_TEST K=$GT_TOPK_TEST DCA $GT_LEVELS_TEST), PUSH ON, phanh cron. Log $LOG" || :; exit 0 ;;
  1) khan "pha A: env test DA cai nhung con KILL_SWITCH KHAC (khong phai cua script) => bot KHONG mo lenh. Kiem; tra cau hinh: gridtest_off.sh" ;;
  *) khan "pha A: hau kiem DAT nhung KHONG thay PUSH ON / khong go duoc KS => da dat lai KS. Kiem golive_monitor.sh ; tra: gridtest_off.sh" ;;
esac
