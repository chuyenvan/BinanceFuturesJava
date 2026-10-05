#!/bin/bash
# chay probe READ-ONLY tren 242 tu Oracle. $1 = file script remote, $2 = file output
ssh -p 2222 -o BatchMode=yes -o ConnectTimeout=20 -i ~/.ssh/id_rsa_chuyennd root@103.157.218.242 'bash -s' < "$1" > "$2" 2>&1
echo "rc=$? lines=$(wc -l < "$2")"
