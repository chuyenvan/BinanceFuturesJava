#!/usr/bin/env bash
# Driver: chay 4 diem quet BD threshold TUAN TU (1 slot JVM), detach bang setsid.
# Dung: bash sweep_driver.sh
set -uo pipefail
R=/home/ubuntu/src/BinanceFuturesJava
PROF=$R/profiles/x1_gs_t170.properties
LOG=/home/ubuntu/java/devrun/BD_THR_SWEEP_driver.log

log(){ echo "$(date '+%H:%M:%S') $*" | tee -a "$LOG"; }

# (TAG, value) theo thu tu TUAN TU
declare -a TAGS=(thr_m025 thr_m028 thr_m036 thr_m045)
declare -a VALS=(-0.025 -0.028 -0.036 -0.045)

log "=== START SWEEP (4 diem) ==="
for i in 0 1 2 3; do
  TAG=${TAGS[$i]}; VAL=${VALS[$i]}
  log "--- run $TAG (SIM_MS_DOWN_BIG_AVG=$VAL) ---"
  bash "$R/run_one.sh" "$TAG" "$PROF" "$VAL" >> "$LOG" 2>&1
  log "--- $TAG RC=$(tail -1 $LOG | grep -o 'RC=.*' ) done ---"
  md5=$(md5sum /home/ubuntu/java/devrun/$TAG/storage/printDone.csv 2>/dev/null | awk '{print $1}')
  nlines=$(wc -l < /home/ubuntu/java/devrun/$TAG/storage/printDone.csv 2>/dev/null)
  log "--- $TAG md5=$md5 lines=$nlines ---"
done
log "=== SWEEP ALL DONE ==="
