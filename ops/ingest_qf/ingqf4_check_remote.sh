#!/usr/bin/env bash
# ingqf_check_remote.sh — CHAY TREN 242 (chi doc). In OK/WAIT/FAIL. args: C A EXPECT_MD5 LEGACY_PID MODE(new|old) [TOKEN] [SINCE_EPOCH]
# MAJ-3: KHONG so Total; chi tieu chi on dinh: phu phut da chot (KLINE-COVER), tuoi gia SAU repair khoi dong, 0 ban/429/418,
# 0 restart JVM, LEGACY song, PAUSE da go, -Xmx2g co hieu luc.
C=$1; A=$2; EXP=$3; LEG=$4; MODE=$5; TOKEN=${6:-none}
PF=${INGQF_PAUSE_FILE:-/var/lib/h242_watchdog/PAUSE}
cd "$C" || { echo "FAIL cd"; exit 0; }
N=$(pgrep -fc 'websocket.BinanceDataIngestor'); P=$(pgrep -f 'websocket.BinanceDataIngestor' | head -1)
[ "$N" = 1 ] && echo "OK 1_process pid=$P" || echo "FAIL so_process=$N"
FD=$(find /proc/$P/fd -lname '*binance-java-sdk*.jar*' 2>/dev/null | head -1)
JM=$(md5sum < "$FD" 2>/dev/null | cut -c1-32)
[ "$JM" = "$EXP" ] && echo "OK jar_md5=$JM" || echo "FAIL jar_md5=$JM (can $EXP)"
if [ "$(cat "$PF" 2>/dev/null)" = "$TOKEN" ]; then echo "FAIL PAUSE_cua_minh_con"; elif [ -f "$PF" ]; then echo "INFO PAUSE_nguoi_khac_dang_co (khong dung toi)"; else echo "OK PAUSE_da_go"; fi
TP=$(pgrep -f 'trading.BinanceOrderTradingManager' | head -1)
[ "$TP" = "$LEG" ] && echo "OK legacy_pid_khong_doi=$TP" || echo "FAIL legacy_pid=$TP (truoc $LEG)"
AG=$(( $(date +%s) - $(stat -c %Y $A/logs/full.log) ))
[ "$AG" -le 90 ] && echo "OK legacy_log_tuoi=${AG}s" || echo "FAIL legacy_log_dung=${AG}s"
L=""; for f in logs/nohup.out logs/full.log; do grep -a -q "PID $P written" $f 2>/dev/null && { L=$f; break; }; done
if [ -z "$L" ]; then echo "FAIL khong_thay_dong_start_pid_$P"; exit 0; fi
X=$(tail -n +$(grep -a -n "PID $P written" $L | tail -1 | cut -d: -f1) $L)
# [11-10 MASTER] SINCE_EPOCH (arg 7, >0): MOI chi so hau kiem CHI tinh dong log co timestamp >= moc bat dau buoc
# (dong khong timestamp theo dong truoc). Dau hieu 1 lan luc start (budget bat, repair khoi dong xong) van doc tu luc start PID (XA).
# Khong co moc (0) = nhu cu: tu luc start PID (deploy_ingest_qf4 / rollback: PID vua start = moc buoc).
SINCE=${7:-0}; XA=$X
if [ "$SINCE" -gt 0 ] 2>/dev/null; then
  SK=$(date -d "@$SINCE" +%Y%m%d%H%M%S)
  X=$(awk -v s="$SK" '/^[0-9][0-9]\/[0-9][0-9]\/[0-9][0-9][0-9][0-9] [0-9][0-9]:[0-9][0-9]:[0-9][0-9]/{k=substr($0,7,4) substr($0,4,2) substr($0,1,2) substr($0,12,2) substr($0,15,2) substr($0,18,2); on=(k>=s)} on' <<<"$XA")
  echo "INFO moc_hau_kiem=$(date -d "@$SINCE" '+%F %T') dong_tu_moc=$(grep -c . <<<"$X")"
fi
grep -a -q 'Too many symbol price errors\|Restart: Reset' <<<"$X" && echo "FAIL co_restart_JVM" || echo "OK 0_restart"
grep -a -q 'REST banned\|REST cooldown\|"code":-1003' <<<"$X" && echo "FAIL co_ban_hoac_cooldown" || echo "OK 0_ban"
grep -a -q 'OutOfMemoryError' <<<"$X" && echo "FAIL OutOfMemoryError" || echo "OK 0_OOM"
grep -a -q 'Q11 VI PHAM' <<<"$X" && echo "FAIL Q11_call_fapi_trong_luc_ban" || echo "OK Q11_0_call_khi_ban"
grep -a -q 'Ch.t n.n ph.t' <<<"$X" && echo "OK co_chot_nen_sau_start" || echo "WAIT chua_co_dong_chot_nen"
[ "$MODE" = new ] || exit 0
tr '\0' '\n' < /proc/$P/environ | grep -qx 'INGEST_SCHEDULED_RESTART_HOURS=0' && echo "OK env_restart_lich_TAT" || echo "FAIL env_INGEST_SCHEDULED_RESTART_HOURS"
tr '\0' '\n' < /proc/$P/environ | grep -q '^JAVA_TOOL_OPTIONS=.*-Xmx2g' && echo "OK Xmx2g" || echo "FAIL thieu_JAVA_TOOL_OPTIONS_-Xmx2g"
grep -a -q '\[REST-BUDGET\] bat' <<<"$XA" && echo "OK budget_bat" || echo "FAIL budget_chua_bat"
B=$(grep -a '\[REST-BUDGET\] calls=' <<<"$X")
H4=$(grep -o 'http4[12][89]=[1-9][0-9]*' <<<"$B" | head -1); [ -z "$H4" ] && echo "OK 0_http429_418" || echo "FAIL $H4"
PK=$(grep -o 'peak60s=[0-9]*' <<<"$B" | sed 's/.*=//' | sort -n | tail -1); [ -z "$PK" ] || [ "$PK" -le 300 ] && echo "OK weight_peak=${PK:-na}" || echo "FAIL weight_peak=$PK"
echo "INFO hdr_max_IP=$(grep -o 'hdr_max=[0-9]*' <<<"$B" | sed 's/.*=//' | sort -n | tail -1) loop_restarts=$(grep -o 'loop_restarts=[0-9]*' <<<"$B" | tail -1)"
if ! grep -a -q 'repair khoi dong xong' <<<"$XA"; then
  # [QF3, MIN-D] tien do repair = so dong 'repair tien do' (deploy so sanh giua 2 lan kiem: con tang = dang chay, dung 5' = ket)
  echo "WAIT repair_khoi_dong_chua_xong REPAIR_PROGRESS=$(grep -a -c 'repair tien do' <<<"$XA")"; exit 0
fi
BR=$(grep -a 'repair_xong=1' <<<"$B")
NR=$(grep -c . <<<"$BR"); [ -z "$BR" ] && NR=0
if [ "$NR" -lt 2 ]; then echo "WAIT budget_sau_repair=$NR (<2)"; else
  PG=$(grep -o 'price_gap_max_ms=[-0-9]*' <<<"$BR" | sed 's/.*=//' | sort -n | tail -1)
  PA=$(grep -o 'price_age_ms=[-0-9]*' <<<"$BR" | tail -1 | sed 's/.*=//')
  [ "$PG" -ge 0 ] 2>/dev/null && [ "$PG" -le 5000 ] && echo "OK price_gap_max_ms_sau_repair=$PG" || echo "FAIL price_gap_max_ms_sau_repair=$PG"
  [ "$PA" -ge 0 ] 2>/dev/null && [ "$PA" -le 5000 ] && echo "OK price_age_ms=$PA" || echo "FAIL price_age_ms=$PA"
fi
CV=$(grep -a '\[KLINE-COVER\]' <<<"$X" | grep 'khoi_dong=0' | tail -2)
NC=$(grep -c . <<<"$CV"); [ -z "$CV" ] && NC=0
if [ "$NC" -lt 2 ]; then echo "WAIT kline_cover_sau_khoi_dong=$NC (<2)"; else
  BAD=$(grep -v 'chua_chot_truoc=0 bo_kiem=0 ' <<<"$CV" | head -1)
  [ -z "$BAD" ] && echo "OK kline_phu_phut_da_chot (2 dong KLINE-COVER chua_chot_truoc=0 bo_kiem=0)" || echo "FAIL kline_cover: $(cut -c1-200 <<<"$BAD")"
  # [QF4] jar moi phai log thieu_luc_chot; so phut chot thieu chi bao (Q12 cham o ing_qf_check)
  grep -q 'thieu_luc_chot=' <<<"$CV" && echo "INFO thieu_luc_chot_2_phut_cuoi=$(grep -o ' thieu_luc_chot=[-0-9]*' <<<"$CV" | sed 's/.*=//' | tr '\n' ',') do_mat_ws=$(grep -o ' thieu_do_mat_ws=[-0-9]*' <<<"$CV" | sed 's/.*=//' | tr '\n' ',') canh_bao_chot_thieu=$(grep -a -c 'KLINE-CHOT-THIEU' <<<"$X") ws_gap=$(grep -a -c 'KLINE-WS-GAP' <<<"$X")" || echo "INFO chua_co_truong_thieu_luc_chot (jar cu?)"
fi
grep -a -q '\[PRICE-AGE\] price_realtime dung' <<<"$X" && echo "FAIL co_canh_bao_PRICE-AGE" || echo "OK 0_PRICE-AGE"
