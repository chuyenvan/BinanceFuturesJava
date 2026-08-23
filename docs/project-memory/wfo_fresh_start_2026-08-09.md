# WFO — FRESH START BRIEF (2026-08-09) — ĐỌC FILE NÀY TRƯỚC

> Uni chốt (09/08): **KHÔNG tái dùng dữ liệu cũ nữa — xuất MỚI toàn bộ.** Session mới làm từ đầu theo spec dưới.
> File này = trạng thái toàn bộ dữ liệu WFO + spec xuất mới. Các doc liên quan (bối cảnh sâu):
> `claude/wfo_muc1_decision_2026-08-08.md`, `claude/wfo_muc1_exec_log.md`, `claude/wfo_data_status.md`,
> `claude/wfo_data_flow_architecture.md`, `claude/wfo_rerun_2026-08-08_ce.md`, `claude/wfo_kaggle_parallel_plan_2026-08-08.md`.
> ⚠️ CHƯA CHẠY GÌ theo spec này — Uni dặn note lại để session mới làm.

> 🔒 **GRID = 1 PHÚT — CHỐT CỨNG (Uni 09/08). LUÔN làm việc trên lưới 1m tuyệt đối, KHÔNG ĐỘNG GÌ tới 15m dưới bất kỳ hình thức nào.** Toàn pipeline (label, features, selector, dataset, WFO) đặt `LABEL_STEP_MIN = FF_GRID_MIN = SELECTOR_GRID_MIN = 1`. 15m từ đây chỉ là rác tham chiếu — KHÔNG cân nhắc lại, KHÔNG đo lại, để tránh lặp lại tư duy sai đã tốn rất nhiều thời gian đợt vừa rồi. (Ghi chú code: nhánh filtered của `ExportFeaturesForPythonTool` vốn đã chạy `selectCoins` MỖI PHÚT — `FF_GRID_MIN` chỉ ảnh hưởng nhánh unfiltered — nên đường filtered vốn dĩ đã là 1m.)

## 0. QUYẾT ĐỊNH CHỐT (spec xuất mới)

1. **Xuất MỚI toàn bộ, không tái dùng dataset cũ** (dữ liệu cũ lộn xộn: lẫn 1m/15m, filtered/unfiltered, bản hỏng, nhiều grid — không tin được). Clean slate.
2. **Nới `EntrySignalFilter` từ top-10% → top-15% hoặc 20%.** Hiện `TOP_PCT=0.10` (hardcode). Mở rộng phễu: nhiều candidate hơn → nhiều dữ liệu train + nhiều cơ hội trade hơn (đổi lại chất lượng TB/candidate giảm nhẹ). → đang ĐO thực tế số bản ghi tại 0.10/0.15/0.20/0.25/0.30 trên lưới 1m để chốt (xem `claude/wfo_toppct_measure_2026-08-09.md`).
3. **Xuất features + label CÙNG GRID = 1m** (bắt buộc khớp, xem landmine #1). Filter áp cho cả 2.
4. **Lưu theo NĂM** (1 file/năm), KHÔNG tách nhỏ theo quý như hiện tại.
5. Chỉ train/serve trên tập đã qua filter (filter-train = filter-trade → không selection bias — đã phân tích, xem mục 4).

**GRID: CHỐT 1 PHÚT (xem callout khoá ở đầu file).** Không còn tham số grid mở.

## 1. CODE PHẢI SỬA TRƯỚC KHI XUẤT

| Thay đổi | File | Ghi chú |
|---|---|---|
| `TOP_PCT` 0.10 → 0.15/0.20 | `src/main/java/com/binance/chuyennd/ai_ml/features/export/funding/EntrySignalFilter.java` | Constant "KHÓA CỨNG" — đổi = re-export + retrain toàn bộ (đúng ý đồ lần này). Giữ nguyên tier volume≥2000 USDT + cửa sổ rate30m. |
| Tách theo QUÝ → NĂM | `ExportFundingLabel.java` (logic chia file quý, xem class-doc TASK-251 fix#3) + `ExportFeaturesForPythonTool.java` (chunk 3 tháng) | Hiện chia quý (Jan/Apr/Jul/Oct) để nhẹ RAM/merge. Đổi sang năm = ít file hơn, mỗi file to hơn (~4× quý). Cân RAM merge cuối. |
| tool1 chạy chế độ FILTER | Nút CE `tool1_export` đang **hardcode `FF_UNFILTERED=1`** (mcp_tools-v3.py ~L871) | Muốn filtered phải bỏ FF_UNFILTERED (mặc định class = filtered/EntrySignalFilter) → phải sửa nút HOẶC bg_run raw với env không set FF_UNFILTERED. |
| Label theo filter? | `ExportFundingLabel` hiện all-coin (universe qua lifecycle isAlive, KHÔNG qua EntrySignalFilter) | Để tập train = filtered: hoặc (a) filter label export luôn, hoặc (b) giữ label all-coin rồi join với features-filtered (label file to hơn nhưng tập train vẫn = filtered). Chốt khi làm. |

⚠️ Máy dev (Windows) build được: Maven qua wrapper `C:\Users\pc\bin\mvn.cmd` (lệnh `mvn` trần trong PowerShell non-interactive báo not-found vì thiếu User PATH → gọi FULL path). JDK `javac 11.0.17`. Oracle chỉ JRE → build trên Windows rồi scp jar lên Oracle.

## 1b. ĐO TOP_PCT (đang làm — 2026-08-09)

Cơ chế `EntrySignalFilter.selectCoins`: cross-sectional MỖI mốc t → lọc `volume≥2000` + `|rate30m|>0` được `N_t` ứng viên → giữ `ceil(N_t × TOP_PCT)`. Vậy `features_count(pct) = Σ_t ceil(N_t × pct)`, **N_t độc lập TOP_PCT** → chỉ cần đo `{N_t}` MỘT lần (count-only, bỏ extractFeatures) là suy ra cả 5 ngưỡng. Chi tiết + kết quả: `claude/wfo_toppct_measure_2026-08-09.md`.

## 2. TRẠNG THÁI DỮ LIỆU HIỆN TẠI (đo trong phiên 08-09/08)

### 2a. Kaggle (sau khi đã dọn 24 dataset phiên 08/08 — dùng ~59/100 GB)
| Dataset | Cỡ | Vai trò | Với plan mới |
|---|---|---|---|
| `hpo-ticker-daily` | 10.7GB | ticker 2021→2025 (nến 1m) | 🟢 GIỮ (nguồn sim, không phải re-export) |
| `hpo-ticker-2026` | 2.7GB | ticker 2026-H1 | 🟢 GIỮ |
| `funding-oi-percoin` | 3.2GB | OI 5 feat + symbol_map.csv | 🟢 GIỮ (OI "kệ nó", merge_asof tol 2h) |
| `funding-gate-wfo-pred` + `gate-dataset-full` | 30MB+361MB | gate pred/feature | 🟢 GIỮ |
| `funding-tool1-1m-*` (22 quý) | 40.8GB | tool1 **1m UNFILTERED** | 🟠 SẼ BỊ THAY bằng bản filtered mới; cân xoá sau khi có bản mới |
| `funding-tool1-features` (4.86GB) + `-unfiltered` (2.19GB) | 7GB | tool1 gộp CŨ | 🟠 rác cũ, xoá được (Uni giữ lại phiên trước để chắc) |
| `wfo-ds-ret2-4h-ff` | 99.5MB | dataset WFO 02/8 (15m, verdict M) | 🟠 tham chiếu; plan mới dựng lại |
| `funding-predict-1m-v1/v1`, `funding-model-v1` | ~1GB | predict/model CŨ | 🟠 xoá được |
| `wfo-dataset-wf-v3/-leakfree`, `wfo-oizgate`, `ablation-4h-ds` | ~0.7GB | thí nghiệm cũ | 🟠 xoá được |
| jars: `java-run-lc`, `wfo-jar-1m`, `label-export-jar`... | ~0.1GB mỗi | runtime | 🟢 GIỮ |

**ĐÃ XOÁ phiên 08/08 (25 dataset, ~9.5GB):** 17 label-1m per-quarter (HỎNG) + `funding-label-1m-y2022` + `funding-label-full` + `qtest-gz/dat` + `ticker-probe-1783948469` + 2 jar label trùng (`wfo-label-jar`, `wfo-label-jar-20260808`).

### 2b. Oracle (161.118.212.3, SSH:22 + Aerospike:3222 đều sống 09/08)
| Path / set | Nội dung | Với plan mới |
|---|---|---|
| `/home/ubuntu/claudedata/wfo15m/label_ds_15m/` | **Label 15m FRESH** phiên 09/08: 21 file quý .pb, 42,723,220 dòng, 778 coin, 1.7GB, PASS sạch (0 orphan part, mọi quý reconciled). meta stepMinutes=15. | 🔴 15m → BỎ theo CHỐT 1m. Giữ tạm chỉ như rác tham chiếu, KHÔNG dùng. |
| `/home/ubuntu/claudedata/wfo1m/label_ds_1m/` + `label_ds_1m_BROKEN_20260808` (3.7GB) | label 1m dở/hỏng (đợt 636M đã bỏ) | 🔴 rác, xoá được |
| `wfo_ds_oiz` | dataset built (generator khác) | tham chiếu |
| `wf_pred_ret2wf` | selector predictions cũ (ret2wf) | tham chiếu |
| `runs/{A,B,C}_RET2WF` | run dir cũ 12/07; `app.jar` = symlink GÃY (`binance-futures-preflight.jar` đã xoá) | không tái dùng được |
| `/home/ubuntu/java/simulator/*.jar` | ~45 jar (gatecount*, preflight*, selrank-v1, binance-lf-frozen-1.0.0...) | jar frozen ĐÚNG cho WFO **chưa xác định** (grep env-knob thất bại) — phải javap kiểm khi tới bước WFO |
| Aerospike: `kline_1m_opt`, `market_data`, `symbol_lifecycle`(698), OI sets, gate sets | nguồn LIVE | 🟢 nguồn để xuất mới |
| WFO jobstore `103.157.218.226:3222 ns=ticker` | 16 window, 2 RUNNING stale −6 ngày, DONE=4 — BẨN. Box 226 đã quyết RETIRE. | 🔴 phải reset (wfo_fanout tự reset) + quyết repoint sang Oracle |

### 2c. Đã dừng phiên 08/08 (đừng tưởng còn chạy)
- Đợt canonical-1m label 636M: 2 trigger (launcher + verify/merge 07:00) ĐÃ XOÁ. 3 shard Kaggle 2021/2022/2025 để tự xong, **bỏ output**.
- Không còn scheduled task WFO nào đang treo (trừ reminder verify label 15m đã fire xong).

## 3. LUỒNG XUẤT MỚI (thứ tự) — theo `wfo_data_flow_architecture.md`

1. **(sửa code)** `TOP_PCT`=0.15/0.20 (chốt sau khi đo); chia file theo NĂM; GRID=1 (đã chốt cứng).
2. **Label** (`ExportFundingLabel`, grid=1, by-year) ← kline_1m_opt + lifecycle. Verify by-số: exit0 / không `.partN.pb` / đủ file năm / meta emittedRows.
3. **tool1 features CÓ FILTER** (`ExportFeaturesForPythonTool`, KHÔNG set FF_UNFILTERED, `FF_GRID_MIN`=1, by-year).
4. **selector predict** (`ml/training/gen_funding_wf_predictions.py` trên Kaggle, `SELECTOR_GRID_MIN`=1, `FIRST_CUTOFF=20230101`, WIN=0.06, chỉ maxFav 4 horizon dùng 4h). ⚠️ Script hiện KHOÁ 1 grid cho cả train+predict (train_predict_fold cắt cùng feat_df) — nếu sau này muốn train-grid≠predict-grid phải sửa.
5. **build_ds** (`WfoDataset.export` trên Oracle) ← market live + gate live + predict_wf. `WFO_SEL_HORIZON_IDX=0`(4h), `WFO_SET_PRED=ai_pred_market_gate_wfo`. ⚠️ Oracle repo KHÔNG git → `code_sha=unknown` làm `export()` throw → truyền code_sha tường minh.
6. **validate_canonical_wfo.py** + gate_sign (người).
7. **WFO fanout** (`ce wfo_fanout <ds> <jar> 1 42 2 0 <tag> "<frozen_env>,WFO_HARNESS_FIX=true"`). Frozen config verdict-M (rank-K8, giveback-floor, funding ON — xem `START_HERE_20260802.md`). N=1 trước, N=30 confirm sau. Bù mảng 2026 forward (Kaggle geo-block Binance → dùng Oracle).

## 4. VÌ SAO (tóm tắt phân tích 08-09/08 — để session mới không đi lại)

- **Q: filter-train + chỉ-trade-khi-qua-filter khác unfiltered ntn?** Nếu train VÀ serve đều chỉ trên tập qua EntrySignalFilter → train-dist = serve-dist → **KHÔNG selection bias**. Unfiltered (canonical) train trên ~90% coin không bao giờ trade = phí + gấp ~10× data + OOM. Filter cố định (không phải cái WFO tối ưu) → **filtered đúng hơn VÀ rẻ hơn**. Đây là lý do bỏ canonical-1m-unfiltered.
- **Q1: 15m có phản ánh 1m khi trade?** Feature + SL: có (SL chạy ticker 1m qua forward-fill). Nhưng **timing VÀO LỆNH ở 15m trễ ≤15'** so với 1m → ĐÃ CHỐT bỏ 15m, chỉ 1m. Filter dùng rate30m (chậm) nên lệch khiêm tốn.
- **Kích thước** (all-coin 1m = 636M đo thật; 15m = 42.7M đo thật): xem mục 5.

## 5. DUNG LƯỢNG DỰ KIẾN theo grid × độ nới filter (15m chỉ để tham chiếu lịch sử — ĐÃ BỎ, xem CHỐT 1m)

Pass-rate EntrySignalFilter: top-10% hiện tại ≈ giữ ~6-10% thị trường. Nới lên 15%/20% ≈ giữ ~15%/20%. (Con số ĐO THỰC đang cập nhật ở `claude/wfo_toppct_measure_2026-08-09.md`.)

| Grid | all-coin | filter 15% | filter 20% | ma trận train (×45 feat ×4B) |
|---|---|---|---|---|
| **1 phút** | 636M | ~95M | ~127M | 15% → ~17GB · 20% → ~23GB (fit Kaggle 30G, hơi sát) |
| **15 phút** (BỎ) | 42.7M | ~6.4M | ~8.5M | ~1.2–1.5GB (nhẹ tênh) — KHÔNG DÙNG |

⇒ 1m-filter-15-20% train được (khác 1m-unfiltered 636M/115GB OOM).
Label (all-coin, không filter) by-year 1m ≈ 27GB / 21 file→6 file năm. Nếu filter label luôn thì nhỏ tương ứng.

## 6. LANDMINE (đừng vấp lại — đã trả giá)

1. **Grid PHẢI đồng bộ** `LABEL_STEP_MIN = FF_GRID_MIN = SELECTOR_GRID_MIN` (= 1, đã chốt). Lệch → join (symbol,ts) rớt ~93% ÂM THẦM (không lỗi). Cảnh báo #1 `WFO_DATA_PIPELINE_MASTER.md`.
2. **Node `label_export` KHÔNG tự `mkdir -p`** dir output → tạo dir trước (đã dính lỗi FileNotFoundException phiên này).
3. **`bg_status` trả khối `result` CŨ lẫn `state`/`log_tail` MỚI** → chỉ tin `log_tail` + `state.status`, KHÔNG tin `result` cũ.
4. **PURGE ở lưới 1m**: default 288 bước = 4.8h ở 1m (không phải 72h) → leak. gen script đã tự tính từ H_STEPS["72h"] — đừng hardcode lại.
5. **`WFO_SEL_HORIZON_IDX` default code = 1 (12h)**; canonical cần **0 (4h)** — override ở build_ds.
6. **Jar WFO** phải có rank-K + WFO_HARNESS_FIX + funding + frozen-genome-inject; dùng nhầm = số SAI ÂM THẦM. Xác định bằng javap (grep chuỗi trong jar fat 99MB thất bại).
7. **Oracle RAM ~23G, dễ OOM compute** (đã sập vì label 1m). KHÔNG chạy 2 job java nặng (≥12G) song song. Count-only N_t nhẹ hơn export thật (bỏ extractFeatures + không ghi) nhưng vẫn chạy PER-YEAR để chặn OOM history tích luỹ.
8. **`ExportFundingLabel`/`ExportFeaturesForPythonTool` từng exit 0 khi BLOCKED/IOException** (che lỗi). Verify PHẢI dựa SỐ, không dựa log "✅ Xong". (Lần label 15m 09/08 fail thì fail loud exit1 — tốt.)
9. **WFO jobstore trỏ box 226 retired + bẩn** → reset + quyết repoint Oracle trước khi fanout.
10. **Oracle `/home/ubuntu/BinanceFuturesJava` KHÔNG phải git** → `code_sha=unknown` → build_ds throw → truyền tường minh.

## 7. CÁCH CHẠM HẠ TẦNG (cho session mới)

- Oracle: qua `orchestrator/ce.cmd` (Desktop Commander start_process, shell powershell/cmd, redirect ra file `C:\Users\pc\*.txt` rồi `type` — capture stdout của ce hay rỗng nếu đọc trực tiếp). ce.cmd PHẢI CRLF (LF → mọi nút exit 255). Nút: `label_export`, `tool1_export`, `bg_status/bg_report/bg_run`, `sys_logtail`, `wfo_fanout/wfo_status/wfo_report`, `sys_health`.
- Kaggle: `kaggle` CLI trên máy Uni (venv `/home/ubuntu/kaggle_latest_venv` trên Oracle, hoặc venv trên máy Uni). Cap 5 slot CPU đồng thời. Quota ~59/100GB.
- Repo máy Uni: `E:\educa\source\github\20260415\BinanceFuturesJava` (device bridge). ssh/scp: `C:\Program Files\Git\usr\bin\{ssh,scp}.exe -i C:\Users\pc\.ssh\id_rsa_chuyennd ubuntu@161.118.212.3`.
- ⚠️ Kaggle đọc Aerospike Oracle chỉ chịu **~3 kernel đồng thời** (kernel thứ 4 EOFException drop connection) — nếu fanout đọc live phải giới hạn.
