#!/bin/bash
SSH="/c/Program Files/Git/usr/bin/ssh.exe"
KEY=/c/Users/pc/.ssh/id_rsa_chuyennd
HOST=ubuntu@161.118.212.3
ENVS="CE_RUN_DIR=/home/ubuntu/claudedata/.run/mcp_ce CE_LOCKS_DIR=/home/ubuntu/claudedata/.run/mcp_ce/locks"
TOOL=/home/ubuntu/claudedata/.run/mcp_tools-v3.py
PID=ladder_1784297380
for i in $(seq 1 96); do
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
  if [ "$PS" = "WAITING_LLM" ] && [ "$CUR" = "decide_tr" ]; then echo "REACHED_DECIDE_TR"; break; fi
  if [ "$PS" = "DONE" ]; then echo "PIPE_DONE"; break; fi
  if [ "$PS" = "FAILED" ] || [ "$PS" = "ERROR" ]; then echo "PIPE_FAILED"; break; fi
  if [ "$PS" = "PARSE_ERR" ]; then echo "PARSE_PROBLEM: $CUR"; fi
  sleep 300
done
echo "POLL_LOOP_END"
