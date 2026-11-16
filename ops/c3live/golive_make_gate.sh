#!/usr/bin/env bash
# =============================================================================
# golive_make_gate.sh — [WAVE1 16/11 B-08 + WAVE1b M4] MASTER tao file gate G-MICRO (deploy/gates/GOLIVE_GATE_MICRO.ok) TU BANG CHUNG, khong go tay.
#   GMICRO_MANUAL=<docs/result/GMICRO_MANUAL_<ngay>.md> REPLAY_RESULT=<file ket qua replay> SIZING_RESULT=<file ket qua sizing> \
#     bash golive_make_gate.sh <prereg_commit> [report_G-MICRO]        # DRY=1: chi in noi dung, khong ghi
# RANG BUOC CUNG (khong override duoc) — sai => TU CHOI:
#   (a) 242 (CHI DOC): 1 process v_t_m, jar DANG chay = NJ_MD5 pin, ingestor DANG chay = ING_FIN_MD5 pin;
#       parity_v12w/gmicro_target.json target_md5 = NJ_MD5 + smoke_start_ms (13 so).
#   (b) prereg_commit (hex 7-40) la commit THAT trong PREREG_REPO (git cat-file), co PREREG_FILE (ADD22) va ADD22 la addendum
#       PREREG_PARITY_V12_DRY moi nhat tai commit do (co ADD23+ => gate phai dua tren prereg moi => TU CHOI, sua PREREG_FILE).
#   report G-MICRO (mac dinh report_*.out moi nhat trong parity_v12w) ton tai, tuoi <= GATE_MAX_AGE_S, co dong "G-MICRO:".
# TRUONG ADD22 §3 (moi truong tro FILE bang chung ton tai; gia tri DAT; thieu => TU CHOI tru khi override):
#   gmicro_i   : report co "G-MICRO: DAT" hoac "i=True"                                   (ev = report)
#   gmicro_ii  : GMICRO_MANUAL (ten GMICRO_MANUAL_*.md, da commit + sach trong git cua no, ADD22 §2.5) co dong "gmicro_ii: DAT",
#                dong chua jar NJ_MD5 va "smoke_start_ms=<smoke_start_ms gmicro_target>"  (ev = GMICRO_MANUAL)
#   smoke      : cung GMICRO_MANUAL, dong "smoke: DAT"                                      (ev = GMICRO_MANUAL)
#   replay_iii : REPLAY_RESULT co dong "replay_iii: DAT" + jar NJ_MD5; prereg PREREG_E2E_REPLAY_V12*.md co trong prereg_commit (ev)
#   sizing_iv  : SIZING_RESULT co dong "sizing_iv: DAT" + jar NJ_MD5 + "smoke_start_ms=<..>" (ev). "KHONG DO DUOC" khong phai DAT
#                => chi qua bang override (ghi ro, ADD22 §3 iv).
#   script_v   : tu kiem: manifest go-live khop (M5) + md5(monitor+lib) co trong A1_APPROVED_MONITOR.md5 (ev = file A1)
# OVERRIDE (chi cho cac truong tren, KHONG cho (a)/(b)): GATE_OVERRIDE_BY="<ten nguoi>" GATE_OVERRIDE_WHY="<ly do >= 10 ky tu>" =>
#   truong thieu ghi "<truong>=OVERRIDE ly_do_thieu=..." + override_by / override_why / override_fields trong gate; micro_on in CANH BAO TO.
# Ghi (umask 077, ban cu => .bak_<ts>): jar_md5, ingestor_md5, created_ms, expires_ms (= created + 48 h), 6 truong tren, prereg_commit,
#   prereg_file, report + report_sha256, by. golive_micro_on.sh kiem DU cac dong + han + ev ton tai (gl_gate strict).
# Ma thoat: 0 da ghi (hoac DRY in) | 1 TU CHOI.
# =============================================================================
set -uo pipefail
. "$(cd "$(dirname "$0")" && pwd)/golive_lib.sh"
gl_manifest_check "$0" || exit 1   # [WAVE1b M5] script + lib + manifest khop md5 da commit, lech => TU CHOI truoc moi viec
PW=${PARITY_W:-/home/ubuntu/claude_master/parity_v12w}
GMICRO_TARGET=${GMICRO_TARGET:-$PW/gmicro_target.json}
PREREG_REPO=${PREREG_REPO:-/home/ubuntu/claude_master/vz_e1_wt}
PREREG_FILE=${PREREG_FILE:-docs/prereg/PREREG_PARITY_V12_DRY_ADDENDUM22_GRID.md}
GMICRO_MANUAL=${GMICRO_MANUAL:-}; REPLAY_RESULT=${REPLAY_RESULT:-}; SIZING_RESULT=${SIZING_RESULT:-}
OVB=${GATE_OVERRIDE_BY:-}; OVW=${GATE_OVERRIDE_WHY:-}
PRC=${1:-}; REP=${2:-$(ls -t "$PW"/report_*.out 2>/dev/null | head -1)}
G=$GATE_DIR/GOLIVE_GATE_MICRO.ok
no() { echo "TU CHOI: $*"; exit 1; }
# ---- (b) prereg
[[ "$PRC" =~ ^[0-9a-f]{7,40}$ ]] || no "prereg_commit '$PRC' khong hop le (hex 7-40). Dung: bash $0 <prereg_commit> [report]"
git -C "$PREREG_REPO" cat-file -e "$PRC^{commit}" 2>/dev/null || no "prereg_commit $PRC KHONG phai commit trong $PREREG_REPO"
git -C "$PREREG_REPO" cat-file -e "$PRC:$PREREG_FILE" 2>/dev/null || no "prereg_commit $PRC khong co $PREREG_FILE (ADD22)"
PN=$(basename "$PREREG_FILE" | sed -n 's/^PREREG_PARITY_V12_DRY_ADDENDUM\([0-9]*\).*/\1/p')
PMAX=$(git -C "$PREREG_REPO" ls-tree --name-only "$PRC" "$(dirname "$PREREG_FILE")/" 2>/dev/null | sed -n 's/.*PREREG_PARITY_V12_DRY_ADDENDUM\([0-9]*\).*/\1/p' | sort -n | tail -1)
[ -n "$PN" ] && [ "$PN" = "$PMAX" ] || no "prereg $PREREG_FILE (ADD$PN) KHONG phai addendum PREREG_PARITY_V12_DRY moi nhat tai $PRC (moi nhat ADD$PMAX)"
PHEAD=$(git -C "$PREREG_REPO" ls-tree --name-only HEAD "$(dirname "$PREREG_FILE")/" 2>/dev/null | sed -n 's/.*PREREG_PARITY_V12_DRY_ADDENDUM\([0-9]*\).*/\1/p' | sort -n | tail -1)
[ "$PHEAD" = "$PN" ] || no "repo prereg HEAD co addendum PREREG_PARITY_V12_DRY moi hon (ADD$PHEAD > ADD$PN) — gate phai theo prereg moi nhat"
git -C "$PREREG_REPO" merge-base --is-ancestor "$PRC" HEAD 2>/dev/null || no "prereg_commit $PRC KHONG nam tren lich su HEAD cua $PREREG_REPO"
PRCF=$(git -C "$PREREG_REPO" rev-parse "$PRC^{commit}")
# ---- report + gmicro_target
[ -s "$REP" ] || no "khong co report G-MICRO ($REP)"
AGE=$(( $(date +%s) - $(stat -c %Y "$REP") )); [ "$AGE" -le "$GATE_MAX_AGE_S" ] || no "report $REP cu ${AGE}s > ${GATE_MAX_AGE_S}s"
GL=$(grep -a '^G-MICRO:' "$REP" | tail -1)
[ -n "$GL" ] || no "report $REP khong co dong 'G-MICRO:'"
TJ=$(python3 -I -c 'import json,sys; d=json.load(open(sys.argv[1])); print(d.get("target_md5",""), d.get("smoke_start_ms",""), d.get("target_jar",""), d.get("prereg",""))' "$GMICRO_TARGET" 2>/dev/null) || no "khong doc duoc $GMICRO_TARGET"
read -r TMD5 SMS TJAR TPRE <<< "$TJ"
[ "$TMD5" = "$NJ_MD5" ] || no "gmicro_target target_md5=$TMD5 != jar pin $NJ_MD5"
[[ "$SMS" =~ ^[0-9]{13}$ ]] || no "gmicro_target thieu smoke_start_ms"
# ---- (a) 242 CHI DOC: jar + ingestor DANG chay = pin
ST=$(gl_state242) || no "ssh toi 242 loi (doc jar/ingestor dang chay)"
{ echo "$ST" | grep -qx END_STATE && ! echo "$ST" | grep -q '^ERR='; } || no "doc trang thai 242 khong tron ven"
[ "$(sv NPROC)" = 1 ] || no "242: so process v_t_m = $(sv NPROC) (can 1)"
[ "$(sv JAR_MD5)" = "$NJ_MD5" ] || no "242: jar DANG chay $(sv JAR_MD5) != pin $NJ_MD5"
[ "$(sv ING_MD5)" = "$ING_FIN_MD5" ] || no "242: ingestor DANG chay '$(sv ING_MD5)' != pin $ING_FIN_MD5"
echo "OK 242: 1 process, jar $NJ_MD5, ingestor $ING_FIN_MD5 (dang chay); prereg $PRCF $PREREG_FILE (moi nhat ADD$PMAX)"
# ---- truong ADD22 §3
WHYS=""; OVF=""
declare -A V
fld() {   # fld <truong> <ly do thieu | rong = DAT> <ev> [them]
  if [ -z "$2" ]; then V[$1]="DAT ev=$3${4:+ $4}"; echo "  OK    $1: DAT (ev $3)"
  else WHYS="$WHYS
  - $1: $2"; OVF="$OVF $1"; V[$1]="OVERRIDE ly_do_thieu=$(printf '%s' "$2" | tr -c 'A-Za-z0-9_.:=/+-' '_' | cut -c1-120)"; echo "  THIEU $1: $2"; fi
}
has() { grep -aqE "$2" "$1" 2>/dev/null; }
ev_ok() { [ -n "$1" ] && [ -s "$1" ] && [ -r "$1" ]; }
git_clean() { local d; d=$(cd "$(dirname "$1")" && pwd) || return 1; git -C "$d" ls-files --error-unmatch "$d/$(basename "$1")" >/dev/null 2>&1 && git -C "$d" diff --quiet HEAD -- "$d/$(basename "$1")" 2>/dev/null; }
echo "--- truong ADD22 §3 (bang chung):"
# gmicro_i
if echo "$GL" | grep -qE '^G-MICRO: DAT( |$)|i=True'; then fld gmicro_i "" "$REP" "n_sach=$(echo "$GL" | grep -oE "sach= \[[^]]*\]" | grep -oE "'[0-9-]+'" | wc -l)"
else fld gmicro_i "G-MICRO chua DAT (report: $GL)" ""; fi
# gmicro_ii + smoke (bien ban tay ADD22 §2.5)
MW=""
if ! ev_ok "$GMICRO_MANUAL"; then MW="thieu bien ban GMICRO_MANUAL (GMICRO_MANUAL='$GMICRO_MANUAL')"
elif ! [[ "$(basename "$GMICRO_MANUAL")" =~ ^GMICRO_MANUAL_.*\.md$ ]]; then MW="ten file khong phai GMICRO_MANUAL_*.md"
elif ! git_clean "$GMICRO_MANUAL"; then MW="bien ban CHUA commit / co sua chua commit (ADD22 §2.5)"
elif ! has "$GMICRO_MANUAL" "$NJ_MD5"; then MW="bien ban khong ghi jar $NJ_MD5"
elif ! has "$GMICRO_MANUAL" "smoke_start_ms=$SMS"; then MW="bien ban khong ghi smoke_start_ms=$SMS (gmicro_target)"; fi
if [ -n "$MW" ]; then fld gmicro_ii "$MW" ""; fld smoke "$MW" ""
else
  if has "$GMICRO_MANUAL" '^gmicro_ii: DAT( |$)'; then fld gmicro_ii "" "$GMICRO_MANUAL"; else fld gmicro_ii "bien ban khong co dong 'gmicro_ii: DAT'" ""; fi
  if has "$GMICRO_MANUAL" '^smoke: DAT( |$)'; then fld smoke "" "$GMICRO_MANUAL"; else fld smoke "bien ban khong co dong 'smoke: DAT'" ""; fi
fi
# replay_iii
RPP=$(git -C "$PREREG_REPO" ls-tree --name-only "$PRC" "$(dirname "$PREREG_FILE")/" 2>/dev/null | grep -E '/PREREG_E2E_REPLAY_V12[^/]*\.md$' | head -1)
if [ -z "$RPP" ]; then fld replay_iii "chua co prereg PREREG_E2E_REPLAY_V12*.md trong $PRC" ""
elif ! ev_ok "$REPLAY_RESULT"; then fld replay_iii "thieu file ket qua replay (REPLAY_RESULT='$REPLAY_RESULT')" ""
elif ! has "$REPLAY_RESULT" "$NJ_MD5"; then fld replay_iii "ket qua replay khong ghi jar $NJ_MD5" ""
elif ! has "$REPLAY_RESULT" '^replay_iii: DAT( |$)'; then fld replay_iii "ket qua replay khong co dong 'replay_iii: DAT'" ""
else fld replay_iii "" "$REPLAY_RESULT" "prereg=$RPP"; fi
# sizing_iv
if ! ev_ok "$SIZING_RESULT"; then fld sizing_iv "thieu file ket qua sizing (SIZING_RESULT='$SIZING_RESULT')" ""
elif ! has "$SIZING_RESULT" "$NJ_MD5" || ! has "$SIZING_RESULT" "smoke_start_ms=$SMS"; then fld sizing_iv "ket qua sizing khong ghi jar $NJ_MD5 + smoke_start_ms=$SMS" ""
elif ! has "$SIZING_RESULT" '^sizing_iv: DAT( |$)'; then fld sizing_iv "ket qua sizing khong co dong 'sizing_iv: DAT' (KHONG DO DUOC chi qua override)" ""
else fld sizing_iv "" "$SIZING_RESULT"; fi
# script_v (manifest da kiem o dau script)
if gl_mon_approved; then fld script_v "" "$A1_APPROVED_FILE" "monitor_lib=$(gl_mon_m12) manifest=$(md5sum < "$GL_HERE/GOLIVE_MANIFEST.md5" | cut -c1-12)"
else fld script_v "md5(monitor+lib) $(gl_mon_m12) chua co trong $A1_APPROVED_FILE" ""; fi
OVL=""
if [ -n "$OVF" ]; then
  if [ -z "$OVB" ] || [ "${#OVW}" -lt 10 ]; then
    no "thieu bang chung ADD22 §3:$WHYS
  (override CHI khi MASTER chiu trach nhiem: GATE_OVERRIDE_BY=<ten> GATE_OVERRIDE_WHY=<ly do >= 10 ky tu>)"
  fi
  echo "!!! OVERRIDE boi '$OVB' (ly do: $OVW) cho:$OVF"
  OVL="
override_by=$(printf '%s' "$OVB" | tr -d '\n\r' | cut -c1-80)
override_why=$(printf '%s' "$OVW" | tr -d '\n\r' | cut -c1-300)
override_fields=$(echo $OVF)"
fi
NOW=$(( $(date +%s) * 1000 )); EXP=$(( NOW + GATE_MAX_AGE_S * 1000 ))
BODY="# G-MICRO gate — golive_make_gate.sh $(TZ=Asia/Ho_Chi_Minh date '+%F %T') (+07)
jar_md5=$NJ_MD5
ingestor_md5=$ING_FIN_MD5
created_ms=$NOW
expires_ms=$EXP
gmicro_i=${V[gmicro_i]}
gmicro_ii=${V[gmicro_ii]}
smoke=${V[smoke]} smoke_start_ms=$SMS target_jar=$TJAR prereg_target=$TPRE
replay_iii=${V[replay_iii]}
sizing_iv=${V[sizing_iv]}
script_v=${V[script_v]}
prereg_commit=$PRCF
prereg_file=$PREREG_FILE
report=$REP
report_sha256=$(sha256sum < "$REP" | cut -c1-64)$OVL
by=MASTER golive_make_gate.sh"
echo "$BODY"
[ "${DRY:-0}" = 1 ] && { echo "DRY=1: KHONG ghi $G"; exit 0; }
mkdir -p "$GATE_DIR" || no "khong tao duoc $GATE_DIR"
[ -f "$G" ] && cp -p "$G" "$G.bak_$(date +%s)"
( umask 077; printf '%s\n' "$BODY" > "$G.tmp" ) && mv -f "$G.tmp" "$G" || no "khong ghi duoc $G"
R=$(gl_gate "$G" 1); echo "$R"; echo "$R" | grep -q '^OK' || no "gate vua ghi KHONG qua gl_gate strict (loi script)"
echo "=== XONG: $G (het han sau $((GATE_MAX_AGE_S / 3600)) h)$([ -n "$OVF" ] && echo " — CO OVERRIDE:$OVF")"
