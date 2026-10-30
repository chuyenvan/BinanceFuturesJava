#!/usr/bin/env bash
# =============================================================================
# rollback_ingest_qf.sh <TS> — tra collectData 242 ve jar/env truoc deploy_ingest_qf (backup .bak_ingqf_<TS>).
# Chay tren ORACLE: bash ~/claude_master/deploy/rollback_ingest_qf.sh 20261031_1015    (DRY=1 de chi kiem)
# Khung giay 08-20 tu dong; KHONG chan theo gio (rollback la khan). Ma thoat: 0 OK | 1 dung truoc khi doi | 2 LOI.
# =============================================================================
set -uo pipefail
TS=${1:-}; [ -n "$TS" ] || { echo "Dung: rollback_ingest_qf.sh <TS>"; exit 1; }
OLD_MD5=cb02d85e4f045c6cbdc8d94c18e188f1
S="ssh -p 2222 -o BatchMode=yes -o ConnectTimeout=20 -i /home/ubuntu/.ssh/id_rsa_chuyennd root@103.157.218.242"
C=/home/chuyennd/java/collectData; A=/home/chuyennd/java/v_t_m; D=/home/ubuntu/claude_master/deploy
LOG=$D/rollback_ingest_qf_${TS}_$(TZ=Asia/Ho_Chi_Minh date +%H%M%S).log
exec > >(tee -a "$LOG") 2>&1
say() { echo "[$(TZ=Asia/Ho_Chi_Minh date '+%F %T')] $*"; }
say "=== rollback_ingest_qf TS=$TS DRY=${DRY:-0} ==="
PRE=$($S "bash -s -- $C $TS $OLD_MD5" <<'EOF'
C=$1; TS=$2; OLD=$3; cd "$C" || { echo "FAIL cd"; exit 0; }
[ -f target/binance-java-sdk-1.2.4.jar.bak_ingqf_$TS ] && [ "$(md5sum < target/binance-java-sdk-1.2.4.jar.bak_ingqf_$TS | cut -c1-32)" = "$OLD" ] && echo "OK backup_jar_md5_dung" || echo "FAIL backup_jar"
[ -f conf/env.sh.bak_ingqf_$TS ] && echo "OK backup_env" || echo "FAIL backup_env"
T=$(grep -a 'Ch.t n.n ph.t' logs/nohup.out | tail -1 | grep -o 'Total: [0-9]*' | tr -dc 0-9); echo "OK tong_symbol=$T"
echo "OK legacy_pid=$(pgrep -f 'trading.BinanceOrderTradingManager' | head -1)"
EOF
)
echo "$PRE"; echo "$PRE" | grep -q '^FAIL' && { say "DUNG: thieu backup — bao MASTER"; exit 1; }
[ "${DRY:-0}" = 1 ] && { say "DRY=1: dung."; exit 0; }
PT=$(echo "$PRE" | grep -o 'tong_symbol=[0-9]*' | tr -dc 0-9); PL=$(echo "$PRE" | grep -o 'legacy_pid=[0-9]*' | tr -dc 0-9)
$S "cd $C && \cp -fp target/binance-java-sdk-1.2.4.jar.bak_ingqf_$TS target/.jar_rb_tmp_$TS && mv -f target/.jar_rb_tmp_$TS target/binance-java-sdk-1.2.4.jar && \cp -fp conf/env.sh.bak_ingqf_$TS conf/env.sh && echo OK chep_lai" || { say "LOI chep backup"; exit 2; }
$S "bash -s -- $C" < $D/ingqf_restart_remote.sh
sleep 100
K=$($S "bash -s -- $C $A $OLD_MD5 ${PT:-0} ${PL:-0} old" < $D/ingqf_check_remote.sh); echo "$K"
echo "$K" | grep -q '^OK jar_md5' && { say "ROLLBACK XONG (jar $OLD_MD5). Log: $LOG"; exit 0; }
say "ROLLBACK LOI — bao MASTER NGAY. Log: $LOG"; exit 2
