#!/bin/bash
# Chay research/parity/parity_check.py trong ban sao CACH LY (khong ghi de docs/result/parity_report.* hay data/ cua repo).
# fetch = READ-ONLY 242 (grep/wc/head). feat_dump/sel_dump LIVE = ban keo ve 2026-10-02 (live242/fd).
set -u
R=/home/ubuntu/src/BinanceFuturesJava
D=/home/ubuntu/claude_master/1002/deploy242
H=$D/harness
mkdir -p $H/research/parity/data $H/docs/result
ln -sfn $R/profiles $H/profiles
ln -sfn $R/research/analysis $H/research/analysis
cp -f $R/research/parity/parity_check.py $H/research/parity/parity_check.py
for f in p15_dev.csv marketparams_inline.csv selector_live.csv; do
  [ -e $H/research/parity/data/$f ] || ln -s $R/research/parity/data/$f $H/research/parity/data/$f; done
sed -i "s#HOME + \"/claudedata/devexport_202609/live_242/feat_dump_\*.csv.gz\"#\"$D/live242/fd/feat_dump/feat_dump_*.csv.gz\"#" $H/research/parity/parity_check.py
sed -i "s#HOME + \"/claudedata/devexport_202609/live_242/sel_dump_\*.csv.gz\"#\"$D/live242/fd/feat_dump/sel_dump_*.csv.gz\"#" $H/research/parity/parity_check.py
grep -n "live242/fd" $H/research/parity/parity_check.py | head
cd $H
python3 research/parity/parity_check.py fetch > $D/harness_fetch.txt 2>&1; echo "fetch rc=$?"
python3 research/parity/parity_check.py all > $D/harness_all.txt 2>&1; echo "all rc=$?"
grep -E '^\[(PASS|FAIL|MISSING)\]|overall|^  - \[' $D/harness_all.txt | cut -c1-260 | head -70
