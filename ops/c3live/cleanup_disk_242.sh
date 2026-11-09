#!/usr/bin/env bash
# =============================================================================
# cleanup_disk_242.sh — don dia 242: CHI cac muc AN TOAN (jar backup cu, log da dong cu, journal). Chay tren ORACLE, tu ssh 242.
#   bash ~/claude_master/deploy/cleanup_disk_242.sh            # MAC DINH DRY: chi liet ke + GB du kien, KHONG doi gi
#   bash ~/claude_master/deploy/cleanup_disk_242.sh --apply    # chay that (khong restart gi, khong dung Aerospike/Redis/docker)
# AN TOAN:
#   1. jar backup trong v_t_m/target, collectData/target: GIU jar dang chay + moi ban trung md5 jar dang chay + ban rollback
#      (v_t_m r4q 8c81e6b5, collectData QF3 a31fdd6c) + 2 ban moi nhat + moi jar moi hon N ngay; khong xoa file dang mo.
#      jar trong v_t_m/backup_* va _deploy_v1 cu hon N ngay (giu file khac: conf...).
#   2. log DA DONG cu hon N ngay (full.log.<so>, gc*.log*, logt9.log) trong v_t_m/logs, collectData/logs: nen gzip vao logs/archived/
#      (ngoai pattern pull242 'logs/full.log.[0-9]*' maxdepth 1); khong dung file dang mo (quet /proc/*/fd + maps — 242 khong co lsof).
#      Ban nen trong archived/ cu hon M ngay => xoa. Giu nguyen moi log N ngay gan nhat (pull242/parity can >= 14 ngay).
#   3. journalctl --vacuum-size=JOURNAL_MAX neu journal > JOURNAL_MAX + 100 MB.
# CAM DUNG (chi liet ke): /opt/aerospike/data (data live), predictionSymbol (LiveGateRollingRatio.seedHistory doc), s1_dump/feat_dump/run
#   (pull242/parity), /var/lib/docker (docker daemon dang tat; log container cu 12.6G — owner/MASTER quyet rieng), Redis/Mongo, /root.
# Loi bat ky => DUNG ngay (in df). Bien: N_DAYS (14, toi thieu 14) M_DAYS (180) JOURNAL_MAX (200M) KEEP_RECENT (2).
# =============================================================================
set -uo pipefail
S=${SSH_242:-"ssh -p 2222 -o BatchMode=yes -o ConnectTimeout=20 -o ServerAliveInterval=10 -o ServerAliveCountMax=6 -i /home/ubuntu/.ssh/id_rsa_chuyennd root@103.157.218.242"}
APPLY=0
case "${1:-}" in
  --apply) APPLY=1;;
  ""|--dry) APPLY=0;;
  *) echo "Dung: $0 [--apply]   (mac dinh DRY)"; exit 1;;
esac
N_DAYS=${N_DAYS:-14}; M_DAYS=${M_DAYS:-180}; JOURNAL_MAX=${JOURNAL_MAX:-200M}; KEEP_RECENT=${KEEP_RECENT:-2}
[ "$N_DAYS" -ge 14 ] 2>/dev/null || { echo "N_DAYS phai >= 14 (pull242/parity can 14 ngay log)"; exit 1; }
[ "$M_DAYS" -gt "$N_DAYS" ] 2>/dev/null || { echo "M_DAYS phai > N_DAYS"; exit 1; }
D=/home/ubuntu/claude_master/deploy
TS=$(TZ=Asia/Ho_Chi_Minh date +%Y%m%d_%H%M%S)
LOG=$D/cleanup_disk_242_${TS}$([ "$APPLY" = 0 ] && echo _dry).log
exec > >(tee -a "$LOG") 2>&1
echo "[$(TZ=Asia/Ho_Chi_Minh date '+%F %T')] === cleanup_disk_242 APPLY=$APPLY N_DAYS=$N_DAYS M_DAYS=$M_DAYS JOURNAL_MAX=$JOURNAL_MAX KEEP_RECENT=$KEEP_RECENT ==="
$S "bash -s -- $APPLY $N_DAYS $M_DAYS $JOURNAL_MAX $KEEP_RECENT" <<'EOF'
APPLY=$1; N=$2; M=$3; JMAX=$4; KEEP=$5
A=/home/chuyennd/java/v_t_m; C=/home/chuyennd/java/collectData
R4Q=8c81e6b560b61e7d43ca32c4a50ec926; QF3=a31fdd6caf12ce35c12b839a3cced929
TOTAL=0; NACT=0
fail() { echo "FAIL: $* => DUNG NGAY"; df -h /; exit 1; }
gb() { awk -v b="$1" 'BEGIN{printf "%.2f GB", b/1073741824}'; }
echo "--- df TRUOC:"; df -h / | tail -1
# file dang mo: /proc/*/fd + /proc/*/maps (jar JVM duoc map)
OPEN=$( { ls -l /proc/[0-9]*/fd/ 2>/dev/null | awk '$NF ~ /^\// {print $NF}'; cat /proc/[0-9]*/maps 2>/dev/null | awk '$6 ~ /^\// {print $6}'; } | sort -u)
is_open() { echo "$OPEN" | grep -qxF "$(readlink -f "$1")"; }
act() {   # $1 mo ta, $2 bytes tiet kiem, roi lenh
  local what=$1 bytes=$2; shift 2
  TOTAL=$((TOTAL + bytes)); NACT=$((NACT + 1))
  if [ "$APPLY" = 1 ]; then "$@" || fail "$what"; echo "  DA $what ($(gb $bytes))"; else echo "  SE $what ($(gb $bytes))"; fi
}
# ---------------------------------------------------------------- 1. jar backup
jar_dir() {   # $1 thu muc target, $2 md5 rollback can giu, $3 nhan
  local T=$1 RB=$2 L=$3 RUN f m keep recent
  [ -f "$T/binance-java-sdk-1.2.4.jar" ] || fail "$L: khong thay jar dang chay $T/binance-java-sdk-1.2.4.jar"
  RUN=$(md5sum < "$T/binance-java-sdk-1.2.4.jar" | cut -c1-32)
  echo "--- jar $L: dang chay $RUN, rollback giu $RB, giu $KEEP ban moi nhat + moi jar moi hon $N ngay"
  recent=$(ls -t "$T"/binance-java-sdk-1.2.4.jar?* 2>/dev/null | grep -v '\.md5$' | while read -r f; do m=$(md5sum < "$f" | cut -c1-32); [ "$m" = "$RUN" ] || [ "$m" = "$RB" ] || echo "$f"; done | head -n "$KEEP")
  for f in $(ls "$T"/binance-java-sdk-1.2.4.jar?* 2>/dev/null | grep -v '\.md5$'); do
    m=$(md5sum < "$f" | cut -c1-32)
    if [ "$m" = "$RUN" ]; then echo "  GIU (trung jar dang chay) $(basename "$f")"; continue; fi
    if [ "$m" = "$RB" ]; then echo "  GIU (rollback) $(basename "$f")"; continue; fi
    if echo "$recent" | grep -qxF "$f"; then echo "  GIU ($KEEP moi nhat) $(basename "$f")"; continue; fi
    if [ -n "$(find "$f" -mtime -"$N" 2>/dev/null)" ]; then echo "  GIU (moi hon $N ngay) $(basename "$f")"; continue; fi
    if is_open "$f"; then echo "  GIU (dang mo) $(basename "$f")"; continue; fi
    act "xoa $L/$(basename "$f")" "$(stat -c %s "$f")" rm -f -- "$f"
  done
}
jar_dir "$A/target" "$R4Q" v_t_m
jar_dir "$C/target" "$QF3" collectData
echo "--- jar trong v_t_m/backup_*, _deploy_v1 (cu hon $N ngay; giu file khac)"
for f in $(find "$A"/backup_* "$A"/_deploy_v1 -maxdepth 3 -type f -name '*.jar*' -mtime +"$N" 2>/dev/null); do
  is_open "$f" && { echo "  GIU (dang mo) $f"; continue; }
  act "xoa ${f#$A/}" "$(stat -c %s "$f")" rm -f -- "$f"
done
# ---------------------------------------------------------------- 2. log da dong
for L in "$A/logs" "$C/logs"; do
  echo "--- log $L: nen gzip file da dong cu hon $N ngay -> archived/"
  [ -d "$L/archived" ] || { if [ "$APPLY" = 1 ]; then mkdir -p "$L/archived" || fail "mkdir $L/archived"; fi; }
  for f in $(find "$L" -maxdepth 1 -type f \( -name 'full.log.[0-9]*' -o -name 'gc*.log*' -o -name 'logt9.log' \) ! -name '*.gz' -mtime +"$N" 2>/dev/null); do
    is_open "$f" && { echo "  GIU (dang mo) $(basename "$f")"; continue; }
    d=$(date -r "$f" +%Y%m%d); dst="$L/archived/$(basename "$f").$d.gz"
    [ -e "$dst" ] && { echo "  BO QUA (da co $dst)"; continue; }
    sz=$(stat -c %s "$f")
    act "gzip $(basename "$f") -> archived/$(basename "$dst") (uoc tiet kiem 90%)" "$((sz * 9 / 10))" \
      bash -c "gzip -9 -c -- '$f' > '$dst.tmp' && gzip -t '$dst.tmp' && mv -f '$dst.tmp' '$dst' && touch -r '$f' '$dst' && rm -f -- '$f'"
  done
  for f in $(find "$L/archived" -maxdepth 1 -type f -name '*.gz' -mtime +"$M" 2>/dev/null); do
    act "xoa ban nen cu hon $M ngay ${f#$L/}" "$(stat -c %s "$f")" rm -f -- "$f"
  done
done
# ---------------------------------------------------------------- 3. journal
JB=$(journalctl --disk-usage 2>/dev/null | grep -oE '[0-9.]+[KMG]' | head -1)
jb=$(echo "$JB" | awk '{v=$1+0; u=substr($1,length($1)); if(u=="G")v*=1024; if(u=="K")v/=1024; print int(v)}')
jm=$(echo "$JMAX" | awk '{v=$1+0; u=substr($1,length($1)); if(u=="G")v*=1024; if(u=="K")v/=1024; print int(v)}')
echo "--- journal: ${JB:-?} (nguong ${JMAX} + 100M)"
if [ -n "$jb" ] && [ "$jb" -gt $((jm + 100)) ]; then
  act "journalctl --vacuum-size=$JMAX" "$(( (jb - jm) * 1048576 ))" journalctl --vacuum-size="$JMAX" -q
else echo "  khong dang ke — bo qua"; fi
# ---------------------------------------------------------------- CAM DUNG (chi liet ke)
echo "--- CAM DUNG (khong xu ly):"
for p in /opt/aerospike/data "$A/storage/data/predictionSymbol" "$A/s1_dump" "$A/feat_dump" "$A/run" /var/lib/docker /var/log/aerospike /var/lib/redis-cluster /var/lib/mongo /root; do
  [ -e "$p" ] && echo "  $(du -xsh "$p" 2>/dev/null | cut -f1)  $p"
done
echo "=== $([ "$APPLY" = 1 ] && echo DA XU LY || echo DRY: SE XU LY) $NACT muc, giai phong $( [ "$APPLY" = 1 ] && echo '' || echo 'du kien ')$(gb $TOTAL)"
echo "--- df SAU:"; df -h / | tail -1
echo END_CLEANUP
EOF
RC=$?
echo "[$(TZ=Asia/Ho_Chi_Minh date '+%F %T')] ssh rc=$RC. Log: $LOG"
cat <<'EOT'
--- DE XUAT (chi in, owner tu cai; khong tu dong):
  1. Cron Oracle hang tuan (Chu nhat 10:17, ngoai khung deploy):
       17 10 * * 0  bash /home/ubuntu/claude_master/deploy/cleanup_disk_242.sh --apply >/dev/null 2>&1
  2. /etc/logrotate.d/aerospike tren 242: 'daily' + 'rotate 14' + 'compress' (hien weekly, aerospike.log ~30 MB/ngay).
  3. predictionSymbol (~0.1 GB/ngay, 5.3 GB, KHONG gioi han): MASTER xac dinh cua so LiveGateRollingRatio.seedHistory can,
     roi them buoc tar.gz theo ngay cho thu muc cu hon cua so do (hien CAM DUNG).
  4. Log container docker cu 12.6 GB (/var/lib/docker/containers/d76683.../*-json.log, ghi lan cuoi 04-15, docker daemon dang tat):
     owner/MASTER quyet; neu dong y: truncate -s 0 <file> (khong xoa thu muc container).
  5. Aerospike /opt/aerospike/data/ticker.data: file thua 50 GB, da cap 46 GB => toi da them ~4 GB roi dung (khong can xu ly).
EOT
exit $RC
