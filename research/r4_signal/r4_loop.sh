#!/bin/bash
# R4_SIGNAL_SCREEN vong tu cho (prereg 5db738e2 §6). DUNG: touch $G/STOP. Log: $G/loop.log. Han 16 h.
G=/home/ubuntu/claude_master/res1109/r4_signal/screen
C=/home/ubuntu/claude_master/vz_e1_wt/research/r4_signal
R=/home/ubuntu/claude_master/vz_e1_wt
LK=/home/ubuntu/claude_master/locks/oracle_heavy.lock
log() { echo "$(date '+%F %T') $*" >> $G/loop.log; }
dead=$(( $(date +%s) + 16*3600 ))
chk() { [ -f $G/STOP ] && { log "STOP file -> dung"; exit 0; }; [ $(date +%s) -gt $dead ] && { log "het han 16h -> dung"; exit 1; }; }
echo $$ > $G/loop.pid
log "start pid $$"
# 1) cho buoc dem
while [ ! -f $G/r4s_cells.parquet ]; do
  chk
  if ! pgrep -f '[r]4_count.py' > /dev/null; then sleep 5; [ -f $G/r4s_cells.parquet ] || { log "r4_count ket thuc KHONG co r4s_cells -> dung (xem count.log)"; exit 1; }; fi
  sleep 60
done
log "dem xong: $(python3 -c "import json;d=json.load(open('$G/count.json'));print({a:(v['ratio'],v['LOAI']) for a,v in d['arms'].items()})")"
ALL=$(python3 -c "import json;d=json.load(open('$G/count.json'));print(int(all(v['LOAI'] for v in d['arms'].values())))")
if [ "$ALL" = 1 ]; then log "ca 3 LOAI o iso/quota -> khong can kernel"; exit 0; fi
# 2) push kernel (thu lai neu Kaggle ban)
until [ -f $G/pushed ]; do
  chk
  python3 $C/r4_push.py push >> $G/loop.log 2>&1 || log "push chua duoc (rc $?) -> doi 10'"
  [ -f $G/pushed ] || sleep 600
done
# 3) cho kernel
while true; do
  chk
  st=$(python3 $C/r4_push.py status 2>&1 | grep -o 'STATUS.*' | tail -1)
  log "$st"
  case "$st" in
    *omplete*) break ;;
    *rror*|*ancel*) log "kernel loi -> dung"; exit 1 ;;
  esac
  sleep 600
done
python3 $C/r4_push.py fetch >> $G/loop.log 2>&1
[ -f $G/out/r4s_fwd.parquet ] || { log "fetch khong co r4s_fwd.parquet -> dung"; exit 1; }
# 4) cham + commit
flock -w 3600 $LK nice -n 10 python3 $C/r4_score.py >> $G/score.log 2>&1 || { log "score loi (xem score.log)"; exit 1; }
mkdir -p $R/docs/result/r4_signal
cp -f $G/count.json $G/r4_screen.json $R/docs/result/r4_signal/
cd $R && git add docs/result/R4_SIGNAL_SCREEN.md docs/result/r4_signal/count.json docs/result/r4_signal/r4_screen.json research/r4_signal/*.py research/r4_signal/*.sh \
  && git commit -q -m "result(R4_SIGNAL_SCREEN, prereg 5db738e2): sang C1/C2/C3 - xem docs/result/R4_SIGNAL_SCREEN.md" && log "COMMIT $(git --no-pager log --oneline -1)"
log "XONG"
