# RESULT_F0_CLOSES1H — generator `CLOSES_1H.bin` + kết quả tái lập (byte-identity KHÔNG đạt — nguồn Vision biến động)

Ngày: 2026-09-29. Task: **F0** (item 2). Pre-reg: **`docs/prereg/PREREG_F0_REPRO.md`** (commit `f675e5ec`).

**Kết luận 1 dòng:** generator **ĐÚNG** (format/quy ước/giá trị khớp 99,9998 %), nhưng
**byte-identity KHÔNG đạt** vì nguồn duy nhất (Binance Vision futures kline 1h) là **nguồn biến
động** đã bị sửa/bổ sung sau khi file gốc được sinh (mtime 2026-09-02).

---

## 1. Generator

`research/pipeline/closes1h_build.py` (commit `f675e5ec`). Tải Vision
`data.binance.vision/data/futures/um/monthly/klines/{SYM}/1h/`, tháng 2021-01..2025-12, ghi 14 B/rec
big-endian `[ts>i8][symId>i2][close>f4]`, `ts = open_time + 1h`, sort `(ts, tên symbol)`.

**1 bẫy đã sửa:** symbol `币安人生USDT` (symId 560) có ký tự non-ASCII — phải `urllib.parse.quote`
tên symbol trong URL (nếu không, 60 tháng download FAIL, mất 80 rec).

## 2. Đối chiếu byte

| | bản gốc | bản tái lập |
|---|---|---|
| đường dẫn | `/home/ubuntu/java/fsrun/CLOSES_1H.bin` | `/home/ubuntu/f0_repro/CLOSES_1H.bin` |
| record | 10 322 386 | 10 636 509 |
| byte | 144 513 404 | 148 911 126 |
| sha256 | `24fd3e93…4d94b5` | `6c2ed3ee…1d3a03` |

**KHÁC** (+314 123 rec). Nhưng **giá trị khớp gần tuyệt đối**: 10 316 936 khoá `(ts,sym)` chung,
chỉ **24** khoá có giá trị close khác nhau (≈ 99,9998 % khớp).

## 3. Khác ở đâu (phân tích record lệch)

| nhóm | số rec | bản chất |
|---|---|---|
| **chỉ có ở bản tái lập** | **319 573** (616 symbol) | symbol đã **delist/đổi tên** (FTT, SC, RAY, USDC, BTCDOM, BNX, STRAX, DGB, RAD, GLMR…) — Vision giờ trả thêm dữ liệu kéo dài tới 2026-01-01 mà file gốc (sinh trước 2026-09-02) không có. Theo năm: 2021 `14 350` · 2022 `36 849` · 2023 `44 286` · 2024 `87 119` · 2025 `136 955` · 2026 `14`. |
| **chỉ có ở bản gốc** | **5 450** (47 symbol cũ: SUSHI, KNC, ZEN, IOTA, NEAR, YFI…) | Vision đã **reset/xoá ~72 giờ** dữ liệu tháng **2022-02** (đo: SUSHIUSDT-1h-2022-02 còn 600 dòng thay vì 672). File gốc giữ bản trước khi Vision sửa. |
| **24 giá trị khác** | 24 | Vision **chỉnh sửa close** (batch 2025-01-29 00:00–02:00 nhiều symbol + 2023-11-10 STEEMUSDT). |
| **BTC thêm 16 giờ** | 16 | Vision **backfill** giờ mất 2025-12-15 09:00→24:00 (outage) sau khi file gốc sinh. |

## 4. Kiểm chứng generator ĐÚNG (không phải bug)

- Bản ghi đầu: `1INCHUSDT` ts=2021-01-01 01:00 close `1.3246` — khớp đúng file gốc (đã đo float32
  round-trip trùng `fs/kl/36.npz` cache của FS job).
- Sort `(ts, name asc)`: khớp 43 824 khối ts của file gốc (`bad=0`), 0 trùng khoá.
- `ts = open_time + 1h`: khớp FS_RESULT §0.1 (sai số float32 4.14e-08).

⇒ mọi lệch đều do **nguồn Vision biến động**, không phải lỗi generator.

## 5. Hệ quả cho pipeline (quan trọng)

`feat_v2_x1.parquet` (đầu vào S1) đang dùng được build từ **bản gốc** `CLOSES_1H.bin`. Nếu rebuild
từ bản tái lập: symbol delist (FTT/SC/RAY/USDC/BTCDOM…) sẽ có thêm giá close 2024–2025 ⇒ feature
`ret_*`/`vol_*` của các symbol này đổi ở đoạn cuối DEV. Nhưng các symbol này **không có dự báo
G015/OI sau delist** ⇒ gần chắc **không nằm trong pool S1** ⇒ ảnh hưởng S1 ≈ 0. **Chưa đo được định
lượng** — cần kiểm ở việc 4 (rebuild feat_v2_x1 + so parity) nếu muốn chắc.

**Khuyến nghị:** ghim `CLOSES_1H.bin` (đã có) làm input chuẩn; generator chỉ dùng để **mở rộng sang
2026** (đoạn mới), KHÔNG dùng để rebuild đoạn DEV cũ (sẽ lệch vì Vision đã đổi).

## 6. Tuân thủ

0 đọc/ghi 2026 (chỉ tải Vision 2021-01..2025-12; bản ghi `ts=2026-01-01 00:00` là close của nến
2025-12-31 23:00). Ghi ra `/home/ubuntu/f0_repro/` (thư mục mới), **KHÔNG** đụng file gốc. Python
dùng `logging` (không `print`). Tải mạng nhẹ (~4 phút, 627 symbol, giai nen trong bộ nhớ).
