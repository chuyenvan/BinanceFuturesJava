#!/usr/bin/env bash
# =============================================================================
# fix_mapper_dirty_242.sh — go 3 muc TEST (ABCUSDT=2, ZZZUSDT=3, XUSDT=1) khoi symbol_mapper 242. Chay tren ORACLE:
#   DRY=1 bash ~/claude_master/deploy/fix_mapper_dirty_242.sh                 # CHI DOC
#   bash ~/claude_master/deploy/fix_mapper_dirty_242.sh                        # go YES 1 lan
#   RESTORE=<backup.json> bash ~/claude_master/deploy/fix_mapper_dirty_242.sh  # tra lai map tu backup
# KHONG restart gi (v_t_m LEGACY + collectData giu nguyen). 1 lenh CAS theo generation; backup JSON dinh dang
# SymbolMapperRepairTool truoc khi ghi; verify BTC=1 ETH=2 BNB=3, moi id khac giu nguyen, 0 id trung; loi => tu khoi phuc.
# Ma thoat: 0 xong | 1 dung truoc khi doi | 2 da doi va loi/khoi phuc (bao MASTER NGAY).
# =============================================================================
set -uo pipefail
D=/home/ubuntu/claude_master/deploy
PY=$D/fix_mapper_dirty_242.py
S="ssh -p 2222 -o BatchMode=yes -o ConnectTimeout=20 -i /home/ubuntu/.ssh/id_rsa_chuyennd root@103.157.218.242"
TS=$(TZ=Asia/Ho_Chi_Minh date +%Y%m%d_%H%M%S)
DRY=${DRY:-0}
LOG=$D/fix_mapper_dirty_${TS}$([ "$DRY" = 1 ] && echo _dry).log
exec > >(tee -a "$LOG") 2>&1
say() { echo "[$(TZ=Asia/Ho_Chi_Minh date '+%F %T')] $*"; }
die() { say "DUNG (khong doi gi): $*"; say "Log: $LOG"; exit 1; }
say "=== fix_mapper_dirty_242 TS=$TS DRY=$DRY ==="
python3 -m py_compile "$PY" && python3 "$PY" selftest || die "selftest $PY loi"

say "--- 1. CHI DOC 242: tien trinh (KHONG dung toi)"
PRE=$($S 'L=$(pgrep -f "trading[.]BinanceOrderTradingManager" | head -1); I=$(pgrep -f "websocket[.]BinanceDataIngestor" | head -1)
echo "legacy_pid=$L ingest_pid=$I"; [ -n "$L" ] && echo OK_legacy || echo FAIL_legacy_khong_chay' < /dev/null) || die "ssh loi"
echo "$PRE"; echo "$PRE" | grep -q FAIL && die "LEGACY khong chay — bao MASTER"
LEG=$(echo "$PRE" | grep -o 'legacy_pid=[0-9]*' | tr -dc 0-9)

say "--- 2. CHI DOC mapper"
python3 "$PY" check; RC=$?
if [ -n "${RESTORE:-}" ]; then
  [ "$DRY" = 1 ] && { say "DRY=1: se tra lai tu $RESTORE (khong ghi)."; exit 0; }
  say ">>> Sap TRA LAI symbol_mapper tu $RESTORE (mapper se CO LAI id trung). Go YES:"; read -r ANS; [ "$ANS" = YES ] || die "Huy."
  CONFIRM=YES python3 "$PY" restore "$RESTORE"; R=$?
else
  [ $RC = 0 ] && { say "Mapper da sach (0 id trung) — khong lam gi."; exit 0; }
  [ "$DRY" = 1 ] && { say "DRY=1: dung o day (khong backup, khong ghi)."; exit 0; }
  say ">>> Sap GO cac muc test o tren khoi symbol_mapper 242 (1 lenh CAS; KHONG restart gi). Go YES:"; read -r ANS
  [ "$ANS" = YES ] || die "Huy."
  BAK=$D/mapper_backup_${TS}.json
  CONFIRM=YES python3 "$PY" apply "$BAK"; R=$?
  [ $R = 0 ] && say "Backup: $BAK — tra lai neu can: RESTORE=$BAK bash $0"
fi
say "--- 3. kiem lai"
python3 "$PY" check
L2=$($S 'pgrep -f "trading[.]BinanceOrderTradingManager" | head -1' < /dev/null)
[ "$L2" = "$LEG" ] && say "OK legacy_pid_khong_doi=$L2" || { say "CANH BAO legacy_pid $LEG -> $L2 — bao MASTER"; R=2; }
case $R in 0) say "XONG. Log: $LOG";; 1) say "DUNG, khong doi gi. Log: $LOG";; *) say "LOI — bao MASTER NGAY. Log: $LOG";; esac
say "NHAC: KHONG restart v_t_m/collectData vi ly do mapper; JVM dang chay giu map trong RAM (v_t_m tu 27/10 khong co 3 muc test)."
exit $R
