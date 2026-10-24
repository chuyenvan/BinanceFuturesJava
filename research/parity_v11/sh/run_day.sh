#!/bin/bash
# PARITY_V11_WINDOW — luot D cho 1 ngay UTC (PREREG 481701b2 + ADDENDUM1 fea9fb97). Khong doc/ghi 242.
# Dieu kien: ~/claude_master/pull242/<D>/COMPLETE (va <D+1> neu co: log/buffer moi hon); Vision daily ngay D da phat hanh.
# Dung:  bash ~/claude_master/vz_e1_wt/research/parity_v11/sh/run_day.sh 2026-10-24 [buoc_bat_dau]
#        buoc: prep vision universe r0 harness eval s1v tsx labels kprime   (mac dinh prep = chay het)
# Ket qua: ~/claude_master/parity_v11w/d/<D>/work/*.json ; log: ~/claude_master/parity_v11w/d/<D>/run_day.log
# Exit: 0 = cham du; 3 = Vision ngay D < 99 % symbol live => chi cham phan khong can Vision (P3, S1-I/m, GV-I, P1-m, TSX co).
set -uo pipefail
unset PV_WORK            # WORK luon = d/<D>/work (PV_WORK chi dung cho regression D1)
D=$1
FROM=${2:-prep}
R=$HOME/claude_master/vz_e1_wt/research/parity_v11
W=$HOME/claude_master/parity_v11w
export PV_DAY=$D
TAG=${D//-/}
B=$W/d/$D
mkdir -p $B/work
exec > >(tee -a $B/run_day.log) 2>&1
STEPS="prep vision universe r0 harness eval s1v tsx labels kprime"
on=0
want() { [ $on -eq 1 ] && return 0; [ "$1" = "$FROM" ] && on=1 && return 0; return 1; }
step() { echo "=== $(date -u +%FT%TZ) $*"; }
run() { step "$@"; "$@" || { echo "FAIL rc=$? : $*"; exit 1; }; }
want prep && run python3 $R/py/day_prep.py prep
D15=$(python3 -c "import datetime as d;print(d.date.fromisoformat('$D')-d.timedelta(days=15))")
want vision && run python3 $R/py/vision_fetch.py $W/univ/ucand_$TAG.txt $D15 $D $W/vision/klines_1m --threads 16
if want universe; then
  step universe; python3 $R/py/day_prep.py universe; RC=$?
  if [ $RC -eq 3 ]; then
    step "Vision $D < 99 % symbol live => chi cham phan KHONG can Vision"
    run python3 $R/py/day_eval.py p3
    run python3 $R/py/day_eval.py s1
    run python3 $R/py/day_eval.py live_only
    run python3 $R/py/day_tsx.py
    exit 3
  elif [ $RC -ne 0 ]; then echo "FAIL universe rc=$RC"; exit 1; fi
fi
want r0 && run python3 $R/py/day_harness.py r0
want harness && run python3 $R/py/day_harness.py main
if want eval; then for s in gate fund net s1 gv p3; do run python3 $R/py/day_eval.py $s; done; fi
want s1v && run python3 $R/py/day_s1v.py
want tsx && run python3 $R/py/day_tsx.py
want labels && run python3 $R/py/day_labels.py
if want kprime; then
  run python3 $R/py/day_kprime.py plan
  run python3 $R/py/day_harness.py drop $B/work/kprime_groups.json
  run python3 $R/py/day_kprime.py eval
fi
# don file trung gian lon (giu JSON + csv nho): cache Vision, NEW2 tung doan, closes cache
rm -f $B/runs/cache_*.ser.gz $B/runs/new2_s*/cache_*.ser.gz $B/runs/new2_s*/out_NEW2.csv.gz $B/runs/new2_s*/fund_NEW2.csv.gz
du -sh $B
step DONE
