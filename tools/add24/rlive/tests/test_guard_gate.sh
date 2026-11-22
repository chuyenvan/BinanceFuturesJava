#!/bin/bash
# ADD24 test (d): tiem "*|*" (guard ca phut) vao 2 phut co gate trong R0 fx1105 => rig 0 lan goi gate (trace_dec gated) + 0 ban ghi r
# (appended) + 0 SUBMIT o 2 phut do. STUB + bwrap qua run_lane_stub.sh. Ket qua: $1 (json).
set -u
T=$(cd "$(dirname "$0")/.." && pwd); OUTJ=${1:-/dev/shm/add24/test_guard_gate.json}
D=/dev/shm/add24/tg_$(date +%H%M%S); mkdir -p $D
M1=1793893860000; M2=1793836920000
printf 'decision_ts,symbol,level,kind\n%s,*,*,TEST\n%s,*,*,TEST\n' $M1 $M2 > $D/block.csv
E2E_FX_DIR=$HOME/claude_master/e2e_v12/fx1105 E2E_OUT=$D E2E_ENV242=$HOME/claude_master/e2e_v12/env242_whitelist.raw \
  flock -w 3600 $HOME/claude_master/locks/oracle_heavy.lock nice -n 10 $T/../run_lane_stub.sh TGUARD FAKE 10000 on E2E_LIVE_BLOCK_FILE=$D/block.csv > $D/lane.txt 2>&1
python3 - "$D" "$OUTJ" $M1 $M2 <<'PY'
import csv, gzip, json, sys
d, o, m1, m2 = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
ref = '/home/ubuntu/claude_master/e2e_v12/out1105_1117_0132/R0/'
def gated(p, m):
    return sum(1 for x in csv.DictReader(gzip.open(p + 'trace_dec.csv.gz', 'rt')) if int(x['ts']) == m and x['gated'] == '1')
def app(p, m):
    return sum(1 for x in csv.DictReader(gzip.open(p + 'appended.csv.gz', 'rt')) if int(x['ts']) == m)
def sub(p, m):
    return sum(1 for x in csv.DictReader(open(p + 'legs.csv')) if int(x['decision_ts']) == m and x['outcome'] == 'SUBMITTED')
t = d + '/TGUARD/'
res = {'ref_gated': [gated(ref, m1), gated(ref, m2)], 'test_gated': [gated(t, m1), gated(t, m2)],
       'ref_appended': [app(ref, m1), app(ref, m2)], 'test_appended': [app(t, m1), app(t, m2)],
       'ref_submit_m1': sub(ref, m1), 'test_submit_m1': sub(t, m1),
       'inj': json.load(open(t + 'result.json')).get('injections', {}).get('live_guard_minutes_skipped')}
res['ok'] = min(res['ref_gated']) > 0 and res['test_gated'] == [0, 0] and res['test_appended'] == [0, 0] and res['test_submit_m1'] == 0 and res['inj'] == 2
json.dump(res, open(o, 'w'), indent=1); print(json.dumps(res)); sys.exit(0 if res['ok'] else 1)
PY
RC=$?; rm -rf $D; exit $RC
