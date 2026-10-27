#!/usr/bin/env bash
# =============================================================================
# canary_lib.sh — ham dung chung cho script owner G-CANARY (ops/c3live/canary/*.sh). KHONG chay truc tiep (source).
# Chay tren ORACLE; moi lenh JVM canary chay tren 242 (ssh root), JVM RIENG (C3LiveCanary), thu muc run/canary/ — KHONG dung
# JVM bot, KHONG restart gi. JVM luon chay bang `env -i` (khong LIVE_PROFILE/TRADING_PROFILE/LIVE_TS_MKT_EXT => khong Aerospike).
# 2 che do (CANARY_MODE):
#   standard (mac dinh, G-CANARY sau deploy dry): APP_DIR = v_t_m, jar = target/binance-java-sdk-1.2.4.jar dang deploy.
#   early (prereg §ADD-1, canary_early_*.sh dat): thu muc RIENG CANARY_HOME (/home/chuyennd/java/c3canary), jar rieng
#     binance-java-sdk-1.2.4.jar (copy tu Oracle), v_t_m CHI DOC (md5 jar/env/start, PID, env process) va phai KHONG DOI.
# Bien de thu (Oracle, 242 GIA trong test_fake242.sh): SSH_242, SCP_242, RHOST, APP_DIR, CANARY_HOME, VTM_DIR, PROC_PAT, JAVA_242,
#   LOGDIR, CANARY_JAR, CANARY_JAR_MD5, CANARY_KEYS_FILE, CANARY_KEYS_OWNER, POLL_S, STEP_MAX_S, GATE_FILES, DRY_MIN_DAYS,
#   TIME_WAIT_MAX_S, MEMINFO_FILE.
# Luat: YES=1 moi ghi/gui lenh; time_ok (FORCE_TIME=1 chi khi MASTER bao); khong in key/secret; log ~/claude_master/canary/.
# =============================================================================
set -uo pipefail
CL_HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
SSH_242=${SSH_242:-"ssh -p 2222 -o BatchMode=yes -o ConnectTimeout=20 -o ServerAliveInterval=30 -o ServerAliveCountMax=6 -i /home/ubuntu/.ssh/id_rsa_chuyennd root@103.157.218.242"}
SCP_242=${SCP_242:-"scp -P 2222 -o BatchMode=yes -i /home/ubuntu/.ssh/id_rsa_chuyennd"}
RHOST=${RHOST-"root@103.157.218.242:"}
CANARY_MODE=${CANARY_MODE:-standard}
if [ "$CANARY_MODE" = early ]; then
  VTM=${VTM_DIR:-/home/chuyennd/java/v_t_m}                  # app bot shadow v1.1 — canary KHONG ghi, chi doc md5/PID/env
  A=${CANARY_HOME:-/home/chuyennd/java/c3canary}             # §ADD-1: thu muc + jar + run/ + lock RIENG
  CJAR=binance-java-sdk-1.2.4.jar
  GATE_FILES=${GATE_FILES:-"/home/ubuntu/claude_master/deploy/gates/GOLIVE_GATE_CODE_V12.ok"}   # MASTER tao sau khi A1 DAT
else
  A=${APP_DIR:-/home/chuyennd/java/v_t_m}
  VTM=${VTM_DIR:-$A}                                         # standard: canary chay trong chinh app bot (sau deploy dry)
  CJAR=target/binance-java-sdk-1.2.4.jar
  GATE_FILES=${GATE_FILES:-"/home/ubuntu/claude_master/deploy/gates/GOLIVE_GATE_CODE_V12.ok /home/ubuntu/claude_master/deploy/gates/GOLIVE_GATE_PROMO_V11.ok"}
fi
PROC_PAT=${PROC_PAT:-BinanceOrderTradingManager}            # process bot — chi DOC env/PID/cwd, khong cham
JAVA_242=${JAVA_242:-java}
CANARY_JAR=${CANARY_JAR:-/home/ubuntu/claude_master/v12/jar/binance-java-sdk-1.2.4.jar_v12dry_3f}   # jar Oracle copy len 242 (early)
CANARY_JAR_MD5=${CANARY_JAR_MD5:-d2f1b52c348b57939efc7e0165b9fdee}   # [V12 3f] pin jar v12dry_3f (canary-early; dry giu pin 3d trong deploy_v12_dry.sh)
KEYS_FILE=${CANARY_KEYS_FILE:-/root/.config/c3live/keys.env}
KEYS_OWNER=${CANARY_KEYS_OWNER:-root}
LOGDIR=${LOGDIR:-/home/ubuntu/claude_master/canary}
POLL_S=${POLL_S:-15}
STEP_MAX_S=${STEP_MAX_S:-7200}
DRY_MIN_DAYS=${DRY_MIN_DAYS:-5}                               # MO-1: >= 5 ngay dry sach (KHONG ap cho early, §ADD-1)
MEMINFO=${MEMINFO_FILE:-/proc/meminfo}
readonly MIN_RAM_MB=1024                                      # §ADD-1: MemAvailable 242 >= 1 GB truoc khi start (hang so)
readonly MIN_RAM_STEP_MB=768                                  # §ADD-1: truoc moi buoc sau do (hang so)
readonly MIN_DISK_MB=400                                      # copy jar ~100 MB + journal
readonly KILL_LOCK_MIN_S=600                                  # [3c MIN-C3] JVM canary giu lock >= 10' ...
readonly KILL_HB_STALE_S=180                                  #   ... va heartbeat luong chinh cu >= 3' => coi la TREO
readonly CUM_LOSS_CAP_USDT=4                                  # [3c MIN-C2] tong lo moi phien canary-early (MASTER doi bang file gate)
CUM_CAP_FILE=${CUM_CAP_FILE:-/home/ubuntu/claude_master/deploy/gates/CANARY_EARLY_CUM_CAP.ok}
YES=${YES:-0}
FORCE_TIME=${FORCE_TIME:-0}
CDIR=run/canary
MAIN=com.binance.chuyennd.c3live.canary.C3LiveCanary
MAIN_PAT='[c]om.binance.chuyennd.c3live.canary.C3LiveCanary'   # [c]: pgrep khong tu khop dong lenh shell chua mau
TS=${CL_TS:-$(TZ=Asia/Ho_Chi_Minh date +%Y%m%d_%H%M%S)}
CL_LAST_RESULT=""
CL_LAST_OUT=""
CL_PROBE=""
CL_VTM0=""

say()  { echo "[$(TZ=Asia/Ho_Chi_Minh date '+%F %T')] $*"; }
die()  { say "DUNG: $*"; say "KET QUA: TU_CHOI"; [ -n "${CL_LOG:-}" ] && say "Log: $CL_LOG"; exit 2; }
ok()   { say "OK: $*"; }

# cl_init <ten>: mo log Oracle (tee) — log KHONG bao gio chua key (key chi doc bang read -s trong c3live_keys_install.sh)
cl_init() {
  mkdir -p "$LOGDIR" || { echo "khong tao duoc $LOGDIR"; exit 2; }
  CL_LOG=$LOGDIR/$1_${TS}.log
  exec > >(tee -a "$CL_LOG") 2>&1
  say "=== $1 TS=$TS MODE=$CANARY_MODE APP_DIR=$A jar_pin=$CANARY_JAR_MD5 YES=$YES ==="
  # chan gia tri la trong bien di vao lenh ssh
  [[ "$A" =~ ^[A-Za-z0-9_./-]+$ ]] || die "APP_DIR/CANARY_HOME la: $A"
  [[ "$VTM" =~ ^[A-Za-z0-9_./-]+$ ]] || die "VTM_DIR la: $VTM"
  [[ "$MEMINFO" =~ ^[A-Za-z0-9_./-]+$ ]] || die "MEMINFO_FILE la"
  [[ "$KEYS_FILE" =~ ^[A-Za-z0-9_./-]+$ ]] || die "CANARY_KEYS_FILE la"
  [[ "$KEYS_OWNER" =~ ^[a-z_][a-z0-9_-]*$ ]] || die "CANARY_KEYS_OWNER la"
  [[ "$JAVA_242" =~ ^[A-Za-z0-9_./\ -]+$ ]] || die "JAVA_242 la"
  [[ "$PROC_PAT" =~ ^[A-Za-z0-9_.\ -]+$ ]] || die "PROC_PAT la"
  [[ "$CANARY_JAR_MD5" =~ ^[0-9a-f]{32}$ ]] || die "CANARY_JAR_MD5 chua pin"
  case "$CANARY_MODE" in standard|early) ;; *) die "CANARY_MODE la: $CANARY_MODE" ;; esac
  if [ "$CANARY_MODE" = early ]; then
    case "$A/" in "$VTM"/*) die "CANARY_HOME ($A) nam trong v_t_m ($VTM) — §ADD-1 can thu muc rieng" ;; esac
    [ "$A" != "$VTM" ] || die "CANARY_HOME = v_t_m"
  fi
}

need_yes() { [ "$YES" = 1 ] || die "can YES=1 (vd: YES=1 bash $0 ${*:-}) — script nay $1"; }

time_ok() {
  local H M
  H=$(TZ=Asia/Ho_Chi_Minh date +%-H); M=$(TZ=Asia/Ho_Chi_Minh date +%-M)
  # moc test (test_fake242): CL_FAKE_HM = file "H M" (gio +07 gia lap) — chi lam gate CHAT hon/long hon nhu FORCE_TIME
  if [ -n "${CL_FAKE_HM:-}" ] && [ -f "$CL_FAKE_HM" ]; then read -r H M < "$CL_FAKE_HM"; fi
  [ "$M" -ge 10 ] && [ "$M" -le 44 ] || return 1          # chi phut :10-:44
  case "$H" in 7|19) return 1;; esac                       # 07:xx/19:xx
  if [ "$H" -eq 1 ] || [ "$H" -eq 13 ]; then [ "$M" -gt 20 ] || return 1; fi   # tranh 00:50-01:20, 12:50-13:20
  return 0
}
# cl_time_gate die: ngoai khung gio => DUNG. [3c MAJ-C1] CHI goi o DAU phien / dau lenh (tai khoan phang) — KHONG BAO GIO cho khung
# gio giua cac buoc (luc do co the con vi the/stop canary mo, khong JVM nao canh tran lo).
cl_time_gate() {
  [ "$FORCE_TIME" = 1 ] && { say "FORCE_TIME=1: bo chot gio (chi khi MASTER bao)"; return 0; }
  time_ok && return 0
  die "gio +07 khong hop le: chi phut :10-:44, tranh 07:xx, 19:xx, 00:50-01:20, 12:50-13:20 (khong cho — chay lai trong khung gio)"
}

# cl_probe: (CHI DOC tren 242) jar canary, process bot (PID/cwd/env), JVM canary, RAM, md5 v_t_m, o dia, (standard) moc dry.
cl_probe() {
  CL_PROBE=$($SSH_242 "PP='$PROC_PAT' MAIN='$MAIN_PAT' bash -s -- $A $CJAR $VTM $MEMINFO" <<'EOF'
A=$1; CJ=$2; V=$3; MI=$4
echo "JAR=$( [ -f "$A/$CJ" ] && md5sum < "$A/$CJ" | cut -c1-32 || echo none)"
VR=$(readlink -f "$V" 2>/dev/null)
P=""
for p in $(pgrep -f -- "$PP" 2>/dev/null); do
  [ "$(readlink -f /proc/$p/cwd 2>/dev/null)" = "$VR" ] && { P=$p; break; }
done
ev() { [ -n "$P" ] && tr '\0' '\n' < /proc/$P/environ 2>/dev/null | grep "^$1=" | head -1 | cut -d= -f2-; }
echo "BOT=${P:-none}"
echo "ADAPTER=$(ev LIVE_ADAPTER)"
echo "PROFILE=$(ev LIVE_PROFILE)"
echo "NOPUSH=$(ev SHADOW_NO_PUSH)"
echo "CANARY_JVM=$(pgrep -fc "$MAIN")"
echo "MEM_MB=$(awk '/^MemAvailable:/ {print int($2/1024)}' "$MI" 2>/dev/null)"
for f in target/binance-java-sdk-1.2.4.jar conf/env.sh bin/start.sh; do
  echo "VTM_MD5 $f $( [ -f "$V/$f" ] && md5sum < "$V/$f" | cut -c1-32 || echo none)"
done
echo "VTM_CANARY=$( [ -e "$V/run/canary" ] && echo co || echo khong)"
D=$A; [ -d "$D" ] || D=$(dirname "$A")
echo "DISK_MB=$(df -Pm "$D" 2>/dev/null | awk 'NR==2 {print $4}')"
if [ -d "$A" ] && cd "$A" 2>/dev/null; then
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
else
  echo "ADIR=none"
fi
EOF
)
}
pv() { printf '%s\n' "$CL_PROBE" | sed -n "s/^$1=//p" | head -1; }
# anh chup v_t_m (de so): md5 jar/env/start + PID + env process bot
cl_vtm_snap() { printf '%s\n' "$CL_PROBE" | grep -E '^(VTM_MD5 |BOT=|PROFILE=|NOPUSH=|ADAPTER=)'; }

# cl_check_242 [dry|early|early_nojar]: (chi doc) dieu kien chay
#   standard/dry: jar dang deploy = pin; bot KHONG adapter live; khong JVM canary khac; dry: >= DRY_MIN_DAYS ngay sach (§2.3).
#   early: (§ADD-1) jar canary rieng = pin (early_nojar: chua copy => bo qua); v_t_m chay c3_shadow + SHADOW_NO_PUSH=true, khong
#     adapter live; khong JVM canary khac; MemAvailable >= 1 GB; v_t_m khong co run/canary; o dia du.
cl_check_242() {
  local mode=${1:-}
  cl_probe || die "khong ssh duoc 242"
  printf '%s\n' "$CL_PROBE" | sed 's/^/   242: /'
  [ -n "$(pv JAR)" ] || die "khong doc duoc 242"
  if [ "$mode" != early_nojar ]; then
    [ "$(pv JAR)" = "$CANARY_JAR_MD5" ] || die "md5 jar tren 242 khac pin $CANARY_JAR_MD5 ($A/$CJAR = $(pv JAR)) — jar chua audit, khong chay"
    ok "jar 242 md5 = pin"
  fi
  [ "$(pv ADAPTER)" = live ] && die "bot dang o LIVE_ADAPTER=live (runtime chinh giu tai khoan con) — canary TU CHOI"
  [ "$(pv CANARY_JVM)" = 0 ] || die "co JVM canary khac dang chay tren 242"
  ok "bot khong o adapter live; khong co JVM canary khac"
  case "$mode" in
    dry)
      [ "$(pv ADAPTER)" = dry ] || die "bot khong chay LIVE_ADAPTER=dry (dieu kien vao §2.3)"
      local st now days; st=$(pv START); now=$(date +%s)
      [[ "$st" =~ ^[0-9]+$ ]] || die "khong co run/.v12_start_epoch (moc start dry)"
      days=$(( (now - st) / 86400 ))
      [ $((now - st)) -ge $((DRY_MIN_DAYS * 86400)) ] || die "dry moi chay ${days} ngay (< $DRY_MIN_DAYS — MO-1)"
      ok "dry chay ${days} ngay (>= $DRY_MIN_DAYS)"
      printf '%s\n' "$CL_PROBE" | grep -q '^LATCH=0 ORDER=0$' || die "log dry tu moc start co [KILLSW] LATCH / [C3-LIVE-ORDER] (§2.3) — MASTER xem"
      ok "log dry tu moc start: 0 [KILLSW] LATCH, 0 [C3-LIVE-ORDER]" ;;
    early|early_nojar)
      [ "$CANARY_MODE" = early ] || die "cl_check_242 early ngoai CANARY_MODE=early"
      [ "$(pv BOT)" != none ] || die "khong thay process bot trong $VTM (§ADD-1: v_t_m phai dang chay c3_shadow)"
      [ "$(pv PROFILE)" = c3_shadow ] || die "v_t_m LIVE_PROFILE='$(pv PROFILE)' (phai c3_shadow — §ADD-1)"
      [ "$(pv NOPUSH)" = true ] || die "v_t_m SHADOW_NO_PUSH='$(pv NOPUSH)' (phai true — tai khoan chinh khong duoc dung)"
      [ -z "$(pv ADAPTER)" ] || die "v_t_m co LIVE_ADAPTER='$(pv ADAPTER)' (canary-early chi khi v_t_m la shadow v1.1)"
      ok "v_t_m: pid $(pv BOT), c3_shadow, SHADOW_NO_PUSH=true, khong LIVE_ADAPTER"
      printf '%s\n' "$CL_PROBE" | grep -q '^VTM_MD5 .* none$' && die "v_t_m thieu jar/env/start (khong chup duoc md5)"
      [ "$(pv VTM_CANARY)" = khong ] || die "v_t_m co run/canary (canary KHONG duoc ghi vao v_t_m) — MASTER xem"
      cl_ram_check "$MIN_RAM_MB" || die "RAM 242 khong du (§ADD-1)"
      local dk; dk=$(pv DISK_MB)
      [[ "$dk" =~ ^[0-9]+$ ]] && [ "$dk" -ge "$MIN_DISK_MB" ] || die "o dia 242 trong ${dk:-?} MB < $MIN_DISK_MB MB" ;;
  esac
}

# cl_ram_check <MB>: MemAvailable (tu lan probe gan nhat) >= MB
cl_ram_check() {
  local m; m=$(pv MEM_MB)
  if [[ "$m" =~ ^[0-9]+$ ]] && [ "$m" -ge "$1" ]; then ok "MemAvailable 242 = ${m} MB (>= $1)"; return 0; fi
  say "!! MemAvailable 242 = ${m:-khong doc duoc} MB < $1 MB"
  return 1
}

# cl_vtm_baseline: chup v_t_m (tu probe hien tai) => CL_VTM0 + file Oracle
cl_vtm_baseline() {
  CL_VTM0=$(cl_vtm_snap)
  [ -n "$CL_VTM0" ] || die "khong chup duoc v_t_m"
  printf '%s\n' "$CL_VTM0" > "$LOGDIR/vtm_baseline_${TS}.txt"
  say "anh chup v_t_m (so truoc/sau moi buoc):"; printf '%s\n' "$CL_VTM0" | sed 's/^/   vtm0: /'
}
# cl_vtm_check <nhan>: probe lai, so v_t_m voi anh chup; 0 = khong doi. Dat CL_VTM_DIFF.
CL_VTM_DIFF=""
cl_vtm_check() {
  local i
  for i in 1 2 3; do   # ssh chap chon: thu 3 lan (10 s) truoc khi coi la "khong kiem duoc" (=> dung, fail-closed)
    cl_probe && [ -n "$(pv JAR)" ] && break
    CL_PROBE=""; [ "$i" -lt 3 ] && sleep "${CL_RETRY_S:-10}"
  done
  if [ -z "$(pv JAR)" ]; then CL_VTM_DIFF="khong doc duoc 242 ($1)"; say "!! v_t_m $1: $CL_VTM_DIFF"; return 1; fi
  local now; now=$(cl_vtm_snap)
  CL_VTM_DIFF=$(diff <(printf '%s\n' "$CL_VTM0") <(printf '%s\n' "$now") | grep '^[<>]' | tr '\n' ';')
  [ "$(pv VTM_CANARY)" = khong ] || CL_VTM_DIFF+=" v_t_m/run/canary xuat hien;"
  if [ -n "$CL_VTM_DIFF" ]; then say "!! v_t_m BI DOI ($1): $CL_VTM_DIFF"; return 1; fi
  say "v_t_m khong doi ($1): pid $(pv BOT), md5 jar/env/start giu nguyen"
  return 0
}

# cl_gates: file gate MASTER ky (Oracle). standard: G-CODE + G-PROMO; early: chi G-CODE (§ADD-1)
cl_gates() {
  local g
  for g in $GATE_FILES; do [ -s "$g" ] || die "thieu file gate MASTER: $g (MASTER tao sau khi A1 DAT)"; done
  ok "file gate MASTER co du: $GATE_FILES"
}

# cl_push_logback: dat logback-canary.xml vao run/canary/ tren 242
cl_push_logback() {
  $SSH_242 "mkdir -p $A/$CDIR" < /dev/null || die "khong tao duoc $A/$CDIR"
  $SCP_242 "$CL_HERE/logback-canary.xml" "${RHOST}$A/$CDIR/logback-canary.xml" || die "khong chep duoc logback-canary.xml"
}

# cl_copy_legacy (early): tap LEGACY tai khoan chinh cho luat §3 — CHI DOC v_t_m/run/legacy_symbols.csv, ghi ban sao vao CANARY_HOME/run
cl_copy_legacy() {
  local r
  r=$($SSH_242 "mkdir -p $A/run && if [ -f $VTM/run/legacy_symbols.csv ]; then cat $VTM/run/legacy_symbols.csv > $A/run/legacy_symbols.csv.tmp && mv -f $A/run/legacy_symbols.csv.tmp $A/run/legacy_symbols.csv && echo \"LEGACY=\$(grep -c . $A/run/legacy_symbols.csv) dong\"; else rm -f $A/run/legacy_symbols.csv; echo LEGACY=none; fi" < /dev/null)
  say "LEGACY (luat §3): ${r#LEGACY=} $( [ "$r" = LEGACY=none ] && echo '(v_t_m khong co run/legacy_symbols.csv => tap rong)')"
  CL_LEGACY=${r#LEGACY=}
}

# cl_run <env "K=V K=V" (da kiem)> <lenh C3LiveCanary...>: chay JVM canary tren 242 bang nohup+setsid (mat ssh KHONG giet JVM),
# env -i (env sach), poll ket qua moi POLL_S. Dat CL_LAST_RESULT + CL_LAST_OUT; tra ma thoat JVM (0 DAT/2 TU_CHOI/3 TRUOT/4 LOI/5 khong ro).
cl_run() {
  local envs=$1; shift
  local a id n=0 rc="" t0 got line
  for a in "$@" $envs; do [[ "$a" =~ ^[A-Za-z0-9_=.]+$ ]] || die "tham so la: $a"; done
  id="${TS}_$$_${RANDOM}"
  say "--> JVM canary: $* ${envs:+(env $envs)}"
  # [3d] { ( ... ) ... & }: CHI subshell JVM chay nen (fd da chuyen /dev/null) — truoc day ca chuoi "cd && mkdir && (...)" bi dua
  # nen voi fd kenh ssh => lenh ssh khoi dong KHONG tra ve toi khi JVM xong (K0 ~65'), STEP_MAX_S/poll khong co tac dung, mat
  # mang giua chung => script die trong khi JVM van chay. Nay ssh tra ve ngay, poll theo doi nhu thiet ke.
  $SSH_242 "cd $A && mkdir -p $CDIR && { ( nohup setsid env -i PATH=\"\$PATH\" HOME=\"\$HOME\" LANG=C.UTF-8 CANARY_DIR=$CDIR \
    LIVE_C3_KEYS_FILE=$KEYS_FILE LIVE_C3_KEYS_OWNER=$KEYS_OWNER $envs \
    $JAVA_242 -Xmx384m -XX:+UseSerialGC -XX:MaxMetaspaceSize=256m -Dlogback.configurationFile=$CDIR/logback-canary.xml -cp $CJAR $MAIN $* \
    > $CDIR/.jvm_$id.out 2>&1 < /dev/null; echo \$? > $CDIR/.jvm_$id.rc.tmp; mv -f $CDIR/.jvm_$id.rc.tmp $CDIR/.jvm_$id.rc ) > /dev/null 2>&1 < /dev/null & }" < /dev/null \
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
      local r6b=$CL_LAST_RESULT
      say "K6b: dong tay (canary_flatten) theo prereg §4 K6b"
      cl_run "" flatten; local rf=$?
      CL_LAST_RESULT="$r6b ; sau do $CL_LAST_RESULT"
      [ $rc = 0 ] || return $rc
      return $rf ;;
    *) die "buoc la: $k (SETUP K1..K8 K6 K6B K7B K6_OPEN K6_RESTART K6B_OPEN K6B_RESTART)" ;;
  esac
}

# cl_kill_hung (CHI mode early, MIN-C3): kill JVM canary TREO truoc khi flatten. Chi kill process: cwd = CANARY_HOME (khong bao gio
#   v_t_m), co arg dung = lop main C3LiveCanary (khong phai vo shell), la pid dang giu lock tai khoan con (run/c3live_account.lock
#   "... pid=<p> since=<ms>") >= KILL_LOCK_MIN_S, va heartbeat luong chinh (run/canary/canary_jvm.hb "pid=<p> ms=<ms>") cu >=
#   KILL_HB_STALE_S (khong co heartbeat cua pid do => tinh tu luc giu lock). Dat CL_KILLED (so JVM da kill).
CL_KILLED=0
cl_kill_hung() {
  CL_KILLED=0
  [ "$CANARY_MODE" = early ] || { say "mode chuan: KHONG tu kill JVM canary (cwd = v_t_m) — kiem tay"; return 0; }
  local r
  r=$($SSH_242 "bash -s -- $A $KILL_LOCK_MIN_S $KILL_HB_STALE_S $VTM" <<'EOF'
A=$(readlink -f "$1"); LK_MIN=$2; HB_MIN=$3; V=$(readlink -f "$4")
M=com.binance.chuyennd.c3live.canary.C3LiveCanary
now=$(date +%s)
LK=$A/run/c3live_account.lock; HB=$A/run/canary/canary_jvm.hb
lk_pid=$(sed -n 's/.* pid=\([0-9]*\).*/\1/p' "$LK" 2>/dev/null | head -1)
lk_ms=$(sed -n 's/.* since=\([0-9]*\).*/\1/p' "$LK" 2>/dev/null | head -1)
hb_pid=$(sed -n 's/^pid=\([0-9]*\) .*/\1/p' "$HB" 2>/dev/null | head -1)
hb_ms=$(sed -n 's/.* ms=\([0-9]*\).*/\1/p' "$HB" 2>/dev/null | head -1)
n=0
for p in $(pgrep -f "[c]om.binance.chuyennd.c3live.canary.C3LiveCanary" 2>/dev/null); do
  tr '\0' '\n' < /proc/$p/cmdline 2>/dev/null | grep -qxF "$M" || continue   # vo shell bao quanh / lenh ssh: khong phai JVM
  n=$((n + 1))
  cwd=$(readlink -f /proc/$p/cwd 2>/dev/null)
  if [ "$cwd" != "$A" ] || [ "$cwd" = "$V" ]; then echo "GIU $p cwd=$cwd (khong phai thu muc canary rieng)"; continue; fi
  if [ -z "$lk_ms" ] || [ "$p" != "$lk_pid" ]; then echo "GIU $p (khong phai pid giu lock: ${lk_pid:-?})"; continue; fi
  lk_age=$(( now - lk_ms / 1000 ))
  if [ "$hb_pid" = "$p" ] && [ -n "$hb_ms" ]; then hb_age=$(( now - hb_ms / 1000 )); else hb_age=$lk_age; fi
  if [ "$lk_age" -ge "$LK_MIN" ] && [ "$hb_age" -ge "$HB_MIN" ]; then
    kill -TERM "$p" 2>/dev/null
    for i in 1 2 3 4 5 6 7 8 9 10; do kill -0 "$p" 2>/dev/null || break; sleep 1; done
    kill -0 "$p" 2>/dev/null && kill -KILL "$p" 2>/dev/null && sleep 1
    if kill -0 "$p" 2>/dev/null; then echo "KILL_FAIL $p"; else echo "KILLED $p lock=${lk_age}s hb=${hb_age}s"; fi
  else
    echo "GIU $p dang song (lock=${lk_age}s hb=${hb_age}s; kill khi >= ${LK_MIN}s va >= ${HB_MIN}s)"
  fi
done
echo "JVM_CANARY=$n"
EOF
)
  printf '%s\n' "$r" | sed 's/^/   kill-hung: /'
  CL_KILLED=$(printf '%s\n' "$r" | grep -c '^KILLED')
  [ "$CL_KILLED" -gt 0 ] && sleep 2
  return 0
}

# cl_cum_loss check|info (CHI mode early, MIN-C2): tong lo MOI phien canary-early tren 242 (run/canary, run/canary_done_*,
#   run/canary_prev_*: moi phien max(0, phi + lo da chot - funding) tu canary_state.json) + so lan CANARY_RESET (= so canary_prev_*).
#   check: tong > tran (4 USDT, hoac so MASTER ghi trong CUM_CAP_FILE) => DUNG. Dat CL_CUM_LOSS, CL_RESETS, CL_CUM_CAP, CL_CUM_DETAIL.
CL_CUM_LOSS=0; CL_RESETS=0; CL_CUM_CAP=$CUM_LOSS_CAP_USDT; CL_CUM_DETAIL=""
cl_cum_loss() {
  local mode=${1:-check} raw out c
  CL_CUM_CAP=$CUM_LOSS_CAP_USDT
  if [ -s "$CUM_CAP_FILE" ]; then
    c=$(tr -d ' \r\n' < "$CUM_CAP_FILE")
    if [[ "$c" =~ ^[0-9]+(\.[0-9]+)?$ ]]; then CL_CUM_CAP=$c; say "tran lo cong don do MASTER dat ($CUM_CAP_FILE): $c USDT"; fi
  fi
  raw=$($SSH_242 "cd $A 2>/dev/null || exit 0; for d in run/canary run/canary_done_* run/canary_prev_*; do [ -f \$d/canary_state.json ] && { echo \"==DIR \$d\"; cat \$d/canary_state.json; echo; }; done; true" < /dev/null) \
    || die "khong doc duoc trang thai cac phien canary tren 242 (MIN-C2)"
  out=$(printf '%s\n' "$raw" | python3 -I -c '
import json, sys
blocks, cur, buf = [], None, []
for line in sys.stdin.read().splitlines():
    if line.startswith("==DIR "):
        if cur is not None: blocks.append((cur, "\n".join(buf)))
        cur, buf = line[6:].strip(), []
    else:
        buf.append(line)
if cur is not None: blocks.append((cur, "\n".join(buf)))
tot, resets = 0.0, 0
for d, t in blocks:
    try: s = json.loads(t)
    except Exception: print("SESS %s HONG (coi lo = 2.0)" % d); tot += 2.0; continue
    l = float(s.get("cumFeeStable") or 0) - float(s.get("cumRealized") or 0) - float(s.get("cumFunding") or 0)
    l = max(0.0, l)
    tot += l
    if d.startswith("run/canary_prev_"): resets += 1
    print("SESS %s lo=%.4f aborted=%s" % (d, l, s.get("aborted")))
print("CUM %.4f %d %d" % (tot, resets, len(blocks)))
') || die "khong tinh duoc lo cong don"
  CL_CUM_DETAIL=$(printf '%s\n' "$out" | grep '^SESS ')
  CL_CUM_LOSS=$(printf '%s\n' "$out" | awk '/^CUM / {print $2}')
  CL_RESETS=$(printf '%s\n' "$out" | awk '/^CUM / {print $3}')
  say "lo cong don moi phien canary-early: ${CL_CUM_LOSS:-?} USDT (tran $CL_CUM_CAP), so lan CANARY_RESET: ${CL_RESETS:-?}"
  printf '%s\n' "$CL_CUM_DETAIL" | sed '/^$/d; s/^/   /'
  [ -n "$CL_CUM_LOSS" ] || die "khong tinh duoc lo cong don"
  if [ "$mode" = check ] && python3 -I -c "import sys; sys.exit(0 if float('$CL_CUM_LOSS') > float('$CL_CUM_CAP') else 1)"; then
    die "tong lo cong don $CL_CUM_LOSS USDT > tran $CL_CUM_CAP USDT (MIN-C2) — KHONG chay phien moi; MASTER quyet"
  fi
  return 0
}

# ---------------------------------------------------------------------------- [3d] dung chung install / canary_early_all.sh
# cl_early_old: (chi doc) phien canary cu trong CANARY_HOME/run/canary => CL_OLD = NONE | K0ONLY | TRADE <buoc,..> | ABORTED | HONG
#   (K0 / SETUP khong tinh la buoc giao dich; FLATTEN / CLEANUP / K1.. co tinh — giong engine hasTradeSteps)
CL_OLD=""
cl_early_old() {
  local st
  st=$($SSH_242 "cat $A/$CDIR/canary_state.json 2>/dev/null" < /dev/null)
  CL_OLD=$(printf '%s' "$st" | python3 -I -c '
import json, sys
t = sys.stdin.read().strip()
if not t: print("NONE"); sys.exit()
try: s = json.loads(t)
except Exception: print("HONG"); sys.exit()
k = [x for x in (s.get("steps") or {}) if x not in ("K0", "SETUP")]
print("TRADE " + ",".join(sorted(k)) if k else ("ABORTED" if s.get("aborted") else "K0ONLY"))
')
  say "phien canary cu tren 242: $CL_OLD"
}

# cl_early_jar: thu muc rieng CANARY_HOME (700) + jar pin (copy neu 242 chua co / khac pin; kiem md5 TREN 242). Dung probe gan nhat.
cl_early_jar() {
  local r
  $SSH_242 "umask 077 && mkdir -p $A/run && chmod 700 $A" < /dev/null || die "khong tao duoc $A tren 242"
  if [ "$(pv JAR)" != "$CANARY_JAR_MD5" ]; then
    say "copy jar -> 242:$A/$CJAR"
    $SCP_242 "$CANARY_JAR" "${RHOST}$A/$CJAR.tmp" || die "scp jar loi"
    r=$($SSH_242 "cd $A && [ \"\$(md5sum < $CJAR.tmp | cut -c1-32)\" = $CANARY_JAR_MD5 ] && mv -f $CJAR.tmp $CJAR && echo JAR_OK || { rm -f $CJAR.tmp; echo JAR_SAI; }" < /dev/null)
    [ "$r" = JAR_OK ] || die "md5 jar tren 242 sau copy khac pin — da xoa ban tam"
  fi
  ok "jar 242:$A/$CJAR md5 = pin"
}

# cl_early_reset: CANARY_RESET=1 va phien cu co giao dich => cleanup (tai khoan con PHAI phang) + doi ten run/canary_prev_<TS>
cl_early_reset() {
  [ "${CANARY_RESET:-0}" = 1 ] && [ "$CL_OLD" != NONE ] && [ "$CL_OLD" != K0ONLY ] || return 0
  cl_push_logback
  cl_run "" cleanup || die "CANARY_RESET: tai khoan con CHUA phang ($CL_LAST_RESULT) — chay bash $CL_HERE/canary_early_flatten.sh truoc"
  $SSH_242 "cd $A && mv $CDIR run/canary_prev_$TS" < /dev/null || die "khong doi ten phien cu"
  ok "phien cu -> $A/run/canary_prev_$TS"
}

# cl_flat_read: (CHI DOC) keycheck => CL_TMB, CL_FLAT ("pos=.. orders=.. algos=.."), CL_USDT, CL_ASSETS. KHONG ghi buoc vao state
#   (khac cleanup/flatten — 2 lenh do ghi buoc CLEANUP/FLATTEN, bi tinh la buoc giao dich). 0 = phang, 1 = KHONG phang,
#   2 = khong doc duoc (CL_FLAT_WHY).
CL_TMB=""; CL_FLAT=""; CL_FLAT_WHY=""; CL_USDT=""; CL_ASSETS=""
cl_flat_read() {
  local l p o g
  CL_TMB=""; CL_FLAT=""; CL_FLAT_WHY=""; CL_USDT=""; CL_ASSETS=""
  cl_run "" keycheck || { CL_FLAT_WHY="keycheck khong DAT (${CL_LAST_RESULT:-khong co RESULT})"; return 2; }
  l=$(printf '%s' "$CL_LAST_OUT" | grep '^KEYCHECK ' | tail -1)
  CL_TMB=$(printf '%s' "$l" | sed -n 's/.* tmb=\([0-9][0-9.]*\) .*/\1/p')
  CL_ASSETS=$(printf '%s' "$l" | sed -n 's/.* assets=\({[^}]*}\).*/\1/p')
  CL_LEGACY=$(printf '%s' "$l" | sed -n 's/.* legacy=\([^ ]*\) .*/\1/p')   # [3f §ADD-4] LEGACY chi dem (khong tinh vao "phang")
  CL_USDT=$(printf '%s' "$CL_ASSETS" | sed -nE 's/.*[{ ]USDT=([0-9.-]+).*/\1/p')
  p=$(printf '%s' "$l" | sed -n 's/.* pos=\([0-9]*\) .*/\1/p')
  o=$(printf '%s' "$l" | sed -n 's/.* orders=\([0-9]*\) .*/\1/p')
  g=$(printf '%s' "$l" | sed -n 's/.* algos=\([0-9]*\)$/\1/p')
  if ! [[ "$p" =~ ^[0-9]+$ && "$o" =~ ^[0-9]+$ && "$g" =~ ^[0-9]+$ ]]; then
    CL_FLAT_WHY="keycheck khong in pos/orders/algos (jar tren 242 cu hon 3d?)"; return 2
  fi
  CL_FLAT="pos=$p orders=$o algos=$g"
  say "keycheck (chi doc, pham vi canary §ADD-4 C): tmb=${CL_TMB:-?} assets=${CL_ASSETS:-?} $CL_FLAT${CL_LEGACY:+ ; LEGACY (chi dem) $CL_LEGACY}"
  [ "$p" = 0 ] && [ "$o" = 0 ] && [ "$g" = 0 ]
}

# cl_tg <tin>: gui Telegram qua kenh san co tren Oracle (CANARY_TG_ENV, mac dinh ~/.config/health242/tg.env, cung cach doc nhu
#   ops/health_242.sh). Token KHONG vao argv / log (curl -K - doc url tu stdin); tin nhan che mau bi mat truoc khi gui.
#   Test: CANARY_TG_SINK=<file> => ghi tin vao file, KHONG goi mang. 0 = da gui.
CANARY_TG_ENV=${CANARY_TG_ENV:-/home/ubuntu/.config/health242/tg.env}
cl_tg() {
  local msg code tok chat
  msg=$(printf '%s' "$1" | sed -E 's/signature=[^ "]*/[CHE]/g; s/[0-9]{8,10}:[A-Za-z0-9_-]{35}/[CHE]/g; s/[A-Za-z0-9]{56,}/[CHE]/g' | head -c 3500)
  if [ -n "${CANARY_TG_SINK:-}" ]; then
    { printf '%s\n' "$msg"; echo "----"; } >> "$CANARY_TG_SINK"; say "Telegram (test sink): da ghi $CANARY_TG_SINK"; return 0
  fi
  [ -r "$CANARY_TG_ENV" ] || { say "!! khong doc duoc $CANARY_TG_ENV — KHONG gui duoc Telegram"; return 1; }
  tok=$(sed -nE 's/^[[:space:]]*(export[[:space:]]+)?(TG_TOKEN=|tele-token:[[:space:]]*)//p' "$CANARY_TG_ENV" | head -1 | tr -d '\r"')
  chat=$(sed -nE 's/^[[:space:]]*(export[[:space:]]+)?(TG_CHAT=|tele-chat-id:[[:space:]]*)//p' "$CANARY_TG_ENV" | head -1 | tr -d '\r"')
  [ -n "$tok" ] && [ -n "$chat" ] || { say "!! $CANARY_TG_ENV thieu TG_TOKEN/TG_CHAT — KHONG gui duoc Telegram"; return 1; }
  code=$(printf 'url = "https://api.telegram.org/bot%s/sendMessage"\n' "$tok" | curl -s -m 15 -o /dev/null -w '%{http_code}' -K - \
    --data-urlencode "chat_id=$chat" --data-urlencode "text=$msg" 2>/dev/null)
  tok=""
  if [ "$code" = 200 ]; then say "Telegram: da gui (HTTP 200)"; return 0; fi
  say "!! Telegram KHONG gui duoc (HTTP ${code:-loi})"; return 1
}
