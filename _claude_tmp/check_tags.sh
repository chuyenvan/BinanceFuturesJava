#!/bin/bash
set -e
cd /home/ubuntu/src/BinanceFuturesJava
echo "---STATUS---"; git status --short | head -20
echo "---HEAD---"; git log -1 --oneline
echo "---GITLOG-TODAY---"; git log --since=today --oneline | head -30
echo "---TAGS---"
for t in cd-sel15 sc-par sc-b1 sc-b2 sc-b3 sc-b4 sh1-s1-sl05 sh1-s2-sl03k16 sh1-s3-ts8 sh1-s4-sl03 tp-par-kg0 tp-par-t170 tp-n1 tp-n2 tp-n3 tp-n4 xs-a1 xs-a2 xs-a3; do
  d=/home/ubuntu/kaggle_sim/out/$t
  if [ -f "$d/storage/printDone.csv" ]; then
    echo "$t OK lines=$(wc -l < "$d/storage/printDone.csv") md5=$(md5sum "$d/storage/printDone.csv" | cut -d' ' -f1)"
  else
    echo "$t MISSING"
  fi
done
echo "---FREE---"; free -g
echo "---DF---"; df -h / | tail -1
echo "---AUDIT-DIR---"; ls -la /home/ubuntu/claude_audit_0928/ 2>/dev/null || echo "no dir yet"
