#!/usr/bin/env bash
# =============================================================================
# swap_v12_dry_jar.sh — [V12 R4q/R4r] THAY JAR v_t_m dry v1.2 (c3_live, LIVE_ADAPTER=dry) OLD_TAG -> NEW_TAG (mac dinh r4t -> r4u3),
#   1 lan restart, KHONG seed.
#   [R4r] tong quat: OLD_TAG/NEW_TAG/OLD_MD5/NJ/NJ_MD5 (pin = cap hien hanh); NEED_MGUARD=1 => hau kiem [MINUTE-GUARD] BAT
#   (TAT => FAIL => rollback), env.sh co LIVE_MINUTE_GUARD=0 => TU CHOI truoc khi dung bot.
#   [R4u] NEED_BIGDOWN=1 (mac dinh): jar moi PHAI co code [BIG_DOWN-SEL] (chuoi trong class com/binance/chuyennd/**, kiem tren Oracle)
#   — khong co => DUNG truoc moi thao tac 242. Rollback ve r4t: OLD_TAG=r4u3 NEW_TAG=r4t OLD_MD5=15f9e14f... NJ=<jar r4t> NJ_MD5=694b29b2...
#   NEED_BIGDOWN=0 bash swap_v12_dry_jar.sh
#   [R4u2] C3_EXCLUDE_LEGACY_HELD: NEW_TAG r4u3* => ghi env.sh false (C3_ACCOUNT=SUB, mac dinh, ke ca dry) | true (MAIN); jar khac
#   (vd ve r4t) => GO dong; hau kiem env process dung gia tri / khong con. Rollback tu dong => env.sh backup (khong co dong).
#   [A1 r4u2 C-1] C3_ACCOUNT=MAIN + EXCL_HELD=false => TU CHOI; SUB: hau kiem log KHONG co [C3-EXCL-FORCE] (jar r4u3 ep true khi
#   live + key khong phai keys_sub.env => env key sai).
#   [ADD19] hau kiem DAT => in + luu START_MS JVM moi (~/claude_master/deploy/swap_start_<tag>_<TS>.txt), dang ky register_jar.sh,
#   ghi smoke_start_ms vao parity_v12w/gmicro_target.json KHI file tro dung target_jar=<NEW_TAG> + target_md5=<NJ_MD5> (khac => WARN).
#   Them C11 (LIVE_SEED_EXCLUDE_DECISION_MIN=1) neu env.sh chua co. Khong doi gi khac (adapter/profile/push giu nguyen = dry).
# Chay tren ORACLE (owner), 1 lenh:
#   DRY=1 bash ~/claude_master/v12/c3live/ops/c3live/swap_v12_dry_jar.sh   # chi kiem (Oracle + 242 CHI DOC), KHONG ghi gi
#   bash ~/claude_master/v12/c3live/ops/c3live/swap_v12_dry_jar.sh         # go YES => JOB NEN tren Oracle (setsid nohup)
#   [A1 R4Q_SWAP MIN-1] Foreground CHI kiem + hoi YES + khoi dong JOB NEN (log rieng) + tail. Dong terminal / rot ssh KHONG dung job.
#   Xem tien do: tail -f ~/claude_master/deploy/swap_v12_dry_jar_<TS>_job_<pid>.log (duong dan in ra sau YES; ket qua gui Telegram).
#   [MIN-2] Job: cho khung gio hop le (:10-:44, toi da WINDOW_WAIT_MAX_S=5400 s) -> kiem 242 LAI -> chep jar -> kiem khung gio LAN NUA
#   NGAY TRUOC stop (ngoai khung => cho tiep, cung tran).
# Thu tu: kiem jar moi tren Oracle (md5) -> kiem 242 CHI DOC (1 process, jar dang chay = OLD r4n, dry, latch NONE, khong PAUSE/
#   canary/soak, RAM/dia, LEGACY doc duoc, gate_ratio_live.bin co, khong seed treo) -> khung gio -> YES -> chep jar len 242
#   (.v12swap_<TS>, kiem md5) -> backup env.sh -> them env -> PAUSE token (+ tu go sau WD_PAUSE_MAX_S) -> stop -> backup jar
#   (.bak_swap_<TS> + .md5 = OLD) + gate_ratio_live.bin (.bak_swap_<TS> + .md5) -> cai jar moi (md5 = NEW) -> start -> hau kiem:
#   1 process, md5 jar = NEW, env (c3_live/dry/SHADOW_NO_PUSH=true/C11=1), khong canh bao race C11, [UNIVERSE-A1] co PREMARKET=,
#   [GATE-PRE] co premarket_bo=, dong LIVE_PROFILE co LEGACY_QUEUE_LIVE_BLOCK=true, LEGACY managed = truoc, latch NONE, 0 KHAN,
#   runtime, GATE tick -> go PAUSE.
# Hau kiem TRUOT => ROLLBACK TU DONG: stop -> jar cu (md5 OLD) + env.sh + gate_ratio_live.bin (md5) -> start lai r4n nhu truoc.
# [R4q ADD11] Hau kiem DAT => dang ky jar cho harness parity: register_jar.sh r4q <jar> <md5> <start_ms JVM r4q> 1 (Oracle).
#   Rollback => KHONG dang ky. Lenh dang ky loi => chi WARN + Telegram (dry r4q GIU nguyen).
# Ma thoat: 0 XONG | 1 DUNG/da rollback | 2 ROLLBACK LOI (PAUSE con — xem dong "PAUSE còn").
# Bien (test): SSH_242 SCP_242 RHOST APP_DIR PROC_PAT OLD_MD5 NJ NJ_MD5 WD_PAUSE WD_PAUSE_MAX_S POST_WAIT_S POST_ROUNDS LOGDIR
#   FORCE_TIME DEPLOY_TG_ENV DEPLOY_TG_SINK MIN_MEM_MB SSH_RETRY_S REG_JAR_SH REG_TIMEOUT_S WINDOW_WAIT_MAX_S WINDOW_POLL_S
#   TIME_OK_FILE (test: co file = trong khung) OLD_TAG NEW_TAG NEED_MGUARD NEED_BIGDOWN C3_ACCOUNT EXCL_HELD GMICRO_TARGET
# =============================================================================
set -uo pipefail
SSH_242=${SSH_242:-"ssh -p 2222 -o BatchMode=yes -o ConnectTimeout=20 -i /home/ubuntu/.ssh/id_rsa_chuyennd root@103.157.218.242"}
SCP_242=${SCP_242:-"scp -P 2222 -o BatchMode=yes -o ConnectTimeout=20 -i /home/ubuntu/.ssh/id_rsa_chuyennd"}
RHOST=${RHOST-"root@103.157.218.242:"}
A=${APP_DIR:-/home/chuyennd/java/v_t_m}
PROC_PAT=${PROC_PAT:-BinanceOrderTradingManager}
OLD_MD5=${OLD_MD5:-694b29b2e5be32b537ca6c38557e64db}   # jar dry DANG chay (r4t, ROUND4T) — khac => TU CHOI
NJ=${NJ:-/home/ubuntu/claude_master/v12/jar/binance-java-sdk-1.2.4.jar_v12_r4u3}
NJ_MD5=${NJ_MD5:-b1f12c3eeaeed72cb17afbe5b4da06cf}   # jar r4u3 (BIG_DOWN-SEL + BIG_DOWN-GATE, ADD18/19); truoc: r4t 694b29b2, r4q 8c81e6b5
OLD_TAG=${OLD_TAG:-r4t}
NEW_TAG=${NEW_TAG:-r4u3}
NEED_BIGDOWN=${NEED_BIGDOWN:-1}   # [R4u] jar moi phai co code [BIG_DOWN-SEL]
C3_ACCOUNT=${C3_ACCOUNT:-SUB}     # [R4u2] SUB (mac dinh, ADD4) | MAIN — quyet dinh C3_EXCLUDE_LEGACY_HELD
case "$C3_ACCOUNT" in SUB|MAIN) ;; *) echo "C3_ACCOUNT=$C3_ACCOUNT khong hop le (SUB | MAIN)"; exit 1;; esac
case "$NEW_TAG" in r4u3*) DEF_EXCL=$([ "$C3_ACCOUNT" = SUB ] && echo false || echo true);; *) DEF_EXCL="";; esac
EXCL_HELD=${EXCL_HELD-$DEF_EXCL}   # [R4u2] export C3_EXCLUDE_LEGACY_HELD=<gia tri> vao env.sh (dong cu bo); RONG = go dong (jar cu / ve r4t)
[ -z "$EXCL_HELD" ] || [ "$EXCL_HELD" = false ] || [ "$EXCL_HELD" = true ] || { echo "EXCL_HELD chi true | false | rong"; exit 1; }
if [ "$C3_ACCOUNT" = MAIN ] && [ "$EXCL_HELD" = false ]; then echo "DUNG: C3_ACCOUNT=MAIN di voi C3_EXCLUDE_LEGACY_HELD=false — TU CHOI (A1 r4u2 C-1: vi the c3 that bi tinh la LEGACY)"; exit 1; fi
GMICRO_TARGET=${GMICRO_TARGET:-/home/ubuntu/claude_master/parity_v12w/gmicro_target.json}   # [ADD19] smoke_start_ms
NEED_MGUARD=${NEED_MGUARD:-1}   # [R4r] jar moi co guard do du phut => hau kiem [MINUTE-GUARD] BAT
WD_PAUSE=${WD_PAUSE:-/var/lib/h242_watchdog/PAUSE}
WD_PAUSE_MAX_S=${WD_PAUSE_MAX_S:-1800}
POST_WAIT_S=${POST_WAIT_S:-60}
POST_ROUNDS=${POST_ROUNDS:-6}
MIN_MEM_MB=${MIN_MEM_MB:-1000}
DRY=${DRY:-0}
FORCE_TIME=${FORCE_TIME:-0}
SSH_RETRY_S=${SSH_RETRY_S:-10}
DEPLOY_TG_ENV=${DEPLOY_TG_ENV:-/home/ubuntu/.config/health242/tg.env}
REG_JAR_SH=${REG_JAR_SH:-/home/ubuntu/claude_master/vz_e1_wt/research/parity_v12/sh/register_jar.sh}
REG_TIMEOUT_S=${REG_TIMEOUT_S:-5400}
WINDOW_WAIT_MAX_S=${WINDOW_WAIT_MAX_S:-5400}
WINDOW_POLL_S=${WINDOW_POLL_S:-30}
SW_JOB=${SW_JOB:-0}   # 1 = job nen (chi foreground khoi dong, kem SW_YES_FILE)
SELF=$(cd "$(dirname "$0")" && pwd)/$(basename "$0")
TS=${SW_TS:-$(TZ=Asia/Ho_Chi_Minh date +%Y%m%d_%H%M%S)}
LOGDIR=${LOGDIR:-/home/ubuntu/claude_master/deploy}
mkdir -p "$LOGDIR"
if [ "$SW_JOB" = 1 ]; then
  LOG=${SW_JOBLOG:?"job nen thieu SW_JOBLOG"}   # stdout/stderr job da vao file nay (nohup)
else
  LOG=$LOGDIR/swap_v12_dry_jar_${TS}.log
  exec > >(tee -a "$LOG") 2>&1
fi
say() { echo "[$(TZ=Asia/Ho_Chi_Minh date '+%F %T')] $*"; }
tg() {
  local msg code tok chat
  msg=$(printf '%s' "$1" | sed -E 's/[0-9]{8,10}:[A-Za-z0-9_-]{35}/[CHE]/g; s/[A-Za-z0-9]{56,}/[CHE]/g' | head -c 3500)
  if [ -n "${DEPLOY_TG_SINK:-}" ]; then { printf '%s\n' "$msg"; echo "----"; } >> "$DEPLOY_TG_SINK"; return 0; fi
  [ -r "$DEPLOY_TG_ENV" ] || { say "!! khong doc duoc $DEPLOY_TG_ENV — KHONG gui Telegram"; return 1; }
  tok=$(sed -nE 's/^[[:space:]]*(export[[:space:]]+)?(TG_TOKEN=|tele-token:[[:space:]]*)//p' "$DEPLOY_TG_ENV" | head -1 | tr -d '\r"')
  chat=$(sed -nE 's/^[[:space:]]*(export[[:space:]]+)?(TG_CHAT=|tele-chat-id:[[:space:]]*)//p' "$DEPLOY_TG_ENV" | head -1 | tr -d '\r"')
  [ -n "$tok" ] && [ -n "$chat" ] || return 1
  code=$(printf 'url = "https://api.telegram.org/bot%s/sendMessage"\n' "$tok" | curl -s -m 15 -o /dev/null -w '%{http_code}' -K - \
    --data-urlencode "chat_id=$chat" --data-urlencode "text=$msg" 2>/dev/null)
  tok=""; [ "$code" = 200 ]
}
die() { say "DUNG: $*"; say "KET QUA: TU_CHOI (khong doi gi). Log: $LOG"; [ "$SW_JOB" = 1 ] && tg "[swap jar dry] DUNG TS=$TS: $* | log $LOG"; exit 1; }
LOCKD=$LOGDIR/.swap_v12_dry_jar.lock.d
lock_take() {   # khoa 1 job NGUYEN TU (nhu deploy_v12_dry_r4.sh)
  if mkdir "$LOCKD" 2>/dev/null; then echo $$ > "$LOCKD/pid"; return 0; fi
  local p q; p=$(cat "$LOCKD/pid" 2>/dev/null)
  if [ -n "$p" ] && kill -0 "$p" 2>/dev/null && tr '\0' ' ' < "/proc/$p/cmdline" 2>/dev/null | grep -q swap_v12_dry_jar; then return 1; fi
  mv "$LOCKD" "$LOCKD.orphan.$$" 2>/dev/null || return 1
  q=$(cat "$LOCKD.orphan.$$/pid" 2>/dev/null)
  if [ "$q" != "$p" ]; then mv "$LOCKD.orphan.$$" "$LOCKD" 2>/dev/null; return 1; fi
  rm -rf "$LOCKD.orphan.$$"; say "khoa mo coi (pid ${p:-?} da chet) => lay lai"
  mkdir "$LOCKD" 2>/dev/null || return 1
  echo $$ > "$LOCKD/pid"
}
s242() {
  local i rc=255
  for i in 1 2 3; do
    $SSH_242 "$@" < /dev/null; rc=$?
    [ "$rc" != 255 ] && return "$rc"
    [ "$i" -lt 3 ] && { echo "[ssh 242 loi ket noi — thu lai $i/2 sau ${SSH_RETRY_S}s]" >&2; sleep "$SSH_RETRY_S"; }
  done
  return "$rc"
}
s242in() {
  local in i rc=255
  in=$(cat)
  for i in 1 2 3; do
    printf '%s\n' "$in" | $SSH_242 "$@"; rc=$?
    [ "$rc" != 255 ] && return "$rc"
    [ "$i" -lt 3 ] && { echo "[ssh 242 loi ket noi — thu lai $i/2 sau ${SSH_RETRY_S}s]" >&2; sleep "$SSH_RETRY_S"; }
  done
  return "$rc"
}
time_ok() {
  if [ -n "${TIME_OK_FILE:-}" ]; then [ -e "$TIME_OK_FILE" ]; return; fi   # test
  local H M
  H=$(TZ=Asia/Ho_Chi_Minh date +%-H); M=$(TZ=Asia/Ho_Chi_Minh date +%-M)
  [ "$M" -ge 10 ] && [ "$M" -le 44 ] || return 1
  case "$H" in 7|19) return 1;; esac
  if [ "$H" -eq 1 ] || [ "$H" -eq 13 ]; then [ "$M" -gt 20 ] || return 1; fi
  return 0
}
# [MIN-2] cho khung gio hop le (toi da WINDOW_WAIT_MAX_S); qua tran => DUNG (truoc stop: khong doi gi tren bot)
wait_window() {
  [ "$FORCE_TIME" = 1 ] && return 0
  local W=0
  until time_ok; do
    [ "$W" -ge "$WINDOW_WAIT_MAX_S" ] && die "cho khung gio qua ${WINDOW_WAIT_MAX_S}s ($1). Bot KHONG bi dung. Chay lai sau."
    [ $((W % 300)) = 0 ] && say "cho khung gio hop le ($1; phut :10-:44, tranh 07/19h, 00:50-01:20, 12:50-13:20) — da cho ${W}s"
    sleep "$WINDOW_POLL_S"; W=$((W + WINDOW_POLL_S))
  done
  say "OK khung gio $(TZ=Asia/Ho_Chi_Minh date +%H:%M) hop le ($1)"
}

say "=== swap_v12_dry_jar TS=$TS OLD=$OLD_MD5 NEW=$NJ_MD5 DRY=$DRY $([ "$SW_JOB" = 1 ] && echo "JOB_NEN pid=$$" || echo foreground) ==="
# ---------------------------------------------------------------- 0. jar moi tren Oracle
[[ "$NJ_MD5" =~ ^[0-9a-f]{32}$ ]] || die "NJ_MD5 khong hop le"
[ "$NJ_MD5" != "$OLD_MD5" ] || die "NJ_MD5 = OLD_MD5"
[ -f "$NJ" ] || die "khong thay jar moi $NJ"
GOT=$(md5sum < "$NJ" | cut -c1-32); [ "$GOT" = "$NJ_MD5" ] || die "md5 jar moi $GOT KHAC pin $NJ_MD5"
say "OK jar moi $NJ md5=$NJ_MD5 ($(stat -c %s "$NJ") byte)"
if [ "$NEED_BIGDOWN" = 1 ]; then   # [R4u] code [BIG_DOWN-SEL] (chon coin BIG_DOWN nhu sim) phai co trong jar moi
  BD=$(python3 -I - "$NJ" <<'PYEOF'
import sys, zipfile
try:
    z = zipfile.ZipFile(sys.argv[1])
except Exception as e:
    print('KHONG_DOC_DUOC_JAR_' + type(e).__name__); sys.exit(0)
for n in sorted(z.namelist(), key=lambda n: 'DetectEntrySignal2TradeNormal' not in n):
    if n.endswith('.class') and n.startswith('com/binance/chuyennd/') and b'BIG_DOWN-SEL' in z.read(n):
        print('OK ' + n); sys.exit(0)
print('KHONG_THAY_BIG_DOWN-SEL')
PYEOF
)
  case "$BD" in OK*) say "OK jar moi co code [BIG_DOWN-SEL] (${BD#OK })";; *) die "jar moi KHONG co code [BIG_DOWN-SEL] ($BD) — NEED_BIGDOWN=1";; esac
fi

# ---------------------------------------------------------------- 1. kiem 242 CHI DOC
pre242() {
  s242in "PP='$PROC_PAT' bash -s -- $A $OLD_MD5 $NJ_MD5 $WD_PAUSE $MIN_MEM_MB $NEED_MGUARD" <<'EOF'
A=$1; OJM=$2; NJM=$3; PAUSE=$4; MINMEM=$5; MG=${6:-0}; cd "$A" || { echo "FAIL cd"; echo END_PRE; exit 0; }
N=$(pgrep -fc "$PP"); [ "$N" = 1 ] && echo "OK so_process=1" || echo "FAIL so_process=$N"
P=$(pgrep -f "$PP" | head -1)
J=$(md5sum < target/binance-java-sdk-1.2.4.jar | cut -c1-32)
if [ "$J" = "$OJM" ]; then echo "OK jar_dang_chay=$OJM (OLD)"; elif [ "$J" = "$NJM" ]; then echo "FAIL jar_dang_chay_DA_LA_moi_$NJM (da swap)"; else echo "FAIL jar_dang_chay_${J}_khac_${OJM}"; fi
E=$(tr '\0' '\n' < /proc/$P/environ 2>/dev/null)
for k in LIVE_PROFILE=c3_live LIVE_ADAPTER=dry SHADOW_NO_PUSH=true; do echo "$E" | grep -qx "$k" && echo "OK env_dang_chay $k" || echo "FAIL env_dang_chay $k"; done
grep -q '^export LIVE_ADAPTER=dry' conf/env.sh && echo "OK env.sh_dry" || echo "FAIL env.sh_khong_phai_dry"
grep -q '^export LIVE_ADAPTER=live' conf/env.sh && echo "FAIL env.sh_LIVE_ADAPTER=live"
[ "$MG" = 1 ] && grep -q '^export LIVE_MINUTE_GUARD=0' conf/env.sh && echo "FAIL env.sh_LIVE_MINUTE_GUARD=0 (jar moi can guard BAT)"
HC=$(grep -c '^export LIVE_SEED_EXCLUDE_DECISION_MIN=1' conf/env.sh); HS=$(grep -c '^export GATE_BUFFER_SEED=' conf/env.sh)
echo "INFO HAS_C11=$HC HAS_SEED_ENV=$HS"
# khong seed: env co GATE_BUFFER_SEED ma CHUA co marker .seeded => restart se NAP seed => TU CHOI
if [ "$HS" != 0 ] && [ ! -f run/gate_ratio_live.bin.seeded ]; then echo "FAIL env_co_GATE_BUFFER_SEED_chua_.seeded (restart se nap seed)"; else echo "OK khong_seed_treo"; fi
[ -s run/gate_ratio_live.bin ] && echo "OK co_gate_ratio_live.bin md5=$(md5sum < run/gate_ratio_live.bin | cut -c1-32)" || echo "FAIL thieu_run/gate_ratio_live.bin"
[ -e "$PAUSE" ] && echo "FAIL PAUSE_watchdog_dang_co $(head -c 80 "$PAUSE" 2>/dev/null)" || echo "OK khong_PAUSE"
C=$(pgrep -fc 'C3LiveCanary|UserStreamSoak'); [ "$C" = 0 ] && echo "OK khong_canary_soak" || echo "FAIL canary/soak_dang_chay=$C"
M=$(awk '/MemAvailable/{print int($2/1024)}' /proc/meminfo); [ "$M" -ge "$MINMEM" ] && echo "OK mem_avail=${M}MB" || echo "FAIL mem_avail=${M}MB < $MINMEM"
F=$(df -Pk . | awk 'NR==2{print $4}'); [ "${F:-0}" -gt 1048576 ] && echo "OK dia_trong=${F}k" || echo "FAIL dia_trong=${F}k"
L0=$(tail -c 20000000 logs/full.log 2>/dev/null | grep -a '\[LEGACY\] managed' | tail -1 | grep -aoE 'managed [0-9]+' | awk '{print $2}')
[ -n "$L0" ] && echo "OK LEGACY_N=$L0" || echo "FAIL khong_doc_duoc_LEGACY_managed"
grep -q '"latch":"NONE"' run/killsw_latch.json 2>/dev/null && echo "OK latch_NONE" || echo "FAIL latch_khac_NONE"
[ -e run/KILL_SWITCH ] && echo "INFO co_run/KILL_SWITCH (dry: giu nguyen)"
echo END_PRE
EOF
}
PRE=$(pre242) || die "ssh toi 242 loi"
echo "$PRE"
echo "$PRE" | grep -qx END_PRE || die "kiem 242 khong tron ven (ssh dut?)"
echo "$PRE" | grep -q '^FAIL' && die "kiem 242 co muc FAIL (xem tren)"
L0=$(echo "$PRE" | sed -n 's/^OK LEGACY_N=//p'); HC=$(echo "$PRE" | sed -n 's/^INFO HAS_C11=\([0-9]*\).*/\1/p')
GR0=$(echo "$PRE" | sed -n 's/^OK co_gate_ratio_live.bin md5=//p')

ENV_ADD="# [v1.2 swap_v12_dry_jar $TS] jar ${OLD_TAG} -> ${NEW_TAG} ($NJ_MD5), khong seed"
[ "${HC:-0}" = 0 ] && ENV_ADD="$ENV_ADD
export LIVE_SEED_EXCLUDE_DECISION_MIN=1"
[ -n "$EXCL_HELD" ] && ENV_ADD="$ENV_ADD
export C3_EXCLUDE_LEGACY_HELD=$EXCL_HELD"
NADD=$(echo "$ENV_ADD" | wc -l)
say "--- C3_EXCLUDE_LEGACY_HELD (C3_ACCOUNT=$C3_ACCOUNT, jar $NEW_TAG): $([ -n "$EXCL_HELD" ] && echo "=$EXCL_HELD (dong cu trong env.sh bo)" || echo 'GO dong khoi env.sh (jar khong dung key)')"
say "--- se THEM vao $A/conf/env.sh ($NADD dong):"; echo "$ENV_ADD" | sed 's/^/   + /'
say "--- se thay $A/target/binance-java-sdk-1.2.4.jar: $OLD_MD5 (${OLD_TAG}, backup .bak_swap_$TS) -> $NJ_MD5 (${NEW_TAG})"
say "--- hau kiem: jar=$NJ_MD5, env dry + C11=1, [UNIVERSE-A1] PREMARKET=, [GATE-PRE] premarket_bo=, LEGACY_QUEUE_LIVE_BLOCK=true, LEGACY $L0, latch NONE, 0 KHAN$([ "$NEED_MGUARD" = 1 ] && echo ', [MINUTE-GUARD] BAT')"
if [ "$SW_JOB" != 1 ]; then
  if [ "$DRY" = 1 ]; then say "DRY=1: dung o day, KHONG ghi gi len 242. (DRY PASS)"; exit 0; fi
  # ------------------------------------------------------------ YES 1 lan -> JOB NEN (setsid nohup) + tail log
  lock_take || die "dang co 1 job swap_v12_dry_jar khac chay (pid $(cat "$LOCKD/pid" 2>/dev/null), $LOCKD). Khong doi gi."
  trap 'rm -rf "$LOCKD"' EXIT
  say ">>> THAY JAR v_t_m dry ${OLD_TAG} -> ${NEW_TAG} (restart). JOB NEN tren Oracle: cho khung gio hop le ke tiep (toi da ${WINDOW_WAIT_MAX_S}s),"
  say "    dong terminal / rot ssh KHONG dung job. LEGACY ngung quan ly ~1-1,5' (SL tren san giu nguyen). Go YES de tiep tuc:"
  read -r ANS || ANS=""
  [ "$ANS" = YES ] || { say "Huy. Khong doi gi."; exit 0; }
  JOBLOG=$LOGDIR/swap_v12_dry_jar_${TS}_job_$$.log
  YESF=$LOCKD/yes
  ( umask 077; echo "$TS" > "$YESF" ) || die "khong ghi duoc $YESF"
  : > "$JOBLOG"
  SW_JOB=1 SW_TS=$TS SW_JOBLOG=$JOBLOG SW_YES_FILE=$YESF setsid nohup bash "$SELF" >> "$JOBLOG" 2>&1 < /dev/null &
  BG=$!
  trap - EXIT   # khoa giao cho job
  say "job NEN pid=$BG job_log=$JOBLOG"
  say "Dong terminal / mat ket noi KHONG dung job. Xem tien do: tail -f $JOBLOG   (ket qua gui Telegram)"
  tail --pid="$BG" -n +1 -f "$JOBLOG" &
  TP=$!
  wait "$BG"; RC=$?
  wait "$TP" 2>/dev/null
  [ "$(cat "$LOCKD/pid" 2>/dev/null)" = "$$" ] && rm -rf "$LOCKD"   # job chet truoc khi nhan khoa
  say "job ket thuc rc=$RC (0 XONG | 1 DUNG/da rollback | 2 ROLLBACK LOI: PAUSE con). Log job: $JOBLOG"
  exit "$RC"
fi
# ================================================================ JOB NEN (SW_JOB=1)
[ "${SW_YES_FILE:-}" = "$LOCKD/yes" ] && [ -f "$SW_YES_FILE" ] && [ "$(cat "$SW_YES_FILE" 2>/dev/null)" = "$TS" ] \
  || die "job nen KHONG co xac nhan YES tu foreground (SW_YES_FILE) => TU CHOI, khong doi gi"
echo $$ > "$LOCKD/pid"
rm -f "$SW_YES_FILE"
trap 'rm -rf "$LOCKD"' EXIT
tg "[swap jar dry] job NEN bat dau TS=$TS: cho khung gio -> kiem 242 lai -> swap. Log $LOG"
wait_window "truoc kiem lai"
# kiem 242 LAI (trang thai co the doi trong luc cho)
PRE=$(pre242) || die "ssh toi 242 loi (kiem lai)"
echo "$PRE" | sed 's/^/   lan 2: /'
echo "$PRE" | grep -qx END_PRE || die "kiem 242 lan 2 khong tron ven (ssh dut?)"
echo "$PRE" | grep -q '^FAIL' && die "kiem 242 lan 2 co muc FAIL (xem tren)"
[ "$(echo "$PRE" | sed -n 's/^INFO HAS_C11=\([0-9]*\).*/\1/p')" = "${HC:-0}" ] || die "trang thai C11 tren 242 doi trong luc cho => chay lai"
L0=$(echo "$PRE" | sed -n 's/^OK LEGACY_N=//p'); GR0=$(echo "$PRE" | sed -n 's/^OK co_gate_ratio_live.bin md5=//p')

# ---------------------------------------------------------------- 2. chep jar
RJ=$A/target/binance-java-sdk-1.2.4.jar.v12swap_$TS
$SCP_242 "$NJ" "${RHOST}$RJ" || die "chep jar len 242 loi"
RM=$(s242 "md5sum < $RJ | cut -c1-32") || die "ssh kiem md5 jar loi"
[ "$RM" = "$NJ_MD5" ] || die "md5 jar tren 242 $RM KHAC $NJ_MD5"
say "OK jar moi tren 242 md5=$RM ($RJ)"

# ---------------------------------------------------------------- 3. env + PAUSE + stop + backup + cai jar + start
# [MIN-2] kiem khung gio NGAY TRUOC stop (scp co the lau); ngoai khung => cho khung ke (cung tran)
wait_window "ngay truoc stop"
PAUSE_TOK="C3SWAP_V12 TS=$TS pid=$$"
on_sig() {
  trap - INT TERM HUP
  s242 "grep -q '^$PAUSE_TOK ' $WD_PAUSE 2>/dev/null && rm -f $WD_PAUSE" >/dev/null 2>&1
  say "BI DUNG (tin hieu). PAUSE cua lan nay da go (neu con). KIEM: bash $(cd "$(dirname "$0")" && pwd)/c3live_status.sh"
  tg "[swap jar dry] TS=$TS bi DUNG giua chung. Kiem c3live_status.sh. Log $LOG"; exit 130
}
trap on_sig INT TERM HUP
EB=$(echo "$ENV_ADD" | base64 -w0)
RS=$(s242in "PP='$PROC_PAT' bash -s -- $A $TS $EB $NADD $WD_PAUSE $WD_PAUSE_MAX_S $$ $OLD_MD5 $NJ_MD5 ${EXCL_HELD:--}" <<'EOF'
A=$1; TS=$2; EB=$3; NADD=$4; PAUSE=$5; MAXS=$6; JP=$7; OJM=$8; NJM=$9; EXN=${10:--}; cd "$A" || { echo "FAIL cd"; exit 0; }
J=target/binance-java-sdk-1.2.4.jar; JN=$J.v12swap_$TS; JB=$J.bak_swap_$TS
[ "$(md5sum < $JN | cut -c1-32)" = "$NJM" ] || { echo "FAIL jar_moi_tren_242_sai_md5"; exit 0; }
\cp -fp conf/env.sh conf/env.sh.bak_swap_$TS || { echo "FAIL backup_env"; exit 0; }
sed -i '/^export C3_EXCLUDE_LEGACY_HELD=/d' conf/env.sh   # [R4u2] bo dong cu; them lai (neu co gia tri) qua ENV_ADD
echo "$EB" | base64 -d >> conf/env.sh
D=$(( $(wc -l < conf/env.sh) - $(wc -l < conf/env.sh.bak_swap_$TS) + $(grep -c '^export C3_EXCLUDE_LEGACY_HELD=' conf/env.sh.bak_swap_$TS) ))   # [R4u2] so dong them (tru dong cu da bo)
tail -n "$NADD" conf/env.sh | cmp -s - <(echo "$EB" | base64 -d) || D=x
[ "$D" = "$NADD" ] && echo "OK env_them_${D}_dong" || { \cp -f conf/env.sh.bak_swap_$TS conf/env.sh; echo "FAIL env_diff=$D (da khoi phuc)"; exit 0; }
EXC=$(grep -c '^export C3_EXCLUDE_LEGACY_HELD=' conf/env.sh); EXW=1; [ "$EXN" = - ] && EXW=0
{ [ "$EXC" = "$EXW" ] && { [ "$EXN" = - ] || grep -qx "export C3_EXCLUDE_LEGACY_HELD=$EXN" conf/env.sh; }; } && echo "OK env.sh C3_EXCLUDE_LEGACY_HELD=${EXN} ($EXC dong)" \
  || { \cp -f conf/env.sh.bak_swap_$TS conf/env.sh; echo "FAIL env.sh_C3_EXCLUDE_LEGACY_HELD (co $EXC dong, can $EXW) (da khoi phuc)"; exit 0; }
TOK="C3SWAP_V12 TS=$TS pid=$JP"
mkdir -p "$(dirname "$PAUSE")" 2>/dev/null; echo "$TOK t=$(date +%s)" > "$PAUSE" && echo "OK watchdog_PAUSE token='$TOK'" || echo "WARN khong_tao_duoc_PAUSE"
setsid nohup bash -c "sleep $MAXS; grep -q '^$TOK ' '$PAUSE' 2>/dev/null && rm -f '$PAUSE'" > /dev/null 2>&1 < /dev/null &
echo "LEGACY_TRUOC_STOP=$(tail -c 20000000 logs/full.log 2>/dev/null | grep -a '\[LEGACY\] managed' | tail -1 | grep -aoE 'managed [0-9]+' | awk '{print $2}')"   # [R4r] chup NGAY truoc stop
bin/daemon.sh stop
for i in $(seq 1 30); do pgrep -f "$PP" >/dev/null || break; sleep 2; done
if pgrep -f "$PP" >/dev/null; then \cp -f conf/env.sh.bak_swap_$TS conf/env.sh; echo "FAIL van_con_process_sau_stop (env khoi phuc)"; exit 0; fi
echo "OK da_stop"
{ \cp -fp $J $JB && [ "$(md5sum < $JB | cut -c1-32)" = "$OJM" ] && echo "$OJM" > $JB.md5; } && echo "OK backup_jar md5=$OJM ($JB)" || echo "FAIL backup_jar"
GR=run/gate_ratio_live.bin; GB=$GR.bak_swap_$TS
{ \cp -fp "$GR" "$GB" && GM=$(md5sum < "$GB" | cut -c1-32) && [ "$GM" = "$(md5sum < "$GR" | cut -c1-32)" ] && echo "$GM" > "$GB.md5"; } \
  && echo "OK backup_gate_ratio md5=$GM" || echo "FAIL backup_gate_ratio"
if [ -f $JB.md5 ]; then
  \cp -f $JN $J && [ "$(md5sum < $J | cut -c1-32)" = "$NJM" ] && echo "OK jar_da_thay md5=$NJM" || echo "FAIL jar_thay_sai"
fi
L=logs/full.log; echo "START_LINE=$(( $(wc -l < $L 2>/dev/null || echo 0) + 1 ))"
bin/daemon.sh start
sleep 8
P=$(pgrep -f "$PP" | head -1)
[ -n "$P" ] && echo "OK started pid=$P lstart=$(ps -o lstart= -p $P)" || echo "FAIL khong_thay_process_sau_start"
[ -n "$P" ] && echo "START_MS=$(( ($(date +%s) - $(ps -o etimes= -p $P | tr -d ' ')) * 1000 ))"
EOF
) || RS="FAIL ssh_restart_loi"
echo "$RS"

autorb() {
  say "$1 => ROLLBACK TU DONG (jar ${OLD_TAG} + env.sh + gate_ratio_live.bin backup TS=$TS)"
  local R
  R=$(s242in "PP='$PROC_PAT' bash -s -- $A $TS $WD_PAUSE $OLD_MD5" <<'EOF'
A=$1; TS=$2; PAUSE=$3; OJM=$4; cd "$A" || { echo "FAIL cd"; echo END_RB; exit 0; }
[ -f conf/env.sh.bak_swap_$TS ] || { echo "FAIL thieu_backup_env"; echo END_RB; exit 0; }
J=target/binance-java-sdk-1.2.4.jar; JB=$J.bak_swap_$TS
bin/daemon.sh stop
for i in $(seq 1 30); do pgrep -f "$PP" >/dev/null || break; sleep 2; done
pgrep -f "$PP" >/dev/null && { echo "FAIL van_con_process"; echo END_RB; exit 0; }
\cp -f conf/env.sh.bak_swap_$TS conf/env.sh && echo "OK env_khoi_phuc"
if [ -f $JB.md5 ]; then
  [ "$(md5sum < $J | cut -c1-32)" = "$OJM" ] || \cp -f $JB $J
  [ "$(md5sum < $J | cut -c1-32)" = "$OJM" ] && echo "OK jar_khoi_phuc md5=$OJM" || echo "FAIL jar_khoi_phuc"
else
  [ "$(md5sum < $J | cut -c1-32)" = "$OJM" ] && echo "OK jar_chua_doi md5=$OJM" || echo "FAIL jar_khac_OLD_va_khong_co_backup"
fi
GR=run/gate_ratio_live.bin; GB=$GR.bak_swap_$TS
if [ -f "$GB.md5" ]; then
  [ ! -f "$GR" ] || mv -f "$GR" "$GR.rb_swap_$TS"
  \cp -fp "$GB" "$GR"; [ "$(md5sum < "$GR" | cut -c1-32)" = "$(cat "$GB.md5")" ] && echo "OK gate_ratio_khoi_phuc md5=$(cat "$GB.md5")" || echo "FAIL gate_ratio_khoi_phuc"
else
  echo "INFO gate_ratio_khong_co_backup (chua toi buoc stop) => giu nguyen"
fi
bin/daemon.sh start; sleep 8
P=$(pgrep -f "$PP" | head -1)
[ -n "$P" ] && echo "OK started pid=$P" || echo "FAIL khong_thay_process"
E=$(tr '\0' '\n' < /proc/$P/environ 2>/dev/null)
echo "$E" | grep -qx LIVE_ADAPTER=dry && echo "OK env LIVE_ADAPTER=dry" || echo "FAIL env LIVE_ADAPTER"
grep -q "^C3SWAP_V12 TS=$TS " "$PAUSE" 2>/dev/null && rm -f "$PAUSE"
[ -e "$PAUSE" ] && echo "WARN PAUSE_con (token khac)" || echo "OK PAUSE_go"
echo END_RB
EOF
) || R="FAIL ssh_rollback_loi"
  echo "$R"
  if echo "$R" | grep -qx END_RB && ! echo "$R" | grep -q '^FAIL'; then
    say "SWAP FAIL ($1). Da ROLLBACK xong: dry ${OLD_TAG} chay lai nhu truoc."
    tg "[swap jar dry] FAIL TS=$TS: $1 => ROLLBACK TU DONG ve ${OLD_TAG} XONG. Log $LOG"
    exit 1
  fi
  local M="PAUSE còn — kiem tay: bash $(cd "$(dirname "$0")" && pwd)/c3live_status.sh ; backup $A/conf/env.sh.bak_swap_$TS + $A/target/binance-java-sdk-1.2.4.jar.bak_swap_$TS"
  say "SWAP FAIL ($1). ROLLBACK TU DONG LOI. $M"
  tg "[swap jar dry] KHAN TS=$TS: swap FAIL ($1) VA ROLLBACK LOI. $M | log $LOG"
  exit 2
}
if echo "$RS" | grep -q '^FAIL'; then
  if echo "$RS" | grep -q '^OK da_stop'; then autorb "swap co FAIL"; fi
  s242 "grep -q '^$PAUSE_TOK ' $WD_PAUSE 2>/dev/null && rm -f $WD_PAUSE" >/dev/null 2>&1
  die "buoc env/stop FAIL truoc khi dung bot (env da khoi phuc neu da sua). Xem tren."
fi
SL=$(echo "$RS" | sed -n 's/^START_LINE=//p'); SL=${SL:-1}
LB=$(echo "$RS" | sed -n 's/^LEGACY_TRUOC_STOP=\([0-9][0-9]*\)$/\1/p' | tail -1)   # [R4r] so LEGACY NGAY truoc stop (khong so cung)
if [ -n "$LB" ]; then [ "$LB" != "${L0:-}" ] && say "INFO LEGACY truoc stop=$LB (luc kiem truoc: ${L0:-?}) => hau kiem so voi $LB"; L0=$LB; fi

# ---------------------------------------------------------------- 4. hau kiem
CHK() {
  s242in "PP='$PROC_PAT' bash -s -- $A $SL $NJ_MD5 ${L0:-0} $NEED_MGUARD ${EXCL_HELD:--} $C3_ACCOUNT" <<'EOF'
A=$1; SL=$2; NJM=$3; L0=$4; MG=${5:-0}; EX=${6:--}; ACC=${7:-SUB}; cd "$A"; L=logs/full.log
T() { tail -n +$SL $L 2>/dev/null | grep -a -c "$1"; }
P=$(pgrep -f "$PP" | head -1)
[ "$(pgrep -fc "$PP")" = 1 ] && echo "OK 1_process" || echo "FAIL so_process"
[ "$(md5sum < target/binance-java-sdk-1.2.4.jar | cut -c1-32)" = "$NJM" ] && echo "OK jar=$NJM" || echo "FAIL jar_md5"
E=$(tr '\0' '\n' < /proc/$P/environ 2>/dev/null)
for k in LIVE_PROFILE=c3_live LIVE_ADAPTER=dry SHADOW_NO_PUSH=true LIVE_SEED_EXCLUDE_DECISION_MIN=1; do
  echo "$E" | grep -qx "$k" && echo "OK env $k" || echo "FAIL env $k"
done
if [ "$EX" = - ]; then echo "$E" | grep -q '^C3_EXCLUDE_LEGACY_HELD=' && echo "FAIL env C3_EXCLUDE_LEGACY_HELD van con (jar nay khong dung key)" || echo "OK env khong_co_C3_EXCLUDE_LEGACY_HELD"
else echo "$E" | grep -qx "C3_EXCLUDE_LEGACY_HELD=$EX" && echo "OK env C3_EXCLUDE_LEGACY_HELD=$EX" || echo "FAIL env C3_EXCLUDE_LEGACY_HELD (can $EX; co: $(echo "$E" | grep '^C3_EXCLUDE_LEGACY_HELD=' | tail -1))"; fi
[ "$(T 'LIVE_SEED_EXCLUDE_DECISION_MIN=0 => race')" = 0 ] && echo "OK C11_khong_canh_bao_race" || echo "FAIL C11_van_canh_bao_race"
if [ "$ACC" = SUB ]; then [ "$(T '\[C3-EXCL-FORCE\]')" = 0 ] && echo "OK 0_C3-EXCL-FORCE" || echo "FAIL C3-EXCL-FORCE (SUB: jar ep C3_EXCLUDE_LEGACY_HELD=true => env key sai)"; fi
[ "$(T '\[GATE-SEED\] nap seed')" = 0 ] && echo "OK khong_nap_seed" || echo "FAIL co_nap_seed"
[ "$(T '\[UNIVERSE-A1\] BAT .*PREMARKET=')" -ge 1 ] && echo "OK UNIVERSE-A1_$(tail -n +$SL $L | grep -a '\[UNIVERSE-A1\] BAT' | tail -1 | grep -aoE 'PREMARKET=[0-9]+')" || echo "WAIT UNIVERSE-A1_PREMARKET"
[ "$(T '\[GATE-PRE\] .*premarket_bo=')" -ge 1 ] && echo "OK GATE-PRE_$(tail -n +$SL $L | grep -a '\[GATE-PRE\] .*premarket_bo=' | tail -1 | grep -aoE 'premarket_bo=[0-9]+')" || echo "WAIT GATE-PRE_premarket_bo"
[ "$(T 'LIVE_PROFILE=c3_live\] BAT.*LEGACY_QUEUE_LIVE_BLOCK=true')" -ge 1 ] && echo "OK LEGACY_QUEUE_LIVE_BLOCK=true" || echo "WAIT LEGACY_QUEUE_LIVE_BLOCK"
[ "$(T '\[KILLSW\] LATCH')" = 0 ] && grep -q '"latch":"NONE"' run/killsw_latch.json 2>/dev/null && echo "OK latch_NONE" || echo "FAIL latch"
K=$(tail -n +$SL $L 2>/dev/null | grep -a 'KHAN' | grep -av 'DRY tren tai khoan chinh' | head -1 | cut -c1-160)
[ -z "$K" ] && echo "OK 0_KHAN" || echo "FAIL KHAN: $K"
[ "$(T 'KHONG tao duoc runtime')" = 0 ] && echo "OK runtime" || echo "FAIL KHONG_tao_duoc_runtime"
LN=$(tail -n +$SL $L 2>/dev/null | grep -a '\[LEGACY\] managed' | tail -1 | grep -aoE 'managed [0-9]+' | awk '{print $2}')
if [ -z "$LN" ]; then echo "WAIT LEGACY_chua_co"; elif [ "$LN" = "$L0" ]; then echo "OK LEGACY_managed=$LN"; elif [ "$LN" -lt "$L0" ] 2>/dev/null; then echo "WARN LEGACY_managed=$LN < truoc stop $L0 (dong tu nhien luc dung? kiem tay)"; else echo "FAIL LEGACY_managed=$LN > truoc stop $L0 (TANG)"; fi
if [ "$MG" = 1 ]; then   # [R4r] guard do du phut
  if [ "$(T '\[MINUTE-GUARD\] TAT')" -ge 1 ]; then echo "FAIL MINUTE-GUARD_TAT"
  elif [ "$(T '\[MINUTE-GUARD\] BAT')" -ge 1 ]; then echo "OK MINUTE-GUARD_BAT"; else echo "WAIT MINUTE-GUARD_BAT"; fi
fi
[ "$(T '\[GATE\] scale')" -ge 1 ] && echo "OK GATE_tick_chay" || echo "WAIT GATE_tick_chua_co"
echo END_CHK
EOF
}
RESULT=""
for r in $(seq 1 "$POST_ROUNDS"); do
  sleep "$POST_WAIT_S"
  RESULT=$(CHK) || RESULT="$RESULT
FAIL kiem_sau_start_ssh"
  echo "$RESULT" | grep -qx END_CHK || RESULT="$RESULT
FAIL kiem_sau_start_khong_tron_ven"
  say "--- hau kiem lan $r/$POST_ROUNDS"; echo "$RESULT"
  echo "$RESULT" | grep -q '^FAIL' && break
  echo "$RESULT" | grep -q '^WAIT' || break
done
if echo "$RESULT" | grep -q '^FAIL\|^WAIT'; then
  autorb "hau kiem KHONG DAT ($(echo "$RESULT" | grep '^FAIL\|^WAIT' | tr '\n' ' ' | cut -c1-200))"
fi
trap - INT TERM HUP
if ! s242 "grep -q '^$PAUSE_TOK ' $WD_PAUSE 2>/dev/null && rm -f $WD_PAUSE; [ ! -e $WD_PAUSE ]"; then
  say "XONG nhung PAUSE còn (ssh?) — tu go sau ${WD_PAUSE_MAX_S}s neu van token lan nay"
fi
# [R4q ADD11] dang ky jar cho harness parity (CHI khi hau kiem DAT); loi => WARN, KHONG rollback
STMS=$(echo "$RS" | sed -n 's/^START_MS=//p' | tail -1)
if [[ "$STMS" =~ ^[0-9]{13}$ ]]; then
  SF=$LOGDIR/swap_start_${NEW_TAG}_$TS.txt
  echo "tag=${NEW_TAG} md5=$NJ_MD5 start_ms=$STMS start=$(TZ=Asia/Ho_Chi_Minh date -d @$((STMS / 1000)) '+%F %T') ts=$TS" > "$SF"
  say "START_MS JVM ${NEW_TAG} (gio start THAT) = $STMS ($(TZ=Asia/Ho_Chi_Minh date -d @$((STMS / 1000)) '+%F %T') +07) — luu $SF"
  GM=$(python3 -I - "$GMICRO_TARGET" "${NEW_TAG}" "$NJ_MD5" "$STMS" <<'PYEOF'
import json, os, shutil, sys, time
p, tag, md5, ms = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
if not os.path.exists(p):
    print('WARN khong co %s — khong ghi (parity tao file)' % p); sys.exit(0)
try:
    cur = json.load(open(p))
except Exception as e:
    print('WARN file hong %s' % type(e).__name__); sys.exit(0)
if cur.get('target_jar') != tag or cur.get('target_md5') != md5:
    print('WARN file tro target_jar=%s target_md5=%s (khac %s %s) — KHONG ghi; parity cap nhat roi dien smoke_start_ms=%d' % (cur.get('target_jar'), cur.get('target_md5'), tag, md5, ms)); sys.exit(0)
shutil.copy2(p, '%s.bak_%d' % (p, int(time.time())))
cur['smoke_start_ms'] = ms
json.dump(cur, open(p + '.tmp', 'w')); os.replace(p + '.tmp', p)
print('OK smoke_start_ms=%d' % ms)
PYEOF
)
  say "gmicro_target.json ($GMICRO_TARGET): $GM"
  case "$GM" in OK*) ;; *) tg "[swap jar dry] WARN TS=$TS: gmicro_target.json $GM";; esac
  say "--- dang ky jar parity: $REG_JAR_SH ${NEW_TAG} $NJ $NJ_MD5 $STMS 1"
  timeout "$REG_TIMEOUT_S" bash "$REG_JAR_SH" ${NEW_TAG} "$NJ" "$NJ_MD5" "$STMS" 1; RRC=$?
  if [ "$RRC" = 0 ]; then say "OK dang ky jar parity ${NEW_TAG} start_ms=$STMS"
  else say "WARN dang ky jar parity LOI rc=$RRC (dry ${NEW_TAG} GIU nguyen) — chay tay: bash $REG_JAR_SH ${NEW_TAG} $NJ $NJ_MD5 $STMS 1"
       tg "[swap jar dry] WARN TS=$TS: register_jar.sh rc=$RRC — chay tay: bash $REG_JAR_SH ${NEW_TAG} $NJ $NJ_MD5 $STMS 1"; fi
else
  say "WARN khong lay duoc start_ms JVM ${NEW_TAG} ('$STMS') => KHONG dang ky jar parity — MASTER chay tay register_jar.sh"
  tg "[swap jar dry] WARN TS=$TS: thieu start_ms => chua dang ky jar parity"
fi
say "=== XONG: dry chay ${NEW_TAG} $NJ_MD5. $(echo "$RS" | grep '^OK started') | jar cu backup target/*.bak_swap_$TS, gate_ratio truoc=$GR0"
say "Ngay hom nay = XAM (ADD6/ADD10). Dry ${NEW_TAG} smoke >= 24 h truoc micro (A1 R4PQ). Log: $LOG"
tg "[swap jar dry] XONG TS=$TS ${OLD_TAG} -> ${NEW_TAG} $NJ_MD5 (C11=1, khong seed). Log $LOG"
exit 0
