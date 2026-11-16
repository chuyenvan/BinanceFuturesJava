#!/usr/bin/env bash
# =============================================================================
# rollback_vtm_r4u3.sh — [WAVE1 16/11 B-01/B-12] 1 LENH ve jar v_t_m r4u3 (b1f12c3e) tu r4u3fin2 (64180356), CHI khi v_t_m DRY.
#   DRY=1 bash $OPS/rollback_vtm_r4u3.sh   # $OPS = thu muc chua script nay   # chi kiem
#   bash $OPS/rollback_vtm_r4u3.sh         # go YES (job nen, cho khung gio — nhu swap_v12_dry_jar.sh)
# = swap_v12_dry_jar.sh voi OLD_TAG=r4u3fin NEW_TAG=r4u3 OLD_MD5=<r4u3fin2> NJ=<jar r4u3> NJ_MD5=<r4u3> NEED_FIN=0 (r4u3 doc bin data,
#   an toan voi ca 2 ingestor). TU CHOI khi: co co micro/pilot (Oracle) hoac v_t_m / env.sh LIVE_ADAPTER=live (dung golive_live_off.sh).
# Ghi chu: 2 co sizing/DCA (neu da bat) GIU trong env.sh — jar r4u3 cung doc 2 co nay (LiveGridSizing/LiveDcaGridC3 co tu 10-03).
# =============================================================================
set -uo pipefail
H=$(cd "$(dirname "$0")" && pwd)
LOGDIR=${LOGDIR:-/home/ubuntu/claude_master/deploy}
GL_MON_FLAG=${GL_MON_FLAG:-$LOGDIR/golive_monitor.on}
SSH_242=${SSH_242:-"ssh -p 2222 -o BatchMode=yes -o ConnectTimeout=20 -o ServerAliveInterval=10 -o ServerAliveCountMax=6 -i /home/ubuntu/.ssh/id_rsa_chuyennd root@103.157.218.242"}
A=${APP_DIR:-/home/chuyennd/java/v_t_m}
PROC_PAT=${PROC_PAT:-BinanceOrderTradingManager}
FROM_MD5=${FROM_MD5:-641803565297d4065d90245e04a00f11}
R4U3_JAR=${R4U3_JAR:-/home/ubuntu/claude_master/v12/jar/binance-java-sdk-1.2.4.jar_v12_r4u3}
R4U3_MD5=${R4U3_MD5:-b1f12c3eeaeed72cb17afbe5b4da06cf}
[ -f "$GL_MON_FLAG" ] && { echo "TU CHOI: co co micro/pilot $GL_MON_FLAG — dang go-live: MODE=drain bash $H/golive_live_off.sh"; exit 1; }
AD=$($SSH_242 "cd $A 2>/dev/null || exit 0; P=\$(pgrep -f '[${PROC_PAT:0:1}]${PROC_PAT:1}' | head -1); echo \"PA=\$(tr '\\0' '\\n' < /proc/\$P/environ 2>/dev/null | sed -n 's/^LIVE_ADAPTER=//p' | tail -1) SA=\$(sed -n 's/^export LIVE_ADAPTER=//p' conf/env.sh | tail -1)\"" < /dev/null) || { echo "TU CHOI: ssh 242 loi (khong doc duoc adapter)"; exit 1; }
echo "adapter 242: $AD"
case "$AD" in *PA=live*|*SA=live*) echo "TU CHOI: v_t_m dang LIVE — dung MODE=drain bash $H/golive_live_off.sh"; exit 1;; esac
[ -f "$R4U3_JAR" ] && [ "$(md5sum < "$R4U3_JAR" | cut -c1-32)" = "$R4U3_MD5" ] || { echo "TU CHOI: jar r4u3 $R4U3_JAR thieu / md5 != $R4U3_MD5"; exit 1; }
exec env OLD_TAG=r4u3fin NEW_TAG=r4u3 OLD_MD5="$FROM_MD5" NJ="$R4U3_JAR" NJ_MD5="$R4U3_MD5" NEED_FIN=0 bash "$H/swap_v12_dry_jar.sh"
