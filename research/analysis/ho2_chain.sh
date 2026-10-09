#!/bin/bash
# HO2 phuong an A: bins 2026 (net015 goc ONNX) -> G-B4c -> loai 3 symbol -> funding.bin -> stage + upload sim-ho26a-bundle
set -e
W=/home/ubuntu/claude_master/1009/ho26
H=/home/ubuntu/claude_master/1003/ho1
R=/home/ubuntu/src/BinanceFuturesJava
mkdir -p $W/bins2026A $W/ds
cd $R/research/pipeline/x1
env X1_CUTS="20260101 20260401" X1_G015_DIR=$W/net015_2026A python3 -u x1_build_map.py ho26s1 $W/bins2026A > $W/bins2026A/map.out 2>&1
python3 $R/research/analysis/ho1_bins_check.py $W/net015_2026A $W/bins2026A > $W/bins2026A/check.out 2>&1
python3 $R/research/analysis/ho1_bins_exclude.py $H/b6/symbols.json $W/bins2026A $W/bins2026Ax > $W/exclude.log 2>&1
cd $R/research/analysis
$W/run_locked.sh $W/ds/funding_build.log python3 ho1_funding_build.py build --extra $W/bins2026Ax --market $H/ds/market.bin --out $W/ds/funding.bin
grep -q 'RC=0' $W/ds/funding_build.log
python3 -c "import json;assert json.load(open('$W/ds/funding.bin.json'))['prefix_equal']"
python3 $W/ho2_stage_bundle.py stage $(git -C $R rev-parse --short=8 HEAD) > $W/stage.log 2>&1
python3 $W/ho2_stage_bundle.py upload >> $W/stage.log 2>&1
echo CHAIN_HO2_DONE >> $W/stage.log
