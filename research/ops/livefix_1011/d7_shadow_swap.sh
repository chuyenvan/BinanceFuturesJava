#!/bin/bash
# BUOC 7 [Oracle, GHI shadow local; CHI DOC 242] thay jar + buffer cho shadow #1 (shadow-c3, K16, s1_new) va #2 (shadow-c3b, K24, s2_new).
# CHI chay SAU khi 242 W5 PASS (mapper da sua: shadow doc mapper TRUC TIEP tu 242 — getClient242, AEROSPIKE_HOST=242;
# Oracle KHONG co ban sao mapper cho shadow — Aerospike local ns ticker khong co record symbol_mapper).
# Usage: d7_shadow_swap.sh [c3|c3b|all]   (mac dinh all, tuan tu). Rollback: r_rollback_shadow.sh <c3|c3b>.
source /home/ubuntu/claude_master/1011/livefix/deploy/dep_env.sh
WHO=${1:-all}
cd $WT && java -Xmx512m -cp $JAR $TOOL check > $LOGD/d7_mapper_check.log 2>&1; RC=$?
[ $RC = 0 ] || { echo "ABORT mapper 242 con id trung (rc=$RC) — jar moi se fail-fast; chay buoc 4 truoc"; exit 2; }
swap1(){  # $1 unit  $2 dir  $3 buffer moi
  local U=$1 A=$2 NB=$3 TS=$(date +%Y%m%d_%H%M) J=$2/target/binance-java-sdk-1.2.4.jar BF=$2/run/gate_ratio_live.bin
  echo "== $U $(date '+%F %T') TS=$TS"; echo $TS > $A/run/livefix_1011.ts
  sudo systemctl stop $U; for i in $(seq 1 30); do [ "$(systemctl is-active $U)" != active ] && break; sleep 2; done
  [ "$(systemctl is-active $U)" != active ] || { echo "ABORT $U chua dung"; return 3; }
  cp -p $J $J.bak_livefix_$TS && cp -p $BF $BF.bak_livefix_$TS
  cp -p $JAR $J && cp -p $NB $BF
  [ "$(sha256sum < $J | cut -c1-64)" = "$JAR_SHA" ] && cmp -s $BF $NB || { echo "ABORT chep sai $U"; return 4; }
  local LN=$(wc -l < $A/logs/full.log); echo $LN > $A/run/livefix_1011.loglines
  sudo systemctl start $U; sleep 150
  local L=$(tail -n +$((LN+1)) $A/logs/full.log)
  echo "$L" | grep -a 'SimpleSymbolMapper initialized' | tail -1 | cut -c1-140
  echo "$L" | grep -a 'NO-WRITE-242\]' | head -1 | cut -c1-140
  echo "$L" | grep -a 'TICKER-CACHE\] full reload\|GATE-RATIO\] LIVE nạp buffer' | tail -2 | cut -c1-180
  local f=0
  echo "$L" | grep -a 'SimpleSymbolMapper initialized' | grep -q 'Total: 933, Next ID: 950' || { echo "FAIL $U mapper init"; f=1; }
  echo "$L" | grep -aq 'MAPPER-DUP\]\|ID-CAP\]' && { echo "FAIL $U MAPPER-DUP/ID-CAP"; f=1; }
  echo "$L" | grep -a 'GATE-RATIO\] LIVE nạp buffer' | tail -1 | grep -q 'warm-up=false' || { echo "FAIL $U gate chua armed"; f=1; }
  [ "$(systemctl is-active $U)" = active ] || { echo "FAIL $U khong active"; f=1; }
  [ $f = 0 ] && echo "== $U PASS" || echo "== $U FAIL — r_rollback_shadow.sh"
  return $f
}
R=0
case $WHO in c3|all) swap1 shadow-c3 /home/ubuntu/shadow_c3/app $G/s1_new.bin || R=1;; esac
[ $R = 0 ] || { echo "dung truoc shadow #2"; exit 1; }
case $WHO in c3b|all) swap1 shadow-c3b /home/ubuntu/shadow_c3b/app $G/s2_new.bin || R=1;; esac
exit $R
