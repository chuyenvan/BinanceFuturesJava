#!/usr/bin/env bash
# =============================================================================
# rollback_ingest_fin.sh <TS> - [FIN 2026-11-14] tra collectData 242 ve jar QF4b (15f47509) + env truoc deploy_ingest_fin (backup .bak_ingqf_<TS>).
# CANH BAO: v_t_m dang chay jar fin-guard => record moi KHONG con bin fin => v_t_m fail-closed moi phut. Rollback v_t_m ve r4u3
#   TRUOC (deploy_chain in lenh) hoac dat LIVE_FIN_GUARD=0 trong env.sh v_t_m roi restart.
# Chay tren ORACLE: bash ~/claude_master/deploy/rollback_ingest_fin.sh 20261115_1015    (DRY=1 de chi kiem, KHONG ghi gi)
# Khung giay 08-20 tu dong; KHONG chan theo gio (rollback la khan). Ma thoat: 0 OK | 1 dung truoc khi doi | 2 LOI.
# [QF3] PAUSE watchdog mang TOKEN rieng; chi go dung TOKEN do; PAUSE cua nguoi khac dang co => dung, khong dung toi.
# [A1-M4 2026-11-14] TU CHOI (ma 1, khong doi gi) khi v_t_m DANG chay jar fin-guard (md5 thuoc VTM_FIN_MD5S HOAC jar co class
#   aerospike/MinuteFin) ma guard fin BAT (env process LIVE_FIN_GUARD khong phai 0/false/no/off): ingestor ve QF4b => record mat bin
#   fin => v_t_m fail-closed MOI PHUT. Lam TRUOC: rollback v_t_m ve r4u3 (lenh deploy_chain in) hoac LIVE_FIN_GUARD=0 + restart v_t_m.
#   Khong thay process v_t_m => cung TU CHOI. FORCE=1 = ep chay (chi khi MASTER/owner chap nhan v_t_m fail-closed).
# =============================================================================
set -uo pipefail
TS=${1:-}; [ -n "$TS" ] || { echo "Dung: rollback_ingest_fin.sh <TS>"; exit 1; }
OLD_MD5=${OLD_MD5:-15f47509d9b9331b340337215e671198}
VTM_FIN_MD5S=${VTM_FIN_MD5S:-"39d998fa6fde882de26d9b046a6288a6 641803565297d4065d90245e04a00f11"}   # [A1-M4] jar v_t_m fin-guard (vong 1, vong 2)
VTM_PAT=${VTM_PAT:-'trading[.]BinanceOrderTradingManager'}   # [.] => khong khop chinh dong lenh bash mang pattern
S=${INGQF_SSH:-"ssh -p 2222 -o BatchMode=yes -o ConnectTimeout=20 -o ServerAliveInterval=10 -o ServerAliveCountMax=6 -i /home/ubuntu/.ssh/id_rsa_chuyennd root@103.157.218.242"}
C=${ING_DIR:-/home/chuyennd/java/collectData}; A=/home/chuyennd/java/v_t_m; D=${DEPLOY_DIR:-/home/ubuntu/claude_master/deploy}
PF=/var/lib/h242_watchdog/PAUSE
LOG=$D/rollback_ingest_fin_${TS}_$(TZ=Asia/Ho_Chi_Minh date +%H%M%S).log
exec > >(tee -a "$LOG") 2>&1
say() { echo "[$(TZ=Asia/Ho_Chi_Minh date '+%F %T')] $*"; }
TOKEN="ingqf_rollback_${TS}_$$"
own_pause_cleanup() {
  $S "f=$PF; [ \"\$(cat \$f 2>/dev/null)\" = '$TOKEN' ] && rm -f \$f && echo PAUSE_cua_minh_da_go || true" < /dev/null 2>/dev/null
}
say "=== rollback_ingest_fin TS=$TS DRY=${DRY:-0} token=$TOKEN ==="
PRE=$($S "bash -s -- $C $TS $OLD_MD5 '$VTM_PAT' '$VTM_FIN_MD5S'" <<'EOF'
C=$1; TS=$2; OLD=$3; VPAT=$4; FINS=$5
# [A1-M4] v_t_m dang chay jar fin-guard + guard BAT => REFUSE_VTM (khong in gi ngoai md5/gia tri co)
VP=$(pgrep -f "$VPAT" | head -1)
if [ -z "$VP" ]; then echo "REFUSE_VTM khong_thay_process_v_t_m ($VPAT) - khong kiem duoc jar dang chay"
else
  VFD=$(find /proc/$VP/fd -lname '*binance-java-sdk*.jar*' 2>/dev/null | head -1)
  VM=$( [ -n "$VFD" ] && md5sum < "$VFD" 2>/dev/null | cut -c1-32)
  VC=$( [ -n "$VFD" ] && grep -a -c 'com/binance/chuyennd/aerospike/MinuteFin' "$VFD" 2>/dev/null)
  VG=$(tr '\0' '\n' < /proc/$VP/environ 2>/dev/null | sed -n 's/^LIVE_FIN_GUARD=//p' | head -1)
  FJ=0; case " $FINS " in *" ${VM:-x} "*) FJ=1;; esac; [ "${VC:-0}" -ge 1 ] && FJ=1
  if [ -z "$VM" ]; then echo "REFUSE_VTM khong_doc_duoc_jar_v_t_m_dang_chay (pid $VP)"
  elif [ "$FJ" = 1 ]; then
    case "$(printf %s "$VG" | tr -d " \t\"'" | tr 'A-Z' 'a-z')" in
      0|false|no|off) echo "OK vtm_jar_fin_md5=$VM nhung LIVE_FIN_GUARD=$VG (guard TAT) => an toan";;
      *) echo "REFUSE_VTM vtm_dang_chay_jar_fin_guard md5=$VM guard BAT => rollback v_t_m ve r4u3 TRUOC hoac LIVE_FIN_GUARD=0 + restart";;
    esac
  else echo "OK vtm_khong_phai_jar_fin md5=$VM"; fi
fi
cd "$C" || { echo "FAIL cd"; exit 0; }
[ -f target/binance-java-sdk-1.2.4.jar.bak_ingqf_$TS ] && [ "$(md5sum < target/binance-java-sdk-1.2.4.jar.bak_ingqf_$TS | cut -c1-32)" = "$OLD" ] && echo "OK backup_jar_md5_dung" || echo "FAIL backup_jar"
[ -f conf/env.sh.bak_ingqf_$TS ] && echo "OK backup_env" || echo "FAIL backup_env"
[ -f /var/lib/h242_watchdog/PAUSE ] && echo "FAIL PAUSE_cua_nguoi_khac_dang_co: $(head -c 120 /var/lib/h242_watchdog/PAUSE)" || echo "OK khong_PAUSE"
echo "OK legacy_pid=$(pgrep -f 'trading.BinanceOrderTradingManager' | head -1)"
EOF
)
echo "$PRE"; echo "$PRE" | grep -q '^FAIL' && { say "DUNG (khong doi gi) — bao MASTER"; exit 1; }
if echo "$PRE" | grep -q '^REFUSE_VTM'; then
  if [ "${FORCE:-0}" = 1 ]; then say "FORCE=1: BO QUA kiem v_t_m - v_t_m se fail-closed MOI PHUT toi khi rollback v_t_m / LIVE_FIN_GUARD=0"
  else say "TU CHOI (khong doi gi): v_t_m con chay jar fin-guard voi guard BAT. Rollback v_t_m TRUOC (lenh r4u3fin -> r4u3 deploy_chain in), roi chay lai. Ep: FORCE=1"; exit 1; fi
fi
[ "${DRY:-0}" = 1 ] && { say "DRY=1: dung (khong ghi gi)."; exit 0; }
PL=$(echo "$PRE" | grep -o 'legacy_pid=[0-9]*' | tr -dc 0-9)
$S "cd $C && \cp -fp target/binance-java-sdk-1.2.4.jar.bak_ingqf_$TS target/.jar_rb_tmp_$TS && mv -f target/.jar_rb_tmp_$TS target/binance-java-sdk-1.2.4.jar && \cp -fp conf/env.sh.bak_ingqf_$TS conf/env.sh && echo OK chep_lai" < /dev/null || { say "LOI chep backup"; exit 2; }
trap own_pause_cleanup EXIT   # chi tu day, chi go PAUSE mang TOKEN nay
R=$($S "bash -s -- $C $TOKEN" < $D/ingqf_restart_remote.sh); echo "$R"
echo "$R" | grep -q 'PAUSE_cua_nguoi_khac' && { say "Co nguoi khac PAUSE — file da tra ve cu nhung CHUA restart; chay lai sau"; exit 2; }
sleep 60
K=$($S "bash -s -- $C $A $OLD_MD5 ${PL:-0} old $TOKEN" < $D/ingqf4_check_remote.sh); echo "$K"
echo "$K" | grep -q '^OK jar_md5' && { say "ROLLBACK XONG (jar $OLD_MD5). Log: $LOG"; exit 0; }
say "ROLLBACK LOI — bao MASTER NGAY. Log: $LOG"; exit 2
