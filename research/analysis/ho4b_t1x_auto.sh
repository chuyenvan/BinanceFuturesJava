#!/bin/bash
# HO4-P0b: cho kernel ho4b-t1x xong -> fetch -> so sanh t1xcmp (duoi khoa RAM). Chay nen (setsid nohup).
cd /home/ubuntu/claude_master/1011/ho4b
for i in $(seq 1 120); do
  S=$(python3 ho4_exp_kernel.py status ho4b-t1x 2>&1 | tail -1)
  echo "$(date +%T) $S"
  case "$S" in
    *complete*) break ;;
    *error*|*cancel*) echo "KERNEL_FAIL"; exit 2 ;;
  esac
  sleep 60
done
python3 ho4_exp_kernel.py fetch ho4b-t1x . > fetch_t1x.log 2>&1
echo "FETCH_RC=$?"
ls kaggle/out/ho4b-t1x/out
./ho4_locked.sh t1xcmp.log python3 ho4b_t1xcmp.py kaggle/out/ho4b-t1x/out t1xcmp.json
echo "CMP_RC=$?"
echo AUTO_DONE
