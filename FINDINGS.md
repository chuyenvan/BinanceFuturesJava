# FINDINGS — Tổng hợp điều tra hệ Bot Trading (nguồn sự thật bền vững)

> Mọi kết luận đã ĐO ĐƯỢC kèm số thật + lý do. Đọc file này là nắm toàn bộ, không cần đào lại.
> 🟢 đã chứng minh bằng số | 🟡 bằng chứng một phần | 🔴 vấn đề/rủi ro | ⚠️ cạm bẫy | ✏️ đính chính kết luận sai cũ.
> Quy tắc vàng: ĐO bằng số trước khi kết luận. Đọc code thật, không đoán. Tách MODEL (Cổng 1) vs CHIẾN LƯỢC (Cổng 2).

---

## 0. HỆ THỐNG

Bot futures Binance, **long-only, leverage 1, martingale/DCA** (nhồi trung bình giá khi tụt),
**KHÔNG hard stop-loss**, thoát bằng **trailing stop chỉ khi đã có lãi**. Hai model AI lọc entry:
(1) **MARKET model** (regression ONNX, basket-level) → `predReturn15M`, `predRisk4H` (24H đã bỏ);
(2) **FUNDING model** (classifier 5 lớp theo symbol) → `symbolPred = pred[0] = P(FAIL)`.
HPO bằng Jenetics phân tán (master + 7 worker). Package `com.binance.chuyennd.*`.

---

## 1. KẾT LUẬN LỚN NHẤT — ✏️ ĐÃ ĐÍNH CHÍNH

**Hệ LÃI thật qua chu kỳ đầy đủ. Entry có edge. DCA GIÚP (không phá). Đây là hệ lành mạnh,
chỉ cần tối ưu nhỏ — KHÔNG phải hệ hỏng cần làm lại.**

🟢 Bằng chứng (RunBreakerBacktest mode OFF, 2021→2026, slippage 0.003):
- totalPnl = **+70986** (vốn 35000 → ~106000, gấp đôi qua 5 năm).
- PnL DƯƠNG **mọi năm**, kể cả bear: 2021=20157, 2022=7658, 2023=9513, 2024=16634, 2025=14956, 2026=2069.
- maxDD = −35.3% vốn (unrealized).

✏️ HAI lần Claude kết luận SAI trong phiên, đã sửa:
- "Hệ lỗ qua chu kỳ" — SAI. Nhầm `UnProfitMin` (−35%/−39% = drawdown unrealized TẠM THỜI lúc cụm đang
  mở) thành lỗ thực hiện. PnL thực hiện DƯƠNG mọi năm. Hệ ôm lệnh tụt sâu chờ hồi rồi thoát có lãi.
- "DCA phá edge, cần breaker" — SAI. Breaker chứng minh DCA GIÚP (xem mục 6).

🟢 Live thật (242) drawdown từng chạm **40%**, user **CHẤP NHẬN ĐƯỢC**. Backtest −35% KHỚP live → backtest
realistic (hiếm; nhiều bot backtest đẹp hơn live xa). Hệ ở trạng thái tốt hơn tưởng.

---

## 2. MARKET MODEL (3 target)

### 2a. predReturn15M 🟢 GIỮ — edge thật, vùng nảy ~1%
- Train (holdout 12 tháng, đã sửa leak): IC 0.5345, t=117. KHÔNG leak gương: bỏ momentum15M+1M → IC giữ
  0.5320. Champion đơn biến `momentumAcceleration` IC 0.4432; bỏ nó IC vẫn 0.5287 → edge phân tán.
- 🟢 OOS THẬT: IC live **0.5175, t=70.5** (set `ai_pred_market_full_basket_v2`, từ 20/12/2025). Edge thật,
  ổn định mọi regime (~0.50/0.51/0.54). Model > rule-base **x1.21** (giá trị AI khiêm tốn nhưng thật).
- Bản chất = "đo volatility/biến động". Phân bố realized 15M: p50=0.85%, **%>1%=30.4%, %>2%=0.9%,
  %>3%=0.1%, %>6%=0.0%**. Edge tập trung **vùng nảy ~1%**. LIFT top-decile: +1% x2.40.
- 🔴 Hệ quả: +3%/+6% gần như KHÔNG xảy ra ở basket 15p → `RATE_PROFIT_STOP_MARKET` đặt cao chống lại
  phân bố thực tế (đáng xem lại exit, chưa làm).

### 2b. predReturn24H ✅ ĐÃ BỎ HẲN khỏi hệ
- n_dov chỉ 360 (thiếu mẫu). Champion `momentumAcceleration` 136% IC = rule-base thuần, model vô dụng.
- Realized 24H: %>3%=100%, %>6%=85.5% → LIFT ~x1.0. Filter ablation A=C tuyệt đối → MOM24 chưa bao giờ
  kích hoạt. ĐÃ bỏ, backtest KHÔNG đổi.
- 🟢 GIỮ INSIGHT (không phải model): giữ lệnh tới 24h thì +3%/+6% gần như chắc chắn → định hình exit.

### 2c. predRisk4H (dd4h) 🟡 giữ qua nhánh RISK, nhưng chỉ là volatility proxy
- Train IC 0.149; champion `basketVolSpike` 131% IC → model thực chất LÀ basketVolSpike đội lốt.
  IC[up]=−0.0155 (âm ở regime tăng). OOS: IC[up]=0.004 (gần 0 đúng lúc cần).
- Nhánh RISK trong filter: bỏ nó (mode B/D) làm PnL tụt 17699→13488 (+31% nếu giữ) → đang LỌC LỆNH KÉM,
  GIỮ. NHƯNG KHÔNG cải thiện đuôi (xem mục 4). ⚠️ Đừng thay dd4h bằng basketVolSpike — nó LÀ basketVolSpike.

---

## 3. FUNDING MODEL — ✏️ ĐÍNH CHÍNH: CÓ EDGE và ĐƯỢC DÙNG MẠNH (không phải no-op)

### Bản chất
- Classifier 5 lớp: 0=Fail, 1=72H, 2=24H, 3=4H, 4=15M (tốc độ chạm +6%). `symbolPred = pred[0] = P(FAIL)`
  = P(72h tới KHÔNG đạt +6%). symbolPred CAO = symbol XẤU. Decode: 16-bit symbolId (bit cao) + 32-bit
  float pred[0] (bit thấp). Map qua `SimpleSymbolMapper`.
- ⚠️ Set hiện tại `funding_pred_1m_v5` đang là **model CŨ** (mỗi record len=1). Model 5 lớp mới (train tới
    20260525) CHƯA gen vào set. Validate dưới đây là cho MODEL CŨ đang chạy live.

### 🟢 Validate OOS (ValidateFundingOOS, model cũ, OOS từ 20251220, n=26006 de-overlap 72h/symbol)
- **IC(symbolPred, realized_FAIL) = 0.2143, t=35.4** (đối chứng: IC với realized_HIT = −0.2143). Edge THẬT.
- Mạnh nhất regime **down**: IC=0.2476 (đúng lúc cần phân biệt nhất). up=0.185, side=0.177.
- Realized khớp ĐÚNG label6 (`FundingDataCollectionManager`): entry=priceClose tại t, target=×1.06,
  hit nếu maxPrice ≥ target trong (t, t+72h]. Đã verify code thật.
- Phân bố symbolPred: **p10=0.425, p50=0.55, p90=0.60**. 0.4% dưới 0.197; **~2-5% dưới 0.32**.
- base-rate FAIL = 55.7%. Nhóm pred<0.5 fail 38% vs pred>0.5 fail 61% → model phân biệt rõ (cách ~23 điểm).

### 🟢 Funding ĐƯỢC DÙNG MẠNH ở PRE-FILTER (chỗ Claude từng bỏ sót → kết luận sai "no-op")
Trong `SimulatorMarketLevelTicker1MStopLoss` (vòng tạo entry PREDICT_SYMBOL_TRADE):
```
maxThres = PREDICT_SYMBOL_RATE_MAX_THRESHOLD(0.15) × AI_DYNAMIC_MAX(2.14135) = 0.321
for (long enc : symbol2Pred)  // ĐÃ sort tăng dần theo float pred
    if (symbolPred > maxThres) break;   // chỉ xét symbol pred <= 0.32
```
- 🟢 Sort ĐÚNG: `preprocessFundingData` → `quickSortByFloatPred` sort theo `Float.intBitsToFloat`, KHÔNG
  phải sort long thô. (Đã nghi bug sort, đọc code thật → không bug.)
- Hệ chỉ trade **~2-5% symbol tốt nhất** mỗi phút (pred ≤ 0.32). ~450 symbol/phút có pred → ~9-22 lọt
  qua break/phút → đủ cho 18848 lệnh/7 tháng. Khớp quan sát live ("top symbol P-fail 0.2-0.4").
- Funding cũng tham gia nhánh EARLY (`symbolPred > PREDICT_SYMBOL_RATE_MAX_THRESHOLD`) + scaleFactor động
  trong `AIRejectFilter.checkSignalDynamic`. Với nhóm trade (pred 0.03-0.32) và ngưỡng 0.15, scaleFactor
  biến thiên ~0.27-2.14 — KHÔNG bão hòa (Claude từng nói bão hòa = SAI, do dùng nhầm phân bố 0.42-0.60).
- → **Funding là bộ lọc vũ trụ CHÍNH, dùng rất mạnh.** Kéo fail-rate nhóm trade xuống ~30-35% vs base 55.7%
  (ước lượng) — giá trị thật, lớn.

### 🔴 Việc dở quan trọng — validate ĐÚNG nhóm hệ dùng
ValidateFundingOOS đo IC/LIFT trên TOÀN BỘ symbol và theo hướng `pred>ngưỡng` (lọc xấu) — SAI nhóm + SAI
hướng so với cách hệ dùng (giữ `pred ≤ 0.32`, nhóm tốt). CẦN sửa tool đo:
1. fail-rate trong nhóm `symbolPred ≤ maxThres(0.32)` vs base 55.7%.
2. IC nội nhóm ≤0.32 (trong nhóm tốt, pred thấp hơn có fail ít hơn không).
3. Chia lát (≤0.1, 0.1-0.2, 0.2-0.32) tìm ngưỡng cắt tối ưu.
   ⚠️ ValidateFundingOOS hardcode EARLY_THRES=0.197 nhưng Configs thật = **0.15** (0.197 là giá trị HPO đã
   revert bỏ) → sửa về 0.15.

---

## 4. FILTER (AIRejectFilter) — lá chắn entry & ablation

- `checkSignalDynamic(prediction, symbolPred)`: nhánh EARLY (`pred15 < MIN_MOMENTUM_15M && symbolPred >
  PREDICT_SYMBOL_RATE_MAX_THRESHOLD`) + scaleFactor động + `evaluate` (RISK + MOM15; MOM24 đã bỏ).
- ValidateBrakeDynamic (12.469.300 quyết định symbol-level, CHƯA de-overlap): PASS 0.1%, REJECT 99.9%.
  Phân rã: RISK 0.0% | MOM15 3.4% | **EARLY 96.5%**. ⚠️ Giá trị tuyệt đối DD phóng đại (chồng lấn), chỉ
  đọc tương đối. AI filter KHÔNG chặn được cú sập (cái 0.1% được vào vẫn tụt sâu).
- ⚠️ Lá chắn EARLY là 15M + funding KẾT HỢP (funding qua pre-filter mục 3 + điều kiện EARLY). Vai trò
  chính xác của từng vế cần ablation funding đo (chưa làm) — ĐỪNG kết luận "chỉ 15M" hay "chỉ funding".

### Filter ablation (backtest 7 tháng 20251001–20260430) — ⚠️ CỬA SỔ NGẮN, THUẬN
| mode | trades | PnL | PF | maxDD | worstLoss |
|------|--------|-----|----|-------|-----------|
| A (full) | 18848 | 17699 | 1.99 | -10115 | -768.6 |
| B (bỏ RISK) | 18527 | 13488 | 1.75 | -10128 | -768.6 |
| C (bỏ MOM24) = A tuyệt đối | | | | | |
| D (bỏ cả) = B | | | | | |
- A=C → MOM24 vô dụng (đã bỏ). B<A → RISK lọc lệnh kém (+31% PnL), giữ. worstLoss/maxDD **y hệt 4 mode**
  → filter KHÔNG chạm được đuôi. ⚠️ 7 tháng này LÃI nhưng là cửa sổ thuận — đừng kết luận từ nó.

**Chốt filter: FILTER_MODE=A** (giữ RISK+MOM15+EARLY), MOM24 đã bỏ hẳn.

---

## 5. CHẨN ĐOÁN NGUỒN LỖ ĐUÔI (RunTailLossDiagnostic, 7 tháng)

- Quy lỗ theo levelChange: `PREDICT_SYMBOL_TRADE` −10631/8246 leg (−1.3/leg, bình thường);
  `DCA_LEVEL1` −5293/86 leg (**−61.5/leg**); worstLeg đơn = DYM −768 BIG_UP (cú lẻ, không hệ thống).
- Cụm tệ nhất: giữ tới **160 ngày** tụt −80%; RAVE/PIPPIN 1 leg tụt −96% (coin rác sập không hồi).
- maxDD −28.9% lúc **325 cụm mở** ngốn **96.8% vốn** → maxDD do MẬT ĐỘ cụm, không do 1 cú lỗ.
- Ba nguồn rủi ro khác nhau: (1) mật độ cụm, (2) DCA khuếch đại, (3) coin rác sập-không-hồi (vấn đề
  CHẤT LƯỢNG ENTRY, không phải phanh). ✏️ Nhưng xem mục 6: chặn (1)(2) bằng breaker làm TỆ HƠN.

---

## 6. CIRCUIT BREAKER — ✏️ ĐÃ THỬ, SAI HƯỚNG, BỎ

RunBreakerBacktest 2021→2026, 4 mode (MARGIN_HALT=0.70, CLUSTER_DD_MAX=−0.30):
| mode | totalPnl | maxDD | 2026 |
|------|----------|-------|------|
| OFF | **70986** | −35.3% | 2069 |
| MARGIN | 60805 (−14%) | −37.0% (xấu hơn) | 709 |
| DCA | 68664 | −33.6% | 1797 |
| BOTH | 55283 (tệ nhất) | −40.3% (tệ nhất) | **−1813** |

🟢 PHÁN QUYẾT: breaker làm TỆ HƠN mọi mặt. Chặn DCA/margin = chặn lãi (đa số DCA cứu lệnh thành công qua
mean-reversion; mở lệnh lúc margin cao = lúc sập = đúng cơ hội DCA tốt). Vài cú thảm họa hiếm (−80%, 160
ngày) KHÔNG đại diện DCA nói chung. **DCA là TÍNH NĂNG, không phải bug. Bỏ ý tưởng breaker.** KHÔNG
force-close. Nếu sau này muốn giảm DD: thử giảm số cụm/size (không chặn DCA), nhưng phải đo — có thể lại
mất lãi như MARGIN.

---

## 7. 🔴 VẤN ĐỀ PHƯƠNG PHÁP LỚN NHẤT — IN-SAMPLE & WFO

Backtest đầy đủ "lãi mọi năm" phần lớn là IN-SAMPLE → là CẬN TRÊN lạc quan, chưa phải OOS thật.
- Model cũ (gen predict set) train tới **20251219** → predict 2021–2025 là in-sample.
- Tham số HPO trên **6 tháng 20251001–20260330** → 2021–~09/2025 là param-OOS (sạch về tham số).
- Cửa sổ SẠCH CẢ HAI (model + tham số OOS) = **chỉ từ 04/2026 trở đi** (~2 tháng, ngắn).
- 🟡 Giảm lo: model OOS IC (0.5175) ≈ in-sample IC (0.5345) → model tổng quát hóa tốt, ít overfit →
  nhiễm model NHỎ. Tham số chỉ in-sample 6 tháng gần. Nên "lãi 2021-2024" (param-OOS) tương đối đáng tin.

### WFO — cách làm đúng (Bước 4 ROADMAP, CHƯA làm)
- Cuốn chiếu: cửa sổ test 3-6 tháng, mỗi cutoff train model + HPO trên dữ liệu TRƯỚC đó (purge ≥ 72h vì
  label nhìn 72h), test sau cutoff, ghép các đoạn test = đường cong OOS thật.
- ⚠️ WFO tạo NHIỀU model mới (mỗi cutoff một cái) — model cũ/mới hiện có KHÔNG dùng được (đã thấy quá nhiều
  dữ liệu). Model mới (tới 20260525) chỉ để PRODUCTION sau khi WFO xác nhận; validate nó trên 2026 =
  in-sample, vô nghĩa.
- ⚠️ WFO phải MIRROR quy trình vận hành thật (train full-history + HPO 6 tháng gần nhất) → chi phí HPO/cửa
  sổ không phình.

### 🔴 Chi phí thật (từ số user) — đừng lao vào full WFO ngay
- HPO 1 vòng/4 tháng = 3 phút; full HPO (master+7 worker) > 1 ngày (11 tham số entry+DCA, CHƯA có trailing/
  quản lý vốn). Train model 6h (không tinh chỉnh) / 2 ngày (tinh chỉnh). Gen predict 5 năm = 2 ngày.
- Full WFO 3 tháng (~10 cửa sổ) ≈ **15–20 ngày** chạy; 6 tháng (~5 cửa sổ) ≈ 8–10 ngày.
- ĐỀ XUẤT: ĐO NHIỄM bằng 1 bước trước (train cutoff 20230930, test H1/2024, so với backtest in-sample cùng
  cửa sổ). Delta nhỏ → backtest hiện tin được, WFO hạ ưu tiên. Delta lớn → full WFO bắt buộc. Bò trước khi chạy.
- ⚠️ Cần xác nhận: pipeline gen predict chạy được cho RIÊNG 1 cửa sổ ngắn không, hay buộc gen cả 5 năm
  (nếu buộc 5 năm → mỗi cửa sổ tốn 2 ngày gen → phải sửa tool gen nhận from/to trước).

---

## 8. QUYẾT ĐỊNH ĐÃ CHỐT (Configs hiện tại)

- ✅ SLIPPAGE_RATE = **0.003** cố định (bi quan-an-toàn; coin rác + nhồi lúc sập). Nên đo slippage thật từ
  lệnh live 242 sau. RATE_FEE=0.002 (2 chân). APPLY_SLIPPAGE=true, BLOCK_INTRABAR_LOOKAHEAD=true.
- ✅ MOM24/predReturn24H bỏ hẳn. FILTER_MODE=A. BREAKER_MODE=OFF (bỏ ý tưởng breaker).
- ✅ Look-ahead đã vá; `BacktestIntegrityGuard.assertProductionGrade()` cắm trong sim.
- Tham số chính: PREDICT_SYMBOL_RATE_MAX_THRESHOLD=0.15, AI_DYNAMIC_MAX=2.14135 (→ pre-filter cut 0.32),
  AI_DYNAMIC_MULTIPLIER=1.2876, MIN_MOMENTUM_15M=0.02284, HARD_RISK_LIMIT_4H=-0.2.
  (Nhiều tham số có comment "HPO đã revert về cũ" — bản đang dùng là bản CŨ revert, không phải bản HPO.)

---

## 9. VIỆC TIẾP (ưu tiên)

1. **Sửa ValidateFundingOOS** đo đúng nhóm hệ dùng (pred ≤ 0.32): fail-rate vs base, IC nội nhóm, chia lát
   tìm ngưỡng tối ưu. Sửa EARLY_THRES 0.197→0.15. → biết funding đóng góp thật bao nhiêu + ngưỡng 0.32 tối ưu chưa.
2. **Ablation funding**: cố định symbolPred=hằng số, backtest đầy đủ → đo đóng góp funding vào PnL/đuôi.
3. **Đo nhiễm in-sample** (1 bước WFO: cutoff 20230930, test H1/2024) → quyết có làm full WFO không.
4. Gen lại funding pred bằng model 5 lớp mới + calibrate ngưỡng theo phân bố model mới.
5. Bật lại `updateFundingFee` (đang comment → PnL tuyệt đối lạc quan; đuôi ít ảnh hưởng).
6. Cải thiện entry tránh coin rác sập-không-hồi (nguồn lỗ 3). Xem lại exit (RATE_PROFIT_STOP cao vs nảy ~1%).

---

## 10. ROADMAP

(0)look-ahead ✓ | (1)đo IC model ✓ (market + funding đều validate OOS) | (2)ablation ✓ filter, ◐ funding
(chưa) | (3)mô hình hóa ruin: breaker đã thử SAI HƯỚNG, bỏ; DCA giúp | (4)WFO ◄ vấn đề lớn nhất, đo nhiễm
trước | (5)hợp nhất sim/product. Bằng chứng dẫn đường, không máy móc.

---

## 11. CẠM BẪY (đừng lặp — Claude đã sai nhiều lần ở các điểm này)

- ⚠️ `UnProfitMin` = drawdown unrealized TẠM THỜI, KHÔNG phải lỗ thực hiện. (Claude nhầm → "hệ lỗ" sai.)
- ⚠️ DCA giúp (mean-reversion), không phá. Vài cú thảm họa hiếm không đại diện. (Claude nhầm → breaker sai.)
- ⚠️ Funding KHÔNG no-op — nó lọc mạnh ở PRE-FILTER trong Simulator (cut 0.32), không chỉ ở AIRejectFilter.
  (Claude bỏ sót pre-filter → kết luận no-op sai. Luôn đọc luồng entry đầy đủ, không chỉ filter class.)
- ⚠️ Cửa sổ ngắn lừa: ablation 7 tháng LÃI, nhưng backtest đầy đủ mới thật. Luôn test qua chu kỳ đầy đủ.
- ⚠️ In-sample lừa: backtest trên giai đoạn model/HPO đã thấy = cận trên. OOS thật cần WFO.
- ⚠️ Win-rate VÔ NGHĨA với martingale (dùng profitFactor/worstLoss/maxDD/payoff). R2 SAI cho label tụ hẹp
  (dùng IC de-overlap + LIFT). IC cao ≠ dùng được.
- ⚠️ De-overlap theo cửa sổ nhãn (15M/72h) trước khi tính t-stat; KHÔNG thì phóng đại. Với nhãn 72h, tính
  realized chỉ cho mẫu sống sót sau de-overlap (online), KHÔNG tính cho mọi phút rồi vứt (OOM + chậm ~1000x).
- ⚠️ decode funding chỉ lấy pred[0]=P(fail), bit thấp; symbolId bit cao. Đổi thứ tự output model = sai âm thầm.
- ⚠️ Backtest phải tái lập: commit trước, ghi commit+giai đoạn+Configs(slippage)+set. Sim không random.
- ⚠️ Bump CONFIG_VERSION khi đổi model/predict; KHÔNG bump cho đổi filter/sim/ablation.
- ⚠️ Phiên chat dài làm context loãng → Claude dễ tính sai cái vừa gửi. Mở chat mới + kéo file này khi cần.

---

## 12. HẠ TẦNG

- **242** (103.157.218.242): PRODUCT tiền thật + data ticker. Aerospike CE 3222 đã khóa firewall (5 rich-
  rule: 242, 127.0.0.1, 226, VPN 10.8.0.0/24, Oracle 161.118.206.1). SSH 2222.
- **226** (103.157.218.226): backtest cá nhân + data predict/market. Aerospike public (Kaggle cần).
- **Oracle VPS** (egress 161.118.206.1): master HPO. **Kaggle**: train GPU + worker HPO.
- Set: market predict `ai_pred_market_full_basket_v2`, funding predict `funding_pred_1m_v5` (đang model cũ len=1).

---

## 13. FILE LIÊN QUAN

Tool validate/diag (Java, 226): ValidateOldPredictVsRealized, ValidateBrakeDynamic, InspectFundingPredRaw,
ValidateFundingOOS, RunFilterAblation, RunTailLossDiagnostic, RunBreakerBacktest.
Docs: FINDINGS.md (file này), AUDIT_filter_ablation.md (luồng dữ liệu + code), TRACE_backtest_drift.md
(vì sao từng không tái lập), CLAUDE.md (luật + trỏ tới các file research).