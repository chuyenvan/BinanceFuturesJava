#!/bin/bash
# CUA SO DUNG 242 (buoc 3b->6a lien mach, dung o loi dau tien): w1 stop -> w2 repair mapper -> w3 thay jar+buffer -> w4 start.
# Truoc do: d1_precheck.sh DAT, d3_stage_242.sh OK. Sau do (~5'): run242.sh w5_verify_242.sh.
source /home/ubuntu/claude_master/1011/livefix/deploy/dep_env.sh
for s in w1_stop_242 w2_repair_242 w3_swap_242 w4_start_242; do
  echo "######## $s $(date '+%F %T')"
  bash $DEP/run242.sh $DEP/$s.sh; rc=$?
  if [ $rc != 0 ]; then
    echo "######## DUNG tai $s rc=$rc"
    case $s in
      w1_stop_242) echo "App co the da dung mot phan: kiem 'systemctl is-active', start lai bang jar CU: $S242 'systemctl start h242-ingest; systemctl start h242-trading'";;
      w2_repair_242) echo "Mapper chua doi (neu khong co dong OK). Start lai jar CU: $S242 'systemctl start h242-ingest; systemctl start h242-trading' (jar cu chay duoc ca mapper cu lan da sua)";;
      *) echo "Rollback: bash $DEP/run242.sh $DEP/r_rollback_242.sh";;
    esac
    exit $rc
  fi
done
echo "######## CUA SO XONG $(date '+%F %T') — doi 5' roi: bash $DEP/run242.sh $DEP/w5_verify_242.sh"
