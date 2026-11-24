#!/usr/bin/env bash
# =============================================================================
# cleanup_oracle_1124.sh v2 - don dia ORACLE (kiem ke 2026-11-24; v2 sua theo A1_CLEANUP_1124.md). MAC DINH DRY; --apply moi lam.
#   bash ~/claude_master/v12/c3live/ops/c3live/cleanup_oracle_1124.sh              # DRY ca 5 muc
#   bash ~/claude_master/v12/c3live/ops/c3live/cleanup_oracle_1124.sh --apply      # owner chay
#   --only=LIST         chi chay cac muc chon; LIST gom 1 2 2b 3 4 5 5a 5b 5c 5d ('5' = 5a..5d; '2' KHONG gom 2b). Gia tri la => exit 1
#                       Mac dinh: tat ca (1,2,2b,3,4,5).
#   --min-gain-pct=N    (mac dinh 10) CHI nen khi uoc thu (tinh ca hardlink) >= N % kich thuoc (ti le tu mau tar 100 MB dau)
# MUC 1 swap: /swapfile -> 4G, chi khi (swap dang dung + 2000 MB) < RAM available; fstab giu nguyen (cung duong dan).
# MUC 2b parity_v11w/d: XOA THANG thu muc con 2026-MM-DD[_ops] (owner xac nhan v1.1 het gia tri; tong ket da commit vz_e1_wt 09622c01),
#        CHI khi: 268 file docs/result/parity_v11_daily_* tracked + sach; khong process dung d; khong co watch_daily.sh (v1.1); manifest
#        archive/parity_v11w_d_manifest_<ts>.txt truoc khi xoa. GIU d/logs, d/run_*.out.
# MUC 2 parity_v11w: ung vien nen {work, regr_d1, regr_d3, tsx, logs}. GIU (CAM DUNG): vision (kho Vision dung chung cua
#        parity v1.2 run_day.sh / pv_cfg.py VIS), live (deploy/check_242_failopen.sh), runs + univ (w3/c3_ops6/ops/verify/harness_*.sh),
#        build, file cap 1. Ung vien bi CHAN neu file harness song co 'parity_v11w' va nhac '/<ten>'.
# MUC 3 res1109: XOA file .bin/.jar/.npz/.gz/.gzdat trong whitelist (r1_s1/a2_bins, r3_gate/{jar,jar_m,jar_q,
#        jar_s,asdump,ds_as,ds_as2,pred}, r3_gate/orch_m2r/ds_sim-jar-*, r5_quality/sig_*.npz). GIU (FORBID, v2 A1 MAJOR-1): r1_s1/g015x26
#        (artifact DONG BANG khong tai lap), r1_s1/a3_bins (REF HO5 P1); GIU r1_s1/kl, r3_wt, 1004/gqd/cand_base.npz,
#        moi file khac (json/md/py/log/...). CHAN = tham chieu SONG (harness/deploy/ops/crontab) hoac process; tham chieu tu script
#        nghien cuu da dong CHI GHI LOG (A1 xet).
# MUC 4 pull242: nen TUNG ngay < 2026-11-18 -> archive/pull242/<ngay>.tar.zst. BO QUA: ngay duoc file harness song co 'pull242' nhac ten,
#        2026-11-04..2026-11-14 (run_rlive.sh dev1105), ngay parity v1.2 (>= START) ma D hoac D-1 chua DONE, khong COMPLETE, co .work.
# MUC 5 a) 'git worktree remove' 6 worktree phu sach: src_wt_{c3live2,geom,gqsf,nowrite,nsel,shadow2} (HEAD thuoc >= 1 nhanh; --force CHI
#        khi thu duy nhat chua commit la DUNG src/main/java/com/binance/chuyennd/config/PrivateConfig.java; file ignored/untracked se mat in
#        vao log, co thu ngoai target/ logs/ PrivateConfig.java ledger.csv => BO QUA). b) nen ~/java/devrun (v2: bi CHAN vi
#        w3/add24_wt/tools/{run_c2b_dev,parity_clean,run_ticklog_*}.sh dung lam baseline). c) nen ~/vz/pilot_upload (khong co bang chung ban Kaggle trung
#        byte). d) sudo journalctl --vacuum-size=200M.
# KHONG BAO GIO DUNG: java/fsrun (CLOSES_1H.bin hard-code trong tradecore VolTargetSizing/PacingSizing), src_wt_pxcache, src_wt_bcd,
#   src_nup3, wt_crashpen, aerospike-data, collect, ledger, gvz, w3, v12, deploy, locks, health242, ing1030, vz_e1_wt, parity_v12w,
#   pull242 >= 2026-11-18, moi thu lien quan 242.
# Nen lossless: tar | zstd -3 -T2 -> .part ; zstd -t ; sha256 TUNG FILE giai nen == goc ; so loai muc (file/dir/symlink) khop ;
#   goc khong doi trong luc nen ; ghi .sha256 + .sha256list ; doi ten ; ROI MOI rm -rf goc. Lech => xoa .part, GIU goc, exit 1.
# Thu tu apply: 1 -> xoa thang (3, 5a) -> nen tu nho den lon (2, 4, 5b, 5c) trong MOT lan 'flock -w 3600 oracle_heavy.lock nice -n 10'
#   (truoc moi muc: khong co run_rlive, RAM available >= 4000 MB, dia trong >= max(6 GiB, kich thuoc muc), kiem lai tham chieu/process/DONE)
#   -> 5d journal. TU CHOI --apply khi co process khop 'run_rlive'; v2: kiem lai run_rlive NGAY TRUOC moi thao tac pha huy
#   (swapoff, moi rm, worktree remove, vacuum) - co thi ABORT muc.
# Thu tu xoa thang: 3 -> 2b -> 5a.
# Exit: 0 OK | 1 co ABORT/lech (da giu goc) | 2 dung phan nen do dieu kien (dia/RAM/run_rlive) | 3 tu choi (run_rlive dang chay)
# Log: ~/claude_master/cleanup_logs/cleanup_1124_<ts>[_dry].log . Kiem ke + ly do: ~/claude_master/v12/CLEANUP_1124_DEV.md
# =============================================================================
set -euo pipefail
export LC_ALL=C
APPLY=0; ONLY=1,2,2b,3,4,5; MINGAIN=10
for a in "$@"; do
  case "$a" in
    --apply) APPLY=1;;
    --dry) APPLY=0;;
    --only=*) ONLY=${a#--only=};;
    --min-gain-pct=*) MINGAIN=${a#--min-gain-pct=};;
    *) echo "Dung: $0 [--apply] [--only=1,2,3,4,5] [--min-gain-pct=N]"; exit 1;;
  esac
done
[[ "$ONLY" =~ ^(1|2|2b|3|4|5|5a|5b|5c|5d)(,(1|2|2b|3|4|5|5a|5b|5c|5d))*$ ]] || { echo "--only sai: $ONLY (cho phep: 1 2 2b 3 4 5 5a 5b 5c 5d)"; exit 1; }
[[ "$MINGAIN" =~ ^[0-9]{1,2}$ ]] || { echo "--min-gain-pct sai: $MINGAIN"; exit 1; }
want() {   # '5' bao gom 5a..5d; '2' KHONG bao gom 2b
  case ",$ONLY," in *",$1,"*) return 0;; esac
  case "$1" in 5a|5b|5c|5d) case ",$ONLY," in *",5,"*) return 0;; esac;; esac
  return 1
}
SBX=0
if [ -n "${CLEAN_H:-}" ]; then   # CHI cho test sandbox
  SBX=1
  case "$CLEAN_H" in /home/ubuntu/claude_master/v12/cleanup_1124_sandbox/*) ;; *) echo "CLEAN_H chi duoc trong v12/cleanup_1124_sandbox"; exit 1;; esac
fi
H=${CLEAN_H:-/home/ubuntu}; CM=$H/claude_master; ARC=$CM/archive; LOCK=$CM/locks/oracle_heavy.lock; LOGD=$CM/cleanup_logs
RLIVE_PAT=run_rlive; MINFREE=6442450944; MINRAM=4000; SWAPF=/swapfile; FSTAB=/etc/fstab
if [ "$SBX" = 1 ]; then
  RLIVE_PAT=${CLEAN_RLIVE_PAT:-run_rlive}; MINFREE=${CLEAN_MINFREE:-$MINFREE}; MINRAM=${CLEAN_MINRAM:-$MINRAM}; FSTAB=${CLEAN_FSTAB:-$FSTAB}
fi
mkdir -p "$LOGD"
TS=$(date +%Y%m%d_%H%M%S); SUF=_dry
if [ "$APPLY" = 1 ]; then SUF=""; fi
LOG=$LOGD/cleanup_1124_${TS}${SUF}.log
exec > >(tee -a "$LOG") 2>&1
say() { echo "[$(date '+%F %T')] $*"; }
gb() { awk -v b="$1" 'BEGIN{printf "%.2f GiB", b/1073741824}'; }
dsz() { du -sb -- "$1" 2>/dev/null | cut -f1; }
TMPD=$(mktemp -d); trap 'rm -rf "$TMPD"' EXIT
RES=$TMPD/res.tsv; : > "$RES"
HSH=$TMPD/hfile.sh
printf '%s\n' '#!/bin/sh' 'h=$(sha256sum | cut -c1-64) || exit 1' 'printf "%s  %s\n" "$h" "$TAR_FILENAME"' > "$HSH"
res() { printf '%s\t%s\t%s\t%s\t%s\n' "$1" "$2" "$3" "$4" "$5" >> "$RES"; }   # muc ten trang_thai byte_goc byte_thu
ab() { say "  ABORT muc ${CUR:-?}: $*"; exit 20; }                            # CHI goi TRONG subshell cua 1 muc
rlive_on() { local rc=0; pgrep -f -- "$RLIVE_PAT" >/dev/null 2>&1 || rc=$?; [ "$rc" != 1 ]; }   # loi pgrep => coi nhu dang chay
esc() { sed 's/[][\.*^$+?(){}|]/\\&/g' <<< "$1"; }
# ---------------------------------------------------------------- CAM DUNG (viet cung, tuyet doi)
FORBID=(
  "$H/aerospike-data" "$H/collect" "$H/ledger" "$H/src" "$H/src_wt_pxcache" "$H/src_wt_bcd" "$H/src_nup3" "$H/wt_crashpen"
  "$H/ops" "$H/vz_e1" "$H/kaggle_sim" "$H/.openclaw" "$H/shadow_c3" "$H/shadow_c3b" "$H/java/fsrun" "$H/java/simulator" "$H/vz/out"
  "$CM/gvz" "$CM/w3" "$CM/v12" "$CM/deploy" "$CM/locks" "$CM/health242" "$CM/ing1030" "$CM/vz_e1_wt" "$CM/parity_v12w" "$CM/r3_wt"
  "$CM/archive" "$CM/cleanup_logs" "$CM/collect" "$CM/ledger"
  "$CM/parity_v11w/vision" "$CM/parity_v11w/live" "$CM/parity_v11w/runs" "$CM/parity_v11w/univ" "$CM/parity_v11w/build"
  "$CM/res1109/r1_s1/kl" "$CM/1004/gqd/cand_base.npz" "$CM/res1109/r1_s1/g015x26" "$CM/res1109/r1_s1/a3_bins"
)
guard() {   # $1 duong dan: ton tai, khong symlink (ca thanh phan), trong $H, khong trung/nam trong/chua FORBID, pull242 chi ngay < 11-18
  local p=$1 rp f d
  if [ -L "$p" ]; then ab "symlink: $p"; fi
  rp=$(realpath -e -- "$p") || ab "khong ton tai: $p"
  [ "$rp" = "$p" ] || ab "realpath khac (symlink trong duong dan?): $p -> $rp"
  case "$rp" in "$H"/*) ;; *) ab "ngoai $H: $rp";; esac
  for f in "${FORBID[@]}"; do
    case "$rp" in "$f"|"$f"/*) ab "CAM DUNG: $rp (thuoc $f)";; esac
    case "$f" in "$rp"/*) ab "CAM DUNG: $rp chua $f";; esac
  done
  case "$rp" in
    "$CM/pull242") ab "CAM DUNG ca pull242";;
    "$CM/pull242"/*) d=${rp#"$CM/pull242/"}; d=${d%%/*}
      [[ "$d" =~ ^20[0-9]{2}-[0-9]{2}-[0-9]{2}$ ]] || ab "pull242: khong phai thu muc ngay: $rp"
      [[ "$d" < "2026-11-18" ]] || ab "pull242 ngay >= 2026-11-18 CAM DUNG: $rp";;
  esac
  return 0
}
# ---------------------------------------------------------------- tham chieu SONG (iv): harness/deploy/ops/crontab
LIVE_DIRS=("$CM/deploy" "$H/ops" "$CM/w3/add24_wt/tools" "$CM/w3/c3_ops6/ops" "$CM/vz_e1_wt/research/parity_v12")   # v2: ca cay add24_wt/tools
GINC=(--include='*.sh' --include='*.py' --include='*.json' --include='*.properties' --include='*.yml' --include='*.yaml' --include='*.java' --include='*.md5' --include='*.ok')
GEXC=(--exclude-dir=.git --exclude-dir=__pycache__ --exclude='*.env' --exclude='tg.env' --exclude='env.local' --exclude='PrivateConfig*' --exclude='keys*'
      --exclude='env.sh' --exclude='kaggle.json' --exclude='chd_env.sh' --exclude='cleanup_*' --exclude='test_cleanup_*' --exclude-dir='cleanup_*_sandbox')
live_grep() {   # $1 ERE -> in danh sach file (va 'crontab') co tham chieu. rc 0 = khong co, 10 = co; loi => ab (fail-closed)
  local re=$1 out err g1 g2 ct crc d PV=()
  out=$TMPD/lg.$BASHPID; err=$out.err
  for d in "${LIVE_DIRS[@]}"; do { [ -d "$d" ] && [ ! -L "$d" ]; } || ab "thu muc harness/ops song thieu hoac symlink: $d (fail-closed)"; done
  mapfile -t PV < <(find "$CM/parity_v12w" -maxdepth 1 -type f -name '*.sh' 2>/dev/null)
  set +e
  grep -rlE "${GINC[@]}" "${GEXC[@]}" -e "$re" -- "${LIVE_DIRS[@]}" > "$out" 2> "$err"; g1=$?
  g2=1; if [ "${#PV[@]}" -gt 0 ]; then grep -lE -e "$re" -- "${PV[@]}" >> "$out" 2>> "$err"; g2=$?; fi
  ct=$(crontab -l 2>&1); crc=$?
  set -e
  if [ "$g1" -gt 1 ] || [ "$g2" -gt 1 ]; then say "  grep loi: $(head -3 "$err" | tr '\n' ' ')"; ab "grep tham chieu loi (rc=$g1/$g2)"; fi
  if [ "$crc" != 0 ] && ! grep -qi 'no crontab' <<< "$ct"; then ab "crontab -l loi (rc=$crc)"; fi
  if [ "$crc" = 0 ] && grep -qE -e "$re" <<< "$ct"; then echo crontab >> "$out"; fi
  if [ -s "$out" ]; then cat "$out"; rm -f "$out" "$err"; return 10; fi
  rm -f "$out" "$err"; return 0
}
proc_uses() {   # $1 duong dan. rc 0 = khong process nao (cwd/fd/cmdline) dung; 10 = co. /proc khong tin duoc => ab
  local d=$1 p pu c fl cm of np=0 nown=0 uid
  uid=$(id -u); of=$TMPD/proc.$BASHPID; : > "$of"
  for p in /proc/[0-9]*; do
    [ -d "$p" ] || continue
    [ "${p#/proc/}" = "$BASHPID" ] && continue
    np=$((np + 1))
    pu=$(stat -c %u "$p" 2>/dev/null) || continue
    if [ "$pu" = "$uid" ]; then
      if c=$(readlink "$p/cwd" 2>/dev/null) && fl=$(ls -l "$p/fd" 2>/dev/null); then
        { echo "$c"; sed -n 's/.* -> //p' <<< "$fl"; tr '\0' '\n' < "$p/cmdline" 2>/dev/null || true; } >> "$of"; nown=$((nown + 1))
      elif [ -d "$p" ]; then
        cm=$(cat "$p/comm" 2>/dev/null || true)
        case "$cm" in
          "(sd-pam)"|sshd) ;;
          *) sleep 0.3   # process vua ket thuc / zombie (khong giu file) => bo qua; con song ma khong doc duoc => fail-closed
             if [ -d "$p" ] && ! sed -n 's/.*) \([ZX]\).*/\1/p' "$p/stat" 2>/dev/null | grep -q . && ! { readlink "$p/cwd" >/dev/null 2>&1 && ls "$p/fd" >/dev/null 2>&1; }; then
               ab "/proc: khong doc duoc cwd/fd pid ${p#/proc/} comm=$cm (fail-closed)"; fi;;
        esac
      fi
    else
      { readlink "$p/cwd" 2>/dev/null; ls -l "$p/fd" 2>/dev/null | sed -n 's/.* -> //p'; tr '\0' '\n' < "$p/cmdline" 2>/dev/null; } >> "$of" || true
    fi
  done
  { [ "$np" -ge 5 ] && [ "$nown" -ge 1 ]; } || ab "/proc: $np process ($nown cua user) - khong tin duoc"
  if grep -qF -- "$d" "$of"; then rm -f "$of"; return 10; fi
  rm -f "$of"; return 0
}
# ================================================================ MUC 1: swap
SW() { if [ "$SBX" = 1 ]; then say "    [sandbox, KHONG chay] sudo $*"; return 0; fi; say "    sudo $*"; sudo "$@"; }
swap_recover() {
  say "  !!! LOI giua chung - co bat lai swap"
  if [ "$SBX" = 1 ]; then say "    [sandbox] (khong chay lenh khoi phuc)"; return 0; fi
  if swapon --show=NAME --noheadings 2>/dev/null | grep -qx "$SWAPF"; then say "  swap $SWAPF van dang bat"; return 0; fi
  if [ -f "$SWAPF" ] && [ ! -L "$SWAPF" ] && [ "$(stat -c %s "$SWAPF")" -ge 1073741824 ]; then
    if SW chmod 600 "$SWAPF" && SW mkswap "$SWAPF" && SW swapon "$SWAPF"; then say "  da bat lai $SWAPF"; return 0; fi
  fi
  if SW rm -f "$SWAPF" && { SW fallocate -l 4G "$SWAPF" || SW dd if=/dev/zero of="$SWAPF" bs=1M count=4096 status=none; } \
     && SW chmod 600 "$SWAPF" && SW mkswap "$SWAPF" && SW swapon "$SWAPF"; then say "  da tao lai + bat $SWAPF 4G"; return 0; fi
  say "  !!! SWAP CHUA BAT LAI DUOC - owner kiem ngay: swapon --show ; free -m"
}
m1() {
  CUR=1; say "--- MUC 1: swap $SWAPF -> 4G"
  local line name size used avail usedm want=4294967296 other
  if [ "$SBX" = 1 ]; then line=${CLEAN_SWAP_SHOW:-}
  else line=$(swapon --show=NAME,SIZE,USED --bytes --noheadings | awk -v f="$SWAPF" '$1==f') || ab "swapon --show loi"; fi
  if [ -z "$line" ]; then say "  BO QUA: $SWAPF khong dang bat"; res 1 swap BO_QUA_khong_bat 0 0; return 0; fi
  read -r name size used <<< "$line"
  [[ "$size" =~ ^[0-9]+$ && "$used" =~ ^[0-9]+$ && "$name" = "$SWAPF" ]] || ab "swapon --show khong doc duoc: $line"
  if [ "$size" -le $((want + 67108864)) ]; then say "  BO QUA: da <= 4G ($(gb "$size"))"; res 1 swap BO_QUA_da_4G "$size" 0; return 0; fi
  if [ "$SBX" = 0 ]; then { [ -f "$SWAPF" ] && [ ! -L "$SWAPF" ]; } || ab "$SWAPF khong phai file thuong"; fi
  grep -qE "^[[:space:]]*$SWAPF[[:space:]]+none[[:space:]]+swap[[:space:]]" "$FSTAB" || ab "$FSTAB khong co dong '$SWAPF none swap ...' - khong dung"
  avail=$(awk '/^MemAvailable:/{print int($2/1024)}' /proc/meminfo)
  if [ "$SBX" = 1 ]; then avail=${CLEAN_MEMAVAIL:-$avail}; fi
  usedm=$((used / 1048576))
  other=$(swapon --show=NAME --noheadings 2>/dev/null | grep -vx "$SWAPF" | tr '\n' ' ' || true)
  say "  hien: $SWAPF $(gb "$size"), dang dung ${usedm} MB; RAM available ${avail} MB; swap khac: ${other:-khong}; fstab: giu nguyen"
  if [ $((usedm + 2000)) -ge "$avail" ]; then say "  BO QUA: swap dang dung ${usedm} MB + 2000 >= RAM available ${avail} MB"; res 1 swap BO_QUA_ram "$size" 0; return 0; fi
  if [ "$APPLY" = 0 ]; then
    say "  SE: swapoff -> rm -> fallocate -l 4G (loi => dd 4096 MiB) -> chmod 600 -> mkswap -> swapon -> kiem 4G; loi giua chung => co bat lai"
    res 1 swap SE_doi_4G "$size" $((size - want)); return 0
  fi
  if rlive_on; then ab "run_rlive dang chay - khong swapoff"; fi
  SW swapoff "$SWAPF" || ab "swapoff loi (swap van bat, khong doi gi)"
  if ! { SW rm -f "$SWAPF" && { SW fallocate -l 4G "$SWAPF" || { say "    fallocate loi -> dd"; SW dd if=/dev/zero of="$SWAPF" bs=1M count=4096 status=none; }; } \
         && SW chmod 600 "$SWAPF" && SW mkswap "$SWAPF" && SW swapon "$SWAPF"; }; then
    swap_recover; ab "doi swap loi (xem tren)"
  fi
  if [ "$SBX" = 0 ]; then
    line=$(swapon --show=NAME,SIZE --bytes --noheadings | awk -v f="$SWAPF" '$1==f{print $2}')
    if ! { [ "${line:-0}" -ge 4000000000 ] && [ "${line:-0}" -le 4400000000 ]; }; then swap_recover; ab "kiem sau: $SWAPF = ${line:-khong bat}"; fi
    say "  DA doi swap: $(swapon --show --noheadings | tr '\n' ' ')"
  fi
  res 1 swap DA_doi_4G "$size" $((size - want))
}
# ================================================================ MUC 3: res1109 (xoa nhi phan whitelist v5)
m3() {
  CUR=3; say "--- MUC 3: res1109 - XOA file nhi phan whitelist v5 (ket qua da commit vz_e1_wt a5ff7c9f; nguon/dataset tren Kaggle)"
  local RS=$CM/res1109 w rel re rc hits o f s s0 nf RS_WL=() FL=() T=() OTH PATF
  if [ ! -d "$RS" ]; then say "  BO QUA (khong co res1109)"; res 3 res1109 BO_QUA_khong_co 0 0; return 0; fi
  if [ -L "$RS" ]; then ab "res1109 la symlink"; fi
  RS_WL=("$RS/r1_s1/a2_bins" "$RS/r3_gate/jar" "$RS/r3_gate/jar_m" "$RS/r3_gate/jar_q" "$RS/r3_gate/jar_s"
         "$RS/r3_gate/asdump" "$RS/r3_gate/ds_as" "$RS/r3_gate/ds_as2" "$RS/r3_gate/pred")
  for w in "$RS"/r3_gate/orch_m2r/ds_sim-jar-*; do if [ -d "$w" ] && [ ! -L "$w" ]; then RS_WL+=("$w"); fi; done
  # tham chieu ngoai harness song: CHI GHI LOG (script nghien cuu da dong) - *.sh/*.py trong ~/claude_master, ~/ops, ~/tools
  OTH=$TMPD/rs_oth; PATF=$TMPD/rs_pat
  { for w in "${RS_WL[@]}"; do echo "${w#"$CM/"}"; done; echo "res1109/r5_quality/sig_"; } > "$PATF"
  T=("$CM"); for w in "$H/ops" "$H/tools"; do if [ -d "$w" ]; then T+=("$w"); fi; done
  set +e; grep -rHoF --include='*.sh' --include='*.py' "${GEXC[@]}" -f "$PATF" -- "${T[@]}" > "$OTH" 2>/dev/null; rc=$?; set -e
  if [ "$rc" -gt 1 ]; then say "  CANH BAO: grep tham chieu ngoai (chi de ghi log) rc=$rc - danh sach co the thieu"; fi
  rs_one() {   # $1 rel (tu $CM), $2 ERE tham chieu; tiep theo: file
    local rel=$1 re=$2; shift 2
    rc=0; hits=$(live_grep "$re") || rc=$?
    case "$rc" in 0) ;; 10) say "  BO QUA $rel - tham chieu SONG: $(tr '\n' ' ' <<< "$hits")"; res 3 "$rel" BO_QUA_tham_chieu_song 0 0; return 0;; *) ab "kiem tham chieu loi ($rel)";; esac
    o=$(awk -v r="$rel" '{i=match($0, /:[^:]*$/); if (i > 0 && substr($0, i + 1) == r) print substr($0, 1, i - 1)}' "$OTH" \
        | grep -vF "$RS/" | grep -v '/docs/result/res1109_raw/' | sort -u | tr '\n' ' ' || true)
    if [ -n "$o" ]; then say "    tham chieu nghien cuu da dong (KHONG chan - A1 xet): $o"; fi
    rc=0; proc_uses "$CM/$rel" || rc=$?
    if [ "$rc" = 10 ]; then say "  BO QUA $rel - process dang dung"; res 3 "$rel" BO_QUA_process 0 0; return 0; fi
    s0=0; nf=0
    for f in "$@"; do
      guard "$f"; [ -f "$f" ] || ab "khong phai file: $f"
      [[ "$(basename -- "$f")" =~ \.(bin|jar|npz|gz|gzdat)$ ]] || ab "duoi khong cho phep: $f"
      case "$f" in "$RS/r1_s1/kl"/*|"$CM/r3_wt"/*) ab "GIU tuyet doi: $f";; esac
      s=$(stat -c %s -- "$f"); s0=$((s0 + s)); nf=$((nf + 1))
      if [ "$APPLY" = 1 ]; then if rlive_on; then ab "run_rlive dang chay - dung truoc rm"; fi; rm -f -- "$f" || ab "rm $f"; fi
    done
    if [ "$nf" = 0 ]; then say "  (khong co file nhi phan) $rel"; return 0; fi
    if [ "$APPLY" = 1 ]; then say "  DA xoa $rel: $nf file ($(gb "$s0"))"; res 3 "$rel" DA_xoa "$s0" "$s0"
    else say "  SE xoa $rel: $nf file nhi phan ($(gb "$s0")); giu json/md/log/..."; res 3 "$rel" SE_xoa "$s0" "$s0"; fi
  }
  for w in "${RS_WL[@]}"; do
    if [ ! -d "$w" ]; then say "  BO QUA (khong co) ${w#"$CM/"}"; continue; fi
    if [ -L "$w" ]; then ab "whitelist la symlink: $w"; fi
    rel=${w#"$CM/"}; re="$(esc "$rel")([^A-Za-z0-9_-]|\$)"
    mapfile -d '' FL < <(find "$w" -type f -regextype posix-extended -regex '.*\.(bin|jar|npz|gz|gzdat)$' -print0 | sort -z)
    rs_one "$rel" "$re" "${FL[@]}"
  done
  mapfile -d '' FL < <(find "$RS/r5_quality" -maxdepth 1 -type f -name 'sig_*.npz' -print0 2>/dev/null | sort -z)
  if [ "${#FL[@]}" -gt 0 ]; then rs_one "res1109/r5_quality/sig_" "$(esc res1109/r5_quality/sig_)" "${FL[@]}"; fi
}
# ================================================================ MUC 5a: worktree phu
m5a() {
  CUR=5a; say "--- MUC 5a: git worktree remove worktree phu sach (khong rm -rf)"
  local MAIN=$H/src/BinanceFuturesJava d top gd cg head nb all other npc rc hits s j m KEEPS V12J ref FORCE ign bad
  local PCP=src/main/java/com/binance/chuyennd/config/PrivateConfig.java PCRE='src/main/java/com/binance/chuyennd/config/PrivateConfig\.java' 
  KEEPS=$( { grep -ho '[0-9a-f]\{32\}' "$CM/parity_v12w/jars.json" "$CM/parity_v12w/gmicro_target.json" 2>/dev/null || true
             for t in "$CM/deploy" "$H/ops" "$CM/v12/c3live/ops"; do
               if [ -d "$t" ]; then find "$t" -type f -size -5M \( -name '*.sh' -o -name '*.py' -o -name '*.json' -o -name '*.md5' -o -name '*.ok' \) -print0 \
                 | xargs -0 -r grep -hoI '[0-9a-f]\{32\}' 2>/dev/null || true; fi
             done; } | sort -u)
  V12J=$( { find "$CM/v12/jar" -maxdepth 1 -type f -print0 2>/dev/null || true; } | xargs -0 -r md5sum | cut -c1-32 | sort -u)
  for d in "$H/src_wt_c3live2" "$H/src_wt_geom" "$H/src_wt_gqsf" "$H/src_wt_nowrite" "$H/src_wt_nsel" "$H/src_wt_shadow2"; do
    if [ ! -d "$d" ]; then say "  BO QUA (khong co) $d"; continue; fi
    guard "$d"
    top=$(git -C "$d" rev-parse --show-toplevel 2>/dev/null || true)
    gd=$(git -C "$d" rev-parse --absolute-git-dir 2>/dev/null || true)
    cg=$(git -C "$d" rev-parse --path-format=absolute --git-common-dir 2>/dev/null || true)
    if ! { [ "$top" = "$d" ] && [ "$gd" != "$cg" ] && [[ "$gd" == */worktrees/* ]] && [ "$cg" = "$MAIN/.git" ]; }; then
      say "  BO QUA (khong phai worktree phu cua $MAIN: top=$top common=$cg) $d"; res 5a "$(basename "$d")" BO_QUA_khong_phai_wt 0 0; continue; fi
    head=$(git -C "$d" rev-parse HEAD 2>/dev/null || true)
    nb=$(git -C "$d" for-each-ref --contains "$head" --format='%(refname)' refs/heads refs/remotes 2>/dev/null | grep -c . || true)
    if [ "${nb:-0}" -lt 1 ]; then say "  BO QUA (HEAD ${head:0:8} khong thuoc nhanh nao) $d"; res 5a "$(basename "$d")" BO_QUA_head_mo_coi 0 0; continue; fi
    all=$(git --no-optional-locks -C "$d" status --porcelain --untracked-files=all --ignored=no 2>/dev/null) || ab "git status loi $d"
    other=$(grep -vE "^.. $PCRE\$" <<< "$all" | grep -c . || true); npc=$(grep -cE "^.. $PCRE\$" <<< "$all" || true)
    if [ "${other:-0}" != 0 ]; then say "  BO QUA ($other file chua commit/untracked ngoai $PCP) $d"; res 5a "$(basename "$d")" BO_QUA_ban 0 0; continue; fi
    ign=$(git --no-optional-locks -C "$d" status --porcelain --untracked-files=all --ignored=matching 2>/dev/null | sed -n 's/^!! //p') || ab "git status --ignored loi $d"
    if [ -n "$ign" ]; then say "    file ignored se MAT khi worktree remove ($d): $(tr '\n' ' ' <<< "$ign" | cut -c1-600)"; fi
    bad=$(grep -vE "^($PCRE|(.*/)?target/.*|(.*/)?target/|(.*/)?logs/.*|(.*/)?logs/|(.*/)?ledger\.csv)\$" <<< "$ign" | grep -c . || true)
    if [ "${bad:-0}" != 0 ]; then say "  BO QUA ($bad muc ignored ngoai target/ logs/ PrivateConfig.java ledger.csv: $(grep -vE "^($PCRE|(.*/)?target/.*|(.*/)?target/|(.*/)?logs/.*|(.*/)?logs/|(.*/)?ledger\.csv)\$" <<< "$ign" | head -5 | tr '\n' ' ')) $d"; res 5a "$(basename "$d")" BO_QUA_ignored_khac 0 0; continue; fi
    rc=0; hits=$(live_grep "$(basename -- "$d")([^A-Za-z0-9_]|\$)") || rc=$?
    case "$rc" in 0) ;; 10) say "  BO QUA $d - tham chieu SONG: $(tr '\n' ' ' <<< "$hits")"; res 5a "$(basename "$d")" BO_QUA_tham_chieu_song 0 0; continue;; *) ab "kiem tham chieu loi";; esac
    rc=0; proc_uses "$d" || rc=$?
    if [ "$rc" = 10 ]; then say "  BO QUA $d - process dang dung"; res 5a "$(basename "$d")" BO_QUA_process 0 0; continue; fi
    ref=""
    while IFS= read -r -d '' j; do
      m=$(md5sum < "$j" | cut -c1-32)
      if grep -qx "$m" <<< "$KEEPS" && ! grep -qx "$m" <<< "$V12J"; then ref="$(basename -- "$j") ${m:0:8}"; break; fi
    done < <(find "$d/target" -maxdepth 1 -type f -name '*.jar' -print0 2>/dev/null)
    if [ -n "$ref" ]; then say "  BO QUA $d - jar $ref duoc tham chieu ma khong co ban trong v12/jar"; res 5a "$(basename "$d")" BO_QUA_jar 0 0; continue; fi
    FORCE=(); if [ "${npc:-0}" != 0 ]; then FORCE=(--force); fi
    s=$(dsz "$d")
    if [ "$APPLY" = 1 ]; then
      if rlive_on; then ab "run_rlive dang chay - dung truoc worktree remove"; fi
      git -C "$MAIN" worktree remove "${FORCE[@]}" -- "$d" || ab "git worktree remove ${FORCE[*]} $d"
      if [ -e "$d" ]; then ab "sau worktree remove van con $d"; fi
      say "  DA git worktree remove ${FORCE[*]} $d ($(gb "$s"))"; res 5a "$(basename "$d")" DA_go "$s" "$s"
    else
      say "  SE git worktree remove ${FORCE[*]} $d ($(gb "$s"), HEAD ${head:0:8} thuoc $nb nhanh${FORCE[*]:+, chi PrivateConfig chua commit})"; res 5a "$(basename "$d")" SE_go "$s" "$s"
    fi
  done
}
# ================================================================ NEN LOSSLESS (muc 2, 4, 5b, 5c)
ratio_est() {   # $1 thu muc -> ti le zstd -3 tren mau tar <= 100 MB dau (khong ghi dia)
  local par n i o
  par=$(dirname -- "$1"); n=$(basename -- "$1")
  i=$( { tar -C "$par" -cf - -- "$n" 2>/dev/null || true; } | head -c 100000000 | wc -c)
  o=$( { tar -C "$par" -cf - -- "$n" 2>/dev/null || true; } | head -c 100000000 | zstd -q -3 -T2 -c | wc -c)
  awk -v a="$o" -v b="$i" 'BEGIN{ if (b > 0) printf "%.4f", a / b; else print 1 }'
}
fsnap() { find "$1" -printf '%y %s %T@ %p\n' | sort | sha256sum | cut -c1-64; }   # anh chup metadata (phat hien goc doi)
pack() {   # $1 thu muc, $2 archive .tar.zst. rc 0 = da kiem khop (CHUA xoa goc); 30 = loi/lech
  local d=$1 out=$2 part=$2.part par n v1 v2 ha hb ta tb h
  par=$(dirname -- "$d"); n=$(basename -- "$d"); ha=$TMPD/ha.$BASHPID; hb=$TMPD/hb.$BASHPID
  v1=$(fsnap "$d") || return 30
  if ! tar -C "$par" -cf - -- "$n" | zstd -q -3 -T2 -o "$part"; then say "    tar | zstd loi"; return 30; fi
  if [ "$SBX" = 1 ] && [ -n "${CLEAN_TEST_MUTATE:-}" ] && [ -f "$CLEAN_TEST_MUTATE" ]; then
    echo x >> "$CLEAN_TEST_MUTATE"; say "    [sandbox] da sua $CLEAN_TEST_MUTATE sau khi nen (gia lap lech)"; fi
  zstd -q -t -- "$part" || { say "    zstd -t loi"; return 30; }
  zstd -q -dc -- "$part" | tar -xf - --to-command="sh $HSH" > "$ha.u" || { say "    giai nen + sha256 loi"; return 30; }
  sort "$ha.u" > "$ha"
  ( cd "$par" && find "$n" -type f -print0 | xargs -0 -r sha256sum ) > "$hb.u" || { say "    sha256 goc loi"; return 30; }
  sort "$hb.u" > "$hb"
  if ! cmp -s "$ha" "$hb"; then say "    LECH sha256 tung file: archive $(wc -l < "$ha") / goc $(wc -l < "$hb") file"; return 30; fi
  ta=$(zstd -q -dc -- "$part" | tar -tvf - | cut -c1 | sort | uniq -c | awk '{printf "%s:%s ", $2, $1}') || return 30
  tb=$(cd "$par" && find "$n" -printf '%y\n' | sed 's/^f$/-/' | sort | uniq -c | awk '{printf "%s:%s ", $2, $1}') || return 30
  if [ "$ta" != "$tb" ]; then say "    LECH loai muc: archive [$ta] goc [$tb]"; return 30; fi
  v2=$(fsnap "$d") || return 30
  if [ "$v1" != "$v2" ]; then say "    goc DOI trong luc nen"; return 30; fi
  h=$(sha256sum < "$part" | cut -c1-64); [ "${#h}" = 64 ] || return 30
  cp -- "$ha" "$part.sha256list" || return 30
  printf '%s  %s\n' "$h" "$(basename -- "$out")" > "$part.sha256" || return 30
  mv -f -- "$part.sha256list" "${out%.tar.zst}.sha256list" && mv -f -- "$part.sha256" "$out.sha256" && mv -f -- "$part" "$out" || { say "    doi ten loi"; return 30; }
  say "    kiem OK: $(wc -l < "$ha") file sha256 khop tung file; loai muc [$ta] khop; goc khong doi; archive sha256 ${h:0:16}"
  rm -f -- "$ha" "$ha.u" "$hb" "$hb.u"
  return 0
}
start12() {   # START cua watcher parity v1.2 (gia tri mac dinh trong script; neu log co START khac => lay nho nhat). Loi => ab
  local w=$CM/vz_e1_wt/research/parity_v12/sh/watch_daily_v12.sh a b
  a=$(grep -oE '^START=\$\{START:-20[0-9]{2}-[0-9]{2}-[0-9]{2}\}' "$w" 2>/dev/null | grep -oE '20[0-9]{2}-[0-9]{2}-[0-9]{2}' | head -1 || true)
  [ -n "$a" ] || ab "khong doc duoc START tu $w"
  b=$(grep -oE 'START pid=[0-9]+ START=20[0-9]{2}-[0-9]{2}-[0-9]{2}' "$CM/parity_v12w/watch_v12.log" 2>/dev/null | grep -oE '20[0-9]{2}-[0-9]{2}-[0-9]{2}$' | sort | head -1 || true)
  if [ -n "$b" ] && [[ "$b" < "$a" ]]; then a=$b; fi
  echo "$a"
}
comp_one() {   # $1 muc $2 nhan $3 thu muc $4 archive. rc 0 xong/bo qua; 30 lech (giu goc); 40 DUNG phan nen; khac = ABORT muc
  local m=$1 lab=$2 d=$3 out=$4 v nf sb s1 r est gain rc hits f day prev st W12 mem avail need zs sub
  CUR=$m
  if [ ! -e "$d" ] && [ ! -L "$d" ]; then say "  BO QUA (khong co) $lab"; res "$m" "$lab" BO_QUA_khong_co 0 0; return 0; fi
  guard "$d"; [ -d "$d" ] || ab "khong phai thu muc: $d"
  case "$out" in "$ARC"/*.tar.zst) ;; *) ab "archive ngoai $ARC: $out";; esac
  if [ -e "$out" ] || [ -e "$out.part" ]; then say "  BO QUA (da co $out[.part] - kiem tay) $lab"; res "$m" "$lab" BO_QUA_da_co_archive 0 0; return 0; fi
  if [ -n "$(find "$d" -name .git -print -quit)" ]; then say "  BO QUA (co .git) $lab"; res "$m" "$lab" BO_QUA_git 0 0; return 0; fi
  v=$(find "$d" -newermt "@$(( $(date +%s) - 259200 ))" -print -quit)
  if [ -n "$v" ]; then say "  BO QUA (co muc moi < 3 ngay: ${v#"$d"/}) $lab"; res "$m" "$lab" BO_QUA_moi 0 0; return 0; fi
  case "$m" in
    2) sub=$(basename -- "$d")
       rc=0; hits=$(live_grep 'parity_v11w') || rc=$?
       case "$rc" in 0|10) ;; *) ab "kiem tham chieu loi";; esac
       if [ "$rc" = 10 ]; then
         v=""; while IFS= read -r f; do
           if [ "$f" = crontab ]; then if crontab -l 2>/dev/null | grep -qE "parity_v11w/$sub([^A-Za-z0-9_]|\$)"; then v="$v crontab"; fi; continue; fi
           if grep -qE "/$sub([^A-Za-z0-9_]|\$)" -- "$f"; then v="$v $f"; fi
         done <<< "$hits"
         if [ -n "$v" ]; then say "  BO QUA $lab - file song co 'parity_v11w' va nhac '/$sub':$v"; res "$m" "$lab" BO_QUA_tham_chieu_song 0 0; return 0; fi
       fi;;
    4) day=$(basename -- "$d")
       if [ ! -f "$d/COMPLETE" ] || [ -e "$d/.work" ]; then say "  BO QUA $lab - khong COMPLETE hoac dang keo (.work)"; res "$m" "$lab" BO_QUA_chua_complete 0 0; return 0; fi
       if [[ ! "$day" < "2026-11-04" ]] && [[ ! "$day" > "2026-11-14" ]]; then say "  BO QUA $lab - run_rlive.sh dev1105 doc pull242 2026-11-04..11-14"; res "$m" "$lab" BO_QUA_rlive_dev 0 0; return 0; fi
       rc=0; hits=$(live_grep 'pull242') || rc=$?
       case "$rc" in 0|10) ;; *) ab "kiem tham chieu loi";; esac
       v=""; if [ "$rc" = 10 ]; then while IFS= read -r f; do
         if [ "$f" != crontab ] && grep -qF -- "$day" "$f"; then v="$v $f"; fi; done <<< "$hits"; fi
       if [ -n "$v" ]; then say "  BO QUA $lab - file song nhac 'pull242' va ngay $day:$v"; res "$m" "$lab" BO_QUA_tham_chieu_song 0 0; return 0; fi
       st=$(start12); W12=$CM/parity_v12w/d
       if [[ ! "$day" < "$st" ]] && [ ! -f "$W12/$day/DONE" ]; then say "  BO QUA $lab - parity v1.2 ngay $day chua DONE (START $st)"; res "$m" "$lab" BO_QUA_chua_done 0 0; return 0; fi
       prev=$(date -u -d "$day -1 day" +%F)
       if [[ ! "$prev" < "$st" ]] && [ ! -f "$W12/$prev/DONE" ]; then say "  BO QUA $lab - parity v1.2 ngay $prev (doc pull242 D+1=$day) chua DONE"; res "$m" "$lab" BO_QUA_chua_done 0 0; return 0; fi;;
    5b|5c) rc=0; hits=$(live_grep "$(esc "${d#"$H/"}")([^A-Za-z0-9_]|\$)") || rc=$?
       case "$rc" in 0) ;; 10) say "  BO QUA $lab - tham chieu SONG: $(tr '\n' ' ' <<< "$hits")"; res "$m" "$lab" BO_QUA_tham_chieu_song 0 0; return 0;; *) ab "kiem tham chieu loi";; esac;;
    *) ab "muc nen la: $m";;
  esac
  rc=0; proc_uses "$d" || rc=$?
  if [ "$rc" = 10 ]; then say "  BO QUA $lab - process dang dung (cwd/fd/cmdline)"; res "$m" "$lab" BO_QUA_process 0 0; return 0; fi
  read -r nf sb s1 < <(find "$d" -type f -printf '%s %n\n' | awk '{n++; t+=$1; if ($2 == 1) u+=$1} END{printf "%d %.0f %.0f\n", n+0, t+0, u+0}')
  if [ "${sb:-0}" = 0 ]; then say "  BO QUA $lab - rong"; res "$m" "$lab" BO_QUA_rong 0 0; return 0; fi
  r=$(ratio_est "$d"); est=$(awk -v s="$sb" -v r="$r" 'BEGIN{printf "%.0f", s * r}'); gain=$((s1 - est))
  if [ $((gain * 100)) -lt $((MINGAIN * sb)) ]; then
    say "  BO QUA $lab - khong dang nen: $(gb "$sb"), ti le mau $r, byte giai phong duoc (nlink=1) $(gb "$s1") => uoc thu $(gb "$gain") < $MINGAIN %"
    res "$m" "$lab" BO_QUA_it_loi "$sb" 0; return 0; fi
  if [ "$APPLY" = 0 ]; then
    say "  SE nen $lab ($(gb "$sb"), $nf file, ti le mau $r => thu uoc $(gb "$gain")) -> ${out#"$CM/"}; kiem sha256 tung file roi moi xoa goc"
    res "$m" "$lab" SE_nen "$sb" "$gain"; return 0; fi
  if rlive_on; then say "  DUNG phan nen: co process '$RLIVE_PAT' (truoc $lab)"; res "$m" "$lab" DUNG_rlive "$sb" 0; return 40; fi
  mem=$(awk '/^MemAvailable:/{print int($2/1024)}' /proc/meminfo)
  if [ "$mem" -lt "$MINRAM" ]; then say "  DUNG phan nen: RAM available $mem MB < $MINRAM (truoc $lab)"; res "$m" "$lab" DUNG_ram "$sb" 0; return 40; fi
  avail=$(df -B1 --output=avail "$CM" | tail -1 | tr -dc 0-9); need=$(( sb > MINFREE ? sb : MINFREE ))
  if [ "$avail" -lt "$need" ]; then say "  DUNG phan nen: dia trong $(gb "$avail") < $(gb "$need") (truoc $lab)"; res "$m" "$lab" DUNG_dia "$sb" 0; return 40; fi
  mkdir -p -- "$(dirname -- "$out")"
  say "  nen $lab ($(gb "$sb"), $nf file) -> ${out#"$CM/"}"
  rc=0; pack "$d" "$out" || rc=$?
  if [ "$rc" != 0 ]; then
    rm -f -- "$out.part" "$out.part.sha256list" "$out.part.sha256"
    if [ ! -e "$out" ]; then rm -f -- "$out.sha256" "${out%.tar.zst}.sha256list"; fi
    say "  LOI nen/kiem $lab - da xoa .part, GIU NGUYEN goc"; res "$m" "$lab" LOI_giu_goc "$sb" 0; return 30
  fi
  guard "$d"
  if rlive_on; then say "  run_rlive xuat hien sau khi nen $lab - GIU goc (archive da kiem, xoa tay sau)"; res "$m" "$lab" DUNG_rlive_giu_goc "$sb" 0; return 40; fi
  rm -rf -- "$d" || ab "xoa goc $d"
  zs=$(stat -c %s -- "$out")
  say "  DA nen $lab: $(gb "$sb") -> $(gb "$zs") + .sha256 + .sha256list; da xoa goc"; res "$m" "$lab" DA_nen "$sb" $((s1 - zs)); return 0
}
comp_loop() {   # $1 file ung vien (muc TAB nhan TAB thu muc TAB archive), da sap nho -> lon. rc 0 | 1 (co lech/abort) | 40 dung
  local m lab d out rc err=0
  while IFS=$'\t' read -r m lab d out; do
    rc=0; set +e; ( set -e; comp_one "$m" "$lab" "$d" "$out" ) < /dev/null; rc=$?; set -e
    case "$rc" in 0) ;; 30) err=1;; 40) return 40;; *) say "  => $lab: ABORT (rc=$rc), giu nguyen"; res "$m" "$lab" ABORT 0 0; err=1;; esac
  done < "$1"
  return "$err"
}
# ================================================================ MUC 5d: journal
m5d() {
  CUR=5d; say "--- MUC 5d: journalctl --vacuum-size=200M"
  local u ub g
  u=$(journalctl --disk-usage 2>/dev/null | grep -oE '[0-9.]+[KMGT]' | tail -1 || true)
  ub=$(numfmt --from=iec "${u:-0}" 2>/dev/null || echo 0); g=$(( ub > 209715200 ? ub - 209715200 : 0 ))
  if [ "$APPLY" = 0 ]; then say "  SE: sudo journalctl --vacuum-size=200M (journal hien ${u:-?})"; res 5d journal SE_vacuum "$ub" "$g"; return 0; fi
  if [ "$SBX" = 1 ]; then say "    [sandbox, KHONG chay] sudo journalctl --vacuum-size=200M"; res 5d journal DA_vacuum_sandbox "$ub" 0; return 0; fi
  if rlive_on; then ab "run_rlive dang chay - khong vacuum"; fi
  sudo journalctl --vacuum-size=200M || ab "journalctl vacuum loi"
  say "  DA vacuum: $(journalctl --disk-usage 2>/dev/null | tail -1)"; res 5d journal DA_vacuum "$ub" "$g"
}
# ================================================================ MUC 2b: XOA THANG parity_v11w/d/2026-* (v2)
m2b() {
  CUR=2b; say "--- MUC 2b: XOA THANG parity_v11w/d/2026-MM-DD[_ops] (parity v1.1 het gia tri - owner; tong ket da commit vz_e1_wt 09622c01)"
  local P11=$CM/parity_v11w D=$CM/parity_v11w/d V=$CM/vz_e1_wt n st rc x s tot=0 L=() man NDOC=${CLEAN_D2B_NDOCS:-268}
  if [ "$SBX" = 0 ]; then NDOC=268; fi
  if [ ! -e "$D" ] && [ ! -L "$D" ]; then say "  BO QUA (khong co $D)"; res 2b parity_v11w/d BO_QUA_khong_co 0 0; return 0; fi
  if [ -L "$P11" ] || [ -L "$D" ]; then ab "parity_v11w hoac d la symlink"; fi
  [ "$(realpath -e -- "$D")" = "$D" ] || ab "realpath $D khac"
  # (i) tong ket ngay da commit + sach
  n=$(git -C "$V" ls-files -- 'docs/result/parity_v11_daily_*' | wc -l) || ab "git ls-files loi"
  st=$(git --no-optional-locks -C "$V" status --porcelain -- 'docs/result/parity_v11_daily_*') || ab "git status loi"
  if [ "$n" -lt "$NDOC" ] || [ -n "$st" ]; then say "  BO QUA: docs/result/parity_v11_daily_* tracked $n (< $NDOC) hoac chua sach: $(head -3 <<< "$st" | tr '\n' ' ')"; res 2b parity_v11w/d BO_QUA_docs_chua_commit 0 0; return 0; fi
  say "  docs/result/parity_v11_daily_*: $n file tracked, sach"
  # (ii) process
  rc=0; pgrep -f 'watch_daily[.]sh( |$)' >/dev/null 2>&1 || rc=$?
  if [ "$rc" = 0 ]; then say "  BO QUA: co process watch_daily.sh (watcher v1.1) dang chay"; res 2b parity_v11w/d BO_QUA_watcher_v11 0 0; return 0; fi
  [ "$rc" = 1 ] || ab "pgrep loi rc=$rc"
  rc=0; proc_uses "$D" || rc=$?
  if [ "$rc" = 10 ]; then say "  BO QUA: process dang dung $D"; res 2b parity_v11w/d BO_QUA_process 0 0; return 0; fi
  # (iii) chi thu muc con truc tiep ten 2026-MM-DD[_ops], khong symlink
  while IFS= read -r -d '' x; do
    if [[ ! "$(basename -- "$x")" =~ ^2026-[0-9]{2}-[0-9]{2}(_ops)?$ ]]; then continue; fi
    if [ -L "$x" ]; then ab "symlink ten ngay trong d: $x"; fi
    [ -d "$x" ] || continue
    guard "$x"; [ "$(dirname -- "$x")" = "$D" ] || ab "khong phai con truc tiep cua $D: $x"
    L+=("$x")
  done < <(find "$D" -mindepth 1 -maxdepth 1 -print0 | sort -z)
  if [ "${#L[@]}" = 0 ]; then say "  BO QUA: khong con thu muc ngay"; res 2b parity_v11w/d BO_QUA_rong 0 0; return 0; fi
  for x in "${L[@]}"; do s=$(dsz "$x"); tot=$((tot + s)); done
  say "  ${#L[@]} thu muc ngay ($(basename -- "${L[0]}") .. $(basename -- "${L[${#L[@]}-1]}")), $(gb "$tot"); GIU: $(find "$D" -mindepth 1 -maxdepth 1 ! -regex '.*/2026-[0-9][0-9]-[0-9][0-9]\(_ops\)?' -printf '%f ' | cut -c1-300)"
  if [ "$APPLY" = 0 ]; then say "  SE xoa thang ${#L[@]} thu muc (manifest -> archive/parity_v11w_d_manifest_<ts>.txt truoc)"; res 2b parity_v11w/d SE_xoa "$tot" "$tot"; return 0; fi
  mkdir -p -- "$ARC"; man=$ARC/parity_v11w_d_manifest_$TS.txt
  { echo "# parity_v11w/d truoc khi xoa ($(date -Is)); size<TAB>type<TAB>path"; for x in "${L[@]}"; do find "$x" -printf '%s\t%y\t%p\n'; done; } > "$man" || ab "ghi manifest loi"
  say "  manifest: $man ($(wc -l < "$man") dong)"
  for x in "${L[@]}"; do
    if rlive_on; then ab "run_rlive dang chay - dung truoc rm"; fi
    guard "$x"; rm -rf -- "$x" || ab "rm $x"
  done
  say "  DA xoa ${#L[@]} thu muc ($(gb "$tot"))"; res 2b parity_v11w/d DA_xoa "$tot" "$tot"
}
# ================================================================ MAIN
run_item() {   # chay 1 muc trong subshell (ABORT chi dung muc do)
  local rc=0
  if [ "$SBX" = 1 ] && [ -n "${CLEAN_TEST_DELAY:-}" ]; then sleep "$CLEAN_TEST_DELAY"; fi   # chi test sandbox (MINOR-3)
  set +e; ( set -e; "$@" ) < /dev/null; rc=$?; set -e
  if [ "$rc" != 0 ]; then say "  => muc ${1#m}: ABORT (rc=$rc) - cac muc khac van tiep tuc"; res "${1#m}" "$1" ABORT 0 0; ERR=1; fi
  return 0
}
say "=== cleanup_oracle_1124 APPLY=$APPLY ONLY=$ONLY MIN_GAIN=${MINGAIN}% SANDBOX=$SBX H=$H ==="
say "df TRUOC: $(df -h / | tail -1)"
say "RAM: $(free -m | awk '/^Mem:/{print "available " $7 " MB"}'); swap: $(free -m | awk '/^Swap:/{print $2 " MB, dung " $3 " MB"}')"
if [ "$APPLY" = 1 ] && rlive_on; then say "TU CHOI --apply: co process khop '$RLIVE_PAT' (R-LIVE dang chay) - khong lam gi"; exit 3; fi
ERR=0; STOP=0
if want 1; then run_item m1; fi
if want 3; then run_item m3; fi
if want 2b; then run_item m2b; fi
if want 5a; then run_item m5a; fi
CAND=$TMPD/cand.tsv; : > "$CAND"
if want 2 || want 4 || want 5b || want 5c; then
  say "--- NEN LOSSLESS (muc 2, 4, 5b, 5c) - tu nho den lon"
  U=$TMPD/cand.u; : > "$U"
  addc() { local s=0; if [ -d "$3" ] && [ ! -L "$3" ]; then s=$(dsz "$3"); fi; printf '%s\t%s\t%s\t%s\t%s\n' "${s:-0}" "$1" "$2" "$3" "$4" >> "$U"; }
  if want 2; then for s in work regr_d1 regr_d3 tsx logs; do addc 2 "parity_v11w/$s" "$CM/parity_v11w/$s" "$ARC/parity_v11w__$s.tar.zst"; done; fi
  if want 4; then
    for p in "$CM"/pull242/20[0-9][0-9]-[0-9][0-9]-[0-9][0-9]; do
      [ -e "$p" ] || continue
      dd=$(basename -- "$p"); if [[ ! "$dd" < "2026-11-18" ]]; then continue; fi
      addc 4 "pull242/$dd" "$p" "$ARC/pull242/$dd.tar.zst"
    done
  fi
  if want 5b; then addc 5b java/devrun "$H/java/devrun" "$ARC/java__devrun.tar.zst"; fi
  if want 5c; then addc 5c vz/pilot_upload "$H/vz/pilot_upload" "$ARC/vz__pilot_upload.tar.zst"; fi
  sort -n -k1,1 "$U" | cut -f2- > "$CAND"
  say "  ung vien: $(wc -l < "$CAND")"
  CH=$TMPD/child.sh
  { echo 'set -euo pipefail'; echo 'export LC_ALL=C'
    declare -p H CM ARC SBX APPLY MINGAIN MINFREE MINRAM RLIVE_PAT FORBID LIVE_DIRS GINC GEXC RES HSH
    declare -f say gb ab res rlive_on esc guard live_grep proc_uses ratio_est fsnap pack start12 comp_one comp_loop
    echo 'TMPD=$(mktemp -d); trap '"'"'rm -rf "$TMPD"'"'"' EXIT'
    echo 'comp_loop "$1"'; } > "$CH"
  rc=0
  if [ "$APPLY" = 1 ]; then
    if rlive_on; then say "  DUNG phan nen: co process '$RLIVE_PAT'"; rc=40
    else set +e; flock -w 3600 "$LOCK" nice -n 10 bash "$CH" "$CAND"; rc=$?; set -e; fi
  else
    set +e; nice -n 10 bash "$CH" "$CAND"; rc=$?; set -e
  fi
  case "$rc" in 0) ;; 1) ERR=1;; 40) STOP=1; say "  DA DUNG phan nen (dieu kien) - cac muc con lai giu nguyen";; *) ERR=1; say "  phan nen: rc=$rc (flock het gio / loi)";; esac
fi
if want 5d; then run_item m5d; fi
TAG="du kien"; if [ "$APPLY" = 1 ]; then TAG="thuc"; fi
say "=== BANG ($TAG): muc | ten | trang thai | GiB goc | GiB thu"
TOT=0
while IFS=$'\t' read -r m n st s g; do
  say "    $m | $n | $st | $(gb "$s") | $(gb "$g")"
  case "$st" in SE_*|DA_*) TOT=$((TOT + g));; esac
done < "$RES"
for m in 1 2 2b 3 4 5a 5b 5c 5d; do
  t=$(awk -F'\t' -v m="$m" '$1 == m && ($3 ~ /^SE_/ || $3 ~ /^DA_/) {s += $5} END{printf "%.0f", s + 0}' "$RES")
  say "  muc $m: $TAG thu $(gb "$t")"
done
say "=== TONG $TAG thu: $(gb "$TOT")"
say "df SAU: $(df -h / | tail -1)"
say "Log: $LOG"
if [ "$ERR" != 0 ]; then say "KET THUC: co ABORT / lech (da giu goc) - xem ABORT/LOI o tren"; exit 1; fi
if [ "$STOP" != 0 ]; then exit 2; fi
exit 0
