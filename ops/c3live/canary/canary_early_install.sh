#!/usr/bin/env bash
# =============================================================================
# canary_early_install.sh — CANARY-EARLY (prereg §ADD-1) LENH 1/2. Chay tren ORACLE, 1 lenh:
#   YES=1 CANARY_EXPECT_TMB=<so da nap tai khoan con, vd 10000> bash ops/c3live/canary/canary_early_install.sh
# Lam: (1) kiem cuc bo: jar Oracle md5 = pin, file gate CODE (MASTER tao sau khi A1 DAT), khung gio;
#      (2) kiem 242 CHI DOC: v_t_m chay c3_shadow + SHADOW_NO_PUSH=true, khong LIVE_ADAPTER, MemAvailable >= 1 GB, o dia, khong JVM canary;
#          chup md5 jar/env/start + PID v_t_m;
#      (3) tao thu muc RIENG /home/chuyennd/java/c3canary (700), copy jar + kiem md5 tren 242, logback, ban sao LEGACY (chi doc v_t_m);
#      (4) keycheck (chi doc) + K0 preflight (CHI DOC, ~65', chon 2 symbol theo luat §3);
#      (5) so lai v_t_m: phai KHONG DOI.
# Khong YES=1 => chi kiem (1)(2), khong ghi gi len 242. KHONG gui lenh giao dich nao. KHONG dung v_t_m (chi doc md5/PID/env).
# Phien cu co buoc giao dich => TU CHOI; MASTER quyet chay lai: them CANARY_RESET=1 (chi khi tai khoan con phang; giu bang chung
#   run/canary_prev_<TS>).
# Tiep theo: bash ops/c3live/canary/canary_early_run.sh   (LENH 2/2)
# Ket qua: "KET QUA: DAT|TRUOT|TU_CHOI".
# =============================================================================
export CANARY_MODE=early
. "$(cd "$(dirname "$0")" && pwd)/canary_lib.sh"
cl_init early_install
ET=${CANARY_EXPECT_TMB:-}
[[ "$ET" =~ ^[0-9]+(\.[0-9]+)?$ ]] || die "thieu/sai CANARY_EXPECT_TMB (so da nap vao tai khoan con, vd 10000) — K0: tmb ~ so da nap +-1 %"
CANARY_RESET=${CANARY_RESET:-0}
cl_time_gate die
cl_gates
[ -f "$CANARY_JAR" ] || die "khong thay jar Oracle $CANARY_JAR"
[ "$(md5sum < "$CANARY_JAR" | cut -c1-32)" = "$CANARY_JAR_MD5" ] || die "md5 jar Oracle $CANARY_JAR khac pin $CANARY_JAR_MD5"
ok "jar Oracle md5 = pin $CANARY_JAR_MD5"
cl_check_242 early_nojar
cl_vtm_baseline
# phien cu?
ST=$($SSH_242 "cat $A/$CDIR/canary_state.json 2>/dev/null" < /dev/null)
OLD=$(printf '%s' "$ST" | python3 -I -c '
import json, sys
t = sys.stdin.read().strip()
if not t: print("NONE"); sys.exit()
try: s = json.loads(t)
except Exception: print("HONG"); sys.exit()
k = [x for x in (s.get("steps") or {}) if x not in ("K0", "SETUP")]
print("TRADE " + ",".join(sorted(k)) if k else ("ABORTED" if s.get("aborted") else "K0ONLY"))
')
say "phien canary cu tren 242: $OLD"
case "$OLD" in
  NONE|K0ONLY) ;;
  *) [ "$CANARY_RESET" = 1 ] || die "da co phien canary ($OLD) trong $A/$CDIR — MASTER quyet chay lai: them CANARY_RESET=1" ;;
esac
if [ "$YES" != 1 ]; then
  say "CHI KIEM: dieu kien vao §ADD-1 DAT (chua ghi gi len 242). Chay that: YES=1 CANARY_EXPECT_TMB=$ET bash $0"
  say "KET QUA: DAT (chi kiem)"
  exit 0
fi
# --- (3) thu muc rieng + jar
$SSH_242 "umask 077 && mkdir -p $A/run && chmod 700 $A" < /dev/null || die "khong tao duoc $A tren 242"
if [ "$(pv JAR)" != "$CANARY_JAR_MD5" ]; then
  say "copy jar -> 242:$A/$CJAR"
  $SCP_242 "$CANARY_JAR" "${RHOST}$A/$CJAR.tmp" || die "scp jar loi"
  R=$($SSH_242 "cd $A && [ \"\$(md5sum < $CJAR.tmp | cut -c1-32)\" = $CANARY_JAR_MD5 ] && mv -f $CJAR.tmp $CJAR && echo JAR_OK || { rm -f $CJAR.tmp; echo JAR_SAI; }" < /dev/null)
  [ "$R" = JAR_OK ] || die "md5 jar tren 242 sau copy khac pin — da xoa ban tam"
fi
ok "jar 242:$A/$CJAR md5 = pin"
if [ "$CANARY_RESET" = 1 ] && [ "$OLD" != NONE ] && [ "$OLD" != K0ONLY ]; then
  cl_push_logback
  cl_run "" cleanup; RC=$?
  [ "$RC" = 0 ] || die "CANARY_RESET: tai khoan con CHUA phang ($CL_LAST_RESULT) — chay CANARY_MODE=early YES=1 bash $(dirname "$0")/canary_flatten.sh truoc"
  $SSH_242 "cd $A && mv $CDIR run/canary_prev_$TS" < /dev/null || die "khong doi ten phien cu"
  ok "phien cu -> $A/run/canary_prev_$TS"
fi
cl_copy_legacy
cl_push_logback
cl_check_242 early
cl_vtm_check "sau copy jar" || die "v_t_m bi doi trong luc install: $CL_VTM_DIFF — MASTER xem"
# --- (4) chi doc
cl_run "" keycheck; RC=$?
[ "$RC" = 0 ] || die "keycheck khong DAT ($CL_LAST_RESULT) — kiem key /root/.config/c3live/keys.env (c3live_keys_install.sh)"
cl_vtm_check "sau keycheck" || die "v_t_m bi doi: $CL_VTM_DIFF — MASTER xem"
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
if ! cl_vtm_check "sau K0"; then
  say "KET QUA: TRUOT (v_t_m bi doi: $CL_VTM_DIFF) — K0 chi doc, khong co gi de dong; MASTER xem"
  say "Log: $CL_LOG"; exit 3
fi
say "K0: $V ($CL_LAST_RESULT)"
if [ "$V" = DAT ]; then
  say "Tiep (LENH 2/2, owner co mat ~2-3 h): bash $(dirname "$0")/canary_early_run.sh"
else
  echo "$CL_LAST_RESULT" | grep -q 'SETUP' && say "marginType/leverage chua CROSSED/1x: MASTER cho phep thi chay CANARY_MODE=early YES=1 bash $(dirname "$0")/canary_step.sh SETUP roi chay lai lenh nay"
fi
say "KET QUA: $V"
say "Log: $CL_LOG"
[ "$V" = DAT ]
