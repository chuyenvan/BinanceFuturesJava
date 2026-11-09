#!/usr/bin/env bash
# =============================================================================
# cleanup_oracle_disk.sh — don dia ORACLE (/dev/sda1). MAC DINH DRY (chi liet ke + GB); --apply moi chay that.
#   bash ~/claude_master/deploy/cleanup_oracle_disk.sh            # DRY
#   bash ~/claude_master/deploy/cleanup_oracle_disk.sh --apply    # owner chay
# PHA 1 (XOA muc AN TOAN):
#   a) ~/claude_master/a1_*scratch* (khong phai git) co file moi nhat truoc 2026-11-01.
#   b) jar build cu ~/claude_master/v12/jar: GIU ten r4n/r4p/r4q/r4r/r4s/r4t, GIU moi jar co md5 trong parity_v12w/jars.json hoac
#      duoc BAT KY file nao trong ~/claude_master/deploy (ca .deploy_chain/jobs), ~/ops, c3live/ops tro toi (32 hex), GIU jar < 7 ngay.
#   c) worktree A1 v12 tao truoc 11-05 (a1_r4i/j/m/n, a1_soak) + ing1030 a1_wt/a1_wt2/a1_wt3/a1_wt4/qf2_build:
#      CHI 'git worktree remove' (khong --force) neu dung la worktree that VA sach (status --porcelain rong); khong rm mu.
#      GIU ing1030/a1_wt4b (nguon jar QF4b dang chay), qf_wt (cron ing_qf_check).
# PHA 2 (NEN, khong xoa du lieu): ~/claude_master/1002..1016 va ~/wfo_ds_x1_2021 — CHI thu muc khong co file ghi trong 14 ngay
#   VA khong bi tham chieu (grep 'claude_master/<ten>' / '<ten>' cho wfo) trong crontab, ~/ops, ~/claude_master/deploy,
#   vz_e1_wt/research/parity_v12 (harness v12 + watcher), c3live/ops. Tung thu muc: tar | zstd -T2 -> ~/claude_master/archive/<ten>.tar.zst,
#   zstd -t + so so file thuong (find vs tar -tv) => moi xoa ban goc. Qua 'flock -w 3600 oracle_heavy.lock nice -n 10' (khong long);
#   free >= 4000 MB va dia trong >= 5 GB truoc MOI thu muc, khong thi DUNG.
# CAM DUNG: aerospike-data, pull242, parity_v12w, parity_v11w, vz_e1_wt, c3live, e2e1105, collect/liq, shadow_c3, gvz, java/simulator,
#   kaggle_sim, vz/out.
# =============================================================================
set -euo pipefail
APPLY=0
case "${1:-}" in --apply) APPLY=1;; ""|--dry) APPLY=0;; *) echo "Dung: $0 [--apply]"; exit 1;; esac
H=/home/ubuntu; CM=$H/claude_master
C3=$CM/v12/c3live; HARN=$CM/vz_e1_wt/research/parity_v12
LOCK=$CM/locks/oracle_heavy.lock; ARC=$CM/archive
TS=$(date +%Y%m%d_%H%M%S); SUF=""; if [ "$APPLY" = 0 ]; then SUF=_dry; fi
LOG=$CM/deploy/cleanup_oracle_disk_${TS}${SUF}.log
exec > >(tee -a "$LOG") 2>&1
say() { echo "[$(date '+%F %T')] $*"; }
fail() { say "ABORT: $*"; df -h / | tail -1; exit 1; }
gb() { awk -v b="$1" 'BEGIN{printf "%.2f GB", b/1073741824}'; }
dsz() { du -sb -- "$1" 2>/dev/null | cut -f1; }
inside() { local rp; rp=$(realpath -e -- "$1") || return 1; case "$rp" in "$CM"/*|"$H/wfo_ds_x1_2021") return 0;; *) return 1;; esac; }
say "=== cleanup_oracle_disk APPLY=$APPLY ==="
say "df TRUOC: $(df -h / | tail -1)"
P1=0; P2=0
# ================================================================ PHA 1a: scratch
say "--- PHA 1a: a1_*scratch* (khong git, file moi nhat < 2026-11-01)"
while IFS= read -r -d '' d; do
  inside "$d" || fail "ngoai $CM: $d"
  if git -C "$d" rev-parse --is-inside-work-tree >/dev/null 2>&1; then say "  BO QUA (la git) $d"; continue; fi
  newest=$(find "$d" -type f -printf '%TY-%Tm-%Td\n' 2>/dev/null | sort | tail -1)
  if [[ "$newest" > "2026-10-31" ]]; then say "  BO QUA (co file $newest) $d"; continue; fi
  s=$(dsz "$d"); P1=$((P1 + s))
  if [ "$APPLY" = 1 ]; then rm -rf -- "$(realpath -e -- "$d")" || fail "rm $d"; say "  DA xoa $(basename "$d") ($(gb "$s"))"
  else say "  SE xoa $(basename "$d") ($(gb "$s"), moi nhat $newest)"; fi
done < <(find "$CM" -mindepth 1 -maxdepth 1 -type d -name 'a1_*scratch*' -print0 | sort -z)
# ================================================================ PHA 1b: jar v12
say "--- PHA 1b: jar build cu $CM/v12/jar"
KEEPMD5=$( { grep -ho '[0-9a-f]\{32\}' "$CM/parity_v12w/jars.json" 2>/dev/null || true
             for t in "$CM/deploy" "$H/ops" "$C3/ops"; do
               [ -d "$t" ] && find "$t" -type f -size -5M -print0 | xargs -0 -r grep -hoI '[0-9a-f]\{32\}' 2>/dev/null || true
             done; } | sort -u)
[ -n "$KEEPMD5" ] || fail "danh sach md5 can giu rong"
for m in 694b29b2e5be32b537ca6c38557e64db 8c81e6b560b61e7d43ca32c4a50ec926; do grep -qx "$m" <<< "$KEEPMD5" || fail "danh sach md5 thieu $m (r4t/r4q)"; done
say "  md5 can giu: $(wc -l <<< "$KEEPMD5")"
while IFS= read -r -d '' f; do
  inside "$f" || fail "ngoai $CM: $f"
  b=$(basename -- "$f"); m=$(md5sum < "$f" | cut -c1-32)
  case "$b" in *_r4n|*_r4p|*_r4q|*_r4r|*_r4s|*_r4t) say "  GIU (ten) $b"; continue;; esac
  if grep -qx "$m" <<< "$KEEPMD5"; then say "  GIU (md5 ${m:0:8} duoc tro toi) $b"; continue; fi
  if [ -n "$(find "$f" -mtime -7)" ]; then say "  GIU (<7 ngay) $b"; continue; fi
  s=$(stat -c %s -- "$f"); P1=$((P1 + s))
  if [ "$APPLY" = 1 ]; then rm -f -- "$(realpath -e -- "$f")" || fail "rm $f"; say "  DA xoa $b"; else say "  SE xoa $b (${m:0:8}, $(gb "$s"))"; fi
done < <(find "$CM/v12/jar" -maxdepth 1 -type f -name 'binance-java-sdk-*' -print0 | sort -z)
# ================================================================ PHA 1c: worktree
say "--- PHA 1c: worktree A1 cu (git worktree remove, chi khi sach)"
for d in "$CM/v12/a1_r4i" "$CM/v12/a1_r4j" "$CM/v12/a1_r4m" "$CM/v12/a1_r4n" "$CM/v12/a1_soak" \
         "$CM/ing1030/a1_wt" "$CM/ing1030/a1_wt2" "$CM/ing1030/a1_wt3" "$CM/ing1030/a1_wt4" "$CM/ing1030/qf2_build"; do
  [ -d "$d" ] || { say "  BO QUA (khong co) $d"; continue; }
  inside "$d" || fail "ngoai $CM: $d"
  top=$(git -C "$d" rev-parse --show-toplevel 2>/dev/null || true)
  gd=$(git -C "$d" rev-parse --absolute-git-dir 2>/dev/null || true); cg=$(git -C "$d" rev-parse --git-common-dir 2>/dev/null || true)
  if [ "$top" != "$d" ] || [ "$gd" = "$cg" ] || [[ "$gd" != */worktrees/* ]]; then say "  BO QUA (khong phai worktree phu that) $d"; continue; fi
  dirty=$(git -C "$d" status --porcelain 2>/dev/null | wc -l)
  if [ "$dirty" != 0 ]; then say "  BO QUA ($dirty thay doi/file chua commit) ${d#$CM/}"; continue; fi
  s=$(dsz "$d"); P1=$((P1 + s))
  if [ "$APPLY" = 1 ]; then git -C "$d" worktree remove -- "$d" || fail "git worktree remove $d"; say "  DA worktree remove ${d#$CM/}"
  else say "  SE git worktree remove ${d#$CM/} ($(gb "$s"))"; fi
done
say "=== PHA 1: $([ "$APPLY" = 1 ] && echo 'da giai phong' || echo 'du kien') $(gb "$P1")"
# ================================================================ PHA 2: nen
say "--- PHA 2: nen tar.zst (khong ghi 14 ngay + khong bi tham chieu)"
REFTXT=$( { crontab -l 2>/dev/null || true
            for t in "$H/ops" "$CM/deploy" "$HARN" "$C3/ops"; do
              [ -d "$t" ] && find "$t" -type f -size -5M -print0 | xargs -0 -r grep -hI "" 2>/dev/null || true   # -I: bo file nhi phan
            done; } )
[ -n "$REFTXT" ] || fail "khong doc duoc nguon tham chieu (crontab/ops/deploy/harness)"
CANDS=()
for d in "$CM"/10[01][0-9] "$H/wfo_ds_x1_2021"; do [ -d "$d" ] && CANDS+=("$d"); done
for d in "${CANDS[@]}"; do
  inside "$d" || fail "ngoai pham vi: $d"
  n=$(basename -- "$d")
  newest=$(find "$d" -printf '%T@\n' 2>/dev/null | sort -n | tail -1 | cut -d. -f1)
  age=$(( ($(date +%s) - ${newest:-0}) / 86400 ))
  if [ "$age" -lt 14 ]; then say "  LOAI $n: co file ghi $age ngay truoc (<14)"; continue; fi
  if [ "$n" = wfo_ds_x1_2021 ]; then pat="wfo_ds_x1_2021"; else pat="claude_master/$n([/\"' ]|\$)"; fi
  if grep -qE -- "$pat" <<< "$REFTXT"; then say "  LOAI $n: bi tham chieu trong cron/ops/deploy/harness"; continue; fi
  s=$(dsz "$d"); nf=$(find "$d" -type f | wc -l)
  if [ "$APPLY" = 0 ]; then say "  SE nen $n ($(gb "$s"), $nf file, khong ghi $age ngay) -> archive/$n.tar.zst"; P2=$((P2 + s)); continue; fi
  mem=$(free -m | awk '/^Mem:/{print $7}'); avail=$(df -BG --output=avail / | tail -1 | tr -dc 0-9)
  [ "$mem" -ge 4000 ] || fail "free ${mem} MB < 4000 truoc $n"
  [ "$avail" -ge 5 ] || fail "dia trong ${avail} GB < 5 truoc $n"
  mkdir -p "$ARC"; out="$ARC/$n.tar.zst"
  [ -e "$out" ] && fail "da co $out (lan truoc do dang?) — kiem tay"
  flock -w 3600 "$LOCK" nice -n 10 bash -c 'set -euo pipefail; tar -C "$1" -cf - "$2" | zstd -q -T2 -o "$3.tmp"' _ "$(dirname "$d")" "$n" "$out" \
    || { rm -f -- "$out.tmp"; fail "nen $n loi"; }
  zstd -q -t -- "$out.tmp" || { rm -f -- "$out.tmp"; fail "zstd -t $n loi"; }
  na=$(zstd -q -dc -- "$out.tmp" | tar -tvf - | grep -c '^-' || true)
  [ "$na" = "$nf" ] || { rm -f -- "$out.tmp"; fail "so file $n lech: goc $nf, archive $na"; }
  mv -f -- "$out.tmp" "$out"
  rm -rf -- "$(realpath -e -- "$d")" || fail "xoa goc $n"
  zs=$(stat -c %s -- "$out"); P2=$((P2 + s - zs))
  say "  DA nen $n: $(gb "$s") -> $(gb "$zs") ($nf file khop)"
done
say "=== PHA 2: $([ "$APPLY" = 1 ] && echo 'da giai phong' || echo 'du kien (truoc nen; thuc te tru kich thuoc .tar.zst)') $(gb "$P2")"
say "df SAU: $(df -h / | tail -1)"
say "Log: $LOG"
