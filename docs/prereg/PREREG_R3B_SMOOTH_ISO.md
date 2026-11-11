# PREREG_R3B_SMOOTH_ISO — p15 làm mượt (MEAN15/MEAN60) ở CÙNG số lệnh (iso-count) — MASTER duyệt 2026-11-11

Trạng thái: **PRE-REG, MASTER duyệt 11-11 (nháp sha256 2a48ba42).** Chỉ chạy SAU khi G3 (họ R3) xong 4 seed đầu + chấm futility; mọi kernel dùng jar đã vá mapper-từ-file (không phụ thuộc Aerospike Oracle). Ứng viên v1.3; không đụng v1.2/go-live. Họ đa kiểm định RIÊNG (m = 2), tách khỏi họ R3 (b901016e).
Người viết: agent Opus R3. Code: Opus, key mặc định OFF, OFF byte-identical, unit test.

## 0. Khai báo trung thực (HARKing)
- ĐÃ THẤY trước khi viết: P1 R3 (f8ff9a5c) — G1 MEAN15 quota 1,70 / Jaccard 0,24; G2 MEAN60 quota 1,64 / 0,17 (LOẠI theo luật quota, CHƯA chấm PnL); R2 proxy timing (trễ trung vị 9′ / 34′, Jaccard phút 0,52 / 0,28; không PnL); bảng PnL theo r/q của GATE_SMART p0a; số leg (không PnL) của G3 seed 42 (3 256 vs B0 3 935).
- Đo cơ chế quota (§6, chỉ đếm) ĐÃ chạy trước nháp này.
- KHÔNG thấy PnL/MTM nào của MEAN15/MEAN60.
- **Prior ÂM:** ENTRY_CONFIRM FAIL (trễ vào = mất đoạn bật đầu, −27,7k/seed); R4_CADENCE (selector 15′: Calmar −24 %); proxy trễ 9′/34′; GATE_ABLATION H60 NO-GO. Kỳ vọng: NO-GO là khả năng cao, MEAN60 thấp hơn MEAN15.

## 1. Câu hỏi
Ở CÙNG số ô pass như B0 (hiệu chỉnh trên năm riêng 2022), thay p15 điểm bằng trung bình causal của p15 trong nhánh PREDICT có làm Calmar MTM 2023–2025 tốt hơn B0 không. (Tách "đổi tín hiệu" khỏi "thêm lệnh" — P1 cho thấy pct gốc làm quota +64–70 %.)

## 2. Arm (tham số CỐ ĐỊNH)
- A0 = B0 `n4f-b0-*` (K24 + skipFull + X14, A1, KILLSW_A40; pred 8 seed như PREREG_R3_GATE_FAMILY §3).
- **B1 MEAN15**: p̃(t) = mean p15 trên [t−14′, t] (gồm t, thời gian thật), cần ≥ 12/15 phút; thiếu ⇒ cell không có p̃ ⇒ không nạp buffer, không pass. Định nghĩa y G1.
- **B2 MEAN60**: như B1, [t−59′, t], cần ≥ 48/60. Định nghĩa y G2.
- p̃ chỉ thay p15 trong nhánh PREDICT_SYMBOL_TRADE (r, buffer, so ngưỡng); DCA_LEVEL1, điều kiện "có pred", BIG_DOWN giữ p15 điểm. Một buffer r (từ p̃), q_h như B0 (90d, đầu giờ, warm-up 7d), pct = **pct_B** hiệu chỉnh §3. Trung bình float64 → float32.

## 3. Hiệu chỉnh pct (thủ tục cố định, CHỈ năm 2022, CHỈ ĐẾM)
- Công cụ: `gate_offline` (như P1: pred n4f-b0 8 seed, held = printDone n4f-b0-*, không mô hình skipFull/U_MAX). Cấm mở pnl/profit/equity/MTM.
- Mục tiêu: T = Σ 8 seed số cell pass A0 năm 2022 (+07, 2022-01-01..2022-12-31). Một pct_B CHUNG 8 seed cho mỗi arm (để triển khai được 1 giá trị).
- Tìm nhị phân trên pct (double) ∈ [0,99990; 0,999999]; mỗi bước ép float32 (`np.float32`, = `Float.parseFloat` của chuỗi ghi ra), đếm N(pct) = Σ 8 seed cell pass arm năm 2022 (buffer/q dùng toàn lịch sử từ 2021-07 như sim). Dừng khi |N/T − 1| ≤ 0,05; tối đa 40 vòng; không hội tụ ⇒ arm LOẠI.
- Ghi `iso_r3b.json` (pct_B float32 dạng chuỗi 9 chữ số, N, T, từng seed, quota 2023–25 mô tả) + commit TRƯỚC mọi push Kaggle. Không hiệu chỉnh lại sau đó.
- Luật (MASTER chốt 11-11): quota 2023–25 (cell pass offline, median 8 seed, arm/A0) ngoài [0,75; 1,25] ⇒ arm LOẠI (nhất quán luật quota họ R3; không chỉnh tham số).

## 4. Đánh giá (Pha 1, Kaggle)
- Sim y cấu hình A0, 8 seed ghép cặp `n4f-b0-*`, chạy 2021-07-01→2026-09-30 như A0; **chỉ chấm 2023-01-01..2025-12-31 (+07)**; 2022 = năm hiệu chỉnh, KHÔNG chấm. HO 2026: chỉ yêu cầu cùng dấu.
- Hợp lệ: G0 jar mới key OFF byte-identical `n4f-b0-a1` (printDone + equity_summary); MTM `gvz_mtm`/kernel MTM với `missing == 0` và đối chứng; jar STUB + jar_sec_check ×2; báo số pass sim vs offline (lệch >3 % ghi, không chỉnh).
- **Tiêu chí GO (tất cả):**
  1. Mean ΔCalmar MTM 2023–25 (arm − A0, ghép cặp) > 0; t ghép cặp một phía, **Holm m = 2**, α = 0,05.
  2. ≥ 7/8 seed ΔCalmar 2023–25 > 0.
  3. Mean ΔmaxDD MTM 2023–25 ≥ −2 pp.
  4. HO 2026: mean ΔROI cùng dấu với ΔCalmar 2023–25.
- **Futility sau 4 seed** (42/7/21/99 chạy trước): arm có ≥ 2/4 seed ΔCalmar ≤ 0 ⇒ DỪNG (không thể đạt 7/8).
- Phụ (báo cáo, không cổng): DSR (N_trials gồm cả họ R3 và các biến thể gate trước), CAGR 2023–25, UW, lệnh/năm, PnL/lệnh, trễ đợt, crowd-out, tỉ lệ leg tick net015 (sim lai S1).
- Hai arm cùng GO ⇒ chọn ΔCalmar lớn hơn. Không thêm arm, không đổi W/minCov/pct sau khi thấy số.

## 5. Ràng buộc
- Sim lai S1 (`selection_mismatch_1109`): giả định ảnh hưởng như nhau; báo tỉ lệ leg tick net015 theo arm, lệch > 5 pp ⇒ "có điều kiện".
- GO chỉ triển khai sau khi B0 "như live" (R1-A3) xác nhận; baseline đổi đáng kể ⇒ chạy lại arm GO trên baseline mới.
- **Mapper:** R3b dùng jar có nhánh `SYMBOL_MAPPER_FILE` (dump global_id_map khoá phiên bản, sha256 ghi trong manifest) và kernel `enable_internet=false`; G0 của jar đó phải byte-identical `n4f-b0-a1`.

## 6. Đo cơ chế quota +70 % (ĐÃ CHẠY, chỉ đếm; `research/r3_gate/quota_mech.py` → `res1109/r3_gate/quota_mech.json`; S42, S7; DEV 2022–25)
| | danh nghĩa (1−pct)·N | pass thật | pass nếu q gồm CẢ giờ hiện tại (chẩn đoán, nhìn trước) | giờ có pass | pass/giờ (trung vị) | % pass trong giờ ≥10 pass |
|---|---|---|---|---|---|---|
| A0 S42 | 2 280 | 2 621 | 2 368 | 267 | 4 | 82,9 % |
| MEAN15 S42 | 2 280 | 4 433 | 2 896 | 205 | 8 | 91,3 % |
| MEAN60 S42 | 2 280 | 4 760 | 3 094 | 173 | 11 | 94,1 % |
| A0 S7 | 2 277 | 2 622 | 2 372 | 254 | 4 | 83,5 % |
| MEAN15 S7 | 2 277 | 4 154 | 2 844 | 195 | 8 | 90,9 % |
| MEAN60 S7 | 2 277 | 3 982 | 2 716 | 154 | 11 | 93,4 % |
Đọc: q đóng băng trong giờ giải thích ~70 % phần vượt danh nghĩa của MEAN15/60 (S42: +2 153 → +616) — tín hiệu dai ⇒ cả giờ đợt vượt q cũ; phần còn lại (+27–36 %) dồn vào 2024 (MEAN15 S42 2024 1 819 vs A0 761) ⇒ đuôi không dừng (suy đoán). Hệ quả thiết kế: iso-count bằng pct cao hơn làm giảm số giờ mở, KHÔNG sửa cơ chế trong-giờ ⇒ pass vẫn dồn cụm hơn A0 (báo mô tả §4).

## 7. Compute (ước)
- Hiệu chỉnh §3 (Oracle, flock): cache theo seed (cây top-J dùng lại khi chỉ đổi pct) ⇒ ~10 s/seed/vòng × 8 × ≤ 40 vòng; RSS ~4 GB ⇒ ≤ 1 h.
- Code: key `SIM_GATE_P15_SMOOTH=W:minCov` (tái dùng `smoothedP15` của R3-G3, r3_wt 12f3b1b6) + test; jar STUB mới.
- Kaggle (1 slot): G0 1 + 2 arm × 8 = 17 kernel × ~45′ (r3g0-a1 2 593 s) ≈ 13 h wall; MTM 2 kernel ~2 h. Futility có thể cắt ~25–50 %. Thứ tự sau R3-G3 và R1-A3.

## 8. Rủi ro
Underpowered + prior âm; HARKing (§0); iso-count hiệu chỉnh trên 2022 có thể lệch ở 2023–25 (đuôi không dừng — §6); pass dồn cụm hơn ⇒ va trần U_MAX/skipFull khác A0 (số lệnh sim có thể lệch xa offline, như G3 s42 −17 % leg); triển khai live cần p15 mỗi phút + rehydrate W phút sau restart; pct_B mới ⇒ seed buffer/parity phải dựng lại.
