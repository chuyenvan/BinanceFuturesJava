#!/bin/bash
# R0 (test chan mang) + R1 (provider offline tren cache 242 DA LUU) — PREREG_PARITY_V11_WINDOW §6. Khong doc/ghi 242.
R=$HOME/claude_master/vz_e1_wt/research/parity_v11
W=$HOME/claude_master/parity_v11w
source $W/build/cp.env
H=$HOME/claude_master/v11_settle/harness
U=$W/univ/u_cache1017.txt
awk '{print $1","NR}' $U > $W/univ/mapper_u_cache1017.csv
export HARNESS_MAPPER_FILE=$W/univ/mapper_u_cache1017.csv LIVE_IS_SHADOW_HOST=true LIVE_WRITE_242_ENABLED=false
# funding Vision monthly <= 2026-09-30 23:59:59.999 UTC
[ -s $W/univ/funding_le202609.csv.gz ] || python3 $R/py/funding_build.py $U 1790812799999 $W/univ/funding_le202609.csv.gz
# ---------------- R0 ----------------
T=$W/runs/r0; rm -rf $T
bash $R/sh/mkdir_run.sh $T/off > /dev/null && bash $R/sh/mkdir_run.sh $T/real real > /dev/null
(cd $T/off && HARNESS_FUNDING_EMPTY_OK=1 java -cp $CP_OFF com.binance.chuyennd.aerospike.OfflineGuardSelfTest driver $CP_OFF $CP_NOSTUB $T/off $T/real 2>&1 | grep -a '\[R0\]')
echo "R0_DRIVER_EXIT=${PIPESTATUS[0]}"
for c in socket242 client242; do
  (cd $T/off && HARNESS_OFFLINE=1 HARNESS_FUNDING_EMPTY_OK=1 strace -f --seccomp-bpf -e trace=connect -o $T/strace_$c.txt java -cp $CP_OFF com.binance.chuyennd.aerospike.OfflineGuardSelfTest case $c > $T/case_$c.log 2>&1; echo "strace case $c exit=$?")
  echo "  connect() tong=$(grep -c 'connect(' $T/strace_$c.txt) toi_242=$(grep -c '103.157.218.242' $T/strace_$c.txt) inet_ngoai_loopback=$(grep 'connect(' $T/strace_$c.txt | grep 'AF_INET' | grep -vc '127.0.0.1')"
  grep -a 'HARNESS-OFFLINE-VIOLATION' $T/case_$c.log | head -1 | cut -c1-200
done
# ---------------- R1 ----------------
R1=$W/runs/r1
for S in "w1 1792155605874 1792155600000 1792198740000 $H/s6 cache_1791922800000_1792198740000.ser.gz" \
         "w2 1792198832747 1792198800000 1792223400000 $H/s6/seg2 cache_1791966000000_1792223400000.ser.gz"; do
  set -- $S
  D=$R1/$1; rm -rf $D; bash $R/sh/mkdir_run.sh $D > /dev/null
  ln -s $5/$6 $D/$6
  for M in BT NEW2; do
    EX=""; [ $M = NEW2 ] && EX="LIVE_FEAT_INPUT=snapshot"
    (cd $D && env HARNESS_OFFLINE=1 HARNESS_FUNDING_FILE=$W/univ/funding_le202609.csv.gz $EX strace -f --seccomp-bpf -e trace=connect -o strace_$M.txt \
       java -Xmx6g -cp $CP_OFF com.binance.chuyennd.aerospike.V11FeatHarness $M $2 $3 $4 out_$M.csv.gz > log_$M.txt 2>&1; echo "R1 $1 $M exit=$?")
    echo "  connect() tong=$(grep -c 'connect(' $D/strace_$M.txt) toi_242=$(grep -c '103.157.218.242' $D/strace_$M.txt) inet=$(grep 'connect(' $D/strace_$M.txt | grep -c 'AF_INET')"
    grep -a 'HARNESS-OFFLINE\]\|VIOLATION\|Loaded Symbol Mapper\|Init funding fee\|AEROSPIKE_READ_CLUSTER\|Exception' $D/log_$M.txt | cut -c1-260 | head -6
    python3 $R/py/cmp_runs.py $5/out_$M.csv.gz $D/out_$M.csv.gz gate $D/cmp_gate_$M.json | cut -c1-600
    python3 $R/py/cmp_runs.py $5/fund_$M.csv.gz $D/fund_$M.csv.gz fund $D/cmp_fund_$M.json | cut -c1-600
  done
done
echo R0R1_DONE
