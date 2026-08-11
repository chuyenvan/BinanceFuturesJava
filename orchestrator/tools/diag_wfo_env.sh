#!/usr/bin/env bash
# DIAG read-only: vi sao WfoWorker Oracle FAIL-FAST "khong co ticker ... tu nguon file".
# Chay tren Oracle: bash /home/ubuntu/claudedata/.run/diag_wfo_env.sh
CWD=/home/ubuntu/claudedata/.run/oracle_worker_cwd
echo "== config.properties tai worker cwd =="
grep -E '^(TICKER_SOURCE|AEROSPIKE_READ_CLUSTER|USE_SMART_CACHE|AEROSPIKE_NAMESPACE)=' "$CWD/config.properties" 2>&1
echo "== kaggle_data_hpo tai worker cwd =="
ls -ld "$CWD/kaggle_data_hpo" 2>&1 | head -2
ls "$CWD/kaggle_data_hpo" 2>/dev/null | wc -l
echo "== thu muc ticker file co san =="
for d in /home/ubuntu/claudedata/ticker_regen /home/ubuntu/claudedata/kaggle_data_hpo /home/ubuntu/java/simulator/kaggle_data_hpo; do
  printf '%s -> ' "$d"; ls "$d" 2>/dev/null | wc -l
done
echo "== kernel dir Kaggle =="
ls -1 /home/ubuntu/claudedata/.run/kernels 2>&1 | head -10
echo "== jar lien quan =="
ls -l /home/ubuntu/java/simulator/binance-exit003-20260730.jar 2>&1 | head -2
md5sum /home/ubuntu/java/simulator/binance-exit003-20260730.jar 2>&1 | head -1
echo "== disk =="
df -h /home/ubuntu | tail -1
