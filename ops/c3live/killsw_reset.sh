#!/usr/bin/env bash
# =============================================================================
# killsw_reset.sh (ban OWNER chay tren ORACLE) — mo latch kill-switch c3_live tren 242 bang ops/killsw_reset.sh CUA BOT
# (deploy_v12_dry.sh da chep vao $APP_DIR/ops/). KHONG restart, KHONG goi san; bot ap dung trong ~15 s.
#   bash ~/claude_master/deploy/killsw_reset.sh              # mac dinh DRY: chi in trang thai latch
#   DRY=0 bash ~/claude_master/deploy/killsw_reset.sh        # mo latch: go YES
#   DRY=0 RESET_PEAK=1 bash ...                              # + dat lai dinh equity A40 (chi khi nap/rut von co chu dich)
# Luu y v1.2 vong 2b: C4 (cong suat) KHONG con latch (tu go); C1/C3/C5 tu go sau 30' sach; C2/C6/A40 can script nay.
# =============================================================================
set -uo pipefail
SSH_242=${SSH_242:-"ssh -p 2222 -o BatchMode=yes -o ConnectTimeout=20 -i /home/ubuntu/.ssh/id_rsa_chuyennd root@103.157.218.242"}
A=${APP_DIR:-/home/chuyennd/java/v_t_m}
DRY=${DRY:-1}
RESET_PEAK=${RESET_PEAK:-0}
case "$RESET_PEAK" in 0|1) ;; *) echo "RESET_PEAK phai la 0 hoac 1"; exit 2;; esac
LOGDIR=${LOGDIR:-/home/ubuntu/claude_master/deploy}
mkdir -p "$LOGDIR"
LOG=$LOGDIR/killsw_reset_$(TZ=Asia/Ho_Chi_Minh date +%Y%m%d_%H%M).log
exec > >(tee -a "$LOG") 2>&1

echo "== trang thai latch tren 242 (chi doc):"
$SSH_242 "cd $A && [ -f ops/killsw_reset.sh ] && DRY=1 RUN_DIR=run bash ops/killsw_reset.sh" \
  || { echo "DUNG: khong chay duoc ops/killsw_reset.sh tren 242 (chua deploy v1.2?)"; exit 1; }
if [ "$DRY" != 0 ]; then
  echo "== DRY: khong ghi gi. Muon mo latch: DRY=0 bash $0"
  exit 0
fi
echo "== Mo latch$( [ "$RESET_PEAK" = 1 ] && echo ' + DAT LAI dinh equity A40'). Dieu kien con dat => bot latch LAI ngay."
read -r -p "Go YES de xac nhan: " ANS
[ "$ANS" = "YES" ] || { echo "== Huy."; exit 3; }
printf 'YES\n' | $SSH_242 "cd $A && DRY=0 RESET_PEAK=$RESET_PEAK RUN_DIR=run WAIT_S=${WAIT_S:-40} bash ops/killsw_reset.sh"
echo "== Xong. Log: $LOG (gui MASTER)"
