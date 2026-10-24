#!/bin/bash
# ADDENDUM1 (PARITY_V11_WINDOW D1): giai ma 7 file predictionSymbol 10-22 00:00-00:06 (+07) da co tren Oracle
# (live/psym, keo tu 242 ngay 10-23, chi doc) nhung bi bo sot khi dung feat45_live_b.csv.gz (bat dau 00:07).
# Dung Pa1020Feat (= FundingOnnxInferenceManager.extractFeaturesToArray cua jar v11c), stub Aerospike dung truoc.
# Kiem: giai ma lai 1792602420000 (00:07, da co trong feat45_live_b) phai trung bit tung dong.
set -euo pipefail
W=~/claude_master/parity_v11w
JAR=/home/ubuntu/claude_master/v11_tsx/jar/binance-java-sdk-1.2.4.jar_v11c_eea5adec
CP=$W/build/stubcls:$W/build/clspa:$JAR
FILES=""
for ts in 1792602000000 1792602060000 1792602120000 1792602180000 1792602240000 1792602300000 1792602360000; do
  FILES="$FILES $W/live/psym/$ts.features"
done
ls -la --time-style=full-iso $FILES
java -cp $CP Pa1020Feat $W/live/feat45_live_c.csv.gz $FILES
java -cp $CP Pa1020Feat $W/live/_chk_0007.csv.gz $W/live/psym/1792602420000.features
python3 - <<'EOF'
import gzip
W='/home/ubuntu/claude_master/parity_v11w/live'
a=[l for l in gzip.open(W+'/_chk_0007.csv.gz','rt').read().splitlines()[1:]]
b=[l for l in gzip.open(W+'/feat45_live_b.csv.gz','rt',errors='ignore').read().splitlines() if l.startswith('1792602420000,')]
print('chk 00:07 rows new',len(a),'old',len(b),'identical',sorted(a)==sorted(b))
c=gzip.open(W+'/feat45_live_c.csv.gz','rt').read().splitlines()
import collections
print('c rows',len(c)-1, collections.Counter(l.split(',')[0] for l in c[1:]))
EOF
rm -f $W/live/_chk_0007.csv.gz
md5sum $W/live/feat45_live_c.csv.gz
