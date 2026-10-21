#!/bin/bash
# v11d legacy-equivalence OFFLINE: harness parity_v11 (HARNESS_OFFLINE=1, stub Aerospike, strace connect) tren jar v11d,
# [GHI CHU 10-21] Luot NEW2_FLAGS cua script nay da chay KHONG co hook (patch assert "anchor NEW2 loop" do vong LIVE cung mau)
#   => thay bang ops/verify/harness_flags_v11d.sh (co hook, ket qua dung trong runbook §1). BT/NEW2/BT_FLAGS hop le.
# so voi output eea5adec da chay 10-21 13:07 (parity_v11w/runs/r1). KHONG doc/ghi 242. Log ra file + stderr co timestamp.
set -u
log(){ echo "$(date '+%F %T') $*" | tee -a $V/logs/harness.log >&2; }
V=$HOME/claude_master/v11d
R=$HOME/claude_master/vz_e1_wt/research/parity_v11
W=$HOME/claude_master/parity_v11w
J=$(ls $V/jar/binance-java-sdk-1.2.4.jar_v11d_*)
B=$V/parity_build
mkdir -p $V/logs
log "jar=$J md5=$(md5sum < $J | cut -c1-32)"
# ---- build harness tren jar v11d (ban sao nguon da patch cua parity_v11; KHONG chay patch_harness tu v11_settle)
rm -rf $B && mkdir -p $B/src $B/cls $B/cls_ops $B/stubcls
cp -r $R/java/com $B/src/
javac -nowarn -encoding UTF-8 -cp $J -d $B/stubcls $R/stub/com/aerospike/client/AerospikeClient.java
javac -nowarn -encoding UTF-8 -cp $J -d $B/cls $B/src/com/binance/chuyennd/aerospike/*.java 2>&1 | grep -v 'Unsafe\|^Note\|warning' || true
# ban co hook OPS (chi dung cho lan chay co bat): goi OpsHooks giong thu tu live (onTickStart truoc read, onMarketData sau tick)
mkdir -p $B/src_ops && cp -r $B/src/com $B/src_ops/
python3 - $B/src_ops/com/binance/chuyennd/aerospike/V11FeatHarness.java <<'EOF'
import sys
p = sys.argv[1]; s = open(p).read()
a = "                for (long ts = first; ts <= last; ts += MIN) {\n                    Map<String, List<KlineObjectSimple>> s2l = win.read(ts + MIN + 6000, 1000);\n"
b = "                for (long ts = first; ts <= last; ts += MIN) {\n                    if (OPS) com.binance.chuyennd.ops.OpsHooks.onTickStart();\n                    Map<String, List<KlineObjectSimple>> s2l = win.read(ts + MIN + 6000, 1000);\n"
assert s.count(a) == 1, "anchor NEW2 loop"
s = s.replace(a, b)
a2 = "                            p.onTick(src, win.lastEndMinute(), null);\n                    if (r == null || r.features == null) continue;\n"
b2 = "                            p.onTick(src, win.lastEndMinute(), null);\n                    if (OPS) com.binance.chuyennd.ops.OpsHooks.onMarketData(s2l);\n                    if (r == null || r.features == null) continue;\n"
assert s.count(a2) == 1, "anchor onTick"
s = s.replace(a2, b2)
a3 = "    public static void main(String[] a) throws Exception {\n"
b3 = "    static final boolean OPS = \"1\".equals(System.getenv(\"HARNESS_OPS_HOOKS\"));\n\n" + a3 + "        if (OPS) com.binance.chuyennd.ops.OpsHooks.start();\n"
assert s.count(a3) == 1, "anchor main"
s = s.replace(a3, b3)
open(p, "w").write(s)
print("patched ops hooks")
EOF
javac -nowarn -encoding UTF-8 -cp $J -d $B/cls_ops $B/src_ops/com/binance/chuyennd/aerospike/*.java 2>&1 | grep -v 'Unsafe\|^Note\|warning' || true
CP_OFF=$B/stubcls:$B/cls:$J
CP_OPS=$B/stubcls:$B/cls_ops:$J
export HARNESS_MAPPER_FILE=$W/univ/mapper_u_cache1017.csv LIVE_IS_SHADOW_HOST=true LIVE_WRITE_242_ENABLED=false
OUT=$V/harness_runs; rm -rf $OUT
for S in "w1 1792155605874 1792155600000 1792198740000 cache_1791922800000_1792198740000.ser.gz" \
         "w2 1792198832747 1792198800000 1792223400000 cache_1791966000000_1792223400000.ser.gz"; do
  set -- $S
  for RUN in BT NEW2 BT_FLAGS NEW2_FLAGS; do
    M=${RUN%_FLAGS}; D=$OUT/$1/$RUN; mkdir -p $D
    cp $W/runs/r1/$1/config.properties $D/config.properties
    grep -q '103.157.218.242' $D/config.properties && { log "config con IP 242 - DUNG"; exit 2; }
    ln -s "$(readlink -f $W/runs/r1/$1/$5)" $D/$5
    EX=""; [ $M = NEW2 ] && EX="LIVE_FEAT_INPUT=snapshot"
    CP=$CP_OFF
    if [ $RUN != $M ]; then EX="$EX LIVE_KILLSW_MODE=log LIVE_HEARTBEAT=1 LIVE_PERIODIC_RESET_HOURS=0 LIVE_PROFILE=c3_shadow HARNESS_OPS_HOOKS=1"; CP=$CP_OPS; fi
    (cd $D && env HARNESS_OFFLINE=1 HARNESS_FUNDING_FILE=$W/univ/funding_le202609.csv.gz $EX strace -f --seccomp-bpf -e trace=connect -o strace.txt \
       java -Xmx6g -cp $CP com.binance.chuyennd.aerospike.V11FeatHarness $M $2 $3 $4 out_$M.csv.gz > log.txt 2>&1; echo "exit=$?" > exit.txt)
    log "$1 $RUN $(cat $D/exit.txt) connect=$(grep -c 'connect(' $D/strace.txt) toi_242=$(grep -c '103.157.218.242' $D/strace.txt) inet=$(grep 'connect(' $D/strace.txt | grep -c AF_INET) killsw_lines=$(grep -c '\[KILLSW\]' $D/log.txt) hb=$( [ -e $D/run/heartbeat ] && echo co || echo khong)"
    python3 $R/py/cmp_runs.py $W/runs/r1/$1/out_$M.csv.gz $D/out_$M.csv.gz gate $D/cmp_gate.json 2>&1 | cut -c1-420 | tee -a $V/logs/harness.log
    python3 $R/py/cmp_runs.py $W/runs/r1/$1/fund_$M.csv.gz $D/fund_$M.csv.gz fund $D/cmp_fund.json 2>&1 | cut -c1-420 | tee -a $V/logs/harness.log
    cmp -s <(zcat $W/runs/r1/$1/out_$M.csv.gz) <(zcat $D/out_$M.csv.gz) && log "  out_$M byte-identical" || log "  out_$M KHAC byte"
    cmp -s <(zcat $W/runs/r1/$1/fund_$M.csv.gz) <(zcat $D/fund_$M.csv.gz) && log "  fund_$M byte-identical" || log "  fund_$M KHAC byte"
  done
done
log HARNESS_DONE
