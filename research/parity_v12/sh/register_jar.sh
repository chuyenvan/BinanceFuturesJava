#!/bin/bash
# [ADD11 §2] dang ky jar dry moi cho harness parity + build harness tren jar do.
# dung: bash register_jar.sh <ten> <duong_dan_jar> <md5_32> <start_JVM_ms> <premarket_excl 0|1>
# start_JVM_ms = moc MainClass khoi dong jar moi tren 242 (ms UTC). Chi doc/ghi tren Oracle; khong cham 242.
set -eu
export LIVE_IS_SHADOW_HOST=true
N=$1; J=$2; M=$3; S=$4; P=$5
R=$HOME/claude_master/vz_e1_wt/research/parity_v12
W=$HOME/claude_master/parity_v12w
echo "$M  $J" | md5sum -c -
python3 - "$N" "$M" "$S" "$P" "$J" <<'EOF'
import json, os, sys
n, m, s, p, j = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4] == "1", sys.argv[5]
f = os.path.expanduser("~/claude_master/parity_v12w/jars.json")
J = json.load(open(f)) if os.path.exists(f) else []
assert n != "r4n" and all(x["name"] != n for x in J), "ten da co"
MIN = 60000
tick = -(-(s - 66000) // MIN) * MIN        # tick quyet dinh dau tien cua process moi (nhu day_prep segs)
J.append({"name": n, "jar": j, "md5": m, "start_ms": s, "t0_tick": tick, "premarket_excl": p})
json.dump(J, open(f, "w"), indent=1)
print("jars.json:", J)
EOF
mkdir -p ~/claude_master/locks
flock -w 3600 ~/claude_master/locks/oracle_heavy.lock nice -n 10 env JAR=$J JAR_MD5=$M B=$W/build_$N bash $R/sh/build.sh | tail -2
