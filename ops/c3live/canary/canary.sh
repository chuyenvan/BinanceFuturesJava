#!/usr/bin/env bash
# =============================================================================
# canary.sh — G-CANARY chuoi K1 -> K8 (prereg §4) bang JVM rieng C3LiveCanary tren 242 (thu muc run/canary/, KHONG dung JVM dry).
# Dieu kien: canary_preflight.sh (K0) DAT. Chay tren ORACLE (owner thuc + co mat, ~2-3 h):
#   YES=1 bash ops/c3live/canary/canary.sh
#   YES=1 CANARY_INJECT_TIMEOUT=1 bash ops/c3live/canary/canary.sh   (MO-5: tiem timeout phia client 1 lan trong K1 — mac dinh TAT)
# Thu tu: K1 K2 K3 K4 K5 K6(OPEN+kill+RESTART) K6b(OPEN+kill+doi ten so+RESTART+dong tay) K7 K7b K8.
# Dung o buoc dau tien KHONG DAT => tu chay flatten (chi 2 symbol canary) + in TRUOT. Giua cac buoc: ngoai khung gio => cho.
# Gioi han CUNG nam trong code (khong config): 20 USDT/lenh (<= 25), tong mo <= 40, tran lo 2 USDT, chi 2 symbol theo luat.
# Ket qua: "KET QUA: DAT|TRUOT|TU_CHOI". Sau DAT: canary_report.sh roi canary_cleanup.sh.
# =============================================================================
. "$(cd "$(dirname "$0")" && pwd)/canary_lib.sh"
cl_init canary
[ "$CANARY_MODE" = standard ] || die "canary.sh chi cho G-CANARY chuan; canary-early dung canary_early_run.sh"
need_yes "gui LENH THAT (tien that, 20 USDT/lenh)"
[[ "${CANARY_INJECT_TIMEOUT:-0}" =~ ^[01]$ ]] || die "CANARY_INJECT_TIMEOUT chi 0/1"
cl_time_gate die
cl_gates
cl_check_242 dry
cl_push_logback
SEQ=${CANARY_SEQ:-"K1 K2 K3 K4 K5 K6 K6B K7 K7B K8"}
for k in $SEQ; do
  case "$k" in K1|K2|K3|K4|K5|K6|K6B|K7|K7B|K8) ;; *) die "CANARY_SEQ co buoc la: $k" ;; esac
done
declare -A RES
FAIL=""
for k in $SEQ; do
  cl_time_gate wait || { FAIL="$k(ngoai khung gio qua ${TIME_WAIT_MAX_S}s)"; break; }
  say "==== buoc $k"
  cl_macro "$k"; RC=$?
  RES[$k]=$(cl_verdict $RC)
  say "==== $k: ${RES[$k]}  ($CL_LAST_RESULT)"
  if [ "$RC" != 0 ]; then FAIL="$k"; break; fi
done
if [ -n "$FAIL" ]; then
  say "DUNG o buoc $FAIL — dong het vi the 2 symbol canary (flatten)"
  cl_run "" flatten; RF=$?
  say "flatten: $(cl_verdict $RF) ($CL_LAST_RESULT)"
  [ "$RF" = 0 ] || say "!! flatten KHONG DAT — owner chay ngay: YES=1 bash $(dirname "$0")/canary_flatten.sh ; bao MASTER"
fi
say "---- tong ket"
for k in $SEQ; do say "   $k: ${RES[$k]:-CHUA_CHAY}"; done
if [ -z "$FAIL" ]; then
  say "KET QUA: DAT (chuoi K1..K8) — tiep: bash $(dirname "$0")/canary_report.sh ; YES=1 bash $(dirname "$0")/canary_cleanup.sh"
  say "Log: $CL_LOG"; exit 0
fi
case "${RES[$FAIL]:-}" in TU_CHOI) V=TU_CHOI ;; *) V=TRUOT ;; esac
say "KET QUA: $V (buoc $FAIL) — gui log + canary_report.sh cho MASTER/A1"
say "Log: $CL_LOG"
exit 3
