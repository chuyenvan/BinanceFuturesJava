#!/usr/bin/env bash
# =============================================================================
# rollback_v12.sh — [DEPRECATED 16/11 WAVE1 B-12] quay 242 ve truoc deploy_v12_dry.sh (jar dcae2e2b v1.1 + env.sh + start.sh cu, c3_shadow)
#   !! LOI THOI: KHONG dung de rollback v_t_m hien tai (r4u3fin2). Dung:
#      - ve jar r4u3 (dry):      bash <repo>/ops/c3live/rollback_vtm_r4u3.sh
#      - dang MICRO/PILOT live:  MODE=drain bash <repo>/ops/c3live/golive_live_off.sh  (roi MODE=dry khi c3 phang)
#   Script TU CHOI khi: process / env.sh LIVE_ADAPTER=live, co co monitor micro/pilot (Oracle), hoac dich = jar v1.1 dcae2e2b
#   (mac dinh) ma khong co ALLOW_V11_ROLLBACK=1 (chi MASTER, sau khi xac nhan dry).
# Chay tren ORACLE:  bash <repo>/ops/c3live/rollback_v12.sh <TS>
#   <TS> = gia tri TS in o dau log deploy_v12dry (dang 20261118_0915)
# Thu (chi doc): DRY=1 bash ~/claude_master/deploy/rollback_v12.sh <TS>
# [2c] Chot gio nhu deploy (khan cap: FORCE_TIME=1). YES_AUTO=1 chi danh cho rollback tu dong cua deploy_v12_dry.sh.
# KHONG xoa so dry (run/c3live_*): doi ten .rb_<TS> de lan deploy sau bat dau sach (so dry khong co tien that).
# [R4m MIN-1 A1 R4K] run/gate_ratio_live.bin DUNG CHUNG v1.1/dry: khoi phuc DUNG ban deploy backup (cung TS, md5 kiem);
#   file cua dry doi ten .rb_<TS>. Khong co backup TS (deploy chua toi restart) => giu nguyen.
# [R4m MIN-2] PAUSE ghi token rieng 'C3ROLLBACK_V12 TS=..' (bo tu go PAUSE cua deploy khong dung toi).
# =============================================================================
set -uo pipefail
TS=${1:?"Thieu TS. Vi du: bash rollback_v12.sh 20261118_0915"}
SSH_242=${SSH_242:-"ssh -p 2222 -o BatchMode=yes -o ConnectTimeout=20 -i /home/ubuntu/.ssh/id_rsa_chuyennd root@103.157.218.242"}
A=${APP_DIR:-/home/chuyennd/java/v_t_m}
PROC_PAT=${PROC_PAT:-BinanceOrderTradingManager}   # mau nhan dien process app (test: process gia)
OLD_MD5=${OLD_MD5:-dcae2e2bbb1a357bc15703b416d4dccb}
WD_PAUSE=${WD_PAUSE:-/var/lib/h242_watchdog/PAUSE}
DRY=${DRY:-0}
FORCE_TIME=${FORCE_TIME:-0}   # [2c MIN-12] bo chot gio (khan cap / rollback tu dong ngay sau deploy)
YES_AUTO=${YES_AUTO:-0}       # [2c] 1 = khong hoi YES (CHI deploy_v12_dry.sh goi khi LATCH sau start)
LOGDIR=${LOGDIR:-/home/ubuntu/claude_master/deploy}
mkdir -p "$LOGDIR"
LOG=$LOGDIR/rollback_v12_$(TZ=Asia/Ho_Chi_Minh date +%Y%m%d_%H%M).log
exec > >(tee -a "$LOG") 2>&1
say() { echo "[$(TZ=Asia/Ho_Chi_Minh date '+%F %T')] $*"; }
CRONTAB_CMD=${CRONTAB_CMD:-crontab}
SSH_RETRY_S=${SSH_RETRY_S:-10}
# [R4e MINOR-4] ssh/scp toi 242: thu lai 3 lan cach SSH_RETRY_S (10 s) KHI loi ket noi (rc 255); lenh tu xa da chay xong
# (rc khac 255) KHONG chay lai. s242in: noi dung stdin (heredoc) duoc giu lai cho moi lan thu.
s242() {
  local i rc=255
  for i in 1 2 3; do
    $SSH_242 "$@" < /dev/null; rc=$?
    [ "$rc" != 255 ] && return "$rc"
    [ "$i" -lt 3 ] && { echo "[ssh 242 loi ket noi (rc 255) — thu lai $i/2 sau ${SSH_RETRY_S}s]" >&2; sleep "$SSH_RETRY_S"; }
  done
  return "$rc"
}
s242in() {
  local in i rc=255
  in=$(cat)
  for i in 1 2 3; do
    printf '%s\n' "$in" | $SSH_242 "$@"; rc=$?
    [ "$rc" != 255 ] && return "$rc"
    [ "$i" -lt 3 ] && { echo "[ssh 242 loi ket noi (rc 255) — thu lai $i/2 sau ${SSH_RETRY_S}s]" >&2; sleep "$SSH_RETRY_S"; }
  done
  return "$rc"
}
c242() {
  local i
  for i in 1 2 3; do
    $SCP_242 "$@" && return 0
    [ "$i" -lt 3 ] && { echo "[scp 242 loi — thu lai $i/2 sau ${SSH_RETRY_S}s]" >&2; sleep "$SSH_RETRY_S"; }
  done
  return 1
}

say "=== rollback v1.2 -> dcae2e2b (c3_shadow) TS=$TS DRY=$DRY ==="
# [WAVE1 B-12] chan dung sai: live / micro-pilot dang bat / dich v1.1
V11_MD5=dcae2e2bbb1a357bc15703b416d4dccb
GL_MON_FLAG=${GL_MON_FLAG:-$LOGDIR/golive_monitor.on}
RBGO="dung: ve r4u3 dry => bash $(cd "$(dirname "$0")" && pwd)/rollback_vtm_r4u3.sh ; dang live => MODE=drain bash $(cd "$(dirname "$0")" && pwd)/golive_live_off.sh"
if [ -f "$GL_MON_FLAG" ]; then say "DUNG: co co micro/pilot $GL_MON_FLAG (go-live dang bat) — rollback_v12 TU CHOI. $RBGO"; exit 1; fi
AD=$(s242 "cd $A 2>/dev/null || exit 0; P=\$(pgrep -f '[${PROC_PAT:0:1}]${PROC_PAT:1}' | head -1); echo \"PA=\$(tr '\\0' '\\n' < /proc/\$P/environ 2>/dev/null | sed -n 's/^LIVE_ADAPTER=//p' | tail -1) SA=\$(sed -n 's/^export LIVE_ADAPTER=//p' conf/env.sh | tail -1)\"") || { say "DUNG: ssh 242 loi (khong doc duoc adapter) — khong doi gi"; exit 1; }
say "adapter 242: $AD"
case "$AD" in *PA=live*|*SA=live*) say "DUNG: v_t_m dang LIVE ($AD) — rollback_v12 TU CHOI (mo coi vi the c3 live). $RBGO"; exit 1;; esac
if [ "$OLD_MD5" = "$V11_MD5" ] && [ "${ALLOW_V11_ROLLBACK:-0}" != 1 ] && [ "$YES_AUTO" != 1 ]; then   # YES_AUTO: rollback tu dong NGAY trong deploy_v12_dry*.sh (dich v1.1 hop le)
  say "DUNG: dich rollback = jar v1.1 dcae2e2b (LOI THOI tu v1.2) — TU CHOI. $RBGO (MASTER co chu dich: ALLOW_V11_ROLLBACK=1)"; exit 1
fi
# [2c MIN-12] chot gio nhu deploy (phut :10-:44, tranh 07:xx/19:xx, 00:50-01:20, 12:50-13:20); khan cap: FORCE_TIME=1
time_ok() {
  H=$(TZ=Asia/Ho_Chi_Minh date +%-H); M=$(TZ=Asia/Ho_Chi_Minh date +%-M)
  [ "$M" -ge 10 ] && [ "$M" -le 44 ] || return 1
  case "$H" in 7|19) return 1;; esac
  if [ "$H" -eq 1 ] || [ "$H" -eq 13 ]; then [ "$M" -gt 20 ] || return 1; fi
  return 0
}
if [ "$DRY" != 1 ] && [ "$FORCE_TIME" != 1 ] && ! time_ok; then
  say "DUNG: gio $(TZ=Asia/Ho_Chi_Minh date +%H:%M) (+07) khong hop le. Chay lai trong phut :10-:44 (tranh 07:xx, 19:xx,"
  say "      00:50-01:20, 12:50-13:20). KHAN CAP (bot hong, MASTER bao): FORCE_TIME=1 bash $0 $TS"
  exit 1
fi
PRE=$(s242in "PP='$PROC_PAT' bash -s -- $A $TS $OLD_MD5" <<'EOF'
A=$1; TS=$2; OLD=$3; cd "$A" || { echo "FAIL cd"; exit 0; }
for f in target/binance-java-sdk-1.2.4.jar.bak_v12pre_$TS conf/env.sh.bak_v12pre_$TS bin/start.sh.bak_v12pre_$TS; do
  [ -f "$f" ] && echo "OK co $f" || echo "FAIL thieu backup $f"
done
J=$(md5sum < target/binance-java-sdk-1.2.4.jar.bak_v12pre_$TS 2>/dev/null | cut -c1-32)
[ "$J" = "$OLD" ] && echo "OK backup_jar_md5=$J" || echo "FAIL backup_jar_md5=$J (mong $OLD)"
echo "INFO jar_dang_chay=$(md5sum < target/binance-java-sdk-1.2.4.jar | cut -c1-32) so_process=$(pgrep -fc "$PP")"
echo "INFO so_dry: $(ls run/c3live_* 2>/dev/null | tr '\n' ' ')"
GB=run/gate_ratio_live.bin.bak_v12pre_$TS
if [ -f "$GB.md5" ]; then
  GM=$(cat "$GB.md5")
  if [ "$GM" = NONE ]; then echo "OK gate_ratio_backup=NONE (truoc deploy chua co file)"
  else G=$(md5sum < "$GB" 2>/dev/null | cut -c1-32); [ "$G" = "$GM" ] && echo "OK gate_ratio_backup_md5=$G" || echo "FAIL gate_ratio_backup_md5=$G (mong $GM)"; fi
else
  echo "INFO gate_ratio: khong co backup TS=$TS (deploy chua toi restart / deploy truoc R4m) => giu nguyen"
fi
EOF
) || { say "DUNG: ssh loi"; exit 1; }
echo "$PRE"
echo "$PRE" | grep -q '^FAIL' && { say "DUNG: thieu backup / md5 sai. KHONG doi gi. Gui log cho MASTER: $LOG"; exit 1; }
[ "$DRY" = 1 ] && { say "DRY=1: dung o day (DRY PASS), khong doi gi."; exit 0; }

if [ "$YES_AUTO" = 1 ]; then
  say "Rollback TU DONG (YES_AUTO=1, goi tu deploy_v12_dry.sh) ve dcae2e2b (c3_shadow) voi backup TS=$TS"
else
  say "Rollback ve dcae2e2b (c3_shadow) voi backup TS=$TS. Go YES de tiep tuc:"
  read -r ANS; [ "$ANS" = YES ] || { say "huy"; exit 0; }
fi
RS=$(s242in "PP='$PROC_PAT' CT='$CRONTAB_CMD' bash -s -- $A $TS $OLD_MD5 $WD_PAUSE" <<'EOF'
A=$1; TS=$2; OLD=$3; PAUSE=$4; cd "$A" || { echo "FAIL cd"; exit 0; }
echo "C3ROLLBACK_V12 TS=$TS t=$(date +%s)" > "$PAUSE" 2>/dev/null
bin/daemon.sh stop
for i in $(seq 1 30); do pgrep -f "$PP" >/dev/null || break; sleep 2; done
pgrep -f "$PP" >/dev/null && { echo "FAIL van con process"; rm -f "$PAUSE"; exit 0; }
\cp -f target/binance-java-sdk-1.2.4.jar.bak_v12pre_$TS target/binance-java-sdk-1.2.4.jar
\cp -f conf/env.sh.bak_v12pre_$TS conf/env.sh
\cp -f bin/start.sh.bak_v12pre_$TS bin/start.sh
GR=run/gate_ratio_live.bin; GB=$GR.bak_v12pre_$TS
if [ -f "$GB.md5" ]; then
  GM=$(cat "$GB.md5")
  [ ! -f "$GR" ] || mv -f "$GR" "$GR.rb_$TS"
  if [ "$GM" = NONE ]; then echo "OK gate_ratio: truoc deploy khong co => file cua dry doi ten .rb_$TS"
  else \cp -fp "$GB" "$GR"; G=$(md5sum < "$GR" 2>/dev/null | cut -c1-32); [ "$G" = "$GM" ] && echo "OK gate_ratio_khoi_phuc md5=$G" || echo "FAIL gate_ratio_khoi_phuc md5=$G (mong $GM)"; fi
else
  echo "INFO gate_ratio_khong_co_backup_TS (giu nguyen)"
fi
for f in run/c3live_book.json run/c3live_dry_state.json run/c3live_ledger.csv run/killsw_latch.json run/c3live_killsw_peak run/c3live_merged.txt run/c3live_equity_c3.json run/c3live_lost.txt run/ts_ext_daily.csv.a1; do
  [ -f "$f" ] && mv -f "$f" "$f.rb_$TS"
done
J=$(md5sum < target/binance-java-sdk-1.2.4.jar | cut -c1-32)
[ "$J" = "$OLD" ] && echo "OK jar=$J" || echo "FAIL jar=$J"
bin/daemon.sh start; sleep 8
P=$(pgrep -f "$PP" | head -1)
[ -n "$P" ] && echo "OK started pid=$P lstart=$(ps -o lstart= -p $P)" || echo "FAIL khong_thay_process"
E=$(tr '\0' '\n' < /proc/$P/environ 2>/dev/null)
echo "$E" | grep -qx 'LIVE_PROFILE=c3_shadow' && echo "OK env LIVE_PROFILE=c3_shadow" || echo "FAIL env LIVE_PROFILE"
echo "$E" | grep -q '^LIVE_ADAPTER=' && echo "FAIL env van co LIVE_ADAPTER" || echo "OK env khong LIVE_ADAPTER"
# [R4e MAJOR-1] go cron lam moi exchangeInfo theo marker (khong dung toi dong cron khac; crontab -l loi la => FAIL, khong ghi de)
MK='# C3LIVE_EXINFO_REFRESH'
if C=$($CT -l 2>/dev/null); then
  if echo "$C" | grep -qF "$MK"; then echo "$C" | grep -vF "$MK" | $CT -; fi
  [ "$($CT -l 2>/dev/null | grep -cF "$MK")" = 0 ] && echo "OK cron_lam_moi_da_go" || echo "FAIL cron_lam_moi_van_con"
elif $CT -l 2>&1 | grep -qi 'no crontab'; then
  echo "OK cron_khong_co"
else
  echo "FAIL crontab_-l_loi (KHONG go duoc cron lam moi: crontab -l | grep -v C3LIVE_EXINFO_REFRESH | crontab -)"
fi
rm -f "$PAUSE"
EOF
) || { say "DUNG: ssh buoc rollback loi — goi MASTER NGAY"; exit 1; }
echo "$RS"
echo "$RS" | grep -q '^FAIL' && { say "ROLLBACK CO FAIL — goi MASTER NGAY. Log: $LOG"; exit 1; }
say "Rollback xong. Gui log cho MASTER: $LOG"
