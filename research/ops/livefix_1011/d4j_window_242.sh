#!/bin/bash
# MASTER 10-12 — CUA SO DUNG 242 (CHI JAR): w1j stop -> w2 repair mapper -> w3j thay jar -> w4 start. Dung o loi dau tien.
# Sua 10-12 20:05: dung w1j_stop_242.sh (w1 cu ABORT vi kiem buffer staged ma ban chi-jar khong stage buffer).
source /home/ubuntu/claude_master/1011/livefix/deploy/dep_env.sh
for s in w1j_stop_242 w2_repair_242 w3j_swap_242 w4_start_242; do
  echo "######## $s $(date '+%F %T')"
  bash $DEP/run242.sh $DEP/$s.sh; rc=$?
  if [ $rc != 0 ]; then
    echo "######## DUNG tai $s rc=$rc"
    case $s in
      w1j_stop_242|w2_repair_242) echo "Start lai jar CU: $S242 'systemctl start h242-ingest; systemctl start h242-trading'";;
      *) echo "Rollback: bash $DEP/run242.sh $DEP/r_rollback_242.sh";;
    esac
    exit $rc
  fi
done
echo "######## CUA SO XONG $(date '+%F %T') — doi 5' roi: bash $DEP/run242.sh $DEP/w5_verify_242.sh"
