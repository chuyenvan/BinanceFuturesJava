# PREREG_BACKCAST_RESERVOIR — kho holdout backcast 2020 (agent BCAST, 2026-10-12)

**TRẠNG THÁI: CÓ HIỆU LỰC từ commit này** (MASTER chọn **P1** sau B0 `a8ce5302`). Commit TRƯỚC mọi bước dựng (B1), trước mọi kernel Kaggle của BCAST. Tại thời điểm viết: chưa có dữ liệu kho nào được dựng; chưa sim; không ai nhìn kết quả chiến lược nào trên 2020 (§7). B0: `docs/result/bcast/BCAST_B0.md`.

## 1. Phạm vi (quyết định MASTER, nguyên ý)
- Dựng dữ liệu **2020-01-01 → 2021-01-03 UTC** (3 ngày cuối chỉ cho 72 h nhìn trước nhãn pool S1).
- **Cửa sổ chấm CHÍNH: 2020-05-01 00:00 → 2020-12-31 23:59 +07.** Báo kèm (không phải cửa sổ chính): biến thể kết thúc 2020-11-30 23:59 +07.
- **2021H1 KHÔNG niêm phong, KHÔNG BAO GIỜ được chấm** (in-sample: gate 8 seed train từ 2021-01-01 UTC, net015 Tool1 từ 2021-01, S1 ledger từ 2021-04-01).
- 2020-01-01 → 2020-04-30 = warm-up (feat_v2 cửa sổ ≤ 336 h ⇒ S1/bins đủ feature từ ~2020-01-15; bộ đệm GateRollingRatio 90 ngày đầy ~2020-05-01). COVID 2020-03-12 nằm trong warm-up, không chấm.

## 2. Nguồn + công cụ (như HO4-P1; khác biệt khai ở mục 3)
1. Vision `futures/um`: klines 1m monthly 2020-01..2021-01, fundingRate monthly 2020-01..2021-01. Exporter Kaggle = `ho4p1_exp_kernel.py` (jar exporter `99c5f040`, dataset `ho4p1-jar-exp`, Aerospike CE trong kernel, guard host 127.0.0.1) sinh lại bằng `research/analysis/bcast_mkexp.py` chỉ đổi: thư mục làm việc, chính sách slot Kaggle (§6). Tasks: `ExportMarketData2File` (TIME_RUN 20200101), `ExportGateDataset` 20200101→20210102, `ExportFeaturesForPythonTool` FF_UNFILTERED=1 20200101→20210102, `ExportFundingLabel` 20200101→20210104 (LABEL_STEP_MIN 15); ingest ticker 20200101→20210103; CLOSES_1H từ 1m; lifecycle từ kline cửa sổ.
2. Chuỗi hạ nguồn Kaggle = hàm của `ho4p1_chain.py` + mode `bc20` (`research/analysis/bcast_chain.py`): p15 8 seed predict-only, market.bin = dump exporter [S_LO, END), net015 ONNX predict-only 4 fold quý +07 (20200101/20200401/20200701/20201001), feat_v2 KEEP9 từ CLOSES_1H Vision 1m, pool S1 (p15 s42 ≥ 0,008, nBars_72h ≥ 288), S1 predict-only, `x1_build_map`, loại symbol không funding. S_LO = 2020-01-01 00:00 +07, END = 2021-01-01 00:00 +07 (sim dừng 2021-01-01 06:59 +07, quy ước ADDENDUM-1 §2).
3. Model đóng băng, không retrain: gate 8 seed (42/7/13/21/99/123/777/2024) `gate_s*_cut20260101p15.json`, net015 ONNX `7921ceaf`, S1 `af706dc6` (sha kiểm trong kernel).

## 3. Khác HO4 (khai trước)
(a) Không có đoạn DEV ghép trước: pred.bin/market.bin/funding.bin chỉ gồm kho. (b) OI = file ghim `oi_percoin_full.bin` (`e3887f63`) cắt theo cửa sổ, KHÔNG dựng lại OI (Vision metrics trước 2021-12 chỉ có BTCUSDT từ 2020-09) ⇒ 5 cột OI net015 + `ls_global`/`rk_oi_delta24h` S1 = NaN trừ BTC (nếu ghim không có hàng 2020 thì NaN toàn bộ — chỉ báo). (c) Gate/Tool1 không có lead-in trước 2020-01-01 (dữ liệu không tồn tại) ⇒ những ngày đầu là warm-up. (d) Sim kỹ thuật: TIME_RUN=20200101 qua bản copy config.properties trong kernel; ticker CHỈ từ exporter kho (không gắn dataset ticker DEV).

## 4. Universe (point-in-time, luật HO4 ADDENDUM-6 §6.2 + HO4-P0b quyết định #1)
- Bộ lọc LIVE `TickerIngestor2AerospikeNew` (USDT, `^[A-Z0-9]+$`, không BTCDOM/USDC) ∩ mapper 863; đuôi settle (volume 0 ≥ 1 440 phút kéo tới kline cuối) cắt từ phút đầu đuôi.
- **Loại LENDUSDT, BTCSTUSDT** (không có trong mapper 863) — liệt kê, KHÔNG cấp id mới.
- Thiếu funding Vision (QTUMUSDT 2020-02, LENDUSDT 2020-11, ICPUSDT 2021-05/06): luật HO4 = symbol không có funding Vision trong cửa sổ ⇒ ở lại dữ liệu, loại khỏi giao dịch (xoá khỏi bins); thiếu tháng lẻ ⇒ giữ, ghi chú.

## 5. Kiểm (cổng B1/B2) — chốt trước, chỉ mức dữ liệu, KHÔNG PnL
- **B1 toàn vẹn:** mọi task exporter rc=0; ticker 369 ngày UTC (20200101..20210103) md5 raw == exporter; market.bin/pred.bin×8/bins×4/net015×4: NaN 0 (p15, p0, market), ts tăng (pred/market) / không giảm (bins); store gate 33 cột: NaN theo tháng báo cáo, **phải = 0 trong cửa sổ chấm**; danh sách symbol loại + lý do; MANIFEST md5 mọi file.
- **B2 P3-DET (cổng):** exporter chạy 2 lần độc lập (`bcast-x20-a`, `-b`) ⇒ MANIFEST trùng md5 100% file; chuỗi hạ nguồn chạy riêng trên a và b (`bcast-ch20-a`, `-b`) ⇒ MANIFEST trùng 100% (pred×8, market, net015×4, bins×4, S1, feat_v2). FAIL ⇒ DỪNG, báo MASTER, không vá.
- **B2 phủ:** số symbol/tháng (ticker, gate, bins) báo cáo.
- **B2 sim kỹ thuật DUY NHẤT:** `bcast-tech` = B0 (profile `r4_kg0_k16_f015_g155` + B0OV), seed 42, phí gốc, jar sim `b7c89f09`, bundle `sim-ho26a-bundle`, TIME_RUN=20200101, SIM_END_DATE=20210101; funding.bin dựng trong kernel (khối FUND_REBUILD_HO4, lo = S_LO, tự kiểm DEV giữ nguyên). Chỉ ghi: exit (java_rc, ok), mapper ≥ 800, TICKER 369/369, FUND_HO4_OK, pred md5, n dòng printDone, md5 printDone, date_first/date_last. Output cất `~/kaggle_sim/sealed/bcast-tech` chmod 700; KHÔNG mở printDone/equity, không đọc trường equity/b của result.json, không grep dòng `Update … b:` của log.
- Kaggle: BCAST tối đa 1 kernel cùng lúc; đẩy chỉ khi toàn tài khoản < 2 kernel đang chạy và không có kernel `bcast-*` đang chạy.

## 6. Luật mở kho (MASTER)
1. Mỗi ý tưởng mở kho **đúng 1 lần**, có pre-reg riêng commit TRƯỚC (giả thuyết, cấu hình, thước, ngưỡng, k biến thể với inflate √(2 ln k), 8 seed ghép cặp, scorer commit trước khi đọc). Chạy lại chỉ khi lỗi hạ tầng, cfg y hệt.
2. **Thước chính: E0 tuyệt đối của ý tưởng** (mean ΣPnL cửa sổ chấm > 0 và ≥ 6/8 seed > 0, trên bản stress) **+ Δ ghép cặp seed so với nền cùng kho** (mean ΔΣPnL, ΔmaxDD MTM; ngưỡng do pre-reg ý tưởng chốt).
3. **Nền chuẩn cùng kho, đúng 2 bản chi phí:** b0 và k24 (định nghĩa như HO4: B0 = K16 G2+FLAT3 B0OV; K24 = B0 + SELECTOR_RANK_TOPK=24 + GATE_QUOTA_SKIP_WHEN_FULL=true) × {phí gốc; stress `SIM_CRASH_ENTRY_PENALTY=0.005`} × 8 seed. Bối cảnh chi phí: EXEC `2c812222` cho thấy penalty 1,675 % phạt thừa ~20×; chi phí thực chân sập ≈ +7 bps, cận trên P0max 50 bps ⇒ stress kho = 0,005.
4. Nền chuẩn chỉ chạy CÙNG lúc với ý tưởng đầu tiên mở kho (cũng tính là mở kho), dùng lại cho ý tưởng sau; không chạy nền để "xem trước".
5. Sổ mở kho trong `docs/plan/BACKCAST_RESERVOIR.md` §log. Kho coi như tiêu cho cùng họ ý tưởng sau ~3–5 lần mở (MASTER chốt).

## 7. Rủi ro (khai trước — kho YẾU, chỉ bằng chứng PHỤ, KHÔNG thay holdout)
- Universe 25 (2020-05) → 80 (2020-12) symbol vs DEV 117–600 ⇒ breadth/basket/rank lệch phân phối train; **H-A k24-vs-b0 khó phân biệt** (top-24 ≈ toàn universe đầu kho).
- OI NaN toàn kho (trừ BTC nếu ghim có). COVID 2020-03-12 trong warm-up, không chấm.
- Chế độ 2020 (bull, vol năm ~76 %) khác DEV. Vision có thể thiếu symbol niêm yết 2019–20 (không kiểm được — cấm REST).
- Model đóng băng chưa từng thấy 2020 nhưng tầng thiết kế (DATA_EXTENT_SURVEY) đã nhìn thống kê BTC năm 2020.

## 8. Ai đã nhìn gì trên 2020 (tính tới commit này)
DATA_EXTENT_SURVEY (2026-06): thống kê BTC năm 2020 (return, vol, ngày tệ nhất), độ phủ Vision. FS: giá 1h từ 2020-12 làm lookback, chấm chỉ 2022-01..2024-06. NBETS/GS/G015CUT/S1CUT: MDE, khả năng lùi DEV. AUDIT_OI_FEAT_PARITY/D1_DATA_AUDIT: độ phủ OI raw. BCAST: liệt kê file Vision, meta train model. Không job nào chạy sim/PnL chiến lược trên 2020 (grep docs + research). Train 3 họ model: thấy 2021H1 (không thấy 2020).
