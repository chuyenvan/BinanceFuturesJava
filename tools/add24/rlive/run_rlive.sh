#!/bin/bash
# ADD24 R-LIVE - 1 LENH.
#   CHINH THUC (CHI sau: owner duyet P1 = commit OWNER_DECISION_*; A1 duyet harness = commit HEAD nay; MASTER commit errata):
#     ADD24_P1_APPROVED=<commit owner> A1_APPROVED=<HEAD> EXINFO=<exchangeInfo json(.gz) da khai trong errata> \
#       bash ~/claude_master/w3/add24_wt/tools/add24/rlive/run_rlive.sh official
#   DEV (fixture 11-05 da co, dry 11-05; khong P1): bash .../run_rlive.sh dev1105
# Moi java: jar STUB + bwrap --unshare-net + LIVE_IS_SHADOW_HOST=true + adapter Fake/dry (run_lane_stub.sh). Khoa chay 1 lan (official).
set -u
MODE=${1:?official|dev1105}
T=$(cd "$(dirname "$0")" && pwd); W=$(cd "$T/../../.." && pwd); A=$HOME/claude_master/w3/add24/a
export LIVE_IS_SHADOW_HOST=true
DF=$(df -BM --output=avail / | tail -1 | tr -dc 0-9); [ "$DF" -ge 15300 ] || { echo "DUNG: dia $DF MB < 15300"; exit 8; }
AV=$(awk '/MemAvailable/{print int($2/1024)}' /proc/meminfo); [ "$AV" -ge 4000 ] || { echo "DUNG: RAM $AV MB < 4000"; exit 8; }
STUB=/dev/shm/add24/jar/binance-java-sdk-1.2.4.jar_add24_stub_01cfbb43; EXPM=cf0f479241265de68836716ee66a1866
if [ ! -f $STUB ] || [ "$(md5sum < $STUB | cut -d' ' -f1)" != "$EXPM" ]; then bash $T/../make_stub.sh || exit 9; fi
[ "$(md5sum < $STUB | cut -d' ' -f1)" = "$EXPM" ] || { echo "TU CHOI: stub md5"; exit 9; }
HEAD=$(git -C $W rev-parse --short HEAD)
TS=$(date +%m%d_%H%M%S); OUT=/dev/shm/add24/rlive_${MODE}_$TS; mkdir -p $OUT
H="flock -w 3600 $HOME/claude_master/locks/oracle_heavy.lock nice -n 10"
LANE=$T/../run_lane_stub.sh
if [ "$MODE" = official ]; then
  [ -n "${A1_APPROVED:-}" ] || { echo "TU CHOI: thieu A1_APPROVED"; exit 2; }
  case "$A1_APPROVED" in "$HEAD"*) ;; *) echo "TU CHOI: HEAD $HEAD != A1_APPROVED"; exit 2;; esac
  [ -z "$(git -C $W status --porcelain -- tools/add24 src/test)" ] || { echo "TU CHOI: worktree chua commit"; exit 2; }
  python3 -c "import sys; sys.path.insert(0,'$T'); import p1_gate; print(p1_gate.require_p1())" || exit 2
  [ -n "${EXINFO:-}" ] && [ -f "$EXINFO" ] || { echo "TU CHOI: thieu EXINFO (khai trong errata)"; exit 2; }
  LOCK=$A/OFFICIAL_ADD24_RLIVE.lock
  [ -e $LOCK ] && [ -z "${E2E_ERRATA:-}" ] && { echo "TU CHOI: da chay chinh thuc (khoa $LOCK); mo lai CHI voi E2E_ERRATA moi"; exit 2; }
  [ -n "${E2E_ERRATA:-}" ] && grep -q "errata=${E2E_ERRATA} " $LOCK 2>/dev/null && { echo "TU CHOI: errata da dung"; exit 2; }
  echo "$(date -Is) head=$HEAD a1=$A1_APPROVED p1=$ADD24_P1_APPROVED errata=${E2E_ERRATA:-} out=$OUT " >> $LOCK
  read TCUT TDAY < <(python3 -c "import sys; sys.path.insert(0,'$T'); import rlive_fixture as F; print(*F.tcut())")
  START='2026-11-19 09:31'; END="$TCUT"; CAP=1000; FLAGS=on; APPLY=on
  DAYS=$(python3 -c "
from datetime import date,timedelta; d=date(2026,11,19); e=date.fromisoformat('$TDAY'); print(','.join(str(d+timedelta(i)) for i in range((e-d).days+1)))")
  python3 -I $T/live_log_parse.py --days $DAYS --start "$START" --end "$END" --out $OUT/live --mode full || exit 11
  python3 $T/rlive_fixture.py --out $OUT/fx --live $OUT/live --exinfo $EXINFO || exit 12
  FX=$OUT/fx; MARK="--mark $FX/mark.csv.gz"; export E2E_OFFICIAL=1
  L0N=L0; L0LANE=(FAKE $CAP $FLAGS); DRYLANE=(DRY $CAP $FLAGS)
else
  START='2026-11-05 07:00'; END='2026-11-14 07:00'; CAP=10000; FLAGS=off; APPLY=off
  DAYS=2026-11-04,2026-11-05,2026-11-06,2026-11-07,2026-11-08,2026-11-09,2026-11-10,2026-11-11,2026-11-12,2026-11-13
  python3 -I $T/live_log_parse.py --days $DAYS --start "$START" --end "$END" --out $OUT/live --mode full || exit 11
  FX=$HOME/claude_master/e2e_v12/fx1105; MARK=""
  L0N=R-OLD; L0LANE=(DRY $CAP $FLAGS); DRYLANE=(DRY $CAP $FLAGS)
fi
# dem doc lap V4 (grep tren dong log khong trung, trong cua so)
V4=$(for d in ${DAYS//,/ }; do for f in $HOME/claude_master/pull242/$d/logs/full.log@*.gz; do [ -f $f ] && zcat $f; done; done | sort -u | grep -F '[C3-LIVE] SUBMIT ' | grep -F ' SUBMITTED ' | \
  python3 -c "
import sys
from datetime import datetime,timedelta,timezone
z=timezone(timedelta(hours=7)); S=datetime.strptime('$START','%Y-%m-%d %H:%M').replace(tzinfo=z); E=datetime.strptime('$END','%Y-%m-%d %H:%M').replace(tzinfo=z)
print(sum(1 for l in sys.stdin if S<=datetime.strptime(l[:19],'%d/%m/%Y %H:%M:%S').replace(tzinfo=z)<E))")
python3 - <<PY
import csv
r=[x for x in csv.DictReader(open('$OUT/live/fill_stream.csv')) if x['cid'].startswith('c3-')]
open('$OUT/live/follow.csv','w').write('cid,avg\n'+''.join('%s,%s\n'%(x['cid'],x['avg']) for x in r))
PY
export E2E_FX_DIR=$FX E2E_OUT=$OUT E2E_ENV242=$HOME/claude_master/e2e_v12/env242_whitelist.raw ADD24_OVR_FILE=$T/overrides_rlive.env
BLK=E2E_LIVE_BLOCK_FILE=$OUT/live/block.csv
$H $LANE $L0N ${L0LANE[@]} $BLK | tee -a $OUT/run_all.txt
$H $LANE L0-FOLLOW FAKE $CAP $FLAGS $BLK E2E_FOLLOW_FILLS=$OUT/live/follow.csv | tee -a $OUT/run_all.txt
[ "$MODE" = official ] && $H $LANE L0-DRY ${DRYLANE[@]} $BLK | tee -a $OUT/run_all.txt
[ "$MODE" = official ] && $H $LANE L-10K FAKE 10000 $FLAGS $BLK | tee -a $OUT/run_all.txt
LANES=$L0N,L0-FOLLOW; [ "$MODE" = official ] && LANES=$LANES,L0-DRY,L-10K
python3 $T/rlive_gates.py --out-dir $OUT --fx $FX --live $OUT/live --start "$START" --end "$END" --v4-grep "$V4" --lanes $LANES --v8-lane $L0N \
  --live-main $A/v8_live_banner_main_1120_0617.txt --live-other $A/v8_live_banner_other_1120_0617.txt \
  --extra stub=$STUB env=$E2E_ENV242 ovr=$ADD24_OVR_FILE > $OUT/gates.txt 2>&1; GRC=$?
cat $OUT/gates.txt
if [ $GRC != 0 ] && [ "$MODE" = official ]; then echo "CONG V truot => KHONG cham (sua dau vao bang errata)"; exit 13; fi
python3 $T/rlive_score.py --live $OUT/live --rig $OUT/$L0N --follow $OUT/L0-FOLLOW --fx $FX $MARK --cap $CAP --apply-ratio $APPLY \
  --start "$START" --end "$END" --out $OUT/score_L0 | tee $OUT/score_L0.txt
[ "$MODE" = official ] && python3 $T/rlive_score.py --live $OUT/live --rig $OUT/L0-DRY --fx $FX $MARK --cap $CAP --apply-ratio $APPLY \
  --start "$START" --end "$END" --out $OUT/score_L0DRY | tee $OUT/score_L0DRY.txt
K=$A/rlive_${MODE}_$TS; mkdir -p $K
cp -r $OUT/score_L0* $OUT/gates.json $OUT/gates.txt $OUT/V8.json $OUT/run_all.txt $K/ 2>/dev/null
cp $OUT/live/counts.json $K/live_counts.json
for L in ${LANES//,/ }; do mkdir -p $K/$L; cp $OUT/$L/{legs.csv,events.csv,fills.csv,result.json,run.log,env_used.sh} $K/$L/ 2>/dev/null; done
echo "R-LIVE $MODE xong head=$HEAD out=$OUT keep=$K gates_rc=$GRC"
