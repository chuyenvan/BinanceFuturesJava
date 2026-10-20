#!/bin/bash
# do nhay universe (a3): chay lai 2025-12..2026-09 voi 2 tap loai tru
W=/home/ubuntu/claude_master/v11_tsx/off
cd $W
mkdir -p outu classes3
javac -nowarn -cp $W/jar_live.jar -d classes3 /tmp/tsx_src_1020/TsxLiveOffline.java || { echo JAVAC_FAIL; exit 1; }
python3 - <<'EOF'
import json
W = "/home/ubuntu/claude_master/v11_tsx/off/"
syms = [s.strip() for s in open(W + "syms.txt") if s.strip()]
A = sorted([s for s in syms if not s.isascii()] + ["BTCDOMUSDT", "USDCUSDT"])
B = sorted(set(A) | set(json.load(open(W + "univ/univ_check.json"))["not_live_top"].keys()))
open(W + "exclA.txt", "w").write("\n".join(A) + "\n")
open(W + "exclB.txt", "w").write("\n".join(B) + "\n")
print("exclA", len(A), A)
print("exclB", len(B), B)
EOF
for M in 2025-12 2026-01 2026-02 2026-03 2026-04 2026-05 2026-06 2026-07 2026-08 2026-09; do
  if [ -f outu/${M}_daysX1.csv ]; then continue; fi
  python3 /tmp/tsx_src_1020/tsx_prep.py $M || { echo "PREP_FAIL $M"; exit 1; }
  TSX_EXCL=$W/exclA.txt:$W/exclB.txt java -Xmx3g -cp classes3:$W/jar_live.jar tsxoff.TsxLiveOffline ew bin/$M.bin syms.txt outu/$M 2>&1 | grep -v DEBUG | tail -3
  rm -f bin/$M.bin
  echo "OK $M $(date +%T)"
done
J="java -Xmx2g -cp classes3:$W/jar_live.jar tsxoff.TsxLiveOffline"
for K in 0 1; do
  L=""; for M in 2025-12 2026-01 2026-02 2026-03 2026-04 2026-05 2026-06 2026-07 2026-08 2026-09; do L="$L outu/${M}_daysX$K.csv"; done
  $J flags outu/flags26_X$K.csv 2026-01-01 2026-09-30 $L 2>&1 | grep -v DEBUG | tail -1
done
python3 - <<'EOF'
import pandas as pd, json
W = "/home/ubuntu/claude_master/v11_tsx/off/"
base = pd.read_csv(W + "out/flags26_64.csv")
out = {}
for k in ("X0", "X1"):
    f = pd.read_csv(W + "outu/flags26_%s.csv" % k)
    on_b = set(base.loc[base.state == "ON", "date"]); on = set(f.loc[f.state == "ON", "date"])
    out[k] = dict(n_on=len(on), gained=sorted(on - on_b), lost=sorted(on_b - on), dd_max_abs=float((f.dd - base.dd).abs().max()))
    print(k, out[k])
json.dump(out, open(W + "univ/univ_flags.json", "w"), indent=1)
EOF
echo PIPE_UNIV_DONE
