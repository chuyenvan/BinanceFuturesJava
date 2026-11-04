#!/bin/bash
# Tao thu muc chay offline: config.properties = ban harness cu, CHI thay 5 key Aerospike bang gia tri gia (khong in config).
# argv: run_dir [real]   (real = giu config that, chi dung cho test am R0)
set -e
D=$1
SRC=$HOME/claude_master/v11_settle/harness/config.properties
mkdir -p $D
cp $SRC $D/config.properties
if [ "$2" != "real" ]; then
  sed -i -E 's/^AEROSPIKE_HOST=.*/AEROSPIKE_HOST=offline.invalid/; s/^AEROSPIKE_PORT=.*/AEROSPIKE_PORT=1/; s/^AEROSPIKE_HOST_226=.*/AEROSPIKE_HOST_226=offline.invalid/; s/^AEROSPIKE_PORT_226=.*/AEROSPIKE_PORT_226=1/; s/^AEROSPIKE_READ_CLUSTER=.*/AEROSPIKE_READ_CLUSTER=226/' $D/config.properties
  n=$(grep -cE '^(AEROSPIKE_HOST=offline.invalid|AEROSPIKE_HOST_226=offline.invalid|AEROSPIKE_READ_CLUSTER=226|AEROSPIKE_PORT=1|AEROSPIKE_PORT_226=1)$' $D/config.properties)
  [ "$n" = "5" ] || { echo "mkdir_run: thay key Aerospike that bai ($n/5)"; exit 2; }
  if grep -q '103.157.218.242' $D/config.properties; then echo "mkdir_run: con IP 242 trong config"; exit 2; fi
fi
grep -E '^AEROSPIKE_(HOST|PORT|HOST_226|PORT_226|READ_CLUSTER)=' $D/config.properties
