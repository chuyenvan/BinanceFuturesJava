#!/bin/bash
set -e
W=/home/ubuntu/claude_master/v11_tsx/off
cd $W
CP="classes2:$W/jar_live.jar"
J="java -Xmx2g -cp $CP tsxoff.TsxLiveOffline"
D26_64=""; D26_32=""; for M in 2025-12 2026-01 2026-02 2026-03 2026-04 2026-05 2026-06 2026-07 2026-08 2026-09; do D26_64="$D26_64 out/${M}_days64.csv"; D26_32="$D26_32 out/${M}_days32.csv"; done
D22_64=""; D22_32=""; for M in 2021-12 2022-01 2022-02 2022-03 2022-04 2022-05 2022-06 2022-07 2022-08 2022-09 2022-10 2022-11 2022-12; do D22_64="$D22_64 out/${M}_days64.csv"; D22_32="$D22_32 out/${M}_days32.csv"; done
$J flags out/flags26_64.csv 2026-01-01 2026-09-30 $D26_64 2>&1 | grep -v DEBUG | tail -1
$J flags out/flags26_32.csv 2026-01-01 2026-09-30 $D26_32 2>&1 | grep -v DEBUG | tail -1
$J flags out/flags22_64.csv 2022-01-01 2022-12-31 $D22_64 2>&1 | grep -v DEBUG | tail -1
$J flags out/flags22_32.csv 2022-01-01 2022-12-31 $D22_32 2>&1 | grep -v DEBUG | tail -1
for SEED in 42 7 13 21 99 123 777 2024; do
python3 - $SEED <<'EOF'
import sys, pandas as pd
sd = sys.argv[1]
d = pd.read_csv("/home/ubuntu/kaggle_sim/out/tsx-ho-x14-s%s/storage/printDone.csv" % sd, index_col=False, dtype=str)
s = pd.to_datetime(d.start, format="%Y%m%d %H:%M") - pd.Timedelta(hours=7)   # printDone in +07
e = pd.to_datetime(d.end, format="%Y%m%d %H:%M") - pd.Timedelta(hours=7)
o = pd.DataFrame(dict(sym=d.sym, anchor_ms=s.astype("int64") // 10**6, exit_ms=e.astype("int64") // 10**6, status=d.status))
o = o[e >= pd.Timestamp("2026-01-01")]
# cum = (sym, exit): cac leg cua MOT cum (DCA/BIG_DOWN) in rieng dong nhung dong cung phut; neo = leg dau (clusterFirstLegTime)
o = o.groupby(["sym", "exit_ms"], as_index=False).agg(anchor_ms=("anchor_ms", "min"), status=("status", "first"), n_rows=("anchor_ms", "size"))
o = o[["sym", "anchor_ms", "exit_ms", "status", "n_rows"]]
o.to_csv("/home/ubuntu/claude_master/v11_tsx/off/out/trades_s%s.csv" % sd, index=False)
print("trades", sd, len(o))
EOF
$J replay out/flags26_64.csv out/trades_s$SEED.csv out/replay_s$SEED.csv 2>&1 | grep -v DEBUG | tail -1
done
python3 /tmp/tsx_src_1020/compare_ac.py
