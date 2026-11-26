#!/bin/bash
# TSX_V3 pipeline cham: cho du run (tai dung tsx2 + moi tsx3) -> HO MTM -> ho_score -> score DEV
R=~/claude_master/vz_e1_wt
W=~/claude_master/tsx_v3
cd $W
need() {
  python3 - <<'PY'
import json, os, sys
W2, W3 = "/home/ubuntu/claude_master/tsx2sim", "/home/ubuntu/claude_master/tsx_v3"
s2 = json.load(open(W2 + "/state.json")); s3 = json.load(open(W3 + "/state.json"))
dev = ["a1", "s7", "s13", "s21", "s99", "s123", "s777", "s2024"]; ho = [42, 7, 13, 21, 99, 123, 777, 2024]
t2 = ["tsx2-%s-%s" % (a, s) for a in ("v420", "vt25", "vl45") for s in dev] + ["tsx2-ho-%s-s%d" % (a, s) for a in ("v420", "vt25", "vl45") for s in ho]
t3 = ["tsx3-ctl-s13"] + ["tsx3-v2-" + s for s in dev]
left = [t for t in t2 if s2.get(t, {}).get("state") != "DONE"] + [t for t in t3 if s3.get(t, {}).get("state") != "DONE"]
print(len(left), " ".join(left[:6]))
sys.exit(0 if not left else 1)
PY
}
while ! need > need.txt; do sleep 300; done
echo "ALL_DONE $(date '+%F %T')" >> pipe.log
TAGS=""
for s in 42 7 13 21 99 123 777 2024; do TAGS="$TAGS ho4-k24-b-s$s tsx-ho-x14-s$s"; done
for a in v420 vt25 vl45; do for s in 42 7 13 21 99 123 777 2024; do TAGS="$TAGS tsx2-ho-$a-s$s"; done; done
python3 ~/claude_master/ks_wt/research/analysis/ecm_mtm_h.py $W/ho_mtm.json $TAGS > ho_mtm.log 2>&1 < /dev/null
echo "HO_MTM_EXIT=$? $(date '+%F %T')" >> pipe.log
python3 $R/research/tsx_v3/ho_score.py > ho_score.log 2>&1 < /dev/null
echo "HO_SCORE_EXIT=$? $(date '+%F %T')" >> pipe.log
python3 $R/research/tsx_v3/score.py > score.log 2>&1 < /dev/null
echo "SCORE_EXIT=$? $(date '+%F %T')" >> pipe.log
