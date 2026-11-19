#!/usr/bin/env bash
# =============================================================================
# golive_first_trade_check.sh - [OPS5 muc 1] KIEM LENH THAT (tra no "sizing_iv", ADD22 ?3 (iv)). CHI DOC 242 + CHI DOC san.
#   bash $OPS/golive_first_trade_check.sh          # tay (owner/MASTER), DRY=1: chi doc log + tinh (a), KHONG goi san, KHONG ghi, KHONG Telegram
#   FT_CRON=1 (cron */5, flock rieng, timeout 110): KHONG co co monitor ($GL_MON_FLAG, micro/pilot dang bat) => thoat ngay, 0 ssh / 0 call.
# Moi dong "[C3-LIVE] SUBMIT" cua JVM HIEN TAI (sau dong MainClass cuoi trong FT_TAIL byte log) CHUA kiem:
#   (a) budget trong +-FT_TOL (2 %) cua 0,0225 x C3_CAPITAL x (1 - U_before/0,6) (C3_CAPITAL = env PROCESS qua gl_state242);
#       level DCA* => legIdx >= 1; legIdx < 0 => FAIL (khong phai leg c3). 1 dong lech => sizing_iv: FAIL.
#       Kem cot chan doan cap_ngam = budget / (0,0225 x (1 - U/0,6)) (von bot thuc dung; KHONG dung de cham).
#   (b) doi chieu san tk con qua gl_api242 mon (duong CHI DOC da audit, 90 weight; chi goi khi co cid dang cho):
#       vi the symbol co tren san (POS_LIST) | da dong (khong con trong so c3) ; con trong so ma san KHONG co sau FT_GRACE_S => FAIL.
#       cum DA arm (C3_ARMED_SYMS) => phai co lenh algo c3 (ALGO_C3_SYMS) cung symbol; thieu 2 luot lien tiep => FAIL.
#       chua arm => cho (kiem lai moi luot toi khi arm / dong / qua FT_PENDING_MAX_S).
#   (c) bang chung $FT_DIR/SIZING_IV_<ts>.md (dong "sizing_iv: DAT|FAIL", md5 jar, tung dong so sanh) khi co ket qua MOI.
#   (d) Telegram tom tat (lib tg; token theo co che san co, khong in); FAIL KHONG giai thich duoc / (b) FAIL => "KHAN";
#       FAIL chi do C_eff / TIER_3 (xem [OPS5_FIX M-3]) => "CANH BAO ... can MASTER phan xu" (khong chu KHAN).
# Idempotent: $FT_DIR/state.txt (1 dong / cid). Ma thoat: 0 | 2 co FAIL moi | 1 DUNG.
# =============================================================================
set -uo pipefail
_OPS=$(cd "$(dirname "$0")" && pwd); _APO=${A1_APPROVED_OPS:-/home/ubuntu/claude_master/deploy/gates/A1_APPROVED_OPS.commit}; _PW=""
_HC=$(git -C "$_OPS" rev-parse --verify -q HEAD 2>/dev/null) || _PW="$_OPS khong phai repo git"
[ -n "$_PW" ] || { [ -f "$_APO" ] && grep -qE "^$_HC([[:space:]]|\$)" "$_APO"; } || _PW="HEAD $_HC CHUA duoc A1 duyet (khong co trong $_APO)"
[ -n "$_PW" ] || git -C "$_OPS" diff --quiet HEAD -- . 2>/dev/null || _PW="$_OPS co sua CHUA commit (git diff HEAD)"
[ -z "$_PW" ] || { echo "TU CHOI [m1]: $_PW - KHONG lam gi."; exit 1; }
FT_CRON=${FT_CRON:-0}
LOGDIR=${LOGDIR:-/home/ubuntu/claude_master/deploy}
FT_DIR=${FT_DIR:-$LOGDIR/first_trade}
GL_MON_FLAG=${GL_MON_FLAG:-$LOGDIR/golive_monitor.on}
if [ "$FT_CRON" = 1 ]; then
  [ -f "$GL_MON_FLAG" ] || exit 0
  FA=$(sed -n 's/^C3_ACCOUNT=//p' "$GL_MON_FLAG" | head -1); FK=$(sed -n 's/^KEYS_FILE=//p' "$GL_MON_FLAG" | head -1)
  case "$FA" in SUB|MAIN) export C3_ACCOUNT=$FA ;; esac
  [ -n "$FK" ] && export KEYS_FILE=$FK
  mkdir -p "$FT_DIR"; CL=$FT_DIR/ft_cron.log
  [ "$(stat -c %s "$CL" 2>/dev/null || echo 0)" -gt 10000000 ] && mv -f "$CL" "$CL.1"
  exec >> "$CL" 2>&1
  export GL_SSH_TRIES=${GL_SSH_TRIES:-1} GL_SSH_TIMEOUT_S=${GL_SSH_TIMEOUT_S:-30} GL_TG_TIMEOUT_S=${GL_TG_TIMEOUT_S:-10}
fi
# moi output qua mask token (dong bo: chay lai chinh no qua ong sed, giu ma thoat)
if [ -z "${_FT_MASKED:-}" ]; then export _FT_MASKED=1; bash "$0" "$@" 2>&1 | sed -u -E 's/[0-9]{8,10}:[A-Za-z0-9_-]{30,}/<TOKEN>/g'; exit "${PIPESTATUS[0]}"; fi
. "$_OPS/golive_lib.sh"
gl_manifest_check "$0" || exit 1
FT_TAIL=${FT_TAIL:-$([ "$FT_CRON" = 1 ] && echo 6000000 || echo 30000000)};   # cron */5: 6 MB (~45 phut log) du - cid da kiem nam trong state
 FT_TOL=${FT_TOL:-0.02}; FT_K=${FT_K:-0.0225}; FT_UMAX=${FT_UMAX:-0.6}
FT_GRACE_S=${FT_GRACE_S:-120}; FT_PENDING_MAX_S=${FT_PENDING_MAX_S:-604800}
FT_STATE=$FT_DIR/state.txt
TS=$(TZ=Asia/Ho_Chi_Minh date +%Y%m%d_%H%M%S); NOW=$(date +%s)
say "=== golive_first_trade_check TS=$TS DRY=$DRY C3_ACCOUNT=$C3_ACCOUNT$([ "$FT_CRON" = 1 ] && echo ' cron') ==="
ST=$(gl_state242) && echo "$ST" | grep -qx END_STATE && ! echo "$ST" | grep -q '^ERR=' || { say "DUNG: doc trang thai 242 loi (ssh?) - thu lai luot sau"; exit 1; }
CAP=$(sv ENV_C3_CAPITAL); JMD5=$(sv JAR_MD5)
[[ "$CAP" =~ ^[0-9]+(\.[0-9]+)?$ ]] && awk -v c="$CAP" 'BEGIN{exit !(c>0)}' || { say "DUNG: C3_CAPITAL process khong hop le ('$CAP')"; exit 1; }
say "process pid=$(sv PID) adapter=$(sv ENV_LIVE_ADAPTER) C3_CAPITAL=$CAP jar=$JMD5"
LOGR=$(s242in "bash -s -- $A $FT_TAIL" <<'EOR'
A=$1; TB=$2; cd "$A" || { echo "ERR=cd"; echo END_FT; exit 0; }
nice -n 19 tail -c "$TB" logs/full.log 2>/dev/null | awk '/MainClass: com\.binance\.chuyennd\.trading\.BinanceOrderTradingManager/{k=0; mc=$1" "$2} /\[C3-LIVE\] SUBMIT /{k++; s[k]=$0} END{print "JVM_START=" mc; for (i=1; i<=k; i++) print "S=" s[i]}'
echo END_FT
EOR
) || LOGR="ERR=ssh"
echo "$LOGR" | grep -qx END_FT && ! echo "$LOGR" | grep -q '^ERR=' || { say "DUNG: doc log 242 loi ($(echo "$LOGR" | grep '^ERR=' | head -1)) - thu lai luot sau"; exit 1; }
JVS=$(echo "$LOGR" | sed -n 's/^JVM_START=//p' | head -1)
say "JVM hien tai bat dau: ${JVS:-(ngoai cua so ${FT_TAIL} byte - moi dong trong cua so)}; so dong SUBMIT JVM nay: $(echo "$LOGR" | grep -c '^S=')"
mkdir -p "$FT_DIR" 2>/dev/null; [ -f "$FT_STATE" ] || : > "$FT_STATE" 2>/dev/null
# state: cid|t_submit|sym|level|a|b|arm|nowarm|first|last|detail
stg() { grep -F "$1|" "$FT_STATE" 2>/dev/null | head -1; }
NEWA=""; ROWS=""; ANYF=0; NPEND=0
declare -A R_T R_S R_L R_A R_B R_ARM R_N R_F R_D
while IFS= read -r ln; do
  [ -n "$ln" ] || continue
  cid=$(printf '%s' "$ln" | grep -oE 'cid=[^ ]+' | head -1 | cut -d= -f2)
  [ -n "$cid" ] || cid="nocid_$(printf '%s' "$ln" | md5sum | cut -c1-12)"
  old=$(stg "$cid")
  if [ -n "$old" ]; then
    IFS='|' read -r _ t sy lv a b arm nw f la d <<<"$old"
    R_T[$cid]=$t; R_S[$cid]=$sy; R_L[$cid]=$lv; R_A[$cid]=$a; R_B[$cid]=$b; R_ARM[$cid]=$arm; R_N[$cid]=$nw; R_F[$cid]=$f; R_D[$cid]=$d
    continue
  fi
  d1=$(printf '%s' "$ln" | cut -c1-19)
  t=$(TZ=Asia/Ho_Chi_Minh date -d "$(printf '%s' "$d1" | awk '{split($1,a,"/"); print a[3]"-"a[2]"-"a[1]" "$2}')" +%s 2>/dev/null || echo 0)
  sy=$(printf '%s' "$ln" | sed -n 's/.*\[C3-LIVE\] SUBMIT \([A-Z0-9]*\) .*/\1/p')
  lv=$(printf '%s' "$ln" | sed -n 's/.*\[C3-LIVE\] SUBMIT [A-Z0-9]* \([A-Z0-9_]*\) .*/\1/p')
  bu=$(printf '%s' "$ln" | grep -oE ' budget=[-0-9.eE]+' | cut -d= -f2); li=$(printf '%s' "$ln" | grep -oE ' legIdx=-?[0-9]+' | cut -d= -f2)
  ub=$(printf '%s' "$ln" | grep -oE ' U_before=[-0-9.eE]+' | cut -d= -f2)
  ev=$(awk -v b="$bu" -v u="$ub" -v c="$CAP" -v k="$FT_K" -v m="$FT_UMAX" -v tol="$FT_TOL" -v li="$li" -v lv="$lv" 'BEGIN{
    if (b=="" || u=="" || li=="") { printf "FAIL;thieu_truong(budget=%s,U_before=%s,legIdx=%s)", b, u, li; exit }
    e=k*c*(1-u/m); r=(e>0)?b/e-1:999; cn=(1-u/m>0)?b/(k*(1-u/m)):-1; why=""
    if (e<=0) why=why" ky_vong<=0(U_before>=" m ")"; else if (r>tol || r< -tol) why=why sprintf(" budget_lech_%+.2f%%", r*100)
    if (li<0) why=why" legIdx<0"
    if (lv ~ /DCA/ && li<1) why=why" leg_DCA_legIdx<1"
    printf "%s;ky_vong=%.4f lech=%+.3f%% cap_ngam=%.2f%s", (why=="")?"DAT":"FAIL", e, r*100, cn, why }')
  a=${ev%%;*}; d="${ev#*;} budget=$bu U_before=$ub legIdx=$li"
  R_T[$cid]=$t; R_S[$cid]=$sy; R_L[$cid]=$lv; R_A[$cid]=$a; R_B[$cid]=CHO; R_ARM[$cid]=CHO; R_N[$cid]=0; R_F[$cid]=$NOW; R_D[$cid]=$d
  NEWA="$NEWA $cid"
  [ "$a" = FAIL ] && ANYF=1
done < <(echo "$LOGR" | sed -n 's/^S=//p')
CIDS=$(for c in "${!R_T[@]}"; do echo "${R_T[$c]} $c"; done | sort -n | awk '{print $2}' | tr '\n' ' ')
for c in $CIDS; do case "${R_B[$c]}|${R_ARM[$c]}" in *CHO*|*NOALGO1*) NPEND=$((NPEND + 1));; esac; done
API=""; APIOK=0; CHG=""; KHANB=0
if [ "$NPEND" -gt 0 ] && [ "$DRY" != 1 ]; then
  API=$(gl_api242 mon) || API="ERR=ssh_api"
  echo "$API" | grep -qx END_API && ! echo "$API" | grep -q '^ERR' && [ "$(av API_OK)" = 1 ] && [ "$(av C3_ARMED_SYMS)" != '?' ] && APIOK=1
  say "san (mon, CHI DOC): API_OK=$(av API_OK) POS_LIST=[$(av POS_LIST)] C3_BOOK_LIST=[$(av C3_BOOK_LIST)] C3_ARMED_SYMS=[$(av C3_ARMED_SYMS)] ALGO_C3_SYMS=[$(av ALGO_C3_SYMS)] W_USED_1M=$(av W_USED_1M)"
  [ "$APIOK" = 1 ] || say "!! doc san KHONG tron ven ($(echo "$API" | grep '^ERR' | head -2 | tr '\n' ' ')) - (b) = KHONG DO DUOC luot nay, giu cho"
elif [ "$DRY" = 1 ]; then say "DRY=1: KHONG goi san (b)"; fi
inl() { case ",$2," in *",$1,"*) return 0;; *) return 1;; esac; }
if [ "$APIOK" = 1 ]; then
  PL=$(av POS_LIST); BL=$(av C3_BOOK_LIST); AL=$(av C3_ARMED_SYMS); GL=$(av ALGO_C3_SYMS)
  for c in $CIDS; do
    sy=${R_S[$c]}; age=$(( NOW - ${R_T[$c]:-0} )); b0=${R_B[$c]}; m0=${R_ARM[$c]}
    if [ "$b0" = CHO ]; then
      if inl "$sy" "$PL"; then R_B[$c]=OK_CO_VI_THE
      elif inl "$sy" "$BL"; then [ "$age" -gt "$FT_GRACE_S" ] && R_B[$c]=FAIL_SO_CO_SAN_KHONG || :
      else R_B[$c]=OK_DA_DONG; fi
    fi
    case "${R_ARM[$c]}" in CHO|NOALGO1)
      if inl "$sy" "$AL"; then
        if inl "$sy" "$GL"; then R_ARM[$c]=OK_ARM_CO_ALGO
        elif [ "${R_ARM[$c]}" = NOALGO1 ]; then R_ARM[$c]=FAIL_ARM_KHONG_ALGO
        else R_ARM[$c]=NOALGO1; fi
      elif ! inl "$sy" "$PL" && ! inl "$sy" "$BL"; then R_ARM[$c]=NA_DONG_TRUOC_ARM
      elif [ $(( NOW - ${R_F[$c]:-$NOW} )) -gt "$FT_PENDING_MAX_S" ]; then R_ARM[$c]=HET_THEO_DOI; fi;;
    esac
    [ "${R_B[$c]}" != "$b0" ] && CHG="$CHG $c"
    [ "${R_ARM[$c]}" != "$m0" ] && [ "${R_ARM[$c]}" != NOALGO1 ] && CHG="$CHG $c"
    case "${R_B[$c]}${R_ARM[$c]}" in *FAIL*) case "$b0$m0" in *FAIL*) ;; *) ANYF=1; KHANB=1;; esac;; esac
  done
fi
# [OPS5_FIX M-3] PHAN LOAI dong (a) FAIL - KHONG doi phan quyet prereg (sizing_iv van FAIL; tieu chi 0,0225 x C3_CAPITAL x (1-U/0,6) +-2 % giu nguyen).
#   C_eff = min(C3_CAPITAL, eq, avail+margin) (jar C3MainEquity.capital():163-170). eq = C3_CAPITAL + (TMB - tmb0) (moc $SUB_BASE_FILE, nhu monitor ?5);
#   avail+margin = AVAIL / (1 - U_before) (margin c3 = U_before x cap). NGUON: gl_api242 mon CUA LUOT NAY (CHI DOC; gia tri LUC CHAY, khong phai luc SUBMIT).
#   budget khop +-FT_TOL voi 0,0225 x C_eff x (1-U/0,6) => GIAI_THICH_DUOC_CEFF. TIER_3 x 0,5 (CoinRankManager, khi TIER_FLAT env process != 1) => GIAI_THICH_DUOC_TIER3x0.5
#   (nhan rieng). Con lai (hoac lech do legIdx / thieu truong / khong doc duoc san) => KHONG_GIAI_THICH_DUOC. Telegram: co dong KHONG giai thich duoc
#   hoac (b) FAIL => KHAN; chi co FAIL giai thich duoc => CANH BAO (khong KHAN) "can MASTER phan xu".
TFL=$(sv ENV_TIER_FLAT); TMBV=""; AVV=""
[ "$APIOK" = 1 ] && { TMBV=$(av TMB); AVV=$(av AVAIL); }
T0B=$(sed -n 's/^tmb0=//p' "$SUB_BASE_FILE" 2>/dev/null | head -1)
CSRC="gl_api242 mon luot $TS (CHI DOC, luc chay): TMB=${TMBV:-?} AVAIL=${AVV:-?} | moc tmb0=${T0B:-?} ($SUB_BASE_FILE) | TIER_FLAT env process=${TFL:-(khong dat)}"
cls_fail() {   # $1 budget $2 U_before $3 ly do FAIL -> nhan phan loai
  case "$3" in *"legIdx<"*|*thieu_truong*) echo "KHONG_GIAI_THICH_DUOC(loi_legIdx/truong)"; return;; esac
  awk -v b="$1" -v u="$2" -v c="$CAP" -v k="$FT_K" -v m="$FT_UMAX" -v tol="$FT_TOL" -v tmb="$TMBV" -v av="$AVV" -v t0="$T0B" -v tf="$TFL" '
  function isn(x) { return x ~ /^-?[0-9]+(\.[0-9]+)?([eE][-+]?[0-9]+)?$/ }
  function ok(e) { return e > 0 && b / e - 1 <= tol && b / e - 1 >= -tol }
  BEGIN { if (!isn(b) || !isn(u)) { print "KHONG_GIAI_THICH_DUOC(thieu_truong)"; exit }
    f = 1 - u / m; ce = c; src = "C3_CAPITAL"; have = 0
    if (isn(tmb) && isn(t0)) { eq = c + (tmb - t0); have = 1; if (eq < ce) { ce = eq; src = "eq=C3_CAPITAL+(TMB-tmb0)" } }
    if (isn(av) && u < 1) { ac = av / (1 - u); have = 1; if (ac < ce) { ce = ac; src = "avail+margin=AVAIL/(1-U)" } }
    if (have && ok(k * ce * f)) { printf "GIAI_THICH_DUOC_CEFF(C_eff=%.2f,%s)\n", ce, src; exit }
    if (tf != "1" && (ok(0.5 * k * c * f) || (have && ok(0.5 * k * ce * f)))) { printf "GIAI_THICH_DUOC_TIER3x0.5(TIER_FLAT=%s)\n", (tf == "" ? "tat" : tf); exit }
    if (have) printf "KHONG_GIAI_THICH_DUOC(C_eff=%.2f,%s)\n", ce, src; else print "KHONG_GIAI_THICH_DUOC(khong_doc_duoc_C_eff)" }'
}
declare -A R_C
for c in $CIDS; do
  [ "${R_A[$c]}" = FAIL ] || continue
  pc=$(printf '%s' "${R_D[$c]}" | grep -oE 'phan_loai=[^ ]+' | head -1 | cut -d= -f2-)
  if [ -z "$pc" ]; then
    pc=$(cls_fail "$(printf '%s' "${R_D[$c]}" | grep -oE 'budget=[-0-9.eE]+' | tail -1 | cut -d= -f2)" "$(printf '%s' "${R_D[$c]}" | grep -oE 'U_before=[-0-9.eE]+' | tail -1 | cut -d= -f2)" "${R_D[$c]}")
    R_D[$c]="${R_D[$c]} phan_loai=$pc"
  fi
  R_C[$c]=$pc
done
NXC=0; NXT=0; NKG=0; NKGNEW=0
for c in $CIDS; do case "${R_C[$c]:-}" in GIAI_THICH_DUOC_CEFF*) NXC=$((NXC + 1));; GIAI_THICH_DUOC_TIER3*) NXT=$((NXT + 1));; KHONG*) NKG=$((NKG + 1)); case " $NEWA " in *" $c "*) NKGNEW=$((NKGNEW + 1));; esac;; esac; done
PLS="giai_thich_duoc_C_eff=$NXC giai_thich_duoc_TIER3x0.5=$NXT KHONG_giai_thich_duoc=$NKG"
CHG=$(echo $NEWA $CHG | tr ' ' '\n' | sort -u | tr '\n' ' ')
# tong (moi cid trong state + moi): sizing_iv theo (a)
NA=0; NAF=0; NBF=0
for c in $CIDS; do NA=$((NA + 1)); [ "${R_A[$c]}" = FAIL ] && NAF=$((NAF + 1)); case "${R_B[$c]}${R_ARM[$c]}" in *FAIL*) NBF=$((NBF + 1));; esac; done
SIV=DAT; [ "$NAF" -gt 0 ] && SIV=FAIL; [ "$NA" = 0 ] && SIV="KHONG_DO_DUOC (0 dong SUBMIT JVM nay)"
DCS=DAT; [ "$NBF" -gt 0 ] && DCS=FAIL; [ "$APIOK" = 1 ] || DCS="${DCS}_(luot nay khong doc duoc san)"
row() { printf '| %s | %s | %s | %s | %s | %s | %s | %s |\n' "$1" "$(TZ=Asia/Ho_Chi_Minh date -d @"${R_T[$1]:-0}" '+%d/%m %H:%M:%S')" "${R_S[$1]}" "${R_L[$1]}" "${R_A[$1]}" "${R_B[$1]}/${R_ARM[$1]}" "${R_D[$1]}" "${R_C[$1]:--}"; }
for c in $CIDS; do say "  $(row "$c")"; done
say "sizing_iv: $SIV (dong SUBMIT JVM nay: $NA, lech: $NAF) | doi_chieu_san: $DCS (FAIL: $NBF) | moi/doi luot nay:${CHG:- 0}"
[ "$NAF" -gt 0 ] && say "phan_loai_FAIL (a): $PLS (phan quyet prereg GIU NGUYEN) | nguon C_eff: $CSRC"
if [ "$DRY" = 1 ]; then say "DRY=1: KHONG ghi state / bang chung / Telegram"; exit 0; fi
# ghi state (thay toan bo dong cua cac cid JVM nay, giu dong cu khac)
{ for c in $CIDS; do printf '%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s\n' "$c" "${R_T[$c]}" "${R_S[$c]}" "${R_L[$c]}" "${R_A[$c]}" "${R_B[$c]}" "${R_ARM[$c]}" "${R_N[$c]}" "${R_F[$c]}" "$NOW" "${R_D[$c]}"; done
  grep -vF -f <(for c in $CIDS; do printf '%s|\n' "$c"; done) "$FT_STATE" 2>/dev/null || :; } > "$FT_STATE.tmp" && mv -f "$FT_STATE.tmp" "$FT_STATE"
CHG=$(echo $CHG); [ -n "$CHG" ] || { say "khong co ket qua moi - khong ghi bang chung, khong Telegram"; exit 0; }
EVF=$FT_DIR/SIZING_IV_$TS.md
{ echo "# SIZING_IV $TS (golive_first_trade_check, ADD22 ?3 (iv))"
  echo "sizing_iv: $SIV"
  echo "doi_chieu_san: $DCS"
  echo "jar_md5: $JMD5"
  echo "c3_capital_process: $CAP | cong thuc: budget trong +-$(awk -v t="$FT_TOL" 'BEGIN{print t*100}')% cua $FT_K x C3_CAPITAL x (1 - U_before/$FT_UMAX); DCA => legIdx>=1"
  echo "jvm_start: ${JVS:-?} | pid: $(sv PID) | adapter: $(sv ENV_LIVE_ADAPTER) | W_USED_1M: $(av W_USED_1M)"
  echo "moi_luot_nay: $CHG"
  echo "phan_loai_FAIL_a: $PLS (CHI chan doan - phan quyet prereg GIU NGUYEN; KHONG noi tieu chi)"
  echo "nguon_C_eff: $CSRC"
  echo
  echo "| cid | gio +07 | symbol | level | (a) sizing | (b) san / arm | chi tiet | phan loai FAIL |"
  echo "|---|---|---|---|---|---|---|---|"
  for c in $CIDS; do row "$c"; done; } > "$EVF.tmp" && mv -f "$EVF.tmp" "$EVF"
say "bang chung: $EVF"
PFX="[golive] sizing_iv"
if [ "$KHANB" = 1 ] || [ "$NKGNEW" -gt 0 ]; then PFX="[golive] KHAN sizing_iv/doi chieu san"
elif [ "$ANYF" = 1 ]; then PFX="[golive] CANH BAO sizing_iv FAIL-GIAI-THICH-DUOC ($PLS) - can MASTER phan xu (prereg FAIL giu nguyen)"; fi
MSG="$PFX TS=$TS: sizing_iv=$SIV ($NA dong, lech $NAF) doi_chieu_san=$DCS (FAIL $NBF). Moi: $(for c in $CHG; do printf '%s %s a=%s b=%s/%s; ' "${R_S[$c]}" "${R_L[$c]}" "${R_A[$c]}" "${R_B[$c]}" "${R_ARM[$c]}"; done | cut -c1-1500) File $EVF"
tg "$MSG" || say "!! gui Telegram loi"
if [ "$ANYF" = 1 ]; then
  if [ "$KHANB" = 1 ] || [ "$NKGNEW" -gt 0 ]; then say "KHAN: co dong lech KHONG giai thich duoc / doi chieu san FAIL - bao MASTER"
  else say "CANH BAO: dong lech deu GIAI THICH DUOC ($PLS) - can MASTER phan xu"; fi
  exit 2
fi
exit 0
