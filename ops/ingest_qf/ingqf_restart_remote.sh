#!/usr/bin/env bash
# ingqf_restart_remote.sh — CHAY TREN 242 (ssh bash -s -- <C> <TOKEN>): stop/start collectData an toan, TACH khoi phien ssh.
# [QF3, A1_QF2 MAJ-B] PAUSE watchdog mang TOKEN cua chinh lan chay nay; PAUSE da co (nguoi khac) => DUNG, KHONG dung toi;
# trap chi go PAUSE neu noi dung dung TOKEN. Than restart chay nen (setsid nohup) => ssh rot giua chung van chay xong.
# Chi bam stop/start o giay [08,20]; start khong bao gio trong :25-:42.
# Bien moi truong chi de TEST (prod de mac dinh): INGQF_PAUSE_FILE, INGQF_TMPD, INGQF_PROC_PAT, INGQF_SEC_FROM/TO, INGQF_POST_START_SLEEP.
C=$1; TOKEN=$2
[ -n "$TOKEN" ] || { echo "FAIL thieu_TOKEN"; exit 0; }
PF=${INGQF_PAUSE_FILE:-/var/lib/h242_watchdog/PAUSE}
TMPD=${INGQF_TMPD:-/root}
B=$TMPD/ingqf_restart_body_$$.sh; L=$TMPD/ingqf_restart_$$.log
cat > $B <<'BODY'
C=$1; TOKEN=$2; PF=$3
PAT=${INGQF_PROC_PAT:-websocket.BinanceDataIngestor}
SF=${INGQF_SEC_FROM:-8}; ST=${INGQF_SEC_TO:-20}; PS=${INGQF_POST_START_SLEEP:-20}
own_rm() { [ "$(cat "$PF" 2>/dev/null)" = "$TOKEN" ] && rm -f "$PF"; }
cd "$C" || { echo "FAIL cd"; echo DONE; exit 0; }
mkdir -p "$(dirname "$PF")"
# tao PAUSE NGUYEN TU (noclobber): da co => cua nguoi khac => dung, khong dung toi
if ! ( set -C; echo "$TOKEN" > "$PF" ) 2>/dev/null; then
  echo "FAIL PAUSE_cua_nguoi_khac_dang_co: $(head -c 120 "$PF" 2>/dev/null) — KHONG restart, KHONG go"
  echo DONE; exit 0
fi
trap own_rm EXIT HUP INT TERM
sec() { echo $((10#$(date +%S))); }
for i in $(seq 1 130); do s=$(sec); [ "$s" -ge "$SF" ] && [ "$s" -le "$ST" ] && break; sleep 0.5; done
P=$(pgrep -f "$PAT" | head -1)
echo "INFO stop_luc=$(date +%T) pid_cu=$P"
bin/daemon.sh stop > /dev/null 2>&1
for i in $(seq 1 30); do pgrep -f "$PAT" >/dev/null || break; sleep 2; done
if pgrep -f "$PAT" >/dev/null; then
  [ -n "$P" ] && kill "$P" 2>/dev/null
  for i in $(seq 1 15); do pgrep -f "$PAT" >/dev/null || break; sleep 2; done
fi
if pgrep -f "$PAT" >/dev/null; then echo "FAIL ingest_khong_dung"; echo DONE; exit 0; fi
echo "OK da_stop $(date +%T)"
s=$(sec); if [ "$s" -ge 25 ] && [ "$s" -le 42 ] && [ "$SF" -ge 8 ]; then sleep $((43 - s)); fi
bin/daemon.sh start > /dev/null 2>&1
echo "INFO start_luc=$(date +%T)"
sleep "$PS"
N=$(pgrep -fc "$PAT"); P=$(pgrep -f "$PAT" | head -1)
[ "$N" = 1 ] && echo "OK started pid=$P" || echo "FAIL so_process_ingest_sau_start=$N"
echo DONE
BODY
setsid nohup bash $B "$C" "$TOKEN" "$PF" > $L 2>&1 < /dev/null &
for i in $(seq 1 120); do grep -q '^DONE' $L 2>/dev/null && break; sleep 2; done
cat $L
grep -q '^DONE' $L || echo "FAIL restart_chua_xong_sau_240s (xem $L)"
sleep 1
if [ "$(cat "$PF" 2>/dev/null)" = "$TOKEN" ]; then echo "FAIL PAUSE_cua_minh_con"; elif [ -f "$PF" ]; then echo "WARN PAUSE_nguoi_khac: $(head -c 120 "$PF")"; else echo "OK PAUSE_da_go"; fi
rm -f $B
