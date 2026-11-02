#!/usr/bin/env bash
# =============================================================================
# exinfo_refresh_242.sh — [V12 R4e MAJOR-1] lam moi raw exchangeInfo cho UNIVERSE_A1 + R7 (CHAY TREN 242, cron root)
# deploy_v12_dry_r4.sh cai vao crontab root (marker "# C3LIVE_EXINFO_REFRESH"), phut 03,18,41,48 (ngoai cua so [27,40]);
# rollback_v12.sh go theo marker. Moi lan:
#   curl -> run/c3live_exchangeInfo.json.new -> python3 -I kiem: JSON hop le; co serverTime > 0 (KHONG doi moi hon — R4n);
#   > 100 symbol; MOI symbol co onboardDate + underlyingType; >= 50 hop dong TradFi; so symbol giam <= 10 %.
#   Hop le => .lastgood + mv -f (nguyen tu; JVM nap lai theo mtime ca A1 lan R7). Khong => GIU file cu, dem loi lien tiep;
#   lan loi thu 3 (roi moi 4 lan) => Telegram (tg.env cua watchdog 242; khong doc duoc => ALERT_PENDING trong run/).
# [R4f] kiem bang exinfo_validate.py (CUNG file voi buoc PRE/chuan bi cua deploy). Phan loai TF/INDEX KHONG o day (chi Java UniverseA1Classifier); day chi kiem nguon tho (cung nguong R4b).
# [R4k] python3 RIENG duong dan tuyet doi C3PY (mac dinh /opt/c3py/python/bin/python3, cai bang c3py_install_242.sh; cron dat C3PY):
#   242 CentOS 7 chi co python2.7 — KHONG dung python theo PATH / he thong. Thieu python => tinh la 1 lan loi (giu file cu, Telegram lan 3).
# [R4n MAJ-X A1 R4M] serverTime la anh chup cache cua san (cu toi 88', co luc lui vai ms) => tuoi file tinh theo LUC TAI:
#   sidecar run/c3live_exchangeInfo.json.meta {"fetchedAtMs","sha256","n_symbols"} ghi .tmp roi mv ngay sau file (R7 Java doc).
# Bien (test): APP_DIR, EXINFO_CMD, EXR_TG_ENV, EXR_TG_SINK, MIN_TRADFI, MAX_SYMBOL_DROP, C3PY.
# =============================================================================
set -uo pipefail
A=${APP_DIR:-$(cd "$(dirname "$0")/.." && pwd)}
VAL=${EXV_PY:-$(cd "$(dirname "$0")" && pwd)/exinfo_validate.py}   # [R4f MINOR-2] bo kiem CHUNG voi deploy
PY=${C3PY:-/opt/c3py/python/bin/python3}   # [R4k] trinh thong dich RIENG, duong dan tuyet doi (xem tren)
cd "$A" || { echo "FAIL cd $A"; exit 1; }
F=run/c3live_exchangeInfo.json
NEW=$F.new
STATE=run/c3live_exinfo_refresh.state
EXC=${EXINFO_CMD:-"curl -s --max-time 30 https://fapi.binance.com/fapi/v1/exchangeInfo"}
MINTF=${MIN_TRADFI:-50}
DROP=${MAX_SYMBOL_DROP:-0.10}
TG_ENV=${EXR_TG_ENV:-/root/.config/h242_watchdog/tg.env}
ts() { date '+%F %T%z'; }

exec 9> run/.exinfo_refresh.lock
flock -n 9 || { echo "$(ts) SKIP: dang co lan lam moi khac"; exit 0; }

tg() {
  local msg="$1" tok chat code
  if [ -n "${EXR_TG_SINK:-}" ]; then { printf '%s\n' "$msg"; echo "----"; } >> "$EXR_TG_SINK"; return 0; fi
  if [ ! -r "$TG_ENV" ]; then echo "$(ts) $msg" >> run/ALERT_PENDING_exinfo.txt; echo "$(ts) NO_CHANNEL $msg"; return 0; fi
  tok=$(sed -nE 's/^[[:space:]]*(export[[:space:]]+)?(TG_TOKEN=|tele-token:[[:space:]]*)//p' "$TG_ENV" | head -1 | tr -d '\r"')
  chat=$(sed -nE 's/^[[:space:]]*(export[[:space:]]+)?(TG_CHAT=|tele-chat-id:[[:space:]]*)//p' "$TG_ENV" | head -1 | tr -d '\r"')
  code=$(printf 'url = "https://api.telegram.org/bot%s/sendMessage"\n' "$tok" | curl -s -m 15 -o /dev/null -w '%{http_code}' -K - \
    --data-urlencode "chat_id=$chat" --data-urlencode "text=$msg" 2>/dev/null)
  tok=""
  [ "$code" = 200 ] || { echo "$(ts) $msg" >> run/ALERT_PENDING_exinfo.txt; echo "$(ts) Telegram loi HTTP ${code:-?}"; }
}

FAILS=$(sed -n 's/^fails=//p' "$STATE" 2>/dev/null | head -1)
case "$FAILS" in ''|*[!0-9]*) FAILS=0;; esac
LASTOK=$(grep '^last_ok=' "$STATE" 2>/dev/null | head -1)
rm -f "$NEW"
eval "$EXC" > "$NEW" 2>/dev/null
RC=$?
FAT=$(date +%s%3N)   # [R4n] luc tai (sidecar fetchedAtMs)
[ -f "$VAL" ] || { echo "$(ts) FAIL thieu bo kiem $VAL"; exit 1; }
MSG=$("$PY" -I "$VAL" "$NEW" "$F" "$MINTF" "$DROP" 2>&1)
VRC=$?
if [ "$RC" = 0 ] && [ "$VRC" = 0 ]; then
  NS=$(printf '%s' "$MSG" | sed -n 's/^symbols=\([0-9]*\) .*/\1/p' | head -1)
  SHA=$(sha256sum < "$NEW" | cut -c1-64)
  if [ -n "$NS" ] && printf '{"fetchedAtMs":%s,"sha256":"%s","n_symbols":%s}\n' "$FAT" "$SHA" "$NS" > "$F.meta.tmp" \
     && cp -f "$NEW" "$F.lastgood.tmp" && mv -f "$F.lastgood.tmp" "$F.lastgood" && mv -f "$NEW" "$F" && mv -f "$F.meta.tmp" "$F.meta"; then
    { echo "fails=0"; echo "last_ok=$(date +%s) $MSG"; } > "$STATE.tmp" && mv -f "$STATE.tmp" "$STATE"
    echo "$(ts) OK $MSG fetchedAtMs=$FAT"
    [ "$FAILS" -ge 3 ] && tg "[C3-LIVE 242] lam moi exchangeInfo DA HOI PHUC sau $FAILS lan loi ($MSG)"
    exit 0
  fi
  MSG="mv loi"
fi
rm -f "$NEW" "$F.lastgood.tmp" "$F.meta.tmp"
FAILS=$((FAILS + 1))
{ echo "fails=$FAILS"; echo "last_err=$(date +%s) curl_rc=$RC $MSG"; if [ -n "$LASTOK" ]; then echo "$LASTOK"; fi; } > "$STATE.tmp"
mv -f "$STATE.tmp" "$STATE"
echo "$(ts) FAIL lan $FAILS lien tiep (curl rc=$RC): $MSG — GIU file cu"
if [ "$FAILS" -ge 3 ] && [ $(( (FAILS - 3) % 4 )) = 0 ]; then
  tg "[C3-LIVE 242] KHAN: lam moi exchangeInfo LOI $FAILS lan lien tiep ($MSG) — giu file cu; qua 45' JVM: R7 STALE (khong mua), listing moi bi loai"
fi
exit 1
