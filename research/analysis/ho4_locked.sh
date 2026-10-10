#!/bin/bash
# HO4: chay lenh nang (>4G) duoi lock oracle_heavy (cho neu co; tao; xoa khi xong). Usage: ho4_locked.sh <log> <cmd...>
L=/home/ubuntu/claude_master/1002/oracle_heavy.lock
LOG=$1; shift
while [ -e $L ]; do sleep 30; done
echo "ho4 $$ $(date +%FT%T) $*" > $L
/usr/bin/time -v "$@" > $LOG 2>&1
RC=$?
rm -f $L
echo "RC=$RC" >> $LOG
