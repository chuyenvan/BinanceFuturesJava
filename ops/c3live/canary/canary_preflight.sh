#!/usr/bin/env bash
# =============================================================================
# canary_preflight.sh — G-CANARY buoc K0 (CHI DOC, ~65') + chon 2 symbol theo LUAT §3 (hang 1 = chinh, hang 2 = phu cho K7b)
# + kiem dieu kien vao §2 (file gate MASTER, jar md5 pin, bot o adapter dry >= 5 ngay sach, khong adapter live, khung gio).
# Chay tren ORACLE:
#   CANARY_EXPECT_TMB=<so da nap, vd 10000> bash ops/c3live/canary/canary_preflight.sh          (chi kiem dieu kien vao)
#   CANARY_EXPECT_TMB=<...> YES=1 bash ops/c3live/canary/canary_preflight.sh                    (kiem + chay K0 65')
# K0 KHONG gui lenh nao. Neu K0 TRUOT vi marginType/leverage: YES=1 bash canary_step.sh SETUP (dat CROSSED / 1x cho 2 symbol) roi chay lai.
# Ket qua: "KET QUA: DAT|TRUOT|TU_CHOI" + symbol da chon + du lieu tho luat chon (dong DATA).
# =============================================================================
. "$(cd "$(dirname "$0")" && pwd)/canary_lib.sh"
cl_init preflight
ET=${CANARY_EXPECT_TMB:-}
[[ "$ET" =~ ^[0-9]+(\.[0-9]+)?$ ]] || die "thieu/sai CANARY_EXPECT_TMB (so da nap vao tai khoan con, vd 10000) — §4 K0 tmb ~ so da nap +-1 %"
cl_time_gate die
cl_gates
cl_check_242 dry
if [ "$YES" != 1 ]; then
  say "CHI KIEM: dieu kien vao §2 DAT. Chay K0 that (chi doc, ~65'): YES=1 CANARY_EXPECT_TMB=$ET bash $0"
  say "KET QUA: DAT (chi kiem dieu kien vao — K0 CHUA chay)"
  exit 0
fi
cl_push_logback
cl_run "CANARY_EXPECT_TMB=$ET" preflight; RC=$?
V=$(cl_verdict $RC)
D=$(printf '%s' "$CL_LAST_OUT" | grep '^DATA ' | tail -1)
python3 -I - "$D" <<'EOF' 2>/dev/null
import json, sys
d = sys.argv[1][5:] if sys.argv[1].startswith("DATA ") else "{}"
try:
    m = json.loads(d)
except Exception:
    m = {}
for k in ("symMain", "symAux", "pick.scanned", "pick.eligible", "pick.rejects", "pick.top", "tmb", "tmbDiffFrac", "tmb0", "assets",
          "multiAssetsMargin", "dualSidePosition", "ws.openMs", "ws.url", "ws.keepAliveOk"):
    if k in m: print("   %s = %s" % (k, json.dumps(m[k], ensure_ascii=False)[:600]))
for k in sorted(m):
    if k.startswith("symbolConfig."): print("   %s = %s" % (k, m[k]))
EOF
say "KET QUA: $V ($CL_LAST_RESULT)"
[ "$V" = DAT ] && say "Tiep: YES=1 bash $(dirname "$0")/canary.sh  (K1..K8; tiem timeout MO-5: them CANARY_INJECT_TIMEOUT=1)"
say "Log: $CL_LOG"
[ "$V" = DAT ]
