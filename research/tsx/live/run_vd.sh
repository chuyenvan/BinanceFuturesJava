#!/bin/bash
# muc 3: co 2026-09-20..10-20 tu Vision (Sep = Kaggle monthly da co; Oct = daily data.binance.vision) + so S_j voi record 242 (cache)
W=/home/ubuntu/claude_master/v11_tsx/off
FJ=/home/ubuntu/claude_master/v11_tsx/jar/binance-java-sdk-1.2.4.jar_v11c_eea5adec
cd $W
D1=${1:-2026-10-19}
python3 /tmp/tsx_src_1020/vision_daily.py 2026-10 2026-10-01 $D1 || { echo VD_FAIL; exit 1; }
mkdir -p outv
TSX_EXCL=$W/excl_notlive_2026-10.txt java -Xmx4g -cp classes3:$FJ tsxoff.TsxLiveOffline ew bin/2026-10_vd.bin syms.txt outv/2026-10 2>&1 | grep -v DEBUG | tail -2
rm -f bin/2026-10_vd.bin
J="java -Xmx2g -cp classes3:$FJ tsxoff.TsxLiveOffline"
$J flags outv/flags_0920_1021_64.csv 2026-09-20 2026-10-21 out/2026-08_days64.csv out/2026-09_days64.csv outv/2026-10_days64.csv 2>&1 | grep -v DEBUG | tail -1
$J flags outv/flags_0920_1021_32.csv 2026-09-20 2026-10-21 out/2026-08_days32.csv out/2026-09_days32.csv outv/2026-10_days32.csv 2>&1 | grep -v DEBUG | tail -1
python3 - <<'EOF'
import pandas as pd
W = "/home/ubuntu/claude_master/v11_tsx/off/"
f = pd.read_csv(W + "outv/flags_0920_1021_64.csv")
print(f[["date", "state", "dd", "p", "max_p", "max_day", "min_n", "reason"]].to_string())
v = pd.read_csv(W + "outv/2026-10_days32.csv").set_index("date")
vl = pd.read_csv(W + "outv/2026-10_daysX0.csv").set_index("date")
c = pd.read_csv(W + "cache_out/cache_1791922800000_1792198740000_days.csv").set_index("date")
c2 = pd.read_csv(W + "cache_out/cache_1791966000000_1792223400000_days.csv").set_index("date")
for d in ("2026-10-14", "2026-10-15", "2026-10-16"):
    cc = c.loc[d] if d in c.index else None
    print(d, "vision32 S=%.9f n=%d" % (v.loc[d, "sum_ew"], v.loc[d, "n_min"]),
          "vision32_liveuniv S=%.9f n=%d" % (vl.loc[d, "sum_ew"], vl.loc[d, "n_min"]),
          "242 S=%.9f n=%d" % (cc["sum_ew"], cc["n_min"]) if cc is not None else "",
          "d_full=%.2e d_univ=%.2e" % (cc["sum_ew"] - v.loc[d, "sum_ew"], cc["sum_ew"] - vl.loc[d, "sum_ew"]) if cc is not None else "")
print(v[["sum_ew", "n_min"]].to_string())
EOF
echo RUN_VD_DONE
