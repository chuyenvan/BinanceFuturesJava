# VZ_REGISTRY — sổ đăng ký kho dữ liệu Binance Vision (Kaggle)

Thiết kế: `docs/plan/VZ_DATA_LAKE.md`. Branch code: `data/vz-lake` (worktree `~/claude_master/vz_wt`).
Owner thực thi: OpenClaw (UniDeep). Ngày: 2026-10-13. Trạng thái: **Phase 0 (pilot 2024-08) XONG — DỪNG chờ MASTER duyệt Phase 1.**

---

## 0. Preflight (Bước 0, chỉ đọc)

| Mục | Kết quả |
|---|---|
| Đĩa `/` | 194 GB, **37 GB trống** lúc đầu (82% dùng) — ⚠ dưới ngưỡng 40 GB của §4 B0, nhưng ≥ 30 GB của §5 suốt pilot (thấp nhất 35 GB) |
| RAM | 23 GB tổng, 11 GB dùng, 11 GB available |
| Tiến trình nền | chỉ dịch vụ sản xuất sẵn có (java 242, `liq_ws.py`) — **không đụng**; không job nặng của pilot chạy song song |
| Libs | `pyarrow 25.0.1`, `pandas 2.3.3`, `requests 2.25.1` — đủ, **không cần pip** |
| Kaggle API | `~/.kaggle/kaggle.json` (mode 600, owner `chuyendinh`), CLI 1.6.17 / server 2.2.2; `kaggle datasets list --mine` OK (21 dataset lúc đầu) |
| **Hạn mức Kaggle** | **200 GB / 1 dataset** · **200 GB tổng dataset private / tài khoản** · tối đa **50 file top-level / dataset** (nguồn: kaggle.com/docs/datasets) |
| Network allowlist | chỉ `data.binance.vision` + `s3-ap-northeast-1.amazonaws.com`; ép trong `vz_common.assert_allowed()` — host khác ⇒ `RuntimeError` |

## 1. Inventory (Bước 1) — toàn bộ lịch sử theo loại

| type | files | bytes | syms giữ |
|---|---|---|---|
| klines 1m | 22 252 | 29.51 GB | 900 |
| premiumIndexKlines 1m | 21 089 | 13.76 GB | 895 |
| markPriceKlines 1m | 22 519 | 16.46 GB | 896 |
| indexPriceKlines 1m | 21 800 | 17.55 GB | 892 |
| metrics (daily) | 580 868 | 6.19 GB | 907 |
| fundingRate (monthly) | 21 094 | 21.6 MB | 901 |
| **tổng** | **~689 622** | **~83.5 GB** | |

Manifest: `~/vz/manifest/<type>.csv.gz` (key,size,last_modified,checksum_key,sym,flag).

## 2. Pilot 2024-08 (Bước 2/3) — byte vào/ra theo loại

| ds | syms | rows | zip IN | parquet OUT | fetch | build | RAM đỉnh (build) | trùng | micro→ms |
|---|---|---|---|---|---|---|---|---|---|
| kline1m | 297 | 12 812 300 | 410 508 982 B (391.5 MiB) | 430 529 122 B (410.6 MiB) | 48.1 s | 89.4 s | 233 MB | 0 | 0 |
| basis1m | 299 | 12 908 417 | 695 477 854 B (663.3 MiB)¹ | 521 172 458 B (497.0 MiB) | 134.0 s | 191.4 s | 218 MB | 0 | 0 |
| metrics5m | 281 | 2 390 446 | 91 020 489 B (86.8 MiB) | 122 179 678 B (116.5 MiB) | 808.9 s | 34.5 s | 141 MB | 0 | 0 |
| funding | 302 | 36 302 | 282 638 B | 570 468 B | 28.5 s | 1.6 s | 124 MB | 0 | 0 |
| **tổng** | | **28 147 465** | **1 197 289 963 B (1.115 GiB)** | **1 074 451 726 B (1.001 GiB)** | | | | | |

¹ basis IN = premium 207 634 563 + mark 231 124 561 + index 256 718 730.
**RAM đỉnh toàn pilot = 508 MB** (fetch metrics, 4 luồng × file nhỏ).

## 3. Validate V1–V6 (Bước 4)

| ds | V1 checksum | V2 phút/(sym,ngày) | V3 OHLC/taker | V4 CLOSES_1H | V5 basis | V6 tái lập |
|---|---|---|---|---|---|---|
| kline1m | **PASS** (297 ok/0 bad/0 missing) | **PASS** (thiếu 0.0738%) | **PASS** (0 vi phạm / 12.81M rows) | **PASS** (183/183 giờ, khớp 100%, \|Δ\|/close ≤ 5.28e-8) | n/a | **PASS** (sha `ea78c056…` trùng) |
| basis1m | **PASS** (916 ok = 299+309+308) | n/a | n/a | n/a | **PASS** (p99 mark 0.19%, prem 0.25%) | **PASS** (sha `bfceeb35…`) |
| metrics5m | **PASS** | n/a | n/a | n/a | n/a | **PASS** (sha `196ff835…`) |
| funding | **PASS** | n/a | n/a | n/a | n/a | **PASS** (sha `25635ce7…`) |

Ghi chú V5: p99 tính **toàn tháng trên các dòng active**; **loại 14 symbol có kline stale 0-volume** của Binance
(AGIX, CTK, CVX, DGB, GLMR, IDEX, MDT, OCEAN, RAD, SLP, SNT, STPT, STRAX, WAVES). Nếu tính cả các symbol stale
thì p99(mark/kline) = 45.7% ⇒ FAIL — đây là placeholder của Binance (giá đóng băng, `count=0` cả tháng), không phải lỗi pipeline
(ADA/BTC/ETH khớp tới <0.3%). Xem "Lệch thiết kế" #3.

## 4. Ngoại suy 2020-01 → 2026-09 (81 tháng, từ manifest thật)

zip IN tổng = **83.40 GB**. Áp tỉ lệ OUT/IN của pilot theo ds:

| ds | zip IN (2020-01→2026-09) | OUT ước tính |
|---|---|---|
| kline1m | 29.51 GB | 30.95 GB |
| basis1m | 47.77 GB | 35.80 GB |
| metrics5m | 6.10 GB | 8.19 GB |
| funding | 0.02 GB | 0.04 GB |
| **tổng** | **83.40 GB** | **≈ 74.98 GB** |

⛔ **VƯỢT ngưỡng §3 (> 60 GB Kaggle)** ⇒ theo runbook: **DỪNG, báo MASTER** trước Phase 1.
Thời gian tải ước tính ≈ **19.5 h** (< 48 h, OK) — chi phối bởi metrics (571 795 file nhỏ daily ≈ 15 h).
Build ≈ 6 h + V6 (rebuild) ≈ 6 h ⇒ tổng pipeline ~31 h. Vẫn nằm trong hạn mức 200 GB Kaggle.

## 5. Upload Kaggle (Bước 5)

| Mục | Giá trị |
|---|---|
| Slug | **`chuyendinh/vz-pilot-202408`** (PRIVATE, KHÔNG `--public`) |
| Version | **1** (`datasets create -r skip`), status `ready` |
| Files | README.md, manifest.csv, validate.json, kline1m-2024-08.parquet, basis1m-2024-08.parquet, metrics5m-2024-08.parquet, funding-2024-08.parquet |
| md5 | kline1m `300769e64753a18722dd943812d98b73` · basis1m `abfd8e4894e5c0ac924ac408c004f343` · metrics5m `8cf9ffdaebf99e3c71034c513844c7e0` · funding `c24c64b5836241fa1f7418f1a86ab647` |
| sha256 | kline1m `ea78c056…` · basis1m `bfceeb35…` · metrics5m `196ff835…` · funding `25635ce7…` |
| Kiểm tra | `datasets files` khớp tên+size 7/7; **tải ngược `kline1m-2024-08.parquet` sha256 TRÙNG** `ea78c056…` |

## 6. Lệch thiết kế / quyết định

1. **Đĩa 37 GB trống** (< 40 GB §4 B0). Vẫn ≥ 30 GB (§5) suốt pilot (min 35 GB) nên tiếp tục; cần dọn trước Phase 1.
2. **Ngoại suy 75 GB > 60 GB** — cao hơn ước lượng §2 (~35 GB) vì symbol tăng mạnh 2025–2026 (kline zip 2025 = 8.03 GB vs 2024 = 5.11 GB) ⇒ chạm cổng dừng §3.
3. **V5 định nghĩa lại = p99 toàn tháng trên dòng active**; loại 14 symbol kline stale 0-volume (Binance). Bản strict all-rows FAIL (45.7%). Đề xuất MASTER chốt: bỏ stale khỏi V5 hay giữ nguyên FAIL.
4. **`kaggle -r skip` bỏ qua thư mục con** ⇒ layout upload là **flat** (`<ds>-2024-08.parquet`) thay vì cây `<ds>/<YYYY>/` trong §2.
5. Thêm module dùng chung `vz_common.py` (allowlist, path, sha256, s3_list phân trang).
6. Zip giữ lại tới **sau V6** rồi mới xoá (`VZ_KEEP_ZIP=1`) để V6 build lại được — §3 ghi xoá ngay sau parse.
7. Chỉ **~300 symbol** có dữ liệu 2024-08 (monthly) dù tổng ~900 symbol ⇒ đa số niêm yết sau 2024-08.

## 7. Code (branch `data/vz-lake`)

`research/data/vz/`: `vz_common.py` · `vz_inventory.py` · `vz_fetch.py` · `vz_build.py` · `vz_validate.py` · `vz_upload.sh`.
Dữ liệu: `~/vz/{manifest,tmp,out,reports,state,logs}`.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
