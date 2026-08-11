#!/bin/bash
SSH="/c/Program Files/Git/usr/bin/ssh.exe"
KEY=/c/Users/pc/.ssh/id_rsa_chuyennd
HOST=ubuntu@161.118.212.3
ENVS="CE_RUN_DIR=/home/ubuntu/claudedata/.run/mcp_ce CE_LOCKS_DIR=/home/ubuntu/claudedata/.run/mcp_ce/locks"
TOOL=/home/ubuntu/claudedata/.run/mcp_tools-v3.py
PID=ladder_peak_1784326982
for i in $(seq 1 160); do
  OUT=$("$SSH" -o StrictHostKeyChecking=no -i "$KEY" "$HOST" "$ENVS python3 $TOOL pipe_status $PID" 2>/dev/null)
  ST=$(echo "$OUT" | python -c "import sys,json
try:
  d=json.load(sys.stdin)
  ps=d['pipe_status']; cs=d['progress']['current_step']; steps=d['steps']
  cur=steps[cs]['id'] if cs<len(steps) else 'END'
  print(ps+'|'+cur)
except Exception as e:
  print('PARSE_ERR|'+str(e))" 2>/dev/null)
  echo "iter=$i status=$ST"
  PS=${ST%%|*}; CUR=${ST#*|}
  if [ "$PS" = "WAITING_LLM" ] && [ "$CUR" = "decide_peak" ]; then echo "REACHED_DECIDE_PEAK"; break; fi
  if [ "$PS" = "DONE" ]; then echo "PIPE_DONE"; break; fi
  if [ "$PS" = "FAILED" ] || [ "$PS" = "ERROR" ] || [ "$PS" = "ABORTED" ]; then echo "PIPE_FAILED"; break; fi
  sleep 300
done
echo "POLL_PEAK_END"
