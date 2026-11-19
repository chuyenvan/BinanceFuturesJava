#!/usr/bin/env bash
# =============================================================================
# c3_oracle_seen_242.sh - [OPS5 muc 2b] (cai tren 242: /usr/local/sbin/c3_oracle_seen.sh, cron root */5 boi install_242_oracle_seen.sh)
#   242 tu biet giam sat Oracle con "cham" khong, KHONG can Oracle ghi gi len 242 (giu nguyen tac chi-doc cua monitor/deadman):
#   moi luot doc cua deadman (*/2) / monitor (*/2) tao dong sshd "Accepted publickey for root from <ORACLE_IP>" trong /var/log/secure.
#   Dong cuoi cu > OS_MAX_S (900 s) => Telegram (kenh watchdog 242) "Oracle KHONG cham 242": Oracle chet / mat mang / cron deadman chet.
#   Chong spam: 1 lan / OS_REMIND_S (1800 s) + tin "DA HOI PHUC". Khong thay dong nao (log vua xoay) => tinh tu luc bat dau khong thay.
# Bien (test): OS_ORACLE_IP OS_AUTHLOG OS_MAX_S OS_REMIND_S OS_STATE_DIR OS_TG_ENV OS_TG_SINK OS_NOW
# =============================================================================
set -uo pipefail
IP=${OS_ORACLE_IP:-161.118.212.3}; LF=${OS_AUTHLOG:-/var/log/secure}; MX=${OS_MAX_S:-900}; RM=${OS_REMIND_S:-1800}
ST=${OS_STATE_DIR:-/var/lib/c3_oracle_seen}; TG_ENV=${OS_TG_ENV:-/root/.config/h242_watchdog/tg.env}
NOW=${OS_NOW:-$(date +%s)}
mkdir -p "$ST" 2>/dev/null; SF=$ST/state
log() { echo "$(date '+%F %T%z') $*" >> "$ST/oracle_seen.log" 2>/dev/null; echo "$*"; }
tg() {
  local msg tok chat code
  msg=$(printf '%s' "$1" | sed -E 's/[0-9]{8,10}:[A-Za-z0-9_-]{30,}/[CHE]/g' | head -c 2000)
  if [ -n "${OS_TG_SINK:-}" ]; then { printf '%s\n' "$msg"; echo "----"; } >> "$OS_TG_SINK"; return 0; fi
  [ -r "$TG_ENV" ] || { log "NO_CHANNEL"; return 1; }
  tok=$(sed -nE 's/^[[:space:]]*(export[[:space:]]+)?(TG_TOKEN=|tele-token:[[:space:]]*)//p' "$TG_ENV" | head -1 | tr -d '\r"')
  chat=$(sed -nE 's/^[[:space:]]*(export[[:space:]]+)?(TG_CHAT=|tele-chat-id:[[:space:]]*)//p' "$TG_ENV" | head -1 | tr -d '\r"')
  [ -n "$tok" ] && [ -n "$chat" ] || return 1
  code=$(printf 'url = "https://api.telegram.org/bot%s/sendMessage"\n' "$tok" | curl -s -m 15 -o /dev/null -w '%{http_code}' -K - \
    --data-urlencode "chat_id=$chat" --data-urlencode "text=$msg" 2>/dev/null); tok=""; chat=""
  [ "$code" = 200 ]
}
A0=$(sed -n 's/^alert_since=//p' "$SF" 2>/dev/null | head -1); S0=$(sed -n 's/^sent=//p' "$SF" 2>/dev/null | head -1); N0=$(sed -n 's/^nomatch_since=//p' "$SF" 2>/dev/null | head -1)
L=$(tail -c 3000000 "$LF" 2>/dev/null | grep -a "Accepted publickey for [a-z]* from $IP " | tail -1 | cut -c1-15)
if [ -n "$L" ]; then
  T=$(date -d "$L" +%s 2>/dev/null || echo 0); [ "$T" -gt $((NOW + 86400)) ] && T=$(date -d "$L 1 year ago" +%s 2>/dev/null || echo 0)
  AGE=$((NOW - T)); N0=""; WHY="lan cham cuoi ($L) cach ${AGE}s"
else
  N0=${N0:-$NOW}; AGE=$((NOW - N0)); WHY="khong thay dong ssh nao tu $IP trong $LF (tu $(date -d @"$N0" '+%d/%m %H:%M'), ${AGE}s)"
fi
if [ "$AGE" -gt "$MX" ]; then
  A0=${A0:-$NOW}
  if [ $((NOW - ${S0:-0})) -ge "$RM" ]; then
    tg "[242-ORACLE-SEEN] CANH BAO: Oracle ($IP) KHONG cham 242 > ${MX}s - $WHY. Giam sat golive (monitor/deadman) co the da chet; kiem Oracle + mang. Bot van chay (khong tu dong gi)." && S0=$NOW
  fi
  log "CANH BAO $WHY"; RC=2
else
  if [ -n "${A0:-}" ]; then tg "[242-ORACLE-SEEN] DA HOI PHUC: Oracle cham lai 242 ($WHY), mat tu $(date -d @"$A0" '+%d/%m %H:%M')" && { A0=""; S0=""; }; fi
  log "OK $WHY"; RC=0
fi
printf 'alert_since=%s\nsent=%s\nnomatch_since=%s\n' "${A0:-}" "${S0:-}" "${N0:-}" > "$SF.tmp" && mv -f "$SF.tmp" "$SF"
exit $RC
