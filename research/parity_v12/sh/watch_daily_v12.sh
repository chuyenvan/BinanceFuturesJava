#!/bin/bash
# watch_daily_v12.sh — PARITY_V12_DRY: watcher cham hang ngay (1 tien trinh, flock). Moi 30':
#   (1) anh chup exchangeInfo dry (chi doc 242) neu ban cuoi > 50' (§2.2 PIT)
#   (2) ngay D chua cham, D >= START: can pull242/D + D+1 COMPLETE; anh chup so giay >= D+1 00:02 UTC (chup neu chua co);
#       chay run_day.sh D (qua oracle_heavy.lock) + day_report_v12 d<D> D; log 'DAY D verdict ...'
#   Vision chua co => run_day rc 3 (cham phan khong can Vision), thu lai toi 36h roi chot.
# Khong ghi 242, khong Binance REST. Dieu khien: sh/run_watch_v12.sh start|status|stop
set -u
export LIVE_IS_SHADOW_HOST=true
R=$HOME/claude_master/vz_e1_wt/research/parity_v12
W=$HOME/claude_master/parity_v12w
P=$HOME/claude_master/pull242
START=${START:-2026-11-04}
END=${END:-2026-12-15}
exec 9>$W/watch_v12.lock
flock -n 9 || { echo "watcher dang chay"; exit 1; }
log() { echo "$(date -u +%FT%TZ) $*" >> $W/watch_v12.log; }
log "START pid=$$ START=$START END=$END"
while true; do
  last=$(ls -t $W/exinfo/exinfo_*.json.gz 2>/dev/null | head -1)
  if [ -z "$last" ] || [ $(( $(date +%s) - $(stat -c %Y "$(ls -t $W/exinfo/index.log | head -1)") )) -gt 3000 ]; then
    bash $R/sh/exinfo_snap.sh >> $W/watch_v12.log 2>&1 || log "exinfo_snap LOI"
  fi
  D=$START
  while [[ "$D" < "$(date -u +%F)" && ! "$D" > "$END" ]]; do
    N=$(date -u -d "$D +1 day" +%F)
    if [ ! -f $W/d/$D/DONE ] && [ -f $P/$D/COMPLETE ] && [ -f $P/$N/COMPLETE ]; then
      need=$(( $(date -u -d "$N 00:02" +%s) * 1000 ))
      have=$(for f in $W/shadow_book/snap_*.txt; do head -1 $f; done 2>/dev/null | sort -n | tail -1)
      [ -n "$have" ] && [ "$have" -ge "$need" ] || bash $R/sh/book_snap.sh >> $W/watch_v12.log 2>&1
      flock -w 3600 $HOME/claude_master/locks/oracle_heavy.lock nice -n 10 bash $R/sh/run_day.sh $D > $W/run_$D.out 2>&1; rc=$?
      age=$(( $(date +%s) - $(date -u -d "$N" +%s) ))
      if [ $rc -eq 0 ] || [ $rc -eq 4 ] || [ $age -gt 129600 ]; then
        python3 $R/py/day_report_v12.py d${D//-/} $D > $W/report_$D.out 2>&1
        v=$(python3 -c "import json,sys;x=json.load(open('$HOME/claude_master/vz_e1_wt/docs/result/parity_v12_d${D//-/}/parity_v12_d${D//-/}.json'))['days']['$D'];print(x['ket_luan'],'|',x['ngay_sach'],'|',x['KPI_TBOOK'])" 2>&1)
        log "DAY $D rc=$rc verdict: $v"
        touch $W/d/$D/DONE
      else
        log "DAY $D rc=$rc (Vision chua du?) -> thu lai"
      fi
    fi
    D=$N
  done
  sleep 1800
done
