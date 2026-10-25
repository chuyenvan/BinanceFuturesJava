#!/usr/bin/env bash
# =============================================================================
# c3live_keys_install.sh — (prereg §6 "golive_keys_install.sh") nhap API key tai khoan con c3_live, ghi keys.env tren 242
# (root, file 600, thu muc 700), roi kiem CHI DOC bang C3LiveCanary keycheck (serverTime, tmb, multiAssets, dual).
# Repo KHONG co script "setup_c3live_key" nao (grep toan repo: chi co ten golive_keys_install.sh trong prereg/GOLIVE) => day la
# script cai key DUY NHAT; dinh dang file dung dung C3LiveKeys (C3_LIVE_API_KEY= / C3_LIVE_API_SECRET=).
# Chay tren ORACLE:   YES=1 bash ops/c3live/canary/c3live_keys_install.sh
#   - key/secret nhap bang read -s (khong hien, khong vao log, khong vao dong lenh ssh: di qua stdin cua ssh)
#   - da co keys.env => can them REPLACE=1 (ban cu duoc backup keys.env.bak_<TS>, 600)
#   - chi kiem lai (khong nhap key):  CHECK_ONLY=1 bash ops/c3live/canary/c3live_keys_install.sh
# Ket qua: dong "KET QUA: DAT|TRUOT|TU_CHOI".
# =============================================================================
. "$(cd "$(dirname "$0")" && pwd)/canary_lib.sh"
cl_init keys_install
REPLACE=${REPLACE:-0}
CHECK_ONLY=${CHECK_ONLY:-0}

if [ "$CHECK_ONLY" != 1 ]; then
  need_yes "ghi key len 242"
  EX=$($SSH_242 "[ -e $KEYS_FILE ] && echo CO || echo KHONG" < /dev/null) || die "khong ssh duoc 242"
  if [ "$EX" = CO ] && [ "$REPLACE" != 1 ]; then die "da co $KEYS_FILE tren 242 — them REPLACE=1 de backup + ghi de (hoac CHECK_ONLY=1 de chi kiem)"; fi
  read -r -s -p "API key tai khoan con c3_live: " K1; echo
  read -r -s -p "API secret: " S1; echo
  [[ "$K1" =~ ^[A-Za-z0-9]{16,128}$ ]] || { unset K1 S1; die "key sai dinh dang (chi chu/so, 16-128 ky tu)"; }
  [[ "$S1" =~ ^[A-Za-z0-9]{16,128}$ ]] || { unset K1 S1; die "secret sai dinh dang (chi chu/so, 16-128 ky tu)"; }
  [ "$K1" != "$S1" ] || { unset K1 S1; die "key = secret?"; }
  # printf la builtin (khong vao ps); noi dung chi di qua stdin cua ssh
  R=$(printf 'C3_LIVE_API_KEY=%s\nC3_LIVE_API_SECRET=%s\n' "$K1" "$S1" | $SSH_242 "umask 077; F=$KEYS_FILE; D=\$(dirname \$F); \
    mkdir -p \$D && chmod 700 \$D && { [ ! -e \$F ] || cp -p \$F \$F.bak_$TS; } && cat > \$F.tmp && chmod 600 \$F.tmp && mv -f \$F.tmp \$F \
    && echo \"GHI_XONG \$(stat -c '%a %U' \$F) dir=\$(stat -c '%a' \$D) dong=\$(grep -c '^C3_LIVE_API_' \$F)\"")
  unset K1 S1
  echo "   242: $R"
  echo "$R" | grep -q "^GHI_XONG 600 $KEYS_OWNER dir=700 dong=2$" || die "ghi keys.env khong dung (mong 600 $KEYS_OWNER, thu muc 700, 2 dong)"
  ok "keys.env ghi xong (600 $KEYS_OWNER, thu muc 700)$( [ "$EX" = CO ] && echo "; ban cu: $KEYS_FILE.bak_$TS")"
fi

# kiem CHI DOC (khong gui lenh): jar pin + keycheck
cl_check_242
cl_push_logback
cl_run "" keycheck; RC=$?
V=$(cl_verdict $RC)
echo "$CL_LAST_OUT" | grep -q 'multiAssets=true' || { [ "$V" = DAT ] && say "CANH BAO: multiAssets khong bat (prereg §2.4 can BAT — K0 se TRUOT)"; }
echo "$CL_LAST_OUT" | grep -q 'dual=false' || { [ "$V" = DAT ] && say "CANH BAO: dualSidePosition khong tat (one-way) — K0 se TRUOT"; }
say "Quyen rut / IP restrict (apiRestrictions) KHONG doc duoc bang key futures: owner tu xac nhan tren web Binance (chi Futures, KHONG rut, IP = 242)."
say "KET QUA: $V ($CL_LAST_RESULT)"
say "Log: $CL_LOG"
[ "$V" = DAT ]
