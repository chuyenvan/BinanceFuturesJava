#!/usr/bin/env bash
# =============================================================================
# golive_micro_on.sh — [V12 R4o] DRY -> MICRO-LIVE tren TAI KHOAN CHINH (GOLIVE_SCENARIO ADD1 §2-3). Chay tren ORACLE (owner):
#   DRY=1 bash ~/claude_master/v12/c3live/ops/c3live/golive_micro_on.sh   # chi kiem + in ke hoach, KHONG ghi gi
#   bash ~/claude_master/v12/c3live/ops/c3live/golive_micro_on.sh         # go YES (khung :10-:44)
# Kiem: file gate G-MICRO (jar_md5 = jar dang chay), dry r4n dang chay, latch NONE, khong run/KILL_SWITCH, key file, LEGACY moi,
#   RAM/dia, khong canary/soak/PAUSE. Lam: env +LIVE_ADAPTER=live C3_CAPITAL=1000 SHADOW_NO_PUSH=false LIVE_ENTRY_ENABLED=true
#   LIVE_C3_KEYS_FILE (+C11=1 neu thieu) ; PAUSE token ; stop ; so/trang thai DRY (so, equity c3, dinh + latch kill-switch nhan dry)
#   doi ten .dry_<TS> => live bat dau SACH (= reset dinh A40/C6 co chu dich; latch dry NONE nen khong mat gi) ; start ;
#   hau kiem: env process, "khoi dong adapter=LIVE ... c3_capital=1000", PUSH=ON, user stream da ket noi, doi chieu khoi dong ok,
#   LEGACY managed = truoc (LEGACY khong bi dung), latch NONE, 0 KHAN, runtime tao duoc.
# Hau kiem TRUOT: c3 CHUA co lenh nao (so 0 cum, 0 dong [C3-LIVE-EXEC]) => ROLLBACK ve dry (env + so dry tra lai);
#   c3 DA co lenh => KHONG ve dry (vi the that se mo coi) — dat run/KILL_SWITCH (dung mo moi) + KHAN, exit 2.
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
say "--- se doi ten (.dry_$TS) neu co: $GL_STATE_FILES ; so dry hien co $(sv BOOK_CUM) cum (khong vao live)"
say "--- hau kiem: adapter=LIVE c3_capital=$MICRO_CAPITAL PUSH=ON stream ket noi, recon ok, LEGACY managed $L0, latch NONE, 0 KHAN"
[ "$DRY" = 1 ] && { say "DRY=1: dung o day, KHONG ghi gi len 242. (DRY PASS)"; exit 0; }
gl_time
gl_yes "BAT MICRO-LIVE: lenh THAT tren tai khoan chinh (C3_CAPITAL=$MICRO_CAPITAL). LEGACY ngung quan ly ~30-60 s."
trap 'say "BI DUNG (tin hieu) — kiem: bash $(cd "$(dirname "$0")" && pwd)/golive_monitor.sh"; gl_pause_clear >/dev/null 2>&1; exit 130' INT TERM HUP
gl_restart "$ENV_ADD" "$GL_STATE_FILES" dry
if echo "$RS" | grep -q '^FAIL'; then
  echo "$RS" | grep -q '^OK da_stop' || { gl_pause_clear >/dev/null 2>&1; die "buoc env/stop FAIL truoc khi dung bot (env da khoi phuc neu da sua)"; }
fi
CHK() { gl_chk_common "$SL" "$L0" '
envk LIVE_ADAPTER=live; envk C3_CAPITAL='"$MICRO_CAPITAL"'; envk SHADOW_NO_PUSH=false; envk LIVE_ENTRY_ENABLED=true; envk LIVE_SEED_EXCLUDE_DECISION_MIN=1
[ "$(T "khoi dong adapter=LIVE")" -ge 1 ] && echo "OK adapter_LIVE" || echo "WAIT adapter_LIVE"
[ "$(tail -n +$SL $L | grep -a "khoi dong adapter=LIVE" | grep -acE "c3_capital='"$MICRO_CAPITAL"'(\.0)?( |$)")" -ge 1 ] && echo "OK c3_capital='"$MICRO_CAPITAL"'" || echo "WAIT c3_capital"
[ "$(T "PUSH=ON")" -ge 1 ] && echo "OK PUSH_ON" || echo "WAIT PUSH_ON"
[ "$(T "C3-LIVE-STREAM\] da ket noi")" -ge 1 ] && echo "OK user_stream" || echo "WAIT user_stream"
LS=$(tail -n +$SL $L | grep -a "LEGACY tren tai khoan chinh:" | tail -1 | grep -aoE "chinh: [0-9]+" | awk "{print \$2}")
[ -z "$LS" ] && echo "WAIT scope_LEGACY" || { [ "$LS" = "$L0" ] && echo "OK scope_LEGACY=$LS" || echo "WARN scope_LEGACY=$LS khac $L0"; }'; }
if ! echo "$RS" | grep -q '^FAIL' && gl_postloop CHK; then
  trap - INT TERM HUP
  gl_pause_clear >/dev/null || say "PAUSE con (ssh?) — tu go sau ${WD_PAUSE_MAX_S}s"
  say "=== XONG: MICRO-LIVE c3 C3_CAPITAL=$MICRO_CAPITAL. Theo doi: bash $(cd "$(dirname "$0")" && pwd)/golive_monitor.sh"
  say "Dung khan: MODE=drain bash $(cd "$(dirname "$0")" && pwd)/golive_live_off.sh  (dung mo moi, giu quan ly vi the)"
  tg "[golive] MICRO-LIVE BAT TS=$TS C3_CAPITAL=$MICRO_CAPITAL. Log $LOG"
  exit 0
fi
WHY=$(echo "${RESULT:-$RS}" | grep '^FAIL\|^WAIT' | tr '\n' ' ' | cut -c1-200)
BC=$(echo "$RESULT" | sed -n 's/.*BOOK_CUM=\([0-9]*\).*/\1/p' | tail -1); CE=$(echo "$RESULT" | sed -n 's/.*C3EXEC=\([0-9]*\).*/\1/p' | tail -1)
if [ "${BC:-0}" = 0 ] && [ "${CE:-0}" = 0 ]; then
  say "hau kiem TRUOT ($WHY); c3 CHUA co lenh => ROLLBACK ve DRY"
  if gl_rollback dry; then
    say "Da ROLLBACK xong: dry chay lai nhu truoc."; tg "[golive] micro_on FAIL TS=$TS: $WHY => ROLLBACK ve dry XONG. Log $LOG"; exit 1
  fi
  M="ROLLBACK LOI — PAUSE còn; kiem tay golive_monitor.sh; env backup $A/conf/env.sh.bak_golive_micro_on_$TS"
else
  s242 "cd $A && echo 'golive_micro_on $TS hau kiem truot' > run/KILL_SWITCH" && say "DA DAT run/KILL_SWITCH (dung mo moi; vi the c3 van duoc quan ly)"
  gl_pause_clear >/dev/null 2>&1
  M="c3 DA co lenh (so $BC cum, $CE dong EXEC) => KHONG ve dry. Dung mo moi bang run/KILL_SWITCH. Owner/MASTER xem: golive_monitor.sh; khi c3 phang: MODE=dry golive_live_off.sh"
fi
say "KHAN: micro_on hau kiem TRUOT ($WHY). $M"; tg "[golive] KHAN TS=$TS micro_on TRUOT ($WHY). $M | log $LOG"; exit 2
