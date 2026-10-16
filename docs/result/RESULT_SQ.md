# RESULT SQ — long sau funding âm sâu kéo dài (họ #3, họ cuối) (MASTER 2026-10-17)

- **Pre-reg:** `docs/prereg/PREREG_SQ.md` (5bb3e1a3).
- **Code:** `research/sq/sq.py`.
- **Output:** `~/claude_master/sq/`.
- **Dữ liệu:**
  - 11 159 lần kích hoạt; sau cooldown còn 1 276 sự kiện trên 272 coin.
  - V1: 10 sự kiện kiểm tay, cả 10 đúng điều kiện kích hoạt, sai số giá 0.
  - V2: 97,9 % sự kiện có đủ giá.

## VERDICT: **NO-GO** — trung bình dương nhưng KHÔNG có ý nghĩa thống kê (trượt G1, G3)

Các con số là lãi ròng trung bình mỗi sự kiện, đã gồm phí 0,14 % và funding nhận được.

| | n | Trung bình | Median | Hit | t (gom theo ngày) | Excess so với BTC | Phần từ funding | 5 % tệ nhất | Bỏ 1 % lãi nhất | Theo năm |
|---|---|---|---|---|---|---|---|---|---|
| H24 DEV | 515 | +0,72 % | −0,37 % | 0,48 | +0,65 | +0,50 % | +0,66 % | −12,1 % | +0,20 % | 22 +0,29 · 23 +0,68 · 24 +1,26 % |
| H24 VAL | 734 | +0,70 % | −0,82 % | 0,44 | +1,24 | +0,61 % | +0,86 % | −11,5 % | −0,27 % | |
| H72 DEV | 485 | +2,01 % | −0,32 % | 0,48 | +1,38 | +1,41 % | +1,52 % | −19,2 % | +0,98 % | 22 +2,1 · 23 +3,3 · 24 +0,9 % |
| H72 VAL | 696 | +1,64 % | −1,06 % | 0,45 | +0,65 | +1,53 % | +2,05 % | −18,3 % | +0,13 % | |

Gate:
- **Đạt:** G2 (dương mọi năm DEV), G4 (excess > 0), G5 (vẫn dương sau khi bỏ 1 % lãi nhất trên DEV).
- **Trượt:** G1 (t 0,65 / 1,38, cần ≥ 3) và G3 (VAL t < 2).

## Diễn giải
- Phần lớn lợi nhuận đến từ **funding nhận được**. Phần giá gần 0 hoặc âm: VAL H72 giá ≈ −0,4 %.
- Rủi ro đuôi rất lớn: 5 % sự kiện tệ nhất lỗ 12–19 %. Median âm; lãi trung bình nhờ vài cú squeeze lớn.
- Với t ≈ 1, đây là nhiễu cho tới khi chứng minh được điều ngược lại. Theo luật đã khai, đóng họ này.

## Kết thúc ngân sách
Cả 3 họ (FW, MK, SQ) đều NO-GO. Theo quy tắc đã chốt với owner, **dừng tìm alpha mới cho tới sau go-live**. Ledger cộng 2.
