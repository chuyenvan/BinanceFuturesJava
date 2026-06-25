# TASK-108: Generate selector predict-only (tách extract, tăng tốc cho WFO)

- **status:** todo
- **Milestone:** B4 (selector WFO) — [docs/ROADMAP.md](../docs/ROADMAP.md)
- **Ưu tiên:** trung bình — chỉ cần TRƯỚC khi chạy WFO nhiều vòng (mỗi vòng phải generate lại set).

## Mục tiêu (1 câu)

Tách `GenerateSelectorPredictionsTool` thành đường **predict-only**: đọc feature đã export sẵn (ff_*.bin từ `ExportFeaturesForPythonTool`) thay vì tính lại `extractFeatures` mỗi mốc, rồi chỉ chạy 4 ONNX → ghi set. Mục đích: bỏ phần nặng nhất (extractFeatures ~2-9s/ngày) để generate nhanh hơn nhiều khi WFO buộc generate lại set sau mỗi lần train model.

## Bối cảnh — vì sao cần (đo được trong TASK-109)

- Generate hiện tại **vừa extractFeatures vừa predict** trong cùng vòng: mỗi mốc phút tính lại 40 Tool1 + cross-sectional #33-35 + OI #41-45 rồi mới `predictAll4`. Đo trên Oracle: `extract ~2-9s` (nặng nhất, CPU-bound, ~95% thời gian), `infer ~1.4-2.4s`, `read ~0.3-1s`. Full 2021→2026 mất ~8h.
- Đã có sẵn ff features export (`ExportFeaturesForPythonTool` → ff_*.bin) và **đã validate generate khớp ff 45/45 feature, max diff <8e-6** (TASK-109, `compare_v2.py`). Nghĩa là feature export = feature generate → có thể đọc lại thay vì tính lại.
- WFO sẽ train lại model nhiều vòng → mỗi vòng cần generate lại set predictions. Nếu mỗi lần ~8h thì WFO rất chậm. Predict-only (đọc ff + chỉ ONNX) ước tính nhanh hơn nhiều lần (bỏ extract, chỉ còn đọc + infer).
- Kaggle KHÔNG hợp cho generate đọc-226-per-ngày (latency mạng Kaggle→226 ~7.5s/đọc, gấp ~11x Oracle 0.7s — đo trong TASK-109). Predict-only đọc ff (file/dataset local) né được vấn đề mạng này → nếu sau muốn đẩy Kaggle 5-CPU thì predict-only mới khả thi.

## Scope

**Trong scope:**
- Thêm chế độ predict-only cho `GenerateSelectorPredictionsTool` (hoặc tool mới `GenerateSelectorFromFeaturesTool`): đầu vào là ff_*.bin (40 Tool1) + OI export (oi_percoin.bin) đã có, ghép đúng 45 feature theo thứ tự `convertFeaturesToArray` + cross-sectional #33-35 + OI #41-45, chạy 4 ONNX, ghi set như hiện tại.
- ⚠️ Cross-sectional #33-35 (fundingRankCS, volumeZRankCS, momentumRankCS) phải rank TRONG tập đã `EntrySignalFilter.selectCoins` mỗi mốc — y hệt đường extract hiện tại (đừng rank trên toàn bộ). Đây là điểm dễ sai nhất.
- Verify byte-khớp: predict-only vs đường extract hiện tại trên cùng 1 ngày test → P(win) phải khớp (~0, vì cùng feature cùng model).

**Ngoài scope (KHÔNG động vào):**
- KHÔNG đổi `extractFeatures`/`FundingDataCollectionManager` (đường extract hiện tại giữ nguyên làm chân lý + để generate realtime live nếu cần).
- KHÔNG đổi model, train, hay engine wiring.
- KHÔNG bắt buộc đẩy Kaggle trong task này (chỉ mở đường; quyết định Kaggle để task riêng nếu cần).

## Bối cảnh cần biết — file/module

- `src/main/java/com/binance/chuyennd/ai_ml/onnx/funding/GenerateSelectorPredictionsTool.java` — vòng extract+predict hiện tại (tham chiếu thứ tự feature, cross-sectional, OI provider, cách ghi set qua `saveSelectorPredictions1M`).
- `src/main/java/com/binance/chuyennd/ai_ml/features/export/fundingv2/ExportFeaturesForPythonTool.java` — sinh ff_*.bin (40 Tool1). Định dạng record 170B: `>i8 ts + >i2 symId + 40×>f4`.
- `src/main/java/com/binance/chuyennd/ai_ml/features/export/fundingv2/ExportFundingOiPerCoin.java` — sinh oi_percoin.bin (5 OI từ Aerospike 226). Record 30B: `ts,symId,5×f4`.
- `SelectorOnnxInferenceManager` — `predictAll4` (4 ONNX). `SelectorOiProvider` — OI provider hiện tại (đường extract).
- `ml/funding_selector/compare_v2.py` — script đã validate generate khớp ff/OI 45/45; tái dùng để verify predict-only.
- Thứ tự 45 feature: 40 Tool1 (theo `convertFeaturesToArray`) + #33-35 cross-sectional + #41-45 OI (oi_delta24h, oi_z, ls_global, ls_toptrader, taker_buy). Chi tiết trong TASK-109.

## Acceptance criteria (Code phải tự kiểm trước khi báo done)

- [ ] Predict-only đọc ff_*.bin + oi_percoin.bin (KHÔNG gọi extractFeatures), ghép đúng 45 feature, chạy 4 ONNX, ghi set.
- [ ] Cross-sectional #33-35 rank trong tập `EntrySignalFilter.selectCoins` mỗi mốc (khớp đường extract).
- [ ] Verify: trên ≥1 ngày test, P(win) predict-only KHỚP đường extract hiện tại (diff ~0, cùng feature+model). Dùng compare hoặc so set trực tiếp.
- [ ] Đo tốc độ: report s/ngày predict-only vs extract hiện tại (kỳ vọng nhanh hơn nhiều lần do bỏ extract).
- [ ] SLF4J log, không System.out. SLF4J/Logback.

---

## (Code điền) Kết quả

<tóm tắt đã làm gì, commit nào>

## (Code điền) Phát hiện ngoài scope

<thấy vấn đề nhưng KHÔNG tự sửa>

## (Code điền) Quyết định phát sinh

<ADR mới nếu có>
