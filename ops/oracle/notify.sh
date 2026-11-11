#!/usr/bin/env bash
# notify.sh "<message>" -> gui tin ngan Telegram TRUC TIEP (api.telegram.org) bang ~/.config/health242/tg.env, cung cach health_242.sh.
# [11-11 MASTER] Bo phu thuoc gateway openclaw (ban cu gui qua conversations.send cua gateway — giu o notify.sh.bak_*).
# Nguoi goi: ~/ops/mem_watchdog.sh (canh bao RAM can). Token KHONG vao argv (curl -K - qua stdin) va KHONG bao gio in ra.
#   NOTIFY_DRY=1  : chi in payload (token che: do dai + sha8), KHONG gui.
#   NOTIFY_TG_ENV : duong dan tg.env khac (mac dinh ~/.config/health242/tg.env; dang 'tele-token:'/'tele-chat-id:' hoac TG_TOKEN=/TG_CHAT=).
set -uo pipefail
MSG="${1:-}"; [ -n "$MSG" ] || { echo "notify: thieu message" >&2; exit 2; }
TG_ENV=${NOTIFY_TG_ENV:-/home/ubuntu/.config/health242/tg.env}
[ -r "$TG_ENV" ] || { echo "notify: khong doc duoc $TG_ENV" >&2; exit 1; }
TG_TOKEN=$(sed -nE 's/^[[:space:]]*(export[[:space:]]+)?(TG_TOKEN=|tele-token:[[:space:]]*)//p' "$TG_ENV" | head -1 | tr -d '\r"')
TG_CHAT=$(sed -nE 's/^[[:space:]]*(export[[:space:]]+)?(TG_CHAT=|tele-chat-id:[[:space:]]*)//p' "$TG_ENV" | head -1 | tr -d '\r"')
[ -n "$TG_TOKEN" ] && [ -n "$TG_CHAT" ] || { echo "notify: $TG_ENV thieu token/chat" >&2; exit 1; }
if [ "${NOTIFY_DRY:-0}" = 1 ]; then
  printf 'DRY url=https://api.telegram.org/bot<%s ky tu, sha8 %s>/sendMessage chat_id=***%s text=%s\n' \
    "${#TG_TOKEN}" "$(printf %s "$TG_TOKEN" | sha256sum | cut -c1-8)" "${TG_CHAT: -4}" "$MSG"
  exit 0
fi
code=$(printf 'url = "https://api.telegram.org/bot%s/sendMessage"\n' "$TG_TOKEN" | curl -s -m 15 -o /dev/null -w '%{http_code}' -K - \
  --data-urlencode "chat_id=$TG_CHAT" --data-urlencode "text=$MSG")
[ "$code" = 200 ] || { echo "notify: http=$code" >&2; exit 1; }
