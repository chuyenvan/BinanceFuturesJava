# DEPLOY242_G2FLAT3_READINESS_20261002 — BẬC 1: audit sẵn sàng đưa 242 (tiền thật) về đúng B0 = G2 + FLAT3

- **Ngày:** 2026-10-02 (GMT+7). **Vai:** release/quant engineer. **Phạm vi bậc này:** CHỈ ĐỌC 242 (cat/grep/tail/ls/sha256sum/ps/free/dmesg + `cat`/`tar` ra stdout để kéo file về Oracle), 0 sửa 242, 0 deploy shadow, 0 sửa `.java`, 0 sim Java, 0 Kaggle. Python offline nhẹ trên Oracle (`nice -n 10`).
- **Baseline:** `profiles/g2_flat3.properties` (md5 file `c6d4ef57…`), B0 printDone md5 `650c386f0d0dfea334af9d55ca2f21d4` (n 2517, eq 131 908).
- **Script (commit cùng doc):** `research/analysis/deploy242_gate_lineage.py` (A retrain+export+parity, B lineage, C phân bố, D buffer) · `deploy242_lineage_probe.py` (cutoff nào tái lập `.onnx` 242) · `deploy242_export_fold.py` (export ứng viên theo CUTOFF) · `deploy242_jar_diff.py` (CRC từng `.class`). Probe 242: `~/claude_master/1002/deploy242/{remote242.sh,remote242b.sh,pull242.sh}`. JSON gộp: `docs/audit/DEPLOY242_G2FLAT3_READINESS_20261002.json`.
- **2026** chỉ dùng để so phân bố LIVE (không chấm sim, không chọn tham số). Mọi số dưới đây đo lại được bằng các script trên.

## 0. QUYẾT ĐỊNH OWNER (ghi nhận 2026-10-02 ~17:05 GMT+7, lúc phiên audit nhận lệnh)

| # | quyết định | hệ quả kỹ thuật (đã kiểm) |
|---|---|---|
| **1a** | **Chấp nhận** 48–62 vị thế LEGACY thật trên 242 chạy theo luật thoát mới (arm 0,07 + FLAT3 gap 3 %), **không** tách lại về luật HEAD cũ. | Đóng F2 của `AUDIT_G2FLAT3_20261002` ở mức governance. Luật thực tế đang áp xem §8 (dead-zone ×5,21847 VẪN còn cho legacy ⇒ SL legacy chỉ ratchet khi lãi ≥ 36,5 %). Hiện `[LEGACY] managed 48`; 0 sự kiện `New price SL`/`Update SL`/`TS-GAP` từ 01/10 00:00 → 02/10 17:14. |
| **2** | Đưa 242 chạy **ĐÚNG cấu hình B0** đã backtest. | Bậc 1 (doc này) = audit + kế hoạch; bậc 2a/2b/3 ở §9. **Bậc 3 hiện CHẶN** (lý do §9.0). |

## 1. KẾT LUẬN (8 câu)

| # | câu | kết luận | 1 dòng bằng chứng |
|---|---|---|---|
| Q1 | Lineage model gate + export ONNX | **CẦN SỬA** (không chặn) | `.onnx` 242 sha256 `d19fc8cd…` = `wfo_models/fold_20` (md5 `8ec99757…`) = **cùng recipe WFO**, cutoff **2026-04-01** (retrain recipe cutoff 20260401 ↔ ONNX242 pearson **0,99821**/spearman 0,99877; 20260101: 0,99675). Export fold cuối DEV (cutoff 20260101) ĐÃ LÀM: sha256 `d37969ee…`, parity Python↔ORT max\|Δ\| **3,4e-8** (n 39 143). Đúng-B0 cho quý 2026Q4 cần fold cutoff **2026-10-01** ⇒ store phải nối tới 2026-09-30 (cần chạy `ExportGateDataset` — ngoài bậc này). |
| Q2 | Phân bố p15 live vs DEV | **ĐẠT** (giả thuyết "khác thế hệ" BÁC BỎ) — kèm rủi ro regime | Trên CÙNG feature LIVE (feat_dump 242, 6 229 phút): ONNX242 max **1,895 %**, model DEV-gen (cut20260101) max **1,975 %**, pearson 0,985. Đổi thế hệ model **không** mở đuôi. Đuôi ≥ 2,947 %: DEV 2025 **3,3e-4** phút, 2025Q4 1,1e-3, replay offline 2026-07…09 (NEW) **8,5e-5**, LIVE **0/6 229**. |
| Q3 | Gate rolling buffer | **CẦN SỬA** | Buffer 46 224 rec (2 889 tick × 16), 2026-09-30 17:01 → 10-02 17:10 (+07), arm ≈ **2026-10-07 17:01**. Đổi model: r_new/r_old trung vị **1,000**, max 0,01344 vs 0,01401 (−4 %) ⇒ chỉ cần biến đổi `r·p15_new/p15_old` (feat_dump phủ 100 % record), KHÔNG phải seed 90 ngày. 90 ngày lịch sử: không đủ (feature LIVE chỉ từ 09-28; sp 1' chỉ từ 09-28). Fallback 7d ⇒ n_pass = 0 (p15 max 1,9–2,0 % < thr_min 3,08 %). |
| Q4 | Parity jar + harness | **CẦN SỬA** | Jar 242 `8f3ee52c` ↔ `ea14071d` (jar đã tái lập B0 md5 `650c386f` byte-identical, kernel `bdjar-par`): **chỉ khác 2 class** `Configs`, `MarketBigChangeDetector` (= `08beda05`, key `SIM_BD_FRACTION` mặc định 0 ⇒ no-op). Harness: config PASS 27/27 · features FAIL 27/33 · gate MISSING · marketparams FAIL · selector MISSING · entry FAIL (0 vs ≥1) · exit MISSING · selftest 4/4 PASS ⇒ overall FAIL. Harness **mù** key `DCA_GRID_ENABLED`. |
| Q5 | Ổn định runtime 242 | **ĐẠT** | Từ 01/10 11:04 → 02/10 17:14: `[GATE]` **1 811/1 811 phút (100 %)**; OOM **0** (OOM cuối 29/08); ERROR/Exception **0**; restart đúng nhịp 12 h (12:54 · 00:55 · 12:56); `[OI-LIVE] inplace refresh 732 coin … evicted=0` mỗi giờ; pass selector p50 178 ms / p99 648 ms. **+ CẦN SỬA:** sau auto-restart JVM chạy KHÔNG có `-Xms5g -Xmx5g` (`Utils.reset`, heap mặc định ≈ 1,95 GB) — §6. |
| Q6 | Chênh runtime 242 ↔ B0 | **CẦN SỬA** (1 lệch lớn) | **DCA grid KHÔNG có trên đường live**: `DCA_GRID_ENABLED` unset trên 242 (`Configs.java:195` ⇒ false) và đường live gọi `DcaProcessor.getDCAProduction` (`:156-179`, logic `shouldDca` cũ, duyệt vị thế THẬT) — grid chỉ ở `getDCA` sim (`:40-43`). Ledger giấy không trừ phí/funding. `WFO_FUNDING_PRED_DIR` (F8) chỉ sim ⇒ 0 ảnh hưởng live. |
| Q7 | Legacy (1a) | **GHI NHẬN** | Legacy: arm 0,07 · SL đầu = lãi−3 pp · ratchet chỉ khi lãi ≥ 36,5 % (×5,21847) · không time-stop · không entry/DCA giấy. Sổ giấy: arm 0,07 · ratchet liên tục · time-stop 168 h. Bảng §8. |
| Q8 | Runbook 3 bậc | §9 | **2a làm được ngay** (cần owner gật + chọn model gate). **Bậc 3 CHẶN**: `LiveProfileC3.forceNoPush()` hardcode true ⇒ `SHADOW_NO_PUSH=false` **không có tác dụng**; tắt profile thì mất S1 selector + quay về dead-zone ×5,22 + mất time-stop ⇒ KHÔNG còn là B0. Cần code mới. |

**Cái gì CHẶN bậc nào (tóm):**
- **2a (shadow_c3 Oracle):** không có gì chặn kỹ thuật. Cần: owner gật; chọn model gate cho 2a (§9.1 đề xuất giữ `fold_20` để cô lập biến); copy buffer 242.
- **2b (242 paper):** chặn bởi 2a PASS. `n_pass>0` chỉ đo được sau khi buffer arm (≥ 2026-10-07 17:01).
- **3 (tiền thật):** CHẶN bởi (i) không có đường code "C3 + lệnh thật" (forceNoPush hardcode; tắt profile ⇒ khác B0); (ii) DCA grid không có ở đường live; (iii) buffer < 30 ngày (rủi ro pass-rate phồng, Q2 audit: 2021Q3 = 2,9× danh nghĩa); (iv) chưa có bằng chứng edge B0 trong regime p15 2026 (đuôi 4× mỏng hơn 2025).

---

## 2. Q1 — LINEAGE MODEL GATE + EXPORT ONNX → **CẦN SỬA**

### 2.1 Model đang chạy trên 242 (kéo về READ-ONLY bằng `cat`)

| thuộc tính | giá trị |
|---|---|
| path | `/home/chuyennd/java/storage/ai_ml_data/ai_models_reg_v3/Model_Regressor_Return15M.onnx` (cwd `v_t_m`, `FILE_AI_PREDICTIONS=../storage/ai_ml_data/ai_models_reg_v3`) |
| sha256 / md5 | `d19fc8cddd9fb11778653e4b108bb52da92ea168117efac4a407c18c0f260474` / `8ec9975726270782692bfe00b39bd37f` |
| mtime 242 | 2026-08-17 16:27 (deploy gate WFO); bản trên Oracle `claudedata/wfo_models/fold_20/` mtime 2026-08-06 — **md5 trùng** |
| cấu trúc | `OnnxMLTools 1.16.0`, opset ai.onnx.ml 1, `TreeEnsembleRegressor` **150 cây**, 4 604 node, 33/33 feature dùng, input `float_input [?,33]`, output `variable [?,1]`, `post_transform NONE`, base 0,006191; **không scaler** (`Scaler_Return15M.onnx` chỉ còn `.disabled_wfo`/`.bak_gatewfo_20260817` ⇒ feed RAW, đúng `train_gate_fold.py:7`) |
| metadata train window | **KHÔNG có** trong file (metadata_props rỗng) ⇒ xác định bằng probe tái lập (§2.2) |

### 2.2 Probe: cutoff nào tái lập `.onnx` đóng băng (`deploy242_lineage_probe.py`, 200 000 dòng store từ 2024-01-01)

| retrain recipe @cutoff | ↔ ONNX242 (fold_20) | ↔ wfo fold_17 | ↔ wfo fold_18 | ↔ wfo fold_19 |
|---|---|---|---|---|
| 20250701 | 0,679 / 0,984 | **0,998 / 0,999** | 0,990 / 0,992 | 0,682 / 0,987 |
| 20251001 | 0,675 / 0,993 | 0,989 / 0,992 | **0,998 / 0,999** | 0,678 / 0,995 |
| 20260101 | 0,997 / 0,997 | 0,702 / 0,988 | 0,699 / 0,996 | **0,998 / 0,999** |
| **20260401** | **0,998 / 0,999** | 0,697 / 0,984 | 0,694 / 0,993 | 0,997 / 0,997 |
| 20260701 | 0,989 / 0,969 | 0,722 / 0,943 | 0,721 / 0,955 | 0,987 / 0,966 |

(pearson / spearman). Đọc: `wfo_models/fold_k` = WFO expanding cùng recipe `ml/gate/train_gate_fold.py` với **cutoff = 2021-04-01 + 3k tháng** (fold_17 → 2025-07-01, fold_18 → 2025-10-01, fold_19 → 2026-01-01, **fold_20 → 2026-04-01**). ⇒ Model live = **fold WFO cutoff 2026-04-01, train 2021-01-01 → 2026-03-31 (gồm 2026Q1)**, cùng họ với thế hệ sinh `pred.bin` (retrain cutoff 20251001 ↔ `pred.bin` 2025Q4: pearson **0,99193** / spearman 0,99547 — tái lập lại đúng `RESULT_PREDBIN_REPRO` §2.2). Pearson thấp (~0,68) giữa các cutoff khác nhau là do vài điểm cực trị (ONNX242 trên store 2025Q4 max **119,5 %**), spearman vẫn ≥ 0,98.
⇒ Phát biểu F1 của `AUDIT_G2FLAT3_20261002` *"model live KHÁC thế hệ DEV"* **sai ở mức recipe**: cùng recipe/feature contract/toolchain, chỉ là fold muộn hơn 2 quý. (Kết luận `RESULT_PREDBIN_REPRO` "bộ `.onnx` đóng băng không phải thế hệ sinh pred.bin" đúng ở nghĩa *khác cutoff*, không phải khác recipe.)

### 2.3 Export fold cuối sang ONNX (ĐÃ làm, ứng viên — CHƯA deploy)

| ứng viên | train window (UTC, purge 15') | rows | sha256 ONNX | parity Python↔ORT | dùng 2026? |
|---|---|---|---|---|---|
| `model/` cut **20260101** (fold cuối DEV) | 2021-01-01 00:00 → 2025-12-31 23:44 | 2 629 425 | `d37969eefa93bf93865cd3de78618a4a5b899b6c22e5a06529e30c0c8aeab915` | max\|Δ\| **3,35e-8** (n 39 143: 20k store + 6 229 feat_dump LIVE + 12 914 devexport) **PASS ≤1e-6** | không (lưu ý: cutoff theo recipe = 00:00 **UTC** ⇒ gồm 7 h đầu 2026-01-01 giờ +07 — giống hệt WFO gốc) |
| `model_cut20260701/` | → 2026-06-30 17:00 (hết store) | 2 889 623 | `9ba5b0b87b6609e0af232a7eb8f56476af1ef268bb12ff2ea978e3bfb3ae1ca9` | max\|Δ\| 6,7e-8 PASS | **CÓ** (2026H1) — chỉ hợp lệ cho LIVE |
| (đúng-B0 cho 2026Q4) cut **20261001** | → 2026-09-30 | — | — | — | **CÓ** — **CHƯA làm được**: store `gate_dataset_full.csv.gz` dừng ở 2026-06-30 17:00 UTC |

Contract I/O của cả 2 ứng viên **trùng ONNX242** (`float_input [?,33]` → `variable [?,1]`, 150 cây, OnnxMLTools 1.16.0) ⇒ Java `OnnxInferenceManager.runModel` (`:149-154`, lấy input đầu tiên, đọc `float[][]`) dùng được **không đổi code**. Thứ tự feature = `V3FULL` khoá cứng (`train_gate_fold.py` = `extractFeaturesV3Full`). Kiểm chuỗi inference LIVE: ONNX242 chạy ORT trên feat_dump ↔ `p15_out` Java ghi ra: max\|Δ\| **5,6e-9** (n 6 229) ⇒ feature dump + inference Java khớp Python.

**Bước export (tái lập, đã script hoá):**
1. `cd ~/claude_master/1002/deploy242 && python3 $R/research/analysis/deploy242_gate_lineage.py` (fold_final 20260101 + parity + manifest) hoặc `CUTOFF=yyyymmdd python3 $R/research/analysis/deploy242_export_fold.py`.
2. Script dùng **đúng** hyperparam `train_gate_fold.py` (XGBRegressor d4/n150/lr0,05/sub0,8/col0,8/mcw10/seed42/n_jobs4), purge 15', nhãn `label_oldbasket`, `onnxmltools.convert_xgboost` + `FloatTensorType([None,33])`; môi trường xgboost 3.2.0 · onnxruntime 1.23.2 · onnxmltools 1.16.0; store sha256 `d153b3ba…`.
3. Parity cổng: Python `model.predict` vs ORT trên ≥20k vector ⇒ max\|Δ\| ≤ 1e-6 (đạt 3,35e-8). Cổng thứ 2 khi deploy: ORT(feat_dump LIVE) ↔ `p15_out` Java sau restart ⇒ max\|Δ\| ≤ 1e-6.

**Việc CẦN SỬA để "đúng B0" tuyệt đối:** B0 dùng p15 OOS của fold có cutoff = đầu quý đang giao dịch. Cho 2026Q4 ⇒ cutoff **2026-10-01** ⇒ phải nối store bằng `features/export/gate/ExportGateDataset` (replay Aerospike, Java) cho 2026-07-01 → 2026-09-30 + nhãn `label_oldbasket`, rồi `deploy242_export_fold.py CUTOFF=20261001`; lặp lại mỗi quý (ghi vào runbook vận hành). Không có thì **phương án B** (đã sẵn): cut20260701 (trễ 1 quý) hoặc giữ fold_20 (trễ 2 quý). Ảnh hưởng thực tế nhỏ: trên feature LIVE, NEW(cut20260101)↔ONNX242 pearson **0,985**, cut20260701↔ONNX242 trung vị khớp (p50 0,865 vs 0,866 %).

## 3. Q2 — PHÂN BỐ p15 LIVE vs DEV → **ĐẠT** (bác bỏ "cùng thế hệ thì đuôi về") + RỦI RO REGIME

`deploy242_gate_lineage.py` §C (đơn vị %, n≥2,947 % = số phút vượt ngưỡng đuôi của `RESULT_GATE_ROOTCAUSE`):

| nguồn | n phút | p50 | p90 | p99 | p99,9 | max | n ≥ 2,947 % (tỉ lệ) |
|---|---|---|---|---|---|---|---|
| `pred.bin` DEV toàn kỳ 2021-04…2025-12 | 2 500 260 | 0,545 | 0,837 | 1,308 | 2,818 | 12,261 | 2 248 (9,0e-4) |
| `pred.bin` DEV **2025** | 525 600 | 0,704 | 0,979 | 1,263 | 1,950 | 11,947 | 174 (**3,3e-4**) |
| `pred.bin` DEV 2025Q4 | 132 480 | 0,901 | 1,114 | 1,402 | 3,483 | 11,947 | 150 (1,1e-3) |
| **LIVE `p15_out`** (feat_dump 242, 2026-09-28 → 10-02) | 6 229 | 0,866 | 1,062 | 1,280 | 1,564 | **1,895** | **0** |
| ONNX242 chạy lại trên feat_dump (kiểm) | 6 229 | 0,866 | 1,062 | 1,280 | 1,564 | 1,895 | 0 |
| **NEW cut20260101 trên feat_dump LIVE** | 6 229 | 0,864 | 1,072 | 1,309 | 1,557 | **1,975** | **0** |
| NEW cut20260701 trên feat_dump LIVE | 6 229 | 0,865 | 1,066 | 1,304 | 1,528 | 1,866 | 0 |
| ONNX242 trên replay offline 2026-07-01 → 09-28 (`devexport_…_FULL`) | 129 137 | 0,594 | 1,006 | 1,244 | 1,539 | 3,570 | 2 (1,5e-5) |
| NEW cut20260101 trên replay offline 2026-07…09 | 129 137 | 0,583 | 1,062 | 1,320 | 1,612 | 6,689 | 11 (**8,5e-5**) |

**Đọc (quyết định):**
1. **Cùng input thì hai thế hệ cho cùng phân bố** (LIVE: pearson 0,985, spearman 0,988; replay: 0,994/0,990). Đổi model **không** làm đuôi LIVE xuất hiện. Đuôi DEV (max 12 %) là thuộc tính của **feature/regime 2021–2025**, không phải của model: chính ONNX242 trên feature store 2025Q4 cho max **119 %** và 198 phút ≥ 2,947 %.
2. 2026-07…09 (replay) đuôi ≥ 2,947 % hiếm hơn 2025 **~4×** (8,5e-5 vs 3,3e-4) và hơn 2025Q4 ~13×. Cửa sổ LIVE 6 229 phút kỳ vọng ~2 phút theo tỉ lệ 2025 ⇒ quan sát 0 **không** đủ bác bỏ "cùng tỉ lệ" (P≈0,13), nhưng replay 129k phút thì có.
3. Hệ quả cho G2: gate là phân vị trên `r` của **chính buffer live** ⇒ sau warm-up sẽ pass ~4,9e-5 × ứng viên **bất kể model** (≈ 1,13 pass/ngày với 16 ứng viên/phút). Nhưng các pass đó sẽ ở p15 ≈ 1,3–2 % thay vì vùng ≥ 3 % như DEV ⇒ **edge của B0 trên DEV chưa chứng minh chuyển giao sang regime 2026** — đây là rủi ro còn lại của F1, KHÔNG sửa được bằng đổi model. Bằng chứng duy nhất khả dĩ: chính paper 2a/2b (mẫu nhỏ) hoặc pre-reg sim B0 trên dữ liệu 2026 (cấm ở bậc này — owner quyết khi nào mở holdout).

## 4. Q3 — GATE ROLLING BUFFER → **CẦN SỬA**

**Hiện trạng** (`run/gate_ratio_live.bin` kéo về READ-ONLY 17:14, sha256 `338e3c0d…`; format `GateRatioPersist` = chunk `[MAGIC "GRR1"][LEN][CRC32][snappy(n×[ts i8][r f4])]`, đọc lại bằng Python, 9 chunk CRC OK):

| chỉ số | giá trị |
|---|---|
| record / tick | **46 224** / 2 889 tick (16 ứng viên/tick) |
| khoảng | 2026-09-30 17:01 → 2026-10-02 17:10 (+07) = **2,0 ngày** |
| r p50 / p99 / max | 0,002074 / 0,006856 / 0,014007 |
| arm (đủ 7 ngày, `GateRatioBuffer.WARMUP_MS`) | ≈ **2026-10-07 17:01** (+07) |
| log | `[GATE-RATIO] q_t=0.008000 buffer=46048 eval=960 pass=0` (17:01) — fallback base |
| bất biến kiểm | record sau khi G2 bật (01/10 11:04): factor·gs = p15/r ≥ 2,658 > sàn 0,26787×1,55 = 0,415 (0 vi phạm); fallback-pass tái tính = **0** = log. Phần seed (17 312 rec, trước 11:04) tính với gs/sp lúc seed, không kiểm chéo được với `[GATE]` cũ (gate fixed 1,70 khi đó). |

**Khi đổi model gate** — buffer cũ **không** vô nghĩa (cùng recipe, cùng input): với model NEW trên đúng các phút trong buffer (feat_dump phủ **100 %** 46 224 record), `r_new = r_old × p15_new/p15_old`: trung vị r_new/r_old ≈ **1,000**, max 0,01344 vs 0,01401 (−4 %). Nhưng phân vị 0,99995 nằm đúng ở đuôi ⇒ vẫn PHẢI biến đổi, không copy nguyên.
**Phương án (đề xuất, theo thứ tự):**
1. **Transform-reseed** (khuyến nghị khi đổi model): tool Python mới (bậc 2a, không đụng `.java`) đọc `gate_ratio_live.bin` + feat_dump cùng phút → ghi file GRR1 mới với `r_new`; record nào thiếu feat_dump thì bỏ. Kiểm: đọc lại = n record, CRC OK, Java `GateRatioPersist.load` nạp được (log `LIVE nạp buffer: size=…`).
2. **Seed 90 ngày: KHÔNG khả thi đúng nghĩa** — feature LIVE chỉ có từ 2026-09-28 (`feat_dump`, 177 file, 1,5 MB); `storage/data/predictionSymbol` (sp) có 44 ngày từ 2026-08-20 nhưng chỉ ~190 tick/ngày tới 09-27, đủ 1' (~2 800/ngày) từ 09-28; replay offline có feature 07-01→09-28 nhưng lệch giá trị 27/33 feature so LIVE (harness). Ghép 3 nguồn này = buffer "nhân tạo" ⇒ **không làm**.
3. **Fallback 7 ngày:** trong warm-up `thr = 0.008·factor·gs` = 3,08–4,30 %; p15 LIVE max 1,895 % (ONNX242) / 1,975 % (NEW) ⇒ **n_pass = 0 cả 7 ngày** với mọi model ⇒ chấp nhận được (sim B0 cũng 0 lệnh 7 ngày đầu 2021-07; tiền thật không bị ảnh hưởng vì không có entry).
**Rủi ro "mở quá tay" khi buffer ngắn:** sau arm, `q_t` = phân vị 0,99995 của 7–30 ngày (161k–691k mẫu ⇒ chỉ 8–34 mẫu trên ngưỡng) ⇒ nhiễu lớn; DEV 2021Q3 pass-rate = 1,45e-4 ≈ **2,9×** danh nghĩa (Q2 audit). ⇒ **Điều kiện bậc 3: buffer ≥ 30 ngày** (sớm nhất ≈ 2026-10-30 nếu không reset) + trần entry/ngày (§8.3).

## 5. Q4 — PARITY JAR + HARNESS → **CẦN SỬA**

**Jar (CRC32 từng `.class` dưới `com/binance/chuyennd/`, `deploy242_jar_diff.py`; javac deterministic ⇒ cùng nguồn = cùng byte):**

| so với jar 242 `8f3ee52c…` (kéo về, sha khớp `EXPORT_FIX_20261001.md`) | class khác | chỉ có ở 242 | chỉ có ở kia | class "nóng" khác |
|---|---|---|---|---|
| `ea14071d…` (module target 10-01 13:14 = `8e7cf99d` + `08beda05` + `a212e79b`) — **đã tái lập B0 md5 `650c386f…` byte-identical** (`kaggle_sim/out/bdjar-par/result.json`: n 2517, eq 131 908, `jar_sha256 ea14071d…`) | **3** (`Configs`, `MarketBigChangeDetector`) | 0 | 1 (`ExportMarketBinFromTicker`) | `Configs`, `MarketBigChangeDetector` = commit `08beda05` (+9/+9 dòng, key `SIM_BD_FRACTION` mặc định 0 ⇒ no-op) |
| `7368be46…` (`sim-jar-gdv2`, worktree `wt_gdv2` = `2b4dcbd3` + cherry-pick GD92 chưa commit) | 17 | 14 | 1 (`GateRollingThreshold`) | `AIRejectFilter`, `GateRollingRatio` (refactor sang `GateRatioBuffer` dùng chung sim/live — đã chứng minh không đổi hành vi bằng parity `ea14071d`), `SimulatorMarketLevelTicker1MStopLoss`, `DetectEntrySignal2TradeNormal`, `BinanceOrderTradingManager`, `S1RankerLive`, `LiveOiFeatProvider`, `DataManagerAerospikeFloatSim`, `LiveFeatureDump` |
| `c389b4be…` (shadow_c3 Oracle hiện tại) | 5 | 4 | 0 | `LiveFeatureDump`, `BinanceOrderTradingManager`, `DetectEntrySignal2TradeNormal` (= EXPORT_FIX + 4h→12h) |

⇒ **Commit nguồn của jar 242** = cây `8e7cf99d` **trừ** `08beda05` (build ~12:53 trước khi commit EXPORT_FIX). Đường sim (gate/exit/sizing) trong jar 242 ≡ jar đã tái lập B0. **Không chứng minh được** đường LIVE (`LiveGateRollingRatio`, `ShadowBookC3`, `BinanceOrderTradingManager`) bằng parity sim — chúng không chạy trong sim; chỉ dùng chung `GateRatioBuffer` + `TradeUtils.trailFromCap`.

**Harness `research/parity/parity_check.py`** (chạy trong bản sao cách ly `~/claude_master/1002/deploy242/harness/`, `fetch` READ-ONLY 72 key, feat_dump/sel_dump kéo về 17:14; KHÔNG ghi đè `docs/result/parity_report.*`): **overall FAIL (exit 2)**

| tầng | KQ | chi tiết |
|---|---|---|
| config | **PASS** | MATCH 27, LECH 0, MISSING 0 (không tính SKIP) — **nhưng** bảng CHECKS không có `DCA_GRID_ENABLED`, `SIM_APPLY_FUNDING`, `SIM_FUNDING_MARK` (lệch thật, §7) |
| features | FAIL | 27/33 vượt ngưỡng tại 451 cặp cùng phút (exact ≤1e-8 / inline ≤1e-3); 26/181 file thiếu gz trailer (file cũ trước EXPORT_FIX + file đang ghi) |
| gate | MISSING | `mode_parity` PASS (ratio=ratio), `gate.repro` PASS (p15_max 0,01895 < thr_min 0,03076 ⇒ 0 pass); cùng-phút DEV MISSING (pred.bin ≤ 2025) |
| marketparams | FAIL | LIVE vs inline 6 179 phút: rateDownAvg max\|d\| 3,3e-3 (corr 0,9936); DCA flip 1 (live 3 / inline 4); BIG_DOWN flip 0 |
| selector | MISSING | sel_dump 1 701 tick/27 216 dòng; thiếu đối ứng DEV cùng tick |
| entry | FAIL | LIVE 0 vs G2 ≥ 1 (hệ quả warm-up) |
| exit | MISSING | 0 lệnh đóng |
| selftest | PASS 4/4 | deterministic · injected-shift · missing-column · gz_writer_finalize |

**Cần sửa:** (a) thêm `DCA_GRID_ENABLED` (+ `SIM_APPLY_FUNDING`, `SIM_FUNDING_MARK`) vào CHECKS harness; (b) tầng exit/entry chỉ đo được sau arm ⇒ tiêu chí 2b; (c) features 27/33 là lệch đã biết (ticker-vs-kline), tổng hiệu ứng lên p15 cùng phút ≤ 0,006 pp (`RESULT_FEATDIFF_PASS2`).

## 6. Q5 — ỔN ĐỊNH RUNTIME 242 (1', TOPK16) → **ĐẠT** cửa sổ 30 h · 1 **CẦN SỬA** (heap sau auto-restart)

| kiểm (READ-ONLY, `remote242*.sh`) | đo |
|---|---|
| cửa sổ | 2026-10-01 11:04 → 2026-10-02 17:31 (+07) = **30,5 h** (yêu cầu ≥ 24 h ✓) |
| `[GATE]` cadence | **1 811 phút distinct / 1 811 phút** (11:04 → 17:14) = **100 %**; giờ thiếu chỉ là 2 giờ biên (11h: 56, 17h: 15). 01/10: 1 439 dòng; 02/10 tới 17:14: 1 035 |
| OOM | `full.log` tổng 229 nhưng **cuối cùng 29/08 21:46**; 28/09 → 02/10: **0/ngày**; `nohup.out` 0; dmesg OOM-kill cuối **14/06** |
| ERROR/Exception | 28/09 → 02/10: **0** mỗi ngày |
| restart | 01/10 11:03 (FIX_242) · 12:54 (EXPORT_FIX) · 02/10 00:55 · 12:56 (auto 12 h ✓, `BinanceOrderTradingManager.java:108` sleep 12 h) |
| RSS JVM trade | PID 13449: 2 021 264 kB (17:11, etime 4:15) → 2 016 436 kB (17:31, 4:35); VmHWM 2 023 428 kB ⇒ **phẳng** (chỉ 2 điểm — trend 24 h cần đo ở 2a) |
| box 242 | RAM 7 821 MB, available ~2 640 MB, swap dùng 631 MB; `BinanceDataIngestor` RSS 2,2 GB; df `/` 86 % |
| pass time | `[PASS-TIMING] selector tick` 02/10 (n 1 035): p50 **178 ms**, p90 264, p99 648, max 37,8 s (tick khởi động) |
| OI fix | `[OI-LIVE] inplace cold-load 644 coin` (12:56) + `inplace refresh 732 coin … evicted=0` mỗi giờ 13:13/14:13/15:13/16:13 ⇒ đang chạy **mode inplace** của `FIX_OOM_OI_LIVE` (`LiveOiFeatProvider.java:76/274-292`; env `OI_LIVE_REFRESH_MODE=inplace`) |

**CẦN SỬA (mới phát hiện):** sau auto-restart, JVM chạy **không có tham số JVM**: `/proc/13449/cmdline` = `java -cp target/binance-java-sdk-1.2.4.jar com.binance.chuyennd.trading.BinanceOrderTradingManager` — `Utils.reset()` (`utils/Utils.java:543-580`) dựng `ProcessBuilder(javaBin,"-cp",classPath,mainClass)` ⇒ mất `-Xms5g -Xmx5g` của `bin/start.sh` (heap mặc định = ¼ RAM ≈ 1,95 GB) và `-Dfile.encoding=UTF-8`. Hiện ổn (0 OOM 02/10 qua 2 chu kỳ) nhờ OI inplace, nhưng **hành vi bộ nhớ khác với lúc deploy/kiểm** và khác shadow_c3 (`-Xmx4g`). Sửa KHÔNG cần `.java`: `export JAVA_TOOL_OPTIONS="-Xms3g -Xmx3g -Dfile.encoding=UTF-8 -Duser.timezone=Asia/Ho_Chi_Minh"` trong `conf/env.sh` (env được copy sang tiến trình con, `Utils.java` `processEnvironment.putAll`) — **đo ở 2a trước**, mức heap đề xuất 3 g (box 7,8 GB + ingestor 2,2 GB; tiền lệ OOM-kill 5,5 GB tháng 6). Sửa gốc (`getInputArguments()`) = việc `.java` của vòng sau.

## 7. Q6 — CHÊNH CÒN LẠI GIỮA RUNTIME 242 VÀ B0 → **CẦN SỬA**

Nguồn: `profiles/g2_flat3.properties` (31 key) vs `conf/env.sh` + `config.properties` 242 (đọc 17:11, lọc key/secret) vs default `Configs.java` vs đường code LIVE thực sự đọc.

| nhóm | key B0 | B0 | 242 | đường LIVE thực dùng | kết |
|---|---|---|---|---|---|
| gate | `SIM_GATE_ROLLING_MODE/DAYS/PCT` | ratio/90/0,999950829 | `LIVE_GATE_ROLLING_*` ratio/90/0,999950829 | `LiveGateRollingRatio` + `GateRatioBuffer` chung sim | khớp (live-only alias) |
| gate | `SIM_GATE_DYN_SCALE` / `SIM_MIN_MOMENTUM_15M` | 1,55 / 0,008 | 1,55 / 0,008 | `EntryGate` | khớp |
| gate | model p15 | OOS WFO theo quý | fold_20 (cutoff 2026-04-01) | `OnnxInferenceManager` | **lệch 2 quý** (Q1) |
| selector | `SELECTOR_RANK_TOPK` / `SELECTOR_ONLY_ENTRY` / nhịp | 16 / 0 / `SIM_ENTRY_SAMPLE_MIN=1` | 16 / 0 / `LIVE_ENTRY_GRID_MIN=1` | S1 `s1a2x1_cut20251231.onnx` + net015 `g015x26_f15_cut20251231.onnx` | khớp; model selector live = fold cuối 2025 (sim 2025Q4 dùng cut20251001) |
| selector | `WFO_FUNDING_PRED_DIR` (F8: 16 vs 18 fold) | `predwf_map_s1a2_x1` | — | **không đọc ở live** | **0 ảnh hưởng live** (chỉ tái lập sim) |
| exit | `SIM_RATE_PROFIT_STOP_MARKET` | 0,07 | 0,07 | giấy: hardcode `LiveProfileC3.ARM_RATE=0.07`; legacy: `Configs` 0,07 | khớp |
| exit | `TS_GIVEBACK_RATIO` / `SIM_TS_MAX_GAP` / `_WEAK` | 1,0 / 0,03 / 0,03 | 1,0 / 0,03 / 0,03 | `TradeUtils.trailFromCap` (chung sim) | khớp |
| exit | `SIM_TS_GIVEBACK=1` (ratchet liên tục) | 1 | 1 | giấy: hardcode liên tục (`ShadowBookC3.tick:365-369`); key không đọc ở live | khớp (giấy) |
| exit | `SIM_LOSER_TIME_STOP_HOURS` | 168 | 168 | giấy: hardcode `TIME_STOP_HOURS=168` (`ShadowBookC3:356`); key không đọc ở live | khớp (giấy) |
| sizing | `SIM_F_BASE` / `U_MAX` / `DCA_GRID_SCALE` / `TIER_FLAT` | 0,015 / 0,60 (default) / 6,0 / 1 | 0,015 / default / 6,0 / 1 | `TradeUtils.managerBudget` (chung) trên equity giấy (`PAPER_EQUITY=35000` + PnL giấy) + trần 4,5 % equity (`DetectEntrySignal2TradeNormal:1000-1002`, không bind: ≈ 0,015/4 equity) | khớp |
| **sizing/DCA** | `DCA_GRID_ENABLED` + `DCA_GRID_WEIGHTS` | **true** + 1,1,1,1 (KEEPLEG0) | **unset ⇒ false** + 1,1,1,1 | live DCA = `DcaProcessor.getDCAProduction` (`:156-179`) — logic `shouldDca` cũ, duyệt **vị thế THẬT** (`BudgetManager.symbol2Pos`) ⇒ trên 242 chỉ gặp coin legacy ⇒ `skip-LEGACY`. Grid (`shouldDcaGrid`) chỉ ở `getDCA` sim (`:40-43`) | **LỆCH LỚN**: sổ giấy **không bao giờ nhồi leg grid**; ngân sách leg0 vẫn chia Σw=4 ⇒ vị thế giấy ≈ ¼ kế hoạch nếu B0 lẽ ra nhồi. (B0: 2 517 cụm = 2 223 PREDICT + 248 BIG_DOWN + 46 DCA_LEVEL1 ở leg đầu; số leg grid không có trong printDone.) |
| risk | `CONC_CAP_PERCOIN_ENABLED/PCT` | true / 0,15 | true / 0,15 | `DetectEntrySignal2TradeNormal:1071-1080` | khớp (no-op trong B0) |
| cost | `SIM_RATE_FEE` / `SIM_SLIPPAGE_RATE` / `SIM_APPLY_FUNDING` / `SIM_FUNDING_MARK` | 0,000982 / 0,000067 / true / true | 2 key đầu có, 2 key sau không | ledger giấy `ShadowBookC3.closeAt` = `(exit−entry)·qty` — **không trừ phí, slippage, funding** | **lệch đo lường** (PnL giấy lạc quan ~0,11 %/vòng + funding) |
| breaker/fix | `SIM_BREAKER_MODE=OFF`, `SIM_FIX_B1..3=true` | | có | sim-only | khớp/no-op |
| **chỉ live** | `LIVE_PROFILE=c3_shadow`, `SHADOW_NO_PUSH=true`, `PAPER_EQUITY=35000`, `ENTRY_CASCADE=0`, `OI_LIVE_REFRESH_MODE=inplace`, `SELECTOR_TIER1_NET015=true`, `TRAIL_HINGE_NET015=true`, `MARKET_SCAN_MIN/PRIORITY=1`, `LIVE_FEAT_DUMP=3000`, `LIVE_FEAT_DUMP_ROTATE_MIN=10`, `TS_PRED_GAP=1`, `SIM_TS_PROFIT_MULTIPLIER=3.0` (key chết), `APP_HEAPSIZE=7000` (không dùng — start.sh cố định 5 g; sau auto-restart: default) | | | | ghi nhận |
| config.properties | `RATE_PROFIT_STOP_MARKET=0.01`, `RATE_FEE=0.0015`, `CAPITAL_START=35000` | | | `Configs` chỉ đọc khoá `SIM_*` qua `Cfg` (`Configs.java:905,925`; comment `:936`) ⇒ 2 key đầu **không có hiệu lực** | ghi nhận |

## 8. Q7 — LEGACY (quyết định 1a): LUẬT ĐANG ÁP THẬT → **GHI NHẬN**

Hai đường cùng một JVM (`LiveProfileC3.on()=true`). Legacy = `(vị thế THẬT Binance) \ (sổ giấy)`, reconcile mỗi `updatePositionInfo` (`LegacySymbols.reconcile`, ghi `run/legacy_symbols.csv`, hiện **48**; tự thu hẹp khi đóng).

| tham số | **LEGACY (tiền thật, đường `processDynamicTP_SL`/`initSLFirst`)** | **SỔ MỚI (giấy, `ShadowBookC3.tick`)** | B0 sim |
|---|---|---|---|
| ngưỡng arm | `Configs.RATE_PROFIT_STOP_MARKET` = env **0,07** (`TradeUtils.java:119-123` → `armRateFor` trả `def` cho legacy) — trước 01/10 là 0,05 | hardcode **0,07** (`LiveProfileC3.ARM_RATE`, `ShadowBookC3:352`) | 0,07 |
| SL khi arm | `entry·(1 + round((L − min(L·1,0; 0,03))/0,005)·0,005)` với L = **lãi hiện tại** lúc arm (`BinanceOrderTradingManager:343-367`, `tsGap:487-500`) ⇒ arm 7 % ⇒ SL ≈ **+4 %** (cũ: arm 5 %, gap T0 = min(L·0,5; 0,08/0,03) ⇒ SL **+2,5 %**) | cùng công thức trên **đỉnh** (`trailRate(peakRate)`) | cùng (`trailFromCap`) |
| ratchet (dời SL lên) | CHỈ khi lãi ≥ **5,21847 × 0,07 = 36,5 %** (`:532-535` dead-zone `LIVE_RATCHET_DEADZONE_MULT`, legacy giữ `def`) — trước 01/10: ≥ 26,1 % | **liên tục** mỗi 10 s (`:365-369`) | liên tục |
| gap FLAT3 | `min(peak·1,0; cap)`, cap = `TS_MAX_GAP`/`_WEAK` theo pNoPump Funding (`LATEST_SEL_PNOPUMP`); cả 2 = **0,03** ⇒ 3 pp theo giá entry (cũ: 0,5 / 0,08 / 0,03) | cùng, pNoPump = net015-mapped (`TRAIL_HINGE_NET015=true`); cả 2 cap = 0,03 ⇒ như nhau | 3 pp |
| sàn SL ≥ entry + 0,5 % | có (`SL_MIN_LOCK_ABOVE_ENTRY`, không thể kích với FLAT3) | không | không |
| time-stop 168 h | **KHÔNG** (`timeStopApplies` = false cho legacy) | có, cụm **chưa arm** (`ShadowBookC3:356-362`) | có (`SIM_LOSER_TIME_STOP_HOURS=168`) |
| SL cứng khi lỗ | không có trên đường này (như HEAD) | không | không |
| entry/DCA mới trên coin legacy | **chặn** (`[SHADOW] skip-LEGACY`, `DetectEntrySignal2TradeNormal:985`, `BinanceOrderTradingManager:221`) — log 566 lần | — | — |
| slot top-K | legacy bỏ qua không đếm rank (`DetectEntrySignal2TradeNormal:467`) | | |
| lệnh thật | SL/TP/reduce-only của legacy **đi sàn thật** (`createSL`) | không (forceNoPush) | — |

Quan sát 01/10 00:00 → 02/10 17:31: **0** `New price SL`, **0** `Update SL`, **0** `[TS-GAP]` ⇒ chưa legacy nào lãi > 7 % kể từ đổi luật; lần gần nhất `New price SL` = 28/09 và 29/09 (1 lần/ngày, luật cũ). Hệ quả cần owner biết: (1) legacy lãi 7–36,5 % sẽ có SL **đứng yên** ở ≈ +4 % (không trailing) — khác cả B0 lẫn luật cũ; (2) không có time-stop ⇒ legacy lỗ giữ vô hạn (như trước).

## 9. Q8 — RUNBOOK 3 BẬC

### 9.0 Cái gì CHẶN bậc nào

| mục | 2a shadow | 2b 242 paper | 3 tiền thật |
|---|---|---|---|
| owner gật bậc | cần | cần | cần (lần cuối) |
| chọn model gate (fold_20 / cut20260701 / cut20261001) | cần (đề xuất fold_20) | cần | cần — đúng-B0 là cut20261001 (cần nối store) |
| buffer gate đủ 7 d (arm) | không chặn ops; chặn tiêu chí n_pass | **chặn** tiêu chí n_pass>0 | — |
| buffer ≥ 30 d | — | — | **CHẶN** |
| đường code "C3 + lệnh thật" | — | — | **CHẶN** — `LiveProfileC3.forceNoPush()` = `ON` (`LiveProfileC3.java:80-82`) và `processOrderNewMarketNew` kiểm nó trước (`BinanceOrderTradingManager.java:174-178`); lệnh giấy còn đi thẳng `shadowHandleOrder` (`DetectEntrySignal2TradeNormal.java:1119-1121`). Tắt `LIVE_PROFILE` ⇒ mất S1 selector (`:421`), ratchet quay về dead-zone ×5,22 (`:532-535`), mất time-stop, sizing theo tài khoản thật, mất tách legacy ⇒ **không còn là B0**. Cần profile mới (vd `c3_live`: chiến lược C3 + push thật + exit đường thật = ratchet liên tục/time-stop đóng thật + giữ tách legacy + kill-switch env) — `.java` + test + parity, vòng sau |
| DCA grid ở đường live | đo lường lệch | đo lường lệch | **CHẶN** (sizing ≠ B0) — cần code hoặc owner chấp nhận "B0-không-grid" sau khi đo tác động trên sim (pre-reg) |
| phí/funding trong ledger giấy | tính offline | tính offline | — |
| heap sau auto-restart | thử `JAVA_TOOL_OPTIONS` | áp nếu 2a PASS | phải xong |
| harness thêm `DCA_GRID_ENABLED` | nên | nên | phải |

### 9.1 BẬC 2a — shadow_c3 Oracle = bản tương đương 242 (PAPER) · bắt đầu được ngay khi owner gật

**Hiện trạng shadow_c3 (đọc 17:26):** `/home/ubuntu/shadow_c3/app`, jar **`c389b4be…`** (không phải `78387f30` như mô tả task — `78387f30` chỉ còn ở `.bak`), `-Xms1g -Xmx4g`, env lệch 242: `TS_GIVEBACK_RATIO=0.5`, `SIM_GATE_DYN_SCALE=1.70`, **không** có `LIVE_GATE_ROLLING_*`/`SIM_TS_MAX_GAP*`/`SIM_F_BASE`/phí/`NET015_MODEL_ONNX`/`SELECTOR_TIER1_NET015`/`TRAIL_HINGE_NET015`, `S1_MODEL_ONNX=…/s1a2x1_cut20251001.onnx`. Đọc Aerospike cụm 242 (`AEROSPIKE_READ_CLUSTER=242`) ⇒ cùng nguồn dữ liệu với 242. Model gate shadow = md5 `8ec99757…` (= 242).
**Đề xuất model gate cho 2a: GIỮ fold_20** (cô lập biến: 2a kiểm *cấu hình + vận hành*; đổi model là bước riêng có cổng parity, §2.3).

```bash
# ---- trên Oracle (KHÔNG đụng 242 ngoài cat/READ-ONLY) ----
A=/home/ubuntu/shadow_c3/app; D=/home/ubuntu/claude_master/1002/deploy242; TS=$(date +%Y%m%d_%H%M%S)
S242="ssh -p 2222 -o BatchMode=yes -i ~/.ssh/id_rsa_chuyennd root@103.157.218.242"
# 0) tiền kiểm: không job nặng, đĩa > 20G
uptime; free -g; df -h / | tail -1
# 1) BACKUP
mkdir -p $A/backup_2a_$TS && cd $A && cp -a target/binance-java-sdk-1.2.4.jar conf/env.sh config.properties bin/start.sh run $A/backup_2a_$TS/ \
  && cp -a ../storage/ai_ml_data/ai_models_reg_v3/Model_Regressor_Return15M.onnx $A/backup_2a_$TS/ \
  && (cd $A/backup_2a_$TS && sha256sum -b binance-java-sdk-1.2.4.jar env.sh config.properties start.sh Model_Regressor_Return15M.onnx > SHA256SUMS)
# 2) JAR = jar 242 (đã kéo, sha 8f3ee52c)
cp $D/live242/jar242.jar $A/target/binance-java-sdk-1.2.4.jar.new && sha256sum $A/target/binance-java-sdk-1.2.4.jar.new | grep -q ^8f3ee52ce4ceac8c \
  && mv -f $A/target/binance-java-sdk-1.2.4.jar.new $A/target/binance-java-sdk-1.2.4.jar
# 3) MODEL selector = đúng bản 242 (READ-ONLY cat), kiểm sha theo SHA256SUMS của 242
$S242 'cat /home/chuyennd/java/storage/c3_models/s1a2x1_cut20251231.onnx'      > /home/ubuntu/s1_model/s1a2x1_cut20251231.onnx
$S242 'cat /home/chuyennd/java/storage/c3_models/g015x26_f15_cut20251231.onnx' > /home/ubuntu/g3x26/g015x26_f15_cut20251231.onnx
sha256sum /home/ubuntu/s1_model/s1a2x1_cut20251231.onnx /home/ubuntu/g3x26/g015x26_f15_cut20251231.onnx   # 8b1dcf00… / 41a07109…
md5sum $A/../storage/ai_ml_data/ai_models_reg_v3/Model_Regressor_Return15M.onnx                         # 8ec99757… (giữ)
# 4) ENV: MERGE (sed đổi tại chỗ + append), KHÔNG thay cả file, KHÔNG đụng SHADOW_NO_PUSH/LIVE_PROFILE
cd $A && sed -i -e 's/^export TS_GIVEBACK_RATIO=.*/export TS_GIVEBACK_RATIO=1.0/' -e 's/^export SIM_GATE_DYN_SCALE=.*/export SIM_GATE_DYN_SCALE=1.55/' \
  -e 's#^export S1_MODEL_ONNX=.*#export S1_MODEL_ONNX=/home/ubuntu/s1_model/s1a2x1_cut20251231.onnx#' conf/env.sh
cat >> conf/env.sh <<'EOF'
# [2a 2026-10-xx] dong bo 242 (G2+FLAT3) — xem docs/audit/DEPLOY242_G2FLAT3_READINESS_20261002.md §9.1
export NET015_MODEL_ONNX=/home/ubuntu/g3x26/g015x26_f15_cut20251231.onnx
export SELECTOR_TIER1_NET015=true
export TRAIL_HINGE_NET015=true
export TS_PRED_GAP=1
export SIM_TS_PROFIT_MULTIPLIER=3.0
export LIVE_GATE_ROLLING_MODE=ratio
export LIVE_GATE_ROLLING_PCT=0.999950829
export LIVE_GATE_ROLLING_DAYS=90
export SIM_TS_MAX_GAP=0.03
export SIM_TS_MAX_GAP_WEAK=0.03
export SIM_F_BASE=0.015
export SIM_RATE_FEE=0.000982
export SIM_SLIPPAGE_RATE=0.000067
export LIVE_FEAT_DUMP_ROTATE_MIN=10
export JAVA_TOOL_OPTIONS="-Xms3g -Xmx3g -Dfile.encoding=UTF-8 -Duser.timezone=Asia/Ho_Chi_Minh"
EOF
# 4b) kiểm key: tập key 242 \ shadow phải RỖNG (trừ đường dẫn model khác thư mục)
$S242 'grep -E "^export" /home/chuyennd/java/v_t_m/conf/env.sh | grep -viE "key|secret|passw|token"' | sed 's/^export //' | sort > /tmp/env242.txt
grep -E '^export' $A/conf/env.sh | sed 's/^export //' | sort > /tmp/envsh.txt
comm -23 <(cut -d= -f1 /tmp/env242.txt) <(cut -d= -f1 /tmp/envsh.txt)     # ky vong: (rong)
join -t= <(sort /tmp/env242.txt) <(sort /tmp/envsh.txt) | awk -F= '$2!=$3'   # ky vong: chi APP_*, *_MODEL_ONNX, SHADOW_C3_DIR
# 5) BUFFER gate = bản 242 (cùng model, cùng nguồn dữ liệu, cùng selector) ⇒ arm cùng lúc 242 (~10-07 17:01)
$S242 'cat /home/chuyennd/java/v_t_m/run/gate_ratio_live.bin' > $A/run/gate_ratio_live.bin
# 6) RESTART chuẩn (SIGTERM, không kill -9 thủ công)
cd $A && bin/daemon.sh restart && sleep 90 && grep -a -E 'GATE-RATIO\] LIVE|LIVE_PROFILE=c3_shadow\] BAT|Picked up JAVA_TOOL_OPTIONS|OI-LIVE\] inplace' logs/full.log logs/nohup.out | tail -6
```

**Theo dõi 2a** (Oracle, script nhẹ — chỉ đọc log/ps của chính shadow, ghi `~/claude_master/2a/`): mỗi giờ `ps -o rss,etime -p $(cat $A/run/*.pid)`, `grep -c` OOM/ERROR, số phút `[GATE]` distinct/giờ, dòng `[GATE-RATIO]` mới nhất, `[SHADOW] would-BUY|arm|closed`; mỗi ngày phân bố `p15_out` feat_dump shadow vs feat_dump 242 cùng cửa sổ (`deploy242_gate_lineage.py` §C, đổi `FEAT_DUMP_DIR`).

**Tiêu chí PASS 2a** (hai pha; FAIL bất kỳ ⇒ ROLLBACK):

| pha | thời lượng | tiêu chí PASS (đo được, chốt trước) |
|---|---|---|
| 2a-ops | **≥ 48 h** từ restart, phủ ≥ 4 lần auto-restart 12 h | (1) `OutOfMemoryError` = 0 (full.log + nohup.out + error.log); (2) ERROR mới = 0 (trừ `AEROSPIKE-RETRY` WARN); (3) `[GATE]` ≥ **95 %** số phút mỗi cửa sổ 6 h; (4) RSS: max ≤ heap + 1,5 GB và sau mỗi auto-restart cmdline/nohup có `Picked up JAVA_TOOL_OPTIONS` (heap đúng 3 g); (5) `[OI-LIVE] inplace refresh … evicted=0` mỗi giờ; (6) ORT(fold_20)(feat_dump shadow) ↔ `p15_out` max\|Δ\| ≤ 1e-6; (7) p15 shadow vs 242 cùng phút: \|Δp50\| ≤ 0,02 pp và `thr=[..]` trong `[GATE]` trùng ±1 % (cùng buffer, cùng input) |
| 2a-gate | từ khi arm (≈ **2026-10-07 17:01**) **+ ≥ 48 h** | (8) `[GATE-RATIO] q_t` ≠ 0,008 (đã arm); (9) `n_pass > 0` trong 72 h sau arm; (10) PREDICT pass/ngày ∈ **[0,34; 3,8]** (= [0,3×; 3,4×] danh nghĩa 1,13/ngày — trần nới cho phồng do buffer ngắn); (11) `[SHADOW] would-BUY` không trên coin legacy (`skip-LEGACY` đúng), mỗi leg có `[SHADOW] arm`/`closed` hợp lệ theo FLAT3: kiểm offline SL = entry·(1+peak−0,03) làm tròn 0,005 trên ≥ 90 % sự kiện `arm` |

**ROLLBACK 2a** (bất kỳ FAIL; < 2 phút):
```bash
A=/home/ubuntu/shadow_c3/app; B=$A/backup_2a_<TS>
cp -f $B/binance-java-sdk-1.2.4.jar $A/target/ && cp -f $B/env.sh $A/conf/env.sh && cp -f $B/config.properties $A/ && cp -f $B/start.sh $A/bin/
rm -f $A/run/gate_ratio_live.bin   # shadow truoc 2a KHONG co buffer (gate fixed); file 242 chi la ban sao
cd $A && bin/daemon.sh restart && (cd $B && sha256sum -c SHA256SUMS)   # verify jar c389b4be…
```
(Việc `rm` là trên Oracle shadow, file do 2a tạo; 242 không bị đụng.)

### 9.2 BẬC 2b — 242 vẫn PAPER (`SHADOW_NO_PUSH=true`, `LIVE_PROFILE=c3_shadow`) ≥ 7 ngày đã arm

Tiền điều kiện: 2a PASS (cả 2 pha) · owner gật · nếu đổi model gate: ứng viên đã qua 2a-bis trên shadow (cùng tiêu chí 1–11 + cổng (6) với model mới) và tool transform-reseed (§4) đã kiểm trên shadow.
Thay đổi trên 242 (ít nhất có thể): (a) `JAVA_TOOL_OPTIONS` (heap) — bắt buộc; (b) model gate + buffer transform — chỉ khi owner chọn đổi model; (c) không đổi key chiến lược nào khác (đã khớp B0, §7).
```bash
# ---- trên 242 (CHỈ khi owner duyệt 2b) ----
D=/home/chuyennd/java/v_t_m; TS=$(date +%Y%m%d_%H%M%S); M=/home/chuyennd/java/storage/ai_ml_data/ai_models_reg_v3
mkdir -p $D/backup_2b_$TS && cp -a $D/target/binance-java-sdk-1.2.4.jar $D/conf/env.sh $D/config.properties $D/run $M/Model_Regressor_Return15M.onnx $D/backup_2b_$TS/
(cd $D/backup_2b_$TS && sha256sum -b binance-java-sdk-1.2.4.jar env.sh config.properties Model_Regressor_Return15M.onnx > SHA256SUMS)
echo 'export JAVA_TOOL_OPTIONS="-Xms3g -Xmx3g -Dfile.encoding=UTF-8"' >> $D/conf/env.sh   # 242 TZ he thong = +07 (Asia/Bangkok)
# (b) chi khi doi model: scp ung vien -> $M/Model_Regressor_Return15M.onnx.new ; sha256 khop manifest ; mv -f ; dat buffer da transform vao run/
cd $D && bin/daemon.sh restart
```
**Tiêu chí PASS 2b** (≥ 7 ngày **sau arm**, đo như 2a): (1)–(11) của 2a trên 242 + (12) `parity_check.py all` (bản đã thêm `DCA_GRID_ENABLED`): config PASS, gate PASS (mode + repro), entry PASS (LIVE ≥ 1 entry), exit: mọi `[SHADOW] closed` khớp luật FLAT3/time-stop tính lại offline từ kline 1m (≤ 1 bước 0,005); (13) legacy: số legacy chỉ giảm khi đóng thật; mọi `New price SL`/`Update SL` của legacy đúng bảng §8 (arm 0,07, SL ≈ lãi−3 pp, ratchet chỉ ≥ 36,5 %); 0 lệnh thật mới (`Create order market` = 0; legacy chỉ có `New price SL`/`Update SL`); (14) PnL giấy tính lại có phí 0,1116 %/vòng + funding thật (offline) — **chỉ ghi nhận**, không làm tiêu chí GO (mẫu ~8–25 lệnh/7 ngày, không đủ power).
**ROLLBACK 2b:** `cp -f backup_2b_$TS/{binance-java-sdk-1.2.4.jar→target/, env.sh→conf/, config.properties, Model_Regressor_Return15M.onnx→$M/}` + khôi phục `run/gate_ratio_live.bin` từ backup + `bin/daemon.sh restart` + `sha256sum -c`.

### 9.3 BẬC 3 — mở lệnh thật (owner gật lần cuối) → **HIỆN CHẶN**

Không thể làm bằng `SHADOW_NO_PUSH=false` (không có tác dụng khi `LIVE_PROFILE=c3_shadow`, §9.0). Điều kiện mở khoá (tất cả):
1. **Code `c3_live`** (vòng sau, có pre-reg + unit test + parity): chiến lược C3 giữ nguyên (S1 + net015 + G2 + FLAT3 ratchet liên tục + time-stop 168 h **đóng thật**), push lệnh thật, **giữ tách legacy** (legacy vẫn luật §8), sizing trên equity thật + `SIM_F_BASE`, kill-switch đọc env `SHADOW_NO_PUSH` mỗi lệnh (đường cũ `Cfg.get`, `BinanceOrderTradingManager:175`) + file cờ `run/KILL` kiểm mỗi tick.
2. **DCA grid** ở đường live (hoặc owner chấp nhận "B0-không-grid" sau pre-reg sim đo tác động trên DEV).
3. 2b PASS; buffer gate **≥ 30 ngày**; heap fix đã chạy ≥ 7 ngày.
4. Model gate theo quyết định owner (khuyến nghị đúng-B0: cut20261001, làm mới mỗi quý).

Giới hạn ban đầu đề xuất (không đổi tham số chiến lược làm lệch gate): **`SIM_F_BASE=0.0075`** (nửa B0) 14 ngày đầu, **giữ TOPK=16** (đổi TOPK đổi tập ứng viên ⇒ đổi phân vị gate), trần **≤ 3 entry PREDICT mới/ngày** và `SIM_U_MAX=0.30` (trần margin 30 % equity) — sau 14 ngày không sự cố ⇒ F_BASE 0,011 → 0,015 mỗi 14 ngày.
Theo dõi 24 h đầu (mỗi entry): giá khớp vs giá tín hiệu (trượt ≤ 0,3 %), SL đặt lên sàn ngay khi arm, margin ≤ kế hoạch, `[GATE]` coverage, không entry trên coin legacy. **Kill-switch:** `sed -i 's/^export SHADOW_NO_PUSH=.*/export SHADOW_NO_PUSH=true/' conf/env.sh && bin/daemon.sh restart` (≤ 1 phút; vị thế đã mở vẫn được quản lý exit bởi SL trên sàn + đường exit). ROLLBACK = về cấu hình 2b từ backup.

## 10. MỤC BỎ / GIỚI HẠN (khai rõ)

- **Không** sửa/restart gì trên 242 (chỉ `cat/grep/tail/ls/sha256sum/ps/free/dmesg`, `tar cf -`/`cat` ra stdout để kéo `feat_dump/`, jar, `.onnx`, buffer về Oracle). Không deploy shadow. Không sửa `.java`. Không sim Java, không Kaggle.
- RSS trend chỉ có 2 điểm (17:11, 17:31) + VmHWM — không đủ cho "24 h trend"; bù bằng 0 OOM/ERROR 5 ngày + 100 % `[GATE]` 30 h. Trend thật đo ở 2a.
- Q2 dùng feat_dump LIVE 6 229 phút (4,3 ngày, có khoảng trống trước EXPORT_FIX) + replay offline 2026-07…09 — 2026 **chỉ** để so phân bố; không chấm sim, không chọn tham số. Model cut20260401/20260701 train có 2026 — chỉ dùng cho truy vết lineage/ứng viên LIVE.
- Harness chạy trong bản sao cách ly (`~/claude_master/1002/deploy242/harness/`): **không** ghi đè `docs/result/parity_report.*` và `research/parity/data/*` của repo.
- Không đo được tầng exit/entry live (0 lệnh từ 12/09; gate đang warm-up tới ~10-07).
- Không xác định số leg DCA-grid của B0 từ printDone (leg đã merge) ⇒ tác động "không-grid" chưa định lượng (cần pre-reg sim).

## 11. ARTIFACT (Oracle `~/claude_master/1002/deploy242/`, không commit dữ liệu)

`probe1.txt`…`probe5.txt` (READ-ONLY 242) · `live242/{jar242.jar,gate242.onnx,gate_ratio_live.bin,feat_dump.tar}` · `lineage.json` · `lineage_probe.json` · `jardiff.json` · `harness_all.txt` · `model/Model_Regressor_Return15M.onnx` (+`manifest.json`, cut20260101) · `model_cut20260701/` (+`manifest.json`). JSON gộp số chính: `docs/audit/DEPLOY242_G2FLAT3_READINESS_20261002.json`.
