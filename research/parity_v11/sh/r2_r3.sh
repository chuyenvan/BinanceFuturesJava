#!/bin/bash
# R2 (cache Vision vs cache 242 da luu, tung o) + R3 (harness offline tren cache Vision vs s6) — PREREG_PARITY_V11_WINDOW §6.
R=$HOME/claude_master/vz_e1_wt/research/parity_v11
W=$HOME/claude_master/parity_v11w
source $W/build/cp.env
H=$HOME/claude_master/v11_settle/harness
U=$W/univ/u_cache1017.txt
export HARNESS_MAPPER_FILE=$W/univ/mapper_u_cache1017.csv LIVE_IS_SHADOW_HOST=true LIVE_WRITE_242_ENABLED=false
R3=$W/runs/r3
for S in "w1 1792155605874 1792155600000 1792198740000 $H/s6 1791922800000 1792198740000" \
         "w2 1792198832747 1792198800000 1792223400000 $H/s6/seg2 1791966000000 1792223400000"; do
  set -- $S
  D=$R3/$1; rm -rf $D; bash $R/sh/mkdir_run.sh $D > /dev/null
  C=cache_$6_$7.ser.gz
  (cd $D && HARNESS_OFFLINE=1 java -Xmx6g -cp $CP_OFF com.binance.chuyennd.aerospike.VisionCacheBuilder $U $W/vision/klines_1m $6 $7 $C holes.csv 2>&1 | grep -a 'cache \|missing=[1-9]' | cut -c1-300)
  (cd $D && java -Xmx8g -cp $CP_OFF com.binance.chuyennd.aerospike.CacheDiff $5/$C $C r2 2>&1 | grep -a 'R2\|minutes=' | cut -c1-900)
  for M in BT NEW2; do
    EX=""; [ $M = NEW2 ] && EX="LIVE_FEAT_INPUT=snapshot"
    (cd $D && env HARNESS_OFFLINE=1 HARNESS_FUNDING_FILE=$W/univ/funding_le202609.csv.gz $EX strace -f --seccomp-bpf -e trace=connect -o strace_$M.txt \
       java -Xmx6g -cp $CP_OFF com.binance.chuyennd.aerospike.V11FeatHarness $M $2 $3 $4 out_$M.csv.gz > log_$M.txt 2>&1; echo "R3 $1 $M exit=$?")
    echo "  connect() tong=$(grep -c 'connect(' $D/strace_$M.txt) toi_242=$(grep -c '103.157.218.242' $D/strace_$M.txt) inet=$(grep 'connect(' $D/strace_$M.txt | grep -c 'AF_INET')"
    python3 $R/py/cmp_runs.py $5/out_$M.csv.gz $D/out_$M.csv.gz gate $D/cmp_gate_$M.json | cut -c1-700
    python3 $R/py/cmp_runs.py $5/fund_$M.csv.gz $D/fund_$M.csv.gz fund $D/cmp_fund_$M.json | cut -c1-700
  done
done
echo R2R3_DONE
