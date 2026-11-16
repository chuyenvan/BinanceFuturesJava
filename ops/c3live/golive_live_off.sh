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
# [WAVE1c m1] pin NGOAI repo, kiem TRUOC khi source lib (lib khong tu chung nhan): HEAD repo chua script = 1 commit A1/MASTER
#   duyet trong A1_APPROVED_OPS (deploy/gates/A1_APPROVED_OPS.commit, 1 dong/commit, script CHI DOC) + thu muc script KHONG co sua chua commit.
# [OPS-MICRO 16/11, quyet dinh MASTER] live_off = lenh GIAM rui ro => FAIL-OPEN (cac script owner KHAC van TU CHOI nhu tren):
#   (1) MODE=drain (khong DRY=1): dat run/KILL_SWITCH la BUOC DAU TIEN, doc lap: TRUOC kiem pin m1 / manifest M5 / source lib / doc 242 /
#       YES / Telegram / log (khong gate, khong heartbeat, khong flock). Chi can ssh 242 (SSH_242 / APP_DIR mac dinh = golive_lib), thu 3 lan,
#       moi lan timeout LO_KS_TIMEOUT_S (60 s). KILL_SWITCH cua script khac (vd token "golive_micro_on <TS>") => GHI DE bang token drain
#       (ban cu => run/KILL_SWITCH.prev_<TS>) de script kia KHONG tu go duoc. Khong dat duoc => KHAN exit 2. Drain KHONG hoi YES nua.
#   (2) MOI MODE: lech pin m1 / thieu file pin / khong phai repo git / lech manifest M5 => CANH BAO TO (neu ly do + file lech)
#       + Telegram (neu duoc) + VAN CHAY. Telegram loi KHONG chan.
_OPS=$(cd "$(dirname "$0")" && pwd); _APO=${A1_APPROVED_OPS:-/home/ubuntu/claude_master/deploy/gates/A1_APPROVED_OPS.commit}; _PW=""
_HC=$(git -C "$_OPS" rev-parse --verify -q HEAD 2>/dev/null) || _PW="$_OPS khong phai repo git"
[ -n "$_PW" ] || { [ -f "$_APO" ] && grep -qE "^$_HC([[:space:]]|\$)" "$_APO"; } || _PW="HEAD $_HC CHUA duoc A1 duyet (khong co trong $_APO)"
[ -n "$_PW" ] || git -C "$_OPS" diff --quiet HEAD -- . 2>/dev/null || _PW="$_OPS co sua CHUA commit (git diff HEAD)"
_LO_TS=$(TZ=Asia/Ho_Chi_Minh date +%Y%m%d_%H%M%S); _KS=""; _KO=""
if [ "${MODE:-}" = drain ] && [ "${DRY:-0}" != 1 ]; then
  _KSSH=${SSH_242:-"ssh -p 2222 -o BatchMode=yes -o ConnectTimeout=20 -o ServerAliveInterval=10 -o ServerAliveCountMax=6 -i /home/ubuntu/.ssh/id_rsa_chuyennd root@103.157.218.242"}
  _KA=${APP_DIR:-/home/chuyennd/java/v_t_m}
  _KC="cd $_KA && { grep -q '^golive_live_off drain ' run/KILL_SWITCH 2>/dev/null || { { [ ! -e run/KILL_SWITCH ] || cp -p run/KILL_SWITCH run/KILL_SWITCH.prev_$_LO_TS; } && echo 'golive_live_off drain $_LO_TS' > run/KILL_SWITCH.tmp_$_LO_TS && mv -f run/KILL_SWITCH.tmp_$_LO_TS run/KILL_SWITCH; }; } && [ -e run/KILL_SWITCH ] && echo KS_OK"
  for _i in 1 2 3; do
    _KO=$(timeout -k 5 "${LO_KS_TIMEOUT_S:-60}" $_KSSH "$_KC" < /dev/null 2>&1)
    echo "$_KO" | grep -qx KS_OK && { _KS=OK; break; }
    [ "$_i" -lt 3 ] && sleep "${SSH_RETRY_S:-10}"
  done
  if [ "$_KS" = OK ]; then echo "[golive_live_off $_LO_TS] BUOC 1 XONG: run/KILL_SWITCH DA DAT tren 242 (truoc moi kiem) - c3 DUNG MO MOI"
  else echo "!!!!!!!!!! [golive_live_off $_LO_TS] KHONG DAT DUOC run/KILL_SWITCH (3 lan): $(echo "$_KO" | tail -2 | tr '\n' ' ' | cut -c1-200)"; fi
fi
[ -z "$_PW" ] || echo "!!!!!!!!!! CANH BAO [m1] (golive_live_off VAN CHAY - lenh giam rui ro): $_PW"
. "$(cd "$(dirname "$0")" && pwd)/golive_lib.sh"
# [WAVE1b M5 -> OPS-MICRO] lech manifest => CANH BAO + VAN CHAY (chi rieng live_off)
if _MWO=$(gl_manifest_check "$0" 2>&1); then _MW=""; else
  _MW=$(printf '%s' "${_MWO:-gl_manifest_check loi (golive_lib thieu/hong?)}" | sed 's/TU CHOI \[M5\]: //; s/KHONG lam gi\./(live_off VAN CHAY)/')
  echo "!!!!!!!!!! CANH BAO [M5] (golive_live_off VAN CHAY): $_MW"
fi
MODE=${MODE:-}
DRY_CAPITAL=${DRY_CAPITAL:-10000}
gl_init golive_live_off
if [ -n "$_PW$_MW" ]; then
  say "!!!!!!!!!! CANH BAO: golive_live_off chay voi ban CHUA duoc pin/duyet - VAN CHAY (lenh giam rui ro, quyet dinh MASTER) !!!!!!!!!!"
  [ -n "$_PW" ] && say "!!! CANH BAO [m1]: $_PW"
  [ -n "$_MW" ] && say "!!! CANH BAO [M5]: $_MW"
  tg "[golive] CANH BAO live_off MODE=$MODE TS=$TS chay voi ban CHUA pin: ${_PW:+[m1] $_PW. }${_MW:+[M5] $_MW}" || say "!! Telegram canh bao KHONG gui duoc - VAN chay tiep"
fi
case "$MODE" in drain|undrain|dry) ;; *) die "MODE phai la drain | undrain | dry";; esac
# [OPS-MICRO] drain that: KILL_SWITCH DA dat o buoc 1 => phan con lai CHI thong tin (khong die truoc khi bao ket qua)
if [ "$MODE" = drain ] && [ "$DRY" != 1 ]; then
  if [ "$_KS" != OK ]; then
    say "KHAN: KHONG dat duoc run/KILL_SWITCH tren 242 (ssh?) - c3 CO THE VAN MO MOI. Chay lai NGAY: MODE=drain bash $0"
    tg "[golive] KHAN live_off drain TS=$TS: KHONG dat duoc run/KILL_SWITCH (ssh 242?). Log $LOG" || say "!! Telegram KHONG gui duoc"
    exit 2
  fi
  say "XONG: run/KILL_SWITCH DA DAT (buoc 1, truoc moi kiem): c3 dung mo moi (lan entry ke tiep), vi the c3 van duoc quan ly. KHONG restart."
  _BC="?"
  if ST=$(gl_state242 2>/dev/null) && echo "$ST" | grep -qx END_STATE; then
    echo "$ST" | grep -v '^END_STATE$' | sed 's/^/   242: /'; _BC=$(sv BOOK_CUM)
    [ "$(sv NPROC)" = 1 ] || say "!! so process bot = $(sv NPROC) (chi thong tin; KILL_SWITCH DA dat)"
    [ "$(sv ENV_LIVE_ADAPTER)" = live ] || say "INFO bot khong chay live (LIVE_ADAPTER=$(sv ENV_LIVE_ADAPTER)) - KILL_SWITCH dat van vo hai"
  else say "!! doc trang thai 242 loi (chi thong tin; KILL_SWITCH DA dat)"; fi
  say "Theo doi so c3 ve 0: golive_monitor.sh ; roi MODE=dry."
  tg "[golive] DRAIN TS=$TS: run/KILL_SWITCH dat, c3 dung mo moi ($_BC cum dang mo). Log $LOG" || say "!! Telegram KHONG gui duoc (KILL_SWITCH van DA dat)"
  exit 0
fi
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
if gl_rollback live live; then say "Da ROLLBACK xong (live, drain; adapter=live da kiem)."; tg "[golive] live_off FAIL TS=$TS: $WHY => ROLLBACK ve live (drain) XONG. Log $LOG"; exit 1; fi
M="ROLLBACK LOI — PAUSE còn; kiem golive_monitor.sh; env backup $A/conf/env.sh.bak_golive_live_off_$TS"
say "KHAN: $M"; tg "[golive] KHAN TS=$TS live_off TRUOT ($WHY) VA $M | log $LOG"; exit 2
