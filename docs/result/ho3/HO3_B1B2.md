# HO3 — B1 kho dữ liệu Q3 2026 + B2 validate chéo nguồn (agent HO3, 2026-10-10)

Pre-reg: `docs/prereg/PREREG_HOLDOUT2026H1.md` ADDENDUM-3 (44d45ca1, commit TRƯỚC mọi bước). Không số hiệu năng Q3 nào được tính/nhìn: chỉ đếm, tỉ lệ khớp, khoảng ts. JSON: `docs/result/ho3/*.json`. Script: `research/analysis/ho3_*.py`. Thư mục Oracle: `~/claude_master/1003/ho3/`.

**KẾT LUẬN: DỪNG TẠI B2 (theo luật ADDENDUM-3 §5 / prompt B2).** 4 thành phần FAIL cổng chéo trên đoạn chồng H1 (market.bin, funding, OI, gate momentum) và kiểm Vision↔242 Q3 FAIL. Phát hiện quan trọng hơn: **klines Aerospike (= ticker HO26) đã lệch Vision ngay trong H1** (06-2026 chỉ 86,7% khớp) ⇒ ngưỡng "Vision vs 242 ≥ 99,99%" không đạt được kể cả với dữ liệu HO26. Không dựng B3, không parity B4, không đẩy kernel B5. Không Kaggle kernel/dataset nào được tạo.

## B1 — Kho dữ liệu và nguồn đề xuất cho 2026-07-01→09-30

| Thành phần | Nguồn HO26 (H1) | Phủ Q3 có sẵn | Nguồn đề xuất Q3 | Trạng thái |
|---|---|---|---|---|
| Ticker 1′ (sim, `ticker_*.bin` Java-serialized) | Aerospike local `test.kline_1m_opt` → `ticker_2026*.bin.gz` | Oracle file tới 08-12; local kline tới 08-13; **242 `ticker.kline_1m_opt` tới 10-09, 0 phút thiếu 07-01→10-01** | 242 (CHỈ ĐỌC) + writer Python format jbin (chưa viết; cổng md5 byte vs file H1) | 242 == ticker HO26 100% (B2-K1) |
| funding_data (3 feature gate funding; feat Tool1) | store local `test.funding_data` (DEV/HO26) | **local chết 2026-07-07 23:00**; 242 sống tới 10-10; Vision monthly | Vision (giá trị == local 100% trên mốc chung) — thiếu 37 symbol | FAIL chặt (99,88%) |
| OI per-coin 5 cột (`oi_percoin_full.bin` e3887f63; net015 + S1) | Vision metrics (build Kaggle cũ, dịch +5′ theo quy ước) | file ghim tới 2026-06-30 23:55 UTC; Vision daily metrics; 242 sets `open_interest` (chưa đo) | Vision daily `sum_open_interest_value` + dịch +5′ (NEW) | FAIL (ls/taker 83%) |
| `market.bin` (sim) + momentum1M/15M/Accel (gate) | set local `market_data_object` | **chết sau 2026-08-13** | 07-01→08-13 store; 08-14→09-30 chỉ có INLINE (`md_inline` / `MarketDataInlineGenerator`) | FAIL (inline ≤1e-6 44%) |
| Store gate 33 feature (p15) | `gate_dataset_full.csv.gz` (08-08, tới 06-30) | `devexport_20260701_20260928_FULL` (port Python, funding 242, md store→0 sau 08-13; tới 09-28 16:16) — KHÔNG phải công thức DEV | devexport port + nguồn đã chốt | FAIL (trích audit: 30/33) |
| Tool1 15′ (net015, 40 feat) | `ds_feat15m/*.t1c.gz` (Java `ExportFeaturesForPythonTool`, tới 07-01) | không có | Java exporter trên Kaggle (`TICKER_SOURCE=file`, cần market data + mapper file) — phụ thuộc market | chưa đo |
| Nhãn 15′ pool S1 (`nBars_72h`) | `ds_label15m/*.pb` (Java `ExportFundingLabel`, tới 07-01) | không có | Java Kaggle (cần `symbol_lifecycle`); chỉ đọc tồn-tại `nBars_72h` | chưa đo |
| p15 pred.bin 8 seed | model gate HO1 B2 cut 2026-01-01 | — | predict Q3 trên store gate Q3 | phụ thuộc store gate |
| net015 bins | ONNX `7921ceaf` (phương án A) | — | predict Tool1+OI Q3 → `x1_build_map` | phụ thuộc Tool1/OI/S1 |
| S1 (CLOSES_1H, feat_v2, ledger, predict, build_map) | Vision 1h + OI ghim + nhãn pool | Vision 1h có | `closes1h_build.py` Vision + OI Q3 + nhãn Q3 | phụ thuộc OI/nhãn |
| funding.bin (bins ffill) | Python append HO2 | — | dựng trên Kaggle (Oracle còn 3,6G, file 5,5G) | — |

## B2 — Validate chéo nguồn (đoạn chồng H1 2026-01-01→06-30 +07, trừ khi ghi khác)

| # | Thành phần | So sánh | Đoạn | Kết quả | Ngưỡng | Kết luận |
|---|---|---|---|---|---|---|
| K1 | klines | Aerospike 242 `ticker.kline_1m_opt` vs ticker HO26 | 181 ngày H1, 260 602 phút | OHLCV khớp 151 127 840 / 151 128 423 = **99,99961%**; phút thiếu 0/0; chỉ 242 có 13 ô; 583 ô giá trị đổi | ≥ 99,99% | **PASS** |
| K2a | klines | Vision monthly vs ticker HO26 | 2026-03 | OHLCV **99,99714%** (25,69 M ô), OHLC 99,99758%; Vision thừa 233 ô | ≥ 99,99% | PASS |
| K2b | klines | Vision vs ticker HO26 | 2026-04 | OHLCV 97,68% cả tháng: **100% mỗi ngày tới 04-24** (04-19..04-24 ≥ 99,91%), rồi **04-25 96,1% → 04-28 83,7%**; Vision thừa 1 215 174 ô, ticker thừa 34 398 | ≥ 99,99% | FAIL (từ 04-25) |
| K2c | klines | Vision vs ticker HO26 | 2026-05 | OHLCV **84,28%**, OHLC 89,69% (25,84 M ô); theo ngày 82–87% | ≥ 99,99% | **FAIL** |
| K2d | klines | Vision vs ticker HO26 | 2026-06 | OHLCV **86,71%**, OHLC 90,85%; Vision thừa 1 008 518 ô; theo ngày 79–93% | ≥ 99,99% | **FAIL** |
| K3 | klines | Vision vs Aerospike 242 | 07-01→07-21 + 08-17→08-31 | OHLCV **91,21% / 91,19%**, OHLC 94,28% / 94,39%; theo ngày 89–93% | ≥ 99,99% | **FAIL** |
| G | klines lỗ | key phút thiếu trên 242 | 07-01→10-01 +07 (132 480 phút) | **0 phút thiếu**, 0 lỗi đọc (`gaps_242_q3.json`) | liệt kê | — |
| F1 | funding | Vision fundingRate vs store local (nguồn DEV/HO26) | H1 (tháng UTC 2025-12..2026-06) | mốc khớp 547 238 / 547 888 = **99,881%**, giá trị trùng 100% trên mốc chung; 650 mốc thiếu dồn ở **37 symbol** (cổ phiếu/ETF perp AAOI, ADBE, ASML…, BDXN, SXP, 币安人生); Vision thừa 34 | 100% mốc | **FAIL** (chặt) |
| F2 | funding | 242 `ticker.funding_data` vs local | H1 | 98,977% mốc; **934 mốc lệch giá trị**; 242 thừa 8 550, thiếu 4 672 | 100% | **FAIL** |
| O | OI per-coin | Vision daily metrics (OI = `sum_open_interest_value`, dịch +5′ NEW) dựng lại `writeCoin` vs file ghim | mẫu 60 symbol × 6 ngày (15/01..15/06), 103 512 dòng | oi_delta24h **99,962%**; ls_global **83,14%**, ls_toptrader 83,14%, taker_buy 83,12% — lệch NGUYÊN NGÀY (vd 2026-06-15: mọi symbol, không dịch ±60′ nào khớp ⇒ Vision đã đổi dữ liệu sau khi build file ghim hoặc file ghim ngày đó từ nguồn khác); oi_z (expanding từ 2021) không đo | ≥ 99,9% | **FAIL** |
| M1 | market.bin | INLINE (`md_inline` port) từ ticker vs market.bin HO26 | H1, 252 470 phút | ≤1e-6: **44,22%**; ≤1e-3: 99,955%; max\|Δ\| 0,13; inline thừa 8 132 phút (store thiếu ~3%), thiếu 22 | ≤ 1e-6 | **FAIL** |
| M2 | market.bin | đọc lại store local `market_data_object` theo key vs HO26 | H1 | ≤1e-6: **99,373%** (T5 98,67%, T6 98,02%); thiếu 1 344, thừa 6 884 (store bị ghi thêm sau export) | ≤ 1e-6 | **FAIL** |
| GF | 33 feature gate | port Python `devexport_202609` vs store DEV (trích `RESULT_DEVEXPORT_202609_AUDIT` §3, không chạy lại) | 2026-03-10, 2026-05-01 | 30/33 khớp ≤1e-8 (store local); momentum1M/15M/Accel lệch ~30/1 440 dòng (nguồn md trôi); dùng funding 242: 27/33 | ≤ 1e-6 | **FAIL** |
| T/L/p15/bins | Tool1, nhãn, p15, bins | — | — | KHÔNG ĐO (phụ thuộc market/funding/OI đã FAIL; luật: DỪNG, không dựng tiếp) | — | — |

Symbol loại: chưa xác định (B3 chưa chạy). Ghi nhận: Q3 có 667 symbol trong kline 242 (07-2026) so với 584 (03-2026); 37 symbol thiếu funding Vision (danh sách `f_h1.json`).

## Đọc kết quả (rủi ro trước)

1. **Nguồn klines của HO26 KHÔNG tương đương Vision từ ~T4–T5/2026** (tới 2026-04-24 ~100%; **gãy từ 2026-04-25 +07**; T5 84%, T6 87%), nhưng Aerospike 242 == ticker HO26 (99,9996%). ⇒ Với Q3, nguồn **nhất quán với HO26 là Aerospike 242**, không phải Vision. Cổng "Vision vs 242 ≥ 99,99%" của prompt không đạt được ngay cả trên dữ liệu HO26 đã dùng ⇒ cần MASTER định nghĩa lại (ví dụ: thước = 242 vs ticker HO26 trên H1, đã PASS; và mô tả bản chất lệch Vision↔Aerospike trước khi chấp nhận). Bản chất lệch (nến live websocket vs nến sàn chuẩn hoá? làm tròn? cập nhật trễ) CHƯA chẩn đoán.
2. **market.bin Q3 sau 08-13 không có nguồn đạt ≤1e-6**: inline chỉ khớp 44% ≤1e-6 (99,96% ≤1e-3); store chết 08-13 và chính store đã trôi so file HO26 (99,37%). Tiền lệ DEV (`RESULT_BD_CHAIN`): market.bin sinh lại từ ticker ⇒ parity printDone FAIL (equity 131878 vs 131908). Đây là chặn cứng nhất.
3. **funding**: Vision trùng giá trị store DEV 100% trên mốc chung; thiếu là do 37 symbol không có trên Vision (cổ phiếu/ETF perp niêm yết 2026 + vài coin). 242 KHÁC store DEV (934 mốc lệch giá trị). Nếu MASTER chấp nhận "100% mốc trên symbol có Vision" thì F1 PASS.
4. **OI**: công thức `writeCoin` + quy ước +5′ tái hiện đúng (oi_delta 99,96%, ls/taker 100% ở đa số ngày) nhưng có NGÀY lệch toàn bộ (2026-06-15) ⇒ Vision đã sửa dữ liệu sau khi build file ghim (08-09) hoặc file ghim ngày đó lấy nguồn khác; oi_z expanding cần toàn lịch sử — rebuild Q3 sẽ không nối liền byte với file ghim.
5. **Store gate**: momentum×3 phụ thuộc market (điểm 2); funding×3 phụ thuộc store funding (điểm 3).

## Lựa chọn cho MASTER (không tự chọn — cần ADDENDUM-4 commit trước khi dựng)

- (A) Giữ cửa sổ 09-30, đổi thước B2: klines = 242 (thước H1 K1 PASS); funding = Vision trên symbol có Vision (loại 37 symbol + liệt kê); OI = Vision rebuild + cổng mức feature/bins thay vì byte; market 08-14→09-30 = inline với cổng parity KINH TẾ (kiểu `market_align` BD_CHAIN: khớp n/equity trên H1 khi thay market.bin H1 bằng inline) — phải khai trước là nguồn khác HO26.
- (B) Rút cửa sổ về 07-01→08-13 (market store còn, kline local + 242) — vẫn phải giải funding/OI/Tool1/nhãn; Δn H-B quy đổi lại.
- (C) Dừng mở rộng holdout; dùng paper 242 (đã chạy từ 08-17) làm forward test thay thế.

## Provenance
Script (commit này): `ho3_b2_kline_as.py`, `ho3_b2_kline_vision.py`, `ho3_b2_market.py`, `ho3_b2_fund.py`, `ho3_b2_oi.py`, `ho3_gaps.py`. Lỗi đã sửa trước khi chốt số: (i) funding v1 thiếu tháng UTC 2025-12 (mốc 2026-01-01 03:00 +07) — file `f_h1_v1_boundarybug.json` không dùng; (ii) OI v1 dùng `sum_open_interest` + thiếu ngày d−2 — `o_h1_v1_portbug.json` không dùng. Đọc Aerospike/Vision CHỈ ĐỌC; 0 ghi 242/shadow; 0 Java; 0 Kaggle.
