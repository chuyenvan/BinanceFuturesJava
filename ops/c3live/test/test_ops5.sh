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
chk "m1 DRY: (a) 2 dong trong cua so (lan dau: NOW - 1800 s) DAT (OLDUSDT 3000 s truoc ngoai cua so), KHONG goi san, KHONG ghi state/bang chung/Telegram" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'sizing_iv: DAT (dong SUBMIT cham: 2, lech: 0, REJECTED: 0)' && ! echo \"\$OUT\" | grep -q OLDUSDT && [ ! -s $W/api/calls.log ] && [ ! -s $FTD/state.txt ] && ! ls $FTD/SIZING_IV_* >/dev/null 2>&1 && [ ! -e $W/tg.txt ]"
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
chk "m1 JVM moi (MainClass moi) [B3 sua hanh vi cu]: dong cua JVM truoc trong cua so / con cho VAN duoc cham => sizing_iv FAIL (BADUSDT), khong con KHONG_DO_DUOC sai" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'sizing_iv: FAIL' && echo \"\$OUT\" | grep -q 'BADUSDT'"
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

# ---- [OPS5_FIX MINOR B3/B4/cron-repo] cua so qua JVM restart / log xoay; REJECTED; cron TU CHOI khong im lang
cp $F/logs/full.log $W/full.log.b5bak; FTB=$W/ft_b5; EB() { E FT_DIR=$FTB "$@"; }
MCLB() { echo "$(D7 $1) INFO  [main] c.b.c.u.Utils: MainClass: com.binance.chuyennd.trading.BinanceOrderTradingManager APPDir: ./run"; }
SUBB() { echo "$(D7 $1) INFO  [pool-1-thread-1] c.b.c.c.e.C3LiveEntry: [C3-LIVE] SUBMIT $2 PREDICT_SYMBOL_TRADE SUBMITTED cid=c3-$2-$1-0 qty=1 budget=$3 legIdx=0 notional=$3 U_before=0.0"; }
api positionRisk '[]'; book '{"clusters":[]}'
{ MCLB $((NOW - 900)); SUBB $((NOW - 600)) LOSTUSDT 99; MCLB $((NOW - 300)); } > $F/logs/full.log
OUT=$(EB DRY=1 bash "$HERE/golive_first_trade_check.sh" 2>&1); RC=$?
chk "b1 [B3] SUBMIT lech o JVM TRUOC restart (chua cron nao cham) => VAN cham: sizing_iv FAIL" "echo \"\$OUT\" | grep -q 'sizing_iv: FAIL (dong SUBMIT cham: 1, lech: 1' && echo \"\$OUT\" | grep -q 'so lan khoi dong JVM trong cua so: 2'"
{ MCLB $((NOW - 900)); SUBB $((NOW - 600)) ROTUSDT 99; } > $F/logs/full.log.1; MCLB $((NOW - 200)) > $F/logs/full.log
OUT=$(EB DRY=1 bash "$HERE/golive_first_trade_check.sh" 2>&1); RC=$?; rm -f $F/logs/full.log.1
chk "b2 [B3] SUBMIT chi con trong full.log.1 (log da xoay) => VAN cham (FAIL)" "echo \"\$OUT\" | grep -q 'ROTUSDT' && echo \"\$OUT\" | grep -q 'sizing_iv: FAIL'"
RN=$(date +%s); { MCLB $((RN - 1500)); SUBB $((RN - 1200)) OLDWUSDT 99; MCLB $((RN - 300)); } > $F/logs/full.log; mkdir -p $FTB; echo $((RN - 60)) > $FTB/last_check
OUT=$(EB DRY=1 bash "$HERE/golive_first_trade_check.sh" 2>&1); RC=$?; rm -f $FTB/last_check
chk "b3 [B3] SUBMIT truoc (lan cham cuoi - 900 s) => ngoai cua so (da cham o luot truoc) => khong cham lai" "! echo \"\$OUT\" | grep -q OLDWUSDT && echo \"\$OUT\" | grep -q 'truoc cua so bo qua: 1'"
{ MCLB $((NOW - 900)); SUBB $((NOW - 600)) REJUSDT 22.5; echo "$(D7 $((NOW - 599))) WARN  [x] c.b.c.c.e.C3LiveOrderExecutor: [C3-LIVE-EXEC] REJUSDT c3-REJUSDT-$((NOW - 600))-0 KHONG khop (REJECTED -2019) => huy giu cho"
  SUBB $((NOW - 500)) RJ2USDT 22.5; echo "$(D7 $((NOW - 499))) WARN [x] C3LiveExec: [C3-LIVE] REJECT RJ2USDT cid=c3-RJ2USDT-x code=-2019"; SUBB $((NOW - 400)) OKBUSDT 22.5; } > $F/logs/full.log
api positionRisk '[{"symbol":"OKBUSDT","positionAmt":"1"}]'; book '{"clusters":[{"symbol":"OKBUSDT","adj_qty":"1"}]}'
OUT=$(EB bash "$HERE/golive_first_trade_check.sh" 2>&1); RC=$?; EV=$(ls -t $FTB/SIZING_IV_*.md 2>/dev/null | head -1)
chk "b4 [B4] REJECT khop cid + REJECT cid la (khop symbol <= 300 s) => REJECTED/NA_REJECTED (KHONG OK_DA_DONG), khong tinh DAT; OKBUSDT DAT; last_check ghi" "[ $RC = 0 ] && grep -q '^c3-REJUSDT-.*|REJECTED|NA_REJECTED|' $FTB/state.txt && grep -q '^c3-RJ2USDT-.*|REJECTED|NA_REJECTED|' $FTB/state.txt && ! grep -q 'REJUSDT|.*OK_DA_DONG' $FTB/state.txt && grep -qx 'sizing_iv: DAT' '$EV' && echo \"\$OUT\" | grep -q 'dong SUBMIT cham: 1, lech: 0, REJECTED: 2' && [ -s $FTB/last_check ]"
{ MCLB $((NOW - 900)); SUBB $((NOW - 600)) REJUSDT 22.5; echo "$(D7 $((NOW - 599))) WARN [x] y: [C3-LIVE] REJECT REJUSDT cid=c3-REJUSDT-$((NOW - 600))-0 code=-2019"; } > $F/logs/full.log; rm -rf $FTB
OUT=$(EB DRY=1 bash "$HERE/golive_first_trade_check.sh" 2>&1); RC=$?
chk "b5 [B4] chi co lenh REJECTED => sizing_iv KHONG_DO_DUOC (khong phai DAT)" "echo \"\$OUT\" | grep -q 'sizing_iv: KHONG_DO_DUOC (0 dong SUBMIT khong-REJECTED trong cua so; REJECTED 1)'"
{ MCLB $((NOW - 900)); SUBB $((NOW - 600)) PNDUSDT 22.5; } > $F/logs/full.log; rm -rf $FTB
api positionRisk '[{"symbol":"PNDUSDT","positionAmt":"1"}]'; book '{"clusters":[{"symbol":"PNDUSDT","adj_qty":"1","armed":false}]}'
OUT=$(EB bash "$HERE/golive_first_trade_check.sh" 2>&1)
MCLB $((NOW - 100)) > $F/logs/full.log; book '{"clusters":[{"symbol":"PNDUSDT","adj_qty":"1","armed":true}]}'; api openAlgoOrders '[{"symbol":"PNDUSDT","clientAlgoId":"c3s-PNDUSDT-1-1"}]'
sleep 1; OUT=$(EB bash "$HERE/golive_first_trade_check.sh" 2>&1); RC=$?
chk "b6 [B3] cid CON CHO trong state ma SUBMIT da ra khoi log => van doi chieu tiep (arm => OK_ARM_CO_ALGO)" "grep -q '^c3-PNDUSDT-.*|OK_CO_VI_THE|OK_ARM_CO_ALGO|' $FTB/state.txt"
api openAlgoOrders '[]'
printf 'C3_ACCOUNT=SUB\nKEYS_FILE=%s\n' "$W/keys_sub.env" > $W/deploy/golive_monitor.on; G0=$(grep -c 'TU CHOI \[m1\]' $W/tg.txt 2>/dev/null)
OUT=$(EB A1_APPROVED_OPS=$W/khong_co.commit FT_CRON=1 bash "$HERE/golive_first_trade_check.sh" 2>&1); RC1=$?
OUT=$(EB A1_APPROVED_OPS=$W/khong_co.commit FT_CRON=1 bash "$HERE/golive_first_trade_check.sh" 2>&1); RC2=$?
G1=$(grep -c 'TU CHOI \[m1\]' $W/tg.txt 2>/dev/null)
chk "b7 [cron] HEAD chua duyet / repo ban + co micro => KHONG im lang: ft_cron.log ghi ly do 2 lan, Telegram CANH BAO dung 1 lan/ngay (G0=${G0:-0} G1=$G1)" "[ $RC1 = 1 ] && [ $RC2 = 1 ] && [ \$(grep -c 'TU CHOI \[m1\]' $FTB/ft_cron.log) = 2 ] && [ \"$G1\" = \$(( ${G0:-0} + 1 )) ] && grep -q 'CANH BAO cron golive_first_trade_check TU CHOI' $W/tg.txt"
rm -f $W/deploy/golive_monitor.on
OUT=$(EB A1_APPROVED_OPS=$W/khong_co.commit FT_CRON=1 bash "$HERE/golive_first_trade_check.sh" 2>&1); RC=$?
chk "b8 [cron] khong co co micro => thoat im rc 0 (ke ca repo chua duyet)" "[ $RC = 0 ] && [ -z \"\$OUT\" ]"
printf 'C3_ACCOUNT=SUB\nKEYS_FILE=%s\n' "$W/keys_sub.env" > $W/deploy/golive_monitor.on
cp $W/full.log.b5bak $F/logs/full.log; api positionRisk '[]'; book '{"clusters":[]}'

# ---- [OPS5_FIX M-3] phan loai dong FAIL (C_eff / TIER_3) - phan quyet prereg giu nguyen
cp $F/logs/full.log $W/full.log.m3bak; FT2=$W/ft_m3; E2() { E FT_DIR=$FT2 "$@"; }
MCL3() { echo "$(D7 $1) INFO  [main] c.b.c.u.Utils: MainClass: com.binance.chuyennd.trading.BinanceOrderTradingManager APPDir: ./run"; }
SUB3() { echo "$(D7 $1) INFO  [pool-1-thread-1] c.b.c.c.e.C3LiveEntry: [C3-LIVE] SUBMIT $2 PREDICT_SYMBOL_TRADE SUBMITTED cid=c3-$2-$1-0 qty=1 budget=$3 legIdx=0 notional=$3 U_before=0.0"; }
printf 'tmb0=1000\nc3_capital=1000\nkey_sha8=%s\nbase_id=t\nrebase_t=1\nreason=t\n' "$SK8" > $W/deploy/c3sub_eq_base.txt
api account '{"totalMarginBalance":"970.00","availableBalance":"990.00","assets":[]}'
api positionRisk '[{"symbol":"EQUSDT","positionAmt":"1"},{"symbol":"T3USDT","positionAmt":"1"},{"symbol":"XXUSDT","positionAmt":"1"},{"symbol":"T4USDT","positionAmt":"1"}]'
book '{"clusters":[{"symbol":"EQUSDT","adj_qty":"1"},{"symbol":"T3USDT","adj_qty":"1"},{"symbol":"XXUSDT","adj_qty":"1"},{"symbol":"T4USDT","adj_qty":"1"}]}'
{ MCL3 $((NOW - 900)); SUB3 $((NOW - 600)) EQUSDT 21.825; } > $F/logs/full.log
OUT=$(E2 bash "$HERE/golive_first_trade_check.sh" 2>&1); RC=$?; EV=$(ls -t $FT2/SIZING_IV_*.md 2>/dev/null | head -1)
chk "f1 [M-3] C_eff=970 (eq=C3_CAPITAL+(TMB-tmb0)): sizing_iv FAIL GIU NGUYEN + phan loai GIAI_THICH_DUOC_CEFF (file co ca 2 + nguon), Telegram CANH BAO 'can MASTER phan xu' KHONG chu KHAN, rc 2" "[ $RC = 2 ] && grep -qx 'sizing_iv: FAIL' '$EV' && grep -q 'EQUSDT .*GIAI_THICH_DUOC_CEFF(C_eff=970.00,eq=C3_CAPITAL+(TMB-tmb0),uoc_luong_sau_fill)' '$EV' && grep -q '^phan_loai_FAIL_a: giai_thich_duoc_C_eff(uoc_luong_sau_fill)=1 KHONG_giai_thich_duoc=0' '$EV' && grep -q '^nguon_C_eff: gl_api242 mon .*TMB=970.00 AVAIL=990.00 .*tmb0=1000' '$EV' && tail -2 $W/tg.txt | grep -q 'CANH BAO sizing_iv FAIL-GIAI-THICH-DUOC.*can MASTER phan xu' && ! tail -2 $W/tg.txt | grep -q KHAN"
SUB3 $((NOW - 500)) T3USDT 11.25 >> $F/logs/full.log
OUT=$(E2 bash "$HERE/golive_first_trade_check.sh" 2>&1); RC=$?; EV=$(ls -t $FT2/SIZING_IV_*.md | head -1)
chk "f2 [F4] budget = x0,5 (giong TIER_3) nhung tier KHONG xac minh duoc tu ops => KHONG_GIAI_THICH_DUOC(...goi_y_x0.5_TIER3_chua_xac_minh) => KHAN" "[ $RC = 2 ] && grep -qx 'sizing_iv: FAIL' '$EV' && grep -q 'T3USDT .*KHONG_GIAI_THICH_DUOC(C_eff=970.00,.*goi_y_x0.5_TIER3_chua_xac_minh)' '$EV' && tail -2 $W/tg.txt | grep -q 'KHAN sizing_iv'"
SUB3 $((NOW - 400)) XXUSDT 99 >> $F/logs/full.log
OUT=$(E2 bash "$HERE/golive_first_trade_check.sh" 2>&1); RC=$?; EV=$(ls -t $FT2/SIZING_IV_*.md | head -1)
chk "f3 [M-3] budget 99 => KHONG_GIAI_THICH_DUOC(C_eff=970.00,...) => Telegram KHAN; dong cu giu phan loai cu" "[ $RC = 2 ] && grep -q 'XXUSDT .*KHONG_GIAI_THICH_DUOC(C_eff=970.00' '$EV' && grep -q 'EQUSDT .*GIAI_THICH_DUOC_CEFF' '$EV' && tail -2 $W/tg.txt | grep -q 'KHAN sizing_iv'"
cleanup; sleep 0.3; (cd "$F" && env -i PATH="$PATH" C3_CAPITAL=1000 TIER_FLAT=1 LIVE_ADAPTER=live LIVE_C3_KEYS_FILE="$W/keys_sub.env" setsid bash -c "exec -a '$FPAT' sleep 900" >/dev/null 2>&1 &); sleep 0.5
SUB3 $((NOW - 300)) T4USDT 11.25 >> $F/logs/full.log
OUT=$(E2 bash "$HERE/golive_first_trade_check.sh" 2>&1); RC=$?; EV=$(ls -t $FT2/SIZING_IV_*.md | head -1)
chk "f4 [M-3] TIER_FLAT=1 tren process => x0,5 KHONG giai thich duoc => KHAN" "[ $RC = 2 ] && grep -q 'T4USDT .*KHONG_GIAI_THICH_DUOC' '$EV' && grep -q 'TIER_FLAT env process=1' '$EV' && tail -2 $W/tg.txt | grep -q 'KHAN sizing_iv'"
OUT=$(E2 DRY=1 bash "$HERE/golive_first_trade_check.sh" 2>&1); RC=$?
chk "f5 [M-3] DRY (khong doc san): dong moi khong co C_eff => in phan loai 'khong_doc_duoc_C_eff' hoac giu nhan cu tu state; sizing_iv FAIL" "echo \"\$OUT\" | grep -q 'sizing_iv: FAIL' && echo \"\$OUT\" | grep -q 'phan_loai_FAIL (a): giai_thich_duoc_C_eff(uoc_luong_sau_fill)=1 KHONG_giai_thich_duoc=3'"
startbot 1000; cp $W/full.log.m3bak $F/logs/full.log; rm -f $W/deploy/c3sub_eq_base.txt
api account '{"totalMarginBalance":"1000.00","availableBalance":"990.00","assets":[{"asset":"USDT","walletBalance":"1000.00","marginBalance":"1000.00","marginAvailable":true}]}'
api positionRisk '[]'; book '{"clusters":[]}'

echo "== OPS5 muc 2a: golive_deadman.sh + install_ops5_oracle.sh"
DMD=$W/deploy/deadman
printf 'MemTotal: 24000000 kB\nMemAvailable: 8000000 kB\n' > $W/meminfo
(setsid bash -c "exec -a 'fk_${TAG}_watch_daily_v12.sh' sleep 900" >/dev/null 2>&1 &); sleep 0.3
gate_at() { echo "$(D7 $1) INFO  [pool-1-thread-1] c.b.c.t.DetectEntrySignal2TradeNormal: [GATE] scale=1.5500 topk=24 n_pass=0 ${2:-}" >> "$F/logs/full.log"; }
DM() { env SSH_242="bash -c" APP_DIR="$F" LOGDIR="$W/deploy" GL_MON_FLAG="$W/deploy/golive_monitor.on" MON_HB_FILE="$W/deploy/run/monitor_heartbeat" \
  DM_WATCH_PAT="fk_${TAG}_watch_daily_v12.sh" DM_DISK_MIN_GB=0 DM_MEMINFO=$W/meminfo DEPLOY_TG_SINK=$W/tgdm.txt "$@"; }
mkdir -p $W/deploy/run; printf 'C3_ACCOUNT=SUB\n' > $W/deploy/golive_monitor.on
touch $W/deploy/run/monitor_heartbeat; gate_at $(( $(date +%s) - 30 ))
OUT=$(DM bash "$HERE/golive_deadman.sh" 2>&1); RC=$?
chk "d1 moi thu OK => rc 0, khong Telegram, heartbeat deadman ghi" "[ $RC = 0 ] && [ ! -e $W/tgdm.txt ] && grep -q '^ts=' $DMD/heartbeat && echo \"\$OUT\" | grep -q 'OK gate tuoi' && echo \"\$OUT\" | grep -q 'OK watcher'"
touch -d '-20 min' $W/deploy/run/monitor_heartbeat
OUT=$(DM bash "$HERE/golive_deadman.sh" 2>&1); RC=$?
chk "d2 tiem loi: heartbeat monitor cu 20' => CANH BAO mon_hb + Telegram 1 lan, rc 2" "[ $RC = 2 ] && [ \$(grep -c 'CANH BAO mon_hb' $W/tgdm.txt) = 1 ]"
OUT=$(DM bash "$HERE/golive_deadman.sh" 2>&1); RC=$?
chk "d2 chong spam: lan 2 (< 30') KHONG gui lai" "[ $RC = 2 ] && [ \$(grep -c 'CANH BAO mon_hb' $W/tgdm.txt) = 1 ] && echo \"\$OUT\" | grep -q 'da bao < 1800s truoc'"
OUT=$(DM DM_REMIND_S=0 bash "$HERE/golive_deadman.sh" 2>&1); RC=$?
chk "d2 nhac lai sau DM_REMIND_S" "[ \$(grep -c 'CANH BAO mon_hb' $W/tgdm.txt) = 2 ]"
touch $W/deploy/run/monitor_heartbeat
OUT=$(DM bash "$HERE/golive_deadman.sh" 2>&1); RC=$?; OUT2=$(DM bash "$HERE/golive_deadman.sh" 2>&1)
chk "d2 hoi phuc: tin 'DA HOI PHUC mon_hb' dung 1 lan, rc 0" "[ $RC = 0 ] && [ \$(grep -c 'DA HOI PHUC mon_hb' $W/tgdm.txt) = 1 ]"
rm -f $W/deploy/golive_monitor.on; touch -d '-30 min' $W/deploy/run/monitor_heartbeat
OUT=$(DM bash "$HERE/golive_deadman.sh" 2>&1); RC=$?
chk "d3 khong co co micro/pilot => bo qua mon_hb (monitor khong chay)" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'bo qua mon_hb'"
printf 'C3_ACCOUNT=SUB\n' > $W/deploy/golive_monitor.on; touch $W/deploy/run/monitor_heartbeat
gate_at $(( $(date +%s) - 240 )) ; sed -i '$!{/\[GATE\] /d}' "$F/logs/full.log"
OUT=$(DM bash "$HERE/golive_deadman.sh" 2>&1); RC=$?
chk "d4 tiem loi: dong [GATE] cuoi cu 4' => CANH BAO gate (bot treo) + Telegram" "[ $RC = 2 ] && grep -q 'CANH BAO gate.*bot treo' $W/tgdm.txt"
gate_at $(( $(date +%s) - 10 )) '1234567890:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA'
OUT=$(DM bash "$HERE/golive_deadman.sh" 2>&1); RC=$?
chk "d4 gate hoi phuc => 'DA HOI PHUC gate'" "[ $RC = 0 ] && grep -q 'DA HOI PHUC gate' $W/tgdm.txt"
printf '#!/bin/bash\nexit 255\n' > $W/ssh255.sh
OUT=$(DM SSH_242="bash $W/ssh255.sh" bash "$HERE/golive_deadman.sh" 2>&1); RC=$?
chk "d5 ssh 242 loi luot 1 => chua canh bao (dem 1/2)" "[ $RC = 0 ] && ! grep -q 'CANH BAO ssh242' $W/tgdm.txt && echo \"\$OUT\" | grep -q 'luot loi lien tiep 1/2'"
OUT=$(DM SSH_242="bash $W/ssh255.sh" bash "$HERE/golive_deadman.sh" 2>&1); RC=$?
chk "d5 tiem loi: ssh 242 loi 2 luot lien tiep => CANH BAO ssh242" "[ $RC = 2 ] && grep -q 'CANH BAO ssh242' $W/tgdm.txt"
OUT=$(DM bash "$HERE/golive_deadman.sh" 2>&1); RC=$?
chk "d5 ssh hoi phuc => 'DA HOI PHUC ssh242', bo dem ve 0" "[ $RC = 0 ] && grep -q 'DA HOI PHUC ssh242' $W/tgdm.txt && grep -qx 'sshfail=0' $DMD/state"
OUT=$(DM DM_WATCH_PAT="khong_co_watcher_$TAG" bash "$HERE/golive_deadman.sh" 2>&1); RC=$?
chk "d6 tiem loi: watcher parity chet => CANH BAO watcher" "[ $RC = 2 ] && grep -q 'CANH BAO watcher' $W/tgdm.txt"
printf 'MemAvailable: 1000000 kB\n' > $W/meminfo
OUT=$(DM DM_DISK_MIN_GB=999999 bash "$HERE/golive_deadman.sh" 2>&1); RC=$?
chk "d6 tiem loi: dia < nguong + RAM available 976 MB < 2000 => CANH BAO disk + mem" "[ $RC = 2 ] && grep -q 'CANH BAO disk' $W/tgdm.txt && grep -q 'CANH BAO mem.*976 MB' $W/tgdm.txt"
printf 'MemAvailable: 8000000 kB\n' > $W/meminfo; G0=$(grep -c '^----' $W/tgdm.txt); cp $DMD/state $W/dmstate0
OUT=$(DM DRY=1 DM_WATCH_PAT="khong_co_watcher2_$TAG" DM_REMIND_S=0 bash "$HERE/golive_deadman.sh" 2>&1); RC=$?
chk "d7 DRY=1: chi in (khong gui), KHONG ghi state" "[ \$(grep -c '^----' $W/tgdm.txt) = $G0 ] && cmp -s $DMD/state $W/dmstate0 && echo \"\$OUT\" | grep -q 'DRY=1 (khong gui)'"
chk "d8 mask token trong output + Telegram; deadman KHONG source golive_lib.sh" "! grep -q '1234567890:AAAA' $W/tgdm.txt $DMD/deadman.log && ! grep -v '^[[:space:]]*#' $HERE/golive_deadman.sh | grep -q 'golive_lib'"
# installer
printf '#!/bin/bash\ncase "$1" in -l) cat %s/ct 2>/dev/null;; -) cat > %s/ct;; esac\n' "$W" "$W" > $W/ct.sh; printf '0 * * * * echo giu # cu\n*/2 * * * * x # golive_monitor (ADD4 C-1)\n' > $W/ct; cp $W/ct $W/ct0
IO() { env ORA_CRONTAB_CMD="bash $W/ct.sh" LOGDIR="$W/deploy" DM_PIN_ROOT=$W/pinned OPS5_LOCKS=$W/locks "$@"; }
OUT=$(IO DRY=1 bash "$HERE/install_ops5_oracle.sh" 2>&1 < /dev/null); RC=$?
chk "i1 install DRY=1: in 2 dong MOI, crontab KHONG doi" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'DRY PASS' && [ \$(echo \"\$OUT\" | grep -c '   MOI: ') = 2 ] && cmp -s $W/ct $W/ct0"
OUT=$(echo YES | IO bash "$HERE/install_ops5_oracle.sh" 2>&1); RC=$?
chk "i2 install: 2 dong OPS5 them, dong cu giu, ban ghim deadman chi doc dung md5" "[ $RC = 0 ] && grep -q 'golive_deadman (OPS5 2a)' $W/ct && grep -q 'FT_CRON=1 .*golive_first_trade (OPS5 1)' $W/ct && grep -q 'echo giu # cu' $W/ct && grep -q 'golive_monitor (ADD4 C-1)' $W/ct && cmp -s $HERE/golive_deadman.sh $W/pinned/golive_deadman_*/golive_deadman.sh && [ ! -w $W/pinned/golive_deadman_*/golive_deadman.sh ]"
chk "i2b [VONG3 nit] install tao file danh dau deadman/INSTALLED (monitor phan biet chua cai / chet)" "grep -q '^installed TS=' $W/deploy/deadman/INSTALLED"
OUT=$(echo YES | IO bash "$HERE/install_ops5_oracle.sh" 2>&1); RC=$?
chk "i3 install lan 2: KHONG DOI, khong nhan doi dong" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'KHONG DOI' && [ \$(grep -c 'OPS5' $W/ct) = 2 ]"
OUT=$(echo YES | IO MODE=rollback bash "$HERE/install_ops5_oracle.sh" 2>&1); RC=$?
chk "i4 rollback: go 2 dong OPS5, crontab = ban dau" "[ $RC = 0 ] && cmp -s $W/ct $W/ct0"
chk "i4b [VONG3 nit] rollback xoa deadman/INSTALLED" "[ ! -e $W/deploy/deadman/INSTALLED ]"
OUT=$(IO A1_APPROVED_OPS=$W/khong_co.commit DRY=1 bash "$HERE/install_ops5_oracle.sh" 2>&1); RC=$?
chk "i5 installer: HEAD chua A1 duyet => TU CHOI [m1]" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'TU CHOI \[m1\]'"
chmod -R u+w $W/pinned 2>/dev/null

echo "== OPS5 muc 5: tre gia (monitor + c3_price_lag_day.sh)"
IGD=$W/collectData; mkdir -p $IGD/logs
NOWL=$(date +%s)
{ for i in $(seq 1 10); do g=3300; [ $i -le 6 ] && g=$((5000 + i * 100)); echo "$(D7 $((NOWL - i * 60))) INFO  [ThreadAutoRestartProgram] c.b.c.w.BinanceDataIngestor: [REST-BUDGET] calls=47 weight=85 | price_gap_max_ms=$g price_age_ms=$((i * 700)) price_diff=2 loop_restarts=0"; done
  echo "$(D7 $((NOWL - 7200))) INFO  [x] c.b.c.w.BinanceDataIngestor: [REST-BUDGET] calls=1 | price_gap_max_ms=99999 price_age_ms=99999 price_diff=0"; } | sort > $IGD/logs/full.log
echo "$(D7 $((NOWL - 120))) INFO  [C3LIVE-OPS] c.b.c.o.OpsHooks: [KILLSW] HOURLY hour=x mode=act | lag_s=6 miss=0/517 api=positions" >> "$F/logs/full.log"
api positionRisk '[]'; book '{"clusters":[]}'; api openAlgoOrders '[]'
OUT=$(E DRY=1 ING_LOG=$IGD/logs/full.log bash "$HERE/golive_monitor.sh" 2>&1); RC=$?
chk "t1 monitor: dong tre_gia_1h dem 10 phut 1 h qua (bo dong 2 h truoc), 6 phut gap > 5000, max 5600, lag_s=6" "echo \"\$OUT\" | grep -q '== tre_gia_1h: n=10 gap_gt=6 gap_max_ms=5600 age_gt=3 age_max_ms=7000 nguong_ms=5000 | lag_s=6 miss=0/517'"
chk "t2 monitor: >= 5 phut tre => CANH BAO tre gia (khong KHAN), TOM TAT tre_gia=6/10" "echo \"\$OUT\" | grep -q 'CANH BAO tre gia: 6/10' && echo \"\$OUT\" | grep -q 'TOM TAT: .* tre_gia=6/10' && ! echo \"\$OUT\" | grep -q 'KHAN.*tre'"
OUT=$(E DRY=1 ING_LOG=$IGD/logs/full.log LAG_WARN_N=7 bash "$HERE/golive_monitor.sh" 2>&1); RC=$?
chk "t3 monitor: duoi nguong canh bao (LAG_WARN_N=7) => khong CANH BAO tre gia" "! echo \"\$OUT\" | grep -q 'CANH BAO tre gia' && echo \"\$OUT\" | grep -q 'tre_gia=6/10'"
OUT=$(E DRY=1 ING_LOG=$W/khong_co.log bash "$HERE/golive_monitor.sh" 2>&1); RC=$?
chk "t4 monitor: thieu log ingestor => n=0, khong loi, TOM TAT tre_gia=0/0" "echo \"\$OUT\" | grep -q 'tre_gia_1h: n=0' && echo \"\$OUT\" | grep -q 'tre_gia=0/0'"
# ---- [OPS5_FIX M-4] monitor canh heartbeat deadman
DMH=$W/deploy/deadman/heartbeat; rm -f $DMH $W/deploy/c3_monitor_dm_alert.txt
rm -f $W/deploy/deadman/INSTALLED
OUT=$(E DRY=1 ING_LOG=$IGD/logs/full.log bash "$HERE/golive_monitor.sh" 2>&1); RC=$?
chk "d0 [VONG3 nit] deadman CHUA cai (khong heartbeat, khong INSTALLED) => INFO, KHONG CANH BAO, deadman=CHUA_CAI" "echo \"\$OUT\" | grep -q 'INFO deadman CHUA cai' && ! echo \"\$OUT\" | grep -q 'CANH BAO deadman' && echo \"\$OUT\" | grep -q 'deadman=CHUA_CAI'"
mkdir -p $W/deploy/deadman; echo 'installed TS=t' > $W/deploy/deadman/INSTALLED
OUT=$(E DRY=1 ING_LOG=$IGD/logs/full.log bash "$HERE/golive_monitor.sh" 2>&1); RC=$?
chk "d1 [M-4] monitor tay: KHONG co heartbeat deadman => CANH BAO (khong KHAN), TOM TAT deadman=KHONG_CO, khong Telegram (tay)" "echo \"\$OUT\" | grep -q 'CANH BAO deadman: heartbeat deadman $DMH KHONG CO' && echo \"\$OUT\" | grep -q 'TOM TAT: .* tre_gia=6/10 deadman=KHONG_CO' && ! echo \"\$OUT\" | grep -q 'KHAN.*deadman' && ! grep -qs 'deadman' $W/tg.txt"
mkdir -p $W/deploy/deadman; printf 'ts=%s rc=0\n' $(( $(date +%s) - 30 )) > $DMH
OUT=$(E DRY=1 ING_LOG=$IGD/logs/full.log bash "$HERE/golive_monitor.sh" 2>&1); RC=$?
chk "d2 [M-4] heartbeat deadman 30 s => OK, deadman=OK" "echo \"\$OUT\" | grep -q 'OK deadman heartbeat tuoi [0-9]*s' && echo \"\$OUT\" | grep -q 'deadman=OK'"
printf 'ts=%s rc=0\n' $(( $(date +%s) - 700 )) > $DMH
OUT=$(E DRY=1 ING_LOG=$IGD/logs/full.log bash "$HERE/golive_monitor.sh" 2>&1); RC=$?
chk "d3 [M-4] heartbeat deadman 700 s > 600 => CANH BAO 'cu', deadman=CU" "echo \"\$OUT\" | grep -q 'CANH BAO deadman: heartbeat deadman .* cu 70[0-9]s > 600s' && echo \"\$OUT\" | grep -q 'deadman=CU'"
printf 'C3_ACCOUNT=SUB\nKEYS_FILE=%s\nby=test TS=1\ndry_ts=\n' "$W/keys_sub.env" > $W/deploy/golive_monitor.on
MCR() { E DRY=1 ING_LOG=$IGD/logs/full.log MONITOR_CRON=1 MON_CRON_LOG=$W/moncron_dm.log MON_HB_FILE=$W/deploy/run/monitor_heartbeat bash "$HERE/golive_monitor.sh" >/dev/null 2>&1; }
G0=$(grep -c 'CANH BAO (khong KHAN).*heartbeat deadman' $W/tg.txt 2>/dev/null); G0=${G0:-0}
MCR; G1=$(grep -c 'CANH BAO (khong KHAN).*heartbeat deadman' $W/tg.txt 2>/dev/null)
MCR; G2=$(grep -c 'CANH BAO (khong KHAN).*heartbeat deadman' $W/tg.txt 2>/dev/null)
chk "d4 [M-4] cron: deadman cu => Telegram CANH BAO (khong KHAN) 1 lan; luot 2 trong 30' khong gui lai (G0=$G0 G1=$G1 G2=$G2)" "[ \"$G1\" = \$(( $G0 + 1 )) ] && [ \"$G2\" = \"$G1\" ] && grep -q 'CANH BAO deadman da gui < 30' $W/moncron_dm.log"
printf 'ts=%s rc=0\n' $(date +%s) > $DMH; MCR
chk "d5 [M-4] cron: deadman hoi phuc => Telegram DA HOI PHUC 1 lan, xoa state" "grep -q 'DA HOI PHUC deadman Oracle' $W/tg.txt && [ ! -e $W/deploy/c3_monitor_dm_alert.txt ]"
rm -f $W/deploy/golive_monitor.on
chk "d6 [M-4] duong heartbeat khop: deadman ghi \$DM_DIR/heartbeat (mac dinh \$LOGDIR/deadman) = monitor doc \$LOGDIR/deadman/heartbeat" "grep -q 'DM_DIR=\${DM_DIR:-\$LOGDIR/deadman}' $HERE/golive_deadman.sh && grep -q '\"\$DM_DIR/heartbeat\"' $HERE/golive_deadman.sh && grep -q 'DM_HB_FILE=\${DM_HB_FILE:-\$LOGDIR/deadman/heartbeat}' $HERE/golive_monitor.sh"
DD=$(TZ=Asia/Ho_Chi_Minh date -d @$((NOWL - 60)) +%F)
OUT=$(env SSH_242="bash -c" APP_DIR=$F ING_DIR=$IGD bash "$HERE/c3_price_lag_day.sh" "$DD" 2>&1); RC=$?
chk "t5 c3_price_lag_day: dem ngay (n, gap_gt, p50, max, lag_s) + ket luan %" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'collectData: n=.* gap_gt=[67] ' && echo \"\$OUT\" | grep -q 'lag_s_max=6' && echo \"\$OUT\" | grep -q 'KET LUAN: [67]/'"
OUT=$(env SSH_242="bash -c" APP_DIR=$F ING_DIR=$IGD bash "$HERE/c3_price_lag_day.sh" 2001-01-01 2>&1); RC=$?
chk "t6 c3_price_lag_day: ngay khong co du lieu => KHONG DO DUOC" "echo \"\$OUT\" | grep -q 'KET LUAN: KHONG DO DUOC'"

echo "== OPS5 muc 3: golive_check_lev.sh"
python3 -c "
import json; s=[{'symbol':'S%02dUSDT'%i,'status':'TRADING','quoteAsset':'USDT','contractType':'PERPETUAL'} for i in range(40)]
s.append({'symbol':'XBTUSD_PERP','status':'TRADING','quoteAsset':'USD','contractType':'PERPETUAL'}); s.append({'symbol':'DEADUSDT','status':'SETTLING','quoteAsset':'USDT','contractType':'PERPETUAL'})
json.dump({'symbols':s}, open('$F/run/c3live_exchangeInfo.json','w'))
json.dump([{'symbol':'S%02dUSDT'%i,'marginType':'CROSSED','isAutoAddMargin':'false','leverage':1,'maxNotionalValue':'25000'} for i in range(40)]+[{'symbol':'DEADUSDT','marginType':'ISOLATED','leverage':1,'maxNotionalValue':'1'}], open('$W/api/symbolConfig.json','w'))"
: > $W/api/calls.log
OUT=$(E DRY=1 bash "$HERE/golive_check_lev.sh" 2>&1); RC=$?
chk "l1 DRY=1: doc C3_CAPITAL process, KHONG goi san" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'DRY PASS' && [ ! -s $W/api/calls.log ]"
OUT=$(E bash "$HERE/golive_check_lev.sh" 2>&1); RC=$?
chk "l2 universe 40 (loc TRADING/USDT/PERPETUAL tu exchangeInfo), tat ca 1x CROSSED maxNotional 25000 => DAT rc 0, in W_USED_1M, chi goi account + symbolConfig" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'universe=40 exchangeInfo' && echo \"\$OUT\" | grep -q 'symbol lech: 0/40' && echo \"\$OUT\" | grep -q 'X-MBX-USED-WEIGHT-1M cuoi=77' && [ \"\$(sort -u $W/api/calls.log | tr '\n' ' ')\" = 'account symbolConfig ' ] && ls $W/deploy/lev_check/LEV_CHECK_SUB_*.txt >/dev/null && nosec \"\$OUT\""
python3 -c "
import json; c=json.load(open('$W/api/symbolConfig.json')); c[0]['leverage']=20; c[1]['marginType']='ISOLATED'; c[2]['maxNotionalValue']='50'; json.dump(c, open('$W/api/symbolConfig.json','w'))"
OUT=$(E bash "$HERE/golive_check_lev.sh" 2>&1); RC=$?
chk "l3 [M-2] tiem loi: 1 symbol leverage 20x (jar can ==1), 1 ISOLATED, 1 maxNotional 50 < 90 => CANH_BAO rc 3, liet ke dung 3 symbol" "[ $RC = 3 ] && echo \"\$OUT\" | grep -q 'symbol lech: 3/40 (leverage != 1: 1, marginType khac 1, maxNotional thap 1)' && echo \"\$OUT\" | grep -q 'S00USDT:lev=20!=1' && echo \"\$OUT\" | grep -q 'S01USDT:margin=ISOLATED' && echo \"\$OUT\" | grep -q 'S02USDT:maxNotional=50<90'"
api account '{"totalMarginBalance":"300.00","availableBalance":"300.00","assets":[]}'
OUT=$(E bash "$HERE/golive_check_lev.sh" 2>&1); RC=$?
chk "l4 [M-2] tmb 300 < von x 0,6 KHONG doi nguong: van == 1 (symbol 20x lech, khong co nguong 'leverage >= N')" "[ $RC = 3 ] && echo \"\$OUT\" | grep -q 'leverage == 1 ' && echo \"\$OUT\" | grep -q 'leverage != 1: 1,' && ! echo \"\$OUT\" | grep -q 'leverage >='"
python3 -c "
import json; c=json.load(open('$W/api/symbolConfig.json')); c[0]['leverage']=0; c[3]['leverage']=2; json.dump(c, open('$W/api/symbolConfig.json','w'))"
OUT=$(E bash "$HERE/golive_check_lev.sh" 2>&1); RC=$?
chk "l4b [M-2] leverage 0 va 2 deu != 1 => lech (2 symbol lev)" "[ $RC = 3 ] && echo \"\$OUT\" | grep -q 'leverage != 1: 2,' && echo \"\$OUT\" | grep -q 'S00USDT:lev=0!=1' && echo \"\$OUT\" | grep -q 'S03USDT:lev=2!=1'"
api account '{"totalMarginBalance":"1000.00","availableBalance":"990.00","assets":[{"asset":"USDT","walletBalance":"1000.00","marginBalance":"1000.00","marginAvailable":true}]}'
echo 400 > $W/api/symbolConfig.code
OUT=$(E bash "$HERE/golive_check_lev.sh" 2>&1); RC=$?
chk "l5 san loi symbolConfig HTTP 400 => DUNG rc 1" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'doc san loi'"
rm -f $W/api/symbolConfig.code

echo "== OPS5 muc 4: c3_autodrain_prestart.sh + install_242_autodrain.sh"
SB=$W/sbin; mkdir -p $SB $W/systemd
printf '#!/bin/bash\necho "deps ok (gia)"\nexit $(cat %s/pre_rc 2>/dev/null || echo 0)\n' "$W" > $SB/h242-prestart.sh; chmod 755 $SB/h242-prestart.sh
printf '#!/bin/bash\nPRESTART=${WD_PRESTART:-/usr/local/sbin/h242-prestart.sh}\n' > $SB/h242_watchdog.sh
printf '#!/bin/bash\ncase "$1" in -l) cat %s/ct242 2>/dev/null;; -) cat > %s/ct242;; esac\n' "$W" "$W" > $W/ct242.sh
printf '*/2 * * * * %s/h242_watchdog.sh >> /var/lib/h242_watchdog/cron.out 2>&1\n3,18,41,48 * * * * cd /x && bash exinfo.sh # C3LIVE_EXINFO\n' "$SB" > $W/ct242; cp $W/ct242 $W/ct242_0
AI() { E AD_SBIN=$SB AD_SYSTEMD_DIR=$W/systemd AD_SYSTEMCTL=true AD_CT242="bash $W/ct242.sh" "$@"; }
OUT=$(AI DRY=1 bash "$HERE/install_242_autodrain.sh" 2>&1 < /dev/null); RC=$?
chk "a1 install DRY=1: doc 242, in ke hoach, KHONG doi cron / sbin / systemd" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'DRY PASS' && cmp -s $W/ct242 $W/ct242_0 && [ ! -e $SB/h242-prestart-c3.sh ] && [ ! -e $W/systemd/h242-trading.service.d ]"
OUT=$(echo YES | AI bash "$HERE/install_242_autodrain.sh" 2>&1); RC=$?
DF=$W/systemd/h242-trading.service.d/c3-autodrain.conf
chk "a2 install: wrapper = c3_autodrain_prestart.sh (755), cron watchdog co WD_PRESTART, dong cron khac giu nguyen, drop-in ExecStartPre=wrapper" "[ $RC = 0 ] && cmp -s $HERE/c3_autodrain_prestart.sh $SB/h242-prestart-c3.sh && [ -x $SB/h242-prestart-c3.sh ] && grep -qx \"\*/2 \* \* \* \* WD_PRESTART=$SB/h242-prestart-c3.sh $SB/h242_watchdog.sh >> /var/lib/h242_watchdog/cron.out 2>&1\" $W/ct242 && grep -q 'C3LIVE_EXINFO' $W/ct242 && grep -qx 'ExecStartPre=' $DF && grep -qx \"ExecStartPre=$SB/h242-prestart-c3.sh $F com.binance.chuyennd.trading.BinanceOrderTradingManager\" $DF && grep -q 'XONG: autodrain da cai' <<<\"\$OUT\""
OUT=$(echo YES | AI bash "$HERE/install_242_autodrain.sh" 2>&1); RC=$?
chk "a3 install lan 2 => KHONG DOI" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'KHONG DOI (da cai dung'"
AW() { env AD_ORIG_PRESTART=$SB/h242-prestart.sh AD_STATE_DIR=$W/adstate AD_TG_SINK=$W/tgad.txt "$@"; }
rm -f $F/run/KILL_SWITCH; WP=$(grep -o 'WD_PRESTART=[^ ]*' $W/ct242 | cut -d= -f2)
OUT=$(AW bash "$WP" "$F" com.binance.chuyennd.trading.BinanceOrderTradingManager 2>&1); RC=$?
chk "a4 watchdog goi WD_PRESTART (tu dong cron da cai), env.sh live, chua co KS => tao run/KILL_SWITCH token c3_autodrain + Telegram, rc 0" "[ $RC = 0 ] && grep -q '^c3_autodrain [0-9_]* caller=' $F/run/KILL_SWITCH && grep -q '\[242-AUTODRAIN\] bot c3 LIVE khoi dong lai NGOAI quy trinh.*DA DAT run/KILL_SWITCH.*golive_boot_undrain.sh' $W/tgad.txt"
echo 'golive_live_off drain 20261119_000000' > $F/run/KILL_SWITCH
OUT=$(AW bash "$WP" "$F" x 2>&1); RC=$?
chk "a5 [OPS6 T20] KS da co (drain cua owner) => dong owner GIU NGUYEN (dong 1), THEM dong token c3_autodrain (>>), bao 'DA THEM'" "[ $RC = 0 ] && [ \"\$(head -1 $F/run/KILL_SWITCH)\" = 'golive_live_off drain 20261119_000000' ] && [ \$(grep -c '' $F/run/KILL_SWITCH) = 2 ] && tail -1 $F/run/KILL_SWITCH | grep -qE '^c3_autodrain [0-9]{8}_[0-9]{6} caller=' && tail -2 $W/tgad.txt | grep -q 'DA THEM dong c3_autodrain'"
OUT=$(AW bash "$WP" "$F" x 2>&1); RC=$?
chk "a5b [OPS6 T20] chay lai (da co dong c3_autodrain) => KHONG them dong thu 3, bao 'DA CO dong c3_autodrain'" "[ $RC = 0 ] && [ \$(grep -c '' $F/run/KILL_SWITCH) = 2 ] && tail -2 $W/tgad.txt | grep -q 'DA CO dong c3_autodrain'"
printf 'golive_live_off drain 20261119_000009' > $F/run/KILL_SWITCH
OUT=$(AW bash "$WP" "$F" x 2>&1); RC=$?
chk "a5c [OPS6 T20] KS dong cuoi THIEU xuong dong => token c3_autodrain thanh dong RIENG (khong dinh vao dong owner)" "[ $RC = 0 ] && grep -qx 'golive_live_off drain 20261119_000009' $F/run/KILL_SWITCH && grep -qxE 'c3_autodrain [0-9]{8}_[0-9]{6} caller=[A-Za-z0-9_.-]*' $F/run/KILL_SWITCH"
rm -f $F/run/KILL_SWITCH; echo 1 > $W/pre_rc
OUT=$(AW bash "$WP" "$F" x 2>&1); RC=$?
chk "a6 prestart goc rc 1 (deps chua san) => tra rc 1, KHONG tao KS" "[ $RC = 1 ] && [ ! -e $F/run/KILL_SWITCH ]"
echo 0 > $W/pre_rc; sed -i 's/^export LIVE_ADAPTER=live/export LIVE_ADAPTER=dry/' $F/conf/env.sh
OUT=$(AW bash "$WP" "$F" x 2>&1); RC=$?
chk "a7 env.sh adapter=dry => khong drain, rc 0" "[ $RC = 0 ] && [ ! -e $F/run/KILL_SWITCH ] && echo \"\$OUT\" | grep -q 'khong live'"
sed -i 's/^export LIVE_ADAPTER=dry/export LIVE_ADAPTER=live/' $F/conf/env.sh; chmod 555 $F/run
OUT=$(AW bash "$WP" "$F" x 2>&1); RC=$?; chmod 755 $F/run
chk "a8 tiem loi: KHONG ghi duoc KS (run chi doc) => van rc 0 (khong chan start, vi the can quan ly) + Telegram KHAN" "[ $RC = 0 ] && [ ! -e $F/run/KILL_SWITCH ] && tail -2 $W/tgad.txt | grep -q 'KHAN bot c3 LIVE.*KHONG dat duoc'"
chk "a9 golive_live_off MODE=undrain go MOI token KILL_SWITCH (mv run/KILL_SWITCH) => mo lai duoc sau autodrain" "grep -q 'mv -f run/KILL_SWITCH run/KILL_SWITCH.off_' $HERE/golive_live_off.sh"
OUT=$(echo YES | AI MODE=rollback bash "$HERE/install_242_autodrain.sh" 2>&1); RC=$?
chk "a10 rollback: cron watchdog = ban dau, drop-in xoa, wrapper -> .off_" "[ $RC = 0 ] && cmp -s $W/ct242 $W/ct242_0 && [ ! -e $DF ] && [ ! -e $SB/h242-prestart-c3.sh ] && ls $SB/h242-prestart-c3.sh.off_* >/dev/null"
printf '*/2 * * * * %s/h242_watchdog.sh\n*/2 * * * * %s/h242_watchdog.sh --x\n' "$SB" "$SB" > $W/ct242
OUT=$(AI DRY=1 bash "$HERE/install_242_autodrain.sh" 2>&1 < /dev/null); RC=$?
chk "a11 cron co 2 dong watchdog => TU CHOI" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'khong dung 1 dong'"
cp $W/ct242_0 $W/ct242; printf '#!/bin/bash\nPRESTART=/usr/local/sbin/h242-prestart.sh\n' > $SB/h242_watchdog.sh
OUT=$(AI DRY=1 bash "$HERE/install_242_autodrain.sh" 2>&1 < /dev/null); RC=$?
chk "a12 watchdog khong ho tro WD_PRESTART => TU CHOI" "[ $RC = 1 ] && echo \"\$OUT\" | grep -q 'KHONG ho tro WD_PRESTART'"
chk "a13 khong lo key/secret (autodrain)" "nosec \"\$OUT\" && ! grep -q \"$SKEY\" $W/tgad.txt"

# ---- [OPS5_FIX A-1] wrapper KHONG BAO GIO tra rc != 0 (tru prestart goc chay duoc va tu tra rc != 0) ----
AWX() { env AD_STATE_DIR=$W/adstate AD_TG_SINK=$W/tgad.txt "$@"; }
rm -f $F/run/KILL_SWITCH
OUT=$(AWX AD_ORIG_PRESTART=$SB/khong_co.sh bash "$HERE/c3_autodrain_prestart.sh" "$F" x 2>&1); RC=$?
chk "a14 [A-1] prestart goc MAT => rc 0, VAN drain (KS dat), Telegram KHAN 'MAT'" "[ $RC = 0 ] && [ -e $F/run/KILL_SWITCH ] && tail -2 $W/tgad.txt | grep -q 'KHAN.*MAT/khong co quyen x'"
rm -f $F/run/KILL_SWITCH; chmod 644 $SB/h242-prestart.sh
OUT=$(AWX AD_ORIG_PRESTART=$SB/h242-prestart.sh bash "$HERE/c3_autodrain_prestart.sh" "$F" x 2>&1); RC=$?; chmod 755 $SB/h242-prestart.sh
chk "a15 [A-1] prestart goc mat quyen x => rc 0 + KS + KHAN" "[ $RC = 0 ] && [ -e $F/run/KILL_SWITCH ] && tail -2 $W/tgad.txt | grep -q KHAN"
rm -f $F/run/KILL_SWITCH; printf '#!/khong/co/interp\nexit 0\n' > $SB/badshebang.sh; chmod 755 $SB/badshebang.sh
OUT=$(AWX AD_ORIG_PRESTART=$SB/badshebang.sh bash "$HERE/c3_autodrain_prestart.sh" "$F" x 2>&1); RC=$?
chk "a16 [A-1] prestart goc shebang hong (exec rc 126/127) => rc 0 + KS + KHAN 'KHONG exec duoc'" "[ $RC = 0 ] && [ -e $F/run/KILL_SWITCH ] && tail -2 $W/tgad.txt | grep -q 'KHONG exec duoc'"
rm -f $F/run/KILL_SWITCH; mkdir -p $W/adfull; ln -sf /dev/full $W/adfull/autodrain.log; ln -sf /dev/full $W/adfull/ALERT_PENDING.txt
OUT=$(env AD_ORIG_PRESTART=$SB/h242-prestart.sh AD_STATE_DIR=$W/adfull AD_TG_SINK=/dev/full bash "$HERE/c3_autodrain_prestart.sh" "$F" x 2>/dev/full >/dev/full); RC=$?
chk "a17 [A-1] het dia (log/Telegram sink/stdout/stderr = /dev/full ENOSPC) => rc 0, KS van dat" "[ $RC = 0 ] && [ -e $F/run/KILL_SWITCH ]"
rm -f $F/run/KILL_SWITCH
OUT=$(env -i PATH=/usr/bin:/bin AD_ORIG_PRESTART= AD_STATE_DIR= AD_TG_ENV= AD_TG_SINK=$W/tgad.txt bash "$HERE/c3_autodrain_prestart.sh" 2>&1); RC=$?
chk "a18 [A-1] env -i + moi bien rong + khong tham so (APP mac dinh, goc mac dinh khong co tren Oracle) => rc 0" "[ $RC = 0 ]"
OUT=$(AWX AD_ORIG_PRESTART=$SB/h242-prestart.sh bash "$HERE/c3_autodrain_prestart.sh" "$W/khong_co_app" x 2>&1); RC=$?
chk "a19 [A-1] APP khong ton tai (env.sh/run mat) => rc 0" "[ $RC = 0 ]"
a20chk() { ! grep -qE '^[^#]*(set -[a-z]*[eu]|pipefail)' "$1" && grep -q '^trap .exit \$_RC. EXIT$' "$1" && bash -n "$1"; }
chk "a20 [A-1] wrapper khong con set -e/-u/pipefail (ngoai comment); co trap EXIT ep rc; bash -n OK" "a20chk $HERE/c3_autodrain_prestart.sh"
# ---- watchdog THAT (ban sao ops/h242_watchdog.sh) + wrapper, tung nhanh loi => bot VAN start (tru goc rc 1) ----
WDC=$W/wd_real.sh; cp "$HERE/../h242_watchdog.sh" $WDC
MCN=com.o5f_$$.Main; WF=$W/wdapp; mkdir -p $WF/conf $WF/run $WF/bin; printf 'export LIVE_ADAPTER=live\n' > $WF/conf/env.sh
printf '#!/bin/bash\ncd %s; nohup bash -c "sleep 300; : o5f_wdjava_%s" %s >/dev/null 2>&1 &\n' "$WF" "$$" "$MCN" > $WF/bin/start.sh; chmod 755 $WF/bin/start.sh
wdk() { local p; for p in $(pgrep -f -- "o5f_wdjava_$$" 2>/dev/null); do pkill -P "$p" 2>/dev/null; kill "$p" 2>/dev/null; done; sleep 0.5; rm -f $WF/run/KILL_SWITCH $W/wd/state; }
WDRUN() {   # $1 = goc, $2 = STATE dir, $3 = sink
  cat > $SB/wr_o5f.sh <<EOW
#!/bin/bash
AD_ORIG_PRESTART=$1 AD_STATE_DIR=$2 AD_TG_SINK=$3 exec bash $HERE/c3_autodrain_prestart.sh "\$@"
EOW
  chmod 755 $SB/wr_o5f.sh
  env -i PATH=/usr/bin:/bin HOME=$W WD_APP=$WF WD_MAIN_CLASS=$MCN WD_STATE_DIR=$W/wd WD_TG_ENV=$W/khong_co WD_START_CMD="bash $WF/bin/start.sh" WD_START_WAIT_SEC=4 WD_START_BACKOFF_SEC=0 WD_PRESTART=$SB/wr_o5f.sh bash $WDC >/dev/null 2>&1
  sleep 1; pgrep -fc -- "o5f_wdjava_$$" 2>/dev/null || true
}
wdk; NP=$(WDRUN $SB/khong_co.sh $W/adstate $W/tgad.txt)
chk "a21 [A-1] watchdog THAT + goc MAT => bot START (NP=$NP) + KS dat" "[ ${NP:-0} -ge 1 ] && [ -e $WF/run/KILL_SWITCH ]"
wdk; chmod 644 $SB/h242-prestart.sh; NP=$(WDRUN $SB/h242-prestart.sh $W/adstate $W/tgad.txt); chmod 755 $SB/h242-prestart.sh
chk "a22 [A-1] watchdog THAT + goc mat quyen x => START (NP=$NP)" "[ ${NP:-0} -ge 1 ]"
wdk; NP=$(WDRUN $SB/badshebang.sh $W/adstate $W/tgad.txt)
chk "a23 [A-1] watchdog THAT + goc shebang hong => START (NP=$NP)" "[ ${NP:-0} -ge 1 ]"
wdk; NP=$(WDRUN $SB/h242-prestart.sh $W/adfull /dev/full)
chk "a24 [A-1] watchdog THAT + het dia (log/sink ENOSPC) => START (NP=$NP) + KS" "[ ${NP:-0} -ge 1 ] && [ -e $WF/run/KILL_SWITCH ]"
wdk; chmod 555 $WF/run; NP=$(WDRUN $SB/h242-prestart.sh /proc/khong_ghi $W/tgad.txt); chmod 755 $WF/run
chk "a25 [A-1] watchdog THAT + run/ chi doc + STATE khong ghi => START (NP=$NP)" "[ ${NP:-0} -ge 1 ]"
wdk; NP=$(WDRUN "" "" $W/tgad.txt)
chk "a26 [A-1] watchdog THAT + bien rong (goc mac dinh khong co) => START (NP=$NP)" "[ ${NP:-0} -ge 1 ]"
wdk; echo 1 > $W/pre_rc; NP=$(WDRUN $SB/h242-prestart.sh $W/adstate $W/tgad.txt); echo 0 > $W/pre_rc
chk "a27 [A-1] watchdog THAT + goc chay duoc TRA rc 1 (deps) => KHONG start (giong truoc OPS5, NP=$NP)" "[ ${NP:-0} = 0 ] && grep -q 'PRESTART rc=1 - KHONG start' $W/wd/watchdog.log"
wdk; rm -rf $W/adfull

echo "== OPS5 muc 2b: c3_oracle_seen_242.sh + install_242_oracle_seen.sh"
OSL=$W/secure; NS=$(date +%s)
printf '%s sshd[1]: Accepted publickey for root from 161.118.212.3 port 1 ssh2: RSA SHA256:x\n%s sshd[2]: Accepted publickey for root from 1.2.3.4 port 1 ssh2\n' "$(date -d @$((NS - 3000)) '+%b %e %H:%M:%S')" "$(date -d @$((NS - 10)) '+%b %e %H:%M:%S')" > $OSL
OS() { env OS_AUTHLOG=$OSL OS_STATE_DIR=$W/osstate OS_TG_SINK=$W/tgos.txt "$@"; }
OUT=$(OS bash "$HERE/c3_oracle_seen_242.sh" 2>&1); RC=$?
chk "o1 tiem loi: lan cham cuoi cua Oracle 50' truoc (IP khac moi hon khong tinh) => CANH BAO + Telegram, rc 2" "[ $RC = 2 ] && grep -q 'ORACLE-SEEN\] CANH BAO: Oracle (161.118.212.3) KHONG cham 242' $W/tgos.txt"
OUT=$(OS bash "$HERE/c3_oracle_seen_242.sh" 2>&1); RC=$?
chk "o2 chong spam: lan 2 < 30' khong gui lai" "[ $RC = 2 ] && [ \$(grep -c 'CANH BAO' $W/tgos.txt) = 1 ]"
printf '%s sshd[3]: Accepted publickey for root from 161.118.212.3 port 2 ssh2\n' "$(date -d @$((NS - 60)) '+%b %e %H:%M:%S')" >> $OSL
OUT=$(OS bash "$HERE/c3_oracle_seen_242.sh" 2>&1); RC=$?
chk "o3 Oracle cham lai (60 s) => DA HOI PHUC 1 lan, rc 0" "[ $RC = 0 ] && [ \$(grep -c 'DA HOI PHUC' $W/tgos.txt) = 1 ]"
OUT=$(OS bash "$HERE/c3_oracle_seen_242.sh" 2>&1); RC=$?
chk "o4 OK tiep => khong tin moi" "[ $RC = 0 ] && [ \$(grep -c '^----' $W/tgos.txt) = 2 ]"
: > $OSL
OUT=$(OS bash "$HERE/c3_oracle_seen_242.sh" 2>&1); RC1=$?; OUT=$(OS OS_NOW=$((NS + 1000)) bash "$HERE/c3_oracle_seen_242.sh" 2>&1); RC=$?
chk "o5 log vua xoay (0 dong): luot dau OK (bat dau dem), sau > 15' khong thay => CANH BAO" "[ $RC1 = 0 ] && [ $RC = 2 ] && tail -2 $W/tgos.txt | grep -q 'khong thay dong ssh nao'"
printf '0 * * * * echo giu\n' > $W/ct242; cp $W/ct242 $W/ct242_os0; rm -f $SB/c3_oracle_seen.sh
OI() { E AD_SBIN=$SB AD_CT242="bash $W/ct242.sh" "$@"; }
OUT=$(OI DRY=1 bash "$HERE/install_242_oracle_seen.sh" 2>&1 < /dev/null); RC=$?
chk "o6 install DRY: KHONG doi" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'DRY PASS' && cmp -s $W/ct242 $W/ct242_os0 && [ ! -e $SB/c3_oracle_seen.sh ]"
OUT=$(echo YES | OI bash "$HERE/install_242_oracle_seen.sh" 2>&1); RC=$?
chk "o7 install: script = c3_oracle_seen_242.sh, 1 dong cron */5 co tag, dong cu giu" "[ $RC = 0 ] && cmp -s $HERE/c3_oracle_seen_242.sh $SB/c3_oracle_seen.sh && grep -qx \"\*/5 \* \* \* \* $SB/c3_oracle_seen.sh >/dev/null 2>&1 # C3_ORACLE_SEEN (OPS5 2b)\" $W/ct242 && grep -q 'echo giu' $W/ct242"
OUT=$(echo YES | OI bash "$HERE/install_242_oracle_seen.sh" 2>&1); RC=$?
chk "o8 install lan 2 => KHONG DOI" "[ $RC = 0 ] && echo \"\$OUT\" | grep -q 'KHONG DOI (da cai)'"
OUT=$(echo YES | OI MODE=rollback bash "$HERE/install_242_oracle_seen.sh" 2>&1); RC=$?
chk "o9 rollback: crontab = ban dau, script -> .off_" "[ $RC = 0 ] && cmp -s $W/ct242 $W/ct242_os0 && [ ! -e $SB/c3_oracle_seen.sh ]"

echo "== OPS5 muc 6: MINOR n1d (ten prereg ngoai mau) + n3c (limits lon) - helper GIONG trong make_gate + micro_on"
PRG5=$W/prereg5; mkdir -p $PRG5/docs/prereg/sub; git -C $PRG5 init -q
pc() { git -C $PRG5 -c user.name=t -c user.email=t@t add -A && git -C $PRG5 -c user.name=t -c user.email=t@t commit -qm x; }
echo a > $PRG5/docs/prereg/PREREG_PARITY_V12_DRY_ADDENDUM22_GRID.md; echo b > $PRG5/docs/prereg/PREREG_E2E_REPLAY_V12_ERRATA1.md; echo c > $PRG5/docs/prereg/PREREG_PARITY_V12_DRY_ADD9.md
python3 -c "print('x' * 300000); print('PREREG_E2E_REPLAY_V12_ERRATA1.md')" > $PRG5/docs/prereg/GATE_LIMITS_MICRO.md; pc
for S in golive_make_gate.sh golive_micro_on.sh; do
  R6=$( PREREG_REPO=$PRG5; GM_LF=docs/prereg/GATE_LIMITS_MICRO.md
    eval "$(grep -E '^gm_(list|pnum|addmax)\(\)' $HERE/$S)"; eval "$(sed -n '/^gm_odd()/,/done; }$/p' $HERE/$S)"; eval "$(sed -n '/^gm_errata_miss()/,/done; }/p' $HERE/$S)"
    eval "$(sed -n '/^gm_set()/,/LC_ALL=C sort; }$/p' $HERE/$S)"
    o0=$(gm_odd HEAD); e0=$(gm_errata_miss HEAD "$(gm_set HEAD)")
    for n in PREREG_PARITY_V12_DRY_ADDENDUM_23.md prereg_parity_v12_dry_add24.md PREREG_PARITY_V12_DRY_ADDENDUM23.MD sub/PREREG_PARITY_V12_DRY_ADDENDUM23.md prereg_e2e_replay_v12_errata4.md; do
      mkdir -p "$(dirname "$PRG5/docs/prereg/$n")"; echo z > "$PRG5/docs/prereg/$n"; pc; o=$(gm_odd HEAD); echo "$o" | grep -qF "$n" && printf 'odd_ok ' || printf 'ODD_MISS:%s ' "$n"; git -C $PRG5 rm -q "docs/prereg/$n"; pc; done
    echo z > $PRG5/docs/prereg/PREREG_PARITY_V12_DRY_ADDENDUM23_X.md; pc; o1=$(gm_odd HEAD); git -C $PRG5 rm -q docs/prereg/PREREG_PARITY_V12_DRY_ADDENDUM23_X.md; pc
    echo "o0=[$o0] e0=[$e0] o1=[$o1]" )
  chk "n1d/n3c ($S): repo dung mau => gm_odd rong; limits 300 KB co ERRATA1 => KHONG tu choi oan (n3c); 5 ten ngoai mau (_ADDENDUM_23, chu thuong, .MD, thu muc con, errata chu thuong) => bi nhan dien; ADDENDUM23_X dung mau => khong" "[ \"\$(echo '$R6' | grep -o 'odd_ok' | wc -l)\" = 5 ] && echo '$R6' | grep -q 'o0=\[\] e0=\[\] o1=\[\]'"
done

echo "== OPS5_FIX muc 8: reanchor nhan cu/moi + micro_on/pilot_on chap nhan KILL_SWITCH c3live_boot/c3_autodrain"
RA=$W/rapp; mkdir -p $RA/logs $RA/run
RAN() { printf '%s\n' "$(D7 $((NOW - 100))) INFO  [main] c.b.c.u.Utils: MainClass: com.binance.chuyennd.trading.BinanceOrderTradingManager APPDir: ./run" "$(D7 $((NOW - 90))) INFO  [main] x: [C3-LIVE] khoi dong adapter=LIVE c3_capital=1000.0 $1 killSwitchArmed=true" > $RA/logs/full.log
  echo YES | env SSH_242="bash -c" APP_DIR=$RA DRY=0 bash "$HERE/c3live_reanchor.sh" 2>&1; }
OUT=$(RAN 'tai_khoan=CHINH(pham vi c3)'); RC=$?
chk "r1 [8a] jar cu 'tai_khoan=CHINH(pham vi c3)' => TU CHOI rc 4, khong ghi req" "[ $RC = 4 ] && echo \"\$OUT\" | grep -q 'TU CHOI' && [ ! -f $RA/run/c3live_reanchor.req ]"
OUT=$(RAN 'tai_khoan=SUB key_file=keys_sub.env key_sha8=1234abcd recon=QTY(pham vi c3)'); RC=$?
chk "r2 [8a] jar moi (W3A muc 2) 'recon=QTY(pham vi c3)' => TU CHOI rc 4" "[ $RC = 4 ] && echo \"\$OUT\" | grep -q 'TU CHOI' && [ ! -f $RA/run/c3live_reanchor.req ]"
OUT=$(RAN 'tai_khoan=DRY(khong dung key) recon=QTY(pham vi c3)'); RC=$?
chk "r3 [8a] jar moi che do DRY cung in recon=QTY => TU CHOI (cung ngu nghia jar cu)" "[ $RC = 4 ]"
OUT=$(RAN 'equity_mode=X'); RC=$?
chk "r4 [8a] khong co nhan QTY (che do equity cu) => KHONG tu choi (ghi req)" "[ $RC != 4 ] && [ -f $RA/run/c3live_reanchor.req ]"
KST() { [ -n "$1" ] && printf '%s\n' "$1" > $F/run/KILL_SWITCH || rm -f $F/run/KILL_SWITCH; E bash -c ". $HERE/golive_lib.sh >/dev/null 2>&1; ST=\$(gl_state242); printf 'TOK=%s ' \"\$(sv KILLSW_TOK)\"; gl_ks_boot_ok && echo CHAP_NHAN || echo TU_CHOI"; }
R8=""; for t in "" "c3live_boot 20261119_101500" "c3_autodrain 20261119_101500 caller=h242_watchdog.sh" "golive_live_off drain 20261119_1" "golive_monitor KHAN x" "nguoi dat tay"; do R8="$R8[$(KST "$t")]"; done
chk "k1 [8b] gl_state242 KILLSW_TOK + gl_ks_boot_ok: khong co / c3live_boot / c3_autodrain => CHAP_NHAN; drain owner / monitor / tay => TU_CHOI ($R8)" "[ \"$R8\" = '[TOK= CHAP_NHAN][TOK=c3live_boot CHAP_NHAN][TOK=c3_autodrain CHAP_NHAN][TOK= TU_CHOI][TOK= TU_CHOI][TOK= TU_CHOI]' ]"
chk "k2 [8b] precheck micro_on + pilot_on dung gl_ks_boot_ok (khong con '[ KILLSW_FILE = 0 ]' tran)" "grep -q '^chk \"khong co run/KILL_SWITCH, hoac token c3live_boot/c3_autodrain.*\" \"gl_ks_boot_ok\"' $HERE/golive_micro_on.sh && grep -q '^chk \"khong co run/KILL_SWITCH, hoac token c3live_boot/c3_autodrain.*\" \"gl_ks_boot_ok\"' $HERE/golive_pilot_on.sh && ! grep -q \"KILLSW_FILE)' = 0 \\]\\\"\" $HERE/golive_micro_on.sh $HERE/golive_pilot_on.sh"
# ---- [VONG3 F1] KILLSW_TOK chat: dung 1 dong + khop tron token chuan; writer APPEND; go KS cua minh chi khi MOI dong la cua minh
JT='c3live_boot 20261119_101500 B-09: JVM LIVE khoi dong KHONG qua script go-live (crash/watchdog/reboot/restart tay) => dung mo moi, vi the c3 van duoc quan ly. Mo: MODE=undrain bash golive_live_off.sh'
R9=""; for t in '#c3live_boot 20261119_101500' 'c3live_bootX 20261119_101500' '"c3live_boot" 20261119_101500' "c3_autodrain 20261119_101500 caller=cron
owner: GIU DRAIN" "c3_autodrain 20261119_101500 caller=x
golive_monitor 20261119_1 KHAN vi_the_ngoai" "$JT" "c3_autodrain 20261119_101500 caller=unknown"; do R9="$R9[$(KST "$t")]"; done
: > $F/run/KILL_SWITCH; R9="$R9[$(E bash -c ". $HERE/golive_lib.sh >/dev/null 2>&1; ST=\$(gl_state242); gl_ks_boot_ok && echo CHAP_NHAN || echo TU_CHOI")]"
printf 'c3live_boot 20261119_101500' > $F/run/KILL_SWITCH; R9="$R9[$(E bash -c ". $HERE/golive_lib.sh >/dev/null 2>&1; ST=\$(gl_state242); gl_ks_boot_ok && echo CHAP_NHAN || echo TU_CHOI")]"
chk "k5 [F1] '#c3live_boot' / 'c3live_bootX' / co ngoac / 2 dong (owner them) / 2 dong (monitor KHAN append) => TU_CHOI; token jar C3BootLock nguyen van + caller=unknown => CHAP_NHAN; file rong => TU_CHOI; 1 dong khong xuong dong => CHAP_NHAN ($R9)" "[ \"$R9\" = '[TOK= TU_CHOI][TOK= TU_CHOI][TOK= TU_CHOI][TOK= TU_CHOI][TOK= TU_CHOI][TOK=c3live_boot CHAP_NHAN][TOK=c3_autodrain CHAP_NHAN][TU_CHOI][CHAP_NHAN]' ]"
chk "k6 [F1] khong con writer 'chi ghi KS khi chua co' (ghi de/nuot KHAN) trong ops/c3live: moi writer APPEND (>>)" "! grep -nE '\[ -e run/KILL_SWITCH \] \|\| (echo|printf)' $HERE/*.sh && grep -q \"echo 'golive_monitor \\\$TS KHAN \\\$KT' >> run/KILL_SWITCH\" $HERE/golive_monitor.sh"
GKO() { E bash -c ". $HERE/golive_lib.sh >/dev/null 2>&1; TS=20990101_000777; gl_ks_go_own golive_micro_on"; }
printf 'golive_micro_on 20990101_000777 hau_kiem\n' > $F/run/KILL_SWITCH; printf 'golive_monitor x KHAN vi_the_ngoai\n' >> $F/run/KILL_SWITCH; G1=$(GKO)
printf 'golive_live_off drain 20990101_1\n' > $F/run/KILL_SWITCH; G2=$(GKO)
printf 'golive_micro_on 20990101_000777 hau_kiem\n' > $F/run/KILL_SWITCH; G3=$(GKO); G4=$(GKO)
chk "k7 [F1] gl_ks_go_own: KS cua minh + dong KHAN monitor => KHAC (GIU); KS owner drain => KHAC; chi cua minh => OK (go, idempotent) ($G1 $G2 $G3 $G4)" "[ '$G1 $G2 $G3 $G4' = 'KHAC KHAC OK OK' ] && [ ! -e $F/run/KILL_SWITCH ] && [ -e $F/run/KILL_SWITCH.ok_20990101_000777 ]"
rm -f $F/run/KILL_SWITCH*

# gl_restart ks=1 THAT (fake daemon.sh) voi KILL_SWITCH c3live_boot co san
cat > $F/bin/daemon.sh <<EOD
#!/bin/bash
case "\$1" in
  stop) [ -e $W/daemon_nostop ] && exit 0; for p in \$(pgrep -f "^BinanceOrderTradingManager fk_$TAG"); do kill \$p 2>/dev/null; done;;
  start) ( cd $F && exec env -i PATH="$PATH" C3_CAPITAL=1000 LIVE_ADAPTER=live nohup bash -c "exec -a '$FPAT' sleep 900" ) >/dev/null 2>&1 </dev/null & ;;
esac
EOD
chmod 755 $F/bin/daemon.sh; cp $F/conf/env.sh $W/env.sh.k8; startbot 1000
GR() { E LOGDIR=$W/deploy WD_PAUSE=$W/PAUSE_k8 WD_PAUSE_MAX_S=3 bash -c ". $HERE/golive_lib.sh >/dev/null 2>&1; GL_NAME=golive_micro_on; TS=\$1; gl_restart '# k8
export O5F_K8=1' '' none 1 2>&1" _ "$1"; }
echo 'c3live_boot 20261119_101500' > $F/run/KILL_SWITCH
OUT=$(GR 20990101_000001); RC=$?
chk "k3 [8b] gl_restart ks=1 + KS c3live_boot => GHI DE token script, ban cu -> run/KILL_SWITCH.prev_<TS>, restart OK" "echo \"\$OUT\" | grep -q 'OK KILL_SWITCH_dat_truoc_start' && grep -q '^golive_micro_on 20990101_000001 ' $F/run/KILL_SWITCH && [ \"\$(cat $F/run/KILL_SWITCH.prev_20990101_000001)\" = 'c3live_boot 20261119_101500' ] && echo \"\$OUT\" | grep -q 'OK started pid='"
cp $W/env.sh.k8 $F/conf/env.sh; startbot 1000; echo 'c3_autodrain 20261119_101500 caller=x' > $F/run/KILL_SWITCH; touch $W/daemon_nostop
OUT=$(GR 20990101_000002); RC=$?; rm -f $W/daemon_nostop
chk "k4 [8b] gl_restart ks=1 FAIL (stop khong dung duoc) => ksoff tra lai token cu c3_autodrain (khong mat drain), env khoi phuc" "echo \"\$OUT\" | grep -q 'FAIL van_con_process_sau_stop' && [ \"\$(cat $F/run/KILL_SWITCH)\" = 'c3_autodrain 20261119_101500 caller=x' ] && [ -e $F/run/KILL_SWITCH.rb_20990101_000002 ] && ! grep -q O5F_K8 $F/conf/env.sh"
cp $W/env.sh.k8 $F/conf/env.sh; startbot 1000; BP=$(pgrep -f "^$FPAT" | head -1); printf 'golive_live_off drain 20990101_1\n' > $F/run/KILL_SWITCH; cp $F/run/KILL_SWITCH $W/ks_owner
OUT=$(GR 20990101_000003); RC=$?
chk "k8 [F3] owner drain xuat hien SAU precheck (truoc buoc dat KS) => gl_restart KHONG ghi de: FAIL KILL_SWITCH_token_khac, KS owner byte-giong, env khoi phuc, bot KHONG bi dung" "echo \"\$OUT\" | grep -q 'FAIL KILL_SWITCH_token_khac_luc_restart' && cmp -s $W/ks_owner $F/run/KILL_SWITCH && [ ! -e $F/run/KILL_SWITCH.prev_20990101_000003 ] && ! grep -q O5F_K8 $F/conf/env.sh && [ \"\$(pgrep -f \"^$FPAT\" | head -1)\" = '$BP' ]"
printf 'c3_autodrain 20261119_101500 caller=x\ngolive_monitor 1 KHAN y\n' > $F/run/KILL_SWITCH; OUT=$(GR 20990101_000004)
chk "k9 [F3] KS 2 dong (autodrain + KHAN monitor append) luc restart => KHONG ghi de" "echo \"\$OUT\" | grep -q 'FAIL KILL_SWITCH_token_khac_luc_restart' && [ \$(grep -c '' $F/run/KILL_SWITCH) = 2 ]"
rm -f $F/run/KILL_SWITCH* $F/run/.golive_* $F/conf/env.sh.bak_*; cp $W/env.sh.k8 $F/conf/env.sh; rm -f $F/bin/daemon.sh; startbot 1000

echo "== OPS5_FIX muc 6/7: deadman bo qua gate khi PAUSE con han; rollback autodrain chi go WD_PRESTART dong watchdog (A19)"
printf 'C3_ACCOUNT=SUB\n' > $W/deploy/golive_monitor.on; touch $W/deploy/run/monitor_heartbeat; rm -rf $DMD; gate_at $(( $(date +%s) - 900 ))
echo "C3GOLIVE_golive_micro_on TS=1 pid=1 t=1" > $W/PAUSE_dm
rm -f $W/tgdm.txt
OUT=$(DM WD_PAUSE=$W/PAUSE_dm bash "$HERE/golive_deadman.sh" 2>&1); RC=$?
chk "g1 [2a] gate cu 900 s NHUNG PAUSE watchdog moi (deploy/restart co chu dich) => BO QUA gate, khong canh bao gate" "echo \"\$OUT\" | grep -q 'INFO PAUSE watchdog 242 con han' && ! echo \"\$OUT\" | grep -q 'CANH BAO gate' && ! grep -qs 'CANH BAO gate' $W/tgdm.txt"
touch -d '-40 min' $W/PAUSE_dm
OUT=$(DM WD_PAUSE=$W/PAUSE_dm bash "$HERE/golive_deadman.sh" 2>&1); RC=$?
chk "g2 [2a] PAUSE CU (> 1800 s, bi bo quen) => VAN canh bao gate" "[ $RC = 2 ] && echo \"\$OUT\" | grep -q 'CANH BAO gate'"
rm -f $W/PAUSE_dm; OUT=$(DM WD_PAUSE=$W/PAUSE_dm bash "$HERE/golive_deadman.sh" 2>&1)
chk "g3 [2a] khong PAUSE + gate cu => canh bao gate (nhu cu)" "echo \"\$OUT\" | grep -q 'CANH BAO gate'"
rm -f $W/deploy/golive_monitor.on; rm -rf $DMD
printf '#!/bin/bash\nPRESTART=${WD_PRESTART:-/usr/local/sbin/h242-prestart.sh}\n' > $SB/h242_watchdog.sh; mkdir -p $SB
cp $W/ct242_0 $W/ct242; printf '*/2 * * * * WD_PRESTART=/x/y.sh /usr/local/sbin/other.sh\n' >> $W/ct242; cp $W/ct242 $W/ct242_a19
OUT=$(echo YES | AI bash "$HERE/install_242_autodrain.sh" 2>&1); OUT=$(echo YES | AI MODE=rollback bash "$HERE/install_242_autodrain.sh" 2>&1); RC=$?
chk "g4 [A19] rollback CHI go WD_PRESTART o dong watchdog; dong cron khac co WD_PRESTART giu nguyen (crontab = ban truoc install)" "[ $RC = 0 ] && cmp -s $W/ct242 $W/ct242_a19 && grep -q 'WD_PRESTART=/x/y.sh /usr/local/sbin/other.sh' $W/ct242"
cp $W/ct242_0 $W/ct242

# == KET THUC ==
cleanup
echo "TEST $( [ $FAILN = 0 ] && echo PASS || echo FAIL ) $PASS/$((PASS+FAILN))"
[ $FAILN = 0 ]
