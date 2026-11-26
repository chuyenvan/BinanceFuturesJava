#!/bin/bash
# usage: bash code/heavy.sh <python args...>   (checks RAM >= 4000 MB and disk >= 12 GB (MASTER 2026-11-26), then flock + nice)
set -u
cd /home/ubuntu/claude_master/w3/levz_b3
avail_mb=$(free -m | awk '/^Mem:/{print $7}')
disk_kb=$(df -Pk /home/ubuntu | awk 'NR==2{print $4}')
if [ "$avail_mb" -lt 4000 ]; then echo "STOP: RAM available ${avail_mb} MB < 4000"; exit 3; fi
if [ "$disk_kb" -lt $((12*1024*1024)) ]; then echo "STOP: disk free ${disk_kb} kB < 12 GB"; exit 3; fi
mkdir -p /home/ubuntu/claude_master/locks
exec flock -w 3600 /home/ubuntu/claude_master/locks/oracle_heavy.lock nice -n 10 /usr/bin/python3 "$@"
