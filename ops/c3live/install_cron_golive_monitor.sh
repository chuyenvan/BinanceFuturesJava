#!/usr/bin/env bash
# =============================================================================
# install_cron_golive_monitor.sh — [A1 ADD4 C-1] OWNER chay tren ORACLE: cai (hoac go) lich chay golive_monitor trong crontab user ubuntu.
#   $OPS = thu muc chua script nay (worktree A1 duyet: HEAD co trong deploy/gates/A1_APPROVED_OPS.commit; MASTER cap duong dan)
#   bash $OPS/install_cron_golive_monitor.sh            # cai / cap nhat pin (idempotent)
#   bash $OPS/install_cron_golive_monitor.sh --remove   # go dong cron (giu cac ban pin)
#   DRY=1 ...                                                                            # chi in truoc/sau, KHONG ghi
# [A1 delta MIN-4] PIN: chep golive_monitor.sh + golive_lib.sh (monitor source lib canh no) vao
#   ~/claude_master/deploy/pinned/golive_monitor_<md5_12>/ (md5_12 = md5(monitor + lib)[:12], chmod 444/555); cron CHI chay ban pin.
#   Chay lai sau khi repo doi => pin moi + dong cron tro pin moi (pin cu giu lai). Pin da co ma noi dung lech ten => TU CHOI.
# Dong cron (1 dong, danh dau "# golive_monitor (ADD4 C-1)"):
#   */2 * * * * flock -n <khoa rieng> timeout -k 10 100 env MONITOR_CRON=1 bash <pin>/golive_monitor.sh >/dev/null 2>&1
#   - 2 phut, 90 weight IP / luot (v3/account 5 + v3/positionRisk 5 + openOrders 40 + openAlgoOrders 40), CHI khi co co micro/pilot
#     (~/claude_master/deploy/golive_monitor.on); khong co co => thoat ngay, 0 ssh / 0 call.
#   - flock -n ~/claude_master/locks/golive_monitor.lock (KHONG oracle_heavy.lock): luot truoc chua xong => bo luot nay.
#   - [A1 delta MIN-1] timeout -k 10 100: ssh treo => giet ca nhom tien trinh sau 100 s (KILL sau 110 s) => tra flock.
#   - moi luot co co ghi heartbeat ~/claude_master/deploy/run/monitor_heartbeat (c3live_status.sh bao KHAN neu > 6').
#   - log: ~/claude_master/deploy/golive_monitor_cron.log (monitor tu xoay > 20 MB).
# Cac dong cron khac GIU NGUYEN. In crontab truoc / sau. Ma thoat 0 OK | 1 loi.
# =============================================================================
set -uo pipefail
# [WAVE1c m1 / OPS-MICRO3 n4] pin NGOAI repo, kiem TRUOC khi source lib (lib khong tu chung nhan): HEAD repo chua script = 1 commit A1/MASTER
#   duyet trong A1_APPROVED_OPS (deploy/gates/A1_APPROVED_OPS.commit, 1 dong/commit, script CHI DOC) + thu muc script KHONG co sua chua commit.
_OPS=$(cd "$(dirname "$0")" && pwd); _APO=${A1_APPROVED_OPS:-/home/ubuntu/claude_master/deploy/gates/A1_APPROVED_OPS.commit}; _PW=""
_HC=$(git -C "$_OPS" rev-parse --verify -q HEAD 2>/dev/null) || _PW="$_OPS khong phai repo git"
[ -n "$_PW" ] || { [ -f "$_APO" ] && grep -qE "^$_HC([[:space:]]|\$)" "$_APO"; } || _PW="HEAD $_HC CHUA duoc A1 duyet (khong co trong $_APO)"
[ -n "$_PW" ] || git -C "$_OPS" diff --quiet HEAD -- . 2>/dev/null || _PW="$_OPS co sua CHUA commit (git diff HEAD)"
[ -z "$_PW" ] || { echo "TU CHOI [m1]: $_PW - KHONG lam gi."; exit 1; }
HERE=$(cd "$(dirname "$0")" && pwd)
# [WAVE1b M5 / OPS-MICRO3 n4] nhu gl_manifest_check (golive_lib; script nay KHONG source lib): script + lib + moi file manifest khop md5
#   da commit, lech => TU CHOI truoc moi viec
MF=$HERE/GOLIVE_MANIFEST.md5
{ [ -s "$MF" ] && grep -qxE "[0-9a-f]{32}  install_cron_golive_monitor.sh" "$MF" && grep -qxE "[0-9a-f]{32}  golive_lib.sh" "$MF" \
  && (cd "$HERE" && md5sum -c --quiet --strict "$MF" >/dev/null 2>&1); } \
  || { echo "TU CHOI [M5]: file go-live KHAC manifest da commit ($MF): $(cd "$HERE" && md5sum -c --strict "$MF" 2>&1 | grep -v ': OK$' | head -5 | tr '\n' ' ') - KHONG lam gi."; exit 1; }
MON_SRC=${MON_SRC:-$HERE}                       # thu muc nguon golive_monitor.sh + golive_lib.sh (test: ban sua)
ORA_CRONTAB_CMD=${ORA_CRONTAB_CMD:-crontab}
LOCKF=${MON_LOCK:-/home/ubuntu/claude_master/locks/golive_monitor.lock}
PIN_ROOT=${MON_PIN_ROOT:-/home/ubuntu/claude_master/deploy/pinned}
MON_MIN=${MON_MIN:-2}
MON_TIMEOUT_S=${MON_TIMEOUT_S:-100}
DRY=${DRY:-0}
TAG='# golive_monitor (ADD4 C-1)'
MODE=install; [ "${1:-}" = --remove ] && MODE=remove
[ -z "${1:-}" ] || [ "$1" = --remove ] || { echo "dung: bash $HERE/install_cron_golive_monitor.sh [--remove]"; exit 1; }
[[ "$MON_MIN" =~ ^[12]$ ]] || { echo "MON_MIN chi 1 | 2"; exit 1; }
[[ "$MON_TIMEOUT_S" =~ ^[0-9]+$ ]] && [ "$MON_TIMEOUT_S" -ge 30 ] && [ "$MON_TIMEOUT_S" -le 110 ] || { echo "MON_TIMEOUT_S 30..110"; exit 1; }
BEFORE=$($ORA_CRONTAB_CMD -l 2>/dev/null) || BEFORE=""
echo "=== crontab TRUOC ($MODE):"; [ -n "$BEFORE" ] && printf '%s\n' "$BEFORE" | sed 's/^/   /' || echo "   (trong)"
REST=$(printf '%s\n' "$BEFORE" | grep -vF "$TAG" | sed '/^$/d')
if [ "$MODE" = install ]; then
  for f in golive_monitor.sh golive_lib.sh; do [ -f "$MON_SRC/$f" ] || { echo "thieu $MON_SRC/$f"; exit 1; }; done
  M12=$(cat "$MON_SRC/golive_monitor.sh" "$MON_SRC/golive_lib.sh" | md5sum | cut -c1-12)
  PIN=$PIN_ROOT/golive_monitor_$M12
  echo "=== pin: $PIN (md5(monitor+lib)[:12]=$M12; monitor $(md5sum < "$MON_SRC/golive_monitor.sh" | cut -c1-8), lib $(md5sum < "$MON_SRC/golive_lib.sh" | cut -c1-8))"
  SCHED='*/2'; [ "$MON_MIN" = 1 ] && SCHED='*'
  LINE="$SCHED * * * * /usr/bin/flock -n $LOCKF /usr/bin/timeout -k 10 $MON_TIMEOUT_S /usr/bin/env MONITOR_CRON=1 /bin/bash $PIN/golive_monitor.sh >/dev/null 2>&1 $TAG"
  AFTER=$(printf '%s\n%s\n' "$REST" "$LINE" | sed '/^$/d')
else
  AFTER=$REST
fi
pin_ok() { [ -f "$1/golive_monitor.sh" ] && [ -f "$1/golive_lib.sh" ] && [ "$(cat "$1/golive_monitor.sh" "$1/golive_lib.sh" | md5sum | cut -c1-12)" = "${1##*_}" ]; }
if [ "$MODE" = install ] && [ -e "$PIN" ] && ! pin_ok "$PIN"; then echo "LOI: pin $PIN da co nhung noi dung LECH ten — TU CHOI (owner xem tay)"; exit 1; fi
if [ "$(printf '%s\n' "$BEFORE" | sed '/^$/d')" = "$AFTER" ] && { [ "$MODE" = remove ] || pin_ok "$PIN"; }; then
  echo "=== KHONG DOI (da dung trang thai $MODE — idempotent)"
  exit 0
fi
if [ "$DRY" = 1 ]; then
  echo "=== DRY=1: crontab SAU se la:"; [ -n "$AFTER" ] && printf '%s\n' "$AFTER" | sed 's/^/   /' || echo "   (trong)"; exit 0
fi
mkdir -p "$(dirname "$LOCKF")" || { echo "khong tao duoc thu muc khoa"; exit 1; }
if [ "$MODE" = install ] && [ ! -e "$PIN" ]; then
  mkdir -p "$PIN_ROOT" && T=$(mktemp -d "$PIN_ROOT/.tmp_pin.XXXXXX") || { echo "LOI tao thu muc pin"; exit 1; }
  cp -p "$MON_SRC/golive_monitor.sh" "$MON_SRC/golive_lib.sh" "$T/" && chmod 444 "$T"/*.sh && chmod 555 "$T" && mv -T "$T" "$PIN" \
    || { chmod -R u+w "$T" 2>/dev/null; rm -rf "$T"; echo "LOI chep pin"; exit 1; }
  pin_ok "$PIN" || { echo "LOI: pin vua chep KHONG khop md5"; exit 1; }
  echo "=== OK chep pin $PIN"
fi
printf '%s\n' "$AFTER" | $ORA_CRONTAB_CMD - || { echo "LOI ghi crontab"; exit 1; }
GOT=$($ORA_CRONTAB_CMD -l 2>/dev/null) || GOT=""
echo "=== crontab SAU:"; [ -n "$GOT" ] && printf '%s\n' "$GOT" | sed 's/^/   /' || echo "   (trong)"
N=$(printf '%s\n' "$GOT" | grep -cF "$TAG")
if [ "$MODE" = install ]; then
  [ "$N" = 1 ] && printf '%s\n' "$GOT" | grep -qxF "$LINE" || { echo "LOI: sau khi cai khong thay dung 1 dong monitor"; exit 1; }
  echo "=== XONG: cai cron golive_monitor ${MON_MIN}' chay ban pin $PIN (chi chay khi co co micro/pilot)"
else
  [ "$N" = 0 ] || { echo "LOI: van con dong monitor"; exit 1; }
  echo "=== XONG: da go cron golive_monitor (cac ban pin giu lai)"
fi
