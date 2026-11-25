#!/usr/bin/env bash
# Test tiem loi pilot_m_daily.py tren du lieu TONG HOP (khong doc log that). In "KET QUA x/y".
set -uo pipefail
HERE="$(dirname "$(readlink -f "$0")")"
TMP="$(mktemp -d)"
python3 -I "$HERE/pm_tests.py" "$TMP"
RC=$?
rm -rf -- "$TMP"
exit $RC
