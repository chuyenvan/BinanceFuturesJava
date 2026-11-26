#!/usr/bin/env bash
# =============================================================================
# golive_set_lev1x.sh - dat leverage 1x cho MOI symbol universe c3 dang != 1x tren TAI KHOAN CON (SUB) cua bot c3. Chay tren ORACLE (owner).
#   Muc dich: golive_check_lev.sh (ops6) ra "KET QUA: DAT" that (sua THUC TE cho khop phep kiem; KHONG noi phep kiem, KHONG sua ops6).
#   A1_LEV1X_APPROVED=<sha256 file nay> bash golive_set_lev1x.sh            # DRY (MAC DINH): chi DOC san, in ke hoach
#   A1_LEV1X_APPROVED=<sha256 file nay> DRY=0 bash golive_set_lev1x.sh      # GHI: hien ke hoach, go 'YES LEV1X' (CHINH XAC) trong 300 s
# Quy uoc DRY: chi DRY=0 (dung chuoi "0") moi ghi; moi gia tri khac / khong dat = DRY=1.
# [v2 A1_LEV1X] B-1 symbol non-ASCII (ten chu Han): query = urllib.parse.quote(sym, safe='') (UTF-8), ky HMAC tren DUNG chuoi da
#   percent-encode se gui (nhu jar C3LiveClient.enc: URLEncoder UTF-8 roi ky); moi ten symbol in/so sanh/truyen Oracle<->242 o dang
#   percent-encode (ASCII); symbol non-ASCII POST SAU CUNG, san loi (tru 429/418/-1003) => KHONG abort, ghi CON + khoi "CAN LAM TAY".
#   M-1 python tren 242 kiem sha8 key doc duoc == pin SUB (!= pin MAIN) TRUOC call dau tien (ca phien doc lan ghi), sai => ERR=KEY_PIN.
#   m-1 doc key cung quy tac lib bash; m-2 bao N_MARGIN + N_MAXNOTIONAL (cung cong thuc check_lev, LEV_CAP mac dinh 5000);
#   m-3 bien noi bo _LV1X_* dat san tu env => TU CHOI, bo loc output luon bat; m-4 chay BAN COPY (mktemp -d 700, file 500, sha256 ban
#   copy == A1_LEV1X_APPROVED); m-5 'YES LEV1X' khop chinh xac; m-6 cho weight in trang thai moi <= 25 s (ca phien doc).
#   Them: in W_PRE truoc POST; LV1X_W_MAX trong [300,1200]; che do that cam chay phut :58-:02 va :29-:31 (gio Oracle), POST dung khi
#   toi phut cam ke tiep (deadline).
# Thu tu: (A) ban goc: tu choi _LV1X_* dat san; copy vao mktemp -d; sha256 ban copy == A1_LEV1X_APPROVED; exec ban copy.
#   (B) ban copy: kiem thu muc/quyen/token; bo loc output; env cam (che do that); khung gio (DRY=0); ops6 GHIM (HEAD 082c10f5.., ops/c3live
#   sach, md5 golive_lib.sh, gl_manifest_check) => source lib (CHI dung ham); gl_init; flock; gl_read_state (CHI DOC 242): file key bot
#   dung = keys_sub.env, sha8 file key = pin SUB != pin MAIN; doc san (95 weight, ky tren 242); DRY => thoat; DRY=0 => 'YES LEV1X' 300 s
#   => khung gio lai => 1 ssh 242: kiem pin key, doc lai, POST /fapi/v1/leverage leverage=1 CHI symbol trong ke hoach DA XAC NHAN, van
#   != 1x, khong vi the, khong lenh mo; nhip >= LV1X_PACE_S; X-MBX-USED-WEIGHT-1M >= LV1X_W_MAX => ngu toi phut sau (tong <= LV1X_WAIT_MAX_S);
#   429/418/-1003 => DUNG NGAY; symbol ASCII: -2014/-2015/-1022 hoac LV1X_ERR_CONSEC loi lien tiep => DUNG; doc lai => KET QUA.
# Ma thoat: 0 DAT | 3 CON symbol != 1x | 4 CANH BAO (lev xong, con marginType/maxNotional) | 1 TU CHOI / DUNG. Khong in key/secret/signature.
# Key KHONG roi 242: chuoi ky + curl chay TREN 242 (python /opt/c3py, doc keys_sub.env tai cho, curl -K - qua stdin).
# Nguon tai dung (doc, KHONG chep): ops6 082c10f5 ops/c3live/golive_lib.sh: gl_init, say, die, s242in, s242in_once, gl_state242/
#   gl_read_state/sv, gl_manifest_check. Python = CHEP + mo rong tu gl_api242 (call HMAC + curl -K -) va che do lev (universe, LEVSYM).
# =============================================================================
set -euo pipefail
LV_NAME=golive_set_lev1x.sh
lv_no() { echo "TU CHOI: $* - KHONG lam gi."; echo "KET QUA: TU_CHOI"; exit 1; }

if [ -z "${_LV1X_STAGE:-}" ]; then
  # ===== (A) BAN GOC: khong doc env nao khac ngoai A1_LEV1X_APPROVED; chi copy + kiem sha ban copy + exec
  _lvx=$(compgen -e | sed -n '/^_LV1X_/p' | tr '\n' ' ')
  [ -z "$_lvx" ] || lv_no "[m-3] bien noi bo dat san tu env: ${_lvx}- unset roi chay lai"
  [[ "${A1_LEV1X_APPROVED:-}" =~ ^[0-9a-f]{64}$ ]] || lv_no "[A1] A1_LEV1X_APPROVED thieu hoac sai dinh dang (64 hex) - chi chay ban A1 da duyet"
  _src=$(readlink -f "$0")
  [ -f "$_src" ] || lv_no "khong doc duoc file script $0"
  umask 077
  _d=$(mktemp -d /tmp/lv1x_run.XXXXXXXXXX) || lv_no "khong tao duoc thu muc tam"
  trap 'rm -rf "$_d"' EXIT
  chmod 700 "$_d" || lv_no "chmod thu muc tam"
  cp "$_src" "$_d/$LV_NAME" || lv_no "khong copy duoc script"
  chmod 500 "$_d/$LV_NAME" || lv_no "chmod ban copy"
  _sha=$(sha256sum "$_d/$LV_NAME" | cut -c1-64)
  [ "$_sha" = "$A1_LEV1X_APPROVED" ] \
    || lv_no "[A1] A1_LEV1X_APPROVED KHONG khop sha256 ban copy (file bat dau ${_sha:0:8}) - chi chay ban A1 da duyet"
  _tok=$(od -An -N16 -tx1 /dev/urandom | tr -d ' \n')
  printf '%s\n' "$_tok" > "$_d/.tok" && chmod 400 "$_d/.tok" || lv_no "khong ghi duoc token"
  trap - EXIT
  exec env _LV1X_STAGE=copy _LV1X_DIR="$_d" _LV1X_TOK="$_tok" bash "$_d/$LV_NAME" "$@"
fi

# ===== (B) BAN COPY
[ "$_LV1X_STAGE" = copy ] || lv_no "[m-3] _LV1X_STAGE la"
LV_D=${_LV1X_DIR:-}; LV_TOK=${_LV1X_TOK:-}
unset _LV1X_STAGE _LV1X_DIR _LV1X_TOK
[[ "$LV_D" =~ ^/tmp/lv1x_run\.[A-Za-z0-9]{10}$ ]] || lv_no "[m-4] thu muc ban copy la"
LV_SELF=$LV_D/$LV_NAME
[ ! -L "$LV_D" ] && [ ! -L "$LV_SELF" ] && [ "$(readlink -f "$0")" = "$LV_SELF" ] || lv_no "[m-4] khong chay tu ban copy $LV_SELF"
[ "$(stat -c '%u %a' "$LV_D")" = "$(id -u) 700" ] && [ "$(stat -c '%u %a' "$LV_SELF")" = "$(id -u) 500" ] \
  || lv_no "[m-4] quyen thu muc/ban copy sai (can 700/500, chu = $(id -u))"
[[ "$LV_TOK" =~ ^[0-9a-f]{32}$ ]] && [ -f "$LV_D/.tok" ] && [ "$(cat "$LV_D/.tok")" = "$LV_TOK" ] || lv_no "[m-4] token ban copy sai"
LV_SED_PID=""
lv_cleanup() {
  rm -rf "$LV_D"
  if [ -n "$LV_SED_PID" ]; then exec 1>&- 2>&-; wait "$LV_SED_PID" 2>/dev/null || :; fi
}
trap lv_cleanup EXIT
LV_SHA=$(sha256sum "$LV_SELF" | cut -c1-64)
[ "$LV_SHA" = "${A1_LEV1X_APPROVED:-}" ] || lv_no "[A1] sha256 ban copy doi sau khi kiem"
# loc output (nhu golive_check_lev.sh:19 + signature/APIKEY/hex64) - LUON bat, khong co co bo qua
exec > >(sed -u -E 's/[0-9]{8,10}:[A-Za-z0-9_-]{30,}/<TOKEN>/g; s/(signature=)[0-9A-Za-z%]+/\1<SIG>/g; s/(X-MBX-APIKEY:)[^"]*/\1<KEY>/Ig; s/[0-9a-fA-F]{64}/<HEX64>/g') 2>&1
LV_SED_PID=$!
LV_T0=$(date +%s)

LV_OPS6=/home/ubuntu/claude_master/w3/c3_ops6
LV_OPS6_HEAD=082c10f518e8a81e90dad0057bd459521303732b
LV_LIB_MD5=5d0febd23158acc52e2fe116c2f60ba8
LV_SUB_SHA8_PIN=43820b5b
LV_MAIN_SHA8_PIN=3ef771e0
LV_KEYS_SUB=/root/.config/c3live/keys_sub.env
LV_FAPI=https://fapi.binance.com
LV_RE_PLAN='^[ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789%,]*$'
LV_TEST=${LV1X_TEST:-0}
if [ "$LV_TEST" = 1 ]; then
  # Che do TEST: PHAI la moi truong gia - khong the cham 242 / san that
  case "${SSH_242:-}" in ""|*ssh*|*103.157.218.242*) lv_no "[TEST] SSH_242 phai dat va KHONG phai ssh/242 that";; esac
  [ -n "${CURL242:-}" ] && [ -f "$CURL242" ] && grep -q LV1X_FAKE_CURL "$CURL242" || lv_no "[TEST] CURL242 phai la fake curl (co dau LV1X_FAKE_CURL)"
  case "${KEYS_FILE:-}" in ""|/root/*) lv_no "[TEST] KEYS_FILE phai dat va khong o /root";; esac
  case "${LOGDIR:-}" in /tmp/*) ;; *) lv_no "[TEST] LOGDIR phai duoi /tmp";; esac
  [[ "${LV1X_TEST_SUB_SHA8:-}" =~ ^[0-9a-f]{8}$ ]] || lv_no "[TEST] thieu LV1X_TEST_SUB_SHA8"
  LV_SUB_SHA8_PIN=$LV1X_TEST_SUB_SHA8; LV_KEYS_SUB=$KEYS_FILE
  if [ -n "${LV1X_TEST_MAIN_SHA8:-}" ]; then
    [[ "$LV1X_TEST_MAIN_SHA8" =~ ^[0-9a-f]{8}$ ]] || lv_no "[TEST] LV1X_TEST_MAIN_SHA8 sai"; LV_MAIN_SHA8_PIN=$LV1X_TEST_MAIN_SHA8
  fi
  [ -z "${LV1X_TEST_NOW_EPOCH:-}" ] || [[ "$LV1X_TEST_NOW_EPOCH" =~ ^[0-9]{9,11}$ ]] || lv_no "[TEST] LV1X_TEST_NOW_EPOCH sai"
  LV_FAPI=https://lv1x-test.invalid   # ten mien .invalid: khong bao gio phan giai
  export https_proxy=http://127.0.0.1:9 HTTPS_PROXY=http://127.0.0.1:9 http_proxy=http://127.0.0.1:9 HTTP_PROXY=http://127.0.0.1:9
else
  [ "$LV_TEST" = 0 ] || lv_no "LV1X_TEST='$LV_TEST' khong hop le"
  for _v in SSH_242 SCP_242 APP_DIR PROC_PAT ING_PAT KEYS_FILE PY242 CURL242 SUB_KEY_SHA8 MAIN_KEY_SHA8 LOGDIR GL_TEST GL_SSH_TRIES \
            GL_SSH_TIMEOUT_S GL_SSH_DEADLINE WD_PAUSE LV1X_TEST_SUB_SHA8 LV1X_TEST_MAIN_SHA8 LV1X_TEST_NOW_EPOCH; do
    [ -z "${!_v:-}" ] || lv_no "bien $_v dat tu env (chi cho phep khi LV1X_TEST=1)"
  done
fi
[ -z "${C3_ACCOUNT:-}" ] || [ "$C3_ACCOUNT" = SUB ] || lv_no "C3_ACCOUNT='$C3_ACCOUNT': script CHI tac dong tai khoan con SUB"
export C3_ACCOUNT=SUB
LV_PACE=${LV1X_PACE_S:-0.25}; LV_WMAX=${LV1X_W_MAX:-600}; LV_WAITMAX=${LV1X_WAIT_MAX_S:-240}; LV_ECONSEC=${LV1X_ERR_CONSEC:-5}
LV_YES_T=${LV1X_YES_TIMEOUT_S:-300}; LV_CAP=${LEV_CAP:-5000}
[[ "$LV_PACE" =~ ^[0-9]+(\.[0-9]+)?$ ]] && awk -v p="$LV_PACE" -v t="$LV_TEST" 'BEGIN{exit !(p >= 0.2 || t == 1)}' || lv_no "LV1X_PACE_S='$LV_PACE' (>= 0.2 s = <= 5 req/s)"
[[ "$LV_WMAX" =~ ^[0-9]+$ ]] && [ "$LV_WMAX" -ge 300 ] && [ "$LV_WMAX" -le 1200 ] || lv_no "LV1X_W_MAX='$LV_WMAX' (300..1200)"
[[ "$LV_WAITMAX" =~ ^[0-9]+$ ]] && [ "$LV_WAITMAX" -le 600 ] || lv_no "LV1X_WAIT_MAX_S='$LV_WAITMAX' (0..600)"
[[ "$LV_ECONSEC" =~ ^[0-9]+$ ]] && [ "$LV_ECONSEC" -ge 1 ] && [ "$LV_ECONSEC" -le 20 ] || lv_no "LV1X_ERR_CONSEC='$LV_ECONSEC' (1..20)"
[[ "$LV_YES_T" =~ ^[0-9]+$ ]] && [ "$LV_YES_T" -ge 1 ] && [ "$LV_YES_T" -le 300 ] || lv_no "LV1X_YES_TIMEOUT_S='$LV_YES_T' (1..300)"
[[ "$LV_CAP" =~ ^[0-9]+(\.[0-9]+)?$ ]] && awk -v c="$LV_CAP" 'BEGIN{exit !(c > 0)}' || lv_no "LEV_CAP='$LV_CAP' (so > 0)"
LV_DRY=1; [ "${DRY:-1}" = 0 ] && LV_DRY=0

# ---- khung gio (CHE DO THAT): cam phut :58 :59 :00 :01 :02 :29 :30 :31 theo dong ho Oracle; LV_DEADLINE = epoch (dong ho that) dau phut cam ke tiep
lv_now() {
  if [ "$LV_TEST" = 1 ] && [ -n "${LV1X_TEST_NOW_EPOCH:-}" ]; then echo $(( LV1X_TEST_NOW_EPOCH + $(date +%s) - LV_T0 )); else date +%s; fi
}
LV_DEADLINE=0; LV_WIN_MSG=""
lv_window() {   # rc 0 = duoc chay (dat LV_DEADLINE), rc 1 = phut cam (dat LV_WIN_MSG)
  local now m s nxt tgt d
  now=$(lv_now); m=$((10#$(date -d "@$now" +%M))); s=$((10#$(date -d "@$now" +%S)))
  case "$m" in
    58|59|0|1|2|29|30|31)
      if [ "$m" -ge 29 ] && [ "$m" -le 31 ]; then tgt=32; else tgt=3; fi
      d=$(( ((tgt - m + 60) % 60) * 60 - s ))
      LV_WIN_MSG="phut hien tai $(TZ=Asia/Ho_Chi_Minh date -d "@$now" +%H:%M) (gio Oracle) thuoc khung cam :58-:02 / :29-:31 - chay lai tu $(TZ=Asia/Ho_Chi_Minh date -d "@$((now + d))" +%H:%M) (nen phut :03-:27 hoac :32-:56)"
      return 1;;
  esac
  if [ "$m" -lt 29 ]; then nxt=29; else nxt=58; fi
  LV_DEADLINE=$(( $(date +%s) + (nxt - m) * 60 - s ))
  return 0
}
if [ "$LV_DRY" = 0 ]; then lv_window || lv_no "[khung gio] $LV_WIN_MSG"; fi

# ops6 GHIM
LV_OPSD=$LV_OPS6/ops/c3live
[ "$(git -C "$LV_OPS6" rev-parse -q --verify HEAD 2>/dev/null)" = "$LV_OPS6_HEAD" ] || lv_no "ops6 $LV_OPS6 HEAD != ${LV_OPS6_HEAD:0:8} (ghim)"
git -C "$LV_OPS6" diff --quiet HEAD -- ops/c3live 2>/dev/null || lv_no "ops6 ops/c3live co sua CHUA commit"
[ "$(md5sum < "$LV_OPSD/golive_lib.sh" | cut -c1-32)" = "$LV_LIB_MD5" ] || lv_no "md5 golive_lib.sh != $LV_LIB_MD5 (ghim)"
DRY=$LV_DRY; export DRY
# shellcheck source=/dev/null
. "$LV_OPSD/golive_lib.sh"
DRY=$LV_DRY
gl_manifest_check "$LV_OPSD/golive_check_lev.sh" >/dev/null || lv_no "manifest ops6 lech (gl_manifest_check)"
[ "$C3_ACCOUNT" = SUB ] && [ "$KEYS_FILE" = "$LV_KEYS_SUB" ] || lv_no "sau source lib: C3_ACCOUNT=$C3_ACCOUNT KEYS_FILE=$KEYS_FILE khong phai SUB"
gl_init golive_set_lev1x
LVD=$LOGDIR/lev1x; mkdir -p "$LVD" || die "khong tao duoc $LVD"
exec 9> "$LVD/.lock"; flock -n 9 || die "dang co 1 golive_set_lev1x khac chay (khoa $LVD/.lock)"
say "script sha256 bat dau ${LV_SHA:0:12} (ban copy $LV_D) | ops6 ${LV_OPS6_HEAD:0:8} lib md5 ${LV_LIB_MD5:0:8} | test=$LV_TEST | nhip ${LV_PACE}s, nguong weight ${LV_WMAX}/phut, cho toi da ${LV_WAITMAX}s, LEV_CAP=$LV_CAP"

# ---- tai khoan: CHI SUB
gl_read_state || :   # ham lib ket thuc bang 'grep ERR= && die' => rc 1 khi KHONG loi; loi that => die ben trong ham
printf '%s\n' "$ST" | grep -qx END_STATE || die "doc trang thai 242 khong tron ven"
NP=$(sv NPROC); PK=$(sv ENV_LIVE_C3_KEYS_FILE); SRC="env process bot"
if [ "${NP:-0}" = 0 ]; then PK=$(sv ENVSH_LIVE_C3_KEYS_FILE); SRC="conf/env.sh (bot dang dung)"; fi
PK=${PK//\"/}; PK=${PK//\'/}
say "bot c3: $NP process, adapter=$(sv ENV_LIVE_ADAPTER) | file key bot dung ($SRC)=${PK:-KHONG_DAT} | file key sha8=$(sv KEYS_FILE_SHA8) quyen=$(sv KEYS_PERM)"
[ -n "$PK" ] || die "khong xac dinh duoc file key bot c3 dang dung (LIVE_C3_KEYS_FILE rong => jar dung keys.env tk CHINH) - khong phai SUB"
[ "$PK" = "$KEYS_FILE" ] || die "bot c3 dung file key '$PK' != $KEYS_FILE (tk con) - khong phai SUB"
[ "$(sv KEYS_OK)" = 1 ] || die "file key $KEYS_FILE khong hop le (600, 2 dong)"
[ "$(sv KEYS_FILE_SHA8)" = "$LV_SUB_SHA8_PIN" ] || die "sha8 key file $(sv KEYS_FILE_SHA8) != tk con da dang ky $LV_SUB_SHA8_PIN"
[ "$(sv KEYS_FILE_SHA8)" != "$LV_MAIN_SHA8_PIN" ] || die "key file = key tk CHINH"

# ---- goi san tu 242 (python tren 242 doc key tai cho; KHONG truyen key qua ssh). Moi tham so ASCII (da kiem).
lv_api() {   # $1 read|write  $2 danh sach symbol da xac nhan (percent-encode, phay) | NONE  $3 deadline epoch (0 = khong)
  local run=s242in
  [ "$1" = write ] && run=s242in_once   # buoc ghi: 1 lan, khong tu chay lai khi ssh loi (chay lai script = idempotent)
  "$run" "bash -s -- $A $1 $KEYS_FILE $PY242 $CURL242 $LV_FAPI ${2:-NONE} $LV_PACE $LV_WMAX $LV_WAITMAX $LV_ECONSEC $LV_SUB_SHA8_PIN $LV_MAIN_SHA8_PIN $LV_CAP ${3:-0}" <<'EOF'
A=$1; MODE=$2; KF=$3; PY=$4; CU=$5; shift 5; cd "$A" 2>/dev/null || { echo "ERR=cd"; echo END_API; exit 2; }
[ -x "$PY" ] || { echo "ERR=thieu_python_$PY"; echo END_API; exit 2; }
"$PY" -I - "$MODE" "$KF" "$CU" "$@" <<'PYEOF'
import hashlib, hmac, json, os, re, subprocess, sys, time
from urllib.parse import quote, unquote
mode, kf, cu, FAPI, allow_s, pace, wmax, waitmax, econ, pin_sub, pin_main, cap, deadline = sys.argv[1:14]
pace = float(pace); wmax = int(wmax); waitmax = int(waitmax); econ = int(econ); cap = float(cap); deadline = float(deadline)
def out(x):   # chi ghi ASCII (khong phu thuoc locale/LANG cua 242; python -I bo qua PYTHONIOENCODING)
    sys.stdout.buffer.write((str(x) + '\n').encode('ascii', 'backslashreplace')); sys.stdout.buffer.flush()
def fin(rc):
    out('END_API'); sys.exit(rc)
def enc(x): return quote(x, safe='')   # UTF-8 percent-encode (A-Z0-9 giu nguyen)
def isna(x): return enc(x) != x
# [m-1] doc key CUNG quy tac lib bash gl_state242: KEYS_OK = quyen 600 + dong neo ^C3_LIVE_API_(KEY|SECRET)= (khong strip dau dong);
#   KEYS_FILE_SHA8 = dong KEY DAU, bo moi ' \t\r"'. Them: dung 1 dong KEY + 1 dong SECRET (khac => tu choi).
k = s = None
try:
    st = os.stat(kf)
    with open(kf, encoding='utf-8') as fh: raw = fh.read()
except Exception as e:
    out('ERR=doc_keys_loi_' + type(e).__name__); fin(2)
kl = [l for l in raw.split('\n') if l.startswith('C3_LIVE_API_KEY=')]
sl = [l for l in raw.split('\n') if l.startswith('C3_LIVE_API_SECRET=')]
if (st.st_mode & 0o777) != 0o600 or len(kl) != 1 or len(sl) != 1:
    out('ERR=keys_khong_hop_le_%o_%d_%d' % (st.st_mode & 0o777, len(kl), len(sl))); fin(2)
k = re.sub('[ \t\r"]', '', kl[0].split('=', 1)[1]); s = re.sub('[ \t\r"]', '', sl[0].split('=', 1)[1]); raw = None
if not k or not s:
    k = s = None; out('ERR=keys_thieu_dong'); fin(2)
ks8 = hashlib.sha256(k.encode('utf-8')).hexdigest()[:8]
out('KEY_SHA8=' + ks8)
# [M-1] pin SUB / MAIN (hang trong script Oracle) - kiem TRUOC moi call (ca GET)
if not re.fullmatch('[0-9a-f]{8}', pin_sub) or ks8 != pin_sub or ks8 == pin_main:
    k = s = None; out('ERR=KEY_PIN'); out('KEY_PIN=key_%s_pin_sub_%s_pin_main_%s' % (ks8, pin_sub[:8], pin_main[:8])); fin(3)
W = {'n': 0, 'used': '', 'wait': 0.0, 'calls': 0, 'post': 0, 'ok': 0, 'err': 0, 'last': 0.0}
class Stop(Exception): pass
def clean(m): return re.sub(r'[^A-Za-z0-9 ._%-]', '', str(m))[:70]
def nap(t, why):   # [m-6] ngu t giay, in 1 dong trang thai moi <= 25 s
    end = time.time() + t
    while True:
        rem = end - time.time()
        if rem <= 0: break
        out('WAIT=%s_con_%ds' % (why, int(rem + 0.999)))
        time.sleep(min(25.0, rem))
def throttle():
    try: u = int(W['used'])
    except Exception: return
    if u < wmax: return
    t = 62 - (time.time() % 60)
    if W['wait'] + t > waitmax: raise Stop('weight_%d_ge_%d_cho_qua_%ds' % (u, wmax, waitmax))
    if deadline > 0 and time.time() + t >= deadline: raise Stop('cho_weight_vuot_khung_gio')
    nap(t, 'used_%d_ge_%d_ngu_%ds' % (u, wmax, int(t))); W['wait'] += t; W['used'] = ''
def call(method, path, w, qs=''):
    dt = time.time() - W['last']
    if dt < pace: time.sleep(pace - dt)
    q = (qs + '&' if qs else '') + 'timestamp=%d&recvWindow=10000' % int(time.time() * 1000)
    if not re.fullmatch(r'[A-Za-z0-9=&%._~-]+', q): raise Stop('query_khong_ascii')
    sig = hmac.new(s.encode('utf-8'), q.encode('utf-8'), hashlib.sha256).hexdigest()   # ky DUNG chuoi da percent-encode se gui
    cfg = 'url = "%s%s?%s&signature=%s"\nheader = "X-MBX-APIKEY: %s"\n' % (FAPI, path, q, sig, k)
    if method == 'POST': cfg += 'request = "POST"\n'
    W['n'] += w; W['calls'] += 1
    try:
        r = subprocess.run([cu, '-s', '-m', '15', '-D', '/dev/stderr', '-w', '\nHTTP=%{http_code}', '-K', '-'], input=cfg.encode('utf-8'),
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=40)
    except Exception as e:
        W['last'] = time.time(); return '000', None
    W['last'] = time.time()
    for hl in r.stderr.decode('utf-8', 'replace').splitlines():
        if hl.lower().startswith('x-mbx-used-weight-1m:'): W['used'] = hl.split(':', 1)[1].strip()
    o = r.stdout.decode('utf-8', 'replace')
    body, _, code = o.rpartition('\nHTTP=')
    code = code.strip()
    try: j = json.loads(body)
    except Exception: j = None
    ec = j.get('code') if isinstance(j, dict) else None
    if code in ('429', '418') or ec == -1003:
        raise Stop('HTTP%s_code%s_%s_%s' % (code, ec, method, path))
    throttle()
    return code, j
def lev(x):
    try: return int(str(x.get('leverage')))
    except Exception: return None
# [m-2] maxNotional: CUNG cong thuc golive_check_lev.sh:45-49 (awk tren LEVSYM '%s' cua maxNotionalValue): bo qua '' / 'None' / ^INF;
#   so sanh so (tien to so nhu awk, khong so => 0) < 4*0.0225*cap
CM = 4 * 0.0225 * cap
def awknum(v):
    mm = re.match(r'[ \t\n]*[-+]?(\d+\.?\d*|\.\d+)([eE][-+]?\d+)?', v)
    return float(mm.group(0)) if mm else 0.0
def mxv(x): return '%s' % x.get('maxNotionalValue')
def mxbad(x):
    v = mxv(x)
    return not (v == '' or v == 'None' or v.startswith('INF')) and awknum(v) < CM
def mtbad(x): return ('%s' % x.get('marginType')).upper() != 'CROSSED'
def lst(xs, f=None): return ','.join(enc(x) + ((':' + f(x)) if f else '') for x in xs)
try:
    try:
        with open('run/c3live_exchangeInfo.json', encoding='utf-8') as fh: ex = json.load(fh)
        sl = ex.get('symbols') if isinstance(ex, dict) else None
        U = sorted(x['symbol'] for x in (sl or []) if isinstance(x, dict) and isinstance(x.get('symbol'), str)
                   and x.get('status') == 'TRADING' and x.get('quoteAsset') == 'USDT' and x.get('contractType') == 'PERPETUAL')
    except Exception as e:
        out('ERR=universe_' + type(e).__name__); raise Stop('universe')
    if not U: out('ERR=universe_rong'); raise Stop('universe_rong')
    US = set(U); ok = True
    code, ac = call('GET', '/fapi/v3/account', 5); out('ACC_HTTP=' + code)
    if code == '200' and isinstance(ac, dict): out('TMB=%s' % clean(ac.get('totalMarginBalance')))
    else: ok = False; out('ERR_ACC=HTTP%s' % code)
    code, sc = call('GET', '/fapi/v1/symbolConfig', 5); out('LEV_HTTP=' + code)
    if code != '200' or not isinstance(sc, list): ok = False; out('ERR_LEV=HTTP%s' % code); sc = []
    code, pr = call('GET', '/fapi/v3/positionRisk', 5); out('POS_HTTP=' + code)
    if code != '200' or not isinstance(pr, list): ok = False; out('ERR_POS=HTTP%s' % code); pr = []
    code, oo = call('GET', '/fapi/v1/openOrders', 40); out('ORD_HTTP=' + code)
    if code != '200' or not isinstance(oo, list): ok = False; out('ERR_ORD=HTTP%s' % code); oo = []
    code, ao = call('GET', '/fapi/v1/openAlgoOrders', 40); out('ALGO_HTTP=' + code)
    if isinstance(ao, dict) and 'code' not in ao: ao = ao.get('orders', ao.get('rows', []))
    if code != '200' or not isinstance(ao, list): ok = False; out('ERR_ALGO=HTTP%s' % code); ao = []
    if not ok: out('READ_OK=0'); raise Stop('doc_san_loi')
    m = {x['symbol']: x for x in sc if isinstance(x, dict) and isinstance(x.get('symbol'), str)}
    pos = set()
    for p in pr:
        try:
            if isinstance(p, dict) and float(p.get('positionAmt') or 0) != 0: pos.add(str(p.get('symbol')))
        except Exception: pos.add(str(p.get('symbol')))
    ords = {str(o.get('symbol')) for o in oo + ao if isinstance(o, dict)}
    busy = pos | ords
    miss = [x for x in U if x not in m]
    levbad = [x for x in U if x in m and lev(m[x]) != 1]
    mbad = [x for x in U if x in m and mtbad(m[x])]
    xbad = [x for x in U if x in m and mxbad(m[x])]
    outu = [x for x in m if x not in US and lev(m[x]) != 1]
    skip = [x for x in levbad if x in busy]
    plan0 = [x for x in levbad if x not in busy]
    plan = [x for x in plan0 if not isna(x)] + [x for x in plan0 if isna(x)]   # [B-1] non-ASCII SAU CUNG
    dist = {}
    for x in U:
        if x in m: dist[lev(m[x])] = dist.get(lev(m[x]), 0) + 1
    out('UNI=%d' % len(U)); out('UNI_NA=%d %s' % (len([x for x in U if isna(x)]), lst([x for x in U if isna(x)])))
    out('CFG_IN_UNI=%d' % (len(U) - len(miss))); out('MISS=%d %s' % (len(miss), lst(miss[:10])))
    out('DIST_LEV=' + ' '.join('%sx:%d' % (a, b) for a, b in sorted(dist.items(), key=lambda z: (z[0] is None, z[0] or 0))))
    out('N_LEV=%d' % len(levbad)); out('LEV_LIST=' + lst(levbad, lambda x: str(lev(m[x]))))
    out('N_MARGIN=%d' % len(mbad)); out('MARGIN_LIST=' + lst(mbad, lambda x: clean(m[x].get('marginType'))))
    out('CLUSTER_MAX=%.2f' % CM); out('N_MAXNOTIONAL=%d' % len(xbad)); out('MAXNOTIONAL_LIST=' + lst(xbad, lambda x: clean(mxv(m[x]))))
    out('N_POS=%d' % len(pos)); out('N_ORDSYM=%d' % len(ords)); out('BUSY_LIST=' + lst(sorted(busy)))
    out('N_SKIP=%d' % len(skip)); out('SKIP_LIST=' + lst(skip))
    out('N_OUTUNI_LEV=%d' % len(outu))
    out('N_PLAN=%d' % len(plan)); out('PLAN=' + lst(plan))
    out('N_PLAN_NA=%d' % len([x for x in plan if isna(x)])); out('PLAN_NA=' + lst([x for x in plan if isna(x)]))
    out('W_EST_WRITE=%d' % (len(plan) + 5 + 95)); out('T_EST_S=%d' % int(len(plan) * max(pace, 0.05) + 10))
    out('READ_OK=1')
    if mode == 'write':
        allow = [a for a in allow_s.split(',') if a] if allow_s != 'NONE' else []
        encU = {enc(x) for x in U}
        bad = [a for a in allow if a not in encU or not re.fullmatch('[A-Z0-9%]+', a)]
        if bad: out('ERR=ke_hoach_ngoai_universe_%d' % len(bad)); raise Stop('ke_hoach_ngoai_universe')
        allow = set(allow)
        todo = [x for x in plan if enc(x) in allow]
        nc = [x for x in plan if enc(x) not in allow]
        out('N_TODO=%d' % len(todo)); out('NOT_CONFIRMED=%d %s' % (len(nc), lst(nc)))
        out('W_PRE=%s' % (W['used'] or '?')); throttle()   # weight hien tai truoc POST dau; >= nguong => cho
        consec = 0
        for sy in todo:
            if deadline > 0 and time.time() >= deadline: raise Stop('het_khung_gio_truoc_phut_cam')
            na = isna(sy); e = enc(sy)
            W['post'] += 1
            code, j = call('POST', '/fapi/v1/leverage', 1, 'symbol=%s&leverage=1' % e)
            if code == '200' and isinstance(j, dict) and lev(j) == 1 and j.get('symbol') == sy:
                W['ok'] += 1; consec = 0; out('CHG=%s:%s->1' % (e, lev(m[sy])))
            else:
                ec = j.get('code') if isinstance(j, dict) else None
                msg = j.get('msg') if isinstance(j, dict) else ''
                W['err'] += 1; out('ERRSYM=%s:HTTP%s:%s:%s' % (e, code, ec, clean(msg)))
                if na: out('MANUAL=%s:HTTP%s:%s' % (e, code, ec)); continue   # [B-1] non-ASCII: khong abort, owner lam tay
                consec += 1
                if ec in (-2014, -2015, -1022): raise Stop('loi_xac_thuc_%s' % ec)
                if consec >= econ: raise Stop('%d_loi_lien_tiep' % consec)
        code, sc2 = call('GET', '/fapi/v1/symbolConfig', 5); out('VERIFY_HTTP=' + code)
        if code != '200' or not isinstance(sc2, list): out('VERIFY_OK=0')
        else:
            m2 = {x['symbol']: x for x in sc2 if isinstance(x, dict) and isinstance(x.get('symbol'), str)}
            rem = [x for x in U if x in m2 and lev(m2[x]) != 1]
            mb2 = [x for x in U if x in m2 and mtbad(m2[x])]
            xb2 = [x for x in U if x in m2 and mxbad(m2[x])]
            out('VERIFY_OK=1'); out('CFG_AFTER=%d' % len([x for x in U if x in m2]))
            out('N_REMAIN=%d' % len(rem)); out('REMAIN=' + lst(rem, lambda x: str(lev(m2[x]))))
            out('REMAIN_NA=' + lst([x for x in rem if isna(x)]))
            out('N_MARGIN_AFTER=%d' % len(mb2)); out('MARGIN_AFTER_LIST=' + lst(mb2, lambda x: clean(m2[x].get('marginType'))))
            out('N_MAXN_AFTER=%d' % len(xb2)); out('MAXN_AFTER_LIST=' + lst(xb2, lambda x: clean(mxv(m2[x]))))
except Stop as e:
    out('STOP=%s' % clean(e))
finally:
    out('N_POST=%d' % W['post']); out('N_OK=%d' % W['ok']); out('N_ERR=%d' % W['err'])
    out('W_NOMINAL=%d' % W['n']); out('W_USED_1M=%s' % clean(W['used'] or '?')); out('W_WAIT_S=%d' % int(W['wait'])); out('N_CALLS=%d' % W['calls'])
    k = s = None
    out('END_API')
PYEOF
EOF
}
# lv_run: goi lv_api, STREAM dong trang thai (WAIT/CHG/...) ra man hinh, giu toan bo output vao LVO; LV_RC = ma thoat ssh/python
LVO=""; LV_RC=0
lv_run() {
  local f=$LVD/.o_${1}_$TS
  LV_RC=0
  lv_api "$1" "$2" "$3" | tee "$f" | sed -u -n -E '/^(CHG|ERRSYM|MANUAL|WAIT|STOP|W_PRE)=/p' || LV_RC=$?
  LVO=$(cat "$f"); rm -f "$f"
}
lv() { printf '%s\n' "$LVO" | sed -n "s/^$1=//p" | head -1; }
lv_has() { printf '%s\n' "$LVO" | grep -q "$1"; }
lv_dec() {   # danh sach percent-encode (phay, co the kem :x) -> "goc (encode)" de owner doc; CHI hien thi
  python3 -I -c 'import sys, urllib.parse as u
r = []
for it in sys.argv[1].split(","):
    if not it: continue
    e = it.split(":", 1)[0]; d = u.unquote(e, errors="replace")
    r.append(d + " (" + it + ")" if d != e else it)
sys.stdout.buffer.write((", ".join(r) + "\n").encode("utf-8"))' "$1"
}
lv_keypin_msg() { echo "ERR KEY_PIN: key doc tren 242 sha8=$(lv KEY_SHA8) khong phai tk con $LV_SUB_SHA8_PIN (hoac = tk CHINH $LV_MAIN_SHA8_PIN) - 0 request"; }
lv_check_read() {
  lv_has '^END_API$' || die "goi API khong tron ven (ssh dut? ma $LV_RC)"
  [ "$(lv ERR)" != KEY_PIN ] || die "$(lv_keypin_msg)"
  ! lv_has '^ERR=' || die "$(printf '%s\n' "$LVO" | grep '^ERR=' | head -1)"
  [ "$LV_RC" = 0 ] || die "phien doc tra ma $LV_RC"
  [ "$(lv KEY_SHA8)" = "$LV_SUB_SHA8_PIN" ] || die "key ky san $(lv KEY_SHA8) != tk con $LV_SUB_SHA8_PIN"
  [ "$(lv KEY_SHA8)" != "$LV_MAIN_SHA8_PIN" ] || die "key ky san = key tk CHINH"
  [ -z "$(lv STOP)" ] || die "doc san DUNG: $(lv STOP) ($(printf '%s\n' "$LVO" | sed -n '/^ERR_/p' | tr '\n' ' '))"
  [ "$(lv READ_OK)" = 1 ] || die "doc san loi ($(printf '%s\n' "$LVO" | sed -n '/^ERR_/p' | tr '\n' ' '))"
}
lv_show() {
  say "san: key_sha8=$(lv KEY_SHA8) totalMarginBalance=$(lv TMB) | universe=$(lv UNI) co_cfg=$(lv CFG_IN_UNI) thieu_cfg=$(lv MISS)"
  say "universe ten non-ASCII: $(lv UNI_NA)"
  say "phan bo leverage (universe): $(lv DIST_LEV)"
  say "leverage != 1: $(lv N_LEV) | marginType != CROSSED: $(lv N_MARGIN) (CHI BAO, KHONG sua) $(lv MARGIN_LIST)"
  say "N_MAXNOTIONAL (maxNotionalValue < $(lv CLUSTER_MAX) = 4 x 0,0225 x LEV_CAP $LV_CAP, CHI BAO): $(lv N_MAXNOTIONAL) $(lv MAXNOTIONAL_LIST)"
  say "symbol co vi the: $(lv N_POS), co lenh mo (thuong+algo): $(lv N_ORDSYM) [$(lv BUSY_LIST)]"
  say "BO QUA (lev != 1 nhung co vi the/lenh): $(lv N_SKIP) $(lv SKIP_LIST)"
  say "ngoai universe co lev != 1: $(lv N_OUTUNI_LEV) (KHONG dong)"
  say "KE HOACH dat 1x: $(lv N_PLAN) symbol: $(lv PLAN)"
  [ "$(lv N_PLAN_NA)" = 0 ] || say "  trong do $(lv N_PLAN_NA) symbol ten non-ASCII (POST SAU CUNG; san loi => CAN LAM TAY): $(lv_dec "$(lv PLAN_NA)")"
  say "uoc: weight ~$(lv W_EST_WRITE) (95 doc + 1/POST + 5 doc lai), thoi gian ~$(lv T_EST_S) s | weight doc vua dung=$(lv W_NOMINAL), X-MBX-USED-WEIGHT-1M=$(lv W_USED_1M)"
}
lv_manual() {   # khoi CAN LAM TAY: symbol non-ASCII con != 1x (sau doc lai) hoac loi khi POST (neu khong doc lai duoc)
  local l
  l=$(lv REMAIN_NA)
  if [ -z "$l" ]; then l=$(printf '%s\n' "$LVO" | sed -n 's/^MANUAL=//p' | cut -d: -f1 | tr '\n' ',' | sed 's/,$//'); fi
  [ -n "$l" ] || return 0
  say "loi san symbol non-ASCII: $(printf '%s\n' "$LVO" | sed -n 's/^MANUAL=//p' | tr '\n' ' ')"
  say "CAN LAM TAY: $(lv_dec "$l") - owner dat 1x bang tay tren app Binance (tai khoan con)"
}
lv_result() {   # $1 KET QUA, $2 rc
  local R=$LVD/LEV1X_${C3_ACCOUNT}_$TS.txt
  { echo "golive_set_lev1x $C3_ACCOUNT $TS key_sha8=$(lv KEY_SHA8) KET QUA: $1"
    echo "script_sha256_12=${LV_SHA:0:12} ops6=${LV_OPS6_HEAD:0:8} DRY=$DRY test=$LV_TEST LEV_CAP=$LV_CAP"
    echo "truoc: UNI=${R_UNI:-?} N_LEV=${R_NLEV:-?} N_MARGIN=${R_NM:-?} N_MAXNOTIONAL=${R_NX:-?} N_SKIP=${R_SKIP:-?} N_PLAN=${R_PLAN:-?}"
    echo "truoc_LEV_LIST=${R_LEVL:-}"
    echo "bo_qua_vi_the_lenh=${R_SKIPL:-}"
    printf '%s\n' "$LVO" | sed -n -E '/^(N_TODO|NOT_CONFIRMED|W_PRE|N_POST|N_OK|N_ERR|STOP|VERIFY_OK|CFG_AFTER|N_REMAIN|REMAIN|REMAIN_NA|N_MARGIN_AFTER|MARGIN_AFTER_LIST|N_MAXN_AFTER|MAXN_AFTER_LIST|W_NOMINAL|W_USED_1M|W_WAIT_S|WAIT|ERR|KEY_PIN)=/p'
    echo "da_doi:"; printf '%s\n' "$LVO" | sed -n '/^CHG=/p'
    echo "loi:"; printf '%s\n' "$LVO" | sed -n '/^ERRSYM=/p'
    echo "can_lam_tay:"; printf '%s\n' "$LVO" | sed -n '/^MANUAL=/p'
  } > "$R"
  say "KET QUA: $1. File: $R"
  say "TIEP: chay lai golive_check_lev.sh de sinh LEV_EV that: LEV_CAP=$LV_CAP bash $LV_OPSD/golive_check_lev.sh"
  exit "$2"
}
# phan loai: DAT chi khi lev=0 VA margin=0 VA maxNotional=0 VA co cfg; chi con margin/maxNotional => CANH BAO
lv_final() {   # $1 n_lev $2 n_margin $3 n_maxn $4 n_cfg $5 danh sach lev $6 ds margin $7 ds maxn  -> echo "KET_QUA|rc"
  if [ "$1" = 0 ] && [ "$2" = 0 ] && [ "$3" = 0 ] && [ "${4:-0}" -gt 0 ]; then echo "DAT|0"
  elif [ "$1" = 0 ]; then echo "CANH BAO (leverage xong; marginType != CROSSED: $2 [$6]; maxNotional < $(lv CLUSTER_MAX): $3 [$7]; co_cfg=$4)|4"
  else echo "CON $1 ($5)|3"; fi
}

# ---- doc san
lv_run read NONE 0
lv_check_read; lv_show
R_UNI=$(lv UNI); R_NLEV=$(lv N_LEV); R_NM=$(lv N_MARGIN); R_NX=$(lv N_MAXNOTIONAL); R_SKIP=$(lv N_SKIP); R_PLAN=$(lv N_PLAN)
R_LEVL=$(lv LEV_LIST); R_SKIPL=$(lv SKIP_LIST); R_CFG=$(lv CFG_IN_UNI)
PL=$(lv PLAN)
[[ "$PL" =~ $LV_RE_PLAN ]] || die "danh sach ke hoach co ky tu la (ngoai A-Z 0-9 % ,)"
LV_F=$(lv_final "$R_NLEV" "$R_NM" "$R_NX" "$R_CFG" "$R_LEVL" "$(lv MARGIN_LIST)" "$(lv MAXNOTIONAL_LIST)")
if [ "$DRY" = 1 ]; then
  say "DRY=1: KHONG ghi san (chi doc). Chay that: them DRY=0 (go 'YES LEV1X')."
  case "$LV_F" in
    DAT*) say "KET QUA (DRY): DAT - 0 symbol != 1x, 0 marginType lech, 0 maxNotional thap"; exit 0;;
    CANH*) say "KET QUA (DRY): ${LV_F%|*}"; exit 4;;
  esac
  say "KET QUA (DRY): CON $R_NLEV symbol != 1x (ke hoach $R_PLAN, bo qua $R_SKIP; marginType lech $R_NM, maxNotional thap $R_NX)"; exit 3
fi
if [ "$R_PLAN" = 0 ]; then lv_result "${LV_F%|*}" "${LV_F##*|}"; fi
say ">>> Se POST /fapi/v1/leverage leverage=1 cho $R_PLAN symbol tren tk CON (SUB). Go 'YES LEV1X' trong ${LV_YES_T} s de tiep tuc:"
ANS=""; YRC=0
IFS= read -r -t "$LV_YES_T" ANS || YRC=$?
[ "$YRC" -le 128 ] || { say "Het thoi gian xac nhan - KHONG doi gi."; say "KET QUA: TU_CHOI"; exit 1; }
[ "$ANS" = "YES LEV1X" ] || { say "Khong xac nhan (phai go CHINH XAC 'YES LEV1X') - KHONG doi gi."; say "KET QUA: TU_CHOI"; exit 1; }
lv_window || { say "TU CHOI [khung gio]: $LV_WIN_MSG - KHONG doi gi."; say "KET QUA: TU_CHOI"; exit 1; }
say "W_USED_1M (phien doc) = $(lv W_USED_1M), nguong $LV_WMAX; POST dung truoc $(TZ=Asia/Ho_Chi_Minh date -d "@$LV_DEADLINE" +%H:%M:%S) (phut cam ke tiep)"
# ---- ghi (stream ra man hinh + file tam)
say "dang ghi... (uoc ~$(lv T_EST_S) s; Ctrl-C an toan: chay lai = idempotent)"
lv_run write "$PL" "$LV_DEADLINE"
lv_has '^END_API$' || { say "!! goi ghi KHONG tron ven (ssh dut? ma $LV_RC) - trang thai chua ro, chay lai DRY de xem"; lv_result "DUNG (ssh dut, chua ro)" 1; }
[ "$(lv ERR)" != KEY_PIN ] || lv_result "DUNG ($(lv_keypin_msg))" 1
! lv_has '^ERR=' || lv_result "DUNG ($(printf '%s\n' "$LVO" | grep '^ERR=' | head -1))" 1
[ "$LV_RC" = 0 ] || lv_result "DUNG (phien ghi tra ma $LV_RC)" 1
[ "$(lv KEY_SHA8)" = "$LV_SUB_SHA8_PIN" ] || lv_result "DUNG (key $(lv KEY_SHA8) != tk con)" 1
say "da POST $(lv N_POST): OK $(lv N_OK), loi $(lv N_ERR); chua xac nhan (moi phat sinh, KHONG dong) $(lv NOT_CONFIRMED); weight X-MBX-USED-WEIGHT-1M=$(lv W_USED_1M) cho=$(lv W_WAIT_S)s"
[ "$(lv N_ERR)" = 0 ] || say "loi tung symbol: $(printf '%s\n' "$LVO" | sed -n 's/^ERRSYM=//p' | tr '\n' ' ')"
[ -z "$(lv STOP)" ] || { lv_manual; lv_result "DUNG ($(lv STOP)); da doi $(lv N_OK)" 1; }
[ "$(lv VERIFY_OK)" = 1 ] || { lv_manual; lv_result "DUNG (doc lai symbolConfig loi HTTP$(lv VERIFY_HTTP))" 1; }
LV_F=$(lv_final "$(lv N_REMAIN)" "$(lv N_MARGIN_AFTER)" "$(lv N_MAXN_AFTER)" "$(lv CFG_AFTER)" "$(lv REMAIN)" "$(lv MARGIN_AFTER_LIST)" "$(lv MAXN_AFTER_LIST)")
lv_manual
lv_result "${LV_F%|*}" "${LV_F##*|}"
