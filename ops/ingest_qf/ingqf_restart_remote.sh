#!/usr/bin/env bash
# ingqf_restart_remote.sh — CHAY TREN 242 (ssh bash -s -- <C>): stop/start collectData an toan, TACH khoi phien ssh.
# Than restart chay nen (setsid nohup) => ssh rot giua chung van chay xong; trap LUON go PAUSE watchdog.
# Chi bam stop/start o giay [08,20] (sau chot nen +4..6 s, truoc burst :27-:40); start khong bao gio trong :25-:42.
C=$1
B=/root/ingqf_restart_body_$$.sh; L=/root/ingqf_restart_$$.log
cat > $B <<'BODY'
C=$1
trap 'rm -f /var/lib/h242_watchdog/PAUSE' EXIT HUP INT TERM
cd "$C" || { echo "FAIL cd"; echo DONE; exit 0; }
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
if pgrep -f 'websocket.BinanceDataIngestor' >/dev/null; then echo "FAIL ingest_khong_dung"; echo DONE; exit 0; fi
echo "OK da_stop $(date +%T)"
s=$(sec); if [ "$s" -ge 25 ] && [ "$s" -le 42 ]; then sleep $((43 - s)); fi
bin/daemon.sh start > /dev/null 2>&1
echo "INFO start_luc=$(date +%T)"
sleep 20
N=$(pgrep -fc 'websocket.BinanceDataIngestor'); P=$(pgrep -f 'websocket.BinanceDataIngestor' | head -1)
[ "$N" = 1 ] && echo "OK started pid=$P" || echo "FAIL so_process_ingest_sau_start=$N"
echo DONE
BODY
setsid nohup bash $B "$C" > $L 2>&1 < /dev/null &
for i in $(seq 1 120); do grep -q '^DONE' $L 2>/dev/null && break; sleep 2; done
cat $L
grep -q '^DONE' $L || echo "FAIL restart_chua_xong_sau_240s (xem $L)"
sleep 1
[ -f /var/lib/h242_watchdog/PAUSE ] && echo "FAIL PAUSE_watchdog_con" || echo "OK PAUSE_da_go"
rm -f $B
