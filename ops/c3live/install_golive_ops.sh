#!/usr/bin/env bash
# =============================================================================
# install_golive_ops.sh - [WAVE1 16/11 B-13] OWNER chay tren ORACLE: dong bo ban cai trong ~/claude_master/deploy/ voi repo
#   (nhanh v1.2/wave1, ~/claude_master/fin1114/c3_fin/ops/c3live). KHONG cham 242, KHONG restart.
#   DRY=1 bash ~/claude_master/fin1114/c3_fin/ops/c3live/install_golive_ops.sh   # chi liet ke file nao lech (md5 cu -> moi), KHONG ghi
#   bash ~/claude_master/fin1114/c3_fin/ops/c3live/install_golive_ops.sh         # go YES: chep (ban cu => <file>.bak_wave1_<TS>)
# File dong bo (repo -> deploy/), md5 repo PHAI = PIN ben duoi (repo bi sua ngoai quy trinh => TU CHOI, khong chep gi):
#   deploy_chain.sh (CHECK_R mac dinh ingfin + pin moi), ingfin_check_remote.sh (51ff3962), set_telegram_env_242.sh (EXPECT_SHA8 bdee1480),
#   deploy_ingest_fin.sh (TG_SHA8 bdee1480, CHECK_R ingfin 51ff3962).
# Script go-live (golive_*.sh, dry_enable_grid_sizing.sh, golive_make_gate.sh, rollback_vtm_r4u3.sh) chay THANG tu repo, khong chep.
# Cron golive_monitor: neu md5(monitor+lib)[:12] cua repo DA co trong deploy/gates/A1_APPROVED_MONITOR.md5 => goi
#   install_cron_golive_monitor.sh (idempotent, pin ban moi; DRY=1 chi in); CHUA duoc A1 duyet => GIU cron/pin cu, in lenh cho A1.
#   (micro_on cung tu pin lai luc bat; cron chi chay khi co co micro/pilot.)
# Ma thoat: 0 OK | 1 loi / TU CHOI.
# =============================================================================
set -uo pipefail
H=$(cd "$(dirname "$0")" && pwd)
# [WAVE1b M5] nhu gl_manifest_check (golive_lib): script nay + lib + moi file manifest khop md5 da commit, lech => TU CHOI truoc moi viec
MF=$H/GOLIVE_MANIFEST.md5
{ [ -s "$MF" ] && grep -qxE "[0-9a-f]{32}  install_golive_ops.sh" "$MF" && grep -qxE "[0-9a-f]{32}  golive_lib.sh" "$MF" \
  && (cd "$H" && md5sum -c --quiet --strict "$MF" >/dev/null 2>&1); } \
  || { echo "TU CHOI [M5]: file go-live KHAC manifest da commit ($MF): $(cd "$H" && md5sum -c --strict "$MF" 2>&1 | grep -v ': OK$' | head -5 | tr '\n' ' ') — KHONG lam gi."; exit 1; }
D=${DEPLOY_DIR:-/home/ubuntu/claude_master/deploy}
A1F=${A1_APPROVED_FILE:-$D/gates/A1_APPROVED_MONITOR.md5}
DRY=${DRY:-0}
TS=$(TZ=Asia/Ho_Chi_Minh date +%Y%m%d_%H%M%S)
# [WAVE1] pin md5 tung file repo (cap nhat CUNG commit khi sua file)
PINS="deploy_chain.sh=ba6b511bb434dc5e6d49747e6bdd715b
ingfin_check_remote.sh=51ff39620a69efacb84563f311fd15b4
set_telegram_env_242.sh=db51cf1cbad86b3c3620c16d0fa25792
deploy_ingest_fin.sh=437cdbfb380d97281c21715cdbbb8853"
FILES=$(printf '%s\n' "$PINS" | cut -d= -f1)
m5() { [ -f "$1" ] && md5sum < "$1" | cut -c1-32 || echo "(khong_co)"; }
N=0; BAD=0
echo "=== install_golive_ops TS=$TS DRY=$DRY  repo=$H  dich=$D"
for f in $FILES; do
  [ -f "$H/$f" ] || { echo "LOI: thieu $H/$f"; exit 1; }
  p=$(printf '%s\n' "$PINS" | sed -n "s/^$f=//p"); a=$(m5 "$D/$f"); b=$(m5 "$H/$f")
  [ "$b" = "$p" ] || { echo "  PIN!   $f repo=$b != pin $p"; BAD=1; continue; }
  if [ "$a" = "$b" ]; then echo "  GIONG  $f $b"; else echo "  LECH   $f deploy=$a -> repo=$b"; N=$((N + 1)); fi
done
[ "$BAD" = 0 ] || { echo "TU CHOI: file repo khac pin (sua ngoai quy trinh?) - KHONG chep gi"; exit 1; }
echo "Ghi chu: deploy/swap_v12_dry_jar.sh khong ton tai (swap chay tu repo); deploy/rollback_v12.sh khong dung nua (DEPRECATED)."
grep -ln '4f49bded' "$D"/*.sh 2>/dev/null | sed 's/^/  CON pin token cu 4f49bded: /'
cron_step() {
  local m12; m12=$(cat "$H/golive_monitor.sh" "$H/golive_lib.sh" | md5sum | cut -c1-12)
  if [ -f "$A1F" ] && grep -qE "^$m12([[:space:]]|$)" "$A1F"; then
    echo "--- cron golive_monitor: md5(monitor+lib)=$m12 DA qua A1 => pin ban repo (DRY=$DRY)"
    DRY=$DRY bash "$H/install_cron_golive_monitor.sh" 2>&1 | sed 's/^/   cron| /'; return "${PIPESTATUS[0]}"
  fi
  echo "--- cron golive_monitor: md5(monitor+lib)=$m12 CHUA co trong $A1F => GIU cron/pin cu."
  echo "    Sau khi A1 duyet: A1 them dong '$m12  # ...' vao $A1F roi chay lai lenh nay (hoac micro_on tu pin)."
  return 0
}
if [ "$N" = 0 ]; then echo "=== KHONG DOI (da dong bo)"; cron_step; exit $?; fi
[ "$DRY" = 1 ] && { echo "=== DRY=1: $N file se duoc chep (khong ghi gi)"; cron_step; exit $?; }
echo ">>> Chep $N file repo -> $D (ban cu => .bak_wave1_$TS). Go YES:"; read -r ANS || ANS=""
[ "$ANS" = YES ] || { echo "Huy. Khong doi gi."; exit 0; }
for f in $FILES; do
  [ "$(m5 "$D/$f")" = "$(m5 "$H/$f")" ] && continue
  [ -f "$D/$f" ] && cp -p "$D/$f" "$D/$f.bak_wave1_$TS"
  cp -p "$H/$f" "$D/$f.tmp_$TS" && mv -f "$D/$f.tmp_$TS" "$D/$f" || { echo "LOI chep $f"; exit 1; }
  [ "$(m5 "$D/$f")" = "$(m5 "$H/$f")" ] && echo "  OK $f $(m5 "$D/$f")" || { echo "LOI md5 sau chep $f"; exit 1; }
done
cron_step || { echo "LOI cai cron golive_monitor (file deploy DA chep xong)"; exit 1; }
echo "=== XONG"
