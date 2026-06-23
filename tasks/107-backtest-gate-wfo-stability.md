---
id: 107
status: todo
owner: unassigned
updated: 2026-06-23T20:45
touches_live_process: false
writes_242_data: false
resource: oracle
checkpoint: true
max_retry: 1
require_review: true
report: docs/reports/107.md
---

# TASK-107: Backtest gate WFO 1 vòng + chấm V4 + phân tích ỔN ĐỊNH per-fold

## Mục tiêu (1 câu)
Đo gate WFO (model train-lại expanding mỗi 3 tháng, KHÔNG leak) có ổn định và sinh lời
qua từng cửa sổ OOS không — bằng số per-fold, KHÔNG kết luận pass/fail (để người quyết).

## Bối cảnh (đọc trước khi làm)
- WFO gate full 1 vòng ĐÃ CHẠY XONG (2026-06-23). KHÔNG chạy lại WFOGateRunner.
  - File gate (chuỗi pred walk-forward liên tục, mọi phút): `~/claudedata/wfo_gate_pred.csv`
    (1,795,680 dòng + header, format `timestamp,predReturn15M,predRisk4H`, range OOS 2023-01→2026-06).
  - Feature store cache: `~/claudedata/wfo_feature_store.csv` (1.04GB) — KHÔNG đụng, để dành HPO sau.
  - 14 fold expanding: train luôn từ 2021-01, OOS 3 tháng liền kề không chồng lấn:
    fold0 OOS[2023-01,2023-04] ... fold13 OOS[2026-04,2026-06].
- Gate WFO CHỈ cô lập 1 biến = **model gate** (predReturn15M train theo WFO). Các thứ khác GIỮ NGUYÊN:
  - predRisk4H: copy từ set cũ `ai_pred_market_full_basket_v2` (KHÔNG train WFO).
  - Selector chọn coin: engine vẫn dùng `funding_pred_1m_v5` (selector 39c CHƯA wire).
  - Funding fee: KHÔNG tính (Bước 3 HOÃN). balanceBasic cố định 35000.
  - → Backtest này trả lời ĐÚNG 1 câu: "train lại gate mỗi 3 tháng có ổn định/lời không",
    KHÔNG nói về selector/funding fee. Đọc kết quả đúng phạm vi này.
- Fitness chấm: `HPOFitnessCalculatorV4` (Calmar mục tiêu + constraint cứng maxDD65%/giữ>7d 2%/năm-dương 80%).
- Backtest đọc gate từ file qua env `GATE_FILE` (đã có `GoldenBacktest.loadGateFromFile`).
- So sánh baseline: gate cũ FULL (set mặc định) Calmar~3.40, PnL~69k, maxDD~58% vốn (số đã đo bằng MetricDistributionTool).

## Scope
**Trong scope:**
1. Backtest TỔNG 1 lần trên gate WFO: `GATE_FILE=~/claudedata/wfo_gate_pred.csv` chạy GoldenBacktest
   (range FULL 2023-01→2026-06 — đúng range OOS của gate WFO, KHÔNG dùng range có in-sample),
   in PnL/maxDD/Calmar/Sortino/nTrades + verdict V4.
2. So với gate cũ trên CÙNG range 2023-01→2026-06 (GATE_SET mặc định hoặc gate v2) — để A/B công bằng.
3. **Phân tích ỔN ĐỊNH per-fold**: chia kết quả backtest theo 14 cửa sổ OOS quý, mỗi quý đo
   PnL/maxDD/Calmar/nTrades. Xuất chuỗi 14 điểm → thấy ổn định hay dao động dữ dội.
   (Nếu GoldenBacktest chưa tách per-window: chạy 14 lần với START/END mỗi quý, HOẶC thêm cờ chia quý.
   Ưu tiên chạy 14 lần đơn giản, KHÔNG viết lại engine.)
4. Tính các chỉ số ổn định: % quý dương (target tham khảo ≥70%), Calmar median + min + spread,
   worst-quarter maxDD, có quý nào âm nặng không.
5. Ghi `docs/reports/107.md`: bảng tổng + bảng 14 quý + so baseline. KHÔNG kết luận pass/fail.

**Ngoài scope (KHÔNG động vào):**
- KHÔNG chạy lại WFOGateRunner / KHÔNG replay lại / KHÔNG đụng feature_store.csv.
- KHÔNG wire selector, KHÔNG bật funding fee, KHÔNG sửa lõi PnL/sim.
- KHÔNG tự kết luận "WFO pass, đem deploy" — chỉ xuất số, người đọc quyết.
- KHÔNG sửa tham số tuning/genome (đây là WFO model, không phải HPO tham số).

## Acceptance criteria (tự kiểm trước khi báo done)
- [ ] Backtest tổng chạy với GATE_FILE, in đủ PnL/maxDD/Calmar/Sortino/nTrades + verdict V4, không Exception/OOM.
- [ ] Có bảng 14 quý OOS với PnL/maxDD/Calmar/nTrades mỗi quý (số thật, không bịa).
- [ ] So baseline gate cũ trên CÙNG range 2023-01→2026-06 (không so range khác nhau — Calmar phụ thuộc độ dài range).
- [ ] Guard look-ahead/slippage/fee BẬT (GoldenBacktest tự check; nếu tắt → DỪNG, không đo cấu hình ảo).
- [ ] SLF4J, không System.out. Log/output ghi `~/claudedata` hoặc `/d/claudedata`, KHÔNG ổ C.
- [ ] report 107.md có đủ 3 bảng (tổng / 14 quý / so baseline), KHÔNG có câu kết luận pass/fail.

## An toàn
- Chạy TRÊN Oracle (resource nặng), đọc Aerospike read-only + đọc file gate. KHÔNG đụng live/242/ingest.
- Verify đồng bộ 1 mốc trước khi tin: chọn 1 timestamp trong gate file, so predReturn15M với giá trị
  Java predict trực tiếp (nếu nghi lệch) — nhưng gate file do chính WFOGateRunner (Java) ghi nên thường khớp.
- Lệnh chạy nền + redirect file (tránh mất kết quả nếu mất kết nối):
  ```bash
  KEY=/c/Users/pc/.ssh/id_rsa_chuyennd
  ssh -i $KEY ubuntu@161.118.212.3 \
    "cd ~/java/simulator && GATE_FILE=~/claudedata/wfo_gate_pred.csv setsid java -Xmx20g \
     -cp binance-futures-verify.jar com.binance.chuyennd.ai_ml.validation.GoldenBacktest FULL \
     </dev/null > ~/wfo_backtest_107.log 2>&1 &"
  ```

## Ước tính thời gian (đo từ WFO vừa chạy)
- Backtest tổng 1 lần: ~5-10 phút (load market+pred+funding + sim).
- 14 lần backtest per-quý (nếu không tách được trong 1 lần): ~14 × vài phút ≈ 30-60 phút.
- Tổng task: ~1 giờ. KHÔNG cần replay (feature store đã cache).

---

## (Worker điền) Kết quả
<bảng tổng + 14 quý + so baseline; commit nào>

## (Worker điền) Phát hiện ngoài scope
<thấy vấn đề nhưng KHÔNG tự sửa — ghi đây để người quyết>

## (Worker điền) Quyết định phát sinh
<có cần ADR mới không?>
