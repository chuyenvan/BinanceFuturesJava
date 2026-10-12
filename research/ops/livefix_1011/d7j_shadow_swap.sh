#!/bin/bash
# MASTER 10-12 — BUOC 7 CHI JAR [Oracle, GHI shadow local; CHI DOC 242]. CHI chay SAU 242 W5 PASS.
# shadow-c3 (#1): thay jar + sua buffer bang kfixm_grrfix.py (bo chunk CRC hong do dia day 10-12). shadow-c3b (#2): thay jar, GIU buffer.
# Usage: d7j_shadow_swap.sh [c3|c3b|all]. Rollback: r_rollback_shadow.sh <c3|c3b> (jar + buffer tu .bak_livefix_<TS>).
source /home/ubuntu/claude_master/1011/livefix/deploy/dep_env.sh
WHO=${1:-all}; FIX=/home/ubuntu/claude_master/1010/kfixm_grrfix.py
cd $WT && java -Xmx512m -cp $JAR $TOOL check > $LOGD/d7j_mapper_check.log 2>&1; RC=$?
[ $RC = 0 ] || { echo "ABORT mapper 242 con id trung (rc=$RC) — jar moi se fail-fast; chay d4j truoc"; exit 2; }
NN=$(grep -a 'MAPPER-CHECK' $LOGD/d7j_mapper_check.log | tail -1 | sed -n 's/.* n=\([0-9]*\) maxId=\([0-9]*\).*/\1/p'); MX=$(grep -a 'MAPPER-CHECK' $LOGD/d7j_mapper_check.log | tail -1 | sed -n 's/.* n=\([0-9]*\) maxId=\([0-9]*\).*/\2/p')
[ -n "$NN" ] && [ -n "$MX" ] || { echo "ABORT khong doc duoc n/maxId mapper"; exit 2; }; EXP="Total: $NN, Next ID: $((MX+1))"; echo "ky vong mapper: $EXP"
swap1(){  # $1 unit  $2 dir  $3 fixbuf(1/0)
  local U=$1 A=$2 FB=$3 TS=$(date +%Y%m%d_%H%M) J=$2/target/binance-java-sdk-1.2.4.jar BF=$2/run/gate_ratio_live.bin
  echo "== $U $(date '+%F %T') TS=$TS fixbuf=$FB"; echo $TS > $A/run/livefix_1011.ts
  sudo systemctl stop $U; for i in $(seq 1 30); do [ "$(systemctl is-active $U)" != active ] && break; sleep 2; done
  [ "$(systemctl is-active $U)" != active ] || { echo "ABORT $U chua dung"; return 3; }
  cp -p $J $J.bak_livefix_$TS && cp -p $BF $BF.bak_livefix_$TS || { echo "ABORT backup $U"; return 4; }
  cp -p $JAR $J
  [ "$(sha256sum < $J | cut -c1-64)" = "$JAR_SHA" ] || { echo "ABORT jar sai sha $U"; return 4; }
  if [ $FB = 1 ]; then
    python3 $FIX $BF.bak_livefix_$TS $BF.grrfix_tmp || { echo "ABORT grrfix"; return 4; }
    [ -s $BF.grrfix_tmp ] || { echo "ABORT grrfix rong"; return 4; }
    mv $BF.grrfix_tmp $BF; echo "buffer: $(stat -c %s $BF.bak_livefix_$TS) -> $(stat -c %s $BF) byte"
  fi
  local LN=$(wc -l < $A/logs/full.log); echo $LN > $A/run/livefix_1011.loglines
  sudo systemctl start $U; sleep 150
  local L=$(tail -n +$((LN+1)) $A/logs/full.log)
  echo "$L" | grep -a 'SimpleSymbolMapper initialized' | tail -1 | cut -c1-140
  echo "$L" | grep -a 'NO-WRITE-242\]' | head -1 | cut -c1-140
  echo "$L" | grep -a 'TICKER-CACHE\] full reload\|GATE-RATIO\] LIVE nạp buffer\|GATE-RATIO\] seed\|GATE-RATIO.*CRC' | tail -3 | cut -c1-200
  local f=0
  echo "$L" | grep -a 'SimpleSymbolMapper initialized' | grep -q "$EXP" || { echo "FAIL $U mapper init"; f=1; }
  echo "$L" | grep -aq 'MAPPER-DUP\]\|ID-CAP\]' && { echo "FAIL $U MAPPER-DUP/ID-CAP"; f=1; }
  echo "$L" | grep -a 'GATE-RATIO\] LIVE nạp buffer' | tail -1 | grep -q 'warm-up=armed' || { echo "FAIL $U gate chua armed"; f=1; }
  [ "$(systemctl is-active $U)" = active ] || { echo "FAIL $U khong active"; f=1; }
  [ $f = 0 ] && echo "== $U PASS" || echo "== $U FAIL — r_rollback_shadow.sh"
  return $f
}
R=0
case $WHO in c3|all) swap1 shadow-c3 /home/ubuntu/shadow_c3/app 1 || R=1;; esac
[ $R = 0 ] || { echo "dung truoc shadow #2"; exit 1; }
case $WHO in c3b|all) swap1 shadow-c3b /home/ubuntu/shadow_c3b/app 0 || R=1;; esac
exit $R
