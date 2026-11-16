#!/bin/bash
# ERRATA3 E11 - thu khoa chay 1 lan (official_lock.sh) tren THU MUC TAM (khong dung khoa that). In bang ca / ky vong / rc.
set -u
W=$(cd "$(dirname "$0")/../.." && pwd); S=$W/tools/e2e/official_lock.sh
T=$(mktemp -d /tmp/e2e4_lock_XXXX); L=$T/OFFICIAL_1105.lock
ok=0; n=0
t() { local name=$1 want=$2; shift 2; "$S" "$@" > "$T/out.txt" 2>&1; local rc=$?; n=$((n+1))
  local got=$([ $rc = 0 ] && echo CHAY || echo TU_CHOI); [ "$got" = "$want" ] && ok=$((ok+1))
  printf '%-58s ky_vong=%-8s ket_qua=%-8s %s | %s\n' "$name" "$want" "$got" "$([ "$got" = "$want" ] && echo DUNG || echo SAI)" "$(head -c 110 "$T/out.txt" | tr '\n' ' ')"; }
t "L1 lan dau (khong errata)"                         CHAY    "$L" ""  h1 h1
t "L2 lan 2 khong errata"                             TU_CHOI "$L" ""  h1 h1
t "L3 errata E_A (khoa da chmod a-w)"                 CHAY    "$L" E_A h1 h1
t "L4 errata E_A lan 2"                               TU_CHOI "$L" E_A h1 h1
t "L5 errata E_B"                                     CHAY    "$L" E_B h1 h1
t "L6 errata E_B lan 2"                               TU_CHOI "$L" E_B h1 h1
t "L7 errata ten co dau cach / dau ="                  TU_CHOI "$L" "E C" h1 h1
chmod a-w "$L"; t "L8 errata E_C khi khoa a-w (A1 L1)"   CHAY    "$L" E_C h1 h1
t "L9 errata E_C lan 2 (sau L8)"                      TU_CHOI "$L" E_C h1 h1
echo "  khoa: $(wc -l < "$L") dong, quyen $(stat -c %A "$L"), errata: $(grep -o 'errata=[^ ]*' "$L" | tr '\n' ' ')"
# ghi khoa THAT BAI => khong duoc chay
D2=$T/ro; mkdir -p $D2; : > $D2/OFFICIAL_1105.lock.flock; chmod a-w $D2
t "L10 thu muc khoa chi doc (ghi khoa lan dau loi)"    TU_CHOI "$D2/OFFICIAL_1105.lock" "" h1 h1
D3=$T/dirlock; mkdir -p $D3/OFFICIAL_1105.lock
t "L11 khoa la thu muc (ghi loi) + errata"             TU_CHOI "$D3/OFFICIAL_1105.lock" E_X h1 h1
D4=$T/ro2; mkdir -p $D4; "$S" $D4/OFFICIAL_1105.lock "" h1 h1 > /dev/null; chmod a-w $D4/OFFICIAL_1105.lock.flock
t "L12 flock khong mo duoc (a-w) + errata"             TU_CHOI "$D4/OFFICIAL_1105.lock" E_Y h1 h1
chmod u+w $D2 $D4/OFFICIAL_1105.lock.flock
echo "TONG: $ok/$n ca dung ky vong (thu muc tam $T)"
rm -rf "$T" 2>/dev/null || chmod -R u+w "$T"
