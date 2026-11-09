#!/usr/bin/env bash
# =============================================================================
# cleanup_docker_log_242.sh — truncate log json cua container docker DA DUNG tren 242 (owner dong y 11-09). Chay tren ORACLE.
#   bash ~/claude_master/deploy/cleanup_docker_log_242.sh            # MAC DINH DRY: chi liet ke + GB du kien
#   bash ~/claude_master/deploy/cleanup_docker_log_242.sh --apply    # truncate -s 0 cac file du dieu kien
# Dieu kien MOI file /var/lib/docker/containers/<id>/<id>-json.log (realpath phai nam trong thu muc nay):
#   config.v2.json cua container co "Running":false; file khong ghi trong DAYS (30) ngay; KHONG tien trinh nao mo (/proc/*/fd).
# ABORT truoc khi lam gi neu: khong doc duoc /proc, danh sach file dang mo rong, hoac dockerd/containerd dang chay.
# KHONG xoa thu muc container/image, KHONG start/stop docker, chi truncate. In df truoc/sau.
# Bien test: SSH_242 CL_DOCKER_DIR CL_PROC CL_DAEMON_PAT CL_LOGDIR DAYS
# =============================================================================
set -euo pipefail
S=${SSH_242:-"ssh -p 2222 -o BatchMode=yes -o ConnectTimeout=20 -o ServerAliveInterval=10 -o ServerAliveCountMax=6 -i /home/ubuntu/.ssh/id_rsa_chuyennd root@103.157.218.242"}
APPLY=0
case "${1:-}" in
  --apply) APPLY=1;;
  ""|--dry) APPLY=0;;
  *) echo "Dung: $0 [--apply]   (mac dinh DRY)"; exit 1;;
esac
DAYS=${DAYS:-30}
[ "$DAYS" -ge 30 ] 2>/dev/null || { echo "DAYS phai >= 30"; exit 1; }
CL_DOCKER_DIR=${CL_DOCKER_DIR:-/var/lib/docker/containers}; CL_PROC=${CL_PROC:-/proc}; CL_DAEMON_PAT=${CL_DAEMON_PAT:-'(^|/)(dockerd|containerd)( |$)'}
D=${CL_LOGDIR:-/home/ubuntu/claude_master/deploy}
TS=$(TZ=Asia/Ho_Chi_Minh date +%Y%m%d_%H%M%S)
SUF=""; if [ "$APPLY" = 0 ]; then SUF=_dry; fi
LOG=$D/cleanup_docker_log_242_${TS}${SUF}.log
exec > >(tee -a "$LOG") 2>&1
echo "[$(TZ=Asia/Ho_Chi_Minh date '+%F %T')] === cleanup_docker_log_242 APPLY=$APPLY DAYS=$DAYS dir=$CL_DOCKER_DIR ==="
set +e
$S "bash -s -- $APPLY $DAYS '$CL_DOCKER_DIR' '$CL_PROC' '$CL_DAEMON_PAT'" <<'EOF'
set -euo pipefail
APPLY=$1; DAYS=$2; DD=$3; PROC=$4; DPAT=$5
fail() { echo "ABORT/FAIL: $* => DUNG NGAY"; df -h / | tail -1; exit 1; }
gb() { awk -v b="$1" 'BEGIN{printf "%.2f GB", b/1073741824}'; }
echo "--- df TRUOC:"; df -h / | tail -1
DD=$(realpath -e -- "$DD") || fail "khong co $DD"
[ -r "$PROC/self/maps" ] || fail "khong doc duoc $PROC"
if pgrep -f -- "$DPAT" >/dev/null 2>&1; then fail "dockerd/containerd DANG CHAY ($(pgrep -af -- "$DPAT" | head -2 | tr '\n' ' ')) — khong truncate"; fi
echo "OK dockerd/containerd khong chay"
OPEN=$(find "$PROC" -mindepth 3 -maxdepth 3 -path "$PROC/[0-9]*/fd/*" -type l -printf '%l\n' 2>/dev/null | sort -u || true)
[ -n "$OPEN" ] || fail "danh sach file dang mo RONG ($PROC khong doc duoc?)"
TOTAL=0; N=0
while IFS= read -r -d '' f; do
  rp=$(realpath -e -- "$f") || fail "realpath $f"
  case "$rp" in "$DD"/*) ;; *) fail "duong dan ngoai $DD: $rp";; esac
  cdir=$(dirname -- "$rp"); id=$(basename -- "$cdir"); cfg="$cdir/config.v2.json"
  sz=$(stat -c %s -- "$rp"); mt=$(date -r "$rp" +%F)
  name=$(grep -o '"Name":"[^"]*"' "$cfg" 2>/dev/null | head -1 | cut -d'"' -f4 || true)
  img=$(grep -o '"Image":"[^"]*"' "$cfg" 2>/dev/null | head -1 | cut -d'"' -f4 || true)
  info="${id:0:12} ${name:-?} ${img:-?} $(gb "$sz") ghi_cuoi=$mt"
  if [ "$sz" = 0 ]; then echo "  BO QUA (da rong) $info"; continue; fi
  if ! grep -q '"Running":false' "$cfg" 2>/dev/null; then echo "  GIU (container khong xac nhan DA DUNG) $info"; continue; fi
  if [ -n "$(find "$rp" -mtime -"$DAYS" 2>/dev/null)" ]; then echo "  GIU (ghi trong $DAYS ngay) $info"; continue; fi
  if grep -qxF -- "$rp" <<< "$OPEN"; then echo "  GIU (dang mo) $info"; continue; fi
  TOTAL=$((TOTAL + sz)); N=$((N + 1))
  if [ "$APPLY" = 1 ]; then truncate -s 0 -- "$rp" || fail "truncate $rp"; echo "  DA truncate $info"; else echo "  SE truncate $info"; fi
done < <(find "$DD" -mindepth 2 -maxdepth 2 -type f -name '*-json.log' -print0)
echo "=== $([ "$APPLY" = 1 ] && echo 'DA truncate' || echo 'DRY: SE truncate') $N file, giai phong $([ "$APPLY" = 1 ] || echo 'du kien ')$(gb "$TOTAL")"
echo "--- df SAU:"; df -h / | tail -1
echo END_DOCKER_LOG
EOF
RC=$?
set -e
echo "[$(TZ=Asia/Ho_Chi_Minh date '+%F %T')] ssh rc=$RC. Log: $LOG"
exit "$RC"
