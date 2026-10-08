# HOLDOUT2026_PROGRESS — dựng holdout 2026H1 (HO1)

Pre-reg `docs/prereg/PREREG_HOLDOUT2026H1.md` (35d03784 + ADDENDUM-1 0e3282a6). Seal ĐÓNG suốt HO1: không kernel 2026, không số hiệu năng 2026.
Thư mục làm việc Oracle: `~/claude_master/1003/ho1/` (dữ liệu lớn KHÔNG push). Lock nặng: `~/claude_master/1003/ho1/run_locked.sh <log> <cmd...>`.
Manifest json nhỏ: `docs/result/ho1/`.

| Bước | Trạng thái | Kết quả / md5 | Script |
|---|---|---|---|
| B1 pre-reg | XONG | 35d03784; ADDENDUM-1 0e3282a6 | — |
| B2 gate 8 seed | XONG | G-B2a PASS (0,99661/0,99691 vs d37969ee, 2025Q4); G-B2b PASS; train_ts_max 2025-12-31 23:44 +07; 2026: 260 602 dòng, 0 NaN. pred.bin: s42 22f69456, s7 a5e60871, s13 a411080f, s21 76ce7375, s99 56c42c0c, s123 764576ec, s777 3889a6c2, s2024 9f76dc5d (`gate/pred_s*/pred.bin`) | ho1_gate_build.py |
| B3 net015 2026 | XONG | G-B3 PASS (keys 4 517 610 = ref, spearman 1,0, max\|d\| 1,19e-7); RSS 6,2G (lock). `net015_2026/predict_wf_20260101.bin` sha256 bc3cddef… (4 587 093 rec, span 89d), `predict_wf_20260401.bin` sha256 100b7c63… (4 891 812 rec, 90d), 0 NaN. Tool1 2025–2026 cùng định dạng T1C2/40 cột/step 1 | ho1_net015_predict.py |
| B4 S1/bins 2026 | ĐANG | CLOSES 2026 Vision OK; G-B4a PASS (0/11 222 082 ô lệch); G-B4p PASS (Jaccard 1,0); G-B4b PASS (cut20251001 tái lập pred_s1a2x1 2025Q4 max\|d\| 0). Đang chạy lại với universe closes mở rộng 33 coin niêm yết 2026 (v1 thiếu → feat_cov 0,956) | ho1_closes2026.py, ho1_featv2_window.py, ho1_s1_2026.py |
| B5a market.bin | XONG (EXPLAINED) | `ds/market.bin` md5 34e33678…, n_2026 252 463 | ho1_market_build.py |
| B5b funding.bin | Cổng PASS (8e57d900); build CHỜ bins B4 | — | ho1_funding_build.py |
| B6 bundle + ticker 2026h1 + symbol | CHƯA | — | — |
| B8 parity C1–C3 + hiệu chuẩn net015 | CHƯA | C1 de-p1 650c386f, C2 gqsf-a1 ad26fd55, C3 nsel-m2-s42 cbc067f7 | — |

## Ghi chú
- `~/featv2/feat_v2_x1.parquet` đã bị xoá khỏi Oracle; thước G-B4a dùng `~/s1hpo/kaggle_ds/feat_v2_x1_keep9.parquet` (KEEP9 ép float32, md5 1aa3b974).
- Lộ thông tin nhỏ (khai báo): khi chẩn đoán pool S1 2026 đã in số dòng pool theo ngày 06-02..06-25 (phản ánh tần suất gate mở đầu tháng 6/2026). Không có PnL/giá trị dự báo.

## Việc còn lại
1. B4: build_map (X1_CUTS="20260101 20260401", X1_G015_DIR=net015_2026) → bins 2026 + G-B4c multiset.
2. B5b build funding.bin holdout; manifest dataset WFO mới.
3. B6: bundle Kaggle + ticker 2026h1 (181 file md5) + symbol thiếu mapper/pin.
4. B8: 3 kernel parity + hiệu chuẩn net015 → DỪNG báo MASTER.
