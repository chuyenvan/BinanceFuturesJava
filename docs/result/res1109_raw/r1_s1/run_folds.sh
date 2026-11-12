#!/bin/bash
# R1 A3 buoc (a): dung lai 16 fold S1 (x1_s1_save_all_folds.py) + cong G-S1R. Qua oracle_heavy.lock, nice 10.
O=$HOME/claude_master/res1109/r1_s1
LOG=$O/folds.log
echo "start $(date)" > $LOG
AV=$(free -m | awk '/Mem:/{print $7}'); DF=$(df -BG --output=avail ~ | tail -1 | tr -dc 0-9)
echo "avail_mb=$AV df_g=$DF" >> $LOG
if [ "$AV" -lt 4000 ] || [ "$DF" -lt 15 ]; then echo "SKIP_RESOURCES" >> $LOG; exit 3; fi
mkdir -p $HOME/claude_master/locks
flock -w 3600 $HOME/claude_master/locks/oracle_heavy.lock nice -n 10 \
  python3 $HOME/claude_master/res1109/r1_s1/s1_allfold_keep9.py >> $LOG 2>&1
echo "RC=$? $(date)" >> $LOG
