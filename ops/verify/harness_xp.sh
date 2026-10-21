#!/bin/bash
# [EXEC-PROBE] legacy-equivalence OFFLINE tren jar exec-probe: harness parity_v11 (HARNESS_OFFLINE=1, stub Aerospike,
# strace connect), KHONG dung harness goc tro 242. 3 luot / cua so (w1, w2):
#   NEW2  : co 0, khong lai so            -> out/fund phai byte-identical voi eea5adec (parity_v11w/runs/r1)
#   XP0   : co 0 + HARNESS_XP_BOOK=1 (lai ShadowBookC3 bang luat tat dinh, goi hook nhu live)
#   XP1   : nhu XP0 + LIVE_EXEC_PROBE=1 EXEC_PROBE_SOURCE=mock (websocket MOCK, khong mang)
#   => out/fund cua ca 3 == r1 ; ledger.csv/open_positions.csv XP1 == XP0 byte ; XP1 co dong [EXEC-PROBE].
# KHONG doc/ghi 242. Log: $X/logs/harness_xp.log
set -u
X=$HOME/claude_master/exec_probe
log(){ echo "$(date '+%F %T') $*" | tee -a $X/logs/harness_xp.log >&2; }
R=$HOME/claude_master/vz_e1_wt/research/parity_v11
W=$HOME/claude_master/parity_v11w
WT=$X/wt
J=$(ls $X/jar/binance-java-sdk-1.2.4.jar_xp_*)
B=$X/parity_build
mkdir -p $X/logs; : > $X/logs/harness_xp.log
log "jar=$J md5=$(md5sum < $J | cut -c1-32)"
rm -rf $B && mkdir -p $B/src $B/cls $B/stubcls
cp -r $R/java/com $B/src/
cp $WT/ops/verify/harness_xp/HarnessXp.java $B/src/com/binance/chuyennd/aerospike/
python3 - $B/src/com/binance/chuyennd/aerospike/V11FeatHarness.java <<'EOF' || exit 2
import sys
p = sys.argv[1]; s = open(p).read()
a = "                    fund(ts, fin.keySet(), fin, r.snapshot, r.featRate, true);\n"
assert s.count(a) == 1, "anchor fund NEW2 %d" % s.count(a)
s = s.replace(a, a + "                    if (HarnessXp.XP) HarnessXp.step(ts, fin);\n")
a2 = "        FW.close();\n"
assert s.count(a2) == 1, "anchor FW.close %d" % s.count(a2)
s = s.replace(a2, "        if (HarnessXp.XP) HarnessXp.finish();\n" + a2)
open(p, "w").write(s)
print("patched harness: 2 cho (step sau fund NEW2, finish truoc FW.close)")
EOF
javac -nowarn -encoding UTF-8 -cp $J -d $B/stubcls $R/stub/com/aerospike/client/AerospikeClient.java
javac -nowarn -encoding UTF-8 -cp $J -d $B/cls $B/src/com/binance/chuyennd/aerospike/*.java 2>&1 | grep -v 'Unsafe\|^Note\|warning' || true
ls $B/cls/com/binance/chuyennd/aerospike/HarnessXp.class > /dev/null || { log "build harness THAT BAI"; exit 2; }
CP=$B/stubcls:$B/cls:$J
export HARNESS_MAPPER_FILE=$W/univ/mapper_u_cache1017.csv LIVE_IS_SHADOW_HOST=true LIVE_WRITE_242_ENABLED=false
OUT=$X/harness_runs; rm -rf $OUT
for S in "w1 1792155605874 1792155600000 1792198740000 cache_1791922800000_1792198740000.ser.gz" \
         "w2 1792198832747 1792198800000 1792223400000 cache_1791966000000_1792223400000.ser.gz"; do
  set -- $S
  for RUN in NEW2 XP0 XP1; do
    M=NEW2; D=$OUT/$1/$RUN; mkdir -p $D
    cp $W/runs/r1/$1/config.properties $D/config.properties
    grep -q '103.157.218.242' $D/config.properties && { log "config con IP 242 - DUNG"; exit 2; }
    ln -s "$(readlink -f $W/runs/r1/$1/$5)" $D/$5
    EX="LIVE_FEAT_INPUT=snapshot SHADOW_C3_DIR=$D"
    [ $RUN = XP0 ] && EX="$EX HARNESS_XP_BOOK=1 LIVE_EXEC_PROBE=0"
    [ $RUN = XP1 ] && EX="$EX HARNESS_XP_BOOK=1 LIVE_EXEC_PROBE=1 EXEC_PROBE_SOURCE=mock EXEC_PROBE_BATCH_MS=0"
    (cd $D && env HARNESS_OFFLINE=1 HARNESS_FUNDING_FILE=$W/univ/funding_le202609.csv.gz $EX strace -f --seccomp-bpf -e trace=connect -o strace.txt \
       /usr/bin/time -v java -Xmx6g -cp $CP com.binance.chuyennd.aerospike.V11FeatHarness $M $2 $3 $4 out_$M.csv.gz > log.txt 2> time.txt; echo "exit=$?" > exit.txt)
    log "$1 $RUN $(cat $D/exit.txt) connect=$(grep -c 'connect(' $D/strace.txt) toi_242=$(grep -c '103.157.218.242' $D/strace.txt) inet=$(grep 'connect(' $D/strace.txt | grep -c AF_INET) xp_lines=$(grep -a -c '\[EXEC-PROBE\] 1,' $D/log.txt) xp_hdr=$(grep -a -c '#hdr' $D/log.txt) maxrss_kb=$(grep 'Maximum resident' $D/time.txt | awk '{print $NF}') cpu_s=$(grep -E 'User time|System time' $D/time.txt | awk '{s+=$NF} END {print s}')"
    grep -a 'HARNESS-XP\]\|EXEC-PROBE\] BAT\|EXEC_PROBE_SOURCE=mock' $D/log.txt | cut -c1-330 | head -3 | tee -a $X/logs/harness_xp.log >&2
    python3 $R/py/cmp_runs.py $W/runs/r1/$1/out_$M.csv.gz $D/out_$M.csv.gz gate $D/cmp_gate.json 2>&1 | cut -c1-300 | tee -a $X/logs/harness_xp.log
    python3 $R/py/cmp_runs.py $W/runs/r1/$1/fund_$M.csv.gz $D/fund_$M.csv.gz fund $D/cmp_fund.json 2>&1 | cut -c1-300 | tee -a $X/logs/harness_xp.log
    cmp -s <(zcat $W/runs/r1/$1/out_$M.csv.gz) <(zcat $D/out_$M.csv.gz) && log "  out_$M byte-identical vs r1" || log "  out_$M KHAC byte vs r1"
    cmp -s <(zcat $W/runs/r1/$1/fund_$M.csv.gz) <(zcat $D/fund_$M.csv.gz) && log "  fund_$M byte-identical vs r1" || log "  fund_$M KHAC byte vs r1"
    if [ $RUN != NEW2 ]; then
      log "  ledger_rows=$(($(wc -l < $D/ledger.csv)-1)) md5_ledger=$(md5sum < $D/ledger.csv | cut -c1-12) md5_state=$(md5sum < $D/open_positions.csv | cut -c1-12)"
      grep -a '\[EXEC-PROBE\] 1,' $D/log.txt | sed 's/^.*\[EXEC-PROBE\] //' > $D/xp.csv
    fi
  done
  for f in ledger.csv open_positions.csv; do
    cmp -s $OUT/$1/XP0/$f $OUT/$1/XP1/$f && log "  $1 $f XP1 == XP0 byte-identical" || log "  $1 $f XP1 KHAC XP0"
  done
  python3 - $OUT/$1/XP1/xp.csv $OUT/$1/XP1/ledger.csv <<'EOF' 2>&1 | tee -a $X/logs/harness_xp.log
import sys, collections
rows = [l.rstrip("\n").split(",") for l in open(sys.argv[1])]
led = sum(1 for _ in open(sys.argv[2])) - 1
c = collections.Counter((r[1], r[-2]) for r in rows)
print("  xp rows=%d ledger_exits=%d by(ev,status)=%s" % (len(rows), led, dict(sorted(c.items()))))
EOF
done
log HARNESS_XP_DONE
