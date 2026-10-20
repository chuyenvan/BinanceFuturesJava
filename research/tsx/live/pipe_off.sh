#!/bin/bash
# TS_MKT_EXT live offline (a): moi thang prep(parquet->bin) -> java ew (code live) -> xoa bin
W=/home/ubuntu/claude_master/v11_tsx/off
JAR=/home/ubuntu/claude_master/v11_tsx/wt/target/binance-java-sdk-1.2.4.jar
cd $W
mkdir -p out classes
cp $JAR $W/jar_live.jar
javac -nowarn -cp $W/jar_live.jar -d classes /tmp/tsx_src_1020/TsxLiveOffline.java || { echo JAVAC_FAIL; exit 1; }
MONTHS="2025-12 2026-01 2026-02 2026-03 2026-04 2026-05 2026-06 2026-07 2026-08 2026-09 2021-12 2022-01 2022-02 2022-03 2022-04 2022-05 2022-06 2022-07 2022-08 2022-09 2022-10 2022-11 2022-12"
for M in $MONTHS; do
  if [ -f out/${M}_days64.csv ]; then echo "done $M"; continue; fi
  python3 /tmp/tsx_src_1020/tsx_prep.py $M || { echo "PREP_FAIL $M"; exit 1; }
  java -Xmx3g -cp classes:$W/jar_live.jar tsxoff.TsxLiveOffline ew bin/$M.bin syms.txt out/$M 2>&1 | grep -v DEBUG | tail -2
  [ -f out/${M}_days64.csv ] || { echo "EW_FAIL $M"; exit 1; }
  rm -f bin/$M.bin
  echo "OK $M $(date +%T)"
done
echo PIPE_OFF_DONE
