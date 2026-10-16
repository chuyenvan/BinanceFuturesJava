# PRE-REG (khám phá mở rộng) — R2X: bookDepth tại tick vào đợt, năm 2023 + 2025 (MASTER 2026-10-16)

## Bối cảnh

- R2 2024 không ra ứng viên (`docs/result/VZ_R2_BOOKDEPTH_2024.md`, 626 chân / 44 đợt):
  - F1 IC +0,065 [−0,010; +0,164];
  - F2 IC +0,055 [−0,042; +0,165].
- Ngày 10-16, owner chọn mở rộng khám phá sang 2023 và 2025 để tăng power. Cái giá đã biết trước: bookDepth không còn năm DEV nào chưa dùng để xác nhận; chỉ còn HO 2026 (n nhỏ, chỉ báo cáo).
- File này commit TRƯỚC khi tải dữ liệu 2023 và 2025.

## Thiết kế: giữ nguyên hoàn toàn R2

Mọi thứ sau đây giống hệt `PREREG_VZ_R2_BOOKDEPTH.md` + addendum 1:

- **Chân:** gqsf-a1 printDone. Một đợt là các chân cùng phút `start` (UTC), có ≥ 6 chân, **gồm cả DCA** như R2.
- **Feature:** F1 `bid1_rel`, F2 `imb1`, F3 `bid5_rel`.
  - Lấy snapshot ≤ t_dec = start + 60 s.
  - Snapshot cũ hơn 5′ ⇒ NaN.
- **Phép thử:**
  - T1–T3: IC trong đợt cho F1, F2, F3.
  - T4: Spearman giữa trung vị F1 của đợt và ret của đợt.
- **CI:** bootstrap theo khối 5 ngày, NREP 2000, seed 20261016.
- **Kiểm dữ liệu:**
  - V1 causal;
  - V2 theo addendum 1: mid ∈ [low·0,998; high·1,002] của nến t0−1′..t0, đạt ở ≥ 95 % chân. Kline lấy từ Vision daily `klines/1m`;
  - V3: độ phủ ≥ 80 %.

## Năm

- 2023 + 2025 (UTC), chấm gộp. bookDepth có từ 2023-01-01.
- 2024 KHÔNG chấm lại. Chỉ báo bảng gộp 2023–2025 để mô tả, không dùng làm tiêu chí.

## Ứng viên (ledger 59 → 63)

Một feature là ứng viên khi đủ cả 4 điều kiện:

1. CI95 gộp 2023 + 2025 không chứa 0.
2. Dấu đúng cơ chế:
   - F1, F3 dương (bid còn dày ⇒ ret tốt);
   - F2 dương (bid lấn ask);
   - T4 dương.
3. Cùng dấu ở 2023 và ở 2025 khi tách riêng.
4. Cùng dấu với ước lượng điểm 2024 (R2).

Nếu không có feature nào đạt: **đóng họ bookDepth tại tick vào**. Không mở thêm feature hay ngưỡng mới.

## Bước sau (chỉ khi có ứng viên)

- Báo cáo HO 2026 trên `ho4-k24-b-s42`, chỉ báo cáo.
- Viết pre-reg riêng cho luật sim (chọn / veto), chạy 8 seed DEV, kèm khai rõ rằng bookDepth không còn năm DEV sạch.

## Addendum 1 (2026-10-16, viết TRƯỚC khi tính outcome; `test` chưa chạy)

**V2 gộp FAIL:** 94,35 % chân đạt (n = 1 027), dưới ngưỡng 95 %. V1 và V3 PASS (phủ 95,9 %).

**Chẩn đoán** (`r2x_diag.py`; chỉ đọc mid, snap và kline, không đọc pnl/ret):
- Tách theo năm: 2023 đạt **99,83 %** (580 chân). 2025 chỉ đạt **87,25 %** (447 chân).
- Có 58 chân fail. 52 chân lệch quá 3 % (trung vị 25 %, max 247 %). Phần lớn nằm trong cú sập **2025-10-10 15:02 → 2025-10-11 13:16**; ở các đợt này 22–86 % số chân fail.
- Độ trễ snapshot của chân fail (28 s) không khác chân đạt (29 s).
- ⇒ Lỗi không đến từ thời gian. Trong cú sập này sổ lệnh bị quét sạch. Snapshot bookDepth khi đó không khớp với giá (mid suy ra từ notional/depth vô nghĩa), nên feature tại những chân này không đo đúng thứ cần đo.

**Sửa:**
- Chân nào có mid nằm ngoài băng [low·0,998; high·1,002] thì F1, F2, F3 = NaN, tức coi là feature không tin được.
- Ngoài việc này, không đổi feature, phép thử hay tiêu chí ứng viên.
- V2 sau lọc = 100 % (đúng theo định nghĩa). Phải giữ V3 ≥ 80 % sau lọc.

**Giới hạn (ghi rõ):**
- Bộ lọc loại đúng những chân trong cú sập lớn nhất của 2025, tức ngày tệ nhất.
- Vì vậy T4 (veto theo đợt) không thể học từ sự kiện đó.
- Báo thêm danh sách các đợt bị ảnh hưởng (số chân bị lọc trên tổng). Ret của các đợt này chỉ báo cáo, không đưa vào phép thử.
