#!/bin/bash
# PULL (READ-ONLY tren 242): chi cat/tar ra stdout, ghi o Oracle. KHONG ghi gi len 242.
set -u
O=/home/ubuntu/claude_master/1002/deploy242/live242
mkdir -p $O
S="ssh -p 2222 -o BatchMode=yes -o ConnectTimeout=20 -i /home/ubuntu/.ssh/id_rsa_chuyennd root@103.157.218.242"
$S 'cd /home/chuyennd/java/v_t_m && tar cf - feat_dump' > $O/feat_dump.tar
$S 'cat /home/chuyennd/java/v_t_m/target/binance-java-sdk-1.2.4.jar' > $O/jar242.jar
$S 'cat /home/chuyennd/java/storage/ai_ml_data/ai_models_reg_v3/Model_Regressor_Return15M.onnx' > $O/gate242.onnx
$S 'cat /home/chuyennd/java/v_t_m/run/gate_ratio_live.bin' > $O/gate_ratio_live.bin
cd $O && sha256sum jar242.jar gate242.onnx gate_ratio_live.bin && ls -la && tar tf feat_dump.tar | wc -l
mkdir -p fd && tar xf feat_dump.tar -C fd && ls fd/feat_dump | head -3
