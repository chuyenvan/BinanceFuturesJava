#!/bin/bash
# R3 Pha 1 sequencer (1 slot): day G3 seed 42,7,21,99 lan luot (r3_push.py tu kiem slot), roi MTM 4 seed + g0. DUNG o day (futility do MASTER/agent cham).
cd /home/ubuntu/claude_master/res1109/r3_gate/orch
log(){ echo "$(date -u +%FT%TZ) $*"; }
for s in 42 7 21 99; do
  while true; do
    python3 r3_push.py g3 $s >> push_seq.out 2>&1; rc=$?
    if [ $rc -eq 0 ]; then log "pushed g3 $s"; break; fi
    if [ $rc -eq 3 ]; then log "g3 $s da co, bo qua"; break; fi
    if [ $rc -ne 2 ]; then log "LOI rc=$rc o g3 $s => dung"; exit 1; fi
    sleep 300
  done
  sleep 120
done
T="r3g3-a1 r3g3-s7 r3g3-s21 r3g3-s99"
while true; do
  done_n=0
  for t in $T; do python3 -c "import sys;sys.path.insert(0,'.');import r3_orch as O;sys.exit(0 if O.KS._status(O.KS.kernel_ref('$t'))=='COMPLETE' else 1)" 2>/dev/null && done_n=$((done_n+1)); done
  log "complete $done_n/4"; [ $done_n -eq 4 ] && break
  for t in $T; do python3 -c "import sys;sys.path.insert(0,'.');import r3_orch as O;s=O.KS._status(O.KS.kernel_ref('$t'));sys.exit(3 if s in ('ERROR','CANCEL_ACKNOWLEDGED','CANCELLED') else 0)" 2>/dev/null; [ $? -eq 3 ] && { log "kernel $t LOI => dung"; exit 1; }; done
  sleep 600
done
while true; do python3 r3_mtm.py r3-mtm-b1 r3g0-a1 $T >> push_seq.out 2>&1; rc=$?; [ $rc -eq 0 ] && { log "pushed MTM"; break; }; [ $rc -ne 2 ] && { log "MTM loi rc=$rc"; exit 1; }; sleep 300; done
log "XONG pha 4 seed + MTM"
