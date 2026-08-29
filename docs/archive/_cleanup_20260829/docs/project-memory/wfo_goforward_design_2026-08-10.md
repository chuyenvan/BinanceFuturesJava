# GO-FORWARD DESIGN — sau chẩn đoán 1m-vs-15m (2026-08-10)

> Nối từ `claude/wfo_diff_15m_vs_1m_2026-08-10.md`. File này = THIẾT KẾ + RUNBOOK, data-backed.

## 0. ✅ UNIVERSE ĐÃ XÁC NHẬN LÀ THỦ PHẠM (test sạch, cùng engine) — 2026-08-10
Dataset `wfo_ds_unf_h4h` = predict UNFILTERED (`wf_pred_ret2wf` 2023-2025) + **CÙNG gate + market + genome frozen
loose_k8 + engine sim 1m** như canon. Chỉ khác đúng 1 biến: universe (unfiltered vs filtered top-10%).

| Quý | canon (filtered 10%) | **UNFILTERED** |
|---|---:|---:|
| 2023Q1–Q4 | +764/+2197/+806/+1326 | +131/+356/+472/+596 |
| 2024Q1 | +7256 | +3134 |
| 2024Q2 | −281 | **+802** |
| 2024Q3 | +1179 | +1527 |
| 2024Q4 | −38 | **+1427** |
| **2025Q1** | **−9906 (DD38%)** | **+1095 (DD11%)** |
| 2025Q2 | +311 | +593 |
| 2025Q3 | −1914 | −555 |
| **2025Q4** | **−3646 (DD48%)** | **+4646 (DD20%)** |
| **TỔNG** | **−1,945** | **+14,225** |

- **+14,225 vs −1,945.** %OOS+ 68.8% (11/12 window trade dương). 2 window thảm hoạ LẬT: 2025Q1 −9906→+1095
  (DD 38→11%), 2025Q4 −3646→+4646 (DD 48→20%).
- **Attribution kín:** so với `g15` (filtered + 15m-cadence = −3354) — bản này khác g15 ĐÚNG một biến universe →
  swing +17.5k = 100% do universe. Tái dựng đúng baseline 2.8 (+14,225 ≈ 2.8 cũ +12,761) nhưng trên **engine 1m**.
- **KẾT LUẬN: 1m KHÔNG hỏng.** Thủ phạm canon thua 2.8 = **filter universe top-10%** (bó vào coin pump-dump dữ nhất),
  bị bundle vào lúc rebuild canonical. Bỏ filter → thắng +14k ngay trên engine 1m. Grid/selector/label/exit đều đã bị loại.
- Nuance: predict là 15m-grid unfiltered chạy trên sim 1m (~15m entry cadence, so công bằng với g15 cũng 15m). Bản
  selector train-1m-unfiltered THẬT (636M, OOM-hard) là bước "làm cho pure-1m", nhưng hiệu ứng universe đã chốt.

## 1. Những gì đã CHỐT bằng số
- Selector 1m KHÔNG hỏng; edge = 15m. Grid KHÔNG phải thủ phạm (g15 −3354). Exit/SL/rank/concurrent làm TỆ HƠN (5 A/B).
- Label `maxFav ≥ 6%` = LƯỚT (chạm). Dùng cho CẢ 2.8 lẫn canon → bệnh nền CHUNG (không phải chỗ khác nhau).
- **Universe filtered top-10% = thủ phạm chính, ĐÃ XÁC NHẬN (§0).**
- predRisk4H brake: signal thật nhưng global-gate cùn → net âm (−5191).

## 2. Bất đối xứng theo horizon (retEnd top8)
| Quý | 4h | 12h | 24h | 72h |
|---|---:|---:|---:|---:|
| 2023Q1 (bull) | +0.08% | +0.31% | +0.72% | **+1.93%** |
| 2025Q1 (crash) | −0.28% | −0.82% | −1.52% | **−4.34%** |
Bull pump giữ&chạy (giữ=lãi); crash pump reverse&dump tiếp (giữ=lỗ nặng hơn). Frozen không thắng cả 2 → entry PHẢI biết regime.

## 3. THIẾT KẾ GO-FORWARD (ưu tiên đã cập nhật sau §0)
### Trụ 1 (cao nhất, ĐÃ CHỨNG MINH) — BỎ FILTER UNIVERSE top-10%
- Đã chứng minh unfiltered thắng +14k. Đi **unfiltered** (hoặc top-30–50% nếu cần cân RAM/tần suất).
- Để có bản **pure 1m unfiltered**: train selector 1m unfiltered = 636M (OOM Kaggle/Oracle). Cách khả thi: (a) top-25%
  1m (146M, fit Kaggle 26GB); (b) train grid THÔ (15m) unfiltered=42.7M rồi forward-fill sim 1m (đã dùng ở §0, work).
  Nhưng ngay cả bản 15m-unfiltered-preds → sim 1m đã +14k → deploy được luôn hướng này.
### Trụ 2 — ĐỔI LABEL "chạm"→"lãi bền" (giảm phụ thuộc regime)
- `maxFav_4h≥6%` → net-return (`retEnd−cost>0`) hoặc sustain (`maxFav≥TP AND maxAdv≥−F`). Giúp model abstain downtrend.
- (Ít cấp bách hơn Trụ 1 vì unfiltered đã cứu 2025; nhưng vẫn nên để robust hơn.)
### Trụ 3 — Gate regime thật (thay predRisk4H mù). Ưu tiên thấp nhất sau khi universe đã cứu phần lớn.

## 4. RUNBOOK cho bản PURE-1M-UNFILTERED (nếu muốn làm chuẩn)
1. Build fat-jar export (Oracle không còn jar có `fundingv2.ExportFeaturesForPythonTool`) — mvn từ repo, scp.
2. Export features UNFILTERED (CE `tool1_export` FF_UNFILTERED=1, FF_GRID_MIN=1) + label 1m khớp grid.
3. Push Kaggle → train selector WF leak-free FIRST_CUTOFF=2023 → predict_wf (1m). ⚠️ 636M OOM — dùng top-25% hoặc per-year memmap.
4. build_ds (gate + market live + predict) → validate → fanout. So vs +14,225 (bản 15m-unfiltered) để xem pure-1m có hơn.
- Disk Oracle 81%; jobstore 226 alive; build_ds jar = binance-fresh-20260809.jar; WFO_CODE_SHA=8741f85.

## 5. Kết luận 1 dòng
**1m không hỏng — filter universe top-10% là thủ phạm (đã chứng minh +14,225 vs −1,945 khi bỏ filter, cùng engine).**
Hướng deploy: universe unfiltered/rộng (Trụ 1, đã work) + optionally label lãi-bền (Trụ 2). Không tinh chỉnh exit (bác 5/5).
