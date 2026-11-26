#!/usr/bin/env bash
# test_set_lev1x.sh - test golive_set_lev1x.sh trong sandbox /tmp: 242 gia (SSH_242="bash -c", APP_DIR tam), san gia (fake curl python,
#   trang thai file, KIEM chu ky HMAC tren DUNG chuoi query percent-encode nhan duoc + kiem query da encode chuan), LV1X_TEST=1
#   (FAPI = https://lv1x-test.invalid + proxy 127.0.0.1:9). KHONG goi san / 242 that. Chay: bash test/test_set_lev1x.sh (~3 phut)
set -uo pipefail
HERE=$(cd "$(dirname "$0")/.." && pwd); S=$HERE/golive_set_lev1x.sh
W=$(mktemp -d /tmp/lv1x_test.XXXXXX); F=$W/f
mkdir -p "$F/run" "$F/conf" "$F/target" "$F/logs" "$W/api" "$W/deploy"
ls -d /tmp/lv1x_run.* 2>/dev/null | sort > "$W/runs_before"
: > "$F/target/binance-java-sdk-1.2.4.jar"
KEY=fakekey_lv1x_$(head -c 12 /dev/urandom | od -An -tx1 | tr -d ' \n'); SEC=fakesecret_lv1x_$(head -c 12 /dev/urandom | od -An -tx1 | tr -d ' \n')
KEY2=fakekey2_lv1x_$(head -c 12 /dev/urandom | od -An -tx1 | tr -d ' \n')
KF=$W/keys_sub.env
keys_ok() { printf 'C3_LIVE_API_KEY=%s\nC3_LIVE_API_SECRET=%s\n' "$KEY" "$SEC" > "$KF"; chmod 600 "$KF"; }
keys_ok
SK8=$(printf '%s' "$KEY" | sha256sum | cut -c1-8); SK8_2=$(printf '%s' "$KEY2" | sha256sum | cut -c1-8)
echo "export LIVE_C3_KEYS_FILE=$KF" > "$F/conf/env.sh"
sym() { printf '{"symbol":"%s","status":"%s","quoteAsset":"%s","contractType":"%s"}' "$1" "$2" "$3" "$4"; }
EXI="$(sym AAAUSDT TRADING USDT PERPETUAL),$(sym BBBUSDT TRADING USDT PERPETUAL),$(sym CCCUSDT TRADING USDT PERPETUAL),$(sym DDDUSDT TRADING USDT PERPETUAL),$(sym EEEUSDT TRADING USDT PERPETUAL),$(sym OUTUSDT SETTLING USDT PERPETUAL),$(sym XXXBUSD TRADING BUSD PERPETUAL),$(sym QQQUSDT TRADING USDT CURRENT_QUARTER)"
echo "{\"symbols\":[$EXI]}" > "$F/run/c3live_exchangeInfo.json"
cat > "$W/fakecurl.py" <<EOC
#!/usr/bin/env python3
# LV1X_FAKE_CURL - san gia: doc cau hinh curl tu stdin, KHONG mo mang
import hashlib, hmac, json, re, sys
from urllib.parse import quote, unquote
st_p = '$W/api/state.json'; log_p = '$W/api/calls.log'; SEC = '$SEC'; KEY = '$KEY'
cfg = sys.stdin.buffer.read().decode('utf-8')
url = re.search(r'url = "([^"]*)"', cfg).group(1); hdr = re.search(r'header = "([^"]*)"', cfg)
meth = 'POST' if 'request = "POST"' in cfg else 'GET'
st = json.load(open(st_p, encoding='utf-8'))
def resp(code, body):
    us = st.get('used_seq')
    used = us.pop(0) if us else st.get('used', 50)
    sys.stderr.write('HTTP/1.1 %s\r\nx-mbx-used-weight-1m: %s\r\n\r\n' % (code, used))
    sys.stdout.write(json.dumps(body) + '\nHTTP=%s' % code); json.dump(st, open(st_p, 'w')); sys.exit(0)
base, _, qs = url.partition('?'); q, _, sig = qs.rpartition('&signature=')
ep = base.rsplit('/', 1)[1]; raw = dict(x.split('=', 1) for x in q.split('&'))
open(log_p, 'a', encoding='utf-8').write('%s %s %s %s\n' % (meth, ep, raw.get('symbol', '-'), base.split('/fapi')[0]))
if not base.startswith('https://lv1x-test.invalid/'): resp(400, {'code': -9999, 'msg': 'BADHOST'})
if not hdr or hdr.group(1) != 'X-MBX-APIKEY: ' + KEY: resp(401, {'code': -2015, 'msg': 'bad key'})
if any(quote(unquote(v), safe='') != v for v in raw.values()): resp(400, {'code': -1100, 'msg': 'Illegal characters found in parameter'})
if sig != hmac.new(SEC.encode('utf-8'), q.encode('utf-8'), hashlib.sha256).hexdigest(): resp(400, {'code': -1022, 'msg': 'Signature for this request is not valid.'})
par = {a: unquote(b) for a, b in raw.items()}
cf = st['cfg']
if ep == 'account': resp(200, {'totalMarginBalance': '1000.0', 'availableBalance': '900.0'})
if ep == 'symbolConfig': resp(200, [{'symbol': s, 'marginType': v[1], 'isAutoAddMargin': False, 'leverage': v[0], 'maxNotionalValue': v[2] if len(v) > 2 else '1000000'} for s, v in sorted(cf.items())])
if ep == 'positionRisk': resp(200, [{'symbol': s, 'positionAmt': a} for s, a in st.get('pos', {}).items()])
if ep == 'openOrders': resp(200, [{'symbol': s, 'clientOrderId': 'c3-x'} for s in st.get('ord', [])])
if ep == 'openAlgoOrders': resp(200, [{'symbol': s, 'clientAlgoId': 'c3s-x'} for s in st.get('algo', [])])
if ep == 'leverage' and meth == 'POST':
    s = par['symbol']; f = st.get('fail', {}).get(s)
    if not f and quote(s, safe='') != s: f = st.get('fail_na')
    if f: resp(f[0], {'code': f[1], 'msg': f[2]})
    if s not in cf: resp(400, {'code': -1121, 'msg': 'Invalid symbol.'})
    cf[s][0] = int(par['leverage']); resp(200, {'symbol': s, 'leverage': int(par['leverage']), 'maxNotionalValue': '50000000'})
resp(404, {'code': -5000, 'msg': 'no ep'})
EOC
chmod +x "$W/fakecurl.py"
state() { printf '%s' "$1" > "$W/api/state.json"; }
pst() { python3 -c "import json,sys; json.dump(eval(sys.argv[1]), open('$W/api/state.json', 'w'))" "$1"; }   # dict python (\\u cho chu Han)
BASE='"cfg":{"AAAUSDT":[1,"CROSSED"],"BBBUSDT":[1,"CROSSED"],"CCCUSDT":[20,"CROSSED"],"DDDUSDT":[20,"CROSSED"],"EEEUSDT":[20,"CROSSED"],"OUTUSDT":[20,"CROSSED"],"XXXBUSD":[20,"CROSSED"],"QQQUSDT":[20,"ISOLATED"],"NOTINEXUSDT":[20,"CROSSED"]}'
state "{$BASE,\"pos\":{\"EEEUSDT\":\"5\"}}"
SHA=$(sha256sum "$S" | cut -c1-64)
HB=$(( $(date +%s) / 3600 * 3600 )); NOW10=$(( HB + 600 ))   # gio gia: phut :10 (ngoai khung cam) - CHI hieu luc khi LV1X_TEST=1
E() { env SSH_242="bash -c" APP_DIR="$F" PROC_PAT=LV1XNOPROCZZ ING_PAT=LV1XNOINGZZ KEYS_FILE="$KF" SUB_KEY_SHA8="$SK8" \
  PY242=/usr/bin/python3 CURL242="$W/fakecurl.py" LOGDIR="$W/deploy" WD_PAUSE="$W/pause" LV1X_TEST=1 LV1X_TEST_SUB_SHA8="$SK8" \
  LV1X_TEST_NOW_EPOCH="$NOW10" LV1X_PACE_S=0 A1_LEV1X_APPROVED="$SHA" SSH_RETRY_S=1 "$@"; }
P=0; N=0; ALL=""
chk() { N=$((N+1)); if eval "$2"; then P=$((P+1)); echo "PASS $N: $1"; else echo "FAIL $N: $1"; echo "----- output:"; echo "$OUT" | tail -25; echo "-----"; fi; }
run() { OUT=$("$@" 2>&1); RC=$?; ALL="$ALL
$OUT"; }
runin() { local i=$1; shift; OUT=$(printf '%s\n' "$i" | "$@" 2>&1); RC=$?; ALL="$ALL
$OUT"; }
YESP="Go 'YES LEV1X'"
posts() { grep -c '^POST ' "$W/api/calls.log" 2>/dev/null || true; }
calls() { grep -c '' "$W/api/calls.log" 2>/dev/null || true; }
levof() { python3 -c "import json,sys;print(json.load(open('$W/api/state.json'))['cfg'][sys.argv[1].encode().decode('unicode_escape')][0])" "$1"; }
: > "$W/api/calls.log"

echo "== chot chan"
run E env -u A1_LEV1X_APPROVED bash "$S"
chk "thieu A1_LEV1X_APPROVED => TU CHOI rc 1, 0 goi san" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'TU CHOI: \[A1\]' && [ \$(calls) = 0 ]"
run E A1_LEV1X_APPROVED=0000000000000000000000000000000000000000000000000000000000000000 bash "$S"
chk "A1_LEV1X_APPROVED sai => TU CHOI rc 1, 0 goi san" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'TU CHOI: \[A1\]' && [ \$(calls) = 0 ]"
run env A1_LEV1X_APPROVED="$SHA" SSH_242="bash -c" bash "$S"
chk "che do that (khong LV1X_TEST) + SSH_242 ghi de => TU CHOI (khong the tro 242/san gia vao che do that)" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'bien SSH_242 dat tu env' && [ \$(calls) = 0 ]"
run E SSH_242="ssh -p 2222 root@103.157.218.242" bash "$S"
chk "LV1X_TEST=1 nhung SSH_242 = 242 that => TU CHOI" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q '\[TEST\] SSH_242' && [ \$(calls) = 0 ]"
run E CURL242=curl bash "$S"
chk "LV1X_TEST=1 nhung CURL242 = curl that => TU CHOI" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q '\[TEST\] CURL242' && [ \$(calls) = 0 ]"
run E C3_ACCOUNT=MAIN bash "$S"
chk "C3_ACCOUNT=MAIN => TU CHOI" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'CHI tac dong tai khoan con SUB' && [ \$(calls) = 0 ]"
echo "export LIVE_C3_KEYS_FILE=/root/.config/c3live/keys.env" > "$F/conf/env.sh"
run E bash "$S"
chk "bot dung file key tk CHINH (env.sh) => khong phai SUB => TU CHOI, 0 goi san" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'khong phai SUB' && [ \$(calls) = 0 ]"
: > "$F/conf/env.sh"
run E bash "$S"
chk "LIVE_C3_KEYS_FILE khong dat (jar mac dinh keys.env) => TU CHOI" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'khong xac dinh duoc file key' && [ \$(calls) = 0 ]"
echo "export LIVE_C3_KEYS_FILE=$KF" > "$F/conf/env.sh"
run E LV1X_TEST_SUB_SHA8=deadbeef bash "$S"
chk "sha8 key file != tk con da dang ky => TU CHOI, 0 goi san" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'sha8 key file' && [ \$(calls) = 0 ]"

echo "== DRY"
run E bash "$S"
chk "DRY mac dinh: rc 3, ke hoach CCC+DDD, bo qua EEE (vi the), 0 POST, trang thai khong doi" "[ $RC = 3 ] && echo \"\$OUT\" | grep -q 'KE HOACH dat 1x: 2 symbol: CCCUSDT,DDDUSDT' && echo \"\$OUT\" | grep -q 'BO QUA.*: 1 EEEUSDT' && [ \$(posts) = 0 ] && [ \$(levof CCCUSDT) = 20 ] && echo \"\$OUT\" | grep -q 'DRY=1: KHONG ghi'"
chk "DRY: universe = 5 (loai SETTLING/BUSD/QUARTER), marginType ISOLATED ngoai universe khong tinh, in phan bo + weight" "echo \"\$OUT\" | grep -q 'universe=5 ' && echo \"\$OUT\" | grep -q 'marginType != CROSSED: 0' && echo \"\$OUT\" | grep -q 'ngoai universe co lev != 1: 4' && echo \"\$OUT\" | grep -q 'X-MBX-USED-WEIGHT-1M=50'"
run E DRY=yes bash "$S"
chk "DRY=yes (khac 0) => van DRY, 0 POST" "[ $RC = 3 ] && echo \"\$OUT\" | grep -q 'DRY=1: KHONG ghi' && [ \$(posts) = 0 ]"

echo "== xac nhan"
runin no E DRY=0 bash "$S"
chk "DRY=0 go sai => TU CHOI rc 1, 0 POST" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q \"\$YESP\" && echo \"\$OUT\" | grep -q 'Khong xac nhan' && [ \$(posts) = 0 ]"
runin YES E DRY=0 bash "$S"
chk "DRY=0 go 'YES' (thieu LEV1X) => TU CHOI, 0 POST" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q \"\$YESP\" && echo \"\$OUT\" | grep -q 'Khong xac nhan' && [ \$(posts) = 0 ]"
OUT=$(sleep 4 | E DRY=0 LV1X_YES_TIMEOUT_S=1 bash "$S" 2>&1); RC=$?; ALL="$ALL
$OUT"
chk "DRY=0 het gio xac nhan => TU CHOI, 0 POST" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'Het thoi gian' && [ \$(posts) = 0 ]"

echo "== ghi"
: > "$W/api/calls.log"
runin "YES LEV1X" E DRY=0 bash "$S"
RF=$(ls -t "$W"/deploy/lev1x/LEV1X_SUB_*.txt 2>/dev/null | head -1)
chk "5 symbol (2 x1, 2 x20, 1 x20 co vi the): POST dung CCC+DDD, rc 3, KET QUA CON 1 EEE" "[ $RC = 3 ] && [ \$(posts) = 2 ] && grep -q '^POST leverage CCCUSDT' $W/api/calls.log && grep -q '^POST leverage DDDUSDT' $W/api/calls.log && echo \"\$OUT\" | grep -q 'KET QUA: CON 1 (EEEUSDT:20)'"
chk "EEE (co vi the) + symbol ngoai universe (OUT/XXX/QQQ/NOTINEX) KHONG bi dong, van 20x" "[ \$(levof EEEUSDT) = 20 ] && [ \$(levof OUTUSDT) = 20 ] && [ \$(levof XXXBUSD) = 20 ] && [ \$(levof QQQUSDT) = 20 ] && [ \$(levof NOTINEXUSDT) = 20 ] && ! grep -qE '^POST leverage (EEE|OUT|XXX|QQQ|NOTINEX)' $W/api/calls.log"
chk "file ket qua co KET QUA, da_doi 2, bo_qua EEE, N_REMAIN=1" "[ -n '$RF' ] && grep -q 'KET QUA: CON 1' '$RF' && [ \$(grep -c '^CHG=' '$RF') = 2 ] && grep -q '^bo_qua_vi_the_lenh=EEEUSDT' '$RF' && grep -qx 'N_REMAIN=1' '$RF'"
chk "moi goi san di toi host gia lv1x-test.invalid (khong host khac)" "! grep -v ' https://lv1x-test.invalid\$' $W/api/calls.log | grep -q ."
: > "$W/api/calls.log"
runin "YES LEV1X" E DRY=0 bash "$S"
chk "chay lai: 0 POST (CCC/DDD da 1x, EEE con vi the), rc 3, khong hoi YES" "[ $RC = 3 ] && [ \$(posts) = 0 ] && ! echo \"\$OUT\" | grep -q \"Go 'YES LEV1X'\""
state "{$(python3 -c "import json;d=json.load(open('$W/api/state.json'));print('\"cfg\":'+json.dumps(d['cfg']))"),\"ord\":[\"EEEUSDT\"]}"
runin "YES LEV1X" E DRY=0 bash "$S"
chk "EEE het vi the nhung CON LENH MO => van bo qua, 0 POST" "[ $RC = 3 ] && [ \$(posts) = 0 ]"
state "{$(python3 -c "import json;d=json.load(open('$W/api/state.json'));print('\"cfg\":'+json.dumps(d['cfg']))")}"
runin "YES LEV1X" E DRY=0 bash "$S"
chk "EEE sach => POST dung EEE, KET QUA DAT rc 0" "[ $RC = 0 ] && [ \$(posts) = 1 ] && grep -q '^POST leverage EEEUSDT' $W/api/calls.log && echo \"\$OUT\" | grep -q 'KET QUA: DAT'"
: > "$W/api/calls.log"
run E bash "$S"
chk "DRY sau khi dat: rc 0 DAT, 0 POST" "[ $RC = 0 ] && [ \$(posts) = 0 ] && echo \"\$OUT\" | grep -q 'KET QUA (DRY): DAT'"

echo "== loi san"
state "{$BASE,\"fail\":{\"CCCUSDT\":[400,-4028,\"Leverage 1 is not valid\"]}}"
: > "$W/api/calls.log"
runin "YES LEV1X" E DRY=0 bash "$S"
RF=$(ls -t "$W"/deploy/lev1x/LEV1X_SUB_*.txt | head -1)
chk "loi san 1 symbol (CCC -4028): tiep tuc DDD+EEE, tong ket OK 2 loi 1, CON 1 CCC, rc 3" "[ $RC = 3 ] && [ \$(posts) = 3 ] && echo \"\$OUT\" | grep -q 'OK 2, loi 1' && echo \"\$OUT\" | grep -q 'KET QUA: CON 1 (CCCUSDT:20)' && grep -q '^ERRSYM=CCCUSDT:HTTP400:-4028' '$RF'"
state "{$BASE,\"fail\":{\"CCCUSDT\":[429,-1003,\"Too many requests\"]}}"
: > "$W/api/calls.log"
runin "YES LEV1X" E DRY=0 bash "$S"
chk "429 o POST dau => DUNG NGAY (1 POST, khong goi them, khong doc lai), rc 1" "[ $RC = 1 ] && [ \$(posts) = 1 ] && echo \"\$OUT\" | grep -q 'KET QUA: DUNG (HTTP429' && [ \$(levof DDDUSDT) = 20 ] && [ \$(calls) = 11 ] && tail -1 $W/api/calls.log | grep -q '^POST leverage CCCUSDT'"
state "{$BASE,\"fail\":{\"CCCUSDT\":[400,-1003,\"Way too many requests\"]}}"
: > "$W/api/calls.log"
runin "YES LEV1X" E DRY=0 bash "$S"
chk "-1003 (HTTP 400) => DUNG NGAY, rc 1" "[ $RC = 1 ] && [ \$(posts) = 1 ] && echo \"\$OUT\" | grep -q 'KET QUA: DUNG (HTTP400_code-1003'"
state "{$BASE,\"fail\":{\"CCCUSDT\":[418,-1003,\"banned\"]}}"
: > "$W/api/calls.log"
runin "YES LEV1X" E DRY=0 bash "$S"
chk "418 => DUNG NGAY, rc 1" "[ $RC = 1 ] && [ \$(posts) = 1 ]"
state "{$BASE,\"fail\":{\"CCCUSDT\":[500,-1001,\"x\"],\"DDDUSDT\":[500,-1001,\"x\"],\"EEEUSDT\":[500,-1001,\"x\"]}}"
: > "$W/api/calls.log"
runin "YES LEV1X" E DRY=0 LV1X_ERR_CONSEC=2 bash "$S"
chk "loi lien tiep >= LV1X_ERR_CONSEC (2) => DUNG sau 2 POST, rc 1" "[ $RC = 1 ] && [ \$(posts) = 2 ] && echo \"\$OUT\" | grep -q '2_loi_lien_tiep'"
state "{$BASE,\"used\":700}"
: > "$W/api/calls.log"
run E LV1X_WAIT_MAX_S=0 bash "$S"
chk "X-MBX-USED-WEIGHT-1M 700 >= 600, khong duoc cho (WAIT_MAX 0) => DUNG sau 1 goi doc, rc 1, 0 POST" "[ $RC = 1 ] && [ \$(calls) = 1 ] && [ \$(posts) = 0 ] && echo \"\$OUT\" | grep -q 'weight_700_ge_600'"
state "{$BASE,\"pos\":{\"EEEUSDT\":\"5\"}}"
: > "$W/api/calls.log"
T0=$(date +%s%N); runin "YES LEV1X" E DRY=0 LV1X_PACE_S=0.3 bash "$S"; DT=$(( ($(date +%s%N) - T0) / 1000000 ))
chk "nhip: LV1X_PACE_S=0.3 duoc ap (13 goi san => >= 3600 ms; do duoc \$DT ms)" "[ $RC = 3 ] && [ \$(posts) = 2 ] && [ \$(calls) = 13 ] && [ $DT -ge 3600 ]"
run env A1_LEV1X_APPROVED="$SHA" LV1X_PACE_S=0.1 bash "$S"
chk "che do that: LV1X_PACE_S < 0.2 (> 5 req/s) => TU CHOI" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'LV1X_PACE_S'"

echo "== [v2] m-3 / m-4 bien noi bo + ban copy"
: > "$W/api/calls.log"; state "{$BASE}"
run E _LV1X_MASKED=12345 bash "$S"
chk "m-3: _LV1X_MASKED dat san tu env => TU CHOI, 0 goi san" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'bien noi bo dat san tu env: _LV1X_MASKED' && [ \$(calls) = 0 ]"
run E _LV1X_STAGE=copy _LV1X_DIR=/tmp/lv1x_run.AAAAAAAAAA _LV1X_TOK=0123456789abcdef0123456789abcdef bash "$S"
chk "m-3/m-4: gia lap co ban copy (_LV1X_STAGE=copy) khi chay ban goc => TU CHOI, 0 goi san" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q '\[m-4\]' && [ \$(calls) = 0 ]"
FD=$(mktemp -d /tmp/lv1x_run.XXXXXXXXXX); cp "$S" "$FD/golive_set_lev1x.sh"; chmod 755 "$FD/golive_set_lev1x.sh"; FT=0123456789abcdef0123456789abcdef; echo "$FT" > "$FD/.tok"
run E _LV1X_STAGE=copy _LV1X_DIR="$FD" _LV1X_TOK="$FT" bash "$FD/golive_set_lev1x.sh"
chk "m-4: ban copy quyen 755 (khong phai 500) => TU CHOI, 0 goi san, khong xoa thu muc la" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q '\[m-4\] quyen' && [ \$(calls) = 0 ] && [ -d '$FD' ]"
rm -rf "$FD"
mkdir -p "$W/s2"; cp "$S" "$W/s2/golive_set_lev1x.sh"; S2=$W/s2/golive_set_lev1x.sh
( (sleep 3; printf 'YES LEV1X\n') | E DRY=0 bash "$S2" > "$W/toc.out" 2>&1; echo $? > "$W/toc.rc" ) &
sleep 1.5
python3 - "$S2" <<'PYT'
import sys
p = sys.argv[1]; b = open(p, 'rb').read(); n = b.count(b'KET QUA')
with open(p, 'r+b') as f: f.write(b.replace(b'KET QUA', b'TAMPERX'))   # ghi de TAI CHO (cung inode, cung do dai)
print('tamper', n)
PYT
wait
OUT=$(cat "$W/toc.out"); RC=$(cat "$W/toc.rc"); ALL="$ALL
$OUT"
CPD=$(echo "$OUT" | grep -oE 'ban copy /tmp/lv1x_run\.[A-Za-z0-9]{10}' | head -1 | cut -d' ' -f3)
chk "m-4 TOCTOU: sua file goc TAI CHO trong luc cho YES => van chay ban copy (KET QUA: DAT, khong TAMPERX), thu muc copy da xoa" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'KET QUA: DAT' && ! echo \"\$OUT\" | grep -q TAMPERX && grep -q TAMPERX '$S2' && [ -n '$CPD' ] && [ ! -e '$CPD' ]"

echo "== [v2] m-5 xac nhan chinh xac"
state "{$BASE}"; : > "$W/api/calls.log"
runin " YES LEV1X" E DRY=0 bash "$S"
chk "m-5: ' YES LEV1X' (khoang trang dau) => TU CHOI, 0 POST" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'Khong xac nhan' && [ \$(posts) = 0 ]"
runin "YES LEV1X " E DRY=0 bash "$S"
chk "m-5: 'YES LEV1X ' (khoang trang cuoi) => TU CHOI, 0 POST" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'Khong xac nhan' && [ \$(posts) = 0 ]"

echo "== [v2] khung gio + LV1X_W_MAX + LEV_CAP"
: > "$W/api/calls.log"
run E DRY=0 LV1X_TEST_NOW_EPOCH=$(( HB + 59*60 + 5 )) bash "$S"
chk "phut :59 + DRY=0 => TU CHOI truoc ssh (0 goi san), goi y chay lai tu :03" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'khung gio' && echo \"\$OUT\" | grep -qE 'chay lai tu [0-9]{2}:03' && [ \$(calls) = 0 ]"
run E DRY=0 LV1X_TEST_NOW_EPOCH=$(( HB + 30*60 )) bash "$S"
chk "phut :30 + DRY=0 => TU CHOI, goi y :32" "[ $RC = 1 ] && echo \"\$OUT\" | grep -qE 'chay lai tu [0-9]{2}:32' && [ \$(calls) = 0 ]"
run E LV1X_TEST_NOW_EPOCH=$(( HB + 30*60 )) bash "$S"
chk "phut :30 + DRY => KHONG chan (DRY chay, rc 3)" "[ $RC = 3 ] && echo \"\$OUT\" | grep -q 'KE HOACH dat 1x' && [ \$(posts) = 0 ]"
run env A1_LEV1X_APPROVED="$SHA" LV1X_TEST_NOW_EPOCH=1 bash "$S"
chk "che do that: LV1X_TEST_NOW_EPOCH dat => TU CHOI (tiem gio CHI o che do test)" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'bien LV1X_TEST_NOW_EPOCH dat tu env'"
: > "$W/api/calls.log"
runin "YES LEV1X" E DRY=0 LV1X_PACE_S=5 LV1X_TEST_NOW_EPOCH=$(( HB + 28*60 + 25 )) bash "$S"
chk "deadline: bat dau 28:25, nhip 5 s => toi phut :29 TRUOC POST dau => DUNG het_khung_gio, 0 POST, rc 1" "[ $RC = 1 ] && [ \$(posts) = 0 ] && echo \"\$OUT\" | grep -q 'het_khung_gio'"
run E LV1X_W_MAX=299 bash "$S"
chk "LV1X_W_MAX=299 (< 300) => TU CHOI" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q \"LV1X_W_MAX='299'\""
run E LV1X_W_MAX=1201 bash "$S"
chk "LV1X_W_MAX=1201 (> 1200) => TU CHOI" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q \"LV1X_W_MAX='1201'\""
run E LEV_CAP=abc bash "$S"
chk "LEV_CAP khong phai so => TU CHOI" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q \"LEV_CAP='abc'\""

echo "== [v2] M-1 pin key trong python 242 + m-1 doc key"
state "{$BASE}"; : > "$W/api/calls.log"
( sleep 1.5; printf 'C3_LIVE_API_KEY=%s\nC3_LIVE_API_SECRET=%s\n' "$KEY2" "$SEC" > "$KF" ) &
OUT=$( (sleep 3; printf 'YES LEV1X\n') | E DRY=0 bash "$S" 2>&1); RC=$?; ALL="$ALL
$OUT"; wait; keys_ok
chk "M-1: doi file key giua phien doc va phien ghi => ERR KEY_PIN, 0 POST, phien ghi 0 request (chi 5 GET phien doc), rc 1" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'ERR KEY_PIN' && [ \$(posts) = 0 ] && [ \$(calls) = 5 ] && [ \$(levof CCCUSDT) = 20 ]"
: > "$W/api/calls.log"
( sleep 1.5; printf 'C3_LIVE_API_KEY=%s\nC3_LIVE_API_SECRET=%s\n' "$KEY2" "$SEC" > "$KF" ) &
OUT=$( (sleep 3; printf 'YES LEV1X\n') | E DRY=0 LV1X_TEST_MAIN_SHA8="$SK8_2" bash "$S" 2>&1); RC=$?; ALL="$ALL
$OUT"; wait; keys_ok
chk "M-1: doi sang key = pin MAIN giua 2 phien => ERR KEY_PIN, 0 POST, rc 1" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'ERR KEY_PIN' && [ \$(posts) = 0 ] && [ \$(calls) = 5 ]"
: > "$W/api/calls.log"
run E LV1X_TEST_MAIN_SHA8="$SK8" bash "$S"
chk "key = MAIN (pin MAIN = sha8 key) => TU CHOI, 0 request" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'key file = key tk CHINH' && [ \$(calls) = 0 ]"
printf '  C3_LIVE_API_KEY=fakekey_lv1x_thut_le_khong_tinh\n' >> "$KF"
run E bash "$S"
chk "m-1: dong KEY thut le (lib khong tinh) => python cung KHONG tinh: DRY doc dung key (san gia chap nhan), rc 3" "[ $RC = 3 ] && echo \"\$OUT\" | grep -q \"key_sha8=$SK8\" && echo \"\$OUT\" | grep -q 'KE HOACH dat 1x: 3 symbol'"
keys_ok; printf 'C3_LIVE_API_KEY=%s\n' "$KEY2" >> "$KF"; : > "$W/api/calls.log"
run E bash "$S"
chk "m-1: 2 dong KEY neo => lib KEYS_OK=0 => TU CHOI, 0 request" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'khong hop le (600, 2 dong)' && [ \$(calls) = 0 ]"
keys_ok

echo "== [v2] m-2 N_MARGIN / N_MAXNOTIONAL"
state '{"cfg":{"AAAUSDT":[1,"CROSSED","400"],"BBBUSDT":[1,"CROSSED"],"CCCUSDT":[1,"CROSSED"],"DDDUSDT":[1,"CROSSED"],"EEEUSDT":[1,"CROSSED"]}}'
run E bash "$S"
chk "maxNotionalValue 400 < 450 (LEV_CAP 5000) => DRY CANH BAO rc 4, liet ke AAAUSDT" "[ $RC = 4 ] && echo \"\$OUT\" | grep -q 'KET QUA (DRY): CANH BAO' && echo \"\$OUT\" | grep -q 'N_MAXNOTIONAL.*: 1 AAAUSDT:400' && echo \"\$OUT\" | grep -q '< 450.00'"
run E LEV_CAP=1000 bash "$S"
chk "cung du lieu, LEV_CAP=1000 (nguong 90) => DRY DAT rc 0" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'KET QUA (DRY): DAT'"
state '{"cfg":{"AAAUSDT":[1,"CROSSED"],"BBBUSDT":[1,"ISOLATED"],"CCCUSDT":[1,"CROSSED"],"DDDUSDT":[1,"CROSSED"],"EEEUSDT":[1,"CROSSED"]}}'
run E bash "$S"
chk "marginType ISOLATED trong universe => DRY CANH BAO rc 4" "[ $RC = 4 ] && echo \"\$OUT\" | grep -q 'marginType != CROSSED: 1' && echo \"\$OUT\" | grep -q 'CANH BAO'"
state '{"cfg":{"AAAUSDT":[1,"CROSSED","400"],"BBBUSDT":[1,"CROSSED"],"CCCUSDT":[20,"CROSSED"],"DDDUSDT":[1,"CROSSED"],"EEEUSDT":[1,"CROSSED"]}}'
: > "$W/api/calls.log"
runin "YES LEV1X" E DRY=0 bash "$S"
chk "ghi: CCC -> 1x, con AAA maxNotional thap => KET QUA: CANH BAO rc 4, in W_PRE truoc POST" "[ $RC = 4 ] && [ \$(posts) = 1 ] && echo \"\$OUT\" | grep -q 'KET QUA: CANH BAO' && echo \"\$OUT\" | grep -q 'AAAUSDT:400' && echo \"\$OUT\" | grep -q '^W_PRE=50'"

echo "== [v2] B-1 symbol chu Han"
CN1=$(python3 -c "print('\u5e01\u5b89USDT')"); CN2=$(python3 -c "print('\u6d4b\u8bd5USDT')")
E1=$(python3 -c "from urllib.parse import quote; print(quote('\u5e01\u5b89USDT', safe=''))"); E2=$(python3 -c "from urllib.parse import quote; print(quote('\u6d4b\u8bd5USDT', safe=''))")
python3 - "$F/run/c3live_exchangeInfo.json" <<'PYT'
import json, sys
p = sys.argv[1]; d = json.load(open(p))
for s in ('\u5e01\u5b89USDT', '\u6d4b\u8bd5USDT'):
    d['symbols'].append({'symbol': s, 'status': 'TRADING', 'quoteAsset': 'USDT', 'contractType': 'PERPETUAL'})
open(p, 'w', encoding='utf-8').write(json.dumps(d, ensure_ascii=False))   # UTF-8 tho, nhu file that
PYT
CNST="{'cfg': {'AAAUSDT': [1, 'CROSSED'], 'BBBUSDT': [1, 'CROSSED'], 'CCCUSDT': [20, 'CROSSED'], 'DDDUSDT': [20, 'CROSSED'], 'EEEUSDT': [20, 'CROSSED'], '\u5e01\u5b89USDT': [20, 'CROSSED'], '\u6d4b\u8bd5USDT': [20, 'CROSSED']}"
pst "$CNST}"; : > "$W/api/calls.log"
run E bash "$S"
chk "DRY: universe 7 (2 chu Han o 20x), ke hoach ASCII truoc + 2 non-ASCII SAU CUNG (percent-encode), liet ke dang goc, 0 POST, rc 3" "[ $RC = 3 ] && echo \"\$OUT\" | grep -q 'universe=7 ' && echo \"\$OUT\" | grep -qF 'KE HOACH dat 1x: 5 symbol: CCCUSDT,DDDUSDT,EEEUSDT,$E1,$E2' && echo \"\$OUT\" | grep -q 'trong do 2 symbol ten non-ASCII' && echo \"\$OUT\" | grep -qF \"$CN1 ($E1)\" && [ \$(posts) = 0 ]"
runin "YES LEV1X" E DRY=0 bash "$S"
chk "ghi: san gia (kiem HMAC tren query percent-encode) CHAP NHAN => DAT rc 0, POST non-ASCII cuoi cung, dang encode" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'KET QUA: DAT' && [ \$(posts) = 5 ] && grep '^POST ' $W/api/calls.log | tail -2 | head -1 | grep -qF 'POST leverage $E1 ' && grep '^POST ' $W/api/calls.log | tail -1 | grep -qF 'POST leverage $E2 ' && [ \$(levof '\u5e01\u5b89USDT') = 1 ] && [ \$(levof '\u6d4b\u8bd5USDT') = 1 ]"
pst "dict($CNST}, fail_na=[400, -1022, 'Signature for this request is not valid.'])"; : > "$W/api/calls.log"
runin "YES LEV1X" E DRY=0 bash "$S"
chk "ghi: san gia tra -1022 cho non-ASCII => KHONG abort, ASCII xong, CAN LAM TAY (goc + encode), rc 3" "[ $RC = 3 ] && [ \$(posts) = 5 ] && ! echo \"\$OUT\" | grep -q 'STOP=' && echo \"\$OUT\" | grep -q 'KET QUA: CON 2' && echo \"\$OUT\" | grep 'CAN LAM TAY' | grep -qF \"$CN1 ($E1)\" && echo \"\$OUT\" | grep 'CAN LAM TAY' | grep -qF \"$CN2 ($E2)\" && echo \"\$OUT\" | grep -q 'tai khoan con' && [ \$(levof CCCUSDT) = 1 ] && [ \$(levof EEEUSDT) = 1 ]"
sed "s/q.encode('utf-8'), hashlib.sha256)/unquote(q).encode('utf-8'), hashlib.sha256)/" "$S" > "$W/mutant.sh"
MSHA=$(sha256sum "$W/mutant.sh" | cut -c1-64)
pst "$CNST}"; : > "$W/api/calls.log"
runin "YES LEV1X" E DRY=0 A1_LEV1X_APPROVED="$MSHA" bash "$W/mutant.sh"
chk "mutant ky tren chuoi CHUA encode => san gia bat -1022 o non-ASCII (test THAT SU kiem chu ky), khong DAT" "! cmp -s '$S' '$W/mutant.sh' && [ $RC = 3 ] && ! echo \"\$OUT\" | grep -q 'KET QUA: DAT' && echo \"\$OUT\" | grep -q 'ERRSYM=$E1:HTTP400:-1022' && [ \$(levof '\u5e01\u5b89USDT') = 20 ]"
pst "dict($CNST}, fail={'\u5e01\u5b89USDT': [429, -1003, 'Too many requests']})"; : > "$W/api/calls.log"
runin "YES LEV1X" E DRY=0 bash "$S"
chk "429 o symbol non-ASCII => VAN DUNG NGAY, rc 1, khong POST symbol sau" "[ $RC = 1 ] && [ \$(posts) = 4 ] && echo \"\$OUT\" | grep -q 'KET QUA: DUNG (HTTP429' && ! grep -qF 'POST leverage $E2' $W/api/calls.log"

echo "== [v2] m-6 cho weight in trang thai (phien DOC) - cho toi ~62 s"
echo "{\"symbols\":[$EXI]}" > "$F/run/c3live_exchangeInfo.json"
state "{$BASE,\"used_seq\":[700]}"; : > "$W/api/calls.log"
run E LV1X_WAIT_MAX_S=120 bash "$S"
NW=$(echo "$OUT" | grep -c '^WAIT=used_700_ge_600_ngu_[0-9]*s_con_'); TW=$(echo "$OUT" | grep -m1 -oE 'ngu_[0-9]+s' | tr -cd '0-9')
chk "m-6: weight 700 o phien DOC => in dong WAIT ngay va moi <= 25 s ($NW dong cho ${TW}s), DRY van xong rc 3" "[ $RC = 3 ] && [ \"\$NW\" -ge 1 ] && [ \"\$NW\" -ge \$(( (\${TW:-0} + 24) / 25 )) ]"

echo "== bao mat"
chk "output + log + file ket qua KHONG chua key/secret/signature/hex64" "! printf '%s' \"\$ALL\" | grep -qE \"$KEY|$KEY2|$SEC|signature=[0-9a-f]|[0-9a-f]{64}\" && ! grep -rqsE \"$KEY|$KEY2|$SEC|signature=[0-9a-f]|[0-9a-f]{64}\" $W/deploy"
ls -d /tmp/lv1x_run.* 2>/dev/null | sort > "$W/runs_after"
chk "khong con thu muc ban copy /tmp/lv1x_run.* nao do test tao ra (trap don)" "[ -z \"\$(comm -13 '$W/runs_before' '$W/runs_after')\" ]"
chk "bash -n script + test" "bash -n '$S' && bash -n '$HERE/test/test_set_lev1x.sh'"
echo "KET QUA TEST: $P/$N"
[ "${KEEP:-0}" = 1 ] && echo "sandbox: $W" || rm -rf "$W"
[ "$P" = "$N" ]
