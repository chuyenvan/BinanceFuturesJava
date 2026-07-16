# OVERNIGHT BRIEF — 2026-07-11 (đọc sáng mai)

## 🚀 06:23 — WFO SO SÁNH 2 CHIẾN LƯỢC ĐÃ CHẠY (kết quả sáng có)
Uni chốt: 2 chiến lược **chỉ khác selector pred (funding.bin)**, còn lại giống hệt → apples-to-apples.
- Tìm được 2 nguồn: **maxFav3 (mới)** = `~/selector_pred_out` (16-fold leak-free WF); **ret2 (cũ)** = `~/claudedata/wf_pred_ret2`.
- Build 2 dataset (horizon 4h, IDX=0): `wfo_ds_maxfav3_4h` + `wfo_ds_ret2_4h`. **Verify apples-to-apples: pred.bin (gate) md5 GIỐNG HỆT, market cùng size/count; chỉ funding.bin KHÁC** — chuẩn để so sánh.
- WFO chạy **master-worker 2 worker Xmx8g, tuần tự** (maxFav3 → ret2), trên gate ĐÃ VÁ 2021-2022. PID `~/claudedata/.run/wfo_compare.pid`.

**Sáng kiểm kết quả so sánh:**
```
tail -40 ~/claudedata/wfo_compare.log                 # tiến độ + 2 VERDICT
cat ~/claudedata/wfo_report_maxfav3_4h.md             # verdict maxFav3@4h
cat ~/claudedata/wfo_report_ret2_4h.md                # verdict ret2 (cũ)
```
So 2 verdict (WFE median / %OOS-dương / maxDD) → **chốt maxFav3@4h có hơn ret2 không** → quyết hướng (tối ưu model hay dừng). Verdict do Uni chốt, tôi trình số.
> ⚠️ Caveat cần Uni lưu: (1) ret2 pred có file 2026-01 nghi 1-cutoff (leaky) — chỉ ảnh hưởng cửa sổ 2026 (ngoài vùng phủ), so sánh 2021-2025 vẫn công bằng; B1-validate nên chạy trên ret2 để chắc. (2) predRisk4H=0 (gate thiếu model maxDrawdown4H) áp cho CẢ 2 → không lệch so sánh. (3) so sánh chỉ tính cửa sổ có đủ data (~2022→2025).



## ✅✅ CẬP NHẬT 00:31/05:24 — GATE COVERAGE ĐÃ VÁ + VERIFIED
- **Gate regen XONG** (GATE_REGEN_EXIT=0): 21 fold, **2,717,280 pred**, phủ **2021-04-01 → 2026-05-31** (y2021=396,420 · y2022=525,600 — trước = 0). csv cũ đã backup.
- **Đã load** vào Aerospike `ai_pred_market_gate_wfo` (ns=test): 2,717,280 record.
- **A1 re-check (hệ validate mới): monthsZeroInSpan 26 → 5** (còn 202101/02/03 warmup Q1-2021 + 202606/07 tương lai). monthsWithData 41 → 62. ⇒ **gap 2021-2022 XÓA XONG**, chỉ còn biên warmup (task 156 pre-register cho phép loại).
- ⚠️ **Caveat:** `predRisk4H=0.0` toàn bộ (fold chỉ train Model_Regressor_Return15M, thiếu Model_Regressor_maxDrawdown4H). Cần Uni xác nhận: risk4H có cần cho gate/strategy không? Nếu cần → train thêm model maxDrawdown4H.

## ✅✅✅ 05:27 — DATASET SẠCH ĐÃ DỰNG + RE-VALIDATE
- `ExportWfoDataset` (WFO_SET_PRED=ai_pred_market_gate_wfo) → **`wfo_dataset_clean`** (market 2,774,140 + pred gate mới + funding). Không đè bản cũ.
- Re-validate FULL trên clean: **A1 gate monthsZero 26→5** (chỉ Q1-2021 warmup + 2026 tương lai) ✅; **A2 3/17 cửa sổ biên chưa phủ** (w0 warmup, w15/w16 do funding clean dừng 2025-12). Giao dùng được **2021-04→2025-12 (~w1-w14)**.
- Kết luận: **gap 2021-2022 đã xóa**; còn lại là giới hạn BIÊN (warmup + đuôi funding), không phải bug. Nền data sạch SẴN SÀNG cho WFO.
- Report: `~/claudedata/preflight_full_clean.md`. Dataset: `~/claudedata/wfo_dataset_clean/`.

## LỆNH WFO SẴN (fire khi Uni chốt strategy) — master-worker
```
# reset jobstore + init 17 window (hook preflight CHƯA cắm nên không chặn)
cd ~/java/simulator
java -cp binance-futures-preflight.jar com.binance.chuyennd.ai_ml.wfo.framework.WfoCoordinator reset strategy_window
# N worker song song (RAM: Oracle 23G -> 2 worker Xmx6g AN TOÀN; 3+ rủi ro treo theo AGENTS.md)
for i in 1 2; do WFO_DATA_DIR=~/claudedata/wfo_dataset_clean WFO_SMART_CACHE=1 \
  nohup java -Xmx6g -cp binance-futures-preflight.jar com.binance.chuyennd.ai_ml.wfo.framework.WfoWorker strategy_window > ~/claudedata/wfo_w$i.log 2>&1 & done
# xong: WfoCoordinator report strategy_window -> verdict
```
> ⚠️ funding trong wfo_dataset_clean = selector_pred_out horizon IDX=1 (12h). Nếu "maxFav3@4h" = horizon 0 (4h) hoặc selector label khác → export lại 1 dataset nữa (đổi WFO_SEL_HORIZON_IDX / predDir) rồi WFO song song để SO SÁNH 2 chiến lược.

## CÒN LẠI (cần Uni sáng)
1. Xác nhận **risk4H=0 có chấp nhận** hay phải train model maxDrawdown4H.
2. WFO đọc `wfo_dataset` hay `wfo_dataset_wf`? → rebuild pred.bin (từ gate mới) đúng chỗ: `ExportWfoDataset` với `WFO_SET_PRED=ai_pred_market_gate_wfo`.
3. "cũ" vs "maxFav3@4h" khác nhau ở đâu (funding/WFO_SEL_HORIZON_IDX)? → export 2 dataset → **WFO master-worker cả 2** → so sánh.
→ Có 3 câu này là tôi chạy WFO ra so sánh ngay.

## ✅ CẬP NHẬT 23:30 — Uni chốt HƯỚNG 1, pipeline ĐÃ LAUNCH
Chain overnight đang chạy trên Oracle (PID `gate_chain.pid`), tuần tự (không tranh RAM):
1. **Validate FULL** (PID `preflight.pid`) đang chạy → ghi `~/claudedata/preflight_full_oracle.md`.
2. Chain **đợi validate xong** → backup `wfo_gate_pred.csv` + `wfo_feature_store.csv` → **regen gate pred 2021-2022** bằng `WFOGateRunner` (jar mới có fix task-156: minTrainMonths 24→3, TRAIN_ANCHOR 2021) → log `~/claudedata/gate_regen.log` + tự đếm tháng 2021/2022 cuối log.

**Sáng kiểm (SSH oracle `ubuntu@161.118.212.3` key `id_rsa_chuyennd`):**
```
tail -30 ~/claudedata/gate_regen.log          # coi GATE_REGEN_EXIT + coverage 2021/2022
cat ~/claudedata/preflight_full_oracle.md      # verdict validate 21 check
```
**Nếu gate_regen PASS (2021-2022 có data):** bước tiếp (cần Uni xác nhận 2 chiến lược cũ vs maxFav3@4h):
`LoadWfoGatePredTool` nạp csv → `ExportWfoDataset` rebuild pred.bin → re-run validate A1/A2 (phải PASS) → WFO master-worker 2 chiến lược → so sánh.
**Nếu gate_regen FAIL/OOM:** đọc log; feature store cũ đã backup, khôi phục được.

---


## Việc đã làm đêm nay (verified)
- Build fat jar (kèm hệ preflight 21 validator) trên local → BUILD SUCCESS.
- scp jar lên Oracle: `~/java/simulator/binance-futures-preflight.jar` (99,389,860 B, khớp local).
- Chạy **validate FULL (hệ thống mới)** trên Oracle với dataset WFO thật `wfo_dataset_wf` (fingerprint 15d05f72…), env=oracle, ns=test. PID ghi `~/claudedata/.run/preflight.pid`, log `~/claudedata/preflight_full_oracle.log`, report `~/claudedata/preflight_full_oracle.md`.

## KẾT QUẢ VALIDATE FULL 21 CHECK (23:32, dataset wfo_dataset_wf) — VERDICT FAIL
**PASS (13):** A3 (625 pred symId đều có ticker, 0 ghost), A4 (17 fold), A5 (72 DEAD), C3 (0 trùng ts/symId), E1 (provenance đủ), E2 (md5 3 file khớp), F1, F2, B1 (leak-free: OOS≥cutoff+embargo 72h), B3, B4 (0 coin tương lai/mẫu), D3.
**BLOCK-fail (3):** A1 (gate 24 tháng 2021-2022 = 0), A2 (2/17 cửa sổ w0/w16 chưa phủ), **C2 (134 nến nhảy ≥50%/phút — phần lớn cụm 2025-10-11 04:18-04:33 = crash thị trường thật; cần Uni xử: bad-tick hay biến động thật)**.
**WARN (3):** B2 (shuffle-test chưa chạy — cần Python), D1 (37,653 mốc funding giờ lẻ UTC), D2 (94 ngày <1440 phút, thiếu 96,395 phút).
**infra-error (3):** validator tầng source (C1/C4 đọc .features + 1) không có input trên Oracle → SKIP (task 207 sẽ phân biệt SKIP vs lỗi).

> Đây là verdict FULL đầu tiên của hệ validate mới trên dataset WFO thật — bắt được A1 (gốc rễ), C2 (134 nến sốc), D1/D2 (tz + gap) bằng số. Report đầy đủ: `~/claudedata/preflight_full_oracle.md`.

## KẾ HOẠCH SÁNG (đã gỡ mơ hồ pred-set)
WFO_DATAFLOW §4: dataset chuẩn build pred.bin bằng `WFO_SET_PRED=ai_pred_market_gate_wfo` → **gate regen ĐÚNG là bước 1**. Chuỗi sáng:
1. Verify gate_regen.log: 2021/2022 có data + GATE_REGEN_EXIT=0.
2. `LoadWfoGatePredTool` nạp `wfo_gate_pred.csv` → set `ai_pred_market_gate_wfo`.
3. `ExportWfoDataset` với `WFO_SET_PRED=ai_pred_market_gate_wfo` → rebuild pred.bin (dataset sạch).
4. Chạy lại validate FULL → A1/A2 phải PASS → đóng stamp.
5. **WFO master-worker 2 chiến lược** (cần Uni xác nhận: dataset/WFO_DATA_DIR nào = "cũ" vs "maxFav3@4h mới"; khác nhau ở funding.bin/selector-horizon).
> ⚠️ Cần Uni chỉ rõ: WFO thật đọc `wfo_dataset` hay `wfo_dataset_wf`? Và 2 chiến lược khác nhau ở đâu (WFO_SEL_HORIZON_IDX / selector label)? → tôi rebuild + WFO đúng chỗ.

## PHÁT HIỆN CHÍNH (số cứng — validate mới bắt đúng gốc rễ)
- **A1 BLOCK-FAIL — gate pred trống 2021-2022.** `ai_pred_market_gate_wfo` có 1,795,680 record / 41 tháng, nhưng **24 tháng = 0**: toàn bộ 202101–202112 và 202201–202212 (median 44,640/tháng). ⇒ đúng nguyên nhân WFO zero-trades 2021-2022 (khớp task 156). Funding (selector) chỉ thiếu 2026 gần đây (edge).
- **A2 BLOCK-FAIL — 2/17 cửa sổ không được phủ:** w0 (2021-01→2022-04, gate trống) và w16 (2025-01→2026-04, funding dừng 2026-03-31). Giao data = 2021-01 → 2026-03-31.

## KẾT LUẬN
**Dataset WFO hiện tại CHƯA sạch** (gate pred thiếu hẳn 2 năm đầu). Verdict WFO v6 (FAIL 29.4% OOS-dương) là **hệ quả của lỗi data, không phải chiến lược thua** — không dùng để so sánh/chốt hướng được.

## VÌ SAO KHÔNG CHẠY WFO OVERNIGHT
Chạy WFO 17 cửa sổ trên data này = tái hiện zero-trades 2021-2022 = rác (như v6). Theo luật "validate sạch TRƯỚC WFO", phải sửa coverage trước. Không phí đêm chạy ra kết quả không tin được.

## QUYẾT ĐỊNH CẦN UNI CHỐT SÁNG (2 hướng)
1. **Sửa coverage rồi mới WFO (đúng bài):** regen gate pred 2021-2022 (task 156 — cần train gate per-fold + predict cho 2021-2022; là job modeling, ~vài giờ, nên làm ban ngày có giám sát). Sau đó dataset PASS A1/A2 → WFO 2 chiến lược master-worker → so sánh THẬT.
2. **So sánh sub-range tạm (nhanh, có ngay):** chạy WFO 2 chiến lược CHỈ trên cửa sổ có data (2023-2025, ~w4→w15) → so sánh công bằng trong vùng phủ, chấp nhận bỏ 2021-2022. Cho hướng sơ bộ trong hôm nay trong khi regen gate.

> Khuyến nghị: (2) để có so sánh sơ bộ NGAY sáng (không tốn regen), song song khởi động (1) để có bản đầy đủ. Cần biết: đâu là "chiến lược cũ" vs "maxFav3@4h mới" (config/label nào chọn model) — chưa xác định chắc, cần Uni chỉ hoặc tôi tra tiếp.

## LỆNH SẴN (khi chốt)
- Đọc report validate đầy đủ: `ssh oracle 'cat ~/claudedata/preflight_full_oracle.md'`
- Runbook validate/WFO: `docs/runbooks/PREFLIGHT_RUN.md`.
