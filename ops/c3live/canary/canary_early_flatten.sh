#!/usr/bin/env bash
# =============================================================================
# canary_early_flatten.sh — KHAN CAP cho CANARY-EARLY (MIN-C4), 1 lenh tren ORACLE:
#   bash ops/c3live/canary/canary_early_flatten.sh        (go YES)
# Tu dat CANARY_MODE=early (thu muc rieng /home/chuyennd/java/c3canary) roi chay canary_flatten.sh:
#   (1) dat file ~/claude_master/canary/CANARY_STOP (phien nen dung sau buoc dang chay, khong mo them);
#   (2) kill JVM canary TREO (chi cwd = c3canary, giu lock >= 10', heartbeat cu >= 3' — MIN-C3; KHONG bao gio dung v_t_m);
#   (3) dong het vi the 2 symbol canary (reduce-only) + huy stop c3s- qua guard; in trang thai.
# Khong chot gio (khan cap). Ket qua: "KET QUA: DAT|TRUOT|TU_CHOI".
# =============================================================================
export CANARY_MODE=early
HERE=$(cd "$(dirname "$0")" && pwd)
if [ "${YES:-0}" != 1 ]; then
  echo "CANARY-EARLY KHAN CAP: dong het vi the canary (tien that, reduce-only)."
  read -r -p "Go YES (in hoa) de flatten: " ANS || ANS=""
  [ "$ANS" = YES ] || { echo "khong go YES — khong lam gi"; exit 2; }
fi
YES=1 exec bash "$HERE/canary_flatten.sh"
