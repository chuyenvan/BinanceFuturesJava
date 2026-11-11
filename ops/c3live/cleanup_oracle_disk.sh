#!/usr/bin/env bash
# =============================================================================
# cleanup_oracle_disk.sh v2 — don dia ORACLE (/dev/sda1). MAC DINH DRY; --apply chay pha 1 roi pha 2.
#   bash ~/claude_master/v12/c3live/ops/c3live/cleanup_oracle_disk.sh            # DRY
#   bash ~/claude_master/v12/c3live/ops/c3live/cleanup_oracle_disk.sh --apply    # owner chay
# PHA 1 (XOA, danh sach co dinh):
#   a) ~/claude_master/a1_*scratch* (khong phai git, khong chua .git) co file moi nhat truoc 2026-11-01.
#   b) jar build cu ~/claude_master/v12/jar: GIU ten r4n/r4p/r4q/r4r/r4s/r4t/r4u3, moi md5 trong parity_v12w/jars.json hoac duoc file
#      trong ~/claude_master/deploy, ~/ops, c3live/ops tro toi, moi jar < 7 ngay.
#      [v2] jar vong r4u THUA (_r4u, _r4u_final, _r4u2): XOA bat ke tuoi, TRU khi md5 nam trong jars.json / gmicro_target /
#      script (*.sh *.py *.json *.md5 *.ok) trong deploy (ca pinned, gates), ~/ops, c3live/ops.
#   c) worktree A1 v12 (a1_r4i/j/m/n, a1_soak) + ing1030 (a1_wt, a1_wt2, a1_wt3, a1_wt4): CHI 'git worktree remove' (khong --force)
#      khi la worktree phu that VA sach. KHONG rm -rf worktree o bat ky pha nao. (qf2_build: KHONG — co ledger.csv/logs/config.)
#   d) [v2] worktree build r4u thua v12/wt_r4u, wt_r4u_final, wt_r4u2 (ca target/): worktree phu that; commit HEAD phai thuoc >=1
#      nhanh (khong mat lich su); sach => 'git worktree remove'; CHI con PrivateConfig chua commit => 'git worktree remove --force';
#      con file khac => BO QUA. GIU wt_r4u3 (jar dang chay), a1_r4u (A1 con duyet r4u3).
#   e) [v2; v3 A1 MIN-1] scratch A1 tu 11-05 trong v12/: CHI a1*_fake* (sandbox test gia), khong git, file moi nhat >= 2026-11-05
#      va cu hon 24 h. KHONG xoa bang chung A1: a1*_adv, a1*_log, a1*_drylog, a1*_gates, a1*_parity.
#   f) [v2; v3 A1 MIN-2] file trung gian parity (parity_v11w, parity_v12w) cua ngay d/YYYY-MM-DD DA co WATCH_DONE/DONE va cu hon
#      3 ngay, CHI 2 ten (doc code harness: duoc dung lai khi thieu / khong la dau vao bat buoc):
#        closes_cache.pkl (day_s1v: thieu => build_closes roi pickle lai), holes.csv (VisionCacheBuilder ghi moi lan, khong ai doc).
#      KHONG xoa: fund_NEW2 (A1 MIN-2), feat45_live* (day_prep giai ma tu psym pull242 — co the da het han),
#        s1v_rows, join_fund, net_live_all, fund_BT (day_kpp/day_kprime read_csv truc tiep khi cham lai), fund_D/fund_d1 (nho), 'cache'.
#      Ngoai le CAM DUNG chi cho dung 2 ten tren trong <parity>/d/<ngay>/; moi duong dan khac van fail-closed.
#   g) [v3] thu muc build Maven 'target' duoi ~/claude_master, ~/shadow_c3, ~/shadow_c3b, ~/src*: CHI thu muc ten 'target' co
#      classes/ hoac maven-status/ ben trong (dung lai bang mvn -o). TRU: wt_r4u3, r3_wt, res1109 va vung du lieu (TG_DENY);
#      target co process dang mo file / cwd / cmdline ben trong (/proc); target chua jar co md5 trong jars.json/pin/script/
#      gmicro_target ma KHONG co ban cung md5 trong v12/jar (=> LOAI, khong chep). Ngoai le CAM DUNG chi cho thu muc 'target'.
#   h) [v3] log shadow_c3 / shadow_c3b (shadow tat 11-03): file trong */app/logs/ cu hon 7 ngay. KHONG dung storage/data, jar.
#   KHONG dua vao: pull242 cu, kaggle_sim, aerospike-data. Cuoi script IN goi y 'sudo journalctl --vacuum-size=200M' (khong chay).
# PHA 2 (NEN): WHITELIST CUNG = ~/claude_master/1006 (A1: 0 tham chieu). Thu muc co .git => ABORT.
#   tar | zstd -T2 -> archive/<ten>.tar.zst, zstd -t + so file thuong, TAT CA trong 1 lan 'flock -w 3600 oracle_heavy.lock nice -n 10'
#   (khong long); free >= 4000 MB; dia trong >= max(5 GB, kich thuoc thu muc) — khong thi DUNG.
# Moi muc dich ma TRUNG / NAM TRONG / CHUA mot muc CAM DUNG => ABORT. KHONG dung: res1109/, r3_wt, vz_e1, kaggle_sim.
# =============================================================================
set -euo pipefail
APPLY=0
case "${1:-}" in --apply) APPLY=1;; ""|--dry) APPLY=0;; *) echo "Dung: $0 [--apply]"; exit 1;; esac
H=${CLEAN_H:-/home/ubuntu}; CM=$H/claude_master; C3=$CM/v12/c3live   # CLEAN_H chi cho test sandbox
LOCK=$CM/locks/oracle_heavy.lock; ARC=$CM/archive
NOW_S=${CLEAN_NOW_S:-$(date +%s)}
# ---------------------------------------------------------------- CAM DUNG (A1 + MASTER) — viet cung
FORBID=(
  "$H/aerospike-data" "$H/collect" "$H/shadow_c3" "$H/shadow_c3b" "$H/java/simulator" "$H/kaggle_sim" "$H/vz/out" "$H/wfo_ds_x1_2021"
  "$H/src" "$H/ops" "$H/vz_e1" "$H/ledger" "$H/.openclaw"
  "$CM/pull242" "$CM/parity_v12w" "$CM/parity_v11w" "$CM/vz_e1_wt" "$C3" "$CM/e2e1105" "$CM/gvz" "$CM/deploy" "$CM/locks"
  "$CM/1002" "$CM/1003" "$CM/1004" "$CM/1005" "$CM/1007" "$CM/1008" "$CM/1009" "$CM/1010" "$CM/1011" "$CM/1012" "$CM/1013" "$CM/1016"
  "$CM/1011/mapfix_wt" "$CM/ing1030/qf_wt" "$CM/ing1030/a1_wt4b" "$CM/ing1030/qf2_build" "$CM/ing1030/jar" "$CM/health242"
  "$CM/v12/a1_r4r" "$CM/v12/a1_r4t" "$CM/v12/a1_pq" "$CM/v12/a1_sw" "$CM/v12/a1_r4o"
  "$CM/res1109" "$CM/r3_wt" "$CM/v12/wt_r4u3" "$CM/v12/a1_r4u"
)
PF_ROOTS=("$CM/parity_v11w" "$CM/parity_v12w")   # [v2 f] ngoai le hep
PF_NAMES="closes_cache.pkl holes.csv"   # v3: fund_NEW2 GIU (A1 MIN-2)
# [v3 g] target/: goc cho phep + vung cam rieng (du lieu / dang chay / bang chung)
TG_DENY=("$CM/v12/wt_r4u3" "$CM/r3_wt" "$CM/res1109" "$H/aerospike-data" "$H/vz_e1" "$H/kaggle_sim" "$H/.openclaw" "$H/ledger" "$H/collect"
  "$H/vz/out" "$H/wfo_ds_x1_2021" "$H/java/simulator" "$CM/pull242" "$CM/parity_v12w" "$CM/parity_v11w" "$CM/deploy" "$CM/locks"
  "$CM/health242" "$CM/ing1030/jar" "$CM/gvz" "$CM/e2e1105" "$H/shadow_c3/app/storage" "$H/shadow_c3b/app/storage")
guard_tg() {   # $1 thu muc target: ten 'target', co classes/ hoac maven-status/, duoi goc cho phep, khong thuoc TG_DENY, khong symlink
  local rp f ok=0
  [ -L "$1" ] && fail "symlink: $1"; rp=$(realpath -e -- "$1") || fail "khong ton tai: $1"; [ -d "$rp" ] || fail "khong phai thu muc: $rp"
  [ "$(basename -- "$rp")" = target ] || fail "khong phai 'target': $rp"
  [ -d "$rp/classes" ] || [ -d "$rp/maven-status" ] || fail "target khong co classes/ maven-status/: $rp"
  case "$rp" in "$CM"/*|"$H"/shadow_c3/*|"$H"/shadow_c3b/*|"$H"/src/*|"$H"/src[_-]*/*) ok=1;; esac
  [ "$ok" = 1 ] || fail "target ngoai goc cho phep: $rp"
  for f in "${TG_DENY[@]}"; do
    case "$rp" in "$f"|"$f"/*) fail "CAM DUNG (target): $rp (thuoc $f)";; esac
    case "$f" in "$rp"/*) fail "CAM DUNG (target): $rp chua $f";; esac
  done
  for f in "${FORBID[@]}"; do case "$f" in "$rp"/*) fail "CAM DUNG: $rp chua $f";; esac; done
}
guard_sl() {   # [v3 h] $1 file log shadow: file thuong trong $H/shadow_c3{,b}/app/logs/
  local rp; [ -L "$1" ] && fail "symlink: $1"; rp=$(realpath -e -- "$1") || fail "khong ton tai: $1"; [ -f "$rp" ] || fail "khong phai file: $rp"
  case "$rp" in "$H"/shadow_c3/app/logs/*|"$H"/shadow_c3b/app/logs/*) ;; *) fail "ngoai app/logs shadow: $rp";; esac
  case "$rp" in *.jar|*/storage/*) fail "jar/storage: $rp";; esac
}
TS=$(date +%Y%m%d_%H%M%S); SUF=""; if [ "$APPLY" = 0 ]; then SUF=_dry; fi
LOG=$CM/deploy/cleanup_oracle_disk_${TS}${SUF}.log
exec > >(tee -a "$LOG") 2>&1
say() { echo "[$(date '+%F %T')] $*"; }
fail() { say "ABORT: $*"; df -h / | tail -1; exit 1; }
gb() { awk -v b="$1" 'BEGIN{printf "%.2f GB", b/1073741824}'; }
dsz() { du -sb -- "$1" 2>/dev/null | cut -f1; }
guard() {   # $1 duong dan dich: phai trong $CM, khong trung/nam trong/chua muc CAM DUNG
  local rp f; rp=$(realpath -e -- "$1") || fail "khong ton tai: $1"
  case "$rp" in "$CM"/*) ;; *) fail "ngoai $CM: $rp";; esac
  for f in "${FORBID[@]}"; do
    case "$rp" in "$f"|"$f"/*) fail "CAM DUNG: $rp (thuoc $f)";; esac
    case "$f" in "$rp"/*) fail "CAM DUNG: $rp chua $f";; esac
  done
}
guard_pf() {   # [v2 f] $1 file: PHAI la file thuong (khong symlink), ten trong PF_NAMES, nam trong <parity>/d/<YYYY-MM-DD>/...;
  local rp f r ok=0 b day                       # CAM DUNG khac (ngoai 2 goc parity) van ap dung
  [ -L "$1" ] && fail "symlink: $1"; rp=$(realpath -e -- "$1") || fail "khong ton tai: $1"; [ -f "$rp" ] || fail "khong phai file: $rp"
  b=$(basename -- "$rp"); case " $PF_NAMES " in *" $b "*) ;; *) fail "ten khong cho phep: $rp";; esac
  for r in "${PF_ROOTS[@]}"; do
    case "$rp" in "$r"/d/*) day=${rp#"$r"/d/}; day=${day%%/*}; [[ "$day" =~ ^20[0-9]{2}-[0-9]{2}-[0-9]{2}$ ]] && ok=1;; esac
  done
  [ "$ok" = 1 ] || fail "ngoai <parity>/d/<ngay>/: $rp"
  for f in "${FORBID[@]}"; do
    case "$f" in "$CM/parity_v11w"|"$CM/parity_v12w") continue;; esac
    case "$rp" in "$f"|"$f"/*) fail "CAM DUNG: $rp (thuoc $f)";; esac
  done
}
say "=== cleanup_oracle_disk v3 APPLY=$APPLY (cam dung: ${#FORBID[@]} muc) ==="
say "df TRUOC: $(df -h / | tail -1)"
P1=0; P2=0; declare -A G=()
add() { G[$1]=$(( ${G[$1]:-0} + $2 )); P1=$((P1 + $2)); }
# ================================================================ PHA 1a: scratch
say "--- PHA 1a: a1_*scratch* (khong git, file moi nhat < 2026-11-01)"
while IFS= read -r -d '' d; do
  guard "$d"
  if git -C "$d" rev-parse --is-inside-work-tree >/dev/null 2>&1 || [ -n "$(find "$d" -name .git -print -quit)" ]; then say "  BO QUA (co git) $d"; continue; fi
  newest=$(find "$d" -type f -printf '%TY-%Tm-%Td\n' 2>/dev/null | sort | tail -1)
  if [[ "$newest" > "2026-10-31" ]]; then say "  BO QUA (co file $newest) $d"; continue; fi
  s=$(dsz "$d"); add 1a "$s"
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
# [v2] md5 giu cho jar r4u thua: jars.json + gmicro_target + SCRIPT/PIN (khong tinh log *.log/*.txt)
KEEPS=$( { grep -ho '[0-9a-f]\{32\}' "$CM/parity_v12w/jars.json" "$CM/parity_v12w/gmicro_target.json" 2>/dev/null || true
           for t in "$CM/deploy" "$H/ops" "$C3/ops"; do
             [ -d "$t" ] && find "$t" -type f -size -5M \( -name '*.sh' -o -name '*.py' -o -name '*.json' -o -name '*.md5' -o -name '*.ok' -o -name '*.env' \) -print0 \
               | xargs -0 -r grep -hoI '[0-9a-f]\{32\}' 2>/dev/null || true
           done; } | sort -u)
grep -qx 694b29b2e5be32b537ca6c38557e64db <<< "$KEEPS" || fail "md5 script thieu r4t"
say "  md5 can giu: $(wc -l <<< "$KEEPMD5") (script/pin: $(wc -l <<< "$KEEPS"))"
while IFS= read -r -d '' f; do
  guard "$f"
  b=$(basename -- "$f"); m=$(md5sum < "$f" | cut -c1-32)
  case "$b" in *_r4n|*_r4p|*_r4q|*_r4r|*_r4s|*_r4t|*_r4u3) say "  GIU (ten) $b"; continue;; esac
  case "$b" in
    *_r4u|*_r4u_final|*_r4u2)   # [v2] jar thua vong r4u
      if grep -qx "$m" <<< "$KEEPS"; then say "  GIU (r4u thua nhung md5 ${m:0:8} co trong script/pin) $b"; continue; fi;;
    *)
      if grep -qx "$m" <<< "$KEEPMD5"; then say "  GIU (md5 ${m:0:8} duoc tro toi) $b"; continue; fi
      if [ -n "$(find "$f" -mtime -7)" ]; then say "  GIU (<7 ngay) $b"; continue; fi;;
  esac
  s=$(stat -c %s -- "$f"); add 1b "$s"
  if [ "$APPLY" = 1 ]; then rm -f -- "$(realpath -e -- "$f")" || fail "rm $f"; say "  DA xoa $b"; else say "  SE xoa $b (${m:0:8}, $(gb "$s"))"; fi
done < <(find "$CM/v12/jar" -maxdepth 1 -type f -name 'binance-java-sdk-*' -print0 | sort -z)
# ================================================================ PHA 1c: worktree (git worktree remove, khong --force)
say "--- PHA 1c: worktree A1 cu (chi git worktree remove khi sach; khong rm -rf)"
wt_real() {   # $1: la worktree phu that (top = $1, git dir rieng trong .../worktrees/...)
  local top gd cg; top=$(git -C "$1" rev-parse --show-toplevel 2>/dev/null || true)
  gd=$(git -C "$1" rev-parse --absolute-git-dir 2>/dev/null || true); cg=$(git -C "$1" rev-parse --git-common-dir 2>/dev/null || true)
  [ "$top" = "$1" ] && [ "$gd" != "$cg" ] && [[ "$gd" == */worktrees/* ]]
}
for d in "$CM/v12/a1_r4i" "$CM/v12/a1_r4j" "$CM/v12/a1_r4m" "$CM/v12/a1_r4n" "$CM/v12/a1_soak" \
         "$CM/ing1030/a1_wt" "$CM/ing1030/a1_wt2" "$CM/ing1030/a1_wt3" "$CM/ing1030/a1_wt4"; do
  [ -d "$d" ] || { say "  BO QUA (khong co) $d"; continue; }
  guard "$d"
  wt_real "$d" || { say "  BO QUA (khong phai worktree phu that) $d"; continue; }
  dirty=$(git -C "$d" status --porcelain --ignored=no 2>/dev/null | wc -l)
  if [ "$dirty" != 0 ]; then say "  BO QUA ($dirty thay doi/file chua commit) ${d#$CM/}"; continue; fi
  s=$(dsz "$d"); add 1c "$s"
  if [ "$APPLY" = 1 ]; then git -C "$d" worktree remove -- "$d" || fail "git worktree remove $d"; say "  DA worktree remove ${d#$CM/}"
  else say "  SE git worktree remove ${d#$CM/} ($(gb "$s"))"; fi
done
# ================================================================ PHA 1d: worktree build r4u thua
say "--- PHA 1d: worktree build r4u thua (wt_r4u, wt_r4u_final, wt_r4u2; GIU wt_r4u3)"
for d in "$CM/v12/wt_r4u" "$CM/v12/wt_r4u_final" "$CM/v12/wt_r4u2"; do
  [ -d "$d" ] || { say "  BO QUA (khong co) ${d#$CM/}"; continue; }
  guard "$d"
  wt_real "$d" || { say "  BO QUA (khong phai worktree phu that) ${d#$CM/}"; continue; }
  head=$(git -C "$d" rev-parse HEAD 2>/dev/null || true)
  nb=$(git -C "$d" for-each-ref --contains "$head" --format='%(refname)' refs/heads refs/remotes 2>/dev/null | grep -c . || true)
  [ "${nb:-0}" -ge 1 ] || { say "  BO QUA (commit ${head:0:8} khong thuoc nhanh nao — xoa se mat lich su) ${d#$CM/}"; continue; }
  all=$(git -C "$d" status --porcelain --ignored=no 2>/dev/null)
  other=$(grep -v 'PrivateConfig' <<< "$all" | grep -c . || true); npc=$(grep -c 'PrivateConfig' <<< "$all" || true)
  if [ "${other:-0}" != 0 ]; then say "  BO QUA ($other file chua commit ngoai PrivateConfig) ${d#$CM/}"; continue; fi
  FORCE=(); [ "${npc:-0}" != 0 ] && FORCE=(--force)
  s=$(dsz "$d"); add 1d "$s"
  FS=${FORCE[*]:+--force }
  if [ "$APPLY" = 1 ]; then git -C "$d" worktree remove "${FORCE[@]}" -- "$d" || fail "git worktree remove $FS$d"; say "  DA worktree remove $FS${d#$CM/} ($(gb "$s"))"
  else say "  SE git worktree remove $FS${d#$CM/} ($(gb "$s"), commit ${head:0:8} thuoc $nb nhanh${FS:+, chi PrivateConfig chua commit})"; fi
done
# ================================================================ PHA 1e: scratch A1 tu 11-05
say "--- PHA 1e: scratch A1 tu 11-05 trong v12/ (CHI a1*_fake*; khong git; cu hon 24 h; GIU bang chung _adv/_log/_drylog/_gates/_parity)"
while IFS= read -r -d '' d; do
  b=$(basename -- "$d")
  case "$b" in a1*_gates*|a1*_parity*|a1*_adv*|a1*_log*|a1*_drylog*|a1_*) say "  BO QUA (bang chung A1 / ten giu) $b"; continue;; esac
  guard "$d"
  if git -C "$d" rev-parse --is-inside-work-tree >/dev/null 2>&1 || [ -n "$(find "$d" -name .git -print -quit)" ]; then say "  BO QUA (co git) $b"; continue; fi
  newest=$(find "$d" -type f -printf '%TY-%Tm-%Td\n' 2>/dev/null | sort | tail -1)
  [ -n "$newest" ] || { say "  BO QUA (rong) $b"; continue; }
  if [[ "$newest" < "2026-11-05" ]]; then say "  BO QUA (truoc 11-05: $newest) $b"; continue; fi
  if [ -n "$(find "$d" -type f -newermt "@$((NOW_S - 86400))" -print -quit 2>/dev/null)" ]; then say "  BO QUA (co file < 24 h — co the dang dung) $b"; continue; fi
  s=$(dsz "$d"); add 1e "$s"
  if [ "$APPLY" = 1 ]; then rm -rf -- "$(realpath -e -- "$d")" || fail "rm $d"; say "  DA xoa $b ($(gb "$s"))"
  else say "  SE xoa $b ($(gb "$s"), moi nhat $newest)"; fi
done < <(find "$CM/v12" -mindepth 1 -maxdepth 1 -type d -name 'a1*_fake*' -print0 | sort -z)
# ================================================================ PHA 1f: file trung gian parity
say "--- PHA 1f: file trung gian parity ($PF_NAMES) cua ngay da DONE va cu hon 3 ngay"
LIM=$(date -d "@$((NOW_S - 3 * 86400))" +%F)
for r in "${PF_ROOTS[@]}"; do
  [ -d "$r/d" ] || { say "  BO QUA (khong co) ${r#$CM/}/d"; continue; }
  for dd in "$r"/d/*/; do
    dd=${dd%/}; day=$(basename -- "$dd")
    [[ "$day" =~ ^20[0-9]{2}-[0-9]{2}-[0-9]{2}$ ]] || continue
    dn=""; for n in WATCH_DONE DONE; do [ -f "$dd/$n" ] && { dn=$dd/$n; break; }; done
    [ -n "$dn" ] || { say "  BO QUA (chua DONE) ${dd#$CM/}"; continue; }
    if [[ ! "$day" < "$LIM" ]] || [ -n "$(find "$dn" -newermt "@$((NOW_S - 3 * 86400))" -print -quit)" ]; then say "  BO QUA (< 3 ngay) ${dd#$CM/}"; continue; fi
    s0=0; nf=0
    while IFS= read -r -d '' f; do
      guard_pf "$f"; s=$(stat -c %s -- "$f"); s0=$((s0 + s)); nf=$((nf + 1)); add 1f "$s"
      if [ "$APPLY" = 1 ]; then rm -f -- "$(realpath -e -- "$f")" || fail "rm $f"; fi
    done < <(find "$dd" -type f \( -name closes_cache.pkl -o -name holes.csv \) -print0 | sort -z)
    [ "$nf" = 0 ] || say "  $([ "$APPLY" = 1 ] && echo DA || echo SE) xoa ${dd#$CM/}: $nf file ($(gb "$s0"))"
  done
done
# ================================================================ PHA 1g: target/ build Maven
say "--- PHA 1g: thu muc build Maven 'target' (classes/ hoac maven-status/) duoi claude_master, shadow_c3, shadow_c3b, src*"
JARMD5=$(find "$CM/v12/jar" -maxdepth 1 -type f -name 'binance-java-sdk-*' -print0 2>/dev/null | xargs -0 -r md5sum | cut -c1-32 | sort -u)
OPEN=$(for p in /proc/[0-9]*; do readlink "$p/cwd" 2>/dev/null; ls -l "$p/fd" 2>/dev/null | sed -n 's/.* -> //p'; tr '\0' '\n' < "$p/cmdline" 2>/dev/null; done | grep '/target' | sort -u)
TGROOTS=("$CM"); for r in "$H/shadow_c3" "$H/shadow_c3b" "$H"/src "$H"/src[_-]*; do [ -d "$r" ] && TGROOTS+=("$r"); done
while IFS= read -r -d '' t; do
  rt=$(realpath -e -- "$t" 2>/dev/null) || continue
  case "$rt" in "$CM"/v12/wt_r4u/*|"$CM"/v12/wt_r4u_final/*|"$CM"/v12/wt_r4u2/*) say "  BO QUA (da tinh trong 1d) ${rt#$H/}"; continue;; esac
  [ -d "$rt/classes" ] || [ -d "$rt/maven-status" ] || { say "  BO QUA (khong co classes/ maven-status/ — co the la du lieu) ${rt#$H/}"; continue; }
  den=""; for f in "${TG_DENY[@]}"; do case "$rt" in "$f"|"$f"/*) den=$f;; esac; done
  [ -z "$den" ] || { say "  BO QUA (vung giu ${den#$H/}) ${rt#$H/}"; continue; }
  if grep -qF -- "$rt" <<< "$OPEN"; then say "  BO QUA (process dang dung file trong) ${rt#$H/}"; continue; fi
  ref=""; while IFS= read -r -d '' j; do
    m=$(md5sum < "$j" | cut -c1-32)
    if grep -qx "$m" <<< "$KEEPS"$'\n'"$KEEPMD5" && ! grep -qx "$m" <<< "$JARMD5"; then ref="$(basename -- "$j") ${m:0:8}"; break; fi
  done < <(find "$rt" -maxdepth 1 -type f -name '*.jar' -print0 2>/dev/null)
  [ -z "$ref" ] || { say "  BO QUA (jar $ref duoc tham chieu, KHONG co ban trong v12/jar) ${rt#$H/}"; continue; }
  guard_tg "$rt"
  s=$(dsz "$rt"); add 1g "$s"
  if [ "$APPLY" = 1 ]; then rm -rf -- "$rt" || fail "rm $rt"; say "  DA xoa ${rt#$H/} ($(gb "$s"))"
  else say "  SE xoa ${rt#$H/} ($(gb "$s"))"; fi
done < <(find "${TGROOTS[@]}" -maxdepth 6 -type d -name target -not -path '*/node_modules/*' -prune -print0 2>/dev/null | sort -z)
# ================================================================ PHA 1h: log shadow cu
say "--- PHA 1h: log shadow_c3 / shadow_c3b (app/logs) cu hon 7 ngay"
for sd in "$H/shadow_c3/app/logs" "$H/shadow_c3b/app/logs"; do
  [ -d "$sd" ] || { say "  BO QUA (khong co) ${sd#$H/}"; continue; }
  s0=0; nf=0
  while IFS= read -r -d '' f; do
    guard_sl "$f"; s=$(stat -c %s -- "$f"); s0=$((s0 + s)); nf=$((nf + 1)); add 1h "$s"
    if [ "$APPLY" = 1 ]; then rm -f -- "$(realpath -e -- "$f")" || fail "rm $f"; fi
  done < <(find "$sd" -type f ! -name '*.jar' -mtime +7 -print0 2>/dev/null | sort -z)
  say "  $([ "$APPLY" = 1 ] && echo DA || echo SE) xoa ${sd#$H/}: $nf file log > 7 ngay ($(gb "$s0"))"
done
say "=== PHA 1: $([ "$APPLY" = 1 ] && echo 'da giai phong' || echo 'du kien') $(gb "$P1") | $(for k in 1a 1b 1c 1d 1e 1f 1g 1h; do printf '%s=%s ' "$k" "$(gb "${G[$k]:-0}")"; done)"
# ================================================================ PHA 2: whitelist cung
say "--- PHA 2: nen WHITELIST cung (1006)"
for d in "$CM/1006"; do
  [ -d "$d" ] || { say "  BO QUA (khong co / da nen) $d"; continue; }
  guard "$d"
  if [ -n "$(find "$d" -name .git -print -quit)" ] || git -C "$d" rev-parse --is-inside-work-tree >/dev/null 2>&1; then fail "$d chua .git/worktree — pha 2 khong bao gio dung"; fi
  n=$(basename -- "$d"); s=$(dsz "$d"); nf=$(find "$d" -type f | wc -l)
  if [ "$APPLY" = 0 ]; then say "  SE nen $n ($(gb "$s"), $nf file) -> archive/$n.tar.zst roi xoa ban goc sau khi kiem"; P2=$((P2 + s)); continue; fi
  mem=$(free -m | awk '/^Mem:/{print $7}'); avail=$(df -B1 --output=avail / | tail -1 | tr -dc 0-9)
  [ "$mem" -ge 4000 ] || fail "free ${mem} MB < 4000 truoc $n"
  need=$(( s > 5368709120 ? s : 5368709120 )); [ "$avail" -ge "$need" ] || fail "dia trong $(gb "$avail") < $(gb "$need") truoc $n"
  mkdir -p "$ARC"; out="$ARC/$n.tar.zst"
  [ -e "$out" ] && fail "da co $out — kiem tay"
  flock -w 3600 "$LOCK" nice -n 10 bash -c '
    set -euo pipefail
    tar -C "$1" -cf - "$2" | zstd -q -T2 -o "$3.tmp"
    zstd -q -t -- "$3.tmp"
    na=$(zstd -q -dc -- "$3.tmp" | tar -tvf - | grep -c "^-" || true)
    [ "$na" = "$4" ] || { echo "so file lech: goc $4, archive $na"; exit 1; }
    mv -f -- "$3.tmp" "$3"' _ "$(dirname "$d")" "$n" "$out" "$nf" || { rm -f -- "$out.tmp"; fail "nen/kiem $n loi"; }
  rm -rf -- "$(realpath -e -- "$d")" || fail "xoa goc $n"
  zs=$(stat -c %s -- "$out"); P2=$((P2 + s - zs))
  say "  DA nen $n: $(gb "$s") -> $(gb "$zs") ($nf file khop)"
done
say "=== PHA 2: $([ "$APPLY" = 1 ] && echo 'da giai phong' || echo 'du kien (truoc nen)') $(gb "$P2")"
say "df SAU: $(df -h / | tail -1)"
say "Goi y (owner tu chay, can sudo; script KHONG chay): sudo journalctl --vacuum-size=200M   (journal hien: $(journalctl --disk-usage 2>/dev/null | grep -oE '[0-9.]+[KMGT]' | tail -1))"
say "Log: $LOG"
