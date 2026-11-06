#!/usr/bin/env bash
# =============================================================================
# golive_micro_on.sh — [V12 R4o/R4q] DRY -> MICRO-LIVE tren TAI KHOAN CHINH (GOLIVE_SCENARIO ADD1 §2-3). Chay tren ORACLE (owner):
#   DRY=1 bash ~/claude_master/v12/c3live/ops/c3live/golive_micro_on.sh   # chi kiem + in ke hoach, KHONG ghi gi
#   bash ~/claude_master/v12/c3live/ops/c3live/golive_micro_on.sh         # go YES (khung :10-:44)
# Kiem: file gate G-MICRO (jar_md5 = jar dang chay), dry dang chay, latch NONE, khong run/KILL_SWITCH, key file, LEGACY moi,
#   RAM/dia, khong canary/soak/PAUSE; [R4q] doc san (chi doc) TRUOC: vi the + 0 lenh/algo c3 => chu ky vi the.
# Lam: env +LIVE_ADAPTER=live C3_CAPITAL=1000 SHADOW_NO_PUSH=false LIVE_ENTRY_ENABLED=true LIVE_C3_KEYS_FILE (+C11=1 neu thieu);
#   PAUSE token; [R4q MAJ-1] dat run/KILL_SWITCH (token) TRUOC khi dung bot => JVM live len KHONG mo lenh moi; stop; so/trang thai DRY
#   doi ten .dry_<TS> (live bat dau SACH); start; hau kiem (env, adapter=LIVE c3_capital, PUSH=OFF vi KILL_SWITCH, stream, recon,
#   LEGACY, latch NONE, 0 KHAN, runtime); DAT => go KILL_SWITCH cua minh => doi log "PUSH doi trang thai -> ON".
# Hau kiem TRUOT: doc LAI 242 ngay luc quyet (so c3 + audit lenh [C3-LIVE-ORDER] + san: lenh/algo c3, chu ky vi the):
#   CHAC CHAN 0 lenh c3 => ROLLBACK ve dry (env + so dry tra lai, KILL_SWITCH cua minh go);
#   co dau hieu / doc loi / khong chac => coi nhu DA co lenh: GIU run/KILL_SWITCH (dung mo moi) + KHAN, KHONG ve dry, exit 2.
# Ma thoat: 0 XONG | 1 DUNG/da rollback | 2 can owner/MASTER.
# =============================================================================
set -uo pipefail
. "$(cd "$(dirname "$0")" && pwd)/golive_lib.sh"
MICRO_CAPITAL=${MICRO_CAPITAL:-1000}
gl_init golive_micro_on
G=$GATE_DIR/GOLIVE_GATE_MICRO.ok
GR=$(gl_gate "$G"); echo "$GR"; echo "$GR" | grep -q '^OK' || die "chua co cong G-MICRO hop le (MASTER tao $G voi jar_md5=$NJ_MD5)"
gl_read_state
echo "$ST" | grep -v '^END_STATE$' | sed 's/^/   242: /'
F=0; chk() { if eval "$2"; then say "OK   $1"; else say "FAIL $1"; F=1; fi; }
chk "1 process bot" "[ '$(sv NPROC)' = 1 ]"
chk "jar dang chay = pin $NJ_MD5" "[ '$(sv JAR_MD5)' = '$NJ_MD5' ]"
chk "dang chay c3_live DRY (env process + env.sh)" "[ '$(sv ENV_LIVE_PROFILE)' = c3_live ] && [ '$(sv ENV_LIVE_ADAPTER)' = dry ] && [ '$(sv ENVSH_LIVE_ADAPTER)' = dry ]"
chk "LIVE_KILLSW_MODE=act" "[ '$(sv ENV_LIVE_KILLSW_MODE)' = act ]"
chk "latch kill-switch NONE (khac => owner xem + DRY=0 bash ops/killsw_reset.sh truoc)" "[ '$(sv LATCH)' = NONE ] || [ '$(sv LATCH)' = NOFILE ]"
chk "khong co run/KILL_SWITCH (co => xoa co chu dich truoc)" "[ '$(sv KILLSW_FILE)' = 0 ]"
chk "file key $KEYS_FILE (600, 2 dong)" "[ '$(sv KEYS_OK)' = 1 ]"
chk "khong PAUSE watchdog" "[ '$(sv PAUSE | cut -c1)' = 0 ]"
chk "khong canary/soak" "[ '$(sv CANARY_SOAK)' = 0 ]"
chk "MemAvailable $(sv MEM) >= $MIN_MEM_MB MB" "[ '$(sv MEM)' -ge $MIN_MEM_MB ] 2>/dev/null"
chk "dia trong >= 1 GB" "[ '$(sv DISK_K)' -gt 1048576 ] 2>/dev/null"
L0=$(sv LEGACY_N)
chk "LEGACY managed doc duoc ($L0), moi ($(sv LEGACY_AGE) s <= 600)" "[ -n '$L0' ] && [ '$(sv LEGACY_AGE)' -ge 0 ] && [ '$(sv LEGACY_AGE)' -le 600 ] 2>/dev/null"
[ "$F" = 0 ] || die "kiem truoc co muc FAIL (xem tren)"
ENV_ADD="# [v1.2 R4o golive_micro_on $TS] MICRO-LIVE tai khoan chinh (GOLIVE_SCENARIO ADD1)
export LIVE_ADAPTER=live
export C3_CAPITAL=$MICRO_CAPITAL
export SHADOW_NO_PUSH=false
export LIVE_ENTRY_ENABLED=true
export LIVE_C3_KEYS_FILE=$KEYS_FILE"
[ "$(sv ENVSH_LIVE_SEED_EXCLUDE_DECISION_MIN)" = 1 ] || ENV_ADD="$ENV_ADD
export LIVE_SEED_EXCLUDE_DECISION_MIN=1"
say "--- se THEM vao $A/conf/env.sh:"; echo "$ENV_ADD" | sed 's/^/   + /'
say "--- se dat run/KILL_SWITCH (token golive_micro_on $TS) TRUOC khi dung bot; chi go sau hau kiem DAT"
say "--- se doi ten (.dry_$TS) neu co: $GL_STATE_FILES ; so dry hien co $(sv BOOK_CUM) cum (khong vao live)"
say "--- hau kiem: adapter=LIVE c3_capital=$MICRO_CAPITAL PUSH=OFF(KILL_SWITCH) stream, recon ok, LEGACY $L0, latch NONE, 0 KHAN => go KILL_SWITCH => PUSH ON"
[ "$DRY" = 1 ] && { say "DRY=1: dung o day, KHONG ghi gi len 242. (DRY PASS)"; exit 0; }
gl_time
gl_yes "BAT MICRO-LIVE: lenh THAT tren tai khoan chinh (C3_CAPITAL=$MICRO_CAPITAL). LEGACY ngung quan ly ~30-60 s."
# [R4q MAJ-1] chup san TRUOC (chi doc): khong doc duoc => khong doi gi
API=$(gl_api242 scope) || die "ssh toi 242 loi (doc san truoc)"
echo "$API" | grep -E '^(KEY_SHA8|POS_TOTAL|POS_SIG|ORD_C3|ALGO_C3|API_OK|ERR)' | sed 's/^/   san truoc: /'
echo "$API" | grep -qx END_API && ! echo "$API" | grep -q '^ERR' && [ "$(av API_OK)" = 1 ] || die "khong doc duoc san bang key c3 (khong doi gi)"
[ "$(av ORD_C3)" = 0 ] && [ "$(av ALGO_C3)" = 0 ] || die "san CON lenh/algo c3 truoc khi bat live (ORD_C3=$(av ORD_C3) ALGO_C3=$(av ALGO_C3)) — xu ly truoc"
SIG0=$(av POS_SIG); [ -n "$SIG0" ] || die "khong co chu ky vi the san"
trap 'say "BI DUNG (tin hieu) — kiem: bash $(cd "$(dirname "$0")" && pwd)/golive_monitor.sh"; gl_pause_clear >/dev/null 2>&1; exit 130' INT TERM HUP
gl_restart "$ENV_ADD" "$GL_STATE_FILES" dry 1
if echo "$RS" | grep -q '^FAIL'; then
  echo "$RS" | grep -q '^OK da_stop' || { gl_pause_clear >/dev/null 2>&1; die "buoc env/KILL_SWITCH/stop FAIL truoc khi dung bot (env + KILL_SWITCH da go neu da dat)"; }
fi
CHK() { gl_chk_common "$SL" "$L0" '
envk LIVE_ADAPTER=live; envk C3_CAPITAL='"$MICRO_CAPITAL"'; envk SHADOW_NO_PUSH=false; envk LIVE_ENTRY_ENABLED=true; envk LIVE_SEED_EXCLUDE_DECISION_MIN=1
[ "$(T "khoi dong adapter=LIVE")" -ge 1 ] && echo "OK adapter_LIVE" || echo "WAIT adapter_LIVE"
[ "$(tail -n +$SL $L | grep -a "khoi dong adapter=LIVE" | grep -acE "c3_capital='"$MICRO_CAPITAL"'(\.0)?( |$)")" -ge 1 ] && echo "OK c3_capital='"$MICRO_CAPITAL"'" || echo "WAIT c3_capital"
grep -q "^golive_micro_on '"$TS"' " run/KILL_SWITCH 2>/dev/null && echo "OK KILL_SWITCH_con (chua mo lenh moi)" || echo "FAIL KILL_SWITCH_cua_script_mat"
[ "$(T "PUSH=ON")" = 0 ] && echo "OK chua_PUSH_ON" || echo "FAIL PUSH_ON_khi_con_KILL_SWITCH"
[ "$(T "C3-LIVE-STREAM\] da ket noi")" -ge 1 ] && echo "OK user_stream" || echo "WAIT user_stream"
LS=$(tail -n +$SL $L | grep -a "LEGACY tren tai khoan chinh:" | tail -1 | grep -aoE "chinh: [0-9]+" | awk "{print \$2}")
[ -z "$LS" ] && echo "WAIT scope_LEGACY" || { if [ "$LS" = "$L0" ]; then echo "OK scope_LEGACY=$LS"; elif [ "$LS" -lt "$L0" ] 2>/dev/null; then echo "WARN scope_LEGACY=$LS < truoc stop $L0 (dong tu nhien)"; else echo "FAIL scope_LEGACY=$LS > truoc stop $L0 (TANG)"; fi; }'; }
if ! echo "$RS" | grep -q '^FAIL' && gl_postloop CHK; then
  # [R4q MAJ-1] hau kiem DAT => go KILL_SWITCH CUA MINH => cho JVM bao PUSH ON
  if s242 "cd $A && grep -q '^golive_micro_on $TS ' run/KILL_SWITCH && mv -f run/KILL_SWITCH run/KILL_SWITCH.ok_$TS && [ ! -e run/KILL_SWITCH ]"; then
    say "OK go run/KILL_SWITCH (hau kiem DAT) — cho PUSH ON"
    PON=0
    for r in $(seq 1 "$POST_ROUNDS"); do
      sleep "$POST_WAIT_S"
      n=$(s242 "cd $A && tail -n +$SL logs/full.log 2>/dev/null | grep -ac 'PUSH doi trang thai -> ON'") || n=x
      [ "$n" != x ] && [ "$n" -ge 1 ] 2>/dev/null && { PON=1; break; }
    done
    if [ "$PON" = 1 ]; then
      trap - INT TERM HUP
      gl_pause_clear >/dev/null || say "PAUSE con (ssh?) — tu go sau ${WD_PAUSE_MAX_S}s"
      say "=== XONG: MICRO-LIVE c3 C3_CAPITAL=$MICRO_CAPITAL (PUSH ON). Theo doi: bash $(cd "$(dirname "$0")" && pwd)/golive_monitor.sh"
      say "Dung khan: MODE=drain bash $(cd "$(dirname "$0")" && pwd)/golive_live_off.sh  (dung mo moi, giu quan ly vi the)"
      tg "[golive] MICRO-LIVE BAT TS=$TS C3_CAPITAL=$MICRO_CAPITAL. Log $LOG"
      exit 0
    fi
    s242 "cd $A && echo 'golive_micro_on $TS push_khong_ON' > run/KILL_SWITCH" && say "DAT LAI run/KILL_SWITCH"
    gl_pause_clear >/dev/null 2>&1
    M="hau kiem DAT nhung KHONG thay 'PUSH doi trang thai -> ON' sau khi go KILL_SWITCH => DAT LAI KILL_SWITCH (an toan, khong mo moi). Owner/MASTER kiem golive_monitor.sh"
  else
    gl_pause_clear >/dev/null 2>&1
    M="hau kiem DAT nhung KHONG go duoc run/KILL_SWITCH (ssh/token) => bot live NHUNG khong mo moi (an toan). Kiem golive_monitor.sh; go: MODE=undrain golive_live_off.sh"
  fi
  say "KHAN: $M"; tg "[golive] KHAN TS=$TS micro_on: $M | log $LOG"; exit 2
fi
WHY=$(echo "${RESULT:-$RS}" | grep '^FAIL\|^WAIT' | tr '\n' ' ' | cut -c1-200)
say "hau kiem TRUOT ($WHY) — doc LAI 242 + san ngay luc quyet:"
SEEN=$(gl_c3_seen "$SL" "$SIG0"); echo "$SEEN" | sed 's/^/   doc lai: /'
V=$(echo "$SEEN" | sed -n 's/^VERDICT=//p' | tail -1)
if [ "${V:-UNKNOWN}" = NONE ]; then
  say "CHAC CHAN c3 chua co lenh (so 0 cum, 0 audit lenh, san 0 lenh/algo c3, vi the khong doi) => ROLLBACK ve DRY"
  if gl_rollback dry; then
    say "Da ROLLBACK xong: dry chay lai nhu truoc."; tg "[golive] micro_on FAIL TS=$TS: $WHY => ROLLBACK ve dry XONG. Log $LOG"; exit 1
  fi
  M="ROLLBACK LOI — PAUSE con; kiem tay golive_monitor.sh; env backup $A/conf/env.sh.bak_golive_micro_on_$TS"
else
  s242 "cd $A && { [ -e run/KILL_SWITCH ] || echo 'golive_micro_on $TS truot' > run/KILL_SWITCH; } && [ -e run/KILL_SWITCH ]" \
    && say "run/KILL_SWITCH DANG DAT (dung mo moi; vi the c3 neu co van duoc quan ly)" || say "!! KHONG xac nhan duoc run/KILL_SWITCH (ssh?) — no da duoc dat TRUOC start"
  gl_pause_clear >/dev/null 2>&1
  M="c3 CO THE da co lenh / khong chac ($V) => KHONG ve dry, GIU run/KILL_SWITCH. Owner/MASTER xem: golive_monitor.sh; khi c3 phang: MODE=dry golive_live_off.sh"
fi
say "KHAN: micro_on hau kiem TRUOT ($WHY). $M"; tg "[golive] KHAN TS=$TS micro_on TRUOT ($WHY). $M | log $LOG"; exit 2
