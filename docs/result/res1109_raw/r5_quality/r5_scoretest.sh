#!/bin/bash
# R5: thu r5_score.py tren Y GIA (ngau nhien) trong thu muc tam - chi bat loi code, KHONG phai ket qua.
set -e
T=/home/ubuntu/claude_master/res1109/r5_quality/scoretest
G=/home/ubuntu/claude_master/res1109/r5_quality
rm -rf $T; mkdir -p $T/out
for f in $G/sig_*.npz $G/sig_meta.json; do ln -s $f $T/; done
python3 - <<'EOF'
import numpy as np, pandas as pd
B = pd.read_parquet("/home/ubuntu/claude_master/res1109/r5_quality/r5q_basket.parquet", columns=["ts"])
rng = np.random.default_rng(3)
B["y72"] = rng.normal(0, 0.05, len(B)); B["y24"] = rng.normal(0, 0.03, len(B))
B.to_parquet("/home/ubuntu/claude_master/res1109/r5_quality/scoretest/out/r5q_y.parquet", index=False)
EOF
sed -e "s#^G = .*#G = \"$T/\"#" -e "s#^RES = .*#RES = \"$T/\"#" /home/ubuntu/claude_master/vz_e1_wt/research/r5_quality/r5_score.py > $T/s.py
python3 -c "import json;json.dump({'selected':['MEAN5','MAX15']},open('$T/sel_override.json','w'))"
time python3 $T/s.py discover 2>&1 | tail -3 | cut -c1-300
cp $T/sel_override.json $T/selection.json
time python3 $T/s.py confirm 2>&1 | tail -2 | cut -c1-400
head -8 $T/R5_SIGNAL_QUALITY_DISCOVER.md
cat $T/R5_SIGNAL_QUALITY_CONFIRM.md
