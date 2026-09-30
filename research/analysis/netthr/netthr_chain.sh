#!/bin/bash
# chain: cho M_015 -> tai -> push M_010 -> cho -> tai -> push M_020 -> cho -> tai. 1 job/luc.
source ~/envs/xgb-env/bin/activate
cd ~/claude_master/0930_netthr
LOG=chain.log
say() { echo "$(date '+%F %T') $*" >> $LOG; }
wait_done() {  # $1 slug
  local n=0
  while true; do
    st=$(kaggle kernels status chuyendinh/$1 2>&1 | tail -1)
    say "$1 :: $st"
    case "$st" in
      *COMPLETE*) return 0;;
      *ERROR*|*CANCEL*) return 1;;
    esac
    n=$((n+1)); [ $n -gt 600 ] && return 2
    sleep 90
  done
}
fetch() {  # $1 slug $2 arm
  mkdir -p out_$2
  kaggle kernels output chuyendinh/$1 -p out_$2 >> $LOG 2>&1
  find out_$2 -name 'predict_wf_*.bin' | wc -l >> $LOG
  # flatten
  find out_$2 -name 'predict_wf_*.bin' -exec mv {} out_$2/ \; 2>/dev/null
  find out_$2 -name 'net_train_summary.json' -exec mv {} out_$2/ \; 2>/dev/null
  say "$2 fetched: $(ls out_$2/predict_wf_*.bin | wc -l) bins"
}
for pair in "netthr-m015-gpu:M_015:" "netthr-m010-gpu:M_010:k_M_010" "netthr-m020-gpu:M_020:k_M_020"; do
  slug=${pair%%:*}; rest=${pair#*:}; arm=${rest%%:*}; kd=${rest#*:}
  if [ -n "$kd" ]; then
    (cd $kd && kaggle kernels push -p . >> ../$LOG 2>&1); say "pushed $slug"
  fi
  wait_done $slug || { say "FAIL $slug"; kaggle kernels output chuyendinh/$slug -p fail_$arm >> $LOG 2>&1; exit 1; }
  fetch $slug $arm
done
say "ALL_FETCHED"
