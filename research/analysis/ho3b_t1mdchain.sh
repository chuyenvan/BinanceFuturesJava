#!/bin/bash
# HO3b §4b-bis (mo ta): chay sau khi chuoi cong 3 xong, duoi lock oracle_heavy
cd /home/ubuntu/claude_master/1003/ho3b
until grep -q '^DONE' g3chain.log 2>/dev/null; do sleep 60; done
L=/home/ubuntu/claude_master/1002/oracle_heavy.lock
LOG=t1md.log
while [ -e $L ]; do echo "$(date) cho lock: $(cat $L)" >> $LOG; sleep 60; done
echo "HO3b $$ $(date) t1md" > $L
mkdir -p t1md
/usr/bin/time -v python3 ho3b_t1md.py kaggle/out/ho3b-mka-h1/market.bin /home/ubuntu/claude_master/1003/ho3b/t1md >> $LOG 2>&1
echo "RC=$? $(date)" >> $LOG
rm -f $L
echo "DONE $(date)" >> $LOG
