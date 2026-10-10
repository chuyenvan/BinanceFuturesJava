#!/bin/bash
# HO3b: dung chuoi cong 3 (bug endianness file OI gio ghep, phat hien qua G-B4a DEV), sua, chay lai
cd /home/ubuntu/claude_master/1003/ho3b
kill 2952862 2>/dev/null
pkill -f 'python3 ho3b_gate3.py --mode' 2>/dev/null
sleep 3
L=/home/ubuntu/claude_master/1002/oracle_heavy.lock
if grep -q '^HO3b 2952862' $L 2>/dev/null; then rm -f $L; echo "lock HO3b cu da go"; fi
python3 - <<'EOF'
p = "ho3b_gate3.py"
s = open(p).read()
o = "    a.tofile(path)\n"
assert s.count(o) == 1
s = s.replace(o, "    a.astype(ODT).tofile(path)   # FIX: np.concatenate tra ve native-endian; file OI la big-endian\n")
open(p, "w").write(s)
print("patched")
EOF
python3 -m py_compile ho3b_gate3.py && echo compiled
mv g3r g3r_bug_endian 2>/dev/null
echo "$(date) RESTART sau fix endianness (G-B4a DEV FAIL 20,4% o ls_global/rk_oi_delta24h do file OI gio ghi little-endian)" >> g3chain.log
setsid nohup ./ho3b_g3chain.sh > /dev/null 2>&1 < /dev/null &
echo relaunched
