#!/bin/bash
# E2E_REPLAY_V12 ERRATA3 E11 - KHOA CHAY 1 LAN cho luot chinh thuc 11-05 (thay khoi khoa trong run_official_1105.sh, A1 R2 L1).
# usage: official_lock.sh <LOCKFILE> <ERRATA|""> <HEAD> <A1_APPROVED>
#   rc 0  = DUOC chay: dong khoa da GHI va DOC LAI thay dung dong (ke ca khi file khoa da chmod a-w tu lan truoc).
#   rc !=0 = TU CHOI: da chay ma khong co errata; errata da dung; ghi/doc lai khoa loi; khoa khong phai file thuong.
# Moi errata mo lai DUNG 1 lan (dong "errata=<ten> " duy nhat). Kiem + ghi trong flock rieng (<LOCK>.flock).
set -u
LOCK=$1; ERR=${2:-}; HEAD=${3:-?}; A1=${4:-?}
D=$(dirname "$LOCK")
mkdir -p "$D" 2>/dev/null
[ -d "$D" ] || { echo "TU CHOI: khong co thu muc khoa $D"; exit 2; }
case "$ERR" in *[[:space:]]*|*=*) echo "TU CHOI: ten errata khong hop le '$ERR'"; exit 2;; esac
exec 9>>"$LOCK.flock" || { echo "TU CHOI: khong mo duoc $LOCK.flock"; exit 2; }
flock -w 30 9 || { echo "TU CHOI: khong lay duoc flock $LOCK.flock"; exit 2; }
if [ -e "$LOCK" ] || [ -L "$LOCK" ]; then
  [ -f "$LOCK" ] && [ ! -L "$LOCK" ] || { echo "TU CHOI: $LOCK khong phai file thuong"; exit 2; }
  [ -n "$ERR" ] || { echo "TU CHOI: luot chinh thuc DA chay (khoa $LOCK). Mo lai chi voi E2E_ERRATA=<errata moi cua MASTER>"; cat "$LOCK"; exit 2; }
  grep -qF "errata=$ERR " "$LOCK" && { echo "TU CHOI: errata '$ERR' da dung de mo lai (khoa $LOCK)"; exit 2; }
  chmod u+w "$LOCK" || { echo "TU CHOI: khong mo quyen ghi khoa $LOCK"; exit 2; }
fi
LINE="$(date -Is) head=$HEAD a1=$A1 errata=$ERR host=$(hostname) pid=$$"
if ! printf '%s\n' "$LINE" >> "$LOCK"; then
  chmod a-w "$LOCK" 2>/dev/null
  echo "TU CHOI: GHI khoa that bai ($LOCK) => khong chay"; exit 2
fi
sync "$LOCK" 2>/dev/null
chmod a-w "$LOCK" || { echo "TU CHOI: khong chmod a-w duoc khoa $LOCK"; exit 2; }
grep -qxF "$LINE" "$LOCK" || { echo "TU CHOI: doc lai khoa khong thay dong vua ghi"; exit 2; }
[ "$(grep -cF "errata=$ERR " "$LOCK")" = 1 ] || { echo "TU CHOI: errata '$ERR' xuat hien != 1 lan trong khoa"; exit 2; }
echo "KHOA OK: $LINE"
exit 0
