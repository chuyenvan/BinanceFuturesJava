#!/usr/bin/env bash
# =============================================================================
# rollback_v12.sh — quay 242 ve truoc deploy_v12_dry.sh (jar dcae2e2b + env.sh + start.sh cu, c3_shadow)
# Chay tren ORACLE:  bash ~/claude_master/deploy/rollback_v12.sh <TS>
#   <TS> = gia tri TS in o dau log deploy_v12dry (dang 20261118_0915)
# Thu (chi doc): DRY=1 bash ~/claude_master/deploy/rollback_v12.sh <TS>
# [2c] Chot gio nhu deploy (khan cap: FORCE_TIME=1). YES_AUTO=1 chi danh cho rollback tu dong cua deploy_v12_dry.sh.
# KHONG xoa so dry (run/c3live_*): doi ten .rb_<TS> de lan deploy sau bat dau sach (so dry khong co tien that).
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

say "=== rollback v1.2 -> dcae2e2b (c3_shadow) TS=$TS DRY=$DRY ==="
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
PRE=$($SSH_242 "PP='$PROC_PAT' bash -s -- $A $TS $OLD_MD5" <<'EOF'
A=$1; TS=$2; OLD=$3; cd "$A" || { echo "FAIL cd"; exit 0; }
for f in target/binance-java-sdk-1.2.4.jar.bak_v12pre_$TS conf/env.sh.bak_v12pre_$TS bin/start.sh.bak_v12pre_$TS; do
  [ -f "$f" ] && echo "OK co $f" || echo "FAIL thieu backup $f"
done
J=$(md5sum < target/binance-java-sdk-1.2.4.jar.bak_v12pre_$TS 2>/dev/null | cut -c1-32)
[ "$J" = "$OLD" ] && echo "OK backup_jar_md5=$J" || echo "FAIL backup_jar_md5=$J (mong $OLD)"
echo "INFO jar_dang_chay=$(md5sum < target/binance-java-sdk-1.2.4.jar | cut -c1-32) so_process=$(pgrep -fc "$PP")"
echo "INFO so_dry: $(ls run/c3live_* 2>/dev/null | tr '\n' ' ')"
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
RS=$($SSH_242 "PP='$PROC_PAT' bash -s -- $A $TS $OLD_MD5 $WD_PAUSE" <<'EOF'
A=$1; TS=$2; OLD=$3; PAUSE=$4; cd "$A" || { echo "FAIL cd"; exit 0; }
touch "$PAUSE" 2>/dev/null
bin/daemon.sh stop
for i in $(seq 1 30); do pgrep -f "$PP" >/dev/null || break; sleep 2; done
pgrep -f "$PP" >/dev/null && { echo "FAIL van con process"; rm -f "$PAUSE"; exit 0; }
\cp -f target/binance-java-sdk-1.2.4.jar.bak_v12pre_$TS target/binance-java-sdk-1.2.4.jar
\cp -f conf/env.sh.bak_v12pre_$TS conf/env.sh
\cp -f bin/start.sh.bak_v12pre_$TS bin/start.sh
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
rm -f "$PAUSE"
EOF
) || { say "DUNG: ssh buoc rollback loi — goi MASTER NGAY"; exit 1; }
echo "$RS"
echo "$RS" | grep -q '^FAIL' && { say "ROLLBACK CO FAIL — goi MASTER NGAY. Log: $LOG"; exit 1; }
say "Rollback xong. Gui log cho MASTER: $LOG"
