#!/bin/bash
# R4: thu r4_score.py tren fwd GIA (ngau nhien) trong thu muc tam - chi de bat loi code, KHONG phai ket qua.
set -e
T=/home/ubuntu/claude_master/res1109/r4_signal/scoretest
rm -rf $T; mkdir -p $T/out
cp /home/ubuntu/claude_master/res1109/r4_signal/screen/cells.parquet /home/ubuntu/claude_master/res1109/r4_signal/screen/count.json $T/
python3 - <<'EOF'
import numpy as np, pandas as pd
U = pd.read_parquet("/home/ubuntu/claude_master/res1109/r4_signal/screen/r4s_cells.parquet")
rng = np.random.default_rng(1)
U["c0"] = 1.0; U["c24"] = 1 + rng.normal(0, 0.05, len(U)); U["c72"] = 1 + rng.normal(0, 0.08, len(U))
U.to_parquet("/home/ubuntu/claude_master/res1109/r4_signal/scoretest/out/r4s_fwd.parquet", index=False)
EOF
sed -e "s#^G = .*#G = \"$T/\"#" -e "s#^DOC = .*#DOC = \"$T/DOC.md\"#" /home/ubuntu/claude_master/vz_e1_wt/research/r4_signal/r4_score.py > $T/score_t.py
python3 $T/score_t.py 2>&1 | tail -8 | cut -c1-600
cat $T/DOC.md
