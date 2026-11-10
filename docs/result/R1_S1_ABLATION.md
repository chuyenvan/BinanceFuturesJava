# R1 — kết quả (S1 ablation và "B0 như live")

Prereg: `PREREG_R1_S1_ABLATION.md` (44acf9cd), ADDENDUM 1 (ce321bd3), ADDENDUM 2 (93b60422). Số liệu chi tiết nằm ở `research/r1_s1/r1_clive.json` và `orch_state.json`.

## 1. C-LIVE: A3 (S1FULL + A1 hạ hạng = B0') so với A0 (B0), 8 cặp seed, DEV 2022–2025

| | A0 (B0) | A3 (B0') | Δ (A3 − A0) | CI95 paired-t của Δ |
|---|---|---|---|---|
| CAGR22 (%) | 39,49 | 37,72 | −1,77 | [−2,72; −0,83] |
| maxDD MTM 2022–25 (%) | −22,55 | −22,72 | −0,18 | [−0,98; +0,62] |
| Calmar22 | 1,76 | 1,67 | | |
| UW MTM 2022–25 (ngày) | 120 | 164 | | |
| Số lệnh/năm | 737 | 740 | | |

Seed dương: 1/8. ΔPnL trung bình theo năm (USDT): 2022 −1 993, 2023 +1 598, 2024 −2 621, 2025 −4 766. Tập lệnh A3 trùng A0 trung bình 55 %.

**Kết luận theo luật đã pre-register: TƯƠNG ĐƯƠNG** (|mean ΔCAGR22| = 1,77 ≤ 2 pp và |mean ΔDD| = 0,18 ≤ 3 pp). MASTER đọc theo đúng luật và không đổi luật sau khi đã thấy số.

**Ghi rõ:** A3 thấp hơn A0 một cách có ý nghĩa thống kê.
- ΔCAGR22 = −1,77 pp, CI95 [−2,72; −0,83], 1/8 seed dương.
- Phép thử tương đương dạng TOST ±2 pp sẽ không đạt.

**Từ 2026-11-10, A3 (B0') là kỳ vọng chính thức cho live:** CAGR22 37,7 %, maxDD −22,7 %, Calmar 1,67, UW 164 ngày (DEV 2022–2025, chưa trừ chi phí D10/D11).

## 2. Cổng
- **G-S1R:** 16/16 fold tái lập bit-exact.
- **G-NET0, G-SAN:** PASS.
- **G-FULL:** PASS theo ADD2 (mẫu số chỉ tính key có trong bin net015).
- **sha bins trong kernel:** trùng ở cả 8 seed.
- **G-P0:** PASS. Chạy lại A0 seed A1 trên ảnh Kaggle hiện tại cho md5 printDone trùng `tsx-x14-a1`, nên dùng lại được A0.
- **G-MTM:** PASS (maxdiff 0). Giá kline1m Vision tải lại từ Kaggle `vz-kline1m-*` (sha khớp README, chỉ giữ ts/sym/close) tái lập đúng cache MTM tsx.
- **G-GATE (≤ 2 %): TRƯỢT**, chỉ 1/8 seed đạt.
  - Phút pass theo GATE-RATIO lệch −2,8 % đến +2,8 %.
  - n_pass lệch −16 % đến +2,8 %.
  - Prereg không đặt luật dừng cho cổng này. Kết quả cho thấy thứ tự S1 làm thay đổi một phần tần suất gate, và phần đó nằm trong Δ.

## 3. T2 (tương đương logic từng khối)
- **T2a — exit:** ExitReplayDevMain chạy trên toàn bộ 151 ngày / 3 220 leg của seed `tsx-x14-a1`, cấu hình bằng profile sim.
  - Symbol-ngày chỉ có 1 leg (2 741): 0 lệch quyết định arm/SL/time-stop/X14.
  - 33 lệch, tất cả ở symbol-ngày nhiều leg. Đây là giới hạn của harness: leg vào lại được bơm vào cụm live đang mở mà không reset stop.
  - Thoát trailing: 2 232/2 259 cùng phút.
  - Giá thoát live thấp hơn sổ giấy trung bình 0,40 % (D11).
- **T2c — sizing và DCA:** property test với 1 500 trạng thái.
  - 5 885 leg có size trùng bit với chuỗi sim.
  - Trần 4,5 % không ràng buộc ở profile B0.
  - BUDGET_SMALL: 5 lần (D9).
  - DCA due/not-due: 4 417/4 417 trùng.
- **T2b:** bỏ (xem plan EQUIV §5).

## 4. C1/C2/C3: A1 NET (net015 thuần, 8 seed) và A2 RND (hoán vị trong cùng ts, 4 seed), DEV 2022–2025

Script `research/r1_s1/r1_score2.py`, kết quả `r1_c1c2.json`. Mọi kernel đều đã validate (sha bins trong kernel, md5 printDone, `ok`, chạy tới 20251230).

| Arm | CAGR22 (%) | maxDD22 (%) | Calmar22 | UW22 (ngày) | Lệnh/năm |
|---|---|---|---|---|---|
| A0 = B0 (8 seed) | 39,49 | −22,55 | 1,76 | 120 | 737 |
| A3 = B0' như live (8 seed) | 37,72 | −22,72 | 1,67 | 164 | 740 |
| A1 = NET (8 seed) | 31,59 | −24,32 | 1,30 | 155 | 801 |
| A2 = RND (4 seed) | 13,63 | −33,42 | 0,41 | 559 | 926 |

| So sánh | mean ΔCAGR22 (pp) | CI95 | CI90 | Seed dương | ΔmaxDD (pp) |
|---|---|---|---|---|---|
| C1: A0 − A1 | +7,90 | [6,55; 9,24] | [6,82; 8,97] | 8/8 | +1,77 [0,78; 2,76] |
| C2: A0 − A2 | +25,18 | [23,61; 26,74] | | 4/4 | +10,29 |
| C3: A1 − A2 (chỉ báo cáo) | +17,55 | [14,81; 20,29] | | 4/4 | +9,37 |

Δ lợi nhuận năm A0 − A1 (pp, trung bình 8 seed): 2022 +3,6; 2023 +13,5; 2024 +8,3; 2025 +7,9. Δ PnL (USDT) tương ứng: +1 480, +7 093, +9 972, +13 942.

**Kết luận theo luật đã pre-register:**
- **C1: "S1 CÒN ĐÓNG GÓP".** Đủ cả bốn điều kiện: mean > 0, cận dưới CI95 > 0, 8/8 seed dương (≥ 6/8), 4/4 năm dương (≥ 3/4).
- **C2: "THỨ TỰ SELECTOR CÒN LÀ LEVER Ở K24"** (cận dưới CI95 > 0).

**Lưu ý bắt buộc khi đọc kết quả:**
1. **G-GATE trượt ở cả 12/12 kernel.**
   - A1 so với A0: phút pass theo GATE-RATIO tăng 6–10 %, n_pass tăng 2–36 %.
   - A2 so với A0: phút pass tăng 17–28 %, n_pass tăng 51–120 %.
   - Như vậy giả định "giữ multiset thì gate bất biến" (PHA0 §1.3) không đúng. Δ ở C1/C2 gồm cả phần do thứ tự coin, cả phần do tần suất gate thay đổi. Prereg không đặt luật dừng cho G-GATE nên kết luận vẫn giữ, nhưng không được hiểu Δ là "chỉ do thứ tự".
2. **A0 có dính leak nhãn tương lai ở pool S1** (prereg §8.1). A3 giảm phần leak này. Thứ tự đo được là A0 > A3 > A1 > A2. Phần A0 hơn A3 (1,77 pp) có thể một phần đến từ leak. Phần A3 hơn A1 (khoảng 6,1 pp, chênh hai trung bình, không phải phép thử pre-register) không dính leak đó.
3. Nhiều phép so sánh: chỉ C1 là phép chính. C2/C3 đã khai trước. Không phép nào dưới đây dùng để ra quyết định.

**Suy giảm theo thời gian (chỉ mô tả, 4 điểm, không kiểm định):**
- Δ năm A0 − A1 không giảm đơn điệu: 2022 thấp nhất (+3,6), 2023 cao nhất (+13,5), 2024–2025 khoảng +8.
- **HO 2026 chưa có số.** Chưa chạy A1/A3 cho HO: A3 HO cần feature S1 năm 2026 (đã hoãn trong ADD1), A1 HO cần bins net015 ONNX 2026.
