#!/usr/bin/env bash
# Chay 17 mutant A1 tren bo test tong hop. In bang mutant -> ca test giet. (~ vai phut, PM_PAR luong song song)
set -uo pipefail
HERE="$(dirname "$(readlink -f "$0")")"
TMP="$(mktemp -d)"
nice -n 10 python3 -I "$HERE/run_mutants.py" "$TMP"
RC=$?
rm -rf -- "$TMP"
exit $RC
