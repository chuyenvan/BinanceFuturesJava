#!/bin/bash
# Watcher mong tren CAC NUT CE co san (wfo_status, wfo_report): poll toi khi DONE+FAILED>=16
# (hoac PENDING=RUN=0) roi tu chay wfo_report <tag>, ghi marker. LLM chi doc marker/report.
# Dung: nohup bash wfo_watch_report.sh <tag> &   (chay detached tren Oracle)
set -u
TAG="${1:-ev2_oiz}"
export CE_RUN_DIR=/home/ubuntu/claudedata/.run/mcp_ce CE_LOCKS_DIR=/home/ubuntu/claudedata/.run/mcp_ce/locks
TOOL=/home/ubuntu/claudedata/.run/mcp_tools-v3.py
LOG=$CE_RUN_DIR/${TAG}_watch.log
MARK=$CE_RUN_DIR/${TAG}_watch.marker
rm -f "$MARK"
echo "=== watch start $(date +%F_%H:%M:%S) tag=$TAG ===" >> "$LOG"
for i in $(seq 1 90); do   # 90 * 120s = 3h tran
  D=$(python3 "$TOOL" wfo_status 2>/dev/null | python3 -c 'import sys,json;d=json.load(sys.stdin);c=d["counts"];print(c.get("DONE",0),c.get("FAILED",0),c.get("PENDING",0),c.get("RUNNING",0))')
  done=$(echo $D | cut -d" " -f1); fail=$(echo $D | cut -d" " -f2); pend=$(echo $D | cut -d" " -f3); run=$(echo $D | cut -d" " -f4)
  echo "$(date +%F_%H:%M:%S) DONE=$done FAILED=$fail PEND=$pend RUN=$run" >> "$LOG"
  fin=$((done+fail))
  if [ "$fin" -ge 16 ] || { [ "$pend" = "0" ] && [ "$run" = "0" ]; }; then
    python3 "$TOOL" wfo_report "$TAG" > "$CE_RUN_DIR/${TAG}_report_out.json" 2>/dev/null
    echo "REPORTED $(date +%F_%H:%M:%S) DONE=$done FAILED=$fail" >> "$LOG"
    echo "DONE=$done FAILED=$fail" > "$MARK"
    break
  fi
  sleep 120
done
echo "=== watch end $(date +%F_%H:%M:%S) ===" >> "$LOG"
