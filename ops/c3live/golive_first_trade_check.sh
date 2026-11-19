#!/usr/bin/env bash
# =============================================================================
# golive_first_trade_check.sh - [OPS5 muc 1] KIEM LENH THAT (tra no "sizing_iv", ADD22 ?3 (iv)). CHI DOC 242 + CHI DOC san.
#   bash $OPS/golive_first_trade_check.sh          # tay (owner/MASTER), DRY=1: chi doc log + tinh (a), KHONG goi san, KHONG ghi, KHONG Telegram
#   FT_CRON=1 (cron */5, flock rieng, timeout 110): KHONG co co monitor ($GL_MON_FLAG, micro/pilot dang bat) => thoat ngay, 0 ssh / 0 call.
# Moi dong "[C3-LIVE] SUBMIT" trong CUA SO (OPS5_FIX MINOR B3: tu lan cham cuoi - FT_OVERLAP_S, doc full.log.1 + full.log, MOI doan JVM -
#   SUBMIT truoc JVM restart / truoc khi log xoay van duoc cham; lan dau: tu co micro hoac FT_WINDOW0_S) + moi cid CON CHO trong state, CHUA kiem:
#   (a) budget trong +-FT_TOL (2 %) cua 0,0225 x C3_CAPITAL x (1 - U_before/0,6) (C3_CAPITAL = env PROCESS qua gl_state242);
#       level DCA* => legIdx >= 1; legIdx < 0 => FAIL (khong phai leg c3). 1 dong lech => sizing_iv: FAIL.
#       Kem cot chan doan cap_ngam = budget / (0,0225 x (1 - U/0,6)) (von bot thuc dung; KHONG dung de cham).
#   (b) doi chieu san tk con qua gl_api242 mon (duong CHI DOC da audit, 90 weight; chi goi khi co cid dang cho):
#       vi the symbol co tren san (POS_LIST) | da dong (khong con trong so c3) ; con trong so ma san KHONG co sau FT_GRACE_S => FAIL.
#       cum DA arm (C3_ARMED_SYMS) => phai co lenh algo c3 (ALGO_C3_SYMS) cung symbol; thieu 2 luot lien tiep => FAIL.
#       chua arm => cho (kiem lai moi luot toi khi arm / dong / qua FT_PENDING_MAX_S).
#       [OPS5_FIX MINOR B4] lenh bi tu choi / huy (dong [C3-LIVE*] REJECT / "huy giu cho" / "tu choi cid=" / "KHONG gui" / status=REJECTED|EXPIRED;
#       khop cid, hoac cung symbol trong FT_REJ_WIN_S sau SUBMIT khi cid dong REJECT khong thuoc SUBMIT nao) => REJECTED (KHONG phai OK_DA_DONG,
#       KHONG tinh la bang chung sizing DAT; dong REJECTED ma (a) FAIL van tinh FAIL).
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
FT_CRON=${FT_CRON:-0}
LOGDIR=${LOGDIR:-/home/ubuntu/claude_master/deploy}
FT_DIR=${FT_DIR:-$LOGDIR/first_trade}
GL_MON_FLAG=${GL_MON_FLAG:-$LOGDIR/golive_monitor.on}
# [OPS5_FIX MINOR B-c] cron + co micro ma repo ban / HEAD chua duyet => KHONG im lang: ghi ly do vao ft_cron.log + Telegram CANH BAO 1 lan / ngay
#   (gui toi thieu, KHONG source lib cua repo chua duyet; token doc tu file, khong in). Tay => TU CHOI nhu cu.
[ "$FT_CRON" = 1 ] && [ ! -f "$GL_MON_FLAG" ] && exit 0   # cron, khong co micro/pilot => thoat im (truoc ca kiem pin)
if [ -n "$_PW" ] && [ "$FT_CRON" = 1 ] && [ -f "$GL_MON_FLAG" ]; then
  mkdir -p "$FT_DIR" 2>/dev/null; _D=$(TZ=Asia/Ho_Chi_Minh date +%Y%m%d)
  echo "[$(TZ=Asia/Ho_Chi_Minh date '+%F %T')] TU CHOI [m1]: $_PW - cron first_trade KHONG cham lenh that luot nay" >> "$FT_DIR/ft_cron.log" 2>/dev/null
  if [ "$(cat "$FT_DIR/pin_refuse_day.txt" 2>/dev/null)" != "$_D" ]; then
    _M="[golive] CANH BAO cron golive_first_trade_check TU CHOI [m1]: $_PW - lenh that KHONG duoc cham (sizing_iv) toi khi sua repo/pin. Bao 1 lan/ngay."
    if [ -n "${DEPLOY_TG_SINK:-}" ]; then { printf '%s\n' "$_M"; echo "----"; } >> "$DEPLOY_TG_SINK" && _OK=1
    else
      _TE=${DEPLOY_TG_ENV:-/home/ubuntu/.config/health242/tg.env}; _OK=0
      if [ -r "$_TE" ]; then
        _T=$(sed -nE 's/^[[:space:]]*(export[[:space:]]+)?(TG_TOKEN=|tele-token:[[:space:]]*)//p' "$_TE" | head -1 | tr -d '\r"')
        _C=$(sed -nE 's/^[[:space:]]*(export[[:space:]]+)?(TG_CHAT=|tele-chat-id:[[:space:]]*)//p' "$_TE" | head -1 | tr -d '\r"')
        [ -n "$_T" ] && [ -n "$_C" ] && [ "$(printf 'url = "https://api.telegram.org/bot%s/sendMessage"\n' "$_T" | curl -s -m 10 -o /dev/null -w '%{http_code}' -K - \
          --data-urlencode "chat_id=$_C" --data-urlencode "text=$_M" 2>/dev/null)" = 200 ] && _OK=1; _T=""; _C=""
      fi
    fi
    [ "${_OK:-0}" = 1 ] && echo "$_D" > "$FT_DIR/pin_refuse_day.txt"
  fi
  exit 1
fi
[ -z "$_PW" ] || { echo "TU CHOI [m1]: $_PW - KHONG lam gi."; exit 1; }
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
FT_TAIL=${FT_TAIL:-$([ "$FT_CRON" = 1 ] && echo 6000000 || echo 30000000)};   # byte cuoi MOI file (full.log.1 + full.log); du lieu khong phu dau cua so => canh bao (khong uoc luong "x phut")
FT_OVERLAP_S=${FT_OVERLAP_S:-900}; FT_WINDOW0_S=${FT_WINDOW0_S:-1800}; FT_REJ_WIN_S=${FT_REJ_WIN_S:-300}
 FT_TOL=${FT_TOL:-0.02}; FT_K=${FT_K:-0.0225}; FT_UMAX=${FT_UMAX:-0.6}
FT_GRACE_S=${FT_GRACE_S:-120}; FT_PENDING_MAX_S=${FT_PENDING_MAX_S:-604800}
FT_STATE=$FT_DIR/state.txt; FT_LAST=$FT_DIR/last_check
TS=$(TZ=Asia/Ho_Chi_Minh date +%Y%m%d_%H%M%S); NOW=$(date +%s)
# [OPS5_FIX MINOR B3] cua so: lan cham cuoi (ghi khi chay that) - FT_OVERLAP_S; chua co => min(mtime co micro, NOW - FT_WINDOW0_S)
LC=$(cat "$FT_LAST" 2>/dev/null | head -1)
if [[ "$LC" =~ ^[0-9]+$ ]]; then W0=$(( LC - FT_OVERLAP_S )); WSRC="lan cham cuoi - ${FT_OVERLAP_S}s"
else W0=$(( NOW - FT_WINDOW0_S )); WSRC="lan dau: NOW - ${FT_WINDOW0_S}s"
  FM=$(stat -c %Y "$GL_MON_FLAG" 2>/dev/null); [[ "$FM" =~ ^[0-9]+$ ]] && [ "$FM" -lt "$W0" ] && { W0=$FM; WSRC="lan dau: tu luc dat co micro"; }
fi
W0K=$(TZ=Asia/Ho_Chi_Minh date -d @"$W0" +%Y%m%d%H%M%S)
say "=== golive_first_trade_check TS=$TS DRY=$DRY C3_ACCOUNT=$C3_ACCOUNT$([ "$FT_CRON" = 1 ] && echo ' cron') ==="
ST=$(gl_state242) && echo "$ST" | grep -qx END_STATE && ! echo "$ST" | grep -q '^ERR=' || { say "DUNG: doc trang thai 242 loi (ssh?) - thu lai luot sau"; exit 1; }
CAP=$(sv ENV_C3_CAPITAL); JMD5=$(sv JAR_MD5)
[[ "$CAP" =~ ^[0-9]+(\.[0-9]+)?$ ]] && awk -v c="$CAP" 'BEGIN{exit !(c>0)}' || { say "DUNG: C3_CAPITAL process khong hop le ('$CAP')"; exit 1; }
say "process pid=$(sv PID) adapter=$(sv ENV_LIVE_ADAPTER) C3_CAPITAL=$CAP jar=$JMD5"
LOGR=$(s242in "bash -s -- $A $FT_TAIL $W0K" <<'EOR'
A=$1; TB=$2; WK=$3; cd "$A" || { echo "ERR=cd"; echo END_FT; exit 0; }
{ nice -n 19 tail -c "$TB" logs/full.log.1 2>/dev/null; nice -n 19 tail -c "$TB" logs/full.log 2>/dev/null; } | awk -v wk="$WK" '
  function key() { split($1, a, "/"); split($2, b, "[:.]"); return a[3] a[2] a[1] b[1] b[2] b[3] }
  $1 ~ /^[0-9][0-9]\/[0-9][0-9]\/[0-9][0-9][0-9][0-9]$/ { if (fk == "") fk = key() }
  /MainClass: com\.binance\.chuyennd\.trading\.BinanceOrderTradingManager/ { mc = $1 " " $2; if (key() >= wk) nj++ }
  /\[C3-LIVE\] SUBMIT / { if (key() >= wk) { k++; s[k] = $0 } else old++; next }
  /\[C3-LIVE[A-Z-]*\]/ && (/ REJECT / || /huy giu cho/ || /tu choi cid=/ || /=> KHONG gui/ || /status=(REJECTED|EXPIRED)/) {
    if (key() < wk) next; c = "-"; y = "-"
    if (match($0, /c3-[A-Za-z0-9_.-]+/)) c = substr($0, RSTART, RLENGTH)
    if (match($0, / [A-Z0-9][A-Z0-9]*USDT[A-Z]* /)) y = substr($0, RSTART + 1, RLENGTH - 2)
    r++; rj[r] = key() "|" c "|" y }
  END { print "JVM_START=" mc; print "JVM_IN_WIN=" nj + 0; print "FIRST_K=" fk; print "OLD_N=" old + 0
        for (i = 1; i <= k; i++) print "S=" s[i]; for (i = 1; i <= r; i++) print "R=" rj[i] }'
echo END_FT
EOR
) || LOGR="ERR=ssh"
echo "$LOGR" | grep -qx END_FT && ! echo "$LOGR" | grep -q '^ERR=' || { say "DUNG: doc log 242 loi ($(echo "$LOGR" | grep '^ERR=' | head -1)) - thu lai luot sau"; exit 1; }
JVS=$(echo "$LOGR" | sed -n 's/^JVM_START=//p' | head -1)
FK=$(echo "$LOGR" | sed -n 's/^FIRST_K=//p' | head -1)
say "cua so cham: tu $(TZ=Asia/Ho_Chi_Minh date -d @"$W0" '+%d/%m %H:%M:%S') ($WSRC); JVM hien tai bat dau: ${JVS:-?}; so lan khoi dong JVM trong cua so: $(echo "$LOGR" | sed -n 's/^JVM_IN_WIN=//p'); dong SUBMIT trong cua so: $(echo "$LOGR" | grep -c '^S=') (truoc cua so bo qua: $(echo "$LOGR" | sed -n 's/^OLD_N=//p')); dong REJECT/huy: $(echo "$LOGR" | grep -c '^R=')"
WCOV=""; [ -n "$FK" ] && [ "$FK" \> "$W0K" ] && { WCOV="du lieu log doc duoc bat dau $FK > dau cua so $W0K (full.log.1 + full.log, FT_TAIL=$FT_TAIL) - CO THE SOT SUBMIT"; say "!! CANH BAO $WCOV"; }
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
# [OPS5_FIX MINOR B3] cid CON CHO trong state (SUBMIT da ra khoi cua so log / log xoay) van duoc doi chieu san tiep
while IFS='|' read -r c t sy lv a b arm nw f la d; do
  [ -n "$c" ] && [ -z "${R_T[$c]:-}" ] || continue
  case "$b|$arm" in *CHO*|*NOALGO1*) ;; *) continue;; esac
  R_T[$c]=$t; R_S[$c]=$sy; R_L[$c]=$lv; R_A[$c]=$a; R_B[$c]=$b; R_ARM[$c]=$arm; R_N[$c]=$nw; R_F[$c]=$f; R_D[$c]=$d
done < <(cat "$FT_STATE" 2>/dev/null)
# [OPS5_FIX MINOR B4] REJECTED: khop cid; cid dong REJECT khong thuoc SUBMIT nao => cung symbol, 0..FT_REJ_WIN_S s sau SUBMIT
RCHG=""; declare -A RJC; RJL=""
while IFS='|' read -r rk rc ry; do
  [ -n "$rk" ] || continue
  if [ "$rc" != - ] && [ -n "${R_T[$rc]:-}" ]; then RJC[$rc]=1
  else rt=$(TZ=Asia/Ho_Chi_Minh date -d "${rk:0:4}-${rk:4:2}-${rk:6:2} ${rk:8:2}:${rk:10:2}:${rk:12:2}" +%s 2>/dev/null || echo 0); RJL="$RJL $rt:$ry"; fi
done < <(echo "$LOGR" | sed -n 's/^R=//p')
for c in "${!R_T[@]}"; do
  hit=${RJC[$c]:-0}
  if [ "$hit" = 0 ]; then for e in $RJL; do dt=$(( ${e%%:*} - ${R_T[$c]:-0} )); [ "${e#*:}" = "${R_S[$c]}" ] && [ "$dt" -ge 0 ] && [ "$dt" -le "$FT_REJ_WIN_S" ] && hit=1; done; fi
  [ "$hit" = 1 ] || continue
  case "${R_B[$c]}" in REJECTED|FAIL*) continue;; esac
  R_B[$c]=REJECTED; R_ARM[$c]=NA_REJECTED; RCHG="$RCHG $c"
done
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
CHG=$(echo $NEWA $CHG $RCHG | tr ' ' '\n' | sort -u | tr '\n' ' ')
# tong (moi cid trong state + moi): sizing_iv theo (a)
NA=0; NAF=0; NBF=0
NREJ=0
for c in $CIDS; do
  if [ "${R_B[$c]}" = REJECTED ] && [ "${R_A[$c]}" != FAIL ]; then NREJ=$((NREJ + 1)); continue; fi   # [B4] REJECTED khong phai bang chung DAT
  NA=$((NA + 1)); [ "${R_A[$c]}" = FAIL ] && NAF=$((NAF + 1)); case "${R_B[$c]}${R_ARM[$c]}" in *FAIL*) NBF=$((NBF + 1));; esac
done
SIV=DAT; [ "$NAF" -gt 0 ] && SIV=FAIL; [ "$NA" = 0 ] && SIV="KHONG_DO_DUOC (0 dong SUBMIT khong-REJECTED trong cua so; REJECTED $NREJ)"
DCS=DAT; [ "$NBF" -gt 0 ] && DCS=FAIL; [ "$APIOK" = 1 ] || DCS="${DCS}_(luot nay khong doc duoc san)"
row() { printf '| %s | %s | %s | %s | %s | %s | %s | %s |\n' "$1" "$(TZ=Asia/Ho_Chi_Minh date -d @"${R_T[$1]:-0}" '+%d/%m %H:%M:%S')" "${R_S[$1]}" "${R_L[$1]}" "${R_A[$1]}" "${R_B[$1]}/${R_ARM[$1]}" "${R_D[$1]}" "${R_C[$1]:--}"; }
for c in $CIDS; do say "  $(row "$c")"; done
say "sizing_iv: $SIV (dong SUBMIT cham: $NA, lech: $NAF, REJECTED: $NREJ) | doi_chieu_san: $DCS (FAIL: $NBF) | moi/doi luot nay:${CHG:- 0}"
[ "$NAF" -gt 0 ] && say "phan_loai_FAIL (a): $PLS (phan quyet prereg GIU NGUYEN) | nguon C_eff: $CSRC"
if [ "$DRY" = 1 ]; then say "DRY=1: KHONG ghi state / bang chung / Telegram"; exit 0; fi
# ghi state (thay toan bo dong cua cac cid JVM nay, giu dong cu khac)
{ for c in $CIDS; do printf '%s|%s|%s|%s|%s|%s|%s|%s|%s|%s|%s\n' "$c" "${R_T[$c]}" "${R_S[$c]}" "${R_L[$c]}" "${R_A[$c]}" "${R_B[$c]}" "${R_ARM[$c]}" "${R_N[$c]}" "${R_F[$c]}" "$NOW" "${R_D[$c]}"; done
  grep -vF -f <(for c in $CIDS; do printf '%s|\n' "$c"; done) "$FT_STATE" 2>/dev/null || :; } > "$FT_STATE.tmp" && mv -f "$FT_STATE.tmp" "$FT_STATE" \
  && echo "$NOW" > "$FT_LAST"   # [B3] moc cua so luot sau (chi khi state ghi xong)
CHG=$(echo $CHG); [ -n "$CHG" ] || { say "khong co ket qua moi - khong ghi bang chung, khong Telegram"; exit 0; }
EVF=$FT_DIR/SIZING_IV_$TS.md
{ echo "# SIZING_IV $TS (golive_first_trade_check, ADD22 ?3 (iv))"
  echo "sizing_iv: $SIV"
  echo "doi_chieu_san: $DCS"
  echo "jar_md5: $JMD5"
  echo "c3_capital_process: $CAP | cong thuc: budget trong +-$(awk -v t="$FT_TOL" 'BEGIN{print t*100}')% cua $FT_K x C3_CAPITAL x (1 - U_before/$FT_UMAX); DCA => legIdx>=1"
  echo "cua_so: tu $(TZ=Asia/Ho_Chi_Minh date -d @"$W0" '+%F %T') +07 ($WSRC)${WCOV:+ | CANH BAO: $WCOV} | REJECTED (khong tinh DAT): $NREJ"
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
