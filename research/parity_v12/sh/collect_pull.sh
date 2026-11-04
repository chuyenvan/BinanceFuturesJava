#!/bin/bash
# collect_pull.sh D — keo log collectData (CHI DOC 242, grep|gzip qua ssh pipe) cho ngay UTC D (+07 D 07:00 -> D+1 07:00):
# lay dong co ngay +07 = D hoac D+1 tu full.log + full.log.1 (+ archived *.gz) roi cham bang py/collect_eval.py.
set -euo pipefail
D=$1
W=$HOME/claude_master/parity_v12w; R=$HOME/claude_master/vz_e1_wt/research/parity_v12
mkdir -p $W/collect
P1=$(date -d "$D" +%d/%m/%Y); P2=$(date -d "$D +1 day" +%d/%m/%Y)
ssh -p 2222 -o BatchMode=yes -o ConnectTimeout=20 -i /home/ubuntu/.ssh/id_rsa_chuyennd root@103.157.218.242 \
  "cd /home/chuyennd/java/collectData/logs && { cat full.log.1 full.log 2>/dev/null; zcat archived/*.gz 2>/dev/null; } | grep -a -E '^($P1|$P2) '" < /dev/null \
  | sort -s -k1,2 | uniq | gzip > $W/collect/collect_$D.log.gz.tmp
mv $W/collect/collect_$D.log.gz.tmp $W/collect/collect_$D.log.gz
python3 $R/py/collect_eval.py $D | grep -E '"(n_lines|covers_day|restart_too_many|mainclass|collectData_restart_le2|http429_max|price_age_warn)"'
