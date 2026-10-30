#!/usr/bin/env bash
# test_pause_trap.sh — [QF3, A1_QF2 MAJ-B] test shell cho PAUSE token / trap / DRY=1. Chay LOCAL tren Oracle trong sandbox,
# KHONG cham 242 (ssh/scp duoc thay bang stub hoac bash local; process "ingestor" la sleep gia ten rieng).
#   bash test_pause_trap.sh <dir chua ingqf_restart_remote.sh> <deploy_ingest_qf.sh da dien>
set -u
R=$1; DEP=$2
T=$(mktemp -d /tmp/ingqf_pause_test_XXXX)
PASS=0; FAILN=0
ok() { echo "PASS $*"; PASS=$((PASS+1)); }
ko() { echo "FAIL $*"; FAILN=$((FAILN+1)); }
PAT="ingqf_test_fake_ingestor_$$"
mkdir -p $T/app/bin $T/wd
cat > $T/app/bin/daemon.sh <<EOF
#!/bin/bash
case \$1 in
  start) (setsid nohup bash -c "exec -a $PAT sleep 600" > /dev/null 2>&1 < /dev/null &) ;;
  stop) pkill -f "^$PAT" ;;
esac
EOF
chmod +x $T/app/bin/daemon.sh
export INGQF_PAUSE_FILE=$T/wd/PAUSE INGQF_TMPD=$T INGQF_PROC_PAT="^$PAT" INGQF_SEC_FROM=0 INGQF_SEC_TO=59 INGQF_POST_START_SLEEP=2
start_fake() { $T/app/bin/daemon.sh start; sleep 1; pgrep -f "^$PAT" | head -1; }

# ---- Ca 1: PAUSE cua NGUOI KHAC co san => restart tu choi, KHONG go, KHONG dung toi process
P0=$(start_fake)
echo "deploy_v12_dry_r4 owner=nguoi_khac" > $INGQF_PAUSE_FILE
OUT=$(bash -s -- $T/app tokA < $R/ingqf_restart_remote.sh 2>&1)
grep -q 'PAUSE_cua_nguoi_khac' <<<"$OUT" && ok "ca1 tu choi khi PAUSE nguoi khac" || ko "ca1 khong tu choi: $OUT"
[ "$(cat $INGQF_PAUSE_FILE)" = "deploy_v12_dry_r4 owner=nguoi_khac" ] && ok "ca1 PAUSE nguoi khac con nguyen" || ko "ca1 PAUSE bi doi/xoa"
[ "$(pgrep -f "^$PAT" | head -1)" = "$P0" ] && ok "ca1 process khong bi dung toi" || ko "ca1 process bi restart"
# trap phia Oracle cua deploy (own_pause_cleanup) voi PAUSE nguoi khac: khong go
TOKEN=tokA; PF=$INGQF_PAUSE_FILE; S="bash -c"
bash -c "f=$PF; c=\$(cat \$f 2>/dev/null); { [ \"\$c\" = '$TOKEN' ] || [ \"\$c\" = '${TOKEN}_rb' ]; } && rm -f \$f || true"
[ -f $INGQF_PAUSE_FILE ] && ok "ca1 cleanup phia Oracle khong go PAUSE nguoi khac" || ko "ca1 cleanup go nham"
rm -f $INGQF_PAUSE_FILE

# ---- Ca 2: DRY=1 => chi doc: dung 1 lan ssh (kiem truoc), stdin khong co lenh ghi, khong scp, khong trap cleanup
cat > $T/stub_ssh.sh <<EOF
#!/bin/bash
echo "ARGS: \$*" >> $T/ssh.log; echo "---STDIN---" >> $T/ssh.log; cat >> $T/ssh.log; echo "---END---" >> $T/ssh.log
EOF
cat > $T/stub_scp.sh <<EOF
#!/bin/bash
echo "SCP: \$*" >> $T/scp.log
EOF
chmod +x $T/stub_ssh.sh $T/stub_scp.sh
: > $T/ssh.log
INGQF_SSH=$T/stub_ssh.sh INGQF_SCP=$T/stub_scp.sh DRY=1 bash $DEP > $T/dry.out 2>&1; RC=$?
[ $RC = 0 ] && ok "ca2 DRY rc=0" || ko "ca2 DRY rc=$RC: $(tail -3 $T/dry.out)"
N=$(grep -c '^ARGS:' $T/ssh.log)
[ "$N" = 1 ] && ok "ca2 DRY dung 1 lan ssh (kiem chi doc)" || ko "ca2 DRY ssh $N lan: $(grep '^ARGS' $T/ssh.log)"
grep -E -q 'rm -f|touch |mv -f|cp -f|> *conf|PAUSE_cua_minh' $T/ssh.log && ko "ca2 DRY co lenh ghi: $(grep -E 'rm -f|touch |mv -f|cp -f' $T/ssh.log | head -2)" || ok "ca2 DRY khong co lenh ghi nao"
[ -f $T/scp.log ] && ko "ca2 DRY co scp" || ok "ca2 DRY khong scp"

# ---- Ca 3: ssh rot giua chung (giet phien ngoai) => than restart van chay xong, go DUNG PAUSE cua minh, process moi len
P1=$(pgrep -f "^$PAT" | head -1)
rm -f $T/ingqf_restart_*.log
( bash -s -- $T/app tokB < $R/ingqf_restart_remote.sh > $T/ca3.out 2>&1 ) &
OUTER=$!
sleep 1
[ "$(cat $INGQF_PAUSE_FILE 2>/dev/null)" = "tokB" ] && ok "ca3 PAUSE mang token cua minh" || ko "ca3 PAUSE khong co token (=$(cat $INGQF_PAUSE_FILE 2>/dev/null))"
pkill -P $OUTER 2>/dev/null; kill $OUTER 2>/dev/null   # "ssh rot"
for i in $(seq 1 30); do LOGB=$(ls $T/ingqf_restart_*.log 2>/dev/null | tail -1); grep -q '^DONE' "$LOGB" 2>/dev/null && break; sleep 1; done
grep -q '^DONE' "$LOGB" && ok "ca3 than restart chay xong sau khi ssh rot" || ko "ca3 than restart khong xong"
sleep 1
[ ! -f $INGQF_PAUSE_FILE ] && ok "ca3 PAUSE cua minh da duoc go (trap)" || ko "ca3 PAUSE con: $(cat $INGQF_PAUSE_FILE)"
P2=$(pgrep -f "^$PAT" | head -1)
[ -n "$P2" ] && [ "$P2" != "$P1" ] && ok "ca3 process moi len ($P1 -> $P2)" || ko "ca3 process ($P1 -> $P2)"

pkill -f "^$PAT"; rm -rf $T
echo "TONG: PASS=$PASS FAIL=$FAILN"
[ $FAILN = 0 ]
