#!/usr/bin/env bash
# =============================================================================
# dry_enable_grid_sizing.sh — [WAVE1 16/11 D-01] BAT 2 co sizing + DCA grid tren v_t_m DRY (KHONG doi jar, CHI env.sh + 1 restart).
#   $OPS = thu muc chua script nay (worktree A1 duyet: HEAD co trong deploy/gates/A1_APPROVED_OPS.commit; MASTER cap duong dan)
#   Owner chay tren ORACLE, 1 lenh:
#     DRY=1 bash $OPS/dry_enable_grid_sizing.sh   # chi kiem + in ke hoach, KHONG ghi gi
#     bash $OPS/dry_enable_grid_sizing.sh         # go YES (khung :10-:44, tranh 07/19h, 00:50-01:20, 12:50-13:20)
# Vi sao: env v_t_m THIEU LIVE_APPLY_GRID_RATIO=true + LIVE_DCA_GRID_ENABLED=true (code mac dinh TAT) => C3LiveEntry (duong lenh THAT,
#   dry lan live) size leg = managerBudget = von x 0,015 / 4 = 37,5 @10 000 (= 1/6 sim 225) va KHONG co leg DCA grid (DCA_OFF).
#   Bat 2 co => leg_i = von x F_BASE / sum(w) x w_i x SCALE = 225 @10 000 moi leg (leg0 + 3 bac DCA -50/-75/-90 %) = sim B0/A3.
# Lam (tai dung golive_lib.sh: gl_restart idempotent + PAUSE token watchdog + backup env.sh.bak_dry_enable_grid_sizing_<TS> 1 lan):
#   env.sh += 2 dong export; PAUSE watchdog (tu go sau WD_PAUSE_MAX_S); stop; start (so dry GIU NGUYEN, khong doi ten, khong KILL_SWITCH).
#   LEGACY (43 vi the THAT tk chinh, cung JVM) ngung quan ly ~30-60 s luc restart.
# Hau kiem (POST_ROUNDS x POST_WAIT_S): 1 process, md5 jar KHONG doi (= NJ_MD5 pin), process env 2 co =true + LIVE_ADAPTER=dry,
#   log JVM moi: "khoi dong adapter=DRY", [MINUTE-FIN] BAT, [LIVE-SIZING] LIVE_APPLY_GRID_RATIO=true, [LIVE-DCA-GRID] ...=true profileC3=true
#   ... applyRatio=true, recon khoi dong ok, latch NONE, 0 KHAN, 0 dong " ERROR ", LEGACY managed TANG = FAIL / GIAM = WARN ghi so truoc-sau
#   (LEGACY tu dong vi the, KHONG rollback) [WAVE1b M3]; [WAVE1b M2] process env C3_CAPITAL = truoc restart + token Telegram sha8 = TG_SHA8
#   (kiem ca TRUOC: process + env.sh; chi sha8, KHONG in token).
#   DAT => go PAUSE, luu START_MS JVM moi (~/claude_master/deploy/dry_grid_start_<TS>.txt), ghi smoke_start_ms vao
#   parity_v12w/gmicro_target.json (CHI khi file tro target_jar=r4u3fin + target_md5=NJ_MD5, nhu swap_v12_dry_jar.sh), REG_NAME=<ten>
#   => goi register_jar.sh (mac dinh KHONG: jar khong doi; in lenh cho MASTER). Ngay hom nay = XAM (doi cau hinh sizing).
#   TRUOT => ROLLBACK TU DONG: env.sh ve backup GOC cua TS + restart + KIEM adapter=dry + C3_CAPITAL cu that; loi => KHAN exit 2.
# Ma thoat: 0 XONG / da BAT tu truoc | 1 DUNG (khong doi gi) hoac da rollback OK | 2 KHAN (owner/MASTER xem ngay).
# Bien test: nhu golive_lib.sh + GMICRO_TARGET REG_JAR_SH REG_NAME TARGET_TAG
# =============================================================================
set -uo pipefail
# [WAVE1c m1] pin NGOAI repo, kiem TRUOC khi source lib (lib khong tu chung nhan): HEAD repo chua script = 1 commit A1/MASTER
#   duyet trong A1_APPROVED_OPS (deploy/gates/A1_APPROVED_OPS.commit, 1 dong/commit, script CHI DOC) + thu muc script KHONG co sua chua commit.
_OPS=$(cd "$(dirname "$0")" && pwd); _APO=${A1_APPROVED_OPS:-/home/ubuntu/claude_master/deploy/gates/A1_APPROVED_OPS.commit}; _PW=""
_HC=$(git -C "$_OPS" rev-parse --verify -q HEAD 2>/dev/null) || _PW="$_OPS khong phai repo git"
[ -n "$_PW" ] || { [ -f "$_APO" ] && grep -qE "^$_HC([[:space:]]|\$)" "$_APO"; } || _PW="HEAD $_HC CHUA duoc A1 duyet (khong co trong $_APO)"
[ -n "$_PW" ] || git -C "$_OPS" diff --quiet HEAD -- . 2>/dev/null || _PW="$_OPS co sua CHUA commit (git diff HEAD)"
[ -z "$_PW" ] || { echo "TU CHOI [m1]: $_PW - KHONG lam gi."; exit 1; }
. "$(cd "$(dirname "$0")" && pwd)/golive_lib.sh"
gl_manifest_check "$0" || exit 1   # [WAVE1b M5] script + lib + manifest khop md5 da commit, lech => TU CHOI truoc moi viec
GMICRO_TARGET=${GMICRO_TARGET:-/home/ubuntu/claude_master/parity_v12w/gmicro_target.json}
REG_JAR_SH=${REG_JAR_SH:-/home/ubuntu/claude_master/vz_e1_wt/research/parity_v12/sh/register_jar.sh}
NJ_PATH=${NJ_PATH:-/home/ubuntu/claude_master/v12/jar/binance-java-sdk-1.2.4.jar_v12_r4u3fin2}
TARGET_TAG=${TARGET_TAG:-r4u3fin}
REG_NAME=${REG_NAME:-}
TG_SHA8=${TG_SHA8:-bdee1480}   # [WAVE1b M2] sha8 token Telegram ky vong (= swap_v12_dry_jar / set_telegram_env_242)
gl_init dry_enable_grid_sizing
gl_read_state
echo "$ST" | grep -v '^END_STATE$' | grep -v '^KEYS_' | sed 's/^/   242: /'
F=0; chk() { if eval "$2"; then say "OK   $1"; else say "FAIL $1"; F=1; fi; }
chk "1 process bot" "[ '$(sv NPROC)' = 1 ]"
chk "jar dang chay = pin $NJ_MD5 (r4u3fin2)" "[ '$(sv JAR_MD5)' = '$NJ_MD5' ]"
chk "dang chay c3_live DRY (env process + env.sh) — script nay CHI cho DRY" "[ '$(sv ENV_LIVE_PROFILE)' = c3_live ] && [ '$(sv ENV_LIVE_ADAPTER)' = dry ] && [ '$(sv ENVSH_LIVE_ADAPTER)' = dry ]"
chk "khong co co micro/pilot ($GL_MON_FLAG)" "[ ! -e '$GL_MON_FLAG' ]"
chk "latch kill-switch NONE" "[ '$(sv LATCH)' = NONE ] || [ '$(sv LATCH)' = NOFILE ]"
chk "khong PAUSE watchdog" "[ '$(sv PAUSE | cut -c1)' = 0 ]"
chk "khong canary/soak" "[ '$(sv CANARY_SOAK)' = 0 ]"
chk "MemAvailable $(sv MEM) >= $MIN_MEM_MB MB" "[ '$(sv MEM)' -ge $MIN_MEM_MB ] 2>/dev/null"
chk "dia trong >= 1 GB" "[ '$(sv DISK_K)' -gt 1048576 ] 2>/dev/null"
L0=$(sv LEGACY_N)
chk "LEGACY managed doc duoc ($L0), moi ($(sv LEGACY_AGE) s <= 600)" "[ -n '$L0' ] && [ '$(sv LEGACY_AGE)' -ge 0 ] && [ '$(sv LEGACY_AGE)' -le 600 ] 2>/dev/null"
say "INFO ingestor md5=$(sv ING_MD5) (FIN pin $ING_FIN_MD5) — chi ghi log"
CAP=$(sv ENV_C3_CAPITAL); CAP=${CAP:-$(sv ENVSH_C3_CAPITAL)}
# [WAVE1b M2] restart KHONG duoc doi von: C3_CAPITAL process = env.sh (neu ca 2 co); token Telegram process + env.sh = TG_SHA8 (chi sha8)
chk "C3_CAPITAL process ($(sv ENV_C3_CAPITAL)) = env.sh ($(sv ENVSH_C3_CAPITAL)) — restart KHONG doi von" "[ -z '$(sv ENV_C3_CAPITAL)' ] || [ -z '$(sv ENVSH_C3_CAPITAL)' ] || [ '$(sv ENV_C3_CAPITAL)' = '$(sv ENVSH_C3_CAPITAL)' ]"
TGS=$(s242 "cd $A && P=\$(pgrep -f '$(gl_rx "$PROC_PAT")' | head -1); echo TGP=\$(tr '\0' '\n' < /proc/\$P/environ 2>/dev/null | sed -n 's/^TELEGRAM_BOT_TOKEN=//p' | tail -1 | tr -d '\n' | sha256sum | cut -c1-8); echo TGE=\$(bash -c '. conf/env.sh >/dev/null 2>&1; printf %s \"\$TELEGRAM_BOT_TOKEN\"' | sha256sum | cut -c1-8)")
TGP=$(echo "$TGS" | sed -n 's/^TGP=//p' | head -1); TGE=$(echo "$TGS" | sed -n 's/^TGE=//p' | head -1)
chk "token Telegram sha8: process $TGP + env.sh $TGE = $TG_SHA8 (khong in token)" "[ '$TGP' = '$TG_SHA8' ] && [ '$TGE' = '$TG_SHA8' ]"
if [ "$(sv ENVSH_LIVE_APPLY_GRID_RATIO)" = true ] && [ "$(sv ENVSH_LIVE_DCA_GRID_ENABLED)" = true ] \
   && [ "$(sv ENV_LIVE_APPLY_GRID_RATIO)" = true ] && [ "$(sv ENV_LIVE_DCA_GRID_ENABLED)" = true ]; then
  say "=== DA BAT tu truoc (env.sh + process env co 2 co = true) — KHONG doi gi."; exit 0
fi
ENV_ADD="# [WAVE1 D-01 dry_enable_grid_sizing $TS] size leg + DCA grid nhu sim (C3LiveEntry + so giay)"
[ "$(sv ENVSH_LIVE_APPLY_GRID_RATIO)" = true ] || ENV_ADD="$ENV_ADD
export LIVE_APPLY_GRID_RATIO=true"
[ "$(sv ENVSH_LIVE_DCA_GRID_ENABLED)" = true ] || ENV_ADD="$ENV_ADD
export LIVE_DCA_GRID_ENABLED=true"
say "--- [D-01] budget leg du kien SAU khi bat (C3_CAPITAL=$CAP; truoc: leg0 = von x F_BASE / sum(w), 0 leg DCA):"
D01=$(gl_d01_plan "${CAP:-10000}"); D01RC=$?; echo "$D01" | sed 's/^/   /'
chk "D-01 leg0 du kien >= $MIN_LEG_BUDGET" "[ '$D01RC' = 0 ]"
[ "$F" = 0 ] || die "kiem truoc co muc FAIL (xem tren)"
say "--- se THEM vao $A/conf/env.sh (backup GOC conf/env.sh.bak_dry_enable_grid_sizing_$TS, 1 lan):"; echo "$ENV_ADD" | sed 's/^/   + /'
say "--- se: PAUSE watchdog (token, tu go sau ${WD_PAUSE_MAX_S}s) -> stop -> start (so dry giu nguyen) -> hau kiem ${POST_ROUNDS}x${POST_WAIT_S}s"
say "--- hau kiem: 1 process, jar $NJ_MD5 khong doi, env 2 co, adapter=DRY, [MINUTE-FIN] BAT, [LIVE-SIZING]/[LIVE-DCA-GRID] BAT, recon ok, latch NONE, 0 KHAN, 0 ERROR, LEGACY >= $L0"
[ "$DRY" = 1 ] && { say "DRY=1: dung o day, KHONG ghi gi len 242. (DRY PASS)"; exit 0; }
gl_time
gl_yes "BAT sizing + DCA grid tren v_t_m DRY (restart 1 lan). LEGACY (43 vi the that, cung JVM) ngung quan ly ~30-60 s."
gl_time   # kiem lai sau YES
trap 'say "BI DUNG (tin hieu) — kiem: bash $GL_HERE/c3live_status.sh"; gl_pause_clear >/dev/null 2>&1; exit 130' INT TERM HUP
gl_restart "$ENV_ADD" "" none 0
if gl_restart_unknown; then
  M="restart: ssh dut, KHONG doc duoc trang thai that tren 242 => KHONG ket luan. Kiem: bash $GL_HERE/c3live_status.sh ; env backup GOC $A/conf/env.sh.bak_dry_enable_grid_sizing_$TS"
  say "KHAN: $M"; tg "[dry grid] KHAN TS=$TS: $M | log $LOG"; exit 2
fi
if echo "$RS" | grep -q '^FAIL' && ! echo "$RS" | grep -q '^OK da_stop'; then
  gl_pause_clear >/dev/null 2>&1
  say "DUNG: buoc env/stop FAIL TRUOC khi dung bot: $(echo "$RS" | grep '^FAIL' | head -2 | tr '\n' ' ')"
  say "KET QUA: TU_CHOI — env.sh da tra ve backup goc, bot dry KHONG bi dung. Log: $LOG"; exit 1
fi
# [WAVE1b M2] C3_CAPITAL KHONG doi so voi truoc restart + token Telegram process = TG_SHA8 (chi sha8, KHONG in token)
if [ -n "$CAP" ]; then CAP_CHK='
envk C3_CAPITAL='"$CAP"
else CAP_CHK='
echo "$E" | grep -q "^C3_CAPITAL=" && echo "FAIL C3_CAPITAL_xuat_hien_sau_restart (truoc: khong dat)" || echo "OK C3_CAPITAL_van_khong_dat"'
fi
TG_CHK='
S8=$(echo "$E" | sed -n "s/^TELEGRAM_BOT_TOKEN=//p" | tail -1 | tr -d "\n" | sha256sum | cut -c1-8); [ "$S8" = "'"$TG_SHA8"'" ] && echo "OK process_env_telegram_sha8=$S8" || echo "FAIL process_env_telegram_sha8=$S8 (ky vong '"$TG_SHA8"')"
'
XCHK='
envk LIVE_ADAPTER=dry
[ "$(md5sum < target/binance-java-sdk-1.2.4.jar | cut -c1-32)" = "'"$NJ_MD5"'" ] && echo "OK jar_khong_doi" || echo "FAIL jar_md5_doi"
[ "$(T "khoi dong adapter=DRY")" -ge 1 ] && echo "OK adapter_DRY" || echo "WAIT adapter_DRY"
[ "$(T "khoi dong adapter=LIVE")" = 0 ] || echo "FAIL adapter_LIVE_trong_log"
[ "$(T "\[MINUTE-FIN\] BAT")" -ge 1 ] && echo "OK MINUTE-FIN_BAT" || echo "WAIT MINUTE-FIN_BAT"
[ "$(T "\[MINUTE-FIN\] TAT")" = 0 ] || echo "FAIL MINUTE-FIN_TAT"
NE=$(tail -n +$SL $L 2>/dev/null | grep -ac " ERROR "); [ "$NE" = 0 ] && echo "OK 0_ERROR" || echo "FAIL ${NE}_dong_ERROR: $(tail -n +$SL $L | grep -a " ERROR " | head -1 | cut -c1-140)"
LN2=$(tail -n +$SL $L 2>/dev/null | grep -a "\[LEGACY\] managed" | tail -1 | grep -aoE "managed [0-9]+" | awk "{print \$2}")
[ -n "$LN2" ] && [ "$LN2" -lt "$L0" ] 2>/dev/null && echo "WARN LEGACY_managed_giam truoc=$L0 sau=$LN2 (LEGACY tu dong vi the; KHONG rollback - WAVE1b M3)"
'"$CAP_CHK$TG_CHK$GL_D01_CHK"
CHK() { gl_chk_common "$SL" "$L0" "$XCHK"; }
if gl_postloop CHK; then
  trap - INT TERM HUP
  gl_pause_clear >/dev/null || say "PAUSE con (ssh?) — tu go sau ${WD_PAUSE_MAX_S}s"
  STMS=$(s242 "P=\$(pgrep -f '$(gl_rx "$PROC_PAT")' | head -1); [ -n \"\$P\" ] && echo \$(( (\$(date +%s) - \$(ps -o etimes= -p \$P | tr -d ' ')) * 1000 ))")
  if [[ "$STMS" =~ ^[0-9]{13}$ ]]; then
    SF=$LOGDIR/dry_grid_start_${TS}.txt
    echo "tag=$TARGET_TAG md5=$NJ_MD5 start_ms=$STMS start=$(TZ=Asia/Ho_Chi_Minh date -d @$((STMS / 1000)) '+%F %T') ts=$TS env=+LIVE_APPLY_GRID_RATIO+LIVE_DCA_GRID_ENABLED" > "$SF"
    say "START_MS JVM moi = $STMS ($(TZ=Asia/Ho_Chi_Minh date -d @$((STMS / 1000)) '+%F %T') +07) — luu $SF"
    GM=$(python3 -I - "$GMICRO_TARGET" "$TARGET_TAG" "$NJ_MD5" "$STMS" <<'PYEOF'
import json, os, shutil, sys, time
p, tag, md5, ms = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
if not os.path.exists(p):
    print('WARN khong co %s — khong ghi (parity tao file)' % p); sys.exit(0)
try:
    cur = json.load(open(p))
except Exception as e:
    print('WARN file hong %s' % type(e).__name__); sys.exit(0)
if cur.get('target_jar') != tag or cur.get('target_md5') != md5:
    print('WARN file tro target_jar=%s target_md5=%s (khac %s %s) — KHONG ghi; MASTER dien smoke_start_ms=%d' % (cur.get('target_jar'), cur.get('target_md5'), tag, md5, ms)); sys.exit(0)
shutil.copy2(p, '%s.bak_%d' % (p, int(time.time())))
cur['smoke_start_ms'] = ms
cur['smoke_note'] = 'dry_enable_grid_sizing: +LIVE_APPLY_GRID_RATIO +LIVE_DCA_GRID_ENABLED (jar khong doi)'
json.dump(cur, open(p + '.tmp', 'w')); os.replace(p + '.tmp', p)
print('OK smoke_start_ms=%d' % ms)
PYEOF
)
    say "gmicro_target.json ($GMICRO_TARGET): $GM"
    case "$GM" in OK*) ;; *) tg "[dry grid] WARN TS=$TS: gmicro_target.json $GM";; esac
    if [ -n "$REG_NAME" ]; then
      say "--- dang ky parity: $REG_JAR_SH $REG_NAME $NJ_PATH $NJ_MD5 $STMS 1"
      timeout 5400 bash "$REG_JAR_SH" "$REG_NAME" "$NJ_PATH" "$NJ_MD5" "$STMS" 1 && say "OK dang ky parity $REG_NAME" || { say "WARN register_jar loi (dry GIU nguyen)"; tg "[dry grid] WARN TS=$TS register_jar $REG_NAME loi"; }
    else
      say "INFO KHONG dang ky jar parity (jar khong doi). Neu harness can moc restart moi: bash $REG_JAR_SH <ten_moi> $NJ_PATH $NJ_MD5 $STMS 1"
    fi
  else
    say "WARN khong lay duoc START_MS ('$STMS') — MASTER dien smoke_start_ms tay"; tg "[dry grid] WARN TS=$TS: thieu START_MS"
  fi
  LW=$(echo "$RESULT" | grep '^WARN LEGACY_managed_giam' | head -1 | cut -c6-90)   # [WAVE1b M3] LEGACY giam = WARN (ghi so), khong rollback
  [ -n "$LW" ] && say "WARN $LW — MASTER doi chieu LEGACY_SYMS (truoc: $(sv LEGACY_SYMS | cut -c1-200))"
  say "=== XONG: v_t_m dry BAT LIVE_APPLY_GRID_RATIO + LIVE_DCA_GRID_ENABLED (jar $NJ_MD5 khong doi). Ngay hom nay = XAM (doi cau hinh). Log: $LOG"
  tg "[dry grid] XONG TS=$TS: v_t_m dry +LIVE_APPLY_GRID_RATIO +LIVE_DCA_GRID_ENABLED (jar khong doi).${LW:+ WARN $LW.} Log $LOG"
  exit 0
fi
WHY=$(echo "${RESULT:-$RS}" | grep '^FAIL\|^WAIT' | tr '\n' ' ' | cut -c1-240)
say "hau kiem TRUOT ($WHY) => ROLLBACK ve env.sh backup GOC (dry, C3_CAPITAL=$CAP)"
if gl_rollback none dry "$CAP"; then
  say "Da ROLLBACK xong: dry chay lai voi env cu (adapter=dry, C3_CAPITAL=$CAP da kiem)."; tg "[dry grid] TRUOT TS=$TS: $WHY => ROLLBACK env cu XONG. Log $LOG"; exit 1
fi
s242 "cd $A && echo 'dry_enable_grid_sizing $TS rollback_loi' >> run/KILL_SWITCH && [ -e run/KILL_SWITCH ]" >/dev/null 2>&1
M="hau kiem TRUOT ($WHY) VA ROLLBACK LOI ($(echo "$RB" | grep '^FAIL' | head -2 | tr '\n' ' ')) — kiem tay c3live_status.sh; env backup GOC $A/conf/env.sh.bak_dry_enable_grid_sizing_$TS"
say "KHAN: $M"; tg "[dry grid] KHAN TS=$TS: $M | log $LOG"; exit 2
