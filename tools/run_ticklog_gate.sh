#!/bin/bash
# CONG NGHIEM THU TICKLOG (docs/PREREG_TICKLOG.md muc 5) — hai phan byte-identity vs baseline C2b.
set -u
R=/home/ubuntu/src/BinanceFuturesJava
B=/home/ubuntu/java/devrun
df -h / | tail -1
AV=$(df -BG / | awk 'NR==2{print $4}' | tr -dc '0-9')
echo "avail=${AV}G"
if [ "$AV" -lt 6 ]; then echo "*** DUNG: dia con ${AV}G < 6G ***"; exit 9; fi
if [ -n "$(pgrep -a java || true)" ]; then echo "*** DUNG: dang co JVM chay ***"; pgrep -a java; exit 3; fi

cp -f $R/profiles/c2b.properties $R/profiles/c2b_ticklog.properties
cat >> $R/profiles/c2b_ticklog.properties <<'EOF'

# --- TICKLOG (docs/PREREG_TICKLOG.md, commit 4d80fb9) — CHI ha tang do luong, khong doi quyet dinh ---
SIM_TICKLOG=1
SIM_TICKLOG_TAG=C2b_TLON
SIM_TICKLOG_POOL=1
SIM_TICKLOG_POS_EVERY_MIN=1
EOF
echo "=== diff hai profile (phai chi la 4 dong ticklog) ==="
diff $R/profiles/c2b.properties $R/profiles/c2b_ticklog.properties

mkdir -p /home/ubuntu/tick
rm -rf /home/ubuntu/tick/C2b_TLON

echo
echo "############ GATE 1: TAT CO ############"
T0=$(date +%s)
bash $R/tools/run_c2b_dev.sh $R/profiles/c2b.properties C2b_TLOFF /home/ubuntu/wfo_ds_tloff $B/C2b 2>&1 | tail -45
T1=$(date +%s)
echo "GATE1_WALL_SEC=$((T1-T0))"
grep -a "PROFILE. days=" $B/C2b_TLOFF/logs/sim.out | tail -1

echo
echo "############ GATE 2: BAT CO ############"
T2=$(date +%s)
bash $R/tools/run_c2b_dev.sh $R/profiles/c2b_ticklog.properties C2b_TLON /home/ubuntu/wfo_ds_tlon $B/C2b 2>&1 | tail -45
T3=$(date +%s)
echo "GATE2_WALL_SEC=$((T3-T2))"
grep -a "PROFILE. days=" $B/C2b_TLON/logs/sim.out | tail -1
grep -a "TICKLOG" $B/C2b_TLON/logs/sim.out | tail -5

echo
echo "=== DUNG LUONG THAT ==="
du -sh /home/ubuntu/tick/C2b_TLON
ls -la /home/ubuntu/tick/C2b_TLON
cat /home/ubuntu/tick/C2b_TLON/meta.txt
echo
echo "=== equity ba run ==="
for T in C2b C2b_TLOFF C2b_TLON; do
  printf "%-12s " $T; grep -a 'done:' $B/$T/logs/sim.out | tail -1 | grep -oE 'b:[0-9-]+|done:[0-9/]+' | tr '\n' ' '; echo
done
echo "=== md5 printDone ==="
md5sum $B/C2b/storage/printDone.csv $B/C2b_TLOFF/storage/printDone.csv $B/C2b_TLON/storage/printDone.csv
echo "=== cmp truc tiep (bo header) ==="
cmp -s <(tail -n +2 $B/C2b_TLOFF/storage/printDone.csv) <(tail -n +2 $B/C2b/storage/printDone.csv) && echo "GATE1=PASS" || echo "GATE1=FAIL"
cmp -s <(tail -n +2 $B/C2b_TLON/storage/printDone.csv) <(tail -n +2 $B/C2b/storage/printDone.csv) && echo "GATE2=PASS" || echo "GATE2=FAIL"
df -h / | tail -1
pgrep -a java || echo "khong con JVM"
echo TL_GATE_DONE
