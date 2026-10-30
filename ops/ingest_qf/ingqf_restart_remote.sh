#!/usr/bin/env bash
# ingqf_restart_remote.sh — CHAY TREN 242 (qua ssh bash -s -- <C>): stop/start collectData an toan.
# Chi bam stop/start o giay [08,20] cua phut (sau chot nen +4..6 s, truoc burst :27-:40); PAUSE watchdog trong luc lam.
C=$1; cd "$C" || { echo "FAIL cd"; exit 0; }
sec() { echo $((10#$(date +%S))); }
for i in $(seq 1 130); do s=$(sec); [ "$s" -ge 8 ] && [ "$s" -le 20 ] && break; sleep 0.5; done
mkdir -p /var/lib/h242_watchdog && touch /var/lib/h242_watchdog/PAUSE
P=$(pgrep -f 'websocket.BinanceDataIngestor' | head -1)
echo "INFO stop_luc=$(date +%T) pid_cu=$P"
bin/daemon.sh stop > /dev/null 2>&1
for i in $(seq 1 30); do pgrep -f 'websocket.BinanceDataIngestor' >/dev/null || break; sleep 2; done
if pgrep -f 'websocket.BinanceDataIngestor' >/dev/null; then
  [ -n "$P" ] && kill "$P" 2>/dev/null
  for i in $(seq 1 15); do pgrep -f 'websocket.BinanceDataIngestor' >/dev/null || break; sleep 2; done
fi
pgrep -f 'websocket.BinanceDataIngestor' >/dev/null && { echo "FAIL ingest_khong_dung"; rm -f /var/lib/h242_watchdog/PAUSE; exit 0; }
echo "OK da_stop $(date +%T)"
s=$(sec); if [ "$s" -ge 25 ] && [ "$s" -le 42 ]; then sleep $((43 - s)); fi
bin/daemon.sh start > /dev/null 2>&1
echo "INFO start_luc=$(date +%T)"
sleep 20
N=$(pgrep -fc 'websocket.BinanceDataIngestor'); P=$(pgrep -f 'websocket.BinanceDataIngestor' | head -1)
rm -f /var/lib/h242_watchdog/PAUSE
[ "$N" = 1 ] && echo "OK started pid=$P" || echo "FAIL so_process_ingest_sau_start=$N"
