#!/bin/bash
# E2E_REPLAY_V12 - chay MOI luot prereg ?4 + REF doc lap + bo cham, tren fixture E2E_FX_DIR (mac dinh DEV 10-30 ERRATA1 fx1030).
# Goi qua lock (khong long flock ben trong):
#   flock -w 3600 ~/claude_master/locks/oracle_heavy.lock nice -n 10 tools/e2e/run_all.sh
# env: E2E_FX_DIR, E2E_OUT, E2E_ENV242, SDCA_AT (ms, mac dinh START+12h), FIN_INJ_AT (ms, mac dinh START), E2E_OFFICIAL=1 cho 11-05
# ERRATA1: REF doc khop SAN cua luot (fills.csv) de tinh E (C_eff) => REF chay SAU luot replay tuong ung.
#   S-TS (CHI fixture dev, khong chay khi E2E_OFFICIAL=1): = R0 + gia phang sau END toi END+168h+30' => co cum TIME_STOP 168 h
#   de thu bo cham X1 (fixture 10-30 chi 72 h < 168 h).
set -u
W=$(cd "$(dirname "$0")/../.." && pwd)
export E2E_FX_DIR=${E2E_FX_DIR:-$HOME/claude_master/e2e_v12/fx1030}
export E2E_OUT=${E2E_OUT:-$HOME/claude_master/e2e_v12/out}
export E2E_ENV242=${E2E_ENV242:-$HOME/claude_master/e2e_v12/env242_whitelist.raw}
START=$(python3 -c "import json;print(json.load(open('$E2E_FX_DIR/manifest.json'))['START'])")
END=$(python3 -c "import json;print(json.load(open('$E2E_FX_DIR/manifest.json'))['END'])")
SDCA_AT=${SDCA_AT:-$((START + 12*3600000))}
FIN_INJ_AT=${FIN_INJ_AT:-$START}
STS_END=$((END + 168*3600000 + 30*60000))
T=$W/tools/e2e
mkdir -p "$E2E_OUT"
echo "fx=$E2E_FX_DIR out=$E2E_OUT START=$START SDCA_AT=$SDCA_AT FIN_INJ_AT=$FIN_INJ_AT errata=${E2E_ERRATA:-}" | tee "$E2E_OUT/run_all.txt"
lane() { "$T/run_lane.sh" "$@" | tee -a "$E2E_OUT/run_all.txt"; }
lane R0      FAKE 10000 on
lane R0-DRY  DRY  10000 on
lane R-OLD   DRY  10000 off
lane S-DCA   FAKE 10000 on E2E_SDCA_AT=$SDCA_AT
lane FIN-INJ FAKE 10000 on E2E_FIN_INJ_AT=$FIN_INJ_AT
lane R-1000  DRY  1000  on
lane R-4000  DRY  4000  on
if [ "${E2E_OFFICIAL:-0}" != 1 ]; then
  lane S-TS  FAKE 10000 on E2E_FLAT_EXT=1 E2E_END=$STS_END
fi
# REF doc lap (khong doc quyet dinh/output cua replay; chi khop SAN fills.csv cho E - ERRATA1 N4)
REF=$E2E_OUT/_ref
ref() { n=$1; shift; mkdir -p "$REF/$n"; python3 "$T/ref_v12.py" --fx "$E2E_FX_DIR" --env "$E2E_ENV242" --out "$REF/$n" --fills "$E2E_OUT/$n/fills.csv" "$@" > "$REF/$n/ref.log" 2>&1; echo "REF $n rc=$?" | tee -a "$E2E_OUT/run_all.txt"; }
ref R0      --venue FAKE --capital 10000 --flags on
ref R0-DRY  --venue DRY  --capital 10000 --flags on
ref S-DCA   --venue FAKE --capital 10000 --flags on --sdca-at "$SDCA_AT"
ref FIN-INJ --venue FAKE --capital 10000 --flags on --fin-inj-at "$FIN_INJ_AT"
if [ "${E2E_OFFICIAL:-0}" != 1 ]; then
  ref S-TS  --venue FAKE --capital 10000 --flags on --flat-ext --end "$STS_END"
fi
python3 "$T/check_v12.py" --runs "$E2E_OUT" --ref "$REF" --fx "$E2E_FX_DIR" --env "$E2E_ENV242" --out "$E2E_OUT/check_v12.json" \
  --dry-1105 "$E2E_FX_DIR/dry_submits.csv" --labels-1105 "${LABELS_1105:-$T/labels_1105.csv}" > "$E2E_OUT/check_v12.txt" 2>&1
echo "CHECK rc=$?" | tee -a "$E2E_OUT/run_all.txt"
head -25 "$E2E_OUT/check_v12.txt"
