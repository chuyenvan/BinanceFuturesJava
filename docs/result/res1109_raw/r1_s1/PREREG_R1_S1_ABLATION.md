# PREREG_R1_S1_ABLATION — S1 còn đóng góp gì trong B0, và "B0 như live" (S1FULL) — BẢN NHÁP chờ MASTER duyệt

Ngày soạn 2026-11-10. Tác giả: agent Opus R1. Cơ sở: `~/claude_master/res1109/r1_s1/PHA0.md`.
Trạng thái: **NHÁP**, chưa commit, chưa đẩy kernel. Sau khi MASTER duyệt, commit đúng file này; mọi thay đổi sau đó phải đi bằng ADDENDUM có commit trước khi nhìn số.

## 1. Câu hỏi
- Q1 (owner): trong B0 hiện tại (K24 + skipFull + X14), tầng S1 còn đóng góp gì so với selector net015 có sẵn?
- Q2 (go-live): live r4u3 chấm S1 ở **mọi** tick, còn sim B0 chỉ chấm S1 ở tick mà gate cũ mở (p15 ≥ 0,008, seed 42). Ở các tick còn lại sim giữ thứ tự net015 (PHA0 §2.3: 10–31 % leg PREDICT DEV). Vậy B0 "như live" khác B0 bao nhiêu?

## 2. Arm (chỉ đổi bins selector; jar, profile, gate, exit giữ nguyên B0)
Mọi arm giữ nguyên tập (ts, symId), thứ tự record và **multiset P(win) mỗi tick**. Nhờ vậy thang gate gần như bất biến (PHA0 §1.3).
| Arm | Bins | Ghi chú |
|---|---|---|
| A0 = B0 | DEV `predwf_map_s1a2_x1`; HO `sim-ho26a-bundle` | tái dùng `tsx-x14-*` / `tsx-ho-x14-*` nếu cổng G-P0 đạt |
| **A3 = S1FULL** (chạy TRƯỚC) | S1 chấm **mọi** tick 15′, map lên net015 raw. DEV: 16 model fold WFO dựng lại (`x1_s1_save_all_folds.py`, cổng tái lập: booster trùng bit với `pred_s1a2x1` trên pool cũ). HO: `s1a2x1_cut20251231` predict-only | vừa là arm R1, vừa là "B0 như live" cho test tương đương |
| A1 = NET | net015 raw (DEV `chuyendinh/predwf-g015x26-gate`; HO `predict_wf_2026*` net015 ONNX đóng băng) | "B0 bỏ S1" |
| A2 = RND | hoán vị bộ-4 giá trị trong cùng ts (rng 42), áp lên A0 | sàn |

Leg BIG_DOWN đổi theo bins ở mọi arm, như sim. Báo cáo tách theo level.

## 3. Dữ liệu và chia kỳ
- DEV 2021-07 → 2025-12. Metric chính chấm trên 2022–2025. Kernel DEV dùng `SIM_END_DATE=20251231` và cờ X14 DEV.
- HO 2026-01 → 2026-09: kernel chain riêng, cờ X14 HO. **HO chỉ dùng để MÔ TẢ.** HO đã bị dùng ≥ 5 lần nên không dùng để chọn hay quyết định.
- Seed gate: A0, A1, A3 dùng 8 seed (A1, S7, S13, S21, S99, S123, S777, S2024); A2 dùng 4 seed (A1, S7, S13, S21). Mọi so sánh ghép cặp theo seed.

## 4. Cổng (TRƯỚC khi nhìn số)
- **G-NET0 (nguồn net015):** với mọi fold, multiset P(win) mỗi tick của nguồn NET phải trùng 100 % với A0 (|Δ| ≤ 1e-6). Ở tick A0 không có điểm S1, cell phải bằng nhau 100 %. Trượt ⇒ DỪNG arm A1 và A3.
- **G-S1R (tái lập S1 fold):** với từng fold, model dựng lại cho score trên pool cũ trùng `pred_s1a2x1.parquet` (Spearman 1,0, max|Δ| ≤ 1e-6). Trượt ⇒ DỪNG A3.
- **G-FULL:** A3 có điểm S1 ở ≥ 99 % số (tick, coin) có P(win). Trên pool cũ, A3 phải trùng A0 từng cell.
- **G-P0:** md5 printDone của A0 chạy lại trên ảnh Kaggle hiện tại phải trùng run tham chiếu. Lệch ⇒ chạy lại A0 cả 8 seed.
- **G-SAN:** hoán vị khác thứ tự; NaN giữ nguyên vị trí; sha256 bins trong kernel trùng bản Oracle.
- **G-GATE:** số phút gate PASS của A1/A3 so với A0 lệch ≤ 2 % (kiểm tính bất biến của gate).

## 5. Metric
CAGR22 (2022–2025), maxDD tính trên MTM ngày (`gvz_mtm`: import trước, assert missing = 0), Calmar = CAGR22/|maxDD|, PnL/lệnh, số lệnh/năm, UW, tỉ lệ trùng tập lệnh với A0. Báo tách theo level, theo năm, và ex-2022.

## 6. Tiêu chí (khai trước, không đổi)
- **C1 (chính, A0 − A1, 8 cặp):**
  - "S1 CÒN đóng góp": mean ΔCAGR22 > 0, cận dưới CI95 paired-t > 0, ≥ 6/8 seed dương và ≥ 3/4 năm (2022–2025) dương.
  - "S1 KHÔNG còn đóng góp": TOST, CI90 nằm trong [−1,5; +1,5] pp.
  - Ngoài hai trường hợp trên: "không kết luận".
- **C2 (A0 − A2):** cận dưới CI95 > 0 ⇒ thứ tự selector còn là lever ở K24. C3 (A1 − A2) chỉ báo cáo.
- **C-LIVE (A3 so với A0, 8 cặp; báo cho go-live, không phải phép thử R1):**
  - "TƯƠNG ĐƯƠNG": |mean ΔCAGR22| ≤ 2 pp VÀ |mean ΔmaxDD| ≤ 3 pp.
  - "XẤU HƠN": mean ΔCAGR22 < −2 pp HOẶC maxDD sâu hơn > 3 pp ⇒ MASTER xem xét lùi D.
  - "TỐT HƠN": ΔCAGR22 > +2 pp và DD không sâu hơn quá 3 pp ⇒ chỉ ghi nhận.
  - Các trường hợp khác (vd. CAGR tốt hơn nhưng DD sâu hơn 3 pp): báo "XẤU HƠN về DD".
- **Suy giảm theo thời gian:** Δ(A0 − A1) theo năm 2022…2025 và HO 2026. Chỉ mô tả, 5 điểm không đủ lực để kiểm định xu hướng.
- **Đa kiểm định:** 1 phép chính (C1). C2/C3/C-LIVE khai trước. Nếu dùng thêm phép thứ hai để ra quyết định thì inflate CI ×1,18.
- **Không tune sau khi thấy kết quả;** không đổi K, gate hay exit trong vòng này.

## 7. MDE / nhiễu
sd seed gate @K24+skipFull: 1,37 pp (gate_1004). 8 cặp, sd cặp ~2 pp (giả định) ⇒ CI95 ±1,7 pp, MDE80 ≈ 2 pp; 4 cặp ⇒ MDE80 ≈ 4 pp. Nhiễu retrain S1 (sd ~0,8 pp) không nằm trong phép so vì S1 cố định; nó chỉ dùng để đặt biên TOST.

## 8. Leak và thiên lệch đã khai
1. **Pool S1 dùng nhãn tương lai:** coin chỉ có điểm S1 khi có nhãn g1lite 72h (`x1_ledger.py:42`). Coin thiếu nhãn (sắp delist, thiếu dữ liệu) giữ net015. A0 dính leak này, kể cả HO. A3 chấm mọi coin nên **giảm** leak này. Δ(A3 − A0) vì vậy gồm cả phần "bỏ leak"; độ lớn chưa đo, dự đoán nhỏ.
2. Pool S1 của A0 định theo gate cũ (p15 ≥ 0,008, seed 42) ≠ gate B0.
3. net015 DEV là WFO; net015 HO là ONNX đóng băng (phương án A). Không trộn ONNX đóng băng vào DEV.
4. A3 DEV dùng model fold WFO (cutoff theo quý, purge 72h). Feature hourly join theo floor giờ, đảm bảo causal.

## 9. Thứ tự chạy và compute
1. Oracle (qua `oracle_heavy.lock`):
   - dựng lại 16 fold S1 + G-S1R: khoảng 3–5 h CPU (giả định);
   - predict mọi tick + map lên net015 raw: khoảng 0,5 h;
   - tải `predwf-g015x26-gate` (~0,9 GB) + G-NET0.
   - Đĩa: bins A3 khoảng 1,3 GB + net015 khoảng 0,9 GB; tối đa khoảng 3 GB tạm.
2. HO A3: feature 2026 tới 2026-10 (close 1h từ Vision + OI 2026 đọc Aerospike, chỉ đọc) ⇒ predict cut20251231.
3. Kaggle (tối đa 2 kernel; hiện 1 slot trống):
   - A3: 8 × (0,7 h DEV + 1,7 h HO) ≈ 19 h kernel;
   - G-P0: 2 kernel ≈ 2,4 h;
   - A1: ≈ 19 h kernel;
   - A2: ≈ 10 h kernel.
   - Tổng ≈ 50 h kernel. Ưu tiên A3 với 4 seed trước (≈ 10 h, đủ cho C-LIVE sơ bộ), sau đó 4 seed còn lại, rồi A1, A2.
