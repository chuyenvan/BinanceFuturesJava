#!/usr/bin/env bash
# =============================================================================
# test_ops5.sh - [OPS5] test fake242 cho tinh nang ops-micro5 (first_trade_check, deadman Oracle/242, check_lev, autodrain, tre gia).
#   bash ops/c3live/test/test_ops5.sh <thu_muc_tam>      (KHONG ssh, KHONG 242, KHONG Binance, Telegram GIA = file sink)
# Process gia ten RIENG "BinanceOrderTradingManager fk_ops5_<pid>" (khong dung mau chung voi bo test khac); don dep CHI theo ten rieng.
# Ket qua: "TEST PASS n/n" | "TEST FAIL ...".
# =============================================================================
set -uo pipefail
HERE=$(cd "$(dirname "$0")/.." && pwd)
W=${1:?"thieu thu muc tam"}
case "$W" in /tmp/*|/home/ubuntu/claude_master/tmp/*) ;; *) echo "TEST FAIL: thu muc tam phai trong /tmp"; exit 1;; esac
rm -rf "$W"; mkdir -p "$W"
git -C "$HERE" diff --quiet HEAD -- . || { echo "TEST FAIL: $HERE co sua CHUA commit - commit truoc"; exit 1; }
export A1_APPROVED_OPS=$W/a1_approved_ops.commit; git -C "$HERE" rev-parse HEAD > "$A1_APPROVED_OPS"
TAG=ops5_$$
FPAT="BinanceOrderTradingManager fk_$TAG"
cleanup() { local p; for p in $(pgrep -f "fk_$TAG" 2>/dev/null); do [ "$p" != $$ ] && kill "$p" 2>/dev/null; done; }
trap cleanup EXIT
trap 'exit 130' INT TERM HUP
PASS=0; FAILN=0
chk() { if eval "$2"; then PASS=$((PASS+1)); echo "  [PASS] $1"; else FAILN=$((FAILN+1)); echo "  [FAIL] $1"; [ -n "${OUT:-}" ] && printf '%s\n' "$OUT" | tail -8 | sed 's/^/      | /'; fi; }
D7() { TZ=Asia/Ho_Chi_Minh date -d @"$1" '+%d/%m/%Y %H:%M:%S.000'; }
NOW=$(date +%s)
# ---------------------------------------------------------------- 242 gia
F=$W/v_t_m; mkdir -p "$F/conf" "$F/bin" "$F/logs" "$F/run" "$F/target" "$W/deploy" "$W/api" "$W/py/bin"
echo "jar gia ops5" > "$F/target/binance-java-sdk-1.2.4.jar"; JM=$(md5sum < "$F/target/binance-java-sdk-1.2.4.jar" | cut -c1-32)
printf 'export LIVE_ADAPTER=live\nexport C3_CAPITAL=1000\n' > "$F/conf/env.sh"
SKEY=fakekey_$(printf '%040d' 7); printf 'C3_LIVE_API_KEY=%s\nC3_LIVE_API_SECRET=fakesecret_sub_%036d\n' "$SKEY" 9 > "$W/keys_sub.env"; chmod 600 "$W/keys_sub.env"
SK8=$(printf '%s' "$SKEY" | sha256sum | cut -c1-8)
ln -s "$(command -v python3)" "$W/py/bin/python3"
startbot() {   # $1 = C3_CAPITAL
  cleanup; sleep 0.3
  (cd "$F" && env -i PATH="$PATH" C3_CAPITAL="$1" LIVE_ADAPTER=live LIVE_C3_KEYS_FILE="$W/keys_sub.env" setsid bash -c "exec -a '$FPAT' sleep 900" >/dev/null 2>&1 &)
  sleep 0.5
}
cat > "$W/fakecurl.sh" <<EOC
#!/bin/bash
cfg=\$(cat); u=\$(printf '%s' "\$cfg" | sed -n 's/^url = "\([^"?]*\).*/\1/p'); n=\${u##*/}
echo "\$n" >> $W/api/calls.log
printf '%s' "\$cfg" | grep -q 'X-MBX-APIKEY: fakekey_' || { printf '{"code":-2015}\nHTTP=401'; exit 0; }
c=200; [ -f "$W/api/\$n.code" ] && c=\$(cat "$W/api/\$n.code")
printf 'HTTP/1.1 %s\r\nx-mbx-used-weight-1m: 77\r\n\r\n' "\$c" >&2
cat "$W/api/\$n.json" 2>/dev/null; printf '\nHTTP=%s' "\$c"
EOC
chmod +x "$W/fakecurl.sh"
api() { printf '%s' "$2" > "$W/api/$1.json"; }
api account '{"totalMarginBalance":"1000.00","availableBalance":"990.00","assets":[{"asset":"USDT","walletBalance":"1000.00","marginBalance":"1000.00","marginAvailable":true}]}'
api openOrders '[]'; api openAlgoOrders '[]'; api positionRisk '[]'
E() { env SSH_242="bash -c" APP_DIR="$F" PROC_PAT="$FPAT" KEYS_FILE="$W/keys_sub.env" SUB_KEY_SHA8="$SK8" C3_ACCOUNT=SUB \
  PY242="$W/py/bin/python3" CURL242="$W/fakecurl.sh" DEPLOY_TG_SINK="$W/tg.txt" LOGDIR="$W/deploy" GL_MON_FLAG="$W/deploy/golive_monitor.on" \
  GATE_DIR="$W/gates" SSH_RETRY_S=1 "$@"; }
nosec() { ! printf '%s' "$1" | grep -q "$SKEY\|fakesecret_sub" && ! grep -rqs "$SKEY\|fakesecret_sub" "$W/deploy" "$W/tg.txt"; }
startbot 1000

echo "== OPS5 muc 1: golive_first_trade_check.sh"
FTD=$W/deploy/first_trade
book() { printf '%s' "$1" > "$F/run/c3live_book.json"; }
T1=$((NOW - 900)); T2=$((NOW - 600))
{ echo "$(D7 $((NOW - 3600))) INFO  [main] c.b.c.u.Utils: MainClass: com.binance.chuyennd.trading.BinanceOrderTradingManager APPDir: ./run"
  echo "$(D7 $((NOW - 3000))) INFO  [pool-1-thread-1] c.b.c.c.e.C3LiveEntry: [C3-LIVE] SUBMIT OLDUSDT PREDICT_SYMBOL_TRADE SUBMITTED cid=c3-OLDUSDT-1-0 qty=1 budget=99 legIdx=0 notional=99 U_before=0.0"
  echo "$(D7 $((NOW - 2000))) INFO  [main] c.b.c.u.Utils: MainClass: com.binance.chuyennd.trading.BinanceOrderTradingManager APPDir: ./run"
  echo "$(D7 $T1) INFO  [pool-1-thread-1] c.b.c.c.e.C3LiveEntry: [C3-LIVE] SUBMIT UAIUSDT PREDICT_SYMBOL_TRADE SUBMITTED cid=c3-UAIUSDT-29898231-0 qty=228 budget=22.5 legIdx=0 notional=22.43519926071166896 U_before=0.0"
  echo "$(D7 $T2) INFO  [pool-1-thread-1] c.b.c.c.e.C3LiveEntry: [C3-LIVE] SUBMIT IDOLUSDT PREDICT_SYMBOL_TRADE SUBMITTED cid=c3-IDOLUSDT-29898231-0 qty=1019 budget=21.658679962158203 legIdx=0 notional=21.64967324770987053 U_before=0.02243519926071167"
} > "$F/logs/full.log"
book '{"clusters":[{"symbol":"UAIUSDT","adj_qty":"228","armed":false},{"symbol":"IDOLUSDT","adj_qty":"1019","armed":false}]}'
api positionRisk '[{"symbol":"UAIUSDT","positionAmt":"228"},{"symbol":"IDOLUSDT","positionAmt":"1019"}]'
: > "$W/api/calls.log"
OUT=$(E DRY=1 bash "$HERE/golive_first_trade_check.sh" 2>&1); RC=$?
chk "m1 DRY: (a) 2 dong JVM hien tai DAT (dong OLDUSDT cua JVM cu bo qua), KHONG goi san, KHONG ghi state/bang chung/Telegram" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'sizing_iv: DAT (dong SUBMIT JVM nay: 2, lech: 0)' && ! echo \"\$OUT\" | grep -q OLDUSDT && [ ! -s $W/api/calls.log ] && [ ! -s $FTD/state.txt ] && ! ls $FTD/SIZING_IV_* >/dev/null 2>&1 && [ ! -e $W/tg.txt ]"
OUT=$(E bash "$HERE/golive_first_trade_check.sh" 2>&1); RC=$?
EV=$(ls -t $FTD/SIZING_IV_*.md 2>/dev/null | head -1)
chk "m1 lan 1: sizing_iv DAT, vi the co tren san, chua arm => cho; bang chung co 'sizing_iv: DAT' + md5 jar + 2 dong; Telegram tom tat" "[ $RC = 0 ] && [ -n '$EV' ] && grep -qx 'sizing_iv: DAT' '$EV' && grep -qx 'jar_md5: $JM' '$EV' && [ \$(grep -c '^| c3-' '$EV') = 2 ] && grep -q 'OK_CO_VI_THE/CHO' '$EV' && grep -q 'sizing_iv=DAT' $W/tg.txt && grep -q 'mon\|account' $W/api/calls.log"
chk "m1 W_USED_1M in ra + khong lo key/secret (output, bang chung, Telegram)" "echo \"\$OUT\" | grep -q 'W_USED_1M=77' && nosec \"\$OUT\""
N0=$(ls $FTD/SIZING_IV_*.md | wc -l); G0=$(grep -c '^----' $W/tg.txt)
sleep 1; OUT=$(E bash "$HERE/golive_first_trade_check.sh" 2>&1); RC=$?
chk "m1 idempotent: chay lai khong co gi moi => khong bang chung moi, khong Telegram" "[ $RC = 0 ] && [ \$(ls $FTD/SIZING_IV_*.md | wc -l) = $N0 ] && [ \$(grep -c '^----' $W/tg.txt) = $G0 ] && echo \"\$OUT\" | grep -q 'khong co ket qua moi'"
book '{"clusters":[{"symbol":"UAIUSDT","adj_qty":"228","armed":true},{"symbol":"IDOLUSDT","adj_qty":"1019","armed":false}]}'
api openAlgoOrders '[{"symbol":"UAIUSDT","clientAlgoId":"c3s-UAIUSDT-1-1"}]'
sleep 1; OUT=$(E bash "$HERE/golive_first_trade_check.sh" 2>&1); RC=$?
EV=$(ls -t $FTD/SIZING_IV_*.md | head -1)
chk "m1 arm: UAIUSDT da arm + co algo c3s- tren san => OK_ARM_CO_ALGO, bang chung moi" "[ $RC = 0 ] && grep -q 'UAIUSDT.*OK_CO_VI_THE/OK_ARM_CO_ALGO' '$EV' && grep -qx 'doi_chieu_san: DAT' '$EV'"
book '{"clusters":[{"symbol":"UAIUSDT","adj_qty":"228","armed":true},{"symbol":"IDOLUSDT","adj_qty":"1019","armed":true}]}'
G0=$(grep -c '^----' $W/tg.txt)
sleep 1; OUT=$(E bash "$HERE/golive_first_trade_check.sh" 2>&1); RC=$?
chk "m1 tiem loi: IDOLUSDT arm nhung san KHONG co algo c3 - luot 1 chua bao (cho 1 luot)" "[ $RC = 0 ] && [ \$(grep -c '^----' $W/tg.txt) = $G0 ]"
sleep 1; OUT=$(E bash "$HERE/golive_first_trade_check.sh" 2>&1); RC=$?
EV=$(ls -t $FTD/SIZING_IV_*.md | head -1)
chk "m1 tiem loi: arm khong algo 2 luot lien tiep => FAIL_ARM_KHONG_ALGO, rc 2, Telegram KHAN, doi_chieu_san FAIL" "[ $RC = 2 ] && grep -q 'IDOLUSDT.*FAIL_ARM_KHONG_ALGO' '$EV' && grep -qx 'doi_chieu_san: FAIL' '$EV' && tail -3 $W/tg.txt | grep -q 'KHAN sizing_iv'"
# budget lech 3 % + DCA legIdx 0 + DCA hop le (U_before=0.36807 => 22.5 x (1-0.36807/0.6) = 8.6973)
echo "$(D7 $((NOW - 500))) INFO  [pool-1-thread-1] c.b.c.c.e.C3LiveEntry: [C3-LIVE] SUBMIT BADUSDT PREDICT_SYMBOL_TRADE SUBMITTED cid=c3-BADUSDT-2-0 qty=1 budget=23.175 legIdx=0 notional=23.1 U_before=0.0" >> "$F/logs/full.log"
api positionRisk '[{"symbol":"UAIUSDT","positionAmt":"228"},{"symbol":"IDOLUSDT","positionAmt":"1019"},{"symbol":"BADUSDT","positionAmt":"1"}]'
book '{"clusters":[{"symbol":"UAIUSDT","adj_qty":"228","armed":true},{"symbol":"IDOLUSDT","adj_qty":"1019","armed":true},{"symbol":"BADUSDT","adj_qty":"1"}]}'
OUT=$(E bash "$HERE/golive_first_trade_check.sh" 2>&1); RC=$?
EV=$(ls -t $FTD/SIZING_IV_*.md | head -1)
chk "m1 tiem loi: budget lech +3 % => sizing_iv: FAIL (budget_lech_+3.00%), rc 2, Telegram KHAN" "[ $RC = 2 ] && grep -qx 'sizing_iv: FAIL' '$EV' && grep -q 'BADUSDT.*FAIL.*budget_lech_+3.00%' '$EV' && tail -3 $W/tg.txt | grep -q 'KHAN sizing_iv.*sizing_iv=FAIL'"
echo "$(D7 $((NOW - 400))) INFO  [pool-1-thread-1] c.b.c.c.e.C3LiveEntry: [C3-LIVE] SUBMIT DCAUSDT DCA_LEVEL1 SUBMITTED cid=c3-DCAUSDT-3-1 qty=1 budget=8.6973 legIdx=1 notional=8.69 U_before=0.36807153650360164" >> "$F/logs/full.log"
echo "$(D7 $((NOW - 390))) INFO  [pool-1-thread-1] c.b.c.c.e.C3LiveEntry: [C3-LIVE] SUBMIT DC0USDT DCA_LEVEL1 SUBMITTED cid=c3-DC0USDT-3-0 qty=1 budget=8.6973 legIdx=0 notional=8.69 U_before=0.36807153650360164" >> "$F/logs/full.log"
OUT=$(E bash "$HERE/golive_first_trade_check.sh" 2>&1); RC=$?
EV=$(ls -t $FTD/SIZING_IV_*.md | head -1)
chk "m1 DCA: leg DCA legIdx=1 dung cong thuc => DAT; leg DCA legIdx=0 => FAIL leg_DCA_legIdx<1; (b) DCAUSDT khong co trong so/san => OK_DA_DONG" "[ $RC = 2 ] && grep -q 'c3-DCAUSDT-3-1 .*| DAT |' '$EV' && grep -q 'c3-DC0USDT-3-0 .*FAIL.*leg_DCA_legIdx<1' '$EV' && grep -q 'c3-DCAUSDT-3-1 .*OK_DA_DONG' '$EV'"
# so co, san khong (sau grace) => FAIL
echo "$(D7 $((NOW - 300))) INFO  [pool-1-thread-1] c.b.c.c.e.C3LiveEntry: [C3-LIVE] SUBMIT GHOUSDT PREDICT_SYMBOL_TRADE SUBMITTED cid=c3-GHOUSDT-4-0 qty=1 budget=22.5 legIdx=0 notional=22.5 U_before=0" >> "$F/logs/full.log"
book '{"clusters":[{"symbol":"UAIUSDT","adj_qty":"228","armed":true},{"symbol":"IDOLUSDT","adj_qty":"1019","armed":true},{"symbol":"BADUSDT","adj_qty":"1"},{"symbol":"GHOUSDT","adj_qty":"1"}]}'
OUT=$(E bash "$HERE/golive_first_trade_check.sh" 2>&1); RC=$?
EV=$(ls -t $FTD/SIZING_IV_*.md | head -1)
chk "m1 tiem loi: so c3 co GHOUSDT nhung san KHONG co vi the (qua grace) => FAIL_SO_CO_SAN_KHONG rc 2" "[ $RC = 2 ] && grep -q 'GHOUSDT.*FAIL_SO_CO_SAN_KHONG' '$EV'"
# san loi => (b) khong do duoc, giu cho, khong FAIL
echo "$(D7 $((NOW - 200))) INFO  [pool-1-thread-1] c.b.c.c.e.C3LiveEntry: [C3-LIVE] SUBMIT NEWUSDT PREDICT_SYMBOL_TRADE SUBMITTED cid=c3-NEWUSDT-5-0 qty=1 budget=22.5 legIdx=0 notional=22.5 U_before=0" >> "$F/logs/full.log"
echo 500 > $W/api/positionRisk.code
OUT=$(E bash "$HERE/golive_first_trade_check.sh" 2>&1); RC=$?
EV=$(ls -t $FTD/SIZING_IV_*.md | head -1)
chk "m1 san loi (HTTP 500): (b) KHONG DO DUOC luot nay - NEWUSDT giu CHO/CHO, (a) van cham DAT" "echo \"\$OUT\" | grep -q 'doc san KHONG tron ven' && grep -q 'c3-NEWUSDT-5-0 .*| DAT | CHO/CHO' '$EV' && grep -q 'luot nay khong doc duoc san' '$EV'"
rm -f $W/api/positionRisk.code
# JVM moi: dong truoc MainClass moi KHONG tinh
echo "$(D7 $((NOW - 100))) INFO  [main] c.b.c.u.Utils: MainClass: com.binance.chuyennd.trading.BinanceOrderTradingManager APPDir: ./run" >> "$F/logs/full.log"
OUT=$(E DRY=1 bash "$HERE/golive_first_trade_check.sh" 2>&1); RC=$?
chk "m1 JVM moi (MainClass moi): 0 dong SUBMIT => sizing_iv KHONG_DO_DUOC" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'sizing_iv: KHONG_DO_DUOC (0 dong SUBMIT JVM nay)'"
startbot abc
OUT=$(E DRY=1 bash "$HERE/golive_first_trade_check.sh" 2>&1); RC=$?
chk "m1 C3_CAPITAL process khong hop le => DUNG rc 1" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'C3_CAPITAL process khong hop le'"
startbot 1000
printf '#!/bin/bash\necho CALLED >> %s/ssh_called\nexit 255\n' "$W" > $W/sshspy.sh; chmod +x $W/sshspy.sh
rm -f $W/deploy/golive_monitor.on
OUT=$(E SSH_242="bash $W/sshspy.sh" FT_CRON=1 bash "$HERE/golive_first_trade_check.sh" 2>&1); RC=$?
chk "m1 cron KHONG co co micro/pilot => thoat ngay rc 0, 0 ssh" "[ $RC = 0 ] && [ ! -e $W/ssh_called ] && [ -z \"\$OUT\" ]"
printf 'C3_ACCOUNT=SUB\nKEYS_FILE=%s\n' "$W/keys_sub.env" > $W/deploy/golive_monitor.on
OUT=$(E SSH_242="bash $W/sshspy.sh" FT_CRON=1 bash "$HERE/golive_first_trade_check.sh" 2>&1); RC=$?
chk "m1 cron co co + ssh 242 loi => DUNG rc 1 (ghi ft_cron.log), khong state hong" "[ $RC = 1 ] && grep -q 'doc trang thai 242 loi' $FTD/ft_cron.log && [ -s $FTD/state.txt ]"
OUT=$(E A1_APPROVED_OPS=$W/khong_co.commit DRY=1 bash "$HERE/golive_first_trade_check.sh" 2>&1); RC=$?
chk "m1 pin: HEAD khong trong A1_APPROVED_OPS => TU CHOI [m1]" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'TU CHOI \[m1\]'"
chk "m1 khong lo key/secret trong toan bo deploy/ + Telegram" "nosec ''"

# == KET THUC ==
cleanup
echo "TEST $( [ $FAILN = 0 ] && echo PASS || echo FAIL ) $PASS/$((PASS+FAILN))"
[ $FAILN = 0 ]
