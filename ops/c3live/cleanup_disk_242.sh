#!/usr/bin/env bash
# =============================================================================
# cleanup_disk_242.sh — don dia 242: CHI muc AN TOAN (jar backup ngoai danh sach md5 can giu, log da dong cu, journal).
# Chay tren ORACLE, tu ssh 242:
#   bash ~/claude_master/deploy/cleanup_disk_242.sh            # MAC DINH DRY: chi liet ke + GB du kien, KHONG doi gi
#   bash ~/claude_master/deploy/cleanup_disk_242.sh --apply    # chay that (khong restart, khong dung Aerospike/Redis/docker)
# [A1 CLEANUP242 MAJ-1] Jar giu theo DANH SACH MD5 (khong theo mtime): moi md5 ma script rollback/deploy/swap/golive/reseed/
#   deploy_chain (ca pin trong jobs/) tro toi + jar dang chay + bat buoc r4t 694b29b2, r4q 8c81e6b5, dcae2e2b (rollback v1.2->v1.1),
#   QF4b 15f47509, QF3 a31fdd6c (+ v11c eea5adec neu co). Jar co md5 trong danh sach => GIU MOI BAN (rollback tro theo TEN .bak_<TS>);
#   ten backup ma script rollback tro toi (.bak_v12pre_*, .bak_ingqf_*, .bak_swap_*, .bak_reseed_*) => GIU bat ke md5.
#   Ngoai ra giu KEEP_RECENT ban moi nhat (theo mtime) cua phan con lai.
# [MAJ-2] find -print0 | while read -d '', duong dan tuyet doi, realpath phai nam trong thu muc cho phep truoc khi rm.
# [MAJ-3] set -euo pipefail ca 2 phia; ABORT truoc khi xoa neu: khong doc duoc /proc, khong thay jar cua 2 JVM trong danh sach
#   file dang mo, danh sach md5 thieu md5 bat buoc, hoac thu muc khong con ban nao cua md5 bat buoc.
# Log: log DA DONG cu hon N ngay (full.log.<so>, gc*.log*, logt9.log) -> gzip vao logs/archived/<ten>.<YYYYMMDD>.gz (ngoai pattern
#   pull242); xoa CHI ban nen do script nay tao (<ten>.<8 so>.gz) cu hon M ngay (khong dung archive cua log4j).
# CAM DUNG: /opt/aerospike/data, predictionSymbol, s1_dump, feat_dump, run, /var/lib/docker, Redis/Mongo, /root.
# Bien: N_DAYS (14, >=14) M_DAYS (180) JOURNAL_MAX (200M) KEEP_RECENT (2). Test: SSH_242 CL_APP CL_ING CL_PROC CL_PP_V CL_PP_I
#   CL_JOURNAL (0 = bo journal) CL_SCRIPTS (danh sach file script lay md5, cach nhau ':').
# =============================================================================
set -euo pipefail
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
CL_APP=${CL_APP:-/home/chuyennd/java/v_t_m}; CL_ING=${CL_ING:-/home/chuyennd/java/collectData}; CL_PROC=${CL_PROC:-/proc}
CL_PP_V=${CL_PP_V:-trading.BinanceOrderTradingManager}; CL_PP_I=${CL_PP_I:-websocket.BinanceDataIngestor}; CL_JOURNAL=${CL_JOURNAL:-1}
D=${CL_LOGDIR:-/home/ubuntu/claude_master/deploy}
O=/home/ubuntu/claude_master/v12/c3live/ops/c3live
REQ_V=${CL_REQ_V:-"694b29b2e5be32b537ca6c38557e64db 8c81e6b560b61e7d43ca32c4a50ec926 dcae2e2bbb1a357bc15703b416d4dccb"}   # r4t r4q v1.1
REQ_I=${CL_REQ_I:-"15f47509d9b9331b340337215e671198 a31fdd6caf12ce35c12b839a3cced929"}                                   # QF4b QF3
OPT="eea5adec"   # tien to v11c (giu neu co)
TS=$(TZ=Asia/Ho_Chi_Minh date +%Y%m%d_%H%M%S)
SUF=""; if [ "$APPLY" = 0 ]; then SUF=_dry; fi
LOG=$D/cleanup_disk_242_${TS}${SUF}.log
exec > >(tee -a "$LOG") 2>&1
say() { echo "[$(TZ=Asia/Ho_Chi_Minh date '+%F %T')] $*"; }
say "=== cleanup_disk_242 APPLY=$APPLY N_DAYS=$N_DAYS M_DAYS=$M_DAYS JOURNAL_MAX=$JOURNAL_MAX KEEP_RECENT=$KEEP_RECENT ==="
# ---------------------------------------------------------------- danh sach md5 can giu (tu script tren Oracle)
if [ -n "${CL_SCRIPTS:-}" ]; then
  IFS=: read -r -a SCR <<< "$CL_SCRIPTS"
else
  SCR=("$O/rollback_v12.sh" "$D/rollback_ingest_qf4.sh" "$D/deploy_ingest_qf4.sh" "$O/swap_v12_dry_jar.sh" "$O/restart_v12_dry_reseed.sh"
       "$O/deploy_v12_dry_r4.sh" "$O/deploy_chain.sh" "$D/deploy_chain.sh")
  for f in "$O"/golive_*.sh; do SCR+=("$f"); done
  while IFS= read -r -d '' f; do SCR+=("$f"); done < <(find "$D/.deploy_chain/jobs" -type f -name '*.sh' -print0 2>/dev/null || true)
fi
KEEP=""
for f in "${SCR[@]}"; do
  [ -r "$f" ] || { say "ABORT: khong doc duoc script $f (can de lay md5 rollback)"; exit 1; }
  KEEP="$KEEP $(grep -o '[0-9a-f]\{32\}' "$f" | tr '\n' ' ' || true)"
done
KEEP=$(echo "$KEEP" | tr ' ' '\n' | grep -E '^[0-9a-f]{32}$' | sort -u | tr '\n' ' ' || true)
for m in $REQ_V $REQ_I; do   # md5 bat buoc phai DUOC script tro toi (script mat/sua => danh sach khong tin cay)
  case " $KEEP " in *" $m "*) ;; *) say "ABORT: danh sach md5 lay tu script thieu md5 bat buoc $m (script rollback/deploy mat hoac doi?)"; exit 1;; esac
done
say "md5 can giu: $(echo "$KEEP" | wc -w) (tu ${#SCR[@]} script + bat buoc)"
set +e
$S "bash -s -- $APPLY $N_DAYS $M_DAYS $JOURNAL_MAX $KEEP_RECENT '$CL_APP' '$CL_ING' '$CL_PROC' '$CL_PP_V' '$CL_PP_I' $CL_JOURNAL '$KEEP' '$REQ_V' '$REQ_I' $OPT" <<'EOF'
set -euo pipefail
APPLY=$1; N=$2; M=$3; JMAX=$4; KEEPN=$5; A=$6; C=$7; PROC=$8; PPV=$9; PPI=${10}; DOJ=${11}; KEEP=${12}; REQV=${13}; REQI=${14}; OPT=${15}
TOTAL=0; NACT=0
fail() { echo "ABORT/FAIL: $* => DUNG NGAY (khong xoa them gi)"; df -h / | tail -1; exit 1; }
gb() { awk -v b="$1" 'BEGIN{printf "%.2f GB", b/1073741824}'; }
A=$(realpath -e -- "$A") || fail "khong co $A"; C=$(realpath -e -- "$C") || fail "khong co $C"
echo "--- df TRUOC:"; df -h / | tail -1
# ---------------------------------------------------------------- file dang mo (fail-closed)
[ -r "$PROC/self/maps" ] || fail "khong doc duoc $PROC"
OPEN=$( { find "$PROC" -mindepth 3 -maxdepth 3 -path "$PROC/[0-9]*/fd/*" -type l -printf '%l\n' 2>/dev/null || true
          for mp in "$PROC"/[0-9]*/maps; do awk '$6 ~ /^\// {print $6}' "$mp" 2>/dev/null || true; done; } | sort -u)
[ -n "$OPEN" ] || fail "danh sach file dang mo RONG ($PROC khong doc duoc?)"
need_open() {   # jar cua JVM khop $1 phai nam trong OPEN
  local pat=$1 dir=$2 found=0 p cwd
  for p in $(pgrep -f -- "$pat" || true); do
    cwd=$(readlink "$PROC/$p/cwd" 2>/dev/null || true)
    if [ -n "$cwd" ] && grep -qxF -- "$cwd/target/binance-java-sdk-1.2.4.jar" <<< "$OPEN"; then found=1; fi
  done
  [ "$found" = 1 ] || fail "khong thay jar dang chay cua JVM '$pat' trong danh sach file dang mo (fd/maps) — khong du tin cay de xoa"
  echo "OK jar dang chay '$pat' co trong danh sach file dang mo"
}
need_open "$PPV" "$A"; need_open "$PPI" "$C"
is_open() { grep -qxF -- "$1" <<< "$OPEN"; }   # here-string (khong pipe: tranh SIGPIPE + pipefail => sai ket qua)
inside() { case "$1" in "$2"/*) return 0;; *) return 1;; esac; }
act() {   # $1 mo ta, $2 bytes, roi lenh
  local what=$1 bytes=$2; shift 2
  TOTAL=$((TOTAL + bytes)); NACT=$((NACT + 1))
  if [ "$APPLY" = 1 ]; then "$@" || fail "$what"; echo "  DA $what ($(gb "$bytes"))"; else echo "  SE $what ($(gb "$bytes"))"; fi
}
safe_rm() {   # $1 file, $2 thu muc cho phep
  local rp; rp=$(realpath -e -- "$1") || return 1
  inside "$rp" "$2" || { echo "  TU CHOI (ngoai $2): $rp"; return 1; }
  rm -f -- "$rp"
}
# ---------------------------------------------------------------- 1. jar backup (giu theo md5)
in_keep() { case " $KEEP " in *" $1 "*) return 0;; esac; case "$1" in "$OPT"*) return 0;; esac; return 1; }
jar_dir() {   # $1 thu muc target, $2 md5 bat buoc (chuoi), $3 nhan
  local T=$1 REQ=$2 L=$3 RUN f m rp req have list
  T=$(realpath -e -- "$T") || fail "khong co $T"
  [ -f "$T/binance-java-sdk-1.2.4.jar" ] || fail "$L: khong thay jar dang chay"
  RUN=$(md5sum < "$T/binance-java-sdk-1.2.4.jar" | cut -c1-32)
  echo "--- jar $L ($T): dang chay $RUN"
  list=$(mktemp)
  find "$T" -maxdepth 1 -type f -name 'binance-java-sdk-1.2.4.jar?*' ! -name '*.md5' -printf '%T@\t%p\0' | sort -z -rn > "$list"
  # md5 bat buoc: thu muc phai con >= 1 ban (dang chay tinh la 1 ban)
  for req in $REQ; do
    have=0
    if [ "$RUN" = "$req" ]; then have=1; fi
    while IFS=$'\t' read -r -d '' _ f; do if [ "$(md5sum < "$f" | cut -c1-32)" = "$req" ]; then have=1; fi; done < "$list"
    if [ "$have" = 0 ]; then echo "  CANH BAO: $L khong con ban nao md5 $req tren 242 (khong lam mat them; bao MASTER)"; fi
  done
  local nrecent=0
  while IFS=$'\t' read -r -d '' _ f; do
    rp=$(realpath -e -- "$f") || fail "realpath $f"
    inside "$rp" "$T" || fail "duong dan ngoai $T: $rp"
    m=$(md5sum < "$rp" | cut -c1-32)
    b=$(basename -- "$rp")
    if [ "$m" = "$RUN" ]; then echo "  GIU (trung jar dang chay) [$b]"; continue; fi
    if in_keep "$m"; then echo "  GIU (md5 trong danh sach rollback/pin ${m:0:8}) [$b]"; continue; fi
    case "$b" in *.bak_v12pre_*|*.bak_ingqf_*|*.bak_swap_*|*.bak_reseed_*) echo "  GIU (ten backup rollback tro toi) [$b]"; continue;; esac
    if [ "$nrecent" -lt "$KEEPN" ]; then nrecent=$((nrecent + 1)); echo "  GIU ($KEEPN moi nhat) [$b]"; continue; fi
    if is_open "$rp"; then echo "  GIU (dang mo) [$b]"; continue; fi
    act "xoa $L/[$b] md5 ${m:0:8}" "$(stat -c %s -- "$rp")" safe_rm "$rp" "$T"
  done < "$list"
  rm -f "$list"
}
jar_dir "$A/target" "$REQV" v_t_m
jar_dir "$C/target" "$REQI" collectData
echo "--- jar trong v_t_m/backup_*, _deploy_v1 (giu md5 trong danh sach)"
while IFS= read -r -d '' f; do
  rp=$(realpath -e -- "$f") || fail "realpath $f"; inside "$rp" "$A" || fail "ngoai $A: $rp"
  m=$(md5sum < "$rp" | cut -c1-32)
  if in_keep "$m"; then echo "  GIU (md5 trong danh sach ${m:0:8}) [${rp#$A/}]"; continue; fi
  if is_open "$rp"; then echo "  GIU (dang mo) [${rp#$A/}]"; continue; fi
  act "xoa [${rp#$A/}] md5 ${m:0:8}" "$(stat -c %s -- "$rp")" safe_rm "$rp" "$A"
done < <(find "$A" -mindepth 2 -maxdepth 3 -type f -name '*.jar*' \( -path "$A/backup_*" -o -path "$A/_deploy_v1/*" \) -print0)
# ---------------------------------------------------------------- 2. log da dong
gz_one() {   # $1 src $2 dst
  gzip -9 -c -- "$1" > "$2.tmp" && gzip -t -- "$2.tmp" && mv -f -- "$2.tmp" "$2" && touch -r "$1" -- "$2" && rm -f -- "$1"
}
for L in "$A/logs" "$C/logs"; do
  echo "--- log $L: gzip file da dong cu hon $N ngay -> archived/"
  if [ ! -d "$L/archived" ] && [ "$APPLY" = 1 ]; then mkdir -p -- "$L/archived" || fail "mkdir $L/archived"; fi
  while IFS= read -r -d '' f; do
    rp=$(realpath -e -- "$f") || fail "realpath $f"; inside "$rp" "$L" || fail "ngoai $L: $rp"
    if is_open "$rp"; then echo "  GIU (dang mo) [$(basename -- "$rp")]"; continue; fi
    dst="$L/archived/$(basename -- "$rp").$(date -r "$rp" +%Y%m%d).gz"
    if [ -e "$dst" ]; then echo "  BO QUA (da co $dst)"; continue; fi
    sz=$(stat -c %s -- "$rp")
    act "gzip [$(basename -- "$rp")] -> archived/ (uoc tiet kiem 90%)" "$((sz * 9 / 10))" gz_one "$rp" "$dst"
  done < <(find "$L" -maxdepth 1 -type f \( -name 'full.log.[0-9]*' -o -name 'gc*.log*' -o -name 'logt9.log' \) ! -name '*.gz' -mtime +"$N" -print0)
  if [ -d "$L/archived" ]; then
    while IFS= read -r -d '' f; do
      act "xoa ban nen (cua script nay) cu hon $M ngay [${f#$L/}]" "$(stat -c %s -- "$f")" safe_rm "$f" "$L/archived"
    done < <(find "$L/archived" -maxdepth 1 -type f -regextype posix-extended -regex '.*\.[0-9]{8}\.gz' -mtime +"$M" -print0)
  fi
done
# ---------------------------------------------------------------- 3. journal
if [ "$DOJ" = 1 ]; then
  JB=$(journalctl --disk-usage 2>/dev/null | grep -oE '[0-9.]+[KMG]' | head -1 || true)
  jb=$(echo "${JB:-0M}" | awk '{v=$1+0; u=substr($1,length($1)); if(u=="G")v*=1024; if(u=="K")v/=1024; print int(v)}')
  jm=$(echo "$JMAX" | awk '{v=$1+0; u=substr($1,length($1)); if(u=="G")v*=1024; if(u=="K")v/=1024; print int(v)}')
  echo "--- journal: ${JB:-?} (nguong $JMAX + 100M)"
  if [ "$jb" -gt $((jm + 100)) ]; then act "journalctl --vacuum-size=$JMAX" "$(( (jb - jm) * 1048576 ))" journalctl --vacuum-size="$JMAX" -q
  else echo "  khong dang ke — bo qua"; fi
fi
echo "--- CAM DUNG (khong xu ly):"
for p in /opt/aerospike/data "$A/storage/data/predictionSymbol" "$A/s1_dump" "$A/feat_dump" "$A/run" /var/lib/docker /var/log/aerospike /var/lib/redis-cluster /var/lib/mongo /root; do
  if [ -e "$p" ]; then echo "  $(du -xsh "$p" 2>/dev/null | cut -f1)  $p"; fi
done
echo "=== $([ "$APPLY" = 1 ] && echo 'DA XU LY' || echo 'DRY: SE XU LY') $NACT muc, giai phong $([ "$APPLY" = 1 ] || echo 'du kien ')$(gb "$TOTAL")"
echo "--- df SAU:"; df -h / | tail -1
echo END_CLEANUP
EOF
RC=$?
set -e
say "ssh rc=$RC. Log: $LOG"
[ "$RC" = 0 ] || { say "CO LOI/ABORT (xem tren) — dung."; exit "$RC"; }
cat <<'EOT'
--- DE XUAT (chi in, owner tu cai; khong tu dong):
  1. Cron Oracle hang tuan CHI DRY (Chu nhat 10:17) + gui log cho MASTER; --apply van do owner chay tay sau khi xem DRY:
       17 10 * * 0  bash /home/ubuntu/claude_master/deploy/cleanup_disk_242.sh >/dev/null 2>&1
  2. /etc/logrotate.d/aerospike tren 242: 'daily' + 'rotate 14' + 'compress' (hien weekly, aerospike.log ~30 MB/ngay).
  3. predictionSymbol (~0.1 GB/ngay, 5.3 GB, khong gioi han): MASTER xac dinh cua so LiveGateRollingRatio.seedHistory can,
     roi them buoc tar.gz theo ngay cho thu muc cu hon cua so do (hien CAM DUNG).
  4. Log container docker cu 12.6 GB (/var/lib/docker/containers/d76683.../*-json.log, ghi lan cuoi 04-15, docker daemon dang tat):
     owner/MASTER quyet; neu dong y: truncate -s 0 <file> (khong xoa thu muc container).
  5. Aerospike /opt/aerospike/data/ticker.data: file thua 50 GB, da cap 46 GB => toi da them ~4 GB roi dung.
EOT
