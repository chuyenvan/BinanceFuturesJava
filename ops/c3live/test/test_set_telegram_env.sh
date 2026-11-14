#!/usr/bin/env bash
# test_set_telegram_env.sh - [A1-M6 2026-11-14] kiem set_telegram_env_242.sh tren thu muc gia (SSH_242="bash -c", khong dung 242).
# Token GIA sinh luc chay (khong phai token that). Kiem: DRY khong ghi; ghi 600/700 dung owner; dong source + export toi process con;
# token KHONG xuat hien trong output; daemon.sh khong nap env.sh => DUNG; user khong ton tai => DUNG; chay lai idempotent; sha sai => DUNG.
set -uo pipefail
H=$(cd "$(dirname "$0")/.." && pwd); SH=$H/set_telegram_env_242.sh
W=$(mktemp -d /tmp/tst_tgenv.XXXXXX); trap 'rm -rf "$W"' EXIT
PASS=0; FAILN=0
chk() { if eval "$2"; then PASS=$((PASS+1)); echo "PASS $1"; else FAILN=$((FAILN+1)); echo "FAIL $1"; fi; }
TOK="1234567890:$(printf 'fakeTokenTestOnly%018d' 7)"
S8=$(printf %s "$TOK" | sha256sum | cut -c1-8)
printf 'TG_TOKEN=%s\n' "$TOK" > $W/src.env; chmod 600 $W/src.env
mk() { for a in collectData v_t_m; do mkdir -p $W/app/$a/conf $W/app/$a/bin; echo 'export APP_MAIN_CLASS=x' > $W/app/$a/conf/env.sh
  printf '#!/bin/bash\nif [ -f "$APP_CONF_DIR/env.sh" ]; then\n  . "$APP_CONF_DIR/env.sh"\nfi\n' > $W/app/$a/bin/daemon.sh; done; }
mk
run() { env SRC=$W/src.env EXPECT_SHA8=$S8 SSH_242="bash -c" SECD=$W/secrets APPS="$W/app/collectData $W/app/v_t_m" RUN_USER=${RU:-$(id -un)} "$@" bash $SH 2>&1; }
OUT=$(run DRY=1); RC=$?
chk "DRY PASS, khong ghi gi" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'DRY PASS' && [ ! -e $W/secrets ] && [ \$(grep -c telegram.env $W/app/v_t_m/conf/env.sh) = 0 ]"
OUT=$(run); RC=$?
chk "ghi XONG rc=0" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q '=== XONG'"
chk "file 600 + thu muc 700 owner = user chay" "[ \$(stat -c %a:%U $W/secrets/telegram.env) = 600:$(id -un) ] && [ \$(stat -c %a:%U $W/secrets) = 700:$(id -un) ]"
chk "export toi process con ca 2 app" "[ \$(echo \"\$OUT\" | grep -c 'OK export_toi_process_con_sha8=$S8') = 2 ]"
chk "token KHONG xuat hien trong output" "! echo \"\$OUT\" | grep -q 'fakeTokenTestOnly'"
OUT=$(run); RC=$?
chk "chay lai idempotent (1 dong source moi env.sh)" "[ $RC = 0 ] && [ \$(grep -c 'secrets/telegram.env' $W/app/collectData/conf/env.sh) = 1 ] && echo \"\$OUT\" | grep -q 'OK da_co_dong_source'"
printf '#!/bin/bash\nexec java -cp x y\n' > $W/app/v_t_m/bin/daemon.sh
OUT=$(run DRY=1); RC=$?
chk "daemon.sh khong nap env.sh => DUNG" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'FAIL daemon.sh_khong_nap_env.sh'"
mk
OUT=$(RU=khong_co_user_nay_42 run DRY=1); RC=$?
chk "user khong ton tai => DUNG" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'FAIL user_khong_ton_tai'"
OUT=$(run EXPECT_SHA8=00000000 DRY=1); RC=$?
chk "sha8 nguon sai => DUNG, khong in token" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'sha8 token nguon' && ! echo \"\$OUT\" | grep -q fakeTokenTestOnly"
echo "TEST_SET_TELEGRAM_ENV PASS=$PASS FAIL=$FAILN"
[ $FAILN = 0 ]
