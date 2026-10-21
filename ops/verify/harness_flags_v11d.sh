#!/bin/bash
# v11d: chay lai 2 lan "co bat" (LIVE_KILLSW_MODE=log LIVE_HEARTBEAT=1 LIVE_PERIODIC_RESET_HOURS=0) voi harness CO goi
# OpsHooks (onTickStart truoc read, onMarketData sau tick — thu tu nhu live), so voi eea5adec (parity_v11w/runs/r1). OFFLINE.
set -u
log(){ echo "$(date '+%F %T') $*" | tee -a $V/logs/harness_flags.log >&2; }
V=$HOME/claude_master/v11d
R=$HOME/claude_master/vz_e1_wt/research/parity_v11
W=$HOME/claude_master/parity_v11w
J=$(ls $V/jar/binance-java-sdk-1.2.4.jar_v11d_*)
B=$V/parity_build
: > $V/logs/harness_flags.log
rm -rf $B/src_ops $B/cls_ops && mkdir -p $B/src_ops $B/cls_ops && cp -r $B/src/com $B/src_ops/
python3 - $B/src_ops/com/binance/chuyennd/aerospike/V11FeatHarness.java <<'EOF' || exit 2
import sys
p = sys.argv[1]; s = open(p).read()
a = ("                    Map<String, List<KlineObjectSimple>> s2l = win.read(ts + MIN + 6000, 1000);\n"
     "                    com.binance.chuyennd.ai_ml.features.export.entry.LiveFeaturePipeline.Result r =\n"
     "                            p.onTick(src, win.lastEndMinute(), null);\n")
assert s.count(a) == 1, "anchor NEW2 %d" % s.count(a)
s = s.replace(a, "                    if (OPS) com.binance.chuyennd.ops.OpsHooks.onTickStart();\n" + a
              + "                    if (OPS) com.binance.chuyennd.ops.OpsHooks.onMarketData(s2l);\n")
a3 = "    public static void main(String[] a) throws Exception {\n"
assert s.count(a3) == 1, "anchor main"
s = s.replace(a3, "    static final boolean OPS = \"1\".equals(System.getenv(\"HARNESS_OPS_HOOKS\"));\n\n" + a3
              + "        if (OPS) com.binance.chuyennd.ops.OpsHooks.start();\n")
open(p, "w").write(s)
print("patched ops hooks: 3 cho")
EOF
javac -nowarn -encoding UTF-8 -cp $J -d $B/cls_ops $B/src_ops/com/binance/chuyennd/aerospike/*.java 2>&1 | grep -v 'Unsafe\|^Note\|warning' || true
grep -c "OpsHooks" $B/src_ops/com/binance/chuyennd/aerospike/V11FeatHarness.java | xargs -I{} echo "OpsHooks call sites in harness: {}" >&2
CP_OPS=$B/stubcls:$B/cls_ops:$J
export HARNESS_MAPPER_FILE=$W/univ/mapper_u_cache1017.csv LIVE_IS_SHADOW_HOST=true LIVE_WRITE_242_ENABLED=false
OUT=$V/harness_runs
for S in "w1 1792155605874 1792155600000 1792198740000 cache_1791922800000_1792198740000.ser.gz" \
         "w2 1792198832747 1792198800000 1792223400000 cache_1791966000000_1792223400000.ser.gz"; do
  set -- $S
  M=NEW2; D=$OUT/$1/NEW2_FLAGS; rm -rf $D; mkdir -p $D
  cp $W/runs/r1/$1/config.properties $D/config.properties
  grep -q '103.157.218.242' $D/config.properties && { log "config con IP 242 - DUNG"; exit 2; }
  ln -s "$(readlink -f $W/runs/r1/$1/$5)" $D/$5
  (cd $D && env HARNESS_OFFLINE=1 HARNESS_FUNDING_FILE=$W/univ/funding_le202609.csv.gz LIVE_FEAT_INPUT=snapshot \
     LIVE_KILLSW_MODE=log LIVE_HEARTBEAT=1 LIVE_PERIODIC_RESET_HOURS=0 HARNESS_OPS_HOOKS=1 \
     strace -f --seccomp-bpf -e trace=connect -o strace.txt \
     java -Xmx6g -cp $CP_OPS com.binance.chuyennd.aerospike.V11FeatHarness $M $2 $3 $4 out_$M.csv.gz > log.txt 2>&1; echo "exit=$?" > exit.txt)
  log "$1 NEW2_FLAGS $(cat $D/exit.txt) connect=$(grep -c 'connect(' $D/strace.txt) toi_242=$(grep -c '103.157.218.242' $D/strace.txt) inet=$(grep 'connect(' $D/strace.txt | grep -c AF_INET) ops_line=$(grep -c '\[OPS\] v11d' $D/log.txt) killsw_BAT=$(grep -c '\[KILLSW\] BAT' $D/log.txt) would=$(grep -c 'WOULD_TRIGGER' $D/log.txt) hb=$( [ -e $D/run/heartbeat ] && stat -c '%s_bytes_mtime=%y' $D/run/heartbeat || echo khong)"
  grep -a '\[OPS\] v11d\|\[KILLSW\] BAT\|\[HEARTBEAT\] BAT' $D/log.txt | cut -c1-330 | head -3 | tee -a $V/logs/harness_flags.log >&2
  grep -a 'WOULD_TRIGGER' $D/log.txt | awk '{for(i=1;i<=NF;i++) if($i ~ /^code=/) print $i}' | sort | uniq -c | tee -a $V/logs/harness_flags.log >&2
  grep -a 'WOULD_TRIGGER' $D/log.txt | head -2 | cut -c1-330 | tee -a $V/logs/harness_flags.log >&2
  python3 $R/py/cmp_runs.py $W/runs/r1/$1/out_$M.csv.gz $D/out_$M.csv.gz gate $D/cmp_gate.json 2>&1 | cut -c1-420 | tee -a $V/logs/harness_flags.log
  python3 $R/py/cmp_runs.py $W/runs/r1/$1/fund_$M.csv.gz $D/fund_$M.csv.gz fund $D/cmp_fund.json 2>&1 | cut -c1-420 | tee -a $V/logs/harness_flags.log
  cmp -s <(zcat $W/runs/r1/$1/out_$M.csv.gz) <(zcat $D/out_$M.csv.gz) && log "  out_$M byte-identical" || log "  out_$M KHAC byte"
  cmp -s <(zcat $W/runs/r1/$1/fund_$M.csv.gz) <(zcat $D/fund_$M.csv.gz) && log "  fund_$M byte-identical" || log "  fund_$M KHAC byte"
done
log HARNESS_FLAGS_DONE
