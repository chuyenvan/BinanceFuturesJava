#!/usr/bin/env bash
# =============================================================================
# canary_early_all.sh — [V12 3d, prereg §ADD-3] CANARY-EARLY MOT LENH. Chay tren ORACLE, owner go YES MOT lan, sau do chay NEN:
#   bash ops/c3live/canary/canary_early_all.sh
# Thu tu (moi buoc deu kiem v_t_m KHONG doi, RAM, file STOP; luat tien §ADD-1/§ADD-2 + MIN-C2/C3 giu nguyen):
#   0. chuan bi: gate CODE, jar Oracle = pin, 242 chi doc (v_t_m c3_shadow + SHADOW_NO_PUSH, RAM >= 1 GB, khong JVM canary khac),
#      lo cong don <= tran, chup v_t_m, phien cu (co giao dich => can CANARY_RESET=1), copy jar pin vao c3canary, LEGACY, logback.
#   1. CHO khung gio hop le (phut :10-:40 de con du thoi gian, tranh 07/19 h, 00:50-01:20, 12:50-13:20) CHI KHI tai khoan PHANG
#      (keycheck chi doc — [3f §ADD-4 C] PHAM VI CANARY: 2 symbol canary 0 vi the/lenh/algo + 0 cid canary o moi noi; LEGACY chi dem) — kiem lai phang moi CL_FLAT_RECHECK_S (600 s) va ngay truoc khi qua;
#      khong phang => DUNG (khong bao gio cho khi co vi the — MAJ-C1). Toi da CL_WAIT_MAX_S (7200 s = 2 h) moi lan cho.
#   2. SETUP (CROSSED/1x cho 2 symbol theo luat) — neu phien da chon symbol (chua chon => K0 chon truoc, SETUP sau).
#   3. K0 (tai khoan CHINH, §ADD-4 H): KHONG kiem tmb tuyet doi — tmb doc duoc chi GHI (file tom tat, KHONG Telegram); engine
#      kiem availableBalance >= 50 USDT, loai symbol LEGACY, chup anh LEGACY. (truoc 3f: tmb trong [9500, 12000] — da bo)
#      CANARY_K0_REUSE_KEEPALIVE=1: engine bo phan cho keepAlive 65' neu K0 truoc (<= 24 h, CUNG jar) da DAT keepAlive >= 2 —
#      ly do bo / khong bo ghi trong log + file ket qua. K0 TRUOT chi vi marginType/leverage => cho khung gio -> SETUP -> K0 lai (1 lan).
#   4. cho khung gio lai (tai khoan phang) -> canary_early_run.sh (CANARY_INJECT_TIMEOUT=1): K1..K8, report, cleanup.
#   5. Telegram (kenh ~/.config/health242/tg.env san co, KHONG in token) khi ket thuc: DAT / TRUOT / LOI + 1 dong + file ket qua.
#   6. Loi o bat ky buoc nao: (jar pin da tren 242) kiem phang chi doc; KHONG phang (hoac khong doc duoc) => kill JVM treo (MIN-C3)
#      + flatten (mode early); roi DUNG va bao. Da phang that (0/0/0 toan tai khoan) => khong goi flatten (flatten ghi buoc FLATTEN
#      vao phien => phien bi coi la "co giao dich", lan sau phai CANARY_RESET).
# Dung khan cap: touch ~/claude_master/canary/CANARY_STOP (phien dung o lan kiem ke tiep + flatten) hoac canary_early_flatten.sh.
# Ket qua: ~/claude_master/canary/canary_early_all_<TS>.txt (+ file ket qua phien canary_early_result_<TS>.txt). Khong chua key.
# Moc test (test_fake242.sh): CL_WAIT_MAX_S, CL_WAIT_POLL_S, CL_FLAT_RECHECK_S, CL_FAKE_HM, CANARY_TG_SINK, CANARY_TG_ENV.
# =============================================================================
export CANARY_MODE=early
. "$(cd "$(dirname "$0")" && pwd)/canary_lib.sh"
STOPF=$LOGDIR/CANARY_STOP
readonly TMB_MIN=9500 TMB_MAX=12000          # §ADD-3: tmb doc duoc phai trong [9500, 12000] (hang so)
readonly WIN_LAST_MIN=40                     # vao buoc ghi muon nhat phut :40 (khung :10-:44, de canary_early_run kip chot gio)
WAIT_MAX=${CL_WAIT_MAX_S:-7200}
WPOLL=${CL_WAIT_POLL_S:-60}
RECHECK=${CL_FLAT_RECHECK_S:-600}
for v in "$WAIT_MAX" "$WPOLL" "$RECHECK"; do [[ "$v" =~ ^[0-9]+$ ]] || die "CL_WAIT_MAX_S/CL_WAIT_POLL_S/CL_FLAT_RECHECK_S phai la so"; done
[ "$WAIT_MAX" -le 7200 ] || die "CL_WAIT_MAX_S > 7200 (toi da 2 h)"

if [ -z "${CANARY_BG:-}" ]; then
  # ---- tien trinh cha: hoi YES 1 lan, roi chay NEN (setsid) va theo doi log (dong terminal KHONG dung phien)
  mkdir -p "$LOGDIR" || die "khong tao duoc $LOGDIR"
  [ -e "$STOPF" ] && die "dang co file $STOPF (lan dung khan cap truoc) — xoa co chu dich roi chay lai"
  if [ "$YES" != 1 ]; then
    echo "CANARY-EARLY MOT LENH: cho khung gio (<= 2 h, chi khi tai khoan phang) -> SETUP -> K0 (~65' hoac bo neu dung lai duoc)"
    echo "  -> phien TIEN THAT K1..K8 tren TAI KHOAN CHINH (cung LEGACY; chi 2 symbol canary + cid c3-/c3s-/c3x-; moi lenh 20 USDT,"
    echo "     tran lo 2 USDT, LEGACY KHONG bao gio bi cham — lan LEGACY tren symbol canary => TRUOT-DO, khong dong, bao MASTER) -> Telegram."
    read -r -p "Go YES (in hoa) de bat dau: " ANS || ANS=""
    [ "$ANS" = YES ] || die "khong go YES — khong chay"
  fi
  OUTB=$LOGDIR/early_all_bg_${TS}.out
  CANARY_BG=1 YES=1 CL_TS=$TS setsid nohup bash "$0" > "$OUTB" 2>&1 < /dev/null &
  BG=$!
  echo "phien chay NEN pid=$BG — co the dong terminal; ket qua gui Telegram. Dung khan cap: touch $STOPF"
  echo "theo doi lai: tail -f $OUTB"
  tail --pid=$BG -n +1 -f "$OUTB" &
  TP=$!
  wait $BG; RC=$?
  sleep 1; kill $TP 2>/dev/null; wait $TP 2>/dev/null
  exit $RC
fi

# ---- tien trinh nen
cl_init early_all
SUMF=$LOGDIR/canary_early_all_${TS}.txt
FLF=$LOGDIR/.early_all_flat_${TS}
STAGE="chuan bi"; DONE=0; JAR_READY=0; LASTMSG=""; LASTV=""; RUN_RESF=""; K0_TMB=""; K0_KA=""; K0_RES=""; NOTES=""; K0_BAL=""
# [3f §ADD-4 D] dong LEGACY (chi dem, khong so du) tu file ket qua phien
leg_line() { { [ -n "$RUN_RESF" ] && grep -m1 '^LEGACY' "$RUN_RESF" 2>/dev/null; } || echo "LEGACY: khong co du lieu (phien K1..K8 chua chay / chua cleanup)"; }
note() { NOTES+="$*"$'\n'; say "ghi chu: $*"; }
# die cua lib: ghi ly do roi thoat => trap on_exit (kiem phang / flatten + Telegram)
die() { LASTMSG="$*"; say "DUNG: $*"; say "KET QUA: ${LASTV:-TU_CHOI}"; [ -n "${CL_LOG:-}" ] && say "Log: $CL_LOG"; exit 2; }

# safe_flat (chay trong subshell — die ben trong chi thoat subshell): kiem phang chi doc; khong phang / khong doc duoc => kill JVM
# treo + flatten. Ghi 1 dong ket qua vao $FLF.
safe_flat() {
  local r rf
  cl_flat_read; r=$?
  if [ "$r" = 0 ]; then
    echo "tai khoan PHANG ($CL_FLAT, keycheck chi doc) — khong can flatten" > "$FLF"; return 0
  fi
  [ "$r" = 1 ] && say "tai khoan KHONG phang ($CL_FLAT) — flatten" || say "khong doc duoc trang thai ($CL_FLAT_WHY) — flatten cho chac"
  echo "flatten: chua xong (loi giua chung)" > "$FLF"
  cl_kill_hung
  cl_run "" flatten; rf=$?
  if printf '%s' "$CL_LAST_RESULT" | grep -q 'TRUOT-DO'; then
    echo "flatten (mode early): TRUOT-DO — KHONG dong (vi the lan LEGACY tren symbol canary, §ADD-4 C) — BAO MASTER, KHONG chay canary_early_flatten.sh | $CL_LAST_RESULT" > "$FLF"
  elif [ "$rf" = 0 ]; then echo "flatten (mode early): DAT | $CL_LAST_RESULT" > "$FLF"
  else echo "flatten (mode early): $(cl_verdict $rf) | $CL_LAST_RESULT — OWNER CHAY NGAY: bash $CL_HERE/canary_early_flatten.sh" > "$FLF"; fi
}

write_sum() {   # <ket qua> <1 dong>
  {
    echo "CANARY-EARLY MOT LENH — $TS (prereg docs/prereg/GCANARY_PREREG.md §ADD-1/§ADD-2/§ADD-3/§ADD-4 tai khoan CHINH)"
    echo "KET QUA: $1"
    echo "TOM TAT: $2"
    echo "buoc cuoi: $STAGE"
    echo "jar 242: $A/$CJAR md5 pin $CANARY_JAR_MD5 ; v_t_m: $VTM (chi doc)"
    echo "K0: CANARY_EXPECT_TMB=${K0_TMB:-chua chay} ; ${K0_RES:-}"
    [ -n "$K0_KA" ] && echo "K0 keepAlive: $K0_KA"
    [ -n "$K0_BAL" ] && echo "K0 so du (chi file nay, KHONG gui Telegram): $K0_BAL"
    [ -n "$NOTES" ] && { echo "ghi chu:"; printf '%s' "$NOTES" | sed 's/^/  - /'; }
    echo "file ket qua phien K1..K8: ${RUN_RESF:-khong co (phien K1..K8 chua chay)}"
    echo "log: $CL_LOG"
  } > "$SUMF.tmp"
  sed -i -E 's/signature=[^ "]*/[CHE]/g; s/[0-9]{8,10}:[A-Za-z0-9_-]{35}/[CHE]/g; s/[A-Za-z0-9]{56,}/[CHE]/g' "$SUMF.tmp"
  mv -f "$SUMF.tmp" "$SUMF"
}

finish_tg() {   # <DAT|TRUOT|LOI> <1 dong>
  local f=${RUN_RESF:-$SUMF}
  write_sum "$1" "$2"
  cl_tg "CANARY-EARLY $1 ($TS)
$2
File ket qua: $f$( [ "$f" != "$SUMF" ] && printf '\nTom tat: %s' "$SUMF")" || say "!! KHONG gui duoc Telegram — owner xem $SUMF"
  say "KET QUA MOT LENH: $1 — $2"
  say "File tom tat: $SUMF"
}

on_exit() {
  local rc=$? fl
  [ "$DONE" = 1 ] && return 0
  trap - EXIT
  DONE=1
  [ -n "$LASTMSG" ] || LASTMSG="thoat bat thuong rc=$rc o buoc $STAGE"
  fl="khong flatten (jar pin chua san tren 242 — chua gui lenh ghi nao)"
  if [ "$JAR_READY" = 1 ]; then
    rm -f "$FLF"
    ( safe_flat )
    fl=$(cat "$FLF" 2>/dev/null); fl=${fl:-"flatten: khong ro ket qua — OWNER CHAY: bash $CL_HERE/canary_early_flatten.sh"}
    rm -f "$FLF"
    say "$fl"
  fi
  finish_tg "${LASTV:-LOI}" "dung o buoc '$STAGE': $LASTMSG | $fl"
  [ "$LASTV" = TRUOT ] && rc=3
  exit "$rc"
}
trap on_exit EXIT
trap 'LASTMSG="bi dung boi tin hieu (TERM/INT/HUP)"; exit 4' TERM INT HUP

# 1 phien mot lenh tai 1 thoi diem (lock Oracle; giu suot ca canary_early_run con)
exec 9> "$LOGDIR/.canary_early_all.lock"
flock -n 9 || { JAR_READY=0; die "dang co canary_early_all.sh khac chay (lock $LOGDIR/.canary_early_all.lock)"; }

# hm hien tai (+07, hoac dong ho gia test CL_FAKE_HM)
cur_m() {
  local H M
  H=$(TZ=Asia/Ho_Chi_Minh date +%-H); M=$(TZ=Asia/Ho_Chi_Minh date +%-M)
  if [ -n "${CL_FAKE_HM:-}" ] && [ -f "$CL_FAKE_HM" ]; then read -r H M < "$CL_FAKE_HM"; fi
  echo "$M"
}
win_ok() { [ "$FORCE_TIME" = 1 ] && return 0; time_ok && [ "$(cur_m)" -le "$WIN_LAST_MIN" ]; }

# step_guard <nhan>: STOP / v_t_m khong doi / RAM >= 768 MB — sai => DUNG (trap: kiem phang / flatten + Telegram)
step_guard() {
  [ -e "$STOPF" ] && die "co file STOP $STOPF (owner dung khan cap) — $1"
  cl_vtm_check "$1" || die "v_t_m bi doi ($1): $CL_VTM_DIFF — MASTER xem"
  cl_ram_check "$MIN_RAM_STEP_MB" || die "MemAvailable 242 $(pv MEM_MB) MB < $MIN_RAM_STEP_MB MB ($1)"
}

# must_flat <nhan>: keycheck chi doc phai PHANG
must_flat() {
  local r
  cl_flat_read; r=$?
  [ "$r" = 2 ] && die "khong doc duoc trang thai pham vi canary ($1): $CL_FLAT_WHY"
  [ "$r" = 0 ] || die "pham vi canary KHONG phang ($1: $CL_FLAT) — KHONG cho khung gio khi con vi the/lenh/stop canary (MAJ-C1)"
  ok "pham vi canary phang ($1: $CL_FLAT)"
}

# wait_window <nhan>: cho khung gio hop le CHI KHI phang (kiem phang luc vao, moi RECHECK s, va ngay truoc khi qua). Toi da WAIT_MAX s.
wait_window() {
  local t0 last now
  STAGE="cho khung gio ($1)"
  t0=$(date +%s)
  step_guard "cho khung gio $1"
  must_flat "vao cho $1"; last=$(date +%s)
  if win_ok; then ok "dang trong khung gio ($1)"; return 0; fi
  say "ngoai khung gio — CHO (toi da ${WAIT_MAX}s, kiem phang moi ${RECHECK}s; tai khoan phang nen an toan)"
  while :; do
    sleep "$WPOLL"
    now=$(date +%s)
    [ -e "$STOPF" ] && die "co file STOP $STOPF trong luc cho khung gio"
    if win_ok; then
      step_guard "het cho $1"
      must_flat "het cho $1"
      if win_ok; then ok "vao khung gio ($1) sau $(( $(date +%s) - t0 ))s"; return 0; fi
      last=$(date +%s)
    elif [ $(( now - last )) -ge "$RECHECK" ]; then
      step_guard "dang cho $1"
      must_flat "dang cho $1"; last=$(date +%s)
    fi
    [ $(( $(date +%s) - t0 )) -ge "$WAIT_MAX" ] && die "cho khung gio qua $(( WAIT_MAX / 60 )) phut ($1) — chay lai lenh sau"
  done
}

# data_get <khoa>: gia tri trong dong DATA cuoi cua lan cl_run gan nhat
data_get() {
  printf '%s' "$CL_LAST_OUT" | grep '^DATA ' | tail -1 | python3 -I -c '
import json, sys
t = sys.stdin.read().strip()
try: m = json.loads(t[5:]) if t.startswith("DATA ") else {}
except Exception: m = {}
v = m.get(sys.argv[1])
print("" if v is None else (v if isinstance(v, str) else json.dumps(v, ensure_ascii=False))[:600])
' "$1"
}

# run_k0: K0 voi tmb doc ngay luc do. Dat K0_RC, K0_RES, K0_TMB, K0_KA.
run_k0() {
  STAGE="K0 ($1)"
  step_guard "truoc K0 ($1)"
  must_flat "truoc K0 ($1)"
  [[ "$CL_TMB" =~ ^[0-9]+(\.[0-9]+)?$ ]] || die "khong doc duoc tmb tu keycheck ('$CL_TMB')"
  K0_TMB=$CL_TMB   # [3f §ADD-4 H] tai khoan CHINH: KHONG kiem tmb tuyet doi — chi GHI (file tom tat, KHONG Telegram)
  K0_BAL="tmb=$CL_TMB USDT=${CL_USDT:-?} assets=${CL_ASSETS:-?}"
  say "CANARY_EXPECT_TMB=$K0_TMB (chi GHI — §ADD-4 H: khong kiem tmb tuyet doi tren tai khoan chinh; engine kiem availableBalance >= 50)"
  if [ -n "$CL_USDT" ] && python3 -I -c "import sys; sys.exit(0 if float('$CL_USDT') != 0 else 1)" 2>/dev/null; then
    case "$NOTES" in *"pilot USDT = 0"*) ;; *) note "USDT != 0 => cau hinh pilot USDT = 0 KHONG duoc kiem (MO-2)";; esac
  fi
  cl_run "CANARY_EXPECT_TMB=$K0_TMB CANARY_K0_REUSE_KEEPALIVE=1" preflight; K0_RC=$?
  K0_RES="K0 ($1): $(cl_verdict $K0_RC) | $CL_LAST_RESULT"
  local sk ru ka
  sk=$(data_get ws.keepAliveSkipped); ru=$(data_get ws.keepAliveReuse); ka=$(data_get ws.keepAliveOk)
  if [ -n "$sk" ]; then K0_KA="BO cho keepAlive 65' — ly do: $sk"
  elif [ -n "$ru" ]; then K0_KA="chay du keepAlive (keepAliveOk=${ka:-?}) — $ru"
  else K0_KA="chay du keepAlive (keepAliveOk=${ka:-?})"; fi
  say "K0 keepAlive: $K0_KA"
  local k; for k in symMain symAux tmb tmbDiffFrac assets ws.openMs; do say "   $k = $(data_get $k)"; done
  printf '%s' "$CL_LAST_OUT" | grep '^DATA ' | tail -1 | grep -o '"symbolConfig\.[A-Z0-9]*":"[^"]*"' | sed 's/^/   /'
  say "$K0_RES"
  cl_vtm_check "sau K0 ($1)" || die "v_t_m bi doi sau K0: $CL_VTM_DIFF — MASTER xem"
}

# k0_setup_only: K0 TRUOT CHI vi marginType/leverage (moi ly do deu goi y canary_step SETUP)
k0_setup_only() {
  local f; f=${CL_LAST_RESULT#*| }
  [ "$K0_RC" = 3 ] && [ "$f" != "$CL_LAST_RESULT" ] || return 1
  python3 -I -c 'import sys; f=[x for x in sys.argv[1].split(" ; ") if x.strip()]; sys.exit(0 if f and all("canary_step SETUP" in x for x in f) else 1)' "$f"
}

# run_setup: SETUP (ghi marginType/leverage 2 symbol canary; tai khoan phang, trong khung gio)
run_setup() {
  STAGE="SETUP ($1)"
  step_guard "truoc SETUP ($1)"
  cl_run "" setup || die "SETUP khong DAT ($CL_LAST_RESULT)"
  ok "SETUP ($1): $CL_LAST_RESULT"
  cl_vtm_check "sau SETUP ($1)" || die "v_t_m bi doi sau SETUP: $CL_VTM_DIFF — MASTER xem"
}

# ============================================================ 0. chuan bi
say "=== CANARY-EARLY MOT LENH (§ADD-3): cho khung gio<=$((WAIT_MAX / 60))' (phang) -> SETUP -> K0 -> K1..K8 -> Telegram"
CANARY_RESET=${CANARY_RESET:-0}
cl_gates
[ -f "$CANARY_JAR" ] || die "khong thay jar Oracle $CANARY_JAR"
[ "$(md5sum < "$CANARY_JAR" | cut -c1-32)" = "$CANARY_JAR_MD5" ] || die "md5 jar Oracle $CANARY_JAR khac pin $CANARY_JAR_MD5"
ok "jar Oracle md5 = pin $CANARY_JAR_MD5"
cl_check_242 early_nojar
[ "$(pv JAR)" = "$CANARY_JAR_MD5" ] && JAR_READY=1
cl_cum_loss check   # [3c MIN-C2]
cl_vtm_baseline
cl_early_old
case "$CL_OLD" in
  NONE|K0ONLY) ;;
  *) [ "$CANARY_RESET" = 1 ] || die "da co phien canary ($CL_OLD) trong $A/$CDIR — MASTER quyet chay lai: them CANARY_RESET=1" ;;
esac
STAGE="cai jar + thu muc rieng"
cl_early_jar
JAR_READY=1
cl_early_reset
cl_copy_legacy
cl_push_logback
cl_check_242 early
cl_vtm_check "sau copy jar" || die "v_t_m bi doi trong luc chuan bi: $CL_VTM_DIFF — MASTER xem"

# ============================================================ 1. cho khung gio (chi khi phang)
wait_window "SETUP/K0"

# ============================================================ 2. SETUP (neu da chon symbol)
cl_run "" status > /dev/null
SYMS=$(printf '%s' "$CL_LAST_OUT" | grep -v '^RESULT ' | python3 -I -c '
import json, sys
try: s = json.loads(sys.stdin.read().strip() or "{}")
except Exception: s = {}
print("%s,%s" % (s.get("symMain"), s.get("symAux")) if s.get("symMain") and s.get("symAux") else "")
')
if [ -n "$SYMS" ]; then
  run_setup "symbol phien hien tai $SYMS"
else
  say "phien chua chon symbol — K0 chon theo luat truoc, SETUP sau neu K0 bao can"
fi

# ============================================================ 3. K0 (tmb doc ngay luc do; dung lai keepAlive neu duoc)
run_k0 "lan 1"
if [ "$K0_RC" != 0 ] && k0_setup_only; then
  say "K0 TRUOT chi vi marginType/leverage cua symbol vua chon => cho khung gio -> SETUP -> K0 lai (1 lan)"
  wait_window "SETUP sau K0"
  run_setup "sau K0 lan 1"
  run_k0 "lan 2 (sau SETUP)"
fi
if [ "$K0_RC" != 0 ]; then LASTV=TRUOT; die "$K0_RES"; fi
ok "$K0_RES"

# ============================================================ 4. cho khung gio -> phien K1..K8 (+ report + cleanup)
wait_window "phien K1..K8"
STAGE="phien K1..K8 (canary_early_run.sh)"
ROUT=$LOGDIR/.early_all_run_${TS}.out
env -u CL_TS CANARY_BG=1 YES=1 CANARY_INJECT_TIMEOUT=1 bash "$CL_HERE/canary_early_run.sh" 2>&1 | tee "$ROUT" | sed -u 's/^/   run| /'
RRC=${PIPESTATUS[0]}
RUN_RESF=$(sed -n 's/.*File ket qua cho MASTER: //p' "$ROUT" | tail -1)
SESS=$(sed -n 's/.*KET QUA PHIEN: //p' "$ROUT" | tail -1)
rm -f "$ROUT"
[ -n "$RUN_RESF" ] && [ -f "$RUN_RESF" ] || RUN_RESF=""
if [ "$RRC" = 0 ] && [ -n "$RUN_RESF" ] && grep -q '^KET QUA PHIEN: DAT' "$RUN_RESF"; then
  DONE=1
  finish_tg DAT "KET QUA PHIEN: $SESS | $(leg_line) | $K0_KA$( [ -n "$NOTES" ] && printf ' | %s' "$(printf '%s' "$NOTES" | tr '\n' ' ')")"
  exit 0
fi
if [ "$RRC" = 1 ] && [ -n "$RUN_RESF" ]; then
  # phien chay het (TRUOT): canary_early_run da flatten khi dung giua chung + cleanup; kiem phang lai cho chac
  DONE=1
  rm -f "$FLF"; ( safe_flat ); FL=$(cat "$FLF" 2>/dev/null); rm -f "$FLF"; say "${FL:=flatten: khong ro — OWNER CHAY canary_early_flatten.sh}"
  finish_tg TRUOT "KET QUA PHIEN: $SESS | $FL | $(leg_line)"
  exit 3
fi
die "canary_early_run.sh thoat rc=$RRC ($( [ -n "$SESS" ] && echo "KET QUA PHIEN: $SESS" || echo 'khong co ket qua phien'))"
