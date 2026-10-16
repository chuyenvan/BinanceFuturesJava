# MASTER_REVIEW_1016 — rà soát sau khi dừng claw + hướng tiếp theo (MASTER 2026-10-16)

## 1. Kết luận nghiên cứu VZ/E1
- Khám phá 2024: 50 phép thử (ledger). Ứng viên duy nhất đưa đi xác nhận: B4. Q6 NO-GO (465eadb7, md5 e9b6560c).
- Audit A–D (e00adb8a + 6e684232): không có lỗi dữ liệu hay lỗi thực thi. A1 lệch 2,2e-6 do 6 sự kiện 2024-01-01 (lookback tháng 1); exposure ở năm xác nhận 0/0/3 sự kiện. MASTER DUYỆT: không chạy lại Q6, NO-GO giữ nguyên.
- B2: ts là ms ở cả 49 tháng (giả thuyết µs của MASTER là sai). 2025 = 4,19× 2023 do universe ×2,44 và sự kiện/symbol ×1,71, không phải symbol rác.
- C1-AGE: KHÔNG pre-reg. Q2 cho thấy net 240′ giảm theo tuổi (+4,22 → +1,31 %), nhưng hold-to-exit (PnL thật của hệ) lại TĂNG theo tuổi (+3,99 → +6,56 %). 4 417/6 709 chân không rõ tuổi. Lọc theo tuổi không có lợi cho PnL.
- E2 trên sự kiện crash thô: KHÔNG chạy. Cùng lỗi phương pháp với B4 (sự kiện thô ≠ quyết định của hệ).
- ⇒ ĐÓNG chương trình event-study E1 trên kline/metrics Vision. Lake vẫn giữ để tái sử dụng.

## 2. Cấu trúc PnL của hệ (sim gqsf-a1 K24+skipFull, 2021-07 → 2025-11, printDone 3 541 lệnh, ΣPnL +111 079)
- 801 "đợt" (cùng phút vào), chỉ 163 ngày có lệnh (~10 % số ngày).
- Cỡ đợt: median 2, p90 14, max 24. Đợt 13–24 lệnh: 88 đợt, 1 676 lệnh, **41,1 % ΣPnL**, 78 % đợt thắng. Đợt 6–12: 32,4 %. Đợt đơn lẻ: 4,5 %.
- Top-10 đợt = 23,8 % ΣPnL. Worst-10 = −20 406. Đợt tệ nhất: 2022-05-05 (18 lệnh, −4 349), 2025-03-02, 2025-10-11, 2021-12-04.
- Tối đa **83 vị thế mở đồng thời** (p99 70).
- Lợi nhuận trung bình theo margin của đợt ≥13 lệnh: mean +3,2 %, median +5,1 %, min −35,7 %.
- ⇒ Hệ thực chất là MỘT tín hiệu timing mức thị trường (p15 market ≥ thr) × chọn top-K bằng S1. Rủi ro tập trung theo đợt.

## 3. Shadow
- c3b (K24): 25 lệnh từ 10-08, trong đó 24 chân ở 1 tick (10-08 22:20) + 1 lệnh 10-13. Tỉ lệ ngày có lệnh 2/8 ≈ sim (~10–25 %). Không thấy lệch tần suất.
- c3 (K16): 90 lệnh trên 5 ngày lịch (từ 09-05).
- Gate hiện thr 3,0–4,1 % trong khi p15 market ~0,8 % ⇒ n_pass=0 gần như mọi phút. Đây là hành vi thiết kế.
- Hệ quả cho PREREG_SHADOW2_PROMOTION: 4 tuần chỉ có ~3 ngày có lệnh, ~15–30 lệnh ⇒ so PnL shadow↔sim KHÔNG đủ power. Cần so theo TỪNG TICK (p15, q_t, thr, top-K S1, n_pass) trên ~40 000 tick/4 tuần.
- Downtime: 2 đoạn (15:44 ~22–26 s; 18:33 ~78 s), gate ARMED, jar 0c2f4d72 (SHADOW2_DOWNTIME.md).

## 4. Hạ tầng
- OOM: python của claw chạy trong memcg gateway (10–11 GB), lúc đó không có swap. Hiện: swap 8G, gateway MemoryMax=6G, Phase 1 chạy scope riêng 9G (MASTER resume 09:04, pid 271902), mem_watchdog cron */3 (TERM python >4 GB khi avail <1,2 GB), RESOURCE_RULES b3761071.
- V6: N/A chỉ hợp lệ khi đã có V6 PASS cho đúng sha (vz_validate.py:441). 2026-02 V6 thật PASS (00:02).
- liq: collector cron (`~/collect/liq`) chạy tốt (~22,9k event/ngày). Service hệ thống `liq-collector` (code module cũ, `~/derivs_store`) không ghi gì kể từ 10-15 18:33 ⇒ thừa, đề xuất disable (owner).
- Shadow gọi REST có ký `fapi/v2/positionRisk`/`account` từ Oracle mỗi phút ("Error get position") ⇒ rủi ro 418 IP, trái luật "không REST từ Oracle". Đây là hành vi có sẵn từ trước, cần owner quyết (tắt bằng cờ paper hay bỏ qua).

## 5. Hướng tiếp theo (đề xuất, chờ owner chọn)
1. [Release v1 — ưu tiên 1] Parity theo tick: sim với SIM_EXPORT_CANDIDATES trên dữ liệu Vision 10-15→10-22 (file daily), so với log [GATE]/[MAP]/Predict của c3b. Thước: |Δp15|, |Δq_t|, |Δthr|, trùng top-K, n_pass. Cần pre-reg ngưỡng.
2. [Khẩu vị rủi ro — ưu tiên 1] Bảng rủi ro theo đợt: lỗ đợt tệ nhất / equity tại thời điểm đó, số vị thế đồng thời, phân phối DD trong 24h sau đợt lớn. Đây là dữ liệu để chốt trần vị thế đồng thời, size/đợt và ngưỡng kill-switch.
3. [Nghiên cứu, nếu muốn tiếp] Câu hỏi đúng tầng là "đợt nào xấu?" (systemic collapse, ví dụ 2022-05, 2025-10-10) trên 801 đợt hoặc tập ứng viên vz-cand. n nhỏ (88 đợt lớn) ⇒ power thấp; chỉ làm khi có giả thuyết cơ chế mạnh.
4. [Dữ liệu] Liquidation forward tiếp tục thu; đánh giá lại sau ≥3 tháng.
