#!/bin/bash
# Probe trang thai du lieu WFO tren Oracle. Chay qua CE: bg_run <id> /home/ubuntu/claudedata/probe_wfo_data.sh 1.0
# Ket qua ghi vao CE_RUN_DIR de doc bang nut sys_logtail (khong can raw ssh doc log).
OUT=/home/ubuntu/claudedata/.run/mcp_ce/probe_out.txt
exec > "$OUT" 2>&1
echo "=== 1. config.properties (key lines) ==="
grep -E "TICKER_SOURCE|AEROSPIKE|IMPORT_DIR|HOST" /home/ubuntu/java/simulator/config.properties
echo "=== 2. aerospike ns=test set objects ==="
if command -v asinfo >/dev/null 2>&1; then
  asinfo -h 127.0.0.1 -p 3222 -v "sets/test" | tr ';' '\n' | cut -d: -f2,3 | head -40
else
  echo "asinfo KHONG co trong PATH"
fi
echo "=== 3. tim core_symbol_lifecycle ==="
find /home/ubuntu -maxdepth 6 -name "core_symbol_lifecycle*" 2>/dev/null
echo "=== 4. kaggle_data_hpo root (10 dau) ==="
ls /home/ubuntu/java/simulator/kaggle_data_hpo 2>&1 | head -10
echo "=== 5. wfo1m ==="
ls -la /home/ubuntu/claudedata/wfo1m 2>&1 | head -15
echo "=== 6. label_ds_1m ==="
ls -la /home/ubuntu/claudedata/wfo1m/label_ds_1m 2>&1 | head -10
echo "=== 7. features_export_python_v3_1m (dem file) ==="
ls /home/ubuntu/claudedata/wfo1m/features_export_python_v3_1m 2>&1 | wc -l
echo "=== 8. jar moi nhat ==="
ls -lat /home/ubuntu/java/simulator/*.jar 2>&1 | head -5
echo "=== DONE ==="
