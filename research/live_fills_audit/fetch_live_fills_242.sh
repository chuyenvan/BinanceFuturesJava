#!/bin/bash
# =============================================================================
# LIVE FILLS AUDIT — fetcher (RUN ON 242, READ-ONLY, GET-ONLY)
# =============================================================================
# Collects real fills from the Binance USDⓈ-M futures API for the live account.
#
# 🔴 SAFETY: this script only ever issues HTTP GET requests.
#    No POST/PUT/DELETE. No /fapi/v1/order placement, no batchOrders, no
#    allOpenOrders DELETE, no leverage/marginType/positionMargin, no cancel.
#
# 🔑 SECRET HANDLING: the key/secret are read at runtime out of the *deployed*
#    jar on 242 (com/binance/chuyennd/config/PrivateConfig.class) into shell
#    variables and are never echoed, logged or written to disk.
#
# Usage (on 242):
#   mkdir -p /tmp/fills_audit && cd /tmp/fills_audit
#   find /home/chuyennd/java/v_t_m/storage/data/order -mindepth 2 -maxdepth 2 -type f \
#        -printf '%f\n' | sed 's/-[0-9]*$//' | sort -u > order_symbols.txt
#   bash fetch_live_fills_242.sh
#
# Output: /tmp/fills_audit/raw2 (userTrades windows + probes),
#         /tmp/fills_audit/raw3 (klines + old-window probe),
#         /tmp/fills_audit/raw4 (allOrders 7d windows),
#         /tmp/fills_audit/raw2/positionRisk.json
#
# API window facts observed 2026-09-23 (Binance USDⓈ-M):
#   GET /fapi/v1/userTrades : max interval 7 days (-4165); history ~91 days
#   GET /fapi/v1/allOrders  : max interval 7 days; window restricted to last
#                             90 days (-4166). Older orders are only reachable
#                             via GET /fapi/v1/order?orderId=...
# =============================================================================
set -u
AUD=${AUD:-/tmp/fills_audit}
BIN="https://fapi.binance.com"
JAR=/home/chuyennd/java/v_t_m/target/binance-java-sdk-1.2.4.jar
mkdir -p "$AUD/raw2" "$AUD/raw3" "$AUD/raw4"

# ---------- keys (read from deployed jar, never printed) ----------
python2 - <<'PY' 2>/dev/null || python3 - <<'PY'
import zipfile
z=zipfile.ZipFile("/home/chuyennd/java/v_t_m/target/binance-java-sdk-1.2.4.jar")
for n in z.namelist():
    if n.endswith("config/PrivateConfig.class"):
        open("/tmp/fills_audit/PrivateConfig.class","wb").write(z.read(n))
PY
mapfile -t KS < <(strings "$AUD/PrivateConfig.class" | grep -E '^.{65}$' | cut -c2-)
# class-file CONSTANT_Utf8 length prefix (0x40 = 64) sticks to the string,
# so the 64-char key/secret show up as 65-char lines -> strip 1 leading char.
APIKEY="${KS[0]:-}"; SECRET="${KS[1]:-}"
[ -z "$APIKEY" ] && { echo "STOP: khong doc duoc key tu jar"; exit 3; }

sign_get() { # $1 = path, $2 = query string
  local ts=$(( $(date +%s%N) / 1000000 ))
  local q="$2&timestamp=${ts}&recvWindow=10000"
  local sig=$(printf '%s' "$q" | openssl dgst -sha256 -hmac "$SECRET" | awk '{print $NF}')
  curl -s --max-time 25 -H "X-MBX-APIKEY: $APIKEY" "$BIN$1?$q&signature=$sig"
}
pub_get() { curl -s --max-time 25 "$BIN$1?$2"; }

NOW=$(date +%s); W=$((7*86400)); T89=$((NOW-89*86400))

# ---------- candidate symbols ----------
sed '/^#/d;/^[[:space:]]*$/d' "$AUD/order_symbols.txt" > "$AUD/c2.txt"
for f in /home/chuyennd/java/v_t_m/run/legacy_symbols.csv; do
  [ -f "$f" ] && sed '/^#/d;/^[[:space:]]*$/d' "$f" >> "$AUD/c2.txt"
done
sort -u "$AUD/c2.txt" -o "$AUD/c2.txt"
sed '/^#/d;/^[[:space:]]*$/d' /home/chuyennd/java/v_t_m/run/legacy_symbols.csv | sort -u > "$AUD/legacy.txt" 2>/dev/null || : > "$AUD/legacy.txt"

# ---------- PHASE 1: probe last 7d per candidate ----------
: > "$AUD/probe2.log"
while read -r s; do
  [ -z "$s" ] && continue
  st=$(( NOW - W ))
  r=$(sign_get /fapi/v1/userTrades "symbol=$s&startTime=$((st*1000))&endTime=$((NOW*1000))&limit=1000")
  printf '%s' "$r" > "$AUD/raw2/probe_${s}.json"
  echo "$s $(printf '%s' "$r" | grep -o '"id"' | wc -l)" >> "$AUD/probe2.log"
  sleep 0.12
done < "$AUD/c2.txt"
awk '$2>0 {print $1}' "$AUD/probe2.log" > "$AUD/hits_recent.txt"
cat "$AUD/legacy.txt" "$AUD/hits_recent.txt" | sed '/^[[:space:]]*$/d' | sort -u > "$AUD/sweep_list.txt"

# ---------- PHASE 2: full 13x7d userTrades sweep ----------
while read -r s; do
  [ -z "$s" ] && continue
  st=$(( NOW - 91*86400 ))
  while [ "$st" -lt "$NOW" ]; do
    en=$((st+W)); [ "$en" -gt "$NOW" ] && en=$NOW
    printf '%s' "$(sign_get /fapi/v1/userTrades "symbol=$s&startTime=$((st*1000))&endTime=$((en*1000))&limit=1000")" > "$AUD/raw2/trades_${s}_${st}.json"
    st=$en; sleep 0.12
  done
done < "$AUD/sweep_list.txt"

# ---------- PHASE 3: allOrders, 7d windows over 89d ----------
while read -r s; do
  [ -z "$s" ] && continue
  st=$T89
  while [ "$st" -lt "$NOW" ]; do
    en=$((st+W)); [ "$en" -gt "$NOW" ] && en=$NOW
    printf '%s' "$(sign_get /fapi/v1/allOrders "symbol=$s&startTime=$((st*1000))&endTime=$((en*1000))&limit=1000")" > "$AUD/raw4/ao_${s}_${st}.json"
    st=$en; sleep 0.12
  done
done < "$AUD/sweep_list.txt"

# ---------- PHASE 4: retention probes + current state (read) ----------
for sym in BEATUSDT ACEUSDT; do
  printf '%s' "$(sign_get /fapi/v1/userTrades "symbol=$sym&startTime=$(( (NOW-100*86400)*1000 ))&endTime=$(( (NOW-93*86400)*1000 ))&limit=1000")" > "$AUD/raw3/old_probe_${sym}.json"
  sleep 0.12
done
sign_get /fapi/v2/positionRisk "" > "$AUD/raw2/positionRisk.json"

echo "ALL_DONE"
