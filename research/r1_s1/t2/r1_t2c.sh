#!/bin/bash
# R1 T2c: property test size/DCA live c3 vs sim. Worktree rieng tu 4479b158 (r4u3), PrivateConfig STUB, chi chay 1 test.
set -u
C=4479b158
W=$HOME/claude_master/v12/wt_t2c
O=$HOME/claude_master/res1109/r1_s1
LOG=$O/t2c.log
export LIVE_IS_SHADOW_HOST=true
export MAVEN_OPTS=-Xmx2g
echo "start $(date)" > $LOG
AV=$(free -m | awk '/Mem:/{print $7}'); DF=$(df -BG --output=avail ~ | tail -1 | tr -dc 0-9)
echo "avail_mb=$AV df_g=$DF" >> $LOG
if [ "$AV" -lt 4000 ] || [ "$DF" -lt 15 ]; then echo "SKIP_RESOURCES" >> $LOG; exit 3; fi
cd $HOME/claude_master/v12/c3live
[ -d $W ] || git worktree add -b r1/t2c-sizing $W $C >> $LOG 2>&1
cd $W
PC=src/main/java/com/binance/chuyennd/config/PrivateConfig.java
mkdir -p $(dirname $PC)
grep -v -E '^[[:space:]]*//.*KEY' $HOME/claude_master/v12/c3live/$PC \
  | sed -E '/(API_KEY|SECRET_KEY)[[:space:]]*=/ s/"[^"]*"/"STUB_R4U_NOT_A_KEY"/' > $PC
echo "stub_fields: $(grep -cE 'STUB_R4U_NOT_A_KEY' $PC)" >> $LOG
cp $O/C3SimSizingPropertyTest.java src/test/java/com/binance/chuyennd/c3live/entry/
flock -w 3600 $HOME/claude_master/locks/oracle_heavy.lock nice -n 10 \
  /home/ubuntu/tools/apache-maven-3.9.9/bin/mvn -o -T 1 test -Dtest=C3SimSizingPropertyTest,C3LiveEntryTest -Dsurefire.failIfNoSpecifiedTests=false >> $LOG 2>&1
echo "MVN_RC=$? $(date)" >> $LOG
grep -h 'R1-T2C\|Tests run' $LOG | tail -5
