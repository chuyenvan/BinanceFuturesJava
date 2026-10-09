#!/usr/bin/env bash
# research/ops/health_242.sh — healthcheck host 242 chạy TRÊN ORACLE (cron */5). Runbook: docs/runbooks/HARDEN_242.md mục R4.
# - CHỈ ĐỌC trên 242: 1 phiên ssh / lần, pgrep + tail log + redis-cli cluster info + systemctl is-active. KHÔNG restart gì.
# - Cảnh báo qua Telegram nếu có file $TG_ENV (TG_TOKEN=..., TG_CHAT=...; chmod 600; KHÔNG commit). Không có ⇒ ghi
#   $STATE_DIR/ALERT_PENDING_NEED_OWNER_CHANNEL.txt (cần owner cấp kênh).
# - Báo khi vấn đề lặp >= CONSEC lần liên tiếp (mặc định 2 = 10 phút, tránh báo nhầm cửa sổ auto-restart 12h),
#   nhắc lại mỗi REMIND_SEC nếu còn lỗi, báo RECOVERED khi hết.
# Dùng: health_242.sh            (chế độ cron)
#       health_242.sh --dry-run  (in probe + quyết định, không gửi, không ghi state)
set -u
S242=${HEALTH242_SSH:-"ssh -p 2222 -o BatchMode=yes -o ConnectTimeout=15 -i /home/ubuntu/.ssh/id_rsa_chuyennd root@103.157.218.242"}
STATE_DIR=${HEALTH242_DIR:-/home/ubuntu/claude_master/health242}
TG_ENV=${HEALTH242_TG_ENV:-/home/ubuntu/.config/health242/tg.env}
MAX_AGE=${HEALTH242_MAX_AGE:-180}      # giây: log [LEGACY] managed / Update all position / Chốt nến phải mới hơn
CONSEC=${HEALTH242_CONSEC:-2}
REMIND_SEC=${HEALTH242_REMIND_SEC:-1800}
DISK_WARN=${HEALTH242_DISK_WARN:-92}
DRY=0; [ "${1:-}" = "--dry-run" ] && DRY=1
mkdir -p "$STATE_DIR"
exec 9>"$STATE_DIR/.lock"; flock -n 9 || { echo "lock busy"; exit 0; }
now=$(date +%s); stamp=$(date '+%F %T%z')
log(){ [ $DRY = 1 ] && echo "$*" || echo "$stamp $*" >> "$STATE_DIR/health.log"; }

# ---- probe trên 242 (chỉ đọc) ----
read -r -d '' REMOTE <<'EOF'
now=$(date +%s)
age(){ l=$(tail -c 3000000 "$1" 2>/dev/null | grep -F "$2" | tail -1); [ -z "$l" ] && { echo -1; return; }
  ts=$(echo "$l" | awk '{split($1,d,"/"); print d[3]"-"d[2]"-"d[1]" "substr($2,1,8)}')
  t=$(date -d "$ts" +%s 2>/dev/null) || { echo -1; return; }; echo $((now-t)); }
A=/home/chuyennd/java/v_t_m/logs/full.log; C=/home/chuyennd/java/collectData/logs/full.log
echo "trading_n=$(pgrep -fc -- '-cp target/binance-java-sdk-1.2.4.jar com.binance.chuyennd.trading.BinanceOrderTradingManager')"
echo "ingest_n=$(pgrep -fc -- '-cp target/binance-java-sdk-1.2.4.jar com.binance.chuyennd.websocket.BinanceDataIngestor')"
echo "legacy_age=$(age $A '[LEGACY] managed')"
echo "legacy_n=$(tail -c 3000000 $A 2>/dev/null | grep -F '[LEGACY] managed' | tail -1 | grep -oE 'managed [0-9]+' | awk '{print $2}')"
echo "updpos_age=$(age $A 'Update all position')"
echo "kline_age=$(age $C 'Chốt nến phút')"
st=; for p in 30001 30002 30003 30004 30005 30006; do
  st=$(timeout 5 /opt/setup/redis-7.0.8/src/redis-cli -h 103.157.218.242 -p $p cluster info 2>/dev/null | tr -d '\r' | awk -F: '/^cluster_state/{print $2}')
  [ -n "$st" ] && break; done; echo "redis_state=${st:-noreply}"
echo "aero_active=$(systemctl is-active aerospike 2>/dev/null)"
echo "aero_port=$(timeout 3 bash -c '</dev/tcp/103.157.218.242/3222' 2>/dev/null && echo up || echo down)"
echo "disk_pct=$(df -P / | awk 'NR==2{gsub("%","",$5);print $5}')"
echo "mem_avail_mb=$(free -m | awk '/^Mem:/{print $7}')"
echo "probe_ok=1"
EOF
OUT=$($S242 'bash -s' <<<"$REMOTE" 2>/dev/null)
declare -A V; while IFS='=' read -r k v; do [ -n "$k" ] && V[$k]=$v; done <<<"$OUT"
g(){ echo "${V[$1]:-}"; }

# ---- đánh giá ----
P=()
stale(){ local a; a=$(g "$1"); [ -z "$a" ] || [ "$a" -lt 0 ] 2>/dev/null || [ "$a" -gt "$MAX_AGE" ] 2>/dev/null; }
if [ "$(g probe_ok)" != 1 ]; then P+=("UNREACHABLE(ssh 242 fail)")
else
  [ "$(g trading_n)" -ge 1 ] 2>/dev/null || P+=("TRADING_DOWN")
  stale legacy_age && P+=("LEGACY_STALE(age=$(g legacy_age)s)")
  stale updpos_age && P+=("UPDPOS_STALE(age=$(g updpos_age)s)")
  [ "$(g ingest_n)" -ge 1 ] 2>/dev/null || P+=("INGEST_DOWN")
  stale kline_age && P+=("KLINE_STALE(age=$(g kline_age)s)")
  [ "$(g redis_state)" = ok ] || P+=("REDIS_$(g redis_state)")
  { [ "$(g aero_active)" = active ] && [ "$(g aero_port)" = up ]; } || P+=("AEROSPIKE_$(g aero_active)_$(g aero_port)")
  [ "$(g disk_pct)" -lt "$DISK_WARN" ] 2>/dev/null || P+=("DISK_$(g disk_pct)pct")
fi
cur=$(printf '%s\n' "${P[@]:-}" | sed 's/(.*//' | sort -u | tr '\n' ' ' | sed 's/ *$//')
summary="trading_n=$(g trading_n) legacy_n=$(g legacy_n) legacy_age=$(g legacy_age) updpos_age=$(g updpos_age) ingest_n=$(g ingest_n) kline_age=$(g kline_age) redis=$(g redis_state) aero=$(g aero_active)/$(g aero_port) disk=$(g disk_pct)% mem_avail=$(g mem_avail_mb)MB"
send(){ local msg="[242-HEALTH] $1"
  if [ $DRY = 1 ]; then echo "WOULD_SEND: $msg"; return; fi
  if [ -r "$TG_ENV" ]; then ( . "$TG_ENV"
      printf 'url = "https://api.telegram.org/bot%s/sendMessage"\n' "$TG_TOKEN" | curl -s -m 15 -o /dev/null -w '%{http_code}' -K - \
        --data-urlencode "chat_id=$TG_CHAT" --data-urlencode "text=$msg" ) > "$STATE_DIR/.last_send_http" 2>&1
    log "SENT http=$(cat "$STATE_DIR/.last_send_http") $msg"
  else echo "$stamp $msg" >> "$STATE_DIR/ALERT_PENDING_NEED_OWNER_CHANNEL.txt"; log "NO_CHANNEL $msg"; fi; }

# ---- state: last_set, consec, last_alert_ts, alerted ----
SF="$STATE_DIR/state"; last_set=; consec=0; last_alert=0; alerted=0
[ -r "$SF" ] && . "$SF"
if [ -n "$cur" ]; then
  if [ "$cur" = "$last_set" ]; then consec=$((consec+1)); else consec=1; fi
  if [ "$consec" -ge "$CONSEC" ] && { [ "$alerted" = 0 ] || [ $((now-last_alert)) -ge "$REMIND_SEC" ]; }; then
    send "FAIL: ${P[*]} | $summary"; last_alert=$now; alerted=1
  fi
  log "FAIL consec=$consec ${P[*]} | $summary"
else
  [ "$alerted" = 1 ] && send "RECOVERED | $summary"
  consec=0; alerted=0; log "OK | $summary"
fi
if [ $DRY = 0 ]; then
  printf 'last_set=%q\nconsec=%s\nlast_alert=%s\nalerted=%s\n' "$cur" "$consec" "$last_alert" "$alerted" > "$SF.tmp" && mv -f "$SF.tmp" "$SF"
  printf '%s %s\n' "$stamp" "${cur:-OK}" > "$STATE_DIR/last_status"
else
  echo "--- probe raw ---"; echo "$OUT"; echo "--- decision: problems='${cur:-none}' consec_next=$consec"
fi
exit 0
