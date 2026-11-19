#!/usr/bin/env bash
# =============================================================================
# c3_price_lag_day.sh - [OPS5 muc 5] DO "do tre gia > 5 s" 1 NGAY tren 242 (CHI DOC, nice/ionice, 1 ssh). Chay tren Oracle.
#   bash $OPS/c3_price_lag_day.sh [YYYY-MM-DD]     (mac dinh: hom qua, gio +07)
# Nguon (khong co truong "price_gap" o log v_t_m - truong nam o log INGESTOR collectData):
#   collectData logs/full.log(.1) dong "[REST-BUDGET] ... | price_gap_max_ms=<ms> price_age_ms=<ms> price_diff=<n>" (1 dong / phut)
#   v_t_m logs/full.log(.1)      dong "[KILLSW] HOURLY ... lag_s=<s> miss=<a>/<b>" (1 dong / gio)
# Nguong (LAG_MS, mac dinh 5000): in so phut co price_gap_max_ms > nguong, price_age_ms > nguong, p50/p95/max; lag_s max/ngay.
# Ngu nghia price_gap_max_ms / price_age_ms CHUA doi chieu code ingestor (MASTER xac nhan): gia tri thuong ~3,3 s (p50) => co the la
#   khoang cach lon nhat giua 2 lan cap nhat gia trong phut, KHONG phai do tre end-to-end.
# =============================================================================
set -uo pipefail
if [ -z "${_PL_MASKED:-}" ]; then export _PL_MASKED=1; bash "$0" "$@" 2>&1 | sed -u -E 's/[0-9]{8,10}:[A-Za-z0-9_-]{30,}/<TOKEN>/g'; exit "${PIPESTATUS[0]}"; fi
SSH_242=${SSH_242:-"ssh -p 2222 -o BatchMode=yes -o ConnectTimeout=20 -i /home/ubuntu/.ssh/id_rsa_chuyennd root@103.157.218.242"}
APP_DIR=${APP_DIR:-/home/chuyennd/java/v_t_m}; ING_DIR=${ING_DIR:-/home/chuyennd/java/collectData}; LAG_MS=${LAG_MS:-5000}
D=${1:-$(TZ=Asia/Ho_Chi_Minh date -d yesterday +%F)}
[[ "$D" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]] || { echo "ngay sai: $D"; exit 1; }
DP=$(echo "$D" | awk -F- '{print $3"/"$2"/"$1}')
R=$(timeout -k 5 120 $SSH_242 "bash -s -- $APP_DIR $ING_DIR '$DP' $LAG_MS" <<'EOR'
A=$1; I=$2; DP=$3; T=$4
for f in "$I/logs/full.log.1" "$I/logs/full.log"; do [ -f "$f" ] && nice -n 19 ionice -c3 grep -a "^$DP .*price_gap_max_ms=" "$f"; done \
 | awk '{ g=-1; a=0; if (match($0,/price_gap_max_ms=[0-9]+/)) g=substr($0,RSTART+17,RLENGTH-17)+0; if (match($0,/price_age_ms=[0-9]+/)) a=substr($0,RSTART+13,RLENGTH-13)+0; if (g>=0) print g, a }' \
 | sort -n -k1,1 | awk -v T="$T" '{ n++; G[n]=$1; if ($1>T) ng++; if ($2>T) na++; if ($2>ma) ma=$2 }
  END { if (n==0) { print "PRICE n=0"; exit } printf "PRICE n=%d gap_gt=%d gap_p50=%d gap_p95=%d gap_max=%d age_gt=%d age_max=%d\n", n, ng, G[int((n-1)*0.5)+1], G[int((n-1)*0.95)+1], G[n], na, ma }'
for f in "$A/logs/full.log.1" "$A/logs/full.log"; do [ -f "$f" ] && nice -n 19 ionice -c3 grep -a "^$DP .*\[KILLSW\] HOURLY" "$f"; done | grep -oE 'lag_s=[0-9]+' | cut -d= -f2 | sort -n | awk '{v[NR]=$1} END{printf "LAG n=%d lag_s_max=%d lag_s_p50=%d\n", NR, (NR?v[NR]:-1), (NR?v[int(NR*0.5)+1]:-1)}'
echo END_PL
EOR
) || { echo "ssh 242 loi"; exit 1; }
echo "$R" | grep -qx END_PL || { echo "doc 242 khong tron ven"; exit 1; }
P=$(echo "$R" | sed -n 's/^PRICE //p'); L=$(echo "$R" | sed -n 's/^LAG //p')
echo "ngay=$D nguong_ms=$LAG_MS | collectData: $P | v_t_m HOURLY: $L"
NG=$(echo "$P" | grep -oE 'gap_gt=[0-9]+' | cut -d= -f2); NN=$(echo "$P" | grep -oE '^n=[0-9]+' | cut -d= -f2)
[ "${NN:-0}" -gt 0 ] && echo "KET LUAN: ${NG:-0}/${NN} phut ($(awk -v a="${NG:-0}" -v b="$NN" 'BEGIN{printf "%.2f", 100*a/b}') %) co price_gap_max_ms > $LAG_MS ms" || echo "KET LUAN: KHONG DO DUOC (0 dong price_gap_max_ms ngay $D)"
