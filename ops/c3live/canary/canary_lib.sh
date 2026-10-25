#!/usr/bin/env bash
# =============================================================================
# canary_lib.sh — ham dung chung cho script owner G-CANARY (ops/c3live/canary/*.sh). KHONG chay truc tiep (source).
# Chay tren ORACLE; moi lenh JVM canary chay tren 242 (ssh root), JVM RIENG (C3LiveCanary), thu muc run/canary/ — KHONG dung
# JVM bot (dry), KHONG restart gi. Jar canary = jar dang deploy tren 242 (target/binance-java-sdk-1.2.4.jar), md5 phai = pin.
# Bien de thu (Oracle, 242 GIA trong test_fake242.sh): SSH_242, SCP_242, RHOST, APP_DIR, PROC_PAT, JAVA_242, LOGDIR,
#   CANARY_JAR_MD5, CANARY_KEYS_FILE, CANARY_KEYS_OWNER, POLL_S, STEP_MAX_S, GATE_FILES, DRY_MIN_DAYS, TIME_WAIT_MAX_S.
# Luat: YES=1 moi ghi/gui lenh; time_ok (FORCE_TIME=1 chi khi MASTER bao); khong in key/secret; log ~/claude_master/canary/.
# =============================================================================
set -uo pipefail
CL_HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
SSH_242=${SSH_242:-"ssh -p 2222 -o BatchMode=yes -o ConnectTimeout=20 -o ServerAliveInterval=30 -o ServerAliveCountMax=6 -i /home/ubuntu/.ssh/id_rsa_chuyennd root@103.157.218.242"}
SCP_242=${SCP_242:-"scp -P 2222 -o BatchMode=yes -i /home/ubuntu/.ssh/id_rsa_chuyennd"}
RHOST=${RHOST-"root@103.157.218.242:"}
A=${APP_DIR:-/home/chuyennd/java/v_t_m}
PROC_PAT=${PROC_PAT:-BinanceOrderTradingManager}            # process bot (dry) — chi DOC env, khong cham
JAVA_242=${JAVA_242:-java}
CANARY_JAR_MD5=${CANARY_JAR_MD5:-e702cc2d85e2402e8f9c1cf841eef875}   # [V12 3] pin jar v12dry_3 (dung chung dry + canary)
KEYS_FILE=${CANARY_KEYS_FILE:-/root/.config/c3live/keys.env}
KEYS_OWNER=${CANARY_KEYS_OWNER:-root}
LOGDIR=${LOGDIR:-/home/ubuntu/claude_master/canary}
POLL_S=${POLL_S:-15}
STEP_MAX_S=${STEP_MAX_S:-7200}
GATE_FILES=${GATE_FILES:-"/home/ubuntu/claude_master/deploy/gates/GOLIVE_GATE_CODE_V12.ok /home/ubuntu/claude_master/deploy/gates/GOLIVE_GATE_PROMO_V11.ok"}
DRY_MIN_DAYS=${DRY_MIN_DAYS:-5}                               # MO-1: >= 5 ngay dry sach
TIME_WAIT_MAX_S=${TIME_WAIT_MAX_S:-3600}
YES=${YES:-0}
FORCE_TIME=${FORCE_TIME:-0}
CDIR=run/canary
MAIN=com.binance.chuyennd.c3live.canary.C3LiveCanary
MAIN_PAT='[c]om.binance.chuyennd.c3live.canary.C3LiveCanary'   # [c]: pgrep khong tu khop dong lenh shell chua mau
TS=$(TZ=Asia/Ho_Chi_Minh date +%Y%m%d_%H%M%S)
CL_LAST_RESULT=""
CL_LAST_OUT=""

say()  { echo "[$(TZ=Asia/Ho_Chi_Minh date '+%F %T')] $*"; }
die()  { say "DUNG: $*"; say "KET QUA: TU_CHOI"; [ -n "${CL_LOG:-}" ] && say "Log: $CL_LOG"; exit 2; }
ok()   { say "OK: $*"; }

# cl_init <ten>: mo log Oracle (tee) — log KHONG bao gio chua key (key chi doc bang read -s trong c3live_keys_install.sh)
cl_init() {
  mkdir -p "$LOGDIR" || { echo "khong tao duoc $LOGDIR"; exit 2; }
  CL_LOG=$LOGDIR/$1_${TS}.log
  exec > >(tee -a "$CL_LOG") 2>&1
  say "=== $1 TS=$TS APP_DIR=$A jar_pin=$CANARY_JAR_MD5 YES=$YES ==="
  # chan gia tri la trong bien di vao lenh ssh
  [[ "$A" =~ ^[A-Za-z0-9_./-]+$ ]] || die "APP_DIR la: $A"
  [[ "$KEYS_FILE" =~ ^[A-Za-z0-9_./-]+$ ]] || die "CANARY_KEYS_FILE la"
  [[ "$KEYS_OWNER" =~ ^[a-z_][a-z0-9_-]*$ ]] || die "CANARY_KEYS_OWNER la"
  [[ "$JAVA_242" =~ ^[A-Za-z0-9_./\ -]+$ ]] || die "JAVA_242 la"
  [[ "$CANARY_JAR_MD5" =~ ^[0-9a-f]{32}$ ]] || die "CANARY_JAR_MD5 chua pin"
}

need_yes() { [ "$YES" = 1 ] || die "can YES=1 (vd: YES=1 bash $0 ${*:-}) — script nay $1"; }

time_ok() {
  local H M
  H=$(TZ=Asia/Ho_Chi_Minh date +%-H); M=$(TZ=Asia/Ho_Chi_Minh date +%-M)
  [ "$M" -ge 10 ] && [ "$M" -le 44 ] || return 1          # chi phut :10-:44
  case "$H" in 7|19) return 1;; esac                       # 07:xx/19:xx
  if [ "$H" -eq 1 ] || [ "$H" -eq 13 ]; then [ "$M" -gt 20 ] || return 1; fi   # tranh 00:50-01:20, 12:50-13:20
  return 0
}
# cl_time_gate die|wait: ngoai khung gio => dung (die) hoac cho toi TIME_WAIT_MAX_S (wait, giua cac buoc)
cl_time_gate() {
  [ "$FORCE_TIME" = 1 ] && { say "FORCE_TIME=1: bo chot gio (chi khi MASTER bao)"; return 0; }
  time_ok && return 0
  [ "$1" = die ] && die "gio $(TZ=Asia/Ho_Chi_Minh date +%H:%M) (+07) khong hop le: chi phut :10-:44, tranh 07:xx, 19:xx, 00:50-01:20, 12:50-13:20"
  local t0; t0=$(date +%s)
  say "ngoai khung gio — cho (toi da ${TIME_WAIT_MAX_S}s)"
  while ! time_ok; do
    [ $(( $(date +%s) - t0 )) -ge "$TIME_WAIT_MAX_S" ] && return 1
    sleep 30
  done
  return 0
}

# cl_check_242 [dry]: (chi doc) jar md5 = pin; bot KHONG o LIVE_ADAPTER=live; khong co JVM canary khac.
#   dry: them dieu kien vao §2.3 — bot o adapter dry >= DRY_MIN_DAYS ngay, 0 [KILLSW] LATCH / 0 [C3-LIVE-ORDER] tu moc start.
cl_check_242() {
  local mode=${1:-} out
  out=$($SSH_242 "PP='$PROC_PAT' MAIN='$MAIN_PAT' bash -s -- $A" <<'EOF'
A=$1; cd "$A" 2>/dev/null || { echo "ERR=cd"; exit 0; }
echo "JAR=$(md5sum < target/binance-java-sdk-1.2.4.jar 2>/dev/null | cut -c1-32)"
P=$(pgrep -f "$PP" | head -1)
AD=""; [ -n "$P" ] && AD=$(tr '\0' '\n' < /proc/$P/environ 2>/dev/null | grep '^LIVE_ADAPTER=' | cut -d= -f2)
echo "BOT=${P:-none} ADAPTER=${AD:-none}"
echo "CANARY_JVM=$(pgrep -fc "$MAIN")"
ST=$(cat run/.v12_start_epoch 2>/dev/null); echo "START=${ST:-none}"
if [ -n "$ST" ]; then
  touch -d @"$ST" /tmp/.canary_mk_$$ 2>/dev/null
  L=0; O=0
  for f in $(find logs -maxdepth 1 -name 'full.log*' -newer /tmp/.canary_mk_$$ 2>/dev/null); do
    c=$(zgrep -a -c '\[KILLSW\] LATCH' "$f" 2>/dev/null); L=$((L + ${c:-0}))
    c=$(zgrep -a -c '\[C3-LIVE-ORDER\]' "$f" 2>/dev/null); O=$((O + ${c:-0}))
  done
  rm -f /tmp/.canary_mk_$$
  echo "LATCH=$L ORDER=$O"
fi
EOF
)
  echo "$out" | sed 's/^/   242: /'
  echo "$out" | grep -q '^ERR=' && die "khong vao duoc $A tren 242"
  [ "$(echo "$out" | sed -n 's/^JAR=//p')" = "$CANARY_JAR_MD5" ] || die "md5 jar tren 242 khac pin $CANARY_JAR_MD5 (jar chua audit) — khong chay"
  ok "jar 242 md5 = pin"
  echo "$out" | grep -q 'ADAPTER=live' && die "bot dang o LIVE_ADAPTER=live (runtime chinh giu tai khoan con) — canary TU CHOI"
  [ "$(echo "$out" | sed -n 's/^CANARY_JVM=//p')" = 0 ] || die "co JVM canary khac dang chay tren 242"
  ok "bot khong o adapter live; khong co JVM canary khac"
  if [ "$mode" = dry ]; then
    echo "$out" | grep -q 'ADAPTER=dry' || die "bot khong chay LIVE_ADAPTER=dry (dieu kien vao §2.3)"
    local st now; st=$(echo "$out" | sed -n 's/^START=//p'); now=$(date +%s)
    [[ "$st" =~ ^[0-9]+$ ]] || die "khong co run/.v12_start_epoch (moc start dry)"
    local days=$(( (now - st) / 86400 ))
    [ $((now - st)) -ge $((DRY_MIN_DAYS * 86400)) ] || die "dry moi chay ${days} ngay (< $DRY_MIN_DAYS — MO-1)"
    ok "dry chay ${days} ngay (>= $DRY_MIN_DAYS)"
    echo "$out" | grep -q '^LATCH=0 ORDER=0$' || die "log dry tu moc start co [KILLSW] LATCH / [C3-LIVE-ORDER] (§2.3) — MASTER xem"
    ok "log dry tu moc start: 0 [KILLSW] LATCH, 0 [C3-LIVE-ORDER]"
  fi
}

# cl_gates: file gate MASTER ky (Oracle) — §2.1 G-CODE, §2.2 G-PROMO
cl_gates() {
  local g
  for g in $GATE_FILES; do [ -s "$g" ] || die "thieu file gate MASTER: $g (§2)"; done
  ok "file gate MASTER co du: $GATE_FILES"
}

# cl_push_logback: dat logback-canary.xml vao run/canary/ tren 242
cl_push_logback() {
  $SSH_242 "mkdir -p $A/$CDIR" < /dev/null || die "khong tao duoc $A/$CDIR"
  $SCP_242 "$CL_HERE/logback-canary.xml" "${RHOST}$A/$CDIR/logback-canary.xml" || die "khong chep duoc logback-canary.xml"
}

# cl_run <env "K=V K=V" (da kiem)> <lenh C3LiveCanary...>: chay JVM canary tren 242 bang nohup+setsid (mat ssh KHONG giet JVM),
# poll ket qua moi POLL_S. Dat CL_LAST_RESULT (dong RESULT) + CL_LAST_OUT; tra ma thoat JVM (0 DAT/2 TU_CHOI/3 TRUOT/4 LOI/5 khong ro).
cl_run() {
  local envs=$1; shift
  local a id n=0 rc="" t0 got line
  for a in "$@" $envs; do [[ "$a" =~ ^[A-Za-z0-9_=.]+$ ]] || die "tham so la: $a"; done
  id="${TS}_$$_${RANDOM}"
  say "--> JVM canary: $* ${envs:+(env $envs)}"
  $SSH_242 "cd $A && mkdir -p $CDIR && ( nohup setsid env CANARY_DIR=$CDIR LIVE_C3_KEYS_FILE=$KEYS_FILE LIVE_C3_KEYS_OWNER=$KEYS_OWNER $envs \
    $JAVA_242 -Xmx384m -Dlogback.configurationFile=$CDIR/logback-canary.xml -cp target/binance-java-sdk-1.2.4.jar $MAIN $* \
    > $CDIR/.jvm_$id.out 2>&1 < /dev/null; echo \$? > $CDIR/.jvm_$id.rc.tmp; mv -f $CDIR/.jvm_$id.rc.tmp $CDIR/.jvm_$id.rc ) > /dev/null 2>&1 < /dev/null &" < /dev/null \
    || die "khong khoi dong duoc JVM canary"
  CL_LAST_OUT=""; t0=$(date +%s)
  while :; do
    sleep "$POLL_S"
    # doc rc TRUOC roi moi dem dong (rc ghi sau khi JVM thoat => out da du); chi in dong da tron (wc -l)
    got=$($SSH_242 "cd $A && R=; [ -f $CDIR/.jvm_$id.rc ] && R=\$(cat $CDIR/.jvm_$id.rc); L=\$(wc -l < $CDIR/.jvm_$id.out 2>/dev/null || echo 0); [ \"\$L\" -gt $n ] && sed -n \"$((n + 1)),\${L}p\" $CDIR/.jvm_$id.out; echo __N=\$L; [ -n \"\$R\" ] && echo __RC=\$R; true" < /dev/null) \
      || { say "(poll ssh loi — thu lai)"; [ $(( $(date +%s) - t0 )) -ge "$STEP_MAX_S" ] && break; continue; }
    while IFS= read -r line; do
      case "$line" in
        __N=*) n=${line#__N=} ;;
        __RC=*) rc=${line#__RC=} ;;
        *) echo "   | $line"; CL_LAST_OUT+="$line"$'\n' ;;
      esac
    done <<< "$got"
    [ -n "$rc" ] && break
    [ $(( $(date +%s) - t0 )) -ge "$STEP_MAX_S" ] && break
  done
  CL_LAST_RESULT=$(printf '%s' "$CL_LAST_OUT" | grep '^RESULT ' | tail -1)
  if [ -z "$rc" ]; then
    say "KHONG RO ket qua sau ${STEP_MAX_S}s (JVM van chay? xem $A/$CDIR/.jvm_$id.out) — chay canary_flatten.sh neu can"
    return 5
  fi
  [[ "$rc" =~ ^[0-9]+$ ]] || rc=4
  [ -n "$CL_LAST_RESULT" ] || { say "JVM thoat rc=$rc nhung khong co dong RESULT"; [ "$rc" = 0 ] && rc=4; }
  return "$rc"
}

# cl_verdict <rc>: in DAT/TRUOT/TU_CHOI tu dong RESULT
cl_verdict() {
  case "$1" in
    0) echo "DAT" ;;
    2) echo "TU_CHOI" ;;
    *) echo "TRUOT" ;;
  esac
}

# cl_macro <K>: 1 buoc kich ban theo prereg §4 (K6 = OPEN + RESTART; K6B = OPEN + doi ten so + RESTART + dong tay)
cl_macro() {
  local k=$1 rc
  case "$k" in
    SETUP) cl_run "" setup; return $? ;;
    K1) cl_run "CANARY_INJECT_TIMEOUT=${CANARY_INJECT_TIMEOUT:-0}" step K1; return $? ;;
    K2|K3|K4|K5|K7|K7B|K8|K6_OPEN|K6_RESTART|K6B_OPEN|K6B_RESTART) cl_run "" step "$k"; return $? ;;
    K6)
      cl_run "" step K6_OPEN; rc=$?; [ $rc = 0 ] || return $rc
      cl_run "" step K6_RESTART; return $? ;;
    K6B)
      cl_run "" step K6B_OPEN; rc=$?; [ $rc = 0 ] || return $rc
      say "K6b: doi ten so canary (gia lap so mat) — $CDIR/c3live_book.json -> .k6b_$TS"
      $SSH_242 "cd $A && mv -f $CDIR/c3live_book.json $CDIR/c3live_book.json.k6b_$TS" < /dev/null || { say "khong doi ten duoc so"; return 3; }
      cl_run "" step K6B_RESTART; rc=$?
      say "K6b: dong tay (canary_flatten) theo prereg §4 K6b"
      cl_run "" flatten; local rf=$?
      [ $rc = 0 ] || return $rc
      return $rf ;;
    *) die "buoc la: $k (SETUP K1..K8 K6 K6B K7B K6_OPEN K6_RESTART K6B_OPEN K6B_RESTART)" ;;
  esac
}
