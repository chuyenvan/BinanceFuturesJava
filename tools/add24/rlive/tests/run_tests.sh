#!/bin/bash
# ADD24 R-LIVE: chay moi test bat buoc A1 (a)-(f). Ket qua -> ~/claude_master/w3/add24/a/tests_<ts>/
set -u
T=$(cd "$(dirname "$0")" && pwd); A=$HOME/claude_master/w3/add24/a/tests_$(date +%m%d_%H%M%S); mkdir -p $A /dev/shm/add24
TEST_OUT=$A/test_score.json python3 $T/test_score.py > $A/test_score.txt 2>&1; R1=$?
bash $T/test_parser_v4b.sh $A/test_parser_v4b.json > $A/test_parser_v4b.txt 2>&1; R2=$?
bash $T/test_guard_gate.sh $A/test_guard_gate.json > $A/test_guard_gate.txt 2>&1; R3=$?
echo "test_score(a,b,c,e)=$R1 test_parser_v4b(f)=$R2 test_guard_gate(d)=$R3 out=$A"; [ $R1$R2$R3 = 000 ]
