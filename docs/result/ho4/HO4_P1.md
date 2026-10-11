# HO4-P1 — sửa race, P3-DET tất định, dựng holdout 2026 từ Vision, đẩy 32 kernel (agent HO4-P1, 2026-10-11)

Pre-reg: `docs/prereg/PREREG_HOLDOUT2026H1.md` ADDENDUM-6 **`af6d6c94`** (+ §6.2a `923d7643`, bổ sung `95da70a9`; đều commit TRƯỚC phép đo/chạy tương ứng; khai: chưa nhìn số sim cửa sổ 2026 nào từ dữ liệu Vision). KHÔNG chấm, KHÔNG mở printDone/equity 2026. JSON `docs/result/ho4/HO4_P1.json` (+ `ho4p1_*.json`). Script `research/analysis/ho4p1_*.py`. Oracle `~/claude_master/1011/ho4p1/` (cache ≤ 500 MB; dữ liệu nặng chỉ trên Kaggle).

## Kết luận (rủi ro trước)
- **P3-DET PASS** (exporter 229/229, OI raw+gz, chuỗi hạ nguồn 8/8 md5 trùng giữa 2 lần chạy độc lập). **S5 chạy lại quý chứa 2026-03 PASS** (q1 vs q1r 137/137; chain 17/17). Dữ liệu 2026 dựng đủ (393 120 phút = 273 ngày × 1 440, NaN 0, ts đơn điệu; đoạn DEV pred 8 seed trùng md5 HO1). C1/C2 + 32 kernel do orchestrator nền chạy (trạng thái ở cuối).
- Rủi ro chính: (1) **mapper có 8 id dùng chung 2 symbol** (843–850) ⇒ 16 symbol niêm yết 07/2026 bị loại khỏi giao dịch (§6.2a); lỗi này nằm trong chính mapper (cả live); (2) P3-DEV (chỉ báo): dữ liệu Vision + universe live lệch DEV mạnh ở mức thành phần (gate 61%, Tool1 strict 56–57% / 1 bước lượng tử 71–72%, net015 13,9% ô ≤1e-3, bins 1,4%) — lệch có chủ đích (universe + set market race của DEV), không phải bất định; (3) 130 symbol bị cắt đuôi settle (R27) — liệt kê `ho4p1_excl26.json`, cần MASTER rà symbol thanh khoản thấp; (4) chuỗi hạ nguồn chạy trên Kaggle (Python 3.13; pin xgboost 3.2.0/onnxruntime 1.23.2/pandas 2.3.3/numpy 2.2.6/pyarrow 25.0.1 như Oracle).

## S1 — sửa race `SimpleDateFormat`
| Mục | Giá trị |
|---|---|
| Fix | `DataManagerAerospikeFloatSim.marketDataKey()` = `ThreadLocal<SimpleDateFormat>` pin GMT+7; `saveMarketDataBatch` + `getMarketDataAtTime` dùng chung. Commit `76c5bc40` |
| Merge `--no-ff` vào module | **`0594986e`** (pushed) |
| Caller | ghi: `ExportMarketData2File:158`, `MarketObjectGapRepairTool:67`; đọc: chỉ tool validate — 0 caller live; GMT+7 ≡ Asia/Ho_Chi_Minh mọi phút 2020–2027 (JUnit) ⇒ host +07 y hệt |
| JUnit `MarketDataKeyRaceTest` (5) | parallelStream 30 ngày × 10 vòng + 16 luồng: 43 200 key, không trùng, == tuần tự; mã cũ tái hiện race 232 744/432 000 key sai |
| `mvn -o test` | trước **259** PASS → sau **264** PASS |
| Jar exporter | sha256 **`99c5f040c9295a610fe815e7c6759ccfccbd1cca370dcfc3bcb935b33ec3a2fb`**, dataset `ho4p1-jar-exp`; jar sim giữ `b7c89f09` |

## S3 — P3 (ADDENDUM-6 §6.3)
| Cổng | Lần a vs b | Kết quả |
|---|---|---|
| **P3-DET exporter** (lát DEV 2025-07-01→12-31, lead-in 06-01) | `ho4p1-det-a` vs `-b` (~2 h 20′ mỗi kernel) | **229/229 md5 trùng** (ticker 214 ngày, market dump, gate CSV, Tool1 3 file, nhãn 4 file, CLOSES_1H, funding Vision, lifecycle, universe) |
| **P3-DET OI** ([2025-06-01, 2026-10-04) UTC) | `ho4p1-oi-a` vs `-b` | raw `2f24cc5d…` = `2f24cc5d…`, gz `715aa75b…` = `715aa75b…`, 77 601 160 dòng |
| **P3-DET chuỗi hạ nguồn** (Kaggle, `ho4p1_chain.py` det) | `ho4p1-chdet-a` vs `-b` | **8/8 md5 trùng** (feat_v2, pred s42, S1, net015 ×2, bins ×2, market) |
| P3-KF | ghi lại P0 `8c3e782b` | K-a 99,9999993%, K-b 0,0034%, F 100%; det-a tính lại F 506 263/506 263 |

**P3-DEV (chỉ báo; `ho4p1-devcmp`, từ det-a/chdet-a vs DEV):** market: 257 447 phút DEV đều có trong bản mới (chỉ-DEV 0), bản mới +7 513 phút (= lỗ race DEV), ô 57,0% (phút chung 58,7%); gate 33 cột 61,2% ô (0 dòng trùng đủ 33); Tool1 Q3/Q4 strict 57,1%/55,6%, dung sai 1 bước lượng tử 71,1%/71,9% (cột tệ nhất 14–15, 32–34 ≈ 0%); nhãn 96,6%/96,4%; feat_v2 61,5% (rk_* ≈ 0–6%, cột không-rank ≥ 96%); p15 M42 35,7% dòng |Δ|≤1e-6 (max 0,233); net015 Q4 13,9% ô ≤1e-3 (spearman 0,979); bins Q4 1,4%; pool Q4 Jaccard 0,841. 2 sim DEV (`sim-ho4p1-dev-{k24,b0}-s-s42`, pred xấp xỉ (a), bins dựng lại cả 2 fold với f15 + S1 cut20251001) xếp pha 2 của orchestrator (sau 32 kernel).

## S4 — dữ liệu 2026 (Vision, công cụ gốc; chỉ đếm/khoảng/md5/NaN)
| Thành phần | Nguồn | Kiểm |
|---|---|---|
| Exporter quý | `ho4p1-x26-q1` (88′), `-q2` (104′), `-q3` (99′) | mọi task rc=0; MANIFEST 137 file/kernel |
| ticker 2026 | `ho4p1-tk26` (273 ngày UTC 01-01..09-30) | md5 raw 273/273 == exporter |
| market.bin | DEV bundle (2 554 408 bản ghi, byte) + Vision 393 120 phút | md5 `0fcc44d8…`, NaN 0, ts tăng |
| store gate | 393 120 dòng (q1 129 600, q2 131 040, q3 132 480) | NaN 0 |
| pred.bin 8 seed | đoạn DEV 2 499 840 bản ghi == md5 HO1 từng seed; +393 120 dòng 2026, NaN 0 | md5 s42 `b692f134…` (đủ 8 trong json) |
| net015 3 fold | 4 656 471 / 4 952 341 / 5 382 633 rec, NaN 0 | fold Q3 bỏ 80 932 dòng id mơ hồ |
| bins 3 file | `042f404f…`, `6299c9e1…`, `91330b01…` | NaN p0 0, ts không giảm |
| feat_v2 / S1 | 3 907 571 dòng / pool 11 477 587 (20 591 tick) | feat_cov 0,998 |

**Symbol loại** (`ho4p1_excl26.json`): ngoài mapper 68 (cổ phiếu/ETF token…; volume ≤ 0,69% tháng 9, 0% T1–T7), BTCDOM/USDC 2, tên không ASCII 5; thiếu funding Vision **0**; id mapper mơ hồ 8 id/16 symbol (0 lệnh trong 48 run ho26); đuôi settle 130 symbol (q1 111, q2 122, q3 128). Tỉ trọng volume universe ≥ 98,7% mọi tháng.

## S5 — parity
- Chạy lại quý chứa 2026-03: **q1 vs q1r 137/137 md5**; **chain-y26 vs chain-y26r 17/17 md5** ⇒ PASS.
- **C1** B0 K16 s42 phí gốc (`SIM_END_DATE=20251231`, artefact mới): n 2 517 = `de-p1`; mọi cột trùng trừ 5 ô in float32 trùng bit (4 volume + 1 quantity, như HO2) ⇒ **PASS**. **C2** K24+skipFull: md5 **`ad26fd55f0bb5db32038ec8b357cf8e7`** == `gqsf-a1` (n 3 541) ⇒ **PASS**. Cả 2: `TICKER_HO4P1 ok=273 bad=0 miss=0 extra=0 other=0`; `FUND_HO4_SELFCHECK keys_equal=True 257 433/257 433 diff=0`; funding.bin prefix 2 301 064 bản ghi (byte bundle) + 393 120 bản ghi 2026 dựng lại.

## S6 — 32 kernel (orchestrator nền, KHÔNG chấm)
- `ho4p1_queue.py` PID trong `~/claude_master/1011/ho4p1/q/queue.pid`; log `q/queue_py.log`; trạng thái `q/queue_status.tsv` (slug/status/md5/n/parity/giờ); state `q/state.json` (resume). ≤ 2 kernel song song toàn tài khoản; retry 1 lần chỉ lỗi hạ tầng (cfg y hệt); parity tự động mỗi kernel: jar `b7c89f09`, override (y hệt `ho26-*`), pred md5 theo seed (`arts.json`), ticker 2026 273/273, FUND selfcheck, mapper ≥ 800, penalty, UNSEAL.
- Pha 1 bắt đầu 20:02 (`ho4-b0-b-s42` …), thứ tự xen kẽ theo seed (4 kernel/seed). Out `~/kaggle_sim/out/ho4-<cfg>-<b|s>-s<seed>`. Pha 2 sau đó: 2 sim DEV P3-DEV (`ho4p1_simdev.py compare` để so).
- Chấm = 2 scorer độc lập vòng sau (commit trước khi đọc output); luật E0/H-A cho 9 tháng / H1 / Q3 + độ nhạy H1 HO4 vs HO26 (ADDENDUM-6 §6.7).
