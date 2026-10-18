# ISO_RISK — tiêu ngân sách DD bằng size / entry trên nền R1 (kết quả)

Ngày 2026-10-19. Pre-reg `docs/prereg/PREREG_ISO_RISK.md` 5caf3c7f + addendum 1 a4a10881 (nguồn giá MTM).
Jar sim-jar-bcd (sha 108e4c69…), profile K24 + skipFull (+B0OV), 5 arm × 8 seed = 40 kernel Kaggle `iso-*`, parity 40/40 PASS.
Script: `research/analysis/iso_risk_driver.py`, `iso_score_v.py`, `iso_tab2.py`. JSON: `docs/result/iso_risk/`.

## 0. Sự cố đo lường (ĐỌC TRƯỚC)

- Lần chấm 1 (06:34) **VÔ HIỆU**: `reset_rule_score.TICKER` trỏ symlink gãy (ticker bin đã bị xoá) ⇒ MTM mới không có giá
  (`missing` 5–10k chân-ngày) ⇒ DD chỉ còn phần realized, quá nông; OFF lại dùng cache cũ (có giá) ⇒ táo-với-cam.
- Lần 2 (addendum 1): MỌI key tính lại bằng `gvz_mtm.py` (close kline1m Vision). P1: OFF tái lập cache gqsf **trùng tuyệt đối**
  8/8 seed (Δdd 0,0000); P2: `missing = 0` mọi key. ⇒ số dưới đây hợp lệ.
- **Cùng lỗi làm hỏng BURST_COOLDOWN (10-16)**: DD R1 V1/V2/V3 đã báo −9,0/−7,8/−6,6 là SAI. Số đúng ở §2.

## 1. Bảng chính (trung bình 8 seed; cửa sổ CAGR22/DD22 = DEV 2022–2024; ΣPnL & số lệnh = toàn kỳ 2021-07→2025-11, vốn 35k)

| Arm | Mô tả | Lệnh/năm | Tổng lệnh | ΣPnL (USD) | CAGR22 % | maxDD22 % | maxDD toàn kỳ % (tệ nhất) | Calmar22 | UW22 (ngày) |
|---|---|---|---|---|---|---|---|---|---|
| OFF | K24+skipFull (nền) | 742 | 3 551 | 110 047 | 37,0 | −22,5 | −22,6 (−24,7) | 1,65 | 116 |
| R1V1 | R1 cooldown (13,120′) | 438 | 2 182 | 64 000 | 24,2 | −18,6 | −18,7 (−21,6) | 1,30 | 206 |
| B15 | OFF, size ×1,5 | 740 | 3 544 | 151 504 | 45,1 | −24,7 | −24,9 (−26,4) | 1,83 | 121 |
| V1S2 | R1, size ×2 | 435 | 2 160 | 100 006 | 33,4 | −23,3 | −24,3 (−28,1) | 1,44 | 192 |
| V1S3 | R1, size ×3 | 443 | 2 220 | 125 984 | 41,8 | −24,8 | −25,8 (−30,1) | 1,69 | 190 |
| V1S4 | R1, size ×4 | 452 | 2 244 | 151 253 | 47,8 | −26,8 | −27,2 (−31,0) | 1,80 | 196 |
| V1K32 | R1, TOPK 32 | 433 | 1 984 | 47 667 | 21,3 | −20,3 | −20,4 (−21,9) | 1,05 | 210 |

## 2. Luật pre-reg

| Arm | E (DD ≤ 40 % 8/8) | ΔCAGR22 vs OFF | CI99 | GO | ΔCalmar (CI99; seed dương) |
|---|---|---|---|---|---|
| B15 | ✔ | +8,08 | [+7,10; +9,06] | **GO** | +0,18 [+0,06; +0,29]; 8/8 |
| V1S2 | ✔ | −3,61 | [−10,9; +3,7] | NO | −0,21; 2/8 |
| V1S3 | ✔ | +4,81 | [−2,9; +12,5] | NO | +0,04; 5/8 |
| V1S4 | ✔ | +10,80 | [+4,51; +17,09] | **GO** | +0,15 [−0,30; +0,60]; 6/8 |
| V1K32 | ✔ | −15,65 | [−19,6; −11,8] | NO | −0,60; 0/8 |

**Winner theo pre-reg (CAGR22 cao nhất trong GO) = V1S4.**

BURST_COOLDOWN chấm lại (cùng nguồn Vision): R1V1 ΔCalmar −0,35 [−0,64; −0,05] 0/8; R1V2 (13,360′) CAGR 21,3 DD −16,8 Calmar 1,33;
R1V3 (6,360′) CAGR 17,1 DD −15,7 Calmar 1,13 ⇒ **R1 làm Calmar XẤU đi, không phải ×2**. Kết luận NO-GO của BURST_COOLDOWN giữ nguyên,
nhưng ghi chú "Calmar ×2 / DD −9 %" bị rút lại.

## 3. Đọc kết quả (hậu kiểm, không đổi luật)

1. Đòn bẩy thật là **size**, không phải giới hạn đợt. R1 cắt ~41 % lệnh, mất 42 % ΣPnL nhưng DD chỉ nông hơn ~4pp.
2. Size scale **dưới tuyến tính** về DD: ×1,5 size ⇒ CAGR +22 %, DD chỉ +10 % (trần gross/per-coin chặn phơi nhiễm lúc sập).
3. V1S4 thắng theo luật nhưng là "R1 (có hại) + đòn bẩy ×4": ΣPnL ngang B15 (151k) với **ít hơn 37 % số lệnh**, DD tệ nhất −31 vs −26,4,
   UW 196 vs 121 ngày, độ phân tán ΣPnL giữa seed gấp ~2,7 lần (sd 23,6k vs 8,6k), ΔCalmar CI chứa 0.
   B15 trội về mọi chỉ số rủi ro và ổn định (ΔCalmar dương 8/8).
4. Ngân sách DD 40 % mới tiêu ~25–27 %. Thanh khoản: EDGE_ATTR ước impact −3,9 % @35k; size ×1,5–×4 ⇒ chi phí impact tăng ~√size, chưa trừ trong sim.

## 4. Hệ quả & bước tiếp (cần owner)

- Pre-reg định HO4 2026 một lần cho winner (V1S4). Thiếu: kline1m 2026 trên Oracle để tính MTM HO (tải Vision, không phải REST).
- Đề xuất của MASTER: pre-reg mới SIZE_FRONTIER (chỉ size trên OFF: ×1,5/×2/×2,5/×3, ràng DD ≤ 40 %, tiêu chí chính Calmar + DD tệ nhất,
  có stress impact theo EDGE_ATTR), rồi HO4 cho winner — thay vì xác nhận V1S4.
- Errata: BURST_COOLDOWN.md, KILLSW_MENU.md (nhóm B dùng số R1 cũ), memory r1r2_1016 / killsw_1018 / iso_risk_1018.
