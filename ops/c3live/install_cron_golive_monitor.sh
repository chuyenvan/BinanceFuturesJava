#!/usr/bin/env bash
# =============================================================================
# install_cron_golive_monitor.sh — [A1 ADD4 C-1] OWNER chay tren ORACLE: cai (hoac go) lich chay golive_monitor.sh trong crontab user ubuntu.
#   bash ~/claude_master/v12/c3live/ops/c3live/install_cron_golive_monitor.sh            # cai (idempotent: da co dung dong => khong doi)
#   bash ~/claude_master/v12/c3live/ops/c3live/install_cron_golive_monitor.sh --remove   # go
#   DRY=1 ...                                                                            # chi in truoc/sau, KHONG ghi
# Dong cron (1 dong, danh dau "# golive_monitor (ADD4 C-1)"):
#   */2 * * * * flock -n <khoa rieng> env MONITOR_CRON=1 bash <repo>/ops/c3live/golive_monitor.sh >/dev/null 2>&1
#   - chu ky 2 phut: moi luot 90 weight IP (v3/account 5 + v3/positionRisk 5 + openOrders 40 + openAlgoOrders 40), chi khi co co
#     micro/pilot (~/claude_master/deploy/golive_monitor.on); khong co co => thoat ngay, 0 ssh / 0 call.
#   - flock -n ~/claude_master/locks/golive_monitor.lock (KHONG dung oracle_heavy.lock): luot truoc chua xong => bo luot nay.
#   - log: ~/claude_master/deploy/golive_monitor_cron.log (monitor tu xoay > 20 MB).
# Cac dong cron khac GIU NGUYEN. In crontab truoc / sau. Ma thoat 0 OK | 1 loi.
# =============================================================================
set -uo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
ORA_CRONTAB_CMD=${ORA_CRONTAB_CMD:-crontab}
LOCKF=${MON_LOCK:-/home/ubuntu/claude_master/locks/golive_monitor.lock}
MON_MIN=${MON_MIN:-2}
DRY=${DRY:-0}
TAG='# golive_monitor (ADD4 C-1)'
MODE=install; [ "${1:-}" = --remove ] && MODE=remove
[ -z "${1:-}" ] || [ "$1" = --remove ] || { echo "dung: $0 [--remove]"; exit 1; }
[[ "$MON_MIN" =~ ^[12]$ ]] || { echo "MON_MIN chi 1 | 2"; exit 1; }
[ -f "$HERE/golive_monitor.sh" ] || { echo "thieu $HERE/golive_monitor.sh"; exit 1; }
SCHED='*/2'; [ "$MON_MIN" = 1 ] && SCHED='*'
LINE="$SCHED * * * * /usr/bin/flock -n $LOCKF /usr/bin/env MONITOR_CRON=1 /bin/bash $HERE/golive_monitor.sh >/dev/null 2>&1 $TAG"
BEFORE=$($ORA_CRONTAB_CMD -l 2>/dev/null) || BEFORE=""
echo "=== crontab TRUOC ($MODE):"; [ -n "$BEFORE" ] && printf '%s\n' "$BEFORE" | sed 's/^/   /' || echo "   (trong)"
REST=$(printf '%s\n' "$BEFORE" | grep -vF "$TAG" | sed '/^$/d')
if [ "$MODE" = install ]; then AFTER=$(printf '%s\n%s\n' "$REST" "$LINE" | sed '/^$/d'); else AFTER=$REST; fi
if [ "$(printf '%s\n' "$BEFORE" | sed '/^$/d')" = "$AFTER" ]; then
  echo "=== KHONG DOI (da dung trang thai $MODE — idempotent)"
  exit 0
fi
if [ "$DRY" = 1 ]; then
  echo "=== DRY=1: crontab SAU se la:"; [ -n "$AFTER" ] && printf '%s\n' "$AFTER" | sed 's/^/   /' || echo "   (trong)"; exit 0
fi
mkdir -p "$(dirname "$LOCKF")" || { echo "khong tao duoc thu muc khoa"; exit 1; }
printf '%s\n' "$AFTER" | $ORA_CRONTAB_CMD - || { echo "LOI ghi crontab"; exit 1; }
GOT=$($ORA_CRONTAB_CMD -l 2>/dev/null) || GOT=""
echo "=== crontab SAU:"; [ -n "$GOT" ] && printf '%s\n' "$GOT" | sed 's/^/   /' || echo "   (trong)"
N=$(printf '%s\n' "$GOT" | grep -cF "$TAG")
if [ "$MODE" = install ]; then
  [ "$N" = 1 ] && printf '%s\n' "$GOT" | grep -qxF "$LINE" || { echo "LOI: sau khi cai khong thay dung 1 dong monitor"; exit 1; }
  echo "=== XONG: cai cron golive_monitor ${MON_MIN}' (chi chay khi co co micro/pilot)"
else
  [ "$N" = 0 ] || { echo "LOI: van con dong monitor"; exit 1; }
  echo "=== XONG: da go cron golive_monitor"
fi
