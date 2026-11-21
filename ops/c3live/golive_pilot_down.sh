#!/usr/bin/env bash
# =============================================================================
# golive_pilot_down.sh - [OPS6 luot 2] HA VON c3 khi LIVE (luat "truot gia xau => giam nua von"; ve micro): C3_CAPITAL hien tai -> dich
#   (5000 hoac 1000, PHAI < von hien tai). KHONG doi jar, KHONG doi tham so khac (chi THEM o CUOI conf/env.sh 1 dong chu thich + 1 dong
#   export C3_CAPITAL; env.sh 242 co the da co >= 2 dong C3_CAPITAL - bash/jar va moi kiem cua script deu lay DONG CUOI; dong cuoi hien tai
#   phai la so tron = von process, khong thi TU CHOI). [luot3 n-4] dong moi ghi SAU khi bot dung + dinh dat lai (gl_restart HA von).
#   [luot3 n-2] run/KILL_SWITCH co dong c3_autodrain (boot guard) => TU CHOI (owner dieu tra + golive_boot_undrain.sh truoc).
#   $OPS = thu muc chua script nay (worktree A1 duyet: HEAD co trong deploy/gates/A1_APPROVED_OPS.commit)
#   DRY=1 bash $OPS/golive_pilot_down.sh 5000     # chi kiem + IN he qua, KHONG ghi gi
#   bash $OPS/golive_pilot_down.sh 5000           # go 'YES HA VON 5000' (khung :10-:44)
# CHI tai khoan con (C3_ACCOUNT=SUB). CHI khi c3 PHANG: so c3 0 cum + tk con 0 vi the / lenh / algo (gl_sub_eval 1). Ly do (doc jar
#   hotfix): cum dang mo giu kich thuoc leg theo von CU, DCA ke tiep size theo von MOI voi U = margin / von moi (TradeUtils.managerBudget:
#   U >= U_MAX 0.60 => chan DCA, throttle 1 - U/0.60), C4 cong suat chan mo cum moi, va nguong -40 % (C6/A40) tinh tren von moi trong khi
#   phoi nhiem con theo von cu => FLATTEN THAT som gap doi. Con vi the => TU CHOI, huong dan: MODE=drain golive_live_off.sh, cho phang.
# IN truoc khi xac nhan: von cu -> moi, equity c3 hien tai (dong [KILLSW] HOURLY gan nhat), realized cong don (ledger KHONG reset khi doi
#   von - quyet dinh MASTER 11-21: giu ngu nghia), equity c3 du kien sau ha + dinh se dat lai, muc dung -40 % (USDT), so vi the dang mo.
# Restart / hau kiem / rollback / KILL_SWITCH / PAUSE / A-02 = gl_cap_switch + gl_restart + a02_reset (golive_lib.sh, chung pilot_on).
#   run/KILL_SWITCH KHONG co => KS token cua script + hau kiem 2 pha (PUSH ON). KS CO SAN (vd owner drain de phang) => GIU NGUYEN, bot
#   VAN DRAIN sau khi ha (mo lai co chu dich: MODE=undrain golive_live_off.sh).
# Ma thoat: 0 XONG / DRY PASS | 1 TU CHOI / da rollback | 2 KHAN.
# =============================================================================
set -uo pipefail
_OPS=$(cd "$(dirname "$0")" && pwd); _APO=${A1_APPROVED_OPS:-/home/ubuntu/claude_master/deploy/gates/A1_APPROVED_OPS.commit}; _PW=""
_HC=$(git -C "$_OPS" rev-parse --verify -q HEAD 2>/dev/null) || _PW="$_OPS khong phai repo git"
[ -n "$_PW" ] || { [ -f "$_APO" ] && grep -qE "^$_HC([[:space:]]|\$)" "$_APO"; } || _PW="HEAD $_HC CHUA duoc A1 duyet (khong co trong $_APO)"
[ -n "$_PW" ] || git -C "$_OPS" diff --quiet HEAD -- . 2>/dev/null || _PW="$_OPS co sua CHUA commit (git diff HEAD)"
[ -z "$_PW" ] || { echo "TU CHOI [m1]: $_PW - KHONG lam gi."; exit 1; }
. "$_OPS/golive_lib.sh"
gl_manifest_check "$0" || exit 1
gl_init golive_pilot_down
trap 'gl_exit_report $?' EXIT   # [OPS6 luot3 muc 14]
GL_DOWN_SIZES="5000 1000"
SIZE=${1:-${PILOT_DOWN_TO:-}}
[ "$C3_ACCOUNT" = SUB ] || die "chi ho tro C3_ACCOUNT=SUB (tk con)"
ACCT_TXT="tai khoan CON (ADD4)"
case " $GL_DOWN_SIZES " in *" $SIZE "*) [ -n "$SIZE" ] || die "thieu von dich (5000 | 1000): bash $_OPS/golive_pilot_down.sh 5000";; *) die "von dich '$SIZE' khong hop le (chi nhan: $GL_DOWN_SIZES)";; esac
gl_read_state
echo "$ST" | grep -v '^END_STATE$' | sed 's/^/   242: /'
F=0; chk() { if eval "$2"; then say "OK   $1"; else say "FAIL $1"; F=1; fi; }
C0=$(sv ENV_C3_CAPITAL)
chk "C3_CAPITAL hien tai ($C0) > dich $SIZE (script CHI HA von)" "[[ '$C0' =~ ^[0-9]+$ ]] && [ '$C0' -gt $SIZE ]"
chk "[m-1] C3_CAPITAL DONG CUOI env.sh ('$(sv ENVSH_C3_CAPITAL)') la so tron = process ($C0) (khong doc duoc / lech => KHONG ha von)" "[[ '$(sv ENVSH_C3_CAPITAL)' =~ ^[0-9]+$ ]] && [ '$C0' = '$(sv ENVSH_C3_CAPITAL)' ]"
chk "run/KILL_SWITCH KHONG co dong c3_autodrain (co $(sv KILLSW_AD); boot guard da chan khoi dong ngoai quy trinh => owner dieu tra + golive_boot_undrain.sh truoc)" "[ '$(sv KILLSW_AD)' = 0 ]"
[ "$(sv KILLSW_AD)" -ge 1 ] 2>/dev/null && GL_NEXT="DRY=1 bash $GL_HERE/golive_boot_undrain.sh  (SAU khi dieu tra vi sao bot khoi dong NGOAI quy trinh)"
chk "1 process bot" "[ '$(sv NPROC)' = 1 ]"
chk "jar dang chay = pin $NJ_MD5 (KHONG doi jar)" "[ '$(sv JAR_MD5)' = '$NJ_MD5' ]"
chk "dang chay c3_live LIVE (SHADOW_NO_PUSH=false, LIVE_ENTRY_ENABLED=true)" "[ '$(sv ENV_LIVE_PROFILE)' = c3_live ] && [ '$(sv ENV_LIVE_ADAPTER)' = live ] && [ '$(sv ENVSH_LIVE_ADAPTER)' = live ] && [ '$(sv ENV_SHADOW_NO_PUSH)' = false ] && [ '$(sv ENV_LIVE_ENTRY_ENABLED)' = true ]"
chk "latch kill-switch NONE (co latch => xu ly truoc bang killsw_reset.sh)" "[ '$(sv LATCH)' = NONE ] || [ '$(sv LATCH)' = NOFILE ]"
chk "so c3 PHANG: 0 cum (co $(sv BOOK_CUM); con vi the => MODE=drain bash $GL_HERE/golive_live_off.sh roi cho phang)" "[ '$(sv BOOK_CUM)' = 0 ]"
chk "khong PAUSE watchdog" "[ '$(sv PAUSE | cut -c1)' = 0 ]"
chk "khong canary/soak" "[ '$(sv CANARY_SOAK)' = 0 ]"
chk "MemAvailable $(sv MEM) >= $MIN_MEM_MB MB" "[ '$(sv MEM)' -ge $MIN_MEM_MB ] 2>/dev/null"
chk "Oracle: khong co tien trinh $CANARY_PAT" "gl_no_canary"
DTS=$(sed -n 's/^dry_ts=//p' "$GL_MON_FLAG" 2>/dev/null | head -1)
chk "co micro/pilot co dry_ts (${DTS:-THIEU})" "[ -n '$DTS' ]"
gl_bootguard242
chk "boot guard 242 DA CAI (T20; $BG_DETAIL)" "[ '$BG' = CAI ]"
chk "A-02: dat lai dinh duoc (python 242 co=$(sv PY_OK); env.sh ghi de duong dan='$(sv ENVSH_PATH_OVR)')" "[ '$(sv PY_OK)' = 1 ] && [ -z '$(sv ENVSH_PATH_OVR)' ]"
L0=SKIP
chk "bot live dung key tk con (LIVE_C3_KEYS_FILE=$KEYS_FILE; co: $(sv ENV_LIVE_C3_KEYS_FILE))" "[ '$(sv ENV_LIVE_C3_KEYS_FILE)' = '$KEYS_FILE' ]"
chk "file key tk con 600 + sha8 $(sv KEYS_FILE_SHA8) = $SUB_KEY_SHA8" "[ '$(sv KEYS_OK)' = 1 ] && [ '$(sv KEYS_PERM)' = 600 ] && [ '$(sv KEYS_FILE_SHA8)' = '$SUB_KEY_SHA8' ]"
chk "cron golive_monitor da cai, ban pin con nguyen" "gl_mon_cron_ok"
HBA=$(gl_hb_age)
chk "heartbeat cron golive_monitor ${HBA}s <= ${MON_HB_MAX_AGE_S}s" "[ $HBA -ge 0 ] && [ $HBA -le $MON_HB_MAX_AGE_S ]"
chk "md5 monitor+lib $(gl_mon_m12) da qua A1" "gl_mon_approved"
API=$(gl_api242 sub) || die "ssh toi 242 loi (doc tk con)"
echo "$API" | grep -v '^END_API$' | sed 's/^/   tk con: /'
gl_sub_eval 1
chk "tk con PHANG + key dat: 0 vi the / 0 lenh / 0 algo (POS_TOTAL=$(av POS_TOTAL) ORD_TOTAL=$(av ORD_TOTAL) ALGO_TOTAL=$(av ALGO_TOTAL))${SUBWHY:+ -$SUBWHY}" "[ '$SUBV' = DAT ]"
KEYCHK="envk LIVE_C3_KEYS_FILE=$KEYS_FILE; envk C3_EXCLUDE_LEGACY_HELD=false; [ \"\$(T '\\[C3-EXCL-FORCE\\]')\" = 0 ] && echo 'OK 0_C3-EXCL-FORCE' || echo 'FAIL C3-EXCL-FORCE (SUB: env key sai)'"
# ---- equity c3 hien tai (CHI DOC: dong [KILLSW] HOURLY gan nhat cua jar) + he qua
HL=$(s242 "cd $A && tail -c 20000000 logs/full.log 2>/dev/null | grep -a '\[KILLSW\] HOURLY' | tail -1 | cut -c1-600") || HL=""
EQN=$(printf '%s' "$HL" | grep -oE ' eq=-?[0-9.]+' | head -1 | cut -d= -f2); PKN=$(printf '%s' "$HL" | grep -oE ' peak=-?[0-9.]+' | head -1 | cut -d= -f2)
AEQ=$(printf '%s' "$HL" | grep -oE ' acct_eq=-?[0-9.]+' | head -1 | cut -d= -f2)
chk "doc duoc equity c3 hien tai (dong [KILLSW] HOURLY gan nhat: eq=${EQN:-?} peak=${PKN:-?} acct_eq=${AEQ:-?}; jar moi start < 1 h => cho dong HOURLY)" "[[ '$EQN' =~ ^-?[0-9]+(\.[0-9]+)?$ ]]"
if [[ "$EQN" =~ ^-?[0-9]+(\.[0-9]+)?$ ]] && [[ "$C0" =~ ^[0-9]+$ ]]; then
  R=$(awk -v e="$EQN" -v c="$C0" -v s="$SIZE" 'BEGIN{ r=e-c; n=s+r; ce=(n<s?n:s); printf "REAL=%.2f\nEQNEW=%.2f\nCAPEFF=%.2f\nSTOP=%.2f\nLOSS=%.2f\n", r, n, ce, 0.6*n, 0.4*n }')
  rv() { printf '%s\n' "$R" | sed -n "s/^$1=//p"; }
  say "=== HE QUA HA VON (doc truoc khi xac nhan):"
  say "   von C3_CAPITAL: $C0 -> $SIZE ($ACCT_TXT); so vi the c3 dang mo: so c3 $(sv BOOK_CUM) cum, san $(av POS_TOTAL) vi the"
  say "   equity c3 hien tai (jar, $(printf '%s' "$HL" | cut -c1-19)): eq=$EQN dinh C6=$PKN | A40 acct_eq=${AEQ:-?}"
  say "   realized + funding cong don tu moc equity c3 (ledger KHONG reset khi doi von - quyet dinh MASTER 11-21): $(rv REAL) USDT"
  say "   equity c3 du kien sau ha = $SIZE + $(rv REAL) = $(rv EQNEW); von tinh size = min(C3_CAPITAL, equity c3, avail+margin) <= $(rv CAPEFF)"
  say "   dinh C6/A40 se DAT LAI (a02_reset truoc start) = equity c3 dau tien sau start ~ $(rv EQNEW) (DD cu duoc xoa co chu dich)"
  say "   muc dung -40 % moi: equity c3 <= $(rv STOP) USDT (lo them $(rv LOSS) USDT tu luc ha) => FLATTEN (latch, chi owner mo)"
  chk "equity c3 du kien sau ha $(rv EQNEW) > 0 (<= 0 => jar khong danh gia DD, khong co von size)" "awk -v n='$(rv EQNEW)' 'BEGIN{exit !(n>0)}'"
fi
say "--- [D-01] budget leg du kien voi C3_CAPITAL=$SIZE:"
D01=$(gl_d01_plan "$SIZE"); D01RC=$?; echo "$D01" | sed 's/^/   /'
chk "D-01 leg0 du kien >= $MIN_LEG_BUDGET" "[ '$D01RC' = 0 ]"
if [ "$(sv KILLSW_FILE)" = 1 ]; then GL_CAP_KS=0; say "INFO run/KILL_SWITCH CO SAN (token $(sv KILLSW_TOK)) => GIU NGUYEN, bot VAN DRAIN sau ha von (mo lai co chu dich: $(gl_ks_hint))"
else GL_CAP_KS=1; say "INFO khong co run/KILL_SWITCH => KS token golive_pilot_down TRUOC stop, hau kiem 2 pha (go KS cua minh => PUSH ON)"; fi
[ "$F" = 0 ] || die "kiem truoc co muc FAIL (xem tren)"
ENV_ADD="# [v1.2 OPS6 golive_pilot_down $TS] HA VON $ACCT_TXT $C0 -> $SIZE
export C3_CAPITAL=$SIZE"
say "--- se THEM vao $A/conf/env.sh:"; echo "$ENV_ADD" | sed 's/^/   + /'
gl_mon_repin_dry() { [ "$DRY" = 1 ] && { gl_mon_repin || say "!! installer cron (DRY) loi"; }; }
gl_mon_repin_dry
[ "$DRY" = 1 ] && { say "DRY=1: dung o day, KHONG ghi gi len 242. (DRY PASS)"; exit 0; }
gl_time
gl_yes "HA VON: C3_CAPITAL $C0 -> $SIZE tren $ACCT_TXT (dung -40 % moi ~ ${EQN:+$(printf '%s\n' "$R" | sed -n 's/^STOP=//p')} USDT equity c3)." "YES HA VON $SIZE"
gl_no_canary || die "co tien trinh $CANARY_PAT tren Oracle (vua xuat hien)"
gl_read_state
[ "$(sv BOOK_CUM)" = 0 ] && [ "$(sv ENV_C3_CAPITAL)" = "$C0" ] && [ "$(sv ENVSH_C3_CAPITAL)" = "$C0" ] && [ "$(sv NPROC)" = 1 ] && [ "$(sv KILLSW_AD)" = 0 ] || die "trang thai doi sau YES (so c3 $(sv BOOK_CUM) cum, von $(sv ENV_C3_CAPITAL) / env.sh $(sv ENVSH_C3_CAPITAL), process $(sv NPROC), c3_autodrain $(sv KILLSW_AD)) - khong ha von"
gl_mon_flag_set || die "KHONG ghi duoc co monitor $GL_MON_FLAG"
gl_mon_repin || die "pin lai cron golive_monitor LOI"
API=$(gl_api242 mon) || die "ssh toi 242 loi (doc tmb)"
echo "$API" | grep -qx END_API || die "doc tmb tk con khong tron ven"
gl_eq_base_set "$(av TMB)" "$SIZE" "$(av KEY_SHA8)" "golive_pilot_down $TS (C3_CAPITAL $C0 -> $SIZE) - RESET dinh eq co chu dich" || die "KHONG ghi duoc moc tmb0"
GL_CAP_LABEL="HA VON"
GL_CAP_TGOK="[golive] HA VON XONG TS=$TS C3_ACCOUNT=$C3_ACCOUNT C3_CAPITAL=$C0 -> $SIZE; dinh C6/A40 + lop phu dat lai co chu dich. Log $LOG"
gl_cap_switch
