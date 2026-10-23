#!/bin/bash
# PAIRS_T1 data fetch: Kaggle private datasets (owner chuyendinh) only. No Binance REST. No 2026, no 2020s.
set -u
K=~/kaggle_venv/bin/kaggle
D=~/claude_master/pairs/data
mkdir -p $D/kline1m $D/funding $D/logs
L=$D/logs/fetch.log
echo "start $(date -Is)" >> $L
for m in 01 02 03 04 05 06 07 08 09 10 11; do
  f=kline1m-2021-$m.parquet
  if [ ! -s $D/kline1m/$f ]; then
    $K datasets download -d chuyendinh/vz-kline1m-2021 -f $f -p $D/kline1m >> $L 2>&1
    [ -f $D/kline1m/$f.zip ] && (cd $D/kline1m && unzip -o -q $f.zip && rm -f $f.zip)
  fi
  ls -la $D/kline1m/$f >> $L 2>&1
done
$K datasets download -d chuyendinh/vz-kline1m-2021 -f README.md -p $D/kline1m >> $L 2>&1
for y in 2021 2022 2023 2024 2025; do
  f=funding-$y.parquet
  if [ ! -s $D/funding/$f ]; then
    $K datasets download -d chuyendinh/vz-funding -f $f -p $D/funding >> $L 2>&1
    [ -f $D/funding/$f.zip ] && (cd $D/funding && unzip -o -q $f.zip && rm -f $f.zip)
  fi
  ls -la $D/funding/$f >> $L 2>&1
done
$K datasets download -d chuyendinh/vz-funding -f README.md -p $D/funding >> $L 2>&1
echo "done $(date -Is)" >> $L
