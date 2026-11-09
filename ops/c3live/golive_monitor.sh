#!/usr/bin/env bash
# =============================================================================
# golive_monitor.sh — [V12 R4o / ADD4] 1 LENH: trang thai tong c3_live tren 242 (khong restart).
#   bash ~/claude_master/v12/c3live/ops/c3live/golive_monitor.sh            # tay; C3_ACCOUNT=SUB mac dinh (MAIN = chi doc nhu R4o)
#   DRY=1 ...            (SUB: chi doc + in, KHONG dat co, KHONG ghi dinh / bo dem)
#   SUB_PEAK_RESET=1 ... dat lai dinh tmb = tmb hien tai (sau khi owner NAP/RUT co chu dich)
#   [A1 ADD4 C-1] CRON (install_cron_golive_monitor.sh, */2 phut, flock -n rieng): MONITOR_CRON=1 => KHONG co co $GL_MON_FLAG
#   (micro_on/pilot_on tao, live_off MODE=dry xoa) => thoat NGAY, 0 ssh / 0 call. Co co => C3_ACCOUNT + KEYS_FILE lay tu co; log
#   ~/claude_master/deploy/golive_monitor_cron.log (xoay > 20 MB); doc 4 MB log 242 / luot; Telegram KHAN lap lai toi da 1 lan / 30'.
# In: process/jar/env (adapter, C3_CAPITAL, push), PUSH (env + run/KILL_SWITCH), latch + dinh kill-switch, equity c3 / HOURLY,
#   so c3 (cum, da arm, stop c3s-), lenh c3 1 h qua, LEGACY, user stream, RAM/dia/RSS, weight/429/418/ban, KHAN/ERROR 1 h qua,
#   PAUSE watchdog, cron exinfo. Ket thuc bang dong TOM TAT.
# [ADD4] SUB doc them san tk con CHI DOC (gl_api242 mon: v3/account 5 + v3/positionRisk 5 + openOrders 40 + openAlgoOrders 40 = 90 weight IP):
#   §4 vi the (vuot qty c3 trong so; leg dang khop => POS_PENDING) / lenh / algo cid KHONG c3-|c3x-|c3s- => KHAN + dat run/KILL_SWITCH
#      (co san: chan MO MOI; vi the c3 van duoc quan ly), KHONG tu dong vi the. Owner/MASTER xu ly; go co: MODE=undrain golive_live_off.sh.
#   §5 DD totalMarginBalance tk con (USDT, gom BFUSD) so voi dinh $SUB_PEAK_FILE (Oracle, theo key_sha8) <= -SUB_DD_LIMIT (0.40 = A40/C6)
#      => KHAN + run/KILL_SWITCH. Owner NAP/RUT co chu dich: SUB_PEAK_RESET=1 bash golive_monitor.sh (dinh = tmb hien tai).
#   key doc san co sha8 = key tk chinh => KHAN. [A1 MIN-1] doc 242/san loi: le => CANH BAO; >= MON_FAIL_MAX (5) luot LIEN TIEP => KHAN +
#      KILL_SWITCH (neu ssh con dat duoc) + Telegram.
#   Lop CHINH (jar r4t, khong doi): KillSwitchEngine A40/C6 (FLATTEN) tren C3MainEquity = C3_CAPITAL + PnL c3 (so) — day la lop ops THU HAI.
#   Ma thoat: 0 | 2 KHAN.
# =============================================================================
set -uo pipefail
MON_CRON=${MONITOR_CRON:-0}
GL_MON_FLAG=${GL_MON_FLAG:-${LOGDIR:-/home/ubuntu/claude_master/deploy}/golive_monitor.on}
if [ "$MON_CRON" = 1 ]; then
  [ -f "$GL_MON_FLAG" ] || exit 0   # khong co micro/pilot dang bat => thoat ngay, 0 call
  FA=$(sed -n 's/^C3_ACCOUNT=//p' "$GL_MON_FLAG" | head -1); FK=$(sed -n 's/^KEYS_FILE=//p' "$GL_MON_FLAG" | head -1)
  case "$FA" in SUB|MAIN) export C3_ACCOUNT=$FA ;; esac
  [ -n "$FK" ] && export KEYS_FILE=$FK
  CL=${MON_CRON_LOG:-${LOGDIR:-/home/ubuntu/claude_master/deploy}/golive_monitor_cron.log}
  mkdir -p "$(dirname "$CL")"
  [ "$(stat -c %s "$CL" 2>/dev/null || echo 0)" -gt 20000000 ] && mv -f "$CL" "$CL.1"
  exec >> "$CL" 2>&1
  MON_TAIL=${MON_TAIL:-4000000}
fi
MON_TAIL=${MON_TAIL:-15000000}
. "$(cd "$(dirname "$0")" && pwd)/golive_lib.sh"
TS=$(TZ=Asia/Ho_Chi_Minh date +%Y%m%d_%H%M%S)
say "=== golive_monitor (C3_ACCOUNT=$C3_ACCOUNT$([ "$MON_CRON" = 1 ] && echo ' cron')) ==="
READOK=1
ST=$(gl_state242) && echo "$ST" | grep -qx END_STATE && ! echo "$ST" | grep -q '^ERR=' || READOK=0
if [ "$READOK" = 0 ]; then
  [ "$C3_ACCOUNT" = SUB ] || die "doc trang thai 242 loi (ssh?)"
  say "!! CANH BAO: doc trang thai 242 loi (ssh?)"; ST=""
fi
OUT=$(s242in "PP='$PROC_PAT' bash -s -- $A $MON_TAIL" <<'EOF'
A=$1; TB=$2; cd "$A" || exit 0; L=logs/full.log
P=$(pgrep -f "$PP" | head -1)
H=$(tail -c $TB $L 2>/dev/null)
last() { echo "$H" | grep -a "$1" | tail -1 | cut -c1-${2:-260}; }
cnt1h() { local s; s=$(TZ=Asia/Ho_Chi_Minh date -d '-1 hour' '+%d/%m/%Y %H:%M'); echo "$H" | awk -v s="$s" '{t=$1" "substr($2,1,5); split(t,a,/[\/ :]/); k=a[3]a[2]a[1]a[4]a[5]; split(s,b,/[\/ :]/); ks=b[3]b[2]b[1]b[4]b[5]; if (k>=ks) print}' | grep -ac "$1"; }
echo "== process pid=$P lstart=$(ps -o lstart= -p $P 2>/dev/null) rss_mb=$(( $(ps -o rss= -p $P 2>/dev/null || echo 0) / 1024 )) threads=$(ls /proc/$P/task 2>/dev/null | wc -l)"
PL=$(echo "$H" | grep -a 'PUSH doi trang thai\|PUSH=ON\|PUSH=OFF' | tail -1)
echo "== PUSH (log): $(echo "$PL" | cut -c1-23) $(echo "$PL" | grep -oE 'PUSH( doi trang thai ->)?[= ]*(ON|OFF)' | tail -1)"
echo "== KILL_SWITCH file: $([ -e run/KILL_SWITCH ] && echo "CO ($(head -c 80 run/KILL_SWITCH))" || echo khong)"
echo "== latch: $(head -c 300 run/killsw_latch.json 2>/dev/null || echo chua_co)"
echo "== dinh A40/C6: $(cat run/c3live_killsw_peak 2>/dev/null || echo chua_co)"
echo "== equity: $(last '\[C3-LIVE-EQ\]' 220)"
echo "== HOURLY: $(last '\[C3-LIVE\] HOURLY' 400)"
echo "== recon: $(last 'C3-LIVE-RECON\] HOURLY' 220)"
B=run/c3live_book.json
[ -f $B ] && echo "== so c3: cum=$(grep -o '"symbol":"' $B | wc -l) da_arm=$(grep -o '"armed":true' $B | wc -l) stop_c3s=$(grep -o '"stop_cid":"' $B | wc -l) sua=$(stat -c %y $B | cut -c1-19)" || echo "== so c3: chua co"
echo "== lenh c3 1h: EXEC=$(cnt1h '\[C3-LIVE-EXEC\]') FILL=$(cnt1h 'C3-LIVE-EXEC\] FILL') TU_CHOI=$(cnt1h 'TU CHOI')"
LG=$(echo "$H" | grep -a '\[LEGACY\] managed' | tail -1); LS=$(echo "$H" | grep -a 'LEGACY tren tai khoan chinh:' | tail -1)
echo "== LEGACY: $(echo "$LG" | cut -c1-23) $(echo "$LG" | grep -oE 'managed [0-9]+') | san(c3 scope): $(echo "$LS" | cut -c1-23) $(echo "$LS" | grep -oE 'chinh: [0-9]+ vi the')"
echo "== stream: $(last 'C3-LIVE-STREAM\]' 200)"
echo "== rate 1h: 429=$(cnt1h 'HTTP 429\|http=429\| 429 ') 418=$(cnt1h 'HTTP 418\|http=418\| 418 ') ban=$(cnt1h '"code":-1003\|code=-1003\|IP banned\|banned until') | $(last 'USED-WEIGHT\|weight=' 200)"
echo "== KHAN 1h=$(cnt1h 'KHAN') ERROR 1h=$(cnt1h ' ERROR ') | KHAN cuoi: $(last 'KHAN' 200)"
echo "== exinfo: tuoi=$(( $(date +%s) - $(stat -c %Y run/c3live_exchangeInfo.json 2>/dev/null || echo 0) ))s $(tr '\n' ' ' < run/c3live_exinfo_refresh.state 2>/dev/null | cut -c1-80)"
echo "== may: MemAvailable=$(awk '/MemAvailable/{print int($2/1024)}' /proc/meminfo)MB swap_free=$(awk '/SwapFree/{print int($2/1024)}' /proc/meminfo)MB dia=$(df -h . | awk 'NR==2{print $4" trong ("$5")"}')"
EOF
) || OUT="(ssh 242 loi)"
echo "$OUT"
echo "== PAUSE watchdog: $(sv PAUSE)  canary/soak=$(sv CANARY_SOAK)"
PUSH=OFF; [ "$(sv ENV_LIVE_ADAPTER)" = live ] && [ "$(sv ENV_SHADOW_NO_PUSH)" = false ] && [ "$(sv ENV_LIVE_ENTRY_ENABLED)" = true ] && [ "$(sv KILLSW_FILE)" = 0 ] && PUSH=ON
RC=0; SUBSUM=""
if [ "$C3_ACCOUNT" = SUB ]; then
  # ---------------------------------------------------------------- [ADD4 §4/§5 + A1 MIN-1] tai khoan con: doc san CHI DOC
  KP=$(sv ENV_LIVE_C3_KEYS_FILE)
  [ "$(sv ENV_LIVE_ADAPTER)" != live ] || [ "$KP" = "$KEYS_FILE" ] || say "!! CANH BAO: bot live dung LIVE_C3_KEYS_FILE='$KP' KHAC $KEYS_FILE (C3_ACCOUNT=$C3_ACCOUNT) — so lieu duoi day la cua $KEYS_FILE"
  API=$(gl_api242 mon) || API="ERR=ssh_api"
  echo "$API" | grep -E '^(KEY_SHA8|TMB|AVAIL|BAL|MARGIN_ASSETS|BFUSD_|POS_TOTAL|POS_NONC3|POS_PENDING|POS_C3_MISMATCH|ORD_|ALGO_|C3_|W_|API_OK|ERR)' | sed 's/^/== tk con: /'
  KH=""; UNK=""
  [ "$READOK" = 1 ] || UNK="$UNK trang_thai_242"
  if echo "$API" | grep -qx END_API; then
    for k in POS_NONC3 ORD_NONC3 ALGO_NONC3; do
      n=$(av $k | awk '{print $1}')
      case "$n" in ''|*[!0-9]*) UNK="$UNK $k";; 0) ;; *) KH="$KH $k=$(av $k | tr ' ' ':')";; esac
    done
  else UNK="$UNK doc_san"; fi
  KS8=$(av KEY_SHA8)
  [ -n "$KS8" ] && [ "$KS8" = "$MAIN_KEY_SHA8" ] && KH="$KH key_doc_san_LA_KEY_TK_CHINH($KS8)"
  # §5 DD totalMarginBalance (USDT, gom gia tri margin BFUSD) so voi dinh luu tren Oracle (theo key_sha8)
  TMB=$(av TMB); DD=""
  if [[ "$TMB" =~ ^[0-9]+(\.[0-9]+)?$ ]] && awk -v e="$TMB" 'BEGIN{exit !(e>0)}'; then
    PK=""; PS=""
    [ -r "$SUB_PEAK_FILE" ] && { PK=$(sed -n 's/^peak=//p' "$SUB_PEAK_FILE" | head -1); PS=$(sed -n 's/^key_sha8=//p' "$SUB_PEAK_FILE" | head -1); }
    NEWPK=""
    if [ "${SUB_PEAK_RESET:-0}" = 1 ]; then NEWPK=$TMB; say "dinh tmb DAT LAI = $TMB (SUB_PEAK_RESET=1)"
    elif ! [[ "$PK" =~ ^[0-9]+(\.[0-9]+)?$ ]] || [ "$PS" != "$KS8" ]; then NEWPK=$TMB; say "dinh tmb khoi tao = $TMB (chua co dinh / key khac)"
    elif awk -v e="$TMB" -v p="$PK" 'BEGIN{exit !(e>p)}'; then NEWPK=$TMB; fi
    if [ -n "$NEWPK" ]; then
      PK=$NEWPK
      if [ "$DRY" = 1 ]; then say "DRY=1: KHONG ghi dinh $SUB_PEAK_FILE"
      else mkdir -p "$(dirname "$SUB_PEAK_FILE")"; printf 'peak=%s\nkey_sha8=%s\nts=%s\n' "$PK" "$KS8" "$TS" > "$SUB_PEAK_FILE.tmp" && mv -f "$SUB_PEAK_FILE.tmp" "$SUB_PEAK_FILE"; fi
    fi
    DD=$(awk -v e="$TMB" -v p="$PK" 'BEGIN{printf "%.4f", e/p-1}')
    say "== DD tk con (ops, tmb): tmb=$TMB dinh=$PK dd=$DD nguong=-$SUB_DD_LIMIT (A40/C6). Lop chinh trong jar: KillSwitchEngine tren C3MainEquity (so c3)"
    awk -v d="$DD" -v l="$SUB_DD_LIMIT" 'BEGIN{exit !(d <= -l)}' && KH="$KH DD_tmb=${DD}_vuot_-${SUB_DD_LIMIT}_(A40/C6)"
  else
    UNK="$UNK TMB"
  fi
  # [A1 MIN-1] bo dem luot doc loi LIEN TIEP (Oracle)
  NF=$(sed -n 's/^n=//p' "$SUB_FAIL_FILE" 2>/dev/null | head -1); [[ "$NF" =~ ^[0-9]+$ ]] || NF=0
  if [ -n "$UNK" ]; then
    NF=$((NF + 1))
    say "!! CANH BAO: doc 242/san tk con KHONG tron ven ($UNK) — luot loi lien tiep $NF/$MON_FAIL_MAX"
    [ "$NF" -ge "$MON_FAIL_MAX" ] && KH="$KH doc_san_loi_${NF}_luot_lien_tiep"
  else NF=0; fi
  [ "$DRY" = 1 ] || { mkdir -p "$(dirname "$SUB_FAIL_FILE")"; printf 'n=%s\nts=%s\n' "$NF" "$TS" > "$SUB_FAIL_FILE"; }
  if [ -n "$KH" ]; then
    RC=2
    KT=$(echo "$KH" | tr -cd 'A-Za-z0-9_=:.,+ -' | sed 's/^ *//' | tr ' ' '_' | cut -c1-160)
    say "KHAN (ADD4 tk con):$KH — CHAN mo moi (run/KILL_SWITCH), KHONG tu dong vi the; owner/MASTER xu ly"
    if [ "$DRY" = 1 ]; then say "DRY=1: KHONG dat run/KILL_SWITCH"
    elif s242 "cd $A && { [ -e run/KILL_SWITCH ] || echo 'golive_monitor $TS KHAN $KT' > run/KILL_SWITCH; } && [ -e run/KILL_SWITCH ]"; then
      say "run/KILL_SWITCH DANG DAT (dung mo moi; vi the c3 van duoc quan ly). Go sau khi xu ly: MODE=undrain golive_live_off.sh"
    else say "!! KHONG dat / xac nhan duoc run/KILL_SWITCH (ssh?) — owner dat tay: MODE=drain golive_live_off.sh"; fi
    # cron: Telegram cung noi dung toi da 1 lan / 30'; chay tay: luon gui
    SIG=$(echo "$KH" | sed 's/DD_tmb=[^ ]*/DD/; s/doc_san_loi_[0-9]*_/doc_san_loi_/' | md5sum | cut -c1-12); NOW=$(date +%s)
    KF2=$LOGDIR/c3sub_monitor_khan.txt; OS=$(sed -n 's/^sig=//p' "$KF2" 2>/dev/null | head -1); OT=$(sed -n 's/^t=//p' "$KF2" 2>/dev/null | head -1)
    if [ "$MON_CRON" != 1 ] || [ "$OS" != "$SIG" ] || [ $(( NOW - ${OT:-0} )) -ge 1800 ]; then
      tg "[golive] KHAN tk con TS=$TS:$KH => run/KILL_SWITCH (chan mo moi), KHONG tu dong vi the. Kiem golive_monitor.sh"
      [ "$DRY" = 1 ] || printf 'sig=%s\nt=%s\n' "$SIG" "$NOW" > "$KF2"
    else say "(Telegram KHAN nay da gui < 30' truoc — khong gui lai)"; fi
    PUSH=OFF
  fi
  SUBSUM=" tk=SUB key=${KS8:-?} tmb=${TMB:-?} dd=${DD:-?} khan=$([ -n "$KH" ] && echo KHAN || { [ -n "$UNK" ] && echo "?(loi $NF/$MON_FAIL_MAX)" || echo 0; })"
fi
say "TOM TAT: adapter=$(sv ENV_LIVE_ADAPTER) C3_CAPITAL=$(sv ENV_C3_CAPITAL) push=$PUSH latch=$(sv LATCH) so_c3=$(sv BOOK_CUM)cum LEGACY=$(sv LEGACY_N) mem=$(sv MEM)MB jar=$(sv JAR_MD5 | cut -c1-8) pause=$(sv PAUSE | cut -c1)$SUBSUM"
exit $RC
