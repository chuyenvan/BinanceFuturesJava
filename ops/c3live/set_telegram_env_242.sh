#!/usr/bin/env bash
# =============================================================================
# set_telegram_env_242.sh - [SEC 2026-11-14] dua token bot Telegram HIEN TAI vao file env rieng tren 242 (chmod 600) cho cap jar
#   fin (collectData qf/fin-bin + v_t_m v1.2/fin-guard): jar KHONG con token hard-code, doc env TELEGRAM_BOT_TOKEN.
# Chay tren ORACLE (owner), 1 lenh:
#   bash ~/claude_master/deploy/set_telegram_env_242.sh          # ghi + kiem (KHONG in token; chi in sha8)
#   DRY=1 bash ~/claude_master/deploy/set_telegram_env_242.sh    # chi kiem nguon + 242 (khong ghi)
# Lam: doc token tu $SRC (Oracle, dong "tele-token:" hoac "TG_TOKEN=") -> kiem dinh dang + sha8 = EXPECT_SHA8 -> day qua STDIN ssh
#   (khong nam tren dong lenh) -> 242: $SECD/telegram.env (export TELEGRAM_BOT_TOKEN=..., root:root 600, thu muc 700, ghi nguyen tu)
#   -> them 1 dong source vao conf/env.sh cua collectData + v_t_m (backup env.sh.bak_tgenv_<TS>; da co => bo qua)
#   -> kiem: sha8 trong file + sha8 khi source tung env.sh (subshell) = EXPECT_SHA8, quyen 600.
# KHONG restart gi: process dang chay (jar cu, token hard-code) khong doi; env co hieu luc o lan start ke (deploy cap jar fin).
# Doi token (rotate qua BotFather): sua $SRC tren Oracle roi chay lai voi EXPECT_SHA8=<8 ky tu sha256 token moi>.
# [A1-M6 2026-11-14] da doc 242 (chi doc): collectData + v_t_m chay user ROOT (unit h242-ingest/h242-trading khong co User=,
#   ExecStart bin/daemon.sh start: daemon.sh `. $APP_CONF_DIR/env.sh` roi nohup bin/start.sh => bien export di vao JVM; tu-restart
#   Utils.reset chep nguyen env; watchdog dung daemon.sh start). Script KIEM lai truoc khi ghi: user process (hoac User= cua unit
#   neu process khong chay) phai DUY NHAT; file/thu muc chown cho user do (root => giu root:root); daemon.sh phai nap conf/env.sh.
#   Sau ghi: kiem bien co EXPORT toi process con (nhu daemon.sh -> start.sh). RUN_USER=<u> chi de test.
# Ma thoat: 0 OK | 1 dung (khong doi gi hoac da kiem FAIL - xem dong FAIL).
# =============================================================================
set -uo pipefail
SRC=${SRC:-/home/ubuntu/.config/health242/tg.env}
EXPECT_SHA8=${EXPECT_SHA8:-bdee1480}   # [WAVE1 B-13] token moi 11-14 (truoc 4f49bded da revoke)
SSH_242=${SSH_242:-"ssh -p 2222 -o BatchMode=yes -o ConnectTimeout=20 -i /home/ubuntu/.ssh/id_rsa_chuyennd root@103.157.218.242"}
SECD=${SECD:-/home/chuyennd/java/secrets}
APPS=${APPS:-"/home/chuyennd/java/collectData /home/chuyennd/java/v_t_m"}
DRY=${DRY:-0}
TS=$(TZ=Asia/Ho_Chi_Minh date +%Y%m%d_%H%M%S)
say() { echo "[$(TZ=Asia/Ho_Chi_Minh date '+%F %T')] $*"; }
die() { say "DUNG: $*"; exit 1; }

say "=== set_telegram_env_242 TS=$TS DRY=$DRY (nguon $SRC, ky vong sha8 $EXPECT_SHA8) ==="
[ -r "$SRC" ] || die "khong doc duoc $SRC"
TOK=$(sed -nE 's/^[[:space:]]*(export[[:space:]]+)?(TG_TOKEN=|tele-token:[[:space:]]*)//p' "$SRC" | head -1 | tr -d "\r\"' ")
[[ "$TOK" =~ ^[0-9]{8,10}:[A-Za-z0-9_-]{30,40}$ ]] || { TOK=""; die "token trong $SRC sai dinh dang"; }
S8=$(printf '%s' "$TOK" | sha256sum | cut -c1-8)
[ "$S8" = "$EXPECT_SHA8" ] || { TOK=""; die "sha8 token nguon = $S8 != $EXPECT_SHA8 (dat EXPECT_SHA8 neu da rotate)"; }
say "OK nguon: dinh dang hop le, sha8=$S8"

# 242 CHI DOC: thu muc app + env.sh co
PRE=$($SSH_242 "bash -s -- $SECD ${RUN_USER:--} $APPS" 2>&1 <<'EOF'
SECD=$1; RU=$2; shift 2
US=""
for a in "$@"; do
  [ -f "$a/conf/env.sh" ] && echo "OK env.sh $a" || echo "FAIL khong_co $a/conf/env.sh"
  grep -q 'secrets/telegram.env' "$a/conf/env.sh" 2>/dev/null && echo "INFO da_co_dong_source $a" || echo "INFO chua_co_dong_source $a"
  # [A1-M6] daemon.sh (ExecStart systemd + watchdog) phai nap conf/env.sh, neu khong dong source vo tac dung
  [ "$(grep -c 'APP_CONF_DIR/env.sh\|conf/env.sh' "$a/bin/daemon.sh" 2>/dev/null)" -ge 1 ] && echo "OK daemon.sh_nap_env.sh $a" || echo "FAIL daemon.sh_khong_nap_env.sh $a"
  case "$a" in *collectData*) MC=websocket.BinanceDataIngestor; UN=h242-ingest;; *v_t_m*) MC=trading.BinanceOrderTradingManager; UN=h242-trading;; *) MC=; UN=;; esac
  P=$( [ -n "$MC" ] && pgrep -f "$MC" | head -1)
  if [ -n "$P" ]; then U=$(ps -o user= -p "$P" | tr -d ' '); echo "INFO user_process=$U $a"
  else U=$( [ -n "$UN" ] && systemctl show -p User --value "$UN" 2>/dev/null); U=${U:-root}; echo "INFO process_khong_chay $a => user unit=$U"; fi
  US="$US $U"
done
[ "$RU" != - ] && US=" $RU"
UU=$(echo $US | tr ' ' '\n' | sort -u)
[ "$(echo "$UU" | wc -l)" = 1 ] && echo "RUN_USER=$UU" || echo "FAIL user_process_khac_nhau: $(echo $UU) (file 600 chi 1 owner)"
id -u "$UU" >/dev/null 2>&1 || echo "FAIL user_khong_ton_tai=$UU"
[ -f "$SECD/telegram.env" ] && echo "INFO da_co_file $SECD/telegram.env quyen=$(stat -c %a "$SECD/telegram.env")" || echo "INFO chua_co_file $SECD/telegram.env"
echo END_PRE
EOF
)
echo "$PRE" | sed 's/^/   /'
echo "$PRE" | grep -qx END_PRE || { TOK=""; die "ssh 242 loi"; }
echo "$PRE" | grep -q '^FAIL' && { TOK=""; die "242 thieu env.sh"; }
RUN_U=$(echo "$PRE" | sed -n 's/^RUN_USER=//p' | head -1)
[ -n "$RUN_U" ] || { TOK=""; die "khong xac dinh duoc user chay process"; }
say "OK user chay java = $RUN_U (file token se thuoc $RUN_U, quyen 600)"
if [ "$DRY" = 1 ]; then TOK=""; say "DRY=1: khong ghi gi. (DRY PASS)"; exit 0; fi

say "--- ghi $SECD/telegram.env (token qua STDIN, khong in)"
printf '%s\n' "$TOK" | $SSH_242 "umask 077; mkdir -p $SECD && chmod 700 $SECD && IFS= read -r T && [ -n \"\$T\" ] && printf 'export TELEGRAM_BOT_TOKEN=%s\n' \"\$T\" > $SECD/.telegram.env.tmp_$TS && chmod 600 $SECD/.telegram.env.tmp_$TS && { [ \"\$(id -un)\" = '$RUN_U' ] || chown '$RUN_U' $SECD $SECD/.telegram.env.tmp_$TS; } && mv -f $SECD/.telegram.env.tmp_$TS $SECD/telegram.env && echo OK_GHI" \
  | grep -qx OK_GHI || { TOK=""; die "ghi file token tren 242 LOI"; }
TOK=""
say "--- them dong source vao env.sh + kiem"
POST=$($SSH_242 "bash -s -- $SECD $TS $EXPECT_SHA8 $RUN_U $APPS" 2>&1 <<'EOF'
SECD=$1; TS=$2; E8=$3; RU=$4; shift 4
F=$SECD/telegram.env
LINE="[ -r $F ] && . $F   # [SEC 2026-11-14] TELEGRAM_BOT_TOKEN (jar fin doc env; file chmod 600)"
for a in "$@"; do
  e=$a/conf/env.sh
  if grep -q 'secrets/telegram.env' "$e"; then echo "OK da_co_dong_source $a"
  else cp -p "$e" "$e.bak_tgenv_$TS" && { printf '\n%s\n' "$LINE" >> "$e"; } && echo "OK them_dong_source $a (backup env.sh.bak_tgenv_$TS)" || echo "FAIL them_dong $a"; fi
  s=$(cd "$a" && bash -c '. conf/env.sh >/dev/null 2>&1; printf %s "$TELEGRAM_BOT_TOKEN"' | sha256sum | cut -c1-8)
  [ "$s" = "$E8" ] && echo "OK source_env.sh_sha8=$s $a" || echo "FAIL source_env.sh_sha8=$s $a"
  # [A1-M6] nhu daemon.sh -> nohup start.sh -> java: bien phai EXPORT toi process con
  c=$(cd "$a" && bash -c '. conf/env.sh >/dev/null 2>&1; bash -c "printf %s \"\$TELEGRAM_BOT_TOKEN\""' | sha256sum | cut -c1-8)
  [ "$c" = "$E8" ] && echo "OK export_toi_process_con_sha8=$c $a" || echo "FAIL export_toi_process_con_sha8=$c $a"
done
s=$(bash -c ". $F >/dev/null 2>&1; printf %s \"\$TELEGRAM_BOT_TOKEN\"" | sha256sum | cut -c1-8)
[ "$s" = "$E8" ] && echo "OK file_sha8=$s" || echo "FAIL file_sha8=$s"
[ "$(stat -c %a "$F")" = 600 ] && [ "$(stat -c %U "$F")" = "$RU" ] && echo "OK quyen_600_$RU" || echo "FAIL quyen=$(stat -c %a:%U "$F") (can 600:$RU)"
[ "$(stat -c %a "$SECD")" = 700 ] && [ "$(stat -c %U "$SECD")" = "$RU" ] && echo "OK thu_muc_700_$RU" || echo "FAIL thu_muc_quyen=$(stat -c %a:%U "$SECD") (can 700:$RU)"
echo END_POST
EOF
)
echo "$POST" | sed 's/^/   /'
echo "$POST" | grep -qx END_POST || die "ssh kiem sau ghi loi"
echo "$POST" | grep -q '^FAIL' && die "kiem sau ghi co FAIL"
say "=== XONG: 242 co TELEGRAM_BOT_TOKEN (sha8 $EXPECT_SHA8) cho collectData + v_t_m qua env.sh. Khong restart gi."
exit 0
