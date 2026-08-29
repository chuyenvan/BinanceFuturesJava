# PLAN — 1m UNFILTERED (train 15m / predict 1m), net@0.008 — 2026-08-11

> Uni chốt: chạy predict+WFO ở lưới 1m, GIỮ unfiltered (Trụ 1 đã thắng), NET_THR=0.008. Đây là campaign nhiều bước.
> File này = trạng thái + recipe để phiên sau tiếp NGAY.

## 0. Vì sao phải re-export (đừng dùng lại data 1m có sẵn)
- Các dataset Kaggle `funding-tool1-1m-<quý>` (2022→2026, tạo 8/9) là **FILTERED TOP_PCT=0.10** — chính universe canon đã THUA (−1,945 vs unfiltered +14,225). KHÔNG dùng cho hướng unfiltered.
- 15m unfiltered tool1 (`funding-tool1-features-unfiltered`) đã bị XÓA (dọn 8/9). Không còn nguồn unfiltered nào.
- ⇒ Phải export **Tool1 UNFILTERED 1m** mới. Một nguồn 1m phục vụ CẢ HAI: train đọc grid-filter→15m, predict đọc 1m.

## 1. Chặn kỹ thuật đã xác định (đọc code thật)
- `gen_funding_wf_predictions_1m.py`: `GRID_MIN` (SELECTOR_GRID_MIN) điều khiển CẢ train sampling LẪN predict cadence (dòng 89 filter; 272/287 assert LABEL step_min==GRID_MIN). `build_features_memmap` đọc Tool1 per-YEAR-glob rồi mới lọc.
- Decode 1m TRỌN 1 năm ≈ 193M rec×170B ≈ 33GB > RAM Kaggle 30GB → OOM lúc READ. `read_tool1` không có ts-range.
- **GIẢI**: export `.t1c.gz` đã chunk sẵn theo QUÝ (ExportFeaturesForPythonTool: cal.add MONTH,3). Sửa gen script đọc PER-QUÝ (không per-year-glob) → 1 quý unfiltered 1m ≈ 5-8GB structured, expand per-month → peak ~15-20GB, vừa RAM.
- Predict KHÔNG cần label 1m (chỉ cần feature 1m vùng OOS). Train vẫn dùng label 15m unfiltered net (đã có, dùng cho sweep +10,942).

## 2. Công cụ export (repo E:\...\BinanceFuturesJava HEAD=8741f85)
- Class: `com.binance.chuyennd.ai_ml.features.export.fundingv2.ExportFeaturesForPythonTool`
  - args: [0]=startYYYYMMDD [1]=endYYYYMMDD [2]=outputDir. Chunk 3 tháng → `features_<s>_to_<e>.t1c.gz`, stepMin=1.
  - Env: **`FF_UNFILTERED=1`** (bỏ EntrySignalFilter, xuất mọi alt), **`FF_GRID_MIN=1`** (grid 1m thật), `TICKER_SOURCE=file` (đọc ticker_*.bin, KHÔNG cần Oracle/Aerospike).
- Chạy trên **Kaggle** (đã có tiền lệ 8/9 filtered chạy Kaggle OK). Nguồn ticker: dataset `chuyendinh/hpo-ticker-daily` (10.7GB) + `hpo-ticker-2026` (2.7GB). Mẫu kernel Java-on-Kaggle: `label-export-2021..2025`, `ticker2026-build`.
- Jar build_ds/export: `binance-fresh-20260809.jar` (khớp code_sha 8741f85). Nếu Kaggle cần jar riêng cho ExportFeaturesForPythonTool → build từ repo (mvn) rồi đưa vào dataset kernel.
- ⚠️ Output unfiltered ~10× filtered: filtered quý ~80-206MB → unfiltered quý ~1-2GB, tổng 2023-2025 (12 quý) ~15-25GB. Kaggle output/quý OK; mỗi quý 1 dataset `funding-tool1-1m-unf-<q>` để tránh vượt giới hạn.

## 3. Phases (fire-and-forget, verify bước đầu)
1. **P1 — SMOKE**: export unfiltered 1m 1 quý (vd 2024Q1, universe đông) → đo size/RAM/thời gian/coin-count per-ts (xác nhận unfiltered THẬT, không dính filter). Verify record count hợp lý (hàng trăm coin/ts).
2. **P2 — FANOUT export**: 12 quý 2023Q1-2025Q4 (+ warmup train: 2021-2022 export ở 1m hoặc tái dùng 15m-nếu-có; train cần ≥2yr trước 2023). Mỗi quý 1 kernel → dataset.
3. **P3 — sửa gen script** (task #15): thêm PRED_GRID_MIN + đọc per-quý-file, per-month expand cho predict 1m. LABEL_MODE=net NET_THR=0.008. Verify parity cột FEAT (45 cột: f0..39 + 5 OI).
4. **P4 — predict 1m** trên Kaggle GPU → predict_wf 1m (~15GB) → build_ds TRÊN KAGGLE (Oracle 7.6G không chứa) → dataset wfo-ds-net1m-t008.
5. **P5 — fanout WFO** Kaggle-fleet (jobstore Oracle-local ns=test) → verdict per-window 12w → SO với 15m@0.008 (+10,942) và +14,225.

## 4. Kỳ vọng (risk) — đọc trước khi kỳ vọng nhiều
- Exit (SL/TP/trailing) ĐÃ chạy tick 1m; chỉ ENTRY-refresh là 15m. "Lên 1m" chỉ đổi tần suất vào/xoay lệnh.
- diff doc §8 đã BÁC cadence là lever thắng (g15 15m vẫn −9139). 1m có thể tăng độ phủ lệnh nhưng CHƯA có bằng chứng nâng PnL. Đây là exploratory, không phải kèo chắc.

## 5. Baseline để so (đã có, số thật)
- net 15m: 0.005=+9,908(pos69%) | **0.008=+10,942** | 0.012=+8,714 | 0.02=+11,738(dồn 2024, 25Q1 âm). Band robust = 0.005–0.008.
- maxFav 15m = −7,030 (thua). ret2 unfiltered 15m = +14,225 (dồn 2025Q4 33%).

## 6. Hạ tầng / vận hành
- SSH Oracle: key `~/.ssh/id_rsa_chuyennd_openssh` (id_rsa_chuyennd cũng OK), user ubuntu@161.118.212.3. Từ Windows dùng claude-code Bash (Git ssh). Cloud container + device VM KHÔNG route được Oracle.
- Kaggle CLI trên Oracle: `/home/ubuntu/kaggle_latest_venv/bin/kaggle`.
- Oracle = master (coordinator + Aerospike ns=test 3222 + build_ds); Kaggle = sim nặng. Oracle disk 95% (7.6G free) — dọn wfo_ds_net_t02(4.4G)+predwf_net_t02(1G) nếu bỏ nhánh 0.02.
- Report md `wfo_strategy_window.md` KHÔNG tin trực tiếp (bị ghi đè) — số per-window đọc từ `sweep/DONE_*.txt`.
