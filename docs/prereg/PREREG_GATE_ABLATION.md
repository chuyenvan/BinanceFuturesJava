# PREREG — GATE_ABLATION (Pha A chương trình GATE)

- **Chốt:** 2026-10-04, TRƯỚC khi sinh bất kỳ pred.bin thay thế / train / sim / đo nào của vòng này. Arm, luật, thước do MASTER chốt; agent chỉ thêm chi tiết kỹ thuật (§3) — ghi rõ lý do, chốt trước khi thấy số.
- **Nền tài liệu:** `docs/audit/GATE_INVENTORY_20261004.md` (886312a4), `docs/result/RESULT_PREDBIN_REPRO.md` (bcfa83b8), `docs/RISK_APPETITE.md` §9 (A-20261003, A.4, A.6), reaudit_1002.
- **Ràng buộc:** 0 sửa .java, 0 build, 0 Java/sim trên Oracle (sim chỉ Kaggle, kernel sinh từ `tools/kaggle_sim.py` HEAD md5 `8b60b00afad39f2528aaa15092225c9b`, guard NOWRITE242), 0 chạm 242/shadow_c3, DEV ≤ 2025-12-31 (2026 niêm phong), RAM ≤ 8G + lock `oracle_heavy.lock`.

## 1. Câu hỏi
- **Q1** Gate p15 có giá trị TIMING đo được không (so với gate ngẫu nhiên cùng quota)?
- **Q2** 33 feature có hơn 1 quy tắc đơn không?
- **Q3** 4 cột lịch (hourOfDay/dayOfWeek/weekOfMonth/monthOfYear) mang tín hiệu thật hay overfit DEV?
- **Q4** Nhãn 15' có tốt hơn 60' không?
- **Q5** Nhiễu retrain của gate model là bao nhiêu (để diễn giải Q3/Q4)?

## 2. Tham chiếu và khung
- **A1** = B0@K24, bins S1 deploy: Kaggle out `~/kaggle_sim/out/n700-a1`; printDone md5 **`d9abf35fdc93cfbcf7c41c9c62c22c20`**, n 3526, n/năm(2022–25) 732,25, eq 144 974, CAGR22 36,65, maxDD MTM −22,21, UW 117, Calmar22 1,650; jar `7368be46…` (sim-jar-gdv2), bundle `sim-x1-2021-bundle`, profile `r4_kg0_k16_f015_g155` + B0OV (ratio/90/0.999950829/GIVEBACK 1.0/MAX_GAP 0.03/0.03) + `SELECTOR_RANK_TOPK=24`, sim_end 20251231.
- **pred.bin gốc:** `/home/ubuntu/wfo_ds_x1_2021/pred.bin` md5 **`5dd6bb4c3f98d89d58770005c0001526`**, n = 2 500 260, big-endian `[count:i32]` + n×`[ts:i64][p15:f32][risk4h:f32]`, 2021-04-01 00:00 → 2025-12-31 23:59 (+07), lưới 1'.
- **Mỗi arm = 1 pred.bin thay thế**: chỉ thay cột p15; `ts` và `risk4h` giữ nguyên byte; header count giữ nguyên. Mọi thứ khác y hệt A1 ⇒ so GHÉP CẶP trực tiếp với A1.
- **Store feature:** `~/claudedata/gate_dataset_full.csv.gz` md5 `4bde28cd6d439ec009954bb6ec7d2537` (33 cột V3FULL + `label_oldbasket`). Script recipe `ml/gate/train_gate_fold.py` md5 `b41c9159597ceecb254240b789429a98`.

## 3. Arm CỐ ĐỊNH (5 kernel Kaggle; KHÔNG thêm arm)
| arm | p15' | dự báo MASTER | trong k? |
|---|---|---|---|
| **G-RND** | iid Uniform(0,1) theo phút, `np.random.default_rng(20261004).random(n)`, rồi biến đổi đơn điệu §3.1 | ΔCAGR −10…−20pp | có |
| **G-RULE** | `−momentum15M` (= −`MarketDataObject.rateDown15MAvg`) từ store, rồi §3.1 | ΔCAGR −3…−8pp | có |
| **G-NOCAL** | retrain đúng recipe, bỏ 4 cột lịch (30 feature), seed 42, purge 15', nhãn `label_oldbasket`; output THÔ | Δ ±2pp | có |
| **G-H60** | retrain đúng recipe (33 feature, seed 42), nhãn max upside 60' cùng rổ losers (§3.3), purge 60'; rồi §3.1 | Δ −2…+3pp | có |
| **G-SEED7** | retrain đúng recipe, seed 7 (chỉ `random_state`); output THÔ | nhiễu | KHÔNG (chỉ báo cáo) |

### 3.1 Biến đổi đơn điệu về phân phối p15 gốc (chi tiết kỹ thuật agent thêm — lý do)
Gate KHÔNG chỉ là quota xếp hạng: (a) nhánh `sp==null` (DCA_LEVEL1: 61 lệnh A1, p15 ≥ 0,0128) và warm-up 7 ngày dùng ngưỡng TUYỆT ĐỐI 0,008 trên p15 (`EntryGate.java:195`); (b) `r = p15/factor(sp)` nên ĐỘ PHÂN TÁN của p15 quyết định trọng số p15 vs sp khi xếp hạng (minute, coin). Uniform(0,1), đơn vị cột feature, hay nhãn 60' đều sai thang ⇒ lẫn hiệu ứng thang với hiệu ứng timing.
⇒ Với **G-RND, G-RULE, G-H60**: `p15' = sort(p15_gốc)[rank(x)]` (rank 0..n−1, `argsort(kind="stable")`) — tức p15' là HOÁN VỊ của đúng tập giá trị p15 gốc, xếp theo thứ tự của chuỗi x. Biên tổng (marginal) giữ y hệt; thứ tự phút giữ y hệt x. Với G-RND, đây đúng là rút iid từ phân phối gốc (inverse-CDF của Uniform).
**G-NOCAL, G-SEED7: output THÔ** (cùng nhãn ⇒ cùng thang; "retrain đúng recipe" nguyên văn). Không áp biến đổi này sau khi thấy số; không thử phiên bản thô/biến đổi còn lại.

### 3.2 Retrain = đúng recipe `train_gate_fold.py`
- `XGBRegressor(objective="reg:squarederror", max_depth=4, n_estimators=150, learning_rate=0.05, subsample=0.8, colsample_bytree=0.8, min_child_weight=10, random_state=SEED, n_jobs=4)`, X float32 theo thứ tự V3FULL, y float32.
- 19 fold DEV: cutoff `yyyymmdd` = 20210401 + 3i tháng (i = 0..18). Train: `ts < pd.Timestamp(yyyymmdd)(UTC) − PURGE` (y nguyên script, kể cả lệch +07/UTC 7h có sẵn của recipe); OOS: `[cutoff_+07, cutoff_kế_+07)` ∩ ts pred.bin (y như `WFOGateRunner`, JVM +07). Predict bằng `model.predict` (float32) — thay ONNX (cùng cây; G0 kiểm).
- PURGE: 15' cho nhãn 15'; 60' cho G-H60 (đúng quy tắc `WFOGateRunner.runPythonTrain`).
- ts pred.bin không có trong store ⇒ giữ p15 gốc tại phút đó, ĐẾM và báo (kỳ vọng 0).

### 3.3 Nhãn 60' cho G-H60 (store không có cột này)
- Store chỉ có `label_oldbasket` (15'), `label_ret60m` (close-to-close, KHÔNG phải max upside), `label_max24h`. ⇒ Dựng lại bằng Python (đọc ticker bins `~/java/simulator/kaggle_data_hpo/ticker_*.bin.gz` bằng `research/analysis/jbin.py`, 0 Java) đúng định nghĩa `HistoryManager.findPotentialLosersShort` (totalUsdt ≥ 5000 nến hiện tại; max(maxPrice) trên nến `startTime ≥ ts−15'`; drop < −0,001; 60 coin drop sâu nhất; coin vắng ≤15' dùng nến cuối) + `ExportGateDataset.basketMaxGain` (entry = close@ts của coin có mặt ở ts; max_k (maxPrice_k − entry)/entry trên nến (ts, ts+H], sàn 0; TB qua coin; stepMin = 1 cho H ≤ 150').
- **Cổng nhãn (trước khi dùng G-H60):** bản dựng lại với H = 15' phải khớp `label_oldbasket` của store: pearson ≥ 0,99 trên toàn 2021-01..2025-09 VÀ ≥ 0,98 từng năm. Trượt ⇒ G-H60 VOID (không sim), báo MASTER.
- Nhãn 60' chỉ tính tới ts ≤ 2025-12-31 22:59 (+07) để không chạm dữ liệu 2026.

## 4. Cổng
- **G0 tái lập:** retrain seed 42, 33 feature, `label_oldbasket`, purge 15' → so pred.bin gốc: pearson từng fold ≥ 0,99 (19/19). Ghi md5 + pearson/spearman per fold. Trượt ⇒ DỪNG, báo MASTER (không sinh NOCAL/H60/SEED7).
- **G1 format:** mọi pred.bin thay thế: n = 2 500 260, cùng header/dtype/offset, `ts` + `risk4h` byte-identical với gốc; md5 từng file ghi vào RESULT (các file sinh SAU commit này; script sinh tất định theo seed/recipe ở trên). Spot-check 3 mốc 2022-06-13, 2024-08-05, 2025-10-10 (00:00 +07 và phút có p15 gốc max của ngày): in p15 gốc vs thay thế.
- **Kaggle:** template = `ks.KERNEL_TEMPLATE` HEAD + 1 khối chèn (assert count==1) thay `pred.bin` bằng file từ dataset arm (symlink market/funding, viết lại `md5_pred` trong manifest), + ghi `pred_md5_base`/`pred_md5_used` vào result.json. Kernel phải log md5 pred gốc = `5dd6bb4c…`. Tối đa 2 kernel song song.
- **Parity từng run:** jar sha `7368be46…`, mapper ≥ 800, `SELECTOR_RANK_TOPK=24` trong prof_run, `pred_md5_used` = md5 arm, `pred_md5_base` = `5dd6bb4c…`, n, eq, md5 printDone. Trượt ⇒ run VOID.
- **G2 quota (sau sim):** (i) n lệnh/năm (đóng 2022–2025, /4) và (ii) số phút gate-mở/năm (= số phút phân biệt có ≥1 entry PREDICT_SYMBOL_TRADE, TB 2022–2025) của mỗi arm phải trong ±25% của A1. Lệch hơn ⇒ ghi "lỗi cơ chế", KHÔNG diễn giải PnL arm đó.

## 5. Thước (vs A1, ghép cặp)
- Bootstrap return NGÀY MTM ghép cặp block-10d, NREP 2000, seed 20260905, cửa sổ 2022-01-01..2025-12-30 (equity rebase 2021-12-31) — cùng máy đo `n700_driver` (SAD.daily_boot). Chỉ số: **ΔCAGR22** (thước chính), ΔPnL (PnL đóng theo ngày, cùng khối), maxDD MTM, Calmar22 (= CAGR22/|maxDD MTM 2022+|), UW (ngày); theo NĂM và theo QUÝ.
- CI raw 95% và **inflate k = 4** (G-RND, G-RULE, G-NOCAL, G-H60): half-width × √(2 ln 4) = 1,6651. G-SEED7 không tính vào k.
- ΔCalmar bootstrap ledger-closed KHÔNG dùng.
- Offline (báo cáo, không phải cổng): rank-IC (Spearman) theo phút của mỗi p15' (và p15 gốc) với nhãn 15' (`label_oldbasket`) và nhãn 60' (§3.3) trên 2022-01-01..2025-09-30.

## 6. Luật diễn giải (cố định)
- **Q1:** G-RND ΔCAGR22 ngoài CI inflate về phía âm (cận trên < 0) ⇒ "gate có giá trị timing"; CI inflate chứa 0 ⇒ "không đo được giá trị timing"; cận dưới > 0 ⇒ "gate model kém ngẫu nhiên".
- **Q2:** G-RULE CI inflate chứa 0 ⇒ "33 feature ≈ 1 quy tắc"; cận trên < 0 ⇒ "33 feature > 1 quy tắc"; cận dưới > 0 ⇒ "quy tắc > model".
- **Q3/Q4:** so band nhiễu G-SEED7: |ΔCAGR22_arm| ≤ |ΔCAGR22_SEED7| ⇒ "không phân biệt được với nhiễu retrain".
- **G-H60 GO** theo §9 A.4: ΔCAGR22 > 0 ngoài CI inflate (cận dưới > 0), maxDD MTM ≥ −40%, Calmar22 ≥ 0,9×A1, ΔROI năm ≥ 0 ở ≥ 3/4 năm (2022–2025). Thiếu 1 ⇒ NO-GO.
- **Luật đơn giản hoá:** G-NOCAL CI inflate chứa 0 VÀ ΔCAGR22_NOCAL ≥ ΔCAGR22_SEED7 − |ΔCAGR22_SEED7| (không tệ hơn band SEED7) ⇒ ĐỀ XUẤT bỏ cột lịch vì robustness (quyết định owner, không tự áp).
- Arm trượt G2 hoặc parity ⇒ không diễn giải. Không tune, không thêm biến thể, không đổi biến đổi §3.1 sau khi thấy số. Mọi thứ ngoài pre-reg = chỉ báo cáo.

## 7. Thứ tự
1. Commit + push pre-reg này (hash ghi ở RESULT). 2. G0 (lock nếu > 4G). 3. Sinh G-RND, G-RULE → G1 → dataset Kaggle → 2 kernel. 4. Nhãn 60' + cổng nhãn; NOCAL/SEED7/H60 → G1 → kernel (≤ 2 song song). 5. `research/analysis/gate_ablation_driver.py` (sinh pred.bin + Kaggle + thước), `docs/result/RESULT_GATE_ABLATION.md` + `docs/result/gate_ablation.json`; commit + push.

## 8. Rủi ro biết trước
- Đường chèn pred.bin trên Kaggle là mới (không có run "pred gốc qua đường chèn" vì không được thêm arm) — kiểm bằng md5 pred base/used + parity; nếu cần, MASTER quyết định có thêm run REF hay không.
- Retrain không bit-exact (RESULT_PREDBIN_REPRO: pearson ~0,99) ⇒ chênh G-NOCAL/G-H60 vs A1 gồm cả nhiễu retrain + chênh "retrain vs pred.bin gốc"; G-SEED7 đo đúng phần này (nó cũng là retrain vs gốc).
- Nhãn 60' dựng lại từ ticker file (không phải Aerospike) — cổng §3.3 chặn lệch nguồn.
