#!/usr/bin/env bash
# =============================================================================
# canary_early_run.sh — CANARY-EARLY (prereg §ADD-1) LENH 2/2. Chay tren ORACLE, 1 lenh (owner co mat ~2-3 h):
#   bash ops/c3live/canary/canary_early_run.sh          (hoi go YES MOT lan o dau phien)
# Dieu kien: canary_early_install.sh da DAT (K0 DAT, < 24 h, phien chua co buoc giao dich).
# Chay K1 K2 K3 K4 K5 K6 (OPEN+kill+RESTART) K6b (OPEN+kill+doi ten so+RESTART+dong) K7 K7b K8 bang JVM rieng trong
#   /home/chuyennd/java/c3canary. Moi lenh 20 USDT trong tran CUNG (<= 25/lenh, <= 40 mo, tran lo 2 USDT, 2 symbol theo luat).
# TRUOC + SAU moi buoc: v_t_m (md5 jar/env/start + PID + env bot) phai KHONG DOI, MemAvailable >= 768 MB, khong co file STOP;
#   sai => DUNG ngay + flatten 2 symbol canary. Buoc dau tien khong DAT => flatten + DUNG.
# Cuoi phien (ca khi TRUOT): canary_report + kiem cleanup; DAT ca phien => doi ten run/canary -> run/canary_done_<TS>.
# Ket qua: 1 file txt tren Oracle  ~/claude_master/canary/canary_early_result_<TS>.txt  (KHONG chua key) — gui MASTER.
# Phien chay NEN (setsid): dong terminal KHONG dung phien. Dung khan cap: touch ~/claude_master/canary/CANARY_STOP
#   (phien dung sau buoc dang chay + flatten), hoac bash canary_early_flatten.sh (tu tao file STOP, kill JVM treo, flatten).
# [3c MAJ-C1] Khung gio CHI kiem o dau phien (tai khoan phang) — KHONG cho giua cac buoc; moi vi the co stop bao ve -4,5 % ngay khi mo.
# [3c MIN-C2] Tong lo moi phien canary-early > 4 USDT => tu choi; file ket qua ghi tong lo + so lan CANARY_RESET.
# Phuong an B (MO-2): USDT = 0 va K1 TRUOT vi -2019 => owner nap 50 USDT vao tai khoan con, bao MASTER (MASTER quyet chay lai).
# =============================================================================
export CANARY_MODE=early
. "$(cd "$(dirname "$0")" && pwd)/canary_lib.sh"
STOPF=$LOGDIR/CANARY_STOP
[[ "${CANARY_INJECT_TIMEOUT:-0}" =~ ^[01]$ ]] || die "CANARY_INJECT_TIMEOUT chi 0/1"

if [ -z "${CANARY_BG:-}" ]; then
  # ---- tien trinh cha: hoi YES 1 lan, roi chay phien NEN va theo doi log
  mkdir -p "$LOGDIR" || die "khong tao duoc $LOGDIR"
  [ -e "$STOPF" ] && die "dang co file $STOPF (lan dung khan cap truoc) — xoa co chu dich roi chay lai"
  if [ "$YES" != 1 ]; then
    echo "CANARY-EARLY: phien TIEN THAT tren TAI KHOAN CHINH (cung LEGACY; chi 2 symbol canary + cid canary; 20 USDT/lenh, tran lo 2 USDT)."
    read -r -p "Go YES (in hoa) de bat dau: " ANS || ANS=""
    [ "$ANS" = YES ] || die "khong go YES — khong chay"
  fi
  OUTB=$LOGDIR/early_run_bg_${TS}.out
  CANARY_BG=1 YES=1 CL_TS=$TS setsid nohup bash "$0" > "$OUTB" 2>&1 < /dev/null &
  BG=$!
  echo "phien chay nen pid=$BG (dong terminal khong dung phien; dung khan cap: touch $STOPF)"
  tail --pid=$BG -n +1 -f "$OUTB" &
  TP=$!
  wait $BG; RC=$?
  sleep 1; kill $TP 2>/dev/null; wait $TP 2>/dev/null
  exit $RC
fi

# ---- tien trinh nen: toan bo phien
cl_init early_run
RESF=$LOGDIR/canary_early_result_${TS}.txt
cl_time_gate die
cl_gates
cl_check_242 early
cl_cum_loss check   # [3c MIN-C2] tong lo moi phien canary-early > 4 USDT => khong chay (MASTER quyet)
cl_vtm_baseline
VTM_LOG=""
vlog() { VTM_LOG+="$*"$'\n'; }
vlog "baseline: $(printf '%s' "$CL_VTM0" | tr '\n' ' ')"
vlog "RAM bat dau: $(pv MEM_MB) MB"
# K0 phai DAT, < 24 h, phien chua co buoc giao dich
cl_run "" status >/dev/null
K0=$(printf '%s' "$CL_LAST_OUT" | grep -v '^RESULT ' | python3 -I -c '
import json, sys, time
t = sys.stdin.read().strip()
try: s = json.loads(t)
except Exception: print("HONG"); sys.exit()
st = s.get("steps") or {}
k0 = st.get("K0") or {}
trade = [x for x in st if x not in ("K0", "SETUP")]
if s.get("aborted"): print("ABORTED"); sys.exit()
if trade: print("TRADE " + ",".join(sorted(trade))); sys.exit()
if k0.get("result") != "DAT": print("K0_CHUA_DAT"); sys.exit()
age = time.time() * 1000 - float(k0.get("ms") or 0)
print("OK %s %s" % (int(age / 60000), s.get("symMain")) if age <= 24 * 3600 * 1000 else "K0_CU %d" % int(age / 3600000))
')
case "$K0" in
  OK*) ok "K0 DAT ${K0#OK } (phut tuoi, symbol chinh)" ;;
  *) die "dieu kien K0: $K0 — chay lai canary_early_install.sh (phien cu co giao dich => MASTER quyet CANARY_RESET=1)" ;;
esac
cl_copy_legacy
cl_push_logback

SEQ="K1 K2 K3 K4 K5 K6 K6B K7 K7B K8"
declare -A RES
FAIL=""; WHY=""; K1OUT=""
for k in $SEQ; do
  [ -e "$STOPF" ] && { FAIL=$k; WHY="file STOP (owner dung khan cap)"; break; }
  # [3c MAJ-C1] KHONG cho khung gio giua cac buoc (co the con vi the/stop mo) — khung gio chi kiem o dau phien (tren)
  if ! cl_vtm_check "truoc $k"; then FAIL=$k; WHY="v_t_m bi doi truoc $k: $CL_VTM_DIFF"; vlog "TRUOC $k: DOI $CL_VTM_DIFF"; break; fi
  vlog "truoc $k: khong doi (pid $(pv BOT)) RAM $(pv MEM_MB) MB"
  cl_ram_check "$MIN_RAM_STEP_MB" || { FAIL=$k; WHY="MemAvailable $(pv MEM_MB) MB < $MIN_RAM_STEP_MB MB"; break; }
  say "==== buoc $k"
  cl_macro "$k"; RC=$?
  RES[$k]="$(cl_verdict $RC) | $CL_LAST_RESULT"
  [ "$k" = K1 ] && K1OUT=$CL_LAST_OUT
  say "==== $k: ${RES[$k]}"
  if ! cl_vtm_check "sau $k"; then FAIL=$k; WHY="v_t_m bi doi sau $k: $CL_VTM_DIFF"; vlog "SAU $k: DOI $CL_VTM_DIFF"; break; fi
  vlog "sau $k: khong doi (pid $(pv BOT))"
  if [ "$RC" != 0 ]; then FAIL=$k; WHY="buoc $k $(cl_verdict $RC)"; break; fi
done
FLAT=""
if [ -n "$FAIL" ]; then
  say "DUNG o buoc $FAIL ($WHY) — dong het vi the 2 symbol canary (flatten)"
  cl_kill_hung   # [3c MIN-C3] JVM canary treo (giu lock, khong heartbeat) => kill truoc, roi flatten
  cl_run "" flatten; RF=$?
  FLAT="flatten: $(cl_verdict $RF) | $CL_LAST_RESULT"
  say "$FLAT"
  if printf '%s' "$CL_LAST_RESULT" | grep -q 'TRUOT-DO'; then
    say "!! TRUOT-DO (§ADD-4 C): vi the lan LEGACY tren symbol canary — KHONG dong; BAO MASTER; KHONG chay canary_early_flatten.sh"
  elif [ "$RF" != 0 ]; then
    say "!! flatten KHONG DAT — owner chay ngay: bash $(dirname "$0")/canary_early_flatten.sh ; bao MASTER"
  fi
  cl_vtm_check "sau flatten" && vlog "sau flatten: khong doi" || vlog "SAU flatten: DOI $CL_VTM_DIFF"
fi
PLANB=""
if printf '%s' "$K1OUT" | grep -q -- '-2019'; then
  PLANB="K1 gap -2019 (margin khong du) voi USDT = 0 => PHUONG AN B (MO-2): owner nap 50 USDT vao tai khoan con, bao MASTER; MASTER quyet chay lai (ghi 'cau hinh pilot USDT = 0 KHONG dat')."
  say "$PLANB"
fi
# ---- [3f §ADD-4 C/D] cleanup TRUOC (CHI DOC: pham vi canary + anh chup LEGACY cuoi phien), roi bao cao (doc ca buoc CLEANUP)
cl_run "" cleanup; RCC=$?
CLEAN="cleanup (2 symbol canary 0 vi the / 0 algo / 0 lenh; 0 lenh canary ngoai pham vi): $(cl_verdict $RCC) | $CL_LAST_RESULT"
say "$CLEAN"
LEGACY=$(printf '%s' "$CL_LAST_OUT" | grep '^DATA ' | tail -1 | python3 -I -c '
import json, sys
t = sys.stdin.read().strip()
try: m = json.loads(t[5:]) if t.startswith("DATA ") else {}
except Exception: m = {}
v = m.get("legacy.summary")
print(v if isinstance(v, str) and v.startswith("LEGACY") else "")
')
[ -n "$LEGACY" ] || LEGACY="LEGACY: khong co du lieu (cleanup khong in legacy.summary)"
say "$LEGACY"
say "---- canary_report (mode early)"
ROUT=$(LOGDIR=$LOGDIR CL_TS= bash "$CL_HERE/canary_report.sh" 2>&1); RRC=$?
printf '%s\n' "$ROUT" | sed 's/^/   r| /' | tail -60
RPT=$(printf '%s\n' "$ROUT" | sed -n 's/.*Bao cao: //p' | tail -1)
SESSION=DAT; [ -n "$FAIL" ] && SESSION=TRUOT; [ "$RRC" = 0 ] || SESSION=TRUOT; [ "$RCC" = 0 ] || SESSION=TRUOT
RENAME="giu nguyen $A/$CDIR (phien KHONG DAT — bang chung + trang thai cho MASTER/A1)"
if [ "$SESSION" = DAT ]; then
  R=$($SSH_242 "cd $A && [ \$(pgrep -fc '$MAIN_PAT') = 0 ] && [ -d $CDIR ] && [ ! -e run/canary_done_$TS ] && mv $CDIR run/canary_done_$TS && echo DOI_TEN_XONG" < /dev/null)
  if [ "$R" = DOI_TEN_XONG ]; then RENAME="$A/$CDIR -> $A/run/canary_done_$TS"; else RENAME="KHONG doi ten duoc $CDIR"; SESSION=TRUOT; fi
fi
cl_vtm_check "cuoi phien" && vlog "cuoi phien: khong doi" || { vlog "CUOI phien: DOI $CL_VTM_DIFF"; SESSION=TRUOT; }
cl_cum_loss info   # [3c MIN-C2] ghi vao file ket qua
# ---- 1 file ket qua (khong key)
{
  echo "CANARY-EARLY — KET QUA PHIEN $TS (prereg docs/prereg/GCANARY_PREREG.md §ADD-1 + §ADD-4 tai khoan CHINH + §4/§5)"
  echo "$LEGACY"
  echo "jar 242: $A/$CJAR md5 $CANARY_JAR_MD5 ; v_t_m: $VTM (chi doc)"
  echo "KET QUA PHIEN: $SESSION$( [ -n "$FAIL" ] && echo " (dung o $FAIL: $WHY)")"
  [ -n "$PLANB" ] && echo "!! $PLANB"
  echo "lo cong don MOI phien canary-early: $CL_CUM_LOSS USDT (tran $CL_CUM_CAP — vuot => phien moi bi tu choi); so lan CANARY_RESET: $CL_RESETS"
  echo "prior dung cho phien (CANARY_PRIOR_LOSS_USDT): ${CL_CUM_PRIOR:-?} USDT — tinh luc ${CL_CUM_PRIOR_AT:-?}"
  printf '%s\n' "$CL_CUM_DETAIL" | sed '/^$/d; s/^/  /'
  echo
  echo "== Buoc"
  for k in $SEQ; do echo "  $k: ${RES[$k]:-CHUA_CHAY}"; done
  [ -n "$FLAT" ] && echo "  $FLAT"
  echo "  $CLEAN"
  echo "  thu muc phien: $RENAME"
  echo
  echo "== v_t_m (md5 target/binance-java-sdk-1.2.4.jar, conf/env.sh, bin/start.sh + PID + env bot)"
  printf '%s' "$VTM_LOG" | sed 's/^/  /'
  echo
  echo "== canary_report ($RPT)"
  [ -n "$RPT" ] && [ -f "$RPT" ] && cat "$RPT" || echo "  (khong co file bao cao — xem log $CL_LOG)"
} > "$RESF.tmp"
# chot chan cuoi: mau bi mat trong file ket qua => che + TRUOT
NB=$(grep -c -E 'signature=|[0-9]{8,10}:[A-Za-z0-9_-]{35}|[A-Za-z0-9]{56,}' "$RESF.tmp")
if [ "${NB:-0}" != 0 ]; then
  sed -i -E 's/signature=[^ "]*/[CHE]/g; s/[0-9]{8,10}:[A-Za-z0-9_-]{35}/[CHE]/g; s/[A-Za-z0-9]{56,}/[CHE]/g; s/^KET QUA PHIEN: DAT/KET QUA PHIEN: TRUOT (file co mau bi mat — da che)/' "$RESF.tmp"
  SESSION=TRUOT
fi
mv -f "$RESF.tmp" "$RESF"
say "KET QUA PHIEN: $SESSION$( [ -n "$FAIL" ] && echo " (buoc $FAIL: $WHY)")"
say "File ket qua cho MASTER: $RESF"
say "Log: $CL_LOG"
[ "$SESSION" = DAT ]
