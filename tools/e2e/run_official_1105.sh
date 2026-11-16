#!/bin/bash
# E2E_REPLAY_V12 - LUOT CHINH THUC fixture 11-05 (prereg ?2, ?8 buoc 4 + ERRATA1 E5). CHI chay khi A1 DA DUYET harness + REF.
# usage (A1/MASTER):  A1_APPROVED=<commit da duyet> tools/e2e/run_official_1105.sh
#   mo lai sau khi da chay (CHI khi co errata MOI cua MASTER):  E2E_ERRATA=<ten errata> A1_APPROVED=<commit> tools/e2e/run_official_1105.sh
# KHOA CHAY 1 LAN (ERRATA1 E5): file khoa CO DINH $LOCK tao NGAY khi bat dau (truoc fixture/build/chay). Da co khoa => TU CHOI,
#   tru khi E2E_ERRATA dat va CHUA tung dung trong khoa (moi errata mo lai dung 1 lan; tools/e2e/official_lock.sh, ERRATA3 E11). Ten errata + khoa ghi vao result.json
#   (errata_mo_lai, official_lock) va check_v12.json.
# 1 lenh: dung fixture 11-05 (khong ghi de neu da co) -> moi luot ?4 + REF + bo cham, qua lock Oracle (1 flock, khong long).
# Truoc khi chay: tao (neu can) tools/e2e/labels_1105.csv (symbol,label) cho cac SUBMIT dry that duoc phep lech theo nhan KHAI TRUOC
#   {LEGACY-11-05, JAR-R4Q-FIN2-BIGDOWN-SEL, JAR-R4Q-FIN2-UNIVERSE-A1, EXCHANGEINFO} ? PHAI commit truoc khi chay.
set -u
[ -n "${A1_APPROVED:-}" ] || { echo "TU CHOI: thieu A1_APPROVED=<commit> (A1 chua duyet harness + REF)"; exit 2; }
W=$(cd "$(dirname "$0")/../.." && pwd)
HEAD=$(git -C "$W" rev-parse --short HEAD)
[ -z "$(git -C "$W" status --porcelain -- src/test tools/e2e)" ] || { echo "TU CHOI: worktree co thay doi chua commit (src/test, tools/e2e)"; exit 2; }
case "$A1_APPROVED" in "$HEAD"*) ;; *) echo "TU CHOI: HEAD $HEAD != commit A1 duyet $A1_APPROVED"; exit 2;; esac
LOCK=$HOME/claude_master/e2e_v12/OFFICIAL_1105.lock
ERR=${E2E_ERRATA:-}
# [ERRATA3 E9] tien kiem (CHI ls, khong dung fixture o day): labels_1105.csv da commit + hop le; nguon LEGACY 11-05 ton tai
git -C "$W" ls-files --error-unmatch tools/e2e/labels_1105.csv > /dev/null 2>&1 || { echo "TU CHOI: tools/e2e/labels_1105.csv chua commit"; exit 2; }
python3 -c "import sys; sys.path.insert(0, '$W/tools/e2e'); import check_v12 as C; ok, _, d = C.labels_check('$W/tools/e2e/labels_1105.csv'); print(d); sys.exit(0 if ok else 1)" \
  || { echo "TU CHOI: labels_1105.csv bi tu choi (nhan ngoai tap khai truoc)"; exit 2; }
ls $HOME/claude_master/pull242/2026-11-05/run/legacy_symbols.csv $HOME/claude_master/pull242/2026-11-05/logs/full.log@*.gz 2>/dev/null | grep -q . \
  || { echo "TU CHOI: khong co nguon LEGACY 11-05 (pull242/2026-11-05)"; exit 2; }
# [ERRATA3 E11] khoa chay 1 lan: GHI khoa phai thanh cong (doc lai thay dong) moi duoc chay; moi errata mo lai dung 1 lan
"$W/tools/e2e/official_lock.sh" "$LOCK" "$ERR" "$HEAD" "$A1_APPROVED" || exit 2
FX=$HOME/claude_master/e2e_v12/fx1105
OUT=$HOME/claude_master/e2e_v12/out1105_$(date +%m%d_%H%M)
[ -e "$OUT" ] && { echo "TU CHOI: $OUT da ton tai"; exit 2; }
mkdir -p ~/claude_master/locks "$OUT"
cp "$LOCK" "$OUT/OFFICIAL_1105.lock.copy"
flock -w 3600 ~/claude_master/locks/oracle_heavy.lock nice -n 10 bash -c "
  set -u
  if [ ! -f '$FX/manifest.json' ]; then
    python3 '$W/tools/e2e/prep_fixture.py' --out '$FX' --start '2026-11-05 07:00' --end '2026-11-14 07:00' --buffer-day 2026-11-05 --dry-submits
  fi
  '$W/tools/e2e/build_v12.sh' --no-lock || exit 9
  E2E_ERRATA='$ERR' E2E_OFFICIAL_LOCK='$LOCK' E2E_OFFICIAL=1 E2E_FX_DIR='$FX' E2E_OUT='$OUT' SDCA_AT=1793894400000 FIN_INJ_AT=1793836800000 '$W/tools/e2e/run_all.sh'
" > "$OUT/official.log" 2>&1
echo "RC=$? out=$OUT (xem $OUT/check_v12.txt, $OUT/official.log)"
# Moc khai truoc: SDCA_AT = 2026-11-05 23:00 +07 (sau cum SUBMIT 22:52-22:53), FIN_INJ_AT = START 2026-11-05 07:00 +07
#   (leg PREDICT PASS dau tien cua cua so bi bo khoi tap fin). Doi moc = errata TRUOC khi chay.
