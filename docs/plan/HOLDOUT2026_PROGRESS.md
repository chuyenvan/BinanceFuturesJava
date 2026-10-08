# HOLDOUT2026_PROGRESS — dựng holdout 2026H1 (HO1)

Pre-reg `docs/prereg/PREREG_HOLDOUT2026H1.md` (35d03784 + ADDENDUM-1). Seal ĐÓNG suốt HO1: không kernel 2026, không số hiệu năng 2026.
Thư mục làm việc Oracle: `~/claude_master/1003/ho1/` (dữ liệu lớn KHÔNG push). Lock nặng: `~/claude_master/1003/ho1/run_locked.sh <log> <cmd...>`.

| Bước | Trạng thái | Kết quả / md5 | Script |
|---|---|---|---|
| B1 pre-reg | XONG | 35d03784 | — |
| B2 gate 8 seed | XONG | G-B2a PASS (pearson 0,99661 / spearman 0,99691 vs d37969ee, 2025Q4); G-B2b PASS; train_ts_max 2025-12-31 23:44 +07; 2026: 260 602 dòng, 0 NaN. pred.bin: s42 22f69456, s7 a5e60871, s13 a411080f, s21 76ce7375, s99 56c42c0c, s123 764576ec, s777 3889a6c2, s2024 9f76dc5d (`gate/pred_s*/pred.bin`, `gate/manifest_gate.json`) | research/analysis/ho1_gate_build.py |
| B5a market.bin | XONG (EXPLAINED, ADDENDUM-1 §1) | `ds/market.bin` md5 34e33678105275b3620d1c92c3510172, n_2026 252 463, 2 phút mơ hồ (`ds/market_meta.json`) | ho1_market_build.py |
| B5b funding.bin | Cổng PASS (G-B5f 8e57d900); build 2026 CHỜ bins B4 | `ds/funding_regen.json` | ho1_funding_build.py (`build --extra DIR --market ds/market.bin --out ds/funding.bin`) |
| B3 net015 2026 | ĐANG | G-B3 lần 1 FAIL do thiếu file quý trước (Tool1 chia quý UTC) + RSS 10,4G; đã vá build_rows/read_oi | ho1_net015_predict.py |
| B4 S1/bins 2026 | CHƯA | cổng G-B4a (feat_v2 2025Q4), G-B4p (pool ≥99%), G-B4b, G-B4c | — |
| B6 bundle + ticker 2026h1 + symbol | CHƯA | — | — |
| B8 parity C1–C3 + hiệu chuẩn net015 | CHƯA | C1 de-p1 650c386f, C2 gqsf-a1 ad26fd55, C3 nsel-m2-s42 cbc067f7 | — |

## Việc còn lại (theo thứ tự)
1. B3: chạy `run_locked.sh net015_2026/b3.log python3 ho1_net015_predict.py` → G-B3 PASS ⇒ `net015_2026/predict_wf_2026{0101,0401}.bin`.
2. B4: CLOSES_1H 2026 (Vision, `closes1h_build.py` tháng 2026-01..06) nối sau CLOSES_1H.bin ghim → feat_v2 cửa sổ (G-B4a) → ledger pool 2026 (p15 seed 42 B2, G-B4p) → S1 predict `s1a2x1_cut20251231.json` → `x1_build_map` (X1_CUTS="20260101 20260401") → bins 2026.
3. B5b build funding.bin holdout; manifest dataset WFO mới (market/pred×8/funding).
4. B6: bundle Kaggle mới + dataset ticker 2026h1 (181 file, md5 manifest), kiểm symbol thiếu mapper/pin.
5. B8: 3 kernel parity (seal đóng, SIM_END_DATE=20251231) + hiệu chuẩn net015 (ADDENDUM/pre-reg §4). PASS ⇒ DỪNG báo MASTER.
