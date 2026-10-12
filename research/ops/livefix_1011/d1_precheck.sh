#!/bin/bash
# BUOC 1 [Oracle, CHI DOC] dieu kien truoc deploy. Exit 0 = DAT moi dieu kien; khac 0 = DUNG.
source /home/ubuntu/claude_master/1011/livefix/deploy/dep_env.sh
F=0; fail(){ echo "FAIL: $*"; F=1; }
BL=/home/ubuntu/claude_master/1010/kfixm_bf_drv.log; BD=/home/ubuntu/claude_master/1010/kfixm_bf
# 1a backfill xong + verify dry-run 0 o doi
grep -q 'BF DRV DONE' $BL || fail "backfill chua xong (thieu 'BF DRV DONE' trong $BL)"
[ "$(ps -eo args | grep -c '[k]fixm_bf_drv.sh')" = 0 ] || fail "kfixm_bf_drv.sh van dang chay"
python3 - "$BD/verify_dry.json" <<'EOF' || F=1
import json, sys
try:
    t = json.load(open(sys.argv[1]))["total"]
except Exception as e:
    print("FAIL: khong doc duoc verify_dry.json:", e); sys.exit(1)
print("verify_dry total:", {k: t.get(k) for k in ("minutes", "cells", "diff", "ulp_only", "minutes_changed")})
if t.get("diff", 1) != 0:
    print("FAIL: verify dry-run con diff=%s o doi (yeu cau 0)" % t.get("diff")); sys.exit(1)
print("OK verify dry-run diff=0")
EOF
# 1b cua so cam 12:50-13:20, 00:50-01:20 (+07)
HM=$(TZ=Asia/Ho_Chi_Minh date +%H%M); case $HM in 125?|13[01]?|1320|005?|01[01]?|0120) fail "dang trong cua so cam ($HM)";; esac
# 1c jar
[ "$(sha256sum < $JAR | cut -c1-64)" = "$JAR_SHA" ] || fail "jar sai sha"
# 1d mapper 242 (CHI DOC): ky vong rc=3 idTrung=8 (hoac rc=0 neu da sua)
cd $WT && java -Xmx512m -cp $JAR $TOOL check > $LOGD/d1_mapper_check.log 2>&1; RC=$?
grep -a 'MAPPER-CHECK' $LOGD/d1_mapper_check.log | cut -c1-400
case $RC in 3) echo "mapper: con 8 id trung (dung ky vong truoc repair)";; 0) echo "mapper: DA sach id trung (repair da chay?)";; *) fail "tool check rc=$RC";; esac
java -Xmx512m -cp $JAR $TOOL plan > $LOGD/d1_mapper_plan.log 2>&1; grep -a 'MAPPER-PLAN' $LOGD/d1_mapper_plan.log | cut -c1-600
# 1e buffer gate moi da dung (buoc 2)
for b in live_new s1_new s2_new; do [ -s $G/$b.bin ] && [ -s $G/$b.json ] || fail "thieu $G/$b.bin/.json (chay d2_build_buffer.sh)"; done
# 1f JVM khac tren Oracle co the ghi mapper 242 (khong phai shadow) — phai = 0 ngoai 2 shadow
echo "Oracle java (main class):"; ps -eo pid,args | grep '[j]ava' | grep -o 'com\.binance\.[A-Za-z0-9_.]*' | sort | uniq -c
# 1g trang thai 242
bash $DEP/run242.sh $DEP/w0_state_242.sh || fail "khong doc duoc 242"
df -h / | tail -1
[ $F = 0 ] && echo "== PRECHECK DAT" || echo "== PRECHECK KHONG DAT"
exit $F
