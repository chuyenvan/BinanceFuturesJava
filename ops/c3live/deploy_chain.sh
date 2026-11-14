#!/usr/bin/env bash
# =============================================================================
# deploy_chain.sh — [V12 R4t] CHUOI deploy nhieu buoc = 1 LENH (Oracle): tu cho, tu kiem, tu chay buoc ke. Owner KHONG canh gio.
#   bash ~/claude_master/deploy/deploy_chain.sh qf4_then_r4t          # in ke hoach + trang thai, go YES 1 lan => JOB NEN
#   DRY=1 bash ~/claude_master/deploy/deploy_chain.sh qf4_then_r4t    # CHI DOC: ke hoach + trang thai tung buoc (+ DRY=1 cua buoc)
#   bash ~/claude_master/deploy/deploy_chain.sh status                # job dang o buoc nao + 25 dong log cuoi
#   bash ~/claude_master/deploy/deploy_chain.sh stop                  # dung chuoi TRUOC buoc ke (buoc dang chay chay tron, co rollback rieng)
# Preset qf4_then_r4t:
#   1. qf4 : collectData jar QF4 (deploy_ingest_qf4.sh). XONG neu jar ingestor dang chay = JAR_MD5 cua script. Dang co job QF4 chay
#            (owner chay tay) => CHO no ket thuc (khong chay song song); ket thuc ma khong XONG => DUNG CHUOI + KHAN.
#   2. r4t : v_t_m jar r4t (swap_v12_dry_jar.sh, NJ_MD5 pin). XONG neu jar v_t_m = NJ_MD5 va 1 process.
#   (preset cu: chi chay khi swap_v12_dry_jar.sh co NEW_TAG mac dinh = r4t; nay mac dinh r4u3 => TU CHOI)
# Preset swap_r4u3 [V12 R4u]: 1 buoc r4u3 = swap_v12_dry_jar.sh mac dinh r4t -> r4u3 (NJ_MD5 pin 15f9e14f).
#   Truoc buoc: jar (Oracle) co code [BIG_DOWN-SEL]; chup LEGACY managed. Ngay sau swap XONG: ghi gio start THAT cua r4u3 vao
#   ~/claude_master/parity_v12w/gmicro_target.json (ADD19 §1: target_jar/target_md5/smoke_start_ms; md5/ten khac => KHAN, khong ghi).
#   Hau kiem STABLE_S (900 s = 15'): 1 process md5 r4u3, 0 ERROR + 0 KHAN tu JVM moi, latch NONE, [MINUTE-GUARD] BAT,
#   MemAvailable >= MIN_MEM_MB, LEGACY managed = chup truoc swap (giam = WARN, tang = FAIL). Loi => KHAN + lenh rollback ve r4t.
# Preset fin_pair [FIN 2026-11-14, phuong an A] (TRUOC: owner chay set_telegram_env_242.sh; MASTER tro gmicro_target.json sang r4u3fin):
#   1. qf4 (= ingestor fin): deploy_ingest_fin.sh (QF4b 15f47509 -> jar qf/fin-bin; hau kiem rieng [KLINE-FIN] BAT + env token).
#   2. r4u3fin: swap_v12_dry_jar.sh mac dinh r4u3 -> r4u3fin (NEED_FIN=1: kiem ingestor fin dang chay + env token TRUOC khi dung bot).
#   Hau kiem r4u3fin = nhu r4u3 + [MINUTE-FIN] BAT, 0 ly_do=FIN_KHONG_BIN. Rollback: v_t_m ve r4u3 TRUOC, roi ingestor ve QF4b.
# Sau MOI buoc: chi di tiep khi rc=0 VA hau kiem on dinh >= STABLE_S (900 s) lien tuc:
#   collectData (ingqf4_check_remote.sh): 0 FAIL, khong WAIT — KLINE-COVER du, 0 http429/418, price_gap/price_age OK, 0 ban/restart;
#   v_t_m: 1 process, 0 dong ERROR tu moc buoc, latch NONE (+ [MINUTE-GUARD] BAT sau r4t). WAIT keo dai > STABLE_MAX_S => FAIL.
# Buoc ke chi bat dau trong KHUNG GIO hop le ke tiep (:10-:39 de con >= 5' trong khung :10-:44; tranh gio 07/19, 00:50-01:20,
#   12:50-13:20). Buoc FAIL / rollback / hau kiem TRUOT => DUNG CA CHUOI + Telegram KHAN; khong chay buoc sau.
# Idempotent: buoc da XONG (md5 tren 242) => bo qua (van kiem on dinh truoc buoc ke).
# [A1 CHAIN MAJ-C] Luc YES: chep script con (+ register_jar) vao .deploy_chain/jobs/<TS>_<preset>/ + kiem md5 PIN_* (ban A1 duyet);
#   job CHI chay ban chep (kiem lai truoc moi buoc); lech => TU CHOI. Thu muc job (chain.log, steps.txt, md5.txt) giu lau dai.
#   stop/FAIL giua hau kiem => KHAN "jar moi chua xac nhan on dinh" + lenh rollback. Kiem "khong job khac" + chay buoc DUOI flock $DLOCK.
# Ma thoat job: 0 XONG ca chuoi | 1 DUNG (FAIL/stop/het gio). Bien test: SSH_242 APP_DIR ING_DIR QF4_SH SWAP_SH CHECK_R CHAIN_DIR
#   STABLE_S STABLE_MAX_S CHK_POLL_S WAIT_RUNNING_MAX_S WINDOW_WAIT_MAX_S FORCE_TIME TIME_OK_FILE DEPLOY_TG_SINK QF4_PAT
# =============================================================================
set -uo pipefail
D=${CHAIN_DIR:-/home/ubuntu/claude_master/deploy}
C3=${C3_OPS:-/home/ubuntu/claude_master/v12/c3live/ops/c3live}
SSH_242=${SSH_242:-"ssh -p 2222 -o BatchMode=yes -o ConnectTimeout=20 -o ServerAliveInterval=10 -o ServerAliveCountMax=6 -i /home/ubuntu/.ssh/id_rsa_chuyennd root@103.157.218.242"}
APP_DIR=${APP_DIR:-/home/chuyennd/java/v_t_m}
ING_DIR=${ING_DIR:-/home/chuyennd/java/collectData}
QF4_SH=${QF4_SH:-$D/deploy_ingest_qf4.sh}
SWAP_SH=${SWAP_SH:-$C3/swap_v12_dry_jar.sh}
CHECK_R=${CHECK_R:-$D/ingqf4_check_remote.sh}
QF4_PAT=${QF4_PAT:-deploy_ingest_qf4.sh}
STABLE_S=${STABLE_S:-900}
STABLE_MAX_S=${STABLE_MAX_S:-3600}
CHK_POLL_S=${CHK_POLL_S:-60}
WAIT_RUNNING_MAX_S=${WAIT_RUNNING_MAX_S:-10800}
WINDOW_WAIT_MAX_S=${WINDOW_WAIT_MAX_S:-10800}
FORCE_TIME=${FORCE_TIME:-0}
DRY=${DRY:-0}
# [A1 CHAIN MAJ-C] pin md5 script con = ban A1 da duyet. Luc YES: chep vao thu muc job + kiem md5; CHI chay ban chep; lech => KHONG chay.
REG_JAR_SH=${REG_JAR_SH:-/home/ubuntu/claude_master/vz_e1_wt/research/parity_v12/sh/register_jar.sh}
PIN_QF4_SH=${PIN_QF4_SH:-880531e5a4545950a02b773b83880432}     # deploy_ingest_qf4.sh QF4b (tu pin md5 ingqf_restart/ingqf4_check remote)
PIN_CHECK_R=${PIN_CHECK_R:-e8d87135085e81f48e8d86aef56bfbdc}   # ingqf4_check_remote.sh
PIN_SWAP_SH=${PIN_SWAP_SH:-a04ee5f6a905b4926b3b6e0efcb39e53}   # swap_v12_dry_jar.sh [R4u2] (mac dinh r4t -> r4u3 + C3_EXCLUDE_LEGACY_HELD; truoc 09ae28e8 r4q -> r4t)
PIN_REG=${PIN_REG:-7d9b2ee0285bdaec05574de86764e73f}           # register_jar.sh (swap goi sau hau kiem DAT)
R4Q_JAR=${R4Q_JAR:-/home/ubuntu/claude_master/v12/jar/binance-java-sdk-1.2.4.jar_v12_r4q}
R4Q_MD5=${R4Q_MD5:-8c81e6b560b61e7d43ca32c4a50ec926}
R4T_JAR=${R4T_JAR:-/home/ubuntu/claude_master/v12/jar/binance-java-sdk-1.2.4.jar_v12_r4t}   # [R4u] dich rollback cua buoc r4u3
R4T_PIN_MD5=${R4T_PIN_MD5:-694b29b2e5be32b537ca6c38557e64db}
R4U3_JAR=${R4U3_JAR:-/home/ubuntu/claude_master/v12/jar/binance-java-sdk-1.2.4.jar_v12_r4u3}   # [FIN] dich rollback cua buoc r4u3fin
R4U3_PIN_MD5=${R4U3_PIN_MD5:-b1f12c3eeaeed72cb17afbe5b4da06cf}
QF4_LOGPFX=${QF4_LOGPFX:-deploy_ingest_qf4}   # [FIN] tien to log script ingestor (fin_pair: deploy_ingest_fin)
QF4_RB_SH=${QF4_RB_SH:-rollback_ingest_qf4.sh}
GMICRO_TARGET=${GMICRO_TARGET:-/home/ubuntu/claude_master/parity_v12w/gmicro_target.json}   # [ADD19] target_jar/target_md5/smoke_start_ms
JARS_JSON=${JARS_JSON:-/home/ubuntu/claude_master/parity_v12w/jars.json}
MIN_MEM_MB=${MIN_MEM_MB:-1000}
# [R4u] jar co code [BIG_DOWN-SEL] (chuoi trong class com/binance/chuyennd/**; CHI DOC Oracle) => in "OK <class>" | ly do
jar_bigdown() {
  python3 -I - "$1" <<'PYEOF'
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
}
# [ADD19] ghi gio start THAT cua jar dich (r4u3) vao gmicro_target.json; $1=1 luon ghi (vua swap), 0 = chi khi smoke_start_ms chua co
gmicro_write() {
  local ms src out rc
  ms=$(python3 -I - "$JARS_JSON" "$TGT_TAG" "$TGT_MD5" <<'PYEOF'
import json, sys
try:
    for x in json.load(open(sys.argv[1])):
        if x.get('name') == sys.argv[2] and x.get('md5') == sys.argv[3]:
            print(x.get('start_ms')); break
except Exception:
    pass
PYEOF
); src="jars.json (register_jar)"
  if ! [[ "$ms" =~ ^[0-9]{12,13}$ ]]; then
    ms=$($SSH_242 "P=\$(pgrep -f '${PROC_PAT:-BinanceOrderTradingManager}' | head -1); [ -n \"\$P\" ] && echo \$(( (\$(date +%s) - \$(ps -o etimes= -p \$P | tr -d ' ')) * 1000 ))" 2>/dev/null)
    src="242 ps etimes"
  fi
  if ! [[ "$ms" =~ ^[0-9]{12,13}$ ]]; then
    say "!! KHONG lay duoc gio start $TGT_TAG — KHONG ghi $GMICRO_TARGET (smoke = CHUA DO)"; tg "[deploy_chain $PRESET] KHAN TS=$TS: khong lay duoc gio start $TGT_TAG — gmicro_target.json CHUA dien smoke_start_ms"; return 1
  fi
  out=$(python3 -I - "$GMICRO_TARGET" "$TGT_TAG" "$TGT_MD5" "$ms" "$1" <<'PYEOF'
import json, os, shutil, sys, time
p, tag, md5, ms, force = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), sys.argv[5] == '1'
cur = {}
if os.path.exists(p):
    try:
        cur = json.load(open(p))
    except Exception as e:
        print('ERR file_hong_' + type(e).__name__); sys.exit(2)
if cur.get('target_md5') not in (None, md5):
    print('ERR target_md5 trong file %s KHAC jar %s' % (cur.get('target_md5'), md5)); sys.exit(2)
if cur.get('target_jar') not in (None, tag):
    print('ERR target_jar trong file %s KHAC %s' % (cur.get('target_jar'), tag)); sys.exit(2)
if not force and cur.get('smoke_start_ms'):
    print('GIU smoke_start_ms=%s' % cur['smoke_start_ms']); sys.exit(0)
if os.path.exists(p):
    shutil.copy2(p, '%s.bak_%d' % (p, int(time.time())))
new = dict(cur); new.update({'target_jar': tag, 'target_md5': md5, 'smoke_start_ms': ms})
os.makedirs(os.path.dirname(p) or '.', exist_ok=True)
tmp = p + '.tmp'
json.dump(new, open(tmp, 'w')); os.replace(tmp, p)
print('OK smoke_start_ms=%d (%s +07)' % (ms, time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(ms / 1000 + 7 * 3600))))
PYEOF
); rc=$?
  if [ "$rc" = 0 ]; then say "gmicro: $out ($GMICRO_TARGET, nguon $src)"; tg "[deploy_chain $PRESET] gmicro_target.json: $TGT_TAG $out (nguon $src)"; return 0; fi
  say "!! gmicro: $out — KHONG ghi $GMICRO_TARGET"; tg "[deploy_chain $PRESET] KHAN TS=$TS: gmicro_target.json KHONG ghi: $out"; return 1
}
DLOCK=${DLOCK:-$D/.deploy.lock}   # [MIN TOCTOU] kiem "khong job deploy khac" + chay buoc DUOI khoa nay
DEPLOY_TG_ENV=${DEPLOY_TG_ENV:-/home/ubuntu/.config/health242/tg.env}
ST=$D/.deploy_chain
mkdir -p "$ST"
SELF=$(cd "$(dirname "$0")" && pwd)/$(basename "$0")
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
setst() { echo "$*" > "$ST/step"; [ -n "${JD:-}" ] && echo "[$(TZ=Asia/Ho_Chi_Minh date '+%F %T')] $*" >> "$JD/steps.txt"; return 0; }
md5f() { md5sum < "$1" 2>/dev/null | cut -c1-32; }
# chep script con vao $1 (thu muc job) + kiem pin; in dong OK/LECH; tra 1 neu lech/thieu
stage_scripts() {
  local jd=$1 bad=0 n src pin dst
  mkdir -p "$jd" || return 1
  for n in "deploy_ingest_qf4.sh|$QF4_SH|$PIN_QF4_SH" "ingqf4_check_remote.sh|$CHECK_R|$PIN_CHECK_R" \
           "swap_v12_dry_jar.sh|$SWAP_SH|$PIN_SWAP_SH" "register_jar.sh|$REG_JAR_SH|$PIN_REG"; do
    dst=$jd/${n%%|*}; src=${n#*|}; pin=${src#*|}; src=${src%%|*}
    if ! cp -p "$src" "$dst" 2>/dev/null; then echo "LECH ${n%%|*}: khong chep duoc $src"; bad=1; continue; fi
    if [ "$(md5f "$dst")" = "$pin" ]; then echo "OK pin ${n%%|*} md5=$pin"; else echo "LECH ${n%%|*}: md5=$(md5f "$dst") != pin $pin ($src)"; bad=1; fi
    echo "${n%%|*} $(md5f "$dst") pin=$pin src=$src" >> "$jd/md5.txt"
  done
  return $bad
}
verify_staged() {   # truoc moi buoc: ban chep van dung pin
  [ "$(md5f "$JD/deploy_ingest_qf4.sh")" = "$PIN_QF4_SH" ] && [ "$(md5f "$JD/ingqf4_check_remote.sh")" = "$PIN_CHECK_R" ] \
    && [ "$(md5f "$JD/swap_v12_dry_jar.sh")" = "$PIN_SWAP_SH" ] && [ "$(md5f "$JD/register_jar.sh")" = "$PIN_REG" ]
}
# ------------------------------------------------------------------ status / stop
case "${1:-}" in
  status)
    P=$(cat "$ST/pid" 2>/dev/null); L=$(cat "$ST/log" 2>/dev/null)
    if [ -n "$P" ] && kill -0 "$P" 2>/dev/null; then echo "JOB CHAY pid=$P preset=$(cat "$ST/preset" 2>/dev/null)"; else echo "KHONG co job chuoi dang chay (pid cu ${P:-none})"; fi
    echo "buoc: $(cat "$ST/step" 2>/dev/null)"; [ -f "$ST/STOP" ] && echo "DA YEU CAU STOP"
    echo "thu muc job (giu lau dai): $(cat "$ST/last" 2>/dev/null) | cac job: $(ls "$ST/jobs" 2>/dev/null | wc -l)"
    [ -n "$L" ] && { echo "log: $L"; tail -n 25 "$L"; }
    exit 0;;
  stop)
    P=$(cat "$ST/pid" 2>/dev/null)
    if [ -n "$P" ] && kill -0 "$P" 2>/dev/null; then touch "$ST/STOP"; echo "Da yeu cau STOP: job $P dung TRUOC buoc ke / trong luc cho (buoc dang chay neu co se chay tron)."
    else echo "Khong co job chuoi dang chay."; fi
    exit 0;;
esac
PRESET=${1:-}
case "$PRESET" in
  qf4_then_r4t) STEPS="qf4 r4t"; WANT_TAG=r4t;;
  swap_r4u3) STEPS="r4u3"; WANT_TAG=r4u3;;
  fin_pair)   # [FIN] ingestor fin TRUOC, v_t_m fin-guard SAU; buoc ingestor dung lai may "qf4" voi script/pin/log rieng
    STEPS="qf4 r4u3fin"; WANT_TAG=r4u3fin
    QF4_SH=${FIN_ING_SH:-$D/deploy_ingest_fin.sh}; PIN_QF4_SH=${PIN_FIN_ING_SH:-f2e6cf9605784c3c30666d17433ad0e2}
    QF4_PAT=${FIN_ING_PAT:-deploy_ingest_fin.sh}; QF4_LOGPFX=deploy_ingest_fin; QF4_RB_SH=rollback_ingest_fin.sh
    SWAP_SH=${FIN_SWAP_SH:-$(dirname "$SELF")/swap_v12_dry_jar.sh}   # swap CUNG nhanh voi chain nay (v1.2/fin-guard)
    PIN_SWAP_SH=${PIN_SWAP_FIN:-1012cdb6c316208c52186257e403020e};;
  *) echo "Dung: $0 <preset>|status|stop - preset: fin_pair | swap_r4u3 | qf4_then_r4t (cu)"; exit 1;;
esac
JD=""
if [ "${CHAIN_JOB:-0}" = 1 ]; then   # job: CHI dung ban chep trong thu muc job (da kiem pin luc YES)
  JD=${CHAIN_JD:?job thieu CHAIN_JD}
  QF4_SH=$JD/deploy_ingest_qf4.sh; CHECK_R=$JD/ingqf4_check_remote.sh; SWAP_SH=$JD/swap_v12_dry_jar.sh; REG_JAR_SH=$JD/register_jar.sh
fi
QF4_MD5=$(sed -n 's/^JAR_MD5=\([0-9a-f]\{32\}\).*/\1/p' "$QF4_SH" 2>/dev/null | head -1)
TGT_MD5=$(sed -n 's/^NJ_MD5=\${NJ_MD5:-\([0-9a-f]\{32\}\)}.*/\1/p' "$SWAP_SH" 2>/dev/null | head -1)
TGT_TAG=$(sed -n 's/^NEW_TAG=\${NEW_TAG:-\([a-z0-9_]*\)}.*/\1/p' "$SWAP_SH" 2>/dev/null | head -1); TGT_TAG=${TGT_TAG:-r4t}
TGT_JAR=$(sed -n 's/^NJ=\${NJ:-\([^}]*\)}.*/\1/p' "$SWAP_SH" 2>/dev/null | head -1)
[ -n "$QF4_MD5" ] || { echo "khong doc duoc JAR_MD5 tu $QF4_SH"; exit 1; }
[ -n "$TGT_MD5" ] || { echo "khong doc duoc NJ_MD5 tu $SWAP_SH"; exit 1; }
if [ "${C3_ACCOUNT:-SUB}" = MAIN ] && [ "${EXCL_HELD:-}" = false ]; then echo "DUNG: C3_ACCOUNT=MAIN di voi C3_EXCLUDE_LEGACY_HELD=false — TU CHOI (A1 r4u2 C-1: vi the c3 that bi tinh la LEGACY)"; exit 1; fi
[ "$TGT_TAG" = "$WANT_TAG" ] || { echo "preset $PRESET can swap NEW_TAG=$WANT_TAG (swap $SWAP_SH mac dinh NEW_TAG=$TGT_TAG) — TU CHOI"; exit 1; }

# ------------------------------------------------------------------ doc 242 (CHI DOC)
rstate() {   # in KEY=VAL: ING_N ING_MD5 VTM_N VTM_MD5 VTM_PID LATCH LINES
  $SSH_242 "bash -s -- $ING_DIR $APP_DIR" <<'EOF'
C=$1; A=$2
N=$(pgrep -fc 'websocket.BinanceDataIngestor'); P=$(pgrep -f 'websocket.BinanceDataIngestor' | head -1)
FD=$(find /proc/$P/fd -lname '*binance-java-sdk*.jar*' 2>/dev/null | head -1)
echo "ING_N=$N"; echo "ING_MD5=$( [ -n "$FD" ] && md5sum < "$FD" 2>/dev/null | cut -c1-32)"
cd "$A" 2>/dev/null || { echo "VTM_N=0"; echo END_ST; exit 0; }
PP=${PROC_PAT:-BinanceOrderTradingManager}
echo "VTM_N=$(pgrep -fc "$PP")"; echo "VTM_PID=$(pgrep -f "$PP" | head -1)"
echo "VTM_MD5=$(md5sum < target/binance-java-sdk-1.2.4.jar 2>/dev/null | cut -c1-32)"
echo "LATCH=$(sed -n 's/.*"latch":"\([A-Z_]*\)".*/\1/p' run/killsw_latch.json 2>/dev/null | head -1)"
echo "LINES=$(wc -l < logs/full.log 2>/dev/null || echo 0)"
echo "LEGACY_N=$(tail -c 20000000 logs/full.log 2>/dev/null | grep -a '\[LEGACY\] managed' | tail -1 | grep -aoE 'managed [0-9]+' | awk '{print $2}')"
echo END_ST
EOF
}
kv() { echo "$RS" | sed -n "s/^$1=//p" | tail -1; }
read_state() { RS=$(rstate 2>/dev/null); echo "$RS" | grep -qx END_ST; }
OTHER_PAT=${OTHER_PAT:-'swap_v12_dry_jar.sh|deploy_v12_dry_r4.sh|restart_v12_dry_reseed.sh|golive_[a-z_]*\.sh|rollback_v12.sh|rollback_ingest_qf4.sh|rollback_ingest_fin.sh'}
qf4_running() {   # job QF4 THAT (bo qua DRY=1)
  local p
  for p in $(pgrep -f "$QF4_PAT"); do
    [ "$p" = "$$" ] && continue
    tr '\0' '\n' < /proc/$p/environ 2>/dev/null | grep -qx 'DRY=1' && continue
    echo "$p"; return 0
  done
}
other_deploy() { pgrep -af "$OTHER_PAT" | grep -v "deploy_chain" | head -1; }
step_done() {   # $1 = buoc; dua tren RS
  case "$1" in
    qf4) [ "$(kv ING_MD5)" = "$QF4_MD5" ] && [ "$(kv ING_N)" = 1 ];;
    r4t|r4u3|r4u3fin) [ "$(kv VTM_MD5)" = "$TGT_MD5" ] && [ "$(kv VTM_N)" = 1 ];;
  esac
}
time_ok() {
  [ "$FORCE_TIME" = 1 ] && return 0
  if [ -n "${TIME_OK_FILE:-}" ]; then [ -f "$TIME_OK_FILE" ]; return; fi
  local H M; H=$(TZ=Asia/Ho_Chi_Minh date +%-H); M=$(TZ=Asia/Ho_Chi_Minh date +%-M)
  case "$H" in 7|19) return 1;; esac
  { [ "$M" -lt 10 ] || [ "$M" -gt 39 ]; } && return 1
  { [ "$H" = 0 ] && [ "$M" -ge 50 ]; } && return 1
  { [ "$H" = 12 ] && [ "$M" -ge 50 ]; } && return 1
  { [ "$H" = 13 ] && [ "$M" -le 20 ]; } && return 1
  { [ "$H" = 1 ] && [ "$M" -le 20 ]; } && return 1
  return 0
}

# ------------------------------------------------------------------ ke hoach + trang thai
plan() {
  say "=== deploy_chain preset=$PRESET (buoc: $STEPS) DRY=$DRY ==="
  for s in $STEPS; do case "$s" in
    qf4) echo "  - qf4 : $QF4_SH (jar collectData $QF4_MD5) — dang co job QF4 => CHO no xong; XONG neu ingestor chay jar $QF4_MD5";;
    *) echo "  - $s : $SWAP_SH (jar v_t_m $TGT_TAG $TGT_MD5) — XONG neu v_t_m chay jar $TGT_MD5";;
  esac; done
  [ "$PRESET" = fin_pair ] && echo "  r4u3fin: nhu r4u3 (BIG_DOWN-SEL, LEGACY, gmicro_target, hau kiem) + swap kiem ingestor fin + env token TRUOC khi dung bot; hau kiem them [MINUTE-FIN] BAT, 0 FIN_KHONG_BIN; loi => KHAN + lenh rollback ve r4u3"
  [ "$PRESET" = swap_r4u3 ] && echo "  r4u3: truoc buoc kiem code [BIG_DOWN-SEL] trong $TGT_JAR + chup LEGACY; sau swap ghi smoke_start_ms vao $GMICRO_TARGET; hau kiem ${STABLE_S}s: md5, 0 ERROR/KHAN, latch NONE, MINUTE-GUARD BAT, RAM >= ${MIN_MEM_MB} MB, LEGACY = chup truoc swap; loi => KHAN + lenh rollback ve r4t"
  echo "  Qua buoc: rc=0 + hau kiem on dinh ${STABLE_S}s lien tuc (collectData: KLINE-COVER du, 0 429/418, price_gap OK; v_t_m: 0 ERROR, latch NONE)"
  echo "  Buoc ke: khung gio ke tiep :10-:39 (tranh 07/19h, 00:50-01:20, 12:50-13:20). FAIL/rollback => DUNG CA CHUOI + Telegram KHAN."
  if read_state; then
    echo "  242 hien tai: ingestor=$(kv ING_N) jar=$(kv ING_MD5) | v_t_m=$(kv VTM_N) jar=$(kv VTM_MD5) latch=$(kv LATCH)"
    for s in $STEPS; do
      if step_done "$s"; then echo "  - $s: DA XONG (se bo qua, van kiem on dinh)";
      elif [ "$s" = qf4 ] && [ -n "$(qf4_running)" ]; then echo "  - $s: DANG CHAY (job pid $(qf4_running)) => chuoi CHO no xong";
      else echo "  - $s: CHUA (se chay)"; fi
    done
  else
    echo "  !! khong doc duoc 242 (ssh)"; return 1
  fi
}

# ------------------------------------------------------------------ foreground
if [ "${CHAIN_JOB:-0}" != 1 ]; then
  plan || { say "DUNG: khong doc duoc 242"; exit 1; }
  P=$(cat "$ST/pid" 2>/dev/null)
  if [ -n "$P" ] && kill -0 "$P" 2>/dev/null; then say "DUNG: da co job chuoi pid $P dang chay (status/stop)."; exit 1; fi
  if [ "$DRY" = 1 ]; then
    TD=$(mktemp -d); say "--- pin script con (ban A1 duyet):"; stage_scripts "$TD" | sed 's/^/   /'; PRC=${PIPESTATUS[0]}; rm -rf "$TD"
    read_state
    if [ "$PRESET" = swap_r4u3 ] || [ "$PRESET" = fin_pair ]; then BD=$(jar_bigdown "$TGT_JAR"); case "$BD" in OK*) say "OK code [BIG_DOWN-SEL] trong $TGT_JAR (${BD#OK })";; *) say "FAIL jar $TGT_JAR KHONG co code [BIG_DOWN-SEL] ($BD)"; PRC=1;; esac; fi
    SWS=$(echo $STEPS | tr ' ' '\n' | grep -E '^r4(t|u3|u3fin)$' | head -1)
    if [ -n "$SWS" ] && ! step_done "$SWS"; then say "--- DRY=1 cua swap (CHI DOC 242):"; DRY=1 bash "$SWAP_SH" 2>&1 | grep -E 'OK jar moi|jar_dang_chay|FAIL|DRY PASS|DUNG' | cut -c1-200; fi
    [ "$PRC" = 0 ] || { say "DRY: co muc FAIL (pin script con / code jar) => chay that se TU CHOI. (DRY FAIL)"; exit 1; }
    say "DRY=1: KHONG chay gi. (DRY PASS)"; exit 0
  fi
  say ">>> Go YES de chay CA CHUOI o JOB NEN (tu cho/kiem/chay buoc ke; khong can canh gio):"
  read -r ANS || ANS=""
  [ "$ANS" = YES ] || { say "Huy. Khong doi gi."; exit 0; }
  TS=$(TZ=Asia/Ho_Chi_Minh date +%Y%m%d_%H%M%S)
  JD=$ST/jobs/${TS}_$PRESET; JL=$JD/chain.log
  say "--- chep script con vao $JD + kiem pin md5 (CHI chay ban chep):"
  mkdir -p "$JD" || { say "DUNG: khong tao duoc $JD"; exit 1; }
  stage_scripts "$JD" > "$JD/pin.txt"; PRC=$?
  sed 's/^/   /' "$JD/pin.txt"
  if [ "$PRC" != 0 ] || grep -q '^LECH' "$JD/pin.txt"; then
    echo "TU CHOI: lech pin" >> "$JD/steps.txt"; echo "$JD" > "$ST/last"
    say "TU CHOI: script con LECH md5 pin (ban A1 duyet) => KHONG chay gi. Chi tiet: $JD/md5.txt"; exit 1
  fi
  if [ "$PRESET" = swap_r4u3 ] || [ "$PRESET" = fin_pair ]; then
    BD=$(jar_bigdown "$TGT_JAR"); case "$BD" in OK*) say "OK code [BIG_DOWN-SEL] trong $TGT_JAR (${BD#OK })";;
      *) echo "TU CHOI: jar khong co [BIG_DOWN-SEL]" >> "$JD/steps.txt"; echo "$JD" > "$ST/last"; say "TU CHOI: jar $TGT_JAR KHONG co code [BIG_DOWN-SEL] ($BD)"; exit 1;; esac
  fi
  rm -f "$ST/STOP"; echo "$PRESET" > "$ST/preset"; echo "$JL" > "$ST/log"; echo "$JD" > "$ST/last"; setst "khoi dong"
  CHAIN_JOB=1 CHAIN_TS=$TS CHAIN_JD=$JD setsid nohup bash "$SELF" "$PRESET" >> "$JL" 2>&1 < /dev/null &
  echo $! > "$ST/pid"
  say "JOB NEN pid=$! thu muc job=$JD (log + ban chep + md5, giu lau dai)"
  say "Xem: bash $SELF status   | dung: bash $SELF stop   | tail -f $JL"
  exit 0
fi

# ------------------------------------------------------------------ JOB NEN
TS=${CHAIN_TS:-$(date +%s)}
echo $$ > "$ST/pid"
IN_STABLE=""   # buoc dang hau kiem on dinh (jar moi DA chay, CHUA xac nhan)
LSNAP=-1      # [R4u] LEGACY managed chup truoc swap
rb_cmd() {   # lenh rollback 1 dong cho buoc $1
  case "$1" in
    qf4) local L4 r; L4=$(ls -t "$D"/${QF4_LOGPFX}_*.log 2>/dev/null | grep -v '_dry.log' | head -1)
         r=$(grep -h 'Rollback 1 lenh:' "$L4" 2>/dev/null | tail -1 | sed 's/.*Rollback 1 lenh: //')
         echo "${r:-bash $D/$QF4_RB_SH <TS trong log $QF4_LOGPFX>}";;
    r4t) echo "OLD_TAG=r4t NEW_TAG=r4q OLD_MD5=$TGT_MD5 NJ=$R4Q_JAR NJ_MD5=$R4Q_MD5 NEED_MGUARD=0 NEED_BIGDOWN=0 bash $JD/swap_v12_dry_jar.sh  (go YES; ve r4q)";;
    r4u3fin) echo "OLD_TAG=r4u3fin NEW_TAG=r4u3 OLD_MD5=$TGT_MD5 NJ=$R4U3_JAR NJ_MD5=$R4U3_PIN_MD5 NEED_MGUARD=1 NEED_FIN=0 bash $JD/swap_v12_dry_jar.sh  (go YES; ve r4u3 - an toan voi ca ingestor fin)";;
    r4u3) echo "OLD_TAG=r4u3 NEW_TAG=r4t OLD_MD5=$TGT_MD5 NJ=$R4T_JAR NJ_MD5=$R4T_PIN_MD5 NEED_MGUARD=1 NEED_BIGDOWN=0 bash $JD/swap_v12_dry_jar.sh  (go YES; ve r4t)";;
  esac
}
unverified_msg() { echo "jar moi $1 DANG CHAY nhung CHUA xac nhan on dinh — owner kiem ngay; rollback neu can: $(rb_cmd "$1")"; }
fail() {
  local extra=""; [ -n "$IN_STABLE" ] && extra=" | $(unverified_msg "$IN_STABLE")"
  setst "DUNG: $*$extra"; say "DUNG CHUOI: $*$extra"
  tg "[deploy_chain $PRESET] KHAN TS=$TS: DUNG CHUOI — $*$extra. Cac buoc sau KHONG chay. Log $(cat "$ST/log" 2>/dev/null)"; exit 1
}
chk_stop() {
  [ -f "$ST/STOP" ] || return 0
  rm -f "$ST/STOP"
  if [ -n "$IN_STABLE" ]; then   # [A1 CHAIN] stop giua hau kiem: jar moi chua xac nhan on dinh => KHAN + lenh rollback
    local m; m=$(unverified_msg "$IN_STABLE")
    setst "DUNG theo stop GIUA hau kiem $IN_STABLE: $m"; say "STOP theo yeu cau owner GIUA hau kiem: $m"
    tg "[deploy_chain $PRESET] KHAN TS=$TS: STOP giua hau kiem — $m"; exit 1
  fi
  setst "DUNG theo yeu cau stop"; say "STOP theo yeu cau owner"; tg "[deploy_chain $PRESET] DUNG theo yeu cau stop TS=$TS"; exit 1
}
sleep_chk() { local i; for i in $(seq 1 "$1"); do chk_stop; sleep 1; done; }

# hau kiem on dinh: $1 = buoc, $2 = dong log v_t_m moc (dem ERROR tu day)
stable() {
  local step=$1 base=$2 since=${3:-0} t0 ok_since=0 now K V lg lines err   # since = moc bat dau buoc (epoch s)
  t0=$(date +%s); IN_STABLE=$step; setst "$step: hau kiem on dinh (${STABLE_S}s)"
  say "--- $step: hau kiem on dinh ${STABLE_S}s (moi ${CHK_POLL_S}s), moc log v_t_m dong $base"
  while :; do
    chk_stop
    now=$(date +%s)
    [ $((now - t0)) -gt "$STABLE_MAX_S" ] && fail "$step: hau kiem khong on dinh sau ${STABLE_MAX_S}s"
    if ! read_state; then say "ssh doc 242 loi — thu lai"; ok_since=0; sleep_chk "$CHK_POLL_S"; continue; fi
    lg=$(kv VTM_PID)
    K=$($SSH_242 "bash -s -- $ING_DIR $APP_DIR $QF4_MD5 ${lg:-0} new none $since" < "$CHECK_R" 2>/dev/null) || K="FAIL ssh_check_collectData"
    lines=$(kv LINES); [ "${lines:-0}" -lt $((base - 1)) ] && base=1   # log xoay (file ngan hon moc)
    V=$($SSH_242 "bash -s -- $APP_DIR $base $step ${LSNAP:--1} $MIN_MEM_MB ${C3_ACCOUNT:-SUB}" <<'EOF'
A=$1; B=$2; S=$3; L0=$4; MM=$5; ACC=${6:-SUB}; cd "$A" || { echo "FAIL cd_vtm"; exit 0; }
PP=${PROC_PAT:-BinanceOrderTradingManager}
[ "$(pgrep -fc "$PP")" = 1 ] && echo "OK vtm_1_process" || echo "FAIL vtm_so_process=$(pgrep -fc "$PP")"
E=$(tail -n +$B logs/full.log 2>/dev/null | grep -a ' ERROR ' | head -1 | cut -c1-160)
[ -z "$E" ] && echo "OK vtm_0_ERROR" || echo "FAIL vtm_ERROR: $E"
grep -q '"latch":"NONE"' run/killsw_latch.json 2>/dev/null && echo "OK latch_NONE" || echo "FAIL latch_khac_NONE"
if [ "$S" = r4t ] || [ "$S" = r4u3 ] || [ "$S" = r4u3fin ]; then tail -n +$B logs/full.log | grep -a -q '\[MINUTE-GUARD\] TAT' && echo "FAIL MINUTE-GUARD_TAT"; fi
if [ "$S" = r4u3fin ]; then   # [FIN] guard bin fin BAT, record co bin fin (FIN_THIEU = fail-closed hop le, chi dem)
  tail -n +$B logs/full.log | grep -a -q '\[MINUTE-FIN\] TAT' && echo "FAIL MINUTE-FIN_TAT"
  # [A1-M7] [MINUTE-FIN] BAT phai co tu dong khoi dong JVM moi nhat (buoc da XONG tu truoc: dong BAT nam truoc moc B)
  JS=$(grep -a -n 'MainClass: com.binance.chuyennd.trading.BinanceOrderTradingManager' logs/full.log 2>/dev/null | tail -1 | cut -d: -f1)
  [ "$(tail -n +${JS:-1} logs/full.log 2>/dev/null | grep -a -c '\[MINUTE-FIN\] BAT')" -ge 1 ] && echo "OK MINUTE-FIN_BAT" || echo "WAIT MINUTE-FIN_BAT_chua_thay"
  NB=$(tail -n +$B logs/full.log 2>/dev/null | grep -a -c 'ly_do=FIN_KHONG_BIN'); [ "${NB:-0}" = 0 ] && echo "OK 0_FIN_KHONG_BIN" || echo "FAIL FIN_KHONG_BIN=$NB (record khong co bin fin)"
  echo "INFO FIN_THIEU=$(tail -n +$B logs/full.log 2>/dev/null | grep -a -c 'ly_do=FIN_THIEU') FIN_WAIT=$(tail -n +$B logs/full.log 2>/dev/null | grep -a -c 'MINUTE-FIN-WAIT') FIN_EXCL_PHUT=$(tail -n +$B logs/full.log 2>/dev/null | grep -a -c '\[MINUTE-FIN-EXCL\] phut=')"
fi
if [ "$S" = r4u3 ] || [ "$S" = r4u3fin ]; then   # [R4u] 0 KHAN, RAM, LEGACY = chup truoc swap
  K=$(tail -n +$B logs/full.log 2>/dev/null | grep -a 'KHAN' | grep -av 'DRY tren tai khoan chinh' | head -1 | cut -c1-160)
  [ -z "$K" ] && echo "OK vtm_0_KHAN" || echo "FAIL vtm_KHAN: $K"
  if [ "$ACC" = SUB ]; then tail -n +$B logs/full.log 2>/dev/null | grep -aq '\[C3-EXCL-FORCE\]' && echo "FAIL C3-EXCL-FORCE (SUB: env key sai)" || echo "OK 0_C3-EXCL-FORCE"; fi
  MA=$(awk '/MemAvailable/{print int($2/1024)}' /proc/meminfo)
  [ "${MA:-0}" -ge "$MM" ] && echo "OK ram_MemAvailable_${MA}MB" || echo "FAIL ram_MemAvailable_${MA}MB<${MM}MB"
  LN=$(tail -n +$B logs/full.log 2>/dev/null | grep -a '\[LEGACY\] managed' | tail -1 | grep -aoE 'managed [0-9]+' | awk '{print $2}')
  if [ -z "$LN" ]; then echo "WAIT vtm_LEGACY_chua_co"
  elif [ "$L0" = -1 ] || [ "$LN" = "$L0" ]; then echo "OK LEGACY_managed=$LN (truoc swap ${L0})"
  elif [ "$LN" -lt "$L0" ] 2>/dev/null; then echo "OK LEGACY_managed=$LN (WARN < truoc swap $L0: dong tu nhien?)"
  else echo "FAIL LEGACY_managed=$LN > truoc swap $L0"; fi
fi
echo END_V
EOF
) || V="FAIL ssh_check_vtm"
    echo "$V" | grep -qx END_V || V="$V
FAIL vtm_check_khong_tron_ven"
    if echo "$K$V" | grep -q '^FAIL'; then
      echo "$K"; echo "$V"; fail "$step: hau kiem FAIL ($(echo "$K
$V" | grep '^FAIL' | head -3 | tr '\n' ' '))"
    fi
    if echo "$K" | grep -q '^WAIT' || echo "$V" | grep -q '^WAIT' || ! echo "$K" | grep -q '^OK kline_phu_phut_da_chot'; then
      ok_since=0; say "$step: cho on dinh: $(echo "$K
$V" | grep '^WAIT' | tr '\n' ' ' | cut -c1-200)"
    else
      [ "$ok_since" = 0 ] && ok_since=$now
      if [ $((now - ok_since)) -ge "$STABLE_S" ]; then
        say "$step: ON DINH ${STABLE_S}s: $(echo "$K" | grep -E '^OK (kline_phu|0_http|price_gap|price_age)' | tr '\n' ' ') | $(echo "$V" | grep '^OK' | tr '\n' ' ')"
        IN_STABLE=""; return 0
      fi
    fi
    sleep_chk "$CHK_POLL_S"
  done
}
wait_window() {   # $1 nhan
  local w=0; setst "$1: cho khung gio"
  until time_ok; do
    chk_stop
    [ $((w % 600)) = 0 ] && say "$1: cho khung gio ke tiep (:10-:39, tranh 07/19h...) — da cho ${w}s"
    [ "$w" -ge "$WINDOW_WAIT_MAX_S" ] && fail "$1: cho khung gio qua ${WINDOW_WAIT_MAX_S}s"
    sleep 10; w=$((w + 10))
  done
}
wait_no_deploy() {   # khong chay song song voi job deploy khac
  local w=0 p
  while :; do
    p=$(qf4_running); [ -z "$p" ] && p=$(other_deploy | awk '{print $1}')
    [ -z "$p" ] && return 0
    chk_stop
    [ $((w % 300)) = 0 ] && say "$1: dang co job deploy khac chay (pid $p) — cho no xong (da cho ${w}s)"
    [ "$w" -ge "$WAIT_RUNNING_MAX_S" ] && fail "$1: job deploy khac (pid $p) chay qua ${WAIT_RUNNING_MAX_S}s"
    sleep 10; w=$((w + 10))
  done
}
say "=== JOB deploy_chain $PRESET TS=$TS pid=$$ (buoc: $STEPS; QF4 $QF4_MD5, $TGT_TAG $TGT_MD5; ban chep $JD) ==="
verify_staged || fail "ban chep script trong $JD khong dung pin md5"
tg "[deploy_chain $PRESET] BAT DAU TS=$TS: buoc $STEPS (tu cho/kiem; FAIL => dung ca chuoi + KHAN)"
FIRST=1
for s in $STEPS; do
  chk_stop
  read_state || { sleep 30; read_state || fail "$s: khong doc duoc 242 (ssh)"; }
  if [ "$s" = qf4 ] && [ -n "$(qf4_running)" ]; then
    setst "qf4: cho job QF4 dang chay"; say "--- qf4: job QF4 DANG CHAY (pid $(qf4_running)) — cho no xong, khong chay song song"
    tg "[deploy_chain $PRESET] qf4: phat hien job QF4 dang chay — cho no xong roi kiem"
    wait_no_deploy qf4
    read_state || fail "qf4: khong doc duoc 242 sau job QF4"
    step_done qf4 || fail "qf4: job QF4 ket thuc nhung ingestor KHONG chay jar $QF4_MD5 (jar=$(kv ING_MD5)) — FAIL/rollback"
    L4=$(ls -t "$D"/${QF4_LOGPFX}_*.log 2>/dev/null | grep -v '_dry.log' | head -1)
    if [ -n "$L4" ] && ! grep -q 'XONG. collectData chay jar' "$L4"; then fail "qf4: log job QF4 $L4 KHONG co dong XONG (rollback/dung?)"; fi
    say "qf4: job QF4 da XONG (jar $QF4_MD5)"; tg "[deploy_chain $PRESET] qf4 XONG (job owner) — kiem on dinh ${STABLE_S}s"
  elif step_done "$s"; then
    say "--- $s: DA XONG tu truoc (md5 tren 242 dung) => bo qua"
    if [ "$s" = r4u3 ] || [ "$s" = r4u3fin ]; then LSNAP=$(kv LEGACY_N); [[ "$LSNAP" =~ ^[0-9]+$ ]] || LSNAP=-1; gmicro_write 0; fi
  else
    wait_no_deploy "$s"
    if [ "$FIRST" = 0 ] || [ "$s" = r4t ] || [ "$s" = r4u3 ] || [ "$s" = r4u3fin ]; then wait_window "$s"; fi
    # [A1 CHAIN MIN TOCTOU] lay khoa deploy ROI moi kiem "khong job khac" va chay buoc; khoa giu suot buoc (ca job nen cua swap)
    while :; do
      wait_no_deploy "$s"
      exec 9>>"$DLOCK"
      if ! flock -n 9; then
        exec 9>&-; setst "$s: cho khoa deploy $DLOCK"; say "$s: khoa deploy $DLOCK dang bi giu — cho"; sleep_chk 10; continue
      fi
      if [ -z "$(qf4_running)" ] && [ -z "$(other_deploy)" ]; then break; fi
      flock -u 9; exec 9>&-; sleep_chk 5
    done
    read_state || fail "$s: khong doc duoc 242 truoc khi chay"
    step_done "$s" && { flock -u 9; exec 9>&-; say "$s: da XONG trong luc cho => bo qua"; continue; }
    verify_staged || fail "$s: ban chep script trong $JD KHONG con dung pin md5 — khong chay"
    if [ "$s" = r4u3 ] || [ "$s" = r4u3fin ]; then
      BD=$(jar_bigdown "$TGT_JAR"); case "$BD" in OK*) say "$s: OK code [BIG_DOWN-SEL] (${BD#OK })";; *) fail "$s: jar $TGT_JAR KHONG co code [BIG_DOWN-SEL] ($BD)";; esac
      LSNAP=$(kv LEGACY_N); [[ "$LSNAP" =~ ^[0-9]+$ ]] || LSNAP=-1; say "$s: chup LEGACY managed truoc swap = $LSNAP"
    fi
    RAN_T0=$(date +%s); RAN_L0=$(( $(kv LINES) + 1 ))   # [11-10] moc bat dau buoc (thoi gian + dong log v_t_m)
    setst "$s: DANG CHAY"; say "--- $s: CHAY (ban chep $JD, khoa $DLOCK)"; tg "[deploy_chain $PRESET] $s: BAT DAU"
    case "$s" in
      qf4) echo YES | bash "$QF4_SH"; RC=$?;;
      r4t|r4u3|r4u3fin) echo YES | REG_JAR_SH=$REG_JAR_SH bash "$SWAP_SH"; RC=$?;;
    esac
    flock -u 9; exec 9>&-
    [ "$RC" = 0 ] || fail "$s: script rc=$RC (FAIL/rollback)"
    read_state || fail "$s: khong doc duoc 242 sau buoc"
    step_done "$s" || fail "$s: rc=0 nhung md5 tren 242 khong dung"
    { [ "$s" = r4u3 ] || [ "$s" = r4u3fin ]; } && gmicro_write 0   # [ADD19] swap da ghi smoke_start_ms (khi file tro r4u3); con trong => chain dien (loi => KHAN, khong dung chuoi)
    tg "[deploy_chain $PRESET] $s: script XONG rc=0 — kiem on dinh ${STABLE_S}s"
  fi
  FIRST=0
  read_state || fail "$s: khong doc duoc 242"
  # [11-10 MASTER] moi chi so hau kiem CHI tinh tu moc bat dau buoc (collectData: theo timestamp; v_t_m: dong log tai moc).
  # Buoc da XONG tu truoc (khong chay lai) => moc = luc bat dau hau kiem. KHONG tinh tu luc process start.
  if [ -n "${RAN_T0:-}" ]; then SINCE=$RAN_T0; BASE=$RAN_L0; else SINCE=$(date +%s); BASE=$(( $(kv LINES) + 1 )); fi
  RAN_T0=""; RAN_L0=""
  say "$s: moc hau kiem = $(date -d "@$SINCE" '+%F %T') (v_t_m tu dong $BASE)"
  if [ "$s" = r4t ] || [ "$s" = r4u3 ] || [ "$s" = r4u3fin ]; then   # sau swap: tinh tu dong khoi dong JVM moi nhat NEU no SAU moc buoc (bo log tat JVM cu)
    SB=$($SSH_242 "grep -a -n 'MainClass: com.binance.chuyennd.trading.BinanceOrderTradingManager' $APP_DIR/logs/full.log | tail -1 | cut -d: -f1" 2>/dev/null)
    [[ "$SB" =~ ^[0-9]+$ ]] && [ "$SB" -gt "$BASE" ] && BASE=$SB
  fi
  stable "$s" "$BASE" "$SINCE"
  setst "$s: XONG + on dinh"; tg "[deploy_chain $PRESET] $s: XONG + on dinh ${STABLE_S}s"
done
setst "XONG ca chuoi"; say "=== XONG CA CHUOI $PRESET ==="
tg "[deploy_chain $PRESET] XONG CA CHUOI TS=$TS (buoc $STEPS; $TGT_TAG $TGT_MD5, on dinh)"
exit 0
