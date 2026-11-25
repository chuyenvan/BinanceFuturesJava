#!/usr/bin/env bash
# Vo chay pilot_m_daily.py. Dung: pilot_m_daily.sh <yyyy-mm-dd> [tham so them, vd --official --pilot-on-start "2026-11-26 09:20"]
set -euo pipefail
D="${1:?thieu ngay yyyy-mm-dd}"; shift
exec python3 -I "$(dirname "$(readlink -f "$0")")/pilot_m_daily.py" "$D" "$@"
