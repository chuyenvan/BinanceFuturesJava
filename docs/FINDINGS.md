# FINDINGS — Tổng hợp điều tra hệ Bot Trading (kết tinh để không mất insight)

> Mục đích: chốt MỌI kết luận đã ĐO ĐƯỢC kèm số thật + lý do, để dùng làm nguồn sự thật bền vững
> (không phụ thuộc trí nhớ phiên chat). Đọc file này là nắm được toàn bộ, không cần đào lại.
> Quy ước đọc: 🟢 = đã chứng minh bằng số | 🟡 = bằng chứng một phần | 🔴 = vấn đề/rủi ro | ⚠️ = cạm bẫy.

---

## 0. HỆ THỐNG LÀ GÌ (one-paragraph)

Bot futures Binance, **long-only, leverage 1, martingale/DCA** (nhồi trung bình giá khi tụt),
**KHÔNG hard stop-loss**, thoát bằng **trailing stop chỉ khi đã có lãi**. Hai model AI lọc entry:
(1) **MARKET model** (regression, ONNX, basket-level) dự báo `futureReturn15M / futureReturn24H /
maxDrawdownNext4H`; (2) **FUNDING model** (classifier 5 lớp, theo symbol) cho `symbolPred`.
HPO bằng Jenetics phân tán. Package gốc `com.binance.chuyennd.*`.

---

## 1. KẾT LUẬN LỚN NHẤT CỦA CẢ BUỔI 🔴🟢

**Entry CÓ edge thật, nhưng cơ chế DCA không giới hạn + không stop PHÁ HẾT edge đó qua chu kỳ đầy đủ.**

Bằng chứng hai vế:
- 🟢 Entry tốt: `PREDICT_SYMBOL_TRADE` payoff ratio **> 1 mọi năm** (2021:1.05 … 2023:3.13, 2024:1.48,
  2026:2.63) trong backtest 2021→2026. Market 15M model có **IC live 0.52** trên OOS thật.
- 🔴 Hệ vẫn LỖ qua chu kỳ: backtest đầy đủ 2021→2026 cho balance-ratio **< 1 mọi năm**, 2026 ≈ 0.12,
  2025 lỗ nặng (~-2003 đến -6962 tùy bộ tham số), maxDD (UnProfitMin) **-35% đến -39% vốn**.

→ Diễn giải: thắng hàng nghìn lệnh nhỏ, nhưng **vài cụm DCA nhồi vô hạn vào coin sập rồi ôm chết**
ăn sạch lãi. Đây là bản chất martingale tự hủy. **Đây là vấn đề trọng tâm cần giải, KHÔNG phải entry.**

---

## 2. MARKET MODEL — 3 TARGET (đã validate kỹ)

### 2a. futureReturn15M 🟢 GIỮ — edge thật, vùng nảy ~1%
- Train mới (holdout 12 tháng, đã sửa leak): **IC 0.5345, t=117**.
- 🟢 KHÔNG phải leak gương: bỏ `momentum15M`+`momentum1M` → IC giữ **0.5320 (x1.00)**. (Claude từng
  nghi leak gương 15p — ĐÃ BÁC BỎ bằng số.)
- Champion đơn biến = `momentumAcceleration` IC 0.4432; bỏ nó IC vẫn 0.5287 → edge phân tán, không
  phụ thuộc 1 feature. Model > rule-base chỉ **x1.21** (giá trị AI khiêm tốn nhưng thật).
- Bản chất edge = "đo volatility/biến động gần đây" (nhóm momentumAcceleration/volatility* top bảng IC).
- IC ổn định mọi regime (~0.50 up / 0.51 down / 0.54 side).
- **Validate OOS THẬT** (predict model cũ trên set `ai_pred_market_full_basket_v2`, từ 20/12/2025 =
  chưa train, 13609 điểm de-overlap): **IC live 0.5175, t=70.5** — không leak được, edge thật.
- Phân bố realized 15M: p50=0.85%, **%>1%=30.4%, %>2%=0.9%, %>3%=0.1%, %>6%=0.0%**.
- LIFT top-decile: +1% → **x2.40** (73% vs 30%); +2% → x5.9; +3% → x4.67 (chỉ 0.5%); +6% → x10 (0.2%).
- 🔴 INSIGHT QUAN TRỌNG: edge tập trung **vùng nảy ~1%**. Nảy +3%/+6% gần như KHÔNG xảy ra ở mức
  basket 15 phút. → `RATE_PROFIT_STOP_MARKET` (trailing) đặt cao (3%) là chống lại phân bố thực tế.
- Drawdown top-decile (điểm model bảo VÀO): p50=-0.5%, p90=-0.25%, worst=-15.6% → phần lớn tụt nông,
  model tránh được phần lớn cú sâu.

### 2b. futureReturn24H 🔴 BỎ — thiếu mẫu cấu trúc
- Train mới: IC 0.1636, **n_dov chỉ 360** (label nhìn 24h → 12 tháng chỉ ~360 điểm độc lập). Gate FAIL.
- Champion `momentumAcceleration` đạt **136% IC của model** → rule-base thuần, model vô dụng.
- Validate OOS: IC 0.256 nhưng n=145 (quá yếu). Realized 24H: **%>3%=100%, %>6%=85.5%** → LIFT ~x1.0
  (mọi điểm đều chạm, model không giúp chọn).
- 🟢 GIỮ INSIGHT (không phải model): **giữ lệnh tới 24h thì +3%/+6% gần như chắc chắn xảy ra.** Đây là
  lý do hệ DCA chờ-lâu có thể thoát mục tiêu cao — định hình exit, không cần model.
- ✅ ĐÃ BỎ `predReturn24H` khỏi filter — backtest KHÔNG đổi (xác nhận vô dụng). Ablation A=C tuyệt đối.

### 2c. maxDrawdownNext4H (dd4h) 🟡 gần vô dụng — chỉ là basketVolSpike trá hình
- Train mới: IC 0.149, t=7.0, n=2157. PASS gate NHƯNG champion `basketVolSpike` đạt **131% IC** →
  model thực chất chỉ là `basketVolSpike` đội lốt. IC[up]=**-0.0155** (âm ở regime tăng), IC[down]=0.21.
- Validate OOS: IC 0.163, IC[up]=0.004, IC[down]=0.054 (gần 0 ở đúng lúc cần — regime sập).
- Phanh cứng `HARD_RISK_LIMIT_4H=-0.092`: model **chưa bao giờ** ra predRisk4H ≤ -9.2% → phanh CỨNG
  reject = 0% mọi regime (nhưng filter live dùng ngưỡng ĐỘNG, xem mục 4).
- ⚠️ Đừng thay dd4h bằng `basketVolSpike` — vì dd4h CHÍNH LÀ basketVolSpike. Thay = thay chính nó.

---

## 3. FUNDING MODEL (symbolPred) 🟢 chạy đúng chiều

- Là classifier **5 lớp** theo tốc độ chạm +6%: `0=Fail, 1=72H, 2=24H, 3=4H, 4=15M`.
- ⚠️⚠️ **`symbolPred` dùng trong filter = `pred[0]` = P(FAIL)** — xác suất 72h tới KHÔNG đạt +6%.
  KHÔNG phải P(chạm). Giá trị cao = symbol XẤU (dễ fail). Chiều này ĐÚNG trong filter (xem mục 4).
- Phân bố lớp (train, 18.5M mẫu): fail~34%, 72H~16%, 24H~29%, 4H~19%, 15M~1.6%.
- Train mới (label6, holdout 12 tháng): rank-IC 0.2249 t=53.6; LIFT P(fast)≥0.5 → hit 52.4% vs base
  6.8% = **x7.68**. PASS.
- ⚠️ NHƯNG: train ĐO trên `pfast = P(lớp 3)+P(lớp 4)` (chạm nhanh), còn filter DÙNG `pred[0]=P(fail)`.
  Hai đại lượng khác nhau — chưa ai gate riêng cho pred[0]. (Việc dở: nên đo LIFT/calibration của
  chính pred[0] tại ngưỡng 0.197.)
- 🟢 Quan sát LIVE thật (user): top 10 symbol P-fail thấp nhất ~0.2–0.4, khi thị trường rung lắc tụt
  <0.1; top dưới 0.4–0.9. → funding model phân biệt được symbol, nhạy với thị trường. Chạy đúng.

### Cạm bẫy encode/decode funding ⚠️
- `encodeFundingMapToBinary` lưu TOÀN BỘ vector; `decodeFundingMapToPrimitiveArray` chỉ lấy `pred[0]`,
  pack 16 bit symbolId + 32 bit float.
- 🔴 Set funding pred HIỆN TẠI trên Aerospike (`funding_pred_1m_v5`) đang là **data CŨ**: mỗi record
  `len=1` (1 giá trị ~P-fail, dao động 0.1–0.9). **Model 5 lớp mới CHƯA được gen lại/deploy.**
  → Khi deploy model 5 lớp mới, pred[0]=P(class0)=P-fail, chiều vẫn nhất quán, nhưng HÀNH VI filter
  sẽ đổi (giá trị phân bố khác). Phải lường trước khi gen lại.
- ⚠️ Nếu đổi thứ tự output funding model → `symbolPred` sai âm thầm, không báo lỗi.

---

## 4. FILTER & PHANH ĐỘNG (AIRejectFilter) — lá chắn thật nằm ở đâu

### Cơ chế
- `checkSignalDynamic(prediction, symbolPred)` — phần lớn entry đi qua đây (ngưỡng ĐỘNG).
- `scaleFactor = clamp((symbolPred / PREDICT_SYMBOL_RATE_MAX_THRESHOLD) * AI_DYNAMIC_MULTIPLIER,
  AI_DYNAMIC_MIN, AI_DYNAMIC_MAX)`. symbolPred=P-fail cao → scale cao → siết chặt (đúng chiều).
- `dynamic_15M = MIN_MOMENTUM_15M * scale`; `dynamic_Risk4H = HARD_RISK_LIMIT_4H / scale`.
- Nhánh **EARLY** (chặn sớm): `if (pred15 < MIN_MOMENTUM_15M && symbolPred > PREDICT_SYMBOL_RATE_MAX_THRESHOLD) REJECT`.
- `evaluate` có 3 nhánh REJECT: RISK (`risk4H ≤ thresRisk`), MOM15 (`pred15 < thres15M`), MOM24 (`pred24 < thres24H`).

### Kết quả mô phỏng phanh động (ValidateBrakeDynamic, 12.469.300 quyết định mức symbol, CHƯA de-overlap)
- PASS=**0.1%**, REJECT=99.9%. Phân rã: **RISK=0.0% | MOM15=3.4% | MOM24=0.0% | EARLY=96.5%**.
- 🟢 PHÁT HIỆN LỚN: **nhánh EARLY (15M + funding bắt tay) gánh 96.5% reject** — đây là lá chắn THẬT,
  KHÔNG phải nhánh RISK (dd4h gần như không đạp qua ngưỡng động).
- 🔴 Realized drawdown 4h (thô, chồng lấn → giá trị tuyệt đối PHÓNG ĐẠI): PASS=-8.4% SÂU HƠN
  REJECT-RISK=-6.1% → log tự kết luận "chặn đúng" là SAI chiều. Cái 0.1% được vào VẪN tụt sâu 8%+.
  → AI filter KHÔNG chặn được cú sập.
- ⚠️ Tool này thiếu de-overlap ở phần phanh; giá trị tuyệt đối không tin, chỉ đọc tương đối.

### Filter ablation (backtest 7 tháng 20251001–20260430)
| mode | trades | PnL | PF | maxDD | worstLoss | nearLiq2 |
|------|--------|-----|----|-------|-----------|----------|
| A (full) | 18848 | 17699 | 1.99 | -10115 | -768.6 | 12 |
| B (bỏ RISK) | 18527 | 13488 | 1.75 | -10128 | -768.6 | 12 |
| C (bỏ MOM24) | =A tuyệt đối | | | | | |
| D (bỏ cả) | =B | | | | | |
- 🟢 **A=C tuyệt đối** → MOM24 (24h) CHƯA BAO GIỜ kích hoạt. Bỏ an toàn hoàn toàn.
- 🟢 Bỏ RISK (B) làm **PnL tụt 17699→13488, PF 1.99→1.75** → nhánh RISK (dd4h) ĐANG lọc lệnh kém
  (+31% PnL). GIỮ. NHƯNG nó **cải thiện PnL, KHÔNG cải thiện đuôi** (maxDD/worstLoss/nearLiq y hệt 4 mode).
- 🔴 **worstLoss -768.6 GIỐNG HỆT cả 4 mode** → cú lỗ tệ nhất + maxDD đến từ thứ filter KHÔNG kiểm soát.
- ⚠️ Ablation 7 tháng này là CỬA SỔ THUẬN (lãi PF 1.99) — backtest đầy đủ 5 năm cho bức tranh NGƯỢC (lỗ).
  Đừng kết luận từ cửa sổ ngắn.

**Chốt: FILTER MODE C** (giữ RISK + MOM15 + EARLY, bỏ MOM24). dd4h giữ qua nhánh RISK (lọc lệnh kém)
dù bản thân model dd4h chỉ là volatility proxy.

---

## 5. CHẨN ĐOÁN NGUỒN LỖ ĐUÔI (RunTailLossDiagnostic, mode C)

### Quy lỗ theo levelChange (theo leg)
- `PREDICT_SYMBOL_TRADE`: -10631 / **8246 leg** = -1.3/leg (bình thường, chi phí kinh doanh).
- `DCA_LEVEL1`: -5293 / **86 leg = -61.5/leg** (gấp ~47 lần!) → 🔴 **DCA khuếch đại lỗ**, đúng martingale.
- worstLeg đơn: DYMUSDT **-768.6 BIG_UP** (cú lẻ, không phải nguồn hệ thống). BIG_DOWN KHÔNG trong top.

### Cụm tệ nhất
- DYM -1233 (4 leg, worstDD **-81%**, giữ **3856h = 160 ngày**); HIPPO -822 (-84.9%); RAVE -266
  (**1 leg, -96.6%**); PIPPIN (1 leg, -97.5%).
- Cụm 1 leg tụt -96% = **coin rác sập không hồi** (vào nhầm coin chết) → vấn đề CHẤT LƯỢNG ENTRY, không
  phải DCA.

### maxDD danh mục — NGUỒN LỚN NHẤT 🔴
- maxDD = **-10115 (-28.9% vốn) lúc 2026-02-06**, có **~325 cụm mở** ngốn margin ~33886 (**96.8% vốn**),
  marginMax 99%.
- → maxDD KHÔNG do 1 cú lỗ, mà do **QUÁ NHIỀU cụm mở cùng lúc** (rủi ro mật độ + tương quan). Hệ "tất
  tay" 99% vốn đúng lúc thị trường sập.

### Ba nguồn rủi ro đuôi KHÁC NHAU
1. **Mật độ (325 cụm, 96.8% margin)** → cần **trần margin danh mục**. LỚN NHẤT.
2. **DCA khuếch đại (-61/leg)** → cần **giới hạn DCA depth**.
3. **Coin rác sập không hồi (-96%, 1 leg)** → cần **chất lượng entry** (không phải phanh).

---

## 6. BACKTEST — VẤN ĐỀ TÁI LẬP & SỰ THẬT 5 NĂM

### Drift (TRACE_backtest_drift.md)
- Lần "chuẩn 10:57" = `TraceData2Test` ĐỌC FILE `../simulator/storage/OrderTestDone.data` (artifact sim
  CŨ, **ngoài git, không tái lập được**). Lần "mới" = chạy tươi Aerospike. → so táo với cam.
- BASE commit `cb50841` (2026-06-01), bộ HPO ĐÃ có sẵn (Configs HPO KHÔNG trôi).
- 🔴 `SLIPPAGE_RATE` từng trôi **0.0005 ↔ 0.003** trên working-tree → backtest không nhất quán.

### Backtest đầy đủ 2021→2026 (3 lần, 3 bộ tham số → 3 kết quả)
- balance-ratio cuối 2026: 0.11 / 0.05 / 0.12. maxDD: -39% / -39% / -35%.
- 🟢 Mẫu XUYÊN SUỐT cả 3 (đáng tin dù số tuyệt đối lệch): **ratio < 1 mọi năm, giảm dần; PnL ròng âm
  gần như mọi năm; 2025 lỗ nặng.** → hệ lỗ qua chu kỳ.
- 🟢 PREDICT_SYMBOL_TRADE payoff > 1 mọi năm (edge entry thật, nghịch lý với hệ lỗ → DCA là thủ phạm).

---

## 7. QUYẾT ĐỊNH ĐÃ CHỐT

- ✅ `SLIPPAGE_RATE = 0.003` cố định (bi quan-an-toàn; hệ vào coin rác + nhồi lúc sập nên slippage thực
  cao; thà ước lượng cao còn hơn thấp). Nên đo slippage thật từ lệnh live 242 sau.
- ✅ `RATE_FEE = 0.002` (2 chân). `APPLY_SLIPPAGE=true`, `BLOCK_INTRABAR_LOOKAHEAD=true`.
- ✅ Bỏ `predReturn24H` khỏi filter (A=C, vô dụng). Filter dùng **mode C**.
- ✅ Look-ahead đã vá (Bước 0): nhánh priceSL==null chỉ đặt SL, không khớp nội nến.
  `BacktestIntegrityGuard.assertProductionGrade()` cắm trong sim, chặn nếu cấu hình ảo.
- 🟡 dd4h: giữ trong filter (nhánh RISK lọc lệnh kém, +31% PnL) NHƯNG model dd4h chỉ là basketVolSpike
  proxy, không chặn được đuôi. KHÔNG train lại dd4h (train ra y cũ).
- 🟡 24h model: bỏ. Giữ insight "giữ lâu → chạm mục tiêu cao".

---

## 8. ĐANG LÀM / VIỆC TIẾP

### Đang chạy: test BREAKER_MODE trên backtest ĐẦY ĐỦ 2021→2026
- `BREAKER_MARGIN_HALT=0.70` (chặn mở mới khi margin/vốn ≥ 70% — nhắm nguồn 1: mật độ 325 cụm).
- `BREAKER_CLUSTER_DD_MAX=-0.30` (ngừng nhồi cụm khi tụt ≥30% — nhắm nguồn 2: DCA khuếch đại).
- KHÔNG force-close (giữ nguyên lý long-only). Phanh chỉ DỪNG MỞ/DỪNG NHỒI.
- So 4 mode OFF/MARGIN/DCA/BOTH, đọc **PnL tổng 5 năm + từng năm + maxDD**.
- **Câu hỏi quyết định**: breaker có biến PnL 5 năm từ ÂM → DƯƠNG không?
    - Có → DCA-không-giới-hạn là thủ phạm, breaker sửa được hệ. Bước ngoặt.
    - Giảm DD mà PnL giữ → đáng áp (an toàn hơn).
    - Giảm DD mà PnL xấu đi → vấn đề SÂU HƠN DCA, phải xem lại chiến lược (không sửa bằng phanh).

### Việc dở (chưa làm)
- Đo LIFT/calibration của chính `pred[0]=P(fail)` tại ngưỡng 0.197 (filter dùng pred[0] nhưng gate đo pfast).
- Gen lại funding pred bằng model 5 lớp mới + lường đổi hành vi filter.
- Bật lại `updateFundingFee` (đang comment → PnL tuyệt đối lạc quan; đuôi ít ảnh hưởng).
- Đo slippage thật từ lệnh live 242.
- Cải thiện chất lượng entry để tránh coin rác sập-không-hồi (nguồn lỗ 3).

---

## 9. ROADMAP — ĐANG Ở ĐÂU

6 bước: (0)look-ahead ✓ | (1)đo IC model ✓ (vượt: validate OOS thật) | (2)ablation AI ✓ (filter
ablation) | (3)mô hình hóa ruin ◄ ĐANG Ở ĐÂY (circuit breaker) | (4)WFO 3 tháng | (5)hợp nhất sim/product.
→ Đang nhảy từ (2) sang (3) sớm vì backtest 5 năm cho thấy RUIN là vấn đề cấp bách nhất. Bằng chứng
dẫn đường, không làm máy móc.

---

## 10. CẠM BẪY & NGUYÊN TẮC (đừng lặp lại)

- ⚠️ **Win-rate VÔ NGHĨA với martingale.** Đo profitFactor/worstSingleLoss/payoff/maxDD/nearLiq.
- ⚠️ **R2 SAI cho label tụ hẹp** (15M quanh 1.6%) — thưởng đoán-trung-bình. Dùng IC de-overlap + LIFT.
- ⚠️ **IC cao ≠ IC thật ≠ dùng được.** 15M IC 0.52 thật nhưng chỉ ở vùng 1%. dd4h IC PASS gate nhưng
  chỉ là volatility proxy.
- ⚠️ **Tách 2 tầng**: đo MODEL (IC) vs đo CHIẾN LƯỢC (backtest). Lỗi tầng nào sửa tầng đó.
- ⚠️ **Cửa sổ ngắn lừa.** Ablation 7 tháng lãi, 5 năm lỗ. Luôn test qua chu kỳ đầy đủ (gồm bear).
- ⚠️ **Backtest phải tái lập**: commit trước khi chạy, ghi commit+giai đoạn+Configs+slippage. Không
  chạy working-tree bẩn. Sim không random → cùng input phải ra cùng output.
- ⚠️ **Mọi backtest qua BacktestIntegrityGuard** (look-ahead off, slippage on, fee 2 chân).
- ⚠️ **decode funding chỉ lấy pred[0]=P(fail)** — đổi thứ tự output model = sai âm thầm.
- ⚠️ **Bump CONFIG_VERSION khi đổi model/predict** (vô hiệu cache HPO). KHÔNG bump cho đổi filter/sim.
- ⚠️ **AI filter KHÔNG chặn được cú sập** — chống sập phải là tầng riêng (breaker theo drawdown thực
  tế), không dựa model dự báo.

---

## 11. HẠ TẦNG (tóm tắt)

- **242** (103.157.218.242): PRODUCT tiền thật + data ticker. Aerospike CE port 3222 — ĐÃ khóa firewall
  (5 rich-rule: 242, 127.0.0.1, 226, VPN 10.8.0.0/24, Oracle 161.118.206.1). SSH 2222 giữ nguyên.
- **226** (103.157.218.226): backtest cá nhân + data predict/market. Aerospike public (Kaggle cần).
- **Oracle VPS** (egress 161.118.206.1): master HPO.
- **Kaggle**: train model GPU + worker HPO.
- Set Aerospike: market predict `ai_pred_market_full_basket_v2`, funding predict `funding_pred_1m_v5`.

---

## 12. FILE CODE ĐÃ TẠO (trong /mnt/user-data/outputs + repo)

Tool validate/diag (Java, chạy 226): `ValidateOldPredictVsRealized`, `ValidateOldPredict3Targets`,
`ValidateBrakeDynamic`, `InspectFundingPredRaw`, `RunFilterAblation`, `RunTailLossDiagnostic`.
Script Kaggle: `diag_market_rulebase_vs_model.py`, `diag_market_3targets.py`.
Prompt cho Claude Code: `PROMPT_filter_ablation`, `PROMPT_gom_audit_bundle`, `PROMPT_circuit_breaker`,
`PROMPT_trace_backtest_drift`, `PROMPT_breaker_full_cycle`.
Repo docs: `CLAUDE.md` (luật), `ROADMAP.md` (6 bước), `PIPELINE.md` (WFO 3 tháng),
`TRACE_backtest_drift.md`, `AUDIT_filter_ablation.md`.