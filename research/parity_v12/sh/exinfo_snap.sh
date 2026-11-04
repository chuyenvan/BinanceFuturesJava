#!/bin/bash
# exinfo_snap.sh — PARITY_V12_DRY §2.2/§8: chup c3live_exchangeInfo.json(.lastgood,.meta) cua dry 242 (CHI DOC) ve Oracle, ten theo serverTime + sha256.
set -euo pipefail
O=$HOME/claude_master/parity_v12w/exinfo; mkdir -p $O
T=$(mktemp -d)
ssh -p 2222 -o BatchMode=yes -o ConnectTimeout=20 -i /home/ubuntu/.ssh/id_rsa_chuyennd root@103.157.218.242 \
  'cd /home/chuyennd/java/v_t_m/run && tar cf - c3live_exchangeInfo.json.lastgood c3live_exchangeInfo.json.meta c3live_exinfo_refresh.state' < /dev/null | tar xf - -C $T
F=$T/c3live_exchangeInfo.json.lastgood
ST=$(python3 -c "import json,sys;print(json.load(open('$F'))['serverTime'])")
SH=$(sha256sum $F | cut -c1-64)
N=$O/exinfo_${ST}_${SH:0:12}.json
[ -f $N.gz ] || { gzip -c $F > $N.gz; cp $T/c3live_exchangeInfo.json.meta $N.meta; cp $T/c3live_exinfo_refresh.state $N.state; }
echo "$(date -u +%FT%TZ) serverTime=$ST sha256=$SH -> $(basename $N).gz" | tee -a $O/index.log
rm -rf $T
