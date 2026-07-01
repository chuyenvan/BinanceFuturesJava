#!/bin/bash
set -e
cd ~/java/simulator
JVM="java -Duser.timezone=Asia/Ho_Chi_Minh -Xmx18g -XX:+UseG1GC"
JAR=binance-futures-verify.jar
S=20210101
E=20260624
LOG=~/claudedata/gen_train.log
echo "=== START $(date) | range $S -> $E ===" | tee -a $LOG

# universe (gom coin chet) cho OI
java -Duser.timezone=Asia/Ho_Chi_Minh -cp "$JAR:." DumpSymbolMapper /tmp/oisyms.txt >> $LOG 2>&1
echo "universe=$(wc -l < /tmp/oisyms.txt) coin" | tee -a $LOG

echo "[1/3] ff START $(date)" | tee -a $LOG
$JVM -cp $JAR com.binance.chuyennd.ai_ml.features.export.fundingv2.ExportFeaturesForPythonTool $S $E ~/claudedata/train_ff/ >> $LOG 2>&1
echo "[1/3] ff DONE $(date)" | tee -a $LOG

echo "[2/3] OI START $(date)" | tee -a $LOG
$JVM -cp $JAR com.binance.chuyennd.ai_ml.features.export.fundingv2.ExportFundingOiPerCoin $S $E symfile=/tmp/oisyms.txt >> $LOG 2>&1
echo "[2/3] OI DONE $(date)" | tee -a $LOG

echo "[3/3] label START $(date)" | tee -a $LOG
$JVM -cp $JAR com.binance.chuyennd.ai_ml.features.export.ExportFundingLabel $S $E ~/claudedata/train_label.csv >> $LOG 2>&1
echo "[3/3] label DONE $(date)" | tee -a $LOG
echo "=== ALL DONE $(date) ===" | tee -a $LOG
