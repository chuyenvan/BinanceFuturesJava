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

## HO2 (2026-10-09 08:20–) — cổng hiệu chuẩn + mở seal (agent HO2, MASTER quyết ADDENDUM-2)
Thư mục Oracle: `~/claude_master/1009/ho26/` (dữ liệu lớn KHÔNG push). Kết quả nhỏ: `docs/result/ho2/`.

| Bước | Trạng thái | Kết quả / hash | Script |
|---|---|---|---|
| ADDENDUM-2 | XONG | 1682a311 (quyết định 1–4), 2691816d (§2a artifact + cổng A chốt trước đo), 8fe35b23 (§5 = PHƯƠNG ÁN A) | — |
| Tìm artifact | XONG | JSON gốc `predwf_G015/model_f15_4h` mất (đĩa + output Kaggle bị ghi đè); dùng ONNX export của chính booster đó `deploy_242_l3/models/g015x26_f15_cut20251001.onnx` 7921ceaf; dự đoán gốc fold 20251001 lấy từ backup Kaggle `predwf-g015x26-gate` (sha e03f0e58) | — |
| Cổng A (DEV 2025Q4) | **PASS** | A0 sha OK; A1 khoá 4 517 610 == gốc, max\|Δ\| 4,77e-7; A2c map(gốc) == bins DEV md5 5ebae929 (byte); A2 max\|Δ\| 4,77e-7, 0 ô > 1e-6, p1..p3 trùng bit (`gateA.json`) | ho2_net015_onnx.py |
| net015 2026 (A) | XONG | predict-only ONNX: 20260101 sha 8df74093 (4 587 093 rec), 20260401 406e527f (4 891 812), NaN 0; RSS 6,1G (lock) | ho2_net015_onnx.py |
| bins 2026 (A) | XONG | x1_build_map + S1 2026 HO1 (`pred_ho26s1`); G-B4c PASS; loại 3 symbol (như B6) → `bins2026Ax` | ho2_chain.sh |
| funding.bin + bundle | XONG | funding.bin md5 0700a96f (đoạn < 2026-01-01 +07 == DEV byte, prefix_equal); bundle mới `sim-ho26a-bundle` (market 34e33678, pred s42 22f69456 giữ HO1) | ho2_stage_bundle.py |
| Parity lại C1–C3 (seal đóng, bundle `sim-ho26a-bundle`) | **PASS** 10:22 | C1 ff3ce513 n 2517 vs de-p1: 0 cột lệch, chỉ in float32 trùng bit (volume 4, quantity 1); C2 ad26fd55 == gqsf-a1 (n 3541); C3 cbc067f7 == nsel-m2-s42 (n 7603); mọi kernel: jar/override/pred/TICKER26 181/181/mapper/penalty/không unseal OK (`docs/result/ho2/parity_ho2.json`) | ho26_queue.py pha 0 |
| 48 kernel holdout (SEAL MỞ 10:22) | ĐANG CHẠY | orchestrator PID 2866443 (Oracle); trạng thái `~/claude_master/1009/ho26/queue_status.tsv` (slug/status/md5/n/parity/giờ — không eq/PnL); out `~/kaggle_sim/out/ho26-<cfg>-<b|s>-s<seed>`; KHÔNG chấm (2 scorer độc lập vòng sau) | ho26_queue.py pha 1 |

Lộ thông tin nhỏ (khai báo): log `x1_build_map` in tỉ lệ dòng "co score" theo fold 2026 (phản ánh tần suất gate mở, như HO1). Không PnL/giá trị dự báo.

HO2 vận hành: 2 kernel đầu `ho26-b0-b-s42`, `ho26-b0-s-s42` COMPLETE + parity tự động PASS (11:06/11:10; ~44–48′/kernel B0; C2/C3 DEV 52–54′ ⇒ K24/M2 holdout ước ~60–65′). ETA 48 kernel ≈ 22–24 h từ 10:22 ⇒ ~2026-10-10 08:00–11:00 +07.
Kiểm tiến độ: `tail -n 60 ~/claude_master/1009/ho26/queue_status.tsv; ps -p $(cat ~/claude_master/1009/ho26/queue.pid) -o pid,etime`. Orchestrator chết ⇒ resume (state.json): `cd ~/claude_master/1009/ho26 && setsid nohup python3 ho26_queue.py >> queue.out 2>&1 < /dev/null &`. Việc còn lại (vòng sau): 2 scorer độc lập commit TRƯỚC khi đọc printDone/equity 2026; chấm 1 lần theo §1.

## HO3 (2026-10-10 08:10–) — kéo dài holdout tới 2026-09-30 (agent HO3)
Pre-reg ADDENDUM-3 `44d45ca1` (commit TRƯỚC mọi bước; chưa nhìn số Q3). Thư mục Oracle `~/claude_master/1003/ho3/`. Kết quả nhỏ `docs/result/ho3/` (chi tiết `HO3_B1B2.md`).

| Bước | Trạng thái | Kết quả | Script |
|---|---|---|---|
| B0 ADDENDUM-3 | XONG | 44d45ca1 | — |
| B1 kho dữ liệu | XONG | kline 242 tới 10-09 (0 phút thiếu Q3); kline local/market_data_object local tới 08-13; funding local chết 07-07, 242 sống; OI ghim tới 06-30 23:55 UTC; store gate/Tool1/nhãn tới 07-01 (Tool1/nhãn = Java exporter) | `ho3_b2_kline_as.py --probe`, `ho3_gaps.py` |
| B2 validate chéo | **FAIL ⇒ DỪNG, báo MASTER** | K1 242 vs ticker HO26 H1 99,99961% PASS; Vision vs ticker HO26: T3 99,997%, gãy từ 04-25 (T5 84,3%, T6 86,7%); Vision vs 242 Q3 91,2% FAIL; funding Vision vs local 99,881% mốc (giá trị 100%, thiếu 37 symbol) FAIL chặt, 242 vs local 98,98% + 934 lệch giá trị; OI Vision rebuild: oi_delta 99,96%, ls/taker 83,1% (lệch nguyên ngày, vd 06-15) FAIL; market inline ≤1e-6 44,2% FAIL, store re-read 99,37% FAIL; gate momentum×3 FAIL (trích audit) | `ho3_b2_*.py` |
| B3 dựng Q3 | KHÔNG LÀM (luật B2) | — | — |
| B4 parity | KHÔNG LÀM | — | — |
| B5 48 kernel | KHÔNG LÀM — 0 kernel, 0 dataset Kaggle | — | — |

Việc còn lại: MASTER chọn A/B/C ở `HO3_B1B2.md` và viết ADDENDUM-4 (thước B2 mới) TRƯỚC khi dựng. Nếu A: writer Python ticker Java-serialized (cổng md5 byte vs `ticker_2026*.bin.gz` H1) → Tool1/nhãn bằng Java exporter trên Kaggle (`TICKER_SOURCE=file`) → store gate Q3 bằng `devexport_202609.py` (funding/market theo nguồn đã chốt) → p15 8 seed → net015 ONNX + S1 → funding.bin trên Kaggle (Oracle còn 3,6G) → parity B4 → orchestrator (mẫu `ho26_queue.py`, slug `ho3-*`, `SIM_END_DATE=20261001`, `ticker_min_days=2099`).
