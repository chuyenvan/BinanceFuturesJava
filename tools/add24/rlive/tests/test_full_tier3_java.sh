#!/bin/bash
# ADD24 test ERRATA5 (Java, STUB + bwrap): D1 (a) so c3 rig day (SIM_U_MAX=0.001 CHI trong test) ma live khong day (E2E_FULL_FROM_LIVE=1,
# khong dong FULL) => gate KHONG bao day (bookfull=0), rig van nap r; (b) live FULL o phut M1 => gate bookfull=1, 0 r, 0 SUBMIT o M1;
# tier3: chan (dts, SYM, DCA_LEVEL1) theo vet => leg DCA do bien mat. Ket qua: $1 (json).
set -u
T=$(cd "$(dirname "$0")/.." && pwd); OUTJ=${1:-/dev/shm/add24/test_full_tier3.json}
D=/dev/shm/add24/tf_$(date +%H%M%S); mkdir -p $D
H="flock -w 3600 $HOME/claude_master/locks/oracle_heavy.lock nice -n 10"
export E2E_FX_DIR=$HOME/claude_master/e2e_v12/fx1105 E2E_OUT=$D E2E_ENV242=$HOME/claude_master/e2e_v12/env242_whitelist.raw
M1=1793893860000
read DD DS DL < <(python3 -c "
import csv
r=[x for x in csv.DictReader(open('$HOME/claude_master/e2e_v12/out1105_1117_0132/S-DCA/legs.csv')) if x['outcome']=='SUBMITTED' and int(x['leg_idx'])>0]
print(r[0]['decision_ts'], r[0]['symbol'], r[0]['level'])")
printf 'decision_ts,symbol,level,kind\n' > $D/empty.csv
printf 'decision_ts,symbol,level,kind\n%s,FULL,*,GATE_SKIPFULL\n' $M1 > $D/full.csv
printf 'decision_ts,symbol,level,kind\n%s,%s,%s,TIER3_DCA\n' $DD $DS $DL > $D/t3.csv
$H $T/../run_lane_stub.sh A0 FAKE 10000 on SIM_U_MAX=0.001 E2E_LIVE_BLOCK_FILE=$D/empty.csv > $D/a0.txt 2>&1
$H $T/../run_lane_stub.sh A1 FAKE 10000 on SIM_U_MAX=0.001 E2E_LIVE_BLOCK_FILE=$D/empty.csv E2E_FULL_FROM_LIVE=1 > $D/a1.txt 2>&1
$H $T/../run_lane_stub.sh B1 FAKE 10000 on E2E_LIVE_BLOCK_FILE=$D/full.csv E2E_FULL_FROM_LIVE=1 > $D/b1.txt 2>&1
$H $T/../run_lane_stub.sh T3 FAKE 10000 on E2E_SDCA_AT=1793894400000 E2E_LIVE_BLOCK_FILE=$D/t3.csv E2E_FULL_FROM_LIVE=1 > $D/t3.txt 2>&1
python3 - "$D" "$OUTJ" $M1 $DD $DS <<'PY'
import csv, gzip, json, sys
d, o, m1, dd, ds = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), sys.argv[5]
tr = lambda L: list(csv.DictReader(gzip.open('%s/%s/trace_dec.csv.gz' % (d, L), 'rt')))
app = lambda L: sum(1 for _ in csv.DictReader(gzip.open('%s/%s/appended.csv.gz' % (d, L), 'rt')))
legs = lambda L: [x for x in csv.DictReader(open('%s/%s/legs.csv' % (d, L))) if x['outcome'] == 'SUBMITTED']
a0, a1, b1 = tr('A0'), tr('A1'), tr('B1')
res = {'a_full_rows_c3_rig': sum(1 for x in a0 if x['bookfull'] == '1'), 'a_full_rows_theo_live': sum(1 for x in a1 if x['bookfull'] == '1'),
       'a_appended_c3': app('A0'), 'a_appended_theo_live': app('A1'),
       'b_M1_gated_full': sum(1 for x in b1 if int(x['ts']) == m1 and x['gated'] == '1' and x['bookfull'] == '1'),
       'b_M1_appended': sum(1 for x in csv.DictReader(gzip.open(d + '/B1/appended.csv.gz', 'rt')) if int(x['ts']) == m1),
       'b_M1_submit': sum(1 for x in legs('B1') if int(x['decision_ts']) == m1),
       't3_leg_blocked': not any(int(x['decision_ts']) == dd and x['symbol'] == ds and int(x['leg_idx']) > 0 for x in legs('T3')),
       't3_ref_leg_present': True}
res['ok'] = (res['a_full_rows_c3_rig'] > 0 and res['a_full_rows_theo_live'] == 0 and res['a_appended_theo_live'] > res['a_appended_c3']
             and res['b_M1_gated_full'] > 0 and res['b_M1_appended'] == 0 and res['b_M1_submit'] == 0 and res['t3_leg_blocked'])
json.dump(res, open(o, 'w'), indent=1); print(json.dumps(res)); sys.exit(0 if res['ok'] else 1)
PY
RC=$?; rm -rf $D; exit $RC
