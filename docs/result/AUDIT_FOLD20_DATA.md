# AUDIT_FOLD20_DATA — nguồn dữ liệu train của model gate p15 `fold_20` (md5 `8ec99757…`)

Ngày 2026-10-21, agent kiểm toán. CHỈ ĐỌC/ĐO: không retrain, không ghi store, không đọc 242, không REST Binance.
Bối cảnh: `docs/plan/V11_COLLECTOR_SETTLE.md` §6.1 "rủi ro provenance (chưa đóng)" — bản `gate15m_v2_full.csv` (06-23,
md5 `7ef6f92b`) khớp store `market_data_object` 99,4 % ở 2025 nhưng ≈ 0,1 % ở 2021–2023, 34 % ở 2024 ⇒ nghi store bị sinh
lại SAU khi train. Script + JSON: `docs/result/audit_1021/`.

## Kết luận (rủi ro trước)

1. **Rủi ro provenance §6.1 ĐÓNG — giả thuyết "store sinh lại SAU train" BÁC BỎ.** Store Oracle được sinh lại **trước** khi
   train: `market_data_object` 2021-01 → 2026-05 ghi lần cuối **2026-06-29 23:35 / 2026-07-07 22:49–23:10 (+07)** (LUT Aerospike),
   `kline_1m_opt` ≤ 07-07 (chỉ 2026-06/07 ghi lại 08-05/08-13), `funding_data` 07-08 (+ 90 symbol mới 08-05). `fold_20` train
   ~2026-08-06. `gate15m_v2_full.csv` (06-23) là bản CŨ trước lần sinh lại ⇒ lệch của nó không nói gì về `fold_20`.
2. **File train xác định được (tương đương bit):** Kaggle `chuyendinh/gate-dataset-full` v1 (2026-08-08 02:32, `gate_dataset_full.csv`
   1 059 933 426 B, md5 **`a1c78e2faeb34856a5e332e3530524a3`**, 2 889 623 dòng) = `chuyendinh/bdchain-gate-store` (10-01, cùng md5)
   = Oracle `~/claude_master/gvz/store/gate_dataset_full.csv`. File CSV gốc của lượt train (`csvStore` = `~/claudedata/wfo_feature_store.csv`
   của `WFOGateRunner` 08-06) KHÔNG còn (bị ghi đè bởi bản smoke 166 836 dòng); `fs_full.csv` (08-18) là lượt khác (model
   `4ac9a576` ≠ `8ec99757`). Không có kernel Kaggle nào train gate (WFOGateRunner chạy trên Oracle bằng `~/envs/xgb-env`, xgboost 3.2.0,
   onnxmltools 1.16.0); output lượt đó đẩy Kaggle: `chuyendinh/funding-gate-wfo-pred` (08-06 15:17, `wfo_gate_pred.csv` md5 `68aab54d…`,
   2 760 442 dòng 2021-04-01 → 2026-06-30, = `wfo-gate-pred-1m` 08-09).
3. **Feature từ store hiện tại = feature lúc train: 100 %.** Replay `ExportGateDataset.replayToCsv` từ store Oracle hôm nay (jar
   `d7824f6d`, config ép 127.0.0.1) vs file train: 385 634 dòng (2021-01-01→07-07 liên tục + 8 cửa sổ 10 ngày 2021–2026Q1):
   **33/33 cột + `label_oldbasket` khớp ≤ 1e-6 ở 100 % dòng, max|Δ| = 0**; p15 `fold_20` bit-exact (max|Δ| 0), PASS q 0,99995
   426/426 trùng. ⇒ **Backtest DEV (store hiện tại) đại diện đúng model đã train.**
4. Rủi ro còn lại (nhỏ): store có **ts trùng nhiều bản ghi** (2 947 861 record / 2 867 134 ts; ~15 000 ts/năm có > 1 record,
   2 350 ts mâu thuẫn giá trị) — `getAllMarketDataFromAerospike` (scan → TreeMap) chọn bản nào tuỳ thứ tự scan ⇒ không tất định
   tuyệt đối. Đo được: momentum file train vs dump store 10-14 khớp 99,94–99,97 %/năm (2021–2024), khớp "một trong các bản" 100 %;
   tác động p15 trong cửa sổ train: 99,964 % dòng ≤ 1e-7, Spearman 0,9999993, PASS q 693/693 trùng. 2026-06/07 (ngoài train)
   store ghi lại 08-15 ⇒ khác file train (06: 20 % khớp, 07: 0 %) — chỉ ảnh hưởng HO 2026, không ảnh hưởng DEV/`fold_20`.

## 1. Xác định file train của `fold_20`

| Thuộc tính | Giá trị | Bằng chứng |
|---|---|---|
| Model | `~/claudedata/wfo_models/fold_20/Model_Regressor_Return15M.onnx` md5 `8ec9975726270782692bfe00b39bd37f`, 150 cây, 4 604 node (2 227 nhánh `BRANCH_LT`) | đọc ONNX |
| Lượt train | `WFOGateRunner` (Java) → `ml/gate/train_gate_fold.py`, ~2026-08-06 (mtime gốc `wfo_models` 08-06, docs DEPLOY242 Q1) | output lượt đó = Kaggle `funding-gate-wfo-pred` 08-06 15:17 |
| Cutoff / cửa sổ train | `CUTOFF=20260401` ⇒ `timestamp < 1775001600000` (2026-04-01 00:00 UTC); bắt đầu 2021-01-01 00:00 UTC; **2 759 040 dòng**; purge **0** (`GATE_PURGE_MS` chỉ có trong `WFOGateRunner` từ `463edee8` 08-21; mặc định script = 0) | `train_gate_fold.py`, `git log -S GATE_PURGE_MS` |
| Valid | không có tập valid/early-stopping trong `train_gate_fold.py`; khối OOS WFO của fold = 2026-04-01 → 2026-06-30 (130 582 dòng) | code |
| Feature | 33 V3FULL (thứ tự khoá cứng) + nhãn `label_oldbasket`; không scaler | code |
| File tương đương | Kaggle `gate-dataset-full` v1 md5 `a1c78e2f…` (2021-01-01 00:00 → 2026-06-30 17:00 UTC) | E1–E4 dưới |

- **E1 (OOS khớp):** `fold_20` predict trên file train ở 2026Q2 vs `wfo_gate_pred.csv` 08-06: **99,982 % dòng ≤ 1e-7**, Pearson
  0,99999995, max|Δ| 1,75e-4 (130 582 dòng). Các quý trước do fold khác sinh (Pearson 0,73–0,98) — đúng kỳ vọng.
- **E2 (dấu vân ngưỡng tách):** XGBoost hist lấy ngưỡng = giá trị dữ liệu train. **1 059/1 059 ngưỡng duy nhất (33/33 cột) có
  mặt chính xác (float32) trong file train**; đối chứng (ngưỡng dịch ±1..3 bước 1e-8): 65,8 % (vd momentum24H 13,8 %,
  distMA20 13,9 %, fundingRateRaw 30,9 %) ⇒ xác suất ngẫu nhiên ≈ 0. Trên lưới 15′ so với bản cũ 06-23: funding
  `fundingRateRaw` 100 % vs **25,9 %**, `fundingRateAvg24H` 100 % vs 58,1 %, `fundingRateTrend` 100 % vs 73,3 % ⇒ `fold_20` KHÔNG
  học từ bản 06-23.
- **E3 (niên đại store, LUT):** bảng §2.
- **E4 (tái lập từ store hôm nay):** bảng §3.

## 2. Niên đại ghi các set nguồn (Oracle `aerospike-wfo`, ns `test`, scan chỉ đọc, LUT +07)

| Set | Record | Ngày ghi cuối (số record) | Phần ghi sau 08-06 |
|---|---|---|---|
| `market_data_object` | 2 947 861 (2 867 134 ts) | 2026-06-29 23:35 (6 787, bản không user-key) · **2026-07-07** (2 840 019; 2021-01→2026-05 ghi 22:49–23:10) · 2026-08-15 13:17 (101 055) | chỉ ts 2026-06 (cuối), 2026-07, 2026-08 |
| `kline_1m_opt` | 2 952 455 | 2026-06-30 (151 903) · **2026-07-07** (2 703 650) · 2026-08-05 (35 509: 2026-06/07) · 2026-08-13 (61 393; key 2026-07: 420) | chỉ 2026-07 |
| `funding_data` | 831 symbol | 2026-07-08 (741) · 2026-08-05 (90 symbol mới: cổ phiếu/niêm yết 07/2026) | không |
| `symbol_mapper` | 1 | 2026-08-05 | (lượt 08-06/08-08 đọc mapper từ 242 theo config cũ; id symbol 2021–2026Q1 không đổi — replay khớp 100 %) |
| `symbol_lifecycle` | 698 | 07-07 (72) · 08-13 (626) | không dùng bởi `ExportGateDataset` (replay khớp 100 %) |

`gate15m_v2_full.csv` ghi 06-23 ⇒ trước cả 2 lần sinh lại (06-29/06-30, 07-07) ⇒ giải thích bảng lệch §6.1.

## 3. Khớp theo năm / cột — file train (NEW) vs store hiện tại

### 3a. Replay `ExportGateDataset` từ store hiện tại (tất cả 33 cột + nhãn)

| Năm | Dòng so | % dòng khớp cả 33 cột ≤ 1e-6 | `label_oldbasket` | cột lệch | lệch tương đối median / p99 | p15 `fold_20` exact ≤ 1e-7 | PASS q 0,99995 train / replay / cả hai |
|---|---|---|---|---|---|---|---|
| 2021 (01-01→07-07 liên tục + 03-22→04-01 + 08-15→08-25) | 299 228 | **100 %** | 100 % | không | 0 / 0 | 100 % | 82 / 82 / 82 |
| 2022 (05-05→05-15, LUNA) | 14 401 | **100 %** | 100 % | không | 0 / 0 | 100 % | 78 / 78 / 78 |
| 2023 (03-10→03-20, USDC) | 14 401 | **100 %** | 100 % | không | 0 / 0 | 100 % | 0 / 0 / 0 |
| 2024 (08-01→08-11) | 14 401 | **100 %** | 100 % | không | 0 / 0 | 100 % | 51 / 51 / 51 |
| 2025 (04-05→04-15, 10-08→10-18) | 28 802 | **100 %** | 100 % | không | 0 / 0 | 100 % | 215 / 215 / 215 |
| 2026Q1 (03-01→03-11) | 14 401 | **100 %** | 100 % | không | 0 / 0 | 100 % | 0 / 0 / 0 |
| **Tổng** | **385 634** | **100 %** | 100 % | — | max|Δ| = 0 mọi cột | **100 %** (Pearson/Spearman 1,0) | **426 / 426 / 426** |

Cửa sổ 10 ngày dùng warm-up 48 h của chính `ExportGateDataset`; cửa sổ 2021-03-22 trùng đoạn liên tục ⇒ warm-up hội tụ (khớp 100 %).
Ngưỡng q: proxy gate = quantile 0,99995 của p15 (1′) trong 90 ngày trước, warm-up 7 ngày, tính trên chuỗi p15 của file train đủ dài
và áp cho cả 2 phiên bản (không phải gateValue sau quantile-map của live).

### 3b. Toàn bộ năm — 3 cột phụ thuộc `market_data_object` (momentum1M, momentum15M, momentumAcceleration) vs dump store 10-14

| Năm | Dòng | momentum1M+15M khớp (≤ 5,1e-9, CSV %.8f) | khớp ≥ 1 bản ghi trùng-ts | p15 `fold_20` exact ≤ 1e-7 (thay momentum bằng store) | Spearman | PASS q (file train / store) |
|---|---|---|---|---|---|---|
| 2021 | 525 180 | 99,97 % | 100 % | 99,970 % | 0,9999992 | 140 / 140 |
| 2022 | 525 600 | 99,93 % | 100 % | 99,948 % | 0,9999980 | 125 / 125 |
| 2023 | 525 600 | 99,93 % | 100 % | 99,943 % | 0,9999971 | 41 / 41 |
| 2024 | 527 040 | 99,95 % | 100 % | 99,967 % | 0,9999994 | 112 / 112 |
| 2025 | 525 600 | 100,00 % | 100 % | 99,985 % | 0,9999999 | 254 / 254 |
| 2026Q1 (trong train) | 130 020 | — | 100 % (01–03) | 99,988 % | 0,9999999 | 21 / 21 |
| 2026 cả năm (06–07 ngoài train) | 260 603 | 86,9 % | 01–05: 100 %, 06: 20,4 %, 07: 0 % | 87,3 % | 0,686 | 35 / 39 |
| **Cửa sổ train `fold_20`** | **2 759 040** | — | — | **99,964 %** (max|Δ| 0,0072) | **0,9999993** | **693 / 693** |

"Dòng" = dòng file train theo năm +07 (cột p15); % khớp momentum tính trên dòng có ts trong store (năm UTC, `a1_fingerprint.json`).
Phần lệch 0,03–0,07 %/năm (2021–2024) = ts có bản ghi trùng mâu thuẫn (scan chọn bản khác) — tất cả khớp "một trong các bản".
82 744 dòng file train không có ts trong store (99,7 % trong số đó momentum1M = 0, ngữ nghĩa Java khi md null); trên các cửa sổ
replay, phía store hiện tại cho đúng giá trị đó (khớp 100 %).

### 3c. Đối chiếu bản cũ `gate15m_v2_full.csv` (06-23) — để giải thích §6.1, KHÔNG phải dữ liệu train

Trên lưới 15′ cùng ts, % dòng khớp cả 33 cột với file train: 2021–2025 **0 %**, 2026 46,6 %. Cột lệch không chỉ momentum: funding
(2021 khớp 4,9 %/5,2 %/9,3 %), breadth/btcDominance (2022 ≈ 55–62 %), momentum (2021–2023 0,3–2 %, 2024 31–35 %, 2025 96 %).
OLD vs store hiện tại: momentum 2021–2023 0,1 %, 2024 26 %, 2025 99,3 % (= số §6.1). Nguyên nhân: kline/funding/market store
được sinh lại 06-29…07-08, sau ngày ghi bản này.

## 4. Kết luận độ tin backtest

- Model `fold_20` (live 242) học từ đúng dữ liệu mà store Oracle hiện tại tái tạo được (feature + nhãn bit-exact trên mẫu 385 634 dòng
  phủ 2021–2026Q1; momentum cả 2,76 triệu dòng train 99,96 % bit-exact, phần còn lại do bản ghi trùng). Backtest DEV đọc cùng store
  (`market.bin` DEV `4ab691c9` = store; pred.bin = model cùng recipe trên cùng store) ⇒ **còn đại diện** cho model đã train.
- Không cần tính lại kết quả DEV vì lý do provenance. Danh sách "phải tính lại" ở §6.1 (do `md_inline.py` cũ / died 242) giữ nguyên —
  khác chủ đề.
- Đề xuất (không làm, cần quyết MASTER — là thao tác GHI): khử trùng `market_data_object` (6 787 record không user-key ghi 06-29 +
  ts có 2 bản) để `getAllMarketDataFromAerospike` tất định; trước đó, mọi so sánh bit-exact với store nên chấp nhận "khớp ≥ 1 bản".

## 5. Lệnh / thao tác

- Kaggle (KaggleApi, chỉ đọc): liệt kê 169 dataset + 1 017 kernel của `chuyendinh` (`kg_ds.txt`, `kg_kn.txt`); không kernel nào train
  gate quanh 08-06/08-18. Tải: `gate-dataset-full`, `funding-gate-wfo-pred`, `wfo-gate-pred-1m`, `wfo-ds-dev-002` (market.bin,
  manifest) — md5 `kg_md5.txt`.
- Replay Java chạy trên Oracle với `config.properties` đã thay MỌI host bằng 127.0.0.1 (kiểm không còn `103.157`), `LIVE_WRITE_242_ENABLED=false`,
  `SYMBOL_MAPPER_DUP_POLICY=WARN` (mapper Oracle có 8 id trùng 843–850 của symbol niêm yết 07/2026, không có trong dữ liệu so), cùng
  vòng giám sát `ss` kill nếu có kết nối tới 103.157.218.x: **0 vi phạm** (`replay_guard.txt`).
- Lần chạy replay đầu (policy FAIL) lỗi mapper mỗi ngày ⇒ dừng, chạy lại với WARN; lượt toàn dải 2021→2026Q1 dừng chủ động sau
  2021-07-07 (≈ 4 h ước tính, máy dùng chung) và thay bằng 8 cửa sổ.
- Không lệnh nào bị chặn quyền.
