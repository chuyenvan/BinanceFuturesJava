#!/bin/bash
# HO3b: chay 1 lenh nang duoi lock oracle_heavy (cho neu dang co lock), log ra $1, rm lock khi xong
LOG=$1; shift
L=/home/ubuntu/claude_master/1002/oracle_heavy.lock
while [ -e $L ]; do echo "$(date) cho lock: $(cat $L)" >> $LOG; sleep 60; done
echo "HO3b $$ $(date) $*" > $L
/usr/bin/time -v "$@" >> $LOG 2>&1
rc=$?
rm -f $L
echo "RC=$rc $(date)" >> $LOG
