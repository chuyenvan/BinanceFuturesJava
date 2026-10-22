#!/bin/bash
# TSX_V3_JAVA pipeline cham: cho run tsx2 (TSX_V2_SIM) -> DEV score -> HO MTM -> HO score. Khong day kernel.
R=~/claude_master/vz_e1_wt
W=~/claude_master/tsx_v3_java
cd $W
need() {
  python3 - "$1" <<'PY'
import json, sys
s2 = json.load(open("/home/ubuntu/claude_master/tsx2sim/state.json"))
dev = ["a1", "s7", "s13", "s21", "s99", "s123", "s777", "s2024"]; ho = [42, 7, 13, 21, 99, 123, 777, 2024]
if sys.argv[1] == "dev":
    t = ["tsx2-%s-%s" % (a, s) for a in ("v420", "vt25", "vl45") for s in dev]
else:
    t = ["tsx2-ho-%s-s%d" % (a, s) for a in ("v420", "vt25", "vl45") for s in ho]
left = [x for x in t if s2.get(x, {}).get("state") != "DONE"]
print(sys.argv[1], len(left), " ".join(left[:8]))
sys.exit(0 if not left else 1)
PY
}
while ! need dev > need_dev.txt; do sleep 300; done
echo "DEV_ALL_DONE $(date '+%F %T')" >> pipe.log
python3 $R/research/tsx_v3_java/score.py > score.log 2>&1 < /dev/null
echo "SCORE_EXIT=$? $(date '+%F %T')" >> pipe.log
while ! need ho > need_ho.txt; do sleep 300; done
echo "HO_ALL_DONE $(date '+%F %T')" >> pipe.log
TAGS=""
for s in 42 7 13 21 99 123 777 2024; do TAGS="$TAGS ho4-k24-b-s$s tsx-ho-x14-s$s"; done
for a in v420 vt25 vl45; do for s in 42 7 13 21 99 123 777 2024; do TAGS="$TAGS tsx2-ho-$a-s$s"; done; done
python3 ~/claude_master/ks_wt/research/analysis/ecm_mtm_h.py $W/ho_mtm.json $TAGS > ho_mtm.log 2>&1 < /dev/null
echo "HO_MTM_EXIT=$? $(date '+%F %T')" >> pipe.log
python3 $R/research/tsx_v3_java/ho_score.py > ho_score.log 2>&1 < /dev/null
echo "HO_SCORE_EXIT=$? $(date '+%F %T')" >> pipe.log
