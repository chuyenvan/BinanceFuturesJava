#!/usr/bin/env bash
# =============================================================================
# cleanup_oracle_disk.sh v6 — don dia ORACLE (/dev/sda1). MAC DINH DRY; --apply chay pha 1 roi pha 2.
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
#   g) [v4 A1 MAJ] 'target' Maven CHI trong WHITELIST cung worktree da xong viec (TG_WL: worktree audit A1 v12/a1*, ing1030/a1_wt*,
#      wt_r4u, wt_r4u_final, wt_r4u2) — KHONG quet toan bo (v3 da tinh xoa nham wt_t2c/target (r1_t2a.sh dung test-classes) va
#      src_wt_bcd/target (sim.jar ec01b7c0 cua burst_cooldown_driver.py)). Moi muc van phai: co classes/ hoac maven-status/;
#      KHONG bi tham chieu trong *.sh/*.py cua ~/claude_master ~/ops ~/tools ~/kaggle_sim va crontab (grep loi => ABORT);
#      /proc khong co process mo file/cwd/cmdline trong do (khong doc duoc /proc cua chinh user => ABORT); jar co md5 duoc tham
#      chieu ma khong co ban trong v12/jar => LOAI. Worktree build cu vong 3c..r4s: khong con worktree nao (da kiem 11-11).
#   h) [v3] log shadow_c3 / shadow_c3b (shadow tat 11-03): file trong */app/logs/ cu hon 7 ngay. KHONG dung storage/data, jar.
#   i) [v5] ban sao nghien cuu trong res1109 (vung CAM DUNG — ngoai le DUNG tung duong dan; ket qua da commit vz_e1_wt a5ff7c9f,
#      nguon con tren Kaggle): r1_s1/{a2_bins,a3_bins,g015x26}, r3_gate/{jar,jar_m,jar_q,jar_s,asdump,ds_as,ds_as2,pred},
#      r3_gate/orch_m2r/ds_sim-jar-*, r5_quality/sig_*.npz. CHI xoa file .bin/.jar/.npz/.gz/.gzdat trong do; GIU json/md/py/log/
#      sh/txt/properties/sha256. GIU tuyet doi: r1_s1/kl, r3_wt, 1004/gqd/cand_base.npz, file .sh co key/token (khong bao gio khop).
#      Van kiem: grep script/crontab tham chieu (loi => ABORT), /proc mo file.
#   KHONG dua vao: pull242 cu, kaggle_sim, aerospike-data. Cuoi script IN goi y 'sudo journalctl --vacuum-size=200M' (khong chay).
# PHA 2 (NEN LOSSLESS) [v6]: WHITELIST CUNG = 1006 + audit_1030b + ~/net015_repro + ~/kg015x26_2021 (kiem ke v12/CLEANUP_V6_DEV.md muc 1).
#   Muc whitelist trung FORBID (neu co) chi duoc mien FORBID cho pha 2; pha 1 van cam. Tu nho den lon; MOI thu muc trong 1 lan
#   'flock -w 3600 oracle_heavy.lock nice -n 10' (khong long): kiem lai (.git => ABORT, symlink => ABORT, muc moi >= 2026-11-01 => BO QUA,
#   grep tham chieu crontab + *.sh/py/properties/json/yaml/yml/java/md5/ok trong claude_master ops tools kaggle_sim java src* + file cap 1
#   cua ~ + systemd user (loi => ABORT; co => BO QUA; docs/*.md|json chi ghi log), /proc => BO QUA), free >= 4000 MB, dia >= max(5 GB,
#   kich thuoc); tar | zstd -3 -T2 -> archive/<ten>.tar.zst.part; zstd -t; so file thuong + tong byte (tar -tv) voi find goc truoc+sau;
#   .sha256 + .manifest.tsv; .part -> .tar.zst; CHI khi khop moi rm -rf goc. Lech => xoa .part, giu goc, exit 1 cuoi script.
#   Da co archive cung ten => BO QUA. Dia trong < 15.3 GiB truoc/sau bat ky thu muc nao => DUNG pha 2. DRY in bang GB thu uoc.
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
say "=== cleanup_oracle_disk v6 APPLY=$APPLY (cam dung: ${#FORBID[@]} muc) ==="
say "df TRUOC: $(df -h / | tail -1)"
P1=0; P2=0; declare -A G=(); D_PLAN=()   # D_PLAN: worktree 1c/1d se go ca thu muc (1g bo qua de khong tinh 2 lan)
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
  s=$(dsz "$d"); add 1c "$s"; D_PLAN+=("$d")
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
  s=$(dsz "$d"); add 1d "$s"; D_PLAN+=("$d")
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
say "--- PHA 1g: 'target' Maven trong WHITELIST worktree da xong viec (khong quet toan bo)"
TG_WL=()
for w in "$CM"/v12/a1 "$CM"/v12/a1_* "$CM"/ing1030/a1_wt*; do [ -d "$w" ] && [ ! -L "$w" ] && TG_WL+=("$w"); done
TG_WL+=("$CM/v12/wt_r4u" "$CM/v12/wt_r4u_final" "$CM/v12/wt_r4u2")
JARMD5=$(find "$CM/v12/jar" -maxdepth 1 -type f -name 'binance-java-sdk-*' -print0 2>/dev/null | xargs -0 -r md5sum | cut -c1-32 | sort -u)
# /proc: fail-closed. Process CUA USER NAY phai doc duoc cwd + fd (bien mat giua chung thi bo qua); process user khac: cmdline (+cwd/fd neu doc duoc).
NPROC=0; NOWN=0; NOTHER=0; NSKIP=0; UIDME=$(id -u); OPENF=$(mktemp); trap 'rm -f "$OPENF" "${GREPF:-}" "${PATF:-}"' EXIT
for p in /proc/[0-9]*; do
  [ -d "$p" ] || continue; NPROC=$((NPROC + 1))
  pu=$(stat -c %u "$p" 2>/dev/null) || continue
  if [ "$pu" = "$UIDME" ]; then
    if c=$(readlink "$p/cwd" 2>/dev/null) && fl=$(ls -l "$p/fd" 2>/dev/null); then
      { echo "$c"; sed -n 's/.* -> //p' <<< "$fl"; tr '\0' '\n' < "$p/cmdline" 2>/dev/null; } >> "$OPENF"; NOWN=$((NOWN + 1))
    elif [ -d "$p" ]; then
      cm=$(cat "$p/comm" 2>/dev/null || true)
      case "$cm" in "(sd-pam)"|sshd) NSKIP=$((NSKIP + 1));;   # khong-dumpable co chu dich (PAM / phien ssh), khong mo file build
        *) [ -d "$p" ] && fail "/proc: khong doc duoc cwd/fd cua process cung user pid $(basename "$p") comm=$cm — fail-closed";; esac
    fi
  else
    { readlink "$p/cwd" 2>/dev/null; ls -l "$p/fd" 2>/dev/null | sed -n 's/.* -> //p'; tr '\0' '\n' < "$p/cmdline" 2>/dev/null; } >> "$OPENF" || true
    NOTHER=$((NOTHER + 1))
  fi
done
[ "$NPROC" -ge 5 ] && [ "$NOWN" -ge 1 ] || fail "/proc: liet ke duoc $NPROC process ($NOWN cua user nay) — khong tin duoc, fail-closed"
say "  /proc: $NPROC process ($NOWN cua user nay doc du cwd/fd; $NSKIP sd-pam/sshd khong doc duoc (bo qua co ly do); $NOTHER user khac: cmdline + phan doc duoc)"
# grep tham chieu: *.sh/*.py trong claude_master, ops, tools, kaggle_sim + crontab. Loi (rc 2) => ABORT.
PATF=$(mktemp); for w in "${TG_WL[@]}"; do echo "${w#$CM/}/target"; done > "$PATF"   # vd v12/a1_r4i/target (khop $CM/..., ~/claude_master/..., tuyet doi)
GREPF=$(mktemp); GD=(); for r in "$CM" "$H/ops" "$H/tools" "$H/kaggle_sim"; do [ -d "$r" ] && GD+=("$r"); done
set +e
grep -rhoF --include='*.sh' --include='*.py' --exclude=cleanup_oracle_disk.sh --exclude=test_cleanup_oracle_disk.sh -f "$PATF" "${GD[@]}" > "$GREPF" 2>"$GREPF.err"; grc=$?
CT=$(crontab -l 2>&1); crc=$?
set -e
if [ "$grc" -gt 1 ]; then say "  grep loi: $(head -3 "$GREPF.err" | tr '\n' ' ')"; rm -f "$GREPF.err"; fail "grep tham chieu loi (rc=$grc) — fail-closed"; fi
rm -f "$GREPF.err"
if [ "$crc" != 0 ] && ! grep -qi 'no crontab' <<< "$CT"; then fail "crontab -l loi (rc=$crc) — fail-closed"; fi
grep -oF -f "$PATF" <<< "$CT" >> "$GREPF" || true
for w in "${TG_WL[@]}"; do
  rt=$w/target; rel=${rt#$CM/}
  [ -e "$rt" ] || continue
  [ -L "$rt" ] && fail "target la symlink: $rt"
  for d in "${D_PLAN[@]}"; do [ "$d" = "$w" ] && { say "  BO QUA (worktree ${w#$CM/} da go nguyen o 1c/1d) $rel"; continue 2; }; done
  [ -d "$rt/classes" ] || [ -d "$rt/maven-status" ] || { say "  BO QUA (khong co classes/ maven-status/) $rel"; continue; }
  if grep -qxF -- "$rel" "$GREPF"; then say "  BO QUA (co script/crontab tham chieu '$rel') $rel"; continue; fi
  if grep -qF -- "$rt" "$OPENF"; then say "  BO QUA (process dang dung file / cwd / cmdline trong) $rel"; continue; fi
  ref=""; while IFS= read -r -d '' j; do
    m=$(md5sum < "$j" | cut -c1-32)
    if grep -qx "$m" <<< "$KEEPS"$'\n'"$KEEPMD5" && ! grep -qx "$m" <<< "$JARMD5"; then ref="$(basename -- "$j") ${m:0:8}"; break; fi
  done < <(find "$rt" -maxdepth 1 -type f -name '*.jar' -print0 2>/dev/null)
  [ -z "$ref" ] || { say "  BO QUA (jar $ref duoc tham chieu, KHONG co ban trong v12/jar) ${rt#$H/}"; continue; }
  guard_tg "$rt"
  s=$(dsz "$rt"); add 1g "$s"
  if [ "$APPLY" = 1 ]; then rm -rf -- "$rt" || fail "rm $rt"; say "  DA xoa ${rt#$H/} ($(gb "$s"))"
  else say "  SE xoa ${rt#$H/} ($(gb "$s"))"; fi
done
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
# ================================================================ PHA 1i: ban sao nghien cuu res1109 (WHITELIST cung tung duong dan)
say "--- PHA 1i: ban sao nghien cuu res1109 (ket qua da commit vz_e1_wt a5ff7c9f; nguon con tren Kaggle — R3 xac nhan)"
RS=$CM/res1109
RS_WL=("$RS/r1_s1/a2_bins" "$RS/r1_s1/a3_bins" "$RS/r1_s1/g015x26" "$RS/r3_gate/jar" "$RS/r3_gate/jar_m" "$RS/r3_gate/jar_q" "$RS/r3_gate/jar_s"
       "$RS/r3_gate/asdump" "$RS/r3_gate/ds_as" "$RS/r3_gate/ds_as2" "$RS/r3_gate/pred")
for w in "$RS"/r3_gate/orch_m2r/ds_sim-jar-*; do [ -d "$w" ] && [ ! -L "$w" ] && RS_WL+=("$w"); done
RS_EXT='bin|jar|npz|gz|gzdat'   # CHI xoa file nhi phan; GIU json/md/py/log/sh/txt/properties/sha256/... (moi thu khac)
RS_KEEP=("$RS/r1_s1/kl" "$CM/1004/gqd/cand_base.npz" "$CM/r3_wt")
guard_rs() {   # $1 file: file thuong, khong symlink, duoi trong RS_EXT, nam trong DUNG 1 muc RS_WL hoac la $RS/r5_quality/sig_*.npz
  local rp ok=0 w f
  [ -L "$1" ] && fail "symlink: $1"; rp=$(realpath -e -- "$1") || fail "khong ton tai: $1"; [ -f "$rp" ] || fail "khong phai file: $rp"
  [[ "$(basename -- "$rp")" =~ \.($RS_EXT)$ ]] || fail "duoi khong cho phep: $rp"
  for w in "${RS_WL[@]}"; do case "$rp" in "$w"/*) ok=1;; esac; done
  [[ "$rp" =~ ^"$RS"/r5_quality/sig_[^/]*\.npz$ ]] && ok=1
  [ "$ok" = 1 ] || fail "ngoai whitelist 1i: $rp"
  for f in "${RS_KEEP[@]}"; do case "$rp" in "$f"|"$f"/*) fail "GIU tuyet doi: $rp";; esac; done
  for f in "${FORBID[@]}"; do [ "$f" = "$RS" ] && continue; case "$rp" in "$f"|"$f"/*) fail "CAM DUNG: $rp (thuoc $f)";; esac; done
}
PATF2=$(mktemp); { for w in "${RS_WL[@]}"; do echo "${w#$CM/}"; done; echo "res1109/r5_quality/sig_"; } > "$PATF2"
set +e
grep -rhoF --include='*.sh' --include='*.py' --exclude=cleanup_oracle_disk.sh --exclude=test_cleanup_oracle_disk.sh -f "$PATF2" "${GD[@]}" > "$PATF2.hit" 2>"$PATF2.err"; grc=$?
set -e
if [ "$grc" -gt 1 ]; then say "  grep loi: $(head -3 "$PATF2.err" | tr '\n' ' ')"; rm -f "$PATF2" "$PATF2.hit" "$PATF2.err"; fail "grep tham chieu 1i loi (rc=$grc) — fail-closed"; fi
grep -oF -f "$PATF2" <<< "$CT" >> "$PATF2.hit" || true
rs_one() {   # $1 nhan (duong dan tuong doi $CM), $2.. file
  local rel=$1; shift; local s0=0 nf=0 f s
  if grep -qxF -- "$rel" "$PATF2.hit"; then say "  BO QUA (co script/crontab tham chieu '$rel')"; return 0; fi
  if grep -qF -- "$CM/$rel" "$OPENF"; then say "  BO QUA (process dang dung file trong $rel)"; return 0; fi
  for f in "$@"; do guard_rs "$f"; s=$(stat -c %s -- "$f"); s0=$((s0 + s)); nf=$((nf + 1)); add 1i "$s"
    if [ "$APPLY" = 1 ]; then rm -f -- "$(realpath -e -- "$f")" || fail "rm $f"; fi; done
  [ "$nf" = 0 ] || say "  $([ "$APPLY" = 1 ] && echo DA || echo SE) xoa $rel: $nf file nhi phan ($(gb "$s0")); giu json/md/log/..."
}
for w in "${RS_WL[@]}"; do
  [ -d "$w" ] || { say "  BO QUA (khong co) ${w#$CM/}"; continue; }
  [ -L "$w" ] && fail "whitelist la symlink: $w"
  mapfile -d '' FL < <(find "$w" -type f -regextype posix-extended -regex ".*\.($RS_EXT)$" -print0 | sort -z)
  rs_one "${w#$CM/}" "${FL[@]}"
done
mapfile -d '' FL < <(find "$RS/r5_quality" -maxdepth 1 -type f -name 'sig_*.npz' -print0 2>/dev/null | sort -z)
[ "${#FL[@]}" = 0 ] || rs_one "res1109/r5_quality/sig_" "${FL[@]}"
rm -f "$PATF2" "$PATF2.hit" "$PATF2.err"
say "=== PHA 1: $([ "$APPLY" = 1 ] && echo 'da giai phong' || echo 'du kien') $(gb "$P1") | $(for k in 1a 1b 1c 1d 1e 1f 1g 1h 1i; do printf '%s=%s ' "$k" "$(gb "${G[$k]:-0}")"; done)"
# ================================================================ PHA 2 [v6]: nen LOSSLESS whitelist cung (tu nho den lon)
# Moi thu muc: KIEM LAI toan bo tieu chi + nen + kiem + xoa goc trong MOT lan 'flock -w 3600 oracle_heavy.lock nice -n 10' (khong long).
# Kiem ke + ly do chon: ~/claude_master/v12/CLEANUP_V6_DEV.md muc 1 (1003/1005/1009/1012/1013/1016... LOAI: con tham chieu / co .git).
P2_WL=("$CM/1006" "$CM/audit_1030b" "$H/net015_repro" "$H/kg015x26_2021")
declare -A P2_RATIO=([1006]=1.00 [audit_1030b]=0.53 [net015_repro]=0.25 [kg015x26_2021]=0.23)   # ti le zstd -3 uoc tu mau - CHI de in DRY
P2_DENY_H="aerospike-data collect java kaggle_sim vz vz_e1 wfo_ds_x1_2021 ops ledger .openclaw envs xgb-env .local .npm-global sel_models_net015 val_pred_net015 predwf_G015_v2 predwf_t1_f4 claude_master tools"
P2_DENY_C="pull242 parity_v11w parity_v12w vz_e1_wt v12 w3 gvz deploy locks health242 res1109 r3_wt e2e1105 ing1030 archive cleanup_logs 1004"
P2_CUT="2026-11-01"
P2_MINFREE=16428249907   # 15.3 GiB: R-LIVE can dia trong >= 15.3 GB; duoi nguong sau bat ky buoc nao => DUNG pha 2
if [ -n "${CLEAN_H:-}" ]; then P2_MINFREE=${CLEAN_P2_MINFREE:-$P2_MINFREE}; fi   # chi sandbox test
p2_res() { printf '%s\t%s\t%s\t%s\t%s\n' "$@" >> "$P2_RES"; }   # ten trang_thai byte_goc so_file byte_thu
guard_p2() {   # $1: DUNG 1 muc P2_WL; thu muc that (khong symlink); cap 1 duoi $CM hoac $H; khong LOAI CUNG; FORBID chi mien muc TRUNG chinh no
  local d=$1 rp f n par ok=0
  for f in "${P2_WL[@]}"; do if [ "$f" = "$d" ]; then ok=1; fi; done
  [ "$ok" = 1 ] || fail "pha 2: ngoai whitelist: $d"
  [ -L "$d" ] && fail "pha 2: symlink: $d"
  rp=$(realpath -e -- "$d") || fail "khong ton tai: $d"
  [ "$rp" = "$d" ] || fail "pha 2: realpath khac: $d -> $rp"
  [ -d "$rp" ] || fail "pha 2: khong phai thu muc: $rp"
  n=$(basename -- "$rp"); par=$(dirname -- "$rp")
  [ "$par" = "$CM" ] || [ "$par" = "$H" ] || fail "pha 2: khong phai cap 1 duoi ~ hoac claude_master: $rp"
  case "$n" in .*|src*|shadow_c3*) fail "pha 2: LOAI CUNG: $rp";; esac
  if [ "$par" = "$H" ]; then case " $P2_DENY_H " in *" $n "*) fail "pha 2: LOAI CUNG: $rp";; esac
  else case " $P2_DENY_C " in *" $n "*) fail "pha 2: LOAI CUNG: $rp";; esac; fi
  for f in "${FORBID[@]}"; do
    [ "$f" = "$rp" ] && continue   # mien FORBID CHI cho pha 2 (nen) cua dung muc nay; pha 1 van cam
    case "$rp" in "$f"/*) fail "CAM DUNG: $rp (thuoc $f)";; esac
    case "$f" in "$rp"/*) fail "CAM DUNG: $rp chua $f";; esac
  done
}
p2_proc() {   # $1 thu muc. rc 0 = khong process nao dung; 10 = co (cwd/fd/cmdline). Fail-closed nhu 1g.
  local d=$1 p pu c fl cm of np=0 nown=0 uid
  uid=$(id -u); of=$(mktemp)
  for p in /proc/[0-9]*; do
    [ -d "$p" ] || continue; np=$((np + 1))
    pu=$(stat -c %u "$p" 2>/dev/null) || continue
    if [ "$pu" = "$uid" ]; then
      if c=$(readlink "$p/cwd" 2>/dev/null) && fl=$(ls -l "$p/fd" 2>/dev/null); then
        { echo "$c"; sed -n 's/.* -> //p' <<< "$fl"; tr '\0' '\n' 2>/dev/null < "$p/cmdline" || true; } >> "$of" 2>/dev/null; nown=$((nown + 1))
      elif [ -d "$p" ]; then
        cm=$(cat "$p/comm" 2>/dev/null || true)
        case "$cm" in "(sd-pam)"|sshd) ;;
          *) if [ -d "$p" ]; then rm -f "$of"; fail "/proc: khong doc duoc cwd/fd cua process cung user pid ${p#/proc/} comm=$cm - fail-closed"; fi;; esac
      fi
    else
      { readlink "$p/cwd" 2>/dev/null; ls -l "$p/fd" 2>/dev/null | sed -n 's/.* -> //p'; tr '\0' '\n' 2>/dev/null < "$p/cmdline"; } >> "$of" 2>/dev/null || true
    fi
  done
  if [ "$np" -lt 5 ] || [ "$nown" -lt 1 ]; then rm -f "$of"; fail "/proc: liet ke duoc $np process ($nown cua user nay) - fail-closed"; fi
  if grep -qF -- "$d" "$of"; then rm -f "$of"; return 10; fi
  rm -f "$of"; return 0
}
p2_refs() {   # $1 thu muc. rc 0 = khong tham chieu; 10 = co. grep / crontab loi => ABORT.
  local d=$1 n ne he p hits err f nb=0 g1 g2 ct crc s R=() HF=()
  n=$(basename -- "$d"); ne=$(sed 's/[][\.*^$+?(){}|]/\\&/g' <<< "$n")
  case "$d" in
    "$CM"/*) p="claude_master/$ne([^A-Za-z0-9_-]|\$)";;
    *) he=$(sed 's/[][\.*^$+?(){}|]/\\&/g' <<< "$H"); p="($he|~|[\$]HOME|[\$][{]HOME[}])/$ne([^A-Za-z0-9_-]|\$)";;
  esac
  for s in "$CM" "$H/ops" "$H/tools" "$H/kaggle_sim" "$H/java" "$H"/src*; do if [ -d "$s" ] && [ ! -L "$s" ]; then R+=("$s"); fi; done
  mapfile -d '' HF < <(find "$H" -maxdepth 1 -type f \( -name '*.sh' -o -name '*.py' -o -name '*.properties' -o -name '*.json' -o -name '*.yaml' \
      -o -name '*.yml' -o -name '*.java' -o -name '*.md5' -o -name '*.ok' -o -name .bashrc -o -name .profile -o -name .bash_profile \) \
      ! -name '*.env' ! -name 'env.local' ! -name 'PrivateConfig*' ! -name 'keys*' ! -name 'env.sh' ! -name 'kaggle.json' ! -name 'chd_env.sh' \
      ! -name 'cleanup_oracle_disk.sh' ! -name 'test_cleanup_oracle_disk.sh' -print0
    if [ -d "$H/.config/systemd/user" ]; then find "$H/.config/systemd/user" -type f -print0; fi)
  hits=$(mktemp); err=$(mktemp)
  set +e
  grep -rlE --exclude-dir=.git --include='*.sh' --include='*.py' --include='*.properties' --include='*.json' --include='*.yaml' --include='*.yml' \
    --include='*.java' --include='*.md5' --include='*.ok' --exclude='*.env' --exclude='tg.env' --exclude='env.local' --exclude='PrivateConfig*' \
    --exclude='keys*' --exclude='env.sh' --exclude='kaggle.json' --exclude='chd_env.sh' --exclude=cleanup_oracle_disk.sh --exclude=test_cleanup_oracle_disk.sh \
    -e "$p" "${R[@]}" > "$hits" 2> "$err"; g1=$?
  g2=1; if [ "${#HF[@]}" -gt 0 ]; then grep -lE -e "$p" -- "${HF[@]}" >> "$hits" 2>> "$err"; g2=$?; fi
  ct=$(crontab -l 2>&1); crc=$?
  set -e
  if [ "$g1" -gt 1 ] || [ "$g2" -gt 1 ]; then say "  grep loi: $(head -3 "$err" | tr '\n' ' ')"; rm -f "$hits" "$err"; fail "grep tham chieu pha 2 loi (rc=$g1/$g2) - fail-closed"; fi
  if [ "$crc" != 0 ] && ! grep -qi 'no crontab' <<< "$ct"; then rm -f "$hits" "$err"; fail "crontab -l loi (rc=$crc) - fail-closed"; fi
  while IFS= read -r f; do
    case "$f" in "$d"/*) continue;; esac                                                  # file trong chinh thu muc
    case "$f" in */docs/*.md|*/docs/*.json) say "    ghi chep docs (khong chan): $f"; continue;; esac
    nb=$((nb + 1)); if [ "$nb" -le 5 ]; then say "    tham chieu: $f"; fi
  done < "$hits"
  if [ "$crc" = 0 ] && grep -qE -e "$p" <<< "$ct"; then nb=$((nb + 1)); say "    tham chieu: crontab"; fi
  rm -f "$hits" "$err"
  if [ "$nb" = 0 ]; then return 0; fi
  if [ "$nb" -gt 5 ]; then say "    ... tong $nb nguon tham chieu"; fi
  return 10
}
p2_pack() {   # $1 thu muc, $2 .part, $3 so file thuong, $4 tong byte (find truoc nen). Moi buoc loi => return 1 (KHONG xoa goc).
  local d=$1 part=$2 nf=$3 sb=$4 n par v na sa nf2 sb2 h out
  n=$(basename -- "$d"); par=$(dirname -- "$d"); out=${part%.part}
  rm -f -- "$part" "$part.manifest" "$part.sha256" || return 1
  tar -C "$par" -cf - -- "$n" | zstd -q -3 -T2 -o "$part" || { say "    tar | zstd loi"; return 1; }
  zstd -q -t -- "$part" || { say "    zstd -t loi"; return 1; }
  v=$(zstd -q -dc -- "$part" | tar -tvf - | awk '$1 ~ /^-/ {n++; t+=$3} END{printf "%d %.0f\n", n+0, t+0}') || { say "    doc lai archive loi"; return 1; }
  read -r na sa <<< "$v"
  v=$(find "$d" -type f -printf '%s\n' | awk '{n++; t+=$1} END{printf "%d %.0f\n", n+0, t+0}') || return 1
  read -r nf2 sb2 <<< "$v"
  if [ "$na" != "$nf" ] || [ "$nf2" != "$nf" ] || [ "$sa" != "$sb" ] || [ "$sb2" != "$sb" ]; then
    say "    LECH: goc truoc $nf file/$sb B, goc sau $nf2 file/$sb2 B, archive $na file/$sa B"; return 1; fi
  find "$d" -type f -printf '%s\t%P\n' | LC_ALL=C sort -t "$(printf '\t')" -k2 > "$part.manifest" || return 1
  [ "$(wc -l < "$part.manifest")" = "$nf" ] || { say "    manifest lech so dong"; return 1; }
  h=$(sha256sum < "$part" | cut -c1-64) || return 1
  [ "${#h}" = 64 ] || return 1
  printf '%s  %s\n' "$h" "$n.tar.zst" > "$part.sha256" || return 1
  mv -f -- "$part.manifest" "$ARC/$n.manifest.tsv" || return 1
  mv -f -- "$part.sha256" "$out.sha256" || return 1
  mv -f -- "$part" "$out" || return 1
  say "    kiem OK: $nf file thuong / $sb B khop (goc truoc = goc sau = archive); sha256 ${h:0:16}"
}
p2_one() {   # env P2_D thu muc, P2_RES file ket qua, P2_R ti le uoc. rc 0 = xong / du kien / bo qua; 30 = kiem lech (giu goc); 40 = DUNG pha 2; khac = ABORT
  local d=$P2_D n out part s nf sb v rc mem avail need est zs
  n=$(basename -- "$d"); out=$ARC/$n.tar.zst; part=$out.part
  if [ ! -e "$d" ] && [ ! -L "$d" ]; then say "  BO QUA (khong co / da nen) $d"; p2_res "$n" BO_QUA_khong_co 0 0 0; return 0; fi
  guard_p2 "$d"
  if [ -e "$out" ]; then say "  BO QUA (da co archive/$n.tar.zst - kiem tay) $d"; p2_res "$n" BO_QUA_da_co_archive 0 0 0; return 0; fi
  if [ -n "$(find "$d" -name .git -print -quit)" ] || git -C "$d" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    fail "$d chua .git/worktree - pha 2 khong bao gio dung"; fi
  v=$(find "$d" -newermt "$P2_CUT" -print -quit)
  if [ -n "$v" ]; then say "  BO QUA (co muc moi >= $P2_CUT: ${v#"$d"/}) $d"; p2_res "$n" BO_QUA_moi 0 0 0; return 0; fi
  rc=0; p2_proc "$d" || rc=$?
  if [ "$rc" = 10 ]; then say "  BO QUA (process dang dung file / cwd / cmdline trong) $d"; p2_res "$n" BO_QUA_process 0 0 0; return 0; fi
  [ "$rc" = 0 ] || fail "p2_proc rc=$rc"
  rc=0; p2_refs "$d" || rc=$?
  if [ "$rc" = 10 ]; then say "  BO QUA (co script/config/crontab tham chieu) $d"; p2_res "$n" BO_QUA_tham_chieu 0 0 0; return 0; fi
  [ "$rc" = 0 ] || fail "p2_refs rc=$rc"
  s=$(du -sb -- "$d" | cut -f1)
  v=$(find "$d" -type f -printf '%s\n' | awk '{n++; t+=$1} END{printf "%d %.0f\n", n+0, t+0}'); read -r nf sb <<< "$v"
  if [ "$APPLY" = 0 ]; then
    est=$(awk -v s="$s" -v r="${P2_R:-1}" 'BEGIN{printf "%.0f", s * (1 - r)}')
    say "  SE nen $n ($(gb "$s"), $nf file, ti le uoc ${P2_R:-1} => thu uoc $(gb "$est")) -> archive/$n.tar.zst (+ .sha256, .manifest.tsv); kiem khop roi moi xoa goc"
    p2_res "$n" SE_nen "$s" "$nf" "$est"; return 0
  fi
  mem=$(free -m | awk '/^Mem:/{print $7}'); avail=$(df -B1 --output=avail "$CM" | tail -1 | tr -dc 0-9)
  if [ "$mem" -lt 4000 ]; then say "  DUNG PHA 2: free ${mem} MB < 4000 truoc $n"; p2_res "$n" DUNG_ram "$s" "$nf" 0; return 40; fi
  need=$(( s > 5368709120 ? s : 5368709120 ))
  if [ "$avail" -lt "$need" ]; then say "  DUNG PHA 2: dia trong $(gb "$avail") < $(gb "$need") truoc $n"; p2_res "$n" DUNG_dia "$s" "$nf" 0; return 40; fi
  mkdir -p "$ARC"
  if ! p2_pack "$d" "$part" "$nf" "$sb"; then
    rm -f -- "$part" "$part.manifest" "$part.sha256"
    say "  LOI nen/kiem $n - da xoa .part, GIU NGUYEN ban goc"; p2_res "$n" LOI_giu_goc "$s" "$nf" 0; return 30
  fi
  rm -rf -- "$d" || fail "xoa goc $n"
  zs=$(stat -c %s -- "$out")
  say "  DA nen $n: $(gb "$s") -> $(gb "$zs") ($nf file khop) + archive/$n.tar.zst.sha256 + archive/$n.manifest.tsv"
  p2_res "$n" DA_nen "$s" "$nf" "$((s - zs))"; return 0
}
say "--- PHA 2 [v6]: nen lossless WHITELIST cung (${#P2_WL[@]} muc) tu nho den lon; kiem lai tieu chi trong 1 lan flock / thu muc; DUNG neu dia trong < $(gb "$P2_MINFREE")"
P2S=$(mktemp); P2_RES=$(mktemp); trap 'rm -f "$OPENF" "${GREPF:-}" "${PATF:-}" "${P2S:-}" "${P2_RES:-}"' EXIT
{ declare -p H CM ARC APPLY P2_CUT FORBID P2_WL P2_DENY_H P2_DENY_C
  declare -f say fail gb p2_res guard_p2 p2_proc p2_refs p2_pack p2_one
  echo 'set -euo pipefail'; echo 'p2_one'; } > "$P2S"
mapfile -t P2_ORD < <(for d in "${P2_WL[@]}"; do if [ -d "$d" ] && [ ! -L "$d" ]; then printf '%s\t%s\n' "$(dsz "$d")" "$d"; else printf '0\t%s\n' "$d"; fi; done | sort -n -k1,1 | cut -f2-)
P2ERR=0
for d in "${P2_ORD[@]}"; do
  av=$(df -B1 --output=avail "$CM" | tail -1 | tr -dc 0-9)
  if [ "$av" -lt "$P2_MINFREE" ]; then
    if [ "$APPLY" = 1 ]; then say "  DUNG PHA 2: dia trong $(gb "$av") < $(gb "$P2_MINFREE") (truoc $(basename -- "$d"))"; break; fi
    say "  CANH BAO (DRY): dia trong $(gb "$av") < $(gb "$P2_MINFREE") - APPLY se DUNG pha 2 tai day"
  fi
  rc=0; r=${P2_RATIO[$(basename -- "$d")]:-1}
  if [ "$APPLY" = 1 ]; then P2_D=$d P2_RES=$P2_RES P2_R=$r flock -w 3600 "$LOCK" nice -n 10 bash "$P2S" || rc=$?
  else P2_D=$d P2_RES=$P2_RES P2_R=$r nice -n 10 bash "$P2S" || rc=$?; fi
  case "$rc" in 0) ;; 30) P2ERR=1;; 40) break;; *) fail "pha 2 $(basename -- "$d"): tien trinh con rc=$rc (ABORT o tren / flock het gio)";; esac
  av=$(df -B1 --output=avail "$CM" | tail -1 | tr -dc 0-9)
  if [ "$APPLY" = 1 ] && [ "$av" -lt "$P2_MINFREE" ]; then say "  DUNG PHA 2: dia trong $(gb "$av") < $(gb "$P2_MINFREE") (sau $(basename -- "$d"))"; break; fi
done
P2_TAG=$([ "$APPLY" = 1 ] && echo 'GB thu thuc' || echo 'GB thu uoc')
say "  BANG PHA 2: ten | GB goc | so file | $P2_TAG | trang thai"
while IFS=$'\t' read -r n st s nf sv; do say "    $n | $(gb "$s") | $nf | $(gb "$sv") | $st"; P2=$((P2 + sv)); done < "$P2_RES"
say "=== PHA 2: $([ "$APPLY" = 1 ] && echo 'da giai phong' || echo 'du kien (uoc theo ti le mau)') $(gb "$P2")"
say "df SAU: $(df -h / | tail -1)"
say "Goi y (owner tu chay, can sudo; script KHONG chay): sudo journalctl --vacuum-size=200M   (journal hien: $(journalctl --disk-usage 2>/dev/null | grep -oE '[0-9.]+[KMGT]' | tail -1))"
say "Log: $LOG"
if [ "$P2ERR" != 0 ]; then say "LOI pha 2: co thu muc nen/kiem lech (da GIU goc) - xem LOI o tren"; exit 1; fi
