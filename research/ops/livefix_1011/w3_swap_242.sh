# BUOC 5 [242, GHI] backup jar + buffer (.bak_livefix_<TS>), thay jar (trading + collectData) va buffer gate. App PHAI dang dung.
# Giu ban staged .livefix_new (tool restore can jar moi khi rollback). Rollback: r_rollback_242.sh.
V=/home/chuyennd/java/v_t_m; C=/home/chuyennd/java/collectData
SHA=db181d41bd6837752638a63de99a2023cee7ad4b897d6e64924ac3d6c8f21577
TS=$(cat /root/livefix_1011.ts) || exit 2
nT=$(pgrep -fc 'com.binance.chuyennd.trading.BinanceOrderTradingManager'); nI=$(pgrep -fc 'com.binance.chuyennd.websocket.BinanceDataIngestor')
[ "$nT" = 0 ] && [ "$nI" = 0 ] || { echo "ABORT app dang chay"; exit 2; }
set -e
for A in $V $C; do
  J=$A/target/binance-java-sdk-1.2.4.jar
  [ -e $J.bak_livefix_$TS ] || cp -p $J $J.bak_livefix_$TS
  echo "$A bak=$(sha256sum < $J.bak_livefix_$TS | cut -c1-16)"
  cp -p $J.livefix_new $J
  [ "$(sha256sum < $J | cut -c1-64)" = "$SHA" ] || { echo "ABORT jar sau thay sai sha $J"; exit 3; }
done
B=$V/run/gate_ratio_live.bin
[ -e $B.bak_livefix_$TS ] || cp -p $B $B.bak_livefix_$TS
cp -p $B.livefix_new $B
cmp -s $B $B.livefix_new || { echo "ABORT buffer chep sai"; exit 3; }
ls -la $B $B.bak_livefix_$TS
echo "== W3 OK"
