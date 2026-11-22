#!/bin/bash
# DEV-2 (S-D, ERRATA1 EB5/EB6): cum DCA sim FIGHT/SPACE (leg0 PREDICT 2026-01-30 08:43, leg DCA 02-06). Du lieu <= 2026-06-30.
set -u
B=$HOME/claude_master/w3/add24/b; S=/dev/shm/add24/b; FX=$S/fx_dev2; DS=$HOME/claude_master/w3/ho5/a3/data26/ds
mkdir -p $FX $S/kl_dev2 $S/kl_ref_dev2 $S/mkt_dev2 $S/out_dev2
python3 $B/conv_rsim.py --warm_lo 2026-01-01 --lo 2026-01-30 --hi 2026-02-07 --bins $DS/predict_wf_20260101.bin --out $FX || exit 1
python3 $B/check_conv.py $FX 20260130 20260207 || exit 2
KL_OUT=$S/kl_dev2 KL_BEG='20260125 00:00' KL_END='20260207 00:00' python3 -I $B/dl_klines.py || exit 3
python3 - <<'PY'
import gzip
lo=1769706000000  # 2026-01-30 00:00 +07
with gzip.open('/dev/shm/add24/b/fx_dev2/cand_win.csv.gz','wt') as f:
    for ln in gzip.open('/dev/shm/add24/b/fx_dev2/cand.csv.gz','rt'):
        if ln.startswith('ts') or int(ln.split(',',1)[0])>=lo: f.write(ln)
PY
python3 -I $B/dl_avail.py --cand $FX/cand_win.csv.gz --lo 2026-01-30 --hi 2026-02-07 --out $FX || exit 4
python3 -I $B/dl_ref.py 2026-01-30 2026-02-22 $S/kl_ref_dev2 || exit 5
python3 -I $B/dl_mkt.py '20260131 21:30' '20260206 05:00' $S/mkt_dev2 || exit 6
python3 -I $B/build_fx.py --fx $FX --kl $S/kl_dev2 --klref $S/kl_ref_dev2 --end 2026-02-22 --patch_settling --mkt $S/mkt_dev2/mkt.csv.gz --unavail_extra $S/fx_dev/unavail.csv || exit 7
KL_DIR=$S/kl_dev2 python3 $B/ssz_inputs.py 20260130 20260207 $FX || exit 8
flock -w 3600 $HOME/claude_master/locks/oracle_heavy.lock nice -n 10 $B/run_rsim.sh DEV2W $FX $S/out_dev2 || exit 9
$B/run_ssz.sh $S/out_dev2/DEV2W $FX || exit 10
python3 $B/score_rsim.py $S/out_dev2/DEV2W $FX 20260130 20260207 --json $S/out_dev2/DEV2W/score.json || exit 11
echo DEV2_DONE
