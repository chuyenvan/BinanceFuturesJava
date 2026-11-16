#!/usr/bin/env bash
# =============================================================================
# golive_use_sub_key.sh — [ADD4 §2] OWNER chay 1 LAN tren ORACLE: dua key TAI KHOAN CON vao file rieng tren 242, roi kiem key (CHI DOC san).
#   $OPS = thu muc chua script nay (worktree A1 duyet: HEAD co trong deploy/gates/A1_APPROVED_OPS.commit; MASTER cap duong dan)
#   DRY=1 bash $OPS/golive_use_sub_key.sh   # chi kiem nguon / dich / file tk chinh, KHONG ghi
#   bash $OPS/golive_use_sub_key.sh         # go YES
# Tren 242 (root): nguon $SUB_SRC (mac dinh keys.env.bak_20261028_050947): sha256(key)[:8] PHAI = $SUB_KEY_SHA8 (43820b5b) va KHAC key
#   tk chinh $MAIN_KEY_SHA8, quyen 600, chu root, dung 1 dong KEY + 1 dong SECRET. Copy (umask 077, cp -p) -> <dich>.tmp_<TS>,
#   chmod 600 + chown root, kiem lai sha8 -> mv -n vao $KEYS_FILE (/root/.config/c3live/keys_sub.env). Dich da co: dung key + 600 + root
#   => khong ghi lai; khac => TU CHOI (khong ghi de). KHONG dong vao $MAIN_KEYS_FILE (keys.env): so mtime/kich thuoc/sha8 truoc = sau.
#   Sau do chay golive_check_key.sh C3_ACCOUNT=SUB (ADD4 §2, CHI DOC san).
# KHONG in key/secret: chi ten file, quyen, chu, mtime, kich thuoc, sha256(key)[:8]; secret KHONG bam, KHONG in.
# Ma thoat: = ma golive_check_key (0 DAT | 3 TRUOT) | 1 DUNG | 2 KHAN (file tk chinh thay doi).
# =============================================================================
set -uo pipefail
# [WAVE1c m1 / OPS-MICRO3 n4] pin NGOAI repo, kiem TRUOC khi source lib (lib khong tu chung nhan): HEAD repo chua script = 1 commit A1/MASTER
#   duyet trong A1_APPROVED_OPS (deploy/gates/A1_APPROVED_OPS.commit, 1 dong/commit, script CHI DOC) + thu muc script KHONG co sua chua commit.
_OPS=$(cd "$(dirname "$0")" && pwd); _APO=${A1_APPROVED_OPS:-/home/ubuntu/claude_master/deploy/gates/A1_APPROVED_OPS.commit}; _PW=""
_HC=$(git -C "$_OPS" rev-parse --verify -q HEAD 2>/dev/null) || _PW="$_OPS khong phai repo git"
[ -n "$_PW" ] || { [ -f "$_APO" ] && grep -qE "^$_HC([[:space:]]|\$)" "$_APO"; } || _PW="HEAD $_HC CHUA duoc A1 duyet (khong co trong $_APO)"
[ -n "$_PW" ] || git -C "$_OPS" diff --quiet HEAD -- . 2>/dev/null || _PW="$_OPS co sua CHUA commit (git diff HEAD)"
[ -z "$_PW" ] || { echo "TU CHOI [m1]: $_PW - KHONG lam gi."; exit 1; }
HERE=$(cd "$(dirname "$0")" && pwd)
export C3_ACCOUNT=SUB
. "$HERE/golive_lib.sh"
gl_manifest_check "$0" || exit 1   # [WAVE1b M5 / OPS-MICRO3 n4] script + lib + manifest khop md5 da commit, lech => TU CHOI truoc moi viec
SUB_SRC=${SUB_SRC:-/root/.config/c3live/keys.env.bak_20261028_050947}
SUB_KEY_SHA8=${SUB_KEY_SHA8:-43820b5b}
MAIN_KEYS_FILE=${MAIN_KEYS_FILE:-/root/.config/c3live/keys.env}
KEY_UID=${KEY_UID:-0}
gl_init golive_use_sub_key
say "nguon $SUB_SRC (sha8 phai = $SUB_KEY_SHA8) -> dich $KEYS_FILE ; KHONG dong $MAIN_KEYS_FILE"
[ "$KEYS_FILE" != "$MAIN_KEYS_FILE" ] && [ "$KEYS_FILE" != "$SUB_SRC" ] || die "dich $KEYS_FILE trung file tk chinh / nguon"
[ "$SUB_KEY_SHA8" != "$MAIN_KEY_SHA8" ] || die "SUB_KEY_SHA8 = key tk chinh"
# finfo <file> : CHI DOC tren 242 -> EXISTS MODE UID MTIME SIZE NKEY NSEC KEY_SHA8 (sha256(key)[:8]; secret khong doc gia tri) END_INFO
finfo() {
  s242in "bash -s -- $PY242 $1" <<'EOF'
PY=$1; F=$2; [ -x "$PY" ] || { echo "ERR=thieu_python_$PY"; echo END_INFO; exit 0; }
"$PY" -I - "$F" <<'PYEOF'
import hashlib, os, sys
f = sys.argv[1]
try:
    st = os.stat(f)
except FileNotFoundError:
    print('EXISTS=0'); print('END_INFO'); sys.exit(0)
print('EXISTS=1'); print('MODE=%o' % (st.st_mode & 0o777)); print('UID=%d' % st.st_uid)
print('MTIME=%d' % int(st.st_mtime)); print('SIZE=%d' % st.st_size)
k = None; nk = ns = 0
try:
    for ln in open(f, encoding='utf-8'):
        ln = ln.strip()
        if ln.startswith('C3_LIVE_API_KEY='): nk += 1; k = ln.split('=', 1)[1].strip().strip('"')
        elif ln.startswith('C3_LIVE_API_SECRET='): ns += 1
except Exception as e:
    print('ERR=doc_loi_' + type(e).__name__)
print('NKEY=%d' % nk); print('NSEC=%d' % ns)
print('KEY_SHA8=' + (hashlib.sha256(k.encode()).hexdigest()[:8] if k else ''))
k = None
print('END_INFO')
PYEOF
EOF
}
iv() { echo "$1" | sed -n "s/^$2=//p" | head -1; }
show() { say "$1: ton_tai=$(iv "$2" EXISTS) quyen=$(iv "$2" MODE) uid=$(iv "$2" UID) mtime=$(d=$(iv "$2" MTIME); [ -n "$d" ] && TZ=Asia/Ho_Chi_Minh date -d "@$d" '+%F %T' || echo -) kich_thuoc=$(iv "$2" SIZE) key_sha8=$(iv "$2" KEY_SHA8)"; }
okinfo() { echo "$1" | grep -qx END_INFO && ! echo "$1" | grep -q '^ERR='; }
goodkey() { [ "$(iv "$1" EXISTS)" = 1 ] && [ "$(iv "$1" MODE)" = 600 ] && [ "$(iv "$1" UID)" = "$KEY_UID" ] && [ "$(iv "$1" NKEY)" = 1 ] \
  && [ "$(iv "$1" NSEC)" = 1 ] && [ "$(iv "$1" KEY_SHA8)" = "$SUB_KEY_SHA8" ]; }

IS=$(finfo "$SUB_SRC") || die "ssh toi 242 loi"; okinfo "$IS" || die "doc nguon loi: $(echo "$IS" | grep '^ERR=')"
show "nguon $SUB_SRC" "$IS"
goodkey "$IS" || die "nguon KHONG dat (can ton tai, 600, uid $KEY_UID, 1 KEY + 1 SECRET, sha8 = $SUB_KEY_SHA8; co sha8=$(iv "$IS" KEY_SHA8))"
IM=$(finfo "$MAIN_KEYS_FILE") || die "ssh toi 242 loi"; okinfo "$IM" || die "doc file tk chinh loi"
show "tk chinh $MAIN_KEYS_FILE (KHONG dong)" "$IM"
ID=$(finfo "$KEYS_FILE") || die "ssh toi 242 loi"; okinfo "$ID" || die "doc dich loi"
COPY=1
if [ "$(iv "$ID" EXISTS)" = 1 ]; then
  show "dich $KEYS_FILE (DA CO)" "$ID"
  goodkey "$ID" || die "dich $KEYS_FILE DA TON TAI voi key/quyen khac — KHONG ghi de (owner xem tay)"
  COPY=0; say "OK dich da co dung key tk con (600, uid $KEY_UID) — KHONG ghi lai"
fi
if [ "$DRY" = 1 ]; then
  [ "$COPY" = 1 ] && say "--- se copy $SUB_SRC -> $KEYS_FILE (600, uid $KEY_UID), roi chay golive_check_key.sh (SUB)"
  say "DRY=1: KHONG ghi gi len 242, KHONG goi san. (DRY PASS)"; exit 0
fi
if [ "$COPY" = 1 ]; then
  gl_yes "COPY key tk con ($SUB_KEY_SHA8) $SUB_SRC -> $KEYS_FILE tren 242 (keys.env tk chinh KHONG dong)."
  T=$KEYS_FILE.tmp_$TS
  RC1=$(s242in "bash -s -- $SUB_SRC $KEYS_FILE $T $KEY_UID" <<'EOF'
S=$1; D=$2; T=$3; U=$4
[ -e "$D" ] && { echo "FAIL dich_da_ton_tai"; exit 0; }
[ -e "$T" ] && { echo "FAIL tmp_da_ton_tai"; exit 0; }
( umask 077; cp -p "$S" "$T" ) || { rm -f "$T"; echo "FAIL cp"; exit 0; }
chmod 600 "$T" && chown "$U" "$T" || { rm -f "$T"; echo "FAIL chmod_chown"; exit 0; }
echo "OK tmp"
EOF
) || RC1="FAIL ssh"
  echo "$RC1" | grep -qx 'OK tmp' || die "copy tam loi: $RC1"
  IT=$(finfo "$T") || IT=""
  if ! okinfo "$IT" || ! goodkey "$IT"; then s242 "rm -f '$T'"; die "file tam KHONG dung (sha8/quyen) — da xoa file tam"; fi
  s242 "mv -n '$T' '$KEYS_FILE' && [ ! -e '$T' ]" || { s242 "rm -f '$T'"; die "mv vao $KEYS_FILE loi (da xoa file tam)"; }
  ID=$(finfo "$KEYS_FILE") || ID=""
  okinfo "$ID" && goodkey "$ID" || die "dich $KEYS_FILE sau copy KHONG dung — owner kiem tay"
  show "dich $KEYS_FILE (MOI)" "$ID"
fi
IM2=$(finfo "$MAIN_KEYS_FILE") || IM2=""
for f in EXISTS MODE UID MTIME SIZE KEY_SHA8; do
  if [ "$(iv "$IM" $f)" != "$(iv "$IM2" $f)" ]; then
    say "KHAN: file tk chinh $MAIN_KEYS_FILE THAY DOI ($f: $(iv "$IM" $f) -> $(iv "$IM2" $f))"; tg "[golive] KHAN use_sub_key TS=$TS: $MAIN_KEYS_FILE thay doi ($f). Log $LOG"; exit 2
  fi
done
say "OK file tk chinh khong doi (mtime/kich thuoc/sha8)"
say "--- chay golive_check_key.sh C3_ACCOUNT=SUB (CHI DOC san)"
C3_ACCOUNT=SUB KEYS_FILE=$KEYS_FILE bash "$HERE/golive_check_key.sh"; RC=$?
say "KET QUA use_sub_key: dich $KEYS_FILE key_sha8=$(iv "$ID" KEY_SHA8), check_key rc=$RC ($([ $RC = 0 ] && echo DAT || echo TRUOT/loi))"
exit $RC
