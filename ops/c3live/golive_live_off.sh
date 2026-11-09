#!/usr/bin/env bash
# =============================================================================
# golive_live_off.sh — [V12 R4o] LIVE -> DRY an toan (GOLIVE_SCENARIO ADD1 §6). Chay tren ORACLE (owner):
#   MODE=drain   bash .../golive_live_off.sh  # dat run/KILL_SWITCH: DUNG MO MOI ngay (khong restart); vi the c3 van duoc quan ly
#                                             #   (trailing/stop/time-stop) toi khi dong. Khong chot gio (khan cap duoc).
#   MODE=undrain bash .../golive_live_off.sh  # go run/KILL_SWITCH (mo lai push) — chi khi co chu dich
#   MODE=dry     bash .../golive_live_off.sh  # khi c3 PHANG: env ve dry, so/trang thai live doi ten .live_<TS>, restart (khung :10-:44)
#   (moi MODE: DRY=1 chi kiem)
# MODE=dry TU CHOI khi: chua drain (khong co run/KILL_SWITCH), so c3 con cum, san con lenh/algo cid 'c3', key/API loi,
#   [R4q] san con vi the tren symbol c3 tung giao dich (ledger live) hoac vi the NGOAI danh sach LEGACY (log [LEGACY] managed moi);
#   sau cat LEGACY (managed 0) => moi vi the. Symbol MERGED cu chi con LEGACY: owner xac nhan LIVE_OFF_ACK_SYMS=SYM1,SYM2.
#   KHONG BAO GIO doi adapter khi c3 con vi the (vi the that se mo coi). Can dong gap: owner dong tay vi the c3 tren UI roi MODE=dry.
# MODE=dry hau kiem TRUOT => rollback ve live (env + so live tra lai; run/KILL_SWITCH van con => khong mo moi).
# [ADD4] C3_ACCOUNT=SUB (mac dinh): tk con chi co c3 => MODE=dry doi bot dung key tk con + tk con 0 vi the + 0 lenh/algo (moi cid);
#   KHONG dung log/danh sach LEGACY (LEGACY o tk chinh, chi ghi log). MAIN: nhu R4q.
# [A1 ADD4 C-1] MODE=dry XONG => go co monitor (cron monitor thoat ngay); undrain => dam bao co; drain giu co.
# =============================================================================
set -uo pipefail
. "$(cd "$(dirname "$0")" && pwd)/golive_lib.sh"
MODE=${MODE:-}
DRY_CAPITAL=${DRY_CAPITAL:-10000}
gl_init golive_live_off
case "$MODE" in drain|undrain|dry) ;; *) die "MODE phai la drain | undrain | dry";; esac
gl_read_state
echo "$ST" | grep -v '^END_STATE$' | sed 's/^/   242: /'
[ "$(sv NPROC)" = 1 ] || die "so process bot = $(sv NPROC)"
[ "$(sv ENV_LIVE_ADAPTER)" = live ] || die "bot KHONG chay live (LIVE_ADAPTER=$(sv ENV_LIVE_ADAPTER)) — khong co gi de tat"
if [ "$MODE" = drain ]; then
  [ "$(sv KILLSW_FILE)" = 1 ] && { say "run/KILL_SWITCH DA CO — push da dong. Khong lam gi."; exit 0; }
  say "--- se tao $A/run/KILL_SWITCH: dung mo moi c3 ngay (lan entry ke tiep), vi the c3 ($(sv BOOK_CUM) cum) van duoc quan ly"
  [ "$DRY" = 1 ] && { say "DRY=1: KHONG ghi gi. (DRY PASS)"; exit 0; }
  gl_yes "DRAIN c3_live (dung mo moi)."
  s242 "cd $A && echo 'golive_live_off drain $TS' > run/KILL_SWITCH && [ -e run/KILL_SWITCH ]" || die "khong tao duoc run/KILL_SWITCH"
  say "XONG: run/KILL_SWITCH da dat. Theo doi so c3 ve 0: golive_monitor.sh ; roi MODE=dry."
  tg "[golive] DRAIN TS=$TS: run/KILL_SWITCH dat, c3 dung mo moi ($(sv BOOK_CUM) cum dang mo). Log $LOG"; exit 0
fi
if [ "$MODE" = undrain ]; then
  [ "$(sv KILLSW_FILE)" = 0 ] && { say "khong co run/KILL_SWITCH. Khong lam gi."; exit 0; }
  [ "$(sv LATCH)" = NONE ] || [ "$(sv LATCH)" = NOFILE ] || die "latch kill-switch=$(sv LATCH) — xu ly latch truoc (killsw_reset.sh)"
  [ "$DRY" = 1 ] && { say "DRY=1: KHONG ghi gi. (DRY PASS)"; exit 0; }
  gl_yes "UNDRAIN: go run/KILL_SWITCH, c3_live MO LAI lenh moi."
  s242 "cd $A && mv -f run/KILL_SWITCH run/KILL_SWITCH.off_$TS && [ ! -e run/KILL_SWITCH ]" || die "khong go duoc run/KILL_SWITCH"
  gl_mon_flag_set; say "XONG: push mo lai."; tg "[golive] UNDRAIN TS=$TS: run/KILL_SWITCH go, c3 mo lai lenh moi. Log $LOG"; exit 0
fi
# ---------------------------------------------------------------- MODE=dry
F=0; chk() { if eval "$2"; then say "OK   $1"; else say "FAIL $1"; F=1; fi; }
chk "da drain (run/KILL_SWITCH co)" "[ '$(sv KILLSW_FILE)' = 1 ]"
chk "so c3 = 0 cum" "[ '$(sv BOOK_CUM)' = 0 ]"
chk "khong PAUSE watchdog" "[ '$(sv PAUSE | cut -c1)' = 0 ]"
API=$(gl_api242 scope) || die "ssh toi 242 loi"
echo "$API" | grep -v '^END_API$' | sed 's/^/   san: /'
chk "doc san duoc (key c3)" "echo \"\$API\" | grep -qx END_API && ! echo \"\$API\" | grep -q '^ERR=' && [ '$(av API_OK)' = 1 ]"
chk "san: 0 lenh c3 + 0 algo c3 dang mo" "[ '$(av ORD_C3)' = 0 ] && [ '$(av ALGO_C3)' = 0 ]"
if [ "$C3_ACCOUNT" = SUB ]; then
  # [ADD4] tk con chi co c3: phang <=> 0 vi the + 0 lenh/algo tren tk con (thu ngoai c3 => owner xu ly truoc, §4); LEGACY chi ghi log
  chk "bot dung key tk con (LIVE_C3_KEYS_FILE=$KEYS_FILE; co: $(sv ENV_LIVE_C3_KEYS_FILE))" "[ '$(sv ENV_LIVE_C3_KEYS_FILE)' = '$KEYS_FILE' ]"
  chk "san tk con: 0 vi the (co $(av POS_TOTAL): $(av POS_LIST))" "[ '$(av POS_TOTAL)' = 0 ]"
  chk "san tk con: 0 lenh / algo moi cid (co $(av ORD_TOTAL)/$(av ALGO_TOTAL))" "[ '$(av ORD_TOTAL)' = 0 ] && [ '$(av ALGO_TOTAL)' = 0 ]"
  say "INFO LEGACY managed=$(sv LEGACY_N) (tk chinh) — chi ghi log"
  L0=SKIP
else
# [R4q MIN-2] vi the c3 tren san = 0
LSY=",$(sv LEGACY_SYMS),"; LGY=",$(sv LEDGER_SYMS),"; ACK=",${LIVE_OFF_ACK_SYMS:-},"; LA=$(sv LEGACY_AGE)
chk "log [LEGACY] managed moi (${LA}s <= 600) de tach vi the LEGACY" "[ '$LA' -ge 0 ] && [ '$LA' -le 600 ] 2>/dev/null"
UNK=""; C3P=""
for x in $(av POS_LIST | tr ',' ' '); do
  case "$ACK" in *",$x,"*) continue;; esac
  case "$LGY" in *",$x,"*) C3P="$C3P $x"; continue;; esac
  case "$LSY" in *",$x,"*) ;; *) UNK="$UNK $x";; esac
done
chk "san: 0 vi the tren symbol c3 tung giao dich${C3P:+ — CO:$C3P (neu chi con LEGACY: LIVE_OFF_ACK_SYMS=...)}" "[ -z '$C3P' ]"
chk "san: 0 vi the ngoai danh sach LEGACY${UNK:+ — CO:$UNK}" "[ -z '$UNK' ]"
L0=$(sv LEGACY_N)
fi
[ "$F" = 0 ] || die "chua phang / kiem co FAIL (xem tren) — KHONG doi adapter"
ENV_ADD="# [v1.2 R4o golive_live_off $TS] LIVE -> DRY (c3 phang)
export LIVE_ADAPTER=dry
export SHADOW_NO_PUSH=true
export LIVE_ENTRY_ENABLED=false
export C3_CAPITAL=$DRY_CAPITAL"
say "--- se THEM vao $A/conf/env.sh:"; echo "$ENV_ADD" | sed 's/^/   + /'
say "--- se doi ten (.live_$TS): $GL_STATE_FILES ; run/KILL_SWITCH giu nguyen (dry khong doc; lan micro_on sau phai go co chu dich)"
[ "$DRY" = 1 ] && { say "DRY=1: dung o day, KHONG ghi gi. (DRY PASS)"; exit 0; }
gl_time
gl_yes "LIVE -> DRY (c3 phang)."
trap 'say "BI DUNG (tin hieu) — kiem golive_monitor.sh"; gl_pause_clear >/dev/null 2>&1; exit 130' INT TERM HUP
gl_restart "$ENV_ADD" "$GL_STATE_FILES" live
if echo "$RS" | grep -q '^FAIL'; then
  echo "$RS" | grep -q '^OK da_stop' || { gl_pause_clear >/dev/null 2>&1; die "buoc env/stop FAIL truoc khi dung bot"; }
fi
CHK() { gl_chk_common "$SL" "$L0" '
envk LIVE_ADAPTER=dry; envk SHADOW_NO_PUSH=true; envk C3_CAPITAL='"$DRY_CAPITAL"'
[ "$(T "khoi dong adapter=DRY")" -ge 1 ] && echo "OK adapter_DRY" || echo "WAIT adapter_DRY"'; }
if ! echo "$RS" | grep -q '^FAIL' && gl_postloop CHK; then
  trap - INT TERM HUP
  gl_pause_clear >/dev/null || say "PAUSE con (ssh?) — tu go sau ${WD_PAUSE_MAX_S}s"
  gl_mon_flag_clear; say "=== XONG: c3_live ve DRY. So live: run/*.live_$TS"; tg "[golive] LIVE -> DRY XONG TS=$TS. Log $LOG"; exit 0
fi
WHY=$(echo "${RESULT:-$RS}" | grep '^FAIL\|^WAIT' | tr '\n' ' ' | cut -c1-200)
say "hau kiem TRUOT ($WHY) => ROLLBACK ve live (KILL_SWITCH van dat => khong mo moi)"
if gl_rollback live; then say "Da ROLLBACK xong (live, drain)."; tg "[golive] live_off FAIL TS=$TS: $WHY => ROLLBACK ve live (drain) XONG. Log $LOG"; exit 1; fi
M="ROLLBACK LOI — PAUSE còn; kiem golive_monitor.sh; env backup $A/conf/env.sh.bak_golive_live_off_$TS"
say "KHAN: $M"; tg "[golive] KHAN TS=$TS live_off TRUOT ($WHY) VA $M | log $LOG"; exit 2
