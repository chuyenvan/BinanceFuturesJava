#!/bin/bash
# X1 — chuoi ledger -> S1 -> map, moi buoc co CONG byte-identical (docs/prereg/PREREG_X1.md muc 2).
# Cong FAIL => dung ngay, KHONG chay tiep. Chay nen: nohup bash run_x1.sh > /home/ubuntu/x1log/chain.out 2>&1 &
set -u
R=/home/ubuntu/src/BinanceFuturesJava
X=$R/research/pipeline/x1
L=/home/ubuntu/x1log
mkdir -p $L
CUTS16="20220101 20220401 20220701 20221001 20230101 20230401 20230701 20231001 20240101 20240401 20240701 20241001 20250101 20250401 20250701 20251001"
cd $X

echo "### $(date +%T) G1 featv2"
python3 -u x1_gates.py g1 2>&1 | tee $L/g1.out || { echo "X1_ABORT_G1"; exit 1; }

echo "### $(date +%T) LEDGER"
env X1_T1=2026-01-01 X1_CUTS="$CUTS16" X1_LNAME=cand_dev_x1 X1_LBGLOB='202[1-5]' \
    python3 -u x1_ledger.py build > $L/ledger.out 2>&1 || { echo "X1_ABORT_LEDGER rc=$?"; tail -20 $L/ledger.out; exit 1; }
tail -4 $L/ledger.out
echo "### $(date +%T) G2 ledger"
python3 -u x1_gates.py g2 2>&1 | tee $L/g2.out || { echo "X1_ABORT_G2"; exit 1; }

echo "### $(date +%T) S1 RANK 16 fold"
env X1_LNAME=cand_dev_x1 X1_FEAT=/home/ubuntu/featv2/feat_v2_x1.parquet X1_ICOUT=pool_rankic_x1 \
    X1_CUTS="$CUTS16" X1_SHUF=0,7,15 \
    python3 -u x1_s1_rank.py 2x1 > $L/s1.out 2>&1 || { echo "X1_ABORT_S1 rc=$?"; tail -20 $L/s1.out; exit 1; }
grep -E "fold |edge5|DONE" $L/s1.out | tail -25
echo "### $(date +%T) G3 pred_s1a2x1"
python3 -u x1_gates.py g3 2>&1 | tee $L/g3.out || { echo "X1_ABORT_G3"; exit 1; }

echo "### $(date +%T) BUILD_MAP 16 fold"
env X1_CUTS="$CUTS16" python3 -u x1_build_map.py s1a2x1 /home/ubuntu/predwf_map_s1a2_x1 \
    > $L/map.out 2>&1 || { echo "X1_ABORT_MAP rc=$?"; tail -20 $L/map.out; exit 1; }
tail -20 $L/map.out
echo "### $(date +%T) G4 bins"
python3 -u x1_gates.py g4 2>&1 | tee $L/g4.out || { echo "X1_ABORT_G4"; exit 1; }

echo "### $(date +%T) sha256 bins X1"
cd /home/ubuntu/predwf_map_s1a2_x1 && sha256sum predict_wf_*.bin | tee BINS_SHA256
ls -la /home/ubuntu/predwf_map_s1a2_x1 | tail -20
df -BG --output=avail / | tail -1
echo "X1_CHAIN_OK $(date +%T)"
