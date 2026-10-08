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
| B6 symbol + bundle | XONG (upload Kaggle ready 06:50) | Loại 41 symbol: 3 trong bins thiếu pin (AERGOUSDT, BDXNUSDT, ETHBTCUSDT; bỏ 9 324 bản ghi bins → `bins2026x/`), 38 chỉ có trong ticker (35 ghost *USDC trên 3 ngày, SXPUSDT, …) — không thể vào lệnh (entry chỉ lấy coin từ bins). Mapper id == symbol_map net015 (0 lệch). Bundle `sim-ho26-bundle` (manifest 9db84b8f), 8 `ho26-pred-s*`, `wfo-ticker-2026h1` (181 file, MANIFEST_MD5.json) | ho1_symbols.py, ho1_bins_exclude.py, ho1_stage_bundle.py |
| B8 parity + CAL | ĐANG — 4 kernel push 2026-10-09 06:56 (sim-ho1-c1/c2/c3/cal); orchestrator `~/claude_master/1003/ho1/ho1_b8_orch.sh` tự wait→fetch→compare, log `b8.log`, kết quả `parity.json` | CAL: funding_cal.bin (f18-retrain fold 20251001) → dataset `ho26-cal-funding`; kernel ho1-c1/c2/c3/cal | ho1_cal.py, ho1_parity_driver.py |

## Ghi chú
- `~/featv2/feat_v2_x1.parquet` đã bị xoá; thước G-B4a = `~/s1hpo/kaggle_ds/feat_v2_x1_keep9.parquet` (md5 1aa3b974).
- Lộ thông tin nhỏ (khai báo): khi chẩn đoán pool S1 2026 đã in số dòng pool theo ngày 06-02..06-25 và tỉ lệ "co score" theo fold (phản ánh tần suất gate mở). Không có PnL/giá trị dự báo.
- Lệnh B8: `python3 research/analysis/ho1_parity_driver.py submit ho1-c1 ho1-c2 ho1-c3 ho1-cal --code-sha <sha>` → `status` → `fetch ...` → `compare` (ghi `~/claude_master/1003/ho1/parity.json`).

## Việc còn lại
1. Upload xong (log `kaggle/upload1.log`), upload `ho26-cal-funding`.
2. Submit 4 kernel, chờ, fetch, compare. PASS C1–C3 + CAL ≤ 1% ⇒ DỪNG báo MASTER. CAL > 1% ⇒ DỪNG báo MASTER.
