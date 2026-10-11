# BUOC 6b [242, CHI DOC] kiem sau start (chay ~5' sau w4; chay lai ~15' de thay [LIVE-KLINE]). Exit 0 = PASS.
V=/home/chuyennd/java/v_t_m; C=/home/chuyennd/java/collectData
SHA=db181d41bd6837752638a63de99a2023cee7ad4b897d6e64924ac3d6c8f21577
read LV LC < /root/livefix_1011.loglines
F=0; ok(){ echo "OK   $*"; }; bad(){ echo "FAIL $*"; F=1; }
TL=$(tail -n +$((LV+1)) $V/logs/full.log); IL=$(tail -n +$((LC+1)) $C/logs/full.log)
for A in $V $C; do [ "$(sha256sum < $A/target/binance-java-sdk-1.2.4.jar | cut -c1-64)" = "$SHA" ] && ok "jar $A" || bad "jar $A"; done
for X in trading ingest; do
  [ $X = trading ] && L="$TL" || L="$IL"
  m=$(echo "$L" | grep -a 'SimpleSymbolMapper initialized' | tail -1 | cut -c1-160)
  echo "$m" | grep -q 'Total: 933, Next ID: 950' && ok "$X mapper: $m" || bad "$X mapper init (ky vong Total 933, Next ID 950): '$m'"
  echo "$L" | grep -aq 'MAPPER-DUP\]' && bad "$X co [MAPPER-DUP]" || ok "$X khong [MAPPER-DUP]"
  echo "$L" | grep -aq 'ID-CAP\]\|MAPPER-CAP\]' && bad "$X co [ID-CAP]/[MAPPER-CAP]" || ok "$X khong vuot tran id"
done
echo "$IL" | grep -a 'Started! \[KLINE-INGEST\] mode=' | tail -1 | grep -q 'mode=ws_settle' && ok "ingest [KLINE-INGEST] mode=ws_settle" || bad "ingest mode"
echo "$IL" | grep -a 'Chốt nến phút' | tail -1 | cut -c1-220
echo "$TL" | grep -a 'TICKER-CACHE\] full reload' | tail -1 | cut -c1-200 | grep . && ok "trading full reload" || bad "chua thay [TICKER-CACHE] full reload"
g=$(echo "$TL" | grep -a 'GATE-RATIO\] LIVE nạp buffer' | tail -1 | cut -c1-200); echo "$g"
echo "$g" | grep -q 'warm-up=false' && ok "[GATE-RATIO] nap buffer moi, armed (warm-up=false)" || bad "[GATE-RATIO] chua armed/khong nap"
echo "$TL" | grep -aq 'GATE-RATIO\] seed' && bad "[GATE-RATIO] seed lai lich su (buffer khong nap duoc)" || ok "khong seed lai"
echo "$TL" | grep -a 'GATE-RATIO\] q_t=' | tail -1 | cut -c1-160
k=$(echo "$TL" | grep -a 'LIVE-KLINE\]' | tail -1 | cut -c1-220); [ -n "$k" ] && ok "$k" || echo "WAIT [LIVE-KLINE] chua co (dong dau ~10' sau start) — chay lai w5"
P=$(pgrep -f 'com.binance.chuyennd.trading.BinanceOrderTradingManager' | head -1)
E=$(tr '\0' '\n' < /proc/$P/environ 2>/dev/null | grep -E '^(LIVE_PROFILE|SHADOW_NO_PUSH)=' | sort | tr '\n' ' ')
echo "$E" | grep -q 'LIVE_PROFILE=c3_shadow' && echo "$E" | grep -q 'SHADOW_NO_PUSH=true' && ok "env PID $P: $E" || bad "env PID $P: '$E'"
echo "$TL" | grep -a 'LEGACY\] managed' | tail -1 | cut -c1-60
echo "exceptions moi: trading=$(echo "$TL" | grep -ac 'Exception') ingest=$(echo "$IL" | grep -ac 'Exception')"
[ $F = 0 ] && echo "== W5 PASS" || echo "== W5 FAIL"
exit $F
