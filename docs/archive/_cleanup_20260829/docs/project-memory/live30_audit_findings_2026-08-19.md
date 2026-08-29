# Audit 30 lệnh LIVE (242) vs backtest — findings — 2026-08-19

## Truy cập ĐÚNG: host 3stech.vn = 103.157.218.242, **port 2222**, user root, key id_rsa_chuyennd.
Log trading: /home/chuyennd/java/v_t_m/logs/full.log. Log ingestor: /home/chuyennd/java/collectData/logs/full.log. Signature:
- ENTRY thật: `BinanceOrderTradingManager: BUY <SYM> entry: <px> quantity: <qty> time:<yyyymmdd HH:MM> market level: PREDICT_SYMBOL_TRADE`
- Gate tick: `DetectEntrySignal2TradeNormal: 🔕 [PREDICT fail N] market[15M:X% Risk4H:Y%] Min15M:0.80% | SYM(score)...` (score=selector prob, thấp=tốt)
- Vị thế: `Update all position:N`. OI-feat: `OI-Feat-Compute-Loop ... ComputeOiFeat2Live242 DONE processed/pushed/empty`.

## Config live (config.properties)
NUMBER_ENTRY_EACH_SIGNAL=**4**, LEVERAGE_ORDER=1, CAPITAL_START=14000, RATE_TARGET=0.01, RATE_PROFIT_STOP_MARKET=**0.01**,
AEROSPIKE_NAMESPACE=ticker, gate FILE_AI_PREDICTIONS=ai_models_reg_v3. DIED_SYMBOLS blacklist dài.

## Phát hiện

### 1. ENTRY LOGIC + GIÁ ENTRY khớp backtest
- Cùng luồng DetectEntrySignal2TradeNormal → gate AIRejectFilter → selector topK → mở NUMBER_ENTRY_EACH_SIGNAL coin top.
- Gate pred live (0.00868, 0.00885...) ≥ Min15M 0.80% → vào đúng ngưỡng. Gate OK.
- Dedup coin-đang-giữ CÓ ở CẢ HAI: live `DetectEntrySignal2TradeNormal:313 symbol2Pos.containsKey→continue`;
  backtest `SimulatorMarketLevelTicker1MStopLoss` dùng `symbolLocked`(activeRunningIds).
- **GIÁ ENTRY khớp close nến 1m tại phút tín hiệu — median slippage ~0.000%**, entry giữa biên độ. Verify BTW 19/08
  (Binance 0.365→0.779) khớp từng mốc giờ log. "10ms loop lấy high" = KHÔNG. (Lượt đầu báo +9.7% là BUG tz của tôi, đã sửa.)

### 2. OI FEATURE — ĐÃ ĐÓNG PARITY (sửa lại nhận định sai trước đó)
- ~~Selector 5 OI = NaN~~ → SAI/lỗi thời. `ComputeOiFeat2Live242` ĐÃ deploy thành thread trong ingestor (OI-Feat-Compute-Loop),
  cadence 60', mỗi vòng processed=883 pushed=**691** empty(no-oi)=192; oi_feat_* tươi ~40' << tol 2h LiveOiFeatProvider.
- Trading log KHÔNG có NaN thật + KHÔNG có cảnh báo out-of-tol. (Con số "8924 NaN" tôi báo trước = FALSE POSITIVE:
  chuỗi "nan" khớp "biNANce" trong URL fapi + tên coin "baNANa"/BANANAS31; các dòng đó toàn 12–15/08 gate cũ Min15M 2.28%.)
- => Selector live chạy 45/45 feature, KHỚP backtest. Bỏ "OI-NaN" khỏi danh sách divergence.
- Caveat: aql/asinfo không cài trên 242 → chưa query trực tiếp lastTs set oi_feat_*; bằng chứng 45/45 là gián tiếp
  (push hourly tươi + zero out-of-tol). Chốt 100% cần ProductionVsBacktestFundingComparator dump feature per-coin.

### 3. LỆCH CONFIG (thật)
- **NUMBER_ENTRY_EACH_SIGNAL=4 (live)** vs code-default=2 (Configs.java:120). Cần xác nhận WFO worker set mấy;
  nếu backtest=2 → live mở GẤP ĐÔI số coin/tick.
- **RATE_PROFIT_STOP_MARKET=0.01** trong config live, MÂU THUẪN doc cũ (SIM_RATE_PROFIT_STOP_MARKET=0.05 qua env).
  Chưa thấy env file trong v_t_m/run → chưa rõ live thật dùng 0.01 hay 0.05. PHẢI check nguồn env (daemon/systemd).

### 4. "Leo tới đỉnh rồi kẹt" — XÁC NHẬN CÓ TRONG LIVE
40 entry gần nhất (18–19/08), stacking re-entry cùng coin leo dốc:
- **BTWUSDT ×7**: 0.492→0.529→0.535→0.564→0.713→0.719 (**+46%**); **HEMIUSDT +44%**; STAR ×7, GPS ×7, XPIN ×6, ACE ×4, ON ×3.
- Cơ chế: dedup CHỈ khóa khi đang giữ; TP thấp (RATE_TARGET 0.01=1%?) → coin pump chạm TP đóng nhanh → tick sau mở khóa →
  vào lại → leo theo pump từng nấc; lệnh cuối gần đỉnh không kịp TP trước dump = "kẹt".
- Backtest CŨNG có (maxdd_anatomy A5: 111 run re-entry≥3) nhưng THƯA hơn; live ĐẬM ĐẶC hơn (nghi do NUMBER_ENTRY=4).

### 5. 72 VỊ THẾ MỞ ĐỒNG THỜI (cần verify vs backtest)
- `Update all position:72–75` phẳng; ~39 symbol từng vào. Rất cao vs backtest.
- CHƯA đối chiếu backtest giữ bao nhiêu đồng thời (chạy sim đếm active-order max). Nếu backtest cap thấp hơn nhiều
  → divergence rủi ro lớn nhất (live over-diversify/over-deploy vốn).

## CÒN LẠI (chưa làm)
- [DONE] Entry-price slippage → khớp close ~0%.
- [DONE] OI parity → đã đóng (thread chạy, push 691/vòng, không NaN thật).
- Backtest concurrent-position count vs 72 (chạy sim, đếm active order max) → chốt divergence #5.
- Truy nguồn env live (RATE_PROFIT_STOP 0.01 vs 0.05; NUMBER_ENTRY backtest thật).

## Verdict (cập nhật)
Entry logic + giá entry + OI feature (45/45) TRUNG THÀNH backtest. Selector KHÔNG còn lệch do OI. Lệch thật thu hẹp về
**THAM SỐ vận hành**: NUMBER_ENTRY_EACH_SIGNAL=4, exit param 0.01-vs-0.05 (mập mờ), và **72 vị thế / stacking leo dốc đậm**
— đúng cái user cảm nhận "vào nhiều + leo đỉnh rồi kẹt". Chưa thấy bug logic; là divergence config vận hành.

## Đính chính 2 lỗi của tôi trong phiên (để không lặp)
1. Slippage +9.7%/+44% = BUG double-trừ 7h (Oracle tz GMT+7). Fix: calendar.timegm.
2. "8924 NaN / selector OI-NaN" = FALSE POSITIVE ("biNANce"/"baNANa") + bê doc lỗi thời. OI thực tế đã đóng parity.
