#!/usr/bin/env bash
# =============================================================================
# canary_set_key.sh — [V12 3f, prereg §ADD-4 J] MOT LENH tren ORACLE: nhap API key RIENG cua canary tren TAI KHOAN CHINH
# (Futures trade BAT, rut tien TAT, IP restrict = 242; KHONG dung key LEGACY / PrivateConfig), ghi keys.env tren 242:
#   bash ~/claude_master/v12/c3live/ops/c3live/canary/canary_set_key.sh
#   - go YES 1 lan; key + secret nhap bang read -s (khong hien, khong vao log, khong vao dong lenh ssh: di qua stdin cua ssh)
#   - da co keys.env (key tai khoan con cu) => backup keys.env.bak_<TS> (600) roi ghi de
#   - ghi: root(owner theo lib), file 600, thu muc 700, dung 2 dong C3_LIVE_API_KEY= / C3_LIVE_API_SECRET= (dinh dang C3LiveKeys)
#   - neu jar pin da co tren 242 (thu muc canary-early): keycheck CHI DOC (khong gui lenh); chua co => canary_early_all.sh se kiem
# Ket qua: dong "KET QUA: DAT|TRUOT|TU_CHOI". KHONG in key/secret o bat ky dau.
# =============================================================================
export CANARY_MODE=early
. "$(cd "$(dirname "$0")" && pwd)/canary_lib.sh"
cl_init set_key

echo "Nhap API key RIENG cho canary tren TAI KHOAN CHINH (Futures trade BAT, rut tien TAT, IP chi 242). KHONG dung key LEGACY."
echo "Key/secret KHONG hien tren man hinh va KHONG vao log. File dich tren 242: $KEYS_FILE (600)."
if [ "${YES:-0}" != 1 ]; then
  read -r -p "Go YES (in hoa) de tiep tuc: " ANS || ANS=""
  [ "$ANS" = YES ] || die "khong go YES — khong ghi gi"
fi
EX=$($SSH_242 "[ -e $KEYS_FILE ] && echo CO || echo KHONG" < /dev/null) || die "khong ssh duoc 242"
read -r -s -p "API key tai khoan CHINH (canary): " K1; echo
read -r -s -p "API secret: " S1; echo
[[ "$K1" =~ ^[A-Za-z0-9]{16,128}$ ]] || { unset K1 S1; die "key sai dinh dang (chi chu/so, 16-128 ky tu)"; }
[[ "$S1" =~ ^[A-Za-z0-9]{16,128}$ ]] || { unset K1 S1; die "secret sai dinh dang (chi chu/so, 16-128 ky tu)"; }
[ "$K1" != "$S1" ] || { unset K1 S1; die "key = secret?"; }
# printf la builtin (khong vao ps); noi dung chi di qua stdin cua ssh; ban cu (neu co) backup 600
R=$(printf 'C3_LIVE_API_KEY=%s\nC3_LIVE_API_SECRET=%s\n' "$K1" "$S1" | $SSH_242 "umask 077; F=$KEYS_FILE; D=\$(dirname \$F); \
  mkdir -p \$D && chmod 700 \$D && { [ ! -e \$F ] || cp -p \$F \$F.bak_$TS; } && cat > \$F.tmp && chmod 600 \$F.tmp && mv -f \$F.tmp \$F \
  && echo \"GHI_XONG \$(stat -c '%a %U' \$F) dir=\$(stat -c '%a' \$D) dong=\$(grep -c '^C3_LIVE_API_' \$F)\"")
unset K1 S1
echo "   242: $R"
echo "$R" | grep -q "^GHI_XONG 600 $KEYS_OWNER dir=700 dong=2$" || die "ghi keys.env khong dung (mong 600 $KEYS_OWNER, thu muc 700, 2 dong)"
ok "keys.env ghi xong (600 $KEYS_OWNER, thu muc 700)$( [ "$EX" = CO ] && echo "; ban cu: $KEYS_FILE.bak_$TS")"

# kiem CHI DOC neu jar pin da nam trong thu muc canary-early tren 242 (chua co => canary_early_all.sh kiem lai bang keycheck + K0)
cl_check_242 early_nojar
V=CHUA_KIEM
if [ "$(pv JAR)" = "$CANARY_JAR_MD5" ]; then
  cl_push_logback
  cl_run "" keycheck; RC=$?
  V=$(cl_verdict $RC)
  echo "$CL_LAST_OUT" | grep -q 'dual=false' || { [ "$V" = DAT ] && say "CANH BAO: dualSidePosition khong tat (one-way) — K0 se TU CHOI (§ADD-4 E: canary KHONG doi)"; }
  say "keycheck (chi doc): $(printf '%s' "$CL_LAST_OUT" | grep '^KEYCHECK ' | tail -1 | sed -E 's/ assets=\{[^}]*\}//; s/ tmb=[0-9.]+//; s/ avail=[0-9.]+//')"
else
  say "jar pin chua co tren 242 (canary-early) — keycheck se chay trong canary_early_all.sh"
fi
say "Quyen rut / IP restrict KHONG doc duoc bang key futures: owner tu xac nhan tren web Binance (Futures trade, KHONG rut, IP = 242)."
say "KET QUA: $( [ "$V" = CHUA_KIEM ] && echo "DAT (ghi key; keycheck de canary_early_all.sh)" || echo "$V ($CL_LAST_RESULT)")"
say "Log: $CL_LOG"
[ "$V" = DAT ] || [ "$V" = CHUA_KIEM ]
