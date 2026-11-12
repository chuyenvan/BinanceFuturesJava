#!/bin/bash
# R1 (chi doc): dem trong log 242 da pull: dong [GATE] co n_pass>0, dong "Level: ... BIG_DOWN", dong C3 onLeg/entry.
cd /home/ubuntu/claude_master/pull242 || exit 1
for d in 2026-11-0[3-9]; do
  [ -d "$d/logs" ] || continue
  f=$(ls $d/logs/full.log* 2>/dev/null | head -1); [ -n "$f" ] || continue
  zcat -f "$f" > /tmp/r1_dry_$$.log 2>/dev/null
  g=$(grep -c "\[GATE\]" /tmp/r1_dry_$$.log)
  p=$(grep "\[GATE\]" /tmp/r1_dry_$$.log | grep -oE "n_pass=[0-9]+" | grep -vc "n_pass=0$")
  b=$(grep -cE "Level: .* BIG_DOWN" /tmp/r1_dry_$$.log)
  bl=$(grep -E "Level: .* BIG_DOWN" /tmp/r1_dry_$$.log | head -2 | cut -c1-160)
  a=$(grep -c "AI PASS" /tmp/r1_dry_$$.log)
  echo "$d GATE_lines=$g n_pass>0=$p BIG_DOWN_level=$b AI_PASS=$a"
  [ -n "$bl" ] && echo "   $bl"
done
rm -f /tmp/r1_dry_$$.log
