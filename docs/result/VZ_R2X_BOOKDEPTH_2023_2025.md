# VZ R2X — bookDepth tại tick vào đợt, KHÁM PHÁ MỞ RỘNG 2023 + 2025 (MASTER 2026-10-16)

- Pre-reg: `docs/prereg/PREREG_VZ_R2X_BOOKDEPTH.md` (commit 96865196), addendum 1 (9f20e236) viết TRƯỚC khi có outcome.
- Code: `research/vz/r2/r2x_bookdepth.py`, `r2x_filter.py`, `r2x_diag.py`. HO dùng `r2h_*.py`.
- Output gốc: `~/vz_bd/r2x_*`. Bản sao json nằm trong `research/vz/r2/`.

**Dữ liệu:** gqsf-a1, đợt ≥ 6 chân, năm 2023 + 2025. Tổng 1 072 chân / 78 đợt. Sau khi lọc theo addendum 1 còn 69 đợt có ≥ 6 chân mang feature.

**Kiểm dữ liệu (sau addendum 1): PASS**
- V1 causal: đạt.
- V2: 2023 đạt 99,8 %, 2025 đạt 87,3 %. Lọc bỏ 58 chân, gần hết thuộc cú sập 2025-10-10/11, lúc sổ lệnh bị quét sạch.
- V3 (độ phủ) sau lọc: 90,5 %.

## Kết quả 4 phép thử (ledger 59 → 63)

| T | Feature | IC / rho gộp | CI95 | 2023 | 2025 | 2024 (R2) | Ứng viên? |
|---|---|---|---|---|---|---|---|
| T1 | F1 `bid1_rel` (trong đợt) | **+0,073** | [+0,011; +0,143] | +0,038 | +0,124 | +0,065 | **CÓ** (đạt đủ 4 điều kiện) |
| T2 | F2 `imb1` (trong đợt) | **+0,123** | **[+0,071; +0,172]** | +0,106 | +0,149 | +0,055 | **CÓ** (đạt đủ 4 điều kiện) |
| T3 | F3 `bid5_rel` (trong đợt) | +0,038 | [−0,016; +0,089] | +0,043 | +0,031 | −0,012 | không |
| T4 | trung vị F1 đợt vs ret đợt | +0,029 | [−0,190; +0,281] | +0,073 | +0,038 | +0,069 | không |

- F2 vẫn đứng nếu siết Bonferroni k = 4. Cận dưới CI95 là +0,071, cách 0 xa.
- F1 chỉ vừa qua ngưỡng (cận dưới +0,011). Với Bonferroni thì nhiều khả năng CI của F1 chứa 0.

**Cơ chế:** bid dày hơn ask trong khoảng ±1 % lúc vào lệnh nghĩa là bên mua đang hấp thụ. Chân như vậy giữ tới khi thoát có kết quả tốt hơn. Đây là tín hiệu **chọn chân trong đợt**. Nó **không** phải tín hiệu veto đợt (T4 bằng 0).

## Mô tả giá trị tiền (không chấm; DEV 2023–2025 gộp, 113 đợt, 1 576 chân)

PnL/margin theo tứ phân vị F2 tính trong từng đợt:

| Tứ phân vị F2 | PnL/margin |
|---|---|
| Q1 (thấp nhất) | +2,1 % |
| Q2 | +4,2 % |
| Q3 | +3,3 % |
| Q4 (cao nhất) | +4,8 % |

- Cả 4 nhóm đều lãi. Vì vậy **bỏ hẳn** chân Q1 sẽ làm giảm tổng PnL. Giá trị chỉ có khi **dồn size** sang chân F2 cao mà giữ nguyên tổng margin.
- Ước tính thô: dời 25 % margin của đợt từ Q1 sang Q4 thì được khoảng +0,7 % margin đợt. Con số này chưa qua sim nên không phải kết quả.

## HO 2026 (`ho4-k24-b-s42`, 24 đợt / 13 ngày, 299 chân; chỉ báo cáo)

- Kiểm dữ liệu PASS. V2 đạt 96,6 %; lọc 10 chân, 9 trong số đó thuộc 2026-09-09.
- F2 IC **−0,021** [−0,085; +0,054] ⇒ **KHÔNG xác nhận**. Spread nửa cao − nửa thấp vẫn dương (+0,6 %).
- F1 IC −0,041, ngược dấu.
- Bootstrap chỉ có 13 ngày (~3 khối) nên CI của HO không đáng tin. Dù vậy, mức +0,12 của DEV vẫn cách ước lượng HO khoảng 2–3 SE.

## Kết luận

- **F2 `imb1` là ỨNG VIÊN DEV.** Dương cả ba năm 2023/2024/2025, CI gộp 2023 + 2025 không chứa 0.
- **Nhưng HO 2026 không xác nhận** (n nhỏ, chỉ báo cáo). Theo pre-reg đây không phải GO.
- bookDepth không còn năm DEV sạch nào để xác nhận thêm.
- ⇒ **Đề xuất:** KHÔNG đầu tư sim/live cho luật này lúc này. Đánh dấu "ứng viên chờ forward". Cách xác nhận duy nhất còn lại là dữ liệu sau 2026-10, gồm:
  - Vision bookDepth các tháng tới, chạy lại HO khi đủ ≥ 40 đợt;
  - shadow 242 ghi depth ±1 % của top-K tại tick gate PASS.
- Luật xác nhận forward chốt ngay bây giờ: F2 IC trong đợt > 0, một phía 95 %, trên các đợt có ngày ≥ 2026-10-17.
