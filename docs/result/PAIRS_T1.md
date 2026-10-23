# PAIRS_T1 — pairs trading / stat-arb market-neutral, tầng 1 (MASTER 2026-10-23)

- **Pre-reg:** `docs/prereg/PREREG_PAIRS_T1.md`, commit **`58d36af4`**. Prereg và toàn bộ mã được commit TRƯỚC khi tính PnL; sau đó không sửa luật hay tham số.
- **Mã + JSON:** `docs/result/pairs_t1/`
  - Chạy: `pairs_t1_run.py main|controls|valid`, `pairs_t1_v5.py`, `pairs_t1_report.py`.
  - Mô tả rủi ro (không phải phép thử): `pairs_t1_anom.py`.
  - Kết quả: `report.json`, `valid.json`, `v5.json`, `anom.json`.
- **Dữ liệu trung gian (không commit):** `~/claude_master/pairs/{data,out}/`.
- **Trial ledger:** +4 (M1–M4).

## VERDICT: cả 4 phương pháp đều **KHÔNG SỐNG tầng 1**

| | Số tiêu chí G1–G6 đạt | Kết luận |
|---|---|---|
| M1 Engle–Granger | 0/6 | Đóng |
| M2 Distance (Gatev) | 0/6 | Đóng |
| M3 Kalman | 1/6 (chỉ G4, vì gần như không có vị thế) | Đóng |
| M4 Avellaneda–Lee | 0/6 | Đóng |

- Không có ứng viên nào cho tầng 2.
- HO 2026 không bị đụng.

## 1. Dữ liệu và kiểm vệ sinh: tất cả PASS

**Nguồn dữ liệu**
- Kline 1m Vision UM, gộp thành nến 1h (`build_1h.py`):
  - 2021-01..11 tải mới từ Kaggle `chuyendinh/vz-kline1m-2021`, sha256 khớp README.
  - 2021-12..2025-12 đọc read-only từ `~/vz_e1/raw`.
- Funding thật: `chuyendinh/vz-funding`, file 2021–2025.
- Panel 43 824 giờ × 637 symbol. 89 symbol hết dữ liệu trước 2025-12.
- 256 tuần, từ 2021-02-03 đến 2025-12-30.
- Không dùng REST, 2026, 2020/`bcast-*`, 242.

| Kiểm | Kết quả |
|---|---|
| **V1** không look-ahead | **PASS.** Kiểm 5 tuần (k = 10/60/120/180/240), thay dữ liệu tương lai bằng rác: universe, cặp và tham số M1/M2 giống hệt; lệnh và đường PnL M1–M3 giống hệt; s-score M4 giống hệt. Lần chạy đầu M4 báo FAIL do lỗi trong chính **phép kiểm** (so hàng s 101 với giờ của hàng 100). Đã sửa phép kiểm, engine không đổi, chạy lại PASS. |
| **V2** có symbol delist | **PASS.** 57 symbol đã delist từng vào universe (LUNA, FTT, SRM, MATIC, FTM, EOS, MKR, RNDR, AGIX, OCEAN, WAVES, BNX…). Số chân lệnh trên các symbol này: M1 388, M2 383, M3 60. 1 lần khớp cờ `delist` (M2), 0 lần `gap`. |
| **V3** control ngẫu nhiên | **PASS ở cả 4** (bảng bên dưới). Gross của control ≈ 0, net ≈ −chi phí. Không có artifact kiểu Track B. |
| **V4** đối soát từng chân | **PASS.** 240 chân, đọc lại từ parquet 1m thô: giá vào/ra khớp 0/240 lệch. Funding tính lại từ parquet thô: lệch rel 0. PnL chân lệch 0. Tổng các lệnh bằng đường PnL ở 0/768 tuần-phương pháp lệch. M4: Σ attribution = equity − 1, sai số ≤ 2e-14. |
| **V5** tính tay 1 tuần | **PASS.** Tuần 2023-06-07 (k = 122): dựng lại nến bằng pandas từ parquet thô, lệch close 0. Universe trùng (50/50). Dùng `statsmodels.coint`: 251 cặp qua lọc, top-10 trùng cả thứ tự. 12/12 lệnh trùng (giờ, lý do, gross, phí, funding < 1e-12). Net tuần +0,78342 % ở cả hai cách tính. ADF nhanh so với `coint` trên 400 cặp: lệch tối đa 1,7e-11, 0 lần lệch quyết định p < 0,05. |

**V5, ví dụ lệnh 1 (M1, AXS/ADA, β = 0,964).**
- z ≥ 2 nên short spread.
- Vào 2023-06-07 17:00 (open nến h = 21305), ra 2023-06-08 07:00 (h = 21319) vì z cắt 0.
- Chân AXS: w = −0,05091 equity, pe 6,330, px 6,153, qty −0,0080433. Gross = −0,0080433 × (6,153 − 6,330) = **+0,0014237**.
- Chân ADA: w = +0,04909, pe 0,3211, px 0,3267, qty 0,152867. Gross = **+0,0008561**.
- Phí 0,07 % × (notional vào + ra) = 0,0001396. Funding −0,0000223.
- Net = **+0,0021178** (= +0,212 % equity).

**V5, ví dụ lệnh 2 (cùng cặp, bị stop |z| ≥ 4).**
- Gross: AXS +0,0014939, ADA −0,0032340.
- Phí 0,0001367, funding −0,0000423.
- Net −0,0019191.

**V3: control C1 (50 lần), gross năm hoá theo % equity**

| | Gross của phương pháp | Control gross TB (sd) | t | Control chi phí | Control net | C2 (cặp ngẫu nhiên, hướng theo luật, 20 lần) |
|---|---|---|---|---|---|---|
| M1 | −10,46 % | +0,01 % (6,48) | 0,01 | 4,58 % | −4,59 % | **−5,61 %, t = −4,86** |
| M2 | +7,60 % | −0,55 % (6,85) | −0,56 | 1,95 % | −2,61 % | −3,19 %, t = −2,71 |
| M3 | −12,47 % | −0,27 % (2,66) | −0,72 | 0,32 % | −0,64 % | +0,40 %, t = 0,68 |
| M4 | +12,35 % (giá) | −1,20 % (6,71) | −1,27 | 104,8 % | −106 % | – |

## 2. Bảng chính (BASE = 0,05 % + 0,02 % mỗi chiều mỗi chân, funding thật)

| | M1 EG | M2 Distance | M3 Kalman | M4 AL |
|---|---|---|---|---|
| **Gross Sharpe E \| C** | −0,51 \| −1,21 | 0,91 \| 0,08 | 0,23 \| −0,78 | 0,94 \| 0,01 ¹ |
| **Net Sharpe E \| C** (G1 ≥ 1) | −0,97 \| −1,61 | 0,41 \| −0,55 | 0,10 \| −0,98 | −4,28 \| −4,63 |
| CAGR net toàn kỳ (E \| C) | −15,9 % (−12,8 \| −20,2) | +0,3 % (+4,7 \| −5,8) | −42 % (cháy tài khoản) | −62 % |
| **maxDD**, MTM giờ (G2 ≤ 20 %) | −58,6 % | −24,0 % | **−112 % (equity < 0)** | −99,3 % |
| **Tuần tệ nhất** (G5 ≥ −10 %) | −17,8 % (09/2025, MYX) | −12,0 % (04/2021, MATIC) | **−93,8 %** (09/2025, MYX) | −17,9 % (07/2025) |
| **×2 chi phí**, lợi nhuận E \| C (G3 > 0) | −43,8 % \| −42,7 % | −7,2 % \| −21,8 % | −1,1 % \| −93,6 % | −99,7 % \| −98,6 % |
| Maker 0,02 %, Sharpe E \| C | −0,65 \| −1,33 | 0,79 \| −0,09 | 0,20 \| −0,97 | −0,54 \| −1,30 |
| **Tháng dương ở C** (G4 ≥ 60 %) | 21 % | 46 % | 62 % ✓ | 17 % |
| **Bỏ top-3 cặp/symbol** (G6 > 0) | −0,86 | −0,03 (tổng +0,05) | −0,91 | −1,10 |
| Turnover (×equity/năm) | 82 | 97 | 11 | **1 545** |
| Lệnh/tháng | 34 | 40 | 4,4 | 643 lần vào |
| Phơi nhiễm gross TB | 11 % | 40 % | 0,4 % | 100 % |
| Funding/năm | −0,02 % | +0,23 % | −4,3 % | −0,8 % |
| Participation p95 @ $1M (vốn để p95 = 1 %) | 0,075 % (~$13M) | 0,068 % (~$15M) | 0,092 % (~$11M) | 0,009 % (~$115M) |
| **Tương quan ngày với crash-buy P0 \| X14** | 0,135 \| 0,128 | 0,008 \| 0,017 | 0,001 \| 0,002 | 0,041 \| 0,034 |
| TB ngày trong 5 % ngày tệ nhất của crash-buy (crash-buy −1,4 %/−1,7 %) | −0,21 % | **+0,06 %** | +0,07 % | −0,37 % |
| Deflated Sharpe (N = 4) | 0,00 | 0,00 | 0,00 | 0,00 |

¹ M4 "gross" là chạy với chi phí = 0 nhưng vẫn có funding. Tách theo năm: giá +12,3 %, funding −0,8 %, chi phí **−106 %**.

Crash-buy để đối chiếu: P0 / X14 TB 8 seed, 2021-07-10 → 2025-11-28, Sharpe ngày 2,10 / 2,05.

## 3. PnL net trong các đợt crash (khung ngày chốt trong prereg)

| Đợt | M1 | M2 | M3 | M4 | crash-buy X14 |
|---|---|---|---|---|---|
| 2021-05-12..23 | −4,5 % | +1,0 % | +5,6 % | −1,2 % | (trước 07/2021) |
| 2021-12-03..05 | −3,1 % | +0,6 % | 0 | +1,6 % | −3,9 % |
| LUNA 2022-05-07..14 | −5,1 % | +0,0 % | +2,1 % | −5,1 % | −10,9 % |
| 3AC 2022-06-10..19 | −1,5 % | +1,5 % | 0 | −5,1 % | +7,0 % |
| FTX 2022-11-06..13 | −4,0 % | +1,0 % | +1,5 % | +4,0 % | −7,4 % |
| 2024-04-12..17 | −1,7 % | +0,9 % | +3,2 % | −1,9 % | −3,3 % |
| 2024-08-02..06 | −1,2 % | +0,9 % | 0 | +1,4 % | +3,1 % |
| 2025-02-02..04 | −1,1 % | +1,6 % | +0,2 % | +1,2 % | +6,5 % |
| 2025-03-03..11 | +1,1 % | +1,6 % | 0 | −3,0 % | −1,4 % |
| 2025-10-10..11 | −0,1 % | +1,1 % | +1,1 % | −0,6 % | +5,5 % |

**M2 dương ở cả 10/10 đợt** (mỗi đợt +0,0 → +1,6 %), và gần như không tương quan với crash-buy. Đây là tính chất đa dạng hoá đúng như owner muốn. Nhưng edge tổng sau chi phí ≈ 0 và âm ở C, nên KHÔNG đủ điều kiện.

## 4. Đọc kết quả: vì sao chết

1. **M1 (EG): cointegration in-sample 30 ngày không giữ được ngoài mẫu.**
   - Lý do thoát: time-stop 58 %, stop |z| ≥ 4 là 24 %, hồi về 0 chỉ 11 %. Spread phần lớn không hồi.
   - Gross đã âm trước phí: −10,5 %/năm.
   - Tệ hơn cả cặp ngẫu nhiên (C2 −5,6 %). Nghĩa là lọc p-value chọn đúng những cặp có 1 chân vừa gãy cấu trúc.
   - Bằng chứng về tập trung: trung vị 4/10 cặp chung 1 coin; 39 % số tuần có 1 coin nằm trong ≥ 5/10 cặp (BCH, ETC, AXS, MYX…).
2. **Mean-reversion giờ trên cặp crypto tuỳ ý là âm** (C2 của M1 t = −4,9, của M2 t = −2,7). Ở chân trời ≤ 1 tuần, độ lệch giữa hai coin có xu hướng kéo dài (momentum / chuyện riêng của từng coin), không hồi.
3. **M2: chọn cặp theo SSD có giá trị thật nhưng nhỏ.**
   - Gross +7,6 %/năm, so với −3,2 % của cặp ngẫu nhiên: chênh khoảng +10,8 pp.
   - Chi phí ăn mất 6,8 %/năm.
   - Edge tập trung ở E (gross Sharpe 0,91), về 0 ở C (0,08). Đúng xu hướng suy giảm được ghi nhận trong literature (Do & Faff 2010).
   - Kể cả với maker, C vẫn âm (Sharpe −0,09).
4. **M3: Kalman gần như không giao dịch, và khi giao dịch thì như một lệnh short trần.**
   - 4,4 lệnh/tháng, phơi nhiễm 0,4 %.
   - Khi vào lệnh, β dự báo có thể rất lớn (β ≈ 9,7 với MYX). Khi đó chân x chiếm khoảng 90 % slot, tức gần như short trần.
   - Tuần 2025-09-03: MYX bị squeeze từ 2,7 lên 14,5 (+430 %, kéo dài nhiều giờ, không phải lỗi dữ liệu). Nhiều cặp cùng short MYX ⇒ tuần −93,8 %, equity < 0.
   - Đây chính là rủi ro T2-MOM H3 lặp lại.
5. **M4 (AL) trên nến 1h: chi phí giết chết.**
   - Edge giá có thật nhưng mỏng: +12 %/năm, Sharpe E 0,94, C 0,01.
   - Turnover 1 545×/năm, tương đương chi phí ~106 %/năm. Maker cũng không cứu được (−0,54 / −1,30).
   - Gốc của vấn đề: hedge bằng eigenportfolio trên 50 coin, rebalance mỗi lần tập tín hiệu thay đổi (~643 lần vào/tháng).

## 5. Rủi ro (nếu có ai muốn quay lại hướng này)

- **Squeeze:**
  - Mọi biến thể short alt đều có đuôi kiểu MYX (09/2025) / MATIC (04/2021).
  - M1 và M3 không có trần notional theo symbol, cũng không trần số cặp chung 1 coin.
  - Biến thể nào sau này cũng phải có hai trần đó trong prereg, không thêm sau.
- **Funding:**
  - Nhỏ với M1/M2.
  - M3 −4,3 %/năm do short MYX lúc funding âm sâu.
- **Delist:** đã xử lý (57 symbol). Chỉ 1 lần đóng bằng giá cuối, ảnh hưởng không đáng kể.
- **Capacity:** không phải ràng buộc. p95 participation < 0,1 % ADV @ $1M, tức khoảng $10–15M trước khi chạm 1 %. Ràng buộc thật là **chi phí so với edge**.

## 6. Bất thường và ghi chú

1. Hai thay đổi sau lần chạy đầu, đều KHÔNG đụng engine, luật hay tham số; commit riêng:
   - Sửa lỗi chỉ số hàng trong phép kiểm V1-M4.
   - Cache đọc parquet trong V4 (chỉ để chạy nhanh hơn).
2. Dữ liệu có bước nhảy đổi mệnh giá BNX ngày 2023-02-22 (85,6 → 1,55). Không lệnh nào giữ qua mốc đó. 0 chân lệnh giữ qua nhảy giá > 2×/giờ.
3. Quy ước tính equity:
   - M3: equity âm sau tuần MYX nên các chỉ số sau đó (CAGR) chỉ mang tính hình thức. Tháng dương ở C 62 % là do phần lớn tháng không có vị thế.
   - M1–M3 dùng committed capital (mỗi slot 10 %); M4 luôn gross 1×. Phơi nhiễm thực của M2 TB chỉ 40 %. Tính theo vốn thực dùng thì Sharpe gần như không đổi, chỉ CAGR và DD to lên.
4. Smoke test trước commit (đã công khai trong prereg) chỉ chạy formation trên dữ liệu thật và chạy engine trên dữ liệu giả lập. Không có PnL thật nào được nhìn trước khi commit.

## 7. Kết luận và đề xuất

- Đóng cả 4 (ledger +4). Pairs/stat-arb cổ điển ở 1h, top-50 perp, chi phí taker **không** cho alpha net.
- Nếu muốn bù tính thưa của crash-buy, tín hiệu duy nhất đáng ghi nhận là **M2 có tương quan ≈ 0 với crash-buy và dương ở 10/10 đợt crash**. Nhưng edge net ≈ 0 và âm ở C.
- Hướng mở lại khả dĩ (prereg MỚI, tính là phép thử mới, không phải cứu M2):
  - distance ở khung **ngày** với chân trời dài hơn, để giảm turnover;
  - có trần theo symbol;
  - khớp maker có mô hình xác suất khớp.
- Ưu tiên: thấp.
