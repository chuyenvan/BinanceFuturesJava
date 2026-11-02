#!/usr/bin/env bash
# =============================================================================
# c3live_status.sh — trang thai c3_live tren 242 (CHI DOC: khong ghi, khong restart, khong goi san)
# Chay tren ORACLE:  bash ~/claude_master/deploy/c3live_status.sh
# In: process/jar/env, latch kill-switch, so that/dry (so cum, da arm, stop mo), ledger gan nhat, doi chieu equity,
#     user stream, so dong [LIVE-DRY]/[C3-LIVE-ORDER], loi 1h qua.
# =============================================================================
set -uo pipefail
SSH_242=${SSH_242:-"ssh -p 2222 -o BatchMode=yes -o ConnectTimeout=20 -i /home/ubuntu/.ssh/id_rsa_chuyennd root@103.157.218.242"}
A=${APP_DIR:-/home/chuyennd/java/v_t_m}
PROC_PAT=${PROC_PAT:-BinanceOrderTradingManager}   # mau nhan dien process app (test: process gia)
$SSH_242 "PP='$PROC_PAT' CT='${CRONTAB_CMD:-crontab}' bash -s -- $A" <<'EOF'
A=$1; cd "$A" || { echo "FAIL cd $A"; exit 1; }
L=logs/full.log
P=$(pgrep -f "$PP" | head -1)
echo "== process pid=${P:-KHONG_CO} so=$(pgrep -fc "$PP") jar=$(md5sum < target/binance-java-sdk-1.2.4.jar | cut -c1-32)"
if [ -n "$P" ]; then
  tr '\0' '\n' < /proc/$P/environ 2>/dev/null | grep -E '^(LIVE_PROFILE|LIVE_ADAPTER|LIVE_KILLSW_MODE|SHADOW_NO_PUSH|LIVE_ENTRY_ENABLED|LIVE_TS_MKT_EXT|LIVE_C3_[A-Z_]*|UNIVERSE_A1[A-Z_]*)=' | sed 's/^/   env /'
fi
[ -f run/heartbeat ] && echo "== heartbeat tuoi=$(( $(date +%s) - $(stat -c %Y run/heartbeat) ))s" || echo "== heartbeat: chua co"
X=run/c3live_exchangeInfo.json   # [R4e] nguon A1 + R7 (cron lam moi tren 242)
[ -f "$X" ] && echo "== exchangeInfo: tuoi=$(( $(date +%s) - $(stat -c %Y "$X") ))s lam_moi: $(tr '\n' ' ' < run/c3live_exinfo_refresh.state 2>/dev/null)" || echo "== exchangeInfo: chua co $X"
[ -f "$X.meta" ] && echo "== exchangeInfo sidecar (R4n luc tai): $(cat "$X.meta")" || echo "== exchangeInfo sidecar: CHUA CO"
echo "== cron lam moi: $($CT -l 2>/dev/null | grep -cF '# C3LIVE_EXINFO_REFRESH') dong; [UNIVERSE-A1]: $(grep -a '\[UNIVERSE-A1\] BAT' $L | tail -1 | grep -o 'TradFi=[0-9]*, INDEX=[0-9]*')"
echo "== [OI-GUARD-2] oi_feat STALE (INFO): $(grep -a -c '\[OI-GUARD-2\].*STALE' $L) dong; gan nhat: $(grep -a '\[OI-GUARD-2\].*STALE' $L | tail -1 | cut -c1-160)"
echo "== kill-switch latch: $( [ -f run/killsw_latch.json ] && cat run/killsw_latch.json || echo '(chua co file = chua latch)')"
grep -a '\[KILLSW\]' $L | grep -a 'LATCH\|AUTO_RELEASE\|C4_CAPACITY\|RESET' | tail -5 | sed 's/^/   /'
B=run/c3live_book.json
if [ -f "$B" ]; then
  echo "== so c3_live ($B, $(stat -c %y "$B" | cut -c1-19)): cum=$(grep -o '"symbol":"' "$B" | wc -l) da_arm=$(grep -o '"armed":true' "$B" | wc -l) stop_active=$(grep -o '"stop_cid":"' "$B" | wc -l) stop_pending=$(grep -o '"pending_stop_cid":"' "$B" | wc -l) leg_treo=$(grep -o '"state":"\(PENDING\|SENDING\|UNKNOWN\)"' "$B" | wc -l)"
  grep -o '"symbol":"[^"]*"' "$B" | cut -d'"' -f4 | tr '\n' ' ' | sed 's/^/   cum: /'; echo
else
  echo "== so c3_live: chua co $B"
fi
D=run/c3live_dry_state.json
[ -f "$D" ] && echo "== dry: vi the=$(grep -o '"cost":"' "$D" | wc -l) stop_mo=$(grep -o '"status":"NEW"' "$D" | wc -l)"
[ -f run/c3live_ledger.csv ] && { echo "== ledger (5 dong cuoi):"; tail -5 run/c3live_ledger.csv | sed 's/^/   /'; }
echo "== doi chieu equity / reconcile:"
grep -a '\[C3-LIVE-RECON\]' $L | tail -3 | cut -c1-400 | sed 's/^/   /'
echo "== HOURLY:"
grep -a '\[C3-LIVE\] HOURLY' $L | tail -1 | cut -c1-600 | sed 's/^/   /'
echo "== user stream:"
grep -a '\[C3-LIVE-STREAM\]' $L | tail -3 | cut -c1-300 | sed 's/^/   /'
echo "== bo nho process (R4h, ro native): $( [ -n "$P" ] && grep -E '^(VmRSS|VmHWM|Threads):' /proc/$P/status 2>/dev/null | tr -s ' \t' ' ' | tr '\n' ' ')"
grep -a '\[OPS-PROC\]' $L | tail -3 | cut -c1-250 | sed 's/^/   /'
echo "== trailing:"
grep -a '\[C3-LIVE-TRAIL\]' $L | tail -5 | cut -c1-300 | sed 's/^/   /'
echo "== dem dong: [LIVE-DRY]=$(grep -a -c '\[LIVE-DRY\]' $L) [C3-LIVE-ORDER]=$(grep -a -c '\[C3-LIVE-ORDER\]' $L) SUBMIT=$(grep -a -c '\[C3-LIVE\] SUBMIT' $L)"
H1=$(date -d '1 hour ago' '+%d/%m/%Y %H')
echo "== loi trong log (ERROR/Exception, bo 'Picked up'): $(grep -a -v 'Picked up' $L | grep -a -c ' ERROR \|Exception')"
EOF
