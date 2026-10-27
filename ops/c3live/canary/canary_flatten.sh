#!/usr/bin/env bash
# =============================================================================
# canary_flatten.sh — KHAN CAP: dong het vi the 2 symbol canary (reduce-only), huy stop c3s- qua guard (chi khi vi the da 0),
# in trang thai cuoi. KHONG cham symbol / vi the / lenh nao khac. Khong chot gio (khan cap). Chay ca khi phien da DUNG.
#   YES=1 bash ops/c3live/canary/canary_flatten.sh
# Ket qua: "KET QUA: DAT|TRUOT|TU_CHOI".
# =============================================================================
. "$(cd "$(dirname "$0")" && pwd)/canary_lib.sh"
cl_init flatten
need_yes "gui lenh dong vi the THAT"
if [ "$CANARY_MODE" = early ]; then
  # canary-early: phien chay nen co the dang chay => dat file STOP truoc (phien dung sau buoc hien tai, khong mo them)
  touch "$LOGDIR/CANARY_STOP" && say "da dat $LOGDIR/CANARY_STOP (phien canary_early_run dung o buoc ke; xoa co chu dich truoc phien moi)"
  # [3c MIN-C3] JVM canary TREO (cwd = c3canary, giu lock >= 10', heartbeat cu >= 3') => kill truoc khi flatten; JVM con song => giu
  cl_kill_hung
  cl_probe
  if [ "$(pv CANARY_JVM)" != 0 ]; then
    say "JVM canary dang chay BINH THUONG (heartbeat moi) — phien nen se dung sau buoc nay va TU flatten (file STOP)."
    say "Cho 1-2 phut roi chay lai lenh nay neu van con vi the."
  fi
fi
cl_check_242
cl_push_logback
cl_run "" flatten; RC=$?
V=$(cl_verdict $RC)
say "flatten: $V ($CL_LAST_RESULT)"
cl_run "" status >/dev/null; say "trang thai phien (run/canary/canary_state.json):"
printf '%s' "$CL_LAST_OUT" | grep -v '^RESULT ' | cut -c1-2000 | sed 's/^/   /'
say "KET QUA: $V"
[ "$V" = DAT ] || say "!! KHONG DAT — kiem tra tay tren web Binance (tai khoan con), bao MASTER"
say "Log: $CL_LOG"
[ "$V" = DAT ]
