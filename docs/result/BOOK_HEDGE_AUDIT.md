# BOOK_HEDGE_AUDIT — chấm lại họ BOOK_HEDGE bằng harness đã sửa (kết quả)

Ngày 2026-10-19. Pre-reg `docs/prereg/PREREG_BOOK_HEDGE_AUDIT.md` 0f2fc006. Script `research/analysis/hedge_audit.py`, JSON `docs/result/book_hedge/hedge_audit.json`.

## Kiểm hợp lệ
- V0 PASS: harness cũ tái lập đúng mọi số đã công bố (TB 8 seed, h0,5): BTC −17,81 · ETH −18,02 · ZIL −11,62 · DYN −11,34 ·
  LINK −11,23 · ADA −13,10 · DOGE −13,14 · XRP −14,42 · BNB −17,56 · SOL −19,47.
- Harness sửa (giữ số lượng giữa sự kiện, phí trên lượng giao dịch thật): coin đơn thay đổi nhỏ (DD lệch 0,1–0,4pp) ⇒ lỗi notional-cố-định
  KHÔNG làm sai kết luận coin đơn; nhưng làm sai nặng DYN (LUNA).

## Kết quả (nền: CAGR22 37,95 · DD22 −22,55 · Calmar 1,69 · ΣPnL 110k; cửa sổ 2023+: DD −17,92 · Calmar 2,79)

| Arm (h0,5) | DD22 | Calmar | ΣPnL | C1 (≥5pp, CI99, PnL) | C2 P(ΔCal>0) / P(ΔDD>0) | C3 ΔDD 2023+ | C4 @25bps | TIỀM NĂNG |
|---|---|---|---|---|---|---|---|---|
| BTC | −17,89 | 1,94 | −9 % | 3/8 ✗ | 0,92 / 0,99 | +0,6 | ✗ | ✗ |
| ETH | −18,04 | 1,96 | −12 % | 5/8 ✗ | 0,97 / 0,99 | −0,1 | ✗ | ✗ |
| **ZIL** | **−11,86** | **2,84** | −16 % | 8/8 ✓ CI [0,69; 1,60] | **0,97 / 0,99** ✓ | **+11,7** ✓ | ✓ | **✓** |
| LINK | −11,62 | 2,56 | −28 % | 8/8 ✓ | 0,83 ✗ / 0,95 | +9,4 ✓ | ✓ | ✗ (C2) |
| ADA | −13,43 | 2,33 | −29 % | 8/8 ✓ | 0,82 ✗ / 0,96 | +9,5 ✓ | ✓ | ✗ (C2) |
| DOGE | −13,54 | 2,17 | −31 % | 8/8 ✓ | 0,71 ✗ / 0,96 | +5,3 ✓ | ✗ | ✗ |
| XRP | −14,69 | 1,97 | −34 % | 7/8, CI chứa 0 ✗ | 0,73 / 0,96 | +3,8 | ✗ | ✗ |
| BNB | −17,62 | 1,90 | −18 % | 6/8 ✗ | 0,87 / 0,97 | +0,3 | ✗ | ✗ |
| SOL | −19,44 | 1,67 | −37 % | 1/8 ✗ | 0,81 / 0,94 | −1,5 | ✗ | ✗ |
| **DYN** | **−17,09** (cũ −11,34) | **1,77** (cũ 2,96) | −30 % | 3/8 ✗ | 0,83 / 0,96 | +4,2 | ✗ | ✗ |
| DYN bỏ LUNA | −14,37 | 1,96 | −34 % | 7/8, CI chứa 0 ✗ | 0,81 / 0,96 | +3,6 | ✗ | ✗ |

h1,0: chỉ ZIL qua C1 (DD −8,87, Calmar 3,12) nhưng trượt C2 (P 0,87); mọi coin khác h1,0 làm Calmar xấu đi (LINK/ADA/DOGE/XRP/SOL/DYN ΔCalmar −0,7…−1,1).

## Phát hiện chính
1. **DYN là ảo**: hedge PnL 2022 từ +15,99k (harness cũ) còn +4,45k (sửa) và +0,24k khi bỏ LUNA ⇒ lợi thế DYN đến từ short LUNA
   cân lại mỗi phút. Kết luận cũ "DYN ≈ ZIL ⇒ hiệu ứng không phải ZIL" bị RÚT LẠI.
2. **Hiệu ứng thật, chung**: short một alt bám nhân tố alt ở h0,5 cắt DD 8–11pp (cả 2022 và 2023+), đổi lại mất 15–31 % ΣPnL.
   BTC/ETH/BNB/SOL cắt kém (≤5pp) vì không bám nhân tố alt đủ.
3. **Calmar có cải thiện hay không phụ thuộc chi phí hedge ở năm tăng**, tức coin đó tụt riêng bao nhiêu 2023–2025:
   ZIL (coin suy tàn, −90 %) rẻ (−5,7/−10,5/−3,4k), LINK/ADA/DOGE đắt (−9…−12k/năm) ⇒ chỉ ZIL qua bootstrap đường giá.
   Phần "ZIL rẻ" chính là phần dễ là may mắn trong mẫu nhất.
4. Chỉ **ZIL h0,5** đạt cả 4 tiêu chí — nhưng: (a) ZIL chọn từ screen 2024 nằm trong cửa sổ đo; (b) là thắng nhất trong 22 arm
   (lời nguyền người thắng); (c) ADV 11,9 M/ngày, trần quy mô ~0,3 M USD; (d) dự án suy tàn — thanh khoản/niêm yết có thể mất.

## Kết luận
- Không có cấu hình nào đủ sạch để coi là ứng viên v1.1 trên DEV. ZIL h0,5 là ứng viên THĂM DÒ duy nhất, chỉ đáng xác nhận 1 lần HO4 2026.
- Không dùng h1,0, không dùng DYN (corr-với-book), không dùng LINK/ADA/DOGE làm hard-pick (trượt bootstrap).
- Nếu muốn một phiên bản ít thiên lệch chọn: giỏ alt thanh khoản point-in-time (top-N theo volume, đều trọng số) — chưa thử, cần pre-reg mới.
