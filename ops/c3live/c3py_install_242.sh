#!/usr/bin/env bash
# =============================================================================
# c3py_install_242.sh — [V12 R4k] python3 RIENG cho 242 (CentOS 7 da EOL, chi co python2.7; KHONG cai python3 he thong, KHONG yum).
# Chay tren ORACLE (owner), 1 lenh:
#   DRY=1 bash ~/claude_master/v12/c3live/ops/c3live/c3py_install_242.sh   # chi kiem + in ke hoach, KHONG ghi gi len 242
#   bash ~/claude_master/v12/c3live/ops/c3live/c3py_install_242.sh         # cai (go YES 1 lan)
#   MODE=status bash .../c3py_install_242.sh                               # xem trang thai (chi doc)
#   MODE=remove bash .../c3py_install_242.sh                               # go (go YES; TU CHOI khi cron lam moi exchangeInfo con cai)
# Ban pin: python-build-standalone 20241016, CPython 3.10.15 x86_64-unknown-linux-gnu install_only (can glibc >= 2.17), sha256 pin.
# Tarball tai ve Oracle (cache), kiem sha256 tren Oracle VA tren 242; giai nen vao thu muc tam <cha>/.c3py_new_<TS>, kiem python chay
# (dung phien ban, import json), ghi marker C3PY_INSTALLED roi DOI TEN nguyen tu thanh /opt/c3py. Python: /opt/c3py/python/bin/python3.
# KHONG dung python he thong / yum / PATH / ld.so.conf; KHONG dung v_t_m, collectData, canary, crontab. Chi ghi /opt/c3py (+ file tam /opt/.c3py_*).
# Dung boi: deploy_v12_dry_r4.sh (PY242) va exinfo_refresh_242.sh (C3PY, cron lam moi exchangeInfo).
# Bien (test): SSH_242, SCP_242, RHOST, C3PY_DIR, PBS_URL, PBS_SHA256, PBS_VER, PBS_CACHE, EXPECT_ARCH, CRONTAB_CMD, FORCE.
# =============================================================================
set -uo pipefail
SSH_242=${SSH_242:-"ssh -p 2222 -o BatchMode=yes -o ConnectTimeout=20 -i /home/ubuntu/.ssh/id_rsa_chuyennd root@103.157.218.242"}
SCP_242=${SCP_242:-"scp -P 2222 -o BatchMode=yes -o ConnectTimeout=20 -i /home/ubuntu/.ssh/id_rsa_chuyennd"}
RHOST=${RHOST-"root@103.157.218.242:"}
C3PY_DIR=${C3PY_DIR:-/opt/c3py}
PBS_VER=${PBS_VER:-3.10.15}
PBS_URL=${PBS_URL:-https://github.com/astral-sh/python-build-standalone/releases/download/20241016/cpython-3.10.15+20241016-x86_64-unknown-linux-gnu-install_only.tar.gz}
PBS_SHA256=${PBS_SHA256:-3db2171e03c1a7acdc599fba583c1b92306d3788b375c9323077367af1e9d9de}
PBS_CACHE=${PBS_CACHE:-/home/ubuntu/claude_master/v12/c3py}
EXPECT_ARCH=${EXPECT_ARCH:-x86_64}
CRONTAB_CMD=${CRONTAB_CMD:-crontab}
MODE=${MODE:-install}
DRY=${DRY:-0}
FORCE=${FORCE:-0}
TS=$(date +%Y%m%d_%H%M%S)
say() { echo "[$(date '+%F %T')] $*"; }
die() { say "DUNG: $*"; say "KET QUA: TU_CHOI"; exit 1; }
P=$(dirname "$C3PY_DIR"); B=$(basename "$C3PY_DIR")
NEWD=$P/.${B}_new_$TS
RMD=$P/.${B}_rm_$TS
TGZ_R=$P/.${B}_$TS.tar.gz
PY=$C3PY_DIR/python/bin/python3
[[ "$PBS_SHA256" =~ ^[0-9a-f]{64}$ ]] || die "PBS_SHA256 chua pin"
say "=== c3py_install_242 MODE=$MODE DRY=$DRY — python rieng $PY (CPython $PBS_VER, sha256 ${PBS_SHA256:0:12}...)"

st242() {   # CHI DOC tren 242
  $SSH_242 "bash -s -- '$C3PY_DIR' '$PBS_VER' '$PBS_SHA256' '$EXPECT_ARCH' '$CRONTAB_CMD'" <<'EOF'
D=$1; VER=$2; SHA=$3; ARCH=$4; CT=$5; P=$(dirname "$D"); B=$(basename "$D")
A=$(uname -m); [ "$A" = "$ARCH" ] && echo "OK arch=$A" || echo "FAIL arch=$A (can $ARCH)"
G=$(ldd --version 2>/dev/null | head -1 | grep -oE '[0-9]+\.[0-9]+$')
echo "$G" | awk -F. '{exit !($1 > 2 || ($1 == 2 && $2 >= 17))}' && echo "OK glibc=$G" || echo "FAIL glibc='$G' (can >= 2.17)"
[ -d "$P" ] && [ -w "$P" ] && echo "OK thu_muc_cha=$P" || echo "FAIL thu_muc_cha $P khong ghi duoc"
F=$(df -Pk "$P" 2>/dev/null | awk 'NR==2{print $4}'); [ "${F:-0}" -gt 524288 ] && echo "OK dia_trong=${F}k" || echo "FAIL dia_trong=${F}k < 512M"
for c in sha256sum tar gzip; do command -v $c >/dev/null && echo "OK co_$c" || echo "FAIL thieu_$c"; done
if [ -e "$D" ]; then
  if [ -f "$D/C3PY_INSTALLED" ] && grep -qx "sha256=$SHA" "$D/C3PY_INSTALLED"; then
    V=$("$D/python/bin/python3" -I -c 'import json, sys; print("%d.%d.%d" % sys.version_info[:3])' 2>&1)
    [ "$V" = "$VER" ] && echo "STATE da_cai ver=$V" || echo "STATE hong ver='$V'"
  elif [ -f "$D/C3PY_INSTALLED" ]; then echo "STATE ban_khac $(tr '\n' ' ' < "$D/C3PY_INSTALLED")"
  else echo "STATE la ($D ton tai nhung KHONG do c3py_install_242.sh cai)"; fi
else echo "STATE chua_cai"; fi
N=$($CT -l 2>/dev/null | grep -cF '# C3LIVE_EXINFO_REFRESH'); echo "CRON exinfo_refresh=${N:-0}"
for t in "$P"/."$B"_new_* "$P"/."$B"_rm_* "$P"/."$B"_*.tar.gz; do [ -e "$t" ] && echo "INFO file_tam_con_lai $t"; done
echo END_ST
EOF
}
get_st() {
  S=$(st242) || die "ssh toi 242 loi"
  echo "$S" | grep -qx END_ST || die "kiem 242 khong tron ven (ssh dut?)"
  echo "$S" | grep -v '^END_ST$'
  STATE=$(echo "$S" | sed -n 's/^STATE \([a-z_]*\).*/\1/p' | head -1)
  NCRON=$(echo "$S" | sed -n 's/^CRON exinfo_refresh=//p' | head -1)
}
yes_or_quit() {
  printf 'Go YES de %s: ' "$1"; read -r ans || ans=""
  [ "$ans" = YES ] || { say "Huy. Khong doi gi."; exit 0; }
}

case "$MODE" in
status)
  get_st; say "KET QUA: STATUS $STATE"; exit 0 ;;
remove)
  get_st
  case "$STATE" in da_cai|hong|ban_khac) ;; *) die "$C3PY_DIR khong co marker cua c3py_install_242.sh (STATE=$STATE) — KHONG xoa";; esac
  if [ "${NCRON:-0}" != 0 ] && [ "$FORCE" != 1 ]; then
    die "cron lam moi exchangeInfo con cai ($NCRON dong, dung python nay) — rollback_v12.sh truoc (FORCE=1 chi khi MASTER bao)"
  fi
  say "ke hoach: doi ten $C3PY_DIR -> $RMD roi xoa $RMD (chi thu muc nay)"
  [ "$DRY" = 1 ] && { say "DRY=1: chi kiem, KHONG ghi gi len 242."; say "KET QUA: DRY PASS"; exit 0; }
  yes_or_quit "GO python rieng $C3PY_DIR tren 242"
  R=$($SSH_242 "bash -s -- '$C3PY_DIR' '$RMD'" <<'EOF'
D=$1; RM=$2
[ -f "$D/C3PY_INSTALLED" ] || { echo "FAIL khong_co_marker"; echo END_RM; exit 0; }
mv -T "$D" "$RM" || { echo "FAIL doi_ten"; echo END_RM; exit 0; }
rm -rf "$RM" && echo "OK da_go $D" || echo "FAIL xoa $RM"
echo END_RM
EOF
) || die "ssh loi khi go"
  echo "$R"
  echo "$R" | grep -q '^FAIL' && die "go FAIL"
  echo "$R" | grep -qx END_RM || die "go khong tron ven (ssh dut?) — MODE=status"
  say "KET QUA: DAT (da go $C3PY_DIR)"; exit 0 ;;
install) ;;
*) die "MODE=$MODE khong hop le (install|status|remove)";;
esac

# ---------------------------------------------------------------- install
mkdir -p "$PBS_CACHE" || die "khong tao duoc $PBS_CACHE"
T=$PBS_CACHE/$(basename "$PBS_URL")
if [ -f "$T" ] && [ "$(sha256sum < "$T" | cut -c1-64)" = "$PBS_SHA256" ]; then
  say "OK tarball cache $T sha256 dung pin"
else
  say "tai $PBS_URL -> $T (chi ghi tren Oracle)"
  rm -f "$T.part"
  curl -fsSL --max-time 900 -o "$T.part" "$PBS_URL" || { rm -f "$T.part"; die "tai tarball loi"; }
  G=$(sha256sum < "$T.part" | cut -c1-64)
  [ "$G" = "$PBS_SHA256" ] || { rm -f "$T.part"; die "sha256 tarball sai ($G, pin $PBS_SHA256)"; }
  mv -f "$T.part" "$T"; say "OK tarball sha256 dung pin"
fi
get_st
echo "$S" | grep -q '^FAIL' && die "kiem 242 co muc FAIL (xem tren). KHONG doi gi."
case "$STATE" in
  da_cai) say "DA CAI dung ban pin ($PY) — khong lam gi."; say "KET QUA: DAT"; exit 0 ;;
  chua_cai) ;;
  *) die "$C3PY_DIR o trang thai '$STATE' — MASTER xem (MODE=status; MODE=remove neu do script nay cai)";;
esac
say "ke hoach: chep tarball -> $TGZ_R; kiem sha256 tren 242; giai nen -> $NEWD; kiem python; marker; doi ten -> $C3PY_DIR; xoa tarball"
[ "$DRY" = 1 ] && { say "DRY=1: chi kiem, KHONG ghi gi len 242. Chay that: bo DRY=1"; say "KET QUA: DRY PASS"; exit 0; }
yes_or_quit "CAI python rieng vao $C3PY_DIR tren 242"
$SCP_242 "$T" "${RHOST}$TGZ_R" || die "chep tarball len 242 loi"
R=$($SSH_242 "bash -s -- '$C3PY_DIR' '$NEWD' '$TGZ_R' '$PBS_SHA256' '$PBS_VER' '$TS' '$PBS_URL'" <<'EOF'
D=$1; NEWD=$2; TGZ=$3; SHA=$4; VER=$5; TS=$6; URL=$7
fail() { rm -rf "$NEWD"; rm -f "$TGZ"; echo "FAIL $*"; echo END_INS; exit 0; }
[ -e "$D" ] && fail "da_ton_tai $D"
[ "$(sha256sum < "$TGZ" | cut -c1-64)" = "$SHA" ] || fail "sha256_tren_242_sai"
echo "OK sha256_tren_242"
mkdir "$NEWD" || fail "mkdir $NEWD"
tar -xzf "$TGZ" -C "$NEWD" --no-same-owner || fail "giai_nen"
V=$("$NEWD/python/bin/python3" -I -c 'import json, sys; json.loads("{\"a\": 1}"); print("%d.%d.%d" % sys.version_info[:3])' 2>&1)
[ "$V" = "$VER" ] || fail "python_moi_khong_chay '$V'"
echo "OK python_moi ver=$V"
{ echo "sha256=$SHA"; echo "ver=$VER"; echo "url=$URL"; echo "ts=$TS"; } > "$NEWD/C3PY_INSTALLED" || fail "marker"
mv -T "$NEWD" "$D" || fail "doi_ten"
rm -f "$TGZ"
V2=$("$D/python/bin/python3" -I -c 'import json, sys; print("%d.%d.%d" % sys.version_info[:3])' 2>&1)
[ "$V2" = "$VER" ] && echo "OK da_cai $D ver=$V2" || echo "FAIL sau_doi_ten '$V2' (MODE=status / MODE=remove)"
echo END_INS
EOF
) || die "ssh loi khi cai (MODE=status de xem)"
echo "$R"
echo "$R" | grep -q '^FAIL' && die "cai FAIL (xem tren)"
echo "$R" | grep -qx END_INS || die "cai khong tron ven (ssh dut?) — MODE=status"
say "KET QUA: DAT — python rieng $PY. Tiep: DRY=1 FORCE=1 bash ~/claude_master/v12/c3live/ops/c3live/deploy_v12_dry_r4.sh"
