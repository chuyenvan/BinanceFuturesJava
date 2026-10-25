#!/bin/bash
# PARITY_V11_WINDOW — watcher cham hang ngay (thay watch_1024b lam tay). 1 tien trinh nohup, lock chong chay trung.
# Voi moi ngay UTC D tu START (mac dinh 2026-10-25) toi END (2026-11-17), tuan tu:
#   1) cho pull242/<D+1> OK (COMPLETE + check.txt STATUS=OK) [va pull242/<D> OK]; qua 48h => PULL_TIMEOUT, sang ngay ke
#   2) cho Vision daily D (data.binance.vision, file tinh): BTCUSDT co file roi chay run_day.sh; neu run_day rc=3
#      (Vision < 99 % symbol live) thu lai moi 30', toi da 36h => VISION_TIMEOUT (giu ket qua phan khong can Vision), sang ngay ke
#   3) run_day.sh D (rc=0) -> day_report.py daily_<YYYYMMDD> D -> 1 dong 'DAY D verdict=.. K5=.. P2max=.. rc=..' vao watch_daily.log
#   Ngay da cham (co WATCH_DONE hoac kpp_<tag>.json + gate_<tag>.json) => bo qua (SKIP).
# Khong crontab, khong cham 242, khong Binance REST. Dung:
#   nohup bash .../watch_daily.sh > ~/claude_master/parity_v11w/watch_daily.out 2>&1 &
#   bash .../watch_daily.sh --dry-run 2026-10-24      (chi in quyet dinh cho 1 ngay, khong chay gi)
set -u
unset PV_WORK PV_DAY
W=$HOME/claude_master/parity_v11w
R=$HOME/claude_master/vz_e1_wt/research/parity_v11
REPO=$HOME/claude_master/vz_e1_wt
PULL=$HOME/claude_master/pull242
LOG=$W/watch_daily.log
START=${WATCH_START:-2026-10-25}
END=${WATCH_END:-2026-11-17}
PULL_MAX_S=$((48*3600)); VIS_MAX_S=$((36*3600)); STEP_S=1800
nextday() { date -u -d "$1 +1 day" +%F; }
ts() { date -u +%FT%TZ; }
pull_ok() { [ -f "$PULL/$1/COMPLETE" ] && grep -q '^STATUS=OK' "$PULL/$1/check.txt" 2>/dev/null; }
vis_btc() { [ "$(curl -s -o /dev/null -w '%{http_code}' "https://data.binance.vision/data/futures/um/daily/klines/BTCUSDT/1m/BTCUSDT-1m-$1.zip")" = "200" ]; }
is_done() { local T=${1//-/}; [ -f "$W/d/$1/WATCH_DONE" ] || { [ -f "$W/d/$1/work/kpp_$T.json" ] && [ -f "$W/d/$1/work/gate_$T.json" ]; }; }
summ() {   # in verdict/K5/P2max tu JSON report
  python3 - "$REPO/docs/result/parity_v11_$2/parity_v11_$2.json" "$1" <<'EOF'
import json, sys
try:
    d = json.load(open(sys.argv[1]))["days"][sys.argv[2]]
    st, rq = d["status"], d.get("rq") or {}
    v = st["ket_luan"].split(" (")[0].replace(" ", "_")
    print("verdict=%s K5=%s P2max=%s/%s rq09=%s/%s" % (v, st.get("K5_official"), rq.get("max_live"), rq.get("max_off"),
                                                     rq.get("ge09_live"), rq.get("ge09_off")))
except Exception as e:  # noqa: BLE001
    print("verdict=? K5=? P2max=? (report loi: %s)" % e)
EOF
}

if [ "${1:-}" = "--dry-run" ]; then
  D=$2; N=$(nextday $D)
  echo "dry-run D=$D: done=$(is_done $D && echo yes || echo no) pull_D=$(pull_ok $D && echo OK || echo no) pull_D+1=$(pull_ok $N && echo OK || echo no) vision_BTC=$(vis_btc $D && echo 200 || echo no)"
  if is_done $D; then echo "=> SKIP (da cham; ket qua giu nguyen)"; else echo "=> se cho pull/Vision roi chay run_day.sh $D"; fi
  exit 0
fi

exec 9>"$W/watch_daily.lock"
flock -n 9 || { echo "$(ts) watcher khac dang chay (lock $W/watch_daily.lock)"; exit 1; }
echo "$(ts) START pid=$$ range=$START..$END" >> $LOG
D=$START
while [[ "$D" < "$(nextday $END)" ]]; do
  T=${D//-/}; N=$(nextday $D)
  if is_done $D; then echo "$(ts) DAY $D SKIP (da cham)" >> $LOG; D=$N; continue; fi
  t0=$(date +%s)
  while ! { pull_ok $D && pull_ok $N; }; do
    [ $(( $(date +%s) - t0 )) -gt $PULL_MAX_S ] && break
    sleep 600
  done
  if ! { pull_ok $D && pull_ok $N; }; then
    echo "$(ts) DAY $D PULL_TIMEOUT pull_D=$(pull_ok $D && echo OK || echo no) pull_D+1=$(pull_ok $N && echo OK || echo no)" >> $LOG
    D=$N; continue
  fi
  t1=$(date +%s); rc=3; first=1
  while true; do
    if vis_btc $D; then
      if [ $first = 1 ]; then bash $R/sh/run_day.sh $D > /dev/null 2>&1; rc=$?; first=0
      else bash $R/sh/run_day.sh $D vision > /dev/null 2>&1; rc=$?; fi
      [ $rc -ne 3 ] && break
    fi
    [ $(( $(date +%s) - t1 )) -gt $VIS_MAX_S ] && break
    sleep $STEP_S
  done
  if [ $rc -eq 3 ]; then
    (cd $W && python3 $R/py/day_report.py daily_$T $D > /dev/null 2>&1)
    echo "$(ts) DAY $D VISION_TIMEOUT $(summ $D daily_$T) rc=3" >> $LOG
  else
    (cd $W && python3 $R/py/day_report.py daily_$T $D > $W/d/$D/report_daily.txt 2>&1)
    echo "$(ts) DAY $D $(summ $D daily_$T) rc=$rc" >> $LOG
    [ $rc -eq 0 ] && date -u +%FT%TZ > $W/d/$D/WATCH_DONE
  fi
  D=$N
done
echo "$(ts) END (qua $END)" >> $LOG
