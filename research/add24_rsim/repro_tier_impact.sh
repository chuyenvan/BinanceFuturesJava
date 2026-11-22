#!/bin/bash
# LUOT6 muc 4: TAI LAP so lieu TIER_IMPACT (LUOT5) tu dau vao con giu trong /dev/shm/add24/b/l5 (khong can mang, khong tai lai ticker).
#  B1 l5_prep.py: cums.csv, p15.csv, market.csv tu printDone HO5 + pred_2026.bin + market26.npy (trich market.bin sim md5 0fcc44d8)
#  B2 run_dcaall.sh: Add24DcaAll (ham jar stub, bwrap) -> dca_all.csv (dung closes.csv.gz = gia sim do Add24TierAll ghi)
#  B3 l5_tier.py -> tier_impact.json; so md5 dau vao/dau ra voi ban LUOT5 (dev_results/tier_impact.json).
#  tier_hourly.csv.gz (Add24TierAll) KHONG tai lap o day (can tai lai 273 file ticker; nay Add24TierAll co chan EB24) - md5 doi chieu 51d66b3f.
set -u
B=$HOME/claude_master/w3/add24/b; S=/dev/shm/add24/b/l5
md5sum $S/tier_hourly.csv.gz $S/closes.csv.gz $S/market26.npy
/home/ubuntu/xgb-env/bin/python3 $B/l5_prep.py || exit 1
md5sum $S/cums.csv
$B/run_dcaall.sh || exit 2
md5sum $S/dca_all.csv
( cd /tmp && /home/ubuntu/xgb-env/bin/python3 $B/l5_tier.py > /dev/null 2>&1 ) || exit 3
python3 - <<'PY'
import json
a = json.load(open('/home/ubuntu/claude_master/w3/add24/b/dev_results/tier_impact.json')); b = json.load(open('/dev/shm/add24/b/l5/tier_impact.json'))
print('TIER_IMPACT tai lap', 'TRUNG' if a == b else 'KHAC')
PY
