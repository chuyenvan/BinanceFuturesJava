#!/bin/bash
# Tai dung file can (Kaggle, chi doc) vao thu muc rieng, kiem md5.
set -u; export PATH=$HOME/.local/bin:$PATH
D=/home/ubuntu/claude_master/audit_1021/kg
mkdir -p $D/gate-dataset-full $D/funding-gate-wfo-pred $D/wfo-gate-pred-1m $D/wfo-ds-dev-002
cd $D
kaggle datasets download chuyendinh/gate-dataset-full -p $D/gate-dataset-full -q > dl1.log 2>&1
kaggle datasets download chuyendinh/funding-gate-wfo-pred -p $D/funding-gate-wfo-pred -q > dl2.log 2>&1
kaggle datasets download chuyendinh/wfo-gate-pred-1m -p $D/wfo-gate-pred-1m -q > dl3.log 2>&1
kaggle datasets download chuyendinh/wfo-ds-dev-002 -f market.bin -p $D/wfo-ds-dev-002 -q > dl4.log 2>&1
kaggle datasets download chuyendinh/wfo-ds-dev-002 -f manifest.txt -p $D/wfo-ds-dev-002 -q >> dl4.log 2>&1
for z in $(find $D -name '*.zip'); do (cd $(dirname $z) && unzip -o -q $(basename $z) && rm -f $(basename $z)); done
find $D -type f ! -name '*.log' -exec md5sum {} \; > $D/md5.txt
find $D -type f ! -name '*.log' -exec ls -la {} \; >> $D/md5.txt
echo DLDONE >> $D/md5.txt
