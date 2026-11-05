#!/usr/bin/env bash
# =============================================================================
# golive_monitor.sh — [V12 R4o] 1 LENH, CHI DOC: trang thai tong c3_live tren 242 (khong ghi, khong restart, khong goi san).
#   bash ~/claude_master/v12/c3live/ops/c3live/golive_monitor.sh
# In: process/jar/env (adapter, C3_CAPITAL, push), PUSH (env + run/KILL_SWITCH), latch + dinh kill-switch, equity c3 / HOURLY,
#   so c3 (cum, da arm, stop c3s-), lenh c3 1 h qua, LEGACY, user stream, RAM/dia/RSS, weight/429/418/ban, KHAN/ERROR 1 h qua,
#   PAUSE watchdog, cron exinfo. Ket thuc bang dong TOM TAT.
# =============================================================================
set -uo pipefail
. "$(cd "$(dirname "$0")" && pwd)/golive_lib.sh"
say "=== golive_monitor (chi doc) ==="
gl_read_state
OUT=$(s242in "PP='$PROC_PAT' bash -s -- $A" <<'EOF'
A=$1; cd "$A" || exit 0; L=logs/full.log
P=$(pgrep -f "$PP" | head -1)
H=$(tail -c 15000000 $L 2>/dev/null)
last() { echo "$H" | grep -a "$1" | tail -1 | cut -c1-${2:-260}; }
cnt1h() { local s; s=$(TZ=Asia/Ho_Chi_Minh date -d '-1 hour' '+%d/%m/%Y %H:%M'); echo "$H" | awk -v s="$s" '{t=$1" "substr($2,1,5); split(t,a,/[\/ :]/); k=a[3]a[2]a[1]a[4]a[5]; split(s,b,/[\/ :]/); ks=b[3]b[2]b[1]b[4]b[5]; if (k>=ks) print}' | grep -ac "$1"; }
echo "== process pid=$P lstart=$(ps -o lstart= -p $P 2>/dev/null) rss_mb=$(( $(ps -o rss= -p $P 2>/dev/null || echo 0) / 1024 )) threads=$(ls /proc/$P/task 2>/dev/null | wc -l)"
PL=$(echo "$H" | grep -a 'PUSH doi trang thai\|PUSH=ON\|PUSH=OFF' | tail -1)
echo "== PUSH (log): $(echo "$PL" | cut -c1-23) $(echo "$PL" | grep -oE 'PUSH( doi trang thai ->)?[= ]*(ON|OFF)' | tail -1)"
echo "== KILL_SWITCH file: $([ -e run/KILL_SWITCH ] && echo "CO ($(head -c 80 run/KILL_SWITCH))" || echo khong)"
echo "== latch: $(head -c 300 run/killsw_latch.json 2>/dev/null || echo chua_co)"
echo "== dinh A40/C6: $(cat run/c3live_killsw_peak 2>/dev/null || echo chua_co)"
echo "== equity: $(last '\[C3-LIVE-EQ\]' 220)"
echo "== HOURLY: $(last '\[C3-LIVE\] HOURLY' 400)"
echo "== recon: $(last 'C3-LIVE-RECON\] HOURLY' 220)"
B=run/c3live_book.json
[ -f $B ] && echo "== so c3: cum=$(grep -o '"symbol":"' $B | wc -l) da_arm=$(grep -o '"armed":true' $B | wc -l) stop_c3s=$(grep -o '"stop_cid":"' $B | wc -l) sua=$(stat -c %y $B | cut -c1-19)" || echo "== so c3: chua co"
echo "== lenh c3 1h: EXEC=$(cnt1h '\[C3-LIVE-EXEC\]') FILL=$(cnt1h 'C3-LIVE-EXEC\] FILL') TU_CHOI=$(cnt1h 'TU CHOI')"
LG=$(echo "$H" | grep -a '\[LEGACY\] managed' | tail -1); LS=$(echo "$H" | grep -a 'LEGACY tren tai khoan chinh:' | tail -1)
echo "== LEGACY: $(echo "$LG" | cut -c1-23) $(echo "$LG" | grep -oE 'managed [0-9]+') | san(c3 scope): $(echo "$LS" | cut -c1-23) $(echo "$LS" | grep -oE 'chinh: [0-9]+ vi the')"
echo "== stream: $(last 'C3-LIVE-STREAM\]' 200)"
echo "== rate 1h: 429=$(cnt1h 'HTTP 429\|http=429\| 429 ') 418=$(cnt1h 'HTTP 418\|http=418\| 418 ') ban=$(cnt1h '"code":-1003\|code=-1003\|IP banned\|banned until') | $(last 'USED-WEIGHT\|weight=' 200)"
echo "== KHAN 1h=$(cnt1h 'KHAN') ERROR 1h=$(cnt1h ' ERROR ') | KHAN cuoi: $(last 'KHAN' 200)"
echo "== exinfo: tuoi=$(( $(date +%s) - $(stat -c %Y run/c3live_exchangeInfo.json 2>/dev/null || echo 0) ))s $(tr '\n' ' ' < run/c3live_exinfo_refresh.state 2>/dev/null | cut -c1-80)"
echo "== may: MemAvailable=$(awk '/MemAvailable/{print int($2/1024)}' /proc/meminfo)MB swap_free=$(awk '/SwapFree/{print int($2/1024)}' /proc/meminfo)MB dia=$(df -h . | awk 'NR==2{print $4" trong ("$5")"}')"
EOF
) || OUT="(ssh 242 loi)"
echo "$OUT"
echo "== PAUSE watchdog: $(sv PAUSE)  canary/soak=$(sv CANARY_SOAK)"
PUSH=OFF; [ "$(sv ENV_LIVE_ADAPTER)" = live ] && [ "$(sv ENV_SHADOW_NO_PUSH)" = false ] && [ "$(sv ENV_LIVE_ENTRY_ENABLED)" = true ] && [ "$(sv KILLSW_FILE)" = 0 ] && PUSH=ON
say "TOM TAT: adapter=$(sv ENV_LIVE_ADAPTER) C3_CAPITAL=$(sv ENV_C3_CAPITAL) push=$PUSH latch=$(sv LATCH) so_c3=$(sv BOOK_CUM)cum LEGACY=$(sv LEGACY_N) mem=$(sv MEM)MB jar=$(sv JAR_MD5 | cut -c1-8) pause=$(sv PAUSE | cut -c1)"
