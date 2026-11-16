#!/bin/bash
# E2E_REPLAY_V12 - LUOT CHINH THUC fixture 11-05 (prereg §2, §8 buoc 4). CHI chay khi A1 DA DUYET harness + REF.
# usage (A1/MASTER):  A1_APPROVED=<commit da duyet> tools/e2e/run_official_1105.sh
# 1 lenh: dung fixture 11-05 (khong ghi de neu da co) -> moi luot §4 + REF + bo cham, qua lock Oracle (1 flock, khong long).
# Truoc khi chay: tao (neu can) tools/e2e/labels_1105.csv (symbol,label) cho cac SUBMIT dry that duoc phep lech theo nhan KHAI TRUOC
#   {LEGACY-11-05, JAR-R4Q-FIN2-BIGDOWN-SEL, JAR-R4Q-FIN2-UNIVERSE-A1, EXCHANGEINFO} — PHAI commit truoc khi chay.
set -u
[ -n "${A1_APPROVED:-}" ] || { echo "TU CHOI: thieu A1_APPROVED=<commit> (A1 chua duyet harness + REF)"; exit 2; }
W=$(cd "$(dirname "$0")/../.." && pwd)
HEAD=$(git -C "$W" rev-parse --short HEAD)
[ -z "$(git -C "$W" status --porcelain -- src/test tools/e2e)" ] || { echo "TU CHOI: worktree co thay doi chua commit (src/test, tools/e2e)"; exit 2; }
case "$A1_APPROVED" in "$HEAD"*) ;; *) echo "TU CHOI: HEAD $HEAD != commit A1 duyet $A1_APPROVED"; exit 2;; esac
FX=$HOME/claude_master/e2e_v12/fx1105
OUT=$HOME/claude_master/e2e_v12/out1105_$(date +%m%d_%H%M)
[ -e "$OUT" ] && { echo "TU CHOI: $OUT da ton tai"; exit 2; }
mkdir -p ~/claude_master/locks "$OUT"
flock -w 3600 ~/claude_master/locks/oracle_heavy.lock nice -n 10 bash -c "
  set -u
  if [ ! -f '$FX/manifest.json' ]; then
    python3 '$W/tools/e2e/prep_fixture.py' --out '$FX' --start '2026-11-05 07:00' --end '2026-11-14 07:00' --buffer-day 2026-11-05 --dry-submits
  fi
  '$W/tools/e2e/build_v12.sh' --no-lock || exit 9
  E2E_OFFICIAL=1 E2E_FX_DIR='$FX' E2E_OUT='$OUT' SDCA_AT=1793894400000 FIN_INJ_AT=1793836800000 '$W/tools/e2e/run_all.sh'
" > "$OUT/official.log" 2>&1
echo "RC=$? out=$OUT (xem $OUT/check_v12.txt, $OUT/official.log)"
# Moc khai truoc: SDCA_AT = 2026-11-05 23:00 +07 (sau cum SUBMIT 22:52-22:53), FIN_INJ_AT = START 2026-11-05 07:00 +07
#   (leg PREDICT PASS dau tien cua cua so bi bo khoi tap fin). Doi moc = errata TRUOC khi chay.
