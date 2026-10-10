#!/bin/bash
# HO3b cong 3: chay rebuilt (cong that) roi pinned (doi chung) duoi CUNG 1 lock oracle_heavy
cd /home/ubuntu/claude_master/1003/ho3b
L=/home/ubuntu/claude_master/1002/oracle_heavy.lock
LOG=g3chain.log
while [ -e $L ]; do echo "$(date) cho lock: $(cat $L)" >> $LOG; sleep 60; done
echo "HO3b $$ $(date) gate3 chain" > $L
mkdir -p g3r g3p
/usr/bin/time -v python3 ho3b_gate3.py --mode rebuilt --out /home/ubuntu/claude_master/1003/ho3b/g3r >> g3r/run.log 2>&1
echo "RC_REBUILT=$? $(date)" >> $LOG
/usr/bin/time -v python3 ho3b_gate3.py --mode pinned --out /home/ubuntu/claude_master/1003/ho3b/g3p >> g3p/run.log 2>&1
echo "RC_PINNED=$? $(date)" >> $LOG
rm -f $L
echo "DONE $(date)" >> $LOG
