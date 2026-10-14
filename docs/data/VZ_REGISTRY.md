# VZ_REGISTRY — sổ đăng ký kho dữ liệu Binance Vision (Kaggle)

Thiết kế: `docs/plan/VZ_DATA_LAKE.md`. Branch code: `data/vz-lake` (worktree `~/claude_master/vz_wt`).
Owner thực thi: OpenClaw (UniDeep). Ngày: 2026-10-13. Trạng thái: **Phase 1a XONG — cổng §1.6 ĐẠT — đang chạy 1b (theo năm).**

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

## 8. Phase 1a — tối ưu mã hoá + đo lại (2024-08, kline1m + basis1m)

Mã hoá thực dùng (VZ_ENC=plaindelta, mặc định): `ts`=DELTA_BINARY_PACKED (tắt dictionary cho ts),
`sym`=dictionary, **các cột float để PLAIN**, zstd **level 9**, row group = 1 symbol.

⚑ **LỆCH THIẾT KẾ (quan trọng) — §1.2 `use_byte_stream_split` phản tác dụng:** đo trên 40 symbol 2024-08:
| biến thể | kline MB | basis MB |
|---|---|---|
| v1 (zstd6, default) | 63.91 | 62.27 |
| **plain + DELTA ts + zstd9** | **46.34** | **46.12** |
| §1.2 literal (byte_stream_split + DELTA ts) | 76.11 | 49.69 |

BSS làm kline **+19%** (76.11 vs 46.34). Xác nhận: pyarrow **bỏ qua** `use_byte_stream_split` nếu không kèm `column_encoding`;
khi bật kèm thì high-entropy mantissa planes làm zstd nén kém hơn. Nguồn lợi thật = **DELTA_BINARY_PACKED trên `ts`**.
⇒ Để đạt cổng §1.6, dùng plain+delta (BSS vẫn chọn được qua `VZ_ENC=bss`). Cần MASTER chốt.

| ds | rows | sym | stale rows | v1 bytes | **v2 bytes** | Δ |
|---|---|---|---|---|---|---|
| kline1m | 12 812 300 | 297 | 907 987 | 430 529 122 | **306 618 954** | −28,8% |
| basis1m | 12 908 417 | 299 | 1 004 630 | 521 172 458 | **332 170 464** | −36,3% |

- **So nội dung v1↔v2: PASS tuyệt đối** (bit-exact float64) — kline 12.81M dòng, basis 12.91M dòng, 0 lệch; chỉ khác cột mới `active` + bỏ `prem_open`.
- **Validate**: kline V1 V2 V3 V4 V6 PASS; basis V1 V5 V6 PASS. V4 khớp CLOSES_1H 183/183 (≤5,28e-8); V5 p99 active mark 0,19% · prem 0,25%; stale 684 759 dòng / 14 symbol (thông tin).
- **Version 2** `chuyendinh/vz-pilot-202408` (kline 292MB, basis 317MB; metrics/funding giữ mã hoá v1). Tải ngược sha256 **TOÀN BỘ 2 file khớp**.
- **Kernel đọc kiểm** `chuyendinh/vz-readcheck-202408` (CPU, private, 1 slot): pandas 2.3.3 / **pyarrow 23.0.1** đọc OK; schema `active:bool` đúng; md5 cột ts kline `45e696981c22…` / basis `a637ae7eb593…` **khớp local**.

### Cổng §1.6 (sau 1a)
- Ngoại suy VZ (kline+basis mã hoá mới; metrics/funding mã hoá cũ): kline 22,04 + basis 22,82 + metrics 8,31 + funding 0,04 = **53,2 GB ≤ 55 GB** ✓
- Dataset private đang dùng ≈ **16,7 GB** ⇒ 16,7 + 53,2 + 40 (dự phòng Phase 2) = **109,9 GB ≤ 180 GB** ✓
- **KẾT LUẬN: ĐẠT ⇒ tự sang 1b (không chờ).**

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>

## 9. Fix V5 NaN (2026-10-13)
- Bug: `np.percentile` trong V5 trả NaN khi bất kỳ dòng active nào có mark/prem NaN (basis1m 2024-02 chỉ 186 NaN/10.599.908 dòng) ⇒ FAIL GIẢ.
- Fix: `np.nanpercentile` + lọc finite trước (hàm `p99`), thêm `n_nan_active_rows` vào report. Ngưỡng §1.5 giữ nguyên (mark<1%, prem<2%, trên dòng ACTIVE).
- Xác nhận: basis1m 2024-02 → V5 PASS (p99 prem 0,0026; mark 0,0017).
- Mã hoá chốt: `VZ_ENC=plaindelta` (float plain + ts DELTA_BINARY_PACKED), KHÔNG đổi nữa.

## 10. Fix idempotency tháng pilot (2026-10-13 22:51)
- Bug: 2024-08 là tháng pilot — fetch state "done" nhưng ZIP đã bị xoá ⇒ build/V6 không có input ⇒ metrics5m parquet rỗng (969 B) ⇒ V6 FAIL (không phải lỗi dữ liệu).
- Fix driver `vz_phase1.py`: `ensure_fetch()` phát hiện state done nhưng ZIP thiếu (đếm < n_ok) ⇒ xoá state + FETCH LẠI; `build_done()` chặt hơn (rows>0, file tồn tại, size == parquet_bytes).
- Reset 2024-08 cho metrics5m + funding (xoá state fetch/build + parquet + report) để BUILD LẠI mã hoá mới rồi V6 PASS. Rà toàn bộ state build: chỉ 1 anomaly (metrics5m 2024-08).

## 11. Siết điều kiện "tháng XONG" (2026-10-14 06:10)
- `vz_build.py` ghi thêm `enc` (=plaindelta) + `build_version`=2 vào build state.
- `vz_phase1.py` `build_done()`: tháng chỉ XONG khi state có `enc==plaindelta` + `build_version>=2` + rows>0 + parquet tồn tại & size == parquet_bytes (không dựa vào việc file parquet có sẵn).
- Backfill 30 state build sẵn có: XÁC MINH mã hoá thật trong parquet (ts=DELTA_BINARY_PACKED, float=PLAIN, zstd) rồi mới ghi `enc` — đủ 30/30 đúng, 0 phải build lại.
- Xoá thủ công 2 file pilot mã hoá cũ (metrics5m/funding 2024-08) + report + state → build lại.
- Dọn: `~/vz/tmp/tmpiomm0faf`, `~/vz/tmp/_v6`, `~/vz/pilot_v1` (908MB). Đĩa trống 37 GB.

## 12. Sửa định nghĩa V2 sau một FAIL (2026-10-14)
- FAIL kline1m 2024-09 (V2): V2 CŨ `missing_min_frac=0,001118 (0,1118%)` ⇒ FAIL. Định nghĩa cũ "số ngày có dữ liệu × 1440" phạt oan symbol niêm yết/gỡ giữa tháng.
- ĐỊNH NGHĨA MỚI: phút kỳ vọng mỗi symbol/tháng = **mọi phút từ ts ĐẦU đến ts CUỐI có dữ liệu**. Giữ ngưỡng thiếu ≤ 0,1 %.
- **2024-09: V2 MỚI `0,0` (0 phút thiếu / 13.168.462 phút kỳ vọng, 316 symbol) ⇒ PASS.**
- Xác nhận nguyên nhân: UXLINKUSDT first=2024-09-15 15:00 · last=2024-09-30 23:59 (niêm yết mid-month, rows=span=22140, missing=0, cutFirst=900′). MATICUSDT first=2024-09-01 00:00 · last=2024-09-11 09:42 (gỡ/đổi tên, rows=span=14983, missing=0, cutLast=857′). Toàn bộ "thiếu" cũ nằm ở ngày niêm yết/gỡ.
- BÁO THÊM (info, không FAIL): `cut_first_last_*` (phút cắt ngày đầu/cuối) + danh sách khoảng trống LIÊN TỤC > 60′ giữa khoảng niêm yết. Toàn 2024: **0 khoảng trống > 60′**.
- Chạy lại V2 (không build lại, V6 giữ nguyên) cho kline1m 2024-01→09, ghi đè validate.json: tất cả V2 PASS (0,0).

## 13. Fix upload/verify too early (2026-10-14 10:10)
- Job dừng ở UPLOAD: verify `datasets.get` 403 khi dataset còn "being created" ⇒ abort. XÁC MINH không phải lỗi thật: `vz-kline1m-2024` = ready, 12 file khớp 12 local.
- Fix `vz_phase1.py`: `upload_auto()` → sau create/version **POLL `datasets status` tới ready** (backoff, tối đa ~20'), 403/timeout chỉ CHỜ; `remote_names()` retry khi 403. Bỏ qua upload nếu dataset đã có đủ file. Thêm guard đĩa <30 GB (chỉ khi còn việc cần làm).

## P1b kline1m (2024)
- slug `chuyendinh/vz-kline1m-2024`; files 12; bytes 3833848788; rows 155015111; syms~370; gov DEV

## P1b kline1m (2024)
- slug `chuyendinh/vz-kline1m-2024`; files 12; bytes 3833848788; rows 155015111; syms~370; gov DEV

## P1b basis1m (2024)
- slug `chuyendinh/vz-basis1m-2024`; files 12; bytes 4084338069; rows 153683583; syms~374; gov DEV
