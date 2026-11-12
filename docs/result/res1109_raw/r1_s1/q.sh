cd ~/claude_master/v12/wt_r4u3
sed -n 341,420p src/main/java/com/binance/chuyennd/ai_ml/onnx/entry/LiveGateRollingRatio.java
echo ----
sed -n 1225,1300p src/main/java/com/binance/chuyennd/trading/DetectEntrySignal2TradeNormal.java
echo ----
grep -nE 'AIRejectFilter\.[a-zA-Z]+\(' src/main/java/com/binance/chuyennd/trading/DetectEntrySignal2TradeNormal.java | head
