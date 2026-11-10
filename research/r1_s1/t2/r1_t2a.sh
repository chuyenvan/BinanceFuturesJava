#!/bin/bash
# R1 T2a: ExitReplayDevMain (test-classes r4u3) tren TOAN BO ngay co chan DEV cua 1 seed X14 (tsx-x14-a1).
# Cau hinh = profile sim (TRADING_PROFILE=prof_run.properties, config.properties cua kernel). Moi ngay 1 JVM
# (ngay loi khong keo ca lo). Lo 40 ngay; moi lo lay oracle_heavy.lock rieng (khong long flock); xoa px_* sau lo.
set -u
SEED=${SEED:-a1}
B=/home/ubuntu/claude_master/res1109/r1_s1/t2a
WT=/home/ubuntu/claude_master/v12/wt_r4u3
TC=/home/ubuntu/claude_master/v12/wt_t2c/target/test-classes
JAR=/home/ubuntu/claude_master/v12/jar/binance-java-sdk-1.2.4.jar_v12_r4u3
LOGF=/home/ubuntu/kaggle_sim/out/tsx-x14-$SEED/logs/full.log
PROF=/home/ubuntu/kaggle_sim/out/tsx-x14-$SEED/prof_run.properties
mkdir -p $B/raw $B/data $B/out $B/shadow $B/run $B/day
cp /home/ubuntu/kaggle_sim/out/tsx-x14-$SEED/config.properties $B/run/config.properties
for f in /home/ubuntu/claude_master/gvz/k2021/kline1m-2021-*.parquet; do
  ym=$(basename $f .parquet | sed 's/kline1m-//'); [[ "$ym" < "2021-12" ]] && ln -sf $f $B/raw/
done
ln -sf /home/ubuntu/claude_master/res1109/r1_s1/kl/kline1m-*.parquet $B/raw/
grep -o 'SELRANK sym=[^ ]* tOpen=[0-9]\{8\}' $LOGF | sed 's/.*tOpen=//' | sort -u > $B/days.txt
echo "jar=$JAR days=$(wc -l < $B/days.txt) seed=$SEED"
rm -f $B/batch_*
split -l 40 -d -a 3 $B/days.txt $B/batch_
for bf in $B/batch_*; do
  n=$(basename $bf)
  [ -f $B/out/$n.done ] && continue
  DAYS=$(tr '\n' ' ' < $bf)
  flock -w 7200 /home/ubuntu/claude_master/locks/oracle_heavy.lock nice -n 10 bash -c "
    python3 $WT/research/v12exit/extract_dev_klines.py $LOGF $B/raw $B/data $DAYS > $B/out/$n.extract.log 2>&1 || exit 9
    cd $B/run
    for d in $DAYS; do
      [ -s $B/day/\$d.json ] && continue
      rm -f $B/run/open_positions.csv $B/run/ledger.csv $B/run/legs.csv $B/shadow/*   # so giay ghi o CWD: moi ngay so rong
      TRADING_PROFILE=$PROF LIVE_IS_SHADOW_HOST=true SHADOW_C3_DIR=$B/shadow java -Xmx4g -XX:-OmitStackTraceInFastThrow \
        -cp $JAR:$TC com.binance.chuyennd.tradecore.selector.ExitReplayDevMain \
        $B/data $PROF $B/day/\$d.json \$d > $B/day/\$d.log 2>&1
      echo \"\$d rc=\$?\" >> $B/out/$n.rc
      grep -q 'EXIT-REPLAY-DEV' $B/day/\$d.log && grep -v '^\s*at \|INFO\|DEBUG' $B/day/\$d.log | head -0
    done
    rm -f $B/data/px_*.csv.gz"
  touch $B/out/$n.done
  echo "$n $(grep -c 'rc=0' $B/out/$n.rc)/$(wc -l < $B/out/$n.rc) ok $(date +%H:%M)"
done
echo T2A_DONE
