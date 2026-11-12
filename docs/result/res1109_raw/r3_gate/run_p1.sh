#!/bin/bash
# R3 P1: cho lock oracle_heavy (khong long), kiem RAM/dia SAU khi co lock
cd /home/ubuntu/claude_master/res1109/r3_gate
export LIVE_IS_SHADOW_HOST=true
exec flock -w 14400 /home/ubuntu/claude_master/locks/oracle_heavy.lock bash -c '
avail=$(awk "/MemAvailable/{print int(\$2/1024)}" /proc/meminfo); disk=$(df -BG --output=avail / | tail -1 | tr -dc 0-9)
echo "lock ok $(date -u +%FT%TZ) MemAvailable=${avail}MB disk=${disk}G"
if [ "$avail" -lt 4000 ] || [ "$disk" -lt 15 ]; then echo "ABORT tai nguyen"; exit 3; fi
nice -n 10 /usr/bin/time -f "rss_kb=%M sec=%e" python3 /home/ubuntu/claude_master/vz_e1_wt/research/r3_gate/p1_screen.py
'
