# R1 — PHA 0: S1 còn đóng góp gì trong B0? (khảo sát + thiết kế, CHƯA chạy thí nghiệm)

Ngày 2026-11-09. Agent Opus (giao bởi MASTER). Chỉ đọc code/dữ liệu. Không chạy kernel, không ghi 242/Aerospike.
Repo đọc: `~/claude_master/v12/c3live` (HEAD a48cc56c, nhánh v1.2/c3-live) và `~/claude_master/vz_e1_wt` (HEAD cb64d74e).
Script đo nhẹ (chỉ đọc) nằm cùng thư mục: `r1_lvl.py`, `r1_ovl.py`, `r1_src.py`, `r1_cov.py`, log `*.log`.
Quy ước: [K] = đã kiểm trong code/dữ liệu; [SĐ] = suy đoán.

---

## 0. Trả lời ngắn

- "p15" là dự báo **mức thị trường**: một số mỗi phút, giống nhau cho mọi coin. Vì vậy p15 không xếp hạng được coin. Arm "xếp hạng p15 thuần" **không định nghĩa được** [K].
- Trong B0, S1 là **thứ tự chọn coin**. Gate dùng một **thang giá trị** lấy từ net015 (P(win), họ G015). Coin hạng k theo S1 nhận P(win) lớn thứ k của tick đó (quantile-map). Selector "trước S1" chính là **net015 raw**. So sánh công bằng là S1-map với net015-raw.
- Khi S1 có điểm, top-24 theo S1 chỉ trùng **39–49 %** với top-24 theo net015. Spearman trung vị trong tick là 0,39–0,65 [K, 2024Q3–2025Q4]. Như vậy, lúc hoạt động, S1 chọn khác net015 rất nhiều.
- **Phát hiện cấu trúc 1 [K]:** bins sim chỉ có điểm S1 ở tick mà gate cũ mở (p15 ≥ 0,008, seed 42). Ở các tick còn lại, coin giữ nguyên net015. Gate của B0 (QUOTA, 8 seed p15) mở cả ngoài tập này, nên **khoảng 10–30 % leg PREDICT DEV được xếp theo net015, không phải S1**. Live chấm S1 ở mọi tick 15′. Hệ quả là sim B0 đang đo một hệ lai, còn live là S1 thuần.
- **Phát hiện cấu trúc 2 [K code, chưa chạy thử]:** leg BIG_DOWN (7 % số leg, 9–12 % PnL B0) trong sim lấy top-2 theo thứ tự bins S1-map. Trên live, cùng leg đó lấy theo `tier1Score` (Funding pNoPump hoặc net015-raw), không qua S1. Đây là lệch parity tiềm năng. Theo những gì đã đọc, harness v1.2 (S1-I/S1-m/S1-V/GV-*) không kiểm việc chọn coin của BIG_DOWN [SĐ một phần].

## 1. Định nghĩa chính xác trong B0

### 1.1 Cấu hình sim B0 (X14) [K]
`~/kaggle_sim/out/tsx-ho-x14-s42/prof_run.properties` = profile `r4_kg0_k16_f015_g155` + override:
`SELECTOR_RANK_TOPK=24`, `SELECTOR_ONLY_ENTRY=0`, `WFO_FUNDING_PRED_DIR=<bins S1-map>`, `SIM_GATE_DYN_SCALE=1.55`,
`SIM_GATE_ROLLING_MODE=ratio`, `_DAYS=90`, `_PCT=0.999950829`, `GATE_QUOTA_SKIP_WHEN_FULL=true`,
`SIM_LOSER_TS_EXT_HOURS=336` + `SIM_LOSER_TS_EXT_DAYS=<cờ X14>`, `SIM_RATE_PROFIT_STOP_MARKET=0.07`.
Bins DEV là `~/predwf_map_s1a2_x1` (16 fold, 2022Q1→2025Q4). Bins HO 2026 nằm trong `sim-ho26a-bundle`, dùng S1 đóng băng `s1a2x1_cut20251231` và net015 ONNX đóng băng (PREREG_HOLDOUT2026H1.md:40,114,313).

### 1.2 Bins S1-map được dựng thế nào [K]
- Pool S1 gồm các tick 15′ mà gate cũ mở (p15 ≥ 0,008, file `wfo_gate_pred.csv`), lấy những coin **có nhãn** g1lite (`research/pipeline/x1/x1_ledger.py:4,31-33,42`).
- Ranker: XGBRanker rank:ndcg topk8, nhãn rel5 = quintile-trong-tick của g1lite 72h, 9 feature KEEP9, 16 fold quý purge 72h (long_1003 + S1_FIRSTHIT_RANK).
- Quantile-map (`x1/x1_build_map.py:31-45`, bản Java `LiveBuildMap.java:10-40`): trong tick, coin hạng k theo S1 nhận P(win) net015 lớn thứ k. **Coin không có điểm S1 giữ nguyên P(win) net015.** Multiset P(win) của mỗi tick không đổi.
- Sim đọc `symbolPred = 1 − P(win)`, sort tăng (`WfoDataset` forward-fill lưới 15′ ra từng phút, `WfoDataset.java:122-125`).

### 1.3 Đường sim (`research/SimulatorMarketLevelTicker1MStopLoss.java`) [K]
- **PREDICT (leg selector):** `selectCands` lấy K=24 phần tử đầu của `symbol2Pred` (:770-776). Hạng đếm trên toàn pool, gồm cả coin đang giữ; coin đang giữ bị bỏ qua sau khi đếm ("cap-then-skip", :442-463). Sau đó gọi `createOrderBUY(..., selRank)`.
- **Gate (:1513-1524):** khi sổ đầy (`managerBudget == null`) và skipFull bật thì REJECT mà không nạp r (`AIRejectFilter.java:105-109`). Nếu không, `r = p15 / (max(0,26787, sp/0,15·1,2876)·1,55)` (`GateRollingRatio.java:115-118`). `q_t` là quantile 0,99995083 của r trong 90 ngày, tính một lần mỗi giờ, causal (`GateRatioBuffer.java:39-48`). PASS ⇔ `p15 ≥ q_t·factor·gs` ⇔ `r ≥ q_t` (`EntryGate.threshold`).
  - ⇒ S1 tác động lên gate **chỉ qua hạng**. Rank 1 luôn nhận sp nhỏ nhất của tick, nên tập r của top-24 gần như **bất biến** khi đổi thứ tự (S1, net015 hay hoán vị). Chỉ có tập coin đang giữ và độ đầy sổ làm nó khác đi. Đây là tính chất giúp ablation sạch.
- **BIG_DOWN (:368-380):** khi `getMarketStatus1M` trả BIG_DOWN, lấy `NUMBER_ENTRY_EACH_SIGNAL=2` coin đầu (1 coin nếu SMALL_*) theo **cùng bins** (`MarketBigChangeDetector.getTopSymbolArray:141-162`). Leg này **không qua gate** (:1506).
- **K24 / skipFull / X14:** K24 chỉ cắt số ứng viên. skipFull chỉ tác động khi sổ đầy, và vì đọc hạng của S1 nên chịu ảnh hưởng gián tiếp. X14 là luật exit/hold, độc lập với S1.

### 1.4 Đường live v1.2 (`trading/DetectEntrySignal2TradeNormal.java`) [K]
- Selector chạy mỗi 15′ (CADENCE-SPLIT, :483-494). Thứ tự lấy từ `buildS1Pool` (S1RankerLive: ONNX `s1a2x1_cut20251231`, 9 feature từ close 1h Aerospike) và chấm **mọi coin, mọi tick 15′** (:506-523).
- Thang gate dùng `buildValueMap`, tức net015 live quantile-map theo thứ tự S1 (:524-531). `GatePreFilter.runSelector` lấy top-24 (bỏ A1, đếm hạng gồm cả LEGACY/held), rồi `createOrderBuyRequest` đi qua cùng `AIRejectFilter.entryGate` (:578-603).
- **BIG_DOWN live:** `getTopSymbol(numberOrder, ..., sortedCandidates)` (:407-421). Ở đây `sortedCandidates` được khoá bằng `tier1Score`, tức Funding `preds[0]` hoặc net015-raw nếu bật `SELECTOR_TIER1_NET015`, và đã lọc `maxThres` (:1075-1089). Leg này đi vào `C3LiveHook.onLeg` với mọi level (:1266-1271). **Không dùng S1.** Env 242 chưa đọc được (cấm ssh 242).
- Parity harness v1.1/v1.2 (PREREG_PARITY_V11_WINDOW.md:70-74): S1-I = thứ tự top-24 sel_dump khớp s1_dump; S1-m = ONNX khớp score; S1-V = feature/score tính lại từ Vision; GV-I/GV-O = thang gate. Các phép này kiểm **đường PREDICT**. Chúng không kiểm coin của BIG_DOWN, và không kiểm việc sim dùng net015 ở tick không có S1 [SĐ: theo những gì đã đọc].

## 2. Đo nhanh (chỉ đọc, Oracle, < 3 phút CPU)

### 2.1 Thành phần leg B0 X14 (`r1_lvl.py`, 8 seed, TB/seed)
| | leg DEV | PnL DEV | leg HO-chain | PnL HO-chain |
|---|---|---|---|---|
| PREDICT_SYMBOL_TRADE | 91,4 % | 82,9 % | 91,3 % | 80,5 % |
| BIG_DOWN | 7,0 % (248/seed, giống nhau 8 seed) | 9,1 % | 7,0 % | 11,9 % |
| DCA_LEVEL1 | 1,6 % | 8,0 % | 1,7 % | 7,5 % |
(Run HO-chain chạy 2021→2026-09 với cờ X14 của HO. Đây không phải số riêng của 2026.)

### 2.2 Độ phủ S1 trong bins (`r1_src.py`, `r1_ovl.py`, nguồn net015-raw = `~/val_pred_net015`)
- `val_pred_net015` có multiset P(win) mỗi tick **= 100 %** bins map (fold 20250101), nên chính là nguồn net015 raw. `~/sel_models_net015` **không phải** nguồn này (multiset khớp 0,01 %).
- Tỉ lệ tick y hệt net015 (S1 không có điểm): 2024Q3–Q4 **0,94**; 2025Q1–Q3 0,76–0,86; 2025Q4 0,22.
- Ở tick S1 có điểm: top-24 S1 ∩ net015 = **0,39** (2024) / **0,49** (2025). Top-8 0,31/0,33. Spearman trung vị 0,39/0,65.
- Raw net015 cho 2022–2024Q2 **không còn trên Oracle** (`~/claudedata/predwf_G015x26` đã mất). Ứng viên là Kaggle `chuyendinh/predwf-g015x26-gate` (16 file 2022Q1–2025Q4, kích thước khớp). Cần cổng G-NET0 (§4).

### 2.3 Leg B0 rơi vào tick có điểm S1 (`r1_cov.py`, tick = floor15′(start−7h), `pred_s1a2x1.parquet` = 17 349 tick có S1 trong 2022–2025)
| năm | PREDICT: % leg ở tick có S1 | % PnL | BIG_DOWN: % leg | % PnL |
|---|---|---|---|---|
| 2022 | 86,6 | 123,6 | 70 | 59 |
| 2023 | 69,3 | 50,9 | 24 | 41 |
| 2024 | 88,3 | 85,7 | 77 | 93 |
| 2025 | 90,4 | 79,6 | 100 | 100 |
Chỉ tính leg vào đúng mốc 15′ thì tỉ lệ là 92–100 %. Leg PREDICT có thể gồm leg DCA-grid mang nhãn của cụm [SĐ], nên đây là số xấp xỉ. 2021H2 hoàn toàn không có S1: `pred_s1a2x1` bắt đầu từ 2022-01-01.

## 3. Lịch sử S1: các đường đã ĐÓNG (không lặp lại)
| Vòng | Kết quả | Nguồn |
|---|---|---|
| S1 vs G015 (C2, gate công bằng) | map_s1a2 16,2 vs G015 13,9 CAGR. C2b +7,35pp, maxDD −13,1 vs −20,8 | selector_s1_ledger, config_redesign |
| SELECTOR_ABLATION @K16 (33d8fc17) | B0 − random-K16: Calmar +3,02 [1,38; 6,74], **CAGR +24,4pp**, 4/4 năm. Thanh khoản thua B0 −17,9pp | RESULT_SELECTOR_ABLATION.md |
| R50/R100 (b7fedef4) | Xáo trong top-50 mất ~60 % khoảng cách. Giá trị nằm ở cắt top-50→16 | RESULT_SELECTOR_ABLATION_R50.md |
| S1_K24 (a23d83ad) | NO-GO 3/3. ndcg@24 bị bác. GEOM +0,73 (bị pha loãng). **ROI/lệnh phẳng theo hạng 1–24** ⇒ xếp lại trong top-24 không phải lever | batch_1004 |
| S1_RETRAIN_NOISE | sd 0,83pp CAGR (3 seed, K16). MDE80 1 run +3,3pp | long_1003 |
| Đặc trưng/nhãn/HPO S1 | Đã ĐÓNG: OI12, FEATGRP, FS15, LS_TAKER, OFI (money NULL), HPO, bagging, MAXFAV, 5m, first-hit (G015 + S1), H3 đầu tuyệt đối, CONF_SIZE, PREDICT_SYMBOL_RATE_MAX. GEOM < MDE, chỉ kiểm forward. S1_V2 draft chưa chạy | long_1003, batch_1004, selector_edge_evidence |
| SELECTOR_LEG_CUT (T170) | Cắt hoặc giới hạn leg selector: NULL | RESULT_SELECTOR_LEG_CUT.md |
| NSEL, MD_STRAT, MKT_UP2 (gate theo S1) | ĐÓNG | nsel_1008, entry_confirm_1020 |
| "S1 selector IC 0,11 không ra tiền" | Đây là **S1 của REX** (hệ mới, LightGBM ngày), **không phải** S1 của B0. Không dùng làm bằng chứng cho B0 | rex_1016 |

Chưa từng đo trên khung hiện tại (K24 + skipFull + X14): B0 so với net015-raw, và B0 so với random. Mọi số ablation ở trên là K16 hoặc khung cũ hơn.

## 4. Thiết kế ablation (tối đa 4 arm; chỉ đổi bins, giữ jar/profile/gate/exit)
Mọi arm giữ nguyên tập (ts, symId), thứ tự record và **multiset P(win) mỗi tick**. Arm chỉ đổi coin nào nhận giá trị nào, nên gate gần như bất biến (§1.3). Cách sinh bins tái dùng `research/analysis/selector_ablation_scores.py` (SA_BLOCK trong kernel, assert sha bằng bản Oracle).

| Arm | Định nghĩa | Vai trò |
|---|---|---|
| **A0 = B0** | bins S1-map hiện tại (DEV `predwf_map_s1a2_x1`, HO bundle `sim-ho26a`) | nền |
| **A1 = NET** | bins net015 **raw** (DEV `predwf-g015x26-gate`, HO `predict_wf_2026*` net015 ONNX 8df74093/406e527f + fold 20260701), tức "B0 bỏ S1", thay bằng selector có sẵn trước S1 | **so sánh chính** |
| **A2 = RND** | hoán vị bộ-4 giá trị giữa các symbol trong cùng ts (rng seed 42), tức null selector. Áp lên bins A0 | sàn: thứ tự có còn quan trọng ở K24 không |
| **A3 = S1FULL** (tuỳ chọn, Pha 1b) | S1 chấm **mọi** tick (như live), map lên net015 raw. DEV dùng 16 model fold WFO predict-only; HO dùng model cut20251231 | đo đúng hệ live; chỉ chạy nếu A1 cho thấy S1 có đóng góp |

Đã bỏ "S1 tham số gốc": `~/predwf_map_s1a2` chỉ có 10 fold 2022Q1–2024Q2 [K], không phủ 2025/HO. Muốn có thì phải retrain, tức là một đề tài mới. Đã bỏ "xếp hạng p15 thuần" vì không định nghĩa được (§0). BIG_DOWN đổi theo bins ở mọi arm. Báo cáo tách theo level (PREDICT / BIG_DOWN / DCA).

## 5. Thiết kế đánh giá (để pre-register)
- **Dữ liệu:** DEV 2021-07→2025-12. Metric chính chấm 2022–2025 (CAGR22). Kernel DEV: `SIM_END_DATE=20251231`, cờ X14 DEV (giống `tsx-x14-*`). HO 2026-01→2026-09: kernel chain riêng với cờ X14 HO (giống `tsx-ho-x14-*`), chỉ chấm năm 2026, HOLDOUT_UNSEAL. HO đã bị dùng ≥ 5 lần (HO4, X14, UP_TRIG, T25…), nên **chỉ mô tả và xác nhận chiều**, không dùng để chọn.
- **Seed:** A0 và A1 dùng 8 seed gate (A1, S7, S13, S21, S99, S123, S777, S2024), ghép cặp. A2 dùng 4 seed (A1, S7, S13, S21) × 1 hoán vị, vì hiệu ứng kỳ vọng lớn (K16: 24pp). A0 tái dùng `tsx-x14-*` / `tsx-ho-x14-*` nếu kernel P0 trên ảnh Kaggle hiện tại cho md5 printDone trùng (1 kernel DEV + 1 HO). Nếu không trùng, chạy lại 8 seed.
- **Metric:** CAGR22, maxDD MTM ngày (`gvz_mtm`: import trước, assert missing = 0), Calmar = CAGR22/|maxDD|, PnL/lệnh, số lệnh/năm, UW. Tách theo level và theo năm. Bổ sung: tỉ lệ trùng tập lệnh với A0.
- **Tiêu chí chính (C1, A0 − A1, cặp theo seed, 2022–2025):**
  - "S1 CÒN đóng góp": mean ΔCAGR22 > 0, CI95 paired-t (8 cặp) có cận dưới > 0, ≥ 6/8 seed dương và ≥ 3/4 năm dương.
  - "S1 KHÔNG còn đóng góp": TOST, CI90 nằm trong [−1,5; +1,5]pp. Biên này ≈ 2 × sd retrain S1 0,8pp, tức dưới mức này thì không phân biệt được với nhiễu retrain.
  - Ngoài hai trường hợp trên là "không kết luận".
  - Phụ: ΔCalmar cùng chiều. Tiêu chí phụ không đổi được verdict chính.
- **C2 (A0 − A2):** CI95 cận dưới > 0 ⇒ "thứ tự selector còn là lever ở K24". **C3 (A1 − A2)** chỉ báo cáo.
- **Suy giảm theo thời gian (câu hỏi của owner):** ΔCAGR(A0−A1) theo năm 2022…2025 + HO 2026. Chỉ mô tả (5 điểm, không đủ lực cho test xu hướng). Nêu rõ HO 2026 dùng model S1 đóng băng, giống live.
- **MDE/nhiễu:** sd seed gate @K24+skipFull là 1,37pp (gate_1004). Half-width cặp ở S1_K24 với 4 seed là ~2,5pp. 8 cặp: sd cặp (2pp, [SĐ]) cho SE ≈ 0,7, CI95 ±1,7pp, MDE80 ≈ 2,0pp. 4 cặp: MDE80 ≈ 4pp. Nhiễu retrain S1 (sd ~0,8pp) **không** nằm trong phép so sánh vì S1 giữ cố định. Nó chỉ dùng để đặt biên tương đương.
- **Compute:** kernel DEV ≈ 42 phút (`tsx-x14-a1` 2622 s), kernel HO-chain ≈ 100 phút (`tsx-ho-x14-s42` 6008 s).
  - A1: 8 × (0,7 + 1,7) h ≈ 19 h.
  - A2: 4 × 2,4 ≈ 10 h.
  - P0 parity: 2 kernel ≈ 2,4 h.
  - Tổng ≈ **31 giờ kernel**, khoảng **16 h wall** với 2 kernel song song.
  - A3 thêm khoảng 2–3 h predict + 8 × 2,4 ≈ 22 h kernel.
  - Oracle: tải/kiểm `predwf-g015x26-gate` (~1,2 GB giải nén [SĐ]; nên giải nén trong kernel, Oracle chỉ cần sha), chấm MTM khoảng 1–2 phút/run, phân tích overlap < 5 phút.
- **Cổng trước khi chạy:**
  - G-NET0: multiset mỗi tick NET = A0 (100 %), và ở tick không có S1 thì cell bằng nhau 100 %.
  - G-P0: md5 printDone A0.
  - G-SAN: hoán vị khác thứ tự; NaN giữ vị trí.
  - G-GATE: số phút gate PASS A1 vs A0 lệch ≤ 2 % (kiểm tính bất biến của gate).

## 6. Rủi ro leakage / thiên lệch / multiple testing
1. **Pool S1 định nghĩa bằng tương lai [K]:** coin chỉ có điểm S1 nếu có nhãn g1lite 72h (`x1_ledger.py:42`). Coin thiếu nhãn, ví dụ sắp delist hoặc thiếu dữ liệu tương lai, giữ net015 trong cùng tick. HO 2026 cũng dùng "glob nhãn 2026 để xác định pool" (PREREG_HOLDOUT2026H1.md:40). Cả A0 lẫn A3 đều dính. Độ lớn chưa đo [SĐ: nhỏ].
2. **Pool theo gate cũ (p15 ≥ 0,008, seed 42) ≠ gate B0 [K]:** sim B0 là hệ lai S1/net015, còn live là S1 thuần. Mọi số B0 sim, kể cả HO, có thể lệch so với live theo hướng chưa biết. A3 dùng để đo điều này.
3. **BIG_DOWN lệch live/sim [K code]:** cần MASTER xác minh env 242 (`SELECTOR_TIER1_NET015`) và quyết định có thêm cổng parity cho coin BIG_DOWN hay không.
4. **net015 DEV là WFO; net015 HO là ONNX đóng băng (phương án A):** không trộn sang DEV, vì ONNX đóng băng chạy trên DEV sẽ thành in-sample.
5. **Đa kiểm định:** họ S1/selector đã có ≥ 45 config (ledger) + ~37 lần nhìn DEV (batch_1004). Đề tài này có 1 phép chính (C1). C2/C3 khai trước, không inflate C1. Với ≥ 2 phép quyết định thì inflate CI ×1,18 như R50. Không tune lại sau khi thấy kết quả, và không đổi K/gate trong vòng này.
6. **Seed:** 2022 chi phối phương sai (gate_1004). Cần báo ex-2022 để chắc kết luận không đến từ một sự kiện (05/2022).
7. **Diễn giải:** A0 − A1 đo giá trị của S1 **trên nền net015**, không phải giá trị tuyệt đối. Nếu A1 ≈ A0 thì chưa có nghĩa "bỏ S1 trên live" an toàn, vì live BIG_DOWN và thang gate vẫn phụ thuộc net015/Funding. Cần một quyết định riêng.
