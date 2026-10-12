#!/bin/bash
# BUOC 2 [Oracle, KHONG ghi 242] dung lai buffer gate (live K16, shadow#1 K16, shadow#2 K24) tu nen 242 DA backfill
# = docs/runbooks/KLINE_FIX_242.md muc C (C1 feat, C2 sp cache, C3 build+so). Chay SAU buoc 1a (backfill xong + verify 0),
# TRUOC cua so dung (buoc 3). Lau 1-2 h: setsid nohup bash d2_build_buffer.sh > $LOGD/d2.out 2>&1 &
# Noi dung KHONG phu thuoc mapper (feature gate tinh theo TEN symbol tu kline 242) — xem LIVE_DEPLOY_1011.md muc 2.
source /home/ubuntu/claude_master/1011/livefix/deploy/dep_env.sh
set -u
cd $WT || exit 1
R=research/ops/kline_gate_buffer_rebuild.py; B=research/parity/build_gate_buffer_k24.py
M=/home/ubuntu/g3x26/g015x26_f15_cut20251231.onnx       # net015 (DEPLOY_SHADOW2_K24_20261008.md §3, md5 e65e683b)
mkdir -p $G
need(){ local fr=$(df --output=avail -m / | tail -1); [ "$fr" -ge "$1" ] || { echo "DUNG: dia con ${fr}MB < $1MB ($2)"; exit 9; }; }
need 500 "truoc C1"
NOW=$(date +%Y%m%d-%H%M); echo "NOW=$NOW"
echo "== C1 feat $(date +%T)"
python3 $R feat --arm 242 --lo 20260929 --hi $(date -d tomorrow +%Y%m%d) --wd $G || exit 11
need 400 "truoc C2"
echo "== C2 sp cache $(date +%T)"
python3 $B extract --data /home/ubuntu/shadow_c3/app/storage/data  --model $M --cache $G/cache_s1 || exit 12
python3 $B extract --data /home/ubuntu/shadow_c3b/app/storage/data --model $M --cache $G/cache_s2 || exit 12
d=20261001; today=$(date +%Y%m%d)
while [ "$d" -le "$today" ]; do
  need 600 "keo storage 242 ngay $d"
  T=$G/tmp_live; rm -rf $T; mkdir -p $T/predictionSymbol $T/prediction
  $SCP242 -r root@103.157.218.242:/home/chuyennd/java/v_t_m/storage/data/predictionSymbol/$d $T/predictionSymbol/ || echo "WARN thieu predictionSymbol/$d"
  $SCP242 -r root@103.157.218.242:/home/chuyennd/java/v_t_m/storage/data/prediction/$d $T/prediction/ || echo "WARN thieu prediction/$d"
  python3 $B extract --data $T --model $M --cache $G/cache_live || exit 13
  rm -rf $T
  d=$(date -d "$d +1 day" +%Y%m%d)
done
echo "== C3 build $(date +%T)"
$SCP242 root@103.157.218.242:/home/chuyennd/java/v_t_m/run/gate_ratio_live.bin $G/live_cur.bin || exit 14
cp -p /home/ubuntu/shadow_c3/app/run/gate_ratio_live.bin $G/s1_cur.bin; cp -p /home/ubuntu/shadow_c3b/app/run/gate_ratio_live.bin $G/s2_cur.bin
F="$G/kdiv_gate_242_20260929_*.csv.gz"
python3 $R build --feat "$F" --sp cache:$G/cache_live --k 16 --now $NOW --out $G/live_new.bin --ref $G/live_cur.bin --json $G/live_new.json || exit 15
python3 $R build --feat "$F" --sp cache:$G/cache_s1   --k 16 --now $NOW --out $G/s1_new.bin   --ref $G/s1_cur.bin   --json $G/s1_new.json || exit 15
python3 $R build --feat "$F" --sp cache:$G/cache_s2   --k 24 --now $NOW --out $G/s2_new.bin   --ref $G/s2_cur.bin   --json $G/s2_new.json || exit 15
sha256sum $G/live_new.bin $G/s1_new.bin $G/s2_new.bin
python3 $DEP/d2_pass.py $G/live_new.json $G/s1_new.json $G/s2_new.json
