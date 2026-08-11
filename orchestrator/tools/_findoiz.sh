#!/bin/bash
for f in $(find /home/ubuntu /tmp -type f -iname '*.csv.gz' 2>/dev/null); do
  h=$(zcat "$f" 2>/dev/null | head -1)
  case "$h" in
    *oi_z*) echo "OIZ: $f  ::  $h";;
  esac
done
echo "=== kaggle CLI ==="
which kaggle && kaggle --version 2>/dev/null
echo "=== python pandas? ==="
python3 -c 'import pandas,sys; sys.stdout.write("pandas "+pandas.__version__+"\n")' 2>&1 | head -1
