#!/usr/bin/env bash
# ingqf_check_remote.sh — CHAY TREN 242 (chi doc): kiem collectData sau deploy/rollback.
# args: C A EXPECT_MD5 PRE_TOTAL LEGACY_PID MODE(new|old)
C=$1; A=$2; EXP=$3; PRE_TOTAL=$4; LEG=$5; MODE=$6
cd "$C" || { echo "FAIL cd"; exit 0; }
N=$(pgrep -fc 'websocket.BinanceDataIngestor'); P=$(pgrep -f 'websocket.BinanceDataIngestor' | head -1)
[ "$N" = 1 ] && echo "OK 1_process pid=$P" || echo "FAIL so_process=$N"
FD=$(find /proc/$P/fd -lname '*binance-java-sdk*.jar*' 2>/dev/null | head -1)
JM=$(md5sum < "$FD" 2>/dev/null | cut -c1-32)
[ "$JM" = "$EXP" ] && echo "OK jar_md5=$JM ($(readlink $FD))" || echo "FAIL jar_md5=$JM (can $EXP)"
L=""; for f in logs/nohup.out logs/full.log; do grep -a -q "PID $P written" $f 2>/dev/null && { L=$f; break; }; done
if [ -z "$L" ]; then echo "FAIL khong_thay_dong_start_pid_$P"; X=""; else
  S0=$(grep -a -n "PID $P written" $L | tail -1 | cut -d: -f1); X=$(tail -n +$S0 $L); echo "OK log_tu_start pid=$P file=$L"; fi
if [ "$MODE" = new ]; then
  tr '\0' '\n' < /proc/$P/environ | grep -qx 'INGEST_SCHEDULED_RESTART_HOURS=0' && echo "OK env_restart_lich_TAT" || echo "FAIL env_INGEST_SCHEDULED_RESTART_HOURS"
  grep -q '\[REST-BUDGET\] bat' <<<"$X" && echo "OK budget_bat" || echo "FAIL budget_chua_bat"
  grep -q '\[KLINE-INGEST\] startup:' <<<"$X" && echo "OK startup: $(grep -a '\[KLINE-INGEST\] startup:' <<<"$X" | tail -1 | grep -o '[0-9]* o thieu.*' | cut -c1-90)" || echo "WARN chua_thay_dong_startup"
  B=$(grep -a '\[REST-BUDGET\] calls=' <<<"$X")
  NB=$(grep -c . <<<"$B")
  [ "$NB" -ge 2 ] && echo "OK budget_lines=$NB" || echo "FAIL budget_lines=$NB (<2)"
  PK=$(grep -o 'peak60s=[0-9]*' <<<"$B" | tr -dc '0-9\n' | sort -n | tail -1)
  [ -n "$PK" ] && [ "$PK" -le 300 ] && echo "OK weight_peak60s_max=$PK" || echo "FAIL weight_peak60s_max=$PK"
  H4=$(grep -o 'http4[12][89]=[1-9][0-9]*' <<<"$B" | head -1)
  [ -z "$H4" ] && echo "OK 0_http429_418" || echo "FAIL $H4"
  HM=$(grep -o 'hdr_max=[0-9]*' <<<"$B" | tr -dc '0-9\n' | sort -n | tail -1); echo "INFO hdr_max_IP=$HM"
  PG=$(grep -o 'price_gap_max_ms=[-0-9]*' <<<"$B" | tail -n +2 | sed 's/.*=//' | sort -n | tail -1)
  [ -n "$PG" ] && [ "$PG" -ge 0 ] && [ "$PG" -le 5000 ] && echo "OK price_gap_max_ms=$PG" || echo "FAIL price_gap_max_ms=$PG"
  grep -a -q 'REST banned\|REST cooldown\|"code":-1003' <<<"$X" && echo "FAIL co_ban_hoac_cooldown_tu_start" || echo "OK 0_ban"
fi
grep -a -q 'Too many symbol price errors\|Restart: Reset' <<<"$X" && echo "FAIL co_restart_JVM" || echo "OK 0_restart"
T=$(grep -a 'Ch.t n.n ph.t' <<<"$X" | tail -2 | grep -o 'Total: [0-9]*' | tr -dc '0-9\n' | sort -n | head -1)
[ -n "$T" ] && [ "$T" -ge "$PRE_TOTAL" ] && echo "OK kline_phut_moi_du_symbol Total=$T (truoc $PRE_TOTAL)" || echo "FAIL kline_Total=$T (truoc $PRE_TOTAL)"
TP=$(pgrep -f 'trading.BinanceOrderTradingManager' | head -1)
[ "$TP" = "$LEG" ] && echo "OK legacy_pid_khong_doi=$TP" || echo "FAIL legacy_pid=$TP (truoc $LEG)"
AG=$(( $(date +%s) - $(stat -c %Y $A/logs/full.log) ))
[ "$AG" -le 90 ] && echo "OK legacy_log_tuoi=${AG}s" || echo "FAIL legacy_log_dung=${AG}s"
if command -v aql >/dev/null; then
  R=$(timeout 10 aql -h 127.0.0.1 -p 3222 -o raw -c "SELECT ts FROM ticker.price_realtime WHERE PK='BTCUSDT'" 2>/dev/null | grep -o 'ts: [0-9]*' | tr -dc 0-9)
  if [ -n "$R" ]; then A2=$(( $(date +%s%3N) - R )); [ "$A2" -le 5000 ] && echo "OK price_realtime_BTC_tuoi_ms=$A2" || echo "FAIL price_realtime_BTC_tuoi_ms=$A2"; else echo "INFO aql_khong_doc_duoc_ts"; fi
fi
