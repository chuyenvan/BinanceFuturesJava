#!/usr/bin/env bash
# =============================================================================
# golive_boot_undrain.sh - [OPS6 T20] OWNER chay tren ORACLE: MO LAI lenh moi sau khi BOOT GUARD 242 (c3_autodrain_prestart.sh, cai boi
#   install_242_autodrain.sh) da chan vi bot khoi dong NGOAI quy trinh go-live (reboot / crash / watchdog start / systemd).
#   DRY=1 bash $OPS/golive_boot_undrain.sh   # CHI DOC: in run/KILL_SWITCH TRUOC + SAU du kien, KHONG ghi
#   bash $OPS/golive_boot_undrain.sh         # go 'YES MO LAI'
#   $OPS = thu muc chua script nay (worktree A1 duyet: HEAD co trong deploy/gates/A1_APPROVED_OPS.commit)
# Lam (1 ssh co tac dung phu, chay 1 lan): CHI go cac dong khop TRON mau token boot guard (GL_AD_RX trong golive_lib.sh:
#   "c3_autodrain <YYYYmmdd_HHMMSS>[ caller=..]"). Ban truoc => run/KILL_SWITCH.bu_<TS>.
#   - file CHI co dong c3_autodrain => doi ten run/KILL_SWITCH.bootok_<TS> => jar doc lai (moi lenh / 10 s) => PUSH ON.
#   - co dong NGUOI KHAC (owner drain / monitor KHAN / script go-live) => GIU NGUYEN cac dong do (file ghi lai khong con dong c3_autodrain),
#     [luot3] ma thoat 1 'CHUA MO: con dong cua <loai>' + VIEC TIEP THEO; bot VAN DRAIN (xu ly dong kia theo quy trinh cua no, vd MODE=undrain golive_live_off.sh).
#   - khong co dong c3_autodrain => khong lam gi.
# In TRUOC / SAU: so dong KS (noi dung loc ky tu), latch, process, adapter, C3_CAPITAL. Telegram (token doc tu file, khong in).
# Gioi han: neu nguoi khac ghi run/KILL_SWITCH DUNG LUC giua doc va thay file => script so (cmp) ban sao ngay truoc khi thay; khac => KHONG
#   thay, KHAN (chay lai). Ma thoat: 0 XONG (da MO) / DRY / khong co gi de go | 1 TU CHOI / CHUA MO (con dong KS khac) | 2 KHAN.
# [OPS6 luot3 M-1] TU CHOI (die, KHONG go KS, ke ca DRY) khi: so process bot != 1 | LIVE_ADAPTER process != live | jar DANG chay != NJ_MD5 |
#   latch kill-switch != NONE (ke ca chua co file) => in ly do + DUNG 1 lenh tiep theo (khoi VIEC TIEP THEO).
# =============================================================================
set -uo pipefail
_OPS=$(cd "$(dirname "$0")" && pwd); _APO=${A1_APPROVED_OPS:-/home/ubuntu/claude_master/deploy/gates/A1_APPROVED_OPS.commit}; _PW=""
_HC=$(git -C "$_OPS" rev-parse --verify -q HEAD 2>/dev/null) || _PW="$_OPS khong phai repo git"
[ -n "$_PW" ] || { [ -f "$_APO" ] && grep -qE "^$_HC([[:space:]]|\$)" "$_APO"; } || _PW="HEAD $_HC CHUA duoc A1 duyet (khong co trong $_APO)"
[ -n "$_PW" ] || git -C "$_OPS" diff --quiet HEAD -- . 2>/dev/null || _PW="$_OPS co sua CHUA commit (git diff HEAD)"
[ -z "$_PW" ] || { echo "TU CHOI [m1]: $_PW - KHONG lam gi."; exit 1; }
. "$_OPS/golive_lib.sh"
gl_manifest_check "$0" || exit 1
gl_init golive_boot_undrain
trap 'gl_exit_report $?' EXIT   # [OPS6 luot3 muc 14]
ksread() {   # CHI DOC: so dong, so dong c3_autodrain, <= 20 dong dau (loc ky tu)
  s242 "cd $A && if [ -e run/KILL_SWITCH ]; then echo KS_N=\$(grep -c '' run/KILL_SWITCH); echo KS_AD=\$(grep -cxE '$GL_AD_RX' run/KILL_SWITCH); sed -n '1,20p' run/KILL_SWITCH | tr -cd 'A-Za-z0-9_ .=:()/\n-' | sed 's/^/KS_L=/'; else echo KS_N=0; echo KS_AD=0; fi; echo KS_LOGN=\$(wc -l < logs/full.log 2>/dev/null || echo 0); echo END_KS"
}
kv() { printf '%s\n' "$1" | sed -n "s/^$2=//p" | head -1; }
gl_read_state
echo "$ST" | grep -E '^(NPROC|JAR_MD5|ENV_LIVE_ADAPTER|ENV_C3_CAPITAL|ENVSH_C3_CAPITAL|LATCH|KILLSW_FILE|KILLSW_AD|PAUSE)=' | sed 's/^/   242: /'
K0=$(ksread) || die "ssh toi 242 loi (doc run/KILL_SWITCH)"
printf '%s\n' "$K0" | grep -qx END_KS || die "doc run/KILL_SWITCH khong tron ven"
say "--- run/KILL_SWITCH TRUOC: $(kv "$K0" KS_N) dong, trong do $(kv "$K0" KS_AD) dong boot guard c3_autodrain:"
printf '%s\n' "$K0" | sed -n 's/^KS_L=/     | /p'
[ "$(kv "$K0" KS_AD)" -ge 1 ] 2>/dev/null || { say "KHONG co dong c3_autodrain trong run/KILL_SWITCH - khong co gi de go (dong khac KHONG dung toi)."; say "KET QUA: KHONG CAN. Log: $LOG"; exit 0; }
# [OPS6 luot3 M-1] dieu kien CUNG truoc khi go (ke ca DRY): sai => DUNG, KHONG go KS
if [ "$(sv NPROC)" != 1 ]; then
  if [ "$(sv NPROC)" = 0 ]; then GL_NEXT="khong chay gi them: bot CHUA chay (watchdog se start duoi KS); chay lai DRY=1 bash $_OPS/golive_boot_undrain.sh khi co dung 1 process"
  else GL_NEXT="khong chay gi them, gui output nay cho MASTER (so process $(sv NPROC) >= 2 = KHAN)"; fi
  die "so process bot = $(sv NPROC) (can dung 1) - KHONG go dong boot guard"
fi
[ "$(sv ENV_LIVE_ADAPTER)" = live ] || die "process LIVE_ADAPTER='$(sv ENV_LIVE_ADAPTER)' != live - KHONG go dong boot guard (bot khong chay live: dong c3_autodrain khong anh huong; MASTER xem)"
[ "$(sv JAR_MD5)" = "$NJ_MD5" ] || die "jar DANG chay $(sv JAR_MD5) != pin NJ_MD5 $NJ_MD5 - KHONG go dong boot guard (MASTER xem jar nao dang chay)"
[ "$(sv LATCH)" = NONE ] || die "latch kill-switch = $(sv LATCH) (can NONE; NOFILE = chua co file latch) - KHONG go dong boot guard (latch => MASTER/owner xu ly bang killsw_reset.sh truoc)"
NO=$(( $(kv "$K0" KS_N) - $(kv "$K0" KS_AD) ))
if [ "$NO" -le 0 ]; then say "--- SAU (du kien): file CHI co dong c3_autodrain => doi ten run/KILL_SWITCH.bootok_<TS> => bot PUSH ON (<= 10 s)"
else say "--- SAU (du kien): con $NO dong NGUOI KHAC (giu nguyen) => bot VAN DRAIN; chi go $(kv "$K0" KS_AD) dong c3_autodrain"; fi
[ "$DRY" = 1 ] && { say "DRY=1: KHONG ghi gi len 242. (DRY PASS)"; exit 0; }
gl_yes "MO LAI sau boot guard: go $(kv "$K0" KS_AD) dong c3_autodrain khoi run/KILL_SWITCH ($( [ "$NO" -le 0 ] && echo 'bot se MO LENH MOI' || echo "con $NO dong khac => van drain"))." "YES MO LAI"
R=$(s242in_once "RX='$GL_AD_RX' PP='$(gl_rx "$PROC_PAT")' NJ=$NJ_MD5 bash -s -- $A $TS" <<'EOR'
A=$1; TS=$2; cd "$A" || { echo "KSU=LOI_cd"; echo END_KSU; exit 0; }
K=run/KILL_SWITCH
# [OPS6 luot4 R2-m3] kiem LAI NGAY truoc khi go (owner co the do du o prompt): dung 1 JVM, adapter process live, jar = pin; sai => KHONG go
NP=$(pgrep -fc "$PP"); P=$(pgrep -f "$PP" | head -1)
[ "$NP" = 1 ] || { echo "KSU=LOI_NPROC_$NP"; echo END_KSU; exit 0; }
AD=$(tr '\0' '\n' < /proc/$P/environ 2>/dev/null | sed -n 's/^LIVE_ADAPTER=//p' | tail -1); [ "$AD" = live ] || { echo "KSU=LOI_ADAPTER_$(printf '%s' "$AD" | tr -cd 'a-z')"; echo END_KSU; exit 0; }
JM=$(md5sum < target/binance-java-sdk-1.2.4.jar 2>/dev/null | cut -c1-32); [ "$JM" = "$NJ" ] || { echo "KSU=LOI_JAR"; echo END_KSU; exit 0; }
if [ ! -e $K ]; then echo "KSU=KHONG_CO_FILE"; echo END_KSU; exit 0; fi
cp -p $K $K.bu_$TS || { echo "KSU=LOI_backup"; echo END_KSU; exit 0; }
NA=$(grep -cxE "$RX" $K.bu_$TS); NO=$(grep -cvxE "$RX" $K.bu_$TS)
if [ "$NA" = 0 ]; then echo "KSU=KHONG_CO_DONG_AUTODRAIN"
elif [ "$NO" = 0 ]; then
  if cmp -s $K $K.bu_$TS && mv -f $K $K.bootok_$TS && [ ! -e $K ]; then echo "KSU=MO"; else echo "KSU=LOI_FILE_DOI_GIUA_CHUNG"; fi
else
  if grep -vxE "$RX" $K.bu_$TS > $K.tmp_$TS && cmp -s $K $K.bu_$TS && mv -f $K.tmp_$TS $K && ! grep -qxE "$RX" $K; then echo "KSU=CON_DONG_KHAC"
  else rm -f $K.tmp_$TS; echo "KSU=LOI_FILE_DOI_GIUA_CHUNG"; fi
fi
[ -e $K ] && echo "SAU_N=$(grep -c '' $K)" || echo "SAU_N=0"
echo END_KSU
EOR
) || true
printf '%s\n' "$R" | grep -v '^END_KSU$' | sed 's/^/   242: /'
U=$(kv "$R" KSU)
K1=$(ksread) && printf '%s\n' "$K1" | grep -qx END_KS && { say "--- run/KILL_SWITCH SAU: $(kv "$K1" KS_N) dong, $(kv "$K1" KS_AD) dong c3_autodrain:"; printf '%s\n' "$K1" | sed -n 's/^KS_L=/     | /p'; } || say "!! doc lai run/KILL_SWITCH loi (ssh?)"
case "$U" in
  MO)
    PON=0; SL=$(( $(kv "$K0" KS_LOGN) + 1 ))
    for r in $(seq 1 "$POST_ROUNDS"); do
      sleep "$POST_WAIT_S"
      n=$(s242 "cd $A && tail -n +$SL logs/full.log 2>/dev/null | grep -ac 'PUSH doi trang thai -> ON'") || n=x
      [ "$n" != x ] && [ "$n" -ge 1 ] 2>/dev/null && { PON=1; break; }
    done
    if [ "$PON" = 1 ]; then M="DA MO: dong c3_autodrain go, run/KILL_SWITCH khong con, bot bao PUSH ON"
    else M="DA go run/KILL_SWITCH (chi co dong c3_autodrain) nhung CHUA thay 'PUSH doi trang thai -> ON' sau $((POST_ROUNDS * POST_WAIT_S))s (bot tat? latch? SHADOW_NO_PUSH?) - kiem golive_monitor.sh"; fi
    say "=== XONG: $M. Log: $LOG"; tg "[golive] BOOT UNDRAIN TS=$TS: $M. Log $LOG" || :; exit 0 ;;
  CON_DONG_KHAC)   # [OPS6 luot3 MASTER] thong nhat voi live_off undrain: con dong KS khac => CHUA MO => rc 1 + VIEC TIEP THEO + 1 lenh owner
    LOAI=$(printf '%s\n' "${K1:-}" | sed -n 's/^KS_L=//p' | awk 'NF{print $1}' | sort | uniq -c | awk '{printf "%s%s x%s", s, $2, $1; s=", "}')
    if [ -z "$LOAI" ] || printf '%s\n' "${K1:-}" | sed -n 's/^KS_L=//p' | awk 'NF{print $1}' | grep -qvxE 'golive_live_off|c3live_boot|golive_monitor'; then GL_NEXT="khong chay gi them, gui output nay cho MASTER (con dong KS cua script/nguoi khac)"
    elif printf '%s\n' "${K1:-}" | grep -q '^KS_L=golive_monitor '; then GL_NEXT="XOA_DONG_MONITOR=YES MODE=undrain bash $_OPS/golive_live_off.sh  (CHI sau khi da xu ly nguyen nhan KHAN monitor)"
    else GL_NEXT="MODE=undrain bash $_OPS/golive_live_off.sh"; fi
    M="CHUA MO: da go dong c3_autodrain nhung run/KILL_SWITCH CON $(kv "$R" SAU_N) dong cua ${LOAI:-?} (giu nguyen) => bot VAN DRAIN"
    say "KET QUA: $M. Log: $LOG"; tg "[golive] BOOT UNDRAIN TS=$TS: $M. Log $LOG" || :; exit 1 ;;
  LOI_NPROC_*|LOI_ADAPTER*|LOI_JAR)   # [luot4 R2-m3] trang thai doi trong luc cho YES => KHONG go
    GL_NEXT="DRY=1 bash $_OPS/golive_boot_undrain.sh  (doc lai trang thai; $U)"
    say "TU CHOI: trang thai 242 DOI sau YES ($U: so JVM / adapter / jar) - run/KILL_SWITCH KHONG doi. Log: $LOG"; exit 1 ;;
  KHONG_CO_FILE|KHONG_CO_DONG_AUTODRAIN) say "KET QUA: KHONG CAN ($U) - khong doi gi. Log: $LOG"; exit 0 ;;
  *) M="go dong boot guard LOI / khong ro (${U:-ssh?}) - run/KILL_SWITCH KHONG doi (hoac khong xac nhan). Chay lai lenh."
    GL_NEXT="DRY=1 bash $_OPS/golive_boot_undrain.sh  (doc lai run/KILL_SWITCH roi moi chay lai)"; say "KHAN: $M"; tg "[golive] KHAN TS=$TS boot_undrain: $M | log $LOG" || :; exit 2 ;;
esac
