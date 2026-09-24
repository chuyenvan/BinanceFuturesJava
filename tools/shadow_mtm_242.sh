#!/bin/bash
# MTM so giay C3 tren 242 — READ-ONLY. Chay TREN 242 (bash+awk+curl, 242 khong co python):
#   ssh.exe -p 2222 ... root@103.157.218.242 "tr -d '\r' | bash -s" < tools/shadow_mtm_242.sh
# In 1 dong tom tat + 3 lenh te nhat. Job SHADOW-HEALTH (docs/plan/QUEUE.md) dan dong nay vao docs/analysis/SHADOW_LOG.md.
# realized = dong '#realized' trong open_positions.csv; unrealized = (px_now - entry)*qty theo fapi ticker. Khong tinh phi/funding.
D=/home/chuyennd/java/shadow_c3; EQ=35000; T=/tmp/shadow_mtm.$$
REAL=$(grep -a '^#realized' $D/open_positions.csv | cut -d, -f2)
tail -n +2 $D/open_positions.csv | grep -v '^#' | while IFS=, read sym ts entry qty rank sp sl peak; do
  px=$(curl -s --max-time 8 "https://fapi.binance.com/fapi/v1/ticker/price?symbol=$sym" | grep -oE '"price":"[0-9.]+"' | grep -oE '[0-9.]+')
  [ -n "$px" ] && awk -v s=$sym -v e=$entry -v q=$qty -v p=$px -v ts=$ts -v now=$(date +%s000) \
      'BEGIN{printf "%s %.4f %.2f %.0f\n", s, (p/e-1)*100, (p-e)*q, (now-ts)/3600000}'
done > $T
awk -v real="$REAL" -v eq="$EQ" -v d="$(date '+%d/%m/%Y %H:%M')" '
  { n++; unrl+=$3; ret+=$2; if($2<0)neg++; if($4>=96)old++ }
  END { net=real+unrl; printf "%s | realized=%.0f | unrealized=%.0f | net=%.0f | net%%=%.2f%% | open=%d | am=%d/%d | avgRet=%.1f%% | >=96h=%d\n",
        d, real, unrl, net, 100*net/eq, n, neg, n, (n?ret/n:0), old }' $T
sort -k2 -n $T | head -3 | awk '{printf "  worst: %s %.1f%% (%.0f USD, %.0fh)\n",$1,$2,$3,$4}'
rm -f $T
