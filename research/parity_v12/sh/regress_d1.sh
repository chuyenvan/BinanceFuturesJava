#!/bin/bash
# Regression: cham lai D1 (2026-10-21) bang code tham so hoa, bo cuc du lieu cu, ghi vao regr_d1/work
R=$HOME/claude_master/vz_e1_wt/research/parity_v11
export PV_DAY=2026-10-21 PV_WORK=$HOME/claude_master/parity_v11w/regr_d1/work
mkdir -p $PV_WORK
cd $PV_WORK
for s in gate fund net s1 gv p3; do echo "=== $s $(date -u +%T)"; python3 $R/py/day_eval.py $s > log_$s.txt 2>&1 || { echo FAIL $s; tail -5 log_$s.txt; }; done
echo "=== s1v $(date -u +%T)"; python3 $R/py/day_s1v.py > log_s1v.txt 2>&1 || { echo FAIL s1v; tail -5 log_s1v.txt; }
echo "=== labels $(date -u +%T)"; python3 $R/py/day_labels.py > log_labels.txt 2>&1 || { echo FAIL labels; tail -5 log_labels.txt; }
echo "=== tsx $(date -u +%T)"; python3 $R/py/day_tsx.py --regress-d1 > log_tsx.txt 2>&1 || { echo FAIL tsx; tail -5 log_tsx.txt; }
echo "=== done $(date -u +%T)"
