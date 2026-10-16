# RESULT REX Bước 1 — selector xếp hạng coin (MASTER 2026-10-16)

- **Pre-reg:** `docs/prereg/PREREG_REX_S1.md` (90a7c9b3).
- **Code:** `research/rex/rex_s1.py`; chẩn đoán hậu kiểm ở `rex_s1_diag.py` (chỉ dùng DEV).
- **Output:** `~/claude_master/rex/`: `s1_result.json`, `s1.log`, `s1_diag.log`, `pred_s1_*.parquet`.
- **Bước 0 PASS** (90a7c9b3):
  - V2: 180 phép tính lại độc lập, sai số 1e-14.
  - Panel 213k dòng (ngày × coin trong universe), 2021-03 → 2026-09.
  - Addendum 1: bỏ 3 feature LS mà Vision 2022 không có.

## VERDICT: **NO-GO theo gate đã khai** — trượt G4 (top-10 ròng không thắng universe)
Biến thể thắng theo t-stat IC là **C1** (h = 1, đủ họ a–g).

| Gate | Kết quả |
|---|---|
| G1 IC DEV > 0, t ≥ 3 | ✓ IC **+0,111**, t **+22,2** |
| G2 dương cả 3 năm | ✓ 2022 0,123 · 2023 0,111 · 2024 0,100 |
| G3 ≥ 65 % tháng dương | ✓ **100 %** tháng |
| G4 top-10 excess ròng Sharpe ≥ 1 và dương mọi năm | ✗ **−0,38** (gross +1,20; turnover 0,95/ngày ăn hết) |
| G5 VAL 2025 | ✓ IC **+0,121**, t +13,1; top-10 excess ròng +13 %/năm (Sh 0,45) |

Model hơn feature đơn tốt nhất 1,38 lần (feature đó là dlo30, IC −0,072).

## Tất cả biến thể (DEV; IC / t / top-10 excess ròng Sharpe / so với BTC / turnover)
| | h1 | h3 | h7 |
|---|---|---|---|
| A (giá + volume) | 0,107 / 21,5 / −0,09 / −0,91 / 0,92 | 0,105 / 14,8 / +0,66 / −0,54 / 0,33 | 0,102 / 10,3 / +0,44 / −0,67 / 0,15 |
| B (+ taker) | 0,107 / 21,7 / −0,17 / −0,93 / 0,89 | 0,106 / 14,7 / +0,84 / −0,41 / 0,34 | 0,105 / 10,8 / +0,58 / −0,56 / 0,16 |
| C (+ funding/OI) | 0,111 / 22,2 / −0,38 / −1,06 / 0,95 | 0,113 / 15,2 / +0,53 / −0,61 / 0,34 | 0,117 / 11,3 / +0,62 / −0,58 / 0,16 |

- Ở h3 và h7, năm 2023 âm với MỌI biến thể (top-10 excess khoảng −0,7 đến −1,2).
- So với BTC thì âm ở MỌI biến thể.

## Chẩn đoán hậu kiểm (chỉ DEV; không phải phép thử)
1. **Tín hiệu xếp hạng là thật và rất ổn định:** IC khoảng 0,11 ở mọi năm, mọi tháng, và VAL xác nhận.
2. **Model thực chất học "coin rủi ro thấp sẽ đứng hạng cao".**
   - Decile trên cùng có rank vol30 khoảng 0,26 và thanh khoản cao nhất.
   - Decile dưới cùng có rank vol30 khoảng 0,75; đây là các coin kiểu xổ số.
3. **Edge nằm ở việc NHẬN DIỆN COIN THUA, không phải coin thắng.**
   - C1 bottom-10: excess gross −64 %/năm, Sharpe −1,18, âm cả 3 năm.
   - C1 top-10: excess gross chỉ +1,20 Sharpe.
4. **Vì sao long-only không ra tiền:**
   - Giỏ universe EW có lợi suất trung bình khoảng 0 mỗi ngày trong DEV, còn BTC +0,10 %/ngày. Tức alt EW chảy máu khoảng 37 %/năm so với BTC.
   - Top decile chỉ được khoảng +0,05 %/ngày, nên vẫn kém BTC.
   - Rebalance hằng ngày (h1) thì phí ăn hết phần thắng.
5. **Phí là vấn đề lớn nhất của h1.** Top-20 gross Sharpe 1,93 và dương cả 3 năm, nhưng ròng chỉ còn 0,34.

## Ý nghĩa cho bước tiếp (cần pre-reg mới; bị nhiễm vì đã xem chẩn đoán DEV)
Selector này là **bộ lọc loại coin xấu** rất tốt, nhưng không phải máy chọn coin thắng. Có ba cách để kiếm tiền từ nó:
- (P1) Market-neutral: long top / short bottom.
- (P2) Lọc veto cho hệ đang có.
- (P3) Long top-k low-vol, có điều kiện regime, và rebalance có buffer để giảm phí.

Ledger cộng 9 biến thể.
