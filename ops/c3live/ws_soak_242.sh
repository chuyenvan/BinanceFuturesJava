#!/usr/bin/env bash
# =============================================================================
# ws_soak_242.sh — [V12 R4h] SOAK user-data stream tai khoan chinh tren 242, CHI DOC, >= 26 h. Chay tren ORACLE (owner):
#   DRY=1 bash ~/claude_master/v12/c3live/ops/c3live/ws_soak_242.sh     # chi kiem, in ke hoach, KHONG ghi gi len 242
#   bash ~/claude_master/v12/c3live/ops/c3live/ws_soak_242.sh           # chep jar rieng vao /home/chuyennd/java/ws_soak, chay nen
#   MODE=status bash .../ws_soak_242.sh                                 # xem tien do / ket qua
#   MODE=stop   bash .../ws_soak_242.sh                                 # dung som (SIGTERM; KHONG DELETE listenKey)
# Cong cu: com.binance.chuyennd.c3live.soak.UserStreamSoak — chi POST/PUT listenKey (SoakGuard chan MOI goi khac ke ca
# DELETE), khong dat/huy lenh, khong dung v_t_m / collectData / canary. JVM rieng -Xmx256m. Ket qua: dong "[WS-SOAK] KET THUC".
# TU CHOI chay khi canary (C3LiveCanary) hoac c3_live LIVE_ADAPTER=live dang chay (stop() cua chung DELETE listenKey => nhieu
# do do); FORCE=1 bo qua (khong khuyen).
# [V12 R4l] BAI THU KET NOI LAI CUONG BUC ~1 h (docs/c3live/SOAK_ADDENDUM_R4L_FORCE_RECONNECT.md), jar soak RIENG (SJ_FC):
#   DRY=1 SOAK_HOURS=1.1 SOAK_FORCE_CLOSE_MIN=10 bash ~/claude_master/v12/c3live/ops/c3live/ws_soak_242.sh   # chi kiem
#   SOAK_HOURS=1.1 SOAK_FORCE_CLOSE_MIN=10 bash ~/claude_master/v12/c3live/ops/c3live/ws_soak_242.sh         # chay nen
#   client dong socket 6 lan (moi 10'); ket qua: dong "[WS-SOAK] KET THUC ... KET_QUA=DAT|CHUA_DAT" (MODE=status).
#   TU CHOI them khi tren Oracle dang co canary (canary_early_*/canary_step/canary.sh) hoac job deploy/rollback.
# =============================================================================
set -uo pipefail
SSH_242=${SSH_242:-"ssh -p 2222 -o BatchMode=yes -o ConnectTimeout=20 -i /home/ubuntu/.ssh/id_rsa_chuyennd root@103.157.218.242"}
SCP_242=${SCP_242:-"scp -P 2222 -o BatchMode=yes -o ConnectTimeout=20 -i /home/ubuntu/.ssh/id_rsa_chuyennd"}
RHOST=${RHOST-"root@103.157.218.242:"}
SJ=${SJ:-/home/ubuntu/claude_master/v12/jar/binance-java-sdk-1.2.4.jar_v12_r4j}
SJ_MD5=${SJ_MD5:-ba71eab2da6aac7bd296d7d5812e2d83}   # [V12 R4j] jar r4j (A1 R4J PASS-WITH-MINOR)
FCM=${SOAK_FORCE_CLOSE_MIN:-0}   # [V12 R4l] 0 = soak thuong; 1..60 = dong cuong buc moi FCM phut, 6 lan
SJ_FC=${SJ_FC:-/home/ubuntu/claude_master/v12/jar/binance-java-sdk-1.2.4.jar_v12_soak_r4l}
SJ_FC_MD5=${SJ_FC_MD5:-7239aa58b877fc554e30c410f3030417}   # [V12 R4l] jar soak RIENG (chi UserStreamSoak khac r4j)
DEPLOY_LOCKD=${DEPLOY_LOCKD:-/home/ubuntu/claude_master/deploy/.deploy_v12dry_r4.lock.d}
RD=${RD:-/home/chuyennd/java/ws_soak}
VTM=${VTM:-/home/chuyennd/java/v_t_m}
HOURS=${SOAK_HOURS:-26}
MODE=${MODE:-run}
DRY=${DRY:-0}
FORCE=${FORCE:-0}
JAVA_BIN=${JAVA_BIN:-java}
KEYS_FILE=${KEYS_FILE:-/root/.config/c3live/keys.env}
say() { echo "[$(TZ=Asia/Ho_Chi_Minh date '+%F %T')] $*"; }
if [ "$FCM" != 0 ]; then   # [R4l] che do ket noi lai cuong buc: jar soak rieng
  { [[ "$FCM" =~ ^[0-9]+$ ]] && [ "$FCM" -ge 1 ] && [ "$FCM" -le 60 ]; } || { say "DUNG: SOAK_FORCE_CLOSE_MIN=$FCM khong hop le (0 hoac 1..60)"; exit 1; }
  SJ=$SJ_FC; SJ_MD5=$SJ_FC_MD5
fi

if [ "$MODE" = status ]; then
  $SSH_242 "cd $RD 2>/dev/null || { echo 'chua co soak'; exit 0; }; P=\$(cat soak.pid 2>/dev/null); \
    if [ -n \"\$P\" ] && kill -0 \$P 2>/dev/null; then echo \"DANG CHAY pid=\$P\"; else echo 'KHONG CHAY'; fi; \
    grep -a '\[WS-SOAK\]' soak.log 2>/dev/null | grep -a 'BAT DAU\|KHE HO\|KET THUC\|khe_ho mat\|DONG CUONG BUC\|KET NOI LAI' | tail -20; \
    grep -a '\[WS-SOAK\] t+' soak.log 2>/dev/null | tail -1 | cut -c1-600; grep -a -c 'KEEPALIVE OK' soak.log 2>/dev/null" < /dev/null
  exit 0
fi
if [ "$MODE" = stop ]; then
  $SSH_242 "cd $RD && P=\$(cat soak.pid 2>/dev/null) && kill -0 \$P 2>/dev/null && kill \$P && echo \"da gui SIGTERM pid=\$P\" || echo 'khong co soak dang chay'" < /dev/null
  exit 0
fi

FAIL=0
chk() { if eval "$2"; then say "OK   $1"; else say "FAIL $1"; FAIL=1; fi; }
[ -f "$SJ" ] && GOT=$(md5sum < "$SJ" | cut -c1-32) || GOT=none
chk "jar soak $SJ md5=$GOT (pin $SJ_MD5)" "[ '$GOT' = '$SJ_MD5' ]"
R=$($SSH_242 "bash -s" <<EOF
echo JAVA=\$(command -v $JAVA_BIN >/dev/null 2>&1 && echo ok || echo none)
echo KEYS=\$( [ -f $KEYS_FILE ] && echo ok || echo none)
echo CANARY=\$(pgrep -fc '[C]3LiveCanary')
LA=0; [ -f $VTM/conf/env.sh ] && LA=\$(grep -c '^export LIVE_ADAPTER=live' $VTM/conf/env.sh); echo LIVEADAPTER=\$LA
echo SOAKRUN=\$( P=\$(cat $RD/soak.pid 2>/dev/null); [ -n "\$P" ] && kill -0 \$P 2>/dev/null && echo 1 || echo 0)
echo MEM=\$(awk '/MemAvailable/{print int(\$2/1024)}' /proc/meminfo)
EOF
)
echo "$R" | sed 's/^/   242: /'
v() { echo "$R" | grep "^$1=" | head -1 | cut -d= -f2; }
chk "242 co java" "[ '$(v JAVA)' = ok ]"
chk "242 co file key c3live (khong doc noi dung)" "[ '$(v KEYS)' = ok ]"
chk "242 khong co soak dang chay" "[ '$(v SOAKRUN)' = 0 ]"
chk "242 MemAvailable >= 600 MB ($(v MEM))" "[ '$(v MEM)' -ge 600 ] 2>/dev/null"
if [ "$FCM" != 0 ]; then
  NEED=$(awk -v m="$FCM" 'BEGIN{printf "%.2f", (6*m+3)/60}')
  chk "SOAK_HOURS=$HOURS du cho 6 lan dong cuong buc moi ${FCM}' (>= $NEED h)" "awk -v h='$HOURS' -v n='$NEED' 'BEGIN{exit !(h+0 >= n+0 && h+0 <= 72)}'"
fi
# [R4l] Oracle: khong chay song song canary (dieu phoi o Oracle, ke ca luc cho khung gio) / job deploy-rollback
OC=$(pgrep -fc 'canary_early_all|canary_early_run|canary_early_install|canary_step|ops/c3live/canary/canary\.sh' 2>/dev/null); OC=${OC:-0}
OD=$(pgrep -fc 'deploy_v12_dry_r4|deploy_v12_dry\.sh|deploy_ingest|rollback_v12|rollback_ingest' 2>/dev/null); OD=${OD:-0}
LKP=$(cat "$DEPLOY_LOCKD/pid" 2>/dev/null); [ -n "$LKP" ] && kill -0 "$LKP" 2>/dev/null && OD=$((OD + 1))
if [ "$FORCE" != 1 ]; then
  chk "khong co canary dang chay (DELETE listenKey cua canary se gay khe ho gia)" "[ '$(v CANARY)' = 0 ]"
  chk "Oracle: khong co script canary dang chay ($OC)" "[ '$OC' = 0 ]"
  chk "Oracle: khong co job deploy/rollback dang chay ($OD)" "[ '$OD' = 0 ]"
  chk "v_t_m khong o LIVE_ADAPTER=live" "[ '$(v LIVEADAPTER)' = 0 ]"
fi
CMD="cd $RD && { setsid nohup env -i PATH=\"\$PATH\" HOME=/root LANG=C.UTF-8 SOAK_HOURS=$HOURS SOAK_FORCE_CLOSE_MIN=$FCM LIVE_C3_KEYS_FILE=$KEYS_FILE $JAVA_BIN -Xmx256m -XX:+UseSerialGC -Dlogback.configurationFile=$RD/logback-soak.xml -cp soak.jar com.binance.chuyennd.c3live.soak.UserStreamSoak > soak.out 2>&1 < /dev/null & echo \$! > soak.pid; }"
say "ke hoach: mkdir $RD; chep jar -> $RD/soak.jar; logback -> $RD/logback-soak.xml; chay: $CMD"
if [ "$FAIL" != 0 ]; then say "DUNG: co muc FAIL (khong ghi gi len 242)"; exit 1; fi
if [ "$DRY" = 1 ]; then say "DRY=1: chi kiem, KHONG ghi gi len 242. Chay that: bo DRY=1"; exit 0; fi

# [R4l] log phien truoc doi ten (MODE=status chi thay phien moi)
$SSH_242 "mkdir -p $RD && cd $RD && { [ ! -f soak.log ] || mv -f soak.log soak.log.prev_\$(date +%Y%m%d_%H%M%S); }" < /dev/null || { say "FAIL mkdir"; exit 1; }
$SCP_242 "$SJ" "${RHOST}$RD/soak.jar" || { say "FAIL chep jar"; exit 1; }
$SSH_242 "cat > $RD/logback-soak.xml" <<'EOF'
<configuration>
  <appender name="F" class="ch.qos.logback.core.FileAppender">
    <file>${SOAK_LOG:-/home/chuyennd/java/ws_soak/soak.log}</file>
    <encoder><pattern>%d{yyyy-MM-dd HH:mm:ss.SSS} %-5level [%thread] %logger{20}: %msg%n</pattern></encoder>
  </appender>
  <root level="INFO"><appender-ref ref="F"/></root>
</configuration>
EOF
RM=$($SSH_242 "md5sum < $RD/soak.jar | cut -c1-32" < /dev/null)
[ "$RM" = "$SJ_MD5" ] || { say "FAIL md5 jar tren 242 $RM"; exit 1; }
$SSH_242 "$CMD" < /dev/null || { say "FAIL khoi dong"; exit 1; }
sleep ${START_WAIT_S:-25}
OUT=$($SSH_242 "cd $RD; P=\$(cat soak.pid); kill -0 \$P 2>/dev/null && echo ALIVE=\$P || echo DEAD; grep -a -c 'da ket noi' soak.log 2>/dev/null; grep -a 'LISTENKEY POST' soak.log 2>/dev/null | tail -1" < /dev/null)
echo "$OUT" | sed 's/^/   /'
if echo "$OUT" | grep -q '^ALIVE='; then
  say "XONG: soak dang chay ~$HOURS h. Xem: MODE=status bash $0 ; dung som: MODE=stop bash $0"
  exit 0
fi
say "FAIL: soak khong song — xem $RD/soak.out, $RD/soak.log tren 242"; exit 2
