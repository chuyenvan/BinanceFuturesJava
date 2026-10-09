# HOLDOUT2026_PROGRESS — dựng holdout 2026H1 (HO1)

Pre-reg `docs/prereg/PREREG_HOLDOUT2026H1.md` (35d03784 + ADDENDUM-1 0e3282a6). Seal ĐÓNG suốt HO1: không kernel 2026, không số hiệu năng 2026.
Thư mục làm việc Oracle: `~/claude_master/1003/ho1/` (dữ liệu lớn KHÔNG push). Lock nặng: `~/claude_master/1003/ho1/run_locked.sh <log> <cmd...>`.
Manifest json nhỏ: `docs/result/ho1/`.

| Bước | Trạng thái | Kết quả / md5 | Script |
|---|---|---|---|
| B1 pre-reg | XONG | 35d03784; ADDENDUM-1 0e3282a6 | — |
| B2 gate 8 seed | XONG | G-B2a PASS (0,99661/0,99691); G-B2b PASS. pred.bin: s42 22f69456, s7 a5e60871, s13 a411080f, s21 76ce7375, s99 56c42c0c, s123 764576ec, s777 3889a6c2, s2024 9f76dc5d | ho1_gate_build.py |
| B3 net015 2026 | XONG | G-B3 PASS (spearman 1,0, max\|d\| 1,19e-7, RSS 6,2G). predict_wf_20260101 bc3cddef…, 20260401 100b7c63… | ho1_net015_predict.py |
| B4 S1/bins 2026 | XONG | CLOSES 2026 Vision md5 fcbed3b6 (627 DEV + 33 coin niêm yết 2026 — chỉ vào cross-section OI từ close đầu tiên); G-B4a PASS 0/11 222 082 ô; G-B4p PASS Jaccard 1,0; G-B4b PASS max\|d\| 0; pool 2026 5 870 333 dòng, feat_cov 0,9989; G-B4c PASS (multiset). bins (`bins2026/`) 908eca5e… / e22be70f… | ho1_closes2026.py, ho1_featv2_window.py, ho1_s1_2026.py, ho1_bins_check.py |
| B5 dataset WFO | XONG | market.bin 34e33678 (EXPLAINED); funding.bin 272f888c (5 550 456 412 B, đoạn < 2026-01-01 +07 == DEV byte, bins đã loại 3 symbol); pred.bin s42 22f69456 | ho1_market_build.py, ho1_funding_build.py |
| B6 symbol + bundle | XONG (ticker 2026h1 version 2 08:11: md5 Kaggle .bin == gunzip Oracle 181/181, `ticker26_md5_check.json`) | Loại 41 symbol: 3 trong bins thiếu pin (AERGOUSDT, BDXNUSDT, ETHBTCUSDT; bỏ 9 324 bản ghi bins → `bins2026x/`), 38 chỉ có trong ticker (35 ghost *USDC trên 3 ngày, SXPUSDT, …) — không thể vào lệnh (entry chỉ lấy coin từ bins). Mapper id == symbol_map net015 (0 lệch). Bundle `sim-ho26-bundle` (manifest 9db84b8f), 8 `ho26-pred-s*`, `wfo-ticker-2026h1` (181 file, MANIFEST_MD5.json) | ho1_symbols.py, ho1_bins_exclude.py, ho1_stage_bundle.py |
| B8 parity + CAL | XONG — **DỪNG (CAL > 1%)** | C1 PASS* md5 ff3ce513 (n 2517 == de-p1, eq 131908; 5 ô lệch CHỈ cách in float: 4 volume + 1 quantity, float32 cùng bit — quantity nằm ngoài chữ luật 'cột volume' ⇒ MASTER xác nhận); C2 PASS ad26fd55 == gqsf-a1; C3 PASS cbc067f7 == nsel-m2-s42; CAL: trước 2025-10-01 trùng 2235/2235 lệnh (thiết lập đúng), Q4 symdiff 125 (56 chỉ C1, 69 chỉ CAL; T10 41/43, T11 15/26) = 44,3% lệnh Q4 = 4,97% lệnh DEV > 1% ⇒ DỪNG báo MASTER. M-cal1 mô tả: flip bản lề 0,29 = 0,81% ô, spearman 0,99495 | ho1_parity_driver.py, ho1_b8_diag.py → docs/result/ho1/parity_b8.json, b8_diag.json |

## HO1b (2026-10-09 07:55–) — phát hiện sau B8
- **Ticker 2026h1 trên Kaggle THIẾU 60/181 file** (20260101..20260301): staging `kaggle/wfo-ticker-2026h1` hardlink vào symlink tương đối `daily/…` ⇒ symlink hỏng, Kaggle bỏ qua. 121 file có mặt md5 == md5(gunzip Oracle) (`ticker26_md5_check_v1.json`). Khối TICKER26_MD5 trong kernel B8 KHÔNG hiệu lực (Kaggle giải nén .gz → .bin, tên lệch ⇒ miss=181). Sửa: `link()` dùng realpath (ho1_stage_bundle.py), restage 181 file 2 486 474 625 B md5 == MANIFEST; version 2 dataset (08:11) ⇒ kernel md5-only `sim-ho1-t26md5`: **181/181 md5 khớp, 0 thiếu, 0 thừa (PASS)**. Kernel B8 C1–C3/CAL dùng v1 nhưng seal đóng không đọc ticker 2026 ⇒ parity không bị ảnh hưởng.
- Bug `q4keys` (start là chuỗi 'YYYYMMDD HH:MM' +07, không phải ms) đã sửa trước khi compare chạy.
- Đuôi 7 h (2026-01-01 00:00–06:59 +07) nằm trong sim DEV (SIM_END_DATE=20251231 UTC) nhưng DEV B0/K24/M2 không có lệnh start sau 2025-11-21 ⇒ thay 420 dòng pred không ảnh hưởng parity.

## Ghi chú
- `~/featv2/feat_v2_x1.parquet` đã bị xoá; thước G-B4a = `~/s1hpo/kaggle_ds/feat_v2_x1_keep9.parquet` (md5 1aa3b974).
- Lộ thông tin nhỏ (khai báo): khi chẩn đoán pool S1 2026 đã in số dòng pool theo ngày 06-02..06-25 và tỉ lệ "co score" theo fold (phản ánh tần suất gate mở). Không có PnL/giá trị dự báo.
- Lệnh B8: `python3 research/analysis/ho1_parity_driver.py submit ho1-c1 ho1-c2 ho1-c3 ho1-cal --code-sha <sha>` → `status` → `fetch ...` → `compare` (ghi `~/claude_master/1003/ho1/parity.json`).

## Việc còn lại
1. **MASTER quyết CAL** (4,97% lệnh DEV > 1%): nguyên nhân lệch Q4 = net015 retrain (f18-retrain) ≠ G015x26 gốc ở mức quyết định lệnh dù flip bản lề chỉ 0,81% ô (path-dependence khuếch đại). Không tự vá/tune. Các hướng để MASTER chọn: chấp nhận + khai báo trong pre-reg; hoặc thước CAL khác (khai trước); hoặc đổi nguồn bins 2026.
2. MASTER xác nhận C1 (1 ô quantity cùng hiện tượng in float32 như volume).
3. Holdout 48 kernel (vòng sau, MASTER mở seal): SIM_END_DATE=20260701 (ADDENDUM-1), `ticker_min_days=2007`, dataset `wfo-ticker-2026h1` bản mới nhất (v2); sửa khối TICKER26_MD5 trong kernel so tên `.bin` với md5 gunzip (`t26md5_out`/`ticker26_oracle_gunzip_md5.json`).
