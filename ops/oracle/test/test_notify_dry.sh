#!/usr/bin/env bash
# test_notify_dry.sh — test GIA cho ops/oracle/notify.sh: tg.env gia, curl gia (bat ky goi nao cung bi ghi lai), KHONG gui tin that.
#   bash ops/oracle/test/test_notify_dry.sh /tmp/t_nt
HERE=$(cd "$(dirname "$0")/.." && pwd); N=$HERE/notify.sh
W=${1:?thu muc tam}; rm -rf "$W"; mkdir -p "$W/bin"; PASS=0; FAILN=0
chk() { if eval "$2"; then PASS=$((PASS+1)); echo "  [PASS] $1"; else FAILN=$((FAILN+1)); echo "  [FAIL] $1"; fi; }
TOK="123456789:AAFakeTokenForTestOnly_abcdefghijklmn"
printf 'tele-token: %s\ntele-chat-id: -100987654321\n' "$TOK" > $W/tg.env; chmod 600 $W/tg.env
printf '#!/bin/bash\necho "$@" >> %s/curl_args; cat > %s/curl_stdin; echo 200\n' "$W" "$W" > $W/bin/curl; chmod +x $W/bin/curl
echo "== notify.sh (gia)"
OUT=$(NOTIFY_DRY=1 NOTIFY_TG_ENV=$W/tg.env PATH=$W/bin:$PATH bash $N "RAM can 300MB" 2>&1); RC=$?
chk "DRY: in payload, token CHE (khong co trong output), co sha8 + text, KHONG goi curl" "[ $RC = 0 ] && ! echo \"\$OUT\" | grep -qF '$TOK' && echo \"\$OUT\" | grep -q 'sha8 ' && echo \"\$OUT\" | grep -q 'text=RAM can 300MB' && [ ! -f $W/curl_args ]"
OUT=$(NOTIFY_TG_ENV=$W/tg.env PATH=$W/bin:$PATH bash $N "xin chao" 2>&1); RC=$?
chk "gui (curl GIA): token chi qua stdin (-K -), KHONG trong argv; chat_id + text qua --data-urlencode" "[ $RC = 0 ] && ! grep -qF '$TOK' $W/curl_args && grep -qF '$TOK' $W/curl_stdin && grep -q 'chat_id=-100987654321' $W/curl_args && grep -q 'text=xin chao' $W/curl_args"
chk "khong con goi openclaw" "! grep -q 'openclaw gateway call' $N"
OUT=$(NOTIFY_TG_ENV=$W/khong_co.env bash $N "x" 2>&1); RC=$?
chk "thieu tg.env => rc!=0, bao loi" "[ $RC != 0 ] && echo \"\$OUT\" | grep -q 'khong doc duoc'"
echo "TEST $( [ $FAILN = 0 ] && echo PASS || echo FAIL ) $PASS/$((PASS+FAILN))"
[ $FAILN = 0 ]
