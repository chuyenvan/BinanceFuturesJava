#!/bin/bash
# R5_SIGNAL_QUALITY vong tu cho (prereg 200a29a3 §7). DUNG: touch $G/STOP. Log $G/loop.log. Han 16 h.
# Thu tu: tin hieu -> kernel -> kham pha -> COMMIT lua chon -> xac nhan -> COMMIT.
G=/home/ubuntu/claude_master/res1109/r5_quality
C=/home/ubuntu/claude_master/vz_e1_wt/research/r5_quality
R=/home/ubuntu/claude_master/vz_e1_wt
LK=/home/ubuntu/claude_master/locks/oracle_heavy.lock
log() { echo "$(date '+%F %T') $*" >> $G/loop.log; }
dead=$(( $(date +%s) + 16*3600 ))
chk() { [ -f $G/STOP ] && { log "STOP -> dung"; exit 0; }; [ $(date +%s) -gt $dead ] && { log "het han 16h"; exit 1; }; }
echo $$ > $G/loop.pid
log "start pid $$"
if [ ! -f $G/sig_meta.json ]; then
  flock -w 3600 $LK nice -n 10 python3 $C/r5_signal.py > $G/signal.log 2>&1 || { log "r5_signal loi (signal.log)"; exit 1; }
fi
log "tin hieu xong: $(tail -1 $G/signal.log | cut -c1-200)"
until [ -f $G/pushed ]; do
  chk
  python3 $C/r5_push.py push >> $G/loop.log 2>&1 || log "push chua duoc (rc $?)"
  [ -f $G/pushed ] || sleep 600
done
while true; do
  chk
  st=$(python3 $C/r5_push.py status 2>&1 | grep -o 'STATUS.*' | tail -1)
  log "$st"
  case "$st" in
    *omplete*) break ;;
    *rror*|*ancel*) log "kernel loi -> dung"; exit 1 ;;
  esac
  sleep 300
done
python3 $C/r5_push.py fetch >> $G/loop.log 2>&1
[ -f $G/out/r5q_y.parquet ] || { log "khong co r5q_y.parquet"; exit 1; }
flock -w 3600 $LK nice -n 10 python3 $C/r5_score.py discover > $G/discover.log 2>&1 || { log "discover loi"; exit 1; }
mkdir -p $R/docs/result/r5_quality
cp -f $G/selection.json $G/discover.json $G/sig_meta.json $G/out/r5q_meta.json $R/docs/result/r5_quality/
cd $R && git add docs/result/R5_SIGNAL_QUALITY_DISCOVER.md docs/result/r5_quality/ research/r5_quality/ \
  && git commit -q -m "result(R5_SIGNAL_QUALITY kham pha 2022-23, prereg 200a29a3): lua chon top-2 $(python3 -c "import json;print(json.load(open('$G/selection.json'))['selected'])") - commit TRUOC xac nhan" \
  && log "COMMIT kham pha $(git --no-pager log --oneline -1 | cut -c1-12)" || { log "commit kham pha loi -> dung"; exit 1; }
NSEL=$(python3 -c "import json;print(len(json.load(open('$G/selection.json'))['selected']))")
if [ "$NSEL" = 0 ]; then log "khong bien the nao > RAW -> DONG, khong xac nhan"; log XONG; exit 0; fi
chk
flock -w 3600 $LK nice -n 10 python3 $C/r5_score.py confirm > $G/confirm.log 2>&1 || { log "confirm loi"; exit 1; }
cp -f $G/confirm.json $R/docs/result/r5_quality/
cd $R && git add docs/result/R5_SIGNAL_QUALITY_CONFIRM.md docs/result/r5_quality/confirm.json \
  && git commit -q -m "result(R5_SIGNAL_QUALITY xac nhan 2024-25, prereg 200a29a3)" && log "COMMIT xac nhan $(git --no-pager log --oneline -1 | cut -c1-12)"
log XONG
