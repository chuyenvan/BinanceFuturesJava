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

## 4. Tiếp theo
- A1 NET (8 seed) và A2 RND (4 seed) để chấm C1/C2. Kết quả bổ sung vào file này.
