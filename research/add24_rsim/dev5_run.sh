#!/bin/bash
# DEV5 (ERRATA2): cua so DEV (cham lenh start 04-01..06-15) + S-G2 ca quy 2026Q2 (sel/follow 04-01..06-30), 2 lane duong gia trong nen.
set -u
B=$HOME/claude_master/w3/add24/b; S=/dev/shm/add24/b; FX=$S/fx_dev5; DS=$HOME/claude_master/w3/ho5/a3/data26/ds
PIN=$S/kg_pin/exchange_info_pin.json
mkdir -p $FX $FX/av2 $S/kl_ref_dev5 $S/out_dev5
python3 $B/conv_rsim.py --warm_lo 2026-01-01 --lo 2026-04-01 --hi 2026-07-01 --bins $DS/predict_wf_20260101.bin $DS/predict_wf_20260401.bin --out $FX || exit 1
python3 $B/check_conv.py $FX 20260401 20260701 || exit 2
python3 - <<'PY'
import gzip
lo=1781456400000   # 2026-06-15 00:00 +07
with gzip.open('/dev/shm/add24/b/fx_dev5/av2/cand_win.csv.gz','wt') as f:
    for ln in gzip.open('/dev/shm/add24/b/fx_dev5/cand.csv.gz','rt'):
        if ln.startswith('ts') or int(ln.split(',',1)[0])>=lo: f.write(ln)
PY
python3 -I $B/dl_avail.py --cand $FX/av2/cand_win.csv.gz --lo 2026-06-15 --hi 2026-07-01 --out $FX/av2 || exit 3
python3 - <<'PY'
import gzip, shutil
S='/dev/shm/add24/b/'
with open(S+'fx_dev5/unavail.csv','w') as f:
    f.write('ts,symbol,reason\n')
    for src in (S+'fx_dev/unavail.csv', S+'fx_dev5/av2/unavail.csv'):
        for ln in open(src):
            if not ln.startswith('ts'): f.write(ln)
with gzip.open(S+'fx_dev5/cand_bars.csv.gz','wt') as f:
    f.write('symbol,t,o,h,l,c\n')
    for src in (S+'fx_dev/cand_bars.csv.gz', S+'fx_dev5/av2/cand_bars.csv.gz'):
        for ln in gzip.open(src,'rt'):
            if not ln.startswith('symbol'): f.write(ln)
shutil.copy(S+'fx_dev/avail_manifest.json', S+'fx_dev5/avail_manifest_part1.json'); shutil.copy(S+'fx_dev5/av2/avail_manifest.json', S+'fx_dev5/avail_manifest.json')
PY
python3 -I $B/dl_ref.py 2026-04-01 2026-07-01 $S/kl_ref_dev5 || exit 4
python3 -I $B/build_fx.py --fx $FX --kl $S/kl --klref $S/kl_ref_dev5 --end 2026-07-01 --patch_settling --pin $PIN || exit 5
python3 $B/ssz_inputs.py 20260401 20260615 $FX || exit 6
for L in sim sens; do
  N=DEV5_$L
  ADD24_INTRABAR=$L flock -w 3600 $HOME/claude_master/locks/oracle_heavy.lock nice -n 10 $B/run_rsim.sh $N $FX $S/out_dev5 || exit 7
  $B/run_ssz.sh $S/out_dev5/$N $FX || exit 8
  python3 $B/score_rsim.py $S/out_dev5/$N $FX 20260401 20260615 --quarter 2026Q2 --json $S/out_dev5/$N/score.json > $S/out_dev5/$N/score.txt 2>&1 || exit 9
  python3 $B/gates_rsim.py $S/out_dev5/$N $FX > $S/out_dev5/$N/gates.json || exit 10
done
echo DEV5_DONE
