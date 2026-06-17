---
id: 104
status: TODO
touches_live_process: false
writes_242_data: false
resource: 226
checkpoint: false
max_retry: 1
require_review: true
---

# TASK-104: A/B test gate 15m (market model) trên golden — gate có làm ra tiền không?

## Câu hỏi cần trả lời
Market model 15m có IC OOS = 0.52 (THẬT, không leak — đã xác nhận). Nhưng IC cao
**không tự động = làm ra tiền**. Phân tích trước (FINDINGS) chỉ ra:
- Label dùng HIGH/đỉnh look-forward → đo "tiềm năng tối đa chạm", model lạc quan hệ thống.
- Market-level smoothing → IC cao do cấu trúc đo, không phải sức mạnh per-trade.
- Model chỉ hơn rule-base ×1.21; edge chỉ ở vùng nảy ~1%.
- Ablation cũ: filter KHÔNG kiểm soát đuôi (worstLoss/maxDD y hệt qua mọi mode).

**A/B test này đo thẳng:** bật/tắt gate 15m ảnh hưởng PnL/maxDD thế nào trên backtest thực
(có slippage/fee/no-lookahead). Rẻ hơn train lại + WFO, trả lời "model có đáng giữ" bằng tiền.

## Vấn đề với ablation hiện tại
`RunFilterAblation` có 4 mode A/B/C/D nhưng **MOM15 (gate 15m) LUÔN GIỮ** ở mọi mode
(chỉ tách RISK + MOM24). Nên ablation cũ KHÔNG đo được tác dụng riêng của gate 15m.
MOM15 xuất hiện 2 chỗ:
1. Nhánh EARLY trong `checkSignalDynamic`: `pred15M < MIN_MOMENTUM_15M && symbolPred > threshold → REJECT`.
2. Check trong `evaluate`: `if (pred15M < thres15M) REJECT`.

## Việc làm

### Bước 1: Thêm mode tách MOM15 vào AIRejectFilter
File: `src/main/java/com/binance/chuyennd/ai_ml/onnx/entry/AIRejectFilter.java`

Thêm flag `checkMom15` điều khiển bởi FILTER_MODE, áp cho CẢ 2 chỗ MOM15:
- Trong `evaluate`: bọc `if (checkMom15 && pred15M < thres15M)`.
- Trong `checkSignalDynamic` nhánh EARLY: bọc điều kiện `pred15M < MIN_MOMENTUM_15M` bằng `checkMom15`.

Quy ước mode MỚI (mở rộng, KHÔNG phá A/B/C/D cũ):
- `A` = hiện trạng (giữ cả RISK + MOM24 + MOM15) — baseline live.
- `E` = TẮT MOM15 (bỏ gate 15m, giữ RISK + MOM24) — đây là "gate-off" cần đo.
- `F` = CHỈ MOM15 (tắt RISK + MOM24, giữ gate 15m) — đo gate 15m đứng một mình.
- `OFF` = tắt hết filter (đã có? nếu chưa, thêm) — sàn so sánh tuyệt đối.

```java
String mode = Configs.FILTER_MODE;
boolean checkRisk  = !("B".equals(mode) || "D".equals(mode) || "E".equals(mode) || "OFF".equals(mode));
boolean checkMom24 = !("C".equals(mode) || "D".equals(mode) || "E".equals(mode) || "OFF".equals(mode));
boolean checkMom15 = !("E".equals(mode) || "OFF".equals(mode));
// F: chi giu MOM15 -> checkRisk=false checkMom24=false checkMom15=true
if ("F".equals(mode)) { checkRisk = false; checkMom24 = false; checkMom15 = true; }
```

Compile `--release 11` PASS trước khi chạy.

### Bước 2: Chạy ablation trên 3 golden range
`RunFilterAblation` hiện hardcode START=20251001 END=20260430. Cần chạy 3 range golden
(khớp ADR-0006 regime): chỉnh START/END hoặc thêm args. 3 range:
- **CRASH:** 2022Q2 (LUNA/FTT) — đuôi nặng nhất, test gate có chặn được sập không.
- **BULL:** 2023Q4 — thị trường lên, test gate có bỏ lỡ sóng không.
- **RECENT:** 20251001→20260430 (range hiện tại) — gần nhất.

Mode chạy: **A, E, F, OFF** (4 mode × 3 range = 12 lần). Mỗi lần in: PnL, maxDD (true),
worstLoss, numTrades, return/maxDD ratio, #lệnh bị gate-15m reject.

```bash
# Trên 226 (đọc Aerospike, không đụng live). Chỉnh MODES + range trong RunFilterAblation.
ssh -i /c/Users/pc/.ssh/id_rsa_chuyennd -p 2222 root@103.157.218.226 \
  "cd /home/chuyennd/java/simulator && java -Duser.timezone=Asia/Ho_Chi_Minh -Xmx24g \
   -cp <jar> com.binance.chuyennd.ai_ml.validation.RunFilterAblation 2>&1 | tail -40"
```

⚠️ PRE-FLIGHT: RunFilterAblation đã có guard — nếu `BLOCK_INTRABAR_LOOKAHEAD=false`
hoặc `APPLY_SLIPPAGE=false` hoặc `RATE_FEE<=0` → DỪNG. KHÔNG đo cấu hình ảo.
⚠️ funding-pred phải có data trong range (nếu rỗng → symbolPred null → nhánh EARLY mất tác dụng,
lệch live; report cũ cảnh báo điều này). Kiểm trước khi tin kết quả CRASH/BULL.

### Bước 3: Đọc kết quả — tiêu chí "gate 15m đáng giữ"
So **A (có gate) vs E (tắt gate)** trên cả 3 range:
- **Gate đáng giữ NẾU:** A có maxDD/worstLoss tốt hơn E rõ rệt (chặn đuôi) HOẶC return/maxDD ratio A > E.
- **Gate KHÔNG đáng giữ NẾU:** A ≈ E về maxDD/worstLoss (gate không chặn đuôi, khớp FINDINGS cũ)
  và PnL A < E (gate chỉ bỏ lỡ lệnh tốt).
- **F (chỉ gate 15m):** xem gate đứng một mình có cứu được gì so OFF không.

### Bước 4: Ghi report + kết luận
Tạo `docs/reports/104.md`: bảng 4 mode × 3 range (PnL/maxDD/worstLoss/nTrades/ratio),
kết luận gate 15m đáng giữ / nên thay label / nên bỏ. KHÔNG tự quyết — báo user.

## An toàn
- Chạy TRÊN 226, đọc Aerospike read-only. KHÔNG đụng live/ingest/Redis.
- KHÔNG sửa tham số tuning (chỉ thêm FILTER_MODE flag).
- Guard look-ahead/slippage/fee phải BẬT (RunFilterAblation tự check).
- SLF4J, không System.out.

## (CCD điền)
- Bước 1: AIRejectFilter thêm mode E/F/OFF — compile PASS?
- Bước 2: bảng kết quả 4 mode × 3 range
- Bước 3: A vs E so sánh (maxDD, worstLoss, PnL, ratio)
- Bước 4: kết luận
