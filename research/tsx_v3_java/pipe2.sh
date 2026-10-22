#!/bin/bash
# TSX_V3_JAVA pipe2 (thay pipe.sh phan HO): cho 22 run tsx2-ho (TSX_V2_SIM) + 2 run retry tsx3j-ho -> HO MTM -> HO score -> md.
R=~/claude_master/vz_e1_wt
W=~/claude_master/tsx_v3_java
cd $W
need() {
  python3 - <<'PY'
import json, os, sys
s2 = json.load(open("/home/ubuntu/claude_master/tsx2sim/state.json"))
W = "/home/ubuntu/claude_master/tsx_v3_java"
sr = json.load(open(W + "/retry_state.json")) if os.path.exists(W + "/retry_state.json") else {}
ho = [42, 7, 13, 21, 99, 123, 777, 2024]
skip = {"tsx2-ho-vt25-s123", "tsx2-ho-v420-s7"}
t = ["tsx2-ho-%s-s%d" % (a, s) for a in ("v420", "vt25", "vl45") for s in ho]
left = [x for x in t if x not in skip and s2.get(x, {}).get("state") != "DONE"]
left += [x for x in ("tsx3j-ho-vt25-s123", "tsx3j-ho-v420-s7") if sr.get(x, {}).get("state") != "DONE"]
print("ho", len(left), " ".join(left[:8]))
sys.exit(0 if not left else 1)
PY
}
while ! need > need_ho.txt; do sleep 300; done
echo "HO_ALL_DONE $(date '+%F %T')" >> pipe.log
TAGS=""
for s in 42 7 13 21 99 123 777 2024; do TAGS="$TAGS ho4-k24-b-s$s tsx-ho-x14-s$s"; done
for a in v420 vt25 vl45; do for s in 42 7 13 21 99 123 777 2024; do TAGS="$TAGS tsx2-ho-$a-s$s"; done; done
TAGS=$(echo $TAGS | sed 's/tsx2-ho-vt25-s123/tsx3j-ho-vt25-s123/; s/tsx2-ho-v420-s7 /tsx3j-ho-v420-s7 /')
echo "TAGS $TAGS" >> pipe.log
python3 ~/claude_master/ks_wt/research/analysis/ecm_mtm_h.py $W/ho_mtm.json $TAGS > ho_mtm.log 2>&1 < /dev/null
echo "HO_MTM_EXIT=$? $(date '+%F %T')" >> pipe.log
python3 $R/research/tsx_v3_java/ho_score.py > ho_score.log 2>&1 < /dev/null
echo "HO_SCORE_EXIT=$? $(date '+%F %T')" >> pipe.log
python3 $R/research/tsx_v3_java/md.py > md.log 2>&1 < /dev/null
echo "MD_EXIT=$? $(date '+%F %T')" >> pipe.log
