#!/usr/bin/env bash
# ==========================================================================================
# KEO du lieu so giay C3 tu 242 ve Oracle roi dung lai bang lenh de doi chung voi sim.
# CHAY TREN ORACLE. READ-ONLY voi 242 (chi scp ve, khong ghi mot byte nao len 242).
#
# 🔴 CHUA BAT — 242 CHUA DEPLOY (2026-09-06). Bat sau khi user bao deploy XONG va verify PASS.
#    Cron (them bang `crontab -e`, dang comment de khong tu chay):
#      # 5 * * * * /home/ubuntu/src/BinanceFuturesJava/tools/pull_242_shadow.sh >> /home/ubuntu/shadow_242/pull.log 2>&1
#
# 242 KHONG co python3 => moi viec phan tich lam o Oracle.
# ==========================================================================================
set -u
KEY=${KEY:-/home/ubuntu/.ssh/id_rsa_chuyennd}
H=root@103.157.218.242
P=2222
APP=/home/chuyennd/java/v_t_m
SH242=/home/chuyennd/java/shadow_c3
OUT=/home/ubuntu/shadow_242
R=/home/ubuntu/src/BinanceFuturesJava
TS=$(date -u +%Y%m%d_%H%M%S)
SSH="ssh -p $P -i $KEY -o BatchMode=yes -o ConnectTimeout=20 -o StrictHostKeyChecking=no"
SCP="scp -P $P -i $KEY -o BatchMode=yes -o ConnectTimeout=20 -o StrictHostKeyChecking=no"

mkdir -p "$OUT/raw"
echo "[$TS] pull tu 242 ..."

# 1. log: chi lay 200k dong cuoi (full.log co the vai GB) — nen truoc khi keo cho nhe WAN
$SSH $H "tail -n 200000 $APP/logs/full.log | gzip -c" > "$OUT/raw/full_$TS.log.gz" || {
  echo "[$TS] LOI: khong keo duoc full.log"; exit 1; }

# 2. so giay + danh sach legacy
$SCP "$H:$SH242/ledger.csv"          "$OUT/raw/ledger_$TS.csv"          || echo "[$TS] chua co ledger.csv"
$SCP "$H:$SH242/open_positions.csv"  "$OUT/raw/open_positions_$TS.csv"  || echo "[$TS] chua co open_positions.csv"
$SCP "$H:$APP/run/legacy_symbols.csv" "$OUT/raw/legacy_symbols_$TS.csv" || echo "[$TS] chua co legacy_symbols.csv"

# 3. ban "moi nhat" de tay dung cho tien
for f in ledger open_positions legacy_symbols; do
  [ -f "$OUT/raw/${f}_$TS.csv" ] && cp -f "$OUT/raw/${f}_$TS.csv" "$OUT/${f}.csv"
done
gunzip -c "$OUT/raw/full_$TS.log.gz" > "$OUT/full.log"

# 4. dung lai bang lenh tu log (doi chung cheo voi ledger.csv do ShadowBookC3 ghi)
python3 "$R/tools/shadow_vs_sim.py" parse "$OUT/full.log" "$OUT/ledger_from_log.csv" \
  || echo "[$TS] shadow_vs_sim parse loi"

# 5. tom tat nhanh de doc trong pull.log
echo "[$TS] legacy managed  : $(grep -a '\[LEGACY\] managed' "$OUT/full.log" | tail -1 | sed -E 's/.*managed ([0-9]+):.*/\1/')"
echo "[$TS] Update all pos  : $(grep -a 'Update all position:' "$OUT/full.log" | tail -1 | sed -E 's/.*position:([0-9]+).*/\1/')"
echo "[$TS] would-BUY       : $(grep -ac '\[SHADOW\] would-BUY' "$OUT/full.log")"
echo "[$TS] skip-LEGACY     : $(grep -ac '\[SHADOW\] skip-LEGACY' "$OUT/full.log")"
echo "[$TS] lenh THAT moi   : $(grep -a 'market level: ' "$OUT/full.log" | grep -av '\[SHADOW\]' | grep -ac 'entry:')"
echo "[$TS] ledger dong     : $(wc -l < "$OUT/ledger.csv" 2>/dev/null || echo 0)"
echo "[$TS] xong."

# 6. don raw cu hon 14 ngay (dia Oracle 97%)
find "$OUT/raw" -type f -mtime +14 -delete 2>/dev/null || true
